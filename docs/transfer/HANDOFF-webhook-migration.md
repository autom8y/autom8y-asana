# HANDOFF: Webhook Migration for Lifecycle Engine

**Date**: 2026-02-11
**From**: R&D Rite (Tech Transfer)
**To**: 10x-dev Rite
**Transfer Doc**: `docs/transfer/TRANSFER-workflow-resolution-platform.md`
**Priority**: P1 (required for lifecycle engine production deployment)
**Estimated Effort**: 1-2 days

---

## 1. Context

The lifecycle engine currently has two trigger paths:

1. **Polling-based (implemented)**: `PipelineTransitionWorkflow` scans 8 pipeline projects for tasks in CONVERTED/DID NOT CONVERT sections, then routes to `LifecycleEngine.handle_transition_async()`.

2. **Webhook-based (partially implemented)**: `src/autom8_asana/lifecycle/webhook.py` defines a FastAPI endpoint that receives Asana Rule webhook POSTs, but this router is NOT registered in the FastAPI app.

The webhook path is the target production architecture. Polling is the fallback.

---

## 2. Current State

### What Exists

**Lifecycle Webhook Handler** at `src/autom8_asana/lifecycle/webhook.py`:
- FastAPI `APIRouter` with prefix `/api/v1/webhooks` and tag `webhooks`
- `POST /api/v1/webhooks/asana` endpoint
- `AsanaWebhookPayload` Pydantic model (task_gid, task_name, project_gid, section_name, tags, custom_fields)
- `WebhookResponse` Pydantic model (accepted, message)
- Reads `request.app.state.automation_dispatch` for routing
- Builds trigger dict from payload and calls `dispatch.dispatch_async()`

**AutomationDispatch** at `src/autom8_asana/lifecycle/dispatch.py`:
- Unified entry point with circular trigger prevention
- Routes `section_changed` events to lifecycle engine via `_handle_section_change()`
- Routes `tag_added` events via `_handle_tag_trigger()` (stub -- returns routed_to but does not execute)

**Existing Webhook Router** at `src/autom8_asana/api/routes/webhooks.py`:
- Already registered in `api/main.py:177` as `webhooks_router`
- Handles `POST /api/v1/webhooks/inbound?token=<secret>`
- Parses raw Task JSON payloads (Asana Rules V1 format)
- Background processing: cache invalidation + NoOp dispatch
- Has `WebhookDispatcher` protocol and `set_dispatcher()` for future wiring

### What Is Missing

| Item | Detail |
|------|--------|
| Router registration | `lifecycle.webhook.router` not included in `api/main.py` |
| App state initialization | `request.app.state.automation_dispatch` never set |
| Lifecycle engine initialization | No startup code creates `LifecycleConfig` + `LifecycleEngine` + `AutomationDispatch` |
| Auth/token verification | Lifecycle webhook has no auth (existing inbound has `verify_webhook_token`) |
| Feature flag | No mechanism to enable/disable lifecycle processing per stage |
| URL namespace coordination | Both routers use `/api/v1/webhooks` prefix (no conflict: `/asana` vs `/inbound`) |

---

## 3. Target State

### Architecture

```
Asana Rules POST
        |
        v
/api/v1/webhooks/asana  (lifecycle webhook)
        |
        v
AutomationDispatch.dispatch_async()
        |
        +-- section_changed --> LifecycleEngine.handle_transition_async()
        |
        +-- tag_added --> LifecycleEngine (when implemented)
```

### Integration Points

**`src/autom8_asana/api/main.py`**:
```python
# Add to imports:
from autom8_asana.lifecycle.webhook import router as lifecycle_webhook_router

# Add in create_app() after existing router registrations:
app.include_router(lifecycle_webhook_router)
```

**`src/autom8_asana/api/lifespan.py`** (or equivalent startup):
```python
from pathlib import Path
from autom8_asana.lifecycle.config import LifecycleConfig
from autom8_asana.lifecycle.engine import LifecycleEngine
from autom8_asana.lifecycle.dispatch import AutomationDispatch

# During startup:
config = LifecycleConfig(Path("config/lifecycle_stages.yaml"))
engine = LifecycleEngine(client, config)
dispatch = AutomationDispatch(client, engine)
app.state.automation_dispatch = dispatch
```

---

## 4. Implementation Plan

### Step 1: Add Auth to Lifecycle Webhook

The lifecycle webhook currently has no authentication. Two options:

**Option A (recommended)**: Reuse existing `verify_webhook_token` dependency from `api/routes/webhooks.py`:
```python
from autom8_asana.api.routes.webhooks import verify_webhook_token

@router.post("/asana")
async def handle_asana_webhook(
    payload: AsanaWebhookPayload,
    request: Request,
    _token: str = Depends(verify_webhook_token),
) -> WebhookResponse:
```

**Option B**: Use a separate token (if Asana Rules sends to different URLs with different tokens).

### Step 2: Add Feature Flag

Add a feature flag to control lifecycle processing:

```python
import os

LIFECYCLE_ENABLED_ENV = "AUTOM8_LIFECYCLE_ENABLED"
LIFECYCLE_ENABLED_STAGES_ENV = "AUTOM8_LIFECYCLE_STAGES"  # comma-separated

def is_lifecycle_enabled(stage_name: str | None = None) -> bool:
    if os.environ.get(LIFECYCLE_ENABLED_ENV, "").lower() in {"false", "0", "no"}:
        return False
    if stage_name:
        enabled_stages = os.environ.get(LIFECYCLE_ENABLED_STAGES_ENV, "").split(",")
        if enabled_stages and enabled_stages != [""]:
            return stage_name in enabled_stages
    return True
```

Check in `AutomationDispatch.dispatch_async()` before routing to lifecycle engine.

### Step 3: Register Router and Initialize State

Add lifecycle webhook router registration and startup initialization per Section 3.

### Step 4: Rollout Strategy

| Phase | Config | Behavior |
|-------|--------|----------|
| **Shadow** | `LIFECYCLE_ENABLED=true`, `LIFECYCLE_STAGES=` (none) | Webhook receives events, logs them, does NOT process |
| **Canary** | `LIFECYCLE_STAGES=sales` | Only sales transitions processed via webhook |
| **Gradual** | `LIFECYCLE_STAGES=sales,outreach,onboarding` | Add stages one at a time |
| **Full** | `LIFECYCLE_STAGES=` (all) or remove env var | All stages processed |

At each phase:
- Monitor transition success/failure metrics (GAP-05)
- Compare results with existing PipelineConversionRule (shadow mode)
- Roll back by setting `LIFECYCLE_ENABLED=false`

---

## 5. Namespace Coordination

Both webhook routers share the `/api/v1/webhooks` prefix. Final routes:

| Route | Router | Purpose |
|-------|--------|---------|
| `POST /api/v1/webhooks/inbound?token=...` | `api/routes/webhooks.py` | Existing: cache invalidation + dispatch protocol |
| `POST /api/v1/webhooks/asana?token=...` | `lifecycle/webhook.py` | New: lifecycle automation triggers |

No conflict. Both can be registered simultaneously.

**Future consideration**: The existing `WebhookDispatcher` protocol in `api/routes/webhooks.py` (GAP-03 seam) could eventually be wired to `AutomationDispatch`, unifying both webhook paths. This is NOT required for initial deployment.

---

## 6. Test Requirements

| Test | Type | Priority |
|------|------|----------|
| Lifecycle webhook returns 200 for valid payload | Unit | P0 |
| Lifecycle webhook returns 401 for missing/invalid token | Unit | P0 |
| AutomationDispatch routes section_changed to engine | Unit | P0 (exists: `test_dispatch.py`) |
| Full webhook -> dispatch -> engine chain | Integration | P1 |
| Feature flag disables processing | Unit | P0 |
| Feature flag restricts to specific stages | Unit | P0 |
| Shadow mode logs but does not execute | Integration | P1 |

Existing tests in `tests/unit/lifecycle/test_webhook.py` (5 tests) and `tests/unit/lifecycle/test_dispatch.py` (4 tests) cover the handler and dispatch logic. New tests needed for auth, feature flag, and router registration.

---

## 7. Key Files

| File | Absolute Path | Action |
|------|---------------|--------|
| Lifecycle webhook handler | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lifecycle/webhook.py` | Add auth dependency |
| Lifecycle dispatch | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lifecycle/dispatch.py` | Add feature flag check |
| FastAPI main | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | Register lifecycle router |
| FastAPI lifespan | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/lifespan.py` | Initialize lifecycle state |
| Existing webhook router | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/webhooks.py` | Reference only (verify_webhook_token import) |
| Lifecycle config | `/Users/tomtenuta/Code/autom8_asana/config/lifecycle_stages.yaml` | No changes |
| Webhook tests | `/Users/tomtenuta/Code/autom8_asana/tests/unit/lifecycle/test_webhook.py` | Extend with auth tests |
| Dispatch tests | `/Users/tomtenuta/Code/autom8_asana/tests/unit/lifecycle/test_dispatch.py` | Extend with feature flag tests |
