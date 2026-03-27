"""Loop detection for webhook-triggered lifecycle transitions.

Per ADR-omniscience-lifecycle-observation Decision 3:
- Time-windowed set of recently-written entity GIDs (30-second window)
- Prevents self-triggered webhook loops
- In-memory dict does not survive process restarts (acceptable for MVP)
- Failure mode: at most one redundant idempotent lifecycle execution
"""

from __future__ import annotations

import time

from autom8y_log import get_logger

logger = get_logger(__name__)


class LoopDetector:
    """Detects self-triggered webhook loops via time-windowed GID tracking.

    When the system writes to an entity (creates, moves section, etc.),
    it records the GID via record_outbound(). When a webhook arrives for
    that GID within the window, is_self_triggered() returns True.

    Integration points for record_outbound():
    1. LifecycleEngine Phase 1 (CREATE) -- after entity creation
    2. CascadingSectionService -- after section move
    3. SaveSession Phase 3 (EXECUTE) -- after BatchExecutor completes

    Attributes:
        window_seconds: TTL for outbound write tracking. Default 30s.
    """

    def __init__(self, window_seconds: int = 30) -> None:
        self._recent_writes: dict[str, float] = {}
        self._window_seconds = window_seconds

    def record_outbound(self, entity_gid: str) -> None:
        """Record that we just wrote to an entity.

        Prunes expired entries on each call for memory hygiene.

        Args:
            entity_gid: The GID of the entity we just modified.
        """
        self._prune()
        self._recent_writes[entity_gid] = time.monotonic()

    def is_self_triggered(self, entity_gid: str) -> bool:
        """Check whether an inbound event for this GID was self-triggered.

        Returns True if we recently wrote to this entity (within the
        window_seconds TTL). Prunes expired entries on each call.

        Args:
            entity_gid: The GID from the inbound webhook event.

        Returns:
            True if the event is likely self-triggered.
        """
        self._prune()
        if entity_gid in self._recent_writes:
            logger.info(
                "loop_detected",
                entity_gid=entity_gid,
                window_seconds=self._window_seconds,
            )
            return True
        return False

    def _prune(self) -> None:
        """Remove entries older than the window."""
        cutoff = time.monotonic() - self._window_seconds
        expired = [gid for gid, ts in self._recent_writes.items() if ts < cutoff]
        for gid in expired:
            del self._recent_writes[gid]

    @property
    def tracked_count(self) -> int:
        """Number of currently tracked GIDs (for monitoring/testing)."""
        self._prune()
        return len(self._recent_writes)
