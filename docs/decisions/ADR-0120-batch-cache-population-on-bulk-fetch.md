# ADR-0120: Batch Cache Population on Bulk Fetch

## Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-23
- **Deciders**: Architect, Principal Engineer
- **Related**: TDD-CACHE-UTILIZATION, ADR-0119 (Client Cache Integration Pattern), ADR-0115 (Parallel Section Fetch Strategy)

---

## Context

When SDK clients fetch lists of entities (e.g., `list_for_project_async()` for sections, `list_async()` for projects), they retrieve full entity data that could be cached individually. Currently, this data is used once and discarded. Subsequent `get_async()` calls for the same entities result in separate API requests.

**Use case**: DataFrame extraction via parallel section fetch (ADR-0115) fetches all sections for a project. If individual sections are later accessed via `get_async()`, they should come from cache rather than triggering new API calls.

**Forces at play**:
- `CacheProvider.set_batch()` exists but is unused
- Bulk fetch returns full entity data
- Subsequent individual lookups should hit cache
- Per-page population minimizes overhead
- Cache key must match `get_async()` pattern

---

## Decision

We will **populate individual cache entries during bulk fetch operations** using `CacheProvider.set_batch()`.

**Implementation**:
1. After each page is fetched via `get_paginated()`
2. Build `CacheEntry` for each entity in the page
3. Call `self._cache.set_batch(entries)` before returning models
4. Cache keys match `get_async()` pattern: `{gid}:{entry_type}`

**Priority for implementation**:

| Method | Client | Priority | Impact |
|--------|--------|----------|--------|
| `list_for_project_async()` | SectionsClient | P0 | Enables parallel fetch cache hits |
| `list_async()` | ProjectsClient | P1 | Workspace-wide project warm |
| `list_for_workspace_async()` | UsersClient | P2 | User directory warm |
| `list_for_workspace_async()` | CustomFieldsClient | P2 | Schema warming |

---

## Rationale

### Opportunistic Cache Warming

The data is already fetched and parsed. Populating cache costs only:
- `CacheEntry` construction (~100ns per entry)
- `set_batch()` call (O(n) dict insertion)

This is negligible compared to the API call that fetched the data.

### Consistent Cache Keys

By using the same key format as `get_async()`, subsequent lookups hit the cache:

```python
# Bulk fetch populates cache
sections = await client.sections.list_for_project_async(project_gid).collect()
# Cache now has: {"section_gid_1:section", "section_gid_2:section", ...}

# Individual lookup hits cache
section = await client.sections.get_async("section_gid_1")
# Returns from cache, no API call
```

### Per-Page vs. Post-Collection

We populate cache **per page** (in `fetch_page()`) rather than after full collection because:
- Immediate benefit: Cache available even if iteration stops early
- Memory efficiency: No need to buffer all entries
- Failure isolation: Partial success still caches fetched pages

### Graceful Degradation

If cache is unavailable or `set_batch()` fails, the operation continues. BaseClient pattern:

```python
if self._cache and data:
    try:
        entries = {...}
        self._cache.set_batch(entries)
    except Exception:
        # Log and continue - caching is optional
        pass
```

---

## Alternatives Considered

### Alternative 1: Post-Collection Population

- **Description**: Cache all entries after `collect()` completes
- **Pros**: Single `set_batch()` call
- **Cons**:
  - Requires buffering all entries
  - No benefit for early iteration termination
  - Memory overhead for large collections
- **Why not chosen**: Per-page is more efficient and provides immediate benefit

### Alternative 2: Cache Only Full Pages

- **Description**: Cache page-level aggregates, not individual entries
- **Pros**: Fewer cache entries
- **Cons**:
  - Key format doesn't match `get_async()` pattern
  - Violates ADR-0118 (no aggregate caching)
  - Individual lookups still miss cache
- **Why not chosen**: Incompatible with per-entity cache architecture

### Alternative 3: Background Population

- **Description**: Spawn async task to populate cache after returning results
- **Pros**: No latency impact on return path
- **Cons**:
  - Complex async coordination
  - Data may be stale by time of population
  - Cache unavailable for immediate subsequent calls
- **Why not chosen**: Synchronous population is fast enough; immediate availability matters

### Alternative 4: Opt-In Population via Parameter

- **Description**: Add `populate_cache: bool = False` parameter to list methods
- **Pros**: User control over cache behavior
- **Cons**:
  - API surface expansion
  - Default should be optimal behavior
  - Users unlikely to think about this
- **Why not chosen**: Population should be automatic; it's always beneficial

---

## Consequences

### Positive

- **Cache warm on bulk fetch**: Subsequent `get_async()` calls hit cache
- **No API overhead**: Uses already-fetched data
- **Minimal code change**: ~10 lines per list method
- **Parallel fetch benefit**: ADR-0115 pattern automatically warms cache

### Negative

- **Increased memory in cache**: More entries stored
- **TTL fragmentation**: Entries may expire at different times than if fetched individually
- **Page-level coupling**: If page structure changes, population logic may need adjustment

### Neutral

- **Metrics impact**: `set_batch()` doesn't record individual writes to metrics (acceptable)
- **Test coverage**: Need to verify cache population in list method tests

---

## Compliance

To ensure this decision is followed:

1. **List method template**: All `list_*()` methods should include batch population block
2. **Test verification**: Unit tests must verify that `set_batch()` is called with correct entries
3. **Entry format**: `CacheEntry` must use same parameters as `get_async()` caching

**Pattern template**:

```python
async def fetch_page(offset: str | None) -> tuple[list[Model], str | None]:
    params = self._build_opt_fields(opt_fields)
    params["limit"] = min(limit, 100)
    if offset:
        params["offset"] = offset

    data, next_offset = await self._http.get_paginated(
        f"/path/to/resource", params=params
    )

    # Batch populate cache
    if self._cache and data:
        from autom8_asana.cache.entry import CacheEntry, EntryType
        from datetime import datetime, timezone

        entries = {}
        now = datetime.now(timezone.utc)
        for item in data:
            # Extract version from modified_at if available
            version = now
            if "modified_at" in item:
                version = self._parse_modified_at(item["modified_at"])

            entry = CacheEntry(
                key=item["gid"],
                data=item,
                entry_type=EntryType.{TYPE},
                version=version,
                ttl={TTL},
            )
            entries[item["gid"]] = entry
        self._cache.set_batch(entries)

    models = [Model.model_validate(item) for item in data]
    return models, next_offset
```

**Implementation checklist for each list method**:
- [ ] Import `CacheEntry` and `EntryType` inside fetch_page
- [ ] Check `self._cache and data` before population
- [ ] Use `datetime.now(timezone.utc)` for version when no `modified_at`
- [ ] Use correct `EntryType` for the entity
- [ ] Use TTL matching the entity's `get_async()` TTL
- [ ] Call `self._cache.set_batch(entries)`
