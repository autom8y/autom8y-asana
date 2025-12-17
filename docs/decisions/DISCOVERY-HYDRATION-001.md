# DISCOVERY-HYDRATION-001: Business Model Hydration Infrastructure

## Metadata

- **Initiative**: Business Model Hydration (Phase 2 Completion)
- **Session**: 1 - Discovery
- **Author**: Requirements Analyst
- **Date**: 2025-12-16
- **Status**: Discovery Complete - Ready for PRD

---

## Executive Summary

This discovery documents the infrastructure required to hydrate business model hierarchies from any task entry point. The key finding is that **all foundational infrastructure exists**--the missing piece is implementing the stubbed `_fetch_holders_async()` methods in each BusinessEntity subclass.

**Key Constraint**: Traversal may span 10-11 levels (5 up to Business, 5 down to leaves).

---

## 1. Infrastructure Inventory

### 1.1 Entity Type Table

| Entity Type | Parent Type | Holder Type | Navigation Properties | Population Methods | Custom Fields |
|-------------|-------------|-------------|----------------------|-------------------|---------------|
| **Business** | (root) | - | `contact_holder`, `unit_holder`, `location_holder`, `dna_holder`, `reconciliations_holder`, `asset_edit_holder`, `videography_holder` | `_populate_holders()`, `_fetch_holders_async()` (stub) | 19 fields |
| **ContactHolder** | Business | HolderMixin[Contact] | `business`, `contacts`, `owner` | `_populate_children()` | - |
| **Contact** | ContactHolder | - | `business`, `contact_holder` | - | 19 fields |
| **UnitHolder** | Business | HolderMixin[Unit] | `business`, `units` | `_populate_children()` | - |
| **Unit** | UnitHolder | - | `business`, `unit_holder`, `offer_holder`, `process_holder`, `offers`, `processes` | `_populate_holders()`, `_fetch_holders_async()` (stub) | 31 fields |
| **OfferHolder** | Unit | HolderMixin[Offer] | `unit`, `business`, `offers`, `active_offers` | `_populate_children()` | - |
| **Offer** | OfferHolder | - | `unit`, `business`, `offer_holder` | - | 39 fields |
| **ProcessHolder** | Unit | HolderMixin[Process] | `unit`, `business`, `processes` | `_populate_children()` | - |
| **Process** | ProcessHolder | - | `unit`, `business`, `process_holder` | - | 9 fields |
| **LocationHolder** | Business | HolderMixin[Location] | `business`, `locations`, `hours`, `primary_location` | `_populate_children()` | - |
| **Location** | LocationHolder | - | `business`, `location_holder` | - | 8 fields |
| **Hours** | LocationHolder | - | `business`, `location_holder` | - | 9 fields |

**Stub Holders** (Business-level, typed as plain Task children):
- `DNAHolder`, `ReconciliationsHolder`, `AssetEditHolder`, `VideographyHolder`

### 1.2 Hierarchy Depth Analysis

```
Business (Level 0)
  +-- ContactHolder (Level 1)
  |     +-- Contact (Level 2)
  +-- UnitHolder (Level 1)
  |     +-- Unit (Level 2)
  |           +-- OfferHolder (Level 3)
  |           |     +-- Offer (Level 4)
  |           +-- ProcessHolder (Level 3)
  |                 +-- Process (Level 4)
  +-- LocationHolder (Level 1)
  |     +-- Location (Level 2)
  |     +-- Hours (Level 2)
  +-- DNAHolder (Level 1)
  |     +-- Task (Level 2)
  ...
```

**Maximum downward depth from Business**: 4 levels (Business -> UnitHolder -> Unit -> OfferHolder -> Offer)
**Maximum upward depth to Business**: 4 levels (Offer -> OfferHolder -> Unit -> UnitHolder -> Business)

### 1.3 Available Client Methods for Fetching Tasks

| Method | Signature | Purpose | Status |
|--------|-----------|---------|--------|
| `get_async()` | `get_async(task_gid: str, *, opt_fields: list[str] | None = None) -> Task` | Fetch single task by GID | Implemented |
| `list_async()` | `list_async(*, project: str | None = None, ...) -> PageIterator[Task]` | List tasks with filters | Implemented |
| `subtasks_async()` | `subtasks_async(task_gid: str, *, opt_fields: list[str] | None = None) -> PageIterator[Task]` | Fetch subtasks of a parent | **Implemented** (per ADR-0057) |

**Critical Finding**: `subtasks_async()` IS implemented in `tasks.py` (lines 540-585) despite ADR-0057 having "Proposed" status. The implementation is complete and matches the ADR specification.

### 1.4 Upward Traversal Infrastructure

#### Task.parent Field

```python
# Task model (task.py:69)
parent: NameGid | None = None  # Changed from dict
```

The `parent` field contains a `NameGid` reference with:
- `gid`: Parent task GID (string, required)
- `name`: Parent task name (string, optional)
- `resource_type`: Always "task" (string, optional)

#### NameGid Structure

```python
# common.py:13-49
class NameGid(BaseModel):
    model_config = ConfigDict(frozen=True)
    gid: str
    name: str | None = None
    resource_type: str | None = None
```

**Key property**: NameGid is immutable (frozen), hashable, and provides only the GID--not the full task data.

#### Upward Navigation Pattern

Current pattern in business entities:

```python
# Example from Offer (offer.py:161-174)
@property
def business(self) -> Business | None:
    if self._business is None:
        unit = self.unit
        if unit is not None:
            self._business = unit.business
    return self._business
```

**Gap**: This relies on cached `_unit` reference being set by holder population. If an Offer is fetched directly (not through hierarchy), `_unit` is None and upward traversal fails.

### 1.5 Downward Population Infrastructure

#### `_populate_holders()` Pattern

```python
# Business._populate_holders() (business.py:419-434)
def _populate_holders(self, subtasks: list[Task]) -> None:
    for subtask in subtasks:
        holder_key = self._identify_holder(subtask)
        if holder_key:
            holder = self._create_typed_holder(holder_key, subtask)
            setattr(self, f"_{holder_key}", holder)
```

**Key behaviors**:
1. Iterates through fetched subtasks
2. Identifies holder type via `_identify_holder()` (name matching, emoji fallback)
3. Creates typed holder via `_create_typed_holder()`
4. Sets back-reference to parent (`holder._business = self`)

#### `_populate_children()` Pattern

```python
# ContactHolder._populate_children() (contact.py:446-465)
def _populate_children(self, subtasks: list[Task]) -> None:
    sorted_tasks = sorted(subtasks, key=lambda t: (t.created_at or "", t.name or ""))
    self._contacts = []
    for task in sorted_tasks:
        contact = Contact.model_validate(task.model_dump())
        contact._contact_holder = self
        contact._business = self._business
        self._contacts.append(contact)
```

**Key behaviors**:
1. Sorts subtasks by created_at (oldest first)
2. Converts Task to typed entity via `model_validate()`
3. Sets bidirectional back-references
4. Stores in typed collection

### 1.6 Cached Reference Patterns (per ADR-0052)

Each entity stores:
1. **Direct parent reference**: `_contact_holder`, `_unit_holder`, `_offer_holder`, etc.
2. **Ancestor shortcuts**: `_business`, `_unit` (lazy-populated on access)
3. **Invalidation method**: `_invalidate_refs()` clears cached references

Example cache pattern:
```python
# Offer._business is populated via lazy evaluation
@property
def business(self) -> Business | None:
    if self._business is None:
        unit = self.unit  # Triggers Unit's business resolution
        if unit is not None:
            self._business = unit.business
    return self._business
```

---

## 2. Dependency Assessment

### 2.1 ADR-0057 (`subtasks_async`) Status

| ADR Status | Implementation Status | Analysis |
|------------|----------------------|----------|
| "Proposed" (in ADR) | **Implemented** (in code) | ADR status is stale; code is complete |

**Evidence**:
- `TasksClient.subtasks_async()` exists at `tasks.py:540-585`
- Returns `PageIterator[Task]` as specified
- Supports `opt_fields` and `limit` parameters
- Uses standard pagination pattern

**Conclusion**: No blocker--`subtasks_async()` is ready for use.

### 2.2 Missing Implementation: `_fetch_holders_async()`

All BusinessEntity subclasses have **stubbed** `_fetch_holders_async()` methods:

```python
# Business._fetch_holders_async() (business.py:520-542)
async def _fetch_holders_async(self, client: AsanaClient) -> None:
    # Phase 2: Implement when TasksClient.get_subtasks_async() is available
    _ = client  # Suppress unused parameter warning

# Unit._fetch_holders_async() (unit.py:320-327)
async def _fetch_holders_async(self, client: AsanaClient) -> None:
    # Phase 2: Implement when TasksClient.get_subtasks_async() is available
    _ = client  # Suppress unused parameter warning
```

**Required implementation** for each entity with `HOLDER_KEY_MAP`:
1. Fetch subtasks via `client.tasks.subtasks_async(self.gid).collect()`
2. Call `_populate_holders(subtasks)`
3. For each typed holder, fetch holder's subtasks and call `_populate_children()`
4. Recursively process nested holders (Unit has OfferHolder, ProcessHolder)

### 2.3 Missing Implementation: Upward Hydration

**Problem**: If a user fetches an Offer directly by GID, the `_business` and `_unit` references are None because population never occurred.

**Required for upward traversal**:
1. Given an entity at any level, walk `Task.parent` up the tree
2. At each level, identify the parent type (Business? Unit? Holder?)
3. Fetch and type-convert the parent
4. Set bidirectional references
5. Continue until reaching Business or root

**Challenge**: The `parent` field is a `NameGid` with only the GID. To determine parent type:
- Option A: Fetch parent task and inspect name/structure
- Option B: Maintain type information in a custom field
- Option C: Infer from naming conventions (holder names: "Contacts", "Units", "Offers", etc.)

### 2.4 Client Reference Storage (per ADR-0063)

`Task._client` stores the `AsanaClient` reference for `save_async()` and `refresh_async()`. This pattern exists and is used by all entities returned from `TasksClient.get_async()`.

**For hydration**: `_fetch_holders_async(client)` must receive the client parameter. When called from `BusinessEntity.from_gid_async(client, gid)`, the client is available.

### 2.5 SaveSession Recursive Tracking (per ADR-0053)

`SaveSession.track(entity, recursive=True)` recursively tracks all descendants:

```python
# session.py:283-312
def _track_recursive(self, entity: AsanaResource) -> None:
    holder_key_map = getattr(entity, "HOLDER_KEY_MAP", None)
    if holder_key_map:
        for holder_name in holder_key_map:
            holder = getattr(entity, f"_{holder_name}", None)
            if holder is not None:
                self._tracker.track(holder)
                self._track_recursive(holder)

    for child_attr in ("_contacts", "_units", "_offers", "_processes"):
        children = getattr(entity, child_attr, None)
        if children and isinstance(children, list):
            for child in children:
                self._tracker.track(child)
                self._track_recursive(child)
```

**Implication**: Once hydrated, `session.track(business, recursive=True)` correctly tracks the entire tree.

---

## 3. Use Case Prioritization

### 3.1 Hydration Scenarios

| Priority | Scenario | Entry Point | Navigation Required | Complexity |
|----------|----------|-------------|---------------------|------------|
| **P0** | Load full business hierarchy | Business GID | Down only (5 levels) | Medium |
| **P1** | Webhook receives Contact GID | Contact | Up 2 levels, then full downward | High |
| **P1** | Search returns Offer GID | Offer | Up 4 levels, then full downward | High |
| **P2** | Deep link to Process | Process | Up 4 levels, then full downward | High |
| **P2** | Load Unit with children only | Unit GID | Down only (2 levels) | Low |
| **P3** | Batch process multiple Contacts | List[Contact GID] | Up 2 levels each, dedupe | Very High |

### 3.2 Navigation Patterns by Entry Point

#### P0: Business Entry (Downward Only)

```
Start: Business GID
  -> get_async(gid) -> Business
  -> subtasks_async() -> [holders]
  -> For ContactHolder: subtasks_async() -> [contacts]
  -> For UnitHolder: subtasks_async() -> [units]
     -> For each Unit: subtasks_async() -> [offer_holder, process_holder]
        -> For OfferHolder: subtasks_async() -> [offers]
        -> For ProcessHolder: subtasks_async() -> [processes]
  -> For LocationHolder: subtasks_async() -> [locations, hours]
```

**API Calls**: 1 + 7 (holders) + N (contacts) + M (units) * 3 + ...
**Worst case**: ~20-50 API calls for a typical business

#### P1: Contact/Offer Entry (Upward + Full Downward)

```
Start: Contact GID
  -> get_async(gid) -> Contact (has parent NameGid)
  -> get_async(parent.gid) -> Task (is it ContactHolder?)
     -> Identify as ContactHolder by name/structure
  -> get_async(parent.gid) -> Task (is it Business?)
     -> Identify as Business by name/HOLDER_KEY_MAP structure
  -> Now have Business; proceed with P0 downward hydration
```

**Challenge**: Type identification from Task requires heuristics:
- Business: Has subtasks with holder names ("Contacts", "Units", etc.)
- Holder: Has name matching known holder patterns
- Entity: Everything else

### 3.3 Priority Justification

**P0 (Business entry)** is the most common case and simplest to implement. All existing code paths assume downward-only traversal.

**P1 (Contact/Offer entry)** covers webhook and search scenarios--high-value use cases that currently require callers to know the Business GID.

**P2/P3** are lower priority because they can be handled by composing P0/P1 patterns.

---

## 4. Architectural Questions for Architect

### 4.1 Upward Traversal Type Detection

**Question**: How should we determine the type of a parent task when traversing upward?

**Options**:
| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Name-based heuristics | No API changes, works with existing data | Brittle if naming changes |
| B | Custom field storing type | Reliable type detection | Requires data migration |
| C | Structure inspection (fetch subtasks, check for holder patterns) | Self-describing | Extra API calls |
| D | Maintain type registry by GID | O(1) lookup | Requires cache management |

**Recommendation for consideration**: Option A with fallback to Option C. Name conventions are already established (e.g., "Contacts", "Units", "Offers") and unlikely to change.

### 4.2 Hydration Depth Control

**Question**: Should hydration be configurable by depth or by type?

**Options**:
| Option | Parameter | Behavior |
|--------|-----------|----------|
| A | `max_depth: int` | Stop at N levels from entry point |
| B | `include_types: set[Type]` | Only hydrate specified entity types |
| C | `full: bool` | All-or-nothing |
| D | Combination | `HydrationConfig(max_depth=3, include_types={Offer})` |

**Recommendation for consideration**: Option D provides maximum flexibility while defaulting to full hydration (current implicit behavior).

### 4.3 Concurrent Fetching Strategy

**Question**: Should holder fetches be concurrent or sequential?

**Options**:
| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Sequential (current pattern) | Simple, predictable | Slow for deep hierarchies |
| B | Concurrent at each level | Faster (batch API calls) | Complex error handling |
| C | Full concurrent (all levels at once) | Fastest | Rate limiting risk, complex |

**Recommendation for consideration**: Option B--concurrent within each level, sequential across levels. This balances speed with maintainability.

### 4.4 Error Handling for Partial Hydration

**Question**: What happens if one holder fetch fails during hydration?

**Options**:
| Option | Behavior |
|--------|----------|
| A | Fail entire hydration | Consistent but brittle |
| B | Mark failed branch as None, continue | Partial result, may confuse callers |
| C | Return HydrationResult with succeeded/failed lists | Explicit, mirrors SaveResult |

**Recommendation for consideration**: Option C aligns with existing `SaveResult` pattern.

### 4.5 Upward-Then-Downward vs. Downward-Only

**Question**: Should `from_gid_async()` support arbitrary entry points (upward + downward) or only root-level entry?

**Current behavior**: `BusinessEntity.from_gid_async(client, gid)` assumes `gid` is a Business.

**Options**:
| Option | Signature | Behavior |
|--------|-----------|----------|
| A | Keep current | Business entry only |
| B | `Contact.from_gid_async(...)` | Each type knows how to hydrate to root |
| C | `BusinessHierarchy.from_any_gid(...)` | Single entry point, detect type |

**Recommendation for consideration**: Option B provides type safety; Option C provides convenience. Both could coexist.

---

## 5. PRD Scope Recommendations

### 5.1 In-Scope (Phase 2 Completion)

| Requirement | Priority | Rationale |
|-------------|----------|-----------|
| Implement `Business._fetch_holders_async()` | P0 | Core downward hydration |
| Implement `Unit._fetch_holders_async()` | P0 | Nested holder hydration |
| Implement upward traversal for Contact | P1 | Webhook use case |
| Implement upward traversal for Offer | P1 | Search use case |
| Type detection heuristics | P1 | Required for upward traversal |
| Concurrent holder fetching (within level) | P2 | Performance optimization |
| `HydrationConfig` for depth/type control | P2 | User control |

### 5.2 Out-of-Scope (Future Work)

| Item | Rationale |
|------|-----------|
| Upward traversal for Process | Lower priority entry point |
| Batch hydration (multiple GIDs) | Can be implemented on top of single-GID |
| Incremental/delta hydration | Requires change tracking infrastructure |
| Hydration caching | Separate concern; may conflict with freshness |
| Process subclass specialization | Phase 3 item per TDD-BIZMODEL |

### 5.3 Suggested Requirement Categories

1. **FR-HYDRATE-DOWN**: Downward hydration from Business entry point
2. **FR-HYDRATE-UP**: Upward traversal to find Business ancestor
3. **FR-HYDRATE-FULL**: Combined upward + downward for arbitrary entry
4. **FR-HYDRATE-CONFIG**: Hydration configuration (depth, types)
5. **FR-HYDRATE-ERROR**: Partial failure handling
6. **NFR-HYDRATE-PERF**: Concurrent fetching, API call optimization

---

## 6. Open Questions Summary

| # | Question | Owner | Due | Blocking? |
|---|----------|-------|-----|-----------|
| Q1 | Type detection strategy for upward traversal | Architect | Session 3 | Yes (for P1) |
| Q2 | Hydration depth control design | Architect | Session 3 | No |
| Q3 | Concurrent fetching strategy | Architect | Session 3 | No |
| Q4 | Partial failure semantics | Architect | Session 3 | No |
| Q5 | Entry point API design (per-type vs unified) | Architect | Session 3 | No |

---

## 7. Appendix: File Locations

| File | Purpose |
|------|---------|
| `/src/autom8_asana/models/business/base.py` | `BusinessEntity`, `HolderMixin` base classes |
| `/src/autom8_asana/models/business/business.py` | `Business`, stub holders, `HOLDER_KEY_MAP` |
| `/src/autom8_asana/models/business/contact.py` | `Contact`, `ContactHolder` |
| `/src/autom8_asana/models/business/unit.py` | `Unit`, `UnitHolder` |
| `/src/autom8_asana/models/business/offer.py` | `Offer`, `OfferHolder` |
| `/src/autom8_asana/models/business/process.py` | `Process`, `ProcessHolder` |
| `/src/autom8_asana/models/business/location.py` | `Location`, `LocationHolder` |
| `/src/autom8_asana/models/business/hours.py` | `Hours` |
| `/src/autom8_asana/models/task.py` | `Task` model with `parent` field |
| `/src/autom8_asana/models/common.py` | `NameGid`, `PageIterator` |
| `/src/autom8_asana/clients/tasks.py` | `TasksClient` with `get_async`, `subtasks_async` |
| `/src/autom8_asana/persistence/session.py` | `SaveSession` with `track(recursive=True)` |
| `/docs/decisions/ADR-0057-subtasks-async-method.md` | `subtasks_async` specification |
| `/docs/decisions/ADR-0050-holder-lazy-loading-strategy.md` | Holder lazy loading design |
| `/docs/decisions/ADR-0052-bidirectional-reference-caching.md` | Reference caching design |
| `/docs/decisions/ADR-0053-composite-savesession-support.md` | Recursive tracking design |

---

## 8. Next Steps

1. **Session 2 (PRD)**: Requirements Analyst creates PRD-HYDRATION.md based on this discovery
2. **Session 3 (TDD)**: Architect resolves open questions and creates TDD-HYDRATION.md
3. **Session 4+ (Implementation)**: Principal Engineer implements per TDD specification

---

*Discovery complete. Ready for PRD creation.*
