"""DNC reopen mechanics for lifecycle transitions.

Per TDD-lifecycle-engine-hardening Section 2.8:
- When Onboarding DNC fires, find and reopen existing Sales process
- Search ProcessHolder subtasks for most recent matching ProcessType
- Mark incomplete and move to target section (OPPORTUNITY)

FR Coverage: FR-DNC-002, FR-REOPEN-001

Error Contract:
- Returns ReopenResult(success=False) on all failure paths
- Top-level except Exception as boundary guard (fail-forward)
- No exceptions propagated to caller
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.lifecycle.config import StageConfig
    from autom8_asana.models.business.process import Process
    from autom8_asana.resolution.context import ResolutionContext

logger = get_logger(__name__)


@dataclass
class ReopenResult:
    """Result of DNC reopen operation.

    Local dataclass matching engine.ReopenResult by structural typing.
    Avoids circular import (engine imports from reopen).
    """

    success: bool
    entity_gid: str = ""
    error: str = ""


class ReopenService:
    """Handles DNC reopen mechanics.

    When Onboarding DNC fires, instead of creating a new process,
    the engine finds the most recent Sales process under the
    ProcessHolder, marks it incomplete, and moves it to the
    Opportunity section in the Sales project.
    """

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def reopen_async(
        self,
        target_stage: StageConfig,
        ctx: ResolutionContext,
        source_process: Process,
    ) -> ReopenResult:
        """Find and reopen the most recent process of the target type.

        Steps:
          1. Resolve ProcessHolder from source_process or ctx fallback
          2. List ProcessHolder subtasks
          3. Filter candidates matching target ProcessType
          4. Sort by created_at descending, pick most recent
          5. Mark incomplete (completed=False)
          6. Move to target section in target project

        Args:
            target_stage: The stage to reopen into (e.g., sales).
            ctx: Resolution context for holder lookup.
            source_process: The process that triggered the DNC.

        Returns:
            ReopenResult with success status and reopened entity GID.
        """
        try:
            # 1. Get ProcessHolder
            holder = getattr(source_process, "process_holder", None)
            if holder is None:
                from autom8_asana.models.business.process import ProcessHolder

                holder = await ctx.resolve_holder_async(ProcessHolder)

            if holder is None:
                return ReopenResult(
                    success=False,
                    error="Cannot resolve ProcessHolder for reopen",
                )

            # 2. List ProcessHolder subtasks
            subtasks_result = self._client.tasks.subtasks_async(
                holder.gid,
                opt_fields=[
                    "name",
                    "completed",
                    "created_at",
                    "custom_fields",
                    "custom_fields.name",
                    "custom_fields.display_value",
                ],
            )
            subtasks = await subtasks_result.collect()

            # 3. Find candidates matching target ProcessType
            candidates = []
            for task in subtasks:
                if self._matches_process_type(task, target_stage.name):
                    candidates.append(task)

            if not candidates:
                return ReopenResult(
                    success=False,
                    error=f"No {target_stage.name} process found to reopen",
                )

            # 4. Sort by created_at descending, pick most recent
            candidates.sort(
                key=lambda t: getattr(t, "created_at", "") or "",
                reverse=True,
            )
            target_process = candidates[0]

            # 5. Mark incomplete
            await self._client.tasks.update_async(
                target_process.gid,
                completed=False,
            )

            # 6. Move to target section
            if target_stage.project_gid:
                await self._move_to_section_async(
                    target_process.gid,
                    target_stage.project_gid,
                    target_stage.target_section or "OPPORTUNITY",
                )

            logger.info(
                "lifecycle_process_reopened",
                process_gid=target_process.gid,
                target_stage=target_stage.name,
            )

            return ReopenResult(
                success=True,
                entity_gid=target_process.gid,
            )

        except Exception as e:  # BROAD-CATCH: boundary guard for reopen flow
            logger.error(
                "lifecycle_reopen_error",
                target_stage=target_stage.name,
                error=str(e),
            )
            return ReopenResult(success=False, error=str(e))

    async def _move_to_section_async(
        self,
        task_gid: str,
        project_gid: str,
        section_name: str,
    ) -> None:
        """Move a task to a named section in the target project.

        Looks up sections by name (case-insensitive). If the target
        section is not found, this is a no-op (graceful degradation).

        Args:
            task_gid: GID of the task to move.
            project_gid: GID of the project containing the section.
            section_name: Name of the target section (e.g., "OPPORTUNITY").
        """
        sections_result = self._client.sections.list_for_project_async(
            project_gid,
        )
        sections = await sections_result.collect()
        target = next(
            (s for s in sections if s.name and s.name.lower() == section_name.lower()),
            None,
        )
        if target:
            await self._client.sections.add_task_async(
                target.gid,
                task=task_gid,
            )

    @staticmethod
    def _matches_process_type(task: Any, stage_name: str) -> bool:
        """Check if a task's ProcessType custom field matches the stage name.

        Handles both dict-style and object-style custom fields.
        Comparison is case-insensitive.

        Args:
            task: An Asana task (or mock) with custom_fields attribute.
            stage_name: The stage name to match (e.g., "sales").

        Returns:
            True if the task's ProcessType matches the stage name.
        """
        cfs = getattr(task, "custom_fields", None) or []
        for cf in cfs:
            name = (
                cf.get("name", "") if isinstance(cf, dict) else getattr(cf, "name", "")
            )
            if name.lower() in ("process type", "processtype"):
                display = (
                    cf.get("display_value", "")
                    if isinstance(cf, dict)
                    else getattr(cf, "display_value", "")
                )
                if display and display.lower() == stage_name.lower():
                    return True
        return False
