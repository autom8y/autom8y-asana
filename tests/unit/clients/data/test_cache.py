"""Tests for DataServiceClient cache integration.

Extracted from test_client.py as part of D-028 test file restructuring.
Maps to: DataServiceClient cache methods, _cache.py
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.data.config import DataServiceConfig


# --- Story 1.8: Cache Integration Tests ---


@pytest.mark.usefixtures("enable_insights_feature")
class TestCacheKeyGeneration:
    """Tests for _build_cache_key method (Story 1.8)."""

    def test_builds_correct_cache_key_format(self) -> None:
        """Cache key format is insights:{factory}:{canonical_key}."""
        from autom8_asana.models.contracts import PhoneVerticalPair

        client = DataServiceClient()
        pvp = PhoneVerticalPair(office_phone="+17705753103", vertical="chiropractic")

        cache_key = client._build_cache_key("account", pvp)

        assert cache_key == "insights:account:pv1:+17705753103:chiropractic"

    def test_uses_normalized_factory_name(self) -> None:
        """Cache key uses the factory name as provided (expected normalized)."""
        from autom8_asana.models.contracts import PhoneVerticalPair

        client = DataServiceClient()
        pvp = PhoneVerticalPair(office_phone="+14155551234", vertical="dental")

        cache_key = client._build_cache_key("account", pvp)

        assert cache_key.startswith("insights:account:")

    def test_different_pvps_produce_different_keys(self) -> None:
        """Different PhoneVerticalPairs produce different cache keys."""
        from autom8_asana.models.contracts import PhoneVerticalPair

        client = DataServiceClient()
        pvp1 = PhoneVerticalPair(office_phone="+17705753103", vertical="chiropractic")
        pvp2 = PhoneVerticalPair(office_phone="+17705753103", vertical="dental")
        pvp3 = PhoneVerticalPair(office_phone="+14155551234", vertical="chiropractic")

        key1 = client._build_cache_key("account", pvp1)
        key2 = client._build_cache_key("account", pvp2)
        key3 = client._build_cache_key("account", pvp3)

        assert key1 != key2  # Different vertical
        assert key1 != key3  # Different phone
        assert key2 != key3  # Different phone and vertical


@pytest.mark.usefixtures("enable_insights_feature")
class TestCacheHit:
    """Tests for cache hit behavior - successful response caching (Story 1.8)."""

    @pytest.mark.asyncio
    async def test_successful_response_is_cached(self) -> None:
        """Successful response is stored in cache."""
        import respx

        mock_cache = MagicMock()
        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    json={
                        "data": [{"spend": 100.0}],
                        "metadata": {
                            "factory": "account",
                            "row_count": 1,
                            "column_count": 1,
                            "columns": [{"name": "spend", "dtype": "float64"}],
                            "cache_hit": False,
                            "duration_ms": 50.0,
                        },
                    }
                )

                async with client:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        # Verify cache.set was called
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args

        # Check cache key format
        cache_key = call_args[0][0]
        assert cache_key == "insights:account:pv1:+17705753103:chiropractic"

        # Check cached data structure
        cached_data = call_args[0][1]
        assert "data" in cached_data
        assert "metadata" in cached_data
        assert "cached_at" in cached_data
        assert cached_data["data"] == [{"spend": 100.0}]

        # Check TTL
        assert call_args.kwargs.get("ttl") == 300  # Default TTL

    @pytest.mark.asyncio
    async def test_custom_ttl_is_used(self) -> None:
        """Custom cache TTL from config is used."""
        import respx

        mock_cache = MagicMock()
        config = DataServiceConfig(cache_ttl=600)  # 10 minutes
        client = DataServiceClient(config=config, cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    json={
                        "data": [],
                        "metadata": {
                            "factory": "account",
                            "row_count": 0,
                            "column_count": 0,
                            "columns": [],
                            "cache_hit": False,
                            "duration_ms": 10.0,
                        },
                    }
                )

                async with client:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        # Check custom TTL was used
        call_args = mock_cache.set.call_args
        assert call_args.kwargs.get("ttl") == 600

    @pytest.mark.asyncio
    async def test_no_caching_without_cache_provider(self) -> None:
        """No caching happens when no cache_provider is configured."""
        import respx

        client = DataServiceClient()  # No cache provider

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    json={
                        "data": [{"spend": 100.0}],
                        "metadata": {
                            "factory": "account",
                            "row_count": 1,
                            "column_count": 1,
                            "columns": [{"name": "spend", "dtype": "float64"}],
                            "cache_hit": False,
                            "duration_ms": 50.0,
                        },
                    }
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        # Response should still work
        assert response.data == [{"spend": 100.0}]
        assert not client.has_cache


@pytest.mark.usefixtures("enable_insights_feature")
class TestCacheMiss:
    """Tests for cache miss behavior - fresh requests (Story 1.8)."""

    @pytest.mark.asyncio
    async def test_fresh_request_when_cache_empty(self) -> None:
        """Fresh request proceeds normally when cache is empty."""
        import respx

        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # Cache miss
        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                route = respx.post("/api/v1/data-service/insights").respond(
                    json={
                        "data": [{"spend": 200.0}],
                        "metadata": {
                            "factory": "account",
                            "row_count": 1,
                            "column_count": 1,
                            "columns": [{"name": "spend", "dtype": "float64"}],
                            "cache_hit": False,
                            "duration_ms": 75.0,
                        },
                    }
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        # HTTP request was made
        assert route.called
        # Fresh response returned
        assert response.data == [{"spend": 200.0}]
        assert response.metadata.is_stale is False


@pytest.mark.usefixtures("enable_insights_feature")
class TestStaleFallback:
    """Tests for stale cache fallback on service errors (Story 1.8)."""

    @pytest.mark.asyncio
    async def test_stale_fallback_on_500_error(self) -> None:
        """Returns stale cache on HTTP 500 error."""
        import respx

        mock_cache = MagicMock()
        # Cache returns stale data
        mock_cache.get.return_value = {
            "data": [{"spend": 150.0}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [{"name": "spend", "dtype": "float64"}],
                "cache_hit": True,
                "duration_ms": 25.0,
            },
            "request_id": "old-request-id",
            "warnings": [],
            "cached_at": "2024-01-01T12:00:00+00:00",
        }

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=500,
                    json={"error": "Internal server error"},
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        # Stale response returned
        assert response.data == [{"spend": 150.0}]
        assert response.metadata.is_stale is True
        assert response.metadata.cached_at is not None
        assert "stale cache" in response.warnings[-1]

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_stale_fallback_on_502_error(self) -> None:
        """Returns stale cache on HTTP 502 Bad Gateway error."""
        import respx

        mock_cache = MagicMock()
        mock_cache.get.return_value = {
            "data": [{"spend": 100.0}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [{"name": "spend", "dtype": "float64"}],
                "cache_hit": False,
                "duration_ms": 50.0,
            },
            "request_id": "cached-id",
            "warnings": [],
            "cached_at": "2024-01-15T10:30:00+00:00",
        }

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=502,
                    json={"error": "Bad gateway"},
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert response.metadata.is_stale is True

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_stale_fallback_on_503_error(self) -> None:
        """Returns stale cache on HTTP 503 Service Unavailable error."""
        import respx

        mock_cache = MagicMock()
        mock_cache.get.return_value = {
            "data": [{"spend": 100.0}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [{"name": "spend", "dtype": "float64"}],
                "cache_hit": False,
                "duration_ms": 50.0,
            },
            "request_id": "cached-id",
            "warnings": [],
            "cached_at": "2024-01-15T10:30:00+00:00",
        }

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=503,
                    json={"error": "Service unavailable"},
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert response.metadata.is_stale is True

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_stale_fallback_on_504_error(self) -> None:
        """Returns stale cache on HTTP 504 Gateway Timeout error."""
        import respx

        mock_cache = MagicMock()
        mock_cache.get.return_value = {
            "data": [{"spend": 100.0}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [{"name": "spend", "dtype": "float64"}],
                "cache_hit": False,
                "duration_ms": 50.0,
            },
            "request_id": "cached-id",
            "warnings": [],
            "cached_at": "2024-01-15T10:30:00+00:00",
        }

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=504,
                    json={"error": "Gateway timeout"},
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert response.metadata.is_stale is True

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_stale_fallback_on_timeout(self) -> None:
        """Returns stale cache on request timeout."""
        import respx

        mock_cache = MagicMock()
        mock_cache.get.return_value = {
            "data": [{"spend": 75.0}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [{"name": "spend", "dtype": "float64"}],
                "cache_hit": False,
                "duration_ms": 30.0,
            },
            "request_id": "cached-id",
            "warnings": [],
            "cached_at": "2024-01-20T08:00:00+00:00",
        }

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").mock(
                    side_effect=httpx.TimeoutException("Request timed out")
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert response.metadata.is_stale is True
        assert response.data == [{"spend": 75.0}]

    @pytest.mark.asyncio
    async def test_stale_fallback_on_connection_error(self) -> None:
        """Returns stale cache on connection error."""
        import respx

        mock_cache = MagicMock()
        mock_cache.get.return_value = {
            "data": [{"spend": 50.0}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [{"name": "spend", "dtype": "float64"}],
                "cache_hit": False,
                "duration_ms": 20.0,
            },
            "request_id": "cached-id",
            "warnings": [],
            "cached_at": "2024-01-25T16:00:00+00:00",
        }

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").mock(
                    side_effect=httpx.ConnectError("Connection refused")
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert response.metadata.is_stale is True

    @pytest.mark.asyncio
    async def test_raises_when_no_stale_cache_on_error(self) -> None:
        """Raises InsightsServiceError when no stale cache available."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # No stale cache

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=500,
                    json={"error": "Internal server error"},
                )

                async with client:
                    with pytest.raises(InsightsServiceError) as exc:
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_no_stale_fallback_on_400_error(self) -> None:
        """No stale fallback on 400 validation errors."""
        import respx

        from autom8_asana.exceptions import InsightsValidationError

        mock_cache = MagicMock()
        mock_cache.get.return_value = {
            "data": [{"spend": 100.0}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [],
                "cache_hit": False,
                "duration_ms": 10.0,
            },
            "cached_at": "2024-01-01T12:00:00+00:00",
        }

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=400,
                    json={"error": "Invalid request"},
                )

                async with client:
                    with pytest.raises(InsightsValidationError):
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

        # Cache get should NOT have been called for 400 errors
        # (validation errors are client-side, cache fallback doesn't help)

    @pytest.mark.asyncio
    async def test_no_stale_fallback_on_404_error(self) -> None:
        """No stale fallback on 404 not found errors."""
        import respx

        from autom8_asana.exceptions import InsightsNotFoundError

        mock_cache = MagicMock()
        mock_cache.get.return_value = {
            "data": [{"spend": 100.0}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [],
                "cache_hit": False,
                "duration_ms": 10.0,
            },
            "cached_at": "2024-01-01T12:00:00+00:00",
        }

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=404,
                    json={"error": "Not found"},
                )

                async with client:
                    with pytest.raises(InsightsNotFoundError):
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )


@pytest.mark.usefixtures("enable_insights_feature")
class TestCacheFailureGracefulDegradation:
    """Tests for graceful degradation when cache operations fail (Story 1.8)."""

    @pytest.mark.asyncio
    async def test_cache_set_failure_does_not_break_request(self) -> None:
        """Cache set failure doesn't break the request."""
        import respx

        mock_cache = MagicMock()
        mock_cache.set.side_effect = ConnectionError("Cache write failed")

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    json={
                        "data": [{"spend": 100.0}],
                        "metadata": {
                            "factory": "account",
                            "row_count": 1,
                            "column_count": 1,
                            "columns": [{"name": "spend", "dtype": "float64"}],
                            "cache_hit": False,
                            "duration_ms": 50.0,
                        },
                    }
                )

                async with client:
                    # Should not raise despite cache failure
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        # Request succeeded despite cache failure
        assert response.data == [{"spend": 100.0}]

    @pytest.mark.asyncio
    async def test_cache_get_failure_does_not_break_fallback(self) -> None:
        """Cache get failure during fallback doesn't break error handling."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        mock_cache = MagicMock()
        mock_cache.get.side_effect = ConnectionError("Cache read failed")

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=500,
                    json={"error": "Internal server error"},
                )

                async with client:
                    with pytest.raises(InsightsServiceError) as exc:
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

        # Original error is raised (cache fallback failed silently)
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_cache_set_logs_warning_on_failure(self) -> None:
        """Cache set failure logs a warning."""
        import respx

        mock_cache = MagicMock()
        mock_cache.set.side_effect = ConnectionError("Cache write failed")
        mock_logger = MagicMock()

        client = DataServiceClient(cache_provider=mock_cache, logger=mock_logger)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    json={
                        "data": [],
                        "metadata": {
                            "factory": "account",
                            "row_count": 0,
                            "column_count": 0,
                            "columns": [],
                            "cache_hit": False,
                            "duration_ms": 10.0,
                        },
                    }
                )

                async with client:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        # Warning should have been logged
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Failed to cache response" in warning_call


@pytest.mark.usefixtures("enable_insights_feature")
class TestStaleResponseMetadata:
    """Tests for stale response metadata (Story 1.8)."""

    @pytest.mark.asyncio
    async def test_stale_response_has_is_stale_true(self) -> None:
        """Stale response has is_stale=True in metadata."""
        import respx

        mock_cache = MagicMock()
        mock_cache.get.return_value = {
            "data": [{"spend": 100.0}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [{"name": "spend", "dtype": "float64"}],
                "cache_hit": False,
                "duration_ms": 50.0,
                "is_stale": False,  # Original value
            },
            "request_id": "original-id",
            "warnings": [],
            "cached_at": "2024-01-01T12:00:00+00:00",
        }

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=500,
                    json={"error": "Server error"},
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        # Metadata should be updated
        assert response.metadata.is_stale is True

    @pytest.mark.asyncio
    async def test_stale_response_has_cached_at_populated(self) -> None:
        """Stale response has cached_at populated from cache entry."""
        import respx

        mock_cache = MagicMock()
        mock_cache.get.return_value = {
            "data": [{"spend": 100.0}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [{"name": "spend", "dtype": "float64"}],
                "cache_hit": False,
                "duration_ms": 50.0,
            },
            "request_id": "original-id",
            "warnings": [],
            "cached_at": "2024-06-15T14:30:00+00:00",
        }

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=500,
                    json={"error": "Server error"},
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        # cached_at should be parsed and populated
        assert response.metadata.cached_at is not None
        assert response.metadata.cached_at.year == 2024
        assert response.metadata.cached_at.month == 6
        assert response.metadata.cached_at.day == 15

    @pytest.mark.asyncio
    async def test_stale_response_includes_warning(self) -> None:
        """Stale response includes warning about stale data."""
        import respx

        mock_cache = MagicMock()
        mock_cache.get.return_value = {
            "data": [{"spend": 100.0}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [{"name": "spend", "dtype": "float64"}],
                "cache_hit": False,
                "duration_ms": 50.0,
            },
            "request_id": "original-id",
            "warnings": ["Original warning"],
            "cached_at": "2024-01-01T12:00:00+00:00",
        }

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=500,
                    json={"error": "Server error"},
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        # Should include original warnings plus stale warning
        assert "Original warning" in response.warnings
        assert any("stale cache" in w for w in response.warnings)

    @pytest.mark.asyncio
    async def test_stale_response_uses_new_request_id(self) -> None:
        """Stale response uses new request_id, not cached one."""
        import respx

        mock_cache = MagicMock()
        mock_cache.get.return_value = {
            "data": [{"spend": 100.0}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [{"name": "spend", "dtype": "float64"}],
                "cache_hit": False,
                "duration_ms": 50.0,
            },
            "request_id": "old-cached-request-id",
            "warnings": [],
            "cached_at": "2024-01-01T12:00:00+00:00",
        }

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=500,
                    json={"error": "Server error"},
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        # Request ID should be the new one, not the cached one
        assert response.request_id != "old-cached-request-id"
        # Should be a valid UUID
        import uuid

        uuid.UUID(response.request_id)
