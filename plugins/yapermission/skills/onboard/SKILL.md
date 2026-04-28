---
name: onboard
description: Scaffold the global yapermission config at ~/.yapermission.yaml from the bundled starter template. Trigger when the user runs /yapermission:onboard or asks to set up yapermission, initialize the policy file, or create a starter yapermission config.
allowed-tools: Bash, Read, Write
---

# Onboard yapermission

Scaffold a starter `~/.yapermission.yaml` from the bundled template so the user has a heavily-commented policy file to edit.

## Steps

1. **Check whether the file already exists.**

   Run: `test -f ~/.yapermission.yaml && echo EXISTS || echo MISSING`

2. **If it exists**, show the user the current top-level structure (just the keys, not the full content) and ask whether to overwrite, back up first, or abort. Wait for confirmation.

   To preview keys only: `grep -E '^(default|deny|approve):' ~/.yapermission.yaml || true`

   If user chooses backup: `cp ~/.yapermission.yaml ~/.yapermission.yaml.bak`

3. **Copy the starter template.**

   Run: `cp ${CLAUDE_PLUGIN_ROOT}/scripts/starter.yaml ~/.yapermission.yaml`

4. **Confirm and orient the user.** Print:
   - The full path of the new file (`~/.yapermission.yaml`)
   - That `default: ask` is set (every unmatched call falls through to the normal prompt)
   - That they can run `/yapermission:explain <Tool> <args>` to dry-run a tool call against the active policy
   - That they should restart Claude Code for the hook config to take effect (hooks load at session start)

## Notes

- Do not edit the file's contents during onboarding — let the user do that. The template is intentionally over-commented.
- A project-level `./.yapermission.yaml` replaces the global file wholesale; this skill only touches the global file.
- If the user wants a project-level file instead, copy the same starter to `./.yapermission.yaml` and remind them the project file *replaces* the global, it does not merge.
