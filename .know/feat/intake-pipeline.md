---
domain: feat/intake-pipeline
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/api/routes/intake_create.py"
  - "./src/autom8_asana/api/routes/intake_resolve.py"
  - "./src/autom8_asana/api/routes/intake_custom_fields.py"
  - "./src/autom8_asana/services/intake_create_service.py"
  - "./src/autom8_asana/services/intake_resolve_service.py"
  - "./src/autom8_asana/services/intake_custom_field_service.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.93
format_version: "1.0"
---

# Intake Pipeline

## Purpose and Design Rationale

The intake pipeline is the S2S JWT-authenticated boundary through which the `autom8y-data`
service provisions and resolves business records in Asana. It exists to decouple the
data-ingestion layer from direct Asana API access: callers provide structured business,
contact, and process data; the pipeline translates that into the canonical Asana entity
hierarchy.

Three distinct concerns are served by five routes across three service classes:

| Concern | Routes | Service |
|---------|--------|---------|
| Creation | `POST /v1/intake/business`, `POST /v1/intake/route` | `IntakeCreateService` |
| Resolution | `POST /v1/resolve/business`, `POST /v1/resolve/contact` | `IntakeResolveService` |
| Custom field writes | `POST /v1/tasks/{task_gid}/custom-fields` | `IntakeCustomFieldService` |

All five routes are hidden from the OpenAPI spec (`include_in_schema=False`); they are an
internal S2S contract, not a public API.

### Key Design Decisions

**ADR-INT-001 — Never return 404 for not-found**: Resolution endpoints return `found=False`
rather than a 404. This prevents the "ANOMALY-F" bug where a stale-GID fallback silently
created duplicate businesses on 404. Documented in `intake_resolve.py` and
`intake_resolve_models.py`.

**ADR-INT-002 — Email-then-phone priority, no name matching**: Contact resolution uses a
fixed two-step algorithm: email exact match → phone exact match → no match. Name matching
was rejected to avoid false-positive merges on common contact names. Documented in
`intake_resolve_service.py:207-302`.

**7-phase strictly-ordered creation with Phase 2 parallelism**: Business hierarchy creation
always runs phases 1-7 in strict sequential order except Phase 2 (7 holder subtasks), which
runs via `asyncio.gather` for throughput. Documented in `intake_create.py` route docstring.

**Idempotent process routing**: `POST /v1/intake/route` checks for an existing open process
subtask by name before creating a new one. Existing → `is_new=False`; new → `is_new=True`.
This prevents double-routing on retry.

**Per-request `AsanaClient`**: Every route instantiates `AsanaClient` inside `async with`
using the JWT-derived PAT from `auth_context.asana_pat`. This deliberately bypasses the
shared `ClientPool`. See Boundaries section for the consequence.

**SOCIAL-PROFILES-ORPHANED fix**: Social profile URLs are now written as custom fields on
the Business task (Phase 6). Prior to this fix they were silently dropped.

**ZIP-MISMATCH fix**: Address uses `postal_code` as the canonical field name everywhere.
The ZIP alias lives in `autom8y-google`'s `StructuredAddress`; by the time data reaches
the intake models the field is already normalized. Enforced in `IntakeAddress` model.

**GAP-001 — CONSULTATION ProcessType missing**: The `consultation` process type is absent
from `VALID_PROCESS_TYPES` (`intake_create_service.py:48`). The code comment documents
this explicitly: `"Per truth audit: 'consultation' removed — ProcessType model does not
exist yet."` Any request with `process_type="consultation"` will receive a 422
UNKNOWN_PROCESS_TYPE response. This blocks the Consultation flow entirely until the
`consultation` enum value is added.

---

## Conceptual Model

### Terminology

| Term | Meaning |
|------|---------|
| **Business** | Root Asana task representing a client business entity |
| **Holder** | Subtask under Business that groups related sub-entities; 7 types: `contact_holder`, `unit_holder`, `location_holder`, `dna_holder`, `reconciliations_holder`, `asset_edit_holder`, `videography_holder` |
| **Unit** | Subtask under `unit_holder`; represents the active service engagement with the business |
| **Contact** | Subtask under `contact_holder`; the primary business contact person |
| **Process** | Subtask under Unit; represents a workflow engagement (sales, retention, implementation) |
| **GID** | Asana Global ID; every Asana task/project has one; the stable identifier used across the pipeline |
| **E.164** | Phone number format `+{country_code}{digits}`; all phone fields use this format |
| **DynamicIndexCache** | In-memory O(1) index for GID lookup by field criteria; used for business resolution |
| **VALID_PROCESS_TYPES** | Set `{"sales", "retention", "implementation"}` — the complete set of allowed process types today |
| **found=False** | Resolution response indicating no match, per ADR-INT-001 |

### Business Hierarchy (Asana structure)

```
Business task  [POST /v1/intake/business creates this]
  ├── contact_holder
  │   └── Contact subtask
  ├── unit_holder
  │   └── Unit subtask
  │       └── {ProcessType} Process subtask  [POST /v1/intake/route]
  ├── location_holder  [receives address custom fields]
  ├── dna_holder
  ├── reconciliations_holder
  ├── asset_edit_holder
  └── videography_holder
```

### 7-Phase Creation Lifecycle

```
Phase 1 → Create Business task (project_gid from EntityProjectRegistry)
Phase 2 → Create 7 holder subtasks (parallel, asyncio.gather)
Phase 3 → Create Unit subtask under unit_holder + write Vertical enum CF
Phase 4 → Create Contact subtask under contact_holder
Phase 5 → Route Process (optional; delegates to route_process())
Phase 6 → Write social profiles as custom fields on Business (conditional)
Phase 7 → Write address fields to location_holder (conditional)
```

Phases 1-4 are always executed. Phases 5-7 are conditional on request fields being
non-None/non-empty.

### Contact Resolution Algorithm (ADR-INT-002)

```
Input: business_gid, email?, phone?
1. Find contact_holder subtask of business (by name substring "contact_holder")
2. Fetch all subtasks of contact_holder with custom_fields
3. If email: scan for exact case-insensitive match on contact_email custom field → return
4. If phone: scan for exact match on contact_phone custom field → return
5. No match → found=False
```

### Business Resolution Algorithm

```
Input: office_phone, vertical?
1. resolve_gid_from_index(office_phone, vertical)
   → try DynamicIndexCache["business"] O(1) lookup
   → fallback: DynamicIndexCache["unit"] O(1) lookup
2. If GID found: fetch task details from Asana, check for unit_holder/contact_holder subtasks
3. Return BusinessResolveResponse(found=True/False)
```

### Inter-Feature Relationships

- **Consumes from**: `EntityProjectRegistry` (provides business project GID for Phase 1),
  `DynamicIndexCache` / `get_shared_index_cache()` (provides O(1) index for business resolution),
  `SchemaRegistry` (optional enrichment in `IntakeCustomFieldService._enrich_from_schema_registry()`),
  `AsanaClient` (all Asana API calls)
- **Provides to**: `autom8y-data` service (primary caller over S2S JWT); GIDs returned are
  used downstream for data association
- **Authentication gate**: `require_service_claims` dependency on all routes; PAT tokens
  are explicitly rejected with `SERVICE_TOKEN_REQUIRED` (401)

---

## Implementation Map

### Route Files

| File | Router Prefix | Routes |
|------|--------------|--------|
| `api/routes/intake_create.py` | `/v1/intake` | `POST /business`, `POST /route` |
| `api/routes/intake_resolve.py` | `/v1` | `POST /resolve/business`, `POST /resolve/contact` |
| `api/routes/intake_custom_fields.py` | `/v1/tasks` | `POST /{task_gid}/custom-fields` |

Router registration in `api/main.py`:
- `intake_resolve_router` (prefix `/v1`, mounts BEFORE `resolver_router` which uses wildcard)
- `intake_custom_fields_router` (prefix `/v1/tasks`)
- `intake_create_router` (prefix `/v1/intake`)

All three routers use `s2s_router()` factory from `api/routes/_security.py`, which wires
`JWTAuthMiddleware` and `require_service_claims`.

### Service Files

| File | Class | Key Methods |
|------|-------|-------------|
| `services/intake_create_service.py` | `IntakeCreateService` | `create_business_hierarchy(request)`, `route_process(unit_gid, process_type, ...)` |
| `services/intake_resolve_service.py` | `IntakeResolveService` | `resolve_business(office_phone, vertical)`, `resolve_contact(business_gid, email, phone)` |
| `services/intake_custom_field_service.py` | `IntakeCustomFieldService` | `write_fields(task_gid, fields)` |

### Co-Located Model Files (TENSION-002)

All three service files import their request/response models from co-located route model
files — an intentional layer violation documented as TENSION-002:

| Service import | Source |
|----------------|--------|
| `intake_create_service.py:23-27` | `api/routes/intake_create_models.py` |
| `intake_resolve_service.py:18-21` | `api/routes/intake_resolve_models.py` |
| `intake_custom_field_service.py:16` | `api/routes/intake_custom_fields_models.py` |

These are bare (non-TYPE_CHECKING) imports. Semgrep's `autom8y.no-services-import-api`
rule flags these on every CI run. No planned migration.

### Module-Level Functions (Testability Pattern)

`intake_create_service.py` and `intake_resolve_service.py` use module-level functions for
registry access to enable clean test patching:

- `resolve_workspace_gid()` — calls `EntityProjectRegistry.get_instance()`, catches all
  exceptions, returns `""` on failure
- `resolve_business_project_gid()` — same pattern for business project GID
- `resolve_gid_from_index(office_phone, vertical)` — calls `get_shared_index_cache()`,
  catches all exceptions, returns `None` on failure

All three swallow exceptions silently. Non-initialization of the registry → empty string /
None return → graceful degradation at the cost of silent misconfiguration.

### Key Constants

| Constant | Location | Value |
|----------|----------|-------|
| `VALID_PROCESS_TYPES` | `intake_create_service.py:48` | `{"sales", "retention", "implementation"}` |
| `HOLDER_TYPES` | `intake_create_service.py:35-44` | 7 holder name strings |
| `SOCIAL_FIELD_MAP` | `intake_create_service.py:51-56` | platform → Asana CF name |
| `ADDRESS_FIELD_MAP` | `intake_create_service.py:59-68` | Python attr → Asana CF display name |
| `_CONTACT_EMAIL_FIELD` | `intake_resolve_service.py:32` | `"contact_email"` |
| `_CONTACT_PHONE_FIELD` | `intake_resolve_service.py:33` | `"contact_phone"` |
| `_COMPANY_ID_FIELD` | `intake_resolve_service.py:34` | `"company_id"` |

### Data Flow

**Creation path**:
```
POST /v1/intake/business
  → validate E.164 phone, validate process_type in VALID_PROCESS_TYPES
  → AsanaClient(token=auth.asana_pat) [per-request, not ClientPool]
  → IntakeCreateService.create_business_hierarchy(request)
    → resolve_business_project_gid()  [EntityProjectRegistry, swallows exc]
    → Phase 1-7 Asana API calls via self._client.tasks.*
  → IntakeBusinessCreateResponse (all entity GIDs)
```

**Business resolution path**:
```
POST /v1/resolve/business
  → validate E.164 phone
  → IntakeResolveService.resolve_business(phone, vertical)
    → resolve_gid_from_index()  [DynamicIndexCache O(1), swallows exc]
    → If found: self._client.tasks.get_async(gid, opt_fields=[...])
    → If found: self._client.tasks.subtasks_async(gid) to check holders
  → BusinessResolveResponse(found=True/False, ...)
```

**Custom field write path**:
```
POST /v1/tasks/{task_gid}/custom-fields
  → validate non-empty fields dict
  → IntakeCustomFieldService.write_fields(task_gid, fields)
    → self._client.tasks.get_async(task_gid, opt_fields=["memberships","custom_fields"])
    → build field_name_to_gid from task's current CFs (display name + snake_case)
    → _enrich_from_schema_registry()  [SchemaRegistry, swallows exc]
    → resolve each field name to GID; unresolved → errors list
    → single self._client.tasks.update_async(task_gid, {"custom_fields": payload})
  → CustomFieldWriteResponse(fields_written=N, errors=[...])
```

### Test Files

7 test files under `tests/unit/api/routes/`:
- `test_intake_create.py` — route handler tests for `POST /v1/intake/business`
- `test_intake_route.py` — route handler tests for `POST /v1/intake/route`
- `test_intake_resolve.py` — route handler tests for `POST /v1/resolve/business` + contact
- `test_intake_custom_fields.py` — route handler tests for `POST /{task_gid}/custom-fields`
- `test_intake_create_models.py` — Pydantic model validation tests
- `test_intake_resolve_models.py` — Pydantic model validation tests
- `test_intake_custom_fields_models.py` — Pydantic model validation tests

No integration tests observed that exercise live Asana API calls. Service-layer unit tests
exist under pycache evidence but dedicated service-layer test files are not present in the
observed path (route-level tests mock the service).

---

## Boundaries and Failure Modes

### Scope Boundaries

This feature does NOT:
- Use the shared `ClientPool` — each request creates a fresh `AsanaClient` via
  `async with AsanaClient(token=auth.asana_pat)`. This is a deliberate divergence from the
  `ClientPool` pattern used by all PAT routes. Consequence: no connection reuse, no
  per-token resilience (DEF-005 pattern not applied). This is a known boundary.
- Support PAT authentication — `require_service_claims` rejects non-service tokens with 401.
- Support `consultation` process type — `VALID_PROCESS_TYPES` deliberately excludes it
  (GAP-001).
- Validate that the GIDs returned by `resolve_gid_from_index()` are still live — it
  returns the first GID from the cache index without a freshness check.
- Provide rollback on partial creation failure — if Phase 3 fails, the Business task and 7
  holders created in Phases 1-2 are orphaned in Asana.
- Appear in the OpenAPI spec — `include_in_schema=False` on all three routers.

### Error Paths

**`POST /v1/intake/business`**:
- 400 `INVALID_PHONE_FORMAT`: E.164 validation fails before service call
- 422 `UNKNOWN_PROCESS_TYPE`: `process.process_type not in VALID_PROCESS_TYPES`
- 503 `PROJECT_NOT_CONFIGURED`: `EntityProjectRegistry` not initialized (`LookupError`)
- 503 `ASANA_UNAVAILABLE`: any other exception at the route boundary (BROAD-CATCH)

**`POST /v1/intake/route`**:
- 404 `UNIT_NOT_FOUND`: `LookupError` from `tasks.get_async(unit_gid)`
- 422 `UNKNOWN_PROCESS_TYPE`: via `ValueError` from `route_process()` or explicit check
- 503 `ASANA_UNAVAILABLE`: any other exception (BROAD-CATCH)

**`POST /v1/resolve/business`**:
- 400 `INVALID_PHONE_FORMAT`: E.164 validation
- 503 `INDEX_NOT_READY`: `RuntimeError` containing "not initialized" or "not ready" from
  `get_shared_index_cache()`
- 503 `ASANA_UNAVAILABLE`: other exceptions (BROAD-CATCH)

**`POST /v1/resolve/contact`**:
- 404 `BUSINESS_NOT_FOUND`: `LookupError` from subtask lookup
- 422 `MISSING_CRITERIA`: neither email nor phone provided
- 503 `ASANA_UNAVAILABLE`: other exceptions (BROAD-CATCH)

**`POST /v1/tasks/{task_gid}/custom-fields`**:
- 404 `TASK_NOT_FOUND`: `NotFoundError` from `tasks.get_async()`
- 422 `EMPTY_FIELDS`: empty fields dict
- 429 `RATE_LIMITED`: `RateLimitError` with `Retry-After` header (tier: external)
- 503 `ASANA_UNAVAILABLE`: other exceptions (BROAD-CATCH)

### Non-Fatal Degradation Paths

Several internal operations are explicitly non-fatal (log warning, continue):
- `_write_vertical_custom_field()` in Phase 3: if "Vertical" CF not found on task, logs
  warning and returns without error
- Phase 6 social profiles: if a field name doesn't resolve to a GID, logs
  `social_field_not_resolved` and skips that profile
- `_resolve_assignee()`: logs warning on any failure, returns `None` (assignee not set)
- `_find_existing_process()`: logs warning on subtask list failure, returns `None`
  (proceeds to create new process — potential double-creation risk on Asana API degradation)
- `_enrich_from_schema_registry()`: swallows all exceptions; field resolution degrades to
  task-fetched CFs only

### Structural Tensions

**TENSION-002**: Services layer imports request/response models from `api/routes/` at
module load time. No `TYPE_CHECKING` guard. Semgrep fires on every CI run. Documented as
intentional, no migration planned. Location: all 3 service files.

**TENSION-002 implication for agents**: Do NOT assume that `api/routes/intake_*_models.py`
files are API-layer-only. The service layer depends on them at runtime. Moving or renaming
these model files requires updating both route and service imports.

### Interaction Points with Other Features

| Boundary | Direction | Nature |
|----------|-----------|--------|
| `EntityProjectRegistry` | consumes | Module-level `resolve_business_project_gid()`; exception-swallowed; returns `""` if not initialized |
| `DynamicIndexCache` / `get_shared_index_cache()` | consumes | Module-level `resolve_gid_from_index()`; exception-swallowed; returns `None` if cache miss or uninitialized |
| `SchemaRegistry` | consumes | `IntakeCustomFieldService._enrich_from_schema_registry()`; exception-swallowed; graceful degradation |
| `AsanaClient.tasks.*` | consumes | All Asana API I/O; `create_async`, `get_async`, `update_async`, `subtasks_async(...).collect()` |
| `autom8y-data` service | consumed by | Primary external caller; dispatches S2S JWT requests |
| `autom8y-interop/asana/models.py` | interop contract | JSON contract with external SDK; not mechanically enforced in CI |

### Known Risks

1. **No creation rollback**: Partial creation failure (e.g., Phase 3 crash) orphans
   Phases 1-2 Asana tasks. The caller receives 503; retrying calls `POST /v1/intake/business`
   again, creating a second Business task. No deduplication at the creation level.

2. **Interop contract unenforced**: `intake_*_models.py` docstrings declare they must match
   `autom8y-client-sdk/asana/models.py`. This contract is documentation-only; no CI test
   validates shape parity.

3. **Contact holder detection by substring**: `resolve_contact()` and `resolve_business()`
   both find `contact_holder` by checking `"contact_holder" in st_name.lower()`. A subtask
   named e.g. `"old_contact_holder_backup"` would match. Non-deterministic if multiple
   matching subtasks exist (returns first match only).

4. **Process idempotency by name**: `_find_existing_process()` matches existing processes
   by exact name `"{process_type.title()} Process"`. Asana tasks can be renamed; a renamed
   process task will not be found, causing a new process to be created.

5. **Phone email non-normalization in contact resolution**: Email matching is
   case-insensitive; phone matching is exact-string. A phone stored as `+14155551234` will
   not match a search for `+1-415-555-1234` (non-E.164 input). The `is_valid_e164` check
   only applies to `office_phone` on the business create/resolve routes, not the contact
   phone on `resolve_contact`.

---

```metadata
source_hash: "8980bcd7"
confidence: 0.93
gaps:
  - "DynamicIndexCache internals (warming lifecycle, eviction, `get_shared_index_cache()` signature) not read in depth"
  - "autom8y-interop contract validation mechanism unknown — CI enforcement absent"
  - "Per-request AsanaClient performance impact under high intake volume not characterized"
  - "Service-layer unit test files (for IntakeCreateService, IntakeResolveService, IntakeCustomFieldService directly) not confirmed by path scan — only route-handler tests observed"
  - "VALID_PROCESS_TYPES synchronization mechanism with downstream ProcessType enum unknown — manual, no CI guard"
```
