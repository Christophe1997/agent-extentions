---
name: Redis Coordination Patterns
description: Use when the user asks about distributed locking, mutex, redlock, rate limiting, throttling, API limits, cross-shard consistency, multi-key transactions, or coordination between services with Redis. Triggers on queries like "how to implement a lock", "distributed mutex", "rate limiter", "throttle requests".
version: 1.0.0
---

# Redis Coordination Patterns

Solutions for distributed coordination, locking, and rate limiting.

## Use Case → Pattern Mapping

| Use Case | Recommended Pattern |
|----------|---------------------|
| Mutual exclusion across processes | Distributed Locking (SET NX) |
| Fault-tolerant distributed locking | Redlock Algorithm |
| API rate limiting | Rate Limiting (various algorithms) |
| Multi-key operations in cluster | Hash Tag Co-location |
| Consistency across shards | Cross-Shard Consistency |

---

## Pattern 1: Distributed Locking

**When to use:** Mutual exclusion across distributed processes.

**How it works:** Use `SET key value NX PX timeout` for atomic lock acquisition with automatic expiration.

```python
import uuid

def acquire_lock(lock_name, timeout_ms=10000):
    """Acquire a distributed lock."""
    identifier = str(uuid.uuid4())
    lock_key = f"lock:{lock_name}"

    # Atomic set-if-not-exists with expiration
    acquired = redis.set(lock_key, identifier, nx=True, px=timeout_ms)

    if acquired:
        return identifier
    return None

def release_lock(lock_name, identifier):
    """Release lock only if we own it."""
    lock_key = f"lock:{lock_name}"

    # Lua script for atomic check-and-delete
    script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """

    return redis.eval(script, 1, lock_key, identifier)

# Usage
def with_lock(lock_name, timeout_ms, fn):
    lock_id = acquire_lock(lock_name, timeout_ms)
    if not lock_id:
        raise Exception("Could not acquire lock")

    try:
        return fn()
    finally:
        release_lock(lock_name, lock_id)
```

**Key commands:** `SET NX PX`, `GET`, `DEL` (via Lua)

**Important:** Always use a unique identifier to prevent releasing another process's lock.

---

## Pattern 2: Redlock Algorithm

**When to use:** When fault tolerance is critical and you need to tolerate node failures.

**How it works:** Acquire locks on a majority (N/2+1) of N independent Redis instances.

```python
import time

class Redlock:
    def __init__(self, redis_clients, lock_name, ttl_ms):
        self.clients = redis_clients
        self.lock_name = lock_name
        self.ttl_ms = ttl_ms
        self.quorum = len(redis_clients) // 2 + 1

    def acquire(self):
        identifier = str(uuid.uuid4())
        start_time = time.time()

        acquired = 0
        for client in self.clients:
            try:
                if client.set(f"lock:{self.lock_name}", identifier, nx=True, px=self.ttl_ms):
                    acquired += 1
            except:
                pass

        # Check if we got quorum and time remains
        elapsed = (time.time() - start_time) * 1000
        if acquired >= self.quorum and elapsed < self.ttl_ms:
            self.identifier = identifier
            return True

        # Failed - release all
        self._release_all(identifier)
        return False

    def _release_all(self, identifier):
        for client in self.clients:
            try:
                release_lock_on_client(client, self.lock_name, identifier)
            except:
                pass

    def release(self):
        if hasattr(self, 'identifier'):
            self._release_all(self.identifier)
```

**Key commands:** `SET NX PX` on multiple instances

**Pros:** Tolerates node failures
**Cons:** Higher latency, more complex

---

## Pattern 3: Rate Limiting

**When to use:** Limit API requests, prevent abuse, implement quotas.

### Option A: Fixed Window

```python
def fixed_window_rate_limit(key, limit, window_seconds):
    """Simple fixed window rate limiter."""
    current = redis.incr(key)

    if current == 1:
        redis.expire(key, window_seconds)

    return current <= limit

# Usage: 100 requests per minute
if not fixed_window_rate_limit("ratelimit:user:123", 100, 60):
    raise Exception("Rate limit exceeded")
```

**Issue:** Allows burst at window boundaries (2x limit possible).

### Option B: Sliding Window Log

```python
def sliding_window_rate_limit(key, limit, window_seconds):
    """Accurate sliding window using sorted set."""
    now = time.time()
    window_start = now - window_seconds

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zadd(key, {str(uuid.uuid4()): now})
    pipe.zcard(key)
    pipe.expire(key, window_seconds + 1)

    _, _, count, _ = pipe.execute()
    return count <= limit
```

**Pros:** Accurate, no boundary issues
**Cons:** Higher memory usage

### Option C: Token Bucket

```python
def token_bucket(key, capacity, refill_rate):
    """Token bucket for smooth rate limiting."""
    now = time.time()
    bucket_key = f"bucket:{key}"

    script = """
    local key = KEYS[1]
    local capacity = tonumber(ARGV[1])
    local refill_rate = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])
    local requested = tonumber(ARGV[4])

    local bucket = redis.call("HMGET", key, "tokens", "last_refill")
    local tokens = tonumber(bucket[1]) or capacity
    local last_refill = tonumber(bucket[2]) or now

    -- Refill tokens
    local elapsed = now - last_refill
    tokens = math.min(capacity, tokens + elapsed * refill_rate)

    if tokens >= requested then
        tokens = tokens - requested
        redis.call("HMSET", key, "tokens", tokens, "last_refill", now)
        redis.call("EXPIRE", key, 3600)
        return {1, tokens}
    else
        return {0, tokens}
    end
    """

    allowed, tokens = redis.eval(script, 1, bucket_key, capacity, refill_rate, now, 1)
    return bool(allowed)
```

**Pros:** Smooth traffic, allows bursts up to capacity
**Cons:** More complex

### Option D: Leaky Bucket

```python
def leaky_bucket(key, capacity, leak_rate):
    """Process requests at a constant rate."""
    now = time.time()
    bucket_key = f"leaky:{key}"

    script = """
    local key = KEYS[1]
    local capacity = tonumber(ARGV[1])
    local leak_rate = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])

    local bucket = redis.call("HMGET", key, "water", "last_leak")
    local water = tonumber(bucket[1]) or 0
    local last_leak = tonumber(bucket[2]) or now

    -- Leak water
    local elapsed = now - last_leak
    water = math.max(0, water - elapsed * leak_rate)

    if water < capacity then
        water = water + 1
        redis.call("HMSET", key, "water", water, "last_leak", now)
        redis.call("EXPIRE", key, 3600)
        return {1, water}
    else
        return {0, water}
    end
    """

    allowed, water = redis.eval(script, 1, bucket_key, capacity, leak_rate, now)
    return bool(allowed)
```

**Pros:** Constant output rate
**Cons:** No bursting allowed

---

## Pattern 4: Hash Tag Co-location

**When to use:** When you need atomic multi-key operations in Redis Cluster.

**How it works:** Force related keys to the same slot using hash tags `{tag}`.

```python
# Without hash tag - different slots, can't use transactions
user_key = "user:123"
session_key = "session:123"
# These may be on different nodes!

# With hash tag - same slot
user_key = "user:{123}"
session_key = "session:{123}"
# Guaranteed on same node

# Now you can use transactions
pipe = redis.pipeline()
pipe.get("user:{123}")
pipe.get("session:{123}")
user, session = pipe.execute()

# Or Lua scripts
redis.eval(script, 2, "user:{123}", "session:{123}", ...)
```

**Key concept:** Only the part inside `{}` is used for hash calculation.

---

## Pattern 5: Cross-Shard Consistency

**When to use:** When atomic multi-key operations aren't possible (different shards).

**How it works:** Use transaction stamps, version tokens, and commit markers.

```python
def write_with_consistency(keys_values):
    """Write to multiple shards with consistency detection."""
    tx_id = str(uuid.uuid4())
    timestamp = time.time()

    # Phase 1: Write with transaction stamp
    for key, value in keys_values:
        redis.hset(f"tx:{tx_id}", key, json.dumps({
            "value": value,
            "timestamp": timestamp,
            "status": "pending"
        }))

    # Phase 2: Commit each key
    committed = []
    for key, _ in keys_values:
        try:
            # Atomic write
            redis.set(key, ...)
            redis.hset(f"tx:{tx_id}", f"{key}:status", "committed")
            committed.append(key)
        except:
            break

    # Phase 3: Verify or rollback
    if len(committed) != len(keys_values):
        # Rollback committed writes
        for key in committed:
            redis.delete(key)
        redis.delete(f"tx:{tx_id}")
        return False

    redis.delete(f"tx:{tx_id}")
    return True
```

---

## Anti-Patterns to Avoid

1. **INCR without EXPIRE** → Keys live forever, memory leak
2. **Releasing locks without verification** → Another process's lock released
3. **No lock timeout** → Deadlock if process crashes
4. **Using KEYS command in production** → O(N) blocking, use SCAN

## Quick Reference

```
# Distributed Lock
SET lock:name identifier NX PX 10000

# Rate Limit (Fixed Window)
INCR ratelimit:key
EXPIRE ratelimit:key 60

# Rate Limit (Sliding Window)
ZREMRANGEBYSCORE key 0 <old_timestamp>
ZADD key <timestamp> <uuid>
ZCARD key

# Hash Tag
user:{123}:profile
user:{123}:settings
```
