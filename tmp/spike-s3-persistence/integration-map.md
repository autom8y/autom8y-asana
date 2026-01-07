# Integration Map: S3 Persistence in ProjectDataFrameBuilder

**Author**: Integration Researcher
**Date**: 2026-01-05
**Status**: DRAFT
**Upstream**: tech-assessment-s3-testing.md (moto confirmed for testing)

## Executive Summary

This document maps the integration points for wiring `DataFramePersistence` into `ProjectDataFrameBuilder` to enable automatic save-after-build functionality. The analysis identifies a clean injection path with minimal code changes, preserving backward compatibility for existing callers.

---

## 1. Current Architecture

### 1.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              api/main.py                                     │
│  - _preload_dataframe_cache() uses DataFramePersistence directly            │
│  - Creates persistence, calls save_dataframe() after incremental catch-up   │
│  - Pattern: explicit persistence orchestration at startup                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ProjectDataFrameBuilder                                │
│  - build_with_parallel_fetch_async() - main build method                    │
│  - refresh_incremental() - incremental sync with watermark                  │
│  - NO persistence awareness currently                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DataFramePersistence                                  │
│  - save_dataframe(project_gid, df, watermark) -> bool                       │
│  - is_available property for S3 health check                                │
│  - Silent degradation on failures (returns False)                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Files and Line Numbers

| File | Lines | Description |
|------|-------|-------------|
| `/src/autom8_asana/dataframes/builders/project.py` | 117-158 | Constructor - injection point |
| `/src/autom8_asana/dataframes/builders/project.py` | 250-342 | `build_with_parallel_fetch_async()` - save trigger |
| `/src/autom8_asana/dataframes/builders/project.py` | 903-999 | `refresh_incremental()` - save trigger |
| `/src/autom8_asana/dataframes/persistence.py` | 332-423 | `save_dataframe()` - target method |
| `/src/autom8_asana/dataframes/persistence.py` | 312-330 | `is_available` property |
| `/src/autom8_asana/dataframes/watermark.py` | 153-176 | `set_watermark()` - coordination point |
| `/src/autom8_asana/settings.py` | 237-266 | `S3Settings` - auto-detection source |
| `/src/autom8_asana/api/main.py` | 267-577 | Existing persistence usage pattern |

---

## 2. Integration Point Analysis

### 2.1 Injection Point: Constructor vs Method Parameter

**Recommendation: Constructor Injection (Option A)**

| Approach | Pros | Cons |
|----------|------|------|
| **A. Constructor** | Single setup, consistent behavior, clear lifecycle | Requires changes to all instantiation sites |
| **B. Method param** | No constructor changes | Inconsistent API, easy to forget, clutters method signatures |
| **C. Global singleton** | Zero code changes | Hidden dependency, hard to test, violates DI principles |

**Constructor injection pattern:**

```python
# project.py lines 117-158 - BEFORE
def __init__(
    self,
    project: Project,
    task_type: str,
    schema: DataFrameSchema,
    sections: list[str] | None = None,
    resolver: CustomFieldResolver | None = None,
    lazy_threshold: int = LAZY_THRESHOLD,
    cache_integration: DataFrameCacheIntegration | None = None,
    client: AsanaClient | None = None,
    unified_store: "UnifiedTaskStore | None" = None,
) -> None:
```

```python
# project.py lines 117-158 - AFTER
def __init__(
    self,
    project: Project,
    task_type: str,
    schema: DataFrameSchema,
    sections: list[str] | None = None,
    resolver: CustomFieldResolver | None = None,
    lazy_threshold: int = LAZY_THRESHOLD,
    cache_integration: DataFrameCacheIntegration | None = None,
    client: AsanaClient | None = None,
    unified_store: "UnifiedTaskStore | None" = None,
    persistence: "DataFramePersistence | None" = None,  # NEW
) -> None:
```

**Auto-detection factory pattern (alternative):**

```python
# New factory method in builders/project.py
@classmethod
def create_with_auto_persistence(
    cls,
    project: Project,
    task_type: str,
    schema: DataFrameSchema,
    **kwargs,
) -> "ProjectDataFrameBuilder":
    """Factory that auto-detects S3 persistence from environment."""
    from autom8_asana.settings import get_settings
    from autom8_asana.dataframes.persistence import DataFramePersistence

    persistence = None
    if get_settings().s3.bucket:
        persistence = DataFramePersistence()
        if not persistence.is_available:
            persistence = None

    return cls(
        project=project,
        task_type=task_type,
        schema=schema,
        persistence=persistence,
        **kwargs,
    )
```

### 2.2 Save Trigger Location

**Primary trigger point: After `build_with_parallel_fetch_async()` returns**

Current flow in `_build_with_unified_store_async()` (lines 371-615):

```python
# Line 559-587 - Current
materialize_start = time.perf_counter()
df = await view_plugin.materialize_async(
    task_gids=all_task_gids,
    project_gid=project_gid,
    freshness=FreshnessMode.IMMEDIATE,
)
# ... section filtering ...
task_count = len(df)

# Log completion
elapsed_ms = (time.perf_counter() - start_time) * 1000
logger.info(
    "unified_dataframe_build_completed",
    extra={...},
)

return df  # <-- INSERT SAVE HERE
```

**Proposed save trigger:**

```python
# Insert before final return (line ~587)
# Persist DataFrame if persistence is configured
if self._persistence is not None:
    await self._persist_dataframe_async(
        project_gid=project_gid,
        df=df,
        watermark=datetime.now(timezone.utc),
    )

return df
```

**Secondary trigger: After `refresh_incremental()` returns**

Current flow (lines 903-999):

```python
# Line 986-999 - Current
df = await self.build_with_parallel_fetch_async(client)

elapsed_ms = (time.perf_counter() - start_time) * 1000
logger.info(
    "full_fetch_completed",
    extra={...},
)

return df, sync_start  # <-- Also save here
```

However, `refresh_incremental` is typically called by `api/main.py` which handles its own persistence. We should NOT duplicate persistence here to avoid double-writes.

**Recommendation: Single save point in `build_with_parallel_fetch_async` only.**

### 2.3 Failure Handling: Silent Fallback

The `DataFramePersistence.save_dataframe()` method already implements graceful degradation:

```python
# persistence.py lines 366-368
if self._degraded:
    logger.debug("Persistence unavailable, skipping save for %s", project_gid)
    return False
```

```python
# persistence.py lines 421-423
except Exception as e:
    self._handle_s3_error(e, "save", project_gid)
    return False  # Never raises, always returns bool
```

**Implementation in ProjectDataFrameBuilder:**

```python
async def _persist_dataframe_async(
    self,
    project_gid: str,
    df: pl.DataFrame,
    watermark: datetime,
) -> None:
    """Persist DataFrame to S3 (fire-and-forget, silent fallback).

    Per user requirement: graceful degradation on S3 failures.
    Save failures are logged but never raise exceptions.
    """
    if self._persistence is None:
        return

    try:
        success = await self._persistence.save_dataframe(
            project_gid=project_gid,
            df=df,
            watermark=watermark,
        )
        if success:
            logger.info(
                "dataframe_persisted",
                extra={
                    "project_gid": project_gid,
                    "row_count": len(df),
                    "watermark": watermark.isoformat(),
                },
            )
        else:
            logger.debug(
                "dataframe_persistence_skipped",
                extra={
                    "project_gid": project_gid,
                    "reason": "persistence_unavailable",
                },
            )
    except Exception as e:
        # Silent fallback - log and continue
        logger.warning(
            "dataframe_persistence_failed",
            extra={
                "project_gid": project_gid,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
```

### 2.4 Watermark Coordination

**Current pattern in api/main.py (lines 451-455):**

```python
await persistence.save_dataframe(
    project_gid, updated_df, new_watermark
)
await persistence.save_index(project_gid, index)
watermark_repo.set_watermark(project_gid, new_watermark)
```

**Key insight:** `save_dataframe()` handles watermark persistence internally:

```python
# persistence.py lines 397-411
watermark_data = {
    "project_gid": project_gid,
    "watermark": watermark.isoformat(),
    "row_count": len(df),
    "columns": df.columns,
    "saved_at": datetime.now(timezone.utc).isoformat(),
}
wm_key = self._make_watermark_key(project_gid)
client.put_object(...)
```

**Recommendation: No separate watermark coordination needed.**

The `save_dataframe()` method already writes the watermark alongside the DataFrame. The builder does NOT need to call `WatermarkRepository.set_watermark()` - that's the responsibility of the calling code (e.g., `refresh_incremental` or `api/main.py`).

### 2.5 Auto-Detection: S3 Configuration

**Detection logic from settings.py (lines 237-266):**

```python
class S3Settings(BaseSettings):
    bucket: str = Field(default="", description="S3 bucket name")
    # ...

# Environment variable: ASANA_CACHE_S3_BUCKET
```

**Detection pattern:**

```python
from autom8_asana.settings import get_settings

def _should_enable_persistence() -> bool:
    """Check if S3 persistence should be enabled."""
    settings = get_settings()
    return bool(settings.s3.bucket)
```

**Integration with DataFramePersistence:**

The `DataFramePersistence.__init__()` (lines 135-161) already handles auto-detection:

```python
if config is None:
    from autom8_asana.settings import get_settings
    s3_settings = get_settings().s3
    resolved_bucket = bucket if bucket is not None else s3_settings.bucket
    # ... creates PersistenceConfig from settings
```

**Recommendation: Pass `DataFramePersistence()` with no args - it auto-configures from environment.**

---

## 3. Hidden Dependencies

### 3.1 Implicit Coupling Found

| Dependency | Location | Risk | Mitigation |
|------------|----------|------|------------|
| `boto3` optional import | persistence.py:179-189 | Medium - fails silently if not installed | Already handled via `_degraded` flag |
| `polars` optional import | persistence.py:193-200 | Low - builder already requires polars | N/A |
| AWS credentials | boto3 client init | Medium - silent degradation | Already handled via `_degraded` flag |
| Event loop requirement | watermark.py:189-196 | Low - async context always exists in builder | N/A |

### 3.2 Data Flow Dependencies

```
ProjectDataFrameBuilder.build_with_parallel_fetch_async()
    │
    ├── UnifiedTaskStore (required, validated in __init__)
    │
    ├── DataFramePersistence (optional, new)
    │       │
    │       ├── boto3 S3 client (lazy init)
    │       │
    │       └── AWS credentials (from environment/IAM)
    │
    └── WatermarkRepository (independent, not directly coupled)
            │
            └── DataFramePersistence (optional, for write-through)
```

### 3.3 Shared State Analysis

| State | Scope | Thread Safety | Issue |
|-------|-------|---------------|-------|
| `DataFramePersistence._client` | Instance | `threading.Lock` | Safe |
| `DataFramePersistence._degraded` | Instance | Atomic bool | Safe |
| `WatermarkRepository._watermarks` | Singleton | `threading.Lock` | Safe |

**No hidden shared state issues detected.**

---

## 4. Effort Estimation

### 4.1 Implementation Phases

| Phase | Task | Estimate | Confidence |
|-------|------|----------|------------|
| **1. Constructor injection** | Add `persistence` param to `__init__` | 30 min | HIGH |
| **2. Save method** | Add `_persist_dataframe_async()` | 30 min | HIGH |
| **3. Save trigger** | Insert save call in build method | 15 min | HIGH |
| **4. Factory method** | Add `create_with_auto_persistence()` | 30 min | HIGH |
| **5. Tests** | Unit tests with moto | 2 hr | MEDIUM |
| **6. Integration tests** | E2E with real S3 | 1 hr | MEDIUM |

**Total estimate: 4.5-5 hours**

### 4.2 Assumptions

- moto is already validated (per tech assessment)
- No breaking changes to existing callers (optional param with default None)
- S3 bucket and credentials are pre-configured in target environments
- No index persistence (per user requirement: "rebuild index on load")

### 4.3 Risk Areas

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance overhead from async save | Low | Low | Save is fire-and-forget, non-blocking |
| Double-write from api/main.py + builder | Medium | Low | Document exclusion zones |
| Credentials missing in new environments | Medium | Low | Silent degradation already implemented |

---

## 5. Approach Options

### Option A: Constructor Injection (Recommended)

**Pros:**
- Clean DI pattern
- Zero changes for existing callers (optional param)
- Easy to test with mock persistence
- Consistent with `cache_integration` pattern

**Cons:**
- Requires modification to api/main.py callers to avoid double-write

**Effort:** 4.5 hr | **Confidence:** HIGH

### Option B: Method Parameter

**Pros:**
- More explicit control per-call
- No constructor signature change

**Cons:**
- Inconsistent with existing patterns
- Easy to forget on some call sites
- Clutters already-large method signatures

**Effort:** 5 hr | **Confidence:** MEDIUM

### Option C: Global Registry Pattern

**Pros:**
- Zero code changes to builder

**Cons:**
- Hidden dependency
- Hard to test
- Violates DI principles
- Race conditions in singleton setup

**Effort:** 3 hr | **Confidence:** LOW

---

## 6. Migration Path

### Phase 1: Add Optional Persistence (Non-Breaking)

1. Add `persistence` param to `ProjectDataFrameBuilder.__init__` with default `None`
2. Add `_persist_dataframe_async()` helper method
3. Add save call at end of `_build_with_unified_store_async()`
4. Add factory method `create_with_auto_persistence()`

**Rollback:** Remove the three additions. No schema changes. No data changes.

### Phase 2: Wire Up in api/main.py

1. Update `_do_incremental_catchup()` to pass persistence to builder
2. Update `_do_full_rebuild()` to pass persistence to builder
3. Remove duplicate `save_dataframe()` calls from `_preload_dataframe_cache()`

**Rollback:** Revert the call site changes. Builder still works without persistence.

### Phase 3: Documentation and Deprecation

1. Document new pattern in docstrings
2. Add migration guide for external callers
3. Consider deprecating direct `persistence.save_dataframe()` calls in favor of builder auto-save

**Rollback:** N/A (documentation only)

---

## 7. Files Requiring Modification

| File | Change Type | Lines Affected |
|------|-------------|----------------|
| `src/autom8_asana/dataframes/builders/project.py` | Add param, add method, add call | ~40 lines added |
| `src/autom8_asana/api/main.py` | Wire persistence to builder | ~10 lines modified |
| `tests/unit/dataframes/test_project_persistence.py` | New test file | ~150 lines |
| `tests/integration/test_s3_persistence_e2e.py` | New test file | ~100 lines |

---

## 8. POC Scope and Success Criteria

### POC Scope

1. Implement constructor injection with `persistence` param
2. Implement `_persist_dataframe_async()` method
3. Add save trigger in `_build_with_unified_store_async()`
4. Write 3 unit tests with moto:
   - Test save triggered after successful build
   - Test silent fallback on S3 failure
   - Test no-op when persistence is None

### Success Criteria

- [ ] Build completes successfully when `persistence=None` (backward compatible)
- [ ] Build saves to S3 when `persistence` is configured and S3 is available
- [ ] Build completes successfully when S3 fails (graceful degradation)
- [ ] No performance regression (save is non-blocking)
- [ ] All existing tests pass

---

## 9. Artifact Verification

| Artifact | Location | Verified |
|----------|----------|----------|
| Tech assessment | `/tmp/spike-s3-persistence/tech-assessment-s3-testing.md` | Read |
| DataFramePersistence | `/src/autom8_asana/dataframes/persistence.py` | Read |
| ProjectDataFrameBuilder | `/src/autom8_asana/dataframes/builders/project.py` | Read |
| api/main.py | `/src/autom8_asana/api/main.py` | Read |
| watermark.py | `/src/autom8_asana/dataframes/watermark.py` | Read |
| settings.py | `/src/autom8_asana/settings.py` | Read |
| base.py | `/src/autom8_asana/dataframes/builders/base.py` | Read |

---

## 10. Handoff to Prototype Engineer

**Ready for prototyping.** The integration path is clear:

1. Constructor injection follows existing `cache_integration` pattern
2. Save trigger location identified with specific line numbers
3. Silent fallback already implemented in `DataFramePersistence`
4. No hidden dependencies that would block implementation
5. moto confirmed for testing (per upstream tech assessment)

**Key decision for POC:** Use constructor injection (Option A) for consistency with existing codebase patterns.

**Recommended first step:** Implement `_persist_dataframe_async()` helper method, then add constructor param, then wire up save trigger.
