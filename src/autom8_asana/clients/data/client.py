"""Client for autom8_data insights API.

DataServiceClient with async context manager protocol, optional cache
fallback (ADR-INS-004), resilience, and full observability.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import date
from typing import TYPE_CHECKING, Any, cast

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
    RetryConfig as SdkRetryConfig,
)
from autom8y_log import get_logger

from autom8_asana.clients.data import _cache as _cache_mod
from autom8_asana.clients.data import _metrics as _metrics_mod
from autom8_asana.clients.data import _normalize as _normalize_mod
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


# --- PII Redaction (Story 1.9, XR-003) ---
# Primitives live in _pii.py to avoid circular imports with submodules.
# Re-exported here for backward compatibility.

# --- Metrics Hook Type (Story 1.9) ---
# Re-exported from _metrics module for backward compatibility.
from autom8_asana.clients.data._metrics import MetricsHook  # noqa: E402
from autom8_asana.clients.data._pii import (  # noqa: E402
    mask_phone_number,
)
from autom8_asana.clients.data._pii import (  # noqa: E402
    mask_pii_in_string as _mask_pii_in_string,
)


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

        Constructor with optional cache fallback (ADR-INS-004) and metrics.

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
                Called with (name, value, tags) for each metric.
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

    # --- Sync Context Manager Protocol ---

    def __enter__(self) -> DataServiceClient:
        """Sync context manager entry.

        Returns self for use in sync with block.

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

        Retry with exponential backoff on transient failures.
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

        Feature is enabled by default. Retained as emergency kill switch
        (not for A/B testing).

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
        from autom8_asana.settings import get_settings

        if not get_settings().data_service.insights_enabled:
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

        Returns True if metrics_hook was provided.

        Returns:
            True if metrics_hook is configured.
        """
        return self._metrics_hook is not None

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Expose circuit breaker for monitoring.

        Allows monitoring of circuit breaker state
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
        "ad_questions": "question",
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

        Runs the async method in a thread pool from sync context (ADR-0002).

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
        return cast(
            InsightsResponse,
            self._run_sync(
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
            ),
        )

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
                        # Sanitize error string to redact any PII (XR-003)
                        sanitized_error = _mask_pii_in_string(str(chunk_result))
                        for pvp in pairs:
                            if pvp.canonical_key not in results:
                                results[pvp.canonical_key] = BatchInsightsResult(
                                    pvp=pvp,
                                    error=sanitized_error,
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

        Delegates to _endpoints.batch.execute_batch_request.
        """
        from autom8_asana.clients.data._endpoints import batch as _batch_ep

        return await _batch_ep.execute_batch_request(
            self, pvp_list, factory, period, refresh, request_id
        )

    @staticmethod
    def _build_entity_response(
        rows: list[dict[str, Any]],
        response_metadata: dict[str, Any],
        request_id: str,
        warnings: list[str],
    ) -> InsightsResponse:
        """Build an InsightsResponse for a single PVP from batch response data.

        Delegates to _endpoints.batch.build_entity_response.
        """
        from autom8_asana.clients.data._endpoints import batch as _batch_ep

        return _batch_ep.build_entity_response(
            rows, response_metadata, request_id, warnings
        )

    def _normalize_period(self, insights_period: str | None) -> str:
        """Normalize insights_period to autom8_data's period format.

        Delegates to _normalize.normalize_period.
        """
        return _normalize_mod.normalize_period(insights_period)

    async def _execute_insights_request(
        self,
        factory: str,
        request: InsightsRequest,
        request_id: str,
        cache_key: str,
    ) -> InsightsResponse:
        """Execute HTTP POST to insights factory endpoint with cache support.

        Delegates to _endpoints.insights.execute_insights_request.
        """
        from autom8_asana.clients.data._endpoints import insights as _insights_ep

        return await _insights_ep.execute_insights_request(
            self, factory, request, request_id, cache_key
        )

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
        from autom8_asana.clients.data._endpoints import export as _export_ep

        return await _export_ep.get_export_csv(
            self, office_phone, start_date=start_date, end_date=end_date
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
        from autom8_asana.clients.data._endpoints import simple as _simple_ep

        return await _simple_ep.get_appointments(
            self, office_phone, days=days, limit=limit
        )

    async def get_reconciliation_async(
        self,
        office_phone: str,
        vertical: str,
        *,
        period: str | None = None,
        window_days: int | None = None,
    ) -> InsightsResponse:
        """Fetch reconciliation data via POST /insights/reconciliation/execute.

        Per TDD-WS5 Part 2 Section 2.1: Uses the InsightExecutor endpoint,
        NOT the InsightsService/FrameTypeMapper path.

        Args:
            office_phone: E.164 formatted phone number.
            vertical: Business vertical.
            period: Time period preset. None = LIFETIME (all data).
            window_days: Window size in days for windowed output. None = flat.

        Returns:
            InsightsResponse with reconciliation data rows.

        Raises:
            InsightsServiceError: Upstream service failure.
            InsightsNotFoundError: No data found.
        """
        from autom8_asana.clients.data._endpoints import reconciliation as _recon_ep

        return await _recon_ep.get_reconciliation(
            self,
            office_phone,
            vertical,
            period=period,
            window_days=window_days,
        )

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
        from autom8_asana.clients.data._endpoints import simple as _simple_ep

        return await _simple_ep.get_leads(
            self,
            office_phone,
            days=days,
            exclude_appointments=exclude_appointments,
            limit=limit,
        )
