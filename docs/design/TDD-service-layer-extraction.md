# TDD: Service Layer Extraction from Route Handlers

**TDD ID**: TDD-SERVICE-LAYER-001
**Version**: 1.0
**Date**: 2026-02-04
**Author**: Architect
**Status**: DRAFT
**PRD Reference**: Architectural Opportunities Initiative, B5 (Wave 3)
**Dependency**: B1 EntityRegistry (TDD-ENTITY-REGISTRY-001, Sprint 2 -- delivered)

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Goals and Non-Goals](#goals-and-non-goals)
4. [Service Inventory](#service-inventory)
5. [Proposed Architecture](#proposed-architecture)
6. [Component Design: Service Protocols](#component-design-service-protocols)
7. [Component Design: Service Implementations](#component-design-service-implementations)
8. [Dependency Injection Pattern](#dependency-injection-pattern)
9. [EntityRegistry Integration](#entityregistry-integration)
10. [Error Handling at Service Boundary](#error-handling-at-service-boundary)
11. [Migration Plan](#migration-plan)
12. [Interface Contracts](#interface-contracts)
13. [Data Flow Diagrams](#data-flow-diagrams)
14. [Non-Functional Considerations](#non-functional-considerations)
15. [Test Strategy](#test-strategy)
16. [Risk Assessment](#risk-assessment)
17. [ADRs](#adrs)
18. [Success Criteria](#success-criteria)

---

## Overview

This TDD specifies the extraction of business logic from FastAPI route handlers in `api/routes/` into a proper service layer under `services/`. Currently, route handlers in `query.py`, `tasks.py`, `sections.py`, and `dataframes.py` contain business logic (entity validation, cache orchestration, DataFrame operations, mutation event construction) interleaved with HTTP concerns (request parsing, status codes, response formatting). This coupling makes the business logic untestable without HTTP fixtures and non-reusable from non-HTTP contexts (CLI tools, background jobs, Lambda functions).

The extraction creates four services -- `QueryService`, `TaskService`, `SectionService`, and `DataFrameService` -- that encapsulate all business logic behind protocol-defined interfaces. Route handlers become thin adapters that parse HTTP requests, call service methods, and map results/errors to HTTP responses.

### Solution Summary

| Component | Location | Purpose |
|-----------|----------|---------|
| `QueryServiceProtocol` | `services/protocols.py` | Interface for query operations |
| `TaskServiceProtocol` | `services/protocols.py` | Interface for task CRUD + invalidation |
| `SectionServiceProtocol` | `services/protocols.py` | Interface for section CRUD + invalidation |
| `DataFrameServiceProtocol` | `services/protocols.py` | Interface for DataFrame build operations |
| `QueryServiceImpl` | `services/query_service.py` | Implementation (extends existing EntityQueryService) |
| `TaskServiceImpl` | `services/task_service.py` | Task business logic extracted from routes |
| `SectionServiceImpl` | `services/section_service.py` | Section business logic extracted from routes |
| `DataFrameServiceImpl` | `services/dataframe_service.py` | DataFrame build logic extracted from routes |
| DI wiring | `api/dependencies.py` | FastAPI Depends() factories for service injection |

---

## Problem Statement

### Current State

Business logic is embedded directly in route handler functions across four modules:

| Route Module | Business Logic Embedded | Lines of Logic vs HTTP |
|-------------|------------------------|----------------------|
| `api/routes/query.py` (666 lines) | Entity validation, project registry lookup, bot PAT acquisition, section resolution, predicate stripping, QueryEngine orchestration | ~70% business, ~30% HTTP |
| `api/routes/tasks.py` (737 lines) | Parameter validation, SDK call orchestration, MutationEvent construction, project GID extraction | ~50% business, ~50% HTTP |
| `api/routes/sections.py` (289 lines) | SDK call orchestration, MutationEvent construction, project GID extraction from responses | ~45% business, ~55% HTTP |
| `api/routes/dataframes.py` (554 lines) | Schema resolution, opt_fields construction, DataFrame building, content negotiation, Polars serialization | ~65% business, ~35% HTTP |

### Specific Problems

**1. Untestable without HTTP layer**: To test that `query_entities` correctly validates entity types, you must construct a full FastAPI TestClient request. The validation logic (`_get_queryable_entities()`, `_validate_fields()`, project registry lookup) cannot be tested in isolation.

**2. Non-reusable**: The Lambda cache warmer in `api/main.py` (`_preload_dataframe_cache_progressive`) duplicates entity resolution and DataFrame building logic because it cannot call route handlers. Background jobs that need to create tasks or query entities must re-implement the business logic.

**3. Interleaved concerns**: In `query_entities()`, a single function handles: request logging, entity type validation, field validation, project registry lookup, bot PAT acquisition, query service invocation, response construction, deprecation headers, and completion logging. This makes the function difficult to reason about and modify safely.

**4. Scattered entity resolution**: Each route module independently performs entity type validation and project GID lookup against `EntityProjectRegistry`. With B1 EntityRegistry now available, these should delegate to a single `EntityService` that provides validated entity context.

**5. Duplicated mutation event construction**: Both `tasks.py` and `sections.py` construct `MutationEvent` instances with identical patterns (extract project GIDs, set entity kind, fire-and-forget). This logic belongs in a service that encapsulates the invalidation concern.

### Why Now

B1 EntityRegistry (Sprint 2) provides the foundation this extraction needs. Services can use `EntityRegistry.get()` and `EntityRegistry.require()` for entity resolution instead of the scattered `EntityProjectRegistry` / `get_resolvable_entities()` pattern currently duplicated across route handlers. Without B1, we would be extracting logic that still depends on the fragmented entity knowledge -- creating services that are marginally better than the status quo.

---

## Goals and Non-Goals

### Goals

| ID | Goal | Rationale |
|----|------|-----------|
| G1 | Extract all business logic from `query.py`, `tasks.py`, `sections.py`, `dataframes.py` into service classes | Separation of concerns |
| G2 | Service classes testable with mock dependencies, zero HTTP fixtures | Testability |
| G3 | Services use B1 EntityRegistry for entity resolution | Single source of truth |
| G4 | Route handlers become thin adapters (<30 lines per endpoint) | Readability |
| G5 | Services callable from non-HTTP contexts (Lambda, CLI, background tasks) | Reusability |
| G6 | Preserve all existing route behavior (100% backward compatible) | Safety |
| G7 | Services receive dependencies via constructor injection | Explicit dependency graph |

### Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | Changing any external API contract (URLs, request/response shapes, status codes) | Backward compatibility |
| NG2 | Duplicating MutationInvalidator logic (A1, Sprint 1) | Services call existing invalidator |
| NG3 | Introducing a message bus or event system | Premature -- fire-and-forget via asyncio.create_task suffices |
| NG4 | Extracting authentication logic from `dependencies.py` | Auth concern is already properly separated |
| NG5 | Replacing existing `EntityQueryService` | Extend and rename, preserving the working implementation |
| NG6 | Creating abstract base classes for every service | Protocols (structural typing) over ABCs per ADR-SLE-001 |

---

## Service Inventory

### Business Logic Extraction Map

This section catalogs every piece of business logic currently embedded in route handlers, and maps it to its target service.

#### From `api/routes/query.py`

| Logic Block | Current Location | Target Service | Method |
|------------|-----------------|----------------|--------|
| Entity type validation | `_get_queryable_entities()` + handler check | `EntityService` | `validate_entity_type(entity_type) -> EntityContext` |
| Field validation against schema | `_validate_fields()` | `QueryService` | `validate_fields(fields, entity_type, field_type)` |
| Project GID resolution | `entity_registry.get_project_gid()` + null checks | `EntityService` | `resolve_project_gid(entity_type) -> str` |
| Bot PAT acquisition | `get_bot_pat()` + error handling | `EntityService` | `get_bot_pat() -> str` |
| Section resolution | `_resolve_section()` | `QueryService` | `resolve_section(section_name, entity_type, project_gid)` |
| Section predicate stripping | inline in `query_rows()` | `QueryService` | `prepare_request(request_body, entity_type, project_gid)` |
| Query execution (legacy) | `query_service.query()` call | `QueryService` | `query(params) -> QueryResult` |
| Query execution (rows) | `engine.execute_rows()` call | `QueryService` | `query_rows(params) -> RowsResponse` |

#### From `api/routes/tasks.py`

| Logic Block | Current Location | Target Service | Method |
|------------|-----------------|----------------|--------|
| List parameter validation | `list_tasks()` inline | `TaskService` | `list_tasks(project, section, limit, offset)` |
| Task CRUD orchestration | `create_task()`, `update_task()`, `delete_task()` | `TaskService` | `create(params)`, `update(gid, params)`, `delete(gid)` |
| MutationEvent construction | inline in each handler | `TaskService` | Internal to service (encapsulated) |
| Project GID extraction from response | `extract_project_gids(task)` calls | `TaskService` | Internal to service |
| Subtask/dependent listing | `list_subtasks()`, `list_dependents()` | `TaskService` | `list_subtasks(gid, limit, offset)`, `list_dependents(gid, limit, offset)` |
| Tag operations | `add_tag()`, `remove_tag()` | `TaskService` | `add_tag(gid, tag_gid)`, `remove_tag(gid, tag_gid)` |
| Membership operations | `move_to_section()`, `set_assignee()`, `add_to_project()`, `remove_from_project()` | `TaskService` | Corresponding methods |

#### From `api/routes/sections.py`

| Logic Block | Current Location | Target Service | Method |
|------------|-----------------|----------------|--------|
| Section CRUD orchestration | `create_section()`, `update_section()`, `delete_section()` | `SectionService` | `create(params)`, `update(gid, params)`, `delete(gid)` |
| MutationEvent construction | inline in each handler | `SectionService` | Internal to service |
| Project GID extraction from response | inline `section.get("project")` | `SectionService` | Internal to service |
| Task-to-section operations | `add_task_to_section()` | `SectionService` | `add_task(section_gid, task_gid)` |
| Reorder validation | `reorder_section()` inline | `SectionService` | `reorder(gid, project_gid, before, after)` |

#### From `api/routes/dataframes.py`

| Logic Block | Current Location | Target Service | Method |
|------------|-----------------|----------------|--------|
| Schema resolution | `_get_schema_mapping()`, `_get_schema()` | `DataFrameService` | `get_schema(schema_name) -> DataFrameSchema` |
| opt_fields construction | hardcoded list in both endpoints | `DataFrameService` | `get_opt_fields() -> list[str]` |
| DataFrame building (project) | `get_project_dataframe()` inline | `DataFrameService` | `build_project_dataframe(gid, schema, client)` |
| DataFrame building (section) | `get_section_dataframe()` inline | `DataFrameService` | `build_section_dataframe(gid, schema, client)` |
| Content negotiation | `_should_use_polars_format()` | Route handler (HTTP concern) | Stays in route |

---

## Proposed Architecture

### Layer Diagram

```
+---------------------------------------------------------------+
|                     HTTP Layer (routes/)                        |
|  Thin adapters: parse request, call service, format response   |
+---------------------------------------------------------------+
                              |
                    Depends() injection
                              |
+---------------------------------------------------------------+
|                   Service Layer (services/)                     |
|  Business logic: validation, orchestration, invalidation       |
|                                                                |
|  +------------------+  +------------------+  +---------------+ |
|  | EntityService    |  | QueryService     |  | TaskService   | |
|  | (shared context) |  | (query ops)      |  | (CRUD + inv.) | |
|  +------------------+  +------------------+  +---------------+ |
|  +------------------+  +------------------+                    |
|  | SectionService   |  | DataFrameService |                    |
|  | (CRUD + inv.)    |  | (build ops)      |                    |
|  +------------------+  +------------------+                    |
+---------------------------------------------------------------+
                              |
                    Constructor injection
                              |
+---------------------------------------------------------------+
|                  Infrastructure Layer                           |
|  EntityRegistry, AsanaClient, MutationInvalidator,             |
|  QueryEngine, SchemaRegistry, SectionPersistence               |
+---------------------------------------------------------------+
```

### Key Principle: Entity Context as First-Class Object

Currently, every route handler independently resolves entity context: validate entity type, look up project GID, acquire bot PAT, check registry readiness. This is extracted into an `EntityContext` dataclass returned by `EntityService`:

```python
@dataclass(frozen=True)
class EntityContext:
    """Validated entity context for service operations."""
    entity_type: str
    project_gid: str
    descriptor: EntityDescriptor  # From B1 EntityRegistry
    bot_pat: str
```

Services that need entity context accept it as a parameter rather than resolving it themselves. This eliminates the 4-way duplication of entity resolution across route modules.

---

## Component Design: Service Protocols

### Location: `src/autom8_asana/services/protocols.py`

All service interfaces are defined as `typing.Protocol` classes. This enables structural typing -- any class with matching methods satisfies the protocol without explicit inheritance. This is the Python-native approach and avoids ABC registration overhead.

```python
from __future__ import annotations
from typing import Any, Protocol, runtime_checkable
from dataclasses import dataclass

@dataclass(frozen=True)
class EntityContext:
    """Validated entity context for service operations."""
    entity_type: str
    project_gid: str
    descriptor: EntityDescriptor
    bot_pat: str


@runtime_checkable
class EntityServiceProtocol(Protocol):
    """Entity resolution and validation service."""

    def validate_entity_type(self, entity_type: str) -> EntityContext:
        """Validate entity type and return full context.

        Raises:
            UnknownEntityError: Entity type not resolvable.
            ServiceNotConfiguredError: Registry not ready or bot PAT missing.
        """
        ...

    def get_queryable_entities(self) -> set[str]:
        """Get entity types that support querying."""
        ...


@runtime_checkable
class QueryServiceProtocol(Protocol):
    """Query operations on DataFrame cache."""

    async def query_legacy(
        self,
        ctx: EntityContext,
        client: AsanaClient,
        where: dict[str, Any],
        select: list[str] | None,
        limit: int,
        offset: int,
    ) -> QueryResult:
        """Execute legacy equality-filter query."""
        ...

    async def query_rows(
        self,
        ctx: EntityContext,
        client: AsanaClient,
        request: RowsRequest,
    ) -> RowsResponse:
        """Execute composable predicate query."""
        ...

    def validate_fields(
        self,
        fields: list[str],
        entity_type: str,
    ) -> None:
        """Validate fields against entity schema.

        Raises:
            InvalidFieldError: Field not in schema.
        """
        ...


@runtime_checkable
class TaskServiceProtocol(Protocol):
    """Task CRUD operations with cache invalidation."""

    async def list_tasks(
        self,
        client: AsanaClient,
        project: str | None,
        section: str | None,
        limit: int,
        offset: str | None,
    ) -> ServiceListResult:
        """List tasks by project or section.

        Raises:
            InvalidParameterError: Neither or both of project/section.
        """
        ...

    async def get_task(
        self,
        client: AsanaClient,
        gid: str,
        opt_fields: list[str] | None,
    ) -> dict[str, Any]:
        """Get task by GID."""
        ...

    async def create_task(
        self,
        client: AsanaClient,
        params: CreateTaskParams,
    ) -> dict[str, Any]:
        """Create task and fire invalidation event."""
        ...

    async def update_task(
        self,
        client: AsanaClient,
        gid: str,
        params: UpdateTaskParams,
    ) -> dict[str, Any]:
        """Update task and fire invalidation event."""
        ...

    async def delete_task(
        self,
        client: AsanaClient,
        gid: str,
    ) -> None:
        """Delete task and fire invalidation event."""
        ...


@runtime_checkable
class SectionServiceProtocol(Protocol):
    """Section CRUD operations with cache invalidation."""

    async def get_section(
        self,
        client: AsanaClient,
        gid: str,
    ) -> dict[str, Any]:
        """Get section by GID."""
        ...

    async def create_section(
        self,
        client: AsanaClient,
        name: str,
        project: str,
    ) -> dict[str, Any]:
        """Create section and fire invalidation event."""
        ...

    async def update_section(
        self,
        client: AsanaClient,
        gid: str,
        name: str,
    ) -> dict[str, Any]:
        """Update section and fire invalidation event."""
        ...

    async def delete_section(
        self,
        client: AsanaClient,
        gid: str,
    ) -> None:
        """Delete section and fire invalidation event."""
        ...


@runtime_checkable
class DataFrameServiceProtocol(Protocol):
    """DataFrame build operations."""

    async def build_project_dataframe(
        self,
        client: AsanaClient,
        project_gid: str,
        schema_name: str,
        limit: int,
        offset: str | None,
    ) -> DataFrameResult:
        """Build DataFrame for project tasks."""
        ...

    async def build_section_dataframe(
        self,
        client: AsanaClient,
        section_gid: str,
        schema_name: str,
        limit: int,
        offset: str | None,
    ) -> DataFrameResult:
        """Build DataFrame for section tasks."""
        ...
```

---

## Component Design: Service Implementations

### EntityService

**Location**: `src/autom8_asana/services/entity_service.py`

The EntityService consolidates entity resolution logic that is currently duplicated across all four route modules. It wraps B1 EntityRegistry and `EntityProjectRegistry` with validation logic and bot PAT acquisition.

```python
class EntityService:
    """Entity resolution service backed by B1 EntityRegistry.

    Consolidates the entity validation + project lookup + bot PAT
    acquisition pattern currently duplicated across route handlers.
    """

    def __init__(
        self,
        entity_registry: EntityRegistry,
        project_registry: EntityProjectRegistry,
    ) -> None:
        self._entity_registry = entity_registry
        self._project_registry = project_registry

    def validate_entity_type(self, entity_type: str) -> EntityContext:
        queryable = self.get_queryable_entities()
        if entity_type not in queryable:
            raise UnknownEntityError(entity_type, sorted(queryable))

        descriptor = self._entity_registry.require(entity_type)
        project_gid = self._project_registry.get_project_gid(entity_type)

        if project_gid is None:
            raise ServiceNotConfiguredError(
                f"No project configured for entity type: {entity_type}"
            )

        from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat
        try:
            bot_pat = get_bot_pat()
        except BotPATError as e:
            raise ServiceNotConfiguredError(f"Bot PAT not configured: {e}")

        return EntityContext(
            entity_type=entity_type,
            project_gid=project_gid,
            descriptor=descriptor,
            bot_pat=bot_pat,
        )

    def get_queryable_entities(self) -> set[str]:
        return get_resolvable_entities(
            project_registry=self._project_registry,
        )
```

### QueryService (extends existing EntityQueryService)

**Location**: `src/autom8_asana/services/query_service.py` (modified)

The existing `EntityQueryService` already contains the core query logic. The extraction adds:
1. Field validation (from `_validate_fields()` in query.py)
2. Section resolution (from `_resolve_section()` in query.py)
3. Request preparation (section predicate stripping)
4. QueryEngine orchestration (from `query_rows()` handler)

```python
class QueryService(EntityQueryService):
    """Extended query service with validation and section resolution.

    Inherits DataFrame query mechanics from EntityQueryService.
    Adds field validation, section resolution, and request preparation
    extracted from route handlers.
    """

    def validate_fields(
        self,
        fields: list[str],
        entity_type: str,
    ) -> None:
        """Validate fields against entity schema.

        Raises:
            InvalidFieldError: With available_fields for error response.
        """
        registry = SchemaRegistry.get_instance()
        schema_key = to_pascal_case(entity_type)
        try:
            schema = registry.get_schema(schema_key)
        except SchemaNotFoundError:
            schema = registry.get_schema("*")

        valid_fields = set(schema.column_names())
        invalid_fields = set(fields) - valid_fields

        if invalid_fields:
            raise InvalidFieldError(
                invalid_fields=sorted(invalid_fields),
                available_fields=sorted(valid_fields),
            )

    async def resolve_section(
        self,
        section_name: str,
        entity_type: str,
        project_gid: str,
    ) -> str:
        """Validate section name against manifest or enum fallback.

        Raises:
            UnknownSectionError: Section name not found.
        """
        # Logic extracted from _resolve_section() in query.py
        ...

    def prepare_rows_request(
        self,
        request: RowsRequest,
        entity_type: str,
        project_gid: str,
    ) -> tuple[RowsRequest, SectionIndex | None]:
        """Prepare rows request: validate section, strip conflicts.

        Returns:
            Tuple of (possibly modified request, section_index or None).
        """
        ...

    async def query_rows(
        self,
        ctx: EntityContext,
        client: AsanaClient,
        request: RowsRequest,
    ) -> RowsResponse:
        """Execute composable predicate query.

        Orchestrates: section resolution, predicate stripping,
        QueryEngine execution, error mapping.
        """
        request, section_index = self.prepare_rows_request(
            request, ctx.entity_type, ctx.project_gid
        )
        engine = QueryEngine()
        return await engine.execute_rows(
            entity_type=ctx.entity_type,
            project_gid=ctx.project_gid,
            client=client,
            request=request,
            section_index=section_index,
        )
```

### TaskService

**Location**: `src/autom8_asana/services/task_service.py`

Encapsulates task CRUD operations with integrated cache invalidation. The service owns MutationEvent construction, eliminating the repeated `extract_project_gids()` + `invalidator.fire_and_forget()` pattern from each route handler.

```python
@dataclass
class ServiceListResult:
    """Paginated list result from service layer."""
    data: list[dict[str, Any]]
    has_more: bool
    next_offset: str | None


class TaskService:
    """Task CRUD operations with integrated cache invalidation.

    Encapsulates:
    - Asana SDK task client calls
    - MutationEvent construction from response data
    - Fire-and-forget invalidation via MutationInvalidator
    """

    def __init__(
        self,
        invalidator: MutationInvalidator,
    ) -> None:
        self._invalidator = invalidator

    async def create_task(
        self,
        client: AsanaClient,
        params: CreateTaskParams,
    ) -> dict[str, Any]:
        if params.projects is None and params.workspace is None:
            raise InvalidParameterError(
                "Either 'projects' or 'workspace' must be provided"
            )

        kwargs: dict[str, Any] = {}
        if params.notes: kwargs["notes"] = params.notes
        if params.assignee: kwargs["assignee"] = params.assignee
        if params.due_on: kwargs["due_on"] = params.due_on

        task = await client.tasks.create_async(
            name=params.name,
            projects=params.projects,
            workspace=params.workspace,
            raw=True,
            **kwargs,
        )

        # Encapsulated invalidation
        project_gids = extract_project_gids(task) or (params.projects or [])
        task_gid = task.get("gid", "") if isinstance(task, dict) else ""
        self._invalidator.fire_and_forget(MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid=task_gid,
            mutation_type=MutationType.CREATE,
            project_gids=list(project_gids),
        ))

        return task

    # Similar pattern for update_task, delete_task, etc.
```

### SectionService

**Location**: `src/autom8_asana/services/section_service.py`

Mirrors TaskService for section operations. Encapsulates SDK calls and invalidation.

### DataFrameService

**Location**: `src/autom8_asana/services/dataframe_service.py`

Extracts DataFrame building logic from the dataframes route. Encapsulates schema resolution, opt_fields construction, and DataFrame assembly.

```python
@dataclass
class DataFrameResult:
    """Result of DataFrame build operation."""
    dataframe: pl.DataFrame
    has_more: bool
    next_offset: str | None


class DataFrameService:
    """DataFrame build operations.

    Extracts schema resolution, opt_fields construction, and
    DataFrame assembly from route handlers.
    """

    # Standard opt_fields for task fetch (was duplicated in both endpoints)
    TASK_OPT_FIELDS: ClassVar[list[str]] = [
        "gid", "name", "resource_type", "completed", "completed_at",
        "created_at", "modified_at", "notes", "assignee", "assignee.name",
        "due_on", "due_at", "start_on", "memberships.section.name",
        "memberships.project.gid", "custom_fields", "custom_fields.gid",
        "custom_fields.name", "custom_fields.resource_subtype",
        "custom_fields.display_value", "custom_fields.enum_value",
        "custom_fields.enum_value.name", "custom_fields.multi_enum_values",
        "custom_fields.multi_enum_values.name", "custom_fields.number_value",
        "custom_fields.text_value",
    ]

    def get_schema(self, schema_name: str) -> DataFrameSchema:
        """Resolve schema name to DataFrameSchema.

        Raises:
            InvalidSchemaError: Schema name not found.
        """
        ...

    async def build_project_dataframe(
        self,
        client: AsanaClient,
        project_gid: str,
        schema_name: str,
        limit: int,
        offset: str | None,
    ) -> DataFrameResult:
        """Build DataFrame for project tasks."""
        ...
```

---

## Dependency Injection Pattern

### Approach: FastAPI `Depends()` with Factory Functions

FastAPI's built-in dependency injection via `Depends()` is the correct pattern for this codebase. Services are instantiated per-request (or shared via singletons stored on `app.state`) and injected into route handlers via `Annotated[ServiceType, Depends(factory)]` type aliases.

### Wiring in `api/dependencies.py`

```python
# --- Service Factories ---

def get_entity_service(request: Request) -> EntityService:
    """Get EntityService from app state (singleton)."""
    entity_service = getattr(request.app.state, "entity_service", None)
    if entity_service is None:
        # Lazy initialization with existing registries
        from autom8_asana.core.entity_registry import get_registry
        from autom8_asana.services.resolver import EntityProjectRegistry
        from autom8_asana.services.entity_service import EntityService

        entity_service = EntityService(
            entity_registry=get_registry(),
            project_registry=EntityProjectRegistry.get_instance(),
        )
        request.app.state.entity_service = entity_service
    return entity_service


def get_query_service() -> QueryService:
    """Get QueryService instance."""
    from autom8_asana.services.query_service import QueryService
    return QueryService()


def get_task_service(request: Request) -> TaskService:
    """Get TaskService with MutationInvalidator."""
    from autom8_asana.services.task_service import TaskService

    invalidator = get_mutation_invalidator(request)
    return TaskService(invalidator=invalidator)


def get_section_service(request: Request) -> SectionService:
    """Get SectionService with MutationInvalidator."""
    from autom8_asana.services.section_service import SectionService

    invalidator = get_mutation_invalidator(request)
    return SectionService(invalidator=invalidator)


def get_dataframe_service() -> DataFrameService:
    """Get DataFrameService instance."""
    from autom8_asana.services.dataframe_service import DataFrameService
    return DataFrameService()


# --- Type Aliases ---
EntityServiceDep = Annotated[EntityService, Depends(get_entity_service)]
QueryServiceDep = Annotated[QueryService, Depends(get_query_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
SectionServiceDep = Annotated[SectionService, Depends(get_section_service)]
DataFrameServiceDep = Annotated[DataFrameService, Depends(get_dataframe_service)]
```

### Lifecycle

| Service | Lifecycle | Reason |
|---------|-----------|--------|
| `EntityService` | Singleton (app.state) | Wraps singleton registries, no per-request state |
| `QueryService` | Per-request | Contains `_last_freshness_info` state |
| `TaskService` | Per-request | Receives request-scoped invalidator |
| `SectionService` | Per-request | Receives request-scoped invalidator |
| `DataFrameService` | Per-request | Stateless, cheap to create |

---

## EntityRegistry Integration

### Before (Current State)

Route handlers perform entity resolution via multiple scattered patterns:

```python
# In query.py -- uses get_resolvable_entities() + EntityProjectRegistry
queryable_types = _get_queryable_entities()
if entity_type not in queryable_types:
    raise HTTPException(status_code=404, ...)

entity_registry = getattr(request.app.state, "entity_project_registry", None)
if entity_registry is None or not entity_registry.is_ready():
    raise HTTPException(status_code=503, ...)

project_gid = entity_registry.get_project_gid(entity_type)
if project_gid is None:
    raise HTTPException(status_code=503, ...)
```

This 15-line pattern is repeated in both `query_entities()` and `query_rows()` with minor variations.

### After (With EntityService)

```python
# In query.py route handler -- single call
try:
    ctx = entity_service.validate_entity_type(entity_type)
except UnknownEntityError as e:
    raise HTTPException(status_code=404, detail=e.to_dict())
except ServiceNotConfiguredError as e:
    raise HTTPException(status_code=503, detail=e.to_dict())
```

### EntityService Internals Using B1 Registry

```python
def validate_entity_type(self, entity_type: str) -> EntityContext:
    # B1 EntityRegistry provides O(1) lookup
    descriptor = self._entity_registry.get(entity_type)
    if descriptor is None:
        raise UnknownEntityError(
            entity_type,
            available=self._entity_registry.all_names(),
        )

    # Check if entity has schema + project (resolvable)
    if not descriptor.has_project:
        raise UnknownEntityError(entity_type, ...)

    project_gid = self._project_registry.get_project_gid(entity_type)
    if project_gid is None:
        raise ServiceNotConfiguredError(...)

    bot_pat = self._acquire_bot_pat()

    return EntityContext(
        entity_type=entity_type,
        project_gid=project_gid,
        descriptor=descriptor,
        bot_pat=bot_pat,
    )
```

---

## Error Handling at Service Boundary

### Service-Level Exceptions

Services raise domain-specific exceptions. Route handlers map these to HTTP responses. This inverts the current pattern where business validation directly raises `HTTPException`.

**Location**: `src/autom8_asana/services/errors.py`

```python
class ServiceError(Exception):
    """Base class for service-layer errors."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to API error response format."""
        return {"error": self.error_code, "message": str(self)}

    @property
    def error_code(self) -> str:
        return "SERVICE_ERROR"


class UnknownEntityError(ServiceError):
    """Entity type not resolvable."""

    def __init__(self, entity_type: str, available: list[str]) -> None:
        self.entity_type = entity_type
        self.available = available
        super().__init__(f"Unknown entity type: {entity_type}")

    @property
    def error_code(self) -> str:
        return "UNKNOWN_ENTITY_TYPE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.error_code,
            "message": str(self),
            "available_types": self.available,
        }


class ServiceNotConfiguredError(ServiceError):
    """Required service dependency not available."""

    @property
    def error_code(self) -> str:
        return "SERVICE_NOT_CONFIGURED"


class InvalidFieldError(ServiceError):
    """Field not valid for entity schema."""

    def __init__(self, invalid_fields: list[str], available_fields: list[str]) -> None:
        self.invalid_fields = invalid_fields
        self.available_fields = available_fields
        super().__init__(f"Invalid fields: {invalid_fields}")

    @property
    def error_code(self) -> str:
        return "INVALID_FIELD"

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.error_code,
            "message": str(self),
            "available_fields": self.available_fields,
        }


class InvalidParameterError(ServiceError):
    """Invalid request parameter."""

    @property
    def error_code(self) -> str:
        return "INVALID_PARAMETER"


class CacheNotReadyError(ServiceError):
    """Cache not warmed for requested entity."""

    @property
    def error_code(self) -> str:
        return "CACHE_NOT_WARMED"
```

### Error Mapping in Route Handlers

Route handlers have a single error-mapping responsibility:

```python
# Standard error mapping pattern for all routes
SERVICE_ERROR_MAP: dict[type, int] = {
    UnknownEntityError: 404,
    InvalidFieldError: 422,
    InvalidParameterError: 400,
    ServiceNotConfiguredError: 503,
    CacheNotReadyError: 503,
}

def map_service_error(error: ServiceError) -> HTTPException:
    """Map service error to HTTP response."""
    status_code = SERVICE_ERROR_MAP.get(type(error), 500)
    return HTTPException(status_code=status_code, detail=error.to_dict())
```

---

## Migration Plan

### Phase 1: Foundation (No Route Changes)

Create service infrastructure without modifying any routes. All new code, zero risk.

| Task | File | Description |
|------|------|-------------|
| 1.1 | `services/errors.py` | Service exception hierarchy |
| 1.2 | `services/protocols.py` | Protocol definitions + EntityContext dataclass |
| 1.3 | `services/entity_service.py` | EntityService implementation |
| 1.4 | `api/dependencies.py` | Add service factory functions and type aliases |
| 1.5 | Tests | Unit tests for EntityService, error hierarchy |

**Acceptance**: All new tests pass. No existing tests affected.

### Phase 2: TaskService + SectionService Extraction

These are the simplest extractions -- the route handlers are mostly thin SDK wrappers with MutationEvent construction.

| Task | File | Description |
|------|------|-------------|
| 2.1 | `services/task_service.py` | TaskService with all 13 operations |
| 2.2 | `services/section_service.py` | SectionService with all 6 operations |
| 2.3 | `api/routes/tasks.py` | Refactor to delegate to TaskService |
| 2.4 | `api/routes/sections.py` | Refactor to delegate to SectionService |
| 2.5 | Tests | Service unit tests + integration regression |

**Acceptance**: All existing API tests pass unchanged. Service tests cover all operations without HTTP fixtures.

### Phase 3: QueryService Enhancement

Extend existing `EntityQueryService` with field validation, section resolution, and request preparation.

| Task | File | Description |
|------|------|-------------|
| 3.1 | `services/query_service.py` | Add `validate_fields`, `resolve_section`, `prepare_rows_request`, `query_rows` |
| 3.2 | `api/routes/query.py` | Refactor both endpoints to delegate to QueryService |
| 3.3 | Tests | Service unit tests + route integration regression |

**Acceptance**: All existing query API tests pass unchanged. Section resolution testable without HTTP.

### Phase 4: DataFrameService Extraction

Most complex extraction due to schema resolution and Polars operations.

| Task | File | Description |
|------|------|-------------|
| 4.1 | `services/dataframe_service.py` | DataFrameService with schema resolution and build |
| 4.2 | `api/routes/dataframes.py` | Refactor to delegate to DataFrameService |
| 4.3 | Tests | Service unit tests + route integration regression |

**Acceptance**: Content negotiation stays in route. Build logic testable without HTTP.

---

## Interface Contracts

### EntityContext (shared across all services)

```python
@dataclass(frozen=True)
class EntityContext:
    entity_type: str        # e.g., "unit", "offer"
    project_gid: str        # Asana project GID
    descriptor: EntityDescriptor  # From B1 EntityRegistry
    bot_pat: str            # Bot PAT for Asana API calls
```

### ServiceListResult (used by TaskService list operations)

```python
@dataclass
class ServiceListResult:
    data: list[dict[str, Any]]
    has_more: bool
    next_offset: str | None
```

### DataFrameResult (used by DataFrameService)

```python
@dataclass
class DataFrameResult:
    dataframe: pl.DataFrame
    has_more: bool
    next_offset: str | None
```

### QueryResult (existing, extended)

```python
@dataclass
class QueryResult:
    data: list[dict[str, Any]]
    total_count: int
    project_gid: str
```

---

## Data Flow Diagrams

### Before: Query Request Flow (current)

```
HTTP Request
    |
    v
query_entities() route handler
    |-- validate entity type (inline, 15 lines)
    |-- validate fields (calls _validate_fields(), 15 lines)
    |-- resolve project GID (inline, 12 lines)
    |-- acquire bot PAT (inline, 10 lines)
    |-- create AsanaClient (inline)
    |-- call EntityQueryService.query() (1 line)
    |-- build QueryResponse (5 lines)
    |-- add deprecation headers (3 lines)
    |-- log completion (10 lines)
    v
HTTP Response
```

### After: Query Request Flow (extracted)

```
HTTP Request
    |
    v
query_entities() route handler (thin adapter)
    |-- entity_service.validate_entity_type(entity_type) -> EntityContext
    |-- query_service.validate_fields(where_fields, entity_type)
    |-- query_service.validate_fields(select_fields, entity_type)
    |-- async with AsanaClient(token=ctx.bot_pat) as client:
    |       result = await query_service.query_legacy(ctx, client, ...)
    |-- return JSONResponse(...)  # + deprecation headers
    v
HTTP Response
```

### Before: Task Creation Flow (current)

```
HTTP Request
    |
    v
create_task() route handler
    |-- validate projects/workspace (3 lines)
    |-- build kwargs dict (6 lines)
    |-- call client.tasks.create_async() (5 lines)
    |-- extract_project_gids(task) (1 line)
    |-- construct MutationEvent (6 lines)
    |-- invalidator.fire_and_forget(event) (1 line)
    |-- build_success_response(data=task) (1 line)
    v
HTTP Response
```

### After: Task Creation Flow (extracted)

```
HTTP Request
    |
    v
create_task() route handler (thin adapter)
    |-- task = await task_service.create_task(client, body)
    |-- return build_success_response(data=task)
    v
HTTP Response
```

---

## Non-Functional Considerations

### Performance

**Impact**: Negligible. The extraction adds one function call indirection per request (service method call). No new I/O operations. No additional memory allocation beyond the EntityContext dataclass (frozen, 4 fields).

**Measurement**: Before/after p99 latency comparison on the query endpoint (target: <1ms overhead).

### Backward Compatibility

**API Contract**: Zero changes. Same URLs, same request/response shapes, same status codes, same error formats, same deprecation headers. The `to_dict()` methods on service errors produce the identical JSON structure as the current inline `HTTPException.detail` dicts.

**Import Paths**: Existing imports of `EntityQueryService` and `CacheNotWarmError` from `services/query_service.py` continue to work. The class is extended, not replaced.

### Observability

**Logging**: Service methods include the same structured log events as current route handlers. The log events move from route to service, but the same `entity_type`, `request_id`, and `duration_ms` fields are preserved.

**Metrics**: No metric changes. Existing endpoint-level metrics continue to measure the same operations.

---

## Test Strategy

### Unit Tests for Services (no HTTP, no IO)

Each service gets a dedicated test module with mock dependencies:

| Test Module | Tests | Key Assertions |
|------------|-------|----------------|
| `tests/unit/services/test_entity_service.py` | Entity validation, unknown entity, unconfigured registry, missing bot PAT | Correct exception types with error details |
| `tests/unit/services/test_query_service.py` | Field validation, section resolution, request preparation, legacy query, rows query | No HTTPException anywhere in service |
| `tests/unit/services/test_task_service.py` | All 13 CRUD operations, MutationEvent construction, invalidation called | fire_and_forget called with correct event |
| `tests/unit/services/test_section_service.py` | All 6 operations, MutationEvent construction | fire_and_forget called with correct event |
| `tests/unit/services/test_dataframe_service.py` | Schema resolution, DataFrame build, opt_fields | Schema errors raise InvalidSchemaError |

### Mock Patterns

```python
# TaskService test example -- no HTTP layer needed
async def test_create_task_fires_invalidation():
    mock_client = AsyncMock()
    mock_client.tasks.create_async.return_value = {
        "gid": "123",
        "memberships": [{"project": {"gid": "proj-1"}}],
    }
    mock_invalidator = MagicMock()

    service = TaskService(invalidator=mock_invalidator)
    result = await service.create_task(
        client=mock_client,
        params=CreateTaskParams(name="Test", projects=["proj-1"]),
    )

    assert result["gid"] == "123"
    mock_invalidator.fire_and_forget.assert_called_once()
    event = mock_invalidator.fire_and_forget.call_args[0][0]
    assert event.mutation_type == MutationType.CREATE
    assert "proj-1" in event.project_gids
```

### Integration Regression Tests

Existing API tests in `tests/api/` continue to pass unchanged. These serve as regression tests ensuring the extraction preserves behavior.

### Error Boundary Tests

```python
async def test_service_errors_do_not_leak_http_exceptions():
    """Services must raise ServiceError, never HTTPException."""
    service = EntityService(...)
    with pytest.raises(UnknownEntityError):  # NOT HTTPException
        service.validate_entity_type("nonexistent")
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Behavior regression during extraction | Medium | High | Phase-by-phase migration with existing API tests as regression gate |
| Service/route error format mismatch | Low | Medium | `to_dict()` methods produce identical JSON; snapshot tests verify |
| Circular import from service -> infrastructure | Medium | Low | Lazy imports in factory functions (existing pattern in codebase) |
| Over-engineering: too many service classes | Low | Low | 5 services matches 4 route modules + 1 shared (EntityService); no artificial splitting |
| EntityRegistry/EntityProjectRegistry dual dependency | Low | Low | EntityService wraps both; future consolidation (EntityProjectRegistry -> EntityRegistry) is a follow-up |

---

## ADRs

### ADR-SLE-001: Protocols Over ABCs for Service Interfaces

**Context**: Service interfaces need to be defined for testability and documentation. Python offers three patterns: Abstract Base Classes (ABCs), typing.Protocol (structural typing), or no formal interface (duck typing).

**Decision**: Use `typing.Protocol` with `@runtime_checkable` for all service interfaces.

**Rationale**:
- Protocols enable structural typing -- any class with matching methods satisfies the protocol without explicit registration or inheritance
- ABCs require `register()` or inheritance, creating coupling between interface and implementation
- `@runtime_checkable` enables `isinstance()` checks for debugging without enforcing inheritance
- The codebase already uses Protocol patterns (e.g., `CacheProvider` protocol in `protocols/cache.py`)
- Protocols work naturally with mock objects in tests (no need to subclass ABC)

**Consequences**:
- Positive: Clean separation, easy mocking, no import coupling
- Negative: No enforcement that implementations cover all methods (caught by type checker, not runtime)
- Mitigation: `mypy --strict` catches missing method implementations

### ADR-SLE-002: Constructor Injection for Service Dependencies

**Context**: Services need dependencies (EntityRegistry, MutationInvalidator, etc.). Options: (1) constructor injection, (2) method parameter injection, (3) module-level singletons, (4) FastAPI Depends() all the way down.

**Decision**: Constructor injection for service dependencies. FastAPI `Depends()` only at the route-to-service boundary.

**Rationale**:
- Constructor injection makes the dependency graph explicit and inspectable
- Services can be instantiated in non-HTTP contexts (Lambda, CLI) by passing dependencies directly
- FastAPI `Depends()` is HTTP-framework-specific and should not leak into the service layer
- Module-level singletons (current pattern for EntityProjectRegistry) create hidden coupling and hinder testing
- Method parameter injection (passing `client` per-call) is appropriate for per-request resources like AsanaClient, which naturally vary per call

**Consequences**:
- Positive: Testable (pass mocks), reusable (non-HTTP), explicit (no hidden state)
- Negative: Factory functions in `dependencies.py` need to wire up constructors
- Acceptable: This is the standard FastAPI DI pattern used by the existing `get_mutation_invalidator()`

### ADR-SLE-003: Service Errors as Domain Exceptions, Not HTTPException

**Context**: Currently, route handlers raise `HTTPException` directly when business validation fails. Options: (1) keep HTTPException in services, (2) create service-specific exceptions mapped in routes, (3) return result objects with error states.

**Decision**: Services raise domain-specific exceptions (`ServiceError` subclasses). Route handlers catch and map to `HTTPException`.

**Rationale**:
- `HTTPException` is an HTTP-framework concern that does not belong in business logic
- Services must be usable from non-HTTP contexts where `HTTPException` has no meaning
- Domain exceptions carry richer context (available fields, entity types) than status codes
- The mapping is mechanical (exception type -> status code) and can be centralized
- Error `to_dict()` methods produce the same JSON format as current `HTTPException.detail` dicts, ensuring backward compatibility

**Consequences**:
- Positive: Services portable to any transport, richer error information
- Negative: One additional layer of exception translation in routes
- Acceptable: Translation is a 3-line pattern per error type, easily centralized via `map_service_error()`

---

## Success Criteria

| ID | Criterion | Measurement |
|----|-----------|-------------|
| SC-1 | All route handlers <= 30 lines (excluding decorators/docstrings) | Line count audit |
| SC-2 | Zero `HTTPException` raised inside any service class | Grep for `HTTPException` in `services/` |
| SC-3 | All existing API tests pass without modification | `pytest tests/api/` green |
| SC-4 | Service tests achieve 100% branch coverage on extracted logic | `pytest --cov=services/` |
| SC-5 | Services usable without FastAPI (importable and callable with plain arguments) | Standalone test: import service, call method, no HTTP |
| SC-6 | EntityService uses B1 EntityRegistry (no direct SchemaRegistry entity enumeration) | Code review: EntityService calls `get_registry()` |
| SC-7 | MutationEvent construction consolidated (zero in route handlers) | Grep for `MutationEvent(` in `api/routes/` returns zero hits |
| SC-8 | p99 latency regression < 1ms on query endpoint | Before/after benchmark |

---

## Attestation Table

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| TDD (this document) | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-service-layer-extraction.md` | Yes |
| Route: query.py (extraction source) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/query.py` | Read |
| Route: tasks.py (extraction source) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/tasks.py` | Read |
| Route: sections.py (extraction source) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/sections.py` | Read |
| Route: dataframes.py (extraction source) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/dataframes.py` | Read |
| Existing DI: dependencies.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/dependencies.py` | Read |
| Existing service: query_service.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py` | Read |
| Existing service: resolver.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` | Read |
| B1 EntityRegistry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/entity_registry.py` | Read |
| A1 MutationInvalidator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/mutation_invalidator.py` | Read |
| A1 MutationEvent | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/mutation_event.py` | Read |
| App initialization: main.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | Read |
| Architectural opportunities | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/architectural-opportunities.md` | Read |
