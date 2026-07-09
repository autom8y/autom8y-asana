"""Tests for the extracted CI-task resolvers (TDD S4 §4 extraction).

These functions were extracted VERBATIM from ``receipts_service`` so the
receipts route AND the S4 backfill can share them. The S1 receipts route tests
(``tests/unit/api/routes/test_receipts.py``) re-assert the SAME behaviour through
the service delegation (behaviour-preserving extraction); these tests lock the
extracted-function contract directly (mirroring the S1 resolver cases at the
function level).

Two-sided where a guard exists: 0 matches, >1 matches, unset field, mapped
option, unmapped option (fail-closed sentinel).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.domain.forwarding_stage import ForwardingStage
from autom8_asana.services.ci_task_resolution import (
    UnknownStage,
    read_current_stage,
    resolve_ci_task_gid,
)

CI_PROJECT_GID = "1209442849265632"  # CALENDAR_INTEGRATIONS_PROJECT
CI_TASK_GID = "1209000000000007"
COMPANY_ID_FIELD_GID = "1200000000000099"
FORWARDING_FIELD_GID = "1216419441591239"
COMPANY_ID = "d167d635aaaa4bbbccccddddeeeeffff"

STAGE_OPTION_GIDS = {
    "Verified": "1216419441591242",
    "Flowing": "1216419441591244",
    "Live": "1216419441591245",
}


def _ci_row(gid: str = CI_TASK_GID, *, in_ci: bool = True) -> dict[str, Any]:
    projects = [{"gid": CI_PROJECT_GID}] if in_ci else [{"gid": "9999"}]
    return {"gid": gid, "name": "PLAY: CI Task", "projects": projects}


def _ci_raw(option_gid: str | None) -> dict[str, Any]:
    enum_value = {"gid": option_gid} if option_gid else None
    return {
        "gid": CI_TASK_GID,
        "custom_fields": [
            {"gid": "9999999999", "name": "Other", "enum_value": None},
            {"gid": FORWARDING_FIELD_GID, "name": "Forwarding Stage", "enum_value": enum_value},
        ],
    }


def _client(
    *,
    search_rows: list[dict[str, Any]] | None = None,
    raw: dict[str, Any] | None = None,
    workspace: str | None = "1140000000000001",
) -> MagicMock:
    c = MagicMock()
    c.default_workspace_gid = workspace
    c.http.get = AsyncMock(return_value=search_rows or [])
    c.tasks.get_async = AsyncMock(return_value=raw)
    return c


class TestResolveCiTaskGid:
    """resolve_ci_task_gid -- exactly-1 match, 0-match, >1-match, no-workspace."""

    @pytest.mark.asyncio
    async def test_exactly_one_match_returns_gid(self) -> None:
        """RED side: filtering that ignores project membership (returning a
        Business-only row) would return the wrong gid."""
        client = _client(search_rows=[_ci_row(), _ci_row(gid="other", in_ci=False)])
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid == CI_TASK_GID

    @pytest.mark.asyncio
    async def test_zero_matches_returns_none(self) -> None:
        """RED side: a fallback-to-first-row on 0 CI matches (guessing) FAILS."""
        client = _client(search_rows=[_ci_row(in_ci=False)])
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid is None

    @pytest.mark.asyncio
    async def test_more_than_one_match_returns_none(self) -> None:
        """RED side: picking a receiver silently on >1 match FAILS (fail-closed)."""
        client = _client(search_rows=[_ci_row(gid="a"), _ci_row(gid="b")])
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid is None

    @pytest.mark.asyncio
    async def test_no_workspace_returns_none_no_call(self) -> None:
        """RED side: issuing a workspace-less search FAILS -- refuse rather than guess."""
        client = _client(search_rows=[_ci_row()], workspace=None)
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid is None
        client.http.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_wrapped_data_envelope_is_unwrapped(self) -> None:
        """The resolver dual-handles a ``{"data": [...]}`` envelope and a bare list."""
        client = _client()
        client.http.get = AsyncMock(return_value={"data": [_ci_row()]})
        gid = await resolve_ci_task_gid(
            client, COMPANY_ID, company_id_field_gid=COMPANY_ID_FIELD_GID
        )
        assert gid == CI_TASK_GID


class TestReadCurrentStage:
    """read_current_stage -- unset, mapped option, unmapped -> UnknownStage."""

    @pytest.mark.asyncio
    async def test_unset_field_returns_none(self) -> None:
        """RED side: reading an unset field as a stage FAILS."""
        client = _client(raw=_ci_raw(None))
        result = await read_current_stage(
            client, CI_TASK_GID, field_gid=FORWARDING_FIELD_GID, option_gids=STAGE_OPTION_GIDS
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_mapped_option_returns_stage(self) -> None:
        """RED side: failing to invert the option-GID map FAILS to read Verified."""
        client = _client(raw=_ci_raw(STAGE_OPTION_GIDS["Verified"]))
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
        client = _client(raw=_ci_raw("9090909090909090"))
        result = await read_current_stage(
            client, CI_TASK_GID, field_gid=FORWARDING_FIELD_GID, option_gids=STAGE_OPTION_GIDS
        )
        assert isinstance(result, UnknownStage)
        assert result.option_gid == "9090909090909090"

    @pytest.mark.asyncio
    async def test_field_absent_from_task_returns_none(self) -> None:
        """A task without the forwarding-stage field at all reads None (unset)."""
        client = _client(raw={"gid": CI_TASK_GID, "custom_fields": []})
        result = await read_current_stage(
            client, CI_TASK_GID, field_gid=FORWARDING_FIELD_GID, option_gids=STAGE_OPTION_GIDS
        )
        assert result is None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
