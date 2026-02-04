# TDD: I2 Service Layer Wiring -- Review and Implementation Addendum

**TDD ID**: TDD-I2-SERVICE-WIRING-001
**Version**: 1.0
**Date**: 2026-02-04
**Author**: Architect
**Status**: APPROVED
**Parent TDD**: TDD-SERVICE-LAYER-001 (docs/design/TDD-service-layer-extraction.md)
**PRD Reference**: Deferred Work Roadmap I2 (Wave 2)
**Session**: session-20260204-195700-0f38ebf6

---

## Table of Contents

1. [Purpose of This Document](#purpose-of-this-document)
2. [Delta Assessment](#delta-assessment)
3. [Current State Inventory](#current-state-inventory)
4. [Route-to-Service Wiring Map](#route-to-service-wiring-map)
5. [Dependencies.py Changes](#dependenciespy-changes)
6. [Per-Route Migration Specifications](#per-route-migration-specifications)
7. [Migration Strategy](#migration-strategy)
8. [Risk Assessment](#risk-assessment)
9. [Success Criteria](#success-criteria)
10. [Sprint Plan](#sprint-plan)
11. [ADRs](#adrs)

---

## Purpose of This Document

This addendum bridges the gap between the original TDD-SERVICE-LAYER-001 (which specified **what** to build) and the actual wiring work (which specifies **how** to connect the now-built service modules to existing API routes). The original TDD's Phase 1 (Foundation) and Phase 2 (TaskService + SectionService) service implementations are complete. What remains is the actual route handler refactoring and DI wiring -- the "last mile" that makes the orphaned services do useful work.

---

## Delta Assessment

### What Changed Since the Original TDD

The hygiene sprint introduced several changes that affect the wiring plan. This section catalogs each change and its impact on the TDD-SERVICE-LAYER-001 design.

| Change | Impact on Wiring | Action |
|--------|-----------------|--------|
| **Cache module reorganization** -- MutationEvent moved from `cache/mutation_event.py` to `cache/models/mutation_event.py`; MutationInvalidator moved to `cache/integration/mutation_invalidator.py` | Service modules already import from new paths. No change needed. | None |
| **Exception hierarchy** (`core/exceptions.py`) -- Added `CACHE_TRANSIENT_ERRORS`, `S3_TRANSPORT_ERRORS`, etc. | `query.py` already uses `S3_TRANSPORT_ERRORS` in `_resolve_section()`. Services should use these tuples instead of bare `except Exception`. | Minor: verify service error handling uses narrowed exceptions |
| **EntityRegistry** (`core/entity_registry.py`) fully built -- B1 complete with `EntityDescriptor`, `get_registry()`, `require()` | EntityService already wired to use it. No change needed. | None |
| **Service modules fully implemented** -- `entity_service.py`, `task_service.py`, `section_service.py`, `entity_context.py`, `errors.py` all built with full docstrings and tests | Original TDD's Phase 1 and Phase 2 are complete. Wiring is Phase 3/4 only. | This addendum covers Phase 3/4 |
| **Service tests exist** -- 1,332 lines across 4 test files | Test foundation exists. Route integration tests needed. | Add route-level regression tests |
| **`errors.py` enhanced** -- Added `status_hint` property, `get_status_for_error()` MRO walker, `EntityNotFoundError`/`EntityValidationError` intermediate classes | Error mapping is richer than TDD-001 specified. Use `get_status_for_error()` instead of manual map. | Adopt `get_status_for_error()` in route error mapper |

### What the Original TDD Got Right (No Changes)

- Service protocols as `typing.Protocol` (ADR-SLE-001) -- still correct
- Constructor injection for service deps (ADR-SLE-002) -- already implemented
- Service errors as domain exceptions (ADR-SLE-003) -- already implemented
- EntityContext as first-class object -- already implemented
- FastAPI `Depends()` at route-to-service boundary -- still the right pattern
- Service lifecycle decisions (EntityService singleton, others per-request) -- still correct

### What the Original TDD Deferred That We Now Address

1. **`protocols.py` file** -- The original TDD specified a `services/protocols.py` module. The implementations were built without it. **Decision**: Skip `protocols.py` for now. The concrete classes serve as their own documentation. Protocols can be extracted later if a second implementation is needed. This follows YAGNI.

2. **DataFrameService** -- The original TDD specified a `DataFrameService`. The `dataframes.py` route is the most complex extraction (schema resolution, Polars operations, content negotiation, SectionProxy). **Decision**: Defer DataFrameService to a later sprint. Focus this initiative on tasks, sections, and query -- the three routes where service modules already exist.

3. **QueryService enhancement** -- The original TDD extended `EntityQueryService`. The existing service already works. **Decision**: Extract field validation and section resolution into the service incrementally during query route wiring.

---

## Current State Inventory

### Route Files (extraction targets)

| File | Lines | Business Logic % | MutationEvent count | HTTPException count |
|------|-------|-------------------|---------------------|---------------------|
| `api/routes/tasks.py` | 736 | ~50% | 10 | 5 |
| `api/routes/sections.py` | 288 | ~45% | 4 | 3 |
| `api/routes/query.py` | 665 | ~70% | 0 | 20 |
| `api/routes/dataframes.py` | 553 | ~65% | 0 | 8 |
| `api/routes/admin.py` | 474 | ~40% | 0 | 5 |

### Service Files (already built, orphaned)

| File | Lines | Tests (lines) | Status |
|------|-------|---------------|--------|
| `services/entity_service.py` | 150 | 245 | Built, orphaned |
| `services/task_service.py` | 644 | 531 | Built, orphaned |
| `services/section_service.py` | 278 | 320 | Built, orphaned |
| `services/entity_context.py` | 41 | (covered by entity_service tests) | Built, orphaned |
| `services/errors.py` | 267 | 236 | Built, orphaned |
| `services/query_service.py` | 408 | (existing tests in multiple files) | In use by query.py already |

### Dependencies Module

| File | Lines | Current DI exports |
|------|-------|--------------------|
| `api/dependencies.py` | 441 | `AsanaClientDualMode`, `MutationInvalidatorDep`, `RequestId`, `AuthContextDep`, `AsanaPAT`, `AsanaClientDep` |

---

## Route-to-Service Wiring Map

This section specifies exactly which service replaces which business logic in each route handler.

### tasks.py --> TaskService

Every route handler in `tasks.py` currently does three things: (1) validate/parse input, (2) call Asana SDK, (3) construct MutationEvent + fire invalidation. Steps 2-3 move entirely into `TaskService`.

| Endpoint | Route Handler | Service Method | What Moves |
|----------|--------------|----------------|------------|
| `GET /tasks` | `list_tasks()` | `task_service.list_tasks()` | Parameter validation, SDK pagination call |
| `GET /tasks/{gid}` | `get_task()` | `task_service.get_task()` | SDK get call |
| `POST /tasks` | `create_task()` | `task_service.create_task()` | Kwargs building, SDK create, MutationEvent |
| `PUT /tasks/{gid}` | `update_task()` | `task_service.update_task()` | Kwargs building, validation, SDK update, MutationEvent |
| `DELETE /tasks/{gid}` | `delete_task()` | `task_service.delete_task()` | SDK delete, MutationEvent |
| `GET /tasks/{gid}/subtasks` | `list_subtasks()` | `task_service.list_subtasks()` | SDK pagination call |
| `GET /tasks/{gid}/dependents` | `list_dependents()` | `task_service.list_dependents()` | SDK pagination call |
| `POST /tasks/{gid}/duplicate` | `duplicate_task()` | `task_service.duplicate_task()` | SDK duplicate, MutationEvent |
| `POST /tasks/{gid}/tags` | `add_tag()` | `task_service.add_tag()` | SDK add_tag, MutationEvent |
| `DELETE /tasks/{gid}/tags/{tag_gid}` | `remove_tag()` | `task_service.remove_tag()` | SDK remove_tag, MutationEvent |
| `POST /tasks/{gid}/section` | `move_to_section()` | `task_service.move_to_section()` | SDK move, MutationEvent (MOVE type) |
| `PUT /tasks/{gid}/assignee` | `set_assignee()` | `task_service.set_assignee()` | SDK set_assignee/update, MutationEvent |
| `POST /tasks/{gid}/projects` | `add_to_project()` | `task_service.add_to_project()` | SDK add_to_project, MutationEvent |
| `DELETE /tasks/{gid}/projects/{project_gid}` | `remove_from_project()` | `task_service.remove_from_project()` | SDK remove_from_project, MutationEvent |

**Post-wiring handler pattern** (all 14 endpoints follow this):

```python
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(
    body: CreateTaskRequest,
    client: AsanaClientDualMode,
    request_id: RequestId,
    task_service: TaskServiceDep,  # NEW: injected service
) -> SuccessResponse[dict[str, Any]]:
    try:
        task = await task_service.create_task(
            client,
            CreateTaskParams(
                name=body.name,
                projects=body.projects,
                workspace=body.workspace,
                notes=body.notes,
                assignee=body.assignee,
                due_on=body.due_on,
            ),
        )
    except InvalidParameterError as e:
        raise HTTPException(status_code=e.status_hint, detail=e.to_dict())
    return build_success_response(data=task, request_id=request_id)
```

**What gets removed from tasks.py**:
- All `MutationEvent` imports and construction (10 instances)
- All `extract_project_gids` calls
- All inline parameter validation (moved to service)
- `MutationInvalidatorDep` dependency from every handler signature
- `from autom8_asana.cache.models.mutation_event import ...` import block

**What stays in tasks.py**:
- Request model parsing (FastAPI `Body`)
- `CreateTaskParams` / `UpdateTaskParams` conversion from request models
- HTTP response construction (`build_success_response`)
- Error mapping (service exception -> HTTPException)
- Pagination metadata construction (`PaginationMeta`)

### sections.py --> SectionService

Same pattern as tasks.py. All 6 handlers delegate to SectionService.

| Endpoint | Route Handler | Service Method | What Moves |
|----------|--------------|----------------|------------|
| `GET /sections/{gid}` | `get_section()` | `section_service.get_section()` | SDK get call |
| `POST /sections` | `create_section()` | `section_service.create_section()` | SDK create, MutationEvent |
| `PUT /sections/{gid}` | `update_section()` | `section_service.update_section()` | SDK update, project GID extraction, MutationEvent |
| `DELETE /sections/{gid}` | `delete_section()` | `section_service.delete_section()` | SDK delete, MutationEvent |
| `POST /sections/{gid}/tasks` | `add_task_to_section()` | `section_service.add_task()` | SDK add_task, MutationEvent |
| `POST /sections/{gid}/reorder` | `reorder_section()` | `section_service.reorder()` | Validation, SDK insert_section |

**What gets removed from sections.py**:
- All `MutationEvent` imports and construction (4 instances)
- Inline project GID extraction logic
- `MutationInvalidatorDep` from 4 handler signatures
- `from autom8_asana.cache.models.mutation_event import ...`

### query.py --> EntityService + QueryService (enhanced)

This is the most impactful wiring. The query route has the highest business-logic-to-HTTP ratio (70%).

| Logic Block | Current Lines | Target | Method |
|------------|---------------|--------|--------|
| Entity type validation | 15 lines x 2 endpoints | `EntityService` | `validate_entity_type()` |
| Field validation | `_validate_fields()` (15 lines) | `QueryService` (new method) | `validate_fields()` |
| Project GID resolution | 15 lines x 2 endpoints | `EntityService` | Part of `validate_entity_type()` -> `EntityContext.project_gid` |
| Bot PAT acquisition | 12 lines x 2 endpoints | `EntityService` | Part of `validate_entity_type()` -> `EntityContext.bot_pat` |
| Section resolution | `_resolve_section()` (35 lines) | `QueryService` (new method) | `resolve_section()` |
| Section predicate stripping | 20 lines inline | `QueryService` (new method) | `prepare_rows_request()` |
| Query execution (legacy) | 5 lines | Already in `EntityQueryService.query()` | No change |
| Query execution (rows) | 15 lines | `QueryService` (new method) | `execute_rows()` |

**Key observation**: `query.py` currently has two helper functions (`_get_queryable_entities()`, `_validate_fields()`) and one section resolver (`_resolve_section()`) that are module-level. These move into `QueryService` or `EntityService`.

**Post-wiring handler pattern for `query_entities()`**:

```python
@router.post("/{entity_type}")
async def query_entities(
    entity_type: str,
    request_body: QueryRequest,
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
    entity_service: EntityServiceDep,  # NEW
    query_service: QueryServiceDep,     # NEW (or keep existing factory pattern)
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")

    # 1. Entity validation (was 15 lines, now 4)
    try:
        ctx = entity_service.validate_entity_type(entity_type)
    except UnknownEntityError as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    except ServiceNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=e.to_dict())

    # 2. Field validation (was inline, now delegated)
    select_fields = request_body.select or DEFAULT_SELECT_FIELDS
    try:
        query_service.validate_fields(list(request_body.where.keys()), entity_type)
        query_service.validate_fields(select_fields, entity_type)
    except InvalidFieldError as e:
        raise HTTPException(status_code=422, detail=e.to_dict())

    # 3. Execute query (was 10 lines of try/except + client setup)
    try:
        async with AsanaClient(token=ctx.bot_pat) as client:
            result = await query_service.query(
                entity_type=entity_type,
                project_gid=ctx.project_gid,
                client=client,
                where=request_body.where,
                select=select_fields,
                limit=request_body.limit,
                offset=request_body.offset,
            )
    except CacheNotWarmError as e:
        raise HTTPException(status_code=503, detail={...})

    # 4. Response construction (stays in route -- HTTP concern)
    response = QueryResponse(data=result.data, meta=QueryMeta(...))
    response_obj = JSONResponse(content=response.model_dump())
    response_obj.headers["Deprecation"] = "true"
    ...
    return response_obj
```

**Estimated line reduction for query.py**: 665 -> ~350 lines (-47%)

### admin.py -- NOT in scope for I2

The admin route's business logic is cache management (refresh, rebuild, lambda invocation). This is not entity CRUD. It does not benefit from TaskService/SectionService/EntityService. Wiring it would require a new `CacheManagementService` which is not built. **Decision**: Exclude admin.py from I2. It can be addressed in I5 (API Main Decomposition) when the cache management endpoints are extracted.

### dataframes.py -- Deferred to I2 Sprint 2 (if time permits)

The dataframes route has significant complexity (schema resolution, Polars operations, SectionProxy hack, opt_fields duplication). The original TDD specified a `DataFrameService` that does not yet exist. Building it requires:
1. New service class (not yet written)
2. Schema resolution logic extraction
3. opt_fields deduplication
4. SectionProxy elimination (or formalization)

**Decision**: Defer to Sprint 2 of I2 as stretch goal. Sprint 1 covers tasks.py + sections.py + query.py which are the three routes with pre-built services.

---

## Dependencies.py Changes

### New Additions

```python
# --- Service Factories (I2 additions) ---

def get_entity_service(request: Request) -> EntityService:
    """Get EntityService singleton from app state.

    Lazy initialization: creates on first access, stores on app.state.
    EntityService wraps singleton registries (EntityRegistry,
    EntityProjectRegistry) and has no per-request state.
    """
    entity_service = getattr(request.app.state, "entity_service", None)
    if entity_service is None:
        from autom8_asana.core.entity_registry import get_registry
        from autom8_asana.services.entity_service import EntityService
        from autom8_asana.services.resolver import EntityProjectRegistry

        entity_service = EntityService(
            entity_registry=get_registry(),
            project_registry=EntityProjectRegistry.get_instance(),
        )
        request.app.state.entity_service = entity_service
    return entity_service


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


# --- Type Aliases ---
EntityServiceDep = Annotated[EntityService, Depends(get_entity_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
SectionServiceDep = Annotated[SectionService, Depends(get_section_service)]
```

### Lifecycle Rationale

| Service | Lifecycle | Reason |
|---------|-----------|--------|
| `EntityService` | Singleton (`app.state`) | Wraps singleton registries; no per-request state; thread-safe after construction |
| `TaskService` | Per-request | Receives `MutationInvalidator` from `app.state` (which itself is a singleton, but wrapping in a per-request service avoids sharing service state) |
| `SectionService` | Per-request | Same rationale as TaskService |
| `QueryService` | Keep existing factory pattern | `_get_query_service()` in query.py already works; no need to inject via `Depends()` until we have a reason |

### What Does NOT Change

- `AsanaClientDualMode` -- unchanged, still injected into route handlers
- `RequestId` -- unchanged
- `AuthContextDep` -- unchanged
- `MutationInvalidatorDep` -- remains for any routes that are not yet wired (admin.py uses it indirectly)

---

## Per-Route Migration Specifications

### tasks.py: Before/After Comparison

**Before** (`create_task` -- 35 lines of handler body):
```
1. Validate projects/workspace (4 lines)
2. Build kwargs dict (6 lines)
3. Call client.tasks.create_async (5 lines)
4. Extract project GIDs (1 line)
5. Construct MutationEvent (5 lines)
6. Call invalidator.fire_and_forget (1 line)
7. Return response (1 line)
```

**After** (`create_task` -- 12 lines of handler body):
```
1. Map CreateTaskRequest -> CreateTaskParams (1 line)
2. try: task = await task_service.create_task(client, params) (1 line)
3. except InvalidParameterError: raise HTTPException (2 lines)
4. Return response (1 line)
```

**Reduction**: 35 -> 12 lines per mutation handler. With 10 mutation handlers, that is approximately 230 lines removed.

**Net reduction for tasks.py**: 736 -> ~400 lines (-45%)

### sections.py: Before/After Comparison

**Before** (`update_section` -- 19 lines):
```
1. Call client.sections.update_async (1 line)
2. Extract project GID from response (5 lines)
3. Construct MutationEvent (5 lines)
4. Call invalidator.fire_and_forget (1 line)
5. Return response (1 line)
```

**After** (`update_section` -- 5 lines):
```
1. section = await section_service.update_section(client, gid, body.name)
2. Return response (1 line)
```

**Net reduction for sections.py**: 288 -> ~160 lines (-44%)

### query.py: Before/After Comparison

**Removed functions**: `_get_queryable_entities()`, `_validate_fields()`, `_resolve_section()` (total ~65 lines)

**`query_entities()` reduction**: 180 lines -> ~80 lines
- Entity validation: 15 lines -> 4 lines (delegated to EntityService)
- Field validation: 6 lines -> 4 lines (delegated to QueryService)
- Project GID resolution: 15 lines -> 0 (part of EntityContext)
- Bot PAT acquisition: 12 lines -> 0 (part of EntityContext)
- Response construction + logging: stays the same

**`query_rows()` reduction**: 160 lines -> ~90 lines
- Same entity/project/bot_pat consolidation
- Section resolution: 8 lines -> 3 lines (delegated)
- Predicate stripping: 20 lines -> 3 lines (delegated)

**Net reduction for query.py**: 665 -> ~350 lines (-47%)

---

## Migration Strategy

### Approach: Incremental Per-Route, One PR Per Route Module

Each route module is migrated independently with its own PR. This enables per-route rollback without affecting other routes.

### Ordering

```
Sprint 1 (I2-S1):
  1. dependencies.py additions (foundation -- enables all subsequent work)
  2. tasks.py wiring (simplest, most handlers, highest LOC savings)
  3. sections.py wiring (simple, mirrors tasks pattern exactly)

Sprint 2 (I2-S2):
  4. query.py wiring (most complex, but highest quality improvement)
  5. dataframes.py wiring (stretch goal -- requires new DataFrameService)
```

### Why This Order

1. **dependencies.py first**: All subsequent routes need the DI factories. Zero risk -- pure additions, no behavior change.

2. **tasks.py second**: 14 handlers, all following identical pattern. One pattern established here applies everywhere. If the TaskService has a bug (method signature mismatch, missing edge case), we find it immediately across 14 call sites.

3. **sections.py third**: 6 handlers, identical pattern to tasks.py. Fast to wire after tasks.py establishes the pattern.

4. **query.py fourth**: Most complex wiring. Benefits from lessons learned in tasks/sections. Requires minor QueryService enhancements (`validate_fields`, `resolve_section`).

### Rollback Plan

Each route migration is a single commit. Rollback is `git revert <commit>`.

**Pre-wiring safeguard**: Before modifying any route, run the full test suite and record the baseline:
```bash
.venv/bin/pytest tests/api/ -x -q --timeout=60
```

**Post-wiring verification**: After each route migration, the same test suite must pass identically.

**Emergency rollback**: If a wired route shows issues in production, revert the specific route commit. The service modules are additive -- they exist whether or not routes use them. Reverting a route migration restores the inline business logic with zero side effects on other routes.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Service method signature mismatch** -- TaskService methods expect different params than route handlers provide | Medium | Low | Service methods were built by reading route code. Each service test verifies the full call signature. |
| **Error format regression** -- Service `to_dict()` produces different JSON than current inline HTTPException detail dicts | Medium | Medium | `errors.py` was designed to match existing formats. Snapshot tests on error responses will catch mismatches. Add explicit error format assertions to existing API tests. |
| **Pagination metadata loss** -- ServiceListResult lacks fields that PaginationMeta needs | Low | Medium | ServiceListResult has `data`, `has_more`, `next_offset`. PaginationMeta needs `limit` (available from request), `has_more`, `next_offset`. No data loss. |
| **MutationInvalidator lifecycle change** -- Currently injected directly into handlers; now wrapped by service | Low | Low | TaskService/SectionService receive the same invalidator instance from the same `get_mutation_invalidator()` factory. The invalidator reference is just passed through. |
| **Query route EntityContext integration** -- query.py currently does its own bot PAT / project GID lookup; switching to EntityService may have subtle behavior differences | Medium | Medium | EntityService wraps the same `EntityProjectRegistry` and `get_bot_pat()` calls. The difference is consolidation, not new logic. Unit test EntityService against edge cases (no project, no bot PAT). |
| **Import cycle from dependencies.py -> services -> cache -> ...** | Low | Low | All service imports in `dependencies.py` use lazy imports inside factory functions (existing pattern for `get_mutation_invalidator`). |

---

## Success Criteria

| ID | Criterion | Measurement | Target |
|----|-----------|-------------|--------|
| SC-1 | `tasks.py` line count | `wc -l` | <= 420 lines (from 736, -43%) |
| SC-2 | `sections.py` line count | `wc -l` | <= 170 lines (from 288, -41%) |
| SC-3 | `query.py` line count | `wc -l` | <= 380 lines (from 665, -43%) |
| SC-4 | MutationEvent construction in routes | `grep -c "MutationEvent(" api/routes/` | 0 occurrences |
| SC-5 | `extract_project_gids` in routes | `grep -c "extract_project_gids" api/routes/` | 0 occurrences |
| SC-6 | All existing API tests pass | `.venv/bin/pytest tests/api/ -x -q --timeout=60` | Green, zero failures |
| SC-7 | All existing service tests pass | `.venv/bin/pytest tests/unit/services/ -x -q --timeout=60` | Green, zero failures |
| SC-8 | No HTTPException in service layer | `grep -r "HTTPException" services/` | 0 occurrences |
| SC-9 | EntityService used for entity resolution in query.py | Code review: no direct `EntityProjectRegistry`/`get_bot_pat()` in query.py | Verified |
| SC-10 | `_get_queryable_entities()` and `_validate_fields()` removed from query.py | `grep` in query.py | 0 occurrences |
| SC-11 | `_resolve_section()` removed from query.py | `grep` in query.py | 0 occurrences (logic moved to QueryService) |
| SC-12 | `dependencies.py` exports service type aliases | Code review | `TaskServiceDep`, `SectionServiceDep`, `EntityServiceDep` present |

---

## Sprint Plan

### Sprint 1 (I2-S1): Tasks + Sections Wiring

**Duration**: 3-5 days
**Commits**: 5 atomic commits

| Commit | Scope | Files Modified | Risk |
|--------|-------|---------------|------|
| C1 | Add service DI factories to dependencies.py | `api/dependencies.py` | None (additive only) |
| C2 | Add error mapping utility to a shared location | `api/routes/_error_mapping.py` (new) or inline in each route | None (additive only) |
| C3 | Wire tasks.py to TaskService | `api/routes/tasks.py` | Low (14 handlers, all identical pattern) |
| C4 | Wire sections.py to SectionService | `api/routes/sections.py` | Low (6 handlers, identical to tasks pattern) |
| C5 | Remove orphan marker comments from service modules | `services/task_service.py`, `services/section_service.py` | None (comment removal) |

**Verification gate**: Full test suite pass after each commit.

### Sprint 2 (I2-S2): Query Wiring + QueryService Enhancement

**Duration**: 3-5 days
**Commits**: 4-5 atomic commits

| Commit | Scope | Files Modified | Risk |
|--------|-------|---------------|------|
| C6 | Add `validate_fields()` to QueryService | `services/query_service.py`, new tests | Low (extracted from existing code) |
| C7 | Add `resolve_section()` to QueryService | `services/query_service.py`, new tests | Medium (S3/manifest fallback logic) |
| C8 | Wire query.py `query_entities()` to EntityService + QueryService | `api/routes/query.py` | Medium (most complex endpoint) |
| C9 | Wire query.py `query_rows()` to EntityService + QueryService | `api/routes/query.py` | Medium (section stripping logic) |
| C10 | Remove `_get_queryable_entities()`, `_validate_fields()`, `_resolve_section()` from query.py | `api/routes/query.py` | Low (dead code removal after C8-C9) |

**Verification gate**: Full test suite pass. Specific attention to `tests/api/test_routes_query_rows.py` and `tests/api/test_routes_query_aggregate.py`.

---

## ADRs

### ADR-I2-001: Skip protocols.py, Use Concrete Classes

**Context**: TDD-SERVICE-LAYER-001 specified `services/protocols.py` with Protocol interfaces for all services. The service implementations were built without protocols. Adding protocols now would mean every service has two files (protocol + implementation) with no second implementation to justify the indirection.

**Decision**: Do not create `services/protocols.py`. Use concrete service classes directly in type annotations.

**Rationale**:
- Only one implementation of each service exists
- Protocol extraction is a 15-minute refactor if a second implementation is needed
- Concrete types provide better IDE support (jump to definition, autocomplete)
- Test mocking works fine with `MagicMock` / `AsyncMock` regardless of protocols

**Consequences**:
- Positive: Less code, simpler dependency graph
- Negative: If a second implementation is needed, a small refactor is required
- Acceptable: YAGNI principle applies

### ADR-I2-002: Defer DataFrameService to Stretch Goal

**Context**: The `dataframes.py` route has significant complexity (schema resolution with global state, Polars operations, SectionProxy hack, duplicated opt_fields). No `DataFrameService` implementation exists yet.

**Decision**: Defer DataFrameService extraction to Sprint 2 stretch goal. If Sprint 2 schedule is tight, defer entirely to I5 (API Main Decomposition).

**Rationale**:
- Tasks, sections, and query routes already have built service modules. Wiring them is mechanical.
- DataFrameService requires new implementation work, not just wiring.
- The `dataframes.py` route is functional and has existing tests.
- I5 will restructure the API layer anyway; extracting DataFrameService then is equally valid.

**Consequences**:
- Positive: I2 scope is predictable and completable in 2 sprints
- Negative: dataframes.py retains inline business logic for now
- Acceptable: The route works; extraction is an improvement, not a fix

### ADR-I2-003: Error Mapping via get_status_for_error()

**Context**: The original TDD specified a `SERVICE_ERROR_MAP` dict and `map_service_error()` function. The implemented `errors.py` has a richer version: `get_status_for_error()` that walks the MRO, plus `status_hint` on each error class.

**Decision**: Use `get_status_for_error()` from `services/errors.py` for all route-level error mapping. Do not create a separate `_error_mapping.py` module.

**Rationale**:
- `get_status_for_error()` already handles the MRO walk correctly
- `status_hint` provides sensible defaults for unmapped error types
- `to_dict()` on each error class produces the right JSON format
- A central error mapper would duplicate what `errors.py` already provides

**Consequences**:
- Route handlers use a consistent 3-line pattern:
  ```python
  except ServiceError as e:
      raise HTTPException(
          status_code=get_status_for_error(e),
          detail=e.to_dict(),
      )
  ```

### ADR-I2-004: Exclude admin.py from I2 Scope

**Context**: The admin route manages cache refresh operations (force rebuild, incremental rebuild, Lambda invocation). Its business logic is cache management, not entity CRUD.

**Decision**: Exclude `admin.py` from I2. It does not benefit from EntityService/TaskService/SectionService.

**Rationale**:
- admin.py does not perform entity operations
- It would require a new `CacheManagementService` (not built)
- I5 (API Main Decomposition) will extract admin endpoints to dedicated route modules
- Extracting admin.py logic into a service during I5 is more natural

**Consequences**:
- admin.py retains inline business logic
- This is acceptable: admin.py is a low-traffic operational endpoint, not a hot path

---

## Attestation Table

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| This addendum | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/TDD-I2-service-layer-wiring-review.md` | Written |
| Original TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-service-layer-extraction.md` | Read |
| Deferred work roadmap | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/deferred-work-roadmap.md` | Read |
| Spike S0-003 | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/spike-S0-003-entity-workflow.md` | Read |
| EntityService | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/entity_service.py` | Read |
| TaskService | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/task_service.py` | Read |
| SectionService | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/section_service.py` | Read |
| EntityContext | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/entity_context.py` | Read |
| Service errors | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | Read |
| QueryService | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py` | Read |
| Route: tasks.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/tasks.py` | Read |
| Route: sections.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/sections.py` | Read |
| Route: query.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/query.py` | Read |
| Route: dataframes.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/dataframes.py` | Read |
| Route: admin.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/admin.py` | Read |
| Dependencies | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/dependencies.py` | Read |
| EntityRegistry (B1) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/entity_registry.py` | Read |
| MutationInvalidator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/mutation_invalidator.py` | Read |

---

**END OF TDD ADDENDUM**
