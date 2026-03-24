# Entity Resolver API

> Resolve business identifiers (phone/vertical, offer_id, etc.) to Asana task GIDs using entity-type-specific resolution strategies.

## Authentication

S2S JWT (service-to-service) authentication required via `Authorization: Bearer <token>` header.

PAT (Personal Access Token) authentication is NOT supported. Requests with PAT tokens receive `401 SERVICE_TOKEN_REQUIRED` error.

The endpoint internally uses a bot PAT to communicate with Asana's API, but client authentication must use service tokens.

## Endpoints

### `POST /v1/resolve/{entity_type}`

Resolve entity identifiers to Asana task GIDs in batch.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_type` | string | Entity type to resolve (unit, business, offer, contact) |

**Request Body:**

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
  "fields": ["gid", "name", "mrr"],
  "active_only": true
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `criteria` | array | Yes | - | List of lookup criteria (max 1000 items) |
| `fields` | array | No | `null` | Optional field filtering (returns enriched data) |
| `active_only` | boolean | No | `true` | Filter results to active/activating statuses only. **Breaking change**: defaults to `true`. Pass `false` to restore prior behavior (all matches returned). Ignored for entity types without a status classifier. |

**Criterion Object:**

The criterion object accepts entity-specific fields dynamically. Use `GET /v1/resolve/{entity_type}/schema` to discover valid fields for each entity type.

Common fields:

| Field | Type | Description |
|-------|------|-------------|
| `phone` | string | E.164 formatted phone number (e.g., `+15551234567`) |
| `vertical` | string | Business vertical (dental, medical, optical, etc.) |

Offer-specific fields:

| Field | Type | Description |
|-------|------|-------------|
| `offer_id` | string | Offer identifier |
| `offer_name` | string | Offer name (for phone/vertical + discriminator) |

Contact-specific fields:

| Field | Type | Description |
|-------|------|-------------|
| `contact_email` | string | Email address |
| `contact_phone` | string | Phone number |

Dynamic fields (any schema column):
- `mrr`, `specialty`, `weekly_ad_spend`, `stripe_id`, etc.
- Validated against entity schema at runtime
- Use schema discovery endpoint to find available fields

**Phone Number Validation:**

Phone numbers must conform to ITU-T E.164 format: `+[country][number]`

- Must start with `+`
- First digit after `+` must be non-zero (1-9)
- Total length: 2-16 characters (including `+`)
- Example: `+15551234567` (valid), `5551234567` (invalid)

**Response Body:**

```json
{
  "results": [
    {
      "gid": "1234567890123456",
      "gids": ["1234567890123456"],
      "match_count": 1,
      "total_match_count": null,
      "status": ["active"],
      "error": null,
      "data": [
        {
          "gid": "1234567890123456",
          "name": "Unit - Dental Practice",
          "mrr": 5000
        }
      ]
    },
    {
      "gid": null,
      "gids": null,
      "match_count": 0,
      "total_match_count": null,
      "status": null,
      "error": "NOT_FOUND",
      "data": null
    }
  ],
  "meta": {
    "resolved_count": 1,
    "unresolved_count": 1,
    "entity_type": "unit",
    "project_gid": "1201081073731555",
    "available_fields": ["gid", "name", "office_phone", "vertical", "mrr", "weekly_ad_spend"],
    "criteria_schema": ["phone", "vertical"]
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | Resolution results in same order as input criteria |
| `meta` | object | Response metadata |

**Result Object:**

| Field | Type | Description |
|-------|------|-------------|
| `gid` | string \| null | First matching GID or null if not found (backwards compatible) |
| `gids` | array \| null | All matching GIDs (supports multi-match scenarios) |
| `match_count` | integer | Number of matches found (post-filter when `active_only=true`) |
| `total_match_count` | integer \| null | Pre-filter total match count. Present when `active_only=true` and filtering removed matches; `null` when `active_only=false` or no filtering occurred. |
| `status` | array \| null | Activity status for each match, parallel to `gids`. Each entry is an `AccountActivity` value (`active`, `activating`, `inactive`, `ignored`) or `null` (unknown section). The entire field is `null` when no classifier exists for the entity type. |
| `error` | string \| null | Error code if resolution failed (`NOT_FOUND`, `MULTIPLE_MATCHES`) |
| `data` | array \| null | Field data for each match (only when `fields` requested) |

**Metadata Object:**

| Field | Type | Description |
|-------|------|-------------|
| `resolved_count` | integer | Number of successfully resolved criteria |
| `unresolved_count` | integer | Number of failed resolutions |
| `entity_type` | string | Entity type that was resolved |
| `project_gid` | string | Asana project GID used for resolution |
| `available_fields` | array | Valid field names for this entity (queryable fields from schema) |
| `criteria_schema` | array | Fields used in the resolution request criteria |

**Example: Unit Resolution (cURL)**

```bash
curl -X POST https://api.example.com/v1/resolve/unit \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": [
      {"phone": "+15551234567", "vertical": "dental"},
      {"phone": "+15559876543", "vertical": "medical"}
    ]
  }'
```

**Example: Unit Resolution with Fields (cURL)**

```bash
curl -X POST https://api.example.com/v1/resolve/unit \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": [
      {"phone": "+15551234567", "vertical": "dental"}
    ],
    "fields": ["gid", "name", "mrr", "weekly_ad_spend"]
  }'
```

**Example: Offer Resolution (cURL)**

```bash
curl -X POST https://api.example.com/v1/resolve/offer \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": [
      {"offer_id": "OFF-12345"}
    ]
  }'
```

**Example: Python httpx**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://api.example.com/v1/resolve/unit",
        headers={
            "Authorization": f"Bearer {s2s_token}",
            "Content-Type": "application/json"
        },
        json={
            "criteria": [
                {"phone": "+15551234567", "vertical": "dental"},
                {"phone": "+15559876543", "vertical": "medical"}
            ],
            "fields": ["gid", "name", "mrr"]
        }
    )
    result = response.json()

    for criterion, res in zip(request["criteria"], result["results"]):
        if res["gid"]:
            print(f"Found: {criterion} -> {res['gid']}")
            if res["data"]:
                print(f"  Data: {res['data'][0]}")
        else:
            print(f"Not found: {criterion} (error: {res['error']})")
```

**Example: Batch Resolution**

```python
import httpx

async def resolve_batch(criteria: list[dict], entity_type: str, token: str):
    """Resolve up to 1000 criteria in a single request."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.example.com/v1/resolve/{entity_type}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={"criteria": criteria},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()

# Example: Resolve 500 units
criteria = [
    {"phone": f"+1555000{i:04d}", "vertical": "dental"}
    for i in range(500)
]
result = await resolve_batch(criteria, "unit", s2s_token)
print(f"Resolved: {result['meta']['resolved_count']}/500")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 401 | `MISSING_AUTH` | No Authorization header provided |
| 401 | `SERVICE_TOKEN_REQUIRED` | PAT token provided (S2S JWT required) |
| 404 | `UNKNOWN_ENTITY_TYPE` | Entity type not recognized or not resolvable |
| 422 | `VALIDATION_ERROR` | Request body validation failed (invalid phone, batch too large) |
| 422 | `MISSING_REQUIRED_FIELD` | Criterion missing required fields for entity type |
| 422 | `INVALID_FIELD` | Requested field not found in entity schema |
| 500 | `RESOLUTION_ERROR` | Unexpected error during resolution |
| 501 | `STRATEGY_NOT_IMPLEMENTED` | Resolution strategy not implemented for entity type |
| 503 | `DISCOVERY_INCOMPLETE` | Entity resolver startup discovery not completed |
| 503 | `PROJECT_NOT_CONFIGURED` | No project configured for entity type |
| 503 | `BOT_PAT_UNAVAILABLE` | Bot PAT not configured for S2S Asana access |

**Error Response Format:**

```json
{
  "detail": {
    "error": "UNKNOWN_ENTITY_TYPE",
    "message": "Unknown entity type: invalid_type. Supported types: unit, business, offer, contact",
    "available_types": ["unit", "business", "offer", "contact"]
  }
}
```

**Validation Error Example:**

```json
{
  "detail": {
    "error": "MISSING_REQUIRED_FIELD",
    "message": "Criterion 0: Missing required field: phone; Missing required field: vertical"
  }
}
```

**Invalid Field Error Example:**

```json
{
  "detail": {
    "error": "INVALID_FIELD",
    "message": "Field 'invalid_field' not found in Unit schema. Available fields: gid, name, office_phone, vertical, mrr, weekly_ad_spend"
  }
}
```

## Resolution Metadata

The `meta` object provides context about the resolution batch:

### `available_fields`

Lists queryable fields for the entity type. These fields can be requested via the `fields` parameter.

Fields are derived from the entity schema and include:
- Fields with a data source (custom fields, core fields)
- Core fields: `gid`, `name`, `parent_gid`

Use `GET /v1/resolve/{entity_type}/schema` for detailed field information.

### `criteria_schema`

Lists all unique field names used across all criteria in the request. Useful for understanding what fields were provided for resolution.

Example: If criteria include `[{"phone": "...", "vertical": "..."}, {"phone": "..."}]`, the `criteria_schema` will be `["phone", "vertical"]`.

## Schema Discovery

### `GET /v1/resolve/{entity_type}/schema`

Returns the schema definition for an entity type, including valid criterion fields and queryable fields.

See schema discovery endpoint documentation for details.

## Multi-Match Behavior

When multiple tasks match a single criterion:

- `gid`: First match GID (backwards compatible)
- `gids`: All matching GIDs
- `match_count`: Total number of matches
- `error`: `MULTIPLE_MATCHES` (if multi-match is an error condition)
- `data`: Field data for all matches (if `fields` requested)

Example multi-match response:

```json
{
  "gid": "1234567890123456",
  "gids": ["1234567890123456", "9876543210987654"],
  "match_count": 2,
  "total_match_count": null,
  "status": ["active", "activating"],
  "error": null,
  "data": [
    {"gid": "1234567890123456", "name": "Unit A"},
    {"gid": "9876543210987654", "name": "Unit B"}
  ]
}
```

## Status Filtering

The `active_only` parameter controls whether results are filtered by entity activity status.

**`active_only=true` (default)**:
- Only GIDs with `active` or `activating` status are returned
- GIDs with `inactive`, `ignored`, or `null` (unknown) status are excluded
- `match_count` reflects the post-filter count
- `total_match_count` shows the pre-filter total when filtering removed matches

**`active_only=false`**:
- All matching GIDs are returned regardless of status
- GIDs are ordered by priority: `active` > `activating` > `inactive` > `ignored` > unknown
- `total_match_count` is `null` (no filtering occurred)

**Entity types without a classifier** (e.g., `contact`, `business`):
- `active_only` is ignored; all matches are returned
- `status` is `null` in the response

### AccountActivity Values

The `status` array entries use the `AccountActivity` vocabulary:

| Value | Description |
|-------|-------------|
| `"active"` | Actively running entities (e.g., Month 1, Consulting, Active, STAGED, ACTIVE sections) |
| `"activating"` | Entities in onboarding or implementation (e.g., Onboarding, Implementing, ACTIVATING, LAUNCH ERROR sections) |
| `"inactive"` | Paused or cancelled entities (e.g., Paused, Cancelled, INACTIVE, ACCOUNT ERROR sections) |
| `"ignored"` | Template or system entities (e.g., Templates, Sales Process, Complete sections) |
| `null` | Section not recognized by the classifier (unknown status) |

### Example: Filtered Response with `active_only=true`

When `active_only=true` filters out matches, `total_match_count` reveals the original count:

```json
{
  "gid": "1234567890123456",
  "gids": ["1234567890123456"],
  "match_count": 1,
  "total_match_count": 3,
  "status": ["active"],
  "error": null,
  "data": null
}
```

In this example, 3 entities matched the criteria but only 1 had an active status.

### Example: Unfiltered Response with `active_only=false`

```json
{
  "gid": "1234567890123456",
  "gids": ["1234567890123456", "1111111111111111", "2222222222222222"],
  "match_count": 3,
  "total_match_count": null,
  "status": ["active", "inactive", "ignored"],
  "error": null,
  "data": null
}
```

GIDs are ordered by priority (`active` first), and all matches are included.

### Example: Entity Type Without Classifier

For entity types without a status classifier (e.g., `contact`), the `status` field is `null`:

```json
{
  "gid": "3333333333333333",
  "gids": ["3333333333333333"],
  "match_count": 1,
  "total_match_count": null,
  "status": null,
  "error": null,
  "data": null
}
```

## Batch Size Limits

Maximum 1000 criteria per request. Requests exceeding this limit receive `422 VALIDATION_ERROR`:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "criteria"],
      "msg": "Batch size 1500 exceeds maximum 1000. Please chunk requests.",
      "input": [...],
      "ctx": {"error": "..."}
    }
  ]
}
```

For larger batches, chunk into multiple requests:

```python
async def resolve_large_batch(criteria: list[dict], entity_type: str, token: str):
    """Resolve more than 1000 criteria by chunking."""
    CHUNK_SIZE = 1000
    results = []

    for i in range(0, len(criteria), CHUNK_SIZE):
        chunk = criteria[i:i + CHUNK_SIZE]
        batch_result = await resolve_batch(chunk, entity_type, token)
        results.extend(batch_result["results"])

    return results
```

## Resolution Strategies

Resolution behavior is entity-type-specific and determined by the resolution strategy:

- **Unit/Business**: Resolves by `phone` + `vertical` (phone mapped to office_phone)
- **Offer**: Resolves by `offer_id` (or phone/vertical + offer_name discriminator)
- **Contact**: Resolves by `contact_email` or `contact_phone`
- **Universal**: Fallback strategy for any entity with schema and registered project

Strategies validate required fields and return appropriate errors for missing or invalid criteria.

## Field Filtering

When `fields` is provided in the request:

1. Resolution returns only the specified fields in the `data` array
2. Fields are validated against the entity schema
3. Invalid fields cause `422 INVALID_FIELD` error
4. Field data is fetched from Asana after GID resolution

Field filtering adds latency (additional Asana API call per result). Use only when enriched data is needed.

## Notes

- Results are returned in the same order as input criteria
- Resolution is performed in batch against the entity's Asana project
- Entity project GIDs are discovered at service startup
- Phone numbers are normalized to E.164 format before resolution
- Field names in criteria are case-sensitive
- The `gid` field in results maintains backwards compatibility with single-match behavior
- **Breaking change**: `active_only` defaults to `true`. Callers who previously received all matches now receive only active/activating matches by default. Pass `active_only: false` to restore prior behavior.
- The `status` list is always parallel to `gids` (same length, same order). When the entity type has no classifier, `status` is `null` rather than a list.
- `ACTIVATING` status is distinct from `ACTIVE` in the `status` list; both pass the `active_only=true` filter
