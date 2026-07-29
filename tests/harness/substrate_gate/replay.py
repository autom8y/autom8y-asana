"""Replay runner (S7 · P5) — executes fixture cases against a substrate-under-test.

REQUIREMENT 1 of the S7 build: artifacts + FreshnessProofs in, expected verdict out
(served-value match OR Refused with reason). The runner is the harness's TEETH: it
classifies each case PASS/FAIL by comparing what the injected ``HarnessSubstrate``
actually served against the case's expected verdict.

The teeth are TWO-SIDED by construction (discriminating-canary posture):
  * a BROKEN case whose substrate SILENTLY SERVES (instead of refusing) → FAIL
    (the exact v1 wound: a stale/divergent number served under a green proof);
  * a GOOD case whose substrate WRONGLY REFUSES (alarm noise) → FAIL.
A substrate that does the right thing on both sides is the only one that passes.

The runner consumes the frozen ``ServedNumber`` sum type through an exhaustive
``match`` with ``assert_never`` — the RC-C-serving [H15] honest floor: a bare
attribute access on an un-handled arm is a type error.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, assert_never

from autom8_asana.substrate.serve import Provable, Refused
from tests.harness.substrate_gate.cases import (
    CaseVariant,
    ExpectRefuse,
    ExpectServe,
    HarnessRefusePayload,
    Verdict,
    verdict_of,
)
from tests.harness.substrate_gate.frame_codec import decode_frame

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from autom8_asana.substrate.serve import ServedNumber
    from tests.harness.substrate_gate.cases import (
        Expected,
        HarnessSubstrate,
        ReplayCase,
        SectionCell,
        SunsetBreach,
    )

_VALUE_ABS_TOL = 0.005


class ResultStatus(Enum):
    """Did the substrate's served number match the case's expected verdict?"""

    PASS = "pass"  # observed matched expected
    FAIL = "fail"  # mismatch — the harness caught a wrong behavior (teeth bit)


@dataclass(frozen=True, slots=True)
class CaseResult:
    """The outcome of replaying one case against the substrate-under-test.

    ``expected_verdict`` is the harness's own classification of the input (SERVE for
    a good input, REJECT for a broken one); ``status`` is whether the substrate met
    it. ``observed`` is the frozen ``ServedNumber`` the substrate actually produced.
    """

    case_id: str
    predicate_id: str
    variant: CaseVariant
    expected_verdict: Verdict
    observed: ServedNumber
    status: ResultStatus
    detail: str


def classify(observed: ServedNumber, expected: Expected) -> tuple[ResultStatus, str]:
    """Compare a served number against an expectation → (status, human detail).

    Exhaustive over both the ``Expected`` arms and the frozen ``ServedNumber`` arms.
    """
    if isinstance(expected, ExpectServe):
        return _classify_expect_serve(observed, expected)
    if isinstance(expected, ExpectRefuse):
        return _classify_expect_refuse(observed, expected)
    assert_never(expected)


def _composition_matches(
    observed: Mapping[str, SectionCell], expected: Mapping[str, SectionCell]
) -> bool:
    """Per-section match: same section set, same rows, values within tolerance."""
    if set(observed) != set(expected):
        return False
    return all(
        observed[name].rows == expected[name].rows
        and math.isclose(observed[name].value, expected[name].value, abs_tol=_VALUE_ABS_TOL)
        for name in expected
    )


def _classify_expect_serve(
    observed: ServedNumber, expected: ExpectServe
) -> tuple[ResultStatus, str]:
    match observed:
        case Provable(frame=frame):
            content = decode_frame(frame)
            value_ok = math.isclose(content.served_value, expected.value, abs_tol=_VALUE_ABS_TOL)
            if not value_ok or content.plane != expected.plane:
                return (
                    ResultStatus.FAIL,
                    f"served-value mismatch: got {content.served_value}@{content.plane}, "
                    f"expected {expected.value}@{expected.plane}",
                )
            if expected.composition is not None and not _composition_matches(
                content.composition, expected.composition
            ):
                return (
                    ResultStatus.FAIL,
                    "served-composition mismatch: right total on the wrong per-section "
                    f"content (plane {content.plane}) — the zero-net-shift wound class",
                )
            return ResultStatus.PASS, f"served {content.served_value} on plane {content.plane}"
        case Refused(reason=reason):
            return (
                ResultStatus.FAIL,
                f"OVER-REFUSAL: expected SERVE {expected.value}@{expected.plane}, "
                f"got REFUSE {reason.value}",
            )
        case _:
            assert_never(observed)


def _observed_sunset_breach(observed: Refused) -> SunsetBreach | None:
    """The C13 marker if the payload carries one (harness-additive), else None."""
    detail = observed.detail
    if isinstance(detail, HarnessRefusePayload):
        return detail.sunset_breach
    return None


def _classify_expect_refuse(
    observed: ServedNumber, expected: ExpectRefuse
) -> tuple[ResultStatus, str]:
    match observed:
        case Refused(reason=reason):
            if reason is not expected.reason:
                return (
                    ResultStatus.FAIL,
                    f"wrong refuse reason: got {reason.value}, expected {expected.reason.value}",
                )
            if expected.sunset_breach is not None:
                observed_breach = _observed_sunset_breach(observed)
                if observed_breach != expected.sunset_breach:
                    return (
                        ResultStatus.FAIL,
                        "sunset_breach marker missing/mismatched (TDD §11 C13): "
                        f"got {observed_breach}, expected {expected.sunset_breach} — "
                        "a sunset-breach STALE must be machine-distinguishable from age-STALE",
                    )
            return ResultStatus.PASS, f"refused {reason.value} as expected"
        case Provable(frame=frame):
            content = decode_frame(frame)
            return (
                ResultStatus.FAIL,
                f"SILENT WRONG-SERVE: served {content.served_value}@{content.plane}, "
                f"expected REFUSE {expected.reason.value}",
            )
        case _:
            assert_never(observed)


class ReplayRunner:
    """Drives a corpus of ``ReplayCase`` through an injected ``HarnessSubstrate``."""

    def __init__(self, substrate: HarnessSubstrate) -> None:
        self._substrate = substrate

    def run_case(self, case: ReplayCase) -> CaseResult:
        """Serve one case's INPUT state and classify the result (blind to expected)."""
        observed = self._substrate.serve(case.state)
        status, detail = classify(observed, case.expected)
        return CaseResult(
            case_id=case.case_id,
            predicate_id=case.predicate_id,
            variant=case.variant,
            expected_verdict=verdict_of(case.expected),
            observed=observed,
            status=status,
            detail=detail,
        )

    def run(self, cases: Iterable[ReplayCase]) -> list[CaseResult]:
        """Replay every case; results preserve input order."""
        return [self.run_case(case) for case in cases]
