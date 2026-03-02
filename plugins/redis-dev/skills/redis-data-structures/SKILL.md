---
name: Redis Data Structures
description: Use when the user asks about efficient storage, memory optimization, unique counting, counting distinct items, leaderboards, rankings, geospatial queries, location-based features, bitmaps, bit operations, probabilistic data structures, HyperLogLog, Bloom filters with Redis. Triggers on queries like "how to count unique", "leaderboard", "nearby locations", "bitmap operations".
version: 1.0.0
---

# Redis Data Structure Patterns

Solutions for efficient data storage, counting, and querying use cases.

## Use Case → Pattern Mapping

| Use Case | Recommended Pattern |
|----------|---------------------|
| Count unique items approximately | HyperLogLog (12KB fixed) |
| Test set membership | Bloom Filter |
| Leaderboards and rankings | Sorted Sets |
| Location-based queries | Geospatial (GEO*) |
| Millions of boolean flags | Bitmaps |
| Efficient small object storage | Hashes with compact encoding |
| Prefix/range queries on strings | Lexicographic Sorted Sets |

---

## Pattern 1: HyperLogLog (Unique Counting)

**When to use:** Count unique items with ~0.81% error using only 12KB memory.

```python
# Add items to HyperLogLog
redis.pfadd("unique:visitors", "user1")
redis.pfadd("unique:visitors", "user2")
redis.pfadd("unique:visitors", "user1")  # Duplicate - ignored

# Get approximate unique count
count = redis.pfcount("unique:visitors")

# Merge multiple HyperLogLogs
redis.pfmerge("unique:total", "unique:day1", "unique:day2")
```

**Key commands:** `PFADD`, `PFCOUNT`, `PFMERGE`

**Memory:** Always 12KB regardless of cardinality
**Error rate:** ~0.81% standard error

**Use cases:** Unique visitors, unique searches, distinct count analytics

---

## Pattern 2: Bloom Filter (Membership Testing)

**When to use:** Test if an item might be in a set (no false negatives, possible false positives).

```python
# Using RedisBloom module (recommended)
redis.execute_command("BF.ADD", "filter:emails", "user@example.com")
redis.execute_command("BF.ADD", "filter:emails", "another@example.com")

# Check membership
exists = redis.execute_command("BF.EXISTS", "filter:emails", "user@example.com")
# Returns 1 = probably exists, 0 = definitely does not exist

# Create with custom error rate
redis.execute_command("BF.RESERVE", "filter:emails", "0.01", "1000000")
# 1% false positive rate, 1 million expected items
```

**Without RedisBloom module (using SET):**
```python
# Fallback: use SET for exact membership (more memory)
redis.sadd("set:emails", "user@example.com")
exists = redis.sismember("set:emails", "user@example.com")
```

**Use cases:** Email/filter checking, preventing cache penetration, fraud detection

---

## Pattern 3: Leaderboards with Sorted Sets

**When to use:** Real-time rankings with O(log N) score updates and rank lookups.

```python
# Add/update scores
redis.zadd("leaderboard:global", {"player1": 1500, "player2": 2000, "player3": 1800})

# Get top 10 players
top10 = redis.zrevrange("leaderboard:global", 0, 9, withscores=True)

# Get a player's rank (0-indexed)
rank = redis.zrevrank("leaderboard:global", "player1")

# Get players around a specific player (contextual leaderboard)
player_rank = redis.zrevrank("leaderboard:global", "player2")
nearby = redis.zrevrange("leaderboard:global",
                          max(0, player_rank - 5),
                          player_rank + 5,
                          withscores=True)

# Get score directly
score = redis.zscore("leaderboard:global", "player1")

# Increment score atomically
redis.zincrby("leaderboard:global", 100, "player1")
```

**Key commands:** `ZADD`, `ZREVRANGE`, `ZREVRANK`, `ZSCORE`, `ZINCRBY`, `ZRANGEBYSCORE`

**Time complexity:** O(log N) for most operations

---

## Pattern 4: Geospatial Queries

**When to use:** Store locations and query by radius, distance, or bounding box.

```python
# Add locations (longitude, latitude)
redis.geoadd("locations:stores",
             -122.4194, 37.7749, "store_sf",
             -118.2437, 34.0522, "store_la",
             -122.0322, 37.3688, "store_sj")

# Find stores within 50km radius
nearby = redis.geosearch("locations:stores",
                         longitude=-122.4194,
                         latitude=37.7749,
                         radius=50,
                         unit="km",
                         withdist=True,
                         withcoord=True)

# Get distance between two locations
distance = redis.geodist("locations:stores", "store_sf", "store_la", unit="km")

# Get coordinates of a location
coords = redis.geopos("locations:stores", "store_sf")
```

**Key commands:** `GEOADD`, `GEOSEARCH`, `GEODIST`, `GEOPOS`, `GEOHASH`

**Note:** Built on Sorted Sets with geohash as score

---

## Pattern 5: Bitmaps

**When to use:** Millions of boolean flags with minimal memory (1 bit per flag).

```python
# Set bits (user activity tracking)
redis.setbit("active:users:2024-01-15", user_id, 1)

# Check if user was active
active = redis.getbit("active:users:2024-01-15", user_id)

# Count active users
count = redis.bitcount("active:users:2024-01-15")

# Find first active user
first_active = redis.bitpos("active:users:2024-01-15", 1)

# Bitwise operations across days
redis.bitop("AND", "active:both", "active:day1", "active:day2")
redis.bitop("OR", "active:either", "active:day1", "active:day2")

# Retention analysis: users active on all days in range
redis.bitop("AND", "retained:7day",
            "active:day1", "active:day2", "active:day3",
            "active:day4", "active:day5", "active:day6", "active:day7")
retained_count = redis.bitcount("retained:7day")
```

**Key commands:** `SETBIT`, `GETBIT`, `BITCOUNT`, `BITPOS`, `BITOP`, `BITFIELD`

**Memory:** 1 bit per position (125 million flags = ~15MB)

**Use cases:** Daily active users, feature flags, attendance tracking, retention analysis

---

## Pattern 6: Memory Optimization with Hashes

**When to use:** Store many small objects efficiently.

```python
# Instead of many string keys (more memory)
redis.set("user:1:name", "Alice")
redis.set("user:1:email", "alice@example.com")
redis.set("user:1:age", "30")

# Use a hash (less memory for small objects)
redis.hset("user:1", mapping={
    "name": "Alice",
    "email": "alice@example.com",
    "age": "30"
})

# Access individual fields
name = redis.hget("user:1", "name")
all_fields = redis.hgetall("user:1")
```

**Why it saves memory:**
- Redis uses listpack encoding for small hashes (very compact)
- Single key overhead instead of multiple keys
- Configure thresholds in redis.conf: `hash-max-listpack-entries`, `hash-max-listpack-value`

---

## Pattern 7: Lexicographic Sorted Sets

**When to use:** Prefix queries, range scans, and autocomplete on string data.

```python
# Add items with same score (0) for lexicographic ordering
redis.zadd("autocomplete:words", {"apple": 0, "application": 0, "banana": 0, "app": 0})

# Find all words starting with "app"
# Use [app and [app\xff as range (inclusive)
words = redis.zrangebylex("autocomplete:words", "[app", "[app\xff")

# Find words in range
words = redis.zrangebylex("autocomplete:words", "[a", "[c")

# Autocomplete with limit
words = redis.zrangebylex("autocomplete:words", "[app", "[app\xff", start=0, num=10)
```

**Key commands:** `ZRANGEBYLEX`, `ZREVRANGEBYLEX`, `ZLEXCOUNT`

**Requirement:** All elements must have the same score (typically 0)

---

## Pattern 8: Probabilistic Data Structures Summary

| Structure | Memory | Use Case | Commands |
|-----------|--------|----------|----------|
| HyperLogLog | 12KB fixed | Approximate unique count | PFADD, PFCOUNT |
| Bloom Filter | Configurable | Membership test (maybe) | BF.ADD, BF.EXISTS* |
| Count-Min Sketch | Configurable | Frequency estimation | CMS.* |
| T-Digest | Configurable | Percentiles | TDIGEST.* |

*Requires RedisBloom module

---

## Quick Reference

```
# HyperLogLog
PFADD unique:visitors user1
PFCOUNT unique:visitors

# Leaderboard
ZADD leaderboard player1 1500
ZREVRANGE leaderboard 0 9 WITHSCORES
ZREVRANK leaderboard player1

# Geospatial
GEOADD stores -122.4 37.8 "store1"
GEOSEARCH stores FROMMEMBER "store1" BYRADIUS 50 km

# Bitmaps
SETBIT active:2024-01-15 123 1
BITCOUNT active:2024-01-15
BITOP AND result active:day1 active:day2

# Hashes
HSET user:1 name "Alice" email "alice@example.com"
HGET user:1 name

# Lexicographic
ZRANGEBYLEX words "[app" "[app\xff"
```
