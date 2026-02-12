# Querying Entity Data

Query cached entity DataFrames through REST endpoints. Filter, paginate, and aggregate entity data without rebuilding from Asana.

## Overview

The entity query API provides read-only access to cached DataFrames. DataFrames are built asynchronously by the cache warming system and stored in-memory with S3 fallback.

**What querying provides:**

- Field-based filtering with composable predicates
- Section-scoped queries
- Pagination and column selection
- Cross-entity joins
- Aggregation operations
- Schema-based views (base, unit, contact, business, offer, asset_edit, asset_edit_holder)

**When to use:**

- Query entities without triggering Asana API calls
- Filter cached data by field values or sections
- Aggregate metrics across entity collections
- Join related entities (offer + business, asset_edit + unit)

**Not for:**

- Real-time data (use cache warming first)
- Writing data (use entity write endpoints)
- Uncached entity types (returns 503)

## Authentication

All query endpoints require S2S JWT authentication:

```bash
curl -X POST https://api.example.com/v1/query/offer/rows \
  -H "Authorization: Bearer <SERVICE_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"where": {"field": "section", "op": "eq", "value": "ACTIVE"}}'
```

PAT pass-through is not supported for query endpoints.

## Query Endpoints

### POST /v1/query/{entity_type}/rows

Primary query endpoint. Supports composable predicate trees, section filtering, pagination, joins, and ordering.

**Path parameters:**

- `entity_type` (string, required) - Entity type to query (offer, business, unit, contact, asset_edit, asset_edit_holder)

**Request body:**

```json
{
  "where": {
    "field": "vertical",
    "op": "eq",
    "value": "dental"
  },
  "section": "ACTIVE",
  "select": ["gid", "name", "office_phone"],
  "limit": 100,
  "offset": 0,
  "order_by": "name",
  "order_dir": "asc"
}
```

**Request fields:**

- `where` (object, optional) - Predicate tree for filtering (see Filtering section)
- `section` (string, optional) - Section name for scoping
- `select` (array[string], optional) - Columns to return (default: ["gid", "name", "section"])
- `limit` (integer, optional) - Maximum rows to return (default: 100, max: 1000)
- `offset` (integer, optional) - Skip N rows (default: 0)
- `order_by` (string, optional) - Column name for sorting
- `order_dir` (string, optional) - Sort direction: "asc" or "desc" (default: "asc")
- `join` (object, optional) - Cross-entity join specification (see Joins section)

**Response:**

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
    "freshness": "fresh",
    "data_age_seconds": 45.2,
    "staleness_ratio": 0.15
  }
}
```

**Response fields:**

- `data` (array) - Matching rows as dictionaries
- `meta.total_count` (integer) - Total matches before pagination
- `meta.returned_count` (integer) - Rows in this response
- `meta.limit` (integer) - Requested limit
- `meta.offset` (integer) - Requested offset
- `meta.entity_type` (string) - Queried entity type
- `meta.project_gid` (string) - Project GID for cache key
- `meta.query_ms` (float) - Query execution time in milliseconds
- `meta.freshness` (string, optional) - Cache freshness status ("fresh", "stale", "expired")
- `meta.data_age_seconds` (float, optional) - Seconds since last cache build
- `meta.staleness_ratio` (float, optional) - Ratio of age to staleness threshold

**Example: Basic query**

```bash
curl -X POST https://api.example.com/v1/query/offer/rows \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "where": {"field": "vertical", "op": "eq", "value": "dental"},
    "select": ["gid", "name", "office_phone"],
    "limit": 10
  }'
```

**Example: Section-scoped query**

```bash
curl -X POST https://api.example.com/v1/query/offer/rows \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "section": "ACTIVE",
    "select": ["gid", "name", "vertical"]
  }'
```

**Example: No filter (all rows)**

```bash
curl -X POST https://api.example.com/v1/query/offer/rows \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "select": ["gid", "name"],
    "limit": 50
  }'
```

### POST /v1/query/{entity_type} (Deprecated)

Legacy query endpoint with flat equality filtering. Use `/rows` for new integrations.

**Deprecation notice:**

- Sunset date: 2026-06-01
- Response headers: `Deprecation: true`, `Sunset: 2026-06-01`, `Link: </v1/query/{entity_type}/rows>; rel="successor-version"`
- Use `/rows` for composable predicates, joins, and aggregation

**Request body:**

```json
{
  "where": {"section": "ACTIVE", "vertical": "dental"},
  "select": ["gid", "name"],
  "limit": 100,
  "offset": 0
}
```

Differences from `/rows`:

- `where` is a flat dictionary (AND semantics only)
- No nested predicates, joins, or aggregation
- No `order_by` or `join` support

## Filtering

### Predicate Structure

Predicates are composable trees with comparison leaves and logical group nodes.

**Comparison (leaf node):**

```json
{
  "field": "vertical",
  "op": "eq",
  "value": "dental"
}
```

**Logical groups:**

- `and` - All children must match
- `or` - At least one child must match
- `not` - Child must not match

**Nested example:**

```json
{
  "and": [
    {"field": "vertical", "op": "eq", "value": "dental"},
    {
      "or": [
        {"field": "section", "op": "eq", "value": "ACTIVE"},
        {"field": "section", "op": "eq", "value": "PAUSED"}
      ]
    }
  ]
}
```

**Flat array sugar:**

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

### Operators

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

**Operator compatibility:**

- String fields (Utf8): All operators
- Numeric fields (Int64, Float64): `eq`, `ne`, `gt`, `lt`, `gte`, `lte`, `in`, `not_in`
- Boolean fields: `eq`, `ne`
- List fields: `contains` (element membership)

Invalid operator for dtype returns 422:

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

### Depth Limits

Predicate trees are limited to depth 5 to prevent query complexity attacks.

Depth 6 example (rejected):

```json
{
  "and": [
    {
      "or": [
        {
          "not": {
            "and": [
              {
                "or": [
                  {
                    "not": {
                      "field": "name",
                      "op": "eq",
                      "value": "test"
                    }
                  }
                ]
              }
            ]
          }
        }
      ]
    }
  ]
}
```

Error response:

```json
{
  "error": "QUERY_TOO_COMPLEX",
  "message": "Predicate tree depth 6 exceeds maximum of 5",
  "max_depth": 5
}
```

## Section Filtering

Section parameter provides a dedicated scoping mechanism. Translates to `section == "NAME"` filter.

**Request with section:**

```json
{
  "section": "ACTIVE",
  "where": {"field": "vertical", "op": "eq", "value": "dental"}
}
```

Equivalent to:

```json
{
  "where": {
    "and": [
      {"field": "section", "op": "eq", "value": "ACTIVE"},
      {"field": "vertical", "op": "eq", "value": "dental"}
    ]
  }
}
```

**Conflict resolution:**

If `section` parameter and `where` predicate both reference the section field, the engine strips section comparisons from the predicate and uses the parameter value. A warning is logged but the query succeeds.

**Unknown section:**

```json
{
  "error": "UNKNOWN_SECTION",
  "message": "Unknown section: 'INVALID'",
  "section": "INVALID"
}
```

Section resolution uses:
1. Project-specific manifest (S3-backed)
2. Entity type enum fallback

## Schema-Based Views

DataFrames use schema definitions from SchemaRegistry. Each entity type maps to a schema defining available columns and types.

**Available schemas:**

- `base` (task_type: "*") - Common fields across all entities (gid, name, section, completed, created_at)
- `unit` (task_type: "Unit") - Unit-specific fields (unit_id, unit_phone, unit_address)
- `contact` (task_type: "Contact") - Contact fields (contact_phone, contact_email)
- `business` (task_type: "Business") - Business fields (business_name, business_address)
- `offer` (task_type: "Offer") - Offer fields (vertical, office_phone, offer_id)
- `asset_edit` (task_type: "AssetEdit") - Asset edit fields
- `asset_edit_holder` (task_type: "AssetEditHolder") - Asset edit holder fields

Schema selection happens at cache build time. Queries operate on the built DataFrame schema.

**Field validation:**

Queries validate field names against the entity schema. Unknown fields return 422:

```json
{
  "error": "UNKNOWN_FIELD",
  "message": "Unknown field: invalid_field",
  "available_fields": ["gid", "name", "section", "vertical", "office_phone", "offer_id"]
}
```

## Cross-Entity Joins

Join related entities to enrich results. Supports one level of joining (no nested joins).

**Join specification:**

```json
{
  "join": {
    "entity_type": "business",
    "on": "business_gid",
    "select": ["business_name", "business_address"]
  }
}
```

**Join fields:**

- `entity_type` (string, required) - Target entity type to join
- `on` (string, optional) - Join key field name (auto-detected if omitted)
- `select` (array[string], required) - Columns from target entity to include

**Full request example:**

```bash
curl -X POST https://api.example.com/v1/query/offer/rows \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "where": {"field": "section", "op": "eq", "value": "ACTIVE"},
    "select": ["gid", "name", "vertical"],
    "join": {
      "entity_type": "business",
      "on": "business_gid",
      "select": ["business_name", "business_address"]
    }
  }'
```

**Response with joined columns:**

```json
{
  "data": [
    {
      "gid": "1234567890123456",
      "name": "Acme Dental - Facebook",
      "vertical": "dental",
      "business_business_name": "Acme Dental",
      "business_business_address": "123 Main St"
    }
  ],
  "meta": {
    "total_count": 47,
    "returned_count": 1,
    "join_entity": "business",
    "join_key": "business_gid",
    "join_matched": 1,
    "join_unmatched": 0
  }
}
```

Joined columns are prefixed with the target entity type: `{entity_type}_{column}`.

**Join metadata:**

- `join_entity` (string) - Joined entity type
- `join_key` (string) - Key used for join
- `join_matched` (integer) - Rows with matching join target
- `join_unmatched` (integer) - Rows without matching join target

**Supported relationships:**

- offer + business
- asset_edit + unit

**Join errors:**

Unknown relationship:

```json
{
  "error": "JOIN_ERROR",
  "message": "No relationship between 'offer' and 'contact'. Joinable types: ['business']"
}
```

Target entity not configured:

```json
{
  "error": "JOIN_ERROR",
  "message": "No project configured for join target: business"
}
```

## Aggregation

Group and aggregate entity data. See aggregation guide for full details.

**Endpoint:**

```
POST /v1/query/{entity_type}/aggregate
```

**Example:**

```bash
curl -X POST https://api.example.com/v1/query/offer/aggregate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "where": {"field": "section", "op": "eq", "value": "ACTIVE"},
    "group_by": ["vertical"],
    "aggregations": [
      {"column": "gid", "agg": "count", "alias": "offer_count"}
    ]
  }'
```

**Response:**

```json
{
  "data": [
    {"vertical": "dental", "offer_count": 27},
    {"vertical": "medical", "offer_count": 20}
  ],
  "meta": {
    "group_count": 2,
    "aggregation_count": 1,
    "group_by": ["vertical"],
    "entity_type": "offer",
    "project_gid": "1143843662099250",
    "query_ms": 8.45
  }
}
```

## Performance

### Cache Behavior

Queries read from cached DataFrames. Cache lifecycle:

1. **Cache hit** - DataFrame in memory or S3. Query executes immediately.
2. **Cache miss** - DataFrame not cached. Self-refresh triggers async build.
3. **Build failure** - Circuit breaker open or build failed. Returns 503.

Cache warming happens via:

- Scheduled builds (cron or event-driven)
- Self-refresh on cache miss (if legacy strategy exists)
- Manual cache priming via admin endpoints

### Query Performance

**Fast path:**

- In-memory cache hit: 5-20ms
- S3 cache hit: 50-200ms

**Slow path:**

- Cache miss + self-refresh: 2-10 seconds (first query only, subsequent queries wait for build)
- Circuit breaker open: Immediate 503

**Optimization tips:**

- Warm cache before query traffic (scheduled or manual)
- Use section parameter for large projects (reduces rows)
- Limit predicate depth (each level adds filter overhead)
- Select only needed columns (reduces serialization cost)
- Use pagination for large result sets

### Freshness Metadata

Response includes cache freshness indicators:

- `freshness` (string) - "fresh" (< staleness threshold), "stale" (> threshold but < TTL), "expired" (> TTL)
- `data_age_seconds` (float) - Seconds since last cache build
- `staleness_ratio` (float) - `data_age_seconds / staleness_threshold`

Use freshness metadata to decide if results are acceptable or if a cache refresh is needed.

## Error Handling

### Common Errors

**503 Cache Not Warmed:**

DataFrame not available after self-refresh attempt.

```json
{
  "error": "CACHE_NOT_WARMED",
  "message": "DataFrame unavailable for offer. Cache warming may be in progress or build failed.",
  "entity_type": "offer",
  "retry_after_seconds": 30
}
```

**Resolution:**

- Retry after 30 seconds
- Check cache warming status
- Trigger manual cache build via admin endpoint

**422 Unknown Field:**

Field not in entity schema.

```json
{
  "error": "UNKNOWN_FIELD",
  "message": "Unknown field: invalid_field",
  "available_fields": ["gid", "name", "section", "vertical", "office_phone"]
}
```

**Resolution:**

- Check available fields in schema
- Use correct field name (case-sensitive)

**422 Invalid Operator:**

Operator not compatible with field type.

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

**Resolution:**

- Use operator compatible with field dtype
- Check operator compatibility table

**422 Coercion Failed:**

Value cannot be coerced to field dtype.

```json
{
  "error": "COERCION_FAILED",
  "message": "Cannot coerce 'not-a-number' to Int64 for field 'count'",
  "field": "count",
  "field_dtype": "Int64",
  "value": "not-a-number"
}
```

**Resolution:**

- Use correct value type for field
- Check schema for expected types

**400 Query Too Complex:**

Predicate depth exceeds maximum.

```json
{
  "error": "QUERY_TOO_COMPLEX",
  "message": "Predicate tree depth 6 exceeds maximum of 5",
  "max_depth": 5
}
```

**Resolution:**

- Simplify predicate tree
- Flatten nested groups

**401 Missing Auth:**

Authorization header missing or invalid.

```json
{
  "error": "MISSING_AUTH",
  "message": "Authorization header required"
}
```

**Resolution:**

- Include `Authorization: Bearer <TOKEN>` header
- Use valid S2S JWT token

### Empty Results

Query returns empty data array if no matches:

```json
{
  "data": [],
  "meta": {
    "total_count": 0,
    "returned_count": 0,
    "limit": 100,
    "offset": 0,
    "entity_type": "offer",
    "project_gid": "1143843662099250",
    "query_ms": 5.23
  }
}
```

This is not an error. Check filter criteria if unexpected.

## Python Client Usage

The autom8_asana Python SDK does not yet provide a query client. Use direct HTTP requests:

```python
import httpx

async def query_offers(token: str, vertical: str) -> list[dict]:
    """Query offers by vertical."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.example.com/v1/query/offer/rows",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "where": {"field": "vertical", "op": "eq", "value": vertical},
                "select": ["gid", "name", "office_phone"],
                "limit": 100,
            },
        )
        response.raise_for_status()
        return response.json()["data"]

# Usage
offers = await query_offers(service_token, "dental")
```

**Error handling:**

```python
import httpx

async def query_with_retry(token: str, entity_type: str, where: dict) -> dict:
    """Query with 503 retry logic."""
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.post(
                f"https://api.example.com/v1/query/{entity_type}/rows",
                headers={"Authorization": f"Bearer {token}"},
                json={"where": where},
            )

            if response.status_code == 503:
                # Cache not warm, retry after delay
                data = response.json()
                retry_after = data.get("retry_after_seconds", 30)
                await asyncio.sleep(retry_after)
                continue

            response.raise_for_status()
            return response.json()
```

**Pagination:**

```python
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
