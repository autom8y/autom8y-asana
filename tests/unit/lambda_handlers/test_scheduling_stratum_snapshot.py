"""Tests for the scheduling-stratum whole-snapshot push handler (I2, DEFAULT-DARK).

Locks the load-bearing safety: the EXPLICIT COMPLETENESS CONTRACT (never push a
partial to the data side's whole-source DELETE), the DEFAULT-DARK gate (skipped +
zero substrate/Asana read when SCHEDULING_STRATUM_PUSH_ENABLED is off), and the
full-office enumeration off the warmed offer frame.
"""

from __future__ import annotations

import datetime as dt
from typing import Any
from unittest.mock import AsyncMock

import polars as pl
import pytest

from autom8_asana.lambda_handlers import scheduling_stratum_snapshot as snap
from autom8_asana.lambda_handlers.scheduling_stratum_snapshot import (
    MIN_POSTURE_SIGNAL_ROWS,
    SnapshotRefusedError,
    assert_complete_office_set,
    assert_posture_signal_floor,
    execute_snapshot_push,
    handler,
    posture_signal_row_count,
    project_offer_frame,
    run_snapshot_push_async,
)
from autom8_asana.normalizer.scheduling_extractor import (
    CUSTOM_CAL_STATUS_FIELD,
    GUID_FIELD,
    REQUIRED_FRAME_COLUMNS,
    ExtractedScheduling,
    FrameSchemaLagError,
)
from autom8_asana.normalizer.scheduling_stratum import CASCADE_PRIORITY
from autom8_asana.services.scheduling_stratum_push import StratumPushResult

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]


def _office(guid: str, *, field: str = "reviewwave_id", value: str = "rw") -> ExtractedScheduling:
    return ExtractedScheduling(
        guid=guid,
        normalized_inputs={**{f: None for f in CASCADE_PRIORITY}, field: value},
    )


def _frame_df(rows: list[dict[str, Any]]) -> pl.DataFrame:
    """Build an offer-frame DataFrame with ALL 1.5.0 posture columns present as keys.

    Any posture column omitted from a row dict defaults to None (a legitimately-null
    projected column -- the office genuinely lacks that field), which is distinct from
    a pre-1.5.0 frame that LACKS the column entirely (the schema-lag case).
    """
    complete: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        base: dict[str, Any] = {
            "gid": row.get("gid", f"o{i}"),
            "last_modified": row.get("last_modified", dt.datetime(2026, 1, 1, tzinfo=dt.UTC)),
        }
        for col in REQUIRED_FRAME_COLUMNS:
            base[col] = row.get(col)
        complete.append(base)
    return pl.DataFrame(complete)


# --- assert_complete_office_set (COMPLETENESS CONTRACT) --------------------------


def test_complete_set_returns_full_gids() -> None:
    assert assert_complete_office_set(["a", "b", "c"], source_complete=True) == ["a", "b", "c"]


def test_complete_set_dedups_preserving_order() -> None:
    assert assert_complete_office_set(["a", "b", "a", "c", "b"], source_complete=True) == [
        "a",
        "b",
        "c",
    ]


def test_refuses_when_source_incomplete() -> None:
    """An unreadable/partial source is REFUSED -- pushing it would mass-wipe."""
    with pytest.raises(SnapshotRefusedError, match="complete snapshot"):
        assert_complete_office_set(["a", "b"], source_complete=False)


def test_refuses_empty_batch() -> None:
    """An empty batch fed to the whole-source DELETE wipes every office -> REFUSE."""
    with pytest.raises(SnapshotRefusedError, match="empty active-office set"):
        assert_complete_office_set([], source_complete=True)
    with pytest.raises(SnapshotRefusedError, match="empty active-office set"):
        assert_complete_office_set(None, source_complete=True)


def test_refuses_all_blank_gids() -> None:
    with pytest.raises(SnapshotRefusedError):
        assert_complete_office_set(["", ""], source_complete=True)


# --- execute_snapshot_push (gate + completeness + push orchestration) ------------


async def _push_ok(offices: list[ExtractedScheduling]) -> StratumPushResult:
    return StratumPushResult(pushed=True, dry_run=False, entry_count=len(offices), payload={})


async def _push_dry(offices: list[ExtractedScheduling]) -> StratumPushResult:
    return StratumPushResult(pushed=False, dry_run=True, entry_count=len(offices), payload={})


async def test_gate_off_skips_without_enumerating() -> None:
    """DEFAULT-DARK: gate off -> skipped, and the enumeration is NEVER invoked."""
    enumerate_called = False

    async def _enumerate() -> tuple[list[ExtractedScheduling], bool]:
        nonlocal enumerate_called
        enumerate_called = True
        return [_office("a")], True

    async def _push(_offices: list[ExtractedScheduling]) -> StratumPushResult:
        raise AssertionError("push must not run when the gate is off")

    result = await execute_snapshot_push(
        gate=lambda: False, enumerate_offices=_enumerate, push=_push
    )
    assert result.status == "skipped"
    assert result.reason == "gate_off"
    assert enumerate_called is False  # no substrate build, no Asana read


async def test_incomplete_source_refuses_without_pushing() -> None:
    push_called = False

    async def _enumerate() -> tuple[list[ExtractedScheduling], bool]:
        return [_office("a"), _office("b")], False  # source_complete=False

    async def _push(_offices: list[ExtractedScheduling]) -> StratumPushResult:
        nonlocal push_called
        push_called = True
        return await _push_ok(_offices)

    result = await execute_snapshot_push(
        gate=lambda: True, enumerate_offices=_enumerate, push=_push
    )
    assert result.status == "refused"
    assert push_called is False  # NEVER push a partial


async def test_schema_lag_refuses_without_pushing() -> None:
    """A SCHEMA-LAG SnapshotRefusedError from enumerate -> refused, push NEVER called.

    Byte-compatible with the incomplete-source refusal: the honest reason flows
    through to the refused outcome and NOTHING is pushed.
    """
    push_called = False

    async def _enumerate() -> tuple[list[ExtractedScheduling], bool]:
        raise SnapshotRefusedError("frame schema pre-1.5.0: projected posture columns absent")

    async def _push(_offices: list[ExtractedScheduling]) -> StratumPushResult:
        nonlocal push_called
        push_called = True
        return await _push_ok(_offices)

    result = await execute_snapshot_push(
        gate=lambda: True, enumerate_offices=_enumerate, push=_push
    )
    assert result.status == "refused"
    assert result.reason is not None and "pre-1.5.0" in result.reason
    assert push_called is False


async def test_complete_source_pushes_full_set() -> None:
    pushed_guids: list[str] = []

    async def _enumerate() -> tuple[list[ExtractedScheduling], bool]:
        return [_office("o1"), _office("o2"), _office("o3")], True

    async def _push(offices: list[ExtractedScheduling]) -> StratumPushResult:
        pushed_guids.extend(o.guid for o in offices)
        return await _push_ok(offices)

    result = await execute_snapshot_push(
        gate=lambda: True, enumerate_offices=_enumerate, push=_push
    )
    assert result.status == "pushed"
    assert result.entry_count == 3
    assert pushed_guids == ["o1", "o2", "o3"]


async def test_dry_run_push_reports_dry_run_status() -> None:
    async def _enumerate() -> tuple[list[ExtractedScheduling], bool]:
        return [_office("o1")], True

    result = await execute_snapshot_push(
        gate=lambda: True, enumerate_offices=_enumerate, push=_push_dry
    )
    assert result.status == "dry_run"


# --- project_offer_frame (PURE frame-first projection) --------------------------


def test_project_hit_path_all_columns_present() -> None:
    """A 1.5.0 frame with all posture columns projects to a correct ExtractedScheduling.

    Absent/unset custom_cal_status -> legacy ACTIVE default -> enrolled=True (never
    fabricated; None is a legitimate null column).
    """
    df = _frame_df([{GUID_FIELD: "gA", "reviewwave_id": "rw"}])  # status None
    extracted, drift = project_offer_frame(df)
    assert len(extracted) == 1
    assert extracted[0].guid == "gA"
    assert extracted[0].enrolled is True  # absent status -> ACTIVE default
    assert extracted[0].normalized_inputs["reviewwave_id"] == "rw"
    assert drift == []


def test_project_deenrolled_office_present_with_enrolled_false() -> None:
    """A de-enrolled (INACTIVE) office is PRESENT with enrolled=False -- never omitted."""
    df = _frame_df([{GUID_FIELD: "gOff", CUSTOM_CAL_STATUS_FIELD: "Inactive", "sked_id": "sk"}])
    extracted, _ = project_offer_frame(df)
    assert len(extracted) == 1
    assert extracted[0].guid == "gOff"
    assert extracted[0].enrolled is False


def test_project_guidless_offer_dropped_fail_safe_by_absence() -> None:
    """UNIVERSE: a guid-less (null/blank company_id) offer DROPS -- fail SAFE by absence."""
    df = _frame_df(
        [
            {"gid": "o-null", GUID_FIELD: None, "reviewwave_id": "rw"},
            {"gid": "o-blank", GUID_FIELD: "  ", "reviewwave_id": "rw"},
            {"gid": "o-ok", GUID_FIELD: "gOk", "reviewwave_id": "rw"},
        ]
    )
    extracted, _ = project_offer_frame(df)
    assert [e.guid for e in extracted] == ["gOk"]  # only the resolvable guid survives


def test_project_multi_offer_dedup_max_modified_at_representative() -> None:
    """Multi-offer-per-guid -> representative by max last_modified (status+destination jointly).

    The NEWER offer (Inactive + sked) wins BOTH the status and the destination; the
    older offer (Active + reviewwave) does not leak into the representative.
    """
    df = _frame_df(
        [
            {
                "gid": "old",
                GUID_FIELD: "gDup",
                CUSTOM_CAL_STATUS_FIELD: "Active",
                "last_modified": dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
                "reviewwave_id": "rw-old",
            },
            {
                "gid": "new",
                GUID_FIELD: "gDup",
                CUSTOM_CAL_STATUS_FIELD: "Inactive",
                "last_modified": dt.datetime(2026, 6, 1, tzinfo=dt.UTC),
                "sked_id": "sk-new",
            },
        ]
    )
    extracted, _ = project_offer_frame(df)
    assert len(extracted) == 1  # one representative per distinct guid
    rep = extracted[0]
    assert rep.guid == "gDup"
    assert rep.enrolled is False  # status from the NEWER offer (Inactive), jointly
    assert rep.normalized_inputs["sked_id"] == "sk-new"  # destination from the newer offer
    assert rep.normalized_inputs["reviewwave_id"] is None  # older offer did NOT leak in


def test_project_status_drift_signalled_when_offers_disagree() -> None:
    """A guid whose offers disagree on custom_cal_status is surfaced as drift."""
    df = _frame_df(
        [
            {"gid": "a", GUID_FIELD: "gDrift", CUSTOM_CAL_STATUS_FIELD: "Active"},
            {"gid": "b", GUID_FIELD: "gDrift", CUSTOM_CAL_STATUS_FIELD: "Inactive"},
            {"gid": "c", GUID_FIELD: "gAgree", CUSTOM_CAL_STATUS_FIELD: "Active"},
            {"gid": "d", GUID_FIELD: "gAgree", CUSTOM_CAL_STATUS_FIELD: "Active"},
        ]
    )
    _, drift = project_offer_frame(df)
    assert drift == ["gDrift"]  # gAgree does NOT drift (both Active)


def test_project_no_drift_when_statuses_agree() -> None:
    """Two-sided: agreeing statuses (incl. one null) produce NO drift signal."""
    df = _frame_df(
        [
            {"gid": "a", GUID_FIELD: "g1", CUSTOM_CAL_STATUS_FIELD: "Active"},
            {"gid": "b", GUID_FIELD: "g1", CUSTOM_CAL_STATUS_FIELD: None},
        ]
    )
    _, drift = project_offer_frame(df)
    assert drift == []


def test_project_empty_universe_yields_empty() -> None:
    """A frame with only guid-less offers projects to an empty set (the gate then REFUSES)."""
    df = _frame_df([{GUID_FIELD: None}, {GUID_FIELD: "   "}])
    extracted, drift = project_offer_frame(df)
    assert extracted == []
    assert drift == []


def test_project_schema_lag_frame_refuses_not_fabricates() -> None:
    """SCHEMA-LAG (two-sided): a pre-1.5.0 frame lacking posture columns REFUSES.

    RED-on-fabricating / GREEN-on-refusing: a variant that ``.get(col, None)`` a
    missing column would FABRICATE enrolled=True (ACTIVE default) from a frame that
    cannot carry the status; the refusing build raises FrameSchemaLagError instead.
    """
    # A pre-1.5.0 frame: gid + last_modified only, NO posture-projection columns.
    stale = pl.DataFrame({"gid": ["o1"], "last_modified": [dt.datetime(2026, 1, 1, tzinfo=dt.UTC)]})

    # Fabricating variant (what NOT to do): silently defaults the absent columns and
    # produces a bogus enrolled=True posture -- the danger the guard exists to stop.
    def _fabricating(row: dict[str, Any]) -> bool:
        from autom8_asana.normalizer.scheduling_extractor import derive_enrolled

        return derive_enrolled(row.get(CUSTOM_CAL_STATUS_FIELD))  # .get -> None -> True

    fabricated = _fabricating(stale.to_dicts()[0])
    assert fabricated is True  # RED: the fabricating variant silently invents ACTIVE

    # The refusing build detects the absent columns and REFUSES honestly.
    with pytest.raises(FrameSchemaLagError, match="pre-1.5.0"):
        project_offer_frame(stale)


# --- VALUE-FLOOR guard (degenerate-source completeness teeth) ---------------------


def test_value_floor_refuses_all_null_posture_universe() -> None:
    """RED (the exact 1.5.0 defect): company_id populated, EVERY posture column null.

    company_id resolves (so assert_complete_office_set would PASS the non-empty SET),
    but 0/N offices carry any scheduling-posture signal -> the value floor REFUSES,
    preventing a degenerate whole-source overwrite of live posture.
    """
    df = _frame_df([{GUID_FIELD: "g1"}, {GUID_FIELD: "g2"}, {GUID_FIELD: "g3"}])
    assert posture_signal_row_count(df) == 0
    with pytest.raises(SnapshotRefusedError, match="degenerate posture source"):
        assert_posture_signal_floor(df)


def test_value_floor_passes_when_status_signal_present() -> None:
    """GREEN: a single non-null custom_cal_status clears the floor (mixed frame passes)."""
    df = _frame_df([{GUID_FIELD: "g1", CUSTOM_CAL_STATUS_FIELD: "Enabled"}, {GUID_FIELD: "g2"}])
    assert posture_signal_row_count(df) >= MIN_POSTURE_SIGNAL_ROWS
    assert_posture_signal_floor(df)  # does not raise


def test_value_floor_passes_on_provider_only_signal() -> None:
    """GREEN (all-GHL fleet): status null everywhere but a provider is set -> passes.

    Distinguishes a degenerate source (NO signal anywhere) from a legitimate fleet whose
    enrollment status happens to be null while a provider carries the destination.
    """
    df = _frame_df(
        [{GUID_FIELD: "g1", CASCADE_PRIORITY[2]: "https://calendly/x"}, {GUID_FIELD: "g2"}]
    )
    assert posture_signal_row_count(df) == 1
    assert_posture_signal_floor(df)  # does not raise


def test_value_floor_not_triggered_on_empty_universe() -> None:
    """A guid-less (empty) universe is the complete-set gate's remit, not the value floor."""
    df = _frame_df([{GUID_FIELD: None}, {GUID_FIELD: "   "}])
    assert posture_signal_row_count(df) == 0
    assert_posture_signal_floor(df)  # does not raise (empty universe not floored)


async def test_enumerate_degenerate_frame_raises_refused() -> None:
    """END-TO-END: a degenerate (all-null posture) frame drives the ``refused`` outcome.

    The value floor propagates SnapshotRefusedError through the enumerate closure so
    execute_snapshot_push converts it to a ``refused`` run (pushes NOTHING).
    """
    df = _frame_df([{GUID_FIELD: "g1"}, {GUID_FIELD: "g2"}])
    cache = _FakeCache(_FakeEntry(df))

    async def _push(_offices: list[ExtractedScheduling]) -> StratumPushResult:
        raise AssertionError("degenerate frame must REFUSE before any push")

    result = await execute_snapshot_push(
        gate=lambda: True,
        enumerate_offices=lambda: snap._enumerate_offices_from_frame(cache, "proj"),
        push=_push,
    )
    assert result.status == "refused"
    assert result.entry_count == 0


# --- _enumerate_offices_from_frame (full offer-frame source, frame-first) --------


class _FakeEntry:
    def __init__(self, dataframe: Any) -> None:
        self.dataframe = dataframe


class _FakeCache:
    def __init__(self, entry: Any) -> None:
        self._entry = entry
        self.requested: tuple[str, str] | None = None

    async def get_async(self, project_gid: str, entity_type: str) -> Any:
        self.requested = (project_gid, entity_type)
        return self._entry


async def test_enumerate_projects_offices_from_frame() -> None:
    df = _frame_df(
        [
            {GUID_FIELD: "g1", "reviewwave_id": "rw"},
            {GUID_FIELD: "g2", "sked_id": "sk"},
        ]
    )
    cache = _FakeCache(_FakeEntry(df))
    extracted, complete = await snap._enumerate_offices_from_frame(cache, "PROJ")
    assert complete is True
    assert {e.guid for e in extracted} == {"g1", "g2"}
    assert cache.requested == ("PROJ", "offer")  # reads the OFFER frame (full source)


async def test_enumerate_absent_frame_is_incomplete() -> None:
    """No warmed offer frame -> source_complete=False -> the gate will REFUSE."""
    extracted, complete = await snap._enumerate_offices_from_frame(_FakeCache(None), "PROJ")
    assert extracted == []
    assert complete is False


async def test_enumerate_frame_without_gid_column_is_incomplete() -> None:
    df = pl.DataFrame({"name": ["a"]})
    extracted, complete = await snap._enumerate_offices_from_frame(
        _FakeCache(_FakeEntry(df)), "PROJ"
    )
    assert extracted == []
    assert complete is False


async def test_enumerate_schema_lag_frame_raises_refused() -> None:
    """A pre-1.5.0 frame (gid present, posture columns absent) -> SnapshotRefusedError.

    The enumerate translates the frame-level FrameSchemaLagError into the honest
    refused reason so execute_snapshot_push records it (never a 500).
    """
    stale = pl.DataFrame({"gid": ["o1"], "last_modified": [dt.datetime(2026, 1, 1, tzinfo=dt.UTC)]})
    with pytest.raises(SnapshotRefusedError, match="pre-1.5.0"):
        await snap._enumerate_offices_from_frame(_FakeCache(_FakeEntry(stale)), "PROJ")


# --- handler (end-to-end DARK) --------------------------------------------------


def test_handler_dark_returns_skipped_200(monkeypatch: pytest.MonkeyPatch) -> None:
    """With the gate unset the handler short-circuits to skipped (200), no substrate."""
    monkeypatch.delenv("SCHEDULING_STRATUM_PUSH_ENABLED", raising=False)
    response = handler({}, context=None)
    assert response["statusCode"] == 200
    assert response["body"]["status"] == "skipped"
    assert response["body"]["reason"] == "gate_off"


async def test_run_snapshot_push_async_dark_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCHEDULING_STRATUM_PUSH_ENABLED", raising=False)
    result = await run_snapshot_push_async(context=None)
    assert result.status == "skipped"


# --- SA-token mint + authed push wiring (retire the AUTOM8Y_DATA_API_KEY fossil) ---
#
# The live push MUST carry a freshly-minted S2S JWT (ServiceTokenAuthProvider),
# mirroring workflow_handler, NOT the legacy AUTOM8Y_DATA_API_KEY fossil -- an
# 11-char single-segment stub the data side rejects with 401 AUTH-TEB-003
# ("Token is malformed: Not enough segments").


class _FakeProvider:
    """Stand-in for ServiceTokenAuthProvider: get_secret -> JWT, close() tracked."""

    instances: list[_FakeProvider] = []

    def __init__(self, token: str = "hdr.pyld.sig") -> None:
        self._token = token
        self.closed = False
        self.secret_keys: list[str] = []
        _FakeProvider.instances.append(self)

    def get_secret(self, key: str) -> str:
        self.secret_keys.append(key)
        return self._token

    def close(self) -> None:
        self.closed = True


def _spy_live_push() -> AsyncMock:
    return AsyncMock(
        return_value=StratumPushResult(pushed=True, dry_run=False, entry_count=1, payload={})
    )


def test_mint_token_returns_none_when_creds_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """No SERVICE_CLIENT_ID/SECRET -> ServiceTokenAuthProvider ValueError -> honest None.

    The honest-skip signal is None (the caller then skips the POST), NEVER a fallback to
    the legacy fossil. No network is touched: the provider raises at construction on
    absent creds (resolve_secret_from_env ValueError), which the broad catch narrows to
    None.
    """
    for var in (
        "SERVICE_CLIENT_ID",
        "SERVICE_CLIENT_ID_ARN",
        "SERVICE_CLIENT_SECRET",
        "SERVICE_CLIENT_SECRET_ARN",
    ):
        monkeypatch.delenv(var, raising=False)
    assert snap._mint_stratum_push_token() is None


def test_mint_token_returns_jwt_and_closes_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """A successful exchange returns the JWT string and releases the provider (close)."""
    _FakeProvider.instances.clear()
    monkeypatch.setattr("autom8_asana.auth.service_token.ServiceTokenAuthProvider", _FakeProvider)
    token = snap._mint_stratum_push_token()
    assert token == "hdr.pyld.sig"
    assert len(_FakeProvider.instances) == 1
    assert _FakeProvider.instances[0].closed is True  # provider resources released


def test_mint_token_none_when_provider_yields_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty token from the exchange normalizes to None (honest skip, not "")."""
    _FakeProvider.instances.clear()
    monkeypatch.setattr(
        "autom8_asana.auth.service_token.ServiceTokenAuthProvider",
        lambda: _FakeProvider(token=""),
    )
    assert snap._mint_stratum_push_token() is None
    assert _FakeProvider.instances[0].closed is True  # closed even on the empty-token path


async def test_live_push_injects_minted_sa_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """LIVE path (gate on, dry_run None): mint the JWT and inject it as ``auth_token``."""
    monkeypatch.setenv("SCHEDULING_STRATUM_PUSH_ENABLED", "true")
    monkeypatch.setattr(snap, "_mint_stratum_push_token", lambda: "hdr.pyld.sig")
    spy = _spy_live_push()
    monkeypatch.setattr(snap, "resolve_and_push_snapshot", spy)

    result = await snap._resolve_and_push_snapshot_authed([_office("g1")], dry_run=None)

    spy.assert_awaited_once()
    assert spy.await_args.kwargs["auth_token"] == "hdr.pyld.sig"  # minted JWT injected
    assert result is not None and result.pushed is True


async def test_mint_failure_honest_skip_no_post(monkeypatch: pytest.MonkeyPatch) -> None:
    """LIVE path, mint returns None: NO POST, pushed=False (never the fossil, never a crash)."""
    monkeypatch.setenv("SCHEDULING_STRATUM_PUSH_ENABLED", "true")
    monkeypatch.setattr(snap, "_mint_stratum_push_token", lambda: None)
    spy = _spy_live_push()
    monkeypatch.setattr(snap, "resolve_and_push_snapshot", spy)

    result = await snap._resolve_and_push_snapshot_authed([_office("g1")], dry_run=None)

    assert result is None  # honest skip -> execute_snapshot_push reports pushed=False
    spy.assert_not_awaited()  # NEVER push with a garbage/fossil token


async def test_dry_run_never_mints(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit dry_run wins even with the gate ON: no mint, pass-through auth_token=None."""
    monkeypatch.setenv("SCHEDULING_STRATUM_PUSH_ENABLED", "true")

    def _no_mint() -> str:
        raise AssertionError("dry-run must never mint a token")

    monkeypatch.setattr(snap, "_mint_stratum_push_token", _no_mint)
    spy = AsyncMock(
        return_value=StratumPushResult(pushed=False, dry_run=True, entry_count=1, payload={})
    )
    monkeypatch.setattr(snap, "resolve_and_push_snapshot", spy)

    result = await snap._resolve_and_push_snapshot_authed([_office("g1")], dry_run=True)

    spy.assert_awaited_once()
    assert spy.await_args.kwargs.get("auth_token") is None  # no token minted on the dry path
    assert result is not None and result.dry_run is True


async def test_gate_off_never_mints_returns_skipped_gate_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gate off: {skipped, gate_off} receipt with ZERO mint attempt (byte-identical DARK)."""
    monkeypatch.delenv("SCHEDULING_STRATUM_PUSH_ENABLED", raising=False)

    def _no_mint() -> str:
        raise AssertionError("gate-off must never mint a token")

    monkeypatch.setattr(snap, "_mint_stratum_push_token", _no_mint)
    result = await run_snapshot_push_async(context=None)
    assert result.status == "skipped"
    assert result.reason == "gate_off"
    assert result.entry_count == 0
