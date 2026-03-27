# llm-doc

Documentation standards for AI coding agents. Provides comprehensive tooling for AGENTS.md lifecycle management and conventional commit messages.

## Features

### Skills

- **agents-md** - Guidance for creating and maintaining AGENTS.md files. Includes structure, sections, best practices, and symlink patterns for multi-agent compatibility.
- **conventional-commits** - Generate compact, clear commit messages following Conventional Commits specification. No `Co-Authored-By` footer for AI agents.

### Commands

| Command | Description |
|---------|-------------|
| `/llm-doc:commit` | Generate commit message from staged changes and create the commit |
| `/llm-doc:init-agents-md [path]` | Scaffold AGENTS.md by analyzing project configuration |
| `/llm-doc:migrate-agents-md [source]` | Migrate AGENT.md, .cursorrules, .windsurfrules to AGENTS.md format |
| `/llm-doc:update-agents-md [path]` | Update existing AGENTS.md to reflect current project state |

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
