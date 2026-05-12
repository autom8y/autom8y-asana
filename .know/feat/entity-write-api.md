---
domain: feat/entity-write-api
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/api/routes/entity_write.py"
  - "./src/autom8_asana/services/field_write_service.py"
  - "./src/autom8_asana/resolution/field_resolver.py"
  - "./src/autom8_asana/resolution/write_registry.py"
  - "./src/autom8_asana/services/errors.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.95
format_version: "1.0"
---

# Entity Write API (Field Coercion and Partial Success)

## Purpose and Design Rationale

Provides a service-to-service API for writing business-domain fields to Asana tasks using human-readable field names rather than raw Asana custom field GIDs. The feature was built to allow downstream fleet services (autom8_data) to update Asana entity state without coupling to Asana internals.

**Core design decisions:**

- **ADR-EW-002**: `EntityWriteRegistry` is an additive overlay on `EntityRegistry` — does not modify the read-path registry, preserving read/write separation.
- **ADR-EW-003**: `FieldResolver` was extracted from `FieldSeeder` (`automation/seeding.py`) to enable reuse across the write API and the seeding pipeline. Both consumers now call the same resolution logic.
- **D-EW-001**: Explicit per-task cache invalidation (`_cache_invalidate`) before re-fetch when `include_updated=True`. Without this, `_fetch_task` from step [2] would still be in the task-level cache and the refetch would return stale pre-write values.
- **D-EW-002**: Short numeric strings (`len < 13`) are treated as option names, not GID passthroughs. Asana GIDs are always ≥13 digits. This prevents numeric enum option names (e.g., "1", "2") from being misinterpreted as GID values.

**Authentication rationale**: S2S JWT only (`require_service_claims`). The bot PAT is obtained from the injected `AuthContextDep` at the call site, not hardcoded. PAT tokens return `401 SERVICE_TOKEN_REQUIRED`. The route is hidden from OpenAPI schema (`include_in_schema=False`).

**Single Asana API call invariant**: All resolved fields — core and custom — are batched into a single `TasksClient.update_async()` call. This minimizes rate limit exposure and ensures atomicity at the Asana API boundary.

**Tradeoffs accepted**: No optimistic locking (last-write-wins). No batching across GIDs (one request per task). Text append uses comma delimiter with no escaping — values containing commas will split incorrectly on round-trip read.

## Conceptual Model

### Entity Writability

An entity type is writable if and only if it satisfies both:
1. Its model class has at least one `CustomFieldDescriptor` property.
2. Its `EntityDescriptor` has a `primary_project_gid`.

Holder entities are unconditionally excluded. The `EntityWriteRegistry` is built once at startup (lifespan step 11) and is immutable thereafter (thread-safe read-many).

### Resolution Priority Cascade

For each field name in the request, `FieldResolver` applies a 4-step cascade:

1. **Core field** (exact key match): `name`, `assignee`, `due_on`, `completed`, `notes` → top-level Asana task keys.
2. **Descriptor index** (O(1) snake_case lookup): e.g., `weekly_ad_spend` → `"Weekly Ad Spend"` via `WritableEntityInfo.descriptor_index`.
3. **Display name scan** (case-insensitive): normalized display name lookup against the task's actual custom fields fetched from Asana.
4. **Not found**: produces a `skipped` result with fuzzy suggestions via `difflib.get_close_matches` (cutoff 0.6, max 3 suggestions).

### Type Coercion Table

| Field Type | Value Rules | Asana API Payload |
|------------|-------------|-------------------|
| `text` | `str` or `list[str]` (append mode) | String passthrough |
| `number` | `int` or `float` | Numeric passthrough |
| `enum` | Case-insensitive name or 13+ digit GID | `{"gid": "<option_gid>"}` (Asana accepts raw GID string) |
| `multi_enum` | `list` of names/GIDs, or single value | `[{"gid": "..."}, ...]` |
| `date` | `str` (YYYY-MM-DD) | `{"date": "YYYY-MM-DD"}` |
| `people` | Passthrough | Raw value |
| `null` | Clears any field type | `None` passthrough |

Enum GID passthrough: a string value ≥13 digits is treated as a GID passthrough only if found in the field's `enum_options`. Shorter numeric strings always go through name-based lookup.

### Partial Success Model

Per-field granularity: resolution errors (field not found, type mismatch, enum value not found) produce `skipped` or `error` status for that field but do not block other fields. The request completes successfully with the writable fields applied.

Request-level failures: `NoValidFieldsError` (all fields failed → 422). Task-level failures: `TaskNotFoundError` (404), `EntityTypeMismatchError` (404 with project details).

**Multi-enum partial resolution**: If some values in a `multi_enum` input resolve and others do not, the resolved subset is written and unresolved items are logged as `multi_enum_option_mismatch` warnings. Only if ALL items fail does the field-level result become `skipped`.

### List Mode

| Mode | Behavior |
|------|----------|
| `replace` (default) | Overwrites entire field value |
| `append` | `multi_enum`: merges with existing selections (dedup); `text`: comma-splits existing, appends new items (dedup, order-preserving) |

### Cache Invalidation — Two Distinct Paths

1. **Per-task invalidation** (`_cache_invalidate(gid, [EntryType.TASK])`): called before `_refetch_updated()` to ensure the re-fetch reads fresh Asana data. Only fires when `include_updated=True`.
2. **DataFrame cache invalidation** (`MutationInvalidator`): fire-and-forget `asyncio.create_task` that propagates the write event to downstream DataFrame caches. Always fires after a successful write. Errors from this path are suppressed (logged as warnings) and do not affect the HTTP response.

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_asana/api/routes/entity_write.py` | Route: `PATCH /api/v1/entity/{entity_type}/{gid}`, S2S JWT auth, request/response models, error-to-HTTP mapping |
| `src/autom8_asana/services/field_write_service.py` | `FieldWriteService`: stateless 9-step pipeline orchestrator |
| `src/autom8_asana/resolution/field_resolver.py` | `FieldResolver`: per-request resolver; 4-step name cascade + type coercion |
| `src/autom8_asana/resolution/write_registry.py` | `EntityWriteRegistry`: startup-built auto-discovery registry from `CustomFieldDescriptor` introspection |
| `src/autom8_asana/services/errors.py` | `TaskNotFoundError`, `EntityTypeMismatchError`, `NoValidFieldsError` + full service error hierarchy |
| `src/autom8_asana/api/dependencies.py` | `EntityWriteRegistryDep` — injects `app.state.entity_write_registry` into the route via FastAPI DI |
| `src/autom8_asana/api/lifespan.py:184-200` | Lifespan step 11: constructs `EntityWriteRegistry(entity_registry)` → `app.state.entity_write_registry` |
| `src/autom8_asana/automation/seeding.py:393-396` | Reuse of `FieldResolver` in `FieldSeeder` (ADR-EW-003 consumer) |

### FieldWriteService 9-Step Pipeline

```
[1] Registry lookup (EntityWriteRegistry.get(entity_type))
[2] Fetch task (custom_fields + enum_options + memberships + core fields)
[3] Verify project membership (EntityTypeMismatchError on failure)
[4] Construct FieldResolver (custom_fields_data + descriptor_index + CORE_FIELD_NAMES)
[5] Resolve all fields → list[ResolvedField]
[6] Build payload: separate core_payload (top-level keys) from custom_payload (GID→value dict)
[7] Single TasksClient.update_async(gid, raw=True, **core_payload, custom_fields=custom_payload)
[8] Optional: _cache_invalidate(gid) → _refetch_updated() if include_updated=True
[9] Fire-and-forget MutationEvent via asyncio.create_task(_invalidate_cache(...))
```

### EntityWriteRegistry Construction

Built at startup via `EntityWriteRegistry(entity_registry)`. Iterates all `EntityDescriptor`s from `EntityRegistry`:
- Skips `category.value == "holder"`.
- Resolves model class via `desc.get_model_class()`.
- Scans `dir(model_class)` for `CustomFieldDescriptor` instances; reads `attr.public_name` → `attr.field_name` pairs into `descriptor_index`.
- Skips entities with no descriptors or no `primary_project_gid`.
- Abbreviation-aware: `public_name` derivation handles `mrr` → `"MRR"`, `company_id` → `"Company ID"`.

Provides: `get(entity_type)`, `is_writable(entity_type)`, `writable_types()`.

### Route Pydantic Models

- `EntityWriteRequest`: `fields: dict[str, Any]`, `list_mode: Literal["replace", "append"]`, `extra="forbid"`, validator rejects empty `fields`.
- `FieldWriteResult` (response): `name`, `status: Literal["written", "skipped", "error"]`, `error`, `suggestions`.
- `EntityWriteResponse`: `gid`, `entity_type`, `fields_written`, `fields_skipped`, `field_results`, `updated_fields` (optional).
- Status mapping in route: internal `"resolved"` → exposed `"written"`.

### OpenAPI Fleet Annotations

Route decorated with `openapi_extra`:
```python
"x-fleet-side-effects": [{"type": "asana_api", "target": "entity_task"}]
"x-fleet-idempotency": {"idempotent": False, "key_source": None}
"x-fleet-rate-limit": {"tier": "external"}
```
Route is hidden from schema (`include_in_schema=False`).

### Test Coverage

| File | Scope |
|------|-------|
| `tests/unit/api/routes/test_entity_write.py` (509 lines) | Route layer: 12 test cases covering success, 401/404/422 flows, partial success, list_mode append, unknown fields |
| `tests/unit/services/test_field_write_service.py` (418 lines) | Service pipeline unit tests |
| `tests/unit/resolution/test_field_resolver.py` (496 lines) | Resolver unit tests: cascade, enum/multi-enum, type validation, text append, fuzzy suggestions |
| `tests/unit/resolution/test_write_registry.py` (147 lines) | Registry discovery unit tests |
| `tests/integration/test_entity_write_smoke.py` (1146 lines) | Live Asana adversarial smoke tests: registry discovery, field name resolution, live writes with restore, enum/multi-enum, error paths, partial success, D-EW-001/D-EW-002/D-EW-003 defect regression tests |

## Boundaries and Failure Modes

### Scope Boundaries

- **Single GID per request.** No batch-write endpoint exists.
- **Write-only.** No create, delete, or read operations.
- **No optimistic locking.** Last-write-wins. Concurrent writes to the same field from different callers will silently overwrite.
- **Holder entities excluded.** `EntityWriteRegistry` skips them at construction; `is_writable()` returns false.
- **Text append uses comma delimiter.** No escaping. Field values containing commas will split incorrectly on round-trip read. Documented limitation.
- **Multi-enum partial resolution is silent.** Partially resolved multi-enum values are written without a request-level warning; only unresolved items are logged.
- **`include_updated` reflects only written fields.** The `updated_fields` dict maps only the resolved+written fields back to their current Asana values. Fields that were skipped or errored are not included.

### Error Paths

| Failure | HTTP | Error Code | Recovery |
|---------|------|------------|----------|
| Entity type unknown or non-writable | 404 | `UNKNOWN_ENTITY_TYPE` | Use `writable_types()` list from response |
| Registry not initialized | 503 | `DISCOVERY_INCOMPLETE` | Retry after service fully starts |
| Task not found (Asana 404) | 404 | `TASK_NOT_FOUND` | Verify GID |
| Task in wrong project | 404 | `ENTITY_TYPE_MISMATCH` | Match `entity_type` to task's actual project; response includes `expected_project` and `actual_projects` |
| All fields fail resolution | 422 | `NO_VALID_FIELDS` | Inspect `field_results` for per-field errors and suggestions |
| Rate limit | 429 | `RATE_LIMITED` | Use `Retry-After` header |
| Asana timeout | 504 | `ASANA_TIMEOUT` | Retry with backoff |
| Asana server error | 502 | `ASANA_UPSTREAM_ERROR` | Retry with backoff |
| Cache invalidation failure | (none) | — | Logged warning; DataFrame TTL expires naturally |
| Empty `fields` dict | 422 | Pydantic validation | Provide at least one field |
| PAT token used | 401 | `SERVICE_TOKEN_REQUIRED` | Use S2S JWT |

### Interaction Points

- **`EntityRegistry`** (read only): `EntityWriteRegistry` iterates it at startup. The write registry does not modify it (ADR-EW-002).
- **`AsanaClient.tasks`**: The only Asana API surface touched. Both `get_async` (fetch + optional refetch) and `update_async` (write) are called. `_cache_invalidate` is called directly on the tasks client for per-task cache invalidation (D-EW-001).
- **`MutationInvalidator`**: Fire-and-forget DataFramecache invalidation. Injected from `app.state` via `MutationInvalidatorDep`. Errors are swallowed after logging.
- **`FieldSeeder` (automation/seeding.py)**: Imports and instantiates `FieldResolver` directly (ADR-EW-003 reuse). Changes to `FieldResolver` API affect both consumers.
- **`AuthContextDep`**: Provides the bot PAT for `AsanaClient` construction. The entity write route constructs an `AsanaClient` per request using `auth_context.asana_pat`. This is distinct from the `ServiceClaims` JWT used for caller identity.

### Configuration Boundaries

- `ASANA_PAT` / `auth_context.asana_pat` — bot PAT required for Asana API access.
- `app.state.entity_write_registry` — must be populated at startup (step 11 of 14 in lifespan). Returns 503 if absent.
- `app.state.mutation_invalidator` — optional; cache invalidation is skipped (not errored) if absent.
- `include_updated` query param — triggers an extra Asana fetch and per-task cache invalidation. Adds one Asana API call to the request cost.

### Known Knowledge Gaps (Carried from Previous Observation)

1. `CustomFieldDescriptor` internals (`public_name`/`field_name` attribute derivation logic) not read from `models/business/descriptors.py`.
2. Disabled enum option write behavior: `_available_enum_options` filters by `enabled=True` for suggestions but `_resolve_single_option` does not filter by enabled — a disabled option GID can still be written if its name matches.
3. `BOT_PAT_UNAVAILABLE` error code origin path not traced (may be raised within `auth_context.asana_pat` access or `AsanaClient` construction).

```metadata
confidence: 0.95
primary_sources_read: entity_write.py, field_write_service.py, field_resolver.py, write_registry.py, services/errors.py, architecture.md
secondary_sources_read: automation/seeding.py (ADR-EW-003 confirm), api/dependencies.py, api/lifespan.py, docs/guides/entity-write.md, scar-tissue.md
test_files_counted: 5 (509 + 418 + 496 + 147 + 1146 = 2716 total lines)
changes_from_prior_version:
  - Added openapi_extra fleet annotations (x-fleet-side-effects, x-fleet-idempotency, x-fleet-rate-limit)
  - Corrected startup lifespan step for EntityWriteRegistry to step 11 (not step 11 as stated — confirmed from lifespan.py position relative to 14-step sequence)
  - Added FieldWriteResult status translation detail (internal "resolved" → exposed "written")
  - Added EntityWriteRegistryDep injection pattern via app.state
  - Expanded test coverage table with line counts
  - Added DISCOVERY_INCOMPLETE 503 error path
  - Confirmed ADR-EW-003 reuse in seeding.py
  - include_in_schema=False documented
  - Disabled enum option gap preserved as known gap
  - source_hash updated from c213958 to 8980bcd7
```
