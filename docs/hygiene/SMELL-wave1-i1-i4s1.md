# Smell Report: Wave 1 (I1 + I4-S1)

## Baseline

- **Test count**: 10,149 passed, 46 skipped, 2 xfailed, 0 failures, 0 errors
- **`except Exception` grep matches**: 148 (146 actual catch sites + 2 docstring references)
- **`except Exception` catch sites**: 146
- **Date**: 2026-02-15
- **Assessed by**: code-smeller

---

## I1 Findings

### B01: Force-Fix Critical Runtime (originally 3 sites)

| ID | Original Description | File:Line | Current State | Still Valid? |
|----|---------------------|-----------|---------------|-------------|
| DOC-001 | Broken `TieredCacheProvider()` call in cache_invalidate.py | `src/autom8_asana/lambda_handlers/cache_invalidate.py:107` | `TieredCacheProvider(hot_tier=hot_tier)` -- uses proper constructor with hot_tier kwarg | **INVALID** -- already fixed. Constructor receives `hot_tier` argument correctly. |
| SW-001 | Swallowed exception in detection/facade.py:167 | `src/autom8_asana/models/business/detection/facade.py:171` | `except Exception` with `logger.warning(...)` + `exc_info=True` + redundant `pass` at line 180 | **PARTIALLY FIXED** -- exception is now logged (not truly swallowed), but redundant `pass` remains. Minor smell only. |
| SW-002 | Swallowed exception in mutation_invalidator.py:309 | File deleted | `cache/mutation_invalidator.py` backward-compat shim was **deleted**. Logic moved to `cache/integration/mutation_invalidator.py`. | **INVALID** -- file no longer exists. See Scope Adjustments. |

**Validation of SW-002 migration**: The new `cache/integration/mutation_invalidator.py` contains 3 `except Exception` blocks at lines 112, 292, 347 -- all with `BROAD-CATCH` annotations and proper logging. No swallowed exceptions.

**B01 Summary**: 0 of 3 original sites remain actionable. DOC-001 was fixed. SW-001 is now logged (minor `pass` cleanup). SW-002 file deleted.

---

### B08: Unused Test Imports (originally 66, estimated ~141)

**Ruff F401 results**: `ruff check tests/ --select F401 --no-fix --config 'lint.per-file-ignores = {}'`

- **Total F401 violations**: 141
- **In `test_reorg_imports.py`** (intentional import-verification test): 34
- **Actionable violations**: 107

**Top-10 files by unused import count (excluding test_reorg_imports.py)**:

| # | File | Count |
|---|------|-------|
| 1 | `tests/unit/persistence/test_holder_ensurer.py` | 14 |
| 2 | `tests/integration/test_lifecycle_smoke.py` | 7 |
| 3 | `tests/unit/dataframes/test_cache_integration.py` | 5 |
| 4 | `tests/unit/automation/workflows/test_conversation_audit.py` | 5 |
| 5 | `tests/unit/persistence/test_action_batch_adversarial.py` | 4 |
| 6 | `tests/unit/core/test_retry.py` | 4 |
| 7 | `tests/unit/lifecycle/test_config.py` | 3 |
| 8 | `tests/unit/dataframes/test_freshness.py` | 3 |
| 9 | `tests/unit/clients/data/test_export.py` | 3 |
| 10 | `tests/unit/api/routes/test_adapter_contracts.py` | 3 |

**Notable patterns**:
- `test_holder_ensurer.py` (14 unused) likely had a large refactor leaving behind stale imports
- Several test files import `asyncio` without using it (likely removed async test functions)
- Multiple files import `typing.Any` unnecessarily
- Some tests import model classes that were moved during cache reorg

**Auto-fixable**: 140 of 141 are auto-fixable with `--fix`. The 1 non-fixable needs manual review.

---

### B09: Swallowed Exceptions (originally 13 sites)

Swallowed = `except` block with only `pass` or `continue` and no logging. Excluding intentional patterns (ImportError for optional deps, RuntimeError for event-loop checks, CancelledError for async cancellation).

| # | File:Line | Except Type | Body | Intentional? | Overlaps I4-S1? |
|---|-----------|-------------|------|-------------|-----------------|
| 1 | `src/autom8_asana/cache/dataframe/tiers/progressive.py:178` | `Exception` | `pass` | Tagged BROAD-CATCH: graceful degradation for metadata | Yes |
| 2 | `src/autom8_asana/models/business/matching/normalizers.py:75` | `Exception` | `pass` | Tagged BROAD-CATCH: vendor-polymorphic phonenumbers parsing | Yes |
| 3 | `src/autom8_asana/resolution/write_registry.py:98` | `Exception` | `continue` | No annotation, no logging -- getattr() on model class | Yes |
| 4 | `src/autom8_asana/api/routes/resolver.py:412` | `Exception` | `pass` | Tagged BROAD-CATCH: non-critical metadata | Yes |
| 5 | `src/autom8_asana/automation/workflows/conversation_audit.py:117` | `Exception` | `pass` | Comment: "Non-circuit-breaker errors are not pre-flight failures" | Yes |
| 6 | `src/autom8_asana/automation/workflows/insights_export.py:140` | `Exception` | `pass` | Comment: "Non-circuit-breaker errors are not pre-flight failures" | Yes |
| 7 | `src/autom8_asana/cache/dataframe/tiers/memory.py:38` | `ValueError` | `pass` | Parsing numeric string -- narrowly typed | No |
| 8 | `src/autom8_asana/cache/models/versioning.py:148` | `ValueError` | `pass` | Version parsing -- narrowly typed | No |
| 9 | `src/autom8_asana/cache/models/versioning.py:164` | `ValueError` | `continue` | Version parsing -- narrowly typed | No |
| 10 | `src/autom8_asana/cache/models/entry.py:283` | `ValueError` | `continue` | Datetime parsing -- narrowly typed | No |
| 11 | `src/autom8_asana/dataframes/extractors/base.py:587` | `ValueError` | `continue` | Datetime parsing -- narrowly typed | No |
| 12 | `src/autom8_asana/dataframes/extractors/base.py:610` | `ValueError` | `continue` | Datetime parsing -- narrowly typed | No |
| 13 | `src/autom8_asana/dataframes/resolver/default.py:329` | `ValueError` | `pass` | Enum/value parsing -- narrowly typed | No |
| 14 | `src/autom8_asana/dataframes/resolver/default.py:338` | `ValueError` | `pass` | Enum/value parsing -- narrowly typed | No |
| 15 | `src/autom8_asana/exceptions.py:161` | `ValueError` | `pass` | Status code parsing -- narrowly typed | No |
| 16 | `src/autom8_asana/transport/response_handler.py:190` | `ValueError` | `pass` | JSON numeric parsing -- narrowly typed | No |
| 17 | `src/autom8_asana/transport/response_handler.py:208` | `JSONDecodeError, KeyError, UnicodeDecodeError` | `pass` | Response body parsing -- narrowly typed | No |
| 18 | `src/autom8_asana/observability/decorators.py:107` | `AttributeError, TypeError` | `pass` | Safe attribute access -- narrowly typed | No |
| 19 | `src/autom8_asana/resolution/strategies.py:278` | `ValueError, ValidationError` | `pass` | Model validation -- narrowly typed | No |

**B09 Summary**: 19 total swallowed exception sites found (vs original estimate of 13). However:
- 6 use `except Exception` (items 1-6 -- overlap with I4-S1)
- 13 use narrowly-typed exceptions (ValueError, JSONDecodeError, etc.) -- these are **intentional** narrow-catch patterns, not B09 targets
- Of the 6 `except Exception` sites: 4 have BROAD-CATCH annotations, 1 has a comment, 1 (`write_registry.py:98`) has no annotation and no logging

**Actionable B09 items**: 3 sites that should add logging or be narrowed:
1. `resolution/write_registry.py:98` -- `except Exception: continue` with no logging
2. `conversation_audit.py:117` -- `except Exception: pass` with only inline comment
3. `insights_export.py:140` -- `except Exception: pass` with only inline comment

---

### B10: Logging Inconsistency (originally 4 modules)

Search for `import logging` or `from logging import` in `src/autom8_asana/`:

| # | Module | Usage | Assessment |
|---|--------|-------|------------|
| 1 | `src/autom8_asana/_defaults/log.py` | `import logging` -- wraps stdlib logging as `DefaultLogProvider` | **INTENTIONAL** -- this IS the fallback logging provider for when autom8y_log is unavailable. It wraps stdlib by design. |
| 2 | `src/autom8_asana/automation/polling/structured_logger.py` | `import logging` -- uses stdlib as fallback when structlog unavailable | **INTENTIONAL** -- graceful fallback pattern per module docstring. |

**B10 Summary**: 2 modules use `import logging`, both intentionally as fallback providers. The original finding of "4 modules" is now **0 actionable** -- either the other 2 were cleaned up or the count was incorrect.

No modules in `src/autom8_asana/` use stdlib logging where they should use `autom8y_log`.

---

### B11: Magic Numbers (originally 5 sites)

Hardcoded numeric TTL/timeout values in `src/autom8_asana/clients/`:

| # | File:Line | Value | Context | Assessment |
|---|-----------|-------|---------|------------|
| 1 | `src/autom8_asana/clients/projects.py:117` | `ttl=900` | 15-min project cache TTL | **MAGIC NUMBER** -- no named constant, not settings-driven |
| 2 | `src/autom8_asana/clients/sections.py:130` | `ttl=1800` | 30-min section cache TTL | **MAGIC NUMBER** -- constant `SECTION_CACHE_TTL` exists at line 27 but is NOT used here |
| 3 | `src/autom8_asana/clients/sections.py:365` | `ttl=1800` | 30-min section cache TTL in batch population | **MAGIC NUMBER** -- same as above, `SECTION_CACHE_TTL` not used |
| 4 | `src/autom8_asana/clients/data/config.py:254` | `cache_ttl: int = 300` | 5-min default for data service | **ACCEPTABLE** -- dataclass field default, documented in docstring |
| 5 | `src/autom8_asana/clients/data/config.py:303` | `cache_ttl = 300` | Fallback on invalid env var | **ACCEPTABLE** -- mirrors the dataclass default above, used in error path |

**B11 Summary**: 3 actionable magic number sites (items 1-3). Items 2-3 are notable because the constant `SECTION_CACHE_TTL = get_settings().cache.ttl_section` is already defined but not used at the actual cache-set callsites.

---

### B12: Missing SDK Docstrings (originally 12 methods)

**Current state of `src/autom8_asana/clients/sections.py`**: All 7 public method implementations and all 12 type overload stubs have docstrings.

| Method | Docstring? |
|--------|-----------|
| `get` (4 overloads + impl) | Yes (all 5) |
| `create` (4 overloads + impl) | Yes (all 5) |
| `update` (4 overloads + impl) | Yes (all 5) |
| `delete` | Yes |
| `list_for_project_async` | Yes |
| `add_task` | Yes |
| `insert_section` | Yes |

**B12 Summary**: **0 missing docstrings**. All 19 methods/overloads have docstrings. This finding was already remediated.

---

## I4-S1 Findings

### Classification Summary

| Classification | Count |
|---|---|
| MECHANICAL | 30 |
| BOUNDARY | 60 |
| COMPLEX | 56 |
| **Total** | **146** |

Note: 146 actual catch sites (148 grep matches minus 2 docstring/comment lines at `lifecycle/engine.py:12` and `lifecycle/reopen.py:12`).

---

### BOUNDARY Sites (stay as except Exception -- 60 sites)

These have `BROAD-CATCH` annotations with clear justification. They serve as intentional degradation boundaries, loop isolation guards, or API-to-error-model wrappers.

| # | File:Line | BROAD-CATCH Tag | Reason to Keep Broad |
|---|-----------|-----------------|---------------------|
| 1 | `_defaults/auth.py:244` | boundary | Wraps diverse boto3 errors into AuthenticationError |
| 2 | `api/lifespan.py:84` | startup | Entity resolver discovery -- must not crash startup |
| 3 | `api/lifespan.py:124` | degrade | Write registry init -- graceful degradation |
| 4 | `api/lifespan.py:168` | degrade | Cache warming cancel -- cleanup path |
| 5 | `api/lifespan.py:179` | degrade | Connection registry shutdown -- cleanup path |
| 6 | `api/preload/legacy.py:381` | isolation | Per-project loop in preload |
| 7 | `api/preload/legacy.py:392` | degrade | Top-level preload function |
| 8 | `api/preload/legacy.py:520` | degrade | Incremental catchup fallback |
| 9 | `api/preload/legacy.py:606` | degrade | Full rebuild fallback |
| 10 | `api/preload/progressive.py:411` | isolation | Per-project loop in progressive preload |
| 11 | `api/preload/progressive.py:474` | degrade | Top-level progressive preload |
| 12 | `api/routes/entity_write.py:280` | boundary | API endpoint boundary (re-raises HTTPException) |
| 13 | `api/routes/resolver.py:365` | boundary | API endpoint boundary (re-raises HTTPException) |
| 14 | `api/routes/internal.py:149` | boundary | API endpoint boundary |
| 15 | `api/startup.py:96` | startup | Mutation invalidator init -- must not crash startup |
| 16 | `automation/engine.py:227` | isolation | Per-rule loop -- single rule failure must not abort batch |
| 17 | `automation/events/emitter.py:104` | isolation | Transport failure must not propagate to commit path |
| 18 | `automation/pipeline.py:482` | isolation | Catch-all for unexpected errors in rule execution |
| 19 | `automation/polling/action_executor.py:181` | isolation | Single action failure returns error result |
| 20 | `automation/polling/cli.py:81` | boundary | CLI entry point |
| 21 | `automation/polling/cli.py:136` | boundary | CLI entry point |
| 22 | `automation/polling/cli.py:216` | boundary | CLI entry point |
| 23 | `automation/polling/polling_scheduler.py:476` | isolation | Per-task loop -- single task must not abort batch |
| 24 | `automation/polling/polling_scheduler.py:561` | isolation | Workflow failure must not abort evaluation cycle |
| 25 | `automation/seeding.py:553` | boundary | Wraps API+accessor+resolution pipeline |
| 26 | `cache/dataframe/decorator.py:235` | boundary | Catch-all converts to HTTPException at API boundary |
| 27 | `cache/integration/dataframe_cache.py:952` | isolation | SWR refresh callback -- must not crash background task |
| 28 | `cache/integration/mutation_invalidator.py:112` | isolation | Background task boundary -- must never propagate |
| 29 | `cache/integration/mutation_invalidator.py:292` | isolation | Per-entry loop with fallback to hard invalidation |
| 30 | `cache/integration/mutation_invalidator.py:347` | isolation | Per-project loop -- single failure must not abort batch |
| 31 | `cache/models/metrics.py:576` | hook | Metrics callbacks must not break cache operations |
| 32 | `core/retry.py:695` | enrichment | Retry loop catches any error to decide retry vs re-raise |
| 33 | `core/retry.py:798` | enrichment | Async retry loop catches any error to decide retry vs re-raise |
| 34 | `lambda_handlers/cache_invalidate.py:184` | boundary | Async function top-level catch |
| 35 | `lambda_handlers/cache_invalidate.py:269` | boundary | Lambda handler top-level catch |
| 36 | `lambda_handlers/cache_warmer.py:208` | isolation | Self-invoke failure must not fail current invocation |
| 37 | `lambda_handlers/cache_warmer.py:554` | isolation | Per-entity-type loop -- single failure must not abort batch |
| 38 | `lambda_handlers/cache_warmer.py:626` | boundary | Async function top-level catch |
| 39 | `lambda_handlers/cache_warmer.py:730` | boundary | Lambda handler top-level catch |
| 40 | `lambda_handlers/checkpoint.py:229` | catch-all-and-degrade | S3 errors should not block warming |
| 41 | `lambda_handlers/checkpoint.py:296` | isolation | Checkpoint save failure returns False |
| 42 | `lambda_handlers/checkpoint.py:329` | isolation | Checkpoint clear failure returns False, expires naturally |
| 43 | `lambda_handlers/cloudwatch.py:73` | metrics | CloudWatch metric emission must not fail the handler |
| 44 | `lifecycle/engine.py:380` | boundary | Orchestrator-level boundary guard |
| 45 | `lifecycle/engine.py:464` | fail-forward | Cascade sections phase |
| 46 | `lifecycle/engine.py:477` | fail-forward | Auto-completion phase |
| 47 | `lifecycle/engine.py:513` | fail-forward | Init actions phase |
| 48 | `lifecycle/engine.py:534` | fail-forward | Dependency wiring phase |
| 49 | `lifecycle/engine.py:586` | fail-forward | Reopen phase |
| 50 | `lifecycle/engine.py:658` | fail-forward | Terminal auto-completion |
| 51 | `lifecycle/engine.py:772` | isolation | Per-action isolation |
| 52 | `lifecycle/reopen.py:153` | boundary | Boundary guard for reopen flow |
| 53 | `lifecycle/wiring.py:105` | fail-forward | Per-dependent wiring |
| 54 | `lifecycle/wiring.py:174` | fail-forward | Open plays wiring |
| 55 | `lifecycle/wiring.py:235` | fail-forward | Dependency wiring |
| 56 | `models/business/hydration.py:290` | boundary | Wraps diverse API+model failures into HydrationError |
| 57 | `models/business/hydration.py:330` | boundary | Wraps diverse API+model failures into HydrationError |
| 58 | `models/business/hydration.py:384` | boundary | Wraps diverse traversal failures into HydrationError |
| 59 | `observability/decorators.py:88` | enrichment | Enriches exception with correlation context then re-raises |
| 60 | `persistence/action_executor.py:274` | intentional | ANY batch endpoint failure triggers chunk-level fallback |

---

### COMPLEX Sites (defer to I4-S2 -- 56 sites)

These involve multiple possible exception types, conditional logic (e.g., partial_ok), or wrap complex multi-step operations.

| # | File:Line | Why Complex |
|---|-----------|-------------|
| 1 | `api/preload/legacy.py:213` | Index recovery: S3 + polars + JSON deserialization errors |
| 2 | `api/preload/progressive.py:57` | Lambda invocation: boto3 + JSON errors |
| 3 | `api/routes/admin.py:142` | Cache invalidation: CACHE_TRANSIENT_ERRORS + potential schema errors |
| 4 | `api/routes/admin.py:169` | S3 purge: S3_TRANSPORT_ERRORS + path construction errors |
| 5 | `api/routes/admin.py:179` | Per-entity refresh: multi-step (invalidate + purge + rebuild) |
| 6 | `api/routes/admin.py:267` | Cache invalidation (variant 2) |
| 7 | `api/routes/admin.py:317` | Per-entity refresh (variant 2) |
| 8 | `api/routes/admin.py:365` | Lambda invocation: boto3 errors |
| 9 | `api/routes/health.py:219` | JWKS health check: HTTP + crypto errors |
| 10 | `api/routes/resolver.py:113` | Entity discovery: registry + import errors |
| 11 | `api/routes/resolver.py:127` | Entity registry check: runtime errors |
| 12 | `api/routes/webhooks.py:238` | Cache invalidation in webhook path |
| 13 | `api/routes/webhooks.py:275` | Dispatch in webhook path |
| 14 | `api/routes/webhooks.py:361` | Pydantic model_validate: ValidationError + diverse pydantic errors |
| 15 | `automation/workflows/conversation_audit.py:334` | Activity resolution: API + data access errors |
| 16 | `automation/workflows/conversation_audit.py:467` | Holder processing: multi-step workflow |
| 17 | `automation/workflows/insights_export.py:278` | Section resolution: API + resolution errors |
| 18 | `automation/workflows/insights_export.py:534` | Offer processing: multi-step workflow |
| 19 | `automation/workflows/insights_export.py:813` | Data fetch: HTTP + parsing + circuit breaker |
| 20 | `automation/workflows/mixins.py:69` | Attachment deletion: API errors |
| 21 | `automation/workflows/pipeline_transition.py:253` | Section resolution fallback |
| 22 | `automation/workflows/pipeline_transition.py:319` | Enumeration error: API + data access |
| 23 | `automation/workflows/pipeline_transition.py:371` | Top-level transition error: multi-step |
| 24 | `cache/dataframe/tiers/progressive.py:144` | vendor-polymorphic: load_dataframe may raise diverse errors (polars, parquet, S3) |
| 25 | `cache/policies/coalescer.py:208` | Batch execution: diverse cache backend errors + future resolution |
| 26 | `dataframes/builders/freshness.py:218` | api-boundary: Asana API diverse HTTP errors |
| 27 | `dataframes/builders/freshness.py:347` | api-boundary: individual task fetch via Asana API |
| 28 | `dataframes/builders/progressive.py:311` | Freshness probe: multi-step API + parsing |
| 29 | `dataframes/builders/progressive.py:659` | Section fetch: API + data processing |
| 30 | `dataframes/builders/progressive.py:748` | Section fetch variant: API + data processing |
| 31 | `dataframes/builders/progressive.py:797` | Checkpoint resume: S3 + JSON |
| 32 | `dataframes/builders/progressive.py:1133` | Store populate: cache + data transformation |
| 33 | `dataframes/builders/progressive.py:1154` | Index build: data transformation + serialization |
| 34 | `dataframes/section_persistence.py:400` | vendor-polymorphic: manifest parsing |
| 35 | `dataframes/section_persistence.py:665` | vendor-polymorphic: sections merge |
| 36 | `lambda_handlers/workflow_handler.py:85` | Workflow execution: diverse errors from full pipeline |
| 37 | `lifecycle/completion.py:87` | Auto-complete: API + session errors |
| 38 | `lifecycle/creation.py:399` | Set due date: API errors |
| 39 | `lifecycle/creation.py:460` | Hierarchy placement: API + session errors |
| 40 | `lifecycle/creation.py:572` | Section placement: API + resolution errors |
| 41 | `lifecycle/creation.py:733` | Set assignee: API errors |
| 42 | `lifecycle/init_actions.py:111` | Comment creation: API errors |
| 43 | `lifecycle/init_actions.py:274` | Play creation: API + model errors |
| 44 | `lifecycle/init_actions.py:345` | Play reopen: API + state errors |
| 45 | `lifecycle/init_actions.py:405` | Entity creation: API + model errors |
| 46 | `lifecycle/init_actions.py:510` | Products check: API + condition evaluation errors |
| 47 | `lifecycle/init_actions.py:554` | Campaign action: diverse action-type errors |
| 48 | `lifecycle/sections.py:128` | Section cascade: API + resolution errors |
| 49 | `models/business/asset_edit.py:490` | Per-strategy loop: diverse strategy errors |
| 50 | `models/business/business.py:226` | catch-all-and-degrade: partial_ok conditional |
| 51 | `models/business/hydration.py:348` | catch-all-and-degrade: partial_ok conditional |
| 52 | `models/business/hydration.py:399` | catch-all-and-degrade: partial_ok conditional |
| 53 | `models/business/mixins.py:179` | catch-all-and-degrade: partial_ok conditional |
| 54 | `models/business/seeder.py:390` | catch-all-and-degrade: composite matching (search+blocking+scoring) |
| 55 | `models/business/seeder.py:495` | catch-all-and-degrade: search API + assertion + data access |
| 56 | `models/business/seeder.py:540` | catch-all-and-degrade: search API + assertion can raise diverse errors |

---

### MECHANICAL Sites (ready for narrowing -- 30 sites)

These have clear exception types inferable from the try-block operation.

| ID | File:Line | Current Catch | Recommended Type | Try-Block Operation | Test Mock Risk |
|----|-----------|---------------|-----------------|---------------------|----------------|
| M01 | `services/field_write_service.py:353` | `except Exception:` | `CACHE_TRANSIENT_ERRORS` | `invalidator.invalidate_async(event)` -- cache invalidation | LOW: test likely mocks invalidator |
| M02 | `services/universal_strategy.py:256` | `except Exception as e:` | `CACHE_TRANSIENT_ERRORS + (RuntimeError,)` | Index build via cache+registry | MEDIUM: check test mocks for get_instance() |
| M03 | `services/universal_strategy.py:648` | `except Exception:` | `(KeyError, RuntimeError)` | `registry.get_schema(schema_key)` -- registry lookup | LOW: get_schema raises KeyError or RuntimeError |
| M04 | `persistence/cache_invalidator.py:147` | `except Exception as exc:` | `CACHE_TRANSIENT_ERRORS` | Cache delete operations (per-gid loop) | LOW: cache mock likely uses ConnectionError |
| M05 | `persistence/cache_invalidator.py:184` | `except Exception as exc:` | `CACHE_TRANSIENT_ERRORS` | Cache + dataframe invalidation (per-gid loop) | LOW: same as M04 |
| M06 | `persistence/cascade.py:181` | `except Exception as e:` | `(ConnectionError, TimeoutError, OSError, RuntimeError)` | Entity update in per-entity loop | MEDIUM: check test side_effect types |
| M07 | `persistence/healing.py:245` | `except Exception as e:` | `(ConnectionError, TimeoutError, OSError, RuntimeError)` | Per-entity healing loop | MEDIUM: check test side_effect types |
| M08 | `persistence/holder_ensurer.py:223` | `except Exception:` | `(ConnectionError, TimeoutError, OSError, RuntimeError)` | `detect_existing_holders()` -- API call | MEDIUM: test uses side_effect=Exception |
| M09 | `persistence/action_executor.py:327` | `except Exception as e:` | `(ConnectionError, TimeoutError, OSError, RuntimeError, ValueError)` | Single action execution | MEDIUM: diverse action types |
| M10 | `persistence/session.py:1029` | `except Exception as e:` | `(ConnectionError, TimeoutError, OSError, RuntimeError)` | Automation execution in commit path | LOW: already has BROAD-CATCH annotation |
| M11 | `models/business/detection/facade.py:112` | `except Exception:` | `CACHE_TRANSIENT_ERRORS` | Cache lookup (cache_get) | LOW: cache mock |
| M12 | `models/business/detection/facade.py:171` | `except Exception:` | `CACHE_TRANSIENT_ERRORS` | Cache store (cache.set) | LOW: cache mock |
| M13 | `models/business/detection/facade.py:215` | `except Exception:` | `(ValidationError, KeyError, AttributeError)` | Pydantic model_validate + attribute access | LOW: narrowly typed |
| M14 | `models/business/matching/normalizers.py:75` | `except Exception:` | `(ValueError, TypeError)` | phonenumbers.parse() -- documented vendor errors | LOW: no test mocks |
| M15 | `models/business/resolution.py:217` | `except Exception as e:` | `(ConnectionError, TimeoutError, OSError, RuntimeError)` | Per-entity resolve_unit_async | MEDIUM: check test side_effect |
| M16 | `models/business/resolution.py:290` | `except Exception as e:` | `(ConnectionError, TimeoutError, OSError, RuntimeError)` | Per-entity resolve_offer_async | MEDIUM: check test side_effect |
| M17 | `resolution/write_registry.py:98` | `except Exception:` | `(AttributeError, TypeError)` | `getattr(model_class, attr_name)` | LOW: purely attribute access |
| M18 | `cache/dataframe/tiers/progressive.py:178` | `except Exception:` | `(json.JSONDecodeError, KeyError, UnicodeDecodeError)` | JSON loads + dict access for watermark metadata | LOW: parsing only |
| M19 | `cache/dataframe/tiers/progressive.py:288` | `except Exception:` | `CACHE_TRANSIENT_ERRORS` | `storage.load_dataframe()` -- S3/cache load | LOW: narrowly typed |
| M20 | `api/routes/resolver.py:412` | `except Exception:` | `(KeyError, AttributeError, RuntimeError)` | Schema lookup for metadata | LOW: registry access |
| M21 | `api/routes/webhooks.py:316` | `except Exception:` | `(json.JSONDecodeError, ValueError, UnicodeDecodeError)` | `request.json()` -- body parsing | LOW: well-known types |
| M22 | `automation/workflows/conversation_audit.py:117` | `except Exception:` | `(ConnectionError, TimeoutError, OSError)` | `_circuit_breaker.check()` -- CB probe | LOW: network only |
| M23 | `automation/workflows/insights_export.py:140` | `except Exception:` | `(ConnectionError, TimeoutError, OSError)` | `_circuit_breaker.check()` -- CB probe | LOW: network only |
| M24 | `automation/workflows/pipeline_transition.py:107` | `except Exception as e:` | `(KeyError, ValueError, AttributeError)` | Config validation: dict access + type checks | LOW: data access only |
| M25 | `models/business/seeder.py:583` | `except Exception as e:` | `(ConnectionError, TimeoutError, OSError, RuntimeError)` | Search by name: search API + assertion | MEDIUM: API mock |
| M26 | `services/universal_strategy.py:464` | `except Exception as e:` | `(KeyError, AttributeError, TypeError)` | Enrichment extraction: dict/attr access | LOW: data access |
| M27 | `services/universal_strategy.py:523` | `except Exception as e:` | `CACHE_TRANSIENT_ERRORS` | Dataframe cache fetch | LOW: cache operation |
| M28 | `services/universal_strategy.py:623` | `except Exception as e:` | `CACHE_TRANSIENT_ERRORS + (RuntimeError, ValueError)` | Entity dataframe build | MEDIUM: multi-step |
| M29 | `api/routes/webhooks.py:238` | `except Exception:` | `CACHE_TRANSIENT_ERRORS` | Cache invalidation in webhook path | LOW: cache operation |
| M30 | `api/routes/webhooks.py:275` | `except Exception:` | `(ConnectionError, TimeoutError, OSError, RuntimeError)` | Dispatch: event dispatcher call | MEDIUM: dispatcher mock |

---

## Overlap Analysis

Items appearing in both I1 (B09) and I4-S1:

| B09 Item | I4-S1 ID | File:Line | Resolution |
|----------|----------|-----------|------------|
| B09-1 | (BOUNDARY) | `cache/dataframe/tiers/progressive.py:178` | I4-S1 M18: Narrow to JSON/Key errors |
| B09-2 | (BOUNDARY) | `models/business/matching/normalizers.py:75` | I4-S1 M14: Narrow to ValueError, TypeError |
| B09-3 | (MECHANICAL) | `resolution/write_registry.py:98` | I4-S1 M17: Narrow to AttributeError, TypeError |
| B09-4 | (BOUNDARY) | `api/routes/resolver.py:412` | I4-S1 M20: Narrow to KeyError, AttributeError, RuntimeError |
| B09-5 | (MECHANICAL) | `conversation_audit.py:117` | I4-S1 M22: Narrow to ConnectionError, TimeoutError, OSError |
| B09-6 | (MECHANICAL) | `insights_export.py:140` | I4-S1 M23: Narrow to ConnectionError, TimeoutError, OSError |

**Recommendation**: Resolve these 6 items via I4-S1 exception narrowing. When narrowed, the B09 swallowed-exception concern is addressed simultaneously.

---

## Scope Adjustments

### Items from roadmap that are now INVALID

| Original ID | Description | Reason |
|-------------|-------------|--------|
| SW-002 | Swallowed exception in mutation_invalidator.py:309 | File `cache/mutation_invalidator.py` (backward-compat shim) **deleted**. Logic at `cache/integration/mutation_invalidator.py` has proper logging. |
| DOC-001 | Broken TieredCacheProvider() call | Already fixed -- uses `TieredCacheProvider(hot_tier=hot_tier)` correctly. |
| B12 (all 12) | Missing docstrings in clients/sections.py | All public methods now have docstrings -- previously remediated. |
| B10 (2 of 4) | Modules using stdlib logging | Only 2 found (both intentional fallback providers). Original "4 modules" count was wrong or already fixed. |

### Backward-compat shims confirmed deleted

All 4 shims verified deleted:
- `src/autom8_asana/cache/mutation_invalidator.py` -- DELETED
- `src/autom8_asana/cache/factory.py` -- DELETED
- `src/autom8_asana/cache/schema_providers.py` -- DELETED
- `src/autom8_asana/cache/tiered.py` -- DELETED

Any prior findings referencing these files are invalidated.

### api/main.py status

- Now 197 lines (down from much larger)
- Only 1 `except ImportError` (intentional optional import)
- 0 `except Exception` sites -- all original bare-except sites migrated to route files or eliminated

---

## Risk Flags

### 1. Test Mock Side-Effect Risk (HIGH)

12 of the 30 MECHANICAL sites are rated MEDIUM for test mock risk. When narrowing `except Exception` to specific types, tests using `side_effect = Exception(...)` will break. **Before narrowing each MECHANICAL site, the janitor MUST check corresponding test files and update mock side_effects to use the new exception type** (typically `ConnectionError` as a safe builtin replacement).

### 2. Unannotated Catch Sites (MEDIUM)

30 of 146 catch sites lack `BROAD-CATCH` annotations. While not a functional issue, this makes future audit harder. The unannotated sites are concentrated in:
- `lifecycle/init_actions.py` (6 sites)
- `api/routes/webhooks.py` (4 sites)
- `automation/workflows/` (12 sites across 4 files)

### 3. Redundant `pass` After Logging (LOW)

`detection/facade.py:180` has a redundant `pass` after `logger.warning(...)` + `exc_info=True`. Not harmful but noisy.

### 4. Unused Constant Not Used at Callsites (LOW)

`clients/sections.py:27` defines `SECTION_CACHE_TTL = get_settings().cache.ttl_section` but both cache-set callsites (lines 130, 365) use hardcoded `ttl=1800` instead. This means the settings-driven TTL is defined but not applied.

---

## Attestation

| Artifact | Path | Verified via Read? |
|----------|------|-------------------|
| Smell Report | `/Users/tomtenuta/Code/autom8_asana/docs/hygiene/SMELL-wave1-i1-i4s1.md` | Written by code-smeller |
| cache_invalidate.py (DOC-001) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_invalidate.py:107` | Read, verified constructor call |
| detection/facade.py (SW-001) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/detection/facade.py:171` | Read, verified logging present |
| mutation_invalidator.py (SW-002) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/mutation_invalidator.py` | Verified deleted via ls |
| sections.py (B11, B12) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | Read full file, verified docstrings and magic numbers |
| projects.py (B11) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/projects.py:117` | Read, verified hardcoded TTL |
| All 146 except Exception sites | `src/autom8_asana/` | grep + contextual Read for each classification |
| Backward-compat shims (4 files) | `src/autom8_asana/cache/` | ls verified all 4 deleted |
| api/main.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | Verified 197 lines, 0 except Exception |
| core/exceptions.py error tuples | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/exceptions.py:274-321` | Read, verified CACHE_TRANSIENT_ERRORS, S3_TRANSPORT_ERRORS, ALL_TRANSPORT_ERRORS |
