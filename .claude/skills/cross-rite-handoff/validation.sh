#!/bin/bash
# validation.sh - HANDOFF artifact validation functions
# Usage: source validation.sh && validate_handoff "/path/to/HANDOFF-*.md"
# Returns: 0=valid, 1=not found, 2=no opener, 3=no closer, 4=missing field, 5=invalid field

set -euo pipefail

validate_handoff() {
    local file="$1"
    local required_fields=("artifact_id" "schema_version" "source_rite" "target_rite"
                           "handoff_type" "priority" "blocking" "initiative"
                           "created_at" "status" "items")

    # Check file exists
    [ -f "$file" ] || { echo "HANDOFF-001: File not found: $file" >&2; return 1; }

    # Check opening delimiter on line 1
    local first_line
    first_line=$(head -n 1 "$file")
    if [[ "$first_line" != "---" ]]; then
        echo "HANDOFF-001: Missing opening '---' delimiter on line 1" >&2
        return 2
    fi

    # Check closing delimiter within first 75 lines
    local closing_line
    closing_line=$(head -n 75 "$file" | tail -n +2 | grep -n "^---$" | head -1 | cut -d: -f1)
    if [[ -z "$closing_line" ]]; then
        echo "HANDOFF-001: Missing closing '---' delimiter within first 75 lines" >&2
        return 3
    fi

    # Extract frontmatter
    local frontmatter_end=$((closing_line + 1))
    local frontmatter
    frontmatter=$(sed -n "2,$((frontmatter_end))p" "$file" | sed '$d')

    # Check required fields
    local missing=()
    for field in "${required_fields[@]}"; do
        if ! echo "$frontmatter" | grep -q "^${field}:"; then
            missing+=("$field")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo "HANDOFF-010: Missing required fields: ${missing[*]}" >&2
        return 4
    fi

    # Validate artifact_id pattern
    local artifact_id
    artifact_id=$(echo "$frontmatter" | grep "^artifact_id:" | sed 's/artifact_id: *//' | tr -d '"')
    if [[ ! "$artifact_id" =~ ^HANDOFF-[a-z0-9-]+-to-[a-z0-9-]+-[0-9]{4}-[0-9]{2}-[0-9]{2}(-[0-9]+)?$ ]]; then
        echo "HANDOFF-001: Invalid artifact_id pattern: $artifact_id" >&2
        return 5
    fi

    # Validate schema_version
    local schema_version
    schema_version=$(echo "$frontmatter" | grep "^schema_version:" | sed 's/schema_version: *//' | tr -d '"')
    if [[ "$schema_version" != "1.0" ]]; then
        echo "HANDOFF-011: Invalid schema_version: $schema_version (must be 1.0)" >&2
        return 5
    fi

    # Validate source_rite != target_rite
    local source_rite target_rite
    source_rite=$(echo "$frontmatter" | grep "^source_rite:" | sed 's/source_rite: *//' | tr -d '"')
    target_rite=$(echo "$frontmatter" | grep "^target_rite:" | sed 's/target_rite: *//' | tr -d '"')
    if [[ "$source_rite" == "$target_rite" ]]; then
        echo "HANDOFF-030: source_rite and target_rite must be different" >&2
        return 5
    fi

    # Validate handoff_type enum
    local handoff_type
    handoff_type=$(echo "$frontmatter" | grep "^handoff_type:" | sed 's/handoff_type: *//' | tr -d '"')
    if [[ ! "$handoff_type" =~ ^(execution|validation|assessment|implementation|strategic_input|strategic_evaluation)$ ]]; then
        echo "HANDOFF-004: Invalid handoff_type: $handoff_type" >&2
        return 5
    fi

    # Validate priority enum
    local priority
    priority=$(echo "$frontmatter" | grep "^priority:" | sed 's/priority: *//' | tr -d '"')
    if [[ ! "$priority" =~ ^(critical|high|medium|low)$ ]]; then
        echo "HANDOFF-005: Invalid priority: $priority" >&2
        return 5
    fi

    # Validate blocking boolean
    local blocking
    blocking=$(echo "$frontmatter" | grep "^blocking:" | sed 's/blocking: *//' | tr -d '"')
    if [[ ! "$blocking" =~ ^(true|false)$ ]]; then
        echo "HANDOFF-006: Invalid blocking value: $blocking (must be true or false)" >&2
        return 5
    fi

    # Validate status enum
    local handoff_status
    handoff_status=$(echo "$frontmatter" | grep "^status:" | sed 's/status: *//' | tr -d '"')
    if [[ ! "$handoff_status" =~ ^(pending|in_progress|completed|rejected)$ ]]; then
        echo "HANDOFF-009: Invalid status: $handoff_status" >&2
        return 5
    fi

    # Validate rejection requires reason
    if [[ "$handoff_status" == "rejected" ]]; then
        if ! echo "$frontmatter" | grep -q "^rejection_reason:"; then
            echo "HANDOFF-031: rejected status requires rejection_reason field" >&2
            return 5
        fi
    fi

    # Warning: If blocking is true, priority should be critical or high
    if [[ "$blocking" == "true" && ! "$priority" =~ ^(critical|high)$ ]]; then
        echo "HANDOFF-033: Warning: blocking is true but priority is $priority (should be critical or high)" >&2
    fi

    # Validate items array is present and non-empty
    if ! echo "$frontmatter" | grep -q "^items:"; then
        echo "HANDOFF-010: Missing items array" >&2
        return 4
    fi

    # Basic check that items array has at least one item
    # This is a simplified check - full item validation would require proper YAML parsing
    local items_section
    items_section=$(echo "$frontmatter" | sed -n '/^items:/,$p')
    if ! echo "$items_section" | grep -q "^  - id:"; then
        echo "HANDOFF-010: items array must contain at least one item" >&2
        return 4
    fi

    # Note: Type-specific field validation (HANDOFF-023, HANDOFF-024, HANDOFF-025)
    # requires full YAML parsing and is beyond the scope of basic bash validation.
    # Consider using yq or a dedicated YAML validator for complete validation.

    return 0
}

# Export for use by other scripts
export -f validate_handoff
