---
name: a2a:onboard
description: Onboards a new A2A agent connection — fetches the Agent Card, checks prerequisites, and guides through saving the alias and configuring authentication. Use when the user wants to "discover", "onboard", "add", "register", or "connect" an A2A agent, or provides an agent URL they want to start using. Also triggers on "what can this agent do?" or "check the agent at <url>".
argument-hint: <url-or-alias> [--extended]
allowed-tools: Bash, Read, Write, AskUserQuestion
---

Parse `$ARGUMENTS`:
- `URL_OR_ALIAS`: the first non-flag token
- `EXTENDED`: true if `--extended` is present

## Step 1: Prerequisites check

Before anything else, verify the `a2a` binary is installed:

```bash
command -v a2a &>/dev/null && echo "ok" || echo "missing"
```

If missing, use `AskUserQuestion`:

```json
{
  "questions": [
    {
      "question": "The `a2a` CLI is not installed. Install it now with `go install github.com/a2aproject/a2a-go/v2/cmd/a2a@latest`?",
      "header": "Install a2a CLI",
      "multiSelect": false,
      "options": [
        {
          "label": "Yes — install now",
          "description": "Run the install command automatically and continue onboarding."
        },
        {
          "label": "No — exit",
          "description": "Stop here. You can install manually and re-run /a2a:onboard later."
        }
      ]
    }
  ]
}
```

- If **Yes**, run:
  ```bash
  go install github.com/a2aproject/a2a-go/v2/cmd/a2a@latest
  ```
  Then verify `command -v a2a` succeeds before continuing. If install fails, report the error and stop.
- If **No**, stop here with:
  > Onboarding cancelled. Install `a2a` with `go install github.com/a2aproject/a2a-go/v2/cmd/a2a@latest` and re-run `/a2a:onboard`.

## Step 2: Locate settings file

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" find-settings
```

This prints either `found:<path>` or `missing:<preferred-path>`. Store the result:
- `SETTINGS_STATUS`: `found` or `missing`
- `SETTINGS_PATH`: the path after the colon

## Step 3: Resolve and discover

```bash
URL=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" resolve "$URL_OR_ALIAS")
AUTH_ARGS=()
while IFS= read -r line; do
  AUTH_ARGS+=("$line")
done < <(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a2a-helper.py" auth "$URL")
a2a discover "$URL" ${EXTENDED:+--extended} "${AUTH_ARGS[@]}"
```

Display the agent card output clearly.

After displaying, extract `SUGGESTED_ALIAS` from the agent name in the card: lowercase, spaces replaced with hyphens, non-alphanumeric characters removed (e.g. "Change Agent" → `change-agent`).

## Step 4: Save alias

Use `AskUserQuestion` with `SUGGESTED_ALIAS` as a pre-filled option:

```json
{
  "questions": [
    {
      "question": "Save this agent as an alias? Select the suggested name or type your own:",
      "header": "Alias name",
      "multiSelect": false,
      "options": [
        {
          "label": "<SUGGESTED_ALIAS>",
          "description": "Derived from the agent's name. Select to use this."
        },
        {
          "label": "Skip — no alias",
          "description": "Continue without saving. You can always add it manually later."
        }
      ]
    }
  ]
}
```

- If the user selects `<SUGGESTED_ALIAS>`: store it as `ALIAS`.
- If the user types a custom name in the **Other** field: store it as `ALIAS`.
- If the user selects **Skip — no alias**: leave `ALIAS` empty.

## Step 5: Auth capture

Only ask if auth was **not already present** in AUTH_ARGS (i.e. the auth step returned nothing):

Use `AskUserQuestion` to ask for the token in one step:

```json
{
  "questions": [
    {
      "question": "Paste your Bearer token (e.g. \"Bearer eyJhbGci...\" or just \"eyJhbGci...\"). The Bearer prefix is added automatically if omitted.",
      "header": "Auth token",
      "multiSelect": false,
      "options": [
        {
          "label": "Skip — no auth needed",
          "description": "Agent is public or auth is handled elsewhere."
        },
        {
          "label": "Bearer <token>",
          "description": "Type or paste your token in the Type something field — Bearer prefix is optional."
        }
      ]
    }
  ]
}
```

- If the user types a token in the **Other** field: normalise into `AUTH_ENTRY`:
  - Starts with `Bearer ` (case-insensitive): `AUTH_ENTRY=Authorization=<input>`
  - Otherwise: `AUTH_ENTRY=Authorization=Bearer <input>`
- If the user selects **Skip — no auth needed**: leave `AUTH_ENTRY` empty.

## Step 6: Write settings file

Now write the gathered config. Settings are always preferred in this order:
1. **Local** — `.claude/a2a.local.md` in the current project directory (project-scoped, git-ignored)
2. **Global** — `~/.claude/a2a.local.md` (user-wide fallback)

`find-settings` already returns the local path as the preferred creation target when no file exists.

There are three cases:

### Case A: No settings file exists (`SETTINGS_STATUS` = `missing`) and user saved alias or auth

Create `SETTINGS_PATH` with content:

```markdown
---
agents:
  <ALIAS>: "<URL>"

auth:
  "<URL-prefix>":
    - "<AUTH_ENTRY>"

timeout: "120s"
---

# A2A Client Settings
Configure your A2A agent connections here.
```

- Omit the `agents:` block if no alias was saved.
- Omit the `auth:` block if no auth was captured.
- Always include `timeout: "120s"` — the CLI default (30s) is too short for most agents.
- Use the URL **without trailing path segments beyond the base** as the auth key prefix (e.g. for `https://api.example.com/a2a/v1`, use `https://api.example.com` as the key).

### Case B: Settings file exists (`SETTINGS_STATUS` = `found`) and user saved alias or auth

Read `SETTINGS_PATH`, then show the user exactly what YAML to add:

> Add to your settings file at `SETTINGS_PATH`:
>
> Under `agents:`:
> ```yaml
>   <ALIAS>: "<URL>"
> ```
>
> Under `auth:` (create section if missing):
> ```yaml
>   "<URL-prefix>":
>     - "<AUTH_ENTRY>"
> ```
>
> If no `timeout:` key exists yet, add:
> ```yaml
> timeout: "120s"
> ```

Do **not** auto-write to an existing settings file — the user's existing config may have formatting or comments to preserve.

### Case C: Nothing to save (no alias, no auth)

No file write needed. Inform the user that onboarding is complete and they can add config manually via `SETTINGS_PATH`.

## Step 7: Confirm

Summarise what was done:

- Agent card fetched from `<URL>`
- Alias `<ALIAS>` → `<URL>` (or "no alias saved")
- Auth configured for `<URL-prefix>` (or "no auth saved")
- Settings file: created at `<SETTINGS_PATH>` / updated manually / no changes needed

Suggest the next step:
> Send a message with `/a2a:send <alias-or-url> "your message"`
