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

import pytest
from autom8y_http import HttpClientConfig

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
        from autom8_asana.cache.models.staleness_settings import StalenessCheckSettings

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

    async def test_aenter_returns_self(self) -> None:
        """__aenter__ returns the client instance."""
        client = DataServiceClient()

        async with client as entered:
            assert entered is client

    async def test_aexit_closes_client(self) -> None:
        """__aexit__ calls close() to release resources."""
        client = DataServiceClient()

        mock_close = AsyncMock()
        client._client = MagicMock()
        client._client.close = mock_close

        async with client:
            pass

        mock_close.assert_called_once()
        assert client._client is None

    async def test_context_manager_closes_on_exception(self) -> None:
        """Context manager closes client even on exception."""
        client = DataServiceClient()

        with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
            with pytest.raises(ValueError):
                async with client:
                    raise ValueError("test error")

            mock_close.assert_called_once()

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

    async def test_close_closes_http_client(self) -> None:
        """close() calls close() on Autom8yHttpClient."""
        client = DataServiceClient()

        mock_http = AsyncMock()
        client._client = mock_http

        await client.close()

        mock_http.close.assert_called_once()
        assert client._client is None

    async def test_close_is_idempotent(self) -> None:
        """close() can be called multiple times safely."""
        client = DataServiceClient()

        # First call does nothing (no client)
        await client.close()
        assert client._client is None

        # Second call also does nothing
        await client.close()
        assert client._client is None

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

    async def test_creates_httpx_client(self) -> None:
        """_get_client creates Autom8yHttpClient with correct config."""
        config = DataServiceConfig(
            base_url="https://test.example.com",
        )
        client = DataServiceClient(config=config)

        with patch("autom8_asana.clients.data.client.Autom8yHttpClient") as mock_class:
            mock_instance = MagicMock()
            mock_instance._client = MagicMock()
            mock_instance._client.headers = {}
            mock_instance.close = AsyncMock()
            mock_class.return_value = mock_instance

            await client._get_client()

            mock_class.assert_called_once()
            call_kwargs = mock_class.call_args.kwargs
            http_config = call_kwargs["config"]
            assert isinstance(http_config, HttpClientConfig)
            assert http_config.base_url == "https://test.example.com"

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

        with patch("autom8_asana.clients.data.client.Autom8yHttpClient") as mock_class:
            mock_instance = MagicMock()
            mock_instance._client = MagicMock()
            mock_instance._client.headers = {}
            mock_instance.close = AsyncMock()
            mock_class.return_value = mock_instance

            await client._get_client()

            call_kwargs = mock_class.call_args.kwargs
            http_config = call_kwargs["config"]
            assert http_config.connect_timeout == 10.0
            assert http_config.read_timeout == 60.0
            assert http_config.write_timeout == 45.0
            assert http_config.pool_timeout == 8.0

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

        with patch("autom8_asana.clients.data.client.Autom8yHttpClient") as mock_class:
            mock_instance = MagicMock()
            mock_instance._client = MagicMock()
            mock_instance._client.headers = {}
            mock_instance.close = AsyncMock()
            mock_class.return_value = mock_instance

            await client._get_client()

            call_kwargs = mock_class.call_args.kwargs
            http_config = call_kwargs["config"]
            assert http_config.max_connections == 20
            assert http_config.max_keepalive_connections == 10
            assert http_config.keepalive_expiry == 60.0

    async def test_includes_auth_header_when_token_available(self) -> None:
        """_get_client includes Authorization header when token is available."""
        mock_auth = MagicMock()
        mock_auth.get_secret.return_value = "test-jwt-token"

        client = DataServiceClient(auth_provider=mock_auth)

        with patch("autom8_asana.clients.data.client.Autom8yHttpClient") as mock_class:
            mock_instance = MagicMock()
            mock_instance._client = MagicMock()
            mock_instance._client.headers = {}
            mock_instance.close = AsyncMock()
            mock_class.return_value = mock_instance

            await client._get_client()

            assert mock_instance._client.headers["Authorization"] == "Bearer test-jwt-token"

    async def test_no_auth_header_when_no_token(self) -> None:
        """_get_client omits Authorization header when no token."""
        config = DataServiceConfig(
            base_url="https://test.example.com",
            token_key="NONEXISTENT_KEY",
        )
        client = DataServiceClient(config=config)

        with patch("autom8_asana.clients.data.client.Autom8yHttpClient") as mock_class:
            mock_instance = MagicMock()
            mock_instance._client = MagicMock()
            mock_instance._client.headers = {}
            mock_instance.close = AsyncMock()
            mock_class.return_value = mock_instance

            with patch.dict(os.environ, {}, clear=True):
                await client._get_client()

            assert "Authorization" not in mock_instance._client.headers

    async def test_includes_content_type_headers(self) -> None:
        """_get_client includes Accept and Content-Type headers."""
        client = DataServiceClient()

        with patch("autom8_asana.clients.data.client.Autom8yHttpClient") as mock_class:
            mock_instance = MagicMock()
            mock_instance._client = MagicMock()
            mock_instance._client.headers = {}
            mock_instance.close = AsyncMock()
            mock_class.return_value = mock_instance

            await client._get_client()

            assert mock_instance._client.headers["Accept"] == "application/json"
            assert mock_instance._client.headers["Content-Type"] == "application/json"

    async def test_returns_same_client_on_subsequent_calls(self) -> None:
        """_get_client returns cached client on subsequent calls."""
        client = DataServiceClient()

        with patch("autom8_asana.clients.data.client.Autom8yHttpClient") as mock_class:
            mock_instance = MagicMock()
            mock_instance._client = MagicMock()
            mock_instance._client.headers = {}
            mock_instance.close = AsyncMock()
            mock_class.return_value = mock_instance

            result1 = await client._get_client()
            result2 = await client._get_client()

            # Only created once
            assert mock_class.call_count == 1
            assert result1 is result2

    async def test_sets_is_initialized_after_creation(self) -> None:
        """_get_client sets is_initialized to True."""
        client = DataServiceClient()

        assert client.is_initialized is False

        with patch("autom8_asana.clients.data.client.Autom8yHttpClient") as mock_class:
            mock_instance = MagicMock()
            mock_instance._client = MagicMock()
            mock_instance._client.headers = {}
            mock_instance.close = AsyncMock()
            mock_class.return_value = mock_instance

            await client._get_client()

        assert client.is_initialized is True

    async def test_logs_when_logger_provided(self) -> None:
        """_get_client logs when logger is provided."""
        mock_logger = MagicMock()
        client = DataServiceClient(logger=mock_logger)

        with patch("autom8_asana.clients.data.client.Autom8yHttpClient") as mock_class:
            mock_instance = MagicMock()
            mock_instance._client = MagicMock()
            mock_instance._client.headers = {}
            mock_instance.close = AsyncMock()
            mock_class.return_value = mock_instance

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
        mock_auth.get_secret.assert_called_once_with("AUTOM8Y_DATA_API_KEY")

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
        mock_auth.get_secret.side_effect = KeyError("Provider error")
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

    def test_resolves_token_via_arn_extension(self) -> None:
        """Resolves token via Lambda extension when {KEY}_ARN is set."""
        config = DataServiceConfig(
            base_url="https://test.example.com",
            token_key="AUTOM8Y_DATA_API_KEY",
        )
        client = DataServiceClient(config=config)

        with (
            patch.dict(
                os.environ,
                {"AUTOM8Y_DATA_API_KEY_ARN": "arn:aws:secretsmanager:us-east-1:123:secret:key"},
                clear=False,
            ),
            patch(
                "autom8y_config.lambda_extension.resolve_secret_arn",
                return_value="resolved-api-key",
            ),
        ):
            token = client._get_auth_token()

        assert token == "resolved-api-key"


class TestDataServiceClientConcurrency:
    """Tests for thread-safety and concurrent access."""

    async def test_concurrent_get_client_creates_only_one(self) -> None:
        """Multiple concurrent _get_client calls create only one client."""
        client = DataServiceClient()
        creation_count = 0

        def mock_create(*args: Any, **kwargs: Any) -> MagicMock:
            nonlocal creation_count
            creation_count += 1
            instance = MagicMock()
            instance._client = MagicMock()
            instance._client.headers = {}
            instance.close = AsyncMock()
            return instance

        with patch(
            "autom8_asana.clients.data.client.Autom8yHttpClient",
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
