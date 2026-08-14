"""Two-sided swap-detector closure — CC-1 (chain-of-custody-closure).

RED-before / GREEN-after, own-hands. The negative these tests hold:

  * "a count-preserving swap passes as OBSERVABLE today" — on the pre-CC-1 join a
    swap (equal ``block_count``, DIFFERENT payload) classified OBSERVABLE, because
    the join never compared a ``content_hash`` and ``DeliveryReceipt`` carried
    none. The RED capture (scratchpad ``RED-reconverge.txt``) recorded exactly
    that.
  * "no over-claiming docstring survives" — post-repair, clause 4a (hash) and 4b
    (block_count) carry DISTINCT reasons, and the clause-3 UNKNOWN over-claim +
    the clause-4a residual are documented, not swept.

This module pins the GREEN closure AND the honest residual the closure leaves
open (a hashless delivery cannot be swap-checked). No defect is injected: the
guard was genuinely absent — these tests fail on the pristine tree because the
swap returns ``observable`` and ``DeliveryReceipt.content_hash`` does not exist.

Swap-fixture provenance: ``tests/fixtures/rung_receipts/PROVENANCE.md``.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from autom8_asana.observability.payload_hash import canonical_payload_hash
from autom8_asana.observability.rail_delivery.delivery_receipt import (
    content_hash as delivery_content_hash,
)
from autom8_asana.observability.rung_receipts import join_occurrences, run_query
from autom8_asana.observability.rung_receipts.schema import (
    DELIVERY_LOGS_INSIGHTS_QUERY,
    RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA,
    DeliveryReceipt,
    NotObservableReason,
    RungEObservability,
)
from autom8_asana.readout.generation import GeneratedOccurrence, render

FIXTURES = Path(__file__).parent.parent / "fixtures" / "readout"
SCOPE = ["Discovery", "Negotiation", "Onboarding", "Closed Won"]
_MATCH = "__match__"


def _generate(
    *,
    invocation_id: str = "CC1-1",
    seq: int = 1,
    generated_at: str = "2026-08-13T09:00:00Z",
) -> GeneratedOccurrence:
    """One real machine-generated occurrence via the actual EX-5 mechanism."""
    return render(
        json.loads((FIXTURES / "rows_response_item1a.json").read_text(encoding="utf-8")),
        cadence_label="Weekly",
        seq=seq,
        invocation_id=invocation_id,
        source_query_id="offer-rows:cc1:item1a",
        generated_at=generated_at,
        in_scope_sections=SCOPE,
    )


def _swap(occ: GeneratedOccurrence) -> tuple[list[dict[str, object]], str]:
    """A count-preserving swap: same block COUNT, DIFFERENT say-able payload + text.

    This is the founding-wound shape — a hand-pasted artifact of the same length
    delivered in place of the machine-generated one.
    """
    swapped = copy.deepcopy(occ.blocks)
    swapped_text = "As of 2026-08-13T09:00:00Z, everything is fine."
    for block in swapped:
        if block.get("role") == "say_able_number":
            block["text"] = swapped_text
            block["say_able_value"] = "2026-01-01T00:00:00Z"
    return swapped, swapped_text


def _delivery(
    occ: GeneratedOccurrence,
    *,
    block_count: int | None = None,
    content_hash: str | None = _MATCH,
) -> dict[str, object]:
    """A ``report_posted`` delivery event paired to ``occ``.

    ``content_hash`` sentinel: ``_MATCH`` -> ``occ.content_hash`` (honest);
    ``None`` -> the field is OMITTED entirely (the hashless live-emitter shape);
    any other str -> used verbatim (a swap's own hash).
    """
    evt: dict[str, object] = {
        "event": "report_posted",
        "invocation_id": occ.invocation_id,
        "channel": "#account-health",
        "block_count": occ.block_count if block_count is None else block_count,
        "abort_reason": "report_success",
        "timestamp": "2026-08-13T09:00:01Z",
    }
    if content_hash == _MATCH:
        evt["content_hash"] = occ.content_hash
    elif content_hash is not None:
        evt["content_hash"] = content_hash
    return evt


def _receipt(delivery_evt: dict[str, object], occ: GeneratedOccurrence) -> dict[str, object]:
    return run_query([delivery_evt, occ.report_generated])["rung_e_limb_a"]["receipts"][0]


# ---------------------------------------------------------------------------
# RED-turned-GREEN — the count-preserving swap is now caught
# ---------------------------------------------------------------------------
class TestSwapNowCaught:
    def test_count_preserving_swap_is_not_observable(self) -> None:
        """RED-before: this was ``observable``. GREEN-after: caught on the hash."""
        occ = _generate()
        swapped, swapped_text = _swap(occ)
        swap_delivery = _delivery(
            occ,
            block_count=len(swapped),  # count-preserving: equal to occ.block_count
            content_hash=canonical_payload_hash(swapped, swapped_text),
        )
        receipt = _receipt(swap_delivery, occ)
        assert receipt["delivery"]["block_count"] == occ.block_count  # equal counts
        assert receipt["rung_e_limb_a_attestation"] == RungEObservability.NOT_OBSERVABLE.value
        assert receipt["rung_e_not_observable_reason"] == (
            NotObservableReason.CONTENT_HASH_MISMATCH.value
        )

    def test_swap_is_caught_on_the_hash_not_the_block_count(self) -> None:
        """The teeth bite on 4a: block counts are EQUAL, so 4b cannot be the cause."""
        occ = _generate()
        swapped, swapped_text = _swap(occ)
        assert len(swapped) == occ.block_count, "fixture must be count-preserving"
        assert canonical_payload_hash(swapped, swapped_text) != occ.content_hash


# ---------------------------------------------------------------------------
# The honest direction — a real delivery of the generated payload passes
# ---------------------------------------------------------------------------
class TestHonestDirection:
    def test_honest_delivery_is_observable(self) -> None:
        occ = _generate()
        receipt = _receipt(_delivery(occ, content_hash=_MATCH), occ)
        assert receipt["delivery"]["content_hash"] == occ.content_hash
        assert receipt["rung_e_limb_a_attestation"] == RungEObservability.OBSERVABLE.value
        assert receipt["rung_e_not_observable_reason"] is None


# ---------------------------------------------------------------------------
# Single-variable causation — the verdict flips on content_hash ALONE
# ---------------------------------------------------------------------------
class TestSingleVariableCausation:
    def test_only_content_hash_flips_the_verdict(self) -> None:
        occ = _generate()
        swapped, swapped_text = _swap(occ)
        honest_delivery = _delivery(occ, content_hash=_MATCH)
        swap_delivery = _delivery(
            occ,
            block_count=len(swapped),
            content_hash=canonical_payload_hash(swapped, swapped_text),
        )
        # The two INPUT events differ in EXACTLY one field: content_hash.
        differing = {
            k
            for k in set(honest_delivery) | set(swap_delivery)
            if honest_delivery.get(k) != swap_delivery.get(k)
        }
        assert differing == {"content_hash"}

        honest = _receipt(honest_delivery, occ)
        swap = _receipt(swap_delivery, occ)
        assert honest["rung_e_limb_a_attestation"] == RungEObservability.OBSERVABLE.value
        assert swap["rung_e_limb_a_attestation"] == RungEObservability.NOT_OBSERVABLE.value
        assert swap["rung_e_not_observable_reason"] == (
            NotObservableReason.CONTENT_HASH_MISMATCH.value
        )


# ---------------------------------------------------------------------------
# Clause-4a residual — a hashless delivery leaves 4a UNATTESTED (not satisfied)
# ---------------------------------------------------------------------------
class TestClause4aResidual:
    def test_hashless_delivery_is_observable_but_hash_is_unattested(self) -> None:
        """The live report_posted shape: no content_hash on the wire.

        Clause 4a cannot run (nothing to compare), so it is UNATTESTED — the
        occurrence passes on clause 4b's block-count alone. This is NOT a hash
        match; it is the absence of a hash check. Pinned so the honest limitation
        is visible, not swept.
        """
        occ = _generate()
        receipt = _receipt(_delivery(occ, content_hash=None), occ)
        assert receipt["delivery"]["content_hash"] is None  # 4a input absent
        assert receipt["rung_e_limb_a_attestation"] == RungEObservability.OBSERVABLE.value
        assert receipt["rung_e_not_observable_reason"] is None

    def test_swap_on_a_hashless_delivery_is_still_undetected(self) -> None:
        """The residual's sharp edge: the fix does NOT claim to catch swaps when
        the delivery carries no hash. A count-preserving swap delivered WITHOUT a
        content_hash still classifies observable — the swap-detector bites only
        once the delivery emitter emits the hash (REC-002, out of CC-1 scope)."""
        occ = _generate()
        swapped, _ = _swap(occ)
        # A swap delivered hashless: equal block_count, no content_hash on the wire.
        receipt = _receipt(_delivery(occ, block_count=len(swapped), content_hash=None), occ)
        assert receipt["delivery"]["content_hash"] is None
        assert receipt["rung_e_limb_a_attestation"] == RungEObservability.OBSERVABLE.value


# ---------------------------------------------------------------------------
# REC-001 — one shared canonicalization; the two call sites agree
# ---------------------------------------------------------------------------
class TestREC001SharedCanon:
    def test_generation_uses_the_shared_symbol(self) -> None:
        occ = _generate()
        assert occ.content_hash == canonical_payload_hash(occ.blocks, occ.text)

    def test_generation_and_delivery_agree_on_the_same_payload(self) -> None:
        """The RED recorded 'two canonicalizations agree? False'; now they agree."""
        occ = _generate()
        assert occ.content_hash == delivery_content_hash(occ.blocks, occ.text)

    def test_shared_symbol_binds_blocks_and_text_both(self) -> None:
        occ = _generate()
        # Changing ONLY the fallback text flips the hash — text is bound, not free.
        assert canonical_payload_hash(occ.blocks, occ.text) != canonical_payload_hash(
            occ.blocks, occ.text + " (edited)"
        )


# ---------------------------------------------------------------------------
# REC-003 — the schema splice makes the delivery side hash-bearing
# ---------------------------------------------------------------------------
class TestREC003SchemaSplice:
    def test_delivery_receipt_carries_content_hash(self) -> None:
        assert "content_hash" in DeliveryReceipt.__dataclass_fields__
        rec = DeliveryReceipt.from_event(
            {
                "invocation_id": "A",
                "channel": "#account-health",
                "block_count": 42,
                "abort_reason": "report_success",
                "timestamp": "2026-08-13T00:00:00Z",
                "content_hash": "sha256:abc",
            }
        )
        assert rec.content_hash == "sha256:abc"

    def test_content_hash_defaults_none_for_the_live_hashless_shape(self) -> None:
        """The live report_posted emitter carries no content_hash -> None, not crash."""
        rec = DeliveryReceipt.from_event(
            {
                "invocation_id": "A",
                "channel": "#account-health",
                "block_count": 42,
                "abort_reason": "report_success",
                "timestamp": "2026-08-13T00:00:00Z",
            }
        )
        assert rec.content_hash is None

    def test_schema_delivery_has_content_hash_optional_not_required(self) -> None:
        """content_hash is in properties but NOT required — a schema that required
        it would reject every live receipt the emitter actually produces."""
        delivery = RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA["properties"]["delivery"]["oneOf"][1]
        assert "content_hash" in delivery["properties"]
        assert "content_hash" not in delivery["required"]

    def test_delivery_ingestion_query_selects_content_hash(self) -> None:
        assert "content_hash" in DELIVERY_LOGS_INSIGHTS_QUERY


# ---------------------------------------------------------------------------
# Clause-3 narrowing — UNKNOWN assembler is reported as ASSEMBLED_BY_HUMAN
# ---------------------------------------------------------------------------
class TestClause3Narrowing:
    def _occ_with_assembler(self, assembler: str) -> dict[str, object]:
        delivery = {
            "event": "report_posted",
            "invocation_id": "C3",
            "channel": "#account-health",
            "block_count": 42,
            "abort_reason": "report_success",
            "timestamp": "2026-08-13T00:00:00Z",
            "content_hash": "sha256:same",
        }
        generation = {
            "event": "report_generated",
            "invocation_id": "C3",
            "assembled_by": assembler,
            "human_in_loop": False,
            "content_hash": "sha256:same",
            "block_count": 42,
            "generated_at": "2026-08-13T00:00:00Z",
        }
        occ = join_occurrences([delivery], [generation])[0]
        return occ.to_dict()

    def test_unknown_assembler_over_claims_assembled_by_human(self) -> None:
        """DOCUMENTED OVER-CLAIM (CC-1): an UNKNOWN assembler — un-attested
        authorship — is reported under the ASSEMBLED_BY_HUMAN token, asserting a
        human authored it. The token is frozen (breaking schema change out of
        scope); this test pins the current (over-claiming) behavior so the
        follow-on schema-version owner sees exactly what to split."""
        receipt = self._occ_with_assembler("unknown")
        assert receipt["rung_e_limb_a_attestation"] == RungEObservability.NOT_OBSERVABLE.value
        assert receipt["rung_e_not_observable_reason"] == (
            NotObservableReason.ASSEMBLED_BY_HUMAN.value
        )

    def test_human_assembler_also_reports_assembled_by_human(self) -> None:
        """The truthful case: an actual HUMAN assembler under the same token."""
        receipt = self._occ_with_assembler("human")
        assert receipt["rung_e_not_observable_reason"] == (
            NotObservableReason.ASSEMBLED_BY_HUMAN.value
        )


# ---------------------------------------------------------------------------
# Clause 4b — block-count mismatch is its OWN reason, distinct from 4a
# ---------------------------------------------------------------------------
class TestClause4bDistinct:
    def test_block_count_mismatch_has_its_own_reason(self) -> None:
        """A bare block-count disagreement (no content_hash on delivery) is
        BLOCK_COUNT_MISMATCH — NEVER mislabelled CONTENT_HASH_MISMATCH."""
        occ = _generate()
        receipt = _receipt(_delivery(occ, block_count=occ.block_count + 5, content_hash=None), occ)
        assert receipt["rung_e_limb_a_attestation"] == RungEObservability.NOT_OBSERVABLE.value
        assert receipt["rung_e_not_observable_reason"] == (
            NotObservableReason.BLOCK_COUNT_MISMATCH.value
        )

    def test_hash_and_count_reasons_are_distinct_tokens(self) -> None:
        assert (
            NotObservableReason.CONTENT_HASH_MISMATCH.value
            != NotObservableReason.BLOCK_COUNT_MISMATCH.value
        )
