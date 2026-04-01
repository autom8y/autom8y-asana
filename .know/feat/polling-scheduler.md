---
domain: feat/polling-scheduler
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/automation/polling/**/*.py"
  - "./config/rules/**/*.yaml"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.85
format_version: "1.0"
---

# Polling-Based Automation Scheduler

## Purpose and Design Rationale

Development-mode and cron-compatible system for evaluating time-based rules against Asana tasks and dispatching registered workflows on configurable schedules.

Two rule modes: **Condition-based** (scan tasks for stale/deadline/age triggers, execute add_tag/comment/section_move) and **Schedule-driven** (daily/weekly frequency, dispatch WorkflowAction from WorkflowRegistry).

### Dev vs. Production

| Mode | Mechanism | Lock |
|------|-----------|------|
| Development | `PollingScheduler.run()` via APScheduler `BlockingScheduler` | `max_instances=1` |
| Production | `PollingScheduler.run_once()` + exit | `fcntl` exclusive file lock |

APScheduler is an optional dependency (`scheduler = ["apscheduler>=3.10.0"]`).

## Implementation Map

8 files: polling_scheduler.py (orchestrator), trigger_evaluator.py (AND-composed conditions), action_executor.py (3 action types), config_schema.py (8 Pydantic models, `extra="forbid"`), config_loader.py (YAML + env var substitution), structured_logger.py, cli.py (validate/status/evaluate), plus `config/rules/conversation-audit.yaml`.

### Live Rule

`conversation-audit.yaml`: One weekly rule targeting project GID 1201500116978260, dispatching `conversation-audit` workflow every Sunday.

## Boundaries and Failure Modes

- Task fetching not implemented (`tasks_by_project` always None in current call sites)
- All broad-catch sites annotated with isolation contracts
- `fcntl` Unix-only (not documented as platform constraint)
- No test coverage confirmed for this package

## Knowledge Gaps

1. Task fetching integration not implemented -- condition-based path has zero production callers.
2. `WorkflowRegistry.list_ids()` signature not read.
3. `EntityScope.from_event()` contract not traced.
4. `fcntl` platform limitation undocumented.
