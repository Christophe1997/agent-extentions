---
name: a2a:discover
description: Fetches and displays the Agent Card for an A2A agent at a given URL or alias. Resolves aliases from settings and applies auth params.
argument-hint: <url-or-alias> [--extended]
allowed-tools: Bash
---

Parse `$ARGUMENTS`:
- `URL_OR_ALIAS`: the first non-flag token
- `EXTENDED`: true if `--extended` is present (add `--extended` flag to the command)

Check that `a2a` is installed before proceeding:

```bash
if ! command -v a2a &>/dev/null; then
  echo "Error: 'a2a' CLI not found. Install with:"
  echo "  go install github.com/a2aproject/a2a-go/v2/cmd/a2a@main"
  exit 1
fi
```

Resolve the URL and fetch the agent card:

```bash
URL=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" resolve "$URL_OR_ALIAS")
AUTH_ARGS=()
while IFS= read -r line; do
  AUTH_ARGS+=("$line")
done < <(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" auth "$URL")
a2a discover "$URL" "${AUTH_ARGS[@]}"          # append --extended if EXTENDED is true
```

Display the agent card output. Then offer to save this agent as an alias — show the exact
YAML snippet to add to `.claude/a2a.local.md`:

```yaml
agents:
  <chosen-alias>: "<url>"
```
