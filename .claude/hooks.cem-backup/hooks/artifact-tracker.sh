#!/bin/bash
# PostToolUse (Write) hook - track artifact creation and agent handoffs
# Detects PRD/TDD/ADR/TP files and logs to session-specific artifacts.log
# Also tracks agent handoffs and task outcomes when detected

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Source logging library
source "$SCRIPT_DIR/lib/logging.sh" 2>/dev/null && log_init "artifact-tracker" && log_start || true

# Read JSON input from stdin
INPUT=$(cat)

# Extract tool name and inputs
if command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
  FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
  TOOL_OUTPUT=$(echo "$INPUT" | jq -r '.tool_output // empty' 2>/dev/null)
else
  # Fallback: grep-based JSON parsing
  TOOL_NAME=$(echo "$INPUT" | grep -o '"tool_name": *"[^"]*"' 2>/dev/null | head -1 | cut -d'"' -f4)
  FILE_PATH=$(echo "$INPUT" | grep -o '"file_path": *"[^"]*"' 2>/dev/null | head -1 | cut -d'"' -f4)
  TOOL_OUTPUT=$(echo "$INPUT" | grep -o '"tool_output": *"[^"]*"' 2>/dev/null | head -1 | cut -d'"' -f4)
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" 2>/dev/null || true

# Source session utilities
source .claude/hooks/lib/session-utils.sh 2>/dev/null || exit 0

SESSION_DIR=$(get_session_dir)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Only track if session exists
if [ -z "$SESSION_DIR" ] || [ ! -d "$SESSION_DIR" ]; then
  exit 0
fi

ARTIFACTS_LOG="$SESSION_DIR/artifacts.log"
HANDOFFS_LOG="$SESSION_DIR/handoffs.log"

# Track Write tool for artifacts
if [[ "$TOOL_NAME" == "Write" && -n "$FILE_PATH" ]]; then
  # Detect artifact type from path pattern
  TYPE=""
  case "$FILE_PATH" in
    */docs/requirements/PRD-*.md) TYPE="PRD" ;;
    */docs/design/TDD-*.md) TYPE="TDD" ;;
    */docs/design/ADR-*.md) TYPE="ADR" ;;
    */docs/testing/TP-*.md) TYPE="Test Plan" ;;
    */docs/test/TP-*.md) TYPE="Test Plan" ;;
  esac

  if [ -n "$TYPE" ]; then
    BASENAME=$(basename "$FILE_PATH")
    echo "$TIMESTAMP | $TYPE | $FILE_PATH" >> "$ARTIFACTS_LOG"

    # Update SESSION_CONTEXT with artifact location
    SESSION_CONTEXT="$SESSION_DIR/SESSION_CONTEXT.md"
    if [ -f "$SESSION_CONTEXT" ]; then
      # Update the Artifacts section
      case "$TYPE" in
        PRD)
          sed -i.bak "s|^- PRD:.*|- PRD: $FILE_PATH|" "$SESSION_CONTEXT" 2>/dev/null && rm -f "$SESSION_CONTEXT.bak"
          ;;
        TDD)
          sed -i.bak "s|^- TDD:.*|- TDD: $FILE_PATH|" "$SESSION_CONTEXT" 2>/dev/null && rm -f "$SESSION_CONTEXT.bak"
          ;;
        ADR)
          # Append ADR to list (there can be multiple)
          if ! grep -q "- ADR:.*$BASENAME" "$SESSION_CONTEXT" 2>/dev/null; then
            sed -i.bak "/^## Artifacts/a\\
- ADR: $FILE_PATH
" "$SESSION_CONTEXT" 2>/dev/null && rm -f "$SESSION_CONTEXT.bak"
          fi
          ;;
        "Test Plan")
          sed -i.bak "s|^- Test Plan:.*|- Test Plan: $FILE_PATH|" "$SESSION_CONTEXT" 2>/dev/null && rm -f "$SESSION_CONTEXT.bak"
          ;;
      esac
    fi

    echo "{\"systemMessage\": \"Artifact tracked: $TYPE ($BASENAME)\"}"
    exit 0
  fi
fi

# Track Task tool invocations (detect from output patterns)
# Task tool would contain agent names and results in output
if [[ "$TOOL_OUTPUT" =~ (Requirements Analyst|Architect|Principal Engineer|QA|Adversary) ]]; then
  # Extract agent information from output
  AGENT_MENTIONED=""
  if [[ "$TOOL_OUTPUT" =~ "Requirements Analyst" ]]; then
    AGENT_MENTIONED="requirements-analyst"
  elif [[ "$TOOL_OUTPUT" =~ "Architect" ]]; then
    AGENT_MENTIONED="architect"
  elif [[ "$TOOL_OUTPUT" =~ "Principal Engineer" ]]; then
    AGENT_MENTIONED="principal-engineer"
  elif [[ "$TOOL_OUTPUT" =~ "QA" || "$TOOL_OUTPUT" =~ "Adversary" ]]; then
    AGENT_MENTIONED="qa-adversary"
  fi

  if [ -n "$AGENT_MENTIONED" ]; then
    echo "$TIMESTAMP | AGENT_INVOCATION | $AGENT_MENTIONED" >> "$HANDOFFS_LOG"

    # Track in SESSION_CONTEXT if it looks like a handoff
    SESSION_CONTEXT="$SESSION_DIR/SESSION_CONTEXT.md"
    if [ -f "$SESSION_CONTEXT" ]; then
      # Add handoff note to Next Steps section
      cat >> "$SESSION_CONTEXT" <<HANDOFF

### Agent Activity: $AGENT_MENTIONED
**Time**: $TIMESTAMP
**Status**: Invoked via Task tool

HANDOFF
    fi

    echo "{\"systemMessage\": \"Agent invocation tracked: $AGENT_MENTIONED\"}"
    exit 0
  fi
fi

# Detect handoff patterns in file writes
if [[ "$TOOL_NAME" == "Write" && "$FILE_PATH" =~ SESSION_CONTEXT\.md && -n "$TOOL_OUTPUT" ]]; then
  # Check if the write contains handoff markers
  if [[ "$TOOL_OUTPUT" =~ "Handoff:" || "$TOOL_OUTPUT" =~ "→" ]]; then
    echo "$TIMESTAMP | HANDOFF_DETECTED | $FILE_PATH" >> "$HANDOFFS_LOG"
    echo "{\"systemMessage\": \"Handoff activity tracked\"}"
    exit 0
  fi
fi

log_end 0 2>/dev/null || true
exit 0
