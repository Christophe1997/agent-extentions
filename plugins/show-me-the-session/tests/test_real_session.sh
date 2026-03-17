#!/usr/bin/env bash
# Test against a real Claude Code session, comparing with claude-code-transcripts reference output
# Usage: bash tests/test_real_session.sh [session_file]

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
GENERATOR="$PLUGIN_DIR/scripts/generate-html.py"

# Use provided session or find one
if [ $# -gt 0 ]; then
    SESSION="$1"
else
    CWD_SLUG=$(echo "$PWD" | sed 's|^/||; s|/|-|g')
    SESSION_DIR="$HOME/.claude/projects/-${CWD_SLUG}"
    SESSION=$(ls -t "$SESSION_DIR"/*.jsonl 2>/dev/null | grep -v '/agent-' | head -1)
    if [ -z "$SESSION" ]; then
        echo "No session file found. Usage: $0 <session.jsonl>"
        exit 1
    fi
fi

echo "Session: $SESSION"
echo "Size: $(du -h "$SESSION" | cut -f1)"

OUR_OUTPUT="/tmp/test-real-our.html"
REF_DIR="/tmp/test-real-ref"

PASS=0
FAIL=0

assert_true() {
    local label="$1"
    local result="$2"
    if [ "$result" = "true" ]; then
        echo "  PASS: $label"
        PASS=$((PASS+1))
    else
        echo "  FAIL: $label"
        FAIL=$((FAIL+1))
    fi
}

# Generate our output
echo ""
echo "=== Generating our HTML ==="
python3 "$GENERATOR" "$SESSION" "$OUR_OUTPUT"

# Generate reference output
echo "=== Generating reference HTML ==="
if command -v uvx &>/dev/null; then
    rm -rf "$REF_DIR"
    uvx claude-code-transcripts json "$SESSION" -o "$REF_DIR" 2>&1 | head -5
else
    echo "SKIP: uvx not available, skipping reference comparison"
    exit 0
fi

echo ""
echo "=== Test: Output exists ==="
assert_true "our output exists" "$([ -f "$OUR_OUTPUT" ] && echo true || echo false)"

echo ""
echo "=== Test: Content fidelity ==="
# Count key elements via regex
our_thinking=$(grep -c 'class="thinking' "$OUR_OUTPUT" 2>/dev/null || echo 0)
ref_thinking=$(grep -c 'class="thinking' "$REF_DIR"/page-*.html 2>/dev/null || echo 0)
assert_true "thinking block count matches ($our_thinking vs $ref_thinking)" \
    "$([ "$our_thinking" = "$ref_thinking" ] && echo true || echo false)"

our_tool_use=$(grep -c 'class="tool-use' "$OUR_OUTPUT" 2>/dev/null || echo 0)
ref_tool_use=$(grep -c 'class="tool-use' "$REF_DIR"/page-*.html 2>/dev/null || echo 0)
assert_true "tool-use block count matches ($our_tool_use vs $ref_tool_use)" \
    "$([ "$our_tool_use" = "$ref_tool_use" ] && echo true || echo false)"

our_tool_result=$(grep -c 'class="tool-result' "$OUR_OUTPUT" 2>/dev/null || echo 0)
ref_tool_result=$(grep -c 'class="tool-result' "$REF_DIR"/page-*.html 2>/dev/null || echo 0)
assert_true "tool-result block count matches ($our_tool_result vs $ref_tool_result)" \
    "$([ "$our_tool_result" = "$ref_tool_result" ] && echo true || echo false)"

our_assistant=$(grep -c 'class="message assistant"' "$OUR_OUTPUT" 2>/dev/null || echo 0)
ref_assistant=$(grep -c 'class="message assistant"' "$REF_DIR"/page-*.html 2>/dev/null || echo 0)
assert_true "assistant message count matches ($our_assistant vs $ref_assistant)" \
    "$([ "$our_assistant" = "$ref_assistant" ] && echo true || echo false)"

echo ""
echo "=== Test: Single file ==="
our_size=$(wc -c < "$OUR_OUTPUT")
assert_true "output is single file (not zero)" "$([ "$our_size" -gt 1000 ] && echo true || echo false)"

echo ""
echo "=== Test: Solarized theme present ==="
assert_true "solarized colors in output" \
    "$(grep -q '#fdf6e3' "$OUR_OUTPUT" && echo true || echo false)"

echo ""
echo "=== Test: No external dependencies ==="
assert_true "no CDN links" \
    "$(grep -qv 'cdn\.\|unpkg\.\|googleapis' "$OUR_OUTPUT" && echo true || echo false)"

echo ""
echo "==============================="
echo "Results: $PASS passed, $FAIL failed"
echo "==============================="
echo ""
echo "Our output: $OUR_OUTPUT ($(du -h "$OUR_OUTPUT" | cut -f1))"
echo "Reference:  $REF_DIR/ ($(du -sh "$REF_DIR" | cut -f1))"

[ "$FAIL" -gt 0 ] && exit 1 || exit 0
