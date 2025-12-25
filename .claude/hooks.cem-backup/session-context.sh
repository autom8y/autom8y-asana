#!/bin/bash
# SessionStart hook - inject project context
# Outputs markdown that becomes Claude context on session start

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || true

# Source session utilities
source .claude/hooks/lib/session-utils.sh 2>/dev/null

# Gather context
ACTIVE_TEAM=$(cat .claude/ACTIVE_TEAM 2>/dev/null || echo "none")
GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "not a git repo")
GIT_STATUS_COUNT=$(git status --short 2>/dev/null | wc -l | tr -d ' ')

# Session state - now session-aware
SESSION_DIR=$(get_session_dir)
SESSION_ID=$(get_session_id)

if [ -n "$SESSION_DIR" ] && [ -f "$SESSION_DIR/SESSION_CONTEXT.md" ]; then
  SESSION_PHASE=$(grep -m1 "^current_phase:" "$SESSION_DIR/SESSION_CONTEXT.md" 2>/dev/null | cut -d: -f2 | tr -d ' "')
  INITIATIVE=$(grep -m1 "^initiative:" "$SESSION_DIR/SESSION_CONTEXT.md" 2>/dev/null | cut -d: -f2 | tr -d ' "')
  PARKED=$(grep -m1 "^parked_at:" "$SESSION_DIR/SESSION_CONTEXT.md" 2>/dev/null)
  AUTO_PARKED=$(grep -m1 "^auto_parked_at:" "$SESSION_DIR/SESSION_CONTEXT.md" 2>/dev/null)

  if [ -n "$PARKED" ] || [ -n "$AUTO_PARKED" ]; then
    SESSION_STATE="PARKED"
  else
    SESSION_STATE="ACTIVE"
  fi
  SESSION_DISPLAY="${INITIATIVE:-$SESSION_ID}"
else
  SESSION_DISPLAY="none"
  SESSION_STATE="IDLE"
  SESSION_PHASE="none"
  SESSION_ID=""
fi

# Artifacts discovery
PRDS=$(ls docs/requirements/PRD-*.md 2>/dev/null | xargs -I{} basename {} 2>/dev/null | tr '\n' ', ' | sed 's/,$//' || echo "")
TDDS=$(ls docs/design/TDD-*.md 2>/dev/null | xargs -I{} basename {} 2>/dev/null | tr '\n' ', ' | sed 's/,$//' || echo "")
ADRS=$(ls docs/design/ADR-*.md 2>/dev/null | wc -l | tr -d ' ')

# Git status summary
if [ "$GIT_STATUS_COUNT" = "0" ]; then
  GIT_DISPLAY="$GIT_BRANCH (clean)"
else
  GIT_DISPLAY="$GIT_BRANCH ($GIT_STATUS_COUNT uncommitted)"
fi

# Workflow info
if [ -f .claude/ACTIVE_WORKFLOW.yaml ]; then
  WORKFLOW_NAME=$(grep "^name:" .claude/ACTIVE_WORKFLOW.yaml 2>/dev/null | awk '{print $2}')
  ENTRY_AGENT=$(grep -A2 "^entry_point:" .claude/ACTIVE_WORKFLOW.yaml 2>/dev/null | grep "agent:" | head -1 | awk '{print $2}')
  WORKFLOW_DISPLAY="$WORKFLOW_NAME (entry: $ENTRY_AGENT)"
else
  WORKFLOW_DISPLAY="none"
fi

# Output as markdown (becomes Claude context)
cat <<EOF
## Project Context (auto-loaded)
- **Project**: $(pwd)
- **Active Team**: $ACTIVE_TEAM
- **Workflow**: $WORKFLOW_DISPLAY
- **Session**: $SESSION_DISPLAY ($SESSION_STATE, $SESSION_PHASE phase)
- **Session ID**: ${SESSION_ID:-none}
- **Git**: $GIT_DISPLAY
- **PRDs**: ${PRDS:-none}
- **TDDs**: ${TDDS:-none}
- **ADRs**: $ADRS total
EOF

exit 0
