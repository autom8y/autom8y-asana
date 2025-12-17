# TDD: Business Model Layer Implementation

## Metadata

- **TDD ID**: TDD-BIZMODEL
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-11
- **Last Updated**: 2025-12-11
- **PRD Reference**: [PRD-BIZMODEL](../requirements/PRD-BIZMODEL.md)
- **Discovery Document**: [DISCOVERY-BIZMODEL-001](../initiatives/DISCOVERY-BIZMODEL-001.md)
- **Related TDDs**: TDD-0011 (Action Endpoints), TDD-0015 (Business Model Architecture - legacy)
- **Related ADRs**: ADR-0050, ADR-0051, ADR-0052, ADR-0053, ADR-0054

---

## Overview

This TDD defines the technical architecture for implementing the Business Model layer on top of the autom8_asana SDK. The design introduces 7 entity types (Business, Contact, Unit, Offer, Process, Address, Hours), 7 holder types, 127 typed custom field accessors, and SaveSession extensions for hierarchical tracking and cascading field propagation. The architecture extends existing SDK infrastructure without modifying core behavior.

---

## Requirements Summary

From PRD-BIZMODEL:
- **FR-MODEL**: 12 requirements for model class definitions
- **FR-HOLDER**: 9 requirements for holder pattern implementation
- **FR-FIELD**: 13 requirements for custom field accessors
- **FR-CASCADE**: 8 requirements for cascading field definitions
- **FR-INHERIT**: 4 requirements for inherited field resolution
- **FR-SESSION**: 10 requirements for SaveSession integration
- **FR-CASCADE-EXEC**: 7 requirements for cascade execution
- **FR-NAV**: 6 requirements for navigation properties

**Total**: 77 functional requirements (60 Must, 12 Should, 5 Could)

---

## System Context

The Business Model layer sits between SDK consumers and the core autom8_asana SDK:

```
+----------------------------------+
|        SDK Consumers             |
|  (Automation scripts, APIs)      |
+----------------------------------+
              |
              v
+----------------------------------+
|     Business Model Layer         |  <-- THIS TDD
|  Business, Unit, Contact, Offer  |
|  Holders, Typed Fields, Cascade  |
+----------------------------------+
              |
              v
+----------------------------------+
|       autom8_asana SDK           |
|  Task, SaveSession, BatchClient  |
+----------------------------------+
              |
              v
+----------------------------------+
|         Asana REST API           |
+----------------------------------+
```

**Integration Points**:
- **Task model**: Business models inherit from `Task` (no modifications to task.py)
- **CustomFieldAccessor**: Used for change tracking (no modifications)
- **SaveSession**: Extended with new parameters and methods (additive changes)
- **BatchClient**: Used by CascadeExecutor for bulk updates

---

## ADR Validation Matrix

All 5 existing ADRs are validated against PRD requirements:

| ADR | Decision | Requirements Satisfied |
|-----|----------|------------------------|
| **ADR-0050** | Holder lazy loading on `track()` with `prefetch_holders=True` | FR-SESSION-001, FR-SESSION-003, FR-SESSION-007, FR-SESSION-009, FR-SESSION-010, FR-HOLDER-008 |
| **ADR-0051** | Hybrid typed properties delegating to CustomFieldAccessor | FR-FIELD-001 to FR-FIELD-013 (all 13 field requirements) |
| **ADR-0052** | Cached upward refs with explicit invalidation | FR-NAV-001 to FR-NAV-006 (all 6 navigation requirements) |
| **ADR-0053** | Optional `recursive=True` for composite SaveSession | FR-SESSION-002, FR-SESSION-009, FR-MODEL-003, FR-MODEL-007 |
| **ADR-0054** | Cascading fields with `allow_override=False` default | FR-CASCADE-001 to FR-CASCADE-008, FR-CASCADE-EXEC-001 to FR-CASCADE-EXEC-007, FR-INHERIT-001 to FR-INHERIT-004 |

**Coverage Summary**: All 77 PRD requirements are covered by existing ADRs. No new ADRs required.

---

## Design

### Package Structure

```
src/autom8_asana/
|
+-- models/
|   +-- task.py                    # Existing (unchanged)
|   +-- custom_field_accessor.py   # Existing (unchanged)
|   +-- business/
|   |   +-- __init__.py            # Public exports: Business, Contact, Unit, etc.
|   |   +-- base.py                # HolderMixin, BusinessEntity base
|   |   +-- fields.py              # CascadingFieldDef, InheritedFieldDef
|   |   |
|   |   +-- business.py            # Business model + 7 holder properties
|   |   +-- contact.py             # Contact, ContactHolder
|   |   +-- unit.py                # Unit, UnitHolder (nested holders)
|   |   +-- offer.py               # Offer, OfferHolder
|   |   +-- process.py             # Process, ProcessHolder
|   |   +-- location.py            # Address, Hours, LocationHolder
|   |
+-- persistence/
|   +-- session.py                 # Extended: prefetch_holders, recursive, cascade_field
|   +-- cascade.py                 # NEW: CascadeOperation, CascadeExecutor
|   +-- ... (existing unchanged)
```

### Component Architecture

```
+-------------------------------------------------------------------------+
|                        Business Model Layer                              |
+-------------------------------------------------------------------------+
|                                                                          |
|  +------------------+     +------------------+     +------------------+  |
|  |    Business      |---->|   ContactHolder  |---->|     Contact      |  |
|  |   (Task subclass)|     |   (Task subclass)|     |   (Task subclass)|  |
|  +------------------+     +------------------+     +------------------+  |
|          |                                                |              |
|          |  +------------------+     +------------------+ |              |
|          +->|    UnitHolder    |---->|       Unit       |-+              |
|          |  +------------------+     +------------------+                |
|          |                                  |                            |
|          |                    +-------------+-------------+              |
|          |                    |                           |              |
|          |            +------------------+     +------------------+      |
|          |            |   OfferHolder    |     |  ProcessHolder   |      |
|          |            +------------------+     +------------------+      |
|          |                    |                           |              |
|          |            +------------------+     +------------------+      |
|          |            |      Offer       |     |     Process      |      |
|          |            +------------------+     +------------------+      |
|          |                                                               |
|          |  +------------------+     +------------------+                |
|          +->| LocationHolder   |---->| Address | Hours  | (siblings)     |
|             +------------------+     +------------------+                |
|                                                                          |
+-------------------------------------------------------------------------+
```

| Component | Responsibility | Location |
|-----------|----------------|----------|
| `Business` | Root entity with 7 holder properties, cascading fields | `models/business/business.py` |
| `Contact`, `ContactHolder` | Contact entities with owner detection | `models/business/contact.py` |
| `Unit`, `UnitHolder` | Unit entities with nested OfferHolder/ProcessHolder | `models/business/unit.py` |
| `Offer`, `OfferHolder` | Offer entities with ad status determination | `models/business/offer.py` |
| `Process`, `ProcessHolder` | Process entities (base type for Phase 2) | `models/business/process.py` |
| `Address`, `Hours`, `LocationHolder` | Location/Hours siblings | `models/business/location.py` |
| `CascadingFieldDef` | Field cascade metadata | `models/business/fields.py` |
| `InheritedFieldDef` | Inherited field metadata | `models/business/fields.py` |
| `CascadeOperation` | Pending cascade representation | `persistence/cascade.py` |
| `CascadeExecutor` | Batch cascade execution | `persistence/cascade.py` |

---

### Class Diagrams

#### Business Entity Hierarchy

```
                      +----------------+
                      |   AsanaResource|
                      +----------------+
                             ^
                             |
                      +----------------+
                      |      Task      |
                      +----------------+
                             ^
                             |
          +------------------+------------------+
          |                  |                  |
   +------------+     +------------+     +------------+
   |  Business  |     |  Contact   |     |    Unit    |
   +------------+     +------------+     +------------+
   | HOLDER_KEY |     | OWNER_POS  |     | HOLDER_KEY |
   | _MAP       |     | _business  |     | _MAP       |
   | _contact_  |     | _contact_  |     | _offer_    |
   |  holder    |     |  holder    |     |  holder    |
   +------------+     +------------+     +------------+
         |                                     |
         v                                     v
   +------------+                       +------------+
   | Contact    |                       |   Offer    |
   |  Holder    |                       |   Holder   |
   +------------+                       +------------+
   | _contacts  |                       | _offers    |
   | _business  |                       | _unit      |
   +------------+                       +------------+
```

#### Field Definitions

```
+---------------------------+       +---------------------------+
|   CascadingFieldDef       |       |   InheritedFieldDef       |
+---------------------------+       +---------------------------+
| name: str                 |       | name: str                 |
| target_types: set | None  |       | inherit_from: list[str]   |
| allow_override: bool=False|       | allow_override: bool      |
| source_field: str | None  |       | override_flag_field: str  |
| transform: Callable | None|       +---------------------------+
+---------------------------+       | applies_to()              |
| applies_to()              |       | resolve()                 |
| get_value()               |       +---------------------------+
| should_update_descendant()|
+---------------------------+
```

#### SaveSession Extensions

```
+-----------------------------------------------+
|              SaveSession (Extended)           |
+-----------------------------------------------+
| _pending_prefetch: list[AsanaResource]  # NEW |
| _pending_cascades: list[CascadeOperation]# NEW|
+-----------------------------------------------+
| track(entity, prefetch_holders, recursive)    |  # Extended signature
| cascade_field(entity, field_name, target_types)| # NEW method
| prefetch_pending()                            |  # NEW method
| _track_recursive(entity)                      |  # NEW internal
| _execute_prefetch()                           |  # NEW internal
| _execute_cascades()                           |  # NEW internal
+-----------------------------------------------+
```

---

### Data Model

#### Entity Storage

All business entities are stored as Asana Tasks. The hierarchy is maintained via `parent` field:

```
Task (gid: "business_123", name: "Acme Corp")
  |
  +-- Task (gid: "holder_contacts", name: "Contacts", parent: "business_123")
  |     |
  |     +-- Task (gid: "contact_1", name: "John Doe", parent: "holder_contacts")
  |     +-- Task (gid: "contact_2", name: "Jane Doe", parent: "holder_contacts")
  |
  +-- Task (gid: "holder_units", name: "Units", parent: "business_123")
  |     |
  |     +-- Task (gid: "unit_1", name: "Downtown Office", parent: "holder_units")
  |           |
  |           +-- Task (gid: "holder_offers", name: "Offers", parent: "unit_1")
  |                 |
  |                 +-- Task (gid: "offer_1", name: "Summer Promo", parent: "holder_offers")
  |
  +-- Task (gid: "holder_location", name: "Location", parent: "business_123")
        |
        +-- Task (gid: "address_1", name: "123 Main St", parent: "holder_location")
        +-- Task (gid: "hours_1", name: "Business Hours", parent: "holder_location")
```

#### Holder Detection Strategy

Holders are identified by name match first, emoji fallback second:

```python
HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
    # property_name: (name_pattern, emoji_fallback)
    "contact_holder": ("Contacts", "busts_in_silhouette"),
    "unit_holder": ("Units", "package"),
    "location_holder": ("Location", "round_pushpin"),
    "dna_holder": ("DNA", "dna"),
    "reconciliations_holder": ("Reconciliations", "abacus"),
    "asset_edit_holder": ("Asset Edit", "art"),
    "videography_holder": ("Videography", "video_camera"),
}
```

---

### API Contracts

#### SaveSession Extended Interface

```python
class SaveSession:
    def track(
        self,
        entity: T,
        *,
        prefetch_holders: bool = False,  # NEW: Default False per discovery
        recursive: bool = False,          # NEW: Default False per ADR-0053
    ) -> T:
        """Track entity with optional holder prefetch and recursive tracking.

        Args:
            entity: AsanaResource to track.
            prefetch_holders: If True and entity has HOLDER_KEY_MAP,
                            queue holder subtasks for prefetch.
            recursive: If True, recursively track all descendants.

        Returns:
            The tracked entity for chaining.
        """

    def cascade_field(
        self,
        entity: AsanaResource,
        field_name: str,
        *,
        target_types: set[type] | None = None,
    ) -> SaveSession:
        """Queue cascade of field value to descendants.

        Args:
            entity: Source entity (Business, Unit, etc.).
            field_name: Custom field to cascade.
            target_types: Optional filter. If None, uses field's declared targets.

        Returns:
            Self for fluent chaining.

        Raises:
            ValueError: If entity has temp GID.
            SessionClosedError: If session is closed.
        """

    async def prefetch_pending(self) -> None:
        """Execute prefetch for all pending entities.

        Called automatically at start of commit_async() if not called explicitly.
        """
```

#### CascadeExecutor Interface

```python
@dataclass(frozen=True)
class CascadeOperation:
    """Pending cascade operation."""
    source: AsanaResource
    field_name: str
    field_gid: str | None = None  # Resolved during execution
    new_value: Any = None
    target_types: set[type] | None = None
    allow_override: bool = False


class CascadeExecutor:
    """Executes cascade operations via batch API."""

    def __init__(self, batch_client: BatchClient) -> None: ...

    async def execute(
        self,
        cascades: list[CascadeOperation],
        descendants_cache: dict[str, list[AsanaResource]] | None = None,
    ) -> list[BatchResult]:
        """Execute all pending cascades.

        Strategy:
        1. Collect descendant GIDs scoped to source entity
        2. Apply allow_override filtering
        3. Resolve field name to GID
        4. Chunk updates (max 10 per batch)
        5. Handle rate limits with exponential backoff
        """
```

---

### Data Flow

#### Cascade Execution Flow

```
cascade_field(business, "Office Phone")
              |
              v
+----------------------------+
| Create CascadeOperation    |
| - source: business         |
| - field_name: Office Phone |
| - new_value: "555-9999"    |
| - target_types: {Unit,...} |
| - allow_override: False    |
+----------------------------+
              |
              v (at commit_async time)
+----------------------------+
| Phase 1: CRUD Operations   |
| - Create/Update entities   |
+----------------------------+
              |
              v
+----------------------------+
| Phase 2: Execute Cascades  |
| - Collect descendants      |
| - Apply override filter    |
| - Resolve field GID        |
| - Batch update             |
+----------------------------+
              |
              v
+----------------------------+
| Phase 3: Action Operations |
| - add_tag, set_parent, etc |
+----------------------------+
```

#### Holder Prefetch Flow

```
track(business, prefetch_holders=True)
              |
              v
+----------------------------+
| Add to _pending_prefetch   |
+----------------------------+
              |
              v (at prefetch_pending() or commit_async())
+----------------------------+
| Fetch subtasks via API     |
| GET /tasks/{gid}/subtasks  |
+----------------------------+
              |
              v
+----------------------------+
| Identify holders by        |
| name/emoji pattern         |
+----------------------------+
              |
              v
+----------------------------+
| For each holder:           |
| - Fetch holder subtasks    |
| - Convert to typed models  |
| - Set back-references      |
+----------------------------+
              |
              v
+----------------------------+
| business.contact_holder    |
| business.contacts          |
| contact.business           |  <-- All now accessible
+----------------------------+
```

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Holder loading timing | On `track()` with `prefetch_holders=True` | Keeps async in async context, batch-friendly | ADR-0050 |
| Custom field type safety | Properties delegating to CustomFieldAccessor | Reuses existing change tracking, IDE support | ADR-0051 |
| Upward navigation | Cached PrivateAttr with invalidation | O(1) access, session-scoped validity | ADR-0052 |
| Recursive tracking | Optional `recursive=True` flag | Explicit control, memory predictability | ADR-0053 |
| Cascade override behavior | `allow_override=False` default | Parent always wins unless explicit opt-in | ADR-0054 |
| Cascade execution timing | After CRUD, before actions | New entities have real GIDs | ADR-0054 |
| LocationHolder children | Address and Hours as siblings | Single-location business model | PRD assumption |
| Stub holders | Return as plain Task | DNA, Reconciliations, etc. not in primary workflow | PRD out-of-scope |

---

## Open Questions Resolution

### Q1: Should `Business.from_gid()` be async factory method or classmethod?

**Resolution: Async factory method with synchronous fallback.**

```python
class Business(Task):
    @classmethod
    async def from_gid_async(
        cls,
        client: AsanaClient,
        gid: str,
        *,
        prefetch_holders: bool = True,
    ) -> Business:
        """Fetch and construct Business from GID.

        Args:
            client: AsanaClient for API calls.
            gid: Business task GID.
            prefetch_holders: If True, also fetch holder subtasks.

        Returns:
            Fully constructed Business with optional holders populated.
        """
        task_data = await client.tasks.get_async(gid)
        business = cls.model_validate(task_data)

        if prefetch_holders:
            await business._fetch_holders_async(client)

        return business

    @classmethod
    def from_gid(cls, client: AsanaClient, gid: str, ...) -> Business:
        """Synchronous wrapper for from_gid_async."""
        return sync_wrapper(cls.from_gid_async(client, gid, ...))
```

**Rationale**: Async factory is required because holder fetching requires API calls. Sync wrapper provides convenience for non-async contexts.

---

### Q2: How should holder children be sorted?

**Resolution: Sort by `created_at` ascending (oldest first), with fallback to `name` alphabetical.**

```python
def _populate_children(self, subtasks: list[Task]) -> None:
    """Populate children from subtasks, sorted by created_at."""
    # Sort by created_at (oldest first), then by name for stability
    sorted_tasks = sorted(
        subtasks,
        key=lambda t: (t.created_at or "", t.name or ""),
    )
    self._contacts = [Contact.model_validate(t.model_dump()) for t in sorted_tasks]
```

**Rationale**: `created_at` provides stable, deterministic ordering that matches user expectations (first-created appears first). Name fallback ensures consistency when created_at is unavailable.

---

### Q3: Should cascade errors fail the entire commit or be partial?

**Resolution: Partial failure with reporting in SaveResult.**

```python
async def commit_async(self) -> SaveResult:
    # Phase 1: CRUD (existing behavior - partial failure)
    crud_result = await self._pipeline.execute(...)

    # Phase 2: Cascades (partial failure)
    cascade_results = await self._execute_cascades(...)

    # Merge results
    return SaveResult(
        success=crud_result.success and all(r.success for r in cascade_results),
        partial=crud_result.partial or any(not r.success for r in cascade_results),
        successful=[...],
        failed=[...],  # Includes cascade failures
    )
```

**Rationale**:
1. CRUD operations already use partial failure semantics
2. Cascade failures should not rollback successful CRUD
3. Developers can inspect `result.failed` and retry selectively
4. Consistent with SDK's commit-and-report philosophy

---

### Q4: CascadeReconciler - Phase 1 or defer?

**Resolution: Defer to future phase (explicitly out of scope per PRD).**

The `CascadeReconciler` class is mentioned in ADR-0054 but is explicitly listed as out of scope in PRD-BIZMODEL. Implementation will occur in a future initiative focused on data consistency tooling.

---

### Q5: Process model - minimal base or forward-compatible for Phase 2 subclasses?

**Resolution: Forward-compatible base with ProcessType enum placeholder.**

```python
class ProcessType(str, Enum):
    """Process subtype enum (expanded in Phase 2)."""
    GENERIC = "generic"
    # Phase 2 additions:
    # AUDIT = "audit"
    # BUILD = "build"
    # CREATIVE = "creative"
    # ... 24+ more


class Process(Task):
    """Process entity (base type for Phase 2 subclasses).

    Phase 1: Returns as-is with ProcessType.GENERIC.
    Phase 2: Subclasses (Audit, Build, Creative, etc.) with specialized fields.
    """

    @property
    def process_type(self) -> ProcessType:
        """Determine process type from task name or custom field."""
        # Phase 1: All processes are generic
        return ProcessType.GENERIC
```

**Rationale**: Forward-compatible design allows Phase 2 to add subclasses without breaking Phase 1 code. The `process_type` property provides the extension point.

---

## Complexity Assessment

**Level: Module (between Script and Service)**

| Factor | Assessment |
|--------|------------|
| Component count | 15 new classes (7 entities, 7 holders, 1 executor) |
| External dependencies | None beyond existing SDK |
| API surface | 5 new public methods on SaveSession |
| State management | Session-scoped (no persistence) |
| Concurrency | Async-first, batch operations |
| Error handling | Partial failure with reporting |

**Why Module, not Service?**

- No new deployment artifacts
- No new external API contracts
- Extends existing infrastructure
- State is session-scoped (no database)
- Testing is unit + integration (no E2E)

**Why not Script?**

- 15+ classes with relationships
- Complex change tracking integration
- Multiple ADRs governing design
- 127 field accessors

---

## Implementation Plan

### Phase 1: Foundation (Estimated: 3-4 days)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `models/business/fields.py` (CascadingFieldDef, InheritedFieldDef) | None | 0.5 day |
| `models/business/base.py` (HolderMixin, BusinessEntity) | fields.py | 0.5 day |
| `models/business/contact.py` (Contact, ContactHolder) | base.py | 0.5 day |
| `models/business/business.py` (Business, 19 fields) | contact.py | 1 day |
| Unit tests for Phase 1 models | All above | 1 day |

**Phase 1 Outputs**:
- Business model with ContactHolder and Contact
- 38 typed field accessors (19 Business + 19 Contact)
- Holder detection via HOLDER_KEY_MAP
- Upward/downward navigation between Business/Contact

### Phase 2: Unit Hierarchy (Estimated: 4-5 days)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `models/business/unit.py` (Unit, UnitHolder, 31 fields) | Phase 1 | 1.5 days |
| `models/business/offer.py` (Offer, OfferHolder, 39 fields) | unit.py | 1 day |
| `models/business/process.py` (Process, ProcessHolder) | unit.py | 0.5 day |
| SaveSession.track() extensions (prefetch_holders, recursive) | Phase 1 | 1 day |
| Unit tests for Phase 2 | All above | 1 day |

**Phase 2 Outputs**:
- Complete Unit->Offer->Process hierarchy
- 70 additional typed field accessors
- SaveSession prefetch_holders and recursive tracking
- Nested holder navigation (Unit.offer_holder.offers)

### Phase 3: Location and Cascade (Estimated: 4-5 days)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `models/business/location.py` (Address, Hours, LocationHolder, 19 fields) | Phase 1 | 1 day |
| `persistence/cascade.py` (CascadeOperation, CascadeExecutor) | Phase 2 | 1.5 days |
| SaveSession.cascade_field() integration | cascade.py | 1 day |
| Integration tests (full hierarchy, cascades) | All above | 1 day |
| Documentation and examples | All above | 0.5 day |

**Phase 3 Outputs**:
- Address/Hours sibling pattern
- 19 additional typed field accessors (127 total)
- cascade_field() with batch execution
- Full integration tests

### Migration Strategy

No migration required - this is additive functionality. Existing SDK code is unchanged:

1. **Task model**: Unchanged. Business models inherit from Task.
2. **SaveSession**: Extended with new optional parameters. Existing `track(entity)` unchanged.
3. **CustomFieldAccessor**: Unchanged. Properties delegate to existing methods.
4. **BatchClient**: Unchanged. CascadeExecutor uses existing batch infrastructure.

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Circular imports in model hierarchy | Medium | Medium | TYPE_CHECKING guards, forward references |
| Custom field GIDs vary between environments | Medium | High | Runtime name resolution via CustomFieldAccessor |
| Large hierarchies exhaust memory | Medium | Low | Document limits, provide streaming option |
| Cascade batch API hits rate limits | Medium | Medium | Exponential backoff via existing BatchClient |
| Holder detection fails on renamed tasks | Medium | Low | Emoji fallback, validation on track |
| Cached refs become stale | Low | Medium | Document session-scoped validity |
| Developer forgets cascade_field() | Medium | High | Lint rule suggestion in docs |

---

## Observability

### Metrics

| Metric | Description |
|--------|-------------|
| `bizmodel.track.duration_ms` | Time to track entity (with prefetch) |
| `bizmodel.cascade.duration_ms` | Time to execute cascade batch |
| `bizmodel.cascade.entity_count` | Number of entities updated per cascade |
| `bizmodel.prefetch.holder_count` | Number of holders prefetched |

### Logging

```python
logger.debug("track: entity=%s prefetch_holders=%s recursive=%s", gid, prefetch, recursive)
logger.debug("prefetch: entity=%s holders_found=%d", gid, len(holders))
logger.info("cascade: field=%s source=%s target_count=%d", field, source_gid, count)
logger.warning("cascade: partial_failure count=%d", len(failed))
```

### Alerting

- Alert if cascade_field() fails for >10% of entities in a batch
- Alert if prefetch takes >5 seconds (potential API issue)

---

## Testing Strategy

### Unit Testing (Phase 1-3)

| Component | Test Focus | Coverage Target |
|-----------|------------|-----------------|
| CascadingFieldDef | applies_to(), should_update_descendant() | 100% |
| InheritedFieldDef | resolve(), override detection | 100% |
| Business model | Field accessors, holder properties | >90% |
| Contact, Unit, Offer | Field accessors, navigation | >90% |
| Holder classes | _populate_children(), detection | >90% |

### Integration Testing

| Scenario | Test Focus |
|----------|------------|
| Full hierarchy creation | Create Business with all holders and children |
| Cascade execution | cascade_field() updates all descendants |
| Partial failure | Some cascade updates fail, others succeed |
| Prefetch flow | track() with prefetch_holders populates holders |
| Recursive tracking | track() with recursive tracks all descendants |

### Type Safety

```bash
mypy src/autom8_asana/models/business/ --strict
# Target: Zero type errors
```

---

## Interface Contracts Summary

### Public API Additions

```python
# models/business/__init__.py
from .business import Business
from .contact import Contact, ContactHolder
from .unit import Unit, UnitHolder
from .offer import Offer, OfferHolder
from .process import Process, ProcessHolder
from .location import Address, Hours, LocationHolder
from .fields import CascadingFieldDef, InheritedFieldDef

__all__ = [
    "Business",
    "Contact", "ContactHolder",
    "Unit", "UnitHolder",
    "Offer", "OfferHolder",
    "Process", "ProcessHolder",
    "Address", "Hours", "LocationHolder",
    "CascadingFieldDef", "InheritedFieldDef",
]
```

### SaveSession Extensions

```python
# persistence/session.py additions
def track(self, entity: T, *, prefetch_holders: bool = False, recursive: bool = False) -> T
def cascade_field(self, entity: AsanaResource, field_name: str, *, target_types: set[type] | None = None) -> SaveSession
async def prefetch_pending(self) -> None
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-11 | Architect | Initial draft |

---

## Quality Gates Checklist

- [x] Traces to approved PRD (PRD-BIZMODEL)
- [x] All significant decisions have ADRs (ADR-0050 to ADR-0054)
- [x] Component responsibilities are clear
- [x] Interfaces are defined
- [x] Complexity level is justified (Module)
- [x] Risks identified with mitigations
- [x] Implementation plan is actionable (3 phases)
- [x] All 5 open questions answered
- [x] ADR validation matrix complete
