# Agent Extensions

Agent extentions in Claude marketplace structure.

## Plugins

| Plugin | Description |
|--------|-------------|
| [review-blog](./plugins/review-blog/README.md) | Review Chinese blog posts for writing style, punctuation, and formatting issues |
| [agentic-doc](./plugins/agentic-doc/README.md) | Documentation standards for agentic programming: AGENTS.md lifecycle & conventional commits |
| [show-me-the-session](./plugins/show-me-the-session/README.md) | Export Claude Code sessions as solarized-light HTML pages |
| [permission-notification](./plugins/permission-notification/README.md) | macOS notifications when Claude Code needs permission |

## Installation

### Add Marketplace

```bash
/plugin marketplace add Christophe1997/agent-extentions
```

### Install Plugins

```bash
/plugin install review-blog@agent-extentions
/plugin install agentic-doc@agent-extentions
/plugin install show-me-the-session@agent-extentions
/plugin install permission-notification@agent-extentions
```

## License

MIT License - see [LICENSE](LICENSE) for details.
