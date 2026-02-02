# TDD: Cache Freshness & Data Completeness Remediation

**Status**: PROPOSED
**Author**: Architect Agent
**Date**: 2026-02-02
**Sprint**: Cache Freshness Remediation Sprint
**Task**: task-001
**Complexity**: MODULE

---

## 1. Overview & Problem Statement

### 1.1 Business Problem

The `/v1/query/offer` endpoint returns 71 ACTIVE offers while the Asana UI shows 80. Nine offers are missing because the DataFrame cache has a watermark of 2026-01-08 -- 22 days stale at time of investigation. The service was deployed on Jan 29 but loaded stale S3 data without triggering a refresh from the Asana API.

### 1.2 Root Cause Analysis

Three independent defects conspire to create a stale cache that never self-heals:

1. **Progressive builder has no manifest age check**: `build_progressive_async()` in `progressive.py` (line 198-226) checks schema compatibility but NOT manifest age. When all sections are COMPLETE, the `sections_to_fetch` list is empty and zero API calls are made. A 22-day-old manifest with all sections COMPLETE looks identical to a 1-minute-old one.

2. **Lambda warmer does not clear manifests**: `_warm_cache_async()` in `cache_warmer.py` writes fresh data to S3 via `CacheWarmer.warm_entity_async()` but never deletes or updates the `manifest.json` files at `dataframes/{project_gid}/manifest.json`. On the next ECS container restart, `build_progressive_async()` finds the old manifest, sees all sections COMPLETE, and skips all API calls.

3. **DataFrameCache._is_valid() is bypassed during progressive preload**: `_preload_dataframe_cache_progressive()` in `main.py` (line 1318) calls `builder.build_progressive_async(resume=True)` which loads section parquets directly from S3 via `SectionPersistence`, completely bypassing the `DataFrameCache._is_valid()` TTL check. The TTL validation in `dataframe_cache.py` (line 462-508) only applies to the `get_async()` lookup path, not the progressive preload path.

### 1.3 Impact

- 9 of 80 ACTIVE offers missing from API responses (11.25% data loss)
- Downstream consumers (insights, reports) operating on incomplete data
- No operational signal that cache is stale -- requires manual comparison with Asana UI

---

## 2. Design: Fix 1 -- Manifest Staleness Detection (Critical)

### 2.1 Approach

Add an age check to the manifest resume path in `build_progressive_async()`. When a manifest's `started_at` timestamp exceeds a configurable TTL, delete it and force a full rebuild. This is the primary fix that prevents the stale-cache-on-restart scenario.

### 2.2 Rationale

The simplest fix is a time-based guard at the resume decision point. The `SectionManifest.started_at` field already exists (see `section_persistence.py` line 97) and records when the manifest was created. Comparing this against a TTL is a single datetime comparison with zero additional I/O.

**Why not use watermark instead of started_at?** The manifest does not carry a separate watermark field. The `started_at` field represents when the build began, which is a reliable proxy for data freshness -- if the build started 22 days ago, the data is at least 22 days old.

**Why delete-and-rebuild instead of incremental?** A stale manifest means the section parquets themselves are stale. Incremental catch-up is designed for small deltas (minutes to hours). A 22-day gap may have section structure changes (sections added/removed in Asana), making section-level resume unreliable. Delete-and-rebuild is safer and the progressive architecture makes it efficient.

### 2.3 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MANIFEST_TTL_HOURS` | `6` | Maximum age (hours) of a manifest before forced rebuild |

**Why 6 hours?** The Lambda warmer runs daily at 2AM UTC. A 6-hour TTL means:
- After a successful warm at 2AM, a restart at 8AM (6 hours) would trigger a rebuild
- A restart at 7AM (5 hours) would resume from the 2AM warm data (acceptable freshness)
- This provides a safety margin while not being so aggressive that every restart forces a full rebuild

The TTL is configurable via environment variable so operations can tune it without code changes. In-progress manifests (with incomplete sections) are exempt from the TTL check to preserve transient failure resume capability.

### 2.4 Code Insertion Point

**File**: `src/autom8_asana/dataframes/builders/progressive.py`
**Function**: `build_progressive_async()`
**Location**: Between manifest retrieval (line 199) and the schema compatibility check (line 202)

```python
# After line 199: manifest = await self._persistence.get_manifest_async(self._project_gid)
# Before line 200: if manifest is not None:

# NEW: Add manifest age check within the existing `if manifest is not None:` block,
# BEFORE the schema compatibility check.
# Insert after line 200 (if manifest is not None:), before line 202 (if not manifest.is_schema_compatible):

import os
manifest_ttl_hours = int(os.environ.get("MANIFEST_TTL_HOURS", "6"))
manifest_age_hours = (datetime.now(UTC) - manifest.started_at).total_seconds() / 3600

if manifest_age_hours > manifest_ttl_hours and manifest.is_complete():
    logger.warning(
        "progressive_build_manifest_stale",
        extra={
            "project_gid": self._project_gid,
            "manifest_age_hours": round(manifest_age_hours, 2),
            "ttl_hours": manifest_ttl_hours,
            "started_at": manifest.started_at.isoformat(),
        },
    )
    await self._persistence.delete_manifest_async(self._project_gid)
    manifest = None  # Force fresh build
```

**Critical preservation of resume**: The `manifest.is_complete()` check ensures that only fully-completed manifests are subject to the TTL. A manifest with IN_PROGRESS or FAILED sections represents a transient failure recovery scenario and should be allowed to resume regardless of age.

### 2.5 SectionManifest.is_complete() Verification

The method already exists at `section_persistence.py` line 168-170:
```python
def is_complete(self) -> bool:
    """Check if all sections are complete."""
    return self.completed_sections == self.total_sections
```

No changes needed to `SectionManifest`.

### 2.6 Error Handling

- If `MANIFEST_TTL_HOURS` is not a valid integer, `int()` will raise `ValueError`. Wrap in try/except with fallback to default (6).
- If `manifest.started_at` is None (legacy manifests), treat as stale (force rebuild). Legacy manifests without `started_at` would fail the `is_schema_compatible` check anyway since they have empty `schema_version`.
- If `delete_manifest_async` fails, log error and continue with stale manifest (graceful degradation -- next restart will retry).

### 2.7 Test Strategy

1. **Unit test**: `test_manifest_stale_triggers_rebuild` -- Mock persistence with a manifest older than TTL where all sections are COMPLETE. Verify `delete_manifest_async` is called and API fetches proceed.
2. **Unit test**: `test_manifest_stale_but_incomplete_resumes` -- Mock persistence with an old manifest that has IN_PROGRESS sections. Verify it resumes (no deletion).
3. **Unit test**: `test_manifest_fresh_resumes_normally` -- Mock persistence with a fresh manifest (under TTL). Verify normal resume path.
4. **Unit test**: `test_manifest_ttl_env_var_override` -- Set `MANIFEST_TTL_HOURS=1` and verify 2-hour-old manifest triggers rebuild.
5. **Unit test**: `test_manifest_ttl_invalid_env_var` -- Set `MANIFEST_TTL_HOURS=abc` and verify fallback to 6.

---

## 3. Design: Fix 2 -- Lambda Warmer Manifest Clearing (Critical)

### 3.1 Approach

After the Lambda warmer successfully writes fresh data for an entity type, delete the S3 manifest for the corresponding project. This ensures the next ECS container startup does NOT find a stale manifest and instead either finds no manifest (triggering fresh build) or finds the fresh data written by the warmer.

### 3.2 Rationale

The Lambda warmer uses `CacheWarmer.warm_entity_async()` which writes fresh DataFrames to S3 via `DataFrameCache.put_async()`. This writes to the progressive tier's S3 location. However, the manifest at `dataframes/{project_gid}/manifest.json` is NOT updated because the warmer bypasses the progressive builder's manifest lifecycle entirely.

**Alternative considered: Update manifest instead of delete.** Updating the manifest would require the warmer to know the section structure of the data it just wrote, which it does not. Deletion is simpler and the progressive builder handles the "no manifest" case correctly (creates a new one).

### 3.3 S3 Key Pattern

Manifests follow the pattern from `section_persistence.py` line 287:
```
dataframes/{project_gid}/manifest.json
```

The warmer needs to resolve `entity_type -> project_gid` (which it already does via `EntityProjectRegistry`) and then delete the manifest at this path.

### 3.4 Code Insertion Point

**File**: `src/autom8_asana/lambda_handlers/cache_warmer.py`
**Function**: `_warm_cache_async()`
**Location**: After successful entity warm (line 614, inside `if status.result == WarmResult.SUCCESS:` block)

```python
# After line 614: completed_entities.append(entity_type)
# Add manifest clearing:

# Clear stale manifest for this entity type's project
project_gid = get_project_gid(entity_type)
if project_gid:
    try:
        from autom8_asana.dataframes.section_persistence import SectionPersistence
        section_persistence = SectionPersistence()
        async with section_persistence:
            await section_persistence.delete_manifest_async(project_gid)
            logger.info(
                "manifest_cleared_after_warm",
                extra={
                    "entity_type": entity_type,
                    "project_gid": project_gid,
                    "invocation_id": invocation_id,
                },
            )
    except Exception as e:
        # Non-fatal: manifest clearing failure should not block warming
        logger.warning(
            "manifest_clear_failed",
            extra={
                "entity_type": entity_type,
                "project_gid": project_gid,
                "error": str(e),
                "invocation_id": invocation_id,
            },
        )
```

### 3.5 Race Condition Analysis

**Scenario**: Lambda clears manifest while ECS service is mid-restart and reading the manifest.

| Timing | Lambda | ECS | Outcome |
|--------|--------|-----|---------|
| T1 | Warm completes, manifest deleted | Not started | Safe: ECS finds no manifest, does fresh build |
| T2 | Warm in progress | Reads manifest, starts resume | Safe: ECS resumes from old manifest. Fix 1 (TTL) will catch on NEXT restart |
| T3 | Warm completes, manifest deleted | Mid-section fetch | Safe: Section parquets are independent objects. Manifest deletion does not affect in-progress section reads. Builder will create new manifest for remaining sections |
| T4 | Manifest deleted | Reads manifest (gets None) | Safe: Builder creates fresh manifest and does full build |

**Conclusion**: The race condition is benign. In the worst case (T2), the ECS service resumes from a stale manifest one time, and Fix 1's TTL check catches it on the next restart. The system converges to fresh data within one restart cycle.

### 3.6 Performance Impact

`delete_manifest_async` is a single S3 DeleteObject call (~50ms). The warmer already takes minutes per entity type, so this is negligible. The `SectionPersistence` context manager is lightweight (creates/destroys an async S3 client session).

### 3.7 Error Handling

- Manifest clearing failure is non-fatal. Logged as warning. The warmer continues with the next entity type.
- If `SectionPersistence` cannot be instantiated (e.g., missing S3 config), catch and log. This should not happen in a correctly configured Lambda but defensive coding protects against partial configuration.

### 3.8 Test Strategy

1. **Unit test**: `test_warmer_clears_manifest_on_success` -- Mock `SectionPersistence.delete_manifest_async` and verify it is called after successful warm for each entity type.
2. **Unit test**: `test_warmer_skips_manifest_clear_on_failure` -- Verify manifest is NOT deleted when entity warm fails.
3. **Unit test**: `test_warmer_continues_on_manifest_clear_failure` -- Mock `delete_manifest_async` to raise exception. Verify warmer continues and returns success.
4. **Integration test**: `test_warmer_manifest_lifecycle` -- Full warm cycle followed by progressive preload. Verify preload does fresh build (not stale resume).

---

## 4. Design: Fix 3 -- Preload Freshness Validation (Important)

### 4.1 Approach

After `_preload_dataframe_cache_progressive()` loads data from S3 via the progressive builder, check the resulting watermark age. If the data is older than the configured threshold, trigger an incremental catch-up using `build_with_parallel_fetch_async()` to fetch only tasks modified since the watermark.

### 4.2 Rationale

Fixes 1 and 2 prevent stale data from persisting across restarts. Fix 3 adds a runtime check that catches staleness even when Fixes 1 and 2 are in place. This is defense-in-depth: if the Lambda warmer fails silently or the manifest TTL is configured too generously, the preload validation catches it.

**Why incremental catch-up instead of full rebuild?** The progressive builder already loaded the data from S3. An incremental catch-up fetches only tasks modified since the watermark, which for a few hours of staleness is typically a small delta. This is much faster than a full rebuild and preserves the cold-start performance target (<5s for cached data).

### 4.3 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PRELOAD_FRESHNESS_THRESHOLD_HOURS` | `8` | Maximum watermark age (hours) before incremental catch-up triggers |

**Why 8 hours?** This is intentionally larger than the manifest TTL (6 hours) to act as a secondary safety net, not a primary enforcement mechanism. If the manifest TTL is working correctly, the preload freshness check will rarely fire. The 8-hour threshold provides a 2-hour grace period above the manifest TTL to avoid redundant API calls during normal operation.

### 4.4 Code Insertion Point

**File**: `src/autom8_asana/api/main.py`
**Function**: `_preload_dataframe_cache_progressive()`, inner function `process_project()`
**Location**: After `builder.build_progressive_async(resume=True)` (line 1318), before storing in watermark repo (line 1326)

```python
# After line 1318: result = await builder.build_progressive_async(resume=True)
# Add freshness validation:

import os
freshness_threshold_hours = int(
    os.environ.get("PRELOAD_FRESHNESS_THRESHOLD_HOURS", "8")
)

# Check watermark age of loaded data
watermark_age_hours = (
    datetime.now(UTC) - result.watermark
).total_seconds() / 3600

if watermark_age_hours > freshness_threshold_hours and result.sections_resumed > 0:
    logger.warning(
        "progressive_preload_stale_data_detected",
        extra={
            "project_gid": project_gid,
            "entity_type": entity_type,
            "watermark_age_hours": round(watermark_age_hours, 2),
            "threshold_hours": freshness_threshold_hours,
            "sections_resumed": result.sections_resumed,
        },
    )

    # Trigger incremental catch-up
    catchup_result = await builder.build_with_parallel_fetch_async(
        project_gid=project_gid,
        schema=schema,
        resume=True,
        incremental=True,
    )

    # Replace result with catch-up result
    from autom8_asana.dataframes.builders.progressive import ProgressiveBuildResult
    result = ProgressiveBuildResult(
        df=catchup_result,
        watermark=datetime.now(UTC),
        total_rows=len(catchup_result),
        sections_fetched=result.sections_fetched,
        sections_resumed=result.sections_resumed,
        fetch_time_ms=result.fetch_time_ms,
        total_time_ms=result.total_time_ms,
    )

    logger.info(
        "progressive_preload_catchup_complete",
        extra={
            "project_gid": project_gid,
            "entity_type": entity_type,
            "rows_after_catchup": result.total_rows,
        },
    )
```

**Key guard**: `result.sections_resumed > 0` ensures we only trigger catch-up when data was actually loaded from S3 cache (resumed). If all sections were freshly fetched (`sections_resumed == 0`), the data is already fresh.

### 4.5 Error Handling

- If incremental catch-up fails, fall through with the stale data (logged as warning). Stale data is better than no data.
- If `PRELOAD_FRESHNESS_THRESHOLD_HOURS` is not a valid integer, fall back to default (8).
- The catch-up uses the same `ProgressiveProjectBuilder` instance, so all error handling from the builder applies (section-level failures, S3 write failures, etc.).

### 4.6 Cold-Start Impact

The incremental catch-up adds API call overhead to cold start. For a few hours of staleness, this is typically:
- 1 API call per section (to list tasks)
- IncrementalFilter skips unchanged tasks
- Only changed tasks are extracted and merged

Estimated additional time: 2-10 seconds depending on change volume. This is acceptable for defense-in-depth and only fires when the primary controls (Fix 1, Fix 2) fail.

### 4.7 Test Strategy

1. **Unit test**: `test_preload_triggers_catchup_for_stale_data` -- Mock builder results with old watermark and `sections_resumed > 0`. Verify `build_with_parallel_fetch_async` is called.
2. **Unit test**: `test_preload_skips_catchup_for_fresh_data` -- Mock builder results with recent watermark. Verify no catch-up triggered.
3. **Unit test**: `test_preload_skips_catchup_when_no_resume` -- Mock builder results with old watermark but `sections_resumed == 0`. Verify no catch-up triggered.
4. **Unit test**: `test_preload_graceful_on_catchup_failure` -- Mock catch-up to raise exception. Verify preload completes with stale data.

---

## 5. Design: Fix 4 -- Admin Cache Refresh Endpoint (Operational)

### 5.1 Approach

Add a `POST /v1/admin/cache/refresh` endpoint that triggers a cache invalidation and rebuild. This provides operations with a manual lever to force fresh data without restarting the service.

### 5.2 Rationale

Automated fixes (1-3) prevent and remediate staleness automatically. However, operations needs a manual escape hatch for:
- Investigating data discrepancies
- Forcing refresh after known Asana data changes
- Testing that the automated fixes work correctly
- Emergency remediation if automated fixes fail

### 5.3 API Contract

**Endpoint**: `POST /v1/admin/cache/refresh`
**Authentication**: Service token (S2S JWT) via `require_service_claims` dependency from `internal.py`
**Content-Type**: `application/json`

**Request Body** (all fields optional):
```json
{
    "entity_type": "offer",
    "force_full_rebuild": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `entity_type` | `string \| null` | `null` | Specific entity type to refresh. If null, refresh all. |
| `force_full_rebuild` | `bool` | `false` | If true, delete manifests and rebuild from scratch. If false, do incremental catch-up. |

**Response** (202 Accepted):
```json
{
    "status": "accepted",
    "message": "Cache refresh initiated for entity_type=offer",
    "entity_types": ["offer"],
    "refresh_id": "uuid-here",
    "force_full_rebuild": false
}
```

**Why 202 instead of 200?** Cache refresh is an async operation that may take seconds to minutes. The endpoint kicks off the refresh as a background task and returns immediately. The caller can poll `/v1/health/ready` or check logs for completion.

**Error Responses**:
- `401 Unauthorized`: Missing or invalid service token
- `400 Bad Request`: Invalid entity_type value
- `503 Service Unavailable`: Cache system not initialized

### 5.4 Execution Model (Async Background Task)

The endpoint spawns a `BackgroundTask` (FastAPI built-in) that:
1. Invalidates the DataFrameCache for the target entity type(s)
2. Deletes manifest(s) if `force_full_rebuild=true`
3. Triggers `build_with_parallel_fetch_async()` for each entity type
4. Updates watermark repo and DataFrameCache singleton on completion

This is the same execution model used by `_preload_dataframe_cache_progressive()` -- a background task that does not block the API.

### 5.5 Code Location

**New file**: `src/autom8_asana/api/routes/admin.py`

```python
"""Admin routes for cache management.

Provides operational endpoints for manual cache control.
Authentication: Service token (S2S JWT) required.
"""

from __future__ import annotations

import uuid
from typing import Any

from autom8y_log import get_logger
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from autom8_asana.api.routes.internal import ServiceClaims, require_service_claims

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/admin", tags=["admin"])

VALID_ENTITY_TYPES = {"unit", "business", "offer", "contact", "asset_edit"}


class CacheRefreshRequest(BaseModel):
    entity_type: str | None = None
    force_full_rebuild: bool = False


class CacheRefreshResponse(BaseModel):
    status: str = "accepted"
    message: str
    entity_types: list[str]
    refresh_id: str
    force_full_rebuild: bool


@router.post("/cache/refresh", response_model=CacheRefreshResponse, status_code=202)
async def refresh_cache(
    request: Request,
    body: CacheRefreshRequest,
    background_tasks: BackgroundTasks,
    claims: ServiceClaims = Depends(require_service_claims),
) -> CacheRefreshResponse:
    """Trigger cache refresh for one or all entity types."""
    # ... validation, background task scheduling, response
```

### 5.6 Router Registration

**File**: `src/autom8_asana/api/main.py`
**Location**: After existing router includes (around line 1504)

Add:
```python
from autom8_asana.api.routes.admin import router as admin_router
app.include_router(admin_router)
```

And add import to `src/autom8_asana/api/routes/__init__.py`.

### 5.7 Error Handling

- Invalid `entity_type`: Return 400 with list of valid types.
- Cache not initialized: Return 503 with message.
- Background task failure: Logged as error. Caller should check `/v1/health/ready` or logs.
- Multiple concurrent refresh requests for same entity type: The coalescer in `DataFrameCache` prevents thundering herd. Second request will wait for first to complete.

### 5.8 Test Strategy

1. **Unit test**: `test_admin_refresh_requires_service_token` -- Verify 401 for PAT and missing auth.
2. **Unit test**: `test_admin_refresh_validates_entity_type` -- Verify 400 for invalid entity type.
3. **Unit test**: `test_admin_refresh_accepts_valid_request` -- Verify 202 response with correct body.
4. **Unit test**: `test_admin_refresh_all_types` -- Verify null entity_type triggers all types.
5. **Integration test**: `test_admin_refresh_full_lifecycle` -- POST refresh, verify cache is invalidated and rebuilt.

---

## 6. Manifest Lifecycle Sequence Diagram

### 6.1 Normal Startup (No Stale Data)

```
ECS Container                Progressive Builder            S3 (Manifest)
    |                              |                              |
    |-- startup ------------------>|                              |
    |                              |-- get_manifest_async() ----->|
    |                              |<-- manifest (age=2h) --------|
    |                              |                              |
    |                              |-- check age vs TTL (6h)      |
    |                              |   2h < 6h => FRESH           |
    |                              |                              |
    |                              |-- check schema compat        |
    |                              |   => compatible              |
    |                              |                              |
    |                              |-- get_incomplete_sections()  |
    |                              |   => [] (all COMPLETE)       |
    |                              |                              |
    |                              |-- merge_sections()           |
    |                              |   => DataFrame (80 rows)     |
    |<-- ProgressiveBuildResult ---|                              |
    |   (sections_resumed=N,       |                              |
    |    sections_fetched=0)       |                              |
```

### 6.2 Stale Manifest Detection (Fix 1)

```
ECS Container                Progressive Builder            S3 (Manifest)
    |                              |                              |
    |-- startup ------------------>|                              |
    |                              |-- get_manifest_async() ----->|
    |                              |<-- manifest (age=22d) -------|
    |                              |                              |
    |                              |-- check age vs TTL (6h)      |
    |                              |   22d > 6h => STALE          |
    |                              |   manifest.is_complete()=True|
    |                              |                              |
    |                              |-- delete_manifest_async() -->|
    |                              |   manifest = None            |
    |                              |                              |
    |                              |-- create_manifest_async() -->|
    |                              |<-- new manifest --------------|
    |                              |                              |
    |                              |-- fetch ALL sections ------->|
    |                              |   (full API fetch)           |
    |                              |                              |
    |<-- ProgressiveBuildResult ---|                              |
    |   (sections_fetched=N,       |                              |
    |    sections_resumed=0)       |                              |
```

### 6.3 Lambda Warmer Manifest Clearing (Fix 2)

```
Lambda Warmer                CacheWarmer                    S3
    |                              |                          |
    |-- warm_entity_async() ------>|                          |
    |                              |-- build & write -------->|
    |                              |   (dataframe.parquet,    |
    |                              |    watermark.json)       |
    |<-- WarmResult.SUCCESS -------|                          |
    |                              |                          |
    |-- delete_manifest_async() ---|                          |
    |                              |-- DELETE manifest.json -->|
    |                              |<-- 204 No Content --------|
    |                              |                          |
    |-- next entity type --------->|                          |
```

### 6.4 Preload Freshness Catch-Up (Fix 3)

```
ECS Preload                  Progressive Builder            Asana API
    |                              |                              |
    |-- build_progressive_async -->|                              |
    |<-- result (watermark=10h) ---|                              |
    |                              |                              |
    |-- check watermark age        |                              |
    |   10h > 8h => STALE          |                              |
    |   sections_resumed > 0       |                              |
    |                              |                              |
    |-- build_with_parallel_fetch  |                              |
    |   (incremental=True) ------->|                              |
    |                              |-- fetch sections ----------->|
    |                              |   (IncrementalFilter skips   |
    |                              |    unchanged tasks)          |
    |                              |<-- delta tasks --------------|
    |                              |                              |
    |                              |-- DeltaMerger.merge()        |
    |<-- updated DataFrame --------|                              |
    |   (80 rows, fresh watermark) |                              |
```

---

## 7. Risk Analysis

### 7.1 TTL Tuning Risk

**Risk**: Manifest TTL too low causes unnecessary full rebuilds on every restart, increasing cold-start time and API rate consumption.

**Mitigation**: Default of 6 hours with environment variable override. Monitor `progressive_build_manifest_stale` log events to tune. The Lambda warmer runs at 2AM, so manifests should be <24h old in steady state. A 6-hour TTL gives 4x margin within a 24-hour cycle.

**Monitoring**: Add structured log field `manifest_age_hours` to both stale and fresh paths so operations can see the distribution of manifest ages.

### 7.2 Race Condition Risk (Fix 2)

**Risk**: Lambda deletes manifest while ECS service is reading it.

**Mitigation**: S3 provides read-after-write consistency. The progressive builder reads the manifest once at the start of `build_progressive_async()` and holds it in memory. A concurrent delete does not affect the in-memory copy. The worst case is the ECS service completes a stale build, which Fix 1 catches on next restart. See Section 3.5 for full analysis.

### 7.3 Cold-Start Impact Risk (Fix 3)

**Risk**: Incremental catch-up during preload extends cold-start time beyond the 5-second target.

**Mitigation**: The catch-up only fires when `watermark_age_hours > 8` AND `sections_resumed > 0`. In normal operation (Lambda warmer working, Fix 1 active), this should rarely fire. When it does, the IncrementalFilter minimizes API calls. Worst case (days of staleness) may take 10-30 seconds -- acceptable for a defense-in-depth measure that indicates other fixes have failed.

### 7.4 Lambda Memory Risk

**Risk**: `SectionPersistence` instantiation in Lambda adds memory overhead.

**Mitigation**: `SectionPersistence` is lightweight -- it only holds an `AsyncS3Client` reference. The async context manager session is opened and closed inline. In a 1024MB Lambda, this is negligible. The S3 DeleteObject call adds ~50ms per entity type.

### 7.5 Backward Compatibility Risk

**Risk**: Existing cached manifests in S3 may not have `started_at` populated correctly.

**Mitigation**: `SectionManifest.started_at` has a `default_factory=lambda: datetime.now(UTC)` (line 97 of `section_persistence.py`). All manifests created by the current codebase have this field. Legacy manifests (if any) without `started_at` would fail pydantic validation during `model_validate()` and return None from `get_manifest_async()`, which triggers a fresh build. This is the correct behavior.

---

## 8. Implementation Order

| Order | Fix | Priority | Est. Effort | Dependencies |
|-------|-----|----------|-------------|--------------|
| 1 | Fix 1: Manifest Staleness Detection | Critical | 1-2 hours | None |
| 2 | Fix 2: Lambda Warmer Manifest Clearing | Critical | 1-2 hours | None (parallel with Fix 1) |
| 3 | Fix 3: Preload Freshness Validation | Important | 2-3 hours | Fix 1 (shares TTL concept) |
| 4 | Fix 4: Admin Cache Refresh Endpoint | Operational | 2-3 hours | None (parallel with Fix 3) |

**Rationale**: Fixes 1 and 2 are independent and address the two root causes directly. They can be implemented in parallel. Fix 3 builds on the freshness concept from Fix 1 and adds defense-in-depth. Fix 4 is an operational tool that can be built independently.

**Deploy Strategy**: Fixes 1 and 2 should be deployed together as they complement each other. Fix 3 can follow in a subsequent deploy. Fix 4 can be deployed independently at any time.

---

## 9. Acceptance Criteria

### 9.1 Primary Acceptance Criteria

- [ ] After deployment, `/v1/query/offer` returns 80 ACTIVE offers (matching Asana UI count)
- [ ] Service restart after >6 hours of idle shows `progressive_build_manifest_stale` log and triggers full rebuild
- [ ] Lambda warmer completion shows `manifest_cleared_after_warm` log for each entity type
- [ ] Progressive preload with stale data shows `progressive_preload_stale_data_detected` log and triggers catch-up

### 9.2 Regression Criteria

- [ ] Resume from transient failure (partial section fetch) still works -- manifest with IN_PROGRESS sections is NOT deleted by TTL check
- [ ] Cold-start time with fresh cached data remains <5 seconds
- [ ] Lambda warmer completes within 900-second timeout (manifest deletion adds <1s per entity)
- [ ] Schema version mismatch still triggers rebuild (existing behavior preserved)

### 9.3 Operational Criteria

- [ ] `POST /v1/admin/cache/refresh` returns 202 and triggers refresh
- [ ] `POST /v1/admin/cache/refresh` rejects PAT tokens (returns 401)
- [ ] All TTL values are configurable via environment variables without code changes

---

## 10. Architecture Decision Records

### ADR-CF-001: Manifest TTL for Staleness Detection

**Status**: PROPOSED
**Context**: The progressive builder resumes from stale manifests without checking age, causing 22-day-old data to be served.
**Decision**: Add a configurable TTL (default 6 hours) that triggers manifest deletion and full rebuild when exceeded, but only for complete manifests.
**Rationale**: Time-based staleness detection is simple, reliable, and configurable. The `is_complete()` guard preserves resume capability for transient failures.
**Consequences**: Additional environment variable. Restart after >6h idle triggers full rebuild (~30-60s). Configurable if default is too aggressive.

### ADR-CF-002: Lambda Warmer Deletes Manifests (Not Updates)

**Status**: PROPOSED
**Context**: Lambda warmer writes fresh data but leaves stale manifests, causing ECS to resume from stale state.
**Decision**: Delete manifest after successful warm rather than updating it.
**Rationale**: The warmer does not know the section structure of the data it wrote. Deletion is simpler and the progressive builder handles "no manifest" correctly by creating a fresh one. Updating would require additional complexity to reconstruct section metadata.
**Consequences**: Next ECS restart after warm creates a fresh manifest. The warm data is still in S3 and will be loaded. Race conditions are benign (see Section 3.5).

### ADR-CF-003: Defense-in-Depth Freshness Validation

**Status**: PROPOSED
**Context**: Fixes 1 and 2 address root causes, but a defense-in-depth check at preload time adds resilience.
**Decision**: Add watermark age check after progressive preload with incremental catch-up as remediation.
**Rationale**: Multiple independent checks prevent data staleness even when individual fixes fail. The incremental catch-up is efficient (uses IncrementalFilter) and only fires when primary controls fail.
**Consequences**: Rare additional API calls during cold start. Threshold (8h) is intentionally higher than manifest TTL (6h) to avoid redundant checks.

### ADR-CF-004: Admin Refresh Endpoint with S2S Auth

**Status**: PROPOSED
**Context**: Operations needs manual cache refresh capability without service restart.
**Decision**: Add `POST /v1/admin/cache/refresh` with S2S JWT auth and async background execution.
**Rationale**: Reuses existing `require_service_claims` auth pattern from `internal.py`. Async execution prevents request timeout for long refreshes. 202 response pattern is standard for async operations.
**Consequences**: New endpoint, new route file. Requires S2S token for access (not available to end users with PAT tokens).

---

## Attestation Table

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD Document | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-cache-freshness-remediation.md` | Written |
| Progressive Builder (Fix 1 target) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py` | Read |
| Section Persistence (manifest schema) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py` | Read |
| Lambda Cache Warmer (Fix 2 target) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_warmer.py` | Read |
| API Main (Fix 3 target) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | Read |
| DataFrame Cache (validation logic) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py` | Read |
| Internal Routes (auth pattern for Fix 4) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/internal.py` | Read |
