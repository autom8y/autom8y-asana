"""Unit tests for @dataframe_cache decorator.

Per TDD-DATAFRAME-CACHE-001: Tests for decorator behavior including
cache hit, cache miss, build coalescing, and 503 responses.
"""

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest
from fastapi import HTTPException

from autom8_asana.cache.dataframe.decorator import dataframe_cache
from autom8_asana.cache.dataframe_cache import (
    CacheEntry,
    DataFrameCache,
    reset_dataframe_cache,
)


def make_entry(project_gid: str = "proj-1") -> CacheEntry:
    """Create a test CacheEntry."""
    df = pl.DataFrame({"gid": ["1", "2"], "name": ["A", "B"]})
    return CacheEntry(
        project_gid=project_gid,
        entity_type="unit",
        dataframe=df,
        watermark=datetime.now(UTC),
        created_at=datetime.now(UTC),
        schema_version="1.0.0",
    )


def make_mock_cache() -> MagicMock:
    """Create a mock DataFrameCache."""
    cache = MagicMock(spec=DataFrameCache)
    cache.get_async = AsyncMock(return_value=None)
    cache.put_async = AsyncMock()
    cache.acquire_build_lock_async = AsyncMock(return_value=True)
    cache.release_build_lock_async = AsyncMock()
    cache.wait_for_build_async = AsyncMock(return_value=None)
    return cache


class TestDataframeCacheDecorator:
    """Tests for @dataframe_cache decorator."""

    @pytest.fixture(autouse=True)
    def cleanup_env(self) -> None:
        """Clean up environment after each test."""
        yield
        if "DATAFRAME_CACHE_BYPASS" in os.environ:
            del os.environ["DATAFRAME_CACHE_BYPASS"]
        reset_dataframe_cache()

    @pytest.mark.asyncio
    async def test_cache_hit_injects_dataframe(self) -> None:
        """On cache hit, injects _cached_dataframe and calls resolve."""
        mock_cache = make_mock_cache()
        entry = make_entry()
        mock_cache.get_async.return_value = entry

        @dataframe_cache(
            cache_provider=lambda: mock_cache,
            entity_type="unit",
        )
        class TestStrategy:
            async def resolve(
                self, criteria: list, project_gid: str, client: object
            ) -> list:
                # Access injected dataframe
                df = getattr(self, "_cached_dataframe", None)
                return [{"gid": "1", "cached": df is not None}]

        strategy = TestStrategy()
        result = await strategy.resolve([], "proj-1", None)

        assert result[0]["cached"] is True
        mock_cache.get_async.assert_called_once_with("proj-1", "unit")
        mock_cache.acquire_build_lock_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_builds_and_caches(self) -> None:
        """On cache miss, acquires lock, builds, and caches result."""
        mock_cache = make_mock_cache()

        @dataframe_cache(
            cache_provider=lambda: mock_cache,
            entity_type="unit",
        )
        class TestStrategy:
            async def resolve(
                self, criteria: list, project_gid: str, client: object
            ) -> list:
                return [{"gid": "1"}]

            async def _build_dataframe(
                self, project_gid: str, client: object
            ) -> tuple[pl.DataFrame, datetime]:
                df = pl.DataFrame({"gid": ["1", "2"]})
                return df, datetime.now(UTC)

        strategy = TestStrategy()
        result = await strategy.resolve([], "proj-1", None)

        assert result[0]["gid"] == "1"
        mock_cache.acquire_build_lock_async.assert_called_once()
        mock_cache.put_async.assert_called_once()
        mock_cache.release_build_lock_async.assert_called_once_with(
            "proj-1", "unit", success=True
        )

    @pytest.mark.asyncio
    async def test_build_in_progress_waits(self) -> None:
        """When build in progress, waits for completion."""
        mock_cache = make_mock_cache()
        mock_cache.acquire_build_lock_async.return_value = False  # Lock not acquired
        mock_cache.wait_for_build_async.return_value = make_entry()  # Build succeeded

        @dataframe_cache(
            cache_provider=lambda: mock_cache,
            entity_type="unit",
        )
        class TestStrategy:
            async def resolve(
                self, criteria: list, project_gid: str, client: object
            ) -> list:
                return [{"gid": "1"}]

        strategy = TestStrategy()
        result = await strategy.resolve([], "proj-1", None)

        assert result[0]["gid"] == "1"
        mock_cache.wait_for_build_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_timeout_returns_503(self) -> None:
        """When wait times out, returns 503."""
        mock_cache = make_mock_cache()
        mock_cache.acquire_build_lock_async.return_value = False
        mock_cache.wait_for_build_async.return_value = None  # Timeout

        @dataframe_cache(
            cache_provider=lambda: mock_cache,
            entity_type="unit",
        )
        class TestStrategy:
            async def resolve(
                self, criteria: list, project_gid: str, client: object
            ) -> list:
                return []

        strategy = TestStrategy()

        with pytest.raises(HTTPException) as exc_info:
            await strategy.resolve([], "proj-1", None)

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["error"] == "CACHE_BUILD_IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_build_failure_returns_503(self) -> None:
        """When build fails, returns 503."""
        mock_cache = make_mock_cache()

        @dataframe_cache(
            cache_provider=lambda: mock_cache,
            entity_type="unit",
        )
        class TestStrategy:
            async def resolve(
                self, criteria: list, project_gid: str, client: object
            ) -> list:
                return []

            async def _build_dataframe(
                self, project_gid: str, client: object
            ) -> tuple[pl.DataFrame | None, datetime]:
                return None, datetime.now(UTC)  # Build fails

        strategy = TestStrategy()

        with pytest.raises(HTTPException) as exc_info:
            await strategy.resolve([], "proj-1", None)

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["error"] == "DATAFRAME_BUILD_FAILED"
        mock_cache.release_build_lock_async.assert_called_once_with(
            "proj-1", "unit", success=False
        )

    @pytest.mark.asyncio
    async def test_build_exception_returns_503(self) -> None:
        """When build raises exception, returns 503."""
        mock_cache = make_mock_cache()

        @dataframe_cache(
            cache_provider=lambda: mock_cache,
            entity_type="unit",
        )
        class TestStrategy:
            async def resolve(
                self, criteria: list, project_gid: str, client: object
            ) -> list:
                return []

            async def _build_dataframe(
                self, project_gid: str, client: object
            ) -> tuple[pl.DataFrame, datetime]:
                raise ValueError("Build error")

        strategy = TestStrategy()

        with pytest.raises(HTTPException) as exc_info:
            await strategy.resolve([], "proj-1", None)

        assert exc_info.value.status_code == 503
        assert "DATAFRAME_BUILD_ERROR" in exc_info.value.detail["error"]

    @pytest.mark.asyncio
    async def test_bypass_env_var(self) -> None:
        """Bypass caching when env var is set."""
        mock_cache = make_mock_cache()
        os.environ["DATAFRAME_CACHE_BYPASS"] = "true"

        @dataframe_cache(
            cache_provider=lambda: mock_cache,
            entity_type="unit",
        )
        class TestStrategy:
            async def resolve(
                self, criteria: list, project_gid: str, client: object
            ) -> list:
                return [{"gid": "bypassed"}]

        strategy = TestStrategy()
        result = await strategy.resolve([], "proj-1", None)

        assert result[0]["gid"] == "bypassed"
        mock_cache.get_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_cache_configured_falls_back(self) -> None:
        """When cache provider returns None, falls back to original."""

        @dataframe_cache(
            cache_provider=lambda: None,
            entity_type="unit",
        )
        class TestStrategy:
            async def resolve(
                self, criteria: list, project_gid: str, client: object
            ) -> list:
                return [{"gid": "no-cache"}]

        strategy = TestStrategy()
        result = await strategy.resolve([], "proj-1", None)

        assert result[0]["gid"] == "no-cache"

    @pytest.mark.asyncio
    async def test_custom_build_method(self) -> None:
        """Uses custom build method name."""
        mock_cache = make_mock_cache()

        @dataframe_cache(
            cache_provider=lambda: mock_cache,
            entity_type="offer",
            build_method="_build_offer_data",
        )
        class TestStrategy:
            async def resolve(
                self, criteria: list, project_gid: str, client: object
            ) -> list:
                return [{"gid": "1"}]

            async def _build_offer_data(
                self, project_gid: str, client: object
            ) -> tuple[pl.DataFrame, datetime]:
                df = pl.DataFrame({"gid": ["offer-1"]})
                return df, datetime.now(UTC)

        strategy = TestStrategy()
        await strategy.resolve([], "proj-1", None)

        mock_cache.put_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_entity_specific_build_method_fallback(self) -> None:
        """Falls back to _build_{entity_type}_dataframe."""
        mock_cache = make_mock_cache()

        @dataframe_cache(
            cache_provider=lambda: mock_cache,
            entity_type="contact",
        )
        class TestStrategy:
            async def resolve(
                self, criteria: list, project_gid: str, client: object
            ) -> list:
                return [{"gid": "1"}]

            async def _build_contact_dataframe(
                self, project_gid: str, client: object
            ) -> tuple[pl.DataFrame, datetime]:
                df = pl.DataFrame({"gid": ["contact-1"]})
                return df, datetime.now(UTC)

        strategy = TestStrategy()
        await strategy.resolve([], "proj-1", None)

        mock_cache.put_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_build_returns_single_value(self) -> None:
        """Handles build method returning just DataFrame."""
        mock_cache = make_mock_cache()

        @dataframe_cache(
            cache_provider=lambda: mock_cache,
            entity_type="unit",
        )
        class TestStrategy:
            async def resolve(
                self, criteria: list, project_gid: str, client: object
            ) -> list:
                return [{"gid": "1"}]

            async def _build_dataframe(
                self, project_gid: str, client: object
            ) -> pl.DataFrame:
                return pl.DataFrame({"gid": ["1"]})

        strategy = TestStrategy()
        await strategy.resolve([], "proj-1", None)

        # Should use current time as watermark
        mock_cache.put_async.assert_called_once()
