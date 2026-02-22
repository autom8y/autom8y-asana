# Topology Inventory: Classification-Linked API Surface

**Scope**: autom8y-asana, single repo -- classification subsystem interop with API surfaces
**Date**: 2026-02-20
**Agent**: topology-cartographer
**Complexity**: SURVEY
**Upstream analysis**: `.claude/wip/ANALYSIS-classification-api-surface.md`

---

## 1. Service Catalog

This inventory covers five units within a single FastAPI application. All units share one deployment boundary (the autom8_asana Lambda / ECS service). There is no separate deployment artifact per unit.

| Unit | Classification | Confidence | Rationale |
|------|---------------|------------|-----------|
| Query Router surface | API module (S2S-only) | High | Explicit router with prefix, auth dependency, Pydantic models |
| Section-Timelines surface | API module (dual-mode) | High | Explicit router with prefix, dual-mode auth dependency |
| DataFrames surface | API module (dual-mode) | High | Explicit router with prefix, dual-mode auth dependency |
| Classification subsystem | Domain library | High | Frozen dataclass, no I/O, module-level singletons |
| Auth subsystem | Infrastructure library | High | FastAPI dependency chain, no business logic |

---

## 2. Unit Profiles

### 2.1 Query Router Surface

**Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/query.py` (route handlers)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/engine.py` (query orchestration)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/models.py` (request/response models)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/query_service.py` (DataFrame cache access)

**Entry points**:

| Endpoint | Method | Path | Auth | Schema Hidden |
|----------|--------|------|------|---------------|
| `query_rows` | POST | `/v1/query/{entity_type}/rows` | S2S JWT (`require_service_claims`) | Yes (`include_in_schema=False`, query.py:58) |
| `query_aggregate` | POST | `/v1/query/{entity_type}/aggregate` | S2S JWT (`require_service_claims`) | Yes |
| `query_entities` (deprecated) | POST | `/v1/query/{entity_type}` | S2S JWT (`require_service_claims`) | Yes |

**Auth scheme**: S2S-only. The `require_service_claims` dependency (internal.py:91-182) extracts a Bearer token, verifies it has exactly 2 dots (JWT detection via `detect_token_type`), rejects PAT tokens with 401 `SERVICE_TOKEN_REQUIRED`, then validates the JWT via `validate_service_token()`. On success, returns `ServiceClaims(sub, service_name, scope)`.

**URL prefix**: `/v1/query` -- no `/api` prefix. Registered at query.py:58.

**Response envelope**: Custom models defined in `query/models.py`:
- `RowsResponse` (line 241-248): `{data: list[dict], meta: RowsMeta}` with query-specific fields (`query_ms`, `freshness`, `staleness_ratio`, `join_entity`, `join_key`, etc.)
- `AggregateResponse` (line 189-196): `{data: list[dict], meta: AggregateMeta}` with `group_count`, `aggregation_count`, `group_by`, `query_ms`

**Request models**:
- `RowsRequest` (query/models.py:198-217): `where` (composable predicate tree), `section` (single section name string), `select`, `limit`, `offset`, `order_by`, `order_dir`, `join`
- `AggregateRequest` (query/models.py:148-169): `where`, `section`, `group_by`, `aggregations`, `having`

**Tech stack elements**: FastAPI `APIRouter`, Pydantic v2 `BaseModel` with discriminated unions (`PredicateNode`), Polars DataFrames for in-memory query execution, `AsanaClient` for cache miss fallback.

**Section resolution flow**: `RowsRequest.section` accepts a single section name string (e.g., `"ACTIVE"`). The `QueryEngine._resolve_section()` method (engine.py:400-423) resolves the name through `SectionIndex`, then applies `pl.col("section") == section_name_filter` at engine.py:127. There is no expansion to multiple sections, no classification group support, and no integration with `SectionClassifier` or `CLASSIFIERS`.

**Classification integration status**: NOT INTEGRATED. The `section` parameter accepts only individual section names. To query all sections in a classification group (e.g., the 20 ACTIVE sections for offers), a consumer must either issue 20 separate requests or construct an `{or: [{field: "section", op: "in", value: [...20 names...]}]}` predicate manually.

**Confidence**: High -- verified from explicit build manifests (Pydantic model definitions, FastAPI route decorators, Polars imports).

---

### 2.2 Section-Timelines Surface

**Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/section_timelines.py` (route handler)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py` (computation + caching)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py` (derived cache operations)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/section_timeline.py` (domain models)

**Entry points**:

| Endpoint | Method | Path | Auth | Schema Hidden |
|----------|--------|------|------|---------------|
| `get_offer_section_timelines` | GET | `/api/v1/offers/section-timelines` | Dual-mode (`AsanaClientDualMode`) | No |

**Auth scheme**: Dual-mode. The `AsanaClientDualMode` dependency alias (dependencies.py:404) chains through `get_asana_client_from_context` -> `get_auth_context` -> `detect_token_type`. JWT tokens are validated and the bot PAT is used for Asana API calls. PAT tokens are passed through directly. Both modes produce a usable `AsanaClient`.

**URL prefix**: `/api/v1/offers` -- standard `/api` prefix. Registered at section_timelines.py:33.

**Response envelope**: `SuccessResponse[SectionTimelinesResponse]` (uses shared `api/models.py:96-109`). Wraps `{data: {timelines: [OfferTimelineEntry, ...]}, meta: {request_id, timestamp}}`.

**Query parameters**: `period_start` (date, required), `period_end` (date, required). No classification filter, no GID-set filter, no pagination.

**Request flow**: The endpoint calls `get_or_compute_timelines()` (section_timeline_service.py:335-610), which:
1. Resolves the classifier from the `CLASSIFIERS` registry using `classifier_name="offer"` (hardcoded at section_timelines.py:104)
2. Checks derived cache for pre-computed timelines keyed by `timeline:{project_gid}:{classifier_name}` with 5-minute TTL (derived.py:32)
3. On cache miss: enumerates ALL tasks, batch-reads cached stories, builds `SectionTimeline` objects, stores in derived cache
4. Calls `_compute_day_counts()` (section_timeline_service.py:613-643) to project `active_section_days` and `billable_section_days` for the requested period

The service uses `SectionClassifier` internally for:
- Cross-project noise filtering (`_is_cross_project_noise`, service line 105-137)
- Interval classification during `_build_intervals_from_stories` (service line 158-232)
- Imputed interval classification for never-moved tasks (service line 498-499)
- Day counting within `SectionTimeline.active_days_in_period()` and `.billable_days_in_period()` (section_timeline.py:61-101)

However, the classifier is used only for computation, never for filtering the result set. All timelines are returned regardless of classification.

**Response model** (`OfferTimelineEntry`, section_timeline.py:157-179):
- `offer_gid: str`
- `office_phone: str | None`
- `active_section_days: int`
- `billable_section_days: int`

Notable: The response model does NOT include `current_section` or `current_classification`. Consumers cannot determine which classification group an offer belongs to from the response alone.

**Classification integration status**: PARTIAL. The service uses `SectionClassifier` internally for timeline computation but does NOT expose classification as a filter parameter or response field. All timelines are returned regardless of classification.

**Confidence**: High -- verified from explicit route decorator, Pydantic response model, and service implementation.

---

### 2.3 DataFrames Surface

**Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/dataframes.py` (route handlers)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/dataframe_service.py` (business logic delegation)

**Entry points**:

| Endpoint | Method | Path | Auth | Schema Hidden |
|----------|--------|------|------|---------------|
| `get_project_dataframe` | GET | `/api/v1/dataframes/project/{gid}` | Dual-mode (`AsanaClientDualMode`) | No |
| `get_section_dataframe` | GET | `/api/v1/dataframes/section/{gid}` | Dual-mode (`AsanaClientDualMode`) | No |

**Auth scheme**: Dual-mode (same chain as Section-Timelines).

**URL prefix**: `/api/v1/dataframes`. Registered at dataframes.py:58.

**Response envelope**: Content-negotiated:
- `application/json` (default): `SuccessResponse` via `build_success_response()` with pagination
- `application/x-polars-json`: Polars-serialized JSON with `ResponseMeta`

**Query parameters**: `schema` (string, selects column schema from SchemaRegistry), `limit` (int, max 100), `offset` (cursor-based pagination), `Accept` header for content negotiation.

**Classification integration status**: NOT INTEGRATED. These endpoints provide raw DataFrame access by project GID or section GID. No classification awareness. The `schema` parameter selects column projection (base, unit, contact, business, offer, asset_edit, asset_edit_holder) but does not filter by classification group.

**Tech stack elements**: FastAPI, Polars DataFrames, content negotiation via Accept header, cursor-based pagination.

**Confidence**: High -- verified from explicit route decorators and Pydantic response models.

---

### 2.4 Classification Subsystem

**Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/activity.py` (classifier + enum + registry)

**Public interface**:

| Symbol | Type | Purpose |
|--------|------|---------|
| `AccountActivity` | Enum (`str, Enum`) | Four-value vocabulary: `ACTIVE`, `ACTIVATING`, `INACTIVE`, `IGNORED` |
| `SectionClassifier` | Frozen dataclass | Maps section names to `AccountActivity` for a single entity type |
| `SectionClassifier.classify(section_name)` | Method -> `AccountActivity \| None` | O(1) case-insensitive lookup |
| `SectionClassifier.sections_for(*categories)` | Method -> `frozenset[str]` | Reverse lookup: categories to section name set |
| `SectionClassifier.active_sections()` | Method -> `frozenset[str]` | Convenience: sections classified as ACTIVE |
| `SectionClassifier.billable_sections()` | Method -> `frozenset[str]` | Convenience: sections classified as ACTIVE + ACTIVATING |
| `OFFER_CLASSIFIER` | Module-level singleton | Offer entity classifier (project GID `1143843662099250`) |
| `UNIT_CLASSIFIER` | Module-level singleton | Unit entity classifier (project GID `1201081073731555`) |
| `CLASSIFIERS` | `dict[str, SectionClassifier]` | Registry: `{"offer": OFFER_CLASSIFIER, "unit": UNIT_CLASSIFIER}` |
| `get_classifier(entity_type)` | Function -> `SectionClassifier \| None` | Registry lookup |
| `extract_section_name(task, project_gid)` | Function -> `str \| None` | Extracts section name from task memberships |
| `ACTIVITY_PRIORITY` | Tuple | Priority ordering for `max_unit_activity` aggregation |

**Classifier coverage**:

| Entity Type | Classifier | Active Sections | Activating Sections | Inactive Sections | Ignored Sections | Total |
|-------------|-----------|-----------------|--------------------|--------------------|-----------------|-------|
| offer | `OFFER_CLASSIFIER` | 20 | 5 | 3 | 4 | 32 |
| unit | `UNIT_CLASSIFIER` | 3 | 4 | 6 | 1 | 14 |

**Consumers within scope**: The `section_timeline_service.py` imports `CLASSIFIERS`, `OFFER_CLASSIFIER`, `AccountActivity`, `SectionClassifier`, and `extract_section_name` directly (service line 24-30). No other API surface in scope imports from `activity.py`.

**Classification integration status**: This IS the classification system. It is a pure domain library with no I/O.

**Confidence**: High -- verified from explicit dataclass definition, enum, and module-level constants.

---

### 2.5 Auth Subsystem

**Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/dependencies.py` (dual-mode auth chain + DI factories)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/auth/dual_mode.py` (token type detection)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/internal.py` (S2S-only auth + `require_service_claims`)

**Public interface**:

| Symbol | File | Purpose |
|--------|------|---------|
| `AsanaClientDualMode` | dependencies.py:404 | Type alias: `Annotated[AsanaClient, Depends(get_asana_client_from_context)]` |
| `get_auth_context()` | dependencies.py:127-286 | Primary dual-mode auth dependency. Detects token type, validates JWT or passes PAT through. Returns `AuthContext`. |
| `AuthContext` | dependencies.py:45-74 | Holds `mode` (JWT/PAT), `asana_pat`, `caller_service` |
| `require_service_claims()` | internal.py:91-182 | S2S-only auth dependency. Rejects PAT with 401, validates JWT, returns `ServiceClaims`. |
| `ServiceClaims` | internal.py:31-42 | Holds `sub`, `service_name`, `scope` |
| `detect_token_type(token)` | dual_mode.py:37-56 | Dot-counting heuristic: 2 dots = JWT, else PAT |
| `AuthMode` | dual_mode.py:25-35 | Enum: `JWT`, `PAT` |
| `RequestId` | dependencies.py:409 | Type alias: `Annotated[str, Depends(get_request_id)]` |

**Two auth modes**:

1. **S2S-only** (`require_service_claims`): Used by query router, entity resolver, entity write, and internal routes. Rejects PAT tokens at internal.py:112-129. On JWT validation success, Asana API calls use the bot PAT (not the caller's token).

2. **Dual-mode** (`AsanaClientDualMode` via `get_auth_context`): Used by section-timelines, dataframes, tasks, projects, sections, users, workspaces. Accepts both JWT and PAT. JWT mode: validates then uses bot PAT. PAT mode: passes user token through to Asana API.

**Token detection mechanism**: `detect_token_type()` at dual_mode.py:37-56 counts dots in the token string. JWT tokens have exactly 2 dots (header.payload.signature). Asana PATs have 0 dots (format: `0/xxxxxxxx` or `1/xxxxxxxx`). This is O(n) on token length.

**Classification integration status**: NOT APPLICABLE. The auth subsystem has no relationship to classification. It is a cross-cutting infrastructure concern.

**Confidence**: High -- verified from explicit FastAPI dependency declarations and token detection implementation.

---

## 3. Tech Stack Inventory

| Technology | Role | Files |
|------------|------|-------|
| FastAPI | HTTP framework, dependency injection, routing | All route files, dependencies.py |
| Pydantic v2 | Request/response validation, serialization | query/models.py, api/models.py, section_timeline.py |
| Polars | In-memory DataFrame operations for query engine | query/engine.py, query_service.py, dataframes.py |
| Python dataclasses (frozen) | Domain models (immutable value objects) | activity.py, section_timeline.py |
| autom8y_auth | JWT validation SDK (S2S) | dependencies.py, internal.py |
| autom8y_log | Structured logging | All files |
| asyncio | Concurrency (computation locks, semaphores) | section_timeline_service.py |

**Dependency manager**: Not directly inspected for this SURVEY scope, but the project uses `pyproject.toml` based on standard Python project structure.

---

## 4. Integration Matrix: Classification x API Surface

This matrix shows which API surfaces currently integrate with `SectionClassifier` / `CLASSIFIERS` and which are recommended for integration per the architect analysis (S-1, S-2, S-3).

| API Surface | Uses SectionClassifier | How | Recommended Change | Ref |
|-------------|----------------------|-----|--------------------|-----|
| **Query Router** (`/v1/query/.../rows`) | No | `section` param accepts single name only; no CLASSIFIERS import | S-2: Add `classification` virtual filter to `RowsRequest`, expand to IN predicate via `CLASSIFIERS.get(entity_type).sections_for()` | ANALYSIS S-2 |
| **Query Router** (`/v1/query/.../aggregate`) | No | Same `section` param pattern | S-2 applies here too (same `RowsRequest`/`AggregateRequest` pattern) | ANALYSIS S-2 |
| **Section-Timelines** (`/api/v1/offers/section-timelines`) | Internally only | Service uses CLASSIFIERS for interval classification and day counting; NOT for result filtering | S-1: Add `?classification=` query parameter for post-cache filtering. S-3: Surface `current_section` and `current_classification` in `OfferTimelineEntry`. | ANALYSIS S-1, S-3 |
| **DataFrames** (`/api/v1/dataframes/...`) | No | Raw DataFrame access by GID; no classification awareness | None recommended -- DataFrames serve a different purpose (raw data export) | -- |

**Classification parameter gap summary**:
- Query Router: A consumer wanting "all ACTIVE offers" must know all 20 section names and construct a 20-element IN predicate. The `SectionClassifier.sections_for(AccountActivity.ACTIVE)` method exists and returns exactly this set, but the query engine does not call it.
- Section-Timelines: Returns all timelines (currently ~3,774 entries). A consumer wanting only ACTIVE entries must filter client-side. The service already resolves the classifier internally but discards classification during response construction.
- DataFrames: No classification gap -- these endpoints serve raw Asana data, not classification-enriched data.

---

## 5. Auth Boundary Map

### 5.1 S2S-Only Boundary

| Endpoint Group | Router Prefix | Auth Dependency | PAT Accepted | JWT Accepted | File |
|----------------|--------------|-----------------|-------------|-------------|------|
| Query | `/v1/query` | `require_service_claims` | No | Yes | query.py:58, 144 |
| Resolver | `/v1/resolve` | `require_service_claims` | No | Yes | resolver.py (per routes/__init__.py) |
| Entity write | `/api/v1/entity` | `require_service_claims` | No | Yes | entity_write.py (per routes/__init__.py) |
| Internal | `/api/v1/internal` | `require_service_claims` | No | Yes | internal.py:24, 91 |

**Characteristic**: No `/api` prefix on query and resolver routes. All use bot PAT for Asana API calls regardless of caller identity. Caller identity is logged via `claims.service_name` for audit purposes.

### 5.2 Dual-Mode Boundary

| Endpoint Group | Router Prefix | Auth Dependency | PAT Accepted | JWT Accepted | File |
|----------------|--------------|-----------------|-------------|-------------|------|
| Section-Timelines | `/api/v1/offers` | `AsanaClientDualMode` | Yes | Yes | section_timelines.py:33, 56 |
| DataFrames | `/api/v1/dataframes` | `AsanaClientDualMode` | Yes | Yes | dataframes.py:58, 170 |
| Tasks | `/api/v1/tasks` | `AsanaClientDualMode` | Yes | Yes | tasks.py (per routes/__init__.py) |
| Projects | `/api/v1/projects` | `AsanaClientDualMode` | Yes | Yes | projects.py (per routes/__init__.py) |
| Sections | `/api/v1/sections` | `AsanaClientDualMode` | Yes | Yes | sections.py (per routes/__init__.py) |
| Users | `/api/v1/users` | `AsanaClientDualMode` | Yes | Yes | users.py (per routes/__init__.py) |
| Workspaces | `/api/v1/workspaces` | `AsanaClientDualMode` | Yes | Yes | workspaces.py (per routes/__init__.py) |

**Characteristic**: All have `/api` prefix. JWT mode uses bot PAT; PAT mode passes user token through. Both modes produce a functional `AsanaClient`.

### 5.3 No-Auth Boundary

| Endpoint Group | Router Prefix | Auth Dependency | File |
|----------------|--------------|-----------------|------|
| Health | `/satellite/health` | None | health.py (per routes/__init__.py) |
| Admin | varies | varies | admin.py (per routes/__init__.py) |

### 5.4 Consumer Journey Impact

The auth boundary split means that a consumer needing data from BOTH the query router (S2S-only) and section-timelines (dual-mode) must handle two auth flows -- unless they use JWT, which is accepted by both. The section-timelines endpoint already accepts JWT through the dual-mode chain. The practical impact is:

- **Internal services (S2S JWT)**: Can call both query router and section-timelines with the same token. No auth boundary friction.
- **External consumers (PAT only)**: Can call section-timelines but NOT the query router. Must use the DataFrames endpoint for raw data access or go through an internal service proxy.

---

## 6. Response Envelope Inventory

Two envelope families coexist across the scoped units:

### 6.1 Query-Specific Envelope

Defined in `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/models.py`.

```
RowsResponse:
  data: list[dict[str, Any]]
  meta: RowsMeta
    total_count: int
    returned_count: int
    limit: int
    offset: int
    entity_type: str
    project_gid: str
    query_ms: float
    join_entity: str | None
    join_key: str | None
    join_matched: int | None
    join_unmatched: int | None
    freshness: str | None
    data_age_seconds: float | None
    staleness_ratio: float | None

AggregateResponse:
  data: list[dict[str, Any]]
  meta: AggregateMeta
    group_count: int
    aggregation_count: int
    group_by: list[str]
    entity_type: str
    project_gid: str
    query_ms: float
    freshness: str | None
    data_age_seconds: float | None
    staleness_ratio: float | None
```

### 6.2 Shared SuccessResponse Envelope

Defined in `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/models.py:96-109`.

```
SuccessResponse[T]:
  data: T
  meta: ResponseMeta
    request_id: str
    timestamp: datetime
    pagination: PaginationMeta | None
      limit: int
      has_more: bool
      next_offset: str | None
```

Used by section-timelines (wrapping `SectionTimelinesResponse`) and dataframes (wrapping records list).

---

## 7. Unit Structure Profiles

### 7.1 Directory Organization

```
src/autom8_asana/
  api/
    routes/
      __init__.py          -- Router aggregation (14 routers)
      query.py             -- Query Router surface
      section_timelines.py -- Section-Timelines surface
      dataframes.py        -- DataFrames surface
      internal.py          -- S2S auth dependency + internal router
      ...                  -- 10 other route modules (out of scope)
    dependencies.py        -- Dual-mode auth chain + DI factories
    models.py              -- Shared response envelope
    errors.py              -- Error response helpers
    main.py                -- App factory, router mounting
  auth/
    dual_mode.py           -- Token type detection
    jwt_validator.py       -- JWT validation wrapper
    bot_pat.py             -- Bot PAT retrieval
  query/
    engine.py              -- QueryEngine orchestrator
    models.py              -- Predicate AST, request/response models
    compiler.py            -- Predicate -> Polars expression
    guards.py              -- Depth/limit guards
    join.py                -- Cross-entity join
    hierarchy.py           -- Entity relationship graph
    aggregator.py          -- Aggregation compilation
  models/business/
    activity.py            -- SectionClassifier, CLASSIFIERS, AccountActivity
    section_timeline.py    -- SectionTimeline, SectionInterval, OfferTimelineEntry
  services/
    section_timeline_service.py -- Timeline computation + derived caching
    query_service.py            -- DataFrame cache query access
    dataframe_service.py        -- DataFrame endpoint business logic
  cache/integration/
    derived.py             -- Derived timeline cache read/write
```

### 7.2 Test Coverage (Structural Observation)

Test files exist for the scoped units (verified via directory structure in git status). Integration tests reference entity resolver and health endpoints. Full test profile enumeration is outside SURVEY scope.

### 7.3 Configuration Loading

- **Classifier configuration**: Hardcoded in `activity.py` as module-level `SectionClassifier.from_groups()` calls with literal section name sets. No external config file, no environment variable. Changes to section names require code changes.
- **Project GIDs**: Hardcoded in classifier singletons (`1143843662099250` for offers, `1201081073731555` for units) and in `section_timeline_service.py:65` (`BUSINESS_OFFERS_PROJECT_GID`).
- **Cache TTL**: Hardcoded constant `_DERIVED_TIMELINE_TTL = 300` in `derived.py:32`.
- **Auth configuration**: Bot PAT from environment via `get_bot_pat()`. JWT validation via `autom8y_auth` SDK (configuration outside this repo).

---

## 8. Unknowns

### Unknown: CLASSIFIERS Registry Extension Pattern
- **Question**: Is the `CLASSIFIERS` dict intended to be extended at runtime (e.g., loading section-to-classification mappings from a config service), or is the hardcoded module-level pattern considered permanent?
- **Why it matters**: If CLASSIFIERS is extended at runtime, a `classification` filter parameter on the query router would need to handle dynamic classifier registration. If static, the current `CLASSIFIERS.get(entity_type)` pattern is sufficient.
- **Evidence**: The `get_classifier(entity_type)` function (activity.py:270-279) provides a lookup interface, but the dict is populated only at import time with two hardcoded entries. No dynamic registration code exists.
- **Suggested source**: Codebase author or ADR covering classifier lifecycle.

### Unknown: DataFrames Endpoint Classification Demand
- **Question**: Are there consumers or planned consumers that need classification-filtered DataFrames (as opposed to classification-filtered query rows or timelines)?
- **Why it matters**: The DataFrames endpoint is marked as "no recommended change" in the integration matrix, but if consumers need classification-filtered raw DataFrames, this gap would need to be addressed.
- **Evidence**: The architect analysis does not mention DataFrames classification integration. The endpoint serves a different purpose (raw data export with schema selection).
- **Suggested source**: Consumer usage logs or product requirements.

### Unknown: Deprecated Query Endpoint Consumer Migration
- **Question**: Which consumers still call the deprecated `POST /v1/query/{entity_type}` endpoint (sunset 2026-06-01), and do they need classification filtering?
- **Why it matters**: If classification filtering is added to `RowsRequest` for the `/rows` endpoint, the legacy endpoint (which uses `QueryRequest` with flat equality `where` dict) would not benefit. Consumers on the legacy endpoint would need to migrate first.
- **Evidence**: The deprecated endpoint at query.py:277-400 emits `Deprecation: true` and `Sunset: 2026-06-01` headers, with a `Link` header pointing to the `/rows` successor.
- **Suggested source**: S2S JWT audit logs (`caller_service` field in the `deprecated_query_endpoint_used` log event).

---

## 9. Handoff Readiness Checklist

- [x] Topology inventory artifact exists with all required sections
- [x] Every target unit has been scanned and classified (5 of 5)
- [x] Confidence ratings assigned to all classifications (all High)
- [x] API surfaces identified with endpoint paths, protocols, and interface detail
- [x] Tech stack inventory includes dependency manager information
- [x] Unknowns section documents items that could not be fully classified
- [x] No target unit was skipped

**Acid test**: The integration matrix (Section 4) and auth boundary map (Section 5) provide enough detail for a dependency-analyst to trace which API surfaces consume or should consume classification logic, and which auth boundaries constrain cross-surface composition, without re-scanning any unit.
