"""Parity exemplar #1 (S7 · P5) — the ``$84,385``-vs-``$79,585`` divergence.

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
