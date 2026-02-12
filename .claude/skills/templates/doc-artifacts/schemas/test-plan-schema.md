---
schema_name: test-plan
schema_version: "1.0"
file_pattern: "docs/testing/TEST-*.md"
artifact_type: test-plan
---

# Test Plan Schema

> Canonical schema for Test Plans at `docs/testing/TEST-{slug}.md`

## YAML Frontmatter

```yaml
---
# Required fields
artifact_id: string        # Pattern: TEST-{slug} (e.g., "TEST-user-auth")
title: string              # Human-readable title
created_at: string         # ISO 8601 timestamp
author: string             # Agent or user who created (e.g., "qa-adversary")
prd_ref: string            # Reference to source PRD
status: enum               # draft | ready | executing | passed | failed

# Coverage tracking
coverage_matrix:           # Maps success criteria to test cases
  - criterion_id: string   # SC-001 from PRD
    test_case_ids: array   # [TC-001, TC-002]
    coverage_type: enum    # full | partial | none

# Test cases (at least one required)
test_cases:
  - id: string             # TC-001, TC-002, etc.
    name: string           # Test case name
    type: enum             # unit | integration | e2e | manual | smoke
    priority: enum         # critical | high | medium | low
    preconditions: array   # What must be true before test
    steps: array           # Test steps
    expected: string       # Expected outcome
    status: enum           # pending | passed | failed | skipped

# Optional fields
tdd_ref: string            # Reference to TDD if design phase ran
environment: string        # Test environment requirements
estimated_duration: string # Time estimate for full run

# Schema versioning
schema_version: "1.0"      # Must be "1.0" for this version
---
```

## Required Fields

| Field | Type | Description | Set By |
|-------|------|-------------|--------|
| `artifact_id` | string | Unique identifier, pattern: `TEST-{slug}` | qa-adversary |
| `title` | string | Human-readable title | qa-adversary |
| `created_at` | string | ISO 8601 creation timestamp | qa-adversary |
| `author` | string | Creating agent or user | qa-adversary |
| `prd_ref` | string | Reference to source PRD | qa-adversary |
| `status` | enum | Current test plan status | qa-adversary |
| `coverage_matrix` | array | Criterion to test case mapping | qa-adversary |
| `test_cases` | array | Test case definitions (min 1) | qa-adversary |
| `schema_version` | string | Schema version for compatibility | qa-adversary |

## Optional Fields

| Field | Type | Description | Set By |
|-------|------|-------------|--------|
| `tdd_ref` | string | Reference to TDD if applicable | qa-adversary |
| `environment` | string | Test environment requirements | qa-adversary |
| `estimated_duration` | string | Time for full test run | qa-adversary |

## Coverage Matrix Object Schema

```yaml
coverage_matrix:
  - criterion_id: string   # "SC-001" - matches PRD success criterion
    test_case_ids: array   # ["TC-001", "TC-002"]
    coverage_type: enum    # full | partial | none
    notes: string          # (optional) Coverage notes
```

## Test Case Object Schema

```yaml
test_cases:
  - id: string             # "TC-001" format
    name: string           # Descriptive test name
    type: enum             # unit | integration | e2e | manual | smoke
    priority: enum         # critical | high | medium | low
    preconditions:         # Setup requirements
      - string
    steps:                 # Test execution steps
      - action: string     # What to do
        data: string       # (optional) Test data
    expected: string       # Expected outcome
    status: enum           # pending | passed | failed | skipped
    actual: string         # (optional) Actual result if executed
    failure_reason: string # (optional) Why it failed
```

## Valid Status Transitions

```
draft --finalize--> ready
ready --start--> executing
executing --complete--> passed | failed
failed --fix--> executing
passed | failed --archive--> (archived)
```

## Validation Rules

### Structure Validation
1. File MUST start with `---` on line 1
2. File MUST have closing `---` within first 100 lines
3. Content between delimiters MUST be valid YAML

### Field Validation
1. `artifact_id` MUST match pattern `^TEST-[a-z0-9-]+$`
2. `prd_ref` MUST match pattern `^PRD-[a-z0-9-]+$`
3. `created_at` MUST be valid ISO 8601 timestamp
4. `status` MUST be one of: draft, ready, executing, passed, failed
5. `coverage_matrix` MUST be array with at least one item
6. `test_cases` MUST be array with at least one item
7. `schema_version` MUST be "1.0"

### Coverage Validation
1. Each coverage entry MUST have `criterion_id`, `test_case_ids`, `coverage_type`
2. `criterion_id` MUST match pattern `^SC-[0-9]+$`
3. `coverage_type` MUST be one of: full, partial, none
4. All `test_case_ids` MUST reference existing test cases

### Test Case Validation
1. Each test case MUST have `id`, `name`, `type`, `priority`, `steps`, `expected`, `status`
2. `id` MUST match pattern `^TC-[0-9]+$`
3. `type` MUST be one of: unit, integration, e2e, manual, smoke
4. `priority` MUST be one of: critical, high, medium, low
5. `status` MUST be one of: pending, passed, failed, skipped

## Example: Valid Test Plan

```yaml
---
artifact_id: TEST-user-authentication
title: "User Authentication Test Plan"
created_at: "2025-12-29T12:00:00Z"
author: qa-adversary
prd_ref: PRD-user-authentication
tdd_ref: TDD-user-authentication
status: ready
coverage_matrix:
  - criterion_id: SC-001
    test_case_ids: [TC-001, TC-002]
    coverage_type: full
  - criterion_id: SC-002
    test_case_ids: [TC-003, TC-004, TC-005]
    coverage_type: full
  - criterion_id: SC-003
    test_case_ids: [TC-006]
    coverage_type: full
test_cases:
  - id: TC-001
    name: "Register with valid email and password"
    type: integration
    priority: critical
    preconditions:
      - "Database is empty or user does not exist"
      - "API server is running"
    steps:
      - action: "POST /api/v1/auth/register"
        data: '{"email": "test@example.com", "password": "SecurePass123!"}'
    expected: "201 Created with user ID in response"
    status: pending
  - id: TC-002
    name: "Reject registration with invalid email"
    type: integration
    priority: high
    preconditions:
      - "API server is running"
    steps:
      - action: "POST /api/v1/auth/register"
        data: '{"email": "invalid-email", "password": "SecurePass123!"}'
    expected: "400 Bad Request with validation error"
    status: pending
  - id: TC-003
    name: "Login with valid credentials"
    type: integration
    priority: critical
    preconditions:
      - "User exists in database"
      - "API server is running"
    steps:
      - action: "POST /api/v1/auth/login"
        data: '{"email": "test@example.com", "password": "SecurePass123!"}'
    expected: "200 OK with JWT token in response"
    status: pending
  - id: TC-004
    name: "Reject login with wrong password"
    type: integration
    priority: critical
    preconditions:
      - "User exists in database"
    steps:
      - action: "POST /api/v1/auth/login"
        data: '{"email": "test@example.com", "password": "WrongPassword"}'
    expected: "401 Unauthorized"
    status: pending
  - id: TC-005
    name: "Reject login with non-existent user"
    type: integration
    priority: high
    preconditions:
      - "User does not exist in database"
    steps:
      - action: "POST /api/v1/auth/login"
        data: '{"email": "nobody@example.com", "password": "AnyPassword"}'
    expected: "401 Unauthorized (same as wrong password)"
    status: pending
  - id: TC-006
    name: "Rate limit after 5 failed attempts"
    type: integration
    priority: high
    preconditions:
      - "User exists in database"
      - "No recent failed attempts"
    steps:
      - action: "POST /api/v1/auth/login with wrong password 5 times"
        data: '{"email": "test@example.com", "password": "WrongPassword"}'
      - action: "POST /api/v1/auth/login 6th time"
        data: '{"email": "test@example.com", "password": "WrongPassword"}'
    expected: "429 Too Many Requests with Retry-After header"
    status: pending
environment: "Integration test environment with test database"
estimated_duration: "15 minutes"
schema_version: "1.0"
---

## Test Plan Overview

This test plan validates all success criteria from PRD-user-authentication.

## Test Environment

- Integration test environment
- Isolated test database (PostgreSQL)
- Mocked external services

## Coverage Summary

| Criterion | Description | Coverage | Test Cases |
|-----------|-------------|----------|------------|
| SC-001 | User registration | Full | TC-001, TC-002 |
| SC-002 | User login | Full | TC-003, TC-004, TC-005 |
| SC-003 | Rate limiting | Full | TC-006 |

## Execution Order

1. TC-001 (registration - creates test user)
2. TC-002 (registration validation)
3. TC-003, TC-004, TC-005 (login tests)
4. TC-006 (rate limiting)

## Smoke Test Subset

For quick validation, run: TC-001, TC-003
```

## Validation Function

```bash
# In artifact-validator.sh
# Usage: validate_test_plan "/path/to/TEST-example.md"
# Returns: 0=valid, 1=not found, 2=no opener, 3=no closer, 4=missing field, 5=invalid field

validate_test_plan() {
    local file="$1"
    local required_fields=("artifact_id" "title" "created_at" "author" "prd_ref" "status" "coverage_matrix" "test_cases" "schema_version")

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
    if [[ ! "$artifact_id" =~ ^TEST-[a-z0-9-]+$ ]]; then
        echo "Invalid artifact_id: Must match pattern TEST-{slug}" >&2
        return 5
    fi

    # Validate prd_ref pattern
    local prd_ref
    prd_ref=$(echo "$frontmatter" | grep "^prd_ref:" | sed 's/prd_ref: *//' | tr -d '"')
    if [[ ! "$prd_ref" =~ ^PRD-[a-z0-9-]+$ ]]; then
        echo "Invalid prd_ref: Must match pattern PRD-{slug}" >&2
        return 5
    fi

    # Validate status enum
    local status
    status=$(echo "$frontmatter" | grep "^status:" | sed 's/status: *//' | tr -d '"')
    if [[ ! "$status" =~ ^(draft|ready|executing|passed|failed)$ ]]; then
        echo "Invalid status: Must be draft, ready, executing, passed, or failed" >&2
        return 5
    fi

    return 0
}
```

## Handoff Criteria

When Test Plan phase completes, orchestrator verifies:

- [ ] `artifact_id` matches file name pattern
- [ ] `prd_ref` references existing approved PRD
- [ ] All PRD success criteria have coverage entries
- [ ] No `coverage_type: none` for `must-have` criteria
- [ ] At least one test case per covered criterion
- [ ] All critical priority test cases defined

## Relationship to Other Artifacts

```
TEST-{slug}.md
    |
    +-- References PRD (test_plan.prd_ref)
    |
    +-- References TDD (test_plan.tdd_ref) if applicable
    |
    +-- coverage_matrix.criterion_id -> PRD.success_criteria.id
    |
    +-- Execution produces pass/fail status
```

## Test Result Tracking

After test execution, update:
1. `status` to passed/failed
2. Each `test_case.status` to passed/failed/skipped
3. Failed cases get `actual` and `failure_reason` populated
