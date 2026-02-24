# WS-ADVISORY: P2/P3 Advisory Items

**Objective**: Address high-value P2 and P3 advisory items from the SLOP-CHOP-TESTS-P2 gate verdict. Non-blocking work, executed if time permits after all P1 items are resolved.

---

## Source Findings

### P2 Items (significant improvement)

| RS-ID | Finding | File | Effort |
|-------|---------|------|--------|
| RS-003 | Broad except in E2E cleanup | test_e2e_offer_write_proof.py | small |
| RS-004 | Copy-paste bloat in entity resolver E2E | test_entity_resolver_e2e.py | small |
| RS-006 | Redundant import + asyncio.run() in GID tests | test_gid_validation_edge_cases.py | small |
| RS-009 | Dead permanently-skipped test | test_lifecycle_smoke.py | trivial |
| RS-014 | Unused mock_client assignments | test_workspace_switching.py | trivial (likely done by WS-WSISO) |
| RS-018 | MIGRATION_REQUIRED pass-only stubs | test_unified_cache_integration.py | medium |
| RS-026 | Or-hedge in snapshot assertion | test_concurrency.py | trivial |
| RS-027 | Missing modification-count assertion | test_concurrency.py | trivial |
| RS-031 | Misnamed "concurrent" test runs sequentially | test_concurrency.py | trivial |
| RS-037 | Dead completion adapter test | test_lifecycle_smoke.py | trivial (overlaps RS-009) |
| RS-038 | Stale MIGRATION_REQUIRED skip | test_unified_cache_integration.py | medium |
| RS-039 | Stale LEGACY_CASCADE_PATH skip | test_unified_cache_integration.py | small |
| RS-045 | Double-skipped empty stub | test_unified_cache_integration.py | trivial (after RS-039) |

### P3 Items (advisory, temporal debt)

| RS-ID | Finding | File | Effort |
|-------|---------|------|--------|
| RS-033 | Unused stale_task + task_with_due_date fixtures | polling/conftest.py | trivial |
| RS-034 | Unused helper triad in validation conftest | validation/conftest.py | trivial |
| RS-036 | Stale scaffold comments in persistence conftest | persistence/conftest.py | trivial (likely done by WS-LIVEAPI) |
| RS-040 | Spike script with hardcoded production GID | spike_write_diagnosis.py | trivial |
| RS-041 | Initiative tag in fixture docstring | test_cascading_field_resolution.py | trivial |
| RS-042 | IMP-23 ticket prefix in docstring | test_hydration_cache_integration.py | trivial |
| RS-043 | Story 3.2 / IMP-20 tags in benchmark | test_insights_benchmark.py | trivial |
| RS-044 | Dead env-var shim fixtures | persistence/conftest.py | trivial (likely done by WS-LIVEAPI) |
| RS-046 | Single-consumer conftest | integration/conftest.py | small |
| RS-047 | TDD-CONV-AUDIT-001 ticket prefix | test_trigger_evaluator_integration.py | trivial |
| RS-048 | Phase 3 qualifier in Phase 4+ module | test_unified_cache_integration.py | trivial |

---

## Grouping Strategy (by file, minimize context switches)

### Batch 1: test_unified_cache_integration.py cluster
RS-018, RS-038, RS-039, RS-045, RS-048 -- all in the same file. Address RS-039 first (un-skip), then RS-045 (delete double-skipped), then RS-038 (implement or delete stubs), then RS-018 + RS-048.

### Batch 2: test_concurrency.py cluster
RS-026, RS-027, RS-031 -- all in the same file. Trivial fixes, apply in sequence.

### Batch 3: Scattered trivial items
RS-009/RS-037 (test_lifecycle_smoke.py), RS-033 (polling conftest), RS-034 (validation conftest), RS-040 (spike script), RS-041/RS-042/RS-043/RS-047 (ephemeral comments), RS-046 (integration conftest).

### Batch 4: Larger refactoring
RS-003 (narrow except), RS-004 (extract fixture), RS-006 (parametrize GID tests).

---

## Effort Estimate

- **Total**: ~4-6 hours
- **Batches 1-3**: ~2-3 hours (mostly trivial deletions, un-skips, comment edits)
- **Batch 4**: ~2-3 hours (fixture extraction, parametrization, exception narrowing)

---

## Dependencies

- WS-WSISO should complete first (RS-014 may be addressed there)
- WS-LIVEAPI should complete first (RS-036, RS-044 may be addressed there)
- RS-045 depends on RS-039 (apply RS-039 first)

---

## Rite / Complexity

- **Rite**: hygiene (recommended, confirm at dispatch)
- **Complexity**: MODULE
