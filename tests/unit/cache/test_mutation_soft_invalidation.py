"""Tests for MutationInvalidator soft invalidation mode.

Per TDD-CROSS-TIER-FRESHNESS-001: Tests for soft invalidation behavior,
configuration filtering, fallback to hard eviction, and default state.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from autom8_asana.cache.integration.mutation_invalidator import (
    _TASK_ENTRY_TYPES,
    MutationInvalidator,
    SoftInvalidationConfig,
)
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.freshness_stamp import FreshnessStamp, VerificationSource
from autom8_asana.cache.models.mutation_event import (
    EntityKind,
    MutationEvent,
    MutationType,
)
from autom8_asana.protocols.cache import CacheProvider

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_cache() -> Mock:
    """Create a mock cache provider."""
    return Mock(spec=CacheProvider)


@pytest.fixture
def task_update_event() -> MutationEvent:
    """Create a task update mutation event."""
    return MutationEvent(
        entity_kind=EntityKind.TASK,
        entity_gid="123456",
        mutation_type=MutationType.UPDATE,
        project_gids=["proj-1"],
    )


@pytest.fixture
def task_create_event() -> MutationEvent:
    """Create a task create mutation event."""
    return MutationEvent(
        entity_kind=EntityKind.TASK,
        entity_gid="123456",
        mutation_type=MutationType.CREATE,
        project_gids=["proj-1"],
    )


def _make_stamped_entry(
    entry_type: EntryType = EntryType.TASK,
) -> CacheEntry:
    """Create a cache entry with a freshness stamp."""
    return CacheEntry(
        key="123456",
        data={"gid": "123456"},
        entry_type=entry_type,
        version=datetime(2025, 1, 1, tzinfo=UTC),
        ttl=300,
        freshness_stamp=FreshnessStamp(
            last_verified_at=datetime(2025, 6, 1, tzinfo=UTC),
            source=VerificationSource.API_FETCH,
        ),
    )


# ============================================================================
# Tests
# ============================================================================


class TestSoftInvalidationDisabledByDefault:
    """Default config uses hard eviction."""

    def test_soft_invalidation_disabled_by_default(
        self, mock_cache: Mock, task_update_event: MutationEvent
    ) -> None:
        """Default config uses hard eviction, not soft invalidation."""
        invalidator = MutationInvalidator(mock_cache)

        invalidator._invalidate_entity_entries("123456", task_update_event)

        # Should call invalidate (hard eviction), not get_versioned+set_versioned
        mock_cache.invalidate.assert_called_once_with("123456", _TASK_ENTRY_TYPES)
        mock_cache.get_versioned.assert_not_called()
        mock_cache.set_versioned.assert_not_called()


class TestSoftInvalidationMarksStamp:
    """Soft invalidation applies staleness hint to stamps."""

    def test_soft_invalidation_marks_stamp(
        self, mock_cache: Mock, task_update_event: MutationEvent
    ) -> None:
        """Entry receives staleness_hint via soft invalidation."""
        stamped_entry = _make_stamped_entry(EntryType.TASK)
        mock_cache.get_versioned.return_value = stamped_entry

        config = SoftInvalidationConfig(
            enabled=True,
            soft_entity_kinds=frozenset({"task"}),
            soft_mutation_types=frozenset({"update"}),
        )
        invalidator = MutationInvalidator(mock_cache, soft_config=config)

        invalidator._invalidate_entity_entries("123456", task_update_event)

        # Should have called set_versioned with marked entry for each entry type
        assert mock_cache.set_versioned.call_count == len(_TASK_ENTRY_TYPES)

        # Check the first call's entry has staleness hint
        set_call = mock_cache.set_versioned.call_args_list[0]
        marked_entry = set_call[0][1]
        assert marked_entry.freshness_stamp is not None
        assert marked_entry.freshness_stamp.staleness_hint is not None
        assert (
            "mutation:task:update:123456" in marked_entry.freshness_stamp.staleness_hint
        )
        # Source should be preserved
        assert marked_entry.freshness_stamp.source == VerificationSource.API_FETCH


class TestSoftInvalidationFallback:
    """Fallback to hard eviction on errors and missing stamps."""

    def test_soft_invalidation_fallback_no_stamp(
        self, mock_cache: Mock, task_update_event: MutationEvent
    ) -> None:
        """Legacy entry without stamp gets hard evicted."""
        legacy_entry = CacheEntry(
            key="123456",
            data={"gid": "123456"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            ttl=300,
            freshness_stamp=None,  # No stamp
        )
        mock_cache.get_versioned.return_value = legacy_entry

        config = SoftInvalidationConfig(
            enabled=True,
            soft_entity_kinds=frozenset({"task"}),
        )
        invalidator = MutationInvalidator(mock_cache, soft_config=config)

        invalidator._invalidate_entity_entries("123456", task_update_event)

        # Should hard invalidate since no stamp
        assert mock_cache.invalidate.call_count == len(_TASK_ENTRY_TYPES)

    def test_soft_invalidation_fallback_on_error(
        self, mock_cache: Mock, task_update_event: MutationEvent
    ) -> None:
        """Falls back to hard eviction on failure."""
        mock_cache.get_versioned.side_effect = RuntimeError("connection lost")

        config = SoftInvalidationConfig(
            enabled=True,
            soft_entity_kinds=frozenset({"task"}),
        )
        invalidator = MutationInvalidator(mock_cache, soft_config=config)

        # Should not raise
        invalidator._invalidate_entity_entries("123456", task_update_event)

        # Should attempt hard invalidation as fallback
        assert mock_cache.invalidate.call_count == len(_TASK_ENTRY_TYPES)

    def test_soft_invalidation_fallback_no_entry(
        self, mock_cache: Mock, task_update_event: MutationEvent
    ) -> None:
        """Missing entry gets hard invalidated."""
        mock_cache.get_versioned.return_value = None

        config = SoftInvalidationConfig(
            enabled=True,
            soft_entity_kinds=frozenset({"task"}),
        )
        invalidator = MutationInvalidator(mock_cache, soft_config=config)

        invalidator._invalidate_entity_entries("123456", task_update_event)

        # Should hard invalidate since no entry found
        assert mock_cache.invalidate.call_count == len(_TASK_ENTRY_TYPES)


class TestSoftInvalidationEntityFilter:
    """Entity kind filtering for soft invalidation."""

    def test_soft_invalidation_config_entity_filter(self, mock_cache: Mock) -> None:
        """Only configured entity kinds get soft invalidation."""
        # Config only allows "section" for soft invalidation
        config = SoftInvalidationConfig(
            enabled=True,
            soft_entity_kinds=frozenset({"section"}),
        )
        invalidator = MutationInvalidator(mock_cache, soft_config=config)

        # Task update should NOT use soft invalidation
        task_event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="123",
            mutation_type=MutationType.UPDATE,
        )
        invalidator._invalidate_entity_entries("123", task_event)

        # Should use hard invalidation since "task" is not in soft_entity_kinds
        mock_cache.invalidate.assert_called_once_with("123", _TASK_ENTRY_TYPES)
        mock_cache.get_versioned.assert_not_called()

    def test_soft_invalidation_mutation_type_filter(self, mock_cache: Mock) -> None:
        """Only configured mutation types get soft invalidation."""
        config = SoftInvalidationConfig(
            enabled=True,
            soft_entity_kinds=frozenset({"task"}),
            soft_mutation_types=frozenset({"update"}),  # Only updates
        )
        invalidator = MutationInvalidator(mock_cache, soft_config=config)

        # CREATE should NOT use soft invalidation
        create_event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="123",
            mutation_type=MutationType.CREATE,
        )
        invalidator._invalidate_entity_entries("123", create_event)

        # Should use hard invalidation since CREATE is not in soft_mutation_types
        mock_cache.invalidate.assert_called_once_with("123", _TASK_ENTRY_TYPES)

    def test_soft_invalidation_empty_entity_filter_allows_all(
        self, mock_cache: Mock, task_update_event: MutationEvent
    ) -> None:
        """Empty soft_entity_kinds allows all entity kinds."""
        stamped_entry = _make_stamped_entry()
        mock_cache.get_versioned.return_value = stamped_entry

        config = SoftInvalidationConfig(
            enabled=True,
            soft_entity_kinds=frozenset(),  # Empty = all allowed
        )
        invalidator = MutationInvalidator(mock_cache, soft_config=config)

        invalidator._invalidate_entity_entries("123456", task_update_event)

        # Should use soft invalidation
        assert mock_cache.set_versioned.call_count == len(_TASK_ENTRY_TYPES)


class TestSoftInvalidationConfig:
    """Tests for SoftInvalidationConfig defaults."""

    def test_default_config(self) -> None:
        """Default config has soft invalidation disabled."""
        config = SoftInvalidationConfig()
        assert config.enabled is False
        assert config.soft_entity_kinds == frozenset()
        assert config.soft_mutation_types == frozenset({"update"})
