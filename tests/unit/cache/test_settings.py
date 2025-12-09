"""Tests for CacheSettings, TTLSettings, and OverflowSettings."""

import pytest

from autom8_asana.cache.entry import EntryType
from autom8_asana.cache.settings import CacheSettings, OverflowSettings, TTLSettings


class TestOverflowSettings:
    """Tests for OverflowSettings."""

    def test_default_thresholds(self) -> None:
        """Test default overflow thresholds."""
        settings = OverflowSettings()

        assert settings.subtasks == 40
        assert settings.dependencies == 40
        assert settings.dependents == 40
        assert settings.stories == 100
        assert settings.attachments == 40

    def test_custom_thresholds(self) -> None:
        """Test custom overflow thresholds."""
        settings = OverflowSettings(
            subtasks=50,
            stories=200,
        )

        assert settings.subtasks == 50
        assert settings.stories == 200
        assert settings.dependencies == 40  # Default

    def test_get_threshold(self) -> None:
        """Test get_threshold returns correct values."""
        settings = OverflowSettings(subtasks=25, stories=75)

        assert settings.get_threshold(EntryType.SUBTASKS) == 25
        assert settings.get_threshold(EntryType.STORIES) == 75
        assert settings.get_threshold(EntryType.DEPENDENCIES) == 40

    def test_get_threshold_no_limit(self) -> None:
        """Test get_threshold returns None for types without limits."""
        settings = OverflowSettings()

        assert settings.get_threshold(EntryType.TASK) is None
        assert settings.get_threshold(EntryType.STRUC) is None

    def test_should_cache_within_threshold(self) -> None:
        """Test should_cache returns True when within threshold."""
        settings = OverflowSettings(subtasks=40)

        assert settings.should_cache(EntryType.SUBTASKS, 0)
        assert settings.should_cache(EntryType.SUBTASKS, 20)
        assert settings.should_cache(EntryType.SUBTASKS, 40)

    def test_should_cache_exceeds_threshold(self) -> None:
        """Test should_cache returns False when exceeding threshold."""
        settings = OverflowSettings(subtasks=40)

        assert not settings.should_cache(EntryType.SUBTASKS, 41)
        assert not settings.should_cache(EntryType.SUBTASKS, 100)

    def test_should_cache_no_threshold(self) -> None:
        """Test should_cache returns True for types without threshold."""
        settings = OverflowSettings()

        assert settings.should_cache(EntryType.TASK, 0)
        assert settings.should_cache(EntryType.TASK, 1000000)
        assert settings.should_cache(EntryType.STRUC, 100)


class TestTTLSettings:
    """Tests for TTLSettings."""

    def test_default_ttl(self) -> None:
        """Test default TTL is 300 seconds."""
        settings = TTLSettings()
        assert settings.default_ttl == 300

    def test_custom_default_ttl(self) -> None:
        """Test custom default TTL."""
        settings = TTLSettings(default_ttl=600)
        assert settings.default_ttl == 600

    def test_get_ttl_default(self) -> None:
        """Test get_ttl returns default when no overrides match."""
        settings = TTLSettings(default_ttl=300)

        assert settings.get_ttl() == 300
        assert settings.get_ttl(project_gid="unknown") == 300
        assert settings.get_ttl(entry_type="unknown") == 300

    def test_get_ttl_project_override(self) -> None:
        """Test get_ttl returns project-specific TTL."""
        settings = TTLSettings(
            default_ttl=300,
            project_ttls={"project_123": 600, "project_456": 900},
        )

        assert settings.get_ttl(project_gid="project_123") == 600
        assert settings.get_ttl(project_gid="project_456") == 900
        assert settings.get_ttl(project_gid="unknown") == 300

    def test_get_ttl_entry_type_override(self) -> None:
        """Test get_ttl returns entry-type-specific TTL."""
        settings = TTLSettings(
            default_ttl=300,
            entry_type_ttls={"stories": 60, "task": 600},
        )

        assert settings.get_ttl(entry_type="stories") == 60
        assert settings.get_ttl(entry_type="task") == 600
        assert settings.get_ttl(entry_type="subtasks") == 300

    def test_get_ttl_entry_type_enum(self) -> None:
        """Test get_ttl handles EntryType enum."""
        settings = TTLSettings(
            default_ttl=300,
            entry_type_ttls={"stories": 60},
        )

        assert settings.get_ttl(entry_type=EntryType.STORIES) == 60
        assert settings.get_ttl(entry_type=EntryType.TASK) == 300

    def test_get_ttl_project_takes_priority(self) -> None:
        """Test project TTL takes priority over entry type TTL."""
        settings = TTLSettings(
            default_ttl=300,
            project_ttls={"project_123": 1000},
            entry_type_ttls={"stories": 60},
        )

        # Project TTL should win
        assert settings.get_ttl(project_gid="project_123", entry_type="stories") == 1000
        # Entry type TTL when no project match
        assert settings.get_ttl(entry_type="stories") == 60


class TestCacheSettings:
    """Tests for CacheSettings."""

    def test_default_settings(self) -> None:
        """Test default cache settings."""
        settings = CacheSettings()

        assert settings.enabled is True
        assert settings.batch_check_ttl == 25
        assert settings.reconnect_interval == 30
        assert settings.max_batch_size == 100
        assert isinstance(settings.ttl, TTLSettings)
        assert isinstance(settings.overflow, OverflowSettings)

    def test_disabled_settings(self) -> None:
        """Test disabled cache settings."""
        settings = CacheSettings(enabled=False)
        assert settings.enabled is False

    def test_custom_batch_settings(self) -> None:
        """Test custom batch settings."""
        settings = CacheSettings(
            batch_check_ttl=50,
            reconnect_interval=60,
            max_batch_size=200,
        )

        assert settings.batch_check_ttl == 50
        assert settings.reconnect_interval == 60
        assert settings.max_batch_size == 200

    def test_get_ttl_delegates(self) -> None:
        """Test get_ttl delegates to TTLSettings."""
        settings = CacheSettings(
            ttl=TTLSettings(
                default_ttl=600,
                project_ttls={"project_123": 1200},
            )
        )

        assert settings.get_ttl() == 600
        assert settings.get_ttl(project_gid="project_123") == 1200

    def test_should_cache_delegates(self) -> None:
        """Test should_cache delegates to OverflowSettings."""
        settings = CacheSettings(
            overflow=OverflowSettings(subtasks=30)
        )

        assert settings.should_cache(EntryType.SUBTASKS, 30)
        assert not settings.should_cache(EntryType.SUBTASKS, 31)

    def test_nested_settings_modification(self) -> None:
        """Test that nested settings can be modified."""
        settings = CacheSettings()

        # Modify TTL settings
        settings.ttl.default_ttl = 600
        assert settings.get_ttl() == 600

        # Modify overflow settings
        settings.overflow.subtasks = 100
        assert settings.should_cache(EntryType.SUBTASKS, 100)
