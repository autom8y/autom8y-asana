#!/bin/bash
# PostToolUse (Write) hook - track artifact creation and agent handoffs
# Category: RECOVERABLE - can detect errors but must degrade gracefully
# Detects PRD/TDD/ADR/TP files and logs to session-specific artifacts.log
# Also tracks agent handoffs and task outcomes when detected

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Library Resolution - per ADR-0002
HOOKS_LIB="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/lib"
source "$HOOKS_LIB/hooks-init.sh"
hooks_init "artifact-tracker" "RECOVERABLE"

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
safe_source "$HOOKS_LIB/session-utils.sh" || exit 0

SESSION_DIR=$(get_session_dir)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Only track if session exists
if [ -z "$SESSION_DIR" ] || [ ! -d "$SESSION_DIR" ]; then
  hooks_finalize 0
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

    # FIXED (Atomicity): Update SESSION_CONTEXT with artifact location using atomic operations
    SESSION_CONTEXT="$SESSION_DIR/SESSION_CONTEXT.md"
    if [ -f "$SESSION_CONTEXT" ]; then
      # Read current content
      CURRENT_CONTENT=$(cat "$SESSION_CONTEXT")

      # Apply transformation based on artifact type
      case "$TYPE" in
        PRD)
          UPDATED_CONTENT=$(echo "$CURRENT_CONTENT" | sed "s|^- PRD:.*|- PRD: $FILE_PATH|")
          ;;
        TDD)
          UPDATED_CONTENT=$(echo "$CURRENT_CONTENT" | sed "s|^- TDD:.*|- TDD: $FILE_PATH|")
          ;;
        ADR)
          # Append ADR to list (there can be multiple)
          if ! echo "$CURRENT_CONTENT" | grep -q "- ADR:.*$BASENAME" 2>/dev/null; then
            UPDATED_CONTENT=$(echo "$CURRENT_CONTENT" | sed "/^## Artifacts/a\\
- ADR: $FILE_PATH
")
          else
            UPDATED_CONTENT="$CURRENT_CONTENT"
          fi
          ;;
        "Test Plan")
          UPDATED_CONTENT=$(echo "$CURRENT_CONTENT" | sed "s|^- Test Plan:.*|- Test Plan: $FILE_PATH|")
          ;;
        *)
          UPDATED_CONTENT="$CURRENT_CONTENT"
          ;;
      esac

      # Write atomically using atomic_write from session-utils
      if ! atomic_write "$SESSION_CONTEXT" "$UPDATED_CONTENT"; then
        echo '{"warning": "Failed to update SESSION_CONTEXT atomically"}' >&2
      fi
    fi

    echo "{\"systemMessage\": \"Artifact tracked: $TYPE ($BASENAME)\"}"
    hooks_finalize 0
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
    hooks_finalize 0
    exit 0
  fi
fi

# Detect handoff patterns in file writes
if [[ "$TOOL_NAME" == "Write" && "$FILE_PATH" =~ SESSION_CONTEXT\.md && -n "$TOOL_OUTPUT" ]]; then
  # Check if the write contains handoff markers
  if [[ "$TOOL_OUTPUT" =~ "Handoff:" || "$TOOL_OUTPUT" =~ "→" ]]; then
    echo "$TIMESTAMP | HANDOFF_DETECTED | $FILE_PATH" >> "$HANDOFFS_LOG"
    echo "{\"systemMessage\": \"Handoff activity tracked\"}"
    hooks_finalize 0
    exit 0
  fi
fi

hooks_finalize 0
exit 0
