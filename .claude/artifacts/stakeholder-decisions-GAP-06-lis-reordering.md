---
artifact_id: stakeholder-decisions-GAP-06-lis-reordering
title: "Stakeholder Decisions: LIS-Based Subtask Reordering"
created_at: "2026-02-07T18:00:00Z"
author: requirements-analyst
status: confirmed
source: docs/requirements/PRD-GAP-06-lis-reordering.md
---

# Stakeholder Decisions — GAP-06: LIS-Based Subtask Reordering

## Open Question Resolutions

| OQ | Decision | Rationale |
|----|----------|-----------|
| OQ-1 (API surface) | **Both**: standalone `compute_reorder_plan()` utility + thin `SaveSession.reorder_subtasks()` wrapper | Testability + ergonomics |
| OQ-2 (Input source) | **Explicit**: caller provides both `current_order` and `desired_order` | Simple, no hidden I/O |
| OQ-3 (Module location) | **`persistence/reorder.py`** | Co-located with SaveSession, single file |
| OQ-4 (Dry-run) | **Free via utility** — `compute_reorder_plan()` IS the dry-run; no separate flag needed | Falls out of the two-layer design |
| OQ-5 (GAP-01 coupling) | **Wire it in** — GAP-01 is already built (likely with naive/missing ordering); integrate LIS into existing flow | Consumer exists, no reason to defer |

## Scope Decisions

| Item | Decision |
|------|----------|
| FR-001 through FR-004 (MUST) | **In scope** |
| FR-005 (dry-run, SHOULD) | **In scope** (free via design) |
| FR-006 (post-exec verification, COULD) | **Dropped** — different concern, adds API calls |
| All listed non-goals/deferrals | **Confirmed** — no scope changes |
| GAP-01 holder ordering wiring | **Added to scope** — since GAP-01 exists |

## Quality Bar

| Dimension | Decision |
|-----------|----------|
| Testing | Unit tests (SC-001 through SC-005) + Hypothesis property-based tests. No benchmark test. |
| Documentation | Code + docstrings only. PRD serves as design record. |
| Logging | structlog with structured events (`reorder_plan_computed`, `move_planned`) |

## Integration Decisions

| Decision | Detail |
|----------|--------|
| Input types | `AsanaResource` objects only (matches existing `reorder_subtask()` pattern) |
| GAP-01 integration | Architect must examine existing holder creation code to identify the wiring point |

## Execution Preferences

| Decision | Detail |
|----------|--------|
| Commits | Atomic commits to main; stakeholder decides on PR |
| Review gates | Direct handoff: architect → principal-engineer. No intermediate TDD review. |
| Workflow | Architect produces TDD, principal-engineer implements with tests |

## Key Constraints for Design Phase

1. The LIS utility must be a **pure function** — no I/O, no session dependencies
2. The SaveSession wrapper must **not modify** the existing `reorder_subtask()` singular method
3. Move references must target elements **NOT also being moved** (stable references)
4. Architect must **inspect GAP-01 code** to understand current holder ordering state before designing the integration
