# PRD: Business Model Hydration

## Metadata

- **PRD ID**: PRD-HYDRATION
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-16
- **Last Updated**: 2025-12-16
- **Stakeholders**: SDK users, SDK maintainers, Business Model consumers, Webhook handlers
- **Related PRDs**: PRD-BIZMODEL (Business Model Phase 1), PRD-SDKUX (SDK Usability)
- **Related Discovery**: DISCOVERY-HYDRATION-001
- **Related ADRs**: ADR-0050 (Holder Lazy Loading), ADR-0052 (Bidirectional References), ADR-0053 (Recursive Tracking), ADR-0057 (subtasks_async)

---

## Problem Statement

### Current State

The SDK supports business model hierarchies (Business -> Units -> Offers, etc.) but **only from the Business root**. The `_fetch_holders_async()` methods are stubbed with placeholder implementations:

```python
# Business._fetch_holders_async() (business.py:520-542)
async def _fetch_holders_async(self, client: AsanaClient) -> None:
    # Phase 2: Implement when TasksClient.get_subtasks_async() is available
    _ = client  # Suppress unused parameter warning
```

**Consequence**: Users cannot hydrate business hierarchies from arbitrary entry points (Contact, Offer, Process).

### Pain Points

1. **Webhook handlers receive entity GIDs, not Business GIDs**: A webhook for "task updated" may receive a Contact GID. Currently, the caller must know the Business GID to load the hierarchy.

2. **Search returns entity GIDs**: Searching for Offers returns Offer GIDs. Users want to navigate to `offer.business.name` but cannot without knowing the Business GID.

3. **Deep links point to entities**: A URL like `/tasks/123456` links to an Offer. The SDK cannot hydrate the full context.

4. **Manual traversal is error-prone**: Users resort to manual `get_async()` + `parent` traversal, losing type safety and caching benefits.

### Who Is Affected

- **Webhook handler developers**: Receive entity GIDs, need full hierarchy context
- **Search feature implementers**: Return entity GIDs from search, need navigation
- **Batch operation developers**: Process multiple entities, need Business context for each
- **Reporting dashboard builders**: Aggregate data across hierarchy levels

### Impact of Not Solving

- **Incomplete SDK**: Business model layer remains partially implemented
- **User frustration**: Manual traversal defeats purpose of typed models
- **Code duplication**: Every consumer reimplements traversal logic
- **Lost context**: Webhook handlers cannot access parent Business data

---

## Goals & Success Metrics

### Goals

1. **Complete Phase 2**: Implement stubbed `_fetch_holders_async()` methods
2. **Enable downward hydration**: Load full hierarchy from Business entry point
3. **Enable upward traversal**: Find Business root from any entity entry point
4. **Enable combined hydration**: Any entry point hydrates complete hierarchy
5. **Maintain patterns**: Follow existing ADR-0052 caching and ADR-0053 tracking

### Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| `contact.business` from Contact GID | `None` | Returns populated `Business` | Integration test |
| `unit.offers` from Unit GID | `[]` | Returns populated `list[Offer]` | Integration test |
| `offer.business.contacts` navigation | Fails | Returns populated list | Integration test |
| Existing tests pass | 100% | 100% | `pytest` unchanged |
| API calls for typical hierarchy | N/A | < 30 calls | Trace logging |
| Type safety | N/A | mypy passes | `mypy src/autom8_asana` |

---

## Scope

### In Scope

**P0 - Downward Hydration (Core)**
- Implement `Business._fetch_holders_async()` - fetch and populate all holder children
- Implement `Unit._fetch_holders_async()` - fetch and populate OfferHolder, ProcessHolder
- Implement holder `_populate_children()` calls during hydration
- Set bidirectional references per ADR-0052

**P1 - Upward Traversal (High Value)**
- Implement upward traversal from Contact to Business (2 levels)
- Implement upward traversal from Offer to Business (4 levels)
- Type detection heuristics for parent identification
- Set bidirectional references during upward traversal

**P2 - Combined Hydration (Full Feature)**
- `hydrate_async()` method for any entity to reach full hierarchy
- Concurrent fetching within each level (performance)
- `HydrationConfig` for depth/type control (optional)

### Out of Scope

| Item | Rationale |
|------|-----------|
| Upward traversal from Process | Lower priority entry point; P2 pattern applies |
| Batch hydration (multiple GIDs) | Composable from single-GID hydration |
| Incremental/delta hydration | Requires change tracking beyond current scope |
| Hydration caching across sessions | Conflicts with freshness; separate concern |
| Process subclass specialization | Phase 3 per TDD-BIZMODEL |
| API location decisions | Deferred to Architect (Session 3) |

---

## Requirements

### Downward Hydration (FR-DOWN-*)

#### FR-DOWN-001: Business Holder Fetching

| Field | Value |
|-------|-------|
| **ID** | FR-DOWN-001 |
| **Requirement** | `Business._fetch_holders_async(client)` fetches all immediate holder subtasks and populates typed holders |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Method implementation replaces stub in `business.py`
- [ ] Calls `client.tasks.subtasks_async(self.gid).collect()` to fetch holder tasks
- [ ] Calls `self._populate_holders(subtasks)` with fetched tasks
- [ ] For each populated holder (ContactHolder, UnitHolder, LocationHolder, etc.), fetches holder's subtasks
- [ ] Calls `holder._populate_children(holder_subtasks)` for each holder
- [ ] Sets `holder._business = self` back-reference for each holder
- [ ] Returns after all holders and their children are populated
- [ ] Raises `APIError` if any fetch fails

**Integration Point**: `/src/autom8_asana/models/business/business.py:520-542`

---

#### FR-DOWN-002: Unit Holder Fetching

| Field | Value |
|-------|-------|
| **ID** | FR-DOWN-002 |
| **Requirement** | `Unit._fetch_holders_async(client)` fetches OfferHolder and ProcessHolder subtasks and populates typed holders |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Method implementation replaces stub in `unit.py`
- [ ] Calls `client.tasks.subtasks_async(self.gid).collect()` to fetch holder tasks
- [ ] Calls `self._populate_holders(subtasks)` with fetched tasks
- [ ] For OfferHolder: fetches subtasks and calls `_populate_children()`
- [ ] For ProcessHolder: fetches subtasks and calls `_populate_children()`
- [ ] Sets `holder._unit = self` and `holder._business = self._business` for each holder
- [ ] Returns after all holders and their children are populated

**Integration Point**: `/src/autom8_asana/models/business/unit.py:320-327`

---

#### FR-DOWN-003: Holder Child Population

| Field | Value |
|-------|-------|
| **ID** | FR-DOWN-003 |
| **Requirement** | During `_fetch_holders_async()`, each holder's `_populate_children()` is called with its subtasks |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] ContactHolder receives subtasks and populates `_contacts` list with typed Contact instances
- [ ] UnitHolder receives subtasks and populates `_units` list with typed Unit instances
- [ ] OfferHolder receives subtasks and populates `_offers` list with typed Offer instances
- [ ] ProcessHolder receives subtasks and populates `_processes` list with typed Process instances
- [ ] LocationHolder receives subtasks and populates `_locations` list and `_hours` reference
- [ ] Each child entity has back-reference set (e.g., `contact._contact_holder = holder`)
- [ ] Each child entity has ancestor shortcuts set (e.g., `contact._business = holder._business`)

**Integration Point**: Existing `_populate_children()` methods in each holder class

---

#### FR-DOWN-004: Nested Holder Recursion

| Field | Value |
|-------|-------|
| **ID** | FR-DOWN-004 |
| **Requirement** | Units populated by UnitHolder must themselves have holders fetched |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] After `UnitHolder._populate_children()` creates Unit instances, each Unit's `_fetch_holders_async()` is called
- [ ] Recursion depth: Business -> UnitHolder -> Unit -> OfferHolder -> Offer (4 levels)
- [ ] All Offers under all Units under the Business are populated after full hydration
- [ ] All Processes under all Units under the Business are populated after full hydration

**Integration Point**: `/src/autom8_asana/models/business/business.py` (during `_fetch_holders_async`)

---

#### FR-DOWN-005: Bidirectional Reference Setting

| Field | Value |
|-------|-------|
| **ID** | FR-DOWN-005 |
| **Requirement** | All populated entities have bidirectional references per ADR-0052 |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] `contact._business` points to containing Business
- [ ] `contact._contact_holder` points to containing ContactHolder
- [ ] `unit._business` points to containing Business
- [ ] `unit._unit_holder` points to containing UnitHolder
- [ ] `offer._business` points to ancestor Business
- [ ] `offer._unit` points to containing Unit
- [ ] `offer._offer_holder` points to containing OfferHolder
- [ ] Same pattern for Process, Location, Hours entities
- [ ] Navigation properties (`contact.business`, `offer.unit`, etc.) return cached references

**Integration Point**: All business model entity classes

---

### Upward Traversal (FR-UP-*)

#### FR-UP-001: Contact Upward Traversal

| Field | Value |
|-------|-------|
| **ID** | FR-UP-001 |
| **Requirement** | Given a Contact GID, traverse upward to find and return the containing Business |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] Method accepts Contact GID and AsanaClient
- [ ] Fetches Contact via `client.tasks.get_async(contact_gid)`
- [ ] Uses `contact.parent.gid` to fetch parent (ContactHolder)
- [ ] Identifies parent as ContactHolder via type detection heuristics (FR-UP-005)
- [ ] Uses `holder.parent.gid` to fetch parent (Business)
- [ ] Identifies parent as Business via type detection heuristics
- [ ] Returns typed Business instance with `_contact_holder` populated
- [ ] Sets `contact._contact_holder` and `contact._business` references

**Integration Point**: To be determined by Architect (new method or class method)

---

#### FR-UP-002: Offer Upward Traversal

| Field | Value |
|-------|-------|
| **ID** | FR-UP-002 |
| **Requirement** | Given an Offer GID, traverse upward through OfferHolder, Unit, UnitHolder to find Business |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] Method accepts Offer GID and AsanaClient
- [ ] Fetches Offer via `client.tasks.get_async(offer_gid)`
- [ ] Traverses: Offer -> OfferHolder -> Unit -> UnitHolder -> Business (4 levels)
- [ ] At each level, identifies parent type via heuristics
- [ ] Returns typed Business instance with full path populated
- [ ] Sets all intermediate references (`offer._offer_holder`, `offer._unit`, `offer._business`, etc.)
- [ ] Intermediate entities (OfferHolder, Unit, UnitHolder) are typed correctly

**Integration Point**: To be determined by Architect

---

#### FR-UP-003: Parent Task Fetching

| Field | Value |
|-------|-------|
| **ID** | FR-UP-003 |
| **Requirement** | Upward traversal uses `Task.parent.gid` to fetch parent tasks iteratively |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] Each entity's `parent` field is a `NameGid` with `gid` attribute
- [ ] Calls `client.tasks.get_async(entity.parent.gid)` to fetch parent Task
- [ ] Handles case where `parent` is `None` (reached root, should be Business)
- [ ] Raises `HydrationError` if parent chain exceeds 10 levels (safety limit)
- [ ] Raises `HydrationError` if parent is not a task (project root reached unexpectedly)

**Integration Point**: Traversal logic in new method

---

#### FR-UP-004: Intermediate Type Conversion

| Field | Value |
|-------|-------|
| **ID** | FR-UP-004 |
| **Requirement** | Fetched parent Tasks are converted to typed entities (Business, Unit, Holder) |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] After type detection, Task is converted via `Entity.model_validate(task.model_dump())`
- [ ] Business is instantiated from Task when detected as Business
- [ ] Unit is instantiated from Task when detected as Unit
- [ ] Holders are instantiated from Task when detected as respective holder type
- [ ] Converted entities maintain all Task fields (gid, name, custom_fields, etc.)

**Integration Point**: Type conversion logic in traversal method

---

#### FR-UP-005: Type Detection Heuristics

| Field | Value |
|-------|-------|
| **ID** | FR-UP-005 |
| **Requirement** | Parent task type is detected via name-based heuristics with structure fallback |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] **Business detection**: Name matches business naming pattern OR task has holder children (Contacts, Units, etc.)
- [ ] **Holder detection**: Name matches holder patterns ("Contacts", "Units", "Offers", "Processes", "Location", etc.)
- [ ] **Unit detection**: Parent is UnitHolder (by name) and task has OfferHolder/ProcessHolder children
- [ ] Case-insensitive name matching
- [ ] Logs warning if heuristics are ambiguous
- [ ] Falls back to structure inspection (fetch subtasks, check for holder names) if name match fails

**Integration Point**: Type detection logic in traversal method

**Open Question for Architect**: Should heuristics use Option A (name-based only), Option C (structure inspection), or combination? See DISCOVERY-HYDRATION-001 Section 4.1.

---

### Combined Hydration (FR-FULL-*)

#### FR-FULL-001: Any Entry Point Hydration

| Field | Value |
|-------|-------|
| **ID** | FR-FULL-001 |
| **Requirement** | `hydrate_async()` method enables full hierarchy hydration from any entity type |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] Method signature: `async def hydrate_async(client: AsanaClient) -> Business`
- [ ] Available on Contact, Offer, Unit, or callable with any entity GID
- [ ] Performs upward traversal to find Business root
- [ ] Performs downward hydration to populate full hierarchy
- [ ] Returns fully populated Business with all descendants
- [ ] The entry point entity is part of the hydrated hierarchy (findable via navigation)

**Integration Point**: To be determined by Architect (entity method or factory method)

---

#### FR-FULL-002: Entry Entity Inclusion

| Field | Value |
|-------|-------|
| **ID** | FR-FULL-002 |
| **Requirement** | The entity used as entry point is included in the hydrated result |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] If starting from Offer with GID X, `business.unit_holder.units[n].offer_holder.offers` contains an Offer with GID X
- [ ] Entry entity's local modifications (if any) are preserved in the hydrated hierarchy
- [ ] Entry entity's `_business`, `_unit` (etc.) references point to the hydrated instances

**Integration Point**: Hydration logic

---

### API Surface (FR-API-*)

#### FR-API-001: Business.from_gid_async Enhancement

| Field | Value |
|-------|-------|
| **ID** | FR-API-001 |
| **Requirement** | Existing `Business.from_gid_async(client, gid)` performs full downward hydration |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Fetches Business via `client.tasks.get_async(gid)`
- [ ] Converts to typed Business via `Business.model_validate()`
- [ ] Calls `business._fetch_holders_async(client)` to populate full hierarchy
- [ ] Returns fully hydrated Business with all descendants populated
- [ ] Raises `APIError` if GID is invalid or not a Business

**Integration Point**: `/src/autom8_asana/models/business/business.py` (existing method)

---

#### FR-API-002: Contact.to_business_async

| Field | Value |
|-------|-------|
| **ID** | FR-API-002 |
| **Requirement** | Contact instances can hydrate to their containing Business |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] Method signature: `async def to_business_async(self, client: AsanaClient) -> Business`
- [ ] Performs upward traversal (FR-UP-001)
- [ ] Performs downward hydration from discovered Business (FR-DOWN-001)
- [ ] Returns fully hydrated Business
- [ ] `self._business` is set to the returned Business

**Integration Point**: `/src/autom8_asana/models/business/contact.py`

---

#### FR-API-003: Offer.to_business_async

| Field | Value |
|-------|-------|
| **ID** | FR-API-003 |
| **Requirement** | Offer instances can hydrate to their containing Business |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] Method signature: `async def to_business_async(self, client: AsanaClient) -> Business`
- [ ] Performs upward traversal (FR-UP-002)
- [ ] Performs downward hydration from discovered Business
- [ ] Returns fully hydrated Business
- [ ] `self._business` and `self._unit` are set to the hydrated instances

**Integration Point**: `/src/autom8_asana/models/business/offer.py`

---

### Error Handling (FR-ERROR-*)

#### FR-ERROR-001: HydrationError Exception

| Field | Value |
|-------|-------|
| **ID** | FR-ERROR-001 |
| **Requirement** | New exception type for hydration failures |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Class: `HydrationError(AsanaError)`
- [ ] Attributes: `entity_gid`, `entity_type`, `phase` (upward/downward), `cause`
- [ ] Message format: `"Hydration failed for {entity_type} {entity_gid} during {phase}: {cause}"`
- [ ] Located in `/src/autom8_asana/exceptions.py`
- [ ] Caught as `AsanaError` for backward compatibility

**Integration Point**: `/src/autom8_asana/exceptions.py`

---

#### FR-ERROR-002: Partial Hydration Handling

| Field | Value |
|-------|-------|
| **ID** | FR-ERROR-002 |
| **Requirement** | If one branch fails during hydration, other branches continue (configurable) |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] Default behavior: Fail entire hydration on any error (consistent, safe)
- [ ] Optional `fail_fast=False` parameter allows partial hydration
- [ ] With `fail_fast=False`, failed branches are set to `None` or empty list
- [ ] Returns `HydrationResult` with `succeeded` and `failed` lists when partial
- [ ] Log warnings for failed branches

**Open Question for Architect**: Should partial hydration return `HydrationResult` or raise with partial data? See DISCOVERY-HYDRATION-001 Section 4.4.

---

#### FR-ERROR-003: Type Detection Failure

| Field | Value |
|-------|-------|
| **ID** | FR-ERROR-003 |
| **Requirement** | Raise clear error when parent type cannot be determined |
| **Priority** | Should |
| **Acceptance Criteria** | |

- [ ] If type heuristics fail, raise `HydrationError` with cause "Unable to determine type of parent task {gid}"
- [ ] Error message includes parent task name for debugging
- [ ] Suggests checking task naming conventions

**Integration Point**: Type detection logic

---

#### FR-ERROR-004: Cycle Detection

| Field | Value |
|-------|-------|
| **ID** | FR-ERROR-004 |
| **Requirement** | Detect and prevent infinite loops during traversal |
| **Priority** | Must |
| **Acceptance Criteria** | |

- [ ] Track visited GIDs during upward traversal
- [ ] If GID is revisited, raise `HydrationError` with cause "Cycle detected: {gid} already visited"
- [ ] Maximum traversal depth of 10 levels (configurable)
- [ ] Raise `HydrationError` if depth exceeded

**Integration Point**: Traversal logic

---

### Non-Functional Requirements

#### NFR-PERF-001: Concurrent Holder Fetching

| Field | Value |
|-------|-------|
| **ID** | NFR-PERF-001 |
| **Requirement** | Holders at the same level are fetched concurrently |
| **Target** | Concurrent fetches within each level |
| **Measurement** | Trace API calls; verify parallel execution |

**Acceptance Criteria**:
- [ ] Business-level holders (ContactHolder, UnitHolder, LocationHolder, etc.) fetched via `asyncio.gather()`
- [ ] Unit-level holders (OfferHolder, ProcessHolder) fetched via `asyncio.gather()`
- [ ] Levels are sequential (Business level completes before Unit level)
- [ ] Rate limiting respected (existing client constraints)

**Integration Point**: `_fetch_holders_async()` implementations

---

#### NFR-PERF-002: API Call Efficiency

| Field | Value |
|-------|-------|
| **ID** | NFR-PERF-002 |
| **Requirement** | Full business hydration completes in reasonable number of API calls |
| **Target** | < 30 API calls for typical hierarchy (1 Business, 5 Contacts, 3 Units, 10 Offers, 5 Processes) |
| **Measurement** | Count API calls in integration test |

**Acceptance Criteria**:
- [ ] One `get_async()` call for Business
- [ ] One `subtasks_async().collect()` call per holder/entity with children
- [ ] No redundant fetches (same entity not fetched twice)
- [ ] Upward traversal: max 5 `get_async()` calls (one per level)

---

#### NFR-PERF-003: Memory Efficiency

| Field | Value |
|-------|-------|
| **ID** | NFR-PERF-003 |
| **Requirement** | Hydrated hierarchy does not cause excessive memory growth |
| **Target** | < 10MB for typical business hierarchy |
| **Measurement** | Memory profiling in test |

**Acceptance Criteria**:
- [ ] Entities store only necessary fields (no duplicate data)
- [ ] Back-references are pointers, not copies
- [ ] No memory leaks from circular references (Pydantic handles)

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
- [ ] No `# type: ignore` except where unavoidable
- [ ] Generic types used correctly (e.g., `list[Contact]`)
- [ ] `TYPE_CHECKING` used for circular import avoidance

---

#### NFR-SAFE-002: Test Coverage

| Field | Value |
|-------|-------|
| **ID** | NFR-SAFE-002 |
| **Requirement** | New hydration code has > 80% test coverage |
| **Target** | > 80% coverage |
| **Measurement** | `pytest --cov` |

**Acceptance Criteria**:
- [ ] Unit tests for `_fetch_holders_async()` methods
- [ ] Unit tests for upward traversal
- [ ] Unit tests for type detection heuristics
- [ ] Integration tests for full hydration scenarios
- [ ] Edge case tests (empty holders, missing parents)

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
- [ ] Existing SaveSession tests unchanged and passing
- [ ] `track(entity, recursive=True)` works with hydrated hierarchies
- [ ] No breaking changes to public API signatures

---

## User Stories / Use Cases

### US-001: Webhook Handler for Contact Update

**As a** webhook handler developer
**I want to** receive a Contact GID and load the full Business context
**So that** I can access Business-level settings when processing Contact changes

**Scenario**:
```python
async def handle_contact_webhook(contact_gid: str):
    contact = await client.tasks.get_async(contact_gid)
    contact = Contact.model_validate(contact.model_dump())

    # NEW: Hydrate to full Business context
    business = await contact.to_business_async(client)

    # Now can access Business-level data
    office_phone = business.office_phone
    primary_location = business.location_holder.primary_location

    # And still navigate to the Contact
    assert contact.gid in [c.gid for c in business.contact_holder.contacts]
```

---

### US-002: Search Results with Business Context

**As a** search feature developer
**I want to** take an Offer GID from search results and load its Business
**So that** I can display the Business name alongside the Offer

**Scenario**:
```python
async def display_offer_with_business(offer_gid: str):
    # Get Offer from search result GID
    offer_task = await client.tasks.get_async(offer_gid)
    offer = Offer.model_validate(offer_task.model_dump())

    # NEW: Hydrate to Business
    business = await offer.to_business_async(client)

    # Display
    print(f"Offer: {offer.name}")
    print(f"Business: {business.name}")
    print(f"Unit: {offer.unit.name}")  # Intermediate Unit also available
```

---

### US-003: Batch Process with Business Context

**As a** batch operation developer
**I want to** load a Business and all its children in one call
**So that** I can process the entire hierarchy without individual fetches

**Scenario**:
```python
async def process_business_hierarchy(business_gid: str):
    # NEW: Load fully hydrated Business
    business = await Business.from_gid_async(client, business_gid)

    # All children are populated
    for contact in business.contact_holder.contacts:
        process_contact(contact)

    for unit in business.unit_holder.units:
        for offer in unit.offer_holder.offers:
            process_offer(offer)
        for process in unit.process_holder.processes:
            process_process(process)
```

---

### US-004: Deep Link Navigation

**As a** UI developer
**I want to** take a task GID from a deep link and determine its type and context
**So that** I can display the appropriate UI with full navigation

**Scenario**:
```python
async def handle_deep_link(task_gid: str):
    task = await client.tasks.get_async(task_gid)

    # Detect type and hydrate appropriately
    if is_offer(task):
        offer = Offer.model_validate(task.model_dump())
        business = await offer.to_business_async(client)
        show_offer_page(offer, business)
    elif is_contact(task):
        contact = Contact.model_validate(task.model_dump())
        business = await contact.to_business_async(client)
        show_contact_page(contact, business)
    # etc.
```

---

## Assumptions

1. **`subtasks_async()` is available**: Discovery confirmed this is implemented (ADR-0057)

2. **Name-based type detection is reliable**: Business model follows naming conventions (Contacts, Units, Offers, etc.) that are unlikely to change

3. **Hierarchy depth is bounded**: Maximum 5 levels down, 5 levels up; no infinite hierarchies exist in practice

4. **Partial hydration is acceptable default behavior**: Most users want fail-fast; partial hydration is opt-in for advanced cases

5. **Client reference is available**: Entities have `_client` reference (per ADR-0063) or client is passed to hydration methods

6. **Concurrent fetching is safe**: Asana API handles concurrent requests within rate limits

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| `subtasks_async()` method | TasksClient | Implemented (ADR-0057) |
| `Task.parent` field as `NameGid` | Task model | Implemented |
| `_populate_holders()` method | Business, Unit | Implemented |
| `_populate_children()` method | All Holders | Implemented |
| ADR-0052 caching pattern | All entities | Implemented |
| ADR-0053 recursive tracking | SaveSession | Implemented |

---

## Open Questions

| # | Question | Owner | Due Date | Resolution |
|---|----------|-------|----------|------------|
| Q1 | Type detection strategy: name-based only, structure inspection, or combination? | Architect | Session 3 | Recommendation: Option A (names) with Option C fallback |
| Q2 | Should `hydrate_async()` be an instance method or factory function? | Architect | Session 3 | - |
| Q3 | Concurrent fetching: within-level only or full concurrent? | Architect | Session 3 | Recommendation: within-level (Option B from Discovery) |
| Q4 | Partial failure: return `HydrationResult` or raise with partial data? | Architect | Session 3 | Recommendation: Option C (HydrationResult) |
| Q5 | API location: entity methods, factory methods, or both? | Architect | Session 3 | Recommendation: both (Option B+C from Discovery) |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Requirements Analyst | Initial PRD based on DISCOVERY-HYDRATION-001 |

---

## Appendix: Hierarchy Diagram

```
Business (Level 0)
  |
  +-- ContactHolder (Level 1)
  |     +-- Contact (Level 2)
  |     +-- Contact
  |     +-- ...
  |
  +-- UnitHolder (Level 1)
  |     +-- Unit (Level 2)
  |     |     +-- OfferHolder (Level 3)
  |     |     |     +-- Offer (Level 4)
  |     |     |     +-- Offer
  |     |     |     +-- ...
  |     |     +-- ProcessHolder (Level 3)
  |     |           +-- Process (Level 4)
  |     |           +-- Process
  |     |           +-- ...
  |     +-- Unit
  |           +-- OfferHolder
  |           +-- ProcessHolder
  |
  +-- LocationHolder (Level 1)
  |     +-- Location (Level 2)
  |     +-- Hours (Level 2)
  |
  +-- DNAHolder (Level 1)
  +-- ReconciliationsHolder (Level 1)
  +-- AssetEditHolder (Level 1)
  +-- VideographyHolder (Level 1)
```

**Maximum depth**: 4 levels (Business -> UnitHolder -> Unit -> OfferHolder -> Offer)

---

## Appendix: API Call Sequence (P0 Downward)

```
1. get_async(business_gid)                      -> Business
2. subtasks_async(business.gid).collect()       -> [ContactHolder, UnitHolder, LocationHolder, ...]
3. subtasks_async(contact_holder.gid).collect() -> [Contact, Contact, ...]
4. subtasks_async(unit_holder.gid).collect()    -> [Unit, Unit, ...]
5. subtasks_async(location_holder.gid).collect()-> [Location, Hours]
6. (for each Unit) subtasks_async(unit.gid).collect() -> [OfferHolder, ProcessHolder]
7. (for each OfferHolder) subtasks_async(offer_holder.gid).collect() -> [Offer, Offer, ...]
8. (for each ProcessHolder) subtasks_async(process_holder.gid).collect() -> [Process, Process, ...]
```

**Total for 3 Units**: 1 + 1 + 3 (holders) + 3 (units) + 6 (offer+process holders) = ~14 API calls

---

## Quality Gates Checklist

- [x] Problem statement is clear and compelling
- [x] Scope explicitly defines in/out
- [x] All requirements are specific and testable
- [x] Acceptance criteria defined for each requirement
- [x] Assumptions documented
- [x] Open questions have owners assigned (Architect, Session 3)
- [x] Dependencies identified with status
- [x] Success metrics are quantified
