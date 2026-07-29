"""Replay-runner + reference-substrate unit tests (S7 · P5).

Covers each gate branch of the reference oracle (MISSING → DIVERGENT → CORRUPT →
STALE → sunset → Provable), the two-sided classifier arms, and the frame codec.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.substrate.freshness import FreshnessProof
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.serve import Provable, Refused, RefuseReason
from tests.harness.substrate_gate import (
    CaseVariant,
    ExpectRefuse,
    ExpectServe,
    FrameContent,
    Materialization,
    ReferenceSubstrate,
    ReplayCase,
    ReplayRunner,
    ResultStatus,
    SectionCell,
    SeededState,
    classify,
    decode_frame,
    encode_frame,
)

_NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def _aid() -> ArtifactId:
    return ArtifactId(project_gid="1", entity_type=EntityType.OFFER)


def _mat(
    plane: str,
    value: float,
    built_at: datetime,
    *,
    digest: str = "d",
    frame_digest: str | None = None,
    sla: int = 3_600,
) -> Materialization:
    return Materialization(
        plane=plane,
        proof=FreshnessProof(built_from_live_at=built_at, content_digest=digest, sla_seconds=sla),
        served_value=value,
        composition={"ALL": SectionCell(rows=1, value=value)},
        frame_digest=frame_digest if frame_digest is not None else digest,
    )


def _serve(state: SeededState) -> object:
    return ReferenceSubstrate().serve(state)


def test_reference_serves_fresh_single_source() -> None:
    state = SeededState(aid=_aid(), materializations=(_mat("v2/offer", 80_000.0, _NOW),), now=_NOW)
    served = _serve(state)
    assert isinstance(served, Provable)
    content = decode_frame(served.frame)
    assert content.served_value == pytest.approx(80_000.0)
    assert content.plane == "v2/offer"


def test_reference_refuses_missing_when_no_materializations() -> None:
    state = SeededState(aid=_aid(), materializations=(), now=_NOW)
    served = _serve(state)
    assert isinstance(served, Refused)
    assert served.reason is RefuseReason.MISSING


def test_reference_refuses_stale_when_age_exceeds_sla() -> None:
    state = SeededState(
        aid=_aid(),
        materializations=(_mat("v2/offer", 80_000.0, _NOW - timedelta(seconds=7_200)),),
        now=_NOW,
    )
    served = _serve(state)
    assert isinstance(served, Refused)
    assert served.reason is RefuseReason.STALE


def test_reference_refuses_corrupt_on_digest_mismatch() -> None:
    state = SeededState(
        aid=_aid(),
        materializations=(_mat("v2/offer", 80_000.0, _NOW, digest="proven", frame_digest="other"),),
        now=_NOW,
    )
    served = _serve(state)
    assert isinstance(served, Refused)
    assert served.reason is RefuseReason.CORRUPT


def test_reference_refuses_divergent_on_disagreeing_copies() -> None:
    state = SeededState(
        aid=_aid(),
        materializations=(
            _mat("v2/offer", 79_585.0, datetime(2026, 7, 13, tzinfo=UTC), digest="a"),
            _mat("fresh", 84_385.0, _NOW, digest="b"),
        ),
        now=_NOW,
    )
    served = _serve(state)
    assert isinstance(served, Refused)
    assert served.reason is RefuseReason.DIVERGENT
    # the divergence payload carries both planes' ages
    assert set(served.detail.absolute_age) == {"v2/offer", "fresh"}
    assert served.detail.magnitude == pytest.approx(4_800.0)


def test_reference_refuses_bridge_past_sunset() -> None:
    state = SeededState(
        aid=_aid(),
        materializations=(_mat("legacy-bridge", 80_000.0, _NOW),),
        now=_NOW,
        sunset_after=_NOW - timedelta(days=1),
    )
    served = _serve(state)
    assert isinstance(served, Refused)
    assert served.reason is RefuseReason.STALE


def test_reference_serves_when_sunset_in_future() -> None:
    state = SeededState(
        aid=_aid(),
        materializations=(_mat("v2/offer", 80_000.0, _NOW),),
        now=_NOW,
        sunset_after=_NOW + timedelta(days=30),
    )
    assert isinstance(_serve(state), Provable)


def test_classify_over_refusal_fails() -> None:
    # expected SERVE, observed Refused -> FAIL (over-refusal)
    refused = ReferenceSubstrate().serve(SeededState(aid=_aid(), materializations=(), now=_NOW))
    status, detail = classify(refused, ExpectServe(value=1.0, plane="v2/offer"))
    assert status is ResultStatus.FAIL
    assert "OVER-REFUSAL" in detail


def test_classify_wrong_reason_fails() -> None:
    refused = ReferenceSubstrate().serve(
        SeededState(aid=_aid(), materializations=(), now=_NOW)
    )  # MISSING
    status, detail = classify(refused, ExpectRefuse(reason=RefuseReason.STALE))
    assert status is ResultStatus.FAIL
    assert "wrong refuse reason" in detail


def test_classify_value_mismatch_fails() -> None:
    provable = ReferenceSubstrate().serve(
        SeededState(aid=_aid(), materializations=(_mat("v2/offer", 80_000.0, _NOW),), now=_NOW)
    )
    status, detail = classify(provable, ExpectServe(value=99_999.0, plane="v2/offer"))
    assert status is ResultStatus.FAIL
    assert "served-value mismatch" in detail


def test_frame_codec_roundtrip() -> None:
    content = FrameContent(
        served_value=84_385.0,
        plane="v2/offer",
        composition={"ACTIVE": SectionCell(rows=48, value=61_585.0)},
    )
    decoded = decode_frame(encode_frame(content))
    assert decoded.served_value == pytest.approx(84_385.0)
    assert decoded.plane == "v2/offer"
    assert decoded.composition["ACTIVE"].rows == 48
    assert decoded.composition["ACTIVE"].value == pytest.approx(61_585.0)


def test_runner_run_preserves_order_and_metadata() -> None:
    good = ReplayCase(
        case_id="g",
        predicate_id="RC-A-1",
        variant=CaseVariant.GOOD,
        state=SeededState(aid=_aid(), materializations=(_mat("v2/offer", 1.0, _NOW),), now=_NOW),
        expected=ExpectServe(value=1.0, plane="v2/offer"),
    )
    bad = ReplayCase(
        case_id="b",
        predicate_id="RC-A-3",
        variant=CaseVariant.BROKEN,
        state=SeededState(aid=_aid(), materializations=(), now=_NOW),
        expected=ExpectRefuse(reason=RefuseReason.MISSING),
    )
    results = ReplayRunner(ReferenceSubstrate()).run([good, bad])
    assert [r.case_id for r in results] == ["g", "b"]
    assert all(r.status is ResultStatus.PASS for r in results)
