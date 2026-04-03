# show-me-the-session

**Code is cheap, show me the session**

Export Claude Code session transcripts to solarized-light themed HTML with pagination support. Inspired by [simonw/claude-code-transcripts](https://github.com/simonw/claude-code-transcripts).

## Features

### Skills

| Skill | Description |
|---------|-------------|
| `smts:export` | Export current session to HTML |

### Capabilities

- **Auto session detection**: Automatically finds the current session by project path
- **Split output**: Large sessions can be split into multiple HTML pages with navigation
- **Self-contained HTML**: All CSS/JS inline, no external dependencies
- **Solarized Light theme**: Comfortable reading with the classic color scheme
- **Rich content rendering**: User messages, assistant text, thinking blocks, tool calls, tool results
- **Keyboard navigation**: Arrow keys navigate between pages in split mode

## Examples

See a [live example](https://christophe1997.github.io/agent-extentions/examples/2ffa0a3c-fd83-4161-bbb9-336f8a0b4705.html).

## Installation

### Requirements

- Python 3 in `$PATH`

```bash
/plugin install show-me-the-session@agent-extentions
```

## Usage

```bash
/smts:export                    # Export current session to docs/sessions/
/smts:export pick               # Choose from recent sessions
/smts:export -o /path/out.html  # Custom output path
/smts:export --split            # Split into multiple pages
/smts:export --split --page-size 30  # Custom page size
```

### CLI Options

| Flag | Description |
|------|-------------|
| `pick` | Choose from recent sessions instead of auto-detecting |
| `-o, --output PATH` | Custom output path (file or directory for split mode) |
| `--split` | Split large sessions into multiple HTML files with index |
| `--page-size N` | Messages per page when splitting (default: 50) |

## License

MIT
