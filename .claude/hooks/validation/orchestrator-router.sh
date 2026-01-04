#!/bin/bash
# orchestrator-router.sh - UserPromptSubmit hook for /start, /sprint, /task routing
# Injects ready-to-execute Task invocation when orchestrator is present
#
# Event: UserPromptSubmit
# Priority: 5 (before start-preflight.sh at 10)
# Matcher: ^/(start|sprint|task)

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Library Resolution - per ADR-0002
HOOKS_LIB="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/lib"
source "$HOOKS_LIB/logging.sh" 2>/dev/null && log_init "orchestrator-router" && log_start || true
source "$HOOKS_LIB/session-utils.sh" 2>/dev/null || exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

# Get user prompt
USER_PROMPT="${CLAUDE_USER_PROMPT:-}"

# Check if this is a workflow command
if [[ ! "$USER_PROMPT" =~ ^/(start|sprint|task) ]]; then
    exit 0
fi

# Extract command
COMMAND=$(echo "$USER_PROMPT" | grep -oE '^/(start|sprint|task)' | tr -d '/')

# Check if orchestrator is present in active team
if [[ ! -f "$PROJECT_DIR/.claude/agents/orchestrator.md" ]]; then
    # No orchestrator = direct execution is valid
    log_end 0 2>/dev/null || true
    exit 0
fi

# Extract initiative from prompt (everything after the command)
INITIATIVE=$(echo "$USER_PROMPT" | sed -E "s|^/$COMMAND[[:space:]]*||" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
[[ -z "$INITIATIVE" ]] && INITIATIVE="Unnamed initiative"

# Extract complexity if provided (last word if it's a valid complexity)
COMPLEXITY="MODULE"
if [[ "$INITIATIVE" =~ (.+)[[:space:]]+(FUNCTION|MODULE|SERVICE|PLATFORM)[[:space:]]*$ ]]; then
    COMPLEXITY="${BASH_REMATCH[2]}"
    INITIATIVE="${BASH_REMATCH[1]}"
fi

# Clean up initiative (remove quotes if present)
INITIATIVE=$(echo "$INITIATIVE" | sed 's/^"//;s/"$//' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

# Get active team
ACTIVE_TEAM=$(cat ".claude/ACTIVE_TEAM" 2>/dev/null || echo "none")

# Check for existing session
SESSION_ID=$(get_session_id 2>/dev/null || echo "")
SESSION_CREATED="false"

# For /start command, create session if none exists
if [[ "$COMMAND" == "start" && -z "$SESSION_ID" ]]; then
    # Create session via session-manager.sh
    SESSION_RESULT=$("$HOOKS_LIB/session-manager.sh" create "$INITIATIVE" "$COMPLEXITY" "$ACTIVE_TEAM" 2>&1) || true

    if [[ "$SESSION_RESULT" == *'"success": true'* ]]; then
        SESSION_ID=$(echo "$SESSION_RESULT" | grep -o '"session_id": *"[^"]*"' | cut -d'"' -f4)
        SESSION_CREATED="true"
    fi
fi

# Get session ID if we don't have it yet (for sprint/task or if create failed)
if [[ -z "$SESSION_ID" ]]; then
    SESSION_ID=$(get_session_id 2>/dev/null || echo "")
fi

# Build session path
SESSION_PATH=""
if [[ -n "$SESSION_ID" ]]; then
    SESSION_PATH=".claude/sessions/$SESSION_ID/SESSION_CONTEXT.md"
fi

# Determine request type based on command
REQUEST_TYPE="initial"
case "$COMMAND" in
    start)
        REQUEST_TYPE="initial"
        ;;
    sprint|task)
        REQUEST_TYPE="checkpoint"
        ;;
esac

# Escape special characters in initiative for Task invocation
INITIATIVE_ESCAPED=$(echo "$INITIATIVE" | sed 's/"/\\"/g')

# Build routing context with ready-to-execute Task invocation
if [[ "$SESSION_CREATED" == "true" ]]; then
    SESSION_MSG="Session created: **$SESSION_ID**"
else
    SESSION_MSG="Using existing session: **$SESSION_ID**"
fi

cat <<EOF

---
## Orchestrator Routing Required

$SESSION_MSG

### Next Step

Execute the following Task invocation:

\`\`\`
Task(orchestrator, "Break down initiative into phases and tasks

Session Context:
- Session ID: $SESSION_ID
- Session Path: $SESSION_PATH
- Initiative: $INITIATIVE_ESCAPED
- Complexity: $COMPLEXITY
- Team: $ACTIVE_TEAM
- Request Type: $REQUEST_TYPE")
\`\`\`

Copy the Task invocation above and execute it, or use \`/consult\` for manual routing.

---

EOF

log_end 0 2>/dev/null || true
exit 0
