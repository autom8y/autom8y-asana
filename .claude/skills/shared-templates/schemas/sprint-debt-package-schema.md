# Sprint Debt Package Schema

**Version:** 1.0
**Type:** sprint-debt-package
**File Pattern:** `docs/sprints/SDP-{slug}.md`

## Purpose

Sprint-ready work units produced by Sprint Planner agent.

## YAML Frontmatter Schema

```yaml
---
# Required fields
artifact_id: string        # Pattern: SDP-{slug}
title: string              # Human-readable title (e.g., "Sprint 24 Debt Package")
type: string               # Must be "sprint-debt-package"
created_at: string         # ISO 8601 timestamp
author: string             # Creating agent (e.g., "sprint-planner")
status: enum               # draft | ready | in-progress | complete
schema_version: "1.0"      # Schema version

# Source reference
source_matrix: string      # Reference to input Risk Matrix (e.g., "RM-api-cleanup")

# Capacity planning
capacity:
  total_hours: integer     # Available capacity in hours
  buffer_percent: integer  # Buffer percentage (default 20%)
  allocated_hours: integer # Hours allocated to packages

# Package summary
package_count: integer     # Number of work packages
total_effort_hours: integer # Sum of package estimates

# Sprint info
sprint:
  name: string             # Sprint name/number
  start_date: string       # ISO 8601 date
  end_date: string         # ISO 8601 date

# Optional fields
session_id: string         # Associated session
initiative: string         # Parent initiative
target_rite: string        # Rite receiving handoff (e.g., "hygiene")
---
```

## Required Sections

| Section | Purpose | Authored By |
|---------|---------|-------------|
| Executive Summary | Sprint goals and key packages | sprint-planner |
| Capacity Model | Available vs allocated hours | sprint-planner |
| Work Packages | Detailed package specifications | sprint-planner |
| Dependency Map | Package dependencies | sprint-planner |
| Acceptance Criteria Summary | Roll-up of all criteria | sprint-planner |

## Optional Sections

| Section | Purpose | When Included |
|---------|---------|---------------|
| Deferred Items | Items not included with rationale | When items deferred |
| HANDOFF | Cross-rite handoff artifact | When target_rite specified |
| Capacity Scenarios | What-if planning alternatives | For complex planning |

## Work Package Object Schema

```yaml
packages:
  - id: string             # "PKG-001", "PKG-002", etc.
    title: string          # Human-readable title
    source_items: array    # Risk matrix item IDs included
    size: enum             # XS | S | M | L | XL
    effort_hours: integer  # Estimated hours
    confidence: enum       # high | medium | low
    priority: enum         # critical | high | medium | low
    sprint: string         # Target sprint (this, next, backlog)
    dependencies: array    # Other package IDs this depends on
    acceptance_criteria:   # Specific, testable criteria
      - string
    owner: string          # Assigned team/person (optional)
    notes: string          # Additional context (optional)
```

## Size Guidelines

| Size | Hours | Points | Scope |
|------|-------|--------|-------|
| XS | 1-2 | 1 | Config change, small fix |
| S | 2-4 | 2 | Single file, straightforward |
| M | 4-8 | 3-5 | Multiple files, contained |
| L | 8-16 | 5-8 | Cross-module, needs design |
| XL | 16-32 | 8-13 | Significant refactor |

## Confidence Adjustments

| Confidence | Buffer Multiplier | Description |
|------------|-------------------|-------------|
| high | 1.0x | Similar work done before, clear scope |
| medium | 1.25-1.5x | Some unknowns |
| low | 1.5-2.0x | Significant unknowns, may need spike |

## Validation Rules

1. `artifact_id` MUST match pattern `^SDP-[a-z0-9-]+$`
2. `type` MUST be exactly "sprint-debt-package"
3. `source_matrix` MUST reference existing Risk Matrix
4. `capacity.allocated_hours` MUST NOT exceed `capacity.total_hours`
5. `total_effort_hours` MUST equal sum of package effort_hours
6. Each package MUST have at least one acceptance criterion
7. `size` MUST be one of: XS, S, M, L, XL
8. Packages larger than XL MUST be split or flagged for spike
9. `status` MUST be one of: draft, ready, in-progress, complete
10. `sprint.start_date` MUST be before `sprint.end_date`

## Package Lifecycle

| Status | Description | Next States |
|--------|-------------|-------------|
| draft | Initial planning, not finalized | ready, archived |
| ready | Approved and ready for sprint | in-progress |
| in-progress | Work underway | complete, ready (if blocked) |
| complete | All acceptance criteria met | N/A (terminal) |

## Version History

| Version | Changes | Migration Required |
|---------|---------|-------------------|
| 1.0 | Initial schema | N/A |
