# zettel-sync

**Turn what you explored into what you remember.**

Maintain a structured Obsidian vault (Zettelkasten-style) from your recent Claude Code sessions. One
command harvests the technical concepts you actually dug into, checks them
against your vault, and produces a single batched-approval review document —
you approve once, and a separate `apply` step writes the result.

Built around your vault's own philosophy: **curation over accumulation**. Drafts
land in `inbox/` for you to promote; existing notes are never modified
automatically.

## Features

### Skills

- **zettel-sync** - Analyze sessions + vault and write a review doc; `apply` to write approved items

### Capabilities

- **Concept harvest**: scans the last N days of sessions across all projects,
  distilling a bounded prose digest (raw transcripts never flood context)
- **Vault-aware**: reads your `_templates/_schema.md` at runtime — convention is
  never hardcoded, so it survives schema changes
- **Orphan detection**: finds atomic notes with no incoming links
- **MOC gaps**: flags tags shared by ≥5 notes with no Map of Content
- **Near-duplicate detection**: title+body similarity scoring proposes merges
- **inbox-first & safe**: only ever creates files in `inbox/`; merges, orphan
  links, and reciprocal edits are surfaced as *suggestions*, never auto-applied
- **Batched approval**: one editable checklist; uncheck what you don't want
- **Idempotent**: a state file prevents re-proposing concepts you declined

## Installation

### Requirements

- **Python 3** in `$PATH` (for the harvest/graph scripts)
- **[uv](https://docs.astral.sh/uv/)** in `$PATH` — provides `uvx`, which launches
  the bundled MCP server (or edit `.mcp.json` to use your own launcher)
- **Obsidian** running with the
  [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api)
  plugin enabled

```bash
/plugin install zettel-sync@agent-extentions
```

This plugin **bundles its own Obsidian MCP server** (`mcp-obsidian`) via
`.mcp.json` — no manual MCP wiring needed. You only need to set the API key.

### Environment variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `OBSIDIAN_API_KEY` | **yes** | — | Copy from the Local REST API plugin's settings |
| `OBSIDIAN_HOST` | no | `127.0.0.1` | Host of the Local REST API |
| `OBSIDIAN_PORT` | no | `27124` | HTTPS port of the Local REST API |
| `OBSIDIAN_VAULT_PATH` | no | auto | Vault root for the on-disk structural scan; auto-detected from Obsidian's `obsidian.json` when unset |
| `NO_PROXY` / `no_proxy` | no | `127.0.0.1,localhost` | Bypass any HTTP proxy for the local API |

Export the key before launching Claude Code (e.g. in your shell profile):

```bash
export OBSIDIAN_API_KEY="<your-local-rest-api-key>"
```

## Usage

```bash
/zettel-sync                 # analyze + write _artifacts/zettel-sync/zettel-sync-<date>.md
/zettel-sync --days 14       # widen the scan window (default 7)
/zettel-sync --dry-run       # print proposals to chat, write nothing
/zettel-sync apply           # write all still-checked Apply items to inbox/
```

Typical loop: run `/zettel-sync`, open the review doc in Obsidian, uncheck
anything you don't want, then run `/zettel-sync apply`. Promote notes from
`inbox/` into `notes/` yourself — that's where your synthesis happens.

### CLI Options

| Flag | Description |
|------|-------------|
| `apply` | Write the still-checked items from the latest review doc |
| `--days N` | Look back N days of sessions (default: 7) |
| `--dry-run` | Print proposals to chat instead of writing the review doc |

## License

MIT

## Vault structure

`zettel-sync` expects an Obsidian vault shaped roughly like this:

```
vault/
├── notes/                  # atomic notes   (frontmatter: type: note)
├── moc/                    # Maps of Content (frontmatter: type: moc)
├── inbox/                  # new drafts land here (auto-created)
├── _templates/_schema.md   # your frontmatter contract (read at runtime)
└── _artifacts/zettel-sync/ # review docs + state (auto-created)
```

Required vs. flexible:

- **Classification is by frontmatter `type:`, not folder.** `notes/` and `moc/`
  are just the default scan dirs — override with `vault_graph.py --dirs a,b`
  (e.g. `--dirs .` for a flat vault), as long as notes carry `type: note` /
  `type: moc`.
- **`inbox/` and `_artifacts/zettel-sync/` are fixed write targets**, both
  auto-created on first run — you don't have to make them.
- **`_templates/_schema.md` is optional** — without it, the frontmatter
  convention is inferred from a few existing notes.
