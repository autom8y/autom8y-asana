# PRD-05: Navigation & Hydration

> Consolidated PRD for entity relationships, hierarchy hydration, and holder factory patterns.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: PRD-0013 (Hierarchy Hydration), PRD-0017 (Navigation Descriptors), PRD-0020 (Holder Factory)
- **Related TDD**: TDD-07-navigation-hydration
- **Related ADRs**: ADR-0050 (Holder Lazy Loading), ADR-0052 (Bidirectional References), ADR-0053 (Recursive Tracking), ADR-0057 (subtasks_async), ADR-0082 (Fields auto-generation)

---

## Executive Summary

The SDK's business layer requires three interconnected capabilities: (1) bidirectional navigation between entities using descriptor-based patterns, (2) hierarchy hydration from any entry point in the entity tree, and (3) declarative holder factories that eliminate ~800+ lines of duplicated code. This PRD consolidates requirements for unified navigation patterns, complete hierarchy traversal, and factory-based holder generation.

---

## Problem Statement

### Current State

The SDK supports business model hierarchies (Business -> Units -> Offers, etc.) but faces three critical gaps:

**1. Hydration Limited to Business Root**
- `_fetch_holders_async()` methods are stubbed with placeholder implementations
- Users cannot hydrate business hierarchies from arbitrary entry points (Contact, Offer, Process)
- Webhook handlers receive entity GIDs but cannot navigate to the containing Business

**2. Navigation Code Duplication**
- ~800+ lines of duplicated navigation code across 10 business entities
- Each entity independently implements identical patterns for navigation properties, holder population, and reference invalidation
- `_invalidate_refs()` exists on all entities but is never called automatically

**3. Holder Boilerplate**
- 4 near-identical holder implementations (DNAHolder, ReconciliationHolder, AssetEditHolder, VideographyHolder)
- Each holder requires ~65-75 lines of code, totaling ~300 lines of duplicated structure
- Adding new holder types requires copying and modifying boilerplate

### Who Is Affected

- **Webhook handler developers**: Receive entity GIDs, need full hierarchy context
- **SDK maintainers**: Must update navigation logic across 10+ files when patterns change
- **Search feature implementers**: Return entity GIDs from search, need navigation to Business
- **Batch operation developers**: Process multiple entities, need Business context for each

### Impact of Not Solving

- Incomplete SDK with partially implemented business model layer
- Bug propagation risk: fix in one entity must be replicated to 9 others manually
- Manual traversal defeats purpose of typed models
- Webhook handlers cannot access parent Business data
- Stale reference risk from manual invalidation

---

## Goals & Non-Goals

### Goals

| ID | Goal | Success Metric |
|----|------|----------------|
| G1 | Complete hierarchy hydration from any entity | `contact.to_business_async()` returns populated Business |
| G2 | Eliminate navigation code duplication | Reduce from ~800 lines to <200 lines |
| G3 | Enable automatic reference invalidation | `_invalidate_refs()` called on hierarchy changes |
| G4 | Simplify holder creation | New holder requires <10 lines of code |
| G5 | Preserve type safety | mypy strict mode passes |
| G6 | Maintain backward compatibility | All existing tests pass unchanged |

### Non-Goals

| Item | Rationale |
|------|-----------|
| SDK core entity navigation | SDK entities use `NameGid` static references, no navigation patterns |
| Batch hydration (multiple GIDs) | Composable from single-GID hydration |
| Incremental/delta hydration | Requires change tracking beyond current scope |
| Hydration caching across sessions | Conflicts with freshness; separate concern |
| `__getattr__` magic for holder access | Explicit properties are intentional for type safety |
| Emoji-based holder detection | Name matching is sufficient |

---

## Requirements

### Navigation Descriptors (FR-DESC)

#### FR-DESC-001: ParentRef Descriptor

| Field | Value |
|-------|-------|
| **ID** | FR-DESC-001 |
| **Requirement** | `ParentRef` descriptor provides cached upward navigation with lazy resolution |
| **Priority** | Must |

**Acceptance Criteria**:
- [ ] `contact.business` returns cached `Business` instance via descriptor
- [ ] If `_business` is `None`, resolves via `_contact_holder._business`
- [ ] Type-safe with `Generic[T]` for IDE autocomplete
- [ ] Returns `None` for uninitialized references (not AttributeError)

#### FR-DESC-002: HolderRef Descriptor

| Field | Value |
|-------|-------|
| **ID** | FR-DESC-002 |
| **Requirement** | `HolderRef` descriptor provides direct holder property access |
| **Priority** | Must |

**Acceptance Criteria**:
- [ ] `business.contact_holder` returns `ContactHolder` via descriptor
- [ ] Type-safe with `Generic[T]` for IDE autocomplete
- [ ] Preserves docstrings for IDE documentation

#### FR-DESC-003: Auto-Invalidation on Reference Change

| Field | Value |
|-------|-------|
| **ID** | FR-DESC-003 |
| **Requirement** | Setting parent reference triggers `_invalidate_refs()` automatically |
| **Priority** | Must |

**Acceptance Criteria**:
- [ ] Setting `contact._contact_holder = new_holder` triggers `_invalidate_refs()`
- [ ] Read access does not trigger invalidation
- [ ] Configurable via `auto_invalidate` parameter

### Holder Consolidation (FR-HOLD)

#### FR-HOLD-001: HolderMixin Base Implementation

| Field | Value |
|-------|-------|
| **ID** | FR-HOLD-001 |
| **Requirement** | `HolderMixin._populate_children()` implemented in base class |
| **Priority** | Must |

**Acceptance Criteria**:
- [ ] Base method handles sorting, typing, reference setting
- [ ] Uses `CHILD_TYPE` ClassVar for child type resolution
- [ ] Uses `PARENT_REF_NAME` ClassVar for holder reference
- [ ] Uses `BUSINESS_REF_NAME` ClassVar for business reference
- [ ] Child sorting remains stable (created_at, then name)

#### FR-HOLD-002: HolderFactory with `__init_subclass__`

| Field | Value |
|-------|-------|
| **ID** | FR-HOLD-002 |
| **Requirement** | `HolderFactory` base class enables declarative holder definitions |
| **Priority** | Should |

**Acceptance Criteria**:
- [ ] Accepts `child_type`, `parent_ref`, `children_attr`, `semantic_alias` arguments
- [ ] Auto-generates ClassVars (CHILD_TYPE, PARENT_REF_NAME, CHILDREN_ATTR)
- [ ] Provides generic `_populate_children()` implementation
- [ ] Dynamic import resolution to avoid circular imports
- [ ] Auto-generates `children` and `business` properties
- [ ] New holder type requires 3-5 lines of code

### Downward Hydration (FR-DOWN)

#### FR-DOWN-001: Business Holder Fetching

| Field | Value |
|-------|-------|
| **ID** | FR-DOWN-001 |
| **Requirement** | `Business._fetch_holders_async()` fetches all immediate holder subtasks and populates typed holders |
| **Priority** | Must |

**Acceptance Criteria**:
- [ ] Replaces stub implementation in `business.py`
- [ ] Calls `client.tasks.subtasks_async(self.gid).collect()` to fetch holder tasks
- [ ] Calls `self._populate_holders(subtasks)` with fetched tasks
- [ ] For each populated holder, fetches holder's subtasks
- [ ] Calls `holder._populate_children(holder_subtasks)` for each holder
- [ ] Sets bidirectional references per ADR-0052

#### FR-DOWN-002: Unit Holder Fetching

| Field | Value |
|-------|-------|
| **ID** | FR-DOWN-002 |
| **Requirement** | `Unit._fetch_holders_async()` fetches OfferHolder and ProcessHolder subtasks |
| **Priority** | Must |

**Acceptance Criteria**:
- [ ] Replaces stub implementation in `unit.py`
- [ ] Populates OfferHolder and ProcessHolder with subtasks
- [ ] Sets intermediate references (`holder._unit`, `holder._business`)

#### FR-DOWN-003: Nested Holder Recursion

| Field | Value |
|-------|-------|
| **ID** | FR-DOWN-003 |
| **Requirement** | Units populated by UnitHolder have their holders fetched recursively |
| **Priority** | Must |

**Acceptance Criteria**:
- [ ] Recursion depth: Business -> UnitHolder -> Unit -> OfferHolder -> Offer (4 levels)
- [ ] All Offers and Processes under all Units are populated after full hydration

### Upward Traversal (FR-UP)

#### FR-UP-001: Contact Upward Traversal

| Field | Value |
|-------|-------|
| **ID** | FR-UP-001 |
| **Requirement** | Given a Contact GID, traverse upward to find the containing Business |
| **Priority** | Should |

**Acceptance Criteria**:
- [ ] Fetches Contact via `client.tasks.get_async(contact_gid)`
- [ ] Uses `contact.parent.gid` to fetch parent (ContactHolder)
- [ ] Identifies parent type via detection heuristics
- [ ] Returns typed Business with bidirectional references set

#### FR-UP-002: Offer Upward Traversal

| Field | Value |
|-------|-------|
| **ID** | FR-UP-002 |
| **Requirement** | Given an Offer GID, traverse upward through 4 levels to find Business |
| **Priority** | Should |

**Acceptance Criteria**:
- [ ] Traverses: Offer -> OfferHolder -> Unit -> UnitHolder -> Business
- [ ] At each level, identifies parent type via heuristics
- [ ] Sets all intermediate references

#### FR-UP-003: Type Detection Heuristics

| Field | Value |
|-------|-------|
| **ID** | FR-UP-003 |
| **Requirement** | Parent task type is detected via name-based heuristics |
| **Priority** | Should |

**Acceptance Criteria**:
- [ ] Business detection: Name matches pattern OR has holder children
- [ ] Holder detection: Name matches patterns ("Contacts", "Units", "Offers", etc.)
- [ ] Case-insensitive name matching
- [ ] Maximum traversal depth of 10 levels (safety limit)

### Combined Hydration (FR-FULL)

#### FR-FULL-001: Any Entry Point Hydration

| Field | Value |
|-------|-------|
| **ID** | FR-FULL-001 |
| **Requirement** | `hydrate_async()` or `to_business_async()` enables full hierarchy hydration from any entity |
| **Priority** | Should |

**Acceptance Criteria**:
- [ ] Method signature: `async def to_business_async(self, client: AsanaClient) -> Business`
- [ ] Available on Contact, Offer, Unit entities
- [ ] Performs upward traversal to find Business root
- [ ] Performs downward hydration to populate full hierarchy
- [ ] Entry point entity is part of the hydrated hierarchy

### Error Handling (FR-ERROR)

#### FR-ERROR-001: HydrationError Exception

| Field | Value |
|-------|-------|
| **ID** | FR-ERROR-001 |
| **Requirement** | New exception type for hydration failures |
| **Priority** | Must |

**Acceptance Criteria**:
- [ ] Class: `HydrationError(AsanaError)`
- [ ] Attributes: `entity_gid`, `entity_type`, `phase` (upward/downward), `cause`
- [ ] Located in `/src/autom8_asana/exceptions.py`

#### FR-ERROR-002: Cycle Detection

| Field | Value |
|-------|-------|
| **ID** | FR-ERROR-002 |
| **Requirement** | Detect and prevent infinite loops during traversal |
| **Priority** | Must |

**Acceptance Criteria**:
- [ ] Track visited GIDs during upward traversal
- [ ] Raise `HydrationError` if GID is revisited
- [ ] Maximum traversal depth of 10 levels

### Naming Standardization (FR-NAME)

#### FR-NAME-001: Reconciliation Holder Rename

| Field | Value |
|-------|-------|
| **ID** | FR-NAME-001 |
| **Requirement** | `_reconciliations_holder` renamed to `_reconciliation_holder` (singular) |
| **Priority** | Must |

**Acceptance Criteria**:
- [ ] All occurrences updated: model, HOLDER_KEY_MAP key, tests
- [ ] Property renamed to `reconciliation_holder`
- [ ] Deprecation alias for `reconciliations_holder` provided with warning

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-001 | Navigation property access latency | < 100ns | Benchmark test |
| NFR-002 | Concurrent holder fetching | Within each level | asyncio.gather() usage |
| NFR-003 | API call efficiency | < 30 calls for typical hierarchy | Trace logging |
| NFR-004 | Memory efficiency | < 10MB for typical hierarchy | Memory profiler |
| NFR-005 | Type safety | mypy clean | `mypy src/autom8_asana --strict` |
| NFR-006 | Test coverage | > 80% | pytest --cov |
| NFR-007 | Lines removed | >= 500 | LOC diff |

---

## User Stories

### US-001: Webhook Handler for Contact Update

**As a** webhook handler developer
**I want to** receive a Contact GID and load the full Business context
**So that** I can access Business-level settings when processing Contact changes

```python
async def handle_contact_webhook(contact_gid: str):
    contact = await client.tasks.get_async(contact_gid)
    contact = Contact.model_validate(contact.model_dump())

    # Hydrate to full Business context
    business = await contact.to_business_async(client)

    # Access Business-level data
    office_phone = business.office_phone
    primary_location = business.location_holder.primary_location
```

### US-002: Search Results with Business Context

**As a** search feature developer
**I want to** take an Offer GID from search results and load its Business
**So that** I can display the Business name alongside the Offer

```python
async def display_offer_with_business(offer_gid: str):
    offer_task = await client.tasks.get_async(offer_gid)
    offer = Offer.model_validate(offer_task.model_dump())

    # Hydrate to Business
    business = await offer.to_business_async(client)

    print(f"Offer: {offer.name}")
    print(f"Business: {business.name}")
    print(f"Unit: {offer.unit.name}")  # Intermediate Unit also available
```

### US-003: Batch Process with Business Context

**As a** batch operation developer
**I want to** load a Business and all its children in one call
**So that** I can process the entire hierarchy without individual fetches

```python
async def process_business_hierarchy(business_gid: str):
    # Load fully hydrated Business
    business = await Business.from_gid_async(client, business_gid)

    # All children are populated
    for contact in business.contact_holder.contacts:
        process_contact(contact)

    for unit in business.unit_holder.units:
        for offer in unit.offer_holder.offers:
            process_offer(offer)
```

### US-004: Navigation Property Usage

**As a** SDK consumer
**I want to** navigate entity hierarchies using typed properties
**So that** I can access parent entities with IDE support

```python
business = await Business.from_gid_async(client, "123")

for contact in business.contacts:
    # Upward navigation works via descriptor
    assert contact.business is business
    assert contact.contact_holder is business.contact_holder

for unit in business.units:
    for offer in unit.offers:
        # Multi-level navigation works
        assert offer.unit is unit
        assert offer.business is business
```

### US-005: Automatic Reference Invalidation

**As a** SDK consumer
**I want** cached references to be invalidated automatically on hierarchy changes
**So that** I don't need to remember manual invalidation calls

```python
# Before: Manual invalidation required (error-prone)
contact._contact_holder = new_holder
contact._invalidate_refs()  # Easy to forget!

# After: Auto-invalidation (descriptor handles it)
contact._contact_holder = new_holder
# _invalidate_refs() called automatically by descriptor __set__
assert contact._business is None  # Cleared automatically
```

### US-006: Declarative Holder Definition

**As a** SDK maintainer
**I want to** define new holders in 3-5 lines
**So that** I can add new holder types without copy-paste boilerplate

```python
# Before: ~70 lines per holder
class DNAHolder(Task, HolderMixin[Task]):
    CHILD_TYPE: ClassVar[type[Task]] = Task
    PARENT_REF_NAME: ClassVar[str] = "_dna_holder"
    # ... 60+ more lines of boilerplate ...

# After: 3-5 lines per holder
class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
    """Holder for DNA children."""
    pass
```

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| `contact.business` from Contact GID | `None` | Returns populated `Business` | Integration test |
| `unit.offers` from Unit GID | `[]` | Returns populated `list[Offer]` | Integration test |
| `offer.business.contacts` navigation | Fails | Returns populated list | Integration test |
| Lines of navigation code | ~800 | <300 | LOC count |
| `_populate_children()` implementations | 9 | 1 (base) + overrides | grep count |
| Auto-invalidation coverage | 0% | 100% of parent changes | Test coverage |
| API calls for typical hierarchy | N/A | < 30 calls | Trace logging |
| New holder definition lines | ~70 | <10 | Code review |
| Type hint accuracy | N/A | 100% mypy clean | mypy strict |
| Existing test pass rate | 100% | 100% | pytest suite |

---

## Dependencies

| Dependency | Owner | Status | Notes |
|------------|-------|--------|-------|
| `subtasks_async()` method | TasksClient | Implemented | Per ADR-0057 |
| `Task.parent` field as `NameGid` | Task model | Implemented | |
| `_populate_holders()` method | Business, Unit | Implemented | |
| `_populate_children()` method | All Holders | Implemented | |
| ADR-0052 caching pattern | All entities | Implemented | |
| ADR-0053 recursive tracking | SaveSession | Implemented | |
| Python 3.10+ Generics | Python | Stable | For Generic[T] descriptor support |
| Pydantic PrivateAttr | Pydantic Library | Stable | Descriptors work with PrivateAttr |

---

## Hierarchy Reference

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
  +-- ReconciliationHolder (Level 1)
  +-- AssetEditHolder (Level 1)
  +-- VideographyHolder (Level 1)
```

**Maximum depth**: 4 levels (Business -> UnitHolder -> Unit -> OfferHolder -> Offer)

---

## API Call Sequence (Downward Hydration)

```
1. get_async(business_gid)                      -> Business
2. subtasks_async(business.gid).collect()       -> [ContactHolder, UnitHolder, ...]
3. subtasks_async(contact_holder.gid).collect() -> [Contact, Contact, ...]
4. subtasks_async(unit_holder.gid).collect()    -> [Unit, Unit, ...]
5. subtasks_async(location_holder.gid).collect()-> [Location, Hours]
6. (for each Unit) subtasks_async(unit.gid).collect() -> [OfferHolder, ProcessHolder]
7. (for each OfferHolder) subtasks_async().collect()  -> [Offer, Offer, ...]
8. (for each ProcessHolder) subtasks_async().collect()-> [Process, Process, ...]
```

**Total for 3 Units**: ~14 API calls (1 + 1 + 3 holders + 3 units + 6 offer+process holders)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Requirements Analyst | PRD-0013 (Hierarchy Hydration) |
| 1.0 | 2025-12-16 | Requirements Analyst | PRD-0017 (Navigation Descriptors) |
| 1.0 | 2025-12-16 | Requirements Analyst | PRD-0020 (Holder Factory) |
| 2.0 | 2025-12-25 | Tech Writer | Consolidated into PRD-05 |
