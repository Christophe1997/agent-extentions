---
name: Redis Production Patterns
description: Use when the user asks about scaling Redis, production deployment, high availability, performance tuning, kernel tuning, Redis clustering, or learning from major tech companies' Redis implementations. Triggers on queries like "scale Redis", "production tuning", "Redis at scale", "kernel parameters for Redis", "Pinterest/Twitter/Uber Redis patterns".
version: 1.0.0
---

# Redis Production Patterns

Real-world patterns for scaling, tuning, and operating Redis in production.

## Topics

| Topic | Description |
|-------|-------------|
| [Kernel Tuning](#linux-kernel-tuning) | Essential OS-level optimizations |
| [Redis as Primary DB](#redis-as-primary-database) | Using Redis as authoritative store |
| [Pinterest Patterns](#pinterest-task-queue-and-functional-partitioning) | Functional partitioning, task queues |
| [Twitter Patterns](#twitter-internals) | Custom data structures, deep internals |
| [Uber Patterns](#uber-resilience-patterns) | Staggered sharding, circuit breakers |

---

## Linux Kernel Tuning

Essential kernel parameters to prevent latency spikes, persistence failures, and connection drops.

### Critical Settings

```bash
# /etc/sysctl.conf or via sysctl

# 1. Disable THP (Transparent Huge Pages)
# CAUSES: Latency spikes, memory allocation delays
echo never > /sys/kernel/mm/transparent_hugepage/enabled

# 2. Overcommit memory
# CAUSES: OOM killer may kill Redis unexpectedly
vm.overcommit_memory = 1

# 3. Net.core somaxconn
# CAUSES: Connection drops under high load
net.core.somaxconn = 65535

# 4. TCP backlog
# Related to somaxconn - increase TCP accept queue
net.ipv4.tcp_max_syn_backlog = 65535

# 5. File descriptor limits
# CAUSES: "Too many open files" errors
# In /etc/security/limits.conf:
redis soft nofile 65535
redis hard nofile 65535
```

### Apply Settings

```bash
# Apply immediately
sudo sysctl -p

# Verify
sysctl vm.overcommit_memory
cat /sys/kernel/mm/transparent_hugepage/enabled
```

### Redis Configuration

```bash
# redis.conf
tcp-backlog 511           # Should be <= net.core.somaxconn
maxclients 10000          # Adjust based on file limits
timeout 0                 # Don't timeout idle connections
tcp-keepalive 300         # Help detect dead peers
```

---

## Redis as Primary Database

Using Redis as the authoritative data store (not just cache).

### When to Consider

- Sub-millisecond latency requirements
- High write throughput needed
- Data fits in memory (or can tier to disk with Redis Enterprise)
- Can accept eventual durability (AOF/replication)

### Configuration

```bash
# redis.conf for durability

# Persistence
appendonly yes
appendfsync everysec        # Balance durability/performance
save 900 1                  # RDB snapshots for backup
save 300 10
save 60 10000

# Replication for HA
replicaof master-ip 6379

# Memory management
maxmemory 4gb
maxmemory-policy noeviction  # Don't evict primary data!
```

### Best Practices

1. **Always use replication** - At least 1 replica for failover
2. **Enable AOF** - Better durability than RDB alone
3. **Monitor memory** - Set alerts at 80% usage
4. **Backup RDB** - Regular snapshots to external storage
5. **Use Redis Sentinel or Cluster** - For automatic failover

### Anti-Patterns

- Using `allkeys-lru` eviction with primary data
- No persistence (data loss on restart)
- Single node (no failover capability)

---

## Pinterest: Task Queue and Functional Partitioning

Pinterest scaled from 1 to 1000+ Redis instances using these patterns.

### Functional Partitioning

Organize Redis instances by use case, not by sharding data:

```
# Instead of sharding user data:
user:1 → redis-user-1
user:2 → redis-user-2

# Partition by function:
session:*    → redis-sessions (TTL-heavy, eviction OK)
cache:*      → redis-cache (LRU eviction)
queue:*      → redis-queues (lists, reliability critical)
counter:*    → redis-counters (high write, INCR-heavy)
leaderboard:* → redis-leaderboards (sorted sets)
```

**Benefits:**
- Tune each instance for its workload
- Isolate failures (cache crash ≠ session loss)
- Different persistence policies per function
- Easier capacity planning

### Reliable Task Queue

Pinterest's pattern for background job processing:

```python
# Producer
def enqueue_job(job_data):
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "data": job_data,
        "enqueued_at": time.time()
    }
    # Push to pending queue
    redis.lpush("queue:pending", json.dumps(job))
    return job_id

# Consumer
def process_jobs():
    while True:
        # Atomically move from pending to processing
        job_json = redis.brpoplpush(
            "queue:pending",
            "queue:processing",
            timeout=5
        )

        if job_json:
            job = json.loads(job_json)
            try:
                execute_job(job)
                # Success - remove from processing
                redis.lrem("queue:processing", 1, job_json)
            except Exception:
                # Failure - job stays in processing for recovery
                log_error(job, exception)

# Recovery process (runs periodically)
def recover_stale_jobs(timeout=300):
    jobs = redis.lrange("queue:processing", 0, -1)
    now = time.time()

    for job_json in jobs:
        job = json.loads(job_json)
        if now - job["enqueued_at"] > timeout:
            # Re-queue stale job
            redis.lrem("queue:processing", 1, job_json)
            redis.lpush("queue:pending", job_json)
```

### Horizontal Scaling

1. **Start small** - Single instance per function
2. **Monitor metrics** - Memory, ops/sec, latency
3. **Add capacity** - New instance, update client routing
4. **Shard when needed** - Consistent hashing within a function

---

## Twitter: Internals and Custom Data Structures

Historical case study - many innovations now in Redis core.

### Key Innovations (Now in Redis)

1. **Quicklist** - Hybrid list encoding (ziplist + linked list)
2. **Memory optimization** - Better small object handling
3. **Pipeline optimization** - Batch command processing

### Lessons Learned

1. **Connection pooling** - Reuse connections, don't create per request
2. **Pipeline aggressively** - Batch commands to reduce RTT
3. **Monitor slowlog** - Identify expensive operations
4. **Use appropriate data structures** - Hash for small objects, avoid massive keys

```bash
# Monitor slow operations
SLOWLOG GET 10

# Configure slowlog threshold (microseconds)
SLOWLOG-SET-THRESHOLD 10000
```

---

## Uber: Resilience Patterns and Staggered Sharding

Uber handles 150M+ ops/sec with these resilience techniques.

### Staggered Sharding

Prevent coordinated failures across shards:

```
# BAD: All shards expire at same time
Shard 1: TTL = 3600 (expires at 00:00)
Shard 2: TTL = 3600 (expires at 00:00)
Shard 3: TTL = 3600 (expires at 00:00)
→ Thundering herd when all expire simultaneously

# GOOD: Staggered expiration
Shard 1: TTL = 3600 (expires at 00:00)
Shard 2: TTL = 3600 + 600 (expires at 00:10)
Shard 3: TTL = 3600 + 1200 (expires at 00:20)
→ Spreads load over time
```

### Circuit Breaker Pattern

```python
class RedisCircuitBreaker:
    def __init__(self, redis_client, failure_threshold=5, recovery_timeout=30):
        self.redis = redis_client
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure = None
        self.state = "closed"  # closed, open, half-open

    def execute(self, command, *args):
        if self.state == "open":
            if time.time() - self.last_failure > self.recovery_timeout:
                self.state = "half-open"
            else:
                raise CircuitOpenError("Circuit breaker is open")

        try:
            result = getattr(self.redis, command)(*args)
            if self.state == "half-open":
                self.state = "closed"
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure = time.time()

            if self.failures >= self.failure_threshold:
                self.state = "open"

            raise
```

### Graceful Degradation

```python
def get_user_with_fallback(user_id):
    """Try Redis, fall back to database, then to cache."""

    # Try Redis first
    try:
        cached = redis.get(f"user:{user_id}")
        if cached:
            return json.loads(cached)
    except RedisError:
        log.warning("Redis unavailable, falling back to DB")

    # Fall back to database
    try:
        user = db.get_user(user_id)
        # Try to repopulate cache
        try:
            redis.setex(f"user:{user_id}", 3600, json.dumps(user))
        except RedisError:
            pass  # Cache write failure is OK
        return user
    except DatabaseError:
        # Last resort: stale cache
        return get_stale_cache(user_id)
```

### Key Metrics to Monitor

1. **Latency percentiles** - P50, P95, P99
2. **Memory usage** - Used vs maxmemory
3. **Evictions** - Keys evicted per second
4. **Replication lag** - Bytes behind master
5. **Connection count** - Active connections
6. **Command stats** - Per-command latency

```bash
# Redis INFO for monitoring
INFO memory
INFO stats
INFO replication
INFO commandstats
```

---

## Production Checklist

### Before Launch

- [ ] Kernel tuned (THP, overcommit, somaxconn)
- [ ] Persistence configured (AOF + RDB)
- [ ] Replication set up (at least 1 replica)
- [ ] Monitoring in place (latency, memory, evictions)
- [ ] Alerts configured (80% memory, high latency)
- [ ] Backup strategy tested
- [ ] File descriptor limits increased
- [ ] maxmemory-policy set appropriately
- [ ] Slowlog configured

### Ongoing

- [ ] Monitor slowlog daily
- [ ] Review memory usage weekly
- [ ] Test failover monthly
- [ ] Update Redis version quarterly
- [ ] Capacity planning quarterly

---

## Quick Reference

```bash
# Check Redis health
redis-cli INFO
redis-cli INFO memory
redis-cli SLOWLOG GET 10

# Monitor in real-time
redis-cli MONITOR  # Warning: affects performance

# Check latency
redis-cli --latency
redis-cli --latency-history

# Memory analysis
redis-cli MEMORY USAGE key
redis-cli MEMORY STATS

# Benchmark
redis-benchmark -t set,get,incr -n 100000 -c 50
```
