# yapermission schema reference

Complete reference for the YAML policy file. The high-level overview lives in `SKILL.md`; this file covers details and edge cases.

## File location

| Path | Role |
|---|---|
| `~/.yapermission.yaml` | Global config — used when no project config is present |
| `./.yapermission.yaml` | Project config — **replaces** the global wholesale |

The hook reads from the cwd of the tool call. Switching directories switches policies.

## Top-level fields

| Key | Type | Required | Default | Notes |
|---|---|---|---|---|
| `default` | string | no | `ask` | One of `approve`, `block`, `ask`. `approve` and `allow` are aliases; `block` and `deny` are aliases. |
| `deny` | list | no | `[]` | Rules evaluated first. First match wins. |
| `approve` | list | no | `[]` | Rules evaluated after `deny`. First match wins. |

Any other top-level keys are ignored.

## Rule fields

| Key | Type | Required | Notes |
|---|---|---|---|
| `name` | string | recommended | Used in audit log and `--verbose` traces. Use a short, unique identifier. |
| `tool` | regex | no | `re.search`-matched against `tool_name`. Missing means "any tool". |
| `matches` | list of dict | yes (to fire) | OR-of-ANDs. Empty or missing = rule never fires. Use `- {}` for "any input". |
| `reason` | string | no | Shown to Claude on `deny`; recorded in the log on either decision. |

## Pattern matching

### Tool name

Tool names you can match include any of Claude Code's built-in tools (`Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, `Task`, `BashOutput`, `KillShell`) and any MCP tool, which has the form `mcp__<server>__<tool>`.

Examples:
- `tool: Bash` — exact match for Bash
- `tool: 'Write|Edit'` — either tool
- `tool: '^mcp__'` — any MCP tool
- `tool: '^mcp__github__(get_|list_|search_)'` — read-only github MCP tools

### Tool input fields

The `tool_input` shape varies by tool. Common fields:

| Tool | Common fields |
|---|---|
| `Bash` | `command`, `description`, `timeout` |
| `Read` | `file_path`, `offset`, `limit` |
| `Write` | `file_path`, `content` |
| `Edit` | `file_path`, `old_string`, `new_string`, `replace_all` |
| `Glob` | `pattern`, `path` |
| `Grep` | `pattern`, `path`, `glob`, `type` |

Match patterns are Python regexes evaluated with `re.search` (i.e., they match anywhere in the string unless anchored with `^` / `$`). All field values are stringified before matching, so numbers and booleans coerce cleanly.

### Common regex patterns

```yaml
# Anchor at the start
command: '^git status'

# Word boundary (prevents matching 'rmdir' when you want 'rm')
command: '\brm\b'

# Alternation
command: '^(ls|pwd|whoami|date)\b'

# Path under a directory
file_path: '^/Users/me/code/'

# Negative lookahead (path NOT under a directory)
file_path: '^(?!/Users/me/code/)'

# Match any input (when the tool regex is sufficient)
matches:
  - {}
```

## Audit log

Every decision is appended to `~/.yapermission.log` as one JSON object per line:

```json
{"ts":"2026-04-28T10:23:11Z","tool":"Bash","decision":"allow","rule":"safe-git-reads","reason":"Read-only git operations","input":{"command":"git status"},"cwd":"/Users/me/proj","config_path":"/Users/me/.yapermission.yaml"}
```

Useful one-liners:

```bash
# Last 20 decisions
tail -20 ~/.yapermission.log | jq .

# Count decisions by rule
jq -r '.rule // "default"' ~/.yapermission.log | sort | uniq -c | sort -rn

# Show all denies with reasons
jq -r 'select(.decision=="deny") | "\(.ts) \(.rule): \(.input | tostring)"' ~/.yapermission.log

# Find calls that fell through to ask (candidates for new rules)
jq -r 'select(.decision=="ask" and .rule==null) | .input' ~/.yapermission.log
```

## Regex caveats (ReDoS)

Patterns are user-controlled and matched with Python's `re` module, which is **not** linear-time. A pathological regex like `(a+)+$` can take exponential time on certain inputs ("regex denial of service"). Practical guardrails:

- The hook is wrapped with a 5-second timeout in `hooks.json`, so the worst case is a 5-second pause before the call falls through to `ask`.
- Avoid nested quantifiers (`(a+)+`, `(.*)*`).
- Anchor with `^` / `$` whenever you can — it short-circuits failures.
- Prefer character classes (`[a-z]+`) over alternation when matching a single position.
- Test new patterns with `/yapermission:explain --verbose` against representative inputs before committing them.

## Failure modes

| Situation | Behavior |
|---|---|
| YAML missing entirely | Every call → `ask` (pass-through) |
| YAML malformed | Hook logs error, falls back to `ask`. Never silently allows. |
| `matches` is `[]` or absent | Rule never fires. Use `[{}]` for "any input". |
| Field referenced in `matches` is absent in `tool_input` | Treated as empty string. `^anything` will not match; `.*` will. |
| `reason` missing on a deny rule | A generic message is recorded and shown to Claude. |
| PyYAML not installed | Hook surfaces a clear error in the audit log and falls back to `ask`. |

## Debugging tips

1. **Run `/yapermission:explain --verbose <Tool> <args>`** for a per-rule trace of which rules were considered and why each matched or skipped.
2. **`tail -f ~/.yapermission.log`** while you work — every tool call shows up.
3. **Test rules in isolation** with explain before committing them to the live config.
4. **A rule that "doesn't fire" is almost always** an empty `matches:` list (use `[{}]`) or a regex that's missing a `^` / word boundary.
5. **Hooks load at session start.** After editing the YAML, restarts are not required (it's re-read each call). After editing `hooks/hooks.json` itself, restart Claude Code.
