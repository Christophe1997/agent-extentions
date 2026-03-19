#!/bin/bash
# Capture session ID at session start and persist it for the export command.
# The session ID is stored as SMTS_SESSION_ID in $CLAUDE_ENV_FILE so it is
# available as an environment variable throughout the session.

set -euo pipefail

input=$(cat)
session_id=$(echo "$input" | jq -r '.session_id // empty')
project_dir=$(echo "$input" | jq -r '.cwd // empty')

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  [ -n "$session_id" ] && echo "export SMTS_SESSION_ID='$session_id'" >> "$CLAUDE_ENV_FILE"
  [ -n "$project_dir" ] && echo "export SMTS_PROJECT_DIR='$project_dir'" >> "$CLAUDE_ENV_FILE"
fi
