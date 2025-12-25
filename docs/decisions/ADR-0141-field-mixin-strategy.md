# ADR-0141: Field Mixin Strategy for Sprint 1 Pattern Completion

## Metadata
- **Status**: Proposed
- **Author**: Architect (Claude)
- **Date**: 2025-12-19
- **Deciders**: SDK Team, Platform Team
- **Related**: PRD-SPRINT-1, TDD-SPRINT-1-PATTERN-COMPLETION, ADR-0081 (Custom Field Descriptors), ADR-0082 (Fields Class Auto-Generation)

## Context

Sprint 1 requires consolidating 17 duplicate field descriptor declarations across Business, Unit, Offer, and Process entities. The PRD identifies 5 fields that appear in multiple entities:

| Field | Type | Occurrences |
|-------|------|-------------|
| `vertical` | EnumField | Business, Unit, Offer, Process (4) |
| `rep` | PeopleField | Business, Unit, Offer, Process (4) |
| `booking_type` | EnumField | Business, Unit, Process (3) |
| `mrr` | NumberField | Unit, Offer, Process (3) |
| `weekly_ad_spend` | NumberField | Unit, Offer, Process (3) |

Additionally, the PRD requires decisions on:
1. **Mixin granularity**: How to group fields into mixins
2. **CascadingFieldDef handling**: Whether mixins include cascading metadata
3. **`to_business_async` extraction**: Where to place extracted traversal logic
4. **Mixin file location**: Where to define mixins

These decisions must account for:
- **Pydantic v2 compatibility**: Mixins must work with Pydantic model inheritance
- **Descriptor MRO resolution**: Python MRO determines which descriptor wins
- **Fields class auto-generation**: Per ADR-0082, descriptors register for Fields generation
- **Circular import avoidance**: Mixin file cannot import entity classes

## Decision

### Decision 1: Coarse-Grained Mixins (2 mixins)

We will create **two coarse-grained mixins** grouping fields by semantic category:

```python
class SharedCascadingFieldsMixin:
    """Fields that cascade through the entity hierarchy."""
    vertical = EnumField()
    rep = PeopleField()

class FinancialFieldsMixin:
    """Financial tracking fields."""
    booking_type = EnumField()
    mrr = NumberField(field_name="MRR")
    weekly_ad_spend = NumberField()
```

### Decision 2: Descriptors Only (No CascadingFieldDef)

Mixins will provide **descriptor definitions only**. CascadingFieldDef metadata will remain on individual entity classes because:
- Cascading target types vary per entity (Unit cascades to Offer, Business cascades to Unit)
- `allow_override` flags differ per entity-field combination
- Cascading is behavior; descriptors are data access

### Decision 3: UpwardTraversalMixin for `to_business_async`

The common `to_business_async` traversal logic will be extracted to a new `UpwardTraversalMixin` with a `_update_refs_after_hydration(business)` hook for entity-specific reference updates.

### Decision 4: New `mixins.py` File

Mixins will be defined in a new `src/autom8_asana/models/business/mixins.py` file to:
- Avoid circular imports (mixins import only from `descriptors.py`)
- Maintain clear separation of concerns
- Enable easy discovery and modification

### Decision 5: `identify_holder()` to detection.py

The extracted `_identify_holder` logic will become a utility function `identify_holder()` in `detection.py`, parameterized with optional `filter_keys` to handle Unit's restricted set.

## Rationale

### Why Coarse-Grained Over Fine-Grained

**Considered Alternative**: 5 single-field mixins (VerticalFieldMixin, RepFieldMixin, etc.)

**Trade-off Analysis**:

| Factor | Coarse (2) | Fine (5) |
|--------|------------|----------|
| MRO complexity | Simple | Complex (5 bases per entity) |
| Reusability | Lower (some entities don't use all fields) | Higher (pick exactly what you need) |
| Maintenance | Edit 1 file for grouped changes | Edit specific mixin per field |
| IDE autocomplete | Clear field grouping | Fragmented across mixins |
| Selective inclusion | Entity ignores unused descriptors | Explicit per-mixin inheritance |

**Why coarse wins**:
1. **Simplicity**: 2 mixins vs 5 reduces cognitive load and MRO depth
2. **Unused fields are harmless**: If Business inherits `mrr` from FinancialFieldsMixin but doesn't have that Asana field, the descriptor returns `None` - no error, no side effect
3. **Semantic cohesion**: "Cascading fields" and "Financial fields" are meaningful categories that aid understanding
4. **Room for refinement**: If finer granularity is needed later, coarse mixins can be decomposed without breaking changes

### Why Descriptors-Only (No Cascading in Mixins)

**Considered Alternative**: Include CascadingFieldDef metadata in mixins:

```python
class SharedCascadingFieldsMixin:
    vertical = EnumField()
    rep = PeopleField()

    class CascadingFields:
        VERTICAL = CascadingFieldDef(name="Vertical", target_types={"Offer", "Process"})
        REP = CascadingFieldDef(name="Rep", target_types={"Offer", "Process"})
```

**Why rejected**:
1. **Target types vary**: Unit cascades to Offer/Process, Business cascades to Unit - different targets
2. **Override behavior varies**: Some fields have `allow_override=True`, others don't
3. **Violates single responsibility**: Mixins provide data access; cascading is workflow behavior
4. **Complexity explosion**: Would need per-entity cascade configuration that defeats mixin purpose

**Consequence**: CascadingFields inner classes remain on entities. Duplication of the 2-line CascadingFieldDef declarations is acceptable given the semantic variation.

### Why UpwardTraversalMixin Over Utility Function

**Considered Alternatives**:
1. **Module-level utility** in hydration.py
2. **Base class method** on BusinessEntity

**Why mixin wins**:
1. **Opt-in inheritance**: Not all entities need `to_business_async` (Business doesn't)
2. **Hook pattern**: `_update_refs_after_hydration(business)` provides clean extension point
3. **Keeps BusinessEntity focused**: Base class shouldn't know about specific traversal patterns
4. **Type safety**: Mixin can be typed for entities with specific ref patterns

### Why detection.py for `identify_holder()`

**Considered Alternatives**:
1. **HolderMixin method**: Add to base holder mixin
2. **New `holder_utils.py`**: Dedicated utilities module

**Why detection.py wins**:
1. **Natural home**: Already contains `detect_entity_type()`, `get_holder_attr()`
2. **Import convenience**: Entities already import from detection.py
3. **Conceptual fit**: Holder identification IS type detection
4. **Avoids new module**: One less file to maintain

### Why New `mixins.py` Over Extending `base.py`

**Considered Alternative**: Add mixins to existing `base.py`

**Why rejected**:
1. **Separation of concerns**: `base.py` is for base classes (HolderMixin, BusinessEntity), not field composition
2. **Circular import risk**: `base.py` already imports from descriptors.py; adding more there increases risk
3. **Discoverability**: Dedicated `mixins.py` clearly communicates "field composition lives here"
4. **File size**: `base.py` is 400+ lines; adding mixins would push it larger

## Alternatives Considered

### Alternative 1: Fine-Grained Mixins (5 single-field)

```python
class VerticalFieldMixin:
    vertical = EnumField()

class RepFieldMixin:
    rep = PeopleField()

class BookingTypeFieldMixin:
    booking_type = EnumField()

class MRRFieldMixin:
    mrr = NumberField(field_name="MRR")

class WeeklyAdSpendFieldMixin:
    weekly_ad_spend = NumberField()

# Usage
class Unit(BusinessEntity, VerticalFieldMixin, RepFieldMixin, BookingTypeFieldMixin, MRRFieldMixin, WeeklyAdSpendFieldMixin):
    pass
```

- **Pros**: Maximum granularity, entities declare exactly what they use
- **Cons**: 5-way multiple inheritance, complex MRO, harder to read
- **Why not chosen**: Complexity not justified; unused descriptors cause no harm

### Alternative 2: Hybrid Mixins (3 mixins)

```python
class VerticalRepMixin:  # Always together
    vertical = EnumField()
    rep = PeopleField()

class BookingTypeMixin:  # Standalone
    booking_type = EnumField()

class MRRSpendMixin:  # Always together
    mrr = NumberField(field_name="MRR")
    weekly_ad_spend = NumberField()
```

- **Pros**: Tighter grouping based on co-occurrence analysis
- **Cons**: 3 is neither simple (2) nor granular (5); awkward middle ground
- **Why not chosen**: No clear advantage over 2 coarse mixins

### Alternative 3: Composition Over Inheritance

```python
class FieldSet:
    def __init__(self, *descriptors):
        self.descriptors = descriptors

    def apply_to(self, cls):
        for desc in self.descriptors:
            setattr(cls, desc.name, desc)

SHARED_CASCADING_FIELDS = FieldSet(
    EnumField(name="vertical"),
    PeopleField(name="rep"),
)

# Usage (in __init_subclass__)
SHARED_CASCADING_FIELDS.apply_to(Unit)
```

- **Pros**: Avoids MI entirely, explicit application
- **Cons**: Breaks descriptor `__set_name__` flow, incompatible with Fields auto-generation (ADR-0082)
- **Why not chosen**: Incompatible with existing descriptor infrastructure

### Alternative 4: Entity Inherits from Mixin First

```python
# MRO: SharedCascadingFieldsMixin -> BusinessEntity -> ...
class Unit(SharedCascadingFieldsMixin, BusinessEntity, FinancialFieldsMixin):
    pass
```

- **Pros**: Mixin fields take precedence over any BusinessEntity defaults
- **Cons**: Violates Python convention (base class first), Pydantic may misbehave
- **Why not chosen**: Standard MRO with BusinessEntity first is safer

## Consequences

### Positive

1. **12 fewer field declarations**: 17 reduced to 5 mixin definitions
2. **Centralized field definitions**: Changes to `vertical` field made once in mixin
3. **Clear semantic grouping**: "Cascading fields" and "Financial fields" aid understanding
4. **Pydantic-compatible**: Works with existing model_config and descriptor handling
5. **Fields class auto-generation works**: ADR-0082 infrastructure handles mixin descriptors
6. **No API changes**: External usage identical (`business.vertical`, `unit.mrr`, etc.)

### Negative

1. **Unused fields on some entities**: Business has `mrr` descriptor but field doesn't exist in Asana
   - Mitigation: Returns `None`, no error - acceptable
2. **MRO complexity increases slightly**: 2 additional bases per entity
   - Mitigation: Standard Python MI; well-understood
3. **CascadingFieldDef duplication remains**: Each entity still declares its cascade rules
   - Mitigation: ~2 lines per field; semantic variation justifies duplication

### Neutral

1. **New file to maintain**: `mixins.py` adds to codebase
2. **Descriptor lookup slightly longer**: MRO traversal includes mixin classes
3. **IDE may show "inherited from" in autocomplete**: Minor UX change for developers

## Compliance

How do we ensure this decision is followed?

1. **Code review checklist**: Any new shared field should be added to appropriate mixin
2. **Import convention**: Entities import from `mixins.py`, not copy descriptors
3. **CI lint rule** (future): Flag duplicate field descriptors across entity files
4. **Documentation**: TDD-SPRINT-1 references this ADR for implementation guidance

## Appendix: Mixin Application Matrix

| Entity | SharedCascadingFieldsMixin | FinancialFieldsMixin | Fields Used | Fields Ignored |
|--------|---------------------------|---------------------|-------------|----------------|
| Business | YES | YES | vertical, rep, booking_type | mrr, weekly_ad_spend |
| Unit | YES | YES | ALL | - |
| Offer | YES | YES | vertical, rep, mrr, weekly_ad_spend | booking_type |
| Process | YES | YES | ALL | - |

## Appendix: Example MRO

```python
class Unit(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin):
    pass

# MRO:
# Unit
# -> BusinessEntity
#    -> Task
#       -> AsanaResource
#          -> BaseModel (Pydantic)
# -> SharedCascadingFieldsMixin
# -> FinancialFieldsMixin
# -> object
```

Descriptor resolution order:
1. Unit (entity-specific overrides)
2. BusinessEntity (no field descriptors)
3. SharedCascadingFieldsMixin (`vertical`, `rep`)
4. FinancialFieldsMixin (`booking_type`, `mrr`, `weekly_ad_spend`)
