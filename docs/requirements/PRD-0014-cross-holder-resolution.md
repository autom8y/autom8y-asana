# PRD: Cross-Holder Relationship Resolution

## Metadata

- **PRD ID**: PRD-RESOLUTION
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-16
- **Last Updated**: 2025-12-16
- **Stakeholders**: SDK users, SDK maintainers, Workflow automation developers, Reporting/analytics consumers
- **Related PRDs**: PRD-BIZMODEL (Business Model Phase 1), PRD-HYDRATION (Business Model Hydration)
- **Related Discovery**: DISCOVERY-RESOLUTION-001
- **Related Initiatives**: PROMPT-0-RELATIONSHIP-RESOLUTION, PROMPT-MINUS-1-RELATIONSHIP-RESOLUTION

---

## Problem Statement

### Current State

The SDK provides excellent **hierarchical navigation** through the business model (offer.unit, unit.business, contact.business). These "fast-paths" follow the containment hierarchy and work reliably.

However, **cross-holder relationships** - relationships between entities that are not in a direct parent/child hierarchy - require domain-specific logic that the SDK does not encapsulate:

```
Business
  +-- AssetEditHolder
  |     +-- AssetEdit (process task)     <-- START: Need to find owning Unit/Offer
  |     +-- AssetEdit
  |
  +-- UnitHolder
        +-- Unit                          <-- TARGET: Which Unit does this AssetEdit belong to?
              +-- OfferHolder
                    +-- Offer             <-- TARGET: Which Offer does this AssetEdit belong to?
```

**The gap**: An AssetEdit entity needs to resolve to its "owning" Unit and Offer, but:
1. AssetEdit is not in the Unit/Offer containment hierarchy
2. Resolution requires checking multiple sources (dependent tasks, custom field mapping, explicit offer_id)
3. Multiple resolution strategies exist with different reliability and cost
4. Users currently implement this logic themselves, leading to inconsistent behavior

### Pain Points

1. **Domain logic duplication**: Every consumer reimplements resolution strategies
2. **Inconsistent behavior**: Different resolution implementations may return different results
3. **No transparency**: Users cannot see which resolution strategy succeeded
4. **No ambiguity handling**: When multiple Units match, behavior is undefined
5. **Missing entity typing**: AssetEdit is currently a plain Task, losing type safety

### Who Is Affected

- **Workflow automation developers**: Processing AssetEdits from webhooks, need to correlate with Units/Offers
- **Reporting consumers**: Aggregating data across AssetEdits, need Business/Unit context
- **Batch operation developers**: Processing collections of AssetEdits, need efficient resolution
- **SDK maintainers**: Domain logic should be in SDK, not scattered across consumers

### Impact of Not Solving

- **Continued duplication**: Resolution logic reimplemented by every consumer
- **Potential bugs**: Inconsistent resolution implementations
- **Lost productivity**: Users spend time on domain logic SDK should handle
- **Incomplete SDK**: Business model layer missing a core workflow pattern

### Use Case Frequency

Per Discovery findings (DISCOVERY-RESOLUTION-001):

> "VERY OFTEN, and also very often in collections. For example, in custom field models these relationships are encoded: when you get `offer.office_phone`, you also load `business.office_phone`. It's incredibly common and often done in threaded access and async methods or batch operations like 'get all office phones of active offers'."

**Assessment**: **VERY HIGH FREQUENCY** - cross-holder resolution is a core workflow pattern, not an edge case.

---

## Goals & Success Metrics

### Goals

1. **Type AssetEdit entity**: Enable typed access to 11 custom fields (prerequisite)
2. **Enable TasksClient.dependents_async()**: Provide API for fetching task dependents (prerequisite)
3. **Enable resolution**: AssetEdit can resolve to owning Unit and Offer
4. **Strategy transparency**: Callers can see which resolution strategy succeeded
5. **Ambiguity handling**: Clear, consistent behavior when multiple matches found
6. **Batch support**: Efficient resolution for collections (given high frequency)

### Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Resolve AssetEdit to Unit | Not possible | `asset_edit.resolve_unit_async()` returns Unit | Integration test |
| Resolve AssetEdit to Offer | Not possible | `asset_edit.resolve_offer_async()` returns Offer | Integration test |
| Strategy transparency | N/A | Result includes `strategy_used` field | Unit test |
| Ambiguity handling | Undefined | Consistent defined behavior | Unit test |
| AssetEdit typed fields | 0 | 11 typed accessors | mypy passes |
| Batch resolution | N/A | `resolve_units_async(asset_edits)` available | Integration test |
| Existing tests pass | 100% | 100% | `pytest` unchanged |

---

## Scope

### In Scope

**Prerequisites (FR-PREREQ-*)**
- Create `AssetEdit` entity class extending `Process`
- Add 11 typed field accessors from legacy model
- Update `AssetEditHolder` to return `AssetEdit` children
- Add `TasksClient.dependents_async()` method

**Core Resolution (FR-RESOLVE-*)**
- Single AssetEdit -> Unit resolution
- Single AssetEdit -> Offer resolution (via Unit)
- Resolution result type with strategy transparency

**Resolution Strategies (FR-STRATEGY-*)**
- DEPENDENT_TASKS: Check task dependents for Unit relationship
- CUSTOM_FIELD_MAPPING: Match vertical field to Unit
- EXPLICIT_OFFER_ID: Read offer_id field directly
- AUTO: Try strategies in priority order (default)

**Ambiguity Handling (FR-AMBIG-*)**
- Define behavior for no matches
- Define behavior for multiple matches
- Architecture to design specific approach

**API Surface (FR-API-*)**
- `AssetEdit.resolve_unit_async()` instance method
- `AssetEdit.resolve_offer_async()` instance method
- Strategy selection parameter (AUTO or explicit)

**Batch Operations (FR-BATCH-*)**
- Batch resolution for collections (promoted to "Should" given high frequency)

### Out of Scope

| Item | Rationale |
|------|-----------|
| Improving existing hierarchical fast-paths | Already work well (offer.unit, unit.business) |
| Other process type resolutions | Future initiative; AssetEdit proves the pattern |
| Resolution caching | Different semantics than hierarchy cache; defer |
| Bidirectional resolution (Unit -> AssetEdits) | Inverse pattern; different use case |
| Circular resolution prevention | Handled by single-direction design |
| Resolution configuration persistence | One-time per-call; not a user preference |

---

## Requirements

### Prerequisites (FR-PREREQ-*)

#### FR-PREREQ-001: AssetEdit Entity Type

| Field | Value |
|-------|-------|
| **ID** | FR-PREREQ-001 |
| **Requirement** | Create `AssetEdit` class extending `Process` with 11 typed field accessors |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Class definition: `class AssetEdit(Process)` in `src/autom8_asana/models/business/asset_edit.py`
- [ ] NAME_CONVENTION class variable for entity detection
- [ ] Inner `Fields` class with constants for all 11 custom field names
- [ ] Typed property getter/setter for each field:
  - `asset_approval: str | None` (enum)
  - `asset_id: str | None` (text)
  - `editor: list[dict[str, Any]]` (people)
  - `reviewer: list[dict[str, Any]]` (people)
  - `offer_id: str | None` (text) - **Key for EXPLICIT_OFFER_ID strategy**
  - `raw_assets: str | None` (text/link)
  - `review_all_ads: bool | None` (enum mapped to bool)
  - `score: Decimal | None` (number)
  - `specialty: str | None` (enum)
  - `template_id: str | None` (text)
  - `videos_paid: int | None` (number)
- [ ] Follows Process base class pattern (inherits status, priority, etc.)
- [ ] mypy passes with strict mode

**Integration Point**: New file `/src/autom8_asana/models/business/asset_edit.py`

---

#### FR-PREREQ-002: AssetEditHolder Update

| Field | Value |
|-------|-------|
| **ID** | FR-PREREQ-002 |
| **Requirement** | Update `AssetEditHolder` to return typed `AssetEdit` children instead of plain `Task` |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Change `CHILD_TYPE: ClassVar[type[Task]] = Task` to `CHILD_TYPE: ClassVar[type[AssetEdit]] = AssetEdit`
- [ ] Rename `_children` to `_asset_edits` for clarity
- [ ] Add `asset_edits` property returning `list[AssetEdit]`
- [ ] Update `_populate_children()` to create `AssetEdit` instances
- [ ] Set back-references: `asset_edit._business = self._business`
- [ ] Keep `children` property for backward compatibility (alias to `asset_edits`)

**Integration Point**: `/src/autom8_asana/models/business/business.py` (AssetEditHolder class)

---

#### FR-PREREQ-003: TasksClient.dependents_async()

| Field | Value |
|-------|-------|
| **ID** | FR-PREREQ-003 |
| **Requirement** | Add `dependents_async()` method to TasksClient following `subtasks_async()` pattern |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Method signature: `def dependents_async(self, task_gid: str, *, opt_fields: list[str] | None = None, limit: int = 100) -> PageIterator[Task]`
- [ ] Calls Asana API: `GET /tasks/{task_gid}/dependents`
- [ ] Returns `PageIterator[Task]` for pagination
- [ ] Handles Asana's 30 dependents+dependencies combined limit
- [ ] Validates `task_gid` using `validate_gid()`
- [ ] Includes sync wrapper `_dependents_sync()`

**Integration Point**: `/src/autom8_asana/clients/tasks.py`

**API Reference**: [Asana API - Get dependents from a task](https://developers.asana.com/reference/getdependentsfortask)

---

### Core Resolution (FR-RESOLVE-*)

#### FR-RESOLVE-001: Resolve AssetEdit to Unit

| Field | Value |
|-------|-------|
| **ID** | FR-RESOLVE-001 |
| **Requirement** | `AssetEdit` can resolve to its owning `Unit` using configured strategies |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Method signature: `async def resolve_unit_async(self, client: AsanaClient, *, strategy: ResolutionStrategy = ResolutionStrategy.AUTO) -> ResolutionResult[Unit]`
- [ ] Executes specified strategy (or AUTO sequence)
- [ ] Returns `ResolutionResult` with resolved Unit (or None)
- [ ] `ResolutionResult.strategy_used` indicates which strategy succeeded
- [ ] `ResolutionResult.entity` contains the resolved Unit or None
- [ ] Raises `ResolutionError` on unrecoverable failures (not ambiguity)

**Integration Point**: `/src/autom8_asana/models/business/asset_edit.py`

---

#### FR-RESOLVE-002: Resolve AssetEdit to Offer

| Field | Value |
|-------|-------|
| **ID** | FR-RESOLVE-002 |
| **Requirement** | `AssetEdit` can resolve to its owning `Offer` via resolved Unit |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Method signature: `async def resolve_offer_async(self, client: AsanaClient, *, strategy: ResolutionStrategy = ResolutionStrategy.AUTO) -> ResolutionResult[Offer]`
- [ ] First resolves to Unit (using FR-RESOLVE-001)
- [ ] Then matches Offer via EXPLICIT_OFFER_ID or Unit's active offers
- [ ] Returns `ResolutionResult` with resolved Offer (or None)
- [ ] `ResolutionResult.strategy_used` indicates strategy chain used
- [ ] Handles case where Unit is resolved but Offer is not found

**Integration Point**: `/src/autom8_asana/models/business/asset_edit.py`

---

#### FR-RESOLVE-003: Resolution Result Type

| Field | Value |
|-------|-------|
| **ID** | FR-RESOLVE-003 |
| **Requirement** | Resolution returns a typed result with transparency about resolution path |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Dataclass or Pydantic model: `ResolutionResult[T]`
- [ ] Fields:
  - `entity: T | None` - Resolved entity or None if not found
  - `strategy_used: ResolutionStrategy | None` - Strategy that succeeded
  - `strategies_tried: list[ResolutionStrategy]` - All strategies attempted
  - `ambiguous: bool` - True if multiple matches were found
  - `candidates: list[T]` - All matching entities (if ambiguous or for debugging)
  - `error: str | None` - Error message if resolution failed
- [ ] `success` property: `True` if exactly one match found
- [ ] Located in `/src/autom8_asana/models/business/resolution.py`

**Integration Point**: New file `/src/autom8_asana/models/business/resolution.py`

---

### Resolution Strategies (FR-STRATEGY-*)

#### FR-STRATEGY-001: ResolutionStrategy Enum

| Field | Value |
|-------|-------|
| **ID** | FR-STRATEGY-001 |
| **Requirement** | Enum defining available resolution strategies and their priority order |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Enum class: `ResolutionStrategy(str, Enum)`
- [ ] Values:
  - `DEPENDENT_TASKS = "dependent_tasks"` - Priority 1 (most reliable)
  - `CUSTOM_FIELD_MAPPING = "custom_field_mapping"` - Priority 2
  - `EXPLICIT_OFFER_ID = "explicit_offer_id"` - Priority 3
  - `AUTO = "auto"` - Try strategies in priority order (default)
- [ ] Priority ordering accessible via class method or ordering

**Integration Point**: `/src/autom8_asana/models/business/resolution.py`

---

#### FR-STRATEGY-002: DEPENDENT_TASKS Strategy

| Field | Value |
|-------|-------|
| **ID** | FR-STRATEGY-002 |
| **Requirement** | Resolve Unit by checking AssetEdit's dependent tasks for Unit relationship |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Calls `client.tasks.dependents_async(self.gid).collect()` to get dependents
- [ ] For each dependent task:
  - Check if dependent is or belongs to a Unit
  - May require fetching parent chain to identify Unit
- [ ] Returns first Unit found in dependents chain
- [ ] Returns None if no Unit found in dependents
- [ ] Handles API errors gracefully (returns None, logs warning)
- [ ] Respects Asana's 30 dependents+dependencies limit

**Integration Point**: Resolution logic in `asset_edit.py` or `resolution.py`

---

#### FR-STRATEGY-003: CUSTOM_FIELD_MAPPING Strategy

| Field | Value |
|-------|-------|
| **ID** | FR-STRATEGY-003 |
| **Requirement** | Resolve Unit by matching AssetEdit's vertical field to Unit's vertical |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Reads `self.vertical` from AssetEdit (inherited from Process)
- [ ] Requires Business context to be available (AssetEdit.business must be set)
- [ ] Iterates `business.units` to find matching vertical
- [ ] Returns Unit where `unit.vertical == self.vertical`
- [ ] Returns None if no matching vertical found
- [ ] Returns None if AssetEdit has no vertical set
- [ ] If multiple Units match, marks result as ambiguous

**Integration Point**: Resolution logic in `asset_edit.py` or `resolution.py`

---

#### FR-STRATEGY-004: EXPLICIT_OFFER_ID Strategy

| Field | Value |
|-------|-------|
| **ID** | FR-STRATEGY-004 |
| **Requirement** | Resolve Offer directly using AssetEdit's explicit offer_id field |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Reads `self.offer_id` from AssetEdit
- [ ] If offer_id is set and non-empty:
  - Fetches Offer via `client.tasks.get_async(offer_id)`
  - Navigates from Offer to Unit via `offer.unit`
  - Returns Offer and/or Unit as appropriate
- [ ] Returns None if offer_id is not set or empty
- [ ] Handles case where offer_id is stale/invalid (GID not found)
- [ ] Logs warning if offer_id refers to non-Offer task

**Integration Point**: Resolution logic in `asset_edit.py` or `resolution.py`

---

#### FR-STRATEGY-005: AUTO Strategy Execution

| Field | Value |
|-------|-------|
| **ID** | FR-STRATEGY-005 |
| **Requirement** | AUTO mode executes strategies in priority order until one succeeds |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Strategy execution order:
  1. DEPENDENT_TASKS (most reliable, domain-specific)
  2. CUSTOM_FIELD_MAPPING (field match)
  3. EXPLICIT_OFFER_ID (direct ID reference)
- [ ] Stops at first successful resolution (single non-ambiguous match)
- [ ] If all strategies fail, returns result with `entity=None`
- [ ] If strategy finds ambiguous matches, continues to next strategy
- [ ] Records all `strategies_tried` in result
- [ ] Records `strategy_used` as the successful one (or None)

**Integration Point**: Resolution logic

---

### Ambiguity Handling (FR-AMBIG-*)

#### FR-AMBIG-001: No Matches Found

| Field | Value |
|-------|-------|
| **ID** | FR-AMBIG-001 |
| **Requirement** | Define clear behavior when no resolution strategy finds a match |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Returns `ResolutionResult` with `entity=None`, `success=False`
- [ ] `strategy_used` is None
- [ ] `strategies_tried` lists all attempted strategies
- [ ] Does NOT raise exception (caller decides how to handle)
- [ ] `error` field contains "No matching entity found"

**Integration Point**: Resolution logic

---

#### FR-AMBIG-002: Multiple Matches Found

| Field | Value |
|-------|-------|
| **ID** | FR-AMBIG-002 |
| **Requirement** | Define clear behavior when a strategy finds multiple matching entities |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] **Default behavior**: Returns `ResolutionResult` with `ambiguous=True`
- [ ] `entity` is set to first match (for convenience)
- [ ] `candidates` contains all matching entities
- [ ] `success` is False (ambiguous is not success)
- [ ] If AUTO mode, continues to next strategy seeking non-ambiguous match
- [ ] Logs info-level message about ambiguity

**Open Question for Architect**: Should ambiguous results return first match or None in `entity` field? Recommendation: First match (allows caller to use if acceptable).

**Integration Point**: Resolution logic

---

#### FR-AMBIG-003: Strategy Failure

| Field | Value |
|-------|-------|
| **ID** | FR-AMBIG-003 |
| **Requirement** | Define behavior when a strategy encounters an error |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] API errors (network, auth, not found) are caught
- [ ] Strategy returns "no match" on error (does not propagate exception)
- [ ] Error is logged as warning with strategy name and details
- [ ] AUTO mode continues to next strategy
- [ ] Only raise `ResolutionError` if ALL strategies fail with errors (no matches attempted)

**Integration Point**: Resolution logic

---

### API Surface (FR-API-*)

#### FR-API-001: Instance Method Signature

| Field | Value |
|-------|-------|
| **ID** | FR-API-001 |
| **Requirement** | Resolution methods are instance methods on AssetEdit entity |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] `resolve_unit_async(self, client, *, strategy=AUTO) -> ResolutionResult[Unit]`
- [ ] `resolve_offer_async(self, client, *, strategy=AUTO) -> ResolutionResult[Offer]`
- [ ] Client is required parameter (resolution requires API calls)
- [ ] Strategy is optional with AUTO default
- [ ] Return type is `ResolutionResult[T]` for type safety
- [ ] Methods are async (resolution involves API calls)

**Integration Point**: `/src/autom8_asana/models/business/asset_edit.py`

---

#### FR-API-002: Sync Wrappers

| Field | Value |
|-------|-------|
| **ID** | FR-API-002 |
| **Requirement** | Sync versions of resolution methods for non-async callers |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] `resolve_unit(self, client, *, strategy=AUTO) -> ResolutionResult[Unit]`
- [ ] `resolve_offer(self, client, *, strategy=AUTO) -> ResolutionResult[Offer]`
- [ ] Uses `@sync_wrapper` pattern from SDK
- [ ] Functionally identical to async versions

**Integration Point**: `/src/autom8_asana/models/business/asset_edit.py`

---

### Batch Operations (FR-BATCH-*)

#### FR-BATCH-001: Batch Unit Resolution

| Field | Value |
|-------|-------|
| **ID** | FR-BATCH-001 |
| **Requirement** | Resolve multiple AssetEdits to Units efficiently |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] Function signature: `async def resolve_units_async(asset_edits: Sequence[AssetEdit], client: AsanaClient, *, strategy: ResolutionStrategy = AUTO) -> dict[str, ResolutionResult[Unit]]`
- [ ] Returns dict mapping `asset_edit.gid` to `ResolutionResult`
- [ ] Optimizes shared lookups (e.g., fetch Business units once for all CUSTOM_FIELD_MAPPING)
- [ ] Uses concurrent fetching where possible
- [ ] Handles partial failures (some resolve, some don't)

**Integration Point**: `/src/autom8_asana/models/business/resolution.py` or `asset_edit.py`

---

#### FR-BATCH-002: Batch Offer Resolution

| Field | Value |
|-------|-------|
| **ID** | FR-BATCH-002 |
| **Requirement** | Resolve multiple AssetEdits to Offers efficiently |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] Function signature: `async def resolve_offers_async(asset_edits: Sequence[AssetEdit], client: AsanaClient, *, strategy: ResolutionStrategy = AUTO) -> dict[str, ResolutionResult[Offer]]`
- [ ] Returns dict mapping `asset_edit.gid` to `ResolutionResult`
- [ ] Can build on `resolve_units_async()` for efficiency
- [ ] Handles partial failures

**Integration Point**: `/src/autom8_asana/models/business/resolution.py` or `asset_edit.py`

---

### Non-Functional Requirements

#### NFR-PERF-001: Single Resolution Latency

| Field | Value |
|-------|-------|
| **ID** | NFR-PERF-001 |
| **Requirement** | Single AssetEdit resolution completes within acceptable time |
| **Target** | p95 < 2 seconds (depends on API, strategy used) |
| **Measurement** | Trace logging, integration test timing |

**Acceptance Criteria**:
- [ ] DEPENDENT_TASKS: 1-2 API calls (dependents + potentially parent fetch)
- [ ] CUSTOM_FIELD_MAPPING: 0 API calls if Business already hydrated
- [ ] EXPLICIT_OFFER_ID: 1-2 API calls (offer fetch + potentially unit)
- [ ] AUTO: At most sum of individual strategies

---

#### NFR-PERF-002: Batch Resolution Efficiency

| Field | Value |
|-------|-------|
| **ID** | NFR-PERF-002 |
| **Requirement** | Batch resolution is more efficient than N individual resolutions |
| **Target** | O(1) shared lookups + O(N) individual lookups |
| **Measurement** | API call count in integration test |

**Acceptance Criteria**:
- [ ] Business units fetched once, not per-AssetEdit
- [ ] Concurrent API calls for independent lookups
- [ ] Demonstrates measurable improvement over sequential single resolutions

---

#### NFR-SAFE-001: Type Safety

| Field | Value |
|-------|-------|
| **ID** | NFR-SAFE-001 |
| **Requirement** | All new code passes mypy strict mode |
| **Target** | mypy exit code 0 |
| **Measurement** | `mypy src/autom8_asana` |

**Acceptance Criteria**:
- [ ] All method signatures fully typed
- [ ] `ResolutionResult[T]` is generic and type-safe
- [ ] No `# type: ignore` except where unavoidable
- [ ] `TYPE_CHECKING` used for circular import avoidance

---

#### NFR-SAFE-002: Test Coverage

| Field | Value |
|-------|-------|
| **ID** | NFR-SAFE-002 |
| **Requirement** | New resolution code has > 80% test coverage |
| **Target** | > 80% coverage |
| **Measurement** | `pytest --cov` |

**Acceptance Criteria**:
- [ ] Unit tests for AssetEdit entity and field accessors
- [ ] Unit tests for each resolution strategy in isolation
- [ ] Unit tests for AUTO strategy ordering
- [ ] Unit tests for ambiguity handling
- [ ] Integration tests for full resolution scenarios
- [ ] Edge case tests (no matches, multiple matches, API errors)

---

#### NFR-COMPAT-001: Backward Compatibility

| Field | Value |
|-------|-------|
| **ID** | NFR-COMPAT-001 |
| **Requirement** | All existing tests pass without modification |
| **Target** | 100% existing tests pass |
| **Measurement** | `pytest` before/after |

**Acceptance Criteria**:
- [ ] Existing business model tests unchanged and passing
- [ ] AssetEditHolder.children still works (backward compat alias)
- [ ] No breaking changes to public API signatures

---

## User Stories / Use Cases

### US-001: Webhook Handler for AssetEdit Update

**As a** webhook handler developer
**I want to** receive an AssetEdit GID and find its owning Unit
**So that** I can access Unit-level settings when processing AssetEdit changes

**Scenario**:
```python
async def handle_asset_edit_webhook(asset_edit_gid: str):
    # Fetch AssetEdit (now typed!)
    task = await client.tasks.get_async(asset_edit_gid)
    asset_edit = AssetEdit.model_validate(task.model_dump())

    # Resolve to Unit
    result = await asset_edit.resolve_unit_async(client)

    if result.success:
        unit = result.entity
        print(f"AssetEdit {asset_edit.name} belongs to Unit {unit.name}")
        print(f"Resolved via strategy: {result.strategy_used}")
    elif result.ambiguous:
        print(f"Multiple Units matched: {[u.name for u in result.candidates]}")
    else:
        print(f"Could not resolve Unit: {result.error}")
```

---

### US-002: Batch Resolution for Reporting

**As a** reporting dashboard developer
**I want to** resolve all AssetEdits under a Business to their Units
**So that** I can aggregate AssetEdit metrics by Unit

**Scenario**:
```python
async def generate_asset_report(business_gid: str):
    # Load hydrated Business
    business = await Business.from_gid_async(client, business_gid)

    # Get all AssetEdits
    asset_edits = business.asset_edit_holder.asset_edits

    # Batch resolve to Units
    results = await resolve_units_async(asset_edits, client)

    # Aggregate by Unit
    by_unit: dict[str, list[AssetEdit]] = {}
    for ae in asset_edits:
        result = results[ae.gid]
        if result.success:
            unit_name = result.entity.name
            by_unit.setdefault(unit_name, []).append(ae)
        else:
            by_unit.setdefault("Unresolved", []).append(ae)

    return by_unit
```

---

### US-003: Explicit Strategy Selection

**As a** developer with domain knowledge
**I want to** specify which resolution strategy to use
**So that** I can optimize for my specific use case

**Scenario**:
```python
async def resolve_with_known_strategy(asset_edit: AssetEdit):
    # I know this AssetEdit has a valid offer_id, skip other strategies
    result = await asset_edit.resolve_offer_async(
        client,
        strategy=ResolutionStrategy.EXPLICIT_OFFER_ID
    )

    if not result.success:
        # Fallback to AUTO if explicit strategy fails
        result = await asset_edit.resolve_offer_async(client)

    return result
```

---

### US-004: Accessing Typed AssetEdit Fields

**As a** SDK user
**I want to** access AssetEdit custom fields with type safety
**So that** I can avoid string-based field access errors

**Scenario**:
```python
async def process_asset_edit(asset_edit: AssetEdit):
    # Typed field access (new capability)
    if asset_edit.score and asset_edit.score > Decimal("90"):
        print(f"High score: {asset_edit.score}")

    # Check reviewer assignment
    if asset_edit.reviewer:
        print(f"Assigned to: {asset_edit.reviewer[0].get('name')}")

    # Access offer_id for resolution
    if asset_edit.offer_id:
        print(f"Explicit offer: {asset_edit.offer_id}")
```

---

## Assumptions

1. **AssetEdit always belongs to exactly one Unit/Offer**: Resolution finds the single correct match, not creates associations

2. **DEPENDENT_TASKS strategy is most reliable**: Task dependencies encode the canonical relationship in Asana

3. **Vertical matching is consistent**: Unit.vertical and AssetEdit.vertical (Process.vertical) use same enum values

4. **offer_id field contains valid GID when populated**: Stale/invalid GIDs are edge cases handled gracefully

5. **Business context is available or fetchable**: Resolution can access Business.units for CUSTOM_FIELD_MAPPING

6. **Asana's 30 dependents limit is rarely hit**: Most tasks have fewer than 30 dependents

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| Process entity base class | Business Model | Implemented |
| CustomFieldAccessor | Business Model | Implemented |
| Business.from_gid_async() with hydration | Hydration Initiative | Implemented |
| TasksClient patterns (get_async, subtasks_async) | TasksClient | Implemented |
| Asana API dependents endpoint | Asana | Available |
| ADR-0052 caching pattern | Business Model | Implemented |

---

## Open Questions

| # | Question | Owner | Due Date | Resolution |
|---|----------|-------|----------|------------|
| Q1 | Should ambiguous result return first match or None in `entity` field? | Architect | Session 3 | Recommendation: First match (convenience) |
| Q2 | Should resolution cache results within a session? | Architect | Session 3 | Recommendation: No caching (different semantics) |
| Q3 | Should batch resolution be a module function or class method? | Architect | Session 3 | - |
| Q4 | Specific ambiguity edge cases to handle? | QA | Session 6 | Deferred per user request |
| Q5 | Should resolution methods accept timeout parameter? | Architect | Session 3 | - |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Requirements Analyst | Initial PRD based on DISCOVERY-RESOLUTION-001 |

---

## Appendix: Legacy AssetEdit Model Reference

From user-provided legacy code:

```python
class AssetEdit(Process):
    ASANA_FIELDS = {
        "asset_approval": AssetApproval,     # Enum field
        "asset_id": AssetId,                  # Text field
        "editor": Editor,                     # People field
        "reviewer": Reviewer,                 # People field
        "offer_id": OfferId,                  # Text field (GID reference)
        "raw_assets": RawAssets,              # Text/link field
        "review_all_ads": ReviewAllAds,       # Enum -> bool mapping
        "score": Score,                       # Number field (Decimal)
        "specialty": SpecialtyField,          # Enum field
        "template_id": TemplateId,            # Text field
        "videos_paid": VideosPaid,            # Number field (int)
    }
```

**Note**: Field types inferred from naming conventions; Architect should validate during TDD.

---

## Appendix: Resolution Strategy Decision Tree

```
AssetEdit.resolve_unit_async(strategy=AUTO)
    |
    v
[DEPENDENT_TASKS]
    | Found Unit via dependents?
    +-- YES --> Return ResolutionResult(entity=Unit, strategy_used=DEPENDENT_TASKS)
    +-- NO/ERROR --> Continue
    v
[CUSTOM_FIELD_MAPPING]
    | AssetEdit.vertical matches Unit.vertical?
    +-- YES (single match) --> Return ResolutionResult(entity=Unit, strategy_used=CUSTOM_FIELD_MAPPING)
    +-- YES (multiple) --> Mark ambiguous, continue
    +-- NO --> Continue
    v
[EXPLICIT_OFFER_ID]
    | AssetEdit.offer_id set and valid?
    +-- YES --> Fetch Offer, get Unit from offer.unit
    |           Return ResolutionResult(entity=Unit, strategy_used=EXPLICIT_OFFER_ID)
    +-- NO --> Continue
    v
[ALL STRATEGIES EXHAUSTED]
    | Any ambiguous results found?
    +-- YES --> Return ResolutionResult(entity=first_match, ambiguous=True, candidates=[...])
    +-- NO --> Return ResolutionResult(entity=None, error="No matching entity found")
```

---

## Quality Gates Checklist

- [x] Problem statement is clear and compelling
- [x] Scope explicitly defines in/out
- [x] All requirements are specific and testable
- [x] Acceptance criteria defined for each requirement
- [x] Assumptions documented
- [x] Open questions have owners assigned (Architect, QA)
- [x] Dependencies identified with status
- [x] Success metrics are quantified
- [x] User stories demonstrate real use cases
- [x] MoSCoW prioritization applied (Must/Should/Could)
