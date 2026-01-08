"""Dynamic index for O(1) lookup on arbitrary column combinations.

Per TDD-DYNAMIC-RESOLVER-001 / FR-003:
Replaces hardcoded GidLookupIndex with generic multi-column support.

Components:
    - DynamicIndexKey: Composite key for versioned cache-friendly lookups
    - DynamicIndex: Generic O(1) lookup index for any column combination
    - DynamicIndexCache: LRU cache for DynamicIndex instances
"""

from __future__ import annotations

import threading
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    import polars as pl

logger = get_logger(__name__)


@dataclass(frozen=True)
class DynamicIndexKey:
    """Composite key for any column combination.

    Per FR-003: Versioned key format for cache compatibility.

    Attributes:
        columns: Tuple of column names (sorted for consistency).
        values: Tuple of values in same order as columns.

    Example:
        >>> key = DynamicIndexKey(
        ...     columns=("office_phone", "vertical"),
        ...     values=("+15551234567", "dental"),
        ... )
        >>> key.cache_key
        'idx1:office_phone=+15551234567:vertical=dental'
    """

    columns: tuple[str, ...]
    values: tuple[str, ...]

    @property
    def cache_key(self) -> str:
        """Generate versioned cache key string.

        Format: 'idx1:col1=val1:col2=val2'

        The 'idx1' prefix enables future format versioning.
        Columns are always sorted to ensure consistent keys
        regardless of criterion field order.

        Returns:
            Versioned cache key string.
        """
        pairs = ":".join(f"{col}={val}" for col, val in zip(self.columns, self.values))
        return f"idx1:{pairs}"

    @classmethod
    def from_criterion(
        cls,
        criterion: dict[str, Any],
        normalize: bool = True,
    ) -> DynamicIndexKey:
        """Create key from criterion dict.

        Args:
            criterion: Field -> value mapping.
            normalize: If True, lowercase string values for case-insensitive matching.

        Returns:
            DynamicIndexKey instance.
        """
        # Sort columns for consistent key generation
        sorted_columns = tuple(sorted(criterion.keys()))

        values = []
        for col in sorted_columns:
            value = criterion[col]
            if normalize and isinstance(value, str):
                value = value.lower()
            values.append(str(value))

        return cls(columns=sorted_columns, values=tuple(values))


@dataclass
class DynamicIndex:
    """Generic O(1) lookup index for any column combination.

    Per TDD-DYNAMIC-RESOLVER-001 / FR-003:
    - O(n) construction from DataFrame
    - O(1) hash-based lookup after construction
    - Supports multi-match (returns list of GIDs)
    - Column-combination agnostic

    Attributes:
        key_columns: Columns used for lookup key.
        value_column: Column containing GID values.
        created_at: Index creation timestamp.

    Example:
        >>> index = DynamicIndex.from_dataframe(
        ...     df=unit_df,
        ...     key_columns=["office_phone", "vertical"],
        ...     value_column="gid",
        ... )
        >>>
        >>> gids = index.lookup({"office_phone": "+15551234567", "vertical": "dental"})
        >>> print(gids)  # ["1234567890123456"]
    """

    # Public attributes
    key_columns: tuple[str, ...]
    value_column: str
    created_at: datetime

    # Internal lookup dict - stores cache_key -> list of GIDs
    _lookup: dict[str, list[str]] = field(default_factory=dict, repr=False)

    @property
    def entry_count(self) -> int:
        """Return number of unique keys in index."""
        return len(self._lookup)

    def __len__(self) -> int:
        """Return number of unique keys in index."""
        return len(self._lookup)

    def lookup(self, criteria: dict[str, Any]) -> list[str]:
        """Return all matching GIDs for criteria.

        Args:
            criteria: Field -> value mapping to look up.

        Returns:
            List of matching GID strings (empty if no match).

        Example:
            >>> gids = index.lookup({"office_phone": "+15551234567"})
            >>> len(gids)
            1
        """
        key = DynamicIndexKey.from_criterion(criteria)
        return self._lookup.get(key.cache_key, [])

    def lookup_single(self, criteria: dict[str, Any]) -> str | None:
        """Return first matching GID (backwards-compatible single lookup).

        Args:
            criteria: Field -> value mapping.

        Returns:
            First matching GID or None.
        """
        gids = self.lookup(criteria)
        return gids[0] if gids else None

    def contains(self, criteria: dict[str, Any]) -> bool:
        """Check if criteria exists in index.

        Args:
            criteria: Field -> value mapping.

        Returns:
            True if at least one match exists.
        """
        key = DynamicIndexKey.from_criterion(criteria)
        return key.cache_key in self._lookup

    def available_columns(self) -> list[str]:
        """Return columns this index can look up.

        Returns:
            List of column names used in index key.
        """
        return list(self.key_columns)

    @classmethod
    def from_dataframe(
        cls,
        df: "pl.DataFrame",
        key_columns: list[str],
        value_column: str = "gid",
    ) -> DynamicIndex:
        """Build index from DataFrame.

        Per FR-003: O(n) scan of DataFrame on first access.

        Args:
            df: Polars DataFrame containing entity data.
            key_columns: Columns to use as lookup key.
            value_column: Column containing GID values.

        Returns:
            DynamicIndex instance with O(1) lookup capability.

        Raises:
            KeyError: If required columns are missing from DataFrame.

        Example:
            >>> index = DynamicIndex.from_dataframe(
            ...     df=pl.DataFrame({
            ...         "office_phone": ["+15551234567", "+15559876543"],
            ...         "vertical": ["dental", "medical"],
            ...         "gid": ["123", "456"],
            ...     }),
            ...     key_columns=["office_phone", "vertical"],
            ... )
        """
        # Validate columns exist
        all_columns = set(key_columns) | {value_column}
        missing = all_columns - set(df.columns)
        if missing:
            raise KeyError(f"Missing required columns: {missing}")

        # Sort key columns for consistent key generation
        sorted_key_columns = tuple(sorted(key_columns))

        # Build lookup dictionary
        lookup: dict[str, list[str]] = defaultdict(list)

        # Filter out rows with null values in key or value columns
        valid_df = df.filter(df[value_column].is_not_null())
        for col in key_columns:
            valid_df = valid_df.filter(valid_df[col].is_not_null())

        # Build index
        for row in valid_df.iter_rows(named=True):
            # Create key from row values (lowercase for case-insensitive matching)
            key_values = tuple(str(row[col]).lower() for col in sorted_key_columns)
            key = DynamicIndexKey(
                columns=sorted_key_columns,
                values=key_values,
            )

            gid = str(row[value_column])
            lookup[key.cache_key].append(gid)

        index = cls(
            key_columns=sorted_key_columns,
            value_column=value_column,
            created_at=datetime.now(timezone.utc),
            _lookup=dict(lookup),
        )

        logger.info(
            "dynamic_index_built",
            extra={
                "key_columns": list(sorted_key_columns),
                "value_column": value_column,
                "entry_count": len(lookup),
                "row_count": len(valid_df),
            },
        )

        return index


@dataclass(frozen=True)
class IndexCacheKey:
    """Cache key for DynamicIndex instances.

    Attributes:
        entity_type: Entity type (e.g., "unit").
        columns: Frozen set of column names (order-independent).
    """

    entity_type: str
    columns: frozenset[str]

    def __hash__(self) -> int:
        return hash((self.entity_type, self.columns))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IndexCacheKey):
            return NotImplemented
        return self.entity_type == other.entity_type and self.columns == other.columns


class DynamicIndexCache:
    """LRU cache for DynamicIndex instances.

    Per NFR-002: Memory Efficiency
    - Max indexes per entity: 5 (most common column combinations)
    - LRU eviction threshold: 10 indexes per entity type
    - Cache TTL for unused indexes: 1 hour

    Attributes:
        max_per_entity: Maximum indexes per entity type.
        ttl_seconds: Time-to-live for cached indexes.

    Example:
        >>> cache = DynamicIndexCache(max_per_entity=5)
        >>>
        >>> # Store index
        >>> cache.put("unit", ["office_phone", "vertical"], index)
        >>>
        >>> # Retrieve (moves to front of LRU)
        >>> index = cache.get("unit", ["office_phone", "vertical"])
    """

    def __init__(
        self,
        max_per_entity: int = 5,
        ttl_seconds: int = 3600,  # 1 hour
    ) -> None:
        """Initialize the cache.

        Args:
            max_per_entity: Maximum indexes to cache per entity type.
            ttl_seconds: Time-to-live for cached indexes in seconds.
        """
        self.max_per_entity = max_per_entity
        self.ttl_seconds = ttl_seconds

        # Internal state
        self._cache: OrderedDict[IndexCacheKey, tuple[DynamicIndex, datetime]] = (
            OrderedDict()
        )
        self._entity_counts: dict[str, int] = {}
        self._lock = threading.RLock()

        # Statistics
        self._stats: dict[str, int] = {
            "hits": 0,
            "misses": 0,
            "evictions_lru": 0,
            "evictions_ttl": 0,
        }

    def get(
        self,
        entity_type: str,
        key_columns: list[str],
    ) -> DynamicIndex | None:
        """Get cached index for entity type and columns.

        Args:
            entity_type: Entity type identifier.
            key_columns: Columns the index was built for.

        Returns:
            DynamicIndex if cached and not stale, None otherwise.
        """
        key = IndexCacheKey(
            entity_type=entity_type,
            columns=frozenset(key_columns),
        )

        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None

            index, cached_at = self._cache[key]

            # Check TTL
            age = (datetime.now(timezone.utc) - cached_at).total_seconds()
            if age > self.ttl_seconds:
                self._evict_key(key)
                self._stats["evictions_ttl"] += 1
                self._stats["misses"] += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._stats["hits"] += 1

            return index

    def put(
        self,
        entity_type: str,
        key_columns: list[str],
        index: DynamicIndex,
    ) -> None:
        """Store index in cache.

        Args:
            entity_type: Entity type identifier.
            key_columns: Columns the index was built for.
            index: DynamicIndex to cache.
        """
        key = IndexCacheKey(
            entity_type=entity_type,
            columns=frozenset(key_columns),
        )

        with self._lock:
            # Remove existing if present
            if key in self._cache:
                self._evict_key(key)

            # Check entity limit
            count = self._entity_counts.get(entity_type, 0)
            while count >= self.max_per_entity:
                self._evict_lru_for_entity(entity_type)
                count = self._entity_counts.get(entity_type, 0)

            # Add entry
            self._cache[key] = (index, datetime.now(timezone.utc))
            self._entity_counts[entity_type] = count + 1

            logger.debug(
                "index_cache_put",
                extra={
                    "entity_type": entity_type,
                    "columns": list(key_columns),
                    "entry_count": index.entry_count,
                },
            )

    def get_or_build(
        self,
        entity_type: str,
        key_columns: list[str],
        df: "pl.DataFrame",
    ) -> DynamicIndex:
        """Get cached index or build new one.

        This is a convenience method that combines get() and put()
        with index construction.

        Args:
            entity_type: Entity type identifier.
            key_columns: Columns for index key.
            df: DataFrame to build index from if not cached.

        Returns:
            Cached or newly built DynamicIndex.
        """
        # Try cache first
        index = self.get(entity_type, key_columns)
        if index is not None:
            return index

        # Build new index
        index = DynamicIndex.from_dataframe(
            df=df,
            key_columns=key_columns,
            value_column="gid",
        )

        # Cache it
        self.put(entity_type, key_columns, index)

        return index

    def invalidate(
        self,
        entity_type: str | None = None,
        key_columns: list[str] | None = None,
    ) -> int:
        """Invalidate cached indexes.

        Args:
            entity_type: Specific entity type or None for all.
            key_columns: Specific columns or None for all of entity.

        Returns:
            Number of entries invalidated.
        """
        with self._lock:
            if entity_type is None:
                # Clear all
                count = len(self._cache)
                self._cache.clear()
                self._entity_counts.clear()
                return count

            if key_columns is not None:
                # Specific entry
                key = IndexCacheKey(
                    entity_type=entity_type,
                    columns=frozenset(key_columns),
                )
                if key in self._cache:
                    self._evict_key(key)
                    return 1
                return 0

            # All entries for entity type
            count = 0
            keys_to_remove = [k for k in self._cache if k.entity_type == entity_type]
            for key in keys_to_remove:
                self._evict_key(key)
                count += 1
            return count

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        with self._lock:
            return {
                **self._stats,
                "total_entries": len(self._cache),
                "entity_types": len(self._entity_counts),
            }

    def _evict_key(self, key: IndexCacheKey) -> None:
        """Evict a specific key (internal, assumes lock held)."""
        if key in self._cache:
            del self._cache[key]
            self._entity_counts[key.entity_type] = max(
                0,
                self._entity_counts.get(key.entity_type, 1) - 1,
            )

    def _evict_lru_for_entity(self, entity_type: str) -> None:
        """Evict LRU entry for entity type (internal, assumes lock held)."""
        for key in self._cache:
            if key.entity_type == entity_type:
                self._evict_key(key)
                self._stats["evictions_lru"] += 1
                break
