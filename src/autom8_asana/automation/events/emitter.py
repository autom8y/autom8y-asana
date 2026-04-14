"""Event emitter for routing envelopes to transport destinations.

Per GAP-03 FR-003/FR-005: Routes envelopes to matching subscriptions.
Per FR-007: Structured log events for metrics extraction.
Per FR-010: Dead letter logging for failed envelopes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.automation.events.config import EventRoutingConfig
    from autom8_asana.automation.events.envelope import EventEnvelope
    from autom8_asana.automation.events.transport import EventTransport

logger = get_logger(__name__)


@dataclass(frozen=True)
class EmitResult:
    """Result of emission attempt across all matching destinations."""

    attempted: int
    succeeded: int
    failed: int

    @property
    def all_succeeded(self) -> bool:
        return self.attempted > 0 and self.failed == 0

    @property
    def partial(self) -> bool:
        return self.succeeded > 0 and self.failed > 0


class EventEmitter:
    """Orchestrates event publication across matching subscriptions.

    The emitter does NOT raise exceptions. All transport errors are caught,
    logged, and swallowed. This is the commit-path safety boundary.
    """

    def __init__(
        self,
        transport: EventTransport,
        config: EventRoutingConfig,
    ) -> None:
        self._transport = transport
        self._config = config

    async def emit(self, envelope: EventEnvelope) -> EmitResult:
        """Publish envelope to all matching subscription destinations.

        Per SC-004: Transport errors are caught and logged, never raised.
        Per FR-010: Failed envelopes logged as structured events.

        Args:
            envelope: The event to publish.

        Returns:
            EmitResult with per-destination success/failure tracking.
        """
        matching = self._config.matching_subscriptions(
            event_type=envelope.event_type.value,
            entity_type=envelope.entity_type,
        )

        if not matching:
            logger.debug(
                "event_no_matching_subscriptions",
                event_type=envelope.event_type.value,
                entity_type=envelope.entity_type,
            )
            return EmitResult(attempted=0, succeeded=0, failed=0)

        attempted = 0
        succeeded = 0
        failed = 0

        for sub in matching:
            attempted += 1
            start = time.perf_counter()
            try:
                await self._transport.publish(envelope, sub.destination)
                elapsed_ms = (time.perf_counter() - start) * 1000
                succeeded += 1

                # FR-007: Emission metrics
                logger.info(
                    "event_emitted",
                    event_type=envelope.event_type.value,
                    entity_type=envelope.entity_type,
                    destination=sub.destination,
                    event_id=envelope.event_id,
                    latency_ms=round(elapsed_ms, 2),
                )

            except (
                Exception  # noqa: BLE001
            ) as e:  # BROAD-CATCH: isolation -- transport failure must not propagate to commit path
                elapsed_ms = (time.perf_counter() - start) * 1000
                failed += 1

                # FR-007: Failure metric
                logger.warning(
                    "event_emission_failed",
                    event_type=envelope.event_type.value,
                    entity_type=envelope.entity_type,
                    destination=sub.destination,
                    event_id=envelope.event_id,
                    error=str(e),
                    error_class=type(e).__name__,
                    latency_ms=round(elapsed_ms, 2),
                )

                # FR-010: Dead letter logging
                logger.warning(
                    "event_dead_letter",
                    envelope=envelope.to_json_dict(),
                    destination=sub.destination,
                    error=str(e),
                )

        return EmitResult(attempted=attempted, succeeded=succeeded, failed=failed)
