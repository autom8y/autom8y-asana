"""Base classes for batch automation workflows.

Per TDD-CONV-AUDIT-001 Section 3.1: WorkflowAction protocol, WorkflowResult,
and WorkflowItemError dataclasses for generalized batch workflow dispatch.

Per TDD-ENTITY-SCOPE-001 Section 2.2: WorkflowAction ABC extended with
enumerate_async(scope) and updated execute_async(entities, params) signature.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from autom8_asana.core.scope import EntityScope


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

    def to_response_dict(
        self,
        extra_metadata_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """Serialize to a Lambda response body dict.

        Args:
            extra_metadata_keys: Additional keys to pull from ``self.metadata``
                into the top-level response dict.  Missing keys default to ``0``.

        Returns:
            Dict suitable for ``json.dumps`` in a Lambda response body.
        """
        d: dict[str, Any] = {
            "status": "completed",
            "workflow_id": self.workflow_id,
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "skipped": self.skipped,
            "duration_seconds": round(self.duration_seconds, 2),
            "failure_rate": round(self.failure_rate, 4),
        }
        for key in extra_metadata_keys or []:
            d[key] = self.metadata.get(key, 0)
        return d


class WorkflowAction(ABC):
    """Protocol for batch automation workflows.

    Each workflow owns its full lifecycle:
    1. Enumerate targets via enumerate_async(scope)
    2. Process the entity list via execute_async(entities, params)
    3. Report results (structured WorkflowResult)

    Implementations must be idempotent: re-running the same workflow
    should produce the same end state.

    Per PRD Section 4.1: WorkflowAction is the generalized batch primitive.
    Per TDD-ENTITY-SCOPE-001 Section 2.2: Protocol-level enumeration.
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
            Examples: missing config, unreachable upstream, invalid credentials.
        """
        ...
