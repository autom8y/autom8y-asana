"""DataFrameCache initialization contract for the generic workflow Lambda handler.

DATAFRAME-CACHE-INIT (contente-onboarding-walkthrough amendment A6, post-deploy
dry-run under the Lambda execution role, 2026-07-02):

    CacheNotWarmError: DataFrame unavailable for business.

IAM is exonerated (simulate-principal-policy: GetObject + prefix-ListBucket
ALLOWED on the real paths). Root cause: ``initialize_dataframe_cache()``
(factory.py:149) is invoked ONLY by the API lifespan (api/lifespan.py:224 ->
api/startup.py:30-32) and the cache_warmer Lambda (cache_warmer.py:382-397).
The walkthrough's shared ``workflow_handler`` never initialized the singleton,
so ``get_dataframe_cache_provider()`` returned None at the workflow's
frame-resolution seam (universal_strategy.py:995-998, the GFR company_id read)
and the read failed CacheNotWarm.

This module pins the contract that the SHARED factory ``_execute`` initializes
the DataFrameCache singleton once per invocation (idempotent on warm
containers), that the provider is non-None where the workflow resolves it once
initialization succeeds, and that siblings on an S3-unconfigured topology still
construct (graceful-None, never a hard failure).

Harness idiom mirrors test_workflow_handler_workspace_gid.py: the production
``handler`` runs ``asyncio.run`` internally, so it is invoked synchronously
from plain ``def`` tests. worker_isolated excludes the handler-invoking tests
from the sharded run; xdist_group co-locates the module on a single worker.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

from autom8_asana.automation.workflows.base import WorkflowAction, WorkflowResult
from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
from autom8_asana.cache.dataframe.factory import (
    get_dataframe_cache_provider,
    reset_dataframe_cache,
    set_dataframe_cache,
)
from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
from autom8_asana.cache.integration.dataframe_cache import DataFrameCache
from autom8_asana.lambda_handlers.workflow_handler import (
    WorkflowHandlerConfig,
    create_workflow_handler,
)

pytestmark = [
    pytest.mark.xdist_group("workflow_handler"),
    pytest.mark.worker_isolated,
]

# The seam the handler's deferred import resolves at call time. Patching the
# factory module attribute intercepts the handler's
# ``from autom8_asana.cache.dataframe.factory import initialize_dataframe_cache``.
_INITIALIZER_SEAM = "autom8_asana.cache.dataframe.factory.initialize_dataframe_cache"


@pytest.fixture(autouse=True)
def _pristine_singleton() -> Iterator[None]:
    """Isolate the module-level DataFrameCache singleton per test."""
    reset_dataframe_cache()
    yield
    reset_dataframe_cache()


# --- Handler harness helpers (mirror test_workflow_handler_workspace_gid.py) ---


def _make_workflow_result(*, succeeded: int = 8, total: int = 10) -> WorkflowResult:
    started = datetime(2026, 7, 2, 2, 6, 0, tzinfo=UTC)
    return WorkflowResult(
        workflow_id="onboarding-walkthrough",
        started_at=started,
        completed_at=started + timedelta(seconds=0.76),
        total=total,
        succeeded=succeeded,
        failed=total - succeeded,
        skipped=0,
        errors=[],
        metadata={},
    )


def _mock_workflow(resolved_providers: list[DataFrameCache | None] | None = None) -> MagicMock:
    """Mock workflow; when ``resolved_providers`` is given, execute_async resolves
    the cache provider EXACTLY the way the GFR read does (a call-time lookup of
    ``get_dataframe_cache_provider()``, universal_strategy.py:995-998) and records
    what it saw."""
    wf = MagicMock(spec=WorkflowAction)
    wf.validate_async = AsyncMock(return_value=[])
    wf.enumerate_async = AsyncMock(return_value=[{"gid": "1"}])

    if resolved_providers is None:
        wf.execute_async = AsyncMock(return_value=_make_workflow_result())
    else:

        async def _execute(*_args: Any, **_kwargs: Any) -> WorkflowResult:
            resolved_providers.append(get_dataframe_cache_provider())
            return _make_workflow_result()

        wf.execute_async = AsyncMock(side_effect=_execute)
    return wf


def _make_config(workflow: MagicMock) -> WorkflowHandlerConfig:
    # requires_data_client=False takes the lean branch: it still passes through
    # the shared setup altitude (workspace_gid + cache init) without dragging in
    # the DataServiceClient/ServiceToken S2S path (owned by the auth_injection
    # suite). fleet_namespace=None opts out of fleet emission side effects.
    return WorkflowHandlerConfig(
        workflow_factory=MagicMock(return_value=workflow),
        workflow_id="onboarding-walkthrough",
        log_prefix="lambda_onboarding_walkthrough",
        default_params={"max_concurrency": 5},
        requires_data_client=False,
        fleet_namespace=None,
    )


def _invoke_handler(workflow: MagicMock) -> dict[str, Any]:
    """Invoke the production handler with the heavy collaborators stubbed."""
    with (
        patch("autom8_asana.client.AsanaClient"),
        patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric"),
        patch(
            "autom8_asana.lambda_handlers.workflow_handler.resolve_secret_from_env",
            side_effect=ValueError("No secret source"),
        ),
    ):
        handler = create_workflow_handler(_make_config(workflow))
        return handler({}, MagicMock())


def _make_in_memory_cache() -> DataFrameCache:
    """Real DataFrameCache over in-memory storage (mirrors
    tests/unit/cache/dataframe/test_dataframe_cache.py::make_cache): a real
    MemoryTier plus a mocked progressive tier -- no S3, no network."""
    return DataFrameCache(
        memory_tier=MemoryTier(max_entries=100),
        progressive_tier=MagicMock(),
        coalescer=DataFrameCacheCoalescer(max_wait_seconds=1.0),
        circuit_breaker=CircuitBreaker(
            failure_threshold=3,
            reset_timeout_seconds=60,
            success_threshold=1,
        ),
    )


class TestFactoryInitializesDataFrameCache:
    """AC-1: the shared factory must call initialize_dataframe_cache() once per
    invocation, at setup altitude (before workflow construction)."""

    def test_handler_calls_initializer_exactly_once(self) -> None:
        """RED on HEAD: the shared factory never touches the cache factory, so
        the singleton stays None and the GFR read raises CacheNotWarm. GREEN
        after fix: _execute calls initialize_dataframe_cache() exactly once per
        invocation (not per-entity), mirroring the API lifespan the Lambda path
        lacks (startup.py:30-32) and the warmer sibling (cache_warmer.py:395-397)."""
        workflow = _mock_workflow()
        with patch(_INITIALIZER_SEAM, return_value=None) as mock_init:
            result = _invoke_handler(workflow)

        assert result["statusCode"] == 200, f"handler did not complete: {result.get('body')}"
        assert mock_init.call_count == 1, (
            "DATAFRAME-CACHE-INIT regression: the shared factory must call "
            "initialize_dataframe_cache() exactly once per invocation -- got "
            f"{mock_init.call_count} calls. Without it the singleton stays None "
            "and any frame-reading workflow dies CacheNotWarm "
            "('DataFrame unavailable for business', amendment-A6 dry-run log)."
        )


class TestProviderResolvesAfterInitialization:
    """AC-2 (GREEN-shape): once initialization succeeds, the provider is
    non-None at the exact seam the workflow resolves it."""

    def test_provider_is_non_none_where_the_workflow_resolves_it(self) -> None:
        cache = _make_in_memory_cache()

        def _initialize_in_memory() -> DataFrameCache:
            # What the real initializer does on a configured topology: store the
            # singleton (factory.py `_dataframe_cache = cache`) and return it --
            # here backed by the in-memory fixture instead of S3.
            set_dataframe_cache(cache)
            return cache

        resolved: list[DataFrameCache | None] = []
        workflow = _mock_workflow(resolved_providers=resolved)

        with patch(_INITIALIZER_SEAM, side_effect=_initialize_in_memory):
            result = _invoke_handler(workflow)

        assert result["statusCode"] == 200, f"handler did not complete: {result.get('body')}"
        assert resolved == [cache], (
            "get_dataframe_cache_provider() must return the initialized cache at "
            "the workflow's resolution seam (the GFR company_id read, "
            f"universal_strategy.py:995-998) -- resolved {resolved!r}. A None here "
            "is exactly the local repro of the amendment-A6 CacheNotWarm fault."
        )


class TestSiblingsUnaffectedWhenS3Unconfigured:
    """AC-3 (sibling-safety, teeth): the REAL initializer's not-configured
    branch (factory.py:190-202) returns None -- construction must still
    complete. Discriminates against a cache_warmer-style hard-fail-on-None
    (cache_warmer.py:398-404) leaking into the shared factory: if the fix
    500'd on None, this test bites."""

    def test_handler_completes_when_s3_unconfigured(self) -> None:
        # NOT patching the initializer: the real factory.py code runs and takes
        # its graceful not-configured branch via settings.s3.bucket == "".
        mock_settings = MagicMock()
        mock_settings.s3.bucket = ""

        resolved: list[DataFrameCache | None] = []
        workflow = _mock_workflow(resolved_providers=resolved)

        with patch("autom8_asana.settings.get_settings", return_value=mock_settings):
            result = _invoke_handler(workflow)

        assert result["statusCode"] == 200, (
            "graceful-None regression: a sibling workflow on an S3-unconfigured "
            "topology must still construct and complete (the workflow degrades "
            f"fail-closed as today), got {result.get('body')}"
        )
        body = json.loads(result["body"])
        assert body.get("status") != "error", f"sibling surfaced an error: {body}"
        assert resolved == [None], (
            "with S3 unconfigured the provider must stay None (fail-closed "
            f"degradation), got {resolved!r} -- a non-None here means the test "
            "did not actually exercise the not-configured branch."
        )
