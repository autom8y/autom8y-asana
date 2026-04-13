"""Unit tests for GID push integration in cache warmer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.lambda_handlers.push_orchestrator import (
    _push_gid_mappings_for_completed_entities,
)


def _gid_for_unit(et: str) -> str | None:
    return "project-123" if et == "unit" else None


def _always_project_456(et: str) -> str:
    return "project-456"


def _always_project_123(et: str) -> str:
    return "project-123"


def _always_none(et: str) -> None:
    return None


class TestPushGidMappingsForCompletedEntities:
    """Tests for the _push_gid_mappings_for_completed_entities helper."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create a mock DataFrameCache."""
        cache = MagicMock()
        cache.get_async = AsyncMock(return_value=None)
        return cache

    @pytest.fixture
    def unit_dataframe(self) -> pl.DataFrame:
        """Create a DataFrame with GID-bearing columns (office_phone, vertical, gid)."""
        return pl.DataFrame(
            {
                "office_phone": ["+15551234567", "+15559876543"],
                "vertical": ["dental", "chiropractic"],
                "gid": ["1111111111111111", "2222222222222222"],
                "name": ["Business A", "Business B"],
            }
        )

    @pytest.fixture
    def offer_dataframe(self) -> pl.DataFrame:
        """Create a DataFrame WITHOUT GID columns (e.g., offer entity)."""
        return pl.DataFrame(
            {
                "gid": ["3333333333333333"],
                "name": ["Offer A"],
                "status": ["active"],
            }
        )

    @pytest.mark.asyncio
    async def test_pushes_for_unit_entity_with_gid_columns(
        self,
        mock_cache: MagicMock,
        unit_dataframe: pl.DataFrame,
    ) -> None:
        """GID mappings are pushed for entities with office_phone/vertical/gid columns."""
        # Mock cache entry with DataFrame
        mock_entry = MagicMock()
        mock_entry.dataframe = unit_dataframe
        mock_cache.get_async.return_value = mock_entry

        with (
            patch(
                "autom8_asana.services.gid_push.push_gid_mappings_to_data_service",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_push,
            patch(
                "autom8_asana.lambda_handlers.push_orchestrator.emit_metric",
            ),
        ):
            await _push_gid_mappings_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid=_gid_for_unit,
                cache=mock_cache,
                invocation_id="test-invoke-1",
            )

        mock_push.assert_called_once()
        call_kwargs = mock_push.call_args[1]
        assert call_kwargs["project_gid"] == "project-123"
        # The index should have 2 entries (from the unit DataFrame)
        assert len(call_kwargs["index"]) == 2

    @pytest.mark.asyncio
    async def test_skips_entity_without_gid_columns(
        self,
        mock_cache: MagicMock,
        offer_dataframe: pl.DataFrame,
    ) -> None:
        """Entities without office_phone/vertical columns are silently skipped."""
        mock_entry = MagicMock()
        mock_entry.dataframe = offer_dataframe
        mock_cache.get_async.return_value = mock_entry

        with (
            patch(
                "autom8_asana.services.gid_push.push_gid_mappings_to_data_service",
                new_callable=AsyncMock,
            ) as mock_push,
            patch(
                "autom8_asana.lambda_handlers.push_orchestrator.emit_metric",
            ),
        ):
            await _push_gid_mappings_for_completed_entities(
                completed_entities=["offer"],
                get_project_gid=_always_project_456,
                cache=mock_cache,
                invocation_id="test-invoke-2",
            )

        # push should NOT have been called (no GID columns)
        mock_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_failure_does_not_raise(
        self,
        mock_cache: MagicMock,
        unit_dataframe: pl.DataFrame,
    ) -> None:
        """Push failure returns False but does not raise an exception."""
        mock_entry = MagicMock()
        mock_entry.dataframe = unit_dataframe
        mock_cache.get_async.return_value = mock_entry

        with (
            patch(
                "autom8_asana.services.gid_push.push_gid_mappings_to_data_service",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "autom8_asana.lambda_handlers.push_orchestrator.emit_metric",
            ) as mock_emit,
        ):
            # Should NOT raise
            await _push_gid_mappings_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid=_always_project_123,
                cache=mock_cache,
                invocation_id="test-invoke-3",
            )

        # Should emit GidPushFailure metric
        metric_calls = [
            call for call in mock_emit.call_args_list if call.args[0] == "GidPushFailure"
        ]
        assert len(metric_calls) == 1

    @pytest.mark.asyncio
    async def test_push_exception_is_caught(
        self,
        mock_cache: MagicMock,
        unit_dataframe: pl.DataFrame,
    ) -> None:
        """Exception during push is caught and logged, not propagated."""
        mock_entry = MagicMock()
        mock_entry.dataframe = unit_dataframe
        mock_cache.get_async.return_value = mock_entry

        with (
            patch(
                "autom8_asana.services.gid_push.push_gid_mappings_to_data_service",
                new_callable=AsyncMock,
                side_effect=RuntimeError("unexpected push error"),
            ),
            patch(
                "autom8_asana.lambda_handlers.push_orchestrator.emit_metric",
            ),
        ):
            # Should NOT raise
            await _push_gid_mappings_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid=_always_project_123,
                cache=mock_cache,
                invocation_id="test-invoke-4",
            )

    @pytest.mark.asyncio
    async def test_skips_entity_with_no_project_gid(
        self,
        mock_cache: MagicMock,
    ) -> None:
        """Entities without a project GID are skipped."""
        with (
            patch(
                "autom8_asana.services.gid_push.push_gid_mappings_to_data_service",
                new_callable=AsyncMock,
            ) as mock_push,
            patch(
                "autom8_asana.lambda_handlers.push_orchestrator.emit_metric",
            ),
        ):
            await _push_gid_mappings_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid=_always_none,
                cache=mock_cache,
                invocation_id="test-invoke-5",
            )

        mock_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_entity_with_no_cached_entry(
        self,
        mock_cache: MagicMock,
    ) -> None:
        """Entities with no cached DataFrame are skipped."""
        mock_cache.get_async.return_value = None

        with (
            patch(
                "autom8_asana.services.gid_push.push_gid_mappings_to_data_service",
                new_callable=AsyncMock,
            ) as mock_push,
            patch(
                "autom8_asana.lambda_handlers.push_orchestrator.emit_metric",
            ),
        ):
            await _push_gid_mappings_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid=_always_project_123,
                cache=mock_cache,
                invocation_id="test-invoke-6",
            )

        mock_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_multiple_entities(
        self,
        mock_cache: MagicMock,
        unit_dataframe: pl.DataFrame,
        offer_dataframe: pl.DataFrame,
    ) -> None:
        """Processes multiple entities, pushing only those with GID columns."""
        unit_entry = MagicMock()
        unit_entry.dataframe = unit_dataframe

        offer_entry = MagicMock()
        offer_entry.dataframe = offer_dataframe

        async def mock_get_async(project_gid: str, entity_type: str) -> MagicMock | None:
            if entity_type == "unit":
                return unit_entry
            elif entity_type == "offer":
                return offer_entry
            return None

        mock_cache.get_async = mock_get_async

        gid_map = {"unit": "project-111", "offer": "project-222"}

        def get_project_gid(et: str) -> str | None:
            return gid_map.get(et)

        with (
            patch(
                "autom8_asana.services.gid_push.push_gid_mappings_to_data_service",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_push,
            patch(
                "autom8_asana.lambda_handlers.push_orchestrator.emit_metric",
            ),
        ):
            await _push_gid_mappings_for_completed_entities(
                completed_entities=["unit", "offer"],
                get_project_gid=get_project_gid,
                cache=mock_cache,
                invocation_id="test-invoke-7",
            )

        # Only "unit" should have been pushed (offer lacks GID columns)
        assert mock_push.call_count == 1
        assert mock_push.call_args.kwargs["project_gid"] == "project-111"

    @pytest.mark.asyncio
    async def test_empty_completed_entities_is_noop(
        self,
        mock_cache: MagicMock,
    ) -> None:
        """No work done when completed_entities is empty."""
        with (
            patch(
                "autom8_asana.services.gid_push.push_gid_mappings_to_data_service",
                new_callable=AsyncMock,
            ) as mock_push,
            patch(
                "autom8_asana.lambda_handlers.push_orchestrator.emit_metric",
            ),
        ):
            await _push_gid_mappings_for_completed_entities(
                completed_entities=[],
                get_project_gid=_always_project_123,
                cache=mock_cache,
                invocation_id="test-invoke-8",
            )

        mock_push.assert_not_called()
