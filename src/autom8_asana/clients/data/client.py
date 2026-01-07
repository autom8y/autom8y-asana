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
from autom8y_log import get_logger
import os
import re
import time
import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

import httpx

from autom8_asana.clients.data.config import DataServiceConfig
from autom8_asana.clients.data.models import (
    BatchInsightsResponse,
    BatchInsightsResult,
    ColumnInfo,
    InsightsMetadata,
    InsightsRequest,
    InsightsResponse,
)
from autom8_asana.exceptions import (
    InsightsError,
    InsightsNotFoundError,
    InsightsServiceError,
    InsightsValidationError,
    SyncInAsyncContextError,
)
# Platform SDK resilience primitives (autom8y-http >= 0.3.0)
from autom8y_http import (
    CircuitBreaker,
    CircuitBreakerConfig as SdkCircuitBreakerConfig,
    CircuitBreakerOpenError as SdkCircuitBreakerOpenError,
    ExponentialBackoffRetry,
    RetryConfig as SdkRetryConfig,
)
from autom8_asana.models.contracts import PhoneVerticalPair

if TYPE_CHECKING:
    from autom8_asana.cache.staleness_settings import StalenessCheckSettings
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

# Type alias for metrics hook callback
# Signature: (name: str, value: float, tags: dict[str, str]) -> None
MetricsHook = Callable[[str, float, dict[str, str]], None]


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
        running_loop: asyncio.AbstractEventLoop | None = None
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - safe to use asyncio.run()
            pass

        if running_loop is not None:
            # If there's a running loop, we can't use asyncio.run()
            # Fail fast per ADR-0002 - don't silently leak resources
            raise SyncInAsyncContextError(
                method_name="__exit__",
                async_method_name="__aexit__",
            )

        asyncio.run(self.close())

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
            except Exception as e:
                if self._log:
                    self._log.warning(
                        f"DataServiceClient: Failed to get token from auth provider: {e}"
                    )
                # Fall through to environment variable

        # Fallback to environment variable
        return os.environ.get(self._config.token_key)

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

    def _emit_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str],
    ) -> None:
        """Emit a metric via the configured metrics hook.

        Per Story 1.9: Generic method for emitting metrics.
        Failures are logged but don't break requests (graceful degradation).

        Args:
            name: Metric name (e.g., "insights_request_total").
            value: Metric value (count=1 for counters, duration for histograms).
            tags: Metric tags/labels for dimensionality.

        Example:
            >>> self._emit_metric("insights_request_total", 1, {"factory": "account", "status": "success"})
            >>> self._emit_metric("insights_request_latency_ms", 125.5, {"factory": "account"})
        """
        if self._metrics_hook is None:
            return

        try:
            self._metrics_hook(name, value, tags)
        except Exception as e:
            # Graceful degradation: metrics failures don't break requests
            if self._log:
                self._log.warning(
                    f"DataServiceClient: Failed to emit metric {name}: {e}",
                    extra={"metric_name": name, "tags": tags},
                )

    # --- Cache Key Generation (Story 1.8) ---

    def _build_cache_key(self, factory: str, pvp: PhoneVerticalPair) -> str:
        """Build cache key for insights response.

        Per Story 1.8: Cache key format is insights:{factory}:{canonical_key}.

        Args:
            factory: Normalized factory name (e.g., "account").
            pvp: PhoneVerticalPair with canonical_key property.

        Returns:
            Cache key string (e.g., "insights:account:pv1:+17705753103:chiropractic").
        """
        return f"insights:{factory}:{pvp.canonical_key}"

    def _cache_response(
        self,
        cache_key: str,
        response: InsightsResponse,
    ) -> None:
        """Cache successful insights response.

        Per Story 1.8: Stores response in cache with configured TTL.
        Cache failures are logged but don't break requests (graceful degradation).

        Args:
            cache_key: Pre-built cache key.
            response: Successful InsightsResponse to cache.
        """
        if self._cache is None:
            return

        try:
            # Serialize response to dict for caching
            cached_data = {
                "data": response.data,
                "metadata": response.metadata.model_dump(mode="json"),
                "request_id": response.request_id,
                "warnings": response.warnings,
                "cached_at": datetime.now(timezone.utc).isoformat(),
            }

            # Use simple set method for cache storage
            self._cache.set(cache_key, cached_data, ttl=self._config.cache_ttl)

            if self._log:
                self._log.debug(
                    f"DataServiceClient: Cached response for {cache_key}",
                    extra={"cache_key": cache_key, "ttl": self._config.cache_ttl},
                )
        except Exception as e:
            # Graceful degradation: cache failures don't break requests
            if self._log:
                self._log.warning(
                    f"DataServiceClient: Failed to cache response: {e}",
                    extra={"cache_key": cache_key},
                )

    def _get_stale_response(
        self,
        cache_key: str,
        request_id: str,
    ) -> InsightsResponse | None:
        """Retrieve stale response from cache for fallback.

        Per Story 1.8: On service failure, returns stale cache entry
        with is_stale=True and cached_at populated.

        Args:
            cache_key: Pre-built cache key.
            request_id: Request ID for the response.

        Returns:
            InsightsResponse with is_stale=True if found, None otherwise.
        """
        if self._cache is None:
            return None

        try:
            cached_data = self._cache.get(cache_key)
            if cached_data is None:
                return None

            # Reconstruct InsightsResponse from cached data
            metadata_dict = cached_data.get("metadata", {})

            # Parse cached_at timestamp
            cached_at_str = cached_data.get("cached_at")
            cached_at = None
            if cached_at_str:
                try:
                    cached_at = datetime.fromisoformat(cached_at_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    cached_at = datetime.now(timezone.utc)

            # Rebuild column info
            columns = [
                ColumnInfo(**col) for col in metadata_dict.get("columns", [])
            ]

            # Create metadata with staleness indicators
            metadata = InsightsMetadata(
                factory=metadata_dict.get("factory", "unknown"),
                frame_type=metadata_dict.get("frame_type"),
                insights_period=metadata_dict.get("insights_period"),
                row_count=metadata_dict.get("row_count", 0),
                column_count=metadata_dict.get("column_count", 0),
                columns=columns,
                cache_hit=metadata_dict.get("cache_hit", False),
                duration_ms=metadata_dict.get("duration_ms", 0.0),
                sort_history=metadata_dict.get("sort_history"),
                is_stale=True,  # Mark as stale
                cached_at=cached_at,  # Populate cached_at
            )

            stale_response = InsightsResponse(
                data=cached_data.get("data", []),
                metadata=metadata,
                request_id=request_id,
                warnings=cached_data.get("warnings", []) + [
                    "Response served from stale cache due to service unavailability"
                ],
            )

            if self._log:
                self._log.info(
                    f"DataServiceClient: Returning stale cache fallback for {cache_key}",
                    extra={
                        "cache_key": cache_key,
                        "cached_at": cached_at_str,
                        "row_count": metadata.row_count,
                    },
                )

            return stale_response

        except Exception as e:
            # Graceful degradation: cache read failures return None
            if self._log:
                self._log.warning(
                    f"DataServiceClient: Failed to retrieve stale response: {e}",
                    extra={"cache_key": cache_key},
                )
            return None

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
    VALID_FACTORIES = frozenset({
        "account", "ads", "adsets", "campaigns", "spend",
        "leads", "appts", "assets", "targeting", "payments",
        "business_offers", "ad_questions", "ad_tests", "base",
    })


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
            pvp = PhoneVerticalPair(office_phone=office_phone, vertical=vertical)
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
        # Check for running event loop (fail-fast per ADR-0002)
        running_loop: asyncio.AbstractEventLoop | None = None
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - safe to use asyncio.run()
            pass

        if running_loop is not None:
            raise SyncInAsyncContextError(
                method_name="get_insights",
                async_method_name="get_insights_async",
            )

        # Run the async method synchronously
        return asyncio.run(
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
            )
        )

    async def get_insights_batch_async(
        self,
        pairs: list[PhoneVerticalPair],
        *,
        factory: str = "account",
        period: str = "lifetime",
        refresh: bool = False,
        max_concurrency: int = 10,
    ) -> BatchInsightsResponse:
        """Fetch insights for multiple businesses concurrently.

        Per TDD-INSIGHTS-001 FR-006: Batch support with partial failure handling.
        Per Story 2.4: Concurrent requests with semaphore for rate limiting.

        This method executes multiple insights requests in parallel, up to
        max_concurrency concurrent requests. Partial failures are captured
        in the response rather than raised as exceptions.

        Args:
            pairs: List of PhoneVerticalPairs to query.
            factory: InsightsFactory name (default: "account").
                See VALID_FACTORIES for all valid factory names.
            period: Time period preset (default: "lifetime").
                Valid: lifetime, t30, l7, etc.
            refresh: Force cache refresh on autom8_data server.
            max_concurrency: Maximum concurrent requests (default: 10).
                Higher values improve throughput but may hit rate limits.

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

        # Execute requests concurrently with semaphore
        semaphore = asyncio.Semaphore(max_concurrency)
        results: dict[str, BatchInsightsResult] = {}

        async def fetch_one(pvp: PhoneVerticalPair) -> None:
            """Fetch insights for a single PVP with semaphore."""
            async with semaphore:
                try:
                    response = await self.get_insights_async(
                        factory=factory_normalized,
                        office_phone=pvp.office_phone,
                        vertical=pvp.vertical,
                        period=period,
                        refresh=refresh,
                    )
                    results[pvp.canonical_key] = BatchInsightsResult(
                        pvp=pvp,
                        response=response,
                    )
                except InsightsError as e:
                    # Capture partial failures in response (per FR-006)
                    results[pvp.canonical_key] = BatchInsightsResult(
                        pvp=pvp,
                        error=str(e),
                    )

        # Execute all requests concurrently
        await asyncio.gather(*[fetch_one(pvp) for pvp in pairs])

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
        path = f"/api/v1/factory/{factory}"

        # Build PII-safe canonical key for logging (Story 1.9)
        pvp_canonical_key = f"pv1:{request.office_phone}:{request.vertical}"
        masked_pvp_key = _mask_canonical_key(pvp_canonical_key)

        # Start timing for latency metrics (Story 1.9)
        start_time = time.monotonic()

        # --- Request Logging (Story 1.9) ---
        if self._log:
            self._log.info(
                "insights_request_started",
                extra={
                    "factory": factory,
                    "period": request.insights_period,
                    "pvp_canonical_key": masked_pvp_key,
                    "request_id": request_id,
                },
            )

        # --- Retry Loop (Story 2.2) ---
        attempt = 0
        response: httpx.Response | None = None

        while True:
            try:
                # Use mode="json" to serialize dates as ISO strings
                response = await client.post(
                    path,
                    json=request.model_dump(mode="json", exclude_none=True),
                    headers={"X-Request-Id": request_id},
                )

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

                        if self._log:
                            self._log.warning(
                                "insights_request_retry",
                                extra={
                                    "request_id": request_id,
                                    "attempt": attempt + 1,
                                    "max_retries": self._config.retry.max_retries,
                                    "status_code": status,
                                    "retry_after": retry_after,
                                },
                            )

                        await self._retry_handler.wait(attempt, retry_after)
                        attempt += 1
                        continue  # Retry the request

                # Non-retryable status or success - exit retry loop
                break

            except httpx.TimeoutException as e:
                # Check if we can retry timeout errors (Story 2.2)
                if attempt < self._config.retry.max_retries:
                    if self._log:
                        self._log.warning(
                            "insights_request_retry",
                            extra={
                                "request_id": request_id,
                                "attempt": attempt + 1,
                                "max_retries": self._config.retry.max_retries,
                                "error_type": "TimeoutException",
                                "reason": "timeout",
                            },
                        )

                    await self._retry_handler.wait(attempt, None)
                    attempt += 1
                    continue  # Retry the request

                # Retries exhausted
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

                # Try stale cache fallback on timeout (Story 1.8)
                stale_response = self._get_stale_response(cache_key, request_id)
                if stale_response is not None:
                    return stale_response
                raise InsightsServiceError(
                    "Request to autom8_data timed out",
                    request_id=request_id,
                    reason="timeout",
                ) from e

            except httpx.HTTPError as e:
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

                # Try stale cache fallback on HTTP error (Story 1.8)
                stale_response = self._get_stale_response(cache_key, request_id)
                if stale_response is not None:
                    return stale_response
                raise InsightsServiceError(
                    f"HTTP error communicating with autom8_data: {e}",
                    request_id=request_id,
                    reason="http_error",
                ) from e

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

    def _validate_factory(self, factory: str, request_id: str) -> None:
        """Validate factory name against VALID_FACTORIES.

        Args:
            factory: Normalized (lowercase) factory name to validate.
            request_id: Request ID for error context.

        Raises:
            InsightsValidationError: If factory name is not in VALID_FACTORIES.
        """
        if factory not in self.VALID_FACTORIES:
            raise InsightsValidationError(
                f"Invalid factory: '{factory}'. "
                f"Valid factories: {', '.join(sorted(self.VALID_FACTORIES))}",
                field="factory",
                request_id=request_id,
            )

    async def _handle_error_response(
        self,
        response: httpx.Response,
        request_id: str,
        cache_key: str,
        factory: str,
        elapsed_ms: float,
    ) -> InsightsResponse:
        """Map HTTP error response to appropriate exception.

        Per TDD-INSIGHTS-001 Section 11.1: Error response mapping.
        Per Story 1.8: Try stale cache fallback for 5xx server errors.
        Per Story 1.9: Full observability with structured logging and metrics.
        Per Story 2.3: Circuit breaker failure recording for 5xx errors.

        Args:
            response: HTTP response with status >= 400.
            request_id: Request ID for error context.
            cache_key: Cache key for stale fallback on 5xx errors.
            factory: Factory name for metrics tags.
            elapsed_ms: Request duration in milliseconds.

        Returns:
            InsightsResponse from stale cache fallback (only for 5xx errors).

        Raises:
            InsightsValidationError: 400 errors (no cache fallback).
            InsightsNotFoundError: 404 errors (no cache fallback).
            InsightsServiceError: 500-level errors if no stale cache available.

        Note: For 4xx errors, this method always raises (no cache fallback).
        """
        status = response.status_code
        message = f"autom8_data API error (HTTP {status})"

        # Try to extract error message from response body
        try:
            body = response.json()
            if "error" in body:
                message = body["error"]
            elif "detail" in body:
                message = body["detail"]
        except Exception:
            # Use default message if body parsing fails
            pass

        # Determine error type for logging/metrics
        if status == 400:
            error_type = "validation_error"
            reason = "validation_error"
        elif status == 404:
            error_type = "not_found"
            reason = "not_found"
        elif status >= 500:
            error_type = "server_error"
            reason = "server_error"
        else:
            error_type = "client_error"
            reason = "client_error"

        # --- Error Logging (Story 1.9) ---
        if self._log:
            self._log.error(
                "insights_request_failed",
                extra={
                    "request_id": request_id,
                    "status_code": status,
                    "error_type": error_type,
                    "reason": reason,
                    "duration_ms": elapsed_ms,
                },
            )

        # --- Error Metrics (Story 1.9) ---
        self._emit_metric(
            "insights_request_error_total",
            1,
            {"factory": factory, "error_type": error_type, "status_code": str(status)},
        )
        self._emit_metric(
            "insights_request_total",
            1,
            {"factory": factory, "status": "error"},
        )
        self._emit_metric(
            "insights_request_latency_ms",
            elapsed_ms,
            {"factory": factory, "status": "error"},
        )

        # Map status code to exception type
        if status == 400:
            # No cache fallback for validation errors
            raise InsightsValidationError(
                message,
                request_id=request_id,
            )
        elif status == 404:
            # No cache fallback for not found errors
            raise InsightsNotFoundError(
                message,
                request_id=request_id,
            )
        else:
            # 500, 502, 503, 504 and any other 5xx - try stale cache fallback
            if status >= 500:
                # --- Circuit Breaker Record Failure (Story 2.3) ---
                # Create an exception to pass to the circuit breaker
                error = InsightsServiceError(
                    message,
                    request_id=request_id,
                    status_code=status,
                    reason=reason,
                )
                await self._circuit_breaker.record_failure(error)

                stale_response = self._get_stale_response(cache_key, request_id)
                if stale_response is not None:
                    return stale_response

                raise error

            raise InsightsServiceError(
                message,
                request_id=request_id,
                status_code=status,
                reason=reason,
            )

    def _parse_success_response(
        self,
        response: httpx.Response,
        request_id: str,
    ) -> InsightsResponse:
        """Parse successful HTTP response to InsightsResponse.

        Per TDD-INSIGHTS-001 Section 4.3: Response parsing.

        Args:
            response: HTTP response with status 2xx.
            request_id: Request ID for response correlation.

        Returns:
            InsightsResponse with data, metadata, and warnings.

        Raises:
            InsightsServiceError: If response body cannot be parsed.
        """
        try:
            body = response.json()
        except Exception as e:
            raise InsightsServiceError(
                f"Failed to parse response JSON: {e}",
                request_id=request_id,
                reason="parse_error",
            ) from e

        try:
            # Parse metadata
            metadata_dict = body.get("metadata", {})
            columns = [
                ColumnInfo(**col) for col in metadata_dict.get("columns", [])
            ]

            metadata = InsightsMetadata(
                factory=metadata_dict.get("factory", "unknown"),
                frame_type=metadata_dict.get("frame_type"),
                insights_period=metadata_dict.get("insights_period"),
                row_count=metadata_dict.get("row_count", 0),
                column_count=metadata_dict.get("column_count", 0),
                columns=columns,
                cache_hit=metadata_dict.get("cache_hit", False),
                duration_ms=metadata_dict.get("duration_ms", 0.0),
                sort_history=metadata_dict.get("sort_history"),
                is_stale=metadata_dict.get("is_stale", False),
                cached_at=metadata_dict.get("cached_at"),
            )

            insights_response = InsightsResponse(
                data=body.get("data", []),
                metadata=metadata,
                request_id=request_id,
                warnings=body.get("warnings", []),
            )

            if self._log:
                self._log.debug(
                    "DataServiceClient: Response parsed successfully",
                    extra={
                        "request_id": request_id,
                        "row_count": metadata.row_count,
                        "cache_hit": metadata.cache_hit,
                        "duration_ms": metadata.duration_ms,
                    },
                )

            return insights_response

        except Exception as e:
            raise InsightsServiceError(
                f"Failed to parse response structure: {e}",
                request_id=request_id,
                reason="parse_error",
            ) from e
