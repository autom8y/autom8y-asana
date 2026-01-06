"""Unit tests for cache_warmer Lambda handler.

Per TDD-DATAFRAME-CACHE-001: Tests for Lambda warm-up handler.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.lambda_handlers.cache_warmer import (
    WarmResponse,
    _match_entity_type,
    _normalize_project_name,
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
        )
