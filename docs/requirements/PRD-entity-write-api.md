# PRD: Entity Write API

```yaml
id: PRD-ENTITY-WRITE-API
status: stakeholder-approved
author: requirements-analyst
date: 2026-02-11
impact: high
impact_categories: [api_contract, data_model, cross_service]
complexity: MODULE
sprints: TBD (Pythia orchestration)
stakeholder_interview: 6 rounds, 22 decisions
```

## Executive Summary

Expose a REST endpoint (`PUT /api/v1/entity/{entity_type}/{gid}`) that writes custom field values and manages tags on Asana entities using business-domain field names. This is the "control plane" complement to the existing read-oriented resolve and query endpoints. External consumers (primarily autom8_data) can modify entity state through a validated, type-safe API that triggers downstream automations identically to internal pipeline operations.

## Background

### Current State

The autom8_asana system has a mature read path: entity resolution (`POST /v1/resolve/{entity_type}`), query endpoints, and a DataFrame-backed data service. However, there is **no REST API for writing entity state**. The only custom field write in the codebase is `FieldSeeder.write_fields_async()` at `automation/seeding.py:539`, which is internal-only (called during pipeline automation, never exposed via REST).

This creates a fundamental asymmetry: external services can read entity data but must use Asana's raw API (with raw GIDs, no type validation, no automation triggers) to write it.

### Why Now

1. **Lifecycle Engine Complete**: The lifecycle hardening initiative delivered data-driven stage transitions. Writing fields is the natural next capability.
2. **autom8_data Dependency**: autom8_data already has a client pattern for calling autom8_asana endpoints. It needs write access to push computed insights back to Asana entities.
3. **Automation Parity**: Manual Asana changes trigger automation rules (via webhooks). API writes must trigger the same rules, or the system diverges.

### Existing Building Blocks

| Component | Location | Reuse Status |
|-----------|----------|--------------|
| CustomFieldAccessor | `models/custom_field_accessor.py` | **Direct reuse** -- name-to-GID resolution, type validation, `to_api_dict()` |
| CustomFieldDescriptor hierarchy | `models/business/descriptors.py` | **Reference** -- defines valid field types per entity (TextField, EnumField, etc.) |
| FieldSeeder.write_fields_async() | `automation/seeding.py:397-568` | **Pattern reference** -- enum-to-GID resolution, field matching, single API call |
| TasksClient.update_async() | `clients/tasks.py:425` | **Direct reuse** -- `custom_fields={gid: value}` kwarg |
| TagsClient | `clients/tags.py` | **Direct reuse** -- add_to_task/remove_from_task (GID-based) |
| EntityService | `services/entity_service.py` | **Direct reuse** -- validates entity type, resolves project GID, acquires bot PAT |
| EntityContext | `services/entity_context.py` | **Direct reuse** -- frozen context with entity_type, project_gid, descriptor, bot_pat |
| AutomationEngine.evaluate_async() | `automation/engine.py:113` | **Integration needed** -- post-write automation evaluation |
| SaveSession | `persistence/session.py` | **Not reused** -- too heavy for single-entity writes; direct client call preferred |
| S2S JWT auth | `api/routes/internal.py` | **Direct reuse** -- `require_service_claims` dependency |
| NameNotFoundError | `exceptions.py:222` | **Direct reuse** -- fuzzy-match suggestions on field name mismatch |

---

## User Stories

### US-WRITE-001: Write Custom Fields by Business Name

**As a** autom8_data service developer
**I want to** update Asana entity custom fields using business-domain field names (e.g., "Weekly Ad Spend", not GID "1234567890")
**So that** I can push computed insights back to Asana without maintaining a GID mapping table

**Acceptance Criteria**:
- [ ] `PUT /api/v1/entity/{entity_type}/{gid}` accepts a JSON body with `fields` dict
- [ ] Field names are resolved to Asana custom field GIDs via CustomFieldAccessor
- [ ] Field values are type-validated against entity model descriptors before write
- [ ] Enum field string values are resolved to option GIDs (case-insensitive)
- [ ] Multi-enum field lists are resolved element-by-element
- [ ] Response includes the list of fields successfully written
- [ ] Response includes fields skipped (not found on entity) with suggestions

### US-WRITE-002: Manage Tags by Name

**As a** autom8_data service developer
**I want to** add and remove tags from entities using tag names (not GIDs)
**So that** I can manage categorical labels without GID lookups

**Acceptance Criteria**:
- [ ] Request body accepts `tags_add` (list of tag names or GIDs) and `tags_remove` (list of tag names or GIDs)
- [ ] Tag names are resolved to GIDs via workspace tag search
- [ ] Tags not found in workspace return a clear error (not silently ignored)
- [ ] Tag operations are atomic per tag (partial success is reported)
- [ ] Response includes which tags were added, removed, and which failed

### US-WRITE-003: Trigger Post-Write Automations

**As a** system operator
**I want** REST API writes to trigger the same automation rules as internal pipeline writes
**So that** the system behaves consistently regardless of write source

**Acceptance Criteria**:
- [ ] After successful field write, AutomationEngine.evaluate_async() is called
- [ ] Automation evaluation is best-effort (failure does not fail the write response)
- [ ] Response includes `automations_triggered` count and any automation errors
- [ ] Automation trigger can be suppressed via `?trigger_automations=false` query param

### US-WRITE-004: Validate Entity Exists Before Write

**As a** API consumer
**I want** the endpoint to validate that the entity GID exists and belongs to the specified entity type
**So that** I get clear errors instead of silent Asana failures

**Acceptance Criteria**:
- [ ] Entity type is validated against EntityService.get_queryable_entities()
- [ ] Task GID is fetched from Asana to confirm existence
- [ ] If task does not belong to the entity type's project, return 404 with explanation
- [ ] If task GID does not exist in Asana, return 404

### US-WRITE-005: Return Updated Entity State

**As a** API consumer
**I want** the write response to include the updated custom field values
**So that** I can confirm the write took effect without a separate read call

**Acceptance Criteria**:
- [ ] Response includes the current custom field values after the write
- [ ] Field values are returned using business-domain names (not GIDs)
- [ ] Only fields that were written or requested are included in the response
- [ ] Response includes the task GID and entity type for correlation

---

## Functional Requirements

### FR-WRITE-001: PUT Endpoint Registration

The system SHALL expose `PUT /api/v1/entity/{entity_type}/{gid}` as a FastAPI route.

- Route prefix: `/api/v1/entity`
- Router registered in `api/main.py` alongside existing routers
- Authentication: S2S JWT via `require_service_claims` dependency (same as resolver)
- Path parameters: `entity_type` (string), `gid` (string, numeric)

**Priority**: MUST

### FR-WRITE-002: Request Body Schema

The request body SHALL conform to this Pydantic model:

```python
class EntityWriteRequest(BaseModel):
    fields: dict[str, Any] | None = None       # Business-name -> value
    tags_add: list[str] | None = None           # Tag names or GIDs to add
    tags_remove: list[str] | None = None        # Tag names or GIDs to remove
    trigger_automations: bool = True            # Override via body or query param
```

Constraints:
- At least one of `fields`, `tags_add`, or `tags_remove` must be non-empty
- Empty request body returns 422

**Priority**: MUST

### FR-WRITE-003: Entity Type Validation

The system SHALL validate `entity_type` against the set of writable entity types.

- v1 writable types: `offer`, `unit`, `business`, `process`, `contact`, `asset_edit`
- Validation via EntityService.validate_entity_type() (reuses existing EntityContext flow)
- Unknown entity type returns 404 with `UNKNOWN_ENTITY_TYPE` error code and available types list
- Discovery-incomplete returns 503 with `DISCOVERY_INCOMPLETE` error code

**Priority**: MUST

### FR-WRITE-004: Task GID Verification

The system SHALL verify that the target task GID exists and belongs to the entity type's project.

- Fetch task via `TasksClient.get_async(gid, opt_fields=["custom_fields", "custom_fields.name", "custom_fields.resource_subtype", "custom_fields.enum_options", "memberships.project.gid", "tags", "tags.name"])` (single API call)
- Verify at least one membership matches the entity type's project GID
- If task not found: 404, error code `TASK_NOT_FOUND`
- If task exists but wrong project: 404, error code `ENTITY_TYPE_MISMATCH`, include actual project GIDs

**Priority**: MUST

### FR-WRITE-005: Custom Field Name Resolution

The system SHALL resolve business-domain field names to Asana custom field GIDs.

- Build CustomFieldAccessor from fetched task's custom_fields data
- Use case-insensitive matching (same as FieldSeeder)
- If field name not found: include in `fields_skipped` response with fuzzy suggestions via NameNotFoundError
- If field name resolves to GID: include in write batch
- Accept raw GIDs (numeric strings) as passthrough (no resolution needed)

**Priority**: MUST

### FR-WRITE-006: Field Type Validation

The system SHALL validate field values against their custom field type before writing.

Type validation rules (matching CustomFieldAccessor._validate_type):

| Field Type | Accepted Input | API Output |
|------------|---------------|------------|
| text | `string` | string |
| number | `int`, `float` | number |
| enum | `string` (option name or GID) | option GID |
| multi_enum | `list[string]` (option names or GIDs) | list of option GIDs |
| date | `string` (ISO 8601: YYYY-MM-DD) | `{"date": "YYYY-MM-DD"}` |
| people | `list[string]` (user GIDs) | list of user GIDs |

- Type mismatch returns 422 with `FIELD_TYPE_ERROR`, field name, expected type, and actual type
- Null/None value clears the field (valid for all types)

**Priority**: MUST

### FR-WRITE-007: Enum Value Resolution

The system SHALL resolve enum string values to Asana option GIDs.

- For `enum` fields: case-insensitive name match against enum_options, or GID passthrough
- For `multi_enum` fields: resolve each element independently
- Unknown enum value: skip that field, include in `fields_skipped` with available options
- Uses FieldSeeder._build_enum_lookup() pattern (case-insensitive name-to-GID + GID passthrough)

**Priority**: MUST

### FR-WRITE-008: Custom Field Write Execution

The system SHALL write resolved fields to Asana in a single API call.

- Build `custom_fields` dict via `CustomFieldAccessor.to_api_dict()`
- Execute via `TasksClient.update_async(gid, custom_fields=api_dict)`
- Single API call for all fields (batch, not per-field)

**Priority**: MUST

### FR-WRITE-009: Tag Name Resolution

The system SHALL resolve tag names to GIDs via workspace tag lookup.

- For each tag name in `tags_add` or `tags_remove`:
  - If numeric string: treat as GID (passthrough)
  - If non-numeric string: search workspace tags by name (case-insensitive)
- Tag resolution uses `TagsClient.list_for_workspace_async()` with name filtering
- Tag name cache per request (avoid redundant API calls for same name)
- Unresolved tag name: include in `tags_failed` response with error detail

**Priority**: MUST

### FR-WRITE-010: Tag Add/Remove Execution

The system SHALL add and remove tags from the target task.

- Add: `TagsClient.add_to_task_async(task_gid, tag=tag_gid)` for each resolved tag
- Remove: `TagsClient.remove_from_task_async(task_gid, tag=tag_gid)` for each resolved tag
- Operations are individual API calls (Asana API constraint: one tag per call)
- Partial success: report each tag operation result individually

**Priority**: MUST

### FR-WRITE-011: Post-Write Automation Trigger

The system SHALL optionally trigger automation evaluation after a successful write.

- Default: `trigger_automations=true`
- Construct a minimal SaveResult-compatible structure for AutomationEngine.evaluate_async()
- Automation evaluation is fire-and-forget within the request (does not block response beyond a timeout)
- Automation timeout: 5 seconds (configurable). If exceeded, return response with `automations_timed_out: true`
- Automation failures are logged but do not affect write response status

**Priority**: SHOULD

### FR-WRITE-012: Response Schema

The system SHALL return a structured response:

```python
class FieldWriteResult(BaseModel):
    name: str                         # Business-domain field name
    status: Literal["written", "skipped", "error"]
    error: str | None = None          # Error detail if skipped/error
    suggestions: list[str] | None = None  # Fuzzy matches if name not found

class TagOperationResult(BaseModel):
    name: str                         # Tag name or GID
    operation: Literal["add", "remove"]
    status: Literal["success", "failed"]
    error: str | None = None

class EntityWriteResponse(BaseModel):
    gid: str
    entity_type: str
    fields_written: int
    fields_skipped: int
    field_results: list[FieldWriteResult]
    tag_results: list[TagOperationResult] | None = None
    automations_triggered: int = 0
    automations_errors: list[str] | None = None
    updated_fields: dict[str, Any] | None = None  # Post-write field values
```

**Priority**: MUST

### FR-WRITE-013: Idempotency

The system SHALL be idempotent for field writes.

- Writing the same field value twice produces the same result
- Asana's custom field update API is naturally idempotent
- Tag add is idempotent (adding an already-present tag is a no-op in Asana)
- Tag remove is idempotent (removing an absent tag is a no-op in Asana)

**Priority**: MUST (by design -- Asana API guarantees this)

### FR-WRITE-014: Partial Write Semantics

The system SHALL apply all valid fields even if some fields fail validation.

- Field validation errors do not abort the entire request
- Valid fields are written; invalid fields are reported in `field_results` with status `skipped`
- If ALL fields fail validation (zero writable fields), return 422 with `NO_VALID_FIELDS` error
- Tag operations proceed independently of field operations

**Priority**: MUST

---

## Non-Functional Requirements

### NFR-WRITE-001: Latency

- P50 latency for a 5-field write: under 800ms
- P99 latency for a 5-field write: under 2000ms
- Breakdown budget: task fetch (~200ms) + field write (~300ms) + tag ops (~200ms/tag) + automation trigger (~200ms)

### NFR-WRITE-002: Rate Limiting

- Inherits service-level rate limits from SlowAPI middleware
- Asana API rate limit: 1500 requests/minute shared across all operations
- Single write request consumes 2-3 Asana API calls minimum (fetch + update + optional tag ops)
- Endpoint-specific limit: 100 write requests/minute (configurable)

### NFR-WRITE-003: Authentication and Authorization

- S2S JWT authentication via `require_service_claims` (same as resolver)
- PAT tokens are NOT supported (internal/service endpoint only)
- No per-entity authorization in v1 (all authenticated services can write all entity types)
- Caller service name logged for audit trail

### NFR-WRITE-004: Observability

Structured logging for every write request:

| Log Event | When | Fields |
|-----------|------|--------|
| `entity_write_request` | Request received | request_id, entity_type, gid, caller_service, field_count |
| `entity_write_field_resolution` | Per field resolved | field_name, resolved_gid, status |
| `entity_write_api_call` | Before Asana API call | task_gid, custom_fields_count |
| `entity_write_tag_operation` | Per tag op | task_gid, tag, operation, status |
| `entity_write_automation_trigger` | After automation eval | automations_triggered, automations_failed |
| `entity_write_complete` | Request complete | request_id, duration_ms, fields_written, fields_skipped |
| `entity_write_error` | On failure | request_id, error_code, error_message |

### NFR-WRITE-005: Error Recovery

- Asana 429 (rate limit): return 429 to caller with Retry-After header
- Asana 5xx (server error): return 502 with `ASANA_UPSTREAM_ERROR`
- Asana timeout: return 504 with `ASANA_TIMEOUT`
- Network error: return 502 with `ASANA_CONNECTION_ERROR`
- All Asana errors surfaced via existing AsanaError hierarchy (AsanaError, RateLimitError, ServerError, TimeoutError)

### NFR-WRITE-006: Concurrency Safety

- No shared mutable state across requests (CustomFieldAccessor is request-scoped)
- Bot PAT acquisition is thread-safe (existing BotPAT singleton)
- No session-level locking needed (unlike SaveSession, this is stateless per-request)

---

## Entity Type Scope

### v1 (This Initiative)

| Entity Type | Custom Fields | Tag Support | Notes |
|-------------|--------------|-------------|-------|
| `offer` | 39+ descriptors | Yes | Primary consumer use case |
| `unit` | 15+ descriptors | Yes | |
| `business` | 10+ descriptors | Yes | |
| `process` | 12+ descriptors | Yes | |
| `contact` | 8+ descriptors | Yes | |
| `asset_edit` | 5+ descriptors | Yes | |

### Deferred (v2)

| Entity Type | Reason |
|-------------|--------|
| Holder types (`offer_holder`, `unit_holder`, etc.) | Holders are structural, not typically written to by external consumers |
| `location`, `hours`, `videography` | Low external demand; can be added by extending WRITABLE_ENTITY_TYPES set |

---

## API Contract

### Request

```
PUT /api/v1/entity/{entity_type}/{gid}
Authorization: Bearer <S2S JWT>
Content-Type: application/json

{
    "fields": {
        "Weekly Ad Spend": 500,
        "Status": "Active",
        "Platforms": ["Facebook", "Google"],
        "Asset ID": "asset-12345",
        "Launch Date": "2026-03-01"
    },
    "tags_add": ["optimize", "priority-high"],
    "tags_remove": ["needs-review"],
    "trigger_automations": true
}
```

### Success Response (200)

```json
{
    "gid": "1234567890",
    "entity_type": "offer",
    "fields_written": 4,
    "fields_skipped": 1,
    "field_results": [
        {"name": "Weekly Ad Spend", "status": "written"},
        {"name": "Status", "status": "written"},
        {"name": "Platforms", "status": "written"},
        {"name": "Asset ID", "status": "written"},
        {"name": "Launch Date", "status": "skipped", "error": "Field 'Launch Date' not found on entity", "suggestions": ["Launch date", "Due Date"]}
    ],
    "tag_results": [
        {"name": "optimize", "operation": "add", "status": "success"},
        {"name": "priority-high", "operation": "add", "status": "success"},
        {"name": "needs-review", "operation": "remove", "status": "success"}
    ],
    "automations_triggered": 1,
    "automations_errors": null,
    "updated_fields": {
        "Weekly Ad Spend": 500,
        "Status": "Active",
        "Platforms": ["Facebook", "Google"],
        "Asset ID": "asset-12345"
    }
}
```

### Error Responses

| Code | Error Code | Condition |
|------|-----------|-----------|
| 401 | `MISSING_AUTH` | No Authorization header |
| 401 | `SERVICE_TOKEN_REQUIRED` | PAT token provided (S2S only) |
| 404 | `UNKNOWN_ENTITY_TYPE` | entity_type not in writable set |
| 404 | `TASK_NOT_FOUND` | GID does not exist in Asana |
| 404 | `ENTITY_TYPE_MISMATCH` | Task exists but belongs to wrong project |
| 422 | `EMPTY_REQUEST` | No fields, tags_add, or tags_remove provided |
| 422 | `NO_VALID_FIELDS` | All fields failed validation (none writable) |
| 422 | `FIELD_TYPE_ERROR` | Type mismatch on a field (included in field_results, request still proceeds for other fields) |
| 429 | `RATE_LIMITED` | Service or Asana rate limit exceeded |
| 502 | `ASANA_UPSTREAM_ERROR` | Asana 5xx or connection error |
| 503 | `DISCOVERY_INCOMPLETE` | Startup discovery not finished |
| 504 | `ASANA_TIMEOUT` | Asana API call timed out |

---

## Edge Cases

### EC-001: Field Name Collision

**Scenario**: Two custom fields on the same entity have names that differ only by case (e.g., "Status" and "STATUS").
**Expected**: Case-insensitive matching returns the first match. Log a warning if multiple fields match the same normalized name.
**Mitigation**: CustomFieldAccessor._build_index() already uses `.lower().strip()`.

### EC-002: Enum Option Not Found

**Scenario**: Caller passes `"Status": "ActiveX"` but available options are ["Active", "Paused", "Inactive"].
**Expected**: Field is skipped (not written). Response includes `suggestions: ["Active"]` via fuzzy matching.

### EC-003: Stale Enum Options

**Scenario**: Asana project admin adds a new enum option after the task was fetched.
**Expected**: The task fetch at write time includes fresh enum_options. No staleness issue because there is no enum option cache -- options are fetched per request with the task.

### EC-004: GID Passthrough for Enum Fields

**Scenario**: Caller passes `"Status": "1234567890"` (a numeric string that is a valid option GID).
**Expected**: Numeric string treated as GID passthrough, validated against known option GIDs. If valid, used directly. If invalid, treated as unknown option.

### EC-005: Multi-Enum Partial Resolution

**Scenario**: `"Platforms": ["Facebook", "InvalidPlatform", "Google"]` where "InvalidPlatform" is not a valid option.
**Expected**: Resolve Facebook and Google; skip InvalidPlatform. Write the two valid options. Report partial resolution in field_results.

### EC-006: Tag Name Ambiguity

**Scenario**: Multiple tags in the workspace have the same name (Asana allows duplicate tag names).
**Expected**: Use the first match by creation order (Asana default sort). Log a warning about ambiguity.

### EC-007: Concurrent Write to Same Entity

**Scenario**: Two API requests write different fields to the same entity simultaneously.
**Expected**: Both succeed (Asana's custom field update is field-level, not task-level lock). Last write wins for overlapping fields. No server-side coordination needed.

### EC-008: Writing to a Completed/Closed Task

**Scenario**: Caller writes fields to a task that has been marked complete in Asana.
**Expected**: Write succeeds. Asana allows custom field updates on completed tasks. No special handling needed.

### EC-009: Empty Fields Dict

**Scenario**: `{"fields": {}, "tags_add": ["optimize"]}`.
**Expected**: Skip field write entirely (no Asana update API call), proceed with tag operations.

### EC-010: Automation Infinite Loop

**Scenario**: Write triggers automation A, which writes to the same entity, which triggers automation A again.
**Expected**: AutomationEngine already has depth tracking (AutomationContext.depth) and visited set. The write endpoint fires automations at depth 0; recursive triggers are bounded by existing safeguards.

### EC-011: Task Exists in Multiple Projects

**Scenario**: An Asana task is a member of multiple projects, including the entity type's project.
**Expected**: Membership check passes if ANY membership matches the entity type's project GID. Task may legitimately exist in multiple projects.

### EC-012: People Field User GID Validation

**Scenario**: Caller passes invalid user GIDs in a people field.
**Expected**: Asana API will reject invalid user GIDs with a 400 error. Catch and report as field error. This is a known limitation: the write endpoint does not pre-validate user GIDs.

---

## Success Criteria

### SC-001: Core Write Path

| Test | Pass Criteria |
|------|---------------|
| Write text, number, enum, multi_enum, date fields to an offer | All 5 field types successfully written; values match on re-read |
| Write with field name not found | Response includes `fields_skipped` with fuzzy suggestions |
| Write with enum value not found | Response includes `fields_skipped` with available options |
| Write with type mismatch (number field, string value) | 422 or field reported as skipped with type error |
| Write with all fields invalid | 422 `NO_VALID_FIELDS` |
| Partial write (3 valid fields, 1 invalid) | 200, 3 written, 1 skipped |

### SC-002: Tag Operations

| Test | Pass Criteria |
|------|---------------|
| Add tag by name | Tag added to task; tag_results shows success |
| Remove tag by name | Tag removed from task; tag_results shows success |
| Add tag by GID | Tag added directly; no name resolution |
| Tag name not found | tag_results shows failed with error detail |
| Add already-present tag | Idempotent success |

### SC-003: Authentication and Authorization

| Test | Pass Criteria |
|------|---------------|
| Valid S2S JWT | 200 success |
| No auth header | 401 MISSING_AUTH |
| PAT token | 401 SERVICE_TOKEN_REQUIRED |
| Expired JWT | 401 |
| Unknown entity type | 404 UNKNOWN_ENTITY_TYPE with available types |
| Valid type, invalid GID | 404 TASK_NOT_FOUND |
| Valid type, GID in wrong project | 404 ENTITY_TYPE_MISMATCH |

### SC-004: Automation Integration

| Test | Pass Criteria |
|------|---------------|
| Write with trigger_automations=true | automations_triggered >= 0 in response |
| Write with trigger_automations=false | automations_triggered == 0, no engine call |
| Automation failure | Write succeeds; automation errors logged and in response |

### SC-005: Error Handling

| Test | Pass Criteria |
|------|---------------|
| Asana 429 | 429 returned with Retry-After |
| Asana 500 | 502 ASANA_UPSTREAM_ERROR |
| Asana timeout | 504 ASANA_TIMEOUT |
| Empty request body | 422 EMPTY_REQUEST |

### SC-006: Observability

| Test | Pass Criteria |
|------|---------------|
| Successful write | `entity_write_request` and `entity_write_complete` logs present with request_id, caller_service, duration_ms |
| Failed write | `entity_write_error` log present with error code |

---

## Out of Scope

| Item | Reason | Potential Future Work |
|------|--------|----------------------|
| Bulk write (multiple entities per request) | Complexity disproportionate to v1 value. Write one entity at a time. | v2: batch endpoint |
| Task name/assignee/due date writes | These are Asana core fields, not custom fields. Different API path. | Could add as separate FR |
| Section move via write endpoint | Section changes have complex automation implications (pipeline conversion). Use dedicated endpoint. | Dedicated `POST /api/v1/entity/{type}/{gid}/move` |
| Subtask creation/management | Out of scope for field write API | Separate endpoint family |
| Tag creation (create new tag if name not found) | Risk of tag proliferation. Require tags to pre-exist. | Could add `auto_create_tags: true` param |
| Per-entity authorization (role-based write permissions) | v1 trusts all authenticated S2S callers | v2: scope-based authorization |
| Write-through cache invalidation | DataFrameCache is read-path; write endpoint does not invalidate it | Could add cache invalidation hook |
| Holder type writes | Holders are structural containers, not typically targets for external writes | Extend WRITABLE_ENTITY_TYPES if needed |
| Webhook-triggered write confirmation | Writing does not emit webhooks back to the caller | Could add webhook notification |

---

## Implementation Hints (Non-Prescriptive)

These are observations for the Architect, not requirements.

1. **EntityWriteService**: A new service class analogous to EntityService that encapsulates the fetch-validate-resolve-write-automate pipeline. Keeps the route handler thin.

2. **Field Resolution Bridge**: Extract the field resolution logic from FieldSeeder into a reusable component. FieldSeeder.write_fields_async() lines 447-568 contain the exact pattern needed: fetch task with custom_fields and enum_options, build accessor, match fields, resolve enums, call update_async.

3. **Tag Resolution Gap**: TagsClient has add_to_task/remove_from_task (GID-based) but no name-to-GID lookup. Need a workspace tag name resolver. Consider adding `resolve_tag_name_async(workspace_gid, name)` to TagsClient or a TagResolver service.

4. **Automation Integration**: The AutomationEngine expects a SaveResult from SaveSession. For the write endpoint, construct a minimal synthetic SaveResult or introduce a simpler `evaluate_for_entity_async(entity, client, event_type)` method.

5. **Route Registration**: Follow the existing pattern in `api/main.py` -- add `entity_write_router` to the router list.

---

## Stakeholder Alignment Record

| Stakeholder | Concern | Resolution |
|-------------|---------|------------|
| autom8_data team | Need write access for computed insights pushback | Primary consumer; endpoint designed for their client pattern |
| Operations | Automation parity between manual and API writes | FR-WRITE-011 ensures automation trigger on write |
| Security | Write access scope | NFR-WRITE-003: S2S only, no PAT; audit logging via caller_service |
| Platform | Asana API rate impact | NFR-WRITE-002: endpoint-level rate limit; 2-3 API calls per write request |

---

## Open Questions

None. All blocking questions resolved during stakeholder interview (6 rounds, 22 decisions).

---

## Stakeholder Interview Amendments (2026-02-11)

The following amendments supersede conflicting sections in the original PRD.

### AMENDMENT A: HTTP Method Change

**Original**: PUT /api/v1/entity/{entity_type}/{gid}
**Amended**: **PATCH** /api/v1/entity/{entity_type}/{gid}

Rationale: PATCH is semantically correct for partial updates. Only specified fields are modified; unspecified fields remain unchanged.

### AMENDMENT B: Field Name Dual Resolution

**Original**: Asana display names only ("Weekly Ad Spend")
**Amended**: **Accept both** Python descriptor names (`weekly_ad_spend`) AND Asana display names ("Weekly Ad Spend").

Resolution order:
1. Check entity model descriptor registry (O(1) dict lookup by snake_case name)
2. If no descriptor match, fall through to CustomFieldAccessor (case-insensitive display name scan)

### AMENDMENT C: Core Fields Included

**Original**: Custom fields only (core fields explicitly out of scope)
**Amended**: **Core fields included** in the same `fields` dict. Core fields (`name`, `assignee`, `due_on`, `completed`, `notes`) and custom fields are sent to Asana in a single `PUT /tasks/{gid}` call.

- Core fields resolved first by known key set (hardcoded list)
- Remaining keys treated as custom field names
- `completed` field passed through with no special handling (Asana manages completion semantics)
- Dependencies are NOT included (different Asana API endpoint)
- Asana API confirmed: core fields + custom_fields all go in the same `data` block

### AMENDMENT D: Tags Deferred to v1.1

**Original**: FR-WRITE-009, FR-WRITE-010 (tag name resolution + add/remove) as MUST
**Amended**: Tags are **DEFERRED to v1.1**. `tags_add` and `tags_remove` removed from v1 request schema.

Rationale: Tags require a new name-to-GID resolution service that doesn't exist. Core field + custom field writes are the primary unlock. Tags can follow as a fast-follow.

### AMENDMENT E: Automations Deferred Entirely

**Original**: FR-WRITE-011 (post-write automation trigger) as SHOULD
**Amended**: Automations are **DEFERRED entirely**. Automations are a separate concern from writes.

Rationale: The write endpoint should be a clean, focused data mutation API. Automation wiring (SaveSession integration, AutomationEngine evaluation) is a distinct initiative. Asana's own webhook/rules system can handle trigger-on-change if configured.

`trigger_automations` parameter removed from v1 request schema. `automations_triggered` and `automations_errors` removed from v1 response schema.

### AMENDMENT F: Request-Level List Mode

**New requirement** (not in original PRD):

The request body SHALL accept an optional `list_mode` parameter:
- `list_mode: "replace"` (default) — list-type field values replace the entire field
- `list_mode: "append"` — list-type field values are appended to existing values

Applies to:
- `multi_enum` fields: append adds new options to existing selection
- `TextListField` fields (e.g., `asset_id`): server-side parse + append + dedup

TextListField append behavior:
1. Read current text value from Asana
2. Split on delimiter (comma or configurable)
3. Append new value(s) if not already present
4. Re-join and write back

### AMENDMENT G: Dynamic Entity Registry

**New requirement** (not in original PRD):

Replace hardcoded `WRITABLE_ENTITY_TYPES` set with a **dynamic `EntityRegistry`**:
- Auto-discovers writable entity types at startup by introspecting entity models
- Any entity model with `CustomFieldDescriptor` properties is auto-registered
- Provides: entity_type -> project_gid, descriptor index, core field definitions
- Replaces `EntityProjectRegistry` as the canonical entity type registry
- EntityService remains as a separate service layer (wraps registry with PAT acquisition + validation)

### AMENDMENT H: Shared FieldResolver Extraction

**New requirement** (not in original PRD):

Extract field resolution logic from `FieldSeeder` into a shared **`FieldResolver`** utility:
- Enum name-to-GID resolution
- Field name matching (case-insensitive)
- Type validation
- Used by both FieldSeeder (pipeline automation) and FieldWriteService (REST API)

### AMENDMENT I: Fire-and-Forget Cache Invalidation

**Original**: Cache invalidation out of scope
**Amended**: After successful write, emit a `MutationEvent` for fire-and-forget cache invalidation via existing `MutationInvalidator` pattern. Non-blocking.

### AMENDMENT J: Response Re-fetch Optional

**Original**: Always return `updated_fields` in response
**Amended**: Default to echo-back (return values as sent). Support `?include_updated=true` query param to re-fetch from Asana and return current field values.

### AMENDMENT K: Revised API Contract

```
PATCH /api/v1/entity/{entity_type}/{gid}?include_updated=false
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

Response (200):
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

### Removed from v1

| Feature | Status | Rationale |
|---------|--------|-----------|
| `tags_add` / `tags_remove` | Deferred v1.1 | Requires new name→GID resolver |
| `trigger_automations` | Deferred entirely | Separate concern |
| `automations_triggered` / `automations_errors` in response | Removed | No automation support in v1 |
| `tag_results` in response | Removed | No tag support in v1 |

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-entity-write-api.md` | Yes (Read-verified 2026-02-11) |
| Stakeholder Interview | 6 rounds, 22 decisions | Completed 2026-02-11 |
