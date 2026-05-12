---
domain: feat/webhooks
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/api/routes/webhooks.py"
  - "./src/autom8_asana/clients/webhooks.py"
  - "./src/autom8_asana/lifecycle/webhook.py"
  - "./src/autom8_asana/lifecycle/webhook_dispatcher.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.95
format_version: "1.0"
---

# Asana Webhook Inbound Event Processing

## Purpose and Design Rationale

### Problem Statement

Asana Rules actions POST a full task JSON payload to a registered HTTP endpoint when a rule fires. The service needs to receive these payloads, authenticate them without bearer tokens (Asana Rules cannot inject `Authorization` headers), invalidate stale cache entries, and route to downstream automation — all without blocking Asana's retry timer.

### Design Decisions

**Immediate 200 response (per PRD-GAP-02, FR-05/SC-004)**: Processing runs as a `BackgroundTask` added to FastAPI's `BackgroundTasks`. The HTTP 200 is sent before cache invalidation or dispatch begins. This is mandatory — Asana treats slow responses as delivery failures and retries, which would cause duplicate processing.

**URL token authentication instead of bearer auth (per TDD-GAP-02, SC-02 exemption)**: Asana Rules cannot inject `Authorization` headers. The token is a shared secret in the query string (`?token=<secret>`), verified with `hmac.compare_digest` for timing-safety. The raw `APIRouter` is used intentionally; `SecureRouter` would inject JWT requirements incompatible with this auth model.

**Two error codes collapse to one wire code (ASANA-AUTH-002)**: Both `MISSING_TOKEN` and `INVALID_TOKEN` paths raise `AsanaWebhookSignatureInvalidError`. Collapsing these denies attackers oracle information about which side of the comparison failed.

**Typed canonical error subclasses (WS-B1+B2 P1-D, ADR-canonical-error-vocabulary D-01/D-04)**: The route defines four service-local error subclasses (`AsanaWebhookSignatureInvalidError`, `AsanaWebhookNotConfiguredError`, `AsanaWebhookInvalidJsonError`, `AsanaWebhookMissingGidError`, `AsanaWebhookInvalidTaskError`) that extend fleet canonical bases. These are consumer-facing contracts — Asana's retry harness may key on wire codes.

**Protocol-based dispatch seam (GAP-03)**: The route defines a `WebhookDispatcher` Protocol and `NoOpDispatcher` default. A module-level `_dispatcher` variable is replaced at GAP-03 via `set_dispatcher()`. `LifecycleWebhookDispatcher` is the production replacement.

**4-layer feature flag (ADR-omniscience-lifecycle-observation Decision 3, R-007 risk mitigation)**: `LifecycleWebhookDispatcher` defaults to `enabled=False` + `dry_run=True` with empty entity and event allowlists. All four layers must be affirmatively configured to allow live dispatch to reach `AutomationDispatch.dispatch_async()`.

**Two webhook API concepts coexist**: V1 (Asana Rules, fully implemented — full task JSON payload, URL token auth) and V2 (Asana Webhooks API, GAP-03 scope — HMAC-SHA256 X-Hook-Signature, event arrays, handshake protocol). V2 tooling (`verify_signature`, `extract_handshake_secret`) is present in `WebhooksClient` but the inbound handler does not call it.

### Rejected Alternatives

- **JWT authentication**: Incompatible with Asana Rules (no header injection). Explicitly excluded via SC-02 exemption.
- **Synchronous processing**: Would cause Asana to retry on slow operations. Rejected in favor of immediate 200 + BackgroundTask.
- **Single wire code for all auth failures**: Rejected in favor of separate configured (503) vs. invalid token (401) distinction to guide operator remediation.

---

## Conceptual Model

### Key Terminology

| Term | Definition |
|------|-----------|
| **V1 webhook** | Asana Rules action: POSTs full task JSON to `POST /api/v1/webhooks/inbound?token=<secret>`. Auth: URL token. |
| **V2 webhook** | Asana Webhooks API (GAP-03, not yet handling inbound): HMAC-SHA256 signature, event array envelope, handshake on creation. |
| **WebhookDispatcher** | Protocol (structural subtyping) defining `async dispatch(task: Task) -> None`. The dispatch seam. |
| **NoOpDispatcher** | V1 default: logs and discards the task. Production placeholder until GAP-03. |
| **LifecycleWebhookDispatcher** | GAP-03 replacement: 4-layer feature flag evaluation then routes to `AutomationDispatch.dispatch_async()`. |
| **WebhookDispatcherConfig** | Frozen dataclass holding the 4 flag layers. Populated from env vars via `from_env()`. |
| **LoopDetector** | Dependency of `LifecycleWebhookDispatcher`. Detects self-triggered events (our outbound writes to Asana may trigger rule callbacks). |
| **GAP-03 seam** | The integration point where `set_dispatcher()` replaces `NoOpDispatcher` with `LifecycleWebhookDispatcher` at startup. |
| **ASANA_WEBHOOK_INBOUND_TOKEN** | Environment variable holding the expected URL token secret. Absence causes 503. |
| **SCAR-029** | GID whitespace-only bypass: `str.strip()` guard applied before truthiness check at `webhooks.py:467-478`. |

### V1 Processing Pipeline

```
POST /api/v1/webhooks/inbound?token=<secret>
  -> verify_webhook_token()            [Dep: 401 ASANA-AUTH-002, 503 ASANA-DEP-002]
  -> request.json()                    [400 ASANA-VAL-002 on parse failure]
  -> body empty?                       [200 "empty payload ignored" if truthy-false]
  -> raw_gid + str.strip() guard       [400 ASANA-VAL-003 if missing/whitespace-only]
  -> Task.model_validate(body)         [400 ASANA-VAL-004 on ValidationError]
  -> logger.info webhook_task_received
  -> get cache_provider from app.state.mutation_invalidator._cache
  -> background_tasks.add_task(_process_inbound_task, task, cache_provider)
  -> return 200 {"status": "accepted"}

  [background]
  -> invalidate_stale_task_cache()     [skip silently on missing modified_at or None provider]
     -> cache_provider.get_versioned(gid, TASK)
     -> cached_entry.is_stale(inbound_modified_at)?
     -> cache_provider.invalidate(gid, [TASK, SUBTASKS, DETECTION])
  -> _dispatcher.dispatch(task)        [errors caught, logged, not propagated]
```

### LifecycleWebhookDispatcher Evaluation (5-layer short-circuit via handle_event)

```
handle_event(event_type, entity_type, entity_gid, payload)
  Layer 1: config.enabled == False  -> {"dispatched": False, "reason": "disabled"}
  Layer 2: entity_type not in allowed_entity_types -> "entity_type_not_allowed"
  Layer 3: event_type not in allowed_event_types   -> "event_type_not_allowed"
  Layer 4: loop_detector.is_self_triggered(gid)    -> "loop_detected"
  Layer 5: config.dry_run == True                  -> log only, "dry_run"
  Live:    dispatch.dispatch_async(trigger)         -> {"dispatched": True, "reason": "live"}
```

**Critical gap**: `webhooks.py` calls `_dispatcher.dispatch(task: Task)` via the `WebhookDispatcher` protocol. `LifecycleWebhookDispatcher` exposes `handle_event(event_type, entity_type, entity_gid, payload)` — a different signature. `LifecycleWebhookDispatcher` does NOT implement `WebhookDispatcher.dispatch()`. The `set_dispatcher()` seam requires an adapter layer that is not yet implemented. Installing `LifecycleWebhookDispatcher` directly via `set_dispatcher()` would fail the `isinstance(x, WebhookDispatcher)` runtime check (Protocol check would pass structurally only if `dispatch` method exists — it does not on `LifecycleWebhookDispatcher`).

### Cache Invalidation Model

Inbound `modified_at` is compared against the cached `TASK` entry via `CacheEntry.is_stale()`. If newer, `TASK`, `SUBTASKS`, and `DETECTION` entries are all invalidated for the GID. Missing `modified_at` or `None` cache provider causes silent skip (NFR-03: cache failures must not affect HTTP response).

### Inter-Feature Relationships

| Consumes | From |
|----------|------|
| `Task` model | `autom8_asana.models.task` |
| `EntryType` enum | `autom8_asana.cache.models.entry` |
| `MutationInvalidator._cache` | `autom8_asana.cache.integration.mutation_invalidator` (private attribute access) |
| `get_settings()` / `settings.webhook.inbound_token` | `autom8_asana.settings` |
| `AutomationDispatch.dispatch_async()` | `autom8_asana.lifecycle.dispatch` (LifecycleWebhookDispatcher only) |
| `LoopDetector.is_self_triggered()` | `autom8_asana.lifecycle.loop_detector` (LifecycleWebhookDispatcher only) |

| Provides | To |
|----------|---|
| `webhooks_router` | `api/main.py` — mounted at `/api/v1/webhooks` |
| `WebhookDispatcher` protocol | GAP-03 adapter or any future dispatcher implementation |
| `set_dispatcher()` | Startup wiring for GAP-03 |
| `WebhooksClient` (CRUD + signature) | Any code managing Asana webhook subscriptions |

---

## Implementation Map

| File | Role | Key Types / Entry Points |
|------|------|--------------------------|
| `src/autom8_asana/api/routes/webhooks.py` | Primary inbound handler. Defines error subclasses, `WebhookDispatcher` protocol, `NoOpDispatcher`, `set_dispatcher()`, `verify_webhook_token()` dep, `invalidate_stale_task_cache()`, `_process_inbound_task()` background coroutine, `receive_inbound_webhook` route. | `WebhookDispatcher`, `NoOpDispatcher`, `AsanaWebhookSignatureInvalidError` (ASANA-AUTH-002), `AsanaWebhookNotConfiguredError` (ASANA-DEP-002), `AsanaWebhookInvalidJsonError` (ASANA-VAL-002), `AsanaWebhookMissingGidError` (ASANA-VAL-003), `AsanaWebhookInvalidTaskError` (ASANA-VAL-004) |
| `src/autom8_asana/lifecycle/webhook_dispatcher.py` | GAP-03 lifecycle dispatcher. 4-layer feature flag + loop detection. Config from env. | `WebhookDispatcherConfig` (frozen dataclass, `from_env()`), `LifecycleWebhookDispatcher` (`handle_event()`, `_build_trigger()`) |
| `src/autom8_asana/lifecycle/webhook.py` | Legacy/prototype route. Defines `POST /api/v1/webhooks/asana`. Same URL prefix as primary route. NOT mounted in `api/main.py`. Contains production breakage (see below). | `AsanaWebhookPayload` (`extra="forbid"`, `task_gid`, `task_name`, `project_gid`, `section_name`, `tags`, `custom_fields`), `WebhookResponse`, `handle_asana_webhook` |
| `src/autom8_asana/clients/webhooks.py` | Outbound webhook management client. Extends `BaseClient`. V2 signature tooling. | `WebhooksClient.get()`, `.create()`, `.update()`, `.delete()`, `.list_for_workspace_async()` (returns `PageIterator[Webhook]`), `.verify_signature()` (static, HMAC-SHA256), `.extract_handshake_secret()` (static) |

### Router Registration

`api/routes/__init__.py` exports `webhooks_router` from `api/routes/webhooks.py`. `api/main.py` line 77 imports and line 443 mounts it via `RouterMount(router=webhooks_router)`. The lifecycle/webhook.py router is **not imported or mounted** anywhere — it is dead code from a startup perspective.

### Environment Variables (4-layer flag)

| Variable | Default | Effect |
|----------|---------|--------|
| `WEBHOOK_DISPATCH_ENABLED` | `"false"` | Global kill switch. Must be `"true"` to allow any dispatch. |
| `WEBHOOK_DISPATCH_DRY_RUN` | `"true"` | Log-only mode. Must be `"false"` for live dispatch. |
| `WEBHOOK_DISPATCH_ENTITY_TYPES` | `""` | Comma-separated allowlist. Empty = nothing allowed. |
| `WEBHOOK_DISPATCH_EVENT_TYPES` | `""` | Comma-separated allowlist. Empty = nothing allowed. |
| `ASANA_WEBHOOK_INBOUND_TOKEN` | absent | Token secret. Absence causes 503 ASANA-DEP-002. |

### Data Flow

```
Asana Rules POST
  -> FastAPI router (api/routes/webhooks.py)
  -> verify_webhook_token() [reads settings.webhook.inbound_token]
  -> receive_inbound_webhook() [parse, validate, enqueue background]
  -> BackgroundTasks
     -> invalidate_stale_task_cache() [reads mutation_invalidator._cache from app.state]
     -> _dispatcher.dispatch(task) [module-level _dispatcher: NoOpDispatcher or GAP-03 impl]
        [if LifecycleWebhookDispatcher via adapter]
        -> WebhookDispatcherConfig.from_env() [env vars]
        -> LoopDetector.is_self_triggered()
        -> AutomationDispatch.dispatch_async()
        -> LifecycleEngine.handle_transition_async()
```

### Test Coverage

| File | Tests | Scope |
|------|-------|-------|
| `tests/unit/api/routes/test_webhooks.py` | 80 (1212 lines) | Token verification (TestVerifyWebhookToken), cache invalidation (TestInvalidateStaleCacheTask), route handler (TestReceiveInboundWebhook), NoOpDispatcher, set_dispatcher, background task, 6 adversarial test classes (TestAdversarialTokenVerification, TestAdversarialPayloadInjection, TestAdversarialPayloadStructure, TestAdversarialCacheInvalidation, TestAdversarialDispatchProtocol, TestAdversarialHTTPEdgeCases, TestAdversarialSecurityLogging) |
| `tests/unit/lifecycle/test_webhook.py` | 5 (87 lines) | Legacy route handler (lifecycle/webhook.py) |
| `tests/unit/lifecycle/test_webhook_dispatcher.py` | 20 (262 lines) | LifecycleWebhookDispatcher: all 5 evaluation layers, config from_env, trigger building |

---

## Boundaries and Failure Modes

### Owns

- Inbound receipt and authentication of Asana Rules action payloads (`POST /api/v1/webhooks/inbound`)
- URL token verification (timing-safe, canonical error envelopes with wire codes)
- Cache invalidation on task change (TASK + SUBTASKS + DETECTION entries)
- Routing to registered dispatcher via `WebhookDispatcher` protocol
- Outbound webhook subscription management (`WebhooksClient` CRUD)
- V2 HMAC-SHA256 signature verification tooling (`WebhooksClient.verify_signature`)

### Does Not Own

- Automation logic after dispatch (LifecycleEngine, AutomationDispatch)
- V2 handshake protocol (creation response with `X-Hook-Secret` header) — tooling present but not wired
- Loop detection implementation (LoopDetector, owned by `lifecycle/loop_detector`)
- Cache entry staleness comparison logic (`CacheEntry.is_stale()`, owned by cache subsystem)
- The legacy `POST /api/v1/webhooks/asana` route (lifecycle/webhook.py — unmounted dead code)

### Failure Modes

| Scenario | Behavior | Wire Code |
|----------|----------|-----------|
| `ASANA_WEBHOOK_INBOUND_TOKEN` env var absent | 503 ASANA-DEP-002 | `AsanaWebhookNotConfiguredError` |
| `?token=` query param missing | 401 ASANA-AUTH-002 + `WWW-Authenticate: URLToken` | `AsanaWebhookSignatureInvalidError` |
| Token mismatch (timing-safe compare_digest) | 401 ASANA-AUTH-002 + `WWW-Authenticate: URLToken` | `AsanaWebhookSignatureInvalidError` |
| Request body not valid JSON | 400 ASANA-VAL-002 | `AsanaWebhookInvalidJsonError` |
| Body empty (falsy) | 200 `{"status": "accepted", "detail": "empty payload ignored"}` | Accepted silently |
| `gid` field absent or whitespace-only (SCAR-029) | 400 ASANA-VAL-003 | `AsanaWebhookMissingGidError` |
| Payload fails `Task.model_validate()` | 400 ASANA-VAL-004 | `AsanaWebhookInvalidTaskError` |
| `modified_at` absent from payload | Cache invalidation skipped silently | `webhook_cache_skip_no_modified_at` log |
| `mutation_invalidator` or `_cache` absent from app.state | Cache invalidation skipped silently | `webhook_cache_skip_no_provider` log |
| Cache operation raises (ValueError, RuntimeError, CACHE_TRANSIENT_ERRORS) | Exception caught, logged, invalidation skipped | `webhook_cache_invalidation_error` log |
| `_dispatcher.dispatch()` raises (ConnectionError, TimeoutError, OSError, RuntimeError) | Exception caught, logged, not propagated | `webhook_dispatch_error` log |
| All 4 dispatch feature flags off | LifecycleWebhookDispatcher returns `{"dispatched": False}` reason strings | No live dispatch |

### Production Breakage Gap: lifecycle/webhook.py

`src/autom8_asana/lifecycle/webhook.py` line 74:

```python
dispatch = request.app.state.automation_dispatch
```

This attribute is never initialized by `lifespan.py` (confirmed: full lifespan.py read at `8980bcd7` — no `automation_dispatch` assignment). If this route were ever mounted, every request to `POST /api/v1/webhooks/asana` would raise `AttributeError` at runtime. The route is currently safe only because it is not mounted — `api/main.py` does not import or register `lifecycle.webhook.router`.

### Protocol Adapter Gap: LifecycleWebhookDispatcher

`webhooks.py` calls `await _dispatcher.dispatch(task: Task)` via `WebhookDispatcher` protocol.
`LifecycleWebhookDispatcher` exposes `handle_event(event_type, entity_type, entity_gid, payload)`.
These signatures are incompatible. `LifecycleWebhookDispatcher` does NOT have a `dispatch()` method.

Installing it directly via `set_dispatcher()` would fail the `isinstance(x, WebhookDispatcher)` runtime check (since `WebhookDispatcher` is `@runtime_checkable` and no `dispatch` method exists on `LifecycleWebhookDispatcher`). GAP-03 completion requires either:
1. Adding a `dispatch(task: Task)` adapter method to `LifecycleWebhookDispatcher`, or
2. Creating a thin adapter class that bridges `dispatch(task)` to `handle_event(...)`.

### Structural Tensions

- **Private attribute access for cache**: `cache_provider = getattr(mutation_invalidator, "_cache", None)` at `webhooks.py:506` — accesses a private attribute of `MutationInvalidator`. Future refactoring of `MutationInvalidator` must account for this.
- **V2 signature tooling unused**: `WebhooksClient.verify_signature()` and `extract_handshake_secret()` implement HMAC-SHA256 verification per ADR-0008 but are not called by the inbound handler. V2 Webhooks API pointed at this service would silently receive no signature verification.
- **SCAR-029 GID strip guard**: Line 472 in `webhooks.py`: `body.get("gid")` truthy check runs before `str.strip()` on line 471. The explicit `.strip()` guard is required because Pydantic `str_strip_whitespace` would strip the GID *after* model validation — a whitespace-only GID passes the truthiness check but would fail or be normalized post-validation. The guard closes this gap.
- **Webhook URL prefix collision**: Both `lifecycle/webhook.py` and `api/routes/webhooks.py` declare `prefix="/api/v1/webhooks"`. If `lifecycle/webhook.py` were ever mounted, route collision would occur for any shared path segment. Currently safe due to `lifecycle/webhook.py` being unmounted.

### Configuration Boundaries

- `ASANA_WEBHOOK_INBOUND_TOKEN` must be a non-empty string; absence causes 503, not 401.
- `WEBHOOK_DISPATCH_ENTITY_TYPES` and `WEBHOOK_DISPATCH_EVENT_TYPES` are comma-separated strings; an empty string produces an empty frozenset, which blocks all dispatch.
- The `dry_run` flag defaults `"true"` and only disables when the env var value (lowercased) is exactly `"false"`. Any other value (empty string, `"0"`, `"no"`) leaves dry_run enabled.

---

```metadata
source_hash: 8980bcd7
generated_at: 2026-05-08T00:00Z
confidence: 0.95
key_files_read:
  - src/autom8_asana/api/routes/webhooks.py (514 lines)
  - src/autom8_asana/lifecycle/webhook_dispatcher.py (216 lines)
  - src/autom8_asana/lifecycle/webhook.py (95 lines)
  - src/autom8_asana/clients/webhooks.py (370 lines)
  - src/autom8_asana/api/lifespan.py (330 lines — confirmed no automation_dispatch init)
  - src/autom8_asana/api/main.py (partial — confirmed lifecycle/webhook.py not mounted)
  - .know/scar-tissue.md (SCAR-029 detail confirmed)
test_counts:
  test_webhooks.py: 80 tests / 1212 lines
  test_webhook.py: 5 tests / 87 lines
  test_webhook_dispatcher.py: 20 tests / 262 lines
changes_from_prior_version:
  - Updated source_hash c213958 -> 8980bcd7
  - Confirmed lifecycle/webhook.py NOT mounted (was "unverified" in prior version)
  - Confirmed no automation_dispatch in lifespan.py (was "unverified" in prior version)
  - Documented protocol adapter gap explicitly (was "knowledge gap #2" in prior version)
  - Added WS-B1+B2 P1-D canonical error subclass documentation (new since prior)
  - Added 5-layer dispatcher evaluation (prior doc said 4-layer; actually 5 evaluation steps)
  - Updated test counts (prior: 80/20/5; current: 80/5/20 — file assignment clarified)
  - Added env var table with exact default behavior
  - Added configuration boundary details (dry_run "false" exact match)
  - Promoted confidence 0.87 -> 0.95
```
