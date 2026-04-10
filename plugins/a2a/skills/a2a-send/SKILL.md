---
name: a2a:send
description: Sends a message to an A2A-compliant agent at a URL or alias. Supports blocking (default) and background (--background) modes. Resolves aliases and auth params from settings. Tracks tasks in session.
argument-hint: <url-or-alias> [--background] [--stream] [--task <id>] [--context <id>] <message>
allowed-tools: Bash
---

Parse `$ARGUMENTS` into:
- `URL_OR_ALIAS`: first non-flag token
- `MESSAGE`: all remaining non-flag tokens joined as the message string
- `BACKGROUND`: true if `--background` present
- `STREAM`: true if `--stream` present
- `TASK_ID`: value after `--task` if present
- `CONTEXT_ID`: value after `--context` if present

## Execution

```bash
URL=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" resolve "$URL_OR_ALIAS")
AUTH_ARGS=()
while IFS= read -r line; do
  AUTH_ARGS+=("$line")
done < <(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" auth "$URL")
```

Build flags array:
- If `BACKGROUND`: add `--immediate`
- If `STREAM`: add `--stream`
- If `TASK_ID`: add `--task "$TASK_ID"`
- If `CONTEXT_ID`: add `--context "$CONTEXT_ID"`

Run:
```bash
a2a send "$URL" "$MESSAGE" "${FLAGS[@]}" "${AUTH_ARGS[@]}"
```

## After the call

Extract the task ID from the output (look for `id:` or `"id":` field).

Always track the task:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" session add "$TASK_ID" "$URL" \
  --alias "$URL_OR_ALIAS" --message "$MESSAGE"
```

## Output

- **Blocking** (default): show the full response including artifacts. Parse and render text parts directly.
- **Background**: show the task ID and status. Inform the user they can check progress with the status skill.
- **Streaming**: relay output as it arrives.

If the task status is `input-required`, prompt the user for the required input and offer to continue
the task by running send again with `--task <task-id>`.
