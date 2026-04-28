---
name: yap-rule-syntax
description: Reference for the yapermission YAML rule schema and evaluation order. Trigger when the user asks how to write a yapermission rule, the yapermission yaml format or schema, how to auto-approve git commands or shell utilities, how to block rm -rf or other dangerous commands, what the deny/approve/default fields mean, or how project and global yapermission configs interact.
---

# yapermission rule syntax

A yapermission policy is a single YAML file with up to three top-level keys: `default`, `deny`, `approve`.

## Top-level shape

```yaml
default: ask              # approve | block | ask  (ask = pass-through to normal prompt)

deny:                     # list of rules; first match wins; evaluated FIRST
  - { ... rule ... }

approve:                  # list of rules; first match wins; evaluated SECOND
  - { ... rule ... }
```

If neither a `deny` rule nor an `approve` rule matches, `default` applies. Missing `default` means `ask`.

## Rule shape

```yaml
- name: short-identifier              # appears in audit log; required for clarity
  tool: Bash                          # regex matched against tool name; missing = match any
  matches:                            # list of input-pattern entries (REQUIRED)
    - command: '^git (status|log)\b'  # all fields in this entry must match (AND)
    - command: '^ls\b'                # any entry that matches makes the rule fire (OR)
  reason: "Read-only operations"      # shown to Claude on deny; logged on approve
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
   │ approve  │ ─────────────►│ return allow │
   └────┬─────┘                └──────────────┘
        │ no match
        ▼
   ┌──────────┐
   │ default  │
   └──────────┘
```

## Config resolution

1. If `./.yapermission.yaml` exists in the cwd, it is the **only** active config (replaces global).
2. Otherwise, `~/.yapermission.yaml` is used.
3. Otherwise, every call falls through to Claude Code's normal permission prompt.
4. If the active YAML fails to parse, the hook logs the error and falls back to `ask` (fail-open).

## Cookbook

**Auto-approve read-only git:**
```yaml
approve:
  - name: safe-git-reads
    tool: Bash
    matches:
      - command: '^git (status|log|diff|branch|show|remote)\b'
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
approve:
  - name: github-reads
    tool: '^mcp__github__(get_|list_|search_)'
    matches:
      - {}                                  # no input constraints
```

For deeper coverage (regex tips, debugging via the audit log, advanced patterns), see [`references/schema.md`](references/schema.md).
