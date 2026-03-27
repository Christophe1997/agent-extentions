# Writing Hugo Blog

Create Chinese blog posts for Hugo static sites with proper front matter, content structure, and AI labeling.

## Features

### Skills

- **writing-hugo-blog** - Automatically activates when creating blog content. Follows structured workflow: explore config, check archetypes, generate draft, review, publish.

### Commands

| Command | Description |
|---------|-------------|
| `/writing-hugo-blog:draft <topic>` | Create a new draft blog post |
| `/writing-hugo-blog:review <path>` | Review existing post for style issues and apply fixes |

### Archetype Support

Respects Hugo's archetype lookup order:
1. `archetypes/posts.md` → 2. Theme archetype → 3. `archetypes/default.md` → 4. Theme default → 5. Built-in

## Examples

```bash
# Create a new blog post
/writing-hugo-blog:draft 如何使用Redis实现分布式锁

# Review existing post
/writing-hugo-blog:review content/posts/my-post.md
```

## Installation

```bash
/plugin install writing-hugo-blog@agent-extentions
```

## Usage

### Create a new blog post

```bash
/writing-hugo-blog:draft 如何使用Redis实现分布式锁
```

### Review existing post

```bash
/writing-hugo-blog:review content/posts/my-post.md
```

### Ask questions

```
"帮我写一篇关于Docker最佳实践的博客"
"Create a blog post about Redis clustering"
```

## License

MIT
