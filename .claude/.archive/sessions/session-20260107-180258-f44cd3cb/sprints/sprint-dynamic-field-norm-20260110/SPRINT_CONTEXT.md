---
schema_version: "1.0"
sprint_id: sprint-dynamic-field-norm-20260110
session_id: session-20260107-180258-f44cd3cb
status: ACTIVE
created_at: "2026-01-10T00:00:00Z"
name: Dynamic Field Normalization
goal: Replace LEGACY_FIELD_MAPPING with hierarchical entity alias algorithm
complexity: MODULE
entry_point: architect
current_phase: design
---

# Sprint: Dynamic Field Normalization

## Goal

Replace static `LEGACY_FIELD_MAPPING` dictionary with a dynamic, schema-driven field normalization algorithm using hierarchical entity aliases.

## Context

- **Spike**: `docs/spikes/SPIKE-dynamic-field-normalization.md` (COMPLETE)
- **Work Type**: Technical Refactoring
- **Entry Point**: Architect (skip PRD - spike serves as requirements)
- **Target File**: `src/autom8_asana/services/resolver.py`

## Task Breakdown

| ID | Task | Agent | Status | Depends On | Artifact |
|----|------|-------|--------|------------|----------|
| TASK-001 | Create TDD for dynamic field normalization | architect | pending | - | `docs/design/TDD-dynamic-field-normalization.md` |
| TASK-002 | Implement ENTITY_ALIASES constant | principal-engineer | pending | TASK-001 | Code in `resolver.py` |
| TASK-003 | Implement _normalize_field() function | principal-engineer | pending | TASK-001 | Code in `resolver.py` |
| TASK-004 | Update _apply_legacy_mapping() integration | principal-engineer | pending | TASK-002, TASK-003 | Code in `resolver.py` |
| TASK-005 | Remove LEGACY_FIELD_MAPPING from exports | principal-engineer | pending | TASK-004 | Code in `resolver.py` |
| TASK-006 | QA validation with tests and demo | qa-adversary | pending | TASK-005 | Test results |

## Algorithm Summary (from Spike)

```python
ENTITY_ALIASES = {
    "unit": ["business_unit"],      # unit IS-A business_unit
    "offer": ["business_offer"],    # offer IS-A business_offer
    "business": ["office"],         # business USES office_ prefix
    "contact": [],                  # contact uses its own prefix
}
```

Resolution Order:
1. Exact match: `field_name in available_fields`
2. Prefix expansion: `{entity_type}_{field_name}`
3. Prefix removal: strip `{entity_type}_` from field_name
4. Alias expansion: `{alias}_{field_name}` for each alias
5. Alias decomposition: strip suffix, recurse to parent

## Success Criteria

- [ ] All existing tests pass
- [ ] Demo script (`scripts/demo_dynamic_api.sh`) produces same results
- [ ] No static per-field mappings required
- [ ] Recursion terminates correctly (no infinite loops)
- [ ] Edge cases handled (unknown entity types, missing schemas)

## Blockers

None.

## Audit Log

| Timestamp | Event | Details |
|-----------|-------|---------|
| 2026-01-10T00:00:00Z | Sprint created | Entry point: architect, complexity: MODULE |
