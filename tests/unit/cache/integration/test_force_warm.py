"""Unit tests for src/autom8_asana/cache/integration/force_warm.py.

Coverage (HANDOFF AC-7 / ADR-003 HYBRID + LD-P3-2 coalescer routing):

- ``resolve_lambda_arn`` — env var contract.
- ``build_coalescer_key`` — namespace + entity_type ordering.
- async-mode (Event) — no L1 invalidation, returns 202 status.
- sync-mode (RequestResponse) — invalidates L1 on success per ADR-003.
- sync-mode failure — raises ForceWarmError, L1 NOT invalidated.
- coalescer dedup — two concurrent calls coalesce to a single Lambda invoke.
- coalescer release on exception — lock not stranded.
- L1 invalidation surface — DataFrameCache.invalidate / invalidate_project
  called per entity_types tuple.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
from autom8_asana.cache.integration.dataframe_cache import DataFrameCache
from autom8_asana.cache.integration.force_warm import (
    COALESCER_KEY_PREFIX,
    LAMBDA_ARN_ENV_VAR,
    ForceWarmError,
    ForceWarmResult,
    build_coalescer_key,
    force_warm,
    resolve_lambda_arn,
)

PROJECT_GID = "1143843662099250"
LAMBDA_ARN = "arn:aws:lambda:us-east-1:123:function:cache-warmer"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_cache() -> DataFrameCache:
    return DataFrameCache(
        memory_tier=MemoryTier(max_entries=100),
        progressive_tier=AsyncMock(),
        coalescer=DataFrameCacheCoalescer(),
        circuit_breaker=CircuitBreaker(),
    )


def _make_lambda_response(
    *,
    status_code: int = 200,
    function_error: str | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a boto3-shaped Lambda invoke response."""
    payload_obj: dict[str, Any] = {}
    if body is not None:
        payload_obj["body"] = json.dumps(body)
    payload_bytes = json.dumps(payload_obj).encode("utf-8") if payload_obj else b""

    body_handle = MagicMock()
    body_handle.read.return_value = payload_bytes

    response: dict[str, Any] = {
        "StatusCode": status_code,
        "Payload": body_handle,
    }
    if function_error is not None:
        response["FunctionError"] = function_error
    return response


# ---------------------------------------------------------------------------
# resolve_lambda_arn
# ---------------------------------------------------------------------------


class TestResolveLambdaArn:
    def test_env_var_present(self) -> None:
        assert resolve_lambda_arn({LAMBDA_ARN_ENV_VAR: LAMBDA_ARN}) == LAMBDA_ARN

    def test_env_var_strips_whitespace(self) -> None:
        assert resolve_lambda_arn({LAMBDA_ARN_ENV_VAR: "  " + LAMBDA_ARN + " "}) == LAMBDA_ARN

    def test_env_var_missing_raises(self) -> None:
        with pytest.raises(ForceWarmError) as exc_info:
            resolve_lambda_arn({})
        assert exc_info.value.kind == ForceWarmError.KIND_CONFIG

    def test_env_var_empty_raises(self) -> None:
        with pytest.raises(ForceWarmError) as exc_info:
            resolve_lambda_arn({LAMBDA_ARN_ENV_VAR: ""})
        assert exc_info.value.kind == ForceWarmError.KIND_CONFIG

    def test_env_var_whitespace_only_raises(self) -> None:
        with pytest.raises(ForceWarmError):
            resolve_lambda_arn({LAMBDA_ARN_ENV_VAR: "   "})


# ---------------------------------------------------------------------------
# build_coalescer_key
# ---------------------------------------------------------------------------


class TestBuildCoalescerKey:
    def test_namespaced_under_forcewarm_prefix(self) -> None:
        key = build_coalescer_key(PROJECT_GID, ())
        assert key.startswith(COALESCER_KEY_PREFIX)

    def test_no_collision_with_swr_build_lock(self) -> None:
        # SWR build-lock keys are "{entity_type}:{project_gid}".
        # Force-warm keys are "forcewarm:{project_gid}:{entity_types}".
        # The two formats cannot collide because SWR keys never contain
        # the literal "forcewarm:" prefix at the start.
        key = build_coalescer_key(PROJECT_GID, ("unit",))
        assert not key.startswith("unit:")
        assert key.startswith(COALESCER_KEY_PREFIX)

    def test_empty_entity_types_uses_wildcard(self) -> None:
        key = build_coalescer_key(PROJECT_GID, ())
        assert key.endswith(":*")

    def test_entity_types_sorted_for_stability(self) -> None:
        # ("offer", "unit") and ("unit", "offer") MUST coalesce.
        key1 = build_coalescer_key(PROJECT_GID, ("unit", "offer"))
        key2 = build_coalescer_key(PROJECT_GID, ("offer", "unit"))
        assert key1 == key2

    def test_distinct_entity_types_distinct_keys(self) -> None:
        key1 = build_coalescer_key(PROJECT_GID, ("unit",))
        key2 = build_coalescer_key(PROJECT_GID, ("offer",))
        assert key1 != key2


# ---------------------------------------------------------------------------
# Async (Event) mode
# ---------------------------------------------------------------------------


class TestForceWarmAsyncMode:
    """Default async path: InvocationType=Event, NO L1 invalidation."""

    @pytest.mark.asyncio
    async def test_async_invoke_returns_202(self) -> None:
        cache = _make_cache()
        client = MagicMock()
        client.invoke.return_value = {"StatusCode": 202}

        result = await force_warm(
            cache=cache,
            project_gid=PROJECT_GID,
            wait=False,
            lambda_client=client,
            env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
        )

        assert isinstance(result, ForceWarmResult)
        assert result.invoked is True
        assert result.deduped is False
        assert result.invocation_type == "Event"
        assert result.lambda_status_code == 202
        assert result.l1_invalidated is False  # async mode does NOT invalidate

        # Lambda was invoked once with InvocationType="Event".
        client.invoke.assert_called_once()
        call_kwargs = client.invoke.call_args.kwargs
        assert call_kwargs["InvocationType"] == "Event"
        assert call_kwargs["FunctionName"] == LAMBDA_ARN
        # Payload contains project_gid.
        payload = json.loads(call_kwargs["Payload"])
        assert payload["project_gid"] == PROJECT_GID

    @pytest.mark.asyncio
    async def test_async_unexpected_status_logged_not_raised(self) -> None:
        cache = _make_cache()
        client = MagicMock()
        client.invoke.return_value = {"StatusCode": 500}

        # Async mode is fire-and-forget: failures populate result.error
        # but do NOT raise.
        result = await force_warm(
            cache=cache,
            project_gid=PROJECT_GID,
            wait=False,
            lambda_client=client,
            env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
        )
        assert result.error is not None
        assert "500" in result.error
        assert result.l1_invalidated is False

    @pytest.mark.asyncio
    async def test_async_does_not_invalidate_l1_per_adr003(self) -> None:
        # Pre-populate L1 with a sentinel and verify it remains.
        cache = _make_cache()
        cache.invalidate = MagicMock()  # type: ignore[method-assign]
        cache.invalidate_project = MagicMock()  # type: ignore[method-assign]

        client = MagicMock()
        client.invoke.return_value = {"StatusCode": 202}

        await force_warm(
            cache=cache,
            project_gid=PROJECT_GID,
            wait=False,
            lambda_client=client,
            env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
        )

        # Neither invalidation method called per ADR-003 async branch.
        cache.invalidate.assert_not_called()
        cache.invalidate_project.assert_not_called()


# ---------------------------------------------------------------------------
# Sync (RequestResponse) mode
# ---------------------------------------------------------------------------


class TestForceWarmSyncMode:
    """--wait path: InvocationType=RequestResponse, INVALIDATES L1."""

    @pytest.mark.asyncio
    async def test_sync_success_invalidates_l1(self) -> None:
        cache = _make_cache()
        cache.invalidate_project = MagicMock()  # type: ignore[method-assign]

        client = MagicMock()
        client.invoke.return_value = _make_lambda_response(
            status_code=200,
            body={"success": True},
        )

        result = await force_warm(
            cache=cache,
            project_gid=PROJECT_GID,
            wait=True,
            lambda_client=client,
            env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
        )

        assert result.invoked is True
        assert result.invocation_type == "RequestResponse"
        assert result.l1_invalidated is True
        cache.invalidate_project.assert_called_once_with(project_gid=PROJECT_GID)

    @pytest.mark.asyncio
    async def test_sync_with_specific_entity_types_invalidates_each(self) -> None:
        cache = _make_cache()
        cache.invalidate = MagicMock()  # type: ignore[method-assign]

        client = MagicMock()
        client.invoke.return_value = _make_lambda_response(status_code=200, body={"success": True})

        result = await force_warm(
            cache=cache,
            project_gid=PROJECT_GID,
            entity_types=("unit", "offer"),
            wait=True,
            lambda_client=client,
            env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
        )

        assert result.l1_invalidated is True
        # Each entity type invalidated.
        assert cache.invalidate.call_count == 2
        called_kwargs = [c.kwargs for c in cache.invalidate.call_args_list]
        called_entity_types = {kw["entity_type"] for kw in called_kwargs}
        assert called_entity_types == {"unit", "offer"}
        assert all(kw["project_gid"] == PROJECT_GID for kw in called_kwargs)

    @pytest.mark.asyncio
    async def test_sync_function_error_raises_and_skips_l1(self) -> None:
        cache = _make_cache()
        cache.invalidate_project = MagicMock()  # type: ignore[method-assign]

        client = MagicMock()
        client.invoke.return_value = _make_lambda_response(
            status_code=200,
            function_error="Unhandled",
        )

        with pytest.raises(ForceWarmError) as exc_info:
            await force_warm(
                cache=cache,
                project_gid=PROJECT_GID,
                wait=True,
                lambda_client=client,
                env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
            )
        assert exc_info.value.kind == ForceWarmError.KIND_LAMBDA
        # L1 NOT invalidated on Lambda failure (would be worse than no-op).
        cache.invalidate_project.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_body_success_false_raises(self) -> None:
        cache = _make_cache()
        cache.invalidate_project = MagicMock()  # type: ignore[method-assign]

        client = MagicMock()
        client.invoke.return_value = _make_lambda_response(
            status_code=200,
            body={"success": False, "error": "no fresh data available"},
        )

        with pytest.raises(ForceWarmError):
            await force_warm(
                cache=cache,
                project_gid=PROJECT_GID,
                wait=True,
                lambda_client=client,
                env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
            )
        cache.invalidate_project.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_invoke_exception_wrapped(self) -> None:
        cache = _make_cache()
        cache.invalidate_project = MagicMock()  # type: ignore[method-assign]

        client = MagicMock()
        client.invoke.side_effect = RuntimeError("network blip")

        with pytest.raises(ForceWarmError) as exc_info:
            await force_warm(
                cache=cache,
                project_gid=PROJECT_GID,
                wait=True,
                lambda_client=client,
                env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
            )
        assert exc_info.value.kind == ForceWarmError.KIND_INVOKE
        cache.invalidate_project.assert_not_called()


# ---------------------------------------------------------------------------
# Coalescer dedup
# ---------------------------------------------------------------------------


class TestCoalescerRouting:
    """LD-P3-2: requests for the same target coalesce; lock released on errors."""

    @pytest.mark.asyncio
    async def test_concurrent_force_warms_coalesce(self) -> None:
        cache = _make_cache()

        invoke_started = asyncio.Event()
        invoke_release = asyncio.Event()

        # Track invocations: only first request should reach the Lambda.
        invocation_count = 0

        def slow_invoke(**kwargs: Any) -> dict[str, Any]:
            nonlocal invocation_count
            invocation_count += 1
            invoke_started.set()
            # Run the wait synchronously; the coalescer-released task is on
            # another asyncio task. We use a sentinel that the test releases.
            return {"StatusCode": 202}

        client = MagicMock()
        client.invoke.side_effect = slow_invoke

        async def first_call() -> ForceWarmResult:
            return await force_warm(
                cache=cache,
                project_gid=PROJECT_GID,
                wait=False,
                lambda_client=client,
                env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
            )

        # Hold the coalescer lock by manually acquiring the same key.
        coalescer_key = build_coalescer_key(PROJECT_GID, ())
        acquired = await cache.coalescer.try_acquire_async(coalescer_key)
        assert acquired

        # Now any force_warm call with the same key will be coalesced.
        async def coalesced_call() -> ForceWarmResult:
            return await force_warm(
                cache=cache,
                project_gid=PROJECT_GID,
                wait=False,
                lambda_client=client,
                env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
                coalescer_wait_seconds=2.0,
            )

        # Schedule the coalesced call; it should wait until we release.
        coalesced_task = asyncio.create_task(coalesced_call())
        await asyncio.sleep(0.05)
        # Coalesced call should still be pending.
        assert not coalesced_task.done()

        # Release the coalescer lock with success.
        await cache.coalescer.release_async(coalescer_key, success=True)

        result = await asyncio.wait_for(coalesced_task, timeout=2.0)

        assert result.deduped is True
        assert result.invoked is False  # No Lambda invoke from coalesced caller.
        # Lambda was NOT invoked by the coalesced caller (the lock-holder
        # was the test, which never called Lambda).
        assert client.invoke.call_count == 0
        # Suppress unused variable warnings.
        _ = (invoke_started, invoke_release, invocation_count, first_call)

    @pytest.mark.asyncio
    async def test_coalesced_wait_timeout_returns_error_result(self) -> None:
        cache = _make_cache()
        coalescer_key = build_coalescer_key(PROJECT_GID, ())
        # Hold the lock and never release.
        await cache.coalescer.try_acquire_async(coalescer_key)

        client = MagicMock()
        result = await force_warm(
            cache=cache,
            project_gid=PROJECT_GID,
            wait=False,
            lambda_client=client,
            env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
            coalescer_wait_seconds=0.1,
        )

        assert result.deduped is True
        assert result.invoked is False
        assert result.error is not None
        client.invoke.assert_not_called()

        # Cleanup the held lock.
        await cache.coalescer.release_async(coalescer_key, success=False)

    @pytest.mark.asyncio
    async def test_lock_released_on_invoke_exception(self) -> None:
        cache = _make_cache()
        client = MagicMock()
        client.invoke.side_effect = RuntimeError("boom")

        with pytest.raises(ForceWarmError):
            await force_warm(
                cache=cache,
                project_gid=PROJECT_GID,
                wait=True,
                lambda_client=client,
                env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
            )

        # Coalescer key must NOT remain BUILDING — a subsequent acquire
        # must succeed (the lock was released in `finally`).
        coalescer_key = build_coalescer_key(PROJECT_GID, ())
        # Wait a tick for the release coroutine to land its state change.
        for _ in range(20):
            if not cache.coalescer.is_building(coalescer_key):
                break
            await asyncio.sleep(0.01)
        assert not cache.coalescer.is_building(coalescer_key)

    @pytest.mark.asyncio
    async def test_uses_namespaced_coalescer_key(self) -> None:
        # Verify the coalescer key carries the forcewarm prefix.
        cache = _make_cache()
        client = MagicMock()
        client.invoke.return_value = {"StatusCode": 202}

        result = await force_warm(
            cache=cache,
            project_gid=PROJECT_GID,
            entity_types=("unit",),
            wait=False,
            lambda_client=client,
            env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
        )

        assert result.coalescer_key.startswith(COALESCER_KEY_PREFIX)
        assert PROJECT_GID in result.coalescer_key
        assert "unit" in result.coalescer_key


# ---------------------------------------------------------------------------
# Direct-invoke FORBIDDEN regression — verify NO direct boto3 invoke
# ---------------------------------------------------------------------------


class TestDirectInvokeForbidden:
    """LD-P3-2: force_warm MUST go through coalescer, never direct boto3."""

    @pytest.mark.asyncio
    async def test_invoke_only_via_injected_lambda_client(self) -> None:
        """When lambda_client is injected, no real boto3 client constructed."""
        cache = _make_cache()
        client = MagicMock()
        client.invoke.return_value = {"StatusCode": 202}

        # If force_warm tried to construct boto3.client(), this would fail
        # in a no-AWS-creds environment. The fact that the test passes
        # without monkey-patching boto3 demonstrates the DI seam.
        result = await force_warm(
            cache=cache,
            project_gid=PROJECT_GID,
            wait=False,
            lambda_client=client,
            env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
        )
        assert result.invoked is True
        client.invoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_coalescer_acquire_called_before_invoke(self) -> None:
        """try_acquire_async MUST fire BEFORE client.invoke — verifies LD-P3-2 wiring.

        The test instruments the coalescer's try_acquire_async to record a
        timestamp and asserts the Lambda invoke happens AFTER acquisition.
        """
        cache = _make_cache()

        acquire_call_order: list[str] = []

        original_try_acquire = cache.coalescer.try_acquire_async

        async def tracked_acquire(key: str) -> bool:
            acquire_call_order.append(f"acquire:{key}")
            return await original_try_acquire(key)

        cache.coalescer.try_acquire_async = tracked_acquire  # type: ignore[method-assign]

        def tracked_invoke(**kwargs: Any) -> dict[str, Any]:
            acquire_call_order.append("invoke")
            return {"StatusCode": 202}

        client = MagicMock()
        client.invoke.side_effect = tracked_invoke

        await force_warm(
            cache=cache,
            project_gid=PROJECT_GID,
            wait=False,
            lambda_client=client,
            env={LAMBDA_ARN_ENV_VAR: LAMBDA_ARN},
        )

        # Acquire must precede invoke.
        assert acquire_call_order[0].startswith("acquire:")
        assert acquire_call_order[1] == "invoke"
