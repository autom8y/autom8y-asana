"""Predicate + metadata unit tests for PHE projection coverage (TDD SS6.2).

Covers: exact-string subset semantics; UNKNOWN normalization (absent AND the
historical ``opt_fields_used: []`` shape from ``create_completeness_metadata``'s
``opt_fields or []``); serialization round-trip; and the METADATA-IS-THE-AUTHORITY
invariants -- the projection must survive ``StalenessCheckCoordinator._extend_ttl``
(which reconstructs a base ``CacheEntry`` spread-preserving only the metadata
dict) and ``MutationInvalidator`` soft-invalidate (``replace()`` preserves
metadata), while ``EntityCacheEntry`` TYPED fields would be silently DROPPED by
``_extend_ttl`` -- pinning why the metadata dict, not the typed slot, is the
authority (ADR fork a).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

from autom8_asana.cache.models.completeness import create_completeness_metadata
from autom8_asana.cache.models.coverage import projection_covers, stored_projection
from autom8_asana.cache.models.entry import CacheEntry, EntityCacheEntry, EntryType
from autom8_asana.cache.models.freshness_stamp import FreshnessStamp, VerificationSource


def make_entry(
    metadata: dict[str, Any] | None = None,
    **overrides: Any,
) -> CacheEntry:
    """Build a TASK CacheEntry with optional projection metadata."""
    kwargs: dict[str, Any] = {
        "key": "1234567890123",
        "data": {"gid": "1234567890123", "name": "Task"},
        "entry_type": EntryType.TASK,
        "version": datetime(2026, 1, 1, tzinfo=UTC),
        "ttl": 300,
        "metadata": metadata if metadata is not None else {},
    }
    kwargs.update(overrides)
    return CacheEntry(**kwargs)


class TestStoredProjection:
    """UNKNOWN normalization of the persisted projection."""

    def test_absent_metadata_is_unknown(self) -> None:
        assert stored_projection(make_entry()) is None

    def test_empty_opt_fields_used_is_unknown(self) -> None:
        """The completeness.py ``opt_fields or []`` historical shape: a
        put_async(opt_fields=None) write yields [] and must NOT claim empty
        coverage."""
        entry = make_entry(metadata={"opt_fields_used": []})
        assert stored_projection(entry) is None

    def test_create_completeness_metadata_none_shape_is_unknown(self) -> None:
        """Wire the normalization to the ACTUAL emitter output."""
        entry = make_entry(metadata=create_completeness_metadata(None))
        assert entry.metadata["opt_fields_used"] == []
        assert stored_projection(entry) is None

    def test_known_projection_round_trips_as_frozenset(self) -> None:
        entry = make_entry(metadata={"opt_fields_used": ["gid", "name"]})
        assert stored_projection(entry) == frozenset({"gid", "name"})


class TestProjectionCovers:
    """Exact-string subset semantics -- no prefix implication."""

    def test_equal_sets_covered(self) -> None:
        entry = make_entry(metadata={"opt_fields_used": ["gid", "name"]})
        assert projection_covers(entry, ["gid", "name"])

    def test_subset_covered(self) -> None:
        entry = make_entry(metadata={"opt_fields_used": ["gid", "name", "notes"]})
        assert projection_covers(entry, ["name"])

    def test_superset_not_covered(self) -> None:
        entry = make_entry(metadata={"opt_fields_used": ["gid"]})
        assert not projection_covers(entry, ["gid", "name"])

    def test_no_prefix_implication(self) -> None:
        """Stored ``custom_fields`` does NOT cover ``custom_fields.display_value``
        (Asana compact objects genuinely differ); the false-negative costs one
        loud re-fetch, never starvation."""
        entry = make_entry(metadata={"opt_fields_used": ["custom_fields"]})
        assert not projection_covers(entry, ["custom_fields.display_value"])

    def test_no_reverse_prefix_implication(self) -> None:
        entry = make_entry(metadata={"opt_fields_used": ["custom_fields.display_value"]})
        assert not projection_covers(entry, ["custom_fields"])

    def test_empty_request_covered_by_any_known_entry(self) -> None:
        entry = make_entry(metadata={"opt_fields_used": ["gid"]})
        assert projection_covers(entry, [])

    def test_unknown_entry_never_covers(self) -> None:
        assert not projection_covers(make_entry(), ["gid"])
        assert not projection_covers(make_entry(), [])


class TestMetadataSurvivalInvariants:
    """The projection's authority slot must survive every entry rewrite path."""

    def _coordinator(self) -> Any:
        from autom8_asana.cache.integration.staleness_coordinator import (
            StalenessCheckCoordinator,
        )
        from autom8_asana.cache.models.staleness_settings import StalenessCheckSettings

        return StalenessCheckCoordinator(
            cache_provider=MagicMock(),
            batch_client=MagicMock(),
            settings=StalenessCheckSettings(),
        )

    def test_projection_survives_extend_ttl(self) -> None:
        """staleness_coordinator._extend_ttl reconstructs a base CacheEntry with
        ``metadata={**entry.metadata, "extension_count": ...}`` -- the persisted
        projection MUST ride that spread."""
        entry = make_entry(
            metadata={"opt_fields_used": ["gid", "name"], "completeness_level": "minimal"}
        )
        extended = self._coordinator()._extend_ttl(entry)

        assert extended.metadata["opt_fields_used"] == ["gid", "name"]
        assert extended.metadata["completeness_level"] == "minimal"
        assert extended.metadata["extension_count"] == 1
        assert stored_projection(extended) == frozenset({"gid", "name"})

    def test_typed_opt_fields_would_be_dropped_by_extend_ttl(self) -> None:
        """The invariant that pins WHY metadata is the authority: an
        EntityCacheEntry's TYPED ``opt_fields``/``completeness_level`` fields do
        NOT survive _extend_ttl (it reconstructs a BASE CacheEntry), so any
        future refactor moving the projection to the typed slot silently breaks
        coverage on the first TTL extension."""
        typed = EntityCacheEntry(
            key="1234567890123",
            data={"gid": "1234567890123"},
            entry_type=EntryType.TASK,
            version=datetime(2026, 1, 1, tzinfo=UTC),
            ttl=300,
            completeness_level="standard",
            opt_fields=("gid", "name"),
        )
        extended = self._coordinator()._extend_ttl(typed)

        assert not isinstance(extended, EntityCacheEntry)
        assert getattr(extended, "opt_fields", None) is None
        # Typed-slot projection is GONE after extension => coverage-UNKNOWN.
        assert stored_projection(extended) is None

    async def test_projection_survives_soft_invalidate(self) -> None:
        """mutation_invalidator soft-invalidate uses ``replace(entry,
        freshness_stamp=...)`` -- metadata (and thus the projection) preserved."""
        from autom8y_cache.testing import MockCacheProvider

        from autom8_asana.cache.integration.mutation_invalidator import (
            MutationInvalidator,
            SoftInvalidationConfig,
        )
        from autom8_asana.cache.models.mutation_event import (
            EntityKind,
            MutationEvent,
            MutationType,
        )

        cache = MockCacheProvider()
        stamp = FreshnessStamp(
            last_verified_at=datetime(2026, 1, 1, tzinfo=UTC),
            source=VerificationSource.API_FETCH,
        )
        entry = make_entry(
            metadata={"opt_fields_used": ["gid", "name"], "completeness_level": "minimal"},
            freshness_stamp=stamp,
        )
        cache.set_versioned(entry.key, entry)

        invalidator = MutationInvalidator(
            cache_provider=cache,
            soft_config=SoftInvalidationConfig(
                enabled=True,
                soft_entity_kinds=frozenset({"task"}),
                soft_mutation_types=frozenset({"update"}),
            ),
        )
        await invalidator.invalidate_async(
            MutationEvent(
                entity_kind=EntityKind.TASK,
                entity_gid=entry.key,
                mutation_type=MutationType.UPDATE,
            )
        )

        marked = cache.get_versioned(entry.key, EntryType.TASK)
        assert marked is not None
        assert marked.freshness_stamp is not None
        assert marked.freshness_stamp.is_soft_invalidated()
        assert marked.metadata["opt_fields_used"] == ["gid", "name"]
        assert stored_projection(marked) == frozenset({"gid", "name"})

    def test_projection_survives_serialization_round_trip(self) -> None:
        """opt_fields_used survives to_dict/from_dict (schema-free: no version
        bump; old readers ignore the key, new readers see UNKNOWN on old data)."""
        entry = make_entry(
            metadata={"opt_fields_used": ["gid", "name"], "completeness_level": "minimal"}
        )
        revived = CacheEntry.from_dict(entry.to_dict())
        assert revived.metadata["opt_fields_used"] == ["gid", "name"]
        assert stored_projection(revived) == frozenset({"gid", "name"})

        legacy_dict = make_entry().to_dict()
        legacy = CacheEntry.from_dict(legacy_dict)
        assert stored_projection(legacy) is None
