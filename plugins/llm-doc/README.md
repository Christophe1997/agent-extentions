# llm-doc

Documentation standards for AI coding agents. Provides comprehensive tooling for AGENTS.md lifecycle management and conventional commit messages.

## Features

### Skills

| Skill | Description |
|-------|-------------|
| `agents-md` | Knowledge base for AGENTS.md format, structure, best practices, and multi-agent compatibility |
| `conventional-commits` | Conventional Commits specification with AI-specific rules (no `Co-Authored-By`) |
| `init-agents-md` | Scaffold AGENTS.md by analyzing project configuration |
| `migrate-agents-md` | Migrate AGENT.md, .cursorrules, .windsurfrules to AGENTS.md format |
| `update-agents-md` | Update existing AGENTS.md to reflect current project state |
| `commit` | Generate commit message from staged changes and create the commit |

## Examples

```bash
# Create AGENTS.md for new project
/llm-doc:init-agents-md

# Migrate existing agent docs
/llm-doc:migrate-agents-md ./AGENT.md

# Update AGENTS.md after project changes
/llm-doc:update-agents-md

# Commit changes with conventional format
/llm-doc:commit
```

## Installation

```bash
/plugin install llm-doc@agent-extentions
```

## Usage

- **New project** → `/llm-doc:init-agents-md`
- **Existing docs** → `/llm-doc:migrate-agents-md`
- **Project changes** → `/llm-doc:update-agents-md`
- **Ready to commit** → `/llm-doc:commit`

## License

MIT
