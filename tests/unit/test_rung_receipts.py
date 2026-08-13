"""Tests for the RUNG E limb (a) receipt schema and join query (EX-4).

Covers the four exit criteria of shape §EX-4:
  1. a receipt schema limb (a) can consume mechanically, demonstrated by a
     query returning a REAL receipt over real delivery telemetry;
  2. the two ladders (RUNG-4, RUNG-E) are separably observable (FS-5);
  3. the join has two-sided teeth (bites on "no human assembled it");
  4. the limb (a) aggregate requires two machine-generated occurrences.

The real fixture is an own-hands read-only CloudWatch census; see
``tests/fixtures/rung_receipts/PROVENANCE.md``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from autom8_asana.observability.rung_receipts import (
    RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA,
    DeliveryOccurrenceReceipt,
    join_occurrences,
    observe_limb_a,
    run_query,
)
from autom8_asana.observability.rung_receipts.schema import (
    Assembler,
    DeliveryReceipt,
    GenerationReceipt,
    LimbAStatus,
    NotObservableReason,
    Rung4Status,
    RungEObservability,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "rung_receipts"


def _load_jsonl(name: str) -> list[dict]:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# --------------------------------------------------------------------------
# Exit criterion 1 — a query returning a REAL receipt over real telemetry
# --------------------------------------------------------------------------
class TestRealCensusQuery:
    """The join query over the 15 real ASR delivery events."""

    def test_query_returns_real_receipts_but_limb_a_not_yet_observed(self) -> None:
        events = _load_jsonl("asr_live_delivery_census.jsonl")
        observation = run_query(events)

        limb_a = observation["rung_e_limb_a"]
        # 15 real delivered invocations -> 15 occurrence receipts.
        assert len(limb_a["receipts"]) == 15
        # Real readouts ARE being delivered, yet limb (a) is NOT met: no
        # delivery has a joined generation receipt attesting machine-authorship.
        assert limb_a["status"] == LimbAStatus.NOT_YET_OBSERVED.value
        assert limb_a["observable_occurrences"] == 0
        assert limb_a["required_occurrences"] == 2

    def test_every_real_occurrence_is_generation_absent(self) -> None:
        events = _load_jsonl("asr_live_delivery_census.jsonl")
        observation = run_query(events)
        for receipt in observation["rung_e_limb_a"]["receipts"]:
            assert receipt["generation"] is None
            assert receipt["rung_e_limb_a_attestation"] == (RungEObservability.NOT_OBSERVABLE.value)
            assert receipt["rung_e_not_observable_reason"] == (
                NotObservableReason.GENERATION_PROVENANCE_ABSENT.value
            )

    def test_real_readout_deliveries_do_not_shortcut_to_observable(self) -> None:
        """A report_success delivery is NOT a generation receipt.

        Three real occurrences carry block_count 42 / report_success. They are
        real readouts, but delivery outcome alone must not clear limb (a) --
        report_posted is silent on authorship.
        """
        events = _load_jsonl("asr_live_delivery_census.jsonl")
        receipts = observe_limb_a(
            join_occurrences([e for e in events if e["event"] == "report_posted"], [])
        ).receipts
        readouts = [r for r in receipts if r.delivery and r.delivery.outcome.value == "readout"]
        assert len(readouts) == 3  # real count from the census
        for r in readouts:
            assert r.rung_e_limb_a_attestation is RungEObservability.NOT_OBSERVABLE


# --------------------------------------------------------------------------
# Exit criterion 2 — FS-5: the two ladders are separably observable
# --------------------------------------------------------------------------
class TestFS5Separability:
    """RUNG-4 and RUNG-E carry separate lines; no signal collapses them."""

    def test_receipt_carries_both_ladders_as_independent_fields(self) -> None:
        fields = DeliveryOccurrenceReceipt.__dataclass_fields__
        assert "rung_e_limb_a_attestation" in fields
        assert "rung_4_attestation" in fields

    def test_rung_4_is_never_derived_from_telemetry(self) -> None:
        """Making RUNG-E observable must leave RUNG-4 untouched."""
        events = _load_jsonl("readout_with_machine_generation.jsonl")
        observation = run_query(events)
        # RUNG-E flips to satisfied...
        assert observation["rung_e_limb_a"]["status"] == LimbAStatus.SATISFIED.value
        # ...while RUNG-4 stays at the felt/operator-only sentinel.
        assert observation["rung_4"]["status"] == (Rung4Status.UNATTESTED_FELT_OPERATOR_ONLY.value)
        for receipt in observation["rung_e_limb_a"]["receipts"]:
            assert receipt["rung_4_attestation"] == (
                Rung4Status.UNATTESTED_FELT_OPERATOR_ONLY.value
            )

    def test_observation_has_no_combined_engagement_field(self) -> None:
        """No emitted signal may collapse the two ladders (shape §EX-4 must-not)."""
        events = _load_jsonl("asr_live_delivery_census.jsonl")
        observation = run_query(events)
        top_keys = set(observation.keys())
        assert top_keys == {"rung_e_limb_a", "rung_4"}
        flat = json.dumps(observation).lower()
        for banned in ("engagement", "combined", "total_engagement", "overall_rung"):
            assert banned not in flat

    def test_json_schema_forbids_additional_properties(self) -> None:
        """The wire schema pins both ladders and bans a combined field."""
        props = RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA["properties"]
        assert "rung_e_limb_a_attestation" in props
        assert "rung_4_attestation" in props
        assert RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA["additionalProperties"] is False
        assert props["rung_4_attestation"]["enum"] == ["unattested_felt_operator_only"]


# --------------------------------------------------------------------------
# Exit criterion 3 — two-sided teeth on "no human assembled it"
# --------------------------------------------------------------------------
class TestTeeth:
    """The join bites on authorship, not on presence."""

    def _occ(self, human_in_loop: bool, assembler: str = "machine") -> DeliveryOccurrenceReceipt:
        delivery = {
            "event": "report_posted",
            "invocation_id": "T-1",
            "channel": "#account-health",
            "block_count": 42,
            "abort_reason": "report_success",
            "timestamp": "2026-08-13T00:00:00Z",
        }
        generation = {
            "event": "report_generated",
            "invocation_id": "T-1",
            "assembled_by": assembler,
            "human_in_loop": human_in_loop,
            "content_hash": "sha256:abc",
            "block_count": 42,
            "generated_at": "2026-08-13T00:00:00Z",
        }
        return join_occurrences([delivery], [generation])[0]

    def test_machine_generation_no_human_is_observable(self) -> None:
        occ = self._occ(human_in_loop=False, assembler="machine")
        assert occ.rung_e_limb_a_attestation is RungEObservability.OBSERVABLE
        assert occ.rung_e_not_observable_reason is None

    def test_human_in_loop_is_not_observable(self) -> None:
        """Same delivery, generation present, but a human was in the loop."""
        occ = self._occ(human_in_loop=True, assembler="machine")
        assert occ.rung_e_limb_a_attestation is RungEObservability.NOT_OBSERVABLE
        assert occ.rung_e_not_observable_reason is NotObservableReason.HUMAN_IN_LOOP

    def test_assembled_by_human_is_not_observable(self) -> None:
        occ = self._occ(human_in_loop=False, assembler="human")
        assert occ.rung_e_limb_a_attestation is RungEObservability.NOT_OBSERVABLE
        assert occ.rung_e_not_observable_reason is NotObservableReason.ASSEMBLED_BY_HUMAN

    def test_block_count_mismatch_is_not_observable(self) -> None:
        """A generated artifact of a DIFFERENT length cannot pass.

        The delivery carries no content_hash (the live report_posted shape), so
        clause 4a is unattested and the mismatch is caught on clause 4b under its
        OWN reason BLOCK_COUNT_MISMATCH — not the pre-CC-1 CONTENT_HASH_MISMATCH
        mislabel (no hash was ever compared here)."""
        delivery = {
            "event": "report_posted",
            "invocation_id": "T-2",
            "channel": "#account-health",
            "block_count": 42,
            "abort_reason": "report_success",
            "timestamp": "2026-08-13T00:00:00Z",
        }
        generation = {
            "event": "report_generated",
            "invocation_id": "T-2",
            "assembled_by": "machine",
            "human_in_loop": False,
            "content_hash": "sha256:abc",
            "block_count": 7,  # != delivered 42
            "generated_at": "2026-08-13T00:00:00Z",
        }
        occ = join_occurrences([delivery], [generation])[0]
        assert occ.rung_e_limb_a_attestation is RungEObservability.NOT_OBSERVABLE
        assert occ.rung_e_not_observable_reason is NotObservableReason.BLOCK_COUNT_MISMATCH


# --------------------------------------------------------------------------
# Join integrity + limb (a) aggregation
# --------------------------------------------------------------------------
class TestJoinIntegrity:
    def test_generation_cannot_clear_a_different_invocation(self) -> None:
        """invocation_id is the sole match key; no cross-occurrence bleed."""
        delivery = {
            "event": "report_posted",
            "invocation_id": "X",
            "channel": "#account-health",
            "block_count": 42,
            "abort_reason": "report_success",
            "timestamp": "2026-08-13T00:00:00Z",
        }
        generation_for_Y = {
            "event": "report_generated",
            "invocation_id": "Y",  # different tick
            "assembled_by": "machine",
            "human_in_loop": False,
            "content_hash": "sha256:abc",
            "block_count": 42,
            "generated_at": "2026-08-13T00:00:00Z",
        }
        receipts = join_occurrences([delivery], [generation_for_Y])
        assert len(receipts) == 1  # only the delivered invocation X
        assert receipts[0].invocation_id == "X"
        assert receipts[0].generation is None
        assert receipts[0].rung_e_limb_a_attestation is RungEObservability.NOT_OBSERVABLE

    def test_generation_without_delivery_is_not_an_occurrence(self) -> None:
        """A generation event alone is not a delivery occurrence."""
        generation = {
            "event": "report_generated",
            "invocation_id": "Z",
            "assembled_by": "machine",
            "human_in_loop": False,
            "content_hash": "sha256:abc",
            "block_count": 42,
            "generated_at": "2026-08-13T00:00:00Z",
        }
        assert join_occurrences([], [generation]) == []

    def test_limb_a_requires_two_distinct_observable_occurrences(self) -> None:
        one = _load_jsonl("readout_with_machine_generation.jsonl")
        # Keep just the first tick (delivery + its generation) -> 1 observable.
        first_tick = [e for e in one if e["invocation_id"] == "SYNTH-gen-0001"]
        obs_one = observe_limb_a(
            join_occurrences(
                [e for e in first_tick if e["event"] == "report_posted"],
                [e for e in first_tick if e["event"] == "report_generated"],
            )
        )
        assert obs_one.status is LimbAStatus.NOT_YET_OBSERVED
        assert obs_one.observable_occurrences == 1

        # Both ticks -> 2 observable -> SATISFIED.
        obs_two = observe_limb_a(
            join_occurrences(
                [e for e in one if e["event"] == "report_posted"],
                [e for e in one if e["event"] == "report_generated"],
            )
        )
        assert obs_two.status is LimbAStatus.SATISFIED
        assert obs_two.observable_occurrences == 2


class TestReceiptProjection:
    def test_receipt_round_trips_to_json(self) -> None:
        delivery = DeliveryReceipt.from_event(
            {
                "invocation_id": "A",
                "channel": "#account-health",
                "block_count": 42,
                "abort_reason": "report_success",
                "timestamp": "2026-08-13T00:00:00Z",
            }
        )
        generation = GenerationReceipt.from_event(
            {
                "invocation_id": "A",
                "assembled_by": "machine",
                "human_in_loop": False,
                "content_hash": "sha256:abc",
                "block_count": 42,
                "generated_at": "2026-08-13T00:00:00Z",
            }
        )
        assert delivery.outcome.value == "readout"
        assert generation.assembled_by is Assembler.MACHINE
        occ = join_occurrences(
            [
                {
                    "event": "report_posted",
                    **delivery.__dict__,
                    "abort_reason": "report_success",
                    "timestamp": delivery.delivered_at,
                }
            ],
            [],
        )
        # Round-trip via to_dict must be json-serialisable.
        json.dumps(occ[0].to_dict())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
