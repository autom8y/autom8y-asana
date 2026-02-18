"""Tests for DataServiceClient circuit breaker integration.

Extracted from test_client.py as part of D-028 test file restructuring.
Maps to: DataServiceClient._circuit_breaker, autom8y_http.CircuitBreaker
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import httpx
import pytest

from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.data.config import DataServiceConfig


@pytest.mark.usefixtures("enable_insights_feature")
class TestCircuitBreaker:
    """Tests for circuit breaker integration (Story 2.3).

    Per Story 2.3 Acceptance Criteria:
    - Circuit breaker is integrated from transport layer
    - 5 consecutive failures triggers open state
    - When open, raises InsightsServiceError immediately (no HTTP)
    - Half-open allows 1 probe request
    - Successful probe closes circuit
    - Failed probe reopens circuit
    """

    @pytest.mark.asyncio
    async def test_circuit_stays_closed_on_success(self) -> None:
        """Circuit stays closed when requests succeed."""
        import respx
        from autom8y_http.protocols import CircuitState

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                json={
                    "data": [{"id": 1}],
                    "metadata": {
                        "factory": "account",
                        "row_count": 1,
                        "column_count": 1,
                        "columns": [{"name": "id", "dtype": "int64"}],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                }
            )

            async with client:
                # Make several successful requests
                for _ in range(3):
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                # Circuit should still be closed
                assert client.circuit_breaker.state == CircuitState.CLOSED
                assert client.circuit_breaker.failure_count == 0

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self) -> None:
        """Circuit opens after 5 consecutive failures (503 responses)."""
        import respx
        from autom8y_http.protocols import CircuitState

        from autom8_asana.clients.data.config import CircuitBreakerConfig, RetryConfig
        from autom8_asana.exceptions import InsightsServiceError

        # Use config with default failure_threshold=5
        # Disable retries to isolate circuit breaker behavior
        config = DataServiceConfig(
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=5,
                recovery_timeout=30.0,
                half_open_max_calls=1,
            ),
            retry=RetryConfig(max_retries=0),
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            # Mock 5 consecutive 503 responses
            respx.post("/api/v1/data-service/insights").respond(
                status_code=503,
                json={"error": "Service unavailable"},
            )

            async with client:
                # Make 5 failing requests to trigger circuit open
                for i in range(5):
                    with pytest.raises(InsightsServiceError):
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

                # Circuit should now be open
                assert client.circuit_breaker.state == CircuitState.OPEN

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_circuit_open_raises_immediately(self) -> None:
        """When circuit is open, raises InsightsServiceError with reason='circuit_breaker'."""
        import respx
        from autom8y_http.protocols import CircuitState

        from autom8_asana.clients.data.config import CircuitBreakerConfig, RetryConfig
        from autom8_asana.exceptions import InsightsServiceError

        # Disable retries to isolate circuit breaker behavior
        config = DataServiceConfig(
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=5,
                recovery_timeout=30.0,  # Long timeout so circuit stays open
                half_open_max_calls=1,
            ),
            retry=RetryConfig(max_retries=0),
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            route = respx.post("/api/v1/data-service/insights").respond(
                status_code=503,
                json={"error": "Service unavailable"},
            )

            async with client:
                # Make 5 failing requests to open circuit
                for _ in range(5):
                    with pytest.raises(InsightsServiceError):
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

                assert client.circuit_breaker.state == CircuitState.OPEN
                call_count_after_open = route.call_count

                # 6th call should fail immediately with circuit_breaker reason
                # and NOT make an HTTP request
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                assert exc.value.reason == "circuit_breaker"
                # No additional HTTP request should have been made
                assert route.call_count == call_count_after_open

    @pytest.mark.asyncio
    async def test_half_open_allows_probe_request(self) -> None:
        """Half-open state allows 1 probe request through."""
        import respx
        from autom8y_http.protocols import CircuitState

        from autom8_asana.clients.data.config import CircuitBreakerConfig, RetryConfig
        from autom8_asana.exceptions import InsightsServiceError

        # Very short recovery timeout so we can test half-open
        # Disable retries to isolate circuit breaker behavior
        config = DataServiceConfig(
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=5,
                recovery_timeout=0.1,  # 100ms
                half_open_max_calls=1,
            ),
            retry=RetryConfig(max_retries=0),  # Disable retries for this test
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            route = respx.post("/api/v1/data-service/insights").respond(
                status_code=503,
                json={"error": "Service unavailable"},
            )

            async with client:
                # Make 5 failing requests to open circuit
                for _ in range(5):
                    with pytest.raises(InsightsServiceError):
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

                assert client.circuit_breaker.state == CircuitState.OPEN
                call_count_before_wait = route.call_count

                # Wait for recovery timeout
                await asyncio.sleep(0.15)

                # Next request should transition to half-open and allow 1 probe
                with pytest.raises(InsightsServiceError):
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                # Probe request should have been made
                assert route.call_count == call_count_before_wait + 1

    @pytest.mark.asyncio
    async def test_successful_probe_closes_circuit(self) -> None:
        """Successful probe in half-open state closes the circuit."""
        import respx
        from autom8y_http.protocols import CircuitState

        from autom8_asana.clients.data.config import CircuitBreakerConfig, RetryConfig
        from autom8_asana.exceptions import InsightsServiceError

        # Disable retries to isolate circuit breaker behavior
        config = DataServiceConfig(
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=5,
                recovery_timeout=0.1,  # 100ms
                half_open_max_calls=1,
            ),
            retry=RetryConfig(max_retries=0),  # Disable retries for this test
        )
        client = DataServiceClient(config=config)

        # Track call count manually
        call_count = 0

        def handle_request(request):
            nonlocal call_count
            call_count += 1
            if call_count <= 5:
                # First 5 calls fail
                return httpx.Response(503, json={"error": "Service unavailable"})
            else:
                # After that, succeed
                return httpx.Response(
                    200,
                    json={
                        "data": [{"id": 1}],
                        "metadata": {
                            "factory": "account",
                            "row_count": 1,
                            "column_count": 1,
                            "columns": [{"name": "id", "dtype": "int64"}],
                            "cache_hit": False,
                            "duration_ms": 10.0,
                        },
                    },
                )

        with respx.mock:
            respx.post("/api/v1/data-service/insights").mock(side_effect=handle_request)

            async with client:
                # Make 5 failing requests to open circuit
                for _ in range(5):
                    with pytest.raises(InsightsServiceError):
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

                assert client.circuit_breaker.state == CircuitState.OPEN

                # Wait for recovery timeout
                await asyncio.sleep(0.15)

                # Next request should succeed and close circuit
                response = await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

                assert response is not None
                assert client.circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failed_probe_reopens_circuit(self) -> None:
        """Failed probe in half-open state reopens the circuit."""
        import respx
        from autom8y_http.protocols import CircuitState

        from autom8_asana.clients.data.config import CircuitBreakerConfig, RetryConfig
        from autom8_asana.exceptions import InsightsServiceError

        # Disable retries to isolate circuit breaker behavior
        config = DataServiceConfig(
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=5,
                recovery_timeout=0.1,  # 100ms
                half_open_max_calls=1,
            ),
            retry=RetryConfig(max_retries=0),  # Disable retries for this test
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            # All requests fail
            respx.post("/api/v1/data-service/insights").respond(
                status_code=503,
                json={"error": "Service unavailable"},
            )

            async with client:
                # Make 5 failing requests to open circuit
                for _ in range(5):
                    with pytest.raises(InsightsServiceError):
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

                assert client.circuit_breaker.state == CircuitState.OPEN

                # Wait for recovery timeout
                await asyncio.sleep(0.15)

                # Probe request should fail
                with pytest.raises(InsightsServiceError):
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                # Circuit should be back to OPEN
                assert client.circuit_breaker.state == CircuitState.OPEN
