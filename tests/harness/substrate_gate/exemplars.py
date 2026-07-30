"""Parity exemplars — #1 (historical ``$84,385``-vs-``$79,585`` divergence) + #2 (current).

Exemplar #1 is FROZEN-HISTORICAL; do not refresh to current prod — current state lives
in exemplar #2 (``exemplar_two_*``, an S8-0 additive current-state anchor derived from
the real S3 offer plane; see the bottom of this module and the recapture receipt).

REQUIREMENT 3 of the S7 build. The DEFECT headline (DEFECT :64-71) encoded as a
fixture: a stale v2/offer plane summing to ``$79,585`` (frozen 2026-07-13) vs a fresh
re-warm summing to ``$84,385`` (15:27 UTC) — a ``+$4,800 / +6%`` divergence that is a
COHERENT COMPOSITION SHIFT, not noise:

    ACTIVE                    51r·$65,585 → 48r·$61,585   = −$4,000
    OPTIMIZE – Human Review    2r·$3,100  →  5r·$7,900    = +$4,800
    STAGED                     5r·$6,000  →  7r·$10,000   = +$4,000
                                                    net    = +$4,800

The three DEFECT sections carry the whole net delta; the unchanged remainder is held
in ``OTHER (unchanged)`` (``$4,900`` both sides, delta ``$0``) so the fixture is
arithmetically self-consistent on BOTH invariants the exemplar test asserts:
Σ per_section_delta == magnitude, and Σ composition == served_value on each plane.

The parity runner must EXPLAIN this divergence via the ledger (the RC-A-2
``RefusePayload``), and the same seeded state drives the RC-A-2 replay case.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from autom8_asana.core.types import EntityType
from autom8_asana.substrate.freshness import FreshnessProof
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.serve import RefuseReason
from tests.harness.substrate_gate.cases import (
    CaseVariant,
    ExpectRefuse,
    Materialization,
    ReplayCase,
    SectionCell,
    SeededState,
)
from tests.harness.substrate_gate.parity import FixtureParitySource, ParityObservation

if TYPE_CHECKING:
    from collections.abc import Callable

# Project verified against S3 in the DEFECT (:20-23, :64-71).
PROJECT_GID = "1143843662099250"

# The re-warm instant; also the serving ``now`` (fresh plane age == 0).
NOW = datetime(2026, 7, 27, 15, 27, tzinfo=UTC)
_FROZEN_AT = datetime(2026, 7, 13, 0, 0, tzinfo=UTC)  # v2/offer plane freeze (14d stale)

_STALE_PLANE = "v2/offer"
_FRESH_PLANE = "fresh-rewarm"
_STALE_VALUE = 79_585.0
_FRESH_VALUE = 84_385.0
_SLA_SECONDS = 3_600  # offer freshness contract (placeholder; S2 sources the real value)

_STALE_COMPOSITION: dict[str, SectionCell] = {
    "ACTIVE": SectionCell(rows=51, value=65_585.0),
    "OPTIMIZE – Human Review": SectionCell(rows=2, value=3_100.0),
    "STAGED": SectionCell(rows=5, value=6_000.0),
    "OTHER (unchanged)": SectionCell(rows=6, value=4_900.0),
}
_FRESH_COMPOSITION: dict[str, SectionCell] = {
    "ACTIVE": SectionCell(rows=48, value=61_585.0),
    "OPTIMIZE – Human Review": SectionCell(rows=5, value=7_900.0),
    "STAGED": SectionCell(rows=7, value=10_000.0),
    "OTHER (unchanged)": SectionCell(rows=6, value=4_900.0),
}


def exemplar_one_aid() -> ArtifactId:
    """The (project, entity) address for the offer-domain exemplar."""
    return ArtifactId(project_gid=PROJECT_GID, entity_type=EntityType.OFFER)


def _stale_materialization() -> Materialization:
    return Materialization(
        plane=_STALE_PLANE,
        proof=FreshnessProof(
            built_from_live_at=_FROZEN_AT,
            content_digest="sha256:stale-79585",
            sla_seconds=_SLA_SECONDS,
        ),
        served_value=_STALE_VALUE,
        composition=_STALE_COMPOSITION,
        frame_digest="sha256:stale-79585",  # digest-consistent: this is DIVERGENCE, not CORRUPT
    )


def _fresh_materialization() -> Materialization:
    return Materialization(
        plane=_FRESH_PLANE,
        proof=FreshnessProof(
            built_from_live_at=NOW,
            content_digest="sha256:fresh-84385",
            sla_seconds=_SLA_SECONDS,
        ),
        served_value=_FRESH_VALUE,
        composition=_FRESH_COMPOSITION,
        frame_digest="sha256:fresh-84385",
    )


def exemplar_one_observation() -> ParityObservation:
    """The v1(stale)-beside-v2(fresh) parity observation for the exemplar."""
    return ParityObservation(
        aid=exemplar_one_aid(),
        v1=_stale_materialization(),
        v2=_fresh_materialization(),
    )


def exemplar_one_source() -> FixtureParitySource:
    """A parity source seeded with exemplar #1 only."""
    return FixtureParitySource([exemplar_one_observation()])


def exemplar_one_replay_case() -> ReplayCase:
    """The RC-A-2 replay case: both disagreeing copies seeded, expect REJECT DIVERGENT.

    The DEFECT's Parity Exemplar maps to RC-A-2 (RC spec :131) — two materializations
    of the same (project, entity) that disagree must be refused, not silently served.
    """
    return ReplayCase(
        case_id="exemplar-1-rc-a-2-divergent",
        predicate_id="RC-A-2",
        variant=CaseVariant.BROKEN,
        state=SeededState(
            aid=exemplar_one_aid(),
            materializations=(_stale_materialization(), _fresh_materialization()),
            now=NOW,
        ),
        expected=ExpectRefuse(reason=RefuseReason.DIVERGENT),
    )


# ============================================================================
# Exemplar #2 — CURRENT offer plane (S8-0 pre-gate recapture · O4 · additive)
# ============================================================================
# Derived from the REAL S3 artifact — 0 Asana API calls; AWS control-plane + S3
# GET/LIST only. Full provenance (probe commands, ETags, digests, torn-read guard)
# in .ledge/reviews/RECEIPT-s8-0-fixture-recapture-2026-07-30.md.
#
# Source: s3://autom8-s3/dataframes/1143843662099250/offer/{dataframe.parquet,
# watermark.json}. Snapshot instant 2026-07-30T12:24:15Z; dataframe.parquet ETag
# "de911e6885a587e09e653ec2d697211d" (sha256 da97751365…c3e7d); watermark.json ETag
# "22dfe7576e7ac5bd2da3e0749c85ad21". Torn-read guard PASSED (watermark post-dates all
# section artifacts: newest section 11:09:04Z < build 12:23:09Z < write 12:24:15Z).

# The watermark BUILD instant (watermark.json "watermark" field) — the artifact's honest
# built_from_live_at (the live-pull moment, NOT the S3 write mtime).
_WATERMARK_BUILT_FROM_LIVE_AT = datetime(2026, 7, 30, 12, 23, 9, 371507, tzinfo=UTC)
_OFFER_SLA_SECONDS = 3600  # the REAL offer freshness contract (governed freshness_sla_seconds, C8/C17 ruling 2026-07-30)

_CURRENT_PLANE = "v2/offer-current"
_CURRENT_VALUE = 80_985.0  # Σ mrr over the three offer-lifecycle sections below

# sha256 over the canonical composition json (sorted, section -> [rows, value]) — a
# genuine DRIFT TRIPWIRE: the same S3 bytes re-derive the same aggregate → same digest.
_CURRENT_DIGEST = "sha256:4e711a7a8b8a7f4b18d4beb7ef9f7dc28286d682d3e339c9a407c63de84bce65"

# The current per-section composition — the THREE offer-lifecycle sections exemplar #1
# tracked, summed straight from the S3 frame's `mrr` column grouped by `section`. NOTE
# the section name is a plain HYPHEN (U+002D) in prod; exemplar #1's fixture used an
# en-dash (U+2013). The real bytes win here (a drift tripwire keys off the true string).
_CURRENT_COMPOSITION: dict[str, SectionCell] = {
    "ACTIVE": SectionCell(rows=47, value=60_085.0),
    "OPTIMIZE - Human Review": SectionCell(rows=7, value=10_900.0),
    "STAGED": SectionCell(rows=7, value=10_000.0),
}


def exemplar_two_aid() -> ArtifactId:
    """The (project, entity) address for the current offer-plane anchor (== exemplar #1's)."""
    return ArtifactId(project_gid=PROJECT_GID, entity_type=EntityType.OFFER)


def exemplar_two_materialization() -> Materialization:
    """The CURRENT offer plane as a coherent, S3-derived materialization.

    DRIFT TRIPWIRE: served_value ``$80,985`` measured against exemplar #1's frozen
    ``$84,385`` IS the measured dark-build drift-delta = **−$3,400 (−4.03%)** over the
    interval. Per-section, mirroring the RC-A-2 ledger idiom (exemplar #1 FRESH →
    exemplar #2 CURRENT)::

        ACTIVE                    48r·$61,585 → 47r·$60,085  = −$1,500
        OPTIMIZE Human Review      5r·$7,900  →  7r·$10,900   = +$3,000  (en-dash → hyphen in prod)
        STAGED                     7r·$10,000 →  7r·$10,000   =     $0
        OTHER (unchanged)          6r·$4,900  →   (dropped)   = −$4,900  (synthetic bucket; no S3 analogue)
                                                        net    = −$3,400

    The +$1,500 real shift across the three shared sections, minus exemplar #1's $4,900
    synthetic OTHER bucket (which has no reproducible S3 analogue), composes the −$3,400
    headline delta. Provenance + the 0-Asana-call affirmation:
    ``.ledge/reviews/RECEIPT-s8-0-fixture-recapture-2026-07-30.md`` (snapshot instant
    2026-07-30T12:24:15Z; sources s3://autom8-s3/dataframes/1143843662099250/offer/).
    """
    return Materialization(
        plane=_CURRENT_PLANE,
        proof=FreshnessProof(
            built_from_live_at=_WATERMARK_BUILT_FROM_LIVE_AT,
            content_digest=_CURRENT_DIGEST,
            sla_seconds=_OFFER_SLA_SECONDS,
        ),
        served_value=_CURRENT_VALUE,
        composition=_CURRENT_COMPOSITION,
        frame_digest=_CURRENT_DIGEST,  # digest-consistent: coherent current state, NOT corrupt
    )


def exemplar_two_observation() -> ParityObservation:
    """The COHERENT current-state anchor: v1 == v2 (no divergence — a tripwire, not a wound)."""
    current = exemplar_two_materialization()
    return ParityObservation(aid=exemplar_two_aid(), v1=current, v2=current)


def exemplar_two_source() -> FixtureParitySource:
    """A parity source seeded with the current offer-plane anchor (exemplar #2 only)."""
    return FixtureParitySource([exemplar_two_observation()])


# The parity-gate enumeration point — exemplar #2 registered BESIDE exemplar #1. Net
# corpus = 22 predicates unchanged + #1 (historical wound) + #2 (current anchor).
PARITY_GATE_SOURCES: tuple[Callable[[], FixtureParitySource], ...] = (
    exemplar_one_source,
    exemplar_two_source,
)
