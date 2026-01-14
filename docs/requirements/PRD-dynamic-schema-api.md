# PRD: Dynamic Schema API Parameter

## Metadata

| Field | Value |
|-------|-------|
| PRD ID | PRD-dynamic-schema-api |
| Status | Draft |
| Author | Requirements Analyst |
| Created | 2025-01-14 |
| Impact | low |
| Impact Categories | - |

---

## Overview

Replace the hardcoded `SchemaType` enum in the dataframes API with dynamic schema validation sourced from the `SchemaRegistry`. This change exposes all 7 registered schemas via the API instead of the current 3, enabling users to query Offer, Business, AssetEdit, and AssetEditHolder entity types through the existing `/api/v1/dataframes/` endpoints.

---

## Background

### Current State

The dataframes API in `src/autom8_asana/api/routes/dataframes.py` defines a static `SchemaType` enum:

```python
class SchemaType(str, Enum):
    base = "base"
    unit = "unit"
    contact = "contact"
```

This enum restricts API users to only 3 schema types despite the `SchemaRegistry` (located at `src/autom8_asana/dataframes/models/registry.py`) registering 7 schemas:

| Registry Key | Schema Name | API Accessible |
|--------------|-------------|----------------|
| `*` | base | Yes |
| `Unit` | unit | Yes |
| `Contact` | contact | Yes |
| `Business` | business | No |
| `Offer` | offer | No |
| `AssetEdit` | asset_edit | No |
| `AssetEditHolder` | asset_edit_holder | No |

### Problem Statement

Users cannot extract DataFrame data for Offer, Business, AssetEdit, or AssetEditHolder entities through the API. When a user attempts to pass `schema=offer` or `schema=asset_edit`, FastAPI returns a 422 validation error because these values are not members of the `SchemaType` enum.

This creates a maintenance burden: every time a new schema is added to the registry, the API enum must be manually updated to expose it.

### Technical Context

| Component | Location | Purpose |
|-----------|----------|---------|
| `SchemaType` enum | `api/routes/dataframes.py:59-64` | Hardcoded schema validation |
| `_get_schema()` | `api/routes/dataframes.py:67-75` | Schema lookup via match statement |
| `SchemaRegistry` | `dataframes/models/registry.py` | Canonical source of schema definitions |
| `SchemaRegistry.list_task_types()` | Line 173-182 | Returns all registered task types |
| `SchemaRegistry.get_schema()` | Line 102-124 | Retrieves schema by task type |
| `SchemaRegistry.has_schema()` | Line 159-171 | Validates task type existence |

---

## User Stories

### US-001: Access Additional Entity Schemas

**As a** API consumer building analytics dashboards
**I want to** request DataFrame data using any registered schema (e.g., `schema=offer`, `schema=asset_edit`)
**So that** I can extract structured data for all entity types in the Asana workspace

**Acceptance Criteria**:
- [ ] `GET /api/v1/dataframes/project/{gid}?schema=offer` returns Offer entity data
- [ ] `GET /api/v1/dataframes/project/{gid}?schema=business` returns Business entity data
- [ ] `GET /api/v1/dataframes/project/{gid}?schema=asset_edit` returns AssetEdit entity data
- [ ] `GET /api/v1/dataframes/project/{gid}?schema=asset_edit_holder` returns AssetEditHolder entity data
- [ ] Same schemas work for section endpoint: `GET /api/v1/dataframes/section/{gid}`

### US-002: Backwards Compatibility

**As an** existing API consumer
**I want** my current API calls using `schema=base`, `schema=unit`, or `schema=contact` to continue working
**So that** I don't need to update any existing integrations

**Acceptance Criteria**:
- [ ] `schema=base` continues to work identically
- [ ] `schema=unit` continues to work identically
- [ ] `schema=contact` continues to work identically
- [ ] Response shape unchanged for existing schemas
- [ ] No breaking changes to existing API contract

### US-003: Helpful Error Messages

**As a** developer debugging an API call
**I want to** receive a clear error message listing valid schema names when I use an invalid schema
**So that** I can quickly correct my request without consulting external documentation

**Acceptance Criteria**:
- [ ] Invalid schema returns HTTP 400 (Bad Request)
- [ ] Error response includes list of valid schema names
- [ ] Error message follows existing API error response format
- [ ] Schema names are presented in lowercase (API convention)

### US-004: Auto-Discovery of New Schemas

**As a** platform maintainer
**I want** newly registered schemas to automatically become available via the API
**So that** I don't need to modify API code when adding new entity types

**Acceptance Criteria**:
- [ ] Adding a new schema to `SchemaRegistry` automatically exposes it via API
- [ ] No code changes required in `dataframes.py` for new schemas
- [ ] OpenAPI documentation reflects available schemas dynamically

---

## Functional Requirements

### Must Have

#### FR-001: Remove Hardcoded SchemaType Enum

The `SchemaType` enum class shall be removed from `dataframes.py`. Schema validation shall be performed dynamically against the `SchemaRegistry` singleton.

#### FR-002: Dynamic Schema Validation

The API shall validate the `schema` query parameter by checking `SchemaRegistry.has_schema()` or equivalent lookup. Valid schema names shall be derived from:

1. The `schema.name` attribute of each registered schema (lowercase: `base`, `unit`, `contact`, `business`, `offer`, `asset_edit`, `asset_edit_holder`)
2. The registry key/task type as a fallback alias (e.g., `Unit` -> `unit`)

**Mapping Logic**:

| API Parameter | Registry Lookup |
|---------------|-----------------|
| `base` | `*` (wildcard) |
| `unit` | `Unit` |
| `contact` | `Contact` |
| `business` | `Business` |
| `offer` | `Offer` |
| `asset_edit` | `AssetEdit` |
| `asset_edit_holder` | `AssetEditHolder` |

#### FR-003: Replace _get_schema() Implementation

The `_get_schema()` function shall be refactored to:

1. Accept a string schema name (not an enum)
2. Map the lowercase schema name to the registry key
3. Return the schema via `SchemaRegistry.get_instance().get_schema(task_type)`
4. Raise `HTTPException` with status 400 if schema not found

#### FR-004: Maintain Query Parameter Default

The `schema` query parameter shall default to `"base"` to maintain backwards compatibility:

```python
schema: Annotated[
    str,
    Query(description="Schema to use for extraction"),
] = "base"
```

#### FR-005: Error Response Format

Invalid schema requests shall return:

```json
{
  "detail": {
    "error": "INVALID_SCHEMA",
    "message": "Unknown schema 'invalid'. Valid schemas: base, unit, contact, business, offer, asset_edit, asset_edit_holder",
    "valid_schemas": ["base", "unit", "contact", "business", "offer", "asset_edit", "asset_edit_holder"]
  }
}
```

### Should Have

#### FR-006: OpenAPI Schema Description

The `schema` query parameter shall include a description listing available schemas:

```python
Query(
    description="Schema to use for extraction. Valid values: base, unit, contact, business, offer, asset_edit, asset_edit_holder"
)
```

This description should be generated dynamically from the registry where feasible within FastAPI constraints.

#### FR-007: Case-Insensitive Schema Names

The API should accept schema names in any case (e.g., `schema=UNIT`, `schema=Unit`, `schema=unit`) and normalize to lowercase internally.

### Could Have

#### FR-008: Schema Discovery Endpoint

A new endpoint `GET /api/v1/dataframes/schemas` could list available schemas with their field definitions:

```json
{
  "schemas": [
    {
      "name": "base",
      "task_type": "*",
      "version": "1.0.0",
      "field_count": 10
    },
    {
      "name": "unit",
      "task_type": "Unit",
      "version": "1.1.0",
      "field_count": 21
    }
  ]
}
```

---

## Non-Functional Requirements

### NFR-001: Performance

| Metric | Target |
|--------|--------|
| Schema lookup latency | < 1ms (registry is singleton, already initialized) |
| No regression in endpoint response time | < 5% increase |
| Memory overhead | None (reuses existing registry) |

### NFR-002: Maintainability

| Metric | Target |
|--------|--------|
| Lines of code change | Net reduction (remove enum + match statement) |
| Single source of truth | SchemaRegistry is authoritative for schema list |
| Test coverage | Maintain existing coverage level |

### NFR-003: Compatibility

| Metric | Target |
|--------|--------|
| API backwards compatibility | 100% for existing valid requests |
| HTTP status codes | Unchanged for valid requests |
| Response format | Unchanged |

---

## Edge Cases

| Case | Expected Behavior |
|------|------------------|
| Empty schema parameter `?schema=` | Use default value `"base"` |
| Missing schema parameter | Use default value `"base"` |
| Schema with wrong case `?schema=UNIT` | Accept (case-insensitive) or reject with valid options |
| Unknown schema `?schema=invalid` | HTTP 400 with valid schema list |
| Schema exists in registry but has no data | Return empty DataFrame (existing behavior) |
| Registry not initialized | Registry lazy-initializes on first access (existing behavior) |
| Concurrent schema parameter validation | Thread-safe (registry uses locks) |
| Schema name with special characters `?schema=foo%20bar` | HTTP 400, invalid schema |
| Wildcard schema `?schema=*` | Map to `base` schema OR return 400 (design decision) |

---

## Success Criteria

- [ ] All 7 registered schemas accessible via API (`base`, `unit`, `contact`, `business`, `offer`, `asset_edit`, `asset_edit_holder`)
- [ ] Existing API calls with `schema=base`, `schema=unit`, `schema=contact` unchanged
- [ ] Invalid schema returns HTTP 400 with list of valid schemas
- [ ] `SchemaType` enum removed from `dataframes.py`
- [ ] `_get_schema()` uses `SchemaRegistry` for lookup
- [ ] Unit tests cover all 7 schemas
- [ ] Integration tests verify backwards compatibility
- [ ] OpenAPI spec reflects available schemas

---

## Out of Scope

| Item | Rationale |
|------|-----------|
| New schema definitions | This PRD addresses API exposure, not schema creation |
| Schema field filtering | Different feature (select specific columns in response) |
| Schema versioning in API | Schemas have internal versions; API does not expose version selection |
| GraphQL endpoint | REST API is current contract |
| Runtime schema registration via API | Security concern; schemas registered at startup only |
| Deprecation of specific schema names | All registry schemas should be exposed |
| Changes to SchemaRegistry itself | Registry API is stable and sufficient |

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| SchemaRegistry singleton | Implemented | Thread-safe, lazy-initialized |
| SchemaRegistry.get_schema() | Implemented | Returns schema or raises SchemaNotFoundError |
| SchemaRegistry.has_schema() | Implemented | Returns bool |
| SchemaRegistry.list_task_types() | Implemented | Returns list excluding "*" |
| All 7 schemas registered | Implemented | BASE, UNIT, BUSINESS, CONTACT, OFFER, ASSET_EDIT, ASSET_EDIT_HOLDER |

---

## Implementation Notes

### Schema Name Mapping

The registry uses task types as keys (e.g., `"Unit"`, `"AssetEdit"`), while schemas have a `name` attribute (e.g., `"unit"`, `"asset_edit"`). The API should accept the lowercase `name` and map to the registry key:

```python
SCHEMA_NAME_TO_TASK_TYPE = {
    "base": "*",
    "unit": "Unit",
    "contact": "Contact",
    "business": "Business",
    "offer": "Offer",
    "asset_edit": "AssetEdit",
    "asset_edit_holder": "AssetEditHolder",
}
```

Alternatively, build this mapping dynamically:

```python
def _build_schema_mapping() -> dict[str, str]:
    registry = SchemaRegistry.get_instance()
    mapping = {"base": "*"}  # Special case for wildcard
    for task_type in registry.list_task_types():
        schema = registry.get_schema(task_type)
        mapping[schema.name] = task_type
    return mapping
```

### Validation Function

```python
def _validate_and_get_schema(schema_name: str) -> DataFrameSchema:
    """Validate schema name and return schema from registry."""
    registry = SchemaRegistry.get_instance()
    task_type = SCHEMA_NAME_TO_TASK_TYPE.get(schema_name.lower())

    if task_type is None or not registry.has_schema(task_type):
        valid_schemas = list(SCHEMA_NAME_TO_TASK_TYPE.keys())
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_SCHEMA",
                "message": f"Unknown schema '{schema_name}'. Valid schemas: {', '.join(sorted(valid_schemas))}",
                "valid_schemas": sorted(valid_schemas),
            }
        )

    return registry.get_schema(task_type)
```

---

## Appendix A: Current vs. Proposed Code

### Current Implementation

```python
class SchemaType(str, Enum):
    base = "base"
    unit = "unit"
    contact = "contact"

def _get_schema(schema_type: SchemaType):
    match schema_type:
        case SchemaType.unit:
            return UNIT_SCHEMA
        case SchemaType.contact:
            return CONTACT_SCHEMA
        case SchemaType.base:
            return BASE_SCHEMA
```

### Proposed Implementation

```python
from autom8_asana.dataframes.models.registry import SchemaRegistry

SCHEMA_NAME_TO_TASK_TYPE = {
    "base": "*",
    "unit": "Unit",
    "contact": "Contact",
    "business": "Business",
    "offer": "Offer",
    "asset_edit": "AssetEdit",
    "asset_edit_holder": "AssetEditHolder",
}

def _get_schema(schema_name: str) -> DataFrameSchema:
    """Get DataFrameSchema for the given schema name."""
    registry = SchemaRegistry.get_instance()
    task_type = SCHEMA_NAME_TO_TASK_TYPE.get(schema_name.lower())

    if task_type is None:
        valid_schemas = sorted(SCHEMA_NAME_TO_TASK_TYPE.keys())
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_SCHEMA",
                "message": f"Unknown schema '{schema_name}'. Valid schemas: {', '.join(valid_schemas)}",
                "valid_schemas": valid_schemas,
            }
        )

    return registry.get_schema(task_type)
```

---

## Appendix B: Test Cases

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| Valid existing schema | `schema=unit` | 200, Unit schema data |
| Valid new schema | `schema=offer` | 200, Offer schema data |
| Valid new schema | `schema=asset_edit` | 200, AssetEdit schema data |
| Invalid schema | `schema=invalid` | 400, error with valid list |
| Default schema | (no param) | 200, Base schema data |
| Case insensitive | `schema=UNIT` | 200, Unit schema data (if FR-007 implemented) |
| Empty schema | `schema=` | 200, Base schema data (default) |

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD | /Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-dynamic-schema-api.md | Yes |
