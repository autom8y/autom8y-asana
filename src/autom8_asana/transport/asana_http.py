"""Asana HTTP client wrapping autom8y-http platform client.

Per TDD-ASANA-HTTP-MIGRATION-001/FR-001: Thin wrapper providing Asana-specific
response handling while delegating HTTP operations to Autom8yHttpClient.

This module implements the transport wrapper that:
1. Maintains backward-compatible API matching AsyncHTTPClient
2. Delegates HTTP operations to Autom8yHttpClient (platform SDK)
3. Applies Asana-specific response unwrapping and error handling
4. Accepts injected shared rate limiter and circuit breaker instances

The key architectural decision (per ADR-0061) is that this is a thin wrapper,
not a facade or direct replacement. The wrapper handles Asana-specific concerns
while the platform client handles generic HTTP concerns.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from autom8y_http import (
    Autom8yHttpClient,
    CircuitBreaker,
    ExponentialBackoffRetry,
    HTTPError,
    RateLimiterProtocol,
    Response,
    TimeoutException,
    TokenBucketRateLimiter,
)
from autom8y_log import LoggerProtocol

from autom8_asana.exceptions import (
    AsanaError,
    RateLimitError,
    ServerError,
    TimeoutError,
)
from autom8_asana.transport.adaptive_semaphore import (
    AIMDConfig,
    AsyncAdaptiveSemaphore,
    FixedSemaphoreAdapter,
)
from autom8_asana.transport.config_translator import ConfigTranslator
from autom8_asana.transport.response_handler import AsanaResponseHandler

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from autom8y_http import CircuitBreakerProtocol, RetryPolicyProtocol

    from autom8_asana.config import AsanaConfig
    from autom8_asana.protocols.auth import AuthProvider
    from autom8_asana.protocols.log import LogProvider

__all__ = ["AsanaHttpClient"]


class AsanaHttpClient:
    """Asana HTTP client wrapping autom8y-http platform client.

    Per TDD-ASANA-HTTP-MIGRATION-001: Thin wrapper providing Asana-specific
    response handling while delegating HTTP operations to Autom8yHttpClient.

    This client provides:
    - Backward-compatible API matching AsyncHTTPClient
    - Asana response unwrapping ({"data": ...} envelope extraction)
    - Shared rate limiter injection (per ADR-0062)
    - Circuit breaker protection
    - Retry with exponential backoff

    Args:
        config: Asana SDK configuration.
        auth_provider: Authentication provider for API token.
        rate_limiter: Shared rate limiter (created from config if None).
        circuit_breaker: Shared circuit breaker (created from config if None).
        retry_policy: Shared retry policy (created from config if None).
        logger: Optional logger for request logging.

    Example:
        >>> from autom8_asana.config import AsanaConfig
        >>> config = AsanaConfig()
        >>> auth = MyAuthProvider()
        >>>
        >>> # With shared rate limiter
        >>> rate_limiter = TokenBucketRateLimiter(...)
        >>> client = AsanaHttpClient(
        ...     config=config,
        ...     auth_provider=auth,
        ...     rate_limiter=rate_limiter,
        ... )
        >>>
        >>> task = await client.get("/tasks/123")
    """

    def __init__(
        self,
        config: AsanaConfig,
        auth_provider: AuthProvider,
        *,
        rate_limiter: RateLimiterProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
        retry_policy: RetryPolicyProtocol | None = None,
        logger: LogProvider | LoggerProtocol | None = None,
    ) -> None:
        """Initialize Asana HTTP client.

        Args:
            config: Asana SDK configuration.
            auth_provider: Authentication provider for API token.
            rate_limiter: Shared rate limiter (created from config if None).
            circuit_breaker: Shared circuit breaker (created from config if None).
            retry_policy: Shared retry policy (created from config if None).
            logger: Optional logger for request logging.

        Key behaviors:
        - If rate_limiter is None, creates one from config.rate_limit
        - If circuit_breaker is None, creates one from config.circuit_breaker
        - If retry_policy is None, creates one from config.retry
        - Rate limiter, circuit breaker, and retry policy are shared instances
        """
        self._config = config
        self._auth_provider = auth_provider
        self._logger = logger

        # Store references for shared policy access
        self._rate_limiter = rate_limiter or self._create_rate_limiter()
        self._circuit_breaker = circuit_breaker or self._create_circuit_breaker()
        self._retry_policy = retry_policy or self._create_retry_policy()

        # Concurrency semaphores with AIMD adaptive control (per TDD-GAP-04)
        # Both AsyncAdaptiveSemaphore and FixedSemaphoreAdapter provide the same
        # acquire() -> Slot interface, so _request() uses a unified code path.
        if config.concurrency.aimd_enabled:
            cc = config.concurrency
            read_aimd_config = AIMDConfig(
                ceiling=cc.read_limit,
                floor=cc.aimd_floor,
                multiplicative_decrease=cc.aimd_multiplicative_decrease,
                additive_increase=cc.aimd_additive_increase,
                grace_period_seconds=cc.aimd_grace_period_seconds,
                increase_interval_seconds=cc.aimd_increase_interval_seconds,
                cooldown_trigger=cc.aimd_cooldown_trigger,
                cooldown_duration_seconds=cc.aimd_cooldown_duration_seconds,
            )
            write_aimd_config = AIMDConfig(
                ceiling=cc.write_limit,
                floor=cc.aimd_floor,
                multiplicative_decrease=cc.aimd_multiplicative_decrease,
                additive_increase=cc.aimd_additive_increase,
                grace_period_seconds=cc.aimd_grace_period_seconds,
                increase_interval_seconds=cc.aimd_increase_interval_seconds,
                cooldown_trigger=cc.aimd_cooldown_trigger,
                cooldown_duration_seconds=cc.aimd_cooldown_duration_seconds,
            )
            semaphore_logger: LoggerProtocol | None = (
                logger if isinstance(logger, LoggerProtocol) else None
            )
            self._read_semaphore: AsyncAdaptiveSemaphore | FixedSemaphoreAdapter = (
                AsyncAdaptiveSemaphore(
                    config=read_aimd_config,
                    name="read",
                    logger=semaphore_logger,
                )
            )
            self._write_semaphore: AsyncAdaptiveSemaphore | FixedSemaphoreAdapter = (
                AsyncAdaptiveSemaphore(
                    config=write_aimd_config,
                    name="write",
                    logger=semaphore_logger,
                )
            )
        else:
            self._read_semaphore = FixedSemaphoreAdapter(config.concurrency.read_limit)
            self._write_semaphore = FixedSemaphoreAdapter(
                config.concurrency.write_limit
            )

        # Platform HTTP client (created lazily with lock)
        self._platform_client: Autom8yHttpClient | None = None
        self._client_lock = asyncio.Lock()

        # Response handler
        self._response_handler = AsanaResponseHandler()

    def _create_rate_limiter(self) -> TokenBucketRateLimiter:
        """Create rate limiter from config."""
        rate_config = ConfigTranslator.to_rate_limiter_config(self._config)
        return TokenBucketRateLimiter(config=rate_config, logger=self._logger)

    def _create_circuit_breaker(self) -> CircuitBreaker:
        """Create circuit breaker from config."""
        cb_config = ConfigTranslator.to_circuit_breaker_config(self._config)
        return CircuitBreaker(config=cb_config, logger=self._logger)

    def _create_retry_policy(self) -> ExponentialBackoffRetry:
        """Create retry policy from config."""
        retry_config = ConfigTranslator.to_retry_config(self._config)
        return ExponentialBackoffRetry(config=retry_config, logger=self._logger)

    async def _get_client(self) -> Autom8yHttpClient:
        """Get or create platform HTTP client.

        Uses asyncio.Lock to prevent race conditions where multiple
        concurrent requests could create duplicate clients.

        Returns:
            Autom8yHttpClient instance with configured headers.
        """
        # Fast path: client already exists
        if self._platform_client is not None:
            return self._platform_client

        # Slow path: acquire lock and create client
        async with self._client_lock:
            # Double-check after acquiring lock
            if self._platform_client is not None:
                return self._platform_client

            # Get auth token
            token = self._auth_provider.get_secret(self._config.token_key)

            # Translate config
            http_config = ConfigTranslator.to_http_client_config(self._config)

            # Create platform client with injected policies
            # Note: We disable the platform's built-in policies and manage them ourselves
            # to ensure the rate limiter is shared across all requests
            self._platform_client = Autom8yHttpClient(
                config=http_config,
                rate_limiter=None,  # We manage rate limiting ourselves
                retry_policy=None,  # We manage retry ourselves
                circuit_breaker=None,  # We manage circuit breaker ourselves
                logger=self._logger,  # type: ignore[arg-type]
            )

            # Store the underlying httpx client for direct header configuration
            # The platform client's internal httpx client needs auth headers
            self._platform_client._client.headers.update(
                {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }
            )

        return self._platform_client

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """GET request with Asana response unwrapping.

        Args:
            path: API path (e.g., "/tasks/123").
            params: Query parameters.

        Returns:
            Unwrapped response data (without {"data": ...} envelope).

        Raises:
            CircuitBreakerOpenError: When circuit breaker is open.
            AsanaError: On API errors.
            TimeoutError: On request timeout.
        """
        return await self._request("GET", path, params=params)

    async def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST request with Asana response unwrapping.

        Args:
            path: API path.
            json: JSON body.
            params: Query parameters.

        Returns:
            Unwrapped response data.
        """
        return await self._request("POST", path, json=json, params=params)

    async def put(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """PUT request with Asana response unwrapping.

        Args:
            path: API path.
            json: JSON body.

        Returns:
            Unwrapped response data.
        """
        return await self._request("PUT", path, json=json)

    async def delete(self, path: str) -> dict[str, Any]:
        """DELETE request with Asana response unwrapping.

        Args:
            path: API path.

        Returns:
            Unwrapped response data.
        """
        return await self._request("DELETE", path)

    async def get_paginated(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """GET with pagination support.

        Args:
            path: API path.
            params: Query parameters (including offset for pagination).

        Returns:
            Tuple of (data list, next_offset or None).

        Raises:
            CircuitBreakerOpenError: When circuit breaker is open.
            AsanaError: On API errors.
            TimeoutError: On request timeout.
        """
        return await self._request_paginated("GET", path, params=params)

    @asynccontextmanager
    async def stream(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> AsyncIterator[Response]:
        """Stream response for large downloads.

        Uses raw() escape hatch from Autom8yHttpClient.
        Rate limiting applied once per stream initiation.

        Args:
            method: HTTP method.
            path: API path or full URL.
            **kwargs: Additional httpx request kwargs.

        Yields:
            httpx.Response for streaming.

        Example:
            >>> async with client.stream("GET", "/attachments/123/download") as response:
            ...     async for chunk in response.aiter_bytes():
            ...         process(chunk)
        """
        platform_client = await self._get_client()

        # Apply rate limiting once per stream
        await self._rate_limiter.acquire()

        async with platform_client.raw() as raw_client:
            async with raw_client.stream(method, path, **kwargs) as response:
                yield response

    async def post_multipart(
        self,
        path: str,
        *,
        files: dict[str, tuple[str, Any, str | None]],
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST with multipart/form-data for file uploads.

        Uses raw() escape hatch from Autom8yHttpClient for custom content type.

        Args:
            path: API path (e.g., "/tasks/{gid}/attachments").
            files: Dict of {field_name: (filename, file_obj, content_type)}.
            data: Additional form fields.

        Returns:
            Unwrapped response data.

        Raises:
            CircuitBreakerOpenError: When circuit breaker is open.
            AsanaError: On API errors.
            TimeoutError: On request timeout.
        """
        platform_client = await self._get_client()

        # Circuit breaker check
        if self._circuit_breaker:
            await self._circuit_breaker.check()

        # Use write semaphore for mutations
        semaphore = self._write_semaphore
        attempt = 0
        max_attempts = self._retry_policy.max_attempts if self._retry_policy else 1

        while True:
            async with await semaphore.acquire() as slot:
                # Rate limit
                await self._rate_limiter.acquire()

                try:
                    if self._logger:
                        self._logger.debug(f"POST {path} (multipart)")

                    # Use raw escape hatch for multipart
                    async with platform_client.raw() as raw_client:
                        # Remove default Content-Type so httpx auto-generates
                        # the correct multipart/form-data boundary header.
                        content_type_backup = raw_client.headers.get("content-type")
                        if content_type_backup:
                            del raw_client.headers["content-type"]
                        try:
                            response = await raw_client.post(
                                path,
                                files=files,
                                data=data,
                            )
                        finally:
                            if content_type_backup:
                                raw_client.headers["content-type"] = content_type_backup

                    # Check for errors and retry if needed
                    if response.status_code >= 400:
                        error = AsanaError.from_response(response)

                        # Handle rate limit
                        if isinstance(error, RateLimitError):
                            slot.reject()  # AIMD: signal 429
                            if self._should_retry(429, attempt, max_attempts):
                                await self._wait_for_retry(attempt, error.retry_after)
                                attempt += 1
                                continue

                        # Check if retryable
                        if self._should_retry(
                            response.status_code, attempt, max_attempts
                        ):
                            if isinstance(error, ServerError):
                                await self._circuit_breaker.record_failure(error)
                            await self._wait_for_retry(attempt)
                            attempt += 1
                            continue

                        # Not retryable
                        if isinstance(error, ServerError):
                            await self._circuit_breaker.record_failure(error)
                        raise error

                    # Success - signal AIMD
                    slot.succeed()
                    await self._circuit_breaker.record_success()
                    return self._response_handler.unwrap_response(response)

                except TimeoutException as e:
                    # No AIMD signal -- timeout is not a rate limit
                    await self._circuit_breaker.record_failure(e)
                    if self._should_retry(504, attempt, max_attempts):
                        if self._logger:
                            self._logger.warning(f"Timeout on POST {path}")
                        await self._wait_for_retry(attempt)
                        attempt += 1
                        continue
                    raise TimeoutError(f"Request timed out: {path}") from e

                except HTTPError as e:
                    # No AIMD signal -- network error is not a rate limit
                    await self._circuit_breaker.record_failure(e)
                    raise AsanaError(f"HTTP error: {e}") from e

    async def get_stream_url(
        self,
        url: str,
    ) -> AsyncIterator[bytes]:
        """Stream response bytes from an external URL (e.g., download URL).

        Per ADR-0009: Used for streaming attachment downloads.

        Args:
            url: Full URL to download from.

        Yields:
            Chunks of bytes from the response body.
        """
        platform_client = await self._get_client()
        await self._rate_limiter.acquire()

        async with platform_client.raw() as raw_client:
            async with raw_client.stream("GET", url) as response:
                if response.status_code >= 400:
                    raise AsanaError(f"Failed to download: HTTP {response.status_code}")
                async for chunk in response.aiter_bytes():
                    yield chunk

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request to Asana API.

        This is the core request method that handles:
        - Circuit breaker check
        - Rate limiting
        - Retry with exponential backoff
        - Error parsing

        Preserves backward compatibility with AsyncHTTPClient.request().

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            path: API path (e.g., "/tasks/123").
            params: Query parameters.
            json: JSON body (for POST/PUT).
            data: Form data.

        Returns:
            Parsed JSON response as dict (unwrapped from {"data": ...}).

        Raises:
            CircuitBreakerOpenError: When circuit breaker is open.
            AsanaError: On API errors.
            TimeoutError: On request timeout.
        """
        return await self._request(method, path, params=params, json=json, data=data)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Internal request implementation with retry and error handling."""
        platform_client = await self._get_client()

        # Circuit breaker check
        if self._circuit_breaker:
            await self._circuit_breaker.check()

        # Select semaphore based on method
        semaphore = (
            self._read_semaphore if method.upper() == "GET" else self._write_semaphore
        )
        attempt = 0
        max_attempts = self._retry_policy.max_attempts if self._retry_policy else 1

        while True:
            async with await semaphore.acquire() as slot:
                # Rate limit
                await self._rate_limiter.acquire()

                try:
                    if self._logger:
                        self._logger.debug(f"{method} {path}")

                    # Access the underlying httpx client directly
                    # We manage policies ourselves, so we bypass Autom8yHttpClient's policy layer
                    response = await platform_client._client.request(
                        method,
                        path,
                        params=params,
                        json=json,
                        data=data,
                    )

                    # Check for errors
                    if response.status_code >= 400:
                        error = AsanaError.from_response(response)

                        # Handle rate limit with Retry-After
                        if isinstance(error, RateLimitError):
                            slot.reject()  # AIMD: signal 429
                            if self._logger:
                                self._logger.warning(
                                    "rate_limit_429_received",
                                    extra={
                                        "path": path,
                                        "attempt": attempt,
                                        "retry_after": error.retry_after,
                                    },
                                )
                            if self._should_retry(429, attempt, max_attempts):
                                await self._wait_for_retry(attempt, error.retry_after)
                                attempt += 1
                                continue

                        # Check if retryable
                        if self._should_retry(
                            response.status_code, attempt, max_attempts
                        ):
                            # Record 5xx as failure for circuit breaker before retry
                            if isinstance(error, ServerError):
                                await self._circuit_breaker.record_failure(error)
                            await self._wait_for_retry(attempt)
                            attempt += 1
                            continue

                        # Record 5xx as failure for circuit breaker before raising
                        if isinstance(error, ServerError):
                            await self._circuit_breaker.record_failure(error)
                        raise error

                    # Success - signal AIMD and return
                    slot.succeed()
                    await self._circuit_breaker.record_success()
                    return self._response_handler.unwrap_response(response)

                except TimeoutException as e:
                    # No AIMD signal -- timeout is not a rate limit
                    await self._circuit_breaker.record_failure(e)
                    if self._should_retry(504, attempt, max_attempts):
                        if self._logger:
                            self._logger.warning(f"Timeout on {method} {path}")
                        await self._wait_for_retry(attempt)
                        attempt += 1
                        continue
                    raise TimeoutError(f"Request timed out: {path}") from e

                except HTTPError as e:
                    # No AIMD signal -- network error is not a rate limit
                    await self._circuit_breaker.record_failure(e)
                    raise AsanaError(f"HTTP error: {e}") from e

    async def _request_paginated(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Internal paginated request implementation."""
        platform_client = await self._get_client()

        # Circuit breaker check
        if self._circuit_breaker:
            await self._circuit_breaker.check()

        semaphore = self._read_semaphore
        attempt = 0
        max_attempts = self._retry_policy.max_attempts if self._retry_policy else 1

        while True:
            async with await semaphore.acquire() as slot:
                # Rate limit
                await self._rate_limiter.acquire()

                try:
                    if self._logger:
                        self._logger.debug(f"{method} {path} (paginated)")

                    # Access the underlying httpx client directly
                    response = await platform_client._client.request(
                        method,
                        path,
                        params=params,
                    )

                    # Check for errors
                    if response.status_code >= 400:
                        error = AsanaError.from_response(response)

                        # Handle rate limit with Retry-After
                        if isinstance(error, RateLimitError):
                            slot.reject()  # AIMD: signal 429
                            if self._logger:
                                self._logger.warning(
                                    "rate_limit_429_received",
                                    extra={
                                        "path": path,
                                        "attempt": attempt,
                                        "retry_after": error.retry_after,
                                    },
                                )
                            if self._should_retry(429, attempt, max_attempts):
                                await self._wait_for_retry(attempt, error.retry_after)
                                attempt += 1
                                continue

                        # Check if retryable
                        if self._should_retry(
                            response.status_code, attempt, max_attempts
                        ):
                            if isinstance(error, ServerError):
                                await self._circuit_breaker.record_failure(error)
                            await self._wait_for_retry(attempt)
                            attempt += 1
                            continue

                        if isinstance(error, ServerError):
                            await self._circuit_breaker.record_failure(error)
                        raise error

                    # Success - signal AIMD
                    slot.succeed()
                    await self._circuit_breaker.record_success()
                    return self._response_handler.unwrap_paginated_response(response)

                except TimeoutException as e:
                    # No AIMD signal -- timeout is not a rate limit
                    await self._circuit_breaker.record_failure(e)
                    if self._should_retry(504, attempt, max_attempts):
                        if self._logger:
                            self._logger.warning(f"Timeout on {method} {path}")
                        await self._wait_for_retry(attempt)
                        attempt += 1
                        continue
                    raise TimeoutError(f"Request timed out: {path}") from e

                except HTTPError as e:
                    # No AIMD signal -- network error is not a rate limit
                    await self._circuit_breaker.record_failure(e)
                    raise AsanaError(f"HTTP error: {e}") from e

    def _should_retry(
        self,
        status_code: int,
        attempt: int,
        max_attempts: int,
    ) -> bool:
        """Check if request should be retried."""
        if attempt >= max_attempts - 1:  # -1 because max_attempts includes initial
            return False
        if self._retry_policy:
            return self._retry_policy.should_retry(status_code, attempt)
        return False

    async def _wait_for_retry(
        self,
        attempt: int,
        retry_after: int | None = None,
    ) -> None:
        """Wait before retry using retry policy."""
        if self._retry_policy:
            await self._retry_policy.wait(attempt, retry_after)

    async def close(self) -> None:
        """Close client and release resources."""
        if self._platform_client is not None:
            await self._platform_client.close()
            self._platform_client = None
