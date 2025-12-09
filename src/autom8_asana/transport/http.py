"""Async HTTP client for Asana API."""

from __future__ import annotations

import asyncio
import json as json_module
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncIterator

import httpx

from autom8_asana.exceptions import (
    AsanaError,
    RateLimitError,
    TimeoutError,
)
from autom8_asana.transport.rate_limiter import TokenBucketRateLimiter
from autom8_asana.transport.retry import RetryHandler

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig
    from autom8_asana.protocols.auth import AuthProvider
    from autom8_asana.protocols.log import LogProvider


class AsyncHTTPClient:
    """Async HTTP client with rate limiting, retry, and connection pooling.

    This is the core transport layer for all Asana API requests.
    Uses httpx for async HTTP operations.
    """

    def __init__(
        self,
        config: AsanaConfig,
        auth_provider: AuthProvider,
        logger: LogProvider | None = None,
    ) -> None:
        """Initialize HTTP client.

        Args:
            config: SDK configuration
            auth_provider: Authentication provider
            logger: Optional logger
        """
        self._config = config
        self._auth_provider = auth_provider
        self._logger = logger

        # Initialize rate limiter
        self._rate_limiter = TokenBucketRateLimiter(
            max_tokens=config.rate_limit.max_requests,
            refill_period=config.rate_limit.window_seconds,
            logger=logger,
        )

        # Initialize retry handler
        self._retry_handler = RetryHandler(config.retry, logger)

        # Concurrency semaphores
        self._read_semaphore = asyncio.Semaphore(config.concurrency.read_limit)
        self._write_semaphore = asyncio.Semaphore(config.concurrency.write_limit)

        # HTTP client (created lazily with lock to prevent race conditions)
        self._client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create httpx client.

        Uses asyncio.Lock to prevent race conditions where multiple
        concurrent requests could create duplicate clients.
        """
        # Fast path: client already exists
        if self._client is not None:
            return self._client

        # Slow path: acquire lock and create client
        async with self._client_lock:
            # Double-check after acquiring lock (another coroutine may have created it)
            if self._client is not None:
                return self._client

            # Get auth token
            token = self._auth_provider.get_secret(self._config.token_key)

            # Configure timeouts
            timeout = httpx.Timeout(
                connect=self._config.timeout.connect,
                read=self._config.timeout.read,
                write=self._config.timeout.write,
                pool=self._config.timeout.pool,
            )

            # Configure connection pool
            limits = httpx.Limits(
                max_connections=self._config.connection_pool.max_connections,
                max_keepalive_connections=self._config.connection_pool.max_keepalive_connections,
                keepalive_expiry=self._config.connection_pool.keepalive_expiry,
            )

            self._client = httpx.AsyncClient(
                base_url=self._config.base_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=timeout,
                limits=limits,
            )

        return self._client

    async def close(self) -> None:
        """Close HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

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

        Handles rate limiting, retry, and error parsing.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: API path (e.g., "/tasks/123")
            params: Query parameters
            json: JSON body (for POST/PUT)
            data: Form data

        Returns:
            Parsed JSON response as dict

        Raises:
            AsanaError: On API errors
            TimeoutError: On request timeout
        """
        client = await self._get_client()

        # Select semaphore based on method
        semaphore = (
            self._read_semaphore
            if method.upper() == "GET"
            else self._write_semaphore
        )

        attempt = 0

        while True:
            async with semaphore:
                # Rate limit
                await self._rate_limiter.acquire()

                try:
                    if self._logger:
                        self._logger.debug(f"{method} {path}")

                    response = await client.request(
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
                            if self._retry_handler.should_retry(429, attempt):
                                await self._retry_handler.wait(
                                    attempt, error.retry_after
                                )
                                attempt += 1
                                continue

                        # Check if retryable
                        if self._retry_handler.should_retry(
                            response.status_code, attempt
                        ):
                            await self._retry_handler.wait(attempt)
                            attempt += 1
                            continue

                        raise error

                    # Success - parse and return
                    try:
                        result = response.json()
                    except json_module.JSONDecodeError as e:
                        request_id = response.headers.get("X-Request-Id", "unknown")
                        body_snippet = response.text[:200] if response.text else "(empty)"
                        raise AsanaError(
                            f"Invalid JSON response from Asana API "
                            f"(HTTP {response.status_code}, request_id={request_id}): "
                            f"{e}. Body: {body_snippet}"
                        ) from e

                    # Asana wraps responses in {"data": ...}
                    if isinstance(result, dict) and "data" in result:
                        return result["data"]  # type: ignore[no-any-return]
                    return result  # type: ignore[no-any-return]

                except httpx.TimeoutException as e:
                    if self._retry_handler.should_retry(504, attempt):
                        if self._logger:
                            self._logger.warning(f"Timeout on {method} {path}")
                        await self._retry_handler.wait(attempt)
                        attempt += 1
                        continue
                    raise TimeoutError(f"Request timed out: {path}") from e

                except httpx.HTTPError as e:
                    raise AsanaError(f"HTTP error: {e}") from e

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """GET request."""
        return await self.request("GET", path, params=params)

    async def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST request."""
        return await self.request("POST", path, json=json, params=params)

    async def put(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """PUT request."""
        return await self.request("PUT", path, json=json)

    async def delete(self, path: str) -> dict[str, Any]:
        """DELETE request."""
        return await self.request("DELETE", path)

    async def get_paginated(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """GET request with pagination support.

        Returns the data list and the next page offset (if any).

        Args:
            path: API path
            params: Query parameters (including offset for pagination)

        Returns:
            Tuple of (data list, next_offset or None)
        """
        client = await self._get_client()

        # Select semaphore for read operation
        semaphore = self._read_semaphore
        attempt = 0

        while True:
            async with semaphore:
                # Rate limit
                await self._rate_limiter.acquire()

                try:
                    if self._logger:
                        self._logger.debug(f"GET {path} (paginated)")

                    response = await client.request(
                        "GET",
                        path,
                        params=params,
                    )

                    # Check for errors
                    if response.status_code >= 400:
                        error = AsanaError.from_response(response)

                        # Handle rate limit with Retry-After
                        if isinstance(error, RateLimitError):
                            if self._retry_handler.should_retry(429, attempt):
                                await self._retry_handler.wait(
                                    attempt, error.retry_after
                                )
                                attempt += 1
                                continue

                        # Check if retryable
                        if self._retry_handler.should_retry(
                            response.status_code, attempt
                        ):
                            await self._retry_handler.wait(attempt)
                            attempt += 1
                            continue

                        raise error

                    # Success - parse response
                    try:
                        result = response.json()
                    except json_module.JSONDecodeError as e:
                        request_id = response.headers.get("X-Request-Id", "unknown")
                        body_snippet = response.text[:200] if response.text else "(empty)"
                        raise AsanaError(
                            f"Invalid JSON response from Asana API "
                            f"(HTTP {response.status_code}, request_id={request_id}): "
                            f"{e}. Body: {body_snippet}"
                        ) from e

                    # Extract data and next_page offset
                    data: list[dict[str, Any]] = []
                    next_offset: str | None = None

                    if isinstance(result, dict):
                        data = result.get("data", [])
                        next_page = result.get("next_page")
                        if next_page and isinstance(next_page, dict):
                            next_offset = next_page.get("offset")

                    return data, next_offset

                except httpx.TimeoutException as e:
                    if self._retry_handler.should_retry(504, attempt):
                        if self._logger:
                            self._logger.warning(f"Timeout on GET {path}")
                        await self._retry_handler.wait(attempt)
                        attempt += 1
                        continue
                    raise TimeoutError(f"Request timed out: {path}") from e

                except httpx.HTTPError as e:
                    raise AsanaError(f"HTTP error: {e}") from e

    @asynccontextmanager
    async def stream(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> AsyncIterator[httpx.Response]:
        """Stream response for large downloads.

        Usage:
            async with client.stream("GET", "/attachments/123/download") as response:
                async for chunk in response.aiter_bytes():
                    ...
        """
        client = await self._get_client()
        await self._rate_limiter.acquire()

        async with client.stream(method, path, **kwargs) as response:
            yield response

    async def post_multipart(
        self,
        path: str,
        *,
        files: dict[str, tuple[str, Any, str | None]],
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST request with multipart/form-data encoding.

        Per ADR-0009: Used for file uploads to Asana API.

        Args:
            path: API path (e.g., "/tasks/{gid}/attachments")
            files: Dict of {field_name: (filename, file_obj, content_type)}
            data: Additional form fields

        Returns:
            Parsed JSON response as dict

        Raises:
            AsanaError: On API errors
            TimeoutError: On request timeout
        """
        client = await self._get_client()

        # Multipart uploads are write operations
        semaphore = self._write_semaphore
        attempt = 0

        while True:
            async with semaphore:
                # Rate limit
                await self._rate_limiter.acquire()

                try:
                    if self._logger:
                        self._logger.debug(f"POST {path} (multipart)")

                    # For multipart, we need to build the request differently
                    # httpx handles the Content-Type header automatically for multipart
                    url = path if path.startswith("http") else path
                    response = await client.post(
                        url,
                        files=files,
                        data=data,
                    )

                    # Check for errors
                    if response.status_code >= 400:
                        error = AsanaError.from_response(response)

                        # Handle rate limit with Retry-After
                        if isinstance(error, RateLimitError):
                            if self._retry_handler.should_retry(429, attempt):
                                await self._retry_handler.wait(
                                    attempt, error.retry_after
                                )
                                attempt += 1
                                continue

                        # Check if retryable
                        if self._retry_handler.should_retry(
                            response.status_code, attempt
                        ):
                            await self._retry_handler.wait(attempt)
                            attempt += 1
                            continue

                        raise error

                    # Success - parse and return
                    try:
                        result = response.json()
                    except json_module.JSONDecodeError as e:
                        request_id = response.headers.get("X-Request-Id", "unknown")
                        body_snippet = response.text[:200] if response.text else "(empty)"
                        raise AsanaError(
                            f"Invalid JSON response from Asana API "
                            f"(HTTP {response.status_code}, request_id={request_id}): "
                            f"{e}. Body: {body_snippet}"
                        ) from e

                    # Asana wraps responses in {"data": ...}
                    if isinstance(result, dict) and "data" in result:
                        return result["data"]  # type: ignore[no-any-return]
                    return result  # type: ignore[no-any-return]

                except httpx.TimeoutException as e:
                    if self._retry_handler.should_retry(504, attempt):
                        if self._logger:
                            self._logger.warning(f"Timeout on POST {path}")
                        await self._retry_handler.wait(attempt)
                        attempt += 1
                        continue
                    raise TimeoutError(f"Request timed out: {path}") from e

                except httpx.HTTPError as e:
                    raise AsanaError(f"HTTP error: {e}") from e

    async def get_stream_url(
        self,
        url: str,
    ) -> AsyncIterator[bytes]:
        """Stream response bytes from an external URL (e.g., download URL).

        Per ADR-0009: Used for streaming attachment downloads.

        Args:
            url: Full URL to download from

        Yields:
            Chunks of bytes from the response body
        """
        client = await self._get_client()
        await self._rate_limiter.acquire()

        async with client.stream("GET", url) as response:
            if response.status_code >= 400:
                raise AsanaError(f"Failed to download: HTTP {response.status_code}")
            async for chunk in response.aiter_bytes():
                yield chunk
