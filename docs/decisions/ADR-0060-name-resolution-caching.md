# ADR-0060: Name Resolution Caching Strategy

**Status:** Accepted
**Date:** 2025-12-12
**Context:** Session 3 Architecture Design (PRD-SDKUX, P3)

---

## Problem

Priority 3 requires resolving human-readable names to GIDs (tag names → tag GIDs, project names → project GIDs, etc.). This requires fetching lists of resources (tags, projects, sections, users) from the API, which can be expensive.

Three caching strategies:

1. **Per-SaveSession Cache:** Cache within SaveSession context, clear on exit
   - Lifetime: Duration of SaveSession
   - Staleness: Zero (fresh data per session)
   - Memory: ~1KB per 100 names

2. **Per-Client TTL Cache:** Cache on client with time-to-live expiration
   - Lifetime: Minutes (e.g., 15 min for tags, 10 min for sections)
   - Staleness: Up to TTL duration
   - Memory: ~1MB per 1000 names
   - Complexity: Requires expiration management, LRU eviction

3. **No Caching:** Resolve names on every call
   - Freshest data (zero staleness risk)
   - Worst performance (API call per resolution)
   - Simplest implementation

## Decision

Implement **Per-SaveSession Caching** for initial implementation (MVP).

Store cache in SaveSession instance:
```python
class SaveSession:
    def __init__(self, ...):
        self._name_cache: dict[str, str] = {}  # key: "tag:name", value: gid
        self._name_resolver = NameResolver(self._client, self._name_cache)

    @property
    def name_resolver(self) -> NameResolver:
        return self._name_resolver
```

Clear cache automatically when SaveSession exits:
```python
async def __aexit__(self, ...):
    self._name_cache.clear()  # Implicit cleanup
    self._state = SessionState.CLOSED
```

## Rationale

### 1. MVP Simplicity
Per-session caching requires minimal code and no background tasks. Fits the "keep it simple" principle.

**Discovery Evidence:** Lines 135-149 in DISCOVERY-SDKUX-001 show per-session caching is sufficient for MVP. TTL-based caching explicitly noted as "future optimization."

### 2. Zero Staleness Within Session
Within a SaveSession context, all name resolutions use the same cache. If a tag is renamed mid-session, the cache won't catch it—but this is acceptable because:
- Sessions are typically seconds long (batch operations)
- Concurrent renames mid-session are rare
- User can create new session if needed (forces fresh cache)

### 3. Natural Lifetime Management
Cache lifetime matches SaveSession lifetime. No need for:
- Background expiry threads
- LRU eviction logic
- TTL checking on every access

**Pattern from SaveSession design:** Lines 159-174 in `persistence/session.py` show SaveSession already manages context lifecycle. Piggyback on that.

### 4. Memory Efficient
Cache is cleared on session exit. No memory leak risk. Typical workspace has ~100 tags, ~10 projects, ~5 sections per project. Cache size per session: <10KB.

### 5. Encourages Good Practices
Users naturally batch operations in SaveSession. Name resolutions happen in same context, so first resolution caches for the batch.

```python
async with SaveSession(client) as session:
    # First call: resolve "Urgent" → API call to list tags
    session.add_tag(task1, "Urgent")
    # Remaining calls: cache hit (no API calls)
    session.add_tag(task2, "Urgent")
    session.add_tag(task3, "Urgent")
    await session.commit_async()
```

## Consequences

### Positive
- Simple implementation (dict storage, no expiration logic)
- Zero staleness risk within session
- Automatic cleanup (no resource leaks)
- Encourages batching (cache hit rate improves with more operations)
- No external dependencies (no cache library needed)

### Negative
- Cache doesn't persist across sessions
- For many small operations, overhead of recreating cache
- Can't optimize for repeated operations spanning multiple sessions
- No insights into cache hit/miss rates (no metrics)

### Neutral
- Users must create SaveSession even for single operations if they want caching (fine; P1 methods create implicit sessions)

## Implementation Details

### Cache Key Format
```python
cache_key = f"{resource_type}:{name}:{scope}"
# Examples:
# "tag:Urgent:workspace_123"
# "section:In Progress:project_456"
# "project:Marketing:workspace_123"
# "user:alice@example.com:workspace_123"
```

### NameResolver Integration
```python
class NameResolver:
    def __init__(self, client: AsanaClient, session_cache: dict[str, str]):
        self._client = client
        self._cache = session_cache  # Shared with SaveSession

    async def resolve_tag_async(self, name_or_gid: str, ...) -> str:
        if self._looks_like_gid(name_or_gid):
            return name_or_gid

        cache_key = f"tag:{name_or_gid}"
        if cached := self._cache.get(cache_key):
            return cached

        # Fetch, find, cache, return...
```

### SaveSession Integration
```python
class SaveSession:
    def __init__(self, client: AsanaClient, ...):
        self._name_cache: dict[str, str] = {}
        self._name_resolver = NameResolver(client, self._name_cache)

    @property
    def name_resolver(self) -> NameResolver:
        """Get name resolver for this session (uses session cache)."""
        return self._name_resolver

    async def __aexit__(self, ...):
        self._name_cache.clear()  # Auto-cleanup
        self._state = SessionState.CLOSED
```

## Future Enhancement: Per-Client TTL Cache

When MVP is complete, can add per-Client cache:

```python
class AsanaClient:
    def __init__(self, ...):
        self._name_cache_ttl = TTLCache(
            maxsize=1000,
            ttl=900,  # 15 minutes
        )

    # Use in NameResolver if no session cache
    if session_cache is None:
        session_cache = self._name_cache_ttl
```

**Trigger for upgrade:** If monitoring shows >5% of name resolutions hit network (cache miss rate too high).

## Alternatives Considered

### Alternative A: Per-Client TTL Cache from Start
```python
class AsanaClient:
    _name_cache = TTLCache(maxsize=1000, ttl=900)
```

**Rejected:** Over-engineering for MVP. Adds complexity (expiration, LRU) without proven need. Can be added later when requirements demand.

### Alternative B: No Caching
Resolve names on every call without caching.

**Rejected:** Performance issue. Resolving "Urgent" requires listing all workspace tags (~100 items). In batch of 10 operations, 10 API calls instead of 1.

### Alternative C: User-Managed Cache
Expose caching to users: `client.name_cache.get("Urgent")`

**Rejected:** Shifts burden to users. Implicit caching is better DX.

## Validation

**Discovery Question Q3 (Lines 95-149):** "For workspace-level resources, can we list them once and cache?"

**Answer:** ✓ YES. Lines 104-108 show TagsClient.list_for_workspace_async() returns all tags. Caching those 100 items per session is efficient.

**Discovery Recommendation (Lines 135-149):** "Per-session caching is low-risk and viable for MVP."

**Evidence:** Implemented in similar SDKs (Firebase, AWS SDK); users expect this pattern.

## Testing Strategy

### Cache Hit/Miss Tests
```python
async def test_cache_hit_same_session():
    async with SaveSession(client) as session:
        # First call: misses cache
        gid1 = await session.name_resolver.resolve_tag_async("Urgent")

        # Second call: hits cache (no API call)
        gid2 = await session.name_resolver.resolve_tag_async("Urgent")

        assert gid1 == gid2
        # Verify only 1 API call made (mock _http.get)

async def test_cache_cleared_on_session_exit():
    async with SaveSession(client) as session:
        gid = await session.name_resolver.resolve_tag_async("Urgent")

    async with SaveSession(client) as session:
        # New session has empty cache
        # Next call will hit API again
        assert len(session._name_cache) == 0
```

### Scope Tests
```python
async def test_project_scope_caching():
    # Section names are project-scoped
    gid1 = await resolver.resolve_section_async("In Progress", project_123)
    gid2 = await resolver.resolve_section_async("In Progress", project_456)

    # Different GIDs even though same name (different projects)
    assert gid1 != gid2

    # Cache keys differentiate by scope
    # "section:In Progress:project_123" != "section:In Progress:project_456"
```

## Decision Log

- **2025-12-12:** Architect chose per-session caching as MVP with documented path to TTL cache
- **Trade-off:** Simplicity now, performance optimization later if needed
- **No blocking questions remaining** (all answered in DISCOVERY-SDKUX-001, Lines 135-149)

---
