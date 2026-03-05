---
name: agents-md
description: This skill should be used when the user asks to "create an AGENTS.md", "write AGENTS.md", "set up AGENTS.md", "what is AGENTS.md", "configure AI agent instructions", "migrate AGENT.md", "update AGENTS.md", or mentions AGENTS.md format. Provides guidance for creating and maintaining AGENTS.md files - a standardized format for AI coding agent context.
---

# AGENTS.md Format

AGENTS.md is a standardized markdown file that serves as a "README for AI coding agents" - providing dedicated, predictable context to help AI coding agents work effectively on a project.

## Purpose

Unlike README.md (designed for humans), AGENTS.md contains:
- Build and test commands
- Code style guidelines
- Testing instructions
- Security considerations
- Any context a new teammate would need

**Key principle**: Give agents a clear, predictable place for instructions while keeping READMEs concise for human contributors.

## Basic Structure

AGENTS.md is standard Markdown with no required fields:

```markdown
# AGENTS.md

## Setup commands
- Install deps: `pnpm install`
- Start dev server: `pnpm dev`
- Run tests: `pnpm test`

## Code style
- TypeScript strict mode
- Single quotes, no semicolons
- Use functional patterns where possible
```

## Simple First Approach

**Default**: Create one compact, lean AGENTS.md file. This satisfies most projects.

**References folder** (optional): Only create `docs/agents/` when:
- Project has complex, project-specific patterns that need detailed explanation
- User explicitly wants separate reference files
- Content exceeds ~80 lines and cannot be condensed

Commands use `AskUserQuestion` to ask about references folder when appropriate.

## Progressive Disclosure Pattern

**Key Principle**: Keep AGENTS.md lean by referencing detailed documentation instead of duplicating content inline.

**Keep in AGENTS.md** (inline):
- Essential commands (install, test, build)
- Critical conventions (quotes, semicolons, etc.)
- Security requirements (brief reminders)
- Brief project overview (1-2 sentences)

**Move to references** (only if needed, default: `docs/agents/`):
- Detailed architecture explanations
- Extensive code examples (>5 lines)
- Long-form documentation (>10 lines per section)
- Project-specific patterns and conventions

Example reference format:
```markdown
## Testing instructions
- Unit tests: `pnpm test`
- E2E tests: `pnpm test:e2e`
See docs/agents/testing.md for detailed guidelines.
```

**Cross-skill references**: Use skill names instead of duplicating content from other domains:
```markdown
## PR instructions
- Use Conventional Commits (see llm-doc:commit-message skill)
```

**Implementation checklist**:
- [ ] AGENTS.md under 100 lines (ideally 50-80)
- [ ] References folder only created if needed
- [ ] Essential commands remain inline

## Recommended Sections

1. **Project Overview**: Brief description (1-2 sentences)
2. **Dev Environment Setup**: Essential commands
3. **Testing Instructions**: How to run and write tests
4. **Code Style Guidelines**: Conventions and patterns
5. **PR/Commit Guidelines**: Reference `llm-doc:commit-message` skill
6. **Security Considerations**: Critical security reminders

See [examples/basic-agents-md.md](./examples/basic-agents-md.md) for a complete example.

## Lifecycle Management

### Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/llm-doc:init-agents-md` | Create new from scratch | New project, no existing docs |
| `/llm-doc:migrate-agents-md` | Convert from other format | Have AGENT.md, .cursorrules, etc. |
| `/llm-doc:update-agents-md` | Update existing AGENTS.md | File exists but outdated |

### Decision Tree

```
No AGENTS.md exists? → Use init-agents-md
AGENT.md or other format exists? → Use migrate-agents-md
AGENTS.md exists but outdated? → Use update-agents-md
```

### References Folder Decision

Commands use `AskUserQuestion` to ask about creating the references folder:

**Ask when**:
- Project has complex, project-specific patterns
- Content would benefit from detailed documentation
- User wants to add architecture diagrams, tutorials, etc.

**Default path**: `docs/agents/`

See [references/lifecycle.md](./references/lifecycle.md) for detailed processes.

## Agent Compatibility

AGENTS.md works across AI coding agents: OpenAI Codex, Cursor, Claude Code, Aider, Google Jules, Factory.

**Symlinks**: Create symbolic links for agent-specific files to maintain one source of truth:
- Claude Code: `ln -s AGENTS.md CLAUDE.md`
- Cursor: `ln -s AGENTS.md .cursorrules`
- Windsurf: `ln -s AGENTS.md .windsurfrules`

See [references/agent-compatibility.md](./references/agent-compatibility.md) for tool-specific configs and monorepo patterns.

## Migration

### Automated
Use `/llm-doc:migrate-agents-md [source-file]` to auto-detect and convert AGENT.md, .cursorrules, etc.

### Manual
```bash
mv AGENT.md AGENTS.md
ln -s AGENTS.md AGENT.md  # backward compatibility
```

See [examples/migration-example.md](./examples/migration-example.md) for a complete before/after example.

## Best Practices

### Do
- Keep it concise and scannable
- Use code blocks for commands
- Include actual commands agents can execute
- Treat it as living documentation
- Apply progressive disclosure

### Don't
- Don't duplicate README content verbatim
- Don't include vague instructions
- Don't make it too long (agents work better with focused context)
- Don't forget to update as project evolves

## Validation

After creating, migrating, or updating AGENTS.md, verify:
- [ ] All commands are executable
- [ ] File is concise (under 100 lines)
- [ ] Progressive disclosure applied
- [ ] No placeholder content
- [ ] Essential commands remain inline

See [references/validation.md](./references/validation.md) for comprehensive validation checklist.

## Agent Behavior Rules

| Rule | Behavior |
|------|----------|
| **No required fields** | Use any structure that fits the project |
| **Test execution** | If tests listed, execute them before completing tasks |
| **Living document** | Update AGENTS.md as project evolves |
| **Symlink prompt** | Ask user about symlinks after creating AGENTS.md |
| **References prompt** | Use AskUserQuestion to ask about references folder when project is complex |

## References

- [references/lifecycle.md](./references/lifecycle.md) - Detailed create/update/migrate processes
- [references/agent-compatibility.md](./references/agent-compatibility.md) - Tool configs, symlinks, monorepo patterns
- [references/validation.md](./references/validation.md) - Comprehensive validation checklist
- [examples/basic-agents-md.md](./examples/basic-agents-md.md) - Complete working example
- [examples/migration-example.md](./examples/migration-example.md) - Before/after migration example
