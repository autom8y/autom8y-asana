"""Subtask waiter utility for polling-based subtask readiness detection.

Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT and ADR-0111: Provides polling-based wait
for subtask availability after task duplication.

After duplicating a task with subtasks, Asana creates the subtasks asynchronously.
This utility polls until the expected subtask count is reached or timeout expires.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

logger = logging.getLogger(__name__)


class SubtaskWaiter:
    """Utility for waiting on asynchronous subtask creation.

    Per FR-WAIT-001: Provides polling-based wait for subtask availability.
    Per ADR-0111: Chosen over fixed delay or webhooks.

    After duplicating a task with subtasks, Asana creates the subtasks
    asynchronously. This utility polls until the expected subtask count
    is reached or timeout expires.

    Example:
        waiter = SubtaskWaiter(client)

        # Get expected count from template before duplication
        template_subtasks = await client.tasks.subtasks_async(template_gid).collect()
        expected_count = len(template_subtasks)

        # Duplicate and wait
        new_task = await client.tasks.duplicate_async(template_gid, name="New Task")
        ready = await waiter.wait_for_subtasks_async(
            new_task.gid,
            expected_count=expected_count,
            timeout=2.0,
        )
        if not ready:
            logger.warning("Subtask creation timed out, proceeding anyway")
    """

    def __init__(
        self,
        client: AsanaClient,
        *,
        default_timeout: float = 2.0,
        default_poll_interval: float = 0.2,
    ) -> None:
        """Initialize SubtaskWaiter.

        Args:
            client: AsanaClient for API operations.
            default_timeout: Default timeout in seconds (FR-WAIT-003).
            default_poll_interval: Default poll interval in seconds (FR-WAIT-004).
        """
        self._client = client
        self._default_timeout = default_timeout
        self._default_poll_interval = default_poll_interval

    async def wait_for_subtasks_async(
        self,
        task_gid: str,
        expected_count: int,
        *,
        timeout: float | None = None,
        poll_interval: float | None = None,
    ) -> bool:
        """Wait for subtask count to reach expected value.

        Per FR-WAIT-002: Polls until count matches or timeout.

        Args:
            task_gid: GID of the parent task.
            expected_count: Number of subtasks to wait for.
            timeout: Timeout in seconds (default: 2.0).
            poll_interval: Poll interval in seconds (default: 0.2).

        Returns:
            True if expected count reached, False if timeout.

        Side Effects:
            Logs warning on timeout with current vs expected count.
        """
        effective_timeout = timeout if timeout is not None else self._default_timeout
        effective_interval = (
            poll_interval if poll_interval is not None else self._default_poll_interval
        )

        start_time = time.monotonic()
        current_count = 0

        while (time.monotonic() - start_time) < effective_timeout:
            current_count = await self.get_subtask_count_async(task_gid)

            if current_count >= expected_count:
                elapsed_ms = (time.monotonic() - start_time) * 1000
                logger.debug(
                    "Subtasks ready: task_gid=%s, count=%d, elapsed_ms=%.1f",
                    task_gid,
                    current_count,
                    elapsed_ms,
                )
                return True

            await asyncio.sleep(effective_interval)

        # Timeout reached
        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.warning(
            "Subtask wait timeout: task_gid=%s, expected=%d, actual=%d, elapsed_ms=%.1f",
            task_gid,
            expected_count,
            current_count,
            elapsed_ms,
        )
        return False

    async def get_subtask_count_async(self, task_gid: str) -> int:
        """Get current subtask count for a task.

        Per FR-WAIT-007: Uses subtasks_async() to get accurate count.

        Args:
            task_gid: GID of the parent task.

        Returns:
            Current number of subtasks.
        """
        # Use minimal opt_fields for efficiency - only need count
        subtasks = await self._client.tasks.subtasks_async(
            task_gid, opt_fields=["gid"]
        ).collect()
        return len(subtasks)
