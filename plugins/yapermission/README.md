# yapermission

Yet Another Permission — declarative allow / ask / deny / defer rules for Claude Code tool calls.

A `PreToolUse` hook evaluates every tool call against a TOML policy and emits the matching `permissionDecision` value: `allow` skips the prompt, `deny` blocks, `ask` forces a prompt with a reason, `defer` hands off to the next hook. Unmatched calls fall through to the top-level `default`.

## Features

| Capability | Description |
|---|---|
| **TOML policy** | Group rules under `[[deny]]`, `[[ask]]`, `[[allow]]`, or `[[defer]]` arrays-of-tables — each key directly mirrors the decision it emits. Every rule takes `tool`, `matches`, optional `reason` |
| **Stdlib-only** | Uses Python 3.11+ `tomllib` — no third-party dependencies |
| **Config hierarchy** | `./.yapermission.toml` (project) overrides `~/.yapermission.toml` (global) wholesale — no merging |
| **Audit log** | Every decision appended to `~/.yapermission.log` as JSON Lines |

### Skills

- **yap-onboard** - `/yapermission:yap-onboard` writes a heavily-commented config to `~/.yapermission.toml` — choose between `starter` (default-ask, conservative) and `yolo` (default-allow with deny-list guardrails)
- **yap-explain** - `/yapermission:yap-explain Bash "git push"` shows which rule matched and why
- **yap:rule-syntax** - Ask "how do I auto-allow git commands?" — auto-loads schema docs

### Hooks

| Hook | Description |
|---|---|
| **PreToolUse** | Intercepts every tool call (Bash, Edit, Write, Read, MCP, …) and emits one of the four `permissionDecision` values: `allow`, `deny`, `ask`, `defer` |

## Examples

```toml
# ~/.yapermission.toml
default = "ask"           # allow | deny | ask | defer

# evaluated 1st; first match wins
[[deny]]
name = "dangerous-deletes"
tool = "Bash"
reason = "Destructive command — manual approval required"
matches = [
  { command = '\brm\s+-rf\b' },
  { command = 'dd\s+.*of=/dev/' },
]

# evaluated 2nd; forces a prompt even when [[allow]] matches
[[ask]]
name = "destructive-git"
tool = "Bash"
reason = "Destructive git operation — confirm before running"
matches = [
  { command = 'git push.*--force\b' },
  { command = 'git reset\s+--hard\b' },
]

# evaluated 3rd; first match wins
[[allow]]
name = "safe-git-reads"
tool = "Bash"
matches = [
  { command = '^git (status|log|diff|branch|show|remote)\b' },
]

[[allow]]
name = "project-reads"
tool = "Read"
matches = [
  { file_path = '^/Users/me/code/' },
]

[[allow]]
name = "mcp-github-reads"
tool = '^mcp__github__(get_|list_|search_)'
matches = [ {} ]                # no input constraints — match any input

# evaluated 4th; passes to next hook in the chain
[[defer]]
name = "sensitive-area"
tool = 'Write|Edit'
reason = "Hand off to the policy-enforcement hook"
matches = [
  { file_path = '^/Users/me/sensitive/' },
]
```

**Evaluation order:** `deny` → `ask` → `allow` → `defer` → top-level `default`.

**Regex tip:** Always use TOML literal strings (single quotes) for patterns. `'\brm\b'` works as written; `"\brm\b"` would interpret `\b` as the ASCII backspace character before regex even sees it.

## Installation

### Prerequisites

- **Python 3.11+** (uses only the standard library — `tomllib` is in stdlib from 3.11 onward)

### Install the plugin

```bash
/plugin install yapermission@agent-extentions
```

### First-run setup

Run the onboarding skill to scaffold a starter config:

```
/yapermission:yap-onboard
```

This writes `~/.yapermission.toml` with comments explaining every field. Edit it to taste. **I think the true value of the plugin is setting a yolo config, thus providing an intermediate form between Claude Code's `acceptEdits` and `bypassPermissions` modes.**

## Usage

Once installed and configured, the hook runs on every tool call automatically. There are three skills you'll interact with directly:

- `/yapermission:yap-onboard` — scaffold or reset the global config
- `/yapermission:yap-explain <Tool> <args>` — dry-run the active config against a sample tool call (add `--verbose` for a per-rule trace)
- Ask "how do I write a yapermission rule?" — auto-loads the schema reference

Decisions are appended to `~/.yapermission.log`:

```json
{"ts":"2026-04-29T10:23:11Z","tool":"Bash","decision":"allow","rule":"safe-git-reads","input":{"command":"git status"},"cwd":"/Users/me/proj"}
{"ts":"2026-04-29T10:23:14Z","tool":"Bash","decision":"deny","rule":"dangerous-deletes","reason":"Destructive command — manual approval required","input":{"command":"rm -rf /tmp/x"},"cwd":"/Users/me/proj"}
{"ts":"2026-04-29T10:23:18Z","tool":"Edit","decision":"ask","rule":null,"input":{"file_path":"/etc/hosts"},"cwd":"/Users/me/proj"}
```

### Config resolution

1. If `./.yapermission.toml` exists, it is the **only** config used (replaces global)
2. Otherwise, `~/.yapermission.toml` is used
3. If neither exists, every call falls through to Claude Code's normal prompt
4. If the active TOML fails to parse, the hook logs the error and falls back to pass-through (fail-open)

## Testing

The pure functions in `scripts/yapermission.py` (`rule_matches`, `decide`, `_normalize_default`, `active_config_path`) are covered by `tests/test_yapermission.py` using the stdlib `unittest` runner — no extra dependencies.

```bash
# from the repo root
python3 -m unittest discover plugins/yapermission/tests -v
```

## License

MIT
