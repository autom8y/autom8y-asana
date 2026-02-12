# HANDOFF Artifact Schema v1.0

> Machine-readable frontmatter schema for cross-rite work transfer

## Overview

The HANDOFF artifact formalizes work transfer between rites with validated schema, type-specific requirements, and session integration.

**File Pattern**: `HANDOFF-{source}-to-{target}-{YYYY-MM-DD}[-{seq}].md`

**Schema Version**: 1.0

---

## Frontmatter Schema

```yaml
---
# ============================================================================
# HANDOFF Artifact Schema v1.0
# ============================================================================
# Machine-readable frontmatter for cross-rite work transfer
# All HANDOFF artifacts MUST conform to this schema

# Required: Core identification
artifact_id: string           # Pattern: HANDOFF-{source}-to-{target}-{YYYY-MM-DD}[-{seq}]
schema_version: "1.0"         # Must be "1.0" for this version

# Required: Rite routing
source_rite: string           # Rite producing the handoff (e.g., "10x-dev")
target_rite: string           # Rite receiving the handoff (e.g., "security")

# Required: Handoff classification
handoff_type: enum            # execution | validation | assessment | implementation | strategic_input | strategic_evaluation
priority: enum                # critical | high | medium | low
blocking: boolean             # If true, source rite cannot proceed until response

# Required: Context
initiative: string            # Initiative or feature name
created_at: string            # ISO 8601 timestamp
status: enum                  # pending | in_progress | completed | rejected

# Required: Work items (at least one)
items: array                  # See Item Object Schema below

# Optional: Source references
source_artifacts: array       # Paths to source artifacts
session_id: string            # Source session ID if within session
sprint_id: string             # Source sprint ID if within sprint

# Optional: Response tracking
response_due: string          # ISO 8601 deadline (derived from priority + SLA)
response_artifact: string     # Path to response artifact when completed

# Optional: Rejection handling
rejection_reason: string      # Why handoff was rejected (if status: rejected)
resubmission_of: string       # artifact_id of original if this is a resubmission
---
```

---

## Item Object Schema

Each item in the `items` array represents a discrete unit of work to hand off.

```yaml
items:
  - id: string                # Unique within handoff (e.g., "SEC-001", "PKG-001")
    summary: string           # 1-2 sentence description (required)
    priority: enum            # critical | high | medium | low (required)

    # Type-specific required fields (see Type-Specific Requirements)
    # At least one type-specific field must be present based on handoff_type

    acceptance_criteria: array     # Required for type: execution
    validation_scope: array        # Required for type: validation
    assessment_questions: array    # Required for type: assessment
    design_references: array       # Required for type: implementation
    data_sources: array            # Required for type: strategic_input
    confidence: enum               # Required for type: strategic_input (high | medium | low)
    evaluation_criteria: array     # Required for type: strategic_evaluation

    # Optional fields
    notes: string             # Additional context for target rite
    dependencies: array       # IDs of other items this depends on
    estimated_effort: string  # Time estimate if known
```

---

## Type-Specific Required Fields

| Handoff Type | Required Per Item | Flow Pattern |
|--------------|-------------------|--------------|
| `execution` | `acceptance_criteria` (array, min 1) | Planning -> Execution |
| `validation` | `validation_scope` (array, min 1) | Dev -> Ops |
| `assessment` | `assessment_questions` (array, min 1) | Dev -> Specialist |
| `implementation` | `design_references` (array, min 1) | Research -> Dev |
| `strategic_input` | `data_sources` (array, min 1), `confidence` | Research -> Strategy |
| `strategic_evaluation` | `evaluation_criteria` (array, min 1) | R&D -> Strategy |

---

## Valid Status Transitions

```
pending --accept--> in_progress
pending --reject--> rejected
in_progress --complete--> completed
rejected --resubmit--> pending (new artifact, references original)
```

---

## Validation Rules

### Structure Validation

1. File MUST start with `---` on line 1
2. File MUST have closing `---` within first 75 lines
3. Content between delimiters MUST be valid YAML
4. File name MUST match pattern `HANDOFF-{source}-to-{target}-{date}[-seq].md`

### Field Validation

| Field | Rule | Error Code |
|-------|------|------------|
| `artifact_id` | Match pattern `^HANDOFF-[a-z0-9-]+-to-[a-z0-9-]+-[0-9]{4}-[0-9]{2}-[0-9]{2}(-[0-9]+)?$` | HANDOFF-001 |
| `source_rite` | Non-empty, match known rite pattern | HANDOFF-002 |
| `target_rite` | Non-empty, different from source_rite | HANDOFF-003 |
| `handoff_type` | One of: execution, validation, assessment, implementation, strategic_input, strategic_evaluation | HANDOFF-004 |
| `priority` | One of: critical, high, medium, low | HANDOFF-005 |
| `blocking` | Boolean | HANDOFF-006 |
| `initiative` | Non-empty string | HANDOFF-007 |
| `created_at` | Valid ISO 8601 timestamp | HANDOFF-008 |
| `status` | One of: pending, in_progress, completed, rejected | HANDOFF-009 |
| `items` | Array with at least one item | HANDOFF-010 |
| `schema_version` | Must be "1.0" | HANDOFF-011 |

### Item Validation

| Rule | Error Code |
|------|------------|
| Each item MUST have `id`, `summary`, `priority` | HANDOFF-020 |
| Item `id` MUST be unique within handoff | HANDOFF-021 |
| Item `priority` MUST be valid enum | HANDOFF-022 |
| Type-specific field MUST be present based on `handoff_type` | HANDOFF-023 |
| Type-specific field MUST be non-empty array | HANDOFF-024 |
| For `strategic_input`, `confidence` MUST be one of: high, medium, low | HANDOFF-025 |

### Cross-Field Validation

| Rule | Error Code |
|------|------------|
| `source_rite` and `target_rite` MUST be different | HANDOFF-030 |
| If `status: rejected`, `rejection_reason` MUST be present | HANDOFF-031 |
| If `resubmission_of` present, referenced artifact MUST exist | HANDOFF-032 |
| If `blocking: true`, `priority` SHOULD be `critical` or `high` | HANDOFF-033 (warning) |

---

## Trigger Conditions

### Required Cross-Rite Handoff

A cross-rite HANDOFF artifact is **required** when:

| Condition | Target Rite | Handoff Type |
|-----------|-------------|--------------|
| Complexity >= SERVICE with security considerations | security | assessment |
| Feature involves production deployment | sre | validation |
| Debt remediation work ready for execution | hygiene | execution |
| R&D prototype ready for strategic evaluation | strategy | strategic_evaluation |
| User research synthesis complete | strategy | strategic_input |
| Strategic go-decision for production build | 10x-dev | implementation |

### Optional Cross-Rite Handoff

A cross-rite HANDOFF artifact is **optional** when:

| Condition | Target Rite | Handoff Type |
|-----------|-------------|--------------|
| Feature complete, documentation update desired | docs | assessment |
| Code review reveals hygiene concerns | hygiene | assessment |
| Performance concerns identified | sre | assessment |
| Minor security considerations (complexity < SERVICE) | security | assessment |

### No Handoff Required

Cross-rite handoff is **not required** when:

- Work remains within single rite's domain
- Phase transition within same rite (use `/handoff` within-rite)
- Quick consultation (use `/consult` or direct user communication)
- Information sharing without action items

---

## Storage Locations

| Context | Location | Pattern |
|---------|----------|---------|
| Active session | `.claude/sessions/{session-id}/` | `HANDOFF-{source}-to-{target}-{date}.md` |
| Initiative docs | `docs/handoffs/` | `HANDOFF-{source}-to-{target}-{date}.md` |
| Sprint context | `.claude/sprints/{sprint-id}/` | `HANDOFF-{source}-to-{target}-{date}.md` |

### Naming Convention

```
HANDOFF-{source}-to-{target}-{YYYY-MM-DD}[-{seq}].md

Examples:
- HANDOFF-10x-dev-to-security-2026-01-03.md
- HANDOFF-debt-triage-to-hygiene-2026-01-03-2.md  (second handoff same day)
```

### Response Artifact Naming

Response artifacts follow similar pattern:
```
HANDOFF-RESPONSE-{target}-to-{source}-{YYYY-MM-DD}.md
```

---

## Session Integration

### SESSION_CONTEXT Schema Extension

Add optional `pending_handoffs` field to SESSION_CONTEXT:

```yaml
# In SESSION_CONTEXT.md frontmatter
pending_handoffs:
  - artifact_id: string      # Reference to HANDOFF artifact
    target_rite: string      # Rite waiting on
    blocking: boolean        # Is this blocking progress
    created_at: string       # When handoff was created
    status: enum             # pending | in_progress
```

### Handoff Lifecycle in Session

```
1. Source rite creates HANDOFF artifact
2. Source rite updates SESSION_CONTEXT.pending_handoffs (if session active)
3. User routes HANDOFF to target rite
4. Target rite accepts, rejects, or requests clarification
5. If accepted: Target rite produces response artifact
6. If rejected: Source rite updates and resubmits (new artifact)
7. On completion: Source rite removes from pending_handoffs
```

---

## Examples

See the [examples/](examples/) directory for complete HANDOFF artifacts:

- [assessment.md](examples/assessment.md) - Security assessment handoff
- [execution.md](examples/execution.md) - Debt remediation execution handoff
- [rejected.md](examples/rejected.md) - Rejected handoff with resubmission guidance
