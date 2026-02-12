# TDD: Entity Write API

```yaml
id: TDD-ENTITY-WRITE-API
status: draft
prd: PRD-ENTITY-WRITE-API
author: architect
date: 2026-02-11
complexity: MODULE
components:
  - EntityWriteRegistry (new)
  - FieldResolver (new, extracted from FieldSeeder)
  - FieldWriteService (new)
  - Entity write route (new)
  - EntityService (existing, extended)
adrs:
  - ADR-EW-001: PATCH over PUT
  - ADR-EW-002: Unified EntityWriteRegistry with auto-discovery
  - ADR-EW-003: Shared FieldResolver extraction
  - ADR-EW-004: TextListField append semantics
```

---

## 1. Executive Summary

This design introduces a `PATCH /api/v1/entity/{entity_type}/{gid}` endpoint that writes both core Asana fields and custom field values to entities using business-domain field names. The system resolves Python descriptor names (snake_case) and Asana display names (Title Case) to custom field GIDs, validates types, resolves enum values to option GIDs, and executes a single Asana API update call. After a successful write, a fire-and-forget MutationEvent is emitted for cache invalidation.

The design introduces three new components:
1. **EntityWriteRegistry** -- auto-discovers writable entity types from model descriptors at startup
2. **FieldResolver** -- shared utility extracted from FieldSeeder for field name resolution, enum resolution, and type validation
3. **FieldWriteService** -- stateless orchestrator for the validate-resolve-write-invalidate pipeline

Tags, automations, and feature flags are explicitly deferred per stakeholder amendments.

---

## 2. System Context

```
                                     +-------------------+
                                     |   autom8_data     |
                                     | (primary caller)  |
                                     +--------+----------+
                                              |
                                    PATCH /api/v1/entity/{type}/{gid}
                                    Authorization: Bearer <S2S JWT>
                                              |
                                              v
                           +------------------+------------------+
                           |       autom8_asana API Layer        |
                           |  (FastAPI + S2S JWT auth)           |
                           +------------------+------------------+
                                              |
                            +-----------------+-----------------+
                            |                                   |
                            v                                   v
                   +-----------------+                 +------------------+
                   | FieldWriteService|                 | MutationInvalidator|
                   | (orchestrator)  |                 | (fire-and-forget)  |
                   +-------+---------+                 +------------------+
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
     +-------------+ +----------+ +-----------+
     |EntityService| |FieldRes. | |TasksClient|
     |(validation) | |(shared)  | |(Asana API)|
     +------+------+ +----------+ +-----------+
            |
    +-------+--------+
    |                 |
    v                 v
+----------+  +------------------+
|EntityWrite|  |EntityProject     |
|Registry   |  |Registry (existing)|
+----------+  +------------------+
```

---

## 3. Component Architecture

### 3.1 EntityWriteRegistry

**Location**: `src/autom8_asana/resolution/write_registry.py`

**Purpose**: Auto-discovers writable entity types by introspecting entity model classes for `CustomFieldDescriptor` properties at startup. Provides the descriptor-name-to-display-name index used for dual field resolution.

**Why a new registry instead of extending EntityRegistry?**

The existing `EntityRegistry` (`core/entity_registry.py`) is a metadata registry for all entity types -- holders, leaf entities, root entities. Its `EntityDescriptor` is a frozen dataclass defining project GIDs, cache behavior, join keys, and detection metadata. It has no knowledge of custom field descriptors. Adding write-specific concerns (descriptor indices, core field sets, writable status) to `EntityDescriptor` would violate its single responsibility and require modifying a frozen, import-time-validated structure.

`EntityWriteRegistry` is a purpose-built overlay that references `EntityRegistry` for project GID lookup but owns the write-specific index:

```python
@dataclass(frozen=True, slots=True)
class WritableEntityInfo:
    """Write-specific metadata for an entity type.

    Attributes:
        entity_type: Canonical snake_case name.
        model_class: The entity model class (e.g., Offer).
        project_gid: Asana project GID from EntityRegistry.
        descriptor_index: Maps snake_case descriptor name -> Asana display name.
            Example: {"weekly_ad_spend": "Weekly Ad Spend", "mrr": "MRR"}
        core_fields: Set of Asana core field names writable on this type.
    """
    entity_type: str
    model_class: type
    project_gid: str
    descriptor_index: dict[str, str]  # snake_case -> "Display Name"
    core_fields: frozenset[str]


# Known Asana core fields accepted in the `fields` dict.
# These map directly to top-level keys in the Asana PUT /tasks/{gid} body.
CORE_FIELD_NAMES: frozenset[str] = frozenset({
    "name", "assignee", "due_on", "completed", "notes",
})


class EntityWriteRegistry:
    """Auto-discovers writable entities from model descriptors.

    Built once at startup. Provides O(1) lookup by entity type.

    Thread Safety: Immutable after construction.
    """

    def __init__(self, entity_registry: EntityRegistry) -> None:
        self._by_type: dict[str, WritableEntityInfo] = {}
        self._discover(entity_registry)

    def _discover(self, entity_registry: EntityRegistry) -> None:
        """Introspect entity models for CustomFieldDescriptor properties.

        For each EntityDescriptor with a model_class_path, lazily resolve the
        class and scan its MRO for CustomFieldDescriptor instances. Any model
        with at least one CustomFieldDescriptor is registered as writable.
        """
        from autom8_asana.models.business.descriptors import CustomFieldDescriptor

        for desc in entity_registry.all_descriptors():
            if desc.category.value == "holder":
                continue  # Holders are not writable targets

            model_class = desc.get_model_class()
            if model_class is None:
                continue

            # Scan all attributes on the class for descriptors
            descriptor_index: dict[str, str] = {}
            for attr_name in dir(model_class):
                try:
                    attr = getattr(model_class, attr_name)
                except Exception:
                    continue
                if isinstance(attr, CustomFieldDescriptor) and attr.field_name:
                    descriptor_index[attr.public_name] = attr.field_name

            if not descriptor_index:
                continue  # No custom fields = not writable

            project_gid = desc.primary_project_gid
            if project_gid is None:
                continue  # No project = can't validate membership

            self._by_type[desc.name] = WritableEntityInfo(
                entity_type=desc.name,
                model_class=model_class,
                project_gid=project_gid,
                descriptor_index=descriptor_index,
                core_fields=CORE_FIELD_NAMES,
            )

    def get(self, entity_type: str) -> WritableEntityInfo | None:
        """O(1) lookup by entity type name."""
        return self._by_type.get(entity_type)

    def is_writable(self, entity_type: str) -> bool:
        return entity_type in self._by_type

    def writable_types(self) -> list[str]:
        return sorted(self._by_type.keys())
```

**Discovery mechanism**: At app startup (during `lifespan`), the registry is constructed and stored on `app.state.entity_write_registry`. It iterates all `EntityDescriptor` entries, calls `get_model_class()` to lazily import the Python class, then scans for `CustomFieldDescriptor` subclass instances via `dir()` + `getattr()`.

**Relationship to EntityProjectRegistry**: `EntityWriteRegistry` reads `primary_project_gid` from the existing `EntityDescriptor` in `EntityRegistry`. It does NOT replace `EntityProjectRegistry` (which is used for dynamic workspace-project discovery at runtime). The write registry is a static, startup-time overlay.

### 3.2 FieldResolver

**Location**: `src/autom8_asana/resolution/field_resolver.py`

**Purpose**: Extracted from `FieldSeeder` (lines 447-568 of `automation/seeding.py`). A stateless utility that handles:

1. Field name matching (case-insensitive, against live task custom fields)
2. Enum name-to-GID resolution (case-insensitive, with GID passthrough)
3. Multi-enum element-by-element resolution
4. Type validation against `resource_subtype`

```python
@dataclass(frozen=True, slots=True)
class ResolvedField:
    """Result of resolving a single field.

    Attributes:
        input_name: The field name as provided by the caller.
        matched_name: The actual Asana field name (or core field key).
        gid: Custom field GID (None for core fields).
        value: The resolved value ready for the Asana API.
        is_core: True if this is a core Asana field (name, assignee, etc.).
        status: "resolved", "skipped", "error".
        error: Error message if status != "resolved".
        suggestions: Fuzzy-match suggestions if field not found.
    """
    input_name: str
    matched_name: str | None = None
    gid: str | None = None
    value: Any = None
    is_core: bool = False
    status: str = "resolved"
    error: str | None = None
    suggestions: list[str] | None = None


class FieldResolver:
    """Resolves business-domain field names to Asana API payloads.

    Stateless. Constructed per-request with the target task's
    custom field definitions.

    Args:
        custom_fields_data: List of custom field dicts from the Asana
            task response (with name, gid, resource_subtype, enum_options).
        descriptor_index: Maps snake_case descriptor name -> display name.
            From EntityWriteRegistry.WritableEntityInfo.descriptor_index.
        core_fields: Set of core field keys. From CORE_FIELD_NAMES.
    """

    def __init__(
        self,
        custom_fields_data: list[dict[str, Any]],
        descriptor_index: dict[str, str],
        core_fields: frozenset[str],
    ) -> None:
        self._custom_fields = custom_fields_data
        self._descriptor_index = descriptor_index
        self._core_fields = core_fields

        # Build case-insensitive display name -> field def index
        self._display_index: dict[str, dict[str, Any]] = {}
        for field in custom_fields_data:
            name = field.get("name", "")
            if name:
                self._display_index[name.lower().strip()] = field

    def resolve_fields(
        self,
        fields: dict[str, Any],
        list_mode: str = "replace",
    ) -> list[ResolvedField]:
        """Resolve all fields in a request.

        Resolution order per field:
        1. Check core fields (exact key match).
        2. Check descriptor index (O(1) dict lookup by snake_case).
        3. Fall through to display name scan (case-insensitive).
        4. If no match, produce a "skipped" result with fuzzy suggestions.

        Args:
            fields: Dict of field_name -> value from request body.
            list_mode: "replace" or "append" for list-type fields.

        Returns:
            List of ResolvedField results, one per input field.
        """
        results: list[ResolvedField] = []
        for name, value in fields.items():
            result = self._resolve_single(name, value, list_mode)
            results.append(result)
        return results

    def _resolve_single(
        self, name: str, value: Any, list_mode: str
    ) -> ResolvedField:
        """Resolve one field name + value."""

        # Step 1: Core field check
        if name in self._core_fields:
            return ResolvedField(
                input_name=name,
                matched_name=name,
                value=value,
                is_core=True,
            )

        # Step 2: Descriptor index lookup
        display_name = self._descriptor_index.get(name)
        if display_name:
            return self._resolve_custom_field(name, display_name, value, list_mode)

        # Step 3: Display name scan (case-insensitive)
        normalized = name.lower().strip()
        field_def = self._display_index.get(normalized)
        if field_def:
            return self._resolve_custom_field(
                name, field_def["name"], value, list_mode
            )

        # Step 4: Not found -- fuzzy suggestions
        available = [f.get("name", "") for f in self._custom_fields if f.get("name")]
        suggestions = _fuzzy_match(name, available)
        return ResolvedField(
            input_name=name,
            status="skipped",
            error=f"Field '{name}' not found on entity",
            suggestions=suggestions,
        )

    def _resolve_custom_field(
        self,
        input_name: str,
        display_name: str,
        value: Any,
        list_mode: str,
    ) -> ResolvedField:
        """Resolve a custom field by its display name."""
        normalized = display_name.lower().strip()
        field_def = self._display_index.get(normalized)
        if not field_def:
            return ResolvedField(
                input_name=input_name,
                status="skipped",
                error=f"Field '{display_name}' exists in model but not on Asana task",
            )

        gid = field_def.get("gid")
        field_type = field_def.get("resource_subtype", "")

        # Type validation
        type_error = self._validate_type(field_type, value, input_name)
        if type_error:
            return ResolvedField(
                input_name=input_name,
                matched_name=display_name,
                gid=gid,
                status="error",
                error=type_error,
            )

        # Enum resolution
        if field_type == "enum" and value is not None:
            resolved_value = self._resolve_enum(field_def, value, input_name)
            if resolved_value is None:
                options = self._available_enum_options(field_def)
                return ResolvedField(
                    input_name=input_name,
                    matched_name=display_name,
                    gid=gid,
                    status="skipped",
                    error=f"Enum value '{value}' not found",
                    suggestions=options,
                )
            return ResolvedField(
                input_name=input_name,
                matched_name=display_name,
                gid=gid,
                value=resolved_value,
            )

        if field_type == "multi_enum" and value is not None:
            resolved_value = self._resolve_multi_enum(
                field_def, value, input_name, list_mode
            )
            return ResolvedField(
                input_name=input_name,
                matched_name=display_name,
                gid=gid,
                value=resolved_value,
            )

        # TextListField append handling
        if (
            field_type == "text"
            and list_mode == "append"
            and isinstance(value, (str, list))
        ):
            resolved_value = self._resolve_text_append(field_def, value)
            return ResolvedField(
                input_name=input_name,
                matched_name=display_name,
                gid=gid,
                value=resolved_value,
            )

        # Date wrapping
        if field_type == "date" and isinstance(value, str):
            return ResolvedField(
                input_name=input_name,
                matched_name=display_name,
                gid=gid,
                value={"date": value},
            )

        # Pass-through for text, number, people, None (clear)
        return ResolvedField(
            input_name=input_name,
            matched_name=display_name,
            gid=gid,
            value=value,
        )
```

**Enum resolution** reuses the exact `_build_enum_lookup` / `_resolve_single_option` pattern from `FieldSeeder` (case-insensitive name match + GID passthrough). The methods are static and extracted as standalone functions in `field_resolver.py`.

**TextListField append logic** (see Section 6 for full detail):
```python
def _resolve_text_append(
    self, field_def: dict[str, Any], value: str | list[str]
) -> str:
    """Server-side text list append with dedup."""
    # Read current value from field_def (already fetched with task)
    current_text = field_def.get("text_value") or ""
    delimiter = ","
    existing = [
        s.strip() for s in current_text.split(delimiter) if s.strip()
    ]
    new_items = [value] if isinstance(value, str) else value
    for item in new_items:
        item = item.strip()
        if item and item not in existing:
            existing.append(item)
    return delimiter.join(existing)
```

**Shared usage**: After extraction, `FieldSeeder.write_fields_async()` will be refactored to delegate to `FieldResolver` for the resolution phase. This is a refactoring task, not a behavioral change. FieldSeeder keeps its cascade/carry-through/compute logic; only the resolve+match+enum logic moves.

### 3.3 FieldWriteService

**Location**: `src/autom8_asana/services/field_write_service.py`

**Purpose**: Stateless, request-scoped orchestrator for the write pipeline. Keeps the route handler thin.

```python
@dataclass(frozen=True, slots=True)
class WriteFieldsResult:
    """Result of a field write operation.

    Attributes:
        gid: Task GID.
        entity_type: Entity type string.
        field_results: Per-field resolution results.
        fields_written: Count of successfully written fields.
        fields_skipped: Count of skipped/errored fields.
        updated_fields: Echoed or re-fetched field values.
    """
    gid: str
    entity_type: str
    field_results: list[ResolvedField]
    fields_written: int
    fields_skipped: int
    updated_fields: dict[str, Any] | None = None


class FieldWriteService:
    """Orchestrates the validate -> resolve -> write -> invalidate pipeline.

    Stateless. Constructed per-request.

    The service does NOT manage authentication or entity type validation.
    Those concerns live in the route handler (auth dependency) and
    EntityService (type validation). This service receives a pre-validated
    EntityContext and executes the write.
    """

    def __init__(
        self,
        client: AsanaClient,
        write_registry: EntityWriteRegistry,
    ) -> None:
        self._client = client
        self._write_registry = write_registry

    async def write_async(
        self,
        entity_type: str,
        gid: str,
        fields: dict[str, Any],
        list_mode: str = "replace",
        include_updated: bool = False,
    ) -> WriteFieldsResult:
        """Execute the complete write pipeline.

        Steps:
        1. Lookup writable entity info from EntityWriteRegistry.
        2. Fetch task with custom_fields + enum_options + memberships.
        3. Verify task membership in entity type's project.
        4. Construct FieldResolver from task's custom field data.
        5. Resolve all fields (core + custom).
        6. Build Asana API payload (core fields + custom_fields dict).
        7. Execute single TasksClient.update_async() call.
        8. Optionally re-fetch for updated field values.
        9. Emit MutationEvent for cache invalidation.

        Args:
            entity_type: Validated entity type string.
            gid: Task GID to write to.
            fields: Dict of field_name -> value from request.
            list_mode: "replace" or "append".
            include_updated: If True, re-fetch and return current values.

        Returns:
            WriteFieldsResult with per-field results and counts.

        Raises:
            TaskNotFoundError: Task GID does not exist.
            EntityTypeMismatchError: Task not in entity's project.
            NoValidFieldsError: All fields failed validation.
        """
```

**Pipeline flow** (detailed in Section 4).

### 3.4 Entity Write Route

**Location**: `src/autom8_asana/api/routes/entity_write.py`

**Prefix**: `/api/v1/entity`

**Registration**: Added to `api/routes/__init__.py` and `api/main.py` following the existing pattern.

```python
router = APIRouter(prefix="/api/v1/entity", tags=["entity-write"])

@router.patch("/{entity_type}/{gid}")
async def write_entity_fields(
    entity_type: str,
    gid: str,
    body: EntityWriteRequest,
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
    include_updated: bool = False,
) -> EntityWriteResponse:
    """Write fields to an Asana entity.

    Authentication: S2S JWT only (require_service_claims dependency).

    Path Parameters:
        entity_type: Entity type (offer, unit, business, etc.)
        gid: Asana task GID

    Query Parameters:
        include_updated: If true, re-fetch and return current field values.

    Request Body:
        EntityWriteRequest with fields dict and optional list_mode.

    Returns:
        EntityWriteResponse with per-field results.
    """
```

### 3.5 EntityService (existing, unchanged)

`EntityService` (`services/entity_service.py`) is NOT modified. The write route uses `EntityWriteRegistry` directly for write-specific validation (is the type writable?) rather than `EntityService.validate_entity_type()` (which checks queryable/resolvable entities, a different concern). The route does call `get_bot_pat()` for PAT acquisition, matching the resolver pattern.

---

## 4. Data Flow

```
HTTP Request                         HTTP Response
     |                                    ^
     v                                    |
[1] Route Handler                    [10] Build EntityWriteResponse
     |                                    ^
     v                                    |
[2] Auth: require_service_claims     [9] Emit MutationEvent (fire-and-forget)
     |                                    ^
     v                                    |
[3] EntityWriteRegistry.get()        [8] TasksClient.update_async()
     | (validate writable type)           ^
     v                                    |
[4] TasksClient.get_async()          [7] Build API payload
     | (fetch task + custom_fields        ^
     |  + enum_options + memberships)     |
     v                                    |
[5] Verify project membership        [6] FieldResolver.resolve_fields()
```

### Step-by-step

**[1] Route Handler** receives `PATCH /api/v1/entity/{entity_type}/{gid}` with `EntityWriteRequest` body.

**[2] Auth**: FastAPI dependency `require_service_claims` validates S2S JWT. Rejects PAT tokens with 401 `SERVICE_TOKEN_REQUIRED`.

**[3] Registry Lookup**: `EntityWriteRegistry.get(entity_type)` returns `WritableEntityInfo` or raises 404 `UNKNOWN_ENTITY_TYPE` with available writable types.

**[4] Task Fetch**: `TasksClient.get_async(gid, opt_fields=[...])` fetches the task with:
```python
opt_fields=[
    "custom_fields",
    "custom_fields.name",
    "custom_fields.resource_subtype",
    "custom_fields.enum_options",
    "custom_fields.text_value",        # For TextListField append
    "custom_fields.number_value",
    "custom_fields.enum_value",
    "custom_fields.multi_enum_values",
    "memberships.project.gid",
    "name",                            # For re-fetch echo
    "assignee",
    "due_on",
    "completed",
    "notes",
]
```
If Asana returns 404: raise `TaskNotFoundError` (HTTP 404).

**[5] Membership Check**: Verify that at least one `membership.project.gid` matches `WritableEntityInfo.project_gid`. If no match: raise `EntityTypeMismatchError` (HTTP 404).

**[6] Field Resolution**: Construct `FieldResolver` with the task's `custom_fields` data, the `WritableEntityInfo.descriptor_index`, and `CORE_FIELD_NAMES`. Call `resolve_fields(request.fields, request.list_mode)`. Returns `list[ResolvedField]`.

**[7] Payload Construction**:
```python
# Separate core fields from custom fields
core_payload: dict[str, Any] = {}
custom_payload: dict[str, Any] = {}

for rf in resolved_fields:
    if rf.status != "resolved":
        continue
    if rf.is_core:
        core_payload[rf.matched_name] = rf.value
    else:
        custom_payload[rf.gid] = rf.value

# Merge into single Asana API data block
update_kwargs = {**core_payload}
if custom_payload:
    update_kwargs["custom_fields"] = custom_payload
```

If zero fields resolved successfully: raise `NoValidFieldsError` (HTTP 422).

**[8] Asana Write**: `TasksClient.update_async(gid, **update_kwargs)`. This calls `PUT /tasks/{gid}` with the merged `data` block. A single API call handles both core and custom fields (confirmed: Asana API accepts `name`, `assignee`, `custom_fields` etc. in one `data` block).

**[9] Cache Invalidation**: Fire-and-forget emission of `MutationEvent`:
```python
event = MutationEvent(
    entity_kind=EntityKind.TASK,
    entity_gid=gid,
    mutation_type=MutationType.UPDATE,
    project_gids=[write_info.project_gid],
)
# Fire and forget via asyncio.create_task
asyncio.create_task(_invalidate_cache(mutation_invalidator, event))
```

**[10] Response**: Build `EntityWriteResponse` from `ResolvedField` results. If `include_updated=true`, re-fetch task and map custom field values back to business names.

---

## 5. Field Resolution Chain

### Dual Resolution Strategy

Each field name in the request is resolved through a three-step chain:

```
Input: "weekly_ad_spend"
  |
  +-> [1] Core field check: "weekly_ad_spend" in {"name","assignee",...}?
  |       NO -> continue
  |
  +-> [2] Descriptor index: descriptor_index.get("weekly_ad_spend")
  |       MATCH -> "Weekly Ad Spend"
  |       -> Look up "weekly ad spend" in display_index -> field_def
  |       -> Resolve value (type check, enum resolution, etc.)
  |       -> Return ResolvedField(gid=field_def["gid"], value=resolved)
  |
  +-> [3] (skipped -- found in step 2)

Input: "Status"
  |
  +-> [1] Core field check: "Status" in {"name","assignee",...}?
  |       NO -> continue
  |
  +-> [2] Descriptor index: descriptor_index.get("Status")
  |       NO MATCH -> continue
  |
  +-> [3] Display name scan: display_index.get("status")
  |       MATCH -> field_def with name="Status", gid="12345..."
  |       -> Resolve value
  |       -> Return ResolvedField

Input: "name"
  |
  +-> [1] Core field check: "name" in {"name","assignee",...}?
  |       YES -> Return ResolvedField(is_core=True, value=<provided>)
```

### Complexity Analysis

| Step | Complexity | Mechanism |
|------|-----------|-----------|
| Core field check | O(1) | `frozenset.__contains__` |
| Descriptor index | O(1) | `dict.get` on `descriptor_index` |
| Display name scan | O(1) | `dict.get` on pre-built `display_index` |
| Fuzzy suggestion | O(n) | `difflib.get_close_matches` (only on miss) |

All successful resolutions are O(1). Fuzzy matching is only invoked for fields that fail all three resolution steps, and only runs once per unresolved field.

### Core vs Custom Field Separation

Core fields are separated during resolution (step 1) and placed in the top-level `data` block of the Asana API call. Custom fields are collected into the `custom_fields` dict within the same `data` block. Asana's `PUT /tasks/{gid}` accepts both in a single request:

```json
{
  "data": {
    "name": "Updated Offer Name",
    "assignee": "1234567890",
    "custom_fields": {
      "9876543210": 500,
      "1111111111": "1234567890"
    }
  }
}
```

---

## 6. TextListField Append Logic

### Problem

Several entity types use text fields as delimited lists (e.g., `asset_id` on Offer stores comma-separated values like `"asset-123, asset-456"`). The PRD requires an `append` mode that adds new values without replacing existing ones.

### Solution

When `list_mode: "append"` is specified and the target field is a text-type field, `FieldResolver._resolve_text_append()` performs server-side append:

```
Step 1: Read current value from fetched task
        current_text = "asset-123, asset-456"

Step 2: Split on delimiter (comma)
        existing = ["asset-123", "asset-456"]

Step 3: Append new value(s)
        new_items = ["asset-789", "asset-123"]  # from request

Step 4: Dedup (preserve order, skip already-present)
        result = ["asset-123", "asset-456", "asset-789"]

Step 5: Re-join
        output = "asset-123, asset-456, asset-789"
```

### Important details

1. **Delimiter**: Comma (`,`). This is the de facto standard in the codebase -- `asset_id` values are comma-separated in production Asana tasks.

2. **Current value source**: The `text_value` field from the custom field dict in the task fetch response (step [4] in the data flow). No extra API call needed -- the value is already fetched.

3. **String vs list input**: The request can send either `"asset-789"` (single string) or `["asset-789", "asset-790"]` (list). Both are handled.

4. **Case-sensitivity**: Dedup is case-sensitive (exact string match). This preserves the caller's intent -- if they send `"Asset-123"` and `"asset-123"` exists, both are kept.

5. **Empty current**: If the field is currently null/empty, the result is just the new value(s) joined.

6. **Multi-enum append**: For `multi_enum` fields in `append` mode, the existing selected option GIDs are read from `multi_enum_values`, new option GIDs are resolved, and the combined set (deduped) is written back. This leverages the existing multi-enum value in the fetched task data.

```python
def _resolve_multi_enum(
    self, field_def, value, input_name, list_mode
):
    """Resolve multi-enum with optional append."""
    enum_options = field_def.get("enum_options", [])
    lookup = _build_enum_lookup(enum_options)

    if not isinstance(value, list):
        value = [value]

    resolved_gids = []
    for item in value:
        gid = _resolve_single_option(item, lookup, enum_options)
        if gid:
            resolved_gids.append(gid)

    if list_mode == "append":
        # Merge with existing selections
        existing = field_def.get("multi_enum_values") or []
        existing_gids = [
            opt["gid"] for opt in existing
            if isinstance(opt, dict) and "gid" in opt
        ]
        # Dedup: add only new GIDs
        combined = list(existing_gids)
        for gid in resolved_gids:
            if gid not in combined:
                combined.append(gid)
        return combined

    return resolved_gids
```

---

## 7. API Contract

### Request Model

```python
class EntityWriteRequest(BaseModel):
    """Request body for PATCH /api/v1/entity/{entity_type}/{gid}.

    Attributes:
        fields: Dict mapping field names to values. Accepts both
            Python descriptor names (weekly_ad_spend) and Asana
            display names ("Weekly Ad Spend"). Core fields (name,
            assignee, due_on, completed, notes) are also accepted.
        list_mode: How to handle list-type fields.
            "replace" (default): Replace entire field value.
            "append": Append to existing values (multi_enum, text lists).
    """
    fields: dict[str, Any]
    list_mode: Literal["replace", "append"] = "replace"

    @model_validator(mode="after")
    def validate_non_empty(self) -> EntityWriteRequest:
        if not self.fields:
            raise ValueError("fields must be non-empty")
        return self
```

### Response Model

```python
class FieldWriteResult(BaseModel):
    """Per-field write result."""
    name: str
    status: Literal["written", "skipped", "error"]
    error: str | None = None
    suggestions: list[str] | None = None


class EntityWriteResponse(BaseModel):
    """Response for entity write endpoint."""
    gid: str
    entity_type: str
    fields_written: int
    fields_skipped: int
    field_results: list[FieldWriteResult]
    updated_fields: dict[str, Any] | None = None
```

### Example Request

```
PATCH /api/v1/entity/offer/1234567890?include_updated=false
Authorization: Bearer <S2S JWT>
Content-Type: application/json

{
    "fields": {
        "name": "Updated Offer Name",
        "weekly_ad_spend": 500,
        "Status": "Active",
        "Platforms": ["Facebook", "Google"],
        "asset_id": "asset-12345"
    },
    "list_mode": "replace"
}
```

### Example Response (200)

```json
{
    "gid": "1234567890",
    "entity_type": "offer",
    "fields_written": 5,
    "fields_skipped": 0,
    "field_results": [
        {"name": "name", "status": "written"},
        {"name": "weekly_ad_spend", "status": "written"},
        {"name": "Status", "status": "written"},
        {"name": "Platforms", "status": "written"},
        {"name": "asset_id", "status": "written"}
    ],
    "updated_fields": null
}
```

### Error Responses

| Code | Error Code | Condition |
|------|-----------|-----------|
| 401 | `MISSING_AUTH` | No Authorization header |
| 401 | `SERVICE_TOKEN_REQUIRED` | PAT token provided (S2S only) |
| 404 | `UNKNOWN_ENTITY_TYPE` | entity_type not writable |
| 404 | `TASK_NOT_FOUND` | GID does not exist in Asana |
| 404 | `ENTITY_TYPE_MISMATCH` | Task exists but wrong project |
| 422 | `EMPTY_REQUEST` | Fields dict is empty |
| 422 | `NO_VALID_FIELDS` | All fields failed resolution |
| 422 | `FIELD_TYPE_ERROR` | Type mismatch (in field_results, request still proceeds) |
| 429 | `RATE_LIMITED` | Service or Asana rate limit |
| 502 | `ASANA_UPSTREAM_ERROR` | Asana 5xx or connection error |
| 503 | `DISCOVERY_INCOMPLETE` | Startup discovery not finished |
| 504 | `ASANA_TIMEOUT` | Asana API call timed out |

### Partial Success Semantics

The endpoint uses **fail-forward** semantics for field resolution:

1. Each field is resolved independently.
2. Fields that fail resolution (unknown name, type mismatch, enum not found) are marked `skipped` or `error` in `field_results`.
3. All successfully resolved fields are written in a single API call.
4. The response status is 200 as long as at least one field was written.
5. If ALL fields fail resolution (zero writable), the response is 422 `NO_VALID_FIELDS`.

This matches the existing `FieldSeeder.write_fields_async()` pattern where `fields_written` and `fields_skipped` coexist in `WriteResult`.

---

## 8. Integration Points

### 8.1 EntityWriteRegistry and EntityRegistry

`EntityWriteRegistry` is constructed with an `EntityRegistry` reference at startup. It calls `entity_registry.all_descriptors()` to iterate all entity types and `desc.get_model_class()` to lazily import each model. It reads `primary_project_gid` from the descriptor. The existing `EntityRegistry` is unmodified.

The `EntityWriteRegistry` is stored on `app.state.entity_write_registry` during the lifespan startup, after `EntityProjectRegistry` is populated (so project GIDs are available).

### 8.2 FieldResolver and FieldSeeder

After `FieldResolver` is extracted, `FieldSeeder.write_fields_async()` will be refactored to use it:

```python
# Before (in FieldSeeder.write_fields_async):
#   manual field matching loop, enum resolution, accessor.set()
# After:
resolver = FieldResolver(
    custom_fields_data=custom_fields_list,
    descriptor_index={},  # FieldSeeder uses display names only
    core_fields=frozenset(),  # FieldSeeder doesn't write core fields
)
resolved = resolver.resolve_fields(mapped_fields)
for rf in resolved:
    if rf.status == "resolved":
        accessor.set(rf.matched_name, rf.value)
        fields_to_write.append(rf.matched_name)
    else:
        fields_skipped.append(rf.input_name)
```

This refactoring is done in the same sprint. FieldSeeder retains its cascade/carry-through/compute logic; only the inner resolution loop is replaced.

### 8.3 MutationEvent and Cache Invalidation

After a successful `TasksClient.update_async()` call, the write service emits a `MutationEvent`:

```python
from autom8_asana.cache.models.mutation_event import (
    EntityKind, MutationEvent, MutationType,
)

event = MutationEvent(
    entity_kind=EntityKind.TASK,
    entity_gid=gid,
    mutation_type=MutationType.UPDATE,
    project_gids=[write_info.project_gid],
)
```

The route handler passes this to `MutationInvalidator.invalidate_async(event)` wrapped in `asyncio.create_task()` for fire-and-forget execution. If the `MutationInvalidator` is not available on `app.state` (e.g., no cache configured), invalidation is silently skipped.

The `MutationInvalidator` already handles all cache tiers:
- Entity-level cache eviction (task GID key)
- Subtask list eviction (parent GID key)
- Detection cache eviction
- DataFrame cache invalidation (project-level)

No changes to `MutationInvalidator` are needed.

### 8.4 EntityService (unchanged)

The write route does NOT use `EntityService.validate_entity_type()` because:
1. `EntityService` validates "queryable" entities (those with schemas in SchemaRegistry). Writability is a different concept -- an entity can be writable without having a DataFrame schema.
2. `EntityService` acquires a bot PAT through `_acquire_bot_pat()`. The write route acquires its own PAT using the same `get_bot_pat()` call, matching the resolver route's pattern.

`EntityService` remains available for other consumers that need query-context validation.

### 8.5 CORS Middleware Update

The existing CORS middleware in `api/main.py` already allows `PATCH` implicitly because `allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]`. We add `"PATCH"` to this list explicitly for correctness.

---

## 9. Error Handling

### Asana API Error Mapping

The write service catches Asana API errors from `TasksClient` and maps them to HTTP responses:

| Asana Error | HTTP Response | Error Code |
|-------------|--------------|------------|
| 404 Not Found | 404 | `TASK_NOT_FOUND` |
| 400 Bad Request | 422 | `ASANA_VALIDATION_ERROR` |
| 429 Rate Limited | 429 | `RATE_LIMITED` (with Retry-After) |
| 5xx Server Error | 502 | `ASANA_UPSTREAM_ERROR` |
| Connection/Timeout | 504 | `ASANA_TIMEOUT` |

These are caught via the existing `AsanaError` hierarchy:
```python
from autom8_asana.exceptions import (
    AsanaError,
    RateLimitError,
    NotFoundError,
)
```

### Service-Layer Exceptions

New exceptions added to `services/errors.py`:

```python
class TaskNotFoundError(EntityNotFoundError):
    """Task GID does not exist in Asana."""
    def __init__(self, gid: str) -> None:
        self.gid = gid
        super().__init__(f"Task not found: {gid}")

    @property
    def error_code(self) -> str:
        return "TASK_NOT_FOUND"


class EntityTypeMismatchError(EntityNotFoundError):
    """Task exists but belongs to wrong project."""
    def __init__(
        self, gid: str, expected_project: str, actual_projects: list[str]
    ) -> None:
        self.gid = gid
        self.expected_project = expected_project
        self.actual_projects = actual_projects
        super().__init__(
            f"Task {gid} does not belong to entity type's project "
            f"(expected {expected_project}, found {actual_projects})"
        )

    @property
    def error_code(self) -> str:
        return "ENTITY_TYPE_MISMATCH"

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.error_code,
            "message": self.message,
            "expected_project": self.expected_project,
            "actual_projects": self.actual_projects,
        }


class NoValidFieldsError(EntityValidationError):
    """All fields failed resolution -- nothing to write."""
    @property
    def error_code(self) -> str:
        return "NO_VALID_FIELDS"

    @property
    def status_hint(self) -> int:
        return 422
```

These follow the existing service error pattern where services raise domain exceptions and route handlers map them to HTTP responses via `get_status_for_error()`.

---

## 10. Observability

### Structured Log Events

| Log Event | Level | When | Fields |
|-----------|-------|------|--------|
| `entity_write_request` | INFO | Request received | request_id, entity_type, gid, caller_service, field_count, list_mode |
| `entity_write_field_resolution` | DEBUG | Per field resolved | field_name, resolved_gid, status, is_core |
| `entity_write_api_call` | INFO | Before Asana update | task_gid, core_fields_count, custom_fields_count |
| `entity_write_cache_invalidation` | DEBUG | MutationEvent emitted | task_gid, project_gid |
| `entity_write_complete` | INFO | Request complete | request_id, duration_ms, fields_written, fields_skipped, caller_service |
| `entity_write_error` | ERROR | On failure | request_id, error_code, error_message |

All log events use `autom8y_log.get_logger(__name__)` and structured key-value pairs, matching the existing codebase pattern.

---

## 11. Performance

### Asana API Call Budget

| Operation | API Calls | Latency (P50) |
|-----------|----------|---------------|
| Task fetch (with custom_fields) | 1 | ~200ms |
| Task update (core + custom) | 1 | ~300ms |
| Optional re-fetch | 0-1 | ~200ms |
| **Total without re-fetch** | **2** | **~500ms** |
| **Total with re-fetch** | **3** | **~700ms** |

This is within the PRD's NFR target: P50 < 800ms for a 5-field write.

### Rate Limit Impact

Each write request consumes 2 Asana API calls (fetch + update), or 3 with `include_updated=true`. With the proposed endpoint-level limit of 100 writes/minute, the maximum Asana API impact is 300 calls/minute -- well within the 1500/minute shared budget.

### No N+1 Queries

All fields (core + custom) are written in a single `PUT /tasks/{gid}` call. There is no per-field API call. Enum options are included in the task fetch response, so no separate lookup is needed.

---

## 12. Security

### Authentication

- S2S JWT only, enforced by `require_service_claims` FastAPI dependency (same as resolver).
- PAT tokens are rejected with 401 `SERVICE_TOKEN_REQUIRED`.
- Caller service name is extracted from JWT claims and logged in every write event.

### Authorization

- v1 has no per-entity authorization. All authenticated S2S callers can write all writable entity types.
- The `caller_service` field in structured logs provides an audit trail for all writes.

### Input Validation

- Entity type validated against `EntityWriteRegistry` (only known writable types accepted).
- Task GID validated via `validate_gid()` (existing pattern from TasksClient).
- Field values are type-checked against `resource_subtype` before Asana API call.
- Enum values are validated against known option GIDs.
- No raw user input is passed to shell commands or SQL queries (not applicable).

---

## 13. File Layout

```
src/autom8_asana/
    resolution/
        __init__.py                    # (existing package)
        write_registry.py              # NEW: EntityWriteRegistry
        field_resolver.py              # NEW: FieldResolver
    services/
        field_write_service.py         # NEW: FieldWriteService
        errors.py                      # MODIFIED: +TaskNotFoundError, +EntityTypeMismatchError, +NoValidFieldsError
    api/
        routes/
            entity_write.py            # NEW: PATCH route + Pydantic models
            __init__.py                # MODIFIED: +entity_write_router
        main.py                        # MODIFIED: +entity_write_router, +PATCH in CORS
    automation/
        seeding.py                     # MODIFIED: refactor to use FieldResolver

tests/unit/
    resolution/
        test_write_registry.py         # NEW
        test_field_resolver.py         # NEW
    services/
        test_field_write_service.py    # NEW
    api/routes/
        test_entity_write.py           # NEW
```

---

## 14. Architecture Decision Records

### ADR-EW-001: PATCH over PUT

**Status**: Accepted

**Context**: The PRD originally specified `PUT /api/v1/entity/{entity_type}/{gid}`. PUT semantics require a complete resource representation -- unspecified fields would be set to null/defaults. The entity write endpoint only modifies specified fields; unspecified fields remain unchanged.

**Options Evaluated**:

| Option | Semantics | Fit |
|--------|-----------|-----|
| PUT | Full replacement; omitted fields cleared | POOR -- forces callers to send all fields |
| PATCH | Partial update; only specified fields change | GOOD -- matches actual behavior |
| POST | General action | POOR -- not semantically an update |

**Decision**: Use `PATCH`. The endpoint performs partial updates: only the fields in the request body are modified. Unspecified fields are untouched. This is the textbook use case for PATCH.

**Consequences**:
- Callers can send only the fields they want to change.
- No risk of accidentally clearing fields by omitting them.
- Standard HTTP semantics -- any HTTP client understands PATCH.
- Idempotency is maintained (same PATCH with same values produces same state).

---

### ADR-EW-002: Separate EntityWriteRegistry

**Status**: Accepted

**Context**: The PRD's Amendment G calls for a "dynamic EntityRegistry" that replaces `EntityProjectRegistry`. After analysis, we determined that the existing `EntityRegistry` and `EntityProjectRegistry` serve different purposes:
- `EntityRegistry`: Static metadata (project GIDs, categories, cache behavior, join keys). Built at module load time from `ENTITY_DESCRIPTORS`.
- `EntityProjectRegistry`: Dynamic workspace-to-project discovery at runtime. Populated during startup lifespan.

Neither registry knows about `CustomFieldDescriptor` properties or which entity types are "writable."

**Options Evaluated**:

| Option | Impact | Risk |
|--------|--------|------|
| A: Add write metadata to `EntityDescriptor` | Modifies frozen dataclass used by 20+ consumers | HIGH -- violates SRP, requires re-validation |
| B: Replace `EntityProjectRegistry` with new registry | Breaks existing resolver/query endpoints | HIGH -- massive blast radius |
| C: Create `EntityWriteRegistry` as purpose-built overlay | New file, no existing code changes | LOW -- additive only |

**Decision**: Option C. `EntityWriteRegistry` is a new, purpose-built registry that:
- Reads from `EntityRegistry` for project GIDs (no duplication)
- Adds write-specific indexes (descriptor_index, core_fields)
- Auto-discovers writable types by introspecting model classes
- Is stored on `app.state` alongside existing registries

**Consequences**:
- Zero changes to `EntityRegistry` or `EntityProjectRegistry`.
- Adding a new writable entity type requires only adding `CustomFieldDescriptor` properties to its model class -- the registry discovers it automatically.
- The registry is startup-only (built once, read-many). No runtime overhead.

---

### ADR-EW-003: Shared FieldResolver Extraction

**Status**: Accepted

**Context**: `FieldSeeder.write_fields_async()` (automation/seeding.py lines 447-568) contains exactly the resolution logic needed for the write endpoint: fetch task with custom_fields, case-insensitive field matching, enum name-to-GID resolution, and batched update. Duplicating this logic would create a maintenance burden.

**Options Evaluated**:

| Option | Duplication | Coupling |
|--------|------------|----------|
| A: Copy resolution logic into FieldWriteService | YES -- ~120 lines duplicated | LOW |
| B: Make FieldWriteService call FieldSeeder | NO | HIGH -- FieldSeeder has cascade/seeding concerns |
| C: Extract shared FieldResolver utility | NO | LOW -- both FieldSeeder and FieldWriteService depend on utility |

**Decision**: Option C. Extract `FieldResolver` as a stateless utility class in `resolution/field_resolver.py`. Both `FieldSeeder` and `FieldWriteService` construct a `FieldResolver` per-request with the task's custom field data.

**Consequences**:
- Single source of truth for field resolution logic.
- `FieldSeeder.write_fields_async()` is refactored but behavior is unchanged (verified by existing tests).
- `FieldResolver` is independently testable with unit tests.
- Future field types (formula, rollup) only need changes in one place.

---

### ADR-EW-004: TextListField Append Semantics

**Status**: Accepted

**Context**: The PRD's Amendment F introduces `list_mode: "append"` for list-type fields. For `multi_enum` fields, append means adding new options to the existing selection. For text fields used as delimited lists (like `asset_id`), append means parsing the existing text, adding new values, deduplicating, and re-joining.

The codebase has no `TextListField` descriptor type -- these are plain `TextField` instances. The "list" behavior is a semantic convention, not a type distinction.

**Options Evaluated**:

| Option | Approach | Complexity |
|--------|----------|-----------|
| A: Introduce a TextListField descriptor type | New descriptor subclass, field discovery | MEDIUM -- requires model changes |
| B: Handle text append generically in FieldResolver | All text fields eligible for append when list_mode="append" | LOW -- no model changes |
| C: Require callers to do their own read-modify-write | No server support | LOW -- pushes complexity to callers |

**Decision**: Option B. When `list_mode: "append"` is set and a text-type field receives a string or list value, `FieldResolver` reads the current `text_value`, splits on comma, appends, deduplicates, and re-joins. This is transparent to callers -- they send the new value, the server handles merge.

**Why not Option A?** Adding a `TextListField` descriptor type would require modifying entity models (e.g., `Offer.asset_id = TextListField()` instead of `TextField()`). This is a model-layer change that affects field reading, writing, and the Fields class generation. It is disproportionate to the v1 need. If text list fields become more common, Option A can be revisited in v2.

**Consequences**:
- Delimiter is comma (`,`), matching the existing production convention.
- Deduplication is case-sensitive (exact string match).
- If a caller sends `list_mode: "append"` for a non-list text field, the behavior is still correct -- it appends to the existing text, which is harmless.
- Multi-enum append is straightforward: merge existing GID list with resolved new GIDs.
- No model-layer changes needed in v1.

---

## 15. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Asana API rate limiting under write load | MEDIUM | Write requests return 429 | Endpoint-level rate limit (100/min); Retry-After header forwarded; callers expected to implement backoff |
| Descriptor index stale after model changes | LOW | New fields not discoverable via descriptor name | `EntityWriteRegistry` is rebuilt on every app restart; display name fallback always works |
| Concurrent writes to same entity | MEDIUM | Last-write-wins for overlapping fields | By design (Asana custom field update is field-level atomic); documented in edge cases |
| TextListField delimiter ambiguity | LOW | Values containing commas are split incorrectly | Document comma delimiter; v2 could support configurable delimiters |
| Cache invalidation failure | LOW | Stale reads after write | Fire-and-forget with error logging; cached data has TTL (naturally expires) |
| Bot PAT rotation during write | LOW | 401 from Asana mid-request | Existing retry logic in `AsanaHttp` handles token refresh |

---

## 16. Test Strategy

### 16.1 EntityWriteRegistry Tests

**File**: `tests/unit/resolution/test_write_registry.py`

| Test | Validates |
|------|-----------|
| `test_discovers_offer_descriptors` | Offer with 39+ descriptors is discovered; descriptor_index has `weekly_ad_spend` -> `"Weekly Ad Spend"` |
| `test_discovers_business_descriptors` | Business with inherited mixin descriptors is discovered |
| `test_skips_holder_types` | Holder types (OfferHolder, etc.) are NOT registered as writable |
| `test_skips_entities_without_project_gid` | Process (no primary_project_gid) is excluded |
| `test_writable_types_sorted` | `writable_types()` returns sorted list of all writable entity names |
| `test_is_writable_true_for_offer` | `is_writable("offer")` returns True |
| `test_is_writable_false_for_holder` | `is_writable("offer_holder")` returns False |
| `test_descriptor_index_includes_mixin_fields` | Inherited descriptors (vertical, rep from mixins) appear in descriptor_index |
| `test_core_fields_set` | `CORE_FIELD_NAMES` contains exactly {name, assignee, due_on, completed, notes} |

### 16.2 FieldResolver Tests

**File**: `tests/unit/resolution/test_field_resolver.py`

| Test | Validates |
|------|-----------|
| `test_resolve_core_field_name` | `"name"` resolves as core field with is_core=True |
| `test_resolve_descriptor_name` | `"weekly_ad_spend"` resolves to GID via descriptor_index |
| `test_resolve_display_name` | `"Weekly Ad Spend"` resolves via display_index |
| `test_resolve_display_name_case_insensitive` | `"weekly ad spend"` resolves via case-insensitive display scan |
| `test_resolve_unknown_field_fuzzy` | Unknown field returns status="skipped" with fuzzy suggestions |
| `test_resolve_enum_by_name` | Enum string "Active" resolves to option GID |
| `test_resolve_enum_by_gid_passthrough` | Numeric string GID passes through for enum fields |
| `test_resolve_enum_unknown_value` | Unknown enum value returns status="skipped" with available options |
| `test_resolve_multi_enum_replace` | Multi-enum list resolves to list of GIDs |
| `test_resolve_multi_enum_append` | Append mode merges with existing selections |
| `test_resolve_text_append_new` | Text append on empty field sets new value |
| `test_resolve_text_append_dedup` | Text append deduplicates existing values |
| `test_resolve_text_append_list_input` | Text append accepts list of strings |
| `test_resolve_date_wrapping` | Date string is wrapped in `{"date": "YYYY-MM-DD"}` |
| `test_resolve_null_clears_field` | None value resolves as None (clear field) |
| `test_type_validation_number_rejects_string` | Number field with string value returns type error |
| `test_type_validation_text_rejects_number` | Text field with number value returns type error |
| `test_mixed_core_and_custom` | Request with both core and custom fields resolves correctly |

### 16.3 FieldWriteService Tests

**File**: `tests/unit/services/test_field_write_service.py`

| Test | Validates |
|------|-----------|
| `test_write_success_single_field` | Single field write returns fields_written=1 |
| `test_write_partial_success` | 3 valid + 1 invalid returns fields_written=3, fields_skipped=1 |
| `test_write_all_invalid_raises` | All fields invalid raises NoValidFieldsError |
| `test_task_not_found_raises` | Asana 404 raises TaskNotFoundError |
| `test_entity_type_mismatch_raises` | Task in wrong project raises EntityTypeMismatchError |
| `test_core_and_custom_single_api_call` | Verifies one update_async call with both core kwargs and custom_fields dict |
| `test_mutation_event_emitted` | MutationEvent is created after successful write |
| `test_include_updated_refetch` | include_updated=True triggers a re-fetch and returns values |
| `test_asana_rate_limit_maps_to_429` | Asana RateLimitError maps to 429 response |

### 16.4 Route Integration Tests

**File**: `tests/unit/api/routes/test_entity_write.py`

| Test | Validates |
|------|-----------|
| `test_patch_success_200` | Full happy path: PATCH -> 200 with field_results |
| `test_missing_auth_401` | No Authorization header -> 401 |
| `test_pat_token_rejected_401` | PAT token -> 401 SERVICE_TOKEN_REQUIRED |
| `test_unknown_entity_type_404` | Unknown type -> 404 with available types |
| `test_task_not_found_404` | Invalid GID -> 404 TASK_NOT_FOUND |
| `test_entity_type_mismatch_404` | Wrong project -> 404 ENTITY_TYPE_MISMATCH |
| `test_empty_fields_422` | Empty fields -> 422 EMPTY_REQUEST |
| `test_no_valid_fields_422` | All fields invalid -> 422 NO_VALID_FIELDS |
| `test_partial_success_200` | Mix of valid/invalid -> 200 with skipped results |
| `test_list_mode_append` | list_mode="append" -> append behavior verified |

### 16.5 FieldSeeder Refactoring Tests

No new tests needed. Existing `tests/unit/automation/test_field_seeder.py` tests verify that the refactored `write_fields_async()` behaves identically. The refactoring replaces the inner resolution loop with `FieldResolver` calls but preserves all inputs, outputs, and error handling.

---

## 17. Implementation Order

The components should be implemented in this order due to dependencies:

1. **FieldResolver** (no dependencies on new code)
2. **EntityWriteRegistry** (depends on existing EntityRegistry only)
3. **Service errors** (TaskNotFoundError, etc.)
4. **FieldWriteService** (depends on FieldResolver, EntityWriteRegistry)
5. **Entity write route** (depends on FieldWriteService)
6. **App registration** (routes/__init__.py, main.py)
7. **FieldSeeder refactoring** (depends on FieldResolver being stable)

Each step is independently testable. Steps 1-2 can be built and tested in isolation before wiring up the HTTP layer.

---

## 18. Out of Scope (Deferred per PRD Amendments)

| Feature | Deferral | Reference |
|---------|----------|-----------|
| Tags (add/remove by name) | v1.1 | Amendment D |
| Automations (post-write trigger) | Entirely deferred | Amendment E |
| Feature flag | Not needed (S2S only) | Amendment K |
| Bulk write (multiple entities) | v2 | PRD Out of Scope |
| Per-entity authorization | v2 | PRD Out of Scope |
| Section moves | Separate endpoint | PRD Out of Scope |

---

## 19. Handoff Checklist

- [x] TDD covers all PRD requirements (with amendments applied)
- [x] Component boundaries and responsibilities are clear
- [x] Data model defined (WritableEntityInfo, ResolvedField, WriteFieldsResult)
- [x] API contract specified (PATCH endpoint, request/response models)
- [x] ADRs document all significant decisions (4 ADRs)
- [x] Risks identified with mitigations (6 risks)
- [x] Integration points documented (5 integration points)
- [x] Test strategy defined per component
- [x] Implementation order specified
- [x] File layout defined

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-entity-write-api.md` | Yes (Read-verified 2026-02-11) |
| Source PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-entity-write-api.md` | Read-verified 2026-02-11 |
