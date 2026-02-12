---
schema_name: tdd
schema_version: "1.0"
file_pattern: "docs/design/TDD-*.md"
artifact_type: tdd
---

# TDD Schema

> Canonical schema for Technical Design Documents at `docs/design/TDD-{slug}.md`

## YAML Frontmatter

```yaml
---
# Required fields
artifact_id: string        # Pattern: TDD-{slug} (e.g., "TDD-user-auth")
title: string              # Human-readable title
created_at: string         # ISO 8601 timestamp
author: string             # Agent or user who created (e.g., "architect")
prd_ref: string            # Reference to source PRD (e.g., "PRD-user-auth")
status: enum               # draft | review | approved | superseded

# Components (at least one required)
components:
  - name: string           # Component name
    type: enum             # service | library | module | script | config
    description: string    # What this component does
    dependencies: array    # Other components or external deps

# Optional technical sections
api_contracts: array       # API endpoint definitions
data_models: array         # Data structure definitions
sequence_diagrams: array   # Interaction flows
security_considerations: array  # Security requirements

# Metadata
superseded_by: string      # TDD ID if this is superseded
related_adrs: array        # ADR references for design decisions

# Schema versioning
schema_version: "1.0"      # Must be "1.0" for this version
---
```

## Required Fields

| Field | Type | Description | Set By |
|-------|------|-------------|--------|
| `artifact_id` | string | Unique identifier, pattern: `TDD-{slug}` | architect |
| `title` | string | Human-readable title | architect |
| `created_at` | string | ISO 8601 creation timestamp | architect |
| `author` | string | Creating agent or user | architect |
| `prd_ref` | string | Reference to source PRD | architect |
| `status` | enum | Current lifecycle status | architect, reviewer |
| `components` | array | System components (min 1) | architect |
| `schema_version` | string | Schema version for compatibility | architect |

## Optional Fields

| Field | Type | Description | Set By |
|-------|------|-------------|--------|
| `api_contracts` | array | API endpoint definitions | architect |
| `data_models` | array | Data structure definitions | architect |
| `sequence_diagrams` | array | Interaction flow references | architect |
| `security_considerations` | array | Security requirements | architect |
| `superseded_by` | string | Reference to replacing TDD | architect |
| `related_adrs` | array | ADR references for decisions | architect |

## Component Object Schema

```yaml
components:
  - name: string           # "AuthService", "UserRepository"
    type: enum             # service | library | module | script | config
    description: string    # Clear purpose statement
    dependencies:          # What this depends on
      - name: string       # Dependency name
        type: enum         # internal | external
        version: string    # Version constraint (optional)
    interfaces:            # (optional) Exposed APIs
      - name: string
        signature: string
    files:                 # (optional) Implementation files
      - string
```

## API Contract Object Schema

```yaml
api_contracts:
  - endpoint: string       # "/api/v1/auth/login"
    method: enum           # GET | POST | PUT | DELETE | PATCH
    description: string    # What this endpoint does
    request:
      headers: object      # Required headers
      body: object         # Request body schema
    response:
      success:
        status: integer    # 200, 201, etc.
        body: object       # Response body schema
      errors:
        - status: integer  # 400, 401, 404, etc.
          description: string
```

## Data Model Object Schema

```yaml
data_models:
  - name: string           # "User", "Session"
    type: enum             # entity | value_object | aggregate | dto
    fields:
      - name: string       # Field name
        type: string       # Data type
        required: boolean  # Is field required
        constraints: string  # Validation rules
    relationships:         # (optional)
      - target: string     # Related model
        type: enum         # one-to-one | one-to-many | many-to-many
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
2. File MUST have closing `---` within first 100 lines
3. Content between delimiters MUST be valid YAML

### Field Validation
1. `artifact_id` MUST match pattern `^TDD-[a-z0-9-]+$`
2. `prd_ref` MUST match pattern `^PRD-[a-z0-9-]+$`
3. `created_at` MUST be valid ISO 8601 timestamp
4. `status` MUST be one of: draft, review, approved, superseded
5. `components` MUST be array with at least one item
6. `schema_version` MUST be "1.0"

### Component Validation
1. Each component MUST have `name`, `type`, `description` fields
2. `type` MUST be one of: service, library, module, script, config

## Example: Valid TDD

```yaml
---
artifact_id: TDD-user-authentication
title: "User Authentication Technical Design"
created_at: "2025-12-29T11:00:00Z"
author: architect
prd_ref: PRD-user-authentication
status: approved
components:
  - name: AuthService
    type: service
    description: "Handles user authentication and session management"
    dependencies:
      - name: UserRepository
        type: internal
      - name: bcrypt
        type: external
        version: "^5.0.0"
    interfaces:
      - name: login
        signature: "login(email: string, password: string) -> Session"
      - name: logout
        signature: "logout(sessionId: string) -> void"
  - name: UserRepository
    type: module
    description: "Data access layer for user entities"
    dependencies:
      - name: PostgreSQL
        type: external
api_contracts:
  - endpoint: "/api/v1/auth/login"
    method: POST
    description: "Authenticate user and create session"
    request:
      headers:
        Content-Type: "application/json"
      body:
        email: string
        password: string
    response:
      success:
        status: 200
        body:
          token: string
          expires_at: string
      errors:
        - status: 401
          description: "Invalid credentials"
        - status: 429
          description: "Rate limit exceeded"
data_models:
  - name: User
    type: entity
    fields:
      - name: id
        type: uuid
        required: true
      - name: email
        type: string
        required: true
        constraints: "unique, valid email format"
      - name: password_hash
        type: string
        required: true
  - name: Session
    type: entity
    fields:
      - name: id
        type: uuid
        required: true
      - name: user_id
        type: uuid
        required: true
      - name: expires_at
        type: timestamp
        required: true
related_adrs:
  - ADR-001
  - ADR-003
schema_version: "1.0"
---

## Overview

This TDD provides the technical design for implementing user authentication...

## Architecture Diagram

```
[Client] --> [AuthService] --> [UserRepository] --> [PostgreSQL]
                |
                v
            [SessionStore]
```

## Implementation Notes

### Security
- Passwords stored using bcrypt with cost factor 12
- Sessions expire after 24 hours
- Rate limiting: 5 attempts per 15 minutes

### Error Handling
- All authentication failures return generic 401
- Rate limit violations return 429 with Retry-After header
```

## Validation Function

```bash
# In artifact-validator.sh
# Usage: validate_tdd "/path/to/TDD-example.md"
# Returns: 0=valid, 1=not found, 2=no opener, 3=no closer, 4=missing field, 5=invalid field

validate_tdd() {
    local file="$1"
    local required_fields=("artifact_id" "title" "created_at" "author" "prd_ref" "status" "components" "schema_version")

    # Check file exists
    [ -f "$file" ] || { echo "File not found: $file" >&2; return 1; }

    # Check opening delimiter on line 1
    local first_line
    first_line=$(head -n 1 "$file")
    if [[ "$first_line" != "---" ]]; then
        echo "Invalid format: Missing opening '---' delimiter on line 1" >&2
        return 2
    fi

    # Check closing delimiter within first 100 lines
    local closing_line
    closing_line=$(head -n 100 "$file" | tail -n +2 | grep -n "^---$" | head -1 | cut -d: -f1)
    if [[ -z "$closing_line" ]]; then
        echo "Invalid format: Missing closing '---' delimiter within first 100 lines" >&2
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
    if [[ ! "$artifact_id" =~ ^TDD-[a-z0-9-]+$ ]]; then
        echo "Invalid artifact_id: Must match pattern TDD-{slug}" >&2
        return 5
    fi

    # Validate prd_ref pattern
    local prd_ref
    prd_ref=$(echo "$frontmatter" | grep "^prd_ref:" | sed 's/prd_ref: *//' | tr -d '"')
    if [[ ! "$prd_ref" =~ ^PRD-[a-z0-9-]+$ ]]; then
        echo "Invalid prd_ref: Must match pattern PRD-{slug}" >&2
        return 5
    fi

    return 0
}
```

## Handoff Criteria

When TDD phase completes, orchestrator verifies:

- [ ] `artifact_id` matches file name pattern
- [ ] `prd_ref` references existing approved PRD
- [ ] `status` is "approved" (not draft or review)
- [ ] At least one `component` with clear interfaces
- [ ] API contracts match PRD success criteria

## Relationship to Other Artifacts

```
TDD-{slug}.md
    |
    +-- References PRD (tdd.prd_ref)
    |
    +-- Referenced by Test Plan (test_plan.tdd_ref)
    |
    +-- Components guide implementation
    |
    +-- API contracts guide integration tests
```
