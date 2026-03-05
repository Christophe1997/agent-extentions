---
name: migrate-agents-md
description: Migrate existing agent documentation (AGENT.md, .cursorrules, etc.) to compact AGENTS.md format
argument-hint: optional source file path (auto-detects AGENT.md, .cursorrules, etc.)
allowed-tools: [Bash, Read, Write, Glob, Skill, AskUserQuestion]
---

Migrate existing agent documentation files to the standardized AGENTS.md format. Default to creating a compact single file; ask about references folder only for complex projects.

## Load Context

Load the agents-md skill for format guidance:
```
Use Skill tool with skill="llm-doc:agents-md"
```
Provides: sections, structure, symlink patterns, best practices

## Migration Sources

Detect and migrate from common agent documentation files:

| Source File | Detection | Migration Strategy |
|-------------|-----------|-------------------|
| `AGENT.md` | Single-file predecessor | Convert to AGENTS.md, ensure all sections covered |
| `.cursorrules` | Cursor IDE rules | Extract rules, convert to AGENTS.md sections |
| `.windsurfrules` | Windsurf IDE rules | Extract rules, convert to AGENTS.md sections |
| `CLAUDE.md` | Claude Code instructions | Merge with AGENTS.md or convert |
| `contributing.md` | Developer guidelines | Extract relevant sections for AGENTS.md |

## Process

1. **Detect source files**:
   ```bash
   ls -la | grep -E '(AGENT\.md|\.cursorrules|\.windsurfrules|CLAUDE\.md)'
   ```

2. **If no source specified, auto-detect**:
   - Priority: AGENT.md > .cursorrules > .windsurfrules > CLAUDE.md
   - Prompt user if multiple files found

3. **Read and analyze source file**:
   - Identify existing sections
   - Extract commands, conventions, and guidelines
   - Note any missing recommended sections

4. **Transform to compact AGENTS.md format**:
   - Map existing content to recommended sections
   - Add missing sections based on project analysis
   - **Keep core AGENTS.md lean and actionable** (target: 50-80 lines)
   - Focus on essential commands and conventions

5. **Create the new AGENTS.md**:
   - Write to ./AGENTS.md (or specified path)
   - Do not overwrite existing AGENTS.md without confirmation

6. **Ask about references folder** using AskUserQuestion (only if source was verbose or user wants detailed docs):
   ```
   questions: [
     {
       "question": "Would you like me to create a references folder for the detailed content from the original file?",
       "header": "References",
       "options": [
         {
           "label": "No, single file is enough",
           "description": "Keep AGENTS.md as a simple, compact file. Recommended for most projects."
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

   **Only ask if**:
   - Original source file was verbose (>100 lines)
   - User explicitly wants to preserve all detailed content
   - Project has complex patterns needing documentation

7. **Create reference files** (if user chose yes):
   - Create detailed docs in references folder (e.g., docs/agents/)
   - Reference them from AGENTS.md

8. **Validate the migrated file**:
   - Check all commands are executable
   - Ensure all recommended sections present
   - Confirm no content lost in migration
   - Verify file is compact (under 100 lines)

9. **Handle original file**:
   - Ask user: "Should I create a symlink from the original file to AGENTS.md?"
   - If yes: `ln -sf AGENTS.md <original-file>`
   - If no: Ask if user wants to delete or keep original

10. **Ask about additional symlinks**:
    "Would you like me to create symlinks for other AI agents? (CLAUDE.md, .cursorrules, .windsurfrules)"

## Content Mapping

Transform common patterns:

| Source Pattern | AGENTS.md Section |
|----------------|-------------------|
| "Run tests with..." | Testing instructions |
| "Code style: ..." | Code style |
| "Before committing..." | PR instructions |
| "Environment setup..." | Setup commands |
| "Security notes..." | Security |

## Example Transformation

```markdown
# Before (verbose .cursorrules, 80 lines)
## Code Style
- Use TypeScript strict mode
- Single quotes for strings
- No semicolons
- Max line length: 100 characters
- Functional components with hooks
- Colocate tests next to components
- Use meaningful variable names
- Avoid any type
- Prefer const over let
- Document complex functions with JSDoc
[... 50 more lines of detailed conventions ...]

# After (compact AGENTS.md, 60 lines)
## Code style
- TypeScript strict mode
- Single quotes, no semicolons
- Functional components with hooks

## PR instructions
- Use Conventional Commits (see llm-doc:commit-message skill)
- Run `pnpm lint && pnpm test` before pushing
```

## Validation Checklist

After migration, verify:
- [ ] All commands are executable
- [ ] All recommended sections present (or intentionally omitted)
- [ ] Original content preserved (nothing lost)
- [ ] Format follows skill best practices
- [ ] File is concise (ideally under 100 lines)
- [ ] References folder only created if user wanted it

## Notes

- Always load the agents-md skill for context
- **Default to compact**: Create a simple AGENTS.md first
- Preserve all original content - migration should not lose information
- Only ask about references folder for verbose sources
- Ask user before deleting original files
- Validate migrated file before completing
- Offer symlink creation for backward compatibility
