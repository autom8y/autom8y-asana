"""Wall-clock anchor for the SD-02 account-status push loop (W1-H1 cure).

THE DEFECT (measured, not assumed -- W1-B re-diagnosis + its rite-disjoint
critic, 2026-09-11): ``AccountStatusPushLoop._run`` slept the whole interval
FIRST, so the loop's fire phase was anchored to process BOOT. The downstream
consumer (``account-status-recon``) reads the offer frame on a FIXED wall-clock
grid -- ``cron(0 */4 * * ? *)``, measured read instant HH:00:46.1 UTC (band
45.4-49.5 s, n=35) -- and suppresses its verdict surface when the frame's
``verification_age_seconds`` exceeds 7200 s (warn at 3600 s). Two unrelated
phases at the same period means ~half of all boots parked this loop's stamp
outside the consumer's window, and the verdict surface stayed dark until the
next restart re-rolled the phase.

THE CURE UNDER TEST: fires are recomputed from the wall clock every cycle onto
the epoch grid ``k * interval - lead`` with ``lead = 1800 s``, so at the
ratified cadence every fire lands on HH:30:00 UTC.

THE STAMP PATH THIS RELIES ON (named so a refactor cannot delete it silently):
the push's per-entity ``cache.get_async`` -> TTL-expired entry -> SWR rebuild ->
``_probe_freshness`` writes ``last_verified_at``. ``TestCouplingRegression``
below is the guard.

DECLARED PREMISES of the age arithmetic (inputs, not findings of this file):

* ``_DELTA_*`` -- push -> stamp latency, n=30, min 25.2 / p50 34.3 / p95 45.7 /
  max 78.2 s (critic's re-derivation; the tail beyond 78 s is UNMEASURED and is
  exactly what the 1800 s lead is spent on).
* ``_READ_OFFSET_*`` -- consumer read instant within its grid hour, n=35.
* ``_ABORT_SECONDS`` / ``_WARN_SECONDS`` -- the consumer's gate, observed on the
  wire as ``threshold_seconds=3600`` with abort at 2x.
* **Whole-scope stamping.** The served figure is ``min(last_verified_at)`` folded
  over the request's classification section set -- NOT simply the most recent
  stamp. The arithmetic here assumes the anchored rebuild verifies the whole
  scope in one pass, which is how all 34 joined ticks behaved but is not
  guaranteed by code: one section that fails its probe leaves an OLDER stamp
  governing and pushes the true age ABOVE what these tests predict. That is a
  property of the builder, not of the anchor, and it is named here so the
  prediction is not read as unconditional.
"""

from __future__ import annotations

import asyncio
import contextlib
import math
import os
import random
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

from autom8_asana.api.status_push import (
    DEFAULT_STATUS_PUSH_INTERVAL_SECONDS,
    AccountStatusPushLoop,
    push_account_status_snapshot,
    seconds_until_next_fire,
)

_STATUS_PUSH_MODULE = "autom8_asana.api.status_push"

# --- measured inputs (see module docstring for provenance) ------------------
_INTERVAL = 14400.0
_LEAD = 1800.0
_READ_OFFSET_EARLY = 45.4
_READ_OFFSET_LATE = 49.5
_DELTA_MIN = 25.2
_DELTA_MAX = 78.2
_ABORT_SECONDS = 7200.0
_WARN_SECONDS = 3600.0

#: Grid tolerance. Epoch seconds near 1.8e9 carry ~5e-7 s of float64 resolution,
#: so "on the grid" is asserted to the millisecond, not to the bit.
_GRID_TOLERANCE_SECONDS = 1e-3

#: A boot instant with an unround offset, so no sweep sample accidentally lands
#: on a grid point (which would flatter the pre-change behaviour).
_SWEEP_BASE_EPOCH = 1789084800.0 + 17.437  # 2026-09-11T00:00:00Z + 17.437 s


def _grid_offset(instant: float, *, interval: float = _INTERVAL, lead: float = _LEAD) -> float:
    """Signed distance from *instant* to the nearest ``k*interval - lead`` point."""
    phase = (-lead) % interval
    residual = (instant - phase) % interval
    return residual if residual <= interval / 2 else residual - interval


def _next_read_after(instant: float, *, offset: float) -> float:
    """First consumer read strictly after *instant* on its fixed wall-clock grid."""
    return (math.floor((instant - offset) / _INTERVAL) + 1) * _INTERVAL + offset


def _anchor_violations(fire_epoch: float) -> list[str]:
    """Legs of the cure's safety property that a fire at *fire_epoch* violates.

    Empty list == the property holds. Each leg is derived from the declared
    bounds in the module docstring, worst case in the direction that hurts:

    * ``grid``          -- the fire is not on the epoch grid.
    * ``stamp_after_read`` -- with the slowest measured push->stamp latency the
      stamp lands at or after the read it is supposed to serve (that read is
      then governed by a stamp one whole period older).
    * ``abort`` / ``warn`` -- with the latest read instant and the fastest stamp
      (the oldest age this fire can produce) the consumer's gate trips.
    """
    violations: list[str] = []
    if abs(_grid_offset(fire_epoch)) > _GRID_TOLERANCE_SECONDS:
        violations.append("grid")

    read_early = _next_read_after(fire_epoch, offset=_READ_OFFSET_EARLY)
    read_late = read_early - _READ_OFFSET_EARLY + _READ_OFFSET_LATE

    if fire_epoch + _DELTA_MAX >= read_early:
        violations.append("stamp_after_read")

    age_worst = read_late - (fire_epoch + _DELTA_MIN)
    if age_worst > _ABORT_SECONDS:
        violations.append("abort")
    if age_worst >= _WARN_SECONDS:
        violations.append("warn")
    return violations


def _boot_sweep() -> list[float]:
    """1440 boots at 60 s spacing across a full day + 500 randomized boots."""
    sweep = [_SWEEP_BASE_EPOCH + i * 60.0 for i in range(1440)]
    rng = random.Random(20260911)
    sweep += [_SWEEP_BASE_EPOCH + rng.uniform(0.0, 86400.0) for _ in range(500)]
    return sweep


def _env_without_interval(**overrides: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "STATUS_PUSH_INTERVAL_SECONDS"}
    env.update(overrides)
    return env


# ---------------------------------------------------------------------------
# Deterministic harness -- an injected clock and an injected sleep. No test in
# this file ever sleeps a real interval.
# ---------------------------------------------------------------------------


class _StopHarness(Exception):
    """Raised by the fake push to end a harness run at a fixed fire count."""


@dataclass
class _Run:
    fires: list[float] = field(default_factory=list)
    sleeps: list[float] = field(default_factory=list)
    started_log: dict[str, object] | None = None
    warnings: list[tuple[str, dict[str, object]]] = field(default_factory=list)
    task_started: bool = False


async def _drive(
    boot_epoch: float,
    *,
    interval: float | None = None,
    lead: float | None = None,
    push_duration: float = 0.0,
    max_fires: int = 5,
) -> _Run:
    """Run the real loop against a fake clock; return what it did."""
    run = _Run()
    now = [boot_epoch]

    async def fake_sleep(delay: float) -> None:
        run.sleeps.append(delay)
        now[0] += delay
        await asyncio.sleep(0)  # yield, so the task is genuinely a task

    async def fake_push(trigger: str) -> None:
        assert trigger == "interval"
        run.fires.append(now[0])
        now[0] += push_duration
        if len(run.fires) >= max_fires:
            raise _StopHarness

    loop = AccountStatusPushLoop(
        interval_seconds=interval,
        lead_seconds=lead,
        clock=lambda: now[0],
        sleep=fake_sleep,
    )
    with (
        patch(f"{_STATUS_PUSH_MODULE}.push_account_status_snapshot", new=fake_push),
        patch(f"{_STATUS_PUSH_MODULE}.logger") as mock_logger,
    ):
        task = loop.start()
        if task is not None:
            run.task_started = True
            with contextlib.suppress(_StopHarness):
                await task
            await loop.stop()
        for call in mock_logger.info.call_args_list:
            if call.args[0] == "status_push_loop_started":
                run.started_log = call.kwargs["extra"]
        run.warnings = [
            (c.args[0], c.kwargs.get("extra", {})) for c in mock_logger.warning.call_args_list
        ]
    return run


# ---------------------------------------------------------------------------
# TEST 1 -- arbitrary-boot property
# ---------------------------------------------------------------------------


class TestArbitraryBootProperty:
    """Whatever instant the process boots at, the fire lands on the grid."""

    def test_first_fire_satisfies_the_safety_property_for_every_boot_instant(self) -> None:
        with patch.dict(os.environ, _env_without_interval(), clear=True):
            loop = AccountStatusPushLoop()
        assert loop._interval == DEFAULT_STATUS_PUSH_INTERVAL_SECONDS == _INTERVAL
        assert loop._lead == _LEAD

        failures: list[tuple[float, list[str]]] = []
        ages: list[float] = []
        for boot in _boot_sweep():
            fire = boot + seconds_until_next_fire(boot, loop._interval, loop._lead)
            violations = _anchor_violations(fire)
            if violations:
                failures.append((boot, violations))
            read_early = _next_read_after(fire, offset=_READ_OFFSET_EARLY)
            read_late = read_early - _READ_OFFSET_EARLY + _READ_OFFSET_LATE
            ages.append(read_late - (fire + _DELTA_MIN))
            ages.append(read_early - (fire + _DELTA_MAX))

        assert not failures, f"{len(failures)} boot instants violated the property: {failures[:3]}"
        # The sharpest falsifiable statement the cure makes: the governing age
        # at every read is pinned to a ~57 s band, four times below the warn
        # edge and eight times below the abort edge.
        assert abs(min(ages) - (_READ_OFFSET_EARLY + _LEAD - _DELTA_MAX)) < _GRID_TOLERANCE_SECONDS
        assert abs(max(ages) - (_READ_OFFSET_LATE + _LEAD - _DELTA_MIN)) < _GRID_TOLERANCE_SECONDS
        assert max(ages) < _WARN_SECONDS
        print(
            f"\n[anchor] predicted governing age at every read: "
            f"{min(ages):.1f}..{max(ages):.1f} s (warn {_WARN_SECONDS:.0f}, abort {_ABORT_SECONDS:.0f})"
        )

    async def test_the_running_loop_fires_on_the_grid_from_an_arbitrary_boot(self) -> None:
        """Same property, asserted against the real `_run`, not just the helper."""
        for boot in (_SWEEP_BASE_EPOCH, _SWEEP_BASE_EPOCH + 6199.13, _SWEEP_BASE_EPOCH + 13777.9):
            with patch.dict(os.environ, _env_without_interval(), clear=True):
                run = await _drive(boot, max_fires=3)
            assert run.fires, "expected the loop to fire"
            for fire in run.fires:
                assert not _anchor_violations(fire), fire
            assert run.fires[0] > boot, "sleep-first is preserved: no fire at t0"


# ---------------------------------------------------------------------------
# TEST 2 -- TEETH. The same property, deliberately wrong inputs.
# ---------------------------------------------------------------------------


class TestTeeth:
    """The property must REJECT the pre-change anchor and a zero lead.

    Neither leg injects a defect into production code: each feeds a
    deliberately-wrong INPUT (the old boot-anchored fire instant; lead=0) to the
    same assertion that Test 1 passes.
    """

    def test_boot_anchored_fire_fails_the_property_for_about_half_of_boots(self) -> None:
        sweep = _boot_sweep()
        # The pre-change behaviour, modelled exactly: sleep the interval first,
        # so the first fire is one whole period after boot.
        old_fires = [boot + _INTERVAL for boot in sweep]

        legs = {"grid": 0, "stamp_after_read": 0, "abort": 0, "warn": 0}
        any_violation = 0
        for fire in old_fires:
            violations = _anchor_violations(fire)
            if violations:
                any_violation += 1
            for leg in violations:
                legs[leg] += 1

        n = len(sweep)
        print(
            f"\n[teeth] boot-anchored (pre-change) over n={n} boots: "
            f"any={any_violation / n:.3f} grid={legs['grid'] / n:.3f} "
            f"abort={legs['abort'] / n:.3f} warn={legs['warn'] / n:.3f} "
            f"stamp_after_read={legs['stamp_after_read'] / n:.3f}"
        )

        # The headline tooth: the consumer's ABORT gate trips for ~half of all
        # boot phases. That is the measured shape of the live defect.
        assert 0.40 <= legs["abort"] / n <= 0.60, legs
        # And the grid leg rejects essentially every boot-anchored fire.
        assert legs["grid"] / n > 0.99, legs
        # Two-sided: the SAME assertion passes for every anchored fire.
        assert all(
            not _anchor_violations(boot + seconds_until_next_fire(boot, _INTERVAL, _LEAD))
            for boot in sweep
        )

    def test_zero_lead_fails_the_stamp_lands_before_the_read_leg(self) -> None:
        sweep = _boot_sweep()
        failures = 0
        for boot in sweep:
            fire = boot + seconds_until_next_fire(boot, _INTERVAL, 0.0)
            violations = _anchor_violations(fire)
            if violations:
                failures += 1
                assert "stamp_after_read" in violations, violations
        print(f"\n[teeth] lead=0 over n={len(sweep)} boots: any={failures / len(sweep):.3f}")
        assert failures == len(sweep), "lead=0 must fail for EVERY boot instant"

    async def test_the_running_loop_with_zero_lead_is_rejected_too(self) -> None:
        """The tooth bites on `_run` as well, not only on the helper."""
        run = await _drive(_SWEEP_BASE_EPOCH + 4321.7, interval=_INTERVAL, lead=0.0, max_fires=2)
        assert run.fires
        assert all(_anchor_violations(fire) for fire in run.fires)


# ---------------------------------------------------------------------------
# TEST 3 -- env override: period preserved, guarantee voided loudly
# ---------------------------------------------------------------------------


class TestEnvOverride:
    async def test_override_preserves_the_period_exactly(self) -> None:
        with patch.dict(os.environ, _env_without_interval(STATUS_PUSH_INTERVAL_SECONDS="600")):
            run = await _drive(_SWEEP_BASE_EPOCH + 91.3, max_fires=5)

        assert len(run.fires) == 5
        gaps = [b - a for a, b in zip(run.fires, run.fires[1:])]
        assert all(abs(gap - 600.0) < _GRID_TOLERANCE_SECONDS for gap in gaps), gaps
        assert all(
            abs(_grid_offset(f, interval=600.0)) < _GRID_TOLERANCE_SECONDS for f in run.fires
        )

    async def test_override_emits_the_guarantee_void_warning_exactly_once(self) -> None:
        with patch.dict(os.environ, _env_without_interval(STATUS_PUSH_INTERVAL_SECONDS="600")):
            run = await _drive(_SWEEP_BASE_EPOCH + 91.3, max_fires=2)

        void = [
            extra
            for event, extra in run.warnings
            if event == "status_push_loop_anchor_guarantee_void"
        ]
        assert len(void) == 1, run.warnings
        assert void[0]["interval_seconds"] == 600.0
        assert void[0]["lead_seconds"] == _LEAD

    async def test_ratified_cadence_emits_no_guarantee_void_warning(self) -> None:
        """Two-sided: the loud line is absent on the cadence it was sized for."""
        with patch.dict(os.environ, _env_without_interval(), clear=True):
            run = await _drive(_SWEEP_BASE_EPOCH + 91.3, max_fires=2)

        assert [e for e, _ in run.warnings if e == "status_push_loop_anchor_guarantee_void"] == []

    def test_nonpositive_interval_still_disables_the_loop(self) -> None:
        assert AccountStatusPushLoop(interval_seconds=0).start() is None
        with patch.dict(os.environ, _env_without_interval(STATUS_PUSH_INTERVAL_SECONDS="-1")):
            assert AccountStatusPushLoop().start() is None

    def test_unparseable_interval_still_falls_back_to_the_ratified_default(self) -> None:
        with patch.dict(
            os.environ, _env_without_interval(STATUS_PUSH_INTERVAL_SECONDS="four-hours")
        ):
            loop = AccountStatusPushLoop()
        assert loop._interval == DEFAULT_STATUS_PUSH_INTERVAL_SECONDS == 14400.0

    async def test_start_log_self_attests_the_anchor(self) -> None:
        boot = _SWEEP_BASE_EPOCH + 3333.25
        with patch.dict(os.environ, _env_without_interval(), clear=True):
            run = await _drive(boot, max_fires=1)

        assert run.started_log is not None
        assert run.started_log["interval_seconds"] == _INTERVAL
        assert run.started_log["lead_seconds"] == _LEAD
        # The logged instant IS the instant the loop then fires at, to the second.
        assert run.started_log["next_fire_at"].endswith("Z")
        assert run.started_log["next_fire_at"] == "2026-09-11T03:30:00Z"
        assert abs(run.fires[0] - 1789097400.0) < _GRID_TOLERANCE_SECONDS  # 03:30:00Z


# ---------------------------------------------------------------------------
# TEST 4 -- no double fire, grid keeping under slow pushes
# ---------------------------------------------------------------------------


class TestNoDoubleFireAndGridKeeping:
    async def test_instant_push_fires_once_per_slot(self) -> None:
        run = await _drive(
            _SWEEP_BASE_EPOCH + 12.5, interval=_INTERVAL, push_duration=0.0, max_fires=6
        )
        gaps = [b - a for a, b in zip(run.fires, run.fires[1:])]
        assert len(run.fires) == len(set(run.fires)) == 6
        assert all(abs(gap - _INTERVAL) < _GRID_TOLERANCE_SECONDS for gap in gaps), gaps
        assert all(not _anchor_violations(f) for f in run.fires)

    async def test_slow_push_stays_on_the_grid(self) -> None:
        run = await _drive(
            _SWEEP_BASE_EPOCH + 12.5, interval=_INTERVAL, push_duration=235.0, max_fires=4
        )
        gaps = [b - a for a, b in zip(run.fires, run.fires[1:])]
        assert all(abs(gap - _INTERVAL) < _GRID_TOLERANCE_SECONDS for gap in gaps), gaps
        assert all(not _anchor_violations(f) for f in run.fires)

    async def test_overrun_longer_than_a_slot_skips_forward_instead_of_firing_twice(self) -> None:
        overrun = _INTERVAL + 137.0
        run = await _drive(
            _SWEEP_BASE_EPOCH + 12.5, interval=_INTERVAL, push_duration=overrun, max_fires=4
        )
        gaps = [b - a for a, b in zip(run.fires, run.fires[1:])]
        assert all(abs(_grid_offset(f)) < _GRID_TOLERANCE_SECONDS for f in run.fires), run.fires
        # Every gap is a whole number of slots, and strictly more than one slot:
        # the overrun SKIPS a slot, it never fires the slot it is still inside.
        for gap in gaps:
            slots = gap / _INTERVAL
            assert abs(slots - round(slots)) < 1e-6, gaps
            assert round(slots) == 2, gaps
        assert all(sleep > 0 for sleep in run.sleeps), run.sleeps

    async def test_a_push_that_returns_instantly_never_refires_the_same_slot(self) -> None:
        """The minimum-gap guard, asserted at the seam it exists for."""
        fire = _SWEEP_BASE_EPOCH - _grid_offset(_SWEEP_BASE_EPOCH)  # exactly a grid point
        delay = seconds_until_next_fire(fire, _INTERVAL, _LEAD)
        assert abs(delay - _INTERVAL) < _GRID_TOLERANCE_SECONDS, delay


# ---------------------------------------------------------------------------
# TEST 5 -- MANDATORY coupling regression
# ---------------------------------------------------------------------------


def _multi_entity_registry() -> MagicMock:
    """Registry with one pipeline-mapped entity and one unmapped one."""
    gids = {"unit": "1201081073731555", "offer": "1143843662099250"}
    registry = MagicMock()
    registry.is_ready.return_value = True
    registry.get_all_entity_types.return_value = ["unit", "offer"]
    registry.get_config.side_effect = lambda et: (
        MagicMock(project_gid=gids[et]) if et in gids else None
    )
    return registry, gids


def _cache_with_unit_rows() -> MagicMock:
    import polars as pl

    entry = MagicMock()
    entry.dataframe = pl.DataFrame(
        {
            "office_phone": ["+15551230001", "+15551230002"],
            "vertical": ["chiropractor", "chiropractor"],
            "section": ["Active", "Month 1"],
        }
    )
    cache = MagicMock()
    cache.get_async = AsyncMock(return_value=entry)
    return cache


class TestCouplingRegression:
    """The freshness axis rides on the push's reads, NOT on the push itself.

    ``STATUS_PUSH_ENABLED`` is checked downstream of the per-entity
    ``cache.get_async`` sweep (``services/gid_push.py`` ->
    ``push_status_to_data_service``), so the lever silences the outbound push and
    leaves the SWR-rebuild-and-stamp side effect intact. That is load-bearing and
    entirely incidental: this test names it so a refactor that "optimises" the
    disabled path cannot silently delete the only traffic-independent advancer of
    the offers verification axis.
    """

    async def _run_push(self, *, enabled: str) -> tuple[MagicMock, AsyncMock]:
        registry, _ = _multi_entity_registry()
        cache = _cache_with_unit_rows()
        env = {
            "AUTOM8Y_DATA_URL": "http://data.internal.test",
            "AUTOM8Y_DATA_API_KEY": "test-token-not-a-secret",
            "STATUS_PUSH_ENABLED": enabled,
        }
        with (
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=registry,
            ),
            patch("autom8_asana.cache.dataframe.factory.get_dataframe_cache", return_value=cache),
            patch(
                "autom8_asana.services.gid_push._push_to_data_service",
                new_callable=AsyncMock,
                return_value=True,
            ) as transport,
            patch("autom8_asana.services.gid_push.emit_metric"),
            patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric"),
            patch.dict(os.environ, env),
        ):
            await push_account_status_snapshot(trigger="interval")
        return cache, transport

    async def test_interval_push_reads_every_entity_even_when_push_disabled(self) -> None:
        cache, transport = await self._run_push(enabled="false")

        # The lever did its job: nothing went out on the wire.
        transport.assert_not_awaited()
        # ...and yet EVERY registry entity was still read. These reads are the
        # SWR trigger; deleting them deletes the offers verification axis.
        read = {call.args for call in cache.get_async.await_args_list}
        assert read == {("1201081073731555", "unit"), ("1143843662099250", "offer")}

    async def test_enabled_push_reads_the_same_entities_and_posts(self) -> None:
        """Two-sided control: with the lever ON, the reads AND the post happen."""
        cache, transport = await self._run_push(enabled="true")

        transport.assert_awaited_once()
        read = {call.args for call in cache.get_async.await_args_list}
        assert read == {("1201081073731555", "unit"), ("1143843662099250", "offer")}
