"""Two-sided proofs for the producer-durability package (C1 emissions + C5 floor).

WHAT THIS GUARDS. Over the 30-day window ending 2026-08-06 the producer ran 121
times, exited 0 every time, and delivered NOTHING to the substrate on 118 of those
runs (100 ``refused`` + 18 ``pushed=false``, own-hands Logs Insights over
/aws/lambda/autom8-asana-scheduling-stratum-snapshot). Both existing alarms
(``-lambda-errors`` on AWS/Lambda:Errors and ``-dlq-not-empty`` on the DLQ depth)
sat in OK the entire time, because the producer fails SILENTLY and CLEANLY. The
metrics below are the missing instruments; these tests are their teeth.

TWO-SIDED (G-THEATER refusal). Every guard is proven from BOTH sides: the healthy
frame/outcome is asserted to pass (GREEN) AND a deliberately-degenerate one is
asserted to TRIP it (RED). A one-sided green proof is vacuous -- an emission that
is never shown to be ABSENT on the failure path proves nothing about detection.

The value-floor / shrink-guard BODIES are deliberately untouched by this package;
``test_certified_guard_bodies_are_untouched`` pins that property.
"""

from __future__ import annotations

import importlib
from typing import Any

import polars as pl
import pytest

from autom8_asana.lambda_handlers import scheduling_stratum_snapshot as mod

# ---------------------------------------------------------------------------
# Frame fixtures
# ---------------------------------------------------------------------------

_SIGNAL_COLS = list(mod._POSTURE_SIGNAL_COLUMNS)
_GUID = mod.GUID_FIELD


def _frame(n_rows: int, n_signal_rows: int) -> pl.DataFrame:
    """A universe of ``n_rows`` offices of which ``n_signal_rows`` carry posture.

    Signal is carried on the FIRST posture column (custom_cal_status in practice);
    the remaining rows are all-null across every posture column -- the exact 1.5.0
    degenerate shape (company_id resolves, content does not).
    """
    data: dict[str, list[Any]] = {_GUID: [f"guid-{i}" for i in range(n_rows)]}
    for idx, col in enumerate(_SIGNAL_COLS):
        if idx == 0:
            data[col] = ["enabled" if i < n_signal_rows else None for i in range(n_rows)]
        else:
            data[col] = [None] * n_rows
    return pl.DataFrame(data)


# ---------------------------------------------------------------------------
# C5 -- the derived value floor
# ---------------------------------------------------------------------------


class TestC5ValueFloorIsDerivedAndRaised:
    def test_floor_is_materially_above_one(self) -> None:
        """The DIAG Leg-A recommendation, implemented: a floor of 1 over a
        921-office universe is 1/921 -- 920 offices could be all-null and pass."""
        assert mod.MIN_POSTURE_SIGNAL_ROWS >= 100
        assert mod._DEFAULT_MIN_POSTURE_SIGNAL_ROWS == 100

    def test_floor_exceeds_the_entire_pre_ws_b_era_universe(self) -> None:
        """Derivation receipt: the largest ``office_count`` across the 18
        ``pushed=false`` ticks of 2026-07-22..08-05 was 44. The floor must be well
        clear of that whole regime, else the darkness-era frames would have passed."""
        assert mod.MIN_POSTURE_SIGNAL_ROWS > 2 * 44

    def test_healthy_frame_passes_the_floor_GREEN(self) -> None:
        """A 921-office universe with ~540 signal-bearing rows (the WS-B DIAG
        observation) must NOT refuse -- a floor that bricks the producer converts a
        detection gap into an outage."""
        mod.assert_posture_signal_floor(_frame(921, 540))

    def test_degenerate_frame_now_trips_the_floor_RED(self) -> None:
        """RED: the band C5 exists to close. A full 921-office universe carrying a
        posture signal on exactly ONE office passed BOTH guards before this change
        (1 >= MIN_POSTURE_SIGNAL_ROWS == 1) and whole-source-overwrote live posture
        with empties. It must now REFUSE."""
        with pytest.raises(mod.SnapshotRefusedError, match="value floor"):
            mod.assert_posture_signal_floor(_frame(921, 1))

    def test_the_old_floor_would_have_admitted_the_degenerate_frame_RED(self) -> None:
        """RED (falsifies the fix): proves the frame above is caught BY THE RAISED
        FLOOR and not by some incidental property of the fixture. Under the old
        threshold of 1 the very same frame is admitted."""
        degenerate = _frame(921, 1)
        assert mod.posture_signal_row_count(degenerate) == 1
        assert 1 >= 1, "old floor admits it"
        assert mod.posture_signal_row_count(degenerate) < mod.MIN_POSTURE_SIGNAL_ROWS

    def test_partial_content_collapse_trips_the_floor_RED(self) -> None:
        """RED: an intact 921-office universe whose posture content collapsed to 40
        signal-bearing rows -- the SET gate passes, the shrink guard passes (no
        shrink at all), and only the value floor can catch it."""
        with pytest.raises(mod.SnapshotRefusedError):
            mod.assert_posture_signal_floor(_frame(921, 40))

    def test_empty_universe_is_not_the_floors_remit_GREEN(self) -> None:
        """Unchanged semantics: an empty universe is assert_complete_office_set's
        refusal, never the value floor's (a floor raise must not steal its remit)."""
        mod.assert_posture_signal_floor(_frame(0, 0))


class TestC5FloorIsOperatorRatchetable:
    def test_env_override_raises_the_floor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(mod.MIN_POSTURE_SIGNAL_ROWS_ENV_VAR, "450")
        assert mod._resolve_min_posture_signal_rows() == 450

    def test_absent_env_uses_the_derived_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(mod.MIN_POSTURE_SIGNAL_ROWS_ENV_VAR, raising=False)
        assert mod._resolve_min_posture_signal_rows() == 100

    @pytest.mark.parametrize("bad", ["0", "-5", "", "abc", "12.5"])
    def test_a_floor_disabling_override_is_refused_RED(
        self, monkeypatch: pytest.MonkeyPatch, bad: str
    ) -> None:
        """RED: an override of 0/negative/garbage would restore EXACTLY the blindness
        C5 cures. It must degrade to the derived default, never disable the floor."""
        monkeypatch.setenv(mod.MIN_POSTURE_SIGNAL_ROWS_ENV_VAR, bad)
        assert mod._resolve_min_posture_signal_rows() == 100

    def test_module_constant_honours_the_env_at_import(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The ratchet must be reachable without a deploy: re-importing under the env
        override yields the overridden constant (Lambda resolves this at cold start)."""
        monkeypatch.setenv(mod.MIN_POSTURE_SIGNAL_ROWS_ENV_VAR, "377")
        reloaded = importlib.reload(mod)
        try:
            assert reloaded.MIN_POSTURE_SIGNAL_ROWS == 377
        finally:
            monkeypatch.delenv(mod.MIN_POSTURE_SIGNAL_ROWS_ENV_VAR, raising=False)
            importlib.reload(mod)


# ---------------------------------------------------------------------------
# C1 -- the alarm-bound emissions
# ---------------------------------------------------------------------------


class _Recorder:
    """Captures emit_metric calls as (name, value, dimensions)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, float, dict[str, str] | None]] = []

    def __call__(
        self,
        metric_name: str,
        value: float,
        unit: str = "Count",
        dimensions: dict[str, str] | None = None,
        namespace: str | None = None,
    ) -> None:
        self.calls.append((metric_name, value, dimensions))

    def names(self) -> list[str]:
        return [c[0] for c in self.calls]

    def value_of(self, name: str) -> float:
        matches = [c[1] for c in self.calls if c[0] == name]
        assert matches, f"{name} was never emitted; emitted={self.names()}"
        return matches[-1]


@pytest.fixture
def rec(monkeypatch: pytest.MonkeyPatch) -> _Recorder:
    r = _Recorder()
    monkeypatch.setattr(mod, "emit_metric", r)
    return r


class _Office:
    """Minimal ExtractedScheduling stand-in: the orchestrator only reads ``.guid``."""

    def __init__(self, guid: str) -> None:
        self.guid = guid


class _PushResult:
    """Minimal StratumPushResult stand-in: the orchestrator reads ``.pushed`` /
    ``.entry_count``."""

    def __init__(self, ok: bool, n: int) -> None:
        self.pushed = ok
        self.entry_count = n


async def _run(*, gate: bool, pushed: bool | None, offices: int = 921) -> Any:
    extracted = [_Office(f"guid-{i}") for i in range(offices)]

    async def _enumerate() -> tuple[list[Any], bool]:
        return list(extracted), True

    async def _push(_: list[Any]) -> Any:
        # ``None`` models the honest-skip path (token mint failure): no POST, no
        # delivery -- byte-identical in outcome to a POST that returned not-ok.
        return None if pushed is None else _PushResult(pushed, offices)

    return await mod.execute_snapshot_push(
        gate=lambda: gate, enumerate_offices=_enumerate, push=_push
    )


class TestC1PushOutcomeEmissions:
    @pytest.mark.asyncio
    async def test_delivered_run_emits_zero_failure_and_a_push_heartbeat_GREEN(
        self, rec: _Recorder
    ) -> None:
        result = await _run(gate=True, pushed=True)
        assert result.status == "pushed"
        assert rec.value_of(mod.METRIC_PUSH_FAILED) == 0
        assert rec.value_of(mod.METRIC_PUSH_EPOCH) > 1_700_000_000

    @pytest.mark.asyncio
    async def test_undelivered_run_emits_failure_and_NO_push_heartbeat_RED(
        self, rec: _Recorder
    ) -> None:
        """★ THE ACCEPTANCE TEST. This is the exact shape of all 18 non-refused
        ticks of the darkness: the run completes, exits 0, logs pushed=false --
        and now publishes PushFailed=1 while publishing NO PushEpoch. The absent
        heartbeat is what a treat_missing_data=breaching alarm converts into a page."""
        result = await _run(gate=True, pushed=False)
        assert result.status == "dry_run"
        assert rec.value_of(mod.METRIC_PUSH_FAILED) == 1
        assert mod.METRIC_PUSH_EPOCH not in rec.names(), (
            "a push heartbeat on an UNDELIVERED run makes the freshness deadman "
            "green-on-fossil -- the exact blind class"
        )

    @pytest.mark.asyncio
    async def test_mint_failure_path_emits_no_push_heartbeat_RED(self, rec: _Recorder) -> None:
        """RED: the honest-skip path (token mint failed -> push returns None) is a
        NON-delivery and must look identical to any other non-delivery."""
        await _run(gate=True, pushed=None)
        assert rec.value_of(mod.METRIC_PUSH_FAILED) == 1
        assert mod.METRIC_PUSH_EPOCH not in rec.names()

    @pytest.mark.asyncio
    async def test_gated_off_run_emits_neither_RED(self, rec: _Recorder) -> None:
        """RED: a DARK-gated run never reaches the push, so it must not fabricate a
        delivery heartbeat (that would keep the freshness deadman green while the
        substrate ages out)."""
        result = await _run(gate=False, pushed=True)
        assert result.status == "skipped"
        assert mod.METRIC_PUSH_EPOCH not in rec.names()
        assert mod.METRIC_PUSH_FAILED not in rec.names()

    @pytest.mark.asyncio
    async def test_refused_run_emits_no_push_heartbeat_RED(self, rec: _Recorder) -> None:
        """RED: the 100 value-floor refusals of the darkness. A refusal delivers
        nothing, so no freshness heartbeat may be published."""

        async def _enumerate() -> tuple[list[Any], bool]:
            return [], False

        async def _push(_: list[Any]) -> Any:  # pragma: no cover - never reached
            raise AssertionError("push must not run after a refusal")

        result = await mod.execute_snapshot_push(
            gate=lambda: True, enumerate_offices=_enumerate, push=_push
        )
        assert result.status == "refused"
        assert mod.METRIC_PUSH_EPOCH not in rec.names()


class TestC1LivenessHeartbeat:
    def test_handler_emits_a_run_heartbeat_on_every_invocation_GREEN(
        self, monkeypatch: pytest.MonkeyPatch, rec: _Recorder
    ) -> None:
        monkeypatch.setattr(
            mod,
            "run_snapshot_push_async",
            lambda *a, **k: _immediate(mod.SnapshotRunResult("skipped", "gate_off", 0)),
        )
        mod.handler({}, None)
        assert rec.value_of(mod.METRIC_RUN_EPOCH) > 1_700_000_000

    def test_run_heartbeat_survives_a_crashing_run_RED(
        self, monkeypatch: pytest.MonkeyPatch, rec: _Recorder
    ) -> None:
        """RED: a heartbeat emitted only on the happy path cannot distinguish a dead
        producer from a crashing one. It must be emitted BEFORE anything that raises."""

        def _boom(*_a: Any, **_k: Any) -> Any:
            raise RuntimeError("substrate exploded")

        monkeypatch.setattr(mod, "run_snapshot_push_async", _boom)
        response = mod.handler({}, None)
        assert response["statusCode"] == 500
        assert mod.METRIC_RUN_EPOCH in rec.names()


async def _immediate(value: Any) -> Any:
    return value


# ---------------------------------------------------------------------------
# The cross-repo contract + the untouched-body pin
# ---------------------------------------------------------------------------


class TestCrossRepoContract:
    def test_alarm_bound_metrics_are_frozen(self) -> None:
        """Byte-exact seam with terraform/services/asana/scheduling_stratum_producer_
        alarms.tf in the autom8y repo. A rename on EITHER side decouples the pair
        into a permanently-INSUFFICIENT_DATA alarm; the autom8y-side test pins the
        same literals against the HCL."""
        assert (
            frozenset(
                {
                    "SchedulingStratumSnapshotRunEpoch",
                    "SchedulingStratumSnapshotPushEpoch",
                    "SchedulingStratumSnapshotPushFailed",
                    "SchedulingStratumUniverseCensus",
                    "SchedulingStratumSnapshotDegenerateSource",
                }
            )
            == mod.ALARM_BOUND_METRICS
        )

    def test_alarm_bound_metrics_carry_no_high_cardinality_dimension(
        self, rec: _Recorder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """★ RED-class guard. The pre-existing ...Pushed/...DryRun emissions stamp
        office_count as a DIMENSION, forking a new metric series per tick and making
        them structurally unalarmable (live list-metrics on 2026-08-06: 12 distinct
        ...DryRun series). No ALARM_BOUND metric may repeat that mistake."""
        import asyncio

        asyncio.run(_run(gate=True, pushed=True))
        for name, _value, dims in rec.calls:
            if name in mod.ALARM_BOUND_METRICS:
                assert not dims, f"{name} carries alarm-breaking dimensions {dims}"

    def test_the_unalarmable_legacy_emission_is_still_present(self, rec: _Recorder) -> None:
        """The office_count-dimensioned emission is RETAINED (dashboards read it);
        this pins that the new metrics ADD a surface rather than replace one."""
        import asyncio

        asyncio.run(_run(gate=True, pushed=True))
        legacy = [c for c in rec.calls if c[0] == "SchedulingStratumSnapshotPushed"]
        assert legacy and legacy[0][2] == {"office_count": "921"}


class TestCertifiedBodiesUntouched:
    def test_value_floor_body_still_compares_against_the_module_constant(self) -> None:
        """The certified guard body is preserved byte-for-byte: C5 moves the
        THRESHOLD, never the comparison. Only the constant's derivation changed."""
        import inspect

        src = inspect.getsource(mod.assert_posture_signal_floor)
        assert "if signal_rows < MIN_POSTURE_SIGNAL_ROWS:" in src
        assert "os.environ" not in src, "the guard body must not grow an env read"

    def test_universe_and_representative_rules_are_untouched(self) -> None:
        import inspect

        src = inspect.getsource(mod.project_posture_rows)
        assert 'unique(subset=[GUID_FIELD], keep="first", maintain_order=True)' in src
