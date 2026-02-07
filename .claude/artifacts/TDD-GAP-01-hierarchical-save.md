---
artifact_id: TDD-GAP-01-hierarchical-save
title: "Technical Design: Hierarchical Save -- Holder Auto-Creation"
created_at: "2026-02-07T17:00:00Z"
author: architect
status: draft
prd_ref: PRD-GAP-01-hierarchical-save
adr_ref: ADR-GAP-01-pipeline-vs-holder-manager
complexity: MODULE
---

# TDD: Hierarchical Save -- Holder Auto-Creation

## 1. Architecture Decision Summary

**Decision**: New SavePipeline phase (ENSURE_HOLDERS) inserted before the existing VALIDATE phase.

**Rationale**: See ADR-GAP-01-pipeline-vs-holder-manager for the full tradeoff analysis. In short: a pipeline phase has direct access to the tracker and graph, avoids introducing a new service boundary, runs at the correct lifecycle moment (after tracking, before graph construction), and follows the established pattern of the existing five-phase pipeline.

The phase is named `ENSURE_HOLDERS` because it is idempotent: it detects existing holders and creates only what is missing, on every commit.

**Updated Pipeline Phases** (six-phase):

```
1. ENSURE_HOLDERS  -- detect + construct missing holders for tracked entities
2. VALIDATE        -- cycle detection + unsupported field validation
3. PREPARE         -- build operations, assign temp GIDs
4. EXECUTE         -- execute CRUD via BatchExecutor
5. ACTIONS         -- execute action operations (setParent, add_tag, etc.)
6. CONFIRM         -- resolve GIDs, update entities, clear dirty state
```

---

## 2. Component Diagram

```
+------------------------------------------------------------------+
|                         SaveSession                               |
|  +-----------+  +---------------+  +---------------------------+  |
|  | tracker   |  | graph         |  | pipeline                  |  |
|  | (Change   |  | (Dependency   |  | (SavePipeline)            |  |
|  |  Tracker) |  |  Graph)       |  |  +---------------------+  |  |
|  +-----------+  +---------------+  |  | ENSURE_HOLDERS phase |  |  |
|                                    |  |  +------------------+|  |  |
|  auto_create_holders: bool = True  |  |  | HolderEnsurer   ||  |  |
|                                    |  |  | - detect()       ||  |  |
|                                    |  |  | - construct()    ||  |  |
|                                    |  |  | - track()        ||  |  |
|                                    |  |  +------------------+|  |  |
|                                    |  | VALIDATE phase       |  |  |
|                                    |  | PREPARE phase        |  |  |
|                                    |  | EXECUTE phase        |  |  |
|                                    |  | ACTIONS phase        |  |  |
|                                    |  | CONFIRM phase        |  |  |
|                                    |  +---------------------+  |  |
|                                    +---------------------------+  |
|                                                                    |
|  +---------------------------+  +-------------------------------+ |
|  | HolderConcurrencyManager  |  | holder_construction module    | |
|  | - _locks: dict[str, Lock] |  | - construct_holder()          | |
|  | - acquire(parent_gid,     |  | - detect_existing_holders()   | |
|  |     holder_type)          |  | - HOLDER_TYPE_REGISTRY        | |
|  | - release(...)            |  +-------------------------------+ |
|  +---------------------------+                                    |
+------------------------------------------------------------------+
```

### New Components

| Component | Module | Responsibility |
|-----------|--------|---------------|
| `HolderEnsurer` | `persistence/holder_ensurer.py` | Orchestrates detection + construction + tracking for a single parent entity. Stateless collaborator used by SavePipeline. |
| `HolderConcurrencyManager` | `persistence/holder_concurrency.py` | Manages `asyncio.Lock` instances keyed by `(parent_gid, holder_type)`. Singleton per SaveSession. |
| `construct_holder()` | `models/business/holder_construction.py` | Pure function that builds a typed holder entity from HOLDER_KEY_MAP metadata. No I/O. |
| `detect_existing_holders()` | `models/business/holder_construction.py` | Async function that calls `subtasks_async` and matches via the same identification logic as `_identify_holder`. |

### Existing Components Modified

| Component | Change |
|-----------|--------|
| `SaveSession.__init__` | New `auto_create_holders: bool = True` parameter. Passes to pipeline. |
| `SaveSession.commit_async` | Calls `pipeline.ensure_holders()` before CRUD if `auto_create_holders` is True. |
| `SavePipeline.__init__` | Accepts `AsanaClient` reference (for subtasks API call in detection). |
| `SavePipeline.execute` | Calls `_ensure_holders()` as Phase 0 before existing Phase 1. |
| `SavePipeline.execute_with_actions` | Same integration point. |

---

## 3. Interface Contracts

### 3.1 SaveSession Constructor (Modified)

```python
class SaveSession:
    def __init__(
        self,
        client: AsanaClient,
        batch_size: int = 10,
        max_concurrent: int = 15,
        auto_heal: bool = False,
        automation_enabled: bool | None = None,
        auto_create_holders: bool = True,       # NEW
    ) -> None:
```

`auto_create_holders` defaults to `True` (opt-out pattern per PRD OQ-1). Independent of `recursive`. When `False`, the ENSURE_HOLDERS phase is skipped entirely.

### 3.2 HolderEnsurer

```python
class HolderEnsurer:
    """Detects missing holders and constructs them for tracked entities.

    Stateless -- instantiated per commit cycle with the needed collaborators.
    """

    def __init__(
        self,
        client: AsanaClient,
        tracker: ChangeTracker,
        concurrency: HolderConcurrencyManager,
        log: Any | None = None,
    ) -> None: ...

    async def ensure_holders_for_entities(
        self,
        dirty_entities: list[AsanaResource],
    ) -> list[AsanaResource]:
        """Detect and construct missing holders for all dirty entities.

        Algorithm:
        1. Collect unique parent entities that have HOLDER_KEY_MAP.
        2. For each parent, determine which holder types have tracked children.
        3. For each needed holder type:
           a. Acquire asyncio.Lock for (parent_gid, holder_type).
           b. Check if holder already tracked in session.
           c. If not, call detect_existing_holders() to check Asana API.
           d. If not found in Asana, call construct_holder() to build.
           e. Track the holder (new or existing) via ChangeTracker.
           f. Wire parent reference on children.
           g. Release lock.
        4. Return all newly constructed holder entities (for addition to
           the dirty list passed to the rest of the pipeline).

        Args:
            dirty_entities: Entities with pending changes from the tracker.

        Returns:
            Combined list: original dirty_entities + newly created holders.
        """
```

### 3.3 construct_holder()

```python
def construct_holder(
    holder_key: str,
    holder_key_map: dict[str, tuple[str, str]],
    parent_entity: AsanaResource,
) -> AsanaResource:
    """Construct a typed holder entity for a given holder_key.

    Uses HOLDER_KEY_MAP metadata to determine:
    - Holder class (ContactHolder, UnitHolder, etc.)
    - Name (from the tuple: e.g., "Contacts", "Business Units")
    - Parent reference (set to parent_entity via NameGid)

    The holder is created with gid=None, causing ChangeTracker to assign
    EntityState.NEW and the pipeline to generate temp_{id(entity)} at
    graph build time.

    Args:
        holder_key: Key from HOLDER_KEY_MAP (e.g., "contact_holder").
        holder_key_map: The HOLDER_KEY_MAP dict from the parent entity.
        parent_entity: The Business or Unit that owns this holder.

    Returns:
        A typed holder entity (e.g., ContactHolder instance) with:
        - gid = None (no GID yet -- temp assigned by pipeline)
        - name = conventional name from HOLDER_KEY_MAP
        - parent = NameGid(gid=parent_entity.gid) if real GID, else
                   reference to parent entity object (for temp GID resolution)
        - resource_type = "task"
    """
```

**Implementation detail**: The function uses a registry mapping `holder_key -> holder_class`:

```python
HOLDER_CLASS_MAP: dict[str, type] = {
    # Business-level holders
    "contact_holder": ContactHolder,
    "unit_holder": UnitHolder,
    "location_holder": LocationHolder,
    "dna_holder": DNAHolder,
    "reconciliation_holder": ReconciliationHolder,
    "asset_edit_holder": AssetEditHolder,
    "videography_holder": VideographyHolder,
    # Unit-level holders
    "offer_holder": OfferHolder,
    "process_holder": ProcessHolder,
}
```

### 3.4 detect_existing_holders()

```python
async def detect_existing_holders(
    client: AsanaClient,
    parent_gid: str,
    holder_key_map: dict[str, tuple[str, str]],
) -> dict[str, AsanaResource]:
    """Detect which holders already exist as subtasks of parent.

    Calls the subtasks API once per parent, then uses _identify_holder()
    (same logic as the read path) to match each subtask.

    Args:
        client: AsanaClient for subtasks_async call.
        parent_gid: GID of the parent entity (Business or Unit).
        holder_key_map: The HOLDER_KEY_MAP to match against.

    Returns:
        Dict of holder_key -> typed holder entity for existing holders.
        Missing holder types are absent from the dict.
    """
```

**Reuse of read-path detection**: This function calls `client.tasks.subtasks_async(parent_gid, include_detection_fields=True).collect()` and then uses the same `identify_holder_type()` function from `models.business.detection.facade` that `Business._identify_holder()` and `Unit._identify_holder()` use. This guarantees detection consistency between read and write paths (FR-001).

### 3.5 HolderConcurrencyManager

```python
class HolderConcurrencyManager:
    """Per-session asyncio.Lock manager keyed by (parent_gid, holder_type).

    Created by SaveSession.__init__ and passed to HolderEnsurer.
    Locks are created lazily on first acquisition and held for the
    duration of the detect-or-create critical section.

    Lifecycle:
    - Created: SaveSession.__init__
    - Used: During ENSURE_HOLDERS phase of each commit
    - Destroyed: When SaveSession is garbage collected (or context exited)

    Thread safety: asyncio.Lock is coroutine-safe but not thread-safe.
    This matches the SaveSession concurrency model (asyncio coroutines).
    """

    def __init__(self) -> None:
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}

    def get_lock(self, parent_gid: str, holder_type: str) -> asyncio.Lock:
        """Get or create a lock for (parent_gid, holder_type)."""
        key = (parent_gid, holder_type)
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]
```

The lock key is `(parent_gid, holder_type)` -- not just `holder_type` -- because two different Businesses can safely create their ContactHolders concurrently. The lock only prevents two coroutines from creating the same holder for the same parent.

---

## 4. Dependency Chain Analysis: 5-Level Proof

### 4.1 The Chain

```
L0: Business (gid=temp_{id(business)})
L1: UnitHolder (gid=temp_{id(unit_holder)}, parent=Business)
L2: Unit (gid=temp_{id(unit)}, parent=UnitHolder)
L3: OfferHolder (gid=temp_{id(offer_holder)}, parent=Unit)
L4: Offer (gid=temp_{id(offer)}, parent=OfferHolder)
```

### 4.2 DependencyGraph.build() Analysis

The current `build()` method (in `graph.py` lines 40-70):

1. Indexes all entities by GID (including `temp_{id(entity)}` for new entities).
2. For each entity, checks `entity.parent`.
3. Resolves `parent_ref` via `_resolve_parent_gid()`, which handles:
   - String GIDs (real)
   - `NameGid` objects with `.gid`
   - `AsanaResource` objects found in the entities list (via identity check `entity is parent_ref`)

**Critical requirement for 5-level chains**: The `parent` field on each entity must reference either:
- A real GID string (for existing entities), or
- The parent entity object itself (so `_resolve_parent_gid` can find it via `entity is parent_ref` and return `temp_{id(entity)}`)

When the holder is constructed, we set `holder.parent = NameGid(gid=parent_entity.gid)` for parents with real GIDs. For parents with temp GIDs (all-new tree), we set `holder.parent = NameGid(gid=f"temp_{id(parent_entity)}")`.

**However**, there is a subtlety in `_resolve_parent_gid()` (lines 192-224):

```python
if hasattr(parent_ref, "gid"):
    gid: str | None = parent_ref.gid
    if gid and not gid.startswith("temp_"):
        return gid
    # If no GID or temp GID, check if it's a tracked entity
    for entity in entities:
        if entity is parent_ref:
            return self._get_gid(entity)
```

When `parent_ref` is a `NameGid` (not the entity itself), the `entity is parent_ref` check will fail because `NameGid` is a different object than the `AsanaResource`. If the parent has a temp GID embedded in the NameGid, the code falls through to return `None`, breaking the chain.

**Solution**: For parents that have no real GID yet (temp GID scenario), set `entity.parent` to the **entity object itself** rather than a `NameGid` wrapper. This allows the `entity is parent_ref` identity check to succeed. The `_resolve_parent_gid` method already handles this path correctly.

With this approach:
- `Business.parent = None` (L0, no parent -- root)
- `UnitHolder.parent = business_entity` (L1, object reference)
- `Unit.parent = unit_holder_entity` (L2, object reference)
- `OfferHolder.parent = unit_entity` (L3, object reference)
- `Offer.parent = offer_holder_entity` (L4, object reference)

### 4.3 Kahn's Algorithm Level Proof

`get_levels()` (lines 111-154) processes nodes layer by layer:

1. **Initial state**: All entities in `remaining`, in_degree computed from edges.
2. **L0 iteration**: Business has in_degree 0 (no parent in graph) -> placed in level 0. Remove Business from remaining, decrement dependents' in_degree.
3. **L1 iteration**: UnitHolder now has in_degree 0 -> placed in level 1. Remove, decrement.
4. **L2 iteration**: Unit now has in_degree 0 -> placed in level 2. Remove, decrement.
5. **L3 iteration**: OfferHolder now has in_degree 0 -> placed in level 3. Remove, decrement.
6. **L4 iteration**: Offer now has in_degree 0 -> placed in level 4. Remove.
7. `remaining` is empty, no cycle.

Result: `[[Business], [UnitHolder], [Unit], [OfferHolder], [Offer]]` -- 5 levels.

### 4.4 GID Resolution Through 5 Levels

In `SavePipeline.execute()` (lines 159-263):

- `gid_map: dict[str, str] = {}` accumulates temp -> real mappings.
- After L0 executes: `gid_map["temp_{id(business)}"] = "real_biz_gid"`. Business.gid updated in place.
- L1 processing: `_prepare_operations()` resolves `UnitHolder.parent` payload. If parent field contains `"temp_{id(business)}"`, it's replaced with `"real_biz_gid"` from gid_map. UnitHolder created, gid_map gains `"temp_{id(unit_holder)}" -> "real_uh_gid"`.
- L2: Unit parent resolved to `"real_uh_gid"`. Created. Mapped.
- L3: OfferHolder parent resolved to `"real_unit_gid"`. Created. Mapped.
- L4: Offer parent resolved to `"real_oh_gid"`. Created. Mapped.

**Key detail in `_prepare_operations`** (lines 400-435):

```python
if "parent" in payload:
    parent_ref = payload["parent"]
    if isinstance(parent_ref, str) and parent_ref.startswith("temp_"):
        if parent_ref in gid_map:
            payload["parent"] = gid_map[parent_ref]
```

This only resolves string temp GIDs in the payload. However, `_build_payload()` calls `_convert_references_to_gids()` which converts `NameGid` objects to their `.gid` string. If the parent is an entity object reference, `model_dump()` may not serialize it correctly.

**Required modification**: The `_build_payload` method for CREATE operations calls `entity.model_dump(exclude_none=True, exclude={"gid", "resource_type"})`. Pydantic will serialize the `parent` field. If `parent` is a `NameGid`, it serializes as `{"gid": "...", "name": "..."}` and then `_convert_references_to_gids` converts it to the gid string. If `parent` is an `AsanaResource`, the conversion also works via `hasattr(value, "gid")`.

**However**, when parent is an entity object with no real GID, `value.gid` will be `None` or `""`, and the conversion will produce `None`. The temp GID for the parent is `temp_{id(parent_entity)}`, but that's not stored on the entity's `.gid` field.

**Solution**: Before the graph phase, update the GID of newly constructed holders to `temp_{id(entity)}` explicitly. We do this by calling `object.__setattr__(holder, "gid", f"temp_{id(holder)}")` immediately after construction. This is the same pattern used throughout the pipeline (see `_get_gid()` in both `graph.py` and `pipeline.py`). Then set `child.parent = NameGid(gid=f"temp_{id(holder)}")` so the payload serialization works correctly.

**Wait -- but this conflicts with the graph resolution**. Let me trace more carefully:

1. `DependencyGraph._get_gid(entity)` checks `entity.gid`. If it starts with `"temp_"`, it returns `f"temp_{id(entity)}"`. If entity.gid is `None` or empty, same result.
2. `_resolve_parent_gid(parent_ref, entities)` checks `parent_ref.gid`. If it starts with `"temp_"`, it searches entities by identity: `entity is parent_ref`.

So the safest approach:
- Set `holder.gid = ""` (empty string, triggering `_get_gid` to produce `temp_{id(holder)}`).
- Set the child's `parent` to the holder entity object reference (not a NameGid).
- The graph's `_resolve_parent_gid` finds the holder via `entity is parent_ref` and returns `temp_{id(holder)}`.
- The graph builds the edge correctly.
- In `_build_payload`, the parent entity object has `gid=""` which becomes `""` after `_convert_references_to_gids`. But then `_prepare_operations` checks `payload["parent"]` for `startswith("temp_")` -- and `""` does not match.

**This is the actual gap.** The pipeline's GID resolution assumes that:
1. Entity GIDs are either real or temp_*.
2. Parent references in payloads are either real GIDs or temp_* strings.

For a truly new entity (no GID), the pipeline generates `temp_{id(entity)}` as the canonical temp GID, but this is used for graph indexing, not stored on the entity. The payload serialization doesn't know about `temp_{id(entity)}`.

**Required fix** (two options):

**Option A (recommended)**: Assign explicit temp GIDs to newly constructed holders at construction time. Set `holder.gid = f"temp_{id(holder)}"` via `object.__setattr__`. Then set `child.parent = NameGid(gid=f"temp_{id(holder)}")`. This makes the payload contain `"parent": "temp_{id(holder)}"`, which `_prepare_operations` correctly resolves.

**Option B**: Modify `_prepare_operations` to also handle entity object references in payloads. More invasive and less explicit.

**Option A is chosen.** This is consistent with how the existing system works -- it just makes explicit what was previously implicit for entities that already had temp_ prefixed GIDs.

### 4.5 Fan-Out Support

The 5-level chain above is linear. The actual tree has fan-outs:

```
Business (L0)
  +-- ContactHolder (L1)
  |     +-- Contact (L2)
  +-- UnitHolder (L1)
  |     +-- Unit (L2)
  |           +-- OfferHolder (L3)
  |           |     +-- Offer (L4)
  |           +-- ProcessHolder (L3)
  |                 +-- Process (L4)
  +-- LocationHolder (L1)
        +-- Location (L2)
```

Kahn's algorithm handles fan-outs naturally: all holders at L1 have the same in_degree (dependent only on Business at L0). They are all placed in the same level and executed in the same batch. The BatchExecutor handles multiple entities per level (that's its purpose).

**Verified**: The 5-level chain with fan-outs produces levels `[[Business], [ContactHolder, UnitHolder, LocationHolder, ...], [Contact, Unit, Location, ...], [OfferHolder, ProcessHolder], [Offer, Process]]`.

---

## 5. Holder Entity Construction Pattern

### 5.1 Construction Function

```python
def construct_holder(
    holder_key: str,
    parent_entity: AsanaResource,
    holder_class: type[AsanaResource],
    conventional_name: str,
) -> AsanaResource:
    """Build a typed holder entity programmatically."""
    holder = holder_class(
        gid="",                    # Will be set to temp_{id()} below
        name=conventional_name,    # e.g., "Contacts", "Business Units"
        resource_type="task",
    )
    # Assign temp GID for pipeline resolution
    object.__setattr__(holder, "gid", f"temp_{id(holder)}")

    # Set parent reference for dependency graph
    if parent_entity.gid and not parent_entity.gid.startswith("temp_"):
        # Parent has real GID
        holder.parent = NameGid(gid=parent_entity.gid)
    else:
        # Parent also new -- use entity object reference
        holder.parent = NameGid(gid=f"temp_{id(parent_entity)}")

    # Wire holder -> parent internal reference
    holder._business = parent_entity if isinstance(parent_entity, Business) else getattr(parent_entity, "_business", None)

    return holder
```

### 5.2 Name Derivation from HOLDER_KEY_MAP

`HOLDER_KEY_MAP` on Business provides `(task_name, emoji_indicator)` per holder:

```python
{
    "contact_holder": ("Contacts", "busts_in_silhouette"),
    "unit_holder": ("Business Units", "package"),
    "location_holder": ("Location", "round_pushpin"),
    "dna_holder": ("DNA", "dna"),
    "reconciliation_holder": ("Reconciliations", "abacus"),
    "asset_edit_holder": ("Asset Edits", "art"),
    "videography_holder": ("Videography", "video_camera"),
}
```

For Unit:
```python
{
    "offer_holder": ("Offers", "gift"),
    "process_holder": ("Processes", "gear"),
}
```

The `conventional_name` is the first element of the tuple. We do NOT include the emoji in the task name -- emojis are stored as Asana custom field metadata, not in the name string. The detection system identifies holders by name match first, emoji fallback second. Creating with the correct name ensures detection works on re-read.

### 5.3 Project Assignment

For holders with `PRIMARY_PROJECT_GID != None`, we add the project to the holder's `projects` list:

```python
if holder_class.PRIMARY_PROJECT_GID is not None:
    holder.projects = [NameGid(gid=holder_class.PRIMARY_PROJECT_GID)]
```

This satisfies FR-008 (holder project assignment) and ensures Tier 1 detection works for future reads.

Holders with `PRIMARY_PROJECT_GID = None` (LocationHolder, ProcessHolder) are created without project assignment. Detection falls back to Tier 2/3, which is acceptable per PRD.

---

## 6. SetParent Wiring

### 6.1 Mechanism

Newly created holders become subtasks of their parent via two mechanisms:

1. **CRUD CREATE with `parent` field**: The Asana Tasks API accepts a `parent` field on POST `/tasks`. When present, the created task is automatically a subtask of that parent. This is handled by the existing pipeline -- the holder entity has `parent` set, the payload includes it, and Asana creates the subtask relationship.

2. **Fallback SET_PARENT action**: If the CREATE does not include a `parent` field (or if the parent must be changed post-creation), we use the existing `session.set_parent()` method which queues an `ActionType.SET_PARENT` operation.

**For this design, mechanism (1) is sufficient.** The holder's `parent` field is set during construction (Section 5.1). The pipeline's EXECUTE phase creates the task with the parent field, and Asana handles the subtask wiring. No separate SET_PARENT action is needed for initial creation.

**When mechanism (2) is needed**: If a holder already exists in Asana but is not yet a subtask of the parent (unlikely but possible due to data corruption). This is a healing concern and explicitly out of scope for v1.

---

## 7. Integration with _track_recursive

### 7.1 No Changes to _track_recursive

`_track_recursive` (session.py lines 436-460) walks `HOLDER_KEY_MAP` and tracks holders that are already populated (`_contact_holder is not None`, etc.). It does NOT construct missing holders -- that is the gap this feature fills.

**Design choice**: `_track_recursive` remains unchanged. Holder construction happens in the ENSURE_HOLDERS pipeline phase, AFTER tracking and BEFORE graph construction. This separation is intentional:

1. `track(entity, recursive=True)` tracks whatever is populated.
2. `commit_async()` runs ENSURE_HOLDERS, which detects what's missing and constructs it.
3. The newly constructed holders are tracked via `self._tracker.track(holder)`.
4. The rest of the pipeline proceeds with the complete entity set.

This means callers can do:

```python
session.track(business, recursive=True)
# At this point, unpopulated holders are NOT tracked.
# But new children (contacts, units, etc.) ARE tracked.

result = await session.commit_async()
# ENSURE_HOLDERS phase detects that Contact children need a ContactHolder,
# constructs the ContactHolder, tracks it, and the pipeline handles the rest.
```

### 7.2 Determining Which Holders Are Needed

The ENSURE_HOLDERS phase determines which holders to create by:

1. For each dirty entity, check if it has a `parent` reference that points to a holder.
2. If the parent is a tracked holder -- done.
3. If the parent is NOT tracked, check the parent entity's HOLDER_KEY_MAP to determine which holder type this entity belongs under.

**Simpler approach**: Scan dirty entities for parent entities that have HOLDER_KEY_MAP. For each such parent, examine which holder types have children in the dirty list. For those holder types, ensure the holder exists.

Concretely:

```python
# Collect parents with HOLDER_KEY_MAP
parents_with_holders = {
    entity for entity in dirty_entities
    if hasattr(entity, "HOLDER_KEY_MAP")
}

# For each parent, check which children are in the dirty list
for parent in parents_with_holders:
    for holder_key, (name, emoji) in parent.HOLDER_KEY_MAP.items():
        private_attr = f"_{holder_key}"
        holder = getattr(parent, private_attr, None)

        if holder is not None and self._tracker.is_tracked(holder.gid or ""):
            # Holder already tracked, skip
            continue

        # Check if any children of this holder type are being saved
        children_attr = _get_children_attr(holder_key)
        children = getattr(parent, children_attr, None)
        if children:
            has_dirty_children = any(
                child in dirty_entities for child in children
            )
            if has_dirty_children:
                # Need this holder -- detect or create
                await self._ensure_holder(parent, holder_key)
```

---

## 8. Opt-Out Flag Flow

### 8.1 Propagation Path

```
SaveSession.__init__(auto_create_holders=True)
    -> self._auto_create_holders = auto_create_holders

SaveSession.commit_async()
    -> if self._auto_create_holders:
           new_holders = await self._holder_ensurer.ensure_holders_for_entities(dirty)
           dirty.extend(new_holders)
       # Otherwise, skip ENSURE_HOLDERS entirely
```

### 8.2 Behavior When Disabled

When `auto_create_holders=False`:
- ENSURE_HOLDERS phase is skipped.
- `_track_recursive` still only tracks populated holders (existing behavior).
- Children with missing holders will be tracked but will fail at EXECUTE time if they reference a parent that doesn't exist in Asana.
- This matches today's behavior exactly (per PRD FR-006).

### 8.3 Property for Inspection

```python
@property
def auto_create_holders(self) -> bool:
    """Whether holder auto-creation is enabled for this session."""
    return self._auto_create_holders
```

---

## 9. Error Handling

### 9.1 Detection Failure

If `detect_existing_holders()` fails (API error fetching subtasks):
- Retry with the existing transport retry/backoff (the AsanaClient already handles this).
- If retry exhausted, log warning and proceed without detection -- create the holder. Worst case: a duplicate holder is created (non-catastrophic, detectable in future read).

### 9.2 Construction Failure

Construction is a pure function (no I/O). It cannot fail unless there's a bug in HOLDER_CLASS_MAP or the model validation rejects the input. This is a programming error, not a runtime error. Let it propagate.

### 9.3 Creation Failure (Partial Success)

If the EXECUTE phase fails to create a specific holder:
- The holder's children become cascading failures (existing pipeline behavior via `_filter_executable`).
- The successfully created holders and their children proceed normally.
- The SaveResult reports the holder creation failure and all cascading child failures.
- This satisfies PRD NFR-002 (partial failure does not corrupt).

### 9.4 Concurrent Duplicate (TOCTOU)

Between detection (no holder found) and creation (creating holder), another coroutine may create the same holder. The asyncio.Lock per `(parent_gid, holder_type)` prevents this for in-process concurrency.

For cross-process concurrency (deferred to v2): Asana allows duplicate-named subtasks. The worst case is two holders with the same name. The read-path detection will find one (the first returned by the subtasks API). This is acceptable for v1 and can be cleaned up by the healing system.

---

## 10. Sprint Decomposition

### Sprint 1: Foundation (SC-001, SC-002, SC-003, SC-005)

**Scope**: Business-level holder auto-creation. Single-level chains only (Business -> Holder -> Child).

**Tasks**:

| ID | Task | Estimate |
|----|------|----------|
| S1-001 | Create `holder_construction.py` with `construct_holder()`, `detect_existing_holders()`, `HOLDER_CLASS_MAP` | S |
| S1-002 | Create `holder_ensurer.py` with `HolderEnsurer` class | M |
| S1-003 | Create `holder_concurrency.py` with `HolderConcurrencyManager` | S |
| S1-004 | Modify `SaveSession.__init__` to accept `auto_create_holders` flag | S |
| S1-005 | Modify `SavePipeline.execute` and `execute_with_actions` to call ENSURE_HOLDERS phase | M |
| S1-006 | Unit tests for `construct_holder()` (all 7 Business holder types) | M |
| S1-007 | Unit tests for `detect_existing_holders()` (mock subtasks API) | M |
| S1-008 | Integration tests for SC-001, SC-002, SC-003, SC-005 | L |

**Success criteria satisfied**: SC-001 (missing holders created), SC-002 (existing reused), SC-003 (children parented), SC-005 (opt-out flag).

**Not in Sprint 1**: Multi-level chains (SC-006, SC-007), concurrency tests (SC-004).

### Sprint 2: Full Tree + Concurrency (SC-004, SC-006, SC-007)

**Scope**: Multi-level holder chains (Unit nested holders), 5-level temp GID chains, concurrency.

**Tasks**:

| ID | Task | Estimate |
|----|------|----------|
| S2-001 | Extend `HolderEnsurer` to handle Unit-level holders (OfferHolder, ProcessHolder) recursively | M |
| S2-002 | Ensure temp GID assignment works for all-new trees (Option A from Section 4.4) | M |
| S2-003 | Verify `_resolve_parent_gid` handles entity object references through 5 levels | M |
| S2-004 | Concurrency tests: two coroutines creating holders for same Business (SC-004) | M |
| S2-005 | Integration test for full tree from scratch (SC-007): Business + all holders + children | L |
| S2-006 | Integration test for Unit nested holders (SC-006) | M |
| S2-007 | Edge case tests from PRD table (wrong name, no project, rate limit, etc.) | M |
| S2-008 | Observability: structured logging for all holder lifecycle events | S |

**Success criteria satisfied**: SC-004 (concurrent no-duplicate), SC-006 (Unit nested holders), SC-007 (full tree from scratch).

---

## 11. Test Strategy

### 11.1 Unit Tests (Mock API, Fast)

| Test | Module | What It Verifies |
|------|--------|-----------------|
| `test_construct_holder_*` (7 types) | `holder_construction.py` | Each holder type constructed with correct class, name, parent |
| `test_construct_holder_with_project_gid` | `holder_construction.py` | Holders with PRIMARY_PROJECT_GID get projects list set |
| `test_construct_holder_without_project_gid` | `holder_construction.py` | Holders without PRIMARY_PROJECT_GID get no projects |
| `test_detect_existing_holders_all_present` | `holder_construction.py` | Returns all 7 when all exist |
| `test_detect_existing_holders_none_present` | `holder_construction.py` | Returns empty dict |
| `test_detect_existing_holders_partial` | `holder_construction.py` | Returns only existing ones |
| `test_concurrency_lock_keying` | `holder_concurrency.py` | Different parents get different locks |
| `test_opt_out_flag_skips_ensure` | `session.py` / `pipeline.py` | `auto_create_holders=False` -> no detection, no creation |
| `test_temp_gid_assignment` | `holder_construction.py` | Constructed holder gets `temp_{id()}` GID |
| `test_parent_reference_real_gid` | `holder_construction.py` | Parent with real GID -> NameGid with that GID |
| `test_parent_reference_temp_gid` | `holder_construction.py` | Parent with temp GID -> NameGid with temp_{id(parent)} |

### 11.2 Integration Tests (Mocked BatchClient, Full Pipeline)

| Test | What It Verifies |
|------|-----------------|
| `test_business_save_creates_missing_holders` (SC-001) | 0 holders -> save -> 7 holders created |
| `test_business_save_reuses_existing_holders` (SC-002) | 3/7 exist -> save -> 4 created, 3 reused |
| `test_children_parented_under_created_holder` (SC-003) | New Contact's parent GID == new ContactHolder's GID |
| `test_opt_out_preserves_current_behavior` (SC-005) | Opt-out -> no holders created |
| `test_unit_nested_holders_created` (SC-006) | Unit + Offer -> OfferHolder created under Unit |
| `test_full_tree_from_scratch` (SC-007) | All-new: Business + 7 holders + Units + OfferHolders + Offers |
| `test_concurrent_saves_no_duplicate` (SC-004) | Two coroutines -> 7 holders, not 14 |
| `test_5_level_dependency_graph` | Graph produces 5 levels for full chain |
| `test_gid_resolution_through_5_levels` | All temp GIDs resolved correctly in pipeline |
| `test_partial_holder_failure` | 5/7 succeed, 2 fail -> children of failed cascade, others saved |

### 11.3 What to Mock

- **BatchClient**: Always mocked in tests. Returns configurable success/failure per operation.
- **AsanaClient.tasks.subtasks_async**: Mocked in detection tests to return configured existing holders.
- **asyncio.Lock**: NOT mocked -- used directly in concurrency tests with multiple coroutines.

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Temp GID resolution breaks for entity object parents | Medium | High | Option A (explicit temp GID assignment) + comprehensive 5-level integration test |
| `model_dump()` serializes parent entity objects incorrectly | Medium | High | Set parent to NameGid with explicit temp_* string, not entity object |
| Detection logic diverges between read and write paths | Low | Medium | Reuse `identify_holder_type` from detection facade -- same function for both |
| Holder name convention changes break detection | Low | Medium | Single source of truth: HOLDER_KEY_MAP. Used by both construction and detection. |
| Lock contention on hot Business GIDs | Low | Low | Locks are per (parent_gid, holder_type). Contention only when 2+ coroutines save same Business concurrently. |
| Performance regression from subtasks API call | Low | Low | One API call per parent per commit. Opt-out flag available. Detection can be cached within session. |

---

## 13. Non-Functional Requirements Approach

### NFR-001: Performance

| Metric | Approach |
|--------|----------|
| Detection latency < 500ms | Single `subtasks_async` call per parent. Existing transport handles retries. |
| Creation latency < 1s | Standard POST to tasks API. Parent set in payload, no separate setParent needed. |
| Full hierarchy < 15s | Holders created in one batch level (L1 for Business holders). Parallelized by BatchExecutor. |
| No regression < 5% | Detection is one API call. For saves where all holders exist, detection returns immediately and no construction happens. |

### NFR-002: Reliability

- Partial failure: Pipeline's existing `_filter_executable` handles cascading failures.
- SaveResult: Holder failures reported as SaveError entries. Children cascade.
- Eventual consistency: Detection cache per session (within one commit, holders detected are remembered).

### NFR-003: Observability

Structured log events using existing `autom8y_log`:

```python
# Detection
log.info("holder_detection_start", parent_gid=..., parent_type=...)
log.info("holder_detected_existing", parent_gid=..., holder_type=..., holder_gid=...)
log.info("holder_detection_complete", parent_gid=..., existing=3, missing=4)

# Construction
log.info("holder_construction_start", parent_gid=..., holder_type=...)
log.info("holder_construction_complete", parent_gid=..., holder_type=..., temp_gid=...)

# Concurrency
log.debug("holder_lock_acquired", parent_gid=..., holder_type=...)
log.debug("holder_lock_released", parent_gid=..., holder_type=...)

# Idempotency
log.info("holder_already_tracked", parent_gid=..., holder_type=..., holder_gid=...)
```

### NFR-004: Backward Compatibility

- `auto_create_holders=True` is the default, matching legacy monolith behavior.
- `auto_create_holders=False` preserves today's autom8_asana behavior exactly.
- No existing SaveSession APIs change signature (only new optional parameter).
- No existing tests need modification (they don't set `auto_create_holders`, get True, but have no children that need holders).

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| This TDD | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/TDD-GAP-01-hierarchical-save.md` | Written |
| PRD (source) | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-GAP-01-hierarchical-save.md` | Read |
| ADR (companion) | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/ADR-GAP-01-pipeline-vs-holder-manager.md` | Written |
| SavePipeline | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/pipeline.py` | Read |
| SaveSession | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` | Read |
| DependencyGraph | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/graph.py` | Read |
| BatchExecutor | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/executor.py` | Read |
| ChangeTracker | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/tracker.py` | Read |
| SaveResult / models | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/models.py` | Read |
| Business model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/business.py` | Read |
| Unit model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/unit.py` | Read |
| HolderFactory | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/holder_factory.py` | Read |
| Offer model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/offer.py` | Read |
| Contact model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/contact.py` | Read |
| Location model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/location.py` | Read |
| Process model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/process.py` | Read |
| HealingManager | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/healing.py` | Read |
| Mixins | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/mixins.py` | Read |
| AsanaResource base | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/base.py` | Read |
| Task model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py` | Read |
| NameGid | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/common.py` | Read |
| Detection facade | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/detection/facade.py` | Read |
