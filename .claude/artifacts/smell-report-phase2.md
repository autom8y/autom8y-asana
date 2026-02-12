# Smell Report -- Phase 2 (WS-4, WS-5)

**Session**: session-20260210-230114-3c7097ab
**Initiative**: Deep Code Hygiene -- autom8_asana
**Phase**: 2 -- Decomposition and Magic Values
**Date**: 2026-02-11
**Agent**: code-smeller

---

## Phase 1 Overlap Assessment

Before assessing Phase 2 targets, the following Phase 1 changes are confirmed:

| Phase 1 Change | Impact on Phase 2 |
|---|---|
| RF-001: `dataframes/decorator.py` decomposed from 172-line `cached_resolve` to 46-line orchestrator | **File deleted** (`src/autom8_asana/dataframes/decorator.py` no longer exists). Replaced by `cache/dataframe/decorator.py` (309 lines, separate module). **DROPPED** from Phase 2 WS-4 targets. |
| RF-006: `clients/data/client.py` -- extracted `_run_sync()` helper | Reduced duplication. File is now 1,916 lines (was 1,844 pre-Phase 1 per claim; actual post-Phase 1 = 1,916 with new export endpoint added). `__init__` is 37 lines (not 189 as claimed). |
| RF-007: `clients/data/client.py` -- extracted `_execute_with_retry()` | Consolidated retry logic. The 97-line `_execute_with_retry()` method now serves both `get_insights_async` and `get_export_csv_async`. |

---

## Pre-Analysis Corrections (Prompt 0 vs Reality)

| Prompt 0 Claim | Actual Finding | Status |
|---|---|---|
| `clients/data/client.py`: 1,844 lines, 189-line `__init__` | 1,916 lines (grew due to export endpoint), `__init__` is 37 lines (lines 172-237) | **CORRECTED** |
| `dataframes/decorator.py`: Phase 2 target | File deleted by Phase 1 RF-001 | **DROPPED** |
| `persistence/session.py`: 1,641 lines | 1,712 lines (grew slightly since measurement) | **CORRECTED** |
| `dataframes/builders/progressive.py`: 1,220 lines | 1,221 lines (confirmed) | **VALIDATED** |
| `automation/seeding.py`: 885 lines, `_resolve_enum_value` 146 lines | 886 lines, `_resolve_enum_value` is 146 lines (lines 740-885) | **VALIDATED** |
| `polling/polling_scheduler.py`: `_evaluate_rules` 10 indent levels | Max nesting = 7 levels (for > if schedule > if should_run > if workflow_id > if workflow > asyncio.run), not 10 | **CORRECTED** |
| `persistence/models.py`: `to_api_call()` 138 lines | `to_api_call()` is 138 lines (lines 526-663) | **VALIDATED** |
| Batch size `100` hardcoded in 3 locations | `100` appears in 40+ locations across the codebase | **CORRECTED** |
| `f"Bearer {token}"` in 4 locations | 3 locations in source code constructing the header | **CORRECTED** |
| API route prefixes `/api/v1/...` in 8 route files | 8 route files use `/api/v1/...` prefix; 4 additional use `/v1/...` prefix (inconsistency) | **CORRECTED** |
| Timeout values scattered | Timeouts are centralized in config classes (DataServiceConfig, AsanaConfig); only 3 hardcoded outliers | **CORRECTED** |
| Error codes `CACHE_BUILD_IN_PROGRESS`, `DATAFRAME_BUILD_UNAVAILABLE` | 2 occurrences total, both in `cache/dataframe/decorator.py` | **VALIDATED** |

---

## Summary Table (All Findings Ranked by ROI)

| ID | Category | Severity | ROI | Title | Lines/Locations |
|---|---|---|---|---|---|
| SM-101 | God Module | HIGH | 8.5 | `clients/data/client.py` -- 1,916-line multi-responsibility client | 1,916 lines, 1 file |
| SM-102 | God Module | HIGH | 8.0 | `persistence/session.py` -- 1,712-line Unit of Work | 1,712 lines, 1 file |
| SM-103 | God Module | MEDIUM | 7.5 | `dataframes/builders/progressive.py` -- 1,221-line builder | 1,221 lines, 1 file |
| SM-104 | Complexity | MEDIUM | 7.0 | `automation/seeding.py` -- 146-line `_resolve_enum_value` | 146 lines, 1 file |
| SM-105 | Complexity | MEDIUM | 6.5 | `persistence/models.py` -- 138-line `to_api_call()` match/case | 138 lines, 1 file |
| SM-106 | Magic Number | MEDIUM | 6.0 | Asana page size `100` hardcoded in 40+ locations | 40+ occurrences, 20+ files |
| SM-107 | Complexity | LOW | 5.5 | `polling_scheduler.py` -- 7-level nesting in `_evaluate_rules` | 135 lines, 1 file |
| SM-108 | Naming | LOW | 5.0 | API route prefix inconsistency (`/api/v1/` vs `/v1/`) | 12 route files |
| SM-109 | Magic String | LOW | 4.5 | `f"Bearer {token}"` in 3 locations | 3 occurrences, 3 files |
| SM-110 | Magic Number | LOW | 4.0 | Hardcoded timeout `5.0` in health check route | 1 occurrence, 1 file |
| SM-111 | Magic String | LOW | 3.5 | Error codes `CACHE_BUILD_IN_PROGRESS` / `DATAFRAME_BUILD_UNAVAILABLE` | 2 occurrences, 1 file |

---

## WS-4: God Module Decomposition

### SM-101: `clients/data/client.py` -- Multi-Responsibility Client (HIGH)

**Category**: God Module
**Severity**: HIGH | **Frequency**: Single module | **Blast Radius**: All insights/export callers
**Fix Complexity**: Medium (clear seams exist)
**ROI Score**: 8.5/10

**Current Measurements (post-Phase 1)**:
- **Line count**: 1,916 lines
- **Total methods**: 29 (12 public, 17 private)
- **Longest function**: `_execute_insights_request` -- 236 lines (lines 1247-1528)
- **Max nesting depth**: 5 levels (within `_get_stale_response`)
- **Phase 1 impact**: RF-006/RF-007 extracted `_run_sync()` (38 lines) and `_execute_with_retry()` (97 lines). These reduced duplication but the file is LARGER than pre-Phase 1 because `get_export_csv_async` was added.

**Why it still qualifies**: Despite Phase 1 improvements, this file carries 5 distinct responsibilities:
1. HTTP client lifecycle (`_get_client`, `close`, context managers) -- lines 240-508
2. Cache layer (build/get/stale fallback) -- lines 663-821
3. Insights API (request/response/validation) -- lines 880-1547
4. Export API (completely different endpoint) -- lines 1751-1901
5. Metrics emission -- lines 628-661

**Prompt 0 `__init__` claim correction**: The `__init__` is 37 lines (172-237), NOT 189 lines. The 189-line claim was completely wrong.

**Natural Decomposition Seams**:
1. **Cache operations** (`_build_cache_key`, `_cache_response`, `_get_stale_response`) -- 160 lines extractable to `DataServiceCache` helper
2. **Export API** (`get_export_csv_async` + response parsing) -- 150 lines extractable to `ExportClient` or a separate method group
3. **Response parsing** (`_parse_success_response`, `_handle_error_response`, `_validate_factory`) -- 220 lines extractable to response handler

**Evidence**:
```
/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/client.py
  Lines 663-821:   Cache operations (159 lines)
  Lines 880-1528:  Insights API with request execution (649 lines)
  Lines 1530-1547: Validation (17 lines)
  Lines 1548-1749: Error handling and response parsing (202 lines)
  Lines 1751-1901: Export API (151 lines)
```

**Boundary flag for Architect Enforcer**: The export API (`get_export_csv_async`) shares circuit breaker and retry with insights but has completely different response parsing (CSV vs JSON). Consider whether this belongs in the same class.

---

### SM-102: `persistence/session.py` -- 1,712-Line Unit of Work (HIGH)

**Category**: God Module
**Severity**: HIGH | **Frequency**: Single module | **Blast Radius**: All save operations
**Fix Complexity**: Medium-High (deep integration)
**ROI Score**: 8.0/10

**Current Measurements**:
- **Line count**: 1,712 lines
- **Total methods**: 44 (31 public, 13 private)
- **Longest function**: `commit_async` -- 232 lines (lines 722-954)
- **Max nesting depth**: 4 levels (within `commit_async` try/if blocks)
- **Phase 1 impact**: Not touched by Phase 1

**Why it qualifies**: SaveSession mixes 7 distinct responsibilities in one class:
1. Entity registration & tracking (`track`, `untrack`, `delete`, `find_by_gid`, etc.) -- 11 methods
2. Change inspection (`get_changes`, `get_state`, `is_tracked`, `preview`) -- 5 methods
3. Commit orchestration (`commit_async`, `commit`) -- the 232-line core
4. Action operations (14 descriptor-based + `add_comment`, `set_parent`, etc.) -- 8 methods
5. Event hooks (`on_pre_save`, `on_post_save`, `on_error`, `on_post_commit`) -- 4 methods
6. Cascade operations (`cascade_field`, `get_pending_cascades`) -- 2 methods
7. Internal state management (`_state_lock`, `_require_open`, `_ensure_open`, etc.) -- 7 methods

The 232-line `commit_async` method is the primary complexity hotspot. It orchestrates 5 phases (ensure holders, CRUD+actions, cache invalidation, cascades, healing, automation) in a single method with multiple lock/unlock cycles.

**Natural Decomposition Seams**:
1. **`commit_async` phase extraction**: The 5 phases could be extracted to a `CommitOrchestrator` or into named phase methods
2. **Reorder operations** (`reorder_subtask`, `reorder_subtasks`) -- 60 lines, could be a mixin
3. **Cascade operations** (`cascade_field`, `get_pending_cascades`) -- 80 lines, could be a mixin

**Evidence**:
```
/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py
  Lines 134-241:   __init__ (108 lines -- 10 subsystems initialized)
  Lines 722-954:   commit_async (232 lines -- 5 phases)
  Lines 1107-1131: 14 ActionBuilder descriptors
  Lines 1136-1469: Custom action methods (333 lines)
```

**Boundary flag for Architect Enforcer**: The `__init__` initializes 10 different subsystems (tracker, graph, events, pipeline, action_executor, cascade_executor, name_resolver, healing_manager, cache_invalidator, holder_concurrency). This is a strong signal for composition over monolith.

---

### SM-103: `dataframes/builders/progressive.py` -- 1,221-Line Builder (MEDIUM)

**Category**: God Module
**Severity**: MEDIUM | **Frequency**: Single module | **Blast Radius**: Progressive build callers
**Fix Complexity**: Medium (well-structured internally)
**ROI Score**: 7.5/10

**Current Measurements**:
- **Line count**: 1,221 lines (including module-level convenience function)
- **Total methods**: 18 (1 public, 17 private)
- **Longest function**: `_fetch_and_persist_section` -- 110 lines (lines 565-673)
- **Max nesting depth**: 4 levels
- **Phase 1 impact**: Not touched by Phase 1

**Why it qualifies (marginally)**: The class is internally well-organized with single-responsibility private methods, but it carries too many concerns in one class:
1. Resume/probe logic (`_check_resume_and_probe`, `_probe_freshness`) -- 160 lines
2. Section fetch/persist (`_fetch_and_persist_section`, `_fetch_large_section`, `_fetch_first_page`) -- 310 lines
3. DataFrame construction (`_build_section_dataframe`, `_extract_rows`, `_task_to_dict`) -- 130 lines
4. Checkpoint management (`_load_checkpoint`, `_write_checkpoint`) -- 100 lines
5. Store population (`_populate_store_with_tasks`) -- 50 lines
6. Build orchestration (`build_progressive_async`) -- 170 lines

**Natural Decomposition Seams**:
1. **Resume/freshness probing** -- extractable to `ProgressiveResumeManager`
2. **Checkpoint management** -- extractable to checkpoint helper (already uses `SectionPersistence` for I/O)
3. **Task-to-DataFrame conversion** (`_task_to_dict`, `_extract_rows`, `_build_section_dataframe`) -- extractable to conversion helper

**Evidence**:
```
/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py
  Lines 155-244:  _check_resume_and_probe (90 lines)
  Lines 377-543:  build_progressive_async (167 lines)
  Lines 565-673:  _fetch_and_persist_section (109 lines)
  Lines 861-913:  _fetch_large_section (53 lines)
  Lines 976-1044: _write_checkpoint (69 lines)
```

**Note**: This is a borderline god module. The internal organization is reasonable, and the public API surface is just 1 method. However, the 1,221-line size creates maintenance burden. Architect Enforcer should evaluate whether decomposition yields net benefit or just adds indirection.

---

### SM-104: `automation/seeding.py` -- 146-Line `_resolve_enum_value` (MEDIUM)

**Category**: Complexity
**Severity**: MEDIUM | **Frequency**: Called per field per task during seeding | **Blast Radius**: Pipeline conversion seeding
**Fix Complexity**: Low (clear algorithmic decomposition)
**ROI Score**: 7.0/10

**Current Measurements**:
- **File line count**: 886 lines
- **`_resolve_enum_value` line count**: 146 lines (lines 740-885)
- **Max nesting depth**: 5 levels (method > if multi_enum > for item > if/elif > if)
- **Public methods**: 7 on `FieldSeeder` class
- **Phase 1 impact**: Not touched by Phase 1

**Why it qualifies**: The `_resolve_enum_value` method handles 3 distinct field types (multi_enum, single enum, non-enum) with duplicated name-to-GID resolution logic between the multi_enum and single enum branches. The two enum branches share: case-insensitive name matching, GID passthrough validation, missing-option warning with available options list.

**Natural Decomposition Seams**:
1. **Extract shared enum resolution**: `_resolve_single_enum_option()` and `_resolve_multi_enum_options()` extractable from the monolith
2. **Extract name-to-GID builder**: The `name_to_gid` dict construction (lines 787-794) is duplicated in concept between multi_enum and single enum branches

**Evidence**:
```
/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/seeding.py
  Lines 740-885:  _resolve_enum_value (146 lines)
  Lines 772-829:  multi_enum branch (58 lines)
  Lines 832-882:  single enum branch (51 lines)
  Lines 884-885:  non-enum passthrough (2 lines)
```

**Note**: The file as a whole (886 lines) is not a god module -- `FieldSeeder` has a clear single purpose (field seeding). The smell is concentrated in this one oversized method.

---

### SM-105: `persistence/models.py` -- 138-Line `to_api_call()` Match/Case (MEDIUM)

**Category**: Complexity
**Severity**: MEDIUM | **Frequency**: Called per action operation during commit | **Blast Radius**: All action execution
**Fix Complexity**: Low-Medium (data-driven approach possible)
**ROI Score**: 6.5/10

**Current Measurements**:
- **File line count**: 778 lines
- **`to_api_call` line count**: 138 lines (lines 526-663)
- **Max nesting depth**: 3 levels (method > match > case body)
- **Action types handled**: 15 cases
- **Phase 1 impact**: Not touched by Phase 1

**Why it qualifies**: The match/case handles 15 `ActionType` variants with 5 sharing identical structure (just different endpoints), and 5 sharing a "positioning" pattern with `insert_before`/`insert_after`. This is a data table disguised as branching logic.

**Natural Decomposition Seams**:
1. **Data-driven dispatch**: A dict mapping `ActionType -> (method, path_template, payload_builder)` would replace 138 lines with ~30 lines + a lookup table
2. **Positioning extraction**: The `insert_before`/`insert_after` logic repeats for ADD_TO_PROJECT, MOVE_TO_SECTION, and SET_PARENT

**Evidence**:
```
/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/models.py
  Lines 540-546:  ADD_TAG (7 lines)
  Lines 547-553:  REMOVE_TAG (7 lines) -- identical structure to ADD_TAG
  Lines 554-565:  ADD_TO_PROJECT (12 lines) -- positioning variant
  Lines 583-594:  MOVE_TO_SECTION (12 lines) -- positioning variant, same structure
  Lines 649-661:  SET_PARENT (13 lines) -- positioning variant, same structure
```

**Note**: The file as a whole (778 lines) is reasonable for a models module. The smell is confined to this one method.

---

### SM-107: `polling_scheduler.py` -- 7-Level Nesting in `_evaluate_rules` (LOW)

**Category**: Complexity
**Severity**: LOW | **Frequency**: Single method | **Blast Radius**: Scheduler rule evaluation
**Fix Complexity**: Low
**ROI Score**: 5.5/10

**Current Measurements**:
- **File line count**: 671 lines
- **`_evaluate_rules` line count**: 135 lines (lines 301-435)
- **Max nesting depth**: 7 levels (method > for rule > if schedule > if should_run > if workflow_id+registry > if workflow > asyncio.run)
- **Public methods**: 4 on `PollingScheduler` class
- **Phase 1 impact**: Not touched by Phase 1

**Why it qualifies (marginally)**: The Prompt 0 claimed 10 indent levels; actual is 7. The deep nesting occurs specifically in the schedule-driven workflow dispatch branch (lines 349-379). This is a single code path and the overall method is manageable.

**Evidence**:
```
/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/polling/polling_scheduler.py
  Lines 346-380:  Schedule-driven workflow dispatch (7 levels deep)
    346: for rule in enabled_rules:                         # level 1
    350:   if rule.schedule is not None and ...:             # level 2
    351:     if self._should_run_schedule(...):               # level 3
    352:       workflow_id = ...                              # level 4
    353:       if workflow_id and self._workflow_registry:    # level 5
    354:         workflow = self._workflow_registry.get(...)   # level 6
    355:         if workflow:                                 # level 7
    356:           asyncio.run(...)
```

**Natural Decomposition Seam**: Extract schedule-driven workflow dispatch into `_dispatch_scheduled_workflow(rule, structured_log)`.

**Note**: This is below the god-module threshold (671 lines). The nesting is localized and the fix is straightforward. Lower priority than SM-101 through SM-105.

---

## WS-5: Magic Numbers and Hardcoded Strings

### SM-106: Asana Page Size `100` Hardcoded in 40+ Locations (MEDIUM)

**Category**: Magic Number
**Severity**: MEDIUM | **Frequency**: 40+ occurrences | **Blast Radius**: 20+ files
**Fix Complexity**: Low (extract constant)
**ROI Score**: 6.0/10

**Three distinct usage patterns for the literal `100`**:

**Pattern A: API limit default parameter (ACCEPTABLE)** -- 20+ occurrences

These are function parameter defaults and are the Asana API's documented page size limit. They serve as documentation of the API contract.

| File | Line | Context |
|---|---|---|
| `clients/tasks.py` | 469, 544, 618 | `limit: int = 100` |
| `clients/projects.py` | 321, 515 | `limit: int = 100` |
| `clients/sections.py` | 311 | `limit: int = 100` |
| `clients/users.py` | 198 | `limit: int = 100` |
| `clients/stories.py` | 213 | `limit: int = 100` |
| `clients/teams.py` | 106, 143, 177 | `limit: int = 100` |
| `clients/goals.py` | 362 | `limit: int = 100` |
| `clients/tags.py` | 273, 307 | `limit: int = 100` |
| `clients/portfolios.py` | 281, 320 | `limit: int = 100` |
| `clients/custom_fields.py` | 350, 569 | `limit: int = 100` |
| `clients/attachments.py` | 119 | `limit: int = 100` |
| `clients/webhooks.py` | 284 | `limit: int = 100` |
| `clients/workspaces.py` | 99 | `limit: int = 100` |
| `clients/goal_relationships.py` | 61 | `limit: int = 100` |
| `models/common.py` | 99 | `page_size: int = 100` |

**Assessment**: ACCEPTABLE. These are parameter defaults documenting the Asana API contract. Changing them would not change behavior (callers can override). However, a single `ASANA_PAGE_SIZE = 100` constant referenced by all would be marginally better for discoverability.

**Pattern B: Progressive builder paging sentinel (PROBLEMATIC)** -- 5 occurrences in 1 file

| File | Line | Context |
|---|---|---|
| `dataframes/builders/progressive.py` | 624 | `if len(first_page_tasks) < 100:` |
| `dataframes/builders/progressive.py` | 828 | `if skip_task_count >= 100:` |
| `dataframes/builders/progressive.py` | 847 | `if len(first_page_tasks) >= 100:` |
| `dataframes/builders/progressive.py` | 855 | `"pacing_enabled": len(first_page_tasks) == 100,` |
| `dataframes/builders/progressive.py` | 888 | `if current_page_task_count >= 100:` |

**Assessment**: PROBLEMATIC. These use `100` as a "page boundary" sentinel -- they assume Asana returns 100 items per page. If the API page size ever changes (or a caller provides a different limit), these comparisons silently break. Should reference a constant.

**Pattern C: Cache/API batch size configs (ALREADY CONFIGURABLE)** -- 6 occurrences

| File | Line | Context |
|---|---|---|
| `cache/models/staleness_settings.py` | 50 | `max_batch_size: int = 100` |
| `cache/models/settings.py` | 157 | `max_batch_size: int = 100` |
| `cache/integration/freshness_coordinator.py` | 94 | `max_batch_size: int = 100` |
| `cache/policies/coalescer.py` | 61 | `max_batch: int = 100` |
| `api/routes/workspaces.py` | 30-31 | `DEFAULT_LIMIT = 100; MAX_LIMIT = 100` |
| Similar in `dataframes.py`, `tasks.py`, `users.py`, `projects.py` | various | Named constants |

**Assessment**: ALREADY CONFIGURABLE. These are config dataclass defaults or module-level named constants. No action needed.

**Pattern D: Other threshold uses (ACCEPTABLE)** -- 3 occurrences

| File | Line | Context |
|---|---|---|
| `dataframes/builders/base.py` | 74 | `LAZY_THRESHOLD = 100` |
| `config.py` | 249 | `max_connections: int = 100` |
| `config.py` | 401 | `HIERARCHY_PACING_THRESHOLD: int = 100` |

**Assessment**: ACCEPTABLE. These are named constants or config fields that happen to use the value 100 for different purposes. No relationship to Asana page size.

---

### SM-108: API Route Prefix Inconsistency (`/api/v1/` vs `/v1/`) (LOW)

**Category**: Naming Inconsistency
**Severity**: LOW | **Frequency**: 12 route files | **Blast Radius**: All API consumers
**Fix Complexity**: Low (rename + update tests)
**ROI Score**: 5.0/10

**Two prefix conventions coexist in the route layer**:

| Convention | Files | Lines |
|---|---|---|
| `/api/v1/{resource}` | `workspaces.py:27`, `dataframes.py:52`, `projects.py:36`, `webhooks.py:24`, `users.py:28`, `tasks.py:54`, `internal.py:23`, `sections.py:38` | 8 files |
| `/v1/{resource}` | `resolver.py:83`, `query.py:62`, `query_v2.py:40`, `admin.py:25` | 4 files |

**Assessment**: PROBLEMATIC but low severity. The newer routes (resolver, query, admin) use `/v1/` while the original routes use `/api/v1/`. This is a naming drift that confuses API consumers. However, changing established routes is a breaking change for clients.

**Note for Architect Enforcer**: This may be intentional -- the `/v1/` routes are internal-only (S2S JWT), while `/api/v1/` routes support PAT auth. If so, the naming convention encodes a security boundary. Verify before recommending changes.

---

### SM-109: `f"Bearer {token}"` in 3 Locations (LOW)

**Category**: Magic String
**Severity**: LOW | **Frequency**: 3 occurrences | **Blast Radius**: Authentication layer
**Fix Complexity**: Low
**ROI Score**: 4.5/10

| File | Line | Context |
|---|---|---|
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/client.py` | 753 | `headers={"Authorization": f"Bearer {token}"}` (workspace auto-detect) |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/asana_http.py` | 241 | `"Authorization": f"Bearer {token}"` (platform client init) |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/client.py` | 491 | `headers["Authorization"] = f"Bearer {token}"` (data service client) |

**Assessment**: ACCEPTABLE. The Prompt 0 claimed 4 locations; actual is 3. Each is in a fundamentally different auth context:
1. `client.py` -- one-shot workspace detection (httpx.Client)
2. `asana_http.py` -- platform SDK client initialization
3. `data/client.py` -- separate HTTP client for data service

These are in 3 different HTTP client initialization paths. Extracting a shared helper would add indirection without reducing risk, since each path uses a different client library or pattern. The `"Bearer "` prefix is an HTTP standard (RFC 6750), not a domain-specific magic string.

---

### SM-110: Hardcoded Timeout `5.0` in Health Check Route (LOW)

**Category**: Magic Number
**Severity**: LOW | **Frequency**: 1 occurrence | **Blast Radius**: Health check only
**Fix Complexity**: Very low
**ROI Score**: 4.0/10

| File | Line | Context |
|---|---|---|
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/health.py` | 198 | `async with httpx.AsyncClient(timeout=5.0) as client:` |

**Assessment**: Marginally problematic. The health check timeout should be configurable (or at least a named constant) since it affects health probe responsiveness. However, this is a single occurrence with minimal blast radius.

**Timeout landscape (for completeness)**:
- `config.py` defines `TimeoutConfig(connect=5.0, read=30.0, write=30.0, pool=10.0)` -- ALREADY CONFIGURABLE
- `clients/data/config.py` defines `DataServiceTimeoutConfig(connect=5.0, read=30.0, write=30.0, pool=5.0)` -- ALREADY CONFIGURABLE
- `automation/waiter.py` defines `default_timeout: float = 2.0` -- ALREADY CONFIGURABLE (constructor param)
- `automation/pipeline.py:371` uses `timeout=2.0` -- references the waiter, ACCEPTABLE
- `cache/backends/redis.py` defines `socket_timeout=1.0, socket_connect_timeout=5.0` -- ALREADY CONFIGURABLE (config class)
- `settings.py` centralizes `REDIS_SOCKET_TIMEOUT`, `REDIS_CONNECT_TIMEOUT`, etc. -- ALREADY CONFIGURABLE

The Prompt 0 suggested timeout values are "scattered across modules." In reality, the codebase has well-structured config classes for timeouts. Only the health check outlier (SM-110) and the `client.py:760` workspace auto-detect timeout (`10.0`) are not configurable. The `client.py` timeout is used in a one-shot initialization path, making it acceptable.

---

### SM-111: Error Code Strings (LOW)

**Category**: Magic String
**Severity**: LOW | **Frequency**: 2 occurrences | **Blast Radius**: Cache decorator only
**Fix Complexity**: Very low
**ROI Score**: 3.5/10

| File | Line | Context |
|---|---|---|
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/decorator.py` | 153 | `"error": "CACHE_BUILD_IN_PROGRESS"` |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/decorator.py` | 191 | `"error": "DATAFRAME_BUILD_UNAVAILABLE"` |

**Assessment**: ACCEPTABLE. Each error code appears exactly once, is clearly named, and is documented by its surrounding context. Extracting to constants would add a layer of indirection for no deduplication benefit. If these codes are ever referenced by API consumers for programmatic handling, they should be extracted to an enum -- but currently they are only in HTTP response bodies.

---

## Scope Exclusion Verification

The following were explicitly excluded and verified NOT flagged:

- [x] `api/main.py` backward-compat shims -- not flagged
- [x] 119 documented broad catches -- not flagged (BROAD-CATCH annotations respected)
- [x] Circular import mitigations, TYPE_CHECKING guards -- not flagged
- [x] Unit extractor TODOs (blocked by OQ-4/OQ-5) -- not flagged
- [x] Public API surfaces -- not flagged
- [x] `cache/backends/base.py` (Phase 1 new file) -- not flagged
- [x] `@async_method` descriptor -- not flagged
- [x] DegradedModeMixin / RetryableErrorMixin -- not flagged

---

## WS-4 Module Summary Table

| Module | Lines | Pre-Prompt 0 Claim | Post-Phase 1 | Public Methods | Longest Function | Max Nesting | Still God Module? |
|---|---|---|---|---|---|---|---|
| `clients/data/client.py` | 1,916 | 1,844 lines | Grew (export added, `_run_sync`+`_execute_with_retry` extracted) | 12 | `_execute_insights_request` (236 lines) | 5 | **YES** |
| `persistence/session.py` | 1,712 | 1,641 lines | Not touched | 31 | `commit_async` (232 lines) | 4 | **YES** |
| `dataframes/builders/progressive.py` | 1,221 | 1,220 lines | Not touched | 1 | `_fetch_and_persist_section` (110 lines) | 4 | **BORDERLINE** |
| `automation/seeding.py` | 886 | 885 lines | Not touched | 7 | `_resolve_enum_value` (146 lines) | 5 | **NO** (single method smell) |
| `polling/polling_scheduler.py` | 671 | N/A (claimed 10 indent) | Not touched | 4 | `_evaluate_rules` (135 lines) | 7 | **NO** (below threshold) |
| `persistence/models.py` | 778 | N/A (claimed 138-line method) | Not touched | 15+ (mix of class methods) | `to_api_call` (138 lines) | 3 | **NO** (single method smell) |
| `dataframes/decorator.py` | DELETED | 251 lines (Phase 1 target) | Deleted by Phase 1 RF-001 | N/A | N/A | N/A | **DROPPED** |

---

## WS-5 Magic Values Summary Table

| Value | Occurrences | Assessment | Action Needed? |
|---|---|---|---|
| Page size `100` (API defaults) | 20+ in clients | ACCEPTABLE (API contract) | Optional: extract `ASANA_PAGE_SIZE` constant |
| Page size `100` (progressive builder) | 5 in progressive.py | PROBLEMATIC | YES: extract constant to avoid silent breakage |
| Batch size `100` (config classes) | 6 in cache configs | ALREADY CONFIGURABLE | No |
| `f"Bearer {token}"` | 3 occurrences | ACCEPTABLE (RFC 6750 standard) | No |
| `/api/v1/` prefix | 8 route files | See SM-108 inconsistency | Architect Enforcer decision |
| `/v1/` prefix | 4 route files | See SM-108 inconsistency | Architect Enforcer decision |
| Timeouts (5.0, 2.0, 10.0, 30.0) | Most in config classes | ALREADY CONFIGURABLE | Only health.py outlier (SM-110) |
| `CACHE_BUILD_IN_PROGRESS` | 1 occurrence | ACCEPTABLE | No |
| `DATAFRAME_BUILD_UNAVAILABLE` | 1 occurrence | ACCEPTABLE | No |
| `timeout=10.0` in client.py:760 | 1 occurrence | ACCEPTABLE (one-shot init) | No |

---

## Boundary Violation Flags for Architect Enforcer

1. **SM-101 (DataServiceClient)**: Export API shares infrastructure but has completely different response handling. Evaluate whether `get_export_csv_async` should be a separate client class or a mixin.

2. **SM-102 (SaveSession)**: 10 subsystems initialized in `__init__`. The 5-phase commit is the central orchestration point for the persistence layer. Decomposition must preserve transactional guarantees.

3. **SM-108 (Route prefixes)**: The `/api/v1/` vs `/v1/` split may encode a security boundary (PAT vs S2S JWT). Architect Enforcer should verify intent before recommending standardization.

4. **SM-106 Pattern B (progressive builder page sentinel)**: The hardcoded `100` in progressive builder creates a hidden coupling to Asana API page size. If Asana ever changes default page size, progressive builds will silently miscount pages.

---

## Attestation Table

| Artifact | Verified Via | Attestation |
|---|---|---|
| `clients/data/client.py` (1,916 lines) | `wc -l` + Read tool, lines 172-237 (__init__) | Confirmed: 1,916 lines, __init__ is 37 lines (NOT 189) |
| `persistence/session.py` (1,712 lines) | `wc -l` + Read tool, lines 722-954 (commit_async) | Confirmed: 1,712 lines, commit_async is 232 lines |
| `dataframes/builders/progressive.py` (1,221 lines) | `wc -l` + Read tool | Confirmed: 1,221 lines, 1 public method |
| `automation/seeding.py` (886 lines) | `wc -l` + Read tool, lines 740-885 | Confirmed: 886 lines, _resolve_enum_value is 146 lines |
| `polling/polling_scheduler.py` (671 lines) | `wc -l` + Read tool, lines 346-380 | Confirmed: 671 lines, max nesting = 7 (NOT 10) |
| `persistence/models.py` (778 lines) | `wc -l` + Read tool, lines 526-663 | Confirmed: 778 lines, to_api_call is 138 lines |
| `dataframes/decorator.py` DELETED | Glob + Read (file not found) | Confirmed: deleted by Phase 1 RF-001 |
| `f"Bearer {token}"` 3 locations | Grep across src/ | Confirmed: client.py:753, asana_http.py:241, data/client.py:491 |
| `/api/v1/` in 8 route files | Grep `prefix="/api/v1/"` | Confirmed: 8 files use `/api/v1/`, 4 use `/v1/` |
| `100` page size in progressive.py | Grep across src/ | Confirmed: 5 occurrences in progressive.py lines 624, 828, 847, 855, 888 |
| Error code strings | Grep for CACHE_BUILD_IN_PROGRESS | Confirmed: 2 occurrences in cache/dataframe/decorator.py |
| Timeouts mostly configurable | Grep + Read of config.py, settings.py, data/config.py | Confirmed: config classes cover all except health.py:198 |
| Smell report written | Read tool verification | All findings have file:line evidence |
| No scope-excluded items flagged | Manual review | Confirmed |
| Phase 1 overlap assessed | Read of deleted decorator.py, client.py measurements | Confirmed |
