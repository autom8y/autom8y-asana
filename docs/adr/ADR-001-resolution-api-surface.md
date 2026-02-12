# ADR-001: Resolution API Surface -- Entity-Native with Composable Low-Level

**Status**: Accepted
**Date**: 2026-02-11
**Deciders**: Moonshot Architect (delegated authority from stakeholder)

## Context

The Workflow Resolution Platform needs an API surface for accessing entity data during workflow execution. The primary smell is `ConversationAuditWorkflow._resolve_office_phone()`, which manually parses custom fields by string name (`cf_dict.get("name") == "Office Phone"`) despite `Business.office_phone = TextField(cascading=True)` already existing.

Three API styles were considered:

1. **Entity-native**: `ctx.business.office_phone` -- uses existing descriptor system directly
2. **Explicit resolve**: `ctx.resolve("business", "office_phone")` -- string-based indirection
3. **String path**: `ctx.resolve_path("business.office_phone")` -- dynamic dotted path resolution

The stakeholder expressed a preference for entity-native and confirmed both composable low-level and declarative high-level APIs are required.

## Decision

**Use entity-native access as the primary API, backed by a composable ResolutionContext that manages entity loading and session caching.**

The API is layered:

### Layer 1: ResolutionContext (Low-Level, Composable)

```python
class ResolutionContext:
    async def resolve_entity_async(
        self,
        entity_type: type[T],
        *,
        from_entity: BusinessEntity,
        predicate: SelectionPredicate | None = None,
    ) -> ResolutionResult[T]: ...
```

Callers use this to resolve any entity from any starting point with full control over selection predicates.

### Layer 2: Entity-Native Access (High-Level, Declarative)

```python
async with ResolutionContext(client, trigger_task=process) as ctx:
    business = await ctx.business_async()       # cached after first call
    phone = business.office_phone               # descriptor access, zero API calls
    unit = await ctx.unit_async()
    products = unit.products                    # MultiEnumField descriptor
    contact = await ctx.contact_async(
        predicate=FieldPredicate("position", "Owner")
    )
```

The high-level layer is sugar over Layer 1, providing typed convenience methods that return fully-hydrated entities.

## Alternatives Considered

### Explicit Resolve (Rejected)

```python
phone = await ctx.resolve("business", "office_phone")
```

Loses type safety. Field names become strings again -- the same anti-pattern we are eliminating. IDE autocomplete does not work. Descriptors are bypassed entirely.

### String Path (Rejected)

```python
phone = await ctx.resolve_path("business.office_phone")
```

Dynamic resolution is fragile, untestable at compile time, and creates a parallel access system that diverges from the entity model. The legacy codebase uses `"offer.office_phone"` string defaults and it is a documented anti-pattern.

## Consequences

### Positive

- Entity descriptors (TextField, EnumField, etc.) work unchanged -- no parallel system
- Type safety is preserved end-to-end: `ctx.business_async()` returns `Business`, `business.office_phone` returns `str | None`
- Session caching is invisible to callers; second call to `ctx.business_async()` returns cached instance
- Existing 8500+ tests continue to pass because entity model layer is unchanged
- IDE autocomplete works for all field access

### Negative

- Callers must await entity access separately from field access (two statements instead of one)
- Adding new convenience methods to ResolutionContext requires code changes (not just config)

### Risks

- If entity hydration cost is too high, selective hydration may be needed (see ADR-005)
