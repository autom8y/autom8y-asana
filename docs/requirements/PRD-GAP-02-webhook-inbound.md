---
artifact_id: PRD-GAP-02-webhook-inbound
title: "Webhook Inbound Event Handler"
created_at: "2026-02-07T15:30:00Z"
revised_at: "2026-02-07T16:00:00Z"
author: requirements-analyst
status: approved
complexity: MODULE
impact: high
impact_categories: [security, api_contract]
source: docs/GAPS/Q1/GAP-02-webhook-inbound.md
related_gaps:
  - GAP-03 (Event Routing -- depends on this PRD)
  - GAP-07 (Adapter Expansion -- depends on this PRD)
related_adrs:
  - ADR-0005 (Pydantic v2 with extra="ignore")
stakeholders:
  - architect
  - principal-engineer
  - qa-adversary
success_criteria:
  - id: SC-003
    description: "Inbound task payloads are parsed into the existing Task Pydantic model via model_validate"
    testable: true
    priority: must-have
    verification: "Raw Asana task JSON (equivalent to GET /tasks/{gid}) round-trips through Task.model_validate without data loss on documented fields"
  - id: SC-004
    description: "Endpoint responds 200 within the Asana Rules delivery timeout regardless of payload size"
    testable: true
    priority: must-have
    verification: "Response time < 1s for a single task payload; cache invalidation and dispatch happen after response"
  - id: SC-006
    description: "Structured log entry emitted for every accepted inbound request with task GID and action metadata"
    testable: true
    priority: should-have
    verification: "Log output contains webhook_task_received with task GID, resource_type, and modified_at"
  - id: SC-007
    description: "Cache invalidation deletes stale entries when inbound modified_at is newer than cached version"
    testable: true
    priority: must-have
    verification: "When inbound task modified_at > cached modified_at, TASK/SUBTASKS/DETECTION cache entries for that GID are deleted; when inbound <= cached, no invalidation occurs"
  - id: SC-008
    description: "Requests with missing or invalid URL token are rejected with 401"
    testable: true
    priority: must-have
    verification: "POST without token param returns 401; POST with wrong token returns 401; POST with correct token returns 200"
schema_version: "1.0"
---

# PRD: Webhook Inbound Event Handler (GAP-02)

## Revision History

| Date | Change | Reason |
|------|--------|--------|
| 2026-02-07 | Initial draft | PRD creation |
| 2026-02-07 | V1 rewrite for Asana Rules integration model | Stakeholder interview confirmed V1 uses Asana Rules (outbound HTTP actions), not Asana Webhooks API. Rewrites auth model, payload shape, and defers handshake/HMAC to V2. |

## Problem Statement

autom8_asana can manage Asana webhook subscriptions (create, update, delete) and can verify inbound signatures, but there is nothing listening for real-time task change notifications. When a task is moved, a field is changed, or a tag is added, the system has no way to react.

This is the single largest gap blocking the monolith replacement. The legacy system's Lambda-based handler (`handler.py`) is the nerve center of all reactive Asana automation. Without an inbound handler, autom8_asana can only act through polling or explicit API calls, leaving the system blind to real-time Asana changes.

**V1 Integration Model: Asana Rules.** Stakeholder interviews confirmed that V1 will use Asana Rules -- the built-in automation feature that sends outbound HTTP POST requests when rule conditions are met. An Asana Rule configured with an "Send external request" action fires a POST containing the full task JSON (equivalent to a GET /tasks/{gid} response) to our endpoint. This is simpler than the Asana Webhooks API: there is no subscription management, no handshake protocol, and no HMAC signing. Authentication is via a URL token in the query parameter.

**V2 Evolution: Asana Webhooks API.** The full Webhooks API (handshake protocol, HMAC-SHA256 signing, event envelope with `events` array, subscription lifecycle) is planned as a V2 evolution once the inbound handler proves the dispatch seam and cache invalidation patterns. All V2 items are tracked in the V2 Roadmap section below.

**Business impact**: Every minute a task change goes unhandled is a minute of stale data, missed automation triggers, and manual intervention that the legacy system handles automatically.

## Goals

1. **Receive**: Accept Asana Rules HTTP POSTs via a FastAPI endpoint at `/api/v1/webhooks/inbound`.
2. **Verify**: Authenticate every inbound request by validating the URL token query parameter (`?token=secret`) against the configured environment variable, using timing-safe comparison.
3. **Parse**: Deserialize the full Asana task JSON payload into the existing `Task` Pydantic model (reuse, not new models) for downstream consumption.
4. **Acknowledge fast**: Return 200 immediately. Never block the response on event processing or cache invalidation.
5. **Configure token via env var**: Read the authentication token from an environment variable at startup. No durable secret storage required for V1.
6. **Invalidate stale cache**: When the inbound task's `modified_at` is newer than the cached version, delete the stale cache entries for that task GID.
7. **Expose a dispatch seam**: Provide a clean internal interface where GAP-03 (Event Routing) can plug in handlers without modifying the inbound layer.

## Non-Goals

1. **Event processing logic** -- This PRD covers receipt, verification, parsing, and cache invalidation. What happens AFTER an event is dispatched (AutomationEngine bridging, external emission) is GAP-03 scope.
2. **Webhook subscription lifecycle management** -- V1 uses Asana Rules (configured in Asana UI), not Webhooks API subscriptions.
3. **Multi-tenant webhook routing** -- One Asana workspace, one set of rules. Multi-workspace fanout is future work.
4. **Event persistence or replay** -- Events are dispatched in-memory to registered handlers. Durable queuing (SQS, Redis Streams) is a GAP-03 decision.
5. **Cross-container coordination** -- If multiple ECS containers receive the same Rule action POST, each processes independently. Coordination is deferred (see INTEGRATE-dataframe-materialization Option D).
6. **AutomationEngine integration** -- Bridging inbound events to `AutomationEngine.evaluate_async()` requires solving the SaveResult impedance mismatch, which is GAP-03 territory.
7. **Asana Webhooks API (handshake, HMAC, event envelope)** -- Deferred to V2. See V2 Roadmap section.

## User Stories

### US-02: Token Verification
**As** a security-conscious service,
**I want** every inbound POST to be verified by checking the URL token query parameter,
**So that** unauthorized requests are rejected before any processing occurs.

**Acceptance criteria**:
- Requests with missing `token` query parameter return 401.
- Requests with empty `token` query parameter return 401.
- Requests with an incorrect token value return 401.
- Requests with the correct token value proceed to parsing.
- Timing-safe comparison is used to prevent timing attacks (`hmac.compare_digest` or `secrets.compare_digest`).
- The expected token value is read from an environment variable at startup.

### US-03: Task Payload Parsing
**As** a downstream event handler,
**I want** inbound Asana task payloads parsed into the existing typed `Task` Pydantic model,
**So that** I can work with structured task data (assignee, projects, custom fields, modified_at) without raw dict manipulation.

**Acceptance criteria**:
- The full task JSON body from the Asana Rules POST is deserialized via `Task.model_validate()`.
- The existing `Task` model (extending `AsanaResource`, `extra="ignore"`) is reused directly -- no new task models are created.
- A thin request wrapper model is added only to validate the inbound request structure (e.g., optional metadata from Asana Rules alongside the task data).
- Unknown fields in the task payload are silently ignored (per ADR-0005 `extra="ignore"` convention).

### US-04: Fast Acknowledgment
**As** a webhook consumer under Asana Rules' delivery contract,
**I want** the endpoint to return 200 as quickly as possible,
**So that** Asana does not mark the Rule action as failed due to slow responses.

**Acceptance criteria**:
- The HTTP response is sent before any event processing or cache invalidation begins.
- Processing happens asynchronously via FastAPI BackgroundTasks.

### US-05: Dispatch Seam
**As** the architect of GAP-03 (Event Routing),
**I want** the inbound handler to call a well-defined internal interface with the parsed task,
**So that** I can implement routing, filtering, and handler dispatch without modifying the inbound layer.

**Acceptance criteria**:
- A callable interface (protocol or abstract base) accepts the parsed `Task` model.
- The default implementation is a no-op (log and discard) so the inbound layer is deployable before GAP-03.
- Replacing the no-op with a real dispatcher requires no changes to the inbound route or verification logic.

### US-06: Cache Invalidation
**As** a data consumer relying on cached task state,
**I want** stale cache entries to be automatically deleted when an inbound task notification arrives with a newer `modified_at` timestamp,
**So that** subsequent reads fetch fresh data from Asana instead of serving stale cache entries.

**Acceptance criteria**:
- When the inbound task's `modified_at` is more recent than the cached version's `modified_at`, the TASK, SUBTASKS, and DETECTION cache entries for that GID are deleted.
- When the inbound task's `modified_at` is equal to or older than the cached version, no invalidation occurs (the cache is already current or newer).
- When there is no cached version for the task GID, no invalidation occurs (nothing to invalidate).
- Cache invalidation failures are logged but do not affect the HTTP response or downstream dispatch.
- Cache invalidation runs asynchronously (inside the BackgroundTask), not in the request path.

## Functional Requirements

### FR-01: Webhook Endpoint (Must Have)
The system SHALL expose an HTTP POST endpoint at `/api/v1/webhooks/inbound` for receiving Asana Rules action payloads.
- The endpoint is publicly reachable (Asana Rules sends outbound HTTP).
- The endpoint does NOT use the standard JWT/PAT authentication middleware (URL token auth only).
- V1 receives full task JSON from Asana Rules. V2 will extend this to handle Webhooks API event envelopes.

### FR-03: Token Verification (Must Have)
The system SHALL verify the `token` query parameter on every inbound POST.
- Read the expected token from an environment variable (e.g., `WEBHOOK_INBOUND_TOKEN`) at startup.
- Compare the request's `?token=` parameter against the expected value using timing-safe comparison.
- Reject requests with missing, empty, or incorrect tokens with 401 before any parsing or dispatch.

### FR-04: Inbound Task Model (Must Have)
The system SHALL reuse the existing `Task` model (`src/autom8_asana/models/task.py`) for deserializing inbound payloads.
- The existing `Task` model extends `AsanaResource` with `extra="ignore"`, which handles unknown fields from the Asana Rules payload.
- A thin request wrapper model MAY be added to capture any Asana Rules metadata (e.g., rule name, trigger type) that arrives alongside the task data, but the core task data MUST be parsed into the existing `Task` model.
- No new task-specific models are required -- the Asana Rules payload is equivalent to the GET /tasks/{gid} response shape.

### FR-05: Async Event Dispatch (Must Have)
The system SHALL dispatch the parsed task asynchronously, after the HTTP response.
- The response to Asana Rules must not be blocked by event processing or cache invalidation.
- Use FastAPI BackgroundTasks as the async dispatch mechanism.

### FR-06: Token Configuration (Must Have)
The system SHALL read the webhook authentication token from an environment variable.
- The environment variable name should be configurable (default: `WEBHOOK_INBOUND_TOKEN`).
- If the environment variable is not set at startup, the endpoint should refuse to start or return 503 for all requests, with a clear error log.

### FR-07: Dispatch Interface (Should Have)
The system SHALL define a typed interface (protocol) for event dispatch that GAP-03 can implement.
- The interface accepts a parsed `Task` model instance.
- The default implementation logs the task GID and discards (no-op).
- Replacing the no-op with a real dispatcher requires no changes to the inbound route or verification logic.

### FR-08: Observability (Should Have)
The system SHALL emit structured logs for:
- Token verification failures (request metadata, NOT the token value itself).
- Accepted inbound requests (task GID, resource_type, modified_at).
- Cache invalidation actions (task GID, whether invalidation occurred, reason).
- Dispatch errors (if the dispatch interface raises).

### FR-09: Payload Edge Case Handling (Should Have)
The system SHALL handle edge cases in the Asana Rules task payload gracefully:
- Empty JSON body (respond 200 after token verification, log warning, no dispatch).
- Non-JSON body (respond 400 with error).
- Valid JSON but missing `gid` field (respond 400 -- not a valid task).
- Missing optional fields (`parent`, `assignee`, `custom_fields`) in the task payload are handled by the existing `Task` model defaults (all nullable).
- Unknown `resource_subtype` values (parse as string, do not reject -- per `extra="ignore"`).

### FR-10: Cache Invalidation (Must Have)
The system SHALL delete stale cache entries when an inbound task's `modified_at` is newer than the cached version.
- Compare the inbound task's `modified_at` (ISO 8601 string from Asana) against the cached task's `modified_at`.
- If inbound is newer: invalidate TASK, SUBTASKS, and DETECTION cache entries for that GID (following the existing `CacheInvalidator._invalidate_entity_caches()` pattern).
- If inbound is equal or older, or if no cached version exists: skip invalidation.
- Invalidation failures are logged but do not affect the HTTP response or dispatch.
- Invalidation runs inside the BackgroundTask, not in the request path.

## Non-Functional Requirements

### NFR-01: Response Latency
The endpoint SHALL respond within 1 second regardless of payload size. Asana Rules marks actions as failed if the target does not respond promptly.

### NFR-02: Security Boundary
This is the first public-facing POST endpoint in the service. All other POST endpoints require JWT or PAT authentication. The webhook endpoint uses URL token verification only. It MUST be explicitly excluded from the global auth middleware.

### NFR-03: Failure Isolation
Failures in cache invalidation (FR-10), event dispatch (FR-05, FR-07), or any background processing SHALL NOT affect the HTTP response. The endpoint always returns 200 for verified requests with a valid task payload, even if downstream processing fails.

### NFR-04: No Secrets in Logs
The URL token, raw query strings containing the token, and raw request bodies SHALL NOT appear in log output. Log the task metadata (GID, resource_type, modified_at) but never the authentication material.

## Edge Cases

| ID | Condition | Expected Behavior |
|----|-----------|-------------------|
| EC-04 | Task payload is unusually large (hundreds of custom fields) | Parse and dispatch normally. Log warning if serialized size exceeds a configurable threshold. |
| EC-05 | Malformed JSON body with valid token | Return 400. Token verification passes, but JSON parse fails. |
| EC-06 | Task payload contains a resource_type we do not specifically model (e.g., subtask with resource_subtype "milestone") | Parse into Task model. Unknown fields ignored per `extra="ignore"`. |
| EC-07 | Multiple Asana Rules fire simultaneously for the same task | Each POST is dispatched independently. Deduplication is GAP-03 scope. |
| EC-08 | Missing `token` query parameter | Return 401. Log token verification failure (without revealing expected token). |
| EC-09 | Empty `token` query parameter (`?token=`) | Return 401. Log token verification failure. |
| EC-10 | Valid token, empty request body | Return 200. Log warning. No dispatch or cache invalidation. |
| EC-11 | Valid token, non-JSON body (e.g., form-encoded) | Return 400. Log parse failure with content-type info. |
| EC-12 | Valid token, valid JSON, but missing `gid` field | Return 400. Log that inbound payload lacks required task GID. |
| EC-13 | Inbound task `modified_at` is null or missing | Skip cache invalidation (cannot compare). Log warning. Dispatch proceeds normally. |
| EC-14 | Cache provider is unavailable during invalidation | Log error. Dispatch proceeds normally. HTTP response already sent (background task). |
| EC-15 | Inbound task `modified_at` is older than cached version | Skip cache invalidation (cache is already newer). Log debug. |

## Dependencies

| Dependency | Type | Status | Impact |
|------------|------|--------|--------|
| `Task` model (`models/task.py`) | Internal | Exists | Direct reuse for inbound payload parsing, no changes needed |
| `AsanaResource` base class (`models/base.py`) | Internal | Exists | Provides `gid` field and `extra="ignore"` config |
| `CacheInvalidator` (`persistence/cache_invalidator.py`) | Internal | Exists | Pattern reference for cache invalidation; may reuse or extend |
| FastAPI route infrastructure | Internal | Exists | New route module, follows existing patterns |
| FastAPI BackgroundTasks | Internal | Exists | Built-in async dispatch mechanism |
| Environment variable configuration | External | Standard | `WEBHOOK_INBOUND_TOKEN` env var must be set in deployment |
| GAP-03 (Event Routing) | Downstream | Not started | Consumes the dispatch seam this PRD defines |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Loop risk**: Our writes trigger Asana Rules back to us | High | High | Out of scope for this PRD (dispatch is no-op), but GAP-03 must address this. Flag in dispatch interface documentation. |
| **Polling overlap**: Scheduled polling and Rules notifications process same entity concurrently | Medium | Medium | Cache invalidation timestamp comparison (FR-10) prevents stale overwrites. Full dedup is GAP-03 scope. |
| **Token exposure in logs**: URL token appears in access logs or error messages | Medium | High | NFR-04 prohibits token logging. FastAPI request logging must be configured to exclude query params on this route. |
| **First public POST endpoint**: New attack surface | Medium | Medium | Token verification is the authentication layer. Global SlowAPI rate limiting applies. No business logic in the handler itself. |
| **Asana Rules delivery**: Rules do not guarantee at-least-once delivery or retries the same way Webhooks API does | Medium | Medium | Acceptable for V1. V2 Webhooks API provides stronger delivery guarantees. |
| **Token rotation**: Changing the token requires redeploying the service and updating the Asana Rule | Low | Low | Acceptable for V1. V2 may introduce token rotation via secret manager. |

## Out of Scope / Deferred

| Item | Reason | Deferred To |
|------|--------|-------------|
| Event-to-AutomationEngine bridge | SaveResult impedance mismatch requires design | GAP-03 |
| External event emission (SQS, SNS) | Consumer notification is routing, not receipt | GAP-03 |
| Webhook subscription auto-creation | V1 uses Asana Rules (configured in UI), not API subscriptions | V2 |
| Event persistence / replay queue | Durability decision belongs with routing | GAP-03 |
| Idempotency / deduplication | Requires event identity tracking | GAP-03 |
| Cross-container event coordination | Redis Pub/Sub or similar; see INTEGRATE doc Option D | Future |
| Loop prevention (our writes triggering inbound events) | Requires understanding the full dispatch chain | GAP-03 |
| Asana Webhooks API handshake protocol | V1 uses Asana Rules, no handshake needed | V2 |
| HMAC-SHA256 signature verification | V1 uses URL token auth | V2 |
| Durable secret storage (Redis, Secrets Manager) | V1 uses env var for token | V2 |
| Event envelope parsing (`events` array) | V1 receives full task JSON, not event arrays | V2 |

## Open Questions

All open questions have been resolved via stakeholder interview (2026-02-07).

| ID | Question | Resolution |
|----|----------|------------|
| OQ-01 | Endpoint path? | **RESOLVED**: `/api/v1/webhooks/inbound`. Follows existing `/api/v1/` prefix convention. Distinct from authenticated resource routes. |
| OQ-02 | Secret storage backend for V1? | **RESOLVED**: Environment variable (`WEBHOOK_INBOUND_TOKEN`). Simplest option for V1 single-token auth. Durable storage (Redis, Secrets Manager) deferred to V2. |
| OQ-03 | Async dispatch mechanism? | **RESOLVED**: FastAPI BackgroundTasks. Simplest option, runs in same process after response. Adequate for V1 no-op dispatch. The dispatch interface abstraction allows swapping to a queue later. |
| OQ-04 | Model organization? | **RESOLVED**: Reuse existing `Task` model directly. Add only a thin request wrapper if needed for Asana Rules metadata. No new `webhook_event.py` models for V1. |
| OQ-05 | Rate limiting? | **RESOLVED**: Global SlowAPI only. No special per-route rate limiting. Asana Rules does not burst the way Webhooks API can, so global limits are sufficient. |

## V2 Roadmap: Asana Webhooks API

The following items are explicitly deferred from V1 (Asana Rules) and planned for V2 (Asana Webhooks API). Each item includes its original PRD identifier for traceability.

### V2-01: Webhook Handshake Protocol (was FR-02, US-01, SC-001)
The system will implement the Asana webhook handshake protocol:
- Detect handshake requests by the presence of `X-Hook-Secret` header.
- Respond with 200 and echo the `X-Hook-Secret` value in the response headers.
- Persist the secret for use in subsequent signature verification.

### V2-02: HMAC-SHA256 Signature Verification (was FR-03, US-02, SC-002)
The system will verify `X-Hook-Signature` on every non-handshake POST:
- Use the existing `WebhooksClient.verify_signature()` static method.
- Reject unverified requests with 401 before any parsing or dispatch.
- Reuse the existing `WebhooksClient.extract_handshake_secret()` static method.

### V2-03: Durable Secret Storage (was FR-06, SC-005)
The system will persist webhook secrets durably so they survive container restarts:
- Pluggable backend (Redis, AWS Secrets Manager).
- Support for multiple webhook subscriptions (not just one token).
- Secret rotation without service restart.

### V2-04: Event Envelope Parsing (was FR-04, US-03)
The system will parse the Webhooks API event envelope format:
- Deserialize the `events` array from the webhook payload.
- Define Pydantic models for the event structure (action, resource, user, parent, created_at, type).
- Handle batch event arrays (multiple events per POST).

### V2-05: Handshake Edge Cases (was EC-01, EC-02, EC-03, EC-08)
Edge cases specific to the handshake protocol:
- Empty `X-Hook-Secret` value handling.
- Event POST before any handshake (no stored secret).
- Duplicate handshake for same resource (secret rotation).
- Container receiving handshake during rolling deploy.

## Artifact Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| Task model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py` | Read |
| AsanaResource base | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/base.py` | Read |
| CacheInvalidator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/cache_invalidator.py` | Read |
| WebhooksClient | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/webhooks.py` | Prior session |
| Webhook model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/webhook.py` | Prior session |
| AutomationEngine | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/engine.py` | Prior session |
| API routes init | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/__init__.py` | Prior session |
| API main | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | Prior session |
| GAP-02 brief | `/Users/tomtenuta/Code/autom8_asana/docs/GAPS/Q1/GAP-02-webhook-inbound.md` | Prior session |
| GAP-03 brief | `/Users/tomtenuta/Code/autom8_asana/docs/GAPS/Q1/GAP-03-event-routing.md` | Prior session |
