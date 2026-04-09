# a2a

Claude Code plugin for the [Agent2Agent (A2A) protocol](https://a2a-protocol.org). Enables any Claude Code agent to communicate with any A2A-compliant agent by URL or saved alias.

## Features

### Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| `a2a-protocol` | Auto | Core A2A knowledge — activates when talking about remote agents, A2A URLs, or agent communication |
| `/a2a:discover` | User | Fetch and display an agent's capabilities (Agent Card) |
| `/a2a:send` | User | Send a message to an agent (blocking or background) |
| `/a2a:status` | User | Show session tasks or get live status of a specific task |
| `/a2a:cancel` | User | Cancel an active task |

## Examples

```bash
# Discover what an agent can do
/a2a:discover https://demo.a2a-protocol.org

# Send a message (blocking — waits for response)
/a2a:send https://demo.a2a-protocol.org "Summarize the latest news about AI"

# Send in background — returns task ID immediately
/a2a:send my-agent --background "Run a long analysis job"

# Check all session tasks
/a2a:status

# Get live status of a specific task
/a2a:status my-agent task_abc123

# Watch a task until completion
/a2a:status my-agent task_abc123 --watch

# Cancel a task
/a2a:cancel my-agent task_abc123
```

## Installation

**Requirements:** `a2a` CLI installed (`brew install a2a` or see [a2aproject/A2A](https://github.com/a2aproject/A2A)), Python 3.

```bash
/plugin install a2a@agent-extentions
```

## Usage

### Settings

Create `.claude/a2a.local.md` in your project root to save agent aliases and auth tokens:

```markdown
---
agents:
  my-agent: "https://my-agent.example.com/a2a"
  local: "http://localhost:8080"

auth:
  "https://my-agent.example.com":
    - "Authorization=Bearer <your-token>"
    - "X-Tenant-ID=my-org"
---
```

- **`agents`**: Maps short alias names to full agent URLs.
- **`auth`**: Maps URL prefixes to lists of `key=value` service params, passed as `--svc-param` to the CLI (repeatable).

This file is gitignored automatically.

### Sending Messages

By default, `/a2a:send` waits for the agent to complete the task before showing the result.

Use `--background` to fire-and-forget — the task ID is tracked in the session and you can check
progress with `/a2a:status`.

Use `--stream` only when you know the agent supports streaming (visible in the agent card).

### Task Continuation

Continue an existing task by passing `--task <task-id>`:

```bash
/a2a:send my-agent --task task_abc123 "Here is the additional context you asked for"
```

## License

MIT
