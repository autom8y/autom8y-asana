"""Watermark repository for incremental sync tracking.

Per TDD-materialization-layer FR-001:
Centralized timestamp tracking for per-project modified_since sync.

Per sprint-materialization-003 Task 4:
Extended with S3 persistence for restart resilience. Watermarks persist to S3
on set and load from S3 on startup, enabling true incremental syncs after
cold starts.

This module provides thread-safe watermark management for incremental
DataFrame synchronization. Each project's watermark represents the last
successful sync timestamp, enabling efficient `modified_since` queries
to fetch only changed tasks.

Thread Safety:
    - Singleton creation protected by class-level lock
    - Instance operations protected by instance-level lock
    - Consistent with EntityProjectRegistry pattern

Persistence:
    - Optional S3 persistence via DataFramePersistence
    - Write-through: set_watermark() persists asynchronously
    - Startup: load_from_persistence() hydrates from S3
    - Graceful degradation when S3 unavailable

Example:
    >>> from autom8_asana.dataframes.watermark import get_watermark_repo
    >>> from datetime import datetime, timezone
    >>>
    >>> repo = get_watermark_repo()
    >>> repo.set_watermark("123456", datetime.now(timezone.utc))
    >>> wm = repo.get_watermark("123456")
    >>> if wm is None:
    ...     # First sync - do full fetch
    ...     pass
    ... else:
    ...     # Incremental sync using modified_since=wm
    ...     pass
"""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.dataframes.persistence import DataFramePersistence

__all__ = ["WatermarkRepository", "get_watermark_repo"]

logger = get_logger(__name__)


class WatermarkRepository:
    """Thread-safe singleton for per-project watermark tracking.

    Per FR-001: Tracks last successful sync timestamp per project.
    Used by incremental refresh to fetch only changed tasks.

    Per sprint-materialization-003 Task 4: Extended with S3 persistence.
    Watermarks are persisted on set and loaded from S3 on startup.

    Thread safety: Uses threading.Lock for concurrent access.
    Singleton pattern: Consistent with EntityProjectRegistry.

    Attributes:
        _watermarks: Dict mapping project_gid to last sync datetime.
        _instance_lock: Threading lock for thread-safe watermark access.
        _persistence: Optional DataFramePersistence for S3 write-through.

    Example:
        >>> repo = WatermarkRepository.get_instance()
        >>> repo.set_watermark("123456", datetime.now(timezone.utc))
        >>> wm = repo.get_watermark("123456")
        >>> if wm is None:
        ...     # First sync - do full fetch
        ...     pass

    Testing:
        >>> WatermarkRepository.reset()  # Clear singleton for test isolation
    """

    _instance: ClassVar[WatermarkRepository | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    # Instance attributes (declared for pyright, initialized in __new__)
    _watermarks: dict[str, datetime]
    _instance_lock: threading.Lock
    _persistence: DataFramePersistence | None

    def __new__(cls) -> WatermarkRepository:
        """Get or create singleton instance (thread-safe).

        Returns:
            The singleton WatermarkRepository instance.
        """
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._watermarks = {}
                instance._instance_lock = threading.Lock()
                instance._persistence = None
                cls._instance = instance
            return cls._instance

    @classmethod
    def get_instance(
        cls, persistence: DataFramePersistence | None = None
    ) -> WatermarkRepository:
        """Get singleton instance, optionally configuring persistence.

        Args:
            persistence: Optional DataFramePersistence for S3 write-through.
                         Only applied on first call or after reset().

        Returns:
            The singleton WatermarkRepository instance.
        """
        instance = cls()
        # Only set persistence if provided and not already set
        if persistence is not None and instance._persistence is None:
            instance._persistence = persistence
        return instance

    def set_persistence(self, persistence: DataFramePersistence | None) -> None:
        """Configure persistence layer after initialization.

        This allows setting persistence after the singleton is created,
        useful for dependency injection patterns.

        Args:
            persistence: DataFramePersistence instance or None to disable.
        """
        with self._instance_lock:
            self._persistence = persistence

    def get_watermark(self, project_gid: str) -> datetime | None:
        """Get last sync timestamp for project.

        Args:
            project_gid: Asana project GID.

        Returns:
            UTC datetime of last successful sync, or None if never synced.
        """
        with self._instance_lock:
            return self._watermarks.get(project_gid)

    def set_watermark(self, project_gid: str, timestamp: datetime) -> None:
        """Update watermark after successful sync.

        If persistence is configured, also persists the watermark to S3
        asynchronously (fire-and-forget). Persistence failures are logged
        but do not affect the in-memory operation.

        Args:
            project_gid: Asana project GID.
            timestamp: UTC datetime of successful sync completion.

        Raises:
            ValueError: If timestamp is not timezone-aware.
        """
        if timestamp.tzinfo is None:
            raise ValueError("Watermark timestamp must be timezone-aware")

        with self._instance_lock:
            self._watermarks[project_gid] = timestamp
            persistence = self._persistence

        # Fire-and-forget async persist (outside lock)
        if persistence is not None:
            self._schedule_persist(project_gid, timestamp, persistence)

    def _schedule_persist(
        self,
        project_gid: str,
        timestamp: datetime,
        persistence: DataFramePersistence,
    ) -> None:
        """Schedule async persistence without blocking.

        Uses create_task if a running loop exists, otherwise logs a warning.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self._persist_watermark(project_gid, timestamp, persistence)
            )
        except RuntimeError:
            # No running event loop - log and skip
            logger.debug(
                "no_event_loop_for_watermark_persist",
                project_gid=project_gid,
            )

    async def _persist_watermark(
        self,
        project_gid: str,
        timestamp: datetime,
        persistence: DataFramePersistence,
    ) -> None:
        """Persist watermark to S3 asynchronously.

        This is a fire-and-forget operation. Failures are logged but
        do not raise exceptions or affect the caller.
        """
        try:
            success = await persistence.save_watermark(project_gid, timestamp)
            if not success:
                logger.debug(
                    "watermark_persist_returned_false",
                    project_gid=project_gid,
                )
        except Exception as e:
            logger.warning(
                "watermark_persist_failed",
                project_gid=project_gid,
                error=str(e),
            )

    def get_all_watermarks(self) -> dict[str, datetime]:
        """Get all watermarks for observability.

        Returns:
            Copy of watermarks dict (project_gid -> datetime).
            Returns a copy to prevent external modification.
        """
        with self._instance_lock:
            return dict(self._watermarks)

    def clear_watermark(self, project_gid: str) -> None:
        """Clear watermark for project (forces full rebuild).

        Args:
            project_gid: Asana project GID.
        """
        with self._instance_lock:
            self._watermarks.pop(project_gid, None)

    async def load_from_persistence(
        self, persistence: DataFramePersistence | None = None
    ) -> int:
        """Load all persisted watermarks from S3 into memory.

        This should be called during application startup to hydrate the
        repository with previously persisted watermarks, enabling incremental
        syncs after container restarts.

        Args:
            persistence: DataFramePersistence instance. If None, uses the
                         instance's configured persistence.

        Returns:
            Number of watermarks loaded from persistence.

        Example:
            >>> persistence = DataFramePersistence()
            >>> repo = get_watermark_repo()
            >>> loaded = await repo.load_from_persistence(persistence)
            >>> print(f"Loaded {loaded} watermarks from S3")
        """
        persistence = persistence or self._persistence
        if persistence is None:
            logger.debug("No persistence configured, skipping watermark load")
            return 0

        try:
            watermarks = await persistence.load_all_watermarks()
            if not watermarks:
                logger.debug("No persisted watermarks found in S3")
                return 0

            with self._instance_lock:
                self._watermarks.update(watermarks)

            logger.info(
                "watermarks_loaded_from_s3",
                count=len(watermarks),
            )
            return len(watermarks)

        except Exception as e:
            logger.warning(
                "watermarks_load_failed",
                error=str(e),
            )
            return 0

    @classmethod
    def reset(cls) -> None:
        """Reset singleton for testing.

        Clears the singleton instance so next access creates a fresh repository.
        """
        with cls._lock:
            cls._instance = None


def get_watermark_repo() -> WatermarkRepository:
    """Module-level accessor for WatermarkRepository singleton.

    Returns:
        WatermarkRepository singleton instance.

    Example:
        >>> repo = get_watermark_repo()
        >>> repo.set_watermark("proj_123", datetime.now(timezone.utc))
    """
    return WatermarkRepository.get_instance()
