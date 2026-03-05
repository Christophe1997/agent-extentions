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

## Process

1. **Explore blog configuration**:
   - Find the Hugo config file using Glob: `config.yml`, `config.yaml`, `config.toml`, `hugo.toml`, or `config/_default/`
   - Read the config to understand: site title, author, theme, front matter fields, content organization

2. **Check content structure**:
   - Explore `content/posts/` directory
   - Identify year-based organization pattern
   - Check existing posts for front matter conventions

3. **Check archetype and create post**:
   - Check for existing archetypes: `archetypes/posts.md` or `archetypes/default.md`
   - If an archetype exists, read it to understand front matter fields
   - Create post using Hugo: `hugo new content/posts/<filename>.md`
   - Add missing front matter fields:
     - `draft: true` - Must be true for drafts
     - `tags` - MUST include `"AI generated"` (required for transparency)
     - `author` - If not provided by archetype
     - `categories` - If not provided by archetype
     - `showToc` - If not provided by archetype

   **Important:** Respect the user's archetype structure. Only add fields that are missing.

4. **Ask user about topic**:

   Use AskUserQuestion to clarify:
   ```json
   {
     "questions": [{
       "question": "What type of article and depth do you want?",
       "header": "Topic",
       "options": [
         {"label": "Quick summary", "description": "500-1500 words, brief overview"},
         {"label": "Deep dive", "description": "2000-3000 words, comprehensive"}
       ]
     }]
   }
   ```

   Also ask about: source materials (URLs/files), key points to cover.

5. **Generate draft**:
   - Create article with this structure:

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

   - Reference Sources section FIRST (after front matter)
   - Main content with clear headings
   - AI disclaimer LAST
   - Save to `content/posts/YYYY/filename.md`

6. **Review writing quality**:
   - Professional yet conversational tone
   - First-person for personal insights
   - Technical concepts explained simply
   - Examples and practical applications included
   - All facts have sources provided by user

7. **Publish article**:

   Ask user if they want to publish:
   ```json
   {
     "questions": [{
       "question": "Review complete. Would you like to publish this article now?",
       "header": "Publish",
       "options": [
         {"label": "Yes, publish", "description": "Set draft: false, article will be publicly visible"},
         {"label": "Keep as draft", "description": "Keep draft: true for further editing"}
       ]
     }]
   }
   ```

   - If "Yes, publish" → Use Edit tool to change `draft: true` to `draft: false`
   - If "Keep as draft" → No changes, remind user they can publish later

## Example Usage

```
/writing-hugo-blog:draft Docker 部署 Go 应用的最佳实践
```

## Tips

- The draft won't be publicly visible until `draft: true` is changed to `draft: false`
- Always include source URLs in the 参考资料 section
- Keep reading time under 5 minutes for most content
