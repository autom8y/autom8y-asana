"""EXECUTABLE self-discrimination test (S7 · P5 · REQUIREMENT 4 · runs in CI).

Proves the harness ITSELF has teeth, TWO-SIDED:

  * a KNOWN-GOOD input is classified SERVE and a correct substrate PASSES it;
  * a KNOWN-BROKEN input is classified REJECT and a correct substrate PASSES it;
  * a substrate that SILENTLY SERVES the broken input is caught (FAIL) — the v1 wound;
  * a substrate that OVER-REFUSES the good input is caught (FAIL) — the noise side.

A runner that could not discriminate would pass all four; only a runner with teeth
produces the FAIL rows below. This is the discriminating-canary posture applied to
the harness itself: it bites ONLY on the wrong behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime

from autom8_asana.core.types import EntityType
from autom8_asana.substrate.freshness import FreshnessProof
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.serve import Provable, Refused, RefuseReason
from tests.harness.substrate_gate import (
    CaseVariant,
    ExpectRefuse,
    ExpectServe,
    Materialization,
    OverRefuseSubstrate,
    ReferenceSubstrate,
    ReplayCase,
    ReplayRunner,
    ResultStatus,
    SectionCell,
    SeededState,
    SilentServeSubstrate,
    Verdict,
)

_NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def _aid() -> ArtifactId:
    return ArtifactId(project_gid="1143843662099250", entity_type=EntityType.OFFER)


def _known_good() -> ReplayCase:
    """A fresh, single-source, plane-correct input — the harness must classify SERVE."""
    proof = FreshnessProof(built_from_live_at=_NOW, content_digest="d-good", sla_seconds=3_600)
    materialization = Materialization(
        plane="v2/offer",
        proof=proof,
        served_value=84_385.0,
        composition={"ALL": SectionCell(rows=1, value=84_385.0)},
        frame_digest="d-good",
    )
    return ReplayCase(
        case_id="synthetic-known-good",
        predicate_id="RC-A-1",
        variant=CaseVariant.GOOD,
        state=SeededState(aid=_aid(), materializations=(materialization,), now=_NOW),
        expected=ExpectServe(value=84_385.0, plane="v2/offer"),
    )


def _known_broken() -> ReplayCase:
    """Two disagreeing copies of the same (project, entity) — the harness must classify REJECT."""
    stale = Materialization(
        plane="v2/offer",
        proof=FreshnessProof(
            built_from_live_at=datetime(2026, 7, 13, tzinfo=UTC),
            content_digest="d-stale",
            sla_seconds=3_600,
        ),
        served_value=79_585.0,
        composition={"ALL": SectionCell(rows=58, value=79_585.0)},
        frame_digest="d-stale",
    )
    fresh = Materialization(
        plane="fresh-rewarm",
        proof=FreshnessProof(built_from_live_at=_NOW, content_digest="d-fresh", sla_seconds=3_600),
        served_value=84_385.0,
        composition={"ALL": SectionCell(rows=60, value=84_385.0)},
        frame_digest="d-fresh",
    )
    return ReplayCase(
        case_id="synthetic-known-broken",
        predicate_id="RC-A-2",
        variant=CaseVariant.BROKEN,
        state=SeededState(aid=_aid(), materializations=(stale, fresh), now=_NOW),
        expected=ExpectRefuse(reason=RefuseReason.DIVERGENT),
    )


def test_known_good_input_classified_serve_and_reference_passes() -> None:
    result = ReplayRunner(ReferenceSubstrate()).run_case(_known_good())
    assert result.expected_verdict is Verdict.SERVE
    assert result.status is ResultStatus.PASS
    assert isinstance(result.observed, Provable)


def test_known_broken_input_classified_reject_and_reference_refuses() -> None:
    result = ReplayRunner(ReferenceSubstrate()).run_case(_known_broken())
    assert result.expected_verdict is Verdict.REJECT
    assert result.status is ResultStatus.PASS
    assert isinstance(result.observed, Refused)
    assert result.observed.reason is RefuseReason.DIVERGENT


def test_teeth_silent_serve_of_broken_input_is_caught() -> None:
    result = ReplayRunner(SilentServeSubstrate()).run_case(_known_broken())
    assert result.status is ResultStatus.FAIL
    assert "SILENT WRONG-SERVE" in result.detail


def test_teeth_over_refusal_of_good_input_is_caught() -> None:
    result = ReplayRunner(OverRefuseSubstrate()).run_case(_known_good())
    assert result.status is ResultStatus.FAIL
    assert "OVER-REFUSAL" in result.detail


def test_two_sided_discrimination_matrix() -> None:
    """The whole teeth proof in one table: correct passes both sides; each broken is caught."""
    good = _known_good()
    broken = _known_broken()

    reference = ReplayRunner(ReferenceSubstrate())
    assert reference.run_case(good).status is ResultStatus.PASS
    assert reference.run_case(broken).status is ResultStatus.PASS

    assert ReplayRunner(SilentServeSubstrate()).run_case(broken).status is ResultStatus.FAIL
    assert ReplayRunner(OverRefuseSubstrate()).run_case(good).status is ResultStatus.FAIL
