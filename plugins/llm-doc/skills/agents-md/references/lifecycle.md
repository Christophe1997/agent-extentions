# AGENTS.md Lifecycle Management

Detailed processes for creating, updating, and migrating AGENTS.md files.

## Core Principle: Simple First

**Default to a compact, single AGENTS.md file.** Only create references folder when:
- Project has complex, project-specific patterns
- User explicitly wants detailed documentation
- Content exceeds ~80 lines and cannot be condensed

## Automated Commands

Use commands for lifecycle management:

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/llm-doc:init-agents-md` | Create new from scratch | New project, no existing agent docs |
| `/llm-doc:migrate-agents-md` | Convert from other format | Have AGENT.md, .cursorrules, etc. |
| `/llm-doc:update-agents-md` | Update existing AGENTS.md | File exists but needs updates |

All commands use `AskUserQuestion` to ask about references folder only when appropriate.

## Initial Creation Process

### Manual Creation Steps

1. **Start simple**: Create basic file with setup commands and test instructions (50-80 lines)
2. **Add conventions**: Document code style and patterns
3. **Include context**: Add anything you'd tell a new teammate
4. **Validate**: Run validation checklist
5. **For monorepos**: Add nested AGENTS.md files for subprojects
6. **Ask about symlinks**: Ask user if they want symbolic links for other agents

**References folder**: Only ask about creating `docs/agents/` if:
- Project is complex with many patterns
- User requests detailed documentation

### Automated Creation

Use `/llm-doc:init-agents-md [path]` to:
1. Analyze project structure and configuration
2. Detect package manager, test framework, linters
3. Generate compact AGENTS.md with project-specific content
4. Ask about references folder using AskUserQuestion (only if needed)
5. Validate the generated file
6. Offer symlink creation for other agents

## Update Process

### When to Update

Trigger updates when:
- New build/test/lint commands added
- Code style conventions changed
- New dependencies or tooling introduced
- Security requirements updated
- Project structure reorganized
- CI/CD pipeline changed
- After major refactoring

### Update Strategies

**Minor Update (1-2 sections)**:
- Directly edit the affected sections
- Keep file compact

**Moderate Update (3-4 sections)**:
- Review related sections for consistency
- May need to reorganize slightly
- Still aim for compact single file

**Major Update**:
- Significant restructure needed
- Consider full rewrite following skill template
- May need references folder (ask user)

### Automated Update

Use `/llm-doc:update-agents-md [path]` to:
1. Read existing AGENTS.md
2. Analyze project for changes
3. Update sections incrementally
4. Ask about references folder (only if file exceeds 80 lines after update)
5. Validate the updated file
6. Report all changes

## Migration Process

### Migration Sources

| Source File | Detection | Migration Strategy |
|-------------|-----------|-------------------|
| `AGENT.md` | Single-file predecessor | Convert to AGENTS.md, ensure all sections covered |
| `.cursorrules` | Cursor IDE rules | Extract rules, convert to AGENTS.md sections |
| `.windsurfrules` | Windsurf IDE rules | Extract rules, convert to AGENTS.md sections |
| `CLAUDE.md` | Claude Code instructions | Merge with AGENTS.md or convert |
| `contributing.md` | Developer guidelines | Extract relevant sections for AGENTS.md |

### Content Mapping

Transform common patterns:

| Source Pattern | AGENTS.md Section |
|----------------|-------------------|
| "Run tests with..." | Testing instructions |
| "Code style: ..." | Code style |
| "Before committing..." | PR instructions |
| "Environment setup..." | Setup commands |
| "Security notes..." | Security |

### Automated Migration

Use `/llm-doc:migrate-agents-md [source-file]` to:
1. Auto-detect source files
2. Transform content to compact AGENTS.md format
3. Ask about references folder using AskUserQuestion (only for verbose sources)
4. Create reference files if user wants them
5. Validate the migrated file
6. Offer symlink creation for backward compatibility

## Iteration and Maintenance

- **Update as project evolves**: AGENTS.md is a living document
- **Keep it compact**: Default to single file, only add references when truly needed
- **Validate regularly**: Test commands after major changes
- **Review periodically**: Ensure content stays current and relevant
