#!/bin/bash
# UserPromptSubmit hook - validate /start command before Claude processes it
# Injects preflight context for session lifecycle commands

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Source logging library
source "$SCRIPT_DIR/lib/logging.sh" 2>/dev/null && log_init "start-preflight" && log_start || true

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
source "$SCRIPT_DIR/lib/session-utils.sh" 2>/dev/null || exit 0

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

        # Extract complexity from /start command if present
        COMPLEXITY=""
        if [[ "$USER_PROMPT" =~ /start[[:space:]]+\"[^\"]+\"[[:space:]]+([A-Z]+) ]]; then
            COMPLEXITY="${BASH_REMATCH[1]}"
        elif [[ "$USER_PROMPT" =~ /start[[:space:]]+[^[:space:]]+[[:space:]]+([A-Z]+) ]]; then
            COMPLEXITY="${BASH_REMATCH[1]}"
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

        if [[ "$IN_WORKTREE" == "true" ]]; then
            cat <<EOF

---
**Preflight Check**: Ready for new session (in worktree)

| Property | Value |
|----------|-------|
| Team | $ACTIVE_TEAM |
| Status | No active session |
| Worktree | $WORKTREE_ID |
| Expected Team | ${WORKTREE_TEAM:-$ACTIVE_TEAM} |

**Worktree Context**: Sessions here are isolated from main project.
Use \`/wrap\` when done to finalize and optionally remove worktree.
${COMPLEXITY_WARNING}
Proceeding with session creation...

---
EOF
        else
            cat <<EOF

---
**Preflight Check**: Ready for new session

| Property | Value |
|----------|-------|
| Team | $ACTIVE_TEAM |
| Status | No active session |
${COMPLEXITY_WARNING}
Proceeding with session creation...

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

log_end 0 2>/dev/null || true
exit 0
