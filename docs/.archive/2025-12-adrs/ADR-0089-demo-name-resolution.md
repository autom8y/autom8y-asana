# ADR-DEMO-002: Name Resolution Approach for Demo Scripts

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-12
- **Deciders**: SDK Team
- **Related**: PRD-SDKDEMO, TDD-SDKDEMO, DISCOVERY-SDKDEMO

## Context

The SDK Demonstration Suite (PRD-SDKDEMO) requires resolving human-readable names to Asana GIDs for:
- **Tags** ("optimize" -> tag GID)
- **Users** ("Tom Tenuta" -> user GID)
- **Enum options** ("High Priority" -> option GID)
- **Sections** ("BUSINESSES" -> section GID)
- **Projects** ("Businesses" -> project GID)

Per Discovery (DISCOVERY-SDKDEMO), the SDK provides:
- **CustomFieldAccessor**: Built-in name-to-GID resolution for custom **field names** (not enum option names)
- **No built-in resolution** for tags, users, sections, or projects

**Forces at play**:

1. **User experience**: Demo should use human-readable names, not cryptic GIDs
2. **Performance**: Name resolution requires API calls; should minimize redundant lookups
3. **Reliability**: Names may not exist; must handle gracefully
4. **Maintainability**: Resolution logic should be reusable across demo categories
5. **SDK alignment**: Should follow SDK patterns (async-first, client usage)

## Decision

**Implement lazy-loading name resolution with session-scoped caching.**

```python
class NameResolver:
    """Resolves human-readable names to Asana GIDs with caching."""

    def __init__(self, client: AsanaClient, workspace_gid: str):
        self._client = client
        self._workspace_gid = workspace_gid
        self._tag_cache: dict[str, str] | None = None  # name -> gid
        self._user_cache: dict[str, str] | None = None
        self._section_cache: dict[str, dict[str, str]] | None = None  # project_gid -> {name: gid}
        self._project_cache: dict[str, str] | None = None

    async def resolve_tag(self, name: str) -> str | None:
        """Resolve tag name to GID. Returns None if not found."""
        if self._tag_cache is None:
            await self._load_tags()
        return self._tag_cache.get(name.lower())

    async def resolve_user(self, name: str) -> str | None:
        """Resolve user display name to GID."""
        if self._user_cache is None:
            await self._load_users()
        return self._user_cache.get(name.lower())

    async def resolve_section(self, project_gid: str, name: str) -> str | None:
        """Resolve section name within a project."""
        if self._section_cache is None:
            self._section_cache = {}
        if project_gid not in self._section_cache:
            await self._load_sections(project_gid)
        return self._section_cache.get(project_gid, {}).get(name.lower())
```

**Key behaviors**:
1. **Lazy loading**: Cache populated on first use, not at startup
2. **Session-scoped**: Single cache instance per demo run
3. **Case-insensitive**: All lookups normalized to lowercase
4. **None on miss**: Returns `None` (not exception) for missing names
5. **Workspace-scoped**: Tags and users loaded for entire workspace

## Rationale

1. **Lazy loading minimizes unnecessary API calls**: If demo skips tag operations, tag cache never loads. Reduces startup latency.

2. **Session-scoped caching is appropriate**: Within a single demo run, tags/users/sections won't change. Fresh cache on next run captures any changes.

3. **Case-insensitive matching is user-friendly**: "Optimize", "optimize", "OPTIMIZE" all resolve to same tag.

4. **None return enables graceful degradation**: Caller decides how to handle missing names (skip, create, error).

5. **Centralized resolver is reusable**: All 10 demo categories can share one resolver instance.

## Alternatives Considered

### Alternative 1: Eager Loading at Startup

- **Description**: Load all caches at demo startup before any operations
- **Pros**: Fast resolution during demo, predictable latency
- **Cons**:
  - Slow startup (multiple API calls before user sees anything)
  - Loads data that may never be used
  - Users who just want to run one category wait for all caches
- **Why not chosen**: Lazy loading provides better perceived performance

### Alternative 2: No Caching (Lookup Each Time)

- **Description**: Every name resolution makes an API call
- **Pros**: Always fresh data, no stale cache concerns
- **Cons**:
  - Extremely slow for repeated lookups
  - Unnecessary API load
  - May hit rate limits in demos with many operations
- **Why not chosen**: Unacceptable performance for interactive demo

### Alternative 3: Use CustomFieldAccessor Pattern for All

- **Description**: Extend CustomFieldAccessor's approach to tags/users/sections
- **Pros**: Consistent pattern, leverages existing code
- **Cons**:
  - CustomFieldAccessor works with entity's own custom_fields list
  - Tags/users don't follow same pattern (workspace-level resources)
  - Would require significant SDK modification
- **Why not chosen**: Different resource types have fundamentally different resolution patterns

### Alternative 4: Global Persistent Cache

- **Description**: Cache persists across demo runs (file-based or redis)
- **Pros**: Instant resolution after first run
- **Cons**:
  - Stale data if workspace changes between runs
  - Cache invalidation complexity
  - Overkill for demo scripts
- **Why not chosen**: Session-scoped caching is simpler and sufficient

## Consequences

### Positive
- **Fast resolution after first lookup**: O(1) dictionary lookups
- **Minimal startup latency**: No API calls until actually needed
- **User-friendly interface**: Pass names, not GIDs
- **Centralized resolution logic**: Easy to maintain and test

### Negative
- **First lookup is slow**: API call required to populate cache
- **Memory for workspace data**: May load all tags/users even if demo uses few
- **Cache not shared across demo runs**: Fresh lookups on each run

### Neutral
- **Enum option resolution requires custom field definition**: Must fetch field definition to get option name->GID mapping (not cached separately)
- **Project-scoped sections**: Section cache is keyed by project_gid

## Compliance

Ensure this decision is followed by:
- Code review: "Name resolution uses NameResolver class, not inline lookups"
- No hardcoded GIDs in demo scripts (except entity GIDs from test data doc)
- All resolution calls use `await resolver.resolve_*()` pattern
- Missing name handling is explicit (check for None, decide action)

