"""Client for autom8_data insights API.

Per TDD-INSIGHTS-001 Section 5.1: DataServiceClient implementation.
Per FR-001: DataServiceClient in autom8_asana.clients module.
Per FR-001.5: Implements async context manager protocol.
Per ADR-INS-004: Optional cache_provider for client-side cache fallback.
Per ADR-INS-005: Composed with existing transport infrastructure (Story 1.6).
Per Story 1.8: Cache integration for resilience and stale fallback.
Per Story 1.9: Full observability with structured logging, PII redaction, and metrics.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import date
from typing import TYPE_CHECKING, Any

import httpx

# Platform SDK resilience primitives (autom8y-http >= 0.3.0)
from autom8y_config.lambda_extension import resolve_secret_from_env
from autom8y_http import (
    CircuitBreaker,
    ExponentialBackoffRetry,
)
from autom8y_http import (
    CircuitBreakerConfig as SdkCircuitBreakerConfig,
)
from autom8y_http import (
    CircuitBreakerOpenError as SdkCircuitBreakerOpenError,
)
from autom8y_http import (
    RetryConfig as SdkRetryConfig,
)
from autom8y_log import get_logger

from autom8_asana.clients.data import _cache as _cache_mod
from autom8_asana.clients.data import _metrics as _metrics_mod
from autom8_asana.clients.data import _response as _response_mod
from autom8_asana.clients.data.config import DataServiceConfig
from autom8_asana.clients.data.models import (
    BatchInsightsResponse,
    BatchInsightsResult,
    ExportResult,
    InsightsRequest,
    InsightsResponse,
)
from autom8_asana.exceptions import (
    ExportError,
    InsightsError,
    InsightsServiceError,
    InsightsValidationError,
    SyncInAsyncContextError,
)
from autom8_asana.models.contracts import PhoneVerticalPair

if TYPE_CHECKING:
    from autom8_asana.cache.models.staleness_settings import StalenessCheckSettings
    from autom8_asana.protocols.auth import AuthProvider
    from autom8_asana.protocols.cache import CacheProvider
    from autom8_asana.protocols.log import LogProvider

logger = get_logger(__name__)

__all__ = ["DataServiceClient", "mask_phone_number"]


# --- PII Redaction (Story 1.9) ---

# Pattern matches E.164 phone numbers: +{country code}{digits}
_PHONE_PATTERN = re.compile(r"\+\d{10,15}")


def mask_phone_number(phone: str) -> str:
    """Mask middle digits of phone number for PII protection.

    Per Story 1.9: Redact phone numbers in logs.
    Pattern: +17705753103 -> +1770***3103 (keep first 4 + last 4 digits)

    Args:
        phone: E.164 formatted phone number (e.g., +17705753103).

    Returns:
        Masked phone number with middle digits replaced by asterisks.
        Returns original string if not a valid phone format.

    Example:
        >>> mask_phone_number("+17705753103")
        '+1770***3103'
        >>> mask_phone_number("+14155551234")
        '+1415***1234'
    """
    if not phone or len(phone) < 9:
        return phone

    # Keep first 5 chars (+1xxx) and last 4 chars (xxxx)
    # Mask everything in between with ***
    if phone.startswith("+") and len(phone) >= 9:
        prefix = phone[:5]
        suffix = phone[-4:]
        return f"{prefix}***{suffix}"

    return phone


def _mask_canonical_key(canonical_key: str) -> str:
    """Mask phone number in canonical key for PII protection.

    Args:
        canonical_key: PVP canonical key (e.g., pv1:+17705753103:chiropractic).

    Returns:
        Canonical key with phone number masked.

    Example:
        >>> _mask_canonical_key("pv1:+17705753103:chiropractic")
        'pv1:+1770***3103:chiropractic'
    """
    # Pattern: pv1:+phone:vertical
    parts = canonical_key.split(":")
    if len(parts) >= 3 and parts[0] == "pv1":
        parts[1] = mask_phone_number(parts[1])
        return ":".join(parts)
    return canonical_key


# --- Metrics Hook Type (Story 1.9) ---
# Re-exported from _metrics module for backward compatibility.
from autom8_asana.clients.data._metrics import MetricsHook  # noqa: E402


class DataServiceClient:
    """Client for autom8_data satellite service.

    Provides access to analytics insights via REST API with:
    - S2S JWT authentication (via AuthProvider or environment variable)
    - Connection pooling for efficient request handling
    - Configurable timeouts for analytics queries
    - Optional client-side caching for resilience (per ADR-INS-004)
    - Emergency kill switch via AUTOM8_DATA_INSIGHTS_ENABLED env var

    Per FR-001.5: Use as async context manager for proper resource cleanup.

    Example:
        >>> async with DataServiceClient() as client:
        ...     response = await client.get_insights_async(
        ...         office_phone="+17705753103",
        ...         vertical="chiropractic",
        ...         factory="account",
        ...         period="t30",
        ...     )
        ...     df = response.to_dataframe()

    Note:
        The insights integration is enabled by default and stable.
        The AUTOM8_DATA_INSIGHTS_ENABLED environment variable exists as an
        emergency kill switch only. Set to 'false' to disable without code
        deployment if service issues arise.
    """

    # Feature flag environment variable name
    FEATURE_FLAG_ENV_VAR = "AUTOM8_DATA_INSIGHTS_ENABLED"

    def __init__(
        self,
        config: DataServiceConfig | None = None,
        auth_provider: AuthProvider | None = None,
        logger: LogProvider | None = None,
        cache_provider: CacheProvider | None = None,
        staleness_settings: StalenessCheckSettings | None = None,
        metrics_hook: MetricsHook | None = None,
    ) -> None:
        """Initialize DataServiceClient.

        Per TDD-INSIGHTS-001 Section 5.1: Constructor parameters.
        Per ADR-INS-004: Optional cache_provider for client-side cache fallback.
        Per Story 1.9: Optional metrics_hook for observability.

        Args:
            config: Service configuration. Defaults to DataServiceConfig.from_env().
            auth_provider: Authentication provider for JWT tokens.
                If None, uses environment variable specified by config.token_key.
            logger: Optional logger for request/response logging.
            cache_provider: Optional cache provider for client-side cache fallback.
                Per ADR-INS-004: Enables returning stale data when autom8_data
                is unavailable.
            staleness_settings: Optional staleness check settings for cache
                TTL extension. Only used when cache_provider is provided.
            metrics_hook: Optional callback for emitting metrics.
                Per Story 1.9: Called with (name, value, tags) for each metric.
                Enables integration with Prometheus, DataDog, CloudWatch, etc.
        """
        self._config = config or DataServiceConfig.from_env()
        self._auth_provider = auth_provider
        self._log = logger
        self._cache = cache_provider
        self._staleness_settings = staleness_settings
        self._metrics_hook = metrics_hook

        # HTTP client (created lazily via _get_client)
        self._client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()

        # Circuit breaker for cascade failure prevention (Story 2.3)
        # Translate domain config to SDK config (autom8y-http >= 0.3.0)
        cb_config = self._config.circuit_breaker
        sdk_cb_config = SdkCircuitBreakerConfig(
            enabled=cb_config.enabled,
            failure_threshold=cb_config.failure_threshold,
            recovery_timeout=cb_config.recovery_timeout,
            half_open_max_calls=cb_config.half_open_max_calls,
        )
        self._circuit_breaker = CircuitBreaker(config=sdk_cb_config, logger=self._log)

        # Retry handler for transient failures (Story 2.2)
        # Translate domain config to SDK config (autom8y-http >= 0.3.0)
        retry_cfg = self._config.retry
        sdk_retry_config = SdkRetryConfig(
            max_retries=retry_cfg.max_retries,
            base_delay=retry_cfg.base_delay,
            max_delay=retry_cfg.max_delay,
            exponential_base=retry_cfg.exponential_base,
            jitter=retry_cfg.jitter,
            retryable_status_codes=retry_cfg.retryable_status_codes,
        )
        self._retry_handler = ExponentialBackoffRetry(
            config=sdk_retry_config, logger=self._log
        )

    # --- Async Context Manager Protocol (FR-001.5) ---

    async def __aenter__(self) -> DataServiceClient:
        """Async context manager entry.

        Per FR-001.5: Returns self for use in async with block.

        Returns:
            This client instance.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit - close client.

        Per FR-001.5: Ensures proper resource cleanup on exit.
        """
        await self.close()

    # --- Sync Context Manager Protocol (Story 2.6) ---

    def __enter__(self) -> DataServiceClient:
        """Sync context manager entry.

        Per Story 2.6: Returns self for use in sync with block.

        Returns:
            This client instance.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Sync context manager exit - closes client.

        Per ADR-0002: Fails fast if called from an async context,
        where resources cannot be properly cleaned up.

        Raises:
            SyncInAsyncContextError: If called from async context.
                Use `async with` instead.
        """
        self._run_sync(self.close(), method_name="__exit__", async_name="__aexit__")

    def _run_sync(
        self,
        coro: Any,
        *,
        method_name: str,
        async_name: str,
    ) -> Any:
        """Execute an async coroutine from a synchronous context.

        Checks for a running event loop and raises SyncInAsyncContextError
        if one exists (fail-fast per ADR-0002), otherwise executes the
        coroutine via asyncio.run().

        Args:
            coro: The coroutine to execute.
            method_name: Name of the sync method (for error messages).
            async_name: Name of the async alternative (for error messages).

        Returns:
            The result of the coroutine.

        Raises:
            SyncInAsyncContextError: If called from an async context.
        """
        running_loop: asyncio.AbstractEventLoop | None = None
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - safe to use asyncio.run()
            pass

        if running_loop is not None:
            raise SyncInAsyncContextError(
                method_name=method_name,
                async_method_name=async_name,
            )

        return asyncio.run(coro)

    # --- Retry Infrastructure ---

    async def _execute_with_retry(
        self,
        make_request: Callable[[], Awaitable[httpx.Response]],
        *,
        on_retry: Callable[[int, int, int | None], Awaitable[None]] | None = None,
        on_timeout_exhausted: Callable[[httpx.TimeoutException, int], Awaitable[None]],
        on_http_error: Callable[[httpx.HTTPError, int], Awaitable[None]],
    ) -> tuple[httpx.Response, int]:
        """Execute an HTTP request with retry on transient failures.

        Per Story 2.2: Retry with exponential backoff on transient failures.
        Handles retryable HTTP status codes, Retry-After header for 429,
        timeout retries, and circuit breaker failure recording.

        The common retry structure is encapsulated here. Caller-specific
        behavior (logging, metrics, stale fallback, error types) is provided
        via callbacks.

        Args:
            make_request: Async callable that performs the HTTP request and
                returns an httpx.Response. Called on each attempt.
            on_retry: Optional async callback invoked before each retry.
                Signature: (attempt, status_code_or_0, retry_after_or_None).
                Use for logging/metrics on retries. Pass None to skip.
            on_timeout_exhausted: Async callback when timeout retries are
                exhausted. Receives (error, attempt). MUST raise an exception.
            on_http_error: Async callback for non-retryable HTTP errors.
                Receives (error, attempt). MUST raise an exception.

        Returns:
            Tuple of (httpx.Response, attempt_count) on success or after
            retryable status codes are exhausted (caller handles >= 400
            responses). attempt_count is the number of retries performed
            (0 means first attempt succeeded).

        Raises:
            Whatever on_timeout_exhausted or on_http_error raise.
        """
        attempt = 0
        response: httpx.Response | None = None

        while True:
            try:
                response = await make_request()

                # Check for retryable HTTP status codes (Story 2.2)
                status = response.status_code
                if status in self._config.retry.retryable_status_codes:
                    if self._retry_handler.should_retry(status, attempt):
                        # Extract Retry-After header for 429 responses
                        retry_after: int | None = None
                        if status == 429:
                            retry_after_header = response.headers.get("Retry-After")
                            if retry_after_header:
                                try:
                                    retry_after = int(retry_after_header)
                                except ValueError:
                                    pass  # Ignore non-integer values

                        if on_retry is not None:
                            await on_retry(attempt, status, retry_after)

                        await self._retry_handler.wait(attempt, retry_after)
                        attempt += 1
                        continue  # Retry the request

                # Non-retryable status or success - exit retry loop
                break

            except httpx.TimeoutException as e:
                # Check if we can retry timeout errors (Story 2.2)
                if attempt < self._config.retry.max_retries:
                    if on_retry is not None:
                        await on_retry(attempt, 0, None)

                    await self._retry_handler.wait(attempt, None)
                    attempt += 1
                    continue  # Retry the request

                # Retries exhausted - delegate to caller's error handler
                await on_timeout_exhausted(e, attempt)

                # on_timeout_exhausted MUST raise; this is a safety fallback
                raise  # pragma: no cover

            except httpx.HTTPError as e:
                # Non-retryable HTTP error - delegate to caller's error handler
                await on_http_error(e, attempt)

                # on_http_error MUST raise; this is a safety fallback
                raise  # pragma: no cover

        return response, attempt

    # --- Resource Management ---

    async def close(self) -> None:
        """Close HTTP client and release resources.

        Per FR-001.5: Explicit close method for resource cleanup.
        Should be called when not using the context manager pattern.

        This method is idempotent - safe to call multiple times.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            if self._log:
                self._log.debug("DataServiceClient: HTTP client closed")

    # --- HTTP Client Management ---

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create httpx client with configured settings.

        Per TDD-INSIGHTS-001 Section 5.1: Creates httpx.AsyncClient with
        connection pooling, timeouts, and authentication headers.

        Uses double-checked locking for thread-safe lazy initialization.

        Returns:
            Configured httpx.AsyncClient instance.
        """
        if self._client is not None:
            return self._client

        async with self._client_lock:
            # Double-check after acquiring lock
            if self._client is not None:
                return self._client

            # Get auth token
            token = self._get_auth_token()

            # Configure timeouts from config
            timeout = httpx.Timeout(
                connect=self._config.timeout.connect,
                read=self._config.timeout.read,
                write=self._config.timeout.write,
                pool=self._config.timeout.pool,
            )

            # Configure connection pool from config
            limits = httpx.Limits(
                max_connections=self._config.connection_pool.max_connections,
                max_keepalive_connections=self._config.connection_pool.max_keepalive_connections,
                keepalive_expiry=self._config.connection_pool.keepalive_expiry,
            )

            # Build headers
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            if token:
                headers["Authorization"] = f"Bearer {token}"

            # Create client with configuration
            self._client = httpx.AsyncClient(
                base_url=self._config.base_url,
                headers=headers,
                timeout=timeout,
                limits=limits,
            )

            if self._log:
                self._log.debug(
                    f"DataServiceClient: HTTP client created "
                    f"(base_url={self._config.base_url})"
                )

            return self._client

    def _get_auth_token(self) -> str | None:
        """Get JWT token from auth provider or environment.

        Per TDD-INSIGHTS-001 Section 5.1: Retrieves authentication token
        using either the injected AuthProvider or falling back to
        environment variable.

        Returns:
            JWT token string, or None if not configured.
        """
        if self._auth_provider is not None:
            try:
                return self._auth_provider.get_secret(self._config.token_key)
            except (KeyError, AttributeError, TypeError) as e:
                if self._log:
                    self._log.warning(
                        f"DataServiceClient: Failed to get token from auth provider: {e}"
                    )
                # Fall through to environment variable

        # Fallback to environment variable (supports Lambda extension ARN resolution)
        try:
            return resolve_secret_from_env(self._config.token_key)
        except ValueError:
            return None

    def _check_feature_enabled(self) -> None:
        """Check if the insights integration is enabled (emergency kill switch).

        Per Story 1.7: Feature flag control for insights integration.
        Per Story 2.7: Feature is now enabled by default.
        Per Story 3.6: Retained as emergency kill switch (not for A/B testing).

        This check exists solely as an emergency disable mechanism, allowing
        the integration to be turned off without code deployment if service
        issues arise. Under normal operation, this flag should not be set.

        The feature is disabled when the env var is explicitly set to one of:
        - "false", "0", "no" (case-insensitive)

        Any other value or unset means enabled (default on).

        Raises:
            InsightsServiceError: If feature is disabled, with reason="feature_disabled"
                and a helpful message explaining how it was disabled.
        """
        env_value = os.environ.get(self.FEATURE_FLAG_ENV_VAR, "").lower()
        disabled_values = {"false", "0", "no"}

        if env_value in disabled_values:
            raise InsightsServiceError(
                f"Insights integration is disabled. "
                f"Remove {self.FEATURE_FLAG_ENV_VAR}=false or set to 'true' to enable.",
                reason="feature_disabled",
            )

    # --- Public API (Skeleton - to be implemented in Story 1.6) ---

    # Note: The following methods are placeholders for Story 1.6:
    # - get_insights_async(): Single factory request with circuit breaker/retry
    # - get_insights_batch_async(): Batch request support
    # See TDD-INSIGHTS-001 Section 5.1 for full API specification.

    # --- Properties ---

    @property
    def config(self) -> DataServiceConfig:
        """Get the client configuration.

        Returns:
            The DataServiceConfig used by this client.
        """
        return self._config

    @property
    def is_initialized(self) -> bool:
        """Check if the HTTP client has been initialized.

        Returns:
            True if _get_client() has been called and client is active.
        """
        return self._client is not None

    @property
    def has_cache(self) -> bool:
        """Check if client-side caching is enabled.

        Per ADR-INS-004: Returns True if cache_provider was provided.

        Returns:
            True if cache_provider is configured.
        """
        return self._cache is not None

    @property
    def has_metrics(self) -> bool:
        """Check if metrics emission is enabled.

        Per Story 1.9: Returns True if metrics_hook was provided.

        Returns:
            True if metrics_hook is configured.
        """
        return self._metrics_hook is not None

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Expose circuit breaker for monitoring.

        Per Story 2.3: Allows monitoring of circuit breaker state
        (CLOSED, OPEN, HALF_OPEN) and failure counts.

        Returns:
            The CircuitBreaker instance used by this client.

        Example:
            >>> async with DataServiceClient() as client:
            ...     print(f"Circuit state: {client.circuit_breaker.state}")
            ...     print(f"Failure count: {client.circuit_breaker.failure_count}")
        """
        return self._circuit_breaker

    # --- Metrics Emission (Story 1.9) ---
    # Delegated to clients/data/_metrics.py module-level function.

    def _emit_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str],
    ) -> None:
        """Emit a metric via the configured metrics hook.

        Delegates to _metrics.emit_metric with instance state.
        """
        _metrics_mod.emit_metric(self._metrics_hook, name, value, tags, self._log)

    # --- Cache Operations (Story 1.8) ---
    # Delegated to clients/data/_cache.py module-level functions.

    def _build_cache_key(self, factory: str, pvp: PhoneVerticalPair) -> str:
        """Build cache key for insights response.

        Delegates to _cache.build_cache_key.
        """
        return _cache_mod.build_cache_key(factory, pvp)

    def _cache_response(
        self,
        cache_key: str,
        response: InsightsResponse,
    ) -> None:
        """Cache successful insights response.

        Delegates to _cache.cache_response with instance state.
        """
        _cache_mod.cache_response(
            self._cache, cache_key, response, self._config.cache_ttl, self._log
        )

    def _get_stale_response(
        self,
        cache_key: str,
        request_id: str,
    ) -> InsightsResponse | None:
        """Retrieve stale response from cache for fallback.

        Delegates to _cache.get_stale_response with instance state.
        """
        return _cache_mod.get_stale_response(
            self._cache, cache_key, request_id, self._log
        )

    # --- Public API (Story 1.6) ---

    # Valid factory names (14 total per parent spike)
    # Each factory maps to a specific frame_type in autom8_data:
    #   account        -> AccountInsightsFrame (aggregated account metrics)
    #   ads            -> AdsInsightsFrame (individual ad performance)
    #   adsets         -> AdsetsInsightsFrame (ad set level metrics)
    #   campaigns      -> CampaignsInsightsFrame (campaign level metrics)
    #   spend          -> SpendInsightsFrame (spend breakdown)
    #   leads          -> LeadsInsightsFrame (lead generation metrics)
    #   appts          -> ApptsInsightsFrame (appointment metrics)
    #   assets         -> AssetsInsightsFrame (creative asset metrics)
    #   targeting      -> TargetingInsightsFrame (audience targeting metrics)
    #   payments       -> PaymentsInsightsFrame (payment/billing metrics)
    #   business_offers -> BusinessOffersInsightsFrame (offer metrics)
    #   ad_questions   -> AdQuestionsInsightsFrame (ad question responses)
    #   ad_tests       -> AdTestsInsightsFrame (A/B test results)
    #   base           -> BaseInsightsFrame (base/raw metrics)
    VALID_FACTORIES = frozenset(
        {
            "account",
            "ads",
            "adsets",
            "campaigns",
            "spend",
            "leads",
            "appts",
            "assets",
            "targeting",
            "payments",
            "business_offers",
            "ad_questions",
            "ad_tests",
            "base",
        }
    )

    # Factory to frame_type mapping for autom8_data API
    # Per docs/design/factory-to-frame-type-mapping.md
    # Maps autom8_asana factory names to autom8_data frame_type values
    FACTORY_TO_FRAME_TYPE: dict[str, str] = {
        "account": "business",
        "ads": "offer",
        "adsets": "offer",
        "campaigns": "offer",
        "spend": "offer",
        "leads": "offer",
        "appts": "offer",
        "assets": "asset",
        "targeting": "offer",
        "payments": "business",
        "business_offers": "offer",
        "ad_questions": "offer",
        "ad_tests": "offer",
        "base": "unit",
    }

    async def get_insights_async(
        self,
        factory: str,
        office_phone: str,
        vertical: str,
        *,
        period: str = "lifetime",
        start_date: date | None = None,
        end_date: date | None = None,
        metrics: list[str] | None = None,
        dimensions: list[str] | None = None,
        groups: list[str] | None = None,
        break_down: list[str] | None = None,
        refresh: bool = False,
        filters: dict[str, Any] | None = None,
    ) -> InsightsResponse:
        """Fetch analytics insights for a business.

        Per TDD-INSIGHTS-001 FR-003: Primary async method for fetching insights.
        Supports all 14 factory types (account, ads, adsets, campaigns, etc.).

        Args:
            factory: InsightsFactory name (case-insensitive). See VALID_FACTORIES.
            office_phone: E.164 formatted phone number (e.g., +17705753103).
            vertical: Business vertical (e.g., chiropractic, dental).
            period: Time period preset (default: "lifetime").
                Valid: lifetime, t30, l7, etc. See InsightsRequest for full list.
            start_date: Custom start date (overrides period if provided).
            end_date: Custom end date (overrides period if provided).
            metrics: Override default metrics returned by factory.
            dimensions: Override default dimensions for grouping.
            groups: Additional grouping columns.
            break_down: Break down results by these columns.
            refresh: Force cache refresh on autom8_data server.
            filters: Additional factory-specific filters.

        Returns:
            InsightsResponse with data, metadata, and DataFrame conversion methods.

        Raises:
            InsightsValidationError: Invalid inputs (bad factory, phone format, etc.).
            InsightsNotFoundError: No data for the PhoneVerticalPair.
            InsightsServiceError: Upstream service failure (500, 502, 503, 504).

        Example:
            >>> async with DataServiceClient() as client:
            ...     response = await client.get_insights_async(
            ...         factory="account",
            ...         office_phone="+17705753103",
            ...         vertical="chiropractic",
            ...         period="t30",
            ...     )
            ...     df = response.to_dataframe()
            ...     print(f"Retrieved {response.metadata.row_count} rows")
        """
        # Check feature flag before any other logic (Story 1.7)
        self._check_feature_enabled()

        # Generate request ID for tracing
        request_id = str(uuid.uuid4())

        # Validate factory name (case-insensitive)
        factory_normalized = factory.lower()
        self._validate_factory(factory_normalized, request_id)

        # Construct and validate PhoneVerticalPair (validates E.164 format)
        try:
            pvp = PhoneVerticalPair(phone=office_phone, vertical=vertical)
        except ValueError as e:
            raise InsightsValidationError(
                str(e),
                field="office_phone",
                request_id=request_id,
            ) from e

        # Build request body
        request = InsightsRequest(
            office_phone=pvp.office_phone,
            vertical=pvp.vertical,
            insights_period=period,
            start_date=start_date,
            end_date=end_date,
            metrics=metrics,
            dimensions=dimensions,
            groups=groups,
            break_down=break_down,
            refresh=refresh,
            filters=filters or {},
        )

        # Build cache key for caching and stale fallback (Story 1.8)
        cache_key = self._build_cache_key(factory_normalized, pvp)

        # Execute HTTP request with normalized factory name and cache support
        return await self._execute_insights_request(
            factory_normalized, request, request_id, cache_key
        )

    def get_insights(
        self,
        factory: str,
        office_phone: str,
        vertical: str,
        *,
        period: str = "lifetime",
        start_date: date | None = None,
        end_date: date | None = None,
        metrics: list[str] | None = None,
        dimensions: list[str] | None = None,
        groups: list[str] | None = None,
        break_down: list[str] | None = None,
        refresh: bool = False,
        filters: dict[str, Any] | None = None,
    ) -> InsightsResponse:
        """Synchronous wrapper for get_insights_async.

        Per ADR-0002: Runs the async method in a thread pool from sync context.
        Per Story 2.6: Provides sync interface for non-async callers.

        This method has identical parameters and return type as get_insights_async.
        See get_insights_async for full documentation.

        Args:
            factory: InsightsFactory name (Sprint 1: "account" only).
            office_phone: E.164 formatted phone number (e.g., +17705753103).
            vertical: Business vertical (e.g., chiropractic, dental).
            period: Time period preset (default: "lifetime").
            start_date: Custom start date (overrides period if provided).
            end_date: Custom end date (overrides period if provided).
            metrics: Override default metrics returned by factory.
            dimensions: Override default dimensions for grouping.
            groups: Additional grouping columns.
            break_down: Break down results by these columns.
            refresh: Force cache refresh on autom8_data server.
            filters: Additional factory-specific filters.

        Returns:
            InsightsResponse with data, metadata, and DataFrame conversion methods.

        Raises:
            SyncInAsyncContextError: If called from async context.
                Use get_insights_async instead.
            InsightsValidationError: Invalid inputs (bad factory, phone format, etc.).
            InsightsNotFoundError: No data for the PhoneVerticalPair.
            InsightsServiceError: Upstream service failure (500, 502, 503, 504).

        Example:
            >>> with DataServiceClient() as client:
            ...     response = client.get_insights(
            ...         factory="account",
            ...         office_phone="+17705753103",
            ...         vertical="chiropractic",
            ...         period="t30",
            ...     )
            ...     df = response.to_dataframe()
        """
        result: InsightsResponse = self._run_sync(
            self.get_insights_async(
                factory=factory,
                office_phone=office_phone,
                vertical=vertical,
                period=period,
                start_date=start_date,
                end_date=end_date,
                metrics=metrics,
                dimensions=dimensions,
                groups=groups,
                break_down=break_down,
                refresh=refresh,
                filters=filters,
            ),
            method_name="get_insights",
            async_name="get_insights_async",
        )
        return result

    # Maximum PVPs per HTTP request (autom8_data's max_length limit)
    _AUTOM8_DATA_MAX_PVP_PER_REQUEST = 1000

    async def get_insights_batch_async(
        self,
        pairs: list[PhoneVerticalPair],
        *,
        factory: str = "account",
        period: str = "lifetime",
        refresh: bool = False,
        max_concurrency: int = 10,
    ) -> BatchInsightsResponse:
        """Fetch insights for multiple businesses in a single HTTP request.

        Per TDD-INSIGHTS-001 FR-006: Batch support with partial failure handling.
        Per IMP-20: Sends all PVPs in a single POST to autom8_data instead of
        N individual requests, reducing HTTP round-trips from N to 1 (or
        ceil(N/1000) for very large batches).

        autom8_data's POST /api/v1/data-service/insights accepts 1-1000 PVPs
        per request. For batches exceeding 1000, requests are chunked and
        executed concurrently with bounded concurrency.

        Args:
            pairs: List of PhoneVerticalPairs to query.
            factory: InsightsFactory name (default: "account").
                See VALID_FACTORIES for all valid factory names.
            period: Time period preset (default: "lifetime").
                Valid: lifetime, t30, l7, etc.
            refresh: Force cache refresh on autom8_data server.
            max_concurrency: Maximum concurrent chunk requests (default: 10).
                Only relevant when batch exceeds 1000 PVPs.

        Returns:
            BatchInsightsResponse with results keyed by canonical_key.
            Use to_dataframe() to combine all successful results.

        Raises:
            InsightsValidationError: If batch size exceeds max_batch_size,
                or factory name is invalid.
            InsightsServiceError: If feature flag is disabled.

        Example:
            >>> pairs = [
            ...     PhoneVerticalPair(office_phone="+17705753103", vertical="chiropractic"),
            ...     PhoneVerticalPair(office_phone="+14155551234", vertical="dental"),
            ... ]
            >>> async with DataServiceClient() as client:
            ...     batch = await client.get_insights_batch_async(pairs, factory="account")
            ...     print(f"Success: {batch.success_count}/{batch.total_count}")
            ...     df = batch.to_dataframe()  # Combined DataFrame with _pvp_key column
        """
        # Check feature flag before any other logic (Story 1.7)
        self._check_feature_enabled()

        # Generate batch request ID for tracing
        request_id = str(uuid.uuid4())

        # Validate batch size
        if len(pairs) > self._config.max_batch_size:
            raise InsightsValidationError(
                f"Batch size {len(pairs)} exceeds maximum {self._config.max_batch_size}",
                field="pairs",
                request_id=request_id,
            )

        # Validate factory name
        factory_normalized = factory.lower()
        self._validate_factory(factory_normalized, request_id)

        # Log batch request start (Story 1.9)
        if self._log:
            self._log.info(
                "insights_batch_started",
                extra={
                    "request_id": request_id,
                    "factory": factory_normalized,
                    "batch_size": len(pairs),
                    "max_concurrency": max_concurrency,
                },
            )

        results: dict[str, BatchInsightsResult] = {}

        # Handle empty batch gracefully
        if not pairs:
            pass  # results stays empty, counts computed below
        else:
            # Chunk PVPs into groups of 1000 (autom8_data's max_length)
            chunk_size = self._AUTOM8_DATA_MAX_PVP_PER_REQUEST
            chunks = [
                pairs[i : i + chunk_size] for i in range(0, len(pairs), chunk_size)
            ]

            if len(chunks) == 1:
                # Single chunk: direct execution (common case)
                chunk_results = await self._execute_batch_request(
                    chunks[0],
                    factory_normalized,
                    period,
                    refresh,
                    request_id,
                )
                results.update(chunk_results)
            else:
                # Multiple chunks: parallel execution with bounded concurrency
                from autom8_asana.core.concurrency import gather_with_semaphore

                async def execute_chunk(
                    chunk: list[PhoneVerticalPair],
                ) -> dict[str, BatchInsightsResult]:
                    return await self._execute_batch_request(
                        chunk,
                        factory_normalized,
                        period,
                        refresh,
                        request_id,
                    )

                chunk_results_list = await gather_with_semaphore(
                    (execute_chunk(chunk) for chunk in chunks),
                    concurrency=max_concurrency,
                    label="batch_insights_chunks",
                )
                for chunk_result in chunk_results_list:
                    if isinstance(chunk_result, BaseException):
                        # If an entire chunk failed, mark all PVPs in that
                        # chunk as errored. Find unprocessed PVPs.
                        for pvp in pairs:
                            if pvp.canonical_key not in results:
                                results[pvp.canonical_key] = BatchInsightsResult(
                                    pvp=pvp,
                                    error=str(chunk_result),
                                )
                    else:
                        results.update(chunk_result)

        # Calculate success/failure counts
        success_count = sum(1 for r in results.values() if r.success)
        failure_count = len(pairs) - success_count

        # Log batch completion (Story 1.9)
        if self._log:
            self._log.info(
                "insights_batch_completed",
                extra={
                    "request_id": request_id,
                    "total_count": len(pairs),
                    "success_count": success_count,
                    "failure_count": failure_count,
                },
            )

        # Emit batch metrics (Story 1.9)
        self._emit_metric(
            "insights_batch_total",
            1,
            {"factory": factory_normalized},
        )
        self._emit_metric(
            "insights_batch_size",
            float(len(pairs)),
            {"factory": factory_normalized},
        )
        self._emit_metric(
            "insights_batch_success_count",
            float(success_count),
            {"factory": factory_normalized},
        )
        if failure_count > 0:
            self._emit_metric(
                "insights_batch_failure_count",
                float(failure_count),
                {"factory": factory_normalized},
            )

        return BatchInsightsResponse(
            results=results,
            request_id=request_id,
            total_count=len(pairs),
            success_count=success_count,
            failure_count=failure_count,
        )

    async def _execute_batch_request(
        self,
        pvp_list: list[PhoneVerticalPair],
        factory: str,
        period: str,
        refresh: bool,
        request_id: str,
    ) -> dict[str, BatchInsightsResult]:
        """Execute a single batched HTTP POST with multiple PVPs.

        Per IMP-20: Sends all PVPs in one HTTP request to autom8_data's
        POST /api/v1/data-service/insights endpoint.

        autom8_data returns:
        - HTTP 200: All PVPs succeeded. Response body has ``data`` list
          with per-entity results containing ``office_phone`` and ``vertical``.
        - HTTP 207: Partial success. Response body has both ``data`` (successes)
          and ``errors`` (per-PVP error details).
        - HTTP 4xx/5xx: Total failure for the entire chunk.

        Args:
            pvp_list: PVPs to include in this request (max 1000).
            factory: Validated, normalized factory name.
            period: Period preset (e.g., "lifetime").
            refresh: Whether to force cache refresh.
            request_id: Batch request correlation ID.

        Returns:
            Dict mapping canonical_key to BatchInsightsResult for each PVP.
        """
        # Build PVP lookup: canonical_key -> PhoneVerticalPair
        pvp_by_key: dict[str, PhoneVerticalPair] = {
            pvp.canonical_key: pvp for pvp in pvp_list
        }
        results: dict[str, BatchInsightsResult] = {}

        # --- Circuit Breaker Check (Story 2.3) ---
        try:
            await self._circuit_breaker.check()
        except SdkCircuitBreakerOpenError as e:
            # Mark all PVPs as failed due to circuit breaker
            error_msg = (
                f"Circuit breaker open. Service appears degraded. "
                f"Retry in {e.time_remaining:.1f}s."
            )
            for pvp in pvp_list:
                results[pvp.canonical_key] = BatchInsightsResult(
                    pvp=pvp,
                    error=error_msg,
                )
            return results

        client = await self._get_client()
        path = "/api/v1/data-service/insights"

        # Map factory to frame_type
        frame_type = self.FACTORY_TO_FRAME_TYPE[factory]

        # Normalize period to autom8_data format
        normalized_period = self._normalize_period(period)

        # Build request body with all PVPs (IMP-20: multi-PVP batch)
        request_body: dict[str, Any] = {
            "frame_type": frame_type,
            "phone_vertical_pairs": [
                {"phone": pvp.office_phone, "vertical": pvp.vertical}
                for pvp in pvp_list
            ],
            "period": normalized_period,
        }

        if refresh:
            request_body["refresh"] = refresh

        # Start timing for latency metrics (Story 1.9)
        start_time = time.monotonic()

        # --- Retry Callbacks ---

        async def _on_retry(
            attempt: int, status_code: int, retry_after: int | None
        ) -> None:
            if self._log:
                extra: dict[str, Any] = {
                    "request_id": request_id,
                    "attempt": attempt + 1,
                    "max_retries": self._config.retry.max_retries,
                    "batch_size": len(pvp_list),
                }
                if status_code:
                    extra["status_code"] = status_code
                    extra["retry_after"] = retry_after
                else:
                    extra["error_type"] = "TimeoutException"
                    extra["reason"] = "timeout"
                self._log.warning("insights_batch_request_retry", extra=extra)

        async def _on_timeout_exhausted(
            e: httpx.TimeoutException, attempt: int
        ) -> None:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            if self._log:
                self._log.error(
                    "insights_batch_request_failed",
                    extra={
                        "request_id": request_id,
                        "error_type": "TimeoutException",
                        "reason": "timeout",
                        "duration_ms": elapsed_ms,
                        "attempt": attempt + 1,
                        "batch_size": len(pvp_list),
                    },
                )
            await self._circuit_breaker.record_failure(e)
            raise InsightsServiceError(
                "Batch request to autom8_data timed out",
                request_id=request_id,
                reason="timeout",
            ) from e

        async def _on_http_error(e: httpx.HTTPError, attempt: int) -> None:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            if self._log:
                self._log.error(
                    "insights_batch_request_failed",
                    extra={
                        "request_id": request_id,
                        "error_type": e.__class__.__name__,
                        "reason": "http_error",
                        "duration_ms": elapsed_ms,
                        "attempt": attempt + 1,
                        "batch_size": len(pvp_list),
                    },
                )
            await self._circuit_breaker.record_failure(e)
            raise InsightsServiceError(
                f"HTTP error communicating with autom8_data: {e}",
                request_id=request_id,
                reason="http_error",
            ) from e

        # --- Execute HTTP request with retry ---
        # Note: W3C traceparent is auto-injected by HTTPXClientInstrumentor.
        # X-Request-Id is kept for backwards compatibility with autom8y-data's
        # RequestIDMiddleware, which uses it for non-OTEL correlation.
        try:
            response, _attempt = await self._execute_with_retry(
                lambda: client.post(
                    path,
                    json=request_body,
                    headers={"X-Request-Id": request_id},
                ),
                on_retry=_on_retry,
                on_timeout_exhausted=_on_timeout_exhausted,
                on_http_error=_on_http_error,
            )
        except (InsightsServiceError, InsightsError) as e:
            # Total failure for entire chunk -- mark all PVPs as errored
            for pvp in pvp_list:
                results[pvp.canonical_key] = BatchInsightsResult(
                    pvp=pvp,
                    error=str(e),
                )
            return results

        elapsed_ms = (time.monotonic() - start_time) * 1000

        # --- Handle total failure (4xx/5xx with no partial data) ---
        if response.status_code >= 400 and response.status_code != 207:
            error_msg = f"autom8_data API error (HTTP {response.status_code})"
            try:
                body = response.json()
                if "error" in body:
                    error_msg = body["error"]
                elif "detail" in body:
                    error_msg = body["detail"]
            except (ValueError, KeyError):
                pass

            if response.status_code >= 500:
                error = InsightsServiceError(
                    error_msg,
                    request_id=request_id,
                    status_code=response.status_code,
                    reason="server_error",
                )
                await self._circuit_breaker.record_failure(error)

            for pvp in pvp_list:
                results[pvp.canonical_key] = BatchInsightsResult(
                    pvp=pvp,
                    error=error_msg,
                )
            return results

        # --- Parse successful / partial response ---
        await self._circuit_breaker.record_success()

        try:
            body = response.json()
        except (ValueError, Exception) as e:
            error_msg = f"Failed to parse response JSON: {e}"
            for pvp in pvp_list:
                results[pvp.canonical_key] = BatchInsightsResult(
                    pvp=pvp,
                    error=error_msg,
                )
            return results

        # Parse successful entity data from response
        data_list: list[dict[str, Any]] = body.get("data", [])
        response_metadata = body.get("metadata", {})
        warnings = body.get("warnings", [])

        # Group data rows by canonical key (supports multiple rows per PVP)
        # Each row in data has office_phone and vertical fields
        rows_by_key: dict[str, list[dict[str, Any]]] = {}
        for row in data_list:
            row_phone = row.get("office_phone", "")
            row_vertical = row.get("vertical", "")
            canonical_key = f"pv1:{row_phone}:{row_vertical.lower()}"

            if canonical_key not in pvp_by_key:
                # Response contained a PVP we didn't request -- skip
                continue

            rows_by_key.setdefault(canonical_key, []).append(row)

        # Build per-PVP InsightsResponse from grouped rows
        for canonical_key, rows in rows_by_key.items():
            pvp = pvp_by_key[canonical_key]
            entity_response = self._build_entity_response(
                rows, response_metadata, request_id, warnings
            )
            results[canonical_key] = BatchInsightsResult(
                pvp=pvp,
                response=entity_response,
            )

        # Parse per-entity errors from response (HTTP 207 partial failures)
        errors_list: list[dict[str, Any]] = body.get("errors", [])
        for error_entry in errors_list:
            error_phone = error_entry.get("office_phone", "")
            error_vertical = error_entry.get("vertical", "")
            error_msg = error_entry.get("error", "Unknown error")
            canonical_key = f"pv1:{error_phone}:{error_vertical.lower()}"

            error_pvp = pvp_by_key.get(canonical_key)
            if error_pvp is not None and canonical_key not in results:
                results[canonical_key] = BatchInsightsResult(
                    pvp=error_pvp,
                    error=error_msg,
                )

        # Mark any remaining PVPs (not in data or errors) as failed
        for pvp in pvp_list:
            if pvp.canonical_key not in results:
                results[pvp.canonical_key] = BatchInsightsResult(
                    pvp=pvp,
                    error="No data returned for this PVP",
                )

        if self._log:
            self._log.info(
                "insights_batch_request_completed",
                extra={
                    "request_id": request_id,
                    "batch_size": len(pvp_list),
                    "data_count": len(data_list),
                    "error_count": len(errors_list),
                    "duration_ms": elapsed_ms,
                },
            )

        return results

    @staticmethod
    def _build_entity_response(
        rows: list[dict[str, Any]],
        response_metadata: dict[str, Any],
        request_id: str,
        warnings: list[str],
    ) -> InsightsResponse:
        """Build an InsightsResponse for a single PVP from batch response data.

        Groups all data rows belonging to one PVP into a single response.
        The metadata is shared across the batch but adapted per entity.

        Args:
            rows: List of data row dicts for this PVP.
            response_metadata: Shared metadata from the batch response.
            request_id: Request correlation ID.
            warnings: Shared warnings from the batch response.

        Returns:
            InsightsResponse for the single PVP.
        """
        from autom8_asana.clients.data.models import (
            ColumnInfo,
            InsightsMetadata,
        )

        columns = [ColumnInfo(**col) for col in response_metadata.get("columns", [])]

        metadata = InsightsMetadata(
            factory=response_metadata.get("factory", "unknown"),
            frame_type=response_metadata.get("frame_type"),
            insights_period=response_metadata.get("insights_period"),
            row_count=len(rows),
            column_count=len(columns) if columns else (len(rows[0]) if rows else 0),
            columns=columns,
            cache_hit=response_metadata.get("cache_hit", False),
            duration_ms=response_metadata.get("duration_ms", 0.0),
            sort_history=response_metadata.get("sort_history"),
            is_stale=response_metadata.get("is_stale", False),
            cached_at=response_metadata.get("cached_at"),
        )

        return InsightsResponse(
            data=rows,
            metadata=metadata,
            request_id=request_id,
            warnings=warnings,
        )

    def _normalize_period(self, insights_period: str | None) -> str:
        """Normalize insights_period to autom8_data's period format.

        Maps autom8_asana's period values to autom8_data's expected format:
        - "lifetime" -> "LIFETIME"
        - "t7", "l7" -> "T7"
        - "t14", "l14" -> "T14"
        - "t30", "l30" -> "T30"
        - "quarter" -> "QUARTER"
        - "month" -> "MONTH"
        - "week" -> "WEEK"

        Args:
            insights_period: Period value from InsightsRequest.

        Returns:
            Normalized period string for autom8_data API.

        Note:
            autom8_data supports T7, T14, T30, LIFETIME, QUARTER, MONTH, WEEK.
            Other period values default to T30 for backward compatibility.
        """
        if insights_period is None:
            return "LIFETIME"

        period_lower = insights_period.lower()

        # Handle lifetime case-insensitively
        if period_lower == "lifetime":
            return "LIFETIME"

        # Map trailing/last day periods to autom8_data format
        if period_lower in ("t7", "l7"):
            return "T7"
        elif period_lower in ("t14", "l14"):
            return "T14"
        elif period_lower in ("t30", "l30"):
            return "T30"
        elif period_lower == "quarter":
            return "QUARTER"
        elif period_lower == "month":
            return "MONTH"
        elif period_lower == "week":
            return "WEEK"

        # Default to T30 for other values (backward compatibility)
        return "T30"

    async def _execute_insights_request(
        self,
        factory: str,
        request: InsightsRequest,
        request_id: str,
        cache_key: str,
    ) -> InsightsResponse:
        """Execute HTTP POST to insights factory endpoint with cache support.

        Per TDD-INSIGHTS-001 Section 5.1: HTTP execution with error mapping.
        Per Story 1.8: Cache successful responses and fall back to stale cache
        on service errors.
        Per Story 1.9: Full observability with structured logging and metrics.
        Per Story 2.2: Retry with exponential backoff on transient failures.
        Per Story 2.3: Circuit breaker integration for cascade failure prevention.

        Cache Flow:
        1. Check circuit breaker (fast-fail if open)
        2. Try HTTP request to autom8_data with retry on transient failures
        3. On success: record success, store in cache, return fresh response
        4. On InsightsServiceError: record failure, try stale cache fallback
        5. If stale entry exists: return with is_stale=True
        6. If no stale entry: re-raise original error

        Retry Flow (Story 2.2):
        - Retries on status codes: 429, 502, 503, 504
        - Retries on timeout errors
        - Maximum 2 retries with exponential backoff (1s, 2s)
        - Respects Retry-After header for 429 responses
        - Does NOT retry 4xx client errors (except 429)

        Args:
            factory: Validated factory name.
            request: InsightsRequest with validated parameters.
            request_id: UUID for request tracing.
            cache_key: Pre-built cache key for storage and fallback.

        Returns:
            InsightsResponse parsed from successful response, or stale cache fallback.

        Raises:
            InsightsValidationError: 400-level errors (no cache fallback).
            InsightsNotFoundError: 404 errors (no cache fallback).
            InsightsServiceError: 500-level errors if no stale cache available,
                or circuit breaker is open (reason="circuit_breaker").
        """
        # --- Circuit Breaker Check (Story 2.3) ---
        # Fast-fail if circuit is open to prevent cascade failures
        try:
            await self._circuit_breaker.check()
        except SdkCircuitBreakerOpenError as e:
            # Convert SDK error to domain error (autom8y-http >= 0.3.0)
            raise InsightsServiceError(
                f"Circuit breaker open. Service appears degraded. "
                f"Retry in {e.time_remaining:.1f}s.",
                request_id=request_id,
                reason="circuit_breaker",
            ) from e

        client = await self._get_client()
        path = "/api/v1/data-service/insights"

        # Build PII-safe canonical key for logging (Story 1.9)
        pvp_canonical_key = f"pv1:{request.office_phone}:{request.vertical}"
        masked_pvp_key = _mask_canonical_key(pvp_canonical_key)

        # Map factory to frame_type
        frame_type = self.FACTORY_TO_FRAME_TYPE[factory]

        # Normalize period to autom8_data format
        period = self._normalize_period(request.insights_period)

        # Transform request body to autom8_data format
        request_body: dict[str, Any] = {
            "frame_type": frame_type,
            "phone_vertical_pairs": [
                {
                    "phone": request.office_phone,
                    "vertical": request.vertical,
                }
            ],
            "period": period,
        }

        # Add optional parameters if present
        if request.start_date is not None:
            request_body["start_date"] = request.start_date.isoformat()
        if request.end_date is not None:
            request_body["end_date"] = request.end_date.isoformat()
        if request.metrics is not None:
            request_body["metrics"] = request.metrics
        if request.dimensions is not None:
            request_body["dimensions"] = request.dimensions
        if request.groups is not None:
            request_body["groups"] = request.groups
        if request.break_down is not None:
            request_body["break_down"] = request.break_down
        if request.refresh:
            request_body["refresh"] = request.refresh
        if request.filters:
            request_body["filters"] = request.filters

        # Start timing for latency metrics (Story 1.9)
        start_time = time.monotonic()

        # --- Request Logging (Story 1.9) ---
        if self._log:
            self._log.info(
                "insights_request_started",
                extra={
                    "factory": factory,
                    "frame_type": frame_type,
                    "period": period,
                    "pvp_canonical_key": masked_pvp_key,
                    "request_id": request_id,
                },
            )

        # --- Retry Callbacks ---

        async def _on_retry(
            attempt: int, status_code: int, retry_after: int | None
        ) -> None:
            """Log retry attempts for insights requests."""
            if self._log:
                extra: dict[str, Any] = {
                    "request_id": request_id,
                    "attempt": attempt + 1,
                    "max_retries": self._config.retry.max_retries,
                }
                if status_code:
                    extra["status_code"] = status_code
                    extra["retry_after"] = retry_after
                else:
                    extra["error_type"] = "TimeoutException"
                    extra["reason"] = "timeout"
                self._log.warning("insights_request_retry", extra=extra)

        async def _on_timeout_exhausted(
            e: httpx.TimeoutException, attempt: int
        ) -> None:
            """Handle exhausted timeout retries for insights."""
            elapsed_ms = (time.monotonic() - start_time) * 1000

            # --- Error Logging (Story 1.9) ---
            if self._log:
                self._log.error(
                    "insights_request_failed",
                    extra={
                        "request_id": request_id,
                        "error_type": "TimeoutException",
                        "reason": "timeout",
                        "duration_ms": elapsed_ms,
                        "attempt": attempt + 1,
                    },
                )

            # --- Error Metrics (Story 1.9) ---
            self._emit_metric(
                "insights_request_error_total",
                1,
                {"factory": factory, "error_type": "timeout"},
            )
            self._emit_metric(
                "insights_request_latency_ms",
                elapsed_ms,
                {"factory": factory, "status": "error"},
            )

            # --- Circuit Breaker Record Failure (Story 2.3) ---
            await self._circuit_breaker.record_failure(e)

            raise InsightsServiceError(
                "Request to autom8_data timed out",
                request_id=request_id,
                reason="timeout",
            ) from e

        async def _on_http_error(e: httpx.HTTPError, attempt: int) -> None:
            """Handle non-retryable HTTP errors for insights."""
            elapsed_ms = (time.monotonic() - start_time) * 1000

            # --- Error Logging (Story 1.9) ---
            if self._log:
                self._log.error(
                    "insights_request_failed",
                    extra={
                        "request_id": request_id,
                        "error_type": e.__class__.__name__,
                        "reason": "http_error",
                        "duration_ms": elapsed_ms,
                        "attempt": attempt + 1,
                    },
                )

            # --- Error Metrics (Story 1.9) ---
            self._emit_metric(
                "insights_request_error_total",
                1,
                {"factory": factory, "error_type": "http_error"},
            )
            self._emit_metric(
                "insights_request_latency_ms",
                elapsed_ms,
                {"factory": factory, "status": "error"},
            )

            # --- Circuit Breaker Record Failure (Story 2.3) ---
            await self._circuit_breaker.record_failure(e)

            raise InsightsServiceError(
                f"HTTP error communicating with autom8_data: {e}",
                request_id=request_id,
                reason="http_error",
            ) from e

        # --- Retry Loop with Stale Fallback (Story 2.2, Story 1.8) ---
        # Note: W3C traceparent is auto-injected by HTTPXClientInstrumentor.
        # X-Request-Id is kept for backwards compatibility with autom8y-data's
        # RequestIDMiddleware, which uses it for non-OTEL correlation.
        try:
            response, attempt = await self._execute_with_retry(
                lambda: client.post(
                    path,
                    json=request_body,
                    headers={"X-Request-Id": request_id},
                ),
                on_retry=_on_retry,
                on_timeout_exhausted=_on_timeout_exhausted,
                on_http_error=_on_http_error,
            )
        except InsightsServiceError:
            # Try stale cache fallback on service errors (Story 1.8)
            stale_response = self._get_stale_response(cache_key, request_id)
            if stale_response is not None:
                return stale_response
            raise

        # Calculate elapsed time
        elapsed_ms = (time.monotonic() - start_time) * 1000

        # Handle error responses (if we got here after retries exhausted or non-retryable error)
        if response is not None and response.status_code >= 400:
            return await self._handle_error_response(
                response, request_id, cache_key, factory, elapsed_ms
            )

        # Parse successful response
        insights_response = self._parse_success_response(response, request_id)

        # --- Response Logging (Story 1.9) ---
        if self._log:
            self._log.info(
                "insights_request_completed",
                extra={
                    "request_id": request_id,
                    "row_count": insights_response.metadata.row_count,
                    "cache_hit": insights_response.metadata.cache_hit,
                    "is_stale": insights_response.metadata.is_stale,
                    "duration_ms": elapsed_ms,
                    "attempt": attempt + 1,
                },
            )

        # --- Success Metrics (Story 1.9) ---
        self._emit_metric(
            "insights_request_total",
            1,
            {"factory": factory, "status": "success"},
        )
        self._emit_metric(
            "insights_request_latency_ms",
            elapsed_ms,
            {"factory": factory, "status": "success"},
        )

        # --- Circuit Breaker Record Success (Story 2.3) ---
        await self._circuit_breaker.record_success()

        # Cache successful response (Story 1.8)
        self._cache_response(cache_key, insights_response)

        return insights_response

    # --- Response Parsing and Error Handling ---
    # Delegated to clients/data/_response.py module-level functions.

    def _validate_factory(self, factory: str, request_id: str) -> None:
        """Validate factory name against VALID_FACTORIES.

        Delegates to _response.validate_factory.
        """
        _response_mod.validate_factory(factory, request_id, self.VALID_FACTORIES)

    async def _handle_error_response(
        self,
        response: httpx.Response,
        request_id: str,
        cache_key: str,
        factory: str,
        elapsed_ms: float,
    ) -> InsightsResponse:
        """Map HTTP error response to appropriate exception.

        Delegates to _response.handle_error_response with instance callbacks.
        """
        return await _response_mod.handle_error_response(
            response,
            request_id,
            cache_key,
            factory,
            elapsed_ms,
            log=self._log,
            emit_metric=self._emit_metric,
            record_circuit_failure=self._circuit_breaker.record_failure,
            get_stale_response=self._get_stale_response,
        )

    def _parse_success_response(
        self,
        response: httpx.Response,
        request_id: str,
    ) -> InsightsResponse:
        """Parse successful HTTP response to InsightsResponse.

        Delegates to _response.parse_success_response.
        """
        return _response_mod.parse_success_response(response, request_id, self._log)

    # --- Export API (TDD-CONV-AUDIT-001 Section 3.5) ---

    async def get_export_csv_async(
        self,
        office_phone: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ExportResult:
        """Fetch conversation CSV export for a business phone number.

        Per TDD-CONV-AUDIT-001 Section 3.5: Calls GET /api/v1/messages/export
        on autom8_data. Returns raw CSV bytes with metadata from response headers.

        Uses the same connection pool, circuit breaker, retry handler, and
        authentication as get_insights_async.

        Args:
            office_phone: E.164 formatted phone number (e.g., "+17705753103").
            start_date: Filter start date. Default: 30 days ago (autom8_data default).
            end_date: Filter end date. Default: today (autom8_data default).

        Returns:
            ExportResult containing CSV bytes, row count, truncation flag,
            phone echo, and filename from Content-Disposition header.

        Raises:
            ExportError: On HTTP errors, circuit breaker open, or timeout.
        """
        # Check circuit breaker
        try:
            await self._circuit_breaker.check()
        except SdkCircuitBreakerOpenError as e:
            raise ExportError(
                f"Circuit breaker open for autom8_data. "
                f"Retry in {e.time_remaining:.1f}s.",
                office_phone=office_phone,
                reason="circuit_breaker",
            ) from e

        client = await self._get_client()
        path = "/api/v1/messages/export"

        # Build query parameters
        params: dict[str, str] = {"office_phone": office_phone}
        if start_date is not None:
            params["start_date"] = start_date.isoformat()
        if end_date is not None:
            params["end_date"] = end_date.isoformat()

        # PII-safe logging
        masked_phone = mask_phone_number(office_phone)

        if self._log:
            self._log.info(
                "export_request_started",
                extra={
                    "office_phone": masked_phone,
                    "path": path,
                },
            )

        start_time = time.monotonic()

        async def _on_export_timeout(e: httpx.TimeoutException, attempt: int) -> None:
            """Handle exhausted timeout retries for export."""
            await self._circuit_breaker.record_failure(e)
            raise ExportError(
                "Export request timed out",
                office_phone=office_phone,
                reason="timeout",
            ) from e

        async def _on_export_http_error(e: httpx.HTTPError, attempt: int) -> None:
            """Handle non-retryable HTTP errors for export."""
            await self._circuit_breaker.record_failure(e)
            raise ExportError(
                f"HTTP error during export: {e}",
                office_phone=office_phone,
                reason="http_error",
            ) from e

        response, _attempt = await self._execute_with_retry(
            lambda: client.get(
                path,
                params=params,
                headers={"Accept": "text/csv"},
            ),
            on_timeout_exhausted=_on_export_timeout,
            on_http_error=_on_export_http_error,
        )

        elapsed_ms = (time.monotonic() - start_time) * 1000

        # Handle error responses
        if response.status_code >= 400:
            if response.status_code >= 500:
                error = ExportError(
                    f"autom8_data export error (HTTP {response.status_code})",
                    office_phone=office_phone,
                    reason="server_error",
                )
                await self._circuit_breaker.record_failure(error)
                raise error
            raise ExportError(
                f"autom8_data export error (HTTP {response.status_code})",
                office_phone=office_phone,
                reason="client_error",
            )

        # Record success with circuit breaker
        await self._circuit_breaker.record_success()

        # Parse response headers
        row_count = int(response.headers.get("X-Export-Row-Count", "0"))
        truncated = (
            response.headers.get("X-Export-Truncated", "false").lower() == "true"
        )

        # Extract filename from Content-Disposition header
        content_disp = response.headers.get("Content-Disposition", "")
        filename = _parse_content_disposition_filename(content_disp)
        if not filename:
            # Fallback: generate filename
            phone_stripped = office_phone.lstrip("+")
            today_str = date.today().isoformat().replace("-", "")
            filename = f"conversations_{phone_stripped}_{today_str}.csv"

        if self._log:
            self._log.info(
                "export_request_completed",
                extra={
                    "office_phone": masked_phone,
                    "row_count": row_count,
                    "truncated": truncated,
                    "duration_ms": elapsed_ms,
                    "filename": filename,
                },
            )

        return ExportResult(
            csv_content=response.content,
            row_count=row_count,
            truncated=truncated,
            office_phone=office_phone,
            filename=filename,
        )

    # --- Appointments & Leads API (TDD-EXPORT-001 W04) ---

    async def get_appointments_async(
        self,
        office_phone: str,
        *,
        days: int = 90,
        limit: int = 100,
    ) -> InsightsResponse:
        """Fetch appointment detail rows for a business.

        Per TDD-EXPORT-001 W04: Maps to GET /appointments on autom8_data.
        Uses the same circuit breaker, retry handler, and auth as
        get_insights_async.

        Args:
            office_phone: E.164 formatted phone number.
            days: Lookback window in days (default: 90).
            limit: Maximum rows to return (default: 100).

        Returns:
            InsightsResponse with appointment detail rows.

        Raises:
            InsightsServiceError: Upstream service failure.
            InsightsNotFoundError: No data found.
        """
        self._check_feature_enabled()

        request_id = str(uuid.uuid4())
        masked_phone = mask_phone_number(office_phone)

        logger.info(
            "appointments_request_started",
            office_phone=masked_phone,
            days=days,
            limit=limit,
            request_id=request_id,
        )

        # Circuit breaker check
        try:
            await self._circuit_breaker.check()
        except SdkCircuitBreakerOpenError as e:
            raise InsightsServiceError(
                f"Circuit breaker open. Retry in {e.time_remaining:.1f}s.",
                request_id=request_id,
                reason="circuit_breaker",
            ) from e

        client = await self._get_client()
        path = "/api/v1/appointments"
        params = {
            "office_phone": office_phone,
            "days": str(days),
            "limit": str(limit),
        }

        start_time = time.monotonic()

        async def _on_timeout(e: httpx.TimeoutException, attempt: int) -> None:
            await self._circuit_breaker.record_failure(e)
            raise InsightsServiceError(
                "Appointments request timed out",
                request_id=request_id,
                reason="timeout",
            ) from e

        async def _on_http_error(e: httpx.HTTPError, attempt: int) -> None:
            await self._circuit_breaker.record_failure(e)
            raise InsightsServiceError(
                f"HTTP error during appointments fetch: {e}",
                request_id=request_id,
                reason="http_error",
            ) from e

        # Note: W3C traceparent is auto-injected by HTTPXClientInstrumentor.
        # X-Request-Id is kept for backwards compatibility.
        response, _attempt = await self._execute_with_retry(
            lambda: client.get(
                path,
                params=params,
                headers={"X-Request-Id": request_id},
            ),
            on_timeout_exhausted=_on_timeout,
            on_http_error=_on_http_error,
        )

        elapsed_ms = (time.monotonic() - start_time) * 1000

        if response.status_code >= 400:
            cache_key = f"appointments:{office_phone}"
            return await self._handle_error_response(
                response, request_id, cache_key, "appointments", elapsed_ms
            )

        insights_response = self._parse_success_response(response, request_id)
        await self._circuit_breaker.record_success()

        logger.info(
            "appointments_request_completed",
            office_phone=masked_phone,
            row_count=insights_response.metadata.row_count,
            duration_ms=elapsed_ms,
            request_id=request_id,
        )

        return insights_response

    async def get_leads_async(
        self,
        office_phone: str,
        *,
        days: int = 30,
        exclude_appointments: bool = True,
        limit: int = 100,
    ) -> InsightsResponse:
        """Fetch lead detail rows for a business.

        Per TDD-EXPORT-001 W04: Maps to GET /leads on autom8_data.
        Uses the same circuit breaker, retry handler, and auth as
        get_insights_async.

        Args:
            office_phone: E.164 formatted phone number.
            days: Lookback window in days (default: 30).
            exclude_appointments: Exclude appointment leads (default: True).
            limit: Maximum rows to return (default: 100).

        Returns:
            InsightsResponse with lead detail rows.

        Raises:
            InsightsServiceError: Upstream service failure.
            InsightsNotFoundError: No data found.
        """
        self._check_feature_enabled()

        request_id = str(uuid.uuid4())
        masked_phone = mask_phone_number(office_phone)

        logger.info(
            "leads_request_started",
            office_phone=masked_phone,
            days=days,
            exclude_appointments=exclude_appointments,
            limit=limit,
            request_id=request_id,
        )

        # Circuit breaker check
        try:
            await self._circuit_breaker.check()
        except SdkCircuitBreakerOpenError as e:
            raise InsightsServiceError(
                f"Circuit breaker open. Retry in {e.time_remaining:.1f}s.",
                request_id=request_id,
                reason="circuit_breaker",
            ) from e

        client = await self._get_client()
        path = "/api/v1/leads"
        params: dict[str, str] = {
            "office_phone": office_phone,
            "days": str(days),
            "limit": str(limit),
        }
        if exclude_appointments:
            params["exclude_appointments"] = "true"

        start_time = time.monotonic()

        async def _on_timeout(e: httpx.TimeoutException, attempt: int) -> None:
            await self._circuit_breaker.record_failure(e)
            raise InsightsServiceError(
                "Leads request timed out",
                request_id=request_id,
                reason="timeout",
            ) from e

        async def _on_http_error(e: httpx.HTTPError, attempt: int) -> None:
            await self._circuit_breaker.record_failure(e)
            raise InsightsServiceError(
                f"HTTP error during leads fetch: {e}",
                request_id=request_id,
                reason="http_error",
            ) from e

        # Note: W3C traceparent is auto-injected by HTTPXClientInstrumentor.
        # X-Request-Id is kept for backwards compatibility.
        response, _attempt = await self._execute_with_retry(
            lambda: client.get(
                path,
                params=params,
                headers={"X-Request-Id": request_id},
            ),
            on_timeout_exhausted=_on_timeout,
            on_http_error=_on_http_error,
        )

        elapsed_ms = (time.monotonic() - start_time) * 1000

        if response.status_code >= 400:
            cache_key = f"leads:{office_phone}"
            return await self._handle_error_response(
                response, request_id, cache_key, "leads", elapsed_ms
            )

        insights_response = self._parse_success_response(response, request_id)
        await self._circuit_breaker.record_success()

        logger.info(
            "leads_request_completed",
            office_phone=masked_phone,
            row_count=insights_response.metadata.row_count,
            duration_ms=elapsed_ms,
            request_id=request_id,
        )

        return insights_response


def _parse_content_disposition_filename(header: str) -> str | None:
    """Extract filename from Content-Disposition header.

    Args:
        header: Content-Disposition header value.

    Returns:
        Filename string or None if not parseable.
    """
    # Pattern: attachment; filename="conversations_17705753103_20260210.csv"
    match = re.search(r'filename="?([^";\s]+)"?', header)
    return match.group(1) if match else None
