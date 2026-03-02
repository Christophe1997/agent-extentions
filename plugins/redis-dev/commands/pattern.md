---
name: pattern
description: Look up Redis design patterns by use case or problem domain
argument-hint: <use-case>
allowed-tools:
  - Read
---

# Redis Pattern Lookup Command

Search and display Redis design patterns based on the user's use case.

## Instructions

1. Parse the use-case argument to understand what problem the user is trying to solve

2. Map the use case to relevant patterns using this guide:

| Use Case Keywords | Patterns to Show |
|-------------------|------------------|
| cache, caching, read-heavy | Cache-Aside, Write-Through, Write-Behind |
| lock, mutex, distributed | Distributed Locking, Redlock |
| queue, job, task | Reliable Queue, Delayed Queue, Streams |
| rate, limit, throttle | Rate Limiting (Fixed, Sliding, Token Bucket) |
| leaderboard, ranking, score | Sorted Sets for Leaderboards |
| unique, count, distinct | HyperLogLog, Bloom Filter |
| location, nearby, geo | Geospatial Patterns |
| bitmap, flag, boolean | Bitmap Patterns |
| session, user state | Session Management |
| stream, event, consumer | Redis Streams, Consumer Groups |
| scale, production, tuning | Production Patterns, Kernel Tuning |

3. Display the relevant patterns with:
   - When to use each pattern
   - Key commands involved
   - Brief code example
   - Pros and cons
   - Link to full skill documentation

## Example Usage

```
/redis-dev:pattern caching
/redis-dev:pattern queue
/redis-dev:pattern rate limiting
/redis-dev:pattern leaderboard
/redis-dev:pattern distributed lock
```

## Output Format

```markdown
## Patterns for: <use-case>

### Pattern 1: <Name>
**When to use:** <description>
**Key commands:** CMD1, CMD2, CMD3

```python
# Brief example
```

**Pros:** ...
**Cons:** ...

---
See full documentation: redis-<category> skill
```

## Pattern Matching

Be flexible with user input:
- "how do I rate limit" → Rate Limiting patterns
- "message queue" → Queue patterns
- "count unique users" → HyperLogLog
- "find nearby stores" → Geospatial
