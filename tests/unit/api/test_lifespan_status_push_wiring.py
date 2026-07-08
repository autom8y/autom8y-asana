"""Lifespan wiring canary for the account-status push loop (sprint-C6, SD-02).

THE GAP THIS CLOSES (QA blocker, mutation M3): TestAccountStatusPushLoop covers
the loop class in isolation and TestPreloadTailFiresStatusPush covers the
one-shot, but NOTHING asserted that lifespan() actually constructs, starts, and
stops the loop. Deleting the entire wiring block from lifespan.py left every
test green -- the exact H1 dark-seam class this sprint exists to fix (machinery
present, wiring absent, nothing noticed). This matters doubly because the
interval loop is the ONLY firing point that survives the preload early-return
paths (no-bot-PAT / no-workspace-GID / no-S3-bucket / legacy-fallback all
return BEFORE the preload-tail one-shot).

These tests run the REAL lifespan context (startup + shutdown) with the heavy
startup collaborators mocked out, but the AccountStatusPushLoop deliberately
REAL -- so removing the wiring block (mutation M3) turns them RED:

1. After startup: ``app.state.status_push_loop`` exists, is a real
   AccountStatusPushLoop, and its background task is LIVE (created, named,
   not done) -- not merely constructed.
2. After shutdown: the task has been cancelled via stop() (awaited teardown).

Pattern precedent: tests/unit/api/test_lifespan_drain_td004.py (lifespan-level
contract tests); mocking altitude mirrors the seam tests in
tests/unit/api/test_status_push_seam.py.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from autom8_asana.api.lifespan import lifespan
from autom8_asana.api.status_push import AccountStatusPushLoop

if TYPE_CHECKING:
    from collections.abc import Iterator

_LIFESPAN = "autom8_asana.api.lifespan"


@pytest.fixture
def _mocked_startup_collaborators() -> Iterator[None]:
    """Neutralize every heavy/global-side-effect startup collaborator.

    Everything EXCEPT the AccountStatusPushLoop wiring is mocked: the loop
    itself must be the real class started by the real lifespan body, so that
    removing the wiring block (mutation M3) fails these tests.
    """
    with contextlib.ExitStack() as stack:
        # Deterministic loop config: enabled, ratified 4h cadence (sleeps
        # first, so nothing fires during the test).
        stack.enter_context(
            patch.dict(os.environ, {"STATUS_PUSH_INTERVAL_SECONDS": "14400"}),
        )

        # Module-level names bound in the lifespan namespace.
        stack.enter_context(patch(f"{_LIFESPAN}.configure_logging"))
        stack.enter_context(
            patch(
                f"{_LIFESPAN}.get_settings",
                return_value=SimpleNamespace(log_level="INFO", debug=False, rate_limit_rpm=150),
            )
        )
        stack.enter_context(
            patch(f"{_LIFESPAN}.ClientPool", return_value=MagicMock(close_all=AsyncMock()))
        )
        stack.enter_context(patch(f"{_LIFESPAN}._discover_entity_projects", new=AsyncMock()))
        stack.enter_context(patch(f"{_LIFESPAN}._initialize_dataframe_cache"))
        stack.enter_context(patch(f"{_LIFESPAN}._initialize_mutation_invalidator"))
        stack.enter_context(patch(f"{_LIFESPAN}._register_schema_providers"))
        stack.enter_context(
            patch(f"{_LIFESPAN}._preload_dataframe_cache_progressive", new=AsyncMock())
        )
        # Shutdown drain: hermetic no-op (its own contract is covered by
        # test_lifespan_drain_td004.py; leftover tasks from other tests must
        # not stall THIS test's shutdown).
        stack.enter_context(patch(f"{_LIFESPAN}._drain_background_builds", new=AsyncMock()))

        # Function-local imports: patch at their source modules.
        stack.enter_context(patch("autom8_asana.models.business._bootstrap.bootstrap"))
        stack.enter_context(
            patch(
                "opentelemetry.instrumentation.httpx.HTTPXClientInstrumentor",
                return_value=MagicMock(),
            )
        )
        stack.enter_context(patch("autom8_asana.config.AsanaConfig"))
        stack.enter_context(patch("autom8_asana.cache.integration.factory.create_cache_provider"))
        stack.enter_context(
            patch(
                "autom8_asana.core.registry_validation.validate_cross_registry_consistency",
                return_value=SimpleNamespace(ok=True),
            )
        )
        stack.enter_context(
            patch("autom8_asana.cache.dataframe.factory.initialize_build_coordinator")
        )
        stack.enter_context(patch("autom8_asana.api.routes.workflows.register_workflow_config"))
        stack.enter_context(patch("autom8_asana.api.routes.health.set_workflow_configs_registered"))
        stack.enter_context(
            patch("autom8_asana.dataframes.cascade_utils.validate_cascade_ordering")
        )
        stack.enter_context(
            patch(
                "autom8_asana.api.event_loop_monitor.EventLoopLagMonitor",
                return_value=MagicMock(stop=AsyncMock()),
            )
        )
        stack.enter_context(
            patch(
                "autom8_asana.api.sli_heartbeat.SliHeartbeat",
                return_value=MagicMock(stop=AsyncMock()),
            )
        )
        # NOTE: AccountStatusPushLoop is deliberately NOT patched.
        yield


async def test_lifespan_starts_status_push_loop_with_live_task(
    _mocked_startup_collaborators: None,
) -> None:
    """Startup wiring: the loop is constructed, stored on app.state, and its
    background task is RUNNING (not merely constructed) after lifespan startup.

    Mutation canary M3: deleting the AccountStatusPushLoop block from
    lifespan() makes app.state.status_push_loop absent -> RED.
    """
    app = FastAPI()

    async with lifespan(app):
        assert hasattr(app.state, "status_push_loop"), (
            "lifespan must store the account-status push loop on app.state "
            "(SD-02 wiring absent = the H1 dark-seam regression)"
        )
        loop = app.state.status_push_loop
        assert isinstance(loop, AccountStatusPushLoop)

        task = loop._task
        assert isinstance(task, asyncio.Task), "loop.start() must have created the task"
        assert not task.done(), "the push loop task must be LIVE after startup"
        assert task.get_name() == "account_status_push_loop"


async def test_lifespan_shutdown_stops_status_push_loop(
    _mocked_startup_collaborators: None,
) -> None:
    """Shutdown wiring: exiting the lifespan awaits loop.stop() -- the task is
    cancelled and torn down, never orphaned past shutdown."""
    app = FastAPI()

    async with lifespan(app):
        task = app.state.status_push_loop._task
        assert task is not None and not task.done()

    assert task.done(), "shutdown must tear the push loop task down"
    assert task.cancelled(), "stop() cancels the loop task (cancel-safe teardown)"
    assert app.state.status_push_loop._task is None, "stop() clears the task handle"
