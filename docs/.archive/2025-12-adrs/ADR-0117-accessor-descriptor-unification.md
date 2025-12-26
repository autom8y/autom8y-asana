# ADR-0117: CustomFieldAccessor/Descriptor Unification Strategy

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-19
- **Deciders**: Architect
- **Related**: ADR-0081 (Custom Field Descriptor Pattern), ADR-0082 (Fields Auto-Generation), ADR-0054 (Cascading Custom Fields), TDD-TECH-DEBT-REMEDIATION Sprint 2

## Context

The SDK has two patterns for custom field access that appeared to create a duality requiring resolution:

### Pattern 1: CustomFieldAccessor (Infrastructure Layer)

Located in `src/autom8_asana/models/custom_field_accessor.py`, this class provides:

- Low-level field access via `.get(name)` / `.set(name, value)`
- Name-to-GID resolution with strict/non-strict modes
- Type validation at set time (text, number, enum, etc.)
- Change tracking via `_modifications` dict
- API serialization via `to_api_dict()`

Exposed via:
- `Task.custom_fields_editor()` (current public API)
- `Task.get_custom_fields()` (deprecated with warning)

### Pattern 2: CustomFieldDescriptor Family (Domain Layer)

Located in `src/autom8_asana/models/business/descriptors.py`, this hierarchy provides:

- Declarative property syntax: `company_id = TextField()`
- Type-specific subclasses: `TextField`, `EnumField`, `NumberField`, `DateField`, etc.
- Type transformation (enum dict -> str, number -> Decimal, date -> Arrow)
- Field name auto-derivation from property name
- `Fields` class auto-generation per ADR-0082

### The Perceived Problem

Initial analysis suggested these patterns create:
1. Consumer confusion about which pattern to use
2. Field name resolution scattered across modules
3. Maintenance burden from two parallel systems

### Forces at Play

1. **Zero-deprecation constraint**: External API stability is the priority
2. **Existing investment**: ADR-0081/ADR-0082 established descriptors as the pattern
3. **Clean separation**: Infrastructure vs. domain concerns should be distinct
4. **Single source of truth**: Field resolution logic should not be duplicated

## Decision

**Retain the current architecture as-is.** The two patterns are not competing systems but a properly-layered design: **Descriptors are the domain layer that wraps the accessor infrastructure layer.**

This is already **Option C (Hybrid)** - no unification refactoring required.

### Architecture Clarification

```
Domain Layer (Consumer-Facing)
+--------------------------------------------------+
|  CustomFieldDescriptor subclasses                |
|  - TextField, EnumField, NumberField, DateField  |
|  - Declarative: `company_id = TextField()`       |
|  - Type transformation (enum->str, date->Arrow)  |
|  - Auto-generated Fields class constants         |
+--------------------------------------------------+
                        |
                        | calls internally
                        v
+--------------------------------------------------+
|  CustomFieldAccessor                             |
|  - obj.get_custom_fields().get/set()            |
|  - Name-to-GID resolution                        |
|  - Type validation                               |
|  - Change tracking for SaveSession               |
|  - API serialization                             |
+--------------------------------------------------+
Infrastructure Layer (Implementation Detail)
```

### Implementation Evidence

From `descriptors.py`, every descriptor subclass delegates to the accessor:

```python
class TextField(CustomFieldDescriptor[str | None]):
    def _get_value(self, obj: Any) -> str | None:
        value = obj.get_custom_fields().get(self.field_name)  # Uses accessor
        # ... type transformation ...

    def _set_value(self, obj: Any, value: str | None) -> None:
        obj.get_custom_fields().set(self.field_name, value)  # Uses accessor
```

This pattern is consistent across all 7 descriptor subclasses.

### Guidance for Consumers

| Use Case | Pattern | Example |
|----------|---------|---------|
| Business entity field access | Descriptor property | `business.vertical` |
| Business entity field mutation | Descriptor property | `business.mrr = Decimal("1000")` |
| Generic Task field access | Accessor via method | `task.custom_fields_editor().get("Status")` |
| Cascade/inheritance metadata | CascadingFieldDef | `CascadingFieldDef(name="Vertical", ...)` |
| Raw API serialization | Accessor method | `accessor.to_api_dict()` |

## Rationale

### Why No Refactoring Needed

1. **Layering is correct**: Descriptors provide domain semantics, accessor provides infrastructure
2. **Single source of truth exists**: All field resolution goes through `CustomFieldAccessor._resolve_gid()`
3. **No API surface duplication**: Consumers use descriptors (entities) or accessor (generic tasks)
4. **Descriptor pattern is established**: ADR-0081/ADR-0082 already codified this as the approach

### Why This Satisfies Zero-Deprecation Constraint

1. **External API unchanged**: `business.vertical`, `unit.mrr` continue to work
2. **No new deprecation warnings**: Existing `get_custom_fields()` deprecation predates this constraint
3. **Internal refactoring only**: If any cleanup is done, it affects implementation, not API

### Field Resolution Centralization

Field name resolution is already centralized in `CustomFieldAccessor._resolve_gid()`:

1. Check if input is numeric GID (return as-is)
2. Check local name-to-GID index (case-insensitive)
3. Check if input matches existing GID exactly
4. Try resolver if configured
5. Apply strict mode (raise `NameNotFoundError` with suggestions) or non-strict (return as-is)

No changes required.

## Alternatives Considered

### Option A: Wrap (Make Accessor Private)

- **Description**: Rename `CustomFieldAccessor` to `_CustomFieldAccessor`, expose only via descriptors
- **Pros**: Cleaner API surface, single entry point
- **Cons**: Breaking change for code using `custom_fields_editor()`, loses generic Task support
- **Why not chosen**: Violates zero-deprecation constraint; generic Tasks need accessor

### Option B: Replace (Deprecate Accessor)

- **Description**: Remove accessor entirely, all access through descriptors
- **Pros**: Single pattern
- **Cons**: Descriptors require class definition; generic Tasks cannot use them
- **Why not chosen**: Fundamentally incompatible with generic Task access pattern

### Option C: Hybrid (Clarify Existing Design)

- **Description**: Keep both patterns, document as layered architecture
- **Pros**: No breaking changes, design is already correct
- **Cons**: Requires documentation clarity
- **Why chosen**: The architecture is already correct; only clarification needed

## Consequences

### Positive

1. **Zero breaking changes**: External API completely stable
2. **No refactoring risk**: No code changes means no regression risk
3. **Clear guidance**: This ADR documents the intended usage patterns
4. **Design validation**: Analysis confirms ADR-0081/ADR-0082 were correctly designed

### Negative

1. **Two patterns remain**: Developers must understand when to use which
   - *Mitigation*: Usage table in this ADR provides clear guidance
2. **Documentation burden**: Must keep this ADR visible
   - *Mitigation*: Link from `autom8-asana` skill and GLOSSARY.md

### Neutral

1. **No Sprint 2 implementation work**: Discovery/Analysis complete; no code changes
2. **Test coverage unchanged**: Existing tests validate both patterns work

## Implementation Notes for Sessions 4-6

### Session 4 (Discovery): COMPLETE

This ADR serves as the discovery artifact. Key findings:
- Architecture is correct as-designed
- No unification refactoring required
- Zero-deprecation constraint is satisfied

### Session 5-6 (Implementation): MINIMAL

If any work is desired:

1. **Documentation updates** (optional):
   - Add usage guidance to `autom8-asana` skill
   - Update GLOSSARY.md with pattern definitions

2. **Test verification** (optional):
   - Audit test coverage for both patterns
   - Ensure descriptor-to-accessor delegation is tested

3. **No code changes required** for unification

## Compliance

### Quality Gate Checklist

- [x] Decision is clear and justified
- [x] Zero-deprecation constraint honored (no API changes)
- [x] Field resolution centralization path defined (already centralized)
- [x] All three options evaluated with tradeoffs
- [x] Next session has clear direction (minimal/no implementation)

### Code Review Checklist (for any future changes)

- [ ] Descriptors always delegate to accessor for field access
- [ ] Accessor remains the single source for name-to-GID resolution
- [ ] No new public API on accessor (use descriptors for new fields)
- [ ] Type transformations happen in descriptors, not accessor
