# show-me-the-session

Export the current Claude Code session as a single solarized-light themed HTML page.

## Features

- Generates a self-contained HTML file (no external dependencies)
- Solarized Light theme for comfortable reading
- Renders all content blocks: user messages, assistant text, thinking, tool calls, tool results
- Collapsible sections for long content
- Auto-detects current session or lets you pick from recent sessions
- Opens directly in your browser

## Usage

```
/show-me-the-session:export         # Export current session
/show-me-the-session:export pick    # Choose from recent sessions
```

## Requirements

- Python 3 (included with macOS)

## Installation

```
/plugin install show-me-the-session@agent-extentions
```
