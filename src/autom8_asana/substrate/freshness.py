"""Substrate-v2 Seam 1 — FRESHNESS (pure core). RC-B.

FROZEN v1.0-frozen-2026-07-29 per TDD-substrate-v2 §4 Seam 1. SEAM-0 landed the
frozen contract surface; **S2 fills the freshness-law bodies here** (this file).

``is_provable`` is the SOLE freshness definition ([H3]/C1); ``canonical_digest``
is [H1] the ONE digest function. Both are consumed identically by serving
(Seam 4) and observability (Seam 5).

The law in one breath (RC-B): freshness is *content-derived truth*, never a
write-time stamp. An artifact's ``built_from_live_at`` is the MIN over its
sections' last **content-fetch** instants (``fold_built_from_live_at``); a probe
may DECIDE a re-fetch but there is **no API here that advances an instant without
a content fetch** — so the v1 D8 null-watermark false-CLEAN class is
*unconstructable*, not merely guarded. ``content_digest`` is a sha256 over the
five-pin canonical form of the **value** columns (``canonical_digest``), never
GIDs and never parquet bytes — so a GID-set-preserving value edit (v1's blind
spot) changes the digest.

Purity: ``canonical_digest`` / ``is_provable`` / ``fold_built_from_live_at`` do
no I/O and touch no registry. ``sla_seconds_for`` is the one function that reads
the entity registry (C8 — no new config home); it uses a function-local import so
the pure core stays registry-free.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    import polars as pl

    from autom8_asana.core.types import EntityType


def _require_aware(moment: datetime, label: str) -> None:
    """[H2] Reject naive datetimes — monotonic freshness decay only holds in UTC.

    Carries the repo's established discipline (``dataframes/storage.py`` raises
    ``"Watermark timestamp must be timezone-aware"`` on a naive watermark). We
    also reject an aware datetime whose ``utcoffset()`` is undefined, which is
    strictly stronger than a bare ``tzinfo is None`` check.
    """
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware (UTC); got naive {moment!r}")


@dataclass(frozen=True, slots=True)
class FreshnessProof:
    """Content-derived freshness proof (RC-B). Seam 1, FROZEN v1.0.

    Fields transcribed verbatim from TDD §4 Seam 1. Frozen + slotted: once built
    by a content-bearing rebuild, no field mutates — there is no "stamp fresh"
    path (D8-unconstructable).
    """

    # tz-aware UTC; = MIN over constituent sections' last REAL content-fetch instants (C1)
    built_from_live_at: datetime
    # sha256 hex over canonical_digest() form — never GIDs, never parquet bytes
    content_digest: str
    # freshness contract for this (project, entity) class; sourced from the entity registry
    sla_seconds: int

    def __post_init__(self) -> None:
        """[H2] tz-reject guard — a proof cannot be born with a naive instant."""
        _require_aware(self.built_from_live_at, "built_from_live_at")


class Provability(Enum):
    """CLOSED — shared verbatim with Seam 5; no builder adds a member."""

    PROVABLE = "provable"
    STALE = "stale"
    CORRUPT = "corrupt"


def is_provable(proof: FreshnessProof, served_frame_digest: str, now: datetime) -> Provability:
    """PROVABLE iff (now - built_from_live_at) <= sla_seconds AND served_frame_digest == content_digest.

    Else STALE (age) or CORRUPT (digest mismatch). Pure; deterministic in its 3
    args; no I/O, no ``now()``. ``proof.built_from_live_at`` is already tz-guarded
    at construction ([H2]); we reject a naive ``now`` here so the subtraction is
    always aware-vs-aware.

    The age arm is checked first (it is the SLA gate serving computes on every
    read); a fresh-but-mismatched digest surfaces as CORRUPT.
    """
    _require_aware(now, "now")
    age_seconds = (now - proof.built_from_live_at).total_seconds()
    if age_seconds > proof.sla_seconds:
        return Provability.STALE
    if served_frame_digest != proof.content_digest:
        return Provability.CORRUPT
    return Provability.PROVABLE


def fold_built_from_live_at(section_fetch_instants: Mapping[str, datetime]) -> datetime:
    """C1: an artifact's ``built_from_live_at`` = MIN over its sections' last content-fetch instants.

    THE LAW (D8-unconstructable): this fold's ONLY input is *content-fetch*
    instants — there is no ``probe_instant`` parameter and no other public
    function advances a section's instant. A cheap structural probe may decide
    *whether* to re-fetch a section (a scheduling optimization owned by the S4
    rebuilder), but it can never feed this fold, so a probe cannot freshen an
    artifact. A reused (not re-fetched) section keeps its OLD instant and honestly
    drags the whole artifact's age back to its stalest section (AV-1 regression
    closed): the artifact ages by its stalest constituent.

    Args:
        section_fetch_instants: ``{section_gid: last_content_fetch_at}`` — every
            value tz-aware UTC. Must be non-empty: an artifact with no sections has
            no defined freshness (fail loud).

    Returns:
        The minimum (stalest) instant — the artifact's ``built_from_live_at``.
    """
    if not section_fetch_instants:
        raise ValueError(
            "cannot fold an empty section-provenance map: an artifact with zero "
            "sections has no defined built_from_live_at"
        )
    for section_gid, instant in section_fetch_instants.items():
        _require_aware(instant, f"section {section_gid!r} content-fetch instant")
    return min(section_fetch_instants.values())


# --- [H1] canonical digest — the ONE digest function, five pins FROZEN here ----

# (a) column set: the REGISTRY-DECLARED offer value columns (verified present in
#     dataframes/schemas/offer.py OFFER_COLUMNS — offer_id/cost/mrr/weekly_ad_spend).
#     The GID and every structural/cascade column is DELIBERATELY excluded: the
#     digest is value-derived (RC-B/P10), never GID-derived — that omission is what
#     kills v1's D8 blind spot. Prod corroboration of the exact economic set rides
#     to S8 as a labelled UV-P; the schema-membership of these four is verified by
#     the registry-anchoring test in tests/unit/substrate/test_freshness.py.
_VALUE_COLUMNS: tuple[str, ...] = ("cost", "mrr", "offer_id", "weekly_ad_spend")

# A pinned scheme tag guards against a future pin change silently colliding with a
# v1.0 digest. Stable for the life of the FROZEN v1.0 seam.
_DIGEST_SCHEME: str = "sv2-canonical-digest-1"


def _canon_number(value: int | float | Decimal) -> str:
    """[H1](e) float/decimal canonicalization — one pinned fixed-precision form.

    Any int/float/Decimal collapses to a single canonical decimal string with
    trailing zeros stripped, scientific notation expanded, and signed-zero folded:
    ``100``, ``100.0``, ``100.00`` and ``Decimal("1E+2")`` all map to ``"100"``;
    ``100.01`` stays ``"100.01"``. A non-finite float (NaN/inf) in a value column
    is corruption — fail loud.
    """
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"non-finite number in a value column: {value!r}")
    dec = Decimal(str(value))  # str(float) yields the shortest round-trip literal
    if dec == 0:
        return "0"
    return format(dec.normalize(), "f")


def _canon_value(value: object) -> str | None:
    """[H1](d)+(e) per-cell canonicalization.

    ``None`` (a polars null) maps to the pinned null sentinel — JSON ``null`` —
    which the type-distinct JSON encoding keeps unambiguous from the string
    ``"null"`` and from the empty string. Numbers route the (e) pin; strings pass
    through verbatim. Anything else in a value column is unexpected — fail loud.
    """
    if value is None:
        return None
    if isinstance(value, bool):  # bool is an int subclass — classify it first
        return "true" if value else "false"
    if isinstance(value, (int, float, Decimal)):
        return _canon_number(value)
    if isinstance(value, str):
        return value
    raise TypeError(
        f"uncanonicalizable value in a value column: {value!r} ({type(value).__name__})"
    )


def canonical_digest(frame: pl.DataFrame) -> str:
    """[H1] the ONE digest function; every producer/consumer calls it.

    Owned by S2 (``substrate.freshness``). Deterministic sha256 hex over the
    canonical *value* form of ``frame``, with all five pins frozen here:

    - (a) **column set** — the registry-declared value columns (``_VALUE_COLUMNS``)
      that are present in ``frame``, selected in sorted order. GID/structural
      columns are excluded, so the digest is value-derived (RC-B/P10).
    - (b) **row order** — ascending lexicographic sort over the per-row canonical
      encodings, so input row order (and duplicate rows) are irrelevant. (A
      pragmatic refinement of "sort on a declared row_key": the full canonical
      value-record is the sort key, robust to a null/duplicate single key.)
    - (c) **serialization** — a parquet-INDEPENDENT UTF-8 JSON encoding of
      sorted-key records; explicitly NOT ``frame.write_parquet()`` bytes (those
      embed non-deterministic compression/metadata).
    - (d) **null** — one pinned sentinel (JSON ``null``), type-distinct from
      ``""`` and ``"null"``.
    - (e) **float** — one pinned fixed-precision decimal form (see ``_canon_number``).

    **Frame type** ([FORK-W1] narrowing): ``frame`` is narrowed from the SEAM-0
    ``object`` stub to ``polars.DataFrame`` — the repo's existing concrete frame
    type (``dataframes/storage.py``). This is the contract S4 (serve) and S5
    (observe) inherit as multi-consumers of this function. No new substrate type
    is introduced.
    """
    present = sorted(column for column in _VALUE_COLUMNS if column in frame.columns)
    records = frame.select(present).to_dicts() if present else []
    encoded_rows = [
        json.dumps(
            {column: _canon_value(row[column]) for column in present},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for row in records
    ]
    encoded_rows.sort()  # (b) canonical row order
    payload = (
        _DIGEST_SCHEME
        + "\x1e"
        + json.dumps(encoded_rows, ensure_ascii=False, separators=(",", ":"))
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sla_seconds_for(entity_type: EntityType) -> int:
    """C8: the freshness ``sla_seconds`` for an entity class, read from the entity registry.

    No new config home ([H1]): the value IS the registry's existing per-entity
    ``default_ttl_seconds`` (e.g. offer = 180s). The registry is a heavy in-memory
    singleton, so the import is function-local to keep the pure-core surface of
    this module registry-free.

    Raises:
        ValueError: if ``entity_type`` has no registry descriptor (an unregistered
            entity has no governed SLA — fail loud rather than assume a default).
    """
    from autom8_asana.core.entity_registry import get_registry

    descriptor = get_registry().get_by_type(entity_type)
    if descriptor is None:
        raise ValueError(
            f"no entity-registry descriptor for {entity_type!r}; cannot resolve sla_seconds"
        )
    seconds: int = descriptor.default_ttl_seconds
    return seconds
