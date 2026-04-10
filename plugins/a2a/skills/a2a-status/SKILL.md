---
name: a2a:status
description: Shows all A2A tasks tracked in the current session, or fetches the full details of a specific task. Fetches live task state from the remote agent when a task ID is provided.
argument-hint: [<url-or-alias> <task-id>] [--watch]
allowed-tools: Bash
---

## No arguments — list all session tasks

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" session list
```

Render the output as a compact Markdown table with columns: Task ID, Status, Alias, Message.
Do not add prose outside the table.

## With `<url-or-alias> <task-id>` — fetch live task state

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

## With `--watch`

Use `a2a subscribe` to stream live updates until the task reaches a terminal state:

```bash
a2a subscribe "$URL" "$TASK_ID" "${AUTH_ARGS[@]}"
```

Relay updates as they arrive. Update session status after the stream closes.
