---
name: commit
description: Generate a commit message from staged changes and create the commit
argument-hint: optional scope (e.g., "api", "ui", "docs")
allowed-tools: [Bash, Read, AskUserQuestion, Skill]
---

Generate a Conventional Commits message from staged changes and create the commit.

## Load Context

First, load the `commit-message` skill to understand commit format and best practices:
```
Use Skill tool with skill="llm-doc:commit-message"
```

This provides:
- Conventional Commits types and usage
- Style rules (imperative mood, no capitalization, etc.)
- Examples of good and bad commit messages

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
   - **Type**: Use types from the loaded skill (feat, fix, docs, etc.)
   - **Scope**: If provided via argument, use it. Otherwise infer from changed files.
   - **Description**: Follow style rules from the skill

4. **Generate commit message** using format from the skill:
   ```
   <type>[scope]: <description>
   ```

5. **Create the commit**:
   ```bash
   git commit -m "<type>[scope]: <description>"
   ```

## Error Handling

- If there are unstaged changes, always ask user whether to stage them first
- If no changes at all (staged or unstaged), inform user and exit
- Follow breaking change format from the skill when applicable
