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
   - Run the session lister script:
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/list-sessions.py"
     ```
   - Each output line is tab-separated: `date \t project-slug \t first-message \t /full/path`
   - Use AskUserQuestion to present each session as `[date] project: first message…`
   - From the chosen entry take the last tab field as `SESSION_FILE` and the second field as `PROJECT_DIR`

   Otherwise (default: auto-detect current session):
   - **Locate the session file**:
     ```bash
     # Convert cwd to the project directory slug
     # e.g., /Users/user/code/myproject -> -Users-user-code-myproject
     PROJECT_DIR=$(echo "$CWD" | sed 's|^/||; s|/|-|g' | sed 's|^|-|')

     # Try the session ID captured at session start (set by SessionStart hook)
     SESSION_ID="${SMTS_SESSION_ID:-}"
     if [ -n "$SESSION_ID" ]; then
       SESSION_FILE=$(ls ~/.claude/projects/${PROJECT_DIR}/${SESSION_ID}.jsonl 2>/dev/null | head -1)
     fi

     # Fallback: most recently modified non-agent JSONL in the project directory
     if [ -z "${SESSION_FILE:-}" ]; then
       SESSION_FILE=$(ls -t ~/.claude/projects/${PROJECT_DIR}/*.jsonl 2>/dev/null | grep -v '/agent-' | head -1)
     fi
     ```

3. **Determine output path**:

   If `-o` was specified:
   - Use the provided path

   Otherwise:
   - Default output directory: `docs/sessions/` (create if needed)
   - Default filename: `<session-id>.html` (or `<session-id>-pages/` for split mode)
   - Ask user: "Export session to `docs/sessions/<session-id>.html`? [Y/n]"

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

## Important Notes

- The generated HTML is fully self-contained (inline CSS + JS, no external dependencies)
- Uses the Solarized Light color scheme for comfortable reading
- All content blocks are rendered: user messages, assistant text, thinking (collapsible), tool calls, tool results
- Long content sections are truncatable with "Show more" buttons
- Split mode creates keyboard navigation (arrow keys) between pages
- Timestamps are converted to local time via JavaScript
