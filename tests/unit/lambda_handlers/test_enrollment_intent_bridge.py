"""Two-sided teeth for the WS-A enrollment intent -> gate bridge (PR-3).

The design contract (TDD-ws-a-intent-gate-bridge-2026-08-05 §3.4/§3.6/§5/§8.1):

  * DEFAULT-DARK -- no S3 read, no token exchange, no HTTP until armed.
  * FIVE refusals, each refusing the WHOLE cycle with ZERO writes: schema-lag,
    freshness (all three frames), universe floor, delta ceiling, and the R-1
    silent-no-op canary.
  * DELTA-ONLY + idempotent: cycle 2 over unchanged intent writes NOTHING.
  * Prereq refusal is LOUD, queued, and never retried as a flip.

Every refusal leg is proven TWO-SIDED: RED on its own broken input AND GREEN on
the healthy fixture. A refusal suite that only proves the RED cannot distinguish a
guard that bites from a guard that bites everything -- and a bridge that refuses
every cycle is just a dark bridge with extra steps.

★ The write-count assertion is the load-bearing one throughout: a refusal that
still wrote something is not a refusal.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import polars as pl
import pytest

from autom8_asana.enrollment.scheduling_client import Outcome, SchedulingConfigClient
from autom8_asana.lambda_handlers import enrollment_intent_bridge as bridge
from autom8_asana.lambda_handlers.enrollment_intent_bridge import (
    ALARM_BOUND_METRICS,
    FRAME_SPECS,
    METRIC_EVALUATION_REFUSED,
    METRIC_LAST_RUN_EPOCH,
    METRIC_NAMESPACE,
    LoadedFrames,
    run_enrollment_bridge,
)

NOW = 1_800_000_000.0
FRESH = NOW - 60.0
CEILING = 43200.0
FLOOR = 3
MAX_DELTA = 10

PHONE_A = "+15550001111"  # explicit Enabled, gate currently OFF -> a real delta
PHONE_B = "+15550002222"  # UNSET -> coerced Enabled, gate already ON -> noop
PHONE_C = "+15550003333"  # explicit Inactive, gate currently ON -> a real delta
PHONE_SALES = "+15550004444"  # Sales Process -- must never appear at all

_T0 = dt.datetime(2026, 8, 1, 12, 0, 0)

_UH_SCHEMA = {
    "gid": pl.Utf8,
    "parent_gid": pl.Utf8,
    "custom_cal_status": pl.Utf8,
    "last_modified": pl.Datetime,
}
_BIZ_SCHEMA = {"gid": pl.Utf8, "office_phone": pl.Utf8, "company_id": pl.Utf8}
_OFFER_SCHEMA = {"office_phone": pl.Utf8, "section": pl.Utf8, "is_completed": pl.Boolean}


def _frames(ages: tuple[tuple[str, float | None], ...] | None = None) -> LoadedFrames:
    """The healthy three-frame fixture -- the GREEN side of every leg."""
    uh = pl.DataFrame(
        [
            {
                "gid": "uh1",
                "parent_gid": "b1",
                "custom_cal_status": "Enabled",
                "last_modified": _T0,
            },
            {"gid": "uh2", "parent_gid": "b2", "custom_cal_status": None, "last_modified": _T0},
            {
                "gid": "uh3",
                "parent_gid": "b3",
                "custom_cal_status": "Inactive",
                "last_modified": _T0,
            },
            {
                "gid": "uh4",
                "parent_gid": "b4",
                "custom_cal_status": "Enabled",
                "last_modified": _T0,
            },
        ],
        schema=_UH_SCHEMA,
    )
    biz = pl.DataFrame(
        [
            {"gid": "b1", "office_phone": PHONE_A, "company_id": "guid-1"},
            # guid NULL, phone present -- must still be reachable (R-12).
            {"gid": "b2", "office_phone": PHONE_B, "company_id": None},
            {"gid": "b3", "office_phone": PHONE_C, "company_id": "guid-3"},
            {"gid": "b4", "office_phone": PHONE_SALES, "company_id": "guid-4"},
        ],
        schema=_BIZ_SCHEMA,
    )
    offer = pl.DataFrame(
        [
            {"office_phone": PHONE_A, "section": "ACTIVE", "is_completed": False},
            {"office_phone": PHONE_B, "section": "Activating", "is_completed": False},
            {"office_phone": PHONE_C, "section": "ACTIVE", "is_completed": False},
            {"office_phone": PHONE_SALES, "section": "Sales Process", "is_completed": False},
        ],
        schema=_OFFER_SCHEMA,
    )
    return LoadedFrames(
        unit_holder=uh,
        business=biz,
        offer=offer,
        ages=ages or (("unit_holder", FRESH), ("business", FRESH), ("offer", FRESH)),
    )


class _FakeApi:
    """A fake governed write path that RECORDS every crossing.

    ``patch_calls`` is the assertion surface for "a refusal wrote NOTHING".
    """

    def __init__(self, state: dict[str, bool]) -> None:
        self.state = dict(state)
        self.get_calls: list[str] = []
        self.patch_calls: list[tuple[str, dict[str, Any]]] = []
        self.prereq_refuse: set[str] = set()
        self.unknown: set[str] = set()

    class _R:
        def __init__(self, status_code: int, body: Any) -> None:
            self.status_code = status_code
            self._body = body

        def json(self) -> Any:
            return self._body

    def _phone(self, url: str) -> str:
        """Percent-DECODE the segment, as a real ASGI server does (D-1).

        The client emits the phone as ONE percent-encoded path segment; a fake that
        skipped decoding would fail every healthy-path assertion for the wrong
        reason and could mask a real encoding regression.
        """
        from urllib.parse import unquote

        return unquote(url.removeprefix("/api/v1/businesses/").removesuffix("/config"))

    def get(self, url: str, *, headers: Any = None) -> Any:
        phone = self._phone(url)
        self.get_calls.append(phone)
        if phone in self.unknown or phone not in self.state:
            return self._R(404, {"error": {"code": "BUSINESS_NOT_FOUND"}})
        return self._R(200, {"data": {"scheduling_enabled": self.state[phone], "offer_id": 1}})

    def patch(self, url: str, *, json: Any = None, headers: Any = None) -> Any:
        phone = self._phone(url)
        payload = json or {}
        self.patch_calls.append((phone, payload))
        desired = bool(payload.get("scheduling_enabled"))
        if desired and phone in self.prereq_refuse and not self.state.get(phone, False):
            return self._R(
                400,
                {
                    "error": {
                        "code": "SCHEDULING_ENABLE_REFUSED",
                        "details": {"reasons": ["timezone_not_configured"]},
                    }
                },
            )
        self.state[phone] = desired
        return self._R(200, {"data": {"updated": True}})


def _run(
    api: _FakeApi,
    *,
    frames: LoadedFrames | None = None,
    gate: bool = True,
    floor: int = FLOOR,
    max_delta: int = MAX_DELTA,
    dry_run: bool = False,
    load_frames: Any = None,
) -> Any:
    return run_enrollment_bridge(
        gate=lambda: gate,
        load_frames=load_frames or (lambda: frames or _frames()),
        client_factory=lambda: SchedulingConfigClient(api, lambda: "jwt"),
        min_inscope_phones=floor,
        max_delta_per_cycle=max_delta,
        staleness_ceiling_seconds=CEILING,
        dry_run=dry_run,
        now_epoch=NOW,
        cycle_id="cycle-under-test",
    )


@pytest.fixture(autouse=True)
def _capture_metrics(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, float]]:
    """Capture emissions so metric assertions do not require live CloudWatch."""
    emitted: list[tuple[str, float]] = []

    def _fake_emit(metric: str, value: float, **_: Any) -> None:
        emitted.append((metric, value))

    monkeypatch.setattr(bridge, "emit_metric", _fake_emit)
    return emitted


# ===========================================================================
# DEFAULT-DARK
# ===========================================================================


class TestDefaultDark:
    def test_gate_off_short_circuits_before_any_io(self) -> None:
        """Dark means dark: no frame read, no token exchange, no HTTP."""
        api = _FakeApi({PHONE_A: False})
        loaded: list[int] = []

        result = _run(api, gate=False, load_frames=lambda: (loaded.append(1), _frames())[1])

        assert result.status == "skipped"
        assert result.reason == "gate_off"
        assert loaded == [], "a DARK cycle must not read the frames"
        assert api.get_calls == []
        assert api.patch_calls == []

    def test_client_is_never_constructed_while_dark(self) -> None:
        """★ The factory must not fire while dark.

        Building the client constructs SERVICE CREDENTIALS, which do not exist
        until the SA is provisioned. A dark bridge that 500s every six hours on
        credentials it is not yet supposed to have is a self-inflicted alarm.
        """
        built: list[int] = []

        def _factory() -> SchedulingConfigClient:
            built.append(1)
            raise AssertionError("client_factory called while the gate is OFF")

        result = run_enrollment_bridge(
            gate=lambda: False,
            load_frames=_frames,
            client_factory=_factory,
            min_inscope_phones=FLOOR,
            max_delta_per_cycle=MAX_DELTA,
            staleness_ceiling_seconds=CEILING,
            now_epoch=NOW,
        )
        assert result.status == "skipped"
        assert built == []

    def test_heartbeat_is_emitted_even_while_dark(
        self, _capture_metrics: list[tuple[str, float]]
    ) -> None:
        """An honest 'alive but intentionally dark' signal -- the dead-man's target."""
        _run(_FakeApi({}), gate=False)
        assert (METRIC_LAST_RUN_EPOCH, NOW) in _capture_metrics


# ===========================================================================
# ★ THE FIVE REFUSALS -- each RED on its break, GREEN on health, ZERO writes
# ===========================================================================


class TestRefusalsWriteNothing:
    def test_GREEN_healthy_cycle_applies_exactly_the_delta(self) -> None:
        """The GREEN side of every refusal leg below."""
        api = _FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True})

        result = _run(api)

        assert result.status == "evaluated"
        assert result.in_scope == 3
        # A: OFF -> ON (explicit Enabled). C: ON -> OFF (explicit Inactive).
        # B: already ON and coerces to Enabled -> noop, no call.
        assert result.delta == 2
        assert result.applied == 2
        assert sorted(p for p, _ in api.patch_calls) == sorted([PHONE_A, PHONE_C])
        assert api.state == {PHONE_A: True, PHONE_B: True, PHONE_C: False}
        assert PHONE_SALES not in api.get_calls, "the R3 wall held end-to-end"

    def test_RED_schema_lag_refuses_and_writes_nothing(self) -> None:
        """★ The leg that fires TODAY -- unit_holder posture columns do not exist
        until WS-B PR-1 deploys AND one warmer cycle completes."""
        api = _FakeApi({PHONE_A: False})
        frames = _frames()
        lagged = LoadedFrames(
            unit_holder=frames.unit_holder.drop("custom_cal_status"),
            business=frames.business,
            offer=frames.offer,
            ages=frames.ages,
        )

        result = _run(api, frames=lagged)

        assert result.status == "refused"
        assert "custom_cal_status" in (result.reason or "")
        assert api.patch_calls == []

    @pytest.mark.parametrize("stale", ["unit_holder", "business", "offer"])
    def test_RED_any_stale_frame_refuses_and_writes_nothing(self, stale: str) -> None:
        """Bound to the office SPINE: a fresh offer frame does not vouch for intent."""
        api = _FakeApi({PHONE_A: False})
        ages = tuple(
            (name, NOW - 999_999.0 if name == stale else FRESH)
            for name in ("unit_holder", "business", "offer")
        )

        result = _run(api, frames=_frames(ages))

        assert result.status == "refused"
        # ★ D-3: the refusal names the ACTUAL stale frame, not a hardcoded one.
        assert f"{stale} (stale" in (result.reason or "")
        assert api.patch_calls == []

    @pytest.mark.parametrize("unprovable", ["unit_holder", "business", "offer"])
    def test_RED_unprovable_frame_age_refuses(self, unprovable: str) -> None:
        api = _FakeApi({PHONE_A: False})
        ages = tuple(
            (name, None if name == unprovable else FRESH)
            for name in ("unit_holder", "business", "offer")
        )
        result = _run(api, frames=_frames(ages))
        assert result.status == "refused"
        assert "unprovable" in (result.reason or "")
        assert api.patch_calls == []

    def test_RED_collapsed_universe_refuses_and_writes_nothing(self) -> None:
        """A fossil/collapsed frame is the mass-enrollment vector -- refuse whole."""
        api = _FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True})

        result = _run(api, floor=500)

        assert result.status == "refused"
        assert "collapsed" in (result.reason or "")
        assert api.patch_calls == []

    def test_RED_unset_floor_refuses_rather_than_running_unbounded(self) -> None:
        """★ Refuse-on-absent-fuel: a guessed floor is no floor."""
        api = _FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True})
        result = _run(api, floor=0)
        assert result.status == "refused"
        assert "unset or non-positive" in (result.reason or "")
        assert api.patch_calls == []

    @pytest.mark.parametrize("ceiling", [0, -1])
    def test_RED_unset_staleness_ceiling_refuses(self, ceiling: int) -> None:
        """★ D-5: a misconfigured staleness ceiling fails OPEN.

        This knob was previously read with a silent default, so garbage ("12h", a
        stray quote, "") resolved to 43200 without a word. A non-positive ceiling
        would make every frame -- including a fossil one -- read as fresh, which
        evaporates the guard exactly when it matters. Refuse instead.
        """
        api = _FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True})
        result = run_enrollment_bridge(
            gate=lambda: True,
            load_frames=_frames,
            client_factory=lambda: SchedulingConfigClient(api, lambda: "jwt"),
            min_inscope_phones=FLOOR,
            max_delta_per_cycle=MAX_DELTA,
            staleness_ceiling_seconds=ceiling,
            now_epoch=NOW,
        )
        assert result.status == "refused"
        assert "staleness ceiling" in (result.reason or "")
        assert api.patch_calls == []

    def test_GREEN_a_real_staleness_ceiling_admits_fresh_frames(self) -> None:
        """Two-sided: the guard bites only on the misconfiguration."""
        api = _FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True})
        assert _run(api).status == "evaluated"

    def test_RED_delta_ceiling_refuses_the_WHOLE_cycle_never_partially(self) -> None:
        """★ The sharpest leg: 2 offices would move, the ceiling admits 1, and
        ZERO are written. A partially-applied mass change writes real gate state
        from unreal intent and leaves no single point to reverse."""
        api = _FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True})

        result = _run(api, max_delta=1)

        assert result.status == "refused"
        assert "delta ceiling tripped" in (result.reason or "")
        assert api.patch_calls == [], "a ceiling breach must write NOTHING, not 'some'"
        assert api.state == {PHONE_A: False, PHONE_B: True, PHONE_C: True}

    def test_GREEN_delta_exactly_at_the_ceiling_applies(self) -> None:
        """Two-sided: the ceiling bites at ceiling+1, not at the ceiling."""
        api = _FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True})
        result = _run(api, max_delta=2)
        assert result.status == "evaluated"
        assert result.applied == 2

    def test_RED_silent_no_op_canary_refuses(self) -> None:
        """★ R-1: a phone-format divergence would 404 every office while the bridge
        reported a clean, healthy, entirely useless cycle. Zero resolved against a
        non-empty universe is a REFUSE."""
        api = _FakeApi({})  # every GET 404s -- nothing resolves
        result = _run(api)
        assert result.status == "refused"
        assert "resolved 0 of 3" in (result.reason or "")
        assert api.patch_calls == []

    def test_GREEN_partial_resolution_is_not_a_refusal(self) -> None:
        """Two-sided: SOME unresolved offices are a queue, not a cycle failure."""
        api = _FakeApi({PHONE_A: False})  # B and C 404
        result = _run(api, floor=1)
        assert result.status == "evaluated"
        assert result.applied == 1
        assert result.outcomes.get(Outcome.UNRESOLVED.value) == 2

    def test_refusal_emits_the_refused_metric_and_no_verdict(
        self, _capture_metrics: list[tuple[str, float]]
    ) -> None:
        """Never a fabricated 0: a refused cycle emits no InScopeOffices at all."""
        api = _FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True})
        _run(api, floor=500)

        assert (METRIC_EVALUATION_REFUSED, 1) in _capture_metrics
        assert not [m for m, _ in _capture_metrics if m == bridge.METRIC_IN_SCOPE_OFFICES], (
            "a refused cycle must not publish a verdict metric -- a fabricated 0 "
            "reads 'nothing to do, all clear' while the instrument is blind"
        )

    def test_delta_ceiling_emits_its_own_distinct_signal(
        self, _capture_metrics: list[tuple[str, float]]
    ) -> None:
        api = _FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True})
        _run(api, max_delta=1)
        assert (bridge.METRIC_DELTA_CEILING_TRIPPED, 1) in _capture_metrics


# ===========================================================================
# ★ IDEMPOTENCE -- cycle 2 writes ZERO
# ===========================================================================


class TestIdempotence:
    def test_second_cycle_over_unchanged_intent_writes_nothing(self) -> None:
        """★ P5. A second wave of writes would falsify the delta-only design, and
        would mean a `scheduling_config_updated` receipt no longer implies a real
        state change -- which is what makes the PT-03 receipt leg meaningful."""
        api = _FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True})

        first = _run(api)
        assert first.applied == 2
        writes_after_first = len(api.patch_calls)

        second = _run(api)

        assert second.status == "evaluated"
        assert second.delta == 0
        assert second.applied == 0
        assert len(api.patch_calls) == writes_after_first, (
            "cycle 2 issued a PATCH -- the sync is not delta-only"
        )
        assert second.outcomes.get(Outcome.NOOP.value) == 3

    def test_noop_offices_are_never_called_at_all(self) -> None:
        """The client-side delta guard: an already-correct office costs one GET."""
        api = _FakeApi({PHONE_A: True, PHONE_B: True, PHONE_C: False})
        result = _run(api)
        assert result.delta == 0
        assert api.patch_calls == []
        assert sorted(api.get_calls) == sorted([PHONE_A, PHONE_B, PHONE_C])


# ===========================================================================
# DRY-RUN (the pre-arm observation path)
# ===========================================================================


class TestDryRun:
    def test_dry_run_computes_the_delta_and_writes_nothing(self) -> None:
        api = _FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True})

        result = _run(api, dry_run=True)

        assert result.status == "evaluated"
        assert result.delta == 2
        assert result.applied == 0
        assert api.patch_calls == []

    def test_dry_run_delta_is_not_reported_as_noop(self) -> None:
        """★ A dry-run cycle must not read as 'already converged' -- these offices
        WOULD have moved."""
        api = _FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True})
        result = _run(api, dry_run=True)
        assert result.outcomes.get(Outcome.DRY_RUN_SUPPRESSED.value) == 2
        assert result.outcomes.get(Outcome.NOOP.value) == 1

    def test_a_dry_run_that_refuses_still_refuses(self) -> None:
        """The pre-arm check: a dry run that refuses is the correct outcome and
        blocks the arm."""
        api = _FakeApi({PHONE_A: False})
        result = _run(api, dry_run=True, floor=500)
        assert result.status == "refused"


# ===========================================================================
# Fail-closed EXECUTION (§5) -- refuse loud, queue, never force-flip
# ===========================================================================


class TestPrereqRefusalIsQueuedNotForced:
    def test_prereq_refused_office_is_never_retried_as_a_flip(self) -> None:
        api = _FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True})
        api.prereq_refuse.add(PHONE_A)

        result = _run(api)

        assert result.outcomes.get(Outcome.PREREQ_REFUSED.value) == 1
        assert [p for p, _ in api.patch_calls].count(PHONE_A) == 1, (
            "exactly ONE attempt -- a refused enable must never be retried as a flip"
        )
        assert api.state[PHONE_A] is False, "never force-flipped"

    def test_a_prereq_refusal_does_not_fail_the_cycle(self) -> None:
        """Terminal for the office, not for the run: the other office still moves."""
        api = _FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True})
        api.prereq_refuse.add(PHONE_A)

        result = _run(api)

        assert result.status == "evaluated"
        assert result.applied == 1
        assert api.state[PHONE_C] is False


# ===========================================================================
# Emit -> alarm contract + frame identity
# ===========================================================================


class TestEmitAlarmContract:
    def test_namespace_is_disjoint_from_the_ws_e_tripwire(self) -> None:
        """WS-A and WS-E are different instruments answering different questions;
        sharing a namespace would let one's alarms watch the other's silence."""
        from autom8_asana.lambda_handlers.traffic_offer_divergence_tripwire import (
            METRIC_NAMESPACE as WS_E_NAMESPACE,
        )

        assert METRIC_NAMESPACE == "Autom8y/AsanaEnrollmentBridge"
        assert METRIC_NAMESPACE != WS_E_NAMESPACE

    def test_alarm_bound_metrics_are_pinned(self) -> None:
        """A rename must trip CI, not production. The terraform half watches these
        EXACT names; a divergence is a green-on-both-halves, dead-as-a-pair alarm."""
        assert (
            frozenset(
                {
                    "LastRunEpoch",
                    "EvaluationRefused",
                    "DeltaCeilingTripped",
                    "InScopeOffices",
                    "ConfigWritesApplied",
                    "UnresolvedOfficeCount",
                    "WriteDeniedCount",
                    "BridgeErrorCount",
                }
            )
            == ALARM_BOUND_METRICS
        )

    def test_three_frames_are_read_in_a_declared_order(self) -> None:
        labels = [label for label, _ in FRAME_SPECS]
        assert labels == ["unit_holder", "business", "offer"]
        for _, key in FRAME_SPECS:
            assert key.endswith("/dataframe.parquet")

    def test_evaluated_cycle_publishes_a_real_refused_zero(
        self, _capture_metrics: list[tuple[str, float]]
    ) -> None:
        """So the refuse alarm sits in OK, not INSUFFICIENT_DATA."""
        _run(_FakeApi({PHONE_A: False, PHONE_B: True, PHONE_C: True}))
        assert (METRIC_EVALUATION_REFUSED, 0) in _capture_metrics
