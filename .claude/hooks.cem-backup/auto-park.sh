#!/bin/bash
# Stop hook - auto-save session state when Claude stops
# Adds auto_parked_at timestamp if session exists and not already parked

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || true

# Source session utilities
source .claude/hooks/lib/session-utils.sh 2>/dev/null

SESSION_DIR=$(get_session_dir)
SESSION_FILE="$SESSION_DIR/SESSION_CONTEXT.md"

# Only act if session exists
if [ -z "$SESSION_DIR" ] || [ ! -f "$SESSION_FILE" ]; then
  exit 0
fi

# Check if already parked (manual or auto)
if grep -q "^parked_at:" "$SESSION_FILE" 2>/dev/null; then
  exit 0
fi
if grep -q "^auto_parked_at:" "$SESSION_FILE" 2>/dev/null; then
  exit 0
fi

# Add auto-park timestamp to frontmatter
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Find the second --- (end of frontmatter) and insert before it
awk -v ts="$TIMESTAMP" '
  /^---$/ && ++count == 2 {
    print "auto_parked_at: " ts
    print "auto_parked_reason: \"Session stopped (auto-park)\""
  }
  { print }
' "$SESSION_FILE" > "${SESSION_FILE}.tmp" && mv "${SESSION_FILE}.tmp" "$SESSION_FILE"

# Output message for Claude
echo '{"systemMessage": "Session auto-saved. Use /continue to resume."}'

exit 0
