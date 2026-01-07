---
artifact_id: TDD-sdk-cascade-resolution
title: "SDK Cascade Resolution Fix"
created_at: "2026-01-05T10:00:00Z"
author: architect
prd_ref: PRD-sdk-cascade-resolution
status: draft
components:
  - name: TasksClient.list_async
    type: module
    description: "Paginated task listing with opt_fields propagation fix"
    dependencies:
      - name: BaseClient._build_opt_fields
        type: internal
      - name: STANDARD_TASK_OPT_FIELDS
        type: internal
  - name: CascadingFieldResolver
    type: module
    description: "Parent chain traversal with unified_store cache integration"
    dependencies:
      - name: UnifiedTaskStore
        type: internal
      - name: CascadingFieldDef
        type: internal
  - name: CascadingFieldDef
    type: module
    description: "Field definition with max_depth configuration"
    dependencies:
      - name: Entity detection
        type: internal
api_contracts: []
data_models:
  - name: CascadingFieldDef
    type: value_object
    fields:
      - name: name
        type: str
        required: true
        constraints: "Custom field name in Asana"
      - name: max_depth
        type: int
        required: false
        constraints: "1-10, default 5"
      - name: target_types
        type: set[str] | None
        required: false
        constraints: "None = all descendants"
security_considerations: []
related_adrs:
  - ADR-0054
  - ADR-0059
schema_version: "1.0"
---

# TDD: SDK Cascade Resolution Fix

> Technical Design Document for fixing cascade field resolution failure affecting 2616 Units.

## 1. Problem Statement

### 1.1 Root Cause

The SDK's `list_async()` method in `clients/tasks.py` does not propagate `opt_fields` correctly to the Asana API. When `opt_fields` is `None`, `_build_opt_fields()` returns an empty dict `{}`, resulting in the Asana API returning only minimal fields (`gid`, `name`, `resource_type`).

**Critical Impact**: Without `parent.gid` in the response, all tasks have `parent=None`, breaking the entire cascade resolution system.

### 1.2 Current Behavior (Bug)

```python
# BaseClient._build_opt_fields (lines 58-69)
def _build_opt_fields(self, opt_fields: list[str] | None) -> dict[str, Any]:
    if not opt_fields:
        return {}  # <-- BUG: Returns empty when None
    return {"opt_fields": ",".join(opt_fields)}
```

When calling:
```python
tasks = await client.tasks.list_async(project="123")  # No opt_fields
```

The API receives no `opt_fields` parameter, returning:
```json
{"gid": "123", "name": "Unit Task", "resource_type": "task"}
// parent field NOT included - cascade resolution impossible
```

### 1.3 Impact Analysis

| Entity Type | Count | Impact |
|-------------|-------|--------|
| Unit | 2616 | Cannot resolve `office_phone` from Business |
| Offer | ~13k | Cannot inherit Business/Unit fields |
| Process | ~52k | Cannot inherit any cascading fields |

**Hierarchy**: Offer -> OfferHolder -> Unit -> UnitHolder -> Business (5 levels)

---

## 2. Design Requirements

### FR-001: Fix opt_fields Propagation in list_async()

`list_async()` MUST always include `parent.gid` in API requests to enable parent chain traversal.

**Acceptance Criteria**:
- When `opt_fields=None`, use `STANDARD_TASK_OPT_FIELDS` as default
- When `opt_fields` provided, merge with minimum required fields (`parent.gid`)
- Existing callers work without modification (backward compatible)

### FR-002: Iterative Parent Fetching with unified_store Integration

`CascadingFieldResolver` MUST integrate with `UnifiedTaskStore` for parent chain caching.

**Acceptance Criteria**:
- Check `unified_store` before API fetch for parent tasks
- Cache fetched parents in `unified_store` with appropriate TTL
- Support batch warm-up for DataFrame operations
- Respect `CompletenessLevel` when retrieving from cache

### FR-003: max_depth Configuration for CascadingFieldDef

`CascadingFieldDef` MUST support configurable traversal depth.

**Acceptance Criteria**:
- Add `max_depth` field with default of 5
- Schema-driven depth (Business fields = 5, Unit fields = 3)
- Prevent infinite traversal loops
- Expose in registry for lookup

### FR-004: Backward Compatibility

Breaking change is acceptable (bug fix), but minimize caller changes.

**Acceptance Criteria**:
- Existing code continues to work without modification
- No new required parameters
- Optional enhanced behavior via new parameters

---

## 3. Component Design

### 3.1 Component: TasksClient.list_async Fix

**File**: `src/autom8_asana/clients/tasks.py` (lines 563-628)

**Current Implementation**:
```python
def list_async(
    self,
    *,
    project: str | None = None,
    # ... other params
    opt_fields: list[str] | None = None,
    limit: int = 100,
) -> PageIterator[Task]:
    async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
        params = self._build_opt_fields(opt_fields)  # Returns {} when None
        # ... build params
```

**Proposed Change**:
```python
from autom8_asana.models.business.fields import STANDARD_TASK_OPT_FIELDS

# Module-level constant for minimum required fields
_MINIMUM_OPT_FIELDS: frozenset[str] = frozenset({"parent.gid"})

def list_async(
    self,
    *,
    project: str | None = None,
    # ... other params
    opt_fields: list[str] | None = None,
    include_standard_fields: bool = True,  # New optional parameter
    limit: int = 100,
) -> PageIterator[Task]:

    # FR-001: Ensure opt_fields always includes parent.gid
    effective_opt_fields = self._resolve_opt_fields(
        opt_fields,
        include_standard=include_standard_fields
    )

    async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
        params = self._build_opt_fields(effective_opt_fields)
        # ... rest unchanged
```

**New Helper Method** (in TasksClient):
```python
def _resolve_opt_fields(
    self,
    opt_fields: list[str] | None,
    include_standard: bool = True,
) -> list[str]:
    """Resolve effective opt_fields with required minimums.

    Per FR-001: Ensures parent.gid is always included for cascade support.

    Args:
        opt_fields: Caller-provided fields or None.
        include_standard: If True, include STANDARD_TASK_OPT_FIELDS.

    Returns:
        Merged opt_fields list including required minimums.
    """
    result: set[str] = set()

    # Always include minimum required fields
    result.update(_MINIMUM_OPT_FIELDS)

    if opt_fields is not None:
        # Caller provided explicit fields - merge with minimums
        result.update(opt_fields)
    elif include_standard:
        # No explicit fields - use standard set
        result.update(STANDARD_TASK_OPT_FIELDS)

    return list(result)
```

**Methods Affected**:
| Method | Change Required |
|--------|-----------------|
| `list_async()` | Yes - use `_resolve_opt_fields()` |
| `subtasks_async()` | Yes - use `_resolve_opt_fields()` |
| `dependents_async()` | Yes - use `_resolve_opt_fields()` |
| `get_async()` | No - already passes opt_fields explicitly |

---

### 3.2 Component: CascadingFieldResolver unified_store Integration

**File**: `src/autom8_asana/dataframes/resolver/cascading.py`

**Current Implementation**:
```python
class CascadingFieldResolver:
    def __init__(
        self,
        client: "AsanaClient",
        cascade_plugin: "CascadeViewPlugin | None" = None,
        hierarchy_resolver: Any | None = None,
    ) -> None:
        self._client = client
        self._cascade_plugin = cascade_plugin
        self._hierarchy_resolver = hierarchy_resolver
        self._parent_cache: dict[str, "Task"] = {}  # Local cache only
```

**Proposed Change**:
```python
class CascadingFieldResolver:
    """Resolves field values by traversing parent task chain.

    Per TDD-SDK-CASCADE-RESOLUTION: Integrates with UnifiedTaskStore
    for shared parent caching across DataFrame operations.
    """

    def __init__(
        self,
        client: "AsanaClient",
        cascade_plugin: "CascadeViewPlugin | None" = None,
        hierarchy_resolver: Any | None = None,
        unified_store: "UnifiedTaskStore | None" = None,  # NEW
    ) -> None:
        self._client = client
        self._cascade_plugin = cascade_plugin
        self._hierarchy_resolver = hierarchy_resolver
        self._unified_store = unified_store
        # Local cache as fallback when unified_store not provided
        self._parent_cache: dict[str, "Task"] = {}
```

**New Method: Cache-Aware Parent Fetch**:
```python
async def _fetch_parent_with_cache_async(
    self,
    parent_gid: str,
) -> "Task | None":
    """Fetch parent task using unified_store if available.

    Per FR-002: Checks unified_store before API, caches result.

    Resolution Order:
    1. Local _parent_cache (session-scoped)
    2. unified_store (shared cache)
    3. API fetch (populates both caches)

    Args:
        parent_gid: GID of parent task to fetch.

    Returns:
        Task if found, None on error.
    """
    # 1. Check local cache first (fastest)
    if parent_gid in self._parent_cache:
        logger.debug("cascade_local_cache_hit", extra={"gid": parent_gid})
        return self._parent_cache[parent_gid]

    # 2. Check unified_store if available
    if self._unified_store is not None:
        cached = await self._unified_store.get_async(
            parent_gid,
            required_level=CompletenessLevel.STANDARD,
        )
        if cached is not None:
            # Convert dict to Task and cache locally
            task = Task.model_validate(cached)
            self._parent_cache[parent_gid] = task
            logger.debug("cascade_unified_store_hit", extra={"gid": parent_gid})
            return task

    # 3. Fetch from API
    try:
        task = await self._client.tasks.get_async(
            parent_gid,
            opt_fields=list(STANDARD_TASK_OPT_FIELDS),
        )

        # Cache in both local and unified store
        self._parent_cache[parent_gid] = task
        if self._unified_store is not None:
            await self._unified_store.put_async(
                task.model_dump(),
                opt_fields=list(STANDARD_TASK_OPT_FIELDS),
            )

        logger.debug("cascade_api_fetch", extra={"gid": parent_gid})
        return task

    except Exception as e:
        logger.warning(
            "cascade_parent_fetch_failed",
            extra={"gid": parent_gid, "error": str(e)},
        )
        return None
```

**Modified resolve_async Method**:
```python
async def resolve_async(
    self,
    task: Task,
    field_name: str,
    max_depth: int | None = None,  # Now optional, uses field def default
) -> Any:
    """Traverse parent chain to find field value.

    Per FR-002: Uses unified_store for parent caching.
    Per FR-003: Respects CascadingFieldDef.max_depth.

    Args:
        task: Starting task to resolve from.
        field_name: Custom field name (e.g., "Office Phone").
        max_depth: Override for traversal depth. If None, uses
                  CascadingFieldDef.max_depth or default of 5.

    Returns:
        Field value from ancestor, or None if not found.
    """
    # Look up field in registry
    result = get_cascading_field(field_name)
    if result is None:
        logger.debug(
            "cascade_field_not_registered",
            extra={"field_name": field_name, "task_gid": task.gid},
        )
        return None

    owner_class, field_def = result

    # FR-003: Use field definition's max_depth if not overridden
    effective_max_depth = max_depth if max_depth is not None else field_def.max_depth

    # ... rest of traversal logic using _fetch_parent_with_cache_async
```

---

### 3.3 Component: CascadingFieldDef max_depth Enhancement

**File**: `src/autom8_asana/models/business/fields.py`

**Current Implementation**:
```python
@dataclass(frozen=True)
class CascadingFieldDef:
    name: str
    target_types: set[str] | None = None
    allow_override: bool = False
    cascade_on_change: bool = True
    source_field: str | None = None
    transform: Callable[[Any], Any] | None = None
```

**Proposed Change**:
```python
@dataclass(frozen=True)
class CascadingFieldDef:
    """Definition of a field that cascades from owner to descendants.

    Per TDD-SDK-CASCADE-RESOLUTION FR-003: Supports max_depth configuration.

    Attributes:
        name: Custom field name in Asana (must match exactly).
        target_types: Set of entity type names to cascade to, or None for all.
        allow_override: If False (DEFAULT), always overwrite descendant.
        cascade_on_change: If True, change detection includes this field.
        source_field: Model attribute to use if not a custom field.
        transform: Optional function to transform value before cascading.
        max_depth: Maximum parent levels to traverse (1-10, default 5).
    """

    name: str
    target_types: set[str] | None = None
    allow_override: bool = False
    cascade_on_change: bool = True
    source_field: str | None = None
    transform: Callable[[Any], Any] | None = None
    max_depth: int = 5  # NEW - Per FR-003

    def __post_init__(self) -> None:
        """Validate max_depth bounds."""
        if not 1 <= self.max_depth <= 10:
            raise ValueError(f"max_depth must be 1-10, got {self.max_depth}")
```

**Updated Business.CascadingFields**:
```python
class CascadingFields:
    """Fields that cascade from Business to descendants."""

    OFFICE_PHONE = CascadingFieldDef(
        name="Office Phone",
        target_types={"Unit", "Offer", "Process", "Contact"},
        max_depth=5,  # Offer->OfferHolder->Unit->UnitHolder->Business
    )

    COMPANY_ID = CascadingFieldDef(
        name="Company ID",
        target_types=None,
        max_depth=5,
    )

    BUSINESS_NAME = CascadingFieldDef(
        name="Business Name",
        target_types={"Unit", "Offer"},
        source_field="name",
        max_depth=5,
    )

    PRIMARY_CONTACT_PHONE = CascadingFieldDef(
        name="Primary Contact Phone",
        target_types={"Unit", "Offer", "Process"},
        max_depth=5,
    )
```

---

## 4. Sequence Diagrams

### 4.1 Current Flow (Bug)

```
DataFrame Build      TasksClient          Asana API          CascadingResolver
     |                   |                    |                      |
     |--list_async()---->|                    |                      |
     |                   |--GET /tasks------->|                      |
     |                   |    (no opt_fields) |                      |
     |                   |<--{gid, name}------|                      |
     |<--Tasks-----------|                    |                      |
     |                   |                    |                      |
     |--resolve("Office Phone")-------------->|                      |
     |                                        |--task.parent.gid---->|
     |                                        |    (NULL!)           |
     |                                        |<--None---------------|
     |<--None---------------------------------|                      |
```

### 4.2 Fixed Flow

```
DataFrame Build      TasksClient          Asana API       UnifiedStore   CascadingResolver
     |                   |                    |                |               |
     |--list_async()---->|                    |                |               |
     |                   |--GET /tasks------->|                |               |
     |                   |  +opt_fields=      |                |               |
     |                   |   parent.gid,name..|                |               |
     |                   |<--Full data--------|                |               |
     |<--Tasks-----------|                    |                |               |
     |                   |                    |                |               |
     |--resolve("Office Phone", unified_store)---------------->|               |
     |                                                         |--get_async--->|
     |                                                         |   (parent_gid)|
     |                                                         |<--cached?-----|
     |                                                         |               |
     |                                                         |--[if miss]--->|
     |                                                         |   fetch API   |
     |                                                         |<--parent------|
     |                                                         |               |
     |                                                         |--put_async--->|
     |                                                         |   (cache)     |
     |                                                         |               |
     |<--office_phone value------------------------------------|               |
```

---

## 5. Error Handling

### 5.1 Parent Not Found

When parent task doesn't exist or API returns 404:

```python
async def _fetch_parent_with_cache_async(self, parent_gid: str) -> "Task | None":
    try:
        task = await self._client.tasks.get_async(parent_gid, ...)
        return task
    except NotFoundError:
        # Parent task deleted - log and return None
        logger.warning(
            "cascade_parent_not_found",
            extra={"parent_gid": parent_gid},
        )
        return None
    except RateLimitError as e:
        # Rate limit - re-raise for caller to handle
        logger.error(
            "cascade_rate_limited",
            extra={"parent_gid": parent_gid, "retry_after": e.retry_after},
        )
        raise
    except AsanaError as e:
        # Other API error - log and return None
        logger.warning(
            "cascade_api_error",
            extra={"parent_gid": parent_gid, "error": str(e)},
        )
        return None
```

### 5.2 Circular Reference Detection

Already implemented in `_traverse_parent_chain()`:

```python
if current.gid in visited:
    logger.error(
        "cascade_loop_detected",
        extra={
            "task_gid": task.gid,
            "field_name": field_def.name,
            "visited_gids": list(visited),
        },
    )
    return None
```

### 5.3 Max Depth Exceeded

```python
if depth >= effective_max_depth:
    logger.info(
        "cascade_max_depth_exceeded",
        extra={
            "task_gid": task.gid,
            "field_name": field_def.name,
            "max_depth": effective_max_depth,
            "current_depth": depth,
        },
    )
    return None
```

---

## 6. Performance Considerations

### 6.1 Batch Warm-Up Strategy

For DataFrame builds processing thousands of tasks:

```python
async def warm_parent_chains(
    resolver: CascadingFieldResolver,
    tasks: list[Task],
    max_depth: int = 5,
) -> None:
    """Pre-fetch all parent chains for batch processing.

    Collects unique parent GIDs from all tasks and fetches
    in parallel, populating unified_store.

    Args:
        resolver: CascadingFieldResolver with unified_store.
        tasks: Tasks to warm parent chains for.
        max_depth: Maximum traversal depth.
    """
    # Collect unique parent GIDs
    parent_gids: set[str] = set()
    for task in tasks:
        if task.parent and task.parent.gid:
            parent_gids.add(task.parent.gid)

    if not parent_gids:
        return

    # Batch fetch via existing warm_parents method
    await resolver.warm_parents(tasks, max_depth=max_depth)
```

### 6.2 Expected Performance Impact

| Metric | Before (Bug) | After (Fix) |
|--------|--------------|-------------|
| API calls per Unit | 0 (no parent) | 1-5 (parent chain) |
| Cache hits after warm-up | N/A | 95%+ |
| Total API calls (2616 Units) | 2616 | ~3000 (warm-up) + cache |
| Cascade resolution success | 0% | 100% |

### 6.3 Cache TTL Strategy

| Entity Type | TTL | Rationale |
|-------------|-----|-----------|
| Business | 24h | Root entities rarely change |
| UnitHolder | 12h | Structural holder |
| Unit | 6h | May change daily |
| OfferHolder | 6h | Structural holder |
| Offer | 2h | Active work entities |

---

## 7. Test Strategy

### 7.1 Unit Tests

**File**: `tests/unit/clients/test_tasks_opt_fields.py`

```python
class TestListAsyncOptFields:
    """Tests for FR-001: opt_fields propagation."""

    async def test_list_async_no_opt_fields_includes_parent_gid(
        self, tasks_client, mock_http
    ):
        """When opt_fields=None, parent.gid must be included."""
        await tasks_client.list_async(project="123").collect()

        call_args = mock_http.get_paginated.call_args
        params = call_args[1]["params"]

        assert "opt_fields" in params
        assert "parent.gid" in params["opt_fields"]

    async def test_list_async_explicit_opt_fields_merged_with_minimum(
        self, tasks_client, mock_http
    ):
        """Explicit opt_fields are merged with minimum required fields."""
        await tasks_client.list_async(
            project="123",
            opt_fields=["name", "notes"],
        ).collect()

        call_args = mock_http.get_paginated.call_args
        params = call_args[1]["params"]
        opt_fields_list = params["opt_fields"].split(",")

        # Explicit fields included
        assert "name" in opt_fields_list
        assert "notes" in opt_fields_list
        # Minimum fields also included
        assert "parent.gid" in opt_fields_list
```

**File**: `tests/unit/dataframes/resolver/test_cascading_unified.py`

```python
class TestCascadingResolverUnifiedStore:
    """Tests for FR-002: unified_store integration."""

    async def test_resolve_checks_unified_store_before_api(
        self, resolver, mock_unified_store, mock_client
    ):
        """unified_store is checked before making API call."""
        mock_unified_store.get_async.return_value = {
            "gid": "parent-123",
            "parent": None,
            "custom_fields": [{"name": "Office Phone", "text_value": "555-1234"}],
        }

        value = await resolver.resolve_async(unit_task, "Office Phone")

        assert value == "555-1234"
        mock_unified_store.get_async.assert_called_once()
        mock_client.tasks.get_async.assert_not_called()

    async def test_resolve_caches_api_result_in_unified_store(
        self, resolver, mock_unified_store, mock_client
    ):
        """API fetch result is cached in unified_store."""
        mock_unified_store.get_async.return_value = None  # Cache miss
        mock_client.tasks.get_async.return_value = parent_task

        await resolver.resolve_async(unit_task, "Office Phone")

        mock_unified_store.put_async.assert_called_once()
```

**File**: `tests/unit/models/business/test_cascading_field_def.py`

```python
class TestCascadingFieldDefMaxDepth:
    """Tests for FR-003: max_depth configuration."""

    def test_max_depth_default_is_5(self):
        """Default max_depth is 5."""
        field_def = CascadingFieldDef(name="Test Field")
        assert field_def.max_depth == 5

    def test_max_depth_can_be_customized(self):
        """max_depth can be set to custom value."""
        field_def = CascadingFieldDef(name="Test Field", max_depth=3)
        assert field_def.max_depth == 3

    def test_max_depth_validation_rejects_zero(self):
        """max_depth must be at least 1."""
        with pytest.raises(ValueError, match="must be 1-10"):
            CascadingFieldDef(name="Test", max_depth=0)

    def test_max_depth_validation_rejects_over_10(self):
        """max_depth cannot exceed 10."""
        with pytest.raises(ValueError, match="must be 1-10"):
            CascadingFieldDef(name="Test", max_depth=11)
```

### 7.2 Integration Tests

**File**: `tests/integration/test_cascade_resolution_e2e.py`

```python
@pytest.mark.integration
class TestCascadeResolutionE2E:
    """End-to-end cascade resolution tests."""

    async def test_unit_resolves_office_phone_from_business(
        self, live_client, known_unit_gid, known_business_phone
    ):
        """Unit task can resolve office_phone from Business ancestor."""
        unit = await live_client.tasks.get_async(known_unit_gid)

        resolver = CascadingFieldResolver(
            client=live_client,
            unified_store=create_unified_store(),
        )

        value = await resolver.resolve_async(unit, "Office Phone")

        assert value == known_business_phone

    async def test_batch_warm_up_reduces_api_calls(
        self, live_client, unit_gids
    ):
        """Batch warm-up populates cache for subsequent resolves."""
        resolver = CascadingFieldResolver(
            client=live_client,
            unified_store=create_unified_store(),
        )

        tasks = [
            await live_client.tasks.get_async(gid)
            for gid in unit_gids[:10]
        ]

        # Warm up
        await resolver.warm_parents(tasks)

        # Subsequent resolves should be cache hits
        initial_stats = resolver._unified_store.get_stats()

        for task in tasks:
            await resolver.resolve_async(task, "Office Phone")

        final_stats = resolver._unified_store.get_stats()

        # All parent lookups should be cache hits
        assert final_stats["get_hits"] > initial_stats["get_hits"]
```

### 7.3 Regression Test

**File**: `tests/regression/test_2616_units_cascade.py`

```python
@pytest.mark.regression
async def test_all_units_can_resolve_office_phone(live_client):
    """Regression: All 2616 Units must resolve office_phone.

    This test validates the fix for the cascade resolution bug
    where parent=None caused 100% resolution failure.
    """
    # Get Units from production project
    units = await live_client.tasks.list_async(
        project=UNITS_PROJECT_GID,
        opt_fields=["name", "parent.gid", "custom_fields"],
    ).collect()

    resolver = CascadingFieldResolver(
        client=live_client,
        unified_store=create_unified_store(),
    )

    # Warm up parent chains
    await resolver.warm_parents(units)

    # Resolve office_phone for all units
    failures = []
    for unit in units:
        value = await resolver.resolve_async(unit, "Office Phone")
        if value is None:
            failures.append(unit.gid)

    # Expect 0 failures (was 2616 before fix)
    assert len(failures) == 0, f"Failed to resolve for {len(failures)} units"
```

---

## 8. Migration Strategy

### 8.1 Phase 1: Fix opt_fields (No Breaking Changes)

1. Add `_resolve_opt_fields()` helper to TasksClient
2. Update `list_async()`, `subtasks_async()`, `dependents_async()`
3. Deploy - existing code works better automatically

### 8.2 Phase 2: Add unified_store Integration (Optional Enhancement)

1. Add `unified_store` parameter to CascadingFieldResolver
2. Update `_fetch_parent_async()` to use cache
3. Update DataFrame builders to pass unified_store

### 8.3 Phase 3: Add max_depth to CascadingFieldDef (Schema Enhancement)

1. Add `max_depth` field with default=5
2. Add validation in `__post_init__`
3. Update Business/Unit CascadingFields definitions

---

## 9. Rollback Plan

### 9.1 Phase 1 Rollback

If opt_fields change causes issues:
```python
# Revert _resolve_opt_fields to pass-through
def _resolve_opt_fields(self, opt_fields, include_standard=True):
    return opt_fields  # Revert to original behavior
```

### 9.2 Phase 2 Rollback

unified_store is optional - no rollback needed:
```python
resolver = CascadingFieldResolver(
    client=client,
    unified_store=None,  # Disable feature
)
```

---

## 10. Verification Checklist

- [ ] `list_async()` always includes `parent.gid` in API requests
- [ ] Tasks returned have non-null `parent` when applicable
- [ ] CascadingFieldResolver uses unified_store when provided
- [ ] Parent tasks are cached in unified_store after fetch
- [ ] CascadingFieldDef accepts and validates max_depth
- [ ] All 2616 Units successfully resolve office_phone
- [ ] Existing tests continue to pass
- [ ] New regression test added and passing

---

## 11. Artifact Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-sdk-cascade-resolution.md` | Pending |
| Implementation | `src/autom8_asana/clients/tasks.py` | Pending |
| Implementation | `src/autom8_asana/dataframes/resolver/cascading.py` | Pending |
| Implementation | `src/autom8_asana/models/business/fields.py` | Pending |
| Tests | `tests/unit/clients/test_tasks_opt_fields.py` | Pending |
| Tests | `tests/regression/test_2616_units_cascade.py` | Pending |
