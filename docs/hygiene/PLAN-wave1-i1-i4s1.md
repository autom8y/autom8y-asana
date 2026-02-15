# Refactoring Plan: Wave 1 (I1 + I4-S1)

**Source**: `docs/hygiene/SMELL-wave1-i1-i4s1.md`
**Produced by**: architect-enforcer
**Date**: 2026-02-15

---

## Baseline

- **Test command**: `.venv/bin/pytest tests/ -x -q --timeout=60`
- **Expected baseline**: 10,149 passed, 46 skipped, 2 xfailed, 0 failures
- **Ruff command**: `ruff check tests/ --select F401 --no-fix --config 'lint.per-file-ignores = {}'`
- **Expected ruff baseline**: 141 violations (34 intentional in `test_reorg_imports.py` + 107 actionable)

**STEP 0**: Before any changes, run both commands and confirm baselines match expectations. If they do not match, STOP and escalate.

---

## Phase Sequencing

```
Phase 1 (WS-D) -> Phase 2 (WS-A) -> Phase 3 (WS-C) -> Phase 4 (WS-B)
                ^                  ^                  ^
           Rollback Point 1   Rollback Point 2   Rollback Point 3
```

Risk ordering: trivial -> auto-fix -> constant replacement -> exception narrowing with test updates.

---

## Phase 1: WS-D -- Redundant Pass Removal

**Blast radius**: 1 file, 1 line
**Risk**: Negligible

### RF-D01: Remove redundant `pass` in detection facade

**Before State**:
- `src/autom8_asana/models/business/detection/facade.py:180`: Line contains `pass` immediately after `logger.warning(...)` with `exc_info=True` at line 172-179. The `pass` is syntactically unnecessary because the `logger.warning(...)` call is already a statement in the except block.

```python
    except Exception:  # BROAD-CATCH: metrics -- per FR-DEGRADE-002, ...
        logger.warning(
            "detection_cache_store_failed_silent",
            extra={
                "task_gid": task.gid,
                "entry_type": EntryType.DETECTION.value,
            },
            exc_info=True,
        )
        pass  # <-- REMOVE THIS LINE
```

**After State**:
- Line 180 (`pass`) is deleted. The `except` block body is the `logger.warning(...)` call only.

**Invariants**:
- No behavior change -- `pass` after a statement is a no-op
- No import changes
- No test changes

**Verification**:
```bash
.venv/bin/pytest tests/unit/models/business/detection/ -x -q --timeout=60
```

**Commit**: `chore(hygiene): remove redundant pass in detection facade`

---

### ROLLBACK POINT 1

Verify full suite green before proceeding:
```bash
.venv/bin/pytest tests/ -x -q --timeout=60
```

---

## Phase 2: WS-A -- Unused Test Imports

**Blast radius**: ~60 test files (test-only, no source changes)
**Risk**: Low -- auto-fix tool, test-only files

### RF-A01: Auto-fix F401 violations via ruff

**Before State**:
- 107 F401 (unused import) violations across test files (excluding `test_reorg_imports.py`)
- 34 F401 violations in `tests/unit/cache/test_reorg_imports.py` that are **intentional** (import-path verification test)
- 1 non-auto-fixable violation requiring manual review

**After State**:
- 0 F401 violations in test files (excluding `test_reorg_imports.py`)
- `test_reorg_imports.py` retains all 34 imports with `# noqa: F401` comments to document intent
- The 1 non-auto-fixable import is resolved manually

**Procedure**:

1. Run auto-fix on all test files EXCEPT `test_reorg_imports.py`:
   ```bash
   ruff check tests/ --select F401 --fix --config 'lint.per-file-ignores = {}'
   ```

2. Restore `test_reorg_imports.py` to its pre-fix state (ruff will have removed the intentional imports):
   ```bash
   git checkout -- tests/unit/cache/test_reorg_imports.py
   ```

3. Add `# noqa: F401` comments to all import lines in `test_reorg_imports.py` that are flagged. These are intentional import-path-verification imports per the file's docstring. The noqa comments document the intent and suppress future ruff warnings.

4. Manually review the 1 non-auto-fixable import and resolve (likely a conditional import or `__all__` re-export pattern).

5. Verify ruff is clean:
   ```bash
   ruff check tests/ --select F401 --config 'lint.per-file-ignores = {}'
   ```
   Expected: 0 violations (the 34 in `test_reorg_imports.py` are now suppressed by `# noqa: F401`).

**Invariants**:
- No source code changes (test files only)
- No behavior change in any test
- All tests that previously passed still pass
- `test_reorg_imports.py` still verifies all import paths

**Verification**:
```bash
.venv/bin/pytest tests/ -x -q --timeout=60
ruff check tests/ --select F401 --config 'lint.per-file-ignores = {}'
```

**Commit**: `chore(hygiene): remove 107 unused test imports (F401) and annotate intentional imports`

---

### ROLLBACK POINT 2

Verify full suite green before proceeding:
```bash
.venv/bin/pytest tests/ -x -q --timeout=60
```

---

## Phase 3: WS-C -- Magic Number Constants

**Blast radius**: 2 source files, 3 lines changed
**Risk**: Low -- replacing hardcoded values with existing/new settings-driven constants

### RF-C01: Replace `ttl=1800` with `SECTION_CACHE_TTL` in sections.py

**Before State**:
- `src/autom8_asana/clients/sections.py:27` defines `SECTION_CACHE_TTL = get_settings().cache.ttl_section` (already exists, default 1800)
- `src/autom8_asana/clients/sections.py:130`: `ttl=1800` hardcoded
- `src/autom8_asana/clients/sections.py:365`: `ttl=1800` hardcoded

**After State**:
- Line 130: `ttl=SECTION_CACHE_TTL`
- Line 365: `ttl=SECTION_CACHE_TTL`
- No new imports needed (`SECTION_CACHE_TTL` is module-level in the same file)

**Invariants**:
- Default TTL value unchanged (1800 seconds)
- Now configurable via `ASANA_CACHE_TTL_SECTION` environment variable
- No test changes needed (TTL value is the same at default)

### RF-C02: Add `PROJECT_CACHE_TTL` constant in projects.py

**Before State**:
- `src/autom8_asana/clients/projects.py:117`: `ttl=900` hardcoded
- `settings.py:173-176`: `ttl_project` field exists with default=900, but no constant defined in `projects.py`

**After State**:
- New module-level constant in `projects.py`:
  ```python
  from autom8_asana.settings import get_settings

  # Cache TTL for project data (15 minutes)
  # Configurable via ASANA_CACHE_TTL_PROJECT environment variable
  PROJECT_CACHE_TTL = get_settings().cache.ttl_project
  ```
- Line 117: `ttl=PROJECT_CACHE_TTL`
- Requires adding `from autom8_asana.settings import get_settings` to imports

**Invariants**:
- Default TTL value unchanged (900 seconds)
- Now configurable via `ASANA_CACHE_TTL_PROJECT` environment variable
- No test changes needed (TTL value is the same at default)

**Verification**:
```bash
.venv/bin/pytest tests/unit/clients/ -x -q --timeout=60
```

**Commit**: `chore(hygiene): replace magic TTL numbers with named constants (B11)`

---

### ROLLBACK POINT 3

Verify full suite green before proceeding:
```bash
.venv/bin/pytest tests/ -x -q --timeout=60
```

---

## Phase 4: WS-B -- Exception Narrowing (I4-S1 MECHANICAL)

**Blast radius**: 16 source files, 30 catch sites, ~12 test files
**Risk**: Medium -- requires coordinated source + test mock updates

### Import Context

The following error tuples are defined in `src/autom8_asana/core/exceptions.py:274-321`:

| Tuple | Contents |
|-------|----------|
| `CACHE_TRANSIENT_ERRORS` | `ALL_TRANSPORT_ERRORS + (CacheConnectionError,)` -- includes S3TransportError, BotoCoreError, ClientError, ConnectionError, TimeoutError, OSError, RedisTransportError, RedisError, CacheConnectionError |
| `S3_TRANSPORT_ERRORS` | S3TransportError, BotoCoreError, ClientError, ConnectionError, TimeoutError, OSError |
| `REDIS_TRANSPORT_ERRORS` | RedisTransportError, RedisError |
| `ALL_TRANSPORT_ERRORS` | `S3_TRANSPORT_ERRORS + REDIS_TRANSPORT_ERRORS` |

For test mocks, `ConnectionError` is a Python builtin present in both `CACHE_TRANSIENT_ERRORS` and `S3_TRANSPORT_ERRORS`, making it the safest replacement for `side_effect=Exception(...)`.

### Commit Group B1: persistence/ (6 sites: M04, M05, M06, M07, M08, M09)

#### RF-M04: persistence/cache_invalidator.py:147

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/persistence/cache_invalidator.py:147` |
| **Current catch** | `except Exception as exc:` |
| **Target catch** | `except CACHE_TRANSIENT_ERRORS as exc:` |
| **Import needed** | Yes: `from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS` |
| **Test mock risk** | LOW |
| **Test update** | None required |

#### RF-M05: persistence/cache_invalidator.py:184

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/persistence/cache_invalidator.py:184` |
| **Current catch** | `except Exception as exc:` |
| **Target catch** | `except CACHE_TRANSIENT_ERRORS as exc:` |
| **Import needed** | Same import as M04 (shared file) |
| **Test mock risk** | LOW |
| **Test update** | None required |

#### RF-M06: persistence/cascade.py:181

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/persistence/cascade.py:181` |
| **Current catch** | `except Exception as e:` |
| **Target catch** | `except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:` |
| **Import needed** | No (all builtins) |
| **Test mock risk** | MEDIUM |
| **Test files** | `tests/unit/persistence/test_cascade.py` |
| **Test update** | No side_effect patterns found in `test_cascade.py` that use `Exception(...)`. The test file tests `CascadeResult` data classes and field-not-found scenarios, not the exception path at line 181. No changes needed. Reclassified to LOW upon investigation. |

#### RF-M07: persistence/healing.py:245

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/persistence/healing.py:245` |
| **Current catch** | `except Exception as e:` |
| **Target catch** | `except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:` |
| **Import needed** | No (all builtins) |
| **Test mock risk** | MEDIUM |
| **Test files** | `tests/unit/persistence/test_healing.py`, `tests/unit/persistence/test_session_healing.py` |
| **Test update -- test_healing.py** | Line 221: `mock_client.tasks.add_to_project_async.side_effect = api_error` where `api_error = RuntimeError("API error")` at line 220. Already uses `RuntimeError`. No change needed. Line 400-403: `side_effect = [None, RuntimeError("API error"), None]`. Already uses `RuntimeError`. No change needed. |
| **Test update -- test_session_healing.py** | Line 520: `side_effect=Exception("API Error")` -- **MUST CHANGE** to `side_effect=ConnectionError("API Error")`. Line 559: `side_effect=Exception("API Error")` -- **MUST CHANGE** to `side_effect=ConnectionError("API Error")`. |

#### RF-M08: persistence/holder_ensurer.py:223

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/persistence/holder_ensurer.py:223` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except (ConnectionError, TimeoutError, OSError, RuntimeError):` |
| **Import needed** | No (all builtins) |
| **Test mock risk** | MEDIUM |
| **Test files** | `tests/unit/persistence/test_holder_ensurer.py` |
| **Test update** | Line 629: `side_effect=ConnectionError("API down")`. Already uses `ConnectionError`. No change needed. Reclassified to LOW upon investigation. |

#### RF-M09: persistence/action_executor.py:327

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/persistence/action_executor.py:327` |
| **Current catch** | `except Exception as e:` |
| **Target catch** | `except (ConnectionError, TimeoutError, OSError, RuntimeError, ValueError) as e:` |
| **Import needed** | No (all builtins) |
| **Test mock risk** | MEDIUM |
| **Test files** | `tests/unit/persistence/test_action_executor.py` |
| **Test update** | Line 131: `side_effect = RuntimeError("API error")`. Already uses `RuntimeError`. Line 159-163: `side_effect = [{"data": {}}, RuntimeError("API error"), {"data": {}}]`. Already uses `RuntimeError`. No change needed. Reclassified to LOW upon investigation. |

**Commit**: `refactor(persistence): narrow exception catches at 6 sites (M04-M09)`

**Verification**:
```bash
.venv/bin/pytest tests/unit/persistence/ -x -q --timeout=60
```

---

### Commit Group B2: models/ (6 sites: M11, M12, M13, M14, M15, M16)

#### RF-M11: models/business/detection/facade.py:112

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/models/business/detection/facade.py:112` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except CACHE_TRANSIENT_ERRORS:` |
| **Import needed** | No (already imported at line 25) |
| **Test mock risk** | LOW |
| **Test update** | None required |

#### RF-M12: models/business/detection/facade.py:171

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/models/business/detection/facade.py:171` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except CACHE_TRANSIENT_ERRORS:` |
| **Import needed** | No (already imported at line 25) |
| **Test mock risk** | LOW |
| **Test update** | None required |

Note: The `pass` at line 180 was already removed in Phase 1 (RF-D01).

#### RF-M13: models/business/detection/facade.py:215

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/models/business/detection/facade.py:215` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except (ValidationError, KeyError, AttributeError):` |
| **Import needed** | Yes: `from pydantic import ValidationError` (check if already imported in file) |
| **Test mock risk** | LOW |
| **Test update** | None required |

#### RF-M14: models/business/matching/normalizers.py:75

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/models/business/matching/normalizers.py:75` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except (ValueError, TypeError):` |
| **Import needed** | No (builtins) |
| **Test mock risk** | LOW |
| **Test update** | None required |
| **Note** | Also resolves B09-2 (swallowed exception). The `pass` body is intentional for phonenumber parsing -- falls through to digits-only extraction. |

#### RF-M15: models/business/resolution.py:217

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/models/business/resolution.py:217` |
| **Current catch** | `except Exception as e:` |
| **Target catch** | `except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:` |
| **Import needed** | No (all builtins) |
| **Test mock risk** | MEDIUM |
| **Test files** | `tests/unit/models/business/test_resolution.py` |
| **Test update** | Line 480: `side_effect=RuntimeError("Network error")`. Already uses `RuntimeError`. No change needed. Reclassified to LOW upon investigation. |

#### RF-M16: models/business/resolution.py:290

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/models/business/resolution.py:290` |
| **Current catch** | `except Exception as e:` |
| **Target catch** | `except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:` |
| **Import needed** | No (all builtins) |
| **Test mock risk** | MEDIUM |
| **Test files** | `tests/unit/models/business/test_resolution.py` |
| **Test update** | Line 769: `side_effect=RuntimeError("Offer resolution error")`. Already uses `RuntimeError`. No change needed. Reclassified to LOW upon investigation. |

**Commit**: `refactor(models): narrow exception catches at 6 sites (M11-M16)`

**Verification**:
```bash
.venv/bin/pytest tests/unit/models/ -x -q --timeout=60
```

---

### Commit Group B3: services/ (5 sites: M01, M02, M03, M26, M27, M28)

#### RF-M01: services/field_write_service.py:353

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/services/field_write_service.py:353` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except CACHE_TRANSIENT_ERRORS:` |
| **Import needed** | Yes: `from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS` |
| **Test mock risk** | LOW |
| **Test update** | None required |

#### RF-M02: services/universal_strategy.py:256

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/services/universal_strategy.py:256` |
| **Current catch** | `except Exception as e:` |
| **Target catch** | `except (*CACHE_TRANSIENT_ERRORS, RuntimeError) as e:` -- Note: Python does not support splat in except. Use a module-level tuple: `_INDEX_BUILD_ERRORS = CACHE_TRANSIENT_ERRORS + (RuntimeError,)` and catch `except _INDEX_BUILD_ERRORS as e:` |
| **Import needed** | No (`CACHE_TRANSIENT_ERRORS` already imported at line 30) |
| **Test mock risk** | MEDIUM |
| **Test files** | `tests/unit/services/test_universal_strategy.py` |
| **Test update** | Line 1252: `raise ConnectionError("Simulated index build failure")`. Already uses `ConnectionError`. No change needed. Reclassified to LOW upon investigation. |

#### RF-M03: services/universal_strategy.py:648

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/services/universal_strategy.py:648` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except (KeyError, RuntimeError):` |
| **Import needed** | No (builtins) |
| **Test mock risk** | LOW |
| **Test update** | None required |

#### RF-M26: services/universal_strategy.py:464

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/services/universal_strategy.py:464` |
| **Current catch** | `except Exception as e:` |
| **Target catch** | `except (KeyError, AttributeError, TypeError) as e:` |
| **Import needed** | No (builtins) |
| **Test mock risk** | LOW |
| **Test update** | None required |

#### RF-M27: services/universal_strategy.py:523

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/services/universal_strategy.py:523` |
| **Current catch** | `except Exception as e:` |
| **Target catch** | `except CACHE_TRANSIENT_ERRORS as e:` |
| **Import needed** | No (already imported at line 30) |
| **Test mock risk** | LOW |
| **Test update** | None required |

#### RF-M28: services/universal_strategy.py:623

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/services/universal_strategy.py:623` |
| **Current catch** | `except Exception as e:` |
| **Target catch** | `except _INDEX_BUILD_ERRORS as e:` -- reuse the same `_INDEX_BUILD_ERRORS = CACHE_TRANSIENT_ERRORS + (RuntimeError,)` tuple defined for M02, but expanded: `_DATAFRAME_BUILD_ERRORS = CACHE_TRANSIENT_ERRORS + (RuntimeError, ValueError)` |
| **Import needed** | No (already imported at line 30) |
| **Test mock risk** | MEDIUM |
| **Test files** | `tests/unit/services/test_universal_strategy.py` |
| **Test update** | No side_effect patterns found for `_build_entity_dataframe`. No change needed. Reclassified to LOW upon investigation. |

**Implementation note for universal_strategy.py**: Define two module-level tuples near the existing `CACHE_TRANSIENT_ERRORS` import:
```python
_INDEX_BUILD_ERRORS = CACHE_TRANSIENT_ERRORS + (RuntimeError,)
_DATAFRAME_BUILD_ERRORS = CACHE_TRANSIENT_ERRORS + (RuntimeError, ValueError)
```

**Commit**: `refactor(services): narrow exception catches at 6 sites (M01-M03, M26-M28)`

**Verification**:
```bash
.venv/bin/pytest tests/unit/services/ -x -q --timeout=60
```

---

### Commit Group B4: automation/ + resolution/ (5 sites: M17, M22, M23, M24, M25)

#### RF-M17: resolution/write_registry.py:98

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/resolution/write_registry.py:98` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except (AttributeError, TypeError):` |
| **Import needed** | No (builtins) |
| **Test mock risk** | LOW |
| **Test update** | None required |
| **Note** | Also resolves B09-3 (swallowed exception with no annotation and no logging). The `continue` body is acceptable here -- this is attribute scanning where some attributes raise on access, and logging every inaccessible attribute would be noise. |

#### RF-M22: automation/workflows/conversation_audit.py:117

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/automation/workflows/conversation_audit.py:117` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except (ConnectionError, TimeoutError, OSError):` |
| **Import needed** | No (builtins) |
| **Test mock risk** | LOW |
| **Test update** | None required |
| **Note** | Also resolves B09-5 (swallowed exception). The `pass` body is intentional -- non-CB errors during circuit breaker probe are ignorable. |

#### RF-M23: automation/workflows/insights_export.py:140

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/automation/workflows/insights_export.py:140` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except (ConnectionError, TimeoutError, OSError):` |
| **Import needed** | No (builtins) |
| **Test mock risk** | LOW |
| **Test update** | None required |
| **Note** | Also resolves B09-6 (swallowed exception). Same pattern as M22. |

#### RF-M24: automation/workflows/pipeline_transition.py:107

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/automation/workflows/pipeline_transition.py:107` |
| **Current catch** | `except Exception as e:` |
| **Target catch** | `except (KeyError, ValueError, AttributeError) as e:` |
| **Import needed** | No (builtins) |
| **Test mock risk** | LOW |
| **Test update** | None required |

#### RF-M25: models/business/seeder.py:583

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/models/business/seeder.py:583` |
| **Current catch** | `except Exception as e:` |
| **Target catch** | `except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:` |
| **Import needed** | No (all builtins) |
| **Test mock risk** | MEDIUM |
| **Test files** | `tests/unit/models/business/test_seeder.py` |
| **Test update** | Line 393: `side_effect=RuntimeError("Unexpected error")`. Already uses `RuntimeError`. Line 482: `side_effect=RuntimeError("Unexpected error")`. Already uses `RuntimeError`. No change needed. Reclassified to LOW upon investigation. |

**Note**: M25 is in `models/` not `automation/`, but is grouped here because the commit is sized for manageability. Alternative: include it in Group B2. The janitor may regroup if preferred.

**Commit**: `refactor(automation): narrow exception catches at 5 sites (M17, M22-M25)`

**Verification**:
```bash
.venv/bin/pytest tests/unit/automation/ tests/unit/resolution/ tests/unit/models/business/test_seeder.py -x -q --timeout=60
```

---

### Commit Group B5: api/ (3 sites: M20, M21, M29, M30)

#### RF-M20: api/routes/resolver.py:412

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/api/routes/resolver.py:412` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except (KeyError, AttributeError, RuntimeError):` |
| **Import needed** | No (builtins) |
| **Test mock risk** | LOW |
| **Test update** | None required |
| **Note** | Also resolves B09-4 (swallowed exception). The `pass` body is acceptable -- this is non-critical metadata lookup. |

#### RF-M21: api/routes/webhooks.py:316

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/api/routes/webhooks.py:316` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except (ValueError, UnicodeDecodeError):` |
| **Import needed** | No (builtins). Note: `json.JSONDecodeError` is a subclass of `ValueError`, so catching `ValueError` already covers JSON parse errors. |
| **Test mock risk** | LOW |
| **Test update** | None required |

#### RF-M29: api/routes/webhooks.py:238

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/api/routes/webhooks.py:238` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except CACHE_TRANSIENT_ERRORS:` |
| **Import needed** | Yes: `from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS` |
| **Test mock risk** | LOW |
| **Test update** | None required. Test at line 292 already uses `side_effect=ConnectionError("Redis down")`. |

#### RF-M30: api/routes/webhooks.py:275

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/api/routes/webhooks.py:275` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except (ConnectionError, TimeoutError, OSError, RuntimeError):` |
| **Import needed** | No (builtins) |
| **Test mock risk** | MEDIUM |
| **Test files** | `tests/unit/api/routes/test_webhooks.py` |
| **Test update** | Line 581: `side_effect=RuntimeError("Dispatch failed")`. Already uses `RuntimeError`. No change needed. Reclassified to LOW upon investigation. |

**Commit**: `refactor(api): narrow exception catches at 4 sites (M20-M21, M29-M30)`

**Verification**:
```bash
.venv/bin/pytest tests/unit/api/ -x -q --timeout=60
```

---

### Commit Group B6: cache/ (2 sites: M18, M19)

#### RF-M18: cache/dataframe/tiers/progressive.py:178

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/cache/dataframe/tiers/progressive.py:178` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except (json.JSONDecodeError, KeyError, UnicodeDecodeError):` |
| **Import needed** | Yes: `import json` at file top (for `json.JSONDecodeError`). Note: `json` is already used inline at line 174 (`import json`; `json.loads(...)`) but the import is inside the try block. Move it to file-level or use `except (ValueError, KeyError, UnicodeDecodeError):` since `JSONDecodeError` subclasses `ValueError`. Recommendation: Use `except (ValueError, KeyError, UnicodeDecodeError):` to avoid import changes. |
| **Test mock risk** | LOW |
| **Test update** | None required |
| **Note** | Also resolves B09-1 (swallowed exception). The `pass` body is intentional -- graceful degradation for watermark metadata. |

#### RF-M19: cache/dataframe/tiers/progressive.py:288

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/cache/dataframe/tiers/progressive.py:288` |
| **Current catch** | `except Exception:` |
| **Target catch** | `except S3_TRANSPORT_ERRORS:` |
| **Import needed** | No (`S3_TRANSPORT_ERRORS` already imported at line 27) |
| **Test mock risk** | LOW |
| **Test update** | None required |

**Commit**: `refactor(cache): narrow exception catches at 2 sites (M18-M19)`

**Verification**:
```bash
.venv/bin/pytest tests/unit/cache/ -x -q --timeout=60
```

---

### Commit Group B7: persistence/session.py (1 site: M10)

#### RF-M10: persistence/session.py:1029

| Field | Value |
|-------|-------|
| **File** | `src/autom8_asana/persistence/session.py:1029` |
| **Current catch** | `except Exception as e:` |
| **Target catch** | `except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:` |
| **Import needed** | No (all builtins) |
| **Test mock risk** | LOW |
| **Test update** | None required. The BROAD-CATCH annotation is already present. |

**Commit**: `refactor(persistence): narrow session automation catch (M10)`

**Verification**:
```bash
.venv/bin/pytest tests/unit/persistence/test_session*.py -x -q --timeout=60
```

---

## Final Verification

After all phases complete:

```bash
# Full test suite
.venv/bin/pytest tests/ -x -q --timeout=60

# Verify F401 clean
ruff check tests/ --select F401 --config 'lint.per-file-ignores = {}'

# Verify except Exception count reduced
# Before: 146 catch sites
# After: 146 - 30 = 116 catch sites (60 BOUNDARY + 56 COMPLEX)
grep -rn "except Exception" src/autom8_asana/ | grep -v "docstring\|#.*except Exception" | wc -l
```

Expected final state:
- 10,149 passed, 46 skipped, 2 xfailed, 0 failures
- 0 F401 violations
- ~116 remaining `except Exception` sites (all BOUNDARY or COMPLEX, deferred to I4-S2)

---

## Risk Matrix

| Phase | Work Stream | Blast Radius | Failure Detection | Recovery Path |
|-------|-------------|-------------|-------------------|---------------|
| 1 | WS-D: Redundant pass | 1 file, 0 behavior | Detection unit tests | `git revert HEAD` |
| 2 | WS-A: Unused imports | ~60 test files, 0 source | Full test suite | `git revert HEAD` |
| 3 | WS-C: Magic numbers | 2 source files, 3 lines | Client unit tests | `git revert HEAD` |
| 4-B1 | WS-B: persistence/ | 4 source + 1 test file | Persistence unit tests | `git revert HEAD` |
| 4-B2 | WS-B: models/ | 4 source files | Models unit tests | `git revert HEAD` |
| 4-B3 | WS-B: services/ | 2 source files | Services unit tests | `git revert HEAD` |
| 4-B4 | WS-B: automation+resolution | 4 source files | Automation + resolution tests | `git revert HEAD` |
| 4-B5 | WS-B: api/ | 2 source files | API route tests | `git revert HEAD` |
| 4-B6 | WS-B: cache/ | 1 source file | Cache unit tests | `git revert HEAD` |
| 4-B7 | WS-B: session | 1 source file | Session unit tests | `git revert HEAD` |

Each commit is independently revertible. No commit depends on a prior WS-B commit.

---

## B09 Overlap Resolution Summary

| B09 Item | Resolution Via | Notes |
|----------|---------------|-------|
| B09-1: `progressive.py:178` | RF-M18 (narrow to ValueError/KeyError/UnicodeDecodeError) | `pass` body retained -- intentional fallback |
| B09-2: `normalizers.py:75` | RF-M14 (narrow to ValueError/TypeError) | `pass` body retained -- intentional fallback |
| B09-3: `write_registry.py:98` | RF-M17 (narrow to AttributeError/TypeError) | `continue` body retained -- attribute scanning |
| B09-4: `resolver.py:412` | RF-M20 (narrow to KeyError/AttributeError/RuntimeError) | `pass` body retained -- non-critical metadata |
| B09-5: `conversation_audit.py:117` | RF-M22 (narrow to ConnectionError/TimeoutError/OSError) | `pass` body retained -- non-CB error ignorable |
| B09-6: `insights_export.py:140` | RF-M23 (narrow to ConnectionError/TimeoutError/OSError) | `pass` body retained -- non-CB error ignorable |

---

## Test Mock Update Summary

Of the 12 MEDIUM-risk sites identified in the smell report, investigation revealed that **only 2 test locations actually require changes**. The remaining 10 either already use a narrowed exception type (typically `RuntimeError` or `ConnectionError`) or have no test mocks exercising the exception path.

| Site | Test File | Current side_effect | Required Change |
|------|-----------|-------------------|-----------------|
| M07 (healing.py:245) | `tests/unit/persistence/test_session_healing.py:520` | `Exception("API Error")` | Change to `ConnectionError("API Error")` |
| M07 (healing.py:245) | `tests/unit/persistence/test_session_healing.py:559` | `Exception("API Error")` | Change to `ConnectionError("API Error")` |

All other MEDIUM sites were reclassified to LOW after investigation:
- M02 (universal_strategy.py:256): Test uses `ConnectionError` already
- M06 (cascade.py:181): No exception-path test mocks found
- M08 (holder_ensurer.py:223): Test uses `ConnectionError` already
- M09 (action_executor.py:327): Test uses `RuntimeError` already
- M15 (resolution.py:217): Test uses `RuntimeError` already
- M16 (resolution.py:290): Test uses `RuntimeError` already
- M25 (seeder.py:583): Test uses `RuntimeError` already
- M28 (universal_strategy.py:623): No exception-path test mocks found
- M30 (webhooks.py:275): Test uses `RuntimeError` already

---

## Janitor Notes

1. **Commit message convention**: Use `chore(hygiene):` for WS-A/WS-C/WS-D, `refactor(scope):` for WS-B. Include the smell IDs in commit body.

2. **BROAD-CATCH annotation updates**: When narrowing a catch site, update or remove the `# BROAD-CATCH:` comment. Replace with the narrowed type description if keeping a comment, e.g., `# CACHE_TRANSIENT_ERRORS: isolation -- per-gid loop`.

3. **Import ordering**: New imports from `autom8_asana.core.exceptions` should follow existing import order in each file. Use `isort` or `ruff format` after changes.

4. **WS-A auto-fix caution**: After running `ruff --fix`, immediately restore `test_reorg_imports.py` via `git checkout` before doing anything else. The ruff fix will remove the intentional imports.

5. **WS-B tuple syntax**: Python except clauses require parenthesized tuples. Use `except (A, B, C) as e:` not `except A, B, C as e:`. For module-level tuple variables, use `except TUPLE_VAR as e:` without parens.

6. **Test run between each B-group commit**: Run the scoped test suite after each commit group. Only proceed to the next group if all tests pass.

7. **Critical ordering within Phase 4**: Groups B1 through B7 are independent and can be done in any order. However, if a group fails tests, fix it before proceeding to the next to maintain a clean rollback point.

8. **The 2 test mock updates (M07)**: These are in `test_session_healing.py` and affect the `healing.py:245` narrowing. They MUST be included in the same commit as the source change (Group B1). Both changes are mechanical: replace `Exception(` with `ConnectionError(` -- the error message strings stay the same.

---

## Attestation Table

| Artifact | Path | Verified via Read? |
|----------|------|-------------------|
| Smell Report | `/Users/tomtenuta/Code/autom8_asana/docs/hygiene/SMELL-wave1-i1-i4s1.md` | Yes -- read in full |
| Error tuples | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/exceptions.py:274-321` | Yes |
| detection/facade.py (WS-D, M11, M12, M13) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/detection/facade.py` | Yes -- lines 105-218 |
| projects.py (WS-C) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/projects.py` | Yes -- lines 1-25, 110-123 |
| sections.py (WS-C) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | Yes -- lines 20-34, 125-136, 360-374 |
| settings.py (WS-C) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/settings.py:165-178` | Yes |
| test_reorg_imports.py (WS-A) | `/Users/tomtenuta/Code/autom8_asana/tests/unit/cache/test_reorg_imports.py` | Yes -- lines 1-50 |
| field_write_service.py (M01) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/field_write_service.py:345-361` | Yes |
| universal_strategy.py (M02, M03, M26-M28) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py` | Yes -- lines 245-270, 455-474, 515-534, 613-634, 640-652 |
| cache_invalidator.py (M04, M05) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/cache_invalidator.py:1-20, 140-192` | Yes |
| cascade.py (M06) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/cascade.py:170-185` | Yes |
| healing.py (M07) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/healing.py:235-260` | Yes |
| holder_ensurer.py (M08) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/holder_ensurer.py:213-237` | Yes |
| action_executor.py (M09) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/action_executor.py:317-333` | Yes |
| session.py (M10) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py:1020-1037` | Yes |
| normalizers.py (M14) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/matching/normalizers.py:68-82` | Yes |
| resolution.py (M15, M16) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/resolution.py` | Yes -- lines 207-230, 280-303 |
| write_registry.py (M17) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/resolution/write_registry.py:90-104` | Yes |
| progressive.py (M18, M19) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/progressive.py` | Yes -- lines 170-194, 280-290 |
| resolver.py (M20) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py:404-423` | Yes |
| webhooks.py (M21, M29, M30) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/webhooks.py` | Yes -- lines 1-25, 230-244, 265-281, 308-327 |
| conversation_audit.py (M22) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/conversation_audit.py:110-120` | Yes |
| insights_export.py (M23) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/insights_export.py:133-143` | Yes |
| pipeline_transition.py (M24) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/pipeline_transition.py:100-110` | Yes |
| seeder.py (M25) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/seeder.py:560-588` | Yes |
| test_universal_strategy.py | `/Users/tomtenuta/Code/autom8_asana/tests/unit/services/test_universal_strategy.py` | Yes -- lines 1-50, 1219-1288 |
| test_cascade.py | `/Users/tomtenuta/Code/autom8_asana/tests/unit/persistence/test_cascade.py` | Yes (grep search, no Exception side_effects) |
| test_healing.py | `/Users/tomtenuta/Code/autom8_asana/tests/unit/persistence/test_healing.py:210-260` | Yes |
| test_session_healing.py | `/Users/tomtenuta/Code/autom8_asana/tests/unit/persistence/test_session_healing.py:510-569` | Yes -- **2 updates required** |
| test_holder_ensurer.py | `/Users/tomtenuta/Code/autom8_asana/tests/unit/persistence/test_holder_ensurer.py:620-643` | Yes |
| test_action_executor.py (persistence) | `/Users/tomtenuta/Code/autom8_asana/tests/unit/persistence/test_action_executor.py:120-240` | Yes |
| test_action_executor.py (polling) | `/Users/tomtenuta/Code/autom8_asana/tests/unit/automation/polling/test_action_executor.py:115-240` | Yes -- **4 sites use Exception(), but these test the POLLING executor, not M09's persistence executor** |
| test_resolution.py | `/Users/tomtenuta/Code/autom8_asana/tests/unit/models/business/test_resolution.py:470-520, 640-690` | Yes |
| test_seeder.py | `/Users/tomtenuta/Code/autom8_asana/tests/unit/models/business/test_seeder.py:365-490` | Yes |
| test_webhooks.py | `/Users/tomtenuta/Code/autom8_asana/tests/unit/api/routes/test_webhooks.py:570-600` | Yes |

### Polling Action Executor Clarification

The smell report lists M09 as `persistence/action_executor.py:327`. The test file `tests/unit/automation/polling/test_action_executor.py` contains 4 `side_effect=Exception(...)` patterns (lines 122, 176, 230, 380), BUT these test the **polling** `ActionExecutor` at `automation/polling/action_executor.py`, NOT the persistence `ActionExecutor` at `persistence/action_executor.py`. These are two different classes in different modules. The persistence action executor tests at `tests/unit/persistence/test_action_executor.py` already use `RuntimeError`. No cross-contamination.

However, `automation/polling/action_executor.py:181` is listed in the smell report as a BOUNDARY site (row 19 of the BOUNDARY table), meaning it stays as `except Exception` and its tests do NOT need updating. This is confirmed.
