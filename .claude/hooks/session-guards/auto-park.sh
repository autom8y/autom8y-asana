#!/bin/bash
# Stop hook - auto-save session state when Claude stops
# Category: RECOVERABLE - can detect errors but must degrade gracefully
# Adds auto_parked_at timestamp if session exists and not already parked

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Library Resolution - per ADR-0002
HOOKS_LIB="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/lib"
source "$HOOKS_LIB/hooks-init.sh"
hooks_init "auto-park" "RECOVERABLE"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || true

# Source session utilities
safe_source "$HOOKS_LIB/session-utils.sh" || exit 0

SESSION_DIR=$(get_session_dir)
SESSION_FILE="$SESSION_DIR/SESSION_CONTEXT.md"

# Only act if session exists
if [ -z "$SESSION_DIR" ] || [ ! -f "$SESSION_FILE" ]; then
  hooks_finalize 0
  exit 0
fi

# Check if already parked (manual or auto)
if grep -q "^parked_at:" "$SESSION_FILE" 2>/dev/null; then
  hooks_finalize 0
  exit 0
fi
if grep -q "^auto_parked_at:" "$SESSION_FILE" 2>/dev/null; then
  hooks_finalize 0
  exit 0
fi

# Add auto-park timestamp to frontmatter
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Generate updated content with auto-park fields inserted before closing ---
UPDATED_CONTENT=$(awk -v ts="$TIMESTAMP" '
  /^---$/ && ++count == 2 {
    print "auto_parked_at: " ts
    print "auto_parked_reason: \"Session stopped (auto-park)\""
  }
  { print }
' "$SESSION_FILE")

# Write atomically using session-utils function (prevents STATE-004 corruption)
if ! atomic_write "$SESSION_FILE" "$UPDATED_CONTENT"; then
  echo '{"error": "Failed to auto-park session: atomic write failed"}' >&2
  exit 1
fi

# Output message for Claude
if is_worktree 2>/dev/null; then
  WORKTREE_ID=$(get_worktree_field worktree_id 2>/dev/null)
  echo "{\"systemMessage\": \"Session auto-saved in worktree $WORKTREE_ID. Use /continue to resume or /worktree remove $WORKTREE_ID to cleanup.\"}"
else
  echo '{"systemMessage": "Session auto-saved. Use /continue to resume."}'
fi

hooks_finalize 0
exit 0
