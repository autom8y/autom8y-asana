# ADR-005: Selective Hydration -- Work Around from_gid_async

**Status**: Accepted
**Date**: 2026-02-11
**Deciders**: Moonshot Architect (delegated authority from stakeholder)

## Context

`Business.from_gid_async(hydrate=True)` fetches the full hierarchy: Business + 7 holders + all children + Unit nested holders. This is 15-25 API calls. Most workflows need only 1-2 specific branches.

The stakeholder asked whether to extend `from_gid_async` with selective hydration or work around it.

`from_gid_async` is a production-critical method used across the codebase. Changing its signature or behavior risks regression across 8500+ tests.

## Decision

**Work around `from_gid_async` by building selective hydration into ResolutionContext, not the entity model layer.**

ResolutionContext loads entities incrementally:

```python
class ResolutionContext:
    async def business_async(self) -> Business:
        """Load Business without hydration, cache it."""
        if "business" not in self._session_cache:
            # Fetch Business task only (1 API call, hydrate=False)
            business = await Business.from_gid_async(
                self._client, self._business_gid, hydrate=False
            )
            self._session_cache[business.gid] = business
        return self._session_cache[self._business_gid]

    async def contact_holder_async(self) -> ContactHolder:
        """Load ContactHolder on demand, populating only that branch."""
        business = await self.business_async()
        if business.contact_holder is None:
            # Fetch only ContactHolder subtask + its children
            await self._hydrate_branch_async(business, "contact_holder")
        return business.contact_holder
```

The `_hydrate_branch_async` method fetches a single holder subtask and its children (2-3 API calls) instead of the full hierarchy (15-25 calls).

### Branch Hydration

```python
async def _hydrate_branch_async(
    self,
    business: Business,
    holder_key: str,
) -> None:
    """Hydrate a single holder branch on a Business."""
    # 1. If holders not yet fetched, fetch Business subtasks (1 call)
    if not self._holders_fetched:
        holder_tasks = await self._client.tasks.subtasks_async(
            business.gid, include_detection_fields=True
        ).collect()
        business._populate_holders(holder_tasks)
        self._holders_fetched = True

    # 2. Fetch children for the specific holder (1 call)
    holder = getattr(business, f"_{holder_key}", None)
    if holder is not None:
        await business._fetch_holder_children_async(
            self._client, holder, holder.CHILDREN_ATTR
        )
```

## Alternatives Considered

### Extend from_gid_async with Branch Selection (Rejected)

```python
business = await Business.from_gid_async(
    client, gid, hydrate=["contact_holder", "unit_holder"]
)
```

This changes the public API of a production-critical method. Every caller of `from_gid_async` would need to be audited. The `_fetch_holders_async` method would need branch filtering logic. Risk is high for the 8500+ test suite.

### Pre-Fetch Specific Entity Types (Rejected)

```python
ctx = await ResolutionContext.preload_async(
    client, business_gid, entities=[Business, ContactHolder, Contact]
)
```

This is the eager push model rejected in ADR-003. It also requires callers to declare their data needs upfront, which is fragile for evolving workflows.

## Consequences

### Positive

- `Business.from_gid_async()` is UNCHANGED -- zero regression risk
- Branch hydration is 2-3 API calls instead of 15-25
- Session caching ensures branch hydration happens at most once per execution
- Entity model layer remains clean; resolution concerns stay in resolution layer

### Negative

- ResolutionContext must understand Business holder structure (holder_key -> holder attribute mapping)
- First holder access requires fetching Business subtasks (1 API call for holder identification)
- Branch hydration methods are duplicating some logic from `_fetch_holders_async`

### Risks

- If a workflow needs 5+ branches, lazy branch hydration may be slower than full hydration. Monitor and add a `hydrate_all_async()` method if needed.
