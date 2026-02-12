# Query API

> Query cached entity DataFrames with composable filters, aggregation, and cross-entity joins.

## Authentication

S2S JWT (service-to-service) authentication required via `Authorization: Bearer <token>` header.

PAT (Personal Access Token) authentication is NOT supported. Requests with PAT tokens receive `401 SERVICE_TOKEN_REQUIRED` error.

The endpoints internally use a bot PAT to access cached DataFrames, but client authentication must use service tokens.

## Endpoints

### `POST /v1/query/{entity_type}` (DEPRECATED)

Legacy query endpoint with flat equality filtering. Use `/rows` for new integrations.

**Deprecation Notice:**

- Sunset date: **2026-06-01**
- Response headers: `Deprecation: true`, `Sunset: 2026-06-01`
- Successor: `Link: </v1/query/{entity_type}/rows>; rel="successor-version"`
- Use `/rows` for composable predicates, joins, and aggregation

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_type` | string | Entity type to query (offer, unit, business, contact) |

**Query Parameters:**

None.

**Request Body:**

```json
{
  "where": {
    "section": "ACTIVE",
    "vertical": "dental"
  },
  "select": ["gid", "name", "office_phone"],
  "limit": 100,
  "offset": 0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `where` | object | No | Flat equality filters (AND semantics). Empty object means no filter. |
| `select` | array[string] | No | Column names to return. Default: `["gid", "name", "section"]` |
| `limit` | integer | No | Maximum rows to return (default: 100, max: 1000) |
| `offset` | integer | No | Skip N rows (default: 0, min: 0) |

**Response Body:**

```json
{
  "data": [
    {
      "gid": "1234567890123456",
      "name": "Acme Dental - Facebook",
      "office_phone": "+15551234567"
    }
  ],
  "meta": {
    "total_count": 47,
    "limit": 100,
    "offset": 0,
    "entity_type": "offer",
    "project_gid": "1143843662099250"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `data` | array | Matching rows as dictionaries |
| `meta.total_count` | integer | Total matches before pagination |
| `meta.limit` | integer | Requested limit |
| `meta.offset` | integer | Requested offset |
| `meta.entity_type` | string | Queried entity type |
| `meta.project_gid` | string | Asana project GID for cache key |

**Limitations:**

- `where` only supports flat equality (AND semantics)
- No nested predicates, OR logic, or NOT logic
- No `order_by`, `join`, or aggregation support
- No predicate tree composition

**Example: cURL**

```bash
curl -X POST https://api.example.com/v1/query/offer \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "where": {"vertical": "dental", "section": "ACTIVE"},
    "select": ["gid", "name", "office_phone"],
    "limit": 50
  }'
```

### `POST /v1/query/{entity_type}/rows`

Query entity rows with composable predicate filtering, joins, and ordering.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_type` | string | Entity type to query (offer, unit, business, contact, asset_edit, asset_edit_holder) |

**Query Parameters:**

None.

**Request Body:**

```json
{
  "where": {
    "and": [
      {"field": "vertical", "op": "eq", "value": "dental"},
      {
        "or": [
          {"field": "section", "op": "eq", "value": "ACTIVE"},
          {"field": "section", "op": "eq", "value": "PAUSED"}
        ]
      }
    ]
  },
  "section": "ACTIVE",
  "select": ["gid", "name", "office_phone"],
  "limit": 100,
  "offset": 0,
  "order_by": "name",
  "order_dir": "asc",
  "join": {
    "entity_type": "business",
    "on": "business_gid",
    "select": ["business_name", "business_address"]
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `where` | PredicateNode | No | Composable predicate tree for filtering (see PredicateNode) |
| `section` | string | No | Section name for scoping (shorthand for section equality filter) |
| `select` | array[string] | No | Column names to return. Default: all schema columns |
| `limit` | integer | No | Maximum rows to return (default: 100, max: 1000, min: 1) |
| `offset` | integer | No | Skip N rows (default: 0, min: 0) |
| `order_by` | string | No | Column name for sorting |
| `order_dir` | string | No | Sort direction: `asc` or `desc` (default: `asc`) |
| `join` | JoinSpec | No | Cross-entity join specification (see JoinSpec) |

**PredicateNode:**

Composable tree structure for filtering. Can be one of:

**Comparison (leaf node):**

```json
{
  "field": "vertical",
  "op": "eq",
  "value": "dental"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `field` | string | Column name from entity schema |
| `op` | Op | Comparison operator (see Operators table) |
| `value` | any | Value to compare against (type must match field dtype) |

**AndGroup (logical AND):**

```json
{
  "and": [
    {"field": "vertical", "op": "eq", "value": "dental"},
    {"field": "section", "op": "eq", "value": "ACTIVE"}
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `and` | array[PredicateNode] | All children must match |

**OrGroup (logical OR):**

```json
{
  "or": [
    {"field": "section", "op": "eq", "value": "ACTIVE"},
    {"field": "section", "op": "eq", "value": "PAUSED"}
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `or` | array[PredicateNode] | At least one child must match |

**NotGroup (logical NOT):**

```json
{
  "not": {
    "field": "section",
    "op": "eq",
    "value": "ARCHIVED"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `not` | PredicateNode | Child must not match |

**Flat Array Sugar:**

Bare arrays auto-wrap to AND groups:

```json
{
  "where": [
    {"field": "vertical", "op": "eq", "value": "dental"},
    {"field": "section", "op": "eq", "value": "ACTIVE"}
  ]
}
```

Equivalent to:

```json
{
  "where": {
    "and": [
      {"field": "vertical", "op": "eq", "value": "dental"},
      {"field": "section", "op": "eq", "value": "ACTIVE"}
    ]
  }
}
```

Empty arrays become `null` (no filter).

**Operators:**

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equality | `{"field": "vertical", "op": "eq", "value": "dental"}` |
| `ne` | Not equal | `{"field": "section", "op": "ne", "value": "ARCHIVED"}` |
| `gt` | Greater than | `{"field": "revenue", "op": "gt", "value": 1000}` |
| `lt` | Less than | `{"field": "age", "op": "lt", "value": 30}` |
| `gte` | Greater than or equal | `{"field": "score", "op": "gte", "value": 80}` |
| `lte` | Less than or equal | `{"field": "price", "op": "lte", "value": 100}` |
| `in` | Value in list | `{"field": "vertical", "op": "in", "value": ["dental", "medical"]}` |
| `not_in` | Value not in list | `{"field": "state", "op": "not_in", "value": ["CA", "NY"]}` |
| `contains` | String contains | `{"field": "name", "op": "contains", "value": "Dental"}` |
| `starts_with` | String starts with | `{"field": "office_phone", "op": "starts_with", "value": "+1555"}` |

Operator compatibility is enforced by field dtype. Invalid operator/field combinations return `422 INVALID_OPERATOR`.

**JoinSpec:**

Cross-entity join specification. Supports one level of joining (no nested joins).

```json
{
  "entity_type": "business",
  "on": "business_gid",
  "select": ["business_name", "business_address"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entity_type` | string | Yes | Target entity type to join (must have relationship with source entity) |
| `on` | string | No | Join key field name (auto-detected if omitted) |
| `select` | array[string] | Yes | Columns from target entity to include in results |

Joined columns are prefixed with the target entity type: `{entity_type}_{column}`.

**Supported relationships:**

- `offer` + `business`
- `asset_edit` + `unit`

**Response Body:**

```json
{
  "data": [
    {
      "gid": "1234567890123456",
      "name": "Acme Dental - Facebook",
      "office_phone": "+15551234567"
    }
  ],
  "meta": {
    "total_count": 47,
    "returned_count": 1,
    "limit": 100,
    "offset": 0,
    "entity_type": "offer",
    "project_gid": "1143843662099250",
    "query_ms": 12.34,
    "join_entity": "business",
    "join_key": "business_gid",
    "join_matched": 1,
    "join_unmatched": 0,
    "freshness": "fresh",
    "data_age_seconds": 45.2,
    "staleness_ratio": 0.15
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `data` | array | Matching rows as dictionaries |
| `meta.total_count` | integer | Total matches before pagination |
| `meta.returned_count` | integer | Rows in this response |
| `meta.limit` | integer | Requested limit |
| `meta.offset` | integer | Requested offset |
| `meta.entity_type` | string | Queried entity type |
| `meta.project_gid` | string | Asana project GID for cache key |
| `meta.query_ms` | float | Query execution time in milliseconds |
| `meta.join_entity` | string \| null | Joined entity type (if join was requested) |
| `meta.join_key` | string \| null | Key used for join (if join was requested) |
| `meta.join_matched` | integer \| null | Rows with matching join target (if join was requested) |
| `meta.join_unmatched` | integer \| null | Rows without matching join target (if join was requested) |
| `meta.freshness` | string \| null | Cache freshness: `fresh`, `stale`, or `expired` |
| `meta.data_age_seconds` | float \| null | Seconds since last cache build |
| `meta.staleness_ratio` | float \| null | Ratio of age to staleness threshold |

**Example: Basic query (cURL)**

```bash
curl -X POST https://api.example.com/v1/query/offer/rows \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "where": {"field": "vertical", "op": "eq", "value": "dental"},
    "select": ["gid", "name", "office_phone"],
    "limit": 10
  }'
```

**Example: Nested predicate (cURL)**

```bash
curl -X POST https://api.example.com/v1/query/offer/rows \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "where": {
      "and": [
        {"field": "vertical", "op": "eq", "value": "dental"},
        {
          "or": [
            {"field": "section", "op": "eq", "value": "ACTIVE"},
            {"field": "section", "op": "eq", "value": "PAUSED"}
          ]
        }
      ]
    },
    "select": ["gid", "name", "section"],
    "limit": 50
  }'
```

**Example: Cross-entity join (cURL)**

```bash
curl -X POST https://api.example.com/v1/query/offer/rows \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "where": {"field": "section", "op": "eq", "value": "ACTIVE"},
    "select": ["gid", "name", "vertical"],
    "join": {
      "entity_type": "business",
      "on": "business_gid",
      "select": ["business_name", "business_address"]
    },
    "limit": 10
  }'
```

**Example: Python httpx**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://api.example.com/v1/query/offer/rows",
        headers={
            "Authorization": f"Bearer {s2s_token}",
            "Content-Type": "application/json"
        },
        json={
            "where": {
                "and": [
                    {"field": "vertical", "op": "eq", "value": "dental"},
                    {"field": "section", "op": "eq", "value": "ACTIVE"}
                ]
            },
            "select": ["gid", "name", "office_phone"],
            "limit": 100
        }
    )
    result = response.json()

    for row in result["data"]:
        print(f"Offer {row['gid']}: {row['name']}")

    print(f"Total matches: {result['meta']['total_count']}")
    print(f"Query time: {result['meta']['query_ms']}ms")
```

**Example: Pagination**

```python
import httpx

async def query_all_pages(token: str, entity_type: str, where: dict) -> list[dict]:
    """Fetch all pages for a query."""
    all_data = []
    offset = 0
    limit = 100

    async with httpx.AsyncClient() as client:
        while True:
            response = await client.post(
                f"https://api.example.com/v1/query/{entity_type}/rows",
                headers={"Authorization": f"Bearer {token}"},
                json={"where": where, "limit": limit, "offset": offset},
            )
            response.raise_for_status()

            result = response.json()
            all_data.extend(result["data"])

            if result["meta"]["returned_count"] < limit:
                break

            offset += limit

    return all_data
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `QUERY_TOO_COMPLEX` | Predicate tree depth exceeds maximum of 5 |
| 404 | `UNKNOWN_ENTITY_TYPE` | Entity type not recognized or not queryable |
| 422 | `UNKNOWN_FIELD` | Field not found in entity schema |
| 422 | `INVALID_OPERATOR` | Operator not compatible with field dtype |
| 422 | `COERCION_ERROR` | Value cannot be coerced to field dtype |
| 422 | `UNKNOWN_SECTION` | Section name not recognized for entity type |
| 503 | `CACHE_NOT_WARMED` | DataFrame not available after cache build attempt |
| 503 | `PROJECT_NOT_CONFIGURED` | No project configured for entity type |
| 503 | `SERVICE_NOT_CONFIGURED` | Bot PAT not configured for cache operations |

**Error Response Examples:**

Query Too Complex:

```json
{
  "error": "QUERY_TOO_COMPLEX",
  "message": "Predicate tree depth 6 exceeds maximum of 5",
  "max_depth": 5
}
```

Unknown Field:

```json
{
  "error": "UNKNOWN_FIELD",
  "message": "Unknown field: invalid_field",
  "available_fields": ["gid", "name", "section", "vertical", "office_phone", "offer_id"]
}
```

Invalid Operator:

```json
{
  "error": "INVALID_OPERATOR",
  "message": "Operator 'gt' not supported for Utf8 field 'name'",
  "field": "name",
  "field_dtype": "Utf8",
  "operator": "gt",
  "supported_operators": ["eq", "ne", "in", "not_in", "contains", "starts_with"]
}
```

Coercion Error:

```json
{
  "error": "COERCION_FAILED",
  "message": "Cannot coerce 'not-a-number' to Int64 for field 'count'",
  "field": "count",
  "field_dtype": "Int64",
  "value": "not-a-number"
}
```

Unknown Section:

```json
{
  "error": "UNKNOWN_SECTION",
  "message": "Unknown section: 'INVALID'",
  "section": "INVALID"
}
```

Cache Not Warmed:

```json
{
  "error": "CACHE_NOT_WARMED",
  "message": "DataFrame unavailable for offer. Cache warming may be in progress or build failed.",
  "entity_type": "offer",
  "retry_after_seconds": 30
}
```

### `POST /v1/query/{entity_type}/aggregate`

Aggregate entity data with grouping and optional HAVING filter.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_type` | string | Entity type to aggregate (offer, unit, business, contact, asset_edit, asset_edit_holder) |

**Query Parameters:**

None.

**Request Body:**

```json
{
  "where": {
    "field": "section",
    "op": "eq",
    "value": "ACTIVE"
  },
  "section": "ACTIVE",
  "group_by": ["vertical", "section"],
  "aggregations": [
    {"column": "gid", "agg": "count", "alias": "offer_count"},
    {"column": "mrr", "agg": "sum", "alias": "total_revenue"}
  ],
  "having": {
    "field": "offer_count",
    "op": "gte",
    "value": 5
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `where` | PredicateNode | No | Pre-aggregation filter (same as `/rows`) |
| `section` | string | No | Section name for scoping (applied before aggregation) |
| `group_by` | array[string] | Yes | Column names to group by (min: 1, max: 5) |
| `aggregations` | array[AggSpec] | Yes | Aggregation specifications (min: 1, max: 10) |
| `having` | PredicateNode | No | Post-aggregation filter (operates on aggregated columns) |

**AggSpec:**

Single aggregation specification.

```json
{
  "column": "mrr",
  "agg": "sum",
  "alias": "total_revenue"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `column` | string | Yes | Column to aggregate (must exist in schema) |
| `agg` | AggFunction | Yes | Aggregation function to apply |
| `alias` | string | No | Output column name. Default: `{agg}_{column}` |

**AggFunction:**

| Function | Description | Example |
|----------|-------------|---------|
| `sum` | Sum of values | Total revenue across offers |
| `count` | Count of rows | Number of offers per vertical |
| `mean` | Average of values | Average MRR per section |
| `min` | Minimum value | Lowest ad spend in group |
| `max` | Maximum value | Highest revenue in group |
| `count_distinct` | Count unique values | Unique verticals per section |

**Response Body:**

```json
{
  "data": [
    {"vertical": "dental", "section": "ACTIVE", "offer_count": 27, "total_revenue": 135000},
    {"vertical": "medical", "section": "ACTIVE", "offer_count": 20, "total_revenue": 98000}
  ],
  "meta": {
    "group_count": 2,
    "aggregation_count": 2,
    "group_by": ["vertical", "section"],
    "entity_type": "offer",
    "project_gid": "1143843662099250",
    "query_ms": 8.45,
    "freshness": "fresh",
    "data_age_seconds": 30.1,
    "staleness_ratio": 0.10
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `data` | array | Aggregated rows as dictionaries (group_by columns + aggregation aliases) |
| `meta.group_count` | integer | Number of groups in result |
| `meta.aggregation_count` | integer | Number of aggregations performed |
| `meta.group_by` | array[string] | Group by columns used |
| `meta.entity_type` | string | Queried entity type |
| `meta.project_gid` | string | Asana project GID for cache key |
| `meta.query_ms` | float | Query execution time in milliseconds |
| `meta.freshness` | string \| null | Cache freshness: `fresh`, `stale`, or `expired` |
| `meta.data_age_seconds` | float \| null | Seconds since last cache build |
| `meta.staleness_ratio` | float \| null | Ratio of age to staleness threshold |

**Example: Basic aggregation (cURL)**

```bash
curl -X POST https://api.example.com/v1/query/offer/aggregate \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "group_by": ["vertical"],
    "aggregations": [
      {"column": "gid", "agg": "count", "alias": "offer_count"},
      {"column": "mrr", "agg": "sum", "alias": "total_revenue"}
    ]
  }'
```

**Example: Aggregation with HAVING filter (cURL)**

```bash
curl -X POST https://api.example.com/v1/query/offer/aggregate \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "where": {"field": "section", "op": "eq", "value": "ACTIVE"},
    "group_by": ["vertical"],
    "aggregations": [
      {"column": "gid", "agg": "count", "alias": "offer_count"}
    ],
    "having": {
      "field": "offer_count",
      "op": "gte",
      "value": 10
    }
  }'
```

**Example: Python httpx**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://api.example.com/v1/query/offer/aggregate",
        headers={
            "Authorization": f"Bearer {s2s_token}",
            "Content-Type": "application/json"
        },
        json={
            "where": {"field": "section", "op": "eq", "value": "ACTIVE"},
            "group_by": ["vertical"],
            "aggregations": [
                {"column": "gid", "agg": "count", "alias": "offer_count"},
                {"column": "mrr", "agg": "sum", "alias": "total_revenue"}
            ]
        }
    )
    result = response.json()

    for row in result["data"]:
        print(f"{row['vertical']}: {row['offer_count']} offers, ${row['total_revenue']} revenue")

    print(f"Groups: {result['meta']['group_count']}")
    print(f"Query time: {result['meta']['query_ms']}ms")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `QUERY_TOO_COMPLEX` | Predicate tree depth exceeds maximum of 5 (where or having) |
| 400 | `AGGREGATE_GROUP_LIMIT_ERROR` | group_by exceeds maximum of 5 columns or aggregations exceeds maximum of 10 |
| 404 | `UNKNOWN_ENTITY_TYPE` | Entity type not recognized or not queryable |
| 422 | `UNKNOWN_FIELD` | Field not found in entity schema |
| 422 | `INVALID_OPERATOR` | Operator not compatible with field dtype |
| 422 | `COERCION_ERROR` | Value cannot be coerced to field dtype |
| 422 | `UNKNOWN_SECTION` | Section name not recognized for entity type |
| 503 | `CACHE_NOT_WARMED` | DataFrame not available after cache build attempt |
| 503 | `PROJECT_NOT_CONFIGURED` | No project configured for entity type |
| 503 | `SERVICE_NOT_CONFIGURED` | Bot PAT not configured for cache operations |

**Error Response Example:**

Aggregate Group Limit:

```json
{
  "error": "AGGREGATE_GROUP_LIMIT_ERROR",
  "message": "group_by limit 5 exceeded: requested 7 columns",
  "limit": 5,
  "requested": 7
}
```

## Section Filtering

The `section` parameter provides a dedicated scoping mechanism. It translates to a `section == "NAME"` filter applied before the main predicate.

**Conflict Resolution:**

If both `section` parameter and `where` predicate reference the section field, the engine strips section comparisons from the predicate and uses the parameter value. A warning is logged but the query succeeds.

Example:

```json
{
  "section": "ACTIVE",
  "where": {"field": "section", "op": "eq", "value": "PAUSED"}
}
```

The `where` section comparison is stripped, and only `section: "ACTIVE"` is applied.

**Section Resolution:**

Sections are resolved using:
1. Project-specific manifest (S3-backed persistence)
2. Entity type enum fallback (hardcoded section names)

Unknown sections return `422 UNKNOWN_SECTION`.

## Predicate Depth Limits

Predicate trees are limited to depth 5 to prevent query complexity attacks.

**Depth calculation:**

- Comparison: depth 1
- AndGroup/OrGroup: 1 + max(child depths)
- NotGroup: 1 + child depth

Queries exceeding depth 5 return `400 QUERY_TOO_COMPLEX`.

## Cache Freshness

Queries read from cached DataFrames. Cache lifecycle:

1. **Cache hit** - DataFrame in memory or S3. Query executes immediately (5-200ms).
2. **Cache miss** - DataFrame not cached. Returns `503 CACHE_NOT_WARMED` if self-refresh unavailable.
3. **Build failure** - Circuit breaker open or build failed. Returns `503 CACHE_NOT_WARMED`.

**Freshness metadata:**

- `freshness` - "fresh" (< staleness threshold), "stale" (> threshold but < TTL), "expired" (> TTL)
- `data_age_seconds` - Seconds since last cache build
- `staleness_ratio` - `data_age_seconds / staleness_threshold`

Use freshness metadata to decide if results are acceptable or if a cache refresh is needed.

## Schema Validation

Field names in predicates, `select`, `group_by`, and `aggregations` are validated against the entity schema. Unknown fields return `422 UNKNOWN_FIELD`.

Available schemas:

- `base` (task_type: "*") - Common fields (gid, name, section, completed, created_at)
- `unit` (task_type: "Unit") - Unit-specific fields (unit_id, unit_phone, unit_address)
- `contact` (task_type: "Contact") - Contact fields (contact_phone, contact_email)
- `business` (task_type: "Business") - Business fields (business_name, business_address)
- `offer` (task_type: "Offer") - Offer fields (vertical, office_phone, offer_id)
- `asset_edit` (task_type: "AssetEdit") - Asset edit fields
- `asset_edit_holder` (task_type: "AssetEditHolder") - Asset edit holder fields

Field validation errors include available fields for discoverability.

## Notes

- Queries operate on cached DataFrames, not live Asana data
- Results reflect the state of the cache at build time
- Cache warming happens via scheduled builds, self-refresh on miss, or manual triggers
- Pagination is supported for `/rows` but not `/aggregate`
- Cross-entity joins are limited to one level (no nested joins)
- PredicateNode uses flat array sugar: bare arrays auto-wrap to AND groups
- Empty `where` or `null` means no filter (all rows)
- Response metadata includes cache freshness and query timing

## See Also

- [Entity Write API](entity-write.md) - Write fields to Asana entities
- [Entity Resolver API](resolver.md) - Resolve business identifiers to Asana GIDs
- [Entity Query Guide](../guides/entity-query.md) - Comprehensive guide with examples and patterns
- [Authentication Guide](../guides/authentication.md) - S2S JWT authentication setup
- [Cache System Guide](../guides/cache-system.md) - Cache warming and lifecycle
