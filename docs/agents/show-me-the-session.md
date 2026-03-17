# show-me-the-session

Export Claude Code session JSONL transcripts to solarized-light HTML with pagination support.

## Architecture

```
show-me-the-session/
├── commands/export.md          # /show-me-the-session:export [pick] [-o PATH] [--split]
├── hooks/
│   ├── hooks.json              # SessionStart hook registration
│   └── session-start.sh        # Captures session ID → $SMTS_SESSION_ID env var
├── scripts/
│   ├── generate-html.py        # JSONL → HTML converter (Python 3 stdlib only)
│   ├── list-sessions.py        # List recent sessions with first-message preview (pick mode)
│   └── templates/
│       ├── style.css           # Solarized Light CSS (inlined into HTML output)
│       ├── script.js           # Timestamp/truncation/keyboard JS (inlined)
│       ├── page.html           # Single-page shell template
│       ├── split-page.html     # Per-page shell template (split mode)
│       └── index.html          # Index shell template (split mode)
└── tests/
    ├── fixture.jsonl            # Synthetic 12-message test session
    ├── test_generate.sh         # 34 assertions: structure, theme, content blocks
    └── test_real_session.sh     # Reference comparison vs claude-code-transcripts
```

## How It Works

`generate-html.py` reads a session JSONL file line-by-line, parsing each JSON object into one of these message types:

| JSONL `type` | `role` | `content` | Rendered as |
|---|---|---|---|
| `user` | `user` | `string` | Blue-accented user message |
| `assistant` | `assistant` | `[{type:"text"}]` | Assistant message with markdown |
| `assistant` | `assistant` | `[{type:"thinking"}]` | Collapsible `<details>` block |
| `assistant` | `assistant` | `[{type:"tool_use"}]` | Specialized tool card (Bash/Read/Write/Edit/Grep/Glob) |
| `user` | `user` | `[{type:"tool_result"}]` | Yellow-accented tool reply |
| `file-history-snapshot` | — | — | Skipped |

System tags (`<system-reminder>`, `<local-command-caveat>`, `<command-name>`, etc.) are stripped via `strip_system_tags()`.

## Session Detection

### Auto-detect (default)

The export command resolves the current session in two steps:

1. **`$SMTS_SESSION_ID` env var** (set by the `SessionStart` hook at session start) — used to locate the exact `~/.claude/projects/<project>/<session-id>.jsonl` file.
2. **Fallback** — if the env var is absent (first session after install, or Claude Code version without `SessionStart` support), picks the most recently modified non-agent JSONL in the project directory.

### Pick mode (`pick` argument)

`list-sessions.py` scans `~/.claude/projects/` for recent sessions (default: last 30 days, up to 20 results) and outputs tab-separated lines:

```
date<TAB>project-slug<TAB>first-user-message<TAB>/full/path/to/session.jsonl
```

Claude presents these as human-readable options via `AskUserQuestion` (`[date] project: first message…`) and derives both `SESSION_FILE` and `PROJECT_DIR` from the chosen entry.

## CLI Options

| Flag | Description |
|------|-------------|
| `session_file` | Path to the session JSONL file (required) |
| `-o, --output PATH` | Output path (file for single HTML, directory for split mode) |
| `--split` | Split output into multiple HTML files with index |
| `--page-size N` | Messages per page when splitting (default: 50) |

## Split Mode

When `--split` is enabled, the generator creates:
- `index.html`: Navigation page listing all pages with message ranges
- `page-1.html`, `page-2.html`, ...: Individual pages with pagination controls

Features:
- Keyboard navigation (arrow keys) between pages
- Each page is a complete, self-contained HTML document
- Consistent styling and stats across all pages

## Solarized Light Theme

All colors use CSS variables mapped to the [Solarized](https://ethanschoonover.com/solarized/) palette:

- Background: `--base3` (#fdf6e3), Alt: `--base2` (#eee8d5)
- Text: `--base00` (#657b83), Emphasis: `--base01` (#586e75)
- Accents: `--blue` (#268bd2) for user, `--violet` (#6c71c4) for tools, `--yellow` (#b58900) for thinking/replies
- Code blocks: `--base02` (#073642) dark background

## Testing

```bash
# Fixture tests (34 assertions)
bash plugins/show-me-the-session/tests/test_generate.sh

# Real session comparison against claude-code-transcripts
bash plugins/show-me-the-session/tests/test_real_session.sh [session.jsonl]
```

## Key Design Decisions

- **Single file output**: All CSS/JS inline — no external dependencies, no framework imports
- **Python 3 stdlib only**: No pip install needed, works on any macOS/Linux (`subprocess` used in `list-sessions.py` to call `find`)
- **Template separation**: CSS/JS/HTML shells live in `scripts/templates/`; loaded once at startup via `Path(__file__).parent / "templates"` and inlined into output — output files remain fully self-contained
- **Simple markdown renderer**: Regex-based (bold, italic, code, links, fenced blocks) — avoids `markdown` library dependency
- **Title extraction**: First meaningful user prompt (skips slash commands and short strings)
- **Truncation**: Content >250px collapses with "Show more" button, gradient fade per parent background
- **Split mode**: For large sessions, creates paginated output with keyboard navigation
