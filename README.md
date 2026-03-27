# Agent Extensions

Agent extentions in Claude marketplace structure.

## Plugins

| Plugin | Description |
|--------|-------------|
| [writing-hugo-blog](./plugins/writing-hugo-blog/README.md) | Create and review Hugo blog posts in Chinese with proper front matter and AI content labeling |
| [llm-doc](./plugins/llm-doc/README.md) | Documentation standards for AI coding agents: AGENTS.md format and conventional commit messages |
| [show-me-the-session](./plugins/show-me-the-session/README.md) | Export Claude Code sessions as solarized-light HTML pages |
| [permission-notification](./plugins/permission-notification/README.md) | macOS notifications when Claude Code needs permission |

## Installation

### Add Marketplace

```bash
/plugin marketplace add Christophe1997/agent-extentions
```

### Install Plugins

```bash
/plugin install writing-hugo-blog@agent-extentions
/plugin install llm-doc@agent-extentions
/plugin install show-me-the-session@agent-extentions
/plugin install permission-notification@agent-extentions
```

## License

MIT License - see [LICENSE](LICENSE) for details.
