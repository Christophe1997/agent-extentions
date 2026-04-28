---
name: yap-rule-syntax
description: Reference for the yapermission YAML rule schema and evaluation order. Trigger when the user asks how to write a yapermission rule, the yapermission yaml format or schema, how to auto-allow git commands or shell utilities, how to force a prompt for force-push or other commands, how to block rm -rf or other dangerous commands, or how project and global yapermission configs interact.
---

# yapermission rule syntax

A yapermission policy is a single YAML file with up to five top-level keys: `default`, `deny`, `ask`, `allow`, `defer`.

## Top-level shape

```yaml
default: ask              # allow | deny | ask | defer  (fallback when no rule matches)

deny:                     # evaluated 1st; matched rule emits permissionDecision "deny"
  - { ... rule ... }

ask:                      # evaluated 2nd; matched rule emits permissionDecision "ask"
  - { ... rule ... }      # forces the prompt even when an `allow:` rule below matches

allow:                    # evaluated 3rd; matched rule emits permissionDecision "allow"
  - { ... rule ... }

defer:                    # evaluated 4th; matched rule emits permissionDecision "defer"
  - { ... rule ... }      # hands the decision to the next PreToolUse hook
```

If no rule matches, the top-level `default:` value is emitted. Missing `default` means `ask`.

Each rule-list key directly mirrors Claude Code's `permissionDecision` field — there are no aliases:

| Decision | Behavior |
|---|---|
| `allow` | Skip the permission prompt and run the tool |
| `deny` | Block the tool call (engine attaches `permissionDecisionReason`) |
| `ask` | Force the permission prompt (rule's `reason:` is shown to the user) |
| `defer` | Hand the decision to the next hook in the chain |

The `default:` field accepts only those four values; anything else falls back to `ask`.

## Rule shape

```yaml
- name: short-identifier              # appears in audit log; required for clarity
  tool: Bash                          # regex matched against tool name; missing = match any
  matches:                            # list of input-pattern entries (REQUIRED)
    - command: '^git (status|log)\b'  # all fields in this entry must match (AND)
    - command: '^ls\b'                # any entry that matches makes the rule fire (OR)
  reason: "Read-only operations"      # shown to the user on deny/ask; logged on allow/defer
```

## Matching semantics

- **`tool`** is a regex (`re.search`). `Bash` matches exactly; `'Write|Edit'` matches either; `'^mcp__github__(get_|list_)'` matches any read-only github MCP call.
- **`matches`** is a *list of entries*. The rule fires if **any one entry** matches.
- Within an entry, **every** `field: pattern` pair is checked with `re.search` against `tool_input[field]`. If a referenced field is absent, it's treated as the empty string.
- Use `- {}` to mean "match any input" (e.g., when the `tool` regex is enough).
- Missing or empty `matches:` means **the rule never fires**. To match any input, write `matches: [{}]`.

## Evaluation order

```
   ┌──────────┐    matched    ┌──────────────┐
   │   deny   │ ─────────────►│  return deny │
   └────┬─────┘                └──────────────┘
        │ no match
        ▼
   ┌──────────┐    matched    ┌──────────────┐
   │   ask    │ ─────────────►│  return ask  │
   └────┬─────┘                └──────────────┘
        │ no match
        ▼
   ┌──────────┐    matched    ┌──────────────┐
   │  allow   │ ─────────────►│ return allow │
   └────┬─────┘                └──────────────┘
        │ no match
        ▼
   ┌──────────┐    matched    ┌──────────────┐
   │  defer   │ ─────────────►│ return defer │
   └────┬─────┘                └──────────────┘
        │ no match
        ▼
   ┌──────────┐
   │ default  │
   └──────────┘
```

The order encodes "more restrictive intent wins": `deny` is absolute, `ask` forces a manual confirm even when a broader `allow:` rule below would auto-approve, and `defer` only fires when nothing earlier had an opinion.

## Config resolution

1. If `./.yapermission.yaml` exists in the cwd, it is the **only** active config (replaces global).
2. Otherwise, `~/.yapermission.yaml` is used.
3. Otherwise, every call falls through to Claude Code's normal permission prompt.
4. If the active YAML fails to parse, the hook logs the error and falls back to `ask` (fail-open).

## Cookbook

**Auto-allow read-only git:**
```yaml
allow:
  - name: safe-git-reads
    tool: Bash
    matches:
      - command: '^git (status|log|diff|branch|show|remote)\b'
```

**Force a prompt for destructive git, even though `git-all` below would auto-allow:**
```yaml
ask:
  - name: destructive-git
    tool: Bash
    matches:
      - command: 'git push.*--force\b'
      - command: 'git reset\s+--hard\b'
      - command: 'git branch\s+-D\b'
    reason: "Destructive git operation — confirm before running"

allow:
  - name: git-all
    tool: Bash
    matches:
      - command: '^git\b'
```

**Block destructive commands:**
```yaml
deny:
  - name: nuke
    tool: Bash
    matches:
      - command: '\brm\s+-rf\b'
      - command: 'sudo\s+rm\b'
      - command: 'dd\s+.*of=/dev/'
    reason: "Destructive command — manual approval required"
```

**Restrict file writes to a project directory:**
```yaml
deny:
  - name: writes-outside-project
    tool: 'Write|Edit'
    matches:
      - file_path: '^(?!/Users/me/code/)'   # negative lookahead
    reason: "Writes outside ~/code/ require manual approval"
```

**Allow a whole MCP namespace:**
```yaml
allow:
  - name: github-reads
    tool: '^mcp__github__(get_|list_|search_)'
    matches:
      - {}                                  # no input constraints
```

**Defer to a downstream policy hook for sensitive paths:**
```yaml
defer:
  - name: sensitive-area
    tool: 'Write|Edit'
    matches:
      - file_path: '^/Users/me/sensitive-area/'
    reason: "Hand off to the policy-enforcement hook"
```

For deeper coverage (regex tips, debugging via the audit log, advanced patterns), see [`references/schema.md`](references/schema.md).
