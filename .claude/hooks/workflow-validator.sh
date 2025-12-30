#!/bin/bash
# PreToolUse (Bash) hook - validate workflow.yaml operations
# - Fires on swap-team.sh commands or ACTIVE_WORKFLOW references
# - Validates workflow.yaml against JSON schema
# - Blocks invalid workflows with clear error messages

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Source logging library
source "$SCRIPT_DIR/lib/logging.sh" 2>/dev/null && log_init "workflow-validator" && log_start || true

# Read JSON input from stdin
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Only validate commands that involve workflow operations
if [[ "$COMMAND" != *"swap-team"* ]] && [[ "$COMMAND" != *"ACTIVE_WORKFLOW"* ]]; then
  exit 0
fi

# Extract target team from swap-team.sh command
# Handles: swap-team.sh teamname, ~/Code/roster/swap-team.sh teamname
if [[ "$COMMAND" == *"swap-team"* ]]; then
  TARGET_TEAM=$(echo "$COMMAND" | grep -oE 'swap-team\.sh[[:space:]]+([^[:space:]|&;]+)' | awk '{print $2}')

  # Skip validation for --list or no argument
  if [ -z "$TARGET_TEAM" ] || [ "$TARGET_TEAM" = "--list" ]; then
    exit 0
  fi

  # Note: ROSTER_HOME is defined in config.sh (sourced via logging.sh)
  ROSTER_DIR="$ROSTER_HOME/teams"
  WORKFLOW_FILE="$ROSTER_DIR/$TARGET_TEAM/workflow.yaml"
elif [[ "$COMMAND" == *"ACTIVE_WORKFLOW"* ]]; then
  # Validate current active workflow (if it exists)
  PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
  ACTIVE_WORKFLOW_LINK="$PROJECT_DIR/.claude/ACTIVE_WORKFLOW"

  if [ -L "$ACTIVE_WORKFLOW_LINK" ]; then
    WORKFLOW_FILE=$(readlink "$ACTIVE_WORKFLOW_LINK")
  else
    # No active workflow to validate
    exit 0
  fi
else
  exit 0
fi

# Check if workflow file exists
if [ ! -f "$WORKFLOW_FILE" ]; then
  # Not blocking - team-validator.sh handles missing teams
  exit 0
fi

# Validate workflow.yaml against schema
SCHEMA_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/schemas/workflow.schema.json"

if [ ! -f "$SCHEMA_FILE" ]; then
  # Schema not found - skip validation (don't block)
  exit 0
fi

# Validation strategy:
# 1. Try yq + jq schema validation (most reliable)
# 2. Fall back to grep-based structural validation

validate_with_yq() {
  local workflow="$1"
  local schema="$2"

  # Check if yq is available
  if ! command -v yq >/dev/null 2>&1; then
    return 1
  fi

  # Convert YAML to JSON for schema validation
  local workflow_json
  workflow_json=$(yq -o=json eval "$workflow" 2>&1)
  if [ $? -ne 0 ]; then
    echo "ERROR: Invalid YAML syntax in $workflow" >&2
    echo "$workflow_json" >&2
    return 2
  fi

  # Extract required fields from schema
  local required_fields
  required_fields=$(jq -r '.required[]' "$schema" 2>/dev/null)

  # Check each required field exists
  for field in $required_fields; do
    if ! echo "$workflow_json" | jq -e ".$field" >/dev/null 2>&1; then
      echo "ERROR: Missing required field '$field' in $workflow" >&2
      return 2
    fi
  done

  # Validate workflow_type enum
  local workflow_type
  workflow_type=$(echo "$workflow_json" | jq -r '.workflow_type // empty' 2>/dev/null)
  if [ -n "$workflow_type" ]; then
    if [[ ! "$workflow_type" =~ ^(sequential|parallel|hybrid)$ ]]; then
      echo "ERROR: Invalid workflow_type '$workflow_type' in $workflow" >&2
      echo "       Must be one of: sequential, parallel, hybrid" >&2
      return 2
    fi
  fi

  # Validate phases is non-empty array
  local phases_count
  phases_count=$(echo "$workflow_json" | jq '.phases | length' 2>/dev/null)
  if [ -z "$phases_count" ] || [ "$phases_count" -eq 0 ]; then
    echo "ERROR: Workflow must have at least one phase in $workflow" >&2
    return 2
  fi

  # Validate each phase has required fields
  local phase_errors
  phase_errors=$(echo "$workflow_json" | jq -r '
    .phases | to_entries | map(
      select(.value.name == null or .value.agent == null) |
      "Phase \(.key): missing required field (name or agent)"
    ) | .[]
  ' 2>/dev/null)

  if [ -n "$phase_errors" ]; then
    echo "ERROR: Invalid phase definitions in $workflow:" >&2
    echo "$phase_errors" >&2
    return 2
  fi

  # Validate entry_point has required agent field
  if ! echo "$workflow_json" | jq -e '.entry_point.agent' >/dev/null 2>&1; then
    echo "ERROR: entry_point must have 'agent' field in $workflow" >&2
    return 2
  fi

  return 0
}

validate_with_grep() {
  local workflow="$1"

  # Basic structural validation using grep
  local errors=()

  # Check required top-level fields
  if ! grep -q '^name:' "$workflow"; then
    errors+=("Missing required field: name")
  fi

  if ! grep -q '^workflow_type:' "$workflow"; then
    errors+=("Missing required field: workflow_type")
  fi

  if ! grep -q '^entry_point:' "$workflow"; then
    errors+=("Missing required field: entry_point")
  fi

  if ! grep -q '^phases:' "$workflow"; then
    errors+=("Missing required field: phases")
  fi

  # Validate workflow_type value
  local wf_type
  wf_type=$(grep '^workflow_type:' "$workflow" | sed 's/^workflow_type:[[:space:]]*//' | tr -d '\r')
  if [ -n "$wf_type" ] && [[ ! "$wf_type" =~ ^(sequential|parallel|hybrid)$ ]]; then
    errors+=("Invalid workflow_type: '$wf_type' (must be sequential, parallel, or hybrid)")
  fi

  # Check entry_point has agent
  if grep -q '^entry_point:' "$workflow"; then
    if ! sed -n '/^entry_point:/,/^[a-z_]/p' "$workflow" | grep -q '[[:space:]]\+agent:'; then
      errors+=("entry_point must have 'agent' field")
    fi
  fi

  # Check phases has at least one phase with name and agent
  if grep -q '^phases:' "$workflow"; then
    local phase_section
    phase_section=$(sed -n '/^phases:/,/^[a-z_]/p' "$workflow")

    if ! echo "$phase_section" | grep -q '[[:space:]]\+- name:'; then
      errors+=("phases must contain at least one phase with 'name' field")
    fi

    if ! echo "$phase_section" | grep -q '[[:space:]]\+agent:'; then
      errors+=("phases must contain at least one phase with 'agent' field")
    fi
  fi

  # Report errors if any
  if [ ${#errors[@]} -gt 0 ]; then
    echo "ERROR: Invalid workflow structure in $workflow:" >&2
    for error in "${errors[@]}"; do
      echo "  - $error" >&2
    done
    return 2
  fi

  return 0
}

# Run validation
validate_with_yq "$WORKFLOW_FILE" "$SCHEMA_FILE"
yq_result=$?

if [ $yq_result -eq 0 ]; then
  # Valid workflow - allow command
  log_end 0 2>/dev/null || true
  exit 0
elif [ $yq_result -eq 2 ]; then
  # Validation failed with yq
  log_error "Workflow validation failed" 2>/dev/null || true
  log_end 2 2>/dev/null || true
  exit 2
else
  # yq not available or failed, try grep-based validation
  if validate_with_grep "$WORKFLOW_FILE"; then
    # Valid workflow - allow command
    log_end 0 2>/dev/null || true
    exit 0
  else
    # Validation failed
    log_error "Workflow validation failed (grep)" 2>/dev/null || true
    log_end 2 2>/dev/null || true
    exit 2
  fi
fi
