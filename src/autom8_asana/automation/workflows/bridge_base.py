"""Intermediate base class for Data Attachment Bridge workflows.

Per ADR-bridge-intermediate-base-class: Absorbs constructor wiring,
validate_async() boilerplate, enumerate_async() scope handling, and
execute_async() semaphore fan-out with per-entity isolation.

File: src/autom8_asana/automation/workflows/bridge_base.py
"""

from __future__ import annotations

import asyncio
import os
from abc import abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.automation.workflows.base import (
    WorkflowAction,
    WorkflowItemError,
    WorkflowResult,
)
from autom8_asana.automation.workflows.mixins import AttachmentReplacementMixin

if TYPE_CHECKING:
    # H-003: Protocol alignment with autom8y-client-sdk.
    # DataInsightProtocol overlaps with DataSource on the insight-fetch
    # subset, but DataSource is deliberately minimal (health-check only).
    # DataServiceClient structurally satisfies DataSource and partially
    # satisfies DataInsightProtocol (via get_insights_async which maps
    # to get_insight). Full migration blocked: interop covers ~30% of
    # DataServiceClient surface. See protocols.py module docstring for
    # the complete coverage map.
    from autom8y_client_sdk.data import (
        DataInsightProtocol as _DataInsightProtocol,  # noqa: F401
    )

    from autom8_asana.automation.workflows.protocols import DataSource
    from autom8_asana.core.scope import EntityScope

logger = get_logger(__name__)


@dataclass
class BridgeOutcome:
    """Base outcome for a single entity processed by a bridge.

    Concrete bridges may subclass this to add domain-specific fields
    (e.g., table counts, CSV row counts).

    Attributes:
        gid: Entity GID that was processed.
        status: Processing result -- "succeeded", "failed", or "skipped".
        reason: Reason for skip (set when status == "skipped").
        error: Error detail (set when status == "failed").
    """

    gid: str
    status: str  # "succeeded" | "failed" | "skipped"
    reason: str | None = None
    error: WorkflowItemError | None = None


class BridgeWorkflowAction(AttachmentReplacementMixin, WorkflowAction):
    """Intermediate base class for all Data Attachment Bridge workflows.

    Absorbs:
    - Constructor wiring (asana_client, data_client, attachments_client)
    - validate_async() boilerplate (kill-switch check + data source
      health check via DataSource.is_healthy())
    - enumerate_async() scope fast-path and limit truncation
    - execute_async() semaphore fan-out and WorkflowResult aggregation

    Subclasses must implement:
    - workflow_id (property, str)
    - feature_flag_env_var (class attribute, str)
    - enumerate_entities(scope) -> list[dict]
    - process_entity(entity, params) -> BridgeOutcome

    Subclasses may override:
    - default_max_concurrency (class attribute, int, default 5)
    - _build_result_metadata(outcomes) -> dict
    - enumerate_async(scope) -- for bridge-specific enumeration behavior
    - execute_async(entities, params) -- for bridge-specific logging

    Per ADR-bridge-intermediate-base-class.
    Per TDD-data-attachment-bridge-platform Section 4.
    """

    # --- Class attributes (set by subclasses) ---
    feature_flag_env_var: str  # e.g., "AUTOM8_EXPORT_ENABLED"
    default_max_concurrency: int = 5

    # --- Constructor ---
    def __init__(
        self,
        asana_client: Any,
        data_client: DataSource | None,
        attachments_client: Any,
    ) -> None:
        """Initialize bridge with required clients.

        Args:
            asana_client: AsanaClient for Asana API operations.
            data_client: DataSource (typically DataServiceClient) for
                satellite data fetching, or None if the bridge does
                not require a data source.
            attachments_client: AttachmentsClient for upload/delete.

        Subclasses should call super().__init__() first, then
        initialize their per-run caches.
        """
        self._asana_client = asana_client
        self._data_client = data_client
        self._attachments_client = attachments_client

    # --- validate_async() ---
    async def validate_async(self) -> list[str]:
        """Pre-flight validation: kill-switch + data source health.

        Checks:
        1. Feature flag env var is not disabled (false/0/no).
        2. Data source is healthy (if _data_client is not None).

        Returns:
            List of validation error strings (empty = ready).

        Per ADR-bridge-validate-extraction.
        """
        errors: list[str] = []

        # (1) Kill-switch check
        env_value = os.environ.get(self.feature_flag_env_var, "").lower()
        if env_value in {"false", "0", "no"}:
            errors.append(
                f"Workflow disabled via {self.feature_flag_env_var}={env_value}"
            )
            return errors  # Short-circuit

        # (2) Data source health check
        if self._data_client is not None:
            try:
                from autom8y_http import (
                    CircuitBreakerOpenError as SdkCBOpen,
                )

                await self._data_client.is_healthy()
            except SdkCBOpen:
                errors.append(
                    "DataServiceClient circuit breaker is open. "
                    "autom8_data may be degraded."
                )
            except (ConnectionError, TimeoutError, OSError):
                pass  # Non-circuit-breaker errors are not pre-flight failures

        return errors

    # --- enumerate_async() ---
    async def enumerate_async(
        self,
        scope: EntityScope,
    ) -> list[dict[str, Any]]:
        """Enumerate entities based on scope.

        Fast-path: When scope.has_entity_ids is True, returns synthetic
        entity dicts for the targeted GIDs without full enumeration.

        Full-path: Delegates to abstract enumerate_entities(), then
        applies scope.limit truncation.

        Subclasses may override for bridge-specific behavior (e.g.,
        additional logging in the fast-path, custom dict shapes).

        Args:
            scope: EntityScope controlling targeting and limits.

        Returns:
            List of entity dicts with at minimum {gid, name} shape.
        """
        if scope.has_entity_ids:
            return [{"gid": gid, "name": None} for gid in scope.entity_ids]

        entities = await self.enumerate_entities(scope)

        if scope.limit is not None and len(entities) > scope.limit:
            entities = entities[: scope.limit]

        return entities

    # --- execute_async() ---
    # H-006 gap: trace_computation decorator is NOT available in
    # autom8y-telemetry 0.6.1 (referenced in pyproject.toml comment
    # "glass-S9: 0.6.0+ required" but not present in installed SDK).
    # Once trace_computation is published, apply it here:
    #   @trace_computation("bridge.execute", engine="autom8y-asana")
    # See SCOUT Section 1.4 for the expected decorator signature.
    async def execute_async(
        self,
        entities: list[dict[str, Any]],
        params: dict[str, Any],
    ) -> WorkflowResult:
        """Execute bridge workflow with semaphore-bounded fan-out.

        For each entity, calls process_entity() with per-entity
        broad-catch isolation. Aggregates outcomes into WorkflowResult.

        Args:
            entities: Entity dicts from enumerate_async.
            params: Configuration parameters (max_concurrency,
                attachment_pattern, dry_run, etc.)

        Returns:
            WorkflowResult with total/succeeded/failed/skipped counts.
        """
        started_at = datetime.now(UTC)

        max_concurrency = params.get("max_concurrency", self.default_max_concurrency)
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _run_one(entity: dict[str, Any]) -> BridgeOutcome:
            async with semaphore:
                try:
                    return await self.process_entity(entity, params)
                except (
                    Exception
                ) as exc:  # BROAD-CATCH: boundary -- per-entity isolation
                    return BridgeOutcome(
                        gid=entity.get("gid", "unknown"),
                        status="failed",
                        reason=None,
                        error=WorkflowItemError(
                            item_id=entity.get("gid", "unknown"),
                            error_type="unexpected_error",
                            message=str(exc),
                            recoverable=True,
                        ),
                    )

        outcomes: list[BridgeOutcome] = list(
            await asyncio.gather(*[_run_one(e) for e in entities])
        )

        succeeded = sum(1 for o in outcomes if o.status == "succeeded")
        failed = sum(1 for o in outcomes if o.status == "failed")
        skipped = sum(1 for o in outcomes if o.status == "skipped")
        errors = [o.error for o in outcomes if o.error is not None]

        return WorkflowResult(
            workflow_id=self.workflow_id,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            total=len(entities),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            errors=errors,
            metadata=self._build_result_metadata(outcomes),
        )

    # --- Abstract methods ---
    @abstractmethod
    async def enumerate_entities(
        self,
        scope: EntityScope,
    ) -> list[dict[str, Any]]:
        """Full enumeration path (no scope.has_entity_ids fast-path).

        Called only when scope.has_entity_ids is False. The base class
        enumerate_async() handles the fast-path and limit truncation.

        Args:
            scope: EntityScope (entity_ids will be empty).

        Returns:
            List of entity dicts for processing.
        """
        ...

    @abstractmethod
    async def process_entity(
        self,
        entity: dict[str, Any],
        params: dict[str, Any],
    ) -> BridgeOutcome:
        """Process a single entity: resolve, fetch, format, upload, cleanup.

        Called by execute_async() within a Semaphore-bounded context.
        Per-entity exceptions are caught by the base class broad-catch;
        implementations may also have their own internal error handling.

        Args:
            entity: Entity dict from enumerate_async (at minimum {gid}).
            params: Full params dict from execute_async.

        Returns:
            BridgeOutcome (or subclass) with processing result.
        """
        ...

    def _build_result_metadata(
        self,
        outcomes: list[BridgeOutcome],
    ) -> dict[str, Any]:
        """Build bridge-specific metadata for WorkflowResult.

        Override to add domain-specific metadata keys (e.g., table
        counts, truncation counts, preview paths).

        Args:
            outcomes: All BridgeOutcome instances from this run.

        Returns:
            Metadata dict to include in WorkflowResult.metadata.
        """
        return {}
