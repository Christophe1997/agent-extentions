---
name: a2a-cancel
description: Cancels an active A2A task. Resolves aliases and auth params from settings, updates session tracking.
argument-hint: <url-or-alias> <task-id>
allowed-tools: Bash
---

## Process

1. **Parse `$ARGUMENTS`**:
   - First token: `URL_OR_ALIAS`
   - Second token: `TASK_ID`

   If either is missing, output:
   ```
   Usage: /a2a-cancel <url-or-alias> <task-id>
   ```

2. **Check that `a2a` is installed** before proceeding:

   ```bash
   if ! command -v a2a &>/dev/null; then
     echo "Error: 'a2a' CLI not found. Install with:"
     echo "  go install github.com/a2aproject/a2a-go/v2/cmd/a2a@latest"
     exit 1
   fi
   ```

3. **Resolve the URL and auth, then cancel the task**:

   ```bash
   URL=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" resolve "$URL_OR_ALIAS")
   AUTH_ARGS=()
   while IFS= read -r line; do
     AUTH_ARGS+=("$line")
   done < <(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" auth "$URL")
   a2a cancel "$URL" "$TASK_ID" "${AUTH_ARGS[@]}"
   ```

4. **Update session tracking** after cancellation:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" session update "$TASK_ID" "canceled"
   ```

5. **Report the result**: Show the updated task state returned by the CLI. If the task was
   already in a terminal state, report that cancellation was not needed.
