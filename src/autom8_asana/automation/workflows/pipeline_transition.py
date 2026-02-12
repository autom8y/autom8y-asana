"""Pipeline Transition Workflow.

Per TDD-lifecycle-engine Phase 2: Batch-process pipeline transitions by
enumerating processes in terminal sections (CONVERTED / DID NOT CONVERT)
and routing them through the LifecycleEngine.

This is Workflow #2 on the platform (Workflow #1 is ConversationAuditWorkflow).

Workflow steps:
1. Enumerate process tasks in CONVERTED/DID NOT CONVERT sections
2. For each process, determine the outcome (converted/did_not_convert)
3. Route to LifecycleEngine.handle_transition_async()
4. Return WorkflowResult with per-item tracking

Parameters:
- pipeline_project_gids: List[str] - Project GIDs to scan (default: all configured)
- max_concurrency: int - Concurrent processing limit (default: 3)
- converted_section: str - Section name for CONVERTED (default: "CONVERTED")
- dnc_section: str - Section name for DID NOT CONVERT (default: "DID NOT CONVERT")

Usage:
    config = LifecycleConfig(Path("config/lifecycle_stages.yaml"))
    workflow = PipelineTransitionWorkflow(client, config)
    result = await workflow.execute_async({
        "pipeline_project_gids": ["1200944186565610"],
        "max_concurrency": 3,
    })
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.automation.workflows.base import (
    WorkflowAction,
    WorkflowItemError,
    WorkflowResult,
)
from autom8_asana.core.project_registry import all_pipeline_project_gids
from autom8_asana.models.business.process import Process, ProcessSection

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.lifecycle.config import LifecycleConfig
    from autom8_asana.lifecycle.engine import LifecycleEngine

logger = get_logger(__name__)

# Default configuration
DEFAULT_MAX_CONCURRENCY = 3
DEFAULT_CONVERTED_SECTION = "CONVERTED"
DEFAULT_DNC_SECTION = "DID NOT CONVERT"

# All pipeline project GIDs from central registry (source of truth)
DEFAULT_PIPELINE_PROJECTS = all_pipeline_project_gids()


class PipelineTransitionWorkflow(WorkflowAction):
    """Batch-process pipeline transitions (CONVERTED / DID NOT CONVERT).

    This workflow enumerates process tasks that have moved to terminal sections
    and routes them through the LifecycleEngine for transition handling.

    The workflow is idempotent: re-running will re-process tasks still in
    terminal sections (which is safe due to duplicate detection in the engine).

    Error isolation: Each process is handled independently. One failure does
    not prevent processing of other processes.
    """

    def __init__(
        self,
        client: AsanaClient,
        config: LifecycleConfig,
    ) -> None:
        self._client = client
        self._config = config
        self._engine: LifecycleEngine | None = None

    @property
    def workflow_id(self) -> str:
        """Workflow identifier."""
        return "pipeline-transition"

    async def validate_async(self) -> list[str]:
        """Pre-flight validation.

        Returns:
            List of validation errors (empty = ready to execute).
        """
        errors: list[str] = []

        # Validate lifecycle config is loaded
        if not self._config:
            errors.append("LifecycleConfig not provided")

        # Validate at least one stage is configured
        try:
            sales_stage = self._config.get_stage("sales")
            if not sales_stage:
                errors.append("No 'sales' stage in lifecycle config")
        except Exception as e:
            errors.append(f"Config validation error: {e}")

        return errors

    async def execute_async(
        self,
        params: dict[str, Any],
    ) -> WorkflowResult:
        """Execute the full workflow cycle.

        Args:
            params: Configuration parameters:
                - pipeline_project_gids: List of project GIDs to scan
                - max_concurrency: Concurrent processing limit
                - converted_section: Section name for CONVERTED
                - dnc_section: Section name for DID NOT CONVERT

        Returns:
            WorkflowResult with per-item success/failure tracking.
        """
        started_at = datetime.now(timezone.utc)
        errors: list[WorkflowItemError] = []

        # Extract parameters
        project_gids = params.get(
            "pipeline_project_gids", DEFAULT_PIPELINE_PROJECTS
        )
        max_concurrency = params.get("max_concurrency", DEFAULT_MAX_CONCURRENCY)
        converted_section = params.get(
            "converted_section", DEFAULT_CONVERTED_SECTION
        )
        dnc_section = params.get("dnc_section", DEFAULT_DNC_SECTION)

        # Initialize engine
        from autom8_asana.lifecycle.engine import LifecycleEngine

        self._engine = LifecycleEngine(self._client, self._config)

        # Phase 1: Enumerate processes in terminal sections
        processes_to_transition = await self._enumerate_processes_async(
            project_gids, converted_section, dnc_section
        )

        total = len(processes_to_transition)
        logger.info(
            "pipeline_transition_workflow_started",
            total_processes=total,
            projects=len(project_gids),
        )

        # Phase 2: Process transitions with concurrency control
        succeeded = 0
        failed = 0
        skipped = 0

        semaphore = asyncio.Semaphore(max_concurrency)

        async def process_one(
            process: Process, outcome: str
        ) -> tuple[bool, WorkflowItemError | None]:
            """Process a single transition."""
            async with semaphore:
                return await self._process_transition_async(process, outcome)

        # Create tasks for all transitions
        tasks = [
            process_one(process, outcome)
            for process, outcome in processes_to_transition
        ]

        # Execute with error isolation
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        for result in results:
            if isinstance(result, Exception):
                failed += 1
                errors.append(
                    WorkflowItemError(
                        item_id="unknown",
                        error_type="workflow_exception",
                        message=str(result),
                        recoverable=True,
                    )
                )
            elif isinstance(result, tuple):
                success, error = result
                if success:
                    succeeded += 1
                elif error:
                    failed += 1
                    errors.append(error)
                else:
                    skipped += 1

        completed_at = datetime.now(timezone.utc)

        logger.info(
            "pipeline_transition_workflow_completed",
            total=total,
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            duration_seconds=(completed_at - started_at).total_seconds(),
        )

        return WorkflowResult(
            workflow_id=self.workflow_id,
            started_at=started_at,
            completed_at=completed_at,
            total=total,
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            errors=errors,
            metadata={
                "projects_scanned": len(project_gids),
                "converted_section": converted_section,
                "dnc_section": dnc_section,
            },
        )

    async def _enumerate_processes_async(
        self,
        project_gids: list[str],
        converted_section: str,
        dnc_section: str,
    ) -> list[tuple[Process, str]]:
        """Enumerate processes in terminal sections.

        Args:
            project_gids: Projects to scan.
            converted_section: Section name for CONVERTED.
            dnc_section: Section name for DID NOT CONVERT.

        Returns:
            List of (Process, outcome) tuples.
        """
        processes: list[tuple[Process, str]] = []

        for project_gid in project_gids:
            try:
                # List incomplete tasks in this project
                page_iter = self._client.tasks.list_for_project_async(
                    project_gid,
                    opt_fields=[
                        "name",
                        "completed",
                        "memberships",
                        "memberships.section",
                        "memberships.section.name",
                    ],
                    completed_since="now",
                )
                tasks = await page_iter.collect()

                # Filter to tasks in terminal sections
                for task in tasks:
                    if task.completed:
                        continue

                    # Check section membership
                    memberships = getattr(task, "memberships", []) or []
                    for membership in memberships:
                        section = membership.get("section", {})
                        section_name = section.get("name", "")

                        if section_name.upper() == converted_section.upper():
                            # Create Process instance
                            process = Process.model_validate(task)
                            processes.append((process, "converted"))
                            break

                        elif section_name.upper() == dnc_section.upper():
                            # Create Process instance
                            process = Process.model_validate(task)
                            processes.append((process, "did_not_convert"))
                            break

            except Exception as e:
                logger.error(
                    "pipeline_transition_enumerate_error",
                    project_gid=project_gid,
                    error=str(e),
                )

        return processes

    async def _process_transition_async(
        self,
        process: Process,
        outcome: str,
    ) -> tuple[bool, WorkflowItemError | None]:
        """Process a single transition.

        Args:
            process: Process to transition.
            outcome: "converted" or "did_not_convert".

        Returns:
            (success, error) tuple.
        """
        try:
            result = await self._engine.handle_transition_async(process, outcome)

            if result.success:
                logger.info(
                    "pipeline_transition_success",
                    process_gid=process.gid,
                    outcome=outcome,
                    entities_created=len(result.entities_created),
                    entities_updated=len(result.entities_updated),
                )
                return (True, None)
            else:
                logger.warning(
                    "pipeline_transition_failed",
                    process_gid=process.gid,
                    outcome=outcome,
                    error=result.error,
                )
                return (
                    False,
                    WorkflowItemError(
                        item_id=process.gid,
                        error_type="transition_failed",
                        message=result.error or "Unknown error",
                        recoverable=True,
                    ),
                )

        except Exception as e:
            logger.error(
                "pipeline_transition_exception",
                process_gid=process.gid,
                outcome=outcome,
                error=str(e),
            )
            return (
                False,
                WorkflowItemError(
                    item_id=process.gid,
                    error_type="exception",
                    message=str(e),
                    recoverable=True,
                ),
            )
