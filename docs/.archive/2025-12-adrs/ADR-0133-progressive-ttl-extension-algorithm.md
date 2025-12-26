# ADR-0133: Progressive TTL Extension Algorithm

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-24
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-CACHE-LIGHTWEIGHT-STALENESS, TDD-CACHE-LIGHTWEIGHT-STALENESS, ADR-0132 (Batch Request Coalescing), ADR-0019 (Staleness Detection Algorithm)

## Context

When a lightweight staleness check determines that a cached entity is unchanged, the system should extend its TTL to reduce future API calls. The extension algorithm must balance:

1. **Efficiency**: Longer TTLs mean fewer checks
2. **Freshness**: Excessively long TTLs increase stale read risk
3. **Recovery**: System should recover quickly when entities start changing
4. **Audit**: Extension history should be traceable for debugging

### Problem Statement

The base TTL of 300s (5 minutes) means a stable entity is checked 24 times over 2 hours. With progressive extension, the same entity could require only 5-6 checks over the same period. The algorithm must:

1. **Extend** TTL progressively for repeatedly unchanged entities
2. **Cap** maximum TTL to bound staleness risk
3. **Reset** to base TTL when entity changes
4. **Track** extension count for observability
5. **Preserve** CacheEntry immutability

### Forces at Play

| Force | Description |
|-------|-------------|
| **API Efficiency** | Fewer checks = fewer API calls |
| **Data Freshness** | Longer TTL = higher stale read probability |
| **Predictability** | Simple algorithm = easier to reason about |
| **Immutability** | CacheEntry is frozen dataclass |
| **Persistence** | Extension state should survive cache operations |
| **Audit Trail** | Need to know extension history for debugging |

### Key Questions

1. **What algorithm** for TTL progression (linear, exponential, Fibonacci)?
2. **What ceiling** for maximum TTL?
3. **How** to store extension state while preserving immutability?
4. **When** to reset TTL (on change, on error, periodically)?

## Decision

**Implement exponential doubling with 24-hour ceiling, using CacheEntry replacement with metadata-stored extension count.**

### Specific Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Algorithm | Exponential doubling: `min(base * 2^count, max)` | Proven pattern, rapid convergence to stable state |
| Base TTL | 300s (5 minutes) | Existing default, reasonable freshness guarantee |
| Max TTL (Ceiling) | 86400s (24 hours) | Bounds staleness risk, aligns with daily refresh patterns |
| Extension Storage | `CacheEntry.metadata["extension_count"]` | Uses existing field, persists across operations |
| Entry Update | Replacement (new CacheEntry) | Preserves frozen dataclass contract |
| Reset Behavior | Reset to base (300s) on change or error | Ensures fresh data after modifications |
| cached_at Update | Reset on every extension | New expiration window starts from now |

### Extension Algorithm

```python
def extend_ttl(
    entry: CacheEntry,
    base_ttl: int = 300,
    max_ttl: int = 86400,
) -> CacheEntry:
    """Create new CacheEntry with extended TTL.

    Per ADR-0133: Exponential doubling with ceiling.

    Algorithm:
        new_ttl = min(base_ttl * 2^(extension_count + 1), max_ttl)

    Progression (base=300, max=86400):
        Count 0 (base): 300s   (5 min)
        Count 1:        600s   (10 min)
        Count 2:        1200s  (20 min)
        Count 3:        2400s  (40 min)
        Count 4:        4800s  (80 min)
        Count 5:        9600s  (160 min)
        Count 6:        19200s (320 min)
        Count 7:        38400s (640 min)
        Count 8:        76800s (1280 min)
        Count 9+:       86400s (24h ceiling)

    Args:
        entry: Original cache entry (unchanged entity).
        base_ttl: Base TTL in seconds (default 300).
        max_ttl: Maximum TTL ceiling in seconds (default 86400).

    Returns:
        New CacheEntry with extended TTL and updated metadata.
    """
    current_count = entry.metadata.get("extension_count", 0)
    new_count = current_count + 1

    # Exponential doubling with ceiling
    new_ttl = min(base_ttl * (2 ** new_count), max_ttl)

    # Create new entry (immutable replacement)
    return CacheEntry(
        key=entry.key,
        data=entry.data,
        entry_type=entry.entry_type,
        version=entry.version,  # Preserved: actual version unchanged
        cached_at=datetime.now(timezone.utc),  # Reset: new expiration window
        ttl=new_ttl,
        project_gid=entry.project_gid,
        metadata={**entry.metadata, "extension_count": new_count},
    )
```

### Reset Behavior

```python
def reset_ttl_on_change(
    entry: CacheEntry,
    new_data: dict[str, Any],
    new_version: datetime,
    base_ttl: int = 300,
) -> CacheEntry:
    """Create new CacheEntry with reset TTL after change.

    Per ADR-0133: Reset to base TTL when entity changes.

    Args:
        entry: Original cache entry.
        new_data: Fresh data from API.
        new_version: New modified_at from API.
        base_ttl: Base TTL to reset to (default 300).

    Returns:
        New CacheEntry with fresh data and reset TTL.
    """
    return CacheEntry(
        key=entry.key,
        data=new_data,
        entry_type=entry.entry_type,
        version=new_version,
        cached_at=datetime.now(timezone.utc),
        ttl=base_ttl,  # Reset to base
        project_gid=entry.project_gid,
        metadata={**entry.metadata, "extension_count": 0},  # Reset count
    )
```

### TTL Progression Table

| Extension Count | TTL (seconds) | TTL (human readable) | Cumulative Time |
|-----------------|---------------|----------------------|-----------------|
| 0 (base) | 300 | 5 minutes | 0 |
| 1 | 600 | 10 minutes | 5 min |
| 2 | 1200 | 20 minutes | 15 min |
| 3 | 2400 | 40 minutes | 35 min |
| 4 | 4800 | 80 minutes (~1.3h) | 1h 15min |
| 5 | 9600 | 160 minutes (~2.7h) | 2h 35min |
| 6 | 19200 | 320 minutes (~5.3h) | 5h 15min |
| 7 | 38400 | 640 minutes (~10.7h) | 10h 35min |
| 8 | 76800 | 1280 minutes (~21h) | 21h 15min |
| 9+ | 86400 | 1440 minutes (24h) CEILING | 42h 15min+ |

### API Call Comparison (2-Hour Session)

| Strategy | API Calls | Calculation |
|----------|-----------|-------------|
| Fixed 5min TTL | 24 | 120min / 5min |
| Progressive TTL | 5 | 5min + 10min + 20min + 40min + 80min > 120min |
| Reduction | 79% | (24-5)/24 |

## Rationale

### Why Exponential Doubling?

| Algorithm | TTL After 5 Checks | Convergence | Complexity |
|-----------|-------------------|-------------|------------|
| Linear (+300s) | 1800s (30min) | Slow | Simple |
| **Exponential (x2)** | **9600s (2.7h)** | **Fast** | **Simple** |
| Fibonacci | ~6500s (1.8h) | Medium | Medium |
| Polynomial (x1.5) | ~2278s (38min) | Medium | Simple |

Exponential doubling:
- Reaches ceiling faster for stable entities
- Well-understood pattern (used in TCP, retry algorithms)
- Simple to implement and explain
- Provides significant savings quickly

### Why 24-Hour Ceiling?

| Ceiling | Use Case | Risk |
|---------|----------|------|
| 1 hour | High-churn data | Frequent checks, less savings |
| 4 hours | Active workday | Moderate balance |
| **24 hours** | **Stable reference data** | **Good balance for most entities** |
| 7 days | Archive data | High stale read risk |
| Unlimited | Never | Unbounded staleness |

24 hours aligns with:
- Daily operational patterns
- Typical task update cadence for stable entities
- Reasonable bound on stale read risk

### Why CacheEntry Replacement?

| Approach | Pros | Cons |
|----------|------|------|
| Mutable CacheEntry | Efficient (in-place) | Breaks frozen contract, thread safety concerns |
| **Replacement** | **Preserves immutability, audit trail** | **Creates new object** |
| Separate tracker | Clean separation | New component, lost on restart |

Replacement preserves the existing `frozen=True` contract on CacheEntry, avoiding:
- Thread safety issues from shared mutable state
- Code audit to find all CacheEntry references
- Potential bugs from unexpected mutation

### Why metadata["extension_count"]?

| Storage Location | Pros | Cons |
|------------------|------|------|
| New CacheEntry field | Type-safe, explicit | Schema change, migration |
| **metadata dict** | **No schema change, flexible** | **String key, less type-safe** |
| Separate cache | Clean separation | Coordination complexity |

The `metadata` field already exists for arbitrary entry-type-specific data. Using it:
- Requires no schema changes
- Persists automatically with cache entry
- Supports future extension (e.g., `metadata["last_extension_at"]`)

## Alternatives Considered

### Alternative 1: Linear TTL Extension

**Description**: Add fixed amount on each extension: `new_ttl = base + (count * increment)`.

```python
# Example: base=300, increment=300
# Count 0: 300s, Count 1: 600s, Count 2: 900s, ...
new_ttl = min(300 + (count * 300), max_ttl)
```

**Pros**:
- Simple and predictable
- Gradual increase
- Easy to calculate final TTL

**Cons**:
- Slow convergence to ceiling
- Many more checks needed for stable entities
- Less efficient API call reduction

**Why not chosen**: Exponential provides faster convergence, meaning fewer API calls for stable entities.

### Alternative 2: Fibonacci TTL Extension

**Description**: TTL follows Fibonacci sequence: 300, 300, 600, 900, 1500, 2400, ...

```python
def fib_ttl(n):
    a, b = 300, 300
    for _ in range(n):
        a, b = b, a + b
    return min(a, max_ttl)
```

**Pros**:
- Smoother than pure exponential
- Natural growth pattern
- Interesting mathematical properties

**Cons**:
- More complex calculation
- Harder to predict TTL at count N
- No practical advantage over exponential

**Why not chosen**: Exponential is simpler with equivalent effectiveness.

### Alternative 3: Mutable CacheEntry

**Description**: Remove `frozen=True` and mutate TTL/metadata in place.

```python
@dataclass  # Remove frozen=True
class CacheEntry:
    # ... fields ...
    ttl: int | None = 300
    extension_count: int = 0

    def extend_ttl(self, base_ttl: int = 300, max_ttl: int = 86400) -> None:
        self.extension_count += 1
        self.ttl = min(base_ttl * (2 ** self.extension_count), max_ttl)
        self.cached_at = datetime.now(timezone.utc)
```

**Pros**:
- More efficient (no new object)
- Direct mutation semantics
- Simpler method signature

**Cons**:
- Breaking change to frozen contract
- Thread safety concerns
- Requires code audit for shared references
- Harder to reason about state changes

**Why not chosen**: Preserving immutability is worth the minor overhead of object creation.

### Alternative 4: Separate TTL Extension Tracker

**Description**: Store extension metadata in separate cache or in-memory dict.

```python
class TTLExtensionTracker:
    _extensions: dict[str, int]  # key -> extension_count

    def get_effective_ttl(self, key: str, base_ttl: int) -> int:
        count = self._extensions.get(key, 0)
        return min(base_ttl * (2 ** count), max_ttl)

    def record_extension(self, key: str) -> None:
        self._extensions[key] = self._extensions.get(key, 0) + 1
```

**Pros**:
- CacheEntry unchanged
- Clean separation of concerns
- No metadata pollution

**Cons**:
- New component to maintain
- Lost on process restart
- Must stay synchronized with cache
- Additional complexity

**Why not chosen**: metadata field provides same benefit without new component.

## Consequences

### Positive

1. **Significant API Reduction**: 79% fewer calls for 2-hour stable entity access
2. **Fast Convergence**: Reaches ceiling after 9 extensions
3. **Bounded Staleness**: 24-hour ceiling limits stale read risk
4. **Audit Trail**: Extension count visible in metadata
5. **Immutability Preserved**: No changes to CacheEntry contract
6. **Persistence**: Extension state survives cache operations

### Negative

1. **Object Creation**: New CacheEntry on every extension
2. **Stale Risk at Ceiling**: 24-hour TTL could serve very stale data
3. **Reset on Change**: Changed entities restart from base TTL
4. **Process Restart**: Extension count resets (but metadata persists in cache)

### Neutral

1. **Configurable**: base_ttl and max_ttl can be tuned
2. **Observable**: Extension count available for metrics
3. **Testable**: Deterministic algorithm enables property testing

## Compliance

### How This Decision Will Be Enforced

1. **Code Review**: Changes to TTL extension require ADR reference
2. **Unit Tests**: Test progression at each count, ceiling enforcement
3. **Property Tests**: Verify `new_ttl <= max_ttl` always
4. **Integration Tests**: Validate API call reduction over time

### Configuration

```python
@dataclass(frozen=True)
class StalenessCheckSettings:
    """Staleness check configuration.

    Per ADR-0133: Configurable TTL parameters.
    """
    enabled: bool = True
    base_ttl: int = 300      # 5 minutes, per ADR-0133
    max_ttl: int = 86400     # 24 hours, per ADR-0133
    coalesce_window_ms: int = 50
    max_batch_size: int = 100
```

### Code Location

```python
# /src/autom8_asana/cache/staleness_coordinator.py

def _extend_ttl(self, entry: CacheEntry) -> CacheEntry:
    """Extend TTL using exponential doubling.

    Per ADR-0133: min(base * 2^count, max).
    """
    current_count = entry.metadata.get("extension_count", 0)
    new_count = current_count + 1

    new_ttl = min(
        self.settings.base_ttl * (2 ** new_count),
        self.settings.max_ttl,
    )

    return CacheEntry(
        key=entry.key,
        data=entry.data,
        entry_type=entry.entry_type,
        version=entry.version,
        cached_at=datetime.now(timezone.utc),
        ttl=new_ttl,
        project_gid=entry.project_gid,
        metadata={**entry.metadata, "extension_count": new_count},
    )
```

### Logging

```python
# TTL extension event
logger.debug(
    "ttl_extended",
    extra={
        "cache_operation": "staleness_check",
        "gid": entry.key,
        "previous_ttl": entry.ttl,
        "new_ttl": new_ttl,
        "extension_count": new_count,
        "at_ceiling": new_ttl == self.settings.max_ttl,
    },
)
```

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `ttl_extension_count` | Histogram | Extension count at check time |
| `ttl_at_ceiling` | Counter | Entries that reached max TTL |
| `ttl_reset_count` | Counter | Entries reset due to change |
| `api_calls_saved` | Counter | Full fetches avoided by extension |
