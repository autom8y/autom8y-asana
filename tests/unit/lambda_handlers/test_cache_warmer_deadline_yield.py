"""F1a pacing teeth: a WarmDeadlineExceeded from a warm becomes a GRACEFUL continue.

This is the sawtooth cure at the orchestration boundary. When a key/entity warm rides a
429 storm into the deadline, the transport retry loop raises WarmDeadlineExceeded; the
warmer must catch it and do the SAME checkpoint + self-invoke it does on the per-item
timeout branch -- turning a would-be SIGKILL strand (no checkpoint, no continuation, frame
stale for hours) into a graceful continue that re-arms the sweep.

RED-AGAINST-MAIN: origin/main has no WarmDeadlineExceeded catch, so a BaseException raised
from the warm would propagate straight out of the handler (the broad `except Exception`
cannot catch a BaseException) -- NO checkpoint, NO self-invoke. The explicit orchestration
catch is the diff that produces the graceful WarmResponse asserted below.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.core.warm_deadline import WarmDeadlineExceeded, disarm_warm_deadline
from autom8_asana.lambda_handlers.cache_warmer import (
    _prematerialize_bulk_set_async,
    _warm_cache_async,
)


class MockLambdaContext:
    def __init__(self, remaining_time_ms: int = 600_000, request_id: str = "test-123"):
        self._remaining_time_ms = remaining_time_ms
        self.aws_request_id = request_id
        self.invoked_function_arn = (
            "arn:aws:lambda:us-east-1:123:function:autom8-asana-cache-warmer-bulk"
        )

    def get_remaining_time_in_millis(self) -> int:
        return self._remaining_time_ms


@pytest.fixture(autouse=True)
def _disarm():
    disarm_warm_deadline()
    yield
    disarm_warm_deadline()


@pytest.fixture
def mock_checkpoint_manager() -> MagicMock:
    mgr = MagicMock()
    mgr.load_async = AsyncMock(return_value=None)
    mgr.save_async = AsyncMock(return_value=True)
    mgr.clear_async = AsyncMock(return_value=True)
    return mgr


@pytest.mark.asyncio
async def test_offer_domain_warm_yields_gracefully_on_deadline(mock_checkpoint_manager):
    """_warm_cache_async: WarmDeadlineExceeded -> checkpoint + self-invoke, not a strand."""
    mock_cache = MagicMock()
    mock_registry = MagicMock()
    mock_registry.is_ready.return_value = True
    mock_registry.get_project_gid.return_value = "project-123"

    mock_warmer = MagicMock()
    # The warm rides a 429 storm into the deadline: the transport loop raised the signal.
    mock_warmer.warm_entity_async = AsyncMock(side_effect=WarmDeadlineExceeded("storm"))

    context = MockLambdaContext(remaining_time_ms=600_000)

    with (
        patch.dict(
            "os.environ",
            {"ASANA_WORKSPACE_GID": "workspace-123", "ASANA_CACHE_S3_BUCKET": "test-bucket"},
        ),
        patch("autom8_asana.cache.dataframe.factory.get_dataframe_cache", return_value=mock_cache),
        patch(
            "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
            return_value=mock_registry,
        ),
        patch(
            "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
            return_value=mock_checkpoint_manager,
        ),
        patch("autom8_asana.auth.bot_pat.get_bot_pat", return_value="test-pat"),
        patch("autom8_asana.cache.dataframe.warmer.CacheWarmer", return_value=mock_warmer),
        patch("autom8_asana.AsanaClient"),
        patch(
            "autom8_asana.lambda_handlers.cache_warmer._self_invoke_continuation"
        ) as mock_self_invoke,
        patch("autom8_asana.lambda_handlers.cache_warmer.emit_metric") as mock_metric,
    ):
        response = await _warm_cache_async(
            entity_types=["offer"],
            strict=False,
            resume_from_checkpoint=False,
            context=context,
        )

    # Graceful continue -- NOT a strand.
    assert response.success is False
    assert "self-continuing (deadline)" in response.message
    mock_checkpoint_manager.save_async.assert_awaited()  # pending tail checkpointed
    mock_self_invoke.assert_called_once()  # continuation fired
    metric_names = [c.args[0] for c in mock_metric.call_args_list]
    assert "WarmerDeadlineYield" in metric_names


@pytest.mark.asyncio
async def test_bulk_premat_yields_gracefully_on_deadline(mock_checkpoint_manager):
    """_prematerialize_bulk_set_async: WarmDeadlineExceeded -> _checkpoint_and_continue."""
    mock_cache = MagicMock()

    mock_warmer = MagicMock()
    mock_warmer.warm_key_async = AsyncMock(side_effect=WarmDeadlineExceeded("storm"))

    context = MockLambdaContext(remaining_time_ms=600_000)

    with (
        patch.dict(
            "os.environ",
            {"ASANA_WORKSPACE_GID": "workspace-123", "ASANA_CACHE_S3_BUCKET": "test-bucket"},
        ),
        patch("autom8_asana.cache.dataframe.factory.get_dataframe_cache", return_value=mock_cache),
        patch(
            "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
            return_value=mock_checkpoint_manager,
        ),
        patch("autom8_asana.auth.bot_pat.get_bot_pat", return_value="test-pat"),
        patch(
            "autom8_asana.lambda_handlers.cache_warmer.resolve_secret_from_env",
            return_value="workspace-123",
        ),
        patch("autom8_asana.cache.dataframe.warmer.CacheWarmer", return_value=mock_warmer),
        patch("autom8_asana.AsanaClient"),
        patch(
            "autom8_asana.lambda_handlers.cache_warmer._self_invoke_continuation"
        ) as mock_self_invoke,
        patch("autom8_asana.lambda_handlers.cache_warmer.emit_metric") as mock_metric,
    ):
        response = await _prematerialize_bulk_set_async(
            resume_from_checkpoint=False,
            context=context,
        )

    assert response.success is False
    assert "self-continuing (deadline)" in response.message
    mock_checkpoint_manager.save_async.assert_awaited()
    mock_self_invoke.assert_called_once()
    # Bulk lane routes the continuation back into the bulk branch.
    assert mock_self_invoke.call_args.kwargs.get("prematerialize_bulk_set") is True
    metric_names = [c.args[0] for c in mock_metric.call_args_list]
    assert "WarmerDeadlineYield" in metric_names
