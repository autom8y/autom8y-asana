---
domain: feat/event-emission
generated_at: "2026-04-01T16:00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/automation/events/**/*.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.88
format_version: "1.0"
---

# Async Event Emission Pipeline

## Purpose and Design Rationale

The Async Event Emission Pipeline provides a fire-and-forget side-channel for publishing domain entity events to external consumers via AWS SQS. Core design rationale is **commit-path isolation**: `SaveSession` must never fail or block because an external event destination is unavailable.

Three defining decisions:

**Non-fatal by contract (NFR-001 / SC-004).** `EventEmitter` wraps every transport call in a broad `except Exception`. Failures are logged as `event_emission_failed` and `event_dead_letter` events but swallowed. `AutomationResult.success` is always `True`.

**Thin payload principle (ADR-GAP03-003).** Envelopes carry GID + metadata only. No entity state embedded. Consumers must fetch full state via the API.

**Feature-flag off by default (ADR-GAP03-005).** `EVENTS_ENABLED` defaults to `false`. When disabled, `matching_subscriptions()` returns empty and no transport is instantiated.

## Conceptual Model

### Event Lifecycle

```
SaveSession completes entity mutation
  -> AutomationEngine iterates rules
    -> EventEmissionRule.should_trigger() checks EventRoutingConfig.matching_subscriptions()
    -> EventEmissionRule.execute_async() builds EventEnvelope, calls EventEmitter.emit()
      -> For each SubscriptionEntry: EventTransport.publish(envelope, destination)
        -> SQSTransport: asyncio.to_thread(boto3.send_message)
      -> Returns AutomationResult (always success=True)
```

### Subscription Matching

A `SubscriptionEntry` matches when: `event_types` is empty (wildcard) OR event_type in list, AND `entity_types` is empty (wildcard) OR entity_type in list.

### Event Types

`EventType(StrEnum)`: CREATED, UPDATED, SECTION_CHANGED, DELETED.

### Envelope Fields

schema_version ("1.0"), event_id (uuid4), event_type, entity_type, entity_gid, timestamp (UTC ISO), source ("save_session"), correlation_id, causation_id (optional), payload (thin metadata). For SECTION_CHANGED: payload includes section_gid and section_name extracted from SaveResult action_results.

## Implementation Map

| File | Class | Role |
|------|-------|------|
| `src/autom8_asana/automation/events/__init__.py` | `setup_event_emission(engine)` | Entry point: reads env vars, wires SQSTransport + EventEmissionRule into engine |
| `src/autom8_asana/automation/events/types.py` | `EventType(StrEnum)` | Closed vocabulary |
| `src/autom8_asana/automation/events/envelope.py` | `EventEnvelope` (frozen) | Immutable carrier with `build()` factory and `to_json_dict()` |
| `src/autom8_asana/automation/events/config.py` | `SubscriptionEntry`, `EventRoutingConfig` | Declarative routing from `EVENTS_*` env vars |
| `src/autom8_asana/automation/events/emitter.py` | `EventEmitter`, `EmitResult` | Orchestration with error absorption |
| `src/autom8_asana/automation/events/rule.py` | `EventEmissionRule` | AutomationRule protocol implementation |
| `src/autom8_asana/automation/events/transport.py` | `EventTransport` (Protocol), `InMemoryTransport`, `SQSTransport` | Transport layer; SQS uses asyncio.to_thread for boto3 |

### SQS Message Attributes

Each message carries `event_type`, `entity_type`, `schema_version` as message attributes (not just body), enabling SQS filtering rules on consumer side.

## Boundaries and Failure Modes

| Failure | Behavior | Signal |
|---------|----------|--------|
| SQS unavailable | Exception caught, `failed += 1` | `event_emission_failed` log warning |
| `EVENTS_ENABLED=true` but no destination | `ValueError` at startup | Hard fail prevents misconfigured start |
| Unknown event type | Returns `AutomationResult` with `skipped_reason` | Skipped reason in result |
| No matching subscriptions | `EmitResult(attempted=0)` | Debug log only |

**State coupling risk:** `EventEmissionRule` stores `_last_event` between `should_trigger()` and `execute_async()`. Safe only if engine calls them consecutively per rule.

**Dead letter handling:** Failed envelopes logged but not persisted, retried, or sent to a DLQ.

## Knowledge Gaps

1. **`autom8y-events` optional dependency** listed but not imported -- may be vestigial.
2. **`setup_event_emission` call site** not observed in lifespan or SaveSession init.
3. **`correlation_id` threading** -- no mechanism for passing inbound `X-Request-ID` through to envelopes.
4. **Dead letter handling** is log-only, no persistence or retry.
