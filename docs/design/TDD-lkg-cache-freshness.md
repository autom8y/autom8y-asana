# TDD: LKG Cache Freshness Production Deployment

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Date** | 2026-02-03 |
| **Author** | Architect |
| **Upstream** | LKG_PROTOTYPE_FINDINGS.md, SPIKE-cache-freshness-patterns.md, SPIKE-cache-freshness-integration-map.md |
| **PRD Ref** | Cache Freshness Remediation (eliminate 503 CACHE_NOT_WARMED) |
| **Complexity** | MODULE |

---

## 1. Overview

Ship the Last-Known-Good (LKG) cache freshness pattern to production. A validated prototype (Option A: Minimal LKG) exists in the working tree with all 37 tests passing. This TDD specifies the remaining production work across two groups:

- **Group A (Cache Layer)**: Circuit breaker LKG serving + max-staleness enforcement
- **Group B (API Layer)**: FreshnessInfo side-channel + response model enrichment

The prototype established the baseline: `FreshnessStatus` enum with five states, `_check_freshness()` returning granular status, `_check_freshness_and_serve()` serving `EXPIRED_SERVABLE` entries as LKG. This TDD builds on that baseline without redesigning what already works.

---

## 2. System Context

```
                           Query Request
                                |
                                v
                    +-------------------+
                    |  query_v2 routes  |
                    +-------------------+
                                |
                                v
                    +-------------------+
                    |   QueryEngine     |  <-- Constructs RowsMeta / AggregateMeta
                    +-------------------+
                                |
                                v
                    +-------------------+
                    | EntityQueryService|  <-- get_dataframe() wrapper
                    +-------------------+
                                |
                                v
                    +-------------------+
                    | UniversalStrategy |  <-- _get_dataframe()
                    +-------------------+
                                |
                                v
                    +-------------------+
                    |  DataFrameCache   |  <-- get_async() with LKG
                    +-------------------+
                     /                \
              MemoryTier        ProgressiveTier (S3)
```

**Data flow for FreshnessInfo threading (Group B):**

```
DataFrameCache._check_freshness_and_serve()
    |
    |-- stores FreshnessInfo in self._last_freshness[cache_key]
    |
    v
DataFrameCache.get_async() returns CacheEntry
    |
    v
UniversalStrategy._get_dataframe() calls cache.get_freshness_info()
    |-- returns FreshnessInfo | None
    |
    v
EntityQueryService.get_dataframe() receives (DataFrame, FreshnessInfo)
    |
    v
QueryEngine.execute_rows() / execute_aggregate()
    |-- populates RowsMeta / AggregateMeta freshness fields from FreshnessInfo
    |
    v
RowsResponse / AggregateResponse (API response with freshness metadata)
```

---

## 3. Group A: Cache Layer

### A1: Circuit Breaker LKG Serving

**Problem**: When circuit breaker is open (line 248-257 of `dataframe_cache.py`), `get_async()` returns `None` immediately. This causes 503 even when valid cached data exists.

**Design**: When circuit is open, attempt to serve from cache tiers (memory then S3) with schema validation, but skip any refresh triggers.

**Method changes to `get_async()` (lines 246-257):**

```python
# Replace the current circuit breaker block:
if self.circuit_breaker.is_open(project_gid):
    self._stats[entity_type]["circuit_breaks"] += 1
    logger.warning(
        "dataframe_cache_circuit_open",
        extra={
            "project_gid": project_gid,
            "entity_type": entity_type,
        },
    )
    # LKG: attempt to serve from cache, skip refresh
    entry = self.memory_tier.get(cache_key)
    if entry is not None and self._schema_is_valid(entry):
        self._stats[entity_type]["lkg_circuit_serves"] += 1
        self._stats[entity_type]["memory_hits"] += 1
        logger.info(
            "dataframe_cache_circuit_lkg_serve",
            extra={
                "project_gid": project_gid,
                "entity_type": entity_type,
                "tier": "memory",
                "row_count": entry.row_count,
            },
        )
        return entry

    # Try progressive tier (read-only, no refresh)
    entry = await self.progressive_tier.get_async(cache_key)
    if entry is not None and self._schema_is_valid(entry):
        self.memory_tier.put(cache_key, entry)
        self._stats[entity_type]["lkg_circuit_serves"] += 1
        self._stats[entity_type]["s3_hits"] += 1
        logger.info(
            "dataframe_cache_circuit_lkg_serve",
            extra={
                "project_gid": project_gid,
                "entity_type": entity_type,
                "tier": "s3",
                "row_count": entry.row_count,
            },
        )
        return entry

    logger.warning(
        "dataframe_cache_circuit_open_no_lkg",
        extra={
            "project_gid": project_gid,
            "entity_type": entity_type,
        },
    )
    return None
```

**New helper method `_schema_is_valid()`:**

Extract schema validation logic from `_check_freshness()` into a reusable helper. This avoids duplicating the schema registry lookup and version comparison.

```python
def _schema_is_valid(self, entry: CacheEntry) -> bool:
    """Check if entry schema version matches current registry.

    Returns True if schema is valid, False on mismatch or lookup failure.
    Used by circuit breaker LKG path where full freshness check is not needed.
    """
    expected_version = _get_schema_version_for_entity(entry.entity_type)
    if expected_version is None:
        return False
    return entry.schema_version == expected_version
```

**New stat counter**: Add `"lkg_circuit_serves": 0` to `_ensure_stats()`.

**Constraints**:
- Schema mismatch data is NEVER served, even under circuit breaker open
- No refresh trigger when circuit is open (the whole point of the circuit breaker)
- Watermark check is intentionally SKIPPED under circuit breaker -- we cannot verify watermark without calling upstream, and the circuit is open because upstream is failing

### A2: LKG_MAX_STALENESS_MULTIPLIER Enforcement

**Problem**: The prototype sets `LKG_MAX_STALENESS_MULTIPLIER = 0.0` (unlimited). Production needs a safety valve to reject data that is excessively stale.

**Design**: Add staleness enforcement in `_check_freshness_and_serve()` within the `EXPIRED_SERVABLE` branch, BEFORE serving. This keeps `_check_freshness()` pure for status determination while policy enforcement lives in the serve layer.

**Changes to `_check_freshness_and_serve()` (after line 331, within the EXPIRED_SERVABLE block):**

```python
if status == FreshnessStatus.EXPIRED_SERVABLE:
    # Check max staleness policy before serving
    from autom8_asana.config import (
        DEFAULT_ENTITY_TTLS,
        DEFAULT_TTL,
        LKG_MAX_STALENESS_MULTIPLIER,
    )

    if LKG_MAX_STALENESS_MULTIPLIER > 0:
        entity_ttl = DEFAULT_ENTITY_TTLS.get(entry.entity_type, DEFAULT_TTL)
        age = (datetime.now(UTC) - entry.created_at).total_seconds()
        max_age = LKG_MAX_STALENESS_MULTIPLIER * entity_ttl
        if age > max_age:
            logger.warning(
                f"dataframe_cache_{tier}_lkg_max_staleness_exceeded",
                extra={
                    "project_gid": project_gid,
                    "entity_type": entity_type,
                    "age_seconds": round(age, 1),
                    "max_age_seconds": round(max_age, 1),
                    "staleness_ratio": round(age / entity_ttl, 2),
                },
            )
            if tier == "memory":
                self.memory_tier.remove(cache_key)
            return None

    # Existing LKG serve logic follows...
    self._stats[entity_type][f"{tier}_hits"] += 1
    self._stats[entity_type]["lkg_serves"] += 1
    # ...
```

**Rationale for separation from `_check_freshness()`**: `_check_freshness()` answers "what IS the freshness state?" while `_check_freshness_and_serve()` answers "should we SERVE given this state?" The max-staleness multiplier is a serving policy, not a freshness determination.

---

## 4. Group B: API Layer

### B1: FreshnessInfo Dataclass

**File**: `src/autom8_asana/cache/dataframe_cache.py`

Add a simple dataclass to carry freshness metadata from the cache layer to the API layer.

```python
@dataclass
class FreshnessInfo:
    """Freshness metadata for a cache serve operation.

    Carried as a side-channel from DataFrameCache to API response.
    Not stored in CacheEntry (freshness changes over time as data ages).
    """

    freshness: str       # "fresh" | "stale_servable" | "expired_servable"
    data_age_seconds: float
    staleness_ratio: float  # age / entity_ttl (>1.0 means past TTL)
```

**Constraints**: This is a simple dataclass, not a wrapper around CacheEntry. It carries computed metadata, not the entry itself.

### B2: Staleness Side-Channel on Cache Instance

**File**: `src/autom8_asana/cache/dataframe_cache.py`

Add a per-cache-key dictionary to store the most recent FreshnessInfo after each `_check_freshness_and_serve()` call.

**New instance field on `DataFrameCache`:**

```python
# Last freshness info per cache key (side-channel for API layer)
_last_freshness: dict[str, FreshnessInfo] = field(
    default_factory=dict, init=False, repr=False
)
```

**Changes to `_check_freshness_and_serve()`**: After computing `age` and determining `status`, store FreshnessInfo before returning:

```python
def _check_freshness_and_serve(self, entry, current_watermark, project_gid,
                                entity_type, cache_key, tier):
    status = self._check_freshness(entry, current_watermark)

    # Compute freshness info for side-channel (before any return)
    from autom8_asana.config import DEFAULT_ENTITY_TTLS, DEFAULT_TTL
    entity_ttl = DEFAULT_ENTITY_TTLS.get(entry.entity_type, DEFAULT_TTL)
    age = (datetime.now(UTC) - entry.created_at).total_seconds()

    if status in (FreshnessStatus.FRESH, FreshnessStatus.STALE_SERVABLE,
                  FreshnessStatus.EXPIRED_SERVABLE):
        self._last_freshness[cache_key] = FreshnessInfo(
            freshness=status.value,
            data_age_seconds=round(age, 1),
            staleness_ratio=round(age / entity_ttl, 2) if entity_ttl > 0 else 0.0,
        )

    # ... existing switch logic follows unchanged ...
```

**Note on age computation**: The existing code already computes `age` in the STALE_SERVABLE and EXPIRED_SERVABLE branches. The refactoring moves this computation earlier (once, before the switch) to avoid duplication and to capture it for FRESH entries too. This is a minor efficiency improvement -- `datetime.now(UTC)` is called once instead of potentially twice.

**New public method:**

```python
def get_freshness_info(
    self,
    project_gid: str,
    entity_type: str,
) -> FreshnessInfo | None:
    """Get freshness info from the most recent get_async() call.

    Returns None if no freshness info is available (cache miss or
    no prior get_async() call for this key).
    """
    cache_key = self._build_key(project_gid, entity_type)
    return self._last_freshness.get(cache_key)
```

### B3: Response Model Changes

**File**: `src/autom8_asana/query/models.py`

Add three optional fields to `RowsMeta` and `AggregateMeta`:

```python
class RowsMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_count: int
    returned_count: int
    limit: int
    offset: int
    entity_type: str
    project_gid: str
    query_ms: float
    join_entity: str | None = None
    join_key: str | None = None
    join_matched: int | None = None
    join_unmatched: int | None = None
    # LKG freshness metadata
    freshness: str | None = None             # "fresh" | "stale_servable" | "expired_servable"
    data_age_seconds: float | None = None    # age of cached data in seconds
    staleness_ratio: float | None = None     # age / entity_ttl (>1.0 means past TTL)
```

```python
class AggregateMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_count: int
    aggregation_count: int
    group_by: list[str]
    entity_type: str
    project_gid: str
    query_ms: float
    # LKG freshness metadata
    freshness: str | None = None
    data_age_seconds: float | None = None
    staleness_ratio: float | None = None
```

**Backward compatibility proof**: Both models use `extra="forbid"`. Adding new Optional fields with `None` defaults is safe:
1. Existing responses that do not populate these fields will serialize them as `null` (or omit with `exclude_none=True`)
2. Existing consumers will not break because the fields are Optional with defaults
3. The `extra="forbid"` setting prevents extra INPUT fields, not output -- these are output-only response models
4. No existing code passes positional arguments to these models (they use keyword arguments)

### B4: FreshnessInfo Threading Path

The threading path connects the cache side-channel to API response metadata. Four files are modified:

**File 1: `src/autom8_asana/services/universal_strategy.py`**

In `_get_dataframe()`, after a successful cache hit, retrieve FreshnessInfo:

```python
async def _get_dataframe(self, project_gid, client):
    # ... existing cache check logic ...

    # After successful cache.get_async():
    if entry is not None:
        # Retrieve freshness info side-channel
        freshness_info = cache.get_freshness_info(project_gid, self.entity_type)
        # Store on instance for downstream access
        self._last_freshness_info = freshness_info
        return entry.dataframe

    # ... rest of method ...
```

Add new instance field:

```python
_last_freshness_info: Any = field(default=None, repr=False)
```

**File 2: `src/autom8_asana/services/query_service.py`**

In `get_dataframe()`, propagate FreshnessInfo from strategy to caller:

```python
async def get_dataframe(self, entity_type, project_gid, client):
    strategy = self.strategy_factory(entity_type)
    df = await strategy._get_dataframe(project_gid, client)
    if df is None:
        raise CacheNotWarmError(...)

    # Propagate freshness info
    self._last_freshness_info = getattr(strategy, '_last_freshness_info', None)
    return df
```

Add new instance field:

```python
_last_freshness_info: Any = field(default=None, repr=False, init=False)
```

**File 3: `src/autom8_asana/query/engine.py`**

In `execute_rows()` and `execute_aggregate()`, read FreshnessInfo from query_service and populate response Meta:

```python
# In execute_rows(), after df = await self.query_service.get_dataframe(...):
freshness_info = getattr(self.query_service, '_last_freshness_info', None)

# In the RowsMeta construction:
return RowsResponse(
    data=data,
    meta=RowsMeta(
        total_count=total_count,
        returned_count=len(data),
        limit=effective_limit,
        offset=request.offset,
        entity_type=entity_type,
        project_gid=project_gid,
        query_ms=round(elapsed_ms, 2),
        freshness=freshness_info.freshness if freshness_info else None,
        data_age_seconds=freshness_info.data_age_seconds if freshness_info else None,
        staleness_ratio=freshness_info.staleness_ratio if freshness_info else None,
        **join_meta,
    ),
)
```

Same pattern for `execute_aggregate()` with `AggregateMeta`.

---

## 5. Implementation Order

| Order | Group | Item | Rationale |
|-------|-------|------|-----------|
| 1 | A | A2: LKG_MAX_STALENESS_MULTIPLIER | Safety valve before expanding LKG surface area |
| 2 | A | A1: Circuit Breaker LKG | Depends on `_schema_is_valid()` helper; builds on proven LKG foundation |
| 3 | B | B1+B2: FreshnessInfo + side-channel | Foundation for API metadata; no external visibility yet |
| 4 | B | B3: Response model fields | Additive fields, backward compatible |
| 5 | B | B4: Threading path | Connects cache -> API; depends on B1-B3 |

**Rationale**: A2 before A1 because the max-staleness safety valve should exist before we expand LKG serving to the circuit breaker path. If circuit breaker LKG is deployed without a staleness ceiling, a prolonged upstream outage could serve arbitrarily stale data through the circuit breaker path with no policy limit. Group B is independent of Group A and can be implemented in parallel, but internally B1 must precede B4.

---

## 6. Circuit Breaker + LKG Interaction Matrix

This matrix documents the expected behavior for every combination of circuit breaker state and data freshness:

| Circuit State | Data State | Memory | S3 | Action | Returns |
|---------------|------------|--------|-----|--------|---------|
| **Closed** | Fresh | Hit | -- | Serve immediately | CacheEntry |
| **Closed** | Stale (SWR window) | Hit | -- | Serve + SWR refresh | CacheEntry |
| **Closed** | Expired Servable | Hit | -- | Serve as LKG + SWR refresh | CacheEntry |
| **Closed** | Expired Servable (max staleness exceeded) | Hit | -- | Evict, fall through to S3 | None if S3 also exceeded |
| **Closed** | Schema Mismatch | Hit | -- | Evict from memory, reject | None |
| **Closed** | Watermark Stale | Hit | -- | Evict from memory, reject | None |
| **Closed** | No data | Miss | Miss | Return None | None |
| **Open** | Fresh/Stale/Expired (schema valid) | Hit | -- | Serve, skip refresh | CacheEntry |
| **Open** | Fresh/Stale/Expired (schema valid) | Miss | Hit | Serve from S3, hydrate memory, skip refresh | CacheEntry |
| **Open** | Schema Mismatch | Hit | -- | Reject (never serve) | None |
| **Open** | Schema Mismatch | Miss | Hit | Reject (never serve) | None |
| **Open** | No data | Miss | Miss | Return None (genuine 503) | None |
| **Half-Open** | Any | -- | -- | Treated as Closed (allows probe) | Per Closed rules |

**Key invariants**:
1. Schema mismatch data is NEVER served, regardless of circuit state
2. Circuit open suppresses all refresh attempts (no SWR trigger, no build callback)
3. Circuit open does NOT skip schema validation
4. Watermark check is skipped under circuit open (cannot verify without upstream)
5. Max staleness multiplier is NOT applied under circuit open (policy defers to "serve what we have")

---

## 7. Files to Modify

| # | File | Changes |
|---|------|---------|
| 1 | `src/autom8_asana/cache/dataframe_cache.py` | Add `FreshnessInfo` dataclass; add `_schema_is_valid()` helper; add `_last_freshness` dict; modify circuit breaker block in `get_async()`; add max-staleness check in `_check_freshness_and_serve()`; add `get_freshness_info()` public method; add `lkg_circuit_serves` stat |
| 2 | `src/autom8_asana/config.py` | No changes (LKG_MAX_STALENESS_MULTIPLIER already exists at 0.0) |
| 3 | `src/autom8_asana/query/models.py` | Add `freshness`, `data_age_seconds`, `staleness_ratio` to `RowsMeta` and `AggregateMeta` |
| 4 | `src/autom8_asana/services/universal_strategy.py` | Add `_last_freshness_info` field; populate from `cache.get_freshness_info()` after cache hit in `_get_dataframe()` |
| 5 | `src/autom8_asana/services/query_service.py` | Add `_last_freshness_info` field; propagate from strategy in `get_dataframe()` |
| 6 | `src/autom8_asana/query/engine.py` | Read `_last_freshness_info` from `query_service`; populate `RowsMeta`/`AggregateMeta` freshness fields in `execute_rows()` and `execute_aggregate()` |
| 7 | `tests/unit/cache/dataframe/test_dataframe_cache.py` | Update `test_get_circuit_open`; add ~12 new tests |

---

## 8. Test Specifications

### Group A Tests (Cache Layer)

| # | Test Name | Description | Key Assertion |
|---|-----------|-------------|---------------|
| T1 | `test_circuit_open_serves_lkg_from_memory` | Circuit open with valid cached entry in memory serves it | `result is entry`; `stats["lkg_circuit_serves"] == 1` |
| T2 | `test_circuit_open_serves_lkg_from_s3` | Circuit open, memory miss, S3 hit with valid schema serves entry and hydrates memory | `result is entry`; `memory.get(key) is entry` |
| T3 | `test_circuit_open_rejects_schema_mismatch` | Circuit open with schema-mismatched entry returns None | `result is None` |
| T4 | `test_circuit_open_no_data_returns_none` | Circuit open with no data in any tier returns None | `result is None`; `stats["circuit_breaks"] == 1` |
| T5 | `test_circuit_open_no_refresh_triggered` | Circuit open serve does NOT trigger SWR refresh | `asyncio.create_task` not called |
| T6 | `test_max_staleness_rejects_overly_stale` | Entry exceeding `LKG_MAX_STALENESS_MULTIPLIER * entity_ttl` is rejected | `result is None`; entry evicted from memory |
| T7 | `test_max_staleness_zero_means_unlimited` | With multiplier=0.0 (default), expired entries are always served | `result is entry` |
| T8 | `test_max_staleness_within_limit_served` | Entry within max staleness limit is served as LKG | `result is entry`; `stats["lkg_serves"] == 1` |
| T9 | `test_schema_is_valid_helper_true` | `_schema_is_valid()` returns True for matching schema | `assert cache._schema_is_valid(entry) is True` |
| T10 | `test_schema_is_valid_helper_false_mismatch` | `_schema_is_valid()` returns False for mismatched schema | `assert cache._schema_is_valid(entry) is False` |
| T11 | `test_schema_is_valid_helper_false_no_registry` | `_schema_is_valid()` returns False when registry lookup fails | `assert cache._schema_is_valid(entry) is False` |

### Group A Test Updates (Existing)

| # | Test Name | Change |
|---|-----------|--------|
| U1 | `test_get_circuit_open` | Update: now expects LKG serve attempt (returns None only if no cached data) |

### Group B Tests (API Layer)

| # | Test Name | Description | Key Assertion |
|---|-----------|-------------|---------------|
| T12 | `test_freshness_info_stored_on_fresh` | FreshnessInfo is stored after serving a FRESH entry | `info.freshness == "fresh"`; `info.staleness_ratio < 1.0` |
| T13 | `test_freshness_info_stored_on_stale` | FreshnessInfo is stored after serving a STALE_SERVABLE entry | `info.freshness == "stale_servable"` |
| T14 | `test_freshness_info_stored_on_lkg` | FreshnessInfo is stored after serving an EXPIRED_SERVABLE entry | `info.freshness == "expired_servable"`; `info.staleness_ratio > 1.0` |
| T15 | `test_freshness_info_not_stored_on_reject` | FreshnessInfo is NOT stored on schema mismatch | `get_freshness_info() returns None` |
| T16 | `test_get_freshness_info_returns_none_on_miss` | `get_freshness_info()` returns None for unknown key | `result is None` |
| T17 | `test_rows_meta_includes_freshness_fields` | RowsMeta accepts and serializes freshness fields | `meta.freshness == "fresh"` |
| T18 | `test_aggregate_meta_includes_freshness_fields` | AggregateMeta accepts and serializes freshness fields | `meta.freshness == "fresh"` |
| T19 | `test_rows_meta_freshness_defaults_to_none` | RowsMeta without freshness fields serializes to None | `meta.freshness is None` |

**Total new tests**: 19 (11 Group A + 8 Group B)
**Updated existing tests**: 1 (test_get_circuit_open)

---

## 9. Risk Assessment

### Risk 1: Side-Channel Staleness (Race Condition)

**Risk**: `_last_freshness` dict stores FreshnessInfo per cache_key. If two concurrent requests for the same cache_key interleave, one request could read the other's FreshnessInfo.

**Severity**: Low
**Probability**: Low (DataFrameCache is used in an async single-threaded context per ECS task)

**Mitigation**: The side-channel stores the last-computed FreshnessInfo. In the single-threaded async model, `_check_freshness_and_serve()` completes before the caller reads `get_freshness_info()`. Even in a race, the FreshnessInfo would differ only by milliseconds of age computation, which is operationally irrelevant.

### Risk 2: Circuit Breaker LKG Masks Persistent Failures

**Risk**: Circuit breaker open + LKG serving means the system silently serves stale data during extended upstream outages. Operators may not notice the issue.

**Severity**: Medium
**Probability**: Medium

**Mitigation**:
1. `lkg_circuit_serves` stat counter makes this visible in metrics
2. `WARNING`-level log on every circuit-breaker LKG serve
3. When `LKG_MAX_STALENESS_MULTIPLIER > 0`, data beyond the limit is rejected even under circuit open -- but this policy is NOT applied under circuit open by design (see interaction matrix). Operators should monitor `circuit_breaks` + `lkg_circuit_serves` for alerting.

### Risk 3: Threading FreshnessInfo Through Private APIs

**Risk**: The threading path uses `strategy._get_dataframe()` (private method) and `getattr(strategy, '_last_freshness_info', None)` which creates a coupling to internal implementation details.

**Severity**: Low
**Probability**: Low (these private methods are already called by `EntityQueryService`)

**Mitigation**: The existing codebase already crosses this boundary (`query_service.py` line 173: `strategy._get_dataframe()`). Adding `_last_freshness_info` follows the same pattern. A future refactoring could introduce a `DataFrameResult` wrapper, but that changes the return type of `_get_dataframe()` across multiple callers -- higher risk for lower benefit right now.

### Risk 4: Memory Pressure from `_last_freshness` Dict

**Risk**: The `_last_freshness` dict grows unboundedly as new cache_keys are accessed.

**Severity**: Low
**Probability**: Low (bounded by number of entity_type:project_gid combinations, typically < 100)

**Mitigation**: The dict stores tiny `FreshnessInfo` dataclasses (3 floats + 1 string per entry). Even with 1000 entries, memory impact is negligible (< 100KB). If needed, LRU eviction can be added later.

### Rollback Strategy

**Group A rollback**: Revert the circuit breaker LKG block to `return None`. Revert the max-staleness check (remove the if-block). Both are isolated changes within `get_async()` and `_check_freshness_and_serve()`.

**Group B rollback**: Remove FreshnessInfo and `_last_freshness` from cache. Remove freshness fields from Meta models (backward compatible -- consumers already handle None). Remove threading logic from strategy/service/engine. API consumers see `null` for freshness fields, which is the pre-deployment state.

**Zero-downtime rollback**: Both groups can be rolled back independently. Group B rollback has zero API impact (fields become null). Group A rollback returns to current production behavior (circuit open returns None).

---

## 10. Non-Functional Requirements

### Performance

| Metric | Target | Approach |
|--------|--------|----------|
| LKG serve latency overhead | < 1ms | FreshnessInfo construction is 3 field assignments |
| Circuit breaker LKG latency | < 5ms (memory), < 50ms (S3) | Same tier access as normal path, minus freshness computation overhead |
| Memory overhead per FreshnessInfo | < 100 bytes | 3 numeric fields + 1 short string |

### Observability

| Signal | Type | Level |
|--------|------|-------|
| `dataframe_cache_circuit_lkg_serve` | Log | INFO |
| `dataframe_cache_circuit_open_no_lkg` | Log | WARNING |
| `dataframe_cache_{tier}_lkg_max_staleness_exceeded` | Log | WARNING |
| `lkg_circuit_serves` | Stat counter | Per entity type |
| `RowsMeta.freshness` | API response field | Per query |
| `RowsMeta.staleness_ratio` | API response field | Per query |

### Backward Compatibility

- `get_async()` return type unchanged: `CacheEntry | None`
- No new API endpoints
- Response model changes are additive Optional fields with None defaults
- Existing test assertions remain valid (prototype tests already pass)

---

## 11. ADR: Circuit Breaker LKG Semantics

### ADR-CB-LKG-001: Circuit Breaker Does Not Apply Max Staleness

**Context**: When the circuit breaker is open, should the `LKG_MAX_STALENESS_MULTIPLIER` policy apply?

**Decision**: No. When the circuit breaker is open, serve any schema-valid cached data regardless of age.

**Rationale**: The circuit breaker opens because upstream is failing. The max-staleness multiplier is a "prefer no data over very stale data" policy. But when the circuit breaker is open, the alternative to stale data is *no data at all* (503). In that context, stale data is always preferable to no data, because:
1. The consumer can see `staleness_ratio` in the response and decide whether to trust the data
2. A 503 is unrecoverable by the consumer; stale data is degraded but functional
3. If operators want to force 503 during prolonged outages, they should reset the cache (invalidation), not rely on the staleness policy

**Consequences**: During prolonged upstream outages with circuit breaker open, data can be served with arbitrarily high staleness ratios. This is the intended behavior. Monitoring on `lkg_circuit_serves` and `staleness_ratio` provides visibility.

### ADR-CB-LKG-002: Watermark Check Skipped Under Circuit Open

**Context**: Should the circuit breaker LKG path check watermark freshness?

**Decision**: No. Skip watermark check when circuit is open.

**Rationale**: Watermark check requires knowing the current max(modified_at) from the source. When the circuit is open, we cannot call the source to get the current watermark. The `current_watermark` parameter to `get_async()` is optionally provided by callers who already have the watermark, but under circuit breaker conditions, callers also cannot obtain it. The `_schema_is_valid()` check is sufficient -- it validates structural compatibility without requiring upstream access.

**Consequences**: Under circuit breaker, data that would fail a watermark check in normal operation may be served. This is acceptable because watermark staleness indicates "newer data exists upstream" -- if upstream is down (circuit open), we cannot get that newer data anyway.

---

## 12. Handoff Checklist

- [x] TDD covers all design scope items (A1, A2, B1-B4)
- [x] Component boundaries and responsibilities are clear
- [x] Data model defined (FreshnessInfo dataclass)
- [x] API contracts specified (RowsMeta/AggregateMeta field additions)
- [x] Key flow has sequence diagram (Section 2 data flow)
- [x] NFRs have concrete approaches (Section 10)
- [x] ADRs document significant decisions (Section 11)
- [x] Risks identified with mitigations (Section 9)
- [x] Circuit breaker + LKG interaction matrix (Section 6)
- [x] Test specifications with assertions (Section 8)
- [x] Implementation order with rationale (Section 5)
- [x] Files to modify with specific changes (Section 7)
- [x] Backward compatibility proof (Section 4, B3)

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD (this document) | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-lkg-cache-freshness.md` | Written |
| Prototype source | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py` | Read |
| Config | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py` | Read |
| Response models | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/models.py` | Read |
| Universal strategy | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py` | Read |
| Query service | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py` | Read |
| Query engine | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py` | Read |
| Existing tests | `/Users/tomtenuta/Code/autom8_asana/tests/unit/cache/dataframe/test_dataframe_cache.py` | Read |
| Prototype findings | `/Users/tomtenuta/Code/autom8_asana/LKG_PROTOTYPE_FINDINGS.md` | Read |
| Integration map spike | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/SPIKE-cache-freshness-integration-map.md` | Read |
| Patterns spike | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/SPIKE-cache-freshness-patterns.md` | Read |
