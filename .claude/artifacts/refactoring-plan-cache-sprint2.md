# Refactoring Plan: Cache Architecture Sprint 2

**Produced by**: Architect Enforcer
**Input**: Smell Report `smell-report-cache-landscape.md` (Sprint 1 deferred items)
**Sprint 1 Status**: 11/11 tasks APPROVED (RF-L01 to RF-L11). 7938 tests passing, mypy --strict clean, ruff clean.
**Date**: 2026-02-04

---

## Architectural Assessment

Sprint 1 eliminated the quick wins, DRY extractions, and method decompositions that had clear boundaries. Sprint 2 tackles the four deferred items that require more careful design: a god method decomposition with entangled state, a cross-layer side-channel formalization, a multi-file error handling extraction, and a large-scale logging migration.

**Root cause clusters for Sprint 2**:
1. **Organic method growth** -- `build_progressive_async` grew as resume, freshness probing, and delta updates were added sequentially (SM-L007)
2. **Side-channel propagation** -- FreshnessInfo travels through 3 layers via `getattr` on private attributes, bypassing type safety (SM-L005)
3. **Independent backend evolution** -- Redis, S3, and AsyncS3 each implemented degraded mode and error handling independently, diverging over time (SM-L003 + SM-L004)
4. **Legacy logging patterns** -- The UnifiedTaskStore subsystem predates the project's structured logging convention (SM-L014)

**Key architectural decisions**:
- RF-L12 is a pure decomposition; no new abstractions, just method extraction following the existing numbered comments
- RF-L13 replaces `getattr` side-channels with explicit typed returns -- this is the minimum viable formalization (not a full result-object redesign)
- RF-L14 extracts shared behavior into a mixin rather than a base class, preserving the existing class hierarchies
- RF-L15 is mechanical but high-volume; the plan provides a pattern catalog to ensure consistency

---

## Phase 1: Method Decomposition (Medium-Risk, Single File)

### RF-L12: Decompose build_progressive_async into focused private methods

- **Addresses**: SM-L007
- **Files**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:138-389`
- **Current State**: 251-line method with 6 numbered steps. Resume logic (lines 184-269) is an 85-line nested conditional block that handles manifest retrieval, schema compatibility check, freshness probing, and delta application -- all entangled.

**Decomposition Plan**:

Extract 4 private methods. The main method becomes a ~60-line orchestrator calling each step:

#### Step 2 extraction: `_check_resume_and_probe`

**Before** (lines 180-269):
```python
# Step 2: Check for existing manifest (resume capability)
manifest: SectionManifest | None = None
sections_to_fetch: list[str] = section_gids
current_schema_version = self._schema.version

if resume:
    manifest = await self._persistence.get_manifest_async(self._project_gid)
    if manifest is not None:
        # Check schema compatibility before resuming
        if manifest is not None and not manifest.is_schema_compatible(
            current_schema_version
        ):
            # ... 8 lines: log warning, delete manifest, set None ...
        elif manifest is not None:
            # Resume: only fetch incomplete sections
            sections_to_fetch = manifest.get_incomplete_section_gids()
            sections_resumed = manifest.completed_sections
            # ... 8 lines: log info ...

            # Step 2b: Probe COMPLETE sections for freshness
            if (
                manifest.is_complete()
                and os.environ.get("SECTION_FRESHNESS_PROBE", "1") != "0"
            ):
                try:
                    # ... 30 lines: freshness probing and delta application ...
                except Exception as e:
                    # ... 7 lines: log warning ...
```

**After**:
```python
@dataclass
class _ResumeResult:
    """Internal result from resume check."""
    manifest: SectionManifest | None
    sections_to_fetch: list[str]
    sections_resumed: int
    sections_probed: int
    sections_delta_updated: int

async def _check_resume_and_probe(
    self,
    section_gids: list[str],
    resume: bool,
) -> _ResumeResult:
    """Check for existing manifest and probe freshness.

    Handles:
    - Manifest retrieval and schema compatibility check
    - Resume detection (skip completed sections)
    - Freshness probing and delta application for complete manifests

    Args:
        section_gids: All section GIDs in the project.
        resume: Whether to attempt resume from existing manifest.

    Returns:
        _ResumeResult with manifest, sections to fetch, and metrics.
    """
    sections_to_fetch = section_gids
    sections_resumed = 0
    sections_probed = 0
    sections_delta_updated = 0
    manifest: SectionManifest | None = None
    current_schema_version = self._schema.version

    if not resume:
        return _ResumeResult(
            manifest=manifest,
            sections_to_fetch=sections_to_fetch,
            sections_resumed=sections_resumed,
            sections_probed=sections_probed,
            sections_delta_updated=sections_delta_updated,
        )

    manifest = await self._persistence.get_manifest_async(self._project_gid)
    if manifest is None:
        return _ResumeResult(
            manifest=manifest,
            sections_to_fetch=sections_to_fetch,
            sections_resumed=sections_resumed,
            sections_probed=sections_probed,
            sections_delta_updated=sections_delta_updated,
        )

    # Check schema compatibility before resuming
    if not manifest.is_schema_compatible(current_schema_version):
        logger.warning(
            "progressive_build_schema_mismatch",
            extra={
                "project_gid": self._project_gid,
                "cached_version": manifest.schema_version,
                "current_version": current_schema_version,
            },
        )
        await self._persistence.delete_manifest_async(self._project_gid)
        return _ResumeResult(
            manifest=None,
            sections_to_fetch=sections_to_fetch,
            sections_resumed=sections_resumed,
            sections_probed=sections_probed,
            sections_delta_updated=sections_delta_updated,
        )

    # Resume: only fetch incomplete sections
    sections_to_fetch = manifest.get_incomplete_section_gids()
    sections_resumed = manifest.completed_sections

    logger.info(
        "progressive_build_resuming",
        extra={
            "project_gid": self._project_gid,
            "total_sections": len(section_gids),
            "completed_sections": sections_resumed,
            "sections_to_fetch": len(sections_to_fetch),
        },
    )

    # Probe COMPLETE sections for freshness
    probed, delta_updated = await self._probe_freshness(manifest)
    sections_probed = probed
    sections_delta_updated = delta_updated

    return _ResumeResult(
        manifest=manifest,
        sections_to_fetch=sections_to_fetch,
        sections_resumed=sections_resumed,
        sections_probed=sections_probed,
        sections_delta_updated=sections_delta_updated,
    )
```

#### Step 2b extraction: `_probe_freshness`

**Before** (lines 216-269, inside the `elif manifest is not None:` block):
```python
# Step 2b: Probe COMPLETE sections for freshness
if (
    manifest.is_complete()
    and os.environ.get("SECTION_FRESHNESS_PROBE", "1") != "0"
):
    try:
        from autom8_asana.dataframes.builders.freshness import (
            ProbeVerdict,
            SectionFreshnessProber,
        )
        prober = SectionFreshnessProber(...)
        probe_results = await prober.probe_all_async()
        sections_probed = len(probe_results)
        stale = [r for r in probe_results if r.verdict not in (...)]
        if stale:
            sections_delta_updated = await prober.apply_deltas_async(...)
            logger.info("progressive_build_freshness_applied", ...)
    except Exception as e:
        logger.warning("progressive_build_freshness_probe_failed", ...)
```

**After**:
```python
async def _probe_freshness(
    self,
    manifest: SectionManifest,
) -> tuple[int, int]:
    """Probe completed sections for freshness and apply deltas.

    Only runs when manifest is fully complete and probe is enabled.

    Args:
        manifest: Complete manifest to probe.

    Returns:
        Tuple of (sections_probed, sections_delta_updated).
    """
    if not manifest.is_complete():
        return 0, 0

    if os.environ.get("SECTION_FRESHNESS_PROBE", "1") == "0":
        return 0, 0

    try:
        from autom8_asana.dataframes.builders.freshness import (
            ProbeVerdict,
            SectionFreshnessProber,
        )

        prober = SectionFreshnessProber(
            client=self._client,
            persistence=self._persistence,
            project_gid=self._project_gid,
            manifest=manifest,
            schema=self._schema,
            dataframe_view=self._dataframe_view,
        )
        probe_results = await prober.probe_all_async()
        sections_probed = len(probe_results)
        sections_delta_updated = 0

        stale = [
            r
            for r in probe_results
            if r.verdict not in (ProbeVerdict.CLEAN, ProbeVerdict.PROBE_FAILED)
        ]
        if stale:
            sections_delta_updated = await prober.apply_deltas_async(
                stale,
                dataframe_view=self._dataframe_view,
            )

            logger.info(
                "progressive_build_freshness_applied",
                extra={
                    "project_gid": self._project_gid,
                    "sections_probed": sections_probed,
                    "sections_stale": len(stale),
                    "sections_delta_updated": sections_delta_updated,
                },
            )

        return sections_probed, sections_delta_updated

    except Exception as e:
        logger.warning(
            "progressive_build_freshness_probe_failed",
            extra={
                "project_gid": self._project_gid,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return 0, 0
```

#### Step 3 extraction: `_ensure_manifest`

**Before** (lines 271-285):
```python
# Step 3: Create/update manifest
if manifest is None:
    section_names: dict[str, str] = {
        s.gid: s.name for s in sections if isinstance(s.name, str)
    }
    manifest = await self._persistence.create_manifest_async(
        self._project_gid,
        self._entity_type,
        section_gids,
        schema_version=current_schema_version,
        section_names=section_names or None,
    )
# Store manifest for section-level access
self._manifest = manifest
```

**After**:
```python
async def _ensure_manifest(
    self,
    manifest: SectionManifest | None,
    sections: list[Section],
    section_gids: list[str],
) -> SectionManifest:
    """Create manifest if none exists, or return existing.

    Args:
        manifest: Existing manifest from resume check, or None.
        sections: Section objects for name extraction.
        section_gids: All section GIDs.

    Returns:
        SectionManifest (created or existing).
    """
    if manifest is None:
        section_names: dict[str, str] = {
            s.gid: s.name for s in sections if isinstance(s.name, str)
        }
        manifest = await self._persistence.create_manifest_async(
            self._project_gid,
            self._entity_type,
            section_gids,
            schema_version=self._schema.version,
            section_names=section_names or None,
        )

    self._manifest = manifest
    return manifest
```

#### Step 5 extraction: `_merge_section_dataframes`

**Before** (lines 322-343):
```python
# Step 5: Merge all sections from S3, with in-memory fallback
merged_df = await self._persistence.merge_sections_to_dataframe_async(
    self._project_gid
)

if merged_df is None and self._section_dfs:
    merged_df = pl.concat(
        list(self._section_dfs.values()), how="diagonal_relaxed"
    )
    logger.warning(
        "progressive_build_s3_fallback",
        extra={...},
    )

if merged_df is None:
    merged_df = pl.DataFrame(schema=self._schema.to_polars_schema())
```

**After**:
```python
async def _merge_section_dataframes(self) -> pl.DataFrame:
    """Merge all sections from S3, with in-memory fallback.

    Returns:
        Merged DataFrame (may be empty if no sections produced data).
    """
    merged_df = await self._persistence.merge_sections_to_dataframe_async(
        self._project_gid
    )

    if merged_df is None and self._section_dfs:
        merged_df = pl.concat(
            list(self._section_dfs.values()), how="diagonal_relaxed"
        )
        logger.warning(
            "progressive_build_s3_fallback",
            extra={
                "project_gid": self._project_gid,
                "sections_in_memory": len(self._section_dfs),
                "total_rows": len(merged_df),
            },
        )

    if merged_df is None:
        merged_df = pl.DataFrame(schema=self._schema.to_polars_schema())

    return merged_df
```

#### Resulting orchestrator method

The main `build_progressive_async` becomes:
```python
async def build_progressive_async(
    self,
    resume: bool = True,
) -> ProgressiveBuildResult:
    """Build DataFrame with progressive section writes to S3."""
    start_time = time.perf_counter()

    await self._ensure_dataframe_view()

    # Step 1: Get section list
    sections = await self._list_sections()
    section_gids = [s.gid for s in sections]

    if not sections:
        # ... early return (unchanged, 10 lines) ...

    # Step 2: Check resume and probe freshness
    resume_result = await self._check_resume_and_probe(section_gids, resume)

    # Step 3: Ensure manifest exists
    manifest = await self._ensure_manifest(
        resume_result.manifest, sections, section_gids,
    )

    logger.info("preload_project_started", extra={...})

    # Step 4: Fetch and persist incomplete sections (unchanged)
    fetch_time = 0.0
    sections_fetched = 0
    if resume_result.sections_to_fetch:
        fetch_start = time.perf_counter()
        # ... section fetching logic (unchanged, ~15 lines) ...
        sections_fetched = sum(1 for r in results if r)
        fetch_time = (time.perf_counter() - fetch_start) * 1000

    # Step 5: Merge sections
    merged_df = await self._merge_section_dataframes()
    total_rows = len(merged_df)
    watermark = datetime.now(UTC)

    # Step 6: Write final artifacts (unchanged)
    if total_rows > 0:
        index_data = self._build_index_data(merged_df)
        await self._persistence.write_final_artifacts_async(...)

    total_time = (time.perf_counter() - start_time) * 1000
    logger.info("progressive_build_complete", extra={...})
    self._section_dfs.clear()

    return ProgressiveBuildResult(
        df=merged_df,
        watermark=watermark,
        total_rows=total_rows,
        sections_fetched=sections_fetched,
        sections_resumed=resume_result.sections_resumed,
        fetch_time_ms=fetch_time,
        total_time_ms=total_time,
        sections_probed=resume_result.sections_probed,
        sections_delta_updated=resume_result.sections_delta_updated,
    )
```

- **Contract**:
  - `build_progressive_async()` public signature unchanged: `(self, resume: bool = True) -> ProgressiveBuildResult`
  - `ProgressiveBuildResult` fields and values identical for any input
  - All logging messages and extra dicts identical (same event names, same keys)
  - Resume behavior identical: same sections fetched, same sections skipped
  - Freshness probing behavior identical: same probes, same deltas applied
  - `_ResumeResult` is a private internal dataclass, not part of public API
- **Invariants**:
  - All 7938 tests pass without modification
  - `mypy --strict` passes (new dataclass and method signatures are fully typed)
  - No callers of `build_progressive_async()` need changes
  - The `_dataframe_view` field is set before `_probe_freshness` uses it (ensured by `_ensure_dataframe_view()` call on line 158)
- **Verification**:
  1. Run: `python -m pytest tests/unit/dataframes/test_progressive_builder.py -x -q`
  2. Run: `python -m pytest tests/unit/cache/dataframe/test_progressive_tier.py -x -q`
  3. Run: `python -m mypy src/autom8_asana/dataframes/builders/progressive.py --strict`
- **Rollback**: Revert single commit
- **Risk**: MEDIUM -- modifies a critical path method, but the extraction is purely structural. All state transitions and control flow are preserved exactly. The `_ResumeResult` dataclass is the only new type.
- **Commit Message**: `refactor(builders): decompose build_progressive_async into focused private methods`

---

## Phase 2: Side-Channel Formalization (Medium-Risk, Cross-Module)

### RF-L13: Formalize FreshnessInfo propagation with explicit typed returns

- **Addresses**: SM-L005, SM-L028 (partially -- the `_get_freshness_meta` helper was extracted in Sprint 1 RF-L07)
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py:85,412-416`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py:117,374-406`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py:425-438`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:39-50,655-666`

**Current Side-Channel Path**:
```
DataFrameCache._last_freshness[cache_key] = FreshnessInfo(...)     # set in _build_freshness_info (line 693)
       |
       v
DataFrameCache.get_freshness_info(project_gid, entity_type)        # public method (line 655)
       |
       v  (called via getattr lambda)
UniversalResolutionStrategy._last_freshness_info = getattr(...)     # line 414
       |
       v  (set as attribute)
EntityQueryService._last_freshness_info = getattr(strategy, ...)    # line 405
       |
       v  (read via getattr in QueryEngine)
QueryEngine._get_freshness_meta() -> getattr(self.query_service, "_last_freshness_info", None)  # line 431
```

**Problem**: Three `getattr` hops on private attributes. Any rename silently breaks the chain (returns `None`, freshness disappears from API response without error).

**Solution**: Make `FreshnessInfo` an explicit return path from `EntityQueryService.get_dataframe()`. The minimum viable change is:

1. **Change `get_dataframe` return type** to include freshness info
2. **Replace `getattr` reads** with typed attribute access
3. **Keep `_last_freshness` dict** in DataFrameCache (it is correctly designed -- the issue is how it propagates)

#### Step 1: Import FreshnessInfo in query_service.py

**Before** (`query_service.py:117`):
```python
# Side-channel for freshness info from last get_dataframe() call
_last_freshness_info: Any = field(default=None, init=False, repr=False)
```

**After**:
```python
from autom8_asana.cache.dataframe_cache import FreshnessInfo

# Freshness info from last get_dataframe() call
_last_freshness_info: FreshnessInfo | None = field(default=None, init=False, repr=False)
```

#### Step 2: Type the attribute in UniversalResolutionStrategy

**Before** (`universal_strategy.py:85`):
```python
# Side-channel for freshness info from last cache access
_last_freshness_info: Any = field(default=None, repr=False)
```

**After**:
```python
from autom8_asana.cache.dataframe_cache import FreshnessInfo

# Freshness info from last cache access
_last_freshness_info: FreshnessInfo | None = field(default=None, repr=False)
```

#### Step 3: Replace getattr in universal_strategy._get_dataframe

**Before** (`universal_strategy.py:412-416`):
```python
if entry is not None:
    # Retrieve freshness info side-channel
    self._last_freshness_info = getattr(
        cache, "get_freshness_info", lambda *a: None
    )(project_gid, self.entity_type)
    return entry.dataframe
```

**After**:
```python
if entry is not None:
    # Retrieve freshness info via typed public method
    self._last_freshness_info = cache.get_freshness_info(
        project_gid, self.entity_type
    )
    return entry.dataframe
```

The `getattr` was guarding against `cache` not having `get_freshness_info`. Since `cache` is always a `DataFrameCache` instance (returned by `get_dataframe_cache_provider()`), and `get_freshness_info` is a public method (line 655), this guard is unnecessary.

#### Step 4: Replace getattr in query_service.get_dataframe

**Before** (`query_service.py:404-405`):
```python
# Propagate freshness info from strategy
self._last_freshness_info = getattr(strategy, "_last_freshness_info", None)
```

**After**:
```python
# Propagate freshness info from strategy (typed attribute)
self._last_freshness_info = strategy._last_freshness_info
```

Since `strategy` is `UniversalResolutionStrategy` (created by `self.strategy_factory`), and `_last_freshness_info` is now typed as `FreshnessInfo | None` on that class, this is a direct attribute access with full type safety.

#### Step 5: Replace getattr in QueryEngine._get_freshness_meta

**Before** (`engine.py:431`):
```python
freshness_info = getattr(self.query_service, "_last_freshness_info", None)
```

**After**:
```python
freshness_info = self.query_service._last_freshness_info
```

Since `self.query_service` is `EntityQueryService` (typed on line 58), and `_last_freshness_info` is now typed as `FreshnessInfo | None`, this is fully type-safe.

Note: Accessing `_last_freshness_info` from QueryEngine on EntityQueryService still crosses a class boundary via a "private" attribute. However, formalizing this to a fully public method (`get_last_freshness_info()`) would be scope creep for this sprint. The key improvement is: (a) the attribute is now **typed** (`FreshnessInfo | None` instead of `Any`), and (b) `getattr` with silent `None` fallback is replaced with direct attribute access that will produce a clear `AttributeError` if the attribute is renamed.

- **Contract**:
  - `EntityQueryService.get_dataframe()` return type unchanged (`pl.DataFrame`)
  - `QueryEngine.execute_rows()` and `execute_aggregate()` response shapes unchanged
  - `FreshnessInfo` dataclass unchanged (same fields, same types)
  - `DataFrameCache.get_freshness_info()` public method unchanged
  - `_last_freshness_info` attribute exists on both classes; only the type annotation changes from `Any` to `FreshnessInfo | None`
- **Invariants**:
  - API responses include identical `freshness`, `data_age_seconds`, `staleness_ratio` values
  - When no freshness info is available, `freshness_meta` is `{}` (same as before)
  - All existing tests pass -- no test uses `getattr` to read these attributes
- **MUST NOT Change**: FreshnessInfo field names, return values, or the DataFrameCache.get_freshness_info() signature
- **MAY Change**: The `Any` type annotation to `FreshnessInfo | None` (stricter typing)
- **Verification**:
  1. Run: `python -m pytest tests/unit/query/ -x -q`
  2. Run: `python -m pytest tests/unit/services/ -x -q`
  3. Run: `python -m mypy src/autom8_asana/query/engine.py src/autom8_asana/services/query_service.py src/autom8_asana/services/universal_strategy.py --strict`
  4. Verify no remaining `getattr.*freshness` in codebase: `rg "getattr.*freshness" src/`
- **Rollback**: Revert single commit
- **Risk**: MEDIUM -- touches 4 files across 3 packages, but each change is a 1-3 line type annotation or `getattr` removal. The `TYPE_CHECKING` import of `FreshnessInfo` in `query_service.py` and `universal_strategy.py` avoids circular imports (both already import from other cache modules). If circular import occurs, use `if TYPE_CHECKING:` guard with string annotation.
- **Commit Message**: `refactor(cache): formalize FreshnessInfo propagation with typed attributes replacing getattr`

---

## Phase 3: Backend Error Handling Extraction (Medium-Risk, Multi-File)

### RF-L14: Extract degraded mode handler and shared error classification

- **Addresses**: SM-L003, SM-L004
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py:127-128,165,188-205,725-755`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:136-138,178,201-217,770-828`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/async_s3.py:187-189,246-265,586-680`
  - New: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/errors.py`

**Current Duplication**:

| Feature | Redis (redis.py) | S3 (s3.py) | AsyncS3 (async_s3.py) |
|---------|-------------------|------------|----------------------|
| `_degraded` bool | line 127 | line 137 | line 187 |
| `_last_reconnect_attempt` float | line 128 | line 138 | `_last_error_time` (line 188) |
| Reconnect interval | `self._settings.reconnect_interval` (30s) | `self._settings.reconnect_interval` (30s) | `self._degraded_backoff = 60.0` (HARDCODED) |
| `_attempt_reconnect()` | lines 188-205 | lines 201-217 | lines 258-263 (inline in `_get_client`) |
| Error classification | `_handle_redis_error` (lines 725-755) | `_handle_s3_error` (lines 770-828) | `_handle_error` (lines 646-680) |
| Not-found check | N/A | `_is_not_found_error` (lines 751-768) | `_is_not_found_error` (lines 586-604) |
| Retryable check | N/A | N/A | `_is_retryable_error` (lines 606-644) |
| Base error types | `(ConnectionError, TimeoutError, OSError)` | `(ConnectionError, TimeoutError, OSError)` | `(ConnectionError, TimeoutError, asyncio.TimeoutError, OSError)` |

**Design Decision**: Extract a `DegradedModeMixin` class rather than a base class, because the three backends have different class hierarchies (Redis and S3 are plain classes, AsyncS3 is an async context manager). A mixin is composable without disrupting the existing inheritance.

#### New file: `cache/errors.py`

```python
"""Shared error classification and degraded mode handling for cache backends.

Extracted from redis.py, s3.py, and async_s3.py to eliminate duplicated
degraded-mode state machines and error classification logic.
"""
from __future__ import annotations

import time
from typing import Any

from autom8y_log import get_logger

logger = get_logger(__name__)


# Base error types that trigger degraded mode across all backends
CONNECTION_ERROR_TYPES: tuple[type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def is_connection_error(
    error: Exception,
    *,
    extra_types: tuple[type[Exception], ...] = (),
) -> bool:
    """Check if error is a connection/timeout error.

    Args:
        error: Exception to classify.
        extra_types: Additional backend-specific error types.

    Returns:
        True if error indicates a connection or timeout failure.
    """
    return isinstance(error, CONNECTION_ERROR_TYPES + extra_types)


def is_s3_not_found_error(error: Exception) -> bool:
    """Check if error indicates S3 object not found (404/NoSuchKey).

    Handles both botocore ClientError and string-pattern matching
    for compatibility with both sync and async S3 clients.

    Args:
        error: Exception to check.

    Returns:
        True if error indicates object not found.
    """
    # Check botocore ClientError response
    if hasattr(error, "response"):
        error_code = error.response.get("Error", {}).get("Code", "")
        if error_code in ("NoSuchKey", "404", "NotFound"):
            return True

    # Check exception class name
    if type(error).__name__ in ("NoSuchKey", "NotFound"):
        return True

    # Check string patterns (used by async_s3.py)
    error_str = str(error).lower()
    if "nosuchkey" in error_str or "not found" in error_str or "404" in error_str:
        return True

    return False


def is_s3_retryable_error(error: Exception) -> bool:
    """Check if S3 error is transient and should be retried.

    Args:
        error: Exception to check.

    Returns:
        True if error is transient (throttling, 5xx, timeout).
    """
    import asyncio

    # Specific exception types
    if isinstance(error, (ConnectionError, TimeoutError, asyncio.TimeoutError, OSError)):
        return True

    # Check botocore error codes
    if hasattr(error, "response"):
        error_code = error.response.get("Error", {}).get("Code", "")
        if error_code in (
            "SlowDown",
            "ServiceUnavailable",
            "InternalError",
            "RequestTimeout",
        ):
            return True

    # String pattern matching for broader compatibility
    error_str = str(error).lower()
    retryable_patterns = [
        "timeout", "connection", "throttl", "slowdown",
        "503", "500", "serviceunav",
    ]
    return any(pattern in error_str for pattern in retryable_patterns)


class DegradedModeMixin:
    """Mixin providing degraded mode state machine for cache backends.

    Manages the _degraded flag, reconnect timing, and mode transitions.
    Backends using this mixin must initialize `_degraded`, `_last_reconnect_attempt`,
    and `_reconnect_interval` attributes.

    Usage:
        class MyBackend(DegradedModeMixin):
            def __init__(self):
                self._degraded = False
                self._last_reconnect_attempt = 0.0
                self._reconnect_interval = 30.0
    """

    _degraded: bool
    _last_reconnect_attempt: float
    _reconnect_interval: float

    def enter_degraded_mode(self, reason: str) -> None:
        """Enter degraded mode with logging.

        Only logs on first entry (not if already degraded).

        Args:
            reason: Human-readable reason for entering degraded mode.
        """
        if not self._degraded:
            logger.warning(
                "backend_entering_degraded_mode",
                extra={
                    "backend": type(self).__name__,
                    "reason": reason,
                },
            )
            self._degraded = True

    def should_attempt_reconnect(self) -> bool:
        """Check if enough time has passed to attempt reconnection.

        Returns:
            True if reconnect should be attempted.
        """
        if not self._degraded:
            return False
        return time.time() - self._last_reconnect_attempt >= self._reconnect_interval

    def record_reconnect_attempt(self) -> None:
        """Record that a reconnect attempt is being made."""
        self._last_reconnect_attempt = time.time()

    def exit_degraded_mode(self) -> None:
        """Exit degraded mode (connection restored)."""
        self._degraded = False
```

#### Changes to redis.py

**Before** (`redis.py:127-128,188-205,725-755`):
```python
# In __init__:
self._degraded = False
self._last_reconnect_attempt = 0.0

# _attempt_reconnect (18 lines):
def _attempt_reconnect(self) -> None:
    now = time.time()
    if now - self._last_reconnect_attempt < self._settings.reconnect_interval:
        return
    with self._pool_lock:
        self._last_reconnect_attempt = now
        try:
            self._initialize_pool()
            if self._pool is not None and self._redis_module is not None:
                redis_cls = self._redis_module.Redis
                conn = redis_cls(connection_pool=self._pool)
                conn.ping()
                self._degraded = False
                logger.info("Redis connection restored")
        except Exception as e:
            logger.warning(f"Redis reconnect failed: {e}")

# _handle_redis_error (31 lines):
def _handle_redis_error(self, error: Exception) -> None:
    error_types = (ConnectionError, TimeoutError, OSError,)
    if self._redis_module is not None:
        # ... build error_types tuple with redis-specific exceptions ...
    if isinstance(error, error_types):
        if not self._degraded:
            logger.warning(f"Redis error, entering degraded mode: {error}")
            self._degraded = True
    else:
        logger.error(f"Redis error: {error}")
```

**After**:
```python
from autom8_asana.cache.errors import DegradedModeMixin, is_connection_error

class RedisCacheProvider(DegradedModeMixin):
    # In __init__:
    self._degraded = False
    self._last_reconnect_attempt = 0.0
    self._reconnect_interval = float(self._settings.reconnect_interval)

    def _attempt_reconnect(self) -> None:
        """Attempt to reconnect to Redis if in degraded mode."""
        if not self.should_attempt_reconnect():
            return

        with self._pool_lock:
            self.record_reconnect_attempt()
            try:
                self._initialize_pool()
                if self._pool is not None and self._redis_module is not None:
                    redis_cls = self._redis_module.Redis
                    conn = redis_cls(connection_pool=self._pool)
                    conn.ping()
                    self.exit_degraded_mode()
                    logger.info("Redis connection restored")
            except Exception as e:
                logger.warning(
                    "redis_reconnect_failed",
                    extra={"error": str(e)},
                )

    def _handle_redis_error(self, error: Exception) -> None:
        """Handle Redis errors and potentially enter degraded mode."""
        extra_types: tuple[type[Exception], ...] = ()
        if self._redis_module is not None:
            redis_connection_error = getattr(
                self._redis_module, "ConnectionError", Exception
            )
            redis_timeout_error = getattr(self._redis_module, "TimeoutError", Exception)
            redis_error = getattr(self._redis_module, "RedisError", Exception)
            extra_types = (redis_connection_error, redis_timeout_error, redis_error)

        if is_connection_error(error, extra_types=extra_types):
            self.enter_degraded_mode(str(error))
        else:
            logger.error(
                "redis_error",
                extra={"error": str(error), "error_type": type(error).__name__},
            )
```

#### Changes to s3.py

Same pattern as Redis. Additionally:

**Before** (`s3.py:751-768`):
```python
def _is_not_found_error(self, error: Exception) -> bool:
    if self._botocore_module is None:
        return False
    client_error = getattr(self._botocore_module, "ClientError", Exception)
    if isinstance(error, client_error):
        error_code = error.response.get("Error", {}).get("Code", "")
        return error_code in ("NoSuchKey", "404", "NotFound")
    return False
```

**After**:
```python
from autom8_asana.cache.errors import is_s3_not_found_error

def _is_not_found_error(self, error: Exception) -> bool:
    """Check if error indicates object not found."""
    return is_s3_not_found_error(error)
```

#### Changes to async_s3.py

**Key divergence fix**: Replace hardcoded `self._degraded_backoff = 60.0` with configurable interval.

**Before** (`async_s3.py:189`):
```python
self._degraded_backoff = 60.0  # seconds before retry in degraded mode
```

**After**:
```python
self._reconnect_interval = 60.0  # seconds before retry in degraded mode
```

And replace `_is_not_found_error`, `_is_retryable_error`, `_handle_error`:

**Before** (`async_s3.py:586-680`):
```python
def _is_not_found_error(self, error: Exception) -> bool:
    error_str = str(error).lower()
    error_class = type(error).__name__
    if "nosuchkey" in error_str or "not found" in error_str:
        return True
    # ... 18 more lines ...

def _is_retryable_error(self, error: Exception) -> bool:
    error_str = str(error).lower()
    retryable_patterns = [...]
    # ... 38 more lines ...

def _handle_error(self, error: Exception, operation: str, key: str) -> None:
    # ... 35 lines ...
```

**After**:
```python
from autom8_asana.cache.errors import (
    DegradedModeMixin,
    is_s3_not_found_error,
    is_s3_retryable_error,
)

class AsyncS3Client(DegradedModeMixin):
    # In __init__:
    self._reconnect_interval = 60.0

    def _is_not_found_error(self, error: Exception) -> bool:
        return is_s3_not_found_error(error)

    def _is_retryable_error(self, error: Exception) -> bool:
        return is_s3_retryable_error(error)

    def _handle_error(self, error: Exception, operation: str, key: str) -> None:
        """Handle S3 errors and potentially enter degraded mode."""
        if hasattr(error, "response"):
            error_code = error.response.get("Error", {}).get("Code", "")
            if error_code in ("AccessDenied", "NoSuchBucket"):
                self.enter_degraded_mode(str(error))
                self._last_error_time = time.time()
                return

        if isinstance(error, (ConnectionError, TimeoutError, asyncio.TimeoutError)):
            self.enter_degraded_mode(str(error))
            self._last_error_time = time.time()
        else:
            logger.error(
                "s3_error",
                extra={
                    "operation": operation,
                    "key": key,
                    "error": str(error),
                },
            )
```

Note: `AsyncS3Client._get_client()` (lines 246-265) uses `self._degraded_backoff` and `self._last_error_time` for its own reconnect logic (different from the mixin pattern -- it checks time inline rather than using `_attempt_reconnect`). We rename `_degraded_backoff` to `_reconnect_interval` for consistency, but keep the inline reconnect logic in `_get_client` unchanged to avoid changing the async behavior.

- **Contract**:
  - All three backends' public API signatures unchanged
  - Degraded mode entry/exit behavior identical (same logging, same timing)
  - `_is_not_found_error` returns same boolean for same error inputs
  - `_is_retryable_error` returns same boolean for same error inputs
  - `_handle_redis_error`, `_handle_s3_error`, `_handle_error` enter degraded mode for same error types
- **Invariants**:
  - Redis reconnect interval: still `self._settings.reconnect_interval` (30s default)
  - S3 reconnect interval: still `self._settings.reconnect_interval` (30s default)
  - AsyncS3 reconnect interval: still 60s (renamed from `_degraded_backoff` to `_reconnect_interval`)
  - All backend tests pass without modification
- **BEHAVIOR NOTE**: The f-string log messages in `_handle_redis_error` and `_handle_s3_error` will change to structured logging as part of this refactor (the mixin uses `extra={}` pattern). This is intentional -- these are the exact same messages that RF-L15 would migrate. Doing it here avoids double-touching these lines.
- **Verification**:
  1. Run: `python -m pytest tests/unit/cache/test_redis_backend.py -x -q`
  2. Run: `python -m pytest tests/unit/cache/test_s3_backend.py -x -q`
  3. Run: `python -m pytest tests/integration/test_s3_persistence_e2e.py -x -q`
  4. Run: `python -m mypy src/autom8_asana/cache/errors.py src/autom8_asana/cache/backends/redis.py src/autom8_asana/cache/backends/s3.py src/autom8_asana/dataframes/async_s3.py --strict`
- **Rollback**: Revert single commit. The new `cache/errors.py` file is deleted, backends revert to inline implementations.
- **Risk**: MEDIUM -- touches 3 backends plus creates a new file. However, the mixin is additive (adds methods, does not remove any). The error classification functions are pure (no side effects). The riskiest part is ensuring `_reconnect_interval` is set before `should_attempt_reconnect()` is called, which is guaranteed by `__init__` ordering.
- **Commit Message**: `refactor(cache): extract DegradedModeMixin and shared error classification into cache/errors.py`

---

## Phase 4: Structured Logging Migration (Low-Risk, High-Volume)

### RF-L15: Migrate f-string logging to structured extra={} pattern

- **Addresses**: SM-L014
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py` -- 9 instances
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py` -- ~15 instances
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py` -- ~10 instances

Note: Some instances in redis.py and s3.py will already be migrated by RF-L14 (the error handler messages). This task covers the remaining instances.

**Pattern Catalog** (before/after for each pattern category):

#### Pattern A: Error context in warning/error logs

**Before** (tiered.py:169):
```python
logger.warning(f"S3 delete failed for {key}, continuing: {e}")
```

**After**:
```python
logger.warning(
    "s3_delete_failed",
    extra={"key": key, "error": str(e)},
)
```

#### Pattern B: Operation failure with key and entry type

**Before** (tiered.py:212):
```python
logger.warning(f"S3 get_versioned failed for {key}/{entry_type.value}: {e}")
```

**After**:
```python
logger.warning(
    "s3_get_versioned_failed",
    extra={"key": key, "entry_type": entry_type.value, "error": str(e)},
)
```

#### Pattern C: Redis pool initialization failure

**Before** (redis.py:165):
```python
logger.error(f"Failed to initialize Redis pool: {e}")
```

**After**:
```python
logger.error(
    "redis_pool_init_failed",
    extra={"error": str(e), "error_type": type(e).__name__},
)
```

#### Pattern D: Import/availability warnings (no variables)

**Before** (redis.py:139):
```python
logger.warning(
    "redis package not installed. RedisCacheProvider will operate in degraded mode."
)
```

**After**:
```python
logger.warning(
    "redis_package_not_installed",
    extra={"fallback": "degraded_mode"},
)
```

#### Pattern E: Deserialization failure

**Before** (redis.py:294):
```python
logger.warning(f"Failed to deserialize cache entry for {key}: {e}")
```

**After**:
```python
logger.warning(
    "cache_entry_deserialize_failed",
    extra={"key": key, "error": str(e)},
)
```

#### Pattern F: Warm stub

**Before** (redis.py:616):
```python
logger.info(f"Cache warm requested for {len(gids)} GIDs (not yet implemented)")
```

**After**:
```python
logger.info(
    "cache_warm_requested",
    extra={"gid_count": len(gids), "status": "not_implemented"},
)
```

#### Pattern G: Batch operation failure

**Before** (tiered.py:297):
```python
logger.warning(f"S3 get_batch failed for {len(missed_keys)} keys: {e}")
```

**After**:
```python
logger.warning(
    "s3_get_batch_failed",
    extra={"key_count": len(missed_keys), "error": str(e)},
)
```

**Complete Instance Inventory** (verified against source):

| File | Line | Pattern | Current Message |
|------|------|---------|----------------|
| tiered.py | 169 | A | `f"S3 delete failed for {key}, continuing: {e}"` |
| tiered.py | 212 | B | `f"S3 get_versioned failed for {key}/{entry_type.value}: {e}"` |
| tiered.py | 228 | A | `f"Promotion to Redis failed for {key}: {e}"` |
| tiered.py | 258 | B | `f"S3 write-through failed for {key}/{entry.entry_type.value}: {e}"` |
| tiered.py | 297 | G | `f"S3 get_batch failed for {len(missed_keys)} keys: {e}"` |
| tiered.py | 318 | A | `f"Batch promotion to Redis failed: {e}"` |
| tiered.py | 345 | A | `f"S3 batch write-through failed: {e}"` |
| tiered.py | 408 | A | `f"S3 invalidate failed for {key}: {e}"` |
| tiered.py | 460 | A | `f"Redis clear_all_tasks failed: {e}"` |
| tiered.py | 470 | A | `f"S3 clear_all_tasks failed: {e}"` |
| redis.py | 139 | D | `"redis package not installed..."` |
| redis.py | 165 | C | `f"Failed to initialize Redis pool: {e}"` |
| redis.py | 205 | A | `f"Redis reconnect failed: {e}"` |
| redis.py | 294 | E | `f"Failed to deserialize cache entry for {key}: {e}"` |
| redis.py | 616 | F | `f"Cache warm requested for {len(gids)} GIDs..."` |
| redis.py | 752 | A | `f"Redis error, entering degraded mode: {error}"` |
| redis.py | 755 | A | `f"Redis error: {error}"` |
| s3.py | 122 | D | `"No S3 bucket configured..."` |
| s3.py | 153 | D | `"boto3 package not installed..."` |
| s3.py | 163 | D | `"No S3 bucket configured..."` |
| s3.py | 178 | C | `f"Failed to initialize S3 client: {e}"` |
| s3.py | 217 | A | `f"S3 reconnect failed: {e}"` |
| s3.py | 333 | E | `f"Failed to deserialize S3 cache entry for {key}: {e}"` |
| s3.py | 639 | F | `f"S3 cache warm requested for {len(gids)} GIDs..."` |
| s3.py | 818 | A | `f"S3 access error, entering degraded mode: {error}"` |
| s3.py | 825 | A | `f"S3 error, entering degraded mode: {error}"` |
| s3.py | 828 | A | `f"S3 error: {error}"` |

Note: Lines in redis.py (752, 755) and s3.py (818, 825, 828) are inside `_handle_redis_error` and `_handle_s3_error` respectively. If RF-L14 migrates these as part of the mixin extraction, they should be SKIPPED in RF-L15. The Janitor should check which instances remain after RF-L14 before executing RF-L15.

- **Contract**:
  - No public API changes
  - Same log levels (warning stays warning, error stays error, info stays info)
  - Log event names are new (e.g., `"s3_delete_failed"` instead of `f"S3 delete failed for..."`) but these are not part of any contract -- they are internal observability
  - The `extra={}` dict keys use snake_case consistently
- **Invariants**:
  - All existing tests pass (no test asserts on log message text)
  - `ruff check` passes (f-string removal does not affect lint)
  - `mypy --strict` passes (no type changes)
- **Verification**:
  1. Run: `python -m pytest tests/unit/cache/test_tiered.py tests/unit/cache/test_redis_backend.py tests/unit/cache/test_s3_backend.py -x -q`
  2. Verify no remaining f-string logs: `rg 'logger\.(warning|error|info)\(f"' src/autom8_asana/cache/tiered.py src/autom8_asana/cache/backends/redis.py src/autom8_asana/cache/backends/s3.py`
  3. Run: `python -m mypy src/autom8_asana/cache/tiered.py src/autom8_asana/cache/backends/redis.py src/autom8_asana/cache/backends/s3.py --strict`
- **Rollback**: Revert single commit
- **Risk**: LOW -- each change is a mechanical transformation of log format. No control flow, no data flow changes. The only risk is a typo in an event name or missing a variable in the `extra` dict, both of which are caught by testing.
- **Commit Message**: `refactor(cache): migrate f-string logging to structured extra={} in tiered and backend modules`

---

## Execution Order

```
Phase 1 (single file, no external dependencies):
  RF-L12   (progressive.py decomposition)

Phase 2 (depends on Phase 1 being clean -- no code dependency, but clean diffs):
  RF-L13   (FreshnessInfo formalization, 4 files)

Phase 3 (independent of Phases 1-2):
  RF-L14   (error handling extraction, 3 files + 1 new)

Phase 4 (MUST follow Phase 3 -- RF-L14 migrates some log lines):
  RF-L15   (logging migration, 3 files)
```

**Dependencies**:
- RF-L14 creates `cache/errors.py` and migrates some f-string logs in error handlers. RF-L15 MUST run after RF-L14 to avoid editing the same lines twice.
- RF-L12 and RF-L13 are independent of RF-L14/RF-L15 and can be done in any order relative to them.
- RF-L12 should be done first because it is the most complex decomposition and benefits from a clean diff baseline.

**Rollback Points**:
- After RF-L12: Single commit, independently revertible
- After RF-L13: Single commit, independently revertible (does not depend on RF-L12)
- After RF-L14: Single commit, revertible. Reverting removes `cache/errors.py` and restores inline implementations
- After RF-L15: Single commit, revertible. Note: if RF-L14 is reverted but RF-L15 is not, the error handler log lines will be inconsistent (RF-L15 migrated the non-error-handler lines, RF-L14 revert restores f-string error handler lines). Best to revert RF-L15 first, then RF-L14.

---

## Risk Matrix

| RF-L | Risk | Blast Radius | Failure Detection | Recovery |
|------|------|-------------|-------------------|----------|
| RF-L12 | MEDIUM | 1 file (critical build path) | Progressive builder tests (7+), mypy | Revert 1 commit |
| RF-L13 | MEDIUM | 4 files across 3 packages | Query engine tests, mypy strict, rg for getattr | Revert 1 commit |
| RF-L14 | MEDIUM | 3 files + 1 new (all backends) | Backend unit tests (3 suites), integration test, mypy | Revert 1 commit |
| RF-L15 | LOW | 3 files (logging only) | Unit tests (3 suites), rg for f-string logs | Revert 1 commit |

---

## Verification Commands

After each commit:
```bash
# Type checking
python -m mypy src/autom8_asana --strict

# Lint
python -m ruff check src/autom8_asana

# Per-phase tests:
# RF-L12:
python -m pytest tests/unit/dataframes/test_progressive_builder.py tests/unit/cache/dataframe/test_progressive_tier.py -x -q

# RF-L13:
python -m pytest tests/unit/query/test_engine.py tests/unit/services/ -x -q

# RF-L14:
python -m pytest tests/unit/cache/test_redis_backend.py tests/unit/cache/test_s3_backend.py tests/integration/test_s3_persistence_e2e.py -x -q

# RF-L15:
python -m pytest tests/unit/cache/test_tiered.py tests/unit/cache/test_redis_backend.py tests/unit/cache/test_s3_backend.py -x -q

# Full verification (run after all phases):
python -m pytest tests/ -x
python -m mypy src/autom8_asana --strict
python -m ruff check src/autom8_asana
```

---

## Janitor Notes

1. **Commit convention**: Each RF-L task = one atomic commit. Use the suggested commit message. Include `Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>`.
2. **New files**: RF-L14 creates `cache/errors.py`. Include `from __future__ import annotations` per project convention.
3. **RF-L12 `_ResumeResult` placement**: Define the `_ResumeResult` dataclass inside `progressive.py` at module level, above the `ProgressiveProjectBuilder` class. Prefix with underscore to indicate it is private to the module.
4. **RF-L13 import strategy**: Use direct import `from autom8_asana.cache.dataframe_cache import FreshnessInfo` in both `query_service.py` and `universal_strategy.py`. If circular import occurs, wrap in `if TYPE_CHECKING:` and use string annotation `"FreshnessInfo | None"`.
5. **RF-L14 critical ordering**: The mixin's `__init__` does NOT set `_degraded`, `_last_reconnect_attempt`, or `_reconnect_interval`. Each backend must set these in its own `__init__` BEFORE any method that calls `should_attempt_reconnect()`. Verify by reading each `__init__` after the change.
6. **RF-L15 post-RF-L14 check**: Before starting RF-L15, run `rg 'logger\.(warning|error|info)\(f"' src/autom8_asana/cache/backends/redis.py src/autom8_asana/cache/backends/s3.py` to see which f-string instances remain after RF-L14. Only migrate those.
7. **RF-L15 event naming**: Use snake_case event names derived from the operation (e.g., `"s3_delete_failed"`, `"redis_pool_init_failed"`). Do not include dynamic values in event names.
8. **Test before committing**: Run the phase-specific test commands. If any test fails, do NOT proceed. Investigate within the same task scope, or flag for architect review.

---

## Deferred Items (Sprint 3 Candidates)

| ID | Finding | Reason for Deferral |
|----|---------|-------------------|
| SM-L008 | `_fetch_and_persist_section` decomposition (247 lines) | Depends on SM-L009 (SectionPersistence public API). Could be Sprint 3 once RF-L12 proves the decomposition pattern. |
| SM-L009 | SectionPersistence public API for checkpoint operations | Requires design discussion about which private methods to promote. The checkpoint write path intentionally bypasses the public API. |
| SM-L010 | Statistics pattern standardization (dict vs CacheMetrics) | Cross-subsystem change affecting observability dashboards. Needs coordination with monitoring setup. |
| SM-L016 | S3 batch parallelization | Performance optimization, not refactoring. Needs load testing. |
| SM-L022 | Extract `_swr_build` closure (factory.py) | Already addressed in Sprint 1 as RF-L10. Verify it was completed. |

---

## Verification Attestation

| Source File | Lines Read | Purpose |
|-------------|-----------|---------|
| `.claude/artifacts/smell-report-cache-landscape.md` | 1-549 (full) | Input smell report |
| `.claude/artifacts/refactoring-plan-cache-landscape.md` | 1-692 (full) | Sprint 1 plan reference |
| `src/autom8_asana/dataframes/builders/progressive.py` | 1-961 (full) | RF-L12 contract verification |
| `src/autom8_asana/cache/dataframe_cache.py` | 1-884 (full) | RF-L13 contract verification |
| `src/autom8_asana/services/query_service.py` | 1-407 (full) | RF-L13 contract verification |
| `src/autom8_asana/query/engine.py` | 1-439 (full) | RF-L13 contract verification |
| `src/autom8_asana/services/universal_strategy.py` | 1-630 (full) | RF-L13 contract verification |
| `src/autom8_asana/cache/backends/redis.py` | 1-813 (full) | RF-L14, RF-L15 contract verification |
| `src/autom8_asana/cache/backends/s3.py` | 1-900 (full) | RF-L14, RF-L15 contract verification |
| `src/autom8_asana/dataframes/async_s3.py` | 1-681 (full) | RF-L14 contract verification |
| `src/autom8_asana/cache/tiered.py` | 1-519 (full) | RF-L15 contract verification |
| `src/autom8_asana/cache/settings.py` | 1-182 (full) | RF-L14 reconnect_interval verification |
| `src/autom8_asana/cache/metrics.py` | 1-577 (full) | RF-L14 CacheMetrics reference |
