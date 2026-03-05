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

## Process

1. **Parse connection arguments**:
   - Default values if not specified:
     - host: localhost
     - port: 6379
     - password: (empty)
     - db: 0

2. **Test the connection**:
   ```bash
   redis-cli -h <host> -p <port> -a <password> -n <db> PING
   ```

3. **Ask user for approval**:

   Present clearly:
   ```
   📦 The following files will be created to save your Redis connection:

   1. .claude/redis-dev.local.md  - Connection settings (may contain credentials)
   2. .gitignore                   - Updated to exclude .claude/*.local.md

   Do you want to proceed?
   ```

   Call the AskUserQuestion tool:
   ```json
   {
     "questions": [{
       "question": "Create these files to save your Redis connection?",
       "header": "Confirm",
       "options": [
         {"label": "Yes, proceed", "description": "Create connection files"},
         {"label": "Cancel", "description": "Abort connection setup"}
       ]
     }]
   }
   ```

4. **Update .gitignore**:
   - If `.gitignore` exists: Check if `.claude/*.local.md` is already ignored. If not, append the entry.
   - If not exists: Create new `.gitignore` with appropriate entries.

5. **Create MCP configuration file** at `.claude/redis-dev.local.md`:

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

6. **Confirm connection**:
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

## Error Handling

If connection fails:
1. Check if Redis is running: `redis-cli ping`
2. Check firewall rules
3. Verify password if authentication is enabled
4. Check if the database number exists (0-15 by default)
