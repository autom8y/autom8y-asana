# ADR-0048: Staleness Detection with Progressive TTL Extension

## Metadata
- **Status**: Accepted
- **Author**: Tech Writer (consolidation)
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Consolidated From**: ADR-0019, ADR-0133
- **Related**: reference/CACHE.md, ADR-0046 (Cache Protocol Extension)

## Context

Cache entries need freshness guarantees without expensive full-fetch validation. Different operations tolerate different staleness levels. Static TTL approaches force a choice between:
- Long TTL: Potentially stale data but fewer API calls
- Short TTL: Fresh data but cache thrashing

Base TTL of 300s (5 minutes) means a stable entity is checked 24 times over 2 hours, wasting API quota.

**Use Case Requirements**:

**Strict freshness** (user-facing edits, webhook handlers):
- Must see latest data
- Can tolerate ~50ms validation latency

**Eventual freshness** (reporting, bulk reads):
- Acceptable to be seconds behind
- Performance critical (~2ms cache read)

**Stable entities** (reference data, infrequently changing tasks):
- Checked repeatedly but unchanged
- Should reduce API calls over time

## Decision

**Implement two-part staleness strategy: `modified_at` comparison with Freshness parameter + progressive TTL extension for stable entities.**

### Part 1: Staleness Detection Algorithm

Use Arrow datetime comparison with `Freshness` parameter:

```python
from enum import Enum
from datetime import datetime
import arrow

class Freshness(Enum):
    STRICT = "strict"      # Always validate against API
    EVENTUAL = "eventual"  # Trust cache within TTL

def is_stale(cached_version: datetime, current_version: datetime) -> bool:
    """Compare cached version against current version using Arrow."""
    cached = arrow.get(cached_version)
    current = arrow.get(current_version)
    return current > cached

async def get_versioned(
    self,
    key: str,
    entry_type: EntryType,
    freshness: Freshness = Freshness.EVENTUAL,
) -> CacheEntry | None:
    """Retrieve versioned cache entry with freshness control."""
    entry = await self._get_from_redis(key, entry_type)

    if entry is None or entry.is_expired():
        await self._delete_from_redis(key, entry_type)
        return None

    if freshness == Freshness.EVENTUAL:
        return entry  # Trust cache, don't validate

    # STRICT mode: validate against API
    current_version = await self._fetch_modified_at(key)

    if current_version is None:
        await self._delete_from_redis(key, entry_type)
        return None

    if is_stale(entry.version, current_version):
        await self._delete_from_redis(key, entry_type)
        return None

    # Cache is fresh - extend TTL
    extended_entry = self._extend_ttl(entry)
    await self._set_versioned(key, extended_entry)

    return extended_entry
```

### Part 2: Progressive TTL Extension

When staleness check confirms entity unchanged, extend TTL using exponential doubling:

```python
def extend_ttl(
    entry: CacheEntry,
    base_ttl: int = 300,
    max_ttl: int = 86400,
) -> CacheEntry:
    """Create new CacheEntry with extended TTL.

    Algorithm: new_ttl = min(base_ttl * 2^(extension_count + 1), max_ttl)

    Progression (base=300, max=86400):
        Count 0: 300s    (5 min)
        Count 1: 600s    (10 min)
        Count 2: 1200s   (20 min)
        Count 3: 2400s   (40 min)
        Count 4: 4800s   (80 min)
        Count 5: 9600s   (160 min)
        Count 6: 19200s  (320 min)
        Count 7: 38400s  (640 min)
        Count 8: 76800s  (1280 min)
        Count 9+: 86400s (24h ceiling)
    """
    current_count = entry.metadata.get("extension_count", 0)
    new_count = current_count + 1
    new_ttl = min(base_ttl * (2 ** new_count), max_ttl)

    return CacheEntry(
        key=entry.key,
        data=entry.data,
        entry_type=entry.entry_type,
        version=entry.version,  # Unchanged
        cached_at=datetime.now(timezone.utc),  # Reset expiration window
        ttl=new_ttl,
        project_gid=entry.project_gid,
        metadata={**entry.metadata, "extension_count": new_count},
    )
```

### Version Sources by Entry Type

| Entry Type | Version Source | Comparison Strategy |
|------------|----------------|---------------------|
| TASK | Task `modified_at` | Direct comparison |
| SUBTASKS | Parent task `modified_at` | Parent change invalidates |
| DEPENDENCIES | Task `modified_at` | Task change invalidates |
| STRUC | Task `modified_at` | Task change invalidates |
| STORIES | `last_story_at` | New stories detected |

### Reset on Change

```python
def reset_ttl_on_change(
    entry: CacheEntry,
    new_data: dict[str, Any],
    new_version: datetime,
    base_ttl: int = 300,
) -> CacheEntry:
    """Reset TTL when entity changes."""
    return CacheEntry(
        key=entry.key,
        data=new_data,
        entry_type=entry.entry_type,
        version=new_version,
        cached_at=datetime.now(timezone.utc),
        ttl=base_ttl,  # Reset to base
        project_gid=entry.project_gid,
        metadata={**entry.metadata, "extension_count": 0},
    )
```

## Rationale

### Why `modified_at` Comparison?

`modified_at` is the canonical indicator of task state in Asana:
- Updated on any task field change
- Available on all task responses
- Lightweight to fetch (single field via `opt_fields=modified_at`)
- Reliable across all API endpoints

### Why Arrow Over stdlib datetime?

Python's `datetime` comparison has edge cases:
- Comparing naive vs. aware datetimes raises `TypeError`
- Timezone handling error-prone
- ISO 8601 parsing limited

Arrow abstracts these issues with minimal performance overhead.

### Why Two Freshness Modes?

| Mode | Use Case | Latency | Accuracy |
|------|----------|---------|----------|
| EVENTUAL | Dataframes, bulk reads | Low (~2ms) | May be seconds stale |
| STRICT | Edits, critical paths | Higher (~50ms) | Always current |

Single mode would either waste API calls (always strict) or risk stale reads (always eventual).

### Why Exponential Doubling?

| Algorithm | TTL After 5 Checks | Convergence | Complexity |
|-----------|-------------------|-------------|------------|
| Linear (+300s) | 1800s (30min) | Slow | Simple |
| **Exponential (x2)** | **9600s (2.7h)** | **Fast** | **Simple** |
| Fibonacci | ~6500s (1.8h) | Medium | Medium |

Exponential doubling:
- Reaches ceiling faster for stable entities
- Well-understood pattern (TCP, retry algorithms)
- Provides significant savings quickly

API call comparison over 2-hour session:
- Fixed 5min TTL: 24 calls
- Progressive TTL: 5 calls
- **Reduction: 79%**

### Why 24-Hour Ceiling?

| Ceiling | Use Case | Risk |
|---------|----------|------|
| 1 hour | High-churn data | Less savings |
| **24 hours** | **Stable reference data** | **Good balance** |
| 7 days | Archive data | High stale risk |

24 hours aligns with daily operational patterns and typical task update cadence.

### Why CacheEntry Replacement?

Preserving `frozen=True` contract avoids:
- Thread safety issues from shared mutable state
- Code audit to find all CacheEntry references
- Potential bugs from unexpected mutation

Minor overhead of object creation worth immutability benefits.

### Why metadata["extension_count"]?

Using existing `metadata` field:
- Requires no schema changes
- Persists automatically with cache entry
- Supports future extensions (e.g., `last_extension_at`)

## Alternatives Considered

### Alternative 1: TTL-Only Expiration
**Rejected**: Cannot guarantee freshness during TTL window. Fails NFR-REL-004.

### Alternative 2: ETag-Based Validation
**Rejected**: Asana API doesn't consistently support ETags across endpoints.

### Alternative 3: Polling-Based Background Refresh
**Rejected**: Too complex for SDK scope. Wastes API quota on unchanged tasks.

### Alternative 4: Webhook-Driven Invalidation
**Rejected**: Webhooks are optional consumer infrastructure. SDK cannot rely on them.

### Alternative 5: Linear TTL Extension
**Rejected**: Slow convergence means fewer API call savings. Exponential more efficient.

### Alternative 6: Mutable CacheEntry
**Rejected**: Breaking change to frozen contract. Thread safety concerns outweigh efficiency gains.

## Consequences

### Positive
- Flexible freshness control per operation
- Lightweight STRICT checks: Only fetches `modified_at`, not full payload
- 79% API call reduction for stable entities
- Robust datetime handling prevents timezone bugs
- Fast convergence to 24h ceiling
- Audit trail via extension count metadata
- Immutability preserved

### Negative
- Arrow dependency (minimal, ~2MB library)
- STRICT mode adds ~50ms API call per cache read
- Version source complexity: Different entry types use different fields
- Object creation overhead on extension
- 24-hour ceiling could serve stale data
- Extension count resets on process restart

### Neutral
- Default is EVENTUAL (consumers opt into STRICT)
- Batch checking uses same algorithm
- Configurable base_ttl and max_ttl
- Extension count available for metrics

## Impact

Production metrics:
- API calls for stable entities: 79% reduction over 2-hour sessions
- Tier 4 detection: 200ms → <5ms (40x speedup) when cached
- Cache hit rates: Maintained high (99%+) while reducing API load

## Compliance

**Enforcement mechanisms**:
1. Code review: Freshness parameter appropriate for operation type
2. Testing: Unit tests for `is_stale()` with various datetime formats, timezone comparisons
3. Integration: Tests verifying STRICT mode API calls, progressive extension behavior
4. Monitoring: Metrics on `ttl_extension_count`, `ttl_at_ceiling`, `api_calls_saved`

**Configuration**:
```python
@dataclass(frozen=True)
class StalenessCheckSettings:
    enabled: bool = True
    base_ttl: int = 300      # 5 minutes
    max_ttl: int = 86400     # 24 hours
    coalesce_window_ms: int = 50
    max_batch_size: int = 100
```
