---
name: export
description: Export the current Claude Code session as a solarized-light themed HTML page
argument-hint: "[pick] [-o PATH] [--split] [--page-size N]"
allowed-tools: [Bash, Read, Glob, AskUserQuestion]
---

Export the current Claude Code session transcript to a single self-contained HTML file with a solarized-light theme, then open it in the browser.

## CLI Options

| Flag | Description |
|------|-------------|
| `pick` | Choose from recent sessions instead of auto-detecting |
| `-o, --output PATH` | Custom output path (file or directory for split mode) |
| `--split` | Split large sessions into multiple HTML files with index |
| `--page-size N` | Messages per page when splitting (default: 50) |

## Process

1. **Parse arguments**: Extract any flags from the user's input:
   - Look for `-o` or `--output` followed by a path
   - Look for `--split` flag
   - Look for `--page-size` followed by a number
   - Check for `pick` keyword

2. **Determine the session file**:

   If `pick` was specified:
   - List recent JSONL sessions from `~/.claude/projects/`:
     ```bash
     find ~/.claude/projects/ -name '*.jsonl' -not -name 'agent-*' -type f -mtime -7 | head -20
     ```
   - Use AskUserQuestion to let the user choose from the list

   Otherwise (default: auto-detect current session):
   - **Get the current session ID**:
   - Use `/status` to get and extract current session id, which begin with `Session ID:`, use it as the `${SESSION_ID}` bellow 
     ```bash
     # Convert cwd to the project directory slug
     # e.g., /Users/user/code/myproject -> -Users-user-code-myproject
     PROJECT_DIR=$(echo "$CWD" | sed 's|^/||; s|/|-|g' | sed 's|^|-|')

     # Find the JSONL file matching the session ID
     SESSION_FILE=$(ls ~/.claude/projects/-${PROJECT_DIR}/${SESSION_ID}.jsonl 2>/dev/null | head -1)
     ```

   - If session file not found, fall back to most recent file in project directory:
     ```bash
     ls -t ~/.claude/projects/-${PROJECT_DIR}/*.jsonl 2>/dev/null | grep -v '/agent-' | head -1
     ```

3. **Determine output path**:

   If `-o` was specified:
   - Use the provided path

   Otherwise:
   - Default output directory: `doc/sessions/` (create if needed)
   - Default filename: `<session-id>.html` (or `<session-id>-pages/` for split mode)
   - Ask user: "Export session to `doc/sessions/<session-id>.html`? [Y/n]"

4. **Check message count and suggest split for large sessions**:

   Count messages in the session:
   ```bash
   wc -l "$SESSION_FILE"
   ```

   If message count > 100 and `--split` was NOT specified:
   - Ask user: "This session has X messages. Split into multiple pages for easier viewing? [y/N]"
   - If yes, enable split mode

5. **Generate the HTML**:

   For single HTML:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/generate-html.py" "$SESSION_FILE" -o "$OUTPUT_PATH"
   ```

   For split HTML:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/generate-html.py" "$SESSION_FILE" -o "$OUTPUT_DIR" --split --page-size "$PAGE_SIZE"
   ```

6. **Open in browser**:
   ```bash
   open "$OUTPUT_PATH"  # or open "$OUTPUT_DIR/index.html" for split mode
   ```

7. **Report to user**: Tell them the output path and that it's been opened in their browser.

## Session Detection Details

The session tracking files in `~/.claude/sessions/` are named by process PID and contain:
- `sessionId`: The UUID of the current session
- `cwd`: The current working directory
- `pid`: The process ID
- `startedAt`: Unix timestamp when session started

The most recently modified session file corresponds to the current active session.

## Important Notes

- The generated HTML is fully self-contained (inline CSS + JS, no external dependencies)
- Uses the Solarized Light color scheme for comfortable reading
- All content blocks are rendered: user messages, assistant text, thinking (collapsible), tool calls, tool results
- Long content sections are truncatable with "Show more" buttons
- Split mode creates keyboard navigation (arrow keys) between pages
- Timestamps are converted to local time via JavaScript
