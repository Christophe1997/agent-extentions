---
name: a2a:send
description: Sends a message to an A2A-compliant agent at a URL or alias. Always runs in blocking mode. Pass --background to return immediately with a task ID instead. Resolves aliases, auth params, and timeout from settings. Tracks tasks in session.
argument-hint: <url-or-alias> [--background] [--stream] [--timeout <duration>] [--task <id>] [--context <id>] <message>
allowed-tools: Bash
---

Parse `$ARGUMENTS` into:
- `URL_OR_ALIAS`: first non-flag token
- `MESSAGE`: all remaining non-flag tokens joined as the message string
- `BACKGROUND`: true if `--background` present, false otherwise
- `STREAM`: true if `--stream` present
- `TIMEOUT`: value after `--timeout` if present (e.g. `60s`, `2m`)
- `TASK_ID`: value after `--task` if present
- `CONTEXT_ID`: value after `--context` if present

## Execution

Check that `a2a` is installed before proceeding:

```bash
if ! command -v a2a &>/dev/null; then
  echo "Error: 'a2a' CLI not found. Install with:"
  echo "  go install github.com/a2aproject/a2a-go/v2/cmd/a2a@main"
  exit 1
fi
```

```bash
URL=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" resolve "$URL_OR_ALIAS")
AUTH_ARGS=()
while IFS= read -r line; do
  AUTH_ARGS+=("$line")
done < <(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" auth "$URL")
SETTINGS_TIMEOUT=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" timeout "$URL")
TIMEOUT_VAL="${TIMEOUT:-${SETTINGS_TIMEOUT:-120s}}"
```

Inform the user of the effective timeout before sending:
> Timeout: `<TIMEOUT_VAL>` (from: `--timeout` flag / settings / default 120s)

Build flags array:
- If `BACKGROUND`: add `--immediate`
- If `STREAM`: add `--stream`
- If `TIMEOUT_VAL` non-empty: add `--timeout "$TIMEOUT_VAL"`
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

If the task fails with a timeout error, suggest retrying with a longer value (e.g. `--timeout 300s`) or increasing `timeout:` in `.claude/a2a.local.md`.

If the task status is `input-required`, prompt the user for the required input and offer to continue
the task by running send again with `--task <task-id>`.
