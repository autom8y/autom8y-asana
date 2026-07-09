"""Two-sided orchestrator teeth for the backfill (TDD S4 §8 T-B*).

Integration tests against a FAKE MonolithEvidenceSource + a FAKE AsanaClient (no
AWS, no live Asana). Every guard is proven RED-on-the-defect AND GREEN-without,
per G-THEATER. The load-bearing teeth:

  - T-B1  happy path stamps (resolvable Flowing clinic, current=Sent -> ADVANCE)
  - T-B2  mangled-log fixture REJECTED loudly (MalformedLogRecordError, counted,
          no phantom clinic)
  - T-B3  downgrade attempt SKIPPED + counted (current=Live, derived Flowing ->
          REFUSE_REGRESSION, zero write)
  - T-B4  unresolvable clinic -> UNRESOLVED bucket, never guessed
  - T-B5  denominator cap -> ABORT LOUD (DenominatorCapError, no PLAN emitted)
  - T-B6  inbox-key equivalence (captured key == chiropractor_guid -> resolves)
  - T-B7  idempotent re-run (2nd apply -> NO_OP, zero additional PUT)
  - T-B8  Nation of Wellness treated like every clinic (no hardcode)
  - T-B9  guest-PAT scope honored (no workspace-level custom_fields listing)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.automation.forwarding_stage_backfill.backfill import (
    BackfillAction,
    BackfillMode,
    BackfillWriteConfig,
    ForwardingStageBackfill,
)
from autom8_asana.automation.forwarding_stage_backfill.evidence_source import (
    BookingGatherResult,
    ConfirmationGatherResult,
    DenominatorCapError,
    MalformedLogRecordError,
    parse_inbox_or_raise,
)
from autom8_asana.domain.forwarding_stage import ForwardingStage
from autom8_asana.domain.forwarding_stage_backfill import BookingSignal, ConfirmationSignal

# ---------------------------------------------------------------------------
# Constants (test values mirroring the S1 receipts fixtures).
# ---------------------------------------------------------------------------

CI_PROJECT_GID = "1209442849265632"  # CALENDAR_INTEGRATIONS_PROJECT
BUSINESSES_PROJECT_GID = "1200653012566782"  # BUSINESS_PROJECT
COMPANY_ID_FIELD_GID = "1200000000000099"
FORWARDING_FIELD_GID = "1216419441591239"

STAGE_OPTION_GIDS = {
    "Sent": "1216419441591240",
    "Approved": "1216419441591241",
    "Verified": "1216419441591242",
    "Stalled": "1216419441591243",
    "Flowing": "1216419441591244",
    "Live": "1216419441591245",
    "Inactive": "1216419441591246",
}

FLOWING_INBOX = "d167d635aaaa4bbbccccddddeeeeffff"
NOW_LASTSEEN = datetime(2026, 7, 9, 10, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Fakes.
# ---------------------------------------------------------------------------


class FakeEvidenceSource:
    """A MonolithEvidenceSource that returns pre-seeded gather results (no AWS)."""

    def __init__(
        self,
        *,
        booking: BookingGatherResult | None = None,
        confirmations: ConfirmationGatherResult | None = None,
    ) -> None:
        self._booking = booking or BookingGatherResult(
            signals={}, row_count=0, cap_hit=False, booking_mail_total=0
        )
        self._confirmations = confirmations or ConfirmationGatherResult(
            signals={}, row_count=0, cap_hit=False
        )

    def booking_mail_counts(self, window_days: int) -> BookingGatherResult:
        return self._booking

    def forwarding_confirmations(self, window_days: int) -> ConfirmationGatherResult:
        return self._confirmations


def _ci_row(inbox_task_gid: str, *, in_ci: bool = True) -> dict[str, Any]:
    projects = [{"gid": CI_PROJECT_GID}] if in_ci else [{"gid": "9999"}]
    return {"gid": inbox_task_gid, "name": "PLAY: CI", "projects": projects}


def _ci_raw(option_gid: str | None) -> dict[str, Any]:
    enum_value = {"gid": option_gid} if option_gid else None
    return {
        "custom_fields": [
            {"gid": FORWARDING_FIELD_GID, "name": "Forwarding Stage", "enum_value": enum_value},
        ],
    }


def _business_row(gid: str) -> dict[str, Any]:
    """A tasks/search row that is a member of the Businesses project (dna_holder)."""
    return {"gid": gid, "name": "Business", "projects": [{"gid": BUSINESSES_PROJECT_GID}]}


def _fake_client(
    *,
    ci_matches: dict[str, list[dict[str, Any]]] | None = None,
    current_by_gid: dict[str, str | None] | None = None,
) -> MagicMock:
    """Fake AsanaClient wired for resolution (http.get) + read (get_async) + PUT.

    ``ci_matches`` maps company_id -> the CI-candidate rows, modelled per the
    ruled ENTITY-DESCEND join: a resolvable company_id search-returns its single
    Business (dna_holder) row, and the candidate rows hang UNDER that Business as
    subtasks (the membership-filtered descend then collects the CI members). An
    absent company_id search-returns [] (no Business card -> unresolved).
    ``current_by_gid`` maps ci_task_gid -> the current option GID (or None unset).
    """
    ci_matches = ci_matches or {}
    current_by_gid = current_by_gid or {}
    client = MagicMock()
    client.default_workspace_gid = "1140000000000001"

    # company_id -> its Business card gid; Business gid -> depth-1 subtask rows.
    business_gid_by_company = {cid: f"biz-{cid}" for cid in ci_matches}
    subtasks_by_parent = {f"biz-{cid}": rows for cid, rows in ci_matches.items()}

    async def _get(url: str, *, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        params = params or {}
        if url.endswith("/tasks/search"):
            # The resolver keys on custom_fields.{field}.value == company_id.
            key = f"custom_fields.{COMPANY_ID_FIELD_GID}.value"
            company_id = params.get(key)
            biz = business_gid_by_company.get(str(company_id))
            return [_business_row(biz)] if biz else []
        if url.startswith("/tasks/") and url.endswith("/subtasks"):
            parent_gid = url.split("/")[2]
            return subtasks_by_parent.get(parent_gid, [])
        raise AssertionError(f"unexpected GET in fake client: {url}")

    client.http.get = AsyncMock(side_effect=_get)

    async def _get_async(ci_gid: str, *, raw: bool, opt_fields: list[str]) -> dict[str, Any]:
        return _ci_raw(current_by_gid.get(ci_gid))

    client.tasks.get_async = AsyncMock(side_effect=_get_async)
    client.tasks.update_async = AsyncMock(return_value=MagicMock())
    # Guard: a workspace-level custom_fields listing must NEVER be called.
    client.custom_fields.get_async = AsyncMock(
        side_effect=AssertionError("workspace-level custom_fields listing is forbidden")
    )
    return client


def _active_cfg() -> BackfillWriteConfig:
    return BackfillWriteConfig(
        enabled=True, field_gid=FORWARDING_FIELD_GID, option_gids=dict(STAGE_OPTION_GIDS)
    )


def _booking_result(**counts: int) -> BookingGatherResult:
    signals = {inbox: BookingSignal(count=n, last_seen=NOW_LASTSEEN) for inbox, n in counts.items()}
    return BookingGatherResult(
        signals=signals,
        row_count=len(signals),
        cap_hit=False,
        booking_mail_total=sum(counts.values()),
    )


def _confirmation_result(**ages_h: float) -> ConfirmationGatherResult:
    now = datetime.now(UTC)
    signals = {
        inbox: ConfirmationSignal(confirmed_at=now - timedelta(hours=age))
        for inbox, age in ages_h.items()
    }
    return ConfirmationGatherResult(signals=signals, row_count=len(signals), cap_hit=False)


def _orchestrator(
    *,
    booking: BookingGatherResult | None = None,
    confirmations: ConfirmationGatherResult | None = None,
    client: MagicMock,
    cfg: BackfillWriteConfig | None = None,
) -> ForwardingStageBackfill:
    return ForwardingStageBackfill(
        evidence_source=FakeEvidenceSource(booking=booking, confirmations=confirmations),
        client=client,
        company_id_field_gid=COMPANY_ID_FIELD_GID,
        write_config=cfg or _active_cfg(),
    )


# ---------------------------------------------------------------------------
# Teeth.
# ---------------------------------------------------------------------------


class TestOrchestratorTeeth:
    @pytest.mark.asyncio
    async def test_tb1_happy_path_stamps(self) -> None:
        """T-B1: a resolvable Flowing clinic, current=Sent -> ADVANCE, action=stamp.

        RED side: a resolvable booking clinic that does NOT produce a stamp row
        (e.g. an orchestrator that never routes ADVANCE to stamp) FAILS.
        """
        client = _fake_client(
            ci_matches={FLOWING_INBOX: [_ci_row("ci-1")]},
            current_by_gid={"ci-1": STAGE_OPTION_GIDS["Sent"]},
        )
        orch = _orchestrator(booking=_booking_result(**{FLOWING_INBOX: 50}), client=client)
        plan = await orch.run(mode=BackfillMode.APPLY, window_days=21)

        (row,) = plan.rows
        assert row.action == BackfillAction.STAMP.value
        assert row.derived_stage == ForwardingStage.FLOWING.value
        assert row.current_stage == ForwardingStage.SENT.value
        assert row.asana_response_status == "ok"
        client.tasks.update_async.assert_awaited_once()
        assert plan.counts["stamp_Flowing"] == 1

    @pytest.mark.asyncio
    async def test_tb2_mangled_log_record_rejected_loudly(self) -> None:
        """T-B2: a mangled @message (no inbox capture) is REJECTED per-record,
        counted, and produces NO phantom clinic.

        RED side: a parser that silently yields a 0-inbox row (or crashes the
        whole run) FAILS. The strict-form gate ``parse_inbox_or_raise`` raises
        MalformedLogRecordError; the gather counts it and never emits a clinic.
        """
        # The strict parser rejects a record with no inbox capture, loudly.
        with pytest.raises(MalformedLogRecordError):
            parse_inbox_or_raise({"@message": '{"garbage": "no-inbox", "truncated'})

        # A well-formed record with an inbox passes.
        assert parse_inbox_or_raise({"inbox": FLOWING_INBOX}) == FLOWING_INBOX

        # And the gather-result malformed count surfaces in the PLAN header
        # WITHOUT a phantom clinic (the malformed row is not in signals).
        booking = BookingGatherResult(
            signals={FLOWING_INBOX: BookingSignal(3, NOW_LASTSEEN)},
            row_count=2,  # one good row + one malformed (dropped)
            cap_hit=False,
            malformed_records=1,
            booking_mail_total=3,
        )
        client = _fake_client(
            ci_matches={FLOWING_INBOX: [_ci_row("ci-1")]},
            current_by_gid={"ci-1": None},
        )
        orch = _orchestrator(booking=booking, client=client)
        plan = await orch.run(mode=BackfillMode.PLAN, window_days=21)
        assert plan.header.malformed_booking_records == 1
        assert plan.header.distinct_clinics_observed == 1  # no phantom
        assert {r.inbox_uuid for r in plan.rows} == {FLOWING_INBOX}

    @pytest.mark.asyncio
    async def test_tb3_downgrade_attempt_skipped_and_counted(self) -> None:
        """T-B3: current=Live, derived Flowing -> REFUSE_REGRESSION, zero write.

        RED side: a Live clinic with a derived Flowing that produces a PUT FAILS
        (the machine must NEVER regress). The refuse is LOUD and counted.
        """
        client = _fake_client(
            ci_matches={FLOWING_INBOX: [_ci_row("ci-live")]},
            current_by_gid={"ci-live": STAGE_OPTION_GIDS["Live"]},
        )
        orch = _orchestrator(booking=_booking_result(**{FLOWING_INBOX: 10}), client=client)
        plan = await orch.run(mode=BackfillMode.APPLY, window_days=21)

        (row,) = plan.rows
        assert row.action == BackfillAction.REFUSE.value
        assert row.decision_outcome == "stage_regression_refused"
        client.tasks.update_async.assert_not_called()
        assert plan.counts["refuse"] == 1

    @pytest.mark.asyncio
    async def test_tb4_unresolvable_clinic_goes_to_unresolved_never_guessed(self) -> None:
        """T-B4: a 0-match (truncated) inbox -> UNRESOLVED bucket, raw inbox
        recorded, NO stamp, NO guess.

        RED side: a truncated inbox resolving to a guessed/fallback task FAILS.
        """
        truncated = "e5a68603ccce"  # the UT-3 malformed class; 0 CI matches
        client = _fake_client(ci_matches={})  # nothing resolves
        orch = _orchestrator(booking=_booking_result(**{truncated: 4}), client=client)
        plan = await orch.run(mode=BackfillMode.APPLY, window_days=21)

        assert plan.rows == []  # no stampable row
        (u,) = plan.unresolved
        assert u.inbox_uuid == truncated
        assert u.action == BackfillAction.UNRESOLVED.value
        assert u.ci_task_gid is None
        client.tasks.update_async.assert_not_called()
        assert plan.counts["unresolved"] == 1

    @pytest.mark.asyncio
    async def test_tb4b_ambiguous_ci_match_goes_to_unresolved(self) -> None:
        """T-B4b: >1 CI match -> UNRESOLVED (never pick a receiver silently)."""
        client = _fake_client(
            ci_matches={FLOWING_INBOX: [_ci_row("ci-a"), _ci_row("ci-b")]},
        )
        orch = _orchestrator(booking=_booking_result(**{FLOWING_INBOX: 4}), client=client)
        plan = await orch.run(mode=BackfillMode.PLAN, window_days=21)
        assert plan.counts["unresolved"] == 1
        client.tasks.update_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_tb5_denominator_cap_aborts_loudly(self) -> None:
        """T-B5: a capped (cap_hit=True) booking result -> DenominatorCapError,
        run aborts, NO PLAN.

        RED side: a capped result producing a partial PLAN (that looks complete)
        FAILS -- the true denominator is unknown, so the run must abort.
        """
        capped = BookingGatherResult(
            signals={FLOWING_INBOX: BookingSignal(1, NOW_LASTSEEN)},
            row_count=10000,
            cap_hit=True,
            booking_mail_total=1,
        )
        client = _fake_client(ci_matches={FLOWING_INBOX: [_ci_row("ci-1")]})
        orch = _orchestrator(booking=capped, client=client)
        with pytest.raises(DenominatorCapError):
            await orch.run(mode=BackfillMode.PLAN, window_days=21)

    @pytest.mark.asyncio
    async def test_tb6_inbox_key_equivalence_resolves(self) -> None:
        """T-B6: the derived key == chiropractor_guid == Company-ID value resolves.

        The evidence key (mailbox local-part) equals the Company-ID field value
        the CI resolution searches on. When the fake keys the CI match on exactly
        that value, the clinic resolves and stamps.

        RED side: a key that kept the @domain (key != Company-ID value) would
        0-match into UNRESOLVED (the silent 'no clinics' failure). Here the key
        matches and resolves -- the two-sided partner is T-B4 (0-match).
        """
        client = _fake_client(
            ci_matches={FLOWING_INBOX: [_ci_row("ci-1")]},  # keyed on the bare guid
            current_by_gid={"ci-1": None},
        )
        orch = _orchestrator(booking=_booking_result(**{FLOWING_INBOX: 7}), client=client)
        plan = await orch.run(mode=BackfillMode.PLAN, window_days=21)
        (row,) = plan.rows
        assert row.ci_task_gid == "ci-1"
        assert row.action == BackfillAction.STAMP.value

    @pytest.mark.asyncio
    async def test_tb7_idempotent_rerun_no_second_put(self) -> None:
        """T-B7: a 2nd apply run where current==derived -> NO_OP, zero new PUT.

        RED side: a 2nd run producing a 2nd PUT for an already-advanced clinic
        FAILS -- re-running the backfill must be safe.
        """
        # 1st run: current=Sent -> stamp Flowing.
        client = _fake_client(
            ci_matches={FLOWING_INBOX: [_ci_row("ci-1")]},
            current_by_gid={"ci-1": STAGE_OPTION_GIDS["Sent"]},
        )
        orch = _orchestrator(booking=_booking_result(**{FLOWING_INBOX: 9}), client=client)
        plan1 = await orch.run(mode=BackfillMode.APPLY, window_days=21)
        assert plan1.counts["stamp_Flowing"] == 1
        client.tasks.update_async.assert_awaited_once()

        # 2nd run: current now Flowing (already advanced) -> NO_OP, no new PUT.
        client2 = _fake_client(
            ci_matches={FLOWING_INBOX: [_ci_row("ci-1")]},
            current_by_gid={"ci-1": STAGE_OPTION_GIDS["Flowing"]},
        )
        orch2 = _orchestrator(booking=_booking_result(**{FLOWING_INBOX: 9}), client=client2)
        plan2 = await orch2.run(mode=BackfillMode.APPLY, window_days=21)
        (row,) = plan2.rows
        assert row.action == BackfillAction.NOOP.value
        client2.tasks.update_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_tb8_nation_of_wellness_treated_like_every_clinic(self) -> None:
        """T-B8: Nation of Wellness is stamped by the general derivation (no hardcode).

        RED side: a hardcoded NoW stamp independent of evidence FAILS. With
        booking mail -> Flowing; with NO evidence -> NO STAMP (both from the
        general path, no special case).
        """
        now_inbox = "1216252254927725now"  # NoW's inbox uuid (test value)
        # (a) NoW with booking mail -> Flowing.
        client = _fake_client(
            ci_matches={now_inbox: [_ci_row("ci-now")]},
            current_by_gid={"ci-now": None},
        )
        orch = _orchestrator(booking=_booking_result(**{now_inbox: 12}), client=client)
        plan = await orch.run(mode=BackfillMode.PLAN, window_days=21)
        (row,) = plan.rows
        assert row.inbox_uuid == now_inbox
        assert row.derived_stage == ForwardingStage.FLOWING.value

        # (b) NoW with NO evidence -> not observed at all -> not in the plan
        # (honest empty; the derivation never fabricates a stamp).
        empty_client = _fake_client(ci_matches={now_inbox: [_ci_row("ci-now")]})
        empty_orch = _orchestrator(client=empty_client)  # no booking, no confirmation
        empty_plan = await empty_orch.run(mode=BackfillMode.PLAN, window_days=21)
        assert empty_plan.rows == []
        assert empty_plan.counts.get("stamp", 0) == 0

    @pytest.mark.asyncio
    async def test_tb9_guest_pat_scope_no_workspace_custom_fields_listing(self) -> None:
        """T-B9: only tasks/search + tasks.get + tasks.update are used.

        RED side: any workspace-level ``custom_fields`` listing FAILS (the fake
        raises on it). The field/option GIDs arrive via config, never a listing.
        """
        client = _fake_client(
            ci_matches={FLOWING_INBOX: [_ci_row("ci-1")]},
            current_by_gid={"ci-1": None},
        )
        orch = _orchestrator(booking=_booking_result(**{FLOWING_INBOX: 3}), client=client)
        await orch.run(mode=BackfillMode.APPLY, window_days=21)
        client.custom_fields.get_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_stall_overlay_stamps(self) -> None:
        """A Verified clinic that derives Stalled -> STALL_OVERLAY -> stamp Stalled.

        Ties the derivation (>48h silent confirmation) to the S1 overlay branch.
        RED side: a Stalled derivation on a Verified clinic that refuses (rather
        than overlays) FAILS.
        """
        client = _fake_client(
            ci_matches={FLOWING_INBOX: [_ci_row("ci-1")]},
            current_by_gid={"ci-1": STAGE_OPTION_GIDS["Verified"]},
        )
        orch = _orchestrator(
            confirmations=_confirmation_result(**{FLOWING_INBOX: 72}), client=client
        )
        plan = await orch.run(mode=BackfillMode.APPLY, window_days=21)
        (row,) = plan.rows
        assert row.derived_stage == ForwardingStage.STALLED.value
        assert row.action == BackfillAction.STAMP.value
        assert plan.counts["stamp_Stalled"] == 1

    @pytest.mark.asyncio
    async def test_unknown_current_option_fails_closed_no_write(self) -> None:
        """A CI task carrying an option GID absent from the config map -> the
        UnknownStage sentinel -> validator REFUSE_UNKNOWN -> no write.

        RED side: guessing an advance off an unknown current option FAILS.
        """
        client = _fake_client(
            ci_matches={FLOWING_INBOX: [_ci_row("ci-1")]},
            current_by_gid={"ci-1": "9090909090909090"},  # not in STAGE_OPTION_GIDS
        )
        orch = _orchestrator(booking=_booking_result(**{FLOWING_INBOX: 5}), client=client)
        plan = await orch.run(mode=BackfillMode.APPLY, window_days=21)
        (row,) = plan.rows
        assert row.action == BackfillAction.REFUSE.value
        assert row.decision_outcome == "stage_unknown_refused"
        client.tasks.update_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_plan_mode_never_writes(self) -> None:
        """plan mode produces stamp rows but ZERO Asana writes.

        RED side: a plan run that PUTs FAILS -- dry-run must not mutate.
        """
        client = _fake_client(
            ci_matches={FLOWING_INBOX: [_ci_row("ci-1")]},
            current_by_gid={"ci-1": STAGE_OPTION_GIDS["Sent"]},
        )
        orch = _orchestrator(booking=_booking_result(**{FLOWING_INBOX: 50}), client=client)
        plan = await orch.run(mode=BackfillMode.PLAN, window_days=21)
        (row,) = plan.rows
        assert row.action == BackfillAction.STAMP.value  # would stamp
        client.tasks.update_async.assert_not_called()  # but did NOT


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
