# TDD: Business Model Hydration

## Metadata

- **TDD ID**: TDD-HYDRATION
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-16
- **Last Updated**: 2025-12-16
- **PRD Reference**: [PRD-HYDRATION](../requirements/PRD-HYDRATION.md)
- **Related TDDs**: TDD-BIZMODEL (Business Model Phase 1)
- **Related ADRs**:
  - [ADR-0050](../decisions/ADR-0050-holder-lazy-loading-strategy.md) - Holder Lazy Loading
  - [ADR-0052](../decisions/ADR-0052-bidirectional-reference-caching.md) - Bidirectional References
  - [ADR-0057](../decisions/ADR-0057-subtasks-async-method.md) - subtasks_async
  - [ADR-0068](../decisions/ADR-0068-type-detection-strategy.md) - Type Detection Strategy
  - [ADR-0069](../decisions/ADR-0069-hydration-api-design.md) - Hydration API Design
  - [ADR-0070](../decisions/ADR-0070-hydration-partial-failure.md) - Partial Failure Handling

## Overview

This TDD specifies the implementation of business model hierarchy hydration, enabling users to load complete Business hierarchies from any entry point (Business GID, Contact, Offer, etc.). The design completes the Phase 2 work by implementing stubbed `_fetch_holders_async()` methods and adding upward traversal capabilities.

## Requirements Summary

From PRD-HYDRATION:

| Priority | Requirement | Summary |
|----------|-------------|---------|
| P0 | FR-DOWN-001 to FR-DOWN-005 | Downward hydration from Business root |
| P1 | FR-UP-001 to FR-UP-005 | Upward traversal to find Business |
| P2 | FR-FULL-001 to FR-FULL-002 | Combined hydration from any entry |
| P2 | FR-API-001 to FR-API-003 | API surface methods |
| P0 | FR-ERROR-001 to FR-ERROR-004 | Error handling |
| P1 | NFR-PERF-001 to NFR-PERF-003 | Concurrent fetching, API efficiency |

## System Context

```
                              +-----------------+
                              |   Asana API     |
                              +--------+--------+
                                       |
                           +-----------+-----------+
                           |                       |
                   +-------v-------+       +-------v-------+
                   | TasksClient   |       | PageIterator  |
                   | - get_async   |       |               |
                   | - subtasks_   |       |               |
                   |   async       |       |               |
                   +-------+-------+       +---------------+
                           |
           +---------------+---------------+
           |               |               |
   +-------v-------+ +-----v-----+ +-------v-------+
   | Business      | | Unit      | | Hydration     |
   | .from_gid_    | | .to_      | | Module        |
   |  async()      | | business_ | | - traverse_up |
   | ._fetch_      | | async()   | | - detect_type |
   |  holders_     | |           | | - HydrationResult
   |  async()      | |           | |               |
   +---------------+ +-----------+ +---------------+
           |               |               |
           +-------+-------+---------------+
                   |
           +-------v-------+
           | Business      |
           | Hierarchy     |
           | (Hydrated)    |
           +---------------+
```

## Design

### Component Architecture

```
src/autom8_asana/models/business/
+-- __init__.py              # Exports HydrationResult, HydrationError
+-- base.py                  # BusinessEntity base (existing)
+-- business.py              # Business with _fetch_holders_async (modify)
+-- unit.py                  # Unit with _fetch_holders_async (modify)
+-- contact.py               # Contact with to_business_async (modify)
+-- offer.py                 # Offer with to_business_async (modify)
+-- detection.py             # NEW: Type detection (ADR-0068)
+-- hydration.py             # NEW: Hydration orchestration (ADR-0069, ADR-0070)

src/autom8_asana/exceptions.py
+-- HydrationError           # NEW: Hydration exception (ADR-0070)
```

| Component | Responsibility | Location |
|-----------|----------------|----------|
| `detection.py` | Type detection from Task | `models/business/detection.py` |
| `hydration.py` | Orchestrate up/down hydration | `models/business/hydration.py` |
| `Business._fetch_holders_async` | Downward hydration entry | `models/business/business.py` |
| `Unit._fetch_holders_async` | Nested holder hydration | `models/business/unit.py` |
| `Contact.to_business_async` | Upward + hydration | `models/business/contact.py` |
| `Offer.to_business_async` | Upward + hydration | `models/business/offer.py` |
| `HydrationError` | Failure exception | `exceptions.py` |
| `HydrationResult` | Result container | `models/business/hydration.py` |

### Data Model

#### EntityType Enum

```python
# detection.py
from enum import Enum

class EntityType(Enum):
    """Types of entities in the business model hierarchy."""
    BUSINESS = "business"
    CONTACT_HOLDER = "contact_holder"
    UNIT_HOLDER = "unit_holder"
    LOCATION_HOLDER = "location_holder"
    DNA_HOLDER = "dna_holder"
    RECONCILIATIONS_HOLDER = "reconciliations_holder"
    ASSET_EDIT_HOLDER = "asset_edit_holder"
    VIDEOGRAPHY_HOLDER = "videography_holder"
    UNIT = "unit"
    OFFER_HOLDER = "offer_holder"
    PROCESS_HOLDER = "process_holder"
    CONTACT = "contact"
    OFFER = "offer"
    PROCESS = "process"
    LOCATION = "location"
    HOURS = "hours"
    UNKNOWN = "unknown"
```

#### HydrationResult Dataclass

```python
# hydration.py
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class HydrationBranch:
    """A successfully hydrated branch."""
    holder_type: str
    holder_gid: str
    child_count: int

@dataclass
class HydrationFailure:
    """A branch that failed to hydrate."""
    holder_type: str
    holder_gid: str | None
    phase: Literal["downward", "upward"]
    error: Exception
    recoverable: bool

@dataclass
class HydrationResult:
    """Complete result of hydration operation."""
    business: Business
    entry_entity: BusinessEntity | None = None
    entry_type: EntityType | None = None
    path: list[BusinessEntity] = field(default_factory=list)
    api_calls: int = 0
    succeeded: list[HydrationBranch] = field(default_factory=list)
    failed: list[HydrationFailure] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """True if hydration completed with no failures."""
        return len(self.failed) == 0
```

#### HydrationError Exception

```python
# exceptions.py
class HydrationError(AsanaError):
    """Hydration operation failed."""

    def __init__(
        self,
        message: str,
        *,
        entity_gid: str,
        entity_type: str | None = None,
        phase: Literal["downward", "upward"],
        partial_result: HydrationResult | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.entity_gid = entity_gid
        self.entity_type = entity_type
        self.phase = phase
        self.partial_result = partial_result
        self.__cause__ = cause
```

### API Contracts

#### Business.from_gid_async (Enhanced)

```python
class Business(BusinessEntity):
    @classmethod
    async def from_gid_async(
        cls,
        client: AsanaClient,
        gid: str,
        *,
        hydrate: bool = True,
        partial_ok: bool = False,
    ) -> Business | HydrationResult:
        """Load Business from GID with optional hierarchy hydration.

        Args:
            client: AsanaClient for API calls.
            gid: Business task GID.
            hydrate: If True (default), load full hierarchy.
            partial_ok: If True, return HydrationResult even on partial failure.

        Returns:
            Business if partial_ok=False and successful.
            HydrationResult if partial_ok=True.

        Raises:
            HydrationError: If hydration fails and partial_ok=False.
            NotFoundError: If Business GID does not exist.
        """
```

#### Contact.to_business_async (New)

```python
class Contact(BusinessEntity):
    async def to_business_async(
        self,
        client: AsanaClient,
        *,
        hydrate_full: bool = True,
        partial_ok: bool = False,
    ) -> Business | HydrationResult:
        """Navigate to containing Business and hydrate.

        Path: Contact -> ContactHolder -> Business

        Args:
            client: AsanaClient for API calls.
            hydrate_full: If True, hydrate full Business hierarchy.
            partial_ok: If True, return HydrationResult on partial failure.

        Returns:
            Business or HydrationResult depending on partial_ok.

        Raises:
            HydrationError: If traversal fails and partial_ok=False.
        """
```

#### Offer.to_business_async (New)

```python
class Offer(BusinessEntity):
    async def to_business_async(
        self,
        client: AsanaClient,
        *,
        hydrate_full: bool = True,
        partial_ok: bool = False,
    ) -> Business | HydrationResult:
        """Navigate to containing Business and hydrate.

        Path: Offer -> OfferHolder -> Unit -> UnitHolder -> Business

        Args:
            client: AsanaClient for API calls.
            hydrate_full: If True, hydrate full Business hierarchy.
            partial_ok: If True, return HydrationResult on partial failure.

        Returns:
            Business or HydrationResult depending on partial_ok.
        """
```

#### hydrate_from_gid_async (Generic Entry)

```python
# hydration.py
async def hydrate_from_gid_async(
    client: AsanaClient,
    gid: str,
    *,
    hydrate_full: bool = True,
    partial_ok: bool = False,
) -> HydrationResult:
    """Hydrate business hierarchy from any task GID.

    Detects entity type, traverses upward to Business if needed,
    then optionally hydrates full hierarchy downward.

    Args:
        client: AsanaClient for API calls.
        gid: Any task GID in the business hierarchy.
        hydrate_full: If True, hydrate full hierarchy after finding Business.
        partial_ok: If True, continue on partial failures.

    Returns:
        HydrationResult with business and metadata.

    Raises:
        HydrationError: If hydration fails and partial_ok=False.
    """
```

### Data Flow

#### Downward Hydration Sequence

```
Business.from_gid_async(client, gid)
    |
    v
get_async(gid) --> Business task
    |
    v
_fetch_holders_async(client)
    |
    v (concurrent via asyncio.gather)
+--------------------------+
| subtasks_async(business) |
| --> [ContactHolder,      |
|      UnitHolder,         |
|      LocationHolder,     |
|      ...]                |
+--------------------------+
    |
    v
_populate_holders(subtasks)
    |
    v (concurrent per holder type)
+-----------------------------------+
| For each typed holder:            |
|   subtasks_async(holder.gid)      |
|   --> [children]                  |
|   holder._populate_children()     |
+-----------------------------------+
    |
    v (for UnitHolder children)
+-----------------------------------+
| For each Unit:                    |
|   unit._fetch_holders_async()     |
|   --> OfferHolder, ProcessHolder  |
|   --> Offers, Processes           |
+-----------------------------------+
    |
    v
Return hydrated Business
```

#### Upward Traversal Sequence

```
contact.to_business_async(client)
    |
    v
_traverse_upward_async(contact, client)
    |
    v
+-----------------------------------+
| parent_gid = contact.parent.gid   |
| parent = get_async(parent_gid)    |
| type = detect_entity_type(parent) |
|   --> ContactHolder               |
+-----------------------------------+
    |
    v
+-----------------------------------+
| parent_gid = holder.parent.gid    |
| parent = get_async(parent_gid)    |
| type = detect_entity_type(parent) |
|   --> Business (name detection    |
|       fails, structure fallback)  |
+-----------------------------------+
    |
    v
business = Business.model_validate(parent)
    |
    v (if hydrate_full=True)
business._fetch_holders_async(client)
    |
    v
Return hydrated Business with self in hierarchy
```

### Algorithm Design

#### Downward Hydration Algorithm

```python
async def _fetch_holders_async(self, client: AsanaClient) -> None:
    """Fetch and populate all holder subtasks with their children.

    Algorithm:
    1. Fetch Business subtasks (holders)
    2. Identify and type each holder
    3. Concurrently fetch each holder's children
    4. For Unit children, recursively fetch nested holders
    5. Set all bidirectional references
    """
    # Step 1: Fetch Business subtasks
    holder_tasks = await client.tasks.subtasks_async(self.gid).collect()

    # Step 2: Populate typed holders
    self._populate_holders(holder_tasks)

    # Step 3: Concurrent child fetching for each populated holder
    fetch_tasks = []

    if self._contact_holder:
        fetch_tasks.append(self._fetch_holder_children(
            client, self._contact_holder, "_contacts"
        ))

    if self._unit_holder:
        fetch_tasks.append(self._fetch_unit_holder_children(client))

    if self._location_holder:
        fetch_tasks.append(self._fetch_holder_children(
            client, self._location_holder, "_children"
        ))

    # Stub holders (DNA, Reconciliations, etc.)
    for holder in [self._dna_holder, self._reconciliations_holder,
                   self._asset_edit_holder, self._videography_holder]:
        if holder:
            fetch_tasks.append(self._fetch_holder_children(
                client, holder, "_children"
            ))

    # Execute all fetches concurrently
    await asyncio.gather(*fetch_tasks)


async def _fetch_unit_holder_children(self, client: AsanaClient) -> None:
    """Fetch Units and their nested holders."""
    if not self._unit_holder:
        return

    # Fetch Unit subtasks
    unit_tasks = await client.tasks.subtasks_async(self._unit_holder.gid).collect()
    self._unit_holder._populate_children(unit_tasks)

    # Recursively fetch each Unit's holders
    unit_fetch_tasks = [
        unit._fetch_holders_async(client)
        for unit in self._unit_holder.units
    ]
    await asyncio.gather(*unit_fetch_tasks)


async def _fetch_holder_children(
    self,
    client: AsanaClient,
    holder: Task,
    children_attr: str,
) -> None:
    """Fetch children for a holder and populate them."""
    subtasks = await client.tasks.subtasks_async(holder.gid).collect()
    holder._populate_children(subtasks)
```

#### Upward Traversal Algorithm

```python
async def _traverse_upward_async(
    entity: Task,
    client: AsanaClient,
    max_depth: int = 10,
) -> tuple[Business, list[BusinessEntity]]:
    """Walk parent chain to find Business root.

    Algorithm:
    1. Start with entity, initialize visited set
    2. Get parent GID from entity.parent
    3. Fetch parent task
    4. Detect parent type
    5. If Business, return
    6. Otherwise, add to path and continue
    7. Safety: abort if depth > max_depth or cycle detected

    Returns:
        (Business, path) where path is entities traversed
    """
    visited: set[str] = {entity.gid}
    path: list[BusinessEntity] = []
    current = entity
    depth = 0

    while depth < max_depth:
        # Check for parent
        if current.parent is None:
            raise HydrationError(
                f"Reached root without finding Business",
                entity_gid=entity.gid,
                phase="upward",
            )

        parent_gid = current.parent.gid

        # Cycle detection
        if parent_gid in visited:
            raise HydrationError(
                f"Cycle detected: {parent_gid} already visited",
                entity_gid=entity.gid,
                phase="upward",
            )
        visited.add(parent_gid)

        # Fetch parent
        parent_task = await client.tasks.get_async(parent_gid)

        # Detect type
        entity_type = await detect_entity_type_async(parent_task, client)

        if entity_type == EntityType.BUSINESS:
            business = Business.model_validate(parent_task.model_dump())
            return business, path

        # Convert to typed entity and continue
        typed_entity = _convert_to_typed(parent_task, entity_type)
        path.append(typed_entity)
        current = parent_task
        depth += 1

    raise HydrationError(
        f"Max traversal depth ({max_depth}) exceeded",
        entity_gid=entity.gid,
        phase="upward",
    )
```

#### Type Detection Algorithm

```python
# detection.py

HOLDER_NAME_MAP: dict[str, EntityType] = {
    "contacts": EntityType.CONTACT_HOLDER,
    "units": EntityType.UNIT_HOLDER,
    "offers": EntityType.OFFER_HOLDER,
    "processes": EntityType.PROCESS_HOLDER,
    "location": EntityType.LOCATION_HOLDER,
    "dna": EntityType.DNA_HOLDER,
    "reconciliations": EntityType.RECONCILIATIONS_HOLDER,
    "asset edit": EntityType.ASSET_EDIT_HOLDER,
    "videography": EntityType.VIDEOGRAPHY_HOLDER,
}


def detect_by_name(name: str | None) -> EntityType | None:
    """Detect entity type by name (sync, no API call)."""
    if name is None:
        return None

    name_lower = name.lower().strip()

    if name_lower in HOLDER_NAME_MAP:
        return HOLDER_NAME_MAP[name_lower]

    return None


async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
) -> EntityType:
    """Detect entity type with structure fallback.

    1. Try name-based detection (fast path)
    2. Fall back to structure inspection (fetch subtasks)
    """
    # Fast path: name detection
    if detected := detect_by_name(task.name):
        return detected

    # Slow path: structure inspection
    subtasks = await client.tasks.subtasks_async(task.gid).collect()
    subtask_names = {s.name.lower() for s in subtasks if s.name}

    # Business has holder subtasks
    business_indicators = {"contacts", "units", "location"}
    if subtask_names & business_indicators:
        return EntityType.BUSINESS

    # Unit has offer/process holder subtasks
    unit_indicators = {"offers", "processes"}
    if subtask_names & unit_indicators:
        return EntityType.UNIT

    return EntityType.UNKNOWN
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Type detection strategy | Name-based with structure fallback | Zero API calls for holders, fallback handles Business/Unit | ADR-0068 |
| API surface | Both instance and factory methods | Matches SDK patterns, ergonomic for all use cases | ADR-0069 |
| Partial failure handling | HydrationResult with opt-in | Follows SaveResult pattern, fail-fast by default | ADR-0070 |
| Concurrent fetching | Within-level only | Balances speed with predictability | NFR-PERF-001 |
| Max traversal depth | 10 levels | Safety limit, actual max is ~5 levels | FR-ERROR-004 |

## Complexity Assessment

**Level**: Module

**Justification**:
- Clear API surface (3 factory methods, 2 instance methods)
- Isolated components (detection, hydration, entity methods)
- No external service dependencies beyond existing TasksClient
- Testable in isolation with mocked client

This is NOT Service-level because:
- No independent deployment
- No new external integrations
- No new data storage requirements
- All code lives within existing business model package

## Implementation Plan

### Phase 1: P0 Downward Hydration (Session 4)

| Task | Deliverable | Dependencies | Estimate |
|------|-------------|--------------|----------|
| 1.1 | `HydrationError` in exceptions.py | None | 0.5h |
| 1.2 | `detection.py` module | None | 1h |
| 1.3 | `Business._fetch_holders_async()` | 1.1, 1.2 | 2h |
| 1.4 | `Unit._fetch_holders_async()` | 1.3 | 1h |
| 1.5 | `Business.from_gid_async()` enhancement | 1.3, 1.4 | 1h |
| 1.6 | Unit tests for downward hydration | 1.5 | 2h |

**Exit Criteria**:
- `Business.from_gid_async(client, gid)` returns fully hydrated Business
- All holder children populated (Contacts, Units, Offers, Processes, Locations)
- Bidirectional references set correctly
- Unit tests passing

### Phase 2: P1 Upward Traversal (Session 5)

| Task | Deliverable | Dependencies | Estimate |
|------|-------------|--------------|----------|
| 2.1 | `_traverse_upward_async()` in hydration.py | P1 complete | 2h |
| 2.2 | `Contact.to_business_async()` | 2.1 | 1h |
| 2.3 | `Offer.to_business_async()` | 2.1 | 1h |
| 2.4 | `Unit.to_business_async()` | 2.1 | 0.5h |
| 2.5 | Unit tests for upward traversal | 2.2, 2.3, 2.4 | 2h |

**Exit Criteria**:
- `contact.to_business_async(client)` returns hydrated Business
- `offer.to_business_async(client)` returns hydrated Business
- Entry entity is findable within hydrated hierarchy
- Unit tests passing

### Phase 3: P2 Combined Hydration + HydrationResult (Session 6)

| Task | Deliverable | Dependencies | Estimate |
|------|-------------|--------------|----------|
| 3.1 | `HydrationResult`, `HydrationBranch`, `HydrationFailure` | P2 complete | 1h |
| 3.2 | `hydrate_from_gid_async()` generic entry | 3.1 | 2h |
| 3.3 | `partial_ok` parameter support | 3.1, 3.2 | 1.5h |
| 3.4 | Integration tests | 3.3 | 2h |

**Exit Criteria**:
- `hydrate_from_gid_async(client, any_gid)` works from any hierarchy level
- `partial_ok=True` returns HydrationResult with failure details
- Integration tests with mocked failures passing

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| API rate limits during hydration | High | Medium | Concurrent within-level only, respect existing rate limiting |
| Type detection heuristics fail | Medium | Low | Structure fallback handles edge cases, log warnings |
| Circular parent references | High | Very Low | Visited set tracking, max depth limit |
| Partial hydration leaves inconsistent references | Medium | Medium | Default fail-fast, partial_ok is explicit opt-in |
| Performance regression for large hierarchies | Medium | Low | Benchmark in integration tests, add logging |

## Observability

### Metrics

- `hydration.duration_ms` - Total hydration time
- `hydration.api_calls` - Number of API calls per hydration
- `hydration.partial_failures` - Count of partial failure events

### Logging

```python
# On hydration start
logger.info("Starting hydration", extra={
    "entry_gid": gid,
    "entry_type": detected_type.value,
})

# On hydration complete
logger.info("Hydration complete", extra={
    "business_gid": business.gid,
    "api_calls": result.api_calls,
    "is_complete": result.is_complete,
    "duration_ms": duration_ms,
})

# On partial failure
logger.warning("Hydration partial failure", extra={
    "business_gid": business.gid,
    "failed_holders": [f.holder_type for f in result.failed],
})
```

### Alerting

- Alert if `hydration.partial_failures` > 10/hour (may indicate API issues)
- Alert if `hydration.duration_ms` p95 > 30s (performance degradation)

## Testing Strategy

### Unit Testing

- **detection.py**: Test each EntityType detection path
  - Name-based detection for all holder types
  - Structure fallback for Business detection
  - Structure fallback for Unit detection
  - Unknown type handling

- **hydration.py**: Test orchestration logic
  - HydrationResult construction
  - Path tracking during traversal
  - API call counting
  - Cycle detection

- **Business._fetch_holders_async()**: Mock TasksClient
  - All 7 holder types populated
  - Nested Unit holders populated
  - Bidirectional references correct
  - Empty holders handled

- **Entity.to_business_async()**: Mock parent chain
  - Contact -> ContactHolder -> Business
  - Offer -> OfferHolder -> Unit -> UnitHolder -> Business
  - Max depth exceeded error

### Integration Testing

- **Full downward hydration**: Real or realistic mock data
  - Business with all entity types
  - Multiple Units with Offers/Processes
  - Verify navigation works end-to-end

- **Upward + downward**: Start from Contact, verify full hierarchy

- **Partial failure simulation**: Mock one holder fetch to fail
  - Verify other branches succeed
  - Verify HydrationResult.failed populated

### Performance Testing

- Benchmark hydration of "typical" Business (5 Contacts, 3 Units, 10 Offers)
- Target: < 30 API calls
- Target: < 5s total time with mocked latency

## Open Questions

All questions from PRD have been resolved:

| Question | Resolution | ADR |
|----------|------------|-----|
| Q1: Type detection strategy | Name-based with structure fallback | ADR-0068 |
| Q2: Instance vs factory method | Both | ADR-0069 |
| Q3: Concurrent fetching strategy | Within-level only | NFR-PERF-001 |
| Q4: Partial failure handling | HydrationResult with opt-in | ADR-0070 |
| Q5: API location | Entity methods + factory methods | ADR-0069 |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Architect | Initial TDD based on PRD-HYDRATION |

## Appendix: Hierarchy Depth Reference

```
Business (Level 0)
  |
  +-- ContactHolder (Level 1)
  |     +-- Contact (Level 2)
  |
  +-- UnitHolder (Level 1)
  |     +-- Unit (Level 2)
  |           +-- OfferHolder (Level 3)
  |           |     +-- Offer (Level 4)
  |           +-- ProcessHolder (Level 3)
  |                 +-- Process (Level 4)
  |
  +-- LocationHolder (Level 1)
  |     +-- Location (Level 2)
  |     +-- Hours (Level 2)
  |
  +-- DNAHolder (Level 1)
  +-- ReconciliationsHolder (Level 1)
  +-- AssetEditHolder (Level 1)
  +-- VideographyHolder (Level 1)

Maximum downward depth: 4 levels (Business -> UnitHolder -> Unit -> OfferHolder -> Offer)
Maximum upward depth: 4 levels (Offer -> OfferHolder -> Unit -> UnitHolder -> Business)
```

## Appendix: API Call Analysis

### Downward Hydration (Typical Business)

```
1x get_async(business_gid)           = 1 call
1x subtasks_async(business)          = 1 call (returns 7 holders)
7x subtasks_async(holder)            = 7 calls (one per holder)
   - ContactHolder -> 5 Contacts
   - UnitHolder -> 3 Units
   - LocationHolder -> 1 Location, 1 Hours
   - DNA/Recon/Asset/Video -> few each
3x subtasks_async(unit)              = 3 calls (one per Unit)
3x subtasks_async(offer_holder)      = 3 calls
3x subtasks_async(process_holder)    = 3 calls
-----------------------------------------
Total: ~19 API calls for typical Business
```

### Upward Traversal (Offer to Business)

```
1x get_async(offer.parent)           = 1 call (OfferHolder)
1x get_async(offer_holder.parent)    = 1 call (Unit)
1x subtasks_async(unit) [detection]  = 1 call (confirms Unit type)
1x get_async(unit.parent)            = 1 call (UnitHolder)
1x get_async(unit_holder.parent)     = 1 call (Business)
1x subtasks_async(business) [detect] = 1 call (confirms Business type)
-----------------------------------------
Total: 6 API calls for upward traversal
```

**Combined (Offer entry, full hydration)**: ~25 API calls

## Quality Gates Checklist

- [x] Traces to approved PRD (PRD-HYDRATION)
- [x] All significant decisions have ADRs (ADR-0068, ADR-0069, ADR-0070)
- [x] Component responsibilities are clear
- [x] Interfaces are defined (API signatures with types)
- [x] Complexity level is justified (Module level)
- [x] Risks identified with mitigations
- [x] Implementation plan is actionable (3 phases with estimates)
