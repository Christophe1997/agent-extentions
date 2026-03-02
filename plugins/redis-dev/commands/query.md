---
name: query
description: Execute a Redis command against the connected instance and explain the results
argument-hint: <command> [args...]
allowed-tools:
  - Read
  - Bash
---

# Redis Query Command

Execute Redis commands against the connected Redis instance and provide explanations.

## Instructions

1. Read the connection configuration from `.claude/redis-dev.local.md` or use defaults:
   - Default host: localhost
   - Default port: 6379

2. Parse the user's Redis command and arguments

3. Execute the command using redis-cli:
```bash
redis-cli -h <host> -p <port> [-a <password>] [-n <db>] <command> [args...]
```

4. Explain the result to the user:
   - What the command does
   - What the output means
   - Any performance considerations
   - Related commands that might be useful

## Safety Guidelines

- **Destructive commands require confirmation**: DEL, FLUSHDB, FLUSHALL, etc.
- **Warn about expensive operations**: KEYS *, full scans
- **Suggest alternatives**: Use SCAN instead of KEYS

## Example Usage

```
/redis-dev:query GET user:123
/redis-dev:query HGETALL session:abc
/redis-dev:query ZREVRANGE leaderboard 0 9 WITHSCORES
/redis-dev:query TTL cache:important
/redis-dev:query INFO memory
```

## Output Format

For each query, provide:
1. **Command executed**: The exact redis-cli command
2. **Result**: The raw output
3. **Explanation**: What this means in context
4. **Tips**: Related patterns or optimizations

## Example Output

```
Command: GET user:123
Result: "Alice"

Explanation: Retrieved the string value for key "user:123".

Tips:
- Use HGETALL for objects with multiple fields
- Check TTL with TTL command if using expiration
- Consider using MGET for batch retrieval
```
