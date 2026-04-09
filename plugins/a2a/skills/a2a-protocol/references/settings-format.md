# A2A Settings Format

Create `.claude/a2a.local.md` in your project root (gitignored):

```markdown
---
# Agent aliases: short name -> full URL
agents:
  my-agent: "https://my-agent.example.com/a2a"
  local: "http://localhost:8080"
  staging: "https://staging.example.com/api/a2a"

# Auth params per URL prefix: list of k=v strings passed as --svc-param
auth:
  "https://my-agent.example.com":
    - "Authorization=Bearer eyJhbGci..."
    - "X-Tenant-ID=my-org"
  "https://staging.example.com":
    - "Authorization=Bearer staging-token"
---

# A2A Client Settings
Configure your A2A agent connections here.
```

## Notes

- `agents` maps alias names to full base URLs.
- `auth` keys are URL prefixes — **longest-prefix matching**: only the single most specific matching prefix is applied.
- Each auth entry is a `k=v` string passed verbatim as `--svc-param k=v` to the CLI.
- Multiple auth entries for one URL are all passed (repeatable `--svc-param`).
- The settings file is never committed (`.gitignore` covers `.claude/*.local.md`).

## Saving an Alias

When the user runs `/a2a:discover` and wants to save the agent as an alias, instruct them to add
an entry under `agents:` in `.claude/a2a.local.md`.
