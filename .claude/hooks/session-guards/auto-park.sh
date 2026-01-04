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

# Source session utilities and FSM
safe_source "$HOOKS_LIB/session-utils.sh" || exit 0
safe_source "$HOOKS_LIB/session-fsm.sh" || exit 0

SESSION_DIR=$(get_session_dir)
SESSION_FILE="$SESSION_DIR/SESSION_CONTEXT.md"

# Only act if session exists
if [ -z "$SESSION_DIR" ] || [ ! -f "$SESSION_FILE" ]; then
  hooks_finalize 0
  exit 0
fi

# FIXED (Hook-FSM Coordination): Use FSM transition instead of direct write
# Get session ID from directory name
session_id=$(basename "$SESSION_DIR")

# Attempt FSM transition to PARKED state
result=$(fsm_transition "$session_id" "PARKED" '{"reason":"Session stopped (auto-park)","auto":true}' 2>/dev/null)

# Check result - if already parked or transition failed, silently continue
if [[ "$result" != *'"success": true'* ]]; then
  # FSM transition failed - may already be parked or archived
  # This is acceptable - degrade gracefully per RECOVERABLE category
  hooks_finalize 0
  exit 0
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
