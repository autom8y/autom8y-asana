"""Corpus scaffold coverage (S7 · P5) — the case-authoring surface is corpus-ready.

Asserts the schema is expressive enough for all 22 RC-A..F predicates: each predicate
id maps to >=1 slot, broken-variant slots expect REJECT, and every WORKED case
discriminates correctly under the reference substrate. The pending slots are the clean
template the qa-adversary authors against next.
"""

from __future__ import annotations

from autom8_asana.substrate.serve import RefuseReason
from tests.harness.substrate_gate import (
    ALL_PREDICATE_IDS,
    CaseVariant,
    ExpectRefuse,
    ExpectServe,
    ReferenceSubstrate,
    ReplayRunner,
    ResultStatus,
    covered_predicate_ids,
    filled_cases,
    filled_slots,
    pending_slots,
)


def test_all_22_predicates_have_at_least_one_slot() -> None:
    assert len(ALL_PREDICATE_IDS) == 22
    assert len(set(ALL_PREDICATE_IDS)) == 22
    assert covered_predicate_ids() == set(ALL_PREDICATE_IDS)


def test_every_broken_filled_slot_expects_reject() -> None:
    for slot in filled_slots():
        assert (
            slot.build is not None
        )  # filled_slots() guarantees this; narrows for the type checker
        case = slot.build()
        if slot.variant is CaseVariant.BROKEN:
            assert isinstance(case.expected, ExpectRefuse), slot.predicate_id
        else:
            assert isinstance(case.expected, ExpectServe), slot.predicate_id


def test_pending_slots_are_declared_broken_reject_placeholders() -> None:
    pending = pending_slots()
    assert pending, "expected some pending slots for the qa-adversary to author"
    for slot in pending:
        assert slot.build is None
        assert slot.variant is CaseVariant.BROKEN  # broken-variant slots carry expected=REJECT


def test_worked_cases_discriminate_under_reference_substrate() -> None:
    runner = ReplayRunner(ReferenceSubstrate())
    results = runner.run(filled_cases())
    failures = [(r.case_id, r.detail) for r in results if r.status is not ResultStatus.PASS]
    assert not failures, failures


def test_worked_corpus_spans_serve_and_every_closed_refuse_reason() -> None:
    reasons: set[RefuseReason] = set()
    served = False
    for case in filled_cases():
        if isinstance(case.expected, ExpectRefuse):
            reasons.add(case.expected.reason)
        else:
            served = True
    assert served, "worked corpus must include at least one SERVE case"
    assert reasons == {
        RefuseReason.STALE,
        RefuseReason.CORRUPT,
        RefuseReason.MISSING,
        RefuseReason.DIVERGENT,
    }


def test_predicate_id_on_each_slot_is_a_known_predicate() -> None:
    known = set(ALL_PREDICATE_IDS)
    for case in filled_cases():
        assert case.predicate_id in known
