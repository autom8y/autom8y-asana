"""B-1 CANARY -- the two-sided per-office DISTRIBUTION canary (compliance blocker B-1).

Closes the evidence gap named in
``autom8y/.ledge/reviews/COMPLIANCE-c1-pii-deidentification-2026-06-29.md`` (a)/(b)/(c)
R-2 + (d) evidence-mechanism #1 + (e) B-1: the data-plane ownership canaries prove the
operator may READ only owned offices, but NOTHING proves the Asana DISTRIBUTOR hands
each office only its OWN slice. This canary is that missing proof.

THE INVARIANT UNDER TEST (HYPOTHESIS):
  For any office A, the rendered deck -- the per-office slice the workflow distributes at
  ``insights/workflow.py:806`` (``self._operator_batch[table].get(office_phone, [])``) --
  contains rows for office A ONLY; zero rows belonging to any other office.

THE REAL SURFACES EXERCISED (no reimplementation):
  1. ``distribute_per_office`` (``clients/data/_endpoints/operator.py:44``) -- the OQ-2
     adapter that folds the data-plane batch envelope into ``{office_phone: rows}``. The
     collision physically lands here (``per_office[phone] = rows`` :78).
  2. ``InsightsExportWorkflow._fetch_all_tables`` -> ``_fetch_table``
     (``insights/workflow.py:806``) -- the per-office read of that folded batch.

THE DISCRIMINATING FIXTURE (discriminating-canary-doctrine -- break the INPUT, never the
SURFACE; G-THEATER forbidden): the ONLY thing that differs between GREEN and RED is the
data-plane response ENVELOPE handed to the real ``distribute_per_office``. No production
file is edited to manufacture the RED. The collision models the KNOWN latent hazard
(``COMPLIANCE-c1`` R-2 latent / fleet-memory ``ebi-forwarding-confirm-golive-nogo``):
``office_phone`` uniqueness is EMERGENT, not enforced (autom8y-data
``repositories/business.py:192`` ``.first()`` -- no ORDER BY, no UNIQUE constraint), so
two distinct offices can share one ``office_phone``, the per-office key collides, and the
distribution invariant breaks silently.

ARMS (two-sided -- positive control + negative control on the SAME harness):
  - TC-GREEN          : A and B have DISTINCT phones -> each deck carries only its own
                        rows -> contamination detector returns [] (isolation holds).
  - TC-RED-MERGE      : A and B SHARE a phone; the office-grain aggregate returns BOTH
                        offices' rows under that one phone -> A's deck contains a B row.
                        The detector CATCHES it. The current distributor has NO guard --
                        it SILENTLY MERGES. This is the B-2 defect, characterized.
  - TC-RED-OVERWRITE  : A and B SHARE a phone; the envelope carries two same-phone
                        entries -> ``distribute_per_office`` last-write-wins -> A's deck
                        is REPLACED by B's rows entirely (A's own data vanishes).
  - TC-TEETH          : the SAME detector + SAME render path returns [] on the clean
                        envelope and non-empty on the collision envelope -- two-sided
                        proof the canary bites ONLY on the defect (not on shape).
  - TC-INVARIANT-B1   : the B-1 isolation invariant asserted as it SHOULD hold under
                        collision. ``xfail(strict=True)`` -- it XFAILs TODAY (B-2
                        unfixed) and flips to XPASS -> SUITE-FAIL the moment B-2 lands,
                        forcing this marker's removal and converting the canary into a
                        permanent live guard. This is the machine-readable "B-2 unfixed"
                        beacon; it does NOT fake a GREEN.
  - TC-SCOPE          : NO arm makes a wire call and NO arm ever touches an SA fleet-read
                        method (``get_leads_async`` / ``get_insights_async`` / ...). Pure
                        test-harness fault injection -- no prod calls, no live export.

VERDICT (see CHAOS-b1-distribution-canary report): the per-office distribution invariant
is NOT enforced today. The distributor distributes by ``office_phone`` with no per-row
office-identity guard; under a shared-phone collision office B's rows leak into office A's
partner deck. B-1 (this canary) is LANDED; B-2 (the office_phone uniqueness fix, data-side
/ operator-terminal) is REQUIRED before export re-enable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.automation.workflows.insights.workflow import (
    DEFAULT_ROW_LIMITS,
    InsightsExportWorkflow,
)
from autom8_asana.clients.data._endpoints.operator import distribute_per_office

if TYPE_CHECKING:
    from autom8_asana.automation.workflows.insights.formatter import TableResult

# --- Two offices: distinct DISPLAY identities (the unmasked `office` dimension is the
# re-identifying column per COMPLIANCE-c1 (a) / Rs-3). The collision is on the PHONE
# (the distribution key), never on the office identity. ---
OFFICE_A = "NHC North Wellness"
OFFICE_B = "Rival Spine & Joint"
PHONE_A = "+17705551111"
PHONE_B = "+17705552222"
SHARED_PHONE = "+17705559999"  # the B-2 hazard: A and B both resolve to ONE office_phone

# The data-plane insight whose grain is `office_phone x office x vertical` (SUMMARY ->
# account_level_stats; COMPLIANCE-c1 (a), lib :455). No activity filter, `office` present.
SUMMARY_TABLE = "SUMMARY"
SUMMARY_INSIGHT = "account_level_stats"


def _row(office: str, phone: str, spend: int) -> dict[str, Any]:
    """A de-identified office-grain aggregate row (spend>0 survives the activity filter)."""
    return {
        "office": office,
        "office_phone": phone,
        "vertical": "chiropractic",
        "spend": spend,
        "leads": 0,
        "convs": 7,  # aggregate COUNT metric, not a patient-grain dimension (lib :1307)
    }


def _phone_result(
    phone: str, rows: list[dict[str, Any]], status: str = "success"
) -> dict[str, Any]:
    """One per-phone entry of the operator-batch envelope (mirrors the data-plane shape)."""
    return {
        "phone": phone,
        "status": status,
        "data": (
            {"result_type": "result", "data": rows, "meta": {}} if status == "success" else None
        ),
        "error": None if status == "success" else "no data",
        "cache_hit": False,
        "duration_ms": 1.0,
    }


def _envelope(results: list[dict[str, Any]], insight: str = SUMMARY_INSIGHT) -> dict[str, Any]:
    """A ``SuccessResponse[BatchInsightResponse]`` envelope (phone-only mode)."""
    return {
        "data": {
            "insight": insight,
            "total_phones": len(results),
            "successful": len(results),
            "failed": 0,
            "results": results,
            "pair_results": None,
            "duration_ms": 5.0,
        },
        "meta": {"request_id": "req_b1_canary"},
    }


def _make_distributor() -> tuple[InsightsExportWorkflow, MagicMock]:
    """Construct the REAL workflow with inert mock clients.

    ``_fetch_table`` reads ONLY ``self._operator_batch`` -- it makes no client call -- so
    MagicMock clients suffice. The SA fleet-read methods are wired as AsyncMocks purely so
    TC-SCOPE can prove they are NEVER touched on the cross-tenant distribution path.
    """
    asana = MagicMock()
    data = MagicMock()
    attachments = MagicMock()
    data.get_leads_async = AsyncMock()
    data.get_insights_async = AsyncMock()
    data.get_appointments_async = AsyncMock()
    data.get_reconciliation_async = AsyncMock()
    wf = InsightsExportWorkflow(
        asana_client=asana,
        data_client=data,
        attachments_client=attachments,
    )
    return wf, data


async def _render_deck(wf: InsightsExportWorkflow, office_phone: str) -> dict[str, TableResult]:
    """Render ONE office's full deck via the REAL distributor (``_fetch_all_tables`` ->
    ``_fetch_table`` -> ``workflow.py:806``)."""
    return await wf._fetch_all_tables(
        office_phone=office_phone,
        vertical="chiropractic",
        row_limits=DEFAULT_ROW_LIMITS,
        offer_gid=f"offer-{office_phone}",
    )


def cross_office_rows(deck: dict[str, TableResult], own_office: str) -> list[dict[str, Any]]:
    """THE CANARY DETECTOR: every row in a rendered deck whose ``office`` != ``own_office``.

    Empty list  == per-office isolation holds (GREEN -- the deck carries only its own rows).
    Non-empty   == cross-office leak (RED -- office B's row rendered into office A's deck).

    The ``office`` display-name renders UNMASKED in the partner deck (COMPLIANCE-c1 (a) /
    Rs-3), so a foreign ``office`` value IS the re-identifying disclosure.
    """
    foreign: list[dict[str, Any]] = []
    for table in deck.values():
        for row in table.data or []:
            if "office" in row and row["office"] != own_office:
                foreign.append(row)
    return foreign


def _seed_summary(wf: InsightsExportWorkflow, envelope: dict[str, Any]) -> None:
    """Fold a data-plane envelope through the REAL adapter into the office's batch cache."""
    wf._operator_batch = {SUMMARY_TABLE: distribute_per_office(envelope)}


class TestB1PerOfficeDistributionCanary:
    """B-1: prove (or falsify) the per-office distribution isolation invariant."""

    async def test_tc_green_distinct_phones_zero_cross_contamination(self) -> None:
        """TC-GREEN: distinct phones -> each office's deck carries ONLY its own rows."""
        wf, _ = _make_distributor()
        envelope = _envelope(
            [
                _phone_result(PHONE_A, [_row(OFFICE_A, PHONE_A, 100)]),
                _phone_result(PHONE_B, [_row(OFFICE_B, PHONE_B, 200)]),
            ]
        )
        _seed_summary(wf, envelope)

        deck_a = await _render_deck(wf, PHONE_A)
        deck_b = await _render_deck(wf, PHONE_B)

        # Steady state: zero cross-contamination in EITHER direction.
        assert cross_office_rows(deck_a, OFFICE_A) == []
        assert cross_office_rows(deck_b, OFFICE_B) == []
        # Positive content check: each deck actually rendered its OWN row (not just empty).
        assert [r["office"] for r in deck_a[SUMMARY_TABLE].data] == [OFFICE_A]
        assert [r["office"] for r in deck_b[SUMMARY_TABLE].data] == [OFFICE_B]

    async def test_tc_red_merge_collision_leaks_office_b_into_office_a(self) -> None:
        """TC-RED-MERGE: A and B share a phone; the office-grain aggregate returns BOTH
        offices' rows under that one phone -> office A's deck contains office B's row.

        The current distributor has NO per-row office-identity guard, so it SILENTLY
        MERGES. This characterizes the B-2 defect: the leak is REAL and unguarded.
        """
        wf, _ = _make_distributor()
        # Faithful collision: ONE phone entry carrying two office-attributed rows (the
        # grain is office_phone x office, so a shared phone yields >1 office row).
        envelope = _envelope(
            [
                _phone_result(
                    SHARED_PHONE,
                    [_row(OFFICE_A, SHARED_PHONE, 100), _row(OFFICE_B, SHARED_PHONE, 200)],
                )
            ]
        )
        _seed_summary(wf, envelope)

        deck_a = await _render_deck(wf, SHARED_PHONE)  # office A's offer resolves here

        leak = cross_office_rows(deck_a, OFFICE_A)
        # The canary BITES: office B's row is present in office A's partner deck.
        assert leak, "expected the shared-phone collision to leak office B's row into A's deck"
        assert any(r["office"] == OFFICE_B for r in leak)
        # And the leaked row is office-attributable (re-identifying): it names OFFICE_B.
        assert {r["office"] for r in deck_a[SUMMARY_TABLE].data} == {OFFICE_A, OFFICE_B}

    async def test_tc_red_overwrite_collision_replaces_office_a_with_office_b(self) -> None:
        """TC-RED-OVERWRITE: A and B share a phone; two same-phone envelope entries ->
        ``distribute_per_office`` last-write-wins (operator.py:78) -> office A's deck is
        REPLACED by office B's rows entirely (A's own data vanishes -- worse than a merge).
        """
        wf, _ = _make_distributor()
        envelope = _envelope(
            [
                _phone_result(SHARED_PHONE, [_row(OFFICE_A, SHARED_PHONE, 100)]),
                _phone_result(SHARED_PHONE, [_row(OFFICE_B, SHARED_PHONE, 200)]),
            ]
        )
        _seed_summary(wf, envelope)

        deck_a = await _render_deck(wf, SHARED_PHONE)

        rendered = {r["office"] for r in deck_a[SUMMARY_TABLE].data}
        # The detector catches B's row in A's deck...
        assert cross_office_rows(deck_a, OFFICE_A), "overwrite collision must leak a B row"
        # ...and A's OWN data has been silently dropped (last-write-wins replaced it).
        assert rendered == {OFFICE_B}

    async def test_tc_teeth_detector_is_two_sided_non_vacuous(self) -> None:
        """TC-TEETH: the SAME detector + SAME render path returns [] on the clean envelope
        and non-empty on the collision envelope -- two-sided proof it bites ONLY on the
        defect (not on row shape). A detector that cannot flip proves nothing.
        """
        wf_clean, _ = _make_distributor()
        _seed_summary(
            wf_clean,
            _envelope(
                [
                    _phone_result(PHONE_A, [_row(OFFICE_A, PHONE_A, 100)]),
                    _phone_result(PHONE_B, [_row(OFFICE_B, PHONE_B, 200)]),
                ]
            ),
        )
        clean_deck = await _render_deck(wf_clean, PHONE_A)

        wf_collision, _ = _make_distributor()
        _seed_summary(
            wf_collision,
            _envelope(
                [
                    _phone_result(
                        SHARED_PHONE,
                        [_row(OFFICE_A, SHARED_PHONE, 100), _row(OFFICE_B, SHARED_PHONE, 200)],
                    )
                ]
            ),
        )
        collision_deck = await _render_deck(wf_collision, SHARED_PHONE)

        # Negative control passes (clean), positive control fires (collision): TEETH.
        assert cross_office_rows(clean_deck, OFFICE_A) == []
        assert cross_office_rows(collision_deck, OFFICE_A) != []

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "B-2 UNFIXED: office_phone is the per-office distribution key but its "
            "uniqueness is EMERGENT not enforced (autom8y-data repositories/business.py:192 "
            ".first(), no ORDER BY, no UNIQUE constraint). The Asana distributor at "
            "insights/workflow.py:806 has NO per-row office-identity guard, so a shared-phone "
            "collision silently merges office B's rows into office A's partner deck. This "
            "xfail(strict) flips to XPASS -> SUITE-FAIL when B-2 lands (UNIQUE/dedup on the "
            "key, or re-key distribution to chiropractors.guid), forcing this marker's "
            "removal and promoting the canary to a permanent live guard."
        ),
    )
    async def test_tc_invariant_b1_isolation_holds_under_collision(self) -> None:
        """TC-INVARIANT-B1: the per-office isolation invariant asserted as it SHOULD hold.

        Under a shared-phone collision, office A's deck MUST contain office A's rows ONLY.
        This is the invariant a FIXED distributor (post-B-2) satisfies. It XFAILs today --
        the loud, machine-readable proof that the invariant is UNGUARDED.
        """
        wf, _ = _make_distributor()
        envelope = _envelope(
            [
                _phone_result(
                    SHARED_PHONE,
                    [_row(OFFICE_A, SHARED_PHONE, 100), _row(OFFICE_B, SHARED_PHONE, 200)],
                )
            ]
        )
        _seed_summary(wf, envelope)

        deck_a = await _render_deck(wf, SHARED_PHONE)

        # The invariant: ZERO foreign-office rows in office A's deck. FAILS today (B-2).
        assert cross_office_rows(deck_a, OFFICE_A) == []

    async def test_tc_scope_no_wire_call_no_sa_fleet_read(self) -> None:
        """TC-SCOPE: pure test-harness fault injection. The distribution path NEVER calls
        an SA fleet-read method -- no prod call, no live export, no fleet fallback.
        """
        wf, data = _make_distributor()
        _seed_summary(
            wf,
            _envelope(
                [
                    _phone_result(
                        SHARED_PHONE,
                        [_row(OFFICE_A, SHARED_PHONE, 100), _row(OFFICE_B, SHARED_PHONE, 200)],
                    )
                ]
            ),
        )

        await _render_deck(wf, SHARED_PHONE)

        data.get_leads_async.assert_not_called()
        data.get_insights_async.assert_not_called()
        data.get_appointments_async.assert_not_called()
        data.get_reconciliation_async.assert_not_called()
