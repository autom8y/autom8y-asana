# ADR-0072: Resolution Caching Decision

## Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: Architect
- **Related**: PRD-RESOLUTION (Q2), TDD-RESOLUTION, ADR-0052 (Bidirectional References), ADR-0060 (Name Resolution Caching)

## Context

When resolving an AssetEdit to its owning Unit multiple times, should we cache the result to avoid redundant API calls?

**Question from PRD (Q2)**: Should resolution cache results within a session?

### Current Caching Patterns

The SDK has two related caching patterns:

1. **Bidirectional Reference Caching (ADR-0052)**: Business model entities cache navigation references (e.g., `Unit._business`). These are structural/hierarchical relationships that don't change during a session.

2. **Name Resolution Caching (ADR-0060)**: SaveSession caches name->GID resolution to avoid repeated lookups of the same tag/project name.

### Resolution Semantics

Cross-holder resolution is fundamentally different from both patterns:

1. **Not hierarchical**: AssetEdit -> Unit is not a parent/child relationship
2. **Multiple strategies**: Different strategies may produce different results
3. **External state dependent**: Resolution depends on task dependents, custom fields, or explicit IDs - all of which can change
4. **Strategy-specific**: Caching a result from DEPENDENT_TASKS shouldn't short-circuit EXPLICIT_OFFER_ID

### Use Cases

1. **Single resolution**: Resolve once, use result
2. **Re-resolution after change**: AssetEdit custom field updated, resolve again
3. **Strategy comparison**: Try different strategies to compare results
4. **Batch operations**: Resolve many AssetEdits in one operation

## Decision

**Resolution results are NOT cached.** Each call to `resolve_unit_async()` or `resolve_offer_async()` executes the resolution logic fresh.

### Rationale

1. **Different semantics**: Resolution is a query, not a relationship traversal
2. **Strategy flexibility**: Callers may want different strategies on subsequent calls
3. **Freshness**: Resolution depends on current API state (dependents, custom fields)
4. **Batch optimization**: Batch helpers provide efficiency without caching complexity
5. **Simplicity**: No cache invalidation logic needed

### Caller-Side Caching

Callers who need caching can implement it trivially:

```python
# Caller maintains their own cache if needed
resolution_cache: dict[str, Unit] = {}

async def get_unit_for_asset_edit(asset_edit: AssetEdit) -> Unit | None:
    if asset_edit.gid not in resolution_cache:
        result = await asset_edit.resolve_unit_async(client)
        if result.success:
            resolution_cache[asset_edit.gid] = result.entity
    return resolution_cache.get(asset_edit.gid)
```

### Batch Operations as Alternative

For efficiency without caching, use batch resolution:

```python
# Instead of resolving one at a time (N API calls)
for ae in asset_edits:
    result = await ae.resolve_unit_async(client)

# Use batch resolution (optimized, shared lookups)
results = await resolve_units_async(asset_edits, client)
```

## Alternatives Considered

### Option A: Cache Results Per Instance

- **Description**: `AssetEdit._resolved_unit: Unit | None` cached after first resolution
- **Pros**: Fast repeated access; matches bidirectional reference pattern
- **Cons**: Stale on external changes; strategy-specific caching complex; invalidation unclear
- **Why not chosen**: Semantics differ from hierarchical navigation

### Option B: Session-Scoped Resolution Cache

- **Description**: Like name resolution (ADR-0060), cache in session context
- **Pros**: Consistent with existing pattern; automatic invalidation on session end
- **Cons**: Resolution is independent of SaveSession; would need new scope mechanism
- **Why not chosen**: Resolution doesn't fit SaveSession lifecycle

### Option C: Strategy-Specific Caching

- **Description**: Cache per (AssetEdit, Strategy) tuple
- **Pros**: Preserves strategy flexibility; enables strategy comparison
- **Cons**: Complex implementation; unclear invalidation; memory overhead
- **Why not chosen**: Over-engineered for use cases; batch operations solve efficiency

### Option D: LRU Cache with TTL

- **Description**: Time-bounded cache with configurable TTL
- **Pros**: Handles staleness via expiration
- **Cons**: Configuration complexity; TTL selection arbitrary; still may be stale
- **Why not chosen**: Adds complexity without clear benefit over batch operations

## Consequences

### Positive

- **Simplicity**: No cache management, invalidation, or configuration
- **Freshness**: Results always reflect current API state
- **Flexibility**: Callers can cache if needed with their own policy
- **Strategy independence**: Each call can use different strategy
- **Batch efficiency**: resolve_units_async() provides optimized bulk resolution

### Negative

- **Repeated API calls**: Multiple resolve calls on same AssetEdit incur API cost
- **No automatic optimization**: Callers must use batch helpers for efficiency
- **Learning curve**: Callers expecting automatic caching may be surprised

### Neutral

- Batch resolution functions provide efficiency for common patterns
- Documentation explains caching decision and batch alternatives
- Logging includes API call counts for performance visibility

## Compliance

- Resolution methods MUST NOT cache results internally
- Resolution methods MUST make fresh API calls on each invocation
- Batch resolution functions MUST optimize shared lookups (e.g., fetch Business once)
- Documentation MUST explain caching decision and recommend batch operations
- Performance tests MUST compare single vs. batch resolution API call counts
