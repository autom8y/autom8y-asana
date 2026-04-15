"""Tests for FIND-002: resolution_null_slot logging in UniversalResolutionStrategy.

Per ADR-error-taxonomy-resolution / FIND-002:
When a resolution slot remains None after Phase 2 (unexpected), the strategy
should emit a structured log with criterion_index and entity_type before
returning RESOLUTION_NULL_SLOT.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.services.dynamic_index import DynamicIndexCache
from autom8_asana.services.universal_strategy import UniversalResolutionStrategy


@pytest.fixture()
def index_cache() -> DynamicIndexCache:
    """Fresh DynamicIndexCache for isolation."""
    return DynamicIndexCache(max_per_entity=5, ttl_seconds=3600)


@pytest.fixture()
def mock_client() -> MagicMock:
    """Mock AsanaClient."""
    client = MagicMock()
    client.unified_store = MagicMock()
    return client


class TestNullSlotLogging:
    """FIND-002: resolution_null_slot emits structured log."""

    async def test_null_slot_logs_criterion_index_and_entity_type(
        self,
        index_cache: DynamicIndexCache,
        mock_client: MagicMock,
    ) -> None:
        """When a results slot is None after Phase 2, logger.error is called.

        Constructs a scenario where _resolve_group never writes to a slot
        (e.g., gather_with_limit succeeds but the group coroutine is mocked
        to skip writing). The strategy should log resolution_null_slot with
        criterion_index and entity_type.
        """
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )

        # Mock validate_criterion_for_entity to return valid criteria
        mock_validation = MagicMock()
        mock_validation.is_valid = True
        mock_validation.normalized_criterion = {"office_phone": "+15551234567"}
        mock_validation.errors = []

        # Mock gather_with_limit to be a no-op -- this leaves results[0] = None
        async def noop_gather(coros: list, max_concurrent: int) -> None:
            pass

        with (
            patch(
                "autom8_asana.services.resolver.validate_criterion_for_entity",
                return_value=mock_validation,
            ),
            patch(
                "autom8_asana.dataframes.builders.base.gather_with_limit",
                side_effect=noop_gather,
            ),
            patch("autom8_asana.services.universal_strategy.logger") as mock_logger,
        ):
            results = await strategy.resolve(
                criteria=[{"phone": "+15551234567"}],
                project_gid="1201081073731555",
                client=mock_client,
            )

        # Verify RESOLUTION_NULL_SLOT returned for the null slot
        assert len(results) == 1
        assert results[0].error == "RESOLUTION_NULL_SLOT"
        assert results[0].gid is None

        # Verify the structured log was emitted
        mock_logger.error.assert_called_once_with(
            "resolution_null_slot",
            extra={
                "criterion_index": 0,
                "entity_type": "unit",
            },
        )

    async def test_multiple_null_slots_log_each_index(
        self,
        index_cache: DynamicIndexCache,
        mock_client: MagicMock,
    ) -> None:
        """Multiple null slots each get their own log entry with correct index."""
        strategy = UniversalResolutionStrategy(
            entity_type="offer",
            index_cache=index_cache,
        )

        mock_validation = MagicMock()
        mock_validation.is_valid = True
        mock_validation.normalized_criterion = {"offer_id": "OID001"}
        mock_validation.errors = []

        async def noop_gather(coros: list, max_concurrent: int) -> None:
            pass

        with (
            patch(
                "autom8_asana.services.resolver.validate_criterion_for_entity",
                return_value=mock_validation,
            ),
            patch(
                "autom8_asana.dataframes.builders.base.gather_with_limit",
                side_effect=noop_gather,
            ),
            patch("autom8_asana.services.universal_strategy.logger") as mock_logger,
        ):
            results = await strategy.resolve(
                criteria=[
                    {"offer_id": "OID001"},
                    {"offer_id": "OID002"},
                    {"offer_id": "OID003"},
                ],
                project_gid="1143843662099250",
                client=mock_client,
            )

        assert len(results) == 3
        for r in results:
            assert r.error == "RESOLUTION_NULL_SLOT"

        # All three slots should have been logged
        error_calls = mock_logger.error.call_args_list
        assert len(error_calls) == 3

        logged_indices = [
            call.kwargs["extra"]["criterion_index"]
            if "extra" in call.kwargs
            else call[1]["extra"]["criterion_index"]
            for call in error_calls
        ]
        assert logged_indices == [0, 1, 2]

        # All should reference "offer" entity type
        for call in error_calls:
            extra = call.kwargs["extra"] if "extra" in call.kwargs else call[1]["extra"]
            assert extra["entity_type"] == "offer"

    async def test_no_null_slot_no_error_log(
        self,
        index_cache: DynamicIndexCache,
        mock_client: MagicMock,
    ) -> None:
        """When all slots are filled, no resolution_null_slot log is emitted."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )

        mock_validation = MagicMock()
        mock_validation.is_valid = True
        mock_validation.normalized_criterion = {"office_phone": "+15551234567"}
        mock_validation.errors = []

        # _resolve_group writes to slot -- mock gather to actually run the coros
        # Simplest approach: mock so that invalid criteria produce error_result (non-None)
        mock_validation.is_valid = False
        mock_validation.errors = ["test error"]

        with (
            patch(
                "autom8_asana.services.resolver.validate_criterion_for_entity",
                return_value=mock_validation,
            ),
            patch("autom8_asana.services.universal_strategy.logger") as mock_logger,
        ):
            results = await strategy.resolve(
                criteria=[{"phone": "+15551234567"}],
                project_gid="1201081073731555",
                client=mock_client,
            )

        # Invalid criteria -> INVALID_CRITERIA error (not RESOLUTION_NULL_SLOT)
        assert len(results) == 1
        assert results[0].error == "INVALID_CRITERIA"

        # No resolution_null_slot log
        for call in mock_logger.error.call_args_list:
            assert call[0][0] != "resolution_null_slot"
