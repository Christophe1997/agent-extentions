---
name: Redis Data Structures
description: Use when the user asks about efficient storage, memory optimization, unique counting, counting distinct items, leaderboards, rankings, geospatial queries, location-based features, bitmaps, bit operations, probabilistic data structures, HyperLogLog, Bloom filters with Redis. Triggers on queries like "how to count unique", "leaderboard", "nearby locations", "bitmap operations".
version: 1.0.0
---

# Redis Data Structure Patterns

## ⚡ Code Example Guidelines

When showing code examples:
1. **Detect the project's programming language** first (check package.json, go.mod, requirements.txt, pom.xml, etc.)
2. **Generate code in the detected language** using the appropriate Redis client
3. **If no language detected**, use pseudocode with Redis commands as shown below

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

### Redis Commands
```bash
PFADD unique:visitors user1 user2 user1   # Add items (duplicates ignored)
PFCOUNT unique:visitors                    # Get approximate count
PFMERGE unique:total unique:day1 unique:day2  # Merge multiple HLLs
```

### Pseudocode
```
# Add items to HyperLogLog
REDIS.PFADD("unique:visitors", "user1")
REDIS.PFADD("unique:visitors", "user2")
REDIS.PFADD("unique:visitors", "user1")  # Duplicate - ignored

# Get approximate unique count
count = REDIS.PFCOUNT("unique:visitors")

# Merge multiple HyperLogLogs
REDIS.PFMERGE("unique:total", "unique:day1", "unique:day2")
```

**Memory:** Always 12KB regardless of cardinality
**Error rate:** ~0.81% standard error

---

## Pattern 2: Bloom Filter (Membership Testing)

**When to use:** Test if an item might be in a set (no false negatives, possible false positives).

### Redis Commands (RedisBloom Module)
```bash
BF.ADD filter:emails user@example.com       # Add to filter
BF.EXISTS filter:emails user@example.com    # Check membership (1=maybe, 0=no)
BF.RESERVE filter:emails 0.01 1000000       # Create with 1% error, 1M items
```

### Pseudocode
```
# Using RedisBloom module (recommended)
REDIS.EXECUTE("BF.ADD", "filter:emails", "user@example.com")
REDIS.EXECUTE("BF.ADD", "filter:emails", "another@example.com")

# Check membership
exists = REDIS.EXECUTE("BF.EXISTS", "filter:emails", "user@example.com")
# Returns 1 = probably exists, 0 = definitely does not exist

# Without RedisBloom: use SET for exact membership (more memory)
REDIS.SADD("set:emails", "user@example.com")
exists = REDIS.SISMEMBER("set:emails", "user@example.com")
```

---

## Pattern 3: Leaderboards with Sorted Sets

**When to use:** Real-time rankings with O(log N) score updates and rank lookups.

### Redis Commands
```bash
ZADD leaderboard:global 1500 player1 2000 player2 1800 player3
ZREVRANGE leaderboard:global 0 9 WITHSCORES    # Top 10
ZREVRANK leaderboard:global player1             # Get rank
ZSCORE leaderboard:global player1               # Get score
ZINCRBY leaderboard:global 100 player1          # Add 100 points
```

### Pseudocode
```
# Add/update scores
REDIS.ZADD("leaderboard:global", {
    "player1": 1500,
    "player2": 2000,
    "player3": 1800
})

# Get top 10 players
top10 = REDIS.ZREVRANGE("leaderboard:global", 0, 9, WITHSCORES=TRUE)

# Get a player's rank (0-indexed)
rank = REDIS.ZREVRANK("leaderboard:global", "player1")

# Get players around a specific player
player_rank = REDIS.ZREVRANK("leaderboard:global", "player2")
nearby = REDIS.ZREVRANGE("leaderboard:global",
                          max(0, player_rank - 5),
                          player_rank + 5,
                          WITHSCORES=TRUE)

# Increment score atomically
REDIS.ZINCRBY("leaderboard:global", 100, "player1")
```

**Time complexity:** O(log N) for most operations

---

## Pattern 4: Geospatial Queries

**When to use:** Store locations and query by radius, distance, or bounding box.

### Redis Commands
```bash
GEOADD locations:stores -122.4194 37.7749 store_sf -118.2437 34.0522 store_la
GEOSEARCH locations:stores FROMLONLAT -122.4 37.8 BYRADIUS 50 km WITHDIST
GEODIST locations:stores store_sf store_la KM
GEOPOS locations:stores store_sf
```

### Pseudocode
```
# Add locations (longitude, latitude)
REDIS.GEOADD("locations:stores",
    -122.4194, 37.7749, "store_sf",
    -118.2437, 34.0522, "store_la",
    -122.0322, 37.3688, "store_sj"
)

# Find stores within 50km radius
nearby = REDIS.GEOSEARCH("locations:stores",
    longitude=-122.4194,
    latitude=37.7749,
    radius=50,
    unit="km",
    WITHDIST=TRUE,
    WITHCOORD=TRUE
)

# Get distance between two locations
distance = REDIS.GEODIST("locations:stores", "store_sf", "store_la", unit="km")
```

**Note:** Built on Sorted Sets with geohash as score

---

## Pattern 5: Bitmaps

**When to use:** Millions of boolean flags with minimal memory (1 bit per flag).

### Redis Commands
```bash
SETBIT active:2024-01-15 {user_id} 1     # Mark user active
GETBIT active:2024-01-15 {user_id}       # Check if active
BITCOUNT active:2024-01-15               # Count active users
BITPOS active:2024-01-15 1               # Find first active
BITOP AND result day1 day2 day3          # Bitwise AND
```

### Pseudocode
```
# Set bits (user activity tracking)
REDIS.SETBIT("active:users:2024-01-15", user_id, 1)

# Check if user was active
active = REDIS.GETBIT("active:users:2024-01-15", user_id)

# Count active users
count = REDIS.BITCOUNT("active:users:2024-01-15")

# Bitwise operations across days
REDIS.BITOP("AND", "active:both", "active:day1", "active:day2")
REDIS.BITOP("OR", "active:either", "active:day1", "active:day2")

# Retention analysis: users active on all 7 days
REDIS.BITOP("AND", "retained:7day",
    "active:day1", "active:day2", "active:day3",
    "active:day4", "active:day5", "active:day6", "active:day7"
)
retained_count = REDIS.BITCOUNT("retained:7day")
```

**Memory:** 1 bit per position (125 million flags = ~15MB)

---

## Pattern 6: Memory Optimization with Hashes

**When to use:** Store many small objects efficiently.

### Redis Commands
```bash
HSET user:1 name Alice email alice@example.com age 30
HGET user:1 name
HGETALL user:1
```

### Pseudocode
```
# Instead of many string keys (more memory)
REDIS.SET("user:1:name", "Alice")
REDIS.SET("user:1:email", "alice@example.com")
REDIS.SET("user:1:age", "30")

# Use a hash (less memory for small objects)
REDIS.HSET("user:1", {
    "name": "Alice",
    "email": "alice@example.com",
    "age": "30"
})

# Access individual fields
name = REDIS.HGET("user:1", "name")
all_fields = REDIS.HGETALL("user:1")
```

**Why it saves memory:**
- Redis uses listpack encoding for small hashes (very compact)
- Single key overhead instead of multiple keys

---

## Pattern 7: Lexicographic Sorted Sets

**When to use:** Prefix queries, range scans, and autocomplete on string data.

### Redis Commands
```bash
ZADD autocomplete:words 0 apple 0 application 0 banana 0 app
ZRANGEBYLEX autocomplete:words "[app" "[app\xff"   # Prefix "app"
ZRANGEBYLEX autocomplete:words "[a" "[c"           # Range a-c
```

### Pseudocode
```
# Add items with same score (0) for lexicographic ordering
REDIS.ZADD("autocomplete:words", {
    "apple": 0,
    "application": 0,
    "banana": 0,
    "app": 0
})

# Find all words starting with "app"
# Use [app and [app\xff as range (inclusive)
words = REDIS.ZRANGEBYLEX("autocomplete:words", "[app", "[app\xff")

# Autocomplete with limit
words = REDIS.ZRANGEBYLEX("autocomplete:words", "[app", "[app\xff",
                          START=0, NUM=10)
```

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
