---
type: audit
---

# Detection Report: Section Timeline Architecture Remediation

**Agent**: hallucination-hunter
**Scope**: 12 files -- Section Timeline Architecture Remediation (8 source, 4 test)
**Date**: 2026-02-20
**Mode**: Interactive

---

## Executive Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 1 |
| LOW | 0 |

All 12 files in scope passed import resolution and API surface verification. No hallucinated imports, phantom dependencies, or non-existent API calls were detected. All cross-file references resolve correctly. `DerivedTimelineCacheEntry` is properly registered in the entry type class map via `__init_subclass__`. All newly exported symbols exist in their declared modules.

One MEDIUM finding: tests import private (underscore-prefixed) symbols directly from `derived.py`. These symbols exist and the imports resolve -- this is a test coupling advisory, not a broken reference.

**Verdict**: No blocking defects. Ready for logic-surgeon.

---

## Scan Results by File

### 1. `src/autom8_asana/cache/integration/derived.py` (NEW FILE)

**Imports verified:**

| Import | Source | Status |
|--------|--------|--------|
| `from datetime import UTC, datetime` | stdlib | PASS |
| `from typing import TYPE_CHECKING, Any` | stdlib | PASS |
| `from autom8_asana.cache.models.entry import DerivedTimelineCacheEntry, EntryType` | `entry.py` lines 587, 20 | PASS |
| `from autom8_asana.models.business.section_timeline import SectionInterval, SectionTimeline` | `section_timeline.py` lines 20, 42 | PASS |
| `from autom8_asana.protocols.cache import CacheProvider` (TYPE_CHECKING only) | `protocols/cache.py` line 18 | PASS |
| Lazy: `from autom8_asana.models.business.activity import AccountActivity` | `activity.py` line 24 | PASS |

**API calls verified:**

| Call | Target | Status |
|------|--------|--------|
| `cache.get_versioned(key, EntryType.DERIVED_TIMELINE)` | `CacheProvider.get_versioned(key, entry_type, freshness=None)` -- `protocols/cache.py` line 76 | PASS |
| `cache.set_versioned(key, entry)` | `CacheProvider.set_versioned(key, entry)` -- `protocols/cache.py` line 95 | PASS |
| `DerivedTimelineCacheEntry(key=..., data=..., entry_type=..., version=..., cached_at=..., ttl=..., project_gid=..., metadata=..., classifier_name=..., source_entity_count=..., source_cache_hits=..., source_cache_misses=..., computation_duration_ms=...)` | All fields declared in `entry.py` lines 600-609 | PASS |
| `EntryType.DERIVED_TIMELINE` | `entry.py` line 55 | PASS |
| `AccountActivity(cls_value)` | `AccountActivity` is `str, Enum` -- valid enum construction by value | PASS |
| `SectionInterval(section_name=..., classification=..., entered_at=..., exited_at=...)` | `section_timeline.py` lines 33-38 | PASS |
| `SectionTimeline(offer_gid=..., office_phone=..., intervals=..., task_created_at=..., story_count=...)` | `section_timeline.py` lines 55-59 | PASS |
| `iv.classification.value` | `AccountActivity` is `str, Enum` -- `.value` is a valid `Enum` attribute | PASS |
| `timeline.offer_gid`, `.office_phone`, `.intervals`, `.task_created_at`, `.story_count` | `SectionTimeline` dataclass fields lines 55-59 | PASS |
| `iv.section_name`, `.classification`, `.entered_at`, `.exited_at` | `SectionInterval` dataclass fields lines 33-38 | PASS |
| `datetime.fromisoformat(...)` | stdlib `datetime` | PASS |
| `datetime.now(UTC)` | stdlib `datetime` | PASS |

**Findings**: None.

---

### 2. `src/autom8_asana/cache/integration/stories.py` (MODIFIED)

Added public functions: `read_cached_stories` (line 35), `read_stories_batch` (line 62).

**Imports for new functions** are already present in the file header: `CacheEntry`, `EntryType` (line 13), `CacheProvider` (TYPE_CHECKING, line 17).

**API calls in new functions:**

| Call | Target | Status |
|------|--------|--------|
| `cache.get_versioned(task_gid, EntryType.STORIES)` | `CacheProvider.get_versioned` -- `protocols/cache.py` line 76 | PASS |
| `cache.get_batch(chunk, EntryType.STORIES)` | `CacheProvider.get_batch(keys, entry_type)` -- `protocols/cache.py` line 108 | PASS |
| `_extract_stories_list(cached_entry.data)` | Defined at line 207 of same file | PASS |
| `EntryType.STORIES` | `entry.py` line 31 | PASS |

**Findings**: None.

---

### 3. `src/autom8_asana/cache/models/entry.py` (MODIFIED)

Added: `DERIVED_TIMELINE` enum member (line 55), `DerivedTimelineCacheEntry` subclass (lines 587-640).

**Registration verified:**

`DerivedTimelineCacheEntry` class statement at line 588:
```python
class DerivedTimelineCacheEntry(
    CacheEntry,
    entry_types=(EntryType.DERIVED_TIMELINE,),
):
```
The `__init_subclass__` hook (line 114) auto-registers `CacheEntry._type_registry["derived_timeline"] = DerivedTimelineCacheEntry`. The `from_dict` dispatch correctly routes `_type == "derived_timeline"` to `DerivedTimelineCacheEntry._from_dict_impl`. PASS.

**`_parse_datetime` reference:**

`CacheEntry.is_current` calls `_parse_datetime` at lines 165-166. `_parse_datetime` is defined in the same module at line 249. PASS.

**Findings**: None.

---

### 4. `src/autom8_asana/services/section_timeline_service.py` (MODIFIED)

Added: `get_or_compute_timelines` (line 336), `_compute_day_counts` (line 567), `_get_computation_lock` (line 50), `_computation_locks` (line 47), `BUSINESS_OFFERS_PROJECT_GID` (line 65).

**Top-level imports verified:**

| Import | Source | Status |
|--------|--------|--------|
| `import asyncio` | stdlib | PASS |
| `import time as time_module` | stdlib | PASS |
| `from collections import defaultdict` | stdlib | PASS |
| `from datetime import date, datetime` | stdlib | PASS |
| `from autom8y_log import get_logger` | installed package | PASS |
| `from autom8_asana.client import AsanaClient` | `client.py` line 50 | PASS |
| `from autom8_asana.models.business.activity import CLASSIFIERS, OFFER_CLASSIFIER, AccountActivity, SectionClassifier, extract_section_name` | `activity.py` lines 264, 187, 24, 53, 138 | PASS |
| `from autom8_asana.models.business.section_timeline import OfferTimelineEntry, SectionInterval, SectionTimeline` | `section_timeline.py` lines 157, 20, 42 | PASS |
| `from autom8_asana.models.story import Story` | `story.py` line 17 -- Pydantic v2 BaseModel subclass | PASS |
| `from autom8_asana.protocols.cache import CacheProvider` (TYPE_CHECKING) | `protocols/cache.py` line 18 | PASS |

**Locally imported symbols in `get_or_compute_timelines` body:**

| Import | Source | Status |
|--------|--------|--------|
| `from autom8_asana.cache.integration.derived import _deserialize_timeline` | `derived.py` line 147 | PASS |
| `from autom8_asana.cache.integration.derived import _serialize_timeline` | `derived.py` line 114 | PASS |
| `from autom8_asana.cache.integration.derived import get_cached_timelines` | `derived.py` line 44 | PASS |
| `from autom8_asana.cache.integration.derived import store_derived_timelines` | `derived.py` line 70 | PASS |
| `from autom8_asana.cache.integration.stories import read_stories_batch` | `stories.py` line 62 | PASS |

**API calls verified in `get_or_compute_timelines`:**

| Call | Target | Status |
|------|--------|--------|
| `CLASSIFIERS.get(classifier_name)` | `dict[str, SectionClassifier]` at `activity.py` line 264 | PASS |
| `getattr(client, "_cache_provider", None)` | `AsanaClient._cache_provider` set at `client.py` line 140 | PASS |
| `get_cached_timelines(project_gid, classifier_name, cache)` | `derived.py` line 44 -- signature matches | PASS |
| `cached_entry.data.get("timelines", [])` | `CacheEntry.data: dict[str, Any]` -- `.get()` on dict | PASS |
| `_deserialize_timeline(d)` | `derived.py` line 147 -- signature `(data: dict[str, Any])` | PASS |
| `_compute_day_counts(timelines, period_start, period_end)` | Defined in same file line 567 | PASS |
| `_get_computation_lock(project_gid, classifier_name)` | Defined in same file line 50 | PASS |
| `client.tasks.list_async(project=project_gid, opt_fields=_TASK_OPT_FIELDS)` | `TasksClient.list_async(*, project=None, opt_fields=None, ...)` at `clients/tasks.py` line 459 | PASS |
| `.collect()` on `PageIterator` | `PageIterator.collect()` at `models/common.py` line 149 -- `async def collect(self) -> list[T]` | PASS |
| `read_stories_batch(task_gids, cache)` | `stories.py` line 62 -- signature `(task_gids, cache, *, chunk_size=500)` | PASS |
| `_parse_datetime(task.created_at)` | Defined in same file line 87 -- `(value: str | None) -> datetime | None` | PASS |
| `extract_section_name(task, project_gid=project_gid)` | `activity.py` line 138 -- accepts `(task, project_gid=None)` | PASS |
| `classifier.classify(section_name)` | `SectionClassifier.classify(section_name: str)` at `activity.py` line 69 | PASS |
| `_extract_office_phone(task.model_dump())` | `_extract_office_phone` defined at line 140; `Task.model_dump()` at `models/task.py` line 283 | PASS |
| `Story.model_validate(s)` | `Story` extends `AsanaResource` extends Pydantic `BaseModel` -- `model_validate` is standard Pydantic v2 classmethod | PASS |
| `_build_intervals_from_stories(filtered_stories, classifier=classifier, entity_gid=task_gid)` | Defined line 158 -- signature `(stories, classifier=None, entity_gid=None)` | PASS |
| `_build_imputed_interval(task_created_at, account_activity, section_name)` | Defined line 235 -- signature `(task_created_at, account_activity, section_name)` | PASS |
| `_serialize_timeline(t)` | `derived.py` line 114 -- signature `(timeline: SectionTimeline)` | PASS |
| `store_derived_timelines(project_gid=..., classifier_name=..., timeline_data=..., cache=..., entity_count=..., cache_hits=..., cache_misses=..., computation_duration_ms=...)` | `derived.py` line 70 -- all keyword arguments match declared signature | PASS |

**Constants verified:**

| Constant | Location | Status |
|----------|----------|--------|
| `BUSINESS_OFFERS_PROJECT_GID` | Defined line 65 of same file | PASS |
| `_TASK_OPT_FIELDS` | Defined line 77 of same file | PASS |
| `_STORY_OPT_FIELDS` | Defined line 68 of same file | PASS |

**`_computation_locks` type:**

`defaultdict(asyncio.Lock)` at line 47. `asyncio.Lock` is callable (default factory). Creates a new `asyncio.Lock` per missing key. PASS.

**Findings**: None.

---

### 5. `src/autom8_asana/api/routes/section_timelines.py` (MODIFIED)

**Imports verified:**

| Import | Source | Status |
|--------|--------|--------|
| `import time` | stdlib | PASS |
| `from datetime import date` | stdlib | PASS |
| `from typing import Annotated` | stdlib | PASS |
| `from autom8y_log import get_logger` | installed package | PASS |
| `from fastapi import APIRouter, Query` | fastapi | PASS |
| `from pydantic import BaseModel, Field` | pydantic | PASS |
| `from autom8_asana.api.dependencies import AsanaClientDualMode, RequestId` | `dependencies.py` lines 404, 409 | PASS |
| `from autom8_asana.api.errors import raise_api_error` | `errors.py` line 85 -- in `__all__` | PASS |
| `from autom8_asana.api.models import SuccessResponse, build_success_response` | `models.py` lines 96, 150 -- in `__all__` | PASS |
| `from autom8_asana.models.business.section_timeline import OfferTimelineEntry` | `section_timeline.py` line 157 | PASS |
| `from autom8_asana.services.section_timeline_service import BUSINESS_OFFERS_PROJECT_GID, get_or_compute_timelines` | `section_timeline_service.py` lines 65, 336 | PASS |

**API calls verified:**

| Call | Target | Status |
|------|--------|--------|
| `raise_api_error(request_id, 422, "VALIDATION_ERROR", "...")` | `errors.py` line 85 -- signature `(request_id, status_code, code, message, *, details=None, headers=None)` | PASS |
| `get_or_compute_timelines(client=..., project_gid=..., classifier_name=..., period_start=..., period_end=...)` | `section_timeline_service.py` line 336 -- all kwargs match | PASS |
| `raise_api_error(request_id, 502, "UPSTREAM_ERROR", "...")` | Same signature | PASS |
| `build_success_response(data=response_data, request_id=request_id)` | `models.py` line 150 -- `(data, request_id, pagination=None)` | PASS |
| `SectionTimelinesResponse(timelines=entries)` | Defined in same file line 36 | PASS |
| `time.perf_counter()` | stdlib `time` module | PASS |

**Type aliases verified:**

`AsanaClientDualMode` = `Annotated[AsanaClient, Depends(get_asana_client_from_context)]` -- valid FastAPI `Depends` annotation. PASS.
`RequestId` = `Annotated[str, Depends(get_request_id)]`. PASS.

**Findings**: None.

---

### 6. `src/autom8_asana/api/lifespan.py` (MODIFIED)

The modification removes the section timeline warm-up pipeline. No new imports were introduced. Remaining imports are pre-existing. No dangling references remain from the removal.

**Findings**: None.

---

### 7. `src/autom8_asana/cache/__init__.py` (MODIFIED)

**New exports added and verified:**

| Symbol | Import source | Source line | In `__all__`? | Status |
|--------|--------------|-------------|---------------|--------|
| `get_cached_timelines` | `cache/integration/derived.py` | 44 | Yes (line 228) | PASS |
| `make_derived_timeline_key` | `cache/integration/derived.py` | 31 | Yes (line 227) | PASS |
| `store_derived_timelines` | `cache/integration/derived.py` | 70 | Yes (line 229) | PASS |
| `read_cached_stories` | `cache/integration/stories.py` | 35 | Yes (line 222) | PASS |
| `read_stories_batch` | `cache/integration/stories.py` | 62 | Yes (line 223) | PASS |

**Findings**: None.

---

### 8. `src/autom8_asana/cache/integration/__init__.py` (MODIFIED)

**New exports added and verified:**

| Symbol | Import source | Source line | In `__all__`? | Status |
|--------|--------------|-------------|---------------|--------|
| `get_cached_timelines` | `derived.py` | 44 | Yes (line 29) | PASS |
| `make_derived_timeline_key` | `derived.py` | 31 | Yes (line 28) | PASS |
| `store_derived_timelines` | `derived.py` | 70 | Yes (line 30) | PASS |
| `read_cached_stories` | `stories.py` | 35 | Yes (line 27) | PASS |
| `read_stories_batch` | `stories.py` | 62 | Yes (line 28) | PASS |

**Findings**: None.

---

### 9. `tests/unit/cache/test_derived_cache.py` (NEW)

**Imports verified:**

| Import | Source | Status |
|--------|--------|--------|
| `from datetime import UTC, datetime` | stdlib | PASS |
| `import pytest` | installed | PASS |
| `from autom8y_cache.testing import MockCacheProvider as _SDKMockCacheProvider` | `autom8y_cache/testing/__init__.py` -- `MockCacheProvider` exported at line 21 | PASS |
| `from autom8_asana.cache.integration.derived import _DERIVED_TIMELINE_TTL, _deserialize_timeline, _serialize_timeline, get_cached_timelines, make_derived_timeline_key, store_derived_timelines` | All exist in `derived.py` at lines 28, 147, 114, 44, 31, 70 | PASS (see HH-001) |
| `from autom8_asana.cache.models.entry import CacheEntry, DerivedTimelineCacheEntry, EntryType` | `entry.py` -- all present | PASS |
| `from autom8_asana.models.business.activity import AccountActivity` | `activity.py` line 24 | PASS |
| `from autom8_asana.models.business.section_timeline import SectionInterval, SectionTimeline` | `section_timeline.py` lines 20, 42 | PASS |

**SDK `MockCacheProvider` attributes used in local subclass:**

| Attribute | SDK definition | Status |
|-----------|---------------|--------|
| `._versioned_store` | `backends.py` line 35 | PASS |
| `.calls` | `backends.py` line 36 | PASS |

**Findings**: HH-001 (MEDIUM) -- private symbols imported from `derived.py`.

---

### 10. `tests/unit/cache/test_stories_batch.py` (NEW)

**Imports verified:**

| Import | Source | Status |
|--------|--------|--------|
| `from autom8y_cache.testing import MockCacheProvider as _SDKMockCacheProvider` | `autom8y_cache/testing/__init__.py` | PASS |
| `from autom8_asana.cache.integration.stories import read_cached_stories, read_stories_batch` | `stories.py` lines 35, 62 | PASS |
| `from autom8_asana.cache.models.entry import CacheEntry, EntryType` | `entry.py` | PASS |

**Local `MockCacheProvider.get_batch` override:**

The local subclass overrides `get_batch(self, keys, entry_type)`. The SDK `MockCacheProvider` already defines `get_batch` at `backends.py` line 85. Valid Python override. PASS.

**Findings**: None.

---

### 11. `tests/unit/services/test_get_or_compute_timelines.py` (NEW)

**Imports verified:**

| Import | Source | Status |
|--------|--------|--------|
| `import asyncio` | stdlib | PASS |
| `from datetime import UTC, date, datetime` | stdlib | PASS |
| `from unittest.mock import AsyncMock, MagicMock, patch` | stdlib | PASS |
| `import pytest` | installed | PASS |
| `from autom8_asana.cache.models.entry import CacheEntry, DerivedTimelineCacheEntry, EntryType` | `entry.py` | PASS |
| `from autom8_asana.models.business.activity import AccountActivity` | `activity.py` | PASS |
| `from autom8_asana.models.business.section_timeline import OfferTimelineEntry, SectionInterval, SectionTimeline` | `section_timeline.py` | PASS |
| `from autom8_asana.services.section_timeline_service import _computation_locks, get_or_compute_timelines` | `section_timeline_service.py` lines 47, 336 | PASS |

**Patch targets verified:**

`get_or_compute_timelines` uses local imports inside the function body. Patching at the source module is correct for locally-imported names.

| Patch string | Import location in service | Strategy | Status |
|--------------|--------------------------|----------|--------|
| `"autom8_asana.cache.integration.derived.get_cached_timelines"` | Local import at service line 371 | Patch at source -- correct | PASS |
| `"autom8_asana.cache.integration.derived.store_derived_timelines"` | Local import at service line 373 | Patch at source -- correct | PASS |
| `"autom8_asana.cache.integration.stories.read_stories_batch"` | Local import at service line 375 | Patch at source -- correct | PASS |

**Findings**: None.

---

### 12. `tests/unit/api/test_routes_section_timelines.py` (MODIFIED)

**Imports verified:**

| Import | Source | Status |
|--------|--------|--------|
| `from datetime import date` | stdlib | PASS |
| `from unittest.mock import AsyncMock, MagicMock, patch` | stdlib | PASS |
| `import pytest` | installed | PASS |
| `from fastapi import FastAPI` | fastapi | PASS |
| `from fastapi.testclient import TestClient` | fastapi | PASS |
| `from autom8_asana.api.dependencies import AsanaClientDualMode, RequestId` | `dependencies.py` lines 404, 409 | PASS |
| `from autom8_asana.api.routes.section_timelines import router` | `section_timelines.py` line 33; in `__all__` line 141 | PASS |
| `from autom8_asana.client import AsanaClient` | `client.py` line 50 | PASS |
| `from autom8_asana.models.business.section_timeline import OfferTimelineEntry` | `section_timeline.py` line 157 | PASS |

**DI override pattern verified:**

```python
app.dependency_overrides[AsanaClientDualMode.__metadata__[0].dependency] = override_client
app.dependency_overrides[RequestId.__metadata__[0].dependency] = override_request_id
```

`AsanaClientDualMode` is `Annotated[AsanaClient, Depends(get_asana_client_from_context)]`. `Annotated.__metadata__[0]` is `Depends(get_asana_client_from_context)`. `.dependency` is `get_asana_client_from_context`. This is the correct FastAPI DI override pattern. PASS.

**Patch target:**

`"autom8_asana.api.routes.section_timelines.get_or_compute_timelines"` -- `get_or_compute_timelines` is imported at module level in `section_timelines.py` line 28. Patching at the consuming module is correct for module-level imports. PASS.

**Response shape assertions verified:**

| Assertion | Model field chain | Status |
|-----------|------------------|--------|
| `body["data"]["timelines"]` | `SuccessResponse.data` -> `SectionTimelinesResponse.timelines` | PASS |
| `body["meta"]["request_id"]` | `SuccessResponse.meta` -> `ResponseMeta.request_id` | PASS |
| `body["detail"]["error"]` (422/502) | `raise_api_error` sets `detail={"error": code, ...}` | PASS |

**Findings**: None.

---

## Findings Register

### HH-001: Private symbol import across module boundary (MEDIUM)

**File**: `tests/unit/cache/test_derived_cache.py:20-24`
**Finding**:
```python
from autom8_asana.cache.integration.derived import (
    _DERIVED_TIMELINE_TTL,
    _deserialize_timeline,
    _serialize_timeline,
    ...
)
```
**Evidence**: `_DERIVED_TIMELINE_TTL` (line 28), `_deserialize_timeline` (line 147), and `_serialize_timeline` (line 114) are underscore-prefixed names in `derived.py`. They are not declared in any `__all__`, not exported from `cache/integration/__init__.py`, and not documented as part of the public API surface. The imports resolve successfully at runtime -- these symbols exist and are importable by direct module access.

The concern is API contract fragility: if `derived.py` renames or inlines these internals, the tests break silently at import time. The test file exercises the serialization round-trip and the TTL value directly, which are internal implementation details.

**Severity**: MEDIUM -- advisory. No blocking defect; all three symbols exist and imports resolve.
**Confidence**: HIGH

---

## Registry Verification

All packages referenced across the 12 files are confirmed installed in the project venv at `/Users/tomtenuta/Code/autom8y-asana/.venv/`:

| Package | Usage | Verification |
|---------|-------|--------------|
| `autom8y_cache` | `testing.MockCacheProvider` | Direct read: `.venv/lib/python3.12/site-packages/autom8y_cache/testing/__init__.py` -- `MockCacheProvider` exported |
| `fastapi` | `APIRouter`, `Query`, `FastAPI`, `TestClient` | Project dependency; confirmed via existing codebase usage |
| `pydantic` | `BaseModel`, `Field` | Project dependency; Pydantic v2 confirmed by `model_validate` usage throughout |
| `autom8y_log` | `get_logger` | Project dependency; confirmed in all route files |
| `pytest` | Test framework | Dev dependency |

No new packages were introduced by the 12 files in scope.

---

## Dependency Audit

**New symbols exported from existing modules:**

| Symbol | Module | Previously exported? |
|--------|--------|----------------------|
| `read_cached_stories` | `cache/integration/stories.py` | No -- new function |
| `read_stories_batch` | `cache/integration/stories.py` | No -- new function |
| `get_cached_timelines` | `cache/integration/derived.py` | No -- new file |
| `make_derived_timeline_key` | `cache/integration/derived.py` | No -- new file |
| `store_derived_timelines` | `cache/integration/derived.py` | No -- new file |
| `DerivedTimelineCacheEntry` | `cache/models/entry.py` | No -- new subclass |
| `EntryType.DERIVED_TIMELINE` | `cache/models/entry.py` | No -- new enum member |
| `BUSINESS_OFFERS_PROJECT_GID` | `services/section_timeline_service.py` | No -- new constant |
| `get_or_compute_timelines` | `services/section_timeline_service.py` | No -- new function |
| `_computation_locks` | `services/section_timeline_service.py` | No -- private; accessed by test only |

**Phantom dependencies**: None. All imports in `cache/__init__.py` and `cache/integration/__init__.py` are consumed.

**Missing dependencies**: None. All packages used are in the dependency tree.

**Dependency sprawl**: None. No stdlib-sufficient replacements applicable.

---

## Handoff Checklist

- [x] Every file in review scope scanned for import/dependency issues
- [x] Each finding includes file path, line number, and resolution failure reason
- [x] Registry verification attempted for all new/changed dependencies
- [x] Severity assigned: CRITICAL (non-existent), HIGH (phantom dep), MEDIUM (private import advisory)
- [x] No files skipped without documented reason

**Ready for logic-surgeon.**
