"""Progressive tier for DataFrame cache using SectionPersistence storage.

Per TDD-UNIFIED-PROGRESSIVE-CACHE-001: Replaces S3Tier to read from the same
storage location as ProgressiveProjectBuilder, eliminating the dual-location bug.

Key format translation:
    "{entity_type}:{project_gid}" -> "dataframes/{project_gid}/"

Read path:
    1. Parse cache key to extract project_gid
    2. Delegate to DataFrameStorage.load_dataframe(project_gid)
    3. Construct CacheEntry with DataFrame and metadata

Write path:
    1. Delegate to SectionPersistence.write_final_artifacts_async()
    2. Ensures consistency with ProgressiveProjectBuilder writes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.core.errors import S3_TRANSPORT_ERRORS

if TYPE_CHECKING:
    from autom8_asana.cache.integration.dataframe_cache import (
        DataFrameCacheEntry as CacheEntry,
    )
    from autom8_asana.dataframes.section_persistence import SectionPersistence

__all__ = ["NULL_WATERMARK_DECAY_ANCHOR", "ProgressiveTier"]

logger = get_logger(__name__)

# FIX-N-B (offers-false-staleness-cure): the decay anchor for a storage
# watermark that could not be derived.
#
# CONTRACT §1.3 (null semantics): "Null -> DECAY. A null content axis means
# *unprovable*, and unprovable is **stale**, never fresh." The watermark is
# NEVER synthesized. Anchoring the age clock at ``datetime.min`` makes a
# null-watermark entry maximally stale by construction, so it classifies
# exactly as ``_check_freshness`` classifies any past-ceiling entry (STALE ->
# LKG) instead of reading age-0 / FRESH.
#
# SCOPE, STATED HONESTLY -- this closes a LATENT trap, not a firing one.
# ``DataFrameStorage`` (the Protocol, ``dataframes/storage.py:114-138``) types
# the watermark as ``datetime | None``, so ``(df, None, meta)`` is admissible at
# the seam. The only concrete implementation in this repo,
# ``S3DataFrameStorage``, cannot currently produce it: ``_load_at_keys``
# (``storage.py:1043-1052``) GETs the watermark sidecar FIRST and returns the
# whole tuple as ``None`` on a miss, constructing the datetime unconditionally
# before the parquet GET. Measured null-watermark frequency in production is
# ZERO. The guard therefore makes the invariant hold for ANY storage
# implementation rather than by accident of the current one's read ordering.
#
# Finite by design: the CONTRACT's C-NULL-a shape asks for a deterministic
# sentinel that is always greater than the ceiling, and explicitly refuses
# non-finite values (``inf`` corrupts downstream minute conversion). This
# anchor is finite, deterministic, and unmistakable for a real watermark.
NULL_WATERMARK_DECAY_ANCHOR = datetime.min.replace(tzinfo=UTC)


@dataclass
class ProgressiveTier:
    """S3 tier using SectionPersistence storage structure.

    Replaces S3Tier to use the same storage location as
    ProgressiveProjectBuilder, eliminating the dual-location bug.

    Key format translation:
        "{entity_type}:{project_gid}" -> "dataframes/{project_gid}/"

    Read path:
        1. Parse cache key to extract project_gid
        2. Load DataFrame and watermark via DataFrameStorage protocol
        3. Construct CacheEntry with metadata

    Write path:
        1. Delegate to SectionPersistence.write_final_artifacts_async()
        2. Ensures consistency with ProgressiveProjectBuilder writes

    Attributes:
        persistence: SectionPersistence instance for S3 operations.
        _stats: Operation statistics (reads, writes, errors, etc.).

    Example:
        >>> from autom8_asana.dataframes.section_persistence import create_section_persistence
        >>> persistence = create_section_persistence()
        >>> tier = ProgressiveTier(persistence=persistence)
        >>> entry = await tier.get_async("unit:proj-123")
    """

    persistence: SectionPersistence
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Initialize statistics."""
        self._stats = {
            "reads": 0,
            "writes": 0,
            "read_errors": 0,
            "write_errors": 0,
            "bytes_read": 0,
            "bytes_written": 0,
            "not_found": 0,
        }

    def _parse_key(self, key: str) -> tuple[str, str]:
        """Parse cache key into entity_type and project_gid.

        Args:
            key: Cache key in format "{entity_type}:{project_gid}".

        Returns:
            Tuple of (entity_type, project_gid).

        Raises:
            ValueError: If key format is invalid.

        Examples:
            "unit:1234567890" -> ("unit", "1234567890")
            "offer:9876543210" -> ("offer", "9876543210")
            "asset_edit:5555555555" -> ("asset_edit", "5555555555")
        """
        parts = key.split(":", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid cache key format: {key}")
        return parts[0], parts[1]

    async def get_async(self, key: str) -> CacheEntry | None:
        """Get entry from progressive storage location.

        Args:
            key: Cache key in format "{entity_type}:{project_gid}".

        Returns:
            CacheEntry if found and readable, None otherwise.

        Algorithm:
            1. Parse key: "unit:1234567890" -> project_gid="1234567890"
            2. Load via DataFrameStorage.load_dataframe(project_gid)
            3. Construct CacheEntry with metadata
            4. Return None on any error (graceful degradation)
        """
        from autom8_asana.cache.integration.dataframe_cache import (
            DataFrameCacheEntry as CacheEntry,
        )

        try:
            entity_type, project_gid = self._parse_key(key)
        except ValueError as e:
            logger.warning(
                "progressive_tier_invalid_key",
                extra={"key": key, "error": str(e)},
            )
            self._stats["read_errors"] += 1
            return None

        self._stats["reads"] += 1

        try:
            storage = self.persistence.storage
            # Use load_dataframe_with_metadata to get schema_version from
            # watermark.json in the same S3 read pass (IMP-06: eliminates
            # a separate load_json call for the same watermark file).
            #
            # SEAM-1 (ADR-SEAM1): entity_type is parsed from the cache key above
            # and MUST be threaded into the storage read. This is the exact
            # historical discard point -- the entity_type was recovered by
            # _parse_key and then dropped one line later, so an offer read and a
            # section read of the same project_gid resolved the SAME entity-
            # agnostic key. Threading it selects the collision-free v2 key (with
            # legacy fallback) so the offer denominator is no longer clobbered.
            if hasattr(storage, "load_dataframe_with_metadata"):
                df, watermark, wm_metadata = await storage.load_dataframe_with_metadata(
                    project_gid, entity_type
                )
            else:
                df, watermark = await storage.load_dataframe(project_gid, entity_type)
                wm_metadata = None
        except S3_TRANSPORT_ERRORS as e:
            self._stats["read_errors"] += 1
            logger.warning(
                "progressive_tier_read_error",
                extra={"key": key, "project_gid": project_gid, "error": str(e)},
            )
            return None
        except (
            Exception  # noqa: BLE001
        ) as e:  # BROAD-CATCH: vendor-polymorphic -- load_dataframe may raise diverse errors
            self._stats["read_errors"] += 1
            logger.warning(
                "progressive_tier_parse_error",
                extra={"key": key, "error": str(e)},
            )
            return None

        if df is None:
            self._stats["not_found"] += 1
            logger.debug(
                "progressive_tier_not_found",
                extra={"key": key, "project_gid": project_gid},
            )
            return None

        # Estimate bytes read from DataFrame memory footprint
        estimated_bytes = int(df.estimated_size())
        self._stats["bytes_read"] += estimated_bytes

        # Use the watermark from storage. When storage carries none, DECAY --
        # do NOT substitute now().
        #
        # FIX-N-B: the pre-fix code substituted ``datetime.now(UTC)`` here and
        # then used that substitute as ``created_at`` below. Fed a frame of
        # arbitrary true age with no watermark, that path hydrates at age 0 and
        # reads FRESH -- a synthetic-fresh generator wired into the seam's type
        # signature (CONTRACT §1.3 names this exact site). It is DISARMED today
        # by ``S3DataFrameStorage``'s sidecar-first read ordering, not by any
        # invariant this module holds; see NULL_WATERMARK_DECAY_ANCHOR. An
        # underivable watermark is UNPROVABLE recency, and unprovable is stale.
        watermark_provable = watermark is not None
        if watermark is None:
            watermark = NULL_WATERMARK_DECAY_ANCHOR
            logger.warning(
                "progressive_tier_null_watermark_decay",
                extra={
                    "key": key,
                    "project_gid": project_gid,
                    "entity_type": entity_type,
                    "reason": "storage_watermark_absent_entry_decayed_not_synthesized",
                },
            )

        # Schema version: extract from watermark metadata (already loaded),
        # fall back to SchemaRegistry if not available
        schema_version = None
        if wm_metadata is not None:
            schema_version = wm_metadata.get("schema_version")

        if schema_version is None:
            from autom8_asana.dataframes.models.registry import get_schema_version

            schema_version = get_schema_version(entity_type) or "unknown"

        entry = CacheEntry(
            project_gid=project_gid,
            entity_type=entity_type,
            dataframe=df,
            watermark=watermark,
            # Use watermark as created_at for consistency. Under FIX-N-B a null
            # storage watermark carries the decay anchor here, so the entry is
            # maximally stale rather than age-0 -- the serve decision is
            # unchanged in kind (the availability design still serves a
            # populated/healthy cache-only frame as LKG); only the freshness
            # SIGNAL stops lying.
            created_at=watermark,
            schema_version=schema_version,
        )

        logger.debug(
            "progressive_tier_read_success",
            extra={
                "key": key,
                "row_count": entry.row_count,
                "bytes_read": estimated_bytes,
                # FIX-N-B measurement surface: makes null-watermark S3 metadata
                # countable per entity_type (the frequency the design flagged as
                # a UV-P because no such log field existed).
                "watermark_provable": watermark_provable,
            },
        )

        return entry

    async def put_async(self, key: str, entry: CacheEntry) -> bool:
        """Store entry to progressive storage location.

        Delegates to SectionPersistence.write_final_artifacts_async() to ensure
        consistency with ProgressiveProjectBuilder writes.

        Args:
            key: Cache key in format "{entity_type}:{project_gid}".
            entry: CacheEntry containing DataFrame and metadata.

        Returns:
            True if written successfully, False on error.
        """
        try:
            entity_type, project_gid = self._parse_key(key)
        except ValueError as e:
            logger.warning(
                "progressive_tier_put_invalid_key",
                extra={"key": key, "error": str(e)},
            )
            self._stats["write_errors"] += 1
            return False

        self._stats["writes"] += 1

        try:
            # Delegate to SectionPersistence for consistent writes. Thread the entry's
            # fail-closed write context (Warmer-Path PRESERVE Enforcement) so the
            # converged write primitive honors PRESERVE/COALESCE at this — the
            # operative warmer write site (W3) — instead of an unconditional save.
            # index_data stays None for the index-laziness reason (unrelated).
            success = await self.persistence.write_final_artifacts_async(
                project_gid=project_gid,
                df=entry.dataframe,
                watermark=entry.watermark,
                index_data=None,  # Index is built lazily, not stored with cache
                entity_type=entity_type,
                population_degraded=getattr(entry, "population_degraded", False),
                population_min_rate=getattr(entry, "population_min_rate", 1.0),
                write_decision=getattr(entry, "write_decision", None),
            )

            if success:
                # Estimate bytes written from DataFrame memory footprint
                self._stats["bytes_written"] += int(entry.dataframe.estimated_size())

                logger.info(
                    "progressive_tier_put_success",
                    extra={
                        "key": key,
                        "row_count": entry.row_count,
                        "watermark": entry.watermark.isoformat(),
                    },
                )
            else:
                self._stats["write_errors"] += 1
                logger.error(
                    "progressive_tier_put_error",
                    extra={"key": key, "project_gid": project_gid},
                )

            return success

        except S3_TRANSPORT_ERRORS as e:
            self._stats["write_errors"] += 1
            logger.error(
                "progressive_tier_put_exception",
                extra={"key": key, "error": str(e), "error_type": type(e).__name__},
            )
            return False

    async def exists_async(self, key: str) -> bool:
        """Check if entry exists by attempting to load the watermark.

        Args:
            key: Cache key in format "{entity_type}:{project_gid}".

        Returns:
            True if dataframe data exists for project.
        """
        try:
            entity_type, project_gid = self._parse_key(key)
        except ValueError:
            return False

        try:
            storage = self.persistence.storage
            # SEAM-1: thread entity_type so existence is checked against the v2
            # key (with legacy fallback), matching the read path in get_async.
            df, _wm = await storage.load_dataframe(project_gid, entity_type)
            return df is not None
        except S3_TRANSPORT_ERRORS:  # graceful degradation
            return False

    async def delete_async(self, key: str) -> bool:
        """Delete entry (dataframe + watermark files).

        Does not delete section files or manifest to preserve resume capability.

        Args:
            key: Cache key in format "{entity_type}:{project_gid}".

        Returns:
            True if deleted or didn't exist.
        """
        try:
            entity_type, project_gid = self._parse_key(key)
        except ValueError as e:
            logger.warning(
                "progressive_tier_delete_invalid_key",
                extra={"key": key, "error": str(e)},
            )
            return False

        try:
            storage = self.persistence.storage
            # SEAM-1: delete the v2 entity-keyed artifacts for this entity view.
            success = await storage.delete_dataframe(project_gid, entity_type)

            if success:
                logger.info(
                    "progressive_tier_delete_success",
                    extra={"key": key, "project_gid": project_gid},
                )
            else:
                logger.warning(
                    "progressive_tier_delete_partial",
                    extra={"key": key, "project_gid": project_gid},
                )

            return success

        except S3_TRANSPORT_ERRORS as e:
            logger.warning(
                "progressive_tier_delete_error",
                extra={"key": key, "error": str(e)},
            )
            return False

    def get_stats(self) -> dict[str, int]:
        """Get tier statistics.

        Returns:
            Dict with keys: reads, writes, read_errors, write_errors,
            bytes_read, bytes_written, not_found.
        """
        return dict(self._stats)

    def _parse_datetime(self, value: str | None) -> datetime:
        """Parse ISO datetime string or return current time.

        Args:
            value: ISO format datetime string or None.

        Returns:
            Parsed datetime, or current UTC time if parsing fails.
        """
        from autom8_asana.core.datetime_utils import parse_iso_datetime

        result = parse_iso_datetime(value, default_now=True)
        assert result is not None  # default_now=True guarantees non-None
        return result
