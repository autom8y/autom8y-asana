# WS-AUTO Session Prompt

## Rite & Workflow
- Rite: hygiene
- Workflow: `/task`
- Complexity: SPOT

## Objective

Apply 5 diff-ready AUTO patches from the SLOP-CHOP-TESTS-P2 remedy plan. All patches are mechanically safe -- no behavioral judgment required. Apply each patch, run the verification command, confirm pass, proceed.

## Context

- Seed doc: `.claude/wip/REM-HYGIENE/WS-AUTO.md`
- Remedy plan: `.claude/wip/SLOP-CHOP-TESTS-P2/phase4-remediation/REMEDY-PLAN.md` (Section 1: AUTO Patches)

## Scope

### IN SCOPE

| RS-ID | File | Fix |
|-------|------|-----|
| RS-008 | `tests/integration/test_custom_field_type_validation.py:493-501` | Rename `test_boolean_rejected_as_number` to `test_boolean_accepted_as_number`, update docstring and comment |
| RS-010 | `tests/integration/test_entity_write_smoke.py:995` | Change `except Exception:` to `except (AttributeError, TypeError):` |
| RS-019 | `tests/integration/test_unified_cache_integration.py:594,624` | Add `assert elapsed_ms < 1000.0` after each timing print |
| RS-021 | `tests/integration/test_platform_performance.py:236` | Add `assert fetch_count == 2` after second resolve_batch |
| RS-024 | `tests/validation/persistence/test_concurrency.py:212` | Change `assert len(levels) >= 0` to `assert len(levels) >= 1` with failure message |

### OUT OF SCOPE

- Any production source files
- Any other test files
- Adding new test cases
- Changing test logic beyond the specified patches

## Execution Plan

Apply in this order (any order is safe, but this groups by directory):

### Patch 1: RS-008

**File**: `tests/integration/test_custom_field_type_validation.py`

```diff
-    def test_boolean_rejected_as_number(self):
-        """Boolean should not be accepted as number (bool is int subclass)."""
+    def test_boolean_accepted_as_number(self):
+        """Boolean is accepted as number because bool is a subclass of int in Python."""
         accessor = CustomFieldAccessor(
             data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
         )
-        # Note: bool is a subclass of int in Python, so this will be accepted
-        # This is consistent with Python's type system
-        accessor.set("Budget", True)  # Allowed because bool is int subclass
+        accessor.set("Budget", True)  # bool is int subclass; accepted by Python type system
         assert accessor.get("Budget") is True
```

**Verify**:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/test_custom_field_type_validation.py::TestValidationEdgeCases::test_boolean_accepted_as_number -v
```

### Patch 2: RS-010

**File**: `tests/integration/test_entity_write_smoke.py`

Change line 995:
```diff
-            except Exception:
+            except (AttributeError, TypeError):
```

**Verify**:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/test_entity_write_smoke.py::test_process_has_descriptors -v
```

### Patch 3: RS-019

**File**: `tests/integration/test_unified_cache_integration.py`

After each `print(f"... {elapsed_ms:.2f}ms")` line (at approximately lines 594 and 624), insert:
```python
        assert elapsed_ms < 1000.0, (
            f"100 lookups took {elapsed_ms:.2f}ms, expected < 1000ms"
        )
```

**Verify**:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/test_unified_cache_integration.py::TestPerformanceTiming -v
```

### Patch 4: RS-021

**File**: `tests/integration/test_platform_performance.py`

After the comment "second call should still hit cache (fetch_count unchanged)" (approximately line 236), insert:
```python
        assert fetch_count == 2, (
            f"Cache miss on second resolve_batch: fetch_count advanced to {fetch_count}, expected 2"
        )
```

**Verify**:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/test_platform_performance.py::TestHierarchyAwareResolver::test_resolve_batch_caches_results -v
```

### Patch 5: RS-024

**File**: `tests/validation/persistence/test_concurrency.py`

```diff
         levels = graph.get_levels()
-        assert len(levels) >= 0  # Just verify it doesn't crash
+        assert len(levels) >= 1, (
+            f"get_levels() returned empty result after concurrent graph build: {levels!r}"
+        )
```

**Verify**:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest "tests/validation/persistence/test_concurrency.py" -k "test_concurrent_graph" -v
```

## Final Verification

After all 5 patches:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest \
  tests/integration/test_custom_field_type_validation.py \
  tests/integration/test_entity_write_smoke.py \
  tests/integration/test_unified_cache_integration.py \
  tests/integration/test_platform_performance.py \
  tests/validation/persistence/test_concurrency.py \
  -v --tb=short
```

## Time Budget

- Estimated: 30 minutes total
- ~5 min per patch (edit + verify)

Commit with message prefix `test(hygiene):`.
