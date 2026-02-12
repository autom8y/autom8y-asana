# DataFrame Layer

## Overview

The DataFrame layer transforms Asana task data into structured, type-safe tabular views using [Polars](https://pola.rs/). Instead of navigating task hierarchies and custom fields manually, you query endpoints that return DataFrames with consistent schemas.

Key capabilities:

- **Type-safe schemas**: Every column has a defined Polars dtype (Utf8, Int64, Datetime, etc.)
- **Custom field resolution**: Columns reference custom fields by name (`cf:MRR`, `cf:Vertical`)
- **Cascade extraction**: Fields like `cascade:Office Phone` traverse task ancestors to find values
- **Format negotiation**: Get JSON records or native Polars wire format
- **Automatic caching**: DataFrames are cached with schema-aware versioning

The layer uses Polars for performance and type safety. All DataFrames are Polars `DataFrame` objects.

## REST API

Two endpoints expose DataFrames:

### Project DataFrames

```http
GET /api/v1/dataframes/project/{gid}
```

Fetches all tasks from a project as a DataFrame.

**Query Parameters**:
- `schema` (string, default: `base`) - Schema name (base, unit, contact, business, offer, asset_edit, asset_edit_holder)
- `limit` (int, default: 100, max: 100) - Items per page
- `offset` (string, optional) - Pagination cursor from previous response

**Request Example**:

```bash
curl -X GET "https://api.example.com/api/v1/dataframes/project/123456?schema=unit&limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Accept: application/json"
```

**Response Example** (JSON records format):

```json
{
  "data": [
    {
      "gid": "1234567890",
      "name": "Unit Task",
      "type": "Unit",
      "date": "2024-01-15",
      "created": "2024-01-15T10:30:00Z",
      "due_on": "2024-01-31",
      "is_completed": false,
      "completed_at": null,
      "url": "https://app.asana.com/0/0/1234567890",
      "last_modified": "2024-01-16T15:45:30Z",
      "assignee": "John Doe",
      "section": "In Progress",
      "mrr": 1250.00,
      "office_phone": "+1-555-0100",
      "vertical": "Healthcare"
    }
  ],
  "meta": {
    "request_id": "abc123",
    "timestamp": "2024-01-20T12:00:00Z",
    "pagination": {
      "limit": 50,
      "has_more": false,
      "next_offset": null
    }
  }
}
```

### Section DataFrames

```http
GET /api/v1/dataframes/section/{gid}
```

Fetches tasks from a specific section as a DataFrame.

**Query Parameters**: Same as project endpoint.

**Request Example**:

```bash
curl -X GET "https://api.example.com/api/v1/dataframes/section/789012?schema=offer" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**: Same structure as project endpoint, filtered to section tasks.

### Error Response

Invalid schema names return HTTP 400 with valid options:

```json
{
  "error": "INVALID_SCHEMA",
  "message": "Unknown schema 'invalid'. Valid schemas: base, unit, contact, business, offer, asset_edit, asset_edit_holder",
  "valid_schemas": ["base", "unit", "contact", "business", "offer", "asset_edit", "asset_edit_holder"]
}
```

## Schemas

Schemas define the columns extracted from tasks. All schemas extend the base schema with task-type-specific columns.

### Base Schema

12 columns applicable to all task types:

| Column | Type | Nullable | Source | Description |
|--------|------|----------|--------|-------------|
| `gid` | Utf8 | No | `gid` | Task identifier |
| `name` | Utf8 | No | `name` | Task name |
| `type` | Utf8 | No | derived | Task type discriminator |
| `date` | Date | Yes | derived | Primary date field (type-specific) |
| `created` | Datetime | No | `created_at` | Creation timestamp |
| `due_on` | Date | Yes | `due_on` | Due date |
| `is_completed` | Boolean | No | `completed` | Completion status |
| `completed_at` | Datetime | Yes | `completed_at` | Completion timestamp |
| `url` | Utf8 | No | derived | Asana task URL |
| `last_modified` | Datetime | No | `modified_at` | Last modification timestamp |
| `assignee` | Utf8 | Yes | `assignee.name` | Assignee name |
| `section` | Utf8 | Yes | `memberships.section.name` | Section name |

Use `schema=base` for generic task extraction without task-type filtering.

### Unit Schema

Extends base with 11 Unit-specific columns:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| `mrr` | Decimal | `cf:MRR` | Monthly recurring revenue |
| `weekly_ad_spend` | Decimal | `cf:Weekly Ad Spend` | Weekly advertising spend |
| `products` | List[Utf8] | `cf:Products` | Product list (multi-enum) |
| `languages` | List[Utf8] | `cf:Languages` | Supported languages |
| `discount` | Decimal | `cf:Discount` | Discount percentage |
| `office` | Utf8 | derived | Office name from office_phone lookup |
| `office_phone` | Utf8 | `cascade:Office Phone` | Cascades from Business ancestor |
| `vertical` | Utf8 | `cf:Vertical` | Business vertical |
| `vertical_id` | Utf8 | derived | Vertical identifier |
| `specialty` | Utf8 | `cf:Specialty` | Business specialty |
| `max_pipeline_stage` | Utf8 | `cf:Max Pipeline Stage` | Pipeline stage |

Use `schema=unit` when querying projects containing Unit tasks.

### Contact Schema

Extends base with 4 Contact-specific columns:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| `email` | Utf8 | `cf:Email` | Contact email address |
| `phone` | Utf8 | `cf:Phone` | Contact phone number |
| `role` | Utf8 | `cf:Role` | Contact role |
| `status` | Utf8 | `cf:Status` | Contact status |

Use `schema=contact` for Contact tasks.

### Business Schema

Extends base with Business-specific columns for company/office entities:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| `company_id` | Utf8 | `cf:Company ID` | Company identifier |
| `name` | Utf8 | derived | Office name |
| `office_phone` | Utf8 | `cf:Office Phone` | Office phone number |
| `stripe_id` | Utf8 | `cf:Stripe ID` | Stripe customer identifier |
| `booking_type` | Utf8 | `cf:Booking Type` | Booking type |
| `facebook_page_id` | Utf8 | `cf:Facebook Page ID` | Facebook page identifier |

Use `schema=business` for Business tasks.

### Offer Schema

Extends base with Offer-specific columns:

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| `office` | Utf8 | derived | Office name |
| `office_phone` | Utf8 | `cascade:Office Phone` | Cascades from Business ancestor |
| `vertical` | Utf8 | `cascade:Vertical` | Cascades from Unit/Business |
| `vertical_id` | Utf8 | derived | Vertical identifier |
| `specialty` | Utf8 | `cf:Specialty` | Business specialty |
| `offer_id` | Utf8 | `cf:Offer ID` | Offer identifier |

Use `schema=offer` for Offer tasks.

### Asset Edit Schemas

Two schemas support asset management workflows:

- **asset_edit**: Individual asset edit tasks
- **asset_edit_holder**: Holder tasks that group asset edits

Use these schemas when working with asset management projects.

## Builders

Builders transform raw Asana task data into DataFrames. Two concrete implementations exist:

### SectionDataFrameBuilder

Builds DataFrames from section tasks. Used by the `/api/v1/dataframes/section/{gid}` endpoint.

**Python Example**:

```python
from autom8_asana.dataframes import SectionDataFrameBuilder, BASE_SCHEMA
from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver

# Fetch section and tasks (simplified)
section = await client.sections.get_section(section_gid="789012")
tasks = await client.tasks.get_tasks_for_section(section_gid="789012")

# Create builder
builder = SectionDataFrameBuilder(
    section=section,
    task_type="*",  # All task types
    schema=BASE_SCHEMA,
    resolver=DefaultCustomFieldResolver(),
)

# Build DataFrame
df = builder.build(tasks=tasks)
print(df.shape)  # (50, 12) for base schema
```

### ProgressiveProjectBuilder

Builds DataFrames from project tasks with incremental refresh support. Handles large projects by fetching tasks progressively.

**Python Example**:

```python
from autom8_asana.dataframes import ProgressiveProjectBuilder
from autom8_asana.dataframes.schemas import UNIT_SCHEMA
from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver

# Create builder
builder = ProgressiveProjectBuilder(
    client=client,
    project_gid="123456",
    entity_type="unit",
    schema=UNIT_SCHEMA,
    persistence=None,  # Optional S3 persistence
)

# Build DataFrame (async)
result = await builder.build_progressive_async()
df = result.dataframe

print(df.shape)  # (500, 23) for unit schema (12 base + 11 unit columns)
print(df.columns)  # ['gid', 'name', 'type', 'date', ..., 'mrr', 'vertical', ...]
```

Both builders use the same core extraction logic via the `DataFrameViewPlugin`.

## Content Negotiation

The API supports two response formats via the `Accept` header:

### JSON Records (default)

**Accept header**: `application/json` (or omit header)

Returns an array of record objects. Each object is one row.

```json
{
  "data": [
    {"gid": "123", "name": "Task 1", "type": "Unit"},
    {"gid": "456", "name": "Task 2", "type": "Contact"}
  ],
  "meta": { ... }
}
```

Best for:
- JavaScript/TypeScript clients
- HTTP clients that don't support Polars
- Quick inspection and debugging

### Polars Wire Format

**Accept header**: `application/x-polars-json`

Returns Polars-serialized JSON format. Clients deserialize directly to Polars DataFrame.

**Request**:

```bash
curl -X GET "https://api.example.com/api/v1/dataframes/project/123456?schema=unit" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Accept: application/x-polars-json"
```

**Response**:

```json
{
  "data": "[{\"columns\":[{\"name\":\"gid\",\"datatype\":\"Utf8\",...}],\"data\":{...}}]",
  "meta": { ... }
}
```

**Python Client Example**:

```python
import polars as pl
import httpx

response = httpx.get(
    "https://api.example.com/api/v1/dataframes/project/123456",
    params={"schema": "unit"},
    headers={
        "Authorization": "Bearer YOUR_TOKEN",
        "Accept": "application/x-polars-json",
    },
)
response.raise_for_status()

# Deserialize Polars JSON
polars_json = response.json()["data"]
df = pl.read_json(polars_json)

print(df.shape)
print(df.head())
```

Best for:
- Python clients using Polars
- Preserves exact dtypes and schema
- More efficient for large DataFrames

## Caching

DataFrames are cached at multiple levels:

### Response Caching

The API caches built DataFrames for common requests. Cache keys include:
- Project or section GID
- Schema name
- Schema version

Cache TTL defaults to 1 hour. Stale data is served with a `X-Cache-Status: stale` header while fresh data is fetched in the background.

### Task Caching

Individual task data is cached by the `UnifiedTaskStore`. When building DataFrames:
1. Check task cache for each task GID
2. Fetch missing tasks from Asana API
3. Store fetched tasks in cache for next build

Task cache TTL: 15 minutes (default)

### Schema Versioning

Schema changes invalidate cached DataFrames. Each schema has a version string (e.g., `1.0.0`). Cache keys include the schema version to prevent stale data after schema updates.

## Python Usage

### Basic Synchronous Usage

```python
from autom8_asana.dataframes import SectionDataFrameBuilder, BASE_SCHEMA
from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
from autom8_asana.clients import AsanaClient

# Initialize client
client = AsanaClient.from_env()

# Fetch section data
section = client.sections.get_section_sync(section_gid="789012")
tasks = client.tasks.get_tasks_for_section_sync(section_gid="789012")

# Build DataFrame
builder = SectionDataFrameBuilder(
    section=section,
    task_type="*",
    schema=BASE_SCHEMA,
    resolver=DefaultCustomFieldResolver(),
)
df = builder.build(tasks=tasks)

# Work with Polars DataFrame
print(df.schema)  # Column names and dtypes
print(df.select(["gid", "name", "type"]))
print(df.filter(pl.col("is_completed") == False))
```

### Async Usage

```python
import asyncio
from autom8_asana.dataframes import ProgressiveProjectBuilder
from autom8_asana.dataframes.schemas import UNIT_SCHEMA
from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
from autom8_asana.clients import AsanaClient

async def fetch_unit_dataframe():
    client = AsanaClient.from_env()

    builder = ProgressiveProjectBuilder(
        client=client,
        project_gid="123456",
        entity_type="unit",
        schema=UNIT_SCHEMA,
        persistence=None,
    )

    result = await builder.build_progressive_async()
    df = result.dataframe

    # Filter and aggregate
    revenue_by_vertical = (
        df.filter(pl.col("is_completed") == False)
        .groupby("vertical")
        .agg(pl.col("mrr").sum().alias("total_mrr"))
        .sort("total_mrr", descending=True)
    )

    print(revenue_by_vertical)

asyncio.run(fetch_unit_dataframe())
```

### Custom Field Resolution

The resolver maps schema `source` attributes (e.g., `cf:MRR`) to actual custom field GIDs:

```python
from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver

resolver = DefaultCustomFieldResolver()

# Resolver fetches project custom field definitions
# and caches GID mappings: "MRR" -> "1234567890"

# Access resolved GID (for debugging)
mrr_gid = resolver.resolve_gid(
    field_name="MRR",
    project_gid="123456",
)
print(f"MRR custom field GID: {mrr_gid}")
```

The resolver handles:
- Name normalization (case-insensitive, whitespace trimming)
- GID caching per project
- Cascade prefix stripping (`cascade:Office Phone` -> `Office Phone`)

### Working with Cascade Fields

Cascade fields traverse task ancestors to find values:

```python
# Unit schema has cascade:Office Phone
# Builder fetches Unit task -> parent Business task -> extracts Office Phone

df = builder.build(tasks=unit_tasks)

# office_phone column populated from Business ancestor
print(df.select(["gid", "name", "office_phone"]))
```

Cascade sources:
- `cascade:Office Phone` - Looks up Business ancestor
- `cascade:Vertical` - Looks up Unit or Business ancestor

### Filtering by Schema

When querying mixed-type projects, filter tasks by type before building:

```python
from autom8_asana.dataframes.schemas import UNIT_SCHEMA, CONTACT_SCHEMA

# Fetch all project tasks
all_tasks = await client.tasks.get_tasks_for_project(project_gid="123456")

# Filter to Unit tasks
unit_tasks = [t for t in all_tasks if t.resource_subtype == "unit"]

# Build Unit DataFrame
builder = SectionDataFrameBuilder(
    section=section,
    task_type="Unit",
    schema=UNIT_SCHEMA,
    resolver=resolver,
)
df = builder.build(tasks=unit_tasks)
```

Or use the base schema with `task_type="*"` to extract all tasks with common columns only.

## Troubleshooting

### Missing Custom Fields

**Problem**: Column returns `null` for all rows.

**Cause**: Custom field name in schema doesn't match Asana project configuration.

**Solution**: Check custom field names in Asana project settings. Names are case-insensitive but must match exactly after normalization.

```python
# Debug custom field resolution
resolver = DefaultCustomFieldResolver()
gid = resolver.resolve_gid(field_name="MRR", project_gid="123456")
if gid is None:
    print("Custom field 'MRR' not found in project")
```

### Schema Validation Errors

**Problem**: HTTP 400 with "Unknown schema" error.

**Cause**: Invalid schema name in query parameter.

**Solution**: Use one of the valid schema names: `base`, `unit`, `contact`, `business`, `offer`, `asset_edit`, `asset_edit_holder`.

### Empty DataFrames

**Problem**: DataFrame has 0 rows despite tasks existing.

**Cause**: Schema task_type filter doesn't match task types in section/project.

**Solution**: Use `schema=base` to extract all tasks regardless of type, or verify task types match the schema.

```python
# Check task types in project
task_types = set(t.resource_subtype for t in tasks)
print(f"Task types in project: {task_types}")
```

### Cascade Field Returns Null

**Problem**: Cascade column (e.g., `office_phone`) returns `null`.

**Cause**: Task has no ancestor with the cascade field, or ancestor fetch failed.

**Solution**: Verify task hierarchy in Asana. Cascade fields require parent tasks with the field populated.

```python
# Check task parent
task = await client.tasks.get_task(task_gid="123456")
parent = task.parent
if parent:
    parent_task = await client.tasks.get_task(task_gid=parent.gid)
    print(f"Parent custom fields: {parent_task.custom_fields}")
```

### Performance Issues

**Problem**: DataFrame build takes too long for large projects.

**Cause**: Synchronous task fetching for 1000+ tasks.

**Solution**: Use `ProgressiveProjectBuilder` with async operations:

```python
# Instead of synchronous build
df = builder.build(tasks=tasks)  # Slow for 1000+ tasks

# Use progressive async build
result = await builder.build_progressive_async()  # Parallelized fetching
df = result.dataframe
```

Progressive builder batches task fetches and uses connection pooling for 10x faster builds on large projects.
