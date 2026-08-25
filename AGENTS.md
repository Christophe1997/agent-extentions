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
│   └── <plugin-name>/         # One directory per plugin — see Plugin Architecture below
└── .claude/
    └── settings.local.json    # Local Claude settings
```

`marketplace.json` is the source of truth for which plugins are installed — don't duplicate that list here.

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
4. Create at least one skill
5. Add the plugin to root README

## Component Patterns

| Component | Location | Purpose | Key Fields |
|-----------|----------|---------|------------|
| Skills | `skills/*/SKILL.md` | Knowledge that activates on queries | `name`, `description` (with trigger phrases) |
| Agents | `agents/*.md` | Autonomous subagents | `description`, `tools`, `model`, `color` |
| Hooks | `hooks/hooks.json` | Event-driven automation | `PreToolUse`, `PostToolUse`, `Stop`, etc. |
| MCP | `.mcp.json` | External service integration | `mcpServers` with `command`, `args`, `env` |
| Settings | `.claude/plugin.local.md` | User config | YAML frontmatter + markdown |

**Patterns:**
- Use `${CLAUDE_PLUGIN_ROOT}` for relative paths within plugin
- Use `${VAR:-default}` for env vars with defaults
- Skills: lean body, use `references/` for details; add `disable-model-invocation: true` for skills that don't need LLM reasoning, and those can only be invoked by human.
- Agents: include "When to Use" section with example queries
- Settings: add `.claude/*.local.md` to `.gitignore`

See [docs/agents/skill-patterns.md](docs/agents/skill-patterns.md) for skill body guidelines.

## Plugin README Structure

All plugin READMEs follow: **Features** → **Examples** (optional) → **Installation** → **Usage** → **License**

See [docs/agents/readme-template.md](docs/agents/readme-template.md) for the full template.

## Validation

Before publishing, verify:
- [ ] `plugin.json` has required fields (name, version, description)
- [ ] `version` field bumped in `plugin.json`/`marketplace.json` for changes
- [ ] Skills have clear trigger phrases in description
- [ ] Agents have "When to Use" section with examples
- [ ] README follows unified structure (Features, Examples, Installation, Usage, License)
- [ ] MCP plugins document environment variables
