#!/bin/bash
# PreToolUse (Edit/Write) hook - warn on direct implementation during workflow
# Emits WARNING (not block) to preserve human override

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Source logging if available
source "$SCRIPT_DIR/lib/logging.sh" 2>/dev/null && log_init "delegation-check" && log_start || true

# Source session utilities for get_session_dir()
source "$SCRIPT_DIR/lib/session-utils.sh" 2>/dev/null || true

# Read JSON input from stdin
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)

# Only check Edit and Write tools
if [[ "$TOOL_NAME" != "Edit" ]] && [[ "$TOOL_NAME" != "Write" ]]; then
  exit 0
fi

# Check for active workflow
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || true

# Get session directory using proper session-utils function
SESSION_DIR=$(get_session_dir 2>/dev/null || echo "")
SESSION_CTX="${SESSION_DIR:+$SESSION_DIR/SESSION_CONTEXT.md}"

# If no session or session context file, allow
if [[ -z "$SESSION_CTX" ]] || [[ ! -f "$SESSION_CTX" ]]; then
  exit 0
fi

# Check workflow.active status
# Parse YAML-like markdown for workflow.active
WORKFLOW_ACTIVE=$(grep -A5 "^workflow:" "$SESSION_CTX" 2>/dev/null | grep "active:" | grep -o "true\|false" | head -1)

if [[ "$WORKFLOW_ACTIVE" != "true" ]]; then
  exit 0
fi

# Get workflow name for context
WORKFLOW_NAME=$(grep -A5 "^workflow:" "$SESSION_CTX" 2>/dev/null | grep "name:" | sed 's/.*name:[[:space:]]*//' | tr -d '"' | head -1)

# Get file being modified
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // "unknown"' 2>/dev/null)

# Check if this is likely specialist work (code files, not session/artifact files)
# Allow modifications to session files, artifacts, and documentation by main thread
ALLOWED_PATHS="SESSION_CONTEXT|sessions/|docs/requirements|docs/design|docs/testing"

if echo "$FILE_PATH" | grep -qE "$ALLOWED_PATHS"; then
  # This is session/artifact management, allowed for main thread
  exit 0
fi

# Emit warning to stderr (becomes context for Claude)
cat >&2 <<EOF

[DELEGATION WARNING]
====================
Active workflow detected: $WORKFLOW_NAME
Tool attempted: $TOOL_NAME on $FILE_PATH

The main thread should delegate implementation to specialists via Task tool.
Direct Edit/Write of code files during active workflow violates the Coach pattern.

If this is intentional (user override), proceed.
If accidental, cancel and use Task tool to invoke the appropriate specialist.

See: .claude/skills/orchestration/main-thread-guide.md
====================

EOF

# Allow the operation (warning only, not blocking)
exit 0
