# ADR-003: Resolution Model -- Lazy Pull with Strategy Chain

**Status**: Accepted
**Date**: 2026-02-11
**Deciders**: Moonshot Architect (delegated authority from stakeholder)

## Context

Entity resolution requires choosing between:

1. **Eager push**: Pre-fetch all potentially needed entities at the start of a workflow
2. **Lazy pull**: Fetch entities on demand when first accessed
3. **Hybrid**: Pre-fetch core entities, lazy-fetch the rest

The stakeholder confirmed dependencies are SPARSE (0-1 per process) and that hierarchy traversal is more important than dependency traversal. Production data shows Business has 7 holder branches; workflows typically need 2-3 of them.

Eager hydration of a full Business tree costs 15-25 API calls (Business + 7 holders + children for each). Most workflows only need Business + 1-2 specific holders.

## Decision

**Lazy pull resolution using an ordered strategy chain, with session caching to amortize repeated access.**

Resolution follows an ordered fallback chain:

```
1. Session cache lookup (GID known) -- 0 API calls
2. Dependency shortcut (deps -> target) -- 2 API calls
3. Hierarchy traversal (up to Business -> down to holder -> down to entity) -- 3-5 API calls
4. Custom field predicate (field match against sibling entities) -- variable
5. FAILED with diagnostics
```

Budget: maximum 8 API calls per single resolution. Fail after budget exhausted.

### Read-First, Write Layer On Top

The resolution system is read-only. Write operations (entity creation, field updates, dependency wiring) are handled by the lifecycle engine, which uses resolution to obtain inputs but never mutates through the resolution system.

This matches the stakeholder's confirmed direction: "read-first, write layer on top."

### Strategy Chain Architecture

```python
class ResolutionStrategy(ABC):
    @abstractmethod
    async def resolve_async(
        self,
        target_type: type[T],
        context: ResolutionContext,
        *,
        from_entity: BusinessEntity,
        budget: ApiBudget,
    ) -> ResolutionResult[T] | None:
        """Return resolved entity, or None to try next strategy."""
```

Strategies are composed into a chain per resolution request. Each strategy either resolves the entity or returns None to pass to the next strategy. The chain stops at the first successful resolution.

## Alternatives Considered

### Eager Push (Rejected)

```python
# Pre-fetch everything
ctx = await ResolutionContext.preload_async(client, business_gid)
# All entities available immediately
phone = ctx.business.office_phone
```

Wastes API calls on unused entities. Business has 7 holder branches; ConversationAuditWorkflow only needs Business (for office_phone) -- a 7x over-fetch. For lifecycle workflows that need Unit + ProcessHolder, the over-fetch is smaller but still includes 5 unnecessary branches.

### Static Configuration (Rejected)

Pre-declare which entities each workflow needs:

```python
class ConversationAuditWorkflow:
    REQUIRED_ENTITIES = ["Business"]
```

This creates coupling between workflow declaration and resolution system. It also cannot handle dynamic resolution (e.g., "resolve the Contact where position=Owner" depends on runtime data).

## Consequences

### Positive

- API calls are proportional to actual data needs, not potential data needs
- Strategy chain is extensible -- new strategies (e.g., cache-based resolution) can be inserted without changing callers
- Session cache prevents re-fetching across multiple resolution requests in the same execution
- Budget enforcement prevents unbounded API chains (the legacy anti-pattern)

### Negative

- First access to an entity incurs latency (not pre-fetched)
- Strategy chain ordering matters -- incorrect ordering could cause unnecessary API calls
- Budget exhaustion is a failure mode that must be handled gracefully

### Risks

- If workflows consistently need 4+ entity types, lazy pull could be slower than selective eager. Monitor resolution patterns after deployment; consider adding a `preload_async(entity_types=[...])` method if patterns stabilize.
