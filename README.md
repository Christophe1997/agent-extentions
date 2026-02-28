# OpenClaw Skills

A collection of Claude Code plugins for content creation and AI development.

## Plugins

| Plugin | Description |
|--------|-------------|
| **writing-hugo-blog** | Create Hugo blog posts in Chinese with proper front matter, formatting, and AI content labeling |
| **agent-design** | Guidelines for designing tools and action spaces for AI agents |

## Installation

### Add Marketplace

```bash
/plugin marketplace add <your-github-username>/skills
```

### Install Plugins

```bash
# Install writing-hugo-blog
/plugin install writing-hugo-blog@openclaw-skills

# Install agent-design
/plugin install agent-design@openclaw-skills
```

## Usage

After installation, skills are automatically activated based on context:

- **writing-hugo-blog**: Activates when creating blog content or working with Hugo
- **agent-design**: Activates when designing agent tools or discussing AI architecture

## License

MIT License - see [LICENSE](LICENSE) for details.
