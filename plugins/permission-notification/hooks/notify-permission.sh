#!/bin/bash
# Send macOS notification when Claude Code needs permission
# Receives JSON via stdin with tool_name and tool_input

set -euo pipefail

# Read JSON input
input=$(cat)

# Extract tool name
tool_name=$(echo "$input" | jq -r '.tool_name // "unknown"')

# Build notification message based on tool type
case "$tool_name" in
  Bash)
    # Extract the command being executed
    command=$(echo "$input" | jq -r '.tool_input.command // "unknown command"')
    # Truncate long commands
    if [ ${#command} -gt 80 ]; then
      command="${command:0:80}..."
    fi
    message="Bash: $command"
    ;;
  Write|Edit)
    file_path=$(echo "$input" | jq -r '.tool_input.file_path // "unknown file"')
    message="$tool_name: $file_path"
    ;;
  *)
    message="Tool: $tool_name"
    ;;
esac

# Detect terminal app bundle ID from TERM_PROGRAM environment variable
TERM_BUNDLE_ID="${TERMINAL_BUNDLE_ID:-}"

if [ -z "$TERM_BUNDLE_ID" ]; then
  case "${TERM_PROGRAM:-}" in
    WarpTerminal) TERM_BUNDLE_ID="dev.warp.Warp-Stable" ;;
    iTerm.app|iTerm2) TERM_BUNDLE_ID="com.googlecode.iterm2" ;;
    Terminal.app) TERM_BUNDLE_ID="com.apple.Terminal" ;;
    Alacritty) TERM_BUNDLE_ID="io.alacritty" ;;
    Kitty) TERM_BUNDLE_ID="net.kovidgoyal.kitty" ;;
    *) TERM_BUNDLE_ID="com.apple.Terminal" ;;  # Fallback
  esac
fi

# Send macOS notification using terminal-notifier (click focuses terminal)
terminal-notifier \
  -title "Claude Code - Permission Required" \
  -message "$message" \
  -activate "$TERM_BUNDLE_ID" \
  2>/dev/null || true

exit 0
