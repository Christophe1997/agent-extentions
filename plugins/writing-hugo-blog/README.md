# Writing Hugo Blog

Create Chinese blog posts for Hugo static sites with proper front matter, content structure, and AI labeling.

## Features

### Skill
Automatically activates when creating blog content or working with Hugo. Follows a structured workflow:
1. Explore blog configuration
2. Recognize content formats and structure
3. Identify front matter requirements
4. Ask user about topic
5. Generate draft (`draft: true`)
6. Review writing quality
7. Publish (`draft: false`)

### Commands

| Command | Description |
|---------|-------------|
| `/writing-hugo-blog:draft <topic>` | Create a new draft blog post |
| `/writing-hugo-blog:review <path>` | Review existing post for style issues and apply fixes |

## Installation

```bash
/plugin install writing-hugo-blog@agent-extentions
```

## Usage

### Create a new blog post
```
/writing-hugo-blog:draft 如何使用Redis实现分布式锁
```

### Review existing post
```
/writing-hugo-blog:review content/posts/my-post.md
```

### Ask questions
```
"帮我写一篇关于Docker最佳实践的博客"
"Create a blog post about Redis clustering"
```

## Style Guide

Follows [中文技术文档的写作规范](https://github.com/ruanyf/document-style-guide) for Chinese content.

## References

- [Hugo Documentation](https://gohugo.io/documentation/)
- [Chinese Writing Style Guide](./skills/writing-hugo-blog/references/chinese-writing-style.md)
