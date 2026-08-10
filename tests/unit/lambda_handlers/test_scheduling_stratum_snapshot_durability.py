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


async def _run(
    *, gate: bool, pushed: bool | None, offices: int = 921, shadow_run: bool = False
) -> Any:
    extracted = [_Office(f"guid-{i}") for i in range(offices)]

    async def _enumerate() -> tuple[list[Any], bool]:
        return list(extracted), True

    async def _push(_: list[Any]) -> Any:
        # ``None`` models the honest-skip path (token mint failure): no POST, no
        # delivery -- byte-identical in outcome to a POST that returned not-ok.
        return None if pushed is None else _PushResult(pushed, offices)

    return await mod.execute_snapshot_push(
        gate=lambda: gate,
        enumerate_offices=_enumerate,
        push=_push,
        shadow_run=shadow_run,
    )


#: The VERBATIM refusal reason observed on 94 of the 102 terminal ticks over the
#: real darkness window 2026-07-06..2026-08-01 on
#: /aws/lambda/autom8-asana-scheduling-stratum-snapshot -- unvarying, and produced
#: by ``assert_complete_office_set``'s empty-set arm.
_LIVE_REFUSAL_REASON = "empty active-office set (refusing an empty whole-source push)"


async def _run_refused_empty_office_set() -> Any:
    """The EXACT live refusal shape: source readable, deduped guid set EMPTY.

    This is the 92% path. ``enumerate_offices`` succeeds (``source_complete=True``)
    and ``assert_complete_office_set`` raises on the empty list -- so the run
    ``return``s from the refusal arm and NEVER reaches the push emissions.
    """

    async def _enumerate() -> tuple[list[Any], bool]:
        return [], True

    async def _push(_: list[Any]) -> Any:  # pragma: no cover - never reached
        raise AssertionError("push must not run after a refusal")

    return await mod.execute_snapshot_push(
        gate=lambda: True, enumerate_offices=_enumerate, push=_push
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
                    "SchedulingStratumSnapshotRefused",
                    "SchedulingStratumSnapshotSchemaLag",
                    "SchedulingStratumUniverseCensus",
                    "SchedulingStratumSnapshotDegenerateSource",
                }
            )
            == mod.ALARM_BOUND_METRICS
        )

    def test_the_shadow_run_marker_is_deliberately_unbound(self) -> None:
        """D-2's new marker is an OPERATIONAL fact, not a fault. Binding an alarm to
        it would page for a deliberate operator action -- the very conflation D-2
        cures, re-introduced on the other side. It must NOT be in the alarm set."""
        assert mod.METRIC_SHADOW_RUN not in mod.ALARM_BOUND_METRICS

    def test_alarm_bound_metrics_carry_no_high_cardinality_dimension(
        self, rec: _Recorder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """★ RED-class guard. The pre-existing ...Pushed/...DryRun emissions stamp
        office_count as a DIMENSION, forking a new metric series per tick and making
        them structurally unalarmable (live list-metrics on 2026-08-06: 12 distinct
        ...DryRun series). No ALARM_BOUND metric may repeat that mistake.

        Swept over EVERY terminal path, not just the delivering one: D-1 was exactly
        an alarm-bound-worthy signal that carried a ``reason`` dimension on a path the
        delivering sweep never visits."""
        import asyncio

        asyncio.run(_run(gate=True, pushed=True))
        asyncio.run(_run(gate=True, pushed=False))
        asyncio.run(_run(gate=False, pushed=True))
        asyncio.run(_run_refused_empty_office_set())
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


# ---------------------------------------------------------------------------
# ★ D-1 -- the REFUSED path must drive an alarm (92% of the historical outage)
# ---------------------------------------------------------------------------
# Measured own-hands by the chaos-engineer over the real darkness window
# 2026-07-06..2026-08-01 on /aws/lambda/autom8-asana-scheduling-stratum-snapshot:
#
#     94 ticks  scheduling_stratum_snapshot_refused   (verbatim, unvarying reason:
#               "empty active-office set (refusing an empty whole-source push)")
#      8 ticks  scheduling_stratum_snapshot_complete with pushed=false
#
# ``SchedulingStratumSnapshotPushFailed`` is emitted only AFTER the push call, and
# the refusal arm ``return``s before it -- so the alarm NAMED for this outage was
# blind to 94/102 = 92% of it. Its alarm is treat_missing_data=notBreaching, so
# that absence read as OK for the whole month.


class TestD1RefusalDrivesAnAlarmableSignal:
    @pytest.mark.asyncio
    async def test_the_live_refusal_shape_is_reproduced_exactly(self) -> None:
        """Anchor the fixture to the measured reality before asserting anything about
        it: this is the byte-exact reason string all 94 refusing ticks logged."""
        result = await _run_refused_empty_office_set()
        assert result.status == "refused"
        assert result.reason == _LIVE_REFUSAL_REASON

    @pytest.mark.asyncio
    async def test_refusing_tick_emits_an_ALARM_BOUND_signal_RED(self, rec: _Recorder) -> None:
        """★ THE D-1 ACCEPTANCE TEST. A tick that refuses with "empty active-office
        set" must publish a signal an alarm can actually bind. Pre-fix the refusal
        emitted a metric that was NOT in ALARM_BOUND_METRICS, so no alarm watched it
        and its absence on the push-failure series read as OK."""
        await _run_refused_empty_office_set()
        bound_emitted = [n for n in rec.names() if n in mod.ALARM_BOUND_METRICS]
        assert bound_emitted, (
            "a refusing tick published NO alarm-bound metric -- the 92% blind path. "
            f"emitted={rec.names()}"
        )
        assert mod.METRIC_REFUSED in bound_emitted

    @pytest.mark.asyncio
    async def test_the_refusal_signal_is_dimension_free_RED(self, rec: _Recorder) -> None:
        """★ THE STRUCTURAL HALF. An alarm pins {environment} and nothing else, and
        CloudWatch dimension matching is EXACT -- a ``reason`` DIMENSION puts the
        datapoint on a series no such alarm can ever read. Pre-fix the refusal carried
        ``dimensions={"reason": "incomplete_office_set"}``: the same trap
        ``office_count`` sprang on ...Pushed/...DryRun. The reason belongs in the LOG
        line (which still carries it verbatim), never in the metric's identity."""
        await _run_refused_empty_office_set()
        emitted = [c for c in rec.calls if c[0] == mod.METRIC_REFUSED]
        assert emitted, f"{mod.METRIC_REFUSED} never emitted; emitted={rec.names()}"
        name, value, dims = emitted[-1]
        assert value == 1
        assert dims is None, (
            f"{name} carries dimension(s) {dims} -- an alarm binding {{environment}} "
            "alone cannot match this series, so the signal is unalarmable"
        )

    @pytest.mark.asyncio
    async def test_the_gate_off_skip_is_also_dimension_free_RED(self, rec: _Recorder) -> None:
        """Same structural cure on the sibling terminal path. No alarm binds Skipped
        (a DARK gate is an operator state, not a fault -- substrate-stale is its
        catcher), but leaving a ``reason`` dimension on it would make it permanently
        UNBINDABLE, which is how this class of blindness is minted in the first place."""
        await _run(gate=False, pushed=True)
        emitted = [c for c in rec.calls if c[0] == mod.METRIC_SKIPPED]
        assert emitted and emitted[-1][2] is None, f"Skipped carries dimensions: {emitted}"

    @pytest.mark.asyncio
    async def test_a_healthy_delivering_tick_does_NOT_emit_the_refusal_signal_GREEN(
        self, rec: _Recorder
    ) -> None:
        """★ THE MUST-NOT-TRIP HALF. A guard that fires on healthy traffic is worse
        than no guard. A delivering tick publishes the push heartbeat and does not
        TRIP the refusal series, so the alarm stays OK through steady state.

        ★ AMENDED BY L2 (2026-08-11), teeth STRENGTHENED not relaxed. This assertion
        was ``METRIC_REFUSED not in rec.names()`` -- which conflated ``did not fire``
        with ``published nothing``, and it was that second property (silence) which
        left the alarm OK-by-missing-data rather than OK-by-measurement. A healthy
        tick now publishes a real 0. The must-not-trip claim is asserted directly
        against the alarm's own comparison (GreaterThanThreshold(0)): the emitted
        value must be 0, which is a STRICTLY stronger statement than absence, since
        absence was also satisfied by a dead emitter."""
        result = await _run(gate=True, pushed=True)
        assert result.status == "pushed"
        assert _values_of(rec, mod.METRIC_REFUSED) == [0], (
            "a delivering tick must publish exactly one MEASURED non-firing 0 on the "
            f"refusal series; emitted={rec.names()}"
        )
        assert not any(v > 0 for v in _values_of(rec, mod.METRIC_REFUSED)), (
            "the refusal alarm is GreaterThanThreshold(0) -- any value above 0 on a "
            "healthy delivering tick would page SEV-1 for steady state"
        )
        assert rec.value_of(mod.METRIC_PUSH_EPOCH) > 1_700_000_000

    @pytest.mark.asyncio
    async def test_push_failed_remains_blind_to_the_refusal_path_by_design(
        self, rec: _Recorder
    ) -> None:
        """The scope correction, asserted rather than merely described. PushFailed is
        the REACHED-PUSH class and stays that way -- the refusal arm returns before
        it. That is precisely why its alarm_description had to be corrected and why a
        SEPARATE refusal binding (not a widened PushFailed) is the cure."""
        await _run_refused_empty_office_set()
        assert mod.METRIC_PUSH_FAILED not in rec.names()
        assert mod.METRIC_PUSH_EPOCH not in rec.names()

    @pytest.mark.asyncio
    async def test_the_schema_lag_marker_is_alarm_bound_and_dimension_free(self) -> None:
        """The second refusal sub-class. ...SchemaLag was already emitted with no
        dimensions and was simply never bound to an alarm -- an instrument that exists
        and watches nothing. It joins the contract here."""
        assert mod.METRIC_SCHEMA_LAG in mod.ALARM_BOUND_METRICS
        assert mod.METRIC_SCHEMA_LAG == "SchedulingStratumSnapshotSchemaLag"


# ---------------------------------------------------------------------------
# ★ D-2 -- a deliberate shadow run is NOT a delivery failure
# ---------------------------------------------------------------------------
# Observed LIVE in production 2026-08-06T09:05:15Z (RequestId
# 8fde3ea0-0436-4492-b2cc-031368bf904e): a forced dry-run (``event["dry_run"]``, an
# explicitly supported operation) emitted SchedulingStratumSnapshotPushFailed=1 and
# suppressed PushEpoch -- byte-identical at the metric layer to a real failure. Once
# actions are armed, two shadow runs inside consecutive 2h windows page SEV-1 (live
# SMS subscriber) for a non-incident.


class TestD2ShadowRunIsDistinguishableFromFailure:
    @pytest.mark.asyncio
    async def test_forced_dry_run_emits_shadow_run_and_NOT_push_failed_RED(
        self, rec: _Recorder
    ) -> None:
        """★ THE D-2 ACCEPTANCE TEST. Pre-fix this exact path emitted PushFailed=1
        (the live 09:05:15Z observation). It must now publish the ShadowRun marker and
        publish NOTHING on the failure series -- not even a 0, which would assert a
        delivery that did not happen."""
        await _run(gate=True, pushed=False, shadow_run=True)
        assert rec.value_of(mod.METRIC_SHADOW_RUN) == 1
        assert mod.METRIC_PUSH_FAILED not in rec.names(), (
            "a deliberate shadow run published on the failure series -- two shadow "
            "runs in consecutive 2h windows would page SEV-1 for a non-incident"
        )

    @pytest.mark.asyncio
    async def test_a_GENUINE_non_delivery_still_emits_push_failed_GREEN(
        self, rec: _Recorder
    ) -> None:
        """★ THE MUST-STILL-TRIP HALF. The cure must not buy quiet by going blind:
        the same run WITHOUT the forced flag is a real failure and still publishes
        PushFailed=1 with no ShadowRun marker."""
        await _run(gate=True, pushed=False, shadow_run=False)
        assert rec.value_of(mod.METRIC_PUSH_FAILED) == 1
        assert mod.METRIC_SHADOW_RUN not in rec.names()

    @pytest.mark.asyncio
    async def test_mint_failure_is_a_genuine_failure_not_a_shadow_run_GREEN(
        self, rec: _Recorder
    ) -> None:
        """The honest-skip path (push returns None) is a NON-delivery nobody asked
        for. It must keep looking like the failure it is."""
        await _run(gate=True, pushed=None, shadow_run=False)
        assert rec.value_of(mod.METRIC_PUSH_FAILED) == 1
        assert mod.METRIC_SHADOW_RUN not in rec.names()

    @pytest.mark.asyncio
    async def test_shadow_run_does_NOT_fabricate_a_push_heartbeat(self, rec: _Recorder) -> None:
        """★ DELIBERATELY PRESERVED. A shadow run does not deliver, so it advances the
        substrate toward the 8h TTL cliff exactly like any other non-delivery.
        substrate-stale MUST keep seeing no PushEpoch. Curing D-2 by emitting a fake
        heartbeat would trade a false page for a fossil substrate served silently."""
        await _run(gate=True, pushed=False, shadow_run=True)
        assert mod.METRIC_PUSH_EPOCH not in rec.names()

    @pytest.mark.asyncio
    async def test_a_delivering_run_never_emits_the_shadow_marker_GREEN(
        self, rec: _Recorder
    ) -> None:
        await _run(gate=True, pushed=True, shadow_run=False)
        assert mod.METRIC_SHADOW_RUN not in rec.names()
        assert rec.value_of(mod.METRIC_PUSH_FAILED) == 0

    def test_the_event_forced_dry_run_reaches_the_orchestrator_as_a_shadow_run_RED(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """★ THE WIRING. Proves the production path end-to-end from the Lambda event:
        handler -> run_snapshot_push_async -> execute_snapshot_push(shadow_run=True).
        Without this leg the new metric could be correct and never reached."""
        seen: dict[str, Any] = {}

        async def _capture(**kwargs: Any) -> Any:
            seen.update(kwargs)
            return mod.SnapshotRunResult("dry_run", None, 0)

        monkeypatch.setattr(mod, "execute_snapshot_push", _capture)
        mod.handler({"dry_run": True}, None)
        assert seen.get("shadow_run") is True

    def test_a_scheduled_tick_is_NEVER_a_shadow_run_GREEN(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RED-complement: the EventBridge tick carries no ``dry_run`` key, so a real
        delivery failure on the scheduled cadence still routes to PushFailed. A
        shadow_run that defaulted true would silence the alarm entirely."""
        seen: dict[str, Any] = {}

        async def _capture(**kwargs: Any) -> Any:
            seen.update(kwargs)
            return mod.SnapshotRunResult("pushed", None, 921)

        monkeypatch.setattr(mod, "execute_snapshot_push", _capture)
        mod.handler({}, None)
        assert seen.get("shadow_run") is False

    def test_an_explicit_dry_run_false_event_is_not_a_shadow_run_GREEN(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A confused/malicious {"dry_run": False} must not be able to mark a real
        failure as a shadow run and suppress its alarm."""
        seen: dict[str, Any] = {}

        async def _capture(**kwargs: Any) -> Any:
            seen.update(kwargs)
            return mod.SnapshotRunResult("pushed", None, 921)

        monkeypatch.setattr(mod, "execute_snapshot_push", _capture)
        mod.handler({"dry_run": False}, None)
        assert seen.get("shadow_run") is False


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

    def test_completeness_contract_body_is_untouched(self) -> None:
        """★ THE FENCE, MADE MECHANICAL. The D-1/D-2 observability cure changes what
        the orchestrator PUBLISHES about a refusal, never what causes one. This body
        is the whole-source-DELETE safety and must stay byte-identical -- including
        the verbatim reason string 94 live ticks logged."""
        import inspect

        src = inspect.getsource(mod.assert_complete_office_set)
        assert 'raise SnapshotRefusedError("empty active-office set ' in src
        assert "if not source_complete:" in src
        assert "emit_metric" not in src, "the guard body must not grow an emission"

    def test_posture_signal_counter_body_is_untouched(self) -> None:
        """Same fence on the value floor's numerator: the instrument moved, the
        arithmetic did not."""
        import inspect

        src = inspect.getsource(mod.posture_signal_row_count)
        assert "pl.any_horizontal([pl.col(c).is_not_null() for c in signal_cols])" in src
        assert "emit_metric" not in src


# ---------------------------------------------------------------------------
# ★ L2 -- the OK-by-MISSING-DATA blindness on the three FIRE-ONLY series
# ---------------------------------------------------------------------------
# Three alarm-bound series published ONLY on their fault path and NOTHING otherwise:
# SchedulingStratumSnapshotDegenerateSource, ...Refused, ...SchemaLag. Their alarms
# are GreaterThanThreshold(0) + treat_missing_data=notBreaching, so on a healthy tick
# the alarm saw NO DATA and sat OK *by the missing-data rule*. That OK is BLIND: it is
# byte-identical to the OK produced by a dead emitter, a renamed metric, a
# wrong-dimension emission, or a revoked cloudwatch:PutMetricData.
#
# Measured own-hands 2026-08-10 via get-metric-statistics on {environment=production}:
# NONE of the three had EVER published a datapoint on the series its alarm binds.
# Over the same window SchedulingStratumSnapshotPushFailed published 13 consecutive
# real 0s at the 2h cadence -- which is exactly why ITS OK is value-driven. These
# tests are the teeth on porting that template to the other three.
#
# SCOPE, do not over-read: a real 0 makes the OK VALUE-DRIVEN. It does NOT prove the
# alarm can reach ALARM. The RED legs are owed to the operator-attended injection
# (CARD-RUL19-INJECTION) because driving these alarms pages a live SEV-1 SMS
# subscriber.


def _uh_business_spine(
    n_rows: int, n_signal_rows: int, *, posture_columns: bool = True
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Build the (unit_holder, business) SPINE the producer actually reads.

    ``posture_columns=False`` yields the SCHEMA-LAG shape: a base-columns-only
    unit_holder frame that predates UNIT_HOLDER_SCHEMA, which is what a warmer that
    has not completed a cycle since a schema change serves.
    """
    import datetime as dt

    from autom8_asana.normalizer.scheduling_extractor import (
        GUID_FIELD,
        REQUIRED_FRAME_COLUMNS,
    )

    unit_holder: dict[str, list[Any]] = {
        "gid": [f"uh{i}" for i in range(n_rows)],
        "parent_gid": [f"b{i}" for i in range(n_rows)],
        "last_modified": [dt.datetime(2026, 1, 1, tzinfo=dt.UTC)] * n_rows,
    }
    if posture_columns:
        for col in REQUIRED_FRAME_COLUMNS:
            if col == GUID_FIELD:
                continue  # company_id lives on the BUSINESS side of the spine
            unit_holder[col] = [None] * n_rows
        # Signal is carried on custom_cal_status, the column the value floor counts.
        unit_holder["custom_cal_status"] = [
            "enabled" if i < n_signal_rows else None for i in range(n_rows)
        ]
    business = pl.DataFrame(
        {"gid": [f"b{i}" for i in range(n_rows)], GUID_FIELD: [f"g{i}" for i in range(n_rows)]}
    )
    return pl.DataFrame(unit_holder), business


class _FakeEntry:
    def __init__(self, dataframe: Any) -> None:
        self.dataframe = dataframe


class _FakeSpineCache:
    """Serves the two spine frames by entity_type (the producer reads BOTH)."""

    def __init__(self, unit_holder: Any, business: Any) -> None:
        self._entries = {
            mod.SNAPSHOT_UNIT_HOLDER_ENTITY_TYPE: _FakeEntry(unit_holder),
            mod.SNAPSHOT_BUSINESS_ENTITY_TYPE: _FakeEntry(business),
        }

    async def get_async(self, _project_gid: str, entity_type: str) -> Any:
        return self._entries.get(entity_type)


async def _run_through_real_enumerate(
    n_rows: int, n_signal_rows: int, *, posture_columns: bool = True
) -> Any:
    """Drive execute_snapshot_push through the REAL ``_enumerate_offices_from_frame``.

    The three 1-emissions live INSIDE that function, so a proof that the companion 0
    never coincides with them has to traverse the real fire sites -- an injectable
    stub would prove only the orchestrator's half.
    """
    unit_holder, business = _uh_business_spine(
        n_rows, n_signal_rows, posture_columns=posture_columns
    )
    cache = _FakeSpineCache(unit_holder, business)

    async def _push(_: list[Any]) -> Any:
        return _PushResult(True, n_rows)

    return await mod.execute_snapshot_push(
        gate=lambda: True,
        enumerate_offices=lambda: mod._enumerate_offices_from_frame(cache, "UH", "BIZ"),
        push=_push,
    )


def _values_of(rec: _Recorder, name: str) -> list[float]:
    return [c[1] for c in rec.calls if c[0] == name]


class TestL2CompanionSeriesContract:
    def test_the_companion_set_is_exactly_the_three_fire_only_series(self) -> None:
        """The seam, pinned. These three -- and ONLY these three -- were alarm-bound
        with no real-0 publisher. RunEpoch/UniverseCensus already publish a value on
        every tick; PushFailed already publishes ``0 if pushed else 1``; PushEpoch is
        deliberately absence-signalling (the freshness dead-man reads its silence)."""
        assert set(mod.SOURCE_HEALTH_COMPANION_METRICS) == {
            "SchedulingStratumSnapshotDegenerateSource",
            "SchedulingStratumSnapshotRefused",
            "SchedulingStratumSnapshotSchemaLag",
        }

    def test_every_companion_is_alarm_bound(self) -> None:
        """A 0 published on a name no alarm binds is storage nobody reads; a companion
        missing from the alarm set means an alarm was retired without its companion."""
        assert set(mod.SOURCE_HEALTH_COMPANION_METRICS) <= mod.ALARM_BOUND_METRICS

    def test_the_absence_signalling_metrics_are_NOT_given_companions_RED(self) -> None:
        """★ RED: PushEpoch's whole detection mechanism IS its absence -- the
        substrate-freshness dead-man is treat_missing_data=breaching and converts
        silence into a page ~1h before every office flips to fallback_ghl. Publishing
        a companion 0 there (or on RunEpoch, the liveness dead-man) would hold both
        dead-men permanently green over a dead producer. This is the single most
        dangerous way to over-apply this cure."""
        assert mod.METRIC_PUSH_EPOCH not in mod.SOURCE_HEALTH_COMPANION_METRICS
        assert mod.METRIC_RUN_EPOCH not in mod.SOURCE_HEALTH_COMPANION_METRICS
        assert mod.METRIC_PUSH_FAILED not in mod.SOURCE_HEALTH_COMPANION_METRICS


class TestL2HealthyTickPublishesRealZeros:
    @pytest.mark.asyncio
    async def test_a_delivering_tick_publishes_a_real_zero_on_all_three_GREEN(
        self, rec: _Recorder
    ) -> None:
        """★ THE L2 ACCEPTANCE TEST. Pre-fix a healthy tick published NOTHING on these
        three and the alarms sat OK purely because treat_missing_data=notBreaching
        said so. Each must now carry a measured 0."""
        result = await _run(gate=True, pushed=True)
        assert result.status == "pushed"
        for name in mod.SOURCE_HEALTH_COMPANION_METRICS:
            assert _values_of(rec, name) == [0], (
                f"{name} did not publish exactly one real 0 on a healthy tick; "
                f"emitted={rec.names()}"
            )

    @pytest.mark.asyncio
    async def test_the_zeros_are_DIMENSION_FREE_RED(self, rec: _Recorder) -> None:
        """★ THE STRUCTURAL HALF, and the ORIGINAL SCAR. CloudWatch dimension matching
        is EXACT: the alarms bind {environment} ALONE. A companion carrying a second
        dimension (the {environment, reason} shape that made the refusal signal
        unalarmable in the first place) would publish onto a series no alarm can read
        -- the alarm would stay OK-by-missing-data and the cure would be theatre."""
        await _run(gate=True, pushed=True)
        for name in mod.SOURCE_HEALTH_COMPANION_METRICS:
            emitted = [c for c in rec.calls if c[0] == name]
            assert emitted, f"{name} never emitted"
            for _n, _v, dims in emitted:
                assert dims is None, (
                    f"{name} companion carries dimension(s) {dims} -- an alarm binding "
                    "{environment} alone cannot match this series"
                )

    @pytest.mark.asyncio
    async def test_a_shadow_run_still_publishes_the_source_zeros_GREEN(
        self, rec: _Recorder
    ) -> None:
        """These three measure SOURCE health, not DELIVERY health. A deliberate shadow
        run DID enumerate and DID clear every guard, so ``no refusal occurred`` is an
        honest fact about it. This is NOT the D-2 shape: D-2 refused to publish
        PushFailed=0 on a shadow run because that would assert a DELIVERY that never
        happened -- here the evaluation genuinely happened."""
        await _run(gate=True, pushed=False, shadow_run=True)
        for name in mod.SOURCE_HEALTH_COMPANION_METRICS:
            assert _values_of(rec, name) == [0]
        assert mod.METRIC_PUSH_FAILED not in rec.names()

    @pytest.mark.asyncio
    async def test_a_non_delivering_tick_still_publishes_the_source_zeros_GREEN(
        self, rec: _Recorder
    ) -> None:
        """A push that reached the data side and failed is a DELIVERY fault. The source
        was still evaluated and still clean, so the source series must say so while
        PushFailed=1 carries the delivery fault on its own honest axis."""
        await _run(gate=True, pushed=False)
        for name in mod.SOURCE_HEALTH_COMPANION_METRICS:
            assert _values_of(rec, name) == [0]
        assert rec.value_of(mod.METRIC_PUSH_FAILED) == 1

    @pytest.mark.asyncio
    async def test_a_gate_off_tick_publishes_NO_companion_zero_RED(self, rec: _Recorder) -> None:
        """★ THE OVER-CLAIM REFUSAL. A DARK gate never enumerates -- no frame is read,
        no guard runs. Publishing ``DegenerateSource=0`` there would assert ``we
        evaluated the source and it was sound`` on a tick that never looked. Same
        discipline D-2 applied when it declined to publish PushFailed=0 on a shadow
        run. A gate left off by accident is the substrate-freshness dead-man's remit."""
        result = await _run(gate=False, pushed=True)
        assert result.status == "skipped"
        for name in mod.SOURCE_HEALTH_COMPANION_METRICS:
            assert name not in rec.names(), (
                f"{name} published on a tick that never evaluated the source"
            )


class TestL2CompanionsCanNeverMaskAFiring:
    """RED side, driven through the REAL fire sites in ``_enumerate_offices_from_frame``."""

    @pytest.mark.asyncio
    async def test_a_refusing_tick_emits_the_1_and_NO_zero_RED(self, rec: _Recorder) -> None:
        """★ The live 92% shape (empty active-office set). Refused must carry 1 and
        NOTHING else -- a 0 alongside it would let the Maximum statistic still see the
        1, but a 0 emitted INSTEAD of the 1 would silence the alarm outright."""
        result = await _run_refused_empty_office_set()
        assert result.status == "refused"
        assert _values_of(rec, mod.METRIC_REFUSED) == [1]
        assert 0 not in _values_of(rec, mod.METRIC_REFUSED)

    @pytest.mark.asyncio
    async def test_a_schema_lag_tick_emits_SchemaLag_1_and_NO_zero_RED(
        self, rec: _Recorder
    ) -> None:
        """RED through the REAL fire site: a base-columns-only unit_holder frame raises
        FrameSchemaLagError inside the enumeration, which emits SchemaLag=1 and
        re-raises as a refusal -- so the orchestrator returns from the except arm and
        the companion line is never reached."""
        result = await _run_through_real_enumerate(5, 5, posture_columns=False)
        assert result.status == "refused"
        assert _values_of(rec, mod.METRIC_SCHEMA_LAG) == [1]
        assert _values_of(rec, mod.METRIC_REFUSED) == [1]
        assert 0 not in _values_of(rec, mod.METRIC_SCHEMA_LAG)

    @pytest.mark.asyncio
    async def test_a_degenerate_source_tick_emits_the_1_and_NO_zero_RED(
        self, rec: _Recorder
    ) -> None:
        """RED through the REAL fire site: a full universe whose posture content is
        all-null trips the value floor, which emits DegenerateSource=1 and re-raises."""
        result = await _run_through_real_enumerate(mod.MIN_POSTURE_SIGNAL_ROWS + 20, 0)
        assert result.status == "refused"
        assert _values_of(rec, "SchedulingStratumSnapshotDegenerateSource") == [1]
        assert 0 not in _values_of(rec, "SchedulingStratumSnapshotDegenerateSource")

    @pytest.mark.asyncio
    async def test_a_healthy_tick_through_the_REAL_enumerate_publishes_zeros_GREEN(
        self, rec: _Recorder
    ) -> None:
        """★ THE MUST-NOT-TRIP HALF of the two RED legs above, through the same code
        path: a spine that clears the floor publishes 0 on all three and 1 on none.
        Without this the RED legs could be passing on an incidental fixture property."""
        n = mod.MIN_POSTURE_SIGNAL_ROWS + 20
        result = await _run_through_real_enumerate(n, n)
        assert result.status == "pushed"
        for name in mod.SOURCE_HEALTH_COMPANION_METRICS:
            assert _values_of(rec, name) == [0]

    def test_no_terminal_path_ever_publishes_BOTH_a_zero_and_a_one_RED(self) -> None:
        """★ THE MUTUAL-EXCLUSION SWEEP. Per TICK (a fresh recorder each run, because
        a shared one would merge ticks and manufacture a false violation), no companion
        series may carry both a 0 and a 1. A tick emitting both would let the Maximum
        statistic keep the firing, but it would also make the series self-contradictory
        and unreviewable -- and any future reordering that put the 0 last would silence
        a real fault under Minimum/Average."""
        import asyncio

        n = mod.MIN_POSTURE_SIGNAL_ROWS + 20
        paths: dict[str, Any] = {
            "delivering": lambda: _run(gate=True, pushed=True),
            "non_delivering": lambda: _run(gate=True, pushed=False),
            "mint_failure": lambda: _run(gate=True, pushed=None),
            "shadow_run": lambda: _run(gate=True, pushed=False, shadow_run=True),
            "gate_off": lambda: _run(gate=False, pushed=True),
            "refused_empty_set": _run_refused_empty_office_set,
            "schema_lag": lambda: _run_through_real_enumerate(5, 5, posture_columns=False),
            "degenerate_source": lambda: _run_through_real_enumerate(n, 0),
            "healthy_real_enumerate": lambda: _run_through_real_enumerate(n, n),
        }
        for label, make in paths.items():
            recorder = _Recorder()
            original = mod.emit_metric
            mod.emit_metric = recorder  # type: ignore[assignment]
            try:
                asyncio.run(make())
            finally:
                mod.emit_metric = original  # type: ignore[assignment]
            for name in mod.SOURCE_HEALTH_COMPANION_METRICS:
                values = set(_values_of(recorder, name))
                assert not ({0, 1} <= values), (
                    f"terminal path {label!r} published BOTH a 0 and a 1 on {name} in a "
                    f"single tick -- the companion can mask (or contradict) a firing"
                )
                assert len(values) <= 1, f"{label!r} published {values} on {name} in one tick"


class TestL2CompanionCannotSwallowAnExceptionIntoAFalseZero:
    @pytest.mark.asyncio
    async def test_a_NON_refusal_exception_publishes_NO_zero_and_PROPAGATES_RED(
        self, rec: _Recorder
    ) -> None:
        """★ THE FALSE-ZERO GUARD. The nightmare shape: an enumeration that blows up
        for a non-refusal reason (unreadable cache, boto timeout, a bug) gets caught,
        swallowed, and reported as ``no refusal detected`` -- a 0 that asserts source
        health nobody ever measured. It would hold all three alarms value-driven-GREEN
        through a total enumeration outage, which is strictly WORSE than the
        missing-data blindness this package cures.

        The exception must escape to the handler (which publishes
        SchedulingStratumSnapshotError=1 and returns an honest 500) and NOT ONE
        companion 0 may be published on the way out."""

        async def _enumerate() -> tuple[list[Any], bool]:
            raise RuntimeError("substrate exploded")

        async def _push(_: list[Any]) -> Any:  # pragma: no cover - never reached
            raise AssertionError("push must not run after an enumeration failure")

        with pytest.raises(RuntimeError, match="substrate exploded"):
            await mod.execute_snapshot_push(
                gate=lambda: True, enumerate_offices=_enumerate, push=_push
            )
        for name in mod.SOURCE_HEALTH_COMPANION_METRICS:
            assert name not in rec.names(), (
                f"{name} published a companion value while the enumeration was failing "
                "-- a swallowed exception became a false assertion of source health"
            )

    @pytest.mark.asyncio
    async def test_a_completeness_gate_crash_publishes_NO_zero_RED(
        self, rec: _Recorder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Same guard on the OTHER statement inside the try: if the completeness gate
        itself raises something that is not a SnapshotRefusedError, no source verdict
        was reached and none may be published."""

        def _boom(*_a: Any, **_k: Any) -> Any:
            raise ValueError("gate imploded")

        monkeypatch.setattr(mod, "assert_complete_office_set", _boom)
        with pytest.raises(ValueError, match="gate imploded"):
            await _run(gate=True, pushed=True)
        for name in mod.SOURCE_HEALTH_COMPANION_METRICS:
            assert name not in rec.names()

    def test_the_companion_emitter_body_carries_no_exception_handler(self) -> None:
        """★ THE FENCE, MADE MECHANICAL (same idiom as the guard-body pins above). A
        try/except inside the emitter is the exact mechanism by which a failure
        becomes a false 0. Emission-level failures already degrade gracefully one
        layer down in ``emit_metric``; a SECOND handler here could only convert a
        control-flow error into a health assertion."""
        import inspect

        # Strip the docstring: it DESCRIBES the dimension trap at length, and matching
        # prose would make this fence pass or fail on wording rather than on code.
        body = inspect.getsource(mod._emit_source_health_companions)
        body = body.replace(mod._emit_source_health_companions.__doc__ or "", "")
        assert "try:" not in body, "the companion emitter must not catch anything"
        assert "except" not in body
        assert "dimensions" not in body, "a companion dimension makes the series unalarmable"

    def test_the_companion_emitter_has_exactly_one_call_site(self) -> None:
        """Two call sites is how a 0-and-1 same-tick violation gets minted later: one
        of them inevitably ends up on the wrong side of the refusal boundary."""
        import inspect

        src = inspect.getsource(mod)
        assert src.count("_emit_source_health_companions()") == 2, (
            "expected exactly the definition + ONE call site; "
            f"found {src.count('_emit_source_health_companions()')} occurrences"
        )
