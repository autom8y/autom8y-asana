#!/bin/bash
# PreToolUse (Edit/Write) hook - warn on direct implementation during workflow
# Category: DEFENSIVE - emits WARNING (not block) to preserve human override

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Library Resolution - per ADR-0002
HOOKS_LIB="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/lib"

# Absolute fallback if hooks-init.sh itself fails
source "$HOOKS_LIB/hooks-init.sh" 2>/dev/null || exit 0

hooks_init "delegation-check" "DEFENSIVE"

# Source session utilities for get_session_dir()
safe_source "$HOOKS_LIB/session-utils.sh" || { hooks_finalize 0; exit 0; }

# Read JSON input from stdin
INPUT=$(cat 2>/dev/null) || INPUT=""
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null) || TOOL_NAME=""

# Only check Edit and Write tools
if [[ "$TOOL_NAME" != "Edit" ]] && [[ "$TOOL_NAME" != "Write" ]]; then
  hooks_finalize 0
  exit 0
fi

# Check for active workflow
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || true

# =============================================================================
# OPTIMIZATION: Use cached session directory and workflow state
# Avoids repeated disk reads for SESSION_CONTEXT.md parsing (~20-30ms savings)
# =============================================================================

# Get session directory (prefer cache if available)
if [[ -n "${CACHED_SESSION_DIR:-}" ]]; then
    SESSION_DIR="$CACHED_SESSION_DIR"
else
    SESSION_DIR=$(get_session_dir 2>/dev/null || echo "")
fi
SESSION_CTX="${SESSION_DIR:+$SESSION_DIR/SESSION_CONTEXT.md}"

# If no session or session context file, allow
if [[ -z "$SESSION_CTX" ]] || [[ ! -f "$SESSION_CTX" ]]; then
  hooks_finalize 0
  exit 0
fi

# Check workflow.active status (use cache if available)
if [[ -n "${CACHED_WORKFLOW_ACTIVE:-}" ]]; then
    WORKFLOW_ACTIVE="$CACHED_WORKFLOW_ACTIVE"
else
    # Parse YAML-like markdown for workflow.active
    WORKFLOW_ACTIVE=$(grep -A5 "^workflow:" "$SESSION_CTX" 2>/dev/null | grep "active:" | grep -o "true\|false" | head -1) || WORKFLOW_ACTIVE=""
    # Cache for subsequent hooks in same process
    export CACHED_WORKFLOW_ACTIVE="$WORKFLOW_ACTIVE"
fi

if [[ "$WORKFLOW_ACTIVE" != "true" ]]; then
  hooks_finalize 0
  exit 0
fi

# Get workflow name for context
WORKFLOW_NAME=$(grep -A5 "^workflow:" "$SESSION_CTX" 2>/dev/null | grep "name:" | sed 's/.*name:[[:space:]]*//' | tr -d '"' | head -1)

# Get file being modified
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // "unknown"' 2>/dev/null)

# Check if this is likely specialist work (code files, not session/artifact files)
# Allow modifications to session files, artifacts, and documentation by main thread
ALLOWED_PATHS="SESSION_CONTEXT|sessions/|docs/requirements|docs/design|docs/testing"

if echo "$FILE_PATH" | grep -qE "$ALLOWED_PATHS" 2>/dev/null; then
  # This is session/artifact management, allowed for main thread
  hooks_finalize 0
  exit 0
fi

# Emit condensed warning to stderr (becomes context for Claude)
cat >&2 <<EOF
[DELEGATION] Workflow active ($WORKFLOW_NAME): $TOOL_NAME on $FILE_PATH
  -> Use Task tool to delegate, or proceed if intentional override.
  -> See: .claude/skills/orchestration/main-thread-guide.md
EOF

# Allow the operation (warning only, not blocking)
hooks_finalize 0
exit 0
