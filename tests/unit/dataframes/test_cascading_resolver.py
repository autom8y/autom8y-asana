"""Unit tests for CascadingFieldResolver.

Per TDD-CASCADING-FIELD-RESOLUTION-001 Task 2: Tests for cascading field
resolution that traverses the parent task chain.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.dataframes.resolver.cascading import CascadingFieldResolver
from autom8_asana.dataframes.views.cf_utils import (
    class_to_entity_type,
    get_custom_field_value,
)
from autom8_asana.models.business.detection import EntityType

# ============================================================================
# Test Fixtures
# ============================================================================


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
    ) -> None:
        self.gid = gid
        self.name = name
        self.parent = parent
        self.custom_fields = custom_fields or []
        self.memberships = memberships or []


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
    """Create a mock AsanaClient with tasks.get_async method."""
    client = MagicMock()
    client.tasks = MagicMock()
    client.tasks.get_async = AsyncMock()
    return client


# ============================================================================
# Test Unknown Field Returns None
# ============================================================================


class TestResolveUnknownField:
    """Test that resolving unknown fields returns None."""

    @pytest.mark.asyncio
    async def test_resolve_returns_none_for_unknown_field(
        self, mock_client: MagicMock
    ) -> None:
        """Test resolve returns None for field not in registry."""
        resolver = CascadingFieldResolver(mock_client)

        task = MockTask(gid="123", name="Test Task")

        # "Unknown Field" is not in CASCADING_FIELD_REGISTRY
        result = await resolver.resolve_async(task, "Unknown Field")  # type: ignore[arg-type]

        assert result is None
        # Should not make any API calls
        mock_client.tasks.get_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolve_returns_none_for_empty_field_name(
        self, mock_client: MagicMock
    ) -> None:
        """Test resolve returns None for empty field name."""
        resolver = CascadingFieldResolver(mock_client)

        task = MockTask(gid="123")

        result = await resolver.resolve_async(task, "")  # type: ignore[arg-type]

        assert result is None


# ============================================================================
# Test Immediate Parent Resolution
# ============================================================================


class TestResolveImmediateParent:
    """Test resolving field values from immediate parent."""

    @pytest.mark.asyncio
    async def test_resolve_finds_value_on_immediate_parent(
        self, mock_client: MagicMock
    ) -> None:
        """Test resolve finds field value on immediate parent."""
        resolver = CascadingFieldResolver(mock_client)

        # Create a Business task with Office Phone
        business_task = MockTask(
            gid="business_123",
            name="Acme Corp",
            custom_fields=[
                make_custom_field("Office Phone", "555-1234", "text"),
            ],
            memberships=[{"project": {"gid": "1209100609254088"}}],  # Business project
        )

        # Create a Unit task (child of Business via UnitHolder)
        unit_task = MockTask(
            gid="unit_456",
            name="Unit 1",
            parent=MockNameGid(gid="business_123"),
            memberships=[{"project": {"gid": "1167650840133982"}}],  # Unit project
        )

        # Mock API to return business task
        mock_client.tasks.get_async.return_value = business_task

        # Patch detect_entity_type to return expected types
        with patch(
            "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
        ) as mock_detect:
            # First call for unit_task returns UNIT
            # Second call for business_task returns BUSINESS
            mock_detect.side_effect = [
                MagicMock(entity_type=EntityType.UNIT),
                MagicMock(entity_type=EntityType.BUSINESS),
            ]

            result = await resolver.resolve_async(unit_task, "Office Phone")  # type: ignore[arg-type]

        assert result == "555-1234"

    @pytest.mark.asyncio
    async def test_resolve_uses_local_value_when_override_allowed(
        self, mock_client: MagicMock
    ) -> None:
        """Test resolve returns local value when allow_override=True."""
        resolver = CascadingFieldResolver(mock_client)

        # Create task with local Vertical value
        # Vertical has allow_override=True in Unit.CascadingFields
        task = MockTask(
            gid="offer_123",
            name="Test Offer",
            custom_fields=[
                make_custom_field("Vertical", "Healthcare", "enum"),
            ],
        )

        # Patch get_cascading_field to return a field with allow_override=True
        with patch(
            "autom8_asana.dataframes.resolver.cascading.get_cascading_field"
        ) as mock_get_field:
            mock_field_def = MagicMock(source_field=None)
            mock_field_def.name = "Vertical"
            mock_field_def.allow_override = True
            mock_field_def.target_types = {"Offer"}

            mock_owner = MagicMock()
            mock_owner.__name__ = "Unit"

            mock_get_field.return_value = (mock_owner, mock_field_def)

            result = await resolver.resolve_async(task, "Vertical")  # type: ignore[arg-type]

        assert result == "Healthcare"
        # Should not fetch parent since local value exists and override is allowed
        mock_client.tasks.get_async.assert_not_called()


# ============================================================================
# Test Grandparent Resolution
# ============================================================================


class TestResolveGrandparent:
    """Test resolving field values from grandparent (2 levels up)."""

    @pytest.mark.asyncio
    async def test_resolve_finds_value_on_grandparent(
        self, mock_client: MagicMock
    ) -> None:
        """Test resolve finds field value on grandparent (2 levels up)."""
        resolver = CascadingFieldResolver(mock_client)

        # Create hierarchy: Business -> UnitHolder -> Unit
        business_task = MockTask(
            gid="business_123",
            name="Acme Corp",
            custom_fields=[
                make_custom_field("Office Phone", "555-9876", "text"),
            ],
        )

        unit_holder_task = MockTask(
            gid="unit_holder_456",
            name="Units",
            parent=MockNameGid(gid="business_123"),
        )

        unit_task = MockTask(
            gid="unit_789",
            name="Unit 1",
            parent=MockNameGid(gid="unit_holder_456"),
        )

        # Mock API calls - return unit_holder first, then business
        mock_client.tasks.get_async.side_effect = [unit_holder_task, business_task]

        # Patch detection
        with patch(
            "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
        ) as mock_detect:
            mock_detect.side_effect = [
                MagicMock(entity_type=EntityType.UNIT),
                MagicMock(entity_type=EntityType.UNIT_HOLDER),
                MagicMock(entity_type=EntityType.BUSINESS),
            ]

            result = await resolver.resolve_async(unit_task, "Office Phone")  # type: ignore[arg-type]

        assert result == "555-9876"
        # Should have made 2 API calls (unit_holder and business)
        assert mock_client.tasks.get_async.call_count == 2


# ============================================================================
# Test Max Depth Limit
# ============================================================================


class TestMaxDepthLimit:
    """Test that max_depth limit is respected."""

    @pytest.mark.asyncio
    async def test_resolve_respects_max_depth_limit(
        self, mock_client: MagicMock
    ) -> None:
        """Test resolve returns None when max_depth is exceeded."""
        resolver = CascadingFieldResolver(mock_client)

        # Create a long chain of tasks (task_5 is the root - not fetched)
        task4 = MockTask(gid="task_4", name="Task 4", parent=MockNameGid(gid="task_5"))
        task3 = MockTask(gid="task_3", name="Task 3", parent=MockNameGid(gid="task_4"))
        task2 = MockTask(gid="task_2", name="Task 2", parent=MockNameGid(gid="task_3"))
        task1 = MockTask(gid="task_1", name="Task 1", parent=MockNameGid(gid="task_2"))

        # Mock API to return tasks in chain
        mock_client.tasks.get_async.side_effect = [task2, task3, task4]

        # Patch detection to return UNIT for all (never reaching owner)
        with patch(
            "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
        ) as mock_detect:
            mock_detect.return_value = MagicMock(entity_type=EntityType.UNIT)

            result = await resolver.resolve_async(
                task1,
                "Office Phone",
                max_depth=3,  # type: ignore[arg-type]
            )

        # Should return None because max_depth exceeded
        assert result is None


# ============================================================================
# Test Allow Override Behavior
# ============================================================================


class TestAllowOverrideBehavior:
    """Test allow_override=True and allow_override=False behaviors."""

    @pytest.mark.asyncio
    async def test_resolve_respects_allow_override_true(
        self, mock_client: MagicMock
    ) -> None:
        """Test resolve keeps local value when allow_override=True."""
        resolver = CascadingFieldResolver(mock_client)

        task = MockTask(
            gid="offer_123",
            name="Test Offer",
            custom_fields=[
                make_custom_field("Platforms", ["Google", "Bing"], "multi_enum"),
            ],
        )

        # Mock field definition with allow_override=True
        with patch(
            "autom8_asana.dataframes.resolver.cascading.get_cascading_field"
        ) as mock_get_field:
            mock_field_def = MagicMock(source_field=None)
            mock_field_def.name = "Platforms"
            mock_field_def.allow_override = True

            mock_owner = MagicMock()
            mock_owner.__name__ = "Unit"

            mock_get_field.return_value = (mock_owner, mock_field_def)

            result = await resolver.resolve_async(task, "Platforms")  # type: ignore[arg-type]

        assert result == ["Google", "Bing"]
        mock_client.tasks.get_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolve_respects_allow_override_false(
        self, mock_client: MagicMock
    ) -> None:
        """Test resolve uses parent value when allow_override=False."""
        resolver = CascadingFieldResolver(mock_client)

        # Task with local value
        task = MockTask(
            gid="unit_123",
            name="Test Unit",
            parent=MockNameGid(gid="business_456"),
            custom_fields=[
                make_custom_field("Office Phone", "local-value", "text"),
            ],
        )

        # Parent with different value
        parent_task = MockTask(
            gid="business_456",
            name="Parent Business",
            custom_fields=[
                make_custom_field("Office Phone", "parent-value", "text"),
            ],
        )

        mock_client.tasks.get_async.return_value = parent_task

        # Mock field definition with allow_override=False (default)
        # Office Phone has allow_override=False in Business.CascadingFields
        with (
            patch(
                "autom8_asana.dataframes.resolver.cascading.get_cascading_field"
            ) as mock_get_field,
            patch(
                "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
            ) as mock_detect,
        ):
            mock_field_def = MagicMock(source_field=None)
            mock_field_def.name = "Office Phone"
            mock_field_def.allow_override = False

            mock_owner = MagicMock()
            mock_owner.__name__ = "Business"

            mock_get_field.return_value = (mock_owner, mock_field_def)
            mock_detect.side_effect = [
                MagicMock(entity_type=EntityType.UNIT),
                MagicMock(entity_type=EntityType.BUSINESS),
            ]

            result = await resolver.resolve_async(task, "Office Phone")  # type: ignore[arg-type]

        # Should traverse to parent because allow_override=False
        assert result == "parent-value"


# ============================================================================
# Test Parent Cache
# ============================================================================


class TestParentCache:
    """Test parent task caching behavior."""

    @pytest.mark.asyncio
    async def test_parent_cache_is_populated_on_traversal(
        self, mock_client: MagicMock
    ) -> None:
        """Test parent cache is populated when fetching parents."""
        resolver = CascadingFieldResolver(mock_client)

        business_task = MockTask(
            gid="business_123",
            name="Acme Corp",
            custom_fields=[
                make_custom_field("Office Phone", "555-1234", "text"),
            ],
        )

        unit_task = MockTask(
            gid="unit_456",
            name="Unit 1",
            parent=MockNameGid(gid="business_123"),
        )

        mock_client.tasks.get_async.return_value = business_task

        with patch(
            "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
        ) as mock_detect:
            mock_detect.side_effect = [
                MagicMock(entity_type=EntityType.UNIT),
                MagicMock(entity_type=EntityType.BUSINESS),
            ]

            await resolver.resolve_async(unit_task, "Office Phone")  # type: ignore[arg-type]

        # Cache should contain the fetched parent
        assert resolver.get_cache_size() == 1
        assert "business_123" in resolver._parent_cache

    @pytest.mark.asyncio
    async def test_parent_cache_prevents_duplicate_fetches(
        self, mock_client: MagicMock
    ) -> None:
        """Test parent cache prevents duplicate API calls."""
        resolver = CascadingFieldResolver(mock_client)

        business_task = MockTask(
            gid="business_123",
            name="Acme Corp",
            custom_fields=[
                make_custom_field("Office Phone", "555-1234", "text"),
            ],
        )

        unit_task_1 = MockTask(
            gid="unit_1",
            name="Unit 1",
            parent=MockNameGid(gid="business_123"),
        )

        unit_task_2 = MockTask(
            gid="unit_2",
            name="Unit 2",
            parent=MockNameGid(gid="business_123"),
        )

        mock_client.tasks.get_async.return_value = business_task

        with patch(
            "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
        ) as mock_detect:
            mock_detect.side_effect = [
                MagicMock(entity_type=EntityType.UNIT),
                MagicMock(entity_type=EntityType.BUSINESS),
                MagicMock(entity_type=EntityType.UNIT),
                MagicMock(entity_type=EntityType.BUSINESS),
            ]

            # First resolution
            await resolver.resolve_async(unit_task_1, "Office Phone")  # type: ignore[arg-type]
            # Second resolution (should use cache)
            await resolver.resolve_async(unit_task_2, "Office Phone")  # type: ignore[arg-type]

        # Should only call API once (business cached after first call)
        assert mock_client.tasks.get_async.call_count == 1

    @pytest.mark.xfail(reason="clear_cache method removed - test needs update")
    def test_clear_cache_empties_the_cache(self, mock_client: MagicMock) -> None:
        """Test clear_cache() empties the parent cache."""
        resolver = CascadingFieldResolver(mock_client)

        # Manually populate cache
        resolver._parent_cache["task_1"] = MockTask(gid="task_1")  # type: ignore[assignment]
        resolver._parent_cache["task_2"] = MockTask(gid="task_2")  # type: ignore[assignment]

        assert resolver.get_cache_size() == 2

        resolver.clear_cache()

        assert resolver.get_cache_size() == 0
        assert len(resolver._parent_cache) == 0


# ============================================================================
# Test Broken Parent Chain
# ============================================================================


class TestBrokenParentChain:
    """Test handling of broken parent chains."""

    @pytest.mark.asyncio
    async def test_broken_parent_chain_returns_none(
        self, mock_client: MagicMock
    ) -> None:
        """Test resolve returns None when parent chain is broken."""
        resolver = CascadingFieldResolver(mock_client)

        # Task with no parent
        task = MockTask(
            gid="orphan_123",
            name="Orphan Task",
            parent=None,  # No parent
        )

        # Mock field definition
        with patch(
            "autom8_asana.dataframes.resolver.cascading.get_cascading_field"
        ) as mock_get_field:
            mock_field_def = MagicMock(source_field=None)
            mock_field_def.name = "Office Phone"
            mock_field_def.allow_override = False

            mock_owner = MagicMock()
            mock_owner.__name__ = "Business"

            mock_get_field.return_value = (mock_owner, mock_field_def)

            with patch(
                "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
            ) as mock_detect:
                mock_detect.return_value = MagicMock(entity_type=EntityType.UNIT)

                result = await resolver.resolve_async(task, "Office Phone")  # type: ignore[arg-type]

        assert result is None

    @pytest.mark.asyncio
    async def test_parent_fetch_failure_returns_none(
        self, mock_client: MagicMock
    ) -> None:
        """Test resolve returns None when parent fetch fails."""
        resolver = CascadingFieldResolver(mock_client)

        task = MockTask(
            gid="unit_123",
            name="Unit 1",
            parent=MockNameGid(gid="missing_parent"),
        )

        # Mock API to raise exception
        mock_client.tasks.get_async.side_effect = ConnectionError("Task not found")

        with (
            patch(
                "autom8_asana.dataframes.resolver.cascading.get_cascading_field"
            ) as mock_get_field,
            patch(
                "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
            ) as mock_detect,
        ):
            mock_field_def = MagicMock(source_field=None)
            mock_field_def.name = "Office Phone"
            mock_field_def.allow_override = False

            mock_owner = MagicMock()
            mock_owner.__name__ = "Business"

            mock_get_field.return_value = (mock_owner, mock_field_def)
            mock_detect.return_value = MagicMock(entity_type=EntityType.UNIT)

            result = await resolver.resolve_async(task, "Office Phone")  # type: ignore[arg-type]

        assert result is None


# ============================================================================
# Test Circular Reference Detection
# ============================================================================


class TestCircularReferenceDetection:
    """Test detection of circular parent references."""

    @pytest.mark.asyncio
    async def test_circular_reference_detected(self, mock_client: MagicMock) -> None:
        """Test resolve detects and handles circular parent references."""
        resolver = CascadingFieldResolver(mock_client)

        # Create circular chain: task_1 -> task_2 -> task_1
        task_1 = MockTask(
            gid="task_1",
            name="Task 1",
            parent=MockNameGid(gid="task_2"),
        )

        task_2 = MockTask(
            gid="task_2",
            name="Task 2",
            parent=MockNameGid(gid="task_1"),
        )

        # Mock API to return tasks in circular pattern
        mock_client.tasks.get_async.side_effect = [task_2, task_1]

        with (
            patch(
                "autom8_asana.dataframes.resolver.cascading.get_cascading_field"
            ) as mock_get_field,
            patch(
                "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
            ) as mock_detect,
        ):
            mock_field_def = MagicMock(source_field=None)
            mock_field_def.name = "Office Phone"
            mock_field_def.allow_override = False

            mock_owner = MagicMock()
            mock_owner.__name__ = "Business"

            mock_get_field.return_value = (mock_owner, mock_field_def)
            # Never return Business type, so traversal continues
            mock_detect.return_value = MagicMock(entity_type=EntityType.UNIT)

            result = await resolver.resolve_async(task_1, "Office Phone")  # type: ignore[arg-type]

        # Should return None due to circular reference detection
        assert result is None


# ============================================================================
# Test Entity Type Mapping
# ============================================================================


class TestEntityTypeMapping:
    """Test mapping of business model classes to EntityType.

    Per TDD-WS3: Tests now target the shared ``class_to_entity_type``
    function in cf_utils instead of the removed private method.
    """

    def test_class_to_entity_type_business(self) -> None:
        """Test Business class maps to EntityType.BUSINESS."""
        mock_class = MagicMock()
        mock_class.__name__ = "Business"

        result = class_to_entity_type(mock_class)

        assert result == EntityType.BUSINESS

    def test_class_to_entity_type_unit(self) -> None:
        """Test Unit class maps to EntityType.UNIT."""
        mock_class = MagicMock()
        mock_class.__name__ = "Unit"

        result = class_to_entity_type(mock_class)

        assert result == EntityType.UNIT

    def test_class_to_entity_type_unknown(self) -> None:
        """Test unknown class maps to EntityType.UNKNOWN."""
        mock_class = MagicMock()
        mock_class.__name__ = "UnknownClass"

        result = class_to_entity_type(mock_class)

        assert result == EntityType.UNKNOWN


# ============================================================================
# Test Custom Field Value Extraction
# ============================================================================


class TestCustomFieldValueExtraction:
    """Test extraction of values from custom field data.

    Per TDD-WS3: Tests now target the shared ``get_custom_field_value``
    function in cf_utils instead of the removed private method.
    """

    def test_extract_text_value(self) -> None:
        """Test extraction of text field value."""
        task = MockTask(
            gid="123",
            custom_fields=[make_custom_field("Office Phone", "555-1234", "text")],
        )

        result = get_custom_field_value(task, "Office Phone")

        assert result == "555-1234"

    def test_extract_number_value(self) -> None:
        """Test extraction of number field value."""
        task = MockTask(
            gid="123",
            custom_fields=[make_custom_field("MRR", 5000.0, "number")],
        )

        result = get_custom_field_value(task, "MRR")

        assert result == 5000.0

    def test_extract_enum_value(self) -> None:
        """Test extraction of enum field value."""
        task = MockTask(
            gid="123",
            custom_fields=[make_custom_field("Vertical", "Healthcare", "enum")],
        )

        result = get_custom_field_value(task, "Vertical")

        assert result == "Healthcare"

    def test_extract_multi_enum_value(self) -> None:
        """Test extraction of multi-enum field value."""
        task = MockTask(
            gid="123",
            custom_fields=[
                make_custom_field("Platforms", ["Google", "Facebook"], "multi_enum")
            ],
        )

        result = get_custom_field_value(task, "Platforms")

        assert result == ["Google", "Facebook"]

    def test_extract_missing_field_returns_none(self) -> None:
        """Test extraction of missing field returns None."""
        task = MockTask(gid="123", custom_fields=[])

        result = get_custom_field_value(task, "NonExistent")

        assert result is None

    def test_extract_case_insensitive(self) -> None:
        """Test field name lookup is case-insensitive."""
        task = MockTask(
            gid="123",
            custom_fields=[make_custom_field("Office Phone", "555-1234", "text")],
        )

        # Different case should still match
        result = get_custom_field_value(task, "office phone")

        assert result == "555-1234"


# ============================================================================
# Integration Test with Real Registry
# ============================================================================


class TestGetFieldValueSourceField:
    """Test get_field_value with source_field wiring.

    Per TDD-WS3: Tests that get_field_value checks source_field first
    before falling through to get_custom_field_value.
    """

    def test_source_field_reads_task_attribute(self) -> None:
        """Test source_field="name" reads from task.name attribute."""
        from autom8_asana.dataframes.views.cf_utils import get_field_value
        from autom8_asana.models.business.fields import CascadingFieldDef

        field_def = CascadingFieldDef(
            name="Business Name",
            source_field="name",
        )

        task = MockTask(gid="biz-001", name="Acme Dental Corp")
        result = get_field_value(task, field_def)

        assert result == "Acme Dental Corp"

    def test_source_field_reads_dict_key(self) -> None:
        """Test source_field="name" reads from dict["name"]."""
        from autom8_asana.dataframes.views.cf_utils import get_field_value
        from autom8_asana.models.business.fields import CascadingFieldDef

        field_def = CascadingFieldDef(
            name="Business Name",
            source_field="name",
        )

        task_dict = {"gid": "biz-001", "name": "Acme Dental Corp", "parent": None}
        result = get_field_value(task_dict, field_def)

        assert result == "Acme Dental Corp"

    def test_no_source_field_falls_through_to_custom_field(self) -> None:
        """Test that source_field=None falls through to get_custom_field_value."""
        from autom8_asana.dataframes.views.cf_utils import get_field_value
        from autom8_asana.models.business.fields import CascadingFieldDef

        field_def = CascadingFieldDef(
            name="Office Phone",
            source_field=None,
        )

        task = MockTask(
            gid="biz-001",
            custom_fields=[make_custom_field("Office Phone", "555-1234", "text")],
        )
        result = get_field_value(task, field_def)

        assert result == "555-1234"

    def test_source_field_returns_none_for_missing_attribute(self) -> None:
        """Test source_field returns None when attribute doesn't exist."""
        from autom8_asana.dataframes.views.cf_utils import get_field_value
        from autom8_asana.models.business.fields import CascadingFieldDef

        field_def = CascadingFieldDef(
            name="Business Name",
            source_field="nonexistent_attr",
        )

        task = MockTask(gid="biz-001", name="Acme")
        result = get_field_value(task, field_def)

        assert result is None

    def test_source_field_returns_none_for_missing_dict_key(self) -> None:
        """Test source_field returns None when dict key doesn't exist."""
        from autom8_asana.dataframes.views.cf_utils import get_field_value
        from autom8_asana.models.business.fields import CascadingFieldDef

        field_def = CascadingFieldDef(
            name="Business Name",
            source_field="name",
        )

        task_dict: dict[str, Any] = {"gid": "biz-001"}  # No "name" key
        result = get_field_value(task_dict, field_def)

        assert result is None

    @pytest.mark.asyncio
    async def test_business_name_resolved_via_source_field_in_resolver(
        self, mock_client: MagicMock
    ) -> None:
        """Test that Business Name resolution uses source_field="name".

        Per TDD-WS3: When CascadingFieldResolver resolves "Business Name",
        get_field_value checks source_field="name" and returns the Business
        task's name attribute instead of searching custom_fields.
        """
        resolver = CascadingFieldResolver(mock_client)

        # Business task with name but NO "Business Name" custom field
        business_task = MockTask(
            gid="business_123",
            name="Acme Dental Corp",
            custom_fields=[],  # No custom fields at all
        )

        unit_task = MockTask(
            gid="unit_456",
            name="Unit 1",
            parent=MockNameGid(gid="business_123"),
        )

        mock_client.tasks.get_async.return_value = business_task

        with patch(
            "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
        ) as mock_detect:
            mock_detect.side_effect = [
                MagicMock(entity_type=EntityType.UNIT),
                MagicMock(entity_type=EntityType.BUSINESS),
            ]

            result = await resolver.resolve_async(unit_task, "Business Name")  # type: ignore[arg-type]

        # Should resolve from task.name via source_field, not custom_fields
        assert result == "Acme Dental Corp"


class TestIntegrationWithRegistry:
    """Integration tests using the real CASCADING_FIELD_REGISTRY."""

    @pytest.mark.asyncio
    async def test_office_phone_resolution(self, mock_client: MagicMock) -> None:
        """Test Office Phone field resolution from real registry."""
        resolver = CascadingFieldResolver(mock_client)

        # Create a realistic hierarchy: Business -> UnitHolder -> Unit
        business_task = MockTask(
            gid="business_123",
            name="Acme Healthcare",
            custom_fields=[
                make_custom_field("Office Phone", "(555) 123-4567", "text"),
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
            name="Main Office Unit",
            parent=MockNameGid(gid="unit_holder_456"),
        )

        # Mock API to return tasks
        mock_client.tasks.get_async.side_effect = [unit_holder_task, business_task]

        # Use real detection
        with patch(
            "autom8_asana.dataframes.resolver.cascading.detect_entity_type"
        ) as mock_detect:
            mock_detect.side_effect = [
                MagicMock(entity_type=EntityType.UNIT),
                MagicMock(entity_type=EntityType.UNIT_HOLDER),
                MagicMock(entity_type=EntityType.BUSINESS),
            ]

            result = await resolver.resolve_async(unit_task, "Office Phone")  # type: ignore[arg-type]

        assert result == "(555) 123-4567"
