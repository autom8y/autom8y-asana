# TDD: Sprint 1 - Pattern Completion and DRY Consolidation

## Metadata
- **TDD ID**: TDD-SPRINT-1
- **Status**: Draft
- **Author**: Architect (Claude)
- **Created**: 2025-12-19
- **Last Updated**: 2025-12-19
- **PRD Reference**: [PRD-SPRINT-1-PATTERN-COMPLETION](../planning/sprints/PRD-SPRINT-1-PATTERN-COMPLETION.md)
- **Related TDDs**: TDD-PATTERNS-C (HolderFactory), TDD-PATTERNS-A (Custom Field Descriptors)
- **Related ADRs**: [ADR-0119-field-mixin-strategy](../decisions/ADR-0119-field-mixin-strategy.md)

## Overview

This TDD defines the technical approach for Sprint 1 pattern completion: migrating 5 remaining holders to HolderFactory, creating field mixins for 5 shared fields, extracting duplicated methods, and achieving descriptor coverage for Location.py and Hours.py. The design prioritizes backward compatibility, test preservation, and phased independent delivery.

## Requirements Summary

From [PRD-SPRINT-1](../planning/sprints/PRD-SPRINT-1-PATTERN-COMPLETION.md):

| Phase | Requirements | Priority |
|-------|--------------|----------|
| Phase 0 | FR-001 to FR-007: HolderFactory migration + Descriptor coverage | Must/Should |
| Phase 1 | FR-008 to FR-013: Field mixins creation and application | Must |
| Phase 2 | FR-014 to FR-016: Method extraction (`_identify_holder`, `to_business_async`) | Must/Should/Could |

**Success Metrics**:
- -258 lines in holder classes (62% reduction)
- 17 to 5 field declarations (12 eliminated)
- 2 to 0 entities using legacy helper methods
- 100% existing tests pass

## System Context

This sprint operates entirely within the Business Model layer (`src/autom8_asana/models/business/`). No changes to transport, cache, or persistence layers.

```
                        ┌─────────────────────────────────┐
                        │     Business Model Layer        │
                        │                                 │
  ┌──────────────┐      │  ┌───────────┐  ┌───────────┐  │
  │  Persistence │◄────►│  │ Entities  │  │  Holders  │  │
  │  (SaveSession)│      │  │(Business, │◄─┤(Contact,  │  │
  └──────────────┘      │  │Unit, etc.)│  │ Unit, etc)│  │
                        │  └─────┬─────┘  └─────┬─────┘  │
                        │        │              │        │
                        │        ▼              ▼        │
                        │  ┌─────────────────────────┐   │
                        │  │  HolderFactory (base)   │   │
                        │  │  CustomFieldDescriptor  │   │
                        │  │  Field Mixins (NEW)     │   │
                        │  └─────────────────────────┘   │
                        └─────────────────────────────────┘
```

**Affected Files**:
- `holder_factory.py` - No changes (pattern already complete)
- `base.py` - No changes
- `descriptors.py` - No changes (all descriptors exist)
- `mixins.py` - **NEW FILE** (field mixins)
- `contact.py`, `unit.py`, `offer.py`, `process.py`, `location.py`, `hours.py` - Modifications
- `business.py` - Modifications (mixin application)
- `detection.py` - Modifications (method extraction target)

## Design

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Business Model Components                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐      ┌─────────────────────────────────────┐   │
│  │  HolderFactory  │      │          Field Mixins (NEW)          │   │
│  │  (existing)     │      │                                      │   │
│  │                 │      │  SharedCascadingFieldsMixin          │   │
│  │  - __init_     │      │    - vertical: EnumField             │   │
│  │    subclass__  │      │    - rep: PeopleField                │   │
│  │  - _populate_  │      │                                      │   │
│  │    children    │      │  FinancialFieldsMixin                │   │
│  └────────┬───────┘      │    - booking_type: EnumField         │   │
│           │               │    - mrr: NumberField                │   │
│  Extends  │               │    - weekly_ad_spend: NumberField    │   │
│           ▼               └──────────────────┬───────────────────┘   │
│  ┌─────────────────┐                         │                       │
│  │ ContactHolder   │                         │ Inherited by          │
│  │ UnitHolder      │                         ▼                       │
│  │ OfferHolder     │      ┌─────────────────────────────────────┐   │
│  │ ProcessHolder   │      │        Entity Classes               │   │
│  │ LocationHolder  │      │                                      │   │
│  │ (migrated)      │      │  Business(SharedCascading,Financial) │   │
│  └─────────────────┘      │  Unit(SharedCascading, Financial)    │   │
│                           │  Offer(SharedCascading, Financial*)   │   │
│                           │  Process(SharedCascading, Financial)  │   │
│                           └─────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   CustomFieldDescriptor                      │    │
│  │                   (existing - used by mixins)                │    │
│  │                                                              │    │
│  │  TextField, EnumField, NumberField, PeopleField, etc.        │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘

* Offer uses mrr, weekly_ad_spend from FinancialFieldsMixin but NOT booking_type
```

| Component | Responsibility | Location |
|-----------|----------------|----------|
| HolderFactory | Auto-configures holder classes via `__init_subclass__` | `holder_factory.py` (existing) |
| SharedCascadingFieldsMixin | Provides `vertical`, `rep` descriptors | `mixins.py` (new) |
| FinancialFieldsMixin | Provides `booking_type`, `mrr`, `weekly_ad_spend` | `mixins.py` (new) |
| CustomFieldDescriptor | Base descriptor pattern for all field access | `descriptors.py` (existing) |
| `identify_holder()` | Utility function for holder identification | `detection.py` (extracted) |

### Data Model

No data model changes. This is a code organization refactoring. Asana schema remains unchanged.

**Field Mapping** (what mixins provide):

| Mixin | Field | Descriptor | Asana Field Name |
|-------|-------|------------|------------------|
| SharedCascadingFieldsMixin | vertical | EnumField | "Vertical" |
| SharedCascadingFieldsMixin | rep | PeopleField | "Rep" |
| FinancialFieldsMixin | booking_type | EnumField | "Booking Type" |
| FinancialFieldsMixin | mrr | NumberField | "MRR" |
| FinancialFieldsMixin | weekly_ad_spend | NumberField | "Weekly Ad Spend" |

### API Contracts

No public API changes. All existing property accessors remain unchanged:

```python
# Before and after - identical usage
business.vertical      # str | None
business.rep           # list[dict]
unit.mrr              # Decimal | None
unit.weekly_ad_spend  # Decimal | None
offer.vertical        # str | None
```

### Data Flow

**HolderFactory Migration Flow** (unchanged from existing pattern):

```
1. Class Definition
   class ContactHolder(HolderFactory, child_type="Contact", parent_ref="_contact_holder"):
       pass
       │
       ▼
2. __init_subclass__ hook fires
   - Sets CHILD_TYPE, PARENT_REF_NAME, CHILDREN_ATTR
   - Generates children property
   - Registers with ProjectTypeRegistry
       │
       ▼
3. Runtime Usage
   holder._populate_children(subtasks)
   - Dynamically imports child class
   - Creates typed children with parent refs
```

**Mixin Field Resolution Flow**:

```
1. Class Definition with Mixin
   class Business(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin):
       │
       ▼
2. Descriptor Registration
   - Mixin descriptors added to class namespace
   - __set_name__ derives field names
   - _pending_fields populated for Fields class generation
       │
       ▼
3. __init_subclass__ hook
   - Generates Fields class from _pending_fields
   - Combines mixin fields with entity-specific fields
       │
       ▼
4. Runtime Property Access
   business.vertical
   - EnumField.__get__ invoked
   - Calls get_custom_fields().get("Vertical")
   - Returns extracted name from enum dict
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Mixin granularity | 2 coarse-grained mixins | Simpler MRO, sufficient flexibility with selective field exclusion | ADR-0119 |
| Mixin inheritance | Entity inherits from mixins (MI) | Pydantic-compatible, Fields class auto-generation works | ADR-0119 |
| CascadingFieldDef in mixins | No - kept on entities | Cascading behavior varies per entity; mixins provide descriptors only | ADR-0119 |
| Method extraction location | `identify_holder()` to detection.py | Natural home; already contains detection utilities | ADR-0119 |
| Mixin file location | New `mixins.py` | Clear separation; avoids circular imports | ADR-0119 |
| `to_business_async` extraction | Base mixin with hooks | Common traversal logic shared; entity-specific updates as hooks | ADR-0119 |

## Complexity Assessment

**Complexity Level**: Module

**Justification**:
- Refactoring only - no new features
- Scope limited to business model layer
- No external API changes
- All patterns already exist (HolderFactory, descriptors)
- Independent phases can merge separately

**Why not Script**: Multiple files affected, requires careful MRO management.
**Why not Service**: No API contracts, no deployment considerations, single-layer change.

## Implementation Plan

### Phase 0: Foundation (HolderFactory + Descriptors)

**FR-001 to FR-005: HolderFactory Migration**

| Holder | Migration Type | Override Needed | Estimated Lines |
|--------|----------------|-----------------|-----------------|
| ContactHolder | Simple | None | 15 |
| UnitHolder | Simple | None | 15 |
| OfferHolder | Override | `_populate_children` for `_unit` propagation | 35 |
| ProcessHolder | Override | `_populate_children` for `_unit` propagation | 35 |
| LocationHolder | Override | `_populate_children` for Hours sibling split | 60 |

**Migration Pattern - Simple**:
```python
# Before (55 lines)
class ContactHolder(Task, HolderMixin[Contact]):
    CHILD_TYPE: ClassVar[type[Contact]] = Contact
    PARENT_REF_NAME: ClassVar[str] = "_contact_holder"
    CHILDREN_ATTR: ClassVar[str] = "_contacts"
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1201500116978260"

    _contacts: list[Contact] = PrivateAttr(default_factory=list)
    _business: Business | None = PrivateAttr(default=None)

    @property
    def contacts(self) -> list[Contact]:
        return self._contacts

    @property
    def business(self) -> Business | None:
        return self._business

# After (12 lines)
class ContactHolder(
    HolderFactory,
    child_type="Contact",
    parent_ref="_contact_holder",
    children_attr="_contacts",
    semantic_alias="contacts",
):
    """Holder for Contact children."""
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1201500116978260"
```

**Migration Pattern - Override** (OfferHolder/ProcessHolder):
```python
class OfferHolder(
    HolderFactory,
    child_type="Offer",
    parent_ref="_offer_holder",
    children_attr="_offers",
    semantic_alias="offers",
):
    """Holder for Offer children."""
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1202500116978261"

    # Intermediate reference for propagation
    _unit: Unit | None = PrivateAttr(default=None)

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Override to propagate _unit reference to children."""
        super()._populate_children(subtasks)
        # Set intermediate ref on all children
        for offer in self.children:
            offer._unit = self._unit
```

**FR-006 to FR-007: Descriptor Coverage**

| File | Current Helper | Replacement Descriptor | Properties Affected |
|------|----------------|------------------------|---------------------|
| location.py | `_get_text_field` | TextField | street_name, city, state, zip_code, suite, neighborhood, office_location |
| location.py | `_get_enum_field` | EnumField | country, time_zone |
| location.py | `_get_number_field_int` | IntField | street_number, min_radius, max_radius |
| hours.py | `_get_multi_enum_field` | MultiEnumField | monday, tuesday, wednesday, thursday, friday, saturday |

**Location.py Migration**:
```python
# Before
def _get_text_field(self, field_name: str) -> str | None:
    value = self.get_custom_fields().get(field_name)
    if value is None or isinstance(value, str):
        return value
    return str(value)

@property
def street_name(self) -> str | None:
    return self._get_text_field(self.Fields.STREET_NAME)

# After
street_name = TextField()  # Auto-derives "Street Name" from snake_case
```

**Hours.py Migration**:
```python
# Before
def _get_multi_enum_field(self, field_name: str) -> list[str]:
    # 19 lines of extraction logic
    ...

@property
def monday(self) -> list[str]:
    return self._get_multi_enum_field(self.Fields.MONDAY)

# After
monday = MultiEnumField()  # Auto-derives "Monday" from snake_case
```

### Phase 1: Field Mixins

**FR-008 to FR-009: Mixin Creation**

Create `src/autom8_asana/models/business/mixins.py`:

```python
"""Field mixins for shared custom field descriptors.

Per ADR-0119: Coarse-grained mixins for DRY field consolidation.
Per TDD-SPRINT-1: SharedCascadingFieldsMixin and FinancialFieldsMixin.

Mixins provide descriptor-only definitions. CascadingFieldDef metadata
remains on entity classes since cascading behavior varies per entity.
"""

from __future__ import annotations

from autom8_asana.models.business.descriptors import (
    EnumField,
    NumberField,
    PeopleField,
)


class SharedCascadingFieldsMixin:
    """Fields that commonly cascade through the entity hierarchy.

    Per FR-008: Provides vertical and rep descriptors.

    Used by: Business, Unit, Offer, Process

    Note: Cascading behavior (CascadingFieldDef) is NOT defined here.
    Each entity defines its own cascading rules since target types
    and allow_override vary.
    """

    vertical = EnumField()
    rep = PeopleField()


class FinancialFieldsMixin:
    """Financial tracking fields.

    Per FR-009: Provides booking_type, mrr, weekly_ad_spend descriptors.

    Used by:
    - Business: booking_type only
    - Unit: all three
    - Offer: mrr, weekly_ad_spend only
    - Process: all three

    Note: Entities that don't need all fields can either:
    1. Override with None to explicitly exclude
    2. Simply not use the inherited descriptor (it returns None if field not present)
    """

    booking_type = EnumField()
    mrr = NumberField(field_name="MRR")
    weekly_ad_spend = NumberField()
```

**FR-010 to FR-013: Mixin Application**

| Entity | Mixins | Fields Used | Fields Not Used |
|--------|--------|-------------|-----------------|
| Business | SharedCascadingFieldsMixin, FinancialFieldsMixin | vertical, rep, booking_type | mrr, weekly_ad_spend |
| Unit | SharedCascadingFieldsMixin, FinancialFieldsMixin | ALL | - |
| Offer | SharedCascadingFieldsMixin, FinancialFieldsMixin | vertical, rep, mrr, weekly_ad_spend | booking_type |
| Process | SharedCascadingFieldsMixin, FinancialFieldsMixin | ALL | - |

**Entity Class Update Pattern**:
```python
# Before
class Unit(BusinessEntity):
    # ... 31 field descriptors including:
    vertical = EnumField()
    rep = PeopleField()
    mrr = NumberField(field_name="MRR")
    weekly_ad_spend = NumberField()
    booking_type = EnumField()
    # ... other fields

# After
from autom8_asana.models.business.mixins import (
    FinancialFieldsMixin,
    SharedCascadingFieldsMixin,
)

class Unit(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin):
    # Mixin fields removed (inherited)
    # ... other entity-specific fields remain

    # Entity-specific fields (not shared)
    discount = EnumField()
    meta_spend = NumberField()
    # ...
```

**MRO Consideration**:
```python
# Correct inheritance order (MRO):
class Unit(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin):
    pass

# MRO: Unit -> BusinessEntity -> SharedCascadingFieldsMixin -> FinancialFieldsMixin -> object
# Descriptors resolve left-to-right; entity-specific overrides take precedence
```

### Phase 2: Method Extraction

**FR-014: `_identify_holder` Extraction**

Current duplication:
- `business.py`: lines 524-572 (49 lines)
- `unit.py`: lines 339-389 (51 lines)

**Extracted Function** (in `detection.py`):
```python
def identify_holder(
    task: Task,
    holder_key_map: dict[str, tuple[str, str]],
    *,
    filter_keys: set[str] | None = None,
) -> str | None:
    """Identify which holder type a task represents.

    Per FR-014: Extracted from Business._identify_holder and Unit._identify_holder.

    Algorithm:
    1. Try detection system (Tier 1: project membership, Tier 2: name patterns)
    2. Fall back to HOLDER_KEY_MAP matching with logged warning
    3. Return holder key if found, None otherwise

    Args:
        task: Task to identify.
        holder_key_map: Map of holder_key -> (name_pattern, emoji).
        filter_keys: If provided, only return keys in this set.
            Used by Unit to filter to its HOLDER_KEY_MAP.

    Returns:
        Holder key (e.g., "contact_holder") or None.
    """
    # Detection system first
    result = detect_entity_type(task)

    if result and result.entity_type.name.endswith("_HOLDER"):
        holder_attr = get_holder_attr(result.entity_type)
        if holder_attr:
            holder_key = holder_attr.lstrip("_")
            if filter_keys is None or holder_key in filter_keys:
                return holder_key

    # Fallback to HOLDER_KEY_MAP
    for key, (name_pattern, emoji) in holder_key_map.items():
        if filter_keys and key not in filter_keys:
            continue
        if _matches_holder(task, name_pattern, emoji):
            logger.warning(
                "Detection fallback: identified %s via HOLDER_KEY_MAP for task '%s'",
                key,
                task.name,
            )
            return key

    return None


def _matches_holder(task: Task, name_pattern: str, emoji: str) -> bool:
    """Check if task matches a holder pattern."""
    # Existing implementation extracted from Business/Unit
    ...
```

**Entity Updates**:
```python
# In business.py
def _identify_holder(self, task: Task) -> str | None:
    from autom8_asana.models.business.detection import identify_holder
    return identify_holder(task, self.HOLDER_KEY_MAP)

# In unit.py
def _identify_holder(self, task: Task) -> str | None:
    from autom8_asana.models.business.detection import identify_holder
    return identify_holder(
        task,
        self.HOLDER_KEY_MAP,
        filter_keys=set(self.HOLDER_KEY_MAP.keys()),
    )
```

**FR-015: `to_business_async` Extraction** (Should Have)

Current duplication:
- `contact.py`: lines 118-199 (82 lines)
- `unit.py`: lines 229-309 (81 lines)
- `offer.py`: lines 193-282 (90 lines)

**Common Structure** (~60 lines shared):
1. Import HydrationError, `_traverse_upward_async`
2. Call `_traverse_upward_async(self, client)`
3. Conditionally hydrate with `business._fetch_holders_async(client)`
4. Handle `partial_ok` error logging
5. Wrap non-HydrationError exceptions

**Extraction Approach**: Create `UpwardTraversalMixin` in `mixins.py`:

```python
class UpwardTraversalMixin:
    """Mixin providing to_business_async implementation.

    Per FR-015: Common traversal + hydration logic.

    Subclasses must implement:
    - _update_refs_after_hydration(business): Entity-specific reference updates
    """

    async def to_business_async(
        self,
        client: AsanaClient,
        *,
        hydrate_full: bool = True,
        partial_ok: bool = False,
    ) -> Business:
        """Navigate to containing Business and optionally hydrate."""
        from autom8_asana.exceptions import HydrationError
        from autom8_asana.models.business.hydration import _traverse_upward_async

        business, path = await _traverse_upward_async(self, client)

        if hydrate_full:
            try:
                await business._fetch_holders_async(client)
            except Exception as e:
                if partial_ok:
                    logger.warning(
                        "Hydration failed with partial_ok=True",
                        extra={"business_gid": business.gid, "error": str(e)},
                    )
                else:
                    if isinstance(e, HydrationError):
                        raise
                    raise HydrationError(
                        f"Downward hydration failed for Business {business.gid}: {e}",
                        entity_gid=business.gid,
                        entity_type="business",
                        phase="downward",
                        cause=e,
                    ) from e

        # Entity-specific ref updates
        self._update_refs_after_hydration(business)
        return business

    def _update_refs_after_hydration(self, business: Business) -> None:
        """Override to update entity-specific references after hydration."""
        raise NotImplementedError
```

**Entity Updates**:
```python
# In contact.py
class Contact(BusinessEntity, UpwardTraversalMixin, ...):
    def _update_refs_after_hydration(self, business: Business) -> None:
        if business._contact_holder is not None:
            self._contact_holder = business._contact_holder
            self._business = business
```

**FR-016: `_populate_children` Consolidation** (Could Have)

OfferHolder and ProcessHolder both have nearly identical `_populate_children` overrides for `_unit` propagation. If time permits, extract to utility:

```python
def propagate_intermediate_ref(
    holder: HolderFactory,
    ref_name: str,
    ref_value: Any,
) -> None:
    """Propagate intermediate reference to all children."""
    for child in holder.children:
        setattr(child, ref_name, ref_value)
```

### Migration Strategy

**Phase Independence**: Each phase can be implemented and merged independently:

```
Phase 0 ─────────► Merge ──┬── Phase 1 ────► Merge ──┬── Phase 2 ────► Merge
                           │                         │
                           └── OR parallel ──────────┘
```

**Migration Order Within Phase 0**:

1. **ContactHolder** (lowest risk - simple migration)
2. **UnitHolder** (simple migration, validates pattern)
3. **Location.py descriptors** (isolated file)
4. **Hours.py descriptors** (isolated file)
5. **OfferHolder** (override required)
6. **ProcessHolder** (override required)
7. **LocationHolder** (most complex - Hours sibling logic)

**Rollback Procedures**:

Each file change is self-contained. Rollback = git revert of specific commit.

For partial rollback during development:
- Keep old implementation commented until tests pass
- Run full test suite after each holder migration
- Integration tests validate end-to-end behavior

### Phases Summary

| Phase | Deliverable | Dependencies | Estimate |
|-------|-------------|--------------|----------|
| 0a | ContactHolder, UnitHolder migration | None | 0.5 day |
| 0b | Location.py, Hours.py descriptors | None | 0.5 day |
| 0c | OfferHolder, ProcessHolder migration | None | 0.5 day |
| 0d | LocationHolder migration | None | 0.5 day |
| 1 | mixins.py + entity updates | Phase 0 complete | 1 day |
| 2a | `_identify_holder` extraction | None | 0.5 day |
| 2b | `to_business_async` extraction | None | 0.5 day |
| 2c | `_populate_children` consolidation | Phase 0c | 0.25 day |

**Total**: ~4 days implementation + 1 day testing/buffer = 5 days

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Pydantic mixin inheritance conflicts | High | Medium | Spike test mixin + Pydantic model before full implementation; fall back to composition |
| Descriptor MRO resolution issues | Medium | Low | Explicit inheritance order; test descriptor resolution in each entity |
| Circular imports from mixins.py | Medium | Medium | Mixins import only from descriptors.py (no entity imports) |
| HolderFactory override patterns expand scope | Medium | Low | Accept overrides as "migrated"; scope is pre-approved per PRD |
| Test modifications required | Low | Low | Refactoring only; tests validate behavior not implementation |
| Hours sibling detection regression | High | Low | Preserve exact detection logic in LocationHolder override |

## Observability

No production observability changes required (refactoring only).

**Development Observability**:
- Existing logging in `_populate_children` preserved
- Detection fallback warnings maintained in extracted `identify_holder()`
- DEBUG logging for mixin field resolution (if needed during debugging)

## Testing Strategy

**Unit Testing**:
- Each migrated holder: verify `children` property, parent refs, business ref
- Mixin field descriptors: verify field resolution via inherited descriptors
- Extracted methods: verify identical behavior to original implementations

**Integration Testing**:
- Full Business hydration: verify all holders populate correctly
- Upward traversal: verify `to_business_async` from each entity type
- Detection system: verify `identify_holder()` matches original behavior

**Regression Testing**:
- Run full `pytest` suite after each phase
- No test modifications allowed (behavior must be identical)
- Use coverage diff to ensure no code paths lost

**Pydantic Compatibility Tests** (new):
```python
def test_mixin_field_resolution():
    """Verify mixin descriptors work with Pydantic model."""
    business = Business.model_validate(task_data)
    assert business.vertical == expected_vertical
    assert business.rep == expected_rep

def test_holder_factory_migration():
    """Verify HolderFactory-based holder behaves identically."""
    holder = ContactHolder.model_validate(holder_data)
    holder._business = business
    holder._populate_children(subtasks)
    assert len(holder.contacts) == expected_count
    assert all(c._contact_holder is holder for c in holder.contacts)
```

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| None - all decisions captured in ADR-0119 | - | - | - |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-19 | Architect (Claude) | Initial draft |

---

## Quality Gate Checklist

- [x] Traces to approved PRD (PRD-SPRINT-1-PATTERN-COMPLETION)
- [x] All significant decisions have ADRs (ADR-0119)
- [x] Component responsibilities are clear (mixins, factories, descriptors)
- [x] Interfaces are defined (mixin method signatures, utility function signatures)
- [x] Complexity level is justified (Module)
- [x] Risks identified with mitigations
- [x] Implementation plan is actionable (phases, order, estimates)

## Handoff Notes for Engineer

1. **Start with ContactHolder** - lowest risk, validates the pattern
2. **Run tests after each holder** - fail fast on regressions
3. **Keep old code commented** - useful for behavior comparison during review
4. **Mixin inheritance order matters** - `(BusinessEntity, Mixin1, Mixin2)` not `(Mixin1, BusinessEntity)`
5. **Location Hours logic is subtle** - preserve exact name matching in override
6. **Phase 2 can be deferred** - Phase 0+1 deliver majority of value; Phase 2 is polish
