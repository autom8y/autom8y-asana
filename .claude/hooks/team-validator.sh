#!/bin/bash
# PreToolUse (Bash) hook - validate team operations and auto-approve slash command patterns
# - Auto-approves safe bash patterns used in slash commands
# - Validates team switch operations
# - Blocks invalid team names, warns on session/team mismatch

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Source logging library
source "$SCRIPT_DIR/lib/logging.sh" 2>/dev/null && log_init "team-validator" && log_start || true

# Read JSON input from stdin
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Helper function to output permission decision
auto_approve() {
  local reason="$1"
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "$reason"
  }
}
EOF
  exit 0
}

# Auto-approve safe patterns used in slash commands
# These are read-only operations used for context injection

# List operations (ls)
if [[ "$COMMAND" =~ ^ls[[:space:]] ]] || [[ "$COMMAND" == "ls" ]]; then
  auto_approve "Safe ls command for context"
fi

# Git read operations
if [[ "$COMMAND" =~ ^git[[:space:]]+(status|branch|log|diff|symbolic-ref|rev-list|rev-parse|remote|config|show) ]]; then
  auto_approve "Safe git read command for context"
fi

# GitHub CLI read operations
if [[ "$COMMAND" =~ ^gh[[:space:]]+(pr|issue)[[:space:]]+(list|view|status) ]]; then
  auto_approve "Safe gh read command for context"
fi

# Cat for reading files
if [[ "$COMMAND" =~ ^cat[[:space:]] ]]; then
  auto_approve "Safe cat command for context"
fi

# Head/tail for reading files
if [[ "$COMMAND" =~ ^(head|tail)[[:space:]] ]]; then
  auto_approve "Safe head/tail command for context"
fi

# Test/existence checks
if [[ "$COMMAND" =~ ^test[[:space:]] ]] || [[ "$COMMAND" =~ ^\[[[:space:]] ]]; then
  auto_approve "Safe test command for context"
fi

# Sed for text processing (typically used with pipes from git)
if [[ "$COMMAND" =~ ^sed[[:space:]] ]]; then
  auto_approve "Safe sed command for context"
fi

# Echo for output
if [[ "$COMMAND" =~ ^echo[[:space:]] ]]; then
  auto_approve "Safe echo command for context"
fi

# Piped commands starting with safe operations
if [[ "$COMMAND" =~ ^(git|gh|ls|cat|head|tail)[[:space:]].*\| ]]; then
  auto_approve "Safe piped command for context"
fi

# Only validate actual swap-team.sh invocations (not mentions in commit messages, etc.)
# Must be at start of command or after a path separator, not embedded in quoted strings
if [[ ! "$COMMAND" =~ (^|[[:space:]/])swap-team\.sh[[:space:]] ]]; then
  exit 0
fi

# Extract target team from command
# Handles: swap-team.sh teamname, ~/Code/roster/swap-team.sh teamname
# The regex ensures we're matching an actual invocation, not text in a string
TARGET_TEAM=$(echo "$COMMAND" | grep -oE '(^|[[:space:]/])swap-team\.sh[[:space:]]+([a-z0-9-]+-pack)' | grep -oE '[a-z0-9-]+-pack')

# Skip validation for --list or no argument
if [ -z "$TARGET_TEAM" ] || [ "$TARGET_TEAM" = "--list" ]; then
  exit 0
fi

# Validate team pack exists
# Note: ROSTER_HOME is defined in config.sh (sourced via logging.sh)
ROSTER_DIR="$ROSTER_HOME/teams"
if [ ! -d "$ROSTER_DIR/$TARGET_TEAM" ]; then
  echo "Team pack '$TARGET_TEAM' not found in $ROSTER_DIR" >&2
  echo "Available teams:" >&2
  ls -1 "$ROSTER_DIR" 2>/dev/null | sed 's/^/  - /' >&2
  exit 2  # Block the command
fi

# Validate team has agents
AGENT_COUNT=$(find "$ROSTER_DIR/$TARGET_TEAM/agents/" -maxdepth 1 -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
if [ "$AGENT_COUNT" = "0" ]; then
  echo "Team pack '$TARGET_TEAM' has no agent files" >&2
  exit 2  # Block the command
fi

# Warn on session/team mismatch (don't block, just warn)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || true

# Source session utilities for proper path resolution
source .claude/hooks/lib/session-utils.sh 2>/dev/null || true

# Get session directory using multi-session architecture
SESSION_DIR=$(get_session_dir 2>/dev/null)
SESSION_FILE="${SESSION_DIR:+$SESSION_DIR/SESSION_CONTEXT.md}"

if [ -n "$SESSION_FILE" ] && [ -f "$SESSION_FILE" ]; then
  SESSION_TEAM=$(grep -m1 "^active_team:" "$SESSION_FILE" 2>/dev/null | cut -d: -f2- | tr -d ' "')
  if [ -n "$SESSION_TEAM" ] && [ "$SESSION_TEAM" != "$TARGET_TEAM" ]; then
    echo "{\"systemMessage\": \"Note: Session was started with '$SESSION_TEAM', switching to '$TARGET_TEAM'\"}"
  fi
fi

# Warn on worktree/team mismatch (don't block, just warn)
if is_worktree 2>/dev/null; then
  WORKTREE_TEAM=$(get_worktree_field team 2>/dev/null)
  if [ -n "$WORKTREE_TEAM" ] && [ "$WORKTREE_TEAM" != "none" ] && [ "$WORKTREE_TEAM" != "$TARGET_TEAM" ]; then
    cat <<EOF
{
  "systemMessage": "Warning: Worktree team mismatch. This worktree was created for '$WORKTREE_TEAM' but switching to '$TARGET_TEAM'. Consider using main project for different team."
}
EOF
  fi
fi

log_end 0 2>/dev/null || true
exit 0
