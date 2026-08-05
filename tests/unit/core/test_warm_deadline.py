"""Unit tests for the F1a process-scoped warm deadline primitive.

The deadline lets a deep 429-retry loop yield before the 900 s Lambda wall so the
warm orchestration can checkpoint + self-invoke instead of SIGKILL-stranding the sweep.
These tests pin the primitive's arm/reach/disarm semantics and the INERT-when-disarmed
byte-identity contract.
"""

from __future__ import annotations

import pytest

from autom8_asana.core import warm_deadline
from autom8_asana.core.warm_deadline import (
    DEADLINE_BUFFER_MS,
    WarmDeadlineExceeded,
    arm_warm_deadline,
    disarm_warm_deadline,
    raise_if_warm_deadline_reached,
    warm_deadline_armed,
    warm_deadline_reached,
)
from autom8_asana.lambda_handlers.timeout import TIMEOUT_BUFFER_MS


class _FakeContext:
    """Minimal Lambda context exposing only get_remaining_time_in_millis()."""

    def __init__(self, remaining_ms: int) -> None:
        self._remaining_ms = remaining_ms

    def get_remaining_time_in_millis(self) -> int:
        return self._remaining_ms


@pytest.fixture(autouse=True)
def _disarm_between_tests():
    disarm_warm_deadline()
    yield
    disarm_warm_deadline()


def test_disarmed_is_inert_default():
    """The default (no arm) is disarmed => reached() is False => INERT passthrough."""
    assert warm_deadline_armed() is False
    assert warm_deadline_reached() is False
    # raise_if... must be a no-op when disarmed (the ECS/API/every-non-warmer state).
    raise_if_warm_deadline_reached()


def test_arm_with_ample_time_not_reached():
    """A context with ample remaining time arms a future deadline that is NOT reached."""
    armed = arm_warm_deadline(_FakeContext(remaining_ms=600_000))
    assert armed is True
    assert warm_deadline_armed() is True
    assert warm_deadline_reached() is False
    raise_if_warm_deadline_reached()  # must not raise


def test_arm_inside_buffer_is_immediately_reached():
    """remaining_ms <= buffer arms a deadline of 'now' => reached immediately."""
    arm_warm_deadline(_FakeContext(remaining_ms=0))
    assert warm_deadline_armed() is True
    assert warm_deadline_reached() is True
    with pytest.raises(WarmDeadlineExceeded):
        raise_if_warm_deadline_reached()


def test_arm_exactly_at_buffer_boundary_reached():
    """remaining_ms == buffer => zero slack => reached (mirrors _should_exit_early '<')."""
    arm_warm_deadline(_FakeContext(remaining_ms=DEADLINE_BUFFER_MS))
    assert warm_deadline_reached() is True


def test_none_context_disarms():
    """A None context never arms (and disarms any prior arm) -- broken input never harms."""
    arm_warm_deadline(_FakeContext(remaining_ms=600_000))
    assert warm_deadline_armed() is True
    armed = arm_warm_deadline(None)
    assert armed is False
    assert warm_deadline_armed() is False


def test_context_without_getter_disarms():
    """A context lacking get_remaining_time_in_millis disarms rather than raising."""

    class _Bare:
        pass

    assert arm_warm_deadline(_Bare()) is False
    assert warm_deadline_armed() is False


def test_broken_getter_disarms_never_raises():
    """A getter that raises must disarm defensively, never propagate into the warm."""

    class _Broken:
        def get_remaining_time_in_millis(self):
            raise RuntimeError("context is broken")

    assert arm_warm_deadline(_Broken()) is False
    assert warm_deadline_armed() is False


def test_env_killswitch_disables_arming(monkeypatch):
    """ASANA_WARMER_DEADLINE_YIELD_ENABLED=false disarms (env-only instant revert)."""
    monkeypatch.setenv("ASANA_WARMER_DEADLINE_YIELD_ENABLED", "false")
    armed = arm_warm_deadline(_FakeContext(remaining_ms=0))
    assert armed is False
    assert warm_deadline_armed() is False
    assert warm_deadline_reached() is False


def test_env_killswitch_default_enabled(monkeypatch):
    """Absent env var => enabled (the deployed default arms)."""
    monkeypatch.delenv("ASANA_WARMER_DEADLINE_YIELD_ENABLED", raising=False)
    assert arm_warm_deadline(_FakeContext(remaining_ms=0)) is True


def test_warm_deadline_exceeded_is_baseexception_not_exception():
    """Control-flow contract: BaseException so broad `except Exception` cannot swallow it."""
    assert issubclass(WarmDeadlineExceeded, BaseException)
    assert not issubclass(WarmDeadlineExceeded, Exception)


def test_buffer_matches_should_exit_early_buffer():
    """Drift guard: the retry-loop yield fires at the SAME instant as the per-item check."""
    assert DEADLINE_BUFFER_MS == TIMEOUT_BUFFER_MS
    assert warm_deadline.DEADLINE_BUFFER_MS == 120_000
