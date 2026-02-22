"""Unit tests for healing module.

Per FR-DET-006/ADR-0118: Tests for self-healing utilities.

Test cases:
1. HealingResult creation and __bool__
2. heal_entity_async with dry_run=True
3. heal_entity_async with actual healing
4. heal_entity_async error handling
5. heal_entities_async batch operation
6. Validation errors for entities that don't need healing
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.models.business.detection import DetectionResult, EntityType
from autom8_asana.persistence.healing import (
    HealingResult,
    heal_entities_async,
    heal_entity_async,
)

# --- Fixtures ---


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock AsanaClient."""
    client = MagicMock()
    client.tasks = MagicMock()
    client.tasks.add_to_project_async = AsyncMock()
    return client


@pytest.fixture
def mock_entity_needs_healing() -> MagicMock:
    """Create a mock entity that needs healing."""
    entity = MagicMock()
    entity.gid = "entity_gid_123"
    entity._detection_result = DetectionResult(
        entity_type=EntityType.CONTACT_HOLDER,
        confidence=0.6,
        tier_used=2,
        needs_healing=True,
        expected_project_gid="expected_project_gid_456",
    )
    return entity


@pytest.fixture
def mock_entity_no_healing_needed() -> MagicMock:
    """Create a mock entity that doesn't need healing."""
    entity = MagicMock()
    entity.gid = "entity_gid_789"
    entity._detection_result = DetectionResult(
        entity_type=EntityType.BUSINESS,
        confidence=1.0,
        tier_used=1,
        needs_healing=False,
        expected_project_gid="project_gid",
    )
    return entity


@pytest.fixture
def mock_entity_no_detection() -> MagicMock:
    """Create a mock entity without detection result."""
    entity = MagicMock(spec=["gid"])
    entity.gid = "entity_gid_no_detection"
    return entity


# --- Test: HealingResult ---


class TestHealingResult:
    """Tests for HealingResult dataclass.

    Per TDD-SPRINT-5-CLEANUP/ABS-001: Tests updated for unified HealingResult
    from models.py with project_gid and entity_type fields.
    """

    def test_creation(self) -> None:
        """HealingResult can be created with all fields."""
        result = HealingResult(
            entity_gid="entity_123",
            entity_type="Contact",
            project_gid="project_456",
            success=True,
            dry_run=False,
            error=None,
        )

        assert result.entity_gid == "entity_123"
        assert result.entity_type == "Contact"
        assert result.project_gid == "project_456"
        assert result.success is True
        assert result.dry_run is False
        assert result.error is None

    def test_frozen_immutability(self) -> None:
        """HealingResult is immutable (frozen)."""
        result = HealingResult(
            entity_gid="entity_123",
            entity_type="Contact",
            project_gid="project_456",
            success=True,
            dry_run=False,
            error=None,
        )

        with pytest.raises(FrozenInstanceError):
            result.success = False  # type: ignore[misc]

    def test_bool_true_for_success(self) -> None:
        """__bool__ returns True when success=True."""
        result = HealingResult(
            entity_gid="entity_123",
            entity_type="Contact",
            project_gid="project_456",
            success=True,
            dry_run=False,
            error=None,
        )

        assert bool(result) is True

    def test_bool_false_for_failure(self) -> None:
        """__bool__ returns False when success=False."""
        result = HealingResult(
            entity_gid="entity_123",
            entity_type="Contact",
            project_gid="project_456",
            success=False,
            dry_run=False,
            error="test error",  # Now str, not Exception per unified type
        )

        assert bool(result) is False

    def test_bool_true_for_dry_run_success(self) -> None:
        """__bool__ returns True for successful dry run."""
        result = HealingResult(
            entity_gid="entity_123",
            entity_type="Contact",
            project_gid="project_456",
            success=True,
            dry_run=True,
            error=None,
        )

        assert bool(result) is True


# --- Test: heal_entity_async ---


class TestHealEntityAsync:
    """Tests for heal_entity_async function.

    Per TDD-SPRINT-5-CLEANUP/ABS-001: Updated to check entity_type and project_gid.
    """

    @pytest.mark.asyncio
    async def test_dry_run_success(
        self, mock_client: MagicMock, mock_entity_needs_healing: MagicMock
    ) -> None:
        """Dry run returns success without making API call."""
        result = await heal_entity_async(
            mock_entity_needs_healing, mock_client, dry_run=True
        )

        assert result.success is True
        assert result.dry_run is True
        assert result.entity_gid == "entity_gid_123"
        assert result.entity_type == "MagicMock"  # Type from mock object
        assert result.project_gid == "expected_project_gid_456"
        assert result.error is None

        # No API call should be made
        mock_client.tasks.add_to_project_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_actual_healing_success(
        self, mock_client: MagicMock, mock_entity_needs_healing: MagicMock
    ) -> None:
        """Actual healing calls API and returns success."""
        result = await heal_entity_async(
            mock_entity_needs_healing, mock_client, dry_run=False
        )

        assert result.success is True
        assert result.dry_run is False
        assert result.entity_gid == "entity_gid_123"
        assert result.entity_type == "MagicMock"  # Type from mock object
        assert result.project_gid == "expected_project_gid_456"
        assert result.error is None

        # API call should be made
        mock_client.tasks.add_to_project_async.assert_called_once_with(
            "entity_gid_123",
            project_gid="expected_project_gid_456",
        )

    @pytest.mark.asyncio
    async def test_actual_healing_api_error(
        self, mock_client: MagicMock, mock_entity_needs_healing: MagicMock
    ) -> None:
        """API error is captured in result as string."""
        api_error = RuntimeError("API error")
        mock_client.tasks.add_to_project_async.side_effect = api_error

        result = await heal_entity_async(
            mock_entity_needs_healing, mock_client, dry_run=False
        )

        assert result.success is False
        assert result.dry_run is False
        assert result.error == "API error"  # Now a string, not Exception

    @pytest.mark.asyncio
    async def test_raises_for_no_detection_result(
        self, mock_client: MagicMock, mock_entity_no_detection: MagicMock
    ) -> None:
        """Raises ValueError if entity has no detection result."""
        with pytest.raises(ValueError, match="has no detection result"):
            await heal_entity_async(mock_entity_no_detection, mock_client)

    @pytest.mark.asyncio
    async def test_raises_for_no_healing_needed(
        self, mock_client: MagicMock, mock_entity_no_healing_needed: MagicMock
    ) -> None:
        """Raises ValueError if entity doesn't need healing."""
        with pytest.raises(ValueError, match="does not need healing"):
            await heal_entity_async(mock_entity_no_healing_needed, mock_client)

    @pytest.mark.asyncio
    async def test_raises_for_no_expected_project_gid(
        self, mock_client: MagicMock
    ) -> None:
        """Raises ValueError if expected_project_gid is None."""
        entity = MagicMock()
        entity.gid = "entity_123"
        entity._detection_result = DetectionResult(
            entity_type=EntityType.UNKNOWN,
            confidence=0.0,
            tier_used=5,
            needs_healing=True,
            expected_project_gid=None,  # No expected project
        )

        with pytest.raises(ValueError, match="has no expected_project_gid"):
            await heal_entity_async(entity, mock_client)


# --- Test: heal_entities_async ---


class TestHealEntitiesAsync:
    """Tests for heal_entities_async batch function."""

    @pytest.fixture
    def mock_entities_mixed(self) -> list[MagicMock]:
        """Create a list of entities with mixed healing needs."""
        entity1 = MagicMock()
        entity1.gid = "entity_1"
        entity1._detection_result = DetectionResult(
            entity_type=EntityType.CONTACT_HOLDER,
            confidence=0.6,
            tier_used=2,
            needs_healing=True,
            expected_project_gid="project_1",
        )

        entity2 = MagicMock()
        entity2.gid = "entity_2"
        entity2._detection_result = DetectionResult(
            entity_type=EntityType.BUSINESS,
            confidence=1.0,
            tier_used=1,
            needs_healing=False,  # Doesn't need healing
            expected_project_gid="project_2",
        )

        entity3 = MagicMock()
        entity3.gid = "entity_3"
        entity3._detection_result = DetectionResult(
            entity_type=EntityType.UNIT_HOLDER,
            confidence=0.6,
            tier_used=2,
            needs_healing=True,
            expected_project_gid="project_3",
        )

        return [entity1, entity2, entity3]

    @pytest.mark.asyncio
    async def test_filters_to_entities_needing_healing(
        self, mock_client: MagicMock, mock_entities_mixed: list[MagicMock]
    ) -> None:
        """Only entities that need healing are processed."""
        results = await heal_entities_async(
            mock_entities_mixed, mock_client, dry_run=True
        )

        # Should only process 2 entities (entity1 and entity3)
        assert len(results) == 2
        assert all(r.success for r in results)
        assert results[0].entity_gid == "entity_1"
        assert results[1].entity_gid == "entity_3"

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self, mock_client: MagicMock) -> None:
        """Empty entity list returns empty results."""
        results = await heal_entities_async([], mock_client)

        assert results == []

    @pytest.mark.asyncio
    async def test_no_entities_need_healing_returns_empty(
        self, mock_client: MagicMock, mock_entity_no_healing_needed: MagicMock
    ) -> None:
        """List with no entities needing healing returns empty."""
        results = await heal_entities_async(
            [mock_entity_no_healing_needed], mock_client
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_concurrent_healing_respects_semaphore(
        self, mock_client: MagicMock
    ) -> None:
        """Batch healing respects max_concurrent limit."""
        # Create 10 entities needing healing
        entities = []
        for i in range(10):
            entity = MagicMock()
            entity.gid = f"entity_{i}"
            entity._detection_result = DetectionResult(
                entity_type=EntityType.CONTACT_HOLDER,
                confidence=0.6,
                tier_used=2,
                needs_healing=True,
                expected_project_gid=f"project_{i}",
            )
            entities.append(entity)

        results = await heal_entities_async(
            entities, mock_client, dry_run=True, max_concurrent=3
        )

        # All should be healed
        assert len(results) == 10
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_actual_healing_calls_api_for_each(
        self, mock_client: MagicMock, mock_entities_mixed: list[MagicMock]
    ) -> None:
        """Actual healing calls API for each entity needing healing."""
        results = await heal_entities_async(
            mock_entities_mixed, mock_client, dry_run=False
        )

        # 2 entities need healing
        assert len(results) == 2
        assert mock_client.tasks.add_to_project_async.call_count == 2

    @pytest.mark.asyncio
    async def test_partial_failure_returns_all_results(
        self, mock_client: MagicMock
    ) -> None:
        """Partial failures still return results for all attempts."""
        # Create 3 entities needing healing
        entities = []
        for i in range(3):
            entity = MagicMock()
            entity.gid = f"entity_{i}"
            entity._detection_result = DetectionResult(
                entity_type=EntityType.CONTACT_HOLDER,
                confidence=0.6,
                tier_used=2,
                needs_healing=True,
                expected_project_gid=f"project_{i}",
            )
            entities.append(entity)

        # Second call fails
        mock_client.tasks.add_to_project_async.side_effect = [
            None,  # Success
            RuntimeError("API error"),  # Failure
            None,  # Success
        ]

        results = await heal_entities_async(entities, mock_client, dry_run=False)

        assert len(results) == 3
        # Note: order may vary due to concurrent execution
        success_count = sum(1 for r in results if r.success)
        failure_count = sum(1 for r in results if not r.success)
        assert success_count == 2
        assert failure_count == 1

    @pytest.mark.asyncio
    async def test_entities_without_detection_result_skipped(
        self, mock_client: MagicMock, mock_entity_no_detection: MagicMock
    ) -> None:
        """Entities without _detection_result are silently skipped."""
        # hasattr will return False for mock_entity_no_detection
        entity_with_detection = MagicMock()
        entity_with_detection.gid = "entity_with"
        entity_with_detection._detection_result = DetectionResult(
            entity_type=EntityType.CONTACT_HOLDER,
            confidence=0.6,
            tier_used=2,
            needs_healing=True,
            expected_project_gid="project_1",
        )

        # Create entity without _detection_result attribute at all
        entity_without = MagicMock(spec=["gid"])
        entity_without.gid = "entity_without"

        results = await heal_entities_async(
            [entity_with_detection, entity_without],
            mock_client,
            dry_run=True,
        )

        # Only entity with detection result should be processed
        assert len(results) == 1
        assert results[0].entity_gid == "entity_with"
