# Agent Extensions

[![skills.sh](https://skills.sh/b/Christophe1997/agent-extentions)](https://skills.sh/Christophe1997/agent-extentions)

Agent extentions in Claude marketplace structure.

## Plugins

| Plugin | Works in | Description |
|--------|----------|-------------|
| [review-blog](./plugins/review-blog/README.md) | Any agent | Review Chinese blog posts for writing style, punctuation, and formatting issues |
| [agentic-doc](./plugins/agentic-doc/README.md) | Any agent | Documentation standards for agentic programming: AGENTS.md lifecycle & conventional commits |
| [show-me-the-session](./plugins/show-me-the-session/README.md) | Claude Code only | Export Claude Code sessions as solarized-light HTML pages |
| [permission-notification](./plugins/permission-notification/README.md) | Claude Code only | macOS notifications when Claude Code needs permission |
| [tdd](./plugins/tdd/README.md) | Any agent | Test-Driven Development guidance based on Kent Beck's Red/Green/Refactor workflow |
| [a2a](./plugins/a2a/README.md) | Any agent | A2A (Agent-to-Agent) protocol client — communicate with any A2A-compliant agent by URL or alias |
| [yapermission](./plugins/yapermission/README.md) | Claude Code only | Auto-approve or block tool calls via a TOML ruleset, with project-overrides-global config and decision logging |

`Claude Code only` plugins depend on Claude Code-specific surfaces (the `PreToolUse` / `PermissionRequest` / `Stop` hook events, the `permissionDecision` return schema, and the Claude Code session-transcript JSON format) and will not function inside Cursor, Copilot, or other agents.

## Installation

### Via Claude Code

Add the marketplace:

```bash
/plugin marketplace add Christophe1997/agent-extentions
```

Install plugins:

```bash
/plugin install review-blog@agent-extentions
/plugin install agentic-doc@agent-extentions
/plugin install show-me-the-session@agent-extentions
/plugin install permission-notification@agent-extentions
/plugin install tdd@agent-extentions
/plugin install a2a@agent-extentions
/plugin install yapermission@agent-extentions
```

### Via skills.sh

For agents other than Claude Code, install the cross-agent skills via the [skills.sh](https://skills.sh) CLI:

```bash
npx skills add Christophe1997/agent-extentions
```

## License

MIT License - see [LICENSE](LICENSE) for details.
