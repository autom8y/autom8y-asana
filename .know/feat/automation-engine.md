---
domain: feat/automation-engine
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/automation/"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.95
format_version: "1.0"
---

# Automation Rule Engine and Workflow Orchestration

## Purpose and Design Rationale

The automation subsystem solves two distinct problems that both live under `automation/`:

**Problem 1 — Reactive rules**: When a Sales Process task moves to the "CONVERTED" section in
Asana, the system automatically creates an Onboarding Process from a template, seeds fields from
the hierarchy (Business -> Unit -> Process carry-through), places the new task in the correct
hierarchy position, sets the assignee from rep field cascade, and adds an onboarding comment. This
entire sequence must be fire-and-forget from the perspective of `SaveSession.commit_async()` — one
rule failure must not abort the commit or affect other rules (NFR-003).

**Problem 2 — Batch workflows**: Lambda-dispatched operations process large entity sets against
Asana and satellite services (autom8y-data). Concrete implementations: ConversationAuditWorkflow,
InsightsExportWorkflow, PaymentReconciliationWorkflow, PipelineTransitionWorkflow. These are
idempotent, semaphore-bounded fan-out operations with per-entity BROAD-CATCH isolation.

**Why these coexist**: Both tracks share the `AutomationContext` carrier, the `WorkflowRegistry`,
and the BROAD-CATCH isolation philosophy. They represent different invocation models
(post-commit reactive vs Lambda batch) over the same underlying Asana client surface.

**Key design decisions and their rationale**:
- **Protocol-based rules** (FR-008): `AutomationRule` is a `runtime_checkable` Protocol, not an
  ABC. This allows mocks in tests to satisfy the interface without explicit subclassing
  (learned from SCAR-026 — MagicMock without `spec=` masked missing method errors).
- **EventType StrEnum** (ADR-GAP03-001): Replaced hardcoded string event literals with
  `EventType(StrEnum)` for closed vocabulary with backward-compatible str comparison.
- **ADR-0055**: `EventType.SECTION_CHANGED` is detected from `action_results`, not from dirty
  fields. A Process moved to a section has no dirty fields, so it would not appear in
  `save_result.succeeded` — it must be collected from `save_result.action_results` with
  `ActionType.MOVE_TO_SECTION`.
- **ADR-0018**: Optional pre/post transition validation with `validate_mode="warn"` (default) or
  `"block"`. Warn mode proceeds even on validation failure; block mode aborts the transition.
- **WorkflowRegistry**: per-invocation (not cross-invocation singleton). Lambda containers get
  a fresh registry per warm invocation. Registered with `SystemContext.register_reset()` for
  test isolation (LB-003 pattern).
- **rules_source**: V1 only supports `"inline"` (programmatic registration). `"file"` and `"api"`
  are reserved in `AutomationConfig` but not implemented.

**Child features carved out per census**: `seeding.py` (FieldSeeder) is documented under the
`business-seeder` feature (`.know/feat/business-seeder.md`). The `events/` subpackage is
documented under the `event-emission` feature (`.know/feat/event-emission.md`). The `polling/`
subpackage is documented under the `polling-scheduler` feature
(`.know/feat/polling-scheduler.md`). This entry covers the engine core + concrete workflows.

---

## Conceptual Model

### Two Tracks

**Track 1 — Reactive (post-commit)**:
```
SaveSession.commit_async()
  -> AutomationEngine.evaluate_async(save_result, client)
     -> collect entities from save_result.succeeded
     -> collect MOVE_TO_SECTION entities from save_result.action_results (ADR-0055)
     -> per entity: _detect_event() -> _build_event_context()
     -> per rule: rule.should_trigger(entity, event, context)
     -> context.can_continue(entity_gid, rule_id)  [depth + visited guard]
     -> rule.execute_async(entity, context)  [BROAD-CATCH isolation per NFR-003]
```

**Track 2 — Batch (Lambda/REST)**:
```
Lambda invocation or POST /api/v1/workflows/{id}/invoke
  -> WorkflowRegistry.get(workflow_id) -> WorkflowAction
  -> workflow.validate_async()          [kill-switch + data source health]
  -> workflow.enumerate_async(scope)    [fast-path for entity_ids, full enumeration otherwise]
  -> workflow.execute_async(entities, params)  [semaphore fan-out, BROAD-CATCH per entity]
  -> WorkflowResult {total, succeeded, failed, skipped, errors}
```

### Key Abstractions

| Abstraction | Location | Role |
|---|---|---|
| `AutomationRule` (Protocol) | `base.py` | `id`, `name`, `trigger`, `should_trigger()`, `execute_async()` |
| `TriggerCondition` | `base.py` | `entity_type + event + filters` matching; `matches()` does case-sensitive filter check |
| `Action` | `base.py` | Declared action type + params; used for configuration, not runtime dispatch |
| `AutomationEngine` | `engine.py` | Rule registry, post-commit dispatch, per-rule BROAD-CATCH isolation |
| `AutomationContext` | `context.py` | Client/config/loop-guard carrier; `max_cascade_depth=5`, shared `visited` set |
| `AutomationConfig` | `config.py` | `enabled`, `max_cascade_depth`, `rules_source`, `pipeline_stages` dict |
| `PipelineStage` | `config.py` | Per-stage config: `project_gid`, `template_section`, `target_section`, `due_date_offset_days`, `assignee_gid`, field lists, `field_name_mapping` |
| `AssigneeConfig` | `config.py` | 4-step assignee cascade config: `assignee_source` field, `assignee_gid`, unit.rep[0], business.rep[0] |
| `PipelineConversionRule` | `pipeline.py` | Built-in rule: SALES->ONBOARDING conversion (configurable source/target/trigger) |
| `ValidationResult` | `validation.py` | Pre/post transition validation outcome; `valid`, `errors`, `warnings` |
| `SubtaskWaiter` | `waiter.py` | Polls for subtask availability after duplication (ADR-0111) |
| `TemplateDiscovery` | `templates.py` | Fuzzy template section/task finder (ADR-0106) |
| `WorkflowAction` (ABC) | `workflows/base.py` | `workflow_id`, `enumerate_async(scope)`, `execute_async(entities, params)`, `validate_async()` |
| `BridgeWorkflowAction` | `workflows/bridge_base.py` | Intermediate base absorbing constructor, validate, enumerate, execute boilerplate |
| `BridgeOutcome` | `workflows/bridge_base.py` | Per-entity outcome: `gid`, `status` ("succeeded"/"failed"/"skipped"), `reason`, `error` |
| `WorkflowResult` | `workflows/base.py` | `total/succeeded/failed/skipped`, `errors`, `metadata`, `duration_seconds`, `failure_rate` |
| `WorkflowRegistry` | `workflows/registry.py` | Dict-based registry; per-invocation, resets via SystemContext |
| `AttachmentReplacementMixin` | `workflows/mixins.py` | Upload-first attachment replacement; `_delete_old_attachments()` |
| `DataSource` | `workflows/protocols.py` | Minimal protocol: `is_healthy()` raises on failure |
| `FormatEngine` | `workflows/protocols.py` | `render(data) -> bytes`; composable formatter protocol |
| `EventType` | `events/types.py` | StrEnum: CREATED, UPDATED, SECTION_CHANGED, DELETED |
| `EventEmissionRule` | `events/rule.py` | AutomationRule that builds EnventEnvelope and emits via EventEmitter |

### PipelineConversionRule Execution Steps

The rule's `execute_async()` runs 9 sequential steps (all non-fatal except step 0 type check):

1. Pre-transition validation (ADR-0018) — skipped if no `required_source_fields`
2. Stage config lookup via `context.config.get_pipeline_stage(target_type.value)` — fatal if missing
3. Template discovery via `discover_template_async()` — fatal if no template found
4. Task duplication (`duplicate_from_template_async`) + add to project + section placement (G3 Gap Fix) + due date (G4 Gap Fix) + subtask wait (ADR-0111)
5. Field seeding via `FieldSeeder` (4-layer precedence: business -> unit -> process carry-through -> computed); delegated to `business-seeder` feature
6. Hierarchy placement via `_place_in_hierarchy_async()` — 3-strategy `ProcessHolder` resolution; graceful degradation (FR-HIER-003)
7. Assignee set via `_set_assignee_from_rep_async()` — 4-step AssigneeConfig cascade (ADR-0113)
8. Onboarding comment creation — FR-COMMENT-001 through FR-COMMENT-005
9. Post-transition validation (advisory, always `valid=True`)

### ProcessHolder Resolution (3-strategy chain)

```
strategy 1: source_process.process_holder (public property)
strategy 2: unit.process_holder (public property)
strategy 3: ResolutionContext.resolve_holder_async(ProcessHolder)  [session-cached, public API]
-> FR-HIER-003: all three returning None -> graceful degradation (log warning, return False)
```

### Loop Prevention (2-layer)

`AutomationContext.can_continue(entity_gid, rule_id)`:
1. Depth guard: `depth >= config.max_cascade_depth` (default 5)
2. Visited set: `(entity_gid, rule_id)` pair already in `visited`

Child contexts created via `context.child_context()` share the `visited` set by reference —
loop detection works across the entire cascade chain.

### Inter-feature Relationships

| Direction | Feature | Relationship |
|---|---|---|
| Delegates to | `business-seeder` | `FieldSeeder` in `automation/seeding.py` does field seeding |
| Delegates to | `event-emission` | `EventEmissionRule` + `EventEmitter` in `automation/events/` |
| Delegates to | `polling-scheduler` | `automation/polling/` APScheduler-based batch scheduling |
| Consumes | `lifecycle-engine` | `PipelineTransitionWorkflow` routes to `LifecycleEngine.handle_transition_async()` |
| Consumes | `save-session` | `SaveSession(automation_enabled=False)` used inside hierarchy placement (prevents re-trigger) |
| Consumes | `resource-clients` | `AsanaClient.tasks`, `.stories`, `.sections`, `.attachments` |
| Consumes | `data-service-client` | `DataServiceClient` satisfies `DataSource` protocol for bridge validation |
| Provides to | `lambda-handlers` | `WorkflowAction` implementations dispatched from workflow_handler, conversation_audit, insights_export, payment_reconciliation Lambda handlers |
| Provides to | `workflow-invoke-api` | `WorkflowRegistry` looked up by `api/routes/workflows.py` at invocation time |

---

## Implementation Map

### Core Engine Package (`automation/`)

| File | LOC (est.) | Primary Purpose |
|---|---|---|
| `engine.py` | ~338 | `AutomationEngine`: rule registry, evaluate_async(), _detect_event(), _build_event_context() |
| `base.py` | ~203 | `AutomationRule` Protocol, `TriggerCondition`, `Action` dataclasses |
| `context.py` | ~111 | `AutomationContext`: client/config carrier, can_continue(), mark_visited(), child_context() |
| `config.py` | ~157 | `AutomationConfig`, `PipelineStage`, `AssigneeConfig` |
| `pipeline.py` | ~959 | `PipelineConversionRule`: full Sales->Onboarding automation (largest file in engine) |
| `seeding.py` | ~816 | `FieldSeeder` + `WriteResult` — **delegated to `business-seeder` feature** |
| `validation.py` | ~50 | `ValidationResult`: pre/post transition validation outcome |
| `waiter.py` | ~80 | `SubtaskWaiter`: polling-based subtask readiness (ADR-0111) |
| `templates.py` | ~80 | `TemplateDiscovery`: fuzzy template section/task matching (ADR-0106) |
| `__init__.py` | minimal | Public re-exports |

### Events Sub-Package (`automation/events/`) — see `event-emission` feature

| File | Primary Purpose |
|---|---|
| `types.py` | `EventType` StrEnum: CREATED, UPDATED, SECTION_CHANGED, DELETED |
| `emitter.py` | `EventEmitter`: routes envelopes to matching subscriptions; BROAD-CATCH isolation |
| `rule.py` | `EventEmissionRule`: AutomationRule implementation for event emission |
| `envelope.py` | `EventEnvelope`: immutable event record with `build()` factory |
| `transport.py` | `EventTransport` Protocol, `InMemoryTransport`, `SQSTransport` (boto3 via asyncio.to_thread) |
| `config.py` | `EventRoutingConfig` + `SubscriptionEntry`: `from_env()` reads EVENTS_ENABLED, EVENTS_SQS_QUEUE_URL, EVENTS_SUBSCRIPTIONS |

### Polling Sub-Package (`automation/polling/`) — see `polling-scheduler` feature

7 files: `polling_scheduler.py`, `trigger_evaluator.py`, `action_executor.py`, `config_schema.py`, `config_loader.py`, `cli.py`, `structured_logger.py` (added in latest cycle).

### Workflows Package (`automation/workflows/`)

| File | LOC (est.) | Primary Purpose |
|---|---|---|
| `base.py` | ~185 | `WorkflowAction` ABC, `WorkflowResult`, `WorkflowItemError` |
| `bridge_base.py` | ~314 | `BridgeWorkflowAction`: intermediate base absorbing constructor, validate, enumerate, execute |
| `protocols.py` | ~120 | `DataSource` Protocol, `FormatEngine` Protocol; TENSION-006 coverage map |
| `registry.py` | ~99 | `WorkflowRegistry`, `get_workflow_registry()`, `reset_workflow_registry()` |
| `mixins.py` | ~79 | `AttachmentReplacementMixin`: `_delete_old_attachments()` |
| `pipeline_transition.py` | ~200 | `PipelineTransitionWorkflow`: batch CONVERTED/DID NOT CONVERT processing via LifecycleEngine |
| `section_resolution.py` | ~65 | `resolve_section_gids()`: name->GID resolution via SectionsClient (30-min cached) |
| `conversation_audit/workflow.py` | large | `ConversationAuditWorkflow(BridgeWorkflowAction)` |
| `insights/workflow.py` | large | `InsightsExportWorkflow(BridgeWorkflowAction)` |
| `insights/formatter.py` | ~1105 | HTML formatter for insights export |
| `insights/tables.py` | medium | Table builders for insights |
| `payment_reconciliation/workflow.py` | medium | `PaymentReconciliationWorkflow(BridgeWorkflowAction)` |
| `payment_reconciliation/formatter.py` | medium | CSV formatter for payment reconciliation |

### Entry Points

- **Reactive track**: `persistence/session.py` -> `AutomationEngine.evaluate_async()` post-commit
- **Batch track (Lambda)**: `lambda_handlers/workflow_handler.py` -> `WorkflowRegistry.get()` -> `workflow.validate_async()` -> `workflow.enumerate_async()` -> `workflow.execute_async()`
- **Batch track (HTTP)**: `api/routes/workflows.py` -> same path via `WorkflowHandlerConfig`
- **Startup registration**: `api/lifespan.py` step 12 calls `register_workflow_config()` ×2 (insights-export, conversation-audit)

### Public API Surface

- `AutomationEngine.register(rule)` / `unregister(rule_id)` / `evaluate_async(save_result, client)`
- `AutomationConfig` (configured in `AsanaConfig`)
- `PipelineConversionRule(source_type, target_type, trigger_section, required_source_fields, validate_mode)` — primary user-visible automation rule
- `WorkflowRegistry.register(workflow)` / `get(workflow_id)` / `list_ids()`
- `WorkflowAction` ABC (implement to create new batch workflows)
- `BridgeWorkflowAction` (subclass for data-attachment bridge workflows)
- `DataSource` Protocol / `FormatEngine` Protocol

### Test Coverage

Unit tests in `tests/unit/automation/`:
- `test_engine.py` — AutomationEngine evaluate_async, rule registration, BROAD-CATCH isolation
- `test_pipeline.py` — PipelineConversionRule execution steps
- `test_pipeline_hierarchy.py` — ProcessHolder resolution strategies (FR-HIER-001 through FR-HIER-003)
- `test_base.py` — TriggerCondition.matches(), AutomationRule Protocol check
- `test_context.py` — AutomationContext.can_continue(), child_context(), loop detection
- `test_config.py` — AutomationConfig validation, PipelineStage defaults
- `test_assignee_resolution.py` — 4-step AssigneeConfig cascade (FR-ASSIGN-001 through FR-ASSIGN-006)
- `test_onboarding_comment.py` — comment text building
- `test_validation.py` — ValidationResult pre/post transition
- `test_waiter.py` — SubtaskWaiter polling logic
- `test_templates.py` — TemplateDiscovery fuzzy matching
- `test_seeding.py`, `test_seeding_write.py` — FieldSeeder (also in `business-seeder`)
- `test_integration.py` — end-to-end rule execution integration
- `test_models.py` — AutomationResult model

Unit tests in `tests/unit/automation/events/`:
- `test_config.py`, `test_emitter.py`, `test_engine_integration.py`, `test_envelope.py`
- `test_rule.py`, `test_sqs_transport.py`, `test_transport.py`, `test_types.py`, `test_wiring.py`

Unit tests in `tests/unit/automation/workflows/`:
- `test_base.py`, `test_bridge_base.py`, `test_protocols.py`, `test_registry.py`
- `test_section_resolution.py`, `test_pipeline_transition.py`
- `test_conversation_audit.py`, `test_insights_export.py`, `test_insights_formatter.py`
- `test_payment_reconciliation.py`, `test_attachment_mixin.py`
- `payment_reconciliation/test_formatter.py`

Integration tests: `tests/integration/automation/workflows/test_conversation_audit_e2e.py`

---

## Boundaries and Failure Modes

### Explicit Scope Boundaries

This feature does NOT:
- Implement the field seeding domain logic (delegated to `business-seeder` / `FieldSeeder`)
- Implement the event transport or subscription management (delegated to `event-emission`)
- Implement the APScheduler polling loop (delegated to `polling-scheduler`)
- Support `rules_source = "file"` or `rules_source = "api"` (V1 only supports `"inline"`)
- Support async context managers on `DataSource` / interop protocols (TENSION-006 migration blocked)

### BROAD-CATCH Boundaries

Three intentional BROAD-CATCH boundaries:
1. `engine.py:224` — per-rule isolation: one rule exception does not abort the rule evaluation loop
2. `pipeline.py:491` — rule-level isolation in PipelineConversionRule.execute_async() catch-all
3. `bridge_base.py:226` — per-entity isolation in BridgeWorkflowAction.execute_async() semaphore fan-out

Each is annotated with `# BROAD-CATCH: isolation` and a `# noqa: BLE001` suppression.

### H-006: trace_computation Gap (OPEN)

`bridge_base.py:191-195` documents a pending observability gap: `@trace_computation` is not
applied to `execute_async()` because the decorator was not available in `autom8y-telemetry 0.6.1`
at time of writing. Tracked as H-006 in `.know/obs.md`. Remains open at source_hash `8980bcd7`.
When the decorator is published, apply: `@trace_computation("bridge.execute", engine="autom8y-asana")`.

### TENSION-006: DataServiceClient / interop Protocol Gap

`protocols.py:32-61` documents that `DataSource.is_healthy()` overlaps with
`DataReadProtocol.health_check()` from `autom8y_client_sdk.data`, but with incompatible
signatures. `get_reconciliation_async()` and `get_export_csv_async()` have no interop analogues.
**Do NOT migrate `DataServiceClient` to interop protocols**. Interop covers ~30% of the client
surface. Migration blocked until interop gains reconciliation/export endpoints AND async context
manager support. See TENSION-006 in `.know/design-constraints.md`.

### Recursive Triggering Prevention

`SaveSession` called inside `_place_in_hierarchy_async()` uses `automation_enabled=False` to
prevent the hierarchy placement from re-triggering the engine. This is the only mechanism that
prevents infinite automation cascade during hierarchy operations.

### EventType.SECTION_CHANGED Detection (ADR-0055)

Section changes are detected from `save_result.action_results` where `action.action == ActionType.MOVE_TO_SECTION`, NOT from dirty fields. An entity moved to a section has no dirty fields. Agents modifying the event detection logic must maintain this invariant.

### Known Failure Modes (SCAR references)

| SCAR | Location | Failure | Status |
|---|---|---|---|
| SCAR-016 | workflow logic | `date_range_days` not forwarded to data client call | Historical/fixed |
| SCAR-017 | workflow logic | `csv_row_count` missing from workflow result metadata | Historical/fixed |
| SCAR-018 | workflow logic | Non-existent method masked by MagicMock without `spec=` | Historical; HYG-002 remediation ongoing (136 `spec=` calls in tests/ at HEAD) |
| SCAR-019 | workflow logic (SCAR-011b) | Silent workflow import errors at startup | Historical/fixed |

### Configuration Boundaries

- `max_cascade_depth` must be >= 1 (validated in `AutomationConfig.__post_init__`; raises `ConfigurationError`)
- `rules_source` must be one of `"inline"`, `"file"`, `"api"` (validated; `"file"` and `"api"` not implemented)
- `PipelineConversionRule` returns a failure `AutomationResult` (not exception) when target stage config is missing
- `BridgeWorkflowAction.validate_async()` returns errors (not exceptions) for kill-switch and circuit-breaker conditions
- `EventRoutingConfig.from_env()` raises `ValueError` at startup if `EVENTS_ENABLED=true` but no destination configured

### WorkflowRegistry Lifecycle

The registry is NOT a cross-invocation singleton. `get_workflow_registry()` returns a
module-level `_default_registry`, but `reset_workflow_registry()` is registered with
`SystemContext.register_reset()` — test isolation guaranteed. Lambda warm invocations that
reuse the container will use the same registry instance unless explicitly reset.

```metadata
confidence_rationale: >
  42 source files read directly (engine.py, base.py, context.py, config.py, pipeline.py, seeding.py,
  validation.py, waiter.py, templates.py, events/ 6 files, workflows/base.py, bridge_base.py,
  protocols.py, registry.py, mixins.py, pipeline_transition.py, section_resolution.py).
  Architecture seed, scar-tissue, design-constraints, obs.md, feat/INDEX.md consulted.
  Test file inventory confirmed (60+ test files covering automation/). Minor gap: concrete
  workflow implementations (conversation_audit/workflow.py, insights/workflow.py,
  payment_reconciliation/workflow.py) not read individually; internals inferred from base class
  and test file evidence. polling/ internals not read (separate polling-scheduler feature).
  Confidence: 0.95.
prior_source_hash: "c213958"
gaps_resolved:
  - "pipeline_transition.py workflow internals — now read"
  - "events/ subpackage — all 6 files read (types, emitter, rule, envelope, transport, config)"
  - "AutomationEventEmitter role — clarified as EventEmitter in events/emitter.py"
  - "seeding.py subsumed into business-seeder feature — explicitly documented"
  - "CONSULTATION process type impact — still unknown; not referenced in automation/ source"
```
