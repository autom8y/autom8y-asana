#!/bin/bash
# PostToolUse (Bash) hook - track git commits to session
# Fires on all Bash calls, filters for git commit operations
# Logs commits to $SESSION_DIR/commits.log and updates SESSION_CONTEXT.md

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Source logging library (optional)
source "$SCRIPT_DIR/lib/logging.sh" 2>/dev/null && log_init "commit-tracker" && log_start || true

# Read JSON input from stdin
INPUT=$(cat)

# Extract tool details
if command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
  TOOL_COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
  TOOL_OUTPUT=$(echo "$INPUT" | jq -r '.tool_output // empty' 2>/dev/null)
else
  # Fallback: grep-based parsing
  TOOL_NAME=$(echo "$INPUT" | grep -o '"tool_name": *"[^"]*"' 2>/dev/null | head -1 | cut -d'"' -f4)
  TOOL_COMMAND=$(echo "$INPUT" | grep -o '"command": *"[^"]*"' 2>/dev/null | head -1 | cut -d'"' -f4)
  TOOL_OUTPUT=$(echo "$INPUT" | grep -o '"tool_output": *"[^"]*"' 2>/dev/null | head -1 | cut -d'"' -f4)
fi

# Only process Bash tool with git commit commands
if [[ "$TOOL_NAME" != "Bash" ]]; then
  exit 0
fi

# Check if this is a git commit command
if [[ ! "$TOOL_COMMAND" =~ git[[:space:]]+commit ]]; then
  exit 0
fi

# Check if commit succeeded (output contains commit hash pattern)
# Pattern: "[branch hash] message" OR "create mode" lines
if [[ ! "$TOOL_OUTPUT" =~ \[[^]]+[[:space:]][a-f0-9]+\] ]]; then
  # Commit may have failed or was aborted
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

# Source session utilities
source .claude/hooks/lib/session-utils.sh 2>/dev/null || exit 0

SESSION_DIR=$(get_session_dir)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SHORT_TIME=$(date +"%H:%M")

# Only track if session exists
if [ -z "$SESSION_DIR" ] || [ ! -d "$SESSION_DIR" ]; then
  # No session active - commit still works, just not tracked
  exit 0
fi

# Extract commit hash and message from git output
# Format: "[branch hash] message"
COMMIT_LINE=$(echo "$TOOL_OUTPUT" | grep -E '^\[[^]]+\]' | head -1)
if [ -z "$COMMIT_LINE" ]; then
  exit 0
fi

# Parse: [branch hash] message
COMMIT_HASH=$(echo "$COMMIT_LINE" | sed 's/^\[[^]]*[[:space:]]\([a-f0-9]*\)\].*/\1/')
COMMIT_MSG=$(echo "$COMMIT_LINE" | sed 's/^\[[^]]*\][[:space:]]*//')

# Truncate message for log (50 chars max)
COMMIT_MSG_SHORT="${COMMIT_MSG:0:50}"

# Log to commits.log
COMMITS_LOG="$SESSION_DIR/commits.log"
echo "$TIMESTAMP | COMMIT | $COMMIT_HASH | $COMMIT_MSG_SHORT" >> "$COMMITS_LOG"

# Update SESSION_CONTEXT.md with commit reference
SESSION_CONTEXT="$SESSION_DIR/SESSION_CONTEXT.md"
if [ -f "$SESSION_CONTEXT" ]; then
  # Check if Commits section exists
  if grep -q "^## Commits" "$SESSION_CONTEXT" 2>/dev/null; then
    # Append to existing Commits table
    # Find the table and append row after header
    sed -i.bak "/^## Commits/,/^## [^C]/{
      /^| Time/a\\
| $SHORT_TIME | $COMMIT_HASH | $COMMIT_MSG_SHORT |
    }" "$SESSION_CONTEXT" 2>/dev/null && rm -f "$SESSION_CONTEXT.bak"
  else
    # Create Commits section before next ## or at end
    # Insert after ## Artifacts section
    if grep -q "^## Artifacts" "$SESSION_CONTEXT" 2>/dev/null; then
      sed -i.bak "/^## Artifacts/,/^## /{
        /^## [^A]/i\\
\\
## Commits\\
<!-- Auto-updated by commit-tracker.sh -->\\
| Time | Hash | Message |\\
|------|------|---------|\\
| $SHORT_TIME | $COMMIT_HASH | $COMMIT_MSG_SHORT |\\

      }" "$SESSION_CONTEXT" 2>/dev/null && rm -f "$SESSION_CONTEXT.bak"
    else
      # Append at end
      cat >> "$SESSION_CONTEXT" <<COMMITS

## Commits
<!-- Auto-updated by commit-tracker.sh -->
| Time | Hash | Message |
|------|------|---------|
| $SHORT_TIME | $COMMIT_HASH | $COMMIT_MSG_SHORT |
COMMITS
    fi
  fi
fi

echo "{\"systemMessage\": \"Commit tracked: $COMMIT_HASH\"}"
log_end 0 2>/dev/null || true
exit 0
