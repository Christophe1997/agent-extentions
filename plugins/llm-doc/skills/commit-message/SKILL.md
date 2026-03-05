---
name: commit-message
description: This skill should be used when the user asks to "write a commit message", "generate a commit", "help me commit", "create a commit message for", "commit these changes", or mentions commits format. Provides guidance for generating compact, clear commit messages following Conventional Commits specification.
---

# Commit Messages

Generate commit messages that are compact, clear, and follow the Conventional Commits specification.

## Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Key rules:**
- Use imperative mood in description ("add" not "added" or "adds")
- No capitalization of first letter in description
- No period at end of description
- Keep description under 72 characters
- Use body only when needed for context

## Types

| Type | Usage | Example |
|------|-------|---------|
| `feat` | New feature | `feat: add user authentication` |
| `fix` | Bug fix | `fix: resolve null pointer in login` |
| `docs` | Documentation only | `docs: update API endpoints` |
| `style` | Formatting, no code change | `style: format indentation` |
| `refactor` | Code change without fix/feature | `refactor: extract utility function` |
| `test` | Adding/updating tests | `test: add unit tests for auth` |
| `chore` | Build, CI, dependencies | `chore: bump dependencies` |
| `perf` | Performance improvement | `perf: optimize query execution` |
| `ci` | CI/CD configuration | `ci: add GitHub Actions workflow` |
| `build` | Build system changes | `build: update webpack config` |
| `revert` | Revert previous commit | `revert: remove broken feature` |

## Scope (Optional)

Scope indicates the affected module or component:

```
feat(auth): add OAuth2 support
fix(api): handle timeout errors
docs(readme): add installation steps
```

**Keep scope short** - typically one word.

## Breaking Changes

For breaking changes, add `!` after type/scope or include `BREAKING CHANGE:` in footer:

```
feat!: redesign API endpoints

BREAKING CHANGE: all endpoints now require authentication
```

## Style Guidelines

### Do

- Be specific and descriptive
- Explain "what" and "why", not "how"
- Use imperative mood
- Keep it compact

### Don't

- Don't use vague messages ("fix bug", "update code")
- Don't describe implementation details
- Don't exceed 72 characters in description
- Don't capitalize description start

## Examples

### Good Examples

```
feat: add password reset functionality
fix: resolve memory leak in worker process
docs: clarify installation requirements
refactor(search): extract ranking algorithm
test: add edge cases for date parser
chore(deps): bump eslint to 9.0.0
feat(api)!: change response format to JSON
```

### Bad Examples

```
Fixed the bug                          # Past tense, vague
Added new feature for user login.      # Capitalized, period
feat: I added a new login page         # First person
fix: fix the thing                     # Vague, not descriptive
updates to the codebase                # No type, vague
feat(authentication-system): add oauth # Scope too long
```

## Process for Generating Commits

1. **Analyze changes**: Review staged files with `git diff --staged`
2. **Identify type**: Determine the primary change category
3. **Add scope**: If changes are focused on specific module
4. **Write description**: Compact summary in imperative mood
5. **Add body**: Only if additional context is necessary

## Multi-line Commits

Use body for additional context when the change is complex:

```
feat: add batch processing endpoint

Add /api/batch endpoint to process multiple items in a single request.
Includes rate limiting and progress tracking.

Closes #123
```

## Related Commits

When referencing issues or PRs:

```
fix: resolve race condition in worker

The concurrent access issue occurred when multiple workers tried to
update the same cache entry simultaneously.

Fixes #456
```

## Co-Authored-By Footer

### Rule: No AI Attribution

**Never add `Co-Authored-By` footer for AI agents** (Claude Code, GitHub Copilot, OpenAI Codex, Cursor, etc.).

AI is a tool, not a co-author. The human takes full ownership of every commit in their repository.

```
feat: add user dashboard

Implement dashboard with analytics widgets and real-time updates.
```

### Human Ownership

All commits are attributed to the human user, regardless of AI assistance. This ensures:

- Clean git history without tool attribution
- Human maintains full responsibility for code changes
- Simpler commit messages focused on content, not tools

### When Co-Authored-By IS Appropriate

Only use `Co-Authored-By` for **human collaborators**:

```
feat: add user dashboard

Co-Authored-By: Jane Doe <jane@example.com>
```
