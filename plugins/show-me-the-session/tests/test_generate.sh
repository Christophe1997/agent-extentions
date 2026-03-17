#!/usr/bin/env bash
# Red/Green/Refactor test suite for show-me-the-session HTML generator
# Usage: bash tests/test_generate.sh

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
GENERATOR="$PLUGIN_DIR/scripts/generate-html.py"
FIXTURE="$SCRIPT_DIR/fixture.jsonl"
OUTPUT="/tmp/test-session-export.html"

PASS=0
FAIL=0

assert_contains() {
    local label="$1"
    local needle="$2"
    local haystack="$3"
    if echo "$haystack" | grep -qF "$needle"; then
        echo "  PASS: $label"
        PASS=$((PASS+1))
    else
        echo "  FAIL: $label"
        echo "    Expected to find: $needle"
        FAIL=$((FAIL+1))
    fi
}

assert_not_contains() {
    local label="$1"
    local needle="$2"
    local haystack="$3"
    if echo "$haystack" | grep -qF "$needle"; then
        echo "  FAIL: $label"
        echo "    Expected NOT to find: $needle"
        FAIL=$((FAIL+1))
    else
        echo "  PASS: $label"
        PASS=$((PASS+1))
    fi
}

assert_regex() {
    local label="$1"
    local pattern="$2"
    local haystack="$3"
    if echo "$haystack" | grep -qE "$pattern"; then
        echo "  PASS: $label"
        PASS=$((PASS+1))
    else
        echo "  FAIL: $label"
        echo "    Expected to match: $pattern"
        FAIL=$((FAIL+1))
    fi
}

# --- Generate HTML ---
echo "=== Generating HTML from fixture ==="
if ! python3 "$GENERATOR" "$FIXTURE" "$OUTPUT"; then
    echo "FATAL: Generator script failed"
    exit 2
fi
HTML=$(cat "$OUTPUT")

echo ""
echo "=== Test: HTML Structure ==="
assert_contains "has DOCTYPE" "<!DOCTYPE html>" "$HTML"
assert_contains "has html lang" '<html lang="en">' "$HTML"
assert_contains "has charset" '<meta charset="UTF-8">' "$HTML"
assert_contains "has viewport meta" "viewport" "$HTML"
assert_contains "has style tag" "<style>" "$HTML"
assert_contains "has script tag" "<script>" "$HTML"
assert_contains "is single file (no external CSS)" "</style>" "$HTML"
assert_not_contains "no framework imports" "cdn.jsdelivr" "$HTML"
assert_not_contains "no framework imports 2" "unpkg.com" "$HTML"

echo ""
echo "=== Test: Solarized Light Theme ==="
# Solarized light base colors
assert_contains "solarized base3 bg (#fdf6e3)" "#fdf6e3" "$HTML"
assert_contains "solarized base00 text (#657b83)" "#657b83" "$HTML"
assert_contains "solarized base01 (#586e75)" "#586e75" "$HTML"

echo ""
echo "=== Test: User Messages ==="
assert_contains "user message text" "Hello, can you help me fix a bug?" "$HTML"
assert_contains "user message 2" "Thanks, that looks great!" "$HTML"
assert_contains "user role label" "User" "$HTML"

echo ""
echo "=== Test: Assistant Text ==="
assert_contains "assistant text" "Sure! Let me look at the code first." "$HTML"
assert_contains "assistant fix message" "hello world" "$HTML"
assert_contains "assistant role label" "Assistant" "$HTML"

echo ""
echo "=== Test: Thinking Blocks ==="
assert_contains "thinking content" "Let me think about this bug fix request." "$HTML"
assert_contains "thinking label" "Thinking" "$HTML"
assert_regex "thinking is collapsible" "<details|data-collapsed" "$HTML"

echo ""
echo "=== Test: Tool Use Blocks ==="
assert_contains "bash tool name" "Bash" "$HTML"
assert_contains "bash command" "cat src/main.py" "$HTML"
assert_contains "tool description" "Read the main source file" "$HTML"
assert_contains "read tool name" "Read" "$HTML"
assert_contains "edit tool name" "Edit" "$HTML"
assert_contains "edit old string" "print(&#x27;world&#x27;)" "$HTML"

echo ""
echo "=== Test: Tool Results ==="
assert_contains "tool result content" "def hello():" "$HTML"
assert_contains "file edit success" "File edited successfully" "$HTML"

echo ""
echo "=== Test: Timestamps ==="
assert_regex "has timestamp data attr" "data-timestamp" "$HTML"
assert_contains "timestamp value" "2026-03-10T10:00:00.000Z" "$HTML"

echo ""
echo "=== Test: Collapsible Sections ==="
assert_regex "has expand/collapse mechanism" "details|truncatable|expand-btn|data-collapsed" "$HTML"

echo ""
echo "=== Test: Markdown in Assistant Text ==="
assert_regex "bold rendered" "<strong>|<b>" "$HTML"
assert_regex "inline code rendered" "<code>" "$HTML"

echo ""
echo "==============================="
echo "Results: $PASS passed, $FAIL failed"
echo "==============================="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
