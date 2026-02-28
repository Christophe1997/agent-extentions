---
name: review
description: Review a blog post for writing style, punctuation, formatting, and content quality. Shows issues found and offers to apply fixes. Use when user wants to improve an existing draft or published post.
argument-hint: path to the blog post file to review
allowed-tools:
  - Read
  - Edit
  - Glob
  - AskUserQuestion
---

# Review Blog Post

Review an existing blog post against the Chinese writing style guide and offer to apply fixes.

## Instructions

### Step 1: Read the Blog Post

1. Parse the user's argument as the file path
2. If path is incomplete or ambiguous, use Glob to find matching files
3. Read the complete file content including front matter

### Step 2: Load Style Guidelines

Reference `references/chinese-writing-style.md` for detailed review criteria:

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

### Step 3: Analyze and Report Issues

For each issue found, report:

```markdown
## Review Results

**File:** `content/posts/2026/example.md`

### Issues Found: 5

#### 1. 字间距 - Line 12
**Original:**
> 本文介绍如何快速启动Windows系统。

**Issue:** 全角中文与半角英文之间应有空格

**Suggested Fix:**
> 本文介绍如何快速启动 Windows 系统。

---

#### 2. 标点符号 - Line 25
**Original:**
> 我最欣赏的科技公司有 Google, Facebook, 腾讯。

**Issue:** 中文并列词应使用顿号

**Suggested Fix:**
> 我最欣赏的科技公司有 Google、Facebook、腾讯。

---
```

### Step 4: Ask User to Apply Changes

After showing all issues, use AskUserQuestion:

```yaml
question: "How would you like to handle these fixes?"
header: "Apply"
options:
  - label: "Apply all"
    description: "Automatically fix all issues found"
  - label: "Review each"
    description: "Go through each fix one by one for approval"
  - label: "Show only"
    description: "Just show the summary, don't modify the file"
```

### Step 5: Apply Fixes (if requested)

**For "Apply all":**
- Use Edit tool to apply all fixes at once
- Report summary of changes made

**For "Review each":**
- For each fix, ask user to confirm or skip
- Apply approved fixes individually

**For "Show only":**
- No file modifications
- User can manually apply changes

### Step 6: Summary

After applying fixes (or showing only), provide:

```markdown
## Summary

**File:** `content/posts/2026/example.md`

| Category | Issues Found | Fixed |
|----------|--------------|-------|
| 字间距 | 3 | 3 |
| 标点符号 | 2 | 2 |
| 句子 | 1 | 1 |
| **Total** | **6** | **6** |

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
