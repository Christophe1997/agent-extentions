# Agent Extensions

Agent extentions in Claude marketplace structure.

## Plugins

| Plugin | Description |
|--------|-------------|
| **writing-hugo-blog** | Create and review Hugo blog posts in Chinese with proper front matter, formatting, and AI content labeling |
| **agent-design** | Guidelines for designing tools and action spaces for AI agents |

## Installation

### Add Marketplace

```bash
/plugin marketplace add Christophe1997/agent-extentions
```

### Install Plugins

```bash
# Install writing-hugo-blog
/plugin install writing-hugo-blog@agent-extentions

# Install agent-design
/plugin install agent-design@agent-extentions
```

## Usage

### writing-hugo-blog

**Skill** - Automatically activates when creating blog content or working with Hugo.

**Workflow:**
1. Explore blog configuration
2. Recognize content formats and structure
3. Identify front matter requirements
4. Ask user about topic
5. Generate draft (`draft: true`)
6. Review writing quality
7. Publish (`draft: false`)

**Commands:**

| Command | Description |
|---------|-------------|
| `/writing-hugo-blog:draft <topic>` | Create a new draft blog post |
| `/writing-hugo-blog:review <path>` | Review existing post for style issues and apply fixes |

**Style Guide:** Follows [中文技术文档的写作规范](https://github.com/ruanyf/document-style-guide)

### agent-design

**Skill** - Automatically activates when designing agent tools or discussing AI architecture.

## License

MIT License - see [LICENSE](LICENSE) for details.
