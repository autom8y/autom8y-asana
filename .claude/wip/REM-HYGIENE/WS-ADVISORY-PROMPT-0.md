# WS-ADVISORY Session Prompt

## Rite & Workflow
- Rite: hygiene
- Workflow: `/task`
- Complexity: MODULE

## Objective

Address P2 and P3 advisory items from the SLOP-CHOP-TESTS-P2 gate verdict, grouped by file to minimize context switches. Non-blocking work, executed after all P1 items are resolved.

## Context

- Seed doc: `.claude/wip/REM-HYGIENE/WS-ADVISORY.md`
- Remedy plan: `.claude/wip/SLOP-CHOP-TESTS-P2/phase4-remediation/REMEDY-PLAN.md` (Section 2+3)
- Decay report: `.claude/wip/SLOP-CHOP-TESTS-P2/phase3-decay/DECAY-REPORT.md`

## Scope

### IN SCOPE

All P2/P3 advisory items NOT already addressed by prior workstreams (WS-WSISO may have handled RS-014; WS-LIVEAPI may have handled RS-036, RS-044). Check prior merge results before starting each item.

### OUT OF SCOPE

- Production source files
- P1 items (already resolved)
- Items already resolved by prior workstreams

## Execution Plan

Work through items in batches, grouped by file. Verify after each batch.

### Batch 1: test_unified_cache_integration.py (RS-039, RS-045, RS-038, RS-018, RS-048)

**Order matters**: RS-039 before RS-045 (RS-045 depends on RS-039).

1. **RS-039**: Remove `LEGACY_CASCADE_PATH` skip from lines 280, 299. Verify tests pass when un-skipped:
   ```bash
   source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
     python -m pytest tests/integration/test_unified_cache_integration.py \
     -k "test_resolver_without_plugin or test_both_paths_return_same_value" -v
   ```
   If pass: remove `LEGACY_CASCADE_PATH` sentinel (line 49) if no other use-sites.

2. **RS-045**: Delete `test_builder_without_unified_store_uses_existing_path` (line ~200, double-skipped empty stub). Remove `LEGACY_PATH_REMOVED` sentinel (line 43) if no other uses.

3. **RS-038**: Remove `MIGRATION_REQUIRED` skip from `TestProjectDataFrameBuilderUnifiedIntegration` (line 182) and `TestNoRegression` (line 507). Either implement stub bodies or delete the classes. Remove `MIGRATION_REQUIRED` sentinel (line 37) if no other uses.

4. **RS-018**: If RS-038 implemented the stubs, this is done. Otherwise implement pass-only stubs using `ProgressiveProjectBuilder`.

5. **RS-048**: Update module docstring: remove `(Phase 3: ...)` qualifier.

**Verify batch**:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/test_unified_cache_integration.py -v --tb=short
```

### Batch 2: test_concurrency.py (RS-026, RS-027, RS-031)

1. **RS-026**: Remove or-hedge from snapshot assertion (line 479). Pick the semantically correct single condition.
2. **RS-027**: Add `assert len(tracker.get_dirty_entities()) == 50` after concurrent modifications.
3. **RS-031**: Rename `test_concurrent_commits_with_shared_entities` to `test_sequential_sessions_with_shared_entity` and update docstring.

**Verify batch**:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/validation/persistence/test_concurrency.py -v --tb=short
```

### Batch 3: Scattered trivial items

1. **RS-009 / RS-037**: Delete `test_completion_adapter_returns_empty` from `test_lifecycle_smoke.py` (lines 1695-1711). Verify `_CompletionAdapter` absent from source first.
2. **RS-033**: Remove `stale_task` and `task_with_due_date` fixtures from `tests/integration/automation/polling/conftest.py`.
3. **RS-034**: Remove `create_multi_result`, `create_task_hierarchy`, `CallTracker`, `call_tracker` from `tests/validation/persistence/conftest.py`.
4. **RS-040**: Delete `tests/integration/spike_write_diagnosis.py` entirely.
5. **RS-041**: Remove initiative tag from `tests/integration/test_cascading_field_resolution.py:108`.
6. **RS-042**: Remove `Per IMP-23:` from `tests/integration/test_hydration_cache_integration.py:91`.
7. **RS-043**: Remove `Per Story 3.2:` and `Per IMP-20:` from `tests/benchmarks/test_insights_benchmark.py`.
8. **RS-046**: Move `client_fixture` and `task_fixture` from `tests/integration/conftest.py` into `tests/integration/test_gid_validation_edge_cases.py`. Delete the conftest.
9. **RS-047**: Remove `Per TDD-CONV-AUDIT-001:` from `tests/integration/automation/polling/test_trigger_evaluator_integration.py:467`.

**Verify batch** (run affected directories):
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/ tests/validation/ tests/benchmarks/ \
  -n auto -q --tb=short
```

### Batch 4: Larger refactoring (if time permits)

1. **RS-003**: Narrow broad except in `test_e2e_offer_write_proof.py:335` to specific API exceptions.
2. **RS-004**: Extract shared mock setup in `test_entity_resolver_e2e.py` into a fixture.
3. **RS-006**: Remove redundant `import pytest` inside test functions in `test_gid_validation_edge_cases.py`. Convert `asyncio.run()` to `@pytest.mark.asyncio`. Parametrize identical test patterns.

**Verify batch**:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest \
  tests/integration/test_e2e_offer_write_proof.py \
  tests/integration/test_entity_resolver_e2e.py \
  tests/integration/test_gid_validation_edge_cases.py \
  -v --tb=short
```

## Verification Commands

For each batch, verify with the specified command before moving to the next batch.

After ALL batches:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/ tests/validation/ tests/benchmarks/ \
  -n auto -q --tb=short
```

## Escalation Triggers

- If RS-038/RS-018 stubs require reading ProgressiveProjectBuilder constructor and the implementation is complex, defer to a follow-up session.
- If RS-046 (conftest migration) breaks fixture resolution for other tests, keep the conftest and only remove dead fixtures.
- If batch count exceeds session budget, stop after Batch 3 (highest-value items addressed) and document remaining.

## Time Budget

- Estimated: 4-6 hours
- Batch 1 (unified cache): ~1.5 hours
- Batch 2 (concurrency): ~30 min
- Batch 3 (scattered trivial): ~1.5 hours
- Batch 4 (larger refactoring): ~2 hours (if time permits)

Commit with message prefix `test(hygiene):`.
