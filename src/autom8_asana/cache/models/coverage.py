"""Projection coverage predicate (PHE: Projection-Honest Entry).

Per ADR-taskcache-projection-coverage-2026-07-08 fork (a): a cache hit may be
served ONLY if the entry's stored projection (the opt_fields union it was
hydrated at) is KNOWN and a superset of the resolved requested projection.
Pure string-set math on persisted dotted opt_fields strings -- zero
platform-shape axioms, no data introspection. Every predicate error costs a
loud bounded re-fetch, never a silently-narrowed serve.

The authority slot is the base ``CacheEntry.metadata`` dict (NOT the
``EntityCacheEntry`` typed fields): ``staleness_coordinator._extend_ttl``
reconstructs a base ``CacheEntry`` spread-preserving only the metadata dict,
so typed subclass fields would be silently dropped on TTL extension.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from autom8_asana.cache.models.entry import CacheEntry

__all__ = ["projection_covers", "stored_projection"]


def stored_projection(entry: CacheEntry) -> frozenset[str] | None:
    """The projection this entry was hydrated at, or None if UNKNOWN.

    Reads ``entry.metadata["opt_fields_used"]`` (the key
    ``create_completeness_metadata`` already emits, completeness.py, and
    ``UnifiedTaskStore`` already writes). Absent OR EMPTY normalizes to None
    (coverage-UNKNOWN): ``create_completeness_metadata`` emits
    ``opt_fields or []``, so a historical ``put_async(opt_fields=None)`` write
    yields ``[]`` and must not claim empty coverage.

    Args:
        entry: Cache entry to read the persisted projection from.

    Returns:
        Frozenset of dotted opt_fields strings, or None when coverage is
        UNKNOWN (miss-once-and-heal).
    """
    raw = entry.metadata.get("opt_fields_used")
    if not raw:
        return None
    return frozenset(raw)


def projection_covers(entry: CacheEntry, requested: Iterable[str]) -> bool:
    """True iff the entry's stored projection is KNOWN and superset of requested.

    Exact-string subset on dotted opt_fields strings. NO prefix implication:
    stored ``custom_fields`` does NOT cover ``custom_fields.display_value``
    (Asana compact objects genuinely differ). Every predicate error is a
    re-fetch, never a narrowed serve. UNKNOWN => not covered =>
    miss-once-and-heal.

    Args:
        entry: Cache entry whose stored projection gates the serve.
        requested: The RESOLVED requested projection (dotted strings).

    Returns:
        True iff every requested field is in the KNOWN stored projection.
    """
    sp = stored_projection(entry)
    return sp is not None and frozenset(requested) <= sp
