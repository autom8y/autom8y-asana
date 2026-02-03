# ADR-0066: Last-Known-Good (LKG) Cache Freshness

## Status

**Accepted** (2026-02-03)

## Context

The query API (`POST /v1/query/{entity_type}/rows`) returned HTTP 503 `CACHE_NOT_WARMED` despite valid data existing in S3. The root cause: entity TTLs range from 60s to 3600s, but the Lambda warmer runs once daily. This meant the cache was in an EXPIRED state for 99%+ of the day. Every request outside the brief post-warm window hit a cache miss.

### Problem Statement

When `_check_freshness()` returned `EXPIRED`, the entry was evicted from memory and the S3 tier also evaluated as EXPIRED (same `created_at`). Both tiers returned `None`, leading to a circular self-refresh failure path ending in 503.

### Research Inputs

Four spike documents evaluated patterns and integration points:
- **Pattern evaluation**: Assessed LKG with decoupled refresh, time-decay scoring, and multi-tier freshness. Selected LKG as the simplest pattern matching the existing SWR architecture.
- **Integration mapping**: The existing SWR architecture implements 70% of LKG. The remaining work extends the grace window concept with configurable max staleness.
- **Architecture vision**: Stress-tested the 5-gate pipeline against four plausible futures (entity proliferation, multi-consumer, event-driven, multi-region). The core thesis holds.
- **Tech transfer**: Prototype validated with all tests passing and GO recommendation.

## Decision

### Core Design

1. **TTL expiry no longer evicts data.** Expired entries are served with a staleness signal while background refresh runs. Schema mismatch remains a hard gate.

2. **FreshnessStatus extended** with three new states: `EXPIRED_SERVABLE` (LKG), `SCHEMA_MISMATCH` (hard reject), `WATERMARK_STALE` (hard reject).

3. **Circuit breaker LKG**: When circuit is open, serve from cache if schema-valid instead of returning None. No refresh triggered. No staleness cap applied (serve any age).

4. **LKG_MAX_STALENESS_MULTIPLIER**: Configurable cap on how long expired entries can be served. Default 0.0 (unlimited). When >0, entries exceeding `multiplier * entity_ttl` age are rejected and evicted.

5. **FreshnessInfo side-channel**: Freshness metadata (`freshness`, `data_age_seconds`, `staleness_ratio`) stored on the cache instance per cache-key and threaded through the service layer to populate API response metadata.

### Key Invariants

- **Schema mismatch NEVER served** under any code path, including circuit breaker open
- **No refresh trigger when circuit is open** (prevents cascading failures)
- **Max staleness not applied under circuit breaker** (degraded mode serves any valid data)
- **Watermark check skipped under circuit breaker** (watermark requires source availability)

### Staleness Threading

Side-channel pattern: `FreshnessInfo` stored on `DataFrameCache._last_freshness[cache_key]` after each serve, read by `UniversalStrategy` after cache hit, propagated through `EntityQueryService` and `QueryEngine` to `RowsMeta`/`AggregateMeta` response fields. Avoids changing `get_async()` return type.

## Consequences

### Positive

- **503 errors eliminated** for any entity type where cached data exists in any tier
- **Availability improved** during Asana API outages (stale data served rather than failing)
- **Zero performance impact** (same read path, staleness computed on read)
- **Observable**: `lkg_serves`, `lkg_circuit_serves` stats, WARNING-level logs, API response freshness metadata

### Negative

- **Stale data served by default** when entries expire beyond grace window
- **Side-channel `_last_freshness` dict** grows unbounded (bounded by entity_type:project_gid combinations, ~100 bytes each)
- **Race condition possible** in async concurrent access to `_last_freshness` (accepted: single-threaded async model, operationally irrelevant)

### Risks

| Risk | Mitigation |
|------|-----------|
| Circuit breaker masks persistent failures | `lkg_circuit_serves` stat for alerting |
| Stale data served indefinitely | `LKG_MAX_STALENESS_MULTIPLIER` available for enforcement |
| Side-channel coupling across layers | `FreshnessInfo` is Optional at every boundary |

## Files Modified

| File | Changes |
|------|---------|
| `src/autom8_asana/cache/dataframe_cache.py` | FreshnessInfo dataclass, circuit breaker LKG, max staleness enforcement, `_schema_is_valid()` helper, FreshnessInfo side-channel |
| `src/autom8_asana/config.py` | `LKG_MAX_STALENESS_MULTIPLIER` constant (pre-existing from prototype) |
| `src/autom8_asana/query/models.py` | `freshness`, `data_age_seconds`, `staleness_ratio` on RowsMeta + AggregateMeta |
| `src/autom8_asana/services/universal_strategy.py` | Read FreshnessInfo after cache hit |
| `src/autom8_asana/services/query_service.py` | Propagate FreshnessInfo to engine |
| `src/autom8_asana/query/engine.py` | Populate Meta fields from FreshnessInfo |
| `tests/unit/cache/dataframe/test_dataframe_cache.py` | 23 new tests |
| `tests/unit/query/test_models.py` | 3 new tests |

## Supersedes

This ADR consolidates and supersedes the following spike documents:
- `docs/spikes/SPIKE-cache-freshness-patterns.md`
- `docs/spikes/SPIKE-cache-freshness-integration-map.md`
- `docs/spikes/SPIKE-cache-freshness-architecture-vision.md`
- `docs/spikes/SPIKE-cache-freshness-tech-transfer.md`
- `LKG_PROTOTYPE_FINDINGS.md`
