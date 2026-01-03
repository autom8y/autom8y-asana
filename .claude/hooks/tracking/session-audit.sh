#!/bin/bash
# Post-write audit hook for SESSION_CONTEXT mutations
# Category: RECOVERABLE - can detect errors but must degrade gracefully
# Logs all Write operations to .claude/sessions/* and validates integrity

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Library Resolution - per ADR-0002
HOOKS_LIB="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/lib"
source "$HOOKS_LIB/hooks-init.sh"
hooks_init "session-audit" "RECOVERABLE"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

# Source session utilities for validation
safe_source "$HOOKS_LIB/session-utils.sh" || exit 0

AUDIT_DIR=".claude/sessions/.audit"
AUDIT_LOG="$AUDIT_DIR/session-mutations.log"

# Ensure audit directory exists
mkdir -p "$AUDIT_DIR" 2>/dev/null || exit 0

# Extract file_path from tool use context
# Expect CLAUDE_HOOK_TOOL_PARAMS to contain JSON with file_path
FILE_PATH="${CLAUDE_HOOK_FILE_PATH:-}"

# Only audit writes to session files
if [[ ! "$FILE_PATH" =~ ^\.claude/sessions/session-.*/.* ]]; then
    exit 0
fi

# Extract session ID from path
SESSION_ID=$(echo "$FILE_PATH" | grep -o 'session-[^/]*' | head -1)
OPERATION="WRITE"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Determine what was written
FILE_NAME=$(basename "$FILE_PATH")
STATUS="SUCCESS"
DETAILS="file=$FILE_NAME"

# Special validation for SESSION_CONTEXT.md
if [[ "$FILE_NAME" == "SESSION_CONTEXT.md" ]]; then
    if [[ -f "$FILE_PATH" ]]; then
        if validate_session_context "$FILE_PATH" 2>/dev/null; then
            STATUS="VALIDATED"
            # Extract key fields for audit
            INITIATIVE=$(get_yaml_field "$FILE_PATH" "initiative" 2>/dev/null || echo "unknown")
            PHASE=$(get_yaml_field "$FILE_PATH" "current_phase" 2>/dev/null || echo "unknown")
            DETAILS="file=$FILE_NAME initiative=$INITIATIVE phase=$PHASE"
        else
            STATUS="VALIDATION_FAILED"
            DETAILS="file=$FILE_NAME error=missing_required_fields"
        fi
    else
        STATUS="ERROR"
        DETAILS="file=$FILE_NAME error=file_not_found_after_write"
    fi
fi

# Log to audit trail
echo "$TIMESTAMP | $SESSION_ID | $OPERATION | $DETAILS | $STATUS" >> "$AUDIT_LOG"

# Log completion and exit 0 to not block the operation
hooks_finalize 0
exit 0
