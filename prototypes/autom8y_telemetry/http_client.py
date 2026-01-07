"""Instrumented HTTP client with automatic OpenTelemetry spans.

This is prototype code - demonstrates HTTP instrumentation pattern.
Production version would live in autom8y_telemetry package.

SHORTCUTS TAKEN (see README.md):
- No retry/circuit breaker integration
- Hardcoded span attributes (no customization)
- Minimal error handling
- No timeout configuration
- Single test coverage only
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import httpx
from opentelemetry import trace

if TYPE_CHECKING:
    from .protocols import RateLimiterProtocol


class TelemetryHTTPClient:
    """HTTP client with automatic OpenTelemetry instrumentation.

    Wraps httpx.AsyncClient and automatically creates spans for each request,
    recording HTTP method, URL, status code, and duration.

    Integrates with rate limiting to demonstrate telemetry platform primitives.

    Example:
        >>> from autom8y_telemetry import init_telemetry, TelemetryHTTPClient
        >>> from autom8y_telemetry import TokenBucketRateLimiter
        >>>
        >>> init_telemetry("my-service")
        >>> rate_limiter = TokenBucketRateLimiter(max_tokens=10, refill_period=1.0)
        >>>
        >>> async with TelemetryHTTPClient(rate_limiter=rate_limiter) as client:
        ...     response = await client.get("https://api.example.com/data")
        ...     print(response.json())
    """

    def __init__(
        self,
        rate_limiter: RateLimiterProtocol | None = None,
        tracer: trace.Tracer | None = None,
        base_url: str = "",
    ) -> None:
        """Initialize instrumented HTTP client.

        Args:
            rate_limiter: Optional rate limiter for request throttling
            tracer: Optional tracer (uses global tracer if None)
            base_url: Base URL for all requests (default: "")
        """
        self._rate_limiter = rate_limiter
        self._tracer = tracer or trace.get_tracer(__name__)
        self._base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Get or create httpx client."""
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self._base_url)
        return self._client

    async def close(self) -> None:
        """Close HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> TelemetryHTTPClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def get(
        self,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """GET request with automatic instrumentation.

        Args:
            url: Request URL
            **kwargs: Additional httpx request parameters

        Returns:
            HTTP response

        Raises:
            httpx.HTTPError: On request failure
        """
        return await self.request("GET", url, **kwargs)

    async def post(
        self,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """POST request with automatic instrumentation.

        Args:
            url: Request URL
            **kwargs: Additional httpx request parameters

        Returns:
            HTTP response

        Raises:
            httpx.HTTPError: On request failure
        """
        return await self.request("POST", url, **kwargs)

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute HTTP request with automatic instrumentation.

        Creates a span for the request, records timing and status,
        and respects rate limiting if configured.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional httpx request parameters

        Returns:
            HTTP response

        Raises:
            httpx.HTTPError: On request failure
        """
        client = await self._ensure_client()

        # Rate limiting
        if self._rate_limiter:
            await self._rate_limiter.acquire()

        # Build full URL for span name
        full_url = url if url.startswith("http") else f"{self._base_url}{url}"

        # Create span for request
        with self._tracer.start_as_current_span(
            f"HTTP {method}",
            attributes={
                "http.method": method,
                "http.url": full_url,
            },
        ) as span:
            start_time = time.monotonic()

            try:
                response = await client.request(method, url, **kwargs)

                # Record response attributes
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("http.response_content_length", len(response.content))

                # Calculate duration
                duration_ms = (time.monotonic() - start_time) * 1000
                span.set_attribute("http.duration_ms", duration_ms)

                # Mark span status based on HTTP status
                if response.status_code >= 400:
                    span.set_status(
                        trace.Status(
                            trace.StatusCode.ERROR,
                            f"HTTP {response.status_code}",
                        )
                    )

                return response

            except Exception as e:
                # Record error in span
                span.set_status(
                    trace.Status(
                        trace.StatusCode.ERROR,
                        str(e),
                    )
                )
                span.record_exception(e)
                raise
