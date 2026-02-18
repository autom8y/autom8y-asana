# Writing Entity Fields

Write fields to Asana entities through the Entity Write API using business-domain field names. The system resolves field names, validates types, handles enum resolution, and executes a single Asana API update.

## Overview

The Entity Write API provides:

- **Field name resolution**: Python descriptor names (snake_case), Asana display names (Title Case), and custom field GIDs
- **Type coercion**: Automatic type validation and enum-to-GID resolution
- **Partial success**: Per-field results with error details and suggestions
- **List mode control**: Replace or append for multi-enum and text list fields
- **Cache invalidation**: Automatic fire-and-forget invalidation after successful writes

Single endpoint: `PATCH /api/v1/entity/{entity_type}/{gid}`

## Authentication

S2S JWT tokens only. PAT tokens are rejected.

The Entity Write API requires service-to-service authentication via JWT. Service tokens include claims identifying the calling service.

```bash
# Service token format
Authorization: Bearer <S2S_JWT_TOKEN>

# Claims include:
# - sub: service:autom8_data
# - service_name: autom8_data
# - scope: multi-tenant
```

PAT tokens return 401 SERVICE_TOKEN_REQUIRED.

**Obtaining service tokens**: Contact platform team for JWT signing keys and claim structure.

## REST API Usage

### Endpoint

```
PATCH /api/v1/entity/{entity_type}/{gid}
```

**Path parameters:**
- `entity_type`: Entity type (offer, unit, business, asset, process)
- `gid`: Asana task GID

**Query parameters:**
- `include_updated` (optional): If true, re-fetch and return current field values after write

### Request Body

```json
{
  "fields": {
    "field_name": "value",
    "another_field": 123
  },
  "list_mode": "replace"
}
```

**Fields:**
- `fields` (required): Dict mapping field names to values
- `list_mode` (optional): "replace" (default) or "append"

### Response

```json
{
  "gid": "1234567890",
  "entity_type": "offer",
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
      "error": "Field 'invalid_field' not found on entity",
      "suggestions": ["weekly_ad_spend", "weekly_spend"]
    }
  ],
  "updated_fields": null
}
```

**Status codes:**
- 200: Success (some or all fields written)
- 401: Missing or invalid authentication
- 404: Entity type unknown or task not found
- 422: All fields failed validation (NO_VALID_FIELDS)
- 429: Rate limit exceeded
- 502: Asana API error
- 503: Service not initialized

### Example: Write Number and Enum Fields

```bash
curl -X PATCH \
  https://autom8y-asana.example.com/api/v1/entity/offer/1234567890 \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "weekly_ad_spend": 1250.50,
      "status": "Active"
    }
  }'
```

Response:
```json
{
  "gid": "1234567890",
  "entity_type": "offer",
  "fields_written": 2,
  "fields_skipped": 0,
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
    }
  ],
  "updated_fields": null
}
```

### Example: Write Multi-Enum with Append

```bash
curl -X PATCH \
  https://autom8y-asana.example.com/api/v1/entity/unit/1234567891 \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "ai_ad_types": ["Facebook", "Google"]
    },
    "list_mode": "append"
  }'
```

Appends "Facebook" and "Google" to existing selections. Duplicates are automatically removed.

### Example: Retrieve Updated Values

```bash
curl -X PATCH \
  "https://autom8y-asana.example.com/api/v1/entity/offer/1234567890?include_updated=true" \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "weekly_ad_spend": 1500
    }
  }'
```

Response includes `updated_fields`:
```json
{
  "gid": "1234567890",
  "entity_type": "offer",
  "fields_written": 1,
  "fields_skipped": 0,
  "field_results": [...],
  "updated_fields": {
    "weekly_ad_spend": 1500.0
  }
}
```

## SDK Usage

Direct `FieldWriteService` usage for SDK consumers.

### Setup

```python
from autom8_asana import AsanaClient
from autom8_asana.core.entity_registry import get_registry
from autom8_asana.resolution.write_registry import EntityWriteRegistry
from autom8_asana.services.field_write_service import FieldWriteService

# Build write registry from entity registry
entity_registry = get_registry()
write_registry = EntityWriteRegistry(entity_registry)

# Create Asana client with bot PAT
async with AsanaClient(token=BOT_PAT) as client:
    service = FieldWriteService(client, write_registry)
```

### Write Fields

```python
result = await service.write_async(
    entity_type="offer",
    gid="1234567890",
    fields={
        "weekly_ad_spend": 1250.50,
        "status": "Active",
    },
    list_mode="replace",
    include_updated=False,
    mutation_invalidator=None,
)

print(f"Written: {result.fields_written}")
print(f"Skipped: {result.fields_skipped}")

for field_result in result.field_results:
    print(f"{field_result.input_name}: {field_result.status}")
    if field_result.error:
        print(f"  Error: {field_result.error}")
    if field_result.suggestions:
        print(f"  Suggestions: {', '.join(field_result.suggestions)}")
```

### With Cache Invalidation

```python
from autom8_asana.cache.integration.mutation_invalidator import MutationInvalidator

# Get invalidator from app.state or construct
mutation_invalidator = app.state.mutation_invalidator

result = await service.write_async(
    entity_type="offer",
    gid="1234567890",
    fields={"weekly_ad_spend": 1500},
    mutation_invalidator=mutation_invalidator,
)
```

Fire-and-forget invalidation runs in background task after successful write.

## Field Name Resolution

Three resolution strategies, evaluated in order:

### 1. Core Fields

Exact match against known Asana core fields:
- `name`: Task name
- `assignee`: User GID or "null" string to clear
- `due_on`: ISO date string (YYYY-MM-DD)
- `completed`: Boolean
- `notes`: Task description text

Core fields pass through directly without custom field lookup.

### 2. Descriptor Names

Python property names on entity model classes. Snake_case with O(1) dict lookup.

```python
# Entity model definition
class Offer(BusinessEntity):
    weekly_ad_spend = NumberField()  # Descriptor
    status = EnumField()
```

Request:
```json
{
  "fields": {
    "weekly_ad_spend": 1250.50
  }
}
```

Descriptor name `weekly_ad_spend` resolves to Asana display name "Weekly Ad Spend" via `EntityWriteRegistry.descriptor_index`.

### 3. Display Names

Asana custom field display names. Case-insensitive fallback scan when descriptor lookup fails.

Request:
```json
{
  "fields": {
    "Weekly Ad Spend": 1250.50
  }
}
```

Matches custom field with display name "Weekly Ad Spend" (case-insensitive).

### Abbreviation Handling

Known abbreviations remain uppercase when deriving display names from descriptors:

| Descriptor | Display Name | Abbreviations |
|------------|--------------|---------------|
| `mrr` | MRR | mrr |
| `company_id` | Company ID | id |
| `ad_url` | AD URL | ad, url |
| `num_ai_copies` | Num AI Copies | ai |

Full abbreviation list: `mrr`, `ai`, `url`, `id`, `num`, `cal`, `vca`, `sms`, `ad`

### Not Found Behavior

When no match found, field returns `skipped` status with fuzzy suggestions:

```json
{
  "name": "weekly_spend",
  "status": "skipped",
  "error": "Field 'weekly_spend' not found on entity",
  "suggestions": ["weekly_ad_spend", "Weekly Ad Spend"]
}
```

Suggestions use difflib with 0.6 cutoff. Maximum 3 suggestions per field.

## Type Validation and Coercion

### Text Fields

Expected type: `str`

```json
{
  "fields": {
    "company_id": "ACME-001"
  }
}
```

**Null clears**: `"company_id": null` clears the field.

**Text lists**: When `list_mode: "append"` and field is text, string or list values append to comma-delimited text:

```json
{
  "fields": {
    "tags": ["new-tag"]
  },
  "list_mode": "append"
}
```

Current value "old-tag,existing" becomes "old-tag,existing,new-tag". Duplicates removed.

### Number Fields

Expected type: `int` or `float`

```json
{
  "fields": {
    "weekly_ad_spend": 1250.50
  }
}
```

Asana rounds to field precision. A field with precision=0 rounds 999.99 to 1000.

### Enum Fields

Expected type: `str` (option name or GID)

```json
{
  "fields": {
    "status": "Active"
  }
}
```

**Resolution**: Case-insensitive lookup against enum options. Resolves "Active" or "active" to option GID `opt_123`.

**GID passthrough**: Numeric strings with >=13 digits treated as GIDs. Validates against field's enum options.

```json
{
  "fields": {
    "status": "1234567890123"
  }
}
```

**Short numeric strings**: Values like "1" or "2" treated as option names, not GIDs.

**Not found**: Returns `skipped` with available option names:

```json
{
  "name": "status",
  "status": "skipped",
  "error": "Enum value 'Invalid' not found",
  "suggestions": ["Active", "Paused", "Completed"]
}
```

### Multi-Enum Fields

Expected type: `list[str]` (single string auto-wrapped to list)

```json
{
  "fields": {
    "ai_ad_types": ["Facebook", "Google"]
  }
}
```

**Replace mode** (default): Replaces all selections with resolved GIDs.

**Append mode**: Merges with existing selections. Deduplicates GIDs.

```json
{
  "fields": {
    "ai_ad_types": ["Facebook"]
  },
  "list_mode": "append"
}
```

If field already contains "Google", result is ["Google", "Facebook"]. Order preserved with new values appended.

**Partial resolution**: Invalid options skipped. If one of two values is invalid, the valid value still writes:

```json
{
  "fields": {
    "ai_ad_types": ["Facebook", "InvalidType"]
  }
}
```

Resolves "Facebook" but skips "InvalidType". No error returned, field writes with resolved values.

### Date Fields

Expected type: `str` (ISO 8601 date)

```json
{
  "fields": {
    "process_due_date": "2026-12-31"
  }
}
```

Automatically wrapped to Asana date object: `{"date": "2026-12-31"}`.

### People Fields

Expected type: `list[dict]` with user GIDs

```json
{
  "fields": {
    "rep": [
      {"gid": "1234567890"}
    ]
  }
}
```

Pass list of dicts with "gid" keys. Asana accepts partial user objects.

## List Mode: Replace vs Append

Controls behavior for multi-enum and text list fields.

### Replace Mode (Default)

Replaces entire field value.

```json
{
  "fields": {
    "ai_ad_types": ["Facebook"]
  },
  "list_mode": "replace"
}
```

Existing selections cleared. Field contains only "Facebook" after write.

### Append Mode

Merges with existing values. Deduplicates.

```json
{
  "fields": {
    "ai_ad_types": ["Google"]
  },
  "list_mode": "append"
}
```

If field already contains "Facebook", result is ["Facebook", "Google"]. Original order preserved, new values appended.

**Text field append**: Comma-delimited merge with dedup.

```json
{
  "fields": {
    "tags": "urgent"
  },
  "list_mode": "append"
}
```

Current value "todo,review" becomes "todo,review,urgent".

## Error Handling

The API returns per-field results with partial success support. Some fields can succeed while others fail.

### Field Status Types

Each field in `field_results` has a status:

- **written**: Field successfully resolved and written to Asana
- **skipped**: Field not found or invalid option (non-blocking)
- **error**: Type validation failure (non-blocking)

### Type Validation Errors

```json
{
  "name": "weekly_ad_spend",
  "status": "error",
  "error": "Field 'weekly_ad_spend' expects a number, got str",
  "suggestions": null
}
```

Type mismatches return error status but don't block other fields.

### Field Not Found

```json
{
  "name": "invalid_field",
  "status": "skipped",
  "error": "Field 'invalid_field' not found on entity",
  "suggestions": ["weekly_ad_spend", "weekly_spend"]
}
```

Fuzzy suggestions (difflib, 0.6 cutoff) help identify typos.

### Enum Value Not Found

```json
{
  "name": "status",
  "status": "skipped",
  "error": "Enum value 'InvalidStatus' not found",
  "suggestions": ["Active", "Paused", "Completed"]
}
```

Suggestions list all enabled enum options.

### No Valid Fields

When all fields fail resolution, returns 422:

```json
{
  "error": "NO_VALID_FIELDS",
  "message": "All fields failed resolution -- nothing to write."
}
```

Inspect `field_results` for individual error details.

### Entity Type Mismatch

Task not in expected entity project:

```json
{
  "error": "ENTITY_TYPE_MISMATCH",
  "message": "Task 1234567890 not found in expected project for entity type 'offer'",
  "expected_project": "1143843662099250",
  "actual_projects": ["9999999999999999"]
}
```

Task exists but belongs to different project. Verify entity_type matches task's project membership.

### Task Not Found

```json
{
  "error": "TASK_NOT_FOUND",
  "message": "Task not found: 9999999999999999"
}
```

GID does not exist in Asana. Returns 404.

### Rate Limits

```json
{
  "error": "RATE_LIMITED",
  "message": "Rate limit exceeded. Please retry after backoff."
}
```

Returns 429 with `Retry-After` header when available. Implement exponential backoff.

## Supported Entity Types

Auto-discovered from entity models at startup. Any model with `CustomFieldDescriptor` properties is writable.

### Current Writable Types

| Entity Type | Project GID | Example Writable Fields |
|-------------|-------------|------------------------|
| offer | 1143843662099250 | weekly_ad_spend, status, asset_id |
| unit | 1143843662123456 | num_ai_copies, ai_ad_types |
| business | 1143843662234567 | company_id, mrr, vertical |
| asset | 1143843662345678 | asset_url, asset_type |
| process | 1143843662456789 | process_due_date, process_status |

**Note**: GIDs are examples. Actual GIDs configured in `EntityRegistry`.

### Querying Available Types

```bash
# Invalid entity type error returns available types
curl -X PATCH \
  https://autom8y-asana.example.com/api/v1/entity/invalid/1234567890 \
  -H "Authorization: Bearer <S2S_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"fields": {"test": "value"}}'
```

Response:
```json
{
  "error": "UNKNOWN_ENTITY_TYPE",
  "message": "Unknown or non-writable entity type: invalid. Available types: asset, business, offer, process, unit",
  "available_types": ["asset", "business", "offer", "process", "unit"]
}
```

### SDK Discovery

```python
write_registry = EntityWriteRegistry(get_registry())
available_types = write_registry.writable_types()
print(available_types)  # ['asset', 'business', 'offer', 'process', 'unit']

# Check if type is writable
if write_registry.is_writable("offer"):
    info = write_registry.get("offer")
    print(info.descriptor_index)
    # {'weekly_ad_spend': 'Weekly Ad Spend', 'status': 'Status', ...}
```

### Holder Entities Not Writable

Holder entities (business_holder, unit_holder, etc.) are not writable targets. They serve as navigational containers, not direct write targets.

Attempting to write to a holder returns UNKNOWN_ENTITY_TYPE.

## Pipeline Architecture

### Write Flow

```
1. Registry Lookup
   EntityWriteRegistry.get(entity_type) -> WritableEntityInfo

2. Fetch Task
   AsanaClient.tasks.get_async(gid, opt_fields=[custom_fields, memberships, ...])

3. Verify Membership
   Check task.memberships contains entity project GID

4. Construct FieldResolver
   FieldResolver(custom_fields_data, descriptor_index, core_fields)

5. Resolve Fields
   resolver.resolve_fields(fields, list_mode) -> list[ResolvedField]

6. Build Payload
   Separate core fields and custom_fields dict

7. Execute Asana Update
   AsanaClient.tasks.update_async(gid, **core_fields, custom_fields={...})

8. Optional Refetch
   If include_updated=true, refetch with cache invalidation

9. Fire-and-Forget Invalidation
   asyncio.create_task(invalidator.invalidate_async(event))
```

### Cache Invalidation

After successful write, emits `MutationEvent`:

```python
MutationEvent(
    entity_kind=EntityKind.TASK,
    entity_gid=gid,
    mutation_type=MutationType.UPDATE,
    project_gids=[entity_project_gid],
)
```

Fire-and-forget background task. Errors logged but don't fail the write request.

**Refetch behavior**: When `include_updated=true`, cache entry invalidated before refetch to ensure fresh data.

## Common Patterns

### Clear a Field

```json
{
  "fields": {
    "weekly_ad_spend": null
  }
}
```

Set any field to `null` to clear. Works for all field types.

### Update Multiple Field Types

```json
{
  "fields": {
    "name": "New Offer Name",
    "weekly_ad_spend": 2000,
    "status": "Active",
    "ai_ad_types": ["Facebook", "Google"],
    "notes": "Updated via API"
  }
}
```

Mix core fields (name, notes) with custom fields in single request.

### Append to Multi-Enum Without Reading Current Value

```json
{
  "fields": {
    "ai_ad_types": ["Instagram"]
  },
  "list_mode": "append"
}
```

Server-side merge. No need to fetch current selections.

### Handle Partial Failures

```python
result = await service.write_async(
    entity_type="offer",
    gid=gid,
    fields={
        "weekly_ad_spend": 1500,
        "invalid_field": "value",
        "status": "Active",
    },
)

successful_fields = [
    rf.input_name
    for rf in result.field_results
    if rf.status == "resolved"
]

failed_fields = [
    (rf.input_name, rf.error)
    for rf in result.field_results
    if rf.status in ("skipped", "error")
]

print(f"Success: {', '.join(successful_fields)}")
for name, error in failed_fields:
    print(f"Failed {name}: {error}")
```

Some fields can fail without blocking others. Check per-field status.

### Validate Before Writing (SDK)

```python
# Check if entity type is writable
if not write_registry.is_writable("offer"):
    raise ValueError("Entity type not writable")

# Get writable info to inspect fields
info = write_registry.get("offer")
field_name = "weekly_ad_spend"

if field_name not in info.descriptor_index:
    # Try to find suggestions
    available = list(info.descriptor_index.keys())
    suggestions = difflib.get_close_matches(field_name, available, n=3)
    raise ValueError(f"Field not found. Did you mean: {suggestions}")
```

Pre-validate field names before API call to avoid round-trip errors.

## Troubleshooting

### 401 SERVICE_TOKEN_REQUIRED

PAT token used instead of S2S JWT. Entity Write API requires service token authentication.

**Fix**: Use S2S JWT token in Authorization header. Contact platform team for JWT configuration.

### 404 UNKNOWN_ENTITY_TYPE

Entity type not registered or has no writable fields.

**Check**:
1. Verify entity type spelling (snake_case)
2. Confirm entity model has `CustomFieldDescriptor` properties
3. Check `EntityRegistry` includes entity with `primary_project_gid`

**Debug**:
```python
registry = EntityWriteRegistry(get_registry())
print(registry.writable_types())
```

### 404 TASK_NOT_FOUND

GID does not exist in Asana.

**Check**:
1. Verify GID format (13+ digit string)
2. Confirm task exists in Asana workspace
3. Check bot PAT has access to task's project

### 404 ENTITY_TYPE_MISMATCH

Task exists but not in expected project.

**Check**:
1. Verify task's project memberships in Asana UI
2. Compare task project GID with entity type's registered project GID
3. Task may be in wrong project or entity_type parameter is incorrect

**Debug**:
```python
info = write_registry.get("offer")
print(f"Expected project: {info.project_gid}")

# Fetch task memberships
task = await client.tasks.get_async(gid, opt_fields=["memberships.project.gid"])
projects = [m["project"]["gid"] for m in task.get("memberships", [])]
print(f"Actual projects: {projects}")
```

### 422 NO_VALID_FIELDS

All fields failed resolution or validation.

**Check**:
1. Review `field_results` in response for individual errors
2. Verify field names match entity model descriptors or Asana display names
3. Check value types match field types (number, text, enum)
4. Inspect suggestions for typos

**Example**:
```json
{
  "error": "NO_VALID_FIELDS",
  "message": "All fields failed resolution -- nothing to write."
}
```

Likely causes: All field names misspelled, wrong entity type, or empty fields dict.

### Fields Skipped with Suggestions

Field name not found. Check suggestions for typos or case mismatches.

```json
{
  "name": "weekly_spend",
  "status": "skipped",
  "suggestions": ["weekly_ad_spend"]
}
```

**Fix**: Use suggested field name. Descriptor names are case-sensitive (snake_case). Display names are case-insensitive.

### Enum Value Skipped

Enum option name not recognized.

```json
{
  "name": "status",
  "status": "skipped",
  "suggestions": ["Active", "Paused"]
}
```

**Fix**: Use exact option name from suggestions. Case-insensitive but must match enabled options.

### Number Field Rounded

Asana rounds to field precision.

**Example**: Field with precision=0 converts 999.99 → 1000.

**Check**: Review field settings in Asana. Adjust precision if needed or expect rounding.

### 429 RATE_LIMITED

Asana API rate limit exceeded.

**Fix**: Implement exponential backoff. Use `Retry-After` header when present. Batch writes where possible.

### 503 DISCOVERY_INCOMPLETE

EntityWriteRegistry not initialized. Service still starting up.

**Fix**: Retry after service fully initialized. Registry built during app lifespan startup.

### Cache Invalidation Not Working

Invalidation runs fire-and-forget. Errors logged but don't fail the write.

**Check**:
1. Verify `mutation_invalidator` passed to `write_async()`
2. Review logs for "entity_write_cache_invalidation_failed" warnings
3. Confirm Redis/cache provider connectivity

**Note**: Write succeeds even if invalidation fails. Cache expires naturally via TTL.
