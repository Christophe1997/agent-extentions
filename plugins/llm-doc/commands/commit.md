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

1. **Check git status**:
   ```bash
   git status --short
   ```
   Identify unstaged files (lines where first column is space, `?`, or has changes not yet staged).

2. **Handle staging decision**:

   Call the AskUserQuestion tool with these parameters:
   ```json
   {
     "questions": [{
       "question": "There are unstaged changes. Would you like me to stage them?",
       "header": "Stage changes",
       "options": [
         {"label": "Stage all", "description": "Run 'git add -A' to stage all changes"},
         {"label": "Skip staging", "description": "Commit only currently staged changes"}
       ]
     }]
   }
   ```

   Wait for the tool response, then:
   - "Stage all" → Run `git add -A`, then continue to step 3
   - "Skip staging" → Continue to step 3 with current staged changes

   If no unstaged changes exist, skip this step and continue directly to step 3.

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

- When unstaged changes exist, ask user via AskUserQuestion before proceeding to step 3
- If no changes at all (staged or unstaged), inform user and exit
- Follow breaking change format from the skill when applicable
