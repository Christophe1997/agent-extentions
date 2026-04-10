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

If missing, tell the user:

> The `a2a` CLI is required. Install it with:
> ```bash
> go install github.com/a2aproject/a2a-go/v2/cmd/a2a@main
> ```
> Then re-run `/a2a:onboard`.

Stop here if binary is missing.

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

## Step 4: Save alias

Use `AskUserQuestion` to offer saving the alias:

```json
{
  "questions": [
    {
      "question": "Save this agent as an alias for future use?",
      "header": "Save alias",
      "multiSelect": false,
      "options": [
        {
          "label": "Yes — save alias",
          "description": "Add a short name so you can use it instead of the full URL."
        },
        {
          "label": "No — skip",
          "description": "Continue without saving. You can always add it manually later."
        }
      ]
    }
  ]
}
```

If **Yes**, ask for the alias name:

```json
{
  "questions": [
    {
      "question": "Enter a short alias name (e.g. \"my-agent\", \"staging\", \"billing\"):",
      "header": "Alias name",
      "multiSelect": false,
      "options": [
        { "label": "Enter custom name", "description": "Type your preferred alias in the Other field." }
      ]
    }
  ]
}
```

Store the chosen alias as `ALIAS`.

## Step 5: Auth capture

Only ask if auth was **not already present** in AUTH_ARGS (i.e. the auth step returned nothing):

Use `AskUserQuestion`:

```json
{
  "questions": [
    {
      "question": "Does this agent require authentication?",
      "header": "Auth",
      "multiSelect": false,
      "options": [
        {
          "label": "Yes — add auth token",
          "description": "Store a Bearer token or custom header for this agent's URL."
        },
        {
          "label": "No auth needed",
          "description": "Agent is public or auth is handled elsewhere."
        }
      ]
    }
  ]
}
```

If **Yes**, ask for the auth value:

```json
{
  "questions": [
    {
      "question": "Enter auth as key=value (e.g. \"Authorization=Bearer eyJhbGci...\", \"X-API-Key=abc123\"):",
      "header": "Auth value",
      "multiSelect": false,
      "options": [
        { "label": "Enter auth value", "description": "Paste your auth param in the Other field." }
      ]
    }
  ]
}
```

Store as `AUTH_ENTRY` (a single `k=v` string). If the user pastes a raw token without a key prefix, wrap it: `Authorization=Bearer <token>`.

## Step 6: Write settings file

Now write the gathered config. There are three cases:

### Case A: No settings file exists (`SETTINGS_STATUS` = `missing`) and user saved alias or auth

Create `SETTINGS_PATH` with content:

```markdown
---
agents:
  <ALIAS>: "<URL>"

auth:
  "<URL-prefix>":
    - "<AUTH_ENTRY>"
---

# A2A Client Settings
Configure your A2A agent connections here.
```

- Omit the `agents:` block if no alias was saved.
- Omit the `auth:` block if no auth was captured.
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
