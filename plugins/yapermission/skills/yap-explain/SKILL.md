---
name: yap-explain
description: Dry-run a tool call against the active yapermission policy and report which rule matched and why. Trigger when the user asks to test/debug/trace a yapermission rule, check whether a command would be auto-approved or blocked, or understand why a yapermission decision happened.
argument-hint: 'Bash "git status"  |  Edit /etc/hosts  |  <Tool> <json> [--verbose]'
allowed-tools: Bash
---

# Explain a yapermission decision

Run the policy engine in dry-run mode against a hypothetical tool call so the user can debug their rules without actually invoking the tool.

## Argument format

The user invokes this with: `<tool_name> <arguments...> [--verbose] [--session <session_id>]`

Translate the friendly form into the JSON `tool_input` the engine expects:

| Tool | User typed | tool_input JSON |
|---|---|---|
| `Bash` | `Bash git status` | `{"command":"git status"}` |
| `Edit` / `Write` | `Edit /etc/hosts` | `{"file_path":"/etc/hosts"}` |
| `Read` | `Read /Users/me/x.py` | `{"file_path":"/Users/me/x.py"}` |
| MCP tools | `mcp__github__list_issues {"owner":"foo"}` | pass the trailing JSON as-is |
| Anything else | `<Tool> <json>` | use the trailing argument as JSON |

If the user passes raw JSON as the second+ argument (starts with `{`), use it directly.

If `--verbose` appears anywhere in the arguments, pass `--verbose` to the engine to get the per-rule trace.

If `--session <session_id>` appears anywhere in the arguments, pass it through to the engine so it also reports live cache state for that session.

## Process

1. **Invoke the engine in dry-run mode**:

   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/yapermission.py explain [--verbose] [--session <session_id>] <tool_name> '<tool_input_json>'
   ```

2. **Read the output**: The script prints:
   - `cwd:` and `config:` (which TOML is active)
   - The matched rule name + reason, or `decision: ask` if nothing matched
   - With `--verbose`: a per-rule "matched" / "skipped" trace
   - `cache:` — without `--session`, reports that cache state wasn't checked; with `--session`, reports a cache hit or "no matching cache entry" for that session

3. **Report verbatim**: Show the output to the user verbatim. If the script exits non-zero, surface the stderr message and stop.

## Example Usage

```
/yapermission:yap-explain Bash "git push --force"
/yapermission:yap-explain Bash "git status"
/yapermission:yap-explain Edit /etc/hosts
/yapermission:yap-explain Read /Users/me/x.py
/yapermission:yap-explain mcp__github__list_issues {"owner":"foo"}
/yapermission:yap-explain Bash "git push" --verbose
/yapermission:yap-explain Bash "git status" --session S1
```

## Common follow-ups

- If the user asks "why didn't *X* match?", re-run with `--verbose` and walk through the trace.
- If `config:` is `(none — every call falls through to ask)`, suggest running `/yapermission:yap-onboard` to scaffold one.
- The engine reads from the **current working directory** to find a project config, so cd-ing somewhere else changes which policy is active.
