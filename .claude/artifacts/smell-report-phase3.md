# Smell Report -- Phase 3 (WS-6, WS-7, WS-8)

**Initiative**: Deep Code Hygiene -- autom8_asana
**Session**: session-20260210-230114-3c7097ab
**Phase**: 3 -- Polish
**Agent**: code-smeller
**Date**: 2026-02-11

---

## Executive Summary

Phase 3 targets three work streams: test fixture consolidation (WS-6), dead code removal (WS-7), and naming convention cataloging (WS-8). After systematic scanning of the post-Phase 1/Phase 2 codebase:

- **WS-6**: Validated and quantified. The fixture duplication is SEVERE -- far beyond the original claims. MockHTTPClient is copy-pasted in 18 files, MockAuthProvider in 26 files, MockLogger in 10 files, and fixture functions (`mock_http`, `config`, `auth_provider`, `logger`) are duplicated across 19-24 files each. Total duplicated test infrastructure: ~1,900 lines.
- **WS-7**: 3 of 7 claims REFUTED, 4 CONFIRMED. The mixins (FinancialFieldsMixin, SharedCascadingFieldsMixin) are NOT empty -- they contain field descriptors. `dataframes/storage.py` is NOT orphaned. However, `cache/connections/` has zero production imports, `SERIALIZATION_ERRORS` is never caught, `inflection` has zero usage, and `CacheReadError`/`CacheWriteError` are never raised.
- **WS-8**: Catalog produced. Notable findings include two `ActionExecutor` classes in different packages, two `BuildStatus` enums with different members, three freshness-related enums, and inconsistent enum base class usage (`str, Enum` vs plain `Enum`).

---

## WS-6: Test Fixture Consolidation

### SM-201: MockHTTPClient Class Duplicated in 18 Files (CRITICAL)

**Category**: DRY Violation -- Test Infrastructure
**Severity**: Critical | **Frequency**: 18 files | **Blast Radius**: ~360 lines | **Fix Complexity**: Low

**Definition Sites** (18 files):

| # | File | Line | Variant |
|---|------|------|---------|
| 1 | `tests/integration/conftest.py` | 33 | Basic (5 methods) |
| 2 | `tests/unit/test_tasks_client.py` | 16 | Basic (5 methods) |
| 3 | `tests/unit/test_batch.py` | 22 | Basic (5 methods) |
| 4 | `tests/unit/test_batch_adversarial.py` | 30 | Basic (5 methods) |
| 5 | `tests/unit/test_tier1_clients.py` | 33 | Basic (5 methods) |
| 6 | `tests/unit/test_tier1_adversarial.py` | 48 | Basic (5 methods) |
| 7 | `tests/unit/clients/test_tasks_cache.py` | 23 | Basic (5 methods) |
| 8 | `tests/unit/clients/test_custom_fields_cache.py` | 24 | Basic (5 methods) |
| 9 | `tests/unit/clients/test_projects_cache.py` | 24 | Basic (5 methods) |
| 10 | `tests/unit/clients/test_sections_cache.py` | 25 | Basic (5 methods) |
| 11 | `tests/unit/clients/test_stories_cache.py` | 22 | Basic (5 methods) |
| 12 | `tests/unit/clients/test_users_cache.py` | 24 | Basic (5 methods) |
| 13 | `tests/unit/clients/test_tasks_duplicate.py` | 18 | Basic (5 methods) |
| 14 | `tests/unit/clients/test_tasks_dependents.py` | 17 | Basic (5 methods) |
| 15 | `tests/unit/test_tier2_clients.py` | 36 | Extended (+post_multipart, get_stream_url) |
| 16 | `tests/unit/test_tier2_adversarial.py` | 55 | Extended (+post_multipart, get_stream_url) |
| 17 | `tests/unit/test_coverage_gap.py` | 26 | Extended (+post_multipart, get_stream_url) |
| 18 | `tests/integration/test_stories_cache_integration.py` | 28 | Basic (5 methods) |

**Evidence**: Two variants exist:
- **Basic** (15 files): `get`, `post`, `put`, `delete`, `get_paginated` -- all `AsyncMock()`
- **Extended** (3 files): Basic + `post_multipart`, `get_stream_url` -- for attachment/stream operations

**Consolidation Assessment**: Both variants are trivially consolidatable into a single class with the superset of methods. A shared `MockHTTPClient` in `tests/conftest.py` or a dedicated `tests/_mocks.py` module would eliminate all 18 copies. The extended variant is a strict superset; unused methods cause no test interference.

**ROI Score**: 9.5/10

---

### SM-202: MockAuthProvider Class Duplicated in 26 Files (CRITICAL)

**Category**: DRY Violation -- Test Infrastructure
**Severity**: Critical | **Frequency**: 26 files | **Blast Radius**: ~78 lines | **Fix Complexity**: Low

**Definition Sites** (26 files):

| # | File | Line | Notes |
|---|------|------|-------|
| 1 | `tests/integration/conftest.py` | 44 | Module-level |
| 2 | `tests/integration/test_savesession_partial_failures.py` | 21 | Module-level |
| 3 | `tests/integration/test_stories_cache_integration.py` | 44 | Module-level |
| 4 | `tests/unit/test_tasks_client.py` | 27 | Module-level |
| 5 | `tests/unit/test_batch.py` | 33 | Module-level |
| 6 | `tests/unit/test_batch_adversarial.py` | 41 | Module-level |
| 7 | `tests/unit/test_tier1_clients.py` | 44 | Module-level |
| 8 | `tests/unit/test_tier1_adversarial.py` | 59 | Module-level |
| 9 | `tests/unit/test_tier2_clients.py` | 49 | Module-level |
| 10 | `tests/unit/test_tier2_adversarial.py` | 68 | Module-level |
| 11 | `tests/unit/test_coverage_gap.py` | 39 | Module-level |
| 12 | `tests/unit/test_client.py` | 16 | Module-level |
| 13 | `tests/unit/transport/test_asana_http.py` | 23 | Module-level |
| 14 | `tests/unit/transport/test_aimd_integration.py` | 23 | Module-level |
| 15 | `tests/unit/clients/test_tasks_cache.py` | 34 | Module-level |
| 16 | `tests/unit/clients/test_custom_fields_cache.py` | 35 | Module-level |
| 17 | `tests/unit/clients/test_projects_cache.py` | 35 | Module-level |
| 18 | `tests/unit/clients/test_sections_cache.py` | 36 | Module-level |
| 19 | `tests/unit/clients/test_stories_cache.py` | 33 | Module-level |
| 20 | `tests/unit/clients/test_users_cache.py` | 35 | Module-level |
| 21 | `tests/unit/clients/test_tasks_duplicate.py` | 29 | Module-level |
| 22 | `tests/unit/clients/test_tasks_dependents.py` | 28 | Module-level |
| 23-26 | `tests/unit/test_phase2a_adversarial.py` | 783, 908, 968, 1026 | Class-scoped (4x) |

**Evidence**: All 26 definitions are functionally identical -- a class with a single `get_secret(key) -> str` method returning `"test-token"`.

**Consolidation Assessment**: 100% identical across all sites. Direct candidate for `tests/conftest.py`.

**ROI Score**: 9.0/10

---

### SM-203: MockLogger Class Duplicated in 10 Files (HIGH)

**Category**: DRY Violation -- Test Infrastructure
**Severity**: High | **Frequency**: 10 files | **Blast Radius**: ~150 lines | **Fix Complexity**: Low

**Definition Sites** (10 files):

| # | File | Line | Variant |
|---|------|------|---------|
| 1 | `tests/integration/conftest.py` | 51 | Basic (4 methods) |
| 2 | `tests/integration/test_savesession_partial_failures.py` | 28 | Extended (+exception) |
| 3 | `tests/unit/test_tasks_client.py` | 34 | Extended (+exception) |
| 4 | `tests/unit/test_batch.py` | 40 | Extended (+exception) |
| 5 | `tests/unit/test_batch_adversarial.py` | 48 | Extended (+exception) |
| 6 | `tests/unit/test_tier1_clients.py` | 51 | Extended (+exception) |
| 7 | `tests/unit/test_tier1_adversarial.py` | 66 | Extended (+exception) |
| 8 | `tests/unit/test_tier2_clients.py` | 56 | Extended (+exception) |
| 9 | `tests/unit/test_tier2_adversarial.py` | 75 | Extended (+exception) |
| 10 | `tests/unit/test_coverage_gap.py` | 46 | Extended (+exception) |

**Evidence**: Two variants:
- **Basic** (1 file): `debug`, `info`, `warning`, `error`
- **Extended** (9 files): Basic + `exception`

**Consolidation Assessment**: Superset approach -- single MockLogger with all 5 methods. The `exception` method is harmless when present but unused.

**ROI Score**: 8.0/10

---

### SM-204: `mock_http` Fixture Duplicated in 24 Files (CRITICAL)

**Category**: DRY Violation -- Fixture Definition
**Severity**: Critical | **Frequency**: 24 files | **Blast Radius**: ~72 lines | **Fix Complexity**: Low

**Definition Sites** (24 total):

**Pattern A -- returns `MockHTTPClient()`** (18 files):
`tests/integration/conftest.py:71`, `tests/unit/test_tasks_client.py:57`, `tests/unit/test_batch.py:63`, `tests/unit/test_batch_adversarial.py:71`, `tests/unit/test_tier1_clients.py:74`, `tests/unit/test_tier1_adversarial.py:89`, `tests/unit/test_tier2_clients.py:79`, `tests/unit/test_tier2_adversarial.py:98`, `tests/unit/test_coverage_gap.py:69`, `tests/unit/clients/test_tasks_cache.py:87`, `tests/unit/clients/test_custom_fields_cache.py:87`, `tests/unit/clients/test_projects_cache.py:87`, `tests/unit/clients/test_sections_cache.py:98`, `tests/unit/clients/test_stories_cache.py:80`, `tests/unit/clients/test_users_cache.py:87`, `tests/unit/clients/test_tasks_duplicate.py:36`, `tests/unit/clients/test_tasks_dependents.py:36`, `tests/integration/test_stories_cache_integration.py:80`

**Pattern B -- returns `MagicMock()` with explicit methods** (2 files):
`tests/integration/test_cache_optimization_e2e.py:97`, `tests/unit/persistence/test_action_executor.py:36`

**Pattern C -- class-scoped `AsyncMock`** (4 class fixtures in 1 file):
`tests/unit/test_phase2a_adversarial.py:771,896,956,1014`

**Consolidation Assessment**: Pattern A (18 files) is trivially consolidatable -- all return `MockHTTPClient()`. Pattern B uses `MagicMock` differently for different test needs. Pattern C is class-scoped and test-specific -- should remain as-is.

**Appropriate conftest level**: `tests/conftest.py` for MockHTTPClient class + `mock_http` fixture (covers both unit and integration).

**ROI Score**: 9.0/10

---

### SM-205: `config` Fixture Duplicated in 19 Files (HIGH)

**Category**: DRY Violation -- Fixture Definition
**Severity**: High | **Frequency**: 19 files | **Blast Radius**: ~57 lines | **Fix Complexity**: Low

**Definition Sites** (19 files returning `AsanaConfig()`):
`tests/unit/test_tasks_client.py:63`, `tests/unit/test_batch.py:69`, `tests/unit/test_batch_adversarial.py:77`, `tests/unit/test_tier1_clients.py:80`, `tests/unit/test_tier1_adversarial.py:95`, `tests/unit/test_tier2_clients.py:85`, `tests/unit/test_tier2_adversarial.py:104`, `tests/unit/test_coverage_gap.py:75`, `tests/unit/clients/test_tasks_cache.py:93`, `tests/unit/clients/test_custom_fields_cache.py:93`, `tests/unit/clients/test_projects_cache.py:93`, `tests/unit/clients/test_sections_cache.py:104`, `tests/unit/clients/test_stories_cache.py:86`, `tests/unit/clients/test_users_cache.py:93`, `tests/unit/clients/test_tasks_duplicate.py:43`, `tests/unit/clients/test_tasks_dependents.py:42`, `tests/integration/test_cache_optimization_e2e.py:115`, `tests/integration/test_savesession_partial_failures.py:51`, `tests/integration/test_stories_cache_integration.py:86`

**Exception** (1 file with different return type):
`tests/unit/automation/events/test_rule.py:45` -- returns `EventRoutingConfig`, not `AsanaConfig`

**Evidence**: All 19 `AsanaConfig` fixtures are identical: `return AsanaConfig()`.

**Consolidation Assessment**: 100% identical. Belongs in `tests/conftest.py`.

**ROI Score**: 8.5/10

---

### SM-206: `auth_provider` / `mock_auth` Fixture Duplicated in 20 Files (HIGH)

**Category**: DRY Violation -- Fixture Definition
**Severity**: High | **Frequency**: 20 files | **Blast Radius**: ~60 lines | **Fix Complexity**: Low

**Definition Sites**:

**`auth_provider` returning `MockAuthProvider()`** (18 files):
`tests/unit/test_tasks_client.py:69`, `tests/unit/test_batch.py:75`, `tests/unit/test_batch_adversarial.py:83`, `tests/unit/test_tier1_clients.py:86`, `tests/unit/test_tier1_adversarial.py:101`, `tests/unit/test_tier2_clients.py:91`, `tests/unit/test_tier2_adversarial.py:110`, `tests/unit/test_coverage_gap.py:81`, `tests/unit/clients/test_tasks_cache.py:99`, `tests/unit/clients/test_custom_fields_cache.py:99`, `tests/unit/clients/test_projects_cache.py:99`, `tests/unit/clients/test_sections_cache.py:110`, `tests/unit/clients/test_stories_cache.py:92`, `tests/unit/clients/test_users_cache.py:99`, `tests/unit/clients/test_tasks_duplicate.py:49`, `tests/unit/clients/test_tasks_dependents.py:48`, `tests/integration/test_stories_cache_integration.py:92`, `tests/integration/test_savesession_partial_failures.py:65`

**`mock_auth` returning `MagicMock`** (2 files):
`tests/integration/conftest.py:77`, `tests/integration/test_cache_optimization_e2e.py:107`

**Evidence**: 18 files return `MockAuthProvider()`. 2 files use MagicMock. Naming is split between `auth_provider` and `mock_auth`.

**Consolidation Assessment**: Naming should be unified. The MockAuthProvider-based fixture belongs in `tests/conftest.py`. The `mock_auth` (MagicMock) variant in integration tests may be needed for different test patterns -- evaluate on merge.

**ROI Score**: 8.5/10

---

### SM-207: `logger` / `mock_logger` Fixture Duplicated in 11 Files (MEDIUM)

**Category**: DRY Violation -- Fixture Definition
**Severity**: Medium | **Frequency**: 11 files | **Blast Radius**: ~33 lines | **Fix Complexity**: Low

**Definition Sites**:

**`logger` returning `MockLogger()`** (9 files):
`tests/unit/test_tasks_client.py:75`, `tests/unit/test_batch.py:81`, `tests/unit/test_batch_adversarial.py:89`, `tests/unit/test_tier1_clients.py:92`, `tests/unit/test_tier1_adversarial.py:107`, `tests/unit/test_tier2_clients.py:97`, `tests/unit/test_tier2_adversarial.py:116`, `tests/unit/test_coverage_gap.py:87`, `tests/integration/test_savesession_partial_failures.py:71`

**`mock_logger` variants** (2 files):
`tests/integration/conftest.py:83` -- returns `MockLogger()`, `tests/unit/dataframes/test_cache_integration.py:71` -- returns `MagicMock()`

**Consolidation Assessment**: 9 files use identical `MockLogger()`. Naming split between `logger` and `mock_logger`. Consolidatable to `tests/conftest.py`.

**ROI Score**: 7.5/10

---

### SM-208: MockCacheProvider Class Duplicated in 8 Files (MEDIUM)

**Category**: DRY Violation -- Test Infrastructure
**Severity**: Medium | **Frequency**: 8 files | **Blast Radius**: ~160 lines | **Fix Complexity**: Medium

**Definition Sites**:

| # | File | Line | Notes |
|---|------|------|-------|
| 1 | `tests/unit/clients/test_tasks_cache.py` | 41 | Full protocol impl |
| 2 | `tests/unit/clients/test_custom_fields_cache.py` | 42 | Full protocol impl |
| 3 | `tests/unit/clients/test_projects_cache.py` | 42 | Full protocol impl |
| 4 | `tests/unit/clients/test_sections_cache.py` | 43 | Full protocol impl |
| 5 | `tests/unit/clients/test_stories_cache.py` | 40 | Full protocol impl |
| 6 | `tests/unit/clients/test_users_cache.py` | 42 | Full protocol impl |
| 7 | `tests/unit/cache/test_dataframes.py` | 20 | Different impl |
| 8 | `tests/unit/cache/test_stories.py` | 20 | Different impl |

**Evidence**: The 6 client cache test files all define identical `MockCacheProvider` classes with `get`, `set`, `invalidate` methods backed by an internal dict. The cache module test files have different implementations.

**Consolidation Assessment**: The 6 client cache test files are identical. Could consolidate into `tests/unit/clients/conftest.py`. The cache module variants are test-specific.

**ROI Score**: 7.0/10

---

### SM-209: `cache_provider` Fixture Duplicated in 8 Files (MEDIUM)

**Category**: DRY Violation -- Fixture Definition
**Severity**: Medium | **Frequency**: 8 files | **Blast Radius**: ~24 lines | **Fix Complexity**: Low

**Definition Sites**:

**`cache_provider` returning `MockCacheProvider()`** (6 files):
`tests/unit/clients/test_tasks_cache.py:105`, `tests/unit/clients/test_custom_fields_cache.py:105`, `tests/unit/clients/test_projects_cache.py:105`, `tests/unit/clients/test_sections_cache.py:116`, `tests/unit/clients/test_stories_cache.py:98`, `tests/unit/clients/test_users_cache.py:105`

**`cache_provider` returning `EnhancedInMemoryCacheProvider`** (2 files):
`tests/integration/test_cache_optimization_e2e.py:91`, `tests/integration/test_stories_cache_integration.py:74`

**Consolidation Assessment**: The 6 client files are identical. Move to `tests/unit/clients/conftest.py`.

**ROI Score**: 6.5/10

---

### SM-210: `clean_registries` / `clean_registry` Fixture Duplicated in 9 Files (MEDIUM)

**Category**: DRY Violation -- Fixture Definition
**Severity**: Medium | **Frequency**: 9 files | **Blast Radius**: ~54 lines | **Fix Complexity**: Low

**Definition Sites**:

**`clean_registries` (resets 2 registries)** (5 files):
`tests/integration/test_detection.py:49`, `tests/integration/test_workspace_registry.py:40`, `tests/integration/test_hydration_cache_integration.py:48`, `tests/integration/test_hydration.py:53`, `tests/unit/models/business/test_detection.py:69`

**`clean_registry` (resets 1 registry)** (4 files):
`tests/unit/models/business/test_detection.py:61`, `tests/unit/detection/test_detection_cache.py:47`, `tests/unit/models/business/test_registry.py:37`, `tests/unit/models/business/test_patterns.py:38`

**Note**: The root `tests/conftest.py` already has `reset_registries` as an autouse fixture that resets 4 registries. These per-file fixtures may be REDUNDANT rather than merely duplicated -- they reset a subset of what the root conftest already handles.

**Consolidation Assessment**: Investigate whether the root conftest `reset_registries` autouse fixture makes these per-file fixtures unnecessary. If so, they can be deleted rather than consolidated.

**ROI Score**: 7.0/10

---

### SM-211: `mock_invalidator` Fixture Duplicated in 4 Files (LOW)

**Category**: DRY Violation -- Fixture Definition
**Severity**: Low | **Frequency**: 4 files | **Blast Radius**: ~12 lines | **Fix Complexity**: Low

**Definition Sites**:
`tests/api/test_tasks_invalidation.py:29`, `tests/api/test_sections_invalidation.py:24`, `tests/unit/services/test_section_service.py:30`, `tests/unit/services/test_task_service.py:35`

**Evidence**: All return `MagicMock()`.

**ROI Score**: 5.0/10

---

### SM-212: `mock_batch_client` Fixture Duplicated in 5+ Files (LOW)

**Category**: DRY Violation -- Fixture Definition
**Severity**: Low | **Frequency**: 5 module-level + 3 class-level | **Blast Radius**: ~30 lines | **Fix Complexity**: Low

**Module-level definition sites**:
`tests/unit/cache/test_freshness_coordinator.py:24`, `tests/unit/cache/test_staleness_coordinator.py:32`, `tests/unit/cache/test_unified.py:33`, `tests/unit/cache/test_lightweight_checker.py:24`, `tests/integration/test_unified_cache_success_criteria.py:67`

**ROI Score**: 5.5/10

---

### SM-213: `reset_cache_ready` Fixture Duplicated in 3 Files (LOW)

**Category**: DRY Violation -- Fixture Definition
**Severity**: Low | **Frequency**: 3 files | **Blast Radius**: ~9 lines | **Fix Complexity**: Low

**Definition Sites**:
`tests/api/test_health.py:34`, `tests/api/test_startup_preload.py:29`, `tests/unit/api/test_preload_parquet_fallback.py:22`

**ROI Score**: 4.5/10

---

### SM-214: `mock_service_claims` Fixture Duplicated in 3 Files (LOW)

**Category**: DRY Violation -- Fixture Definition
**Severity**: Low | **Frequency**: 3 files | **Blast Radius**: ~9 lines | **Fix Complexity**: Low

**Definition Sites**:
`tests/api/test_routes_admin_adversarial.py:33`, `tests/api/test_routes_admin.py:32`, `tests/integration/test_entity_resolver_e2e.py:94`

**ROI Score**: 4.5/10

---

### WS-6 Consolidation Summary

**Total duplicated test infrastructure**: ~1,900 lines across 6 mock classes + 8 fixture categories

**Recommended conftest hierarchy**:
- `tests/conftest.py` (root): MockHTTPClient, MockAuthProvider, MockLogger classes + `mock_http`, `config`, `auth_provider`, `logger` fixtures
- `tests/unit/clients/conftest.py` (new): MockCacheProvider class + `cache_provider` fixture
- Per-file: Class-scoped fixtures (test_phase2a_adversarial) and test-specific MagicMock variants remain local

---

## WS-7: Dead Code Verification

### SM-215: `cache/connections/` Package -- Zero Production Imports (HIGH)

**Category**: Dead Code -- Orphaned Module
**Severity**: High | **Blast Radius**: 3 files (~400 lines) | **Fix Complexity**: Low

**Claim**: `cache/connections/` package has 0 production imports.

**Verification**: CONFIRMED.

**Evidence**:
```
# Grep for imports from cache.connections across ALL production code:
src/autom8_asana/cache/connections/__init__.py  -- self-referential only
src/autom8_asana/cache/connections/redis.py     -- internal
src/autom8_asana/cache/connections/registry.py  -- internal
src/autom8_asana/cache/connections/s3.py        -- internal
```

Zero imports from any file outside `cache/connections/` itself. The backends (`cache/backends/s3.py`, `cache/backends/redis.py`) accept `connection_manager` parameters typed as `Any | None` but never import the connection manager classes.

**Test-only usage**: 5 test files import from `cache.connections`:
- `tests/unit/cache/connections/test_s3_manager.py`
- `tests/unit/cache/connections/test_redis_manager.py`
- `tests/unit/cache/connections/test_registry.py`
- `tests/unit/cache/test_backends_with_manager.py`
- `tests/unit/cache/test_registry_lifespan.py`

**Phase 1/2 impact**: Phase 1 created `cache/backends/base.py` but did NOT wire it to connection managers. Status unchanged.

**ROI Score**: 7.5/10

---

### SM-216: `SERIALIZATION_ERRORS` Tuple -- Defined but Never Caught (MEDIUM)

**Category**: Dead Code -- Unused Constant
**Severity**: Medium | **Blast Radius**: 5 lines | **Fix Complexity**: Low

**Claim**: `SERIALIZATION_ERRORS` defined but never used in any `except` clause.

**Verification**: CONFIRMED.

**Evidence**:
- Defined at `src/autom8_asana/core/exceptions.py:336`
- Contains: `CacheReadError`, `CacheWriteError`
- Grep for `except.*SERIALIZATION_ERRORS` across all source: **0 matches**
- `CacheReadError` is never raised (0 `raise CacheReadError` in source)
- `CacheWriteError` is never raised (0 `raise CacheWriteError` in source)
- Only external reference: `tests/unit/core/test_exceptions.py` (membership tests)

**Note**: The exception classes themselves (`CacheReadError`, `CacheWriteError`) are also dead -- defined but never raised.

**ROI Score**: 6.0/10

---

### SM-217: `inflection` Dependency -- Zero Usage (MEDIUM)

**Category**: Dead Code -- Unused Dependency
**Severity**: Medium | **Blast Radius**: 1 line in pyproject.toml | **Fix Complexity**: Low

**Claim**: `inflection` dependency is unused.

**Verification**: CONFIRMED.

**Evidence**:
- Declared at `pyproject.toml:22`: `"inflection>=0.5.0"`
- Grep for `import inflection` or `from inflection` across entire repo: **0 matches**
- Comment says: "Singularization for entity type mapping (Rails port)" -- this functionality was apparently never implemented or was removed.

**ROI Score**: 6.5/10

---

### SM-218: `arrow` Dependency -- 2 Files, Stdlib Replaceable (LOW)

**Category**: Dead Code -- Unnecessary Dependency
**Severity**: Low | **Blast Radius**: 2 source files | **Fix Complexity**: Medium

**Claim**: `arrow` can be replaced with stdlib.

**Verification**: PARTIALLY CONFIRMED -- used in 2 files but replaceable.

**Usage sites**:

1. `src/autom8_asana/automation/seeding.py:22`:
   - `arrow.now().format("YYYY-MM-DD")` at line 334
   - Replaceable with `datetime.date.today().isoformat()`

2. `src/autom8_asana/models/business/descriptors.py:40`:
   - `arrow.Arrow` type alias at line 77
   - `arrow.get(value)` date parsing at line 701
   - `arrow.parser.ParserError` exception at line 702
   - `arrow.now().shift(days=7)` in docstring/example at line 679
   - More involved replacement -- arrow provides flexible date parsing and arrow types are part of the descriptors API

3. `tests/unit/models/business/test_custom_field_descriptors.py:14` (test file)

**Assessment**: The `seeding.py` usage is trivially replaceable. The `descriptors.py` usage is more embedded -- arrow types are part of the `DateField` descriptor return type. Replacing would require changing the public API of `DateField`.

**ROI Score**: 4.0/10

---

### SM-219: FinancialFieldsMixin -- NOT Empty (REFUTED)

**Category**: Claim Verification
**Severity**: N/A -- Claim refuted

**Claim**: "FinancialFieldsMixin is empty, used by 4 classes."

**Verification**: REFUTED.

**Evidence**: `src/autom8_asana/models/business/mixins.py:72-96`
```python
class FinancialFieldsMixin:
    booking_type = EnumField()
    mrr = NumberField(field_name="MRR")
    weekly_ad_spend = NumberField()
```

Contains 3 field descriptors. Used by Business, Unit, Offer, Process (4 classes as claimed). The mixin is ACTIVE and FUNCTIONAL -- it provides DRY field descriptor inheritance.

---

### SM-220: SharedCascadingFieldsMixin -- NOT Empty (REFUTED)

**Category**: Claim Verification
**Severity**: N/A -- Claim refuted

**Claim**: "SharedCascadingFieldsMixin is empty."

**Verification**: REFUTED.

**Evidence**: `src/autom8_asana/models/business/mixins.py:51-69`
```python
class SharedCascadingFieldsMixin:
    vertical = EnumField()
    rep = PeopleField()
```

Contains 2 field descriptors. Used by Business, Unit, Offer, Process (4 classes).

---

### Phase 1/2 Overlap Assessment

**sync_wrapper still in use**: `sync_wrapper` from `transport.sync` is still actively used in:
- `batch/client.py` (5 decorators)
- `models/business/seeder.py` (1 decorator)
- `models/task.py` (2 inline usages)
- `persistence/session.py` (1 decorator)
- `transport/__init__.py` (re-export)

Phase 1 converted Asana clients to `@async_method` but did NOT convert batch client, seeder, task model, or session. `sync_wrapper` is NOT dead code.

**`dataframes/storage.py`**: NOT orphaned -- actively imported by `section_persistence.py`, `watermark.py`, `api/preload/progressive.py`, `api/preload/legacy.py`.

---

## WS-8: Naming and Convention Catalog

*This section catalogs current naming conventions for ADR authoring. No SM identifiers or ROI scores are assigned.*

### Class Suffix Inventory

| Suffix | Count | Locations |
|--------|-------|-----------|
| **Client** | 18 | `AsanaClient`, `AsanaHttpClient`, `BaseClient`, `BatchClient`, `DataServiceClient`, `TasksClient`, `ProjectsClient`, `SectionsClient`, `UsersClient`, `StoriesClient`, `TeamsClient`, `TagsClient`, `GoalsClient`, `AttachmentsClient`, `PortfoliosClient`, `WebhooksClient`, `WorkspacesClient`, `CustomFieldsClient` |
| **Provider** | 14 | `CacheProvider` (Protocol), `LogProvider` (Protocol), `AuthProvider` (Protocol), `NullCacheProvider`, `InMemoryCacheProvider`, `DefaultLogProvider`, `EnvAuthProvider`, `NotConfiguredAuthProvider`, `SecretsManagerAuthProvider`, `TieredCacheProvider`, `S3CacheProvider`, `RedisCacheProvider`, `EnhancedInMemoryCacheProvider`, `AsanaSchemaProvider` |
| **Manager** | 5 | `CheckpointManager`, `ConnectionManager` (Protocol), `HolderConcurrencyManager`, `HealingManager`, `S3ConnectionManager`, `RedisConnectionManager` |
| **Registry** | 8 | `EntityProjectRegistry`, `EntityRegistry`, `ConnectionRegistry`, `WorkflowRegistry`, `SchemaRegistry`, `MetricRegistry`, `ProjectTypeRegistry`, `WorkspaceProjectRegistry` |
| **Executor** | 4 | `CascadeExecutor`, `BatchExecutor`, `ActionExecutor` (persistence), `ActionExecutor` (automation/polling) |
| **Coordinator** | 4 | `TaskCacheCoordinator`, `StalenessCheckCoordinator`, `FreshnessCoordinator`, `BuildCoordinator` |
| **Service** | 5 | `EntityQueryService`, `EntityService`, `TaskService`, `SectionService`, `SearchService` |
| **Builder** | 4 | `ActionBuilder`, `DataFrameBuilder` (ABC), `ProgressiveProjectBuilder`, `SectionDataFrameBuilder` |
| **Factory** | 2 | `CacheProviderFactory`, `HolderFactory` |
| **Handler** | 1 | `AsanaResponseHandler` |
| **Strategy** | 1 | `UniversalResolutionStrategy` |
| **Mixin** | 8 | `HolderMixin`, `DegradedModeMixin`, `SharedCascadingFieldsMixin`, `FinancialFieldsMixin`, `UpwardTraversalMixin`, `UnitNavigableEntityMixin`, `UnitNestedHolderMixin`, `RetryableErrorMixin` |

**Notable naming collision**: Two `ActionExecutor` classes exist in different packages:
- `src/autom8_asana/persistence/action_executor.py:98` -- batch API action execution
- `src/autom8_asana/automation/polling/action_executor.py:78` -- polling rule action execution

### Enum Base Class Patterns

| Pattern | Count | Examples |
|---------|-------|---------|
| `str, Enum` | 20 | `Op`, `AggFunction`, `EventType`, `SectionStatus`, `EntityCategory`, `OfferSection`, `SectionOutcome`, `BuildStatus` (builders), `MutationType`, `EntityKind`, `ResolutionStrategy`, `ProcessType`, `ProcessSection`, `EntryType`, `ActionType`, `VerificationSource`, `FreshnessClassification`, `FreshnessStatus`, `AuthMode`, `BuildOutcome` |
| `Enum` (plain) | 9 | `EntityType`, `BackoffType`, `Subsystem`, `CBState`, `ConnectionState`, `EntityState`, `OperationType`, `ActionVariant`, `BuildStatus` (coalescer), `WarmResult`, `FreshnessMode`, `CircuitState` |
| `IntEnum` | 1 | `CompletenessLevel` |

**Notable naming collision**: Two `BuildStatus` enums:
- `src/autom8_asana/dataframes/builders/build_result.py:90` -- `str, Enum` with SUCCESS/PARTIAL/FAILURE
- `src/autom8_asana/cache/dataframe/coalescer.py:21` -- plain `Enum` with BUILDING/SUCCESS/FAILURE

**Three freshness-related enums with overlapping concepts**:
- `FreshnessClassification` (`cache/models/freshness_stamp.py:37`) -- `str, Enum`
- `Freshness` (`cache/models/freshness.py:20`) -- `str, Enum`
- `FreshnessStatus` (`cache/integration/dataframe_cache.py:43`) -- `str, Enum`

### Module Naming: Singular vs. Plural

| Pattern | Examples |
|---------|---------|
| **Singular** (module = single concept) | `client.py`, `config.py`, `settings.py`, `entrypoint.py`, `task.py`, `project.py`, `section.py`, `story.py`, `user.py`, `team.py`, `tag.py`, `goal.py`, `portfolio.py`, `webhook.py`, `workspace.py`, `attachment.py`, `custom_field.py` |
| **Plural** (module = collection/operations for type) | `clients/` (package), `tasks.py`, `projects.py`, `sections.py`, `users.py`, `stories.py`, `teams.py`, `tags.py`, `goals.py`, `portfolios.py`, `webhooks.py`, `workspaces.py`, `attachments.py`, `custom_fields.py`, `services/` (package), `models/` (package), `protocols/` (package), `patterns/` (package), `metrics/` (package) |

**Convention**: Models are singular (`models/task.py`), clients are plural (`clients/tasks.py`). Packages are plural. This is consistent with common Python conventions.

### Constants Typing Patterns

| Pattern | Count | Examples |
|---------|-------|---------|
| `dict[K, V]` | 8+ | `SERVICE_ERROR_MAP`, `ENTITY_ALIASES`, `DEFAULT_KEY_COLUMNS`, `ACTION_REGISTRY`, etc. |
| `tuple[type[Exception], ...]` | 5 | `CACHE_TRANSIENT_ERRORS`, `S3_TRANSPORT_ERRORS`, `REDIS_TRANSPORT_ERRORS`, `ALL_TRANSPORT_ERRORS`, `SERIALIZATION_ERRORS` |
| `list[T]` | 4+ | `ORDERING_RULES`, `ENTITY_RELATIONSHIPS`, schema column lists |
| `set[str]` | 2 | `SUPPORTED_ENTITY_TYPES`, `PRELOAD_EXCLUDE_PROJECT_GIDS` |
| `frozenset[str]` | 2 | `SUPPORTED_AGGS`, values in `AGG_COMPATIBILITY` / `OPERATOR_MATRIX` |
| `Final` | 0 | No usage of `Final` for constants anywhere |

**Note**: No constants use `Final` typing despite all being module-level immutables. This is a convention gap -- `Final` would prevent accidental reassignment.

### Return Pattern Notes

- Client methods consistently return `Model | dict` via `@overload` pattern (Phase 1 standardized this)
- Service methods return domain-specific result objects
- No notable inconsistencies in return patterns post-Phase 1/2

---

## ROI Summary Table (WS-6 + WS-7)

| ID | Finding | Severity | Files | Lines | Fix Complexity | ROI |
|----|---------|----------|-------|-------|----------------|-----|
| SM-201 | MockHTTPClient duplication | Critical | 18 | ~360 | Low | 9.5 |
| SM-204 | `mock_http` fixture duplication | Critical | 24 | ~72 | Low | 9.0 |
| SM-202 | MockAuthProvider duplication | Critical | 26 | ~78 | Low | 9.0 |
| SM-205 | `config` fixture duplication | High | 19 | ~57 | Low | 8.5 |
| SM-206 | `auth_provider`/`mock_auth` duplication | High | 20 | ~60 | Low | 8.5 |
| SM-203 | MockLogger duplication | High | 10 | ~150 | Low | 8.0 |
| SM-207 | `logger`/`mock_logger` duplication | Medium | 11 | ~33 | Low | 7.5 |
| SM-215 | `cache/connections/` zero prod imports | High | 3 | ~400 | Low | 7.5 |
| SM-208 | MockCacheProvider duplication | Medium | 8 | ~160 | Medium | 7.0 |
| SM-210 | `clean_registries` duplication | Medium | 9 | ~54 | Low | 7.0 |
| SM-209 | `cache_provider` fixture duplication | Medium | 8 | ~24 | Low | 6.5 |
| SM-217 | `inflection` unused dependency | Medium | 1 | ~1 | Low | 6.5 |
| SM-216 | `SERIALIZATION_ERRORS` + exceptions dead | Medium | 1 | ~10 | Low | 6.0 |
| SM-212 | `mock_batch_client` duplication | Low | 5+ | ~30 | Low | 5.5 |
| SM-211 | `mock_invalidator` duplication | Low | 4 | ~12 | Low | 5.0 |
| SM-214 | `mock_service_claims` duplication | Low | 3 | ~9 | Low | 4.5 |
| SM-213 | `reset_cache_ready` duplication | Low | 3 | ~9 | Low | 4.5 |
| SM-218 | `arrow` replaceable with stdlib | Low | 2 | ~10 | Medium | 4.0 |

---

## Attestation Table

| Artifact | Path | Verified Via | Status |
|----------|------|-------------|--------|
| MockHTTPClient definitions | 18 files listed in SM-201 | `Grep class MockHTTPClient` | Verified |
| MockAuthProvider definitions | 26 files listed in SM-202 | `Grep class MockAuthProvider` | Verified |
| MockLogger definitions | 10 files listed in SM-203 | `Grep class MockLogger` | Verified |
| mock_http fixtures | 24 files listed in SM-204 | `Grep def mock_http` | Verified |
| config fixtures | 19 files listed in SM-205 | `Grep def config()` | Verified |
| auth_provider fixtures | 20 files listed in SM-206 | `Grep def (auth_provider\|mock_auth)` | Verified |
| logger fixtures | 11 files listed in SM-207 | `Grep def (logger\|mock_logger)` | Verified |
| cache/connections imports | Zero production imports | `Grep from.*cache\.connections` (src only) | Verified |
| SERIALIZATION_ERRORS usage | Never caught | `Grep except.*SERIALIZATION_ERRORS` | Verified |
| CacheReadError/CacheWriteError | Never raised | `Grep raise Cache(Read\|Write)Error` | Verified |
| inflection imports | Zero | `Grep (import\|from) inflection` | Verified |
| arrow usage | 2 source files | `Grep (import\|from) arrow` (src only) | Verified |
| FinancialFieldsMixin content | 3 descriptors (NOT empty) | `Read mixins.py:72-96` | Verified |
| SharedCascadingFieldsMixin content | 2 descriptors (NOT empty) | `Read mixins.py:51-69` | Verified |
| sync_wrapper usage | Still active in 4 modules | `Grep sync_wrapper` (src only) | Verified |
| dataframes/storage.py imports | Active (4+ importers) | `Grep from.*dataframes\.storage` | Verified |
| Root conftest fixtures | 3 fixtures (builder, settings reset, registry reset) | `Read tests/conftest.py` | Verified |
| Enum base class patterns | 20 str,Enum + 9 plain Enum + 1 IntEnum | `Grep class.*Enum\)` (src only) | Verified |
| ActionExecutor collision | 2 classes in different packages | `Grep class.*Executor` (src only) | Verified |
| BuildStatus collision | 2 enums with different members | `Grep class BuildStatus` (src only) | Verified |
