---
domain: feat/webhooks
generated_at: "2026-04-01T16:40:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/api/routes/webhooks.py"
  - "./src/autom8_asana/clients/webhooks.py"
  - "./src/autom8_asana/lifecycle/webhook.py"
  - "./src/autom8_asana/lifecycle/webhook_dispatcher.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.87
format_version: "1.0"
---

# Asana Webhook Inbound Event Processing

## Purpose and Design Rationale

Provides `POST /api/v1/webhooks/inbound` to receive Asana event payloads, authenticate via URL token, invalidate stale cache entries, and dispatch to a pluggable handler.

**Immediate 200 response**: Processing runs as `BackgroundTask` to avoid Asana treating slow operations as delivery failures. **URL token auth**: Asana Rules cannot inject Authorization headers; `?token=` with `hmac.compare_digest`. **Protocol-based dispatch**: `WebhookDispatcher` protocol with `NoOpDispatcher` default; GAP-03 replaces with `LifecycleWebhookDispatcher`. **4-layer feature flag**: Dispatcher defaults `enabled=False` + `dry_run=True` with empty allowlists.

**Two webhook concepts coexist**: V1 (Asana Rules, implemented -- full task JSON, URL token) and V2 (Asana Webhooks API, planned GAP-03 -- HMAC signature, event arrays, handshake).

## Conceptual Model

### V1 Processing Pipeline

```
POST /api/v1/webhooks/inbound?token=<secret>
  -> verify_webhook_token() [401/503]
  -> parse JSON, validate gid [400 on missing/whitespace per SCAR-029]
  -> Task.model_validate(body)
  -> add_background_task(_process_inbound_task)
  -> return 200 {"status": "accepted"}
  [background] invalidate TASK/SUBTASKS/DETECTION cache -> dispatch to handler
```

### LifecycleWebhookDispatcher Evaluation (5 layers, short-circuit)

1. `enabled == False` -> disabled
2. entity_type not in allowlist -> filtered
3. event_type not in allowlist -> filtered
4. `loop_detector.is_self_triggered()` -> loop_detected
5. `dry_run == True` -> log only; else -> live dispatch

### Cache Invalidation

Inbound `modified_at` compared against cached entry. If newer, invalidates TASK + SUBTASKS + DETECTION. Missing timestamps or unavailable cache silently skipped.

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_asana/api/routes/webhooks.py` | Primary route: `POST /inbound`, `WebhookDispatcher` protocol, `NoOpDispatcher`, token verification, cache invalidation, background task dispatch |
| `src/autom8_asana/lifecycle/webhook_dispatcher.py` | `LifecycleWebhookDispatcher` with 4-layer feature flag + loop detection. Env: `WEBHOOK_DISPATCH_ENABLED`, `_DRY_RUN`, `_ENTITY_TYPES`, `_EVENT_TYPES` |
| `src/autom8_asana/lifecycle/webhook.py` | Legacy/prototype route (`POST /asana`) with stricter `AsanaWebhookPayload` model (`extra="forbid"`) |
| `src/autom8_asana/clients/webhooks.py` | Outbound webhook management: CRUD, `verify_signature()` (HMAC-SHA256), `extract_handshake_secret()` |

**Test coverage**: 80 tests for primary route (1153 lines, 45 adversarial per SCAR-029), 20 tests for dispatcher, 5 for legacy route.

## Boundaries and Failure Modes

### Owns

- Inbound receipt and authentication of Asana Rule payloads
- Cache invalidation on task change
- Routing to registered dispatcher

### Does Not Own

- Creating/listing/deleting Asana webhooks (WebhooksClient)
- HMAC signature verification for V2 events (available but not called by inbound handler)
- Automation logic after dispatch (LifecycleEngine)

### Failure Modes

| Scenario | Behavior |
|----------|----------|
| Missing/invalid token | 401 |
| Token env var absent | 503 WEBHOOK_NOT_CONFIGURED |
| Whitespace-only gid | 400 MISSING_GID (SCAR-029) |
| Cache provider unavailable | Skip invalidation silently |
| Dispatch errors | Log, don't propagate |
| Loop detected | Return dispatched=false |

### Structural Tensions

- **Two route files** at same prefix: `lifecycle/webhook.py` registration status in `api/main.py` unverified
- **V2 gap**: `verify_signature()` exists but inbound handler doesn't call it; no handshake handling
- **Private attribute access**: Cache provider via `mutation_invalidator._cache`

## Knowledge Gaps

1. `lifecycle/webhook.py` router registration status unconfirmed.
2. `LifecycleWebhookDispatcher.handle_event()` signature doesn't match `WebhookDispatcher.dispatch()` protocol -- adapter layer unclear.
3. `LoopDetector` implementation details not read.
4. V2 handshake handling absent -- would silently fail if V2 webhooks pointed here.
