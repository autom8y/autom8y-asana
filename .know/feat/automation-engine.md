---
domain: feat/automation-engine
generated_at: "2026-03-18T12:39:28Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/automation/**/*.py"
  - "./docs/guides/automation-pipelines.md"
  - "./docs/guides/pipeline-automation-setup.md"
  - "./runbooks/RUNBOOK-pipeline-automation.md"
  - "./.know/architecture.md"
generator: theoros
source_hash: "2c604fa"
confidence: 0.91
format_version: "1.0"
---

# Automation Rule Engine and Workflow Orchestration

## Purpose and Design Rationale

### Problem Solved

The automation engine exists to eliminate manual operational work that is triggered by predictable state changes in Asana. Two classes of work drove the design:

1. **Reactive conversions**: When a Sales process moves to the "Converted" section, an Onboarding process must be created, populated with data from the hierarchy, assigned, and placed correctly -- a multi-step operation that was previously done manually.
2. **Periodic batch operations**: Refreshing conversation CSV attachments for ContactHolders, exporting insights HTML reports for Offers, and batch-processing pipeline transitions -- operations that must run on a schedule across a collection of entities.

### Design Decisions

**Two-mode architecture (event-driven vs. batch)**: The engine deliberately provides two distinct execution modes. Event-driven rules execute inline after `SaveSession.commit_async()` completes. Batch workflows execute on a cron schedule via `PollingScheduler`. This separation means real-time entity saves never block on batch concerns, and batch jobs never trigger per-entity rule evaluation.

**Isolation-first failure model (NFR-003)**: Rule execution failures are caught per-rule and per-entity with broad-catch exception handlers. A failing rule produces a failed `AutomationResult` but does not abort evaluation of other rules. This is a deliberate contract: automation is best-effort and must never break the write path.

**Cascade depth and visited-set loop prevention**: The engine tracks execution context via `AutomationContext`. Two layers prevent infinite loops: a maximum cascade depth (default: 5) prevents unbounded recursion when a rule-created entity triggers another rule; a visited set of `(entity_gid, rule_id)` tuples prevents the same rule from running twice on the same entity in one chain.

**V1 rules are inline only** (`rules_source = "inline"`): There is no YAML-driven or API-driven rule loading for event-driven rules in the current implementation. All rules are registered programmatically at startup via `engine.register(rule)`. The `rules_source` config supports `"file"` and `"api"` as future extension points only.

**Polling YAML is operator-owned**: The polling scheduler uses a separate YAML configuration (`config/pipeline-rules.yaml`). The distinction is explicit in the design: Operations owns the values; Developers own the schema. This allows operators to modify trigger thresholds without code changes.

**PipelineConversionRule is lazy-loaded**: `src/autom8_asana/automation/__init__.py` uses `__getattr__` to lazy-load `PipelineConversionRule` from `pipeline.py`. This breaks a circular import chain: `models.business.__init__` (bootstrap) -> cache -> config -> automation -> pipeline -> `models.business`.

**Pipeline vs. Lifecycle dual path (TENSION-007)**: `pipeline.py` (`PipelineConversionRule`) and `src/autom8_asana/lifecycle/` (`LifecycleEngine`) both handle pipeline transitions but are not duplicate. The design constraint notes that D-022 was closed -- lifecycle absorbed most behavior, but pipeline retains "essential pipeline differences lifecycle does not cover." The `PipelineTransitionWorkflow` (batch workflow) delegates to `LifecycleEngine.handle_transition_async()`, not to `PipelineConversionRule` directly.

### Alternatives Rejected

- **Sync rule execution**: Rules are async-only in V1. The docstring in `base.py` explicitly notes "Async-only for V1."
- **YAML-driven event rules**: Only batch polling uses YAML. Event-driven rules require code for type safety and to support complex conditions.
- **Propagating exceptions**: Rules swallow all exceptions and return failure results. This was a deliberate choice over letting failures propagate to the SaveSession caller.

---

## Conceptual Model

### Mental Model: Two Execution Planes

```
PLANE 1 -- Event-Driven (real-time, per-commit)
---------------------------------------------
SaveSession.commit_async()
    -> AutomationEngine.evaluate_async(save_result, client)
            -> detect event for each entity (CREATED / UPDATED / SECTION_CHANGED)
            -> for each rule: should_trigger(entity, event, context)?
            -> if yes: execute_async(entity, context)
            -> return List[AutomationResult]

PLANE 2 -- Batch (scheduled, per-collection)
---------------------------------------------
PollingScheduler (cron or APScheduler)
    -> _evaluate_rules()
            -> condition-based rules: TriggerEvaluator.evaluate_conditions() -> ActionExecutor
            -> workflow rules: WorkflowRegistry.get(workflow_id) -> workflow.enumerate_async() -> workflow.execute_async()
```

### Key Abstractions

**`AutomationRule` (Protocol)**: The contract for event-driven rules. Three required properties (`id`, `name`, `trigger`), two required methods (`should_trigger`, `execute_async`). Uses `@runtime_checkable` so `isinstance()` checks work at runtime.

**`TriggerCondition`**: Frozen dataclass. Specifies what entity type, what event, and what filter values must match. Calling `.matches(entity, event, context)` performs the check. Filters are applied as `context.get(key) == expected` with fallback to `getattr(entity, key)`.

**`EventType` (StrEnum)**: Closed vocabulary -- `CREATED`, `UPDATED`, `SECTION_CHANGED`, `DELETED`. Inherits from `str` for backward compatibility with string comparisons. Defined in `src/autom8_asana/automation/events/types.py`.

**`AutomationContext`**: Mutable execution context passed to each rule. Carries `client`, `config`, `depth`, `visited` (shared set across child contexts), and `save_result`. The `child_context()` method creates a new context with `depth + 1` and the same `visited` reference -- enabling loop detection across the entire cascade chain.

**`AutomationConfig`**: Frozen-ish dataclass (uses `@dataclass` not `frozen=True`). Contains `enabled` (master switch), `max_cascade_depth`, `rules_source`, and `pipeline_stages` (a `dict[str, PipelineStage]`). `PipelineStage` is the per-process-type configuration for pipeline transitions: which project, which template section, which target section, due date offset, assignee cascade, and field mappings.

**`WorkflowAction` (ABC)**: The contract for batch workflows. Three abstract methods: `enumerate_async(scope)`, `execute_async(entities, params)`, `validate_async()`. Each workflow owns its full lifecycle -- enumeration, processing, and reporting.

**`WorkflowRegistry`**: Simple dictionary-based registry. Workflows are registered at startup and looked up by `workflow_id` when the scheduler encounters an action with `type == "workflow"`.

**`EntityScope`**: Controls batch workflow targeting. When `scope.has_entity_ids` is `True`, workflows skip full enumeration and process only the specified GIDs. When `scope.has_entity_ids` is `False`, full enumeration runs. Constructed from `EntityScope.from_event(params)`.

### State / Lifecycle

For event-driven rules, there is no persistent state. Each `evaluate_async()` call creates a fresh `AutomationContext` with `depth=0` and an empty `visited` set.

For batch workflows, `WorkflowResult` provides the outcome. Each workflow also maintains internal per-run caches (e.g., `InsightsExportWorkflow._business_cache`, `ConversationAuditWorkflow._activity_map`) that are populated during a single execution cycle and not persisted.

### Terminology

- **Rule**: An event-driven automation trigger + action, registered in `AutomationEngine`.
- **Workflow**: A batch automation unit implementing `WorkflowAction`, registered in `WorkflowRegistry`.
- **Pipeline stage**: A named `PipelineStage` entry in `AutomationConfig.pipeline_stages`, keyed by process type string (e.g., `"onboarding"`).
- **Field seeding**: The act of computing and writing initial field values from the entity hierarchy (Business -> Unit -> source Process) to a newly created process.
- **Cascade depth**: The depth counter in `AutomationContext`. Starts at 0; incremented via `child_context()` when a rule-created entity triggers further automation.
- **Section-targeted enumeration**: Fetching tasks directly from specific section GIDs instead of project-level fetch + client-side filter. Used in `InsightsExportWorkflow` and `PipelineTransitionWorkflow` for efficiency. Falls back to project-level fetch if section resolution fails.

---

## Implementation Map

### Package Structure

```
src/autom8_asana/automation/
├── __init__.py              -- Public API surface (lazy-loads PipelineConversionRule)
├── base.py                  -- TriggerCondition, Action, AutomationRule (Protocol)
├── config.py                -- AutomationConfig, PipelineStage, AssigneeConfig
├── context.py               -- AutomationContext (loop prevention, cascade tracking)
├── engine.py                -- AutomationEngine (rule registry, evaluate_async)
├── pipeline.py              -- PipelineConversionRule (built-in conversion rule)
├── seeding.py               -- FieldSeeder (hierarchy cascade + carry-through)
├── templates.py             -- TemplateDiscovery
├── validation.py            -- ValidationResult (pre/post transition validation)
├── waiter.py                -- SubtaskWaiter (polls for async subtask creation)
├── events/
│   ├── config.py            -- EventRoutingConfig, subscription matching
│   ├── emitter.py           -- EventEmitter (routes envelopes to transports)
│   ├── envelope.py          -- EventEnvelope (event payload)
│   ├── rule.py              -- EventRule (event subscription definition)
│   ├── transport.py         -- EventTransport protocol + LogTransport
│   └── types.py             -- EventType StrEnum
├── polling/
│   ├── action_executor.py   -- ActionExecutor (executes actions on matched tasks)
│   ├── cli.py               -- CLI entry point (validate, evaluate, run)
│   ├── config_loader.py     -- ConfigurationLoader (YAML -> Pydantic)
│   ├── config_schema.py     -- AutomationRulesConfig, RuleConfig, ScheduleConfig, ActionConfig
│   ├── polling_scheduler.py -- PollingScheduler (APScheduler or cron single-shot)
│   ├── structured_logger.py -- StructuredLogger (JSON output for log aggregation)
│   └── trigger_evaluator.py -- TriggerEvaluator (evaluates YAML conditions against tasks)
└── workflows/
    ├── base.py              -- WorkflowAction (ABC), WorkflowResult, WorkflowItemError
    ├── conversation_audit.py -- ConversationAuditWorkflow ("conversation-audit")
    ├── insights_export.py   -- InsightsExportWorkflow ("insights-export")
    ├── insights_formatter.py -- HTML report composition (InsightsReportData, compose_report)
    ├── insights_tables.py   -- TABLE_SPECS, TableSpec, DispatchType (12 table definitions)
    ├── mixins.py            -- AttachmentReplacementMixin (upload-first, delete-old)
    ├── pipeline_transition.py -- PipelineTransitionWorkflow ("pipeline-transition")
    ├── registry.py          -- WorkflowRegistry
    └── section_resolution.py -- resolve_section_gids() utility
```

### Key Entry Points and Type Signatures

**`AutomationEngine.evaluate_async`** -- called by `SaveSession` after commit:
```python
async def evaluate_async(
    self,
    save_result: SaveResult,
    client: AsanaClient,
) -> list[AutomationResult]
```

**`AutomationEngine.register`** -- called at application startup:
```python
def register(self, rule: AutomationRule) -> None  # raises ValueError on duplicate ID
```

**`PipelineConversionRule.__init__`** -- built-in rule constructor:
```python
def __init__(
    self,
    source_type: ProcessType = ProcessType.SALES,
    target_type: ProcessType = ProcessType.ONBOARDING,
    trigger_section: ProcessSection = ProcessSection.CONVERTED,
    required_source_fields: list[str] | None = None,
    validate_mode: Literal["warn", "block"] = "warn",
) -> None
```

**`WorkflowAction.enumerate_async`** / **`execute_async`** -- batch workflow lifecycle:
```python
async def enumerate_async(self, scope: EntityScope) -> list[dict[str, Any]]
async def execute_async(self, entities: list[dict[str, Any]], params: dict[str, Any]) -> WorkflowResult
async def validate_async(self) -> list[str]
```

**`FieldSeeder.seed_fields_async`** -- main seeding entry point:
```python
async def seed_fields_async(
    self,
    business: Business | None,
    unit: Unit | None,
    source_process: Process,
) -> dict[str, Any]
```

**`FieldSeeder.write_fields_async`** -- persists seeded fields to API:
```python
async def write_fields_async(
    self,
    target_task_gid: str,
    fields: dict[str, Any],
    field_name_mapping: dict[str, str] | None = None,
    target_task: Any | None = None,
) -> WriteResult
```

**`PollingScheduler.run_once`** -- production cron entry point:
```python
def run_once(self) -> None  # acquires file lock, evaluates all enabled rules, releases lock
```

### Data Flow: Event-Driven Path

```
Asana webhook event / SaveSession commit
    -> save_result.succeeded (list[AsanaResource]) + save_result.action_results
    -> AutomationEngine.evaluate_async()
        -> _detect_event(entity, save_result) -> EventType
        -> _build_event_context(entity, event, save_result) -> dict
        -> for each rule: rule.should_trigger(entity, event, context)?
            -> context.can_continue(entity_gid, rule.id)?
                -> context.mark_visited(entity_gid, rule.id)
                -> await rule.execute_async(entity, context)
                    -> [PipelineConversionRule] discover template -> duplicate task -> seed fields
                        -> place in hierarchy -> set assignee -> create comment
                    -> return AutomationResult
    -> List[AutomationResult]
```

**Important**: `MOVE_TO_SECTION` action results are also evaluated (lines 153-163 of `engine.py`). A Process moved to a section via `ActionType.MOVE_TO_SECTION` has no dirty fields, so it will not appear in `save_result.succeeded`. The engine explicitly adds such entities to the evaluation list.

### Data Flow: Batch Workflow Path

```
PollingScheduler._evaluate_rules()
    -> rule.schedule is not None and rule.action.type == "workflow"?
        -> _dispatch_scheduled_workflow(rule)
            -> _should_run_schedule(schedule) -> bool
            -> workflow_registry.get(workflow_id) -> WorkflowAction
            -> _execute_workflow_async(workflow, rule)
                -> workflow.validate_async() -> list[str] errors
                -> EntityScope.from_event(rule.action.params)
                -> workflow.enumerate_async(scope) -> list[dict]
                -> workflow.execute_async(entities, rule.action.params) -> WorkflowResult
```

### PipelineConversionRule Execution Steps

1. Look up target `PipelineStage` from `context.config.get_pipeline_stage(target_type.value)`
2. `discover_template_async(client, target_project_gid, template_section)` -- finds template task
3. `duplicate_from_template_async(client, template_task, new_task_name)` -- duplicates with subtasks
4. `add_to_project_async(new_task.gid, target_project_gid)` -- adds to target project
5. `place_in_section_async(...)` and optionally `tasks.update_async(due_on=...)` -- section and due date
6. `wait_for_subtasks_async(...)` -- polls until subtasks appear (Asana creates them async)
7. `FieldSeeder.seed_fields_async()` + `write_fields_async()` -- hierarchy field cascade
8. `_place_in_hierarchy_async()` -- sets parent under ProcessHolder with `insert_after=source_process`
9. `_set_assignee_from_rep_async()` -- rep field cascade (Unit.rep -> Business.rep -> fixed GID)
10. `_create_onboarding_comment_async()` -- adds comment with conversion context and source link

### Persistence Model

The automation engine produces `AutomationResult` objects (defined in `src/autom8_asana/persistence/models.py`). Fields include: `rule_id`, `rule_name`, `triggered_by_gid`, `triggered_by_type`, `success`, `error`, `actions_executed`, `entities_created`, `entities_updated`, `execution_time_ms`, `skipped_reason`, `pre_validation`, `post_validation`, `enhancement_results`.

`WorkflowResult` is defined in `src/autom8_asana/automation/workflows/base.py`. It includes: `workflow_id`, `started_at`, `completed_at`, `total`, `succeeded`, `failed`, `skipped`, `errors`, `metadata`.

### Public API Surface

The canonical import path is `from autom8_asana.automation import ...`. Public names in `__all__`:
- Core: `AutomationEngine`, `AutomationRule`, `TriggerCondition`, `Action`, `AutomationContext`, `AutomationConfig`, `AssigneeConfig`, `PipelineStage`, `EventType`
- Phase 2 (lazy): `PipelineConversionRule`
- Utilities: `TemplateDiscovery`, `FieldSeeder`, `SubtaskWaiter`

### Test Coverage

Unit tests span 44 files in `tests/unit/automation/`. Key test files:
- `tests/unit/automation/test_engine.py` -- 360 lines, tests `AutomationEngine.evaluate_async`, loop prevention, disabled engine, action-result entities
- `tests/unit/automation/test_pipeline.py` -- 1706 lines, comprehensive coverage of `PipelineConversionRule`
- `tests/unit/automation/test_seeding.py`, `test_seeding_write.py` -- `FieldSeeder` coverage
- `tests/unit/automation/test_context.py` -- `AutomationContext` loop prevention
- `tests/unit/automation/workflows/test_conversation_audit.py`, `test_insights_export.py`, `test_pipeline_transition.py` -- workflow implementations
- `tests/unit/automation/events/` -- 10 test files covering the event emission pipeline
- `tests/unit/automation/polling/` -- 8 test files covering `PollingScheduler`, `TriggerEvaluator`, `ActionExecutor`
- Integration: `tests/integration/automation/workflows/test_conversation_audit_e2e.py` (265 lines), `tests/integration/automation/polling/test_action_executor_integration.py`, `test_trigger_evaluator_integration.py`

---

## Boundaries and Failure Modes

### What This Feature Does NOT Do

- **No persistent rule storage**: Rules are registered in-memory at startup. `rules_source = "file"` and `rules_source = "api"` are future extension points with no implementation.
- **No retry on rule failure**: A failed rule produces a failed `AutomationResult` and is not retried. The calling code (SaveSession) does not act on rule failures.
- **No real-time webhook path for batch workflows**: Batch workflows are scheduled, not event-triggered. The `PollingScheduler` does not subscribe to Asana webhooks.
- **No distributed locking for event-driven rules**: The polling scheduler uses file-based locking (`fcntl.flock`) to prevent concurrent executions. Event-driven rules have no such protection -- if two SaveSession commits occur concurrently and both trigger the same rule, both executions will proceed independently.
- **`automation_enabled=False` on nested SaveSession**: `PipelineConversionRule._place_in_hierarchy_async()` calls `SaveSession(client, automation_enabled=False)` explicitly to prevent the hierarchy placement from triggering further rule evaluation. This is critical: nested saves must opt out of automation to avoid cascade.

### Known Edge Cases and Limitations

**MOVE_TO_SECTION entities**: A process moved to a section via `ActionType.MOVE_TO_SECTION` does not appear in `save_result.succeeded` because it has no dirty fields. The engine handles this explicitly at lines 153-163 of `engine.py`. If this special-case logic is removed, `PipelineConversionRule` will silently stop triggering on section changes.

**Event detection is heuristic**: `_detect_event` checks action_results for section changes, then `entity._is_new` flag, then `entity.gid.startswith("temp_")`. There is no `FIELD_UPDATED` detection path in the engine itself. Rules filtering on `EventType.FIELD_UPDATED` will never trigger from the current engine.

**Template subtask timing**: Asana creates subtask duplicates asynchronously. `wait_for_subtasks_async` polls with a timeout. If the timeout expires, execution continues (non-fatal) and the subtasks may be missing when field seeding runs. This is logged as `pipeline_subtask_timeout`.

**FieldSeeder enum resolution requires target task fetch**: `write_fields_async` fetches the target task's custom field definitions to resolve enum values to GIDs. When a pre-fetched `target_task` is provided, this API call is skipped. If the task's `custom_fields` are incomplete (wrong `opt_fields`), enum resolution silently skips the field.

**Empty Business cascade fields**: `FieldSeeder.DEFAULT_BUSINESS_CASCADE_FIELDS = []`. No Business fields are seeded by default. This prevents silent failures on target projects that don't have the same fields as the Business. Callers must explicitly configure `business_cascade_fields` in `PipelineStage`.

**Polling scheduler dry-run behavior**: If `PollingScheduler` is initialized without a `client`, it runs in dry-run mode -- matched tasks are logged but actions are not executed. There is no explicit dry-run flag; the absence of a client is the signal.

**`AUTOM8_AUDIT_ENABLED` / `AUTOM8_EXPORT_ENABLED` env vars**: Both `ConversationAuditWorkflow.validate_async()` and `InsightsExportWorkflow.validate_async()` check these env vars. When set to `false`, `0`, or `no`, the workflow returns an error from `validate_async()` and does not execute. The scheduler logs `workflow_validation_failed` and moves on.

**Circuit breaker in validate_async**: Both conversation audit and insights export check the `DataServiceClient` circuit breaker during `validate_async()`. If the breaker is open, the workflow is skipped for that scheduler cycle. This is the correct behavior but means a sustained circuit-breaker-open condition silently skips all affected workflows.

### Error Paths and Recovery

| Failure | Behavior | Recovery |
|---------|----------|----------|
| Rule exception during `evaluate_async` | Broad-catch, `AutomationResult(success=False)` produced, other rules continue | Log review; no automatic retry |
| No template found in target project | `AutomationResult(success=False, error="No template found...")` | Fix template section configuration in `PipelineStage` |
| No target pipeline stage in config | `AutomationResult(success=False, error="No target project configured...")` | Add `PipelineStage` entry to `AutomationConfig.pipeline_stages` |
| Field seeding failure (API error) | `logger.warning("pipeline_field_seeding_failed")`, task created but fields missing | Non-fatal; task is created, fields must be manually set |
| Hierarchy placement failure | `enhancement_results["hierarchy_placement"] = False`, task is still created | Non-fatal; task created at project root |
| Assignee not found | `logger.warning("pipeline_no_rep_for_assignee")`, task unassigned | Non-fatal |
| Comment creation failure | `enhancement_results["comment_created"] = False` | Non-fatal |
| `validate_mode="block"` + validation failure | `AutomationResult(success=False, error="Pre-transition validation failed...")` | Rule does not execute; transition is fully blocked |
| WorkflowItemError per holder/offer | Counted as `failed`, other items continue | Batch continues; check `result.errors` |
| Polling lock not acquired | Logs `lock_acquisition_failed`, returns without executing | Expected concurrent-run protection |
| DataServiceClient circuit breaker open | `validate_async()` returns error, workflow skipped | Wait for circuit breaker to close |

### Interaction Points Where Boundaries Blur

**SaveSession <-> AutomationEngine**: `SaveSession` calls `engine.evaluate_async()` if `automation_enabled=True` (the default). The engine is optional -- if `AsanaConfig.automation` is `None`, no engine is instantiated and automation is silently skipped. Creating a `SaveSession` with `automation_enabled=False` is the way to opt out of triggering automation from within automation (nested saves).

**PipelineConversionRule <-> LifecycleEngine**: `PipelineConversionRule` does not use `LifecycleEngine`. It performs the conversion directly. `PipelineTransitionWorkflow` (batch) uses `LifecycleEngine.handle_transition_async()`. These are separate paths that may produce different results for the same process (TENSION-007).

**PollingScheduler <-> WorkflowRegistry**: The scheduler dispatches workflows only when `workflow_registry` is provided at construction time. Rules with `action.type == "workflow"` but no registry configured will log `workflow_registry_not_configured` and silently skip. There is no error raised.

**Events pipeline <-> main automation**: The `events/` sub-package (`EventEmitter`, `EventEnvelope`, `EventTransport`) is a separate event emission path invoked by `SaveSession` after automation rule evaluation completes. It is not invoked by the automation engine itself. Agents should not confuse `EventType` (used as trigger vocabulary in `TriggerCondition`) with `EventEnvelope` (used for downstream event publication).

**`automation/pipeline.py` naming**: The file `pipeline.py` contains `PipelineConversionRule`. The file `workflows/pipeline_transition.py` contains `PipelineTransitionWorkflow`. These are not the same class. `PipelineConversionRule` is the event-driven rule (triggers on individual section changes); `PipelineTransitionWorkflow` is the batch workflow (enumerates terminal-section tasks and calls `LifecycleEngine`).

---

## Knowledge Gaps

1. **`rules_source = "file"` and `rules_source = "api"`**: These are declared in `AutomationConfig` and validated, but no loader code exists. Any attempt to set these will validate successfully but produce no rules at runtime.
2. **`EventType.FIELD_UPDATED` and `EventType.DELETED`**: Declared in the enum but `engine._detect_event()` has no detection path for these. Rules using these event types will never trigger.
3. **TENSION-007 essential pipeline differences**: The design constraint notes `pipeline.py` retains "essential pipeline differences lifecycle does not cover" but does not enumerate them. Behavioral comparison between `PipelineConversionRule` and `LifecycleEngine` for the same conversion scenario was not traced.
4. **`automation/events/config.py` subscription routing**: The events sub-package has its own `EventRoutingConfig` and subscription matching logic. This was not fully traced -- the depth of SQS transport configuration and subscription matching in production is not captured here.
5. **`polling/config_schema.py` full condition vocabulary**: The YAML condition schema (`stale`, `deadline_proximity`, `age_tracking`) was not fully read. The guide describes these but the Pydantic schema details were not verified.
