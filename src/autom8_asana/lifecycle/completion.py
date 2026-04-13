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
from typing import TYPE_CHECKING

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
        except Exception as e:  # BROAD-CATCH: boundary -- auto-complete failure is non-fatal
            logger.warning(
                "lifecycle_auto_complete_failed",
                process_gid=source_process.gid,
                error=str(e),
            )

        return result
