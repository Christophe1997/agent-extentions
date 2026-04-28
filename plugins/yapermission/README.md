# yapermission

Yet Another Permission — declarative allow / ask / deny / defer rules for Claude Code tool calls.

A `PreToolUse` hook evaluates every tool call against a YAML policy and emits the matching `permissionDecision` value: `allow` skips the prompt, `deny` blocks, `ask` forces a prompt with a reason, `defer` hands off to the next hook. Unmatched calls fall through to the top-level `default:`.

## Features

| Capability | Description |
|---|---|
| **PreToolUse hook** | Intercepts every tool call (Bash, Edit, Write, Read, MCP, …) and emits one of the four `permissionDecision` values: `allow`, `deny`, `ask`, `defer` |
| **YAML policy** | Group rules under `deny:`, `ask:`, `allow:`, or `defer:` blocks — each key directly mirrors the decision it emits. Every rule takes `tool`, `matches[]`, optional `reason` |
| **Config hierarchy** | `./.yapermission.yaml` (project) overrides `~/.yapermission.yaml` (global) wholesale — no merging |
| **Audit log** | Every decision appended to `~/.yapermission.log` as JSON Lines |
| **Onboarding** | `/yapermission:yap-onboard` writes a heavily-commented config to `~/.yapermission.yaml` — choose between `starter` (default-ask, conservative) and `yolo` (default-allow with deny-list guardrails) |
| **Dry-run debugger** | `/yapermission:yap-explain Bash "git push"` shows which rule matched and why |
| **Knowledge skill** | Ask "how do I auto-allow git commands?" — auto-loads schema docs |

## Examples

```yaml
# ~/.yapermission.yaml
default: ask              # allow | deny | ask | defer

deny:                     # evaluated 1st; first match wins
  - name: dangerous-deletes
    tool: Bash
    matches:
      - command: '\brm\s+-rf\b'
      - command: 'dd\s+.*of=/dev/'
    reason: "Destructive command — manual approval required"

ask:                      # evaluated 2nd; forces a prompt even when `allow:` matches
  - name: destructive-git
    tool: Bash
    matches:
      - command: 'git push.*--force\b'
      - command: 'git reset\s+--hard\b'
    reason: "Destructive git operation — confirm before running"

allow:                    # evaluated 3rd; first match wins
  - name: safe-git-reads
    tool: Bash
    matches:
      - command: '^git (status|log|diff|branch|show|remote)\b'

  - name: project-reads
    tool: Read
    matches:
      - file_path: '^/Users/me/code/'

  - name: mcp-github-reads
    tool: '^mcp__github__(get_|list_|search_)'
    matches:
      - {}                # no input constraints — match any input

defer:                    # evaluated 4th; passes to next hook in the chain
  - name: sensitive-area
    tool: 'Write|Edit'
    matches:
      - file_path: '^/Users/me/sensitive/'
    reason: "Hand off to the policy-enforcement hook"
```

**Evaluation order:** `deny` → `ask` → `allow` → `defer` → top-level `default`.

## Installation

### Prerequisites

- **Python 3.8+** (uses only the standard library + `pyyaml`)
- **PyYAML**: `pip install --user pyyaml` (or `pip3`)

### Install the plugin

```bash
/plugin install yapermission@agent-extentions
```

### First-run setup

Run the onboarding skill to scaffold a starter config:

```
/yapermission:yap-onboard
```

This writes `~/.yapermission.yaml` with comments explaining every field. Edit it to taste. **I think the true value of the plugin is setting a yolo config, thus providing an intermediate form between Claude Code's `acceptEdits` and `bypassPermissions` modes.**

## Usage

Once installed and configured, the hook runs on every tool call automatically. There are three skills you'll interact with directly:

- `/yapermission:yap-onboard` — scaffold or reset the global config
- `/yapermission:yap-explain <Tool> <args>` — dry-run the active config against a sample tool call (add `--verbose` for a per-rule trace)
- Ask "how do I write a yapermission rule?" — auto-loads the schema reference

Decisions are appended to `~/.yapermission.log`:

```json
{"ts":"2026-04-28T10:23:11Z","tool":"Bash","decision":"allow","rule":"safe-git-reads","input":{"command":"git status"},"cwd":"/Users/me/proj"}
{"ts":"2026-04-28T10:23:14Z","tool":"Bash","decision":"deny","rule":"dangerous-deletes","reason":"Destructive command — manual approval required","input":{"command":"rm -rf /tmp/x"},"cwd":"/Users/me/proj"}
{"ts":"2026-04-28T10:23:18Z","tool":"Edit","decision":"ask","rule":null,"input":{"file_path":"/etc/hosts"},"cwd":"/Users/me/proj"}
```

### Config resolution

1. If `./.yapermission.yaml` exists, it is the **only** config used (replaces global)
2. Otherwise, `~/.yapermission.yaml` is used
3. If neither exists, every call falls through to Claude Code's normal prompt
4. If the active YAML fails to parse, the hook logs the error and falls back to pass-through (fail-open)

## Testing

The pure functions in `scripts/yapermission.py` (`rule_matches`, `decide`, `_normalize_default`, `active_config_path`) are covered by `tests/test_yapermission.py` using the stdlib `unittest` runner — no extra dependencies.

```bash
# from the repo root
python3 -m unittest discover plugins/yapermission/tests -v
```

## License

MIT
