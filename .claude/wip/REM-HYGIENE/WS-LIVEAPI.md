# WS-LIVEAPI: Dead String-Literal Test Suite

**Objective**: Resolve the dead string-literal test suite in `test_live_api.py` by either promoting it to active code or deleting it after coverage verification.

---

## Source Findings

| RS-ID | Finding | Severity | Confidence |
|-------|---------|----------|------------|
| RS-020 | Entire test suite (TestLiveAPICreate, TestLiveAPIUpdate, TestLiveAPIBatch, TestLiveAPIDelete, TestLiveAPIErrors) stored as triple-quoted string. Dead Python. Blocking condition ("once save_session() is implemented") is met. | DEFECT HIGH | HIGH |

Related temporal findings:
| RS-035 | Same as RS-020 from temporal debt angle (63-day-old orphaned infra) | SMELL | -- |
| RS-044 | Dead env-var shim fixtures in persistence conftest (scaffolded for these tests) | SMELL | -- |
| RS-036 | Stale "uncomment when available" scaffold comments | SMELL | -- |

---

## File Targets

- **Test file**: `tests/integration/persistence/test_live_api.py` (lines 42-306)
- **Conftest**: `tests/integration/persistence/conftest.py` (fixtures at lines 40, 47, 53, and scaffold at lines 58-80)
- **Coverage reference (read only)**: `tests/integration/persistence/test_action_batch_integration.py`
- **Production source (read only)**: `src/autom8_asana/persistence/session.py` (SaveSession API)

---

## Decision Tree

### Step 1: Coverage Verification

Read `test_action_batch_integration.py` to determine if it covers the same scenarios as the dead string-literal suite:
- Create operations
- Update operations
- Batch operations
- Delete operations
- Error handling

### Step 2a: If Coverage Exists (Option B -- Delete)

1. Delete lines 42-306 (the entire string literal block)
2. Delete `TestIntegrationInfrastructure` class if it only checks env vars
3. Delete dead env-var shim fixtures from conftest.py (RS-044: `asana_token`, `workspace_gid`, `project_gid`)
4. Remove stale scaffold comments from conftest.py (RS-036)
5. Verify no collection errors

### Step 2b: If Coverage Gap Exists (Option A -- Promote)

1. Extract the string literal into active Python code
2. Adapt imports, method signatures, and fixtures to current SaveSession API
3. Guard with `@pytest.mark.skipif(not os.getenv("ASANA_ACCESS_TOKEN"), reason="requires live Asana credentials")`
4. Verify tests are collected by pytest
5. Verify tests pass in skip mode (no credentials in CI)

---

## Effort Estimate

- **Total**: ~2 hours
- **Breakdown**: ~30 min coverage verification, ~1.5h implementation (promote or delete + cleanup)
- **Risk**: LOW for delete path, MEDIUM for promote path (SaveSession API may have diverged from string literal assumptions)

---

## Dependencies

- None. File has zero overlap with other workstreams.

---

## Rite / Complexity

- **Rite**: 10x-dev (recommended, confirm at dispatch)
- **Complexity**: MODULE
