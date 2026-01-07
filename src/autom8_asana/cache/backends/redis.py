"""Redis cache provider with versioning support."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from types import ModuleType
from typing import Any, cast

from autom8y_log import get_logger

from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.freshness import Freshness
from autom8_asana.cache.metrics import CacheMetrics
from autom8_asana.cache.settings import CacheSettings
from autom8_asana.cache.versioning import format_version, is_current, parse_version
from autom8_asana.protocols.cache import WarmResult

logger = get_logger(__name__)


@dataclass
class RedisConfig:
    """Redis connection configuration.

    Attributes:
        host: Redis host address.
        port: Redis port number.
        db: Redis database number.
        password: Optional authentication password.
        ssl: Enable TLS/SSL connection.
        ssl_cert_reqs: SSL certificate requirements ("required", "optional", "none").
        socket_timeout: Operation timeout in seconds.
        socket_connect_timeout: Connection timeout in seconds.
        max_connections: Maximum connections in pool.
        retry_on_timeout: Whether to retry on timeout.
        health_check_interval: Seconds between health checks.
        decode_responses: Whether to decode responses to strings.
    """

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    ssl: bool = False
    ssl_cert_reqs: str = "required"
    socket_timeout: float = 1.0
    socket_connect_timeout: float = 5.0
    max_connections: int = 10
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    decode_responses: bool = True


class RedisCacheProvider:
    """Redis-based cache provider with versioning support.

    Implements the CacheProvider protocol using Redis as the backend.
    Supports versioned entries, batch operations, and thread-safe
    access through connection pooling.

    Key Structure:
        asana:tasks:{gid}:{entry_type}     - JSON data
        asana:struc:{task_gid}:{project}   - JSON struc data
        asana:tasks:{gid}:_meta            - Redis HASH with versions

    Thread Safety:
        Uses connection pooling with per-operation connections.
        Atomic updates use WATCH/MULTI pattern (ADR-0024).

    Example:
        >>> from autom8_asana.cache.backends import RedisCacheProvider
        >>> cache = RedisCacheProvider(
        ...     config=RedisConfig(host="localhost", port=6379)
        ... )
        >>> cache.is_healthy()
        True
    """

    # Key prefixes following ADR-0017 structure
    TASK_PREFIX = "asana:tasks"
    STRUC_PREFIX = "asana:struc"
    CONFIG_PREFIX = "asana:config"
    META_SUFFIX = "_meta"

    def __init__(
        self,
        config: RedisConfig | None = None,
        settings: CacheSettings | None = None,
        *,
        host: str = "localhost",
        port: int = 6379,
        password: str | None = None,
        ssl: bool = False,
        db: int = 0,
    ) -> None:
        """Initialize Redis cache provider.

        Can be initialized with a RedisConfig or individual parameters.

        Args:
            config: Redis configuration object (preferred).
            settings: Cache settings for TTL and overflow thresholds.
            host: Redis host (if config not provided).
            port: Redis port (if config not provided).
            password: Redis password (if config not provided).
            ssl: Enable SSL (if config not provided).
            db: Redis database number (if config not provided).
        """
        if config is None:
            config = RedisConfig(
                host=host,
                port=port,
                password=password,
                ssl=ssl,
                db=db,
            )

        self._config = config
        self._settings = settings or CacheSettings()
        self._metrics = CacheMetrics()
        self._pool: Any = None
        self._pool_lock = Lock()
        self._degraded = False
        self._last_reconnect_attempt = 0.0
        self._redis_module: ModuleType | None = None

        # Import redis here to make it optional dependency
        try:
            import redis

            self._redis_module = redis
            self._initialize_pool()
        except ImportError:
            logger.warning(
                "redis package not installed. RedisCacheProvider will operate in degraded mode."
            )
            self._degraded = True

    def _initialize_pool(self) -> None:
        """Initialize Redis connection pool."""
        if self._redis_module is None:
            return

        try:
            self._pool = self._redis_module.ConnectionPool(
                host=self._config.host,
                port=self._config.port,
                db=self._config.db,
                password=self._config.password,
                socket_timeout=self._config.socket_timeout,
                socket_connect_timeout=self._config.socket_connect_timeout,
                max_connections=self._config.max_connections,
                retry_on_timeout=self._config.retry_on_timeout,
                decode_responses=self._config.decode_responses,
                # SSL configuration
                ssl=self._config.ssl,
                ssl_cert_reqs=self._config.ssl_cert_reqs if self._config.ssl else None,
            )
            self._degraded = False
        except Exception as e:
            logger.error(f"Failed to initialize Redis pool: {e}")
            self._degraded = True

    def _get_connection(self) -> Any:
        """Get a Redis connection from the pool.

        Returns:
            Redis client instance.

        Raises:
            RuntimeError: If Redis is not available.
        """
        if self._redis_module is None:
            raise RuntimeError("Redis package not installed")

        if self._degraded:
            self._attempt_reconnect()

        if self._pool is None:
            raise RuntimeError("Redis connection pool not initialized")

        return self._redis_module.Redis(connection_pool=self._pool)

    def _attempt_reconnect(self) -> None:
        """Attempt to reconnect to Redis if in degraded mode."""
        now = time.time()
        if now - self._last_reconnect_attempt < self._settings.reconnect_interval:
            return

        with self._pool_lock:
            self._last_reconnect_attempt = now
            try:
                self._initialize_pool()
                if self._pool is not None and self._redis_module is not None:
                    redis_cls = getattr(self._redis_module, "Redis")
                    conn = redis_cls(connection_pool=self._pool)
                    conn.ping()
                    self._degraded = False
                    logger.info("Redis connection restored")
            except Exception as e:
                logger.warning(f"Redis reconnect failed: {e}")

    def _make_key(self, key: str, entry_type: EntryType) -> str:
        """Generate Redis key for a cache entry.

        Args:
            key: Cache key (task GID).
            entry_type: Type of entry.

        Returns:
            Full Redis key string.
        """
        if entry_type == EntryType.DATAFRAME:
            # Dataframe keys include project GID which should be in key
            return f"{self.STRUC_PREFIX}:{key}"
        return f"{self.TASK_PREFIX}:{key}:{entry_type.value}"

    def _make_meta_key(self, key: str) -> str:
        """Generate Redis key for metadata hash.

        Args:
            key: Cache key (task GID).

        Returns:
            Full Redis key for metadata hash.
        """
        return f"{self.TASK_PREFIX}:{key}:{self.META_SUFFIX}"

    def _serialize_entry(self, entry: CacheEntry) -> dict[str, str]:
        """Serialize CacheEntry for Redis storage.

        Args:
            entry: Cache entry to serialize.

        Returns:
            Dict suitable for Redis HSET.
        """
        return {
            "data": json.dumps(entry.data),
            "entry_type": entry.entry_type.value,
            "version": format_version(entry.version),
            "cached_at": format_version(entry.cached_at),
            "ttl": str(entry.ttl) if entry.ttl is not None else "",
            "project_gid": entry.project_gid or "",
            "metadata": json.dumps(entry.metadata),
            "key": entry.key,
        }

    def _deserialize_entry(self, data: dict[str, str], key: str) -> CacheEntry | None:
        """Deserialize Redis data to CacheEntry.

        Args:
            data: Dict from Redis HGETALL.
            key: Cache key.

        Returns:
            CacheEntry or None if data is invalid.
        """
        if not data:
            return None

        try:
            entry_data = json.loads(data.get("data", "{}"))
            entry_type_str = data.get("entry_type", "task")
            version_str = data.get("version", "")
            cached_at_str = data.get("cached_at", "")
            ttl_str = data.get("ttl", "")
            project_gid = data.get("project_gid", "") or None
            metadata_str = data.get("metadata", "{}")

            entry_type = EntryType(entry_type_str)
            version = (
                parse_version(version_str)
                if version_str
                else datetime.now(timezone.utc)
            )
            cached_at = (
                parse_version(cached_at_str)
                if cached_at_str
                else datetime.now(timezone.utc)
            )
            ttl = int(ttl_str) if ttl_str else None
            metadata = json.loads(metadata_str) if metadata_str else {}

            return CacheEntry(
                key=key,
                data=entry_data,
                entry_type=entry_type,
                version=version,
                cached_at=cached_at,
                ttl=ttl,
                project_gid=project_gid,
                metadata=metadata,
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to deserialize cache entry for {key}: {e}")
            return None

    # === Original methods (backward compatible) ===

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve value from cache (simple key-value).

        Args:
            key: Cache key.

        Returns:
            Cached dict if found, None if miss.
        """
        start = time.perf_counter()
        try:
            if self._degraded:
                self._metrics.record_miss(0.0, key=key)
                return None

            conn = self._get_connection()
            try:
                data = conn.get(key)
                latency = (time.perf_counter() - start) * 1000

                if data is None:
                    self._metrics.record_miss(latency, key=key)
                    return None

                self._metrics.record_hit(latency, key=key)
                if isinstance(data, str):
                    return cast(dict[str, Any], json.loads(data))
                return cast(dict[str, Any], json.loads(data.decode("utf-8")))
            finally:
                conn.close()
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            self._metrics.record_error(key=key, error_message=str(e))
            self._handle_redis_error(e)
            return None

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Store value in cache (simple key-value).

        Args:
            key: Cache key.
            value: Dict to cache.
            ttl: Time-to-live in seconds, None for no expiration.
        """
        start = time.perf_counter()
        try:
            if self._degraded:
                return

            conn = self._get_connection()
            try:
                serialized = json.dumps(value)
                if ttl is not None:
                    conn.setex(key, ttl, serialized)
                else:
                    conn.set(key, serialized)

                latency = (time.perf_counter() - start) * 1000
                self._metrics.record_write(latency, key=key)
            finally:
                conn.close()
        except Exception as e:
            self._metrics.record_error(key=key, error_message=str(e))
            self._handle_redis_error(e)

    def delete(self, key: str) -> None:
        """Remove value from cache.

        Args:
            key: Cache key to delete.
        """
        try:
            if self._degraded:
                return

            conn = self._get_connection()
            try:
                conn.delete(key)
                self._metrics.record_eviction(key=key)
            finally:
                conn.close()
        except Exception as e:
            self._metrics.record_error(key=key, error_message=str(e))
            self._handle_redis_error(e)

    # === New versioned methods ===

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: Freshness | None = None,
    ) -> CacheEntry | None:
        """Retrieve versioned cache entry with freshness control.

        Args:
            key: Cache key (task GID).
            entry_type: Type of entry for version resolution.
            freshness: STRICT validates version, EVENTUAL returns without check.

        Returns:
            CacheEntry if found and not expired, None otherwise.
        """
        if freshness is None:
            freshness = Freshness.EVENTUAL

        start = time.perf_counter()
        entry_type_str = entry_type.value

        try:
            if self._degraded:
                self._metrics.record_miss(0.0, key=key, entry_type=entry_type_str)
                return None

            conn = self._get_connection()
            try:
                redis_key = self._make_key(key, entry_type)
                data = conn.hgetall(redis_key)
                latency = (time.perf_counter() - start) * 1000

                if not data:
                    self._metrics.record_miss(
                        latency, key=key, entry_type=entry_type_str
                    )
                    return None

                entry = self._deserialize_entry(data, key)
                if entry is None:
                    self._metrics.record_miss(
                        latency, key=key, entry_type=entry_type_str
                    )
                    return None

                # Check TTL expiration
                if entry.is_expired():
                    # Delete expired entry
                    conn.delete(redis_key)
                    self._metrics.record_miss(
                        latency, key=key, entry_type=entry_type_str
                    )
                    return None

                # For STRICT freshness, caller must validate against source
                # This is documented behavior - strict validation requires API call
                self._metrics.record_hit(latency, key=key, entry_type=entry_type_str)
                return entry
            finally:
                conn.close()
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            self._metrics.record_error(
                key=key, entry_type=entry_type_str, error_message=str(e)
            )
            self._handle_redis_error(e)
            return None

    def set_versioned(
        self,
        key: str,
        entry: CacheEntry,
    ) -> None:
        """Store versioned cache entry.

        Uses Redis HSET for structured storage and EXPIRE for TTL.

        Args:
            key: Cache key.
            entry: CacheEntry with data and metadata.
        """
        start = time.perf_counter()
        entry_type_str = entry.entry_type.value

        try:
            if self._degraded:
                return

            conn = self._get_connection()
            try:
                redis_key = self._make_key(key, entry.entry_type)
                serialized = self._serialize_entry(entry)

                # Use pipeline for atomic HSET + EXPIRE
                pipe = conn.pipeline()
                pipe.hset(redis_key, mapping=serialized)
                if entry.ttl is not None:
                    pipe.expire(redis_key, entry.ttl)
                pipe.execute()

                # Update version in metadata hash
                meta_key = self._make_meta_key(key)
                conn.hset(meta_key, entry_type_str, format_version(entry.version))
                if entry.ttl is not None:
                    conn.expire(meta_key, entry.ttl)

                latency = (time.perf_counter() - start) * 1000
                self._metrics.record_write(latency, key=key, entry_type=entry_type_str)
            finally:
                conn.close()
        except Exception as e:
            self._metrics.record_error(
                key=key, entry_type=entry_type_str, error_message=str(e)
            )
            self._handle_redis_error(e)

    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]:
        """Retrieve multiple entries in single operation.

        Uses pipelined HGETALL for efficiency.

        Args:
            keys: List of cache keys.
            entry_type: Type of entries to retrieve.

        Returns:
            Dict mapping keys to CacheEntry or None if not found.
        """
        result: dict[str, CacheEntry | None] = {}
        if not keys:
            return result

        try:
            if self._degraded:
                return {key: None for key in keys}

            conn = self._get_connection()
            try:
                pipe = conn.pipeline()
                redis_keys = [self._make_key(key, entry_type) for key in keys]

                for redis_key in redis_keys:
                    pipe.hgetall(redis_key)

                responses = pipe.execute()

                for key, data in zip(keys, responses):
                    if data:
                        entry = self._deserialize_entry(data, key)
                        if entry is not None and not entry.is_expired():
                            result[key] = entry
                        else:
                            result[key] = None
                    else:
                        result[key] = None

                return result
            finally:
                conn.close()
        except Exception as e:
            self._metrics.record_error(error_message=str(e))
            self._handle_redis_error(e)
            return {key: None for key in keys}

    def set_batch(
        self,
        entries: dict[str, CacheEntry],
    ) -> None:
        """Store multiple entries in single operation.

        Uses pipelined operations for efficiency.

        Args:
            entries: Dict mapping keys to CacheEntry objects.
        """
        if not entries:
            return

        try:
            if self._degraded:
                return

            conn = self._get_connection()
            try:
                pipe = conn.pipeline()

                for key, entry in entries.items():
                    redis_key = self._make_key(key, entry.entry_type)
                    serialized = self._serialize_entry(entry)
                    pipe.hset(redis_key, mapping=serialized)
                    if entry.ttl is not None:
                        pipe.expire(redis_key, entry.ttl)

                    # Update metadata
                    meta_key = self._make_meta_key(key)
                    pipe.hset(
                        meta_key, entry.entry_type.value, format_version(entry.version)
                    )

                pipe.execute()
            finally:
                conn.close()
        except Exception as e:
            self._metrics.record_error(error_message=str(e))
            self._handle_redis_error(e)

    def warm(
        self,
        gids: list[str],
        entry_types: list[EntryType] | None = None,
    ) -> WarmResult:
        """Pre-populate cache for specified GIDs and entry types.

        Note: Actual warming requires API calls which are out of scope
        for Phase 1. This method returns a placeholder result.

        Args:
            gids: List of task GIDs to warm.
            entry_types: Entry types to fetch and cache.

        Returns:
            WarmResult with success/failure counts.
        """
        # Phase 1: Warming requires integration with TasksClient
        # which is out of scope. Return placeholder.
        logger.info(f"Cache warm requested for {len(gids)} GIDs (not yet implemented)")
        return WarmResult(warmed=0, failed=0, skipped=len(gids))

    def check_freshness(
        self,
        key: str,
        entry_type: EntryType,
        current_version: datetime,
    ) -> bool:
        """Check if cached version matches current version.

        Args:
            key: Cache key.
            entry_type: Type of entry.
            current_version: Known current modified_at timestamp.

        Returns:
            True if cache is fresh, False if stale or missing.
        """
        try:
            if self._degraded:
                return False

            conn = self._get_connection()
            try:
                meta_key = self._make_meta_key(key)
                cached_version_str = conn.hget(meta_key, entry_type.value)

                if not cached_version_str:
                    return False

                cached_version = parse_version(cached_version_str)
                return is_current(cached_version, current_version)
            finally:
                conn.close()
        except Exception as e:
            self._handle_redis_error(e)
            return False

    def invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None:
        """Invalidate cache entries for a key.

        Args:
            key: Cache key (task GID).
            entry_types: Specific types to invalidate. If None, all types.
        """
        try:
            if self._degraded:
                return

            conn = self._get_connection()
            try:
                if entry_types is None:
                    entry_types = list(EntryType)

                pipe = conn.pipeline()
                for entry_type in entry_types:
                    redis_key = self._make_key(key, entry_type)
                    pipe.delete(redis_key)

                # Remove metadata entries
                meta_key = self._make_meta_key(key)
                for entry_type in entry_types:
                    pipe.hdel(meta_key, entry_type.value)

                pipe.execute()

                for entry_type in entry_types:
                    self._metrics.record_eviction(key=key, entry_type=entry_type.value)
            finally:
                conn.close()
        except Exception as e:
            self._metrics.record_error(key=key, error_message=str(e))
            self._handle_redis_error(e)

    def is_healthy(self) -> bool:
        """Check if cache backend is operational.

        Returns:
            True if Redis is healthy and responding to PING.
        """
        if self._degraded or self._redis_module is None:
            return False

        try:
            conn = self._get_connection()
            try:
                return bool(conn.ping())
            finally:
                conn.close()
        except Exception:
            return False

    def get_metrics(self) -> CacheMetrics:
        """Get cache metrics aggregator.

        Returns:
            CacheMetrics instance with hit/miss statistics.
        """
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset cache metrics to zero."""
        self._metrics.reset()

    def _handle_redis_error(self, error: Exception) -> None:
        """Handle Redis errors and potentially enter degraded mode.

        Args:
            error: The exception that occurred.
        """
        error_types: tuple[type[Exception], ...] = (
            ConnectionError,
            TimeoutError,
            OSError,
        )

        # Check for redis-specific errors
        if self._redis_module is not None:
            redis_connection_error = getattr(
                self._redis_module, "ConnectionError", Exception
            )
            redis_timeout_error = getattr(self._redis_module, "TimeoutError", Exception)
            redis_error = getattr(self._redis_module, "RedisError", Exception)
            error_types = error_types + (
                redis_connection_error,
                redis_timeout_error,
                redis_error,
            )

        if isinstance(error, error_types):
            if not self._degraded:
                logger.warning(f"Redis error, entering degraded mode: {error}")
                self._degraded = True
        else:
            logger.error(f"Redis error: {error}")

    def clear_all_tasks(self) -> int:
        """Clear all task entries from Redis cache.

        Uses SCAN to find all task keys and deletes them in batches.
        Used for cache invalidation when cached data becomes stale
        or corrupted (e.g., missing required fields like memberships).

        Returns:
            Count of keys deleted.
        """
        if self._degraded:
            logger.warning("clear_all_tasks called while in degraded mode")
            return 0

        try:
            conn = self._get_connection()
            try:
                pattern = f"{self.TASK_PREFIX}:*"
                deleted_count = 0
                cursor = 0

                # Use SCAN to iterate over all task keys
                while True:
                    cursor, keys = conn.scan(cursor=cursor, match=pattern, count=1000)

                    if keys:
                        # Delete keys in a pipeline for efficiency
                        pipe = conn.pipeline()
                        for key in keys:
                            pipe.delete(key)
                        results = pipe.execute()
                        deleted_count += sum(1 for r in results if r)

                    if cursor == 0:
                        break

                logger.info(
                    "redis_clear_all_tasks_complete",
                    extra={
                        "deleted_count": deleted_count,
                        "pattern": pattern,
                    },
                )

                return deleted_count

            finally:
                conn.close()

        except Exception as e:
            logger.error(
                "redis_clear_all_tasks_failed",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            self._handle_redis_error(e)
            return 0
