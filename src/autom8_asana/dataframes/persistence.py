"""S3 persistence layer for DataFrames, watermarks, and GidLookupIndex.

Per sprint-materialization-002 Task T3:
Provides restart resilience by persisting DataFrame state and watermarks to S3.
Enables containers to load baseline state on startup instead of full Asana API fetch.

Per sprint-materialization-003 Task 2:
Extended to also persist GidLookupIndex for O(1) phone/vertical to GID resolution,
eliminating the need to rebuild the index from DataFrame on container restart.

This module provides:
- DataFramePersistence: S3-based persistence for DataFrames, watermarks, and GidLookupIndex
- Parquet format for efficient DataFrame serialization
- JSON format for GidLookupIndex serialization
- Graceful degradation when S3 is unavailable

Thread Safety:
    - Client initialization protected by threading.Lock
    - Read/write operations are thread-safe via boto3 client

Example:
    >>> from autom8_asana.dataframes.persistence import DataFramePersistence
    >>> from autom8_asana.services.gid_lookup import GidLookupIndex
    >>> from datetime import datetime, timezone
    >>> import polars as pl
    >>>
    >>> persistence = DataFramePersistence(bucket="my-bucket")
    >>> df = pl.DataFrame({"gid": ["123"], "name": ["Task 1"]})
    >>> watermark = datetime.now(timezone.utc)
    >>>
    >>> # Save DataFrame to S3
    >>> await persistence.save_dataframe("proj_123", df, watermark)
    >>>
    >>> # Save GidLookupIndex to S3
    >>> index = GidLookupIndex.from_dataframe(df)
    >>> await persistence.save_index("proj_123", index)
    >>>
    >>> # Load from S3
    >>> loaded_df, loaded_wm = await persistence.load_dataframe("proj_123")
    >>> loaded_index = await persistence.load_index("proj_123")
"""

from __future__ import annotations

import io
import json
from autom8y_log import get_logger
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from types import ModuleType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import polars as pl

    from autom8_asana.services.gid_lookup import GidLookupIndex

__all__ = ["DataFramePersistence", "PersistenceConfig"]

logger = get_logger(__name__)


@dataclass
class PersistenceConfig:
    """Configuration for DataFrame persistence.

    Attributes:
        bucket: S3 bucket name for persistence storage.
        prefix: Key prefix for persisted objects (default "dataframes/").
        region: AWS region (default "us-east-1").
        endpoint_url: Custom endpoint URL for LocalStack or S3-compatible storage.
        enabled: Whether persistence is enabled (default True).
    """

    bucket: str
    prefix: str = "dataframes/"
    region: str = "us-east-1"
    endpoint_url: str | None = None
    enabled: bool = True


class DataFramePersistence:
    """S3-based persistence for DataFrames and watermarks.

    Provides restart resilience by persisting DataFrame state to S3. Each project's
    DataFrame is stored as a Parquet file with an associated watermark JSON file.

    Key Structure:
        {prefix}{project_gid}/dataframe.parquet - DataFrame in Parquet format
        {prefix}{project_gid}/watermark.json - Watermark timestamp and metadata

    Features:
        - Parquet format for efficient, columnar storage
        - Watermark stored separately for fast metadata access
        - Graceful degradation when S3 is unavailable
        - Thread-safe client initialization

    Thread Safety:
        Uses a single boto3 client instance with internal connection pooling.
        Client creation is protected by a lock for safe lazy initialization.

    Example:
        >>> persistence = DataFramePersistence(bucket="my-cache-bucket")
        >>> df = pl.DataFrame({"gid": ["123"], "name": ["Task"]})
        >>> await persistence.save_dataframe("proj_123", df, datetime.now(timezone.utc))
        >>> loaded_df, watermark = await persistence.load_dataframe("proj_123")
    """

    def __init__(
        self,
        config: PersistenceConfig | None = None,
        *,
        bucket: str | None = None,
        prefix: str = "dataframes/",
        region: str | None = None,
        endpoint_url: str | None = None,
        enabled: bool = True,
    ) -> None:
        """Initialize DataFrame persistence.

        Can be initialized with a PersistenceConfig or individual parameters.
        Uses Pydantic Settings for environment variable configuration when
        no explicit bucket is provided.

        Args:
            config: Persistence configuration object (preferred).
            bucket: S3 bucket name (if config not provided).
            prefix: Key prefix (if config not provided).
            region: AWS region (if config not provided).
            endpoint_url: Custom endpoint URL (if config not provided).
            enabled: Whether persistence is enabled (default True).
        """
        if config is None:
            # Use Pydantic Settings for S3 configuration
            from autom8_asana.settings import get_settings

            s3_settings = get_settings().s3

            # Explicit parameters override settings from env
            resolved_bucket = bucket if bucket is not None else s3_settings.bucket
            resolved_prefix = prefix
            resolved_region = region if region is not None else s3_settings.region
            resolved_endpoint = (
                endpoint_url if endpoint_url is not None else s3_settings.endpoint_url
            )

            if not resolved_bucket:
                logger.warning(
                    "No S3 bucket configured for persistence. "
                    "Set ASANA_CACHE_S3_BUCKET or pass bucket parameter."
                )

            config = PersistenceConfig(
                bucket=resolved_bucket or "",
                prefix=resolved_prefix,
                region=resolved_region,
                endpoint_url=resolved_endpoint,
                enabled=enabled,
            )

        self._config = config
        self._client: Any = None
        self._client_lock = threading.Lock()
        self._degraded = False
        self._last_reconnect_attempt = 0.0
        self._reconnect_interval = 60.0  # seconds
        self._boto3_module: ModuleType | None = None
        self._botocore_module: ModuleType | None = None
        self._polars_module: ModuleType | None = None

        # Import optional dependencies
        self._initialize_modules()

    def _initialize_modules(self) -> None:
        """Initialize optional dependency modules."""
        # Import boto3
        try:
            import boto3
            import botocore.exceptions

            self._boto3_module = boto3
            self._botocore_module = botocore.exceptions
        except ImportError:
            logger.warning(
                "boto3 package not installed. DataFramePersistence will operate in degraded mode."
            )
            self._degraded = True

        # Import polars
        try:
            import polars

            self._polars_module = polars
        except ImportError:
            logger.warning(
                "polars package not installed. DataFramePersistence will operate in degraded mode."
            )
            self._degraded = True

        # Initialize client if modules available
        if not self._degraded:
            self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize S3 client with configuration."""
        if self._boto3_module is None:
            return

        if not self._config.bucket:
            logger.warning(
                "No S3 bucket configured. DataFramePersistence will operate in degraded mode."
            )
            self._degraded = True
            return

        if not self._config.enabled:
            logger.info("DataFrame persistence is disabled.")
            self._degraded = True
            return

        try:
            client_kwargs: dict[str, Any] = {
                "region_name": self._config.region,
            }
            if self._config.endpoint_url:
                client_kwargs["endpoint_url"] = self._config.endpoint_url

            self._client = self._boto3_module.client("s3", **client_kwargs)
            self._degraded = False
            logger.debug(
                "DataFramePersistence initialized with bucket=%s prefix=%s",
                self._config.bucket,
                self._config.prefix,
            )
        except Exception as e:
            logger.error("Failed to initialize S3 client for persistence: %s", e)
            self._degraded = True

    def _get_client(self) -> Any:
        """Get S3 client, attempting reconnection if in degraded mode.

        Returns:
            boto3 S3 client instance.

        Raises:
            RuntimeError: If boto3 is not available or client cannot be created.
        """
        if self._boto3_module is None:
            raise RuntimeError("boto3 package not installed")

        if self._degraded:
            self._attempt_reconnect()

        if self._client is None:
            raise RuntimeError("S3 client not initialized for persistence")

        return self._client

    def _attempt_reconnect(self) -> None:
        """Attempt to reconnect to S3 if in degraded mode."""
        now = time.time()
        if now - self._last_reconnect_attempt < self._reconnect_interval:
            return

        with self._client_lock:
            self._last_reconnect_attempt = now
            try:
                self._initialize_client()
                if self._client is not None:
                    # Test connectivity with a simple HEAD bucket
                    self._client.head_bucket(Bucket=self._config.bucket)
                    self._degraded = False
                    logger.info("S3 persistence connection restored")
            except Exception as e:
                logger.warning("S3 persistence reconnect failed: %s", e)

    def _make_dataframe_key(self, project_gid: str) -> str:
        """Generate S3 object key for DataFrame.

        Args:
            project_gid: Asana project GID.

        Returns:
            Full S3 object key for the DataFrame file.
        """
        return f"{self._config.prefix}{project_gid}/dataframe.parquet"

    def _make_watermark_key(self, project_gid: str) -> str:
        """Generate S3 object key for watermark.

        Args:
            project_gid: Asana project GID.

        Returns:
            Full S3 object key for the watermark file.
        """
        return f"{self._config.prefix}{project_gid}/watermark.json"

    def _make_index_key(self, project_gid: str) -> str:
        """Generate S3 object key for GidLookupIndex.

        Args:
            project_gid: Asana project GID.

        Returns:
            Full S3 object key for the index file.
        """
        return f"{self._config.prefix}{project_gid}/gid_lookup_index.json"

    @property
    def is_available(self) -> bool:
        """Check if persistence is available and healthy.

        Returns:
            True if S3 is healthy and bucket is accessible.
        """
        if self._degraded or self._boto3_module is None or self._polars_module is None:
            return False

        if not self._config.enabled:
            return False

        try:
            client = self._get_client()
            client.head_bucket(Bucket=self._config.bucket)
            return True
        except Exception:
            return False

    async def save_dataframe(
        self,
        project_gid: str,
        df: "pl.DataFrame",
        watermark: datetime,
    ) -> bool:
        """Persist DataFrame and associated watermark to S3.

        Stores the DataFrame in Parquet format for efficient storage and
        fast columnar reads. The watermark is stored as a separate JSON
        file for quick metadata access without loading the full DataFrame.

        Args:
            project_gid: Asana project GID.
            df: Polars DataFrame to persist.
            watermark: Watermark timestamp (must be timezone-aware).

        Returns:
            True if saved successfully, False on error.

        Raises:
            ValueError: If watermark is not timezone-aware.

        Example:
            >>> df = pl.DataFrame({"gid": ["123"], "name": ["Task"]})
            >>> success = await persistence.save_dataframe(
            ...     "proj_123",
            ...     df,
            ...     datetime.now(timezone.utc)
            ... )
        """
        if watermark.tzinfo is None:
            raise ValueError("Watermark timestamp must be timezone-aware")

        if self._degraded:
            logger.debug("Persistence unavailable, skipping save for %s", project_gid)
            return False

        if self._polars_module is None:
            logger.warning("polars not available, cannot save DataFrame")
            return False

        try:
            client = self._get_client()

            # Serialize DataFrame to Parquet bytes
            buffer = io.BytesIO()
            df.write_parquet(buffer)
            buffer.seek(0)
            parquet_bytes = buffer.read()

            # Save DataFrame
            df_key = self._make_dataframe_key(project_gid)
            client.put_object(
                Bucket=self._config.bucket,
                Key=df_key,
                Body=parquet_bytes,
                ContentType="application/octet-stream",
                Metadata={
                    "project-gid": project_gid,
                    "row-count": str(len(df)),
                    "watermark": watermark.isoformat(),
                },
            )

            # Save watermark as separate JSON for fast access
            watermark_data = {
                "project_gid": project_gid,
                "watermark": watermark.isoformat(),
                "row_count": len(df),
                "columns": df.columns,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            wm_key = self._make_watermark_key(project_gid)
            client.put_object(
                Bucket=self._config.bucket,
                Key=wm_key,
                Body=json.dumps(watermark_data).encode("utf-8"),
                ContentType="application/json",
            )

            logger.info(
                "Persisted DataFrame for project %s: %d rows, watermark=%s",
                project_gid,
                len(df),
                watermark.isoformat(),
            )
            return True

        except Exception as e:
            self._handle_s3_error(e, "save", project_gid)
            return False

    async def load_dataframe(
        self,
        project_gid: str,
    ) -> tuple["pl.DataFrame | None", datetime | None]:
        """Load DataFrame and watermark from S3.

        Retrieves a previously persisted DataFrame and its associated watermark.
        Returns (None, None) gracefully if the objects don't exist.

        Args:
            project_gid: Asana project GID.

        Returns:
            Tuple of (DataFrame, watermark) if found, (None, None) if not found
            or on error.

        Example:
            >>> df, watermark = await persistence.load_dataframe("proj_123")
            >>> if df is not None:
            ...     print(f"Loaded {len(df)} rows from watermark {watermark}")
            ... else:
            ...     print("No persisted state, doing full fetch")
        """
        if self._degraded:
            logger.debug("Persistence unavailable, skipping load for %s", project_gid)
            return None, None

        if self._polars_module is None:
            logger.warning("polars not available, cannot load DataFrame")
            return None, None

        try:
            client = self._get_client()
            pl = self._polars_module

            # Load watermark first (fast, tells us if data exists)
            wm_key = self._make_watermark_key(project_gid)
            try:
                wm_response = client.get_object(
                    Bucket=self._config.bucket,
                    Key=wm_key,
                )
                wm_body = wm_response["Body"].read()
                wm_data = json.loads(wm_body.decode("utf-8"))
                watermark = datetime.fromisoformat(wm_data["watermark"])
            except Exception as e:
                if self._is_not_found_error(e):
                    logger.debug("No persisted watermark for project %s", project_gid)
                    return None, None
                raise

            # Load DataFrame
            df_key = self._make_dataframe_key(project_gid)
            try:
                df_response = client.get_object(
                    Bucket=self._config.bucket,
                    Key=df_key,
                )
                df_body = df_response["Body"].read()
                buffer = io.BytesIO(df_body)
                df = pl.read_parquet(buffer)
            except Exception as e:
                if self._is_not_found_error(e):
                    logger.warning(
                        "Watermark exists but DataFrame missing for project %s",
                        project_gid,
                    )
                    return None, None
                raise

            logger.info(
                "Loaded persisted DataFrame for project %s: %d rows, watermark=%s",
                project_gid,
                len(df),
                watermark.isoformat(),
            )
            return df, watermark

        except Exception as e:
            self._handle_s3_error(e, "load", project_gid)
            return None, None

    async def delete_dataframe(self, project_gid: str) -> bool:
        """Remove persisted DataFrame from S3.

        Deletes both the DataFrame and watermark files for a project.
        Returns True even if files don't exist (idempotent operation).

        Args:
            project_gid: Asana project GID.

        Returns:
            True if deleted successfully or files don't exist, False on error.

        Example:
            >>> success = await persistence.delete_dataframe("proj_123")
        """
        if self._degraded:
            logger.debug("Persistence unavailable, skipping delete for %s", project_gid)
            return False

        try:
            client = self._get_client()

            # Delete both files (ignore if not found)
            df_key = self._make_dataframe_key(project_gid)
            wm_key = self._make_watermark_key(project_gid)

            for key in [df_key, wm_key]:
                try:
                    client.delete_object(
                        Bucket=self._config.bucket,
                        Key=key,
                    )
                except Exception as e:
                    if not self._is_not_found_error(e):
                        raise

            logger.info("Deleted persisted DataFrame for project %s", project_gid)
            return True

        except Exception as e:
            self._handle_s3_error(e, "delete", project_gid)
            return False

    async def get_watermark_only(self, project_gid: str) -> datetime | None:
        """Get watermark without loading the full DataFrame.

        Useful for quick staleness checks without the overhead of
        loading the entire DataFrame.

        Args:
            project_gid: Asana project GID.

        Returns:
            Watermark datetime if found, None otherwise.

        Example:
            >>> wm = await persistence.get_watermark_only("proj_123")
            >>> if wm is not None and wm > some_threshold:
            ...     # Use persisted data
            ...     pass
        """
        if self._degraded:
            return None

        try:
            client = self._get_client()

            wm_key = self._make_watermark_key(project_gid)
            response = client.get_object(
                Bucket=self._config.bucket,
                Key=wm_key,
            )
            body = response["Body"].read()
            data = json.loads(body.decode("utf-8"))
            return datetime.fromisoformat(data["watermark"])

        except Exception as e:
            if self._is_not_found_error(e):
                return None
            self._handle_s3_error(e, "get_watermark", project_gid)
            return None

    async def list_persisted_projects(self) -> list[str]:
        """List all projects with persisted DataFrames.

        Scans the S3 prefix to find all projects that have persisted data.

        Returns:
            List of project GIDs with persisted DataFrames.

        Example:
            >>> projects = await persistence.list_persisted_projects()
            >>> print(f"Found {len(projects)} persisted projects")
        """
        if self._degraded:
            return []

        try:
            client = self._get_client()

            # List objects under the prefix
            paginator = client.get_paginator("list_objects_v2")
            projects: set[str] = set()

            for page in paginator.paginate(
                Bucket=self._config.bucket,
                Prefix=self._config.prefix,
                Delimiter="/",
            ):
                # Common prefixes are directories (project_gid/)
                for prefix_info in page.get("CommonPrefixes", []):
                    prefix = prefix_info.get("Prefix", "")
                    # Extract project GID from prefix like "dataframes/proj_123/"
                    if prefix.startswith(self._config.prefix):
                        remaining = prefix[len(self._config.prefix) :]
                        project_gid = remaining.rstrip("/")
                        if project_gid:
                            projects.add(project_gid)

            return sorted(projects)

        except Exception as e:
            self._handle_s3_error(e, "list", "all")
            return []

    def _is_not_found_error(self, error: Exception) -> bool:
        """Check if an exception indicates object not found.

        Args:
            error: The exception to check.

        Returns:
            True if error indicates object not found (404/NoSuchKey).
        """
        if self._botocore_module is None:
            return False

        client_error = getattr(self._botocore_module, "ClientError", Exception)
        if isinstance(error, client_error):
            error_code = error.response.get("Error", {}).get("Code", "")  # type: ignore[attr-defined]
            return error_code in ("NoSuchKey", "404", "NotFound")

        return False

    def _handle_s3_error(
        self, error: Exception, operation: str, project_gid: str
    ) -> None:
        """Handle S3 errors and potentially enter degraded mode.

        Args:
            error: The exception that occurred.
            operation: Name of the operation (save, load, delete).
            project_gid: Project GID involved.
        """
        error_types: tuple[type[Exception], ...] = (
            ConnectionError,
            TimeoutError,
            OSError,
        )

        # Check for boto3-specific errors
        if self._botocore_module is not None:
            no_credentials = getattr(
                self._botocore_module, "NoCredentialsError", Exception
            )
            partial_credentials = getattr(
                self._botocore_module, "PartialCredentialsError", Exception
            )
            endpoint_error = getattr(
                self._botocore_module, "EndpointConnectionError", Exception
            )
            connect_timeout = getattr(
                self._botocore_module, "ConnectTimeoutError", Exception
            )
            read_timeout = getattr(self._botocore_module, "ReadTimeoutError", Exception)

            error_types = error_types + (
                no_credentials,
                partial_credentials,
                endpoint_error,
                connect_timeout,
                read_timeout,
            )

            # ClientError needs special handling
            client_error = getattr(self._botocore_module, "ClientError", Exception)
            if isinstance(error, client_error):
                error_code = error.response.get("Error", {}).get("Code", "")  # type: ignore[attr-defined]
                # Access denied or bucket not found are serious
                if error_code in ("AccessDenied", "NoSuchBucket"):
                    if not self._degraded:
                        logger.warning(
                            "S3 persistence access error during %s for %s, entering degraded mode: %s",
                            operation,
                            project_gid,
                            error,
                        )
                        self._degraded = True
                    return

        if isinstance(error, error_types):
            if not self._degraded:
                logger.warning(
                    "S3 persistence error during %s for %s, entering degraded mode: %s",
                    operation,
                    project_gid,
                    error,
                )
                self._degraded = True
        else:
            logger.error(
                "S3 persistence error during %s for %s: %s",
                operation,
                project_gid,
                error,
            )

    async def save_watermark(self, project_gid: str, watermark: datetime) -> bool:
        """Persist a single watermark to S3.

        This is a lightweight operation that only writes the watermark JSON file,
        suitable for write-through caching from WatermarkRepository.set_watermark().

        Args:
            project_gid: Asana project GID.
            watermark: Watermark timestamp (must be timezone-aware).

        Returns:
            True if saved successfully, False on error.

        Raises:
            ValueError: If watermark is not timezone-aware.

        Example:
            >>> success = await persistence.save_watermark(
            ...     "proj_123",
            ...     datetime.now(timezone.utc)
            ... )
        """
        if watermark.tzinfo is None:
            raise ValueError("Watermark timestamp must be timezone-aware")

        if self._degraded:
            logger.debug(
                "Persistence unavailable, skipping watermark save for %s", project_gid
            )
            return False

        try:
            client = self._get_client()

            watermark_data = {
                "project_gid": project_gid,
                "watermark": watermark.isoformat(),
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            wm_key = self._make_watermark_key(project_gid)
            client.put_object(
                Bucket=self._config.bucket,
                Key=wm_key,
                Body=json.dumps(watermark_data).encode("utf-8"),
                ContentType="application/json",
            )

            logger.debug(
                "Persisted watermark for project %s: %s",
                project_gid,
                watermark.isoformat(),
            )
            return True

        except Exception as e:
            self._handle_s3_error(e, "save_watermark", project_gid)
            return False

    async def load_all_watermarks(self) -> dict[str, datetime]:
        """Load all persisted watermarks from S3.

        Efficient bulk load that retrieves all watermark JSON files from S3.
        Used during startup to hydrate WatermarkRepository before loading DataFrames.

        Returns:
            Dict mapping project_gid to watermark datetime.
            Returns empty dict on error or when degraded.

        Example:
            >>> watermarks = await persistence.load_all_watermarks()
            >>> for project_gid, wm in watermarks.items():
            ...     print(f"{project_gid}: {wm.isoformat()}")
        """
        if self._degraded:
            logger.debug("Persistence unavailable, skipping load_all_watermarks")
            return {}

        try:
            # First get list of projects with persisted data
            project_gids = await self.list_persisted_projects()

            if not project_gids:
                return {}

            watermarks: dict[str, datetime] = {}

            for project_gid in project_gids:
                try:
                    wm = await self.get_watermark_only(project_gid)
                    if wm is not None:
                        watermarks[project_gid] = wm
                except Exception as e:
                    # Log but continue with other projects
                    logger.warning(
                        "Failed to load watermark for project %s: %s",
                        project_gid,
                        e,
                    )

            logger.info(
                "Loaded %d watermarks from S3",
                len(watermarks),
            )
            return watermarks

        except Exception as e:
            self._handle_s3_error(e, "load_all_watermarks", "all")
            return {}

    async def save_index(
        self,
        project_gid: str,
        index: "GidLookupIndex",
    ) -> bool:
        """Persist GidLookupIndex to S3 as JSON.

        Stores the index in JSON format for efficient serialization and
        human-readability. The index can be loaded on container restart
        without needing to rebuild from the DataFrame.

        Args:
            project_gid: Asana project GID.
            index: GidLookupIndex instance to persist.

        Returns:
            True if saved successfully, False on error.

        Example:
            >>> index = GidLookupIndex.from_dataframe(df)
            >>> success = await persistence.save_index("proj_123", index)
        """
        if self._degraded:
            logger.debug(
                "Persistence unavailable, skipping index save for %s", project_gid
            )
            return False

        try:
            client = self._get_client()

            # Serialize index to JSON
            index_data = index.serialize()
            json_bytes = json.dumps(index_data).encode("utf-8")

            # Save to S3
            key = self._make_index_key(project_gid)
            client.put_object(
                Bucket=self._config.bucket,
                Key=key,
                Body=json_bytes,
                ContentType="application/json",
                Metadata={
                    "project-gid": project_gid,
                    "entry-count": str(len(index)),
                    "created-at": index.created_at.isoformat(),
                },
            )

            logger.info(
                "Persisted GidLookupIndex for project %s: %d entries",
                project_gid,
                len(index),
            )
            return True

        except Exception as e:
            self._handle_s3_error(e, "save_index", project_gid)
            return False

    async def load_index(
        self,
        project_gid: str,
    ) -> "GidLookupIndex | None":
        """Load GidLookupIndex from S3.

        Retrieves a previously persisted GidLookupIndex. Returns None
        gracefully if the index doesn't exist or on error.

        Args:
            project_gid: Asana project GID.

        Returns:
            Reconstructed GidLookupIndex if found, None if not found or on error.

        Example:
            >>> index = await persistence.load_index("proj_123")
            >>> if index is not None:
            ...     print(f"Loaded index with {len(index)} entries")
            ... else:
            ...     print("No persisted index, building from DataFrame")
        """
        if self._degraded:
            logger.debug(
                "Persistence unavailable, skipping index load for %s", project_gid
            )
            return None

        try:
            client = self._get_client()

            key = self._make_index_key(project_gid)
            try:
                response = client.get_object(
                    Bucket=self._config.bucket,
                    Key=key,
                )
                body = response["Body"].read()
                data = json.loads(body.decode("utf-8"))
            except Exception as e:
                if self._is_not_found_error(e):
                    logger.debug("No persisted index for project %s", project_gid)
                    return None
                raise

            # Import and deserialize
            from autom8_asana.services.gid_lookup import GidLookupIndex

            index = GidLookupIndex.deserialize(data)

            logger.info(
                "Loaded persisted GidLookupIndex for project %s: %d entries",
                project_gid,
                len(index),
            )
            return index

        except Exception as e:
            self._handle_s3_error(e, "load_index", project_gid)
            return None

    async def delete_index(self, project_gid: str) -> bool:
        """Remove persisted GidLookupIndex from S3.

        Deletes the index file for a project. Returns True even if the
        file doesn't exist (idempotent operation).

        Args:
            project_gid: Asana project GID.

        Returns:
            True if deleted successfully or file doesn't exist, False on error.

        Example:
            >>> success = await persistence.delete_index("proj_123")
        """
        if self._degraded:
            logger.debug(
                "Persistence unavailable, skipping index delete for %s", project_gid
            )
            return False

        try:
            client = self._get_client()

            key = self._make_index_key(project_gid)
            try:
                client.delete_object(
                    Bucket=self._config.bucket,
                    Key=key,
                )
            except Exception as e:
                if not self._is_not_found_error(e):
                    raise

            logger.info("Deleted persisted GidLookupIndex for project %s", project_gid)
            return True

        except Exception as e:
            self._handle_s3_error(e, "delete_index", project_gid)
            return False
