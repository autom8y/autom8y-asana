#!/bin/bash
# orchestrator-router.sh - UserPromptSubmit hook for /start, /sprint, /task routing
# Injects CONSULTATION_REQUEST when orchestrator is present in active team
#
# Event: UserPromptSubmit
# Priority: 5 (before start-preflight.sh at 10)
# Matcher: ^/(start|sprint|task)

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Library Resolution - per ADR-0002
HOOKS_LIB="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/lib"
source "$HOOKS_LIB/logging.sh" 2>/dev/null && log_init "orchestrator-router" && log_start || true

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

# Build routing context with CONSULTATION_REQUEST
cat <<EOF

---
## Orchestrator Routing Required

This **/$COMMAND** command requires consultation with the Orchestrator before proceeding.

### CONSULTATION_REQUEST

\`\`\`yaml
type: $REQUEST_TYPE
initiative:
  name: "$INITIATIVE"
  complexity: "MODULE"  # Assess and adjust based on scope
state:
  current_phase: null
  completed_phases: []
  artifacts_produced: []
context_summary: |
  User invoked /$COMMAND. Assess complexity and determine phase sequence.
\`\`\`

**IMPORTANT**: Invoke the orchestrator via Task tool with this CONSULTATION_REQUEST before any specialist work. Let hooks handle state mutations - do not call state-mate directly during orchestrated workflows.

---

EOF

log_end 0 2>/dev/null || true
exit 0
