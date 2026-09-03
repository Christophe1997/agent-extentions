---
name: agd-commit
description: This skill should be used when the user asks to "commit these changes", "create a commit", "commit this", "make a commit", or when the agent has completed a task and has uncommitted changes ready to commit. Generates a Conventional Commits message from staged changes and creates the commit, confirming with the user first unless the change is small and unambiguous.
argument-hint: optional scope (e.g., "api", "ui", "docs")
allowed-tools: [Bash, Read, AskUserQuestion, Skill]
---

Generate a Conventional Commits message from staged changes and create the commit.

## Core Principle

**Human owns the commit.** Never add `Co-Authored-By` footer for AI assistance, unless the project explicitly allows it. The human takes full responsibility for all commits in their repository.

## Load Context

First, load the `conventional-commits` skill to understand commit format and best practices:
```
Use Skill tool with skill="agd-conventional-commits"
```

This provides:
- Conventional Commits types and usage
- Style rules (imperative mood, no capitalization, etc.)
- Examples of good and bad commit messages
- Co-Authored-By guidance (never for AI, unless the project explicitly allows it)

## Process

1. **Check git status**:
   ```bash
   git status --short
   ```
   Identify unstaged files (lines where first column is space, `?`, or has changes not yet staged).

2. **Handle staging decision**:

   If the unstaged files clearly belong to the same change being committed
   (e.g. they're part of the task just finished, or the user's request
   plainly covers "these changes"), run `git add -A` without asking and
   continue to step 3.

   Otherwise — the unstaged files look unrelated to the change being
   committed, or it's unclear whether they belong — call the AskUserQuestion
   tool with these parameters:
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
   - **Body**: Check change size/complexity per skill's "When to Add Body" section

4. **Generate commit message**:
   - For small/simple changes: `<type>[scope]: <description>`
   - For large/complex changes: Include body with what/why/impact

   **Important**: Do NOT add `Co-Authored-By` footer unless the project explicitly allows it. The commit belongs to the human user.

5. **Decide whether to confirm**:

   Use judgment about whether to ask before committing rather than always
   prompting.

   **Confirm first** when any of these apply:
   - The user did not explicitly ask for a commit — the skill triggered
     itself after finishing an unrelated task. Always confirm in this case.
   - Type or scope required a judgment call rather than a clear read of the diff.
   - The diff mixes unrelated concerns instead of one clear change.
   - A breaking change is involved.
   - Anything in the diff looks risky — deletions of tracked files, possible
     secrets, or destructive/hard-to-reverse changes.
   - Anything about the request or session suggests the user wants to review
     the message first.

   To confirm, call the AskUserQuestion tool with the commit message in
   `preview` so it renders in the side-by-side monospace pane (preserving
   alignment, blank lines, and any trailers). Keep the question short — the
   preview carries the content.

   ```json
   {
     "questions": [{
       "question": "Ready to commit with this message?",
       "header": "Confirm commit",
       "multiSelect": false,
       "options": [
         {
           "label": "Yes, commit",
           "description": "Create the commit with this message",
           "preview": "<full commit message — subject + blank line + body>"
         },
         {
           "label": "Edit message",
           "description": "Provide a custom commit message instead"
         }
       ]
     }]
   }
   ```

   Notes on the `preview` field:
   - Required only on the "Yes, commit" option — its presence triggers the
     split layout. Leaving "Edit message" without a preview is intentional;
     the focus pane is empty for that option.
   - Pass the **complete** commit message including any trailers. Newlines
     inside the JSON string become real line breaks in the rendered box.
   - Previews require `multiSelect: false` — they are not supported in
     multi-select questions.

   Decision handling:
   - If "Yes, commit" → Proceed to step 6
   - If "Edit message" → Ask user for custom message, then proceed to step 6
   - If the user attached free-text via the Notes input (returned in the
     `annotations` field keyed by question text), treat it as an amendment
     request: incorporate the note into the message and re-confirm.

   **Otherwise, commit directly**: none of the above apply, so surface the
   generated commit message as normal output text immediately before
   committing — the user still sees what was written even though they
   weren't asked — then proceed straight to step 6.

6. **Create the commit**:
   - For single-line: `git commit -m "<type>[scope]: <description>"`
   - For multi-line: `git commit -m "<type>[scope]: <description>" -m "<body line 1>" -m "<body line 2>"`

## Error Handling

- When unstaged changes exist, stage them directly if they clearly belong to
  the change being committed; otherwise ask via AskUserQuestion before
  proceeding to step 3
- If no changes at all (staged or unstaged), inform user and exit
- Follow breaking change format from the skill when applicable
- Confirm before executing `git commit` whenever any condition in step 5
  applies — especially when the skill self-triggered without an explicit
  user request — and when in doubt, ask
