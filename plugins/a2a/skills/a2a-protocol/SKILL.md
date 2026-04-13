---
name: a2a-protocol
description: This skill provides the foundational A2A protocol knowledge Claude needs whenever a user wants to communicate with an A2A-compliant agent, call a remote agent by URL or alias, understand how agent cards work, integrate an agent-to-agent connection, construct an `a2a` CLI command, list or poll task status, cancel a running task, or subscribe to task updates. Relevant when the user mentions "A2A protocol", "agent card", "remote agent", "agent endpoint", "agent-to-agent", "a2a CLI", "use an agent", "call an agent", "ping an agent", or needs to understand task lifecycle states.
---

# A2A Protocol Client

The `a2a` CLI communicates with any A2A-compliant agent. All operations resolve agent aliases and
auth parameters via the settings file (see `references/settings-format.md`).

## Prerequisites

**Check binary before any operation:**

```bash
command -v a2a &>/dev/null || {
  echo "Error: 'a2a' CLI not found. Install with:"
  echo "  go install github.com/a2aproject/a2a-go/v2/cmd/a2a@latest"
  exit 1
}
```

If the binary is missing, show the install command and stop. Do not attempt any `a2a` subcommands.

**First-time setup:** If no `~/.claude/a2a.local.md` exists, suggest running `/a2a:onboard <url>`
instead of constructing raw CLI calls — it handles binary check, discovery, alias saving, and auth
configuration in one flow.

## Helper Script

All operations use the helper script at `${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py`:

```bash
# Resolve alias -> URL (passes raw URLs through unchanged)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" resolve <alias-or-url>

# Get auth args for a URL (one token per line, safe for values with spaces)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" auth <url>

# Track a task in current session
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" session add <task-id> <url> --alias <alias> --message "<msg>"

# List all session tasks
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" session list

# Update a task's status (exits non-zero if task ID not found)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" session update <task-id> <status>
```

## Building a CLI Invocation

Always resolve alias and auth before calling `a2a`. Use an array to safely handle auth values
that may contain spaces:

```bash
URL=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" resolve "$ALIAS_OR_URL")
AUTH_ARGS=()
while IFS= read -r line; do
  AUTH_ARGS+=("$line")
done < <(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" auth "$URL")
a2a <subcommand> "$URL" <args> "${AUTH_ARGS[@]}"
```

If the `a2a` binary is not installed, direct the user to install it:
```bash
go install github.com/a2aproject/a2a-go/v2/cmd/a2a@latest
```

## Core Operations

### Discover Agent Card
```bash
a2a discover "$URL" "${AUTH_ARGS[@]}"
a2a discover "$URL" --extended "${AUTH_ARGS[@]}"   # authenticated extended card
```
`discover` is the canonical subcommand; `a2a get card` is an alias for it.

### Send Message
```bash
# Blocking — waits for task to reach terminal state (default)
a2a send "$URL" "your message" "${AUTH_ARGS[@]}"

# Non-blocking — returns immediately with task ID
a2a send "$URL" "your message" --immediate "${AUTH_ARGS[@]}"

# Streaming — only if agent card declares streaming support
a2a send "$URL" "your message" --stream "${AUTH_ARGS[@]}"

# Continue an existing task
a2a send "$URL" "follow-up" --task <task-id> "${AUTH_ARGS[@]}"

# With context grouping
a2a send "$URL" "message" --context <context-id> "${AUTH_ARGS[@]}"
```

### Task Management
```bash
a2a get task "$URL" <task-id> "${AUTH_ARGS[@]}"    # current state + artifacts (i.e. task status)
a2a list tasks "$URL" "${AUTH_ARGS[@]}"            # list tasks (paginated)
a2a cancel "$URL" <task-id> "${AUTH_ARGS[@]}"      # cancel task
a2a subscribe "$URL" <task-id> "${AUTH_ARGS[@]}"   # stream updates until terminal state
```

## Execution Strategy

1. **Default**: blocking send — waits for completion, shows full response.
2. **Background**: use `--immediate`, track task ID, user polls via the status skill.
3. **Streaming**: avoid unless agent card explicitly declares `streaming: true` in capabilities.
4. **Long-running tasks**: after non-blocking send, use `a2a subscribe` internally to monitor
   until terminal state if the user requests live updates.

## Task Lifecycle

```
submitted → working → ┬→ completed
                      ├→ failed
                      ├→ canceled
                      ├→ rejected
                      ├→ input-required  (agent needs more info from user)
                      └→ auth-required   (agent needs authentication)
```

Terminal states: `completed`, `failed`, `canceled`, `rejected`
Intermediate states: `input-required`, `auth-required` (can resume via send with `--task`)

## Output Handling

- Blocking send returns the final Task with artifacts inline.
- Non-blocking returns a Task with `working` status — use task ID to poll.
- Artifacts in Task responses contain Parts: text, file references, or structured data.
- Present text parts directly; for file parts, show the file URI or download suggestion.
- Use `-o json` to get structured JSON output for programmatic parsing.

See `references/settings-format.md` for settings file format.
See `references/cli-reference.md` for full CLI flag reference.
