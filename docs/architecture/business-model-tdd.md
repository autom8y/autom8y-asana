# TDD-0015: Business Model Skills Architecture

## Metadata
- **TDD ID**: TDD-0015
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-11
- **Last Updated**: 2025-12-11
- **PRD Reference**: [skilify.md](../initiatives/skilify.md)
- **Related TDDs**:
  - [TDD-0010](../design/TDD-0010-save-orchestration.md) - SaveSession and DependencyGraph
  - [TDD-0002](../design/TDD-0002-models-pagination.md) - Base Pydantic models
- **Related ADRs**:
  - [ADR-0029](../decisions/ADR-0029-task-subclass-strategy.md) - Task Subclass Strategy
  - [ADR-0030](../decisions/ADR-0030-custom-field-typing.md) - Custom Field Typing
  - [ADR-0031](../decisions/ADR-0031-lazy-eager-evaluation.md) - Lazy vs Eager Evaluation
  - [ADR-0035](../decisions/ADR-0035-unit-of-work-pattern.md) - Unit of Work Pattern
  - [ADR-0036](../decisions/ADR-0036-change-tracking-strategy.md) - Change Tracking Strategy
  - ADR-0050 (new) - Holder Lazy Loading Strategy
  - ADR-0051 (new) - Custom Field Type Safety
  - ADR-0052 (new) - Bidirectional Reference Caching
  - ADR-0053 (new) - Composite SaveSession Support
  - [ADR-0054](../decisions/ADR-0054-cascading-custom-fields.md) - Cascading Custom Fields Strategy

## Overview

This design introduces a Business Model layer for the autom8_asana SDK that enables domain-aware operations on Business entities and their hierarchical relationships (ContactHolder, UnitHolder, LocationHolder, etc.). The architecture builds on existing SDK patterns (Task model, CustomFieldAccessor, SaveSession with DependencyGraph) to provide typed access to business-specific custom fields and navigation through the holder hierarchy.

The design addresses five critical architecture decisions:
1. **Task Subclass Hierarchy** (decided): Business/Contact/Unit/Location/Hours inherit from Task
2. **Holder Lazy Loading Strategy**: When to fetch subtasks for holder properties
3. **Custom Field Type Safety**: How to implement typed access to custom fields
4. **Bidirectional Reference Caching**: Cache vs compute parent/child references
5. **Composite SaveSession Support**: Auto-track vs manual tracking for hierarchies

## Requirements Summary

From [skilify.md](../initiatives/skilify.md):

| Requirement | Summary | Design Impact |
|-------------|---------|---------------|
| 7 holders from Business | ContactHolder, UnitHolder, LocationHolder, DNAHolder, ReconciliationsHolder, AssetEditHolder, VideographyHolder | Business model with holder properties |
| ContactHolder owner detection | Identify owner contact via position field | Contact model with is_owner property |
| Unit nested holders | OfferHolder + ProcessHolder within Unit | Recursive holder pattern |
| 18+ Business custom fields | CompanyId, BookingType, etc. | Typed field accessors |
| SaveSession for composites | Track hierarchies in dependency order | SaveSession extension |
| Bidirectional navigation | Contact -> Business, Unit -> ContactHolder | Reference caching strategy |

## Architecture Decisions

### Decision 1: Task Subclass Hierarchy (Pre-Decided)

**Status**: Accepted

**Decision**: Business, Contact, Unit, Location, Hours all inherit from Task.

**Rationale**:
- Leverages existing SaveSession infrastructure for dependency ordering
- Reuses ChangeTracker snapshot-based dirty detection via `model_dump()`
- Custom fields already accessible via `get_custom_fields()` accessor
- Asana API treats all business entities as tasks with subtasks

**Code Sketch**:
```python
from autom8_asana.models.task import Task

class Business(Task):
    """Business entity - root of the hierarchy."""

    # Holder key map for subtask type detection
    HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        "contact_holder": ("Contacts", "person"),
        "unit_holder": ("Units", "package"),
        "location_holder": ("Location", "map"),
        # ... other holders
    }
```

---

### Decision 2: Holder Lazy Loading Strategy

**Status**: Decided

**Context**:

When should subtasks (children) be fetched for holder properties like `business.contact_holder`? The options are:

| Option | Fetch Timing | Pros | Cons |
|--------|--------------|------|------|
| A: On property access | When `.contact_holder` called | Laziest, minimal initial load | Async in sync context, unpredictable |
| B: On `SaveSession.track()` | When entity registered | Predictable, batch-friendly | Fetches even if not accessed |
| C: On init (eager) | At Business construction | Simplest | Many network calls, memory cost |

**Decision**: **Option B - Fetch on `SaveSession.track()` with optional prefetch flag**

**Rationale**:

1. **Async context alignment**: `SaveSession` is already an async context manager. Fetching at `track()` keeps async operations in async context, avoiding the complexity of sync properties triggering async operations.

2. **Batch-friendly**: When tracking a Business, we can fetch all holder subtasks in a single batch request using the existing `BatchClient`:
   ```python
   # Single batch request for all holder subtasks
   subtasks = await client.tasks.get_subtasks_async(business.gid)
   ```

3. **Predictable behavior**: Developers know exactly when network calls happen - at track time, not scattered across property accesses.

4. **Memory-efficient**: Only tracked entities have their holders fetched. Untracked Business objects remain lightweight.

5. **Optional prefetch control**: Add `prefetch_holders=True|False` parameter for explicit control:
   ```python
   session.track(business, prefetch_holders=True)  # Default: fetch holders
   session.track(business, prefetch_holders=False) # Skip holder fetch
   ```

**Alternatives Rejected**:

- **Option A (on property access)**: Creating an async property or returning coroutines from properties breaks Python conventions. It would require `await business.contact_holder` which is unintuitive and complicates type hints.

- **Option C (eager on init)**: Would require async factory or trigger network calls in `__init__`, violating principle of construction being cheap. Also fetches holders even when not needed.

**Code Sketch**:
```python
# In SaveSession
def track(
    self,
    entity: T,
    prefetch_holders: bool = True,
) -> T:
    """Track entity with optional holder prefetch.

    For Business entities, prefetch_holders=True (default) will
    fetch all subtasks and populate holder properties.
    """
    self._tracker.track(entity)

    if prefetch_holders and isinstance(entity, Business):
        self._pending_prefetch.append(entity)

    return entity

async def _prefetch_holders(self, entities: list[Business]) -> None:
    """Batch fetch holder subtasks for Business entities."""
    for business in entities:
        subtasks = await self._client.tasks.get_subtasks_async(business.gid)
        business._populate_holders(subtasks)
```

**Consequences**:

| Impact | Description |
|--------|-------------|
| Positive | Predictable async behavior, batch-friendly, memory-efficient |
| Positive | Works with existing SaveSession context manager pattern |
| Negative | Adds prefetch step to commit flow |
| Negative | Holders unavailable until entity tracked in session |
| Mitigation | Provide explicit `fetch_holders()` method for standalone use |

---

### Decision 3: Custom Field Type Safety

**Status**: Decided

**Context**:

How should typed access to custom fields be implemented? The existing `CustomFieldAccessor` provides string-based access:
```python
accessor = task.get_custom_fields()
accessor.set("Priority", "High")  # Untyped
```

For business fields like `CompanyId`, `BookingType`, `MRR`, we need type-safe access with validation.

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A: Field type wrapper classes | `OfficePhone`, `CompanyId` classes | Explicit types, custom validation | Boilerplate, 80+ field classes |
| B: Pydantic validators on model | Field definitions with validators | Less code, integrated | Hard to share validators |
| C: Hybrid | Validators for simple, accessors for complex | Balanced | Two patterns to learn |

**Decision**: **Option C - Hybrid with typed property accessors and CustomFieldAccessor integration**

**Rationale**:

1. **Leverage existing CustomFieldAccessor**: The SDK already has `CustomFieldAccessor` with name-to-GID resolution and change tracking. Build on it rather than replace.

2. **Properties for ergonomics**: Business-specific properties provide IDE autocomplete:
   ```python
   business.company_id  # Property returns str | None
   business.mrr         # Property returns Decimal | None
   ```

3. **Type conversion in property getters/setters**: Handle type coercion centrally:
   ```python
   @property
   def mrr(self) -> Decimal | None:
       value = self.get_custom_fields().get("MRR")
       return Decimal(str(value)) if value is not None else None

   @mrr.setter
   def mrr(self, value: Decimal | None) -> None:
       self.get_custom_fields().set("MRR", float(value) if value else None)
   ```

4. **Validators for complex types only**: Enum fields like `BookingType` have validators; simple strings don't need them.

5. **Preserves change tracking**: All modifications flow through `CustomFieldAccessor`, so `has_changes()` and `model_dump()` work correctly.

**Alternatives Rejected**:

- **Option A (wrapper classes)**: 80+ custom field classes is excessive. Most fields are simple types (str, int, Decimal) that don't need custom classes. Wrapper overhead without benefit.

- **Option B (pure Pydantic)**: Pydantic validators on model fields would require making custom fields part of the Pydantic schema, conflicting with the API's dynamic custom field structure.

**Code Sketch**:
```python
class Business(Task):
    """Business entity with typed custom field accessors."""

    # Custom field name constants (for IDE autocomplete on field names)
    class Fields:
        COMPANY_ID = "Company ID"
        BOOKING_TYPE = "Booking Type"
        MRR = "MRR"
        # ... 15 more

    @property
    def company_id(self) -> str | None:
        """Company identifier (custom field)."""
        return self.get_custom_fields().get(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)

    @property
    def booking_type(self) -> BookingType | None:
        """Booking type enum (custom field)."""
        value = self.get_custom_fields().get(self.Fields.BOOKING_TYPE)
        return BookingType(value) if value else None

    @booking_type.setter
    def booking_type(self, value: BookingType | None) -> None:
        self.get_custom_fields().set(
            self.Fields.BOOKING_TYPE,
            value.value if value else None
        )
```

**Consequences**:

| Impact | Description |
|--------|-------------|
| Positive | IDE autocomplete for field names and properties |
| Positive | Type safety via property type hints |
| Positive | Reuses existing CustomFieldAccessor change tracking |
| Negative | Boilerplate for property definitions (mitigated by code generation) |
| Negative | Field name constants must match Asana field names exactly |
| Mitigation | Generate property definitions from field metadata |

---

### Decision 4: Bidirectional Reference Caching

**Status**: Decided

**Context**:

Should parent/child references be cached or computed on access?

```python
contact.business      # Navigate up: Contact -> ContactHolder -> Business
contact.contact_holder  # Navigate up: Contact -> ContactHolder
```

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A: Cache upward refs | Store `_business`, `_contact_holder` | O(1) access | Memory cost, stale refs |
| B: Compute on access | Walk `parent.parent` chain | Always fresh | O(n) per access |
| C: Weak references | `weakref.ref()` to parents | Memory-safe | Complexity, GC unpredictability |

**Decision**: **Option A - Cache upward references with explicit invalidation**

**Rationale**:

1. **Common access pattern**: Navigation up the hierarchy (`contact.business`) is frequent. O(1) access is worth the memory cost.

2. **Session-scoped lifetime**: Within a SaveSession, references remain valid. Stale references only matter across sessions.

3. **Explicit invalidation**: Provide `_invalidate_refs()` method called when hierarchy changes:
   ```python
   def set_parent(self, new_parent: Task) -> None:
       super().set_parent(new_parent)
       self._business = None  # Invalidate cached ref
       self._contact_holder = None
   ```

4. **Memory is cheap**: A reference is 8 bytes on 64-bit Python. Even 1000 contacts cost only 8KB for business references.

5. **Predictable performance**: No surprise O(n) tree walks during property access.

**Alternatives Rejected**:

- **Option B (compute on access)**: Walking `parent.parent` chain on every access is wasteful for common patterns like `for contact in contacts: print(contact.business.name)`.

- **Option C (weak references)**: GC behavior is unpredictable. A weakref could become invalid mid-operation if no strong reference remains, causing confusing `ReferenceError` exceptions.

**Code Sketch**:
```python
class Contact(Task):
    """Contact entity with cached upward references."""

    # Private cached references
    _business: Business | None = PrivateAttr(default=None)
    _contact_holder: Task | None = PrivateAttr(default=None)

    @property
    def business(self) -> Business | None:
        """Navigate to containing Business (cached)."""
        if self._business is None:
            self._business = self._resolve_business()
        return self._business

    @property
    def contact_holder(self) -> Task | None:
        """Navigate to containing ContactHolder (cached)."""
        if self._contact_holder is None and self.parent:
            self._contact_holder = self.parent
        return self._contact_holder

    def _resolve_business(self) -> Business | None:
        """Walk up the tree to find Business root."""
        current = self.parent
        while current is not None:
            if isinstance(current, Business):
                return current
            current = getattr(current, 'parent', None)
        return None

    def _invalidate_refs(self) -> None:
        """Invalidate cached references (call on hierarchy change)."""
        self._business = None
        self._contact_holder = None
```

**Consequences**:

| Impact | Description |
|--------|-------------|
| Positive | O(1) upward navigation |
| Positive | Predictable performance in loops |
| Positive | Simple implementation |
| Negative | Stale refs possible if hierarchy modified outside session |
| Negative | Must remember to invalidate on parent change |
| Mitigation | Document that navigation props assume session-scoped consistency |

---

### Decision 5: Composite SaveSession Support

**Status**: Decided

**Context**:

When a developer tracks a Business, should SaveSession automatically track its children (ContactHolder, UnitHolder, etc.)?

| Option | Behavior | Pros | Cons |
|--------|----------|------|------|
| A: Manual | Developer tracks each entity | Explicit, flexible | Verbose, easy to miss entities |
| B: Automatic | `track(business)` tracks entire tree | Convenient | Magic, large memory footprint |
| C: Optional | `track(business, recursive=True)` | Balanced | Extra parameter to learn |

**Decision**: **Option C - Optional recursive tracking with explicit flag**

**Rationale**:

1. **Explicit is better than implicit**: Python Zen applies. Auto-tracking an entire hierarchy could pull thousands of tasks into memory without developer awareness.

2. **Existing DependencyGraph handles ordering**: SaveSession's `DependencyGraph` already uses Kahn's algorithm to order saves based on `parent` field. Recursive tracking just needs to populate the graph.

3. **Common patterns supported**:
   ```python
   # Pattern 1: Track entire hierarchy
   session.track(business, recursive=True)

   # Pattern 2: Track specific branches
   session.track(business)
   session.track(business.contact_holder, recursive=True)

   # Pattern 3: Track leaf nodes only
   for contact in business.contacts:
       session.track(contact)
   ```

4. **Performance control**: Developer chooses memory/network tradeoff:
   - `recursive=False`: Track only what you modify
   - `recursive=True`: Track full subtree for comprehensive save

5. **Debug-ability**: When something fails, explicit tracking makes it clear what's in the session via `session.preview()`.

**Alternatives Rejected**:

- **Option A (manual only)**: Too verbose for common case of "save this business and its contacts." Would require:
  ```python
  session.track(business)
  session.track(business.contact_holder)
  for contact in business.contacts:
      session.track(contact)
  ```

- **Option B (automatic)**: Violates principle of least surprise. Developer might modify one contact but accidentally save changes to 50 units.

**Code Sketch**:
```python
class SaveSession:
    def track(
        self,
        entity: T,
        recursive: bool = False,
        prefetch_holders: bool = True,
    ) -> T:
        """Track entity for change detection.

        Args:
            entity: AsanaResource to track
            recursive: If True, also track all children (subtasks)
            prefetch_holders: If True and entity is Business, fetch holders

        Returns:
            The tracked entity (for chaining)
        """
        self._tracker.track(entity)

        if recursive:
            self._track_recursive(entity)

        if prefetch_holders and isinstance(entity, Business):
            self._pending_prefetch.append(entity)

        return entity

    def _track_recursive(self, entity: Task) -> None:
        """Recursively track all children."""
        # Check for holder properties (Business, Unit)
        if hasattr(entity, 'HOLDER_KEY_MAP'):
            for holder_name in entity.HOLDER_KEY_MAP:
                holder = getattr(entity, holder_name, None)
                if holder is not None:
                    self._tracker.track(holder)
                    self._track_recursive(holder)

        # Track direct subtasks
        for child in getattr(entity, '_children', []):
            self._tracker.track(child)
            self._track_recursive(child)
```

**Consequences**:

| Impact | Description |
|--------|-------------|
| Positive | Explicit control over what's tracked |
| Positive | Works with existing DependencyGraph ordering |
| Positive | Debug-friendly via preview() |
| Negative | Extra parameter for common recursive case |
| Negative | Developer must understand hierarchy to track correctly |
| Mitigation | Document common patterns in guides |

---

## System Context

```
+-----------------------------------------------------------------------------+
|                           SYSTEM CONTEXT                                      |
+-----------------------------------------------------------------------------+

                         +---------------------------+
                         |      SDK Consumers        |
                         |   (autom8, services)      |
                         +------------+--------------+
                                      |
                         async with SaveSession(client):
                             session.track(business, recursive=True)
                             business.company_id = "NEW123"
                             await session.commit_async()
                                      |
                                      v
+-----------------------------------------------------------------------------+
|                           autom8_asana SDK                                    |
|                                                                               |
|  +------------------------------------------------------------------------+  |
|  |                    Business Model Layer (NEW)                          |  |
|  |                                                                        |  |
|  |  +----------------+  +----------------+  +----------------+             |  |
|  |  |    Business    |  |    Contact     |  |     Unit       |             |  |
|  |  |  (Task subclass)|  | (Task subclass)|  | (Task subclass)|            |  |
|  |  +-------+--------+  +-------+--------+  +-------+--------+             |  |
|  |          |                   |                   |                      |  |
|  |          |  HOLDER_KEY_MAP   |  cached refs      |  nested holders      |  |
|  |          |                   |                   |                      |  |
|  |          v                   v                   v                      |  |
|  |  +----------------+  +----------------+  +----------------+             |  |
|  |  | ContactHolder  |  |  LocationHolder|  |  OfferHolder   |             |  |
|  |  | UnitHolder     |  |  Hours         |  |  ProcessHolder |             |  |
|  |  | etc.           |  |                |  |                |             |  |
|  |  +----------------+  +----------------+  +----------------+             |  |
|  |                                                                        |  |
|  +-----------------------------------+------------------------------------+  |
|                                      |                                       |
|  +-----------------------------------v------------------------------------+  |
|  |                    Save Orchestration Layer                            |  |
|  |                                                                        |  |
|  |  +----------------+  +----------------+  +----------------+             |  |
|  |  |  SaveSession   |  | ChangeTracker  |  |DependencyGraph |             |  |
|  |  | track(recursive)|  | (snapshots)   |  |  (Kahn's alg)  |             |  |
|  |  +----------------+  +----------------+  +----------------+             |  |
|  |                                                                        |  |
|  +-----------------------------------+------------------------------------+  |
|                                      |                                       |
|  +-----------------------------------v------------------------------------+  |
|  |                    Core SDK Infrastructure                             |  |
|  |                                                                        |  |
|  |  +----------------+  +----------------+  +----------------+             |  |
|  |  |      Task      |  |CustomFieldAccess|  |  BatchClient   |            |  |
|  |  |  (base model)  |  |  (name->GID)   |  |  (bulk ops)    |            |  |
|  |  +----------------+  +----------------+  +----------------+             |  |
|  |                                                                        |  |
|  +------------------------------------------------------------------------+  |
|                                                                               |
+-----------------------------------------------------------------------------+
                                      |
                                      v
                         +---------------------------+
                         |     Asana Batch API       |
                         +---------------------------+
```

## Component Architecture

### Package Structure

```
src/autom8_asana/
+-- models/
|   +-- business/
|   |   +-- __init__.py          # Public exports
|   |   +-- business.py          # Business(Task) model
|   |   +-- contact_holder.py    # ContactHolder(Task) model
|   |   +-- contact.py           # Contact(Task) model
|   |   +-- unit_holder.py       # UnitHolder(Task) model
|   |   +-- unit.py              # Unit(Task) model
|   |   +-- location_holder.py   # LocationHolder(Task) model
|   |   +-- location.py          # Location(Task) model
|   |   +-- hours.py             # Hours(Task) model
|   |   +-- fields.py            # Field name constants and enums
|   +-- task.py                  # Existing Task model (unchanged)
|   +-- base.py                  # Existing AsanaResource (unchanged)
+-- persistence/
|   +-- session.py               # SaveSession (extend with recursive tracking)
|   +-- ... (existing files)
```

### Class Hierarchy

```
AsanaResource (base.py)
    |
    +-- Task (task.py) - existing, unchanged
           |
           +-- Business (business/business.py)
           |      - HOLDER_KEY_MAP
           |      - company_id, booking_type, mrr properties
           |      - contact_holder, unit_holder properties
           |
           +-- ContactHolder (business/contact_holder.py)
           |      - contacts property (list of Contact)
           |      - owner property (Contact | None)
           |
           +-- Contact (business/contact.py)
           |      - _business, _contact_holder cached refs
           |      - full_name, contact_phone, position properties
           |      - is_owner property
           |
           +-- UnitHolder (business/unit_holder.py)
           |      - units property (list of Unit)
           |
           +-- Unit (business/unit.py)
           |      - nested HOLDER_KEY_MAP (offer_holder, process_holder)
           |      - mrr, ad_spend, vertical properties
           |
           +-- LocationHolder (business/location_holder.py)
           +-- Location (business/location.py)
           +-- Hours (business/hours.py)
```

## Data Flow

### Tracking and Saving a Business Hierarchy

```
Developer Code                     SDK Internals
     |                                  |
     |  async with client.save_session() as session:
     |      session.track(business, recursive=True)
     |                                  |
     |                                  v
     |                          SaveSession.track()
     |                                  |
     |                          _track_recursive(business)
     |                                  |
     |                          for holder in HOLDER_KEY_MAP:
     |                              track(holder)
     |                              for child in holder.children:
     |                                  track(child)
     |                                  |
     |      business.company_id = "NEW123"
     |                                  |
     |                          CustomFieldAccessor.set()
     |                          _modifications["Company ID"] = "NEW123"
     |                                  |
     |      await session.commit_async()
     |                                  |
     |                          ChangeTracker.get_dirty_entities()
     |                          -> [business] (only business modified)
     |                                  |
     |                          DependencyGraph.build([business])
     |                          -> levels: [[business]]
     |                                  |
     |                          SavePipeline.execute()
     |                          BatchExecutor -> PUT /tasks/{gid}
     |                                  |
     |      result.success -> True     |
     v                                  v
```

### Holder Population Flow

```
     |  session.track(business, prefetch_holders=True)
     |                                  |
     v                                  v
SaveSession._pending_prefetch.append(business)
     |
     |  (at commit or explicit prefetch call)
     |
     v
_prefetch_holders([business])
     |
     v
client.tasks.get_subtasks_async(business.gid)
     |
     v
Returns: [
    Task(name="Contacts", emoji="person"),
    Task(name="Units", emoji="package"),
    Task(name="Location", emoji="map"),
    ...
]
     |
     v
business._populate_holders(subtasks)
     |
     v
for subtask in subtasks:
    for holder_name, (name_pattern, emoji) in HOLDER_KEY_MAP.items():
        if subtask.name == name_pattern:
            setattr(business, f"_{holder_name}", ContactHolder(subtask))
```

## Technical Decisions Summary

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Task subclass hierarchy | Business/Contact/Unit inherit Task | Reuses SaveSession, ChangeTracker, CustomFieldAccessor | Pre-decided |
| Holder lazy loading | Fetch on `track()` with prefetch flag | Async-safe, batch-friendly, predictable | ADR-0050 |
| Custom field type safety | Hybrid: properties + CustomFieldAccessor | IDE support, reuses change tracking | ADR-0051 |
| Bidirectional references | Cache with explicit invalidation | O(1) access, session-scoped validity | ADR-0052 |
| Composite SaveSession | Optional `recursive=True` flag | Explicit control, debug-friendly | ADR-0053 |
| Cascading/Inherited fields | Denormalize + explicit cascade | O(1) reads, batch-friendly writes | ADR-0054 |

## Decision 6: Cascading and Inherited Custom Fields

**Status**: Decided

**Context**:

The business model hierarchy requires custom fields that flow across levels. Key insight: **cascading can originate from ANY level**, not just Business (root).

| Source | Target(s) | Example Field | Override Allowed? |
|--------|-----------|---------------|-------------------|
| Business | Unit, Offer, Process, Contact | `office_phone` | NO (default) |
| Business | Unit, Offer, Process | `company_id` | NO (default) |
| Unit | Offer | `platforms` | YES (explicit opt-in) |
| Unit | Offer, Process | `vertical` | NO (default) |

**Critical Design Constraint: Override is Opt-In**

- **DEFAULT BEHAVIOR** (`allow_override=False`): Parent value ALWAYS overwrites descendant value
- **EXPLICIT OPT-IN** (`allow_override=True`): Only cascade if descendant value is null

Examples:
- `office_phone`: Should NEVER permit local overrides - descendant always accepts parent value
- `platforms` on Unit->Offer: Explicit opt-in - Offer can override if it has a non-null value

| Pattern | Source of Truth | Propagation | Example |
|---------|-----------------|-------------|---------|
| Cascading (no override) | Owner (Business, Unit, etc.) | Explicit push down, always overwrite | Office Phone, Company ID |
| Cascading (with override) | Owner + local | Explicit push down, skip non-null | Platforms |
| Inherited | Nearest ancestor | On-access resolution | Vertical, Manager |

**Decision**: **Denormalized storage with explicit multi-level cascade operations**

**Rationale**:

1. **Read performance dominates**: Displaying Office Phone on Offer cards is frequent; changing Business phone is rare (monthly?). Optimize for reads.

2. **Asana constraints**: Custom fields are per-task, not relational. Can't do SQL-style joins.

3. **Query efficiency**: Denormalized values visible in Asana views/reports/filters.

4. **Explicit over magic**: Developer explicitly calls `cascade_field()` instead of automatic propagation.

5. **Multi-level support**: Unit can cascade to its Offers independently of Business-level cascading.

6. **Scope limiting**: `cascade_field(unit, "platforms")` only affects that unit's offers, not sibling units.

See [ADR-0054](../decisions/ADR-0054-cascading-custom-fields.md) for full decision record.

### Cascading Field Pattern (Multi-Level)

Fields can be declared at **any level** and cascade to descendants:

```python
class Business(Task):
    """Business-level cascading fields (no override - default)."""

    class CascadingFields:
        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            target_types={Unit, Offer, Process},
            # allow_override=False is DEFAULT - parent always wins
        )
        COMPANY_ID = CascadingFieldDef(
            name="Company ID",
            target_types=None,  # None = all descendants
        )


class Unit(Task):
    """Unit-level cascading fields (some with override opt-in)."""

    class CascadingFields:
        PLATFORMS = CascadingFieldDef(
            name="Platforms",
            target_types={Offer},
            allow_override=True,  # EXPLICIT: Offers can keep their value
        )
        VERTICAL = CascadingFieldDef(
            name="Vertical",
            target_types={Offer, Process},
            # allow_override=False - Offers always get Unit's vertical
        )


# Usage - Business cascade (no override)
async with client.save_session() as session:
    session.track(business, recursive=True)
    business.office_phone = "555-9999"

    session.cascade_field(business, "Office Phone")

    result = await session.commit_async()
    # ALL descendants get "555-9999" regardless of current value


# Usage - Unit cascade (with override)
async with client.save_session() as session:
    session.track(unit, recursive=True)
    unit.platforms = ["Google", "Meta"]

    session.cascade_field(unit, "Platforms")

    await session.commit_async()
    # Only offers with null platforms get updated
    # Offers with existing platforms keep their value
```

### Inherited Field Pattern

Fields that resolve from parent unless locally overridden:

```python
class Offer(Task):
    class InheritedFields:
        VERTICAL = InheritedFieldDef(
            name="Vertical",
            inherit_from=["Unit", "Business"],
            allow_override=True,
        )

    @property
    def vertical(self) -> str | None:
        """Get vertical, inheriting from parent if not overridden."""
        if self._is_field_overridden("Vertical"):
            return self.get_custom_fields().get("Vertical")
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

### SaveSession Cascade Integration

```python
class SaveSession:
    def cascade_field(
        self,
        entity: AsanaResource,
        field_name: str,
        *,
        targets: list[str] | None = None,
    ) -> SaveSession:
        """Queue cascade of field value to descendants.

        Executed after CRUD operations in commit_async().
        Uses BatchClient for efficient bulk updates.

        Args:
            entity: Source entity (e.g., Business)
            field_name: Custom field to cascade
            targets: Filter target types (default: field's declared targets)
        """
        self._pending_cascades.append(
            CascadeOperation(
                source=entity,
                field_name=field_name,
                new_value=entity.get_custom_fields().get(field_name),
                targets=targets,
            )
        )
        return self
```

### Consistency Model

- **During commit**: Cascade executes in same commit as source change
- **Eventual consistency**: Brief window (seconds) where descendants may have stale value
- **Reconciliation**: `CascadeReconciler` class for drift detection and repair

```python
# Optional reconciliation
reconciler = CascadeReconciler(client)
drifts = await reconciler.check_consistency(business, "Office Phone")
if drifts:
    await reconciler.repair(session, drifts)
```

### Field Declarations Summary

| Entity | Cascading Fields | Override? | Inherited Fields |
|--------|-----------------|-----------|------------------|
| Business | Office Phone, Company ID, Business Name | NO (default) | - |
| Unit | Platforms, Vertical, Booking Type | Platforms=YES, others=NO | Default Vertical (from Business) |
| Offer | - | - | Vertical, Manager (from Unit) |
| Process | - | - | Vertical (from Offer/Unit) |
| Contact | - | - | - |

**Cascade Behavior Summary**:

| `allow_override` | Behavior | Use Case |
|------------------|----------|----------|
| `False` (DEFAULT) | Always overwrite descendant value | `office_phone`, `company_id`, `vertical` |
| `True` (explicit) | Only overwrite if descendant is null | `platforms` (Offer can have local value) |

**Consequences**:

| Impact | Description |
|--------|-------------|
| Positive | O(1) read access to cascaded fields |
| Positive | Explicit cascade call is clear and testable |
| Positive | Works with existing BatchClient for bulk updates |
| Positive | Multi-level cascading supports Unit->Offer patterns |
| Positive | Default no-override prevents accidental data loss |
| Negative | Storage redundancy (same value N times) |
| Negative | Developer must call cascade_field() explicitly |
| Mitigation | Lint rule to detect cascading field changes without cascade |

---

## Implementation Plan

### Phase 1: Core Models (Week 1)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `models/business/fields.py` - Field constants, enums | None | 2h |
| `models/business/business.py` - Business model | Task, fields.py | 4h |
| `models/business/contact_holder.py` - ContactHolder | Task | 2h |
| `models/business/contact.py` - Contact with cached refs | Task, fields.py | 4h |
| Unit tests for models | All models | 4h |

**Exit Criteria**: Models instantiate from API responses; custom field properties work; cached refs resolve.

### Phase 2: Holder Pattern (Week 1-2)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Holder population logic | Business model | 3h |
| Unit/Location/Hours models | Task | 4h |
| Navigation property tests | All models | 3h |

**Exit Criteria**: `business.contact_holder.contacts` returns Contact list; `contact.business` resolves.

### Phase 3: SaveSession Extensions (Week 2)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `track(recursive=True)` implementation | SaveSession, models | 4h |
| `prefetch_holders` implementation | SaveSession, TasksClient | 4h |
| Integration tests with SaveSession | All components | 4h |

**Exit Criteria**: `session.track(business, recursive=True)` tracks entire hierarchy; commit saves dirty entities in order.

### Phase 4: Cascading and Inherited Fields (Week 2-3)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `CascadingFieldDef` and `InheritedFieldDef` dataclasses | None | 2h |
| Field declarations on Business, Unit, Offer models | Core models | 3h |
| `SaveSession.cascade_field()` method | SaveSession | 4h |
| Cascade execution in commit flow | BatchClient | 4h |
| Inherited field property pattern with override | Core models | 3h |
| `CascadeReconciler` for drift detection | Models, Client | 4h |
| Unit tests for cascade and inheritance | All components | 4h |

**Exit Criteria**: `cascade_field()` updates all descendants via batch API; inherited fields resolve correctly; override flag works.

### Phase 5: Documentation and Skills (Week 3-4)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| autom8-asana-business-schemas skill | Implementation | 4h |
| autom8-asana-business-relationships skill | Implementation | 3h |
| autom8-asana-business-fields skill | Implementation | 3h |
| autom8-asana-business-workflows skill | Implementation | 3h |
| Cascading fields guide | Phase 4 | 2h |

**Exit Criteria**: Skills activate on relevant keywords; patterns documented with examples.

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Circular imports in model hierarchy | High | Medium | Use TYPE_CHECKING imports, forward references |
| Custom field GID changes between envs | Medium | Medium | Use field names (resolved at runtime), not hardcoded GIDs |
| Large hierarchies exhaust memory | Medium | Low | Document batch size limits; provide streaming alternative |
| Cached refs become stale | Medium | Medium | Document session-scoped validity; provide refresh method |
| Name-based holder detection fragile | High | Medium | Use emoji indicators as fallback; validate at track time |
| Rate limits during cascade | High | Medium | Exponential backoff, chunk via BatchClient (10/batch) |
| Cascade drift accumulation | Medium | Low | Periodic reconciliation via CascadeReconciler |
| Developer forgets cascade_field() | Medium | High | Lint rule to detect cascading field changes without cascade |
| Large hierarchy cascade timeout | Medium | Low | Stream descendants; progress callbacks; timeout config |

## Testing Strategy

### Unit Tests (Target: 90% coverage)

- **Model construction**: Business/Contact/Unit from API responses
- **Custom field properties**: Get/set/delete for all 18+ Business fields
- **Cached reference resolution**: Parent navigation, invalidation
- **Holder detection**: Name + emoji matching
- **CascadingFieldDef**: Field declaration, target matching
- **InheritedFieldDef**: Resolution order, override detection
- **Inherited field resolution**: Parent chain traversal, override flag

### Integration Tests (Target: 80% coverage)

- **End-to-end flow**: Track Business -> modify Contact -> commit
- **Recursive tracking**: Full hierarchy tracked and saved
- **Prefetch verification**: Holders populated correctly
- **DependencyGraph ordering**: Parents saved before children
- **Cascade propagation**: Business.office_phone -> all descendants via batch
- **Cascade with filtering**: Target specific entity types only
- **Inherited override**: Offer overrides Unit's vertical
- **Reconciliation**: Detect drift, repair via session

### Performance Benchmarks

| Scenario | Target | Measurement |
|----------|--------|-------------|
| Track Business with 50 contacts | < 100ms | Time to complete track() |
| Navigate contact.business 1000x | < 10ms | Cached vs uncached |
| Save Business + 10 contacts | < 2s | Full commit cycle |
| Cascade to 50 descendants | < 3s | Time for cascade_field() commit |
| Cascade to 200 descendants | < 10s | Time for large hierarchy cascade |
| Inherited field resolution 1000x | < 50ms | Cached parent chain traversal |

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should holder types be Protocol or ABC? | Engineer | Phase 1 | TBD based on extensibility needs |
| How to handle holder without children? | Architect | Phase 2 | Return empty list vs None |
| Cache invalidation triggers? | Engineer | Phase 2 | Document all mutation points |
| Auto-cascade on save vs explicit cascade_field()? | Architect | Phase 4 | Explicit (per ADR-0054) |
| How to handle cascade partial failures? | Engineer | Phase 4 | Report in SaveResult, don't rollback |
| Should reconciliation be automatic or on-demand? | Architect | Phase 4 | On-demand via CascadeReconciler |
| Cascade to new entities (temp GIDs)? | Engineer | Phase 4 | Skip temp GIDs, cascade after real GID assigned |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-11 | Architect | Initial design with 5 architecture decisions |
| 1.1 | 2025-12-11 | Architect | Added Decision 6: Cascading and Inherited Fields (ADR-0054) |
