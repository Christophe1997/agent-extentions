---
name: Redis Commands Reference
description: Use when the user asks about Redis commands, command syntax, command options, or needs a quick reference for any Redis command. Triggers on queries like "how to use SET command", "Redis GET options", "ZADD syntax", "command reference".
version: 1.0.0
---

# Redis Commands Reference

Quick reference for Redis commands organized by category.

## Command Categories

| Category | Description | Key Commands |
|----------|-------------|--------------|
| [Strings](#strings) | Simple key-value pairs | SET, GET, INCR, APPEND |
| [Hashes](#hashes) | Field-value maps | HSET, HGET, HGETALL, HMSET |
| [Lists](#lists) | Ordered sequences | LPUSH, RPOP, LRANGE, LMOVE |
| [Sets](#sets) | Unordered unique items | SADD, SREM, SMEMBERS, SISMEMBER |
| [Sorted Sets](#sorted-sets) | Scored rankings | ZADD, ZRANGE, ZSCORE, ZINCRBY |
| [Streams](#streams) | Log data structures | XADD, XREAD, XREADGROUP |
| [Geo](#geo) | Geospatial indexes | GEOADD, GEOSEARCH, GEODIST |
| [Bitmaps](#bitmaps) | Bit-level operations | SETBIT, GETBIT, BITCOUNT |
| [HyperLogLog](#hyperloglog) | Cardinality estimation | PFADD, PFCOUNT |
| [Pub/Sub](#pubsub) | Messaging | PUBLISH, SUBSCRIBE |
| [Transactions](#transactions) | Atomic operations | MULTI, EXEC, WATCH |
| [Keys](#keys) | Key management | DEL, EXPIRE, TTL, TYPE |
| [Connection](#connection) | Client connections | AUTH, SELECT, PING |

---

## Strings

Basic key-value operations.

```
SET key value [EX seconds] [PX ms] [NX|XX]
GET key
DEL key [key ...]
EXISTS key [key ...]

# Expiration
SETEX key seconds value      # Set with expiry
TTL key                      # Get remaining TTL
PERSIST key                  # Remove expiry

# Numeric
INCR key                     # Increment by 1
INCRBY key increment         # Increment by N
DECR key                     # Decrement by 1
DECRBY key decrement         # Decrement by N

# String operations
APPEND key value             # Append to value
STRLEN key                   # Get length
GETRANGE key start end       # Get substring
SETRANGE key offset value    # Set substring
```

**Examples:**
```bash
SET user:1 "Alice" EX 3600   # Set with 1 hour expiry
SET lock:resource "uuid" NX PX 10000  # Distributed lock pattern
INCR page:views              # Atomic counter
```

---

## Hashes

Field-value maps within a key.

```
HSET key field value [field value ...]
HGET key field
HMGET key field [field ...]
HGETALL key
HDEL key field [field ...]
HEXISTS key field

# Numeric
HINCRBY key field increment
HINCRBYFLOAT key field increment

# Utility
HKEYS key                    # All fields
HVALS key                    # All values
HLEN key                     # Number of fields
HSETNX key field value       # Set if not exists
```

**Examples:**
```bash
HSET user:1 name "Alice" email "alice@example.com" age 30
HGET user:1 name              # "Alice"
HGETALL user:1                # All fields
HINCRBY user:1 age 1          # Birthday!
```

---

## Lists

Ordered sequences, good for queues.

```
# Push/Pop
LPUSH key element [element ...]
RPUSH key element [element ...]
LPOP key [count]
RPOP key [count]
LMOVE source destination LEFT|RIGHT LEFT|RIGHT

# Access
LRANGE key start stop
LINDEX key index
LLEN key

# Modify
LSET key index element
LREM key count element
LTRIM key start stop

# Blocking
BLPOP key [key ...] timeout
BRPOP key [key ...] timeout
```

**Examples:**
```bash
LPUSH queue:tasks task1 task2
RPOP queue:tasks              # FIFO: task1
LMOVE queue:pending queue:processing RIGHT LEFT  # Reliable queue
LRANGE mylist 0 -1            # All elements
```

---

## Sets

Unordered collections of unique strings.

```
SADD key member [member ...]
SREM key member [member ...]
SISMEMBER key member
SMEMBERS key
SCARD key                     # Count

# Set operations
SINTER key [key ...]          # Intersection
SUNION key [key ...]          # Union
SDIFF key [key ...]           # Difference
SINTERSTORE destination key [key ...]
SUNIONSTORE destination key [key ...]
SDIFFSTORE destination key [key ...]

# Random
SRANDMEMBER key [count]
SPOP key [count]
```

**Examples:**
```bash
SADD tags:article:1 redis database caching
SISMEMBER tags:article:1 redis  # 1 (true)
SINTER tags:article:1 tags:article:2  # Common tags
```

---

## Sorted Sets

Ordered by score, perfect for leaderboards.

```
ZADD key [NX|XX] [CH] [INCR] score member [score member ...]
ZREM key member [member ...]
ZSCORE key member
ZRANK key member              # Index (low to high)
ZREVRANK key member           # Index (high to low)
ZCARD key                     # Count

# Range queries
ZRANGE key start stop [BYSCORE|BYLEX] [REV] [WITHSCORES]
ZREVRANGE key start stop [WITHSCORES]
ZRANGEBYSCORE key min max [WITHSCORES] [LIMIT offset count]
ZREVRANGEBYSCORE key max min [WITHSCORES]

# Score operations
ZINCRBY key increment member
ZCOUNT key min max            # Count in score range

# Lexicographic (all scores equal)
ZRANGEBYLEX key min max [LIMIT offset count]
ZREVRANGEBYLEX key max min
```

**Examples:**
```bash
ZADD leaderboard 1500 player1 2000 player2 1800 player3
ZREVRANGE leaderboard 0 9 WITHSCORES  # Top 10
ZINCRBY leaderboard 100 player1       # Add 100 points
ZRANK leaderboard player1             # Get rank
```

---

## Streams

Log-style data structure for event streaming.

```
# Add entries
XADD key [NOMKSTREAM] [<MAXLEN|MINID threshold> [=|~] threshold] *|ID field value [field value ...]

# Read
XREAD [COUNT count] [BLOCK ms] STREAMS key [key ...] ID [ID ...]
XRANGE key start end [COUNT count]
XREVRANGE key end start [COUNT count]
XLEN key

# Consumer Groups
XGROUP CREATE key groupname ID|$ [MKSTREAM] [ENTRIESREAD entries_read]
XREADGROUP GROUP group consumer [COUNT count] [BLOCK ms] [NOACK] STREAMS key [key ...] ID [ID ...]
XACK key group ID [ID ...]
XGROUP DESTROY key groupname
XGROUP DELCONSUMER key groupname consumername

# Pending Entries List (PEL)
XPENDING key group [[IDLE min-idle-time] start end count [consumer]]
XCLAIM key group consumer min-idle-time ID [ID ...]
XAUTOCLAIM key group consumer min-idle-time start [COUNT count]

# Trimming
XTRIM key <MAXLEN|MINID> threshold [LIMIT threshold]
```

**Examples:**
```bash
XADD mystream * field1 value1
XREAD STREAMS mystream 0
XGROUP CREATE mystream mygroup $
XREADGROUP GROUP mygroup consumer1 STREAMS mystream >
XACK mystream mygroup 1526569495631-0
```

---

## Geo

Geospatial indexes.

```
GEOADD key [NX|XX] [CH] longitude latitude member [longitude latitude member ...]
GEOPOS key member [member ...]
GEODIST key member1 member2 [M|KM|FT|MI]
GEOHASH key member [member ...]
GEOSEARCH key [FROMMEMBER member|FROMLONLAT longitude latitude] [BYRADIUS radius M|KM|FT|MI|BYBOX width height M|KM|FT|MI] [ASC|DESC] [COUNT count [ANY]] [WITHCOORD] [WITHDIST] [WITHHASH]
GEOSEARCHSTORE destination source [FROMMEMBER member|FROMLONLAT longitude latitude] [BYRADIUS radius M|KM|FT|MI|BYBOX width height M|KM|FT|MI] [ASC|DESC] [COUNT count [ANY]] [WITHCOORD] [WITHDIST] [WITHHASH]
```

**Examples:**
```bash
GEOADD stores -122.4 37.8 "San Francisco"
GEOSEARCH stores FROMMEMBER "San Francisco" BYRADIUS 50 km WITHDIST
GEODIST stores "San Francisco" "Los Angeles" KM
```

---

## Bitmaps

Bit-level operations on string values.

```
SETBIT key offset value
GETBIT key offset
BITCOUNT key [start end [BYTE|BIT]]
BITPOS key bit [start [end [BYTE|BIT]]]
BITOP <AND|OR|XOR|NOT> destkey key [key ...]
BITFIELD key [GET type offset] [SET type offset value] [INCRBY type offset increment] [OVERFLOW WRAP|SAT|FAIL]
BITFIELD_RO key [GET type offset]
```

**Examples:**
```bash
SETBIT active:2024-01-15 100 1    # User 100 active
GETBIT active:2024-01-15 100      # Returns 1
BITCOUNT active:2024-01-15        # Count active users
BITOP AND retained day1 day2 day3 # Users active all 3 days
```

---

## HyperLogLog

Approximate cardinality counting.

```
PFADD key element [element ...]
PFCOUNT key [key ...]
PFMERGE destkey sourcekey [sourcekey ...]
```

**Examples:**
```bash
PFADD unique:visitors user1 user2 user1
PFCOUNT unique:visitors          # Returns ~2
PFMERGE unique:total unique:day1 unique:day2
```

---

## Pub/Sub

Publish-subscribe messaging.

```
PUBLISH channel message
SUBSCRIBE channel [channel ...]
UNSUBSCRIBE [channel [channel ...]]
PSUBSCRIBE pattern [pattern ...]
PUNSUBSCRIBE [pattern [pattern ...]]
PUBSUB CHANNELS [pattern]
PUBSUB NUMSUB [channel [channel ...]]
PUBSUB NUMPAT
```

**Examples:**
```bash
PUBLISH notifications "New message!"
SUBSCRIBE notifications
PSUBSCRIBE news:*  # Pattern subscribe
```

---

## Transactions

Atomic command execution.

```
MULTI                         # Start transaction
EXEC                          # Execute all queued commands
DISCARD                       # Cancel transaction
WATCH key [key ...]           # Watch for changes (optimistic locking)
UNWATCH                       # Unwatch all keys
```

**Examples:**
```bash
WATCH balance
current = GET balance
MULTI
SET balance (current - 100)
EXEC    # Fails if balance changed
```

---

## Keys

Key management commands.

```
DEL key [key ...]
UNLINK key [key ...]          # Async delete
EXISTS key [key ...]
EXPIRE key seconds [NX|XX|GT|LT]
EXPIREAT key unix-time-seconds
TTL key                       # Seconds until expiry
PTTL key                      # Milliseconds
PERSIST key                   # Remove expiry
TYPE key
RENAME key newkey
RENAMENX key newkey

# Scanning (use instead of KEYS in production)
SCAN cursor [MATCH pattern] [COUNT count] [TYPE type]
```

**Warning:** Avoid `KEYS *` in production - use `SCAN` instead.

---

## Connection

Client connection commands.

```
PING [message]
AUTH [username] password
SELECT index                  # Switch database
QUIT
ECHO message
CLIENT LIST
CLIENT ID
CLIENT SETNAME name
CLIENT TRACKING ON|OFF [NOLOOP]
```

---

## Quick Command Lookup by Task

| Task | Command |
|------|---------|
| Set a value | `SET key value` |
| Get a value | `GET key` |
| Delete a key | `DEL key` |
| Set with expiry | `SETEX key seconds value` |
| Check if exists | `EXISTS key` |
| Increment counter | `INCR key` |
| Add to set | `SADD key member` |
| Check set membership | `SISMEMBER key member` |
| Add to sorted set | `ZADD key score member` |
| Get top N | `ZREVRANGE key 0 N-1 WITHSCORES` |
| Push to queue | `LPUSH key value` |
| Pop from queue | `RPOP key` |
| Publish message | `PUBLISH channel message` |
| Add to stream | `XADD key * field value` |
| Set hash field | `HSET key field value` |
| Get hash field | `HGET key field` |

---

## Official Documentation

For complete command documentation, see: https://redis.io/commands/
