# TDD: autom8_asana Insights Integration with autom8_data

**TDD ID**: TDD-INSIGHTS-001
**Status**: Draft
**Author**: Architect (Claude Opus 4.5)
**Date**: 2025-12-30
**PRD Reference**: [PRD-INSIGHTS-001](../requirements/PRD-insights-integration.md)
**Parent Initiative**: autom8 Satellite Extraction (SPIKE-AUTOM8-DATA-PVP-MODERNIZATION)

---

## 1. Executive Summary

This Technical Design Document specifies the architecture for integrating autom8_asana with the autom8_data satellite service to consume analytics insights via REST API. The design introduces a new `DataServiceClient` class in the `autom8_asana.clients` module, with supporting models, exception hierarchy, and feature flag integration.

**Key Design Decisions**:
1. **PhoneVerticalPair** owned by autom8_asana (not shared package) - see ADR-INS-001
2. **JSON response with dtype metadata** (Arrow deferred to future) - see ADR-INS-002
3. **S2S JWT authentication** reusing existing AuthProvider protocol - see ADR-INS-003
4. **Server-side caching** delegated to autom8_data - see ADR-INS-004
5. **Circuit breaker composition** with existing transport layer - see ADR-INS-005

---

## 2. System Context

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           autom8_asana SDK                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐ │
│  │  Business Model │───▶│ DataServiceClient│───▶│  InsightsResponse       │ │
│  │  (office_phone, │    │                 │    │  (to_dataframe())       │ │
│  │   vertical)     │    │  get_insights_  │    └─────────────────────────┘ │
│  └─────────────────┘    │  async()        │                                │
│                         └────────┬────────┘                                │
│                                  │                                          │
│  ┌───────────────────────────────┼───────────────────────────────────────┐ │
│  │                     Transport Layer                                    │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │  │ AsyncHTTP   │  │   Retry     │  │  Circuit    │  │    Rate     │   │ │
│  │  │  Client     │  │  Handler    │  │  Breaker    │  │   Limiter   │   │ │
│  │  └──────┬──────┘  └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  └─────────┼─────────────────────────────────────────────────────────────┘ │
│            │                                                                │
└────────────┼────────────────────────────────────────────────────────────────┘
             │ HTTPS + JWT
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          autom8_data Satellite                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  POST /api/v1/factory/{factory_name}                                        │
│  - AccountInsights, AdsInsights, SpendInsights, ... (14 factories)         │
│  - JSON response with dtype metadata                                        │
│  - S3 caching (InsightExportsBucket)                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Boundaries

| Component | Responsibility | Package |
|-----------|---------------|---------|
| `DataServiceClient` | HTTP communication with autom8_data | `autom8_asana.clients.data` |
| `PhoneVerticalPair` | Business identifier model | `autom8_asana.models.contracts` |
| `InsightsResponse` | Typed response with DataFrame conversion | `autom8_asana.models.insights` |
| `InsightsError` hierarchy | Structured exception handling | `autom8_asana.exceptions` |
| `DataServiceConfig` | Configuration for autom8_data connection | `autom8_asana.config` |

---

## 3. Module Design

### 3.1 Package Structure

```
src/autom8_asana/
├── clients/
│   ├── __init__.py          # Export DataServiceClient
│   ├── base.py              # Existing BaseClient
│   ├── data/                # NEW: autom8_data client package
│   │   ├── __init__.py      # Export DataServiceClient, config
│   │   ├── client.py        # DataServiceClient implementation
│   │   ├── config.py        # DataServiceConfig
│   │   └── models.py        # InsightsRequest, InsightsResponse
│   └── ...existing clients
├── models/
│   ├── contracts/           # NEW: Cross-service contracts
│   │   ├── __init__.py
│   │   └── phone_vertical.py  # PhoneVerticalPair model
│   └── ...existing models
├── exceptions.py            # Add InsightsError hierarchy
└── transport/
    └── ...existing (reuse circuit_breaker, retry)
```

### 3.2 Class Hierarchy

```
                    BaseClient (existing)
                         │
                         │ composition (not inheritance)
                         ▼
             ┌───────────────────────┐
             │   DataServiceClient   │
             │  - _http: httpx       │
             │  - _config            │
             │  - _circuit_breaker   │
             │  - _retry_handler     │
             └───────────┬───────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
   get_insights_async()      get_insights_batch_async()
            │                         │
            ▼                         ▼
    InsightsResponse          BatchInsightsResponse
```

---

## 4. Data Models

### 4.1 PhoneVerticalPair

**Location**: `autom8_asana/models/contracts/phone_vertical.py`

```python
"""Cross-service identifier for business scoping.

Per ADR-INS-001: Owned by autom8_asana, not a shared package.
Per parent spike: Version-prefixed canonical_key (pv1:) for future migration.
"""

from __future__ import annotations

import re
from typing import Iterator

from pydantic import BaseModel, ConfigDict, field_validator


class PhoneVerticalPair(BaseModel):
    """Immutable identifier for a business by phone number and vertical.

    Attributes:
        office_phone: E.164 formatted phone number (e.g., +17705753103)
        vertical: Business vertical (e.g., chiropractic, dental)

    Example:
        >>> pvp = PhoneVerticalPair(
        ...     office_phone="+17705753103",
        ...     vertical="chiropractic"
        ... )
        >>> pvp.canonical_key
        'pv1:+17705753103:chiropractic'
    """

    model_config = ConfigDict(
        frozen=True,  # Immutable for hashability
        str_strip_whitespace=True,
    )

    office_phone: str
    vertical: str

    @field_validator("office_phone")
    @classmethod
    def validate_e164(cls, v: str) -> str:
        """Validate E.164 phone format.

        Per ITU-T E.164: + followed by 1-15 digits.
        """
        if not re.match(r"^\+[1-9]\d{1,14}$", v):
            raise ValueError(
                f"Invalid E.164 format: {v}. "
                f"Expected format: +[country][number] (e.g., +17705753103)"
            )
        return v

    @property
    def canonical_key(self) -> str:
        """Version-prefixed cache/routing key.

        Per parent spike ADR-PVP-002: pv1: prefix enables graceful
        migration to pv2: if multi-tenant requirements emerge.
        """
        return f"pv1:{self.office_phone}:{self.vertical}"

    # Backward compatibility with tuple unpacking (per legacy namedtuple)
    def __iter__(self) -> Iterator[str]:
        """Enable tuple unpacking: phone, vertical = pvp."""
        return iter((self.office_phone, self.vertical))

    def __getitem__(self, index: int) -> str:
        """Enable index access: pvp[0], pvp[1]."""
        return (self.office_phone, self.vertical)[index]

    def __hash__(self) -> int:
        """Enable use as dict key / set member."""
        return hash((self.office_phone, self.vertical))

    @classmethod
    def from_business(cls, business: "Business") -> "PhoneVerticalPair":
        """Create PhoneVerticalPair from Business entity.

        Args:
            business: Business model with office_phone and vertical fields.

        Returns:
            PhoneVerticalPair instance.

        Raises:
            InsightsValidationError: If office_phone or vertical is None.
        """
        from autom8_asana.exceptions import InsightsValidationError

        if not business.office_phone:
            raise InsightsValidationError(
                "Cannot create PhoneVerticalPair: office_phone is required",
                field="office_phone",
            )
        if not business.vertical:
            raise InsightsValidationError(
                "Cannot create PhoneVerticalPair: vertical is required",
                field="vertical",
            )
        return cls(
            office_phone=business.office_phone,
            vertical=business.vertical,
        )
```

### 4.2 InsightsRequest

**Location**: `autom8_asana/clients/data/models.py`

```python
"""Request/response models for autom8_data insights API."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InsightsRequest(BaseModel):
    """Request body for insights factory API.

    Maps to POST /api/v1/factory/{factory_name} request body.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    # Filtering
    office_phone: str
    vertical: str

    # Time period
    insights_period: str | None = Field(default="lifetime")
    start_date: date | None = None
    end_date: date | None = None

    # Grouping
    metrics: list[str] | None = None
    dimensions: list[str] | None = None
    groups: list[str] | None = None
    break_down: list[str] | None = None

    # Caching
    refresh: bool = False

    # Additional factory-specific filters
    filters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("insights_period")
    @classmethod
    def validate_period(cls, v: str | None) -> str | None:
        """Validate period format.

        Valid formats:
        - Standard: lifetime, date, day, week, month, quarter, year
        - Trailing: t1, t3, t7, t10, t14, t30, t90, t180, t365
        - Last: l1, l3, l7, l10, l14, l30, l90, l180, l365, l24h
        """
        if v is None:
            return v

        v_lower = v.lower()
        valid_standards = {
            "lifetime", "date", "day", "week", "month", "quarter", "year"
        }

        if v_lower in valid_standards:
            return v_lower

        # Trailing days: t{N}
        if re.match(r"^t\d+$", v_lower):
            return v_lower

        # Last days: l{N} or l{N}h
        if re.match(r"^l\d+h?$", v_lower):
            return v_lower

        raise ValueError(
            f"Invalid period format: {v}. "
            f"Expected: lifetime, t30, l7, etc."
        )


import re  # Add at top of file
```

### 4.3 InsightsResponse

```python
class ColumnInfo(BaseModel):
    """Column metadata for dtype preservation.

    Per parent spike: Include dtype hints for DataFrame reconstruction.
    """

    name: str
    dtype: str  # "int64", "float64", "datetime64[ns]", "object", etc.
    nullable: bool = True


class InsightsMetadata(BaseModel):
    """Metadata about the insights response.

    Per parent spike API spec: Include sort_history from DataFrame.attrs.
    Per ADR-INS-004 (revised): Include staleness indicators for cache fallback.
    """

    factory: str
    frame_type: str | None = None
    insights_period: str | None = None

    row_count: int
    column_count: int
    columns: list[ColumnInfo]

    cache_hit: bool
    duration_ms: float

    sort_history: list[str] | None = None

    # Staleness indicators (per ADR-INS-004 revision)
    is_stale: bool = False  # True if served from cache during service unavailability
    cached_at: datetime | None = None  # When response was originally cached (if stale)


class InsightsResponse(BaseModel):
    """Response from insights factory API.

    Per FR-005: Contains data, metadata, and DataFrame conversion methods.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    data: list[dict[str, Any]]
    metadata: InsightsMetadata
    request_id: str
    warnings: list[str] = Field(default_factory=list)

    def to_dataframe(self) -> "pl.DataFrame":
        """Convert response to Polars DataFrame.

        Per ADR-0028: autom8_asana uses Polars as primary DataFrame library.
        Per FR-005.4: Reconstructs dtypes from metadata.

        Returns:
            Polars DataFrame with proper dtypes.
        """
        import polars as pl

        if not self.data:
            # Return empty DataFrame with schema
            schema = {
                col.name: self._polars_dtype(col.dtype)
                for col in self.metadata.columns
            }
            return pl.DataFrame(schema=schema)

        df = pl.DataFrame(self.data)

        # Cast columns to correct dtypes
        for col_info in self.metadata.columns:
            if col_info.name in df.columns:
                target_dtype = self._polars_dtype(col_info.dtype)
                if target_dtype is not None:
                    try:
                        df = df.with_columns(
                            pl.col(col_info.name).cast(target_dtype)
                        )
                    except Exception:
                        # Log and continue with original dtype
                        pass

        return df

    def to_pandas(self) -> "pd.DataFrame":
        """Convert response to pandas DataFrame.

        Per FR-005.5: Backward compatibility with pandas consumers.

        Returns:
            pandas DataFrame.
        """
        return self.to_dataframe().to_pandas()

    @staticmethod
    def _polars_dtype(dtype_str: str) -> "pl.DataType | None":
        """Map dtype string to Polars dtype."""
        import polars as pl

        dtype_map = {
            "int64": pl.Int64,
            "int32": pl.Int32,
            "float64": pl.Float64,
            "float32": pl.Float32,
            "bool": pl.Boolean,
            "object": pl.Utf8,
            "string": pl.Utf8,
            "datetime64[ns]": pl.Datetime,
            "date": pl.Date,
        }
        return dtype_map.get(dtype_str)
```

### 4.4 BatchInsightsResponse

```python
class BatchInsightsResult(BaseModel):
    """Result for a single PVP in batch response."""

    pvp: PhoneVerticalPair
    response: InsightsResponse | None = None
    error: str | None = None

    @property
    def success(self) -> bool:
        """Whether this PVP succeeded."""
        return self.response is not None and self.error is None


class BatchInsightsResponse(BaseModel):
    """Response from batch insights request.

    Per FR-006: Partial failures included in response, not raised.
    """

    results: dict[str, BatchInsightsResult]  # keyed by canonical_key
    request_id: str
    total_count: int
    success_count: int
    failure_count: int

    def to_dataframe(self) -> "pl.DataFrame":
        """Concatenate all successful results into single DataFrame.

        Returns:
            Combined Polars DataFrame from all successful responses.
        """
        import polars as pl

        dfs = []
        for result in self.results.values():
            if result.success and result.response:
                df = result.response.to_dataframe()
                # Add canonical_key column for grouping
                df = df.with_columns(
                    pl.lit(result.pvp.canonical_key).alias("_pvp_key")
                )
                dfs.append(df)

        if not dfs:
            return pl.DataFrame()

        return pl.concat(dfs)

    def get(self, pvp: PhoneVerticalPair) -> BatchInsightsResult | None:
        """Get result for a specific PhoneVerticalPair."""
        return self.results.get(pvp.canonical_key)
```

---

## 5. DataServiceClient

### 5.1 Client Implementation

**Location**: `autom8_asana/clients/data/client.py`

```python
"""Client for autom8_data insights API.

Per FR-001: DataServiceClient in autom8_asana.clients module.
Per FR-001.5: Implements context manager protocol.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncIterator

import httpx

from autom8_asana.clients.data.config import DataServiceConfig
from autom8_asana.clients.data.models import (
    BatchInsightsResponse,
    BatchInsightsResult,
    InsightsMetadata,
    InsightsRequest,
    InsightsResponse,
)
from autom8_asana.exceptions import (
    InsightsError,
    InsightsNotFoundError,
    InsightsServiceError,
    InsightsValidationError,
)
from autom8_asana.models.contracts import PhoneVerticalPair
from autom8_asana.transport.circuit_breaker import CircuitBreaker
from autom8_asana.transport.retry import RetryHandler

if TYPE_CHECKING:
    from autom8_asana.protocols.auth import AuthProvider
    from autom8_asana.protocols.log import LogProvider


class DataServiceClient:
    """Client for autom8_data satellite service.

    Provides access to analytics insights via REST API with:
    - S2S JWT authentication
    - Circuit breaker for cascade failure prevention
    - Retry with exponential backoff
    - Connection pooling

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
    """

    # Valid factory names (14 total per parent spike)
    VALID_FACTORIES = frozenset({
        "account", "ads", "adsets", "campaigns", "spend",
        "leads", "appts", "assets", "targeting", "payments",
        "business_offers", "ad_questions", "ad_tests", "base",
    })

    def __init__(
        self,
        config: DataServiceConfig | None = None,
        auth_provider: AuthProvider | None = None,
        logger: LogProvider | None = None,
    ) -> None:
        """Initialize DataServiceClient.

        Args:
            config: Service configuration. Defaults to DataServiceConfig.from_env().
            auth_provider: Authentication provider for JWT tokens.
                If None, uses environment variable for API key.
            logger: Optional logger for request/response logging.
        """
        self._config = config or DataServiceConfig.from_env()
        self._auth_provider = auth_provider
        self._logger = logger

        # Initialize retry handler with data service config
        self._retry_handler = RetryHandler(self._config.retry, logger)

        # Initialize circuit breaker
        self._circuit_breaker = CircuitBreaker(self._config.circuit_breaker, logger)

        # HTTP client (created lazily)
        self._client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create httpx client with JWT auth."""
        if self._client is not None:
            return self._client

        async with self._client_lock:
            if self._client is not None:
                return self._client

            # Get auth token
            token = self._get_auth_token()

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

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            if token:
                headers["Authorization"] = f"Bearer {token}"

            self._client = httpx.AsyncClient(
                base_url=self._config.base_url,
                headers=headers,
                timeout=timeout,
                limits=limits,
            )

        return self._client

    def _get_auth_token(self) -> str | None:
        """Get JWT token from auth provider or environment."""
        if self._auth_provider:
            return self._auth_provider.get_secret(self._config.token_key)
        # Fallback to environment variable
        return os.environ.get(self._config.token_key)

    async def close(self) -> None:
        """Close HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "DataServiceClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit - close client."""
        await self.close()

    # --- Main API Methods ---

    async def get_insights_async(
        self,
        office_phone: str,
        vertical: str,
        *,
        factory: str = "account",
        period: str | None = "lifetime",
        start_date: str | None = None,
        end_date: str | None = None,
        metrics: list[str] | None = None,
        dimensions: list[str] | None = None,
        refresh: bool = False,
    ) -> InsightsResponse:
        """Fetch analytics insights for a business.

        Per FR-003: Primary async method for fetching insights.

        Args:
            office_phone: E.164 formatted phone number.
            vertical: Business vertical.
            factory: InsightsFactory name (default: "account").
            period: Time period preset (default: "lifetime").
            start_date: Custom start date (YYYY-MM-DD).
            end_date: Custom end date (YYYY-MM-DD).
            metrics: Override default metrics.
            dimensions: Override default dimensions.
            refresh: Force cache refresh.

        Returns:
            InsightsResponse with data and metadata.

        Raises:
            InsightsValidationError: Invalid inputs.
            InsightsNotFoundError: No data for PVP.
            InsightsServiceError: Upstream service failure.
            CircuitBreakerOpenError: Service degraded.
        """
        # Validate inputs
        self._validate_factory(factory)
        pvp = PhoneVerticalPair(office_phone=office_phone, vertical=vertical)

        # Build request
        request = InsightsRequest(
            office_phone=pvp.office_phone,
            vertical=pvp.vertical,
            insights_period=period,
            start_date=self._parse_date(start_date),
            end_date=self._parse_date(end_date),
            metrics=metrics,
            dimensions=dimensions,
            refresh=refresh,
        )

        # Execute with circuit breaker and retry
        return await self._execute_request(factory, request)

    async def get_insights_batch_async(
        self,
        pairs: list[PhoneVerticalPair],
        *,
        factory: str = "account",
        period: str | None = "lifetime",
        refresh: bool = False,
        max_concurrency: int = 10,
    ) -> BatchInsightsResponse:
        """Fetch insights for multiple businesses.

        Per FR-006: Batch support with partial failure handling.

        Args:
            pairs: List of PhoneVerticalPairs.
            factory: InsightsFactory name.
            period: Time period preset.
            refresh: Force cache refresh.
            max_concurrency: Max concurrent requests.

        Returns:
            BatchInsightsResponse with results keyed by canonical_key.
        """
        if len(pairs) > self._config.max_batch_size:
            raise InsightsValidationError(
                f"Batch size {len(pairs)} exceeds maximum {self._config.max_batch_size}",
                field="pairs",
            )

        self._validate_factory(factory)
        request_id = str(uuid.uuid4())

        # Execute requests concurrently with semaphore
        semaphore = asyncio.Semaphore(max_concurrency)
        results: dict[str, BatchInsightsResult] = {}

        async def fetch_one(pvp: PhoneVerticalPair) -> None:
            async with semaphore:
                try:
                    response = await self.get_insights_async(
                        office_phone=pvp.office_phone,
                        vertical=pvp.vertical,
                        factory=factory,
                        period=period,
                        refresh=refresh,
                    )
                    results[pvp.canonical_key] = BatchInsightsResult(
                        pvp=pvp,
                        response=response,
                    )
                except InsightsError as e:
                    results[pvp.canonical_key] = BatchInsightsResult(
                        pvp=pvp,
                        error=str(e),
                    )

        await asyncio.gather(*[fetch_one(pvp) for pvp in pairs])

        success_count = sum(1 for r in results.values() if r.success)
        return BatchInsightsResponse(
            results=results,
            request_id=request_id,
            total_count=len(pairs),
            success_count=success_count,
            failure_count=len(pairs) - success_count,
        )

    # --- Internal Methods ---

    async def _execute_request(
        self,
        factory: str,
        request: InsightsRequest,
    ) -> InsightsResponse:
        """Execute HTTP request with circuit breaker and retry."""
        client = await self._get_client()
        request_id = str(uuid.uuid4())

        # Circuit breaker check
        await self._circuit_breaker.check()

        path = f"/api/v1/factory/{factory}"
        attempt = 0

        while True:
            try:
                if self._logger:
                    self._logger.debug(
                        f"POST {path}",
                        extra={"request_id": request_id},
                    )

                response = await client.post(
                    path,
                    json=request.model_dump(exclude_none=True),
                    headers={"X-Request-Id": request_id},
                )

                # Handle errors
                if response.status_code >= 400:
                    error = self._parse_error(response, request_id)

                    # Check if retryable
                    if self._retry_handler.should_retry(response.status_code, attempt):
                        if response.status_code >= 500:
                            await self._circuit_breaker.record_failure(error)
                        await self._retry_handler.wait(attempt)
                        attempt += 1
                        continue

                    # Record failure for circuit breaker
                    if response.status_code >= 500:
                        await self._circuit_breaker.record_failure(error)
                    raise error

                # Parse successful response
                body = response.json()
                await self._circuit_breaker.record_success()

                return InsightsResponse(
                    data=body.get("data", []),
                    metadata=InsightsMetadata(**body.get("metadata", {})),
                    request_id=request_id,
                    warnings=body.get("warnings", []),
                )

            except httpx.TimeoutException as e:
                await self._circuit_breaker.record_failure(e)
                if self._retry_handler.should_retry(504, attempt):
                    await self._retry_handler.wait(attempt)
                    attempt += 1
                    continue
                raise InsightsServiceError(
                    "Request timed out",
                    request_id=request_id,
                    reason="timeout",
                ) from e

            except httpx.HTTPError as e:
                await self._circuit_breaker.record_failure(e)
                raise InsightsServiceError(
                    f"HTTP error: {e}",
                    request_id=request_id,
                ) from e

    def _validate_factory(self, factory: str) -> None:
        """Validate factory name."""
        if factory.lower() not in self.VALID_FACTORIES:
            raise InsightsValidationError(
                f"Invalid factory: {factory}. "
                f"Valid factories: {', '.join(sorted(self.VALID_FACTORIES))}",
                field="factory",
            )

    def _parse_date(self, date_str: str | None) -> "date | None":
        """Parse date string to date object."""
        from datetime import date

        if date_str is None:
            return None
        return date.fromisoformat(date_str)

    def _parse_error(
        self,
        response: httpx.Response,
        request_id: str,
    ) -> InsightsError:
        """Parse error response to appropriate exception."""
        status = response.status_code
        message = f"autom8_data API error (HTTP {status})"

        try:
            body = response.json()
            if "error" in body:
                message = body["error"]
            elif "detail" in body:
                message = body["detail"]
        except Exception:
            pass

        if status == 400:
            return InsightsValidationError(message, request_id=request_id)
        elif status == 404:
            return InsightsNotFoundError(message, request_id=request_id)
        else:
            return InsightsServiceError(
                message,
                request_id=request_id,
                status_code=status,
            )
```

### 5.2 Sync Wrapper

```python
def get_insights(
    self,
    office_phone: str,
    vertical: str,
    **kwargs: Any,
) -> InsightsResponse:
    """Synchronous wrapper for get_insights_async.

    Per FR-004 and ADR-0002: Fail-fast in async context.

    Raises:
        SyncInAsyncContextError: If called from async context.
    """
    from autom8_asana.transport.sync import run_sync

    return run_sync(
        self.get_insights_async(office_phone, vertical, **kwargs),
        method_name="get_insights",
        async_method_name="get_insights_async",
    )
```

---

## 6. Exception Hierarchy

### 6.1 InsightsError Classes

**Location**: Add to `autom8_asana/exceptions.py`

```python
# --- Insights API Exceptions (FR-008) ---

class InsightsError(AsanaError):
    """Base exception for insights API errors.

    Per FR-008.1: Base class in autom8_asana.exceptions.

    Attributes:
        request_id: Request correlation ID for tracing.
    """

    def __init__(
        self,
        message: str,
        *,
        request_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.request_id = request_id


class InsightsValidationError(InsightsError):
    """Invalid input for insights request.

    Per FR-008.2: 400-level client errors.

    Attributes:
        field: Field name that failed validation.
    """

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.field = field


class InsightsNotFoundError(InsightsError):
    """No insights data found for the requested parameters.

    Per FR-008.3: 404-level not found errors.
    """

    pass


class InsightsServiceError(InsightsError):
    """Upstream service failure.

    Per FR-008.4: 500-level server errors.

    Attributes:
        reason: Failure reason (timeout, circuit_breaker, etc.)
    """

    def __init__(
        self,
        message: str,
        *,
        reason: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.reason = reason
```

---

## 7. Configuration

### 7.1 DataServiceConfig

**Location**: `autom8_asana/clients/data/config.py`

```python
"""Configuration for autom8_data client.

Per FR-001.2: Constructor accepts base_url with env default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TimeoutConfig:
    """HTTP timeout configuration."""

    connect: float = 5.0
    read: float = 30.0
    write: float = 30.0
    pool: float = 5.0


@dataclass(frozen=True)
class ConnectionPoolConfig:
    """HTTP connection pool configuration."""

    max_connections: int = 10
    max_keepalive_connections: int = 5
    keepalive_expiry: float = 30.0


@dataclass(frozen=True)
class RetryConfig:
    """Retry configuration for insights API.

    Per NFR-002: 2 retries with exponential backoff.
    """

    max_retries: int = 2
    base_delay: float = 1.0
    max_delay: float = 10.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_status_codes: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 502, 503, 504})
    )


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Circuit breaker configuration.

    Per NFR-002: 5 failures in 60s triggers open state.
    """

    enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 1


@dataclass
class DataServiceConfig:
    """Configuration for DataServiceClient.

    Per FR-001.2: base_url defaults from AUTOM8_DATA_URL env var.
    """

    base_url: str = field(
        default_factory=lambda: os.environ.get(
            "AUTOM8_DATA_URL", "http://localhost:8000"
        )
    )
    token_key: str = "AUTOM8_DATA_API_KEY"

    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    connection_pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)

    max_batch_size: int = 50  # Per FR-006.4

    @classmethod
    def from_env(cls) -> "DataServiceConfig":
        """Create config from environment variables."""
        return cls(
            base_url=os.environ.get("AUTOM8_DATA_URL", "http://localhost:8000"),
        )
```

---

## 8. Feature Flags

### 8.1 Feature Flag Integration

**Environment Variable**: `AUTOM8_DATA_INSIGHTS_ENABLED`

```python
# In DataServiceClient.__init__
def __init__(self, ...):
    ...
    self._enabled = os.environ.get(
        "AUTOM8_DATA_INSIGHTS_ENABLED", "false"
    ).lower() == "true"

async def get_insights_async(self, ...):
    if not self._enabled:
        raise InsightsServiceError(
            "Insights integration is disabled. "
            "Set AUTOM8_DATA_INSIGHTS_ENABLED=true to enable.",
            reason="feature_disabled",
        )
    ...
```

### 8.2 Feature Flag Rollout

| Phase | Flag Value | Behavior |
|-------|------------|----------|
| Sprint 1 | `false` (default) | Disabled, raises error |
| Sprint 2 | `true` (default) | Enabled for all |
| Post-launch | Remove flag | Always enabled |

---

## 9. Business Integration

### 9.1 Business.get_insights_async()

**Per FR-007**: Convenience method on Business entity.

**Location**: Add to `autom8_asana/models/business/business.py`

```python
async def get_insights_async(
    self,
    client: "DataServiceClient",
    *,
    factory: str = "account",
    period: str = "lifetime",
    **kwargs: Any,
) -> "InsightsResponse":
    """Fetch analytics insights for this business.

    Per FR-007: Convenience method using self.office_phone and self.vertical.

    Args:
        client: DataServiceClient instance.
        factory: InsightsFactory name.
        period: Time period preset.
        **kwargs: Additional parameters for get_insights_async.

    Returns:
        InsightsResponse with data and metadata.

    Raises:
        InsightsValidationError: If office_phone or vertical is None.
        InsightsError: On API errors.

    Example:
        >>> async with DataServiceClient() as data_client:
        ...     business = await Business.from_gid_async(asana_client, gid)
        ...     insights = await business.get_insights_async(
        ...         data_client, factory="account", period="t30"
        ...     )
        ...     df = insights.to_dataframe()
    """
    from autom8_asana.exceptions import InsightsValidationError

    if not self.office_phone:
        raise InsightsValidationError(
            "Cannot request insights: office_phone is required",
            field="office_phone",
        )
    if not self.vertical:
        raise InsightsValidationError(
            "Cannot request insights: vertical is required",
            field="vertical",
        )

    return await client.get_insights_async(
        office_phone=self.office_phone,
        vertical=self.vertical,
        factory=factory,
        period=period,
        **kwargs,
    )
```

---

## 10. Sequence Diagrams

### 10.1 Single Insights Request

```
┌────────┐    ┌─────────────────┐    ┌─────────────┐    ┌──────────────┐
│Consumer│    │DataServiceClient│    │CircuitBreaker│    │autom8_data   │
└───┬────┘    └───────┬─────────┘    └──────┬──────┘    └──────┬───────┘
    │                 │                     │                   │
    │ get_insights_   │                     │                   │
    │   async()       │                     │                   │
    │────────────────▶│                     │                   │
    │                 │                     │                   │
    │                 │ check()             │                   │
    │                 │────────────────────▶│                   │
    │                 │                     │                   │
    │                 │ [CLOSED]            │                   │
    │                 │◀────────────────────│                   │
    │                 │                     │                   │
    │                 │ POST /api/v1/factory/account            │
    │                 │─────────────────────────────────────────▶
    │                 │                     │                   │
    │                 │                     │   200 OK + JSON   │
    │                 │◀─────────────────────────────────────────
    │                 │                     │                   │
    │                 │ record_success()    │                   │
    │                 │────────────────────▶│                   │
    │                 │                     │                   │
    │ InsightsResponse│                     │                   │
    │◀────────────────│                     │                   │
    │                 │                     │                   │
```

### 10.2 Circuit Breaker Open Scenario

```
┌────────┐    ┌─────────────────┐    ┌─────────────┐
│Consumer│    │DataServiceClient│    │CircuitBreaker│
└───┬────┘    └───────┬─────────┘    └──────┬──────┘
    │                 │                     │
    │ get_insights_   │                     │
    │   async()       │                     │
    │────────────────▶│                     │
    │                 │                     │
    │                 │ check()             │
    │                 │────────────────────▶│
    │                 │                     │
    │                 │ [OPEN - 5 failures] │
    │                 │◀────────────────────│
    │                 │                     │
    │ CircuitBreakerOpenError               │
    │◀────────────────│                     │
    │                 │                     │
```

---

## 11. Error Handling

### 11.1 Error Response Mapping

| HTTP Status | Exception | Retry? | Circuit Breaker |
|-------------|-----------|--------|-----------------|
| 400 | InsightsValidationError | No | No |
| 401 | InsightsServiceError (auth) | No | No |
| 404 | InsightsNotFoundError | No | No |
| 429 | InsightsServiceError (rate_limit) | Yes (with Retry-After) | No |
| 500 | InsightsServiceError | Yes | Record failure |
| 502 | InsightsServiceError | Yes | Record failure |
| 503 | InsightsServiceError | Yes | Record failure |
| 504 | InsightsServiceError (timeout) | Yes | Record failure |
| Timeout | InsightsServiceError | Yes | Record failure |

### 11.2 PII Redaction

Per NFR-005: Phone numbers may be PII.

```python
def _redact_phone(phone: str) -> str:
    """Redact phone number for error messages."""
    if len(phone) <= 4:
        return "***"
    return phone[:4] + "*" * (len(phone) - 4)

# In error handling
raise InsightsValidationError(
    f"Invalid phone format: {_redact_phone(office_phone)}",
    field="office_phone",
)
```

---

## 12. Observability

### 12.1 Logging

Per NFR-003: Structured logs for request/response/error.

```python
# Request logging
self._logger.info(
    "insights_request",
    extra={
        "factory": factory,
        "period": period,
        "request_id": request_id,
        "pvp_canonical_key": pvp.canonical_key,
    },
)

# Response logging
self._logger.info(
    "insights_response",
    extra={
        "request_id": request_id,
        "row_count": response.metadata.row_count,
        "cache_hit": response.metadata.cache_hit,
        "duration_ms": response.metadata.duration_ms,
    },
)

# Error logging
self._logger.error(
    "insights_error",
    extra={
        "request_id": request_id,
        "status_code": status,
        "error_type": type(error).__name__,
    },
)
```

### 12.2 Metrics

Per NFR-003: Emit metrics for monitoring.

| Metric | Type | Labels |
|--------|------|--------|
| `insights_request_total` | Counter | factory, period |
| `insights_request_duration_ms` | Histogram | factory |
| `insights_error_total` | Counter | factory, error_type |
| `insights_cache_hit_total` | Counter | factory |
| `circuit_breaker_state` | Gauge | - |

---

## 13. Implementation Phases

### 13.1 Sprint 1: Foundation (Days 1-5)

| Task | Deliverable | Acceptance |
|------|-------------|------------|
| Create `models/contracts/` package | `PhoneVerticalPair` model | E.164 validation, canonical_key |
| Create `clients/data/` package | `DataServiceClient` skeleton | Context manager, config loading |
| Implement `get_insights_async` | Single factory support | Returns `InsightsResponse` |
| Add `InsightsError` hierarchy | 4 exception classes | All include request_id |
| Add feature flag | `AUTOM8_DATA_INSIGHTS_ENABLED` | Default off |
| Unit tests | 90% coverage of new code | Mocked HTTP responses |
| Integration test | Staging call | One successful call |

**Sprint 1 DoD**:
- [ ] `PhoneVerticalPair` with E.164 validation
- [ ] `DataServiceClient.get_insights_async()` working
- [ ] `InsightsResponse.to_dataframe()` returns Polars
- [ ] Exception hierarchy with request_id
- [ ] Feature flag controls activation
- [ ] Unit tests passing

### 13.2 Sprint 2: Hardening (Days 6-10)

| Task | Deliverable | Acceptance |
|------|-------------|------------|
| All 14 factories | Factory validation | Each factory callable |
| Batch insights | `get_insights_batch_async` | Up to 50 PVPs |
| Circuit breaker | Integration with transport | Trips after 5 failures |
| Retry logic | Exponential backoff | Respects Retry-After |
| Observability | Logging + metrics | Structured logs emitted |
| Sync wrapper | `get_insights()` | ADR-0002 compliant |

**Sprint 2 DoD**:
- [ ] All 14 factory types working
- [ ] Batch requests with partial failure handling
- [ ] Circuit breaker tripping on failures
- [ ] Retry with exponential backoff
- [ ] Metrics emitted to hooks
- [ ] Feature flag default: `true`

### 13.3 Sprint 3: Integration (Days 11-15)

| Task | Deliverable | Acceptance |
|------|-------------|------------|
| `Business.get_insights_async()` | Convenience method | Uses self.office_phone/vertical |
| Performance testing | Benchmark results | P95 < 500ms |
| Shadow mode (optional) | Compare with monolith | Parity validation |
| Documentation | SDK docs | All public methods documented |
| Examples | Usage examples | In docstrings and examples/ |

**Sprint 3 DoD**:
- [ ] Business entity integration
- [ ] P95 < 500ms validated
- [ ] SDK documentation complete
- [ ] Examples for common use cases

---

## 14. Architecture Decision Records

### ADR-INS-001: PhoneVerticalPair Ownership

**Context**: PhoneVerticalPair is needed by autom8_asana, autom8_data, and potentially other satellites.

**Decision**: autom8_asana owns its own `PhoneVerticalPair` Pydantic model.

**Rationale**:
- Avoids shared package dependency complexity
- autom8_asana can evolve independently
- "Rule of three" not yet met (only 2 consumers)
- API contract is the interface, not the class

**Consequences**:
- (+) No shared package dependency
- (+) Independent versioning
- (-) Duplicate model definitions
- (-) Must keep in sync manually

**Status**: Accepted

---

### ADR-INS-002: JSON Response Format (Defer Arrow)

**Context**: Parent spike recommends JSON with dtype metadata, Arrow via content negotiation for performance.

**Decision**: Use JSON with dtype metadata for v1. Arrow deferred to future.

**Rationale**:
- JSON is universally compatible (curl, browser)
- Polars can reconstruct DataFrame from JSON + metadata
- Arrow adds complexity (content negotiation, binary parsing)
- Response sizes < 10MB don't warrant Arrow overhead
- Can add Arrow later via `Accept: application/vnd.apache.arrow.stream`

**Consequences**:
- (+) Simpler initial implementation
- (+) Easy debugging (human-readable)
- (+) No binary protocol complexity
- (-) ~7x larger than Arrow for large responses
- (-) Serialization overhead

**Status**: Accepted

---

### ADR-INS-003: S2S JWT Authentication

**Context**: autom8_data requires authentication. Options: API key, JWT, OAuth2.

**Decision**: Use S2S JWT authentication reusing existing AuthProvider protocol.

**Rationale**:
- autom8_data already uses JWT (per parent spike)
- AuthProvider protocol exists in autom8_asana
- JWT enables fine-grained permissions if needed
- Consistent with platform auth patterns

**Consequences**:
- (+) Reuses existing AuthProvider
- (+) Consistent with platform
- (+) Token caching built-in
- (-) More complex than API key

**Status**: Accepted

---

### ADR-INS-004: Client-Side Cache with Fallback (REVISED)

**Context**: Where to cache insights responses? Options: client-side, Redis, autom8_data.

**Original Decision**: Delegate caching to autom8_data (server-side).

**Revised Decision**: Client-side cache with fallback using existing `CacheProvider` infrastructure.

**Revision Rationale**:
- User requirement: Return stale data when autom8_data is unavailable
- autom8_asana already has production-ready tiered caching (Memory + Redis + S3)
- `CacheProvider` protocol provides versioned entries with staleness detection
- Graceful degradation pattern (ADR-0127) ensures cache failures don't break requests
- Can compose DataServiceClient with injected `CacheProvider`

**Implementation Pattern**:
```python
class DataServiceClient:
    def __init__(
        self,
        config: DataServiceConfig | None = None,
        cache_provider: CacheProvider | None = None,  # Injected
        staleness_settings: StalenessCheckSettings | None = None,
    ):
        self._cache = cache_provider
        self._staleness_settings = staleness_settings or StalenessCheckSettings()

    async def get_insights_async(self, ...) -> InsightsResponse:
        cache_key = f"insights:{factory}:{pvp.canonical_key}"

        # 1. Try autom8_data first (fresh data preferred)
        try:
            response = await self._fetch_from_service(...)
            # Cache successful response
            if self._cache:
                entry = CacheEntry(
                    key=cache_key,
                    data=response.model_dump(),
                    entry_type=EntryType.INSIGHTS,
                    cached_at=datetime.now(timezone.utc),
                    ttl=self._config.cache_ttl,
                )
                self._cache.set_versioned(cache_key, entry)
            return response
        except InsightsServiceError as e:
            # 2. On failure, check cache
            if self._cache:
                entry = self._cache.get_versioned(cache_key, EntryType.INSIGHTS)
                if entry and not self._is_too_stale(entry):
                    return self._make_stale_response(entry)
            raise  # No cache or too stale
```

**Required Changes**:
1. Add `EntryType.INSIGHTS` to `autom8_asana/cache/entry.py`
2. Add `AUTOM8_DATA_CACHE_TTL` to config (default: 300s for live analytics)
3. Add `is_stale: bool` and `cached_at: datetime | None` to `InsightsMetadata`
4. Use cache key format: `insights:{factory}:{canonical_key}`

**Consequences**:
- (+) Resilience when autom8_data unavailable
- (+) Reuses existing production-ready cache infrastructure
- (+) Graceful degradation on cache failures
- (+) Transparent staleness via metadata flags
- (-) Additional complexity vs pure server-side
- (-) Potential for stale data (acceptable per user decision)

**Status**: Accepted (revised from original)

---

### ADR-INS-005: Circuit Breaker Composition

**Context**: How to integrate circuit breaker with DataServiceClient?

**Decision**: Compose with existing `CircuitBreaker` class from transport layer.

**Rationale**:
- Existing CircuitBreaker is well-tested (ADR-0048)
- Consistent pattern with AsyncHTTPClient
- State machine logic already implemented
- Hook integration available

**Consequences**:
- (+) Reuses proven implementation
- (+) Consistent failure handling
- (+) Observability via hooks
- (-) Tight coupling to transport layer

**Status**: Accepted

---

## 15. Risk Assessment

### 15.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| autom8_data API changes | Medium | High | Pin API version, contract tests |
| Network latency > 500ms | Medium | Medium | Connection pooling, caching |
| JWT token expiration mid-request | Low | Medium | Automatic refresh on 401 |
| Polars dtype mismatch | Medium | Low | Fallback to original dtype |
| Circuit breaker false positives | Low | Medium | Tune thresholds, alerting |

### 15.2 Mitigation Strategies

1. **API Changes**: Implement API version header, add contract tests
2. **Latency**: Monitor P95, add client-side caching if needed
3. **Token Expiration**: Implement token refresh interceptor
4. **Dtype Mismatch**: Log warnings, use safe casting
5. **False Positives**: Monitor circuit breaker state, tune thresholds

---

## 16. Testing Strategy

### 16.1 Unit Tests

```python
# tests/unit/clients/data/test_client.py

@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for unit tests."""
    with respx.mock() as mock:
        yield mock

async def test_get_insights_success(mock_httpx_client):
    """Test successful insights request."""
    mock_httpx_client.post("/api/v1/factory/account").respond(
        json={
            "data": [{"spend": 100.0}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [{"name": "spend", "dtype": "float64", "nullable": True}],
                "cache_hit": False,
                "duration_ms": 50.0,
            },
        }
    )

    async with DataServiceClient() as client:
        response = await client.get_insights_async(
            office_phone="+17705753103",
            vertical="chiropractic",
        )

    assert response.metadata.row_count == 1
    assert len(response.data) == 1

async def test_get_insights_validation_error():
    """Test invalid factory raises validation error."""
    async with DataServiceClient() as client:
        with pytest.raises(InsightsValidationError) as exc:
            await client.get_insights_async(
                office_phone="+17705753103",
                vertical="chiropractic",
                factory="invalid_factory",
            )
    assert "Invalid factory" in str(exc.value)
```

### 16.2 Integration Tests

```python
# tests/integration/test_insights_integration.py

@pytest.mark.integration
async def test_insights_staging():
    """Integration test against staging autom8_data."""
    config = DataServiceConfig(
        base_url=os.environ["AUTOM8_DATA_STAGING_URL"],
    )

    async with DataServiceClient(config=config) as client:
        response = await client.get_insights_async(
            office_phone="+17705753103",
            vertical="chiropractic",
            factory="account",
            period="t30",
        )

    assert response.metadata.factory == "account"
    assert response.request_id is not None
```

---

## 17. Artifact Verification

| Artifact | Absolute Path | Status |
|----------|---------------|--------|
| This TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-insights-integration.md` | Created |
| PRD Reference | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-insights-integration.md` | Exists |

---

## 18. Handoff Checklist

Ready for Implementation phase when:

- [x] TDD covers all PRD requirements (FR-001 through FR-009)
- [x] Component boundaries and responsibilities are clear
- [x] Data models defined (PhoneVerticalPair, InsightsResponse)
- [x] API contracts specified (request/response schemas)
- [x] Key flows have sequence diagrams
- [x] NFRs have concrete approaches (circuit breaker, retry, observability)
- [x] ADRs document 5 significant decisions
- [x] Risks identified with mitigations
- [x] Implementation phases defined with DoD
- [x] Testing strategy outlined
- [x] Artifact verification table included

**Handoff**: Route to **Principal Engineer** for Sprint 1 implementation starting with `PhoneVerticalPair` model and `DataServiceClient` skeleton.

---

**TDD Author**: Architect (Claude Opus 4.5)
**Review Date**: 2025-12-30
**Approvers**: Pending stakeholder review
