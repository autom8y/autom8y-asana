"""Tests for CacheEntry and EntryType."""

from datetime import UTC, datetime, timedelta

import pytest

from autom8_asana.cache.entry import CacheEntry, EntryType, _parse_datetime


class TestEntryType:
    """Tests for EntryType enum."""

    def test_entry_type_values(self) -> None:
        """Verify all expected entry types exist."""
        assert EntryType.TASK.value == "task"
        assert EntryType.SUBTASKS.value == "subtasks"
        assert EntryType.DEPENDENCIES.value == "dependencies"
        assert EntryType.DEPENDENTS.value == "dependents"
        assert EntryType.STORIES.value == "stories"
        assert EntryType.ATTACHMENTS.value == "attachments"
        assert EntryType.DATAFRAME.value == "dataframe"

    def test_entry_type_project_sections_exists(self) -> None:
        """Verify PROJECT_SECTIONS entry type exists (FR-CACHE-001)."""
        assert EntryType.PROJECT_SECTIONS.value == "project_sections"
        assert isinstance(EntryType.PROJECT_SECTIONS, str)
        assert EntryType("project_sections") == EntryType.PROJECT_SECTIONS

    def test_entry_type_gid_enumeration_exists(self) -> None:
        """Verify GID_ENUMERATION entry type exists (FR-CACHE-002)."""
        assert EntryType.GID_ENUMERATION.value == "gid_enumeration"
        assert isinstance(EntryType.GID_ENUMERATION, str)
        assert EntryType("gid_enumeration") == EntryType.GID_ENUMERATION

    def test_entry_type_is_string_enum(self) -> None:
        """Verify EntryType is a string enum."""
        assert isinstance(EntryType.TASK, str)
        assert EntryType.TASK == "task"

    def test_entry_type_from_string(self) -> None:
        """Verify can create EntryType from string."""
        assert EntryType("task") == EntryType.TASK
        assert EntryType("subtasks") == EntryType.SUBTASKS


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_create_entry(self) -> None:
        """Test creating a basic cache entry."""
        now = datetime.now(UTC)
        entry = CacheEntry(
            key="1234567890",
            data={"gid": "1234567890", "name": "Test Task"},
            entry_type=EntryType.TASK,
            version=now,
            cached_at=now,
            ttl=300,
        )

        assert entry.key == "1234567890"
        assert entry.data["name"] == "Test Task"
        assert entry.entry_type == EntryType.TASK
        assert entry.version == now
        assert entry.ttl == 300

    def test_entry_is_frozen(self) -> None:
        """Test that CacheEntry is immutable."""
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
        )

        with pytest.raises(AttributeError):
            entry.key = "456"  # type: ignore

    def test_default_cached_at(self) -> None:
        """Test that cached_at defaults to current time."""
        before = datetime.now(UTC)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
        )
        after = datetime.now(UTC)

        assert before <= entry.cached_at <= after

    def test_default_ttl(self) -> None:
        """Test that TTL defaults to 300 seconds."""
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
        )

        assert entry.ttl == 300

    def test_is_expired_within_ttl(self) -> None:
        """Test entry is not expired within TTL."""
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
            cached_at=datetime.now(UTC),
            ttl=300,
        )

        assert not entry.is_expired()

    def test_is_expired_after_ttl(self) -> None:
        """Test entry is expired after TTL."""
        past = datetime.now(UTC) - timedelta(seconds=400)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=past,
            cached_at=past,
            ttl=300,
        )

        assert entry.is_expired()

    def test_is_expired_no_ttl(self) -> None:
        """Test entry with no TTL never expires."""
        past = datetime.now(UTC) - timedelta(days=365)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=past,
            cached_at=past,
            ttl=None,
        )

        assert not entry.is_expired()

    def test_is_expired_with_custom_now(self) -> None:
        """Test is_expired with custom now time."""
        cached_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_at,
            cached_at=cached_at,
            ttl=300,
        )

        # 200 seconds later - not expired
        now1 = datetime(2025, 1, 1, 12, 3, 20, tzinfo=UTC)
        assert not entry.is_expired(now1)

        # 400 seconds later - expired
        now2 = datetime(2025, 1, 1, 12, 6, 40, tzinfo=UTC)
        assert entry.is_expired(now2)

    def test_is_current_same_version(self) -> None:
        """Test entry is current when versions match."""
        version = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=version,
        )

        assert entry.is_current(version)

    def test_is_current_newer_version(self) -> None:
        """Test entry is current when cached version is newer."""
        cached_version = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        current_version = datetime(2025, 1, 1, 11, 0, 0, tzinfo=UTC)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_version,
        )

        assert entry.is_current(current_version)

    def test_is_current_stale(self) -> None:
        """Test entry is not current when source is newer."""
        cached_version = datetime(2025, 1, 1, 11, 0, 0, tzinfo=UTC)
        current_version = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_version,
        )

        assert not entry.is_current(current_version)

    def test_is_current_with_string_version(self) -> None:
        """Test is_current handles string versions."""
        cached_version = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_version,
        )

        assert entry.is_current("2025-01-01T11:00:00+00:00")
        assert not entry.is_current("2025-01-01T13:00:00+00:00")

    def test_is_stale_inverse_of_is_current(self) -> None:
        """Test is_stale is inverse of is_current."""
        cached_version = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        current_version = datetime(2025, 1, 1, 13, 0, 0, tzinfo=UTC)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_version,
        )

        assert entry.is_stale(current_version) != entry.is_current(current_version)

    def test_project_gid_for_dataframe(self) -> None:
        """Test project_gid is set for dataframe entries."""
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.DATAFRAME,
            version=datetime.now(UTC),
            project_gid="project_456",
        )

        assert entry.project_gid == "project_456"

    def test_metadata_default_empty(self) -> None:
        """Test metadata defaults to empty dict."""
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
        )

        assert entry.metadata == {}

    def test_metadata_custom(self) -> None:
        """Test custom metadata."""
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
            metadata={"source": "api", "count": 5},
        )

        assert entry.metadata["source"] == "api"
        assert entry.metadata["count"] == 5


class TestParseDatetime:
    """Tests for _parse_datetime helper."""

    def test_parse_iso_with_timezone(self) -> None:
        """Test parsing ISO format with timezone."""
        result = _parse_datetime("2025-01-15T10:30:00+00:00")
        assert result == datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)

    def test_parse_iso_with_z_suffix(self) -> None:
        """Test parsing ISO format with Z suffix."""
        result = _parse_datetime("2025-01-15T10:30:00Z")
        assert result == datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)

    def test_parse_iso_without_timezone(self) -> None:
        """Test parsing ISO format without timezone (assumes UTC)."""
        result = _parse_datetime("2025-01-15T10:30:00")
        assert result.tzinfo == UTC
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_parse_iso_with_microseconds(self) -> None:
        """Test parsing ISO format with microseconds."""
        result = _parse_datetime("2025-01-15T10:30:00.123456+00:00")
        assert result.microsecond == 123456

    def test_parse_invalid_raises_error(self) -> None:
        """Test parsing invalid format raises ValueError."""
        with pytest.raises(ValueError):
            _parse_datetime("not a date")
