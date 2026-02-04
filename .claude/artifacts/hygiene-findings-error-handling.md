# HYG-003: Error Handling & Exception Pattern Scan

**Scan Date**: 2026-02-04
**Scope**: `src/autom8_asana/` (all `.py` files)
**Agent**: code-smeller (HYG-003)
**Total Findings**: 134

---

## Summary

| Category | Critical | Moderate | Minor | Total |
|----------|----------|----------|-------|-------|
| bare-except | 10 | 89 | 7 | 106 |
| swallowed-exception | 2 | 9 | 4 | 15 |
| unused-exception-type | 0 | 5 | 1 | 6 |
| exception-misuse | 0 | 2 | 1 | 3 |
| cancelled-error-catch | 0 | 2 | 0 | 2 |
| broad-try | 0 | 1 | 0 | 1 |
| inconsistent-handling | 0 | 1 | 0 | 1 |
| **Total** | **12** | **109** | **13** | **134** |

---

## Findings

### Category: bare-except (except Exception)

All `except Exception` sites. 106 total across the codebase. Grouped by module for readability.

#### api/main.py (11 sites)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-001 | `src/autom8_asana/api/main.py` | 167 | moderate | `except Exception as exc` on mutation_invalidator init; logs and swallows -- intentional graceful degradation but should catch specific init errors |
| BE-002 | `src/autom8_asana/api/main.py` | 229 | moderate | `except Exception as e` on client_registry init |
| BE-003 | `src/autom8_asana/api/main.py` | 290 | minor | `except Exception as e` on cache warming cancel error -- follows correct CancelledError pattern above it |
| BE-004 | `src/autom8_asana/api/main.py` | 487 | moderate | `except Exception as e` on index recovery during preload |
| BE-005 | `src/autom8_asana/api/main.py` | 653 | moderate | `except Exception as e` on per-project preload failure |
| BE-006 | `src/autom8_asana/api/main.py` | 664 | moderate | `except Exception as e` outer catch on entire preload -- broad scope |
| BE-007 | `src/autom8_asana/api/main.py` | 788 | moderate | `except Exception as e` on incremental_catchup failure; returns existing state unchanged |
| BE-008 | `src/autom8_asana/api/main.py` | 874 | moderate | `except Exception as e` on full_rebuild failure; returns None |
| BE-009 | `src/autom8_asana/api/main.py` | 928 | moderate | `except Exception as e` on Lambda invoke failure |
| BE-010 | `src/autom8_asana/api/main.py` | 1242 | moderate | `except Exception as e` nested in progressive preload loop |
| BE-011 | `src/autom8_asana/api/main.py` | 1305 | moderate | `except Exception as e` outer catch on progressive preload |

#### api/routes/admin.py (6 sites)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-012 | `src/autom8_asana/api/routes/admin.py` | 142 | moderate | `except Exception as e` on cache warm per-entity failure |
| BE-013 | `src/autom8_asana/api/routes/admin.py` | 165 | moderate | `except Exception as e` on cache warm failure |
| BE-014 | `src/autom8_asana/api/routes/admin.py` | 175 | moderate | `except Exception as e` on cache warm outer catch |
| BE-015 | `src/autom8_asana/api/routes/admin.py` | 263 | moderate | `except Exception as e` on cache invalidation failure |
| BE-016 | `src/autom8_asana/api/routes/admin.py` | 313 | moderate | `except Exception as e` on staleness coordinator failure |
| BE-017 | `src/autom8_asana/api/routes/admin.py` | 361 | moderate | `except Exception as e` on hierarchy warmer failure |

#### api/routes/ (other)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-018 | `src/autom8_asana/api/routes/internal.py` | 147 | moderate | `except Exception as e` |
| BE-019 | `src/autom8_asana/api/routes/health.py` | 219 | minor | `except Exception` on JWKS health check -- acceptable for health probes |
| BE-020 | `src/autom8_asana/api/routes/resolver.py` | 275 | moderate | `except Exception as e` |
| BE-021 | `src/autom8_asana/api/routes/resolver.py` | 289 | moderate | `except Exception as e` |
| BE-022 | `src/autom8_asana/api/routes/resolver.py` | 527 | moderate | `except Exception as e` |

#### services/universal_strategy.py (6 sites)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-023 | `src/autom8_asana/services/universal_strategy.py` | 179 | moderate | `except Exception as e` on resolution lookup; logs and continues |
| BE-024 | `src/autom8_asana/services/universal_strategy.py` | 362 | moderate | `except Exception as e` on enrichment extraction |
| BE-025 | `src/autom8_asana/services/universal_strategy.py` | 418 | moderate | `except Exception as e` on dataframe cache fetch |
| BE-026 | `src/autom8_asana/services/universal_strategy.py` | 449 | moderate | `except Exception as e` on legacy strategy build |
| BE-027 | `src/autom8_asana/services/universal_strategy.py` | 547 | moderate | `except Exception as e` on final fallback |
| BE-028 | `src/autom8_asana/services/universal_strategy.py` | 572 | moderate | `except Exception` bare -- no error variable captured; falls back to base schema |

#### clients/data/client.py (7 sites)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-029 | `src/autom8_asana/clients/data/client.py` | 394 | moderate | `except Exception as e` on auth token retrieval |
| BE-030 | `src/autom8_asana/clients/data/client.py` | 527 | moderate | `except Exception as e` on metrics emission |
| BE-031 | `src/autom8_asana/clients/data/client.py` | 586 | moderate | `except Exception as e` |
| BE-032 | `src/autom8_asana/clients/data/client.py` | 671 | moderate | `except Exception as e` |
| BE-033 | `src/autom8_asana/clients/data/client.py` | 1392 | moderate | `except Exception` on body parsing; swallows silently |
| BE-034 | `src/autom8_asana/clients/data/client.py` | 1500 | moderate | `except Exception as e` |
| BE-035 | `src/autom8_asana/clients/data/client.py` | 1546 | moderate | `except Exception as e` |

#### lambda_handlers/cache_warmer.py (6 sites)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-036 | `src/autom8_asana/lambda_handlers/cache_warmer.py` | 235 | moderate | `except Exception as e` on CloudWatch metric emit |
| BE-037 | `src/autom8_asana/lambda_handlers/cache_warmer.py` | 294 | moderate | `except Exception as e` |
| BE-038 | `src/autom8_asana/lambda_handlers/cache_warmer.py` | 372 | moderate | `except Exception as e` |
| BE-039 | `src/autom8_asana/lambda_handlers/cache_warmer.py` | 634 | moderate | `except Exception as e` |
| BE-040 | `src/autom8_asana/lambda_handlers/cache_warmer.py` | 706 | critical | `except Exception as e` at Lambda handler top-level; should be the final catch-all but logs only |
| BE-041 | `src/autom8_asana/lambda_handlers/cache_warmer.py` | 810 | critical | `except Exception as e` at Lambda handler top-level |

#### lambda_handlers/cache_invalidate.py (2 sites)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-042 | `src/autom8_asana/lambda_handlers/cache_invalidate.py` | 153 | critical | `except Exception as e` at handler boundary |
| BE-043 | `src/autom8_asana/lambda_handlers/cache_invalidate.py` | 236 | critical | `except Exception as e` at handler boundary |

#### lambda_handlers/checkpoint.py (3 sites)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-044 | `src/autom8_asana/lambda_handlers/checkpoint.py` | 229 | moderate | `except Exception as e` |
| BE-045 | `src/autom8_asana/lambda_handlers/checkpoint.py` | 296 | moderate | `except Exception as e` |
| BE-046 | `src/autom8_asana/lambda_handlers/checkpoint.py` | 329 | moderate | `except Exception as e` |

#### cache/ subsystem (21 sites)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-047 | `src/autom8_asana/cache/policies/coalescer.py` | 208 | moderate | `except Exception as e` |
| BE-048 | `src/autom8_asana/cache/dataframe/build_coordinator.py` | 345 | moderate | `except Exception as exc` |
| BE-049 | `src/autom8_asana/cache/providers/unified.py` | 286 | moderate | `except Exception as e` |
| BE-050 | `src/autom8_asana/cache/providers/unified.py` | 377 | moderate | `except Exception as e` |
| BE-051 | `src/autom8_asana/cache/providers/unified.py` | 601 | moderate | `except Exception as e` |
| BE-052 | `src/autom8_asana/cache/policies/lightweight_checker.py` | 128 | moderate | `except Exception as e` |
| BE-053 | `src/autom8_asana/cache/dataframe/tiers/progressive.py` | 162 | moderate | `except Exception as e` |
| BE-054 | `src/autom8_asana/cache/dataframe/tiers/progressive.py` | 179 | moderate | `except Exception` on watermark parse; swallows and defaults to now() |
| BE-055 | `src/autom8_asana/cache/dataframe/tiers/progressive.py` | 265 | moderate | `except Exception as e` |
| BE-056 | `src/autom8_asana/cache/integration/upgrader.py` | 144 | moderate | `except Exception as e` |
| BE-057 | `src/autom8_asana/cache/integration/hierarchy_warmer.py` | 94 | moderate | `except Exception as e` |
| BE-058 | `src/autom8_asana/cache/dataframe/warmer.py` | 246 | moderate | `except Exception as e` |
| BE-059 | `src/autom8_asana/cache/dataframe/warmer.py` | 382 | moderate | `except Exception as e` |
| BE-060 | `src/autom8_asana/cache/dataframe/warmer.py` | 473 | moderate | `except Exception as e` |
| BE-061 | `src/autom8_asana/cache/dataframe/decorator.py` | 224 | moderate | `except Exception as e` |
| BE-062 | `src/autom8_asana/cache/integration/dataframe_cache.py` | 910 | moderate | `except Exception` on SWR refresh; logs exception trace |
| BE-063 | `src/autom8_asana/cache/integration/freshness_coordinator.py` | 248 | moderate | `except Exception as e` |
| BE-064 | `src/autom8_asana/cache/integration/freshness_coordinator.py` | 479 | moderate | `except Exception as e` |
| BE-065 | `src/autom8_asana/cache/integration/autom8_adapter.py` | 301 | moderate | `except Exception` counts errors and re-raises |
| BE-066 | `src/autom8_asana/cache/integration/autom8_adapter.py` | 438 | moderate | `except Exception as e` |
| BE-067 | `src/autom8_asana/cache/models/metrics.py` | 572 | minor | `except Exception` on callback error; swallows silently |

#### cache/integration/mutation_invalidator.py (6 sites)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-068 | `src/autom8_asana/cache/integration/mutation_invalidator.py` | 111 | moderate | `except Exception as exc` -- fire-and-forget pattern, acceptable |
| BE-069 | `src/autom8_asana/cache/integration/mutation_invalidator.py` | 195 | moderate | `except Exception as exc` |
| BE-070 | `src/autom8_asana/cache/integration/mutation_invalidator.py` | 241 | moderate | `except Exception as exc` |
| BE-071 | `src/autom8_asana/cache/integration/mutation_invalidator.py` | 297 | moderate | `except Exception as exc` on soft invalidation |
| BE-072 | `src/autom8_asana/cache/integration/mutation_invalidator.py` | 309 | critical | `except Exception` bare -- swallows hard-invalidation fallback failure silently with `pass` |
| BE-073 | `src/autom8_asana/cache/integration/mutation_invalidator.py` | 320 | moderate | `except Exception as exc` |
| BE-074 | `src/autom8_asana/cache/integration/mutation_invalidator.py` | 344 | moderate | `except Exception as exc` |

#### cache/connections/registry.py (3 sites)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-075 | `src/autom8_asana/cache/connections/registry.py` | 85 | moderate | `except Exception as e` on health check |
| BE-076 | `src/autom8_asana/cache/connections/registry.py` | 127 | moderate | `except Exception as e` on close |
| BE-077 | `src/autom8_asana/cache/connections/registry.py` | 144 | moderate | `except Exception as e` on async close |

#### persistence/ (6 sites)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-078 | `src/autom8_asana/persistence/action_executor.py` | 115 | moderate | `except Exception as e` |
| BE-079 | `src/autom8_asana/persistence/cache_invalidator.py` | 147 | moderate | `except Exception as exc` |
| BE-080 | `src/autom8_asana/persistence/cache_invalidator.py` | 184 | moderate | `except Exception as exc` |
| BE-081 | `src/autom8_asana/persistence/cascade.py` | 181 | moderate | `except Exception as e` |
| BE-082 | `src/autom8_asana/persistence/events.py` | 194 | minor | `except Exception` on post-save hook; logs warning -- acceptable hook pattern |
| BE-083 | `src/autom8_asana/persistence/events.py` | 227 | minor | `except Exception` on error hook; logs warning -- acceptable |
| BE-084 | `src/autom8_asana/persistence/events.py` | 290 | minor | `except Exception` on post-commit hook; logs warning -- acceptable |
| BE-085 | `src/autom8_asana/persistence/healing.py` | 245 | moderate | `except Exception as e` |
| BE-086 | `src/autom8_asana/persistence/healing.py` | 369 | moderate | `except Exception as e` |
| BE-087 | `src/autom8_asana/persistence/session.py` | 871 | moderate | `except Exception as e` on automation evaluation; NFR-003 graceful degradation |

#### dataframes/ (12 sites)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-088 | `src/autom8_asana/dataframes/builders/freshness.py` | 218 | moderate | `except Exception as e` -- has BROAD-CATCH comment annotation (api-boundary) |
| BE-089 | `src/autom8_asana/dataframes/builders/freshness.py` | 260 | moderate | `except Exception as e` -- has BROAD-CATCH comment annotation (mixed-boundary) |
| BE-090 | `src/autom8_asana/dataframes/builders/freshness.py` | 345 | moderate | `except Exception as e` -- has BROAD-CATCH comment annotation (api-boundary) |
| BE-091 | `src/autom8_asana/dataframes/watermark.py` | 219 | moderate | `except Exception as e` |
| BE-092 | `src/autom8_asana/dataframes/watermark.py` | 287 | moderate | `except Exception as e` |
| BE-093 | `src/autom8_asana/dataframes/extractors/base.py` | 155 | moderate | `except Exception as e` |
| BE-094 | `src/autom8_asana/dataframes/extractors/base.py` | 191 | moderate | `except Exception as e` |
| BE-095 | `src/autom8_asana/dataframes/builders/progressive.py` | 306 | moderate | `except Exception as e` on freshness probe |
| BE-096 | `src/autom8_asana/dataframes/builders/progressive.py` | 654 | moderate | `except Exception as e` on section fetch |
| BE-097 | `src/autom8_asana/dataframes/builders/progressive.py` | 743 | moderate | `except Exception as e` |
| BE-098 | `src/autom8_asana/dataframes/builders/progressive.py` | 792 | moderate | `except Exception as e` |
| BE-099 | `src/autom8_asana/dataframes/builders/progressive.py` | 1038 | moderate | `except Exception as e` |
| BE-100 | `src/autom8_asana/dataframes/builders/progressive.py` | 1132 | moderate | `except Exception as e` |
| BE-101 | `src/autom8_asana/dataframes/builders/progressive.py` | 1153 | moderate | `except Exception as e` |
| BE-102 | `src/autom8_asana/dataframes/resolver/cascading.py` | 95 | moderate | `except Exception as e` |
| BE-103 | `src/autom8_asana/dataframes/resolver/cascading.py` | 515 | moderate | `except Exception as e` |
| BE-104 | `src/autom8_asana/dataframes/resolver/cascading.py` | 536 | moderate | `except Exception as e` |
| BE-105 | `src/autom8_asana/dataframes/section_persistence.py` | 435 | moderate | `except Exception as e` |
| BE-106 | `src/autom8_asana/dataframes/section_persistence.py` | 659 | moderate | `except Exception as e` |
| BE-107 | `src/autom8_asana/dataframes/section_persistence.py` | 748 | moderate | `except Exception as e` |
| BE-108 | `src/autom8_asana/dataframes/views/dataframe_view.py` | 306 | moderate | `except Exception as e` |

#### automation/ (13 sites)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-109 | `src/autom8_asana/automation/pipeline.py` | 473 | critical | `except Exception as e` wraps entire rule execution (~100 lines); returns AutomationResult with success=False |
| BE-110 | `src/autom8_asana/automation/pipeline.py` | 611 | moderate | `except Exception as e` on process holder fetch |
| BE-111 | `src/autom8_asana/automation/pipeline.py` | 652 | moderate | `except Exception as e` on hierarchy placement |
| BE-112 | `src/autom8_asana/automation/pipeline.py` | 723 | moderate | `except Exception as e` on section move |
| BE-113 | `src/autom8_asana/automation/pipeline.py` | 770 | moderate | `except Exception as e` on due date set |
| BE-114 | `src/autom8_asana/automation/pipeline.py` | 826 | moderate | `except Exception as e` on unit rep access |
| BE-115 | `src/autom8_asana/automation/pipeline.py` | 837 | moderate | `except Exception as e` on business rep access |
| BE-116 | `src/autom8_asana/automation/pipeline.py` | 854 | moderate | `except Exception as e` on assignee API call |
| BE-117 | `src/autom8_asana/automation/pipeline.py` | 907 | moderate | `except Exception as e` |
| BE-118 | `src/autom8_asana/automation/engine.py` | 226 | moderate | `except Exception as e` on single rule evaluation |
| BE-119 | `src/autom8_asana/automation/seeding.py` | 548 | moderate | `except Exception as e` |
| BE-120 | `src/autom8_asana/automation/seeding.py` | 606 | moderate | `except Exception as e` |
| BE-121 | `src/autom8_asana/automation/seeding.py` | 624 | moderate | `except Exception as e` |
| BE-122 | `src/autom8_asana/automation/seeding.py` | 641 | moderate | `except Exception as e` |
| BE-123 | `src/autom8_asana/automation/polling/cli.py` | 82 | moderate | `except Exception as e` |
| BE-124 | `src/autom8_asana/automation/polling/cli.py` | 137 | moderate | `except Exception as e` |
| BE-125 | `src/autom8_asana/automation/polling/cli.py` | 217 | moderate | `except Exception as e` |
| BE-126 | `src/autom8_asana/automation/polling/action_executor.py` | 181 | moderate | `except Exception as exc` |
| BE-127 | `src/autom8_asana/automation/polling/polling_scheduler.py` | 423 | moderate | `except Exception as exc` |

#### models/ (11 sites)

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-128 | `src/autom8_asana/models/business/mixins.py` | 179 | moderate | `except Exception as e` |
| BE-129 | `src/autom8_asana/models/business/asset_edit.py` | 490 | moderate | `except Exception as e` |
| BE-130 | `src/autom8_asana/models/business/seeder.py` | 390 | moderate | `except Exception as e` |
| BE-131 | `src/autom8_asana/models/business/seeder.py` | 496 | moderate | `except Exception as e` |
| BE-132 | `src/autom8_asana/models/business/seeder.py` | 541 | moderate | `except Exception as e` |
| BE-133 | `src/autom8_asana/models/business/seeder.py` | 585 | moderate | `except Exception as e` |
| BE-134 | `src/autom8_asana/models/business/detection/facade.py` | 108 | moderate | `except Exception` swallowed -- returns None |
| BE-135 | `src/autom8_asana/models/business/detection/facade.py` | 167 | critical | `except Exception` swallowed with `pass` -- no logging |
| BE-136 | `src/autom8_asana/models/business/detection/facade.py` | 204 | moderate | `except Exception` returns None |
| BE-137 | `src/autom8_asana/models/business/detection/facade.py` | 509 | moderate | `except Exception as exc` |
| BE-138 | `src/autom8_asana/models/business/detection/facade.py` | 538 | moderate | `except Exception as exc` |
| BE-139 | `src/autom8_asana/models/business/resolution.py` | 149 | moderate | `except Exception as e` |
| BE-140 | `src/autom8_asana/models/business/resolution.py` | 215 | moderate | `except Exception as e` |
| BE-141 | `src/autom8_asana/models/business/resolution.py` | 289 | moderate | `except Exception as e` |
| BE-142 | `src/autom8_asana/models/business/hydration.py` | 290 | moderate | `except Exception as e` |
| BE-143 | `src/autom8_asana/models/business/hydration.py` | 330 | moderate | `except Exception as e` |
| BE-144 | `src/autom8_asana/models/business/hydration.py` | 348 | moderate | `except Exception as e` |
| BE-145 | `src/autom8_asana/models/business/hydration.py` | 384 | moderate | `except Exception as e` |
| BE-146 | `src/autom8_asana/models/business/hydration.py` | 399 | moderate | `except Exception as e` |
| BE-147 | `src/autom8_asana/models/business/business.py` | 225 | moderate | `except Exception as e` |
| BE-148 | `src/autom8_asana/models/business/matching/normalizers.py` | 75 | minor | `except Exception` with `pass` -- phone number parse fallback, acceptable |

#### Other files

| ID | File | Line | Severity | Description |
|----|------|------|----------|-------------|
| BE-149 | `src/autom8_asana/observability/decorators.py` | 88 | moderate | `except Exception as e` in tracing decorator -- catches, enriches, re-raises; acceptable pattern but still broad |
| BE-150 | `src/autom8_asana/client.py` | 891 | moderate | `except Exception` on bulk API call; increments failed counter |
| BE-151 | `src/autom8_asana/core/schema.py` | 32 | moderate | `except Exception as e` |
| BE-152 | `src/autom8_asana/core/retry.py` | 659 | critical | `except Exception as exc` in sync retry loop; catches all errors including `KeyboardInterrupt`-adjacent; see CE-001 |
| BE-153 | `src/autom8_asana/core/retry.py` | 756 | critical | `except Exception as exc` in async retry loop; same concern as BE-152 |
| BE-154 | `src/autom8_asana/clients/sections.py` | 336 | moderate | `except Exception` with `pass` -- silently swallowed |
| BE-155 | `src/autom8_asana/clients/data/models.py` | 268 | moderate | `except Exception` with `pass` -- dtype cast failure silently ignored |
| BE-156 | `src/autom8_asana/_defaults/auth.py` | 243 | moderate | `except Exception as e` |
| BE-157 | `src/autom8_asana/search/service.py` | 215 | moderate | `except Exception as e` |
| BE-158 | `src/autom8_asana/api/dependencies.py` | 185 | moderate | `except Exception as e` |
| BE-159 | `src/autom8_asana/models/custom_field_accessor.py` | 356 | moderate | `except (KeyError, AttributeError, Exception)` -- redundant: Exception already covers KeyError and AttributeError |

---

### Category: swallowed-exception

Exceptions caught and either silently ignored (`pass`) or logged without propagation where the error should potentially propagate.

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| SW-001 | `src/autom8_asana/models/business/detection/facade.py` | 167 | swallowed-exception | critical | `except Exception: pass` -- no logging at all. Cache storage failure silently ignored. Comment says "FR-DEGRADE-002" but at minimum should log |
| SW-002 | `src/autom8_asana/cache/integration/mutation_invalidator.py` | 309 | swallowed-exception | critical | `except Exception: pass` -- hard-invalidation fallback failure completely silenced. If soft AND hard invalidation both fail, there is no trace |
| SW-003 | `src/autom8_asana/cache/models/metrics.py` | 572 | swallowed-exception | moderate | `except Exception: pass` -- callback errors silenced |
| SW-004 | `src/autom8_asana/clients/data/client.py` | 1392 | swallowed-exception | moderate | `except Exception: pass` -- response body parsing failure silenced |
| SW-005 | `src/autom8_asana/clients/sections.py` | 336 | swallowed-exception | moderate | `except Exception: pass` -- per ADR-0127 graceful degradation, but no logging |
| SW-006 | `src/autom8_asana/clients/data/models.py` | 268 | swallowed-exception | moderate | `except Exception: pass` -- dtype cast failure silenced; comment says "log warning" but no logging present |
| SW-007 | `src/autom8_asana/models/business/detection/facade.py` | 108 | swallowed-exception | moderate | `except Exception: return None` -- cache lookup silenced |
| SW-008 | `src/autom8_asana/models/business/detection/facade.py` | 204 | swallowed-exception | moderate | `except Exception: return None` -- no logging |
| SW-009 | `src/autom8_asana/services/universal_strategy.py` | 572 | swallowed-exception | moderate | `except Exception` -- no error variable captured, falls back silently |
| SW-010 | `src/autom8_asana/cache/dataframe/tiers/progressive.py` | 179 | swallowed-exception | moderate | `except Exception` -- watermark parse failure silently defaults to now(); data freshness silently compromised |
| SW-011 | `src/autom8_asana/models/business/matching/normalizers.py` | 75 | swallowed-exception | minor | `except Exception: pass` -- phone number parsing; low impact |
| SW-012 | `src/autom8_asana/cache/integration/dataframe_cache.py` | 910 | swallowed-exception | minor | `except Exception` -- SWR refresh failure; does log via .exception() |
| SW-013 | `src/autom8_asana/client.py` | 891 | swallowed-exception | minor | `except Exception` -- increments counter but doesn't log error details |
| SW-014 | `src/autom8_asana/api/routes/health.py` | 219 | swallowed-exception | minor | `except Exception` -- health check; uses logger.exception() |

---

### Category: unused-exception-type

New exception types defined in the architectural initiative that are NOT actually raised or caught anywhere outside their definition module and tests.

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| UE-001 | `src/autom8_asana/core/exceptions.py` | 245 | unused-exception-type | moderate | `AutomationError` -- defined but never raised or caught anywhere outside `core/exceptions.py`. The `automation/pipeline.py` module catches generic `Exception` instead |
| UE-002 | `src/autom8_asana/core/exceptions.py` | 268 | unused-exception-type | moderate | `RuleExecutionError` -- defined but never raised or caught. `automation/engine.py` catches generic `Exception` at line 226 |
| UE-003 | `src/autom8_asana/core/exceptions.py` | 274 | unused-exception-type | moderate | `SeedingError` -- defined but never raised or caught. `automation/seeding.py` catches generic `Exception` |
| UE-004 | `src/autom8_asana/core/exceptions.py` | 280 | unused-exception-type | moderate | `PipelineActionError` -- defined but never raised or caught. Pipeline action methods catch generic `Exception` |
| UE-005 | `src/autom8_asana/core/exceptions.py` | 222-231 | unused-exception-type | moderate | `CacheReadError` and `CacheWriteError` -- defined and included in `SERIALIZATION_ERRORS` tuple but never raised by any cache backend. Only referenced in the exceptions module itself |
| UE-006 | `src/autom8_asana/services/errors.py` | 210 | unused-exception-type | minor | `ServiceNotConfiguredError` -- defined but only used in the `SERVICE_ERROR_MAP`; never raised by any service. `CacheNotReadyError` is also only imported by `entity_service.py` but that service module is new and may not yet be wired into routes |

---

### Category: exception-misuse

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| EM-001 | `src/autom8_asana/models/custom_field_accessor.py` | 356 | exception-misuse | moderate | `except (KeyError, AttributeError, Exception)` -- redundant catch hierarchy. `Exception` already catches `KeyError` and `AttributeError`. The explicit listing is misleading, suggesting these are the expected errors when actually any exception is caught |
| EM-002 | `src/autom8_asana/core/retry.py` | 364 | exception-misuse | moderate | `CircuitBreakerOpenError(Exception)` duplicates `exceptions.CircuitBreakerOpenError(AsanaError)` at `src/autom8_asana/exceptions.py:202`. Two distinct exception hierarchies exist for the same concept; `clients/data/client.py` imports both with aliasing (`SdkCircuitBreakerOpenError`) |
| EM-003 | `src/autom8_asana/core/exceptions.py` | 194 | exception-misuse | minor | `CacheError(Autom8Error)` with `transient=False` but `CacheConnectionError(CacheError)` overrides to `transient=True`. Semantic hierarchy inversion: a connection error IS a cache error but has opposite transience. This is technically correct by intent but surprising for callers checking `isinstance(err, CacheError)` and assuming permanent |

---

### Category: cancelled-error-catch

In Python 3.12+, `asyncio.CancelledError` inherits from `BaseException`, not `Exception`, so `except Exception` does NOT catch it. These are the async sites where `except Exception` appears in an async context -- they are safe in Python 3.12+ but would break on Python 3.8 where `CancelledError` was an `Exception`.

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| CE-001 | `src/autom8_asana/core/retry.py` | 756 | cancelled-error-catch | moderate | `except Exception as exc` in `execute_with_retry_async` -- safe on 3.12+ but the retry loop will delay `CancelledError` propagation if the operation itself catches and wraps `CancelledError` in a generic Exception before re-raising. The retry loop has no explicit `except asyncio.CancelledError` guard (contrast with `cache/policies/coalescer.py` which does) |
| CE-002 | `src/autom8_asana/cache/dataframe/build_coordinator.py` | 345 | cancelled-error-catch | moderate | `except Exception as exc` in async build context. Unlike `coalescer.py` (lines 135, 160, 261) which explicitly handles `CancelledError`, the build coordinator does not guard against it |

---

### Category: broad-try

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| BT-001 | `src/autom8_asana/automation/pipeline.py` | 473 | broad-try | moderate | Try block at line ~375 wraps approximately 100 lines of rule execution logic (entity matching, action dispatch, hierarchy placement, section moves, due dates, assignees). Only the API calls at the leaf need try/except. The outer catch masks which operation actually failed |

---

### Category: inconsistent-handling

| ID | File | Line | Category | Severity | Description |
|----|------|------|----------|----------|-------------|
| IH-001 | `src/autom8_asana/cache/integration/mutation_invalidator.py` | 297+309 | inconsistent-handling | moderate | Soft invalidation at line 297 catches `Exception` and logs + falls back to hard invalidation. The hard invalidation fallback at line 309 catches `Exception` with bare `pass`. The two layers have inconsistent error visibility -- a double failure is completely silent |

---

## New File Adoption Analysis

### `src/autom8_asana/core/exceptions.py`

**Status**: Partially adopted.

| Type | Imported By | Raised By | Caught By |
|------|------------|-----------|-----------|
| `Autom8Error` | `core/retry.py` | Nobody | Nobody |
| `TransportError` | Nobody (outside module) | Nobody | Nobody |
| `S3TransportError` | `cache/backends/s3.py`, `dataframes/storage.py` | `cache/backends/s3.py`, `dataframes/storage.py` | `dataframes/storage.py` |
| `RedisTransportError` | `cache/backends/redis.py` | `cache/backends/redis.py` | Nobody |
| `CacheError` | Nobody (outside module) | Nobody | Nobody |
| `CacheReadError` | `SERIALIZATION_ERRORS` tuple only | Nobody | Nobody |
| `CacheWriteError` | `SERIALIZATION_ERRORS` tuple only | Nobody | Nobody |
| `CacheConnectionError` | `cache/connections/s3.py`, `redis.py` | `cache/connections/s3.py`, `redis.py` | `cache/connections/s3.py` |
| `AutomationError` | Nobody | Nobody | Nobody |
| `RuleExecutionError` | Nobody | Nobody | Nobody |
| `SeedingError` | Nobody | Nobody | Nobody |
| `PipelineActionError` | Nobody | Nobody | Nobody |
| `S3_TRANSPORT_ERRORS` tuple | 7 modules | n/a | 7 modules |
| `REDIS_TRANSPORT_ERRORS` tuple | 2 modules | n/a | 2 modules |
| `CACHE_TRANSIENT_ERRORS` tuple | 6 modules | n/a | 6 modules |

**Key finding**: The error tuples (`S3_TRANSPORT_ERRORS`, `REDIS_TRANSPORT_ERRORS`, `CACHE_TRANSIENT_ERRORS`) are well-adopted. The individual exception classes for automation (`AutomationError`, `RuleExecutionError`, `SeedingError`, `PipelineActionError`) and semantic cache errors (`CacheReadError`, `CacheWriteError`) are completely unused -- defined but never raised.

### `src/autom8_asana/core/retry.py`

**Status**: Adopted by infrastructure layer.

Imported by: `cache/connections/s3.py`, `cache/connections/redis.py`, `dataframes/storage.py`, `cache/dataframe/factory.py`, `config.py`, `clients/data/config.py`, `transport/asana_http.py`, `transport/config_translator.py`, `client.py`, `clients/data/client.py`, `cache/dataframe/circuit_breaker.py` + 4 more.

`CircuitBreaker` and `RetryOrchestrator` are actively used. The duplicate `CircuitBreakerOpenError` issue (EM-002) is the main concern.

### `src/autom8_asana/core/connections.py`

**Status**: Adopted by cache/connections subsystem only.

Imported by: `cache/connections/s3.py`, `cache/connections/redis.py`, `cache/connections/registry.py`. The `ConnectionManager` protocol and `ConnectionState`/`HealthCheckResult` types are used by the new connection managers.

### `src/autom8_asana/services/errors.py`

**Status**: Minimally adopted.

Imported by: `services/entity_service.py` (5 types), `services/task_service.py` (1 type), `services/section_service.py` (1 type). NOT imported by any route handler -- the `get_status_for_error()` mapping function and `SERVICE_ERROR_MAP` are unused at the API layer. The route handlers in `api/routes/` still raise `HTTPException` directly rather than catching `ServiceError`.

---

## Top 10 Priority Fixes (by ROI)

| Rank | IDs | Action | Files Affected | Effort | Impact |
|------|-----|--------|----------------|--------|--------|
| 1 | SW-001, SW-002 | Add logging to silent `except Exception: pass` sites | 2 | Low | High -- invisible failures |
| 2 | UE-001..UE-004 | Wire automation exception types into `pipeline.py`, `engine.py`, `seeding.py` | 4 | Medium | High -- exceptions were designed for this |
| 3 | EM-002 | Consolidate duplicate `CircuitBreakerOpenError` classes | 6 | Medium | Medium -- confusing for callers |
| 4 | SW-003..SW-006 | Add logging to remaining silent swallowed exceptions | 4 | Low | Medium |
| 5 | UE-005 | Wire `CacheReadError`/`CacheWriteError` into cache backends | 3 | Medium | Medium -- enables retry policy to distinguish |
| 6 | EM-001 | Fix redundant `except (KeyError, AttributeError, Exception)` | 1 | Low | Low -- clarity |
| 7 | BE-109, BT-001 | Decompose broad try block in `pipeline.py` execute | 1 | Medium | Medium -- better error attribution |
| 8 | UE-006 | Wire `ServiceError` types into route handlers via `get_status_for_error()` | 5+ | High | High -- completes service layer extraction |
| 9 | CE-001, CE-002 | Add explicit `CancelledError` guards in async retry and build coordinator | 2 | Low | Medium -- defensive against task cancellation |
| 10 | IH-001 | Fix inconsistent error handling in mutation_invalidator double-catch | 1 | Low | Medium -- prevents silent double failures |

---

## Methodology

- **bare-except**: Grep for `except\s+Exception` and `except:` patterns
- **swallowed-exception**: Manual review of `except Exception` sites where body is `pass`, `return None`, or log-only without re-raise on critical paths
- **unused-exception-type**: Cross-referencing class definitions against imports/raise/except sites across the codebase
- **exception-misuse**: Manual review of exception hierarchies, duplicate definitions, and redundant catch clauses
- **cancelled-error-catch**: Grep for `CancelledError` usage and cross-reference with `except Exception` in async contexts
- **broad-try**: Manual review of try block scope (lines between `try:` and `except`)
- **inconsistent-handling**: Cross-module comparison of error handling for the same operation type

**Note on Python version**: This codebase runs on Python 3.12+ where `asyncio.CancelledError` is a `BaseException`. The `except Exception` blocks do NOT catch `CancelledError` directly. The concern in CE-001/CE-002 is about operations that might wrap `CancelledError` in another exception before it reaches the retry loop.

**Note on "BROAD-CATCH" annotations**: The `dataframes/builders/freshness.py` module uses inline `# BROAD-CATCH: <boundary>` comments to document intentional broad catches at API boundaries. This is a good practice that should be extended to other modules.
