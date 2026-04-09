---
name: a2a-status
description: >
  Show all A2A tasks tracked in the current session, or get the full details of a specific task.
  User-invocable as /a2a:status. Fetches live task state from the remote agent.
argument-hint: '[<url-or-alias> <task-id>] [--watch]'
disable-model-invocation: true
allowed-tools: Bash(python3:*), Bash(a2a:*)
---

## No arguments — list all session tasks

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" session list
```

Render the output as a compact Markdown table with columns: Task ID, Status, Alias, Message.
Do not add prose outside the table.

## With `<url-or-alias> <task-id>` — fetch live task state

```bash
URL=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" resolve "$URL_OR_ALIAS")
AUTH=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" auth "$URL")
a2a get task "$URL" "$TASK_ID" $AUTH
```

Present the full output including status, artifacts, and history.

Then update session:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" session update "$TASK_ID" "$NEW_STATUS"
```

## With `--watch`

If `--watch` is present, use `a2a subscribe` to stream live updates:

```bash
a2a subscribe "$URL" "$TASK_ID" $AUTH
```

Relay updates as they arrive. Stop when the stream closes (task reached terminal state).
Update session status after the stream ends.
