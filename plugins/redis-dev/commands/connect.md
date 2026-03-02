---
name: connect
description: Connect to a Redis instance and configure MCP integration for live queries
argument-hint: [--host <host>] [--port <port>] [--password <password>] [--db <db>]
allowed-tools:
  - Read
  - Write
  - Bash
  - AskUserQuestion
---

# Redis Connect Command

Configure connection to a Redis instance for live queries through MCP.

## Instructions

1. Parse the connection arguments provided by the user
2. Default values if not specified:
   - host: localhost
   - port: 6379
   - password: (empty)
   - db: 0

3. **Test the connection first** using redis-cli:
```bash
redis-cli -h <host> -p <port> -a <password> -n <db> PING
```

4. **Ask user for approval** before creating any files. Present this clearly:

```
📦 The following files will be created to save your Redis connection:

1. .claude/redis-dev.local.md  - Connection settings (may contain credentials)
2. .gitignore                   - Updated to exclude .claude/*.local.md

Do you want to proceed?
```

Use the AskUserQuestion tool to get explicit approval before proceeding.

5. After approval, check if `.gitignore` exists in the project root:
   - If it exists: Check if `.claude/*.local.md` is already ignored. If not, append the entry.
   - If it doesn't exist: Create a new `.gitignore` file with appropriate entries.

6. Create the MCP configuration file at `.claude/redis-dev.local.md`:

```yaml
---
redis_host: <host>
redis_port: <port>
redis_password: <password>
redis_db: <db>
---
# Redis Connection Settings
# This file is ignored by git to protect credentials.
# To reconnect, run: /redis-dev:connect
```

7. If successful, confirm connection and show server info:
```bash
redis-cli -h <host> -p <port> INFO server
```

## Example Usage

```
/redis-dev:connect
/redis-dev:connect --host 192.168.1.100 --port 6380
/redis-dev:connect --host redis.example.com --port 6379 --password secret --db 1
```

## Connection State

After connecting, the following commands will use this connection:
- `/redis-dev:query` - Execute Redis commands
- Any Redis-related questions will have access to live data

## Security Note

⚠️ The `.claude/redis-dev.local.md` file may contain sensitive credentials (passwords).
This file is automatically added to `.gitignore` to prevent accidental commits.

## Troubleshooting

If connection fails:
1. Check if Redis is running: `redis-cli ping`
2. Check firewall rules
3. Verify password if authentication is enabled
4. Check if the database number exists (0-15 by default)
