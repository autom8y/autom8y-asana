"""ITEM-A core tests -- unified in-process singleton advisory limiter.

Covers the flagship reconciliation item: process-singleton identity, the static
C-11-decoupled published floor, advisory overage telemetry (never blocks), the
``ASANA_BUDGET_ALLOCATOR_ENABLED`` knob (default INERT), and ``from_env``
precedence.

TL-A BUILD-GATE (ITEM-A): with the limiter constructed as a process singleton
and ENABLED=true in test, two lanes observe ONE instance (id equal); the 110/60s
floor reads from config with ZERO calls into C-11 instrumentation. If the limiter
is per-lane, or the floor-read triggers dynamic instrumentation, the design
premise is falsified -- HALT.
"""

from __future__ import annotations

from typing import Any

import pytest

from autom8_asana.config import BudgetAllocatorConfig
from autom8_asana.transport import budget_allocator as ba_module
from autom8_asana.transport.budget_allocator import (
    BudgetAllocator,
    Lane,
    PublishedFloor,
    get_budget_allocator,
    reset_budget_allocator,
    set_budget_allocator,
)


class _RecordingLog:
    """Minimal LoggerProtocol recorder capturing (event, extra) tuples."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, Any]]] = []

    def _rec(self, level: str, event: str, extra: dict[str, Any] | None = None) -> None:
        self.events.append((level, event, extra or {}))

    def debug(self, event: str, extra: dict[str, Any] | None = None, **_: Any) -> None:
        self._rec("debug", event, extra)

    def info(self, event: str, extra: dict[str, Any] | None = None, **_: Any) -> None:
        self._rec("info", event, extra)

    def warning(self, event: str, extra: dict[str, Any] | None = None, **_: Any) -> None:
        self._rec("warning", event, extra)

    def error(self, event: str, extra: dict[str, Any] | None = None, **_: Any) -> None:
        self._rec("error", event, extra)

    def events_named(self, name: str) -> list[dict[str, Any]]:
        return [extra for _lvl, ev, extra in self.events if ev == name]


@pytest.fixture(autouse=True)
def _clean_allocator_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no ambient ASANA_BUDGET_ALLOCATOR_* leaks into these tests."""
    for key in list(__import__("os").environ):
        if key.startswith("ASANA_BUDGET_ALLOCATOR_"):
            monkeypatch.delenv(key, raising=False)
    reset_budget_allocator()


def _armed(**overrides: Any) -> BudgetAllocator:
    cfg = BudgetAllocatorConfig(enabled=True, **overrides)
    return BudgetAllocator(cfg, log_provider=_RecordingLog())


# --------------------------------------------------------------------------
# AC-1: single process-singleton limiter (identity-stable across lanes)
# --------------------------------------------------------------------------


def test_singleton_identity_stable_across_lanes() -> None:
    """TL-A: two 'lanes' consulting the allocator observe ONE instance."""
    lane_a = get_budget_allocator()
    lane_b = get_budget_allocator()
    assert lane_a is lane_b
    assert id(lane_a) == id(lane_b)


def test_singleton_is_not_per_lane_instance() -> None:
    """Falsification guard: the limiter must NOT be per-lane (per-construction)."""
    first = get_budget_allocator()
    # Simulate many "lanes" each grabbing the allocator; all must be identical.
    ids = {id(get_budget_allocator()) for _ in range(25)}
    assert ids == {id(first)}


def test_set_and_reset_singleton() -> None:
    """Explicit injection (canary fixtures) and reset both work."""
    injected = _armed()
    set_budget_allocator(injected)
    assert get_budget_allocator() is injected
    reset_budget_allocator()
    assert get_budget_allocator() is not injected


# --------------------------------------------------------------------------
# AC-2: static floor = 110/60s from config, C-11-DECOUPLED
# --------------------------------------------------------------------------


def test_published_floor_default_110_over_60() -> None:
    cfg = BudgetAllocatorConfig()  # defaults
    alloc = BudgetAllocator(cfg, log_provider=_RecordingLog())
    floor = alloc.published_floor()
    assert isinstance(floor, PublishedFloor)
    assert floor.max_requests == 110
    assert floor.window_seconds == 60
    assert floor.rate_per_second == pytest.approx(110 / 60)


def test_published_floor_is_c11_decoupled_no_aimd_import() -> None:
    """TL-A: floor-read must NOT touch C-11 dynamic instrumentation (AIMD).

    Two-sided proof: (a) the allocator module does not IMPORT the AIMD semaphore
    at runtime (import-graph check -- robust against docstring prose); (b)
    ``published_floor`` reaches the value even if the AIMD module is made to
    explode on any attribute access -- proving the read never routes through it.
    """
    # (a) import-graph: the module namespace must not bind the AIMD symbols.
    assert not hasattr(ba_module, "AsyncAdaptiveSemaphore")
    assert not hasattr(ba_module, "adaptive_semaphore")
    assert not hasattr(ba_module, "Slot")

    # (b) behavioral: poison the AIMD module; the floor read must still succeed.
    class _Exploding:
        def __getattr__(self, name: str) -> Any:
            raise AssertionError(f"C-11 instrumentation touched during floor read: {name}")

    import sys

    saved = sys.modules.get("autom8_asana.transport.adaptive_semaphore")
    sys.modules["autom8_asana.transport.adaptive_semaphore"] = _Exploding()  # type: ignore[assignment]
    try:
        floor = _armed().published_floor()
        assert floor.max_requests == 110
    finally:
        if saved is not None:
            sys.modules["autom8_asana.transport.adaptive_semaphore"] = saved
        else:  # pragma: no cover - defensive
            del sys.modules["autom8_asana.transport.adaptive_semaphore"]


def test_floor_is_env_tunable_without_code_change() -> None:
    """killswitch-rollback-spec §2.7: floor VALUE re-tunable via config/env."""
    alloc = _armed(floor_max_requests=220, floor_window_seconds=60)
    assert alloc.published_floor().max_requests == 220


# --------------------------------------------------------------------------
# AC-3/4: knob default false => no-op passthrough; explicit true => active
# --------------------------------------------------------------------------


def test_default_is_inert() -> None:
    alloc = BudgetAllocator(BudgetAllocatorConfig(), log_provider=_RecordingLog())
    assert alloc.enabled is False


def test_explicit_true_is_active() -> None:
    assert _armed().enabled is True


def test_allocator_boot_log_emitted_with_state() -> None:
    log = _RecordingLog()
    BudgetAllocator(BudgetAllocatorConfig(enabled=False), log_provider=log)
    boots = log.events_named("allocator_boot")
    assert len(boots) == 1
    assert boots[0]["state"] == "inert"
    assert boots[0]["enabled"] is False

    log2 = _RecordingLog()
    BudgetAllocator(BudgetAllocatorConfig(enabled=True), log_provider=log2)
    assert log2.events_named("allocator_boot")[0]["state"] == "active"


# --------------------------------------------------------------------------
# ITEM-A AC3: advisory semantics -- overage TELEMETERED, never hard-blocked
# --------------------------------------------------------------------------


def test_observe_admission_is_advisory_never_blocks() -> None:
    """Advisory: observe_admission returns None and never raises, even at cap."""
    alloc = _armed(fair_share_max_requests=5)
    for _ in range(100):
        assert alloc.observe_admission(Lane.FAIR_SHARE) is None


def test_fair_share_overage_emits_budget_floor_overage() -> None:
    log = _RecordingLog()
    alloc = BudgetAllocator(
        BudgetAllocatorConfig(enabled=True, fair_share_max_requests=3),
        log_provider=log,
    )
    # 3 within cap -> silent; 4th and 5th -> overage telemetered.
    for _ in range(5):
        alloc.observe_admission(Lane.FAIR_SHARE)
    overages = log.events_named("budget_floor_overage")
    assert overages, "expected budget_floor_overage once the cap is exceeded"
    last = overages[-1]
    assert last["lane"] == "fair_share"
    assert last["admitted"] == 5
    assert last["cap"] == 3
    assert last["overage"] == 2


def test_warmer_lane_is_not_overage_telemetered() -> None:
    """PC-4 warmer-insulation: the 110 reservation is not a fair-share overage."""
    log = _RecordingLog()
    alloc = BudgetAllocator(
        BudgetAllocatorConfig(enabled=True, fair_share_max_requests=1),
        log_provider=log,
    )
    for _ in range(50):
        alloc.observe_admission(Lane.WARMER)
    assert log.events_named("budget_floor_overage") == []


def test_inert_allocator_emits_no_overage() -> None:
    """INERT: advisory observation is a no-op (byte-identical passthrough)."""
    log = _RecordingLog()
    alloc = BudgetAllocator(
        BudgetAllocatorConfig(enabled=False, fair_share_max_requests=1),
        log_provider=log,
    )
    for _ in range(50):
        alloc.observe_admission(Lane.FAIR_SHARE)
    assert log.events_named("budget_floor_overage") == []


# --------------------------------------------------------------------------
# from_env precedence
# --------------------------------------------------------------------------


def test_from_env_default_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASANA_BUDGET_ALLOCATOR_ENABLED", raising=False)
    cfg = BudgetAllocatorConfig.from_env()
    assert cfg.enabled is False
    assert cfg.floor_max_requests == 110
    assert cfg.floor_window_seconds == 60
    assert cfg.fair_share_max_requests == 1390


def test_from_env_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASANA_BUDGET_ALLOCATOR_ENABLED", "true")
    assert BudgetAllocatorConfig.from_env().enabled is True


def test_from_env_floor_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASANA_BUDGET_ALLOCATOR_FLOOR_MAX_REQUESTS", "220")
    assert BudgetAllocatorConfig.from_env().floor_max_requests == 220
