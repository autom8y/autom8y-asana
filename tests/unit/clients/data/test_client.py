"""Tests for DataServiceClient skeleton implementation.

Per TDD-INSIGHTS-001 Section 16: Unit tests for DataServiceClient.
Per Story 1.5 Acceptance Criteria:
- Context manager lifecycle
- Client creation with config
- Cache injection
- Auth token retrieval
"""

from __future__ import annotations

import asyncio
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.data.config import (
    ConnectionPoolConfig,
    DataServiceConfig,
    TimeoutConfig,
)


class TestDataServiceClientInit:
    """Tests for DataServiceClient initialization."""

    def test_default_config_from_env(self) -> None:
        """Uses DataServiceConfig.from_env() when no config provided."""
        client = DataServiceClient()

        assert client.config is not None
        assert isinstance(client.config, DataServiceConfig)
        # Default base_url from config
        assert client.config.base_url is not None

    def test_accepts_custom_config(self) -> None:
        """Accepts custom DataServiceConfig."""
        config = DataServiceConfig(
            base_url="https://custom.example.com",
            cache_ttl=600,
        )
        client = DataServiceClient(config=config)

        assert client.config.base_url == "https://custom.example.com"
        assert client.config.cache_ttl == 600

    def test_accepts_auth_provider(self) -> None:
        """Accepts optional auth_provider parameter."""
        mock_auth = MagicMock()
        mock_auth.get_secret.return_value = "test-token"

        client = DataServiceClient(auth_provider=mock_auth)

        # Auth provider stored for later use
        assert client._auth_provider is mock_auth

    def test_accepts_logger(self) -> None:
        """Accepts optional logger parameter."""
        mock_logger = MagicMock()

        client = DataServiceClient(logger=mock_logger)

        assert client._log is mock_logger

    def test_accepts_cache_provider(self) -> None:
        """Accepts optional cache_provider per ADR-INS-004."""
        mock_cache = MagicMock()

        client = DataServiceClient(cache_provider=mock_cache)

        assert client._cache is mock_cache
        assert client.has_cache is True

    def test_accepts_staleness_settings(self) -> None:
        """Accepts optional staleness_settings parameter."""
        from autom8_asana.cache.staleness_settings import StalenessCheckSettings

        settings = StalenessCheckSettings(base_ttl=600)

        client = DataServiceClient(staleness_settings=settings)

        assert client._staleness_settings is settings

    def test_has_cache_false_when_no_cache_provider(self) -> None:
        """has_cache returns False when no cache_provider."""
        client = DataServiceClient()

        assert client.has_cache is False

    def test_is_initialized_false_before_use(self) -> None:
        """is_initialized returns False before _get_client called."""
        client = DataServiceClient()

        assert client.is_initialized is False

    def test_client_not_created_on_init(self) -> None:
        """HTTP client is not created during __init__ (lazy initialization)."""
        client = DataServiceClient()

        assert client._client is None


class TestDataServiceClientContextManager:
    """Tests for async context manager protocol."""

    @pytest.mark.asyncio
    async def test_aenter_returns_self(self) -> None:
        """__aenter__ returns the client instance."""
        client = DataServiceClient()

        async with client as entered:
            assert entered is client

    @pytest.mark.asyncio
    async def test_aexit_closes_client(self) -> None:
        """__aexit__ calls close() to release resources."""
        client = DataServiceClient()

        # Force client creation
        with patch.object(httpx.AsyncClient, "aclose", new_callable=AsyncMock) as mock_close:
            # Manually set a mock client to test close
            client._client = MagicMock()
            client._client.aclose = mock_close

            async with client:
                pass

            mock_close.assert_called_once()
            assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_exception(self) -> None:
        """Context manager closes client even on exception."""
        client = DataServiceClient()

        with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
            with pytest.raises(ValueError):
                async with client:
                    raise ValueError("test error")

            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_with_no_client_created(self) -> None:
        """Context manager handles case where client was never created."""
        client = DataServiceClient()

        # No exception should be raised when closing without client creation
        async with client:
            assert client._client is None

        # Still no client after exit
        assert client._client is None


class TestDataServiceClientClose:
    """Tests for close() method."""

    @pytest.mark.asyncio
    async def test_close_closes_http_client(self) -> None:
        """close() calls aclose() on httpx client."""
        client = DataServiceClient()

        mock_http = AsyncMock()
        client._client = mock_http

        await client.close()

        mock_http.aclose.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self) -> None:
        """close() can be called multiple times safely."""
        client = DataServiceClient()

        # First call does nothing (no client)
        await client.close()
        assert client._client is None

        # Second call also does nothing
        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_with_logger(self) -> None:
        """close() logs when logger is provided."""
        mock_logger = MagicMock()
        client = DataServiceClient(logger=mock_logger)

        mock_http = AsyncMock()
        client._client = mock_http

        await client.close()

        mock_logger.debug.assert_called()


class TestDataServiceClientGetClient:
    """Tests for _get_client() method."""

    @pytest.mark.asyncio
    async def test_creates_httpx_client(self) -> None:
        """_get_client creates httpx.AsyncClient with correct config."""
        config = DataServiceConfig(
            base_url="https://test.example.com",
        )
        client = DataServiceClient(config=config)

        with patch("autom8_asana.clients.data.client.httpx.AsyncClient") as mock_class:
            mock_instance = AsyncMock()
            mock_class.return_value = mock_instance

            await client._get_client()

            mock_class.assert_called_once()
            call_kwargs = mock_class.call_args.kwargs

            assert call_kwargs["base_url"] == "https://test.example.com"
            assert "timeout" in call_kwargs
            assert "limits" in call_kwargs
            assert "headers" in call_kwargs

    @pytest.mark.asyncio
    async def test_configures_timeouts_from_config(self) -> None:
        """_get_client configures timeouts from config."""
        config = DataServiceConfig(
            base_url="https://test.example.com",
            timeout=TimeoutConfig(
                connect=10.0,
                read=60.0,
                write=45.0,
                pool=8.0,
            ),
        )
        client = DataServiceClient(config=config)

        with patch("autom8_asana.clients.data.client.httpx.AsyncClient") as mock_class:
            await client._get_client()

            call_kwargs = mock_class.call_args.kwargs
            timeout = call_kwargs["timeout"]

            assert isinstance(timeout, httpx.Timeout)
            assert timeout.connect == 10.0
            assert timeout.read == 60.0
            assert timeout.write == 45.0
            assert timeout.pool == 8.0

    @pytest.mark.asyncio
    async def test_configures_connection_pool_from_config(self) -> None:
        """_get_client configures connection pool from config."""
        config = DataServiceConfig(
            base_url="https://test.example.com",
            connection_pool=ConnectionPoolConfig(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=60.0,
            ),
        )
        client = DataServiceClient(config=config)

        with patch("autom8_asana.clients.data.client.httpx.AsyncClient") as mock_class:
            await client._get_client()

            call_kwargs = mock_class.call_args.kwargs
            limits = call_kwargs["limits"]

            assert isinstance(limits, httpx.Limits)
            assert limits.max_connections == 20
            assert limits.max_keepalive_connections == 10
            assert limits.keepalive_expiry == 60.0

    @pytest.mark.asyncio
    async def test_includes_auth_header_when_token_available(self) -> None:
        """_get_client includes Authorization header when token is available."""
        mock_auth = MagicMock()
        mock_auth.get_secret.return_value = "test-jwt-token"

        client = DataServiceClient(auth_provider=mock_auth)

        with patch("autom8_asana.clients.data.client.httpx.AsyncClient") as mock_class:
            await client._get_client()

            call_kwargs = mock_class.call_args.kwargs
            headers = call_kwargs["headers"]

            assert headers["Authorization"] == "Bearer test-jwt-token"

    @pytest.mark.asyncio
    async def test_no_auth_header_when_no_token(self) -> None:
        """_get_client omits Authorization header when no token."""
        config = DataServiceConfig(
            base_url="https://test.example.com",
            token_key="NONEXISTENT_KEY",
        )
        client = DataServiceClient(config=config)

        with patch("autom8_asana.clients.data.client.httpx.AsyncClient") as mock_class:
            with patch.dict(os.environ, {}, clear=True):
                await client._get_client()

            call_kwargs = mock_class.call_args.kwargs
            headers = call_kwargs["headers"]

            assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_includes_content_type_headers(self) -> None:
        """_get_client includes Accept and Content-Type headers."""
        client = DataServiceClient()

        with patch("autom8_asana.clients.data.client.httpx.AsyncClient") as mock_class:
            await client._get_client()

            call_kwargs = mock_class.call_args.kwargs
            headers = call_kwargs["headers"]

            assert headers["Accept"] == "application/json"
            assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_returns_same_client_on_subsequent_calls(self) -> None:
        """_get_client returns cached client on subsequent calls."""
        client = DataServiceClient()

        with patch("autom8_asana.clients.data.client.httpx.AsyncClient") as mock_class:
            mock_instance = AsyncMock()
            mock_class.return_value = mock_instance

            result1 = await client._get_client()
            result2 = await client._get_client()

            # Only created once
            assert mock_class.call_count == 1
            assert result1 is result2

    @pytest.mark.asyncio
    async def test_sets_is_initialized_after_creation(self) -> None:
        """_get_client sets is_initialized to True."""
        client = DataServiceClient()

        assert client.is_initialized is False

        with patch("autom8_asana.clients.data.client.httpx.AsyncClient"):
            await client._get_client()

        assert client.is_initialized is True

    @pytest.mark.asyncio
    async def test_logs_when_logger_provided(self) -> None:
        """_get_client logs when logger is provided."""
        mock_logger = MagicMock()
        client = DataServiceClient(logger=mock_logger)

        with patch("autom8_asana.clients.data.client.httpx.AsyncClient"):
            await client._get_client()

        mock_logger.debug.assert_called()


class TestDataServiceClientGetAuthToken:
    """Tests for _get_auth_token() method."""

    def test_returns_token_from_auth_provider(self) -> None:
        """Returns token from auth_provider.get_secret()."""
        mock_auth = MagicMock()
        mock_auth.get_secret.return_value = "provider-token"

        client = DataServiceClient(auth_provider=mock_auth)

        token = client._get_auth_token()

        assert token == "provider-token"
        mock_auth.get_secret.assert_called_once_with("AUTOM8_DATA_API_KEY")

    def test_uses_custom_token_key_from_config(self) -> None:
        """Uses token_key from config when calling auth_provider."""
        mock_auth = MagicMock()
        mock_auth.get_secret.return_value = "custom-token"

        config = DataServiceConfig(
            base_url="https://test.example.com",
            token_key="CUSTOM_TOKEN_KEY",
        )
        client = DataServiceClient(config=config, auth_provider=mock_auth)

        client._get_auth_token()

        mock_auth.get_secret.assert_called_once_with("CUSTOM_TOKEN_KEY")

    def test_falls_back_to_env_var_when_no_provider(self) -> None:
        """Falls back to environment variable when no auth_provider."""
        config = DataServiceConfig(
            base_url="https://test.example.com",
            token_key="TEST_TOKEN",
        )
        client = DataServiceClient(config=config)

        with patch.dict(os.environ, {"TEST_TOKEN": "env-token"}):
            token = client._get_auth_token()

        assert token == "env-token"

    def test_falls_back_to_env_var_on_provider_error(self) -> None:
        """Falls back to environment variable when auth_provider raises."""
        mock_auth = MagicMock()
        mock_auth.get_secret.side_effect = Exception("Provider error")
        mock_logger = MagicMock()

        config = DataServiceConfig(
            base_url="https://test.example.com",
            token_key="TEST_TOKEN",
        )
        client = DataServiceClient(
            config=config,
            auth_provider=mock_auth,
            logger=mock_logger,
        )

        with patch.dict(os.environ, {"TEST_TOKEN": "fallback-token"}):
            token = client._get_auth_token()

        assert token == "fallback-token"
        mock_logger.warning.assert_called()

    def test_returns_none_when_no_token_available(self) -> None:
        """Returns None when no auth_provider and env var not set."""
        config = DataServiceConfig(
            base_url="https://test.example.com",
            token_key="NONEXISTENT_KEY",
        )
        client = DataServiceClient(config=config)

        with patch.dict(os.environ, {}, clear=True):
            token = client._get_auth_token()

        assert token is None


class TestDataServiceClientConcurrency:
    """Tests for thread-safety and concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_get_client_creates_only_one(self) -> None:
        """Multiple concurrent _get_client calls create only one client."""
        client = DataServiceClient()
        creation_count = 0
        mock_instance = MagicMock()

        def mock_create(*args: Any, **kwargs: Any) -> MagicMock:
            nonlocal creation_count
            creation_count += 1
            return mock_instance

        with patch(
            "autom8_asana.clients.data.client.httpx.AsyncClient",
            side_effect=mock_create,
        ):
            # Start multiple concurrent calls
            results = await asyncio.gather(
                client._get_client(),
                client._get_client(),
                client._get_client(),
            )

        # Only one client should be created (due to lock)
        assert creation_count == 1
        # All calls should return the same instance
        assert results[0] is results[1] is results[2]
        assert results[0] is mock_instance


class TestDataServiceClientProperties:
    """Tests for client properties."""

    def test_config_property_returns_config(self) -> None:
        """config property returns the DataServiceConfig."""
        config = DataServiceConfig(base_url="https://test.example.com")
        client = DataServiceClient(config=config)

        assert client.config is config

    def test_is_initialized_reflects_client_state(self) -> None:
        """is_initialized reflects whether HTTP client exists."""
        client = DataServiceClient()

        assert client.is_initialized is False

        client._client = MagicMock()
        assert client.is_initialized is True

        client._client = None
        assert client.is_initialized is False

    def test_has_cache_reflects_cache_provider(self) -> None:
        """has_cache reflects whether cache_provider is set."""
        client_no_cache = DataServiceClient()
        assert client_no_cache.has_cache is False

        client_with_cache = DataServiceClient(cache_provider=MagicMock())
        assert client_with_cache.has_cache is True


# --- Story 1.6: get_insights_async Tests ---


@pytest.fixture
def enable_insights_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable insights feature flag for testing."""
    monkeypatch.setenv("AUTOM8_DATA_INSIGHTS_ENABLED", "true")


@pytest.mark.usefixtures("enable_insights_feature")
class TestGetInsightsAsyncValidation:
    """Tests for get_insights_async input validation."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("factory_name", [
        "account", "ads", "adsets", "campaigns", "spend",
        "leads", "appts", "assets", "targeting", "payments",
        "business_offers", "ad_questions", "ad_tests", "base",
    ])
    async def test_all_14_factories_accepted(self, factory_name: str) -> None:
        """All 14 factory names are accepted by validation."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            respx.post(f"/api/v1/factory/{factory_name}").respond(
                json={
                    "data": [{"value": 100.0}],
                    "metadata": {
                        "factory": factory_name,
                        "row_count": 1,
                        "column_count": 1,
                        "columns": [{"name": "value", "dtype": "float64"}],
                        "cache_hit": False,
                        "duration_ms": 50.0,
                    },
                }
            )

            # Should not raise - all 14 factories are valid
            async with client:
                response = await client.get_insights_async(
                    factory=factory_name,
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )
                assert response.metadata.factory == factory_name

    @pytest.mark.asyncio
    async def test_rejects_invalid_factory(self) -> None:
        """Invalid factory names are rejected with helpful error listing valid factories."""
        from autom8_asana.exceptions import InsightsValidationError

        client = DataServiceClient()

        async with client:
            with pytest.raises(InsightsValidationError) as exc:
                await client.get_insights_async(
                    factory="not_a_factory",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

        error_msg = str(exc.value)
        assert "Invalid factory" in error_msg
        assert "not_a_factory" in error_msg
        # Error message should list valid factories
        assert "Valid factories:" in error_msg
        assert "account" in error_msg
        assert "ads" in error_msg
        assert "campaigns" in error_msg
        assert exc.value.field == "factory"
        assert exc.value.request_id is not None

    @pytest.mark.asyncio
    async def test_rejects_invalid_phone_format(self) -> None:
        """Invalid E.164 phone format is rejected."""
        from autom8_asana.exceptions import InsightsValidationError

        client = DataServiceClient()

        async with client:
            with pytest.raises(InsightsValidationError) as exc:
                await client.get_insights_async(
                    factory="account",
                    office_phone="555-123-4567",  # Invalid: not E.164
                    vertical="chiropractic",
                )

        assert "Invalid E.164 format" in str(exc.value)
        assert exc.value.field == "office_phone"

    @pytest.mark.asyncio
    async def test_validates_period_format(self) -> None:
        """Invalid period format raises error during request construction."""
        from pydantic import ValidationError

        from autom8_asana.clients.data.models import InsightsRequest

        # This tests the InsightsRequest validation directly
        with pytest.raises(ValidationError):
            InsightsRequest(
                office_phone="+17705753103",
                vertical="chiropractic",
                insights_period="invalid_period",
            )


@pytest.mark.usefixtures("enable_insights_feature")
class TestGetInsightsAsyncHTTPContract:
    """Contract tests for get_insights_async HTTP behavior using respx."""

    @pytest.mark.asyncio
    async def test_posts_to_correct_endpoint(self) -> None:
        """Request is POST to /api/v1/factory/{factory_name}."""
        import respx

        client = DataServiceClient(
            config=DataServiceConfig(base_url="https://data.example.com")
        )

        with respx.mock:
            route = respx.post("https://data.example.com/api/v1/factory/account").respond(
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

            assert route.called

    @pytest.mark.asyncio
    async def test_includes_request_id_header(self) -> None:
        """Request includes X-Request-Id header."""
        import respx

        client = DataServiceClient()
        captured_headers: dict[str, str] = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            nonlocal captured_headers
            captured_headers = dict(request.headers)
            return httpx.Response(
                200,
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
                },
            )

        with respx.mock:
            respx.post("/api/v1/factory/account").mock(side_effect=capture_request)

            async with client:
                await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

        assert "x-request-id" in captured_headers
        # Should be a valid UUID
        import uuid
        uuid.UUID(captured_headers["x-request-id"])

    @pytest.mark.asyncio
    async def test_sends_correct_request_body(self) -> None:
        """Request body matches InsightsRequest schema."""
        import respx

        client = DataServiceClient()
        captured_body: dict[str, Any] = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            import json
            captured_body = json.loads(request.content)
            return httpx.Response(
                200,
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
                },
            )

        with respx.mock:
            respx.post("/api/v1/factory/account").mock(side_effect=capture_request)

            async with client:
                from datetime import date
                await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                    period="t30",
                    start_date=date(2024, 1, 1),
                    metrics=["spend", "leads"],
                    refresh=True,
                )

        assert captured_body["office_phone"] == "+17705753103"
        assert captured_body["vertical"] == "chiropractic"
        assert captured_body["insights_period"] == "t30"
        assert captured_body["start_date"] == "2024-01-01"
        assert captured_body["metrics"] == ["spend", "leads"]
        assert captured_body["refresh"] is True

    @pytest.mark.asyncio
    async def test_excludes_none_values_from_body(self) -> None:
        """Request body excludes None values (exclude_none=True)."""
        import respx

        client = DataServiceClient()
        captured_body: dict[str, Any] = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            import json
            captured_body = json.loads(request.content)
            return httpx.Response(
                200,
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
                },
            )

        with respx.mock:
            respx.post("/api/v1/factory/account").mock(side_effect=capture_request)

            async with client:
                await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                    # metrics=None (default), should not be in body
                )

        # None values should not be present
        assert "metrics" not in captured_body
        assert "dimensions" not in captured_body
        assert "start_date" not in captured_body
        assert "end_date" not in captured_body


@pytest.mark.usefixtures("enable_insights_feature")
class TestGetInsightsAsyncErrorMapping:
    """Tests for HTTP error response mapping."""

    @pytest.mark.asyncio
    async def test_400_maps_to_validation_error(self) -> None:
        """HTTP 400 maps to InsightsValidationError."""
        import respx

        from autom8_asana.exceptions import InsightsValidationError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
                status_code=400,
                json={"error": "Invalid phone format"},
            )

            async with client:
                with pytest.raises(InsightsValidationError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert "Invalid phone format" in str(exc.value)
        assert exc.value.request_id is not None

    @pytest.mark.asyncio
    async def test_404_maps_to_not_found_error(self) -> None:
        """HTTP 404 maps to InsightsNotFoundError."""
        import respx

        from autom8_asana.exceptions import InsightsNotFoundError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
                status_code=404,
                json={"error": "No insights found for pv1:+17705753103:chiropractic"},
            )

            async with client:
                with pytest.raises(InsightsNotFoundError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert "No insights found" in str(exc.value)
        assert exc.value.request_id is not None

    @pytest.mark.asyncio
    async def test_500_maps_to_service_error(self) -> None:
        """HTTP 500 maps to InsightsServiceError."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
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

        assert "Internal server error" in str(exc.value)
        assert exc.value.status_code == 500
        assert exc.value.reason == "server_error"

    @pytest.mark.asyncio
    async def test_502_maps_to_service_error(self) -> None:
        """HTTP 502 maps to InsightsServiceError."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
                status_code=502,
                json={"error": "Bad gateway"},
            )

            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.status_code == 502
        assert exc.value.reason == "server_error"

    @pytest.mark.asyncio
    async def test_503_maps_to_service_error(self) -> None:
        """HTTP 503 maps to InsightsServiceError."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
                status_code=503,
                json={"error": "Service unavailable"},
            )

            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.status_code == 503

    @pytest.mark.asyncio
    async def test_504_maps_to_service_error(self) -> None:
        """HTTP 504 maps to InsightsServiceError."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
                status_code=504,
                json={"error": "Gateway timeout"},
            )

            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.status_code == 504

    @pytest.mark.asyncio
    async def test_timeout_maps_to_service_error(self) -> None:
        """Request timeout maps to InsightsServiceError."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").mock(
                side_effect=httpx.TimeoutException("Connection timed out")
            )

            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert "timed out" in str(exc.value)
        assert exc.value.reason == "timeout"

    @pytest.mark.asyncio
    async def test_http_error_maps_to_service_error(self) -> None:
        """Generic HTTP error maps to InsightsServiceError."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").mock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.reason == "http_error"

    @pytest.mark.asyncio
    async def test_error_includes_detail_field(self) -> None:
        """Error response with 'detail' field is extracted."""
        import respx

        from autom8_asana.exceptions import InsightsValidationError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
                status_code=400,
                json={"detail": "Validation failed: missing required field"},
            )

            async with client:
                with pytest.raises(InsightsValidationError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert "Validation failed" in str(exc.value)


@pytest.mark.usefixtures("enable_insights_feature")
class TestGetInsightsAsyncSuccessResponse:
    """Tests for successful response parsing."""

    @pytest.mark.asyncio
    async def test_parses_successful_response(self) -> None:
        """Successful response is parsed to InsightsResponse."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
                json={
                    "data": [
                        {"spend": 1500.00, "leads": 45, "cpl": 33.33},
                    ],
                    "metadata": {
                        "factory": "account",
                        "frame_type": "ACCOUNT_INSIGHTS",
                        "insights_period": "t30",
                        "row_count": 1,
                        "column_count": 3,
                        "columns": [
                            {"name": "spend", "dtype": "float64", "nullable": False},
                            {"name": "leads", "dtype": "int64", "nullable": False},
                            {"name": "cpl", "dtype": "float64", "nullable": True},
                        ],
                        "cache_hit": True,
                        "duration_ms": 45.2,
                        "sort_history": ["spend"],
                    },
                    "warnings": ["Some data may be incomplete"],
                }
            )

            async with client:
                response = await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                    period="t30",
                )

        assert len(response.data) == 1
        assert response.data[0]["spend"] == 1500.00
        assert response.metadata.factory == "account"
        assert response.metadata.frame_type == "ACCOUNT_INSIGHTS"
        assert response.metadata.row_count == 1
        assert response.metadata.cache_hit is True
        assert response.metadata.duration_ms == 45.2
        assert response.warnings == ["Some data may be incomplete"]
        assert response.request_id is not None

    @pytest.mark.asyncio
    async def test_parses_empty_response(self) -> None:
        """Empty data response is handled correctly."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "row_count": 0,
                        "column_count": 3,
                        "columns": [
                            {"name": "spend", "dtype": "float64"},
                            {"name": "leads", "dtype": "int64"},
                            {"name": "cpl", "dtype": "float64"},
                        ],
                        "cache_hit": False,
                        "duration_ms": 25.0,
                    },
                }
            )

            async with client:
                response = await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

        assert response.data == []
        assert response.metadata.row_count == 0
        assert len(response.metadata.columns) == 3

    @pytest.mark.asyncio
    async def test_uses_client_request_id_not_server(self) -> None:
        """Response uses client-generated request_id, not server's."""
        import respx

        client = DataServiceClient()
        server_request_id = "server-generated-id"

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
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
                    "request_id": server_request_id,  # Server sends this
                }
            )

            async with client:
                response = await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

        # Client generates its own request_id
        assert response.request_id != server_request_id
        # Should be a valid UUID
        import uuid
        uuid.UUID(response.request_id)


@pytest.mark.usefixtures("enable_insights_feature")
class TestGetInsightsAsyncIntegration:
    """Integration test for successful call pattern (mocked)."""

    @pytest.mark.asyncio
    async def test_full_successful_flow(self) -> None:
        """Full successful call flow: validate -> request -> parse -> return."""
        import respx

        from autom8_asana.clients.data.models import InsightsResponse

        config = DataServiceConfig(
            base_url="https://data.test.autom8.io",
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            respx.post("https://data.test.autom8.io/api/v1/factory/account").respond(
                json={
                    "data": [
                        {"spend": 2500.00, "leads": 75, "cpl": 33.33, "roas": 3.5},
                    ],
                    "metadata": {
                        "factory": "account",
                        "frame_type": "ACCOUNT_INSIGHTS",
                        "insights_period": "t30",
                        "row_count": 1,
                        "column_count": 4,
                        "columns": [
                            {"name": "spend", "dtype": "float64", "nullable": False},
                            {"name": "leads", "dtype": "int64", "nullable": False},
                            {"name": "cpl", "dtype": "float64", "nullable": True},
                            {"name": "roas", "dtype": "float64", "nullable": True},
                        ],
                        "cache_hit": False,
                        "duration_ms": 125.5,
                    },
                }
            )

            async with client:
                response = await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                    period="t30",
                    metrics=["spend", "leads", "cpl", "roas"],
                )

        # Verify response type and structure
        assert isinstance(response, InsightsResponse)
        assert response.metadata.factory == "account"
        assert response.metadata.row_count == 1
        assert response.data[0]["spend"] == 2500.00
        assert response.data[0]["leads"] == 75

        # Verify DataFrame conversion works
        df = response.to_dataframe()
        assert len(df) == 1
        assert "spend" in df.columns
        assert "leads" in df.columns

    @pytest.mark.asyncio
    @pytest.mark.parametrize("input_case,expected", [
        ("ACCOUNT", "account"),
        ("Account", "account"),
        ("aCcOuNt", "account"),
        ("ADS", "ads"),
        ("Campaigns", "campaigns"),
    ])
    async def test_factory_case_insensitive(self, input_case: str, expected: str) -> None:
        """Factory name validation is case-insensitive (e.g., ACCOUNT, Account work)."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            respx.post(f"/api/v1/factory/{expected}").respond(
                json={
                    "data": [],
                    "metadata": {
                        "factory": expected,
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                }
            )

            async with client:
                # Should work with any case
                response = await client.get_insights_async(
                    factory=input_case,
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )
                assert response is not None
                assert response.metadata.factory == expected

    @pytest.mark.asyncio
    async def test_with_all_optional_parameters(self) -> None:
        """Call with all optional parameters."""
        import respx
        from datetime import date

        client = DataServiceClient()
        captured_body: dict[str, Any] = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            import json
            captured_body = json.loads(request.content)
            return httpx.Response(
                200,
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
                },
            )

        with respx.mock:
            respx.post("/api/v1/factory/account").mock(side_effect=capture_request)

            async with client:
                await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                    period="t30",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    metrics=["spend", "leads"],
                    dimensions=["date"],
                    groups=["ad_account_id"],
                    break_down=["campaign_id"],
                    refresh=True,
                    filters={"ad_account_id": "123456"},
                )

        # Verify all parameters were sent
        assert captured_body["office_phone"] == "+17705753103"
        assert captured_body["vertical"] == "chiropractic"
        assert captured_body["insights_period"] == "t30"
        assert captured_body["start_date"] == "2024-01-01"
        assert captured_body["end_date"] == "2024-12-31"
        assert captured_body["metrics"] == ["spend", "leads"]
        assert captured_body["dimensions"] == ["date"]
        assert captured_body["groups"] == ["ad_account_id"]
        assert captured_body["break_down"] == ["campaign_id"]
        assert captured_body["refresh"] is True
        assert captured_body["filters"] == {"ad_account_id": "123456"}


# --- Story 1.7: Feature Flag Tests ---


class TestFeatureFlagDisabled:
    """Tests for feature flag disabled behavior (Story 1.7, updated per Story 2.7).

    Per Story 2.7: Feature is now enabled by default.
    Explicit opt-out requires setting env var to "false", "0", or "no".
    """

    @pytest.mark.asyncio
    async def test_disabled_when_env_var_false(self) -> None:
        """get_insights_async raises InsightsServiceError when env var is 'false'."""
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "false"}):
            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.reason == "feature_disabled"
        assert "Insights integration is disabled" in str(exc.value)

    @pytest.mark.asyncio
    async def test_disabled_when_env_var_zero(self) -> None:
        """get_insights_async raises InsightsServiceError when env var is '0'."""
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "0"}):
            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.reason == "feature_disabled"

    @pytest.mark.asyncio
    async def test_disabled_when_env_var_no(self) -> None:
        """get_insights_async raises InsightsServiceError when env var is 'no'."""
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "no"}):
            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.reason == "feature_disabled"

    @pytest.mark.asyncio
    async def test_disabled_with_case_variations(self) -> None:
        """Explicit disable values are case-insensitive."""
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        # Test case-insensitive opt-out values
        disabled_values = ["false", "FALSE", "False", "no", "NO", "No", "0"]

        for value in disabled_values:
            with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": value}):
                async with client:
                    with pytest.raises(InsightsServiceError) as exc:
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

                assert exc.value.reason == "feature_disabled", (
                    f"Expected feature_disabled for value '{value}'"
                )

    @pytest.mark.asyncio
    async def test_feature_check_happens_before_validation(self) -> None:
        """Feature flag check happens before any other validation."""
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        # Even with invalid inputs, feature flag check should happen first
        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "false"}):
            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="invalid_factory",  # Would fail validation
                        office_phone="not-a-phone",  # Would fail validation
                        vertical="",  # Would fail validation
                    )

        # Should get feature_disabled error, not validation error
        assert exc.value.reason == "feature_disabled"


class TestFeatureFlagEnabled:
    """Tests for feature flag enabled behavior (Story 1.7, updated per Story 2.7).

    Per Story 2.7: Feature is now enabled by default.
    """

    @pytest.mark.asyncio
    async def test_enabled_by_default_when_env_var_not_set(self) -> None:
        """get_insights_async succeeds when env var is not set (Story 2.7)."""
        import respx

        client = DataServiceClient()

        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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

                assert response.metadata.factory == "account"

    @pytest.mark.asyncio
    async def test_enabled_when_env_var_empty(self) -> None:
        """get_insights_async succeeds when env var is empty string (Story 2.7)."""
        import respx

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": ""}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                assert response is not None

    @pytest.mark.asyncio
    async def test_enabled_with_true_lowercase(self) -> None:
        """get_insights_async succeeds when env var is 'true'."""
        import respx

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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

                assert response.metadata.factory == "account"

    @pytest.mark.asyncio
    async def test_enabled_with_true_uppercase(self) -> None:
        """get_insights_async succeeds when env var is 'TRUE' (case-insensitive)."""
        import respx

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "TRUE"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                assert response is not None

    @pytest.mark.asyncio
    async def test_enabled_with_one(self) -> None:
        """get_insights_async succeeds when env var is '1'."""
        import respx

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "1"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                assert response is not None

    @pytest.mark.asyncio
    async def test_enabled_with_yes(self) -> None:
        """get_insights_async succeeds when env var is 'yes'."""
        import respx

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "yes"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                assert response is not None

    @pytest.mark.asyncio
    async def test_enabled_with_yes_uppercase(self) -> None:
        """get_insights_async succeeds when env var is 'YES' (case-insensitive)."""
        import respx

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "YES"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                assert response is not None


class TestCheckFeatureEnabled:
    """Direct tests for _check_feature_enabled() method (updated per Story 2.7)."""

    def test_does_not_raise_when_not_set(self) -> None:
        """_check_feature_enabled does not raise when env var not set (Story 2.7)."""
        client = DataServiceClient()

        with patch.dict(os.environ, {}, clear=True):
            # Should not raise - enabled by default
            client._check_feature_enabled()

    def test_does_not_raise_when_empty(self) -> None:
        """_check_feature_enabled does not raise when env var is empty (Story 2.7)."""
        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": ""}):
            # Should not raise - empty means enabled (default)
            client._check_feature_enabled()

    def test_does_not_raise_when_enabled(self) -> None:
        """_check_feature_enabled does not raise when explicitly enabled."""
        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            # Should not raise
            client._check_feature_enabled()

    def test_raises_when_explicitly_disabled(self) -> None:
        """_check_feature_enabled raises when explicitly set to false."""
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "false"}):
            with pytest.raises(InsightsServiceError) as exc:
                client._check_feature_enabled()

        assert exc.value.reason == "feature_disabled"

    def test_error_message_is_helpful(self) -> None:
        """Error message explains how to re-enable."""
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "false"}):
            with pytest.raises(InsightsServiceError) as exc:
                client._check_feature_enabled()

        error_message = str(exc.value)
        assert "Insights integration is disabled" in error_message
        # Updated per Story 2.7: message now explains how to re-enable
        assert "AUTOM8_DATA_INSIGHTS_ENABLED" in error_message
        assert "true" in error_message.lower()


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
                respx.post("/api/v1/factory/account").respond(
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
                respx.post("/api/v1/factory/account").respond(
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
                respx.post("/api/v1/factory/account").respond(
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
                route = respx.post("/api/v1/factory/account").respond(
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
                respx.post("/api/v1/factory/account").respond(
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
                respx.post("/api/v1/factory/account").respond(
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
                respx.post("/api/v1/factory/account").respond(
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
                respx.post("/api/v1/factory/account").respond(
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
                respx.post("/api/v1/factory/account").mock(
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
                respx.post("/api/v1/factory/account").mock(
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
                respx.post("/api/v1/factory/account").respond(
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
                respx.post("/api/v1/factory/account").respond(
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
                respx.post("/api/v1/factory/account").respond(
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
        mock_cache.set.side_effect = Exception("Cache write failed")

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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
        mock_cache.get.side_effect = Exception("Cache read failed")

        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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
        mock_cache.set.side_effect = Exception("Cache write failed")
        mock_logger = MagicMock()

        client = DataServiceClient(cache_provider=mock_cache, logger=mock_logger)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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
                respx.post("/api/v1/factory/account").respond(
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
        from datetime import datetime, timezone

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
                respx.post("/api/v1/factory/account").respond(
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
                respx.post("/api/v1/factory/account").respond(
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
                respx.post("/api/v1/factory/account").respond(
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


class TestEntryTypeInsights:
    """Tests for EntryType.INSIGHTS (Story 1.8)."""

    def test_insights_entry_type_exists(self) -> None:
        """EntryType.INSIGHTS is defined."""
        from autom8_asana.cache.entry import EntryType

        assert hasattr(EntryType, "INSIGHTS")
        assert EntryType.INSIGHTS.value == "insights"

    def test_insights_entry_type_is_string_enum(self) -> None:
        """EntryType.INSIGHTS is a string enum value."""
        from autom8_asana.cache.entry import EntryType

        assert isinstance(EntryType.INSIGHTS.value, str)
        assert EntryType.INSIGHTS == "insights"


# --- Story 1.9: Observability (Full Metrics) Tests ---


class TestMaskPhoneNumber:
    """Tests for mask_phone_number PII redaction helper (Story 1.9)."""

    def test_masks_standard_us_phone(self) -> None:
        """Standard US phone number is masked correctly."""
        from autom8_asana.clients.data.client import mask_phone_number

        result = mask_phone_number("+17705753103")

        assert result == "+1770***3103"

    def test_masks_phone_keep_first_five_last_four(self) -> None:
        """Keeps first 5 chars and last 4 chars, masks middle."""
        from autom8_asana.clients.data.client import mask_phone_number

        result = mask_phone_number("+14155551234")

        assert result == "+1415***1234"
        assert result.startswith("+1415")
        assert result.endswith("1234")

    def test_returns_short_phone_unchanged(self) -> None:
        """Short phone numbers (< 9 chars) are returned unchanged."""
        from autom8_asana.clients.data.client import mask_phone_number

        # Too short to mask meaningfully
        result = mask_phone_number("+123456")

        assert result == "+123456"

    def test_returns_empty_string_unchanged(self) -> None:
        """Empty string is returned unchanged."""
        from autom8_asana.clients.data.client import mask_phone_number

        result = mask_phone_number("")

        assert result == ""

    def test_returns_none_phone_unchanged(self) -> None:
        """None-like empty value is handled."""
        from autom8_asana.clients.data.client import mask_phone_number

        # Empty string edge case
        result = mask_phone_number("")

        assert result == ""

    def test_returns_non_e164_unchanged(self) -> None:
        """Non-E.164 format strings without + prefix are returned unchanged."""
        from autom8_asana.clients.data.client import mask_phone_number

        result = mask_phone_number("7705753103")

        # No + prefix, returned as-is
        assert result == "7705753103"

    def test_masks_international_phone(self) -> None:
        """International phone numbers are masked correctly."""
        from autom8_asana.clients.data.client import mask_phone_number

        # UK number
        result = mask_phone_number("+447911123456")

        assert result == "+4479***3456"


class TestMaskCanonicalKey:
    """Tests for _mask_canonical_key helper (Story 1.9)."""

    def test_masks_phone_in_canonical_key(self) -> None:
        """Phone number in canonical key is masked."""
        from autom8_asana.clients.data.client import _mask_canonical_key

        result = _mask_canonical_key("pv1:+17705753103:chiropractic")

        assert result == "pv1:+1770***3103:chiropractic"

    def test_preserves_version_and_vertical(self) -> None:
        """Version prefix and vertical are preserved."""
        from autom8_asana.clients.data.client import _mask_canonical_key

        result = _mask_canonical_key("pv1:+14155551234:dental")

        assert result.startswith("pv1:")
        assert result.endswith(":dental")

    def test_returns_non_pv1_unchanged(self) -> None:
        """Non-pv1 keys are returned unchanged."""
        from autom8_asana.clients.data.client import _mask_canonical_key

        result = _mask_canonical_key("other:+17705753103:vertical")

        assert result == "other:+17705753103:vertical"

    def test_returns_malformed_key_unchanged(self) -> None:
        """Malformed keys are returned unchanged."""
        from autom8_asana.clients.data.client import _mask_canonical_key

        result = _mask_canonical_key("notakey")

        assert result == "notakey"


class TestMetricsHook:
    """Tests for metrics hook integration (Story 1.9)."""

    def test_accepts_metrics_hook_parameter(self) -> None:
        """DataServiceClient accepts metrics_hook parameter."""
        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(metrics_hook=mock_hook)

        assert client._metrics_hook is mock_hook
        assert client.has_metrics is True

    def test_has_metrics_false_when_no_hook(self) -> None:
        """has_metrics returns False when no metrics_hook provided."""
        client = DataServiceClient()

        assert client.has_metrics is False

    def test_emit_metric_calls_hook(self) -> None:
        """_emit_metric calls the configured hook."""
        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(metrics_hook=mock_hook)

        client._emit_metric("test_metric", 42.5, {"factory": "account"})

        assert len(metrics_calls) == 1
        assert metrics_calls[0] == ("test_metric", 42.5, {"factory": "account"})

    def test_emit_metric_no_op_without_hook(self) -> None:
        """_emit_metric does nothing when no hook is configured."""
        client = DataServiceClient()

        # Should not raise
        client._emit_metric("test_metric", 1.0, {"tag": "value"})

    def test_emit_metric_catches_hook_errors(self) -> None:
        """_emit_metric catches and logs errors from hook."""
        def failing_hook(name: str, value: float, tags: dict[str, str]) -> None:
            raise RuntimeError("Hook failed")

        mock_logger = MagicMock()
        client = DataServiceClient(metrics_hook=failing_hook, logger=mock_logger)

        # Should not raise despite hook failure
        client._emit_metric("test_metric", 1.0, {"tag": "value"})

        # Warning should be logged
        mock_logger.warning.assert_called_once()


@pytest.mark.usefixtures("enable_insights_feature")
class TestObservabilityLogging:
    """Tests for structured logging (Story 1.9)."""

    @pytest.mark.asyncio
    async def test_request_started_log_emitted(self) -> None:
        """insights_request_started log is emitted at request start."""
        import respx

        mock_logger = MagicMock()
        client = DataServiceClient(logger=mock_logger)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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
                        period="t30",
                    )

        # Check for request started log
        info_calls = [call for call in mock_logger.info.call_args_list]
        assert len(info_calls) >= 1

        # First info call should be request started
        first_call = info_calls[0]
        assert first_call[0][0] == "insights_request_started"
        extra = first_call[1]["extra"]
        assert extra["factory"] == "account"
        assert extra["period"] == "t30"
        assert "request_id" in extra

    @pytest.mark.asyncio
    async def test_request_completed_log_emitted(self) -> None:
        """insights_request_completed log is emitted on success."""
        import respx

        mock_logger = MagicMock()
        client = DataServiceClient(logger=mock_logger)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
                    json={
                        "data": [{"spend": 100.0}],
                        "metadata": {
                            "factory": "account",
                            "row_count": 1,
                            "column_count": 1,
                            "columns": [{"name": "spend", "dtype": "float64"}],
                            "cache_hit": True,
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

        # Check for request completed log
        info_calls = [call for call in mock_logger.info.call_args_list]
        assert len(info_calls) >= 2

        # Second info call should be request completed
        completed_call = info_calls[1]
        assert completed_call[0][0] == "insights_request_completed"
        extra = completed_call[1]["extra"]
        assert extra["row_count"] == 1
        assert extra["cache_hit"] is True
        assert "duration_ms" in extra
        assert "request_id" in extra

    @pytest.mark.asyncio
    async def test_request_failed_log_emitted_on_error(self) -> None:
        """insights_request_failed log is emitted on error."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        mock_logger = MagicMock()
        client = DataServiceClient(logger=mock_logger)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
                    status_code=500,
                    json={"error": "Internal server error"},
                )

                async with client:
                    with pytest.raises(InsightsServiceError):
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

        # Check for request failed log
        error_calls = [call for call in mock_logger.error.call_args_list]
        assert len(error_calls) >= 1

        # Should have insights_request_failed log
        failed_call = error_calls[0]
        assert failed_call[0][0] == "insights_request_failed"
        extra = failed_call[1]["extra"]
        assert extra["status_code"] == 500
        assert extra["error_type"] == "server_error"
        assert "request_id" in extra
        assert "duration_ms" in extra

    @pytest.mark.asyncio
    async def test_phone_is_masked_in_logs(self) -> None:
        """Phone number is masked in pvp_canonical_key log field."""
        import respx

        mock_logger = MagicMock()
        client = DataServiceClient(logger=mock_logger)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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

        # Check that phone is masked in request started log
        info_calls = [call for call in mock_logger.info.call_args_list]
        request_started_call = info_calls[0]
        extra = request_started_call[1]["extra"]
        pvp_key = extra["pvp_canonical_key"]

        # Phone should be masked
        assert "+17705753103" not in pvp_key
        assert "+1770***3103" in pvp_key


@pytest.mark.usefixtures("enable_insights_feature")
class TestObservabilityMetrics:
    """Tests for metrics emission (Story 1.9)."""

    @pytest.mark.asyncio
    async def test_success_metrics_emitted(self) -> None:
        """Success metrics are emitted on successful request."""
        import respx

        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(metrics_hook=mock_hook)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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

        # Should have emitted insights_request_total and insights_request_latency_ms
        metric_names = [call[0] for call in metrics_calls]
        assert "insights_request_total" in metric_names
        assert "insights_request_latency_ms" in metric_names

        # Check insights_request_total
        total_call = next(c for c in metrics_calls if c[0] == "insights_request_total")
        assert total_call[1] == 1
        assert total_call[2]["factory"] == "account"
        assert total_call[2]["status"] == "success"

        # Check insights_request_latency_ms has positive duration
        latency_call = next(c for c in metrics_calls if c[0] == "insights_request_latency_ms")
        assert latency_call[1] > 0
        assert latency_call[2]["factory"] == "account"

    @pytest.mark.asyncio
    async def test_error_metrics_emitted_on_500(self) -> None:
        """Error metrics are emitted on 500 error."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(metrics_hook=mock_hook)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
                    status_code=500,
                    json={"error": "Internal server error"},
                )

                async with client:
                    with pytest.raises(InsightsServiceError):
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

        # Should have emitted error metrics
        metric_names = [call[0] for call in metrics_calls]
        assert "insights_request_error_total" in metric_names
        assert "insights_request_total" in metric_names
        assert "insights_request_latency_ms" in metric_names

        # Check error_total metric
        error_call = next(c for c in metrics_calls if c[0] == "insights_request_error_total")
        assert error_call[1] == 1
        assert error_call[2]["factory"] == "account"
        assert error_call[2]["error_type"] == "server_error"
        assert error_call[2]["status_code"] == "500"

    @pytest.mark.asyncio
    async def test_error_metrics_emitted_on_timeout(self) -> None:
        """Error metrics are emitted on timeout."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(metrics_hook=mock_hook)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").mock(
                    side_effect=httpx.TimeoutException("Timeout")
                )

                async with client:
                    with pytest.raises(InsightsServiceError):
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

        # Should have emitted error metrics with timeout type
        error_call = next(c for c in metrics_calls if c[0] == "insights_request_error_total")
        assert error_call[2]["error_type"] == "timeout"

    @pytest.mark.asyncio
    async def test_latency_metric_has_positive_value(self) -> None:
        """Latency metric has a positive value reflecting actual duration."""
        import respx

        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(metrics_hook=mock_hook)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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

        latency_call = next(c for c in metrics_calls if c[0] == "insights_request_latency_ms")
        # Should be a positive number (request took some time)
        assert latency_call[1] > 0
        # Should be in milliseconds (unlikely to exceed 10 seconds in test)
        assert latency_call[1] < 10000


@pytest.mark.usefixtures("enable_insights_feature")
class TestObservabilityIntegration:
    """Integration tests for full observability stack (Story 1.9)."""

    @pytest.mark.asyncio
    async def test_full_observability_on_success(self) -> None:
        """Full observability: logging + metrics on successful request."""
        import respx

        mock_logger = MagicMock()
        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(logger=mock_logger, metrics_hook=mock_hook)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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
                        period="t30",
                    )

        # Response should be valid
        assert response.data == [{"spend": 100.0}]

        # Logging should have happened
        assert mock_logger.info.call_count >= 2  # started + completed
        info_msgs = [call[0][0] for call in mock_logger.info.call_args_list]
        assert "insights_request_started" in info_msgs
        assert "insights_request_completed" in info_msgs

        # Metrics should have been emitted
        assert len(metrics_calls) >= 2
        metric_names = [call[0] for call in metrics_calls]
        assert "insights_request_total" in metric_names
        assert "insights_request_latency_ms" in metric_names

    @pytest.mark.asyncio
    async def test_full_observability_on_error(self) -> None:
        """Full observability: logging + metrics on error."""
        import respx

        from autom8_asana.exceptions import InsightsValidationError

        mock_logger = MagicMock()
        metrics_calls: list[tuple[str, float, dict[str, str]]] = []

        def mock_hook(name: str, value: float, tags: dict[str, str]) -> None:
            metrics_calls.append((name, value, tags))

        client = DataServiceClient(logger=mock_logger, metrics_hook=mock_hook)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.post("/api/v1/factory/account").respond(
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

        # Error logging should have happened
        assert mock_logger.error.call_count >= 1
        error_msgs = [call[0][0] for call in mock_logger.error.call_args_list]
        assert "insights_request_failed" in error_msgs

        # Error metrics should have been emitted
        metric_names = [call[0] for call in metrics_calls]
        assert "insights_request_error_total" in metric_names


# --- Story 2.6: Sync Wrapper Tests ---


@pytest.mark.usefixtures("enable_insights_feature")
class TestSyncWrapper:
    """Tests for get_insights sync wrapper and sync context manager."""

    def test_sync_wrapper_works(self) -> None:
        """Sync method works from sync context."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
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

            # Note: use sync context manager (not async)
            with client:
                response = client.get_insights(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )
                assert response.metadata.factory == "account"
                assert response.metadata.row_count == 1

    @pytest.mark.asyncio
    async def test_sync_wrapper_raises_in_async_context(self) -> None:
        """Sync wrapper raises SyncInAsyncContextError in async context."""
        from autom8_asana.exceptions import SyncInAsyncContextError

        client = DataServiceClient()

        async with client:
            with pytest.raises(SyncInAsyncContextError) as exc:
                client.get_insights(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

        assert "get_insights" in str(exc.value)
        assert "get_insights_async" in str(exc.value)

    def test_sync_wrapper_passes_all_parameters(self) -> None:
        """Sync method passes all parameters to async method."""
        import respx
        from datetime import date

        client = DataServiceClient()
        captured_body: dict[str, Any] = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            import json
            captured_body = json.loads(request.content)
            return httpx.Response(
                200,
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
                },
            )

        with respx.mock:
            respx.post("/api/v1/factory/account").mock(side_effect=capture_request)

            with client:
                client.get_insights(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                    period="t30",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    metrics=["spend", "leads"],
                    dimensions=["day"],
                    groups=["platform"],
                    break_down=["campaign"],
                    refresh=True,
                    filters={"platform": "facebook"},
                )

        # Verify all parameters were passed through
        assert captured_body["office_phone"] == "+17705753103"
        assert captured_body["vertical"] == "chiropractic"
        assert captured_body["insights_period"] == "t30"
        assert captured_body["start_date"] == "2024-01-01"
        assert captured_body["end_date"] == "2024-12-31"
        assert captured_body["metrics"] == ["spend", "leads"]
        assert captured_body["dimensions"] == ["day"]
        assert captured_body["groups"] == ["platform"]
        assert captured_body["break_down"] == ["campaign"]
        assert captured_body["refresh"] is True
        assert captured_body["filters"] == {"platform": "facebook"}

    def test_sync_context_manager_works(self) -> None:
        """Sync context manager (__enter__/__exit__) works in sync context."""
        client = DataServiceClient()

        # Should not raise
        with client as entered:
            assert entered is client
            assert client.is_initialized is False  # lazy init

    @pytest.mark.asyncio
    async def test_sync_exit_raises_in_async_context(self) -> None:
        """Sync __exit__ raises SyncInAsyncContextError in async context."""
        from autom8_asana.exceptions import SyncInAsyncContextError

        client = DataServiceClient()

        # Enter works (just returns self)
        entered = client.__enter__()
        assert entered is client

        # Exit should raise in async context
        with pytest.raises(SyncInAsyncContextError) as exc:
            client.__exit__(None, None, None)

        assert "__exit__" in str(exc.value)
        assert "__aexit__" in str(exc.value)

    def test_sync_wrapper_propagates_validation_errors(self) -> None:
        """Sync wrapper propagates InsightsValidationError correctly."""
        from autom8_asana.exceptions import InsightsValidationError

        client = DataServiceClient()

        with client:
            with pytest.raises(InsightsValidationError) as exc:
                client.get_insights(
                    factory="invalid_factory",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

        assert "Invalid factory" in str(exc.value)

    def test_sync_wrapper_propagates_service_errors(self) -> None:
        """Sync wrapper propagates InsightsServiceError correctly."""
        import respx

        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
                status_code=500,
                json={"error": "Internal server error"},
            )

            with client:
                with pytest.raises(InsightsServiceError) as exc:
                    client.get_insights(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.status_code == 500


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

        from autom8_asana.transport.circuit_breaker import CircuitState

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
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

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self) -> None:
        """Circuit opens after 5 consecutive failures (503 responses)."""
        import respx

        from autom8_asana.clients.data.config import CircuitBreakerConfig
        from autom8_asana.exceptions import InsightsServiceError
        from autom8_asana.transport.circuit_breaker import CircuitState

        # Use config with default failure_threshold=5
        config = DataServiceConfig(
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=5,
                recovery_timeout=30.0,
                half_open_max_calls=1,
            )
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            # Mock 5 consecutive 503 responses
            respx.post("/api/v1/factory/account").respond(
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

    @pytest.mark.asyncio
    async def test_circuit_open_raises_immediately(self) -> None:
        """When circuit is open, raises InsightsServiceError with reason='circuit_breaker'."""
        import respx

        from autom8_asana.clients.data.config import CircuitBreakerConfig
        from autom8_asana.exceptions import InsightsServiceError
        from autom8_asana.transport.circuit_breaker import CircuitState

        config = DataServiceConfig(
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=5,
                recovery_timeout=30.0,  # Long timeout so circuit stays open
                half_open_max_calls=1,
            )
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            route = respx.post("/api/v1/factory/account").respond(
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

        from autom8_asana.clients.data.config import CircuitBreakerConfig
        from autom8_asana.exceptions import InsightsServiceError
        from autom8_asana.transport.circuit_breaker import CircuitState

        from autom8_asana.clients.data.config import RetryConfig

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
            route = respx.post("/api/v1/factory/account").respond(
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

        from autom8_asana.clients.data.config import CircuitBreakerConfig, RetryConfig
        from autom8_asana.exceptions import InsightsServiceError
        from autom8_asana.transport.circuit_breaker import CircuitState

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
            respx.post("/api/v1/factory/account").mock(side_effect=handle_request)

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

        from autom8_asana.clients.data.config import CircuitBreakerConfig, RetryConfig
        from autom8_asana.exceptions import InsightsServiceError
        from autom8_asana.transport.circuit_breaker import CircuitState

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
            respx.post("/api/v1/factory/account").respond(
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
            route = respx.post("/api/v1/factory/account").mock(
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
            route = respx.post("/api/v1/factory/account").mock(
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
            route = respx.post("/api/v1/factory/account").mock(
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
        from autom8_asana.exceptions import InsightsServiceError

        config = DataServiceConfig(
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
            )
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            route = respx.post("/api/v1/factory/account").mock(
                side_effect=[
                    Response(503, json={"error": "service unavailable"}),
                    Response(503, json={"error": "service unavailable"}),
                    Response(503, json={"error": "service unavailable"}),  # 3rd call, retries exhausted
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
        from unittest.mock import AsyncMock, patch

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
            route = respx.post("/api/v1/factory/account").mock(
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
        from httpx import Response

        from autom8_asana.clients.data.config import RetryConfig
        from autom8_asana.exceptions import InsightsValidationError

        config = DataServiceConfig(
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
            )
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            route = respx.post("/api/v1/factory/account").respond(
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
        from httpx import Response

        from autom8_asana.clients.data.config import RetryConfig
        from autom8_asana.exceptions import InsightsNotFoundError

        config = DataServiceConfig(
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
            )
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            route = respx.post("/api/v1/factory/account").respond(
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
            respx.post("/api/v1/factory/account").mock(side_effect=handle_request)

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
        from autom8_asana.exceptions import InsightsServiceError

        config = DataServiceConfig(
            retry=RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
            )
        )
        client = DataServiceClient(config=config)

        with respx.mock:
            respx.post("/api/v1/factory/account").mock(
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


# --- Story 2.4: Batch Insights Tests ---


@pytest.fixture
def sample_pvps() -> list:
    """Create sample PhoneVerticalPairs for batch testing."""
    from autom8_asana.models.contracts import PhoneVerticalPair

    return [
        PhoneVerticalPair(office_phone="+17705753103", vertical="chiropractic"),
        PhoneVerticalPair(office_phone="+14155551234", vertical="dental"),
        PhoneVerticalPair(office_phone="+12125559876", vertical="medical"),
    ]


def make_insights_response(factory: str = "account", spend: float = 100.0) -> dict:
    """Create a valid insights response for testing."""
    return {
        "data": [{"spend": spend, "leads": 10}],
        "metadata": {
            "factory": factory,
            "row_count": 1,
            "column_count": 2,
            "columns": [
                {"name": "spend", "dtype": "float64"},
                {"name": "leads", "dtype": "int64"},
            ],
            "cache_hit": False,
            "duration_ms": 50.0,
        },
    }


@pytest.mark.usefixtures("enable_insights_feature")
class TestGetInsightsBatchAsync:
    """Tests for get_insights_batch_async method (Story 2.4)."""

    @pytest.mark.asyncio
    async def test_batch_success_all_pvps(self, sample_pvps: list) -> None:
        """Happy path - batch with 3 PVPs, all succeed."""
        import respx

        from autom8_asana.clients.data.models import BatchInsightsResponse

        client = DataServiceClient()

        with respx.mock:
            # Mock responses for each PVP
            respx.post("/api/v1/factory/account").respond(
                json=make_insights_response(spend=100.0)
            )

            async with client:
                result = await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                )

        assert isinstance(result, BatchInsightsResponse)
        assert result.total_count == 3
        assert result.success_count == 3
        assert result.failure_count == 0
        assert result.request_id is not None

        # All results should be present and successful
        for pvp in sample_pvps:
            batch_result = result.results.get(pvp.canonical_key)
            assert batch_result is not None
            assert batch_result.success is True
            assert batch_result.response is not None
            assert batch_result.error is None

    @pytest.mark.asyncio
    async def test_partial_failure_one_pvp_fails(self, sample_pvps: list) -> None:
        """Partial failure - 3 PVPs, 1 fails with 404, others succeed."""
        import respx

        client = DataServiceClient()
        call_count = 0

        def handle_request(request: Any) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # First call fails with 404, others succeed
            if call_count == 1:
                return httpx.Response(
                    404,
                    json={"error": "No insights found for business"},
                )
            return httpx.Response(200, json=make_insights_response())

        with respx.mock:
            respx.post("/api/v1/factory/account").mock(side_effect=handle_request)

            async with client:
                result = await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                )

        # Verify partial success/failure counts
        assert result.total_count == 3
        assert result.success_count == 2
        assert result.failure_count == 1

        # Verify failed results contain error message
        failed_results = result.failed_results()
        assert len(failed_results) == 1
        assert failed_results[0].error is not None
        assert failed_results[0].success is False
        assert failed_results[0].response is None

        # Verify successful results
        successful_results = result.successful_results()
        assert len(successful_results) == 2
        for success_result in successful_results:
            assert success_result.success is True
            assert success_result.response is not None

    @pytest.mark.asyncio
    async def test_batch_size_exceeds_max_raises_validation_error(
        self, sample_pvps: list
    ) -> None:
        """Batch size validation - exceeds max_batch_size raises InsightsValidationError."""
        from autom8_asana.exceptions import InsightsValidationError

        # Create config with very small max_batch_size
        config = DataServiceConfig(
            base_url="https://test.example.com",
            max_batch_size=2,  # Smaller than our 3 PVPs
        )
        client = DataServiceClient(config=config)

        async with client:
            with pytest.raises(InsightsValidationError) as exc:
                await client.get_insights_batch_async(
                    pairs=sample_pvps,  # 3 PVPs, max is 2
                    factory="account",
                )

        assert "Batch size 3 exceeds maximum 2" in str(exc.value)
        assert exc.value.field == "pairs"
        assert exc.value.request_id is not None

    @pytest.mark.asyncio
    async def test_invalid_factory_raises_validation_error(
        self, sample_pvps: list
    ) -> None:
        """Invalid factory - raises InsightsValidationError."""
        from autom8_asana.exceptions import InsightsValidationError

        client = DataServiceClient()

        async with client:
            with pytest.raises(InsightsValidationError) as exc:
                await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="not_a_valid_factory",
                )

        assert "Invalid factory" in str(exc.value)
        assert "not_a_valid_factory" in str(exc.value)
        assert exc.value.field == "factory"

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_raises_service_error(
        self, sample_pvps: list
    ) -> None:
        """Feature flag disabled - raises InsightsServiceError with reason='feature_disabled'.

        Per Story 2.7: Feature is now enabled by default. Must explicitly disable.
        """
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        # Explicitly disable feature flag (per Story 2.7: default is now enabled)
        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "false"}):
            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_batch_async(
                        pairs=sample_pvps,
                        factory="account",
                    )

        assert exc.value.reason == "feature_disabled"
        assert "Insights integration is disabled" in str(exc.value)

    @pytest.mark.asyncio
    async def test_concurrency_limiting_semaphore(self, sample_pvps: list) -> None:
        """Concurrency limiting - verify semaphore limits concurrent requests."""
        import respx

        client = DataServiceClient()
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def handle_request(request: Any) -> httpx.Response:
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent

            # Simulate some async work
            await asyncio.sleep(0.05)

            async with lock:
                current_concurrent -= 1

            return httpx.Response(200, json=make_insights_response())

        with respx.mock:
            respx.post("/api/v1/factory/account").mock(side_effect=handle_request)

            async with client:
                # Use max_concurrency=2, with 3 PVPs
                await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                    max_concurrency=2,
                )

        # Should never exceed max_concurrency
        assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_metrics_emission(self, sample_pvps: list) -> None:
        """Metrics emission - verify all 4 batch metrics emitted."""
        import respx

        client = DataServiceClient()
        emitted_metrics: list[tuple[str, float, dict]] = []

        original_emit = client._emit_metric

        def capture_metric(name: str, value: float, tags: dict) -> None:
            emitted_metrics.append((name, value, tags))
            original_emit(name, value, tags)

        with patch.object(client, "_emit_metric", side_effect=capture_metric):
            call_count = 0

            def handle_request(request: Any) -> httpx.Response:
                nonlocal call_count
                call_count += 1
                # Make one request fail
                if call_count == 2:
                    return httpx.Response(
                        500, json={"error": "Internal server error"}
                    )
                return httpx.Response(200, json=make_insights_response())

            with respx.mock:
                respx.post("/api/v1/factory/account").mock(side_effect=handle_request)

                async with client:
                    await client.get_insights_batch_async(
                        pairs=sample_pvps,
                        factory="account",
                    )

        # Extract metric names
        metric_names = [m[0] for m in emitted_metrics]

        # Note: individual request metrics are also emitted, we check batch-specific
        assert "insights_batch_total" in metric_names
        assert "insights_batch_size" in metric_names
        assert "insights_batch_success_count" in metric_names
        assert "insights_batch_failure_count" in metric_names

        # Verify metric values
        batch_total = next(m for m in emitted_metrics if m[0] == "insights_batch_total")
        assert batch_total[1] == 1
        assert batch_total[2]["factory"] == "account"

        batch_size = next(m for m in emitted_metrics if m[0] == "insights_batch_size")
        assert batch_size[1] == 3.0

        success_count = next(
            m for m in emitted_metrics if m[0] == "insights_batch_success_count"
        )
        assert success_count[1] == 2.0

        failure_count = next(
            m for m in emitted_metrics if m[0] == "insights_batch_failure_count"
        )
        assert failure_count[1] == 1.0

    @pytest.mark.asyncio
    async def test_empty_batch_graceful_handling(self) -> None:
        """Empty batch - verify graceful handling."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            async with client:
                result = await client.get_insights_batch_async(
                    pairs=[],
                    factory="account",
                )

        assert result.total_count == 0
        assert result.success_count == 0
        assert result.failure_count == 0
        assert result.results == {}
        assert result.request_id is not None

    @pytest.mark.asyncio
    async def test_batch_result_to_dataframe(self, sample_pvps: list) -> None:
        """Test that batch results can be converted to DataFrame."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
                json=make_insights_response(spend=150.0)
            )

            async with client:
                result = await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                )

        # Convert to DataFrame
        df = result.to_dataframe()
        assert len(df) == 3  # One row per successful PVP
        assert "spend" in df.columns
        assert "_pvp_key" in df.columns  # Added by to_dataframe

    @pytest.mark.asyncio
    async def test_batch_get_by_pvp(self, sample_pvps: list) -> None:
        """Test that results can be retrieved by PVP."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
                json=make_insights_response()
            )

            async with client:
                result = await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                )

        # Get result by PVP
        first_pvp = sample_pvps[0]
        batch_result = result.get(first_pvp)
        assert batch_result is not None
        assert batch_result.pvp == first_pvp
        assert batch_result.success is True

    @pytest.mark.asyncio
    async def test_factory_case_insensitive(self, sample_pvps: list) -> None:
        """Factory name is case-insensitive."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/factory/account").respond(
                json=make_insights_response()
            )

            async with client:
                result = await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="ACCOUNT",  # Uppercase
                )

        assert result.success_count == 3

    @pytest.mark.asyncio
    async def test_batch_with_custom_period_and_refresh(
        self, sample_pvps: list
    ) -> None:
        """Batch passes period and refresh parameters to individual requests."""
        import json

        import respx

        client = DataServiceClient()
        captured_bodies: list[dict] = []

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured_bodies.append(json.loads(request.content))
            return httpx.Response(200, json=make_insights_response())

        with respx.mock:
            respx.post("/api/v1/factory/account").mock(side_effect=capture_request)

            async with client:
                await client.get_insights_batch_async(
                    pairs=sample_pvps,
                    factory="account",
                    period="t30",
                    refresh=True,
                )

        # Verify all requests have the period and refresh parameters
        for body in captured_bodies:
            assert body["insights_period"] == "t30"
            assert body["refresh"] is True
