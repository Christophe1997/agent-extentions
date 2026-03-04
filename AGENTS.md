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
│   ├── agent-design/          # AI agent design guidelines
│   └── redis-dev/             # Redis development tools
└── .claude/
    └── settings.local.json    # Local Claude settings
```

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
4. Create at least one skill in `skills/` directory

## Component Patterns

### Skills (SKILL.md)
Skills provide specialized knowledge that activates on specific queries.

```yaml
---
name: skill-name
description: Third-person description with specific trigger phrases
trigger: Optional glob patterns for auto-activation
---
```

Keep body lean, use `references/` for details, `examples/` for code samples.

### Commands (commands/*.md)
Commands are user-initiated slash commands.

```yaml
---
name: command-name
description: What the command does
argument-hint: Optional argument description
allowed-tools: [Read, Write, Bash, Skill]
---
```

Invoked as: `/plugin-name:command-name [args]`. Include `Skill` in allowed-tools to load skills for context.

### Agents (agents/*.md)
Agents are autonomous subagents for specialized tasks.

```yaml
---
description: When to trigger this agent (with example queries)
tools: [Read, Grep, Glob]  # Tools the agent can use
model: sonnet | haiku      # Model selection
color: blue | orange | ... # UI indicator
---
```

**Key:** Include "When to Use" section with concrete example queries for triggering.

### MCP Integration (.mcp.json)
For external service integration:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "executable",
      "args": ["-h", "${HOST:-localhost}", "-p", "${PORT:-6379}"],
      "env": {
        "HOST": "${ENV_VAR}"
      }
    }
  }
}
```

**Patterns:**
- Use `${CLAUDE_PLUGIN_ROOT}` for relative paths within plugin
- Use `${VAR:-default}` for environment variables with defaults
- Document required environment variables in README

### Plugin Settings (.local.md)
For user-configurable settings, use the `.claude/plugin-name.local.md` pattern:

```yaml
---
setting1: value1
setting2: value2
---
# Optional documentation
```

**Add to .gitignore:** `.claude/*.local.md`

## Validation

Before publishing, verify:
- [ ] `plugin.json` has required fields (name, version, description)
- [ ] Skills have clear trigger phrases in description
- [ ] Agents have "When to Use" section with examples
- [ ] README documents any required configuration
- [ ] MCP plugins document environment variables
