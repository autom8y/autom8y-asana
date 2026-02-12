# DataFrames API

> Fetch Asana tasks as structured DataFrames with flexible schema-based extraction.

## Authentication

Dual-mode Bearer token authentication via `Authorization: Bearer <token>` header.

Supports both:
- **S2S JWT** (service-to-service): Machine-to-machine authentication
- **PAT** (Personal Access Token): User-based authentication

## Endpoints

### `GET /api/v1/dataframes/project/{gid}`

Fetch all tasks in a project as a DataFrame. Returns structured data with custom field extraction based on the selected schema.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Asana project GID |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `schema` | string | base | Schema for field extraction. Valid: `base`, `unit`, `contact`, `business`, `offer`, `asset_edit`, `asset_edit_holder`. Case-insensitive. |
| `limit` | integer | 100 | Number of items per page (1-100) |
| `offset` | string | null | Pagination cursor from previous response |

**Headers:**

| Header | Type | Default | Description |
|--------|------|---------|-------------|
| `Accept` | string | application/json | Response format: `application/json` for JSON records, `application/x-polars-json` for Polars-serialized format |

**Response Body (JSON format):**

```json
{
  "data": [
    {
      "gid": "1234567890123456",
      "name": "Task 1",
      "type": "Unit",
      "completed": false,
      "created_at": "2024-01-01T00:00:00Z",
      "office_phone": "+15551234567",
      "weekly_ad_spend": 5000
    },
    {
      "gid": "9876543210987654",
      "name": "Task 2",
      "type": "Contact",
      "completed": true,
      "created_at": "2024-01-02T00:00:00Z",
      "email": "contact@example.com"
    }
  ],
  "meta": {
    "request_id": "abc123",
    "timestamp": "2024-01-01T00:00:00Z",
    "pagination": {
      "limit": 100,
      "has_more": false,
      "next_offset": null
    }
  }
}
```

**Response Body (Polars format):**

```json
{
  "data": "[{\"columns\":[{\"name\":\"gid\",\"datatype\":\"String\"},...],\"data\":{\"columns\":[...]}}]",
  "meta": {
    "request_id": "abc123",
    "timestamp": "2024-01-01T00:00:00Z",
    "pagination": {
      "limit": 100,
      "has_more": false,
      "next_offset": null
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `data` | array \| string | For JSON format: array of task records. For Polars format: serialized Polars DataFrame as JSON string. |
| `meta` | object | Response metadata including request ID, timestamp, and pagination |
| `meta.pagination.limit` | integer | Requested page size |
| `meta.pagination.has_more` | boolean | Whether more results exist |
| `meta.pagination.next_offset` | string \| null | Cursor for next page (pass as `offset` parameter) |

**Example: cURL (JSON format)**

```bash
curl -X GET "https://api.example.com/api/v1/dataframes/project/1234567890123456?schema=unit&limit=50" \
  -H "Authorization: Bearer <JWT_OR_PAT_TOKEN>" \
  -H "Accept: application/json"
```

**Example: cURL (Polars format)**

```bash
curl -X GET "https://api.example.com/api/v1/dataframes/project/1234567890123456?schema=unit" \
  -H "Authorization: Bearer <JWT_OR_PAT_TOKEN>" \
  -H "Accept: application/x-polars-json"
```

**Example: Python httpx with Polars deserialization**

```python
import httpx
import polars as pl
from io import StringIO

async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://api.example.com/api/v1/dataframes/project/1234567890123456",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/x-polars-json"
        },
        params={"schema": "unit", "limit": 100}
    )
    result = response.json()

    # Deserialize Polars DataFrame from response
    df = pl.read_json(StringIO(result["data"]))
    print(f"Fetched {len(df)} rows with {len(df.columns)} columns")
```

**Example: Pagination**

```bash
# First page
curl -X GET "https://api.example.com/api/v1/dataframes/project/1234567890123456?limit=50" \
  -H "Authorization: Bearer <TOKEN>"

# Response includes next_offset in meta.pagination
# Use it for the next page
curl -X GET "https://api.example.com/api/v1/dataframes/project/1234567890123456?limit=50&offset=eyJvZmZzZXQiOiI1MCJ9" \
  -H "Authorization: Bearer <TOKEN>"
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `INVALID_SCHEMA` | Schema name not recognized. Response includes `valid_schemas` array. |
| 401 | `UNAUTHORIZED` | Missing or invalid Bearer token |
| 404 | `NOT_FOUND` | Project with specified GID does not exist |
| 429 | `RATE_LIMITED` | Asana API rate limit exceeded (includes `Retry-After` header) |
| 502 | `ASANA_UPSTREAM_ERROR` | Asana API server error |
| 504 | `ASANA_TIMEOUT` | Asana API call timed out |

**Error Response Format:**

```json
{
  "detail": {
    "error": "INVALID_SCHEMA",
    "message": "Unknown schema 'invalid'. Valid schemas: base, unit, contact, business, offer, asset_edit, asset_edit_holder",
    "valid_schemas": ["base", "unit", "contact", "business", "offer", "asset_edit", "asset_edit_holder"]
  }
}
```

---

### `GET /api/v1/dataframes/section/{gid}`

Fetch all tasks in a section as a DataFrame. Returns structured data with custom field extraction based on the selected schema.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Asana section GID |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `schema` | string | base | Schema for field extraction. Valid: `base`, `unit`, `contact`, `business`, `offer`, `asset_edit`, `asset_edit_holder`. Case-insensitive. |
| `limit` | integer | 100 | Number of items per page (1-100) |
| `offset` | string | null | Pagination cursor from previous response |

**Headers:**

| Header | Type | Default | Description |
|--------|------|---------|-------------|
| `Accept` | string | application/json | Response format: `application/json` for JSON records, `application/x-polars-json` for Polars-serialized format |

**Response Body:**

Same structure as project endpoint. See above for details.

**Example: cURL**

```bash
curl -X GET "https://api.example.com/api/v1/dataframes/section/1234567890123456?schema=contact" \
  -H "Authorization: Bearer <JWT_OR_PAT_TOKEN>" \
  -H "Accept: application/json"
```

**Example: Python httpx**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://api.example.com/api/v1/dataframes/section/1234567890123456",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        },
        params={"schema": "contact", "limit": 100}
    )
    result = response.json()
    tasks = result["data"]
    print(f"Fetched {len(tasks)} tasks from section")
```

**Errors:**

Same as project endpoint, plus:

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `NOT_FOUND` | Section not found or has no parent project |

---

## Schemas

Schema determines which custom fields are extracted and included in the DataFrame. Each schema defines:
- Core fields (gid, name, completed, created_at, etc.)
- Entity-specific custom fields (office_phone, weekly_ad_spend, etc.)
- Field data types (string, integer, float, boolean, date, etc.)

Available schemas:

| Schema | Description | Use Case |
|--------|-------------|----------|
| `base` | Minimal core fields only | When you only need GID, name, completion status |
| `unit` | Unit-specific custom fields | Extracting advertising unit data |
| `contact` | Contact-specific custom fields | Extracting contact information |
| `business` | Business-specific custom fields | Extracting business/account data |
| `offer` | Offer-specific custom fields | Extracting offer/deal data |
| `asset_edit` | Asset edit custom fields | Extracting asset editing metadata |
| `asset_edit_holder` | Asset edit holder custom fields | Extracting asset holder information |

Invalid schema names return HTTP 400 with a list of valid schemas in the error response.

## Output Formats

### JSON Records (default)

Returns an array of task objects. Each task is a dictionary with flat key-value pairs.

**Pros:**
- Universal compatibility (any HTTP client)
- Human-readable
- Easy to debug

**Cons:**
- Larger payload size
- Requires manual DataFrame construction if needed

**When to use:** REST clients, web frontends, debugging, exploratory work.

### Polars Serialized

Returns a Polars DataFrame serialized as JSON string in the `data` field. The serialized format preserves column types and can be directly deserialized using `polars.read_json()`.

**Pros:**
- Preserves type information
- Direct deserialization to DataFrame
- Smaller payload for large datasets

**Cons:**
- Requires Polars library on client side
- Not human-readable
- Opaque for debugging

**When to use:** Data pipelines, analytics workflows, Python clients with Polars installed.

### Selecting Format

Set the `Accept` header:
- `Accept: application/json` → JSON records (default)
- `Accept: application/x-polars-json` → Polars serialized format

If no `Accept` header is provided, JSON format is used.

## Pagination

All dataframe endpoints return paginated results with a maximum page size of 100 items.

**How it works:**
1. First request: Omit `offset` parameter
2. Check `meta.pagination.has_more` in response
3. If `true`, use `meta.pagination.next_offset` as the `offset` parameter for the next request
4. Repeat until `has_more` is `false`

**Example pagination loop:**

```python
import httpx

async def fetch_all_tasks(project_gid: str, token: str):
    all_tasks = []
    offset = None

    async with httpx.AsyncClient() as client:
        while True:
            params = {"schema": "unit", "limit": 100}
            if offset:
                params["offset"] = offset

            response = await client.get(
                f"https://api.example.com/api/v1/dataframes/project/{project_gid}",
                headers={"Authorization": f"Bearer {token}"},
                params=params
            )
            result = response.json()

            all_tasks.extend(result["data"])

            if not result["meta"]["pagination"]["has_more"]:
                break

            offset = result["meta"]["pagination"]["next_offset"]

    return all_tasks
```

## Performance Notes

- DataFrame construction happens server-side. Response time scales with task count.
- Custom field extraction adds overhead. Use `base` schema if you only need core fields.
- Polars format is ~30% smaller than JSON format for large datasets.
- Pagination cursors are opaque tokens. Do not construct them manually.
- First page is typically fastest (Asana API caching).

## See Also

- [Tasks API Reference](tasks.md) - Lower-level task operations
- [Projects API Reference](projects.md) - Project metadata operations
- [Sections API Reference](sections.md) - Section metadata operations
