---
schema_name: adr
schema_version: "1.0"
file_pattern: "docs/design/ADR-*.md"
artifact_type: adr
---

# ADR Schema

> Canonical schema for Architecture Decision Records at `docs/design/ADR-{number}.md`

## YAML Frontmatter

```yaml
---
# Required fields
artifact_id: string        # Pattern: ADR-{number} (e.g., "ADR-001")
title: string              # Decision title (concise)
created_at: string         # ISO 8601 timestamp
author: string             # Agent or user who created (e.g., "architect")
status: enum               # proposed | accepted | deprecated | superseded

# Decision record
context: string            # Why this decision is needed (1-3 sentences)
decision: string           # What was decided (1-2 sentences)
consequences:              # Outcomes of this decision
  - type: enum             # positive | negative | neutral
    description: string    # What happens as a result

# Supersession chain (optional)
supersedes: string         # ADR ID this replaces (e.g., "ADR-003")
superseded_by: string      # ADR ID that replaces this

# References
related_artifacts: array   # PRDs, TDDs, or other ADRs
tags: array                # Categorization tags

# Schema versioning
schema_version: "1.0"      # Must be "1.0" for this version
---
```

## Required Fields

| Field | Type | Description | Set By |
|-------|------|-------------|--------|
| `artifact_id` | string | Unique identifier, pattern: `ADR-{number}` | architect |
| `title` | string | Concise decision title | architect |
| `created_at` | string | ISO 8601 creation timestamp | architect |
| `author` | string | Creating agent or user | architect |
| `status` | enum | Current lifecycle status | architect, team |
| `context` | string | Why this decision is needed | architect |
| `decision` | string | What was decided | architect |
| `consequences` | array | Outcomes (min 1) | architect |
| `schema_version` | string | Schema version for compatibility | architect |

## Optional Fields

| Field | Type | Description | Set By |
|-------|------|-------------|--------|
| `supersedes` | string | ADR ID this decision replaces | architect |
| `superseded_by` | string | ADR ID that replaces this | architect |
| `related_artifacts` | array | Referenced PRDs, TDDs, ADRs | architect |
| `tags` | array | Categorization (e.g., "security", "performance") | architect |

## Consequence Object Schema

```yaml
consequences:
  - type: enum             # positive | negative | neutral
    description: string    # Clear statement of outcome
    mitigation: string     # (optional) How to address if negative
```

## Valid Status Transitions

```
proposed --accept--> accepted
proposed --reject--> (deleted or never created)
accepted --deprecate--> deprecated
accepted --supersede--> superseded
deprecated --supersede--> superseded
```

## Validation Rules

### Structure Validation
1. File MUST start with `---` on line 1
2. File MUST have closing `---` within first 50 lines
3. Content between delimiters MUST be valid YAML

### Field Validation
1. `artifact_id` MUST match pattern `^ADR-[0-9]+$`
2. `created_at` MUST be valid ISO 8601 timestamp
3. `status` MUST be one of: proposed, accepted, deprecated, superseded
4. `context` MUST be non-empty string
5. `decision` MUST be non-empty string
6. `consequences` MUST be array with at least one item
7. `schema_version` MUST be "1.0"

### Consequence Validation
1. Each consequence MUST have `type`, `description` fields
2. `type` MUST be one of: positive, negative, neutral

### Supersession Validation
1. If `status` is "superseded", `superseded_by` MUST be set
2. If `supersedes` is set, referenced ADR should have `status: superseded`

## Example: Valid ADR

```yaml
---
artifact_id: ADR-001
title: "Use JWT for Session Management"
created_at: "2025-12-29T09:00:00Z"
author: architect
status: accepted
context: "We need a stateless authentication mechanism that works across multiple services and supports horizontal scaling without shared session storage."
decision: "Use JSON Web Tokens (JWT) with short-lived access tokens (15 min) and long-lived refresh tokens (7 days) for user authentication."
consequences:
  - type: positive
    description: "Stateless design enables horizontal scaling without session affinity"
  - type: positive
    description: "Reduced database load - no session lookup per request"
  - type: negative
    description: "Token revocation requires blacklist or short expiry"
    mitigation: "Implement token blacklist in Redis with TTL matching token expiry"
  - type: neutral
    description: "Requires client-side token storage and refresh logic"
related_artifacts:
  - PRD-user-authentication
  - TDD-user-authentication
tags:
  - security
  - authentication
  - scalability
schema_version: "1.0"
---

## Context

The system needs to authenticate users across multiple microservices. Traditional session-based authentication requires either sticky sessions or shared session storage, both of which complicate horizontal scaling.

## Decision

We will use JWT-based authentication with:
- Access tokens: 15-minute expiry, contains user ID and roles
- Refresh tokens: 7-day expiry, stored in database
- Token rotation on refresh

## Consequences

### Positive
- Stateless validation enables any service instance to verify tokens
- No session database queries for authentication
- Easy to implement in API gateways

### Negative
- Cannot immediately revoke access tokens (must wait for expiry)
- Refresh token rotation adds complexity
- Token size larger than session ID cookies

### Mitigation
- Short access token expiry (15 min) limits revocation window
- Redis blacklist for critical revocations
- Compress JWT payload to minimize size

## References
- RFC 7519 - JSON Web Token
- OWASP JWT Security Cheat Sheet
```

## Validation Function

```bash
# In artifact-validator.sh
# Usage: validate_adr "/path/to/ADR-001.md"
# Returns: 0=valid, 1=not found, 2=no opener, 3=no closer, 4=missing field, 5=invalid field

validate_adr() {
    local file="$1"
    local required_fields=("artifact_id" "title" "created_at" "author" "status" "context" "decision" "consequences" "schema_version")

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
    if [[ ! "$artifact_id" =~ ^ADR-[0-9]+$ ]]; then
        echo "Invalid artifact_id: Must match pattern ADR-{number}" >&2
        return 5
    fi

    # Validate status enum
    local status
    status=$(echo "$frontmatter" | grep "^status:" | sed 's/status: *//' | tr -d '"')
    if [[ ! "$status" =~ ^(proposed|accepted|deprecated|superseded)$ ]]; then
        echo "Invalid status: Must be proposed, accepted, deprecated, or superseded" >&2
        return 5
    fi

    return 0
}
```

## Handoff Criteria

When ADR is created or updated, validation verifies:

- [ ] `artifact_id` matches file name pattern
- [ ] `status` reflects current decision state
- [ ] `context` explains why decision is needed
- [ ] `decision` clearly states what was decided
- [ ] At least one consequence documented
- [ ] Supersession chain is consistent (if applicable)

## Relationship to Other Artifacts

```
ADR-{number}.md
    |
    +-- Referenced by TDD (tdd.related_adrs)
    |
    +-- Referenced by PRD (prd.related_adrs)
    |
    +-- May supersede other ADRs
    |
    +-- May be superseded by newer ADRs
```

## ADR Numbering

ADR numbers are sequential and never reused:
- ADR-001, ADR-002, ADR-003, ...
- Deprecated or superseded ADRs keep their number
- New ADRs get the next available number

## MADR Compatibility

This schema is compatible with the Markdown Any Decision Records (MADR) format. Key differences:
- Uses YAML frontmatter for machine parsing
- Consequences are structured objects, not prose
- Adds `supersedes`/`superseded_by` for explicit chains
