---
name: yap:onboard
description: Scaffold the global yapermission config at ~/.yapermission.toml from a bundled template. Two templates are offered — `starter` (default-ask, conservative) and `yolo` (default-allow with hard guardrails). Trigger when the user asks to set up yapermission, initialize the policy file, or create a starter/yolo yapermission config.
allowed-tools: Bash, Read, Write
---

# Onboard yapermission

Scaffold `~/.yapermission.toml` from one of the bundled templates so the user has a heavily-commented policy file to edit.

## Templates

| Template | File | Mode | When to choose |
|---|---|---|---|
| `starter` | `${CLAUDE_PLUGIN_ROOT}/scripts/starter.toml` | `default = "ask"` — broad allow rules + targeted asks/denies; unmatched calls prompt | Default choice. Conservative, low-blast-radius, fail-safe. |
| `yolo` | `${CLAUDE_PLUGIN_ROOT}/scripts/yolo.toml` | `default = "allow"` — comprehensive deny list + ask list; unmatched calls auto-run | Trusted dev environments, autonomous loops, sandbox/worktree work. Faster but the deny list is the only safety net. |

## Process

1. **Check whether the file already exists.**

   Run: `test -f ~/.yapermission.toml && echo EXISTS || echo MISSING`

2. **If it exists**, show the user the current top-level structure (just the keys, not the full content) and ask whether to overwrite, back up first, or abort. Wait for confirmation.

   To preview keys only: `grep -E '^(default|\[\[(deny|ask|allow|defer)\]\])' ~/.yapermission.toml || true`

   If user chooses backup: `cp ~/.yapermission.toml ~/.yapermission.toml.bak`

3. **Ask which template** — use AskUserQuestion to present the choice. Recommend `starter` as the default unless the user already used "yolo" / "default-allow" / "permissive" terminology in their request.

   ```
   Question: "Which template?"
   Header: "Template"
   Options:
     - "starter (default-ask, conservative) (Recommended)"
       description: "Asks for confirmation on anything not explicitly allowed. Safer default."
     - "yolo (default-allow with deny-list)"
       description: "Allows anything not denied/asked. Faster but the deny list is your only guardrail."
   ```

4. **Copy the chosen template.**

   - `starter` → `cp ${CLAUDE_PLUGIN_ROOT}/scripts/starter.toml ~/.yapermission.toml`
   - `yolo` → `cp ${CLAUDE_PLUGIN_ROOT}/scripts/yolo.toml ~/.yapermission.toml`

5. **Confirm and orient the user.** Print:
   - The full path of the new file (`~/.yapermission.toml`)
   - The active mode: `default = "ask"` (starter) or `default = "allow"` (yolo)
   - For yolo only: a one-line warning that the deny list is the only guardrail and any new dangerous tool added in future Claude Code versions won't be auto-blocked.
   - That they can run `/yapermission:yap-explain <Tool> <args>` to dry-run a tool call against the active policy
   - That they should restart Claude Code for the hook config to take effect (hooks load at session start)

## Notes

- Do not edit the file's contents during onboarding — let the user do that. The templates are intentionally over-commented.
- A project-level `./.yapermission.toml` replaces the global file wholesale; this skill only touches the global file.
- **Project-level yolo is often safer than global yolo.** If the user wants default-allow, suggest copying `yolo.toml` to `./.yapermission.toml` in a single trusted directory rather than installing it as global. That way the conservative global config still applies everywhere else.
- **Python 3.11+ required** — yapermission uses `tomllib` from the standard library. On older Pythons the hook will error on import.
