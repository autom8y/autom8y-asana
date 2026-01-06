"""Unit tests for cache_warmer Lambda handler.

Per TDD-DATAFRAME-CACHE-001 and TDD-lambda-cache-warmer: Tests for Lambda
warm-up handler including timeout detection, checkpoint integration, and
CloudWatch metric emission.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.lambda_handlers.cache_warmer import (
    TIMEOUT_BUFFER_MS,
    WarmResponse,
    _emit_metric,
    _match_entity_type,
    _normalize_project_name,
    _should_exit_early,
    _warm_cache_async,
    handler,
    handler_async,
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


class TestNormalizeProjectName:
    """Tests for _normalize_project_name function."""

    def test_normalize_business_units(self) -> None:
        """Business Units normalizes to unit."""
        assert _normalize_project_name("Business Units") == "unit"

    def test_normalize_units(self) -> None:
        """Units normalizes to unit."""
        assert _normalize_project_name("Units") == "unit"

    def test_normalize_businesses(self) -> None:
        """Businesses normalizes to business."""
        assert _normalize_project_name("Businesses") == "business"

    def test_normalize_business(self) -> None:
        """Business normalizes to business."""
        assert _normalize_project_name("Business") == "business"

    def test_normalize_offers(self) -> None:
        """Offers normalizes to offer."""
        assert _normalize_project_name("Offers") == "offer"

    def test_normalize_offer(self) -> None:
        """Offer normalizes to offer."""
        assert _normalize_project_name("Offer") == "offer"

    def test_normalize_contacts(self) -> None:
        """Contacts normalizes to contact."""
        assert _normalize_project_name("Contacts") == "contact"

    def test_normalize_contact(self) -> None:
        """Contact normalizes to contact."""
        assert _normalize_project_name("Contact") == "contact"

    def test_normalize_case_insensitive(self) -> None:
        """Normalization is case insensitive."""
        assert _normalize_project_name("BUSINESS UNITS") == "unit"
        assert _normalize_project_name("OFFERS") == "offer"

    def test_normalize_with_whitespace(self) -> None:
        """Normalization handles whitespace."""
        assert _normalize_project_name("  Business Units  ") == "unit"


class TestMatchEntityType:
    """Tests for _match_entity_type function."""

    def test_match_unit(self) -> None:
        """Match Business Units to unit."""
        entity_types = ["unit", "business", "offer", "contact"]
        assert _match_entity_type("Business Units", entity_types) == "unit"

    def test_match_offer(self) -> None:
        """Match Offers to offer."""
        entity_types = ["unit", "business", "offer", "contact"]
        assert _match_entity_type("Offers", entity_types) == "offer"

    def test_no_match(self) -> None:
        """Return None for unmatched project name."""
        entity_types = ["unit", "business", "offer", "contact"]
        assert _match_entity_type("Random Project", entity_types) is None


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
        return pl.DataFrame({
            "gid": ["1", "2", "3"],
            "name": ["Task A", "Task B", "Task C"],
        })

    @pytest.mark.asyncio
    async def test_no_cache_available(self) -> None:
        """Return failure when cache cannot be initialized."""
        # Need to patch where the imports happen (inside the function)
        with patch.dict("os.environ", {}, clear=True), patch(
            "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
            return_value=None,
        ), patch(
            "autom8_asana.cache.dataframe.factory.initialize_dataframe_cache",
            return_value=None,
        ):
            response = await _warm_cache_async()

        assert response.success is False
        assert "Failed to initialize DataFrameCache" in response.message

    @pytest.mark.asyncio
    async def test_registry_not_ready(self, mock_cache: MagicMock) -> None:
        """Return failure when registry not ready and discovery fails."""
        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = False

        with patch.dict("os.environ", {}, clear=True), patch(
            "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
            return_value=mock_cache,
        ), patch(
            "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
            return_value=mock_registry,
        ), patch(
            "autom8_asana.lambda_handlers.cache_warmer._discover_entity_projects_for_lambda",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Discovery failed"),
        ):
            response = await _warm_cache_async()

        assert response.success is False
        assert "EntityProjectRegistry not initialized" in response.message

    @pytest.mark.asyncio
    async def test_invalid_entity_types(self, mock_cache: MagicMock) -> None:
        """Return failure for invalid entity types."""
        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = True

        with patch.dict("os.environ", {}, clear=True), patch(
            "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
            return_value=mock_cache,
        ), patch(
            "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
            return_value=mock_registry,
        ):
            response = await _warm_cache_async(entity_types=["invalid_type"])

        assert response.success is False
        assert "Invalid entity types" in response.message

    @pytest.mark.asyncio
    async def test_missing_bot_pat(self, mock_cache: MagicMock) -> None:
        """Return failure when bot PAT not available."""
        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = True
        mock_registry.get_project_gid.return_value = "project-123"

        from autom8_asana.auth.bot_pat import BotPATError

        with patch.dict("os.environ", {}, clear=True), patch(
            "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
            return_value=mock_cache,
        ), patch(
            "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
            return_value=mock_registry,
        ), patch(
            "autom8_asana.auth.bot_pat.get_bot_pat",
            side_effect=BotPATError("No PAT"),
        ):
            response = await _warm_cache_async(entity_types=["unit"])

        assert response.success is False
        assert "Failed to get bot PAT" in response.message

    @pytest.mark.asyncio
    async def test_missing_workspace_gid(self, mock_cache: MagicMock) -> None:
        """Return failure when workspace GID not set."""
        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = True
        mock_registry.get_project_gid.return_value = "project-123"

        # Set up environment without ASANA_WORKSPACE_GID
        with patch.dict("os.environ", {"ASANA_BOT_PAT": "test-pat"}, clear=True), patch(
            "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
            return_value=mock_cache,
        ), patch(
            "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
            return_value=mock_registry,
        ), patch(
            "autom8_asana.auth.bot_pat.get_bot_pat",
            return_value="test-pat",
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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
    """Tests for _emit_metric CloudWatch helper."""

    def test_emits_metric_with_dimensions(self) -> None:
        """Metric is emitted with environment and custom dimensions."""
        mock_client = MagicMock()

        with patch(
            "autom8_asana.lambda_handlers.cache_warmer._get_cloudwatch_client",
            return_value=mock_client,
        ), patch(
            "autom8_asana.lambda_handlers.cache_warmer.ENVIRONMENT",
            "test-env",
        ):
            _emit_metric(
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
            "autom8_asana.lambda_handlers.cache_warmer._get_cloudwatch_client",
            return_value=mock_client,
        ):
            _emit_metric(
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
            "autom8_asana.lambda_handlers.cache_warmer._get_cloudwatch_client",
            return_value=mock_client,
        ):
            # Should not raise
            _emit_metric(metric_name="WarmSuccess", value=1)

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

    @pytest.mark.asyncio
    async def test_resumes_from_fresh_checkpoint(
        self,
        mock_checkpoint_manager: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Warming resumes from checkpoint when fresh checkpoint exists."""
        from autom8_asana.lambda_handlers.checkpoint import CheckpointRecord

        # Create a fresh checkpoint with unit completed
        now = datetime.now(timezone.utc)
        checkpoint = CheckpointRecord(
            invocation_id="prior-123",
            completed_entities=["unit"],
            pending_entities=["business", "offer", "contact"],
            entity_results=[{
                "entity_type": "unit",
                "result": "success",
                "row_count": 100,
            }],
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

        with patch.dict("os.environ", {
            "ASANA_WORKSPACE_GID": "workspace-123",
            "ASANA_CACHE_S3_BUCKET": "test-bucket",
        }), patch(
            "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
            return_value=mock_cache,
        ), patch(
            "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
            return_value=mock_registry,
        ), patch(
            "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
            return_value=mock_checkpoint_manager,
        ), patch(
            "autom8_asana.auth.bot_pat.get_bot_pat",
            return_value="test-pat",
        ), patch(
            "autom8_asana.cache.dataframe.warmer.CacheWarmer",
            return_value=mock_warmer,
        ), patch(
            "autom8_asana.AsanaClient",
        ), patch(
            "autom8_asana.lambda_handlers.cache_warmer._emit_metric",
        ):
            await _warm_cache_async(
                resume_from_checkpoint=True,
                context=MockLambdaContext(remaining_time_ms=600_000),
            )

        # Verify checkpoint was loaded
        mock_checkpoint_manager.load_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_ignores_stale_checkpoint(self) -> None:
        """Warming ignores stale checkpoint."""
        from autom8_asana.lambda_handlers.checkpoint import CheckpointRecord

        # Create a stale checkpoint
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
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

    @pytest.mark.asyncio
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

        with patch.dict("os.environ", {
            "ASANA_WORKSPACE_GID": "workspace-123",
            "ASANA_CACHE_S3_BUCKET": "test-bucket",
        }), patch(
            "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
            return_value=mock_cache,
        ), patch(
            "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
            return_value=mock_registry,
        ), patch(
            "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
            return_value=mock_checkpoint_manager,
        ), patch(
            "autom8_asana.auth.bot_pat.get_bot_pat",
            return_value="test-pat",
        ), patch(
            "autom8_asana.AsanaClient",
        ), patch(
            "autom8_asana.lambda_handlers.cache_warmer._emit_metric",
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

    @pytest.mark.asyncio
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

        with patch.dict("os.environ", {
            "ASANA_WORKSPACE_GID": "workspace-123",
            "ASANA_CACHE_S3_BUCKET": "test-bucket",
        }), patch(
            "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
            return_value=mock_cache,
        ), patch(
            "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
            return_value=mock_registry,
        ), patch(
            "autom8_asana.lambda_handlers.checkpoint.CheckpointManager",
            return_value=mock_checkpoint_manager,
        ), patch(
            "autom8_asana.auth.bot_pat.get_bot_pat",
            return_value="test-pat",
        ), patch(
            "autom8_asana.cache.dataframe.warmer.CacheWarmer",
            return_value=mock_warmer,
        ), patch(
            "autom8_asana.cache.dataframe.warmer.WarmResult",
        ) as mock_warm_result, patch(
            "autom8_asana.AsanaClient",
        ), patch(
            "autom8_asana.lambda_handlers.cache_warmer._emit_metric",
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

    @pytest.mark.asyncio
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
