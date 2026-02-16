"""Unified DataFrame persistence via the DataFrameStorage protocol.

Per TDD-UNIFIED-DF-PERSISTENCE-001 (S4-007/B6):
Single protocol with unified retry, error handling, and configuration
for all DataFrame S3 persistence operations.

Components:
- DataFrameStorage: @runtime_checkable Protocol for all persistence ops
- S3DataFrameStorage: Single S3 implementation using RetryOrchestrator
- create_s3_retry_orchestrator: Factory for S3 retry configuration

Design decisions (from TDD ADRs):
- ADR-B6-001: Single protocol covering all persistence operations
- ADR-B6-002: RetryOrchestrator injected at construction, not per-op
- ADR-B6-003: Phased migration (delegate, then deprecate)
- ADR-B6-004: Index ops accept dict[str, Any], not GidLookupIndex

Module: src/autom8_asana/dataframes/storage.py
"""

from __future__ import annotations

import asyncio
import io
import json
import threading
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

import polars as pl
from autom8y_log import get_logger

from autom8_asana.config import S3LocationConfig
from autom8_asana.core.exceptions import S3_TRANSPORT_ERRORS, S3TransportError
from autom8_asana.core.retry import (
    BackoffType,
    BudgetConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    DefaultRetryPolicy,
    RetryBudget,
    RetryOrchestrator,
    RetryPolicyConfig,
    Subsystem,
)

__all__ = [
    "DataFrameStorage",
    "S3DataFrameStorage",
    "create_s3_retry_orchestrator",
]

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class DataFrameStorage(Protocol):
    """Protocol for DataFrame persistence operations.

    Defines the complete interface for persisting and retrieving DataFrames,
    watermarks, GidLookupIndex data, and section-level parquet files to a
    storage backend.

    Per TDD-UNIFIED-DF-PERSISTENCE-001 Section 5: Single protocol covering
    all S3 persistence operations.
    """

    # ---- Availability ----

    @property
    def is_available(self) -> bool:
        """Whether the storage backend is currently healthy."""
        ...

    # ---- DataFrame operations ----

    async def save_dataframe(
        self,
        project_gid: str,
        df: pl.DataFrame,
        watermark: datetime,
        *,
        entity_type: str | None = None,
    ) -> bool:
        """Persist DataFrame and watermark atomically (best-effort).

        Args:
            project_gid: Asana project GID.
            df: Polars DataFrame to persist.
            watermark: Watermark timestamp (must be timezone-aware).
            entity_type: Optional entity type for watermark metadata.

        Returns:
            True if both writes succeed, False if either fails.

        Raises:
            ValueError: If watermark is not timezone-aware.
        """
        ...

    async def load_dataframe(
        self,
        project_gid: str,
    ) -> tuple[pl.DataFrame | None, datetime | None]:
        """Load DataFrame and watermark. Returns (None, None) if not found."""
        ...

    async def delete_dataframe(self, project_gid: str) -> bool:
        """Delete DataFrame, watermark, and index for a project."""
        ...

    # ---- Watermark operations ----

    async def save_watermark(self, project_gid: str, watermark: datetime) -> bool:
        """Persist watermark only (lightweight write-through)."""
        ...

    async def get_watermark(self, project_gid: str) -> datetime | None:
        """Get watermark without loading DataFrame."""
        ...

    async def load_all_watermarks(self) -> dict[str, datetime]:
        """Bulk load all watermarks (startup hydration)."""
        ...

    # ---- GidLookupIndex operations ----

    async def save_index(self, project_gid: str, index_data: dict[str, Any]) -> bool:
        """Persist serialized GidLookupIndex."""
        ...

    async def load_index(self, project_gid: str) -> dict[str, Any] | None:
        """Load serialized GidLookupIndex."""
        ...

    async def delete_index(self, project_gid: str) -> bool:
        """Delete GidLookupIndex."""
        ...

    # ---- Section operations ----

    async def save_section(
        self,
        project_gid: str,
        section_gid: str,
        df: pl.DataFrame,
        *,
        metadata: dict[str, str] | None = None,
    ) -> bool:
        """Persist a section-level parquet file."""
        ...

    async def load_section(
        self,
        project_gid: str,
        section_gid: str,
    ) -> pl.DataFrame | None:
        """Load a section-level parquet file."""
        ...

    async def delete_section(self, project_gid: str, section_gid: str) -> bool:
        """Delete a section-level parquet file."""
        ...

    # ---- Raw object operations (for manifests, etc.) ----

    async def save_json(self, key: str, data: bytes) -> bool:
        """Write raw JSON bytes to a key."""
        ...

    async def load_json(self, key: str) -> bytes | None:
        """Read raw bytes from a key. Returns None if not found."""
        ...

    async def delete_object(self, key: str) -> bool:
        """Delete a single object by key."""
        ...

    # ---- Enumeration ----

    async def list_projects(self) -> list[str]:
        """List all project GIDs with persisted data."""
        ...


# ---------------------------------------------------------------------------
# RetryOrchestrator factory
# ---------------------------------------------------------------------------


def create_s3_retry_orchestrator(
    budget: RetryBudget | None = None,
) -> RetryOrchestrator:
    """Create a RetryOrchestrator configured for S3 persistence operations.

    Per TDD Section 8.1: Configures exponential backoff with 3 attempts,
    0.5s base delay, and a circuit breaker with 5-failure threshold.

    Args:
        budget: Shared retry budget. If None, creates a standalone budget.
            In production, pass the application-wide shared budget.

    Returns:
        Configured RetryOrchestrator for Subsystem.S3.
    """
    policy = DefaultRetryPolicy(
        RetryPolicyConfig(
            backoff_type=BackoffType.EXPONENTIAL,
            max_attempts=3,
            base_delay=0.5,
            max_delay=10.0,
            jitter=True,
        )
    )

    if budget is None:
        budget = RetryBudget(
            BudgetConfig(
                per_subsystem_max=20,
                global_max=50,
                window_seconds=60.0,
            )
        )

    circuit_breaker = CircuitBreaker(
        CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60.0,
            half_open_max_probes=2,
            name="s3-dataframe-storage",
        )
    )

    return RetryOrchestrator(
        policy=policy,
        budget=budget,
        circuit_breaker=circuit_breaker,
        subsystem=Subsystem.S3,
    )


# ---------------------------------------------------------------------------
# S3 Implementation
# ---------------------------------------------------------------------------


class S3DataFrameStorage:
    """S3 implementation of DataFrameStorage protocol.

    Single S3 persistence implementation with:
    - RetryOrchestrator for coordinated retry with budget enforcement
    - S3LocationConfig for configuration
    - S3TransportError for error classification
    - asyncio.to_thread() for non-blocking I/O

    Per TDD Section 6: All S3 operations route through RetryOrchestrator.
    Degraded mode uses circuit breaker recovery, not manual timers.

    Key formats are identical to existing implementations (no migration needed):
        {prefix}{project_gid}/dataframe.parquet
        {prefix}{project_gid}/watermark.json
        {prefix}{project_gid}/gid_lookup_index.json
        {prefix}{project_gid}/manifest.json
        {prefix}{project_gid}/sections/{section_gid}.parquet

    Thread Safety:
        A single boto3 S3 client is shared across all to_thread() calls.
        Client creation is protected by threading.Lock.
        boto3 clients are thread-safe for S3 operations.
    """

    def __init__(
        self,
        location: S3LocationConfig,
        *,
        prefix: str = "dataframes/",
        retry_orchestrator: RetryOrchestrator | None = None,
        enabled: bool = True,
        connect_timeout: int = 10,
        read_timeout: int = 30,
    ) -> None:
        """Initialize S3 DataFrame storage.

        Args:
            location: S3 bucket/region/endpoint configuration.
            prefix: S3 key prefix for all objects (default "dataframes/").
            retry_orchestrator: RetryOrchestrator for S3 operations.
                If None, creates one with default S3 configuration.
            enabled: Master enable/disable switch.
            connect_timeout: boto3 connection timeout in seconds.
            read_timeout: boto3 read timeout in seconds.
        """
        self._location = location
        self._prefix = prefix
        self._retry = retry_orchestrator or create_s3_retry_orchestrator()
        self._enabled = enabled
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout

        self._client: Any = None
        self._client_lock = threading.Lock()
        self._permanently_disabled = False

        if not self._enabled:
            logger.info("s3_storage_disabled")
            self._permanently_disabled = True
        elif not self._location.bucket:
            logger.warning("s3_storage_no_bucket", prefix=self._prefix)
            self._permanently_disabled = True

    # ---- Key formatting (consolidated from 3 implementations) ----

    def _df_key(self, project_gid: str) -> str:
        """Generate S3 key for project DataFrame."""
        return f"{self._prefix}{project_gid}/dataframe.parquet"

    def _watermark_key(self, project_gid: str) -> str:
        """Generate S3 key for project watermark."""
        return f"{self._prefix}{project_gid}/watermark.json"

    def _index_key(self, project_gid: str) -> str:
        """Generate S3 key for project GidLookupIndex."""
        return f"{self._prefix}{project_gid}/gid_lookup_index.json"

    def _section_key(self, project_gid: str, section_gid: str) -> str:
        """Generate S3 key for section parquet."""
        return f"{self._prefix}{project_gid}/sections/{section_gid}.parquet"

    def _manifest_key(self, project_gid: str) -> str:
        """Generate S3 key for project manifest."""
        return f"{self._prefix}{project_gid}/manifest.json"

    # ---- Client management ----

    def _get_client(self) -> Any:
        """Get or create the boto3 S3 client.

        Returns:
            boto3 S3 client instance.

        Raises:
            RuntimeError: If boto3 is not available or bucket not configured.
        """
        if self._client is not None:
            return self._client

        with self._client_lock:
            # Double-check after acquiring lock
            if self._client is not None:
                return self._client

            import boto3
            from botocore.config import Config

            boto_config = Config(
                connect_timeout=self._connect_timeout,
                read_timeout=self._read_timeout,
                retries={"max_attempts": 0},  # RetryOrchestrator handles retries
            )

            client_kwargs: dict[str, Any] = {
                "region_name": self._location.region,
                "config": boto_config,
            }
            if self._location.endpoint_url:
                client_kwargs["endpoint_url"] = self._location.endpoint_url

            self._client = boto3.client("s3", **client_kwargs)

            logger.debug(
                "s3_storage_initialized",
                bucket=self._location.bucket,
                prefix=self._prefix,
                region=self._location.region,
            )

            return self._client

    # ---- Availability ----

    @property
    def is_available(self) -> bool:
        """Whether the storage backend is currently healthy.

        Returns False if permanently disabled (no bucket, disabled by config)
        or if the circuit breaker is open (transient S3 outage).
        Returns True when the circuit breaker allows requests (CLOSED or HALF_OPEN).
        """
        if self._permanently_disabled:
            return False
        return self._retry.circuit_breaker.allow_request()

    # ---- Core S3 operations (all go through RetryOrchestrator) ----

    async def _put_object(
        self,
        key: str,
        body: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> bool:
        """Write object to S3 via RetryOrchestrator.

        All S3 write operations route through this method.

        Args:
            key: S3 object key.
            body: Raw bytes to write.
            content_type: MIME content type.
            metadata: Optional S3 object metadata.

        Returns:
            True on success, False on failure.
        """
        if self._permanently_disabled:
            return False
        if not self._retry.circuit_breaker.allow_request():
            logger.warning("s3_storage_circuit_open", key=key, operation="put")
            return False

        try:
            client = self._get_client()

            def _do_put() -> None:
                put_kwargs: dict[str, Any] = {
                    "Bucket": self._location.bucket,
                    "Key": key,
                    "Body": body,
                    "ContentType": content_type,
                }
                if metadata:
                    put_kwargs["Metadata"] = metadata
                client.put_object(**put_kwargs)

            await self._retry.execute_with_retry_async(
                lambda: asyncio.to_thread(_do_put),
                operation_name=f"s3_put:{key}",
            )

            logger.debug(
                "s3_storage_put_success",
                key=key,
                size_bytes=len(body),
            )
            return True

        except CircuitBreakerOpenError:
            # CB is already open; recovery happens automatically via
            # HALF_OPEN after recovery_timeout.
            logger.warning("s3_storage_circuit_open", key=key, operation="put")
            return False
        except S3_TRANSPORT_ERRORS as e:
            wrapped = S3TransportError.from_boto_error(
                e, operation="put_object", bucket=self._location.bucket, key=key
            )
            if not wrapped.transient:
                # Permanent errors like AccessDenied indicate config issues, not
                # transient degradation. Log at ERROR but do not latch -- the
                # error is specific to this operation, not all future operations.
                logger.error(
                    "s3_storage_permanent_error",
                    key=key,
                    error_code=wrapped.error_code,
                    error=str(wrapped),
                )
            else:
                logger.error(
                    "s3_storage_transient_error_exhausted",
                    key=key,
                    operation="put",
                    error=str(wrapped),
                )
            return False

    async def _get_object(self, key: str) -> bytes | None:
        """Read object from S3 via RetryOrchestrator.

        All S3 read operations route through this method.

        Args:
            key: S3 object key.

        Returns:
            Raw bytes if found, None if not found or on error.
        """
        if self._permanently_disabled:
            return None
        if not self._retry.circuit_breaker.allow_request():
            logger.warning("s3_storage_circuit_open", key=key, operation="get")
            return None

        try:
            client = self._get_client()

            def _do_get() -> bytes:
                response = client.get_object(
                    Bucket=self._location.bucket,
                    Key=key,
                )
                body_bytes: bytes = response["Body"].read()
                return body_bytes

            data = await self._retry.execute_with_retry_async(
                lambda: asyncio.to_thread(_do_get),
                operation_name=f"s3_get:{key}",
            )

            logger.debug(
                "s3_storage_get_success",
                key=key,
                size_bytes=len(data),
            )
            return data

        except CircuitBreakerOpenError:
            # CB is already open; recovery happens automatically via
            # HALF_OPEN after recovery_timeout.
            logger.warning("s3_storage_circuit_open", key=key, operation="get")
            return None
        except S3_TRANSPORT_ERRORS as e:
            wrapped = S3TransportError.from_boto_error(
                e, operation="get_object", bucket=self._location.bucket, key=key
            )
            # Not-found is a normal application condition, not an error.
            # With _is_transient() fix (B1), NoSuchKey is not retried and
            # does not feed the CB. Handle it cleanly at debug level.
            if wrapped.error_code in ("NoSuchKey", "404", "NotFound"):
                logger.debug("s3_storage_not_found", key=key)
                return None
            if not wrapped.transient:
                logger.error(
                    "s3_storage_permanent_error",
                    key=key,
                    error_code=wrapped.error_code,
                    error=str(wrapped),
                )
            else:
                logger.error(
                    "s3_storage_transient_error_exhausted",
                    key=key,
                    operation="get",
                    error=str(wrapped),
                )
            return None

    async def _delete_s3_object(self, key: str) -> bool:
        """Delete object from S3 via RetryOrchestrator.

        Args:
            key: S3 object key.

        Returns:
            True on success (including not-found), False on error.
        """
        if self._permanently_disabled:
            return False
        if not self._retry.circuit_breaker.allow_request():
            logger.warning("s3_storage_circuit_open", key=key, operation="delete")
            return False

        try:
            client = self._get_client()

            def _do_delete() -> None:
                client.delete_object(
                    Bucket=self._location.bucket,
                    Key=key,
                )

            await self._retry.execute_with_retry_async(
                lambda: asyncio.to_thread(_do_delete),
                operation_name=f"s3_delete:{key}",
            )
            return True

        except CircuitBreakerOpenError:
            logger.warning("s3_storage_circuit_open", key=key, operation="delete")
            return False
        except S3_TRANSPORT_ERRORS as e:
            wrapped = S3TransportError.from_boto_error(
                e, operation="delete_object", bucket=self._location.bucket, key=key
            )
            if wrapped.error_code in ("NoSuchKey", "404", "NotFound"):
                return True  # Already gone
            if not wrapped.transient:
                logger.error(
                    "s3_storage_permanent_error",
                    key=key,
                    error_code=wrapped.error_code,
                    error=str(wrapped),
                )
            else:
                logger.error(
                    "s3_storage_transient_error_exhausted",
                    key=key,
                    operation="delete",
                    error=str(wrapped),
                )
            return False

    async def _list_common_prefixes(self, prefix: str) -> list[str]:
        """List common prefixes (directories) under a prefix.

        Args:
            prefix: S3 key prefix.

        Returns:
            List of prefix strings, or empty on error.
        """
        if self._permanently_disabled:
            return []
        if not self._retry.circuit_breaker.allow_request():
            logger.warning("s3_storage_circuit_open", operation="list")
            return []

        try:
            client = self._get_client()

            def _do_list() -> list[str]:
                paginator = client.get_paginator("list_objects_v2")
                prefixes: list[str] = []
                for page in paginator.paginate(
                    Bucket=self._location.bucket,
                    Prefix=prefix,
                    Delimiter="/",
                ):
                    for prefix_info in page.get("CommonPrefixes", []):
                        prefixes.append(prefix_info.get("Prefix", ""))
                return prefixes

            return await self._retry.execute_with_retry_async(
                lambda: asyncio.to_thread(_do_list),
                operation_name=f"s3_list:{prefix}",
            )

        except CircuitBreakerOpenError:
            logger.warning("s3_storage_circuit_open", operation="list")
            return []
        except S3_TRANSPORT_ERRORS as e:
            wrapped = S3TransportError.from_boto_error(
                e, operation="list_objects", bucket=self._location.bucket
            )
            if not wrapped.transient:
                logger.error(
                    "s3_storage_permanent_error",
                    operation="list",
                    error_code=wrapped.error_code,
                    error=str(wrapped),
                )
            else:
                logger.error(
                    "s3_storage_transient_error_exhausted",
                    operation="list",
                    error=str(wrapped),
                )
            return []

    # ---- Serialization helpers ----

    @staticmethod
    def _serialize_parquet(df: pl.DataFrame) -> bytes:
        """Serialize DataFrame to Parquet bytes."""
        buffer = io.BytesIO()
        df.write_parquet(buffer)
        buffer.seek(0)
        return buffer.read()

    @staticmethod
    def _deserialize_parquet(data: bytes) -> pl.DataFrame:
        """Deserialize Parquet bytes to DataFrame."""
        return pl.read_parquet(io.BytesIO(data))

    @staticmethod
    def _serialize_watermark(
        project_gid: str,
        watermark: datetime,
        df: pl.DataFrame | None = None,
        entity_type: str | None = None,
    ) -> bytes:
        """Serialize watermark metadata to JSON bytes.

        Format matches the established watermark JSON schema.
        """
        watermark_data: dict[str, Any] = {
            "project_gid": project_gid,
            "watermark": watermark.isoformat(),
            "saved_at": datetime.now(UTC).isoformat(),
        }
        if df is not None:
            watermark_data["row_count"] = len(df)
            watermark_data["columns"] = df.columns
        if entity_type is not None:
            watermark_data["entity_type"] = entity_type
        return json.dumps(watermark_data).encode("utf-8")

    @staticmethod
    def _deserialize_watermark(data: bytes) -> datetime:
        """Deserialize watermark JSON bytes to datetime."""
        wm_data = json.loads(data.decode("utf-8"))
        return datetime.fromisoformat(wm_data["watermark"])

    # ---- DataFrame operations ----

    async def save_dataframe(
        self,
        project_gid: str,
        df: pl.DataFrame,
        watermark: datetime,
        *,
        entity_type: str | None = None,
    ) -> bool:
        """Persist DataFrame and watermark to S3.

        Writes both dataframe.parquet and watermark.json. Both must
        succeed for the operation to return True. On partial failure,
        consumers must tolerate inconsistent state.

        Args:
            project_gid: Asana project GID.
            df: Polars DataFrame to persist.
            watermark: Watermark timestamp (must be timezone-aware).
            entity_type: Optional entity type for watermark metadata.

        Returns:
            True if both writes succeed, False if either fails.

        Raises:
            ValueError: If watermark is not timezone-aware.
        """
        if watermark.tzinfo is None:
            raise ValueError("Watermark timestamp must be timezone-aware")

        if self._permanently_disabled:
            logger.debug(
                "s3_storage_skip", operation="save_dataframe", project_gid=project_gid
            )
            return False

        # Serialize DataFrame to Parquet
        parquet_bytes = self._serialize_parquet(df)

        # Write DataFrame
        df_ok = await self._put_object(
            self._df_key(project_gid),
            parquet_bytes,
            content_type="application/octet-stream",
            metadata={
                "project-gid": project_gid,
                "row-count": str(len(df)),
                "watermark": watermark.isoformat(),
            },
        )
        if not df_ok:
            return False

        # Write watermark
        wm_bytes = self._serialize_watermark(project_gid, watermark, df, entity_type)
        wm_ok = await self._put_object(
            self._watermark_key(project_gid),
            wm_bytes,
            content_type="application/json",
        )

        if df_ok and wm_ok:
            logger.info(
                "s3_storage_dataframe_saved",
                project_gid=project_gid,
                row_count=len(df),
                watermark=watermark.isoformat(),
            )
        return df_ok and wm_ok

    async def load_dataframe(
        self,
        project_gid: str,
    ) -> tuple[pl.DataFrame | None, datetime | None]:
        """Load DataFrame and watermark from S3.

        Loads watermark first (fast check), then DataFrame.
        Returns (None, None) if not found or on error.

        Args:
            project_gid: Asana project GID.

        Returns:
            Tuple of (DataFrame, watermark) if found, (None, None) otherwise.
        """
        if self._permanently_disabled:
            logger.debug(
                "s3_storage_skip", operation="load_dataframe", project_gid=project_gid
            )
            return None, None

        # Load watermark first (fast existence check)
        wm_data = await self._get_object(self._watermark_key(project_gid))
        if wm_data is None:
            return None, None

        watermark = self._deserialize_watermark(wm_data)

        # Load DataFrame
        df_data = await self._get_object(self._df_key(project_gid))
        if df_data is None:
            logger.warning(
                "s3_storage_orphan_watermark",
                project_gid=project_gid,
            )
            return None, None

        df = self._deserialize_parquet(df_data)

        logger.info(
            "s3_storage_dataframe_loaded",
            project_gid=project_gid,
            row_count=len(df),
            watermark=watermark.isoformat(),
        )
        return df, watermark

    async def delete_dataframe(self, project_gid: str) -> bool:
        """Delete DataFrame, watermark, and index for a project.

        Idempotent: returns True even if objects do not exist.

        Args:
            project_gid: Asana project GID.

        Returns:
            True if all deletes succeed, False on error.
        """
        if self._permanently_disabled:
            return False

        keys = [
            self._df_key(project_gid),
            self._watermark_key(project_gid),
            self._index_key(project_gid),
        ]

        results = [await self._delete_s3_object(key) for key in keys]
        return all(results)

    # ---- Watermark operations ----

    async def save_watermark(self, project_gid: str, watermark: datetime) -> bool:
        """Persist watermark only (lightweight write-through).

        Args:
            project_gid: Asana project GID.
            watermark: Watermark timestamp (must be timezone-aware).

        Returns:
            True on success, False on failure.

        Raises:
            ValueError: If watermark is not timezone-aware.
        """
        if watermark.tzinfo is None:
            raise ValueError("Watermark timestamp must be timezone-aware")

        if self._permanently_disabled:
            return False

        wm_bytes = self._serialize_watermark(project_gid, watermark)
        return await self._put_object(
            self._watermark_key(project_gid),
            wm_bytes,
            content_type="application/json",
        )

    async def get_watermark(self, project_gid: str) -> datetime | None:
        """Get watermark without loading DataFrame.

        Args:
            project_gid: Asana project GID.

        Returns:
            Watermark datetime if found, None otherwise.
        """
        data = await self._get_object(self._watermark_key(project_gid))
        if data is None:
            return None
        return self._deserialize_watermark(data)

    async def load_all_watermarks(self) -> dict[str, datetime]:
        """Bulk load all watermarks from S3.

        Lists all project prefixes, then loads each watermark in parallel.
        Used during startup for WatermarkRepository hydration.

        Returns:
            Dict mapping project_gid to watermark datetime.
        """
        if self._permanently_disabled:
            return {}

        project_gids = await self.list_projects()
        if not project_gids:
            return {}

        from autom8_asana.core.concurrency import gather_with_semaphore

        async def _load_one(gid: str) -> tuple[str, datetime | None]:
            wm = await self.get_watermark(gid)
            return (gid, wm)

        results = await gather_with_semaphore(
            (_load_one(gid) for gid in project_gids),
            concurrency=10,
            label="load_all_watermarks",
        )

        watermarks: dict[str, datetime] = {}
        for r in results:
            if isinstance(r, BaseException):
                logger.warning(
                    "watermark_load_failed",
                    error=str(r),
                    error_type=type(r).__name__,
                )
            else:
                gid, wm = r
                if wm is not None:
                    watermarks[gid] = wm

        logger.info("s3_storage_watermarks_loaded", count=len(watermarks))
        return watermarks

    # ---- GidLookupIndex operations ----

    async def save_index(self, project_gid: str, index_data: dict[str, Any]) -> bool:
        """Persist serialized GidLookupIndex to S3 as JSON.

        Per ADR-B6-004: Accepts dict, not GidLookupIndex. Serialization
        is the consumer's responsibility.

        Args:
            project_gid: Asana project GID.
            index_data: Serialized index data from GidLookupIndex.serialize().

        Returns:
            True on success, False on failure.
        """
        if self._permanently_disabled:
            return False

        json_bytes = json.dumps(index_data).encode("utf-8")
        return await self._put_object(
            self._index_key(project_gid),
            json_bytes,
            content_type="application/json",
        )

    async def load_index(self, project_gid: str) -> dict[str, Any] | None:
        """Load serialized GidLookupIndex from S3.

        Args:
            project_gid: Asana project GID.

        Returns:
            Deserialized index dict if found, None otherwise.
        """
        data = await self._get_object(self._index_key(project_gid))
        if data is None:
            return None
        result: dict[str, Any] = json.loads(data.decode("utf-8"))
        return result

    async def delete_index(self, project_gid: str) -> bool:
        """Delete GidLookupIndex from S3.

        Args:
            project_gid: Asana project GID.

        Returns:
            True on success, False on failure.
        """
        return await self._delete_s3_object(self._index_key(project_gid))

    # ---- Section operations ----

    async def save_section(
        self,
        project_gid: str,
        section_gid: str,
        df: pl.DataFrame,
        *,
        metadata: dict[str, str] | None = None,
    ) -> bool:
        """Persist a section-level parquet file.

        Does NOT update manifests -- that responsibility stays with
        SectionPersistence.

        Args:
            project_gid: Asana project GID.
            section_gid: Asana section GID.
            df: Polars DataFrame for the section.
            metadata: Optional S3 object metadata.

        Returns:
            True on success, False on failure.
        """
        parquet_bytes = self._serialize_parquet(df)
        return await self._put_object(
            self._section_key(project_gid, section_gid),
            parquet_bytes,
            content_type="application/octet-stream",
            metadata=metadata,
        )

    async def load_section(
        self,
        project_gid: str,
        section_gid: str,
    ) -> pl.DataFrame | None:
        """Load a section-level parquet file.

        Args:
            project_gid: Asana project GID.
            section_gid: Asana section GID.

        Returns:
            Polars DataFrame if found, None otherwise.
        """
        data = await self._get_object(self._section_key(project_gid, section_gid))
        if data is None:
            return None
        return self._deserialize_parquet(data)

    async def delete_section(self, project_gid: str, section_gid: str) -> bool:
        """Delete a section-level parquet file.

        Args:
            project_gid: Asana project GID.
            section_gid: Asana section GID.

        Returns:
            True on success, False on failure.
        """
        return await self._delete_s3_object(self._section_key(project_gid, section_gid))

    # ---- Raw object operations (for manifests, etc.) ----

    async def save_json(self, key: str, data: bytes) -> bool:
        """Write raw JSON bytes to a key.

        Used by SectionPersistence for manifest persistence.

        Args:
            key: Full S3 key.
            data: Raw JSON bytes.

        Returns:
            True on success, False on failure.
        """
        return await self._put_object(
            key,
            data,
            content_type="application/json",
        )

    async def load_json(self, key: str) -> bytes | None:
        """Read raw bytes from a key.

        Args:
            key: Full S3 key.

        Returns:
            Raw bytes if found, None otherwise.
        """
        return await self._get_object(key)

    async def delete_object(self, key: str) -> bool:
        """Delete a single object by key.

        Args:
            key: Full S3 key.

        Returns:
            True on success, False on failure.
        """
        return await self._delete_s3_object(key)

    # ---- Enumeration ----

    async def list_projects(self) -> list[str]:
        """List all project GIDs with persisted data.

        Scans S3 common prefixes under the configured prefix.

        Returns:
            Sorted list of project GID strings.
        """
        if self._permanently_disabled:
            return []

        prefixes = await self._list_common_prefixes(self._prefix)

        project_gids: list[str] = []
        for prefix_str in prefixes:
            if prefix_str.startswith(self._prefix):
                remaining = prefix_str[len(self._prefix) :]
                project_gid = remaining.rstrip("/")
                if project_gid:
                    project_gids.append(project_gid)

        return sorted(project_gids)

    # ---- Async context manager ----

    async def __aenter__(self) -> S3DataFrameStorage:
        """Initialize boto3 client eagerly."""
        if not self._permanently_disabled:
            await asyncio.to_thread(self._get_client)
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Release resources."""
        self._client = None
