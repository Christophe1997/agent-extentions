---
name: draft
description: "Create a draft Hugo blog post (draft: true) for later publishing. Follows the full workflow: explore blog config, check content structure, gather topic requirements, generate draft, and review writing quality."
argument-hint: topic or title for the draft post
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebFetch
  - WebSearch
  - AskUserQuestion
---

# Create Draft Blog Post

Create a draft Hugo blog post in Chinese following the structured workflow.

## Workflow

### Step 1: Explore Blog Configuration

1. Find the Hugo config file using Glob:
   - `config.yml`, `config.yaml`, `config.toml`, `hugo.toml`
   - Or `config/_default/` directory

2. Read the config to understand:
   - Site title and author
   - Theme and available front matter fields
   - Content organization preferences

### Step 2: Check Content Structure

1. Explore `content/posts/` directory
2. Identify year-based organization pattern
3. Check existing posts for front matter conventions

### Step 3: Determine Front Matter

Based on config and existing posts, use this standard format:

```yaml
---
title: "文章标题"
date: YYYY-MM-DDTHH:MM:SS+08:00
draft: true
author: "<AgentName>"
categories: ["Things I Learned"]
showToc: true
tags: ["tag1", "tag2", "AI generated"]
---
```

### Step 4: Ask User About Topic

Use AskUserQuestion to clarify:

- **Topic type**: Technical tutorial, project experience, research summary, or quick insight
- **Depth**: Quick summary (500-1500 words) or deep dive (2000-3000 words)
- **Source materials**: URLs or files to reference
- **Key points**: What should the article cover

### Step 5: Generate Draft

Create the article with this structure:

```markdown
## 参考资料

- [Source Title](url)

---

## Main Heading

Content...

### Subheading

More content...

---

*本文包含AI生成内容*
```

**Key requirements:**
- Reference Sources section FIRST (after front matter)
- Main content with clear headings
- AI disclaimer LAST
- Set `draft: true`
- Save to `content/posts/YYYY/filename.md`

### Step 6: Review Writing Quality

Before finalizing, verify:

**Writing Style:**
- [ ] Professional yet conversational tone
- [ ] First-person for personal insights
- [ ] Technical concepts explained simply
- [ ] Examples and practical applications included
- [ ] Length matches article type

**Fact Verification:**
- [ ] All facts have sources provided by user
- [ ] Unsourced claims are removed or qualified

### Step 7: Publish Article

After review, ask user if they want to publish:

1. Use AskUserQuestion:
   ```yaml
   question: "Review complete. Would you like to publish this article now?"
   header: "Publish"
   options:
     - label: "Yes, publish"
       description: "Set draft: false, article will be publicly visible"
     - label: "Keep as draft"
       description: "Keep draft: true for further editing"
   ```

2. If user chooses "Yes, publish":
   - Use Edit tool to change `draft: true` to `draft: false`
   - Confirm the article is now published

3. If user chooses "Keep as draft":
   - No changes to front matter
   - Remind user they can publish later by changing draft to false

## Example Usage

```
/writing-hugo-blog:draft Docker 部署 Go 应用的最佳实践
```

## Tips

- The draft won't be publicly visible until `draft: true` is changed to `draft: false`
- Always include source URLs in the 参考资料 section
- Keep reading time under 5 minutes for most content
