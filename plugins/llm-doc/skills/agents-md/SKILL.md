---
name: agents-md
description: This skill should be used when the user asks to "create an AGENTS.md", "write AGENTS.md", "help me set up AGENTS.md", "what is AGENTS.md", "configure AI coding agent instructions", "add agent documentation", or mentions AGENTS.md format. Provides guidance for creating AGENTS.md files - a standardized format for providing context and instructions to AI coding agents.
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

## Recommended Sections

### 1. Project Overview
Brief description of what the project does and its architecture.

### 2. Dev Environment Setup
Essential commands for getting started:
```markdown
## Setup commands
- Install: `npm install`
- Dev server: `npm run dev`
- Build: `npm run build`
- Test: `npm test`
```

### 3. Testing Instructions
How to run and write tests:
```markdown
## Testing instructions
- Run all tests: `pnpm test`
- Run specific test: `pnpm vitest run -t "test name"`
- Coverage: `pnpm test:coverage`
- Add or update tests for code you change
```

### 4. Code Style Guidelines
Conventions and patterns:
```markdown
## Code style
- Use TypeScript strict mode
- Prefer const over let
- Max line length: 100 characters
- Use meaningful variable names
```

### 5. PR/Commit Guidelines
Reference the `llm-doc:commit-message` skill for Conventional Commits format:
```markdown
## PR instructions
- Use Conventional Commits format (see llm-doc:commit-message skill)
- Run `pnpm lint` and `pnpm test` before committing
- Reference issues: Fixes #123
```

When generating this section, load the `commit-message` skill for commit format details.

### 6. Security Considerations
```markdown
## Security
- Never commit .env files
- Validate all user inputs
- Use parameterized queries
```

## Monorepo Support

For large monorepos, use nested AGENTS.md files:

```
my-monorepo/
├── AGENTS.md              # Root-level instructions
├── packages/
│   ├── api/
│   │   └── AGENTS.md      # API-specific instructions
│   └── web/
│       └── AGENTS.md      # Web-specific instructions
```

**Precedence**: The closest AGENTS.md to the edited file wins. Explicit user chat prompts override everything.

## Agent Compatibility

AGENTS.md works across many AI coding agents:
- OpenAI Codex
- Cursor
- Claude Code
- Aider
- Google Jules
- Factory

### Tool-Specific Configuration

**Aider** (`.aider.conf.yml`):
```yaml
read: AGENTS.md
```

**Gemini CLI** (`.gemini/settings.json`):
```json
{
  "contextFileName": "AGENTS.md"
}
```

## Best Practices

### Do

- Keep it concise and scannable
- Use code blocks for commands
- Include actual commands agents can execute
- Treat it as living documentation
- Add sections that help agents work effectively
- Include anything you'd tell a new teammate

### Don't

- Don't duplicate README content verbatim
- Don't include vague instructions
- Don't forget to update it as the project evolves
- Don't make it too long (agents work better with focused context)

## Complete Example

See [examples/basic-agents-md.md](./examples/basic-agents-md.md) for a full working example demonstrating:
- Project overview with stack description
- Setup and dev commands
- Testing instructions with specific commands
- Code style conventions
- PR workflow and commit format
- Security considerations

## Migration Guide

If you have existing agent documentation:

```bash
# Rename existing file
mv AGENT.md AGENTS.md

# Create backward-compatible symlink
ln -s AGENTS.md AGENT.md
```

## Agent Behavior Rules

When working with AGENTS.md, follow these rules:

| Rule | Behavior |
|------|----------|
| **No required fields** | AGENTS.md is standard Markdown - use any structure that fits the project |
| **Test execution** | If tests are listed, execute them and fix failures before completing tasks |
| **Living document** | Update AGENTS.md as the project evolves - it's not static |
| **Symlink prompt** | After creating AGENTS.md, ask user if they want symlinks for agent-specific files |

## Agent-Specific Symlinks

Many AI coding agents have their own configuration file names. Instead of maintaining multiple files, create symbolic links to AGENTS.md:

| Agent | File | Symlink Command |
|-------|------|-----------------|
| Claude Code | `CLAUDE.md` | `ln -s AGENTS.md CLAUDE.md` |
| Cursor | `.cursorrules` | `ln -s AGENTS.md .cursorrules` |
| Windsurf | `.windsurfrules` | `ln -s AGENTS.md .windsurfrules` |
| Aider | `AGENTS.md` | Configured in `.aider.conf.yml` |
| Gemini CLI | `AGENTS.md` | Configured in `.gemini/settings.json` |

**Benefits**: Maintain one source of truth while supporting multiple agents.

## Process for Creating AGENTS.md

1. **Start simple**: Create basic file with setup commands and test instructions
2. **Add conventions**: Document code style and patterns
3. **Include context**: Add anything you'd tell a new teammate
4. **Iterate**: Update as you discover what agents need
5. **For monorepos**: Add nested AGENTS.md files for subprojects
6. **Ask about symlinks**: After creating AGENTS.md, ask the user if they want symbolic links for other agent-specific files (CLAUDE.md, .cursorrules, etc.)
