# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code extensions marketplace repository. It distributes plugins that enhance AI agent capabilities through the Claude Code marketplace system.

## Core Design Principle

**Progressive Disclosure Over Context Bloat**: Give agents tools to discover context themselves. Skills should reference other files rather than containing all information inline.

See [docs/agents/progressive-disclosure.md](docs/agents/progressive-disclosure.md) for detailed patterns.

## Repository Structure

```
agent-extentions/
├── .claude-plugin/
│   └── marketplace.json       # Central plugin registry
├── plugins/
│   ├── writing-hugo-blog/     # Hugo blog post creator
│   ├── llm-doc/               # AGENTS.md & commit message standards
│   └── show-me-the-session/   # Session transcript HTML exporter
└── .claude/
    └── settings.local.json    # Local Claude settings
```

See [docs/agents/show-me-the-session.md](docs/agents/show-me-the-session.md) for the session exporter architecture.

## Plugin Architecture

Each plugin follows this structure:
```
plugin-name/
├── .claude-plugin/
│   └── plugin.json            # Plugin metadata
├── README.md                  # Plugin documentation
├── skills/                    # Core functionality (knowledge)
│   └── skill-name/
│       ├── SKILL.md           # Skill definition with frontmatter
│       └── references/        # Optional: detailed content
├── commands/                  # Optional: user-initiated actions
│   └── command-name.md        # Command with YAML frontmatter
├── agents/                    # Optional: autonomous tasks
│   └── agent-name.md          # Agent definition
├── hooks/                     # Optional: event-driven automation
│   └── hooks.json             # Hook configuration
├── .mcp.json                  # Optional: MCP server config
└── scripts/                   # Optional: utility scripts
```

## Adding a New Plugin

1. Create directory under `plugins/` with the plugin name
2. Add `plugin.json` under `.claude-plugin/`
3. Register in `marketplace.json` with source path `./plugins/your-plugin`
4. Create at least one skill or command

## Component Patterns

| Component | Location | Purpose | Key Fields |
|-----------|----------|---------|------------|
| Skills | `skills/*/SKILL.md` | Knowledge that activates on queries | `name`, `description` (with trigger phrases) |
| Commands | `commands/*.md` | User slash commands (`/plugin:cmd`) | `name`, `allowed-tools`, `argument-hint` |
| Agents | `agents/*.md` | Autonomous subagents | `description`, `tools`, `model`, `color` |
| Hooks | `hooks/hooks.json` | Event-driven automation | `PreToolUse`, `PostToolUse`, `Stop`, etc. |
| MCP | `.mcp.json` | External service integration | `mcpServers` with `command`, `args`, `env` |
| Settings | `.claude/plugin.local.md` | User config | YAML frontmatter + markdown |

**Patterns:**
- Use `${CLAUDE_PLUGIN_ROOT}` for relative paths within plugin
- Use `${VAR:-default}` for env vars with defaults
- Skills: lean body, use `references/` for details
- Commands: include `Skill` in `allowed-tools` to load skill context
- Commands: use `AskUserQuestion` for all interactive prompts — avoid plain-text "ask user" instructions
- Agents: include "When to Use" section with example queries
- Settings: add `.claude/*.local.md` to `.gitignore`

See [docs/agents/command-patterns.md](docs/agents/command-patterns.md) for command details.

## Plugin README Structure

All plugin READMEs follow this unified structure:

1. **Features** - List what's included (Commands, Skills, Hooks, MCP, Agents as tables)
2. **Examples** - Code samples (optional)
3. **Installation** - Requirements + `/plugin install ${plugin-name}@agent-extentions`
4. **Usage** - How to use the plugin
5. **License** - MIT

See [docs/agents/readme-template.md](docs/agents/readme-template.md) for the full template.

## Validation

Before publishing, verify:
- [ ] `plugin.json` has required fields (name, version, description)
- [ ] `version` field in related `plugin.json`, `marketplace.json` have updated correctly for changes
- [ ] Skills have clear trigger phrases in description
- [ ] Agents have "When to Use" section with examples
- [ ] README follows unified structure (Features, Examples, Installation, Usage, License)
- [ ] MCP plugins document environment variables
