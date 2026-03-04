---
name: commit
description: Generate a commit message from staged changes and create the commit
argument-hint: optional scope (e.g., "api", "ui", "docs")
allowed-tools: [Bash, Read, AskUserQuestion]
---

Generate a Conventional Commits message from staged changes and create the commit.

## Process

1. **Check for unstaged changes**:
   ```bash
   git status --short
   ```

2. **If there are unstaged changes**, always ask the user:
   - Show the unstaged files
   - Ask: "There are unstaged changes. Would you like me to stage them?"
   - If yes, run: `git add <files>` or `git add -A` for all
   - If no, proceed with only currently staged changes

3. **Analyze the diff** to determine:
   - **Type**: feat, fix, docs, style, refactor, test, chore, perf, ci, build
   - **Scope**: If provided via argument, use it. Otherwise infer from changed files.
   - **Description**: Compact summary in imperative mood (under 72 chars)

4. **Generate commit message** following Conventional Commits:
   ```
   <type>[scope]: <description>
   ```

5. **Create the commit**:
   ```bash
   git commit -m "<type>[scope]: <description>"
   ```

## Type Selection Guide

| Type | When to use |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only changes |
| `style` | Formatting, no code logic change |
| `refactor` | Code change without fix/feature |
| `test` | Adding or updating tests |
| `chore` | Build, CI, dependencies, tooling |
| `perf` | Performance improvement |

## Style Rules

- Use imperative mood ("add" not "added")
- No capitalization of first letter
- No period at end
- Keep description under 72 characters

## Examples

```bash
# User runs: /llm-doc:commit
# Staged: src/auth/login.ts modified
# Output: git commit -m "fix(auth): handle empty password"

# User runs: /llm-doc:commit api
# Staged: src/api/*.ts files modified
# Output: git commit -m "feat(api): add rate limiting"
```

## Error Handling

- If there are unstaged changes, always ask user whether to stage them first
- If no changes at all (staged or unstaged), inform user and exit
- If description exceeds 72 chars, split into subject + body
- For breaking changes, add `!` after type: `feat!: breaking change`
