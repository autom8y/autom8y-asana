# ADR-0054: Cascading Custom Fields Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-11
- **Last Updated**: 2025-12-11
- **Deciders**: Architect, Principal Engineer
- **Related**:
  - [TDD-0015](../architecture/business-model-tdd.md) - Business Model Architecture
  - [ADR-0030](ADR-0030-custom-field-typing.md) - Custom Field Typing
  - [ADR-0035](ADR-0035-unit-of-work-pattern.md) - Unit of Work Pattern
  - [ADR-0053](ADR-0053-composite-savesession-support.md) - Composite SaveSession Support

## Context

The Business Model hierarchy requires custom fields that flow across levels for data consistency and operational efficiency.

### Hierarchy Structure

```
Business
├── ContactHolder → Contact[]
├── UnitHolder → Unit[]
│   ├── OfferHolder → Offer[]
│   └── ProcessHolder → Process[]
├── LocationHolder → Location → Hours
└── (other holders...)
```

### Key Insight: Cascading is Multi-Level

Cascading can originate from **any level** in the hierarchy, not just Business (root):

| Source | Target(s) | Example Field | Override Allowed? |
|--------|-----------|---------------|-------------------|
| Business | Unit, Offer, Process, Contact | `office_phone` | NO (default) |
| Business | Unit, Offer, Process | `company_id` | NO (default) |
| Unit | Offer | `platforms` | YES (explicit opt-in) |
| Unit | Offer, Process | `vertical` | NO (default) |

### Critical Design Constraint: Override is Opt-In

**DEFAULT BEHAVIOR**: Cascading fields do NOT permit local overrides. Descendants always accept the parent value.

**Override is EXPLICIT OPT-IN**: Only fields explicitly configured with `allow_override=True` permit descendants to have local values that take precedence.

Examples:
- `office_phone`: Should NEVER permit local overrides - descendant always accepts parent value
- `platforms` on Unit->Offer: Explicit opt-in - Offer can override if it has a non-null value

### Two Distinct Patterns Identified

**Pattern 1: Cascading Fields (Multi-Level, Default No Override)**
Fields that propagate from an owner to its descendants. By default, the parent value always wins.
- Source of truth: Owner entity (Business, Unit, etc.)
- Descendants receive the value (no local override by default)
- When owner changes, descendants must update
- Examples: Office Phone, Company ID (Business->all), Platforms (Unit->Offer with override opt-in)

**Pattern 2: Inherited Fields (Bubble Up Default)**
Fields that resolve from parent chain with optional override capability.
- `Unit.vertical` is source of truth for that branch
- `Offer.vertical` inherits from parent Unit
- `Business.default_vertical` computed from children
- Examples: Vertical, Booking Type, Manager

### Forces at Play

| Force | Pull Toward |
|-------|-------------|
| Read performance | Denormalize (copy values down) |
| Write simplicity | Virtual property (compute on access) |
| Data consistency | Single source of truth |
| API efficiency | Batch updates |
| Staleness risk | Eventual consistency acceptable |
| SDK complexity | Simple, explicit patterns |

### The Core Tradeoff

```
                    WRITE COMPLEXITY
                         ^
                         |
    Virtual Props        |        Denormalized
    (compute on read)    |        (copy on write)
                         |
       Reads: O(n)       |        Reads: O(1)
       Writes: O(1)      |        Writes: O(n)
       Consistent: Yes   |        Consistent: Eventually
                         |
    <-------------------|------------------>
                    READ COMPLEXITY
```

For our domain:
- **Reads are frequent**: Display Office Phone on every Offer card
- **Writes are infrequent**: Business phone changes rarely (monthly?)
- **Eventual consistency acceptable**: A few seconds of stale data is fine

This points strongly toward **denormalized storage with async propagation**.

## Decision

Implement **denormalized storage with explicit cascade operations** using multi-level cascading with opt-in override:

### Pattern 1: Cascading Fields (Multi-Level with Default No Override)

Fields can be declared at **any level** in the hierarchy and cascade to specified descendants. The critical design principle is that **override is opt-in** (disabled by default).

```python
class Business(Task):
    """Business entity with cascading field declarations."""

    class CascadingFields:
        """Fields that cascade to descendants.

        CRITICAL: allow_override=False is the DEFAULT.
        Parent value ALWAYS wins unless override is explicitly enabled.
        """
        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            target_types={Unit, Offer, Process},
            # allow_override=False is DEFAULT - descendant value always overwritten
        )
        COMPANY_ID = CascadingFieldDef(
            name="Company ID",
            target_types=None,  # None = all descendants
            # allow_override=False - no local overrides permitted
        )
        BUSINESS_NAME = CascadingFieldDef(
            name="Business Name",
            target_types={Unit, Offer},
            source_field="name",  # Maps from Task.name
        )


class Unit(Task):
    """Unit entity with its own cascading fields."""

    class CascadingFields:
        """Fields that cascade from Unit to its descendants."""
        PLATFORMS = CascadingFieldDef(
            name="Platforms",
            target_types={Offer},  # Only cascade to Offers
            allow_override=True,  # EXPLICIT OPT-IN: Offer can override if non-null
        )
        VERTICAL = CascadingFieldDef(
            name="Vertical",
            target_types={Offer, Process},
            # allow_override=False - Offer/Process always get Unit's vertical
        )
```

### Cascade Behavior Based on allow_override

| `allow_override` | Cascade Behavior |
|------------------|------------------|
| `False` (DEFAULT) | **Always overwrite** descendant value with parent value |
| `True` (explicit) | Only overwrite if descendant value is `None`/null |

### Pattern 2: Inherited Fields (Parent-Owned with Override)

Fields that inherit from parent unless explicitly overridden at child level. This pattern is for **read-time resolution**, not write-time propagation.

```python
class Offer(Task):
    """Offer entity with inherited field declarations."""

    class InheritedFields:
        """Fields inherited from parent unless overridden."""
        VERTICAL = InheritedFieldDef(
            name="Vertical",
            inherit_from=["Unit", "Business"],  # Resolution order
            allow_override=True,
        )
        MANAGER = InheritedFieldDef(
            name="Manager",
            inherit_from=["Unit"],
            allow_override=False,  # Always use parent's value
        )
```

### Storage Strategy: Denormalize with Source Tracking

Each descendant stores:
1. The field value (for fast reads)
2. A flag indicating if locally overridden (for inherited fields)

```python
# Asana stores as custom fields
{
    "gid": "offer_123",
    "custom_fields": [
        {"gid": "cf_office_phone", "text_value": "555-1234"},
        {"gid": "cf_vertical", "enum_value": {"name": "Retail"}},
        {"gid": "cf_vertical_override", "enum_value": {"name": "Yes"}},  # Inherited with override
    ]
}
```

### Propagation Mechanism

```python
@dataclass(frozen=True)
class CascadeOperation:
    """Represents a field cascade to be executed.

    Supports multi-level cascading from any source entity.
    """

    source: AsanaResource  # Entity that owns the value (Business, Unit, etc.)
    field_name: str        # "Office Phone", "Platforms", etc.
    new_value: Any         # Value to propagate
    target_types: set[type] | None  # {Offer, Process} or None for all
    allow_override: bool   # If True, skip descendants with non-null values


class SaveSession:
    """Extended with cascade support."""

    def cascade_field(
        self,
        entity: AsanaResource,
        field_name: str,
        *,
        target_types: set[type] | None = None,
    ) -> SaveSession:
        """Explicitly cascade a field change to descendants.

        IMPORTANT: Cascade scope is relative to the source entity.
        - cascade_field(unit, "platforms") only affects that unit's offers
        - cascade_field(business, "office_phone") affects all business descendants

        The allow_override behavior is determined by the field's CascadingFieldDef.

        Args:
            entity: Source entity (Business, Unit, etc.)
            field_name: Field to cascade (e.g., "Office Phone", "Platforms")
            target_types: Optional filter of target entity types. If None, uses
                         field's declared target_types from CascadingFields.

        Returns:
            Self for fluent chaining.

        Example - Business field (no override):
            business.office_phone = "555-9999"
            session.cascade_field(business, "Office Phone")
            await session.commit_async()
            # All descendants get "555-9999" regardless of their current value

        Example - Unit field (with override opt-in):
            unit.platforms = ["Google", "Meta"]
            session.cascade_field(unit, "Platforms")
            await session.commit_async()
            # Only offers with null platforms get updated
            # Offers with existing platforms keep their value
        """
        # Get field definition to determine override behavior
        field_def = self._get_cascade_field_def(entity, field_name)

        self._pending_cascades.append(
            CascadeOperation(
                source=entity,
                field_name=field_name,
                new_value=entity.get_custom_fields().get(field_name),
                target_types=target_types or (field_def.target_types if field_def else None),
                allow_override=field_def.allow_override if field_def else False,
            )
        )
        return self

    def _get_cascade_field_def(
        self,
        entity: AsanaResource,
        field_name: str,
    ) -> CascadingFieldDef | None:
        """Lookup field definition from entity's CascadingFields class."""
        if hasattr(entity, 'CascadingFields'):
            return entity.CascadingFields.get(field_name)
        return None
```

### Batch Execution Strategy

Cascades execute via Asana Batch API (per ADR-0010) for efficiency:

```python
async def _execute_cascades(
    self,
    cascades: list[CascadeOperation],
) -> list[BatchResult]:
    """Execute cascade operations in batches.

    Strategy:
    1. Collect all descendant GIDs to update (scoped to source entity)
    2. Apply allow_override filtering
    3. Group by field (same field -> same batch request)
    4. Execute in chunks of 10 (Asana batch limit)
    5. Handle rate limits with exponential backoff

    CRITICAL: Descendants are scoped to the source entity.
    - cascade from Unit X only affects Unit X's children
    - cascade from Business affects all Business descendants
    """
    all_updates: list[tuple[str, dict]] = []

    for cascade in cascades:
        # Get descendants of THIS SPECIFIC source entity
        descendants = await self._get_descendants(
            cascade.source,
            cascade.target_types,
        )

        for descendant in descendants:
            # Handle allow_override behavior
            if cascade.allow_override:
                # Only update if descendant value is null
                current_value = descendant.get_custom_fields().get(cascade.field_name)
                if current_value is not None:
                    continue  # Skip - descendant has override value

            # Default (allow_override=False): Always update
            all_updates.append((
                descendant.gid,
                {"custom_fields": {
                    cascade.field_gid: cascade.new_value
                }}
            ))

    # Use existing BatchClient for chunked execution
    return await self._client.batch.update_tasks_async(all_updates)
```

### Consistency Model: Eventual with Reconciliation

**During normal operation**: Eventual consistency (cascade propagates within same commit)

**Drift detection**: Optional reconciliation to detect stale values

```python
class CascadeReconciler:
    """Detect and repair cascading field drift."""

    async def check_consistency(
        self,
        business: Business,
        field_name: str,
    ) -> list[DriftReport]:
        """Check if descendants have stale cascade values.

        Returns list of entities with mismatched values.
        """
        expected = business.get_custom_fields().get(field_name)
        descendants = await self._get_all_descendants(business)

        return [
            DriftReport(entity=d, field=field_name, expected=expected, actual=actual)
            for d in descendants
            if (actual := d.get_custom_fields().get(field_name)) != expected
        ]

    async def repair(
        self,
        session: SaveSession,
        drifts: list[DriftReport],
    ) -> None:
        """Repair detected drift by updating stale values."""
        for drift in drifts:
            drift.entity.get_custom_fields().set(drift.field, drift.expected)
            session.track(drift.entity)
```

### SaveSession Integration

The cascade operation integrates with existing SaveSession flow:

```python
# Explicit cascade (recommended)
async with client.save_session() as session:
    session.track(business)
    business.office_phone = "555-9999"

    # Explicitly request cascade
    session.cascade_field(business, "Office Phone")

    result = await session.commit_async()
    # Business saved, then cascade batch executed


# Automatic cascade via hook (optional)
async with client.save_session() as session:
    session.enable_auto_cascade()  # Opt-in to automatic cascading

    session.track(business)
    business.office_phone = "555-9999"

    result = await session.commit_async()
    # Detects Office Phone is cascading field
    # Auto-adds cascade operation
```

### Inherited Field Resolution

For fields that inherit from parent:

```python
class Offer(Task):
    """Offer with inherited vertical field."""

    @property
    def vertical(self) -> str | None:
        """Get vertical, inheriting from parent if not overridden."""
        # Check local override flag
        if self._is_field_overridden("Vertical"):
            return self.get_custom_fields().get("Vertical")

        # Inherit from parent Unit
        if self.unit:
            return self.unit.vertical

        return None

    @vertical.setter
    def vertical(self, value: str | None) -> None:
        """Set vertical, marking as locally overridden."""
        self.get_custom_fields().set("Vertical", value)
        self.get_custom_fields().set("Vertical Override", "Yes")

    def inherit_vertical(self) -> None:
        """Clear local override, inherit from parent."""
        self.get_custom_fields().remove("Vertical Override")
```

## Rationale

### Why Denormalized Storage?

1. **Read performance**: O(1) access to Office Phone on Offer cards, no traversal
2. **Query efficiency**: Can filter/sort by cascaded fields in Asana views
3. **Offline capability**: Descendant has complete data without fetching ancestors
4. **Asana constraints**: Asana custom fields are per-task, not relational

### Why Explicit Cascade Over Automatic?

1. **No magic**: Developer sees exactly what's happening
2. **Performance control**: Large hierarchies don't auto-cascade on every change
3. **Atomic commits**: Cascade happens within same commit transaction
4. **Testing**: Easy to unit test cascade logic in isolation

```python
# Explicit is clear
session.cascade_field(business, "Office Phone")

# vs. Automatic (hidden behavior)
business.office_phone = "555"  # Secretly queues 50 updates?
```

### Why Eventual Consistency?

1. **Acceptable for domain**: Users can tolerate a few seconds of stale data
2. **Simpler implementation**: No distributed transactions needed
3. **Batch-friendly**: Collect changes, batch execute, accept eventual state
4. **Reconciliation available**: Can detect/repair drift if needed

### Why Source Tracking for Inherited Fields?

1. **Clear semantics**: Is this value local or inherited?
2. **Override capability**: Some fields allow local override, some don't
3. **Debugging**: Easy to see where a value came from
4. **Reconciliation**: Can distinguish intentional difference from drift

## Alternatives Considered

### Alternative 1: Virtual Properties (Compute on Access)

```python
@property
def office_phone(self) -> str | None:
    return self.business.office_phone  # Always traverse up
```

**Rejected because**:
- O(n) traversal on every read
- Requires Business to be loaded for every Offer access
- Cannot query/filter by cascaded fields in Asana

### Alternative 2: Event-Driven Propagation

```python
@business.office_phone.on_change
def propagate(new_value):
    for descendant in business.all_descendants:
        descendant.office_phone = new_value
```

**Rejected because**:
- Complex event wiring
- Hard to batch (events fire individually)
- Testing complexity
- Implicit behavior

### Alternative 3: Database-Style Foreign Keys

Store only at root, descendants reference via GID:
```python
offer.business_gid  # Reference to Business
offer.office_phone  # -> Business.get(offer.business_gid).office_phone
```

**Rejected because**:
- Asana doesn't support relational queries
- Would require loading Business for every Offer display
- No native support in Asana UI

### Alternative 4: Hybrid Cache Layer

Cache cascade values in SDK memory, sync to Asana periodically.

**Rejected because**:
- Adds complexity (cache invalidation)
- SDK should be stateless between sessions
- Would require persistent cache infrastructure

## Consequences

### Positive

1. **Fast reads**: O(1) field access on any entity in hierarchy
2. **Explicit control**: Developer decides when cascades happen
3. **Batch efficiency**: Uses existing BatchClient for bulk updates
4. **Queryable**: Cascaded fields visible in Asana views/reports
5. **Testable**: Cascade logic isolated and deterministic
6. **Reconcilable**: Can detect and repair drift

### Negative

1. **Storage redundancy**: Same value stored N times (acceptable tradeoff)
2. **Eventual consistency**: Brief window of stale data
3. **API calls**: Cascade requires O(descendants) API calls
4. **Manual cascade**: Developer must explicitly cascade (not automatic)
5. **Rate limit risk**: Large hierarchies may hit Asana limits

### Mitigation Strategies

| Risk | Mitigation |
|------|------------|
| Rate limits during cascade | Exponential backoff, chunking per ADR-0010 |
| Drift accumulation | Periodic reconciliation job |
| Developer forgets cascade | Lint rule to detect cascading field changes without cascade_field() |
| Large hierarchy memory | Stream descendants instead of loading all |

## Implementation Plan

### Phase 1: Field Declaration Infrastructure (Week 1)
- `CascadingFieldDef` and `InheritedFieldDef` dataclasses
- Field metadata on Business, Unit, Offer models
- Unit tests for field declarations

### Phase 2: Cascade Operation (Week 1-2)
- `SaveSession.cascade_field()` method
- `CascadeOperation` execution in commit flow
- Integration with BatchClient
- Error handling and partial failure reporting

### Phase 3: Inherited Field Resolution (Week 2)
- Inherited field property pattern
- Override flag handling
- Parent resolution chain
- Unit tests for inheritance scenarios

### Phase 4: Reconciliation (Week 3)
- `CascadeReconciler` class
- Drift detection algorithm
- Repair mechanism
- CLI command for ad-hoc reconciliation

## Code Sketches

### CascadingFieldDef (Updated for Multi-Level Cascading)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource


@dataclass(frozen=True)
class CascadingFieldDef:
    """Definition of a field that cascades from owner to descendants.

    Supports multi-level cascading: any entity can declare cascading fields
    that propagate to its descendants. The owner level is implicit from
    where the field is declared.

    CRITICAL DESIGN CONSTRAINT:
    - allow_override=False is the DEFAULT
    - This means parent value ALWAYS overwrites descendant value
    - Only set allow_override=True when descendants should keep non-null values

    Attributes:
        name: Custom field name in Asana (must match exactly)
        target_types: Set of entity types to cascade to, or None for all descendants
        allow_override: If False (DEFAULT), always overwrite descendant value.
                       If True, only overwrite if descendant value is None.
        cascade_on_change: If True, change detection includes this field
        source_field: Model attribute to use as source (if not a custom field)
        transform: Optional function to transform value before cascading

    Example - No override (DEFAULT):
        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            target_types={Unit, Offer, Process},
            # allow_override=False is default - parent always wins
        )

    Example - With override opt-in:
        PLATFORMS = CascadingFieldDef(
            name="Platforms",
            target_types={Offer},
            allow_override=True,  # EXPLICIT: Offer can have its own value
        )
    """

    name: str
    target_types: set[type] | None = None  # None = all descendants
    allow_override: bool = False  # DEFAULT: NO override - parent always wins
    cascade_on_change: bool = True
    source_field: str | None = None
    transform: Callable[[Any], Any] | None = None

    def applies_to(self, entity: AsanaResource) -> bool:
        """Check if this cascade should apply to given entity.

        Args:
            entity: Entity to check (e.g., Unit, Offer instance)

        Returns:
            True if cascade targets this entity type
        """
        if self.target_types is None:
            return True  # None means all descendants
        return type(entity) in self.target_types

    def applies_to_type(self, entity_type: type) -> bool:
        """Check if this cascade applies to given entity class.

        Args:
            entity_type: Entity class (e.g., Unit, Offer)

        Returns:
            True if cascade targets this entity type
        """
        if self.target_types is None:
            return True
        return entity_type in self.target_types

    def get_value(self, entity: AsanaResource) -> Any:
        """Extract value from source entity.

        Args:
            entity: Source entity (e.g., Business, Unit)

        Returns:
            Value to cascade, optionally transformed
        """
        if self.source_field:
            value = getattr(entity, self.source_field, None)
        else:
            value = entity.get_custom_fields().get(self.name)

        if self.transform and value is not None:
            value = self.transform(value)

        return value

    def should_update_descendant(
        self,
        descendant: AsanaResource,
    ) -> bool:
        """Determine if descendant should be updated during cascade.

        Args:
            descendant: Entity that would receive the cascaded value

        Returns:
            True if descendant should be updated

        Logic:
            - allow_override=False (DEFAULT): Always update
            - allow_override=True: Only update if descendant has null value
        """
        if not self.allow_override:
            return True  # DEFAULT: Always overwrite

        # allow_override=True: Check if descendant has a value
        current_value = descendant.get_custom_fields().get(self.name)
        return current_value is None
```

### InheritedFieldDef

```python
@dataclass(frozen=True)
class InheritedFieldDef:
    """Definition of a field inherited from parent with optional override.

    This is for READ-TIME resolution (property access), not write-time propagation.
    For write-time propagation, use CascadingFieldDef.

    Attributes:
        name: Custom field name in Asana
        inherit_from: Parent types to inherit from, in resolution order
        allow_override: If True, child can set local value. If False, always inherit.
        override_flag_field: Custom field tracking override status
    """

    name: str
    inherit_from: list[str]  # Resolution order: ["Unit", "Business"]
    allow_override: bool = True
    override_flag_field: str | None = None

    @property
    def override_field_name(self) -> str:
        """Name of the override flag field."""
        return self.override_flag_field or f"{self.name} Override"
```

### Multi-Level Cascade Examples

#### Example 1: Business.office_phone (No Override - Default)

```python
class Business(Task):
    """Business entity - root of hierarchy."""

    class CascadingFields:
        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            target_types={Unit, Offer, Process, Contact},
            # allow_override=False is DEFAULT
            # Descendants ALWAYS get Business's value
        )

    @property
    def office_phone(self) -> str | None:
        return self.get_custom_fields().get("Office Phone")

    @office_phone.setter
    def office_phone(self, value: str | None) -> None:
        self.get_custom_fields().set("Office Phone", value)


# Usage - ALL descendants get the value (no override)
async with client.save_session() as session:
    session.track(business, recursive=True)

    business.office_phone = "555-9999"
    session.cascade_field(business, "Office Phone")

    await session.commit_async()

    # Result: Business, Unit, Offer, Process, Contact ALL have "555-9999"
    # Even if Offer had "555-1111" before, it's now "555-9999"
```

#### Example 2: Unit.platforms (With Override Opt-In)

```python
class Unit(Task):
    """Unit entity - can have cascading fields to its children."""

    class CascadingFields:
        PLATFORMS = CascadingFieldDef(
            name="Platforms",
            target_types={Offer},  # Only cascade to Offers
            allow_override=True,   # EXPLICIT: Offers can keep their own value
        )

    @property
    def platforms(self) -> list[str] | None:
        return self.get_custom_fields().get("Platforms")

    @platforms.setter
    def platforms(self, value: list[str] | None) -> None:
        self.get_custom_fields().set("Platforms", value)


# Usage - Only offers with null platforms get updated
async with client.save_session() as session:
    session.track(unit, recursive=True)

    unit.platforms = ["Google", "Meta"]
    session.cascade_field(unit, "Platforms")

    await session.commit_async()

    # Result:
    # - Offer A (platforms=None): Updated to ["Google", "Meta"]
    # - Offer B (platforms=["Bing"]): KEPT as ["Bing"] (override)
    # - Offer C (platforms=None): Updated to ["Google", "Meta"]
```

#### Example 3: Scope-Limited Cascading

```python
# Cascade only affects descendants of the specific source entity

async with client.save_session() as session:
    # Load two different units
    unit_retail = await client.tasks.get_async(unit_retail_gid)
    unit_industrial = await client.tasks.get_async(unit_industrial_gid)

    session.track(unit_retail, recursive=True)
    session.track(unit_industrial, recursive=True)

    # Change platforms on retail unit only
    unit_retail.platforms = ["Google Shopping", "Amazon"]
    session.cascade_field(unit_retail, "Platforms")

    await session.commit_async()

    # Result:
    # - unit_retail's offers: Updated (respecting allow_override)
    # - unit_industrial's offers: UNCHANGED (different scope)
```

### Cascade in SaveSession Commit Flow

```python
async def commit_async(self) -> SaveResult:
    """Execute all pending changes including cascades."""
    self._ensure_open()

    # Phase 1: Execute CRUD operations
    dirty_entities = self._tracker.get_dirty_entities()
    crud_result = await self._pipeline.execute(dirty_entities)

    # Phase 2: Execute cascades (after CRUD so new entities exist)
    cascade_results = []
    if self._pending_cascades:
        cascade_results = await self._execute_cascades(self._pending_cascades)
        self._pending_cascades.clear()

    # Phase 3: Execute actions
    action_results = []
    if self._pending_actions:
        action_results = await self._execute_actions(self._pending_actions)
        self._pending_actions.clear()

    return self._merge_results(crud_result, cascade_results, action_results)
```

## Compliance

### How This Decision Is Enforced

1. **Code patterns**:
   - `CascadingFieldDef` used for all cascading fields (any level)
   - `allow_override=False` is DEFAULT - do not change unless explicitly needed
   - `InheritedFieldDef` used for read-time inheritance
   - `cascade_field()` called when modifying cascading fields

2. **Lint rules** (optional):
   ```python
   # Detect cascading field change without cascade_field()
   if field_name in entity.CascadingFields and not session.has_cascade(field_name):
       warn("Cascading field modified without cascade_field() call")
   ```

3. **Unit tests**:
   ```python
   # Test 1: Default behavior (no override) - parent always wins
   async def test_cascade_no_override_always_overwrites():
       """Default: allow_override=False means parent value always wins."""
       # Setup: Offer has existing value
       offer.get_custom_fields().set("Office Phone", "555-OLD")

       # Cascade from Business
       business.office_phone = "555-NEW"
       session.cascade_field(business, "Office Phone")
       await session.commit_async()

       # Result: Offer's value is OVERWRITTEN (no override allowed)
       assert offer.get_custom_fields().get("Office Phone") == "555-NEW"

   # Test 2: Explicit override opt-in - null values updated
   async def test_cascade_with_override_updates_null_only():
       """allow_override=True: Only update descendants with null values."""
       # Setup
       offer_a.get_custom_fields().set("Platforms", None)  # Will be updated
       offer_b.get_custom_fields().set("Platforms", ["Bing"])  # Will be KEPT

       # Cascade with override enabled
       unit.platforms = ["Google", "Meta"]
       session.cascade_field(unit, "Platforms")
       await session.commit_async()

       # Result: Only null values updated
       assert offer_a.get_custom_fields().get("Platforms") == ["Google", "Meta"]
       assert offer_b.get_custom_fields().get("Platforms") == ["Bing"]  # KEPT

   # Test 3: Cascade scope is limited to source entity's descendants
   async def test_cascade_scope_limited_to_source_descendants():
       """Cascade from Unit A does not affect Unit B's children."""
       unit_a.platforms = ["Google"]
       unit_b.platforms = ["Meta"]

       # Only cascade Unit A
       session.cascade_field(unit_a, "Platforms")
       await session.commit_async()

       # Unit A's offers updated, Unit B's offers unchanged
       assert offer_from_unit_a.platforms == ["Google"]
       assert offer_from_unit_b.platforms is None  # Unchanged

   # Test 4: Multi-level cascade (Business -> all descendants)
   async def test_cascade_from_business_reaches_all_levels():
       """Business cascade reaches Unit, Offer, Process, Contact."""
       business.company_id = "ACME-123"
       session.cascade_field(business, "Company ID")
       await session.commit_async()

       for unit in business.units:
           assert unit.get_custom_fields().get("Company ID") == "ACME-123"
           for offer in unit.offers:
               assert offer.get_custom_fields().get("Company ID") == "ACME-123"

   # Test 5: CascadingFieldDef.should_update_descendant
   def test_cascading_field_def_should_update_logic():
       """Verify should_update_descendant respects allow_override."""
       no_override = CascadingFieldDef(name="Office Phone", allow_override=False)
       with_override = CascadingFieldDef(name="Platforms", allow_override=True)

       # Descendant with existing value
       offer.get_custom_fields().set("Office Phone", "existing")
       offer.get_custom_fields().set("Platforms", "existing")

       assert no_override.should_update_descendant(offer) is True  # Always
       assert with_override.should_update_descendant(offer) is False  # Has value

       # Descendant with null value
       offer.get_custom_fields().set("Office Phone", None)
       offer.get_custom_fields().set("Platforms", None)

       assert no_override.should_update_descendant(offer) is True  # Always
       assert with_override.should_update_descendant(offer) is True  # Null
   ```

4. **Documentation**:
   - [ ] "Cascading Fields" section in Business Model guide
   - [ ] Multi-level cascading patterns and examples
   - [ ] "allow_override=False is DEFAULT" emphasized prominently
   - [ ] "Inherited Fields" section with resolution examples
   - [ ] "Consistency and Reconciliation" guide
