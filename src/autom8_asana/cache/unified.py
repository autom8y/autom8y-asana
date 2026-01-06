"""Unified task store for single source of truth caching.

Per TDD-UNIFIED-CACHE-001: Consolidates TaskCacheCoordinator,
CascadingFieldResolver cache, and parent chain resolution into
a unified cache layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.cache.completeness import (
    CompletenessLevel,
    create_completeness_metadata,
    get_entry_completeness,
    get_fields_for_level,
    is_entry_sufficient,
)
from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.freshness_coordinator import (
    FreshnessCoordinator,
    FreshnessMode,
)
from autom8_asana.cache.hierarchy import HierarchyIndex

if TYPE_CHECKING:
    from autom8_asana.batch.client import BatchClient
    from autom8_asana.clients.tasks import TasksClient
    from autom8_asana.protocols.cache import CacheProvider

logger = get_logger(__name__)


@dataclass
class UnifiedTaskStore:
    """Single source of truth for task data with hierarchy awareness.

    Per TDD-UNIFIED-CACHE-001: Consolidates TaskCacheCoordinator,
    CascadingFieldResolver cache, and parent chain resolution.

    Composes:
    - CacheProvider: Storage backend (TieredCacheProvider or equivalent)
    - HierarchyIndex: Parent-child relationship tracking
    - FreshnessCoordinator: Batch staleness checks via Asana Batch API

    Attributes:
        cache: Cache provider for storage (Redis/S3 tiered).
        batch_client: BatchClient for Asana batch API (optional).
        freshness_mode: Default freshness mode for operations.

    Example:
        >>> store = UnifiedTaskStore(
        ...     cache=tiered_cache,
        ...     batch_client=batch_client,
        ...     freshness_mode=FreshnessMode.EVENTUAL,
        ... )
        >>> # Get single task
        >>> task = await store.get_async("task-gid")
        >>> # Get batch with freshness check
        >>> tasks = await store.get_batch_async(["gid1", "gid2", "gid3"])
        >>> # Get parent chain for cascade resolution
        >>> parents = await store.get_parent_chain_async("child-gid")
    """

    cache: "CacheProvider"
    batch_client: "BatchClient | None" = None
    freshness_mode: FreshnessMode = FreshnessMode.EVENTUAL

    # Internal components
    _hierarchy: HierarchyIndex = field(default_factory=HierarchyIndex, init=False)
    _freshness: FreshnessCoordinator = field(init=False)

    # Statistics
    _stats: dict[str, int] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize internal components."""
        self._freshness = FreshnessCoordinator(
            batch_client=self.batch_client,
            coalesce_window_ms=50,
            max_batch_size=100,
        )
        self._stats = {
            "get_hits": 0,
            "get_misses": 0,
            "put_count": 0,
            "invalidate_count": 0,
            "parent_chain_lookups": 0,
            "completeness_misses": 0,
            "upgrade_count": 0,
        }

    async def get_async(
        self,
        gid: str,
        freshness: FreshnessMode | None = None,
        required_level: CompletenessLevel = CompletenessLevel.STANDARD,
    ) -> dict[str, Any] | None:
        """Get single task, respecting freshness mode and completeness.

        Per TDD-UNIFIED-CACHE-001 Section 5.1:
        - IMMEDIATE: Return cached without validation
        - EVENTUAL: Return cached if TTL not expired, else validate
        - STRICT: Always validate against API

        Per TDD-CACHE-COMPLETENESS-001 Section 7.3:
        If cached entry exists but is insufficient for required_level,
        returns None (caller should upgrade or re-fetch).

        Args:
            gid: Task GID to retrieve.
            freshness: Override default freshness mode.
            required_level: Minimum completeness required.

        Returns:
            Task dict if found, fresh, AND sufficient; None otherwise.
        """
        mode = freshness or self.freshness_mode

        # Get from cache
        entry = self.cache.get_versioned(gid, EntryType.TASK)

        if entry is None:
            self._stats["get_misses"] += 1
            return None

        # Check completeness (per TDD-CACHE-COMPLETENESS-001)
        if not is_entry_sufficient(entry, required_level):
            self._stats["get_misses"] += 1
            self._stats["completeness_misses"] += 1
            logger.debug(
                "cache_completeness_insufficient",
                extra={
                    "gid": gid,
                    "cached_level": get_entry_completeness(entry).name,
                    "required_level": required_level.name,
                },
            )
            return None

        # For IMMEDIATE mode, return cached immediately
        if mode == FreshnessMode.IMMEDIATE:
            self._stats["get_hits"] += 1
            return entry.data

        # Check freshness
        results = await self._freshness.check_batch_async([entry], mode=mode)
        if results and results[0].is_fresh:
            self._stats["get_hits"] += 1
            return entry.data

        # Stale or error - return None (caller should fetch fresh)
        self._stats["get_misses"] += 1
        return None

    async def get_batch_async(
        self,
        gids: list[str],
        freshness: FreshnessMode | None = None,
        required_level: CompletenessLevel = CompletenessLevel.STANDARD,
    ) -> dict[str, dict[str, Any] | None]:
        """Get multiple tasks with batch freshness check and completeness.

        Per TDD-UNIFIED-CACHE-001 Goal G4: Single batch API call validates N tasks.
        Per TDD-CACHE-COMPLETENESS-001: Checks completeness before returning.

        Args:
            gids: Task GIDs to retrieve.
            freshness: Override default freshness mode.
            required_level: Minimum completeness required.

        Returns:
            Dict mapping GID to Task dict or None if not found/stale/insufficient.
        """
        if not gids:
            return {}

        mode = freshness or self.freshness_mode

        # Get all from cache
        entries = self.cache.get_batch(gids, EntryType.TASK)

        # Separate found vs missing, checking completeness
        found_entries: list[CacheEntry] = []
        result: dict[str, dict[str, Any] | None] = {}

        for gid in gids:
            entry = entries.get(gid)
            if entry is None:
                result[gid] = None
                self._stats["get_misses"] += 1
            elif not is_entry_sufficient(entry, required_level):
                # Entry exists but is insufficient
                result[gid] = None
                self._stats["get_misses"] += 1
                self._stats["completeness_misses"] += 1
                logger.debug(
                    "cache_completeness_insufficient",
                    extra={
                        "gid": gid,
                        "cached_level": get_entry_completeness(entry).name,
                        "required_level": required_level.name,
                    },
                )
            else:
                found_entries.append(entry)

        if not found_entries:
            return result

        # For IMMEDIATE mode, return all found entries
        if mode == FreshnessMode.IMMEDIATE:
            for entry in found_entries:
                result[entry.key] = entry.data
                self._stats["get_hits"] += 1
            return result

        # Check freshness for found entries
        freshness_results = await self._freshness.check_batch_async(
            found_entries, mode=mode
        )

        # Map results
        gid_to_freshness = {r.gid: r for r in freshness_results}
        for entry in found_entries:
            fr = gid_to_freshness.get(entry.key)
            if fr and fr.is_fresh:
                result[entry.key] = entry.data
                self._stats["get_hits"] += 1
            else:
                result[entry.key] = None
                self._stats["get_misses"] += 1

        return result

    async def upgrade_async(
        self,
        gid: str,
        target_level: CompletenessLevel,
        tasks_client: "TasksClient | None" = None,
    ) -> dict[str, Any] | None:
        """Upgrade cache entry to target completeness level.

        Per TDD-CACHE-COMPLETENESS-001 Section 7.4:
        Fetches task from API with expanded opt_fields corresponding
        to target_level, then updates cache.

        Args:
            gid: Task GID to upgrade.
            target_level: Desired completeness level.
            tasks_client: Optional TasksClient for fetch.

        Returns:
            Upgraded task data, or None if fetch failed.
        """
        opt_fields = get_fields_for_level(target_level)

        try:
            # Fetch via tasks client
            if tasks_client is None:
                logger.warning("upgrade_async called without tasks_client")
                return None

            task = await tasks_client.get_async(gid, opt_fields=opt_fields, raw=True)
            if task is None:
                return None

            # Store with new completeness
            await self.put_async(task, opt_fields=opt_fields)

            self._stats["upgrade_count"] += 1
            logger.info(
                "cache_entry_upgraded",
                extra={"gid": gid, "target_level": target_level.name},
            )
            return task

        except Exception as e:
            logger.warning(
                "cache_upgrade_failed",
                extra={"gid": gid, "target_level": target_level.name, "error": str(e)},
            )
            return None

    async def get_with_upgrade_async(
        self,
        gid: str,
        required_level: CompletenessLevel = CompletenessLevel.STANDARD,
        freshness: FreshnessMode | None = None,
        tasks_client: "TasksClient | None" = None,
    ) -> dict[str, Any] | None:
        """Get task with automatic upgrade if insufficient.

        Per TDD-CACHE-COMPLETENESS-001 Section 7.1:
        If cached entry is insufficient, fetches fresh with expanded fields.

        Args:
            gid: Task GID to retrieve.
            required_level: Minimum completeness required.
            freshness: Override default freshness mode.
            tasks_client: Client for upgrade fetch.

        Returns:
            Task dict at required completeness, or None if fetch failed.
        """
        # Try cache first
        result = await self.get_async(
            gid, freshness=freshness, required_level=required_level
        )
        if result is not None:
            return result

        # Upgrade if we have a client
        if tasks_client is not None:
            return await self.upgrade_async(
                gid, required_level, tasks_client=tasks_client
            )

        return None

    async def get_batch_with_upgrade_async(
        self,
        gids: list[str],
        required_level: CompletenessLevel = CompletenessLevel.STANDARD,
        tasks_client: "TasksClient | None" = None,
    ) -> dict[str, dict[str, Any] | None]:
        """Get batch with automatic upgrade for insufficient entries.

        Per TDD-CACHE-COMPLETENESS-001 Section 9.1:
        1. Check cache for all GIDs
        2. Partition into sufficient/insufficient
        3. Batch fetch insufficient via API
        4. Update cache with fetched entries
        5. Return combined results

        Args:
            gids: Task GIDs to retrieve.
            required_level: Minimum completeness required.
            tasks_client: Client for upgrade fetch.

        Returns:
            Dict mapping GID to task dict or None if not found/failed.
        """
        if not gids:
            return {}

        # Check cache
        cached = await self.get_batch_async(gids, required_level=required_level)

        # Identify misses
        insufficient_gids = [gid for gid, data in cached.items() if data is None]

        if not insufficient_gids or tasks_client is None:
            return cached

        # Batch upgrade
        opt_fields = get_fields_for_level(required_level)
        upgraded: dict[str, dict[str, Any] | None] = {}

        for gid in insufficient_gids:
            try:
                task = await tasks_client.get_async(gid, opt_fields=opt_fields, raw=True)
                if task:
                    await self.put_async(task, opt_fields=opt_fields)
                    upgraded[gid] = task
                    self._stats["upgrade_count"] += 1
            except Exception as e:
                logger.warning(
                    "batch_upgrade_failed",
                    extra={"gid": gid, "error": str(e)},
                )
                upgraded[gid] = None

        # Merge results
        return {**cached, **upgraded}

    async def put_async(
        self,
        task: dict[str, Any],
        ttl: int | None = None,
        opt_fields: list[str] | None = None,
    ) -> None:
        """Store task in cache with hierarchy indexing and completeness tracking.

        Per TDD-UNIFIED-CACHE-001 Section 5.1:
        - Stores task data in cache
        - Registers parent-child relationship in hierarchy index
        - Extracts entity_type from detection results if available

        Per TDD-CACHE-COMPLETENESS-001 Section 7.2:
        - Includes completeness level in metadata based on opt_fields

        Args:
            task: Task dict with at least "gid" key.
            ttl: Optional TTL override.
            opt_fields: Fields used in fetch (for completeness inference).

        Raises:
            ValueError: If task is missing required "gid" field.
        """
        gid = task.get("gid")
        if not gid:
            raise ValueError("Task must have 'gid' field")

        # Extract version from modified_at
        modified_at = task.get("modified_at")
        version = self._parse_version(modified_at)

        # Build metadata with completeness tracking
        base_metadata = self._extract_metadata(task)
        completeness_metadata = create_completeness_metadata(opt_fields)

        # Create cache entry
        entry = CacheEntry(
            key=gid,
            data=task,
            entry_type=EntryType.TASK,
            version=version,
            cached_at=datetime.now(timezone.utc),
            ttl=ttl,
            metadata={**base_metadata, **completeness_metadata},
        )

        # Store in cache
        self.cache.set_versioned(gid, entry)

        # Register in hierarchy
        self._hierarchy.register(task)

        self._stats["put_count"] += 1

        logger.debug(
            "unified_store_put",
            extra={
                "gid": gid,
                "has_parent": task.get("parent") is not None,
                "ttl": ttl,
                "completeness_level": completeness_metadata.get("completeness_level"),
            },
        )

    async def put_batch_async(
        self,
        tasks: list[dict[str, Any]],
        ttl: int | None = None,
        opt_fields: list[str] | None = None,
        tasks_client: "TasksClient | None" = None,
        warm_hierarchy: bool = False,
    ) -> int:
        """Store multiple tasks with batch write and completeness tracking.

        Per TDD-CACHE-COMPLETENESS-001: Includes completeness level in metadata.
        Per ADR-hierarchy-registration-architecture: Optionally warms parent
        chains for complete cascade resolution.

        Args:
            tasks: List of task dicts to cache.
            ttl: Optional TTL override.
            opt_fields: Fields used in fetch (for completeness inference).
            tasks_client: Optional TasksClient for hierarchy warming.
            warm_hierarchy: If True, recursively fetch and register parent chains.

        Returns:
            Count of successfully cached tasks.
        """
        if not tasks:
            return 0

        entries: dict[str, CacheEntry] = {}
        cached_count = 0

        # Pre-compute completeness metadata (same for all tasks in batch)
        completeness_metadata = create_completeness_metadata(opt_fields)

        for task in tasks:
            gid = task.get("gid")
            if not gid:
                continue

            modified_at = task.get("modified_at")
            version = self._parse_version(modified_at)

            # Build metadata with completeness tracking
            base_metadata = self._extract_metadata(task)

            entry = CacheEntry(
                key=gid,
                data=task,
                entry_type=EntryType.TASK,
                version=version,
                cached_at=datetime.now(timezone.utc),
                ttl=ttl,
                metadata={**base_metadata, **completeness_metadata},
            )

            entries[gid] = entry

            # Register in hierarchy
            self._hierarchy.register(task)

            cached_count += 1

        # Batch store in cache
        if entries:
            self.cache.set_batch(entries)
            self._stats["put_count"] += cached_count

        # Warm parent chains if requested
        # Per ADR-hierarchy-registration-architecture: Recursively fetch and
        # register missing ancestors for complete cascade resolution
        ancestors_warmed = 0
        immediate_parents_fetched = 0
        if warm_hierarchy and tasks_client is not None:
            from autom8_asana.cache.hierarchy_warmer import (
                _HIERARCHY_OPT_FIELDS,
                warm_ancestors_async,
            )

            # Per TDD-unit-cascade-resolution-fix Fix 4: Fetch and register immediate
            # parents BEFORE calling warm_ancestors_async. This ensures the hierarchy
            # index has parent tasks registered so get_ancestor_chain() works.
            parent_gids_needed: set[str] = set()
            for task in tasks:
                parent = task.get("parent")
                if parent and isinstance(parent, dict):
                    parent_gid = parent.get("gid")
                    if parent_gid and not self._hierarchy.contains(parent_gid):
                        parent_gids_needed.add(parent_gid)

            if parent_gids_needed:
                logger.debug(
                    "warm_hierarchy_fetching_immediate_parents",
                    extra={"parent_count": len(parent_gids_needed)},
                )
                for parent_gid in parent_gids_needed:
                    try:
                        parent_task = await tasks_client.get_async(
                            parent_gid, opt_fields=_HIERARCHY_OPT_FIELDS
                        )
                        if parent_task:
                            parent_dict = parent_task.model_dump(exclude_none=True)
                            self._hierarchy.register(parent_dict)
                            await self.put_async(
                                parent_dict, opt_fields=_HIERARCHY_OPT_FIELDS
                            )
                            immediate_parents_fetched += 1
                    except Exception as e:
                        logger.warning(
                            "warm_immediate_parent_failed",
                            extra={"parent_gid": parent_gid, "error": str(e)},
                        )

            # Then warm deeper ancestors (grandparents and beyond)
            task_gids = [t.get("gid") for t in tasks if t.get("gid")]
            if task_gids:
                ancestors_warmed = await warm_ancestors_async(
                    gids=task_gids,
                    hierarchy_index=self._hierarchy,
                    tasks_client=tasks_client,
                    max_depth=5,
                    unified_store=self,  # Pass self to cache fetched parents
                )

        logger.debug(
            "unified_store_put_batch",
            extra={
                "task_count": len(tasks),
                "cached_count": cached_count,
                "ttl": ttl,
                "completeness_level": completeness_metadata.get("completeness_level"),
                "warm_hierarchy": warm_hierarchy,
                "immediate_parents_fetched": immediate_parents_fetched,
                "ancestors_warmed": ancestors_warmed,
            },
        )

        return cached_count

    async def get_parent_chain_async(
        self,
        gid: str,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        """Get parent chain for cascade resolution.

        Per TDD-UNIFIED-CACHE-001 Goal G3: Uses same cache as task lookups.

        First attempts to resolve via hierarchy index, then fetches
        any missing parents from cache.

        Args:
            gid: Starting task GID.
            max_depth: Maximum chain depth.

        Returns:
            List of parent task dicts from immediate parent to root.
            Empty list if task has no parent or chain not in cache.
        """
        self._stats["parent_chain_lookups"] += 1

        # Get ancestor GIDs from hierarchy index
        ancestor_gids = self._hierarchy.get_ancestor_chain(gid, max_depth=max_depth)

        if not ancestor_gids:
            return []

        # Fetch all ancestors from cache
        # Use IMMEDIATE mode since we want whatever is cached
        entries = self.cache.get_batch(ancestor_gids, EntryType.TASK)

        # Build ordered chain, stopping at first missing
        chain: list[dict[str, Any]] = []
        for ancestor_gid in ancestor_gids:
            entry = entries.get(ancestor_gid)
            if entry is not None:
                chain.append(entry.data)
            else:
                # Stop at first missing - can't continue chain
                logger.debug(
                    "parent_chain_incomplete",
                    extra={
                        "gid": gid,
                        "missing_gid": ancestor_gid,
                        "found_count": len(chain),
                    },
                )
                break

        return chain

    async def check_freshness_batch_async(
        self,
        gids: list[str],
    ) -> dict[str, bool]:
        """Batch check if cached tasks are fresh.

        Uses Asana Batch API to fetch modified_at for all GIDs
        in a single request (chunked by 10 per Asana limit).

        Args:
            gids: Task GIDs to check.

        Returns:
            Dict mapping GID to freshness status (True = fresh).
        """
        if not gids:
            return {}

        # Get cache entries
        entries = self.cache.get_batch(gids, EntryType.TASK)

        # Filter to found entries
        found_entries = [e for e in entries.values() if e is not None]
        if not found_entries:
            return {gid: False for gid in gids}

        # Check freshness
        results = await self._freshness.check_batch_async(
            found_entries, mode=FreshnessMode.STRICT
        )

        # Build result map
        result = {gid: False for gid in gids}  # Default to stale
        for fr in results:
            result[fr.gid] = fr.is_fresh

        return result

    def invalidate(
        self,
        gid: str,
        cascade: bool = False,
    ) -> None:
        """Invalidate cached task.

        Args:
            gid: Task GID to invalidate.
            cascade: If True, also invalidate all descendants.
        """
        self._stats["invalidate_count"] += 1

        # Invalidate the task
        self.cache.invalidate(gid, [EntryType.TASK])

        # Optionally invalidate descendants
        if cascade:
            descendant_gids = self._hierarchy.get_descendant_gids(gid)
            for desc_gid in descendant_gids:
                self.cache.invalidate(desc_gid, [EntryType.TASK])

            logger.debug(
                "unified_store_cascade_invalidate",
                extra={
                    "gid": gid,
                    "descendant_count": len(descendant_gids),
                },
            )

        # Remove from hierarchy
        self._hierarchy.remove(gid)

    def get_hierarchy_index(self) -> HierarchyIndex:
        """Get the hierarchy index for external traversal.

        Useful for cascade resolution and invalidation planning.

        Returns:
            HierarchyIndex instance.
        """
        return self._hierarchy

    def get_freshness_coordinator(self) -> FreshnessCoordinator:
        """Get the freshness coordinator.

        Useful for advanced freshness checking scenarios.

        Returns:
            FreshnessCoordinator instance.
        """
        return self._freshness

    def get_stats(self) -> dict[str, int]:
        """Get store statistics.

        Returns:
            Dict with hit/miss counts and operation counts.
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset statistics to zero."""
        for key in self._stats:
            self._stats[key] = 0

    def _parse_version(self, modified_at: str | None) -> datetime:
        """Parse modified_at to datetime for version tracking.

        Args:
            modified_at: ISO format timestamp or None.

        Returns:
            Parsed datetime, or current time if None.
        """
        if not modified_at:
            return datetime.now(timezone.utc)

        # Handle Z suffix
        if modified_at.endswith("Z"):
            modified_at = modified_at[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(modified_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            logger.warning(
                "version_parse_failed",
                extra={"modified_at": modified_at},
            )
            return datetime.now(timezone.utc)

    def _extract_metadata(self, task: dict[str, Any]) -> dict[str, Any]:
        """Extract metadata from task for cache entry.

        Args:
            task: Task dict.

        Returns:
            Metadata dict with entity_type, parent_gid, etc.
        """
        metadata: dict[str, Any] = {}

        # Extract parent GID
        parent = task.get("parent")
        if parent and isinstance(parent, dict):
            metadata["parent_gid"] = parent.get("gid")

        # Extract project GIDs if present
        projects = task.get("projects")
        if projects and isinstance(projects, list):
            metadata["project_gids"] = [
                p.get("gid") for p in projects if isinstance(p, dict) and p.get("gid")
            ]

        return metadata
