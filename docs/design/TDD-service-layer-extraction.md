# TDD-SERVICE-LAYER-001 v2.0: Service Layer Completion

**TDD ID**: TDD-SERVICE-LAYER-001
**Version**: 2.0
**Original Date**: 2026-02-04
**Revision Date**: 2026-02-15
**Author**: Architect
**Status**: APPROVED (revised from v1.0 DRAFT)
**PRD Reference**: Architectural Opportunities Initiative, B5 (Wave 3)
**Dependency**: B1 EntityRegistry (TDD-ENTITY-REGISTRY-001, Sprint 2 -- delivered)

---

## Revision Summary

v2.0 is a focused rewrite. The original TDD described a monolithic extraction across four phases. Phases 1-2 shipped during the I5 route decomposition (Feb 5-8, 2026). This revision:

1. **Attests Phase 1-2 as COMPLETE** with file:line evidence. No design content is repeated for completed work.
2. **Adds query_v2.py to Phase 3 scope.** This 294-line file was created after the original TDD and duplicates the exact inline entity resolution pattern the TDD eliminates. It has three endpoints worth of boilerplate entity validation (lines 68-117 and 187-236) that should delegate to EntityServiceDep.
3. **Scopes resolver.py OUT** with explicit rationale. It serves a different domain (entity resolution, not query/CRUD) and its extraction belongs to a future initiative.
4. **Provides detailed Phase 4 design** addressing the two divergent DataFrame build paths (DataFrameViewPlugin vs SectionDataFrameBuilder), the SectionProxy hack, and the module-level schema cache.
5. **Drops protocols.py from scope** (ADR-SLE-001 addendum). Four services shipped as concrete classes. Retrofitting Protocols for two more would create inconsistency without value.
6. **Reconciles FieldWriteService's invalidator pattern** with ADR-SLE-002 (accepted variance).
7. **Updates all stale references**: line counts, file paths, attestation table.

---

## Current State (Phase 1-2 Attestation)

Phases 1 and 2 are **COMPLETE**. The service layer foundation is fully operational with 113 unit tests across 4 test modules.

### Phase 1: Foundation -- COMPLETE

| Artifact | Path | LOC | Evidence |
|----------|------|-----|----------|
| Service errors | `services/errors.py` | 343 | 13 exception classes, `get_status_for_error()` MRO walker, `SERVICE_ERROR_MAP` (exceeds v1.0 spec of 6 classes) |
| EntityContext | `services/entity_context.py` | 41 | Frozen dataclass with `entity_type`, `project_gid`, `descriptor`, `bot_pat` |
| EntityService | `services/entity_service.py` | 148 | Constructor injection of `EntityRegistry` + `EntityProjectRegistry`. `validate_entity_type()` returns `EntityContext`. `get_queryable_entities()` delegates to `get_resolvable_entities()` |
| DI wiring | `api/dependencies.py:466-546` | +80 | `get_entity_service()` singleton on `app.state`, `get_task_service()`, `get_section_service()`. Type aliases: `EntityServiceDep`, `TaskServiceDep`, `SectionServiceDep` |

### Phase 2: TaskService + SectionService -- COMPLETE

| Artifact | Path | LOC | Tests | Test Count |
|----------|------|-----|-------|------------|
| TaskService | `services/task_service.py` | 634 | `test_task_service.py` (516 LOC) | 25 |
| SectionService | `services/section_service.py` | 274 | `test_section_service.py` (311 LOC) | 16 |
| EntityService | `services/entity_service.py` | 148 | `test_entity_service.py` (246 LOC) | 10 |
| Service errors | `services/errors.py` | 343 | `test_service_errors.py` (365 LOC) | 62 |

### Route Delegation Status

| Route File | Current LOC | Thin Adapter? | SC-1 (<30 lines/endpoint) |
|------------|-------------|---------------|---------------------------|
| `routes/tasks.py` | 578 (16 endpoints) | YES | YES -- longest is `list_tasks()` at 20 lines |
| `routes/sections.py` | 224 (6 endpoints) | YES | YES -- longest is `reorder_section()` at 12 lines |
| `routes/query.py` | 372 (2 endpoints) | PARTIAL | NO -- `query_rows` is ~80 lines with inline orchestration |
| `routes/query_v2.py` | 294 (2 endpoints) | NO | NO -- inline entity validation duplicated across both endpoints |
| `routes/dataframes.py` | 556 (2 endpoints) | NO | NO -- endpoints are ~180 lines each |

### Success Criteria Already Met

| ID | Criterion | Status |
|----|-----------|--------|
| SC-2 | Zero `HTTPException` in services/ | MET. `grep -r "HTTPException" services/` returns 0 hits |
| SC-5 | Services usable without FastAPI | MET. All test files instantiate services with plain constructors |
| SC-6 | EntityService uses B1 EntityRegistry | MET. `entity_service.py:91` calls `self._entity_registry.require()` |
| SC-7 | MutationEvent construction consolidated | MET. `grep -r "MutationEvent(" api/routes/` returns 0 hits |

---

## Remaining Work

### Phase 3: QueryService DI Wiring + query_v2.py Alignment

**Goal**: Eliminate inline entity resolution from `query_v2.py` and complete DI wiring for `query.py`.

**Scope**: 3 files modified, 1 file augmented (dependencies.py).

#### 3.1 query_v2.py: Replace Inline Entity Resolution with EntityServiceDep

`query_v2.py` contains the inline entity resolution pattern at two locations:

1. **`query_rows()` lines 68-117** (50 lines): `get_resolvable_entities()` check, `EntityProjectRegistry` from `app.state`, `get_bot_pat()`, manual section index construction.
2. **`query_aggregate()` lines 187-236** (50 lines): Exact copy of the same pattern.

Both endpoints should receive `EntityServiceDep` and replace the 50-line inline block with:

```python
try:
    ctx = entity_service.validate_entity_type(entity_type)
except ServiceError as e:
    raise HTTPException(status_code=get_status_for_error(e), detail=e.to_dict())
```

**Section index construction** (lines 119-131, 238-249) uses `SectionIndex.from_manifest_async()` with a manifest-first, enum-fallback pattern that differs from `query.py`'s simpler enum-only fallback. This logic should move to `resolve_section_index()` on `query_service.py` as a module-level function (consistent with existing `validate_fields()` and `resolve_section()` pattern):

```python
async def resolve_section_index(
    section_name: str | None,
    entity_type: str,
    project_gid: str,
) -> SectionIndex | None:
    """Build section index with manifest-first, enum-fallback strategy.

    Returns None if section_name is None.
    """
    if section_name is None:
        return None

    from autom8_asana.dataframes.section_persistence import create_section_persistence
    from autom8_asana.metrics.resolve import SectionIndex

    persistence = create_section_persistence()
    section_index = await SectionIndex.from_manifest_async(persistence, project_gid)
    if section_index.resolve(section_name) is None:
        section_index = SectionIndex.from_enum_fallback(entity_type)
    return section_index
```

**entity_project_registry parameter**: `query_v2.py` line 143 passes `entity_project_registry=registry` to `engine.execute_rows()`. After migration, this should use `request.app.state.entity_project_registry` accessed via a lightweight dependency or passed from `EntityServiceDep` (EntityService already holds `_project_registry`). Add a property to EntityService:

```python
@property
def project_registry(self) -> EntityProjectRegistry:
    """Expose project registry for callers that need it directly."""
    return self._project_registry
```

#### 3.2 query.py: Remove Inline _get_query_service() and Complete DI

`query.py` line 112 creates `EntityQueryService` inline via `_get_query_service()`. This conflicts with the DI pattern already in use for `EntityServiceDep`. The fix:

1. Remove `_get_query_service()` (line 112-114).
2. The `EntityQueryService` instantiation at line 178 becomes `EntityQueryService()` directly in the handler. This is acceptable because `EntityQueryService` is stateless-per-request (dataclass with `_last_freshness_info` state). Creating it inline is equivalent to DI -- the class has no constructor dependencies that need injection.

**Decision**: Do NOT create `QueryServiceDep` or a DI factory for `EntityQueryService`. The service has no constructor dependencies that benefit from injection. The current `EntityQueryService()` call is self-contained. Adding DI would add complexity without value. The module-level functions `validate_fields()` and `resolve_section()` remain as imports.

**Rationale**: TaskService and SectionService benefit from DI because they receive `MutationInvalidator` (a request-scoped, app-state-dependent object). `EntityQueryService` takes an optional `strategy_factory` with a sensible default. There is no hidden dependency to inject.

#### 3.3 Move _has_section_pred and Section Stripping to query_service.py

The `_has_section_pred()` helper (query.py lines 117-129) and the section predicate stripping logic (lines 310-322) are business logic that belongs in the service layer. Add to `query_service.py`:

```python
def strip_section_conflicts(
    request_body: RowsRequest,
    section_name: str | None,
) -> RowsRequest:
    """Strip section predicates if section parameter conflicts.

    Per EC-006: When both ?section param and predicate tree contain
    section comparisons, the param wins and predicates are stripped.

    Returns the request unmodified if no conflict exists.
    """
    if section_name is None or request_body.where is None:
        return request_body
    if not _has_section_pred(request_body.where):
        return request_body

    stripped = strip_section_predicates(request_body.where)
    return request_body.model_copy(update={"where": stripped})
```

#### 3.4 Phase 3 Task List

| Task | File | Description |
|------|------|-------------|
| 3.1 | `services/query_service.py` | Add `resolve_section_index()` and `strip_section_conflicts()` module functions |
| 3.2 | `services/entity_service.py` | Add `project_registry` property |
| 3.3 | `api/routes/query_v2.py` | Replace inline entity resolution with `EntityServiceDep`, replace inline section index with `resolve_section_index()` |
| 3.4 | `api/routes/query.py` | Remove `_get_query_service()`, remove `_has_section_pred()`, use `strip_section_conflicts()` |
| 3.5 | `api/dependencies.py` | No changes needed -- EntityServiceDep already exists |
| 3.6 | Tests | Add/update `test_query_service.py` for new functions. Update `test_routes_query_rows.py` and `test_routes_query_aggregate.py` for EntityServiceDep |

**Acceptance**: All existing query API tests pass. `query_v2.py` has zero `get_resolvable_entities()` calls. `query.py` has zero `_get_query_service()` or `_has_section_pred()`.

---

### Phase 4: DataFrameService Extraction

**Goal**: Extract business logic from `dataframes.py` into `DataFrameService`. Route becomes a thin adapter handling only HTTP concerns (content negotiation, response formatting).

**Scope**: 1 new file, 2 modified files, 1 new test file.

#### 4.1 Design Analysis: Two Build Paths

The current `dataframes.py` has two fundamentally different build paths:

**Project path** (`get_project_dataframe`, lines 196-350):
1. Fetches tasks via `client._http.get_paginated("/tasks", params)` with pagination
2. Creates `InMemoryCacheProvider()` + `UnifiedTaskStore` per-request
3. Creates `DataFrameViewPlugin(schema, store, resolver)`
4. Calls `view_plugin._extract_rows_async(data, project_gid=gid)` (async, returns list of dicts)
5. Constructs `pl.DataFrame` from rows

**Section path** (`get_section_dataframe`, lines 383-553):
1. Fetches section metadata via `client._http.get("/sections/{gid}", ...)` for parent project GID
2. Fetches tasks via `client._http.get_paginated("/tasks", params)` with pagination
3. Converts raw data to `Task` model instances
4. Creates `SectionProxy` inline class as adapter
5. Creates `SectionDataFrameBuilder(section=proxy, task_type="*", schema, resolver)`
6. Calls `builder.build(tasks=tasks)` (sync, returns `pl.DataFrame` directly)

**Key difference**: The project path uses async extraction via `DataFrameViewPlugin._extract_rows_async()` returning raw dicts, while the section path uses sync extraction via `SectionDataFrameBuilder.build()` returning a DataFrame directly. The project path needs `UnifiedTaskStore`; the section path does not.

#### 4.2 DataFrameService Design

The service abstracts over both paths by providing two methods with a common return type. It does NOT attempt to unify the internal build paths -- they serve different purposes and forcing them into a single abstraction would be artificial.

**Location**: `src/autom8_asana/services/dataframe_service.py`

```python
"""DataFrame build service.

Extracts schema resolution, opt_fields management, and DataFrame
construction from route handlers into a testable service.

Per TDD-SERVICE-LAYER-001 v2.0 Phase 4.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

import polars as pl
from autom8y_log import get_logger

from autom8_asana.dataframes.models.registry import SchemaRegistry
from autom8_asana.dataframes.models.schema import DataFrameSchema
from autom8_asana.services.errors import InvalidParameterError

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

logger = get_logger(__name__)


class InvalidSchemaError(InvalidParameterError):
    """Schema name not found in SchemaRegistry."""

    def __init__(self, schema_name: str, valid_schemas: list[str]) -> None:
        self.schema_name = schema_name
        self.valid_schemas = valid_schemas
        super().__init__(
            f"Unknown schema '{schema_name}'. "
            f"Valid schemas: {', '.join(valid_schemas)}"
        )

    @property
    def error_code(self) -> str:
        return "INVALID_SCHEMA"

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.error_code,
            "message": self.message,
            "valid_schemas": self.valid_schemas,
        }


@dataclass(frozen=True)
class DataFrameResult:
    """Result of DataFrame build operation."""
    dataframe: pl.DataFrame
    has_more: bool
    next_offset: str | None


class DataFrameService:
    """DataFrame build operations.

    Extracts schema resolution, opt_fields construction, and DataFrame
    assembly from route handlers. Handles both project-scoped and
    section-scoped builds via separate methods.

    Thread Safety: Stateless. Safe for concurrent use.
    """

    # Standard opt_fields for task fetch (was duplicated in both endpoints).
    TASK_OPT_FIELDS: ClassVar[list[str]] = [
        "gid",
        "name",
        "resource_type",
        "completed",
        "completed_at",
        "created_at",
        "modified_at",
        "notes",
        "assignee",
        "assignee.name",
        "due_on",
        "due_at",
        "start_on",
        "memberships.section.name",
        "memberships.project.gid",
        "custom_fields",
        "custom_fields.gid",
        "custom_fields.name",
        "custom_fields.resource_subtype",
        "custom_fields.display_value",
        "custom_fields.enum_value",
        "custom_fields.enum_value.name",
        "custom_fields.multi_enum_values",
        "custom_fields.multi_enum_values.name",
        "custom_fields.number_value",
        "custom_fields.text_value",
    ]

    def get_schema(self, schema_name: str) -> DataFrameSchema:
        """Resolve schema name to DataFrameSchema.

        Handles normalization, wildcard blocking, and fallback to base.

        Args:
            schema_name: Schema name from API request (case-insensitive).

        Returns:
            DataFrameSchema from registry.

        Raises:
            InvalidSchemaError: Schema name not found.
        """
        mapping, valid_schemas = self._get_schema_mapping()

        if not schema_name or not schema_name.strip():
            return SchemaRegistry.get_instance().get_schema("*")

        normalized = schema_name.lower().strip()

        if normalized == "*":
            raise InvalidSchemaError("*", valid_schemas)

        task_type = mapping.get(normalized)
        if task_type is None:
            raise InvalidSchemaError(schema_name, valid_schemas)

        return SchemaRegistry.get_instance().get_schema(task_type)

    async def build_project_dataframe(
        self,
        client: AsanaClient,
        project_gid: str,
        schema: DataFrameSchema,
        limit: int,
        offset: str | None,
    ) -> DataFrameResult:
        """Build DataFrame for project tasks.

        Uses DataFrameViewPlugin._extract_rows_async() for async
        extraction with UnifiedTaskStore backing.

        Args:
            client: AsanaClient for API calls.
            project_gid: Asana project GID.
            schema: Resolved DataFrameSchema.
            limit: Page size.
            offset: Pagination cursor.

        Returns:
            DataFrameResult with DataFrame and pagination info.
        """
        from autom8_asana._defaults.cache import InMemoryCacheProvider
        from autom8_asana.cache.providers.unified import UnifiedTaskStore
        from autom8_asana.dataframes import DefaultCustomFieldResolver
        from autom8_asana.dataframes.views.dataframe_view import (
            DataFrameViewPlugin,
        )

        params: dict[str, Any] = {
            "project": project_gid,
            "limit": limit,
            "opt_fields": ",".join(self.TASK_OPT_FIELDS),
        }
        if offset:
            params["offset"] = offset

        data, next_offset = await client._http.get_paginated(
            "/tasks", params=params
        )

        resolver = DefaultCustomFieldResolver()
        unified_store = UnifiedTaskStore(cache=InMemoryCacheProvider())
        view_plugin = DataFrameViewPlugin(
            schema=schema,
            store=unified_store,
            resolver=resolver,
        )

        rows = await view_plugin._extract_rows_async(
            data, project_gid=project_gid
        )
        if rows:
            df = pl.DataFrame(rows, schema=schema.to_polars_schema())
        else:
            df = pl.DataFrame(schema=schema.to_polars_schema())

        return DataFrameResult(
            dataframe=df,
            has_more=next_offset is not None,
            next_offset=next_offset,
        )

    async def build_section_dataframe(
        self,
        client: AsanaClient,
        section_gid: str,
        schema: DataFrameSchema,
        limit: int,
        offset: str | None,
    ) -> tuple[DataFrameResult, str]:
        """Build DataFrame for section tasks.

        Uses SectionDataFrameBuilder.build() for synchronous extraction
        with Task model conversion.

        Args:
            client: AsanaClient for API calls.
            section_gid: Asana section GID.
            schema: Resolved DataFrameSchema.
            limit: Page size.
            offset: Pagination cursor.

        Returns:
            Tuple of (DataFrameResult, project_gid). The project_gid
            is returned because it is resolved during the section
            fetch and the route may need it for response metadata.

        Raises:
            EntityNotFoundError: Section not found or has no parent project.
        """
        from autom8_asana.dataframes import (
            DefaultCustomFieldResolver,
            SectionDataFrameBuilder,
        )
        from autom8_asana.models.task import Task
        from autom8_asana.services.errors import EntityNotFoundError

        # Fetch section to get parent project GID
        section_data = await client._http.get(
            f"/sections/{section_gid}",
            params={"opt_fields": "project.gid"},
        )
        project_gid = section_data.get("project", {}).get("gid")

        if not project_gid:
            raise EntityNotFoundError(
                "Section not found or has no parent project"
            )

        # Fetch section tasks
        params: dict[str, Any] = {
            "section": section_gid,
            "limit": limit,
            "opt_fields": ",".join(self.TASK_OPT_FIELDS),
        }
        if offset:
            params["offset"] = offset

        data, next_offset = await client._http.get_paginated(
            "/tasks", params=params
        )

        # Convert to Task models for SectionDataFrameBuilder
        tasks = [Task.model_validate(t) for t in data]

        resolver = DefaultCustomFieldResolver()

        # SectionDataFrameBuilder expects a section-like object
        # with .gid, .project, and .tasks attributes.
        section_proxy = _SectionProxy(section_gid, project_gid, tasks)

        builder = SectionDataFrameBuilder(
            section=section_proxy,
            task_type="*",
            schema=schema,
            resolver=resolver,
        )
        df = builder.build(tasks=tasks)

        return (
            DataFrameResult(
                dataframe=df,
                has_more=next_offset is not None,
                next_offset=next_offset,
            ),
            project_gid,
        )

    @staticmethod
    def _get_schema_mapping() -> tuple[dict[str, str], list[str]]:
        """Get schema name -> task_type mapping.

        Uses module-level cache for thread-safe lazy initialization.
        See Decision #4 for rationale on keeping module-level cache.
        """
        return _get_schema_mapping_cached()


class _SectionProxy:
    """Adapter for SectionDataFrameBuilder's section interface.

    SectionDataFrameBuilder expects a section object with .gid,
    .project (dict with 'gid'), and .tasks attributes. This provides
    that interface from primitive values.

    This replaces the inline class definition that was in dataframes.py.
    """

    __slots__ = ("gid", "project", "tasks")

    def __init__(
        self, gid: str, project_gid: str, tasks: list[Any]
    ) -> None:
        self.gid = gid
        self.project = {"gid": project_gid}
        self.tasks = tasks


# Module-level cached schema mapping (thread-safe via CPython GIL).
# See Decision #4 for rationale on keeping this at module level.
_schema_mapping_cache: dict[str, str] | None = None
_valid_schemas_cache: list[str] | None = None


def _get_schema_mapping_cached() -> tuple[dict[str, str], list[str]]:
    """Get cached schema mapping, building it if necessary.

    Thread-safe: SchemaRegistry._ensure_initialized() uses locking.
    The global assignment is atomic in CPython.
    """
    global _schema_mapping_cache, _valid_schemas_cache

    if _schema_mapping_cache is None:
        registry = SchemaRegistry.get_instance()
        mapping = {"base": "*"}
        for task_type in registry.list_task_types():
            schema = registry.get_schema(task_type)
            mapping[schema.name] = task_type

        _schema_mapping_cache = mapping
        _valid_schemas_cache = sorted(mapping.keys())

    assert _valid_schemas_cache is not None
    return _schema_mapping_cache, _valid_schemas_cache
```

#### 4.3 DataFrameService DI Wiring

Add to `api/dependencies.py`:

```python
def get_dataframe_service() -> DataFrameService:
    """Get DataFrameService instance.

    Stateless, cheap to create. Per-request lifecycle.
    """
    from autom8_asana.services.dataframe_service import DataFrameService
    return DataFrameService()

# After existing type aliases:
DataFrameServiceDep = Annotated["DataFrameService", Depends(get_dataframe_service)]
```

#### 4.4 Route Refactor: dataframes.py After Extraction

After extraction, `dataframes.py` becomes a thin adapter handling only:
- Parameter parsing (schema name, limit, offset, Accept header)
- Schema resolution via `dataframe_service.get_schema()`
- Delegation to `dataframe_service.build_*_dataframe()`
- Content negotiation (`_should_use_polars_format()` stays in route -- it is an HTTP concern)
- Response formatting (Polars JSON buffer, response envelope)
- Error mapping (`InvalidSchemaError` -> `HTTPException`)

Estimated post-refactor: ~250 LOC (from 556), with ~180 lines being response formatting, OpenAPI decorators, and parameter declarations.

#### 4.5 SectionProxy Resolution

The inline `SectionProxy` class (dataframes.py lines 499-503) moves to `dataframe_service.py` as `_SectionProxy` (module-private). This is the pragmatic choice:

- **Option A (chosen)**: Keep the adapter as `_SectionProxy` in the service module. It is a 6-line `__slots__` class. The cost of refactoring `SectionDataFrameBuilder` to accept primitives outweighs the benefit.
- **Option B (rejected)**: Refactor `SectionDataFrameBuilder` to accept `(gid, project_gid, tasks)` instead of a section object. This would change the builder's public API and require updating all downstream callers (builders are also used by progressive builds, not just the API route). The blast radius is not justified.

#### 4.6 Phase 4 Task List

| Task | File | Description |
|------|------|-------------|
| 4.1 | `services/dataframe_service.py` | Create DataFrameService with `get_schema()`, `build_project_dataframe()`, `build_section_dataframe()`, `InvalidSchemaError`, `DataFrameResult`, `_SectionProxy` |
| 4.2 | `services/errors.py` | Add `InvalidSchemaError` to `SERVICE_ERROR_MAP` (maps to 400) |
| 4.3 | `api/dependencies.py` | Add `get_dataframe_service()` factory and `DataFrameServiceDep` alias |
| 4.4 | `api/routes/dataframes.py` | Refactor to delegate to `DataFrameServiceDep`. Remove `_get_schema_mapping()`, `_get_schema()`, duplicated `opt_fields`, `SectionProxy` class, module-level cache variables |
| 4.5 | `tests/unit/services/test_dataframe_service.py` | Unit tests for schema resolution, project build, section build, error cases |
| 4.6 | Regression | Run `tests/api/test_routes_dataframes.py` (1020 LOC) to verify no behavior change |

**Acceptance**: `dataframes.py` has zero `HTTPException` raises for schema errors (uses `InvalidSchemaError`). Opt_fields list exists in exactly one place (`DataFrameService.TASK_OPT_FIELDS`). No inline `class SectionProxy` in route file.

---

## Decision Log (Answers to 7 Critical Questions)

### Decision 1: Should query_v2.py use EntityServiceDep?

**YES.** query_v2.py duplicates the exact 50-line entity resolution pattern that EntityService exists to eliminate. The duplication appears twice (lines 68-117 for `/rows`, lines 187-236 for `/aggregate`), making it 100 lines of boilerplate. The likely reason it was not wired during initial implementation is that query_v2.py was created after the EntityService was built but before the wiring pattern was established in query.py. This is an oversight, not a deliberate decision.

Phase 3 includes this work.

### Decision 2: Drop Protocol pattern or retrofit?

**DROP.** ADR-SLE-001 is superseded. The four shipped services (EntityService, TaskService, SectionService, EntityQueryService) all operate as concrete classes. No consumer imports or type-checks against a Protocol. Tests mock concrete classes directly. Retrofitting Protocols for only DataFrameService would create an inconsistency worse than having no Protocols at all.

**ADR-SLE-001 Addendum**: Status changed from ACCEPTED to SUPERSEDED. The Protocol pattern was evaluated during Phase 1 implementation and found to add type-annotation overhead without practical benefit in a codebase that does not run `mypy --strict`. Concrete classes with constructor injection provide sufficient testability. If `mypy --strict` is adopted in the future, Protocols can be added to all services in a single pass.

### Decision 3: How to handle 2 divergent DataFrame build paths?

**Keep them separate.** `DataFrameService.build_project_dataframe()` uses `DataFrameViewPlugin._extract_rows_async()` (async, dict-based). `DataFrameService.build_section_dataframe()` uses `SectionDataFrameBuilder.build()` (sync, Task-model-based). Both return `DataFrameResult` -- the common return type is the abstraction boundary.

Forcing these into a single method with a `scope: Literal["project", "section"]` parameter would create a false abstraction. The paths have different input types (`project_gid` vs `section_gid`), different intermediate representations (raw dicts vs Task models), different lifecycle requirements (`UnifiedTaskStore` vs none), and different sync/async behaviors. The route already knows which path to call based on the URL.

### Decision 4: Module-level schema cache -- move to service or keep singleton?

**Keep module-level singleton, accessed via service method.** The cache (`_schema_mapping`, `_valid_schemas`) has the following properties:

1. **Immutable after first write**: SchemaRegistry contents do not change after initialization.
2. **Thread-safe via CPython GIL**: The single global assignment is atomic.
3. **Process-lifetime validity**: Schema registration happens at import time.

Moving this into the service instance would mean either (a) the service must be a singleton (contradicting per-request lifecycle), or (b) every request rebuilds the mapping (wasteful). The module-level cache accessed via `DataFrameService._get_schema_mapping()` (which delegates to the module function) preserves the correct semantics while providing a testable API surface.

For testing, the module-level cache can be reset by setting `_schema_mapping_cache = None` in test fixtures, exactly as the current `_schema_mapping = None` pattern works.

### Decision 5: Should resolver.py (456 lines) be in scope?

**NO.** `resolver.py` serves the entity resolution domain (POST `/v1/resolve/{entity_type}`), not the query/CRUD domain. It uses `get_resolvable_entities()` and `EntityProjectRegistry` from `app.state` -- the same inline pattern as query_v2.py -- but its business logic is fundamentally different (resolution strategies, criteria validation, field filtering).

Extracting resolver.py into an `EntityResolverService` is a separate initiative. The inline entity validation in resolver.py (lines 218-237, 240-279) duplicates the EntityService pattern and should eventually be replaced with `EntityServiceDep`, but this is lower priority because:

1. resolver.py has a richer validation flow (strategy lookup, criteria validation, field validation against schema) that does not cleanly map to `validate_entity_type()` alone.
2. The endpoint has its own test suite and is actively evolving (Entity Resolution Hardening initiative).
3. Mixing resolver.py into I2 would expand the blast radius beyond the query/CRUD/DataFrame scope.

**Deferred to**: Future initiative (INIT-ER-002 or a service-layer sweep).

### Decision 6: Reconcile FieldWriteService invalidator pattern with ADR-SLE-002?

**Accept as documented variance.** ADR-SLE-002 mandates constructor injection for service dependencies. FieldWriteService receives `client` and `write_registry` via constructor but `mutation_invalidator` via method parameter (`write_async(... mutation_invalidator=None)`).

This is intentional, not a violation:

1. `FieldWriteService` is constructed per-request with a pre-validated `AsanaClient` and `EntityWriteRegistry`. These are true dependencies.
2. `mutation_invalidator` is optional (None disables invalidation) and is a cross-cutting concern. The caller (entity_write route) decides whether to pass it based on app.state availability.
3. The pattern matches the TDD's own guidance (ADR-SLE-002 note): "Method parameter injection (passing `client` per-call) is appropriate for per-request resources."

**ADR-SLE-002 Addendum**: Constructor injection is the default for service dependencies. Optional cross-cutting concerns (invalidation, telemetry) MAY be passed per-call when their availability depends on runtime state and their absence should not prevent service construction.

### Decision 7: How does inline _get_query_service() interact with DI QueryServiceDep?

**Remove _get_query_service(); do NOT create QueryServiceDep.** The interaction is unnecessary.

`query.py` line 112 defines `_get_query_service() -> EntityQueryService` which returns `EntityQueryService()` with no arguments. Line 178 calls it: `query_service = _get_query_service()`. This is a zero-dependency factory.

`EntityQueryService` is a `@dataclass` with an optional `strategy_factory` that defaults to `get_universal_strategy`. It has no constructor dependencies that benefit from DI injection. Creating a `QueryServiceDep` would add infrastructure (factory function, type alias, Depends chain) for a class that is self-sufficient.

**Action**: Delete `_get_query_service()`. Replace `query_service = _get_query_service()` with `query_service = EntityQueryService()` directly. This is explicit, readable, and does not pretend there is a dependency graph to manage.

---

## ADRs

### ADR-SLE-001 (Revised): Protocols Superseded by Concrete Classes

**Status**: SUPERSEDED (was ACCEPTED in v1.0)

**Context**: v1.0 mandated `typing.Protocol` for all service interfaces. During Phase 1-2 implementation, Protocols were not created. Four services shipped as concrete classes with constructor injection.

**Decision**: Drop the Protocol requirement. Services are concrete classes. No `services/protocols.py` will be created.

**Rationale**: Protocols add value when (a) multiple implementations exist, (b) `mypy --strict` enforces structural typing, or (c) services are consumed across package boundaries. None apply here. All services have exactly one implementation. `mypy --strict` is not in use. Services are consumed within the same package.

**Consequences**: Positive: less boilerplate, simpler import graph. Negative: no compile-time interface checking. Mitigation: comprehensive service unit tests (113 tests) serve as the de facto contract.

### ADR-SLE-002 (Amended): Constructor Injection with Per-Call Variance

**Status**: ACCEPTED (amended from v1.0)

**Original Decision**: Constructor injection for all service dependencies.

**Amendment**: Optional cross-cutting concerns (e.g., `mutation_invalidator`) MAY be passed as method parameters when their availability depends on runtime state. This is not a violation but a documented variance for concerns that are truly optional.

**Evidence**: `FieldWriteService.write_async(mutation_invalidator=None)` -- invalidation is optional. `TaskService.__init__(invalidator=...)` -- invalidation is required for task CRUD. The distinction is whether the concern is integral (constructor) or supplementary (method).

### ADR-SLE-003: Service Errors as Domain Exceptions (Unchanged)

**Status**: ACCEPTED (no changes from v1.0)

Services raise `ServiceError` subclasses. Routes catch and map to `HTTPException` via `get_status_for_error()`. This remains the governing pattern.

---

## Migration Plan

### Phase 3: QueryService DI Wiring + query_v2.py Alignment (1 Sprint)

#### Commit 1: Extract section index + section conflict helpers to query_service.py

```
Modified: services/query_service.py
  - Add resolve_section_index() module function
  - Add strip_section_conflicts() module function
  - Move _has_section_pred() from query.py (renamed, module-private)

Modified: services/entity_service.py
  - Add project_registry property

New/Modified: tests/unit/services/test_query_service.py
  - Tests for resolve_section_index() (manifest-first, enum-fallback, None case)
  - Tests for strip_section_conflicts() (no conflict, conflict strips, no section)
```

**Verify**: `.venv/bin/pytest tests/unit/services/test_query_service.py -x -q`

#### Commit 2: Wire query_v2.py to EntityServiceDep

```
Modified: api/routes/query_v2.py
  - Add EntityServiceDep parameter to query_rows() and query_aggregate()
  - Replace inline entity resolution (lines 68-117, 187-236) with:
    ctx = entity_service.validate_entity_type(entity_type)
  - Replace inline section index construction with resolve_section_index()
  - Use entity_service.project_registry for engine.execute_rows() parameter
  - Remove imports: get_resolvable_entities, EntityProjectRegistry
  - Add imports: EntityServiceDep, ServiceError, get_status_for_error, resolve_section_index
```

**Verify**: `.venv/bin/pytest tests/api/test_routes_query_rows.py tests/api/test_routes_query_aggregate.py -x -q`

#### Commit 3: Clean up query.py inline factories

```
Modified: api/routes/query.py
  - Remove _get_query_service() (line 112-114)
  - Remove _has_section_pred() (lines 117-129)
  - Replace query_service = _get_query_service() with EntityQueryService() direct
  - Replace inline section stripping (lines 310-322) with strip_section_conflicts()
  - Import strip_section_conflicts from services.query_service
```

**Verify**: `.venv/bin/pytest tests/api/test_routes_query.py -x -q`

#### Commit 4: Full regression

**Verify**: `.venv/bin/pytest tests/ -x -q --timeout=60`

### Phase 4: DataFrameService Extraction (1 Sprint)

#### Commit 1: Create DataFrameService and InvalidSchemaError

```
New: services/dataframe_service.py
  - DataFrameService class
  - InvalidSchemaError exception class
  - DataFrameResult dataclass
  - _SectionProxy adapter class
  - Module-level schema mapping cache

Modified: services/errors.py
  - Import and add InvalidSchemaError to SERVICE_ERROR_MAP (400)

Modified: api/dependencies.py
  - Add get_dataframe_service() factory
  - Add DataFrameServiceDep type alias

New: tests/unit/services/test_dataframe_service.py
  - Schema resolution: valid schema, invalid schema, wildcard rejection, empty input
  - Build project: happy path, empty results, pagination
  - Build section: happy path, missing project GID, pagination
  - TASK_OPT_FIELDS: verify deduplicated (single source)
```

**Verify**: `.venv/bin/pytest tests/unit/services/test_dataframe_service.py -x -q`

#### Commit 2: Refactor dataframes.py to use DataFrameServiceDep

```
Modified: api/routes/dataframes.py
  - Add DataFrameServiceDep parameter to both endpoints
  - Replace _get_schema_mapping(), _get_schema() with dataframe_service.get_schema()
  - Replace inline opt_fields lists with removal (service handles internally)
  - Replace inline DataFrame build logic with dataframe_service.build_*_dataframe()
  - Replace inline SectionProxy with removal (service handles internally)
  - Replace inline HTTPException for schema errors with InvalidSchemaError mapping
  - Remove module-level _schema_mapping, _valid_schemas variables
  - Keep _should_use_polars_format() and content negotiation in route
  - Keep PaginationMeta construction and response envelope in route
```

**Verify**: `.venv/bin/pytest tests/api/test_routes_dataframes.py -x -q`

#### Commit 3: Full regression

**Verify**: `.venv/bin/pytest tests/ -x -q --timeout=60`

---

## Updated Success Criteria

| ID | Criterion | Measurement | Status |
|----|-----------|-------------|--------|
| SC-1 | All route handlers <= 30 lines (excluding decorators/docstrings) | Line count audit | PARTIAL -- tasks.py and sections.py MET. query.py, query_v2.py, dataframes.py NOT MET (targeted by Phase 3-4) |
| SC-2 | Zero `HTTPException` raised inside any service class | `grep -r "HTTPException" services/` | MET |
| SC-3 | All existing API tests pass without modification | `.venv/bin/pytest tests/api/ -q` | MET for Phase 1-2 routes. Phase 3-4 will be verified per-commit |
| SC-4 | Service tests achieve 100% branch coverage on extracted logic | `.venv/bin/pytest --cov=services/` | PARTIAL -- 113 tests exist. Phase 3-4 add coverage for new functions |
| SC-5 | Services usable without FastAPI | Standalone test: import, call, no HTTP | MET |
| SC-6 | EntityService uses B1 EntityRegistry | Code review: `entity_service.py:91` calls `self._entity_registry.require()` | MET |
| SC-7 | MutationEvent construction consolidated | `grep -r "MutationEvent(" api/routes/` returns 0 | MET |
| SC-8 | p99 latency regression < 1ms | Before/after benchmark on query endpoint | NOT MEASURED -- to be verified during Phase 3 |
| SC-9 | query_v2.py uses EntityServiceDep (NEW) | `grep "EntityServiceDep" query_v2.py` returns hits | NOT MET -- targeted by Phase 3 |
| SC-10 | opt_fields defined in exactly one location (NEW) | `grep -r "opt_fields = \[" api/routes/dataframes.py` returns 0 | NOT MET -- targeted by Phase 4 |
| SC-11 | Zero inline SectionProxy in route files (NEW) | `grep -r "class SectionProxy" api/routes/` returns 0 | NOT MET -- targeted by Phase 4 |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| query_v2.py EntityServiceDep breaks section index behavior | Medium | Medium | query_v2.py uses manifest-first section index; new `resolve_section_index()` preserves this. Test with section-parameterized queries |
| DataFrameService changes UnifiedTaskStore lifecycle | Low | High | Per-request `InMemoryCacheProvider()` creation is preserved exactly as-is in service method. No lifecycle change |
| Module-level schema cache reset in tests causes flaky tests | Low | Low | Existing pattern (`_schema_mapping = None` in conftest) works identically with renamed cache variable |
| query_v2.py test mocks depend on `get_resolvable_entities` import path | Medium | Low | Update test mocks to patch `EntityServiceDep` instead. Standard FastAPI DI override pattern |
| Performance regression from additional service-layer indirection | Low | Low | Single function call overhead. No new I/O. SC-8 gates deployment |

---

## Updated Attestation Table

| Artifact | Absolute Path | Status | LOC |
|----------|--------------|--------|-----|
| TDD (this document) | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-service-layer-extraction.md` | v2.0 | - |
| EntityService | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/entity_service.py` | COMPLETE | 148 |
| EntityContext | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/entity_context.py` | COMPLETE | 41 |
| TaskService | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/task_service.py` | COMPLETE | 634 |
| SectionService | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/section_service.py` | COMPLETE | 274 |
| Service errors | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | COMPLETE (Phase 4 adds InvalidSchemaError) | 343 |
| QueryService | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py` | PARTIAL (Phase 3 adds helpers) | 512 |
| DataFrameService | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/dataframe_service.py` | NOT STARTED (Phase 4) | 0 |
| DI wiring | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/dependencies.py` | COMPLETE (Phase 4 adds DataFrameServiceDep) | 574 |
| Route: query.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/query.py` | PARTIAL (Phase 3 cleanup) | 372 |
| Route: query_v2.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/query_v2.py` | NOT STARTED (Phase 3 target) | 294 |
| Route: dataframes.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/dataframes.py` | NOT STARTED (Phase 4 target) | 556 |
| Route: tasks.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/tasks.py` | COMPLETE (thin adapter) | 578 |
| Route: sections.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/sections.py` | COMPLETE (thin adapter) | 224 |
| Route: resolver.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py` | OUT OF SCOPE | 456 |
| FieldWriteService | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/field_write_service.py` | COMPLETE (accepted variance on invalidator pattern) | 361 |
| A1 MutationInvalidator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/mutation_invalidator.py` | Reference | - |
| A1 MutationEvent | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/mutation_event.py` | Reference | - |
| B1 EntityRegistry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/entity_registry.py` | Reference | - |
| Test: entity_service | `/Users/tomtenuta/Code/autom8_asana/tests/unit/services/test_entity_service.py` | COMPLETE | 246 |
| Test: task_service | `/Users/tomtenuta/Code/autom8_asana/tests/unit/services/test_task_service.py` | COMPLETE | 516 |
| Test: section_service | `/Users/tomtenuta/Code/autom8_asana/tests/unit/services/test_section_service.py` | COMPLETE | 311 |
| Test: service_errors | `/Users/tomtenuta/Code/autom8_asana/tests/unit/services/test_service_errors.py` | COMPLETE | 365 |
| Test: query_service | `/Users/tomtenuta/Code/autom8_asana/tests/unit/services/test_query_service.py` | PARTIAL (Phase 3 adds tests) | 235 |
| Test: dataframes routes | `/Users/tomtenuta/Code/autom8_asana/tests/api/test_routes_dataframes.py` | Regression gate for Phase 4 | 1020 |
| Steel-man analysis | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/I2-steelman-analysis.md` | Input to v2.0 | - |
| Straw-man analysis | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/I2-strawman-analysis.md` | Input to v2.0 | - |

---

## Non-Functional Considerations

### Performance

**Impact**: Negligible. Phase 3 replaces 50 lines of inline code with a single `entity_service.validate_entity_type()` call. Phase 4 adds one function call indirection per request. No new I/O operations. No additional memory allocation beyond the service object (stateless, no instance state).

**Measurement**: Before/after p99 latency comparison on query and DataFrame endpoints (SC-8: target <1ms overhead).

### Backward Compatibility

**API Contract**: Zero changes. Same URLs, same request/response shapes, same status codes, same error formats, same deprecation headers. The `to_dict()` methods on `InvalidSchemaError` produce the identical JSON structure as the current inline `HTTPException.detail` dicts.

### Observability

**Logging**: Service methods include structured log events matching current route handler patterns. Log events move from route to service but preserve `entity_type`, `request_id`, and `duration_ms` fields.

---

## Handoff Checklist

Phase 3 and Phase 4 are ready for implementation when:

- [x] TDD covers all remaining requirements (query_v2.py alignment, DataFrameService extraction)
- [x] Component boundaries and responsibilities are clear (service vs route)
- [x] Data model defined (DataFrameResult, _SectionProxy, InvalidSchemaError)
- [x] API contracts specified (no external changes)
- [x] ADRs document all significant decisions (7 decisions answered)
- [x] Risks identified with mitigations (5 risks documented)
- [x] Principal Engineer can implement without architectural questions (commit-level plan with verify commands)
- [x] All source artifacts verified via Read tool

**Estimated effort**: Phase 3 = 1 sprint. Phase 4 = 1 sprint. Total: 2 sprints to I2 completion.
