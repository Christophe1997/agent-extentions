---
name: a2a:protocol
description: This skill provides the foundational A2A protocol knowledge Claude needs whenever a user wants to communicate with an A2A-compliant agent, call a remote agent by URL or alias, understand how agent cards work, integrate an agent-to-agent connection, construct an `a2a` CLI command, list or poll task status, cancel a running task, or subscribe to task updates. Relevant when the user mentions "A2A protocol", "agent card", "remote agent", "agent endpoint", "agent-to-agent", "a2a CLI", "use an agent", "call an agent", "ping an agent", or needs to understand task lifecycle states.
---

# A2A Protocol Client

The `a2a` CLI communicates with any A2A-compliant agent. All operations resolve agent aliases and
auth parameters via the settings file (see `references/settings-format.md`).

## Process

This is reference knowledge for any A2A operation. Apply it in this order, drilling into the
detailed sections below for each step:

1. **Check prerequisites**: Verify the `a2a` binary is installed and, on first use, prefer the
   onboarding flow over raw CLI calls. See [Prerequisites](#prerequisites).
2. **Build the CLI invocation**: Resolve the alias to a URL and load auth args via the helper
   script before calling `a2a`, using an array to handle auth values that may contain spaces.
   See [Helper Script](#helper-script) and [Building a CLI Invocation](#building-a-cli-invocation).
3. **Pick an execution strategy**: Default to a blocking send; use `--immediate` for background
   tasks, and reach for `--stream` only when the agent card declares streaming support.
   See [Execution Strategy](#execution-strategy) and [Core Operations](#core-operations).
4. **Track the task lifecycle**: Map the returned status onto the lifecycle states, distinguishing
   terminal states from intermediate states that can be resumed via `send --task`.
   See [Task Lifecycle](#task-lifecycle).
5. **Handle the output**: Read artifacts and Parts from the Task response, present text parts
   directly, surface file parts as URIs, and use `-o json` for structured parsing.
   See [Output Handling](#output-handling).

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

## Example Usage

This is a knowledge skill — it is not invoked directly. It loads automatically when a user talks
about A2A agents, or it is loaded by the `a2a` command skills (`a2a-onboard`, `a2a-send`,
`a2a-status`, `a2a-cancel`) for foundational protocol context.

Model-invocation triggers (user prose):

```
Call the remote agent at https://demo.a2a-protocol.org and summarize the latest news about AI
Ping my-agent and tell me if it's up
What states can an A2A task be in?
How do I construct an a2a CLI command to cancel a running task?
```

Loaded by another a2a skill for protocol knowledge:

```
Use Skill tool with skill="a2a:protocol"
```

The slash commands that build on this knowledge:

```bash
/a2a:onboard https://demo.a2a-protocol.org
/a2a:send https://demo.a2a-protocol.org "Summarize the latest news about AI"
/a2a:send my-agent --background "Run a long analysis job"
/a2a:status my-agent task_abc123 --watch
/a2a:cancel my-agent task_abc123
```
