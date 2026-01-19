---
sprint_id: sprint-dynamic-api-criteria-20260108
session_id: session-20260107-180258-f44cd3cb
sprint_name: Dynamic API Criteria Implementation
initiative: EntityTypeDetectionFix
created_at: 2026-01-08T15:06:21Z
status: pending
goal: "Enable dynamic API criteria for schema-driven resolution (Option B from SPIKE-dynamic-api-criteria)"
complexity: PATCH
active_rite: 10x-dev-pack
estimated_duration: "2-4 hours"
source_spikes:
  - docs/spikes/SPIKE-dynamic-api-criteria.md
schema_version: "1.0"
current_task: none
last_updated: 2026-01-08T15:06:21Z
---

# Sprint: Dynamic API Criteria Implementation

## Sprint Goal

Implement Option B (Hybrid Approach) from SPIKE-dynamic-api-criteria to enable dynamic/flexible query criteria in the resolver REST API while maintaining backwards compatibility and type safety.

## Success Criteria

- [ ] ResolutionCriterion model updated with `extra="allow"`
- [ ] Schema discovery endpoint implemented (`GET /{entity_type}/schema`)
- [ ] Existing validation logic works with dynamic fields
- [ ] All existing tests pass
- [ ] New integration test for dynamic field resolution
- [ ] API documentation updated for new capabilities

## Task Breakdown

### TASK-001: Update ResolutionCriterion Model
- **Status**: pending
- **Agent**: principal-engineer
- **Complexity**: SMALL
- **Depends On**: none
- **Produces**: Updated `src/autom8_asana/api/routes/resolver.py`
- **Description**: Change `model_config = ConfigDict(extra="forbid")` to `extra="allow"` in ResolutionCriterion class

### TASK-002: Add Schema Discovery Endpoint
- **Status**: pending
- **Agent**: principal-engineer
- **Complexity**: SMALL
- **Depends On**: TASK-001
- **Produces**: New endpoint in `src/autom8_asana/api/routes/resolver.py`
- **Description**: Add `GET /{entity_type}/schema` endpoint that returns queryable fields from SchemaRegistry

### TASK-003: Update Tests for Dynamic Criteria
- **Status**: pending
- **Agent**: principal-engineer
- **Complexity**: SMALL
- **Depends On**: [TASK-001, TASK-002]
- **Produces**: Updated test suite
- **Description**: Add integration test for dynamic field resolution and schema discovery endpoint

### TASK-004: QA Validation
- **Status**: pending
- **Agent**: qa-adversary
- **Complexity**: SMALL
- **Depends On**: TASK-003
- **Produces**: QA report
- **Description**: Validate dynamic field resolution, backwards compatibility, error handling, and security considerations

## Dependency Graph

```
TASK-001 (ResolutionCriterion)
    │
    ├────────────────┐
    ▼                ▼
TASK-002        TASK-003
(Schema         (Tests)
Endpoint)           │
    │               │
    └───────────────┘
            │
            ▼
        TASK-004
          (QA)
```

## Implementation Notes

### Phase 1: Enable Dynamic Fields (Non-Breaking)
1. Change `extra="forbid"` → `extra="allow"`
2. Existing requests continue working (phone, vertical, etc.)
3. New fields immediately available (mrr, specialty, etc.)

### Phase 2: Add Schema Discovery
1. Add `GET /v1/resolve/{entity_type}/schema` endpoint
2. Document in API reference
3. Update client SDKs (if any)

### Backend Validation
The `UniversalResolutionStrategy.validate_criterion()` method already validates criterion fields against the schema, so no additional validation logic is needed.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing clients | Low | High | Preserve backwards-compatible field names |
| Field injection attacks | Low | Medium | Backend validates against schema allowlist |
| Incomplete documentation | Medium | Low | Add OpenAPI additionalProperties documentation |

## Out of Scope

- Query operators (gt, lt, contains, etc.) - equality only for this sprint
- Deprecation of legacy field names - future major version
- Client SDK updates - manual for now

## Reference Artifacts

- **Spike Report**: docs/spikes/SPIKE-dynamic-api-criteria.md
- **Related PRD**: docs/requirements/PRD-dynamic-resolver-architecture.md
- **Related TDD**: docs/design/TDD-dynamic-resolver-architecture.md
