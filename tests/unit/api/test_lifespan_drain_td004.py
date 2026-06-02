"""TD-004 SIGTERM graceful-drain tests (thermia cache-architecture ADR-002).

Verifies the bounded drain that the FastAPI lifespan performs at shutdown
(after ``yield``, before client-pool teardown) over the fire-and-forget
background-build task set (``universal_strategy._background_tasks``):

1. The drain WAITS for in-flight builds, up to the configured timeout.
2. A task that completes within the window is awaited to completion.
3. The drain TIMES OUT gracefully if the window is exceeded (no hang; the
   still-pending tasks are left running, never awaited forever).
4. ADVERSARIAL / INVARIANT: a drain timeout greater than the ECS
   ``deregistration_delay`` would be unsafe (ECS SIGKILLs mid-drain). The
   25s default + the ADR-002 >=30s deregistration_delay (Q5 RESOLVED) keep
   the invariant satisfied; this is asserted as a guard so a future bump of
   the default that breaks the invariant fails loudly.

These tests exercise ``_drain_background_builds`` directly — the lifespan body
delegates to it — so the drain semantics are covered without standing up the
full startup path (Asana discovery / S3 / cache preload).

NO HTTP contract is touched: the drain runs only on shutdown.
"""

from __future__ import annotations

import asyncio

import pytest

from autom8_asana.api.lifespan import _drain_background_builds
from autom8_asana.settings import get_settings, reset_settings

# ECS SIGTERM->SIGKILL stop-timeout floor. ADR-002 Q5 RESOLVED: the TF task
# definition sets deregistration_delay default 300s (>= 30s). The drain default
# MUST stay at or below this so ECS does not SIGKILL the task mid-drain.
_ECS_DEREGISTRATION_DELAY_FLOOR_SECONDS = 30.0


@pytest.fixture(autouse=True)
def _reset_settings() -> None:
    reset_settings()
    yield
    reset_settings()


async def test_drain_awaits_task_completing_within_window() -> None:
    """A build that finishes inside the window is awaited to completion."""
    completed = asyncio.Event()

    async def quick_build() -> None:
        await asyncio.sleep(0.02)
        completed.set()

    task: asyncio.Task[None] = asyncio.create_task(quick_build())
    tasks = {task}

    await _drain_background_builds(tasks, drain_timeout=5.0)

    assert task.done(), "drain must wait for an in-flight build to finish"
    assert completed.is_set(), "the build body must have run to completion"
    assert not task.cancelled(), "drain must not cancel a draining build"


async def test_drain_times_out_gracefully_without_hanging() -> None:
    """A build longer than the window does NOT hang the drain.

    The drain returns at the timeout; the still-pending task is left running
    (NOT awaited forever, NOT cancelled by the drain itself). This is the
    "drain timeout exceeded" ADR-002 case — same orphaning as pre-TD-004,
    never worse.
    """

    async def slow_build() -> None:
        await asyncio.sleep(10.0)

    task: asyncio.Task[None] = asyncio.create_task(slow_build())
    tasks = {task}

    # Drain bounded well under the build duration; must return promptly.
    await asyncio.wait_for(
        _drain_background_builds(tasks, drain_timeout=0.05),
        timeout=2.0,  # outer guard: if the drain hangs, THIS fails the test
    )

    assert not task.done(), "drain should leave the over-window task running"
    # The drain itself must not cancel the task (orphaning is ECS's SIGKILL job).
    assert not task.cancelled()

    # Cleanup: cancel the lingering slow build so the loop closes cleanly.
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_drain_waits_for_multiple_inflight_builds() -> None:
    """The drain waits for the whole in-flight set, not just one task."""
    n = 4
    finished = 0

    async def build() -> None:
        nonlocal finished
        await asyncio.sleep(0.02)
        finished += 1

    tasks = {asyncio.create_task(build()) for _ in range(n)}

    await _drain_background_builds(tasks, drain_timeout=5.0)

    assert finished == n, "every in-flight build must be drained"
    assert all(t.done() for t in tasks)


async def test_drain_no_pending_tasks_is_noop() -> None:
    """Empty set / all-done tasks: drain returns immediately (no error)."""

    async def already() -> None:
        return None

    done_task: asyncio.Task[None] = asyncio.create_task(already())
    await done_task  # ensure it is done before draining

    # Empty set
    await asyncio.wait_for(_drain_background_builds(set(), 5.0), timeout=1.0)
    # All-done set: nothing to wait on
    await asyncio.wait_for(_drain_background_builds({done_task}, 5.0), timeout=1.0)


async def test_drain_zero_timeout_skips_drain() -> None:
    """A drain_timeout of 0 skips the drain (no-op), per the ADR-002 contract."""

    async def slow_build() -> None:
        await asyncio.sleep(10.0)

    task: asyncio.Task[None] = asyncio.create_task(slow_build())

    # timeout=0 must short-circuit BEFORE asyncio.wait, returning at once.
    await asyncio.wait_for(_drain_background_builds({task}, 0.0), timeout=1.0)
    assert not task.done()

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def test_default_drain_timeout_respects_ecs_deregistration_floor() -> None:
    """ADR-002 INVARIANT GUARD: default drain <= ECS deregistration_delay floor.

    A drain timeout GREATER than deregistration_delay would let ECS SIGKILL the
    task mid-drain (re-orphaning builds, defeating TD-004). The shipped default
    (25s) must stay at or below the ADR-002 >=30s deregistration_delay floor
    (Q5 RESOLVED). If a future change bumps the default past the floor without a
    matching TF deregistration_delay bump, THIS test fails loudly.
    """
    default = get_settings().runtime.build_drain_timeout_seconds
    assert default <= _ECS_DEREGISTRATION_DELAY_FLOOR_SECONDS, (
        f"build_drain_timeout_seconds default ({default}s) exceeds the ECS "
        f"deregistration_delay floor ({_ECS_DEREGISTRATION_DELAY_FLOOR_SECONDS}s); "
        "ECS would SIGKILL mid-drain (ADR-002 unsafe). Lower the default OR raise "
        "deregistration_delay in the autom8y TF task definition first."
    )
    assert default > 0, "default drain must be positive (drain actually runs)"


def test_drain_timeout_env_override() -> None:
    """BUILD_DRAIN_TIMEOUT_SECONDS env var overrides the default (ADR-002 name)."""
    import os

    os.environ["BUILD_DRAIN_TIMEOUT_SECONDS"] = "12.5"
    try:
        reset_settings()
        assert get_settings().runtime.build_drain_timeout_seconds == 12.5
    finally:
        del os.environ["BUILD_DRAIN_TIMEOUT_SECONDS"]
        reset_settings()
