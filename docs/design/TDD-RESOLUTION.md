# TDD: Cross-Holder Relationship Resolution

## Metadata

- **TDD ID**: TDD-RESOLUTION
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-16
- **Last Updated**: 2025-12-16
- **PRD Reference**: [PRD-RESOLUTION](/docs/requirements/PRD-RESOLUTION.md)
- **Related TDDs**: TDD-BIZMODEL (Business Model), TDD-HYDRATION (Hydration)
- **Related ADRs**: ADR-0071 (Ambiguity Handling), ADR-0072 (Resolution Caching), ADR-0073 (Batch Resolution API), ADR-0052 (Bidirectional References)

---

## Overview

This design enables AssetEdit entities to resolve their owning Unit and Offer across the business model hierarchy using configurable resolution strategies. The solution introduces a typed AssetEdit entity extending Process, a ResolutionResult generic type for transparent results, and a strategy pattern for pluggable resolution algorithms (DEPENDENT_TASKS, CUSTOM_FIELD_MAPPING, EXPLICIT_OFFER_ID, AUTO).

---

## Requirements Summary

Per PRD-RESOLUTION, the core requirements are:

- **FR-PREREQ-001**: AssetEdit entity with 11 typed field accessors
- **FR-PREREQ-002**: AssetEditHolder returns typed AssetEdit children
- **FR-PREREQ-003**: TasksClient.dependents_async() method
- **FR-RESOLVE-001/002**: resolve_unit_async() and resolve_offer_async() methods
- **FR-RESOLVE-003**: ResolutionResult[T] generic type with strategy transparency
- **FR-STRATEGY-001 through FR-STRATEGY-005**: Resolution strategy enum and implementations
- **FR-BATCH-001/002**: Batch resolution for collections

See [PRD-RESOLUTION](/docs/requirements/PRD-RESOLUTION.md) for full requirement details.

---

## System Context

```
                                    +------------------------+
                                    |      AsanaClient       |
                                    | (tasks.get_async,      |
                                    |  tasks.dependents_async)|
                                    +------------------------+
                                              |
                                              v
+------------------+    resolve     +-------------------+
|   AssetEdit      |--------------->|  Resolution       |
| (extends Process)|                |  Module           |
| - 11 typed fields|                | - strategies      |
| - resolve_unit() |                | - batch helpers   |
| - resolve_offer()|                +-------------------+
+------------------+                          |
        |                                     |
        v                                     v
+------------------+                +-------------------+
| Business Model   |                | ResolutionResult  |
| - Business       |<---------------|  [T]              |
| - Unit           |    returns     | - entity          |
| - Offer          |                | - strategy_used   |
+------------------+                | - candidates      |
                                    +-------------------+
```

### Integration Points

1. **AssetEdit entity**: New file extending Process with typed field accessors
2. **AssetEditHolder**: Updated to return typed AssetEdit children
3. **TasksClient**: New dependents_async() method following subtasks_async() pattern
4. **Resolution module**: New module with ResolutionStrategy enum, ResolutionResult type, and strategy implementations
5. **Exceptions**: New ResolutionError exception class

---

## Design

### Component Architecture

```
src/autom8_asana/
+-- models/
|   +-- business/
|       +-- asset_edit.py          # NEW: AssetEdit entity
|       +-- resolution.py          # NEW: Resolution types and strategies
|       +-- business.py            # MODIFIED: AssetEditHolder update
+-- clients/
|   +-- tasks.py                   # MODIFIED: dependents_async()
+-- exceptions.py                  # MODIFIED: ResolutionError
```

| Component | Responsibility | Location |
|-----------|----------------|----------|
| AssetEdit | Typed entity with 11 field accessors and resolution methods | `models/business/asset_edit.py` |
| ResolutionStrategy | Enum defining available strategies with priority order | `models/business/resolution.py` |
| ResolutionResult[T] | Generic dataclass for resolution outcomes | `models/business/resolution.py` |
| Strategy implementations | Pluggable resolution algorithms | `models/business/resolution.py` |
| Batch helpers | Efficient collection resolution | `models/business/resolution.py` |
| AssetEditHolder | Updated holder returning typed children | `models/business/business.py` |
| TasksClient.dependents_async | API method for fetching task dependents | `clients/tasks.py` |

---

### Data Model

#### AssetEdit Entity

```python
class AssetEdit(Process):
    """AssetEdit entity extending Process with 11 typed field accessors.

    Hierarchy:
        Business
            +-- AssetEditHolder
                  +-- AssetEdit (this entity)

    Resolution:
        AssetEdit is NOT in the Unit/Offer containment hierarchy.
        It must resolve to Unit/Offer via resolution strategies.
    """

    NAME_CONVENTION: ClassVar[str] = "[AssetEdit Name]"

    # Private cached references (ADR-0052)
    _asset_edit_holder: AssetEditHolder | None = PrivateAttr(default=None)

    class Fields:
        """Custom field name constants for IDE discoverability."""
        ASSET_APPROVAL = "Asset Approval"
        ASSET_ID = "Asset ID"
        EDITOR = "Editor"
        REVIEWER = "Reviewer"
        OFFER_ID = "Offer ID"
        RAW_ASSETS = "Raw Assets"
        REVIEW_ALL_ADS = "Review All Ads"
        SCORE = "Score"
        SPECIALTY = "Specialty"
        TEMPLATE_ID = "Template ID"
        VIDEOS_PAID = "Videos Paid"

    # --- Typed Field Accessors (11 fields) ---

    @property
    def asset_approval(self) -> str | None:
        """Asset approval status (enum custom field)."""
        return self._get_enum_field(self.Fields.ASSET_APPROVAL)

    @property
    def asset_id(self) -> str | None:
        """Asset identifier (text custom field)."""
        return self._get_text_field(self.Fields.ASSET_ID)

    @property
    def editor(self) -> list[dict[str, Any]]:
        """Editor users (people custom field)."""
        value = self.get_custom_fields().get(self.Fields.EDITOR)
        return value if isinstance(value, list) else []

    @property
    def reviewer(self) -> list[dict[str, Any]]:
        """Reviewer users (people custom field)."""
        value = self.get_custom_fields().get(self.Fields.REVIEWER)
        return value if isinstance(value, list) else []

    @property
    def offer_id(self) -> str | None:
        """Explicit offer ID reference (text custom field).

        Key field for EXPLICIT_OFFER_ID resolution strategy.
        Contains the GID of the associated Offer task.
        """
        return self._get_text_field(self.Fields.OFFER_ID)

    @property
    def raw_assets(self) -> str | None:
        """Raw assets link/text (text custom field)."""
        return self._get_text_field(self.Fields.RAW_ASSETS)

    @property
    def review_all_ads(self) -> bool | None:
        """Review all ads flag (enum mapped to bool).

        Returns True if enum value is "Yes", False if "No", None otherwise.
        """
        value = self._get_enum_field(self.Fields.REVIEW_ALL_ADS)
        if value is None:
            return None
        return value.lower() == "yes"

    @property
    def score(self) -> Decimal | None:
        """Score value (number custom field)."""
        return self._get_number_field(self.Fields.SCORE)

    @property
    def specialty(self) -> str | None:
        """Specialty type (enum custom field)."""
        return self._get_enum_field(self.Fields.SPECIALTY)

    @property
    def template_id(self) -> str | None:
        """Template identifier (text custom field)."""
        return self._get_text_field(self.Fields.TEMPLATE_ID)

    @property
    def videos_paid(self) -> int | None:
        """Number of videos paid (number custom field)."""
        return self._get_int_field(self.Fields.VIDEOS_PAID)

    # --- Resolution Methods ---

    async def resolve_unit_async(
        self,
        client: AsanaClient,
        *,
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
    ) -> ResolutionResult[Unit]:
        """Resolve to owning Unit using configured strategy."""
        ...

    async def resolve_offer_async(
        self,
        client: AsanaClient,
        *,
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
    ) -> ResolutionResult[Offer]:
        """Resolve to owning Offer using configured strategy."""
        ...
```

#### ResolutionStrategy Enum

```python
class ResolutionStrategy(str, Enum):
    """Available resolution strategies with priority ordering.

    Priority order (for AUTO mode):
    1. DEPENDENT_TASKS - Most reliable, domain-specific relationship
    2. CUSTOM_FIELD_MAPPING - Vertical field matching
    3. EXPLICIT_OFFER_ID - Direct ID reference

    AUTO executes strategies in priority order until one succeeds.
    """

    DEPENDENT_TASKS = "dependent_tasks"
    CUSTOM_FIELD_MAPPING = "custom_field_mapping"
    EXPLICIT_OFFER_ID = "explicit_offer_id"
    AUTO = "auto"

    @classmethod
    def priority_order(cls) -> list[ResolutionStrategy]:
        """Return strategies in priority order (for AUTO mode)."""
        return [
            cls.DEPENDENT_TASKS,
            cls.CUSTOM_FIELD_MAPPING,
            cls.EXPLICIT_OFFER_ID,
        ]
```

#### ResolutionResult[T] Generic Type

```python
from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T", bound="BusinessEntity")

@dataclass
class ResolutionResult(Generic[T]):
    """Result of a resolution operation with strategy transparency.

    Per FR-RESOLVE-003: Provides full transparency about resolution path.
    Per ADR-0071: Ambiguous results return first match in entity field.

    Attributes:
        entity: Resolved entity or None if not found. If ambiguous, contains
               first match for convenience (caller can check candidates).
        strategy_used: Strategy that produced the result (None if all failed).
        strategies_tried: All strategies attempted in order.
        ambiguous: True if multiple matches were found.
        candidates: All matching entities (populated if ambiguous or for debugging).
        error: Error message if resolution failed.

    Properties:
        success: True if exactly one match found (entity set, not ambiguous).
    """

    entity: T | None = None
    strategy_used: ResolutionStrategy | None = None
    strategies_tried: list[ResolutionStrategy] = field(default_factory=list)
    ambiguous: bool = False
    candidates: list[T] = field(default_factory=list)
    error: str | None = None

    @property
    def success(self) -> bool:
        """True if resolution succeeded with exactly one match.

        Returns False if:
        - No entity found (entity is None)
        - Multiple matches found (ambiguous is True)
        """
        return self.entity is not None and not self.ambiguous
```

---

### API Contracts

#### AssetEdit Resolution Methods

```python
# Instance methods on AssetEdit

async def resolve_unit_async(
    self,
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> ResolutionResult[Unit]:
    """Resolve AssetEdit to its owning Unit.

    Args:
        client: AsanaClient for API calls.
        strategy: Resolution strategy to use (default: AUTO).

    Returns:
        ResolutionResult containing:
        - entity: Resolved Unit or None
        - strategy_used: Which strategy succeeded
        - ambiguous: True if multiple Units matched
        - candidates: All matching Units

    Raises:
        ResolutionError: On unrecoverable failures (not ambiguity).

    Example:
        result = await asset_edit.resolve_unit_async(client)
        if result.success:
            unit = result.entity
            print(f"Resolved via {result.strategy_used}")
        elif result.ambiguous:
            print(f"Multiple matches: {result.candidates}")
    """

async def resolve_offer_async(
    self,
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> ResolutionResult[Offer]:
    """Resolve AssetEdit to its owning Offer via Unit.

    First resolves to Unit, then matches Offer within Unit.
    For EXPLICIT_OFFER_ID strategy, fetches Offer directly.

    Args:
        client: AsanaClient for API calls.
        strategy: Resolution strategy to use (default: AUTO).

    Returns:
        ResolutionResult containing resolved Offer or None.

    Raises:
        ResolutionError: On unrecoverable failures.
    """
```

#### TasksClient.dependents_async()

```python
def dependents_async(
    self,
    task_gid: str,
    *,
    opt_fields: list[str] | None = None,
    limit: int = 100,
) -> PageIterator[Task]:
    """List dependent tasks with automatic pagination.

    Per FR-PREREQ-003: Follows subtasks_async() pattern.

    A dependent task is one that depends on this task (inverse of dependency).
    Asana limits combined dependents+dependencies to 30.

    Args:
        task_gid: GID of the task to get dependents for.
        opt_fields: Fields to include in response.
        limit: Number of items per page (default 100, max 100).

    Returns:
        PageIterator[Task] - async iterator over dependent Task objects.

    Example:
        async for dependent in client.tasks.dependents_async(task_gid):
            print(dependent.name)
    """
```

#### Batch Resolution Functions

```python
# Module-level functions in resolution.py

async def resolve_units_async(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Unit]]:
    """Batch resolve multiple AssetEdits to Units.

    Per FR-BATCH-001: Optimizes shared lookups.
    Per ADR-0073: Module function for batch operations.

    Args:
        asset_edits: Collection of AssetEdit entities to resolve.
        client: AsanaClient for API calls.
        strategy: Resolution strategy to use for all.

    Returns:
        Dict mapping asset_edit.gid to ResolutionResult[Unit].
        Every input AssetEdit has an entry (even if resolution failed).

    Example:
        results = await resolve_units_async(asset_edits, client)
        for ae in asset_edits:
            result = results[ae.gid]
            if result.success:
                print(f"{ae.name} -> {result.entity.name}")
    """

async def resolve_offers_async(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Offer]]:
    """Batch resolve multiple AssetEdits to Offers.

    Per FR-BATCH-002: Builds on resolve_units_async for efficiency.

    Args:
        asset_edits: Collection of AssetEdit entities to resolve.
        client: AsanaClient for API calls.
        strategy: Resolution strategy to use for all.

    Returns:
        Dict mapping asset_edit.gid to ResolutionResult[Offer].
    """
```

---

### Data Flow

#### Single Resolution Flow (AUTO Strategy)

```
AssetEdit.resolve_unit_async(client, strategy=AUTO)
    |
    v
[1. DEPENDENT_TASKS Strategy]
    |-- Call client.tasks.dependents_async(self.gid).collect()
    |-- For each dependent:
    |       Check if it's a Unit or belongs to Unit hierarchy
    |-- Result: Unit found?
           +-- YES (single) --> Return ResolutionResult(entity=Unit, strategy_used=DEPENDENT_TASKS)
           +-- YES (multiple) --> Mark ambiguous, continue to next strategy
           +-- NO/Error --> Continue to next strategy
    v
[2. CUSTOM_FIELD_MAPPING Strategy]
    |-- Read self.vertical (inherited from Process)
    |-- If no vertical set --> Continue to next strategy
    |-- Check self.business (from AssetEditHolder._business)
    |       If None --> Error (Business context required)
    |-- Iterate business.units, find matching vertical
    |-- Result: Unit found?
           +-- YES (single) --> Return ResolutionResult(entity=Unit, strategy_used=CUSTOM_FIELD_MAPPING)
           +-- YES (multiple) --> Mark ambiguous, continue
           +-- NO --> Continue to next strategy
    v
[3. EXPLICIT_OFFER_ID Strategy]
    |-- Read self.offer_id
    |-- If empty --> Continue (no more strategies)
    |-- Fetch Offer: client.tasks.get_async(offer_id)
    |       If NotFoundError --> Log warning, continue
    |-- Navigate: offer.unit (may need hydration)
    |-- Result: Unit found?
           +-- YES --> Return ResolutionResult(entity=Unit, strategy_used=EXPLICIT_OFFER_ID)
           +-- NO --> Continue
    v
[All Strategies Exhausted]
    |-- If any ambiguous result was found:
    |       Return ResolutionResult(entity=first_match, ambiguous=True, candidates=[...])
    |-- Otherwise:
            Return ResolutionResult(entity=None, error="No matching entity found")
```

#### Batch Resolution Flow

```
resolve_units_async(asset_edits, client, strategy=AUTO)
    |
    v
[1. Group by Business]
    |-- Identify unique Businesses from asset_edits
    |-- For each Business: ensure units are hydrated (single fetch)
    |
    v
[2. Pre-fetch Shared Data]
    |-- If using DEPENDENT_TASKS:
    |       Fetch dependents for all AssetEdits concurrently
    |-- If using CUSTOM_FIELD_MAPPING:
    |       Business.units already available from step 1
    |-- If using EXPLICIT_OFFER_ID:
    |       Batch fetch unique offer_ids
    |
    v
[3. Resolve Each AssetEdit]
    |-- Use pre-fetched data to avoid redundant API calls
    |-- Run resolution logic per AssetEdit
    |
    v
[4. Return Results]
    +-- Dict[gid, ResolutionResult[Unit]]
```

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Ambiguous results return first match in entity | Return first match | Convenience for callers who don't care about ambiguity | ADR-0071 |
| No resolution caching within session | No caching | Resolution semantics differ from hierarchy cache; results may change | ADR-0072 |
| Batch resolution as module functions | Module functions | Cleaner than class methods; parallel to resolve_units_async pattern | ADR-0073 |
| No timeout parameter | Use transport defaults | Timeout should be controlled at transport layer, not per-operation | N/A (follows existing pattern) |
| Strategy priority order | DEPENDENT_TASKS > CUSTOM_FIELD_MAPPING > EXPLICIT_OFFER_ID | Most reliable first; domain relationships trump field matches | ADR-0071 |

---

## Complexity Assessment

**Complexity Level: Module**

This design is appropriately scoped as a **Module** because:

1. **Clean API Surface**: Resolution is exposed through instance methods on AssetEdit and module functions for batch operations
2. **Clear Boundaries**: Resolution logic is isolated in `resolution.py`, entity definition in `asset_edit.py`
3. **Minimal External Contracts**: Only depends on existing TasksClient and Business model
4. **No Infrastructure Requirements**: No database, no external services, no deployment concerns

**Escalation Triggers (not present)**:
- No independent deployment needed
- No external API contract required
- No multiple consumers (single SDK internal use)

---

## Implementation Plan

### Phase 1: Prerequisites (FR-PREREQ-*)

| Task | Deliverable | Dependencies | Estimate |
|------|-------------|--------------|----------|
| 1.1 | AssetEdit entity with 11 typed field accessors | Process base class | 1 day |
| 1.2 | Update AssetEditHolder to return typed AssetEdit | AssetEdit entity | 0.5 day |
| 1.3 | TasksClient.dependents_async() method | PageIterator pattern | 0.5 day |
| 1.4 | Unit tests for prerequisites | Above deliverables | 1 day |

### Phase 2: Resolution Core (FR-RESOLVE-*, FR-STRATEGY-*)

| Task | Deliverable | Dependencies | Estimate |
|------|-------------|--------------|----------|
| 2.1 | ResolutionStrategy enum | None | 0.25 day |
| 2.2 | ResolutionResult[T] dataclass | None | 0.25 day |
| 2.3 | ResolutionError exception | AsanaError base | 0.25 day |
| 2.4 | DEPENDENT_TASKS strategy impl | dependents_async | 0.5 day |
| 2.5 | CUSTOM_FIELD_MAPPING strategy impl | Business model | 0.5 day |
| 2.6 | EXPLICIT_OFFER_ID strategy impl | TasksClient | 0.5 day |
| 2.7 | AUTO strategy orchestration | All strategy impls | 0.5 day |
| 2.8 | resolve_unit_async() method | Strategies | 0.5 day |
| 2.9 | resolve_offer_async() method | resolve_unit_async | 0.5 day |
| 2.10 | Unit tests for resolution | Above deliverables | 1.5 days |

### Phase 3: Batch Operations (FR-BATCH-*)

| Task | Deliverable | Dependencies | Estimate |
|------|-------------|--------------|----------|
| 3.1 | resolve_units_async() batch function | Phase 2 | 1 day |
| 3.2 | resolve_offers_async() batch function | resolve_units_async | 0.5 day |
| 3.3 | Batch optimization (shared lookups) | Above | 0.5 day |
| 3.4 | Unit and integration tests | Above | 1 day |

### Phase 4: Sync Wrappers and Polish

| Task | Deliverable | Dependencies | Estimate |
|------|-------------|--------------|----------|
| 4.1 | resolve_unit() sync wrapper | resolve_unit_async | 0.25 day |
| 4.2 | resolve_offer() sync wrapper | resolve_offer_async | 0.25 day |
| 4.3 | Documentation and examples | All above | 0.5 day |
| 4.4 | Integration tests | All above | 1 day |

**Total Estimate**: ~12 days

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Asana's 30 dependents limit hit | Medium | Low | Document limit; DEPENDENT_TASKS strategy falls back gracefully |
| Business context not available | High | Medium | Require hydrated Business for CUSTOM_FIELD_MAPPING; clear error message |
| Stale offer_id references | Medium | Low | Handle NotFoundError gracefully; log warning and continue |
| Multiple Units match vertical | Medium | Medium | Return ambiguous result with all candidates; AUTO continues to next strategy |
| API rate limits during batch | Medium | Medium | Use concurrent fetching with semaphore; respect retry-after |
| Circular import with Business model | Low | Medium | Use TYPE_CHECKING imports; lazy imports where needed |

---

## Observability

### Metrics

- `resolution.attempts` - Counter of resolution attempts by strategy
- `resolution.success` - Counter of successful resolutions by strategy
- `resolution.ambiguous` - Counter of ambiguous results
- `resolution.failed` - Counter of failed resolutions
- `resolution.latency_ms` - Histogram of resolution latency by strategy

### Logging

```python
# On resolution start
logger.debug("Starting resolution", extra={
    "asset_edit_gid": self.gid,
    "strategy": strategy.value,
})

# On strategy attempt
logger.debug("Trying strategy", extra={
    "strategy": strategy.value,
    "asset_edit_gid": self.gid,
})

# On success
logger.info("Resolution succeeded", extra={
    "asset_edit_gid": self.gid,
    "strategy_used": result.strategy_used.value,
    "resolved_to": result.entity.gid if result.entity else None,
})

# On ambiguity
logger.info("Resolution ambiguous", extra={
    "asset_edit_gid": self.gid,
    "candidate_count": len(result.candidates),
    "candidates": [c.gid for c in result.candidates],
})

# On failure
logger.warning("Resolution failed", extra={
    "asset_edit_gid": self.gid,
    "strategies_tried": [s.value for s in result.strategies_tried],
    "error": result.error,
})
```

### Alerting

- Alert if resolution failure rate exceeds 20% over 1 hour
- Alert if average resolution latency exceeds 5 seconds

---

## Testing Strategy

### Unit Tests

- **AssetEdit entity**: Field accessors, type conversions, enum-to-bool mapping
- **ResolutionStrategy**: Priority ordering, enum values
- **ResolutionResult**: success property, ambiguous handling
- **Each strategy in isolation**: Mock API responses, verify resolution logic
- **AUTO orchestration**: Strategy ordering, fallback behavior, ambiguity handling
- **Batch helpers**: Optimization verification, partial failure handling

### Integration Tests

- **Full resolution scenario**: Real(ish) hierarchy with AssetEdit resolving to Unit
- **DEPENDENT_TASKS strategy**: AssetEdit with dependent that links to Unit
- **CUSTOM_FIELD_MAPPING strategy**: AssetEdit with matching vertical
- **EXPLICIT_OFFER_ID strategy**: AssetEdit with valid offer_id
- **Ambiguity scenario**: Multiple Units with same vertical
- **No match scenario**: AssetEdit with no resolution path
- **Batch resolution**: Multiple AssetEdits with mixed results

### Edge Cases

- AssetEdit with no Business context (hydration required)
- AssetEdit with stale/invalid offer_id
- AssetEdit with no vertical set
- Empty dependents list
- Rate limit during resolution
- Unit with no offers (for resolve_offer_async)

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Q1: Ambiguous return first or None? | Architect | Resolved | First match per ADR-0071 |
| Q2: Resolution caching? | Architect | Resolved | No caching per ADR-0072 |
| Q3: Batch API location? | Architect | Resolved | Module functions per ADR-0073 |
| Q5: Timeout parameter? | Architect | Resolved | No - use transport defaults |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Architect | Initial design based on PRD-RESOLUTION |

---

## Appendix: AssetEditHolder Update

The existing AssetEditHolder stub needs to be updated to return typed AssetEdit children:

```python
# Before (current stub)
class AssetEditHolder(Task, HolderMixin[Task]):
    CHILD_TYPE: ClassVar[type[Task]] = Task
    _children: list[Task] = PrivateAttr(default_factory=list)

    @property
    def children(self) -> list[Task]:
        return self._children

# After (updated)
class AssetEditHolder(Task, HolderMixin[AssetEdit]):
    CHILD_TYPE: ClassVar[type[AssetEdit]] = AssetEdit
    _asset_edits: list[AssetEdit] = PrivateAttr(default_factory=list)

    @property
    def asset_edits(self) -> list[AssetEdit]:
        """All AssetEdit children."""
        return self._asset_edits

    @property
    def children(self) -> list[AssetEdit]:
        """Backward-compatible alias for asset_edits."""
        return self._asset_edits

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate AssetEdit children from fetched subtasks."""
        sorted_tasks = sorted(
            subtasks,
            key=lambda t: (t.created_at or "", t.name or ""),
        )
        self._asset_edits = []
        for task in sorted_tasks:
            asset_edit = AssetEdit.model_validate(task.model_dump())
            asset_edit._asset_edit_holder = self
            asset_edit._business = self._business
            self._asset_edits.append(asset_edit)
```

---

## Appendix: File Structure

```
src/autom8_asana/
+-- models/
|   +-- business/
|   |   +-- __init__.py          # Export AssetEdit, resolution types
|   |   +-- asset_edit.py        # NEW: AssetEdit entity
|   |   +-- resolution.py        # NEW: Resolution module
|   |   +-- business.py          # MODIFIED: AssetEditHolder
|   |   +-- process.py           # UNCHANGED: Process base
|   |   +-- unit.py              # UNCHANGED: Unit
|   |   +-- offer.py             # UNCHANGED: Offer
|   |   +-- ...
|   +-- __init__.py              # Export new types
+-- clients/
|   +-- tasks.py                 # MODIFIED: dependents_async()
+-- exceptions.py                # MODIFIED: ResolutionError

tests/
+-- unit/
|   +-- models/
|   |   +-- business/
|   |       +-- test_asset_edit.py        # NEW
|   |       +-- test_resolution.py        # NEW
|   +-- clients/
|       +-- test_tasks_dependents.py      # NEW
+-- integration/
    +-- test_resolution_scenarios.py      # NEW
```
