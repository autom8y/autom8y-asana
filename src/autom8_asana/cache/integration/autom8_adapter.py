"""Adapter for integrating autom8_asana SDK caching with legacy autom8.

This module provides helper functions to migrate from the legacy S3-based
cache to the new Redis-based intelligent caching layer.

Per ADR-0025: Big-bang cutover strategy with no S3 fallback.

Migration Process:
    1. Provision Redis (ElastiCache)
    2. Configure environment variables
    3. Deploy SDK with Redis cache
    4. Accept initial cache miss spike (100% at T+0)
    5. Cache warms naturally from API calls
    6. Use warm() API for high-traffic tasks

Usage in autom8:
    from autom8_asana.cache.autom8_adapter import (
        create_autom8_cache_provider,
        migrate_task_collection_loading,
        MigrationResult,
    )

    # Initialize Redis cache provider
    cache = create_autom8_cache_provider()

    # Use SDK caching in place of legacy S3 cache
    result = await migrate_task_collection_loading(
        task_dicts=task_dicts,
        cache=cache,
        batch_api=asana_batch_api,
        task_fetcher=fetch_tasks_from_api,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8_asana.cache.integration.batch import fetch_task_modifications
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.settings import CacheSettings
from autom8_asana.cache.policies.staleness import (
    check_batch_staleness,
    partition_by_staleness,
)
from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS
from autom8_asana.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from autom8_asana.cache.backends.redis import RedisCacheProvider


class MissingConfigurationError(Exception):
    """Raised when required configuration is missing."""

    pass


@dataclass(frozen=True)
class MigrationResult:
    """Result of task collection migration operation.

    Attributes:
        total_tasks: Total number of tasks processed.
        cache_hits: Number of tasks found fresh in cache.
        cache_misses: Number of tasks fetched from API.
        fetch_errors: Number of tasks that failed to fetch.
        tasks: The resulting task list (fresh + cached).
    """

    total_tasks: int
    cache_hits: int
    cache_misses: int
    fetch_errors: int
    tasks: list[dict[str, Any]] = field(default_factory=list)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as percentage (0-100)."""
        if self.total_tasks == 0:
            return 0.0
        return (self.cache_hits / self.total_tasks) * 100.0


def create_autom8_cache_provider(
    redis_host: str | None = None,
    redis_port: int | None = None,
    redis_password: str | None = None,
    redis_ssl: bool | None = None,
    redis_db: int = 0,
    settings: CacheSettings | None = None,
) -> RedisCacheProvider:
    """Create a RedisCacheProvider configured for autom8.

    Reads configuration from environment variables via Pydantic Settings
    if not provided explicitly:
    - REDIS_HOST (required)
    - REDIS_PORT (default: 6379)
    - REDIS_PASSWORD (optional)
    - REDIS_SSL (default: true)

    Args:
        redis_host: Redis host (or from REDIS_HOST env var).
        redis_port: Redis port (or from REDIS_PORT env var).
        redis_password: Redis password (or from REDIS_PASSWORD env var).
        redis_ssl: Enable TLS (or from REDIS_SSL env var).
        redis_db: Redis database number (default: 0).
        settings: Cache settings (or use defaults).

    Returns:
        Configured RedisCacheProvider.

    Raises:
        MissingConfigurationError: If REDIS_HOST is not provided.

    Example:
        >>> # Using environment variables
        >>> # export REDIS_HOST="your-redis-host.elasticache.amazonaws.com"
        >>> cache = create_autom8_cache_provider()

        >>> # Using explicit configuration
        >>> cache = create_autom8_cache_provider(
        ...     redis_host="localhost",
        ...     redis_port=6379,
        ...     redis_ssl=False,
        ... )
    """
    # Import here to make redis an optional dependency
    from autom8_asana.cache.backends.redis import RedisCacheProvider, RedisConfig

    # Get unified settings
    sdk_settings = get_settings()
    redis_settings = sdk_settings.redis

    # Resolve configuration: explicit params > settings from env
    host = redis_host or redis_settings.host
    if not host:
        raise MissingConfigurationError(
            "REDIS_HOST environment variable or redis_host parameter required. "
            "For AWS ElastiCache, use the primary endpoint hostname."
        )

    port = redis_port if redis_port is not None else redis_settings.port
    password = (
        redis_password
        if redis_password is not None
        else (
            redis_settings.password.get_secret_value()
            if redis_settings.password
            else None
        )
    )
    ssl = redis_ssl if redis_ssl is not None else redis_settings.ssl

    config = RedisConfig(
        host=host,
        port=port,
        password=password,
        ssl=ssl,
        db=redis_db,
        # Use Pydantic Settings for timeout configuration
        socket_timeout=redis_settings.socket_timeout,
        socket_connect_timeout=redis_settings.connect_timeout,
        max_connections=20,
        retry_on_timeout=True,
    )

    return RedisCacheProvider(
        config=config,
        settings=settings or CacheSettings(),
    )


async def migrate_task_collection_loading(
    task_dicts: list[dict[str, Any]],
    cache: RedisCacheProvider,
    batch_api: Callable[[list[str]], Awaitable[dict[str, str]]],
    task_fetcher: Callable[[list[str]], Awaitable[list[dict[str, Any]]]],
    ttl: int | None = 300,
) -> MigrationResult:
    """Migrate load_task_collection() to use SDK caching.

    This replaces the legacy S3-based staleness checking with
    the new Redis-based intelligent caching.

    Process:
    1. Extract GIDs from task_dicts
    2. Fetch current modified_at timestamps via batch API (with 25s TTL cache)
    3. Check staleness against cached versions
    4. Fetch stale tasks from API
    5. Update cache with fresh data
    6. Return merged task list

    Args:
        task_dicts: List of task dicts (may have modified_at or be empty).
            These are typically the tasks returned from a project query.
        cache: SDK cache provider (from create_autom8_cache_provider).
        batch_api: Async function to fetch modified_at via Asana batch API.
            Takes list of GIDs, returns dict mapping GID to modified_at.
        task_fetcher: Async function to fetch full task data for stale GIDs.
            Takes list of GIDs, returns list of task dicts.
        ttl: Cache TTL in seconds (default: 300 = 5 minutes).

    Returns:
        MigrationResult with task list and cache statistics.

    Example:
        >>> async def batch_api(gids: list[str]) -> dict[str, str]:
        ...     # Call Asana batch API to get modified_at timestamps
        ...     return {gid: "2025-01-01T00:00:00Z" for gid in gids}

        >>> async def task_fetcher(gids: list[str]) -> list[dict[str, Any]]:
        ...     # Fetch full task data from Asana API
        ...     return [{"gid": gid, "name": f"Task {gid}"} for gid in gids]

        >>> result = await migrate_task_collection_loading(
        ...     task_dicts=[{"gid": "123"}, {"gid": "456"}],
        ...     cache=cache,
        ...     batch_api=batch_api,
        ...     task_fetcher=task_fetcher,
        ... )
        >>> print(f"Hit rate: {result.hit_rate:.1f}%")
    """
    if not task_dicts:
        return MigrationResult(
            total_tasks=0,
            cache_hits=0,
            cache_misses=0,
            fetch_errors=0,
            tasks=[],
        )

    # Extract GIDs (filter out None/empty)
    gids = [t.get("gid") for t in task_dicts if t.get("gid")]
    if not gids:
        return MigrationResult(
            total_tasks=len(task_dicts),
            cache_hits=0,
            cache_misses=0,
            fetch_errors=0,
            tasks=task_dicts,
        )

    # Fetch current versions (uses 25s TTL cache internally per ADR-0018)
    # Filter out None values from gids for type safety
    valid_gids: list[str] = [g for g in gids if g is not None]
    current_versions = await fetch_task_modifications(
        gids=valid_gids,
        batch_api=batch_api,
    )

    # Check staleness against cache
    staleness = check_batch_staleness(
        cache=cache,
        task_gids=valid_gids,
        entry_type=EntryType.TASK,
        current_versions=current_versions,
    )

    # Partition into stale (need fetch) and current (use cache)
    stale_gids, current_gids = partition_by_staleness(staleness)

    cache_hits = len(current_gids)
    cache_misses = len(stale_gids)
    fetch_errors = 0

    # Get cached task data for current GIDs
    cached_entries = (
        cache.get_batch(current_gids, EntryType.TASK) if current_gids else {}
    )
    cached_tasks = {
        gid: entry.data for gid, entry in cached_entries.items() if entry is not None
    }

    # Fetch fresh data for stale tasks
    fresh_tasks_by_gid: dict[str, dict[str, Any]] = {}
    if stale_gids:
        try:
            fresh_tasks_list = await task_fetcher(stale_gids)

            # Cache fresh tasks
            for task in fresh_tasks_list:
                gid = task.get("gid")
                if not gid:
                    continue

                modified_at = task.get("modified_at")
                if modified_at:
                    if isinstance(modified_at, str):
                        version = _parse_version(modified_at)
                    else:
                        version = modified_at
                else:
                    version = datetime.now(UTC)

                entry = CacheEntry(
                    key=gid,
                    data=task,
                    entry_type=EntryType.TASK,
                    version=version,
                    cached_at=datetime.now(UTC),
                    ttl=ttl,
                )
                cache.set_versioned(gid, entry)
                fresh_tasks_by_gid[gid] = task

            # Track any GIDs that weren't returned by fetcher
            fetch_errors = len(stale_gids) - len(fresh_tasks_by_gid)

        except CACHE_TRANSIENT_ERRORS:
            # On fetch error, count all stale as errors
            fetch_errors = len(stale_gids)
            # Re-raise to let caller handle
            raise

    # Merge results: prefer fresh data, then cached, then original
    gid_to_original = {t.get("gid"): t for t in task_dicts if t.get("gid")}
    result_tasks = []

    for gid in gids:
        if gid in fresh_tasks_by_gid:
            result_tasks.append(fresh_tasks_by_gid[gid])
        elif gid in cached_tasks:
            result_tasks.append(cached_tasks[gid])
        elif gid in gid_to_original:
            result_tasks.append(gid_to_original[gid])

    return MigrationResult(
        total_tasks=len(gids),
        cache_hits=cache_hits,
        cache_misses=cache_misses,
        fetch_errors=fetch_errors,
        tasks=result_tasks,
    )


async def warm_project_tasks(
    cache: RedisCacheProvider,
    project_gid: str,
    task_fetcher: Callable[[str], Awaitable[list[dict[str, Any]]]],
    ttl: int | None = 300,
) -> int:
    """Pre-warm cache for all tasks in a project.

    Use this to reduce cache miss spike after deployment by
    warming high-traffic projects.

    Args:
        cache: SDK cache provider.
        project_gid: Project GID to warm.
        task_fetcher: Async function that takes project_gid and returns
            list of task dicts (with modified_at).
        ttl: Cache TTL in seconds.

    Returns:
        Number of tasks warmed.

    Example:
        >>> async def fetch_project_tasks(project_gid: str) -> list[dict]:
        ...     # Fetch all tasks from project via Asana API
        ...     return [...]

        >>> warmed = await warm_project_tasks(
        ...     cache=cache,
        ...     project_gid="123456789",
        ...     task_fetcher=fetch_project_tasks,
        ... )
        >>> print(f"Warmed {warmed} tasks")
    """
    tasks = await task_fetcher(project_gid)

    entries_to_cache: dict[str, CacheEntry] = {}
    now = datetime.now(UTC)

    for task in tasks:
        gid = task.get("gid")
        if not gid:
            continue

        modified_at = task.get("modified_at")
        if modified_at:
            version = (
                _parse_version(modified_at)
                if isinstance(modified_at, str)
                else modified_at
            )
        else:
            version = now

        entry = CacheEntry(
            key=gid,
            data=task,
            entry_type=EntryType.TASK,
            version=version,
            cached_at=now,
            ttl=ttl,
        )
        entries_to_cache[gid] = entry

    if entries_to_cache:
        cache.set_batch(entries_to_cache)

    return len(entries_to_cache)


def check_redis_health(cache: RedisCacheProvider) -> dict[str, Any]:
    """Check Redis connection health and return diagnostic info.

    Use this during deployment verification to ensure Redis is properly
    configured and accessible.

    Args:
        cache: SDK cache provider.

    Returns:
        Dict with health status and diagnostics.

    Example:
        >>> health = check_redis_health(cache)
        >>> if health["healthy"]:
        ...     print("Redis connection OK")
        ... else:
        ...     print(f"Redis error: {health['error']}")
    """
    result: dict[str, Any] = {
        "healthy": False,
        "error": None,
        "metrics": None,
    }

    try:
        healthy = cache.is_healthy()
        result["healthy"] = healthy

        if healthy:
            metrics = cache.get_metrics()
            result["metrics"] = {
                "total_hits": metrics.hits,
                "total_misses": metrics.misses,
                "total_writes": metrics.writes,
                "total_errors": metrics.errors,
                "hit_rate": metrics.hit_rate,
            }
        else:
            result["error"] = "Redis health check failed (PING returned false)"

    except CACHE_TRANSIENT_ERRORS as e:
        result["error"] = str(e)

    return result


def _parse_version(version_str: str) -> datetime:
    """Parse version string to datetime.

    Handles ISO format strings including Z suffix.

    Args:
        version_str: ISO format datetime string.

    Returns:
        Parsed datetime with UTC timezone.
    """
    if version_str.endswith("Z"):
        version_str = version_str[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(version_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        # Fallback to current time if parsing fails
        return datetime.now(UTC)
