# Webhook Integration Guide

This guide explains how to receive and process events from Asana via webhooks.

## Overview

The autom8_asana platform receives inbound webhook events from Asana Rules and the Asana Webhooks API. Webhooks enable real-time event processing without polling.

### What Webhooks Do

Webhooks notify your application when Asana resources change. The platform handles:

- **Event receipt**: Accept webhook POST requests with authentication
- **Cache invalidation**: Update stale cache entries when tasks change
- **Event dispatch**: Route events to the automation engine
- **Loop prevention**: Detect and block circular webhook-write cycles

### Architecture

```
Asana → POST /api/v1/webhooks/inbound → Cache Invalidation
                                       → Dispatch Protocol
                                       → Automation Engine
```

## Endpoint: POST /api/v1/webhooks/inbound

The primary webhook endpoint receives Asana Rules action payloads.

### Request Format

```http
POST /api/v1/webhooks/inbound?token=<secret> HTTP/1.1
Host: your-server.com
Content-Type: application/json

{
  "gid": "1234567890",
  "resource_type": "task",
  "name": "Test Task",
  "modified_at": "2026-02-07T15:30:00.000Z",
  "assignee": {"gid": "111", "name": "User"},
  "projects": [{"gid": "222", "name": "Project"}],
  "custom_fields": []
}
```

The payload is the full Asana task JSON (equivalent to `GET /tasks/{gid}`).

### Response Format

**Success (200 OK)**:
```json
{
  "status": "accepted"
}
```

**Missing GID (400 Bad Request)**:
```json
{
  "error": "MISSING_GID",
  "message": "Task payload must include 'gid' field"
}
```

**Invalid Token (401 Unauthorized)**:
```json
{
  "error": "INVALID_TOKEN",
  "message": "Authentication failed"
}
```

**Not Configured (503 Service Unavailable)**:
```json
{
  "error": "WEBHOOK_NOT_CONFIGURED",
  "message": "Webhook endpoint is not configured"
}
```

### cURL Example

```bash
curl -X POST "https://your-server.com/api/v1/webhooks/inbound?token=your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "gid": "1234567890",
    "resource_type": "task",
    "name": "Deal Converted",
    "modified_at": "2026-02-07T15:30:00.000Z",
    "custom_fields": []
  }'
```

## Authentication: Token-Based Query Parameter

The webhook endpoint uses token-based authentication via a query parameter.

### Configuration

Set the webhook token via environment variable:

```bash
export WEBHOOK_INBOUND_TOKEN="your-secret-token-here"
```

The token is verified using timing-safe comparison (`hmac.compare_digest`).

### Security Considerations

**Token validation**:
- Missing token returns 401 (MISSING_TOKEN)
- Incorrect token returns 401 (INVALID_TOKEN)
- Unconfigured token returns 503 (WEBHOOK_NOT_CONFIGURED)

**Information leakage prevention**:
- Error responses never reveal the expected token
- Token values never appear in log output
- Authentication occurs before body parsing

**Best practices**:
- Use a strong random token (32+ characters)
- Rotate tokens periodically
- Store tokens in secure secret management systems
- Never commit tokens to version control

## V1: Asana Rules Action Payloads

Asana Rules send webhook POST requests when configured actions trigger.

### How to Configure Asana Rules

1. Open an Asana project
2. Click "Customize" > "Rules"
3. Create a new rule with trigger: "Task moved to section"
4. Add action: "Send a webhook"
5. Enter webhook URL: `https://your-server.com/api/v1/webhooks/inbound?token=<secret>`
6. Configure payload: Send full task object

### Payload Structure

Asana Rules V1 sends the complete task JSON with all fields:

```json
{
  "gid": "1234567890",
  "resource_type": "task",
  "name": "Deal Name",
  "modified_at": "2026-02-07T15:30:00.000Z",
  "assignee": {"gid": "111", "name": "User"},
  "projects": [{"gid": "222", "name": "Sales"}],
  "memberships": [
    {
      "project": {"gid": "222", "name": "Sales"},
      "section": {"gid": "333", "name": "CONVERTED"}
    }
  ],
  "custom_fields": [
    {
      "gid": "444",
      "name": "Deal Value",
      "display_value": "$50,000",
      "number_value": 50000
    }
  ]
}
```

Unknown fields are silently ignored for forward compatibility.

### Common Triggers

| Trigger | Description | Use Case |
|---------|-------------|----------|
| Task moved to section | Task changes section within project | Pipeline stage transitions |
| Tag added to task | Task receives a new tag | Workflow routing (route_*, request_*) |
| Custom field changed | Task field updated | State tracking |
| Task completed | Task marked done | Completion events |

## V2 Extension: Asana Webhooks API

The Asana Webhooks API (V2) provides real-time notifications for any resource change. V2 support is planned but not yet implemented.

### Handshake Protocol

When creating a webhook via the Asana API, Asana sends a handshake request:

```http
POST /api/v1/webhooks/inbound?token=<secret> HTTP/1.1
X-Hook-Secret: random-secret-from-asana
```

Your server must:
1. Respond with 200 OK
2. Store the `X-Hook-Secret` for signature verification
3. Complete the handshake within 72 hours

### HMAC Signature Verification

After handshake, Asana includes an HMAC signature on all webhook requests:

```http
POST /api/v1/webhooks/inbound?token=<secret> HTTP/1.1
X-Hook-Signature: sha256=computed-signature
Content-Type: application/json

{"events": [...]}
```

Verify the signature using `WebhooksClient.verify_signature()`:

```python
from autom8_asana.clients.webhooks import WebhooksClient

is_valid = WebhooksClient.verify_signature(
    request_body=request.get_data(),
    signature=request.headers.get("X-Hook-Signature", ""),
    secret=stored_webhook_secret,
)

if not is_valid:
    return 401  # Reject unsigned requests
```

### Event Envelope

Asana V2 sends event arrays rather than full task JSON:

```json
{
  "events": [
    {
      "action": "changed",
      "created_at": "2026-02-07T15:30:00.000Z",
      "resource": {
        "gid": "1234567890",
        "resource_type": "task"
      },
      "parent": null,
      "user": {
        "gid": "987654321",
        "resource_type": "user"
      }
    }
  ]
}
```

Event types: `changed`, `added`, `removed`, `deleted`, `undeleted`.

V2 implementation is tracked in GAP-03.

## Dispatch Protocol

After accepting a webhook, the endpoint dispatches events to registered handlers via the `WebhookDispatcher` protocol.

### Default Behavior (V1)

The default dispatcher is `NoOpDispatcher`, which logs events and discards them:

```python
class NoOpDispatcher:
    async def dispatch(self, task: Task) -> None:
        logger.info(
            "webhook_task_dispatched_noop",
            extra={
                "task_gid": task.gid,
                "resource_type": task.resource_type,
            },
        )
```

### Custom Dispatcher

Replace the dispatcher during app startup:

```python
from autom8_asana.api.routes.webhooks import set_dispatcher

class CustomDispatcher:
    async def dispatch(self, task: Task) -> None:
        # Route to automation engine
        await automation_engine.process_task(task)

set_dispatcher(CustomDispatcher())
```

### Background Processing

Webhook processing occurs in a FastAPI background task:

1. Endpoint validates token and parses body
2. Endpoint returns 200 immediately
3. Background task runs cache invalidation
4. Background task calls dispatcher

Dispatch errors are logged but do not affect the HTTP response.

## Loop Prevention

Webhook-triggered writes to Asana can create infinite loops.

### The Problem

```
Webhook → Process Task → Write to Asana → Asana Rule Fires → Webhook → ...
```

### Detection Strategy

The `AutomationDispatch` system tracks trigger chains:

```python
async def dispatch_async(
    self,
    trigger: dict[str, Any],
    trigger_chain: list[str] | None = None,
) -> dict[str, Any]:
    chain = trigger_chain or []
    trigger_id = trigger.get("id", "unknown")

    if trigger_id in chain:
        logger.warning("circular_trigger_detected", trigger_id=trigger_id)
        return {"success": False, "error": "circular_trigger"}

    chain.append(trigger_id)
    # ... dispatch to handler
```

### Prevention Best Practices

**Use trigger IDs**:
- Include a unique ID in webhook payloads
- Pass trigger_chain when calling downstream automation

**Limit write-back**:
- Avoid updating the same task that triggered the webhook
- Use distinct sections for automation-written tasks

**Monitor loops**:
- Watch for `circular_trigger_detected` log events
- Alert on high webhook volume from a single task GID

## Cache Invalidation

Webhooks invalidate stale cache entries when a task changes.

### Invalidation Strategy

The endpoint compares inbound `modified_at` against the cached version:

```python
if inbound_modified_at > cached_version:
    cache_provider.invalidate(task_gid, [
        EntryType.TASK,
        EntryType.SUBTASKS,
        EntryType.DETECTION,
    ])
```

### Entry Types Invalidated

| Entry Type | Purpose |
|------------|---------|
| TASK | Full task JSON |
| SUBTASKS | List of subtask GIDs |
| DETECTION | Entity detection results |

### When Invalidation Occurs

**Invalidation runs when**:
- Inbound `modified_at` is newer than cached version
- Cache entry exists for the task GID

**Invalidation skips when**:
- Inbound `modified_at` is missing
- No cached entry exists
- Inbound version is older than cached version
- Cache provider is unavailable

### Error Handling

Cache errors never break webhook processing:

```python
try:
    invalidate_stale_task_cache(task_gid, modified_at, cache_provider)
except Exception:
    logger.exception("webhook_cache_invalidation_error")
    # Continue processing
```

See the [Cache System Guide](cache-system.md) for details on cache architecture.

## Lifecycle Engine Integration

Webhooks route lifecycle transitions to the automation engine via `AutomationDispatch`.

### Section Change Events

When a task moves to a terminal section (CONVERTED or DID NOT CONVERT):

1. Webhook receives task payload
2. Dispatcher extracts section name
3. Dispatcher routes to `LifecycleEngine.handle_transition_async()`
4. Engine executes CREATE → CONFIGURE → ACTIONS → WIRE phases

### Tag-Based Routing

Tag-based triggers (e.g., `route_sales`, `request_asset_edit`) are routed via:

```python
if tag_name.startswith("route_"):
    stage = tag_name.replace("route_", "")
    # Route to lifecycle engine
```

Tag routing is planned for GAP-03.

See the [Lifecycle Engine Guide](lifecycle-engine.md) for transition details.

## Testing

### Unit Tests

Test token verification:

```python
from autom8_asana.api.routes.webhooks import verify_webhook_token

def test_valid_token_accepted():
    result = verify_webhook_token(token="valid-token")
    assert result == "valid-token"

def test_invalid_token_rejected():
    with pytest.raises(HTTPException) as exc:
        verify_webhook_token(token="wrong-token")
    assert exc.value.status_code == 401
```

### Integration Tests

Test the full endpoint with FastAPI TestClient:

```python
from fastapi.testclient import TestClient

def test_webhook_endpoint(client: TestClient):
    response = client.post(
        "/api/v1/webhooks/inbound?token=test-token",
        json={
            "gid": "1234567890",
            "resource_type": "task",
            "modified_at": "2026-02-07T15:30:00.000Z",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
```

### Webhook Testing Tools

**LocalTunnel** (expose localhost to Asana):
```bash
npm install -g localtunnel
lt --port 8000 --subdomain my-webhook-test
```

**Ngrok** (secure tunneling):
```bash
ngrok http 8000
```

**Webhook.site** (inspect payloads without running a server):
- Visit https://webhook.site
- Copy the unique URL
- Configure Asana Rule to POST to that URL
- Inspect received payloads in the web UI

## Troubleshooting

### Webhook Returns 401

**Cause**: Token mismatch or missing token.

**Fix**:
- Verify `WEBHOOK_INBOUND_TOKEN` is set
- Check query parameter: `?token=<secret>`
- Ensure token matches exactly (case-sensitive)

### Webhook Returns 503

**Cause**: `WEBHOOK_INBOUND_TOKEN` not configured.

**Fix**:
```bash
export WEBHOOK_INBOUND_TOKEN="your-token-here"
```

Restart the application.

### Cache Not Invalidating

**Cause**: `modified_at` missing or cache provider unavailable.

**Check logs**:
```
webhook_cache_skip_no_modified_at
webhook_cache_skip_no_provider
webhook_cache_skip_not_stale
```

**Fix**:
- Ensure Asana Rules send full task JSON (includes `modified_at`)
- Verify cache provider is initialized in `app.state.mutation_invalidator`

### Events Not Dispatching

**Cause**: Default `NoOpDispatcher` is active.

**Check logs**:
```
webhook_task_dispatched_noop
```

**Fix**: Replace dispatcher during startup:
```python
from autom8_asana.api.routes.webhooks import set_dispatcher
set_dispatcher(YourCustomDispatcher())
```

### Circular Trigger Loop

**Symptom**: Same task GID appears repeatedly in webhooks.

**Check logs**:
```
circular_trigger_detected
```

**Fix**:
- Add trigger_chain tracking to your automation
- Avoid writing to the task that triggered the webhook
- Use distinct sections for automation-written tasks

## Related Guides

- [Cache System](cache-system.md) - Cache invalidation details
- [Lifecycle Engine](lifecycle-engine.md) - Pipeline automation via webhooks
- [Entity Resolution](entity-resolution.md) - Resolving entities from webhook payloads

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBHOOK_INBOUND_TOKEN` | (empty) | Shared secret for webhook authentication |
| `ASANA_CACHE_ENABLED` | `true` | Enable cache invalidation |

### Route Registration

The webhook router is registered in `src/autom8_asana/api/main.py`:

```python
from autom8_asana.api.routes.webhooks import router as webhooks_router

app.include_router(webhooks_router)
```

### Dispatcher Protocol

Custom dispatchers must implement:

```python
from autom8_asana.api.routes.webhooks import WebhookDispatcher
from autom8_asana.models.task import Task

class MyDispatcher:
    async def dispatch(self, task: Task) -> None:
        # Your logic here
        pass
```

Dispatchers must not raise exceptions (errors are logged internally).

## Next Steps

1. **Configure authentication**: Set `WEBHOOK_INBOUND_TOKEN`
2. **Create Asana Rule**: Configure webhook URL with token query parameter
3. **Implement dispatcher**: Replace `NoOpDispatcher` with your automation logic
4. **Monitor events**: Watch structured logs for `webhook_task_received`
5. **Test invalidation**: Verify cache entries update on webhook receipt
