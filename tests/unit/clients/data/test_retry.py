"""Tests for DataServiceClient retry infrastructure.

Extracted from test_client.py as part of D-028 test file restructuring.
Maps to: DataServiceClient._execute_with_retry, _retry.py
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.data.config import DataServiceConfig


@pytest.mark.usefixtures("enable_insights_feature")
class TestRetryHandler:
    """Tests for retry behavior with exponential backoff (Story 2.2).

    Per TDD-INSIGHTS-001 and Story 2.2:
    - Retry on status codes: 429, 502, 503, 504
    - Do NOT retry 4xx client errors (except 429)
    - Respect Retry-After header for 429
    - Maximum 2 retries with exponential backoff
    - Timeout errors trigger retry
    """

    @pytest.mark.asyncio
    async def test_retry_on_503_succeeds_after_retry(self) -> None:
        """First request returns 503, second returns 200."""
        import respx
        from httpx import Response

        from autom8_asana.clients.data.config import RetryConfig

        # Use a config with no jitter for deterministic testing
        config = DataServiceConfig(
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,  # Very short delay for fast tests
                jitter=False,
            )
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            route = respx.post("/api/v1/data-service/insights").mock(
                side_effect=[
                    Response(503, json={"error": "service unavailable"}),
                    Response(
                        200,
                        json={
                            "data": [{"spend": 100.0}],
                            "metadata": {
                                "factory": "account",
                                "row_count": 1,
                                "column_count": 1,
                                "columns": [{"name": "spend", "dtype": "float64"}],
                                "cache_hit": False,
                                "duration_ms": 25.0,
                            },
                        },
                    ),
                ]
            )

            async with client:
                response = await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

            assert response is not None
            assert response.data == [{"spend": 100.0}]
            assert route.call_count == 2  # First call failed, second succeeded

    @pytest.mark.asyncio
    async def test_retry_on_502_succeeds_after_retry(self) -> None:
        """First request returns 502, second returns 200."""
        import respx
        from httpx import Response

        from autom8_asana.clients.data.config import RetryConfig

        config = DataServiceConfig(
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
            )
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            route = respx.post("/api/v1/data-service/insights").mock(
                side_effect=[
                    Response(502, json={"error": "bad gateway"}),
                    Response(
                        200,
                        json={
                            "data": [{"spend": 200.0}],
                            "metadata": {
                                "factory": "account",
                                "row_count": 1,
                                "column_count": 1,
                                "columns": [{"name": "spend", "dtype": "float64"}],
                                "cache_hit": False,
                                "duration_ms": 30.0,
                            },
                        },
                    ),
                ]
            )

            async with client:
                response = await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

            assert response is not None
            assert response.data == [{"spend": 200.0}]
            assert route.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_504_succeeds_after_retry(self) -> None:
        """First request returns 504, second returns 200."""
        import respx
        from httpx import Response

        from autom8_asana.clients.data.config import RetryConfig

        config = DataServiceConfig(
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
            )
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            route = respx.post("/api/v1/data-service/insights").mock(
                side_effect=[
                    Response(504, json={"error": "gateway timeout"}),
                    Response(
                        200,
                        json={
                            "data": [{"spend": 300.0}],
                            "metadata": {
                                "factory": "account",
                                "row_count": 1,
                                "column_count": 1,
                                "columns": [{"name": "spend", "dtype": "float64"}],
                                "cache_hit": False,
                                "duration_ms": 35.0,
                            },
                        },
                    ),
                ]
            )

            async with client:
                response = await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

            assert response is not None
            assert response.data == [{"spend": 300.0}]
            assert route.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exhaustion_raises_error(self) -> None:
        """After max_retries, raises InsightsServiceError."""
        import respx
        from httpx import Response

        from autom8_asana.clients.data.config import RetryConfig
        from autom8_asana.errors import InsightsServiceError

        config = DataServiceConfig(
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
            )
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            route = respx.post("/api/v1/data-service/insights").mock(
                side_effect=[
                    Response(503, json={"error": "service unavailable"}),
                    Response(503, json={"error": "service unavailable"}),
                    Response(
                        503, json={"error": "service unavailable"}
                    ),  # 3rd call, retries exhausted
                ]
            )

            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

            assert exc.value.status_code == 503
            # 1 initial call + 2 retries = 3 total calls
            assert route.call_count == 3

    @pytest.mark.asyncio
    async def test_429_respects_retry_after_header(self) -> None:
        """429 with Retry-After header respects the delay."""
        import respx
        from httpx import Response

        from autom8_asana.clients.data.config import RetryConfig

        config = DataServiceConfig(
            retry=RetryConfig(
                max_retries=2,
                base_delay=1.0,  # Default delay
                max_delay=10.0,
                jitter=False,
            )
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            route = respx.post("/api/v1/data-service/insights").mock(
                side_effect=[
                    Response(
                        429,
                        json={"error": "rate limited"},
                        headers={"Retry-After": "2"},
                    ),
                    Response(
                        200,
                        json={
                            "data": [{"spend": 400.0}],
                            "metadata": {
                                "factory": "account",
                                "row_count": 1,
                                "column_count": 1,
                                "columns": [{"name": "spend", "dtype": "float64"}],
                                "cache_hit": False,
                                "duration_ms": 40.0,
                            },
                        },
                    ),
                ]
            )

            # Mock asyncio.sleep to capture the delay value
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

            assert response is not None
            assert route.call_count == 2
            # Should have called sleep with 2.0 (from Retry-After header)
            mock_sleep.assert_called()
            # The delay should be 2.0 from Retry-After header
            call_args = mock_sleep.call_args[0]
            assert call_args[0] == 2.0

    @pytest.mark.asyncio
    async def test_400_is_not_retried(self) -> None:
        """400 validation error is NOT retried."""
        import respx

        from autom8_asana.clients.data.config import RetryConfig
        from autom8_asana.errors import InsightsValidationError

        config = DataServiceConfig(
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
            )
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            route = respx.post("/api/v1/data-service/insights").respond(
                status_code=400,
                json={"error": "invalid request"},
            )

            async with client:
                with pytest.raises(InsightsValidationError):
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

            # Should only be called once - no retry for 400
            assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_404_is_not_retried(self) -> None:
        """404 not found error is NOT retried."""
        import respx

        from autom8_asana.clients.data.config import RetryConfig
        from autom8_asana.errors import InsightsNotFoundError

        config = DataServiceConfig(
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
            )
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            route = respx.post("/api/v1/data-service/insights").respond(
                status_code=404,
                json={"error": "not found"},
            )

            async with client:
                with pytest.raises(InsightsNotFoundError):
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

            # Should only be called once - no retry for 404
            assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_timeout_triggers_retry(self) -> None:
        """Timeout error triggers retry, then succeeds."""
        import respx
        from httpx import Response

        from autom8_asana.clients.data.config import RetryConfig

        config = DataServiceConfig(
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
            )
        )
        client = DataServiceClient(config=config)

        call_count = 0

        def handle_request(request: Any) -> Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.TimeoutException("Connection timed out")
            return Response(
                200,
                json={
                    "data": [{"spend": 500.0}],
                    "metadata": {
                        "factory": "account",
                        "row_count": 1,
                        "column_count": 1,
                        "columns": [{"name": "spend", "dtype": "float64"}],
                        "cache_hit": False,
                        "duration_ms": 50.0,
                    },
                },
            )

        with respx.mock:
            respx.post("/api/v1/data-service/insights").mock(side_effect=handle_request)

            async with client:
                response = await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

            assert response is not None
            assert response.data == [{"spend": 500.0}]
            assert call_count == 2  # First timed out, second succeeded

    @pytest.mark.asyncio
    async def test_timeout_exhaustion_raises_error(self) -> None:
        """After max_retries of timeout, raises InsightsServiceError."""
        import respx

        from autom8_asana.clients.data.config import RetryConfig
        from autom8_asana.errors import InsightsServiceError

        config = DataServiceConfig(
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
            )
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            respx.post("/api/v1/data-service/insights").mock(
                side_effect=httpx.TimeoutException("Connection timed out")
            )

            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

            assert exc.value.reason == "timeout"
            assert "timed out" in str(exc.value)
