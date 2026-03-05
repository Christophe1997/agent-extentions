---
name: review
description: "Review a blog post for writing style, punctuation, formatting, and content quality. Shows issues found and offers to apply fixes. Use when user wants to improve an existing draft or published post."
argument-hint: path to the blog post file to review
allowed-tools:
  - Read
  - Edit
  - Glob
  - AskUserQuestion
---

# Review Blog Post

Review an existing blog post against the Chinese writing style guide and offer to apply fixes.

## Process

1. **Read the blog post**:
   - Parse the user's argument as the file path
   - If path is incomplete or ambiguous, use Glob to find matching files
   - Read the complete file content including front matter

2. **Load style guidelines**:
   - Reference `references/chinese-writing-style.md` for detailed review criteria

   **Review Categories:**

   | Category | Check Items |
   |----------|-------------|
   | **标题 (Headings)** | Level hierarchy, no orphan headings, no duplicate names |
   | **字间距 (Spacing)** | Chinese-English spacing, number-unit spacing |
   | **句子 (Sentences)** | Length (<40 chars), active voice, positive form |
   | **写作风格 (Style)** | Formal tone, clear pronouns, proper 的/地/得 |
   | **段落 (Paragraphs)** | One topic per paragraph, ≤7 lines |
   | **标点符号 (Punctuation)** | Full-width for Chinese, proper 顿号 for lists |
   | **引用 (Citations)** | Sources noted, external images credited |
   | **AI 标签** | AI disclaimer present at end |

3. **Analyze and report issues**:
   - For each issue, report: line number, original text, issue description, suggested fix

   Example output:
   ```markdown
   ## Review Results

   **File:** `content/posts/2026/example.md`

   ### Issues Found: 2

   #### 1. 字间距 - Line 12
   **Original:** 本文介绍如何快速启动Windows系统。
   **Issue:** 全角中文与半角英文之间应有空格
   **Suggested Fix:** 本文介绍如何快速启动 Windows 系统。
   ```

4. **Ask user to apply changes**:

   ```json
   {
     "questions": [{
       "question": "How would you like to handle these fixes?",
       "header": "Apply",
       "options": [
         {"label": "Apply all", "description": "Automatically fix all issues found"},
         {"label": "Review each", "description": "Go through each fix one by one for approval"},
         {"label": "Show only", "description": "Just show the summary, don't modify the file"}
       ]
     }]
   }
   ```

5. **Apply fixes** (if requested):
   - "Apply all" → Use Edit tool to apply all fixes, report summary
   - "Review each" → For each fix, ask user to confirm or skip
   - "Show only" → No file modifications

6. **Provide summary**:

   ```markdown
   ## Summary

   **File:** `content/posts/2026/example.md`

   | Category | Issues Found | Fixed |
   |----------|--------------|-------|
   | 字间距 | 3 | 3 |
   | 标点符号 | 2 | 2 |
   | **Total** | **5** | **5** |

   ✅ Review complete. File updated.
   ```

## Example Usage

```
/writing-hugo-blog:review content/posts/2026/my-docker-guide.md
```

## Tips

- Works on both draft and published posts
- Preserves front matter unchanged
- Focuses on style and formatting, not content accuracy
- For content accuracy, the user should verify facts separately
