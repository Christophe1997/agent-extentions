# show-me-the-session

Export a Claude Code session JSONL transcript to a single self-contained solarized-light HTML page.

## Architecture

```
show-me-the-session/
├── commands/export.md          # /show-me-the-session:export [pick]
├── scripts/generate-html.py    # JSONL → HTML converter (Python 3 stdlib only)
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

System tags (`<system-reminder>`, `<local-command-caveat>`, etc.) are stripped via `strip_system_tags()`.

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
- **Python 3 stdlib only**: No pip install needed, works on any macOS/Linux
- **Simple markdown renderer**: Regex-based (bold, italic, code, links, fenced blocks) — avoids `markdown` library dependency
- **Title extraction**: First meaningful user prompt (skips slash commands and short strings)
- **Truncation**: Content >250px collapses with "Show more" button, gradient fade per parent background
