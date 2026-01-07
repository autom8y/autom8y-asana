---
sprint_id: sprint-cascade-factory-fix-001
name: Cascade Field Resolution - Factory Schema Version Fix
goal: Fix DataFrameCache factory to use per-entity schema version lookup
session_id: session-20260106-175204-b357000f
created_at: 2026-01-07T12:15:00Z
status: active
complexity: MODULE

tasks:
  - id: task-001
    name: Modify DataFrameCache for per-entity schema version lookup
    status: in_progress
    agent: principal-engineer
    depends_on: []
    artifacts: []
    description: |
      - Modify _is_valid() to lookup version from SchemaRegistry
      - Modify put_async() to stamp entries with registry version
      - Remove hardcoded schema_version from factory.py

  - id: task-002
    name: Add factory unit test for schema version regression
    status: pending
    agent: principal-engineer
    depends_on: [task-001]
    artifacts: []
    description: |
      - Test _is_valid() rejects entries with wrong version
      - Test put_async() stamps entries with registry version
      - Test edge cases for unknown entity types

  - id: task-003
    name: Run cascade field integration tests across all entities
    status: pending
    agent: qa-adversary
    depends_on: [task-002]
    artifacts: []
    description: |
      - Run tests/integration/test_cascading_field_resolution.py
      - Run tests/integration/test_unit_cascade_resolution.py
      - Verify cascade works for Unit, Contact, Offer, Business

  - id: task-004
    name: Deploy and verify with demo script
    status: pending
    agent: principal-engineer
    depends_on: [task-003]
    artifacts: []
    description: |
      - Push changes to deploy
      - Wait for ECS deployment
      - Run demo at /Users/tomtenuta/Code/autom8-s2s-demo/examples/05_gid_lookup.py
      - Expected: 2/3 matches

burndown:
  total: 4
  completed: 0
  in_progress: 1
  blocked: 0
---

# Sprint: Cascade Field Resolution - Factory Schema Version Fix

## Root Cause

`DataFrameCache` factory at `src/autom8_asana/cache/dataframe/factory.py:120` hardcodes `schema_version="1.0.0"` instead of reading from actual schema definitions.

**Impact**: UNIT_SCHEMA was bumped to "1.1.0" but cache still uses "1.0.0", so stale DataFrames are returned.

## User Decisions

1. **Version Source**: Per-entity lookup from SchemaRegistry
2. **S3 Cleanup**: Let version check handle it (stress test the system)
3. **Verification**: Full integration tests across ALL entity types
4. **Prevention**: Factory unit test for regression protection

## Implementation Approach

Per orchestrator directive:
- `_is_valid()` looks up version from `SchemaRegistry.get_schema(entity_type).version`
- `put_async()` stamps entries with schema version from registry
- Factory stops passing hardcoded `schema_version="1.0.0"`
- Entity type mapping: "unit" -> "Unit" for registry lookup

## Key Files

| File | Change |
|------|--------|
| `src/autom8_asana/cache/dataframe_cache.py` | Modify `_is_valid()` and `put_async()` |
| `src/autom8_asana/cache/dataframe/factory.py` | Remove hardcoded `schema_version` |
| `tests/unit/cache/test_dataframe_cache_schema_version.py` | New regression test |

## Quality Gates

| Gate | Criteria |
|------|----------|
| Implementation | `_is_valid()` uses SchemaRegistry lookup |
| Unit Tests | New test + all existing cache tests pass |
| Integration | `test_cascading_field_resolution.py` passes |
| Demo | 2/3 matches in 05_gid_lookup.py |
