---
name: A2A Protocol Client
description: >
  Use this skill when the user wants to communicate with an external agent via A2A protocol,
  send a task or message to a remote agent at a URL, discover what a remote agent can do,
  check the status of an A2A task, or integrate with any agent that supports the Agent-to-Agent protocol.
  Triggers on: "talk to agent", "send to agent", "A2A", "agent URL", "remote agent", "agent card",
  "agent endpoint", "communicate with agent".
---

# A2A Protocol Client

The `a2a` CLI communicates with any A2A-compliant agent. All operations resolve agent aliases and auth
parameters via the settings file (see `references/settings-format.md`).

## Helper Script

All commands use the helper script at `${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py`:

```bash
# Resolve alias -> URL
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" resolve <alias-or-url>

# Get --svc-param flags for a URL (prints one flag per line)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" auth <url>

# Track a task in current session
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" session add <task-id> <url> --alias <alias> --message "<msg>"

# List all session tasks
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" session list

# Update a task's status
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" session update <task-id> <status>
```

## Building a CLI Invocation

Always resolve alias and auth before calling `a2a`:

```bash
URL=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" resolve "$ALIAS_OR_URL")
AUTH=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" auth "$URL")
# AUTH is zero or more "--svc-param key=value" lines — pass as positional args via eval or xargs
a2a <subcommand> "$URL" <args> $AUTH
```

## Core Operations

### Discover Agent Card
```bash
a2a discover <url> $AUTH
a2a discover <url> --extended $AUTH   # authenticated extended card
```

### Send Message (blocking by default)
```bash
# Blocking — waits for task to reach terminal state
a2a send <url> "your message" $AUTH

# Non-blocking — returns immediately with task ID
a2a send <url> "your message" --immediate $AUTH

# Streaming — only if agent card declares streaming support
a2a send <url> "your message" --stream $AUTH

# Continue an existing task
a2a send <url> "follow-up" --task <task-id> $AUTH

# With context grouping
a2a send <url> "message" --context <context-id> $AUTH
```

### Task Management
```bash
a2a get task <url> <task-id> $AUTH          # current state + artifacts
a2a list tasks <url> $AUTH                  # list tasks (paginated)
a2a cancel <url> <task-id> $AUTH            # cancel task
a2a subscribe <url> <task-id> $AUTH         # stream updates for existing task
```

## Execution Strategy

1. **Default**: blocking send — waits for completion, shows full response.
2. **Background** (`--background` flag in `/a2a:send`): use `--immediate`, track task ID, user polls via `/a2a:status`.
3. **Streaming**: avoid unless agent card explicitly declares `streaming: true` in capabilities.
4. **Long-running tasks**: after non-blocking send, use `a2a subscribe` internally to monitor until terminal state if the user requests live updates.

## Task Lifecycle

States: `submitted` → `working` → `input-required` | `auth-required` → `completed` | `failed` | `canceled` | `rejected`

Terminal states: `completed`, `failed`, `canceled`, `rejected`

## Output Handling

- Blocking send returns the final Task with artifacts inline.
- Non-blocking returns a Task with `working` status — use task ID to poll.
- Artifacts in Task responses contain Parts: text, file references, or structured data.
- Present text parts directly; for file parts, show the file URI or download suggestion.

See `references/settings-format.md` for settings file format.
See `references/cli-reference.md` for full CLI flag reference.
