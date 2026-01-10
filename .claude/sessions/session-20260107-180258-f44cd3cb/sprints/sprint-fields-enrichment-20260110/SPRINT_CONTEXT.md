---
schema_version: "1.0"
sprint_id: sprint-fields-enrichment-20260110
session_id: session-20260107-180258-f44cd3cb
status: ACTIVE
created_at: "2026-01-10T00:00:00Z"
name: Fields Enrichment
goal: Wire up fields parameter to return additional entity data in resolution responses
complexity: MODULE
entry_point: architect
current_phase: design
---

# Sprint: Fields Enrichment

## Goal

Implement the `fields` parameter in resolution requests to return additional entity data (name, vertical, etc.) alongside GIDs.

## Context

- **Spike**: `docs/spikes/SPIKE-fields-enrichment-gap-analysis.md` (COMPLETE)
- **Work Type**: Enhancement (wiring existing infrastructure)
- **Entry Point**: Architect (skip PRD - spike serves as requirements)
- **Risk Level**: Low (additive changes only, backwards compatible)

## Task Breakdown

| ID | Task | Agent | Status | Depends On | Artifact |
|----|------|-------|--------|------------|----------|
| TASK-001 | Create TDD for fields enrichment | architect | pending | - | `docs/design/TDD-fields-enrichment.md` |
| TASK-002 | Add `_enrich_from_dataframe()` method | principal-engineer | pending | TASK-001 | Code in `universal_strategy.py` |
| TASK-003 | Update `resolve()` signature and wiring | principal-engineer | pending | TASK-002 | Code in `universal_strategy.py` |
| TASK-004 | Update API response model and route | principal-engineer | pending | TASK-003 | Code in `routes/resolver.py` |
| TASK-005 | QA validation with tests | qa-adversary | pending | TASK-004 | Test results |

## Gaps Being Addressed (from Spike)

| Gap | Solution |
|-----|----------|
| DynamicIndex only stores GIDs | Post-lookup DataFrame enrichment |
| Strategy ignores `fields` param | Add `requested_fields` parameter |
| No enrichment method | Implement `_enrich_from_dataframe()` |
| Response model lacks `data` field | Add `data: list[dict] \| None` |
| API discards match_context | Map to response `data` field |

## Expected Response Format

```json
{
  "results": [{
    "gid": "1234567890123456",
    "gids": ["1234567890123456"],
    "match_count": 1,
    "data": [{
      "gid": "1234567890123456",
      "name": "Total Vitality Group",
      "vertical": "chiropractic"
    }]
  }]
}
```

## Success Criteria

- [ ] `fields` parameter returns requested field data
- [ ] Existing GID-only requests unchanged (zero cost)
- [ ] All existing tests continue to pass
- [ ] New tests for field enrichment
- [ ] Demo script shows field data

## Blockers

None.

## Audit Log

| Timestamp | Event | Details |
|-----------|-------|---------|
| 2026-01-10T00:00:00Z | Sprint created | Entry point: architect, complexity: MODULE |
