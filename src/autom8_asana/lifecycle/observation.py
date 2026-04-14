"""Stage transition observation data model and emitter.

Per ADR-omniscience-lifecycle-observation Decision 1:
- StageTransitionRecord: frozen dataclass generalizing SectionInterval to all entity types
- EntityStageTimeline: per-entity stage history with computed properties
- StageTransitionEmitter: async, fire-and-forget emitter called from LifecycleEngine

Data Sources:
- LifecycleEngine.handle_transition_async() emits records after successful transitions
- Records persist to entity-type-partitioned parquet via StageTransitionStore
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.lifecycle.observation_store import StageTransitionStore

logger = get_logger(__name__)


@dataclass(frozen=True)
class StageTransitionRecord:
    """A single stage transition observation for any entity type.

    Generalizes SectionInterval from offer-only to all entity types.
    Each record captures one transition event in the pipeline.

    Attributes:
        entity_gid: Asana task GID of the transitioned entity.
        entity_type: Entity class name (e.g., "Business", "Unit", "Offer", "Process").
        business_gid: Parent business GID for joining (None if not applicable).
        from_stage: Source stage name (None for initial placement).
        to_stage: Target stage name.
        pipeline_stage_num: Numeric pipeline_stage from config (1-10).
        transition_type: One of "converted", "did_not_convert", "initial", "reopen".
        entered_at: UTC timestamp when entity entered to_stage.
        exited_at: UTC timestamp when entity left to_stage (None = still current).
        automation_result_id: Correlation to AutomationResult rule_id.
        duration_ms: Time spent in from_stage before this transition.
    """

    entity_gid: str
    entity_type: str
    business_gid: str | None

    from_stage: str | None
    to_stage: str
    pipeline_stage_num: int

    transition_type: str  # "converted" | "did_not_convert" | "initial" | "reopen"

    entered_at: datetime
    exited_at: datetime | None

    automation_result_id: str | None
    duration_ms: float | None


@dataclass(frozen=True)
class EntityStageTimeline:
    """Complete stage history for any entity, generalizing SectionTimeline.

    SectionTimeline (offer-only) uses Asana story API for reconstruction.
    EntityStageTimeline uses lifecycle engine events for reconstruction,
    making it available for ALL entity types that flow through the pipeline.

    Attributes:
        entity_gid: Asana task GID.
        entity_type: Entity class name.
        business_gid: Parent business GID for joining.
        intervals: Tuple of StageTransitionRecords ordered by entered_at.
    """

    entity_gid: str
    entity_type: str
    business_gid: str | None
    intervals: tuple[StageTransitionRecord, ...]

    def time_in_stage(self, stage: str) -> timedelta | None:
        """Total time spent in a specific stage across all intervals.

        Only counts intervals where exited_at is set (completed intervals).
        Returns None if no completed intervals exist for the stage.
        """
        total_seconds = 0.0
        found = False
        for interval in self.intervals:
            if interval.to_stage == stage and interval.exited_at is not None:
                delta = interval.exited_at - interval.entered_at
                total_seconds += delta.total_seconds()
                found = True
        return timedelta(seconds=total_seconds) if found else None

    def current_stage(self) -> str | None:
        """Current stage (last interval with exited_at=None).

        Returns None if all intervals are closed (entity has exited pipeline).
        """
        for interval in reversed(self.intervals):
            if interval.exited_at is None:
                return interval.to_stage
        return None

    def days_in_current_stage(self) -> int:
        """Days since entering current stage.

        Returns 0 if entity has no open interval.
        """
        for interval in reversed(self.intervals):
            if interval.exited_at is None:
                delta = datetime.now(UTC) - interval.entered_at
                return delta.days
        return 0

    def converted_through(self, stages: list[str]) -> bool:
        """Whether entity passed through all listed stages in order.

        Checks that each stage appears in the intervals with
        transition_type="converted", and in the given order.

        Args:
            stages: Ordered list of stage names to check.

        Returns:
            True if entity converted through all stages in order.
        """
        if not stages:
            return True

        stage_idx = 0
        for interval in self.intervals:
            if interval.to_stage == stages[stage_idx] and interval.transition_type == "converted":
                stage_idx += 1
                if stage_idx >= len(stages):
                    return True
        return False


class StageTransitionEmitter:
    """Async, fire-and-forget emitter for stage transition records.

    Injected into LifecycleEngine via constructor injection. Called after
    _build_result() in handle_transition_async() to emit observation records
    for all transition types (converted, DNC, terminal, deferred).

    The emitter swallows all exceptions to preserve the fail-forward contract.
    Emission failures are logged but never block the transition pipeline.
    """

    def __init__(self, store: StageTransitionStore) -> None:
        self._store = store

    async def emit(self, record: StageTransitionRecord) -> None:
        """Emit a stage transition record to the store.

        Fire-and-forget: exceptions are logged but not propagated.
        Uses asyncio.to_thread to avoid blocking the event loop on
        parquet I/O.

        Args:
            record: The transition record to persist.
        """
        try:
            await asyncio.to_thread(self._store.append, record)
            logger.info(
                "stage_transition_emitted",
                entity_gid=record.entity_gid,
                entity_type=record.entity_type,
                from_stage=record.from_stage,
                to_stage=record.to_stage,
                transition_type=record.transition_type,
            )
        except Exception:  # BROAD-CATCH: fire-and-forget (fail-forward)  # noqa: BLE001
            logger.warning(
                "stage_transition_emit_failed",
                entity_gid=record.entity_gid,
                entity_type=record.entity_type,
                exc_info=True,
            )
