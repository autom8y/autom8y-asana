"""Tests for BaseClient cache helper methods.

Per TDD-CACHE-INTEGRATION Section 9.1: Unit tests for BaseClient cache helpers.
Covers get/set/invalidate operations, graceful degradation, and error handling.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from autom8_asana._defaults.cache import InMemoryCacheProvider, NullCacheProvider
from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.clients.base import BaseClient
from autom8_asana.config import AsanaConfig, CacheConfig


class TestBaseClientCacheGet:
    """Tests for BaseClient._cache_get()."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_http = MagicMock()
        self.mock_auth = MagicMock()
        self.config = AsanaConfig(cache=CacheConfig(enabled=True))
        self.cache_provider = InMemoryCacheProvider(default_ttl=300)
        self.client = BaseClient(
            http=self.mock_http,
            config=self.config,
            auth_provider=self.mock_auth,
            cache_provider=self.cache_provider,
        )

    def test_returns_none_when_no_cache_provider(self) -> None:
        """Returns None when cache provider is None."""
        client = BaseClient(
            http=self.mock_http,
            config=self.config,
            auth_provider=self.mock_auth,
            cache_provider=None,
        )

        result = client._cache_get("123", EntryType.TASK)

        assert result is None

    def test_returns_cached_entry_on_hit(self) -> None:
        """Returns CacheEntry when cache hit occurs."""
        # Store an entry first
        entry = CacheEntry(
            key="123",
            data={"gid": "123", "name": "Test Task"},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
            ttl=300,
        )
        self.cache_provider.set_versioned("123", entry)

        result = self.client._cache_get("123", EntryType.TASK)

        assert result is not None
        assert result.key == "123"
        assert result.data["name"] == "Test Task"

    def test_returns_none_on_cache_miss(self) -> None:
        """Returns None when entry not in cache."""
        result = self.client._cache_get("nonexistent", EntryType.TASK)

        assert result is None

    def test_returns_none_when_entry_expired(self) -> None:
        """Returns None when cached entry has expired."""
        # Store an entry with very short TTL
        entry = CacheEntry(
            key="123",
            data={"gid": "123", "name": "Test Task"},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
            ttl=0,  # Already expired
            cached_at=datetime(2020, 1, 1, tzinfo=UTC),  # In the past
        )
        self.cache_provider.set_versioned("123", entry)

        result = self.client._cache_get("123", EntryType.TASK)

        assert result is None

    def test_graceful_degradation_on_exception(self) -> None:
        """Returns None and logs warning when cache raises exception."""
        mock_cache = MagicMock()
        mock_cache.get_versioned.side_effect = Exception("Cache connection failed")

        client = BaseClient(
            http=self.mock_http,
            config=self.config,
            auth_provider=self.mock_auth,
            cache_provider=mock_cache,
        )

        with patch("autom8_asana.clients.base.logger") as mock_logger:
            result = client._cache_get("123", EntryType.TASK)

        assert result is None
        mock_logger.warning.assert_called_once()
        assert "Cache get failed" in str(mock_logger.warning.call_args)


class TestBaseClientCacheSet:
    """Tests for BaseClient._cache_set()."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_http = MagicMock()
        self.mock_auth = MagicMock()
        self.config = AsanaConfig(cache=CacheConfig(enabled=True))
        self.cache_provider = InMemoryCacheProvider(default_ttl=300)
        self.client = BaseClient(
            http=self.mock_http,
            config=self.config,
            auth_provider=self.mock_auth,
            cache_provider=self.cache_provider,
        )

    def test_does_nothing_when_no_cache_provider(self) -> None:
        """Silently returns when cache provider is None."""
        client = BaseClient(
            http=self.mock_http,
            config=self.config,
            auth_provider=self.mock_auth,
            cache_provider=None,
        )

        # Should not raise
        client._cache_set("123", {"gid": "123"}, EntryType.TASK)

    def test_stores_entry_in_cache(self) -> None:
        """Stores entry in cache and can be retrieved."""
        data = {
            "gid": "123",
            "name": "Test Task",
            "modified_at": "2025-01-01T00:00:00Z",
        }

        self.client._cache_set("123", data, EntryType.TASK)

        # Retrieve and verify
        entry = self.cache_provider.get_versioned("123", EntryType.TASK)
        assert entry is not None
        assert entry.data["name"] == "Test Task"

    def test_uses_config_ttl_when_not_specified(self) -> None:
        """Uses default TTL from config when ttl parameter is None."""
        # Set custom TTL in config
        config = AsanaConfig(cache=CacheConfig(enabled=True))
        config.cache._ttl = config.cache.ttl
        config.cache.ttl.default_ttl = 600

        client = BaseClient(
            http=self.mock_http,
            config=config,
            auth_provider=self.mock_auth,
            cache_provider=self.cache_provider,
        )

        data = {"gid": "123", "name": "Test Task"}
        client._cache_set("123", data, EntryType.TASK)

        entry = self.cache_provider.get_versioned("123", EntryType.TASK)
        assert entry is not None
        assert entry.ttl == 600

    def test_uses_explicit_ttl_when_specified(self) -> None:
        """Uses explicit TTL parameter over config default."""
        data = {"gid": "123", "name": "Test Task"}

        self.client._cache_set("123", data, EntryType.TASK, ttl=900)

        entry = self.cache_provider.get_versioned("123", EntryType.TASK)
        assert entry is not None
        assert entry.ttl == 900

    def test_extracts_version_from_modified_at(self) -> None:
        """Extracts version timestamp from modified_at field."""
        data = {"gid": "123", "modified_at": "2025-06-15T10:30:00Z"}

        self.client._cache_set("123", data, EntryType.TASK)

        entry = self.cache_provider.get_versioned("123", EntryType.TASK)
        assert entry is not None
        assert entry.version.year == 2025
        assert entry.version.month == 6
        assert entry.version.day == 15

    def test_uses_current_time_when_no_modified_at(self) -> None:
        """Uses current time as version when modified_at not present."""
        data = {"gid": "123", "name": "Test Task"}
        before = datetime.now(UTC)

        self.client._cache_set("123", data, EntryType.TASK)

        after = datetime.now(UTC)
        entry = self.cache_provider.get_versioned("123", EntryType.TASK)
        assert entry is not None
        assert before <= entry.version <= after

    def test_graceful_degradation_on_exception(self) -> None:
        """Logs warning and continues when cache raises exception."""
        mock_cache = MagicMock()
        mock_cache.set_versioned.side_effect = Exception("Cache write failed")

        client = BaseClient(
            http=self.mock_http,
            config=self.config,
            auth_provider=self.mock_auth,
            cache_provider=mock_cache,
        )

        with patch("autom8_asana.clients.base.logger") as mock_logger:
            # Should not raise
            client._cache_set("123", {"gid": "123"}, EntryType.TASK)

        mock_logger.warning.assert_called_once()
        assert "Cache set failed" in str(mock_logger.warning.call_args)


class TestBaseClientCacheInvalidate:
    """Tests for BaseClient._cache_invalidate()."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_http = MagicMock()
        self.mock_auth = MagicMock()
        self.config = AsanaConfig(cache=CacheConfig(enabled=True))
        self.cache_provider = InMemoryCacheProvider(default_ttl=300)
        self.client = BaseClient(
            http=self.mock_http,
            config=self.config,
            auth_provider=self.mock_auth,
            cache_provider=self.cache_provider,
        )

    def test_does_nothing_when_no_cache_provider(self) -> None:
        """Silently returns when cache provider is None."""
        client = BaseClient(
            http=self.mock_http,
            config=self.config,
            auth_provider=self.mock_auth,
            cache_provider=None,
        )

        # Should not raise
        client._cache_invalidate("123")

    def test_invalidates_entry(self) -> None:
        """Invalidates entry so it no longer exists in cache."""
        # Store an entry first
        entry = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
        )
        self.cache_provider.set_versioned("123", entry)

        # Verify it exists
        assert self.cache_provider.get_versioned("123", EntryType.TASK) is not None

        # Invalidate
        self.client._cache_invalidate("123", [EntryType.TASK])

        # Verify it's gone
        assert self.cache_provider.get_versioned("123", EntryType.TASK) is None

    def test_invalidates_specific_entry_types(self) -> None:
        """Invalidates only specified entry types."""
        # Store entries of different types
        task_entry = CacheEntry(
            key="123",
            data={"gid": "123", "type": "task"},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
        )
        subtasks_entry = CacheEntry(
            key="123",
            data={"gid": "123", "type": "subtasks"},
            entry_type=EntryType.SUBTASKS,
            version=datetime.now(UTC),
        )
        self.cache_provider.set_versioned("123", task_entry)
        self.cache_provider.set_versioned("123", subtasks_entry)

        # Invalidate only TASK
        self.client._cache_invalidate("123", [EntryType.TASK])

        # TASK should be gone, SUBTASKS should remain
        assert self.cache_provider.get_versioned("123", EntryType.TASK) is None
        assert self.cache_provider.get_versioned("123", EntryType.SUBTASKS) is not None

    def test_graceful_degradation_on_exception(self) -> None:
        """Logs warning and continues when cache raises exception."""
        mock_cache = MagicMock()
        mock_cache.invalidate.side_effect = Exception("Cache invalidate failed")

        client = BaseClient(
            http=self.mock_http,
            config=self.config,
            auth_provider=self.mock_auth,
            cache_provider=mock_cache,
        )

        with patch("autom8_asana.clients.base.logger") as mock_logger:
            # Should not raise
            client._cache_invalidate("123")

        mock_logger.warning.assert_called_once()
        assert "Cache invalidate failed" in str(mock_logger.warning.call_args)


class TestBaseClientParseModifiedAt:
    """Tests for BaseClient._parse_modified_at()."""

    def test_parses_iso_string_with_z_suffix(self) -> None:
        """Parses ISO string with Z timezone suffix."""
        result = BaseClient._parse_modified_at("2025-06-15T10:30:00Z")

        assert result.year == 2025
        assert result.month == 6
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.tzinfo == UTC

    def test_parses_iso_string_with_offset(self) -> None:
        """Parses ISO string with explicit timezone offset."""
        result = BaseClient._parse_modified_at("2025-06-15T10:30:00+00:00")

        assert result.year == 2025
        assert result.tzinfo is not None

    def test_parses_naive_datetime_string(self) -> None:
        """Parses naive datetime string and adds UTC timezone."""
        result = BaseClient._parse_modified_at("2025-06-15T10:30:00")

        assert result.year == 2025
        assert result.tzinfo == UTC

    def test_passes_through_datetime_with_timezone(self) -> None:
        """Passes through datetime that already has timezone."""
        dt = datetime(2025, 6, 15, 10, 30, tzinfo=UTC)

        result = BaseClient._parse_modified_at(dt)

        assert result is dt

    def test_adds_utc_to_naive_datetime(self) -> None:
        """Adds UTC timezone to naive datetime."""
        dt = datetime(2025, 6, 15, 10, 30)

        result = BaseClient._parse_modified_at(dt)

        assert result.tzinfo == UTC
        assert result.year == 2025

    def test_parses_iso_string_with_microseconds(self) -> None:
        """Parses ISO string with microseconds."""
        result = BaseClient._parse_modified_at("2025-06-15T10:30:00.123456Z")

        assert result.year == 2025
        assert result.microsecond == 123456


class TestBaseClientWithNullCacheProvider:
    """Tests for BaseClient with NullCacheProvider."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_http = MagicMock()
        self.mock_auth = MagicMock()
        self.config = AsanaConfig(cache=CacheConfig(enabled=False))
        self.client = BaseClient(
            http=self.mock_http,
            config=self.config,
            auth_provider=self.mock_auth,
            cache_provider=NullCacheProvider(),
        )

    def test_cache_get_returns_none(self) -> None:
        """Cache get always returns None with NullCacheProvider."""
        result = self.client._cache_get("123", EntryType.TASK)
        assert result is None

    def test_cache_set_does_nothing(self) -> None:
        """Cache set does nothing with NullCacheProvider."""
        # Should not raise
        self.client._cache_set("123", {"gid": "123"}, EntryType.TASK)

        # Verify nothing was stored
        result = self.client._cache_get("123", EntryType.TASK)
        assert result is None

    def test_cache_invalidate_does_nothing(self) -> None:
        """Cache invalidate does nothing with NullCacheProvider."""
        # Should not raise
        self.client._cache_invalidate("123")
