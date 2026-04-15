"""Tests for detection result caching.

Per TDD-CACHE-PERF-DETECTION: Unit tests for detection cache behavior.
Per PRD-CACHE-PERF-DETECTION: Validates cache integration requirements.

Test cases:
1. EntryType.DETECTION exists in enum
2. Cache hit returns cached DetectionResult
3. Cache miss proceeds to Tier 4 and stores result
4. Graceful degradation on cache failure
5. Tiers 1-3 bypass cache entirely (zero overhead)
6. UNKNOWN results are not cached
7. Serialization roundtrip preserves all fields
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.models.business.detection.facade import (
    DETECTION_CACHE_TTL,
    _cache_detection_result,
    _get_cached_detection,
    detect_entity_type_async,
)
from autom8_asana.models.business.detection.types import (
    CONFIDENCE_TIER_4,
    DetectionResult,
    EntityType,
)
from autom8_asana.models.task import Task

# --- Fixtures ---


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create a mock cache provider."""
    cache = MagicMock()
    cache.get.return_value = None
    return cache


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock AsanaClient without cache."""
    client = MagicMock()
    client._cache_provider = None
    client.default_workspace_gid = None
    return client


@pytest.fixture
def mock_client_with_cache(mock_cache: MagicMock) -> MagicMock:
    """Create a mock AsanaClient with cache provider."""
    client = MagicMock()
    client._cache_provider = mock_cache
    client.default_workspace_gid = None
    return client


def make_task(
    gid: str = "task_gid",
    name: str | None = "Test Task",
    modified_at: str | None = None,
    memberships: list[dict] | None = None,
) -> Task:
    """Create a Task with specified attributes."""
    return Task(gid=gid, name=name, modified_at=modified_at, memberships=memberships)


def make_detection_result(
    entity_type: EntityType = EntityType.BUSINESS,
    confidence: float = CONFIDENCE_TIER_4,
    tier_used: int = 4,
    needs_healing: bool = True,
    expected_project_gid: str | None = "project_123",
) -> DetectionResult:
    """Create a DetectionResult with specified attributes."""
    return DetectionResult(
        entity_type=entity_type,
        confidence=confidence,
        tier_used=tier_used,
        needs_healing=needs_healing,
        expected_project_gid=expected_project_gid,
    )


def make_cache_entry(
    task_gid: str,
    result: DetectionResult,
    cached_at: datetime | None = None,
    ttl: int = DETECTION_CACHE_TTL,
) -> CacheEntry:
    """Create a CacheEntry for a DetectionResult."""
    if cached_at is None:
        cached_at = datetime.now(UTC)

    return CacheEntry(
        key=task_gid,
        data={
            "entity_type": result.entity_type.value,
            "confidence": result.confidence,
            "tier_used": result.tier_used,
            "needs_healing": result.needs_healing,
            "expected_project_gid": result.expected_project_gid,
        },
        entry_type=EntryType.DETECTION,
        version=cached_at,
        cached_at=cached_at,
        ttl=ttl,
    )


# --- Test: EntryType.DETECTION ---


class TestEntryTypeDetection:
    """Tests for EntryType.DETECTION enum member."""

    def test_entry_type_detection_exists(self) -> None:
        """FR-ENTRY-001: EntryType.DETECTION exists in enum."""
        assert hasattr(EntryType, "DETECTION")
        assert EntryType.DETECTION.value == "detection"

    def test_entry_type_detection_is_string_enum(self) -> None:
        """Verify DETECTION is a string enum."""
        assert isinstance(EntryType.DETECTION, str)
        assert EntryType.DETECTION == "detection"

    def test_entry_type_detection_from_string(self) -> None:
        """Verify can create EntryType.DETECTION from string."""
        assert EntryType("detection") == EntryType.DETECTION


# --- Test: _get_cached_detection ---


class TestGetCachedDetection:
    """Tests for _get_cached_detection helper."""

    def test_cache_hit_returns_result(self, mock_cache: MagicMock) -> None:
        """FR-CACHE-001: Cache hit returns DetectionResult."""
        task_gid = "task_123"
        expected_result = make_detection_result(
            entity_type=EntityType.BUSINESS,
            confidence=0.9,
            tier_used=4,
            needs_healing=True,
            expected_project_gid="proj_456",
        )
        cache_entry = make_cache_entry(task_gid, expected_result)
        mock_cache.get.return_value = cache_entry

        result = _get_cached_detection(task_gid, mock_cache)

        assert result is not None
        assert result.entity_type == EntityType.BUSINESS
        assert result.confidence == 0.9
        assert result.tier_used == 4
        assert result.needs_healing is True
        assert result.expected_project_gid == "proj_456"
        mock_cache.get.assert_called_once_with(task_gid, EntryType.DETECTION)

    def test_cache_miss_returns_none(self, mock_cache: MagicMock) -> None:
        """FR-CACHE-001: Cache miss returns None."""
        mock_cache.get.return_value = None

        result = _get_cached_detection("task_123", mock_cache)

        assert result is None

    def test_expired_entry_returns_none(self, mock_cache: MagicMock) -> None:
        """FR-VERSION-003: Expired cache entry returns None."""
        # Create an expired entry (cached 10 minutes ago with 5 minute TTL)
        past = datetime.now(UTC) - timedelta(minutes=10)
        expected_result = make_detection_result()
        cache_entry = make_cache_entry("task_123", expected_result, cached_at=past, ttl=300)
        mock_cache.get.return_value = cache_entry

        result = _get_cached_detection("task_123", mock_cache)

        assert result is None

    def test_cache_error_returns_none(self, mock_cache: MagicMock) -> None:
        """FR-DEGRADE-001: Cache lookup error returns None (graceful degradation)."""
        mock_cache.get.side_effect = ConnectionError("Cache connection failed")

        result = _get_cached_detection("task_123", mock_cache)

        assert result is None

    def test_deserializes_all_entity_types(self, mock_cache: MagicMock) -> None:
        """FR-ENTRY-003: All EntityType values can be deserialized."""
        for entity_type in [
            EntityType.BUSINESS,
            EntityType.UNIT,
            EntityType.CONTACT,
            EntityType.OFFER,
            EntityType.PROCESS,
        ]:
            expected_result = make_detection_result(entity_type=entity_type)
            cache_entry = make_cache_entry("task_123", expected_result)
            mock_cache.get.return_value = cache_entry

            result = _get_cached_detection("task_123", mock_cache)

            assert result is not None
            assert result.entity_type == entity_type


# --- Test: _cache_detection_result ---


class TestCacheDetectionResult:
    """Tests for _cache_detection_result helper."""

    def test_stores_entry_with_correct_key_and_type(self, mock_cache: MagicMock) -> None:
        """FR-CACHE-002: Stores entry with correct key and EntryType."""
        task = make_task(gid="task_123")
        result = make_detection_result()

        _cache_detection_result(task, result, mock_cache)

        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args[0][0] == "task_123"
        entry = call_args[0][1]
        assert entry.key == "task_123"
        assert entry.entry_type == EntryType.DETECTION

    def test_uses_task_modified_at_as_version(self, mock_cache: MagicMock) -> None:
        """FR-VERSION-001: Uses task.modified_at as version."""
        modified_at_str = "2025-01-15T12:00:00+00:00"
        expected_version = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        task = make_task(gid="task_123", modified_at=modified_at_str)
        result = make_detection_result()

        _cache_detection_result(task, result, mock_cache)

        entry = mock_cache.set.call_args[0][1]
        assert entry.version == expected_version

    def test_uses_current_time_when_no_modified_at(self, mock_cache: MagicMock) -> None:
        """FR-VERSION-002: Uses current time if modified_at is None."""
        before = datetime.now(UTC)
        task = make_task(gid="task_123", modified_at=None)
        result = make_detection_result()

        _cache_detection_result(task, result, mock_cache)
        after = datetime.now(UTC)

        entry = mock_cache.set.call_args[0][1]
        assert before <= entry.version <= after

    def test_uses_correct_ttl(self, mock_cache: MagicMock) -> None:
        """FR-VERSION-003: Uses DETECTION_CACHE_TTL (300s)."""
        task = make_task(gid="task_123")
        result = make_detection_result()

        _cache_detection_result(task, result, mock_cache)

        entry = mock_cache.set.call_args[0][1]
        assert entry.ttl == 300

    def test_skips_unknown_results(self, mock_cache: MagicMock) -> None:
        """FR-CACHE-006: Does not cache UNKNOWN results."""
        task = make_task(gid="task_123")
        result = make_detection_result(entity_type=EntityType.UNKNOWN)

        _cache_detection_result(task, result, mock_cache)

        mock_cache.set.assert_not_called()

    def test_preserves_all_fields(self, mock_cache: MagicMock) -> None:
        """FR-ENTRY-003: All 5 DetectionResult fields are preserved."""
        task = make_task(gid="task_123")
        result = make_detection_result(
            entity_type=EntityType.UNIT,
            confidence=0.85,
            tier_used=4,
            needs_healing=False,
            expected_project_gid="proj_789",
        )

        _cache_detection_result(task, result, mock_cache)

        entry = mock_cache.set.call_args[0][1]
        data = entry.data
        assert data["entity_type"] == "unit"
        assert data["confidence"] == 0.85
        assert data["tier_used"] == 4
        assert data["needs_healing"] is False
        assert data["expected_project_gid"] == "proj_789"

    def test_cache_error_does_not_raise(self, mock_cache: MagicMock) -> None:
        """FR-DEGRADE-002: Cache storage error does not raise."""
        mock_cache.set.side_effect = ConnectionError("Cache write failed")
        task = make_task(gid="task_123")
        result = make_detection_result()

        # Should not raise
        _cache_detection_result(task, result, mock_cache)


# --- Test: Serialization Roundtrip ---


class TestSerializationRoundtrip:
    """Tests for DetectionResult serialization/deserialization roundtrip."""

    def test_roundtrip_preserves_all_fields(self, mock_cache: MagicMock) -> None:
        """NFR-ACCURACY-003: All DetectionResult fields preserved through roundtrip."""
        task = make_task(gid="task_123")
        original = make_detection_result(
            entity_type=EntityType.BUSINESS,
            confidence=0.9,
            tier_used=4,
            needs_healing=True,
            expected_project_gid="proj_456",
        )

        # Store
        _cache_detection_result(task, original, mock_cache)
        entry = mock_cache.set.call_args[0][1]

        # Setup cache to return what was stored
        mock_cache.get.return_value = entry

        # Retrieve
        retrieved = _get_cached_detection("task_123", mock_cache)

        assert retrieved is not None
        assert retrieved.entity_type == original.entity_type
        assert retrieved.confidence == original.confidence
        assert retrieved.tier_used == original.tier_used
        assert retrieved.needs_healing == original.needs_healing
        assert retrieved.expected_project_gid == original.expected_project_gid

    def test_roundtrip_with_none_project_gid(self, mock_cache: MagicMock) -> None:
        """Roundtrip handles None expected_project_gid."""
        task = make_task(gid="task_123")
        original = make_detection_result(expected_project_gid=None)

        _cache_detection_result(task, original, mock_cache)
        entry = mock_cache.set.call_args[0][1]
        mock_cache.get.return_value = entry

        retrieved = _get_cached_detection("task_123", mock_cache)

        assert retrieved is not None
        assert retrieved.expected_project_gid is None


# --- Test: detect_entity_type_async Cache Integration ---


class TestDetectEntityTypeAsyncCacheIntegration:
    """Tests for cache integration in detect_entity_type_async."""

    @pytest.fixture
    def mock_subtask(self) -> MagicMock:
        """Create a mock subtask."""
        subtask = MagicMock()
        subtask.name = "Contacts"
        return subtask

    async def test_cache_hit_returns_result_without_api_call(
        self,
        mock_client_with_cache: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """FR-CACHE-001: Cache hit returns result without Tier 4 API call."""
        task = make_task(gid="task_123", name="Random Name")
        cached_result = make_detection_result(entity_type=EntityType.BUSINESS)
        cache_entry = make_cache_entry(task.gid, cached_result)
        mock_cache.get.return_value = cache_entry

        result = await detect_entity_type_async(
            task, mock_client_with_cache, allow_structure_inspection=True
        )

        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 4  # Cached from Tier 4
        # Verify no API call was made
        mock_client_with_cache.tasks.subtasks_async.assert_not_called()

    async def test_cache_miss_executes_tier4_and_stores(
        self,
        mock_client_with_cache: MagicMock,
        mock_cache: MagicMock,
        mock_subtask: MagicMock,
    ) -> None:
        """FR-CACHE-002: Cache miss executes Tier 4 and stores result."""
        task = make_task(gid="task_123", name="Random Name")
        mock_cache.get.return_value = None  # Cache miss

        # Mock Tier 4 API call
        mock_client_with_cache.tasks.subtasks_async.return_value.collect = AsyncMock(
            return_value=[mock_subtask]
        )

        result = await detect_entity_type_async(
            task, mock_client_with_cache, allow_structure_inspection=True
        )

        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 4
        # Verify API was called
        mock_client_with_cache.tasks.subtasks_async.assert_called_once_with(task.gid)
        # Verify cache was populated
        mock_cache.set.assert_called_once()

    async def test_no_cache_check_for_tier1_success(
        self,
        mock_client_with_cache: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """NFR-LATENCY-004: No cache check when Tier 1 succeeds."""
        # Register project in static registry
        from autom8_asana.models.business.registry import get_registry

        registry = get_registry()
        registry.register("proj_456", EntityType.BUSINESS)

        task = make_task(
            gid="task_123",
            name="Test",
            memberships=[{"project": {"gid": "proj_456"}}],
        )

        result = await detect_entity_type_async(
            task, mock_client_with_cache, allow_structure_inspection=True
        )

        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 1
        # No cache interaction should occur for Tier 1 success
        mock_cache.get.assert_not_called()
        mock_cache.set.assert_not_called()

    async def test_no_cache_check_for_tier2_success(
        self,
        mock_client_with_cache: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """NFR-LATENCY-004: No cache check when Tier 2 succeeds."""
        task = make_task(gid="task_123", name="Contacts")  # Matches Tier 2 pattern

        result = await detect_entity_type_async(
            task, mock_client_with_cache, allow_structure_inspection=True
        )

        assert result.entity_type == EntityType.CONTACT_HOLDER
        assert result.tier_used == 2
        # No cache interaction for Tier 2 success
        mock_cache.get.assert_not_called()
        mock_cache.set.assert_not_called()

    async def test_cache_check_failure_degrades_gracefully(
        self,
        mock_client_with_cache: MagicMock,
        mock_cache: MagicMock,
        mock_subtask: MagicMock,
    ) -> None:
        """FR-DEGRADE-001: Cache check failure degrades gracefully."""
        task = make_task(gid="task_123", name="Random Name")
        mock_cache.get.side_effect = ConnectionError("Cache connection failed")

        # Mock Tier 4 API call (should proceed despite cache failure)
        mock_client_with_cache.tasks.subtasks_async.return_value.collect = AsyncMock(
            return_value=[mock_subtask]
        )

        result = await detect_entity_type_async(
            task, mock_client_with_cache, allow_structure_inspection=True
        )

        # Detection should succeed via Tier 4
        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 4

    async def test_cache_store_failure_degrades_gracefully(
        self,
        mock_client_with_cache: MagicMock,
        mock_cache: MagicMock,
        mock_subtask: MagicMock,
    ) -> None:
        """FR-DEGRADE-002: Cache store failure degrades gracefully."""
        task = make_task(gid="task_123", name="Random Name")
        mock_cache.get.return_value = None
        mock_cache.set.side_effect = ConnectionError("Cache write failed")

        # Mock Tier 4 API call
        mock_client_with_cache.tasks.subtasks_async.return_value.collect = AsyncMock(
            return_value=[mock_subtask]
        )

        result = await detect_entity_type_async(
            task, mock_client_with_cache, allow_structure_inspection=True
        )

        # Detection should succeed despite cache store failure
        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 4

    async def test_no_cache_provider_proceeds_normally(
        self,
        mock_client: MagicMock,
        mock_subtask: MagicMock,
    ) -> None:
        """FR-DEGRADE-004: No cache provider proceeds normally."""
        task = make_task(gid="task_123", name="Random Name")
        mock_client._cache_provider = None  # No cache

        # Mock Tier 4 API call
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(
            return_value=[mock_subtask]
        )

        result = await detect_entity_type_async(task, mock_client, allow_structure_inspection=True)

        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 4

    async def test_tier4_none_result_not_cached(
        self,
        mock_client_with_cache: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """FR-CACHE-005: Tier 4 None result (no match) not cached."""
        task = make_task(gid="task_123", name="Random Name")
        mock_cache.get.return_value = None

        # Mock Tier 4 to return no match
        non_indicator_subtask = MagicMock()
        non_indicator_subtask.name = "Random Subtask"
        mock_client_with_cache.tasks.subtasks_async.return_value.collect = AsyncMock(
            return_value=[non_indicator_subtask]
        )

        result = await detect_entity_type_async(
            task, mock_client_with_cache, allow_structure_inspection=True
        )

        # Falls through to UNKNOWN
        assert result.entity_type == EntityType.UNKNOWN
        assert result.tier_used == 5
        # Cache should not be written for UNKNOWN
        mock_cache.set.assert_not_called()


# --- Test: Cache with structure_inspection disabled ---


class TestCacheWithStructureInspectionDisabled:
    """Tests for cache behavior when structure_inspection is disabled."""

    async def test_no_cache_interaction_when_inspection_disabled(
        self,
        mock_client_with_cache: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """No cache check when allow_structure_inspection=False."""
        task = make_task(gid="task_123", name="Random Name")

        result = await detect_entity_type_async(
            task, mock_client_with_cache, allow_structure_inspection=False
        )

        # Falls through to UNKNOWN (Tier 5)
        assert result.entity_type == EntityType.UNKNOWN
        assert result.tier_used == 5
        # No cache interaction
        mock_cache.get.assert_not_called()
        mock_cache.set.assert_not_called()
