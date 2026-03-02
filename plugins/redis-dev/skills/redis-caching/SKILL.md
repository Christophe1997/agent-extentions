---
name: Redis Caching Patterns
description: Use when the user asks about caching strategies, cache consistency, cache invalidation, cache stampede, write-through, write-behind, cache-aside, lazy loading, or client-side caching with Redis. Triggers on queries like "how to cache", "cache pattern", "prevent cache stampede", "Redis caching best practices".
version: 1.0.0
---

# Redis Caching Patterns

Solutions for common caching use cases using Redis.

## ⚡ Code Example Guidelines

When showing code examples:
1. **Detect the project's programming language** first (check package.json, go.mod, requirements.txt, pom.xml, etc.)
2. **Generate code in the detected language** using the appropriate Redis client:
   - JavaScript/TypeScript: `ioredis` or `redis` (node-redis)
   - Python: `redis-py`
   - Go: `go-redis`
   - Java: `jedis` or `lettuce`
   - C#: `StackExchange.Redis`
3. **If no language detected**, use pseudocode with Redis commands

---

| Use Case | Recommended Pattern |
|----------|---------------------|
| Read-heavy workload, stale data OK | Cache-Aside (Lazy Loading) |
| Strong cache-database consistency | Write-Through |
| Maximum write throughput | Write-Behind (Write-Back) |
| Frequently accessed keys, reduce latency | Client-Side Caching |
| Prevent thundering herd on cache miss | Cache Stampede Prevention |

---

## Pattern 1: Cache-Aside (Lazy Loading)

**When to use:** Read-heavy workloads where stale data is acceptable.

**How it works:** On cache miss, fetch from database and populate cache. On write, invalidate or update cache explicitly.

### Redis Commands
```bash
# Read flow
GET user:{id}           # Try cache first
# If nil:
SETEX user:{id} 3600 {value}  # Cache with 1 hour TTL

# Write flow
DEL user:{id}           # Invalidate cache
```

### Pseudocode
```
function get_user(user_id):
    key = "user:" + user_id

    # 1. Try cache first
    cached = REDIS.GET(key)
    IF cached:
        RETURN parse(cached)

    # 2. Cache miss - fetch from database
    user = DATABASE.query("SELECT * FROM users WHERE id = ?", user_id)

    # 3. Populate cache with TTL
    REDIS.SETEX(key, 3600, serialize(user))

    RETURN user

function update_user(user_id, data):
    # 1. Update database
    DATABASE.update("UPDATE users SET ... WHERE id = ?", user_id)

    # 2. Invalidate cache
    REDIS.DEL("user:" + user_id)
```

**Key commands:** `GET`, `SETEX`, `DEL`

**Pros:** Simple, only caches what's actually requested
**Cons:** Stale data possible, cache miss penalty

---

## Pattern 2: Write-Through Caching

**When to use:** When strong consistency between cache and database is required.

**How it works:** Write to both cache and database synchronously before returning success.

### Redis Commands
```bash
SET user:{id} {value}   # Update cache immediately
```

### Pseudocode
```
function update_user(user_id, data):
    # Use a transaction or distributed transaction
    BEGIN_TRANSACTION():

        # 1. Update database
        DATABASE.update("UPDATE users SET ... WHERE id = ?", user_id)

        # 2. Update cache immediately
        REDIS.SET("user:" + user_id, serialize(data))

    COMMIT_TRANSACTION()

    RETURN success
```

**Key commands:** `SET`, `GET`

**Pros:** Always fresh data, reads always hit cache
**Cons:** Higher write latency, more cache writes

---

## Pattern 3: Write-Behind (Write-Back)

**When to use:** When write throughput is critical and immediate durability can be traded.

**How it works:** Write only to Redis, asynchronously sync to database later.

### Redis Commands
```bash
SET user:{id} {value}           # Write to cache immediately
LPUSH sync:queue {task_data}    # Queue for async sync
BRPOP sync:queue 0              # Worker picks up task (blocking)
```

### Pseudocode
```
function update_user(user_id, data):
    key = "user:" + user_id

    # 1. Write to Redis immediately
    REDIS.SET(key, serialize(data))

    # 2. Queue for async DB sync
    task = {
        "type": "user_update",
        "id": user_id,
        "data": data,
        "timestamp": current_time()
    }
    REDIS.LPUSH("sync:queue", serialize(task))

    RETURN success

# Background worker (runs separately)
function sync_worker():
    LOOP:
        # Blocking pop from queue
        item = REDIS.BRPOP("sync:queue", timeout=1)
        IF item:
            data = parse(item)
            DATABASE.update(...)  # Sync to database
```

**Key commands:** `SET`, `LPUSH`, `BRPOP`

**Pros:** Maximum write throughput, reduced database load
**Cons:** Potential data loss if Redis fails before sync

---

## Pattern 4: Client-Side Caching

**When to use:** Frequently accessed keys where network round-trips are a bottleneck.

**How it works:** Cache values in application memory with Redis 6+ sending invalidation messages when data changes.

### Redis Commands
```bash
CLIENT TRACKING ON      # Enable invalidation messages
GET user:{id}           # Redis tracks this key
# When key changes, Redis sends: invalidate user:{id}
```

### Pseudocode
```
# Enable client tracking on connection
REDIS.EXECUTE("CLIENT", "TRACKING", "ON")

# Local in-memory cache
LOCAL_CACHE = {}

function get_user(user_id):
    key = "user:" + user_id

    # 1. Check local cache first
    IF key IN LOCAL_CACHE:
        RETURN LOCAL_CACHE[key]

    # 2. Fetch from Redis
    value = REDIS.GET(key)
    IF value:
        LOCAL_CACHE[key] = parse(value)

    RETURN LOCAL_CACHE[key]

# Handle invalidation messages (separate thread/connection)
function handle_invalidation():
    LOOP:
        message = REDIS.LISTEN()
        IF message.type == "invalidate":
            FOR key IN message.keys:
                LOCAL_CACHE.DELETE(key)
```

**Key commands:** `CLIENT TRACKING`, `GET`

**Pros:** Zero network latency for cached keys
**Cons:** Complexity, memory usage on client

---

## Pattern 5: Cache Stampede Prevention

**When to use:** When multiple clients might simultaneously request the same expensive-to-compute cache key.

**How it works:** Prevent multiple clients from regenerating an expired cache key using locking, probabilistic early refresh, or request coalescing.

### Option A: Locking

### Redis Commands
```bash
SET lock:{key} 1 NX EX 10   # Acquire lock (atomic, 10s expiry)
GET {key}                   # Check cache
SETEX {key} 3600 {value}    # Update cache
DEL lock:{key}              # Release lock
```

### Pseudocode
```
function get_with_lock(key, ttl, compute_fn):
    value = REDIS.GET(key)
    IF value:
        RETURN value

    # Try to acquire lock
    lock_key = "lock:" + key
    acquired = REDIS.SET(lock_key, "1", NX=True, EX=10)

    IF acquired:
        TRY:
            # Compute and cache
            value = compute_fn()
            REDIS.SETEX(key, ttl, value)
            RETURN value
        FINALLY:
            REDIS.DEL(lock_key)
    ELSE:
        # Wait and retry
        SLEEP(0.1)
        RETURN get_with_lock(key, ttl, compute_fn)
```

### Option B: Probabilistic Early Refresh

### Redis Commands
```bash
GET {key}
TTL {key}                   # Get remaining TTL
SETEX {key} 3600 {value}
```

### Pseudocode
```
function get_with_early_refresh(key, ttl, compute_fn):
    value = REDIS.GET(key)
    remaining_ttl = REDIS.TTL(key)

    IF value IS NIL:
        value = compute_fn()
        REDIS.SETEX(key, ttl, value)
        RETURN value

    # Probabilistic early refresh
    IF remaining_ttl < ttl * 0.2:  # Less than 20% TTL remaining
        IF RANDOM() < 0.1:  # 10% chance to refresh
            SPAWN_THREAD(refresh_cache, key, ttl, compute_fn)

    RETURN value
```

**Key commands:** `SET NX EX`, `GET`, `TTL`, `SETEX`

**Pros:** Prevents thundering herd, reduces latency spikes
**Cons:** Added complexity

---

## Anti-Patterns to Avoid

1. **No TTL on cache keys** → Memory exhaustion
2. **Caching large objects** → Network overhead, consider compression
3. **Cache everything** → Memory waste, only cache hot data
4. **Ignoring cache invalidation** → Stale data bugs

## Quick Reference

```
# Cache-Aside
GET key           # Check cache
SETEX key 3600 v  # Set with TTL (1 hour)
DEL key           # Invalidate

# Write-Through
SET key value     # Update cache on write

# Client-Side
CLIENT TRACKING ON
GET key           # Redis sends invalidations

# Stampede Prevention
SET lock:key 1 NX EX 10  # Acquire lock
```
