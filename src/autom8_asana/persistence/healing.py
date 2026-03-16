"""Entity self-healing utilities.

Per ADR-0095/ADR-0118/FR-DET-006: Self-healing for entities missing project membership.
Per TDD-SPRINT-5-CLEANUP/ABS-001: HealingResult consolidated to models.py.

This module provides utilities for "healing" entities that were detected via
fallback tiers (Tier 2 name patterns, Tier 3 parent inference) rather than
the deterministic Tier 1 project membership. Healing adds the entity to its
expected project so future detection is deterministic.

Self-healing is OPT-IN - it must be explicitly enabled via:
1. SaveSession `healing_enabled=True` parameter (planned)
2. Standalone `heal_entity_async()` or `heal_entities_async()` functions

Example:
    # Standalone healing
    from autom8_asana.persistence.healing import heal_entity_async
    from autom8_asana.persistence.models import HealingResult

    result = await heal_entity_async(entity, client, dry_run=True)
    if result.success:
        print(f"Would heal {result.entity_gid} -> {result.project_gid}")

    # Actually heal
    result = await heal_entity_async(entity, client, dry_run=False)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

# Import HealingResult from models (canonical location per ABS-001)
from autom8_asana.persistence.models import HealingResult

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.base import BusinessEntity
    from autom8_asana.persistence.models import HealingReport
    from autom8_asana.transport.asana_http import AsanaHttpClient

__all__ = [
    "HealingResult",
    "HealingManager",
    "heal_entity_async",
    "heal_entities_async",
]

logger = get_logger(__name__)


class HealingManager:
    """Manages self-healing queue and execution for SaveSession.

    Per TDD-TECH-DEBT-REMEDIATION Phase 3: Consolidates healing logic that was
    previously inline in SaveSession. Extracted to improve testability and
    separation of concerns.

    Self-healing adds missing project memberships to entities that were
    detected via fallback tiers (2-5) instead of deterministic Tier 1.
    Healing is opt-in and non-blocking - failures are logged and reported
    but do not fail the overall SaveSession commit.

    The HealingManager is created by SaveSession and coordinates:
    1. Eligibility checking via should_heal()
    2. Queue management via enqueue()
    3. Execution via execute_async()

    Example:
        # Typical usage within SaveSession
        manager = HealingManager(auto_heal=True)

        # During track()
        if manager.should_heal(entity):
            manager.enqueue(entity)

        # During commit()
        report = await manager.execute_async(http_client)
    """

    def __init__(self, auto_heal: bool = False) -> None:
        """Initialize the healing manager.

        Args:
            auto_heal: If True, entities detected via fallback tiers (2-5)
                      will be eligible for healing. Default: False.
        """
        self._auto_heal = auto_heal
        self._queue: list[tuple[Any, str]] = []
        self._entity_heal_flags: dict[str, bool] = {}

    @property
    def auto_heal(self) -> bool:
        """Whether auto-healing is enabled."""
        return self._auto_heal

    @property
    def queue(self) -> list[tuple[Any, str]]:
        """Return copy of healing queue.

        Returns:
            List of (entity, expected_project_gid) tuples queued for healing.
        """
        return list(self._queue)

    def set_entity_heal_flag(self, gid: str, heal: bool) -> None:
        """Set per-entity heal override.

        Args:
            gid: Entity GID to set flag for.
            heal: True to force healing, False to skip healing.
        """
        self._entity_heal_flags[gid] = heal

    def should_heal(self, entity: Any, heal_override: bool | None = None) -> bool:
        """Check if entity needs healing based on detection result.

        Per TDD-DETECTION/ADR-0095: Healing is triggered when ALL conditions are met:
        1. Session has auto_heal=True OR heal_override=True
        2. Entity has _detection_result attribute
        3. detection_result.tier_used > 1 (not Tier 1 deterministic)
        4. detection_result.expected_project_gid is not None
        5. detection_result.needs_healing is True
        6. Per-entity override heal=False was not specified

        Args:
            entity: Entity to check for healing eligibility.
            heal_override: Per-entity heal flag (None uses session default).

        Returns:
            True if entity should be queued for healing.
        """
        # Check per-entity override first (explicit False skips healing)
        if heal_override is False:
            return False

        # Check session-level flag OR per-entity force heal
        should_heal_session = self._auto_heal or heal_override is True

        if not should_heal_session:
            return False

        # Must have detection result
        detection = getattr(entity, "_detection_result", None)
        if detection is None:
            return False

        # Must have used fallback tier (not Tier 1)
        if detection.tier_used <= 1:
            return False

        # Must have expected project GID
        if detection.expected_project_gid is None:
            return False

        # Must have needs_healing flag set
        return bool(detection.needs_healing)

    def enqueue(self, entity: Any) -> None:
        """Add entity to healing queue if eligible.

        Per TDD-DETECTION/ADR-0095: Add entity to healing queue with
        deduplication by GID.

        Args:
            entity: Entity with _detection_result to queue for healing.
        """
        detection = getattr(entity, "_detection_result", None)
        if detection is None or detection.expected_project_gid is None:
            return

        # Avoid duplicates (same entity GID)
        for queued_entity, _ in self._queue:
            if queued_entity.gid == entity.gid:
                return

        self._queue.append((entity, detection.expected_project_gid))

        logger.debug(
            "Queued entity for healing",
            extra={
                "entity_type": type(entity).__name__,
                "entity_gid": entity.gid,
                "expected_project_gid": detection.expected_project_gid,
                "tier_used": detection.tier_used,
            },
        )

    async def execute_async(self, http_client: AsanaHttpClient) -> HealingReport:
        """Execute healing for all queued entities.

        Per TDD-DETECTION/ADR-0095: Healing adds missing project memberships.
        Per TDD-SPRINT-5-CLEANUP/ABS-001: Uses unified HealingResult from models.py.
        Healing failures are NON-BLOCKING - they are logged and reported
        but do not fail the overall commit.

        Args:
            http_client: Async HTTP client for making API requests. Expected to have
                        a request() method for POST requests.

        Returns:
            HealingReport with all healing outcomes.
        """
        from autom8_asana.persistence.models import HealingReport

        report = HealingReport()

        if not self._queue:
            return report

        for entity, project_gid in self._queue:
            report.attempted += 1
            entity_type = type(entity).__name__

            try:
                # Use add_to_project via HTTP request
                await http_client.request(
                    "POST",
                    f"/tasks/{entity.gid}/addProject",
                    data={"data": {"project": project_gid}},
                )

                result = HealingResult(
                    entity_gid=entity.gid,
                    entity_type=entity_type,
                    project_gid=project_gid,
                    success=True,
                    error=None,
                )
                report.succeeded += 1
                report.results.append(result)

                logger.info(
                    "entity_healed",
                    entity_gid=entity.gid,
                    entity_type=entity_type,
                    project_gid=project_gid,
                )

            except (
                ConnectionError,
                TimeoutError,
                OSError,
                RuntimeError,
            ) as e:  # isolation -- per-entity healing loop, failure must not abort batch
                error_msg = str(e)
                result = HealingResult(
                    entity_gid=entity.gid,
                    entity_type=entity_type,
                    project_gid=project_gid,
                    success=False,
                    error=error_msg,
                )
                report.failed += 1
                report.results.append(result)

                # Non-blocking: log warning and continue
                logger.warning(
                    "healing_failed",
                    entity_gid=entity.gid,
                    entity_type=entity_type,
                    error=error_msg,
                )

        # Clear the healing queue after execution
        self._queue.clear()

        return report

    def clear(self) -> None:
        """Clear the healing queue.

        Called after execution or when resetting session state.
        """
        self._queue.clear()


async def heal_entity_async(
    entity: BusinessEntity,
    client: AsanaClient,
    dry_run: bool = False,
) -> HealingResult:
    """Heal a single entity by adding to expected project.

    Per ADR-0118/FR-DET-006: Standalone healing utility.
    Per TDD-SPRINT-5-CLEANUP/ABS-001: Uses unified HealingResult from models.py.

    This function adds the entity to its expected project (determined during
    detection). The entity must have a _detection_result attribute with:
    - needs_healing=True
    - expected_project_gid set

    Args:
        entity: BusinessEntity to heal (must have _detection_result).
        client: AsanaClient for API calls.
        dry_run: If True, log what would happen but don't make API call.

    Returns:
        HealingResult with outcome.

    Raises:
        ValueError: If entity has no detection result, doesn't need healing,
            or has no expected_project_gid.

    Example:
        # Check if healing would succeed
        result = await heal_entity_async(entity, client, dry_run=True)
        if result:
            print(f"Would add {entity.gid} to project {result.project_gid}")

        # Actually heal
        result = await heal_entity_async(entity, client)
        if result:
            print("Entity healed successfully")
        else:
            print(f"Healing failed: {result.error}")
    """
    detection = getattr(entity, "_detection_result", None)

    if detection is None:
        raise ValueError(f"Entity {entity.gid} has no detection result")
    if not detection.needs_healing:
        raise ValueError(f"Entity {entity.gid} does not need healing")
    if not detection.expected_project_gid:
        raise ValueError(f"Entity {entity.gid} has no expected_project_gid")

    entity_type = type(entity).__name__
    project_gid = detection.expected_project_gid

    if dry_run:
        logger.info(
            "Dry run: would heal entity",
            extra={
                "entity_gid": entity.gid,
                "entity_type": entity_type,
                "project_gid": project_gid,
            },
        )
        return HealingResult(
            entity_gid=entity.gid,
            entity_type=entity_type,
            project_gid=project_gid,
            success=True,
            dry_run=True,
            error=None,
        )

    try:
        await client.tasks.add_to_project_async(
            entity.gid,
            project_gid=project_gid,
        )
        logger.info(
            "Healed entity",
            extra={
                "entity_gid": entity.gid,
                "entity_type": entity_type,
                "project_gid": project_gid,
            },
        )
        return HealingResult(
            entity_gid=entity.gid,
            entity_type=entity_type,
            project_gid=project_gid,
            success=True,
            dry_run=False,
            error=None,
        )
    except (
        Exception
    ) as e:  # BROAD-CATCH: isolation -- returns error result, never propagates
        logger.warning(
            "Failed to heal entity",
            extra={
                "entity_gid": entity.gid,
                "entity_type": entity_type,
                "project_gid": project_gid,
                "error": str(e),
            },
        )
        return HealingResult(
            entity_gid=entity.gid,
            entity_type=entity_type,
            project_gid=project_gid,
            success=False,
            dry_run=False,
            error=str(e),  # Convert Exception to str per unified type
        )


async def heal_entities_async(
    entities: list[BusinessEntity],
    client: AsanaClient,
    dry_run: bool = False,
    max_concurrent: int = 5,
) -> list[HealingResult]:
    """Heal multiple entities with concurrency control.

    Per ADR-0118: Batch healing with configurable concurrency.

    This function heals multiple entities concurrently, respecting the
    max_concurrent limit to avoid overwhelming the API.

    Args:
        entities: List of BusinessEntity instances to heal.
        client: AsanaClient for API calls.
        dry_run: If True, log what would happen but don't make API calls.
        max_concurrent: Maximum concurrent healing operations (default: 5).

    Returns:
        List of HealingResult for entities that needed healing.
        Empty list if no entities needed healing.

    Example:
        results = await heal_entities_async(entities, client, dry_run=True)
        for result in results:
            if result:
                print(f"Would heal {result.entity_gid}")

        # Actually heal
        results = await heal_entities_async(entities, client)
        succeeded = sum(1 for r in results if r.success)
        print(f"Healed {succeeded}/{len(results)} entities")
    """
    # Filter to entities that actually need healing
    to_heal = [
        e
        for e in entities
        if hasattr(e, "_detection_result")
        and e._detection_result
        and e._detection_result.needs_healing
        and e._detection_result.expected_project_gid
    ]

    if not to_heal:
        return []

    semaphore = asyncio.Semaphore(max_concurrent)

    async def heal_one(entity: BusinessEntity) -> HealingResult:
        async with semaphore:
            return await heal_entity_async(entity, client, dry_run)

    return list(await asyncio.gather(*[heal_one(e) for e in to_heal]))
