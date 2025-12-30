#!/bin/bash
# SessionStart hook - comprehensive context injection
# Pre-computes EVERYTHING Claude needs for session management
# Output becomes Claude context on session start

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Source logging library
source "$SCRIPT_DIR/lib/logging.sh" 2>/dev/null && log_init "session-context" && log_start || true
START_TIME=$(get_time_ms 2>/dev/null || echo 0)

# Source session utilities
source "$SCRIPT_DIR/lib/session-utils.sh" 2>/dev/null || {
    # Fallback if session-utils not available
    echo "## Project Context (fallback mode)"
    echo "- **Project**: $(pwd)"
    echo "- **Status**: Session utilities not initialized"
    echo ""
    echo "*Run \`cem init\` to set up the Claude ecosystem.*"
    exit 0
}

# Cleanup stale/orphaned TTY mappings (STATE-002)
# Run early before session detection, silently to avoid polluting hook output
CLEANUP_COUNT=$(cleanup_stale_mappings 2>/dev/null) || true
if [[ -n "$CLEANUP_COUNT" && "$CLEANUP_COUNT" -gt 0 ]]; then
    log_debug "Cleaned up $CLEANUP_COUNT stale TTY mappings" 2>/dev/null || true
fi

# Get full session status via session-manager
if [[ -x "$SCRIPT_DIR/lib/session-manager.sh" ]]; then
    SESSION_JSON=$("$SCRIPT_DIR/lib/session-manager.sh" status 2>/dev/null || echo '{}')
else
    SESSION_JSON='{}'
fi

# Parse JSON values (with fallbacks for missing jq)
parse_json() {
    local key="$1"
    local default="$2"
    if command -v jq >/dev/null 2>&1; then
        echo "$SESSION_JSON" | jq -r ".$key // \"$default\"" 2>/dev/null || echo "$default"
    else
        # Fallback: simple grep-based parsing
        echo "$SESSION_JSON" | grep -o "\"$key\": *\"[^\"]*\"" | cut -d'"' -f4 || echo "$default"
    fi
}

parse_json_bool() {
    local key="$1"
    local default="$2"
    if command -v jq >/dev/null 2>&1; then
        echo "$SESSION_JSON" | jq -r ".$key // $default" 2>/dev/null || echo "$default"
    else
        echo "$SESSION_JSON" | grep -o "\"$key\": *[a-z]*" | awk '{print $2}' || echo "$default"
    fi
}

# Extract session data
HAS_SESSION=$(parse_json_bool "has_session" "false")
SESSION_STATE=$(parse_json "session_state" "IDLE")
SESSION_ID=$(parse_json "session_id" "null")
INITIATIVE=$(parse_json "initiative" "null")
COMPLEXITY=$(parse_json "complexity" "null")
CURRENT_PHASE=$(parse_json "current_phase" "null")
PARKED=$(parse_json_bool "parked" "false")
ACTIVE_TEAM=$(parse_json "active_team" "none")
WORKFLOW_NAME=$(parse_json "workflow_name" "null")
WORKFLOW_ENTRY=$(parse_json "workflow_entry" "null")
GIT_BRANCH=$(parse_json "git_branch" "unknown")
GIT_CHANGES=$(parse_json "git_changes" "0")
SUGGESTED_ID=$(parse_json "suggested_session_id" "")
WORKFLOW_ACTIVE=$(parse_json_bool "workflow_active" "false")
WORKFLOW_MODE=$(parse_json "workflow_mode" "none")

# Git display
if [[ "$GIT_CHANGES" == "0" ]]; then
    GIT_DISPLAY="$GIT_BRANCH (clean)"
else
    GIT_DISPLAY="$GIT_BRANCH ($GIT_CHANGES uncommitted)"
fi

# Worktree detection
WORKTREE_ID=""
WORKTREE_NAME=""
WORKTREE_DISPLAY="main project"
IS_WORKTREE="false"

GIT_DIR=$(git rev-parse --git-dir 2>/dev/null || echo "")
if [[ -f "$GIT_DIR" ]] && grep -q "^gitdir:" "$GIT_DIR" 2>/dev/null; then
    IS_WORKTREE="true"
    if [[ -f ".claude/.worktree-meta.json" ]]; then
        if command -v jq >/dev/null 2>&1; then
            WORKTREE_ID=$(jq -r '.worktree_id // "unknown"' ".claude/.worktree-meta.json" 2>/dev/null)
            WORKTREE_NAME=$(jq -r '.name // "unnamed"' ".claude/.worktree-meta.json" 2>/dev/null)
            WORKTREE_TEAM=$(jq -r '.team // "none"' ".claude/.worktree-meta.json" 2>/dev/null)
            WORKTREE_DISPLAY="$WORKTREE_ID ($WORKTREE_NAME, team: $WORKTREE_TEAM)"
        else
            WORKTREE_ID=$(grep -o '"worktree_id": *"[^"]*"' ".claude/.worktree-meta.json" 2>/dev/null | cut -d'"' -f4 || echo "unknown")
            WORKTREE_DISPLAY="$WORKTREE_ID (metadata available)"
        fi
    else
        WORKTREE_DISPLAY="unmanaged worktree"
    fi
fi

# Workflow display
if [[ "$WORKFLOW_NAME" != "null" && -n "$WORKFLOW_NAME" ]]; then
    WORKFLOW_DISPLAY="$WORKFLOW_NAME (entry: ${WORKFLOW_ENTRY:-unknown})"
else
    WORKFLOW_DISPLAY="none"
fi

# Artifacts discovery (fast version)
PRDS=$(find docs/requirements -maxdepth 1 -name "PRD-*.md" 2>/dev/null | wc -l | tr -d ' ')
TDDS=$(find docs/design -maxdepth 1 -name "TDD-*.md" 2>/dev/null | wc -l | tr -d ' ')
ADRS=$(find docs/design -maxdepth 1 -name "ADR-*.md" 2>/dev/null | wc -l | tr -d ' ')

# Output comprehensive context as markdown
cat <<EOF
## Project Context (auto-loaded)

| Property | Value |
|----------|-------|
| **Project** | $(pwd) |
| **Worktree** | $WORKTREE_DISPLAY |
| **Active Team** | $ACTIVE_TEAM |
| **Workflow** | $WORKFLOW_DISPLAY |
| **Git** | $GIT_DISPLAY |

### Session Status

| Property | Value |
|----------|-------|
| **Has Session** | $HAS_SESSION |
| **Session State** | $SESSION_STATE |
| **Session ID** | ${SESSION_ID} |
| **Initiative** | ${INITIATIVE} |
| **Complexity** | ${COMPLEXITY} |
| **Current Phase** | ${CURRENT_PHASE} |
| **Parked** | $PARKED |
| **Workflow Active** | $WORKFLOW_ACTIVE |
| **Workflow Mode** | $WORKFLOW_MODE |

### Artifacts
- **PRDs**: $PRDS
- **TDDs**: $TDDS
- **ADRs**: $ADRS

### Pre-computed Values (for /start)
- **Suggested Session ID**: \`$SUGGESTED_ID\`
- **Entry Agent**: ${WORKFLOW_ENTRY:-requirements-analyst}
- **Sessions Directory**: \`.claude/sessions/\`

---

**Session Commands**:
EOF

# Provide context-appropriate guidance
if [[ "$HAS_SESSION" == "true" ]]; then
    if [[ "$PARKED" == "true" ]]; then
        cat <<EOF
- \`/continue\` - Resume parked session "$INITIATIVE"
- \`/wrap\` - Finalize and archive session
- \`/sessions\` - List all sessions
EOF
    else
        cat <<EOF
- \`/park\` - Pause current session
- \`/handoff <agent>\` - Transfer to another agent
- \`/wrap\` - Finalize session
EOF
    fi
else
    cat <<EOF
- \`/start <initiative>\` - Create new session (ready!)
- \`/sessions\` - List existing sessions
- \`/worktree create <name>\` - Start isolated parallel work
EOF
fi

# Add worktree-specific guidance
if [[ "$IS_WORKTREE" == "true" ]]; then
    cat <<EOF

**Worktree Note**: You are in an isolated worktree. Changes here don't affect the main project.
- \`/worktree list\` - See all worktrees
- \`/wrap\` will offer to remove this worktree when done
EOF
fi

# Note: Coach Mode reminder moved to coach-mode.sh hook (RF-008)

# Team routing context (if team is active)
# Note: ROSTER_HOME is defined in config.sh (sourced via session-utils.sh)
if [[ -f ".claude/ACTIVE_TEAM" ]]; then
    TEAM_CONTEXT=$("$ROSTER_HOME/generate-team-context.sh" 2>/dev/null || echo "")
    if [[ -n "$TEAM_CONTEXT" ]]; then
        echo ""
        echo "$TEAM_CONTEXT"
    fi
fi

echo ""

# Log completion
if [[ "$START_TIME" != "0" ]]; then
    DURATION=$(calc_duration_ms "$START_TIME" 2>/dev/null || echo "")
    log_end 0 "$DURATION" 2>/dev/null || true
fi

exit 0
