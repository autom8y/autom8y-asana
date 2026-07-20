"""WS-A Finding-1: /ready must fail closed when the startup preload fails.

Two-sided discriminating-canary battery (Mode-2 genuine-gap production fix per
``discriminating-canary-doctrine``). The fleet points the ALB target-group
health check at ``/ready``; before this fix ``/ready`` was FAIL-OPEN because the
progressive preload set the cache ready in a ``finally`` block regardless of
outcome. A failed or aborted preload therefore masqueraded as ready and shifted
production traffic onto a silently-cold task (the liveness-masquerade).

Teeth (two-sided, bites only on the defect):

  Positive control  — preload runs to completion   -> READY    -> /ready 200.
  Negative control  — preload raises (broken input) -> FAILED   -> /ready 503,
                      honest cause PRELOAD_FAILED, and NEVER flips ready true.

The negative-control fixture is a deliberately-broken INPUT (an entity registry
whose ``is_ready()`` raises), which the FIXED surface correctly rejects. Against
the pre-fix fail-open code (``set_cache_ready(True)`` in the preload ``finally``)
the SAME fixture wrongly reports the pod ready -- that is the RED these tests
turn GREEN.

``/health`` (liveness) is deliberately untouched: a failed preload keeps the pod
alive so the previous task keeps serving under the target-group gate and
operators see the true state (liveness/readiness split).
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Reuse the proven completion patch stack from the sibling phase-exception suite
# so the positive control drives the *real* preload to completion, not a stub.
from tests.unit.api.preload.test_preload_phase_exception_logging import (
    _build_patch_stack,
    _make_entity_registry,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_preload_state():
    """Isolate module-global preload state across tests.

    Restores the serviceable READY state after each test so a lingering FAILED
    state from a teeth test cannot leak into unrelated suites sharing the
    module-scoped health module.
    """
    from autom8_asana.api.routes.health import set_cache_ready

    set_cache_ready(True)
    yield
    set_cache_ready(True)


def _broken_registry(exc: BaseException) -> MagicMock:
    """Entity registry whose ``is_ready()`` raises -- the broken INPUT fixture.

    ``is_ready()`` is the first external call in the preload try body, so the
    raised exception escapes to the outer handler and exercises the fail-closed
    path without needing the full completion patch stack.
    """
    registry = MagicMock()
    registry.is_ready.side_effect = exc
    return registry


def _completion_app() -> MagicMock:
    app = MagicMock()
    app.state.entity_project_registry = _make_entity_registry()
    return app


async def _drive_completion(app: MagicMock) -> None:
    """Drive the real progressive preload to completion (positive control)."""
    from autom8_asana.api.preload.progressive import (
        _preload_dataframe_cache_progressive,
    )

    mock_persistence = MagicMock()
    mock_persistence.is_available = True
    mock_persistence.get_manifest_async = AsyncMock(return_value=None)
    mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
    mock_persistence.__aexit__ = AsyncMock(return_value=None)

    mock_df_storage = MagicMock()
    mock_df_storage.load_dataframe = AsyncMock(return_value=(None, None))

    async def fake_gather(*coros, return_exceptions=False):
        # Clean input: every project processed successfully.
        for c in coros:
            c.close()
        return [True]

    with _build_patch_stack(mock_persistence, mock_df_storage):
        with patch("asyncio.gather", side_effect=fake_gather):
            await _preload_dataframe_cache_progressive(app)


# ---------------------------------------------------------------------------
# Layer 1 — the preload function's state outcome (drive the surface directly)
# ---------------------------------------------------------------------------


class TestPreloadStateOutcome:
    """The preload must set an HONEST three-way outcome, not blanket-ready."""

    async def test_completed_preload_marks_ready(self) -> None:
        """Positive control (requirement a): completion -> READY, serviceable."""
        from autom8_asana.api.routes.health import (
            PreloadState,
            get_preload_state,
            is_cache_ready,
        )

        await _drive_completion(_completion_app())

        assert get_preload_state() is PreloadState.READY
        assert is_cache_ready() is True

    async def test_failed_preload_marks_failed_not_ready(self) -> None:
        """THE TEETH (requirement b): a raising preload -> FAILED, NOT ready.

        RED against the pre-fix fail-open code: the ``finally`` block set the
        cache ready even on exception, so ``is_cache_ready()`` returned True and
        the state was ``ready``. GREEN with the fix: the outer handler marks
        FAILED and never flips ready true.
        """
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )
        from autom8_asana.api.routes.health import (
            PreloadState,
            get_preload_detail,
            get_preload_state,
            is_cache_ready,
        )

        app = MagicMock()
        app.state.entity_project_registry = _broken_registry(
            RuntimeError("simulated preload failure")
        )

        # The generic Exception is swallowed (pod stays alive), NOT re-raised.
        await _preload_dataframe_cache_progressive(app)

        assert get_preload_state() is PreloadState.FAILED
        assert is_cache_ready() is False
        assert get_preload_detail() == "preload_exception_RuntimeError"

    async def test_aborted_preload_marks_failed_and_reraises(self) -> None:
        """SIGTERM/abort (requirement c): CancelledError -> FAILED and re-raised.

        RED against the pre-fix code: CancelledError propagated but the
        ``finally`` still set the cache ready. GREEN: fail closed AND honor
        cooperative cancellation by re-raising.
        """
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )
        from autom8_asana.api.routes.health import (
            PreloadState,
            get_preload_state,
            is_cache_ready,
        )

        app = MagicMock()
        app.state.entity_project_registry = _broken_registry(asyncio.CancelledError())

        with pytest.raises(asyncio.CancelledError):
            await _preload_dataframe_cache_progressive(app)

        assert get_preload_state() is PreloadState.FAILED
        assert is_cache_ready() is False

    async def test_warmup_ordering_violation_marks_failed_and_reraises(self) -> None:
        """SCAR-005/006 preserved AND fail-closed: WarmupOrderingError re-raises.

        The safety-critical re-raise (never caught by BROAD-CATCH) is preserved;
        the fix additionally marks FAILED so the invariant violation cannot
        masquerade as ready.
        """
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )
        from autom8_asana.api.routes.health import (
            PreloadState,
            get_preload_state,
            is_cache_ready,
        )
        from autom8_asana.dataframes.cascade_utils import WarmupOrderingError

        app = MagicMock()
        app.state.entity_project_registry = _broken_registry(
            WarmupOrderingError("cascade ordering violated")
        )

        with pytest.raises(WarmupOrderingError):
            await _preload_dataframe_cache_progressive(app)

        assert get_preload_state() is PreloadState.FAILED
        assert is_cache_ready() is False

    async def test_deliberate_degrade_is_serviceable(self) -> None:
        """Deliberate degrade preserved: no bot PAT -> DEGRADED, still serviceable.

        Confirms the fix does NOT over-reach: a documented degrade-but-serviceable
        path (cache builds on request) stays serviceable rather than being
        wrongly marked FAILED.
        """
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )
        from autom8_asana.api.routes.health import (
            PreloadState,
            get_preload_state,
            is_cache_ready,
        )
        from autom8_asana.auth.bot_pat import BotPATError

        registry = _make_entity_registry()
        app = MagicMock()
        app.state.entity_project_registry = registry

        with patch(
            "autom8_asana.auth.bot_pat.get_bot_pat",
            side_effect=BotPATError("no PAT"),
        ):
            await _preload_dataframe_cache_progressive(app)

        assert get_preload_state() is PreloadState.DEGRADED
        assert is_cache_ready() is True


# ---------------------------------------------------------------------------
# Layer 2 — the /ready endpoint renders the outcome into the ALB gate
# ---------------------------------------------------------------------------


class TestReadyEndpointFailClosed:
    """/ready must gate the target group truthfully on the three-way outcome."""

    def test_ready_503_with_honest_cause_when_failed(self, client: TestClient) -> None:
        """THE TEETH at the HTTP surface: FAILED -> 503 + cause PRELOAD_FAILED.

        RED against the pre-fix code: a failed preload set the cache ready, so
        /ready returned 200 and the ALB shifted traffic to a cold task.
        """
        from autom8_asana.api.routes.health import set_cache_failed

        set_cache_failed("preload_exception_RuntimeError")
        response = client.get("/ready")

        assert response.status_code == 503
        cache_check = response.json()["checks"]["cache"]
        assert cache_check["status"] == "unavailable"
        assert cache_check["detail"]["cause"] == "PRELOAD_FAILED"
        assert cache_check["detail"]["reason"] == "preload_exception_RuntimeError"

    def test_ready_200_when_completed(self, client: TestClient) -> None:
        """Positive control at the HTTP surface: READY -> 200."""
        from autom8_asana.api.routes.health import set_cache_ready

        set_cache_ready(True)
        response = client.get("/ready")

        assert response.status_code == 200
        assert response.json()["checks"]["cache"]["status"] == "ok"

    def test_ready_200_with_degraded_signal_when_degraded(self, client: TestClient) -> None:
        """Deliberate degrade -> 200 WITH a surfaced degraded signal (not silent)."""
        from autom8_asana.api.routes.health import set_cache_degraded

        set_cache_degraded("bot_pat_unavailable")
        response = client.get("/ready")

        assert response.status_code == 200
        cache_check = response.json()["checks"]["cache"]
        assert cache_check["status"] == "degraded"
        assert cache_check["detail"]["cause"] == "PRELOAD_DEGRADED"
        assert cache_check["detail"]["reason"] == "bot_pat_unavailable"

    def test_failed_cause_is_distinct_from_warming(self, client: TestClient) -> None:
        """Honest cause: a FAILED preload is distinguishable from warming.

        Both are 503, but the cause must differ so operators can tell a broken
        preload (PRELOAD_FAILED) from a still-warming one (CACHE_BUILD_IN_PROGRESS).
        """
        from autom8_asana.api.routes.health import set_cache_failed, set_cache_ready

        set_cache_failed("preload_exception_ValueError")
        failed = client.get("/ready").json()["checks"]["cache"]
        assert failed["detail"]["cause"] == "PRELOAD_FAILED"

        set_cache_ready(False)  # reset to warming
        warming = client.get("/ready").json()["checks"]["cache"]
        assert warming["detail"]["cause"] == "CACHE_BUILD_IN_PROGRESS"

        assert failed["detail"]["cause"] != warming["detail"]["cause"]

    def test_health_stays_200_when_preload_failed(self, client: TestClient) -> None:
        """Requirement (d): liveness/readiness split — /health untouched.

        A FAILED preload gates /ready to 503 but /health stays 200 so the pod
        stays alive and the previous task keeps serving under the TG gate.
        """
        from autom8_asana.api.routes.health import set_cache_failed

        set_cache_failed("preload_exception_RuntimeError")

        assert client.get("/ready").status_code == 503
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
