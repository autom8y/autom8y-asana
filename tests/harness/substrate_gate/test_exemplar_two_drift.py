"""Exemplar #2 current-state drift tripwire (S8-0 pre-gate · O4 · additive).

Exemplar #2 is a fresh-and-coherent CURRENT offer-plane anchor derived from the real S3
artifact (0 Asana calls; see RECEIPT-s8-0-fixture-recapture-2026-07-30.md). These tests
pin it as a DRIFT TRIPWIRE: the same S3 bytes re-derive the same served value, its value
measured against exemplar #1's frozen ``$84,385`` IS the measured dark-build drift-delta
(−$3,400), and the coherent anchor emits NO divergence (it is a tripwire, not a wound).
"""

from __future__ import annotations

import pytest

from tests.harness.substrate_gate.exemplars import (
    PARITY_GATE_SOURCES,
    exemplar_one_observation,
    exemplar_two_aid,
    exemplar_two_materialization,
    exemplar_two_observation,
    exemplar_two_source,
)
from tests.harness.substrate_gate.parity import ParityRunner

_EXEMPLAR_ONE_FROZEN_VALUE = 84_385.0  # exemplar #1's fresh re-warm headline
_EXEMPLAR_TWO_VALUE = 80_985.0  # S3-derived current offer plane
_DRIFT_DELTA = -3_400.0


def test_current_served_value_is_pinned_to_the_s3_derived_number() -> None:
    """Drift tripwire: a changed S3 build would change this pinned aggregate."""
    materialization = exemplar_two_materialization()
    assert materialization.served_value == pytest.approx(_EXEMPLAR_TWO_VALUE)
    assert materialization.plane == "v2/offer-current"


def test_composition_sums_to_served_value() -> None:
    """Coherence (also construction-enforced): Σ per-section == served_value."""
    materialization = exemplar_two_materialization()
    total = sum(cell.value for cell in materialization.composition.values())
    assert total == pytest.approx(materialization.served_value)
    assert sum(cell.rows for cell in materialization.composition.values()) == 61


def test_section_name_uses_prod_hyphen_not_fixture_en_dash() -> None:
    """The real S3 bytes carry a plain hyphen; exemplar #1's synthetic fixture used an en-dash."""
    composition = exemplar_two_materialization().composition
    assert "OPTIMIZE - Human Review" in composition  # U+002D hyphen (prod)
    assert "OPTIMIZE – Human Review" not in composition  # U+2013 en-dash (fixture)


def test_drift_delta_against_exemplar_one_frozen_value() -> None:
    """served_value(#2) − $84,385 IS the measured dark-build drift-delta."""
    fresh_one = exemplar_one_observation().v2.served_value
    assert fresh_one == pytest.approx(_EXEMPLAR_ONE_FROZEN_VALUE)
    measured = exemplar_two_materialization().served_value - fresh_one
    assert measured == pytest.approx(_DRIFT_DELTA)


def test_freshness_proof_carries_watermark_instant_and_offer_sla() -> None:
    proof = exemplar_two_materialization().proof
    assert proof.built_from_live_at.isoformat() == "2026-07-30T12:23:09.371507+00:00"
    assert proof.sla_seconds == 180  # the real offer contract, not the #1 placeholder 3600


def test_coherent_anchor_emits_no_divergence() -> None:
    """A tripwire, not a wound: v1 == v2, so the parity runner emits nothing."""
    now = exemplar_two_materialization().proof.built_from_live_at
    ledger = ParityRunner(exemplar_two_source(), now=now).run([exemplar_two_aid()])
    assert ledger == []


def test_registered_at_parity_gate_enumeration_beside_exemplar_one() -> None:
    """Net corpus: 22 predicates unchanged + #1 + #2 — both sources enumerated."""
    from tests.harness.substrate_gate.exemplars import exemplar_one_source

    assert (exemplar_one_source, exemplar_two_source) == PARITY_GATE_SOURCES
    # both produce a usable parity source
    assert exemplar_two_source().fetch(exemplar_two_aid()) is not None
