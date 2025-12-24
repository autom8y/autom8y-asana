"""Tests for StalenessCheckCoordinator.

Per TDD-CACHE-LIGHTWEIGHT-STALENESS: Validates TTL extension, changed detection,
and error handling.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.staleness_coordinator import StalenessCheckCoordinator
from autom8_asana.cache.staleness_settings import StalenessCheckSettings


@pytest.fixture
def mock_cache_provider() -> MagicMock:
    """Create a mock CacheProvider."""
    provider = MagicMock()
    provider.set_versioned = MagicMock()
    provider.invalidate = MagicMock()
    return provider


@pytest.fixture
def mock_batch_client() -> MagicMock:
    """Create a mock BatchClient."""
    client = MagicMock()
    client.execute_async = AsyncMock(return_value=[])
    return client


@pytest.fixture
def coordinator(
    mock_cache_provider: MagicMock, mock_batch_client: MagicMock
) -> StalenessCheckCoordinator:
    """Create a StalenessCheckCoordinator with mocks."""
    return StalenessCheckCoordinator(
        cache_provider=mock_cache_provider,
        batch_client=mock_batch_client,
        settings=StalenessCheckSettings(
            enabled=True,
            base_ttl=300,
            max_ttl=86400,
            coalesce_window_ms=1,  # Fast for testing
            max_batch_size=100,
        ),
    )


def make_entry(
    gid: str,
    modified_at: str = "2025-12-23T10:00:00.000Z",
    ttl: int = 300,
    extension_count: int = 0,
) -> CacheEntry:
    """Create a test CacheEntry."""
    version = datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
    return CacheEntry(
        key=gid,
        data={"gid": gid, "name": f"Task {gid}"},
        entry_type=EntryType.TASK,
        version=version,
        cached_at=datetime.now(timezone.utc),
        ttl=ttl,
        metadata={"extension_count": extension_count} if extension_count > 0 else {},
    )


class TestStalenessCheckCoordinator:
    """Tests for StalenessCheckCoordinator."""

    @pytest.mark.asyncio
    async def test_unchanged_extends_ttl(
        self, coordinator: StalenessCheckCoordinator
    ) -> None:
        """Test that unchanged entity gets TTL extended."""
        entry = make_entry("123", modified_at="2025-12-23T10:00:00.000Z")

        # Mock coalescer to return same modified_at (unchanged)
        with patch.object(
            coordinator._coalescer,
            "request_check_async",
            return_value="2025-12-23T10:00:00.000Z",
        ):
            result = await coordinator.check_and_get_async(entry)

        # Should return extended entry
        assert result is not None
        assert result.key == "123"
        assert result.ttl == 600  # 300 * 2^1
        assert result.metadata.get("extension_count") == 1

    @pytest.mark.asyncio
    async def test_changed_returns_none(
        self, coordinator: StalenessCheckCoordinator
    ) -> None:
        """Test that changed entity returns None."""
        entry = make_entry("123", modified_at="2025-12-23T10:00:00.000Z")

        # Mock coalescer to return different modified_at (changed)
        with patch.object(
            coordinator._coalescer,
            "request_check_async",
            return_value="2025-12-23T12:00:00.000Z",  # 2 hours later
        ):
            result = await coordinator.check_and_get_async(entry)

        # Should return None
        assert result is None

        # Stats should track change
        stats = coordinator.get_extension_stats()
        assert stats["changed_count"] == 1

    @pytest.mark.asyncio
    async def test_error_returns_none_and_invalidates(
        self,
        coordinator: StalenessCheckCoordinator,
        mock_cache_provider: MagicMock,
    ) -> None:
        """Test that error/deleted returns None and invalidates cache."""
        entry = make_entry("123")

        # Mock coalescer to return None (error/deleted)
        with patch.object(
            coordinator._coalescer,
            "request_check_async",
            return_value=None,
        ):
            result = await coordinator.check_and_get_async(entry)

        # Should return None
        assert result is None

        # Should invalidate cache
        mock_cache_provider.invalidate.assert_called_once_with("123", [EntryType.TASK])

        # Stats should track error
        stats = coordinator.get_extension_stats()
        assert stats["error_count"] == 1

    @pytest.mark.asyncio
    async def test_exception_graceful_degradation(
        self, coordinator: StalenessCheckCoordinator
    ) -> None:
        """Test that exceptions are handled gracefully (FR-DEGRADE-006)."""
        entry = make_entry("123")

        # Mock coalescer to raise exception
        with patch.object(
            coordinator._coalescer,
            "request_check_async",
            side_effect=Exception("Network error"),
        ):
            result = await coordinator.check_and_get_async(entry)

        # Should return None (not raise)
        assert result is None

        # Stats should track error
        stats = coordinator.get_extension_stats()
        assert stats["error_count"] == 1

    @pytest.mark.asyncio
    async def test_disabled_returns_none(
        self,
        mock_cache_provider: MagicMock,
        mock_batch_client: MagicMock,
    ) -> None:
        """Test that disabled coordinator returns None without checking."""
        coordinator = StalenessCheckCoordinator(
            cache_provider=mock_cache_provider,
            batch_client=mock_batch_client,
            settings=StalenessCheckSettings(enabled=False),
        )

        entry = make_entry("123")
        result = await coordinator.check_and_get_async(entry)

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_update_on_extension(
        self,
        coordinator: StalenessCheckCoordinator,
        mock_cache_provider: MagicMock,
    ) -> None:
        """Test that extended entry is stored in cache."""
        entry = make_entry("123", modified_at="2025-12-23T10:00:00.000Z")

        with patch.object(
            coordinator._coalescer,
            "request_check_async",
            return_value="2025-12-23T10:00:00.000Z",
        ):
            result = await coordinator.check_and_get_async(entry)

        # Should store extended entry
        mock_cache_provider.set_versioned.assert_called_once()
        call_args = mock_cache_provider.set_versioned.call_args
        assert call_args[0][0] == "123"  # key
        stored_entry = call_args[0][1]
        assert stored_entry.ttl == 600  # Extended TTL

    @pytest.mark.asyncio
    async def test_cache_update_failure_still_returns_entry(
        self,
        coordinator: StalenessCheckCoordinator,
        mock_cache_provider: MagicMock,
    ) -> None:
        """Test that cache update failure still returns extended entry."""
        entry = make_entry("123", modified_at="2025-12-23T10:00:00.000Z")
        mock_cache_provider.set_versioned.side_effect = Exception("Cache error")

        with patch.object(
            coordinator._coalescer,
            "request_check_async",
            return_value="2025-12-23T10:00:00.000Z",
        ):
            result = await coordinator.check_and_get_async(entry)

        # Should still return extended entry
        assert result is not None
        assert result.ttl == 600

    @pytest.mark.asyncio
    async def test_stats_tracking(
        self, coordinator: StalenessCheckCoordinator
    ) -> None:
        """Test that stats are tracked correctly."""
        entry = make_entry("123", modified_at="2025-12-23T10:00:00.000Z")

        with patch.object(
            coordinator._coalescer,
            "request_check_async",
            return_value="2025-12-23T10:00:00.000Z",
        ):
            await coordinator.check_and_get_async(entry)

        stats = coordinator.get_extension_stats()
        assert stats["total_checks"] == 1
        assert stats["unchanged_count"] == 1
        assert stats["api_calls_saved"] == 1
        assert stats["changed_count"] == 0
        assert stats["error_count"] == 0


class TestTTLExtension:
    """Tests for TTL extension algorithm."""

    @pytest.mark.asyncio
    async def test_first_extension(
        self, coordinator: StalenessCheckCoordinator
    ) -> None:
        """Test first TTL extension (base * 2^1 = 600)."""
        entry = make_entry("123", ttl=300, extension_count=0)

        with patch.object(
            coordinator._coalescer,
            "request_check_async",
            return_value="2025-12-23T10:00:00.000Z",
        ):
            result = await coordinator.check_and_get_async(entry)

        assert result is not None
        assert result.ttl == 600  # 300 * 2
        assert result.metadata.get("extension_count") == 1

    @pytest.mark.asyncio
    async def test_second_extension(
        self, coordinator: StalenessCheckCoordinator
    ) -> None:
        """Test second TTL extension (base * 2^2 = 1200)."""
        entry = make_entry("123", ttl=600, extension_count=1)

        with patch.object(
            coordinator._coalescer,
            "request_check_async",
            return_value="2025-12-23T10:00:00.000Z",
        ):
            result = await coordinator.check_and_get_async(entry)

        assert result is not None
        assert result.ttl == 1200  # 300 * 4
        assert result.metadata.get("extension_count") == 2

    @pytest.mark.asyncio
    async def test_ttl_ceiling_enforced(
        self, coordinator: StalenessCheckCoordinator
    ) -> None:
        """Test that max_ttl ceiling is enforced (FR-TTL-002)."""
        # At count 8: 300 * 2^9 = 153600, but ceiling is 86400
        entry = make_entry("123", ttl=76800, extension_count=8)

        with patch.object(
            coordinator._coalescer,
            "request_check_async",
            return_value="2025-12-23T10:00:00.000Z",
        ):
            result = await coordinator.check_and_get_async(entry)

        assert result is not None
        assert result.ttl == 86400  # Ceiling
        assert result.metadata.get("extension_count") == 9

    @pytest.mark.asyncio
    async def test_cached_at_reset_on_extension(
        self, coordinator: StalenessCheckCoordinator
    ) -> None:
        """Test that cached_at is reset on extension."""
        old_cached_at = datetime.now(timezone.utc) - timedelta(hours=1)
        entry = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime.fromisoformat("2025-12-23T10:00:00+00:00"),
            cached_at=old_cached_at,
            ttl=300,
        )

        with patch.object(
            coordinator._coalescer,
            "request_check_async",
            return_value="2025-12-23T10:00:00.000Z",
        ):
            result = await coordinator.check_and_get_async(entry)

        assert result is not None
        # cached_at should be reset to now (not old time)
        assert result.cached_at > old_cached_at

    @pytest.mark.asyncio
    async def test_version_preserved_on_extension(
        self, coordinator: StalenessCheckCoordinator
    ) -> None:
        """Test that version is preserved on extension (FR-TTL-006)."""
        original_version = datetime.fromisoformat("2025-12-23T10:00:00+00:00")
        entry = CacheEntry(
            key="123",
            data={"gid": "123", "name": "Original"},
            entry_type=EntryType.TASK,
            version=original_version,
            cached_at=datetime.now(timezone.utc),
            ttl=300,
        )

        with patch.object(
            coordinator._coalescer,
            "request_check_async",
            return_value="2025-12-23T10:00:00.000Z",
        ):
            result = await coordinator.check_and_get_async(entry)

        assert result is not None
        assert result.version == original_version  # Preserved
        assert result.data == {"gid": "123", "name": "Original"}  # Preserved

    @pytest.mark.asyncio
    async def test_entry_immutability(
        self, coordinator: StalenessCheckCoordinator
    ) -> None:
        """Test that original entry is not mutated (FR-TTL-006)."""
        entry = make_entry("123", ttl=300, extension_count=0)
        original_ttl = entry.ttl
        original_metadata = dict(entry.metadata)

        with patch.object(
            coordinator._coalescer,
            "request_check_async",
            return_value="2025-12-23T10:00:00.000Z",
        ):
            result = await coordinator.check_and_get_async(entry)

        # Original entry should be unchanged
        assert entry.ttl == original_ttl
        assert entry.metadata == original_metadata

        # Result should be a different object
        assert result is not entry
        assert result.ttl != entry.ttl


class TestStalenessCheckSettings:
    """Tests for StalenessCheckSettings."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        settings = StalenessCheckSettings()
        assert settings.enabled is True
        assert settings.base_ttl == 300
        assert settings.max_ttl == 86400
        assert settings.coalesce_window_ms == 50
        assert settings.max_batch_size == 100

    def test_custom_settings(self) -> None:
        """Test custom settings."""
        settings = StalenessCheckSettings(
            enabled=False,
            base_ttl=600,
            max_ttl=43200,
            coalesce_window_ms=100,
            max_batch_size=50,
        )
        assert settings.enabled is False
        assert settings.base_ttl == 600
        assert settings.max_ttl == 43200
        assert settings.coalesce_window_ms == 100
        assert settings.max_batch_size == 50

    def test_validation_base_ttl_positive(self) -> None:
        """Test that base_ttl must be positive."""
        with pytest.raises(ValueError, match="base_ttl must be positive"):
            StalenessCheckSettings(base_ttl=0)

        with pytest.raises(ValueError, match="base_ttl must be positive"):
            StalenessCheckSettings(base_ttl=-1)

    def test_validation_max_ttl_positive(self) -> None:
        """Test that max_ttl must be positive."""
        with pytest.raises(ValueError, match="max_ttl must be positive"):
            StalenessCheckSettings(max_ttl=0)

    def test_validation_max_ttl_gte_base_ttl(self) -> None:
        """Test that max_ttl must be >= base_ttl."""
        with pytest.raises(ValueError, match="max_ttl.*must be >= base_ttl"):
            StalenessCheckSettings(base_ttl=600, max_ttl=300)

    def test_validation_coalesce_window_non_negative(self) -> None:
        """Test that coalesce_window_ms must be non-negative."""
        # 0 is allowed (no coalescing)
        settings = StalenessCheckSettings(coalesce_window_ms=0)
        assert settings.coalesce_window_ms == 0

        with pytest.raises(ValueError, match="coalesce_window_ms must be non-negative"):
            StalenessCheckSettings(coalesce_window_ms=-1)

    def test_validation_max_batch_size_positive(self) -> None:
        """Test that max_batch_size must be positive."""
        with pytest.raises(ValueError, match="max_batch_size must be positive"):
            StalenessCheckSettings(max_batch_size=0)

    def test_calculate_extended_ttl(self) -> None:
        """Test TTL calculation at various extension counts."""
        settings = StalenessCheckSettings(base_ttl=300, max_ttl=86400)

        # Per ADR-0133 TTL progression table
        assert settings.calculate_extended_ttl(0) == 300  # base
        assert settings.calculate_extended_ttl(1) == 600  # 300 * 2
        assert settings.calculate_extended_ttl(2) == 1200  # 300 * 4
        assert settings.calculate_extended_ttl(3) == 2400  # 300 * 8
        assert settings.calculate_extended_ttl(4) == 4800  # 300 * 16
        assert settings.calculate_extended_ttl(5) == 9600  # 300 * 32
        assert settings.calculate_extended_ttl(6) == 19200  # 300 * 64
        assert settings.calculate_extended_ttl(7) == 38400  # 300 * 128
        assert settings.calculate_extended_ttl(8) == 76800  # 300 * 256
        assert settings.calculate_extended_ttl(9) == 86400  # ceiling

    def test_calculate_extended_ttl_ceiling(self) -> None:
        """Test that TTL is capped at max_ttl."""
        settings = StalenessCheckSettings(base_ttl=300, max_ttl=86400)

        # High extension counts should all return ceiling
        for count in [9, 10, 20, 100]:
            assert settings.calculate_extended_ttl(count) == 86400

    def test_calculate_extended_ttl_negative_count_raises(self) -> None:
        """Test that negative extension count raises."""
        settings = StalenessCheckSettings()
        with pytest.raises(ValueError, match="extension_count must be non-negative"):
            settings.calculate_extended_ttl(-1)
