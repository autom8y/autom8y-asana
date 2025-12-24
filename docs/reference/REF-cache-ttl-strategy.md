# Cache TTL Strategy Reference

## Overview

Time-to-Live (TTL) controls how long cached data remains valid before requiring refresh. The autom8_asana SDK implements entity-specific base TTLs with progressive extension for stable entities, balancing freshness requirements against API efficiency.

**Purpose**: Minimize API calls while ensuring cached data remains sufficiently fresh for application needs.

**Key Principle**: TTL should reflect entity volatility. Frequently-modified entities get short TTL, stable entities get longer TTL.

## Base TTL Calculation

### Default TTL Values

Base TTL varies by entity type based on typical modification frequency:

| Entity Type | Base TTL | Rationale |
|-------------|----------|-----------|
| Task | 3600s (1 hour) | Frequently modified in active workflows |
| Project | 7200s (2 hours) | Less frequently modified than tasks |
| Portfolio | 14400s (4 hours) | Rarely modified, mostly read access |
| Section | 7200s (2 hours) | Moderate modification frequency |
| Custom Field Defs | 86400s (24 hours) | Schema-level entities, very stable |
| User | 86400s (24 hours) | User profiles rarely change |
| Workspace | 86400s (24 hours) | Workspace settings very stable |
| Team | 43200s (12 hours) | Team membership changes occasionally |

**Source**: ADR-0126 (Entity TTL Resolution)

### Entity Type Multipliers

TTL calculation uses entity type as primary factor:

```python
# Base TTL lookup
BASE_TTL = {
    "task": 3600,
    "project": 7200,
    "portfolio": 14400,
    "section": 7200,
    "custom_field_setting": 86400,
    "user": 86400,
    "workspace": 86400,
    "team": 43200,
}

def get_base_ttl(entity_type: str) -> int:
    """Get base TTL for entity type.

    Args:
        entity_type: Asana entity type

    Returns:
        Base TTL in seconds
    """
    return BASE_TTL.get(entity_type, 3600)  # Default: 1 hour
```

### Contextual TTL Adjustment

In some cases, TTL varies based on entity context:

| Context | TTL Adjustment | Example |
|---------|----------------|---------|
| Task in active project | -50% (shorter) | Task in project with recent activity |
| Task marked complete | +100% (longer) | Completed tasks change less frequently |
| High-traffic entity | -25% (shorter) | Entities accessed frequently may change more |
| Archive/read-only | +200% (longer) | Archived projects unlikely to change |

**Implementation Note**: Contextual adjustment is optional and not currently implemented. Base TTL by entity type is sufficient for most use cases.

## Progressive TTL Extension

### Algorithm

**Concept**: Entities that remain unchanged across multiple cache accesses likely have lower volatility. Progressively extend TTL to reduce API calls for stable entities.

**Algorithm** (from ADR-0133):

```python
def calculate_extended_ttl(
    base_ttl: int,
    extension_count: int,
    max_ttl: int = 86400,
) -> int:
    """Calculate extended TTL using exponential backoff.

    Args:
        base_ttl: Base TTL for entity type
        extension_count: Number of times TTL extended
        max_ttl: Maximum TTL cap (default 24 hours)

    Returns:
        Extended TTL in seconds
    """
    # Exponential: double TTL each extension
    extended = base_ttl * (2 ** extension_count)

    # Cap at maximum
    return min(extended, max_ttl)
```

### Extension Rules

**When to extend**:
1. TTL expires
2. Perform lightweight staleness check
3. If entity unchanged: increment `extension_count`, recalculate TTL
4. If entity changed: reset `extension_count = 0`, use base TTL

**Extension progression** (example for task with base_ttl=3600s):

| Access | Extension Count | TTL (seconds) | TTL (human) | Condition |
|--------|----------------|---------------|-------------|-----------|
| 1st | 0 | 3600 | 1 hour | Initial cache |
| 2nd (unchanged) | 1 | 7200 | 2 hours | First extension |
| 3rd (unchanged) | 2 | 14400 | 4 hours | Second extension |
| 4th (unchanged) | 3 | 28800 | 8 hours | Third extension |
| 5th (unchanged) | 4 | 57600 | 16 hours | Fourth extension |
| 6th (unchanged) | 5 | 86400 | 24 hours | Capped at max |
| Nth (changed) | 0 | 3600 | 1 hour | Reset on change |

**Storage**: Track extension count in cache entry metadata:

```python
class CacheEntry:
    key: str
    data: dict
    created_at: datetime
    ttl: int
    metadata: dict  # {"extension_count": 2, "modified_at": "2025-12-24T..."}
```

### Reset Conditions

Reset TTL to base value when:

1. **Entity modified**: Staleness check detects `modified_at` changed
2. **Explicit invalidation**: Cache entry explicitly deleted
3. **Write operation**: Entity updated via SDK
4. **Extension error**: Staleness check fails, fallback to safe refresh

**Reset implementation**:

```python
async def handle_modified_entry(entry: CacheEntry):
    """Reset TTL when entity changed."""
    entry.metadata["extension_count"] = 0
    entry.metadata["ttl"] = get_base_ttl(entry.entity_type)
    entry.metadata["modified_at"] = current_modified_at
    entry.created_at = datetime.now()

    await cache.set(entry.key, entry)
```

## TTL Tuning Guidelines

### When to Increase TTL

Increase base TTL when:

- **Data changes infrequently**: Analysis shows entity modified less than once per current TTL period
- **Acceptable staleness window is large**: Use case tolerates data being hours old
- **Performance is priority over freshness**: Reporting/analytics where speed matters
- **API quota is constrained**: Need to reduce API calls

**How to increase**:
```python
# Increase base TTL for specific entity type
BASE_TTL["task"] = 7200  # 2 hours instead of 1 hour

# Or increase max TTL cap for progressive extension
MAX_TTL = 172800  # 48 hours instead of 24 hours
```

### When to Decrease TTL

Decrease base TTL when:

- **Data changes frequently**: Entity modified multiple times within current TTL
- **Freshness is critical**: Interactive UI where users expect current data
- **Staleness causes user-facing issues**: Reports show stale reads impacting UX
- **Strict mode overhead acceptable**: Willing to pay API cost for freshness

**How to decrease**:
```python
# Decrease base TTL for specific entity type
BASE_TTL["task"] = 1800  # 30 minutes instead of 1 hour

# Or disable progressive extension
USE_PROGRESSIVE_TTL = False  # Always use base TTL
```

### Monitoring and Adjustment

**Metrics to track**:

| Metric | Target | Action if Off-Target |
|--------|--------|---------------------|
| Cache hit rate | >80% | If low: increase TTL |
| Stale read rate | <1% | If high: decrease TTL or use STRICT mode |
| API calls per session | Declining over time | Progressive TTL working correctly |
| Average TTL extension | 2-3 extensions | If low: entities too volatile; if high: max cap too low |

**Tuning process**:
1. Collect metrics for 1 week
2. Identify entity types with high staleness
3. Adjust base TTL for those types
4. Monitor impact for 1 week
5. Iterate

## TTL vs. Staleness Detection

TTL and staleness detection serve different but complementary purposes:

### TTL: Passive Expiration

**What**: Define cache lifetime boundary
**When**: Checked on every cache access
**Cost**: Zero (local timestamp comparison)
**Guarantee**: Data not older than TTL
**Limitation**: May serve stale data if entity changed before TTL expires

### Staleness Detection: Active Validation

**What**: Verify cached data matches current API version
**When**: On cache hit in STRICT mode
**Cost**: Lightweight API call (~100 bytes)
**Guarantee**: Data matches API (100% freshness)
**Limitation**: Requires API call, slower than TTL-only

### Combined Strategy

| Mechanism | Purpose | When Used |
|-----------|---------|-----------|
| TTL | Define upper bound on cache age | Always (EVENTUAL and STRICT modes) |
| Staleness Detection | Verify data hasn't changed | STRICT mode only |
| Progressive TTL | Optimize for stable entities | After staleness check passes |

**Flow**:
```
1. Access cache entry
2. Check TTL expired?
   - No → Return cached data (EVENTUAL) or check staleness (STRICT)
   - Yes → Perform staleness check
3. Staleness check:
   - Stale → Fetch from API, reset TTL
   - Fresh → Extend TTL, return cached data
```

**Example scenarios**:

| Scenario | TTL Status | Staleness Check | Result |
|----------|-----------|----------------|--------|
| Access at T+30min (TTL=1h) | Not expired | Skipped (EVENTUAL) | Return cache |
| Access at T+30min (TTL=1h) | Not expired | Performed (STRICT) | Check API, return cache if fresh |
| Access at T+90min (TTL=1h) | Expired | Performed | Check API, extend TTL if unchanged |
| Access at T+90min (TTL=1h, changed) | Expired | Performed | Fetch from API, reset TTL |

## Implementation Notes

### Calculating TTL on Cache Write

**On initial cache write**:
```python
async def cache_entity(
    self,
    gid: str,
    entity_type: str,
    data: dict,
):
    base_ttl = get_base_ttl(entity_type)

    entry = CacheEntry(
        key=gid,
        data=data,
        created_at=datetime.now(),
        ttl=base_ttl,
        metadata={
            "extension_count": 0,
            "modified_at": data.get("modified_at"),
            "entity_type": entity_type,
        }
    )

    await self.cache_provider.set(gid, entry, ttl=base_ttl)
```

### Calculating TTL on Extension

**After staleness check passes**:
```python
async def extend_entry_ttl(self, entry: CacheEntry):
    extension_count = entry.metadata.get("extension_count", 0) + 1
    base_ttl = get_base_ttl(entry.metadata["entity_type"])
    new_ttl = calculate_extended_ttl(base_ttl, extension_count)

    entry.metadata["extension_count"] = extension_count
    entry.ttl = new_ttl
    entry.created_at = datetime.now()  # Reset clock for new TTL

    await self.cache_provider.set(entry.key, entry, ttl=new_ttl)
```

### TTL in Batch Operations

**Batch cache population**: Use consistent TTL for all entities in batch.

```python
async def cache_batch(
    self,
    entities: list[dict],
    entity_type: str,
):
    base_ttl = get_base_ttl(entity_type)

    entries = {
        entity["gid"]: CacheEntry(
            key=entity["gid"],
            data=entity,
            created_at=datetime.now(),
            ttl=base_ttl,
            metadata={"extension_count": 0, "modified_at": entity["modified_at"]},
        )
        for entity in entities
    }

    await self.cache_provider.set_multi(entries, ttl=base_ttl)
```

## Related Documentation

- [ADR-0126: Entity TTL Resolution](../decisions/ADR-0126-entity-ttl-resolution.md) - Base TTL specification
- [ADR-0133: Progressive TTL Extension Algorithm](../decisions/ADR-0133-progressive-ttl-extension-algorithm.md) - Extension algorithm
- [REF-cache-staleness-detection.md](REF-cache-staleness-detection.md) - Staleness detection algorithms
- [REF-cache-provider-protocol.md](REF-cache-provider-protocol.md) - Cache provider integration
- [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md) - Cache requirements
- [PRD-CACHE-LIGHTWEIGHT-STALENESS](../requirements/PRD-CACHE-LIGHTWEIGHT-STALENESS.md) - Progressive TTL use cases
- [RUNBOOK-cache-troubleshooting.md](../runbooks/RUNBOOK-cache-troubleshooting.md) - TTL tuning troubleshooting
