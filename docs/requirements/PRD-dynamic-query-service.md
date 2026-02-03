# PRD: Dynamic Query Service

## Metadata

| Field | Value |
|-------|-------|
| **PRD ID** | PRD-dynamic-query-service |
| **Status** | Draft |
| **Created** | 2026-02-03 |
| **Author** | Requirements Analyst |
| **Impact** | high |
| **Impact Categories** | api_contract, data_model |
| **Supersedes** | PRD-entity-query-endpoint (flat equality filtering) |

---

## Overview

Replace the existing flat-equality `POST /v1/query/{entity_type}` endpoint with three focused endpoints powered by an AST-based predicate tree, schema-aware compilation, and section-scoped data access. The new endpoints are:

1. **POST /v1/query/{entity_type}/rows** -- Filtered row retrieval with composable predicate trees
2. **POST /v1/query/{entity_type}/aggregate** -- Grouped aggregations (sum, count, mean, min, max)
3. **POST /v1/query/{entity_type}/metric** -- Named metric computation via the existing MetricRegistry

All three endpoints operate over the pre-warmed DataFrame cache via `UniversalResolutionStrategy._get_dataframe()`, preserving the existing cache lifecycle (Memory -> S3 -> self-refresh -> circuit breaker). No new data sources are introduced.

---

## Background

### Current State

The existing `POST /v1/query/{entity_type}` endpoint (implemented in `src/autom8_asana/api/routes/query.py`) supports only flat equality filtering: a `where` dict of `field: value` pairs ANDed together. This works for simple "section = ACTIVE" queries but cannot express:

- Range conditions (`mrr > 1000`)
- Disjunctions (`section = ACTIVE OR section = ONBOARDING`)
- Negations (`vertical != "dental"`)
- Substring matching (`name contains "Smith"`)
- Grouped aggregations (`sum(mrr) group by vertical`)
- Named metric computations already defined in the MetricRegistry

### Why Three Endpoints

| Aspect | `/rows` | `/aggregate` | `/metric` |
|--------|---------|--------------|-----------|
| **Purpose** | Filtered row retrieval | Grouped aggregation | Named metric scalar |
| **Output shape** | List of entity dicts | List of group dicts with agg values | Single scalar + metadata |
| **Predicate support** | Full AST | Full AST (pre-agg filter) | Metric-defined (scope + expr) |
| **Pagination** | Yes (offset/limit) | No (full result) | No (single value) |
| **Consumer** | n8n workflows, dashboards | Reporting, summaries | CLI scripts, monitoring |

### Technical Foundation

| Component | Location | Role |
|-----------|----------|------|
| EntityQueryService | `services/query_service.py` | Cache access + Polars operations |
| SchemaRegistry | `dataframes/models/registry.py` | Column/dtype validation |
| ColumnDef | `dataframes/models/schema.py` | Per-column dtype + metadata |
| SectionIndex | `metrics/resolve.py` | Section name -> GID resolution |
| OfferSection | `models/business/sections.py` | Hardcoded section GIDs |
| MetricRegistry | `metrics/registry.py` | Named metric definitions |
| compute_metric | `metrics/compute.py` | Metric execution pipeline |
| require_service_claims | `api/routes/internal.py` | S2S JWT auth dependency |

---

## User Stories

### US-001: Filter Rows with Complex Predicates

**As an** n8n workflow developer
**I want to** query offers with conditions like "section = ACTIVE AND mrr > 1000"
**So that** I can build targeted automations without post-filtering large result sets

**Acceptance Criteria**:
- [ ] `POST /v1/query/offer/rows` accepts a predicate tree with AND/OR/NOT composition
- [ ] Comparison operators include eq, ne, gt, lt, gte, lte, in, not_in, contains, starts_with
- [ ] Predicates are validated against SchemaRegistry column definitions
- [ ] Incompatible operator/dtype combinations are rejected with a descriptive error
- [ ] Results include pagination (offset/limit) and total_count metadata

### US-002: Aggregate Data by Grouping

**As a** reporting dashboard consumer
**I want to** request grouped aggregations like "sum of mrr grouped by vertical"
**So that** I can render summary charts without downloading all rows

**Acceptance Criteria**:
- [ ] `POST /v1/query/offer/aggregate` accepts group_by columns and aggregation specs
- [ ] Supported aggregations: sum, count, mean, min, max
- [ ] Pre-aggregation filtering via the same predicate tree as /rows
- [ ] Response includes one row per group with aggregated values
- [ ] Full result returned (no pagination; result set is inherently small)

### US-003: Compute Named Metrics via API

**As a** monitoring service
**I want to** request a named metric (e.g., "active_mrr") via HTTP
**So that** I can integrate metric values into dashboards without running CLI scripts

**Acceptance Criteria**:
- [ ] `POST /v1/query/offer/metric` accepts a metric name from MetricRegistry
- [ ] Response includes the scalar result, metric metadata, and row count used
- [ ] Unknown metric names return a descriptive error with available metrics list
- [ ] Metric scope (section, dedup, filters) is applied exactly as in CLI compute_metric

### US-004: Section-Scoped Queries

**As an** API consumer
**I want to** scope any query to a named section (e.g., "Active") without knowing the GID
**So that** I can write readable queries without hardcoding Asana GIDs

**Acceptance Criteria**:
- [ ] All three endpoints accept an optional `section` parameter (human-readable name)
- [ ] Section name is resolved to GID via SectionIndex (manifest-first, enum fallback)
- [ ] Unknown section names return UNKNOWN_SECTION error
- [ ] Section filter is ANDed with the user's predicate tree
- [ ] Omitting section queries across all sections

### US-005: Backward-Compatible Migration

**As an** existing API consumer
**I want** the current `POST /v1/query/{entity_type}` endpoint to continue working
**So that** I can migrate to the new endpoints at my own pace

**Acceptance Criteria**:
- [ ] Existing endpoint continues to function with identical behavior
- [ ] Response includes a `Deprecation` header with sunset date
- [ ] Deprecation is logged for monitoring
- [ ] Migration guide documents mapping from old to new request format

### US-006: Flat-Array Predicate Sugar

**As an** API consumer
**I want to** pass a bare list of predicates without wrapping in an AND group
**So that** simple queries remain concise

**Acceptance Criteria**:
- [ ] A bare list of comparison predicates auto-wraps to `{"and": [...]}`
- [ ] Behavior is identical to explicit AND group
- [ ] This sugar is documented in the API schema

---

## Functional Requirements

### FR-001: Predicate AST Schema

The predicate tree is a recursive structure of group nodes (AND/OR/NOT) and leaf comparison nodes.

#### Leaf Node (Comparison)

```json
{
  "field": "mrr",
  "op": "gt",
  "value": 1000
}
```

#### Group Nodes

```json
{
  "and": [
    {"field": "section", "op": "eq", "value": "1143843662099256"},
    {"or": [
      {"field": "vertical", "op": "eq", "value": "dental"},
      {"field": "vertical", "op": "eq", "value": "medical"}
    ]}
  ]
}
```

#### NOT Node

```json
{
  "not": {"field": "vertical", "op": "eq", "value": "dental"}
}
```

#### Flat-Array Sugar

A bare list auto-wraps to AND:

```json
[
  {"field": "section", "op": "eq", "value": "1143843662099256"},
  {"field": "mrr", "op": "gt", "value": 1000}
]
```

is equivalent to:

```json
{
  "and": [
    {"field": "section", "op": "eq", "value": "1143843662099256"},
    {"field": "mrr", "op": "gt", "value": 1000}
  ]
}
```

**Priority**: MUST

### FR-002: Supported Operators

| Operator | Meaning | Applicable Dtypes |
|----------|---------|-------------------|
| `eq` | Equal | All |
| `ne` | Not equal | All |
| `gt` | Greater than | Utf8, Int64, Int32, Float64, Date, Datetime |
| `lt` | Less than | Utf8, Int64, Int32, Float64, Date, Datetime |
| `gte` | Greater or equal | Utf8, Int64, Int32, Float64, Date, Datetime |
| `lte` | Less or equal | Utf8, Int64, Int32, Float64, Date, Datetime |
| `in` | In set | All (value must be array) |
| `not_in` | Not in set | All (value must be array) |
| `contains` | Substring match | Utf8 only |
| `starts_with` | Prefix match | Utf8 only |

#### Operator x Dtype Compatibility Matrix

| Dtype | eq | ne | gt | lt | gte | lte | in | not_in | contains | starts_with |
|-------|----|----|----|----|-----|-----|----|--------|----------|-------------|
| Utf8 | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| Int64 | Y | Y | Y | Y | Y | Y | Y | Y | N | N |
| Int32 | Y | Y | Y | Y | Y | Y | Y | Y | N | N |
| Float64 | Y | Y | Y | Y | Y | Y | Y | Y | N | N |
| Boolean | Y | Y | N | N | N | N | Y | Y | N | N |
| Date | Y | Y | Y | Y | Y | Y | Y | Y | N | N |
| Datetime | Y | Y | Y | Y | Y | Y | Y | Y | N | N |
| List[Utf8] | N | N | N | N | N | N | N | N | N | N |
| Decimal | Y | Y | Y | Y | Y | Y | Y | Y | N | N |

**Note**: List[Utf8] columns (e.g., `tags`, `platforms`) are excluded from predicate filtering in Sprint 1. List-element predicates (e.g., "tags contains 'urgent'") are deferred to Sprint 2+.

**Priority**: MUST

### FR-003: Schema-Aware Compilation

Predicates are compiled to Polars expressions using SchemaRegistry dtype information:

1. **Field validation**: Each `field` in a leaf node must exist in the entity's schema (via `SchemaRegistry.get_schema(to_pascal_case(entity_type))`). Unknown fields produce `UNKNOWN_FIELD` error.
2. **Operator validation**: The operator must be compatible with the field's dtype per the matrix above. Incompatible pairs produce `INVALID_OPERATOR` error.
3. **Value coercion**: The JSON value is coerced to the column's Polars dtype before comparison. Coercion failures produce `COERCION_FAILED` error. Coercion rules:
   - String -> Utf8: passthrough
   - Number -> Int64/Int32/Float64: standard numeric cast
   - String -> Date: ISO 8601 date string (`YYYY-MM-DD`)
   - String -> Datetime: ISO 8601 datetime string (`YYYY-MM-DDTHH:MM:SSZ`)
   - Boolean -> Boolean: passthrough
   - Array -> set of coerced elements (for `in`/`not_in`)
4. **Expression assembly**: Leaf nodes compile to `pl.col(field).op(value)`. Group nodes combine children with `&` (AND), `|` (OR), or `~` (NOT).

**Priority**: MUST

### FR-004: POST /v1/query/{entity_type}/rows Endpoint

#### Request Schema

```json
{
  "where": <PredicateNode | PredicateNode[]>,
  "section": "Active",
  "select": ["gid", "name", "mrr", "vertical"],
  "limit": 100,
  "offset": 0,
  "order_by": "name",
  "order_dir": "asc"
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `where` | PredicateNode or PredicateNode[] | No | None (no filter) | MAX_PREDICATE_DEPTH=5 |
| `section` | string | No | None (all sections) | Must resolve via SectionIndex |
| `select` | string[] | No | `["gid", "name", "section"]` | Must be valid schema columns |
| `limit` | int | No | 100 | 1 <= limit <= 1000 |
| `offset` | int | No | 0 | >= 0 |
| `order_by` | string | No | None (unordered) | Must be valid schema column |
| `order_dir` | string | No | `"asc"` | `"asc"` or `"desc"` |

**Note**: `gid` is always included in the response regardless of `select`.

#### Response Schema

```json
{
  "data": [
    {"gid": "123", "name": "Acme Dental", "mrr": "500", "vertical": "dental"}
  ],
  "meta": {
    "total_count": 47,
    "returned_count": 47,
    "limit": 100,
    "offset": 0,
    "entity_type": "offer",
    "project_gid": "1143843662099250",
    "query_ms": 12.5
  }
}
```

**Priority**: MUST (Sprint 1)

### FR-005: POST /v1/query/{entity_type}/aggregate Endpoint

#### Request Schema

```json
{
  "where": <PredicateNode | PredicateNode[]>,
  "section": "Active",
  "group_by": ["vertical"],
  "aggregations": [
    {"column": "mrr", "agg": "sum", "alias": "total_mrr"},
    {"column": "gid", "agg": "count", "alias": "offer_count"}
  ]
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `where` | PredicateNode or PredicateNode[] | No | None | MAX_PREDICATE_DEPTH=5 |
| `section` | string | No | None | Must resolve via SectionIndex |
| `group_by` | string[] | Yes | -- | 1-5 valid schema columns; no List dtypes |
| `aggregations` | AggSpec[] | Yes | -- | 1-10 aggregation specs |

**AggSpec**:

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `column` | string | Yes | -- |
| `agg` | string | Yes | -- |
| `alias` | string | No | `"{agg}_{column}"` |

Supported agg values: `sum`, `count`, `mean`, `min`, `max` (matching `SUPPORTED_AGGS` in `metrics/expr.py`).

#### Response Schema

```json
{
  "data": [
    {"vertical": "dental", "total_mrr": 15000.0, "offer_count": 12},
    {"vertical": "medical", "total_mrr": 22000.0, "offer_count": 8}
  ],
  "meta": {
    "group_count": 2,
    "entity_type": "offer",
    "project_gid": "1143843662099250",
    "query_ms": 8.3
  }
}
```

**Priority**: SHOULD (Sprint 2)

### FR-006: POST /v1/query/{entity_type}/metric Endpoint

#### Request Schema

```json
{
  "metric": "active_mrr",
  "section": "Active"
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `metric` | string | Yes | -- | Must exist in MetricRegistry |
| `section` | string | No | None | Overrides metric's scope.section_name if provided |

**Note**: The `section` parameter allows overriding the metric's built-in section scope. If omitted, the metric's own `scope.section` / `scope.section_name` is used. If the metric has no section in its scope and none is provided, computation runs across all sections.

#### Response Schema

```json
{
  "data": {
    "metric": "active_mrr",
    "value": 37000.0,
    "row_count": 20,
    "description": "Total MRR for ACTIVE offers, deduped by phone+vertical"
  },
  "meta": {
    "entity_type": "offer",
    "project_gid": "1143843662099250",
    "section": "Active",
    "query_ms": 6.1
  }
}
```

**Priority**: COULD (Sprint 3)

### FR-007: Section Scoping

Section scoping applies consistently across all three endpoints:

1. If `section` parameter is provided, resolve name to GID via `SectionIndex.from_manifest_async()` (primary) with `SectionIndex.from_enum_fallback()` (secondary).
2. Resolved GID is used to filter DataFrame rows where `section` column equals the GID value.
3. Section filter is logically ANDed with the user's predicate tree (applied before predicate evaluation).
4. If section resolution fails, return `UNKNOWN_SECTION` error.

**Interaction with predicates**: If the user also includes a `section` field in their predicate tree AND specifies the `section` parameter, the parameter takes precedence and the predicate's section clause is ignored with a warning logged.

**Priority**: MUST

### FR-008: Query Guards

| Guard | Value | Behavior |
|-------|-------|----------|
| MAX_RESULT_ROWS | 10,000 | /rows: If total_count exceeds limit, results are truncated to limit. If limit > MAX_RESULT_ROWS, clamp to MAX_RESULT_ROWS. |
| MAX_PREDICATE_DEPTH | 5 | Reject predicate trees deeper than 5 levels with QUERY_TOO_COMPLEX error. |
| Query timing | -- | Log `query_ms` in structured log and include in response meta. |

**Priority**: MUST

### FR-009: Backward Compatibility

The existing `POST /v1/query/{entity_type}` endpoint must continue to function:

1. Route handler remains registered at the existing path.
2. Request/response schemas are unchanged.
3. Add `Deprecation: true` and `Sunset: <date>` response headers.
4. Log deprecation usage: `deprecated_query_endpoint_used` with caller_service.
5. Document migration mapping:
   - `where: {"section": "ACTIVE"}` -> `where: [{"field": "section", "op": "eq", "value": "ACTIVE"}]`
   - `select: [...]` -> `select: [...]` (unchanged)
   - `limit`/`offset` -> `limit`/`offset` (unchanged)

**Priority**: MUST

---

## Non-Functional Requirements

### NFR-001: Latency

| Endpoint | p50 Target | p99 Target | Condition |
|----------|------------|------------|-----------|
| /rows | < 50ms | < 200ms | Cache hit, < 1000 rows returned, predicate depth <= 3 |
| /aggregate | < 30ms | < 150ms | Cache hit, < 50 groups |
| /metric | < 20ms | < 100ms | Cache hit, single metric |

Measured from request receipt to response write, excluding network. These targets assume the DataFrame is already in the memory tier of the cache.

**Priority**: SHOULD

### NFR-002: Security

- All three endpoints require S2S JWT authentication via `require_service_claims()`.
- PAT tokens are rejected (consistent with existing query endpoint).
- Predicate values are used only in Polars expression construction -- no string interpolation, no SQL, no eval. This eliminates injection vectors.
- MAX_PREDICATE_DEPTH prevents resource exhaustion from deeply nested trees.
- MAX_RESULT_ROWS prevents memory exhaustion from unbounded result sets.
- All request parameters are validated via Pydantic models with `extra="forbid"`.

**Priority**: MUST

### NFR-003: Observability

Each request logs:
- `request_id`, `entity_type`, `caller_service` (from JWT claims)
- `predicate_depth`, `predicate_leaf_count` (complexity metrics)
- `section_resolved` (boolean, plus resolved GID if applicable)
- `query_ms` (wall-clock query time)
- `total_count`, `returned_count`

**Priority**: SHOULD

### NFR-004: Input Validation

- Pydantic models enforce request structure with `extra="forbid"`.
- SchemaRegistry validates field names against entity schema.
- Dtype compatibility matrix validates operator/field combinations.
- Value coercion validates type compatibility before Polars expression construction.
- Predicate depth is checked before compilation (fail fast).

**Priority**: MUST

---

## Error Taxonomy

All errors follow the existing pattern established in `api/routes/query.py`: structured JSON with `error` code and `message`.

### Error Responses by HTTP Status

#### 400 Bad Request

| Error Code | Condition | Response Body |
|------------|-----------|---------------|
| `QUERY_TOO_COMPLEX` | Predicate depth exceeds MAX_PREDICATE_DEPTH (5) | `{"error": "QUERY_TOO_COMPLEX", "message": "Predicate tree depth 7 exceeds maximum of 5", "max_depth": 5}` |

#### 401 Unauthorized

Unchanged from existing endpoint. Handled by `require_service_claims()`:
- `MISSING_AUTH` -- No Authorization header
- `SERVICE_TOKEN_REQUIRED` -- PAT token provided (S2S only)
- `JWT_INVALID` -- JWT validation failed

#### 404 Not Found

| Error Code | Condition | Response Body |
|------------|-----------|---------------|
| `UNKNOWN_ENTITY_TYPE` | entity_type not in queryable set | `{"error": "UNKNOWN_ENTITY_TYPE", "message": "Unknown entity type: widget", "available_types": ["offer", "unit", ...]}` |

#### 422 Unprocessable Entity

| Error Code | Condition | Response Body |
|------------|-----------|---------------|
| `UNKNOWN_FIELD` | Predicate references non-existent column | `{"error": "UNKNOWN_FIELD", "message": "Unknown field: foo", "available_fields": ["gid", "name", ...]}` |
| `INVALID_OPERATOR` | Operator incompatible with field dtype | `{"error": "INVALID_OPERATOR", "message": "Operator 'contains' not supported for Int64 field 'mrr'", "field": "mrr", "field_dtype": "Int64", "operator": "contains", "supported_operators": ["eq", "ne", "gt", ...]}` |
| `COERCION_FAILED` | Value cannot be coerced to field dtype | `{"error": "COERCION_FAILED", "message": "Cannot coerce 'abc' to Int64 for field 'mrr'", "field": "mrr", "field_dtype": "Int64", "value": "abc"}` |
| `UNKNOWN_SECTION` | Section name cannot be resolved to GID | `{"error": "UNKNOWN_SECTION", "message": "Unknown section: 'Archived'", "section": "Archived"}` |
| `UNKNOWN_METRIC` | Metric name not in MetricRegistry | `{"error": "UNKNOWN_METRIC", "message": "Unknown metric: 'foo'. Available: active_ad_spend, active_mrr", "available_metrics": ["active_ad_spend", "active_mrr"]}` |
| `VALIDATION_ERROR` | Pydantic validation failure | Standard FastAPI 422 format |

#### 503 Service Unavailable

Unchanged from existing endpoint:
- `CACHE_NOT_WARMED` -- DataFrame cache not available after self-refresh
- `PROJECT_NOT_CONFIGURED` -- No project configured for entity type
- `SERVICE_NOT_CONFIGURED` -- Bot PAT not configured

---

## Sprint Phasing

| Sprint | Scope | Deliverables |
|--------|-------|--------------|
| **Sprint 1** | `/rows` endpoint | Predicate AST model, schema-aware compiler, `/rows` route, section scoping, query guards, deprecation headers on old endpoint |
| **Sprint 2** | `/aggregate` endpoint + hierarchy | `/aggregate` route, aggregation spec model, List[Utf8] predicate support (e.g., tags contains), section hierarchy resolution |
| **Sprint 3** | `/metric` endpoint | `/metric` route, MetricRegistry HTTP bridge, section override logic |

### Sprint 1 Detailed Scope

**In scope**:
- Pydantic models: `PredicateNode`, `ComparisonPredicate`, `GroupPredicate`, `RowsRequest`, `RowsResponse`
- Predicate compiler: `PredicateNode` -> `pl.Expr` with schema validation
- Route: `POST /v1/query/{entity_type}/rows`
- Section scoping via SectionIndex
- Query guards (MAX_RESULT_ROWS, MAX_PREDICATE_DEPTH, timing)
- Deprecation headers on existing `POST /v1/query/{entity_type}`
- Error responses for all 422 cases
- Unit tests for predicate compilation and validation
- Integration test for end-to-end /rows flow

**Out of scope for Sprint 1**:
- `/aggregate` endpoint
- `/metric` endpoint
- List[Utf8] column predicates (tags, platforms)
- `order_by` / `order_dir` (deferred to Sprint 1.5 if needed)
- Removal of old endpoint

---

## Edge Cases

### EC-001: Empty Results

- Predicate matches zero rows: Return `{"data": [], "meta": {"total_count": 0, ...}}` with 200 status.
- No entities of the given type exist: Same empty result (not an error).

### EC-002: Null Handling

- Null column values: Comparison operators treat null as "not matching" (consistent with SQL/Polars NULL semantics). `eq(null)` does not match null values; use `is_null` operator if needed (deferred to Sprint 2).
- Null in `in` set: Ignored. `in: [null, "dental"]` matches only "dental".

### EC-003: Unknown Entity Types

- Return 404 `UNKNOWN_ENTITY_TYPE` with list of available types.
- Entity type validation uses `get_resolvable_entities()` (same as existing endpoint).

### EC-004: Deeply Nested Predicates

- Predicate depth is computed as max nesting level of group nodes.
- A single comparison = depth 1. `{and: [{field...}]}` = depth 2.
- Depth > MAX_PREDICATE_DEPTH (5) returns 400 `QUERY_TOO_COMPLEX` before any compilation.

### EC-005: Empty Predicate

- `where: null` or `where` omitted: No filter applied, returns all rows (subject to pagination and section scoping).
- `where: []` (empty array): Treated as no filter (sugar for "match all").
- `where: {"and": []}` (empty AND): Treated as "match all" (identity element of AND).

### EC-006: Section Conflicts

- User provides `section` parameter AND `section` field in predicate tree: The `section` parameter wins. A warning is logged but no error is returned.
- Rationale: The `section` parameter is the preferred mechanism; predicate-level section filtering is allowed but discouraged.

### EC-007: Value Type Mismatches

- String value for numeric field (e.g., `"mrr" eq "abc"`): COERCION_FAILED at compile time.
- Numeric value for string field (e.g., `"name" eq 123`): Coerced to string "123" (permissive).
- Array value for non-in/not_in operator: VALIDATION_ERROR (Pydantic rejects).

### EC-008: Large DataFrames

- DataFrames exceeding MAX_RESULT_ROWS after filtering: Results truncated to limit (clamped at MAX_RESULT_ROWS=10000). `total_count` in meta reflects the true count.
- Memory pressure: Polars lazy evaluation is NOT used in Sprint 1 (DataFrames are already materialized in cache). Lazy evaluation is a potential Sprint 2 optimization.

### EC-009: Concurrent Requests

- All operations are read-only against immutable cached DataFrames.
- No locking required for query operations.
- Cache refresh is handled by the existing UniversalResolutionStrategy coalescing mechanism.

### EC-010: Schema Column "section" Ambiguity

- The base schema includes a `section` column (dtype Utf8) that stores the section name string from Asana memberships.
- The `section` request parameter resolves to a GID and filters the `section` column by GID match.
- If the `section` column in the DataFrame stores section names (not GIDs), the resolution layer must handle this mapping. The SectionIndex already provides this via name -> GID mapping.
- Implementation note: The DataFrame `section` column stores section **names** (e.g., "Active"), not GIDs. The `section` parameter resolves to a name match, not a GID match. Verify during implementation.

---

## Out of Scope

The following are explicitly excluded from all sprints of this initiative:

- **New data sources**: All queries operate over existing cached DataFrames. No direct Asana API queries.
- **Write operations**: The query service is read-only. No create/update/delete.
- **Cross-entity joins**: Queries operate on a single entity type per request. Join-like behavior (e.g., "offers for businesses in vertical X") requires multiple API calls.
- **Real-time subscriptions / WebSocket**: Query results are point-in-time snapshots.
- **Query caching**: Individual query results are not cached. The underlying DataFrame is cached.
- **Custom aggregation functions**: Only the five standard aggregations (sum, count, mean, min, max) are supported.
- **is_null / is_not_null operators**: Deferred. NULL comparisons use Polars default semantics.
- **Regex operator**: Deferred. Use `contains` and `starts_with` for string matching.

---

## Migration / Deprecation Plan

### Phase 1: Parallel Operation (Sprint 1)

- New `/rows` endpoint deployed alongside existing `/query/{entity_type}`.
- Old endpoint gets `Deprecation` and `Sunset` headers.
- Both endpoints share the same EntityQueryService for cache access.

### Phase 2: Consumer Migration (Post-Sprint 1)

- Notify consuming services of deprecation timeline.
- Provide request format migration examples (see FR-009).
- Monitor deprecated endpoint usage via structured logs.

### Phase 3: Removal (TBD)

- Remove old endpoint after all consumers have migrated.
- Exact timeline depends on consumer adoption velocity.
- Minimum 30-day sunset period from deprecation announcement.

---

## Attestation Table

| File | Absolute Path | Read |
|------|---------------|------|
| Query Service | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py` | Yes |
| Query Route | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/query.py` | Yes |
| Schema Registry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py` | Yes |
| Schema Model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/schema.py` | Yes |
| Section Resolve | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/metrics/resolve.py` | Yes |
| OfferSection | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/sections.py` | Yes |
| Auth (internal) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/internal.py` | Yes |
| Router Registration | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` (lines 1353-1364) | Yes |
| Metrics __init__ | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/metrics/__init__.py` | Yes |
| Metric Model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/metrics/metric.py` | Yes |
| MetricExpr | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/metrics/expr.py` | Yes |
| MetricRegistry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/metrics/registry.py` | Yes |
| compute_metric | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/metrics/compute.py` | Yes |
| Offer Definitions | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/metrics/definitions/offer.py` | Yes |
| Offer Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/offer.py` | Yes |
| Base Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/base.py` | Yes |
| Resolver | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` | Yes (partial) |
| Existing Query PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-entity-query-endpoint.md` | Yes (partial) |
