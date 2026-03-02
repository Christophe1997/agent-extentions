---
name: Redis Coordination Patterns
description: Use when the user asks about distributed locking, mutex, redlock, rate limiting, throttling, API limits, cross-shard consistency, multi-key transactions, or coordination between services with Redis. Triggers on queries like "how to implement a lock", "distributed mutex", "rate limiter", "throttle requests".
version: 1.0.0
---

# Redis Coordination Patterns

## ⚡ Code Example Guidelines

When showing code examples:
1. **Detect the project's programming language** first (check package.json, go.mod, requirements.txt, pom.xml, etc.)
2. **Generate code in the detected language** using the appropriate Redis client
3. **If no language detected**, use pseudocode with Redis commands as shown below

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

### Redis Commands
```bash
SET lock:{name} {identifier} NX PX 10000   # Acquire lock (10s expiry)
GET lock:{name}                            # Check lock owner
DEL lock:{name}                            # Release lock (use Lua for safety)
```

### Lua Script for Safe Release
```lua
-- Only delete if we own the lock
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
```

### Pseudocode
```
function acquire_lock(lock_name, timeout_ms=10000):
    identifier = generate_uuid()
    lock_key = "lock:" + lock_name

    # Atomic set-if-not-exists with expiration
    acquired = REDIS.SET(lock_key, identifier, NX=True, PX=timeout_ms)

    IF acquired:
        RETURN identifier
    RETURN NULL

function release_lock(lock_name, identifier):
    lock_key = "lock:" + lock_name

    # Use Lua script for atomic check-and-delete
    RETURN REDIS.EVAL(release_script, 1, lock_key, identifier)

# Usage
function with_lock(lock_name, timeout_ms, fn):
    lock_id = acquire_lock(lock_name, timeout_ms)
    IF NOT lock_id:
        RAISE "Could not acquire lock"

    TRY:
        RETURN fn()
    FINALLY:
        release_lock(lock_name, lock_id)
```

**Important:** Always use a unique identifier to prevent releasing another process's lock.

---

## Pattern 2: Redlock Algorithm

**When to use:** When fault tolerance is critical and you need to tolerate node failures.

**How it works:** Acquire locks on a majority (N/2+1) of N independent Redis instances.

### Redis Commands (on each instance)
```bash
SET lock:{name} {identifier} NX PX {ttl_ms}
```

### Pseudocode
```
class Redlock:
    function __init__(redis_clients, lock_name, ttl_ms):
        self.clients = redis_clients
        self.lock_name = lock_name
        self.ttl_ms = ttl_ms
        self.quorum = length(redis_clients) / 2 + 1

    function acquire():
        identifier = generate_uuid()
        start_time = current_time()

        acquired = 0
        FOR client IN self.clients:
            TRY:
                IF client.SET("lock:" + self.lock_name, identifier, NX=True, PX=self.ttl_ms):
                    acquired += 1
            CATCH:
                PASS

        # Check if we got quorum and time remains
        elapsed = (current_time() - start_time) * 1000
        IF acquired >= self.quorum AND elapsed < self.ttl_ms:
            self.identifier = identifier
            RETURN TRUE

        # Failed - release all
        self._release_all(identifier)
        RETURN FALSE

    function _release_all(identifier):
        FOR client IN self.clients:
            TRY:
                release_lock_on_client(client, self.lock_name, identifier)
            CATCH:
                PASS
```

**Pros:** Tolerates node failures
**Cons:** Higher latency, more complex

---

## Pattern 3: Rate Limiting

**When to use:** Limit API requests, prevent abuse, implement quotas.

### Option A: Fixed Window

### Redis Commands
```bash
INCR ratelimit:{key}
EXPIRE ratelimit:{key} {window_seconds}
```

### Pseudocode
```
function fixed_window_rate_limit(key, limit, window_seconds):
    current = REDIS.INCR(key)

    IF current == 1:
        REDIS.EXPIRE(key, window_seconds)

    RETURN current <= limit
```

**Issue:** Allows burst at window boundaries (2x limit possible).

### Option B: Sliding Window Log

### Redis Commands
```bash
ZREMRANGEBYSCORE {key} 0 {old_timestamp}
ZADD {key} {timestamp} {uuid}
ZCARD {key}
EXPIRE {key} {window_seconds}
```

### Pseudocode
```
function sliding_window_rate_limit(key, limit, window_seconds):
    now = current_timestamp()
    window_start = now - window_seconds

    # Pipeline for atomicity
    REDIS.PIPELINE():
        ZREMRANGEBYSCORE(key, 0, window_start)
        ZADD(key, now, generate_uuid())
        count = ZCARD(key)
        EXPIRE(key, window_seconds + 1)

    RETURN count <= limit
```

**Pros:** Accurate, no boundary issues
**Cons:** Higher memory usage

### Option C: Token Bucket

### Redis Commands
```bash
HMGET bucket:{key} tokens last_refill
HMSET bucket:{key} tokens {n} last_refill {timestamp}
EXPIRE bucket:{key} 3600
```

### Lua Script (Recommended)
```lua
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local bucket = redis.call("HMGET", key, "tokens", "last_refill")
local tokens = tonumber(bucket[1]) or capacity
local last_refill = tonumber(bucket[2]) or now

-- Refill tokens based on elapsed time
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
```

**Pros:** Smooth traffic, allows bursts up to capacity
**Cons:** More complex

---

## Pattern 4: Hash Tag Co-location

**When to use:** When you need atomic multi-key operations in Redis Cluster.

**How it works:** Force related keys to the same slot using hash tags `{tag}`.

### Key Naming
```bash
# Without hash tag - different slots, can't use transactions
user:123        # Slot 1
session:123     # Slot 2 (different node!)

# With hash tag - same slot
user:{123}      # Same slot
session:{123}   # Same slot (guaranteed)
```

### Pseudocode
```
# Now you can use transactions
REDIS.PIPELINE():
    GET("user:{123}")
    GET("session:{123}")

# Or Lua scripts
REDIS.EVAL(script, 2, "user:{123}", "session:{123}", ...)
```

**Key concept:** Only the part inside `{}` is used for hash calculation.

---

## Pattern 5: Cross-Shard Consistency

**When to use:** When atomic multi-key operations aren't possible (different shards).

**How it works:** Use transaction stamps, version tokens, and commit markers.

### Pseudocode
```
function write_with_consistency(keys_values):
    tx_id = generate_uuid()
    timestamp = current_time()

    # Phase 1: Write with transaction stamp
    FOR key, value IN keys_values:
        REDIS.HSET("tx:" + tx_id, key, {
            "value": value,
            "timestamp": timestamp,
            "status": "pending"
        })

    # Phase 2: Commit each key
    committed = []
    FOR key, value IN keys_values:
        TRY:
            REDIS.SET(key, value)
            REDIS.HSET("tx:" + tx_id, key + ":status", "committed")
            committed.append(key)
        CATCH:
            BREAK

    # Phase 3: Verify or rollback
    IF length(committed) != length(keys_values):
        # Rollback committed writes
        FOR key IN committed:
            REDIS.DEL(key)
        REDIS.DEL("tx:" + tx_id)
        RETURN FALSE

    REDIS.DEL("tx:" + tx_id)
    RETURN TRUE
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
