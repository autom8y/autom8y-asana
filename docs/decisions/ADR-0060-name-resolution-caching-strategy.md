# ADR-0060: Name Resolution Caching Strategy

**Date:** 2025-12-12
**Status:** Approved
**Context:** SDK Usability Overhaul - Name Resolution (P3, Session 3)
**References:** PRD-SDKUX, DISCOVERY-SDKUX-001 (lines 135-149)

---

## Context and Problem

P3 (Name Resolution) requires resolving human-readable names (tag names, project names, etc.) to GIDs. This involves API calls to list all names in a scope:

```python
# List all tags in workspace
async for tag in client.tags.list_for_workspace_async(workspace_gid):
    if tag.name.lower() == "Urgent".lower():
        return tag.gid
```

**Problem:** For repeated name resolutions in the same batch operation, this results in duplicate API calls:

```python
async with SaveSession(client) as session:
    # First call: lists all tags (100+ tags)
    tag_gid_1 = await resolver.resolve_tag_async("Urgent", workspace_gid)

    # Second call: lists all tags AGAIN (duplicate API call!)
    tag_gid_2 = await resolver.resolve_tag_async("Backlog", workspace_gid)
```

We need to decide: should we cache at the **SaveSession level** (per-operation), **Client level** (global with TTL), or **no caching at all**?

**Three Options:**

1. **Per-SaveSession Cache (chosen)**: Cache within SaveSession context, cleared on exit
   - Pros: Zero staleness, simple, safe lifetime management
   - Cons: No benefit across different sessions

2. **Per-Client TTL Cache**: Cache on client with expiration (5-15 min TTL)
   - Pros: Benefits across multiple sessions
   - Cons: Staleness risk, more complex, requires maintenance

3. **No Caching**: Fetch fresh every time
   - Pros: Simplest, zero staleness
   - Cons: Poor performance for repeated names in same session

---

## Decision

**Implement Per-SaveSession Cache** - Cache name resolutions within each SaveSession context, cleared when context exits.

### Implementation

```python
class NameResolver:
    """Resolve resource names to GIDs with per-session caching."""

    def __init__(self, client: AsanaClient):
        self._client = client
        self._cache: dict[str, dict[str, str]] = {}  # scope -> {name: gid}

    async def resolve_tag_async(
        self,
        name_or_gid: str,
        project_gid: str | None = None
    ) -> str:
        """Resolve tag name to GID with caching."""
        # GID passthrough
        if self._looks_like_gid(name_or_gid):
            return name_or_gid

        # Check cache
        cache_key = f"tag:{self._client.default_workspace_gid}"
        if cache_key in self._cache:
            if name_or_gid.lower() in self._cache[cache_key]:
                return self._cache[cache_key][name_or_gid.lower()]

        # Cache miss - fetch and populate
        all_tags = []
        async for tag in self._client.tags.list_for_workspace_async(
            self._client.default_workspace_gid
        ):
            all_tags.append(tag)

        # Initialize cache for this scope
        if cache_key not in self._cache:
            self._cache[cache_key] = {}

        # Populate cache
        for tag in all_tags:
            cache_key_name = tag.name.lower().strip()
            self._cache[cache_key][cache_key_name] = tag.gid

            if cache_key_name == name_or_gid.lower().strip():
                return tag.gid

        # Not found - raise with suggestions
        available_names = [tag.name for tag in all_tags]
        suggestions = get_close_matches(name_or_gid, available_names, n=3, cutoff=0.6)
        raise NameNotFoundError(
            name=name_or_gid,
            resource_type="tag",
            scope=self._client.default_workspace_gid,
            suggestions=suggestions,
            available_names=available_names
        )
```

**Cache Behavior:**

1. **First resolve call** (cache miss):
   ```
   resolve_tag_async("Urgent") → List all tags (1 API call) → Cache result → Return GID
   ```

2. **Repeated resolve call** (cache hit):
   ```
   resolve_tag_async("Backlog") → Check cache (0 API calls) → Return GID
   ```

3. **Next SaveSession** (new cache):
   ```
   Previous cache discarded when SaveSession exits → Fresh list on new session
   ```

**Scope Mapping:**

- **Workspace-scoped resources** (tags, projects, users): Cache key = `resource:workspace_gid`
- **Project-scoped resources** (sections): Cache key = `section:project_gid`

---

## Rationale

### Why Per-SaveSession Cache (not TTL or no caching)?

1. **Zero Staleness**
   - Data fetched fresh at session start
   - No stale GID risk (resource renamed, moved, deleted)
   - Especially important for sections (project-scoped, volatile)

2. **Simple Lifecycle Management**
   - Cache tied to SaveSession context manager
   - No need to manage expiration, cleanup, or invalidation
   - When session exits, cache automatically discarded

3. **Sufficient Performance**
   - Typical batch operation: 5-10 names from same workspace
   - Per-session cache: 1 API call per scope, reused for all names
   - Performance improvement: 5-10x reduction in API calls

4. **Safe Memory Usage**
   - Each cache: ~1KB per 100 names
   - Lifetime: Duration of SaveSession (seconds to minutes)
   - No long-term memory pressure

5. **MVP Priority**
   - Meets P3 requirements
   - Future optimization: Add per-Client TTL cache without breaking existing code
   - Avoids premature complexity

### Why Not Per-Client TTL Cache?

1. **Complexity**
   - Requires LRU cache implementation or decorator
   - TTL selection: Too short (misses benefit), too long (staleness risk)
   - Invalidation: How to detect when names change? (not available in API)

2. **Staleness Risk**
   - Tag renamed: Old GID cached, user gets "tag not found" error
   - User deleted: Old GID still in cache, causes unexpected behavior
   - Especially problematic for project-scoped sections

3. **Not Blocking**
   - Per-SaveSession cache is sufficient for MVP
   - Can add TTL cache in future (P3.1 optimization)
   - No users blocked waiting for cross-session benefit

4. **Multi-Tenant Complexity**
   - If client switches workspaces: Cache could have wrong workspace's data
   - Per-session eliminates this risk

### Why Not No Caching?

1. **Performance Regression**
   - SaveSession batch operation with 5 operations on same workspace
   - Without cache: 5 API calls to list all tags (even if resolved multiple times)
   - With cache: 1 API call to list tags, 4 cache hits

2. **Cost**
   - Each list API call costs quota
   - Repeated listing is wasteful

---

## Consequences

### Positive

1. **Zero Staleness**: Fresh data at session start, no risk of using deleted/renamed resources
2. **Simple**: Cache lifecycle tied to SaveSession (no manual management)
3. **Safe**: Memory limited by session duration (not accumulating across app lifetime)
4. **Efficient**: Batch operations get 5-10x reduction in API calls
5. **Testable**: Cache behavior easy to verify within session scope

### Negative

1. **No Cross-Session Benefit**: Cache discarded when SaveSession exits
   - User making two separate calls: No cached benefit
   - Mitigation: Typical usage bundles operations in single SaveSession

2. **Requires SaveSession**: Name resolution tied to SaveSession lifecycle
   - Mitigation: Can instantiate separate NameResolver instance for different use cases
   - Document: "For repeated resolutions, use SaveSession"

3. **Namespace Pollution**: Cache grows as more names resolved
   - Mitigation: Cache cleared with SaveSession (bounded growth)
   - Typical workspace: <1000 names → <1MB cache

### Neutral

1. **Future Optimization Path**: Can add per-Client TTL cache without changing API
2. **Compatible with Direct Methods (P1)**: Each direct method creates short SaveSession with fresh cache

---

## Alternatives Considered

### Alternative 1: Per-Client TTL Cache

```python
# Hypothetical - NOT CHOSEN
class NameResolver:
    def __init__(self, client: AsanaClient):
        self._client = client
        self._cache_with_ttl: dict[str, tuple[str, float]] = {}  # gid, expiry

    async def resolve_tag_async(self, name_or_gid: str, ...) -> str:
        cache_key = f"tag:{name_or_gid.lower()}"
        if cache_key in self._cache_with_ttl:
            gid, expiry = self._cache_with_ttl[cache_key]
            if time.time() < expiry:
                return gid  # Cache hit

        # Cache miss - fetch and store with TTL
        gid = await self._fetch_tag_gid(name_or_gid)
        self._cache_with_ttl[cache_key] = (gid, time.time() + 600)  # 10 min TTL
        return gid
```

**Rejected because:**
- Staleness risk (renamed/deleted resources)
- Complex TTL selection
- No automatic cleanup (need background thread or manual invalidation)
- Over-engineered for MVP

### Alternative 2: No Caching

```python
# Hypothetical - NOT CHOSEN
async def resolve_tag_async(self, name_or_gid: str, ...) -> str:
    if self._looks_like_gid(name_or_gid):
        return name_or_gid

    # Always fetch fresh
    async for tag in self._client.tags.list_for_workspace_async(...):
        if tag.name.lower() == name_or_gid.lower():
            return tag.gid

    # Not found
    raise NameNotFoundError(...)
```

**Rejected because:**
- No performance benefit for batch operations
- Each resolve call costs API quota
- Repeated resolutions in same session: wasted API calls

---

## Implementation Notes

### File: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/name_resolver.py`

1. **NameResolver class**
   - Init: `__init__(self, client: AsanaClient)`
   - Cache: `self._cache: dict[str, dict[str, str]]` (scope -> {name.lower(): gid})

2. **Resolve methods**
   - `resolve_tag_async()`, `resolve_tag()`
   - `resolve_section_async()`, `resolve_section()`
   - `resolve_project_async()`, `resolve_project()`
   - `resolve_assignee_async()`, `resolve_assignee()`

3. **Helper methods**
   - `_looks_like_gid()`: Check if input is 36-char alphanumeric
   - `_get_cache_key()`: Generate scope-based cache key
   - `_fetch_and_cache()`: List API, populate cache, find match

4. **Error handling**
   - Raise `NameNotFoundError` with suggestions
   - Include available names for debugging

### Integration with SaveSession

Option: Store NameResolver instance on SaveSession
```python
# In SaveSession.__init__
self._name_resolver = NameResolver(client)

# Users access via
async with SaveSession(client) as session:
    tag_gid = await session._name_resolver.resolve_tag_async("Urgent")
```

**Or**: Pass NameResolver separately
```python
resolver = NameResolver(client)
async with SaveSession(client) as session:
    tag_gid = await resolver.resolve_tag_async("Urgent")
```

**Decision**: Implement standalone NameResolver; future P3.1 can integrate with SaveSession

---

## Verification

### Tests Required

1. **Cache Hit**
   - First resolve: API call made
   - Second resolve (same name): No API call (cache hit)

2. **Cache Isolation**
   - Different scopes (different workspaces): Separate caches
   - New SaveSession: Fresh cache (old cache not reused)

3. **Correctness**
   - Cached GID matches fresh fetch
   - Case-insensitive matching works
   - GID passthrough works

4. **Staleness**
   - Within session: Cache is current (fresh from session start)
   - Across sessions: Old cache discarded, fresh fetch on new session

### Backward Compatibility

- No impact on existing SaveSession (unchanged)
- New NameResolver is pure addition
- No changes to existing API

---

## Decision Record

**Decision:** Implement Per-SaveSession Cache for name resolution

**Decided by:** Architect (Session 3)

**Rationale:** Zero staleness, simple lifecycle, sufficient performance, MVP-ready

**Implementation Timeline:** Session 5b (P3 Priority, after P1)

**Future Optimization:** Can add per-Client TTL cache in P3.1 without API changes

---

## Related ADRs

- ADR-0059: Direct Methods vs SaveSession Actions (P1 methods use name resolution)
- ADR-0035: Unit of Work Pattern (SaveSession design)

---
