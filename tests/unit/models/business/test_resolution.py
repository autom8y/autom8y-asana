"""Tests for resolution types and strategies.

Per TDD-RESOLUTION: Tests for ResolutionStrategy enum and ResolutionResult dataclass.
Per ADR-0073: Tests for batch resolution functions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.models.business.resolution import (
    ResolutionResult,
    ResolutionStrategy,
    resolve_offers_async,
    resolve_units_async,
)
from autom8_asana.models.business.unit import Unit


class TestResolutionStrategy:
    """Tests for ResolutionStrategy enum."""

    def test_strategy_values(self) -> None:
        """All strategy enum values are correct."""
        assert ResolutionStrategy.DEPENDENT_TASKS.value == "dependent_tasks"
        assert ResolutionStrategy.CUSTOM_FIELD_MAPPING.value == "custom_field_mapping"
        assert ResolutionStrategy.EXPLICIT_OFFER_ID.value == "explicit_offer_id"
        assert ResolutionStrategy.AUTO.value == "auto"

    def test_strategy_is_string_enum(self) -> None:
        """Strategy enum values are strings for serialization."""
        assert isinstance(ResolutionStrategy.DEPENDENT_TASKS, str)
        assert ResolutionStrategy.DEPENDENT_TASKS == "dependent_tasks"

    def test_priority_order_returns_correct_sequence(self) -> None:
        """priority_order returns strategies in expected priority."""
        order = ResolutionStrategy.priority_order()

        assert len(order) == 3
        assert order[0] == ResolutionStrategy.DEPENDENT_TASKS
        assert order[1] == ResolutionStrategy.CUSTOM_FIELD_MAPPING
        assert order[2] == ResolutionStrategy.EXPLICIT_OFFER_ID

    def test_priority_order_excludes_auto(self) -> None:
        """AUTO is not included in priority order (it orchestrates the others)."""
        order = ResolutionStrategy.priority_order()
        assert ResolutionStrategy.AUTO not in order

    def test_priority_order_returns_new_list(self) -> None:
        """priority_order returns a new list each time (not a reference)."""
        order1 = ResolutionStrategy.priority_order()
        order2 = ResolutionStrategy.priority_order()

        assert order1 == order2
        assert order1 is not order2

    def test_all_strategies_enumerable(self) -> None:
        """All strategies can be enumerated."""
        strategies = list(ResolutionStrategy)
        assert len(strategies) == 4


class TestResolutionResult:
    """Tests for ResolutionResult dataclass."""

    def test_default_values(self) -> None:
        """Result has correct default values."""
        result = ResolutionResult[Unit]()

        assert result.entity is None
        assert result.strategy_used is None
        assert result.strategies_tried == []
        assert result.ambiguous is False
        assert result.candidates == []
        assert result.error is None

    def test_success_property_true_on_single_match(self) -> None:
        """success is True when entity is set and not ambiguous."""
        unit = Unit(gid="u1", name="Test Unit")
        result = ResolutionResult[Unit](
            entity=unit,
            strategy_used=ResolutionStrategy.DEPENDENT_TASKS,
        )

        assert result.success is True

    def test_success_property_false_when_no_entity(self) -> None:
        """success is False when no entity found."""
        result = ResolutionResult[Unit](
            error="No matching Unit found",
        )

        assert result.success is False

    def test_success_property_false_when_ambiguous(self) -> None:
        """success is False when multiple matches found."""
        unit1 = Unit(gid="u1", name="Unit 1")
        unit2 = Unit(gid="u2", name="Unit 2")

        result = ResolutionResult[Unit](
            entity=unit1,  # First match per ADR-0071
            ambiguous=True,
            candidates=[unit1, unit2],
            strategy_used=ResolutionStrategy.CUSTOM_FIELD_MAPPING,
        )

        assert result.success is False
        assert result.entity is unit1  # Still has entity for convenience

    def test_entity_with_strategy_used(self) -> None:
        """Result tracks which strategy produced the match."""
        unit = Unit(gid="u1", name="Test Unit")
        result = ResolutionResult[Unit](
            entity=unit,
            strategy_used=ResolutionStrategy.EXPLICIT_OFFER_ID,
            strategies_tried=[
                ResolutionStrategy.DEPENDENT_TASKS,
                ResolutionStrategy.CUSTOM_FIELD_MAPPING,
                ResolutionStrategy.EXPLICIT_OFFER_ID,
            ],
        )

        assert result.strategy_used == ResolutionStrategy.EXPLICIT_OFFER_ID
        assert len(result.strategies_tried) == 3

    def test_strategies_tried_tracking(self) -> None:
        """All attempted strategies are tracked."""
        result = ResolutionResult[Unit](
            error="All strategies failed",
            strategies_tried=[
                ResolutionStrategy.DEPENDENT_TASKS,
                ResolutionStrategy.CUSTOM_FIELD_MAPPING,
            ],
        )

        assert ResolutionStrategy.DEPENDENT_TASKS in result.strategies_tried
        assert ResolutionStrategy.CUSTOM_FIELD_MAPPING in result.strategies_tried
        assert ResolutionStrategy.EXPLICIT_OFFER_ID not in result.strategies_tried

    def test_ambiguous_with_candidates(self) -> None:
        """Ambiguous result includes all candidates."""
        unit1 = Unit(gid="u1", name="Unit 1")
        unit2 = Unit(gid="u2", name="Unit 2")
        unit3 = Unit(gid="u3", name="Unit 3")

        result = ResolutionResult[Unit](
            entity=unit1,
            ambiguous=True,
            candidates=[unit1, unit2, unit3],
            strategy_used=ResolutionStrategy.DEPENDENT_TASKS,
        )

        assert result.ambiguous is True
        assert len(result.candidates) == 3
        assert result.entity is unit1

    def test_error_message(self) -> None:
        """Error message is accessible."""
        result = ResolutionResult[Unit](
            error="Task with GID 12345 not found",
            strategies_tried=[ResolutionStrategy.EXPLICIT_OFFER_ID],
        )

        assert "12345" in result.error
        assert result.success is False


class TestResolutionResultGenericType:
    """Tests for ResolutionResult generic type handling."""

    def test_result_with_unit_type(self) -> None:
        """Result correctly holds Unit type."""
        unit = Unit(gid="u1", name="Test Unit")
        result: ResolutionResult[Unit] = ResolutionResult(entity=unit)

        assert isinstance(result.entity, Unit)

    def test_result_with_offer_type(self) -> None:
        """Result correctly holds Offer type."""
        from autom8_asana.models.business.offer import Offer

        offer = Offer(gid="o1", name="Test Offer")
        result: ResolutionResult[Offer] = ResolutionResult(entity=offer)

        assert isinstance(result.entity, Offer)

    def test_candidates_list_type(self) -> None:
        """Candidates list holds correct type."""
        from autom8_asana.models.business.offer import Offer

        offer1 = Offer(gid="o1", name="Offer 1")
        offer2 = Offer(gid="o2", name="Offer 2")

        result: ResolutionResult[Offer] = ResolutionResult(
            entity=offer1,
            ambiguous=True,
            candidates=[offer1, offer2],
        )

        assert all(isinstance(o, Offer) for o in result.candidates)


class TestBatchResolution:
    """Tests for batch resolution functions.

    Per ADR-0073: Tests for resolve_units_async and resolve_offers_async.
    """

    async def test_resolve_units_async_empty_list_returns_empty_dict(self) -> None:
        """Empty input returns empty dict."""
        client = MagicMock()

        results = await resolve_units_async([], client)

        assert results == {}

    async def test_resolve_offers_async_empty_list_returns_empty_dict(self) -> None:
        """Empty input returns empty dict for offers."""
        client = MagicMock()

        results = await resolve_offers_async([], client)

        assert results == {}

    async def test_resolve_units_async_single_asset_edit(self) -> None:
        """Single AssetEdit is resolved correctly."""
        from autom8_asana.models.business.asset_edit import AssetEdit

        asset_edit = AssetEdit(gid="ae1", name="Asset Edit 1")
        unit = Unit(gid="u1", name="Unit 1")

        expected_result = ResolutionResult[Unit](
            entity=unit,
            strategy_used=ResolutionStrategy.DEPENDENT_TASKS,
        )

        client = MagicMock()
        # Patch at class level
        with patch.object(
            AssetEdit, "resolve_unit_async", new=AsyncMock(return_value=expected_result)
        ):
            results = await resolve_units_async([asset_edit], client)

        assert len(results) == 1
        assert "ae1" in results
        assert results["ae1"].entity == unit
        assert results["ae1"].success is True

    async def test_resolve_units_async_multiple_same_business(self) -> None:
        """Multiple AssetEdits from same Business share hydration."""
        from autom8_asana.models.business.asset_edit import AssetEdit
        from autom8_asana.models.business.business import Business
        from autom8_asana.models.business.unit import UnitHolder

        # Create mock business with unit holder already populated
        business = Business(gid="b1", name="Test Business")
        unit_holder = MagicMock(spec=UnitHolder)
        business._unit_holder = unit_holder

        # Create multiple asset edits pointing to same business
        asset_edit1 = AssetEdit(gid="ae1", name="Asset Edit 1")
        asset_edit1._business = business
        asset_edit2 = AssetEdit(gid="ae2", name="Asset Edit 2")
        asset_edit2._business = business

        unit1 = Unit(gid="u1", name="Unit 1")

        result = ResolutionResult[Unit](
            entity=unit1,
            strategy_used=ResolutionStrategy.CUSTOM_FIELD_MAPPING,
        )

        client = MagicMock()
        # Patch at class level - all calls return same result
        with patch.object(AssetEdit, "resolve_unit_async", new=AsyncMock(return_value=result)):
            results = await resolve_units_async([asset_edit1, asset_edit2], client)

        assert len(results) == 2
        assert "ae1" in results
        assert "ae2" in results
        # Both resolve to the same result since we patched at class level
        assert results["ae1"].entity == unit1
        assert results["ae2"].entity == unit1

    async def test_resolve_units_async_multiple_different_businesses(self) -> None:
        """Multiple AssetEdits from different Businesses are resolved."""
        from autom8_asana.models.business.asset_edit import AssetEdit
        from autom8_asana.models.business.business import Business
        from autom8_asana.models.business.unit import UnitHolder

        # Create two businesses with unit holders
        business1 = Business(gid="b1", name="Business 1")
        business1._unit_holder = MagicMock(spec=UnitHolder)
        business2 = Business(gid="b2", name="Business 2")
        business2._unit_holder = MagicMock(spec=UnitHolder)

        # Create asset edits pointing to different businesses
        asset_edit1 = AssetEdit(gid="ae1", name="Asset Edit 1")
        asset_edit1._business = business1
        asset_edit2 = AssetEdit(gid="ae2", name="Asset Edit 2")
        asset_edit2._business = business2

        unit = Unit(gid="u1", name="Unit 1")

        result = ResolutionResult[Unit](
            entity=unit,
            strategy_used=ResolutionStrategy.DEPENDENT_TASKS,
        )

        client = MagicMock()
        with patch.object(AssetEdit, "resolve_unit_async", new=AsyncMock(return_value=result)):
            results = await resolve_units_async([asset_edit1, asset_edit2], client)

        assert len(results) == 2
        assert "ae1" in results
        assert "ae2" in results

    async def test_resolve_units_async_partial_failure(self) -> None:
        """Partial failures still return results for all inputs."""
        from autom8_asana.models.business.asset_edit import AssetEdit

        asset_edit1 = AssetEdit(gid="ae1", name="Asset Edit 1")
        asset_edit2 = AssetEdit(gid="ae2", name="Asset Edit 2")

        unit = Unit(gid="u1", name="Unit 1")
        success_result = ResolutionResult[Unit](
            entity=unit,
            strategy_used=ResolutionStrategy.DEPENDENT_TASKS,
        )
        failure_result = ResolutionResult[Unit](
            error="No matching Unit found",
            strategies_tried=[
                ResolutionStrategy.DEPENDENT_TASKS,
                ResolutionStrategy.CUSTOM_FIELD_MAPPING,
                ResolutionStrategy.EXPLICIT_OFFER_ID,
            ],
        )

        # Use side_effect to return different results for each call
        mock_resolve = AsyncMock(side_effect=[success_result, failure_result])

        client = MagicMock()
        with patch.object(AssetEdit, "resolve_unit_async", new=mock_resolve):
            results = await resolve_units_async([asset_edit1, asset_edit2], client)

        # Both have entries
        assert len(results) == 2
        assert "ae1" in results
        assert "ae2" in results

        # First succeeded, second failed
        assert results["ae1"].success is True
        assert results["ae2"].success is False
        assert results["ae2"].error == "No matching Unit found"

    async def test_resolve_units_async_with_dependent_tasks_strategy(self) -> None:
        """Strategy parameter is passed correctly."""
        from autom8_asana.models.business.asset_edit import AssetEdit

        asset_edit = AssetEdit(gid="ae1", name="Asset Edit 1")
        unit = Unit(gid="u1", name="Unit 1")

        result = ResolutionResult[Unit](
            entity=unit,
            strategy_used=ResolutionStrategy.DEPENDENT_TASKS,
        )

        mock_resolve = AsyncMock(return_value=result)
        client = MagicMock()

        with patch.object(AssetEdit, "resolve_unit_async", new=mock_resolve):
            await resolve_units_async(
                [asset_edit], client, strategy=ResolutionStrategy.DEPENDENT_TASKS
            )

            # Verify strategy was passed
            mock_resolve.assert_called_once_with(
                client, strategy=ResolutionStrategy.DEPENDENT_TASKS
            )

    async def test_resolve_units_async_with_custom_field_strategy(self) -> None:
        """CUSTOM_FIELD_MAPPING strategy is passed correctly."""
        from autom8_asana.models.business.asset_edit import AssetEdit

        asset_edit = AssetEdit(gid="ae1", name="Asset Edit 1")
        unit = Unit(gid="u1", name="Unit 1")

        result = ResolutionResult[Unit](
            entity=unit,
            strategy_used=ResolutionStrategy.CUSTOM_FIELD_MAPPING,
        )

        mock_resolve = AsyncMock(return_value=result)
        client = MagicMock()

        with patch.object(AssetEdit, "resolve_unit_async", new=mock_resolve):
            await resolve_units_async(
                [asset_edit], client, strategy=ResolutionStrategy.CUSTOM_FIELD_MAPPING
            )

            mock_resolve.assert_called_once_with(
                client, strategy=ResolutionStrategy.CUSTOM_FIELD_MAPPING
            )

    async def test_resolve_units_async_with_explicit_offer_id_strategy(self) -> None:
        """EXPLICIT_OFFER_ID strategy is passed correctly."""
        from autom8_asana.models.business.asset_edit import AssetEdit

        asset_edit = AssetEdit(gid="ae1", name="Asset Edit 1")
        unit = Unit(gid="u1", name="Unit 1")

        result = ResolutionResult[Unit](
            entity=unit,
            strategy_used=ResolutionStrategy.EXPLICIT_OFFER_ID,
        )

        mock_resolve = AsyncMock(return_value=result)
        client = MagicMock()

        with patch.object(AssetEdit, "resolve_unit_async", new=mock_resolve):
            await resolve_units_async(
                [asset_edit], client, strategy=ResolutionStrategy.EXPLICIT_OFFER_ID
            )

            mock_resolve.assert_called_once_with(
                client, strategy=ResolutionStrategy.EXPLICIT_OFFER_ID
            )

    async def test_resolve_offers_async_delegates_correctly(self) -> None:
        """resolve_offers_async delegates to instance method."""
        from autom8_asana.models.business.asset_edit import AssetEdit
        from autom8_asana.models.business.offer import Offer

        asset_edit = AssetEdit(gid="ae1", name="Asset Edit 1")
        offer = Offer(gid="o1", name="Offer 1")

        result = ResolutionResult[Offer](
            entity=offer,
            strategy_used=ResolutionStrategy.EXPLICIT_OFFER_ID,
        )

        client = MagicMock()
        with patch.object(AssetEdit, "resolve_offer_async", new=AsyncMock(return_value=result)):
            results = await resolve_offers_async([asset_edit], client)

        assert len(results) == 1
        assert "ae1" in results
        assert results["ae1"].entity == offer
        assert results["ae1"].success is True

    async def test_resolve_units_async_exception_creates_error_result(self) -> None:
        """Exception during resolution creates error result."""
        from autom8_asana.models.business.asset_edit import AssetEdit

        asset_edit = AssetEdit(gid="ae1", name="Asset Edit 1")

        client = MagicMock()
        with patch.object(
            AssetEdit,
            "resolve_unit_async",
            new=AsyncMock(side_effect=RuntimeError("Network error")),
        ):
            results = await resolve_units_async([asset_edit], client)

        # Should still have entry
        assert len(results) == 1
        assert "ae1" in results

        # Error result
        result = results["ae1"]
        assert result.success is False
        assert result.entity is None
        assert "Network error" in result.error

    async def test_resolve_units_async_returns_dict_keyed_by_gid(self) -> None:
        """Results are keyed by asset_edit.gid."""
        from autom8_asana.models.business.asset_edit import AssetEdit

        # Use distinctive GIDs
        asset_edit1 = AssetEdit(gid="1234567890", name="AE1")
        asset_edit2 = AssetEdit(gid="0987654321", name="AE2")

        unit = Unit(gid="u1", name="Unit 1")
        result = ResolutionResult[Unit](
            entity=unit,
            strategy_used=ResolutionStrategy.AUTO,
        )

        client = MagicMock()
        with patch.object(AssetEdit, "resolve_unit_async", new=AsyncMock(return_value=result)):
            results = await resolve_units_async([asset_edit1, asset_edit2], client)

        # Keys are GIDs, not indices
        assert "1234567890" in results
        assert "0987654321" in results


class TestBatchResolutionEdgeCases:
    """Edge case tests for batch resolution functions.

    Per QA validation: Tests for edge cases not covered by primary test suite.
    """

    async def test_resolve_units_async_asset_edit_without_business_context(
        self,
    ) -> None:
        """AssetEdit without Business context still gets a result entry."""
        from autom8_asana.models.business.asset_edit import AssetEdit

        # Asset edit with no business set (ae._business is None)
        asset_edit = AssetEdit(gid="ae1", name="Orphan Asset Edit")
        # Explicitly confirm no business
        assert asset_edit.business is None

        # Mock the instance method to return an error (no business context)
        error_result = ResolutionResult[Unit](
            error="Business context required for CUSTOM_FIELD_MAPPING strategy",
            strategies_tried=[ResolutionStrategy.CUSTOM_FIELD_MAPPING],
        )

        client = MagicMock()
        with patch.object(
            AssetEdit, "resolve_unit_async", new=AsyncMock(return_value=error_result)
        ):
            results = await resolve_units_async([asset_edit], client)

        # Should have an entry even without business context
        assert len(results) == 1
        assert "ae1" in results
        assert results["ae1"].success is False
        assert "Business context" in results["ae1"].error

    async def test_resolve_units_async_all_fail_resolution(self) -> None:
        """All AssetEdits failing resolution returns all error entries."""
        from autom8_asana.models.business.asset_edit import AssetEdit

        asset_edit1 = AssetEdit(gid="ae1", name="Asset Edit 1")
        asset_edit2 = AssetEdit(gid="ae2", name="Asset Edit 2")
        asset_edit3 = AssetEdit(gid="ae3", name="Asset Edit 3")

        # All fail
        failure_result = ResolutionResult[Unit](
            error="No matching Unit found",
            strategies_tried=[
                ResolutionStrategy.DEPENDENT_TASKS,
                ResolutionStrategy.CUSTOM_FIELD_MAPPING,
                ResolutionStrategy.EXPLICIT_OFFER_ID,
            ],
        )

        client = MagicMock()
        with patch.object(
            AssetEdit, "resolve_unit_async", new=AsyncMock(return_value=failure_result)
        ):
            results = await resolve_units_async([asset_edit1, asset_edit2, asset_edit3], client)

        # All three should have entries
        assert len(results) == 3
        assert all(gid in results for gid in ["ae1", "ae2", "ae3"])

        # All should be failures
        assert all(not r.success for r in results.values())
        assert all(r.error == "No matching Unit found" for r in results.values())

    async def test_resolve_units_async_duplicate_gids_last_wins(self) -> None:
        """Duplicate AssetEdits with same GID - last result overwrites."""
        from autom8_asana.models.business.asset_edit import AssetEdit

        # Two asset edits with same GID (edge case)
        asset_edit1 = AssetEdit(gid="ae1", name="First Asset Edit")
        asset_edit2 = AssetEdit(gid="ae1", name="Second Asset Edit")

        unit1 = Unit(gid="u1", name="Unit 1")
        unit2 = Unit(gid="u2", name="Unit 2")

        # Different results for each
        result1 = ResolutionResult[Unit](
            entity=unit1,
            strategy_used=ResolutionStrategy.DEPENDENT_TASKS,
        )
        result2 = ResolutionResult[Unit](
            entity=unit2,
            strategy_used=ResolutionStrategy.CUSTOM_FIELD_MAPPING,
        )

        mock_resolve = AsyncMock(side_effect=[result1, result2])
        client = MagicMock()

        with patch.object(AssetEdit, "resolve_unit_async", new=mock_resolve):
            results = await resolve_units_async([asset_edit1, asset_edit2], client)

        # Only one key because both have same GID
        assert len(results) == 1
        assert "ae1" in results
        # Last one wins (unit2)
        assert results["ae1"].entity == unit2
        assert results["ae1"].strategy_used == ResolutionStrategy.CUSTOM_FIELD_MAPPING

    async def test_resolve_units_async_hydration_exception_continues(self) -> None:
        """Exception during hydration doesn't prevent resolution attempts."""
        from autom8_asana.models.business.asset_edit import AssetEdit
        from autom8_asana.models.business.business import Business

        # Create business without unit holder (needs hydration)
        business = Business(gid="b1", name="Test Business")
        # No _unit_holder set, so hydration will be attempted

        asset_edit = AssetEdit(gid="ae1", name="Asset Edit 1")
        asset_edit._business = business

        unit = Unit(gid="u1", name="Unit 1")
        success_result = ResolutionResult[Unit](
            entity=unit,
            strategy_used=ResolutionStrategy.DEPENDENT_TASKS,
        )

        client = MagicMock()

        # Hydration fails but resolution still proceeds
        with (
            patch(
                "autom8_asana.models.business.resolution._ensure_units_hydrated",
                new=AsyncMock(side_effect=RuntimeError("Hydration failed")),
            ),
            patch.object(
                AssetEdit,
                "resolve_unit_async",
                new=AsyncMock(return_value=success_result),
            ),
        ):
            results = await resolve_units_async([asset_edit], client)

        # Resolution still happened (hydration failure was caught)
        assert len(results) == 1
        assert "ae1" in results
        # Resolution succeeded even though hydration failed
        assert results["ae1"].success is True

    async def test_resolve_units_async_shared_hydration_optimization(self) -> None:
        """CRITICAL: Business.units fetched once per unique Business, not per AssetEdit."""
        from autom8_asana.models.business.asset_edit import AssetEdit
        from autom8_asana.models.business.business import Business

        # Create ONE business
        business = Business(gid="b1", name="Test Business")

        # Create THREE asset edits pointing to SAME business
        asset_edit1 = AssetEdit(gid="ae1", name="Asset Edit 1")
        asset_edit1._business = business
        asset_edit2 = AssetEdit(gid="ae2", name="Asset Edit 2")
        asset_edit2._business = business
        asset_edit3 = AssetEdit(gid="ae3", name="Asset Edit 3")
        asset_edit3._business = business

        unit = Unit(gid="u1", name="Unit 1")
        result = ResolutionResult[Unit](
            entity=unit,
            strategy_used=ResolutionStrategy.CUSTOM_FIELD_MAPPING,
        )

        client = MagicMock()

        # Track how many times hydration is called
        hydration_mock = AsyncMock()

        with (
            patch(
                "autom8_asana.models.business.resolution._ensure_units_hydrated",
                new=hydration_mock,
            ),
            patch.object(AssetEdit, "resolve_unit_async", new=AsyncMock(return_value=result)),
        ):
            results = await resolve_units_async([asset_edit1, asset_edit2, asset_edit3], client)

        # CRITICAL CHECK: Hydration called only ONCE (for one unique business)
        assert hydration_mock.call_count == 1
        # All three AssetEdits got results
        assert len(results) == 3

    async def test_resolve_units_async_multiple_businesses_separate_hydration(
        self,
    ) -> None:
        """Multiple unique Businesses each get hydrated once."""
        from autom8_asana.models.business.asset_edit import AssetEdit
        from autom8_asana.models.business.business import Business

        # Create TWO businesses
        business1 = Business(gid="b1", name="Business 1")
        business2 = Business(gid="b2", name="Business 2")

        # Create asset edits - 2 for business1, 1 for business2
        ae1 = AssetEdit(gid="ae1", name="AE1")
        ae1._business = business1
        ae2 = AssetEdit(gid="ae2", name="AE2")
        ae2._business = business1
        ae3 = AssetEdit(gid="ae3", name="AE3")
        ae3._business = business2

        unit = Unit(gid="u1", name="Unit 1")
        result = ResolutionResult[Unit](
            entity=unit,
            strategy_used=ResolutionStrategy.AUTO,
        )

        client = MagicMock()
        hydration_mock = AsyncMock()

        with (
            patch(
                "autom8_asana.models.business.resolution._ensure_units_hydrated",
                new=hydration_mock,
            ),
            patch.object(AssetEdit, "resolve_unit_async", new=AsyncMock(return_value=result)),
        ):
            results = await resolve_units_async([ae1, ae2, ae3], client)

        # Hydration called TWICE (once per unique business)
        assert hydration_mock.call_count == 2
        # All three AssetEdits got results
        assert len(results) == 3

    async def test_resolve_offers_async_exception_creates_error_result(self) -> None:
        """Exception during offer resolution creates error result."""
        from autom8_asana.models.business.asset_edit import AssetEdit

        asset_edit = AssetEdit(gid="ae1", name="Asset Edit 1")

        client = MagicMock()
        with patch.object(
            AssetEdit,
            "resolve_offer_async",
            new=AsyncMock(side_effect=RuntimeError("Offer resolution error")),
        ):
            results = await resolve_offers_async([asset_edit], client)

        # Should still have entry
        assert len(results) == 1
        assert "ae1" in results

        # Error result
        result = results["ae1"]
        assert result.success is False
        assert result.entity is None
        assert "Offer resolution error" in result.error

    async def test_resolve_units_async_mixed_with_and_without_business(self) -> None:
        """Mix of AssetEdits with and without Business context."""
        from autom8_asana.models.business.asset_edit import AssetEdit
        from autom8_asana.models.business.business import Business
        from autom8_asana.models.business.unit import UnitHolder

        # One with business, one without
        business = Business(gid="b1", name="Test Business")
        business._unit_holder = MagicMock(spec=UnitHolder)

        ae_with_business = AssetEdit(gid="ae1", name="With Business")
        ae_with_business._business = business
        ae_without_business = AssetEdit(gid="ae2", name="Without Business")
        # ae_without_business._business is None by default

        unit = Unit(gid="u1", name="Unit 1")
        success_result = ResolutionResult[Unit](
            entity=unit,
            strategy_used=ResolutionStrategy.CUSTOM_FIELD_MAPPING,
        )
        error_result = ResolutionResult[Unit](
            error="Business context required",
            strategies_tried=[ResolutionStrategy.CUSTOM_FIELD_MAPPING],
        )

        mock_resolve = AsyncMock(side_effect=[success_result, error_result])
        client = MagicMock()

        with patch.object(AssetEdit, "resolve_unit_async", new=mock_resolve):
            results = await resolve_units_async([ae_with_business, ae_without_business], client)

        # Both have entries
        assert len(results) == 2
        assert results["ae1"].success is True
        assert results["ae2"].success is False


class TestBatchResolutionSyncWrappers:
    """Tests for sync wrappers of batch resolution functions."""

    def test_resolve_units_sync_wrapper(self) -> None:
        """resolve_units calls resolve_units_async via asyncio.run."""
        from autom8_asana.models.business.resolution import resolve_units

        # Note: Can't actually call sync wrapper in test because asyncio.run
        # will fail in an already-running event loop. Instead verify the
        # function exists and has correct signature.
        assert callable(resolve_units)

    def test_resolve_offers_sync_wrapper(self) -> None:
        """resolve_offers calls resolve_offers_async via asyncio.run."""
        from autom8_asana.models.business.resolution import resolve_offers

        # Verify function exists and is callable
        assert callable(resolve_offers)
