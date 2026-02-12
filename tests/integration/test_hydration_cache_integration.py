"""Integration tests for hydration and cache field consistency.

Per PRD-CACHE-PERF-HYDRATION and TDD-CACHE-PERF-HYDRATION:
Tests that verify cache population provides fields required for hydration traversal.

These tests validate:
- Traversal uses STANDARD_TASK_OPT_FIELDS
- parent.gid available from cached tasks
- custom_fields available from cached Business tasks
- Standard fields are superset of detection fields

Test Strategy:
- Uses mocks (no live Asana credentials required in CI)
- Validates field presence and consistency
- Documents cache population path from TasksClient.get_async()
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.models.business.business import Business
from autom8_asana.models.business.detection import EntityType
from autom8_asana.models.business.fields import (
    DETECTION_OPT_FIELDS,
    STANDARD_TASK_OPT_FIELDS,
)
from autom8_asana.models.business.hydration import (
    _DETECTION_OPT_FIELDS as HYDRATION_DETECTION_OPT_FIELDS,
)
from autom8_asana.models.business.hydration import (
    _traverse_upward_async,
    hydrate_from_gid_async,
)
from autom8_asana.models.task import Task

# --- Fixtures ---


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock AsanaClient for testing."""
    client = MagicMock()
    client.default_workspace_gid = "workspace_test_123"
    return client


def make_mock_task(
    gid: str,
    name: str,
    parent_gid: str | None = None,
    memberships: list[dict[str, Any]] | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
) -> Task:
    """Create a mock Task with specified attributes.

    Note: When parent_gid is provided, the returned Task will have
    parent.gid available, which is required for upward traversal.
    """
    return Task(
        gid=gid,
        name=name,
        parent={"gid": parent_gid} if parent_gid else None,
        memberships=memberships or [],
        custom_fields=custom_fields or [],
    )


def make_subtask(gid: str, name: str) -> MagicMock:
    """Create a mock subtask."""
    subtask = MagicMock()
    subtask.gid = gid
    subtask.name = name
    return subtask


# =============================================================================
# Test: Traversal Uses STANDARD_TASK_OPT_FIELDS
# =============================================================================


class TestTraversalUsesStandardFields:
    """FR-BUSINESS-001: Verify traversal uses standard fields."""

    def test_hydration_detection_fields_equal_canonical(self) -> None:
        """hydration._DETECTION_OPT_FIELDS equals DETECTION_OPT_FIELDS.

        Per FR-DETECT-001: Hydration module's detection fields should be
        derived from the canonical source in fields.py.
        """
        assert set(HYDRATION_DETECTION_OPT_FIELDS) == set(DETECTION_OPT_FIELDS)

    def test_standard_fields_include_parent_gid(self) -> None:
        """FR-FIELDS-003: STANDARD_TASK_OPT_FIELDS includes parent.gid.

        This is critical for upward traversal - without parent.gid,
        _traverse_upward_async cannot navigate to parent tasks.
        """
        assert "parent.gid" in STANDARD_TASK_OPT_FIELDS

    def test_standard_fields_include_detection_fields(self) -> None:
        """FR-DETECT-001: Detection fields are subset of standard fields.

        Ensures that any task fetched with standard fields will have
        all fields required for entity type detection.
        """
        detection_set = set(DETECTION_OPT_FIELDS)
        standard_set = set(STANDARD_TASK_OPT_FIELDS)
        assert detection_set.issubset(standard_set), (
            f"Detection fields not subset of standard. "
            f"Missing: {detection_set - standard_set}"
        )


# =============================================================================
# Test: parent.gid Available from Cached Tasks
# =============================================================================


@pytest.mark.asyncio
class TestParentGidFromCachedTasks:
    """FR-BUSINESS-001: Verify parent.gid available for traversal."""

    async def test_task_with_parent_gid_enables_traversal(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Cached task with parent.gid enables upward traversal.

        Per FR-CACHE-001: TasksClient._DETECTION_FIELDS includes parent.gid,
        so tasks fetched with include_detection_fields=True will have
        parent.gid available for _traverse_upward_async.
        """
        from autom8_asana.models.business.registry import get_registry

        # Register Business project for Tier 1 detection
        registry = get_registry()
        registry.register("business_project", EntityType.BUSINESS)

        # Setup: Task with parent.gid populated (simulating cached task)
        # This is the key test - parent.gid must be present
        child_task = make_mock_task(
            "child_001",
            "Child Task",
            parent_gid="parent_001",  # parent.gid is available
        )
        parent_holder = make_mock_task(
            "parent_001",
            "Contacts",
            parent_gid="business_001",
        )
        business_task = make_mock_task(
            "business_001",
            "Acme Corporation",
            memberships=[{"project": {"gid": "business_project"}}],
            custom_fields=[{"gid": "cf_001", "name": "Office Phone"}],
        )

        # Verify child_task has parent.gid available
        assert child_task.parent is not None, "Task must have parent"
        assert child_task.parent.gid == "parent_001", "parent.gid must be available"

        # Mock API responses
        async def mock_get(gid: str, **kwargs: Any) -> Task:
            if gid == "parent_001":
                return parent_holder
            elif gid == "business_001":
                return business_task
            raise ValueError(f"Unexpected GID: {gid}")

        mock_client.tasks.get_async = mock_get

        # Execute traversal - should succeed because parent.gid is available
        business, path = await _traverse_upward_async(child_task, mock_client)

        assert isinstance(business, Business)
        assert business.gid == "business_001"
        assert len(path) >= 1

    async def test_traversal_fails_without_parent_gid(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Traversal fails when parent.gid is missing.

        This test documents the failure mode that occurs when
        parent.gid is not included in the opt_fields - the exact
        bug that PRD-CACHE-PERF-HYDRATION addresses.
        """
        from autom8_asana.exceptions import HydrationError

        # Task without parent.gid (simulating cache miss scenario)
        orphan_task = make_mock_task(
            "orphan_001",
            "Orphan Task",
            parent_gid=None,  # No parent.gid
        )

        # Mock empty subtasks (not a Business structure)
        subtasks_mock = MagicMock()
        subtasks_mock.collect = AsyncMock(return_value=[])
        mock_client.tasks.subtasks_async = MagicMock(return_value=subtasks_mock)

        # Traversal should fail - no parent to navigate to
        with pytest.raises(HydrationError) as exc_info:
            await _traverse_upward_async(orphan_task, mock_client)

        assert (
            "root" in str(exc_info.value).lower()
            or "parent" in str(exc_info.value).lower()
        )


# =============================================================================
# Test: custom_fields Available from Cached Business Tasks
# =============================================================================


@pytest.mark.asyncio
class TestCustomFieldsFromCachedBusiness:
    """FR-BUSINESS-003: Verify custom_fields available on Business."""

    async def test_business_has_custom_fields_after_hydration(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Business entity has custom_fields available after hydration.

        Per FR-FIELDS-004: STANDARD_TASK_OPT_FIELDS includes
        custom_fields.people_value and other custom_fields subfields,
        enabling Owner cascading and other field operations.
        """
        # Business task with custom_fields populated
        business_task = make_mock_task(
            "bus_001",
            "Acme Corporation",
            custom_fields=[
                {"gid": "cf_001", "name": "Office Phone", "display_value": "555-1234"},
                {
                    "gid": "cf_002",
                    "name": "Owner",
                    "people_value": [{"gid": "user_001", "name": "John Doe"}],
                },
            ],
        )

        mock_client.tasks.get_async = AsyncMock(return_value=business_task)

        # Mock structure inspection for Business detection
        subtasks = [
            make_subtask("holder_001", "Contacts"),
            make_subtask("holder_002", "Units"),
        ]
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(
            return_value=subtasks
        )

        with patch.object(Business, "_fetch_holders_async", new_callable=AsyncMock):
            result = await hydrate_from_gid_async(mock_client, "bus_001")

        # Verify custom_fields are accessible
        assert result.business is not None
        custom_fields = result.business.custom_fields
        assert custom_fields is not None
        assert len(custom_fields) == 2

        # Verify specific field values via custom_fields_editor() accessor
        cf_accessor = result.business.custom_fields_editor()
        # Use the accessor's get() method to retrieve values
        office_phone = cf_accessor.get("Office Phone")
        assert office_phone == "555-1234"


class TestStandardFieldsIncludePeopleValue:
    """Separate class for non-async tests."""

    def test_standard_fields_include_people_value(self) -> None:
        """FR-FIELDS-004: STANDARD_TASK_OPT_FIELDS includes people_value.

        This is required for Owner cascading from Business to descendants.
        """
        assert "custom_fields.people_value" in STANDARD_TASK_OPT_FIELDS


# =============================================================================
# Test: Standard Fields Superset of Detection Fields
# =============================================================================


class TestStandardSupersetOfDetection:
    """FR-DETECT-001: Standard fields are superset of detection fields."""

    def test_all_detection_fields_in_standard(self) -> None:
        """Every detection field exists in standard field set.

        This ensures that any task fetched with standard fields can be
        used for entity type detection without additional API calls.
        """
        for field in DETECTION_OPT_FIELDS:
            assert field in STANDARD_TASK_OPT_FIELDS, (
                f"Detection field '{field}' missing from STANDARD_TASK_OPT_FIELDS"
            )

    def test_standard_has_more_fields_than_detection(self) -> None:
        """Standard set is strictly larger than detection set.

        Detection fields are minimal; standard includes custom_fields
        subfields for cascading operations.
        """
        assert len(STANDARD_TASK_OPT_FIELDS) > len(DETECTION_OPT_FIELDS)

    def test_detection_fields_count(self) -> None:
        """Detection has exactly 4 minimal fields.

        Per FR-DETECT-003: Detection uses minimal fields for performance.
        """
        assert len(DETECTION_OPT_FIELDS) == 4

    def test_standard_fields_count(self) -> None:
        """Standard has exactly 15 fields.

        Per FR-FIELDS-001: Standard set has 15 fields.
        """
        assert len(STANDARD_TASK_OPT_FIELDS) == 15


# =============================================================================
# Test: Cache Population Path Verification
# =============================================================================


class TestCachePopulationPath:
    """Verify cache population provides required fields.

    Per TDD-CACHE-PERF-HYDRATION: These tests document the cache population
    path from TasksClient.get_async() to _traverse_upward_async().
    """

    def test_tasks_client_detection_fields_equals_standard(self) -> None:
        """TasksClient._DETECTION_FIELDS equals STANDARD_TASK_OPT_FIELDS.

        Per FR-CACHE-003: TasksClient must use standard fields so that
        cached tasks have all fields required for downstream hydration.

        Cache Population Path:
        1. TasksClient.subtasks_async(include_detection_fields=True)
        2. Uses _DETECTION_FIELDS which equals STANDARD_TASK_OPT_FIELDS
        3. Tasks cached with all 15 fields including parent.gid
        4. Later hydrate_from_gid_async() can access parent.gid from cache
        """
        from autom8_asana.clients.tasks import TasksClient

        assert set(TasksClient._DETECTION_FIELDS) == set(STANDARD_TASK_OPT_FIELDS)

    def test_tasks_client_has_parent_gid_for_traversal(self) -> None:
        """TasksClient._DETECTION_FIELDS includes parent.gid.

        Per FR-CACHE-001: This is the critical field for upward traversal.
        Without it, _traverse_upward_async() would fail with NoneType error.
        """
        from autom8_asana.clients.tasks import TasksClient

        assert "parent.gid" in TasksClient._DETECTION_FIELDS

    def test_tasks_client_has_people_value_for_cascading(self) -> None:
        """TasksClient._DETECTION_FIELDS includes people_value.

        Per FR-CACHE-002: Required for Owner field cascading from Business
        to descendant entities (Unit, Offer, Process).
        """
        from autom8_asana.clients.tasks import TasksClient

        assert "custom_fields.people_value" in TasksClient._DETECTION_FIELDS


# =============================================================================
# Test: Hydration with Cached Tasks
# =============================================================================


@pytest.mark.asyncio
class TestHydrationWithCachedTasks:
    """FR-BUSINESS-002: Hydration works with cached tasks."""

    async def test_hydration_succeeds_with_standard_fields(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Hydration completes when tasks have standard fields.

        This test simulates the happy path where TasksClient.get_async()
        returns tasks that were previously cached with standard fields,
        including parent.gid for traversal.
        """
        from autom8_asana.models.business.registry import get_registry

        # Register projects for Tier 1 detection
        registry = get_registry()
        registry.register("business_project", EntityType.BUSINESS)
        registry.register("contact_project", EntityType.CONTACT)

        # Simulate cached tasks with all standard fields
        contact_task = make_mock_task(
            "contact_001",
            "John Smith",
            parent_gid="holder_001",
            memberships=[{"project": {"gid": "contact_project"}}],
            custom_fields=[
                {
                    "gid": "cf_001",
                    "name": "Contact Email",
                    "text_value": "john@example.com",
                }
            ],
        )
        holder_task = make_mock_task(
            "holder_001",
            "Contacts",
            parent_gid="bus_001",
        )
        business_task = make_mock_task(
            "bus_001",
            "Acme Corporation",
            memberships=[{"project": {"gid": "business_project"}}],
            custom_fields=[
                {"gid": "cf_002", "name": "Office Phone", "display_value": "555-1234"},
            ],
        )

        # Mock API responses (simulating cache returns)
        async def mock_get(gid: str, **kwargs: Any) -> Task:
            tasks = {
                "contact_001": contact_task,
                "holder_001": holder_task,
                "bus_001": business_task,
            }
            return tasks.get(gid, business_task)

        mock_client.tasks.get_async = mock_get

        # Mock subtasks for structure inspection
        subtasks_mock = MagicMock()
        subtasks_mock.collect = AsyncMock(return_value=[])
        mock_client.tasks.subtasks_async = MagicMock(return_value=subtasks_mock)

        with patch.object(Business, "_fetch_holders_async", new_callable=AsyncMock):
            result = await hydrate_from_gid_async(mock_client, "contact_001")

        # Verify successful hydration
        assert result.business is not None
        assert result.business.gid == "bus_001"
        assert result.entry_type == EntityType.CONTACT
        assert len(result.path) > 0

    async def test_hydration_traverses_full_hierarchy(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Hydration traverses from deep entity to Business root.

        This tests a deeper hierarchy: Offer -> OfferHolder -> Unit ->
        UnitHolder -> Business, verifying parent.gid works at each level.
        """
        from autom8_asana.models.business.registry import get_registry

        registry = get_registry()
        registry.register("business_project", EntityType.BUSINESS)

        # Deep hierarchy with parent.gid at each level
        offer_task = make_mock_task(
            "offer_001",
            "Special Offer",
            parent_gid="offer_holder_001",
        )
        offer_holder_task = make_mock_task(
            "offer_holder_001",
            "Offers",
            parent_gid="unit_001",
        )
        unit_task = make_mock_task(
            "unit_001",
            "Premium Package",
            parent_gid="unit_holder_001",
        )
        unit_holder_task = make_mock_task(
            "unit_holder_001",
            "Units",
            parent_gid="bus_001",
        )
        business_task = make_mock_task(
            "bus_001",
            "Acme Corporation",
            memberships=[{"project": {"gid": "business_project"}}],
        )

        async def mock_get(gid: str, **kwargs: Any) -> Task:
            tasks = {
                "offer_001": offer_task,
                "offer_holder_001": offer_holder_task,
                "unit_001": unit_task,
                "unit_holder_001": unit_holder_task,
                "bus_001": business_task,
            }
            return tasks.get(gid, business_task)

        mock_client.tasks.get_async = mock_get

        subtasks_mock = MagicMock()
        subtasks_mock.collect = AsyncMock(return_value=[])
        mock_client.tasks.subtasks_async = MagicMock(return_value=subtasks_mock)

        with patch.object(Business, "_fetch_holders_async", new_callable=AsyncMock):
            result = await hydrate_from_gid_async(mock_client, "offer_001")

        assert result.business is not None
        assert result.business.gid == "bus_001"
        # Path should include intermediate entities that were successfully typed.
        # Note: Some entities may not be typed (UNKNOWN returns None) but traversal
        # still succeeds because parent.gid is present at each level.
        # The key validation is that traversal completed from offer to business.
        assert len(result.path) >= 2  # At least OfferHolder and UnitHolder typed
