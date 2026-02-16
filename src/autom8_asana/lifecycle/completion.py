"""Explicit per-transition auto-completion service.

Per TDD-lifecycle-engine-hardening Section 2.6:
- Rewritten to use explicit per-transition auto_complete_prior flag
- Eliminates stage-number comparison (_get_pipeline_stage removed)
- Auto-completion is config-driven, not derived from stage ordering

FR Coverage: FR-COMPLETE-001

Error Contract:
- Completion failure is logged as warning and skipped (fail-forward)
- Already-completed processes are silently skipped (idempotent)

Design Decision:
- The engine checks transition.auto_complete_prior before calling this service
- This service only marks the source process as complete
- No stage-number comparison or process scanning logic
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.process import Process

logger = get_logger(__name__)


@dataclass
class CompletionResult:
    """Result of auto-completion.

    Attributes:
        completed: GIDs of processes marked as complete.
    """

    completed: list[str] = field(default_factory=list)


class CompletionService:
    """Handles explicit per-transition auto-completion.

    Per FR-COMPLETE-001: Auto-completion is controlled by the
    auto_complete_prior flag on each transition in YAML config,
    not derived from stage number comparison.

    The engine is responsible for checking the flag before calling
    this service. This service simply marks the source process
    as complete via the Asana API.
    """

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def complete_source_async(self, source_process: Process) -> CompletionResult:
        """Mark the source process as complete.

        Only called when transition config has auto_complete_prior=true.
        Idempotent: if the process is already completed, returns
        immediately with an empty result.

        Args:
            source_process: The process being transitioned.

        Returns:
            CompletionResult with the completed process GID, or empty
            if already completed or on failure.
        """
        result = CompletionResult()

        if source_process.completed:
            return result

        try:
            await self._client.tasks.update_async(source_process.gid, completed=True)
            result.completed.append(source_process.gid)
            logger.info(
                "lifecycle_auto_completed",
                process_gid=source_process.gid,
                process_name=source_process.name,
            )
        except (
            Exception
        ) as e:  # BROAD-CATCH: boundary -- auto-complete failure is non-fatal
            logger.warning(
                "lifecycle_auto_complete_failed",
                process_gid=source_process.gid,
                error=str(e),
            )

        return result


# Backward compatibility alias for engine.py which imports
# PipelineAutoCompletionService. This alias will be removed
# when engine.py is rewritten to use CompletionService directly.
class PipelineAutoCompletionService:
    """Deprecated: Use CompletionService instead.

    Backward-compatible wrapper that preserves the old API signature
    used by engine.py. The auto_complete_async method delegates to
    CompletionService.complete_source_async, ignoring the stage
    number parameter (which is no longer used for auto-completion
    decisions per FR-COMPLETE-001).
    """

    def __init__(self, client: AsanaClient) -> None:
        self._service = CompletionService(client)
        self._client = client

    async def auto_complete_async(
        self,
        source_process: Process,
        new_pipeline_stage: int,
        ctx: Any = None,
    ) -> CompletionResult:
        """Backward-compatible auto-completion.

        Delegates to CompletionService.complete_source_async.
        The new_pipeline_stage and ctx parameters are ignored
        (retained only for API compatibility with engine.py).

        Args:
            source_process: Process being transitioned.
            new_pipeline_stage: Ignored (legacy parameter).
            ctx: Ignored (legacy parameter).

        Returns:
            CompletionResult with completed process GIDs.
        """
        return await self._service.complete_source_async(source_process)
