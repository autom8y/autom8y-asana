---
domain: feat/event-emission
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/automation/events/"
  - "./pyproject.toml"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.92
format_version: "1.0"
---

# Async Event Emission Pipeline

## Purpose and Design Rationale

The Async Event Emission Pipeline provides a fire-and-forget side-channel for publishing domain entity events to external consumers via AWS SQS. Its primary existence justification is **commit-path isolation**: the `SaveSession` / `AsanaClient` initialization path must never fail or block because an external event destination is unavailable.

Three defining decisions, all traceable to the GAP-03 spec:

**Non-fatal by contract (NFR-001 / SC-004).** `EventEmitter.emit()` wraps every per-subscription transport call in a broad `except Exception` (annotated `# BROAD-CATCH: isolation`). Transport failures increment `failed` and log `event_emission_failed` + `event_dead_letter` structured events, but are never re-raised. `AutomationResult.success` is always `True` regardless of transport outcome.

**Thin payload principle (ADR-GAP03-003).** Envelopes carry entity GID + minimal metadata only. No entity state is embedded. Consumers must fetch full state from the API independently. The `_build_payload` method in `EventEmissionRule` enforces this by only attaching `process_type` (when present) and `section_gid`/`section_name` for `SECTION_CHANGED`.

**Feature-flag off by default (ADR-GAP03-005).** `EVENTS_ENABLED` env var defaults to `"false"`. When disabled, `matching_subscriptions()` returns an empty list before evaluating any subscriptions, and no SQS client is instantiated.

**Call site**: `setup_event_emission(engine)` is called unconditionally in `AsanaClient.__init__()` (line 267 of `client.py`) whenever `automation.enabled=True`. A `ValueError` from misconfigured env vars (enabled but no destination) propagates and aborts client initialization.

**Optional dep**: `autom8y-events>=1.2.0,<2.0.0` is declared in `pyproject.toml` as an optional group `[events]` (line 58) but is **never imported** anywhere in the implementation. The package is treated as a future forward-compatibility placeholder or was a vestigial registry entry; the actual transport is direct boto3 per ADR-GAP03-004.

## Conceptual Model

### Event Lifecycle

```
AsanaClient.__init__() (automation.enabled=True)
  -> setup_event_emission(engine)
       -> EventRoutingConfig.from_env()  [reads EVENTS_ENABLED, EVENTS_SQS_QUEUE_URL, EVENTS_SUBSCRIPTIONS]
       -> SQSTransport.from_boto3()
       -> EventEmitter(transport, config)
       -> EventEmissionRule(emitter)
       -> engine.register(rule)

SaveSession completes entity mutation
  -> AutomationEngine iterates registered rules
     -> EventEmissionRule.should_trigger(entity, event, context)
          -> config.matching_subscriptions(event_type, entity_type)
          -> if matching: stores event_value in self._last_event; returns True
     -> EventEmissionRule.execute_async(entity, context)
          -> EventType(self._last_event)   [ValueError -> AutomationResult with skipped_reason]
          -> _build_payload(entity, event_type, context)
          -> EventEnvelope.build(...)       [auto-generates event_id=uuid4, correlation_id=uuid4, timestamp=UTC now]
          -> emitter.emit(envelope)
               -> config.matching_subscriptions() [second lookup]
               -> for each sub: transport.publish(envelope, sub.destination)
                    SQSTransport: asyncio.to_thread(boto3.send_message, QueueUrl=..., MessageBody=json, MessageAttributes={event_type, entity_type, schema_version})
               -> EmitResult(attempted, succeeded, failed)
          -> AutomationResult(success=True, enhancement_results={events_attempted, events_succeeded, events_failed})
```

### Subscription Matching

`SubscriptionEntry.matches(event_type, entity_type)` applies AND logic:
- `event_types` empty → wildcard (matches all event types)
- `entity_types` empty → wildcard (matches all entity types)
- Both empty → matches everything

Two configuration modes:
1. **Simple**: `EVENTS_SQS_QUEUE_URL=<url>` creates a single wildcard `SubscriptionEntry`.
2. **Advanced**: `EVENTS_SUBSCRIPTIONS=<json_array>` parses an array of objects with `destination` (required), `event_types` (optional), `entity_types` (optional).

### Event Types

`EventType(StrEnum)` — four values, inheriting from `str` for backward compatibility with `TriggerCondition.matches()` string comparisons:

| Value | Constant |
|-------|----------|
| `"created"` | `EventType.CREATED` |
| `"updated"` | `EventType.UPDATED` |
| `"section_changed"` | `EventType.SECTION_CHANGED` |
| `"deleted"` | `EventType.DELETED` |

### Envelope Fields

`EventEnvelope` is a frozen dataclass (immutable carrier):

| Field | Type | Source |
|-------|------|--------|
| `schema_version` | `str` | Hardcoded `"1.0"` |
| `event_id` | `str` | `uuid.uuid4()` — idempotency key |
| `event_type` | `EventType` | From `should_trigger` state |
| `entity_type` | `str` | `type(entity).__name__` |
| `entity_gid` | `str` | `entity.gid` |
| `timestamp` | `str` | `datetime.now(UTC).isoformat()` |
| `source` | `str` | `"save_session"` (configurable in rule init) |
| `correlation_id` | `str` | `uuid4()` — **auto-generated; NOT threaded from inbound request** |
| `causation_id` | `str \| None` | Optional; not set by current rule |
| `payload` | `dict` | Thin: `process_type`, `section_gid`/`section_name` (SECTION_CHANGED only) |

### SQS Message Attributes

Three attributes sent alongside the JSON body, enabling SQS filter policies on the consumer side: `event_type`, `entity_type`, `schema_version` (all `DataType: "String"`).

## Implementation Map

| File | Class / Symbol | Role |
|------|---------------|------|
| `src/autom8_asana/automation/events/__init__.py` | `setup_event_emission(engine)` | Entry point: reads env, wires `SQSTransport` + `EventEmissionRule` into engine; called from `client.py:267` |
| `src/autom8_asana/automation/events/types.py` | `EventType(StrEnum)` | Closed 4-value vocabulary (GAP-03 FR-001 / ADR-GAP03-001) |
| `src/autom8_asana/automation/events/envelope.py` | `EventEnvelope` (frozen dataclass) | Immutable carrier; `build()` factory auto-generates `event_id`, `correlation_id`, `timestamp` |
| `src/autom8_asana/automation/events/config.py` | `SubscriptionEntry`, `EventRoutingConfig` | Declarative routing from env vars; startup validation (enabled + no destination → `ValueError`) |
| `src/autom8_asana/automation/events/emitter.py` | `EventEmitter`, `EmitResult` | Orchestrates per-subscription dispatch; absorbs all transport exceptions; returns `EmitResult` |
| `src/autom8_asana/automation/events/rule.py` | `EventEmissionRule` | `AutomationRule` protocol impl; holds `_last_event` state thread; builds envelope and delegates to emitter |
| `src/autom8_asana/automation/events/transport.py` | `EventTransport` (Protocol), `InMemoryTransport`, `SQSTransport` | Transport layer; SQS uses `asyncio.to_thread(boto3.send_message)` |
| `src/autom8_asana/client.py` (lines 263–270) | `AsanaClient.__init__` | Only call site; invokes `setup_event_emission` unconditionally when automation is enabled |

### Test Coverage

| Test File | Covers |
|-----------|--------|
| `tests/unit/automation/events/test_config.py` | `EventRoutingConfig.from_env()`, subscription parsing, validation |
| `tests/unit/automation/events/test_emitter.py` | `EventEmitter.emit()`, error absorption, `EmitResult` |
| `tests/unit/automation/events/test_envelope.py` | `EventEnvelope.build()`, `to_json_dict()` |
| `tests/unit/automation/events/test_rule.py` | `EventEmissionRule.should_trigger()`, `execute_async()`, `_build_payload()` |
| `tests/unit/automation/events/test_transport.py` | `InMemoryTransport` |
| `tests/unit/automation/events/test_sqs_transport.py` | `SQSTransport.publish()`, message attributes |
| `tests/unit/automation/events/test_types.py` | `EventType` StrEnum |
| `tests/unit/automation/events/test_wiring.py` | `setup_event_emission()` wiring |
| `tests/unit/automation/events/test_engine_integration.py` | End-to-end rule registration + engine dispatch |
| `tests/integration/events/test_sqs_integration.py` | SQS integration (LocalStack or mock SQS) |

## Boundaries and Failure Modes

### Scope Boundaries — What This Feature Does NOT Do

- Does **not** retry failed deliveries. Failed envelopes are log-only (`event_dead_letter`). There is no DLQ, no persistence, no retry schedule.
- Does **not** embed entity state in envelopes. Thin payloads only (ADR-GAP03-003). Consumers must re-fetch.
- Does **not** thread inbound `X-Request-ID` into `correlation_id`. The field is auto-generated with `uuid4()` in `EventEnvelope.build()`. No mechanism passes the HTTP request ID through `AutomationContext` to the envelope.
- Does **not** use the `autom8y-events` optional dependency. The package is listed in `pyproject.toml [events]` extras but is never imported. The transport is direct boto3.
- Does **not** support non-SQS transports in production. `InMemoryTransport` is test-only.
- Does **not** implement causation chain. `causation_id` field exists on `EventEnvelope` but `EventEmissionRule` never sets it.

### Failure Mode Catalog

| Failure | Behavior | Signal |
|---------|----------|--------|
| SQS unavailable / network error | Exception caught in `emitter.emit()`, `failed += 1` | `event_emission_failed` (WARNING) + `event_dead_letter` (WARNING) |
| `EVENTS_ENABLED=true` but no destination | `ValueError` at `EventRoutingConfig.from_env()` → propagates through `setup_event_emission` → aborts `AsanaClient.__init__` | `event_routing_config_invalid` (ERROR) then exception |
| Unknown `event_type` string (not in `EventType`) | `ValueError` caught in `execute_async`, returns `AutomationResult(success=True, skipped_reason="unknown_event_type:<value>")` | `skipped_reason` in result metadata |
| No matching subscriptions | `EmitResult(attempted=0)`, no transport call | `event_no_matching_subscriptions` (DEBUG) |
| `EVENTS_ENABLED=false` | `matching_subscriptions()` returns `[]` immediately | `event_emission_disabled` (DEBUG) |

### State Coupling Risk

`EventEmissionRule` stores `self._last_event` (a `str`) between `should_trigger()` and `execute_async()`. This is **safe only when the engine calls them consecutively per rule per invocation**. Concurrent engine invocations sharing a single rule instance would race on this field. Safe under current `AutomationEngine` design (sequential rule iteration per save), but represents a latent hazard if engine parallelism is introduced.

### Interaction Points

- **Consumes from**: `AutomationEngine` (rule registration + dispatch protocol), `AutomationContext.save_result` (for SECTION_CHANGED payload), `autom8_asana.persistence.models.ActionType` (for section extraction), `autom8_asana.automation.base.TriggerCondition`.
- **Provides to**: External SQS consumers (envelope JSON + message attributes). No other internal packages depend on this module at runtime.
- **Wired by**: `AsanaClient.__init__` (the only call site for `setup_event_emission`).

### Configuration Boundaries

| Env Var | Valid Values | Invalid / Error Condition |
|---------|-------------|--------------------------|
| `EVENTS_ENABLED` | `"true"` or `"false"` (default `"false"`) | Any truthy-like value besides `"true"` is treated as disabled |
| `EVENTS_SQS_QUEUE_URL` | Any SQS queue URL string | Empty when `EVENTS_ENABLED=true` and no `EVENTS_SUBSCRIPTIONS` → `ValueError` |
| `EVENTS_SUBSCRIPTIONS` | JSON array; each object requires `"destination"` | Missing `destination` key → `ValueError`; malformed JSON → `json.JSONDecodeError` |

## Knowledge Gaps

1. **`autom8y-events` optional dependency** listed in `pyproject.toml` extras but never imported. Likely a vestigial forward-compatibility reservation or planning artifact. Not used by any code path.
2. **`correlation_id` is not threaded from inbound requests.** `EventEnvelope.build()` auto-generates a `uuid4()` when `correlation_id=None`. `EventEmissionRule.execute_async()` never passes a correlation ID from `AutomationContext`. Cross-service loop detection using this field is limited to within-session scope.
3. **`causation_id` is always `None`.** The field exists on `EventEnvelope` but is never set by `EventEmissionRule`. Causation chains cannot be reconstructed from events.
4. **Dead letter handling is log-only.** Failed envelopes are not persisted, not sent to an SQS DLQ, and not retried. Under sustained SQS unavailability, events are silently lost after logging.

```metadata
source_files_read: 7
test_files_observed: 10
call_sites_traced: 1
known_gaps_carried_forward: 2
known_gaps_resolved: 1
gaps_newly_identified: 2
confidence_basis: all_6_source_files_read_directly + call_site_verified + test_inventory_complete
```
