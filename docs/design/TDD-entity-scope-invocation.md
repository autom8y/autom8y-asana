# TDD: EntityScope Invocation Layer (Revised)

```yaml
id: TDD-ENTITY-SCOPE-001
prd: PRD-ENTITY-SCOPE-001
status: draft
author: architect
date: 2026-02-19
revision: 2
revision_note: Stakeholder interview overrides -- protocol-level enumerate_async, production API, clean break
complexity: MODULE
estimated_effort: 7-10 days
```

## 1. Overview

This document specifies the technical design for adding entity-scoped invocation to the batch workflow subsystem. The feature introduces four capabilities:

1. **EntityScope abstraction** -- a frozen dataclass that represents entity targeting and execution control, passed to workflows via the handler factory.
2. **WorkflowAction ABC extension** -- a new abstract method `enumerate_async(scope)` on the ABC, with a corresponding signature change to `execute_async(entities, params)`. This is a **clean break** -- no deprecation bridge, all implementations update.
3. **Handler factory orchestration** -- `create_workflow_handler` calls `enumerate_async(scope)` and passes the resulting entity list to `execute_async(entities, params)`.
4. **Production invoke endpoint** -- `POST /api/v1/workflows/{workflow_id}/invoke` with API versioning, rate limiting, full audit logging, and an error response contract aligned with existing API patterns.

### Revision History

This is **Revision 2**. The following decisions were overridden by stakeholder interview:

| Original TDD Decision | Stakeholder Override | Impact |
|----------------------|---------------------|--------|
| Inline 4-line checks per workflow (ADR-001) | `enumerate_async(scope)` as abstract method on WorkflowAction ABC | Protocol-level change; all implementations must provide enumeration |
| Dev tooling assumption for invoke endpoint | Full production API contract | Rate limiting, audit logging, proper error responses, API versioning |
| Backward-compatible params dict transport | Clean break: `execute_async(entities, params)` receives entity list | All existing tests need signature updates |
| Scope: protocol + all 3 workflows wired | Protocol + 2 workflows wired (insights-export, conversation-audit); PipelineTransition gets ABC method but wiring deferred | Reduces blast radius |
| EntityScope module home in `automation/workflows/scope.py` | Architect determines based on dependency analysis | See ADR-001 |

### Design Principles

- **Protocol-level enumeration**: Every workflow declares its enumeration strategy via `enumerate_async`. The handler factory orchestrates: enumerate, then execute.
- **Clean separation of concerns**: `enumerate_async` owns entity discovery; `execute_async` owns processing. Neither knows about the other's internals.
- **Production-grade API surface**: The invoke endpoint is a durable contract. Other services and triggers may call it.
- **Clean break over backward compat**: The ABC changes. All implementations and tests update in a single coordinated change.

### Constraint Summary

| Constraint | Source | Implication |
|------------|--------|-------------|
| `WorkflowAction` ABC has 3 production implementations | base.py, insights_export.py, conversation_audit.py, pipeline_transition.py | All must implement `enumerate_async` and adapt to new `execute_async` signature |
| Whitelist merge in handler factory | `create_workflow_handler` lines 121-124 | Handler factory now calls `enumerate_async` before `execute_async` |
| Per-request AsanaClient in API context | ADR-ASANA-007 | Workflows in API context need freshly constructed clients |
| DataServiceClient token via `AUTOM8_DATA_API_KEY` env var | `config.py`, `resolve_secret_from_env` | Production auth uses `ASANA_SERVICE_KEY` -> JWT exchange -> data service |
| Existing test suite assumes `execute_async(params: dict)` signature | ~34 test files reference execute_async | Clean break requires test migration |

---

## 2. Component Design

### 2.1 EntityScope Dataclass

**File**: `src/autom8_asana/core/scope.py` (new file)

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EntityScope:
    """Workflow-agnostic entity targeting and execution control.

    Frozen dataclass constructed once at the invocation boundary (Lambda
    handler, API endpoint, or CLI). Passed to WorkflowAction.enumerate_async()
    to control which entities are resolved.

    Attributes:
        entity_ids: GIDs to target. Empty tuple means full enumeration.
        section_filter: Section names to restrict enumeration to.
            Ignored when entity_ids is non-empty.
        limit: Maximum entities to process. None means no limit.
        dry_run: If True, skip write operations (upload, delete).
    """

    entity_ids: tuple[str, ...] = ()
    section_filter: frozenset[str] = frozenset()
    limit: int | None = None
    dry_run: bool = False

    @classmethod
    def from_event(cls, event: dict[str, Any]) -> EntityScope:
        """Construct from a Lambda event dict or API request body.

        Normalizes input types:
        - entity_ids: accepts list[str] or tuple[str, ...], stored as tuple
        - section_filter: accepts list[str] or set[str], stored as frozenset
        - limit: accepts int or None
        - dry_run: accepts bool (default False)

        Unknown keys are silently ignored (forward-compatible).

        Args:
            event: Raw event dict from Lambda, API, or CLI.

        Returns:
            Frozen EntityScope instance.
        """
        raw_ids = event.get("entity_ids", ())
        raw_sections = event.get("section_filter", ())
        return cls(
            entity_ids=tuple(raw_ids) if raw_ids else (),
            section_filter=frozenset(raw_sections) if raw_sections else frozenset(),
            limit=event.get("limit"),
            dry_run=bool(event.get("dry_run", False)),
        )

    @property
    def has_entity_ids(self) -> bool:
        """True when specific entities are targeted."""
        return bool(self.entity_ids)

    def to_params(self) -> dict[str, Any]:
        """Serialize to flat dict for injection into workflow params.

        Returns:
            Dict with dry_run key only. Entity targeting is handled
            via enumerate_async, not params.
        """
        return {
            "dry_run": self.dry_run,
        }
```

**Module home rationale (see ADR-001)**: `core/scope.py`, not `automation/workflows/scope.py`. EntityScope is consumed by the handler factory (in `lambda_handlers/`), the API layer (in `api/routes/`), and the CLI (in `scripts/`). Placing it in `automation/workflows/` would create an upward dependency from `core/` consumers into `automation/`. The `core/` package is the project's cross-cutting concern home -- it already holds `entity_types.py`, `creation.py`, and `project_registry.py`. EntityScope fits this pattern.

### 2.2 WorkflowAction ABC Extension

**File**: `src/autom8_asana/automation/workflows/base.py` (modify)

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from autom8_asana.core.scope import EntityScope


# WorkflowItemError and WorkflowResult unchanged (omitted for brevity)


class WorkflowAction(ABC):
    """Protocol for batch automation workflows.

    Each workflow owns its full lifecycle:
    1. Enumerate targets via enumerate_async(scope)
    2. Process the entity list via execute_async(entities, params)
    3. Report results (structured WorkflowResult)

    Implementations must be idempotent: re-running the same workflow
    should produce the same end state.
    """

    @property
    @abstractmethod
    def workflow_id(self) -> str:
        """Unique identifier for this workflow type."""
        ...

    @abstractmethod
    async def enumerate_async(
        self,
        scope: EntityScope,
    ) -> list[dict[str, Any]]:
        """Enumerate entities to process based on the given scope.

        When scope.has_entity_ids is True, return synthetic entity dicts
        for the targeted GIDs (skip full project enumeration).

        When scope.has_entity_ids is False, perform full enumeration
        (existing behavior).

        The returned list shape is workflow-specific:
        - InsightsExport: [{gid, name, parent_gid}, ...]
        - ConversationAudit: [{gid, name, parent_gid, parent}, ...]
        - PipelineTransition: [{gid, name, project_gid, outcome}, ...]

        Args:
            scope: EntityScope controlling targeting, filtering, and limits.

        Returns:
            List of entity dicts ready for execute_async processing.
        """
        ...

    @abstractmethod
    async def execute_async(
        self,
        entities: list[dict[str, Any]],
        params: dict[str, Any],
    ) -> WorkflowResult:
        """Execute the workflow for the given entity list.

        Args:
            entities: Entity dicts from enumerate_async. Shape is
                workflow-specific.
            params: Configuration parameters (max_concurrency,
                attachment_pattern, dry_run, etc.)

        Returns:
            WorkflowResult with per-item success/failure tracking.
        """
        ...

    @abstractmethod
    async def validate_async(self) -> list[str]:
        """Pre-flight validation before execution.

        Returns:
            List of validation error strings (empty = ready to execute).
        """
        ...
```

**Key changes**:
1. New abstract method `enumerate_async(self, scope: EntityScope) -> list[dict[str, Any]]`
2. `execute_async` signature changes from `(self, params: dict)` to `(self, entities: list[dict], params: dict)`
3. `validate_async` is unchanged.

### 2.3 Handler Factory Extension

**File**: `src/autom8_asana/lambda_handlers/workflow_handler.py` (modify `_execute`)

The handler factory becomes the orchestrator: it constructs `EntityScope`, calls `enumerate_async`, then passes the entity list to `execute_async`.

**Current code (lines 110-137)**:
```python
async def _execute(event: dict[str, Any]) -> dict[str, Any]:
    # ... client construction ...
    params: dict[str, Any] = {**config.default_params}
    for key in config.default_params:
        if key in event:
            params[key] = event[key]
    params["workflow_id"] = config.workflow_id

    # ... workflow construction and execution ...
    result = await workflow.execute_async(params)
```

**New code**:
```python
from autom8_asana.core.scope import EntityScope

async def _execute(event: dict[str, Any]) -> dict[str, Any]:
    from autom8_asana.client import AsanaClient

    logger.info(f"{config.log_prefix}_started", lambda_event=event)
    emit_metric(
        "WorkflowExecutionCount",
        1,
        dimensions={"workflow_id": config.workflow_id},
    )

    # Construct EntityScope from event
    scope = EntityScope.from_event(event)

    # Merge event overrides onto defaults (existing whitelist)
    params: dict[str, Any] = {**config.default_params}
    for key in config.default_params:
        if key in event:
            params[key] = event[key]
    params["workflow_id"] = config.workflow_id

    # Inject scope-derived params (dry_run)
    params.update(scope.to_params())

    # Add source and dry_run to execution metric
    emit_metric(
        "WorkflowExecutionCount",
        1,
        dimensions={
            "workflow_id": config.workflow_id,
            "source": "lambda",
            "dry_run": str(scope.dry_run).lower(),
        },
    )

    asana_client = AsanaClient()

    if config.requires_data_client:
        from autom8_asana.clients.data.client import DataServiceClient

        async with DataServiceClient() as data_client:
            workflow = config.workflow_factory(asana_client, data_client)
            return await _validate_enumerate_and_run(workflow, scope, params)
    else:
        workflow = config.workflow_factory(asana_client, None)
        return await _validate_enumerate_and_run(workflow, scope, params)


async def _validate_enumerate_and_run(
    workflow: WorkflowAction,
    scope: EntityScope,
    params: dict[str, Any],
) -> dict[str, Any]:
    # Pre-flight validation
    validation_errors = await workflow.validate_async()
    if validation_errors:
        logger.error(
            f"{config.log_prefix}_validation_failed",
            errors=validation_errors,
        )
        emit_metric(
            "WorkflowValidationSkipped",
            1,
            dimensions={"workflow_id": config.workflow_id},
        )
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "skipped",
                "reason": "validation_failed",
                "errors": validation_errors,
            }),
        }

    # Enumerate entities
    entities = await workflow.enumerate_async(scope)

    # Execute workflow with entity list
    result = await workflow.execute_async(entities, params)

    emit_metric(
        "WorkflowDuration",
        result.duration_seconds,
        unit="Seconds",
        dimensions={"workflow_id": config.workflow_id},
    )
    emit_metric(
        "WorkflowSuccessRate",
        round(100 * (1 - result.failure_rate), 2),
        unit="Percent",
        dimensions={"workflow_id": config.workflow_id},
    )

    return {
        "statusCode": 200,
        "body": json.dumps(
            result.to_response_dict(
                extra_metadata_keys=list(config.response_metadata_keys),
            )
        ),
    }
```

**Why this ordering matters**: The handler factory now orchestrates the workflow lifecycle: validate, enumerate, execute. This separates enumeration concerns from execution concerns at the protocol level.

### 2.4 Workflow Implementation -- InsightsExportWorkflow

**File**: `src/autom8_asana/automation/workflows/insights_export.py`

#### 2.4.1 New `enumerate_async` method

The existing `_enumerate_offers()` logic is moved into `enumerate_async`:

```python
async def enumerate_async(
    self,
    scope: EntityScope,
) -> list[dict[str, Any]]:
    """Enumerate Offer entities based on scope.

    When scope.has_entity_ids: return synthetic offer dicts for each GID.
    When scope is empty: perform full section-targeted enumeration.
    """
    if scope.has_entity_ids:
        offers = [
            {"gid": gid, "name": None, "parent_gid": None}
            for gid in scope.entity_ids
        ]
        logger.info(
            "insights_export_targeted",
            entity_ids=scope.entity_ids,
            dry_run=scope.dry_run,
        )
        return offers

    # Full enumeration (existing _enumerate_offers logic)
    offers = await self._enumerate_offers()

    # Apply section_filter if provided
    # (section_filter is applied at enumeration time, not here,
    #  since _enumerate_offers already filters by ACTIVE sections)

    # Apply limit if provided
    if scope.limit is not None and len(offers) > scope.limit:
        offers = offers[:scope.limit]

    return offers
```

#### 2.4.2 Modified `execute_async` signature

```python
async def execute_async(
    self,
    entities: list[dict[str, Any]],
    params: dict[str, Any],
) -> WorkflowResult:
    """Execute the insights export for the given entities.

    Args:
        entities: Offer dicts from enumerate_async.
            Shape: [{gid, name, parent_gid}, ...]
        params: Configuration parameters:
            - max_concurrency (int): Parallel offer limit, default 5
            - row_limits (dict): Per-table row limits override
            - attachment_pattern (str): Glob for old attachment cleanup
            - dry_run (bool): Skip write operations

    Returns:
        WorkflowResult with total/succeeded/failed/skipped counts.
    """
    started_at = datetime.now(UTC)

    max_concurrency = params.get("max_concurrency", DEFAULT_MAX_CONCURRENCY)
    attachment_pattern = params.get(
        "attachment_pattern", DEFAULT_ATTACHMENT_PATTERN
    )
    row_limits = params.get("row_limits", DEFAULT_ROW_LIMITS)
    dry_run = params.get("dry_run", False)

    offers = entities  # Named alias for clarity

    logger.info(
        "insights_export_started",
        total_offers=len(offers),
        max_concurrency=max_concurrency,
        dry_run=dry_run,
    )

    # Process each offer with concurrency control
    semaphore = asyncio.Semaphore(max_concurrency)
    results: list[_OfferOutcome] = []

    async def process_one(
        offer_gid: str,
        offer_name: str | None,
        parent_gid: str | None,
    ) -> None:
        async with semaphore:
            outcome = await self._process_offer(
                offer_gid=offer_gid,
                offer_name=offer_name,
                parent_gid=parent_gid,
                attachment_pattern=attachment_pattern,
                row_limits=row_limits,
                dry_run=dry_run,
            )
            results.append(outcome)

    await asyncio.gather(
        *[process_one(o["gid"], o.get("name"), o.get("parent_gid")) for o in offers]
    )

    # ... rest of aggregation unchanged ...
```

#### 2.4.3 Dry-run gating in `_process_offer`

Add `dry_run: bool = False` parameter to `_process_offer`. Gate write operations:

```python
async def _process_offer(
    self,
    offer_gid: str,
    offer_name: str | None,
    parent_gid: str | None,
    attachment_pattern: str,
    row_limits: dict[str, int],
    dry_run: bool = False,
) -> _OfferOutcome:
    # ... Steps A-D unchanged (resolve, fetch tables, compose report) ...

    # Step E: Upload-first attachment replacement
    if not dry_run:
        await self._attachments_client.upload_async(
            parent=offer_gid,
            file=markdown_content.encode("utf-8"),
            name=filename,
            content_type="text/markdown",
        )

        # Step F: Delete old matching attachments
        await self._delete_old_attachments(
            offer_gid, attachment_pattern, exclude_name=filename
        )
    else:
        logger.info(
            "insights_export_dry_run_skip_write",
            offer_gid=offer_gid,
        )

    # ... Outcome construction ...
```

**Dry-run metadata enrichment**:

```python
if dry_run:
    metadata["dry_run"] = True
    metadata["report_preview"] = markdown_content[:2000]
```

### 2.5 Workflow Implementation -- ConversationAuditWorkflow

**File**: `src/autom8_asana/automation/workflows/conversation_audit.py`

#### 2.5.1 New `enumerate_async` method

```python
async def enumerate_async(
    self,
    scope: EntityScope,
) -> list[dict[str, Any]]:
    """Enumerate ContactHolder entities based on scope.

    When scope.has_entity_ids: return synthetic holder dicts for each GID.
        Skips bulk pre-resolution (single entity does not benefit).
    When scope is empty: perform full enumeration + bulk pre-resolution
        + pre-filter by business activity.
    """
    if scope.has_entity_ids:
        holders = [
            {"gid": gid, "name": None, "parent_gid": None, "parent": None}
            for gid in scope.entity_ids
        ]
        logger.info(
            "conversation_audit_targeted",
            entity_ids=scope.entity_ids,
            dry_run=scope.dry_run,
        )
        return holders

    # Full enumeration
    holders = await self._enumerate_contact_holders()

    # Bulk pre-resolve Business activities
    await self._pre_resolve_business_activities(holders)

    # Pre-filter holders with inactive parent Businesses
    from autom8_asana.models.business.activity import AccountActivity

    active_holders: list[dict[str, Any]] = []
    for h in holders:
        parent_gid = h.get("parent_gid")
        if parent_gid:
            activity = self._activity_map.get(parent_gid)
            if activity != AccountActivity.ACTIVE:
                continue
        active_holders.append(h)

    logger.info(
        "conversation_audit_enumerated",
        total_holders=len(holders),
        active_holders=len(active_holders),
        skipped_inactive=len(holders) - len(active_holders),
    )

    # Apply limit if provided
    if scope.limit is not None and len(active_holders) > scope.limit:
        active_holders = active_holders[:scope.limit]

    return active_holders
```

**Design note**: The pre-filter step moves into `enumerate_async` because it is logically part of enumeration (deciding which entities to process), not execution. This makes the separation cleaner: `enumerate_async` answers "what to process"; `execute_async` answers "how to process it".

The skipped-inactive count tracking that previously fed into `WorkflowResult.metadata` is preserved via a logging event during enumeration. The `execute_async` will track its own succeeded/failed/skipped based on the entities it receives.

#### 2.5.2 Modified `execute_async` signature

```python
async def execute_async(
    self,
    entities: list[dict[str, Any]],
    params: dict[str, Any],
) -> WorkflowResult:
    """Execute the conversation audit for the given entities.

    Args:
        entities: Holder dicts from enumerate_async.
            Shape: [{gid, name, parent_gid, parent}, ...]
        params: Configuration parameters.

    Returns:
        WorkflowResult with per-item tracking.
    """
    started_at = datetime.now(UTC)
    max_concurrency = params.get("max_concurrency", DEFAULT_MAX_CONCURRENCY)
    attachment_pattern = params.get(
        "attachment_pattern", DEFAULT_ATTACHMENT_PATTERN
    )
    date_range_days = params.get("date_range_days", DEFAULT_DATE_RANGE_DAYS)
    dry_run = params.get("dry_run", False)

    end_date = date.today()
    start_date = end_date - timedelta(days=date_range_days)

    holders = entities  # Named alias

    logger.info(
        "conversation_audit_started",
        total_holders=len(holders),
        max_concurrency=max_concurrency,
        dry_run=dry_run,
    )

    # Process each holder with concurrency control
    semaphore = asyncio.Semaphore(max_concurrency)
    results: list[_HolderOutcome] = []

    async def process_one(
        holder_gid: str,
        holder_name: str | None,
        parent_gid: str | None,
    ) -> None:
        async with semaphore:
            outcome = await self._process_holder(
                holder_gid=holder_gid,
                holder_name=holder_name,
                parent_gid=parent_gid,
                attachment_pattern=attachment_pattern,
                start_date=start_date,
                end_date=end_date,
                dry_run=dry_run,
            )
            results.append(outcome)

    await asyncio.gather(
        *[
            process_one(h["gid"], h.get("name"), h.get("parent_gid"))
            for h in holders
        ]
    )

    # ... rest of aggregation unchanged ...
```

#### 2.5.3 Dry-run gating in `_process_holder`

Add `dry_run: bool = False` parameter to `_process_holder`. Gate write operations:

```python
# Step D: Upload-first attachment replacement
if not dry_run:
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
else:
    logger.info(
        "conversation_audit_dry_run_skip_write",
        holder_gid=holder_gid,
    )
```

**Dry-run metadata**:
```python
if dry_run:
    metadata["dry_run"] = True
    metadata["csv_row_count"] = export.row_count
```

### 2.6 Workflow Implementation -- PipelineTransitionWorkflow (ABC only)

**File**: `src/autom8_asana/automation/workflows/pipeline_transition.py`

PipelineTransitionWorkflow gets the `enumerate_async` method and the updated `execute_async` signature, but API wiring is deferred. The existing enumeration logic (scanning CONVERTED/DID NOT CONVERT sections) moves into `enumerate_async`:

```python
async def enumerate_async(
    self,
    scope: EntityScope,
) -> list[dict[str, Any]]:
    """Enumerate pipeline process tasks based on scope.

    When scope.has_entity_ids: return synthetic process dicts.
    When scope is empty: scan terminal sections across pipeline projects.
    """
    if scope.has_entity_ids:
        # Targeted invocation -- build minimal process dicts
        return [
            {"gid": gid, "name": None, "project_gid": None, "outcome": None}
            for gid in scope.entity_ids
        ]

    # Full enumeration (existing logic extracted from execute_async)
    project_gids = self._default_project_gids
    converted_section = DEFAULT_CONVERTED_SECTION
    dnc_section = DEFAULT_DNC_SECTION
    # ... existing section resolution and task enumeration logic ...
    return processes


async def execute_async(
    self,
    entities: list[dict[str, Any]],
    params: dict[str, Any],
) -> WorkflowResult:
    """Execute pipeline transitions for the given process entities."""
    # Signature updated; existing logic adapts to receive entities
    # rather than performing inline enumeration.
    # ...
```

**Deferred**: PipelineTransition is not registered in the API workflow config registry or included in test wiring for the invoke endpoint. It gets the ABC method to satisfy the interface contract only.

### 2.7 FastAPI Invoke Endpoint (Production-Grade)

**File**: `src/autom8_asana/api/routes/workflows.py` (new file)

#### 2.7.1 Request/Response Models

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator


class WorkflowInvokeRequest(BaseModel):
    """Request body for workflow invocation.

    Attributes:
        entity_ids: List of Asana GIDs to target. Must be non-empty.
        dry_run: If True, skip write operations.
        params: Additional workflow-specific parameter overrides.
    """

    entity_ids: list[str]
    dry_run: bool = False
    params: dict[str, Any] = {}

    @field_validator("entity_ids")
    @classmethod
    def validate_entity_ids(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("entity_ids must be a non-empty list")
        if len(v) > 100:
            raise ValueError("entity_ids must contain at most 100 items")
        for gid in v:
            if not gid.isdigit():
                raise ValueError(
                    f"Invalid entity_id '{gid}': must be numeric (Asana GID format)"
                )
        return v


class WorkflowInvokeResponse(BaseModel):
    """Response body wrapping WorkflowResult.

    Attributes:
        request_id: Correlation ID for this invocation.
        invocation_source: Always "api" for this endpoint.
        workflow_id: ID of the invoked workflow.
        dry_run: Whether this was a dry-run invocation.
        entity_count: Number of entities processed.
        result: Serialized WorkflowResult.
    """

    request_id: str
    invocation_source: str = "api"
    workflow_id: str
    dry_run: bool
    entity_count: int
    result: dict[str, Any]
```

#### 2.7.2 Route Handler

```python
import asyncio

from autom8y_log import get_logger
from fastapi import APIRouter, Depends, Request

from autom8_asana.api.dependencies import (
    AuthContextDep,
    RequestId,
)
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.rate_limit import limiter
from autom8_asana.core.scope import EntityScope

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])

# Default timeout for workflow execution (seconds)
WORKFLOW_EXECUTION_TIMEOUT = 120


@router.post(
    "/{workflow_id}/invoke",
    response_model=WorkflowInvokeResponse,
    responses={
        400: {"description": "Validation error (empty entity_ids, non-numeric GID)"},
        401: {"description": "Missing or invalid authentication"},
        404: {"description": "Unknown workflow_id"},
        422: {"description": "Workflow pre-flight validation failed"},
        429: {"description": "Rate limit exceeded"},
        504: {"description": "Workflow execution timed out"},
    },
)
@limiter.limit("10/minute")
async def invoke_workflow(
    workflow_id: str,
    body: WorkflowInvokeRequest,
    request: Request,
    auth_context: AuthContextDep,
    request_id: RequestId,
) -> WorkflowInvokeResponse:
    """Invoke a workflow for specific entities.

    Production endpoint: rate limited, audit logged, timeout-aware.

    Constructs workflow with per-request clients, calls enumerate_async
    with targeted scope, then execute_async with the entity list.
    """
    # Audit log (full invocation context)
    logger.info(
        "workflow_invoke_api",
        workflow_id=workflow_id,
        entity_ids=body.entity_ids,
        dry_run=body.dry_run,
        request_id=request_id,
        caller_service=auth_context.caller_service,
        auth_mode=auth_context.mode.value,
    )

    # Look up workflow factory config
    factory_config = _get_workflow_factory(workflow_id)
    if factory_config is None:
        raise_api_error(
            request_id, 404, "WORKFLOW_NOT_FOUND",
            f"Workflow '{workflow_id}' is not registered for API invocation",
        )

    # Construct EntityScope
    scope = EntityScope(
        entity_ids=tuple(body.entity_ids),
        dry_run=body.dry_run,
    )

    # Build params: factory defaults + request overrides + scope
    params: dict[str, Any] = {**factory_config.default_params}
    params.update(body.params)
    params["workflow_id"] = workflow_id
    params.update(scope.to_params())

    # Construct workflow with per-request clients
    from autom8_asana.client import AsanaClient
    from autom8_asana.clients.data.client import DataServiceClient

    asana_client = AsanaClient(token=auth_context.asana_pat)

    try:
        if factory_config.requires_data_client:
            async with DataServiceClient() as data_client:
                workflow = factory_config.workflow_factory(asana_client, data_client)
                result = await _validate_enumerate_execute(
                    workflow, scope, params, request_id, WORKFLOW_EXECUTION_TIMEOUT
                )
        else:
            workflow = factory_config.workflow_factory(asana_client, None)
            result = await _validate_enumerate_execute(
                workflow, scope, params, request_id, WORKFLOW_EXECUTION_TIMEOUT
            )
    except asyncio.TimeoutError:
        logger.error(
            "workflow_invoke_timeout",
            workflow_id=workflow_id,
            request_id=request_id,
            timeout_seconds=WORKFLOW_EXECUTION_TIMEOUT,
        )
        raise_api_error(
            request_id, 504, "WORKFLOW_TIMEOUT",
            f"Workflow execution timed out after {WORKFLOW_EXECUTION_TIMEOUT}s",
        )

    # Emit metric
    from autom8_asana.lambda_handlers.cloudwatch import emit_metric

    emit_metric(
        "WorkflowInvokeCount",
        1,
        dimensions={
            "workflow_id": workflow_id,
            "source": "api",
            "dry_run": str(body.dry_run).lower(),
        },
    )

    # Audit log completion
    logger.info(
        "workflow_invoke_completed",
        workflow_id=workflow_id,
        request_id=request_id,
        succeeded=result.succeeded,
        failed=result.failed,
        duration_seconds=round(result.duration_seconds, 2),
    )

    return WorkflowInvokeResponse(
        request_id=request_id,
        invocation_source="api",
        workflow_id=workflow_id,
        dry_run=body.dry_run,
        entity_count=result.total,
        result=result.to_response_dict(
            extra_metadata_keys=list(factory_config.response_metadata_keys),
        ),
    )


async def _validate_enumerate_execute(
    workflow, scope, params, request_id, timeout_seconds,
):
    """Validate, enumerate, and execute with timeout.

    Raises:
        asyncio.TimeoutError: If execution exceeds timeout.
    """
    from autom8_asana.api.errors import raise_api_error

    # Pre-flight validation
    validation_errors = await workflow.validate_async()
    if validation_errors:
        raise_api_error(
            request_id, 422, "WORKFLOW_VALIDATION_FAILED",
            "Workflow pre-flight validation failed",
            details={"validation_errors": validation_errors},
        )

    # Enumerate + execute with timeout
    async def _run():
        entities = await workflow.enumerate_async(scope)
        return await workflow.execute_async(entities, params)

    return await asyncio.wait_for(_run(), timeout=timeout_seconds)
```

#### 2.7.3 Workflow Factory Registry (API-side)

```python
from autom8_asana.lambda_handlers.workflow_handler import WorkflowHandlerConfig

# Populated at module load from Lambda handler configs
_WORKFLOW_CONFIGS: dict[str, WorkflowHandlerConfig] = {}


def register_workflow_config(config: WorkflowHandlerConfig) -> None:
    """Register a workflow config for API invocation."""
    _WORKFLOW_CONFIGS[config.workflow_id] = config


def _get_workflow_factory(workflow_id: str) -> WorkflowHandlerConfig | None:
    """Look up workflow config by ID."""
    return _WORKFLOW_CONFIGS.get(workflow_id)
```

#### 2.7.4 Startup Registration

**File**: `src/autom8_asana/api/lifespan.py` -- add after EntityWriteRegistry initialization:

```python
# Register workflow configs for API invocation
try:
    from autom8_asana.api.routes.workflows import register_workflow_config
    from autom8_asana.lambda_handlers.insights_export import _config as insights_config
    from autom8_asana.lambda_handlers.conversation_audit import _config as audit_config

    register_workflow_config(insights_config)
    register_workflow_config(audit_config)
    logger.info(
        "workflow_configs_registered",
        extra={"workflow_ids": ["insights-export", "conversation-audit"]},
    )
except Exception as e:  # BROAD-CATCH: degrade
    logger.warning(
        "workflow_configs_registration_failed",
        extra={
            "error": str(e),
            "impact": "Workflow invoke endpoint will return 404 for all workflows",
        },
    )
```

#### 2.7.5 Router Registration

**File**: `src/autom8_asana/api/routes/__init__.py` -- add:

```python
from .workflows import router as workflows_router
```

Add `"workflows_router"` to `__all__`.

**File**: `src/autom8_asana/api/main.py` -- add:

```python
from .routes import workflows_router
# ...
app.include_router(workflows_router)
```

### 2.8 Developer CLI

**File**: `scripts/invoke_workflow.py` (new file)

Same as original TDD Section 2.7 with one adaptation: the direct invocation path now calls `enumerate_async(scope)` then `execute_async(entities, params)`:

```python
async def _invoke_direct(args: argparse.Namespace) -> int:
    """Construct workflow directly and invoke."""
    # ... config lookup, scope construction, param building ...

    # Construct clients and workflow
    from autom8_asana.client import AsanaClient

    asana_client = AsanaClient()

    if config.requires_data_client:
        from autom8_asana.clients.data.client import DataServiceClient

        async with DataServiceClient() as data_client:
            workflow = config.workflow_factory(asana_client, data_client)
            validation_errors = await workflow.validate_async()
            if validation_errors:
                print(f"VALIDATION FAILED: {validation_errors}", file=sys.stderr)
                return 1
            entities = await workflow.enumerate_async(scope)
            result = await workflow.execute_async(entities, params)
    else:
        workflow = config.workflow_factory(asana_client, None)
        validation_errors = await workflow.validate_async()
        if validation_errors:
            print(f"VALIDATION FAILED: {validation_errors}", file=sys.stderr)
            return 1
        entities = await workflow.enumerate_async(scope)
        result = await workflow.execute_async(entities, params)

    # ... output ...
```

### 2.9 Justfile Recipe

**File**: `justfile` -- append:

```just
# === Workflow Invocation ===

# Invoke a workflow (direct or API mode)
invoke workflow_id *args:
    uv run python scripts/invoke_workflow.py {{workflow_id}} {{args}}
```

### 2.10 Local Environment Seeding

**File**: `.env/local` -- append after existing exports:

```bash
###############################################################################
# Data Service (for workflow invocation and local dev)
###############################################################################

# Local data service URL (run autom8y-data separately)
export AUTOM8_DATA_URL="http://localhost:8001"

# AUTH_DEV_MODE bypasses JWT validation on both this service and autom8_data.
# DataServiceClient._get_token() returns None when AUTOM8_DATA_API_KEY is
# unset, which is fine under AUTH_DEV_MODE.
export AUTH_DEV_MODE="true"
```

---

## 3. Auth Strategy

### 3.1 Production Auth Flow

The invoke endpoint is a production API. When called by other services, the auth flow is:

```
Caller Service                     autom8_asana API                   autom8_data
     |                                    |                                |
     |-- POST /invoke                     |                                |
     |   Authorization: Bearer <JWT>      |                                |
     |                                    |                                |
     |                          get_auth_context()                         |
     |                          detect_token_type(token)                   |
     |                          -> JWT mode                                |
     |                          validate_service_token(token)              |
     |                          -> claims.service_name                     |
     |                          get_bot_pat() -> asana_pat                 |
     |                                    |                                |
     |                          DataServiceClient()                        |
     |                          _get_token()                               |
     |                          resolve_secret_from_env(AUTOM8_DATA_API_KEY)|
     |                          -> ASANA_SERVICE_KEY value                  |
     |                                    |-- GET /insights                |
     |                                    |   Authorization: Bearer <key>  |
     |                                    |<- 200 data                     |
     |                                    |                                |
     |<- 200 WorkflowInvokeResponse       |                                |
```

### 3.2 ASANA_SERVICE_KEY Configuration

The `ASANA_SERVICE_KEY` (`sk_prod_c5PNK7aViFlAulrMPB2m6XQAbmxP1JfV`) is the service key for authenticating with the data service in production.

**Current auth mechanism**: `DataServiceClient._get_token()` calls `resolve_secret_from_env(self._config.token_key)` where `token_key` defaults to `"AUTOM8_DATA_API_KEY"`. This resolves the environment variable (or Lambda extension ARN) to get the API key.

**Production configuration**: The ECS task definition must include `AUTOM8_DATA_API_KEY` pointing to the Secrets Manager entry containing the service key. This is infrastructure configuration, not application code. The DataServiceClient handles this transparently.

**JWT exchange path (future)**: If the auth service's `POST /internal/service-token` endpoint becomes available, the flow would be:

1. `ASANA_SERVICE_KEY` sent to auth service
2. Auth service returns a short-lived JWT
3. JWT used as Bearer token for data service calls

This is a **future enhancement**, not part of this TDD. The current direct API key mechanism works and is already deployed for the Lambda path. The invoke endpoint reuses the same `DataServiceClient` and therefore the same auth flow.

### 3.3 Local Development Auth

- `AUTH_DEV_MODE=true` bypasses JWT validation on both autom8_asana and autom8_data
- `DataServiceClient._get_token()` returns `None` when `AUTOM8_DATA_API_KEY` is unset, which is accepted under dev mode
- No `ASANA_SERVICE_KEY` needed locally

---

## 4. Data Models

### 4.1 EntityScope

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `entity_ids` | `tuple[str, ...]` | `()` | Asana GIDs to target |
| `section_filter` | `frozenset[str]` | `frozenset()` | Section names for filtered enumeration |
| `limit` | `int \| None` | `None` | Max entities to process |
| `dry_run` | `bool` | `False` | Skip write operations |

### 4.2 WorkflowInvokeRequest

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `entity_ids` | `list[str]` | Yes | Non-empty; max 100; each element must be numeric |
| `dry_run` | `bool` | No | Default: `False` |
| `params` | `dict[str, Any]` | No | Default: `{}` |

### 4.3 WorkflowInvokeResponse

| Field | Type | Description |
|-------|------|-------------|
| `request_id` | `str` | Correlation ID from request |
| `invocation_source` | `str` | Always `"api"` |
| `workflow_id` | `str` | ID of the invoked workflow |
| `dry_run` | `bool` | Whether this was a dry-run |
| `entity_count` | `int` | Number of entities processed |
| `result` | `dict[str, Any]` | Serialized `WorkflowResult.to_response_dict()` |

---

## 5. API Contract

### 5.1 POST /api/v1/workflows/{workflow_id}/invoke

**Auth**: `Authorization: Bearer <JWT|PAT>` (via `get_auth_context`)

**Rate Limit**: 10 requests/minute per client (separate from default 100/min)

**Timeout**: 120 seconds (covers insights-export 10-table fetch + composition)

**Path Parameters**:

| Param | Type | Description |
|-------|------|-------------|
| `workflow_id` | `str` | Registered workflow ID (e.g., `insights-export`) |

**Request Body**:

```json
{
    "entity_ids": ["1205925604226368"],
    "dry_run": true,
    "params": {}
}
```

**Success Response (200)**:

```json
{
    "request_id": "a1b2c3d4e5f67890",
    "invocation_source": "api",
    "workflow_id": "insights-export",
    "dry_run": true,
    "entity_count": 1,
    "result": {
        "status": "completed",
        "workflow_id": "insights-export",
        "total": 1,
        "succeeded": 1,
        "failed": 0,
        "skipped": 0,
        "duration_seconds": 12.34,
        "failure_rate": 0.0,
        "total_tables_succeeded": 10,
        "total_tables_failed": 0
    }
}
```

**Error Responses**:

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `VALIDATION_ERROR` | Empty `entity_ids`, non-numeric GID, or >100 items |
| 401 | `MISSING_AUTH` | No Authorization header |
| 404 | `WORKFLOW_NOT_FOUND` | Unknown `workflow_id` |
| 422 | `WORKFLOW_VALIDATION_FAILED` | Workflow pre-flight validation failed (feature flag disabled, circuit breaker open) |
| 429 | Rate limited | Exceeds 10/min |
| 504 | `WORKFLOW_TIMEOUT` | Execution exceeds 120s timeout |

Error responses follow the existing `raise_api_error` pattern from `api/errors.py`:
```json
{
    "error": "WORKFLOW_NOT_FOUND",
    "message": "Workflow 'nonexistent' is not registered for API invocation",
    "request_id": "a1b2c3d4e5f67890"
}
```

---

## 6. Sequence Diagrams

### 6.1 API Invocation (Happy Path)

```
Client                    FastAPI                    Workflow
  |                          |                          |
  |-- POST /invoke --------->|                          |
  |   {entity_ids, dry_run}  |                          |
  |                          |-- auth_context ----------|
  |                          |-- lookup config -------->|
  |                          |-- construct AsanaClient  |
  |                          |-- DataServiceClient ----->|
  |                          |   (async context mgr)    |
  |                          |-- workflow_factory() ---->|
  |                          |                          |-- validate_async()
  |                          |                          |<- [] (ok)
  |                          |                          |
  |                          |-- enumerate_async(scope)->|
  |                          |                          |-- scope.has_entity_ids?
  |                          |                          |   yes: return [{gid, ...}]
  |                          |<- entities               |
  |                          |                          |
  |                          |-- execute_async(entities, params) ->|
  |                          |                          |-- _process_offer(gid)
  |                          |                          |   (fetch data, compose)
  |                          |                          |   (dry_run? skip upload)
  |                          |                          |<- WorkflowResult
  |                          |<- result                 |
  |<- 200 WorkflowInvokeResp|                          |
```

### 6.2 Lambda Invocation (Full Enumeration)

```
EventBridge               Lambda Handler              Workflow
  |                          |                          |
  |-- event {} ------------->|                          |
  |   (no entity_ids)        |                          |
  |                          |-- EntityScope.from_event |
  |                          |   entity_ids=()          |
  |                          |   dry_run=False          |
  |                          |-- whitelist merge ------>|
  |                          |                          |
  |                          |-- validate_async() ----->|
  |                          |                          |<- [] (ok)
  |                          |                          |
  |                          |-- enumerate_async(scope)->|
  |                          |                          |-- scope.has_entity_ids?
  |                          |                          |   no: _enumerate_offers()
  |                          |                          |<- [all active offers]
  |                          |                          |
  |                          |-- execute_async(entities, params) ->|
  |                          |                          |-- (full batch as before)
  |                          |                          |<- WorkflowResult
  |<- 200 response ----------|                          |
```

### 6.3 Handler Factory Orchestration (Detailed)

```
_execute(event)
    |
    |--> EntityScope.from_event(event)
    |--> whitelist merge (existing params)
    |--> params.update(scope.to_params())  # dry_run
    |
    |--> AsanaClient(), DataServiceClient()
    |--> workflow = config.workflow_factory(client, data_client)
    |
    |--> workflow.validate_async()
    |    |-- check feature flag
    |    |-- check circuit breaker
    |    |-- return [] or ["error..."]
    |
    |--> workflow.enumerate_async(scope)
    |    |-- if scope.has_entity_ids:
    |    |     return [{gid: "123", name: None, ...}]
    |    |-- else:
    |    |     return _enumerate_offers()  # full project scan
    |
    |--> workflow.execute_async(entities, params)
    |    |-- for each entity in entities:
    |    |     _process_offer(gid, ..., dry_run=params["dry_run"])
    |    |-- return WorkflowResult
    |
    |--> emit metrics, return response
```

---

## 7. Error Handling

### 7.1 Invalid GID (Asana 404)

When a targeted GID does not exist in Asana, the workflow's `_resolve_offer` or `_resolve_office_phone` will hit an Asana 404. This is already handled by the per-item error boundary (`except Exception` in `_process_offer`/`_process_holder`). The entity is reported as `failed` in WorkflowResult with `error_type="unexpected"`.

No new error handling needed.

### 7.2 Wrong Entity Type

If a Business GID is passed to insights-export (which expects Offer GIDs), `_resolve_offer` returns `None`, and the entity is reported as `skipped` with `reason="no_resolution"`. Existing behavior, no change needed.

### 7.3 DataServiceClient Unavailable

The existing circuit breaker pattern in `validate_async` catches this. The API endpoint checks validation_errors and returns 422. The CLI prints the validation errors to stderr and exits 1.

### 7.4 Workflow Factory Not Registered

If `_WORKFLOW_CONFIGS` is empty (lifespan registration failed), the 404 response clearly communicates the workflow is not found. The structured log `workflow_configs_registered` during startup makes debugging straightforward.

### 7.5 Execution Timeout

The API endpoint wraps `enumerate_async` + `execute_async` in `asyncio.wait_for(timeout=120)`. If the workflow exceeds this, a 504 `WORKFLOW_TIMEOUT` error is returned. This protects against runaway workflows holding open HTTP connections.

### 7.6 Concurrent Invocations

Same GID invoked twice concurrently: both run independently. Workflows are idempotent (upload-first pattern ensures latest attachment wins). No locking required.

---

## 8. Test Strategy

### 8.1 Test Migration Plan (Clean Break)

The signature change to `execute_async` and the addition of `enumerate_async` require updating all existing tests that interact with `WorkflowAction` implementations.

#### 8.1.1 Files Requiring Migration

| Test File | Change Required |
|-----------|----------------|
| `tests/unit/automation/workflows/test_insights_export.py` | Update all `execute_async` calls to pass `(entities, params)` instead of `(params)`. Add `entities` fixtures. |
| `tests/unit/automation/workflows/test_conversation_audit.py` | Same pattern as insights_export. |
| `tests/unit/automation/workflows/test_pipeline_transition.py` | Same pattern. Also add `enumerate_async` stub. |
| `tests/unit/lambda_handlers/test_workflow_handler.py` | Update mock workflow to have both `enumerate_async` and `execute_async(entities, params)`. |
| `tests/unit/test_batch.py` | Update if it calls `execute_async` directly. |
| `tests/unit/test_batch_adversarial.py` | Same. |
| Any integration tests calling `execute_async` | Same pattern. |

#### 8.1.2 Migration Pattern

For each test that currently does:
```python
result = await workflow.execute_async(params)
```

Change to:
```python
entities = await workflow.enumerate_async(scope)
result = await workflow.execute_async(entities, params)
```

For tests that mock `execute_async`:
```python
# Before:
mock_workflow.execute_async = AsyncMock(return_value=mock_result)

# After:
mock_workflow.enumerate_async = AsyncMock(return_value=[{"gid": "123"}])
mock_workflow.execute_async = AsyncMock(return_value=mock_result)
```

Where `scope` is typically:
```python
from autom8_asana.core.scope import EntityScope

scope = EntityScope()  # Default: full enumeration
# or
scope = EntityScope(entity_ids=("123",), dry_run=True)  # Targeted
```

#### 8.1.3 Migration Order

1. Update `base.py` (ABC) -- this breaks compilation of all implementations
2. Update all three workflow implementations (`enumerate_async` + `execute_async` signature)
3. Update handler factory
4. Update all test files
5. Verify full test suite passes

This must be done in a single commit to maintain a green tree.

### 8.2 New Unit Tests -- EntityScope

**File**: `tests/unit/core/test_scope.py`

| Test | Description |
|------|-------------|
| `test_from_event_empty` | `EntityScope.from_event({})` returns defaults |
| `test_from_event_entity_ids` | `from_event({"entity_ids": ["123"]})` produces `entity_ids=("123",)` |
| `test_from_event_dry_run` | `from_event({"dry_run": True})` produces `dry_run=True` |
| `test_from_event_section_filter` | Accepts list, produces frozenset |
| `test_from_event_limit` | Integer passthrough |
| `test_from_event_unknown_keys_ignored` | Extra keys do not raise |
| `test_has_entity_ids_true` | Non-empty entity_ids returns True |
| `test_has_entity_ids_false` | Empty entity_ids returns False |
| `test_to_params_returns_dry_run` | `to_params()` produces `{"dry_run": ...}` |
| `test_frozen` | Assignment raises `FrozenInstanceError` |

### 8.3 New Unit Tests -- enumerate_async

**File**: `tests/unit/automation/workflows/test_insights_export.py` (extend)

| Test | Description |
|------|-------------|
| `test_enumerate_with_entity_ids_returns_synthetic_dicts` | Targeted scope returns `[{gid, name: None, parent_gid: None}]` |
| `test_enumerate_without_entity_ids_calls_enumerate_offers` | Full scope triggers `_enumerate_offers` |
| `test_enumerate_with_limit_truncates` | `scope.limit=2` with 5 offers returns 2 |
| `test_enumerate_targeted_does_not_call_enumerate_offers` | `_enumerate_offers` mock NOT called |

**File**: `tests/unit/automation/workflows/test_conversation_audit.py` (extend)

| Test | Description |
|------|-------------|
| `test_enumerate_with_entity_ids_skips_pre_resolution` | `_pre_resolve_business_activities` NOT called |
| `test_enumerate_without_entity_ids_calls_pre_resolution` | `_pre_resolve_business_activities` IS called |
| `test_enumerate_filters_inactive_businesses` | Only ACTIVE holders returned |

### 8.4 New Unit Tests -- Handler Factory

**File**: `tests/unit/lambda_handlers/test_workflow_handler.py` (extend)

| Test | Description |
|------|-------------|
| `test_handler_calls_enumerate_then_execute` | Mock workflow: `enumerate_async` called with `EntityScope`, then `execute_async` called with entities and params |
| `test_handler_passes_scope_to_enumerate` | Verify `EntityScope` fields match event |
| `test_handler_dry_run_in_params` | `dry_run=True` in event -> `params["dry_run"]` is True |
| `test_handler_empty_event_default_scope` | Empty event -> `EntityScope()` (full enumeration) |

### 8.5 New Unit Tests -- API Endpoint

**File**: `tests/unit/api/routes/test_workflows.py` (new file)

| Test | Description |
|------|-------------|
| `test_invoke_success` | Mock workflow returns result; 200 with expected shape |
| `test_invoke_unknown_workflow_404` | Unregistered workflow_id returns 404 |
| `test_invoke_empty_entity_ids_400` | `{"entity_ids": []}` returns 400 |
| `test_invoke_non_numeric_gid_400` | `{"entity_ids": ["abc"]}` returns 400 |
| `test_invoke_too_many_entity_ids_400` | `{"entity_ids": ["1"]*101}` returns 400 |
| `test_invoke_no_auth_401` | Missing Authorization header returns 401 |
| `test_invoke_validation_failed_422` | Workflow `validate_async` returns errors; 422 |
| `test_invoke_dry_run_flag_passed` | `dry_run=True` reaches workflow params |
| `test_invoke_params_override` | Custom params merge into workflow params |
| `test_invoke_response_shape` | Verify `request_id`, `workflow_id`, `dry_run`, `entity_count`, `result` fields |
| `test_invoke_audit_log_emitted` | Structured log contains `workflow_id`, `entity_ids`, `caller_service` |

### 8.6 New Unit Tests -- Dry-Run

**File**: `tests/unit/automation/workflows/test_insights_export.py` (extend)

| Test | Description |
|------|-------------|
| `test_dry_run_skips_upload` | `_attachments_client.upload_async` NOT called |
| `test_dry_run_skips_delete` | `_delete_old_attachments` NOT called |
| `test_dry_run_includes_report_preview` | `metadata["report_preview"]` present, max 2000 chars |
| `test_dry_run_metadata_flag` | `metadata["dry_run"]` is `True` |

**File**: `tests/unit/automation/workflows/test_conversation_audit.py` (extend)

| Test | Description |
|------|-------------|
| `test_dry_run_skips_csv_upload` | upload NOT called |
| `test_dry_run_metadata_csv_row_count` | `metadata["csv_row_count"]` present |

### 8.7 Integration Test Strategy

Integration tests require live Asana credentials and a running data service. Marked `@pytest.mark.integration`.

| Test | Description |
|------|-------------|
| `test_invoke_insights_export_single_offer` | Real GID, dry-run, verify result shape and `report_preview` |
| `test_invoke_conversation_audit_single_holder` | Real GID, dry-run, verify result shape and `csv_row_count` |

### 8.8 Test Count Estimate

- EntityScope: 10 tests
- enumerate_async (insights + conversation): 7 tests
- Handler factory: 4 tests
- API endpoint: 11 tests
- Dry-run: 6 tests
- **Total new tests: ~38**
- **Existing tests modified: ~30-40** (signature migration)

---

## 9. Migration / Rollout Plan

### 9.1 Implementation Order

This is a clean break. All changes must ship together.

1. **Create `core/scope.py`** with EntityScope
2. **Modify `base.py`** -- add `enumerate_async`, change `execute_async` signature
3. **Modify all three workflow implementations** -- extract enumeration into `enumerate_async`, adapt `execute_async`
4. **Modify handler factory** -- call `enumerate_async` then `execute_async`
5. **Create `api/routes/workflows.py`** -- production invoke endpoint
6. **Modify `api/lifespan.py`** -- register workflow configs
7. **Modify `api/routes/__init__.py` and `api/main.py`** -- router registration
8. **Create `scripts/invoke_workflow.py`** and justfile recipe
9. **Migrate all existing tests** -- signature updates
10. **Add new tests** -- EntityScope, enumerate_async, API endpoint, dry-run
11. **Update `.env/local`**

### 9.2 Deployment

1. **Merge PR** containing all components.
2. **Deploy to staging** -- existing EventBridge schedules run. Verify no regression.
3. **Smoke test API endpoint** on staging: `curl -X POST .../invoke` with a known test GID.
4. **Smoke test CLI** on developer machine: `just invoke insights-export --gid <test-gid> --dry-run`.
5. **Deploy to production** -- EventBridge schedules continue unchanged. API endpoint available immediately.

### 9.3 Rollback

If the deployment introduces issues:
- **EventBridge path**: The handler factory now calls `enumerate_async` before `execute_async`. This is a structural change. If rollback is needed, revert the entire PR. The clean break means there is no partial rollback.
- **API path**: The new endpoint is additive. Reverting removes it.

### 9.4 Feature Flags

No feature flag. The clean break is all-or-nothing.

---

## 10. Architecture Decision Records

### ADR-001: EntityScope Module Home -- `core/scope.py`

**Context**: EntityScope is consumed by three layers: the handler factory (`lambda_handlers/`), the API layer (`api/routes/`), and the CLI (`scripts/`). The original TDD placed it in `automation/workflows/scope.py`, adjacent to `base.py`.

**Decision**: Place EntityScope in `core/scope.py`.

**Alternatives considered**:
1. **`automation/workflows/scope.py`**: Adjacent to the ABC, but `core/` and `lambda_handlers/` would depend upward into `automation/`. This inverts the dependency direction: `core/` should not import from `automation/`.
2. **`api/models/scope.py`**: Too API-specific. Lambda handlers and CLI also need it.
3. **Top-level `scope.py`**: Too flat. The `core/` package already exists as the cross-cutting concern home.

**Rationale**:
- `core/` already holds cross-cutting primitives: `entity_types.py`, `creation.py`, `project_registry.py`, `logging.py`.
- EntityScope is a cross-cutting invocation concern, not a workflow-specific concern.
- Dependency direction is correct: `automation/workflows/base.py` imports from `core/`, not the reverse. The handler factory and API also import from `core/`.

**Consequences**:
- Import path: `from autom8_asana.core.scope import EntityScope`
- `automation/workflows/__init__.py` does NOT re-export EntityScope (it belongs to `core/`)
- Clean dependency direction: `core/` -> consumed by `automation/`, `lambda_handlers/`, `api/`

### ADR-002: Protocol-Level `enumerate_async` vs. Inline Checks

**Context**: The original TDD (ADR-001 v1) chose inline 4-line `if entity_ids:` checks in each workflow's `execute_async`. The stakeholder interview overrode this, requesting `enumerate_async(scope)` as an abstract method on the ABC.

**Decision**: Add `enumerate_async(self, scope: EntityScope) -> list[dict[str, Any]]` as an abstract method on `WorkflowAction`. Change `execute_async` signature to `(self, entities: list[dict], params: dict)`.

**Rationale**:
- **Separation of concerns**: Enumeration (what to process) is distinct from execution (how to process). Making this separation explicit in the protocol is cleaner than mixing both in `execute_async`.
- **Handler factory as orchestrator**: The handler factory calls `enumerate_async`, then passes the result to `execute_async`. This makes the workflow lifecycle explicit: validate -> enumerate -> execute.
- **Testability**: `enumerate_async` can be tested independently from `execute_async`. Tests can supply synthetic entity lists directly to `execute_async`.
- **Future workflows**: New WorkflowAction implementations must declare their enumeration strategy, preventing the pattern of "copy the 4-line check from another workflow and hope it's right."

**Consequences**:
- All three WorkflowAction implementations must be updated (clean break).
- All existing tests must be migrated (signature change).
- The handler factory grows slightly more complex (orchestration logic).
- `entity_ids` is no longer a flat key in params -- it travels via EntityScope -> enumerate_async, not through the params dict.

### ADR-003: WorkflowHandlerConfig Reuse for API (unchanged from v1)

**Context**: The API endpoint needs to construct workflows with per-request clients. The existing `WorkflowRegistry` stores constructed instances with shared clients.

**Decision**: Reuse `WorkflowHandlerConfig` objects from Lambda handlers in a module-level dict (`_WORKFLOW_CONFIGS`), registered during app lifespan startup.

**Rationale**: Same as original TDD. `WorkflowHandlerConfig` already encapsulates the factory callable, default params, and metadata keys.

**Consequences**: Same as original TDD.

### ADR-004: Production API Contract

**Context**: The original TDD treated the invoke endpoint as developer tooling. The stakeholder interview clarified it is a durable production API contract.

**Decision**: Implement production-grade features:
1. Timeout-aware execution (`asyncio.wait_for`, 120s)
2. Rate limiting (10/min per client via existing `limiter`)
3. Full audit logging (start + completion events with entity_ids, caller identity)
4. Error response contract aligned with existing `raise_api_error` pattern
5. API versioning via `/api/v1/` prefix (consistent with all existing routes)
6. Response envelope includes `workflow_id`, `dry_run`, `entity_count` metadata

**Rationale**:
- Other services may invoke this endpoint. It must be reliable, observable, and well-documented.
- The 120s timeout protects against runaway workflows holding HTTP connections.
- Rate limiting prevents abuse of a write-capable endpoint.
- Audit logging satisfies compliance requirements for "who invoked what, when, which entities."

**Consequences**:
- More error response variants (504 timeout in addition to 400/401/404/422/429).
- Completion audit log enables retrospective analysis.
- Rate limit may need tuning based on production usage patterns.

### ADR-005: Clean Break vs. Deprecation Bridge

**Context**: Changing the `execute_async` signature breaks all callers. The original TDD preserved the signature and transported EntityScope via the params dict.

**Decision**: Clean break. No deprecation bridge. All implementations and tests update simultaneously.

**Rationale**:
- There are only 3 implementations and ~30-40 test files. The blast radius is manageable.
- A deprecation bridge (supporting both old and new signatures) would add complexity for a transition period with no external consumers.
- The params dict transport was a workaround to avoid the signature change. With the stakeholder explicitly choosing the clean break, the workaround is unnecessary.
- Shipping the entire change in one PR ensures the tree stays green. There is no intermediate state where some callers use the old signature and others use the new one.

**Consequences**:
- All changes must be in a single PR.
- Implementation takes 1-2 extra days for test migration.
- No backward compatibility burden.
- Clean protocol: `enumerate_async` + `execute_async(entities, params)` is the final form.

---

## 11. File Change Summary

| File | Action | Description |
|------|--------|-------------|
| `src/autom8_asana/core/scope.py` | **CREATE** | EntityScope frozen dataclass |
| `src/autom8_asana/automation/workflows/base.py` | MODIFY | Add `enumerate_async` abstract method; change `execute_async` signature |
| `src/autom8_asana/automation/workflows/insights_export.py` | MODIFY | Extract `enumerate_async`; adapt `execute_async` signature; add dry-run gating |
| `src/autom8_asana/automation/workflows/conversation_audit.py` | MODIFY | Extract `enumerate_async`; adapt `execute_async` signature; add dry-run gating |
| `src/autom8_asana/automation/workflows/pipeline_transition.py` | MODIFY | Extract `enumerate_async`; adapt `execute_async` signature (no API wiring) |
| `src/autom8_asana/lambda_handlers/workflow_handler.py` | MODIFY | Call `enumerate_async` then `execute_async(entities, params)` |
| `src/autom8_asana/api/routes/workflows.py` | **CREATE** | Production invoke endpoint + workflow config registry |
| `src/autom8_asana/api/routes/__init__.py` | MODIFY | Import workflows_router |
| `src/autom8_asana/api/main.py` | MODIFY | Include workflows_router |
| `src/autom8_asana/api/lifespan.py` | MODIFY | Register workflow configs at startup |
| `scripts/invoke_workflow.py` | **CREATE** | Developer CLI |
| `justfile` | MODIFY | Add `invoke` recipe |
| `.env/local` | MODIFY | Add AUTOM8_DATA_URL and AUTH_DEV_MODE |
| `tests/unit/core/test_scope.py` | **CREATE** | EntityScope unit tests |
| `tests/unit/lambda_handlers/test_workflow_handler.py` | MODIFY | Handler factory tests (enumerate -> execute pattern) |
| `tests/unit/automation/workflows/test_insights_export.py` | MODIFY | enumerate_async + dry-run + signature migration |
| `tests/unit/automation/workflows/test_conversation_audit.py` | MODIFY | enumerate_async + dry-run + signature migration |
| `tests/unit/automation/workflows/test_pipeline_transition.py` | MODIFY | Signature migration |
| `tests/unit/api/routes/test_workflows.py` | **CREATE** | API endpoint tests |
| `tests/unit/test_batch.py` | MODIFY | Signature migration (if applicable) |
| `tests/unit/test_batch_adversarial.py` | MODIFY | Signature migration (if applicable) |

**New files**: 4 production, 2 test
**Modified files**: 14+ (including test migrations)

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Clean break introduces regressions in existing Lambda paths | Medium | High | All changes in single PR; full test suite must pass before merge; staging deployment validates EventBridge runs |
| Test migration misses a file | Low | Medium | Grep for `execute_async(params` (old signature) across entire test suite; CI catches compilation failures |
| enumerate_async extracts pre-filter logic incorrectly | Low | High | ConversationAudit pre-filter (business activity) is the most complex extraction. Dedicated tests for inactive business filtering in enumerate_async. |
| 120s API timeout too short for insights-export on slow data service | Low | Medium | Timeout is configurable (module constant). Monitor P99 latency of insights-export single-entity invocations. |
| Rate limit (10/min) too restrictive for batch API callers | Low | Low | Rate limit is per-client. Batch callers should use Lambda. Rate limit is configurable. |
| PipelineTransition enumerate_async correctness untested (deferred wiring) | Medium | Low | ABC method is implemented; no API wiring means no production traffic. Tests verify compilation only. |

---

## 13. Open Questions

None. The stakeholder interview resolved all ambiguities. The design is ready for implementation.

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD (this document) | `/Users/tomtenuta/Code/autom8y-asana/docs/design/TDD-entity-scope-invocation.md` | Yes |
| PRD (input) | `/Users/tomtenuta/Code/autom8y-asana/docs/requirements/PRD-entity-scope-invocation.md` | Yes |
| WorkflowAction ABC (reference) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/workflows/base.py` | Yes |
| Handler factory (reference) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/workflow_handler.py` | Yes |
| InsightsExportWorkflow (reference) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/workflows/insights_export.py` | Yes |
| ConversationAuditWorkflow (reference) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/workflows/conversation_audit.py` | Yes |
| PipelineTransitionWorkflow (reference) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/workflows/pipeline_transition.py` | Yes |
| API dependencies (reference) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/dependencies.py` | Yes |
| API errors (reference) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/errors.py` | Yes |
| Admin routes (pattern reference) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/admin.py` | Yes |
| DataServiceClient config (reference) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/config.py` | Yes |
| Lifespan (reference) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/lifespan.py` | Yes |
