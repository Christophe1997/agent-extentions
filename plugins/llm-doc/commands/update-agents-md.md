---
name: update-agents-md
description: Update existing AGENTS.md with current project changes. Keep it compact by default.
argument-hint: optional path (default: ./AGENTS.md)
allowed-tools: [Bash, Read, Write, Glob, Skill, AskUserQuestion]
---

Update an existing AGENTS.md file to reflect current project state. Default to keeping the file compact; ask about references folder only if content becomes too verbose.

## Load Context

Load the agents-md skill for format guidance:
```
Use Skill tool with skill="llm-doc:agents-md"
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

2. **Analyze project for changes**:
   - Check package.json scripts vs documented commands
   - Compare linter/formatter config with documented style
   - Review CI/CD workflows for new steps
   - Detect new tools or dependencies

3. **Identify update scope**:
   - **Minor update**: 1-2 sections need changes
   - **Moderate update**: 3-4 sections or new sections needed
   - **Major update**: Significant restructure required

4. **Update sections incrementally**:
   - Preserve existing structure and style
   - Update outdated commands
   - Add new sections for new tools/processes
   - Remove obsolete sections
   - **Keep file compact** (target: 50-80 lines)

5. **Write updated AGENTS.md**:
   - Maintain consistent formatting
   - Keep file concise (under 100 lines)
   - Ensure all commands are current and executable

6. **Ask about references folder** (only if file exceeds 80 lines after update):
   Use AskUserQuestion:
   ```
   questions: [
     {
       "question": "The AGENTS.md is getting long. Would you like me to create a references folder for detailed documentation?",
       "header": "References",
       "options": [
         {
           "label": "No, keep it compact",
           "description": "Keep AGENTS.md as a single compact file. Try to condense content further."
         },
         {
           "label": "Yes, create docs/agents/",
           "description": "Create references folder and move detailed content there."
         },
         {
           "label": "Yes, use custom path",
           "description": "Specify a custom path for the references folder."
         }
       ]
     }
   ]
   ```

7. **Validate the updated file**:
   - Run validation checklist from skill
   - Test all commands are executable
   - Ensure no information lost
   - Verify file is compact

8. **Report changes**:
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
- [ ] File is concise (under 100 lines)
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
- Only ask about references folder when file exceeds 80 lines
- Validate before completing
- Report all changes to user
