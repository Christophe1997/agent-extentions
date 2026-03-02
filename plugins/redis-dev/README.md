# Redis Dev Plugin

Comprehensive Redis design patterns, best practices, and command references for Claude Code. Includes MCP integration for live Redis queries.

## Features

### Skills (Use-Case Driven)

| Skill | Use Cases |
|-------|-----------|
| `redis-caching` | Caching strategies, cache consistency, stampede prevention |
| `redis-messaging` | Queues, reliable delivery, event streaming, pub/sub |
| `redis-coordination` | Distributed locking, rate limiting, cross-shard consistency |
| `redis-data-structures` | Efficient storage, unique counting, leaderboards, geospatial |
| `redis-commands` | Complete Redis command reference with examples |
| `redis-production` | Scaling, tuning, high availability patterns |

### Commands

| Command | Description |
|---------|-------------|
| `/redis-dev:connect` | Connect to a Redis instance (asks for approval before creating files) |
| `/redis-dev:query <command>` | Execute a Redis command and explain results |
| `/redis-dev:pattern <use-case>` | Look up patterns by use case |

### Agents

- `redis-code-reviewer` - Analyzes code for Redis anti-patterns and suggests improvements

### MCP Integration

Connect to live Redis instances for real-time queries and inspection.

## Installation

```bash
/plugin install redis-dev@agent-extentions
```

## MCP Configuration

Create a `.claude/redis-dev.local.md` file to configure your Redis connection:

```yaml
---
redis_host: localhost
redis_port: 6379
redis_password: ""
redis_db: 0
---
```

Or set environment variables:
```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

## Usage

### Ask about patterns

```
"How do I implement a rate limiter with Redis?"
"What's the best caching strategy for read-heavy workloads?"
"How do I build a reliable message queue with Redis?"
```

### Use commands

```
/redis-dev:connect --host localhost --port 6379
/redis-dev:query GET user:123
/redis-dev:pattern queue
```

### Code review

The `redis-code-reviewer` agent automatically analyzes code for:
- Key naming anti-patterns
- Missing TTL on cache keys
- Inefficient data structure choices
- Race conditions in distributed scenarios

## Code Examples

This plugin uses **pseudocode + Redis commands** for language-agnostic documentation. When you ask questions, it will:
1. Detect your project's programming language
2. Generate code examples in that language
3. Fall back to pseudocode if no language is detected

## Documentation Source

This plugin follows the [Redis llms.txt specification](https://redis.antirez.com/llms.txt).

## License

MIT
