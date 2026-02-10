# TDD: Weekly Conversation Audit Workflow -- Phase 1

**TDD ID**: TDD-CONV-AUDIT-001
**Status**: Draft
**Date**: 2026-02-10
**Author**: Architect
**PRD Reference**: `PRD-CONV-AUDIT-001` (`/Users/tomtenuta/code/autom8_asana/docs/requirements/PRD-conversation-audit-workflow.md`)
**Spike Reference**: `/Users/tomtenuta/Code/autom8_data/.claude/.wip/SPIKE-conversation-audit-workflow.md`

---

## 1. Architecture Overview

### 1.1 System Context

The conversation audit workflow introduces a new automation tier -- batch workflows -- alongside the existing per-task action dispatch. The workflow runs weekly, enumerates active ContactHolder tasks, resolves each to a Business `office_phone`, fetches a 30-day conversation CSV from autom8_data, and replaces the attachment on each ContactHolder task.

```
                           autom8_asana
  +----------------------------------------------------------+
  |                                                          |
  |  PollingScheduler                                        |
  |    |                                                     |
  |    +-- action.type == "workflow"                          |
  |    |     |                                               |
  |    |     +-- WorkflowRegistry.get("conversation-audit")  |
  |    |           |                                         |
  |    |           +-- ConversationAuditWorkflow              |
  |    |                 |                                   |
  |    |                 +-- AsanaClient (enumerate holders)  |
  |    |                 +-- AsanaClient (resolve parent)     |
  |    |                 +-- DataServiceClient (export CSV)   |
  |    |                 +-- AttachmentsClient (upload/delete) |
  |    |                                                     |
  |    +-- action.type == "add_tag" | "add_comment" | ...    |
  |          |                                               |
  |          +-- ActionExecutor (existing per-task dispatch)  |
  |                                                          |
  +----------------------------------------------------------+
                      |                        |
                      v                        v
                Asana API                autom8_data
              (Tasks, Attachments)    GET /messages/export
```

**Dependency direction**: `autom8_asana --> autom8_data` (unidirectional, read-only). `autom8_data` requires zero changes.

### 1.2 New Automation Tier

| Dispatch Model | Trigger | Target | Contract | Examples |
|---------------|---------|--------|----------|----------|
| **ActionExecutor** (existing) | Condition match on individual task | Single task GID | `execute_async(task_gid, action) -> ActionResult` | `add_tag`, `add_comment`, `change_section` |
| **WorkflowAction** (new) | Schedule (time-based) | Self-enumerated batch | `execute_async(params) -> WorkflowResult` | `conversation-audit`, future: `data-sync`, `enrichment` |

Both dispatch models are invoked by PollingScheduler. The scheduler dispatches to the WorkflowRegistry when it encounters `action.type: "workflow"`.

---

## 2. Module Structure

### 2.1 Package Layout

```
src/autom8_asana/
  automation/
    workflows/                           # NEW package
      __init__.py                        # Exports WorkflowAction, WorkflowResult, WorkflowRegistry
      base.py                            # WorkflowAction ABC, WorkflowResult, WorkflowItemError
      registry.py                        # WorkflowRegistry
      conversation_audit.py              # ConversationAuditWorkflow
    polling/
      config_schema.py                   # MODIFIED: add ScheduleConfig, relax Rule.conditions
      polling_scheduler.py               # MODIFIED: add workflow dispatch branch
      action_executor.py                 # UNCHANGED (not modified)
  clients/
    data/
      client.py                          # MODIFIED: add get_export_csv_async()
      models.py                          # MODIFIED: add ExportResult dataclass
  lambda_handlers/
    conversation_audit.py                # NEW: Lambda entry point
config/
  rules/
    conversation-audit.yaml              # NEW: YAML rule definition
tests/
  unit/
    automation/
      workflows/                         # NEW
        __init__.py
        test_base.py                     # WorkflowAction protocol + WorkflowRegistry tests
        test_conversation_audit.py       # ConversationAuditWorkflow unit tests
    clients/
      data/
        test_export.py                   # NEW: get_export_csv_async tests
  integration/
    automation/
      workflows/                         # NEW
        __init__.py
        test_conversation_audit_e2e.py   # Integration test with mocked externals
```

### 2.2 Design Decision: `automation/workflows/` Placement

The workflows package sits at `automation/workflows/` (sibling to `automation/polling/` and `automation/events/`). This reflects the architectural distinction: workflows are a new dispatch model alongside polling (per-task condition match) and events (pub/sub). They are not a sub-concept of polling; rather, polling is one trigger mechanism that can dispatch to either ActionExecutor or WorkflowRegistry.

### 2.3 Design Decision: ActionExecutor Remains Unchanged

The PRD file impact matrix lists `action_executor.py` as modified. After analyzing the actual code, this is unnecessary and would be a design mistake.

**Why**: ActionExecutor's contract is `execute_async(task_gid, action) -> ActionResult` -- a per-task dispatch. Forcing workflow dispatch through ActionExecutor would require a sentinel `task_gid` and break the semantic contract. Instead, the scheduler itself branches on `action.type == "workflow"` and dispatches directly to WorkflowRegistry. This keeps ActionExecutor focused on its single responsibility (per-task actions) and avoids coupling two fundamentally different dispatch models.

---

## 3. Component Design

### 3.1 WorkflowAction ABC (`automation/workflows/base.py`)

```python
"""Base classes for batch automation workflows.

Per TDD-CONV-AUDIT-001 Section 3.1: WorkflowAction protocol, WorkflowResult,
and WorkflowItemError dataclasses for generalized batch workflow dispatch.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WorkflowItemError:
    """Error detail for a single item in a batch workflow.

    Attributes:
        item_id: Identifier for the failed item (e.g., task GID).
        error_type: Classification of the error (e.g., "export_failed",
            "phone_missing", "circuit_breaker_open").
        message: Human-readable error description.
        recoverable: Whether the error is transient and retryable.
    """

    item_id: str
    error_type: str
    message: str
    recoverable: bool = True


@dataclass
class WorkflowResult:
    """Outcome of a workflow execution cycle.

    Per PRD REQ-F08: Structured summary with total/succeeded/failed/skipped.

    Attributes:
        workflow_id: Identifier of the workflow that produced this result.
        started_at: UTC timestamp when execution began.
        completed_at: UTC timestamp when execution finished.
        total: Total items enumerated for processing.
        succeeded: Items processed successfully.
        failed: Items that encountered errors.
        skipped: Items skipped (e.g., missing phone, zero rows).
        errors: Per-item error details for failed items.
        metadata: Workflow-specific additional data (e.g., truncated count).
    """

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
        """Total execution duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def failure_rate(self) -> float:
        """Fraction of items that failed (0.0-1.0)."""
        return self.failed / self.total if self.total > 0 else 0.0


class WorkflowAction(ABC):
    """Protocol for batch automation workflows.

    Each workflow owns its full lifecycle:
    1. Enumerate targets (from Asana project, API, etc.)
    2. Process each target (fetch data, transform, act)
    3. Report results (structured WorkflowResult)

    Implementations must be idempotent: re-running the same workflow
    should produce the same end state.

    Per PRD Section 4.1: WorkflowAction is the generalized batch primitive.
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
            params: YAML-configured parameters for this workflow instance
                (e.g., date_range_days, attachment_pattern, max_concurrency).

        Returns:
            WorkflowResult with per-item success/failure tracking.
        """
        ...

    @abstractmethod
    async def validate_async(self) -> list[str]:
        """Pre-flight validation before execution.

        Returns:
            List of validation error strings (empty = ready to execute).
            Examples: missing config, unreachable upstream, invalid credentials.
        """
        ...
```

### 3.2 WorkflowRegistry (`automation/workflows/registry.py`)

```python
"""Registry for discovering and dispatching batch workflows.

Per TDD-CONV-AUDIT-001 Section 3.2: Simple dictionary-based registry.
"""

from __future__ import annotations

from autom8y_log import get_logger

from autom8_asana.automation.workflows.base import WorkflowAction

logger = get_logger(__name__)

__all__ = ["WorkflowRegistry"]


class WorkflowRegistry:
    """Registry of available WorkflowAction implementations.

    Workflows are registered at application startup and looked up by
    workflow_id when the scheduler encounters action.type == "workflow".
    """

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowAction] = {}

    def register(self, workflow: WorkflowAction) -> None:
        """Register a workflow for scheduler dispatch.

        Args:
            workflow: WorkflowAction implementation.

        Raises:
            ValueError: If workflow_id is already registered.
        """
        wid = workflow.workflow_id
        if wid in self._workflows:
            raise ValueError(
                f"Workflow '{wid}' is already registered. "
                f"Duplicate registration is not allowed."
            )
        self._workflows[wid] = workflow
        logger.info("workflow_registered", workflow_id=wid)

    def get(self, workflow_id: str) -> WorkflowAction | None:
        """Look up a workflow by ID.

        Args:
            workflow_id: The workflow_id to look up.

        Returns:
            WorkflowAction instance, or None if not found.
        """
        return self._workflows.get(workflow_id)

    def list_ids(self) -> list[str]:
        """List all registered workflow IDs.

        Returns:
            Sorted list of registered workflow_id strings.
        """
        return sorted(self._workflows.keys())
```

### 3.3 ScheduleConfig and Config Schema Extension (`polling/config_schema.py`)

The existing `Rule` model uses `conditions: list[RuleCondition]` where each `RuleCondition` requires at least one trigger type (stale/deadline/age). Workflow rules are schedule-driven with no conditions.

**Changes to `config_schema.py`**:

1. Add `ScheduleConfig` Pydantic model for per-rule schedule configuration.
2. Make `conditions` optional on `Rule` when a `schedule` block is present.
3. Add optional `schedule: ScheduleConfig | None` field to `Rule`.

```python
# New model added to config_schema.py

class ScheduleConfig(BaseModel):
    """Per-rule schedule configuration for time-based workflow triggers.

    Per TDD-CONV-AUDIT-001 Section 3.3: Enables YAML-configurable schedule
    without hardcoded day/time values.

    Attributes:
        frequency: Schedule frequency ("weekly", "daily").
        day_of_week: ISO day name for weekly schedules (e.g., "sunday").
            Required when frequency is "weekly". Ignored for "daily".

    Example YAML:
        schedule:
          frequency: "weekly"
          day_of_week: "sunday"
    """

    model_config = ConfigDict(extra="forbid")

    frequency: str
    day_of_week: str | None = None

    @field_validator("frequency")
    @classmethod
    def frequency_must_be_valid(cls, v: str) -> str:
        valid = {"weekly", "daily"}
        if v.lower() not in valid:
            raise ValueError(f"frequency must be one of {valid}, got '{v}'")
        return v.lower()

    @field_validator("day_of_week")
    @classmethod
    def day_must_be_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = {
            "monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday",
        }
        if v.lower() not in valid:
            raise ValueError(f"day_of_week must be one of {valid}, got '{v}'")
        return v.lower()

    @model_validator(mode="after")
    def weekly_requires_day(self) -> ScheduleConfig:
        if self.frequency == "weekly" and self.day_of_week is None:
            raise ValueError(
                "day_of_week is required when frequency is 'weekly'"
            )
        return self
```

**Modified `Rule` model**:

```python
class Rule(BaseModel):
    """A single automation rule definition.

    Per TDD-CONV-AUDIT-001: Extended to support schedule-driven workflow rules.
    - Condition-based rules: conditions is required (at least 1), schedule is None.
    - Schedule-based rules: conditions can be empty, schedule is required,
      action.type must be "workflow".
    """

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    name: str
    project_gid: str
    conditions: list[RuleCondition] = []  # Changed: default empty list
    action: ActionConfig
    enabled: bool = True
    schedule: ScheduleConfig | None = None  # NEW field

    @field_validator("rule_id")
    @classmethod
    def rule_id_must_be_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("rule_id must be non-empty")
        return v

    @model_validator(mode="after")
    def validate_rule_completeness(self) -> Rule:
        """Ensure rule has either conditions or schedule (or both)."""
        has_conditions = len(self.conditions) > 0
        has_schedule = self.schedule is not None

        if not has_conditions and not has_schedule:
            raise ValueError(
                "Rule must have at least one condition or a schedule block. "
                "Empty conditions are only allowed for schedule-driven rules."
            )

        if has_schedule and self.action.type != "workflow":
            raise ValueError(
                "Schedule-driven rules must use action.type='workflow'. "
                f"Got action.type='{self.action.type}'."
            )

        return self
```

**Backward compatibility**: Existing condition-based rules with no `schedule` field continue to work unchanged. The `conditions` default changes from required-list to default-empty-list, but the `validate_rule_completeness` validator ensures that rules without a schedule still require at least one condition.

### 3.4 PollingScheduler Dispatch Branch (`polling/polling_scheduler.py`)

The current `_evaluate_rules` method iterates enabled rules and calls `TriggerEvaluator.evaluate_conditions()` for each. For schedule-driven workflow rules, we add a dispatch branch before condition evaluation.

**Where the change goes**: In the `_evaluate_rules` method, inside the `for rule in enabled_rules:` loop, before the existing condition evaluation logic.

```python
# In _evaluate_rules(), within the enabled_rules loop, BEFORE condition evaluation:

if rule.schedule is not None and rule.action.type == "workflow":
    # Schedule-driven workflow dispatch
    if self._should_run_schedule(rule.schedule):
        workflow_id = rule.action.params.get("workflow_id")
        if workflow_id and self._workflow_registry:
            workflow = self._workflow_registry.get(workflow_id)
            if workflow:
                # Pre-flight validation
                validation_errors = await workflow.validate_async()
                if validation_errors:
                    structured_log.error(
                        "workflow_validation_failed",
                        rule_id=rule.rule_id,
                        workflow_id=workflow_id,
                        errors=validation_errors,
                    )
                    continue

                # Execute workflow
                result = await workflow.execute_async(rule.action.params)
                structured_log.info(
                    "workflow_completed",
                    rule_id=rule.rule_id,
                    workflow_id=workflow_id,
                    total=result.total,
                    succeeded=result.succeeded,
                    failed=result.failed,
                    skipped=result.skipped,
                    duration_seconds=result.duration_seconds,
                )
            else:
                structured_log.error(
                    "workflow_not_found",
                    rule_id=rule.rule_id,
                    workflow_id=workflow_id,
                    available=self._workflow_registry.list_ids(),
                )
    continue  # Skip condition evaluation for schedule-driven rules
```

**PollingScheduler constructor changes**:

```python
def __init__(
    self,
    config: AutomationRulesConfig,
    *,
    lock_path: str = DEFAULT_LOCK_PATH,
    client: Any = None,
    workflow_registry: WorkflowRegistry | None = None,  # NEW
) -> None:
    # ... existing init ...
    self._workflow_registry = workflow_registry
```

**`_should_run_schedule` method**:

```python
def _should_run_schedule(self, schedule: ScheduleConfig) -> bool:
    """Check if a schedule-driven rule should run now.

    For weekly schedules, checks if today matches the configured day_of_week.
    For daily schedules, always returns True (runs every day).

    Args:
        schedule: ScheduleConfig with frequency and day_of_week.

    Returns:
        True if the schedule matches the current day.
    """
    local_now = datetime.now(UTC).astimezone(self.timezone)

    if schedule.frequency == "daily":
        return True

    if schedule.frequency == "weekly":
        # Python: Monday=0, Sunday=6
        day_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
        }
        target_day = day_map.get(schedule.day_of_week or "", -1)
        return local_now.weekday() == target_day

    return False
```

**`_evaluate_rules` becomes async**: Currently `_evaluate_rules` is synchronous and wraps async action calls with `asyncio.run()`. Since workflow execution is async, the method needs to support `await`. Two options:

1. Make `_evaluate_rules` async and adjust callers.
2. Keep it sync and wrap workflow calls in `asyncio.run()` like actions.

**Decision**: Use `asyncio.run()` for workflow dispatch within `_evaluate_rules`, matching the existing pattern for `_execute_actions_async`. This avoids changing the `run()` and `run_once()` call sites.

```python
# Inside the schedule dispatch branch in _evaluate_rules:
if workflow:
    asyncio.run(self._execute_workflow_async(workflow, rule, structured_log))
```

```python
async def _execute_workflow_async(
    self,
    workflow: WorkflowAction,
    rule: Rule,
    structured_log: Any,
) -> None:
    """Execute a workflow with pre-flight validation and logging."""
    workflow_id = rule.action.params.get("workflow_id", "unknown")

    # Pre-flight validation
    validation_errors = await workflow.validate_async()
    if validation_errors:
        structured_log.error(
            "workflow_validation_failed",
            rule_id=rule.rule_id,
            workflow_id=workflow_id,
            errors=validation_errors,
        )
        return

    # Execute workflow
    try:
        result = await workflow.execute_async(rule.action.params)
        structured_log.info(
            "workflow_completed",
            rule_id=rule.rule_id,
            workflow_id=workflow_id,
            total=result.total,
            succeeded=result.succeeded,
            failed=result.failed,
            skipped=result.skipped,
            duration_seconds=round(result.duration_seconds, 2),
        )
    except Exception as exc:
        structured_log.error(
            "workflow_execution_error",
            rule_id=rule.rule_id,
            workflow_id=workflow_id,
            error=str(exc),
        )
```

### 3.5 DataServiceClient Extension (`clients/data/client.py`)

A new public method on `DataServiceClient` that reuses the existing `_get_client()`, `_circuit_breaker`, `_retry_handler`, and auth infrastructure.

```python
async def get_export_csv_async(
    self,
    office_phone: str,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> ExportResult:
    """Fetch conversation CSV export for a business phone number.

    Per TDD-CONV-AUDIT-001 Section 3.5: Calls GET /api/v1/messages/export
    on autom8_data. Returns raw CSV bytes with metadata from response headers.

    Uses the same connection pool, circuit breaker, retry handler, and
    authentication as get_insights_async.

    Args:
        office_phone: E.164 formatted phone number (e.g., "+17705753103").
        start_date: Filter start date. Default: 30 days ago (autom8_data default).
        end_date: Filter end date. Default: today (autom8_data default).

    Returns:
        ExportResult containing CSV bytes, row count, truncation flag,
        phone echo, and filename from Content-Disposition header.

    Raises:
        ExportError: On HTTP errors, circuit breaker open, or timeout.
    """
    # Check circuit breaker
    try:
        await self._circuit_breaker.check()
    except SdkCircuitBreakerOpenError as e:
        raise ExportError(
            f"Circuit breaker open for autom8_data. "
            f"Retry in {e.time_remaining:.1f}s.",
            office_phone=office_phone,
            reason="circuit_breaker",
        ) from e

    client = await self._get_client()
    path = "/api/v1/messages/export"

    # Build query parameters
    params: dict[str, str] = {"office_phone": office_phone}
    if start_date is not None:
        params["start_date"] = start_date.isoformat()
    if end_date is not None:
        params["end_date"] = end_date.isoformat()

    # PII-safe logging
    masked_phone = mask_phone_number(office_phone)

    if self._log:
        self._log.info(
            "export_request_started",
            extra={
                "office_phone": masked_phone,
                "path": path,
            },
        )

    start_time = time.monotonic()
    attempt = 0

    while True:
        try:
            response = await client.get(
                path,
                params=params,
                headers={"Accept": "text/csv"},
            )

            status = response.status_code
            if status in self._config.retry.retryable_status_codes:
                if self._retry_handler.should_retry(status, attempt):
                    retry_after: int | None = None
                    if status == 429:
                        ra_header = response.headers.get("Retry-After")
                        if ra_header:
                            try:
                                retry_after = int(ra_header)
                            except ValueError:
                                pass
                    await self._retry_handler.wait(attempt, retry_after)
                    attempt += 1
                    continue
            break

        except httpx.TimeoutException as e:
            if attempt < self._config.retry.max_retries:
                await self._retry_handler.wait(attempt, None)
                attempt += 1
                continue
            await self._circuit_breaker.record_failure(e)
            raise ExportError(
                "Export request timed out",
                office_phone=office_phone,
                reason="timeout",
            ) from e

        except httpx.HTTPError as e:
            await self._circuit_breaker.record_failure(e)
            raise ExportError(
                f"HTTP error during export: {e}",
                office_phone=office_phone,
                reason="http_error",
            ) from e

    elapsed_ms = (time.monotonic() - start_time) * 1000

    # Handle error responses
    if response.status_code >= 400:
        if response.status_code >= 500:
            error = ExportError(
                f"autom8_data export error (HTTP {response.status_code})",
                office_phone=office_phone,
                reason="server_error",
            )
            await self._circuit_breaker.record_failure(error)
            raise error
        raise ExportError(
            f"autom8_data export error (HTTP {response.status_code})",
            office_phone=office_phone,
            reason="client_error",
        )

    # Record success with circuit breaker
    await self._circuit_breaker.record_success()

    # Parse response headers
    row_count = int(response.headers.get("X-Export-Row-Count", "0"))
    truncated = response.headers.get("X-Export-Truncated", "false").lower() == "true"

    # Extract filename from Content-Disposition header
    content_disp = response.headers.get("Content-Disposition", "")
    filename = _parse_content_disposition_filename(content_disp)
    if not filename:
        # Fallback: generate filename
        phone_stripped = office_phone.lstrip("+")
        today_str = date.today().isoformat().replace("-", "")
        filename = f"conversations_{phone_stripped}_{today_str}.csv"

    if self._log:
        self._log.info(
            "export_request_completed",
            extra={
                "office_phone": masked_phone,
                "row_count": row_count,
                "truncated": truncated,
                "duration_ms": elapsed_ms,
                "filename": filename,
            },
        )

    return ExportResult(
        csv_content=response.content,
        row_count=row_count,
        truncated=truncated,
        office_phone=office_phone,
        filename=filename,
    )


def _parse_content_disposition_filename(header: str) -> str | None:
    """Extract filename from Content-Disposition header.

    Args:
        header: Content-Disposition header value.

    Returns:
        Filename string or None if not parseable.
    """
    # Pattern: attachment; filename="conversations_17705753103_20260210.csv"
    match = re.search(r'filename="?([^";\s]+)"?', header)
    return match.group(1) if match else None
```

### 3.6 ExportResult Dataclass (`clients/data/models.py`)

```python
@dataclass
class ExportResult:
    """Result of a conversation export CSV fetch.

    Per TDD-CONV-AUDIT-001 Section 3.6: Contains CSV bytes and
    metadata from autom8_data response headers.

    Attributes:
        csv_content: Raw CSV bytes (UTF-8 with BOM). Passed directly
            to AttachmentsClient.upload_async without parsing.
        row_count: Data row count from X-Export-Row-Count header.
        truncated: Whether the export was truncated at the 10K row cap,
            from X-Export-Truncated header.
        office_phone: Echo of the queried phone (for correlation in logs).
        filename: Filename from Content-Disposition header or generated fallback.
    """

    csv_content: bytes
    row_count: int
    truncated: bool
    office_phone: str
    filename: str
```

### 3.7 ExportError Exception (`exceptions.py`)

```python
class ExportError(AsanaError):
    """Error from the conversation export endpoint.

    Per TDD-CONV-AUDIT-001 Section 3.7: Raised by
    DataServiceClient.get_export_csv_async() on HTTP errors,
    circuit breaker open, or timeout.

    Attributes:
        office_phone: The phone number that was being exported.
        reason: Classification of the error.
    """

    def __init__(
        self,
        message: str,
        *,
        office_phone: str = "",
        reason: str = "unknown",
    ) -> None:
        super().__init__(message)
        self.office_phone = office_phone
        self.reason = reason
```

### 3.8 ConversationAuditWorkflow (`automation/workflows/conversation_audit.py`)

This is the first concrete `WorkflowAction` implementation. It owns the full enumerate-resolve-fetch-replace lifecycle.

```python
"""Conversation audit workflow -- weekly CSV refresh for ContactHolders.

Per TDD-CONV-AUDIT-001 Section 3.8: First WorkflowAction implementation.
Enumerates active ContactHolders, resolves each to a Business office_phone,
fetches 30-day conversation CSV from autom8_data, and replaces the
attachment on each ContactHolder task.
"""

from __future__ import annotations

import asyncio
import fnmatch
import io
import os
from datetime import UTC, datetime
from typing import Any

from autom8y_log import get_logger

from autom8_asana.automation.workflows.base import (
    WorkflowAction,
    WorkflowItemError,
    WorkflowResult,
)
from autom8_asana.clients.attachments import AttachmentsClient
from autom8_asana.clients.data.client import DataServiceClient, mask_phone_number
from autom8_asana.exceptions import ExportError
from autom8_asana.models.business.contact import ContactHolder

logger = get_logger(__name__)

# Feature flag environment variable
AUDIT_ENABLED_ENV_VAR = "AUTOM8_AUDIT_ENABLED"

# ContactHolder project GID (from ContactHolder.PRIMARY_PROJECT_GID)
CONTACT_HOLDER_PROJECT_GID = "1201500116978260"

# Default concurrency for parallel processing
DEFAULT_MAX_CONCURRENCY = 5

# Default attachment pattern for cleanup
DEFAULT_ATTACHMENT_PATTERN = "conversations_*.csv"


class ConversationAuditWorkflow(WorkflowAction):
    """Weekly conversation audit CSV refresh for ContactHolders.

    Per PRD REQ-F18: First concrete WorkflowAction implementation.

    Lifecycle:
    1. Check feature flag (AUTOM8_AUDIT_ENABLED)
    2. Enumerate active ContactHolder tasks in PRIMARY_PROJECT_GID
    3. For each ContactHolder (with concurrency limit):
       a. Resolve parent Business -> office_phone
       b. Fetch CSV from DataServiceClient.get_export_csv_async()
       c. Upload new CSV attachment (upload-first)
       d. Delete old matching CSV attachments
    4. Return WorkflowResult with per-item tracking

    Args:
        asana_client: AsanaClient for Asana API operations.
        data_client: DataServiceClient for autom8_data CSV export.
        attachments_client: AttachmentsClient for upload/delete operations.
    """

    def __init__(
        self,
        asana_client: Any,  # AsanaClient (TYPE_CHECKING avoids circular)
        data_client: DataServiceClient,
        attachments_client: AttachmentsClient,
    ) -> None:
        self._asana_client = asana_client
        self._data_client = data_client
        self._attachments_client = attachments_client

    @property
    def workflow_id(self) -> str:
        return "conversation-audit"

    async def validate_async(self) -> list[str]:
        """Pre-flight validation.

        Checks:
        1. Feature flag is enabled.
        2. DataServiceClient is reachable (circuit breaker not open).
        3. ContactHolder project is accessible.

        Returns:
            List of validation error strings (empty = ready).
        """
        errors: list[str] = []

        # Check feature flag
        env_value = os.environ.get(AUDIT_ENABLED_ENV_VAR, "").lower()
        if env_value in {"false", "0", "no"}:
            errors.append(
                f"Workflow disabled via {AUDIT_ENABLED_ENV_VAR}={env_value}"
            )
            return errors  # Short-circuit; no point checking other things

        # Check DataServiceClient circuit breaker
        try:
            from autom8y_http import CircuitBreakerOpenError as SdkCBOpen
            await self._data_client._circuit_breaker.check()
        except SdkCBOpen:
            errors.append(
                "DataServiceClient circuit breaker is open. "
                "autom8_data may be degraded."
            )
        except Exception:
            pass  # Non-circuit-breaker errors are not pre-flight failures

        return errors

    async def execute_async(
        self,
        params: dict[str, Any],
    ) -> WorkflowResult:
        """Execute the full conversation audit cycle.

        Args:
            params: YAML-configured parameters:
                - workflow_id (str): "conversation-audit"
                - date_range_days (int): Export window, default 30
                - attachment_pattern (str): Glob for old attachment cleanup
                - max_concurrency (int): Parallel processing limit, default 5

        Returns:
            WorkflowResult with total/succeeded/failed/skipped counts.
        """
        started_at = datetime.now(UTC)

        max_concurrency = params.get("max_concurrency", DEFAULT_MAX_CONCURRENCY)
        attachment_pattern = params.get(
            "attachment_pattern", DEFAULT_ATTACHMENT_PATTERN
        )

        # Step 1: Enumerate active ContactHolders
        holders = await self._enumerate_contact_holders()

        logger.info(
            "conversation_audit_started",
            total_holders=len(holders),
            max_concurrency=max_concurrency,
        )

        # Step 2: Process each holder with concurrency control
        semaphore = asyncio.Semaphore(max_concurrency)
        results: list[_HolderOutcome] = []

        async def process_one(holder_gid: str, holder_name: str | None) -> None:
            async with semaphore:
                outcome = await self._process_holder(
                    holder_gid=holder_gid,
                    holder_name=holder_name,
                    attachment_pattern=attachment_pattern,
                )
                results.append(outcome)

        await asyncio.gather(
            *[
                process_one(h["gid"], h.get("name"))
                for h in holders
            ]
        )

        # Step 3: Aggregate results
        succeeded = sum(1 for r in results if r.status == "succeeded")
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status == "skipped")
        truncated_count = sum(1 for r in results if r.truncated)
        errors = [r.error for r in results if r.error is not None]

        completed_at = datetime.now(UTC)

        workflow_result = WorkflowResult(
            workflow_id=self.workflow_id,
            started_at=started_at,
            completed_at=completed_at,
            total=len(holders),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            errors=errors,
            metadata={"truncated_count": truncated_count},
        )

        logger.info(
            "conversation_audit_completed",
            total=workflow_result.total,
            succeeded=workflow_result.succeeded,
            failed=workflow_result.failed,
            skipped=workflow_result.skipped,
            truncated=truncated_count,
            duration_seconds=round(workflow_result.duration_seconds, 2),
        )

        return workflow_result

    # --- Private Methods ---

    async def _enumerate_contact_holders(self) -> list[dict[str, Any]]:
        """List all active (non-completed) tasks in the ContactHolder project.

        Uses paginated task listing with completed_since=now filter to
        exclude completed/archived ContactHolders.

        Returns:
            List of task dicts with at least {gid, name, parent} fields.
        """
        page_iterator = self._asana_client.tasks.list_for_project_async(
            CONTACT_HOLDER_PROJECT_GID,
            opt_fields=["name", "completed", "parent", "parent.name"],
            completed_since="now",
        )
        tasks = await page_iterator.collect()
        return [
            {"gid": t.gid, "name": t.name, "parent": t.parent}
            for t in tasks
            if not t.completed
        ]

    async def _process_holder(
        self,
        holder_gid: str,
        holder_name: str | None,
        attachment_pattern: str,
    ) -> _HolderOutcome:
        """Process a single ContactHolder: resolve phone, fetch CSV, replace attachment.

        Per PRD REQ-F07: Errors are captured per-item; batch continues.

        Args:
            holder_gid: ContactHolder task GID.
            holder_name: ContactHolder task name (for logging).
            attachment_pattern: Glob pattern for old attachment cleanup.

        Returns:
            _HolderOutcome with status and optional error.
        """
        try:
            # Step A: Resolve office_phone via parent Business
            office_phone = await self._resolve_office_phone(holder_gid)
            if not office_phone:
                logger.warning(
                    "holder_skipped_no_phone",
                    holder_gid=holder_gid,
                    holder_name=holder_name,
                )
                return _HolderOutcome(
                    holder_gid=holder_gid,
                    status="skipped",
                    reason="no_office_phone",
                )

            # Step B: Fetch CSV export
            masked = mask_phone_number(office_phone)
            try:
                export = await self._data_client.get_export_csv_async(office_phone)
            except ExportError as e:
                logger.error(
                    "holder_export_failed",
                    holder_gid=holder_gid,
                    office_phone=masked,
                    error=str(e),
                    reason=e.reason,
                )
                return _HolderOutcome(
                    holder_gid=holder_gid,
                    status="failed",
                    error=WorkflowItemError(
                        item_id=holder_gid,
                        error_type=f"export_{e.reason}",
                        message=str(e),
                        recoverable=e.reason != "client_error",
                    ),
                )

            # Step C: Skip if zero data rows (REQ-F06)
            if export.row_count == 0:
                logger.info(
                    "holder_skipped_zero_rows",
                    holder_gid=holder_gid,
                    office_phone=masked,
                )
                return _HolderOutcome(
                    holder_gid=holder_gid,
                    status="skipped",
                    reason="zero_rows",
                )

            # Step D: Upload-first attachment replacement (REQ-F04)
            csv_file = io.BytesIO(export.csv_content)
            await self._attachments_client.upload_async(
                parent=holder_gid,
                file=csv_file,
                name=export.filename,
                content_type="text/csv",
            )

            # Step E: Delete old matching attachments
            await self._delete_old_attachments(
                holder_gid, attachment_pattern, exclude_name=export.filename
            )

            logger.info(
                "holder_succeeded",
                holder_gid=holder_gid,
                office_phone=masked,
                row_count=export.row_count,
                truncated=export.truncated,
            )

            return _HolderOutcome(
                holder_gid=holder_gid,
                status="succeeded",
                truncated=export.truncated,
            )

        except Exception as exc:
            logger.error(
                "holder_processing_error",
                holder_gid=holder_gid,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return _HolderOutcome(
                holder_gid=holder_gid,
                status="failed",
                error=WorkflowItemError(
                    item_id=holder_gid,
                    error_type="unexpected",
                    message=str(exc),
                    recoverable=True,
                ),
            )

    async def _resolve_office_phone(self, holder_gid: str) -> str | None:
        """Resolve ContactHolder -> parent Business -> office_phone.

        Per TDD-CONV-AUDIT-001 Section 4: Uses the Asana parent task
        relationship. ContactHolder is a subtask of Business in the
        holder pattern. Fetches the parent task with custom_fields to
        read office_phone. Single API call per holder.

        Args:
            holder_gid: ContactHolder task GID.

        Returns:
            E.164 phone string, or None if parent has no office_phone.
        """
        # Fetch the ContactHolder task to get its parent reference
        holder_task = await self._asana_client.tasks.get_async(
            holder_gid,
            opt_fields=["parent", "parent.gid"],
        )

        parent_ref = holder_task.parent
        if not parent_ref or not parent_ref.gid:
            return None

        # Fetch the parent Business task with custom_fields
        parent_task = await self._asana_client.tasks.get_async(
            parent_ref.gid,
            opt_fields=["custom_fields", "custom_fields.name",
                        "custom_fields.display_value"],
        )

        # Extract office_phone from custom_fields
        if parent_task.custom_fields:
            for cf in parent_task.custom_fields:
                cf_dict = cf if isinstance(cf, dict) else cf.model_dump()
                if cf_dict.get("name") == "Office Phone":
                    return cf_dict.get("display_value") or cf_dict.get("text_value")

        return None

    async def _delete_old_attachments(
        self,
        holder_gid: str,
        pattern: str,
        exclude_name: str,
    ) -> None:
        """Delete old CSV attachments matching pattern.

        Per PRD REQ-F04: Only deletes attachments matching the
        conversations_*.csv pattern. Non-CSV attachments are untouched.
        The just-uploaded file (exclude_name) is not deleted.

        Args:
            holder_gid: Task GID to list attachments for.
            pattern: Glob pattern to match (e.g., "conversations_*.csv").
            exclude_name: Filename to exclude from deletion (the new upload).
        """
        page_iter = self._attachments_client.list_for_task_async(
            holder_gid,
            opt_fields=["name"],
        )
        async for attachment in page_iter:
            att_name = attachment.name or ""
            if fnmatch.fnmatch(att_name, pattern) and att_name != exclude_name:
                try:
                    await self._attachments_client.delete_async(attachment.gid)
                    logger.debug(
                        "old_attachment_deleted",
                        holder_gid=holder_gid,
                        attachment_gid=attachment.gid,
                        attachment_name=att_name,
                    )
                except Exception as exc:
                    # Per EC-05: Delete failure is non-fatal.
                    # Next run cleans up the duplicate.
                    logger.warning(
                        "old_attachment_delete_failed",
                        holder_gid=holder_gid,
                        attachment_gid=attachment.gid,
                        error=str(exc),
                    )


# --- Internal Data Structure ---

from dataclasses import dataclass as _dataclass


@_dataclass
class _HolderOutcome:
    """Internal per-holder processing result."""

    holder_gid: str
    status: str  # "succeeded", "failed", "skipped"
    reason: str | None = None
    error: WorkflowItemError | None = None
    truncated: bool = False
```

---

## 4. Phone Resolution Strategy

### 4.1 ADR: Parent Task Fetch vs. Hierarchy Hydration

**Context**: ContactHolder tasks need to be resolved to their parent Business's `office_phone` field. The spike proposed two approaches:

1. **Contact hierarchy hydration**: Traverse ContactHolder -> Contact children -> UpwardTraversalMixin.to_business_async() -> Business.office_phone.
2. **Parent task fetch**: Use the Asana `parent` field on the ContactHolder task to fetch the parent Business task directly, then read `office_phone` from custom_fields.

**Decision**: **Parent task fetch** (option 2).

**Rationale**:

1. **API efficiency**: Parent task fetch is 2 API calls per holder (get holder for parent ref, get parent for custom_fields). Hierarchy hydration involves fetching all Contact children, then traversing to Business -- potentially 3-5 API calls per holder.

2. **Model relationship confirmed**: The `Task` model has `parent: NameGid | None = None`. In the holder pattern, ContactHolder is a subtask of Business (confirmed by `_create_typed_holder` in `business.py` which sets `holder._business = self`). The parent relationship is direct and reliable.

3. **No hydration overhead**: Hierarchy hydration (via `Business.from_gid_async(hydrate=True)`) loads all 7 holders and their children recursively. We only need one field (`office_phone`) from the Business. Full hydration is wasteful for a batch operation that processes 200-500 holders.

4. **Custom field extraction**: `office_phone` is a `TextField(cascading=True)` descriptor on the Business model. At the API level, it is a custom field. The parent task fetch retrieves `custom_fields` and extracts the value by name ("Office Phone"). This avoids instantiating a full Business model.

**Consequences**:

- The workflow reads `office_phone` from raw custom_fields rather than the Business model's descriptor property. This is acceptable because the field name ("Office Phone") is stable and the workflow does not need any other Business model behavior.
- If the Asana hierarchy ever changes (ContactHolder is no longer a direct child of Business), this approach breaks. This is a low-risk scenario given the established domain model.

### 4.2 Optimization: Batch Parent Resolution

For future optimization (not Phase 1), the workflow could batch-fetch all unique parent GIDs in a single pass before processing, avoiding redundant fetches when multiple ContactHolders share a parent Business. Phase 1 fetches per-holder for simplicity.

---

## 5. Concurrency Model

### 5.1 Semaphore-Based Throttling

```python
semaphore = asyncio.Semaphore(max_concurrency)  # Default: 5

async def process_one(holder_gid: str, holder_name: str | None) -> None:
    async with semaphore:
        outcome = await self._process_holder(holder_gid, holder_name, pattern)
    results.append(outcome)

await asyncio.gather(*[process_one(h["gid"], h.get("name")) for h in holders])
```

**Why semaphore**: The workflow makes both Asana API calls (rate-limited at ~1500 req/min) and autom8_data calls (protected by circuit breaker). A semaphore limits how many holders are being processed concurrently, controlling the rate of API calls without explicit rate-limiting logic.

**Default value (5)**: With 5 concurrent holders, each requiring ~4 API calls (2 Asana + 1 data export + 1 upload), the peak rate is ~20 calls in flight. For Asana at 1500 req/min, this is well within limits. For 500 holders at ~3s per holder with concurrency=5, total time is ~300s (5 min).

**Configuration**: The `max_concurrency` parameter comes from YAML `action.params.max_concurrency`, making it tunable without code changes.

---

## 6. Error Handling

### 6.1 Error Handling Matrix

| Scenario | Detection | Behavior | Recovery | REQ |
|----------|-----------|----------|----------|-----|
| No `office_phone` on parent Business | `_resolve_office_phone` returns None | Skip, count as `skipped`, log warning | Next run retries (data quality fix upstream) | REQ-F05 |
| Export returns 0 rows | `export.row_count == 0` | Skip attachment replacement, count `skipped` | Next run retries (new messages may arrive) | REQ-F06 |
| Export truncated (>10K rows) | `export.truncated == True` | Upload truncated CSV, log warning, count in metadata | Accept; narrower date range in Phase 3 | EC-03 |
| autom8_data 5xx / circuit breaker open | `ExportError` with `reason=circuit_breaker` or `server_error` | Fail this holder, existing attachment preserved | Circuit breaker resets; next weekly run retries all | REQ-F07, NFR-02 |
| Upload succeeds, delete-old fails | Exception in `_delete_old_attachments` | Log warning, continue. Holder has 2 CSVs temporarily | Next run deletes the extra attachment | EC-05 |
| Upload fails | Exception from `AttachmentsClient.upload_async` | Fail this holder, existing attachment preserved (upload-first means old still exists) | Next run retries upload | EC-06 (impossible with upload-first) |
| Asana API 429 rate limit | httpx transport respects `Retry-After` | Automatic backoff via transport layer | Transparent retry | NFR-05 |
| Lambda 15-minute timeout | Lambda kills the process | Partial progress logged; some holders updated, some not | Next run is idempotent -- retries all | EC-11, NFR-08 |
| `AUTOM8_AUDIT_ENABLED=false` | `validate_async` returns error | Workflow skipped entirely, no API calls | Set env var to `true` to re-enable | REQ-F11 |
| ContactHolder task completed | `completed_since=now` filter | Excluded from enumeration | N/A (correct behavior) | EC-07 |
| Parent Business has no parent ref | `holder_task.parent is None` | Skip, count as `skipped` | Data quality issue upstream | Defensive |

### 6.2 Upload-First Attachment Pattern

The PRD mandates upload-first (upload new before deleting old) to avoid a zero-attachment window. The sequence per holder is:

1. **Upload new CSV** to ContactHolder task.
2. **List existing attachments** matching `conversations_*.csv`.
3. **Delete old attachments** (excluding the just-uploaded file).

If step 3 fails (delete error), the holder temporarily has 2 CSV attachments. The next weekly run's step 3 cleans up both old files (the one from the failed delete plus the one from this run).

If step 1 fails (upload error), no attachments are modified. The existing (old) CSV is preserved. The holder is counted as `failed` and retried next run.

### 6.3 Circuit Breaker Behavior

The workflow reuses DataServiceClient's existing circuit breaker:

- **Threshold**: 5 consecutive failures open the circuit.
- **Recovery timeout**: 30 seconds before half-open probe.
- **Batch impact**: When the circuit opens, remaining holders fast-fail with `CircuitBreakerOpenError`. This is correct behavior -- we do not hammer a degraded service. The errors are captured per-item in `WorkflowResult.errors`.
- **Weekly recovery**: The 1-week interval between runs far exceeds the 30s recovery timeout. All holders are retried on the next run.

---

## 7. Configuration

### 7.1 YAML Rule Definition (`config/rules/conversation-audit.yaml`)

```yaml
scheduler:
  time: "02:00"
  timezone: "America/New_York"

rules:
  - rule_id: "weekly-conversation-audit"
    name: "Weekly conversation audit CSV refresh"
    project_gid: "1201500116978260"
    conditions: []
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

### 7.2 Environment Variables

| Variable | New/Existing | Default | Purpose |
|----------|-------------|---------|---------|
| `AUTOM8_DATA_URL` | Existing | `http://localhost:8000` | Base URL for DataServiceClient |
| `AUTOM8_DATA_API_KEY` | Existing | (required) | JWT token for S2S auth |
| `AUTOM8_AUDIT_ENABLED` | **New** | `true` (enabled) | Feature flag / kill switch |

**Feature flag semantics**: Matches the existing `AUTOM8_DATA_INSIGHTS_ENABLED` pattern. The workflow is enabled by default. Setting the env var to `"false"`, `"0"`, or `"no"` (case-insensitive) disables the workflow. Any other value or unset means enabled.

---

## 8. Lambda Handler (`lambda_handlers/conversation_audit.py`)

```python
"""Lambda handler for conversation audit workflow.

Per TDD-CONV-AUDIT-001 Section 8: Entry point for scheduled Lambda execution.
Triggered by EventBridge rule on configured schedule.

Environment Variables Required:
    ASANA_PAT: Asana Personal Access Token
    AUTOM8_DATA_URL: Base URL for autom8_data
    AUTOM8_DATA_API_KEY: API key for autom8_data
    AUTOM8_AUDIT_ENABLED: Feature flag (default: "true")
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from typing import Any

from autom8y_log import get_logger

logger = get_logger(__name__)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for conversation audit workflow.

    Args:
        event: EventBridge event (can contain override params).
        context: Lambda context with timeout info.

    Returns:
        Dict with execution result summary.
    """
    return asyncio.run(_handler_async(event, context))


async def _handler_async(
    event: dict[str, Any], context: Any
) -> dict[str, Any]:
    """Async implementation of the Lambda handler."""
    from autom8_asana.client import AsanaClient
    from autom8_asana.clients.data.client import DataServiceClient
    from autom8_asana.automation.workflows.conversation_audit import (
        ConversationAuditWorkflow,
        DEFAULT_MAX_CONCURRENCY,
        DEFAULT_ATTACHMENT_PATTERN,
    )

    started_at = datetime.now(UTC)
    logger.info("lambda_conversation_audit_started", event=event)

    # Build params from event or defaults
    params = {
        "workflow_id": "conversation-audit",
        "max_concurrency": event.get("max_concurrency", DEFAULT_MAX_CONCURRENCY),
        "attachment_pattern": event.get(
            "attachment_pattern", DEFAULT_ATTACHMENT_PATTERN
        ),
    }

    # Initialize clients
    asana_client = AsanaClient()
    async with DataServiceClient() as data_client:
        workflow = ConversationAuditWorkflow(
            asana_client=asana_client,
            data_client=data_client,
            attachments_client=asana_client.attachments,
        )

        # Pre-flight validation
        validation_errors = await workflow.validate_async()
        if validation_errors:
            logger.error(
                "lambda_validation_failed",
                errors=validation_errors,
            )
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": "skipped",
                    "reason": "validation_failed",
                    "errors": validation_errors,
                }),
            }

        # Execute workflow
        result = await workflow.execute_async(params)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "completed",
                "workflow_id": result.workflow_id,
                "total": result.total,
                "succeeded": result.succeeded,
                "failed": result.failed,
                "skipped": result.skipped,
                "duration_seconds": round(result.duration_seconds, 2),
                "failure_rate": round(result.failure_rate, 4),
                "truncated_count": result.metadata.get("truncated_count", 0),
            }),
        }
```

---

## 9. Sequence Diagrams

### 9.1 Happy Path: End-to-End Flow

```
Lambda/Cron                Workflow                  Asana API             DataServiceClient        autom8_data        AttachmentsClient
    |                         |                         |                         |                      |                      |
    |-- execute_async(params)->|                         |                         |                      |                      |
    |                         |-- list_for_project ----->|                         |                      |                      |
    |                         |<-- [holder1, holder2] ---|                         |                      |                      |
    |                         |                         |                         |                      |                      |
    |                         |-- [per holder, semaphore(5)] ----+                |                      |                      |
    |                         |                                  |                |                      |                      |
    |                         |-- get_async(holder_gid) -------->|                |                      |                      |
    |                         |<-- task(parent={gid:BIZ}) -------|                |                      |                      |
    |                         |-- get_async(BIZ, custom_fields)->|                |                      |                      |
    |                         |<-- task(office_phone=+1...) -----|                |                      |                      |
    |                         |                                  |                |                      |                      |
    |                         |-- get_export_csv_async(phone) ----------------->  |                      |                      |
    |                         |                                  |                |-- GET /export ------->|                      |
    |                         |                                  |                |<-- CSV + headers -----|                      |
    |                         |<-- ExportResult(csv, rows, trunc) --------------|                      |                      |
    |                         |                                  |                |                      |                      |
    |                         |-- upload_async(holder, csv) ------------------------------------------------>|                 |
    |                         |<-- Attachment ------------------------------------------------------------|                 |
    |                         |                                  |                |                      |                      |
    |                         |-- list_for_task(holder) -------------------------------------------------------->|              |
    |                         |<-- [old_csv, new_csv] ----------------------------------------------------------|              |
    |                         |-- delete_async(old_csv.gid) ---------------------------------------------------->|              |
    |                         |<-- OK -------------------------------------------------------------------|              |
    |                         |                                  |                |                      |                      |
    |<-- WorkflowResult ------|                                  |                |                      |                      |
```

### 9.2 Error Path: Circuit Breaker Opens Mid-Batch

```
    Workflow                  DataServiceClient        Circuit Breaker
      |                              |                       |
      |-- process holder 1 --------->|                       |
      |<-- ExportResult (OK) --------|-- record_success ---->|
      |                              |                       |
      |-- process holder 2 --------->|                       |
      |<-- 500 error ----------------|-- record_failure ---->| (count: 1)
      |   [retry...]                 |                       |
      |<-- 500 error ----------------|-- record_failure ---->| (count: 2)
      |   [retry exhausted]          |                       |
      |   result: failed             |                       |
      |                              |                       |
      |-- ...holders 3-6 fail... --->|-- record_failure ---->| (count: 5 = threshold)
      |                              |                       | STATE -> OPEN
      |                              |                       |
      |-- process holder 7 --------->|                       |
      |                              |-- check() ----------->|
      |                              |<-- CircuitBreakerOpen -|  (fast-fail)
      |<-- ExportError(circuit_breaker)|                     |
      |   result: failed             |                       |
      |                              |                       |
      |-- ...remaining holders fast-fail similarly...        |
      |                              |                       |
      |-- WorkflowResult(failed=N, succeeded=1) ------------>|
```

### 9.3 Error Path: Upload-First Attachment Replacement Failure

```
    Workflow                  AttachmentsClient
      |                              |
      |-- upload_async(new CSV) ---->|
      |<-- Attachment(new_gid) ------|  SUCCESS: new CSV is now on the task
      |                              |
      |-- list_for_task(holder) ---->|
      |<-- [old_csv, new_csv] ------|
      |                              |
      |-- delete_async(old_csv) ---->|
      |<-- EXCEPTION (Asana error) --|  FAILURE: delete failed
      |                              |
      |   Log warning; continue      |  Holder has 2 CSVs temporarily
      |   status: "succeeded"        |  Next run cleans up the duplicate
      |                              |
```

---

## 10. Test Strategy

### 10.1 Unit Test Boundaries

| Test File | What is Tested | What is Mocked |
|-----------|----------------|----------------|
| `tests/unit/automation/workflows/test_base.py` | `WorkflowResult` properties (`duration_seconds`, `failure_rate`), `WorkflowItemError` dataclass, `WorkflowRegistry` (register, get, list_ids, duplicate rejection) | Nothing (pure data structures) |
| `tests/unit/automation/workflows/test_conversation_audit.py` | `ConversationAuditWorkflow.execute_async`: enumeration, phone resolution, skip-no-phone, skip-zero-rows, upload-first ordering, delete-old-pattern-matching, error isolation, semaphore concurrency, feature flag | `AsanaClient` (MagicMock), `DataServiceClient` (AsyncMock), `AttachmentsClient` (AsyncMock) |
| `tests/unit/clients/data/test_export.py` | `DataServiceClient.get_export_csv_async`: successful export, header parsing (row_count, truncated, filename), circuit breaker integration, retry on 5xx, timeout handling, 0-row response | `httpx.AsyncClient` (via `respx` mock), circuit breaker (mock) |

### 10.2 Integration Test

| Test File | Scope | Mocking |
|-----------|-------|---------|
| `tests/integration/automation/workflows/test_conversation_audit_e2e.py` | Full workflow lifecycle: enumerate -> resolve -> fetch -> replace, with multiple holders including skip and failure scenarios | Asana API: `respx` intercepting httpx calls. autom8_data: `respx` intercepting the export endpoint. No live API calls. |

### 10.3 Mock Conventions

Following existing test patterns in the codebase:

```python
# Pattern from test_client.py: MagicMock for providers, direct instantiation for config
from unittest.mock import AsyncMock, MagicMock, patch

# AsanaClient mock with sub-client chain
mock_asana = MagicMock()
mock_asana.tasks.get_async = AsyncMock(return_value=mock_task)
mock_asana.tasks.list_for_project_async = MagicMock(return_value=mock_page_iter)

# DataServiceClient mock
mock_data_client = AsyncMock(spec=DataServiceClient)
mock_data_client.get_export_csv_async = AsyncMock(return_value=ExportResult(...))

# AttachmentsClient mock
mock_attachments = AsyncMock(spec=AttachmentsClient)
mock_attachments.upload_async = AsyncMock(return_value=mock_attachment)
mock_attachments.list_for_task_async = MagicMock(return_value=mock_page_iter)
mock_attachments.delete_async = AsyncMock()
```

### 10.4 Key Test Scenarios

**WorkflowRegistry tests** (`test_base.py`):
- Register and retrieve workflow by ID.
- `get` returns None for unregistered ID.
- `list_ids` returns sorted list.
- Duplicate registration raises ValueError.

**ConversationAuditWorkflow tests** (`test_conversation_audit.py`):
- Happy path: 3 holders, all succeed. Assert `succeeded=3, failed=0, skipped=0`.
- Skip no phone: 1 of 3 holders has no parent.office_phone. Assert `skipped=1`.
- Skip zero rows: export returns `row_count=0`. Assert `skipped=1`.
- Export failure: DataServiceClient raises ExportError. Assert `failed=1`, error captured.
- Circuit breaker open: All exports fail. Assert `failed=N`.
- Upload-first ordering: Assert `upload_async` called before `delete_async`.
- Feature flag disabled: `validate_async` returns error. Workflow not executed.
- Truncated export: `export.truncated=True`. Assert metadata has `truncated_count`.
- Delete-old failure: `delete_async` raises. Holder still counted as `succeeded`.
- Concurrency: Assert `asyncio.Semaphore` used with correct value from params.

**get_export_csv_async tests** (`test_export.py`):
- Successful 200 with CSV body and expected headers.
- Parse `X-Export-Row-Count` and `X-Export-Truncated` from headers.
- Parse filename from `Content-Disposition` header.
- Fallback filename when Content-Disposition is missing.
- Circuit breaker check called before request.
- Circuit breaker records success on 200.
- Circuit breaker records failure on 5xx.
- Retry on 502/503/504.
- ExportError raised on 4xx.
- Timeout handling with retry.

---

## 11. File Impact Matrix

### 11.1 Files Created

| File | Description |
|------|-------------|
| `src/autom8_asana/automation/workflows/__init__.py` | Package init. Exports `WorkflowAction`, `WorkflowResult`, `WorkflowItemError`, `WorkflowRegistry`. |
| `src/autom8_asana/automation/workflows/base.py` | `WorkflowAction` ABC, `WorkflowResult` and `WorkflowItemError` dataclasses. |
| `src/autom8_asana/automation/workflows/registry.py` | `WorkflowRegistry` class. |
| `src/autom8_asana/automation/workflows/conversation_audit.py` | `ConversationAuditWorkflow` implementing the full lifecycle. |
| `src/autom8_asana/lambda_handlers/conversation_audit.py` | Lambda handler entry point for scheduled execution. |
| `config/rules/conversation-audit.yaml` | YAML rule definition for the weekly audit. |
| `tests/unit/automation/workflows/__init__.py` | Test package init. |
| `tests/unit/automation/workflows/test_base.py` | Unit tests for `WorkflowAction` protocol and `WorkflowRegistry`. |
| `tests/unit/automation/workflows/test_conversation_audit.py` | Unit tests for `ConversationAuditWorkflow`. |
| `tests/unit/clients/data/test_export.py` | Unit tests for `get_export_csv_async`. |
| `tests/integration/automation/workflows/__init__.py` | Integration test package init. |
| `tests/integration/automation/workflows/test_conversation_audit_e2e.py` | Integration test with mocked HTTP. |

### 11.2 Files Modified

| File | Change Description |
|------|-------------------|
| `src/autom8_asana/clients/data/client.py` | Add `get_export_csv_async()` method (~80 lines) and `_parse_content_disposition_filename` helper. Add `ExportError` import. |
| `src/autom8_asana/clients/data/models.py` | Add `ExportResult` dataclass (~20 lines). Add `dataclasses` import. |
| `src/autom8_asana/exceptions.py` | Add `ExportError` exception class (~20 lines). |
| `src/autom8_asana/automation/polling/config_schema.py` | Add `ScheduleConfig` model (~40 lines). Modify `Rule` model: make `conditions` default to `[]`, add `schedule` field, add `validate_rule_completeness` validator. Update `__all__`. |
| `src/autom8_asana/automation/polling/polling_scheduler.py` | Add `workflow_registry` constructor parameter. Add `_should_run_schedule` method (~20 lines). Add schedule dispatch branch in `_evaluate_rules` (~30 lines). Add `_execute_workflow_async` method (~25 lines). Add `WorkflowRegistry` import. |
| `src/autom8_asana/automation/polling/__init__.py` | Add `ScheduleConfig` to imports and `__all__`. |

### 11.3 Files NOT Modified

| File | Reason |
|------|--------|
| `src/autom8_asana/automation/polling/action_executor.py` | ActionExecutor handles per-task dispatch only. Workflow dispatch goes through PollingScheduler -> WorkflowRegistry, not through ActionExecutor. See ADR Section 2.3. |
| `src/autom8_asana/clients/data/config.py` | No configuration changes needed. Export calls reuse existing `DataServiceConfig` (base_url, timeout, retry, circuit_breaker). |
| All `autom8_data` files | Locked decision: zero changes to autom8_data. |

---

## 12. ADRs

### ADR-CONV-001: Workflow Dispatch Bypasses ActionExecutor

**Context**: The PRD file impact matrix listed `action_executor.py` as modified to register `"workflow"` action type. After code analysis, ActionExecutor's contract is `execute_async(task_gid, action) -> ActionResult` -- fundamentally a per-task dispatch.

**Decision**: Workflow dispatch goes directly from PollingScheduler to WorkflowRegistry, bypassing ActionExecutor entirely.

**Rationale**: Forcing workflow dispatch through ActionExecutor requires a sentinel `task_gid` (e.g., the project GID) and would break the semantic contract. The workflow enumerates its own targets internally. Keeping the dispatch models separate preserves clean separation of concerns: ActionExecutor for per-task actions, WorkflowRegistry for batch workflows.

**Consequences**: ActionExecutor remains unchanged and focused. PollingScheduler has a new branch in `_evaluate_rules` for `action.type == "workflow"` rules. The two dispatch models are orthogonal.

### ADR-CONV-002: Parent Task Fetch for Phone Resolution

**Context**: Two approaches for resolving ContactHolder -> office_phone. See Section 4.1 for full analysis.

**Decision**: Use Asana `parent` field to fetch the parent Business task directly, read `office_phone` from `custom_fields`.

**Rationale**: 2 API calls per holder vs. 3-5 for hierarchy hydration. No need for full Business model instantiation. The parent relationship is reliable in the holder pattern.

**Consequences**: The workflow reads raw custom_fields by name ("Office Phone") rather than using the Business model's descriptor property. Coupling to the field name is acceptable given its stability.

### ADR-CONV-003: ExportResult as Dataclass, Not Pydantic Model

**Context**: The existing data client models (`InsightsRequest`, `InsightsResponse`) use Pydantic v2 models. `ExportResult` could follow this pattern or use a plain dataclass.

**Decision**: Use a plain `@dataclass` for `ExportResult`.

**Rationale**: `ExportResult` is an internal data transfer object constructed by `get_export_csv_async` from HTTP response headers and body. It does not need Pydantic validation, serialization, or model_validate. The `csv_content: bytes` field is poorly suited to Pydantic's JSON serialization. A dataclass is simpler and sufficient.

**Consequences**: `ExportResult` cannot be serialized to JSON via `model_dump()`. This is acceptable because the CSV bytes are written directly to the Asana upload stream. Logging uses the scalar fields (row_count, truncated, filename).

### ADR-CONV-004: Schedule Evaluation in PollingScheduler, Not Separate ScheduleEvaluator

**Context**: The schedule check (`_should_run_schedule`) could live in its own class (analogous to `TriggerEvaluator` for conditions) or as a method on `PollingScheduler`.

**Decision**: Add `_should_run_schedule` as a private method on `PollingScheduler`.

**Rationale**: The schedule evaluation is trivially simple (check day-of-week for weekly, always-true for daily). Extracting it into a separate class would be over-engineering. If schedule evaluation becomes complex (cron expressions, per-rule last-run tracking), it can be extracted later. For Phase 1, a private method is sufficient.

**Consequences**: PollingScheduler grows by one small method. The method is easily testable in isolation.

---

## 13. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `conditions: []` default breaks existing rules | Low | High | `validate_rule_completeness` validator requires either conditions or schedule. Rules without schedule still need conditions. Unit tests cover both paths. |
| Phone resolution returns stale or wrong phone | Low | Medium | `office_phone` is a cascading field on Business -- always propagated. The parent relationship is stable. |
| Concurrent `asyncio.run()` calls in `_evaluate_rules` | Medium | Medium | Only one workflow rule should be present per config file. If multiple schedule rules exist, each gets its own `asyncio.run()` call sequentially (rules loop is sequential). |
| Lambda cold start adds latency | Low | Low | Lazy client initialization. Cold start adds ~2-3s, negligible for a workflow that takes 60-300s. |
| `_get_client()` creates httpx client with `Accept: application/json` | Medium | High | `get_export_csv_async` passes `headers={"Accept": "text/csv"}` per-request, overriding the client default. httpx merges request headers over client headers. |

---

## 14. Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| This TDD | `/Users/tomtenuta/code/autom8_asana/docs/design/TDD-conversation-audit-workflow.md` | Written |
| PRD | `/Users/tomtenuta/code/autom8_asana/docs/requirements/PRD-conversation-audit-workflow.md` | Read in full |
| Spike | `/Users/tomtenuta/Code/autom8_data/.claude/.wip/SPIKE-conversation-audit-workflow.md` | Read in full |
| DataServiceClient | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/clients/data/client.py` | Read in full (1664 lines) |
| DataServiceConfig | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/clients/data/config.py` | Read in full (309 lines) |
| Data client models | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/clients/data/models.py` | Read in full (468 lines) |
| AttachmentsClient | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/clients/attachments.py` | Read in full (673 lines) |
| PollingScheduler | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/automation/polling/polling_scheduler.py` | Read in full (544 lines) |
| ActionExecutor | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/automation/polling/action_executor.py` | Read in full (246 lines) |
| Config schema | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/automation/polling/config_schema.py` | Read in full (294 lines) |
| Config loader | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/automation/polling/config_loader.py` | Read in full (242 lines) |
| ContactHolder model | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/models/business/contact.py` | Read in full (237 lines) |
| Business model | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/models/business/business.py` | Read in full (792 lines) |
| Task model | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/models/task.py` | Read (80 lines, `parent: NameGid` confirmed) |
| Automation __init__ | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/automation/__init__.py` | Read in full |
| Polling __init__ | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/automation/polling/__init__.py` | Read in full |
| Lambda handler pattern | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/lambda_handlers/cache_warmer.py` | Read (60 lines, bootstrap pattern) |
| Exceptions | `/Users/tomtenuta/code/autom8_asana/src/autom8_asana/exceptions.py` | Grep'd for exception hierarchy |
| Test conventions | `/Users/tomtenuta/code/autom8_asana/tests/unit/clients/data/test_client.py` | Read (100 lines, mock patterns) |
| pyproject.toml | `/Users/tomtenuta/code/autom8_asana/pyproject.toml` | Read in full (200 lines) |
