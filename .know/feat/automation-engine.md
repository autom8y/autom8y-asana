---
domain: feat/automation-engine
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/automation/**/*.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.82
format_version: "1.0"
---

# Automation Rule Engine and Workflow Orchestration

## Purpose and Design Rationale

The automation subsystem handles: **reactive rule evaluation** (triggered by entity state changes in SaveSession post-commit) and **batch workflow orchestration** (Lambda-dispatched operations against Asana and satellite services).

Primary use case: when a Sales Process task moves to "CONVERTED" section, the engine automatically creates an Onboarding Process task from a template, seeds fields, places in hierarchy, sets assignee, and adds a comment.

## Conceptual Model

### Two Tracks

**Track 1 -- Reactive**: `SaveSession.commit_async()` -> `AutomationEngine.evaluate_async()` -> per-entity event detection -> rule matching -> `rule.execute_async()`.

**Track 2 -- Batch**: Lambda/REST -> `WorkflowRegistry.get()` -> `workflow.validate_async()` -> `enumerate_async()` -> `execute_async()` with semaphore fan-out.

### Key Abstractions

- `AutomationRule` (Protocol): `should_trigger()` + `execute_async()`
- `AutomationEngine`: Rule registry, post-commit dispatch, per-rule BROAD-CATCH isolation (NFR-003)
- `AutomationContext`: Client/config/loop-guard carrier, max_cascade_depth=5, visited set dedup
- `PipelineConversionRule`: Built-in rule (SALES->ONBOARDING), 7 sequential steps
- `WorkflowAction` (ABC): Base for batch workflows
- `BridgeWorkflowAction`: Shared base for data-attachment bridge workflows
- `WorkflowRegistry`: Per-process dict registry with SystemContext reset

### PipelineConversionRule Steps

1. Pre-transition validation, 2. Stage config lookup, 3. Template discovery, 4. Task duplication + placement, 5. Field seeding (4-layer precedence), 6. Hierarchy placement (3-strategy ProcessHolder resolution), 7. Assignee resolution (4-step cascade), 8. Onboarding comment, 9. Post-transition validation.

## Implementation Map

Reactive: engine.py, base.py, context.py, config.py, pipeline.py, seeding.py, events/types.py, validation.py, waiter.py, templates.py.
Batch: workflows/base.py, bridge_base.py, protocols.py, registry.py, mixins.py, section_resolution.py, pipeline_transition.py, conversation_audit/workflow.py, insights/workflow.py, payment_reconciliation/workflow.py.

## Boundaries and Failure Modes

- `automation_enabled=False` in nested SaveSession (hierarchy placement) prevents recursive triggering
- BROAD-CATCH boundaries intentional in engine and bridge base
- `EventType.SECTION_CHANGED` detected from `action_results`, not dirty fields (ADR-0055)
- Only "inline" rules_source supported in V1
- `DataSource`/interop protocol migration blocked until interop gains async context manager support

### Scars: SCAR-016 (date_range_days not forwarded), SCAR-017 (csv_row_count missing), SCAR-026 (non-existent method masked by MagicMock), SCAR-011b (silent workflow import errors).

## Knowledge Gaps

1. Polling scheduler subpackage not read (separate feature).
2. `pipeline_transition.py` workflow internals not read.
3. `AutomationEventEmitter` / events/ subpackage not read.
4. CONSULTATION process type automation impact unknown.
