# yapermission schema reference

Complete reference for the TOML policy file. The high-level overview lives in `SKILL.md`; this file covers details and edge cases.

## File location

| Path | Role |
|---|---|
| `~/.yapermission.toml` | Global config — used when no project config is present |
| `./.yapermission.toml` | Project config — **replaces** the global wholesale |

The hook reads from the cwd of the tool call. Switching directories switches policies.

## Top-level fields

| Key | Type | Required | Default | Notes |
|---|---|---|---|---|
| `default` | string | no | `ask` | One of `allow`, `deny`, `ask`, `defer` — exactly mirroring Claude Code's `permissionDecision` field. Any other value falls back to `ask`. |
| `deny`  | array of tables | no | `[]` | Rules evaluated 1st. First match emits `permissionDecision: "deny"`. |
| `ask`   | array of tables | no | `[]` | Rules evaluated 2nd. First match emits `permissionDecision: "ask"`. Forces the prompt even when an `[[allow]]` rule below would match. |
| `allow` | array of tables | no | `[]` | Rules evaluated 3rd. First match emits `permissionDecision: "allow"`. |
| `defer` | array of tables | no | `[]` | Rules evaluated 4th. First match emits `permissionDecision: "defer"`. Hands the decision to the next PreToolUse hook in the chain. |

Any other top-level keys are ignored.

### permissionDecision values

| Value | Hook behavior |
|---|---|
| `allow` | Tool runs without a prompt |
| `deny` | Tool call is blocked; `permissionDecisionReason` is sent back to Claude |
| `ask` | Forces Claude Code's permission prompt; the rule's `reason` is shown to the user |
| `defer` | Hands the decision to the next hook in the chain |

## Rule fields

| Key | Type | Required | Notes |
|---|---|---|---|
| `name` | string | recommended | Used in audit log and `--verbose` traces. Use a short, unique identifier. |
| `tool` | regex string | no | `re.search`-matched against `tool_name`. Missing means "any tool". |
| `matches` | array of inline tables | yes (to fire) | OR-of-ANDs. Empty or missing = rule never fires. Use `[ {} ]` for "any input". |
| `reason` | string | no | Shown to the user on `deny` and `ask` (via `permissionDecisionReason`); recorded in the audit log for every decision. |

## TOML string types and regex

TOML has two relevant string forms; they behave very differently for regex:

| Form | Quote | Backslash handling | Recommended for regex? |
|---|---|---|---|
| Literal | `'...'` | Backslashes are literal — `'\b'` is two characters: `\` and `b` | **Yes — always use this for regex.** |
| Basic | `"..."` | Backslashes are escape sequences — `"\b"` is the backspace character | No — would force you to write `"\\b"` everywhere. |

```toml
matches = [
  { command = '\brm\s+-rf\b' },         # ✅ literal string — regex works
  { command = "\\brm\\s+-rf\\b" },      # ⚠️  basic string — works but doubles every backslash
  { command = "\brm\s+-rf\b" },         # ❌ broken — \b becomes ASCII backspace before regex sees it
]
```

## Pattern matching

### Tool name

Tool names you can match include any of Claude Code's built-in tools (`Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, `Task`, `BashOutput`, `KillShell`) and any MCP tool, which has the form `mcp__<server>__<tool>`.

Examples:
- `tool = "Bash"` — exact match for Bash
- `tool = 'Write|Edit'` — either tool
- `tool = '^mcp__'` — any MCP tool
- `tool = '^mcp__github__(get_|list_|search_)'` — read-only github MCP tools

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

```toml
# Anchor at the start
{ command = '^git status' }

# Word boundary (prevents matching 'rmdir' when you want 'rm')
{ command = '\brm\b' }

# Alternation
{ command = '^(ls|pwd|whoami|date)\b' }

# Path under a directory
{ file_path = '^/Users/me/code/' }

# Negative lookahead (path NOT under a directory)
{ file_path = '^(?!/Users/me/code/)' }

# Match any input (when the tool regex is sufficient)
matches = [ {} ]
```

## Audit log

Every decision is appended to `~/.yapermission.log` as one JSON object per line:

```json
{"ts":"2026-04-29T10:23:11Z","tool":"Bash","decision":"allow","rule":"safe-git-reads","reason":"Read-only git operations","input":{"command":"git status"},"cwd":"/Users/me/proj","config_path":"/Users/me/.yapermission.toml"}
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
- Test new patterns with `/yapermission:yap-explain --verbose` against representative inputs before committing them.

## Failure modes

| Situation | Behavior |
|---|---|
| TOML missing entirely | Every call → `ask` (pass-through) |
| TOML malformed | Hook logs error (with `tomllib.TOMLDecodeError` in the record), falls back to `ask`. Never silently allows. |
| `matches` is `[]` or absent | Rule never fires. Use `[ {} ]` for "any input". |
| Field referenced in `matches` is absent in `tool_input` | Treated as empty string. `^anything` will not match; `.*` will. |
| `reason` missing on a deny rule | A generic message is recorded and shown to Claude. |
| Python < 3.11 | Hook errors on import — `tomllib` is a 3.11+ stdlib module. |

## Debugging tips

1. **Run `/yapermission:yap-explain --verbose <Tool> <args>`** for a per-rule trace of which rules were considered and why each matched or skipped.
2. **`tail -f ~/.yapermission.log`** while you work — every tool call shows up.
3. **Test rules in isolation** with explain before committing them to the live config.
4. **A rule that "doesn't fire" is almost always** an empty `matches` list (use `[ {} ]`) or a regex that's missing a `^` / word boundary.
5. **Hooks load at session start.** After editing the TOML, restarts are not required (it's re-read each call). After editing `hooks/hooks.json` itself, restart Claude Code.
