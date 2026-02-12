# Entity Write API

> Write fields to Asana entities via structured field updates with automatic field resolution.

## Authentication

S2S JWT (service-to-service) authentication required via `Authorization: Bearer <token>` header.

PAT (Personal Access Token) authentication is NOT supported. Requests with PAT tokens receive `401 SERVICE_TOKEN_REQUIRED` error.

The endpoint internally uses a bot PAT to communicate with Asana's API, but client authentication must use service tokens.

## Endpoints

### `PATCH /api/v1/entity/{entity_type}/{gid}`

Write fields to an Asana entity (task) identified by GID.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_type` | string | Entity type (offer, unit, business, etc.) |
| `gid` | string | Asana task GID |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_updated` | boolean | false | If true, re-fetch and return current field values after write |

**Request Body:**

```json
{
  "fields": {
    "weekly_ad_spend": 5000,
    "status": "Active",
    "notes": "Updated via API"
  },
  "list_mode": "replace"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `fields` | object | Yes | Field name-value pairs. Must be non-empty. |
| `list_mode` | string | No | How to handle list-type fields: `replace` (default) or `append` |

**Field Name Formats:**

The `fields` object accepts multiple naming formats:

- Python descriptor names: `weekly_ad_spend`, `office_phone`
- Asana display names: `"Weekly Ad Spend"`, `"Office Phone"`
- Core fields: `name`, `assignee`, `due_on`, `completed`, `notes`

**Response Body:**

```json
{
  "gid": "1234567890123456",
  "entity_type": "unit",
  "fields_written": 2,
  "fields_skipped": 1,
  "field_results": [
    {
      "name": "weekly_ad_spend",
      "status": "written",
      "error": null,
      "suggestions": null
    },
    {
      "name": "status",
      "status": "written",
      "error": null,
      "suggestions": null
    },
    {
      "name": "invalid_field",
      "status": "skipped",
      "error": "Field not found in schema",
      "suggestions": ["status_type", "status_reason"]
    }
  ],
  "updated_fields": {
    "weekly_ad_spend": 5000,
    "status": "Active"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `gid` | string | Asana task GID |
| `entity_type` | string | Entity type |
| `fields_written` | integer | Count of successfully written fields |
| `fields_skipped` | integer | Count of skipped fields (resolution failed) |
| `field_results` | array | Per-field write results |
| `updated_fields` | object \| null | Current field values (only if `include_updated=true`) |

**Field Result Object:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Input field name as provided in request |
| `status` | string | `written`, `skipped`, or `error` |
| `error` | string \| null | Error message if status is `skipped` or `error` |
| `suggestions` | array \| null | Suggested field names if field not found |

**Example: cURL**

```bash
curl -X PATCH https://api.example.com/api/v1/entity/unit/1234567890123456 \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "weekly_ad_spend": 5000,
      "office_phone": "+15551234567"
    },
    "list_mode": "replace"
  }'
```

**Example: Python httpx**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.patch(
        "https://api.example.com/api/v1/entity/unit/1234567890123456",
        headers={
            "Authorization": f"Bearer {s2s_token}",
            "Content-Type": "application/json"
        },
        json={
            "fields": {
                "weekly_ad_spend": 5000,
                "office_phone": "+15551234567"
            },
            "list_mode": "replace"
        }
    )
    result = response.json()
    print(f"Written: {result['fields_written']}, Skipped: {result['fields_skipped']}")
```

**Example: Append to multi-enum field**

```bash
curl -X PATCH https://api.example.com/api/v1/entity/offer/9876543210987654 \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "tags": ["urgent", "reviewed"]
    },
    "list_mode": "append"
  }'
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 401 | `SERVICE_TOKEN_REQUIRED` | PAT token provided (S2S JWT required) |
| 404 | `TASK_NOT_FOUND` | Asana task with specified GID does not exist |
| 404 | `UNKNOWN_ENTITY_TYPE` | Entity type not recognized or not writable |
| 404 | `ENTITY_TYPE_MISMATCH` | Task exists but is not of the specified entity type |
| 422 | `NO_VALID_FIELDS` | All fields failed resolution (nothing to write) |
| 422 | `VALIDATION_ERROR` | Request body validation failed (empty fields, invalid list_mode) |
| 429 | `RATE_LIMITED` | Asana API rate limit exceeded (includes `Retry-After` header) |
| 502 | `ASANA_UPSTREAM_ERROR` | Asana API server error or unexpected error |
| 503 | `DISCOVERY_INCOMPLETE` | Entity write registry not initialized (service starting up) |
| 503 | `BOT_PAT_UNAVAILABLE` | Bot PAT not configured for S2S Asana access |
| 504 | `ASANA_TIMEOUT` | Asana API call timed out |

**Error Response Format:**

```json
{
  "detail": {
    "error": "UNKNOWN_ENTITY_TYPE",
    "message": "Unknown or non-writable entity type: invalid_type. Available types: offer, unit, business, contact",
    "available_types": ["offer", "unit", "business", "contact"]
  }
}
```

**Entity Type Mismatch Example:**

```json
{
  "detail": {
    "error": "ENTITY_TYPE_MISMATCH",
    "message": "Task 1234567890123456 is type 'offer', not 'unit'",
    "expected": "unit",
    "actual": "offer",
    "gid": "1234567890123456"
  }
}
```

## Field Resolution

The endpoint automatically resolves field names to Asana custom field GIDs:

1. Checks Python descriptor names in the entity schema
2. Checks Asana display names in the entity schema
3. Checks core field names (name, assignee, due_on, completed, notes)
4. If field not found, status is `skipped` with suggestions

Field resolution is case-sensitive for descriptor names but matches display names as stored in Asana.

## List Mode Behavior

### `replace` (default)

Replaces the entire field value with the provided value. For multi-enum fields, this clears existing selections and sets only the provided values.

### `append`

Appends to existing values. Supported for:
- Multi-enum custom fields
- Text list fields

For single-value fields, `append` behaves the same as `replace`.

## Notes

- Writes are executed synchronously. Response indicates write completion.
- Cache invalidation is triggered automatically if `MutationInvalidator` is configured.
- Field suggestions use fuzzy matching when a field name is not found.
- The `updated_fields` response field requires an additional Asana API call (use sparingly).
