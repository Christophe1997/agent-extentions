---
name: export
description: Export the current Claude Code session as a solarized-light themed HTML page
argument-hint: "[pick] to choose from recent sessions"
allowed-tools: [Bash, Read, Glob, AskUserQuestion]
---

Export the current Claude Code session transcript to a single self-contained HTML file with a solarized-light theme, then open it in the browser.

## Process

1. **Determine the session file**:

   If the user provided the argument `pick`:
   - List recent JSONL sessions from `~/.claude/projects/`:
     ```bash
     find ~/.claude/projects/ -name '*.jsonl' -not -name 'agent-*' -newer ~/.claude/projects/ -maxdepth 3 | head -20
     ```
   - Use AskUserQuestion to let the user choose from the list (show filename + first user message preview + file size)

   Otherwise (default: auto-detect current session):
   - Find the most recently modified `.jsonl` file in `~/.claude/projects/` that matches the current working directory path:
     ```bash
     # Convert cwd to Claude's project folder name format (replace / with -)
     CWD_SLUG=$(echo "$PWD" | sed 's|^/||; s|/|-|g')
     SESSION_DIR="$HOME/.claude/projects/-${CWD_SLUG}"
     # Find most recent non-agent session
     ls -t "$SESSION_DIR"/*.jsonl 2>/dev/null | grep -v '/agent-' | head -1
     ```
   - If no session found, inform the user and suggest using `pick` argument

2. **Generate the HTML**:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/generate-html.py" "<session_file>" "/tmp/session-export-$(date +%s).html"
   ```

3. **Open in browser**:
   ```bash
   open "<output_file>"
   ```

4. **Report to user**: Tell them the output file path and that it's been opened in their browser.

## Important Notes

- The generated HTML is fully self-contained (inline CSS + JS, no external dependencies)
- Uses the Solarized Light color scheme for comfortable reading
- All content blocks are rendered: user messages, assistant text, thinking (collapsible), tool calls, tool results
- Long content sections are truncatable with "Show more" buttons
- Timestamps are converted to local time via JavaScript
