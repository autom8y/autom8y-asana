#!/bin/bash
# command-validator.sh - Unified PreToolUse validator for Bash commands
# Consolidates: team-validator.sh + workflow-validator.sh
#
# CRITICAL: NO set -e, NO set -euo pipefail - hooks must NEVER crash
# CRITICAL: NO sourcing session-utils.sh - it can fail and crash the hook
#
# Addresses: SRP-003, DRY-001
# Part of Ecosystem v2 refactoring (RF-007)

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Source ONLY config.sh - it has no logic, only variable definitions
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh" 2>/dev/null || {
    # If even config.sh fails, set minimal defaults
    ROSTER_HOME="${ROSTER_HOME:-$HOME/Code/roster}"
    CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
}

# Source logging (optional - failures are OK)
source "$SCRIPT_DIR/lib/logging.sh" 2>/dev/null && log_init "command-validator" && log_start || true

# =============================================================================
# Input Handling (defensive - never crash on malformed input)
# =============================================================================

INPUT=$(cat 2>/dev/null) || INPUT=""
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || COMMAND=""

# Empty command = nothing to validate
[[ -z "$COMMAND" ]] && exit 0

# =============================================================================
# Helper Functions
# =============================================================================

auto_approve() {
    local reason="$1"
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "$reason"
  }
}
EOF
    log_end 0 2>/dev/null || true
    exit 0
}

# =============================================================================
# FAST PATH: Auto-approve safe read-only commands
# These are the most common - exit quickly for performance
# =============================================================================

# List operations (ls)
[[ "$COMMAND" =~ ^ls[[:space:]] ]] || [[ "$COMMAND" == "ls" ]] && auto_approve "Safe ls command"

# Git read operations
[[ "$COMMAND" =~ ^git[[:space:]]+(status|branch|log|diff|symbolic-ref|rev-list|rev-parse|remote|config|show) ]] && auto_approve "Safe git read command"

# GitHub CLI read operations
[[ "$COMMAND" =~ ^gh[[:space:]]+(pr|issue)[[:space:]]+(list|view|status) ]] && auto_approve "Safe gh read command"

# Cat for reading files
[[ "$COMMAND" =~ ^cat[[:space:]] ]] && auto_approve "Safe cat command"

# Head/tail for reading files
[[ "$COMMAND" =~ ^(head|tail)[[:space:]] ]] && auto_approve "Safe head/tail command"

# Test/existence checks
[[ "$COMMAND" =~ ^test[[:space:]] ]] || [[ "$COMMAND" =~ ^\[[[:space:]] ]] && auto_approve "Safe test command"

# Sed for text processing
[[ "$COMMAND" =~ ^sed[[:space:]] ]] && auto_approve "Safe sed command"

# Echo for output
[[ "$COMMAND" =~ ^echo[[:space:]] ]] && auto_approve "Safe echo command"

# Piped commands starting with safe operations
[[ "$COMMAND" =~ ^(git|gh|ls|cat|head|tail)[[:space:]].*\| ]] && auto_approve "Safe piped command"

# =============================================================================
# TEAM VALIDATION
# Only fires for swap-team.sh invocations
# =============================================================================

# Check if this is a swap-team.sh command (not just mentioned in a string)
if [[ "$COMMAND" =~ (^|[[:space:]/])swap-team\.sh[[:space:]] ]]; then
    # Extract target team from command
    TARGET_TEAM=$(echo "$COMMAND" | grep -oE '(^|[[:space:]/])swap-team\.sh[[:space:]]+([a-z0-9-]+-pack)' | grep -oE '[a-z0-9-]+-pack') || TARGET_TEAM=""

    # Skip validation for --list or no argument
    if [[ -n "$TARGET_TEAM" ]] && [[ "$TARGET_TEAM" != "--list" ]]; then
        ROSTER_DIR="$ROSTER_HOME/teams"

        # Validate team pack exists
        if [[ ! -d "$ROSTER_DIR/$TARGET_TEAM" ]]; then
            echo "Team pack '$TARGET_TEAM' not found in $ROSTER_DIR" >&2
            echo "Available teams:" >&2
            ls -1 "$ROSTER_DIR" 2>/dev/null | sed 's/^/  - /' >&2 || echo "  (none found)" >&2
            log_end 2 2>/dev/null || true
            exit 2  # Block the command
        fi

        # Validate team has agents
        AGENT_COUNT=$(find "$ROSTER_DIR/$TARGET_TEAM/agents/" -maxdepth 1 -name "*.md" 2>/dev/null | wc -l | tr -d ' ') || AGENT_COUNT="0"
        if [[ "$AGENT_COUNT" == "0" ]]; then
            echo "Team pack '$TARGET_TEAM' has no agent files" >&2
            log_end 2 2>/dev/null || true
            exit 2  # Block the command
        fi

        # Warn on session/team mismatch (don't block, just warn)
        # NOTE: We do NOT source session-utils.sh here to avoid crashes
        # Instead we do a simple file check
        PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
        CURRENT_SESSION_FILE="$PROJECT_DIR/.claude/sessions/.current-session"

        if [[ -f "$CURRENT_SESSION_FILE" ]]; then
            SESSION_DIR=$(cat "$CURRENT_SESSION_FILE" 2>/dev/null | tr -d '\n') || SESSION_DIR=""
            SESSION_FILE="${SESSION_DIR:+$SESSION_DIR/SESSION_CONTEXT.md}"

            if [[ -n "$SESSION_FILE" ]] && [[ -f "$SESSION_FILE" ]]; then
                SESSION_TEAM=$(grep -m1 "^active_team:" "$SESSION_FILE" 2>/dev/null | cut -d: -f2- | tr -d ' "') || SESSION_TEAM=""
                if [[ -n "$SESSION_TEAM" ]] && [[ "$SESSION_TEAM" != "$TARGET_TEAM" ]]; then
                    echo "{\"systemMessage\": \"Note: Session was started with '$SESSION_TEAM', switching to '$TARGET_TEAM'\"}"
                fi
            fi
        fi

        # Check for worktree/team mismatch (simple check without session-utils)
        GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || GIT_DIR=""
        if [[ -f "$GIT_DIR" ]] && grep -q "^gitdir:" "$GIT_DIR" 2>/dev/null; then
            # This is a worktree
            if [[ -f "$PROJECT_DIR/.claude/.worktree-meta.json" ]]; then
                WORKTREE_TEAM=$(jq -r '.team // "none"' "$PROJECT_DIR/.claude/.worktree-meta.json" 2>/dev/null) || WORKTREE_TEAM=""
                if [[ -n "$WORKTREE_TEAM" ]] && [[ "$WORKTREE_TEAM" != "none" ]] && [[ "$WORKTREE_TEAM" != "$TARGET_TEAM" ]]; then
                    cat <<EOF
{
  "systemMessage": "Warning: Worktree team mismatch. This worktree was created for '$WORKTREE_TEAM' but switching to '$TARGET_TEAM'. Consider using main project for different team."
}
EOF
                fi
            fi
        fi
    fi
fi

# =============================================================================
# WORKFLOW VALIDATION
# Only fires for swap-team or ACTIVE_WORKFLOW commands
# =============================================================================

# Only validate commands that involve workflow operations
if [[ "$COMMAND" == *"swap-team"* ]] || [[ "$COMMAND" == *"ACTIVE_WORKFLOW"* ]]; then
    WORKFLOW_FILE=""

    # Determine which workflow file to validate
    if [[ "$COMMAND" == *"swap-team"* ]]; then
        # Extract target team from swap-team.sh command
        TARGET_TEAM=$(echo "$COMMAND" | grep -oE 'swap-team\.sh[[:space:]]+([^[:space:]|&;]+)' | awk '{print $2}') || TARGET_TEAM=""

        # Skip validation for --list or no argument
        if [[ -n "$TARGET_TEAM" ]] && [[ "$TARGET_TEAM" != "--list" ]]; then
            ROSTER_DIR="$ROSTER_HOME/teams"
            WORKFLOW_FILE="$ROSTER_DIR/$TARGET_TEAM/workflow.yaml"
        fi
    elif [[ "$COMMAND" == *"ACTIVE_WORKFLOW"* ]]; then
        # Validate current active workflow (if it exists)
        PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
        ACTIVE_WORKFLOW_LINK="$PROJECT_DIR/.claude/ACTIVE_WORKFLOW"

        if [[ -L "$ACTIVE_WORKFLOW_LINK" ]]; then
            WORKFLOW_FILE=$(readlink "$ACTIVE_WORKFLOW_LINK" 2>/dev/null) || WORKFLOW_FILE=""
        fi
    fi

    # Validate workflow file if we have one
    if [[ -n "$WORKFLOW_FILE" ]] && [[ -f "$WORKFLOW_FILE" ]]; then
        SCHEMA_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/schemas/workflow.schema.json"

        # Only validate if schema exists
        if [[ -f "$SCHEMA_FILE" ]]; then
            # yq is required for workflow validation (RF-010: removed grep fallback)
            if ! command -v yq >/dev/null 2>&1; then
                echo "ERROR: yq is required for workflow validation but not found" >&2
                echo "       Install with: brew install yq (macOS) or apt-get install yq (Linux)" >&2
                log_end 2 2>/dev/null || true
                exit 2
            fi

            # Perform yq validation
            workflow_json=$(yq -o=json eval "$WORKFLOW_FILE" 2>&1)
            yq_status=$?

            if [[ $yq_status -ne 0 ]]; then
                echo "ERROR: Invalid YAML syntax in $WORKFLOW_FILE" >&2
                echo "$workflow_json" >&2
                log_end 2 2>/dev/null || true
                exit 2
            fi

            # Extract required fields from schema and validate
            required_fields=$(jq -r '.required[]' "$SCHEMA_FILE" 2>/dev/null) || required_fields=""

            for field in $required_fields; do
                if ! echo "$workflow_json" | jq -e ".$field" >/dev/null 2>&1; then
                    echo "ERROR: Missing required field '$field' in $WORKFLOW_FILE" >&2
                    log_end 2 2>/dev/null || true
                    exit 2
                fi
            done

            # Validate workflow_type enum
            workflow_type=$(echo "$workflow_json" | jq -r '.workflow_type // empty' 2>/dev/null) || workflow_type=""
            if [[ -n "$workflow_type" ]]; then
                if [[ ! "$workflow_type" =~ ^(sequential|parallel|hybrid)$ ]]; then
                    echo "ERROR: Invalid workflow_type '$workflow_type' in $WORKFLOW_FILE" >&2
                    echo "       Must be one of: sequential, parallel, hybrid" >&2
                    log_end 2 2>/dev/null || true
                    exit 2
                fi
            fi

            # Validate phases is non-empty array
            phases_count=$(echo "$workflow_json" | jq '.phases | length' 2>/dev/null) || phases_count="0"
            if [[ -z "$phases_count" ]] || [[ "$phases_count" -eq 0 ]]; then
                echo "ERROR: Workflow must have at least one phase in $WORKFLOW_FILE" >&2
                log_end 2 2>/dev/null || true
                exit 2
            fi

            # Validate each phase has required fields
            phase_errors=$(echo "$workflow_json" | jq -r '
                .phases | to_entries | map(
                    select(.value.name == null or .value.agent == null) |
                    "Phase \(.key): missing required field (name or agent)"
                ) | .[]
            ' 2>/dev/null) || phase_errors=""

            if [[ -n "$phase_errors" ]]; then
                echo "ERROR: Invalid phase definitions in $WORKFLOW_FILE:" >&2
                echo "$phase_errors" >&2
                log_end 2 2>/dev/null || true
                exit 2
            fi

            # Validate entry_point has required agent field
            if ! echo "$workflow_json" | jq -e '.entry_point.agent' >/dev/null 2>&1; then
                echo "ERROR: entry_point must have 'agent' field in $WORKFLOW_FILE" >&2
                log_end 2 2>/dev/null || true
                exit 2
            fi
        fi
    fi
fi

# =============================================================================
# Default: Allow command (no validation triggered)
# =============================================================================

log_end 0 2>/dev/null || true
exit 0
