"""Substrate cutover-gate harness (S7 · P5 · WAVE-2 dark build).

The S8 machinery — scaffolded here, EXECUTED at S8 (not now). Two runners:

  * ``ReplayRunner`` — replays fixture cases against an injected substrate-under-test
    (artifacts + FreshnessProofs in → served-value match OR Refused-with-reason out),
    with two-sided teeth (silent-serve of a broken input FAILS; over-refusal of a good
    input FAILS).
  * ``ParityRunner`` — computes v2-beside-v1 and emits a per-divergence ledger carrying
    the FROZEN RC-A-2 ``RefusePayload`` observable AS LANDED. Its live path is DARK
    (``PacedLiveParitySource``, guarded by ``LiveParityNotArmedError``) and composes v1's
    pacing controllers directly (RC-E-4).

This is a corpus-ready SCAFFOLD; the qa-adversary authors the acceptance corpus against
it. It makes NO v2-parity claim — v2's serve does not exist until S5/S8. See
``corpus.ALL_PREDICATE_IDS`` for the 22-predicate authoring surface.
"""

from __future__ import annotations

from tests.harness.substrate_gate.cases import (
    CaseVariant,
    Expected,
    ExpectRefuse,
    ExpectServe,
    HarnessSubstrate,
    Materialization,
    ReplayCase,
    SectionCell,
    SeededState,
    Verdict,
    verdict_of,
)
from tests.harness.substrate_gate.corpus import (
    ALL_PREDICATE_IDS,
    CORPUS_SLOTS,
    CaseSlot,
    covered_predicate_ids,
    filled_cases,
    filled_slots,
    pending_slots,
)
from tests.harness.substrate_gate.divergence import (
    divergence_payload,
    diverges,
    explain_divergence,
    order_by_age,
)
from tests.harness.substrate_gate.frame_codec import FrameContent, decode_frame, encode_frame
from tests.harness.substrate_gate.parity import (
    DivergenceLedgerEntry,
    FixtureParitySource,
    LiveParityNotArmedError,
    PacedLiveParitySource,
    ParityObservation,
    ParityRunner,
    ParitySource,
    display_key,
)
from tests.harness.substrate_gate.reference import (
    OverRefuseSubstrate,
    ReferenceSubstrate,
    SilentServeSubstrate,
)
from tests.harness.substrate_gate.replay import CaseResult, ReplayRunner, ResultStatus, classify

__all__ = [
    "ALL_PREDICATE_IDS",
    "CORPUS_SLOTS",
    "CaseResult",
    "CaseSlot",
    "CaseVariant",
    "DivergenceLedgerEntry",
    "Expected",
    "ExpectRefuse",
    "ExpectServe",
    "FixtureParitySource",
    "FrameContent",
    "HarnessSubstrate",
    "LiveParityNotArmedError",
    "Materialization",
    "OverRefuseSubstrate",
    "PacedLiveParitySource",
    "ParityObservation",
    "ParityRunner",
    "ParitySource",
    "ReferenceSubstrate",
    "ReplayCase",
    "ReplayRunner",
    "ResultStatus",
    "SectionCell",
    "SeededState",
    "SilentServeSubstrate",
    "Verdict",
    "classify",
    "covered_predicate_ids",
    "decode_frame",
    "display_key",
    "diverges",
    "divergence_payload",
    "encode_frame",
    "explain_divergence",
    "filled_cases",
    "filled_slots",
    "order_by_age",
    "pending_slots",
    "verdict_of",
]
