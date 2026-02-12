# Entity Resolution Guide

## Overview

Entity resolution maps business identifiers (phone numbers, verticals, offer IDs) to Asana task GIDs. Use this API to find existing entities in Asana without manual lookup.

**Typical use case**: You have a phone number and vertical from your business system. You need the Asana task GID to create dependencies, fetch custom fields, or trigger workflows.

**Key features**:
- Batch resolution (up to 1000 criteria per request)
- O(1) index lookups for fast response times
- Schema-driven validation with helpful error messages
- Multi-match detection with disambiguation support
- Optional field enrichment for matched entities

## Quick Start

Resolve a unit by phone and vertical:

```bash
curl -X POST https://api.autom8.app/v1/resolve/unit \
  -H "Authorization: Bearer YOUR_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": [
      {
        "phone": "+15551234567",
        "vertical": "dental"
      }
    ]
  }'
```

Response:

```json
{
  "results": [
    {
      "gid": "1234567890123456",
      "gids": ["1234567890123456"],
      "match_count": 1,
      "error": null,
      "data": null
    }
  ],
  "meta": {
    "resolved_count": 1,
    "unresolved_count": 0,
    "entity_type": "unit",
    "project_gid": "1201081073731555",
    "available_fields": ["gid", "name", "office_phone", "vertical"],
    "criteria_schema": ["phone", "vertical"]
  }
}
```

## Authentication

All resolution endpoints require service-to-service (S2S) authentication using JWT tokens. Personal Access Tokens (PAT) are not supported.

**Header format**:
```
Authorization: Bearer <SERVICE_TOKEN>
```

**Error responses**:
- 401 MISSING_AUTH: No Authorization header provided
- 401 SERVICE_TOKEN_REQUIRED: PAT token provided (use S2S token instead)

## Supported Entity Types

The resolution API supports these entity types:

| Entity Type | Resolution Criteria | Example |
|-------------|---------------------|---------|
| `unit` | phone + vertical | `{"phone": "+15551234567", "vertical": "dental"}` |
| `business` | phone + vertical | Same as unit (resolves parent business) |
| `offer` | offer_id or phone + vertical + offer_name | `{"offer_id": "offer-12345"}` |
| `contact` | contact_email or contact_phone | `{"contact_email": "owner@example.com"}` |

**Entity type discovery**: Use `GET /v1/resolve/{entity_type}/schema` to discover valid fields for each entity type.

## REST API

### Resolve Entities

**Endpoint**: `POST /v1/resolve/{entity_type}`

**Path parameters**:
- `entity_type`: Entity type to resolve (unit, business, offer, contact)

**Request body**:

```json
{
  "criteria": [
    {
      "phone": "+15551234567",
      "vertical": "dental"
    },
    {
      "phone": "+15559876543",
      "vertical": "medical"
    }
  ],
  "fields": ["name", "vertical"]
}
```

**Request fields**:
- `criteria` (required): Array of lookup criteria (max 1000 items)
- `fields` (optional): Array of field names to include in response data

**Response**:

```json
{
  "results": [
    {
      "gid": "1234567890123456",
      "gids": ["1234567890123456"],
      "match_count": 1,
      "error": null,
      "data": [
        {
          "gid": "1234567890123456",
          "name": "Acme Dental",
          "vertical": "dental"
        }
      ]
    },
    {
      "gid": null,
      "gids": null,
      "match_count": 0,
      "error": "NOT_FOUND",
      "data": null
    }
  ],
  "meta": {
    "resolved_count": 1,
    "unresolved_count": 1,
    "entity_type": "unit",
    "project_gid": "1201081073731555",
    "available_fields": ["gid", "name", "office_phone", "vertical"],
    "criteria_schema": ["phone", "vertical"]
  }
}
```

**Response fields**:

`results` array (one per criterion, in request order):
- `gid`: First matching GID or null (backwards compatible)
- `gids`: All matching GIDs (use this for multi-match handling)
- `match_count`: Number of matches found
- `error`: Error code if resolution failed (NOT_FOUND, INVALID_CRITERIA, etc.)
- `data`: Field values for each match (only when fields requested)

`meta` object:
- `resolved_count`: Number of successful resolutions
- `unresolved_count`: Number of failed resolutions
- `entity_type`: Entity type that was resolved
- `project_gid`: Asana project GID used for resolution
- `available_fields`: Valid field names for this entity type (from schema)
- `criteria_schema`: Field names used in the criteria

## Batch Resolution

Send up to 1000 criteria in one request for efficient bulk lookups.

**Example** (resolve multiple units):

```bash
curl -X POST https://api.autom8.app/v1/resolve/unit \
  -H "Authorization: Bearer YOUR_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": [
      {"phone": "+15551111111", "vertical": "dental"},
      {"phone": "+15552222222", "vertical": "medical"},
      {"phone": "+15553333333", "vertical": "dental"}
    ]
  }'
```

**Response guarantees**:
- Results returned in same order as criteria
- One result per criterion (even if resolution fails)
- Batch limit: 1000 criteria per request
- Exceeding batch limit returns 422 VALIDATION_ERROR

**Performance**: Batch resolution groups criteria by lookup columns, builds each index once, then performs O(1) lookups. A 100-item batch with mixed criteria typically completes in 200-500ms.

## Resolution Criteria

### Dynamic Schema Validation

Criteria fields are validated against entity schemas at runtime. Invalid fields return 422 VALIDATION_ERROR with available fields list.

**Example validation error**:

```json
{
  "error": "MISSING_REQUIRED_FIELD",
  "message": "Criterion 0: Unknown field(s) for unit: ['invalid_field']. Valid fields: ['gid', 'name', 'office_phone', 'vertical']"
}
```

### Field Name Normalization

The API automatically normalizes legacy field names to schema column names:

| Input Field | Normalized Field | Entity Context |
|-------------|------------------|----------------|
| `phone` | `office_phone` | unit, business |
| `email` | `contact_email` | contact |
| `vertical` | `vertical` | No change (exact match) |

**Hierarchical alias resolution**: The system walks entity relationships to resolve fields. For unit entities, `phone` maps to `office_phone` via the business->office hierarchy.

### Phone Number Format

Phone numbers must use E.164 format: `+[country][number]`

**Valid examples**:
- `+15551234567` (US number)
- `+442071234567` (UK number)
- `+819012345678` (Japan number)

**Invalid examples**:
- `5551234567` (missing + prefix)
- `+0551234567` (country code cannot start with 0)
- `+1 555 123 4567` (no spaces allowed)

Validation errors return 422 with message: "Invalid E.164 format: {phone}. Expected format: +[country][number]"

### Discovery API

Get valid criteria fields for an entity type:

```bash
curl https://api.autom8.app/v1/resolve/unit/schema \
  -H "Authorization: Bearer YOUR_SERVICE_TOKEN"
```

Response includes:
- Required fields for resolution
- Optional discriminator fields
- Data types for each field
- Example criteria

## Resolution Strategies

The system uses multiple strategies to find entities, attempting each in order until a match is found.

### Index Lookup (Primary Strategy)

Uses in-memory indexes built from cached DataFrames. Indexes are keyed by the criterion fields you provide.

**How it works**:
1. System validates criterion fields against entity schema
2. Groups criteria by field combination (e.g., [phone, vertical])
3. Builds or retrieves index for that field combination
4. Performs O(1) lookup for each criterion in the group

**Performance**: 1-5ms per lookup after index build. Indexes are cached for 1 hour (configurable via `ASANA_CACHE_TTL_DYNAMIC_INDEX`).

**Index cache behavior**:
- Separate index per field combination (phone+vertical vs. offer_id)
- Max 5 indexes per entity type (LRU eviction)
- Indexes cleared on project data refresh

### Hierarchy Traversal (Fallback Strategy)

When index lookup fails or is unavailable, the system traverses Asana's task hierarchy to find related entities.

**Example** (unit to business):
1. Start at unit task (trigger entity)
2. Fetch parent task (2 API calls)
3. Validate parent is business type
4. Return business task GID

**Performance**: 3-8 API calls depending on hierarchy depth. Only used when DataFrame cache is unavailable (startup, cache miss).

### Session Cache (Cross-Request Optimization)

Within a single resolution context, previously resolved entities are cached in memory. Subsequent requests for the same entity return instantly without API calls or index lookups.

**Use case**: Resolving business, then unit, then contact from the same business avoids redundant API calls.

## Budget and Timeouts

Resolution chains enforce API call budgets to prevent unbounded execution.

### API Budget

Default budget: 8 API calls per resolution chain (configurable via `ResolutionContext(max_api_calls=N)`).

**Budget consumption**:
- Index lookup: 0 API calls (uses cached DataFrame)
- Hierarchy traversal: 2-5 API calls (parent fetching)
- Holder resolution: 1-2 API calls (subtask listing + validation)

**Budget exhaustion**: When budget is exceeded, resolution returns error with diagnostics:

```json
{
  "gid": null,
  "error": "BUDGET_EXHAUSTED",
  "match_count": 0
}
```

**Diagnostics** (logged, not returned in API response):
```
[
  "session_cache: no result",
  "navigation_ref: no result",
  "hierarchy_traversal: no result",
  "Budget exhausted after 8 API calls"
]
```

### Request Timeout

Default timeout: 120 seconds per HTTP request (configured at Bash tool level).

**Timeout behavior**:
- Partial results returned for completed criteria
- Incomplete criteria return TIMEOUT error
- Batch resolution continues until overall request timeout

**Timeout tuning**: For large batches (500+ criteria), consider chunking into multiple requests rather than increasing timeout.

## Error Handling

### Common Error Codes

| Code | Meaning | Resolution |
|------|---------|-----------|
| `NOT_FOUND` | No entity matches criteria | Check phone format, verify entity exists in Asana |
| `INVALID_CRITERIA` | Criterion validation failed | Check field names against schema, fix data types |
| `INDEX_UNAVAILABLE` | Index build failed | Retry request (transient cache error) |
| `LOOKUP_ERROR` | Lookup execution failed | Check logs for details, contact support if persistent |
| `BUDGET_EXHAUSTED` | API call budget exceeded | Simplify criteria or increase budget (internal use) |

### HTTP Status Codes

| Status | Error Code | Description |
|--------|------------|-------------|
| 200 | - | Success (check individual results for NOT_FOUND) |
| 401 | MISSING_AUTH | No Authorization header |
| 401 | SERVICE_TOKEN_REQUIRED | PAT token used instead of S2S |
| 404 | UNKNOWN_ENTITY_TYPE | Invalid entity type in URL path |
| 422 | MISSING_REQUIRED_FIELD | Criterion missing required fields |
| 422 | INVALID_FIELD | Unknown field name in criteria or fields list |
| 422 | VALIDATION_ERROR | Batch size exceeds 1000 or phone format invalid |
| 503 | DISCOVERY_INCOMPLETE | Service still initializing (retry after 5s) |
| 503 | PROJECT_NOT_CONFIGURED | Entity type not configured (contact support) |

### Error Response Format

```json
{
  "error": "MISSING_REQUIRED_FIELD",
  "message": "Criterion 2: Missing required field 'vertical' for unit resolution",
  "available_types": ["unit", "business", "offer", "contact"]
}
```

### Multi-Match Handling

When multiple entities match the same criteria, the response includes all matches:

```json
{
  "gid": "1234567890123456",
  "gids": ["1234567890123456", "9876543210987654"],
  "match_count": 2,
  "error": null
}
```

**Client handling**:
- Check `match_count` to detect ambiguity
- Use `gids` array to access all matches
- Use `gid` for backwards compatibility (returns first match)
- Add discriminator fields to criteria to narrow results (e.g., add `offer_name` when resolving offers)

## Caching Behavior

### DataFrame Cache

Entity DataFrames are cached in Redis for fast index builds.

**Cache TTL**:
- Default: 1 hour (configurable via `ASANA_CACHE_TTL_DATAFRAME`)
- Controlled by DataFrameCache provider
- Warmup happens at service startup and periodically via background tasks

**Cache freshness**: Response metadata does not include cache age. Check application logs for cache hit/miss events.

### Index Cache

DynamicIndex structures are cached in-memory per process.

**Cache TTL**: 1 hour (configurable via `ASANA_CACHE_TTL_DYNAMIC_INDEX`)

**Cache eviction**:
- LRU policy: Max 5 indexes per entity type
- Automatic eviction on DataFrame cache refresh
- Manual reset via service restart or internal admin endpoint

**Cache warming**: Indexes are built on-demand during first request with a given field combination. Subsequent requests with the same fields use the cached index.

## Python Client Example

```python
import httpx
import asyncio

async def resolve_unit(phone: str, vertical: str) -> str | None:
    """Resolve unit GID by phone and vertical."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.autom8.app/v1/resolve/unit",
            headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
            json={
                "criteria": [
                    {"phone": phone, "vertical": vertical}
                ]
            }
        )
        response.raise_for_status()

        data = response.json()
        result = data["results"][0]

        if result["error"]:
            print(f"Resolution failed: {result['error']}")
            return None

        if result["match_count"] > 1:
            print(f"Multiple matches found: {result['gids']}")
            # Handle ambiguity - use first match or prompt user

        return result["gid"]

# Usage
gid = asyncio.run(resolve_unit("+15551234567", "dental"))
print(f"Unit GID: {gid}")
```

## Field Enrichment

Request additional fields beyond GID by including a `fields` array in the request.

**Example** (get name and vertical with resolution):

```bash
curl -X POST https://api.autom8.app/v1/resolve/unit \
  -H "Authorization: Bearer YOUR_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": [
      {"phone": "+15551234567", "vertical": "dental"}
    ],
    "fields": ["name", "vertical", "mrr"]
  }'
```

**Response with enrichment**:

```json
{
  "results": [
    {
      "gid": "1234567890123456",
      "gids": ["1234567890123456"],
      "match_count": 1,
      "error": null,
      "data": [
        {
          "gid": "1234567890123456",
          "name": "Acme Dental",
          "vertical": "dental",
          "mrr": 5000
        }
      ]
    }
  ],
  "meta": {
    "available_fields": ["gid", "name", "office_phone", "vertical", "mrr", "specialty"]
  }
}
```

**Field enrichment behavior**:
- `gid` always included in data objects (for correlation)
- Unknown fields return 422 INVALID_FIELD error
- Null values returned for missing data
- Data array matches order of `gids` array (one object per match)

**Available fields**: Check `meta.available_fields` in response or use schema discovery endpoint.

## Troubleshooting

### Resolution returns NOT_FOUND but entity exists

**Check**:
- Phone number uses E.164 format (+15551234567 not 5551234567)
- Vertical spelling matches Asana custom field exactly (case-sensitive)
- Entity is in the correct project (check `meta.project_gid`)
- DataFrame cache is up-to-date (check service logs for last warmup)

**Solution**: Use Asana UI to verify exact field values, then match criteria exactly.

### Resolution times out for large batches

**Symptoms**:
- Request exceeds 120s timeout
- Batch size 500+ criteria

**Solution**:
- Chunk batch into multiple requests (200-300 criteria per request)
- Check DataFrame cache status (cold cache triggers rebuild)
- Review logs for slow index builds (indicates missing cache)

### Multiple matches returned unexpectedly

**Symptoms**:
- `match_count > 1` for criteria you expect to be unique
- Different GIDs returned across requests

**Root causes**:
- Duplicate entities in Asana (same phone+vertical)
- Criteria not discriminating enough (need offer_name for offers)

**Solution**:
- Add discriminator fields to criteria (e.g., offer_name, contact_email)
- Review Asana project for duplicate tasks
- Use `gids` array to handle all matches explicitly

### 503 DISCOVERY_INCOMPLETE on first request

**Symptoms**:
- Service returns 503 immediately after deployment
- Error message: "Entity resolver startup discovery has not completed"

**Solution**:
- Wait 5-10 seconds for startup discovery to complete
- Retry request
- Check service logs for discovery completion: `entity_resolution_ready`

### Field enrichment returns null values

**Symptoms**:
- `data` array contains `null` for requested fields
- GID resolution succeeds but field values missing

**Root causes**:
- Field not populated in Asana task (custom field empty)
- Field name typo in request
- Field not included in DataFrame schema

**Solution**:
- Verify field exists in `meta.available_fields`
- Check Asana task for field value
- Use schema discovery endpoint to confirm field name
