"""Integration tests for Cascading Field Resolution.

Per TDD-CASCADING-FIELD-RESOLUTION-001 Task 4: QA validation of end-to-end
cascading field resolution enabling Entity Resolver to correctly resolve
phone/vertical pairs to Unit GIDs.

Tests verify:
- cascade: source prefix in UNIT_SCHEMA triggers parent traversal
- Office Phone cascades from Business (grandparent) to Unit
- GidLookupIndex correctly indexes cascaded office_phone values
- BaseExtractor.extract_async() handles cascade: fields
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.resolver.cascading import CascadingFieldResolver
from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA
from autom8_asana.models.business.detection import EntityType
from autom8_asana.models.business.fields import get_cascading_field
from autom8_asana.services.gid_lookup import GidLookupIndex

# =============================================================================
# Test Fixtures
# =============================================================================


class MockNameGid:
    """Mock NameGid object for parent reference."""

    def __init__(self, gid: str, name: str | None = None) -> None:
        self.gid = gid
        self.name = name


class MockTask:
    """Mock Task object for testing cascading resolution."""

    def __init__(
        self,
        gid: str,
        name: str | None = None,
        parent: MockNameGid | None = None,
        custom_fields: list[dict[str, Any]] | None = None,
        memberships: list[dict[str, Any]] | None = None,
        created_at: str = "2024-01-01T00:00:00Z",
        modified_at: str = "2024-01-01T00:00:00Z",
        completed: bool = False,
        completed_at: str | None = None,
        due_on: str | None = None,
        tags: list[Any] | None = None,
        resource_subtype: str = "default_task",
    ) -> None:
        self.gid = gid
        self.name = name
        self.parent = parent
        self.custom_fields = custom_fields or []
        self.memberships = memberships or []
        self.created_at = created_at
        self.modified_at = modified_at
        self.completed = completed
        self.completed_at = completed_at
        self.due_on = due_on
        self.tags = tags or []
        self.resource_subtype = resource_subtype


def make_custom_field(
    name: str,
    value: Any,
    resource_subtype: str = "text",
) -> dict[str, Any]:
    """Create a custom field dict for testing."""
    cf: dict[str, Any] = {
        "gid": f"cf_{name.lower().replace(' ', '_')}",
        "name": name,
        "resource_subtype": resource_subtype,
    }

    match resource_subtype:
        case "text":
            cf["text_value"] = value
        case "number":
            cf["number_value"] = value
        case "enum":
            cf["enum_value"] = (
                {"gid": f"enum_{value}", "name": value} if value else None
            )
        case "multi_enum":
            cf["multi_enum_values"] = [
                {"gid": f"me_{v}", "name": v} for v in (value or [])
            ]

    return cf


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock AsanaClient with tasks.get_async method.

    Sets unified_store=None to ensure tests use legacy cascade resolution path.
    """
    client = MagicMock()
    client.tasks = MagicMock()
    client.tasks.get_async = AsyncMock()
    # Explicitly set unified_store to None for legacy cascade path
    client.unified_store = None
    return client


# =============================================================================
# Test: UNIT_SCHEMA Contains cascade:Office Phone
# =============================================================================


class TestUnitSchemaCascadeSource:
    """Verify UNIT_SCHEMA uses cascade: prefix for office_phone."""

    def test_office_phone_column_has_cascade_source(self) -> None:
        """Test office_phone column in UNIT_SCHEMA uses cascade: source."""
        office_phone_col = None
        for col in UNIT_SCHEMA.columns:
            if col.name == "office_phone":
                office_phone_col = col
                break

        assert office_phone_col is not None, (
            "office_phone column not found in UNIT_SCHEMA"
        )
        assert office_phone_col.source == "cascade:Office Phone", (
            f"Expected source='cascade:Office Phone', got source='{office_phone_col.source}'"
        )

    def test_office_phone_field_in_cascading_registry(self) -> None:
        """Test Office Phone is registered in CASCADING_FIELD_REGISTRY."""
        result = get_cascading_field("Office Phone")

        assert result is not None, "Office Phone not found in CASCADING_FIELD_REGISTRY"
        owner_class, field_def = result
        assert owner_class.__name__ == "Business"
        assert field_def.name == "Office Phone"
        assert field_def.allow_override is False


# =============================================================================
# Test: End-to-End Cascading Resolution
# =============================================================================


class TestEndToEndCascadingResolution:
    """Integration tests for end-to-end cascading field resolution."""

    @pytest.mark.asyncio
    async def test_unit_task_resolves_office_phone_from_business_grandparent(
        self, mock_client: MagicMock
    ) -> None:
        """Test Unit task resolves Office Phone from Business (2 levels up).

        Hierarchy: Business -> UnitHolder -> Unit
        Office Phone lives on Business, should cascade to Unit.
        """
        # Create task hierarchy
        business_task = MockTask(
            gid="business_123",
            name="Acme Healthcare",
            custom_fields=[
                make_custom_field("Office Phone", "+12604442080", "text"),
                make_custom_field("Company ID", "ACME001", "text"),
            ],
        )

        unit_holder_task = MockTask(
            gid="unit_holder_456",
            name="Units",
            parent=MockNameGid(gid="business_123"),
        )

        unit_task = MockTask(
            gid="unit_789",
            name="Main Office",
            parent=MockNameGid(gid="unit_holder_456"),
            custom_fields=[
                make_custom_field("Vertical", "chiropractic", "enum"),
            ],
        )

        # Configure mock API responses
        mock_client.tasks.get_async.side_effect = [unit_holder_task, business_task]

        # Create resolver
        resolver = CascadingFieldResolver(mock_client)

        # Patch entity type detection
        with patch(
            "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
        ) as mock_detect:
            mock_detect.side_effect = [
                MagicMock(entity_type=EntityType.UNIT),
                MagicMock(entity_type=EntityType.UNIT_HOLDER),
                MagicMock(entity_type=EntityType.BUSINESS),
            ]

            result = await resolver.resolve_async(unit_task, "Office Phone")  # type: ignore[arg-type]

        # Assert Office Phone resolved from Business
        assert result == "+12604442080"
        assert mock_client.tasks.get_async.call_count == 2

    @pytest.mark.asyncio
    async def test_parent_cache_efficiency_for_batch_extraction(
        self, mock_client: MagicMock
    ) -> None:
        """Test parent cache prevents duplicate API calls in batch extraction.

        Per NFR-CASCADE-001: Batch of 100 tasks with same Business parent
        should make minimal API calls due to caching.
        """
        # Create shared parent hierarchy
        business_task = MockTask(
            gid="business_123",
            name="Acme Healthcare",
            custom_fields=[
                make_custom_field("Office Phone", "+12604442080", "text"),
            ],
        )

        unit_holder_task = MockTask(
            gid="unit_holder_456",
            name="Units",
            parent=MockNameGid(gid="business_123"),
        )

        # Create multiple Unit tasks sharing the same parent chain
        unit_tasks = [
            MockTask(
                gid=f"unit_{i}",
                name=f"Unit {i}",
                parent=MockNameGid(gid="unit_holder_456"),
            )
            for i in range(10)
        ]

        # Configure mock API - should only be called twice total (then cached)
        mock_client.tasks.get_async.side_effect = [unit_holder_task, business_task]

        resolver = CascadingFieldResolver(mock_client)

        # Create the detect_entity_type mock responses for the full traversal
        # First resolution: unit_0 -> UNIT, then fetch unit_holder -> UNIT_HOLDER,
        # then fetch business -> BUSINESS (where Office Phone is found)
        # Subsequent resolutions: unit_N -> UNIT, then use cached parents
        detection_responses = []
        for _ in range(10):
            # Each unit starts as UNIT
            detection_responses.append(MagicMock(entity_type=EntityType.UNIT))
            # Then checks cached unit_holder (or fetches first time)
            detection_responses.append(MagicMock(entity_type=EntityType.UNIT_HOLDER))
            # Then checks cached business (or fetches first time)
            detection_responses.append(MagicMock(entity_type=EntityType.BUSINESS))

        with patch(
            "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
        ) as mock_detect:
            mock_detect.side_effect = detection_responses

            # Resolve all unit tasks
            results = []
            for unit_task in unit_tasks:
                result = await resolver.resolve_async(unit_task, "Office Phone")  # type: ignore[arg-type]
                results.append(result)

        # All should resolve to same value
        assert all(r == "+12604442080" for r in results), f"Got results: {results}"

        # API should only be called twice (parents cached after first resolution)
        assert mock_client.tasks.get_async.call_count == 2

        # Cache should contain both parents
        assert resolver.get_cache_size() == 2


# =============================================================================
# Test: GidLookupIndex with Cascaded Office Phone
# =============================================================================


class TestGidLookupIndexWithCascadedValues:
    """Test GidLookupIndex correctly indexes cascaded office_phone values."""

    def test_index_from_dataframe_with_office_phone(self) -> None:
        """Test GidLookupIndex.from_dataframe() indexes office_phone correctly."""
        # Create DataFrame simulating Unit data with cascaded office_phone
        df = pl.DataFrame(
            {
                "gid": ["unit_001", "unit_002", "unit_003"],
                "name": ["Unit A", "Unit B", "Unit C"],
                "office_phone": ["+12604442080", "+19127481506", "+14045551234"],
                "vertical": ["chiropractic", "chiropractic", "dental"],
            }
        )

        index = GidLookupIndex.from_dataframe(df)

        # Verify index contains expected entries
        assert len(index) == 3

        # Create PhoneVerticalPair-like object for lookup
        from autom8_asana.models.contracts.phone_vertical import PhoneVerticalPair

        pair1 = PhoneVerticalPair(office_phone="+12604442080", vertical="chiropractic")
        pair2 = PhoneVerticalPair(office_phone="+19127481506", vertical="chiropractic")
        pair3 = PhoneVerticalPair(office_phone="+14045551234", vertical="dental")

        # Verify lookups return correct GIDs
        assert index.get_gid(pair1) == "unit_001"
        assert index.get_gid(pair2) == "unit_002"
        assert index.get_gid(pair3) == "unit_003"

    def test_index_handles_null_office_phone(self) -> None:
        """Test GidLookupIndex filters out rows with null office_phone."""
        df = pl.DataFrame(
            {
                "gid": ["unit_001", "unit_002", "unit_003"],
                "name": ["Unit A", "Unit B", "Unit C"],
                "office_phone": ["+12604442080", None, "+14045551234"],
                "vertical": ["chiropractic", "dental", "medical"],
            }
        )

        index = GidLookupIndex.from_dataframe(df)

        # Should only index 2 entries (skipping null office_phone)
        assert len(index) == 2


# =============================================================================
# Test: BaseExtractor cascade: Handling
# =============================================================================


class MinimalExtractor(BaseExtractor):
    """Minimal extractor for testing cascade: support in BaseExtractor."""

    def _create_row(self, data: dict[str, Any]) -> dict[str, Any]:
        # Return raw dict for testing - avoid TaskRow validation complexity
        return data  # type: ignore[return-value]


class TestBaseExtractorCascadeSupport:
    """Test BaseExtractor handles cascade: source prefix correctly."""

    def test_sync_extract_raises_for_cascade_source(
        self, mock_client: MagicMock
    ) -> None:
        """Test sync extract() raises ValueError for cascade: sources.

        Note: The ValueError is raised during _extract_column, but since
        BaseExtractor catches exceptions in extract() and stores them as
        errors, we check that office_phone is None (error occurred).
        """
        schema = DataFrameSchema(
            name="test",
            task_type="*",
            columns=[
                ColumnDef(name="gid", dtype="Utf8", nullable=False, source="gid"),
                ColumnDef(
                    name="office_phone",
                    dtype="Utf8",
                    nullable=True,
                    source="cascade:Office Phone",
                ),
            ],
            version="1.0.0",
        )

        extractor = MinimalExtractor(schema, client=mock_client)
        task = MockTask(gid="123", name="Test")

        # BaseExtractor.extract() catches exceptions per FR-ERROR-005
        # So it won't raise, but the cascade field will be None (extraction failed)
        result = extractor.extract(task)  # type: ignore[arg-type]
        assert result["gid"] == "123"
        # office_phone should be None because extraction failed with ValueError
        assert result["office_phone"] is None

    @pytest.mark.asyncio
    async def test_async_extract_resolves_cascade_source(
        self, mock_client: MagicMock
    ) -> None:
        """Test async extract_async() resolves cascade: sources."""
        schema = DataFrameSchema(
            name="test",
            task_type="*",
            columns=[
                ColumnDef(name="gid", dtype="Utf8", nullable=False, source="gid"),
                ColumnDef(name="name", dtype="Utf8", nullable=True, source="name"),
                ColumnDef(
                    name="office_phone",
                    dtype="Utf8",
                    nullable=True,
                    source="cascade:Office Phone",
                ),
            ],
            version="1.0.0",
        )

        # Create hierarchy
        business_task = MockTask(
            gid="business_123",
            name="Acme Corp",
            custom_fields=[
                make_custom_field("Office Phone", "+15551234567", "text"),
            ],
        )

        unit_task = MockTask(
            gid="unit_456",
            name="Test Unit",
            parent=MockNameGid(gid="business_123"),
        )

        mock_client.tasks.get_async.return_value = business_task

        extractor = MinimalExtractor(schema, client=mock_client)

        with patch(
            "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
        ) as mock_detect:
            mock_detect.side_effect = [
                MagicMock(entity_type=EntityType.UNIT),
                MagicMock(entity_type=EntityType.BUSINESS),
            ]

            row = await extractor.extract_async(unit_task)  # type: ignore[arg-type]

        # Verify extraction results (row is a dict from MinimalExtractor)
        assert row["gid"] == "unit_456"
        assert row["name"] == "Test Unit"
        # office_phone should be resolved from parent via cascade:
        assert row["office_phone"] == "+15551234567"


# =============================================================================
# Test: Error Handling
# =============================================================================


class TestCascadingErrorHandling:
    """Test error handling in cascading resolution."""

    @pytest.mark.asyncio
    async def test_missing_client_returns_none_for_cascade_field(self) -> None:
        """Test extractor returns None for cascade: field if client not provided.

        Note: BaseExtractor catches exceptions per FR-ERROR-005, so instead
        of raising, the cascade field will be None (extraction failed).
        """
        schema = DataFrameSchema(
            name="test",
            task_type="*",
            columns=[
                ColumnDef(name="gid", dtype="Utf8", nullable=False, source="gid"),
                ColumnDef(
                    name="office_phone",
                    dtype="Utf8",
                    nullable=True,
                    source="cascade:Office Phone",
                ),
            ],
            version="1.0.0",
        )

        # No client provided
        extractor = MinimalExtractor(schema, client=None)
        task = MockTask(gid="123", name="Test")

        # BaseExtractor.extract_async() catches exceptions per FR-ERROR-005
        result = await extractor.extract_async(task)  # type: ignore[arg-type]
        assert result["gid"] == "123"
        # office_phone should be None because extraction failed (no client)
        assert result["office_phone"] is None

    @pytest.mark.asyncio
    async def test_broken_parent_chain_returns_none(
        self, mock_client: MagicMock
    ) -> None:
        """Test cascading returns None when parent chain is broken."""
        resolver = CascadingFieldResolver(mock_client)

        # Task with no parent
        orphan_task = MockTask(gid="orphan_123", name="Orphan Task", parent=None)

        with patch(
            "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
        ) as mock_detect:
            mock_detect.return_value = MagicMock(entity_type=EntityType.UNIT)

            result = await resolver.resolve_async(orphan_task, "Office Phone")  # type: ignore[arg-type]

        assert result is None
        mock_client.tasks.get_async.assert_not_called()


# =============================================================================
# Test: Production Validation Scenarios
# =============================================================================


class TestProductionValidationScenarios:
    """Scenarios that should work in production.

    Per TDD Task 4: Document what needs to be validated in production.
    """

    @pytest.mark.asyncio
    async def test_scenario_chiropractic_unit_with_known_phone(
        self, mock_client: MagicMock
    ) -> None:
        """Test: +12604442080 / chiropractic should return Unit GID.

        This is a known production phone/vertical pair that was returning
        NOT_FOUND before the cascading fix.
        """
        # Simulate production hierarchy
        business_task = MockTask(
            gid="business_prod_001",
            name="Production Business",
            custom_fields=[
                make_custom_field("Office Phone", "+12604442080", "text"),
            ],
        )

        unit_holder_task = MockTask(
            gid="unit_holder_prod_001",
            name="Units",
            parent=MockNameGid(gid="business_prod_001"),
        )

        unit_task = MockTask(
            gid="unit_prod_001",
            name="Production Unit",
            parent=MockNameGid(gid="unit_holder_prod_001"),
            custom_fields=[
                make_custom_field("Vertical", "chiropractic", "enum"),
            ],
        )

        mock_client.tasks.get_async.side_effect = [unit_holder_task, business_task]

        resolver = CascadingFieldResolver(mock_client)

        with patch(
            "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
        ) as mock_detect:
            mock_detect.side_effect = [
                MagicMock(entity_type=EntityType.UNIT),
                MagicMock(entity_type=EntityType.UNIT_HOLDER),
                MagicMock(entity_type=EntityType.BUSINESS),
            ]

            office_phone = await resolver.resolve_async(unit_task, "Office Phone")  # type: ignore[arg-type]

        # Verify cascaded value
        assert office_phone == "+12604442080"

        # Now verify GidLookupIndex would correctly index this
        df = pl.DataFrame(
            {
                "gid": ["unit_prod_001"],
                "name": ["Production Unit"],
                "office_phone": [office_phone],  # Cascaded value
                "vertical": ["chiropractic"],
            }
        )

        index = GidLookupIndex.from_dataframe(df)

        from autom8_asana.models.contracts.phone_vertical import PhoneVerticalPair

        pair = PhoneVerticalPair(office_phone="+12604442080", vertical="chiropractic")
        resolved_gid = index.get_gid(pair)

        # This should NOT be None after the cascading fix
        assert resolved_gid == "unit_prod_001"

    @pytest.mark.asyncio
    async def test_scenario_second_chiropractic_unit(
        self, mock_client: MagicMock
    ) -> None:
        """Test: +19127481506 / chiropractic should return Unit GID."""
        business_task = MockTask(
            gid="business_prod_002",
            name="Second Production Business",
            custom_fields=[
                make_custom_field("Office Phone", "+19127481506", "text"),
            ],
        )

        unit_holder_task = MockTask(
            gid="unit_holder_prod_002",
            name="Units",
            parent=MockNameGid(gid="business_prod_002"),
        )

        unit_task = MockTask(
            gid="unit_prod_002",
            name="Second Production Unit",
            parent=MockNameGid(gid="unit_holder_prod_002"),
            custom_fields=[
                make_custom_field("Vertical", "chiropractic", "enum"),
            ],
        )

        mock_client.tasks.get_async.side_effect = [unit_holder_task, business_task]

        resolver = CascadingFieldResolver(mock_client)

        with patch(
            "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
        ) as mock_detect:
            mock_detect.side_effect = [
                MagicMock(entity_type=EntityType.UNIT),
                MagicMock(entity_type=EntityType.UNIT_HOLDER),
                MagicMock(entity_type=EntityType.BUSINESS),
            ]

            office_phone = await resolver.resolve_async(unit_task, "Office Phone")  # type: ignore[arg-type]

        assert office_phone == "+19127481506"

        # Verify index lookup
        df = pl.DataFrame(
            {
                "gid": ["unit_prod_002"],
                "name": ["Second Production Unit"],
                "office_phone": [office_phone],
                "vertical": ["chiropractic"],
            }
        )

        index = GidLookupIndex.from_dataframe(df)

        from autom8_asana.models.contracts.phone_vertical import PhoneVerticalPair

        pair = PhoneVerticalPair(office_phone="+19127481506", vertical="chiropractic")
        resolved_gid = index.get_gid(pair)

        assert resolved_gid == "unit_prod_002"
