---
artifact_id: TDD-dynamic-schema-api
title: "Dynamic Schema API Parameter"
created_at: "2026-01-14T15:00:00Z"
author: architect
prd_ref: PRD-dynamic-schema-api
status: draft
components:
  - name: SchemaValidator
    type: module
    description: "Dynamic schema validation replacing hardcoded SchemaType enum"
    dependencies:
      - name: SchemaRegistry
        type: internal
      - name: FastAPI
        type: external
  - name: SchemaMappingProvider
    type: module
    description: "Builds and caches the schema name to task type mapping"
    dependencies:
      - name: SchemaRegistry
        type: internal
api_contracts:
  - endpoint: "GET /api/v1/dataframes/project/{gid}"
    method: GET
    description: "Get project tasks as DataFrame with dynamic schema selection"
    request:
      query_params:
        schema: "str - Schema name (default: 'base'). Valid: base, unit, contact, business, offer, asset_edit, asset_edit_holder"
        limit: "int - Items per page (1-100, default: 100)"
        offset: "str | None - Pagination cursor"
      headers:
        Accept: "Response format preference (application/json or application/x-polars-json)"
    response:
      success:
        status: 200
        body:
          data: array
          meta: object
      errors:
        - status: 400
          description: "Invalid schema name"
          body:
            detail:
              error: "INVALID_SCHEMA"
              message: "string"
              valid_schemas: "list[str]"
  - endpoint: "GET /api/v1/dataframes/section/{gid}"
    method: GET
    description: "Get section tasks as DataFrame with dynamic schema selection"
    request:
      query_params:
        schema: "str - Schema name (default: 'base'). Valid: base, unit, contact, business, offer, asset_edit, asset_edit_holder"
        limit: "int - Items per page (1-100, default: 100)"
        offset: "str | None - Pagination cursor"
      headers:
        Accept: "Response format preference"
    response:
      success:
        status: 200
        body:
          data: array
          meta: object
      errors:
        - status: 400
          description: "Invalid schema name"
        - status: 404
          description: "Section not found"
data_models:
  - name: SchemaMapping
    type: value_object
    fields:
      - name: name_to_task_type
        type: dict[str, str]
        required: true
        constraints: "Lowercase schema names to registry task type keys"
      - name: valid_schema_names
        type: list[str]
        required: true
        constraints: "Sorted list of valid schema names for error messages"
security_considerations:
  - "No security domains affected - internal data model change only"
  - "Schema validation prevents arbitrary registry key injection"
  - "Case-insensitive normalization prevents enumeration attacks"
related_adrs:
  - ADR-0066
schema_version: "1.0"
---

# TDD: Dynamic Schema API Parameter

> Technical Design Document for replacing the hardcoded `SchemaType` enum with dynamic schema validation sourced from the `SchemaRegistry`.

---

## 1. Overview

This TDD defines the technical design for removing the hardcoded `SchemaType` enum from `dataframes.py` and replacing it with dynamic validation against the `SchemaRegistry`. This change exposes all 7 registered schemas via the API instead of the current 3.

### 1.1 Design Goals

| Goal | Approach |
|------|----------|
| **Single Source of Truth** | SchemaRegistry becomes authoritative for available schemas |
| **Backwards Compatibility** | Existing API calls unchanged; same response format |
| **Helpful Errors** | Invalid schema returns 400 with list of valid options |
| **Maintainability** | New schemas auto-exposed without API code changes |
| **Performance** | Schema mapping cached; no per-request registry iteration |

### 1.2 Constraints

| Constraint | Value | Source |
|------------|-------|--------|
| Backwards compatibility | 100% | PRD US-002 |
| Error status code | HTTP 400 | PRD FR-005 |
| Default schema | "base" | PRD FR-004 |
| Case handling | Case-insensitive | PRD FR-007 (Should Have) |

---

## 2. Architecture

### 2.1 System Context

```
                    +------------------+
                    |   API Request    |
                    | ?schema=unit     |
                    +--------+---------+
                             |
                             v
+-------------------+    +---+-----------------+
|  FastAPI Router   |--->| _get_schema()       |
| dataframes.py     |    | Schema Validator    |
+-------------------+    +--------+------------+
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
         +------------------+        +--------------------+
         | SchemaMappingProvider|    | SchemaRegistry     |
         | (Cached mapping)     |    | (Singleton)        |
         +------------------+        +--------------------+
                    |                           |
                    +-------------+-------------+
                                  |
                                  v
                        +------------------+
                        | DataFrameSchema  |
                        | (unit, business, |
                        |  offer, etc.)    |
                        +------------------+
```

### 2.2 Component Architecture

```
src/autom8_asana/api/routes/dataframes.py
  - REMOVE: class SchemaType(str, Enum)
  - MODIFY: _get_schema() function
  - ADD: _build_schema_mapping() function (module-level)
  - ADD: SCHEMA_NAME_TO_TASK_TYPE (module-level cached mapping)
  - MODIFY: get_project_dataframe() endpoint signature
  - MODIFY: get_section_dataframe() endpoint signature
```

---

## 3. Design Decision: Mapping Strategy

### 3.1 Decision: Static Mapping with Dynamic Generation

**Decision**: Use a static module-level mapping dict, built dynamically on first access via the SchemaRegistry.

**Alternatives Considered**:

| Strategy | Pros | Cons |
|----------|------|------|
| **Static mapping built on import** | Fast lookup; simple; predictable | Built once per process; requires restart for new schemas |
| Pydantic custom validator | Integrates with FastAPI validation | Complex; harder to customize error format |
| Dynamic registry lookup per request | Always current | Performance overhead; repeated iteration |
| Enum generated from registry | Type safety; IDE completion | Requires code generation; restart to update |

**Rationale**: The static mapping approach provides:
1. O(1) lookup performance
2. No per-request registry iteration
3. Schema mapping built once when module loads (registry lazy-initializes)
4. Clear, readable code
5. Custom error messages with schema list

The tradeoff of requiring process restart for new schemas is acceptable because schema changes require code deployment anyway.

See **ADR-0066** for full decision record.

### 3.2 Schema Name to Task Type Mapping

The registry uses task types as keys (e.g., `"Unit"`, `"AssetEdit"`), while schemas have a `name` attribute (e.g., `"unit"`, `"asset_edit"`). The API accepts lowercase names.

```python
# Built dynamically from SchemaRegistry
SCHEMA_NAME_TO_TASK_TYPE = {
    "base": "*",           # Wildcard/base schema
    "unit": "Unit",
    "contact": "Contact",
    "business": "Business",
    "offer": "Offer",
    "asset_edit": "AssetEdit",
    "asset_edit_holder": "AssetEditHolder",
}
```

### 3.3 Dynamic Mapping Builder

```python
def _build_schema_mapping() -> dict[str, str]:
    """Build schema name to task type mapping from registry.

    Returns:
        Dict mapping lowercase schema names to registry task type keys.

    Note:
        Called once at module load. SchemaRegistry uses lazy initialization
        with double-checked locking, so first access initializes it.
    """
    registry = SchemaRegistry.get_instance()

    # Special case: base schema uses "*" wildcard
    mapping = {"base": "*"}

    # Build mapping from registered schemas
    for task_type in registry.list_task_types():
        schema = registry.get_schema(task_type)
        mapping[schema.name] = task_type

    return mapping
```

---

## 4. Implementation Approach

### 4.1 Module-Level Mapping (Lazy Initialization)

```python
# src/autom8_asana/api/routes/dataframes.py

from autom8_asana.dataframes.models.registry import SchemaRegistry

# Module-level cached mapping (built on first access)
_schema_mapping: dict[str, str] | None = None
_valid_schemas: list[str] | None = None


def _get_schema_mapping() -> tuple[dict[str, str], list[str]]:
    """Get cached schema mapping, building it if necessary.

    Returns:
        Tuple of (name_to_task_type mapping, sorted valid schema names).

    Note:
        Thread-safe: SchemaRegistry._ensure_initialized() uses locking.
        The global assignment is atomic in CPython.
    """
    global _schema_mapping, _valid_schemas

    if _schema_mapping is None:
        registry = SchemaRegistry.get_instance()

        # Build mapping: schema.name -> task_type
        mapping = {"base": "*"}  # Special case for wildcard
        for task_type in registry.list_task_types():
            schema = registry.get_schema(task_type)
            mapping[schema.name] = task_type

        _schema_mapping = mapping
        _valid_schemas = sorted(mapping.keys())

    return _schema_mapping, _valid_schemas
```

### 4.2 Schema Validation Function

```python
def _get_schema(schema_name: str) -> DataFrameSchema:
    """Get DataFrameSchema for the given schema name.

    Args:
        schema_name: Schema name from API request (case-insensitive).

    Returns:
        DataFrameSchema from registry.

    Raises:
        HTTPException: 400 if schema name is invalid.
    """
    mapping, valid_schemas = _get_schema_mapping()

    # Normalize to lowercase for case-insensitive lookup
    normalized = schema_name.lower().strip()

    task_type = mapping.get(normalized)

    if task_type is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_SCHEMA",
                "message": f"Unknown schema '{schema_name}'. Valid schemas: {', '.join(valid_schemas)}",
                "valid_schemas": valid_schemas,
            },
        )

    registry = SchemaRegistry.get_instance()
    return registry.get_schema(task_type)
```

### 4.3 Updated Endpoint Signature

```python
@router.get(
    "/project/{gid}",
    summary="Get project tasks as dataframe",
    # ... existing responses ...
)
async def get_project_dataframe(
    gid: str,
    client: AsanaClientDualMode,
    request_id: RequestId,
    schema: Annotated[
        str,
        Query(
            description="Schema to use for extraction. Valid values: base, unit, contact, business, offer, asset_edit, asset_edit_holder",
        ),
    ] = "base",  # Default to base schema
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_LIMIT, description="Number of items per page"),
    ] = DEFAULT_LIMIT,
    offset: Annotated[
        str | None,
        Query(description="Pagination cursor from previous response"),
    ] = None,
    accept: Annotated[
        str | None,
        Header(alias="Accept", description="Response format preference"),
    ] = MIME_JSON,
) -> Response:
    # ... existing implementation ...

    # Get schema using dynamic validation
    df_schema = _get_schema(schema)

    # ... rest unchanged ...
```

### 4.4 Code to Remove

```python
# REMOVE: Hardcoded enum
class SchemaType(str, Enum):
    """Schema type selector for DataFrame extraction."""
    base = "base"
    unit = "unit"
    contact = "contact"

# REMOVE: Match statement implementation
def _get_schema(schema_type: SchemaType):
    """Get DataFrameSchema for the given schema type."""
    match schema_type:
        case SchemaType.unit:
            return UNIT_SCHEMA
        case SchemaType.contact:
            return CONTACT_SCHEMA
        case SchemaType.base:
            return BASE_SCHEMA

# REMOVE: Direct schema imports (no longer needed)
from autom8_asana.dataframes import (
    BASE_SCHEMA,
    CONTACT_SCHEMA,
    UNIT_SCHEMA,
    ...
)
```

---

## 5. Interface Contracts

### 5.1 Request Format

**Valid Request**:
```
GET /api/v1/dataframes/project/1234567890?schema=offer
GET /api/v1/dataframes/project/1234567890?schema=OFFER  (case-insensitive)
GET /api/v1/dataframes/project/1234567890?schema=asset_edit
GET /api/v1/dataframes/project/1234567890  (defaults to base)
```

### 5.2 Success Response (Unchanged)

```json
{
  "data": [
    {"gid": "123", "name": "Task 1", "type": "Offer"},
    {"gid": "456", "name": "Task 2", "type": "Offer"}
  ],
  "meta": {
    "request_id": "abc123",
    "timestamp": "2026-01-14T00:00:00Z",
    "pagination": {
      "limit": 100,
      "has_more": false,
      "next_offset": null
    }
  }
}
```

### 5.3 Error Response (FR-005)

**Invalid Schema Request**:
```
GET /api/v1/dataframes/project/1234567890?schema=invalid
```

**Response** (HTTP 400):
```json
{
  "detail": {
    "error": "INVALID_SCHEMA",
    "message": "Unknown schema 'invalid'. Valid schemas: asset_edit, asset_edit_holder, base, business, contact, offer, unit",
    "valid_schemas": ["asset_edit", "asset_edit_holder", "base", "business", "contact", "offer", "unit"]
  }
}
```

### 5.4 OpenAPI Documentation

The Query parameter description will list available schemas:

```yaml
parameters:
  - name: schema
    in: query
    required: false
    schema:
      type: string
      default: "base"
    description: "Schema to use for extraction. Valid values: base, unit, contact, business, offer, asset_edit, asset_edit_holder"
```

**Note**: FastAPI does not support dynamic enum generation from runtime data for OpenAPI. The description string provides discoverability. For full dynamic schema discovery, consider implementing the optional FR-008 schema discovery endpoint in a future iteration.

---

## 6. Error Handling Strategy

### 6.1 Error Classification

| Error Case | HTTP Status | Behavior |
|------------|-------------|----------|
| Unknown schema | 400 | Return valid_schemas list |
| Empty schema string | 200 | Use default "base" |
| Missing schema param | 200 | Use default "base" |
| Schema with special chars | 400 | Return valid_schemas list |
| Wildcard schema `*` | 400 | Not a valid API schema name |

### 6.2 Edge Case Handling

```python
def _get_schema(schema_name: str) -> DataFrameSchema:
    """Get DataFrameSchema for the given schema name."""
    mapping, valid_schemas = _get_schema_mapping()

    # Handle empty/whitespace input (FastAPI defaults handle missing)
    if not schema_name or not schema_name.strip():
        # Use base schema as fallback
        return SchemaRegistry.get_instance().get_schema("*")

    # Normalize: lowercase and strip whitespace
    normalized = schema_name.lower().strip()

    # Block wildcard as direct input (it's exposed as "base")
    if normalized == "*":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_SCHEMA",
                "message": "Unknown schema '*'. Use 'base' for the base schema. Valid schemas: " +
                          ", ".join(valid_schemas),
                "valid_schemas": valid_schemas,
            },
        )

    task_type = mapping.get(normalized)

    if task_type is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_SCHEMA",
                "message": f"Unknown schema '{schema_name}'. Valid schemas: {', '.join(valid_schemas)}",
                "valid_schemas": valid_schemas,
            },
        )

    return SchemaRegistry.get_instance().get_schema(task_type)
```

---

## 7. Thread Safety Analysis

### 7.1 SchemaRegistry Thread Safety

The `SchemaRegistry` is already thread-safe:

```python
class SchemaRegistry:
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def _ensure_initialized(self) -> None:
        """Lazy initialization of built-in schemas."""
        if self._initialized:
            return

        with self._lock:
            # Double-checked locking
            if self._initialized:
                return
            # ... initialization ...
            self._initialized = True
```

### 7.2 Module-Level Mapping Safety

The module-level mapping uses a simple check-then-build pattern:

```python
_schema_mapping: dict[str, str] | None = None

def _get_schema_mapping() -> tuple[dict[str, str], list[str]]:
    global _schema_mapping, _valid_schemas

    if _schema_mapping is None:
        # Build mapping (SchemaRegistry handles its own locking)
        registry = SchemaRegistry.get_instance()
        mapping = {"base": "*"}
        for task_type in registry.list_task_types():
            schema = registry.get_schema(task_type)
            mapping[schema.name] = task_type

        _schema_mapping = mapping  # Atomic assignment in CPython
        _valid_schemas = sorted(mapping.keys())

    return _schema_mapping, _valid_schemas
```

**Thread Safety Assessment**:
1. `SchemaRegistry.get_instance()` - Thread-safe (double-checked locking)
2. `registry.list_task_types()` - Thread-safe (uses lock)
3. `registry.get_schema()` - Thread-safe (uses lock)
4. `_schema_mapping = mapping` - Atomic in CPython (GIL)

**Worst Case**: Two threads both see `_schema_mapping is None` and both build the mapping. Both will produce identical mappings. The final assignment is atomic, so one wins. No corruption or invalid state is possible.

For additional safety, a lock could be added, but it's not necessary given:
- Mapping is immutable once built
- Both threads produce identical results
- This is a hot path; unnecessary locking hurts performance

---

## 8. Test Plan

### 8.1 Unit Tests

```python
# tests/api/test_routes_dataframes.py

class TestDynamicSchemaValidation:
    """Tests for dynamic schema validation (TDD-dynamic-schema-api)."""

    def test_all_registered_schemas_accessible(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """All 7 registered schemas are accessible via API."""
        client, mock_sdk = authed_client
        mock_sdk._http.get_paginated.return_value = ([], None)

        valid_schemas = [
            "base", "unit", "contact", "business",
            "offer", "asset_edit", "asset_edit_holder"
        ]

        for schema in valid_schemas:
            response = client.get(
                f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema={schema}",
                headers={"Authorization": "Bearer test_pat_token_12345"},
            )
            assert response.status_code == 200, f"Schema {schema} should be valid"

    def test_invalid_schema_returns_400(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Invalid schema returns 400 (not 422)."""
        client, _ = authed_client

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=invalid",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["error"] == "INVALID_SCHEMA"
        assert "valid_schemas" in detail
        assert len(detail["valid_schemas"]) == 7

    def test_invalid_schema_lists_valid_options(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Error response includes list of valid schemas."""
        client, _ = authed_client

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=foobar",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        detail = response.json()["detail"]
        valid_schemas = detail["valid_schemas"]

        assert "base" in valid_schemas
        assert "unit" in valid_schemas
        assert "business" in valid_schemas
        assert "offer" in valid_schemas
        assert "asset_edit" in valid_schemas

    def test_case_insensitive_schema_validation(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Schema validation is case-insensitive."""
        client, mock_sdk = authed_client
        mock_sdk._http.get_paginated.return_value = ([], None)

        # Test various case combinations
        case_variants = ["UNIT", "Unit", "uNiT", "unit"]

        for variant in case_variants:
            response = client.get(
                f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema={variant}",
                headers={"Authorization": "Bearer test_pat_token_12345"},
            )
            assert response.status_code == 200, f"Schema {variant} should be valid"

    def test_default_schema_unchanged(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Default schema remains 'base' when not specified."""
        client, mock_sdk = authed_client
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

    def test_wildcard_schema_rejected(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Wildcard '*' is rejected as direct input."""
        client, _ = authed_client

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=*",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 400
        assert "base" in response.json()["detail"]["message"]


class TestBackwardsCompatibility:
    """Tests ensuring backwards compatibility (PRD US-002)."""

    def test_existing_schema_base_unchanged(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """schema=base continues to work identically."""
        client, mock_sdk = authed_client
        mock_sdk._http.get_paginated.return_value = ([SAMPLE_TASK_DATA], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=base",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        # Verify response structure unchanged
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert "pagination" in data["meta"]

    def test_existing_schema_unit_unchanged(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """schema=unit continues to work identically."""
        client, mock_sdk = authed_client
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=unit",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

    def test_existing_schema_contact_unchanged(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """schema=contact continues to work identically."""
        client, mock_sdk = authed_client
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=contact",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200


class TestNewSchemaAccess:
    """Tests for newly exposed schemas (PRD US-001)."""

    def test_offer_schema_accessible(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Offer schema is now accessible."""
        client, mock_sdk = authed_client
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=offer",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

    def test_business_schema_accessible(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Business schema is now accessible."""
        client, mock_sdk = authed_client
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=business",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

    def test_asset_edit_schema_accessible(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """AssetEdit schema is now accessible."""
        client, mock_sdk = authed_client
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=asset_edit",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

    def test_asset_edit_holder_schema_accessible(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """AssetEditHolder schema is now accessible."""
        client, mock_sdk = authed_client
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=asset_edit_holder",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

    def test_section_endpoint_supports_new_schemas(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Section endpoint also supports new schemas."""
        client, mock_sdk = authed_client
        mock_sdk._http.get.return_value = {
            "gid": TEST_SECTION_GID,
            "project": {"gid": TEST_PROJECT_GID},
        }
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}?schema=offer",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
```

### 8.2 Test Migration

Update existing tests that expect HTTP 422 for invalid schemas to expect HTTP 400:

```python
# BEFORE (current)
def test_get_project_dataframe_invalid_schema_returns_422(
    self, authed_client: tuple[TestClient, MagicMock]
) -> None:
    """Invalid schema value returns 422 validation error."""
    client, _ = authed_client
    response = client.get(...)
    assert response.status_code == 422

# AFTER (updated)
def test_get_project_dataframe_invalid_schema_returns_400(
    self, authed_client: tuple[TestClient, MagicMock]
) -> None:
    """Invalid schema value returns 400 with valid schema list."""
    client, _ = authed_client
    response = client.get(...)
    assert response.status_code == 400
    assert "valid_schemas" in response.json()["detail"]
```

---

## 9. Migration and Rollback

### 9.1 Migration Steps

1. **Add new implementation** (no breaking changes yet):
   - Add `_get_schema_mapping()` function
   - Add new `_get_schema()` implementation

2. **Update endpoints**:
   - Change `schema` parameter type from `SchemaType` to `str`
   - Update Query description

3. **Remove old code**:
   - Remove `SchemaType` enum
   - Remove old `_get_schema()` match statement
   - Remove direct schema imports (BASE_SCHEMA, UNIT_SCHEMA, CONTACT_SCHEMA)

4. **Update tests**:
   - Change expected status code from 422 to 400
   - Add tests for new schemas
   - Add case-insensitivity tests

### 9.2 Rollback Strategy

**Risk Level**: Low - Internal implementation change with backwards-compatible API.

**Rollback Approach**:
1. Revert the commit (git revert)
2. Redeploy previous version

**No data migration needed** - This is a stateless API change.

### 9.3 Feature Flag (Optional)

If gradual rollout is desired:

```python
import os

USE_DYNAMIC_SCHEMA = os.environ.get("FEATURE_DYNAMIC_SCHEMA", "true").lower() == "true"

def _get_schema(schema_name: str) -> DataFrameSchema:
    if USE_DYNAMIC_SCHEMA:
        return _get_schema_dynamic(schema_name)
    else:
        # Fall back to enum-based validation
        try:
            schema_type = SchemaType(schema_name)
            return _get_schema_legacy(schema_type)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid schema")
```

**Recommendation**: Feature flag adds complexity and is not necessary given the low-risk nature of this change. Direct implementation is preferred.

---

## 10. Performance Analysis

### 10.1 Performance Impact

| Operation | Current | Proposed | Impact |
|-----------|---------|----------|--------|
| Schema lookup | O(1) enum | O(1) dict lookup | None |
| First request | N/A | Registry init + mapping build | ~1ms one-time |
| Subsequent requests | O(1) | O(1) | None |
| Memory | Enum class | ~300 bytes dict | Negligible |

### 10.2 Benchmarks (Expected)

```
# Current (enum validation)
Schema validation: ~0.1ms

# Proposed (dict lookup)
Schema validation: ~0.1ms

# First request initialization
Registry + mapping: ~1-2ms (one-time)
```

---

## 11. Implementation Plan

### Phase 1: Implementation (1-2 hours)

**File**: `src/autom8_asana/api/routes/dataframes.py`

**Tasks**:
1. Add `_get_schema_mapping()` function
2. Replace `_get_schema()` implementation
3. Update endpoint signatures (schema: str instead of SchemaType)
4. Update Query description with all schemas
5. Remove `SchemaType` enum
6. Remove unused imports (BASE_SCHEMA, UNIT_SCHEMA, CONTACT_SCHEMA)

### Phase 2: Tests (1 hour)

**File**: `tests/api/test_routes_dataframes.py`

**Tasks**:
1. Update existing tests (422 -> 400)
2. Add tests for all 7 schemas
3. Add case-insensitivity tests
4. Add error response format tests

### Phase 3: Documentation (30 minutes)

**Tasks**:
1. Update endpoint docstrings
2. Verify OpenAPI spec reflects changes

---

## 12. Architecture Decision Record

### ADR-0066: Dynamic Schema Validation Strategy

**Status**: Proposed

**Context**: The dataframes API uses a hardcoded `SchemaType` enum that restricts users to 3 schemas despite 7 being registered in the SchemaRegistry.

**Decision**: Replace the enum with dynamic validation against SchemaRegistry using a cached module-level mapping.

**Consequences**:
- **Positive**: All registered schemas automatically exposed; single source of truth; better error messages
- **Negative**: No IDE completion for valid schema names; requires restart for new schemas
- **Neutral**: HTTP error code changes from 422 to 400 (semantically more correct)

---

## 13. Artifact Verification

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-dynamic-schema-api.md` | Read |
| Current Implementation | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/dataframes.py` | Read |
| SchemaRegistry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py` | Read |
| DataFrameSchema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/schema.py` | Read |
| Existing Tests | `/Users/tomtenuta/Code/autom8_asana/tests/api/test_routes_dataframes.py` | Read |
| Example Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/asset_edit.py` | Read |
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-dynamic-schema-api.md` | Written |

---

## 14. Handoff Checklist

Ready for Implementation phase when:

- [x] TDD covers all PRD requirements (FR-001 through FR-007)
- [x] Component boundaries and responsibilities are clear
- [x] Data models defined (SchemaMapping)
- [x] API contracts specified (request/response formats)
- [x] Key flows documented (mapping builder, validation)
- [x] Error handling strategy defined
- [x] Thread safety analysis complete
- [x] Test plan outlined with specific test cases
- [x] Migration/rollback approach documented
- [x] Performance impact assessed
- [x] ADR documents mapping strategy decision
- [x] Principal Engineer can implement without architectural questions
- [x] All artifacts verified via Read tool
- [x] Attestation table included with absolute paths

---

**End of TDD**
