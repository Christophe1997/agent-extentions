---
name: a2a-cancel
description: >
  Cancel an active A2A task. User-invocable as /a2a:cancel.
  Resolves aliases and auth params from settings, updates session tracking.
argument-hint: '<url-or-alias> <task-id>'
disable-model-invocation: true
allowed-tools: Bash(python3:*), Bash(a2a:*)
---

Parse `$ARGUMENTS`:
- First token: `URL_OR_ALIAS`
- Second token: `TASK_ID`

If either is missing, output:
```
Usage: /a2a:cancel <url-or-alias> <task-id>
```

```bash
URL=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" resolve "$URL_OR_ALIAS")
AUTH=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" auth "$URL")
a2a cancel "$URL" "$TASK_ID" $AUTH
```

After cancellation, update session tracking:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" session update "$TASK_ID" "canceled"
```

Show the updated task state returned by the CLI. If the task was already in a terminal state,
report that cancellation was not needed.
