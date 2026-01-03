#!/bin/bash
# coach-mode.sh - SessionStart hook for Coach Mode reminder
# Category: RECOVERABLE - can detect errors but must degrade gracefully
# Extracted from session-context.sh (RF-008)
#
# This hook outputs a reminder when workflow.active is true in SESSION_CONTEXT.md
#
# Addresses: SRP-002 (Coach Mode leaking into session-context)
# Part of Ecosystem v2 refactoring (RF-008)

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Library Resolution - per ADR-0002
HOOKS_LIB="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/lib"
source "$HOOKS_LIB/hooks-init.sh"
hooks_init "coach-mode" "RECOVERABLE"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

# Get current session directory
CURRENT_SESSION_FILE="${CURRENT_SESSION_FILE:-$PROJECT_DIR/.claude/sessions/.current-session}"

if [[ ! -f "$CURRENT_SESSION_FILE" ]]; then
    exit 0
fi

SESSION_DIR=$(cat "$CURRENT_SESSION_FILE" 2>/dev/null | tr -d '\n') || SESSION_DIR=""
SESSION_CTX="${SESSION_DIR:+$SESSION_DIR/SESSION_CONTEXT.md}"

# If no session context file, exit silently
if [[ -z "$SESSION_CTX" ]] || [[ ! -f "$SESSION_CTX" ]]; then
    exit 0
fi

# Check workflow.active status in SESSION_CONTEXT.md
# Parse YAML-like markdown for workflow.active (same pattern as delegation-check.sh)
WORKFLOW_ACTIVE=$(grep -A5 "^workflow:" "$SESSION_CTX" 2>/dev/null | grep "active:" | grep -o "true\|false" | head -1) || WORKFLOW_ACTIVE=""

# Only output reminder if workflow is active
if [[ "$WORKFLOW_ACTIVE" == "true" ]]; then
    cat <<EOF

**COACH MODE ACTIVE**
You are the Coach. Delegate all implementation via Task tool.
Do NOT use Edit/Write directly on code files.
See: .claude/skills/orchestration/main-thread-guide.md
EOF
fi

exit 0
