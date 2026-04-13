"""Lifecycle webhook dispatcher replacing NoOpDispatcher at GAP-03 seam.

Per ADR-omniscience-lifecycle-observation Decision 3:
- LifecycleWebhookDispatcher implements the webhook dispatch path
- 4-layer feature flag: global enable, dry_run, entity allowlist, event allowlist
- Defaults to DISABLED + DRY_RUN (R-007 risk mitigation)
- Integrates LoopDetector for self-triggered event prevention

Evaluation order:
  enabled == false -> short-circuit return
  entity_type not in allowlist -> skip
  event_type not in allowlist -> skip
  loop detected -> skip
  dry_run == true -> log and return
  otherwise -> live dispatch
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.lifecycle.dispatch import AutomationDispatch
    from autom8_asana.lifecycle.loop_detector import LoopDetector

logger = get_logger(__name__)


@dataclass(frozen=True)
class WebhookDispatcherConfig:
    """4-layer feature flag configuration for webhook dispatcher.

    All defaults are maximally conservative: disabled, dry-run, empty allowlists.
    Configuration is read from environment variables at startup.

    Attributes:
        enabled: Global kill switch. Default: False.
        dry_run: Log-only mode even when enabled. Default: True.
        allowed_entity_types: Entity types permitted for dispatch. Empty = none.
        allowed_event_types: Event types permitted for dispatch. Empty = none.
    """

    enabled: bool = False
    dry_run: bool = True
    allowed_entity_types: frozenset[str] = field(default_factory=frozenset)
    allowed_event_types: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_env(cls) -> WebhookDispatcherConfig:
        """Build config from environment variables.

        Environment variables:
            WEBHOOK_DISPATCH_ENABLED: "true"/"false" (default: "false")
            WEBHOOK_DISPATCH_DRY_RUN: "true"/"false" (default: "true")
            WEBHOOK_DISPATCH_ENTITY_TYPES: comma-separated (default: "")
            WEBHOOK_DISPATCH_EVENT_TYPES: comma-separated (default: "")

        Returns:
            WebhookDispatcherConfig populated from environment.
        """
        enabled = os.getenv("WEBHOOK_DISPATCH_ENABLED", "false").lower() == "true"
        dry_run = os.getenv("WEBHOOK_DISPATCH_DRY_RUN", "true").lower() != "false"

        entity_types_raw = os.getenv("WEBHOOK_DISPATCH_ENTITY_TYPES", "")
        entity_types = frozenset(t.strip() for t in entity_types_raw.split(",") if t.strip())

        event_types_raw = os.getenv("WEBHOOK_DISPATCH_EVENT_TYPES", "")
        event_types = frozenset(t.strip() for t in event_types_raw.split(",") if t.strip())

        return cls(
            enabled=enabled,
            dry_run=dry_run,
            allowed_entity_types=entity_types,
            allowed_event_types=event_types,
        )


class LifecycleWebhookDispatcher:
    """Webhook dispatcher that routes inbound Asana events to lifecycle automation.

    Replaces NoOpDispatcher at the GAP-03 seam. Connects the inbound webhook
    path to AutomationDispatch.dispatch_async() with 4-layer feature flag
    control and loop detection.

    Flow:
        webhook inbound -> detect event type -> detect entity type
        -> evaluate feature flag -> (dry-run: log / live: dispatch)
        -> AutomationDispatch.dispatch_async()
        -> LifecycleEngine.handle_transition_async()
    """

    def __init__(
        self,
        automation_dispatch: AutomationDispatch,
        config: WebhookDispatcherConfig,
        loop_detector: LoopDetector,
    ) -> None:
        self._dispatch = automation_dispatch
        self._config = config
        self._loop_detector = loop_detector

    async def handle_event(
        self,
        event_type: str,
        entity_type: str,
        entity_gid: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate feature flags and optionally dispatch a lifecycle event.

        Evaluation order (short-circuit on any rejection):
        1. Global enable check
        2. Entity type allowlist
        3. Event type allowlist
        4. Loop detection
        5. Dry-run vs live dispatch

        Args:
            event_type: Event type string (e.g., "section_changed").
            entity_type: Entity type string (e.g., "Process").
            entity_gid: Asana GID of the affected entity.
            payload: Full webhook payload for dispatch context.

        Returns:
            Result dict with "dispatched", "reason", and optionally "result".
        """
        # Layer 1: Global enable
        if not self._config.enabled:
            return {"dispatched": False, "reason": "disabled"}

        # Layer 2: Entity allowlist (empty allowlist means nothing allowed)
        if entity_type not in self._config.allowed_entity_types:
            logger.debug(
                "webhook_entity_type_filtered",
                entity_type=entity_type,
                allowed=list(self._config.allowed_entity_types),
            )
            return {"dispatched": False, "reason": "entity_type_not_allowed"}

        # Layer 3: Event allowlist (empty allowlist means nothing allowed)
        if event_type not in self._config.allowed_event_types:
            logger.debug(
                "webhook_event_type_filtered",
                event_type=event_type,
                allowed=list(self._config.allowed_event_types),
            )
            return {"dispatched": False, "reason": "event_type_not_allowed"}

        # Layer 4: Loop detection
        if self._loop_detector.is_self_triggered(entity_gid):
            logger.info(
                "webhook_loop_detected",
                entity_gid=entity_gid,
                event_type=event_type,
            )
            return {"dispatched": False, "reason": "loop_detected"}

        # Layer 5: Dry-run vs live
        if self._config.dry_run:
            logger.info(
                "webhook_dispatch_dry_run",
                event_type=event_type,
                entity_type=entity_type,
                entity_gid=entity_gid,
            )
            return {"dispatched": False, "reason": "dry_run"}

        # Live dispatch
        trigger = self._build_trigger(event_type, entity_gid, payload)
        try:
            result = await self._dispatch.dispatch_async(trigger)
            logger.info(
                "webhook_dispatch_live",
                event_type=event_type,
                entity_type=entity_type,
                entity_gid=entity_gid,
                success=result.get("success", False),
            )
            return {"dispatched": True, "reason": "live", "result": result}
        except Exception:  # BROAD-CATCH: fail-forward
            logger.warning(
                "webhook_dispatch_failed",
                entity_gid=entity_gid,
                event_type=event_type,
                exc_info=True,
            )
            return {"dispatched": False, "reason": "dispatch_error"}

    def _build_trigger(
        self,
        event_type: str,
        entity_gid: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a trigger dict compatible with AutomationDispatch.

        Maps webhook event types to the trigger format expected by
        dispatch_async().
        """
        trigger: dict[str, Any] = {
            "id": f"webhook_{entity_gid}_{event_type}",
            "task_gid": entity_gid,
            "type": event_type,
        }

        # Extract section_name from payload if present
        section_name = payload.get("section_name")
        if section_name:
            trigger["section_name"] = section_name

        return trigger
