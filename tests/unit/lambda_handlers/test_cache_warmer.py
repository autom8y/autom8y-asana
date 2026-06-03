"""Unit tests for cache_warmer Lambda handler.

Per TDD-DATAFRAME-CACHE-001 and TDD-lambda-cache-warmer: Tests for Lambda
warm-up handler including timeout detection, checkpoint integration, and
CloudWatch metric emission.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.lambda_handlers.cache_warmer import (
    WarmResponse,
    _warm_cache_async,
    handler,
    handler_async,
)
from autom8_asana.lambda_handlers.cloudwatch import emit_metric
from autom8_asana.lambda_handlers.timeout import (
    TIMEOUT_BUFFER_MS,
    _should_exit_early,
)


class TestWarmResponse:
    """Tests for WarmResponse dataclass."""

    def test_create_success_response(self) -> None:
        """Create a success response with all fields."""
        response = WarmResponse(
            success=True,
            message="Cache warm complete",
            entity_results=[{"entity_type": "unit", "result": "success"}],
            total_rows=5000,
            duration_ms=2500.0,
        )

        assert response.success is True
        assert response.message == "Cache warm complete"
        assert len(response.entity_results) == 1
        assert response.total_rows == 5000
        assert response.duration_ms == 2500.0
        assert response.timestamp is not None

    def test_create_failure_response(self) -> None:
        """Create a failure response."""
        response = WarmResponse(
            success=False,
            message="Cache warm failed",
        )

        assert response.success is False
        assert response.entity_results == []
        assert response.total_rows == 0

    def test_to_dict(self) -> None:
        """Convert response to dictionary."""
        response = WarmResponse(
            success=True,
            message="Cache warm complete",
            total_rows=5000,
            duration_ms=2500.0,
        )

        result = response.to_dict()

        assert result["success"] is True
        assert result["message"] == "Cache warm complete"
        assert result["total_rows"] == 5000
        assert result["duration_ms"] == 2500.0
        assert "timestamp" in result


class TestWarmCacheAsync:
    """Tests for _warm_cache_async function.

    Note: These tests verify the _warm_cache_async function's behavior
    by patching dependencies. The full integration tests would require
    proper environment setup with ASANA_PAT and ASANA_WORKSPACE_GID.
    """

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create a mock DataFrameCache."""
        cache = MagicMock()
        cache.put_async = AsyncMock()
        return cache

    @pytest.fixture
    def sample_dataframe(self) -> pl.DataFrame:
        """Create a sample DataFrame for testing."""
        return pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["Task A", "Task B", "Task C"],
            }
        )

    async def test_no_cache_available(self) -> None:
        """Return failure when cache cannot be initialized."""
        # Need to patch where the imports happen (inside the function)
        with (
            patch.dict("os.environ", {}, clear=True),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=None,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.initialize_dataframe_cache",
                return_value=None,
            ),
        ):
            response = await _warm_cache_async()

        assert response.success is False
        assert "Failed to initialize DataFrameCache" in response.message

    async def test_registry_not_ready(self, mock_cache: MagicMock) -> None:
        """Return failure when registry not ready and discovery fails."""
        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = False

        with (
            patch.dict("os.environ", {}, clear=True),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=mock_registry,
            ),
            patch(
                "autom8_asana.services.discovery.discover_entity_projects_async",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Discovery failed"),
            ),
        ):
            response = await _warm_cache_async()

        assert response.success is False
        assert "EntityProjectRegistry not initialized" in response.message

    async def test_invalid_entity_types(self, mock_cache: MagicMock) -> None:
        """Return failure for invalid entity types."""
        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = True

        with (
            patch.dict("os.environ", {}, clear=True),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=mock_registry,
            ),
        ):
            response = await _warm_cache_async(entity_types=["invalid_type"])

        assert response.success is False
        assert "Invalid entity types" in response.message

    async def test_missing_bot_pat(self, mock_cache: MagicMock) -> None:
        """Return failure when bot PAT not available."""
        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = True
        mock_registry.get_project_gid.return_value = "project-123"

        from autom8_asana.auth.bot_pat import BotPATError

        with (
            patch.dict("os.environ", {}, clear=True),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=mock_registry,
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                side_effect=BotPATError("No PAT"),
            ),
        ):
            response = await _warm_cache_async(entity_types=["unit"])

        assert response.success is False
        assert "Failed to get bot PAT" in response.message

    async def test_missing_workspace_gid(self, mock_cache: MagicMock) -> None:
        """Return failure when workspace GID not set."""
        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = True
        mock_registry.get_project_gid.return_value = "project-123"

        # Set up environment without ASANA_WORKSPACE_GID
        with (
            patch.dict("os.environ", {"ASANA_BOT_PAT": "test-pat"}, clear=True),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=mock_registry,
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test-pat",
            ),
        ):
            response = await _warm_cache_async(entity_types=["unit"])

        assert response.success is False
        assert "ASANA_WORKSPACE_GID" in response.message


class TestHandler:
    """Tests for Lambda handler function."""

    @pytest.fixture
    def mock_warm_response(self) -> WarmResponse:
        """Create a mock warm response."""
        return WarmResponse(
            success=True,
            message="Cache warm complete",
            entity_results=[],
            total_rows=100,
            duration_ms=500.0,
        )

    def test_handler_success(self, mock_warm_response: WarmResponse) -> None:
        """Handler returns 200 on success."""
        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._warm_cache_async",
            new_callable=AsyncMock,
            return_value=mock_warm_response,
        ):
            result = handler({}, None)

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True

    def test_handler_failure(self) -> None:
        """Handler returns 500 on failure."""
        failure_response = WarmResponse(
            success=False,
            message="Cache warm failed",
        )

        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._warm_cache_async",
            new_callable=AsyncMock,
            return_value=failure_response,
        ):
            result = handler({}, None)

        assert result["statusCode"] == 500
        assert result["body"]["success"] is False

    def test_handler_with_entity_types(
        self,
        mock_warm_response: WarmResponse,
    ) -> None:
        """Handler passes entity_types from event."""
        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._warm_cache_async",
            new_callable=AsyncMock,
            return_value=mock_warm_response,
        ) as mock_warm:
            handler({"entity_types": ["unit", "offer"]}, None)

        mock_warm.assert_called_once_with(
            entity_types=["unit", "offer"],
            strict=True,
            resume_from_checkpoint=True,
            context=None,
        )

    def test_handler_with_strict_false(
        self,
        mock_warm_response: WarmResponse,
    ) -> None:
        """Handler passes strict=False from event."""
        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._warm_cache_async",
            new_callable=AsyncMock,
            return_value=mock_warm_response,
        ) as mock_warm:
            handler({"strict": False}, None)

        mock_warm.assert_called_once_with(
            entity_types=None,
            strict=False,
            resume_from_checkpoint=True,
            context=None,
        )

    def test_handler_exception(self) -> None:
        """Handler catches exceptions and returns 500."""
        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._warm_cache_async",
            new_callable=AsyncMock,
            side_effect=Exception("Unexpected error"),
        ):
            result = handler({}, None)

        assert result["statusCode"] == 500
        assert "Handler exception" in result["body"]["message"]


class TestHandlerAsync:
    """Tests for async Lambda handler function."""

    async def test_handler_async_success(self) -> None:
        """Async handler returns 200 on success."""
        mock_response = WarmResponse(
            success=True,
            message="Cache warm complete",
            total_rows=100,
        )

        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._warm_cache_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await handler_async({})

        assert result["statusCode"] == 200
        assert result["body"]["success"] is True

    async def test_handler_async_failure(self) -> None:
        """Async handler returns 500 on failure."""
        mock_response = WarmResponse(
            success=False,
            message="Cache warm failed",
        )

        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._warm_cache_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await handler_async({})

        assert result["statusCode"] == 500
        assert result["body"]["success"] is False

    async def test_handler_async_with_event(self) -> None:
        """Async handler passes event parameters."""
        mock_response = WarmResponse(
            success=True,
            message="Cache warm complete",
        )

        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._warm_cache_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_warm:
            await handler_async({"entity_types": ["unit"], "strict": False})

        mock_warm.assert_called_once_with(
            entity_types=["unit"],
            strict=False,
            resume_from_checkpoint=True,
            context=None,
        )


# ============================================================================
# TD-005: Bulk Pre-Materialization
# ============================================================================


class TestKeyTokenCodec:
    """Tests for the (project_gid, entity_type) checkpoint-token codec."""

    def test_round_trip(self) -> None:
        from autom8_asana.lambda_handlers.cache_warmer import (
            _decode_key_token,
            _encode_key_token,
        )

        token = _encode_key_token("1200653012566782", "section")
        assert token == "1200653012566782:section"
        assert _decode_key_token(token) == ("1200653012566782", "section")


class TestPrematerializeBulkSet:
    """Tests for _prematerialize_bulk_set_async (TD-005)."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        cache = MagicMock()
        cache.put_async = AsyncMock()
        return cache

    def _patches(self, mock_cache: MagicMock) -> list:
        """Common patch set: cache, bot PAT, workspace, AsanaClient."""
        client_cm = MagicMock()
        client_cm.__aenter__ = AsyncMock(return_value=MagicMock())
        client_cm.__aexit__ = AsyncMock(return_value=False)
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
                return_value=client_cm,
            ),
        ]

    async def test_full_coverage_warms_all_68_keys(
        self, mock_cache: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A clean run (chunking disabled) warms every enumerated key, rate 1.0.

        ADR-3: the reconciled set is 34 GIDs x 2 arms = 68 keys. Chunking is
        disabled (ASANA_WARMER_KEY_BUDGET=0) so the whole set is attempted in one
        link -- the single-invocation full-coverage path. The default budget
        (16) chunks instead; that path is covered by test_key_budget_chunking_*.
        """
        from autom8_asana.lambda_handlers.cache_warmer import (
            _prematerialize_bulk_set_async,
        )

        monkeypatch.setenv("ASANA_WARMER_KEY_BUDGET", "0")

        async def fake_warm_key(
            self: object, project_gid: str, entity_type: str, client: object
        ) -> object:
            from autom8_asana.cache.dataframe.warmer import WarmResult, WarmStatus

            return WarmStatus(
                entity_type=entity_type,
                result=WarmResult.SUCCESS,
                project_gid=project_gid,
                row_count=10,
            )

        checkpoint_mgr = MagicMock()
        checkpoint_mgr.load_async = AsyncMock(return_value=None)
        checkpoint_mgr.save_async = AsyncMock()
        checkpoint_mgr.clear_async = AsyncMock(return_value=True)

        with contextlib.ExitStack() as stack:
            for p in self._patches(mock_cache):
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
            response = await _prematerialize_bulk_set_async(context=None)

        assert response.success is True
        assert "warmer_coverage_rate=1.0000" in response.message
        assert len(response.entity_results) == 68
        # Coverage emitted with completed==total==68 (materialized count).
        emit_cov.assert_called_once_with(68, 68)
        checkpoint_mgr.clear_async.assert_awaited_once()
        # Full materialization attests durable coverage to the re-gate.
        assert response.checkpoint_cleared is True

    async def test_partial_coverage_reports_gap(
        self, mock_cache: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A failing arm yields success=False and coverage < 1.0 (chunking off)."""
        from autom8_asana.lambda_handlers.cache_warmer import (
            _prematerialize_bulk_set_async,
        )

        monkeypatch.setenv("ASANA_WARMER_KEY_BUDGET", "0")

        async def fake_warm_key(
            self: object, project_gid: str, entity_type: str, client: object
        ) -> object:
            from autom8_asana.cache.dataframe.warmer import WarmResult, WarmStatus

            if entity_type == "section":
                return WarmStatus(
                    entity_type=entity_type,
                    result=WarmResult.FAILURE,
                    project_gid=project_gid,
                    error="boom",
                )
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
            for p in self._patches(mock_cache):
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
                    return_value=0.5,
                )
            )
            response = await _prematerialize_bulk_set_async(context=None)

        assert response.success is False
        # 34 project arms warmed, 34 section arms failed -> 34/68 completed.
        emit_cov.assert_called_once_with(34, 68)
        # A gap must NOT clear the checkpoint (the pending tail must survive).
        checkpoint_mgr.clear_async.assert_not_awaited()
        assert response.checkpoint_cleared is False

    async def test_key_budget_chunks_and_self_invokes(
        self, mock_cache: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ADR-3 §3.2(b): a small key budget proactively chunks + self-invokes.

        With budget=4 and 68 keys, the first link warms exactly 4 keys then hands
        off the tail via the bulk-flagged continuation -- the EXPECTED path that
        prevents OOM by bounding per-link memory, NOT a post-OOM finalizer.
        """
        from autom8_asana.lambda_handlers.cache_warmer import (
            _prematerialize_bulk_set_async,
        )

        monkeypatch.setenv("ASANA_WARMER_KEY_BUDGET", "4")

        async def fake_warm_key(
            self: object, project_gid: str, entity_type: str, client: object
        ) -> object:
            from autom8_asana.cache.dataframe.warmer import WarmResult, WarmStatus

            return WarmStatus(
                entity_type=entity_type,
                result=WarmResult.SUCCESS,
                project_gid=project_gid,
                row_count=10,
            )

        checkpoint_mgr = MagicMock()
        checkpoint_mgr.load_async = AsyncMock(return_value=None)
        checkpoint_mgr.save_async = AsyncMock()
        checkpoint_mgr.clear_async = AsyncMock(return_value=True)

        with contextlib.ExitStack() as stack:
            for p in self._patches(mock_cache):
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
            self_invoke = stack.enter_context(
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer._self_invoke_continuation",
                )
            )
            stack.enter_context(
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer.emit_warmer_coverage_rate",
                    return_value=4 / 68,
                )
            )
            response = await _prematerialize_bulk_set_async(context=None)

        assert response.success is False
        assert "self-continuing (key_budget)" in response.message
        # Exactly the budget was warmed before handoff.
        assert len(response.entity_results) == 4
        # The continuation carries the bulk flag and the 64-key pending tail.
        self_invoke.assert_called_once()
        assert self_invoke.call_args.kwargs["prematerialize_bulk_set"] is True
        pending = self_invoke.call_args.args[1]
        assert len(pending) == 64
        # A chunk handoff must NOT clear the checkpoint.
        checkpoint_mgr.clear_async.assert_not_awaited()

    async def test_key_budget_zero_disables_chunking(
        self, mock_cache: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A budget <= 0 processes the whole set in one link (no chunk handoff)."""
        from autom8_asana.lambda_handlers.cache_warmer import (
            _prematerialize_bulk_set_async,
        )

        monkeypatch.setenv("ASANA_WARMER_KEY_BUDGET", "-1")

        async def fake_warm_key(
            self: object, project_gid: str, entity_type: str, client: object
        ) -> object:
            from autom8_asana.cache.dataframe.warmer import WarmResult, WarmStatus

            return WarmStatus(
                entity_type=entity_type,
                result=WarmResult.SUCCESS,
                project_gid=project_gid,
                row_count=10,
            )

        checkpoint_mgr = MagicMock()
        checkpoint_mgr.load_async = AsyncMock(return_value=None)
        checkpoint_mgr.save_async = AsyncMock()
        checkpoint_mgr.clear_async = AsyncMock(return_value=True)

        with contextlib.ExitStack() as stack:
            for p in self._patches(mock_cache):
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
            self_invoke = stack.enter_context(
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer._self_invoke_continuation",
                )
            )
            stack.enter_context(
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer.emit_warmer_coverage_rate",
                    return_value=1.0,
                )
            )
            response = await _prematerialize_bulk_set_async(context=None)

        assert response.success is True
        assert len(response.entity_results) == 68
        self_invoke.assert_not_called()
        checkpoint_mgr.clear_async.assert_awaited_once()

    async def test_timeout_self_invokes_with_bulk_flag(self, mock_cache: MagicMock) -> None:
        """On timeout, the continuation carries prematerialize_bulk_set=True."""
        from autom8_asana.lambda_handlers.cache_warmer import (
            _prematerialize_bulk_set_async,
        )

        # Context that always signals timeout -> exits on the first key.
        context = MockLambdaContext(remaining_time_ms=0)

        checkpoint_mgr = MagicMock()
        checkpoint_mgr.load_async = AsyncMock(return_value=None)
        checkpoint_mgr.save_async = AsyncMock()
        checkpoint_mgr.clear_async = AsyncMock(return_value=True)

        with contextlib.ExitStack() as stack:
            for p in self._patches(mock_cache):
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
            response = await _prematerialize_bulk_set_async(context=context)

        assert response.success is False
        assert "self-continuing" in response.message
        # Self-invoke called with the bulk flag so the next invocation re-enters
        # the bulk branch (not the offer-domain warm).
        self_invoke.assert_called_once()
        assert self_invoke.call_args.kwargs["prematerialize_bulk_set"] is True
        checkpoint_mgr.save_async.assert_awaited()

    async def test_no_cache_returns_failure(self) -> None:
        """No cache -> failure response, no enumeration attempted."""
        from autom8_asana.lambda_handlers.cache_warmer import (
            _prematerialize_bulk_set_async,
        )

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=None,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.initialize_dataframe_cache",
                return_value=None,
            ),
        ):
            response = await _prematerialize_bulk_set_async(context=None)

        assert response.success is False
        assert "Failed to initialize DataFrameCache" in response.message


class TestHandlerBulkRouting:
    """The prematerialize_bulk_set flag routes to the bulk branch."""

    async def test_handler_async_routes_to_bulk(self) -> None:
        mock_response = WarmResponse(success=True, message="ok")
        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._prematerialize_bulk_set_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_bulk:
            result = await handler_async({"prematerialize_bulk_set": True})

        assert result["statusCode"] == 200
        mock_bulk.assert_called_once_with(
            resume_from_checkpoint=True,
            context=None,
        )

    def test_handler_routes_to_bulk(self) -> None:
        mock_response = WarmResponse(success=True, message="ok")
        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._prematerialize_bulk_set_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_bulk:
            result = handler({"prematerialize_bulk_set": True}, None)

        assert result["statusCode"] == 200
        mock_bulk.assert_called_once()


class TestPrematerializeFastSet:
    """Tests for the SRE fast lane: _prematerialize_bulk_set_async over the 4-key
    fast source. Mirrors TestPrematerializeBulkSet but with the heavy subset."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        cache = MagicMock()
        cache.put_async = AsyncMock()
        return cache

    def _patches(self, mock_cache: MagicMock) -> list:
        """Common patch set: cache, bot PAT, workspace, AsanaClient."""
        client_cm = MagicMock()
        client_cm.__aenter__ = AsyncMock(return_value=MagicMock())
        client_cm.__aexit__ = AsyncMock(return_value=False)
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
                return_value=client_cm,
            ),
        ]

    async def test_full_coverage_warms_all_4_keys(
        self, mock_cache: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A clean fast-lane run warms exactly the 4 heavy keys over its own
        denominator -- WarmerCheckpointCleared/coverage are emitted as (4, 4)."""
        from autom8_asana.core.project_registry import (
            fast_lane_prematerialization_keys,
        )
        from autom8_asana.lambda_handlers.cache_warmer import (
            _prematerialize_bulk_set_async,
        )

        monkeypatch.setenv("ASANA_WARMER_KEY_BUDGET", "0")

        async def fake_warm_key(
            self: object, project_gid: str, entity_type: str, client: object
        ) -> object:
            from autom8_asana.cache.dataframe.warmer import WarmResult, WarmStatus

            return WarmStatus(
                entity_type=entity_type,
                result=WarmResult.SUCCESS,
                project_gid=project_gid,
                row_count=10,
            )

        checkpoint_mgr = MagicMock()
        checkpoint_mgr.load_async = AsyncMock(return_value=None)
        checkpoint_mgr.save_async = AsyncMock()
        checkpoint_mgr.clear_async = AsyncMock(return_value=True)

        with contextlib.ExitStack() as stack:
            for p in self._patches(mock_cache):
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
                key_source=fast_lane_prematerialization_keys,
                fast_lane=True,
            )

        assert response.success is True
        assert "warmer_coverage_rate=1.0000" in response.message
        # The fast lane's denominator is 4, NOT the 68-key bulk sweep.
        assert len(response.entity_results) == 4
        emit_cov.assert_called_once_with(4, 4)
        checkpoint_mgr.clear_async.assert_awaited_once()
        # checkpoint_cleared True over the 4-key denominator (WarmerCheckpointCleared).
        assert response.checkpoint_cleared is True

    async def test_timeout_self_invokes_with_fast_flag(
        self, mock_cache: MagicMock
    ) -> None:
        """On timeout, the fast-lane continuation carries prematerialize_fast_set=True
        and NOT prematerialize_bulk_set -- it must re-enter the fast branch."""
        from autom8_asana.core.project_registry import (
            fast_lane_prematerialization_keys,
        )
        from autom8_asana.lambda_handlers.cache_warmer import (
            _prematerialize_bulk_set_async,
        )

        context = MockLambdaContext(remaining_time_ms=0)

        checkpoint_mgr = MagicMock()
        checkpoint_mgr.load_async = AsyncMock(return_value=None)
        checkpoint_mgr.save_async = AsyncMock()
        checkpoint_mgr.clear_async = AsyncMock(return_value=True)

        with contextlib.ExitStack() as stack:
            for p in self._patches(mock_cache):
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
                key_source=fast_lane_prematerialization_keys,
                fast_lane=True,
            )

        assert response.success is False
        assert "self-continuing" in response.message
        self_invoke.assert_called_once()
        # Lane isolation: fast continuation routes to the fast branch, never bulk.
        assert self_invoke.call_args.kwargs["prematerialize_fast_set"] is True
        assert self_invoke.call_args.kwargs["prematerialize_bulk_set"] is False
        checkpoint_mgr.save_async.assert_awaited()


class TestHandlerFastRouting:
    """The prematerialize_fast_set flag routes to the fast lane with the 4-key source."""

    async def test_handler_async_routes_to_fast(self) -> None:
        from autom8_asana.core.project_registry import (
            fast_lane_prematerialization_keys,
        )

        mock_response = WarmResponse(success=True, message="ok")
        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._prematerialize_bulk_set_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_fast:
            result = await handler_async({"prematerialize_fast_set": True})

        assert result["statusCode"] == 200
        mock_fast.assert_called_once_with(
            resume_from_checkpoint=True,
            context=None,
            key_source=fast_lane_prematerialization_keys,
            fast_lane=True,
        )

    def test_handler_routes_to_fast(self) -> None:
        from autom8_asana.core.project_registry import (
            fast_lane_prematerialization_keys,
        )

        mock_response = WarmResponse(success=True, message="ok")
        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._prematerialize_bulk_set_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_fast:
            result = handler({"prematerialize_fast_set": True}, None)

        assert result["statusCode"] == 200
        mock_fast.assert_called_once()
        assert mock_fast.call_args.kwargs["fast_lane"] is True
        assert (
            mock_fast.call_args.kwargs["key_source"]
            is fast_lane_prematerialization_keys
        )

    def test_fast_flag_takes_precedence_over_bulk(self) -> None:
        """If both flags are set, fast wins (mutually-exclusive lanes; fast first)."""
        mock_response = WarmResponse(success=True, message="ok")
        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._prematerialize_bulk_set_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_pre:
            result = handler(
                {"prematerialize_fast_set": True, "prematerialize_bulk_set": True},
                None,
            )

        assert result["statusCode"] == 200
        # Fast branch is evaluated first; it injects the fast source.
        assert mock_pre.call_args.kwargs.get("fast_lane") is True


# ============================================================================
# Tests for Timeout Detection (per TDD-lambda-cache-warmer Section 3.2)
# ============================================================================


class MockLambdaContext:
    """Mock Lambda context for testing timeout detection."""

    def __init__(self, remaining_time_ms: int = 300_000, request_id: str = "test-123"):
        """Initialize mock context.

        Args:
            remaining_time_ms: Remaining time in milliseconds.
            request_id: Lambda request ID for correlation.
        """
        self._remaining_time_ms = remaining_time_ms
        self.aws_request_id = request_id

    def get_remaining_time_in_millis(self) -> int:
        """Return mock remaining time."""
        return self._remaining_time_ms


class TestShouldExitEarly:
    """Tests for _should_exit_early timeout detection function."""

    def test_returns_true_when_remaining_less_than_buffer(self) -> None:
        """Handler exits when remaining time < buffer (2 minutes)."""
        context = MockLambdaContext(remaining_time_ms=60_000)  # 1 minute
        assert _should_exit_early(context) is True

    def test_returns_true_at_exactly_buffer_minus_one(self) -> None:
        """Handler exits when remaining time is just under buffer."""
        context = MockLambdaContext(remaining_time_ms=TIMEOUT_BUFFER_MS - 1)
        assert _should_exit_early(context) is True

    def test_returns_false_when_remaining_equals_buffer(self) -> None:
        """Handler continues when remaining time equals buffer."""
        context = MockLambdaContext(remaining_time_ms=TIMEOUT_BUFFER_MS)
        assert _should_exit_early(context) is False

    def test_returns_false_when_sufficient_time(self) -> None:
        """Handler continues when remaining time > buffer."""
        context = MockLambdaContext(remaining_time_ms=300_000)  # 5 minutes
        assert _should_exit_early(context) is False

    def test_returns_false_when_context_is_none(self) -> None:
        """Handler continues when context is None (no timeout enforcement)."""
        assert _should_exit_early(None) is False

    def test_returns_false_when_context_lacks_method(self) -> None:
        """Handler continues when context lacks get_remaining_time_in_millis."""
        context = MagicMock(spec=[])  # No methods
        assert _should_exit_early(context) is False

    def test_returns_true_when_remaining_time_is_zero(self) -> None:
        """Handler exits immediately when remaining time is 0ms (GAP-001)."""
        context = MockLambdaContext(remaining_time_ms=0)
        assert _should_exit_early(context) is True

    def test_returns_true_when_remaining_time_is_one_ms(self) -> None:
        """Handler exits when remaining time is 1ms (near-immediate timeout)."""
        context = MockLambdaContext(remaining_time_ms=1)
        assert _should_exit_early(context) is True


# ============================================================================
# Tests for CloudWatch Metric Emission (per TDD-lambda-cache-warmer Section 5.2)
# ============================================================================


class TestEmitMetric:
    """Tests for emit_metric CloudWatch helper (shared cloudwatch module)."""

    def test_emits_metric_with_dimensions(self) -> None:
        """Metric is emitted with environment and custom dimensions."""
        mock_client = MagicMock()
        mock_settings = MagicMock()
        mock_settings.observability.environment = "test-env"
        mock_settings.observability.cloudwatch_namespace = "autom8/lambda"

        with (
            patch(
                "autom8_asana.lambda_handlers.cloudwatch._get_cloudwatch_client",
                return_value=mock_client,
            ),
            patch(
                "autom8_asana.settings.get_settings",
                return_value=mock_settings,
            ),
        ):
            emit_metric(
                metric_name="WarmSuccess",
                value=1,
                dimensions={"entity_type": "unit"},
            )

        mock_client.put_metric_data.assert_called_once()
        call_args = mock_client.put_metric_data.call_args
        metric_data = call_args.kwargs["MetricData"][0]

        assert metric_data["MetricName"] == "WarmSuccess"
        assert metric_data["Value"] == 1
        assert metric_data["Unit"] == "Count"

        # Check dimensions include environment and entity_type
        dim_dict = {d["Name"]: d["Value"] for d in metric_data["Dimensions"]}
        assert dim_dict["environment"] == "test-env"
        assert dim_dict["entity_type"] == "unit"

    def test_emits_metric_without_extra_dimensions(self) -> None:
        """Metric is emitted with only environment dimension."""
        mock_client = MagicMock()

        with patch(
            "autom8_asana.lambda_handlers.cloudwatch._get_cloudwatch_client",
            return_value=mock_client,
        ):
            emit_metric(
                metric_name="TotalDuration",
                value=5000.5,
                unit="Milliseconds",
            )

        mock_client.put_metric_data.assert_called_once()
        call_args = mock_client.put_metric_data.call_args
        metric_data = call_args.kwargs["MetricData"][0]

        assert metric_data["MetricName"] == "TotalDuration"
        assert metric_data["Value"] == 5000.5
        assert metric_data["Unit"] == "Milliseconds"
        assert len(metric_data["Dimensions"]) == 1  # Only environment

    def test_handles_cloudwatch_error_gracefully(self) -> None:
        """CloudWatch errors are logged but don't raise exceptions."""
        mock_client = MagicMock()
        mock_client.put_metric_data.side_effect = Exception("CloudWatch error")

        with patch(
            "autom8_asana.lambda_handlers.cloudwatch._get_cloudwatch_client",
            return_value=mock_client,
        ):
            # Should not raise
            emit_metric(metric_name="WarmSuccess", value=1)

        mock_client.put_metric_data.assert_called_once()


# ============================================================================
# Tests for Checkpoint Integration (per TDD-lambda-cache-warmer Section 3.6)
# ============================================================================


class TestCheckpointIntegration:
    """Tests for checkpoint-based resume functionality."""

    @pytest.fixture
    def mock_checkpoint_manager(self) -> MagicMock:
        """Create a mock CheckpointManager."""
        mgr = MagicMock()
        mgr.load_async = AsyncMock(return_value=None)
        mgr.save_async = AsyncMock(return_value=True)
        mgr.clear_async = AsyncMock(return_value=True)
        return mgr

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create a mock DataFrameCache."""
        cache = MagicMock()
        cache.put_async = AsyncMock()
        return cache

    async def test_resumes_from_fresh_checkpoint(
        self,
        mock_checkpoint_manager: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Warming resumes from checkpoint when fresh checkpoint exists."""
        from autom8_asana.lambda_handlers.checkpoint import CheckpointRecord

        # Create a fresh checkpoint with unit completed
        now = datetime.now(UTC)
        checkpoint = CheckpointRecord(
            invocation_id="prior-123",
            completed_entities=["unit"],
            pending_entities=["business", "offer", "contact"],
            entity_results=[
                {
                    "entity_type": "unit",
                    "result": "success",
                    "row_count": 100,
                }
            ],
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
        mock_checkpoint_manager.load_async.return_value = checkpoint

        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = True
        mock_registry.get_project_gid.return_value = "project-123"

        mock_warmer = MagicMock()
        mock_warm_status = MagicMock()
        mock_warm_status.result.name = "SUCCESS"
        mock_warm_status.row_count = 50
        mock_warm_status.to_dict.return_value = {
            "entity_type": "business",
            "result": "success",
            "row_count": 50,
        }
        mock_warmer.warm_entity_async = AsyncMock(return_value=mock_warm_status)

        with (
            patch.dict(
                "os.environ",
                {
                    "ASANA_WORKSPACE_GID": "workspace-123",
                    "ASANA_CACHE_S3_BUCKET": "test-bucket",
                },
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=mock_registry,
            ),
            patch(
                "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
                return_value=mock_checkpoint_manager,
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test-pat",
            ),
            patch(
                "autom8_asana.cache.dataframe.warmer.CacheWarmer",
                return_value=mock_warmer,
            ),
            patch(
                "autom8_asana.AsanaClient",
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer.emit_metric",
            ),
        ):
            await _warm_cache_async(
                resume_from_checkpoint=True,
                context=MockLambdaContext(remaining_time_ms=600_000),
            )

        # Verify checkpoint was loaded
        mock_checkpoint_manager.load_async.assert_called_once()

    async def test_ignores_stale_checkpoint(self) -> None:
        """Warming ignores stale checkpoint."""
        from autom8_asana.lambda_handlers.checkpoint import CheckpointRecord

        # Create a stale checkpoint
        old_time = datetime.now(UTC) - timedelta(hours=2)
        stale_checkpoint = CheckpointRecord(
            invocation_id="old-123",
            completed_entities=["unit"],
            pending_entities=["business"],
            entity_results=[],
            created_at=old_time,
            expires_at=old_time + timedelta(hours=1),
        )

        # is_stale() should return True for this checkpoint
        assert stale_checkpoint.is_stale() is True

    async def test_saves_checkpoint_on_timeout(
        self,
        mock_checkpoint_manager: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Checkpoint is saved when timeout approaches."""
        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = True
        mock_registry.get_project_gid.return_value = "project-123"

        # Context that will trigger early exit
        context = MockLambdaContext(remaining_time_ms=60_000)  # 1 minute

        with (
            patch.dict(
                "os.environ",
                {
                    "ASANA_WORKSPACE_GID": "workspace-123",
                    "ASANA_CACHE_S3_BUCKET": "test-bucket",
                },
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=mock_registry,
            ),
            patch(
                "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
                return_value=mock_checkpoint_manager,
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test-pat",
            ),
            patch(
                "autom8_asana.AsanaClient",
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer.emit_metric",
            ),
        ):
            response = await _warm_cache_async(
                resume_from_checkpoint=False,  # Start fresh
                context=context,
            )

        # Should have partial completion due to timeout
        assert response.success is False
        assert "timeout" in response.message.lower() or "Partial" in response.message

        # Checkpoint should have been saved
        mock_checkpoint_manager.save_async.assert_called()

    async def test_clears_checkpoint_on_success(
        self,
        mock_checkpoint_manager: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Checkpoint is cleared on successful completion."""
        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = True
        mock_registry.get_project_gid.return_value = "project-123"

        mock_warmer = MagicMock()
        mock_warm_status = MagicMock()
        mock_warm_status.result.name = "SUCCESS"
        mock_warm_status.row_count = 100
        mock_warm_status.error = None
        mock_warm_status.to_dict.return_value = {
            "entity_type": "unit",
            "result": "success",
            "row_count": 100,
        }
        mock_warmer.warm_entity_async = AsyncMock(return_value=mock_warm_status)

        # Sufficient time context
        context = MockLambdaContext(remaining_time_ms=600_000)

        with (
            patch.dict(
                "os.environ",
                {
                    "ASANA_WORKSPACE_GID": "workspace-123",
                    "ASANA_CACHE_S3_BUCKET": "test-bucket",
                },
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            ),
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=mock_registry,
            ),
            patch(
                "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
                return_value=mock_checkpoint_manager,
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test-pat",
            ),
            patch(
                "autom8_asana.cache.dataframe.warmer.CacheWarmer",
                return_value=mock_warmer,
            ),
            patch(
                "autom8_asana.cache.dataframe.warmer.WarmResult",
            ) as mock_warm_result,
            patch(
                "autom8_asana.AsanaClient",
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer.emit_metric",
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._push_gid_mappings_for_completed_entities",
                new_callable=AsyncMock,
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._push_account_status_for_completed_entities",
                new_callable=AsyncMock,
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._warm_story_caches_for_completed_entities",
                new_callable=AsyncMock,
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._run_vertical_backfill",
                new_callable=AsyncMock,
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._aggregate_pipeline_stages",
                new_callable=AsyncMock,
            ),
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._run_reconciliation_shadow",
                new_callable=AsyncMock,
            ),
        ):
            # Make WarmResult.SUCCESS comparison work
            mock_warm_result.SUCCESS = mock_warm_status.result

            response = await _warm_cache_async(
                entity_types=["unit"],  # Single entity for faster test
                resume_from_checkpoint=False,
                context=context,
            )

        # Should have been successful
        assert response.success is True
        assert response.checkpoint_cleared is True

        # Checkpoint should have been cleared
        mock_checkpoint_manager.clear_async.assert_called_once()


# ============================================================================
# Tests for Handler Context Passing
# ============================================================================


class TestHandlerContextPassing:
    """Tests for handler functions passing context correctly."""

    def test_handler_passes_context_to_warm_async(self) -> None:
        """Handler passes Lambda context to _warm_cache_async."""
        mock_response = WarmResponse(
            success=True,
            message="Cache warm complete",
        )
        context = MockLambdaContext(remaining_time_ms=300_000, request_id="req-456")

        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._warm_cache_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_warm:
            handler({}, context)

        mock_warm.assert_called_once_with(
            entity_types=None,
            strict=True,
            resume_from_checkpoint=True,
            context=context,
        )

    def test_handler_passes_resume_from_checkpoint_false(self) -> None:
        """Handler passes resume_from_checkpoint=False when specified."""
        mock_response = WarmResponse(
            success=True,
            message="Cache warm complete",
        )

        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._warm_cache_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_warm:
            handler({"resume_from_checkpoint": False}, None)

        mock_warm.assert_called_once_with(
            entity_types=None,
            strict=True,
            resume_from_checkpoint=False,
            context=None,
        )

    async def test_handler_async_passes_context(self) -> None:
        """Async handler passes Lambda context to _warm_cache_async."""
        mock_response = WarmResponse(
            success=True,
            message="Cache warm complete",
        )
        context = MockLambdaContext(remaining_time_ms=300_000, request_id="req-789")

        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._warm_cache_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_warm:
            await handler_async({}, context)

        mock_warm.assert_called_once_with(
            entity_types=None,
            strict=True,
            resume_from_checkpoint=True,
            context=context,
        )


# ============================================================================
# Tests for WarmResponse Extended Fields
# ============================================================================


class TestWarmResponseExtended:
    """Tests for WarmResponse checkpoint_cleared and invocation_id fields."""

    def test_to_dict_includes_checkpoint_cleared(self) -> None:
        """WarmResponse.to_dict() includes checkpoint_cleared field."""
        response = WarmResponse(
            success=True,
            message="Cache warm complete",
            checkpoint_cleared=True,
        )

        result = response.to_dict()
        assert result["checkpoint_cleared"] is True

    def test_to_dict_includes_invocation_id(self) -> None:
        """WarmResponse.to_dict() includes invocation_id field."""
        response = WarmResponse(
            success=True,
            message="Cache warm complete",
            invocation_id="test-invoke-123",
        )

        result = response.to_dict()
        assert result["invocation_id"] == "test-invoke-123"

    def test_defaults_for_new_fields(self) -> None:
        """New fields have correct defaults."""
        response = WarmResponse(
            success=True,
            message="Cache warm complete",
        )

        assert response.checkpoint_cleared is False
        assert response.invocation_id is None


# ============================================================================
# Tests for Reconciliation Shadow Mode (Phase 5 - Project Ignition)
# ============================================================================


class TestReconciliationShadowIntegration:
    """Tests for reconciliation shadow mode integration in cache warmer.

    Verifies that _run_reconciliation_shadow is called as Phase 5 of the
    post-warm sequence with the correct arguments, and that failures in
    shadow mode do not affect the cache warmer's WarmResponse.
    """

    def _build_warm_stack(
        self,
        shadow_mock: AsyncMock,
    ) -> contextlib.ExitStack:
        """Build an ExitStack with all patches for a successful single-entity warm.

        Returns an un-entered ExitStack. Caller must use it as a context
        manager. Sets self._warm_status for WarmResult comparison setup.
        """
        mock_checkpoint_mgr = MagicMock()
        mock_checkpoint_mgr.load_async = AsyncMock(return_value=None)
        mock_checkpoint_mgr.save_async = AsyncMock(return_value=True)
        mock_checkpoint_mgr.clear_async = AsyncMock(return_value=True)

        mock_cache = MagicMock()
        mock_cache.put_async = AsyncMock()

        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = True
        mock_registry.get_project_gid.return_value = "project-123"

        mock_warm_status = MagicMock()
        mock_warm_status.result.name = "SUCCESS"
        mock_warm_status.row_count = 100
        mock_warm_status.error = None
        mock_warm_status.to_dict.return_value = {
            "entity_type": "unit",
            "result": "success",
            "row_count": 100,
        }
        self._warm_status = mock_warm_status

        mock_warmer = MagicMock()
        mock_warmer.warm_entity_async = AsyncMock(return_value=mock_warm_status)

        stack = contextlib.ExitStack()
        stack.enter_context(
            patch.dict(
                "os.environ",
                {
                    "ASANA_WORKSPACE_GID": "workspace-123",
                    "ASANA_CACHE_S3_BUCKET": "test-bucket",
                },
            )
        )
        stack.enter_context(
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=mock_cache,
            )
        )
        stack.enter_context(
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=mock_registry,
            )
        )
        stack.enter_context(
            patch(
                "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
                return_value=mock_checkpoint_mgr,
            )
        )
        stack.enter_context(
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test-pat",
            )
        )
        stack.enter_context(
            patch(
                "autom8_asana.cache.dataframe.warmer.CacheWarmer",
                return_value=mock_warmer,
            )
        )
        stack.enter_context(patch("autom8_asana.cache.dataframe.warmer.WarmResult"))
        stack.enter_context(patch("autom8_asana.AsanaClient"))
        stack.enter_context(patch("autom8_asana.lambda_handlers.cache_warmer.emit_metric"))
        stack.enter_context(
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._push_gid_mappings_for_completed_entities",
                new_callable=AsyncMock,
            )
        )
        stack.enter_context(
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._push_account_status_for_completed_entities",
                new_callable=AsyncMock,
            )
        )
        stack.enter_context(
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._warm_story_caches_for_completed_entities",
                new_callable=AsyncMock,
            )
        )
        stack.enter_context(
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._run_vertical_backfill",
                new_callable=AsyncMock,
            )
        )
        stack.enter_context(
            patch(
                "autom8_asana.lambda_handlers.cache_warmer._run_reconciliation_shadow",
                new=shadow_mock,
            )
        )
        return stack

    async def test_shadow_called_with_correct_args(self) -> None:
        """_run_reconciliation_shadow is called with the right arguments after warming."""
        shadow_mock = AsyncMock()
        stack = self._build_warm_stack(shadow_mock)

        with stack:
            from autom8_asana.cache.dataframe import warmer as warmer_mod

            warmer_mod.WarmResult.SUCCESS = self._warm_status.result

            context = MockLambdaContext(remaining_time_ms=600_000)
            response = await _warm_cache_async(
                entity_types=["unit"],
                resume_from_checkpoint=False,
                context=context,
            )

        assert response.success is True
        shadow_mock.assert_called_once()
        call_kwargs = shadow_mock.call_args.kwargs
        assert "unit" in call_kwargs["completed_entities"]
        assert call_kwargs["cache"] is not None
        assert call_kwargs["get_project_gid"] is not None
        assert call_kwargs["invocation_id"] is not None

    async def test_shadow_exception_does_not_propagate(self) -> None:
        """An exception in _run_reconciliation_shadow does not propagate as unhandled.

        The runner's internal try/except handles errors in production. This
        test verifies that even if the mock bypasses that guard and raises
        directly, the cache warmer's top-level try/except still returns a
        WarmResponse (no raw exception escapes _warm_cache_async).
        """
        shadow_mock = AsyncMock(
            side_effect=RuntimeError("Reconciliation engine exploded"),
        )
        stack = self._build_warm_stack(shadow_mock)

        with stack:
            from autom8_asana.cache.dataframe import warmer as warmer_mod

            warmer_mod.WarmResult.SUCCESS = self._warm_status.result

            context = MockLambdaContext(remaining_time_ms=600_000)
            response = await _warm_cache_async(
                entity_types=["unit"],
                resume_from_checkpoint=False,
                context=context,
            )

        shadow_mock.assert_called_once()
        # Top-level except returns a WarmResponse -- no unhandled crash
        assert isinstance(response, WarmResponse)

    async def test_shadow_called_even_when_flag_not_set(self) -> None:
        """The cache warmer always calls _run_reconciliation_shadow.

        The feature flag check is inside the runner itself, not in the
        cache warmer. The warmer simply calls it; the runner returns early
        when the flag is not set.
        """
        shadow_mock = AsyncMock()
        stack = self._build_warm_stack(shadow_mock)

        with stack:
            from autom8_asana.cache.dataframe import warmer as warmer_mod

            warmer_mod.WarmResult.SUCCESS = self._warm_status.result

            context = MockLambdaContext(remaining_time_ms=600_000)
            response = await _warm_cache_async(
                entity_types=["unit"],
                resume_from_checkpoint=False,
                context=context,
            )

        assert response.success is True
        # Shadow is called regardless -- the env var guard is inside the runner
        shadow_mock.assert_called_once()
