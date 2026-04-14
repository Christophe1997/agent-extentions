---
name: agd:update-agents-md
description: "This skill should be used when the user says their AGENTS.md is outdated, stale, or needs refreshing, or when they say 'update AGENTS.md', 'refresh AGENTS.md', 'AGENTS.md is out of date', or 'sync AGENTS.md with project'. Provides a step-by-step process to update an existing AGENTS.md to reflect current project state."
argument-hint: optional path (default: ./AGENTS.md)
allowed-tools: [Bash, Read, Write, Glob, Skill, AskUserQuestion]
---

Update an existing AGENTS.md file to reflect current project state. Default to keeping the file compact; ask about references folder only if content becomes too verbose.

## Load Context

Load the agents-md skill for format guidance:
```
Use Skill tool with skill="agd:agents-md"
```
Provides: sections, structure, validation checklist, best practices

## When to Update

Trigger updates when:
- New build/test/lint commands added to package.json or config
- Code style conventions changed (formatter config, linter rules)
- New dependencies or tooling introduced
- Security requirements updated
- Project structure reorganized
- CI/CD pipeline changed
- After major refactoring

## Process

1. **Read existing AGENTS.md**:
   ```bash
   cat AGENTS.md
   ```
   - Identify current sections and content
   - Note current line count

2. **Freshness check** — determine what has changed since AGENTS.md was last updated:
   ```bash
   # When was AGENTS.md last committed?
   git log -1 --format="%ar" -- AGENTS.md

   # What files changed since then? (guard against untracked/never-committed case)
   AGENTS_COMMIT=$(git log -1 --format="%H" -- AGENTS.md)
   [ -n "$AGENTS_COMMIT" ] && git diff --name-only "$AGENTS_COMMIT" HEAD || git status --short
   ```
   - If AGENTS.md is untracked or was never committed, `$AGENTS_COMMIT` will be empty and the command falls back to `git status --short` automatically
   - If the subshell returns empty without the guard, `git diff --name-only HEAD` silently diffs the working tree instead — always use the guarded form
   - Scan the diff output for staleness signals:
     - New/removed directories (`plugins/`, `src/`, `packages/`) → structure drift
     - Changes to `package.json`, `Makefile`, or build configs → commands may be outdated
     - New CI workflow files (`.github/workflows/`) → undocumented pipeline steps
     - New linter/formatter configs (`.eslintrc`, `vitest.config.ts`) → style section stale
   - Use signals to pre-classify the update scope before deeper analysis:
     - **Fresh** (0-1 signals AND committed <1 month ago): expect a minor 1-2 section edit
     - **Moderate** (2-3 signals): focus step 3 analysis on flagged areas only
     - **Stale** (4+ signals, OR last commit >3 months ago regardless of signal count): full pass required
   - This is a predictive pre-classification to scope step 3 effort. The final update scope is confirmed in step 4 after analysis and may differ.

3. **Analyze project for changes**:
   - Check package.json scripts vs documented commands
   - Compare linter/formatter config with documented style
   - Review CI/CD workflows for new steps
   - Detect new tools or dependencies

4. **Identify update scope**:
   - **Minor update**: 1-2 sections need changes
   - **Moderate update**: 3-4 sections or new sections needed
   - **Major update**: Significant restructure required

5. **Update sections incrementally**:
   - Preserve existing structure and style
   - Update outdated commands
   - Add new sections for new tools/processes
   - Remove obsolete sections
   - **Target: 50-80 lines** — condense aggressively before writing
   - **Use relative paths** for all references (e.g., `./docs/agents/testing.md`, `../api/AGENTS.md`)
   - **For monorepos**: Add/update relative path references to sibling packages

6. **Check line count before writing**:
   - Count projected lines of updated content
   - If over 100 lines, **first try to condense**: shorten descriptions, remove duplicated info, apply progressive disclosure
   - If still over 100 lines after condensing, proceed to step 7 before writing

7. **If projected content exceeds 100 lines** — ask and then act:
   Use AskUserQuestion:
   ```
   questions: [
     {
       "question": "The AGENTS.md will exceed 100 lines. Would you like me to split detailed content into a references folder?",
       "header": "References",
       "options": [
         {
           "label": "No, keep it compact",
           "description": "Try harder to condense. Keep AGENTS.md as a single file."
         },
         {
           "label": "Yes, create docs/agents/",
           "description": "Create docs/agents/ and move detailed sections there, leaving brief summaries with links in AGENTS.md."
         },
         {
           "label": "Yes, use custom path",
           "description": "Specify a custom path for the references folder."
         }
       ]
     }
   ]
   ```

   **If user chooses to split**:
   - Identify sections that are best candidates: architecture explanations, long code examples, multi-step guides
   - For each section to move: create `docs/agents/<section-name>.md` (or user-specified path)
   - Replace the section in AGENTS.md with a 2-3 line summary + `See docs/agents/<section-name>.md for details.`
   - Ensure AGENTS.md stays under 100 lines after the split

8. **Write updated AGENTS.md**:
   - Maintain consistent formatting
   - Ensure all commands are current and executable

9. **Validate the updated file**:
   - Run validation checklist from skill
   - Test all commands are executable
   - Ensure no information lost
   - Verify file is under 100 lines

10. **Report changes**:
   Summarize what was updated:
   ```
   Updated AGENTS.md:
   - Added: New testing commands (vitest)
   - Updated: Build process (now uses turbo)
   - Removed: Obsolete npm scripts
   - Line count: 65 (was 58)
   ```

## Update Strategies

### Minor Update (1-2 sections)
- Directly edit the affected sections
- No need for extensive analysis
- Keep file compact

### Moderate Update (3-4 sections)
- Review related sections for consistency
- May need to reorganize slightly
- Still aim for compact single file

### Major Update
- Significant restructure needed
- Consider full rewrite following skill template
- May need references folder (ask user)

## Validation Checklist

After update, verify:
- [ ] All commands are current and executable
- [ ] File is concise (under 100 lines; if over, references split was applied)
- [ ] No information lost during update
- [ ] Format consistent with skill best practices
- [ ] All sections relevant to current project state

## Diff Format

Show changes in unified diff format for clarity:

```diff
## Setup commands
 - Install: `npm install`
 + Install: `pnpm install`
 - Dev server: `npm run dev`
 + Dev server: `pnpm dev`
```

## Notes

- Always load the agents-md skill for context
- Preserve existing voice and style where possible
- Update incrementally - don't rewrite entire file unnecessarily
- **Default to compact**: Keep AGENTS.md as a single file unless it gets too long
- When file exceeds 100 lines: ask user AND then actually perform the split if they confirm
- Validate before completing
- Report all changes to user
