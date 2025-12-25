#!/bin/bash
# PostToolUse (Write) hook - track artifact creation
# Detects PRD/TDD/ADR/TP files and logs to session-specific artifacts.log

# Read JSON input from stdin
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# Exit silently if no file path
if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Detect artifact type from path pattern
case "$FILE_PATH" in
  */docs/requirements/PRD-*.md) TYPE="PRD" ;;
  */docs/design/TDD-*.md) TYPE="TDD" ;;
  */docs/design/ADR-*.md) TYPE="ADR" ;;
  */docs/test/TP-*.md) TYPE="Test Plan" ;;
  *) exit 0 ;;  # Not a tracked artifact
esac

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || true

# Source session utilities
source .claude/hooks/lib/session-utils.sh 2>/dev/null

SESSION_DIR=$(get_session_dir)
BASENAME=$(basename "$FILE_PATH")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Only track if session exists
if [ -z "$SESSION_DIR" ] || [ ! -d "$SESSION_DIR" ]; then
  echo "{\"systemMessage\": \"Artifact created: $TYPE ($BASENAME) - no active session to track\"}"
  exit 0
fi

# Append to session-specific artifacts log
ARTIFACTS_LOG="$SESSION_DIR/artifacts.log"
echo "$TIMESTAMP | $TYPE | $FILE_PATH" >> "$ARTIFACTS_LOG"

echo "{\"systemMessage\": \"Artifact tracked: $TYPE ($BASENAME)\"}"
exit 0
