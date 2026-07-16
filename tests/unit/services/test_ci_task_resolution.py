"""Tests for the extracted CI-task resolvers (TDD S4 §4 extraction).

These functions were extracted from ``receipts_service`` so the receipts route
AND the S4 backfill can share them. The S1 receipts route tests
(``tests/unit/api/routes/test_receipts.py``) re-assert the behaviour through
the service delegation; these tests lock the extracted-function contract
directly.

Join-key repair (entity-descend ruling, 2026-07-09): ``resolve_ci_task_gid``
now resolves via the entity tree -- Company-ID search to the Business
(dna_holder) card, then a membership-filtered descend (depth cap 2) to the
PLAY task multi-homed into Calendar Integrations. The fake client here models
that tree (search rows + a parent-gid -> subtask-rows map).

Duplicate-Company-ID union (remediation, 2026-07-09): hop 1 legitimately
returns MULTIPLE Business cards when a practice card and practitioner card(s)
share one Company ID (the data model's NORMAL shape -- the Total Wellness
BLOCK). The resolver descends the UNION of all matched subtrees and
adjudicates exactly-one/zero/ambiguous on the DISTINCT PLAY set.

Receipts-leg holder resolution (G3, 2026-07-16): the SAME union-descend
semantics, ported for ``_resolve_business_gid`` -- but the return value is the
HOLDING Business gid (the receipt's comment receiver), with the unique PLAY as
the disambiguator. ``resolve_play_holder_business_gid`` locks that contract:
exactly one distinct PLAY held by exactly one matched subtree resolves; zero /
>1 distinct PLAYs / a single PLAY without a single nameable holder all return
``None`` (the caller fail-closes exactly as pre-cure).

Two-sided where a guard exists: happy two-hop, direct depth-1 member,
zero-member (the membership-filter teeth), multi-member ambiguous refuse,
depth cap, truncation loud-abort, 0 Business matches, duplicate-Company-ID
union (one-PLAY resolve / each-holds-one ambiguous / zero unresolved /
same-PLAY dedupe), no-workspace; and for the stage read: unset field, mapped
option, unmapped option (fail-closed sentinel).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.domain.forwarding_stage import ForwardingStage
from autom8_asana.services.ci_task_resolution import (
    SubtaskPageCapExceeded,
    UnknownStage,
    read_current_stage,
    resolve_ci_task_gid,
    resolve_play_holder_business_gid,
)

CI_PROJECT_GID = "1209442849265632"  # CALENDAR_INTEGRATIONS_PROJECT
BUSINESSES_PROJECT_GID = "1200653012566782"  # BUSINESS_PROJECT
CI_TASK_GID = "1209000000000007"
BUSINESS_GID = "1208000000000001"
HOLDER_GID = "1208000000000002"  # the "{Clinic} PLAYS/REQUESTS" holder (NOT a CI member)
COMPANY_ID_FIELD_GID = "1200000000000099"
FORWARDING_FIELD_GID = "1216419441591239"
COMPANY_ID = "d167d635aaaa4bbbccccddddeeeeffff"

STAGE_OPTION_GIDS = {
    "Verified": "1216419441591242",
    "Flowing": "1216419441591244",
    "Live": "1216419441591245",
}


def _business_row(gid: str = BUSINESS_GID, *, in_businesses: bool = True) -> dict[str, Any]:
    """A tasks/search row with (optional) Businesses-project membership."""
    projects = [{"gid": BUSINESSES_PROJECT_GID}] if in_businesses else [{"gid": "9999"}]
    return {"gid": gid, "name": "Business", "projects": projects}


def _node(gid: str, *, in_ci: bool = False) -> dict[str, Any]:
    """A subtask row; the name is deliberately unhelpful (membership-only filter)."""
    projects = [{"gid": CI_PROJECT_GID}] if in_ci else [{"gid": "9999"}]
    return {"gid": gid, "name": "an unrelated-looking task name", "projects": projects}


def _ci_raw(option_gid: str | None) -> dict[str, Any]:
    enum_value = {"gid": option_gid} if option_gid else None
    return {
        "gid": CI_TASK_GID,
        "custom_fields": [
            {"gid": "9999999999", "name": "Other", "enum_value": None},
            {"gid": FORWARDING_FIELD_GID, "name": "Forwarding Stage", "enum_value": enum_value},
        ],
    }


def _tree_client(
    *,
    search_rows: Any = None,
    subtasks: dict[str, Any] | None = None,
    raw: dict[str, Any] | None = None,
    workspace: str | None = "1140000000000001",
) -> MagicMock:
    """A fake AsanaClient modelling the entity tree.

    ``search_rows`` is what the Company-ID ``tasks/search`` returns (bare list
    or ``{"data": [...]}`` envelope); ``subtasks`` maps a parent task gid -> the
    rows its ``/tasks/{gid}/subtasks`` listing returns. Every issued GET url is
    recorded on ``client.get_urls`` (depth-cap teeth assert on it).
    """
    subtasks_by_parent = subtasks or {}
    c = MagicMock()
    c.default_workspace_gid = workspace
    get_urls: list[str] = []

    async def _get(url: str, *, params: dict[str, Any] | None = None) -> Any:
        get_urls.append(url)
        if url.endswith("/tasks/search"):
            return search_rows or []
        if url.startswith("/tasks/") and url.endswith("/subtasks"):
            return subtasks_by_parent.get(url.split("/")[2], [])
        raise AssertionError(f"unexpected GET in fake client: {url}")

    c.http.get = AsyncMock(side_effect=_get)
    c.get_urls = get_urls
    c.tasks.get_async = AsyncMock(return_value=raw)
    return c


class TestResolveCiTaskGid:
    """resolve_ci_task_gid -- the ruled entity-descend join, two-sided."""

    @pytest.mark.asyncio
    async def test_ci_member_grandchild_resolves(self) -> None:
        """Happy two-hop (the live-proven shape): Business -> holder -> PLAY.

        Exactly one CI-member grandchild resolves; a non-member sibling
        grandchild is ignored. RED side: a name-keyed or filterless collect
        would return 2+ candidates and fail the exactly-one assertion.
        """
        client = _tree_client(
            search_rows=[_business_row()],
            subtasks={
                BUSINESS_GID: [_node(HOLDER_GID)],
                HOLDER_GID: [_node(CI_TASK_GID, in_ci=True), _node("noise-1")],
                CI_TASK_GID: [],
                "noise-1": [],
            },
        )
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid == CI_TASK_GID

    @pytest.mark.asyncio
    async def test_direct_depth1_ci_member_resolves(self) -> None:
        """Robustness clause: a clinic that links the PLAY directly under the
        Business (no holder hop) still resolves."""
        client = _tree_client(
            search_rows=[_business_row()],
            subtasks={
                BUSINESS_GID: [_node(CI_TASK_GID, in_ci=True)],
                CI_TASK_GID: [],
            },
        )
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid == CI_TASK_GID

    @pytest.mark.asyncio
    async def test_zero_ci_members_returns_none(self) -> None:
        """Membership-filter teeth: a tree with exactly ONE descendant, which is
        NOT a CI member, must NOT resolve.

        RED side: REMOVING the membership filter (collecting every descendant)
        would make the holder the single 'match' and return its gid -> this
        test fires RED.
        """
        client = _tree_client(
            search_rows=[_business_row()],
            subtasks={
                BUSINESS_GID: [_node(HOLDER_GID)],
                HOLDER_GID: [],
            },
        )
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid is None

    @pytest.mark.asyncio
    async def test_multiple_ci_members_ambiguous_refused(self) -> None:
        """RED side: picking a receiver silently on >1 CI members FAILS
        (fail-closed ambiguous refuse, counted in the log)."""
        client = _tree_client(
            search_rows=[_business_row()],
            subtasks={
                BUSINESS_GID: [_node(HOLDER_GID)],
                HOLDER_GID: [_node("ci-a", in_ci=True), _node("ci-b", in_ci=True)],
                "ci-a": [],
                "ci-b": [],
            },
        )
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid is None

    @pytest.mark.asyncio
    async def test_depth_cap_ci_member_at_depth3_not_found(self) -> None:
        """Bounded descend: a CI member at depth 3 is OUT OF SCOPE (cap 2).

        Also asserts the resolver never even LISTS the depth-2 node's subtasks
        (the cap bounds the API fan-out, not just the collection).
        RED side: an unbounded recursive descend would find the deep member and
        return its gid.
        """
        client = _tree_client(
            search_rows=[_business_row()],
            subtasks={
                BUSINESS_GID: [_node("child-1")],
                "child-1": [_node("child-2")],
                "child-2": [_node("deep-ci", in_ci=True)],
            },
        )
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid is None
        assert "/tasks/child-2/subtasks" not in client.get_urls

    @pytest.mark.asyncio
    async def test_truncated_subtask_page_aborts_loud(self) -> None:
        """Cap-abort teeth (S4 discipline): a FULL subtask page (row_count ==
        cap) cannot prove completeness -> LOUD SubtaskPageCapExceeded, never a
        silent resolution over a truncated child set.

        RED side: a resolver that quietly resolved from the truncated page
        would return a gid instead of raising.
        """
        full_page = [_node(f"bulk-{i}") for i in range(100)]
        client = _tree_client(
            search_rows=[_business_row()],
            subtasks={BUSINESS_GID: full_page},
        )
        with pytest.raises(SubtaskPageCapExceeded) as exc_info:
            await resolve_ci_task_gid(client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID)
        assert exc_info.value.parent_gid == BUSINESS_GID
        assert exc_info.value.depth == 1
        assert exc_info.value.cap == 100

    @pytest.mark.asyncio
    async def test_zero_business_matches_returns_none_no_descend(self) -> None:
        """RED side: a fallback-to-first-row on 0 Business matches (guessing a
        dna_holder) FAILS; no subtask listing is ever issued."""
        client = _tree_client(search_rows=[_business_row(in_businesses=False)])
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid is None
        assert client.get_urls == [f"/workspaces/{client.default_workspace_gid}/tasks/search"]

    @pytest.mark.asyncio
    async def test_duplicate_business_single_play_union_resolves(self) -> None:
        """Duplicate-Company-ID fixture A (the Total Wellness shape): TWO
        Business cards share the Company ID (practice + practitioner -- the
        data model's NORMAL shape); only ONE subtree holds a CI PLAY. The
        union descend resolves to that PLAY.

        RED side (the two-sided teeth): with the union logic reverted to the
        len!=1 hop-1 refuse, the duplicate Business cards fail-close to None
        and this test fires RED (the exact rite-disjoint QA BLOCK).
        """
        client = _tree_client(
            search_rows=[_business_row("biz-practice"), _business_row("biz-practitioner")],
            subtasks={
                "biz-practice": [_node(HOLDER_GID)],
                HOLDER_GID: [_node(CI_TASK_GID, in_ci=True)],
                CI_TASK_GID: [],
                "biz-practitioner": [_node("practitioner-holder")],
                "practitioner-holder": [],
            },
        )
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid == CI_TASK_GID

    @pytest.mark.asyncio
    async def test_duplicate_business_each_subtree_play_ambiguous_refused(self) -> None:
        """Duplicate-Company-ID fixture B: two Businesses, EACH subtree holds
        a DISTINCT CI PLAY -> two distinct receivers in the union -> ambiguous
        refuse (fail-closed at the PLAY level, never pick)."""
        client = _tree_client(
            search_rows=[_business_row("biz-a"), _business_row("biz-b")],
            subtasks={
                "biz-a": [_node("holder-a")],
                "holder-a": [_node("ci-a", in_ci=True)],
                "ci-a": [],
                "biz-b": [_node("holder-b")],
                "holder-b": [_node("ci-b", in_ci=True)],
                "ci-b": [],
            },
        )
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid is None

    @pytest.mark.asyncio
    async def test_duplicate_business_zero_plays_unresolved(self) -> None:
        """Duplicate-Company-ID fixture C: two Businesses, zero CI PLAYs
        anywhere in the union -> UNRESOLVED (None), never a guess."""
        client = _tree_client(
            search_rows=[_business_row("biz-a"), _business_row("biz-b")],
            subtasks={
                "biz-a": [_node("holder-a")],
                "holder-a": [],
                "biz-b": [],
            },
        )
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid is None

    @pytest.mark.asyncio
    async def test_duplicate_business_same_play_both_subtrees_dedupes_resolves(self) -> None:
        """Distinct-set teeth: the SAME PLAY reachable from BOTH subtrees is
        ONE distinct receiver, not an ambiguity -> resolves.

        RED side: adjudicating on the raw collected list (no dedupe) would
        count the PLAY twice and refuse as ambiguous."""
        client = _tree_client(
            search_rows=[_business_row("biz-a"), _business_row("biz-b")],
            subtasks={
                "biz-a": [_node("holder-a")],
                "holder-a": [_node(CI_TASK_GID, in_ci=True)],
                "biz-b": [_node("holder-b")],
                "holder-b": [_node(CI_TASK_GID, in_ci=True)],
                CI_TASK_GID: [],
            },
        )
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid == CI_TASK_GID

    @pytest.mark.asyncio
    async def test_no_workspace_returns_none_no_call(self) -> None:
        """RED side: issuing a workspace-less search FAILS -- refuse rather than guess."""
        client = _tree_client(search_rows=[_business_row()], workspace=None)
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid is None
        client.http.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_wrapped_data_envelope_is_unwrapped(self) -> None:
        """The resolver dual-handles a ``{"data": [...]}`` search envelope."""
        client = _tree_client(
            search_rows={"data": [_business_row()]},
            subtasks={
                BUSINESS_GID: [_node(CI_TASK_GID, in_ci=True)],
                CI_TASK_GID: [],
            },
        )
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid == CI_TASK_GID


class TestResolvePlayHolderBusinessGid:
    """resolve_play_holder_business_gid -- the receipts-leg union descend (G3).

    Same descend machinery as ``resolve_ci_task_gid`` (membership-filtered,
    name-free, depth cap 2, page-cap loud abort), but the RESOLVED VALUE is the
    HOLDING Business gid -- the receipts comment threads onto the Business card,
    so the unique PLAY is the disambiguator, not the target. The fake never
    needs the search leg: the function takes the hop-1 Business gids as input.
    """

    # The live Total Wellness shape (the G3 first-real-client defect).
    PRACTICE = "1214127219419742"  # "Total Wellness Center" -- holds the PLAY
    PRACTITIONER = "1214420107547660"  # "Holly R. Geersen DC" -- zero PLAYs
    PLAY = "1215766139321621"

    @pytest.mark.asyncio
    async def test_tw_duplicate_single_play_resolves_holding_business(self) -> None:
        """The G3 cure (live TW shape): two Business subtrees, ONE PLAY under the
        practice's holder, practitioner subtree empty -> the PRACTICE gid.

        RED side: a Business-level len!=1 adjudication (the pre-cure
        _resolve_business_gid) has no single Business to name and fail-closes --
        exactly the CompanyAmbiguous/409 that dropped Total Wellness.
        """
        client = _tree_client(
            subtasks={
                self.PRACTICE: [_node(HOLDER_GID)],
                HOLDER_GID: [_node(self.PLAY, in_ci=True), _node("noise-1")],
                self.PRACTITIONER: [_node("practitioner-holder")],
                "practitioner-holder": [],
            },
        )
        gid = await resolve_play_holder_business_gid(
            client, COMPANY_ID, business_gids=[self.PRACTICE, self.PRACTITIONER]
        )
        assert gid == self.PRACTICE

    @pytest.mark.asyncio
    async def test_direct_depth1_play_resolves_holder(self) -> None:
        """Robustness clause parity: a PLAY linked DIRECTLY under one Business
        (no holder hop) still names that Business."""
        client = _tree_client(
            subtasks={
                self.PRACTICE: [_node(self.PLAY, in_ci=True)],
                self.PLAY: [],
                self.PRACTITIONER: [],
            },
        )
        gid = await resolve_play_holder_business_gid(
            client, COMPANY_ID, business_gids=[self.PRACTICE, self.PRACTITIONER]
        )
        assert gid == self.PRACTICE

    @pytest.mark.asyncio
    async def test_two_distinct_plays_refused(self) -> None:
        """RED side (no over-relax): EACH subtree holds a DISTINCT PLAY -> two
        distinct receivers -> ``None`` (fail-closed at the PLAY level, never
        pick)."""
        client = _tree_client(
            subtasks={
                self.PRACTICE: [_node("holder-a")],
                "holder-a": [_node("play-a", in_ci=True)],
                self.PRACTITIONER: [_node("holder-b")],
                "holder-b": [_node("play-b", in_ci=True)],
            },
        )
        gid = await resolve_play_holder_business_gid(
            client, COMPANY_ID, business_gids=[self.PRACTICE, self.PRACTITIONER]
        )
        assert gid is None

    @pytest.mark.asyncio
    async def test_two_plays_in_one_subtree_refused(self) -> None:
        """Adjudication is on the DISTINCT PLAY SET, not per-Business: TWO PLAYs
        under the SAME subtree (the other empty) is still ambiguous -> ``None``.

        RED side: a per-Business exactly-one rule would call the practice
        subtree ambiguous but could 'resolve' via a wrong reduction; the set
        rule refuses outright.
        """
        client = _tree_client(
            subtasks={
                self.PRACTICE: [_node("holder-a")],
                "holder-a": [_node("play-a", in_ci=True), _node("play-b", in_ci=True)],
                self.PRACTITIONER: [],
            },
        )
        gid = await resolve_play_holder_business_gid(
            client, COMPANY_ID, business_gids=[self.PRACTICE, self.PRACTITIONER]
        )
        assert gid is None

    @pytest.mark.asyncio
    async def test_zero_plays_refused(self) -> None:
        """Zero PLAYs anywhere in the union -> no disambiguating evidence ->
        ``None`` (the caller keeps the pre-cure fail-close)."""
        client = _tree_client(
            subtasks={
                self.PRACTICE: [_node("holder-a")],
                "holder-a": [],
                self.PRACTITIONER: [],
            },
        )
        gid = await resolve_play_holder_business_gid(
            client, COMPANY_ID, business_gids=[self.PRACTICE, self.PRACTITIONER]
        )
        assert gid is None

    @pytest.mark.asyncio
    async def test_empty_business_gids_refused(self) -> None:
        """Degenerate input: no Business gids -> ``None``, zero API calls."""
        client = _tree_client(subtasks={})
        gid = await resolve_play_holder_business_gid(client, COMPANY_ID, business_gids=[])
        assert gid is None
        client.http.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_same_play_under_both_subtrees_refused(self) -> None:
        """DELIBERATE divergence from resolve_ci_task_gid's same-PLAY dedupe:
        there the PLAY is the target (one distinct PLAY -> resolve); HERE the
        Business is the target, and a PLAY reachable from BOTH subtrees names no
        single holder -> ``None`` (never pick a receiver silently).

        Structurally impossible via Asana subtask parentage (one parent per
        task), guarded anyway.
        """
        client = _tree_client(
            subtasks={
                self.PRACTICE: [_node("holder-a")],
                "holder-a": [_node(self.PLAY, in_ci=True)],
                self.PRACTITIONER: [_node("holder-b")],
                "holder-b": [_node(self.PLAY, in_ci=True)],
            },
        )
        gid = await resolve_play_holder_business_gid(
            client, COMPANY_ID, business_gids=[self.PRACTICE, self.PRACTITIONER]
        )
        assert gid is None

    @pytest.mark.asyncio
    async def test_duplicate_input_gids_deduped(self) -> None:
        """The same Business gid passed twice is descended once and cannot
        manufacture a phantom second holder."""
        client = _tree_client(
            subtasks={
                self.PRACTICE: [_node(HOLDER_GID)],
                HOLDER_GID: [_node(self.PLAY, in_ci=True)],
            },
        )
        gid = await resolve_play_holder_business_gid(
            client, COMPANY_ID, business_gids=[self.PRACTICE, self.PRACTICE]
        )
        assert gid == self.PRACTICE
        subtask_urls = [u for u in client.get_urls if u.endswith("/subtasks")]
        assert subtask_urls.count(f"/tasks/{self.PRACTICE}/subtasks") == 1

    @pytest.mark.asyncio
    async def test_truncated_subtask_page_aborts_loud(self) -> None:
        """Cap-abort teeth: a FULL page under ANY matched Business poisons the
        whole union -> LOUD SubtaskPageCapExceeded, never a silent resolution
        over a truncated child set (even though the OTHER subtree alone would
        have resolved cleanly)."""
        full_page = [_node(f"bulk-{i}") for i in range(100)]
        client = _tree_client(
            subtasks={
                self.PRACTICE: [_node(HOLDER_GID)],
                HOLDER_GID: [_node(self.PLAY, in_ci=True)],
                self.PRACTITIONER: full_page,
            },
        )
        with pytest.raises(SubtaskPageCapExceeded) as exc_info:
            await resolve_play_holder_business_gid(
                client, COMPANY_ID, business_gids=[self.PRACTICE, self.PRACTITIONER]
            )
        assert exc_info.value.parent_gid == self.PRACTITIONER
        assert exc_info.value.cap == 100

    @pytest.mark.asyncio
    async def test_depth3_play_out_of_scope(self) -> None:
        """Bounded descend parity: a PLAY at depth 3 is OUT OF SCOPE (cap 2) ->
        the union sees zero PLAYs -> ``None``, and the depth-2 node's subtasks
        are never even listed."""
        client = _tree_client(
            subtasks={
                self.PRACTICE: [_node("child-1")],
                "child-1": [_node("child-2")],
                "child-2": [_node("deep-play", in_ci=True)],
                self.PRACTITIONER: [],
            },
        )
        gid = await resolve_play_holder_business_gid(
            client, COMPANY_ID, business_gids=[self.PRACTICE, self.PRACTITIONER]
        )
        assert gid is None
        assert "/tasks/child-2/subtasks" not in client.get_urls


class TestReadCurrentStage:
    """read_current_stage -- unset, mapped option, unmapped -> UnknownStage."""

    @pytest.mark.asyncio
    async def test_unset_field_returns_none(self) -> None:
        """RED side: reading an unset field as a stage FAILS."""
        client = _tree_client(raw=_ci_raw(None))
        result = await read_current_stage(
            client, CI_TASK_GID, field_gid=FORWARDING_FIELD_GID, option_gids=STAGE_OPTION_GIDS
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_mapped_option_returns_stage(self) -> None:
        """RED side: failing to invert the option-GID map FAILS to read Verified."""
        client = _tree_client(raw=_ci_raw(STAGE_OPTION_GIDS["Verified"]))
        result = await read_current_stage(
            client, CI_TASK_GID, field_gid=FORWARDING_FIELD_GID, option_gids=STAGE_OPTION_GIDS
        )
        assert result is ForwardingStage.VERIFIED

    @pytest.mark.asyncio
    async def test_unmapped_option_returns_unknown_sentinel(self) -> None:
        """RED side (fail-closed teeth): an option GID absent from the config map
        must return the UnknownStage sentinel (so the validator fail-closes), NOT
        None (which would look 'unset' and allow an advance) and NOT a guessed
        ForwardingStage."""
        client = _tree_client(raw=_ci_raw("9090909090909090"))
        result = await read_current_stage(
            client, CI_TASK_GID, field_gid=FORWARDING_FIELD_GID, option_gids=STAGE_OPTION_GIDS
        )
        assert isinstance(result, UnknownStage)
        assert result.option_gid == "9090909090909090"

    @pytest.mark.asyncio
    async def test_field_absent_from_task_returns_none(self) -> None:
        """A task without the forwarding-stage field at all reads None (unset)."""
        client = _tree_client(raw={"gid": CI_TASK_GID, "custom_fields": []})
        result = await read_current_stage(
            client, CI_TASK_GID, field_gid=FORWARDING_FIELD_GID, option_gids=STAGE_OPTION_GIDS
        )
        assert result is None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
