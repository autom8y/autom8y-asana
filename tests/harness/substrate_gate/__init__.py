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

This is a corpus-ready harness; the qa-adversary authored the acceptance corpus against
it. v2's serve now EXISTS (``substrate.serve``, landed PR #286) — this harness EXECUTES
against it at S8. Until it runs, the harness itself makes NO v2-parity claim: a green
corpus here is the acceptance surface, not evidence v2 has been served. See
``corpus.ALL_PREDICATE_IDS`` for the 22-predicate surface.
"""

from __future__ import annotations

from tests.harness.substrate_gate.budget import (
    BudgetedPacedFetcher,
    ParityBudgetExhausted,
    PerDayBudgetLedger,
)
from tests.harness.substrate_gate.cases import (
    CaseVariant,
    Expected,
    ExpectRefuse,
    ExpectServe,
    HarnessRefusePayload,
    HarnessSubstrate,
    Materialization,
    ReplayCase,
    SectionCell,
    SeededState,
    SunsetBreach,
    Verdict,
    verdict_of,
)
from tests.harness.substrate_gate.corpus import (
    ALL_PREDICATE_IDS,
    CONSTRUCTION_ALTITUDE_IDS,
    CORPUS_SLOTS,
    SABOTEUR_SIDE_ONLY_IDS,
    CaseSlot,
    construction_slots,
    covered_predicate_ids,
    filled_cases,
    filled_slots,
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
    ParityOutboundError,
    ParityRunner,
    ParitySource,
    display_key,
    get_process_fetcher,
)
from tests.harness.substrate_gate.reference import (
    OverRefuseSubstrate,
    ReferenceSubstrate,
    SilentServeSubstrate,
)
from tests.harness.substrate_gate.replay import CaseResult, ReplayRunner, ResultStatus, classify

__all__ = [
    "ALL_PREDICATE_IDS",
    "CONSTRUCTION_ALTITUDE_IDS",
    "CORPUS_SLOTS",
    "SABOTEUR_SIDE_ONLY_IDS",
    "BudgetedPacedFetcher",
    "CaseResult",
    "CaseSlot",
    "CaseVariant",
    "DivergenceLedgerEntry",
    "Expected",
    "ExpectRefuse",
    "ExpectServe",
    "FixtureParitySource",
    "FrameContent",
    "HarnessRefusePayload",
    "HarnessSubstrate",
    "LiveParityNotArmedError",
    "Materialization",
    "OverRefuseSubstrate",
    "PacedLiveParitySource",
    "ParityBudgetExhausted",
    "ParityObservation",
    "ParityOutboundError",
    "ParityRunner",
    "ParitySource",
    "PerDayBudgetLedger",
    "ReferenceSubstrate",
    "ReplayCase",
    "ReplayRunner",
    "ResultStatus",
    "SectionCell",
    "SeededState",
    "SilentServeSubstrate",
    "SunsetBreach",
    "Verdict",
    "classify",
    "construction_slots",
    "covered_predicate_ids",
    "decode_frame",
    "display_key",
    "diverges",
    "divergence_payload",
    "encode_frame",
    "explain_divergence",
    "filled_cases",
    "filled_slots",
    "get_process_fetcher",
    "order_by_age",
    "verdict_of",
]
