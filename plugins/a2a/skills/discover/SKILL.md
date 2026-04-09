---
name: a2a-discover
description: >
  Fetch and display the Agent Card for an A2A agent at a given URL or alias.
  User-invocable as /a2a:discover. Resolves aliases from settings, applies auth params.
argument-hint: '<url-or-alias> [--extended]'
disable-model-invocation: true
allowed-tools: Bash(python3:*), Bash(a2a:*)
---

Resolve the URL and fetch the agent card:

```bash
URL=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" resolve "$ARGUMENTS_BEFORE_FLAGS")
AUTH=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" auth "$URL")
a2a discover "$URL" $AUTH $EXTENDED_FLAG
```

Parse `$ARGUMENTS`:
- If `--extended` is present, add `--extended` to the command and strip it from the URL argument.
- The first non-flag token is the URL or alias.

Output the agent card. Then offer the user the option to save this agent as an alias in
`.claude/a2a.local.md` — show the exact YAML snippet they need to add.
