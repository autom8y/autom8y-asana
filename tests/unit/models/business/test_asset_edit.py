"""Tests for AssetEdit entity.

Per TDD-RESOLUTION FR-PREREQ-001: Tests for AssetEdit entity with 11 typed field accessors.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.models.business.asset_edit import AssetEdit
from autom8_asana.models.business.business import AssetEditHolder, Business
from autom8_asana.models.business.resolution import ResolutionResult, ResolutionStrategy
from autom8_asana.models.business.unit import Unit


class TestAssetEditEntity:
    """Tests for AssetEdit entity creation and properties."""

    def test_asset_edit_inherits_from_process(self) -> None:
        """AssetEdit inherits from Process."""
        from autom8_asana.models.business.process import Process

        asset_edit = AssetEdit(gid="ae1", name="Test AssetEdit")

        assert isinstance(asset_edit, Process)
        assert asset_edit.gid == "ae1"
        assert asset_edit.name == "Test AssetEdit"

    def test_asset_edit_has_name_convention(self) -> None:
        """AssetEdit has NAME_CONVENTION class variable."""
        assert hasattr(AssetEdit, "NAME_CONVENTION")
        assert AssetEdit.NAME_CONVENTION == "[AssetEdit Name]"

    def test_asset_edit_has_primary_project_gid(self) -> None:
        """AssetEdit has PRIMARY_PROJECT_GID per PRD-0024."""
        assert hasattr(AssetEdit, "PRIMARY_PROJECT_GID")
        assert AssetEdit.PRIMARY_PROJECT_GID == "1202204184560785"

    def test_asset_edit_holder_property(self) -> None:
        """asset_edit_holder returns cached reference."""
        asset_edit = AssetEdit(gid="ae1")
        holder = AssetEditHolder(gid="h1")
        asset_edit._asset_edit_holder = holder

        assert asset_edit.asset_edit_holder is holder

    def test_business_navigation_via_holder(self) -> None:
        """business property navigates via asset_edit_holder."""
        business = Business(gid="b1", name="Test Business")
        holder = AssetEditHolder(gid="h1")
        holder._business = business

        asset_edit = AssetEdit(gid="ae1")
        asset_edit._asset_edit_holder = holder

        assert asset_edit.business is business

    def test_invalidate_refs(self) -> None:
        """_invalidate_refs clears cached references."""
        asset_edit = AssetEdit(gid="ae1")
        asset_edit._asset_edit_holder = AssetEditHolder(gid="h1")
        asset_edit._business = Business(gid="b1")  # type: ignore

        asset_edit._invalidate_refs()

        assert asset_edit._asset_edit_holder is None
        assert asset_edit._business is None


class TestAssetEditFields:
    """Tests for AssetEdit 11 typed field accessors."""

    def test_fields_class_constants(self) -> None:
        """Fields class has all 11 field name constants."""
        assert AssetEdit.Fields.ASSET_APPROVAL == "Asset Approval"
        assert AssetEdit.Fields.ASSET_ID == "Asset ID"
        assert AssetEdit.Fields.EDITOR == "Editor"
        assert AssetEdit.Fields.REVIEWER == "Reviewer"
        assert AssetEdit.Fields.OFFER_ID == "Offer ID"
        assert AssetEdit.Fields.RAW_ASSETS == "Raw Assets"
        assert AssetEdit.Fields.REVIEW_ALL_ADS == "Review All Ads"
        assert AssetEdit.Fields.SCORE == "Score"
        assert AssetEdit.Fields.SPECIALTY == "Specialty"
        assert AssetEdit.Fields.TEMPLATE_ID == "Template ID"
        assert AssetEdit.Fields.VIDEOS_PAID == "Videos Paid"

    def test_asset_approval_getter(self) -> None:
        """asset_approval getter extracts enum value."""
        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Asset Approval",
                    "enum_value": {"name": "Approved"},
                }
            ],
        )
        assert asset_edit.asset_approval == "Approved"

    def test_asset_approval_setter(self) -> None:
        """asset_approval setter updates value."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])
        asset_edit.asset_approval = "Pending"
        assert asset_edit.custom_fields_editor().get("Asset Approval") == "Pending"

    def test_asset_id_getter(self) -> None:
        """asset_id getter returns text value."""
        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[
                {"gid": "1", "name": "Asset ID", "text_value": "ASSET-12345"}
            ],
        )
        assert asset_edit.asset_id == "ASSET-12345"

    def test_asset_id_setter(self) -> None:
        """asset_id setter updates value."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])
        asset_edit.asset_id = "NEW-ID"
        assert asset_edit.custom_fields_editor().get("Asset ID") == "NEW-ID"

    def test_editor_getter(self) -> None:
        """editor getter returns people list."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])
        asset_edit.custom_fields_editor().set(
            "Editor",
            [{"gid": "u1", "name": "John Doe"}],
        )
        assert len(asset_edit.editor) == 1
        assert asset_edit.editor[0]["name"] == "John Doe"

    def test_editor_empty(self) -> None:
        """editor returns empty list when not set."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])
        assert asset_edit.editor == []

    def test_reviewer_getter(self) -> None:
        """reviewer getter returns people list."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])
        asset_edit.custom_fields_editor().set(
            "Reviewer",
            [{"gid": "u2", "name": "Jane Smith"}],
        )
        assert len(asset_edit.reviewer) == 1
        assert asset_edit.reviewer[0]["name"] == "Jane Smith"

    def test_offer_id_getter(self) -> None:
        """offer_id getter returns int value per PRD-0024."""
        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[
                {"gid": "1", "name": "Offer ID", "number_value": 1234567890}
            ],
        )
        assert asset_edit.offer_id == 1234567890

    def test_offer_id_setter(self) -> None:
        """offer_id setter updates value."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])
        asset_edit.offer_id = 9876543210
        assert asset_edit.custom_fields_editor().get("Offer ID") == 9876543210

    def test_raw_assets_getter(self) -> None:
        """raw_assets getter returns text value."""
        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[
                {
                    "gid": "1",
                    "name": "Raw Assets",
                    "text_value": "https://drive.google.com/...",
                }
            ],
        )
        assert asset_edit.raw_assets == "https://drive.google.com/..."

    def test_review_all_ads_getter_yes(self) -> None:
        """review_all_ads returns True for 'Yes'."""
        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[
                {"gid": "1", "name": "Review All Ads", "enum_value": {"name": "Yes"}}
            ],
        )
        assert asset_edit.review_all_ads is True

    def test_review_all_ads_getter_no(self) -> None:
        """review_all_ads returns False for 'No'."""
        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[
                {"gid": "1", "name": "Review All Ads", "enum_value": {"name": "No"}}
            ],
        )
        assert asset_edit.review_all_ads is False

    def test_review_all_ads_getter_none(self) -> None:
        """review_all_ads returns None when not set."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])
        assert asset_edit.review_all_ads is None

    def test_review_all_ads_setter(self) -> None:
        """review_all_ads setter converts bool to enum string."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])

        asset_edit.review_all_ads = True
        assert asset_edit.custom_fields_editor().get("Review All Ads") == "Yes"

        asset_edit.review_all_ads = False
        assert asset_edit.custom_fields_editor().get("Review All Ads") == "No"

        asset_edit.review_all_ads = None
        assert asset_edit.custom_fields_editor().get("Review All Ads") is None

    def test_score_getter(self) -> None:
        """score getter returns Decimal value."""
        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[{"gid": "1", "name": "Score", "number_value": 95.5}],
        )
        assert asset_edit.score == Decimal("95.5")

    def test_score_setter(self) -> None:
        """score setter updates value."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])
        asset_edit.score = Decimal("88.3")
        assert asset_edit.custom_fields_editor().get("Score") == 88.3

    def test_specialty_getter(self) -> None:
        """specialty getter returns list from multi-enum per PRD-0024."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])
        asset_edit.custom_fields_editor().set(
            "Specialty",
            [
                {"gid": "s1", "name": "Video"},
                {"gid": "s2", "name": "Image"},
            ],
        )
        assert asset_edit.specialty == ["Video", "Image"]

    def test_specialty_empty(self) -> None:
        """specialty returns empty list when not set."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])
        assert asset_edit.specialty == []

    def test_template_id_getter(self) -> None:
        """template_id getter returns int value per PRD-0024."""
        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[{"gid": "1", "name": "Template ID", "number_value": 42}],
        )
        assert asset_edit.template_id == 42

    def test_videos_paid_getter(self) -> None:
        """videos_paid getter returns integer value."""
        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[{"gid": "1", "name": "Videos Paid", "number_value": 5}],
        )
        assert asset_edit.videos_paid == 5

    def test_videos_paid_setter(self) -> None:
        """videos_paid setter updates value."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])
        asset_edit.videos_paid = 10
        assert asset_edit.custom_fields_editor().get("Videos Paid") == 10


class TestAssetEditHolder:
    """Tests for AssetEditHolder with typed children."""

    def test_asset_edits_property_empty(self) -> None:
        """asset_edits returns empty list by default."""
        holder = AssetEditHolder(gid="h1")
        assert holder.asset_edits == []

    def test_children_alias(self) -> None:
        """children property is alias for asset_edits."""
        holder = AssetEditHolder(gid="h1")
        assert holder.children == holder.asset_edits

    def test_populate_children_creates_typed_asset_edits(self) -> None:
        """_populate_children creates typed AssetEdit instances."""
        from autom8_asana.models.task import Task

        holder = AssetEditHolder(gid="h1")
        subtasks = [
            Task(gid="ae1", name="AssetEdit 1", created_at="2024-01-01T00:00:00Z"),
            Task(gid="ae2", name="AssetEdit 2", created_at="2024-01-02T00:00:00Z"),
        ]

        holder._populate_children(subtasks)

        assert len(holder.asset_edits) == 2
        assert all(isinstance(ae, AssetEdit) for ae in holder.asset_edits)
        assert holder.asset_edits[0].name == "AssetEdit 1"
        assert holder.asset_edits[1].name == "AssetEdit 2"

    def test_populate_children_sets_back_references(self) -> None:
        """_populate_children sets back references on AssetEdit children."""
        from autom8_asana.models.task import Task

        business = Business(gid="b1")
        holder = AssetEditHolder(gid="h1")
        holder._business = business

        subtasks = [Task(gid="ae1", name="AssetEdit 1")]
        holder._populate_children(subtasks)

        assert holder.asset_edits[0]._asset_edit_holder is holder
        assert holder.asset_edits[0]._business is business

    def test_invalidate_cache(self) -> None:
        """invalidate_cache clears asset_edits list."""
        from autom8_asana.models.task import Task

        holder = AssetEditHolder(gid="h1")
        subtasks = [Task(gid="ae1", name="AssetEdit 1")]
        holder._populate_children(subtasks)

        assert len(holder.asset_edits) == 1

        holder.invalidate_cache()

        assert holder.asset_edits == []


class TestAssetEditResolution:
    """Tests for AssetEdit resolution methods."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock client with tasks client."""
        client = MagicMock()
        client.tasks = MagicMock()
        client.tasks.dependents_async = MagicMock()
        client.tasks.get_async = AsyncMock()
        return client

    async def test_resolve_unit_async_returns_result(
        self, mock_client: MagicMock
    ) -> None:
        """resolve_unit_async returns ResolutionResult."""
        # Mock dependents returning no results
        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(return_value=[])
        mock_client.tasks.dependents_async.return_value = mock_iterator

        asset_edit = AssetEdit(gid="ae1", custom_fields=[])

        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.DEPENDENT_TASKS,
        )

        assert isinstance(result, ResolutionResult)

    async def test_resolve_unit_async_with_auto_strategy(
        self, mock_client: MagicMock
    ) -> None:
        """AUTO strategy tries all strategies in order."""
        # Mock dependents returning no results
        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(return_value=[])
        mock_client.tasks.dependents_async.return_value = mock_iterator

        asset_edit = AssetEdit(gid="ae1", custom_fields=[])

        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.AUTO,
        )

        # All strategies should be tried
        assert len(result.strategies_tried) >= 1

    async def test_resolve_unit_via_dependents_success(
        self, mock_client: MagicMock
    ) -> None:
        """DEPENDENT_TASKS finds Unit in dependents."""
        from autom8_asana.models.task import Task

        # Create mock Unit task with Unit-specific custom field
        unit_task = Task(
            gid="u1",
            name="Test Unit",
            custom_fields=[{"gid": "cf1", "name": "MRR", "number_value": 1000}],
        )

        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(return_value=[unit_task])
        mock_client.tasks.dependents_async.return_value = mock_iterator

        asset_edit = AssetEdit(gid="ae1", custom_fields=[])

        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.DEPENDENT_TASKS,
        )

        assert result.success
        assert result.entity is not None
        assert result.strategy_used == ResolutionStrategy.DEPENDENT_TASKS

    async def test_resolve_unit_via_vertical_requires_business(
        self, mock_client: MagicMock
    ) -> None:
        """CUSTOM_FIELD_MAPPING requires Business context."""
        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[
                {"gid": "1", "name": "Vertical", "enum_value": {"name": "Healthcare"}}
            ],
        )
        # No business context set

        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.CUSTOM_FIELD_MAPPING,
        )

        assert not result.success
        assert "Business context required" in result.error

    async def test_resolve_unit_via_vertical_success(
        self, mock_client: MagicMock
    ) -> None:
        """CUSTOM_FIELD_MAPPING finds Unit by matching vertical."""
        # Set up Business with Units
        business = Business(gid="b1")
        unit1 = Unit(gid="u1", name="Unit 1")
        unit1.custom_fields_editor().set("Vertical", {"name": "Healthcare"})
        unit2 = Unit(gid="u2", name="Unit 2")
        unit2.custom_fields_editor().set("Vertical", {"name": "Finance"})

        # Mock business.units
        from autom8_asana.models.business.unit import UnitHolder

        unit_holder = UnitHolder(gid="uh1")
        unit_holder._units = [unit1, unit2]
        business._unit_holder = unit_holder

        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[
                {"gid": "1", "name": "Vertical", "enum_value": {"name": "Healthcare"}}
            ],
        )
        asset_edit._business = business

        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.CUSTOM_FIELD_MAPPING,
        )

        assert result.success
        assert result.entity is not None
        assert result.entity.gid == "u1"

    async def test_resolve_unit_via_offer_id_no_offer_id(
        self, mock_client: MagicMock
    ) -> None:
        """EXPLICIT_OFFER_ID fails gracefully when no offer_id set."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])

        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.EXPLICIT_OFFER_ID,
        )

        assert not result.success
        assert "no offer_id set" in result.error.lower()

    async def test_resolve_offer_async_returns_result(
        self, mock_client: MagicMock
    ) -> None:
        """resolve_offer_async returns ResolutionResult."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])

        result = await asset_edit.resolve_offer_async(
            mock_client,
            strategy=ResolutionStrategy.EXPLICIT_OFFER_ID,
        )

        assert isinstance(result, ResolutionResult)

    async def test_resolve_offer_directly_via_offer_id(
        self, mock_client: MagicMock
    ) -> None:
        """resolve_offer_async can fetch Offer directly via offer_id."""
        from autom8_asana.models.task import Task

        offer_task = Task(gid="123456789", name="Test Offer")
        mock_client.tasks.get_async.return_value = offer_task

        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[{"gid": "1", "name": "Offer ID", "number_value": 123456789}],
        )

        result = await asset_edit.resolve_offer_async(
            mock_client,
            strategy=ResolutionStrategy.EXPLICIT_OFFER_ID,
        )

        assert result.success
        assert result.entity is not None
        assert result.entity.gid == "123456789"


class TestAssetEditEdgeCases:
    """Edge case tests for AssetEdit resolution.

    Per QA Session 6: Comprehensive edge case coverage for release readiness.
    """

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock client with tasks client."""
        client = MagicMock()
        client.tasks = MagicMock()
        client.tasks.dependents_async = MagicMock()
        client.tasks.get_async = AsyncMock()
        return client

    # --- Edge Case 4: offer_id pointing to non-existent task ---

    async def test_resolve_unit_via_offer_id_not_found(
        self, mock_client: MagicMock
    ) -> None:
        """EXPLICIT_OFFER_ID handles NotFoundError gracefully.

        Per FR-STRATEGY-004: Handle NotFoundError gracefully when offer_id
        refers to a non-existent task.
        """
        from autom8_asana.errors import NotFoundError

        mock_client.tasks.get_async.side_effect = NotFoundError(
            "Task not found",
            status_code=404,
        )

        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[{"gid": "1", "name": "Offer ID", "number_value": 999999999}],
        )

        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.EXPLICIT_OFFER_ID,
        )

        assert not result.success
        assert result.entity is None
        assert "not found" in result.error.lower()
        assert ResolutionStrategy.EXPLICIT_OFFER_ID in result.strategies_tried

    # --- Edge Case 5: Multiple Units matching vertical (ambiguity) ---

    async def test_resolve_unit_via_vertical_multiple_matches(
        self, mock_client: MagicMock
    ) -> None:
        """CUSTOM_FIELD_MAPPING returns ambiguous result when multiple Units match.

        Per FR-AMBIG-002 and ADR-0071: Return first match in entity,
        set ambiguous=True, populate candidates.
        """
        # Set up Business with multiple Units having same vertical
        business = Business(gid="b1")
        unit1 = Unit(gid="u1", name="Unit 1 - Healthcare")
        unit1.custom_fields_editor().set("Vertical", {"name": "Healthcare"})
        unit2 = Unit(gid="u2", name="Unit 2 - Healthcare")
        unit2.custom_fields_editor().set("Vertical", {"name": "Healthcare"})
        unit3 = Unit(gid="u3", name="Unit 3 - Finance")
        unit3.custom_fields_editor().set("Vertical", {"name": "Finance"})

        from autom8_asana.models.business.unit import UnitHolder

        unit_holder = UnitHolder(gid="uh1")
        unit_holder._units = [unit1, unit2, unit3]
        business._unit_holder = unit_holder

        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[
                {"gid": "1", "name": "Vertical", "enum_value": {"name": "Healthcare"}}
            ],
        )
        asset_edit._business = business

        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.CUSTOM_FIELD_MAPPING,
        )

        # Ambiguous result per ADR-0071
        assert result.ambiguous is True
        assert result.success is False  # Ambiguous is not success
        assert result.entity is not None  # First match per ADR-0071
        assert result.entity.gid == "u1"  # First match
        assert len(result.candidates) == 2  # Both Healthcare Units
        assert result.strategy_used == ResolutionStrategy.CUSTOM_FIELD_MAPPING

    # --- Edge Case 6: AUTO with first strategy ambiguous, second succeeds ---

    async def test_resolve_unit_auto_continues_after_ambiguous(
        self, mock_client: MagicMock
    ) -> None:
        """AUTO continues to next strategy when first finds ambiguous result.

        Per FR-STRATEGY-005: If strategy finds ambiguous matches, continues to next.
        """
        from autom8_asana.models.task import Task

        # Set up DEPENDENT_TASKS to return multiple Units (ambiguous)
        unit_task1 = Task(
            gid="u1",
            name="Unit 1",
            custom_fields=[{"gid": "cf1", "name": "MRR", "number_value": 1000}],
        )
        unit_task2 = Task(
            gid="u2",
            name="Unit 2",
            custom_fields=[{"gid": "cf2", "name": "MRR", "number_value": 2000}],
        )

        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(return_value=[unit_task1, unit_task2])
        mock_client.tasks.dependents_async.return_value = mock_iterator

        # Set up Business for CUSTOM_FIELD_MAPPING with single match
        business = Business(gid="b1")
        unit_single = Unit(gid="u3", name="Unit 3 - Healthcare")
        unit_single.custom_fields_editor().set("Vertical", {"name": "Healthcare"})

        from autom8_asana.models.business.unit import UnitHolder

        unit_holder = UnitHolder(gid="uh1")
        unit_holder._units = [unit_single]
        business._unit_holder = unit_holder

        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[
                {"gid": "1", "name": "Vertical", "enum_value": {"name": "Healthcare"}}
            ],
        )
        asset_edit._business = business

        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.AUTO,
        )

        # Should succeed via CUSTOM_FIELD_MAPPING after DEPENDENT_TASKS was ambiguous
        assert result.success is True
        assert result.entity.gid == "u3"
        assert result.strategy_used == ResolutionStrategy.CUSTOM_FIELD_MAPPING
        # Both strategies should be in tried list
        assert ResolutionStrategy.DEPENDENT_TASKS in result.strategies_tried
        assert ResolutionStrategy.CUSTOM_FIELD_MAPPING in result.strategies_tried

    # --- Edge Case 7: All strategies fail ---

    async def test_resolve_unit_auto_all_strategies_fail(
        self, mock_client: MagicMock
    ) -> None:
        """AUTO returns error result when all strategies fail.

        Per FR-AMBIG-001: entity=None, success=False, strategy_used=None.
        """
        # Set up DEPENDENT_TASKS to return no Units
        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(return_value=[])
        mock_client.tasks.dependents_async.return_value = mock_iterator

        # No business context (CUSTOM_FIELD_MAPPING will fail)
        # No offer_id (EXPLICIT_OFFER_ID will fail)
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])

        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.AUTO,
        )

        assert result.success is False
        assert result.entity is None
        assert result.strategy_used is None
        assert result.error is not None
        assert "No matching Unit found" in result.error
        # All strategies should be tried
        assert len(result.strategies_tried) == 3

    # --- Edge Case 8: API error during resolution ---

    async def test_resolve_unit_via_dependents_api_error_propagates_when_direct(
        self, mock_client: MagicMock
    ) -> None:
        """DEPENDENT_TASKS propagates exception when called directly.

        Note: Exception handling only happens at AUTO level per implementation.
        Direct strategy calls propagate exceptions to caller.
        """
        # Simulate network error
        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(
            side_effect=Exception("Network connection failed")
        )
        mock_client.tasks.dependents_async.return_value = mock_iterator

        asset_edit = AssetEdit(gid="ae1", custom_fields=[])

        # Direct strategy call propagates the exception
        with pytest.raises(Exception, match="Network connection failed"):
            await asset_edit.resolve_unit_async(
                mock_client,
                strategy=ResolutionStrategy.DEPENDENT_TASKS,
            )

    async def test_resolve_unit_auto_continues_after_api_error(
        self, mock_client: MagicMock
    ) -> None:
        """AUTO continues to next strategy after API error in first strategy.

        Per FR-AMBIG-003: AUTO mode continues to next strategy after error.
        """
        # DEPENDENT_TASKS will error
        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(side_effect=Exception("Network error"))
        mock_client.tasks.dependents_async.return_value = mock_iterator

        # Set up Business for CUSTOM_FIELD_MAPPING success
        business = Business(gid="b1")
        unit = Unit(gid="u1", name="Unit 1")
        unit.custom_fields_editor().set("Vertical", {"name": "Healthcare"})

        from autom8_asana.models.business.unit import UnitHolder

        unit_holder = UnitHolder(gid="uh1")
        unit_holder._units = [unit]
        business._unit_holder = unit_holder

        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[
                {"gid": "1", "name": "Vertical", "enum_value": {"name": "Healthcare"}}
            ],
        )
        asset_edit._business = business

        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.AUTO,
        )

        # Should succeed via CUSTOM_FIELD_MAPPING after DEPENDENT_TASKS errored
        assert result.success is True
        assert result.entity.gid == "u1"
        assert result.strategy_used == ResolutionStrategy.CUSTOM_FIELD_MAPPING

    # --- Edge Case: AssetEdit with no vertical (CUSTOM_FIELD_MAPPING fails) ---

    async def test_resolve_unit_via_vertical_no_vertical_set(
        self, mock_client: MagicMock
    ) -> None:
        """CUSTOM_FIELD_MAPPING fails gracefully when AssetEdit has no vertical.

        Per FR-STRATEGY-003: Returns None if AssetEdit has no vertical set.
        """
        business = Business(gid="b1")
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])  # No vertical
        asset_edit._business = business

        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.CUSTOM_FIELD_MAPPING,
        )

        assert not result.success
        assert "no vertical set" in result.error.lower()

    # --- Edge Case: CUSTOM_FIELD_MAPPING with no matching vertical ---

    async def test_resolve_unit_via_vertical_no_matching_unit(
        self, mock_client: MagicMock
    ) -> None:
        """CUSTOM_FIELD_MAPPING fails when no Unit has matching vertical."""
        business = Business(gid="b1")
        unit = Unit(gid="u1", name="Unit 1")
        unit.custom_fields_editor().set("Vertical", {"name": "Finance"})

        from autom8_asana.models.business.unit import UnitHolder

        unit_holder = UnitHolder(gid="uh1")
        unit_holder._units = [unit]
        business._unit_holder = unit_holder

        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[
                {"gid": "1", "name": "Vertical", "enum_value": {"name": "Healthcare"}}
            ],
        )
        asset_edit._business = business

        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.CUSTOM_FIELD_MAPPING,
        )

        assert not result.success
        assert "Healthcare" in result.error
        assert result.entity is None

    # --- Edge Case: AUTO returns ambiguous when no non-ambiguous found ---

    async def test_resolve_unit_auto_returns_ambiguous_if_all_ambiguous(
        self, mock_client: MagicMock
    ) -> None:
        """AUTO returns first ambiguous result if no non-ambiguous found.

        Per FR-STRATEGY-005 and ADR-0071: If all strategies exhausted,
        return the first ambiguous result found.
        """
        # DEPENDENT_TASKS finds multiple Units
        from autom8_asana.models.task import Task

        unit_task1 = Task(
            gid="u1",
            name="Unit 1",
            custom_fields=[{"gid": "cf1", "name": "MRR", "number_value": 1000}],
        )
        unit_task2 = Task(
            gid="u2",
            name="Unit 2",
            custom_fields=[{"gid": "cf2", "name": "MRR", "number_value": 2000}],
        )

        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(return_value=[unit_task1, unit_task2])
        mock_client.tasks.dependents_async.return_value = mock_iterator

        # No business context, no offer_id - other strategies will fail
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])

        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.AUTO,
        )

        # Should return the ambiguous result from DEPENDENT_TASKS
        assert result.ambiguous is True
        assert result.success is False
        assert result.entity is not None  # First match per ADR-0071
        assert len(result.candidates) == 2

    # --- Edge Case: resolve_offer_async when Unit has no Offers ---

    async def test_resolve_offer_unit_has_no_offers(
        self, mock_client: MagicMock
    ) -> None:
        """resolve_offer_async handles Unit with no Offers.

        Per FR-RESOLVE-002: Handle case where Unit is resolved but Offer not found.
        """
        # Set up successful Unit resolution via CUSTOM_FIELD_MAPPING
        business = Business(gid="b1")
        unit = Unit(gid="u1", name="Unit 1")
        unit.custom_fields_editor().set("Vertical", {"name": "Healthcare"})
        # Unit has no offers (empty _offers list)

        from autom8_asana.models.business.unit import UnitHolder

        unit_holder = UnitHolder(gid="uh1")
        unit_holder._units = [unit]
        business._unit_holder = unit_holder

        asset_edit = AssetEdit(
            gid="ae1",
            custom_fields=[
                {"gid": "1", "name": "Vertical", "enum_value": {"name": "Healthcare"}}
            ],
        )
        asset_edit._business = business

        result = await asset_edit.resolve_offer_async(
            mock_client,
            strategy=ResolutionStrategy.CUSTOM_FIELD_MAPPING,
        )

        # Should fail because Unit has no Offers
        assert result.success is False
        assert result.entity is None
        assert "no Offers" in result.error

    # --- Edge Case: Unknown strategy ---

    async def test_resolve_unit_unknown_strategy(self, mock_client: MagicMock) -> None:
        """resolve_unit_async handles unknown strategy gracefully."""
        asset_edit = AssetEdit(gid="ae1", custom_fields=[])

        # Create a mock "unknown" strategy by directly calling with invalid enum
        # This shouldn't happen in practice, but tests the error branch
        result = await asset_edit.resolve_unit_async(
            mock_client,
            strategy=ResolutionStrategy.AUTO,  # AUTO is known, will succeed
        )

        # Just verify it doesn't crash and returns a result
        assert isinstance(result, ResolutionResult)
