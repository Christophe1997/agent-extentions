---
name: Redis Caching Patterns
description: Use when the user asks about caching strategies, cache consistency, cache invalidation, cache stampede, write-through, write-behind, cache-aside, lazy loading, or client-side caching with Redis. Triggers on queries like "how to cache", "cache pattern", "prevent cache stampede", "Redis caching best practices".
version: 1.0.0
---

# Redis Caching Patterns

Solutions for common caching use cases using Redis.

## Use Case → Pattern Mapping

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

```python
def get_user(user_id):
    # Try cache first
    cached = redis.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)

    # Cache miss - fetch from DB
    user = db.query("SELECT * FROM users WHERE id = ?", user_id)

    # Populate cache with TTL
    redis.setex(f"user:{user_id}", 3600, json.dumps(user))
    return user

def update_user(user_id, data):
    # Update database
    db.update("UPDATE users SET ... WHERE id = ?", user_id)

    # Invalidate cache
    redis.delete(f"user:{user_id}")
```

**Key commands:** `GET`, `SETEX`, `DEL`

**Pros:** Simple, only caches what's actually requested
**Cons:** Stale data possible, cache miss penalty

---

## Pattern 2: Write-Through Caching

**When to use:** When strong consistency between cache and database is required.

**How it works:** Write to both cache and database synchronously before returning success.

```python
def update_user(user_id, data):
    # Use a transaction or distributed transaction
    with transaction():
        # Update database
        db.update("UPDATE users SET ... WHERE id = ?", user_id)

        # Update cache immediately
        redis.set(f"user:{user_id}", json.dumps(data))

    return success
```

**Key commands:** `SET`, `GET`

**Pros:** Always fresh data, reads always hit cache
**Cons:** Higher write latency, more cache writes

---

## Pattern 3: Write-Behind (Write-Back)

**When to use:** When write throughput is critical and immediate durability can be traded.

**How it works:** Write only to Redis, asynchronously sync to database later.

```python
def update_user(user_id, data):
    # Write to Redis immediately
    redis.set(f"user:{user_id}", json.dumps(data))

    # Queue for async DB sync
    redis.lpush("sync:queue", json.dumps({
        "type": "user_update",
        "id": user_id,
        "data": data,
        "timestamp": time.time()
    }))

    return success

# Background worker
async def sync_worker():
    while True:
        item = redis.brpop("sync:queue", timeout=1)
        if item:
            data = json.loads(item[1])
            db.update(...)  # Sync to database
```

**Key commands:** `SET`, `LPUSH`, `BRPOP`

**Pros:** Maximum write throughput, reduced database load
**Cons:** Potential data loss if Redis fails before sync

---

## Pattern 4: Client-Side Caching

**When to use:** Frequently accessed keys where network round-trips are a bottleneck.

**How it works:** Cache values in application memory with Redis 6+ sending invalidation messages when data changes.

```python
# Enable client tracking
redis.execute_command("CLIENT", "TRACKING", "ON")

# Local cache
local_cache = {}

def get_user(user_id):
    key = f"user:{user_id}"

    # Check local cache first
    if key in local_cache:
        return local_cache[key]

    # Fetch from Redis
    value = redis.get(key)
    if value:
        local_cache[key] = json.loads(value)

    return local_cache.get(key)

# Handle invalidation messages (in separate thread)
def handle_invalidation():
    for message in redis.listen():
        if message["type"] == "invalidate":
            for key in message["keys"]:
                local_cache.pop(key, None)
```

**Key commands:** `CLIENT TRACKING`, `GET`

**Pros:** Zero network latency for cached keys
**Cons:** Complexity, memory usage on client

---

## Pattern 5: Cache Stampede Prevention

**When to use:** When multiple clients might simultaneously request the same expensive-to-compute cache key.

**How it works:** Prevent multiple clients from regenerating an expired cache key using locking, probabilistic early refresh, or request coalescing.

### Option A: Locking

```python
def get_with_lock(key, ttl, compute_fn):
    value = redis.get(key)
    if value:
        return value

    # Try to acquire lock
    lock_key = f"lock:{key}"
    if redis.set(lock_key, "1", nx=True, ex=10):
        try:
            # Compute and cache
            value = compute_fn()
            redis.setex(key, ttl, value)
            return value
        finally:
            redis.delete(lock_key)
    else:
        # Wait and retry
        time.sleep(0.1)
        return get_with_lock(key, ttl, compute_fn)
```

### Option B: Probabilistic Early Refresh

```python
def get_with_early_refresh(key, ttl, compute_fn):
    value, remaining_ttl = redis.get(key), redis.ttl(key)

    if value is None:
        value = compute_fn()
        redis.setex(key, ttl, value)
        return value

    # Probabilistic early refresh
    if remaining_ttl < ttl * 0.2:  # Less than 20% TTL remaining
        if random.random() < 0.1:  # 10% chance to refresh
            threading.Thread(target=refresh_cache, args=(key, ttl, compute_fn)).start()

    return value
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
