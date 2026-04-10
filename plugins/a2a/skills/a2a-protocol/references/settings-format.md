# A2A Settings Format

Create `.claude/a2a.local.md` in the **project root** — the directory where Claude Code is
launched (the one that contains `.claude/`). This file is gitignored automatically.

## Minimal Example (one alias, no auth)

```markdown
---
agents:
  my-agent: "https://my-agent.example.com/a2a"
---
```

## Full Example

```markdown
---
# Agent aliases: short name -> full URL
agents:
  my-agent: "https://my-agent.example.com/a2a"
  local: "http://localhost:8080"
  staging: "https://staging.example.com/api/a2a"

# Auth params per URL prefix: list of k=v strings passed as --svc-param
# IMPORTANT: URL keys must be quoted (double quotes) — bare URLs break YAML parsing
auth:
  "https://my-agent.example.com":
    - "Authorization=Bearer eyJhbGci..."
    - "X-Tenant-ID=my-org"
  "https://staging.example.com":
    - "Authorization=Bearer staging-token"

# Default request timeout (applies to all agents unless overridden)
# Accepts Go duration strings: 30s, 2m, 90s, etc. Default is 30s.
timeout: "60s"

# Per-URL timeout overrides (same longest-prefix matching as auth)
timeouts:
  "https://slow-agent.example.com": "120s"
---

# A2A Client Settings
Configure your A2A agent connections here.
```

## Notes

- **`agents`**: maps alias names to full base URLs. A raw URL passed where an alias is expected
  is returned unchanged — no error is raised for unknown aliases.
- **`auth`**: keys are URL prefixes. **Longest-prefix matching** applies: only the single most
  specific matching prefix is used. For example, `https://api.example.com/v2` takes priority
  over `https://api.example.com` when both are configured.
  **URL keys containing colons (`:`) must be quoted** — e.g. `"http://localhost:8000"` not
  `http://localhost:8000`. Unquoted URL keys will be misparsed.
- Each auth entry is a `k=v` string passed verbatim as `--svc-param k=v`. Multiple entries
  for one prefix are all passed (repeatable `--svc-param`).
- **Do NOT use HTTP header syntax** (`--header "Authorization: Bearer ..."`) — the `a2a` CLI
  uses `--svc-param`, not `--header`. The correct format is always `Key=Value`, e.g.
  `Authorization=Bearer eyJhbGci...` (no space after the `=`, key is the header name).
- `--auth <creds>` is shorthand only for the `Authorization` header. Any other header
  (e.g. `X-Tenant-ID`) must be specified as a full `k=v` auth entry.
- **`timeout`**: global default timeout for all `a2a send` calls. Accepts Go duration strings
  (`30s`, `2m`, `90s`). The CLI default is `30s` if not set.
- **`timeouts`**: per-URL timeout overrides using the same longest-prefix matching as `auth`.
- The settings file is never committed (`.gitignore` covers `.claude/*.local.md`).

## Saving a New Alias

After discovering an agent at a URL, add it to the `agents:` section manually:

```yaml
agents:
  <chosen-alias>: "<full-url>"
```
