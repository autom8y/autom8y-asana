"""Tests for the item-1a readout generation mechanism (EX-5, WS-2).

Demonstrates, over SYNTHETIC ``/rows`` data (the live worked render is EXIT-HELD,
operator/credential-gated per CR-5):

  * item 1a under DR-2 (``max`` per section, ``min`` floor over constituents);
  * the C-6 / DENOM-FENCE typed ``k of n`` denominator;
  * the C-5 per-render G4' enumeration, INCLUDING the FLAG F-2 truncation branch;
  * a ``report_generated`` emission matching EX-4's ``GenerationReceipt`` with a
    REAL ``content_hash`` (EX-4 CONCERN-1 discharge);
  * the limb-(a) join GREEN through EX-4's own ``run_query`` — two machine
    occurrences -> ``observable``/``satisfied``; a human-in-loop variant ->
    ``not_observable``. Two-sided.
  * DF-1: the mechanism imports nothing from the broken temporal substrate.

No authenticated/credential-bearing call is fired: every input is an in-memory
synthetic response and every emission is an in-memory event dict.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

import autom8_asana.readout.generation as generation_mod
import autom8_asana.readout.item_1a as item_1a_mod
import autom8_asana.readout.template as template_mod
from autom8_asana.observability.rung_receipts import run_query
from autom8_asana.observability.rung_receipts.schema import (
    Assembler,
    GenerationReceipt,
    NotObservableReason,
)
from autom8_asana.readout import (
    Ex2Disposition,
    G4PrimeSign,
    Item1aError,
    compute_item_1a,
    enumerate_g4_prime,
    render,
    render_blocks,
)
from autom8_asana.readout.generation import GeneratedOccurrence, content_hash_of

FIXTURES = Path(__file__).parent.parent / "fixtures" / "readout"
SCOPE = ["Discovery", "Negotiation", "Onboarding", "Closed Won"]
EXPECTED_MIN_FLOOR = "2026-08-08T10:00:00Z"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _rows_and_meta(name: str) -> tuple[list[dict], dict]:
    resp = _load(name)["data"]
    return resp["data"], resp["meta"]


def _generate(
    name: str = "rows_response_item1a.json",
    *,
    seq: int = 1,
    invocation_id: str = "EX5-1",
    cadence_label: str = "Weekly",
    generated_at: str = "2026-08-13T09:00:00Z",
) -> GeneratedOccurrence:
    return render(
        _load(name),
        cadence_label=cadence_label,
        seq=seq,
        invocation_id=invocation_id,
        source_query_id=f"offer-rows:{generated_at}:item1a",
        generated_at=generated_at,
        in_scope_sections=SCOPE,
    )


def _delivery_for(occ: GeneratedOccurrence, *, block_count: int | None = None) -> dict:
    """A synthetic ``report_posted`` delivery event paired to a generation.

    Honest by default: the delivery delivered exactly what was generated, so its
    ``block_count`` equals the occurrence's. ``block_count`` can be overridden to
    simulate a swap (a delivered artifact != the generated one).
    """
    return {
        "event": "report_posted",
        "invocation_id": occ.invocation_id,
        "channel": "#account-health",
        "block_count": occ.block_count if block_count is None else block_count,
        "abort_reason": "report_success",
        "timestamp": occ.report_generated["generated_at"],
    }


# ---------------------------------------------------------------------------
# item 1a under DR-2 + the C-6 denominator
# ---------------------------------------------------------------------------
class TestComputeItem1a:
    def test_min_floor_is_oldest_per_section_max(self) -> None:
        """DR-2: t_s is the min over per-section max(last_modified)."""
        rows, meta = _rows_and_meta("rows_response_item1a.json")
        figure = compute_item_1a(rows, SCOPE, meta)
        # Discovery max 08-12, Negotiation max 08-11, Onboarding max 08-08 ->
        # the min floor is the oldest of those maxes.
        assert figure.as_of_iso == EXPECTED_MIN_FLOOR
        assert figure.per_section_max["Discovery"].isoformat().startswith("2026-08-12T09:00")
        assert figure.per_section_max["Onboarding"].isoformat().startswith("2026-08-08T10:00")

    def test_denominator_k_of_n(self) -> None:
        """n = in-scope sections; k = those contributing a non-null max."""
        rows, meta = _rows_and_meta("rows_response_item1a.json")
        figure = compute_item_1a(rows, SCOPE, meta)
        assert figure.n == 4  # Discovery, Negotiation, Onboarding, Closed Won
        assert figure.k == 3  # Closed Won contributed no rows
        assert "Closed Won" not in figure.per_section_max

    def test_zero_constituents_refuses_loudly(self) -> None:
        """k == 0 has no min floor: the mechanism refuses, never invents one."""
        rows, meta = _rows_and_meta("rows_response_item1a.json")
        with pytest.raises(Item1aError):
            # None of these sections is present in the rows -> k == 0.
            compute_item_1a(rows, ["Nonexistent A", "Nonexistent B"], meta)

    def test_null_last_modified_row_is_skipped_not_crashed(self) -> None:
        rows, meta = _rows_and_meta("rows_response_item1a.json")
        rows = [*rows, {"section": "Discovery", "last_modified": None}]
        figure = compute_item_1a(rows, SCOPE, meta)
        # The null row does not move Discovery's max nor the floor.
        assert figure.as_of_iso == EXPECTED_MIN_FLOOR


# ---------------------------------------------------------------------------
# C-5 per-render G4' enumeration + FLAG F-2 truncation branch
# ---------------------------------------------------------------------------
class TestG4PrimeEnumeration:
    def test_single_signed_pass_overstate_only(self) -> None:
        rows, meta = _rows_and_meta("rows_response_item1a.json")
        bound = enumerate_g4_prime(compute_item_1a(rows, SCOPE, meta))
        assert bound.single_signed is True
        assert bound.dominant_sign is G4PrimeSign.OVERSTATE_AGE
        # No present branch understates the age (reads fresher than truth).
        assert all(b.sign is not G4PrimeSign.UNDERSTATE_AGE for b in bound.branches if b.present)

    def test_f2_truncation_branch_is_always_declared(self) -> None:
        """FLAG F-2: the truncation branch appears even when NOT truncated."""
        rows, meta = _rows_and_meta("rows_response_item1a.json")
        bound = enumerate_g4_prime(compute_item_1a(rows, SCOPE, meta))
        trunc = [b for b in bound.branches if "truncation" in b.name.lower()]
        assert len(trunc) == 1, "the truncation branch must be enumerated exactly once"
        # Not truncated here -> declared-and-absent, never silently 'neutral/none'.
        assert trunc[0].present is False
        assert "declared and considered" in trunc[0].note

    def test_f2_truncation_branch_bites_when_truncated(self) -> None:
        """When truncated, the branch is present and contributes OVERSTATE_AGE."""
        rows, meta = _rows_and_meta("rows_response_item1a_truncated.json")
        figure = compute_item_1a(rows, SCOPE, meta)
        assert figure.truncated is True
        bound = enumerate_g4_prime(figure)
        trunc = next(b for b in bound.branches if "truncation" in b.name.lower())
        assert trunc.present is True
        assert trunc.sign is G4PrimeSign.OVERSTATE_AGE
        # Truncation is stale-safe, so the single-signed PASS SURVIVES (F-2).
        assert bound.single_signed is True
        assert bound.dominant_sign is G4PrimeSign.OVERSTATE_AGE
        # The bound text carries a truncation disclosure (§1.2b T-GUARD bind).
        assert "truncated result window" in bound.text

    def test_truncation_only_differs_by_meta(self) -> None:
        """Rows identical; only meta flips truncation — isolates the signal."""
        rows_a, meta_a = _rows_and_meta("rows_response_item1a.json")
        rows_b, meta_b = _rows_and_meta("rows_response_item1a_truncated.json")
        assert rows_a == rows_b
        assert compute_item_1a(rows_a, SCOPE, meta_a).truncated is False
        assert compute_item_1a(rows_b, SCOPE, meta_b).truncated is True


# ---------------------------------------------------------------------------
# Template — slots, DENOM-FENCE, extension point, SC-1, R-16
# ---------------------------------------------------------------------------
class TestTemplate:
    def test_slot_inventory_present_and_ordered(self) -> None:
        occ = _generate()
        roles = [b["role"] for b in occ.blocks]
        assert roles == [
            "header",
            "say_able_number",
            "g4_prime_bound",
            "disclosure",
            "extension_point",
            "orientation_footer",
        ]

    def test_sc1_exactly_one_say_able_number(self) -> None:
        """SC-1: exactly one say-able number; it equals the DR-2 floor."""
        occ = _generate()
        say_able = [b for b in occ.blocks if b.get("say_able_value") is not None]
        assert len(say_able) == 1
        assert say_able[0]["say_able_value"] == occ.figure.as_of_iso == EXPECTED_MIN_FLOOR
        # The observation instant is provenance, NOT a say-able number.
        assert say_able[0]["observation_instant"] != say_able[0]["say_able_value"]

    def test_denom_fence_slot_is_typed(self) -> None:
        """C-6 / DENOM-FENCE: the denominator is int k, int n, unit 'sections'."""
        occ = _generate()
        denom = [b for b in occ.blocks if b["role"] == "say_able_number"][0]["denominator"]
        assert denom == {"k": 3, "n": 4, "unit": "sections"}
        assert isinstance(denom["k"], int) and isinstance(denom["n"], int)
        # Structurally cannot carry an age/rate: there is no such field.
        assert set(denom) == {"k", "n", "unit"}

    def test_g4_bound_rides_with_the_number(self) -> None:
        """C-5: a render carrying the number must carry its bound (per-render)."""
        occ = _generate()
        bound_block = [b for b in occ.blocks if b["role"] == "g4_prime_bound"][0]
        assert bound_block["text"] == occ.g4_bound.text
        assert bound_block["single_signed"] is True
        assert "fails toward stale" in bound_block["text"]

    def test_extension_point_declared_empty_and_attested(self) -> None:
        """SC-6 / C-4 / DF-5: declared, empty, attested (not merely blank)."""
        occ = _generate()
        ext = [b for b in occ.blocks if b["role"] == "extension_point"][0]
        assert ext["ex2_disposition"] == Ex2Disposition.STILL_ONE.value
        assert ext["second_number_class"] is None  # empty until EX-2 promotes (C-4)

    def test_sc7_orientation_register_no_steering(self) -> None:
        """SC-7 / R-16 / F-E3: no recommendation, ranking, CTA, or health verdict."""
        occ = _generate()
        blob = " ".join(str(b["text"]) for b in occ.blocks).lower()
        banned = [
            "you should",
            "recommend",
            "action required",
            "take action",
            "worst section",
            "top section",
            "ranked",
            "at risk",
            "healthy",
            "unhealthy",
            "click here",
            "please review",
        ]
        for token in banned:
            assert token not in blob, f"steering token leaked into render: {token!r}"


# ---------------------------------------------------------------------------
# EX-4 CONCERN-1 — the REAL content_hash
# ---------------------------------------------------------------------------
class TestContentHash:
    def test_content_hash_is_a_real_sha256(self) -> None:
        occ = _generate()
        assert occ.content_hash.startswith("sha256:")
        hexpart = occ.content_hash.split(":", 1)[1]
        assert len(hexpart) == 64
        int(hexpart, 16)  # is hex — raises if not

    def test_content_hash_covers_the_delivered_payload(self) -> None:
        """The emitted hash is exactly the hash of the assembled blocks."""
        occ = _generate()
        assert occ.report_generated["content_hash"] == content_hash_of(occ.blocks)

    def test_content_hash_is_deterministic(self) -> None:
        assert _generate().content_hash == _generate().content_hash

    def test_content_hash_flips_on_any_payload_change(self) -> None:
        """A different render -> different bytes -> different hash (no collision)."""
        base = _generate(seq=1, generated_at="2026-08-13T09:00:00Z")
        diff_seq = _generate(seq=2, generated_at="2026-08-13T09:00:00Z")
        diff_time = _generate(seq=1, generated_at="2026-08-20T09:00:00Z")
        diff_figure = render(
            _load("rows_response_item1a_truncated.json"),
            cadence_label="Weekly",
            seq=1,
            invocation_id="EX5-1",
            source_query_id="q",
            generated_at="2026-08-13T09:00:00Z",
            in_scope_sections=SCOPE,
        )
        hashes = {
            base.content_hash,
            diff_seq.content_hash,
            diff_time.content_hash,
            diff_figure.content_hash,
        }
        assert len(hashes) == 4  # every payload delta flips the hash


# ---------------------------------------------------------------------------
# report_generated emission matches EX-4's GenerationReceipt
# ---------------------------------------------------------------------------
class TestReportGeneratedEmission:
    def test_projects_into_ex4_generation_receipt(self) -> None:
        occ = _generate(invocation_id="EX5-77")
        receipt = GenerationReceipt.from_event(occ.report_generated)
        assert receipt.invocation_id == "EX5-77"
        assert receipt.assembled_by is Assembler.MACHINE
        assert receipt.human_in_loop is False
        assert receipt.content_hash == occ.content_hash
        assert receipt.content_hash != ""  # a REAL hash, not the schema default
        assert receipt.source_query_id == occ.report_generated["source_query_id"]
        assert receipt.block_count == occ.block_count

    def test_mechanism_cannot_emit_human_authorship(self) -> None:
        """The 'no human assembled it' claim is structural, not a parameter."""
        occ = _generate()
        assert occ.report_generated["assembled_by"] == "machine"
        assert occ.report_generated["human_in_loop"] is False
        # No render() argument can flip these — they are module constants.
        assert generation_mod.HUMAN_IN_LOOP is False
        assert generation_mod.ASSEMBLED_BY is Assembler.MACHINE

    def test_keyed_on_invocation_id(self) -> None:
        occ = _generate(invocation_id="EX5-KEY")
        assert occ.report_generated["invocation_id"] == "EX5-KEY"


# ---------------------------------------------------------------------------
# The limb-(a) join GREEN over synthetic data — TWO-SIDED, via EX-4's run_query
# ---------------------------------------------------------------------------
class TestLimbAJoinGreen:
    def test_two_machine_occurrences_satisfy_limb_a(self) -> None:
        """POSITIVE control: two machine-assembled occurrences -> SATISFIED."""
        occ1 = _generate(seq=1, invocation_id="EX5-1", generated_at="2026-08-13T09:00:00Z")
        occ2 = _generate(seq=2, invocation_id="EX5-2", generated_at="2026-08-20T09:00:00Z")
        events = [
            _delivery_for(occ1),
            occ1.report_generated,
            _delivery_for(occ2),
            occ2.report_generated,
        ]
        limb_a = run_query(events)["rung_e_limb_a"]
        assert limb_a["status"] == "satisfied"
        assert limb_a["observable_occurrences"] == 2
        for receipt in limb_a["receipts"]:
            assert receipt["rung_e_limb_a_attestation"] == "observable"
            assert receipt["rung_e_not_observable_reason"] is None

    def test_human_in_loop_variant_is_not_observable(self) -> None:
        """NEGATIVE control (two-sided): a human-in-loop input is rejected."""
        occ = _generate(invocation_id="EX5-H")
        human_variant = {**occ.report_generated, "human_in_loop": True}
        limb_a = run_query([_delivery_for(occ), human_variant])["rung_e_limb_a"]
        assert limb_a["status"] == "not_yet_observed"
        assert limb_a["receipts"][0]["rung_e_not_observable_reason"] == (
            NotObservableReason.HUMAN_IN_LOOP.value
        )

    def test_emission_closes_the_generation_provenance_gap(self) -> None:
        """EX-4 NR-4 discharge: delivery alone is provenance-absent; the
        mechanism's report_generated flips the same occurrence to observable."""
        occ = _generate(invocation_id="EX5-GAP")
        before = run_query([_delivery_for(occ)])["rung_e_limb_a"]
        assert before["receipts"][0]["rung_e_not_observable_reason"] == (
            NotObservableReason.GENERATION_PROVENANCE_ABSENT.value
        )
        after = run_query([_delivery_for(occ), occ.report_generated])["rung_e_limb_a"]
        assert after["receipts"][0]["rung_e_limb_a_attestation"] == "observable"

    def test_swap_is_caught_via_block_count(self) -> None:
        """A delivered artifact different from the generated one cannot pass.

        EX-4's join compares block_count under the CONTENT_HASH_MISMATCH label
        (report_posted carries no content_hash). Our generation half now carries
        a REAL content_hash ready for when delivery closes that gap; today the
        swap is caught on block_count."""
        occ = _generate(invocation_id="EX5-SWAP")
        swapped_delivery = _delivery_for(occ, block_count=occ.block_count + 5)
        limb_a = run_query([swapped_delivery, occ.report_generated])["rung_e_limb_a"]
        assert limb_a["receipts"][0]["rung_e_not_observable_reason"] == (
            NotObservableReason.CONTENT_HASH_MISMATCH.value
        )

    def test_rung_4_ladder_stays_operator_only(self) -> None:
        """FS-5: making RUNG-E observable never moves the felt rung-4 line."""
        occ1 = _generate(seq=1, invocation_id="EX5-1")
        occ2 = _generate(seq=2, invocation_id="EX5-2", generated_at="2026-08-20T09:00:00Z")
        obs = run_query(
            [_delivery_for(occ1), occ1.report_generated, _delivery_for(occ2), occ2.report_generated]
        )
        assert obs["rung_4"]["status"] == "unattested_felt_operator_only"


# ---------------------------------------------------------------------------
# DF-1 — the independence that is the easiest thing here to get wrong
# ---------------------------------------------------------------------------
class TestDF1Independence:
    """SC-3: the generation path imports NOTHING from the broken substrate."""

    _FORBIDDEN = ("temporal", "section_timeline", "section_timelines", "story", "stories")

    def _imported_modules(self, path: Path) -> list[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
        return modules

    @pytest.mark.parametrize("mod", [generation_mod, item_1a_mod, template_mod])
    def test_no_forbidden_import(self, mod) -> None:
        path = Path(mod.__file__)
        for imported in self._imported_modules(path):
            lowered = imported.lower()
            for token in self._FORBIDDEN:
                assert token not in lowered, (
                    f"{path.name} imports {imported!r} — DF-1 forbids reaching "
                    f"the temporal/section-timelines/story substrate"
                )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
