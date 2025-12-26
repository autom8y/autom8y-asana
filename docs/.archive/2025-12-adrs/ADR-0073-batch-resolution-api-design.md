# ADR-0073: Batch Resolution API Design

## Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: Architect
- **Related**: PRD-RESOLUTION (Q3, FR-BATCH-001, FR-BATCH-002), TDD-RESOLUTION, ADR-0072 (Resolution Caching)

## Context

Batch resolution of multiple AssetEdits to Units/Offers is a high-frequency use case per PRD-RESOLUTION discovery. The API design must balance:

1. **Efficiency**: Minimize redundant API calls
2. **Ergonomics**: Easy to use for common patterns
3. **Consistency**: Match existing SDK patterns
4. **Flexibility**: Support different resolution strategies

**Question from PRD (Q3)**: Should batch resolution be a module function or class method?

### Existing Patterns

The SDK has several batch operation patterns:

1. **Instance methods**: `task.save_async()`, `business.from_gid_async()`
2. **Client methods**: `client.tasks.list_async()`, `client.tasks.subtasks_async()`
3. **Module functions**: None currently for batch entity operations
4. **SaveSession**: Batch persistence via `session.commit_async()`

### Use Cases

1. **Report generation**: Resolve all AssetEdits under a Business to group by Unit
2. **Webhook batch**: Process multiple AssetEdit updates in one batch
3. **Data migration**: Resolve and update large collections

## Decision

**Batch resolution is implemented as module-level functions** in `resolution.py`:

```python
# Module functions in src/autom8_asana/models/business/resolution.py

async def resolve_units_async(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Unit]]:
    """Batch resolve multiple AssetEdits to Units."""

async def resolve_offers_async(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Offer]]:
    """Batch resolve multiple AssetEdits to Offers."""
```

### API Design

```python
# Usage
from autom8_asana.models.business.resolution import resolve_units_async

results = await resolve_units_async(asset_edits, client)

for asset_edit in asset_edits:
    result = results[asset_edit.gid]
    if result.success:
        print(f"{asset_edit.name} -> {result.entity.name}")
```

### Return Type

Dictionary mapping `asset_edit.gid` to `ResolutionResult`:
- Every input AssetEdit has an entry (even on failure)
- GID key enables O(1) lookup without searching
- Matches patterns like `asyncio.gather()` results

### Optimization Strategy

1. **Group by Business**: Identify unique Businesses from input AssetEdits
2. **Bulk hydration**: Ensure each Business has units hydrated (single fetch per Business)
3. **Concurrent dependents fetch**: For DEPENDENT_TASKS strategy, fetch dependents concurrently
4. **Shared offer lookups**: For EXPLICIT_OFFER_ID strategy, batch fetch unique offer_ids
5. **Per-AssetEdit resolution**: Apply resolution logic using pre-fetched data

```python
async def resolve_units_async(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Unit]]:
    # 1. Collect unique Businesses
    businesses = _collect_unique_businesses(asset_edits)

    # 2. Ensure all Businesses have units hydrated
    await asyncio.gather(*[
        _ensure_units_hydrated(b, client) for b in businesses.values()
    ])

    # 3. Pre-fetch strategy-specific data concurrently
    if strategy in (ResolutionStrategy.AUTO, ResolutionStrategy.DEPENDENT_TASKS):
        dependents_map = await _batch_fetch_dependents(asset_edits, client)

    # 4. Resolve each AssetEdit using pre-fetched data
    results = {}
    for ae in asset_edits:
        result = await _resolve_single_with_context(
            ae, client, strategy,
            dependents=dependents_map.get(ae.gid, []),
            business=businesses.get(ae._business.gid if ae._business else None),
        )
        results[ae.gid] = result

    return results
```

## Rationale

**Why module functions instead of class methods?**

1. **No natural class home**: Batch resolution operates on a collection, not a single entity
2. **Cleaner signature**: `resolve_units_async(asset_edits, client)` is clearer than `AssetEdit.resolve_units_batch_async(asset_edits, client)`
3. **Parallel to utilities**: Similar to how `asyncio.gather()` is a module function, not a method
4. **Import clarity**: `from resolution import resolve_units_async` is explicit

**Why not a client method?**

1. **Entity-specific**: This is specific to AssetEdit resolution, not a general task operation
2. **Business model layer**: Resolution logic belongs in business model, not transport layer
3. **Consistency**: Other business model operations are not on clients

**Why not on AssetEditHolder?**

1. **Input flexibility**: Callers may have AssetEdits from different holders
2. **No holder dependency**: Batch resolution should work on any collection
3. **Separation of concerns**: Holder manages children; resolution is a query

**Why dict return type?**

1. **O(1) lookup**: Callers can find result for specific AssetEdit without iteration
2. **Completeness**: Every input has an entry, even on failure
3. **Composability**: Easy to merge with other dicts or iterate

## Alternatives Considered

### Option A: Class Method on AssetEdit

```python
results = await AssetEdit.resolve_units_batch_async(asset_edits, client)
```

- **Pros**: Discoverable via class; follows `from_gid_async` pattern
- **Cons**: Awkward to call on class with instances as input; conflates instance and collection operations
- **Why not chosen**: Module function is more natural for collection operations

### Option B: Method on AssetEditHolder

```python
results = await holder.resolve_all_units_async(client)
```

- **Pros**: Natural home for holder's children; no need to pass collection
- **Cons**: Limits input to single holder's children; callers may have mixed collections
- **Why not chosen**: Inflexible for cross-holder collections

### Option C: Client Method

```python
results = await client.resolution.resolve_units_async(asset_edits)
```

- **Pros**: Matches client pattern; clear API home
- **Cons**: Requires new client attribute; mixes business model with transport
- **Why not chosen**: Resolution is business model logic, not transport

### Option D: Iterator/Generator

```python
async for gid, result in resolve_units_stream(asset_edits, client):
    yield (gid, result)
```

- **Pros**: Memory efficient for huge collections; streaming results
- **Cons**: Complex for simple use cases; can't random-access results
- **Why not chosen**: Over-engineered; dict is sufficient for expected collection sizes

## Consequences

### Positive

- **Clear API**: Module function with explicit inputs
- **Efficient**: Shared lookups, concurrent fetches
- **Flexible**: Works with any collection of AssetEdits
- **Composable**: Results can be filtered, merged, iterated
- **Testable**: Pure function with clear inputs/outputs

### Negative

- **Import required**: Callers must import from resolution module
- **Less discoverable**: Not visible on entity or client
- **New pattern**: Introduces module-function pattern for batch operations

### Neutral

- Sync wrappers (`resolve_units`, `resolve_offers`) follow same pattern
- Documentation provides examples for common use cases
- Batch functions are exported from `models.business` for discoverability

## Compliance

- Batch functions MUST be module-level in `resolution.py`
- Return type MUST be `dict[str, ResolutionResult[T]]`
- Every input AssetEdit MUST have an entry in result dict
- Batch functions MUST optimize shared lookups (e.g., fetch Business.units once)
- Batch functions MUST be exported from `models.business` package `__init__.py`
- Documentation MUST include usage examples for common patterns
