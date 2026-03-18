# show-me-the-session

**Code is cheap, show me the session**

Export Claude Code session transcripts to solarized-light themed HTML with pagination support. It's inspired by [simonw/claude-code-transcripts](https://github.com/simonw/claude-code-transcripts).

## Examples

See a [simple example transcripts](https://christophe1997.github.io/agent-extentions/examples/2ffa0a3c-fd83-4161-bbb9-336f8a0b4705.html).

## Features

- **Auto session detection**: Automatically finds the current session by project path
- **Split output**: Large sessions can be split into multiple HTML pages with navigation
- **Configurable page size**: Control how many messages per page
- **Self-contained HTML**: All CSS/JS inline, no external dependencies
- **Solarized Light theme**: Comfortable reading with the classic color scheme
- **Rich content rendering**: User messages, assistant text, thinking blocks, tool calls, tool results
- **Collapsible sections**: Long content is truncatable with "Show more" buttons
- **Keyboard navigation**: Arrow keys navigate between pages in split mode

## Usage

```
/show-me-the-session:export                    # Export current session to docs/sessions/
/show-me-the-session:export pick               # Choose from recent sessions
/show-me-the-session:export -o /path/out.html  # Custom output path
/show-me-the-session:export --split            # Split into multiple pages
/show-me-the-session:export --split --page-size 30  # Custom page size
```

### CLI Options

| Flag | Description |
|------|-------------|
| `pick` | Choose from recent sessions instead of auto-detecting |
| `-o, --output PATH` | Custom output path (file or directory for split mode) |
| `--split` | Split large sessions into multiple HTML files with index |
| `--page-size N` | Messages per page when splitting (default: 50) |

## Requirements

- Python3 in the $PATH 

## Installation

```
/plugin install show-me-the-session@agent-extentions
```
