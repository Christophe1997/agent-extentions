# Agent Extensions

Claude Code plugins to my own taste.

## Plugins

| Plugin | Description |
|--------|-------------|
| [review-blog](./plugins/review-blog/README.md) | Review Chinese blog posts for writing style, punctuation, and formatting issues |
| [agentic-doc](./plugins/agentic-doc/README.md) | Documentation standards for agentic programming: AGENTS.md lifecycle & conventional commits |
| [show-me-the-session](./plugins/show-me-the-session/README.md) | Export Claude Code sessions as solarized-light HTML pages |
| [permission-notification](./plugins/permission-notification/README.md) | macOS notifications when Claude Code needs permission |
| [tdd](./plugins/tdd/README.md) | Test-Driven Development guidance based on Kent Beck's Red/Green/Refactor workflow |
| [a2a](./plugins/a2a/README.md) | A2A (Agent-to-Agent) protocol client — communicate with any A2A-compliant agent by URL or alias |
| [yapermission](./plugins/yapermission/README.md) | Auto-approve or block tool calls via a TOML ruleset, with project-overrides-global config and decision logging |
| [go-pkg-discovery](./plugins/go-pkg-discovery/README.md) | Discover Go packages, modules, versions, vulnerabilities, reverse dependencies, and exported symbols via pkg.go.dev (wraps `pkgsite-cli`) |
| [zettel-sync](./plugins/zettel-sync/README.md) | Maintain a structured Obsidian vault (Zettelkasten-style) from recent Claude Code sessions: harvest concepts into inbox drafts, detect orphans, near-duplicates, and MOC gaps — all as a single batched-approval review doc |

> **Portability note.** All plugins are authored for Claude Code and rely on Claude-specific tools (`AskUserQuestion`, `Skill` chaining, the `agents/` subagent format) and/or hook events (`PreToolUse`, `PermissionRequest`, `Stop`). Installing via skills.sh in another agent will load the `SKILL.md` prose, but the Claude-specific UX and automation will not function.

## Installation

### Via Claude Code

Add the marketplace:

```bash
/plugin marketplace add Christophe1997/agent-extentions
```

Install plugins:

```bash
/plugin install review-blog@agent-extentions
/plugin install agentic-doc@agent-extentions
/plugin install show-me-the-session@agent-extentions
/plugin install permission-notification@agent-extentions
/plugin install tdd@agent-extentions
/plugin install a2a@agent-extentions
/plugin install yapermission@agent-extentions
/plugin install go-pkg-discovery@agent-extentions
/plugin install zettel-sync@agent-extentions
```

### Via skills.sh

For agents other than Claude Code, install the cross-agent skills via the [skills.sh](https://skills.sh) CLI:

```bash
npx skills add Christophe1997/agent-extentions
```

## License

MIT License - see [LICENSE](LICENSE) for details.
