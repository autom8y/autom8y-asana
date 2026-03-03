---
schema_name: prd
schema_version: "1.0"
file_pattern: ".ledge/specs/PRD-*.md"
artifact_type: prd
---

# PRD Schema

> Canonical schema for Product Requirements Documents at `.ledge/specs/PRD-{slug}.md`

## YAML Frontmatter

```yaml
---
# Required fields
artifact_id: string        # Pattern: PRD-{slug} (e.g., "PRD-user-auth")
title: string              # Human-readable title
created_at: string         # ISO 8601 timestamp
author: string             # Agent or user who created (e.g., "requirements-analyst")
status: enum               # draft | review | approved | superseded
complexity: enum           # SCRIPT | MODULE | SERVICE | PLATFORM

# Success criteria (at least one required)
success_criteria:
  - id: string             # SC-001, SC-002, etc.
    description: string    # What must be true for success
    testable: boolean      # Can this be verified by test?
    priority: enum         # must-have | should-have | nice-to-have

# Optional fields
superseded_by: string      # PRD ID if this is superseded
related_adrs: array        # ADR references
stakeholders: array        # Who needs to approve
target_release: string     # Version or date target

# Schema versioning
schema_version: "1.0"      # Must be "1.0" for this version
---
```

## Required Fields

| Field | Type | Description | Set By |
|-------|------|-------------|--------|
| `artifact_id` | string | Unique identifier, pattern: `PRD-{slug}` | requirements-analyst |
| `title` | string | Human-readable title | requirements-analyst |
| `created_at` | string | ISO 8601 creation timestamp | requirements-analyst |
| `author` | string | Creating agent or user | requirements-analyst |
| `status` | enum | Current lifecycle status | requirements-analyst, reviewer |
| `complexity` | enum | Scope classification | orchestrator |
| `success_criteria` | array | Testable success conditions (min 1) | requirements-analyst |
| `schema_version` | string | Schema version for compatibility | requirements-analyst |

## Optional Fields

| Field | Type | Description | Set By |
|-------|------|-------------|--------|
| `superseded_by` | string | Reference to replacing PRD | requirements-analyst |
| `related_adrs` | array | ADR references for decisions | architect |
| `stakeholders` | array | Approval authorities | requirements-analyst |
| `target_release` | string | Target version/date | product owner |

## Success Criterion Object Schema

```yaml
success_criteria:
  - id: string             # "SC-001" format
    description: string    # Clear, testable statement
    testable: boolean      # true if can be verified by test
    priority: enum         # must-have | should-have | nice-to-have
    verification: string   # (optional) How to verify
    linked_tests: array    # (optional) Test case IDs
```

## Valid Status Transitions

```
draft --review--> review
review --approve--> approved
review --reject--> draft
approved --supersede--> superseded
```

## Validation Rules

### Structure Validation
1. File MUST start with `---` on line 1
2. File MUST have closing `---` within first 50 lines
3. Content between delimiters MUST be valid YAML

### Field Validation
1. `artifact_id` MUST match pattern `^PRD-[a-z0-9-]+$`
2. `created_at` MUST be valid ISO 8601 timestamp
3. `status` MUST be one of: draft, review, approved, superseded
4. `complexity` MUST be one of: SCRIPT, MODULE, SERVICE, PLATFORM
5. `success_criteria` MUST be array with at least one item
6. `schema_version` MUST be "1.0"

### Success Criteria Validation
1. Each criterion MUST have `id`, `description`, `testable` fields
2. `id` MUST match pattern `^SC-[0-9]+$`
3. `testable` MUST be boolean
4. `priority` MUST be one of: must-have, should-have, nice-to-have

## Example: Valid PRD

```yaml
---
artifact_id: PRD-user-authentication
title: "User Authentication System"
created_at: "2025-12-29T10:00:00Z"
author: requirements-analyst
status: approved
complexity: MODULE
success_criteria:
  - id: SC-001
    description: "Users can register with email and password"
    testable: true
    priority: must-have
  - id: SC-002
    description: "Users can log in with valid credentials"
    testable: true
    priority: must-have
  - id: SC-003
    description: "Failed login attempts are rate-limited"
    testable: true
    priority: should-have
stakeholders:
  - product-owner
  - security-team
target_release: "v2.0"
schema_version: "1.0"
---

## Overview

This PRD defines requirements for implementing user authentication...

## User Stories

### US-001: User Registration
As a new user, I want to register with my email...

## Acceptance Criteria

- [ ] SC-001: Registration endpoint accepts email/password
- [ ] SC-002: Login returns JWT on success
- [ ] SC-003: Rate limiting after 5 failed attempts

## Out of Scope

- Social login (OAuth) - future PRD
- Multi-factor authentication - future PRD
```

## Validation Function

```bash
# In artifact-validator.sh
# Usage: validate_prd "/path/to/PRD-example.md"
# Returns:
#   0 = valid
#   1 = file not found
#   2 = missing opening --- delimiter
#   3 = missing closing --- delimiter (within first 50 lines)
#   4 = missing required field (field name in stderr)
#   5 = field validation failed (details in stderr)

validate_prd() {
    local file="$1"
    local required_fields=("artifact_id" "title" "created_at" "author" "status" "complexity" "success_criteria" "schema_version")

    # Check file exists
    [ -f "$file" ] || { echo "File not found: $file" >&2; return 1; }

    # Check opening delimiter on line 1
    local first_line
    first_line=$(head -n 1 "$file")
    if [[ "$first_line" != "---" ]]; then
        echo "Invalid format: Missing opening '---' delimiter on line 1" >&2
        return 2
    fi

    # Check closing delimiter within first 50 lines
    local closing_line
    closing_line=$(head -n 50 "$file" | tail -n +2 | grep -n "^---$" | head -1 | cut -d: -f1)
    if [[ -z "$closing_line" ]]; then
        echo "Invalid format: Missing closing '---' delimiter within first 50 lines" >&2
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
        echo "Missing required fields: ${missing[*]}" >&2
        return 4
    fi

    # Validate artifact_id pattern
    local artifact_id
    artifact_id=$(echo "$frontmatter" | grep "^artifact_id:" | sed 's/artifact_id: *//' | tr -d '"')
    if [[ ! "$artifact_id" =~ ^PRD-[a-z0-9-]+$ ]]; then
        echo "Invalid artifact_id: Must match pattern PRD-{slug}" >&2
        return 5
    fi

    # Validate status enum
    local status
    status=$(echo "$frontmatter" | grep "^status:" | sed 's/status: *//' | tr -d '"')
    if [[ ! "$status" =~ ^(draft|review|approved|superseded)$ ]]; then
        echo "Invalid status: Must be draft, review, approved, or superseded" >&2
        return 5
    fi

    return 0
}
```

## Handoff Criteria

When PRD phase completes, orchestrator verifies:

- [ ] `artifact_id` matches file name pattern
- [ ] `status` is "approved" (not draft or review)
- [ ] At least one `success_criteria` with `testable: true`
- [ ] All `must-have` criteria have clear descriptions

## Relationship to Other Artifacts

```
PRD-{slug}.md
    |
    +-- Referenced by TDD (tdd.prd_ref)
    |
    +-- Referenced by Test Plan (test_plan.prd_ref)
    |
    +-- Success criteria linked to Test Cases
```
