# Agent Extensions

Agent extentions in Claude marketplace structure.

## Plugins

| Plugin | Description |
|--------|-------------|
| [writing-hugo-blog](./plugins/writing-hugo-blog/README.md) | Create and review Hugo blog posts in Chinese with proper front matter and AI content labeling |
| [agent-design](./plugins/agent-design/README.md) | Guidelines for designing tools and action spaces for AI agents |
| [redis-dev](./plugins/redis-dev/README.md) | Redis design patterns, best practices, and command references with MCP integration |

## Installation

### Add Marketplace

```bash
/plugin marketplace add Christophe1997/agent-extentions
```

### Install Plugins

```bash
/plugin install writing-hugo-blog@agent-extentions
/plugin install agent-design@agent-extentions
/plugin install redis-dev@agent-extentions
```

## License

MIT License - see [LICENSE](LICENSE) for details.
