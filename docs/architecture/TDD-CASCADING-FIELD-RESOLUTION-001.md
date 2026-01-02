# TDD: Cascading Field Resolution for DataFrame Extractors

**TDD ID**: TDD-CASCADING-FIELD-RESOLUTION-001
**Version**: 1.0
**Date**: 2026-01-02
**Author**: Architect
**Status**: DRAFT
**PRD Reference**: N/A (Technical initiative from Entity Resolver NOT_FOUND investigation)

---

## Overview

This document defines the technical approach for enabling DataFrame extractors to resolve custom fields from parent and grandparent tasks using the existing `CascadingFieldDef` system. Currently, the Entity Resolver returns NOT_FOUND for valid phone/vertical pairs because Unit tasks do not directly contain the `Office Phone` custom field - it lives on the Business (grandparent) task and should cascade down.

### Problem Statement

```
Entity Hierarchy:
Business (has Office Phone) --> UnitHolder --> Unit (needs Office Phone for lookup)
                                              ^
                                              |
                                   Entity Resolver queries here,
                                   but Office Phone is 2 levels up
```

The `UNIT_SCHEMA` declares:
```python
ColumnDef(
    name="office_phone",
    source="cf:Office Phone",  # <-- Looks locally, but field is on Business
)
```

The `DefaultCustomFieldResolver.get_value()` only searches `task.custom_fields` on the current task. It does not traverse to parent tasks.

### Solution Summary

Bridge the DataFrame extraction layer to the business model layer's `CascadingFieldDef` system by:

1. Introducing a new column source prefix: `cascade:` (e.g., `source="cascade:Office Phone"`)
2. Creating a `CascadingFieldResolver` that wraps `DefaultCustomFieldResolver` and adds parent traversal
3. Leveraging existing caching mechanisms to minimize API calls

---

## Constraints

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Python version | >= 3.11 | Match existing requirements |
| API calls | Acceptable | Per stakeholder: correctness over speed |
| DRY principle | Mandatory | Must use existing CascadingFieldDef, no new source of truth |
| Backward compatibility | Required | Existing `cf:` sources must continue to work |
| Test coverage | >= existing baseline | No regression |
| Cache utilization | Required | Use existing caching to minimize API overhead |

---

## Functional Requirements

### FR-CASCADE-RESOLVE-001: Cascade Source Prefix

The schema system SHALL support a `cascade:` prefix in `ColumnDef.source` to indicate fields that require parent traversal.

**Acceptance Criteria:**
- `source="cascade:Office Phone"` triggers parent chain resolution
- `source="cf:Office Phone"` continues to resolve locally only (backward compatible)
- Prefix is case-insensitive (`CASCADE:`, `Cascade:` also work)

### FR-CASCADE-RESOLVE-002: Parent Chain Traversal

When a `cascade:` source is encountered, the resolver SHALL traverse the parent chain to find the field value.

**Traversal Algorithm:**
1. Check current task's `custom_fields` first (local value)
2. If not found or if `allow_override=False` in CascadingFieldDef, fetch `parent.gid`
3. Fetch parent task with `custom_fields` and `parent.gid`
4. Repeat until field found or root reached (no parent)
5. Return first non-null value in chain, respecting `allow_override` semantics

**Acceptance Criteria:**
- Unit task can resolve `Office Phone` from Business (2 levels up)
- Traversal stops at first non-null value (or continues based on `allow_override`)
- Returns `None` if field not found in entire chain

### FR-CASCADE-RESOLVE-003: CascadingFieldDef Integration

The resolver SHALL consult the `CascadingFieldDef` registry to determine:
- Whether the field cascades to the current entity type
- Whether local override is allowed (`allow_override`)
- Which entity types define this cascading field

**Acceptance Criteria:**
- `Business.CascadingFields.OFFICE_PHONE` configuration is respected
- `target_types` filter is applied (e.g., OFFICE_PHONE targets Unit, Offer, Process)
- Resolution fails gracefully if field has no CascadingFieldDef registered

### FR-CASCADE-RESOLVE-004: Task Caching

Parent task fetches SHALL utilize existing caching mechanisms to minimize API calls.

**Caching Strategy:**
- Check `_gid_index_cache` or task cache before API call
- Cache fetched parent tasks for reuse within same extraction batch
- Respect cache TTL (`_INDEX_TTL_SECONDS = 3600`)

**Acceptance Criteria:**
- Repeated parent traversals within same batch use cached tasks
- Cache misses trigger single API call per unique parent GID
- Cache invalidation follows existing patterns

### FR-CASCADE-RESOLVE-005: Batch Optimization

For batch extraction of multiple tasks, the resolver SHALL optimize parent fetches.

**Optimization Strategy:**
1. Collect all unique parent GIDs needed across batch
2. Batch-fetch parents in single request where possible
3. Cache all fetched parents for subsequent traversals

**Acceptance Criteria:**
- Extracting 100 Units with same Business parent makes <= 3 API calls (Business + UnitHolder + batch fetch)
- Parent GIDs are deduplicated before fetching

### FR-CASCADE-RESOLVE-006: Schema Update for Unit

The `UNIT_SCHEMA` SHALL be updated to use `cascade:` prefix for fields that live on parent tasks.

**Fields to Update:**
- `office_phone`: `source="cf:Office Phone"` -> `source="cascade:Office Phone"`
- `vertical`: May remain `cf:` if typically set on Unit

**Acceptance Criteria:**
- UNIT_SCHEMA uses `cascade:Office Phone` for office_phone column
- Entity Resolver returns correct Unit GIDs for phone/vertical lookups

### FR-CASCADE-RESOLVE-007: Fallback to Local

If `cascade:` resolution finds no value in parent chain, the resolver SHALL fall back to checking the local task.

**Acceptance Criteria:**
- `cascade:Office Phone` on a Business task returns Business's own value
- Orphan tasks (no parent) return their local value or None

---

## Non-Functional Requirements

### NFR-CASCADE-001: Performance

Parent traversal SHALL complete within acceptable latency bounds.

| Metric | Target | Rationale |
|--------|--------|-----------|
| Single task extraction | < 500ms | Acceptable for correctness-first approach |
| Batch extraction (100 tasks) | < 5s | Amortized via caching |
| Parent chain depth | <= 5 levels | Business -> UnitHolder -> Unit -> OfferHolder -> Offer |

### NFR-CASCADE-002: Reliability

The cascading resolver SHALL handle edge cases gracefully.

| Scenario | Behavior |
|----------|----------|
| Parent task deleted | Return None, log warning |
| API rate limit | Respect existing RetryHandler/RateLimiter |
| Circular parent reference | Detect loop, return None, log error |
| Cache corruption | Clear cache, retry fetch |

### NFR-CASCADE-003: Observability

The resolver SHALL emit structured logs for debugging.

| Log Event | Level | Fields |
|-----------|-------|--------|
| `cascade_traversal_start` | DEBUG | task_gid, field_name, source |
| `cascade_parent_fetch` | DEBUG | child_gid, parent_gid, cache_hit |
| `cascade_field_found` | DEBUG | task_gid, field_name, found_at_gid, depth |
| `cascade_field_not_found` | INFO | task_gid, field_name, chain_depth |
| `cascade_loop_detected` | ERROR | task_gid, visited_gids |

### NFR-CASCADE-004: Testability

All cascading resolution logic SHALL be unit-testable with mock data.

**Requirements:**
- `CascadingFieldResolver` accepts injectable client/cache for testing
- Mock parent chains can be constructed without API calls
- Integration tests use test project with known hierarchy

---

## Component Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DataFrame Extraction Layer                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌──────────────────────┐    ┌───────────────────┐  │
│  │  ColumnDef  │───>│   BaseExtractor      │───>│    TaskRow        │  │
│  │  source=    │    │   _extract_column()  │    │                   │  │
│  │  "cascade:" │    │                      │    │                   │  │
│  └─────────────┘    └──────────────────────┘    └───────────────────┘  │
│        │                     │                                          │
│        │                     v                                          │
│        │            ┌──────────────────────┐                           │
│        │            │ CascadingFieldResolver│  <── NEW COMPONENT       │
│        │            │ (wraps Default)       │                           │
│        │            └──────────────────────┘                           │
│        │                     │                                          │
│        │                     v                                          │
│        │            ┌──────────────────────┐                           │
│        │            │DefaultCustomFieldResolver│                        │
│        │            │ (local lookup)        │                           │
│        │            └──────────────────────┘                           │
│        │                     │                                          │
└────────┼─────────────────────┼──────────────────────────────────────────┘
         │                     │
         v                     v
┌─────────────────────────────────────────────────────────────────────────┐
│                        Business Model Layer                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────┐    ┌──────────────────────┐                  │
│  │   CascadingFieldDef  │    │   Parent Traversal   │                  │
│  │   (field definitions)│    │   (API + Cache)      │                  │
│  │                      │    │                      │                  │
│  │   OFFICE_PHONE =     │    │   task.parent.gid    │                  │
│  │     CascadingFieldDef│───>│   client.tasks.get() │                  │
│  │     target_types=    │    │   _parent_cache      │                  │
│  │     {"Unit",...}     │    │                      │                  │
│  └──────────────────────┘    └──────────────────────┘                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component: CascadingFieldResolver

**Location**: `src/autom8_asana/dataframes/resolver/cascading.py`

**Responsibilities:**
1. Parse `cascade:` prefix from source strings
2. Delegate local lookups to `DefaultCustomFieldResolver`
3. Traverse parent chain when cascade resolution needed
4. Cache parent task data for batch efficiency
5. Consult `CascadingFieldDef` registry for field semantics

**Interface:**

```python
class CascadingFieldResolver:
    """Resolver that supports parent chain traversal for cascading fields.

    Wraps DefaultCustomFieldResolver and adds cascade: source prefix support.
    Uses CascadingFieldDef from business model layer for field semantics.

    Example:
        >>> resolver = CascadingFieldResolver(client=client)
        >>> # Local lookup (cf: prefix)
        >>> value = await resolver.get_value_async(task, "cf:MRR")
        >>> # Cascading lookup (cascade: prefix)
        >>> value = await resolver.get_value_async(task, "cascade:Office Phone")
    """

    def __init__(
        self,
        client: AsanaClient | None = None,
        default_resolver: DefaultCustomFieldResolver | None = None,
        parent_cache: dict[str, Task] | None = None,
    ) -> None:
        """Initialize resolver with optional dependencies for testing."""
        ...

    async def get_value_async(
        self,
        task: Task,
        source: str,
        column_def: ColumnDef | None = None,
    ) -> Any:
        """Get field value, traversing parents if source uses cascade: prefix."""
        ...

    def get_value(
        self,
        task: Task,
        source: str,
        column_def: ColumnDef | None = None,
    ) -> Any:
        """Sync wrapper - raises if cascade: used without event loop."""
        ...

    async def prefetch_parents_async(
        self,
        tasks: list[Task],
    ) -> None:
        """Prefetch all parent tasks needed for a batch extraction."""
        ...

    def _parse_source(self, source: str) -> tuple[str, str]:
        """Parse source into (prefix, field_name)."""
        ...

    async def _resolve_cascade_async(
        self,
        task: Task,
        field_name: str,
        column_def: ColumnDef | None,
    ) -> Any:
        """Traverse parent chain to resolve cascading field."""
        ...

    def _get_cascading_field_def(self, field_name: str) -> CascadingFieldDef | None:
        """Look up CascadingFieldDef by field name from registered entities."""
        ...
```

### Component: ColumnDef Extension

**Location**: `src/autom8_asana/dataframes/models/schema.py`

**Changes:**
- Document `cascade:` prefix in ColumnDef docstring
- No code changes needed - prefix parsing handled by resolver

```python
@dataclass(frozen=True)
class ColumnDef:
    """Definition of a single DataFrame column.

    Source Prefixes:
        - None: Derived field, delegates to _extract_{name} method
        - "attribute": Direct attribute access on task
        - "cf:Name": Custom field lookup by name (local only)
        - "gid:123": Custom field lookup by GID (local only)
        - "cascade:Name": Cascading field - traverses parent chain
    """
```

### Component: BaseExtractor Integration

**Location**: `src/autom8_asana/dataframes/extractors/base.py`

**Changes to `_extract_column()`:**

```python
def _extract_column(
    self,
    task: Task,
    col: ColumnDef,
    project_gid: str | None = None,
) -> Any:
    """Extract a single column value from a task."""
    if col.source is None:
        # Derived field handling (unchanged)
        ...

    # NEW: Handle cascade: prefix
    if col.source.lower().startswith("cascade:"):
        if self._resolver is None:
            raise ValueError(
                f"Resolver required for cascading field: {col.source}"
            )
        # CascadingFieldResolver handles the traversal
        return self._resolver.get_value(task, col.source, column_def=col)

    if col.source.startswith("cf:") or col.source.startswith("gid:"):
        # Custom field extraction (unchanged)
        ...

    # Direct attribute access (unchanged)
    ...
```

**Async Extraction Support:**

For cascading fields that require API calls, introduce async extraction:

```python
async def extract_async(
    self,
    task: Task,
    project_gid: str | None = None,
) -> TaskRow:
    """Async extraction supporting cascading fields."""
    ...
```

---

## Data Flow

### Sequence: Single Task Extraction with Cascade

```
┌──────────┐     ┌──────────────┐     ┌───────────────────┐     ┌─────────────┐
│  Caller  │     │ UnitExtractor│     │CascadingFieldResolver│   │ AsanaClient │
└────┬─────┘     └──────┬───────┘     └─────────┬─────────┘     └──────┬──────┘
     │                  │                       │                      │
     │ extract_async()  │                       │                      │
     │─────────────────>│                       │                      │
     │                  │                       │                      │
     │                  │ _extract_column()     │                      │
     │                  │ source="cascade:..."  │                      │
     │                  │──────────────────────>│                      │
     │                  │                       │                      │
     │                  │                       │ Check local first    │
     │                  │                       │──────┐               │
     │                  │                       │<─────┘ Not found     │
     │                  │                       │                      │
     │                  │                       │ Check parent cache   │
     │                  │                       │──────┐               │
     │                  │                       │<─────┘ Miss          │
     │                  │                       │                      │
     │                  │                       │ tasks.get_async()    │
     │                  │                       │─────────────────────>│
     │                  │                       │                      │
     │                  │                       │<─────────────────────│
     │                  │                       │      parent Task     │
     │                  │                       │                      │
     │                  │                       │ Cache parent         │
     │                  │                       │──────┐               │
     │                  │                       │<─────┘               │
     │                  │                       │                      │
     │                  │                       │ Check parent cf      │
     │                  │                       │──────┐               │
     │                  │                       │<─────┘ Not found     │
     │                  │                       │                      │
     │                  │                       │ Recurse to grandparent│
     │                  │                       │─────────────────────>│
     │                  │                       │                      │
     │                  │                       │<─────────────────────│
     │                  │                       │      grandparent Task│
     │                  │                       │                      │
     │                  │                       │ Check grandparent cf │
     │                  │                       │──────┐               │
     │                  │                       │<─────┘ FOUND!        │
     │                  │                       │                      │
     │                  │<──────────────────────│ return value         │
     │                  │                       │                      │
     │<─────────────────│ TaskRow               │                      │
     │                  │                       │                      │
```

### Sequence: Batch Extraction with Prefetch

```
┌──────────┐     ┌──────────────┐     ┌───────────────────┐     ┌─────────────┐
│  Caller  │     │ UnitExtractor│     │CascadingFieldResolver│   │ AsanaClient │
└────┬─────┘     └──────┬───────┘     └─────────┬─────────┘     └──────┬──────┘
     │                  │                       │                      │
     │ extract_batch()  │                       │                      │
     │ [task1..task100] │                       │                      │
     │─────────────────>│                       │                      │
     │                  │                       │                      │
     │                  │ prefetch_parents()    │                      │
     │                  │ [task1..task100]      │                      │
     │                  │──────────────────────>│                      │
     │                  │                       │                      │
     │                  │                       │ Collect unique       │
     │                  │                       │ parent GIDs          │
     │                  │                       │──────┐               │
     │                  │                       │<─────┘               │
     │                  │                       │                      │
     │                  │                       │ Batch fetch parents  │
     │                  │                       │ (deduplicated)       │
     │                  │                       │─────────────────────>│
     │                  │                       │                      │
     │                  │                       │<─────────────────────│
     │                  │                       │      [parents]       │
     │                  │                       │                      │
     │                  │                       │ Cache all parents    │
     │                  │                       │──────┐               │
     │                  │                       │<─────┘               │
     │                  │                       │                      │
     │                  │<──────────────────────│ prefetch complete    │
     │                  │                       │                      │
     │                  │ for task in tasks:    │                      │
     │                  │   extract_async()     │                      │
     │                  │   (uses cached parents)                      │
     │                  │───────────────────────────────────────────────│
     │                  │                       │                      │
     │<─────────────────│ [TaskRow1..100]       │                      │
     │                  │                       │                      │
```

---

## Schema Changes

### UNIT_SCHEMA Update

**File**: `src/autom8_asana/dataframes/schemas/unit.py`

```python
UNIT_COLUMNS: list[ColumnDef] = [
    # ... existing columns ...

    ColumnDef(
        name="office_phone",
        dtype="Utf8",
        nullable=True,
        source="cascade:Office Phone",  # CHANGED from "cf:Office Phone"
        description="Office phone number (cascades from Business)",
    ),

    # vertical stays as cf: since it's typically set on Unit
    ColumnDef(
        name="vertical",
        dtype="Utf8",
        nullable=True,
        source="cf:Vertical",  # UNCHANGED - usually on Unit
        description="Business vertical",
    ),

    # ... rest unchanged ...
]
```

---

## CascadingFieldDef Registry

### Field Definition Lookup

The resolver needs to find CascadingFieldDef for a given field name. Options:

**Option A: Static Registry (Recommended)**
Create a module-level registry mapping field names to their definitions:

```python
# src/autom8_asana/models/business/fields.py

CASCADING_FIELD_REGISTRY: dict[str, CascadingFieldDef] = {}

def register_cascading_field(field_def: CascadingFieldDef) -> None:
    """Register a cascading field definition."""
    CASCADING_FIELD_REGISTRY[field_def.name] = field_def

def get_cascading_field_def(field_name: str) -> CascadingFieldDef | None:
    """Get CascadingFieldDef by field name."""
    return CASCADING_FIELD_REGISTRY.get(field_name)

# Auto-register on module load
for field_def in Business.CascadingFields.all():
    register_cascading_field(field_def)
for field_def in Unit.CascadingFields.all():
    register_cascading_field(field_def)
```

**Option B: Dynamic Discovery**
Walk entity classes at runtime. More complex, less predictable.

**Decision**: Option A - Static registry is simpler, faster, and explicit.

---

## API/Interface Changes

### New Protocol: AsyncCustomFieldResolver

```python
# src/autom8_asana/dataframes/resolver/protocol.py

class AsyncCustomFieldResolver(Protocol):
    """Protocol for resolvers supporting async cascading resolution."""

    async def get_value_async(
        self,
        task: Task,
        source: str,
        column_def: ColumnDef | None = None,
    ) -> Any:
        """Async field value resolution."""
        ...

    async def prefetch_parents_async(
        self,
        tasks: list[Task],
    ) -> None:
        """Prefetch parent tasks for batch efficiency."""
        ...
```

### BaseExtractor Changes

```python
class BaseExtractor(ABC):
    def __init__(
        self,
        schema: DataFrameSchema,
        resolver: CustomFieldResolver | AsyncCustomFieldResolver | None = None,
    ) -> None:
        """Accept both sync and async resolvers."""
        ...

    async def extract_async(
        self,
        task: Task,
        project_gid: str | None = None,
    ) -> TaskRow:
        """Async extraction for cascading field support."""
        ...

    async def extract_batch_async(
        self,
        tasks: list[Task],
        project_gid: str | None = None,
    ) -> list[TaskRow]:
        """Batch extraction with prefetch optimization."""
        if hasattr(self._resolver, 'prefetch_parents_async'):
            await self._resolver.prefetch_parents_async(tasks)
        return [await self.extract_async(t, project_gid) for t in tasks]
```

---

## Migration Strategy

### Phase 1: Add CascadingFieldResolver (Non-Breaking)

1. Create `CascadingFieldResolver` class
2. Create static `CASCADING_FIELD_REGISTRY`
3. Add `extract_async()` to BaseExtractor
4. Add unit tests for cascading resolution

**Rollback**: Delete new files, no schema changes yet.

### Phase 2: Update UNIT_SCHEMA

1. Change `office_phone` source to `cascade:Office Phone`
2. Update UnitExtractor to use CascadingFieldResolver
3. Run integration tests

**Rollback**: Revert schema to `cf:Office Phone`.

### Phase 3: Update Entity Resolver

1. Inject CascadingFieldResolver into UnitResolutionStrategy
2. Use async DataFrame building with cascading support
3. Verify phone/vertical lookups succeed

**Rollback**: Revert to DefaultCustomFieldResolver.

### Phase 4: Extend to Other Schemas

1. Audit other schemas for cascading field candidates
2. Update schemas as needed
3. Monitor performance in production

---

## Test Strategy

### Unit Tests

**File**: `tests/unit/test_cascading_resolver.py`

| Test Case | Description |
|-----------|-------------|
| `test_parse_cascade_source` | Parses `cascade:Office Phone` correctly |
| `test_parse_cf_source` | Delegates `cf:MRR` to default resolver |
| `test_local_value_found` | Returns local value when present |
| `test_parent_traversal` | Fetches parent and finds field |
| `test_grandparent_traversal` | Traverses 2 levels to find field |
| `test_field_not_found` | Returns None when field not in chain |
| `test_cache_hit` | Uses cached parent on second access |
| `test_prefetch_batch` | Prefetches all unique parents |
| `test_circular_detection` | Detects parent loop, returns None |
| `test_allow_override_true` | Respects local override when allowed |
| `test_allow_override_false` | Uses parent value regardless of local |

### Integration Tests

**File**: `tests/integration/test_cascading_extraction.py`

| Test Case | Description |
|-----------|-------------|
| `test_unit_with_cascading_office_phone` | Extract Unit, get Business's Office Phone |
| `test_batch_extraction_efficiency` | 100 Units, verify <= 5 API calls |
| `test_entity_resolver_with_cascade` | Phone/vertical lookup returns correct GID |

### Backward Compatibility Tests

| Test Case | Description |
|-----------|-------------|
| `test_cf_source_unchanged` | `cf:MRR` still works as before |
| `test_existing_schemas_pass` | All existing schema tests pass |
| `test_sync_extractor_unchanged` | Sync extraction still works for non-cascade |

---

## Risk Assessment

| Risk ID | Risk | Probability | Impact | Mitigation |
|---------|------|-------------|--------|------------|
| RISK-001 | API rate limiting from parent fetches | Medium | High | Batch prefetch, caching, respect RateLimiter |
| RISK-002 | Performance regression for large batches | Medium | Medium | Prefetch optimization, cache parent tasks |
| RISK-003 | Circular parent references | Low | High | Loop detection with visited set |
| RISK-004 | CascadingFieldDef not found for field | Low | Low | Graceful fallback to local-only |
| RISK-005 | Breaking sync extraction | Medium | High | Preserve sync path, only cascade: requires async |

---

## ADR: Cascade Source Prefix

**ADR-CASCADE-001: Introduce cascade: Source Prefix**

**Status**: Proposed

**Context**: The DataFrame extraction layer and business model layer use different mechanisms for field resolution. Custom fields that cascade from parent entities (e.g., Office Phone from Business to Unit) are not resolved by the current `cf:` prefix which only searches locally.

**Decision**: Introduce a `cascade:` source prefix that signals the extractor to traverse the parent chain using the existing `CascadingFieldDef` system from the business model layer.

**Consequences**:
- Positive: Bridges two layers without duplicating relationship definitions (DRY)
- Positive: Explicit opt-in via prefix - no surprise behavior changes
- Positive: Backward compatible - existing `cf:` sources unchanged
- Negative: Requires async extraction for cascading fields
- Negative: Additional API calls for parent traversal (mitigated by caching)

---

## Success Criteria

Migration complete when:

- [ ] `cascade:` prefix recognized and parsed by resolver
- [ ] Parent chain traversal correctly finds Business.office_phone from Unit
- [ ] `CascadingFieldDef` semantics (target_types, allow_override) respected
- [ ] Parent tasks cached within extraction batch
- [ ] UNIT_SCHEMA updated with `cascade:Office Phone`
- [ ] Entity Resolver returns correct Unit GIDs for phone/vertical lookups
- [ ] All existing tests pass (no regression)
- [ ] Performance within NFR bounds (< 500ms single, < 5s batch of 100)
- [ ] ruff check and mypy pass

---

## Artifact Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/architecture/TDD-CASCADING-FIELD-RESOLUTION-001.md` | Pending |
| CascadingFieldDef | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/fields.py` | Yes |
| DefaultCustomFieldResolver | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/resolver/default.py` | Yes |
| BaseExtractor | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/extractors/base.py` | Yes |
| UNIT_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/unit.py` | Yes |
| Entity Resolver | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` | Yes |

---

**End of TDD**
