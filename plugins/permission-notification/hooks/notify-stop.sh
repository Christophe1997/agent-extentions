#!/bin/bash
# Send macOS notification when Claude Code stops (task complete)

set -euo pipefail

# Detect terminal app bundle ID from TERM_PROGRAM environment variable
TERM_BUNDLE_ID="${TERMINAL_BUNDLE_ID:-}"

if [ -z "$TERM_BUNDLE_ID" ]; then
  case "${TERM_PROGRAM:-}" in
    WarpTerminal) TERM_BUNDLE_ID="dev.warp.Warp-Stable" ;;
    iTerm.app|iTerm2) TERM_BUNDLE_ID="com.googlecode.iterm2" ;;
    Terminal.app) TERM_BUNDLE_ID="com.apple.Terminal" ;;
    Alacritty) TERM_BUNDLE_ID="io.alacritty" ;;
    Kitty) TERM_BUNDLE_ID="net.kovidgoyal.kitty" ;;
    *) TERM_BUNDLE_ID="com.apple.Terminal" ;;
  esac
fi

# Send macOS notification (click focuses terminal)
terminal-notifier \
  -title "Claude Code - Done" \
  -message "Waiting for your input" \
  -activate "$TERM_BUNDLE_ID" \
  2>/dev/null || true

exit 0
