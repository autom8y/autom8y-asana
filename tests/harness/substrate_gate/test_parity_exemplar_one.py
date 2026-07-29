"""Parity exemplar #1 ledger test (S7 · P5 · REQUIREMENT 3).

The ``$84,385``-vs-``$79,585`` divergence must be EXPLAINED by the parity ledger as a
coherent composition shift, through the FROZEN RC-A-2 ``RefusePayload`` observable AS
LANDED (four fields, Mappings preserved). Same seeded state → the RC-A-2 replay case
REJECTS with reason DIVERGENT.
"""

from __future__ import annotations

import pytest

from autom8_asana.substrate.serve import Refused, RefuseReason
from tests.harness.substrate_gate import ReferenceSubstrate, ReplayRunner, ResultStatus
from tests.harness.substrate_gate.exemplars import (
    NOW,
    exemplar_one_aid,
    exemplar_one_observation,
    exemplar_one_replay_case,
    exemplar_one_source,
)
from tests.harness.substrate_gate.parity import ParityRunner


def _only_entry() -> object:
    ledger = ParityRunner(exemplar_one_source(), now=NOW).run([exemplar_one_aid()])
    assert len(ledger) == 1
    return ledger[0]


def test_ledger_carries_all_four_frozen_refusepayload_fields() -> None:
    entry = ParityRunner(exemplar_one_source(), now=NOW).run([exemplar_one_aid()])[0]
    payload = entry.payload

    # (1) plane — the stale copy the refusal concerns
    assert payload.plane == "v2/offer"
    assert entry.stale_plane == "v2/offer"
    assert entry.fresh_plane == "fresh-rewarm"

    # (2) absolute_age — a Mapping with an entry per copy (multiplicity NOT collapsed)
    assert set(payload.absolute_age) == {"v2/offer", "fresh-rewarm"}
    assert payload.absolute_age["fresh-rewarm"] == pytest.approx(0.0)
    assert payload.absolute_age["v2/offer"] == pytest.approx(1_265_220.0)

    # (3) magnitude — +$4,800
    assert payload.magnitude == pytest.approx(4_800.0)

    # (4) per_section_delta — a Mapping, un-narrowed, summing to magnitude
    delta = payload.per_section_delta
    assert delta["ACTIVE"] == pytest.approx(-4_000.0)
    assert delta["OPTIMIZE – Human Review"] == pytest.approx(4_800.0)
    assert delta["STAGED"] == pytest.approx(4_000.0)
    assert sum(delta.values()) == pytest.approx(payload.magnitude)


def test_ledger_explains_composition_shift_not_noise() -> None:
    entry = ParityRunner(exemplar_one_source(), now=NOW).run([exemplar_one_aid()])[0]
    assert "composition shift, not noise" in entry.explanation
    assert "ACTIVE -$4,000" in entry.explanation
    assert "OPTIMIZE – Human Review +$4,800" in entry.explanation
    assert "STAGED +$4,000" in entry.explanation
    assert "+$4,800" in entry.explanation
    assert "+6%" in entry.explanation


def test_exemplar_composition_sums_to_served_value_on_each_plane() -> None:
    observation = exemplar_one_observation()
    assert sum(cell.value for cell in observation.v1.composition.values()) == pytest.approx(
        observation.v1.served_value
    )
    assert sum(cell.value for cell in observation.v2.composition.values()) == pytest.approx(
        observation.v2.served_value
    )


def test_exemplar_maps_to_rc_a_2_replay_reject() -> None:
    result = ReplayRunner(ReferenceSubstrate()).run_case(exemplar_one_replay_case())
    assert result.predicate_id == "RC-A-2"
    assert result.status is ResultStatus.PASS
    assert isinstance(result.observed, Refused)
    assert result.observed.reason is RefuseReason.DIVERGENT


def test_coherent_state_produces_no_ledger_entry() -> None:
    """Two-sided: when v1 and v2 AGREE, the parity runner emits nothing (no false divergence)."""
    from tests.harness.substrate_gate.parity import FixtureParitySource, ParityObservation

    observation = exemplar_one_observation()
    coherent = ParityObservation(
        aid=observation.aid, v1=observation.v2, v2=observation.v2
    )  # both fresh
    ledger = ParityRunner(FixtureParitySource([coherent]), now=NOW).run([observation.aid])
    assert ledger == []
