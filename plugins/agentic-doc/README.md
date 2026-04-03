# agentic-doc

Documentation standards for agentic programming. Provides comprehensive tooling for AGENTS.md lifecycle management and conventional commit messages.

## Features

### Skills

| Skill | Description |
|-------|-------------|
| `agd:agents-md` | Knowledge base for AGENTS.md format, structure, best practices, and multi-agent compatibility |
| `agd:conventional-commits` | Conventional Commits specification with AI-specific rules (no `Co-Authored-By`) |
| `agd:init-agents-md` | Scaffold AGENTS.md by analyzing project configuration |
| `agd:migrate-agents-md` | Migrate AGENT.md, .cursorrules, .windsurfrules to AGENTS.md format |
| `agd:update-agents-md` | Update existing AGENTS.md to reflect current project state |
| `agd:commit` | Generate commit message from staged changes and create the commit |

## Examples

```bash
# Create AGENTS.md for new project
/agd:init-agents-md

# Migrate existing agent docs
/agd:migrate-agents-md ./AGENT.md

# Update AGENTS.md after project changes
/agd:update-agents-md

# Commit changes with conventional format
/agd:commit
```

## Installation

```bash
/plugin install agentic-doc@agent-extentions
```

## Usage

- **New project** → `/agd:init-agents-md`
- **Existing docs** → `/agd:migrate-agents-md`
- **Project changes** → `/agd:update-agents-md`
- **Ready to commit** → `/agd:commit`

## License

MIT
