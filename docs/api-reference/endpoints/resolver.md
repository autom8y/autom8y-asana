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
| `entity_type` | string | Entity type to resolve (`unit`, `business`, `offer`, `contact`, `asset_edit`, `asset_edit_holder`) |

See [Resolvable Entity Types](#resolvable-entity-types) for full documentation on each type, required fields, and cascade dependencies.

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
| `error` | string \| null | Error code if resolution failed (`NOT_FOUND`, `MULTIPLE_MATCHES`, `RESOLUTION_NULL_SLOT`, `INDEX_UNAVAILABLE`, `INVALID_CRITERIA`). See [Result Error Codes](#result-error-codes). |
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
| 503 | `CASCADE_NOT_READY` | Cascade data quality below threshold for reliable resolution |


See [HTTP Error Codes](#http-error-codes) for errors that originate from upstream Asana API failures and the catch-all fallback path.

**Error Response Format:**

```json
{
  "detail": {
    "error": "UNKNOWN_ENTITY_TYPE",
    "message": "Unknown entity type: invalid_type. Supported types: unit, business, offer, contact, asset_edit, asset_edit_holder",
    "available_types": ["unit", "business", "offer", "contact", "asset_edit", "asset_edit_holder"],
    "request_id": "req_abc123"
  }
}
```

**Validation Error Example:**

```json
{
  "detail": {
    "error": "MISSING_REQUIRED_FIELD",
    "message": "Criterion 0: Missing required field: phone; Missing required field: vertical",
    "request_id": "req_abc123"
  }
}
```

**Invalid Field Error Example:**

```json
{
  "detail": {
    "error": "INVALID_FIELD",
    "message": "Field 'invalid_field' not found in Unit schema. Available fields: gid, name, office_phone, vertical, mrr, weekly_ad_spend",
    "request_id": "req_abc123"
  }
}
```

## Resolvable Entity Types

The set of valid `entity_type` values is determined at service startup via dynamic discovery. Six entity types are currently resolvable.

| entity_type | category | key_columns | cascade_dependencies | holder_for | has_status_classifier |
|---|---|---|---|---|---|
| `business` | ROOT | `office_phone` | — | — | No |
| `unit` | COMPOSITE | `office_phone`, `vertical` | `office_phone` (cascade-sourced) | — | Yes |
| `contact` | LEAF | `office_phone`, `contact_phone`, `contact_email` | `office_phone` (cascade-sourced) | — | No |
| `offer` | LEAF | `office_phone`, `vertical`, `offer_id` | `office_phone`, `vertical` (cascade-sourced) | — | Yes |
| `asset_edit` | LEAF | `office_phone`, `vertical`, `asset_id`, `offer_id` | `office_phone`, `vertical` (cascade-sourced) | — | No |
| `asset_edit_holder` | HOLDER | `office_phone` | `office_phone` (cascade-sourced — 100% of key columns) | `asset_edit` | No |

**Column definitions:**

- **key_columns** — Fields used to construct the resolution index. All must be present (directly or via cascade) for a successful resolution.
- **cascade_dependencies** — Key columns populated from the cache warm cycle rather than from the resolution request. If the cache has not been warmed, these columns are null and resolution returns `NOT_FOUND` silently.
- **holder_for** — For HOLDER entities, the LEAF entity type this holder contains. HOLDER entities resolve across all leaf records belonging to a business. See [Entity Selection Guide](#entity-selection-guide) for when to use a HOLDER vs LEAF type.
- **has_status_classifier** — Whether this entity type participates in status filtering via `active_only`. Entities without a classifier return all matches regardless of `active_only`.

**Cascade field warming precondition:** Entities with cascade dependencies require cache warmup to have completed before their cascade-sourced key columns are populated. If warmup has not finished for a target business, the resolution returns [`NOT_FOUND`](#result-error-codes) even when the entity exists. `asset_edit_holder` carries the highest risk: its only key column (`office_phone`) is cascade-sourced, so a missing warmup produces `NOT_FOUND` for every request against that business.

---

## Entity Selection Guide

Entity types follow two structural patterns. LEAF entities represent individual records within a project. HOLDER entities represent the collection of all leaf records across projects for a given business. Most consumers want a LEAF type; use a HOLDER type only when you need to enumerate all records for a business without knowing the discriminating criteria.

| When you want | Use |
|---|---|
| A specific asset edit record matching known criteria (vertical, asset_id, offer_id) | `asset_edit` |
| All asset edit records for a business (resolved by phone only) | `asset_edit_holder` |

`asset_edit` resolves within a single project using `office_phone` + `vertical` + `asset_id` + `offer_id` as discriminating keys. Because it uses specific criteria, a failure produces a precise error you can act on.

`asset_edit_holder` resolves at the business level using only `office_phone`. It returns a GID representing the holder task that aggregates all asset edits for that business across projects. The `holder_for` relationship is documented in [Resolvable Entity Types](#resolvable-entity-types).

**Important:** `asset_edit_holder` has 100% cascade dependency — resolution will silently return [`NOT_FOUND`](#result-error-codes) if cache warmup has not completed for the target business. Prefer `asset_edit` whenever you have discriminating criteria available, because `asset_edit` failures produce more diagnostic context than a bare `NOT_FOUND` from the holder path.

Consumers can programmatically discover which entity types are holders (and which leaf type they hold) via the schema discovery endpoint `GET /v1/resolve/{entity_type}/schema`. The `category` field returns `"holder"` for holder entities, and the `holder_for` field returns the target leaf entity name. See [Schema Discovery](#schema-discovery) for details.

---

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

Returns the schema definition for an entity type, including valid criterion fields, queryable fields, and entity category metadata.

**Response Body:**

| Field | Type | Description |
|-------|------|-------------|
| `entity_type` | string | Entity type name |
| `version` | string | Schema version |
| `category` | string | Entity category: `"root"`, `"composite"`, `"leaf"`, or `"holder"` |
| `holder_for` | string \| null | Target leaf entity name (non-null only for HOLDER entities, e.g., `"asset_edit"` for `asset_edit_holder`) |
| `parent_entity` | string \| null | Parent entity name (null for ROOT entities) |
| `queryable_fields` | array | List of queryable field metadata objects |

**Example: Holder entity (asset_edit_holder)**

```json
{
  "entity_type": "asset_edit_holder",
  "version": "1.2.0",
  "category": "holder",
  "holder_for": "asset_edit",
  "parent_entity": "business",
  "queryable_fields": [
    {"name": "gid", "type": "Utf8", "description": "Asana task GID"},
    {"name": "name", "type": "Utf8", "description": "Task name"},
    {"name": "office_phone", "type": "Utf8", "description": "Office phone number"}
  ]
}
```

**Example: Root entity (business)**

```json
{
  "entity_type": "business",
  "version": "1.1.0",
  "category": "root",
  "holder_for": null,
  "parent_entity": null,
  "queryable_fields": [ "..." ]
}
```

**Example: Composite entity (unit)**

```json
{
  "entity_type": "unit",
  "version": "2.0.0",
  "category": "composite",
  "holder_for": null,
  "parent_entity": null,
  "queryable_fields": [ "..." ]
}
```

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

**Entity types without a classifier** (e.g., `contact`, `business`, `asset_edit`):
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

- **Unit**: Resolves by `phone` + `vertical` (phone mapped to office_phone)
- **Business**: Resolves by `phone` only (phone mapped to office_phone)
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

## Result Error Codes

Result-level errors appear in `results[n].error` and indicate why a specific criterion failed. They are distinct from HTTP-level errors, which appear in the `detail` object and indicate why the entire request failed.

| Error Code | When It Fires | Consumer Action |
|---|---|---|
| `NOT_FOUND` | No matching entity for the criterion | Verify criterion values. If the entity type has cascade dependencies (see [Resolvable Entity Types](#resolvable-entity-types)), confirm that cache warmup has completed for the target business. |
| `MULTIPLE_MATCHES` | More than one entity matches the criterion | Narrow the criterion with additional discriminating fields, or pass `active_only=false` to inspect all matches. |
| `RESOLUTION_NULL_SLOT` | Group coroutine completed without writing to result slot (criterion never processed) | Contact support with `request_id` — indicates a resolution pipeline fault. |
| `INDEX_UNAVAILABLE` | The resolution index for the entity type failed to build | Retry after cache warmup completes. Check service health if the error persists. |
| `INVALID_CRITERIA` | Criterion fields do not match the entity schema for this type | Verify field names against the schema via `GET /v1/resolve/{entity_type}/schema`. |
| `LOOKUP_ERROR` | A per-criterion data operation failed during resolution (e.g., type conversion error, field access error, or transient cache failure) | Retry the specific criterion. If persistent, verify criterion field types match schema. |

**`NOT_FOUND` is the most ambiguous code.** It can result from a genuine absence of the entity or from a silent cascade failure when warmup has not completed. Before escalating a `NOT_FOUND` result, confirm warmup status for the target business. See [Resolvable Entity Types](#resolvable-entity-types) to identify which entity types have cascade dependencies.

See also: [HTTP Error Codes](#http-error-codes) for request-level failures that prevent results from being produced at all.

---

## HTTP Error Codes

Some errors originate from the upstream Asana API during resolution and are proxied back to the caller. These are distinct from the service-originated errors listed in the endpoint Errors table above.

**Upstream Asana errors**

| HTTP Status | Error Code | Condition | Consumer Action |
|---|---|---|---|
| 429 | (from upstream) | Asana rate limit exceeded | Retry with exponential backoff; reduce request concurrency. |
| 502 | `UPSTREAM_ERROR` | Asana returned a server error or the connection to Asana failed | Check Asana service status; retry after a delay. |
| 504 | `UPSTREAM_TIMEOUT` | Request to Asana API timed out | Retry with a reduced batch size; check Asana service status. |

**Catch-all fallback**

| HTTP Status | Error Code | Condition | Consumer Action |
|---|---|---|---|
| 500 | `RESOLUTION_ERROR` | Unexpected exception not covered by other error codes | Include the `request_id` from the response headers when reporting. This code indicates an unhandled condition in the service. |

**`RESOLUTION_ERROR` (HTTP 500) vs `RESOLUTION_NULL_SLOT` (in results):** `RESOLUTION_ERROR` means the entire request failed before any results were produced. [`RESOLUTION_NULL_SLOT`](#result-error-codes) in the results array means a specific criterion was not processed, but the request itself succeeded and other criteria in the same batch may have resolved normally.

**Cascade Data Quality**

| HTTP Status | Error Code | Condition | Consumer Action |
|---|---|---|---|
| 503 | `CASCADE_NOT_READY` | Cascade-sourced key columns have >20% null rate, indicating cache warmup is incomplete for this entity type | Retry after cache warmup completes. Response includes `entity_type` and `degraded_columns` for diagnosis. |

**`CASCADE_NOT_READY` error response:**

```json
{
  "detail": {
    "error": "CASCADE_NOT_READY",
    "message": "Cascade data not ready for unit: degraded columns [office_phone (25.3%)] exceed 20% null threshold",
    "entity_type": "unit",
    "degraded_columns": {"office_phone": 0.253},
    "request_id": "req_abc123"
  }
}
```

`CASCADE_NOT_READY` is also request-level (HTTP 503) — it fires before resolution begins when the service detects that cascade data quality is insufficient to produce reliable results.

---

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
