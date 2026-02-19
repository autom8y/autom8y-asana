# PRD: EntityScope Invocation Layer

```yaml
id: PRD-ENTITY-SCOPE-001
status: draft
author: requirements-analyst
date: 2026-02-19
impact: high
impact_categories: [api_contract, cross_service]
complexity: MODULE
sprints: TBD (Pythia orchestration)
```

## 1. Problem Statement

All three batch workflows (InsightsExportWorkflow, ConversationAuditWorkflow, PipelineTransitionWorkflow) operate exclusively in "enumerate everything" mode. Every invocation scans an entire Asana project or set of sections and processes every entity found. There is no mechanism to target a single entity by GID, filter to a subset, perform a dry run, or invoke a workflow on demand.

This creates four concrete pain points:

1. **No on-demand invocation**: When an account manager reports a stale attachment on a single Offer, the only remedy is to wait for the next scheduled run (daily for insights-export, weekly for conversation-audit) or manually trigger the entire Lambda. Processing hundreds of entities to fix one is wasteful and slow.

2. **No developer CLI**: Debugging a workflow failure for a specific entity requires either modifying source code to hardcode a GID, or invoking the Lambda handler directly with a crafted JSON event. Neither is documented, neither is safe, and both bypass validation.

3. **No dry-run capability**: There is no way to verify what a workflow *would* process without actually executing writes (uploading attachments, triggering lifecycle transitions). This makes pre-production validation and incident investigation unnecessarily risky.

4. **No API surface for workflow invocation**: The FastAPI application exposes 13 route modules but none can trigger a workflow. Any future integration (webhooks, UI-driven reruns, cross-service orchestration) would need to shell out to Lambda or duplicate workflow construction logic.

### Current State

| Component | Status | Limitation |
|-----------|--------|------------|
| `WorkflowAction` (ABC) | Production | `execute_async(params)` receives flat dict; no entity scoping concept |
| `WorkflowHandlerConfig` | Production | Whitelist merge: only keys present in `default_params` pass through |
| `WorkflowRegistry` | Production | Dict-based lookup, used by scheduler only |
| Lambda handlers | Production (2 of 3) | `insights_export.py`, `conversation_audit.py` -- EventBridge scheduled |
| FastAPI API | Production (13 routes) | No workflow invocation endpoint |
| `.env/local` | Exists | Missing `AUTOM8_DATA_URL` and `AUTOM8_DATA_API_KEY` for local data service connectivity |

### Why Now

- Both production workflows (insights-export, conversation-audit) are stable and the WorkflowAction pattern is proven. Adding entity scoping is a natural extension, not a rewrite.
- The Asana service already runs FastAPI with dual-mode auth (JWT + PAT). Adding an invoke endpoint reuses existing infrastructure.
- Developer productivity: the most common debugging task -- "rerun this one entity" -- currently requires disproportionate effort.

---

## 2. Stakeholders & Consumers

| Stakeholder | Role | Interest |
|-------------|------|----------|
| Developers | Primary consumer | CLI invocation for debugging, testing, and on-demand reruns |
| Operations | System owner | API-triggered reruns for incident response without full Lambda cycles |
| Account Managers | Indirect beneficiary | Faster resolution when a single entity's attachment is stale |
| Platform | Infrastructure | Consistent invocation surface for future orchestration (webhooks, Step Functions) |

---

## 3. Scope

### 3.1 In-Scope

| Feature | Description |
|---------|-------------|
| EntityScope abstraction | Frozen dataclass for scoping workflow execution to specific entities |
| Handler factory extension | `create_workflow_handler` passes EntityScope fields as first-class params |
| Workflow entity resolution | Each workflow checks for `entity_ids` in params and bypasses enumeration |
| FastAPI invoke endpoint | `POST /api/v1/workflows/{workflow_id}/invoke` with JWT auth |
| Developer CLI | `scripts/invoke_workflow.py` + `just invoke` recipe |
| Local env seeding | `.env/local` additions for data service connectivity |

### 3.2 Out of Scope

| Item | Rationale |
|------|-----------|
| PipelineTransitionWorkflow entity_ids support | No Lambda handler exists yet; entity scoping for this workflow is deferred until Lambda handler is created |
| ServiceAuthClient automatic token exchange | Future work; developers use manual JWT or AUTH_DEV_MODE for now |
| Step Functions / queue-based fan-out | Premature for current scale (< 500 entities per workflow run) |
| Batch GID invocation (multiple GIDs in single request) | Phase 2; v1 supports single GID targeting only per invocation |
| Workflow scheduling changes | EventBridge schedules remain unchanged |
| New workflow creation | Only existing workflows are extended |

---

## 4. User Stories

### US-01: Developer targets a single entity via CLI

**As a** developer debugging a stale insights attachment,
**I want to** run `just invoke insights-export --gid=1205925604226368 --dry-run`,
**So that** I can verify the workflow would process this specific Offer without executing writes.

**Acceptance Criteria:**
- AC-01.1: CLI accepts `--gid` argument with a single Asana GID
- AC-01.2: CLI accepts `--dry-run` flag that prevents write operations (attachment upload, deletion)
- AC-01.3: CLI prints structured output showing entity metadata and processing outcome
- AC-01.4: CLI returns non-zero exit code on failure
- AC-01.5: When `--dry-run` is omitted, the workflow executes normally (writes occur)

### US-02: Developer invokes workflow for a single entity (live)

**As a** developer responding to an account manager report,
**I want to** run `just invoke insights-export --gid=1205925604226368`,
**So that** the insights attachment for that specific Offer is regenerated immediately.

**Acceptance Criteria:**
- AC-02.1: Workflow processes only the specified entity (no enumeration of full project)
- AC-02.2: Workflow result is printed to stdout as JSON
- AC-02.3: All normal workflow behavior occurs (data fetch, attachment upload, old attachment cleanup)

### US-03: Operations invokes workflow via API

**As an** operations engineer,
**I want to** `POST /api/v1/workflows/insights-export/invoke` with a JWT and entity_ids,
**So that** I can trigger a targeted rerun without Lambda access.

**Acceptance Criteria:**
- AC-03.1: Endpoint requires JWT authentication (existing `get_auth_context` dependency)
- AC-03.2: Request body accepts `entity_ids`, `dry_run`, and optional `params` override
- AC-03.3: Response returns `WorkflowResult` as JSON
- AC-03.4: Invalid `workflow_id` returns 404
- AC-03.5: Empty `entity_ids` list returns 400 validation error
- AC-03.6: Unauthenticated request returns 401

### US-04: Existing scheduled runs are unaffected

**As** the platform team,
**I want** existing EventBridge-triggered Lambda invocations to continue working identically,
**So that** this feature introduces zero regression risk.

**Acceptance Criteria:**
- AC-04.1: EventBridge events with no `entity_ids` field trigger full enumeration (existing behavior)
- AC-04.2: No changes to Lambda handler entry points (`insights_export.handler`, `conversation_audit.handler`)
- AC-04.3: WorkflowHandlerConfig `default_params` whitelist behavior unchanged for existing keys
- AC-04.4: All existing workflow tests pass without modification

---

## 5. Functional Requirements

### FR-001: EntityScope Abstraction

**Priority: MUST**

| ID | Requirement |
|----|------------|
| FR-001.1 | `EntityScope` is a frozen dataclass in `autom8_asana.automation.workflows.scope` |
| FR-001.2 | Fields: `entity_ids: tuple[str, ...] = ()`, `section_filter: frozenset[str] = frozenset()`, `limit: int | None = None`, `dry_run: bool = False` |
| FR-001.3 | `EntityScope.from_event(event: dict) -> EntityScope` factory method constructs from Lambda event or API request body |
| FR-001.4 | `EntityScope.from_event({})` returns default scope (empty entity_ids, no filters, dry_run=False) -- equivalent to current full-enumeration behavior |
| FR-001.5 | `EntityScope.has_entity_ids` property returns `bool(self.entity_ids)` |
| FR-001.6 | `EntityScope` is importable from `autom8_asana.automation.workflows` package |
| FR-001.7 | EntityScope is workflow-agnostic: it does not contain workflow-specific logic |

### FR-002: Handler Factory Extension

**Priority: MUST**

| ID | Requirement |
|----|------------|
| FR-002.1 | `create_workflow_handler` constructs `EntityScope.from_event(event)` before param merging |
| FR-002.2 | EntityScope fields (`entity_ids`, `dry_run`, `section_filter`, `limit`) are injected into `params` dict as first-class keys, bypassing the whitelist merge |
| FR-002.3 | Existing `default_params` whitelist merge continues to function for all other event keys |
| FR-002.4 | If `entity_ids` is not present in the event, params contain `entity_ids=()` (empty tuple, not absent) |
| FR-002.5 | If `dry_run` is not present in the event, params contain `dry_run=False` |

### FR-003: Workflow Entity Resolution -- InsightsExportWorkflow

**Priority: MUST**

| ID | Requirement |
|----|------------|
| FR-003.1 | `execute_async` checks `params.get("entity_ids")` at the start of execution |
| FR-003.2 | If `entity_ids` is non-empty: bypass `_enumerate_offers()`, construct offer dicts from GIDs directly (each dict has `gid`, `name=None`, `parent_gid=None`) |
| FR-003.3 | If `entity_ids` is empty or absent: existing enumeration behavior unchanged |
| FR-003.4 | If `params.get("dry_run")` is True: skip attachment upload (`_attachments_client.upload_async`) and old attachment deletion (`_delete_old_attachments`), but still execute data fetch and report composition |
| FR-003.5 | Dry-run results include `metadata.dry_run=True` in the WorkflowResult |
| FR-003.6 | Dry-run results include the composed markdown content in `metadata.report_preview` (truncated to 2000 chars) for the targeted entity |

### FR-004: Workflow Entity Resolution -- ConversationAuditWorkflow

**Priority: MUST**

| ID | Requirement |
|----|------------|
| FR-004.1 | Same entity_ids check pattern as FR-003.1-003.3, applied to `_enumerate_contact_holders()` |
| FR-004.2 | When entity_ids is provided, bypass `_pre_resolve_business_activities()` bulk pre-resolution (single entity does not benefit from bulk) |
| FR-004.3 | Dry-run behavior: skip CSV upload and old attachment deletion, but still fetch CSV data |
| FR-004.4 | Dry-run results include `metadata.dry_run=True` and `metadata.csv_row_count` |

### FR-005: FastAPI Invoke Endpoint

**Priority: MUST**

| ID | Requirement |
|----|------------|
| FR-005.1 | Route: `POST /api/v1/workflows/{workflow_id}/invoke` |
| FR-005.2 | Route module: `src/autom8_asana/api/routes/workflows.py` |
| FR-005.3 | Auth: `Depends(get_auth_context)` -- same JWT/PAT dual-mode as existing routes |
| FR-005.4 | Request body model `WorkflowInvokeRequest`: `entity_ids: list[str]`, `dry_run: bool = False`, `params: dict[str, Any] = {}` |
| FR-005.5 | Validate: `entity_ids` must be non-empty list; return 400 if empty or missing |
| FR-005.6 | Validate: each entity_id must be a numeric string (Asana GID format); return 400 if non-numeric |
| FR-005.7 | Lookup `workflow_id` via `WorkflowRegistry`; return 404 if not found |
| FR-005.8 | Response model `WorkflowInvokeResponse`: wraps `WorkflowResult.to_response_dict()` with additional `request_id` and `invocation_source: "api"` |
| FR-005.9 | Rate limited: 10 requests per minute per client (separate from default 100/min) |
| FR-005.10 | Audit logged: structured log event `workflow_invoke_api` with `workflow_id`, `entity_ids`, `dry_run`, `request_id`, `caller_service` (if JWT) |
| FR-005.11 | WorkflowRegistry must be populated during app startup (lifespan) and available on `app.state.workflow_registry` |
| FR-005.12 | The endpoint constructs workflow instances using the same factory pattern as Lambda handlers (AsanaClient + DataServiceClient) |

### FR-006: Developer CLI

**Priority: MUST**

| ID | Requirement |
|----|------------|
| FR-006.1 | Script: `scripts/invoke_workflow.py` |
| FR-006.2 | CLI interface: `python scripts/invoke_workflow.py <workflow_id> [--gid GID] [--dry-run] [--api-url URL]` |
| FR-006.3 | Justfile recipe: `just invoke workflow_id *args` delegates to `uv run python scripts/invoke_workflow.py {{workflow_id}} {{args}}` |
| FR-006.4 | Primary mode (API): when `--api-url` is provided or API is detected running on localhost:8000, send POST to invoke endpoint |
| FR-006.5 | Fallback mode (direct): when API is not available, construct workflow directly (same factory as Lambda handler) and invoke `execute_async` |
| FR-006.6 | Direct mode requires `ASANA_PAT` and `AUTOM8_DATA_URL` environment variables |
| FR-006.7 | Output: JSON-formatted WorkflowResult to stdout |
| FR-006.8 | Exit code: 0 on success, 1 on workflow failure, 2 on CLI argument error |

### FR-007: Local Environment Seeding

**Priority: SHOULD**

| ID | Requirement |
|----|------------|
| FR-007.1 | `.env/local` must include `AUTOM8_DATA_URL` pointing to local data service (default: `http://localhost:8001`) |
| FR-007.2 | `.env/local` must include `AUTH_DEV_MODE=true` to bypass JWT validation in local development |
| FR-007.3 | Document in `.env/local` comments: data service must be running separately with `AUTH_DEV_MODE=true` |
| FR-007.4 | `AUTOM8_DATA_API_KEY` is NOT seeded because `AUTH_DEV_MODE=true` bypasses token validation on the data service side; the DataServiceClient `_get_token()` gracefully returns None when the env var is unset |

---

## 6. Non-Functional Requirements

### NFR-001: Backward Compatibility

| ID | Requirement | Target |
|----|------------|--------|
| NFR-001.1 | Existing EventBridge Lambda invocations produce identical results | Zero behavioral change for events without `entity_ids` |
| NFR-001.2 | Existing test suite passes without modification | 10,552+ tests pass |
| NFR-001.3 | No changes to WorkflowHandlerConfig constructor signature | Existing Lambda handler configs unchanged |

### NFR-002: Performance

| ID | Requirement | Target |
|----|------------|--------|
| NFR-002.1 | Single-entity invocation via API completes within workflow timeout | < 30s for insights-export (10 table fetches), < 15s for conversation-audit (1 CSV fetch) |
| NFR-002.2 | EntityScope construction overhead | < 1ms (frozen dataclass, no I/O) |
| NFR-002.3 | API endpoint latency overhead (excluding workflow execution) | < 50ms for auth + registry lookup + request parsing |

### NFR-003: Security

| ID | Requirement | Target |
|----|------------|--------|
| NFR-003.1 | Invoke endpoint requires authentication | JWT or PAT via existing `get_auth_context` |
| NFR-003.2 | Rate limiting on invoke endpoint | 10 req/min per client (prevents abuse of write-capable endpoint) |
| NFR-003.3 | Audit logging for all invocations | Structured log with caller identity, workflow_id, entity_ids |
| NFR-003.4 | No new secrets introduced | Uses existing ASANA_PAT and data service auth flow |

### NFR-004: Observability

| ID | Requirement | Target |
|----|------------|--------|
| NFR-004.1 | CloudWatch metric: `WorkflowInvokeCount` with dimensions `{workflow_id, source}` where source is "api", "cli", or "lambda" | Emitted on every invocation |
| NFR-004.2 | Structured log correlation | `request_id` present in all API-invoked workflow logs |
| NFR-004.3 | Dry-run results distinguishable in metrics | `dry_run` dimension on `WorkflowInvokeCount` |

---

## 7. Edge Cases & Failure Modes

### EC-001: Invalid GID

| Scenario | Expected Behavior |
|----------|-------------------|
| GID does not exist in Asana | Workflow processes it; Asana API returns 404; workflow reports it as a failed item in WorkflowResult.errors |
| GID exists but is a different entity type (e.g., passing a Business GID to insights-export which expects Offers) | Workflow attempts resolution; resolution fails (no parent, no phone, no vertical); item is reported as skipped with reason |
| GID is not numeric | API endpoint returns 400 before workflow execution |

### EC-002: Concurrent Invocation

| Scenario | Expected Behavior |
|----------|-------------------|
| Same GID invoked twice concurrently via API | Both invocations run independently. Workflows are idempotent (upload-first pattern ensures latest attachment wins). No locking required. |
| API invoke concurrent with scheduled Lambda run | Same entity may be processed twice. Acceptable: idempotent behavior ensures no data corruption. |

### EC-003: Dry-Run Boundaries

| Scenario | Expected Behavior |
|----------|-------------------|
| Dry-run with valid GID | Data is fetched, report/CSV is composed, but no attachment upload or deletion occurs. Result includes preview. |
| Dry-run with invalid GID | Same as non-dry-run invalid GID: failure reported in WorkflowResult.errors |
| Dry-run flag on full enumeration (no entity_ids) | Supported: enumerates all entities but skips all writes. Useful for "what would this run do?" verification. |

### EC-004: WorkflowRegistry Empty or Missing Workflow

| Scenario | Expected Behavior |
|----------|-------------------|
| Registry not populated at startup | 500 error from endpoint; structured log `workflow_registry_not_initialized` |
| Valid workflow_id but workflow fails validation | 200 response with `status: skipped`, `reason: validation_failed` (matches existing Lambda behavior) |
| `pipeline-transition` requested via API | 404: not registered in API-accessible registry (no Lambda handler, excluded from scope) |

### EC-005: Data Service Unavailable

| Scenario | Expected Behavior |
|----------|-------------------|
| `AUTOM8_DATA_URL` not configured in local env | DataServiceConfig defaults to `http://localhost:8000`; connection refused error; workflow fails with circuit breaker open |
| Data service circuit breaker open | Workflow `validate_async()` returns validation error; workflow is skipped (not failed) |
| Data service returns 500 for specific entity | Retry handler attempts retries per RetryConfig; if exhausted, entity reported as failed |

### EC-006: Authentication Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| CLI invocation without running API server | CLI falls back to direct invocation mode; uses ASANA_PAT from environment |
| API invocation with PAT auth (not JWT) | Accepted: dual-mode auth supports both. PAT-authenticated requests use the caller's token for Asana operations. |
| `AUTH_DEV_MODE=true` in production | Not our concern; AUTH_DEV_MODE is an API config flag, not something this feature introduces |

---

## 8. Success Criteria

| ID | Criterion | Verification Method |
|----|-----------|-------------------|
| SC-1 | `just invoke insights-export --gid=1205925604226368 --dry-run` returns entity metadata without executing writes | Manual test: run command, verify no new attachment on Asana task, verify JSON output includes `dry_run: true` and `report_preview` |
| SC-2 | `just invoke insights-export --gid=1205925604226368` processes single offer, uploads attachment | Manual test: run command, verify new attachment appears on Asana task |
| SC-3 | Existing EventBridge-triggered Lambda behavior unchanged (no regression) | Automated: all existing tests pass (`just test`); deploy to staging and verify scheduled run produces same results |
| SC-4 | `POST /api/v1/workflows/insights-export/invoke` with JWT returns WorkflowResult | Integration test: POST with valid JWT, assert 200 response with expected WorkflowResult structure |
| SC-5 | Invalid workflow_id returns 404 | Unit test: POST to `/api/v1/workflows/nonexistent/invoke`, assert 404 |
| SC-6 | Unauthenticated request returns 401 | Unit test: POST without Authorization header, assert 401 with `WWW-Authenticate: Bearer` |
| SC-7 | `entity_ids=[]` (empty list) returns 400 validation error | Unit test: POST with `{"entity_ids": []}`, assert 400 |
| SC-8 | conversation-audit workflow also supports entity_ids targeting | Integration test: invoke with single ContactHolder GID, verify CSV attachment produced |

---

## 9. Dependencies

| Dependency | Type | Status | Risk |
|------------|------|--------|------|
| `WorkflowAction` ABC | Internal | Stable (production) | Low: additive changes only (no signature changes to base class) |
| `WorkflowRegistry` | Internal | Stable (production) | Low: used as-is for lookup |
| `WorkflowHandlerConfig` + `create_workflow_handler` | Internal | Stable (production) | Medium: requires modification to pass EntityScope fields through whitelist |
| FastAPI dual-mode auth (`get_auth_context`) | Internal | Stable (production) | Low: reused as-is |
| `DataServiceClient` | Internal | Stable (production) | Low: no changes required |
| `AsanaClient` | Internal | Stable (production) | Low: no changes required |
| `.env/local` | Local dev | Exists but incomplete | Low: additive only |
| `autom8y-auth` SDK | External | Installed | Low: used by existing auth flow |

---

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Handler factory whitelist bypass introduces unintended param injection | Low | Medium | EntityScope fields are a closed set (4 fields); explicitly named, not open-ended. Unit test: verify only EntityScope fields bypass whitelist. |
| WorkflowRegistry not populated during app startup | Low | High | Fail-fast: if `app.state.workflow_registry` is None, endpoint returns 503 with clear error. Add startup health check. |
| Dry-run flag accidentally left in production invocation | Low | Low | Dry-run is explicit opt-in (default False). API response clearly labels `dry_run: true`. No silent dry-run. |
| Single-entity invocation reveals different behavior than batch (e.g., missing parent_gid from enumeration) | Medium | Medium | FR-003.2 specifies `parent_gid=None` for GID-constructed entities; existing `_resolve_offer` handles None parent_gid by fetching the task. Same code path, just with an extra API call. |
| Rate limit on invoke endpoint too restrictive for batch reruns | Low | Low | 10/min is sufficient for on-demand single-entity reruns. Batch reruns should use Lambda. Rate limit is configurable. |
| `AUTOM8_DATA_API_KEY` confusion in local dev | Medium | Low | FR-007.4 explicitly documents that AUTH_DEV_MODE bypasses token validation. DataServiceClient._get_token() returns None gracefully. |

---

## 11. Implementation Guidance (Non-Normative)

This section provides architectural hints for the downstream Architect and Principal Engineer. These are suggestions, not requirements.

### EntityScope Location

`src/autom8_asana/automation/workflows/scope.py` -- adjacent to `base.py` and `registry.py`. Exported from `__init__.py`.

### Handler Factory Change Pattern

The whitelist merge in `create_workflow_handler._execute` (lines 121-124 of `workflow_handler.py`) should be extended with a pre-merge step that injects EntityScope fields unconditionally:

```
scope = EntityScope.from_event(event)
params["entity_ids"] = scope.entity_ids
params["dry_run"] = scope.dry_run
# ... then existing whitelist merge for default_params keys
```

### Workflow Entity Resolution Pattern

A mixin or utility function `resolve_entity_ids_or_enumerate` could reduce duplication across workflows, but given only 2 workflows in scope, inline conditionals in each `execute_async` are acceptable for v1.

### WorkflowRegistry Population at Startup

The `lifespan` context manager in `api/lifespan.py` should construct and register workflows during startup, storing the registry on `app.state.workflow_registry`. This requires access to AsanaClient and DataServiceClient at startup time.

### CLI Health Check

The CLI should attempt `GET http://localhost:8000/health` before deciding API vs. direct mode. Timeout: 1 second.

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8y-asana/docs/requirements/PRD-entity-scope-invocation.md` | Yes |
