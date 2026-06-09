"""Tests for the section-lane handler routing (ADR §B).

Mirrors TestHandlerBulkRouting / TestPrematerializeFastSet / TestHandlerFastRouting
but for the section-arm-only lane.  Three test classes cover:
  1. TestSectionLaneKeySource       -- key-source enumeration (34 section keys)
  2. TestSectionLaneFlagRouting     -- handler flag routing (prematerialize_section_set)
  3. TestSectionLaneSelfContinuation -- checkpoint-prefix isolation and section flag continuity
"""

from __future__ import annotations

import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.lambda_handlers.cache_warmer import (
    WarmResponse,
    _prematerialize_bulk_set_async,
    handler,
    handler_async,
)
from autom8_asana.lambda_handlers.cloudwatch import emit_metric

# =============================================================================
# Helpers
# =============================================================================


class MockLambdaContext:
    """Minimal Lambda context stub for timeout/ARN testing."""

    def __init__(
        self,
        remaining_time_ms: int = 900_000,
        arn: str = "arn:aws:lambda:us-east-1:123:function:warmer",
    ) -> None:
        self.remaining_time_ms = remaining_time_ms
        self.invoked_function_arn = arn
        self.aws_request_id = "test-request-id"

    def get_remaining_time_in_millis(self) -> int:
        return self.remaining_time_ms


def _make_client_cm() -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=MagicMock())
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _standard_patches(mock_cache: MagicMock) -> list:
    """Patch set mirroring TestPrematerializeFastSet._patches."""
    return [
        patch(
            "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
            return_value=mock_cache,
        ),
        patch(
            "autom8_asana.cache.dataframe.factory.initialize_dataframe_cache",
            return_value=mock_cache,
        ),
        patch("autom8_asana.auth.bot_pat.get_bot_pat", return_value="pat"),
        patch(
            "autom8_asana.lambda_handlers.cache_warmer.resolve_secret_from_env",
            return_value="ws-123",
        ),
        patch(
            "autom8_asana.AsanaClient",
            return_value=_make_client_cm(),
        ),
    ]


# =============================================================================
# 1. Key-Source Enumeration
# =============================================================================


class TestSectionLaneKeySource:
    """section_only_prematerialization_keys() produces 34 (gid, 'section') keys."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        cache = MagicMock()
        cache.put_async = AsyncMock()
        return cache

    async def test_full_coverage_warms_all_34_section_keys(
        self, mock_cache: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A clean section-lane run warms exactly 34 section keys over its own
        denominator -- WarmerCheckpointCleared/coverage emitted as (34, 34)."""
        from autom8_asana.cache.dataframe.warmer import WarmResult, WarmStatus
        from autom8_asana.core.project_registry import section_only_prematerialization_keys

        monkeypatch.setenv("ASANA_WARMER_KEY_BUDGET", "0")

        async def fake_warm_key(
            self_obj: object, project_gid: str, entity_type: str, client: object
        ) -> WarmStatus:
            return WarmStatus(
                entity_type=entity_type,
                result=WarmResult.SUCCESS,
                project_gid=project_gid,
                row_count=5,
            )

        checkpoint_mgr = MagicMock()
        checkpoint_mgr.load_async = AsyncMock(return_value=None)
        checkpoint_mgr.save_async = AsyncMock()
        checkpoint_mgr.clear_async = AsyncMock(return_value=True)

        with contextlib.ExitStack() as stack:
            for p in _standard_patches(mock_cache):
                stack.enter_context(p)
            stack.enter_context(
                patch(
                    "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
                    return_value=checkpoint_mgr,
                )
            )
            stack.enter_context(
                patch(
                    "autom8_asana.cache.dataframe.warmer.CacheWarmer.warm_key_async",
                    new=fake_warm_key,
                )
            )
            emit_cov = stack.enter_context(
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer.emit_warmer_coverage_rate",
                    return_value=1.0,
                )
            )
            response = await _prematerialize_bulk_set_async(
                context=None,
                key_source=section_only_prematerialization_keys,
                section_lane=True,
            )

        assert response.success is True
        assert "warmer_coverage_rate=1.0000" in response.message
        # The section lane's denominator is 34, NOT the 68-key bulk sweep.
        assert len(response.entity_results) == 34
        emit_cov.assert_called_once_with(34, 34)
        checkpoint_mgr.clear_async.assert_awaited_once()
        assert response.checkpoint_cleared is True

    async def test_all_keys_are_section_arm(
        self, mock_cache: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Every key warmed by the section lane has entity_type == 'section'."""
        from autom8_asana.cache.dataframe.warmer import WarmResult, WarmStatus
        from autom8_asana.core.project_registry import section_only_prematerialization_keys

        monkeypatch.setenv("ASANA_WARMER_KEY_BUDGET", "0")
        warmed: list[tuple[str, str]] = []

        async def fake_warm_key(
            self_obj: object, project_gid: str, entity_type: str, client: object
        ) -> WarmStatus:
            warmed.append((project_gid, entity_type))
            return WarmStatus(
                entity_type=entity_type,
                result=WarmResult.SUCCESS,
                project_gid=project_gid,
                row_count=1,
            )

        checkpoint_mgr = MagicMock()
        checkpoint_mgr.load_async = AsyncMock(return_value=None)
        checkpoint_mgr.save_async = AsyncMock()
        checkpoint_mgr.clear_async = AsyncMock(return_value=True)

        with contextlib.ExitStack() as stack:
            for p in _standard_patches(mock_cache):
                stack.enter_context(p)
            stack.enter_context(
                patch(
                    "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
                    return_value=checkpoint_mgr,
                )
            )
            stack.enter_context(
                patch(
                    "autom8_asana.cache.dataframe.warmer.CacheWarmer.warm_key_async",
                    new=fake_warm_key,
                )
            )
            stack.enter_context(
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer.emit_warmer_coverage_rate",
                    return_value=1.0,
                )
            )
            await _prematerialize_bulk_set_async(
                context=None,
                key_source=section_only_prematerialization_keys,
                section_lane=True,
            )

        assert len(warmed) == 34
        assert all(et == "section" for _gid, et in warmed)


# =============================================================================
# 2. Flag Routing
# =============================================================================


class TestSectionLaneFlagRouting:
    """prematerialize_section_set=True routes to the section lane."""

    async def test_handler_async_routes_to_section_lane(self) -> None:
        """handler_async with prematerialize_section_set=True calls
        _prematerialize_bulk_set_async with the section key source and section_lane=True."""
        from autom8_asana.core.project_registry import section_only_prematerialization_keys

        mock_response = WarmResponse(success=True, message="ok")
        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._prematerialize_bulk_set_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_section:
            result = await handler_async({"prematerialize_section_set": True})

        assert result["statusCode"] == 200
        mock_section.assert_called_once_with(
            resume_from_checkpoint=True,
            context=None,
            key_source=section_only_prematerialization_keys,
            section_lane=True,
        )

    def test_handler_routes_to_section_lane(self) -> None:
        """handler with prematerialize_section_set=True invokes the section branch."""
        from autom8_asana.core.project_registry import section_only_prematerialization_keys

        mock_response = WarmResponse(success=True, message="ok")
        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._prematerialize_bulk_set_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_section:
            result = handler({"prematerialize_section_set": True}, None)

        assert result["statusCode"] == 200
        mock_section.assert_called_once()
        assert mock_section.call_args.kwargs["section_lane"] is True
        assert mock_section.call_args.kwargs["key_source"] is section_only_prematerialization_keys

    def test_section_flag_takes_precedence_over_bulk(self) -> None:
        """If both prematerialize_section_set and prematerialize_bulk_set are set,
        the section lane wins (it is evaluated first in the if-elif chain)."""
        mock_response = WarmResponse(success=True, message="ok")
        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._prematerialize_bulk_set_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_pre:
            result = handler(
                {"prematerialize_section_set": True, "prematerialize_bulk_set": True},
                None,
            )

        assert result["statusCode"] == 200
        # Section flag evaluated first; section_lane=True in kwargs.
        assert mock_pre.call_args.kwargs.get("section_lane") is True

    def test_bulk_flag_alone_does_not_set_section_lane(self) -> None:
        """prematerialize_bulk_set=True must NOT inject section_lane=True."""
        mock_response = WarmResponse(success=True, message="ok")
        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._prematerialize_bulk_set_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_pre:
            handler({"prematerialize_bulk_set": True}, None)

        # section_lane kwarg must be absent or False for the bulk path.
        kwargs = mock_pre.call_args.kwargs
        assert not kwargs.get("section_lane", False)


# =============================================================================
# 3. Self-Continuation (checkpoint-prefix isolation)
# =============================================================================


class TestSectionLaneSelfContinuation:
    """On timeout, the section-lane continuation carries prematerialize_section_set=True
    and NOT prematerialize_bulk_set -- it must re-enter the section branch."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        cache = MagicMock()
        cache.put_async = AsyncMock()
        return cache

    async def test_timeout_self_invokes_with_section_flag(self, mock_cache: MagicMock) -> None:
        from autom8_asana.core.project_registry import section_only_prematerialization_keys

        context = MockLambdaContext(remaining_time_ms=0)

        checkpoint_mgr = MagicMock()
        checkpoint_mgr.load_async = AsyncMock(return_value=None)
        checkpoint_mgr.save_async = AsyncMock()
        checkpoint_mgr.clear_async = AsyncMock(return_value=True)

        with contextlib.ExitStack() as stack:
            for p in _standard_patches(mock_cache):
                stack.enter_context(p)
            stack.enter_context(
                patch(
                    "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
                    return_value=checkpoint_mgr,
                )
            )
            self_invoke = stack.enter_context(
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer._self_invoke_continuation",
                )
            )
            stack.enter_context(
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer.emit_warmer_coverage_rate",
                    return_value=0.0,
                )
            )
            response = await _prematerialize_bulk_set_async(
                context=context,
                key_source=section_only_prematerialization_keys,
                section_lane=True,
            )

        assert response.success is False
        assert "self-continuing" in response.message
        self_invoke.assert_called_once()
        # Lane isolation: section continuation routes to section, never bulk.
        assert self_invoke.call_args.kwargs["prematerialize_section_set"] is True
        assert self_invoke.call_args.kwargs["prematerialize_bulk_set"] is False
        checkpoint_mgr.save_async.assert_awaited()

    async def test_bulk_timeout_does_not_set_section_flag(self, mock_cache: MagicMock) -> None:
        """Bulk lane timeout continuation must NOT carry prematerialize_section_set."""
        context = MockLambdaContext(remaining_time_ms=0)

        checkpoint_mgr = MagicMock()
        checkpoint_mgr.load_async = AsyncMock(return_value=None)
        checkpoint_mgr.save_async = AsyncMock()
        checkpoint_mgr.clear_async = AsyncMock(return_value=True)

        with contextlib.ExitStack() as stack:
            for p in _standard_patches(mock_cache):
                stack.enter_context(p)
            stack.enter_context(
                patch(
                    "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
                    return_value=checkpoint_mgr,
                )
            )
            self_invoke = stack.enter_context(
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer._self_invoke_continuation",
                )
            )
            stack.enter_context(
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer.emit_warmer_coverage_rate",
                    return_value=0.0,
                )
            )
            # Default bulk path (no key_source / section_lane).
            await _prematerialize_bulk_set_async(context=context)

        self_invoke.assert_called_once()
        kwargs = self_invoke.call_args.kwargs
        assert kwargs.get("prematerialize_bulk_set") is True
        assert not kwargs.get("prematerialize_section_set", False)
