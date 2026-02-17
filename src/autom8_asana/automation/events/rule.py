"""Event emission automation rule.

Per GAP-03 FR-003: AutomationRule implementation for event emission.
Per ADR-GAP03-002: Engine detects events; rule builds envelopes and dispatches.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.automation.base import TriggerCondition
from autom8_asana.automation.events.envelope import EventEnvelope
from autom8_asana.automation.events.types import EventType
from autom8_asana.core.timing import elapsed_ms
from autom8_asana.persistence.models import AutomationResult

if TYPE_CHECKING:
    from autom8_asana.automation.context import AutomationContext
    from autom8_asana.automation.events.emitter import EventEmitter
    from autom8_asana.models.base import AsanaResource

logger = get_logger(__name__)


class EventEmissionRule:
    """Automation rule that emits events to external transport.

    Per FR-003: Implements AutomationRule protocol for event emission.
    Per ADR-GAP03-002: Engine detects events; this rule builds envelopes
    and dispatches via EventEmitter.
    """

    def __init__(
        self,
        emitter: EventEmitter,
        rule_id: str = "event_emission",
        source: str = "save_session",
    ) -> None:
        self._emitter = emitter
        self._rule_id = rule_id
        self._source = source
        # Store last event from should_trigger for use in execute_async
        self._last_event: str = ""

    @property
    def id(self) -> str:
        return self._rule_id

    @property
    def name(self) -> str:
        return "Event Emission"

    @property
    def trigger(self) -> TriggerCondition:
        # Wildcard trigger — actual filtering done via subscription config
        return TriggerCondition(entity_type="*", event="*")

    def should_trigger(
        self,
        entity: AsanaResource,
        event: str,
        context: dict[str, Any],
    ) -> bool:
        """Check if any subscription matches this event.

        Per ADR-GAP03-005: Returns False when events are disabled.

        Args:
            entity: The entity that triggered the event.
            event: The event type string (or EventType).
            context: Additional context.

        Returns:
            True if at least one subscription matches.
        """
        entity_type = type(entity).__name__
        event_value = event.value if hasattr(event, "value") else event

        matching = self._emitter._config.matching_subscriptions(
            event_type=event_value,
            entity_type=entity_type,
        )

        if matching:
            # Store event for execute_async (called immediately after)
            self._last_event = event_value

        return len(matching) > 0

    async def execute_async(
        self,
        entity: AsanaResource,
        context: AutomationContext,
    ) -> AutomationResult:
        """Build envelope and emit via transport.

        Per NFR-001: Fire-and-forget. Transport errors caught by emitter.
        Per FR-002: Builds well-formed EventEnvelope.

        Args:
            entity: The entity that triggered emission.
            context: Automation execution context.

        Returns:
            AutomationResult tracking emission outcome.
        """
        start_time = time.perf_counter()
        entity_type = type(entity).__name__

        # Convert event string to EventType
        try:
            event_type = EventType(self._last_event)
        except ValueError:
            return AutomationResult(
                rule_id=self.id,
                rule_name=self.name,
                triggered_by_gid=entity.gid,
                triggered_by_type=entity_type,
                success=True,
                skipped_reason=f"unknown_event_type:{self._last_event}",
                execution_time_ms=elapsed_ms(start_time),
            )

        # Build thin payload
        payload = self._build_payload(entity, event_type, context)

        envelope = EventEnvelope.build(
            event_type=event_type,
            entity_type=entity_type,
            entity_gid=entity.gid,
            source=self._source,
            payload=payload,
        )

        # Emit (all errors caught by emitter)
        result = await self._emitter.emit(envelope)

        return AutomationResult(
            rule_id=self.id,
            rule_name=self.name,
            triggered_by_gid=entity.gid,
            triggered_by_type=entity_type,
            actions_executed=["emit_event"],
            success=True,  # Emission failures are non-fatal
            execution_time_ms=elapsed_ms(start_time),
            enhancement_results={
                "events_attempted": result.attempted,
                "events_succeeded": result.succeeded,
                "events_failed": result.failed,
            },
        )

    def _build_payload(
        self,
        entity: AsanaResource,
        event_type: EventType,
        context: AutomationContext,
    ) -> dict[str, Any]:
        """Build thin payload with event-specific metadata.

        Per ADR-GAP03-003: GID + metadata only.
        """
        payload: dict[str, Any] = {}

        # Add process_type for entities that have it
        if hasattr(entity, "process_type"):
            pt = entity.process_type
            payload["process_type"] = pt.value if hasattr(pt, "value") else pt

        # Add section info for SECTION_CHANGED
        if event_type == EventType.SECTION_CHANGED and context.save_result:
            from autom8_asana.persistence.models import ActionType

            for action_result in context.save_result.action_results:
                action_op = action_result.action
                if (
                    action_op.task.gid == entity.gid
                    and action_op.action == ActionType.MOVE_TO_SECTION
                    and action_op.target
                ):
                    payload["section_gid"] = action_op.target.gid
                    if action_op.target.name:
                        payload["section_name"] = action_op.target.name
                    break

        return payload
