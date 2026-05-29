---
name: a2a:status
description: Shows all A2A tasks tracked in the current session, or fetches the full details of a specific task. Fetches live task state from the remote agent when a task ID is provided.
argument-hint: [<url-or-alias> <task-id>] [--watch]
allowed-tools: Bash
---

## Process

1. **Check prerequisites**: Confirm the `a2a` CLI is installed before proceeding.

   ```bash
   if ! command -v a2a &>/dev/null; then
     echo "Error: 'a2a' CLI not found. Install with:"
     echo "  go install github.com/a2aproject/a2a-go/v2/cmd/a2a@latest"
     exit 1
   fi
   ```

2. **Route by argument shape**: Inspect `$ARGUMENTS` and pick the matching mode below.
   - No tokens → list all session tasks (mode in step 3).
   - `<url-or-alias> <task-id>` → fetch live task state (mode in step 4).
   - `<url-or-alias> <task-id> --watch` → stream live updates (mode in step 5).

3. **List all session tasks** (no arguments):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" session list
   ```

   Render the output as a compact Markdown table with columns: Task ID, Status, Agent (show alias if available), Message, Commands (follow-up commands).
   Do not add prose outside the table.

4. **Fetch live task state** (with `<url-or-alias> <task-id>`):

   Parse `$ARGUMENTS`:
   - `URL_OR_ALIAS`: first token
   - `TASK_ID`: second token
   - `WATCH`: true if `--watch` present

   ```bash
   URL=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" resolve "$URL_OR_ALIAS")
   AUTH_ARGS=()
   while IFS= read -r line; do
     AUTH_ARGS+=("$line")
   done < <(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" auth "$URL")
   a2a get task "$URL" "$TASK_ID" "${AUTH_ARGS[@]}"
   ```

   Present the full output including status, artifacts, and history. Then update session:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" session update "$TASK_ID" "$NEW_STATUS"
   ```

5. **Stream live updates** (with `--watch`):

   Use `a2a subscribe` to stream live updates until the task reaches a terminal state:

   ```bash
   a2a subscribe "$URL" "$TASK_ID" "${AUTH_ARGS[@]}"
   ```

   Relay updates as they arrive. Update session status after the stream closes.

## Example Usage

```bash
# Check all session tasks
/a2a:status

# Get live status of a specific task
/a2a:status my-agent task_abc123

# Watch a task until completion
/a2a:status my-agent task_abc123 --watch
```
