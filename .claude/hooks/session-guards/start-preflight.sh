#!/bin/bash
# UserPromptSubmit hook - validate /start command before Claude processes it
# Category: RECOVERABLE - can detect errors but must degrade gracefully
# Injects preflight context for session lifecycle commands

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Library Resolution - per ADR-0002
HOOKS_LIB="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/lib"
source "$HOOKS_LIB/hooks-init.sh"
hooks_init "start-preflight" "RECOVERABLE"

# Check if this is a session lifecycle command
USER_PROMPT="${CLAUDE_USER_PROMPT:-}"

# Only act on session lifecycle commands
if [[ ! "$USER_PROMPT" =~ ^/(start|continue|park|wrap|sessions|worktree) ]]; then
    exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Source session utilities
safe_source "$HOOKS_LIB/session-utils.sh" || exit 0

# Detect worktree context
IN_WORKTREE="false"
WORKTREE_ID=""
WORKTREE_TEAM=""
if is_worktree; then
    IN_WORKTREE="true"
    WORKTREE_ID=$(get_worktree_field worktree_id)
    WORKTREE_TEAM=$(get_worktree_field team)
fi

# Get session state
SESSION_ID=$(get_session_id)
SESSION_DIR=$(get_session_dir)
HAS_SESSION="false"
PARKED="false"
INITIATIVE=""

if [[ -n "$SESSION_ID" && -d ".claude/sessions/$SESSION_ID" ]]; then
    HAS_SESSION="true"
    CTX_FILE=".claude/sessions/$SESSION_ID/SESSION_CONTEXT.md"

    if [[ -f "$CTX_FILE" ]]; then
        INITIATIVE=$(grep -m1 "^initiative:" "$CTX_FILE" 2>/dev/null | cut -d: -f2- | tr -d ' "' || echo "unnamed")
        if grep -qE "^(parked_at|auto_parked_at):" "$CTX_FILE" 2>/dev/null; then
            PARKED="true"
        fi
    fi
fi

# Handle /start specifically
if [[ "$USER_PROMPT" =~ ^/start ]]; then
    if [[ "$HAS_SESSION" == "true" ]]; then
        if [[ "$PARKED" == "true" ]]; then
            cat <<EOF

---
**Preflight Check**: Session exists (parked)

You have a parked session: **$INITIATIVE**

| Option | Command | Description |
|--------|---------|-------------|
| Resume | \`/continue\` | Resume the parked session |
| Finalize | \`/wrap\` | Archive session and start fresh |
| Parallel | \`/worktree create\` | Start new work in isolated worktree |

---
EOF
        else
            cat <<EOF

---
**Preflight Check**: Session already active

You have an active session: **$INITIATIVE**

| Option | Command | Description |
|--------|---------|-------------|
| Pause | \`/park\` | Save current work, then \`/start\` |
| Finalize | \`/wrap\` | Archive session, then \`/start\` |
| Parallel | \`/worktree create\` | Start new work in isolated worktree |

---
EOF
        fi
    else
        ACTIVE_TEAM=$(cat ".claude/ACTIVE_TEAM" 2>/dev/null || echo "none")
        SUGGESTED_ID=$(generate_session_id)

        # Extract initiative and complexity from /start command
        # Format: /start "initiative name" COMPLEXITY or /start initiative COMPLEXITY
        INITIATIVE=$(echo "$USER_PROMPT" | sed 's|^/start[[:space:]]*||')
        COMPLEXITY="MODULE"  # Default

        # Check for complexity at end of command
        if [[ "$INITIATIVE" =~ (.+)[[:space:]]+(FUNCTION|MODULE|SERVICE|PLATFORM)[[:space:]]*$ ]]; then
            COMPLEXITY="${BASH_REMATCH[2]}"
            INITIATIVE="${BASH_REMATCH[1]}"
        fi

        # Clean up initiative (remove quotes if present)
        INITIATIVE=$(echo "$INITIATIVE" | sed 's/^"//;s/"$//' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [[ -z "$INITIATIVE" ]] && INITIATIVE="Unnamed initiative"

        # Trigger session creation via session-manager.sh (hook-triggered)
        SESSION_CREATE_RESULT=$("$HOOKS_LIB/session-manager.sh" create "$INITIATIVE" "$COMPLEXITY" "$ACTIVE_TEAM" 2>&1)
        SESSION_CREATE_SUCCESS=$?

        if [[ $SESSION_CREATE_SUCCESS -eq 0 ]]; then
            # Extract session_id from JSON result
            CREATED_SESSION_ID=$(echo "$SESSION_CREATE_RESULT" | grep -o '"session_id": *"[^"]*"' | cut -d'"' -f4)

            # Log as hook-triggered creation (audit trail differentiation)
            AUDIT_LOG="$PROJECT_DIR/.claude/sessions/.audit/session-mutations.log"
            mkdir -p "$(dirname "$AUDIT_LOG")" 2>/dev/null
            TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
            echo "$TIMESTAMP | $CREATED_SESSION_ID | CREATE | hook | start-preflight.sh" >> "$AUDIT_LOG"
        fi

        # Generate complexity warning if PLATFORM
        COMPLEXITY_WARNING=""
        if [[ "$COMPLEXITY" == "PLATFORM" ]]; then
            COMPLEXITY_WARNING="

**Complexity Warning**: PLATFORM-level complexity detected.

For large-scale initiatives, consider using the Session -1/0 protocol:
- **Session -1** (Initiative Assessment): Evaluate feasibility, scope, team readiness
- **Session 0** (Orchestrator Initialization): Break down into epics and tasks

See the \`initiative-scoping\` skill for templates and guidance.

This is informational only - you may proceed with /start if appropriate.
"
        fi

        # Build session creation status message
        SESSION_STATUS_MSG=""
        if [[ $SESSION_CREATE_SUCCESS -eq 0 ]]; then
            SESSION_STATUS_MSG="Session created: **$CREATED_SESSION_ID**"
        else
            SESSION_STATUS_MSG="Session creation warning (proceeding): $SESSION_CREATE_RESULT"
        fi

        if [[ "$IN_WORKTREE" == "true" ]]; then
            cat <<EOF

---
**Preflight Check**: Ready for new session (in worktree)

| Property | Value |
|----------|-------|
| Team | $ACTIVE_TEAM |
| Initiative | $INITIATIVE |
| Complexity | $COMPLEXITY |
| Worktree | $WORKTREE_ID |
| Expected Team | ${WORKTREE_TEAM:-$ACTIVE_TEAM} |

**Worktree Context**: Sessions here are isolated from main project.
Use \`/wrap\` when done to finalize and optionally remove worktree.
${COMPLEXITY_WARNING}
$SESSION_STATUS_MSG

---
EOF
        else
            cat <<EOF

---
**Preflight Check**: Session Created (Hook-Triggered)

| Property | Value |
|----------|-------|
| Team | $ACTIVE_TEAM |
| Initiative | $INITIATIVE |
| Complexity | $COMPLEXITY |
${COMPLEXITY_WARNING}
$SESSION_STATUS_MSG

---
EOF
        fi
    fi
fi

# Handle /continue
if [[ "$USER_PROMPT" =~ ^/continue ]]; then
    if [[ "$HAS_SESSION" != "true" ]]; then
        cat <<EOF

---
**Preflight Check**: No session to continue

No active or parked session found for this terminal.

Use \`/start <initiative>\` to create a new session.

---
EOF
    elif [[ "$PARKED" != "true" ]]; then
        cat <<EOF

---
**Preflight Check**: Session already active

Session **$INITIATIVE** is already active (not parked).

Continue working or use \`/park\` to pause first.

---
EOF
    fi
fi

# Handle /park
if [[ "$USER_PROMPT" =~ ^/park ]]; then
    if [[ "$HAS_SESSION" != "true" ]]; then
        cat <<EOF

---
**Preflight Check**: No session to park

No active session found. Use \`/start\` to create one.

---
EOF
    elif [[ "$PARKED" == "true" ]]; then
        cat <<EOF

---
**Preflight Check**: Session already parked

Session **$INITIATIVE** is already parked.

Use \`/continue\` to resume or \`/wrap\` to finalize.

---
EOF
    fi
fi

# Handle /wrap
if [[ "$USER_PROMPT" =~ ^/wrap ]]; then
    if [[ "$HAS_SESSION" != "true" ]]; then
        cat <<EOF

---
**Preflight Check**: No session to wrap

No active session found. Nothing to finalize.

---
EOF
    fi
fi

hooks_finalize 0
exit 0
