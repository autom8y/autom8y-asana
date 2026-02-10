# PRD: Weekly Conversation Audit Workflow

**PRD ID**: PRD-CONV-AUDIT-001
**Status**: Draft
**Date**: 2026-02-10
**Author**: Requirements Analyst
**Stakeholders**: CS Team, Engineering
**Spike Reference**: `/autom8_data/.claude/.wip/SPIKE-conversation-audit-workflow.md`

---

```yaml
impact: high
impact_categories: [api_contract, cross_service]
complexity: MODULE
```

---

## 1. Executive Summary

### Problem

The CS team manually exports 30-day conversation audit CSVs from autom8_data and attaches them to Asana ContactHolder tasks. With 200-500 active ContactHolders, this represents 200-500 manual export-download-upload cycles per week. The operation is entirely deterministic -- the same phone number, the same endpoint, the same attachment target -- and produces zero unique value per repetition.

### Solution

Build a scheduled automation workflow in autom8_asana that enumerates active ContactHolders, resolves each to a Business phone number, fetches the conversation export CSV from autom8_data's existing `/api/v1/messages/export` endpoint, and replaces the attachment on each ContactHolder task. autom8_data requires zero changes.

### Strategic Significance

This is the **first workflow** in a generalized cross-service automation layer between autom8_asana and autom8_data. The primitives, action contracts, scheduling patterns, and error-handling conventions established here will serve as the foundation for 10s-100s of future workflows (data sync, enrichment, notifications, reconciliation, reporting). The design must be deliberately generalized: build the conversation audit as the first instantiation of a reusable automation toolkit, not as a one-off script.

---

## 2. Background: Existing Infrastructure

### autom8_asana (Workflow Host)

| Component | Location | Relevance |
|-----------|----------|-----------|
| **PollingScheduler** | `src/autom8_asana/automation/polling/polling_scheduler.py` | Daily scheduler with timezone support, file locking, cron + APScheduler modes. Currently evaluates condition-based rules only. |
| **ActionExecutor** | `src/autom8_asana/automation/polling/action_executor.py` | Dispatches `add_tag`, `add_comment`, `change_section` actions on individually matched tasks. Not designed for batch workflows. |
| **ConfigSchema** | `src/autom8_asana/automation/polling/config_schema.py` | Pydantic v2 `Rule` model requires `conditions: list[RuleCondition]` where each RuleCondition must have at least one trigger type (stale/deadline/age). No support for time-only or batch-action rules. |
| **EventEmitter** | `src/autom8_asana/automation/events/emitter.py` | Event pub/sub with subscription routing and transport abstraction. Fire-and-forget with dead-letter logging. |
| **EventType** | `src/autom8_asana/automation/events/types.py` | Closed enum: `CREATED`, `UPDATED`, `SECTION_CHANGED`, `DELETED`. |
| **DataServiceClient** | `src/autom8_asana/clients/data/client.py` | HTTP client for `autom8_data` with circuit breaker, retry, auth, connection pooling. Currently serves `POST /api/v1/data-service/insights` only. |
| **AttachmentsClient** | `src/autom8_asana/clients/attachments.py` | Full attachment lifecycle: upload (multipart), download (streaming), delete, list-for-task with pagination. |
| **ContactHolder model** | `src/autom8_asana/models/business/contact.py` | `PRIMARY_PROJECT_GID = "1201500116978260"`. Extends `HolderFactory`. Children are `Contact` entities. |
| **Business model** | `src/autom8_asana/models/business/business.py` | `office_phone = TextField(cascading=True)`. Parent of ContactHolder in the hierarchy. 1:1 Business:office_phone cardinality. |
| **ConfigurationLoader** | `src/autom8_asana/automation/polling/config_loader.py` | Loads YAML with env var substitution and Pydantic validation. |

### autom8_data (Data Source -- NO CHANGES)

| Component | Status |
|-----------|--------|
| `GET /api/v1/messages/export?office_phone={E.164}` | Production-ready. Returns CSV with BOM, `X-Export-Row-Count` and `X-Export-Truncated` headers. 10K row cap. 30-day default window. |
| S2S auth via JWT | Existing `AUTOM8_DATA_API_KEY` flow. |

---

## 3. Abstraction Pattern Recommendation

### The Core Question

autom8_asana already has four automation primitives:

1. **PollingScheduler** -- time-based daily evaluation of condition-matched rules
2. **ActionExecutor** -- dispatches atomic actions (`add_tag`, `add_comment`, `change_section`) on individual tasks
3. **EventEmitter** -- pub/sub event routing with subscription-based fan-out
4. **AutomationEngine** (in `automation/base.py` + `automation/engine.py`) -- SaveSession-triggered rule evaluation with `should_trigger` / `execute_async` protocol

The conversation audit workflow does not fit any of these cleanly:
- It is **time-triggered** (like PollingScheduler) but not **condition-matched** (unlike PollingScheduler rules).
- It is a **batch operation** (unlike ActionExecutor which operates per-task).
- It is **cross-service** (unlike existing actions which are Asana-only).
- It is **scheduled** (unlike EventEmitter which is event-driven).

### Evaluated Patterns

#### Pattern A: Action Registry (extend ActionExecutor)

Add `conversation_audit` to `_SUPPORTED_ACTIONS` in ActionExecutor. Relax the Rule schema to allow empty `conditions` with a `schedule` block.

**Pros**: Minimal new infrastructure; reuses YAML config, config loader, scheduler.
**Cons**: ActionExecutor's contract is `execute_async(task_gid, action)` -- a per-task dispatch. The conversation audit is a batch operation that enumerates its own targets. Forcing it into a per-task dispatch model means the "task_gid" would be a sentinel value (the project GID), and the action would internally re-enumerate all tasks -- breaking the semantic contract. Future batch workflows would all need the same workaround.

**Verdict**: Poor fit. The per-task dispatch model is fundamentally wrong for batch operations.

#### Pattern B: Pipeline/Step (new abstraction)

Create a `WorkflowAction` abstract base class with a `execute_batch_async()` method. Each workflow is a class that implements the full lifecycle (enumerate, transform, act, report). Register workflows in YAML. PollingScheduler dispatches to workflows based on schedule configuration.

**Pros**: Clean separation between per-task actions and batch workflows. The WorkflowAction contract is designed for the conversation audit's actual needs. New workflows implement a well-defined protocol. Composes naturally with PollingScheduler's existing scheduling infrastructure.
**Cons**: New abstraction layer. But the abstraction is small (one ABC, one registration mechanism).

**Verdict**: Best fit. The batch-workflow use case is genuinely different from per-task actions, and deserves its own contract.

#### Pattern C: Event-Driven (extend EventEmitter)

Emit a synthetic `SCHEDULE_TICK` event from the scheduler, and have a subscriber that triggers the audit workflow.

**Pros**: Leverages existing event infrastructure.
**Cons**: The event system is designed for entity lifecycle events (created, updated, section_changed, deleted). Grafting time-based scheduling onto it conflates two different trigger models. The EventEmitter's fire-and-forget contract means the scheduler cannot track workflow outcomes. Future workflows that need result reporting would all fight this limitation.

**Verdict**: Poor fit. Scheduling is not an event; conflating them creates confusion.

### Recommendation: Pattern B -- WorkflowAction Protocol

Introduce a `WorkflowAction` protocol (abstract base class) alongside the existing `ActionExecutor`. This gives the automation layer two dispatch models:

| Dispatch Model | Trigger | Target | Contract | Examples |
|---------------|---------|--------|----------|----------|
| **ActionExecutor** (existing) | Condition match on individual task | Single task GID | `execute_async(task_gid, action) -> ActionResult` | `add_tag`, `add_comment`, `change_section` |
| **WorkflowAction** (new) | Schedule (time-based) | Self-enumerated batch | `execute_async(config) -> WorkflowResult` | `conversation_audit`, future: `data_sync`, `enrichment`, `reconciliation` |

Both dispatch models are invoked by PollingScheduler. The scheduler already iterates rules; adding a branch for "if rule has schedule and no conditions, dispatch to WorkflowAction registry" is a small, additive change.

---

## 4. Action Contract / Interface Definition

### 4.1 WorkflowAction Protocol

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WorkflowResult:
    """Outcome of a workflow execution cycle."""
    workflow_id: str
    started_at: datetime
    completed_at: datetime
    total: int
    succeeded: int
    failed: int
    skipped: int
    errors: list[WorkflowItemError] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def failure_rate(self) -> float:
        return self.failed / self.total if self.total > 0 else 0.0


@dataclass
class WorkflowItemError:
    """Error detail for a single item in a batch workflow."""
    item_id: str
    error_type: str
    message: str
    recoverable: bool = True


class WorkflowAction(ABC):
    """Protocol for batch automation workflows.

    Each workflow owns its full lifecycle:
    1. Enumerate targets (from Asana project, API, etc.)
    2. Process each target (fetch data, transform, act)
    3. Report results (structured logging, metrics)

    Implementations must be idempotent: re-running the same
    workflow should produce the same end state.
    """

    @property
    @abstractmethod
    def workflow_id(self) -> str:
        """Unique identifier for this workflow type.

        Convention: domain-verb (e.g., 'conversation-audit',
        'data-sync', 'contact-enrichment').
        """
        ...

    @abstractmethod
    async def execute_async(
        self,
        params: dict[str, Any],
    ) -> WorkflowResult:
        """Execute the full workflow cycle.

        Args:
            params: YAML-configured parameters for this workflow
                (e.g., date_range_days, attachment_pattern).

        Returns:
            WorkflowResult with per-item success/failure tracking.
        """
        ...

    @abstractmethod
    async def validate_async(self) -> list[str]:
        """Pre-flight validation before execution.

        Returns:
            List of validation errors (empty = ready to execute).
            Examples: missing config, unreachable upstream, invalid credentials.
        """
        ...
```

### 4.2 Workflow Registry

A simple dictionary mapping `workflow_id` strings to `WorkflowAction` instances. Registered during application startup. PollingScheduler looks up the registry when dispatching schedule-triggered rules.

```python
class WorkflowRegistry:
    """Registry of available workflow actions."""

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowAction] = {}

    def register(self, workflow: WorkflowAction) -> None:
        self._workflows[workflow.workflow_id] = workflow

    def get(self, workflow_id: str) -> WorkflowAction | None:
        return self._workflows.get(workflow_id)

    def list_ids(self) -> list[str]:
        return list(self._workflows.keys())
```

### 4.3 How a New Workflow Author Adds a Workflow

1. Create a class that extends `WorkflowAction` in `src/autom8_asana/automation/workflows/{domain_verb}.py`
2. Implement `workflow_id`, `execute_async`, and `validate_async`
3. Register the workflow in the application's startup (e.g., `WorkflowRegistry.register(ConversationAuditWorkflow(...))`)
4. Add a YAML rule with `workflow_id` matching the registered ID, `schedule` block, and `params`
5. Done. PollingScheduler discovers and dispatches it.

### 4.4 YAML Schema Extension

The existing `Rule` model in `config_schema.py` needs two additions:

1. A `schedule` field for time-based triggering (weekly, daily, custom cron)
2. Relaxation of the `conditions` requirement when `schedule` is present

```yaml
rules:
  # Existing condition-based rule (unchanged)
  - rule_id: "escalate-triage"
    conditions:
      - stale: { field: "Section", days: 3 }
    action:
      type: "add_tag"
      params: { tag_gid: "123" }

  # New schedule-based workflow rule
  - rule_id: "weekly-conversation-audit"
    name: "Weekly conversation audit CSV refresh"
    project_gid: "1201500116978260"
    conditions: []   # Empty -- schedule-driven, not condition-driven
    action:
      type: "workflow"
      params:
        workflow_id: "conversation-audit"
        date_range_days: 30
        attachment_pattern: "conversations_*.csv"
        max_concurrency: 5
    enabled: true
    schedule:
      frequency: "weekly"
      day_of_week: "sunday"
```

The `action.type: "workflow"` signals the scheduler to dispatch via WorkflowRegistry instead of ActionExecutor. The `schedule` block provides per-rule schedule overrides beyond the global `scheduler.time`.

---

## 5. Requirements

### Functional Requirements

| ID | Priority | Requirement | Acceptance Criteria | Source |
|----|----------|-------------|---------------------|--------|
| REQ-F01 | **Must** | System SHALL enumerate all non-completed tasks in the ContactHolder project (GID `1201500116978260`) | Given the scheduler triggers, when enumeration runs, then all active ContactHolder tasks are retrieved via paginated Asana API | Stakeholder |
| REQ-F02 | **Must** | System SHALL resolve each ContactHolder to its parent Business's `office_phone` field | Given a ContactHolder task, when phone resolution runs, then the parent Business task is fetched and `office_phone` (TextField, cascading=True) is extracted | Spike 3.4 |
| REQ-F03 | **Must** | System SHALL fetch conversation export CSV from `GET /api/v1/messages/export?office_phone={E.164}` via DataServiceClient | Given a valid E.164 phone number, when export is requested, then CSV bytes are returned with row count and truncation metadata | Spike 3.1 |
| REQ-F04 | **Must** | System SHALL use upload-first attachment replacement (upload new CSV, then delete old) | Given an existing CSV attachment on a ContactHolder, when replacement runs, then the new CSV is uploaded before old attachments matching `conversations_*.csv` are deleted | Spike 6.3 |
| REQ-F05 | **Must** | System SHALL skip ContactHolders with no resolvable `office_phone` and log a warning | Given a ContactHolder whose parent Business has no `office_phone`, when processing runs, then it is counted as `skipped` with a structured log warning | Spike 7.3 |
| REQ-F06 | **Must** | System SHALL skip attachment replacement when CSV export returns 0 data rows | Given an export with `X-Export-Row-Count: 0`, when processing runs, then no attachment changes are made and the item is counted as `skipped` | Spike 6.1 |
| REQ-F07 | **Must** | System SHALL continue processing remaining ContactHolders when individual items fail | Given a failure on ContactHolder N, when processing continues, then ContactHolders N+1 through end are still processed | Spike 6.5 |
| REQ-F08 | **Must** | System SHALL produce a structured summary log at run completion with total/succeeded/failed/skipped counts | Given a completed run, then a JSON log entry includes `total`, `succeeded`, `failed`, `skipped`, `truncated`, `duration_seconds` | Spike 6.5 |
| REQ-F09 | **Must** | System SHALL extend DataServiceClient with `get_export_csv_async()` method reusing existing circuit breaker, retry, auth, and connection pool infrastructure | Given the export call, when executed, then it uses the same `_get_client()`, `_circuit_breaker`, and `_retry_handler` as insights calls | Spike 3.1, ADR 8 |
| REQ-F10 | **Must** | System SHALL add `ExportResult` dataclass to data client models containing `csv_content`, `row_count`, `truncated`, `office_phone`, `filename` | Given a successful export response, then all fields are populated from response body and headers | Spike 3.1 |
| REQ-F11 | **Must** | System SHALL provide `AUTOM8_AUDIT_ENABLED` feature flag as an emergency kill switch | Given env var set to "false"/"0"/"no", when scheduler triggers, then the workflow is skipped with a log message | Spike 5 |
| REQ-F12 | **Must** | System SHALL define the `WorkflowAction` abstract base class and `WorkflowRegistry` for generalized batch workflow dispatch | Given a new workflow class, when registered, then the scheduler can discover and dispatch it via YAML configuration | Section 4 |
| REQ-F13 | **Must** | System SHALL extend the config schema (`Rule` model) to support an optional `schedule` block and allow empty `conditions` for schedule-driven rules | Given a YAML rule with `schedule` and empty `conditions`, when loaded, then validation passes | Section 4.4 |
| REQ-F14 | **Must** | System SHALL use YAML-configurable schedule (day/time) with no hardcoded schedule values | Given a YAML change to `schedule.day_of_week`, when the scheduler runs, then it respects the new schedule without code changes | Locked decision |
| REQ-F15 | **Should** | System SHALL support configurable `max_concurrency` for parallel ContactHolder processing (default: 5) | Given `max_concurrency: 10` in YAML params, when processing runs, then at most 10 ContactHolders are processed concurrently | Spike 7.2 |
| REQ-F16 | **Should** | System SHALL name CSV attachments matching the format from autom8_data's `Content-Disposition` header: `conversations_{phone}_{date}.csv` | Given a successful upload, then the filename matches the pattern from the export endpoint | Spike 3.5 |
| REQ-F17 | **Could** | System SHALL add a comment to ContactHolder task when CSV export is truncated (`X-Export-Truncated: true`) | Given a truncated export, then a comment is added noting the truncation | Spike 6.4 |
| REQ-F18 | **Must** | System SHALL implement `ConversationAuditWorkflow` as the first concrete `WorkflowAction` implementation | Given the YAML rule referencing `workflow_id: "conversation-audit"`, when the scheduler dispatches, then the full enumerate-resolve-fetch-replace lifecycle executes | Section 4 |

### Non-Functional Requirements

| ID | Category | Requirement | Target | Measurement |
|----|----------|-------------|--------|-------------|
| NFR-01 | Performance | Workflow SHALL complete within 10 minutes for 500 ContactHolders | < 600s total | Structured log `duration_seconds` field |
| NFR-02 | Reliability | Circuit breaker SHALL prevent cascading failure to autom8_data | 5 consecutive failures open circuit; 30s recovery | Existing `CircuitBreakerConfig` defaults |
| NFR-03 | Availability | Feature flag SHALL allow disabling workflow without code deployment | `AUTOM8_AUDIT_ENABLED=false` stops execution | Manual verification |
| NFR-04 | Observability | Every run SHALL produce structured JSON logs parseable by CloudWatch Insights | All log events include `event`, `workflow_id`, and count fields | Log format inspection |
| NFR-05 | Scalability | Workflow SHALL operate within Asana API rate limits (1500 req/min) | ~400 calls for 100 holders; concurrency throttle for 500+ | Rate limit monitoring |
| NFR-06 | Security | Phone numbers in logs SHALL be PII-masked using existing `mask_phone_number()` | Middle digits replaced with `***` | Log output inspection |
| NFR-07 | Idempotency | Re-running the workflow SHALL produce the same end state (latest CSV attached) | Upload-first, then delete old; no duplicate attachments | Manual verification |
| NFR-08 | Execution | Phase 1 SHALL target Lambda execution with 15-minute timeout | < 15 min for 500 holders | Lambda metrics |

---

## 6. User Stories

### US-01: Weekly Automated Refresh

**As a** CS team member, **I want** every active ContactHolder to have a fresh 30-day conversation audit CSV attached by Monday morning, **so that** I can review conversation history without manually exporting from the data service.

**Acceptance Criteria:**
1. Given the scheduler triggers on the configured day/time, when the workflow completes, then each active ContactHolder with a resolvable `office_phone` has a CSV attachment dated within the last 7 days.
2. Given a ContactHolder previously had a `conversations_*.csv` attachment, when the new CSV is uploaded, then the old attachment is deleted.
3. Given the workflow runs at 02:00 Sunday ET, when CS opens Asana on Monday, then all attachments reflect the latest 30-day window ending Saturday.

### US-02: Graceful Handling of Missing Phone Numbers

**As a** CS team member, **I want** ContactHolders without phone numbers to be skipped without affecting other ContactHolders, **so that** one data quality issue does not block the entire team's audit documents.

**Acceptance Criteria:**
1. Given a ContactHolder whose parent Business has no `office_phone`, when the workflow processes it, then it is skipped and counted in `skipped`.
2. Given 3 of 100 ContactHolders lack phone numbers, when the workflow completes, then the summary log shows `skipped: 3, succeeded: 97`.

### US-03: Resilience to autom8_data Outage

**As an** operations engineer, **I want** the workflow to degrade gracefully when autom8_data is unavailable, **so that** a data service outage does not cause cascading failures or data loss.

**Acceptance Criteria:**
1. Given autom8_data returns 5xx errors, when the circuit breaker opens after 5 failures, then remaining ContactHolders fast-fail without hammering the degraded service.
2. Given a failed export, when the workflow skips that ContactHolder, then the existing (old) CSV attachment is preserved (not deleted).
3. Given the next weekly run, when autom8_data has recovered, then all ContactHolders are retried successfully.

### US-04: Emergency Disable

**As an** operations engineer, **I want** to disable the workflow via environment variable without redeployment, **so that** I can stop it immediately if it causes unexpected issues.

**Acceptance Criteria:**
1. Given `AUTOM8_AUDIT_ENABLED=false` is set, when the scheduler triggers, then the workflow is skipped with a log entry `workflow_disabled`.
2. Given the env var is removed or set to `true`, when the scheduler triggers, then the workflow executes normally.

### US-05: New Workflow Onboarding

**As a** developer building the next automation workflow, **I want** a clear protocol for creating and registering new batch workflows, **so that** I can focus on business logic rather than plumbing.

**Acceptance Criteria:**
1. Given a new class extending `WorkflowAction` with `workflow_id = "my-workflow"`, when registered in `WorkflowRegistry` and referenced in YAML, then the scheduler dispatches it on the configured schedule.
2. Given the developer implements only `execute_async` and `validate_async`, the workflow participates in scheduling, logging, and error reporting without additional wiring.

---

## 7. Success Metrics

| Metric | Target | Measurement Method | Timeframe |
|--------|--------|--------------------|-----------|
| Manual export requests eliminated | 100% reduction | CS team Slack channel audit request count: 0 per week | 2 weeks post-Phase 1 |
| Workflow success rate per run | >= 95% of active ContactHolders | `succeeded / total` from structured run summary log | Every run |
| Attachment freshness | 100% of active ContactHolders with CSV dated within 7 days | Audit query: count ContactHolders with `conversations_*.csv` modified in last 7 days | Weekly |
| Run duration (100 holders) | < 120 seconds | `duration_seconds` from run summary log | Every run |
| Run duration (500 holders) | < 600 seconds | `duration_seconds` from run summary log | Every run |
| Phone resolution coverage | >= 95% of active ContactHolders resolve to `office_phone` | `(total - skipped_no_phone) / total` from run log | Every run |
| Alert threshold | < 10% failure rate per run | `failed / total < 0.10` from run log; alert in Phase 2 | Every run |
| Zero autom8_data changes | 0 files modified in autom8_data | Code review verification | Phase 1 |

---

## 8. Phased Scope

### Phase 1: Core Workflow + Automation Primitives (This Sprint)

**IN scope:**
- `WorkflowAction` ABC and `WorkflowResult` / `WorkflowItemError` dataclasses
- `WorkflowRegistry` with startup registration
- Config schema extension: `ScheduleConfig` model, optional `schedule` field on `Rule`, relaxed `conditions` validator
- PollingScheduler branch: dispatch to `WorkflowRegistry` for schedule-triggered rules with `action.type: "workflow"`
- `DataServiceClient.get_export_csv_async()` method
- `ExportResult` dataclass in data client models
- `ConversationAuditWorkflow` implementing the full enumerate-resolve-fetch-replace lifecycle
- YAML rule definition for the weekly audit: `config/rules/conversation-audit.yaml`
- `AUTOM8_AUDIT_ENABLED` feature flag
- Unit tests for `get_export_csv_async`, `ExportResult`, `WorkflowAction` protocol
- Integration test for `ConversationAuditWorkflow` with mocked Asana + autom8_data
- Lambda handler entry point for scheduled execution
- Structured logging for run summary and per-item outcomes
- `validate_async` pre-flight check (DataServiceClient reachable, ContactHolder project accessible)

**OUT of scope (Phase 1):**
- CloudWatch metrics and alarms
- Dashboard
- Configurable per-ContactHolder parameters
- Transform pipeline (filter columns, reorder, etc.)
- Dry-run mode (beyond logging)
- Backfill CLI for single ContactHolder
- Run history persistence (DynamoDB or equivalent)
- Concurrency tuning beyond default (5)
- Truncation comment on ContactHolder (Could priority, deferred)

### Phase 2: Observability + Alerting (Sprint +1)

**IN scope:**
- CloudWatch custom metrics: `workflow_run_total`, `workflow_item_success`, `workflow_item_failure`, `workflow_item_skipped`, `workflow_run_duration_seconds`
- CloudWatch alarm: `workflow_item_failure` rate > 10% of total triggers SNS notification to `autom8-platform-alerts`
- Structured log enrichment: per-item timing, CSV size bytes, truncation flags
- Run history persistence (DynamoDB table or CloudWatch Insights query)
- Dashboard for weekly run summaries
- Truncation comment on ContactHolder task (REQ-F17)

**OUT of scope (Phase 2):**
- Per-ContactHolder date range overrides
- Per-ContactHolder filter overrides
- Dry-run mode
- Backfill CLI

### Phase 3: Configurability + Developer Experience (Sprint +2)

**IN scope:**
- Per-ContactHolder date range override (Asana custom field or YAML mapping)
- Per-ContactHolder filter overrides (direction, status, intent)
- Configurable concurrency ceiling in YAML params
- Dry-run mode: execute full lifecycle but skip upload/delete (log what would happen)
- Backfill capability: run for specific ContactHolder(s) on demand (CLI or API trigger)
- Transform extension point: optional post-fetch CSV transformation step in `WorkflowAction` lifecycle

**OUT of scope (all phases):**
- Any changes to autom8_data (locked decision)
- Real-time or sub-daily refresh cadence
- PDF or non-CSV export formats
- Notification to individual business owners (CS team handles distribution)
- Bi-directional data flow (autom8_data writing back to Asana)

---

## 9. Edge Cases

| # | Scenario | Expected Behavior | REQ |
|---|----------|-------------------|-----|
| EC-01 | ContactHolder's parent Business has no `office_phone` | Skip, count as `skipped`, log warning with ContactHolder GID | REQ-F05 |
| EC-02 | Export returns 0 data rows (`X-Export-Row-Count: 0`) | Skip attachment replacement, preserve existing attachment, count as `skipped` | REQ-F06 |
| EC-03 | Export is truncated (`X-Export-Truncated: true`) | Upload truncated CSV (10K rows), count as `truncated` in summary, log warning | REQ-F03 |
| EC-04 | autom8_data returns 5xx; circuit breaker opens | Remaining holders fast-fail via circuit breaker; existing attachments preserved | REQ-F07, NFR-02 |
| EC-05 | Upload succeeds but delete-old fails | ContactHolder has 2 CSV attachments temporarily; next run cleans up | REQ-F04 |
| EC-06 | Delete-old succeeds but upload-new fails | Not possible with upload-first pattern (upload happens before delete) | REQ-F04 |
| EC-07 | ContactHolder task is completed (archived) | Excluded from enumeration (`completed_since=now` filter) | REQ-F01 |
| EC-08 | Duplicate phone numbers across ContactHolders | Each gets its own export call; CSV content is identical but attachment targets differ | REQ-F03 |
| EC-09 | ContactHolder has non-CSV attachments (PDFs, images) | Only `conversations_*.csv` pattern matched for deletion; other attachments untouched | REQ-F04 |
| EC-10 | Asana API rate limit (429) | httpx transport respects `Retry-After` header; automatic backoff | NFR-05 |
| EC-11 | Lambda 15-minute timeout for large batches | Log partial progress; next run retries all (idempotent) | NFR-08 |
| EC-12 | Concurrent scheduler instances (overlapping cron) | File lock prevents concurrent execution (`_acquire_lock`) | PollingScheduler |
| EC-13 | `AUTOM8_AUDIT_ENABLED=false` | Workflow skipped entirely; no API calls made | REQ-F11 |
| EC-14 | DataServiceClient not initialized (missing env vars) | `validate_async` catches during pre-flight; run aborts with clear error | REQ-F12 |
| EC-15 | ContactHolder has no existing CSV attachment (first run) | Upload succeeds; delete-old is a no-op (no matching attachments) | REQ-F04 |

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Asana API rate limits at 500+ holders** | Medium | Medium | Configurable `max_concurrency` (default 5); Asana 429 backoff in transport layer; Phase 1 targets 200-500 holders which is within safe bounds |
| **autom8_data outage during workflow run** | Low | Low | Circuit breaker opens after 5 failures; existing attachments preserved; next weekly run retries all |
| **Lambda 15-minute timeout** | Low | Medium | 500 holders at 3s each = ~5 min with concurrency=5; log partial progress for debugging; can switch to ECS Fargate task if needed |
| **Phone resolution coverage < 95%** | Low | Low | Pre-flight validation logs count of resolvable phones; operational alert if coverage drops; upstream data quality remediation |
| **Schema migration breaks existing rules** | Medium | High | Config schema extension is additive (new optional `schedule` field); existing rules with `conditions` are unaffected; `extra="forbid"` catches typos |
| **WorkflowAction abstraction too rigid for future workflows** | Low | High | Protocol is minimal (3 methods); `params: dict[str, Any]` provides flexibility; `metadata` on `WorkflowResult` supports workflow-specific data without contract changes |
| **CSV file size causes memory pressure in Lambda** | Low | Low | 10K rows at ~500 bytes/row = ~5MB per CSV; well within Lambda's 512MB+ memory; no in-memory accumulation across holders |

---

## 11. Technical Constraints

| Constraint | Detail |
|------------|--------|
| **Python 3.11+** | Per `pyproject.toml` `requires-python = ">=3.11"` |
| **Pydantic v2** | Config schema uses `model_config = ConfigDict(extra="forbid")` |
| **httpx** | DataServiceClient uses httpx async client; export call must follow same pattern |
| **No new package dependencies** | All capabilities exist in current dep tree (httpx, pydantic, autom8y-* SDKs) |
| **autom8_data: NO changes** | Locked decision. Export endpoint is production-ready. |
| **E.164 phone format** | Export endpoint requires E.164 (`+1XXXXXXXXXX`); `office_phone` field stores this format |
| **CSV with BOM** | Export response includes UTF-8 BOM; pass through as-is (Sheets handles BOM) |
| **Asana attachment size limit** | 100MB per attachment (Asana Business tier); 10K-row CSV is ~5MB, well under limit |
| **ContactHolder project GID** | `1201500116978260` (hardcoded in model as `PRIMARY_PROJECT_GID`) |

---

## 12. Dependencies

| Dependency | Type | Owner | Status |
|------------|------|-------|--------|
| `autom8_data` `/messages/export` endpoint | Runtime (HTTP) | autom8_data team | Production-ready, no changes needed |
| `autom8y-http` circuit breaker + retry | Library | Platform SDKs | Available (`>= 0.3.0`) |
| `autom8y-auth` S2S JWT | Library | Platform SDKs | Available (`>= 0.1.0`) |
| `autom8y-log` structured logging | Library | Platform SDKs | Available (`>= 0.3.2`) |
| Asana API (Tasks, Attachments) | Runtime (HTTP) | Asana | Stable, rate-limited |
| `AUTOM8_DATA_URL` env var | Configuration | Infrastructure | Already deployed |
| `AUTOM8_DATA_API_KEY` env var | Configuration | Infrastructure | Already deployed |
| Lambda scheduled trigger (EventBridge) | Infrastructure | Platform | Needs configuration in Phase 1 |

---

## 13. File Impact Summary

### autom8_asana -- Created

| File | Description |
|------|-------------|
| `src/autom8_asana/automation/workflows/__init__.py` | Package init, exports `WorkflowAction`, `WorkflowResult`, `WorkflowRegistry` |
| `src/autom8_asana/automation/workflows/base.py` | `WorkflowAction` ABC, `WorkflowResult`, `WorkflowItemError` dataclasses |
| `src/autom8_asana/automation/workflows/registry.py` | `WorkflowRegistry` class |
| `src/autom8_asana/automation/workflows/conversation_audit.py` | `ConversationAuditWorkflow` implementation |
| `config/rules/conversation-audit.yaml` | YAML rule definition |
| `tests/unit/clients/data/test_export.py` | Unit tests for `get_export_csv_async` |
| `tests/unit/automation/workflows/test_conversation_audit.py` | Unit tests for `ConversationAuditWorkflow` |
| `tests/unit/automation/workflows/test_base.py` | Unit tests for `WorkflowAction` protocol and `WorkflowRegistry` |
| `tests/integration/test_conversation_audit_workflow.py` | Integration test with mocked externals |

### autom8_asana -- Modified

| File | Change |
|------|--------|
| `src/autom8_asana/clients/data/client.py` | Add `get_export_csv_async()` method |
| `src/autom8_asana/clients/data/models.py` | Add `ExportResult` dataclass |
| `src/autom8_asana/automation/polling/config_schema.py` | Add `ScheduleConfig` model, optional `schedule` field on `Rule`, relaxed `conditions` validator for schedule-driven rules |
| `src/autom8_asana/automation/polling/polling_scheduler.py` | Add workflow dispatch branch in `_evaluate_rules()` for schedule-triggered rules |
| `src/autom8_asana/automation/polling/action_executor.py` | Register `"workflow"` action type that delegates to `WorkflowRegistry` |
| `src/autom8_asana/automation/polling/__init__.py` | Export new schema models (`ScheduleConfig`) |

### autom8_data -- No Changes

Per locked decision. The export endpoint at `GET /api/v1/messages/export` is production-ready.

---

## 14. Open Questions (Resolved)

All open questions from the intake have been resolved in this document:

| Question | Resolution | Section |
|----------|-----------|---------|
| Abstraction pattern for automation layer | Pattern B: WorkflowAction protocol (Pipeline/Step) | Section 3 |
| How conversation-audit generalizes | `WorkflowAction` ABC + `WorkflowRegistry` + YAML schema extension | Section 4 |
| Formal acceptance criteria | Defined per user story and per requirement | Sections 5, 6 |
| Success metrics | 8 quantitative metrics with targets and measurement methods | Section 7 |
| Per-phase scope boundaries | Explicit IN/OUT lists for P1, P2, P3 | Section 8 |

---

## 15. Stakeholder Alignment Record

| Decision | Stakeholder | Status |
|----------|-------------|--------|
| autom8_asana hosts workflow; autom8_data unchanged | Engineering | Confirmed (locked) |
| Unidirectional dependency: asana -> data | Engineering | Confirmed (locked) |
| Upload-first attachment replacement | Engineering | Confirmed (locked) |
| PollingScheduler as trigger mechanism | Engineering | Confirmed (locked) |
| Silent truncation at 10K rows | CS Team | Confirmed (locked) |
| 30-day hardcoded date window | CS Team | Confirmed (locked) |
| > 10% failure rate alert threshold | Operations | Confirmed (locked) |
| YAML-configurable schedule | Engineering | Confirmed (locked) |
| Domain-verb naming convention | Engineering | Confirmed (locked) |
| Active ContactHolders only | CS Team | Confirmed (locked) |
| WorkflowAction as batch automation primitive | Engineering | New (this PRD) |
| WorkflowRegistry for workflow discovery | Engineering | New (this PRD) |
| Schema extension (schedule block) over schema fork | Engineering | New (this PRD) |

---

## 16. Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| This PRD | `/Users/tomtenuta/code/autom8_asana/docs/requirements/PRD-conversation-audit-workflow.md` | Yes |
| Spike document | `/Users/tomtenuta/Code/autom8_data/.claude/.wip/SPIKE-conversation-audit-workflow.md` | Read in full |
| DataServiceClient | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/clients/data/client.py` | Read in full |
| DataServiceConfig | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/clients/data/config.py` | Read in full |
| Data client models | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/clients/data/models.py` | Read in full |
| AttachmentsClient | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/clients/attachments.py` | Read in full |
| ContactHolder model | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/models/business/contact.py` | Read in full |
| Business model | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/models/business/business.py` | Read in full |
| PollingScheduler | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/automation/polling/polling_scheduler.py` | Read in full |
| ActionExecutor | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/automation/polling/action_executor.py` | Read in full |
| Config schema | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/automation/polling/config_schema.py` | Read in full |
| Automation config | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/automation/config.py` | Read in full |
| EventEmitter | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/automation/events/emitter.py` | Read in full |
| EventType | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/automation/events/types.py` | Read in full |
| EventEmissionRule | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/automation/events/rule.py` | Read in full |
| pyproject.toml | `/Users/tomtenuta/code/autom8_asana/pyproject.toml` | Read in full |
