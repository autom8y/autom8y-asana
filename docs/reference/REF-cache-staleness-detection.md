# Cache Staleness Detection Reference

## Overview

Staleness detection determines when cached data is outdated and needs refreshing from the Asana API. The autom8_asana SDK implements multiple staleness detection strategies optimized for different use cases: TTL-based expiration, watermark-based change detection, and progressive TTL extension for stable entities.

**Purpose**: Reduce unnecessary API calls while ensuring data freshness meets application requirements.

**Key Principle**: Different use cases have different freshness requirements. Strict mode validates every access, eventual mode trusts cache within TTL.

## Staleness Detection Approaches

### 1. TTL-Based Staleness

**Mechanism**: Cache entries expire after a fixed time-to-live (TTL) period.

**How it works**:
- Each cache entry stores a `created_at` timestamp
- On access, compare current time against `created_at + TTL`
- If current time exceeds TTL boundary, entry is stale

**Advantages**:
- Simple to implement
- Predictable behavior
- Low overhead (no API calls)

**Disadvantages**:
- May serve stale data if entity changes before TTL expires
- May fetch unchanged data if entity is stable beyond TTL

**Use when**: Acceptable staleness window is known and consistent.

### 2. Watermark-Based Staleness

**Mechanism**: Track the `modified_at` timestamp of cached entities and compare against current API version.

**How it works**:
1. Cache stores entity data + `modified_at` timestamp
2. On access (in STRICT mode), fetch current `modified_at` from API
3. Compare cached `modified_at` vs. current `modified_at`
4. If current > cached, entity changed (stale)
5. If current == cached, entity unchanged (fresh)

**Advantages**:
- Detects changes with 100% accuracy
- Lightweight check (~100 bytes vs. ~5KB full fetch)
- Can extend TTL for unchanged entities

**Disadvantages**:
- Requires API call on every strict-mode access
- Not applicable to entity types without `modified_at`

**Use when**: Strict freshness required, entity has `modified_at` field.

### 3. Progressive TTL Extension

**Mechanism**: Extend TTL for entities that remain unchanged across multiple accesses.

**How it works**:
1. First access: Set base TTL (e.g., 300s for tasks)
2. On TTL expiration: Perform lightweight staleness check
3. If unchanged: Double TTL (300s → 600s → 1200s → ...)
4. If changed: Reset to base TTL
5. Cap at maximum TTL (e.g., 86400s / 24 hours)

**Advantages**:
- Optimizes for stable entities (90%+ API call reduction)
- Adapts automatically to entity change frequency
- Maintains strict freshness when needed

**Disadvantages**:
- More complex to implement
- Requires metadata storage (extension_count)
- Only beneficial for long-running sessions

**Use when**: Accessing stable entities repeatedly over extended periods.

## Algorithms

### Lightweight Staleness Detection

**Algorithm** (from ADR-0133):

```python
async def check_entry_staleness(
    self,
    entry: CacheEntry,
    freshness: Freshness = Freshness.STRICT,
) -> bool:
    """Check if cache entry is stale.

    Args:
        entry: Cache entry to check
        freshness: STRICT (validate) or EVENTUAL (trust cache)

    Returns:
        True if entry is stale, False if fresh
    """
    # EVENTUAL mode: trust TTL only
    if freshness == Freshness.EVENTUAL:
        return entry.is_expired()

    # STRICT mode: validate against API
    if entry.is_expired():
        return True

    # Fetch current modified_at from API
    current_modified_at = await self._fetch_modified_at(entry.key)

    if current_modified_at is None:
        # Entity deleted
        return True

    # Compare timestamps
    cached_modified_at = entry.metadata.get("modified_at")
    return current_modified_at > cached_modified_at
```

**Batch Optimization**: Coalesce multiple staleness checks into single batch API call:

```python
async def check_batch_staleness(
    self,
    entries: list[CacheEntry],
) -> dict[str, bool]:
    """Check staleness for multiple entries in single API call.

    Returns:
        Mapping of entry key → is_stale
    """
    gids = [entry.key for entry in entries]

    # Single batch API call
    current_versions = await self.client.tasks.get_batch(
        gids,
        opt_fields=["modified_at"]
    )

    results = {}
    for entry in entries:
        current = current_versions.get(entry.key)
        if current is None:
            results[entry.key] = True  # Deleted
        else:
            cached_modified = entry.metadata.get("modified_at")
            results[entry.key] = current["modified_at"] > cached_modified

    return results
```

### Watermark Staleness Check

**Algorithm** (from PRD-WATERMARK-CACHE):

Used for collection caching (e.g., all tasks in a project):

```python
async def check_collection_staleness(
    self,
    collection_key: str,
    watermark: datetime,
) -> bool:
    """Check if collection changed since watermark.

    Args:
        collection_key: Collection identifier (e.g., "project:123")
        watermark: Timestamp when collection was cached

    Returns:
        True if any entity in collection changed since watermark
    """
    # Query entities modified since watermark
    modified_gids = await self.client.tasks.find_all(
        project=collection_key.split(":")[1],
        modified_since=watermark.isoformat(),
        opt_fields=["gid"]
    )

    # If any entities modified, collection is stale
    return len(modified_gids) > 0
```

### Progressive TTL Extension Algorithm

**Algorithm** (from ADR-0133):

```python
def calculate_extended_ttl(
    base_ttl: int,
    extension_count: int,
    max_ttl: int = 86400,
) -> int:
    """Calculate extended TTL for stable entity.

    Args:
        base_ttl: Base TTL in seconds
        extension_count: Number of times TTL has been extended
        max_ttl: Maximum TTL cap (default 24 hours)

    Returns:
        Extended TTL in seconds
    """
    # Exponential backoff: double each time
    extended = base_ttl * (2 ** extension_count)

    # Cap at maximum
    return min(extended, max_ttl)

# Example progression for task (base_ttl=300s):
# extension_count=0: 300s (5 min)
# extension_count=1: 600s (10 min)
# extension_count=2: 1200s (20 min)
# extension_count=3: 2400s (40 min)
# extension_count=4: 4800s (80 min)
# extension_count=5: 9600s (160 min) → capped at 86400s (24h)
```

**Extension Reset**: When entity changes, reset to base TTL:

```python
async def handle_stale_entry(entry: CacheEntry):
    """Reset TTL extension when entity changes."""
    entry.metadata["extension_count"] = 0
    entry.metadata["ttl"] = BASE_TTL_FOR_ENTITY_TYPE[entry.entity_type]
```

## Heuristics

### When to Check Staleness

| Access Pattern | Check Strategy | Rationale |
|----------------|----------------|-----------|
| On cache hit (EVENTUAL mode) | TTL check only | Trust cache, no API call |
| On cache hit (STRICT mode) | Lightweight watermark check | Validate freshness, minimal overhead |
| Before returning cached data | TTL + extension logic | Extend TTL if unchanged |
| Background refresh | Proactive batch check | Refresh before user access |

### Freshness Mode Selection

| Use Case | Recommended Mode | Why |
|----------|-----------------|-----|
| Interactive UI | STRICT | User expects current data |
| Reporting/analytics | EVENTUAL | Acceptable lag, performance priority |
| Webhook handlers | STRICT | Processing updates, need current state |
| Bulk operations | EVENTUAL | Read-heavy, slight staleness OK |
| Long-running sessions | STRICT + progressive TTL | Balance freshness and efficiency |

### Trade-offs

| Approach | Accuracy | Performance | Best For |
|----------|----------|-------------|----------|
| TTL-based | Medium | High (no API calls) | General purpose caching |
| Watermark | High | Medium (lightweight API call) | Strict freshness requirements |
| Progressive TTL | High | High (adapts to stability) | Stable entities, long sessions |

## Edge Cases

### Race Conditions

**Scenario**: Entity modified between staleness check and cache write.

**Mitigation**:
- Use API-provided `modified_at` as version marker
- Batch operations use consistent read timestamp
- Accept eventual consistency (last write wins)

### Clock Skew

**Scenario**: Client and server clocks differ.

**Mitigation**:
- Use API-provided timestamps, not client time
- TTL calculated from server `created_at`
- Staleness comparison uses API `modified_at` values

### Cache Invalidation

**Relationship**: Staleness detection is passive; invalidation is active.

**Staleness detection**: "Is this cached data still valid?"
**Cache invalidation**: "This data is now invalid, discard it."

**When to use each**:
- Staleness: Check on access (pull-based)
- Invalidation: Receive webhook or write operation (push-based)

**Combined approach**:
```python
# On webhook: explicit invalidation
await cache.delete(task_gid)

# On access: staleness check
entry = await cache.get(task_gid, freshness=Freshness.STRICT)
if entry and await cache.is_stale(entry):
    entry = None  # Fetch fresh data
```

### Deleted Entities

**Scenario**: Cached entity no longer exists in API.

**Detection**:
- Watermark check returns None (entity not found)
- Treat as stale, invalidate cache entry

**Handling**:
```python
current_modified = await fetch_modified_at(gid)
if current_modified is None:
    # Entity deleted, invalidate cache
    await cache.delete(gid)
    return None
```

## Integration Patterns

### Client Cache Pattern

**Pattern** (from ADR-0124): Integrate staleness checks into resource clients.

```python
class TaskClient:
    async def get_task(
        self,
        gid: str,
        freshness: Freshness = Freshness.EVENTUAL,
    ) -> Task:
        # Check cache
        entry = await self.cache.get(gid)

        if entry:
            # Check staleness
            is_stale = await self.cache.check_entry_staleness(
                entry,
                freshness=freshness
            )

            if not is_stale:
                return entry.data

        # Cache miss or stale: fetch from API
        task = await self.api.get_task(gid)

        # Update cache
        await self.cache.set(
            gid,
            task,
            metadata={"modified_at": task.modified_at}
        )

        return task
```

### Post-Commit Invalidation Pattern

**Pattern**: Invalidate cache after write operations.

```python
async def update_task(self, gid: str, data: dict) -> Task:
    # Update via API
    updated_task = await self.api.update_task(gid, data)

    # Invalidate cache (data just changed)
    await self.cache.delete(gid)

    # Optionally: populate cache with fresh data
    await self.cache.set(
        gid,
        updated_task,
        metadata={"modified_at": updated_task.modified_at}
    )

    return updated_task
```

### Batch Staleness Check Pattern

**Pattern**: Coalesce multiple staleness checks.

```python
# Collect expired entries within 50ms window
expired_entries = []
async for entry in cache_hits:
    if entry.is_expired():
        expired_entries.append(entry)

# Batch staleness check
staleness_results = await cache.check_batch_staleness(expired_entries)

# Process results
for entry in expired_entries:
    if staleness_results[entry.key]:
        # Stale: fetch from API
        await fetch_and_cache(entry.key)
    else:
        # Fresh: extend TTL
        await cache.extend_ttl(entry)
```

## Related Documentation

- [ADR-0019: Staleness Detection Algorithm](../decisions/ADR-0019-staleness-detection-algorithm.md) - Original decision and implementation
- [ADR-0133: Progressive TTL Extension Algorithm](../decisions/ADR-0133-progressive-ttl-extension-algorithm.md) - Progressive TTL specification
- [ADR-0134: Staleness Check Integration Pattern](../decisions/ADR-0134-staleness-check-integration-pattern.md) - Integration patterns
- [REF-cache-ttl-strategy.md](REF-cache-ttl-strategy.md) - TTL calculation details
- [REF-cache-provider-protocol.md](REF-cache-provider-protocol.md) - Cache provider integration
- [PRD-CACHE-LIGHTWEIGHT-STALENESS](../requirements/PRD-CACHE-LIGHTWEIGHT-STALENESS.md) - Requirements and use cases
- [RUNBOOK-cache-troubleshooting.md](../runbooks/RUNBOOK-cache-troubleshooting.md) - Operational troubleshooting
