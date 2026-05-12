---
domain: feat/polling-scheduler
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/automation/polling/"
  - "./config/rules/"
  - "./pyproject.toml"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.93
format_version: "1.0"
---

# Polling-Based Automation Scheduler

## Purpose and Design Rationale

The polling scheduler exists to evaluate time-based automation rules against Asana tasks and dispatch registered workflows on configurable schedules. It decouples automation triggers from event-driven webhooks: where webhooks fire on mutations, the scheduler fires on elapsed time (staleness, deadline proximity, age, or calendar schedule).

**Design origin**: TDD-PIPELINE-AUTOMATION-EXPANSION. Extended by TDD-CONV-AUDIT-001 to add schedule-driven workflow dispatch (the `ScheduleConfig` + `workflow` action type path).

**Two rule modes**:

| Mode | Trigger | Action |
|------|---------|--------|
| Condition-based | Task attribute checks (stale/deadline/age) | `add_tag`, `add_comment`, `change_section` |
| Schedule-driven | Day-of-week or daily cadence | `workflow` (dispatches a registered `WorkflowAction`) |

**Dev vs. Production execution modes**:

| Mode | Mechanism | Concurrency guard |
|------|-----------|-------------------|
| Development | `PollingScheduler.run()` — APScheduler `BlockingScheduler`, CronTrigger | `max_instances=1`, `coalesce=True` |
| Production | `PollingScheduler.run_once()` + exit — invoked by system cron | `fcntl.flock(LOCK_EX | LOCK_NB)` on `/tmp/autom8_asana_polling.lock` |

**Key tradeoffs accepted**:
- APScheduler is an optional dependency (`scheduler = ["apscheduler>=3.10.0"]` in pyproject.toml) — dev mode raises `ImportError` at runtime if not installed; production cron requires no APScheduler at all.
- `fcntl` file locking is Unix-only (Linux/macOS). This is an undocumented platform constraint; Windows deployment is not supported.
- Task fetching is not implemented in the current callers: `_evaluate_rules` receives `tasks_by_project=None`, which defaults to an empty dict. Condition-based rules will never match tasks until a caller supplies populated task data.

---

## Conceptual Model

### Key Abstractions

| Term | Definition |
|------|-----------|
| `AutomationRulesConfig` | Root Pydantic model; validates the YAML file. Contains `SchedulerConfig` + list of `Rule`. |
| `SchedulerConfig` | Time-of-day (`HH:MM`) and IANA timezone for daily evaluation. |
| `Rule` | One automation rule: a `rule_id`, `project_gid`, list of `RuleCondition`, an `ActionConfig`, optional `ScheduleConfig`, and `enabled` flag. |
| `RuleCondition` | AND-composed set of triggers within a rule: up to one each of `stale`, `deadline`, `age`. `field_whitelist` reserved for future use. |
| `ScheduleConfig` | Per-rule schedule: `frequency` (`daily`|`weekly`) + optional `day_of_week`. Only valid when `action.type == "workflow"`. |
| `ActionConfig` | `type` + `params` dict. Supported condition-based types: `add_tag`, `add_comment`, `change_section`. Schedule-driven type: `workflow`. |
| `TriggerEvaluator` | Stateless evaluator. `evaluate_conditions(rule, tasks)` returns tasks matching ALL conditions (AND composition). |
| `ActionExecutor` | Executes `add_tag`/`add_comment`/`change_section` against `AsanaClient`. Returns `ActionResult`. |
| `StructuredLogger` | Singleton-like class-method logger wrapping `autom8y_log`. Binds context; provides `log_rule_evaluation`, `log_action_result`, `log_automation_result`. |
| `ConfigurationLoader` | Stateless YAML loader: reads file → parses YAML → substitutes `${ENV_VAR}` → validates via Pydantic. |
| `PollingScheduler` | Orchestrator. Wires all components. Entry points: `run()` (blocking/dev), `run_once()` (cron/prod), `from_config_file()` (factory). |

### Rule Lifecycle

```
YAML file
  → ConfigurationLoader.load_from_file() → AutomationRulesConfig
  → PollingScheduler.__init__(config)
  → run() or run_once()
      → _evaluate_rules(tasks_by_project)
          → for each enabled rule:
              if rule.schedule and action.type == "workflow":
                  _dispatch_scheduled_workflow(rule)
                    → _should_run_schedule(schedule) [day-of-week check]
                    → WorkflowRegistry.get(workflow_id)
                    → workflow.validate_async()
                    → EntityScope.from_event(rule.action.params)
                    → workflow.enumerate_async(scope)
                    → workflow.execute_async(entities, params)
              else (condition-based):
                  TriggerEvaluator.evaluate_conditions(rule, tasks)
                  → for matched tasks:
                      ActionExecutor.execute_async(task_gid, action)
```

### Trigger Types

| Trigger | Field read | Match condition |
|---------|-----------|----------------|
| `stale` | `task.modified_at` | `modified_at <= now - N days` |
| `deadline` | `task.due_at` then `task.due_on` | `due_date <= now + N days` |
| `age` | `task.created_at` + `task.completed` | `created_at <= now - N days AND NOT completed` |

All date comparisons use UTC. Missing date fields → False (no match), invalid format → warning + False.

### Schedule Frequency Logic

`_should_run_schedule(schedule)`:
- `daily`: always True
- `weekly`: `datetime.now(UTC).astimezone(timezone).weekday() == day_map[day_of_week]`

Python weekday: Monday=0 … Sunday=6. The `day_map` dict in `_should_run_schedule` is the authoritative lookup.

---

## Implementation Map

### Package: `src/autom8_asana/automation/polling/` (7 source files + 1 YAML rule)

| File | Purpose | Key types/exports |
|------|---------|-------------------|
| `polling_scheduler.py` | Orchestrator + entry points | `PollingScheduler` (run, run_once, from_config_file, _evaluate_rules, _dispatch_scheduled_workflow) |
| `trigger_evaluator.py` | Condition evaluation | `TriggerEvaluator` (evaluate_conditions, _evaluate_stale_trigger, _evaluate_deadline_trigger, _evaluate_age_trigger) |
| `action_executor.py` | Action dispatch | `ActionExecutor` (execute_async), `ActionResult` (dataclass) |
| `config_schema.py` | Pydantic models, strict validation | `AutomationRulesConfig`, `SchedulerConfig`, `Rule`, `RuleCondition`, `ScheduleConfig`, `ActionConfig`, `TriggerStaleConfig`, `TriggerDeadlineConfig`, `TriggerAgeConfig` |
| `config_loader.py` | YAML load + env var substitution + Pydantic validation | `ConfigurationLoader` (load_from_file, substitute_env_vars) |
| `structured_logger.py` | Structured JSON logging via autom8y-log SDK | `StructuredLogger` (configure, get_logger, log_rule_evaluation, log_action_result, log_automation_result) |
| `cli.py` | Operator CLI | `validate_command`, `status_command`, `evaluate_command`, `main` |
| `__init__.py` | Public API re-exports | All major types listed above |

### Config Rule: `config/rules/conversation-audit.yaml`

One live rule: `weekly-conversation-audit` targeting project GID `1201500116978260`, dispatching `conversation-audit` workflow every Sunday at 02:00 America/New_York. Params: `workflow_id`, `date_range_days: 30`, `attachment_pattern: "conversations_*.csv"`, `max_concurrency: 5`.

### External Dependencies

| Package | Role |
|---------|------|
| `apscheduler>=3.10.0` | Optional; required only for `run()` (dev blocking mode). Not needed for `run_once()` cron path. |
| `autom8y_log` | `get_logger()` and `configure_logging()` — used in all 7 source files |
| `autom8_asana.automation.workflows.registry.WorkflowRegistry` | `get(workflow_id) → WorkflowAction | None` and `list_ids() → list[str]` — consumed by `_dispatch_scheduled_workflow` |
| `autom8_asana.automation.workflows.base.WorkflowAction` | Protocol: `validate_async()`, `enumerate_async(scope)`, `execute_async(entities, params) → WorkflowResult` |
| `autom8_asana.core.scope.EntityScope` | `from_event(dict) → EntityScope` (frozen dataclass) — called with `rule.action.params` during workflow dispatch |
| `autom8_asana.errors.ConfigurationError` | Raised by loader, scheduler init, and CLI boundary catches |
| `fcntl` (stdlib) | Unix-only exclusive file lock for `run_once()` concurrent execution prevention |

### Public API Surface (from `__init__.py`)

All of the following are importable from `autom8_asana.automation.polling`:
`PollingScheduler`, `TriggerEvaluator`, `ActionExecutor`, `ActionResult`, `StructuredLogger`, `ConfigurationLoader`, `AutomationRulesConfig`, `ScheduleConfig`, `SchedulerConfig`, `Rule`, `RuleCondition`, `ActionConfig`, `TriggerStaleConfig`, `TriggerDeadlineConfig`, `TriggerAgeConfig`.

### Test Coverage

Substantial test suite (not zero-coverage as the previous snapshot claimed). Confirmed files:

**Unit tests** (`tests/unit/automation/polling/`): `test_polling_scheduler.py`, `test_trigger_evaluator.py`, `test_action_executor.py`, `test_config_loader.py`, `test_config_schema.py`, `test_structured_logger.py`, `test_cli.py`, `conftest.py`

**Integration tests** (`tests/integration/automation/polling/`): `test_trigger_evaluator_integration.py`, `test_action_executor_integration.py`, `test_end_to_end.py`, `conftest.py`

[KNOW-CANDIDATE] Previous snapshot asserted "No test coverage confirmed for this package" — this was false; 11 test files exist across unit + integration tiers.

---

## Boundaries and Failure Modes

### Scope Boundaries

- **Does NOT fetch tasks**: `_evaluate_rules` accepts `tasks_by_project: dict | None`. Current call sites pass `None`, which defaults to `{}`. Condition-based rules will never match until a caller integrates task fetching.
- **Does NOT manage WorkflowRegistry**: The registry must be injected via `__init__(workflow_registry=...)`. If not injected and a schedule-driven rule fires, `workflow_registry_not_configured` is logged and execution continues silently.
- **Does NOT handle OR/NOT logic**: `RuleCondition` supports only AND composition across trigger types (stale, deadline, age). There is no OR or NOT operator at the condition level.
- **Does NOT support more than 3 trigger types**: `stale`, `deadline`, `age` are the only condition trigger types. `field_whitelist` is schema-present but `TriggerEvaluator` does not use it — it appears reserved for future custom-field filtering (MVP deferral noted in TDD).
- **Single YAML file per scheduler instance**: No multi-file config aggregation.

### Failure Modes

| Failure | Behavior |
|---------|---------|
| Missing YAML file | `ConfigurationError` raised at `from_config_file()` / `load_from_file()` |
| Invalid YAML syntax | `ConfigurationError` with YAML parse error detail |
| Pydantic schema violation (`extra="forbid"`) | `ConfigurationError` with field path + message |
| Missing `${ENV_VAR}` | `ConfigurationError` with variable name and config path |
| Invalid timezone in config | `ConfigurationError` at `PollingScheduler.__init__()` |
| APScheduler not installed | `ImportError` at `run()` invocation — NOT at import time |
| Lock held by another process | Warning log + silent return; no error raised (safe for overlapping cron runs) |
| `fcntl` unavailable (Windows) | `AttributeError` at `run_once()` — undocumented platform constraint |
| Workflow not found in registry | `workflow_not_found` error log; evaluation cycle continues |
| Workflow validation failure | `workflow_validation_failed` error log; execution skipped; cycle continues |
| Workflow execution exception | `workflow_execution_error` error log; cycle continues (BROAD-CATCH with isolation comment) |
| Per-task action execution error | `ActionResult(success=False)` returned; loop continues to next task (BROAD-CATCH isolation) |
| `TriggerEvaluator` missing task fields | Logs debug/warning + returns `False` for that task; does not raise |

### Interaction Points and Boundary Assessment

- **`WorkflowRegistry`** (automation/workflows/registry.py): called via `get(id)` and `list_ids()` — the registry is injected; if None, silent error path.
- **`WorkflowAction`** protocol (automation/workflows/base.py): `validate_async()`, `enumerate_async(scope)`, `execute_async(entities, params)` are awaited; any exception is caught and logged.
- **`EntityScope.from_event(params)`** (core/scope.py): called with `rule.action.params` dict. Contract: `from_event(event: dict[str, Any]) → EntityScope`. Frozen dataclass result. No exception handling around this call — if `from_event` raises, the BROAD-CATCH in `_execute_workflow_async` will catch it.
- **`AsanaClient`** (for condition-based actions): injected optionally. Absent client = dry-run mode (matches logged but no API calls). Present client = `ActionExecutor` calls `client.tags.add_to_task_async`, `client.stories.create_comment_async`, `client.sections.add_task_async`.
- **`autom8_asana.core.logging`**: `StructuredLogger.configure()` calls `configure(level=..., format=...)` and `get_logger()` calls `get_logger("autom8_asana.automation.polling").bind(...)`. Idempotent guard: `cls._configured` prevents double-configuration.
- **`asyncio.run()`**: Used in sync `_evaluate_rules` to bridge async action execution and workflow dispatch. This means `run_once()` / cron callers MUST NOT already be inside a running event loop.

### Configuration Boundaries

| Setting | Valid values | Validation |
|---------|-------------|-----------|
| `scheduler.time` | `HH:MM` 24-hour regex `^([01]\d|2[0-3]):([0-5]\d)$` | `field_validator` in `SchedulerConfig` |
| `scheduler.timezone` | Any IANA timezone string | `ZoneInfo(tz)` at `PollingScheduler.__init__()` |
| `rule.rule_id` | Non-empty string | `field_validator` |
| `condition.days` | `>= 1` integer | `field_validator` on all three trigger configs |
| `schedule.frequency` | `"weekly"` or `"daily"` | `field_validator` |
| `schedule.day_of_week` | ISO day name (`monday`…`sunday`) | `field_validator`; required when frequency=`weekly` |
| Rule with schedule | `action.type` must be `"workflow"` | `model_validator` on `Rule` |
| Rule without schedule | Must have >= 1 condition | `model_validator` on `Rule` |
| `action.type` (condition rules) | `add_tag`, `add_comment`, `change_section` | Validated at `ActionExecutor.execute_async()` runtime; raises `ValueError` for unknown type |
| `action.params` | Type-specific; see `_SUPPORTED_ACTIONS` dict in action_executor.py | Runtime validation in `execute_async()` |

---

```metadata
source_files_read: 9
source_files_in_scope: 7
config_files_read: 1
test_files_identified: 11
key_design_refs: ["TDD-PIPELINE-AUTOMATION-EXPANSION", "TDD-CONV-AUDIT-001"]
previous_gaps_resolved: ["task-fetching-status", "WorkflowRegistry.list_ids-signature", "EntityScope.from_event-contract", "fcntl-platform-constraint", "test-coverage-false-negative", "structured_logger-integration"]
new_findings: ["structured_logger documented (new file vs previous snapshot)", "test coverage exists (previous snapshot was incorrect)", "asyncio.run bridge in sync context (event loop restriction)", "field_whitelist deferred/unused in TriggerEvaluator"]
```
