# I2 Straw-Man Analysis: What's Broken in TDD-SERVICE-LAYER-001

**Date**: 2026-02-15
**Analyst**: Architect (straw-man challenger)
**TDD Under Review**: TDD-SERVICE-LAYER-001, dated 2026-02-04
**Codebase State Delta**: 11 days of active development since TDD authorship

---

## Executive Summary

**The TDD is approximately 60% obsolete.** Two of its four extraction targets (tasks, sections) are already fully implemented and wired. The Attestation Table references two deleted file paths. The remaining two targets (query, dataframes) are partially done for query and untouched for dataframes. The TDD's framing as a monolithic extraction from a 1466-line main.py is completely stale -- that decomposition shipped 10 days ago as I5. The document is still useful as a design reference for the *remaining* QueryService enhancement and DataFrameService extraction, but executing it as-written would duplicate work that already exists and reference files that no longer exist at the stated paths.

---

## A. Stale References -- 11 outdated references

| # | TDD Section/Line | Stale Reference | Current Reality |
|---|---|---|---|
| 1 | Problem Statement, line 75 | `api/main.py` contains `_preload_dataframe_cache_progressive` | Function moved to `api/preload/progressive.py` as part of I5 decomposition |
| 2 | Problem Statement, line 66 | `api/routes/query.py (666 lines)` | query.py is now 372 lines (44% reduction already happened) |
| 3 | Problem Statement, line 67 | `api/routes/tasks.py (737 lines)` | tasks.py is now 578 lines but already delegates to TaskService -- it is a thin adapter |
| 4 | Problem Statement, line 68 | `api/routes/sections.py (289 lines)` | sections.py is now 224 lines and already delegates to SectionService |
| 5 | Problem Statement, line 69 | `api/routes/dataframes.py (554 lines)` | dataframes.py is 556 lines -- essentially unchanged (this target remains valid) |
| 6 | Attestation Table, line 1301 | `cache/mutation_invalidator.py` path | File is at `cache/integration/mutation_invalidator.py` (moved during cache reorg) |
| 7 | Attestation Table, line 1302 | `cache/mutation_event.py` path | File is at `cache/models/mutation_event.py` (moved during cache reorg) |
| 8 | Solution Summary, line 46 | `services/protocols.py` to be created | File was never created. No protocols exist. The Protocol pattern from ADR-SLE-001 is not implemented |
| 9 | Migration Plan Phase 1, line 961 | `services/errors.py` to be created | Already exists with a RICHER hierarchy than the TDD specified (adds EntityNotFoundError, EntityValidationError, NoValidFieldsError, TaskNotFoundError, EntityTypeMismatchError, UnknownSectionError, get_status_for_error()) |
| 10 | DI Wiring, line 731 | `get_query_service()` factory in dependencies.py | Not implemented. dependencies.py has no QueryService or DataFrameService factories |
| 11 | DI Wiring, line 753-764 | `QueryServiceDep`, `DataFrameServiceDep` type aliases | Not implemented. Only `EntityServiceDep`, `TaskServiceDep`, `SectionServiceDep` exist |

**Verdict**: The Attestation Table alone has 2 broken file paths. The Problem Statement line counts are wrong for 3 of 4 modules. The Solution Summary references an artifact (protocols.py) that was decided against in practice. Roughly 40% of the TDD's concrete code references point to incorrect locations or non-existent artifacts.

---

## B. Scope Mismatch -- SEVERE

### What the TDD Proposes vs. What Already Shipped

The TDD was written to solve two interleaved problems:
1. **Monolithic main.py** -- a 1466-line file with routes, middleware, and logic
2. **Business logic in route handlers** -- route handlers doing validation, orchestration, invalidation

Problem 1 was solved by I5 (api/main.py decomposition) which shipped Feb 5-8. main.py is now 197 lines. 17 route files were extracted. This invalidates the TDD's framing narrative.

Problem 2 was partially solved by the Phase 1+2 work that shipped alongside the route extraction:

| TDD Phase | Status | Evidence |
|-----------|--------|----------|
| Phase 1: Foundation | **COMPLETE** | `services/errors.py` (344 lines, richer than TDD spec), `services/entity_context.py`, `services/entity_service.py`, DI factories in `dependencies.py` for EntityService/TaskService/SectionService |
| Phase 2: TaskService + SectionService | **COMPLETE** | `services/task_service.py` (635 lines, all 13 operations), `services/section_service.py` (275 lines, all 6 operations), routes/tasks.py and routes/sections.py both delegate to services, `tests/unit/services/test_task_service.py` (516 lines), `tests/unit/services/test_section_service.py` (311 lines) |
| Phase 3: QueryService Enhancement | **PARTIAL** | `query_service.py` has `validate_fields()` and `resolve_section()` as module-level functions. `query.py` uses `EntityServiceDep` for entity validation. BUT: QueryService is NOT injected via DI -- `query.py` still calls `_get_query_service()` inline and `validate_fields()` / `resolve_section()` as bare functions |
| Phase 4: DataFrameService | **NOT STARTED** | No `dataframe_service.py` exists. `dataframes.py` still has all business logic inline (schema resolution, opt_fields, DataFrame building, content negotiation) |

### The LOC Reduction Targets

The TDD does not state explicit percentage targets. However, the implicit goal is "route handlers become thin adapters (<30 lines per endpoint)" (SC-1). Current status:

| Route File | Current Lines | Thin Adapter? | SC-1 Met? |
|------------|--------------|---------------|-----------|
| tasks.py | 578 lines, 16 endpoints | YES -- each endpoint is 15-25 lines, delegates to TaskService | YES |
| sections.py | 224 lines, 6 endpoints | YES -- each endpoint is 15-20 lines, delegates to SectionService | YES |
| query.py | 372 lines, 2 endpoints | MIXED -- entity validation delegates but query orchestration is still inline (~80 lines per endpoint) | NO |
| dataframes.py | 556 lines, 2 endpoints | NO -- all logic inline, endpoints are ~180 lines each | NO |

### Did the Decomposition Already Accomplish the TDD Goals?

For tasks and sections: **yes, fully**. The TDD's Phase 2 is done.

For query: **partially**. Entity validation is extracted but query orchestration and field validation are not injected via DI.

For dataframes: **no**. This is the one target where the TDD is still fully applicable.

---

## C. Implementation Gaps -- ~55% actually implemented

### Module-by-Module Reality Check

| Module | TDD Specifies | Actually Exists | Gap |
|--------|--------------|-----------------|-----|
| `services/protocols.py` | 5 Protocol classes | File does not exist | 100% gap -- decision was apparently made to skip Protocols entirely |
| `services/errors.py` | 6 exception classes + SERVICE_ERROR_MAP | 13 exception classes + `get_status_for_error()` MRO walker | Exceeds spec (good) |
| `services/entity_context.py` | EntityContext dataclass | Exists, matches spec | 0% gap |
| `services/entity_service.py` | EntityService with validate + get_queryable | Exists, matches spec | 0% gap |
| `services/task_service.py` | TaskService with CRUD + invalidation | Exists, all 13 operations | 0% gap |
| `services/section_service.py` | SectionService with CRUD + invalidation | Exists, all 6 operations | 0% gap |
| `services/query_service.py` | QueryService extending EntityQueryService with validate_fields, resolve_section, prepare_rows_request, query_rows | `validate_fields()` and `resolve_section()` exist as module-level functions, not as methods on a QueryService class | 60% gap -- functions exist but not as class methods, not injected via DI |
| `services/dataframe_service.py` | DataFrameService with schema resolution + build | File does not exist | 100% gap |
| `api/dependencies.py` DI | 5 service factories + 5 type aliases | 3 service factories + 3 type aliases (Entity, Task, Section only) | 40% gap -- no QueryServiceDep or DataFrameServiceDep |

### Dependencies on Deleted/Moved APIs

The existing service implementations import from correct paths:
- `task_service.py` imports `MutationEvent` from `cache.models.mutation_event` (correct post-reorg path)
- `section_service.py` imports from `cache.models.mutation_event` (correct)
- `entity_service.py` imports from `core.entity_registry` (correct)

No circular dependency issues detected between services and routes. The TYPE_CHECKING guard pattern is used consistently.

### Critical Finding: query_v2.py is NOT Using EntityService

`query_v2.py` (294 lines) still uses the old inline pattern:

```python
# query_v2.py lines 69-117 -- entity validation is INLINE, not delegated
queryable = get_resolvable_entities()
if entity_type not in queryable:
    raise HTTPException(status_code=404, ...)

registry: EntityProjectRegistry | None = getattr(
    request.app.state, "entity_project_registry", None,
)
# ... 20 more lines of manual resolution
```

This is the EXACT pattern the TDD exists to eliminate. It appears query_v2.py was created AFTER the TDD but BEFORE the EntityService wiring was applied to query.py. The TDD does not even mention query_v2.py because it did not exist on 2026-02-04.

---

## D. Hidden Complexity -- 6 non-extractable concerns

### 1. Content Negotiation in dataframes.py (HTTP-layer concern)

The TDD correctly identifies this as staying in the route (line 165: "Stays in route"). However, the actual dataframes.py has ~60 lines of content negotiation logic including Polars JSON serialization, StringIO buffer management, and response envelope wrapping. This is not trivially thin.

### 2. SectionProxy Hack in dataframes.py (lines 499-505)

```python
class SectionProxy:
    def __init__(self, gid: str, project_gid: str, tasks: list[Task]):
        self.gid = gid
        self.project = {"gid": project_gid}
        self.tasks = tasks
```

This inline class definition exists because `SectionDataFrameBuilder` expects a section object with specific attributes. A DataFrameService extraction would need to either: (a) keep this hack, (b) refactor SectionDataFrameBuilder to accept primitives, or (c) create a proper adapter. The TDD does not address this.

### 3. Two Different DataFrame Build Paths

`get_project_dataframe()` uses `DataFrameViewPlugin._extract_rows_async()` while `get_section_dataframe()` uses `SectionDataFrameBuilder.build()`. These are fundamentally different code paths with different dependencies (UnifiedTaskStore + resolver vs. SectionDataFrameBuilder). A DataFrameService would need to abstract over both, which is more complex than the TDD's unified `build_project_dataframe`/`build_section_dataframe` signatures suggest.

### 4. query.py Deprecation Headers (lines 240-245)

The legacy query endpoint adds `Deprecation`, `Sunset`, and `Link` headers. These are HTTP concerns that belong in the route, but the current logic interleaves them with response construction. A thin adapter needs to handle this without the extraction feeling incomplete.

### 5. query.py Section Predicate Stripping (lines 311-322)

The section predicate conflict resolution (`_has_section_pred` + `strip_section_predicates`) is business logic that modifies the request body before passing to QueryEngine. This is firmly in service territory but depends on query model internals (`RowsRequest.model_copy`).

### 6. query_v2.py Section Index Construction (lines 120-131)

The manifest-first, enum-fallback section index construction is duplicated between query.py (via `resolve_section()` module function) and query_v2.py (inline). query_v2.py also passes `entity_project_registry` to `engine.execute_rows()` -- a parameter that query.py's version does not use. This API surface inconsistency would need to be resolved during service extraction.

### Already-Wired Services That Set Precedent

| Service | Pattern | Conflicts with TDD? |
|---------|---------|---------------------|
| `field_write_service.py` | Receives `client` and `write_registry` in constructor, `mutation_invalidator` as method parameter | CONFLICTS -- TDD says invalidator should be constructor-injected (ADR-SLE-002), but FieldWriteService passes it per-call |
| `universal_strategy.py` | Factory function `get_universal_strategy(entity_type)`, no DI | Does not conflict but is not integrated into the TDD's DI model |
| `query_service.py` (validate_fields, resolve_section) | Module-level functions, not class methods | CONFLICTS -- TDD specifies these as QueryService methods |

---

## E. Risk Assessment

### Blast Radius

| Remaining Work | Files Modified | Tests at Risk |
|----------------|---------------|---------------|
| QueryService DI wiring | query.py, dependencies.py, query_service.py | `tests/api/test_routes_query.py`, `tests/unit/services/test_query_service.py` |
| query_v2.py service extraction | query_v2.py, dependencies.py | `tests/api/test_routes_query_rows.py`, `tests/api/test_routes_query_aggregate.py` |
| DataFrameService extraction | dataframes.py, new dataframe_service.py, dependencies.py | `tests/api/test_routes_dataframes.py` (1020 lines) |

The DataFrameService extraction has the highest risk because:
1. `test_routes_dataframes.py` is 1020 lines -- substantial test surface
2. Two fundamentally different build paths (ViewPlugin vs SectionDataFrameBuilder)
3. Module-level cached state (`_schema_mapping`, `_valid_schemas`) needs lifecycle management
4. The route returns `Response` objects with custom media types, not Pydantic models

### Test Coupling

There are NO unit tests for TaskService route wiring (`tests/api/test_routes_tasks.py` does not exist). There ARE route tests for:
- `test_routes_sections.py` (319 lines) -- tests section routes end-to-end
- `test_routes_dataframes.py` (1020 lines) -- heavy coverage of DataFrame routes
- `test_routes_query.py` (exists) -- covers legacy + rows query
- `test_routes_query_rows.py` (exists) -- covers query_v2 rows
- `test_routes_query_aggregate.py` (exists) -- covers query_v2 aggregate

### Performance Regression Risk

LOW for query (one indirection layer, same cache path).
MEDIUM for dataframes -- adding a service layer between the route and `DataFrameViewPlugin._extract_rows_async()` could inadvertently change how the async context or UnifiedTaskStore lifecycle works. The current code creates `InMemoryCacheProvider()` per-request in the route; moving this to a service needs to preserve that lifecycle.

---

## F. Alternative Paths

### Option 1: Declare Phase 1+2 Done, Revise TDD for Remaining Work Only

**Effort**: Low (document update)
**Risk**: Low
**Value**: Accurate documentation

The TDD should be updated to reflect that Phase 1 and Phase 2 are complete. A new TDD (or TDD revision) should focus exclusively on:
- Phase 3 (QueryService DI wiring + query_v2.py alignment)
- Phase 4 (DataFrameService extraction)

### Option 2: Skip QueryService Class, Wire Module Functions

**Effort**: Very low
**Risk**: Very low
**Value**: 80% of Phase 3 value

`validate_fields()` and `resolve_section()` already exist as module-level functions in `query_service.py`. Rather than wrapping them in a class and injecting via DI, the route can continue importing them directly. The real value of the QueryService class (TDD line 487: "extends EntityQueryService") is questionable because EntityQueryService already works fine as a standalone.

This approach accepts that query.py already uses EntityServiceDep for entity validation (the highest-value extraction) and does not force the remaining logic into a class just for architectural purity.

### Option 3: Thin DataFrameService Without Full Schema Resolution

**Effort**: Medium
**Risk**: Medium
**Value**: 70% of Phase 4 value

Instead of extracting the full schema resolution + DataFrame build into a service, extract just the common pattern:
- Module-level `_get_schema()` becomes a service method
- opt_fields list becomes a class constant (TDD already proposes this)
- The actual DataFrame build call stays in the route because the two build paths are too different to abstract cleanly

This avoids the SectionProxy hack and the ViewPlugin vs SectionDataFrameBuilder divergence.

### Option 4: Do Nothing for query_v2.py

**Effort**: Zero
**Risk**: Zero
**Value**: Accept tech debt

query_v2.py has the old inline pattern but it is a newer, actively maintained endpoint. It was written after the TDD and was apparently deemed acceptable without service extraction. The 50 lines of entity resolution boilerplate are annoying but functional. The argument: if the developer who built query_v2.py did not feel compelled to use EntityService (which existed at the time), perhaps the extraction value is lower than the TDD assumes.

Counter-argument: query_v2.py may simply have been built in a rush and this is exactly the kind of duplication the TDD exists to prevent.

---

## Strongest Arguments AGAINST Proceeding As-Is

### 1. The TDD Would Cause Duplicate Work

Executing Phase 1 and Phase 2 as written would re-create `services/errors.py`, `services/entity_context.py`, `services/entity_service.py`, `services/task_service.py`, and `services/section_service.py` -- all of which already exist with richer implementations than the TDD specifies. An implementer following the TDD literally would either overwrite the existing (better) code or get confused about what to do.

### 2. protocols.py Was Never Created -- Is the Protocol Pattern Still Wanted?

The TDD dedicates an entire ADR (ADR-SLE-001) to using Protocols over ABCs. But in practice, the implemented services have no Protocol interfaces. The routes import concrete classes. The tests mock concrete classes. If Protocols were deemed unnecessary during Phase 1+2 implementation, the TDD should acknowledge this or the ADR should be revised. Proceeding with Protocols for QueryService and DataFrameService alone would create an inconsistency.

### 3. query_v2.py is a Blind Spot

The TDD does not mention `query_v2.py`, `entity_write.py`, `resolver.py`, `projects.py`, `users.py`, `workspaces.py`, or `webhooks.py` -- all route files that were created after the TDD. Of these, `query_v2.py` is the most critical because it duplicates exactly the pattern the TDD exists to eliminate (inline entity resolution, manual bot PAT acquisition, inline section index construction). Any revised plan needs to include query_v2.py or explicitly scope it out.

### 4. The DataFrameService Extraction is Under-Specified

The TDD's DataFrameService spec (lines 648-699) shows a clean interface with `build_project_dataframe()` and `build_section_dataframe()`. But the actual implementation would need to handle:
- Two different builder APIs (DataFrameViewPlugin vs SectionDataFrameBuilder)
- Per-request UnifiedTaskStore with InMemoryCacheProvider lifecycle
- Module-level schema caching with thread-safety concerns
- SectionProxy adapter class
- Polars import and schema construction

None of these are addressed in the TDD's code sketch. Phase 4 is the highest-risk phase and has the least design detail.

### 5. Success Criteria SC-7 is Already Met (for tasks/sections) But Not Measurable for the Full Scope

SC-7 states: "Grep for `MutationEvent(` in `api/routes/` returns zero hits." A grep confirms this is ALREADY true -- tasks.py and sections.py delegate all MutationEvent construction to their services. The other routes never constructed MutationEvents. So SC-7 is already met. SC-1 (<30 lines per endpoint) is met for tasks and sections but not for query or dataframes.

---

## Critical Questions the TDD Doesn't Answer

1. **Should query_v2.py use EntityServiceDep?** It currently uses the old pattern. Was this intentional or an oversight? This is the single most impactful question for Phase 3 scope.

2. **Should the Protocol pattern (ADR-SLE-001) be followed for remaining services?** It was skipped for Task/Section/Entity services. Creating Protocols only for Query/DataFrame would be inconsistent.

3. **How should DataFrameService handle the two divergent build paths?** ViewPlugin._extract_rows_async (project) vs SectionDataFrameBuilder.build (section) have different signatures, different input types, and different lifecycle requirements.

4. **Should the module-level schema cache in dataframes.py be moved into the service or kept as a module singleton?** The TDD implies service encapsulation but the cache has thread-safety properties that depend on module-level semantics.

5. **What happens to resolver.py (456 lines)?** It uses `get_resolvable_entities()` and `entity_project_registry` from app.state -- the same pattern as query_v2.py. The TDD does not scope it in, but it has the same duplication problem.

6. **What is the migration path for `field_write_service.py`'s invalidator pattern?** It passes `mutation_invalidator` as a method parameter, conflicting with ADR-SLE-002's constructor injection mandate. Should this be aligned or accepted as a variance?

7. **How does the existing `_get_query_service()` inline factory in query.py interact with the proposed DI-injected QueryServiceDep?** query.py line 112 creates an EntityQueryService inline. The TDD proposes replacing this with DI injection. But the current query.py already uses EntityServiceDep for entity validation -- so it would use two different DI patterns in the same handler.

---

## Recommendation

**Do not execute TDD-SERVICE-LAYER-001 as-is.** Issue a TDD revision (v2.0) that:

1. Marks Phase 1 and Phase 2 as COMPLETE with attestation
2. Drops `services/protocols.py` from scope (or makes an explicit decision to add them retroactively to all services)
3. Revises Phase 3 to include query_v2.py alongside query.py
4. Provides additional design detail for Phase 4's two divergent build paths
5. Updates all line counts, file paths, and the Attestation Table
6. Adds query_v2.py, entity_write.py, and resolver.py to the scope analysis (even if scoped out)
7. Reconciles FieldWriteService's invalidator pattern with ADR-SLE-002
8. Updates SUCCESS CRITERIA to reflect which ones are already met
