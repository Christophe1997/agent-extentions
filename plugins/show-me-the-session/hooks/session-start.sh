#!/bin/bash
# Capture session ID at session start and persist it for the export command.
# The session ID is stored as SMTS_SESSION_ID in $CLAUDE_ENV_FILE so it is
# available as an environment variable throughout the session.

set -euo pipefail

input=$(cat)
session_id=$(echo "$input" | jq -r '.session_id // empty')

if [ -n "$session_id" ] && [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export SMTS_SESSION_ID='$session_id'" >> "$CLAUDE_ENV_FILE"
fi
