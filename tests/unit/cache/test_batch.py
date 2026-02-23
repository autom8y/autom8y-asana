"""Tests for batch modification checking with TTL caching."""

import asyncio
import os
import socket
import threading
import time
from unittest.mock import AsyncMock, patch

import pytest

from autom8_asana.cache.integration.batch import (
    DEFAULT_MODIFICATION_CHECK_TTL,
    ModificationCheck,
    ModificationCheckCache,
    fetch_task_modifications,
    get_modification_cache,
    reset_modification_cache,
    ttl_cached_modifications,
)


class TestModificationCheck:
    """Tests for ModificationCheck dataclass."""

    def test_creation(self) -> None:
        """Test ModificationCheck creation."""
        check = ModificationCheck(
            gid="123",
            modified_at="2025-01-01T00:00:00Z",
            checked_at=time.monotonic(),
        )

        assert check.gid == "123"
        assert check.modified_at == "2025-01-01T00:00:00Z"
        assert isinstance(check.checked_at, float)

    def test_immutability(self) -> None:
        """Test ModificationCheck is immutable."""
        check = ModificationCheck(
            gid="123",
            modified_at="2025-01-01T00:00:00Z",
            checked_at=time.monotonic(),
        )

        with pytest.raises(AttributeError):
            check.gid = "456"  # type: ignore[misc]


class TestModificationCheckCache:
    """Tests for ModificationCheckCache class."""

    def test_default_ttl(self) -> None:
        """Test default TTL is 25 seconds per ADR-0018."""
        cache = ModificationCheckCache()
        assert cache.ttl == DEFAULT_MODIFICATION_CHECK_TTL
        assert cache.ttl == 25.0

    def test_custom_ttl(self) -> None:
        """Test custom TTL setting."""
        cache = ModificationCheckCache(ttl=60.0)
        assert cache.ttl == 60.0

    def test_set_and_get(self) -> None:
        """Test basic set and get operations."""
        cache = ModificationCheckCache()
        cache.set("123", "2025-01-01T00:00:00Z")

        check = cache.get("123")
        assert check is not None
        assert check.gid == "123"
        assert check.modified_at == "2025-01-01T00:00:00Z"

    def test_get_missing(self) -> None:
        """Test get returns None for missing entry."""
        cache = ModificationCheckCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self) -> None:
        """Test entries expire after TTL."""
        cache = ModificationCheckCache(ttl=0.1)  # 100ms TTL
        cache.set("123", "2025-01-01T00:00:00Z")

        assert cache.get("123") is not None
        time.sleep(0.15)  # Wait for expiration
        assert cache.get("123") is None

    def test_set_many(self) -> None:
        """Test batch set operation."""
        cache = ModificationCheckCache()
        cache.set_many(
            {
                "123": "2025-01-01T00:00:00Z",
                "456": "2025-01-02T00:00:00Z",
                "789": "2025-01-03T00:00:00Z",
            }
        )

        assert cache.get("123") is not None
        assert cache.get("456") is not None
        assert cache.get("789") is not None

    def test_get_many(self) -> None:
        """Test batch get operation."""
        cache = ModificationCheckCache()
        cache.set("123", "2025-01-01T00:00:00Z")
        cache.set("456", "2025-01-02T00:00:00Z")

        cached, uncached = cache.get_many(["123", "456", "789"])

        assert cached == {"123": "2025-01-01T00:00:00Z", "456": "2025-01-02T00:00:00Z"}
        assert uncached == ["789"]

    def test_get_many_with_expired(self) -> None:
        """Test get_many handles expired entries."""
        cache = ModificationCheckCache(ttl=0.1)
        cache.set("123", "2025-01-01T00:00:00Z")

        time.sleep(0.15)
        cache.set("456", "2025-01-02T00:00:00Z")

        cached, uncached = cache.get_many(["123", "456"])

        assert cached == {"456": "2025-01-02T00:00:00Z"}
        assert uncached == ["123"]

    def test_clear(self) -> None:
        """Test clear removes all entries."""
        cache = ModificationCheckCache()
        cache.set_many({"123": "v1", "456": "v2"})

        cache.clear()

        assert cache.size() == 0
        assert cache.get("123") is None
        assert cache.get("456") is None

    def test_size(self) -> None:
        """Test size returns correct count."""
        cache = ModificationCheckCache()
        assert cache.size() == 0

        cache.set("123", "v1")
        assert cache.size() == 1

        cache.set("456", "v2")
        assert cache.size() == 2

    def test_cleanup_expired(self) -> None:
        """Test cleanup_expired removes old entries."""
        cache = ModificationCheckCache(ttl=0.1)
        cache.set("123", "v1")
        cache.set("456", "v2")

        time.sleep(0.15)
        cache.set("789", "v3")

        removed = cache.cleanup_expired()

        assert removed == 2
        assert cache.size() == 1
        assert cache.get("789") is not None

    def test_run_id_generation(self) -> None:
        """Test run ID is generated."""
        cache = ModificationCheckCache()
        assert cache.run_id is not None
        assert len(cache.run_id) > 0

    def test_custom_run_id(self) -> None:
        """Test custom run ID is accepted."""
        cache = ModificationCheckCache(run_id="custom-run-123")
        assert cache.run_id == "custom-run-123"

    def test_run_id_uses_ecs_metadata(self) -> None:
        """Test run ID prefers ECS metadata when available."""
        with patch.dict(
            os.environ, {"ECS_CONTAINER_METADATA_URI_V4": "ecs://task/123"}
        ):
            cache = ModificationCheckCache()
            assert cache.run_id == "ecs://task/123"

    def test_run_id_uses_ecs_task_id(self) -> None:
        """Test run ID uses ECS_TASK_ID when available."""
        with patch.dict(
            os.environ,
            {"ECS_TASK_ID": "task-456"},
            clear=False,
        ):
            # Clear the V4 URI to test fallback
            env = os.environ.copy()
            env.pop("ECS_CONTAINER_METADATA_URI_V4", None)
            env["ECS_TASK_ID"] = "task-456"

            with patch.dict(os.environ, env, clear=True):
                cache = ModificationCheckCache()
                assert cache.run_id == "task-456"

    def test_run_id_fallback_to_hostname(self) -> None:
        """Test run ID falls back to hostname:pid."""
        with patch.dict(os.environ, {}, clear=True):
            cache = ModificationCheckCache()
            expected_prefix = f"{socket.gethostname()}:{os.getpid()}"
            assert cache.run_id == expected_prefix

    def test_thread_safety(self) -> None:
        """Test cache is thread-safe."""
        cache = ModificationCheckCache()
        errors: list[Exception] = []

        def writer(prefix: str) -> None:
            try:
                for i in range(100):
                    cache.set(f"{prefix}_{i}", f"value_{i}")
            except Exception as e:
                errors.append(e)

        def reader(prefix: str) -> None:
            try:
                for i in range(100):
                    cache.get(f"{prefix}_{i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=("a",)),
            threading.Thread(target=writer, args=("b",)),
            threading.Thread(target=reader, args=("a",)),
            threading.Thread(target=reader, args=("b",)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            if t.is_alive():
                raise AssertionError(f"Thread {t.name} did not complete within timeout")

        assert errors == []


class TestGlobalModificationCache:
    """Tests for global modification cache functions."""

    def setup_method(self) -> None:
        """Reset global cache before each test."""
        reset_modification_cache()

    def teardown_method(self) -> None:
        """Reset global cache after each test."""
        reset_modification_cache()

    def test_get_creates_singleton(self) -> None:
        """Test get_modification_cache creates singleton."""
        cache1 = get_modification_cache()
        cache2 = get_modification_cache()

        assert cache1 is cache2

    def test_reset_clears_singleton(self) -> None:
        """Test reset_modification_cache clears singleton."""
        cache1 = get_modification_cache()
        cache1.set("123", "v1")

        reset_modification_cache()

        cache2 = get_modification_cache()
        assert cache2.get("123") is None

    def test_ttl_only_used_on_creation(self) -> None:
        """Test TTL is only used when creating new cache."""
        cache1 = get_modification_cache(ttl=60.0)
        cache2 = get_modification_cache(ttl=120.0)  # Should be ignored

        assert cache1 is cache2
        assert cache1.ttl == 60.0


class TestFetchTaskModifications:
    """Tests for fetch_task_modifications function."""

    def setup_method(self) -> None:
        """Reset global cache before each test."""
        reset_modification_cache()

    def teardown_method(self) -> None:
        """Reset global cache after each test."""
        reset_modification_cache()

    @pytest.mark.asyncio
    async def test_fetches_all_on_empty_cache(self) -> None:
        """Test all GIDs are fetched when cache is empty."""
        mock_api = AsyncMock(
            return_value={
                "123": "2025-01-01T00:00:00Z",
                "456": "2025-01-02T00:00:00Z",
            }
        )

        result = await fetch_task_modifications(["123", "456"], mock_api)

        assert result == {
            "123": "2025-01-01T00:00:00Z",
            "456": "2025-01-02T00:00:00Z",
        }
        mock_api.assert_called_once_with(["123", "456"])

    @pytest.mark.asyncio
    async def test_uses_cache_for_cached_gids(self) -> None:
        """Test cached GIDs are not refetched."""
        # Pre-populate cache
        cache = get_modification_cache()
        cache.set("123", "2025-01-01T00:00:00Z")

        mock_api = AsyncMock(return_value={"456": "2025-01-02T00:00:00Z"})

        result = await fetch_task_modifications(["123", "456"], mock_api)

        assert result == {
            "123": "2025-01-01T00:00:00Z",
            "456": "2025-01-02T00:00:00Z",
        }
        # Only uncached GID should be fetched
        mock_api.assert_called_once_with(["456"])

    @pytest.mark.asyncio
    async def test_no_api_call_when_all_cached(self) -> None:
        """Test no API call when all GIDs are cached."""
        cache = get_modification_cache()
        cache.set_many(
            {
                "123": "2025-01-01T00:00:00Z",
                "456": "2025-01-02T00:00:00Z",
            }
        )

        mock_api = AsyncMock(return_value={})

        result = await fetch_task_modifications(["123", "456"], mock_api)

        assert result == {
            "123": "2025-01-01T00:00:00Z",
            "456": "2025-01-02T00:00:00Z",
        }
        mock_api.assert_not_called()

    @pytest.mark.asyncio
    async def test_caches_fetched_results(self) -> None:
        """Test fetched results are cached."""
        mock_api = AsyncMock(return_value={"123": "2025-01-01T00:00:00Z"})

        await fetch_task_modifications(["123"], mock_api)

        # Verify cached
        cache = get_modification_cache()
        check = cache.get("123")
        assert check is not None
        assert check.modified_at == "2025-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_empty_gids_list(self) -> None:
        """Test with empty GIDs list."""
        mock_api = AsyncMock(return_value={})

        result = await fetch_task_modifications([], mock_api)

        assert result == {}
        mock_api.assert_not_called()

    @pytest.mark.asyncio
    async def test_custom_ttl(self) -> None:
        """Test custom TTL is used."""
        reset_modification_cache()

        mock_api = AsyncMock(return_value={"123": "v1"})

        await fetch_task_modifications(["123"], mock_api, cache_ttl=0.1)

        # Wait for expiration
        await asyncio.sleep(0.15)

        mock_api.reset_mock()
        mock_api.return_value = {"123": "v2"}

        result = await fetch_task_modifications(["123"], mock_api, cache_ttl=0.1)

        assert result["123"] == "v2"
        mock_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_returns_partial_results(self) -> None:
        """Test handling when API returns fewer GIDs than requested."""

        async def mock_api(gids: list[str]) -> dict[str, str]:
            return {gid: "2025-01-01T00:00:00Z" for gid in gids[: len(gids) // 2]}

        result = await fetch_task_modifications(["1", "2", "3", "4"], mock_api)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_api_returns_extra_gids(self) -> None:
        """Test handling when API returns more GIDs than requested."""

        async def mock_api(gids: list[str]) -> dict[str, str]:
            out = {gid: "2025-01-01T00:00:00Z" for gid in gids}
            out["extra_gid"] = "2025-01-01T00:00:00Z"
            return out

        result = await fetch_task_modifications(["1", "2"], mock_api)
        assert "extra_gid" in result


class TestTtlCachedModificationsDecorator:
    """Tests for ttl_cached_modifications decorator."""

    def setup_method(self) -> None:
        """Reset global cache before each test."""
        reset_modification_cache()

    def teardown_method(self) -> None:
        """Reset global cache after each test."""
        reset_modification_cache()

    @pytest.mark.asyncio
    async def test_decorator_caches_results(self) -> None:
        """Test decorator adds caching to function."""
        call_count = 0

        @ttl_cached_modifications(ttl=25.0)
        async def fetch_modifications(gids: list[str]) -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            return {gid: f"v_{gid}" for gid in gids}

        # First call
        result1 = await fetch_modifications(["123", "456"])
        assert call_count == 1

        # Second call - should use cache
        result2 = await fetch_modifications(["123", "456"])
        assert call_count == 1  # No additional call

        assert result1 == result2

    @pytest.mark.asyncio
    async def test_decorator_only_fetches_uncached(self) -> None:
        """Test decorator only passes uncached GIDs to function."""
        fetched_gids: list[list[str]] = []

        @ttl_cached_modifications(ttl=25.0)
        async def fetch_modifications(gids: list[str]) -> dict[str, str]:
            fetched_gids.append(gids)
            return {gid: f"v_{gid}" for gid in gids}

        # First call - all fetched
        await fetch_modifications(["123", "456"])
        assert fetched_gids[-1] == ["123", "456"]

        # Second call with one new GID
        await fetch_modifications(["123", "789"])
        assert fetched_gids[-1] == ["789"]  # Only uncached

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self) -> None:
        """Test decorator preserves function name and docstring."""

        @ttl_cached_modifications(ttl=25.0)
        async def fetch_modifications(gids: list[str]) -> dict[str, str]:
            """Fetch modification timestamps."""
            return {}

        assert fetch_modifications.__name__ == "fetch_modifications"
        assert fetch_modifications.__doc__ == "Fetch modification timestamps."

    @pytest.mark.asyncio
    async def test_decorator_with_extra_args(self) -> None:
        """Test decorator handles functions with extra arguments."""

        @ttl_cached_modifications(ttl=25.0)
        async def fetch_modifications(
            gids: list[str],
            project_gid: str,
            workspace_gid: str | None = None,
        ) -> dict[str, str]:
            return {gid: f"{project_gid}:{gid}" for gid in gids}

        result = await fetch_modifications(["123"], "project_1")
        assert result == {"123": "project_1:123"}

    @pytest.mark.asyncio
    async def test_decorator_respects_ttl(self) -> None:
        """Test decorator respects TTL expiration."""
        reset_modification_cache()
        call_count = 0

        @ttl_cached_modifications(ttl=0.1)
        async def fetch_modifications(gids: list[str]) -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            return {gid: f"v{call_count}_{gid}" for gid in gids}

        # First call
        result1 = await fetch_modifications(["123"])
        assert result1 == {"123": "v1_123"}
        assert call_count == 1

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Second call after expiration
        result2 = await fetch_modifications(["123"])
        assert result2 == {"123": "v2_123"}
        assert call_count == 2


class TestMonotonicTimeUsage:
    """Tests verifying monotonic time is used (not wall clock)."""

    def test_uses_monotonic_time(self) -> None:
        """Test that monotonic time is used for TTL checks."""
        cache = ModificationCheckCache(ttl=1.0)
        cache.set("123", "v1")

        # Get the check
        check = cache.get("123")
        assert check is not None

        # Verify checked_at is using monotonic time scale
        # Monotonic time typically starts near 0 at boot, while
        # wall clock time would be a large unix timestamp
        # This is a heuristic - monotonic time will be much smaller
        # than wall clock time (which would be ~1.7B)
        assert check.checked_at < 1_000_000_000


class TestLargeBatchHandling:
    """Tests for handling large batches (100+ GIDs)."""

    def setup_method(self) -> None:
        """Reset global cache before each test."""
        reset_modification_cache()

    def teardown_method(self) -> None:
        """Reset global cache after each test."""
        reset_modification_cache()

    @pytest.mark.asyncio
    async def test_handles_100_plus_gids(self) -> None:
        """Test handling 100+ GIDs efficiently."""
        gids = [str(i) for i in range(150)]

        mock_api = AsyncMock(return_value={gid: f"v_{gid}" for gid in gids})

        result = await fetch_task_modifications(gids, mock_api)

        assert len(result) == 150
        mock_api.assert_called_once_with(gids)

    @pytest.mark.asyncio
    async def test_partial_cache_with_large_batch(self) -> None:
        """Test partial cache hit with large batch."""
        # Pre-cache first 50
        cache = get_modification_cache()
        for i in range(50):
            cache.set(str(i), f"cached_{i}")

        gids = [str(i) for i in range(150)]

        mock_api = AsyncMock(
            return_value={str(i): f"fetched_{i}" for i in range(50, 150)}
        )

        result = await fetch_task_modifications(gids, mock_api)

        assert len(result) == 150
        # First 50 should be from cache
        for i in range(50):
            assert result[str(i)] == f"cached_{i}"
        # Rest should be fetched
        for i in range(50, 150):
            assert result[str(i)] == f"fetched_{i}"

        # Only uncached should be fetched
        mock_api.assert_called_once()
        fetched_gids = mock_api.call_args[0][0]
        assert len(fetched_gids) == 100
