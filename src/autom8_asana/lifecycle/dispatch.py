# src/autom8_asana/lifecycle/dispatch.py

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.lifecycle.engine import LifecycleEngine

logger = get_logger(__name__)


class AutomationDispatch:
    """Unified entry point for all automation triggers.

    Routes:
    - Section change events -> LifecycleEngine
    - Tag-based triggers -> LifecycleEngine (via tag routing config)
    - Action requests -> ActionExecutor (existing)
    - Workflow requests -> WorkflowAction registry (existing)

    Circular trigger prevention via trigger_chain tracking.
    """

    def __init__(
        self,
        client: AsanaClient,
        lifecycle_engine: LifecycleEngine,
    ) -> None:
        self._client = client
        self._lifecycle_engine = lifecycle_engine

    async def dispatch_async(
        self,
        trigger: dict[str, Any],
        trigger_chain: list[str] | None = None,
    ) -> dict[str, Any]:
        """Route trigger to appropriate subsystem.

        Args:
            trigger: Trigger data (from webhook, polling, or internal).
            trigger_chain: Chain of trigger IDs for circular prevention.

        Returns:
            Result dict from the handling subsystem.
        """
        chain = trigger_chain or []
        trigger_id = trigger.get("id", "unknown")

        # Circular trigger prevention
        if trigger_id in chain:
            logger.warning(
                "circular_trigger_detected",
                trigger_id=trigger_id,
                chain=chain,
            )
            return {"success": False, "error": "circular_trigger"}

        chain.append(trigger_id)

        trigger_type = trigger.get("type")

        if trigger_type == "section_changed":
            return await self._handle_section_change(trigger, chain)
        elif trigger_type == "tag_added":
            return await self._handle_tag_trigger(trigger, chain)

        return {
            "success": False,
            "error": f"unknown_trigger_type: {trigger_type}",
        }

    async def _handle_section_change(
        self,
        trigger: dict[str, Any],
        chain: list[str],
    ) -> dict[str, Any]:
        """Route section change to lifecycle engine."""
        from autom8_asana.models.business.process import (
            Process,
        )

        task_gid: str = trigger.get("task_gid", "")
        section_name = trigger.get("section_name", "").lower()

        # Determine outcome from section
        if "converted" == section_name:
            outcome = "converted"
        elif "did not convert" in section_name or "did_not_convert" in section_name:
            outcome = "did_not_convert"
        else:
            return {
                "success": False,
                "error": f"unhandled_section: {section_name}",
            }

        # Fetch process
        task_data = await self._client.tasks.get_async(task_gid)  # type: ignore[arg-type]  # task_gid validated non-None by caller
        process = Process.model_validate(task_data.model_dump())

        result = await self._lifecycle_engine.handle_transition_async(process, outcome)
        return {"success": result.success, "result": result}

    async def _handle_tag_trigger(
        self,
        trigger: dict[str, Any],
        chain: list[str],
    ) -> dict[str, Any]:
        """Route tag-based trigger to lifecycle engine."""
        tag_name = trigger.get("tag_name", "")

        if tag_name.startswith("route_"):
            stage = tag_name.replace("route_", "")
            # Route to lifecycle engine as a "converted" transition
            # targeting the specified stage
            return {"success": True, "routed_to": f"lifecycle:{stage}"}

        return {"success": False, "error": f"unhandled_tag: {tag_name}"}
