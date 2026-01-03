#!/bin/bash
# orchestrator-bypass-check.sh - PreToolUse hook for Task tool invocations
# Warns when invoking specialists without orchestrator consultation (warn-only, non-blocking)
#
# Event: PreToolUse
# Priority: 20 (after other PreToolUse guards)
# Matcher: Task

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

# Library Resolution - per ADR-0002
HOOKS_LIB="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/lib"
source "$HOOKS_LIB/logging.sh" 2>/dev/null && log_init "orchestrator-bypass-check" && log_start || true
source "$HOOKS_LIB/session-utils.sh" 2>/dev/null || { log_end 1 2>/dev/null; exit 0; }

# Read input from stdin (PreToolUse hook receives tool invocation info)
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)

# Only check Task tool invocations
if [[ "$TOOL_NAME" != "Task" ]]; then
    exit 0
fi

# Get the agent being invoked
AGENT=$(echo "$INPUT" | jq -r '.tool_input.task // .tool_input.agent // ""' 2>/dev/null)

# Skip if invoking orchestrator itself
if [[ "$AGENT" == "orchestrator" ]]; then
    exit 0
fi

# Skip if no orchestrator in team
if [[ ! -f "$PROJECT_DIR/.claude/agents/orchestrator.md" ]]; then
    exit 0
fi

# Check for active workflow
has_active_workflow() {
    local session_dir
    session_dir=$(get_session_dir 2>/dev/null || echo "")
    [[ -z "$session_dir" ]] && return 1

    local ctx_file="$session_dir/SESSION_CONTEXT.md"
    [[ ! -f "$ctx_file" ]] && return 1

    # Check if workflow is active
    if grep -qE "^current_phase:" "$ctx_file" 2>/dev/null; then
        return 0
    fi

    return 1
}

if ! has_active_workflow; then
    # No workflow = no orchestration required
    exit 0
fi

# Check session for recent orchestrator consultation
# Look for orchestrator consultation marker in last 5 minutes
check_recent_consultation() {
    local session_dir
    session_dir=$(get_session_dir 2>/dev/null || echo "")
    [[ -z "$session_dir" ]] && return 1

    local events_file="$session_dir/events.jsonl"
    [[ ! -f "$events_file" ]] && return 1

    # Check for orchestrator consultation event in last 5 minutes
    # Use portable date commands for macOS and Linux
    local five_min_ago
    if date -u -v-5M +%Y-%m-%dT%H:%M:%SZ 2>/dev/null >/dev/null; then
        # macOS
        five_min_ago=$(date -u -v-5M +%Y-%m-%dT%H:%M:%SZ)
    elif date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null >/dev/null; then
        # Linux
        five_min_ago=$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ)
    else
        # Fallback: just check last 20 events
        tail -20 "$events_file" 2>/dev/null | grep -q '"event":"ORCHESTRATOR_CONSULTED"' && return 0
        return 1
    fi

    # Check for recent orchestrator consultation events
    tail -20 "$events_file" 2>/dev/null | grep -q '"event":"ORCHESTRATOR_CONSULTED"' && return 0
    return 1
}

if check_recent_consultation; then
    # Recent consultation found - allow without warning
    exit 0
fi

# Emit warning to stderr (non-blocking - operation continues)
cat >&2 <<EOF

## Warning: Orchestrator Consultation Recommended

You are invoking specialist **$AGENT** without recent orchestrator consultation.

**Best Practice**: During active workflows, consult the orchestrator first:

\`\`\`
Task(orchestrator, "CONSULTATION_REQUEST with current state...")
\`\`\`

Then invoke specialists based on the orchestrator's directive.

*This is a warning only - proceeding with specialist invocation.*

EOF

log_end 0 2>/dev/null || true
exit 0
