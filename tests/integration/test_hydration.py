"""Integration tests for Business hierarchy hydration.

Per TDD-TECH-DEBT-REMEDIATION Phase 3 / FR-TEST-002:
Tests hydration workflows with mocked API responses.

These tests validate:
- Downward hydration from Business root
- Upward traversal from leaf entities to Business
- HydrationResult tracking (succeeded, failed, api_calls)
- Partial failure handling with partial_ok mode
- Entity type conversion during traversal

Hard Constraint: Uses mocks (no live Asana credentials required in CI).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.errors import HydrationError
from autom8_asana.models.business.business import Business
from autom8_asana.models.business.contact import Contact, ContactHolder
from autom8_asana.models.business.detection import EntityType
from autom8_asana.models.business.hydration import (
    HydrationBranch,
    HydrationFailure,
    HydrationResult,
    _convert_to_typed_entity,
    _is_recoverable,
    _traverse_upward_async,
    hydrate_from_gid_async,
)
from autom8_asana.models.business.offer import Offer
from autom8_asana.models.business.process import Process
from autom8_asana.models.business.unit import Unit, UnitHolder
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
    """Create a mock Task with specified attributes."""
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


# --- Test: HydrationResult Dataclass ---


class TestHydrationResult:
    """Tests for HydrationResult dataclass behavior."""

    def test_is_complete_with_no_failures(self) -> None:
        """is_complete is True when no failures exist."""
        result = HydrationResult(
            business=MagicMock(spec=Business),
            succeeded=[
                HydrationBranch(
                    holder_type="contact_holder",
                    holder_gid="holder_001",
                    child_count=5,
                )
            ],
            failed=[],
        )

        assert result.is_complete is True

    def test_is_complete_with_failures(self) -> None:
        """is_complete is False when failures exist."""
        result = HydrationResult(
            business=MagicMock(spec=Business),
            succeeded=[],
            failed=[
                HydrationFailure(
                    holder_type="unit_holder",
                    holder_gid="holder_001",
                    phase="downward",
                    error=Exception("Test error"),
                    recoverable=False,
                )
            ],
        )

        assert result.is_complete is False

    def test_default_values(self) -> None:
        """HydrationResult has sensible defaults."""
        business = MagicMock(spec=Business)
        result = HydrationResult(business=business)

        assert result.entry_entity is None
        assert result.entry_type is None
        assert result.path == []
        assert result.api_calls == 0
        assert result.succeeded == []
        assert result.failed == []
        assert result.warnings == []

    def test_hydration_branch(self) -> None:
        """HydrationBranch stores branch success details."""
        branch = HydrationBranch(
            holder_type="contact_holder",
            holder_gid="holder_001",
            child_count=10,
        )

        assert branch.holder_type == "contact_holder"
        assert branch.holder_gid == "holder_001"
        assert branch.child_count == 10

    def test_hydration_failure(self) -> None:
        """HydrationFailure stores failure details."""
        error = ValueError("Test error")
        failure = HydrationFailure(
            holder_type="unit_holder",
            holder_gid="holder_001",
            phase="downward",
            error=error,
            recoverable=True,
        )

        assert failure.holder_type == "unit_holder"
        assert failure.holder_gid == "holder_001"
        assert failure.phase == "downward"
        assert failure.error is error
        assert failure.recoverable is True


# --- Test: Error Recoverability ---


class TestIsRecoverable:
    """Tests for _is_recoverable error classification."""

    def test_rate_limit_is_recoverable(self) -> None:
        """RateLimitError is recoverable."""
        from autom8_asana.errors import RateLimitError

        error = RateLimitError("Rate limited")
        assert _is_recoverable(error) is True

    def test_timeout_is_recoverable(self) -> None:
        """TimeoutError is recoverable."""
        from autom8_asana.errors import TimeoutError

        error = TimeoutError("Request timed out")
        assert _is_recoverable(error) is True

    def test_server_error_is_recoverable(self) -> None:
        """ServerError is recoverable."""
        from autom8_asana.errors import ServerError

        error = ServerError("Internal server error")
        assert _is_recoverable(error) is True

    def test_not_found_is_not_recoverable(self) -> None:
        """NotFoundError is not recoverable."""
        from autom8_asana.errors import NotFoundError

        error = NotFoundError("Resource not found")
        assert _is_recoverable(error) is False

    def test_forbidden_is_not_recoverable(self) -> None:
        """ForbiddenError is not recoverable."""
        from autom8_asana.errors import ForbiddenError

        error = ForbiddenError("Access denied")
        assert _is_recoverable(error) is False

    def test_generic_exception_is_not_recoverable(self) -> None:
        """Generic exceptions default to not recoverable."""
        error = ValueError("Generic error")
        assert _is_recoverable(error) is False


# --- Test: Entity Type Conversion ---


class TestConvertToTypedEntity:
    """Tests for _convert_to_typed_entity function."""

    def test_convert_to_business_returns_none(self) -> None:
        """Business type returns None (Business handled separately in traversal).

        Per implementation: BUSINESS is handled in _traverse_upward_async,
        not via _convert_to_typed_entity.
        """
        task = make_mock_task("bus_001", "Acme Corporation")

        entity = _convert_to_typed_entity(task, EntityType.BUSINESS)

        # Business is handled separately in traversal, returns None here
        assert entity is None

    def test_convert_to_contact(self) -> None:
        """Task is converted to Contact entity."""
        task = make_mock_task("contact_001", "John Smith")

        entity = _convert_to_typed_entity(task, EntityType.CONTACT)

        assert isinstance(entity, Contact)
        assert entity.gid == "contact_001"

    def test_convert_to_contact_holder(self) -> None:
        """Task is converted to ContactHolder entity."""
        task = make_mock_task("holder_001", "Contacts")

        entity = _convert_to_typed_entity(task, EntityType.CONTACT_HOLDER)

        assert isinstance(entity, ContactHolder)

    def test_convert_to_unit(self) -> None:
        """Task is converted to Unit entity."""
        task = make_mock_task("unit_001", "Premium Package")

        entity = _convert_to_typed_entity(task, EntityType.UNIT)

        assert isinstance(entity, Unit)

    def test_convert_to_unit_holder(self) -> None:
        """Task is converted to UnitHolder entity."""
        task = make_mock_task("holder_001", "Units")

        entity = _convert_to_typed_entity(task, EntityType.UNIT_HOLDER)

        assert isinstance(entity, UnitHolder)

    def test_convert_to_offer(self) -> None:
        """Task is converted to Offer entity."""
        task = make_mock_task("offer_001", "Special Offer")

        entity = _convert_to_typed_entity(task, EntityType.OFFER)

        assert isinstance(entity, Offer)

    def test_convert_to_process(self) -> None:
        """Task is converted to Process entity."""
        task = make_mock_task("process_001", "Demo Call")

        entity = _convert_to_typed_entity(task, EntityType.PROCESS)

        assert isinstance(entity, Process)

    def test_unknown_type_returns_none(self) -> None:
        """Unknown entity type returns None (logs warning).

        Per implementation: UNKNOWN returns None with a warning,
        does not raise an exception.
        """
        task = make_mock_task("task_001", "Random Task")

        entity = _convert_to_typed_entity(task, EntityType.UNKNOWN)

        assert entity is None


# --- Test: Upward Traversal ---


class TestUpwardTraversal:
    """Tests for _traverse_upward_async function."""

    async def test_traversal_from_contact_to_business(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Traverses from Contact through hierarchy to Business."""
        from autom8_asana.models.business.registry import get_registry

        # Register Business project for Tier 1 detection
        registry = get_registry()
        registry.register("business_project", EntityType.BUSINESS)

        # Setup: Contact -> ContactHolder -> Business
        contact_task = make_mock_task("contact_001", "John Smith", parent_gid="holder_001")
        holder_task = make_mock_task("holder_001", "Contacts", parent_gid="bus_001")
        business_task = make_mock_task(
            "bus_001",
            "Acme Corporation",
            memberships=[{"project": {"gid": "business_project"}}],
        )

        # Mock API responses - each get_async call needs a fresh return
        async def mock_get(gid: str, **kwargs: Any) -> Task:
            if gid == "holder_001":
                return holder_task
            elif gid == "bus_001":
                return business_task
            raise ValueError(f"Unexpected GID: {gid}")

        mock_client.tasks.get_async = mock_get

        business, path = await _traverse_upward_async(contact_task, mock_client)

        assert isinstance(business, Business)
        assert business.gid == "bus_001"
        assert len(path) >= 1  # At least holder in path

    async def test_traversal_with_max_depth(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Traversal respects max depth limit."""
        # Create a deep hierarchy that exceeds max depth
        task = make_mock_task("deep_001", "Deep Task", parent_gid="parent_001")

        # Mock infinite parent chain - async function
        async def create_parent(gid: str, **kwargs: Any) -> Task:
            parent_num = int(gid.split("_")[1])
            return make_mock_task(
                gid, f"Parent {parent_num}", parent_gid=f"parent_{parent_num + 1:03d}"
            )

        mock_client.tasks.get_async = create_parent

        # Mock subtasks for structure inspection (empty - no Business structure)
        subtasks_mock = MagicMock()
        subtasks_mock.collect = AsyncMock(return_value=[])
        mock_client.tasks.subtasks_async = MagicMock(return_value=subtasks_mock)

        with pytest.raises(HydrationError) as exc_info:
            await _traverse_upward_async(task, mock_client)

        # Should fail with max depth exceeded error
        error_msg = str(exc_info.value).lower()
        assert "max traversal depth" in error_msg or "exceeded" in error_msg

    async def test_traversal_stops_at_business(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Traversal stops when Business is detected and does not continue past it."""
        # Setup: child -> Business (which itself has a parent that should NOT be visited)
        child_task = make_mock_task("child_001", "Some Child", parent_gid="bus_001")
        business_task = make_mock_task("bus_001", "Acme Corporation", parent_gid="grandparent_001")

        # Mock structure inspection for Business detection (Tier 4 fallback)
        subtasks = [
            make_subtask("holder_001", "Contacts"),
            make_subtask("holder_002", "Units"),
        ]
        subtasks_mock = MagicMock()
        subtasks_mock.collect = AsyncMock(return_value=subtasks)
        mock_client.tasks.subtasks_async = MagicMock(return_value=subtasks_mock)

        # Only bus_001 should be fetched; grandparent_001 should never be reached
        async def mock_get(gid: str, **kwargs: Any) -> Task:
            if gid == "bus_001":
                return business_task
            raise AssertionError(f"Unexpected fetch for GID: {gid}")

        mock_client.tasks.get_async = mock_get

        # Act
        business, path = await _traverse_upward_async(child_task, mock_client)

        # Assert: traversal found the Business and stopped
        assert isinstance(business, Business)
        assert business.gid == "bus_001"
        assert business.name == "Acme Corporation"
        # Path should be empty -- child_task is the start entity (not in path),
        # and Business is the destination (not in path either)
        assert len(path) == 0


# --- Test: Full Hydration Workflow ---


class TestHydrateFromGidAsync:
    """Tests for hydrate_from_gid_async entry point."""

    async def test_hydrate_from_business_gid(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Hydration from Business GID performs downward hydration."""
        business_task = make_mock_task(
            "bus_001",
            "Acme Corporation",
            custom_fields=[{"gid": "cf_001", "name": "Office Phone"}],
        )

        # Mock API responses
        mock_client.tasks.get_async = AsyncMock(return_value=business_task)

        # Mock structure inspection for Business detection
        subtasks = [
            make_subtask("holder_001", "Contacts"),
            make_subtask("holder_002", "Units"),
        ]
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(return_value=subtasks)

        # Mock holder hydration (simplified - empty holders)
        with patch.object(Business, "_fetch_holders_async", new_callable=AsyncMock):
            result = await hydrate_from_gid_async(mock_client, "bus_001")

        assert result.business is not None
        assert result.business.gid == "bus_001"
        assert result.entry_entity is None  # Started at Business
        assert result.entry_type == EntityType.BUSINESS
        assert result.api_calls > 0

    async def test_hydrate_from_non_business_gid(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Hydration from non-Business GID traverses upward first."""
        from autom8_asana.models.business.registry import get_registry

        # Register both Business and Contact projects for Tier 1 detection
        registry = get_registry()
        registry.register("business_project", EntityType.BUSINESS)
        registry.register("contact_project", EntityType.CONTACT)

        contact_task = make_mock_task(
            "contact_001",
            "John Smith",
            parent_gid="holder_001",
            memberships=[{"project": {"gid": "contact_project"}}],
        )
        holder_task = make_mock_task("holder_001", "Contacts", parent_gid="bus_001")
        business_task = make_mock_task(
            "bus_001",
            "Acme Corporation",
            memberships=[{"project": {"gid": "business_project"}}],
            custom_fields=[],
        )

        # Mock API responses for traversal
        async def mock_get(gid: str, **kwargs: Any) -> Task:
            task_map = {
                "contact_001": contact_task,
                "holder_001": holder_task,
                "bus_001": business_task,
            }
            if gid in task_map:
                return task_map[gid]
            raise ValueError(f"Unexpected GID: {gid}")

        mock_client.tasks.get_async = mock_get

        # Mock subtasks for structure inspection (in case Tier 4 is triggered)
        subtasks_mock = MagicMock()
        subtasks_mock.collect = AsyncMock(return_value=[])
        mock_client.tasks.subtasks_async = MagicMock(return_value=subtasks_mock)

        with patch.object(Business, "_fetch_holders_async", new_callable=AsyncMock):
            result = await hydrate_from_gid_async(mock_client, "contact_001")

        assert result.business is not None
        assert result.business.gid == "bus_001"
        assert result.entry_entity is not None
        assert result.entry_type == EntityType.CONTACT
        assert len(result.path) > 0  # Traversal path captured

    async def test_hydrate_without_full_hydration(
        self,
        mock_client: MagicMock,
    ) -> None:
        """hydrate_full=False skips downward hydration."""
        business_task = make_mock_task("bus_001", "Acme Corporation")

        mock_client.tasks.get_async = AsyncMock(return_value=business_task)

        subtasks = [make_subtask("holder_001", "Contacts")]
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(return_value=subtasks)

        result = await hydrate_from_gid_async(mock_client, "bus_001", hydrate_full=False)

        assert result.business is not None
        # Fewer API calls since no downward hydration
        # (just detection and business fetch)

    async def test_hydrate_with_partial_ok(
        self,
        mock_client: MagicMock,
    ) -> None:
        """partial_ok=True allows partial failures."""
        business_task = make_mock_task("bus_001", "Acme Corporation")

        mock_client.tasks.get_async = AsyncMock(return_value=business_task)

        subtasks = [make_subtask("holder_001", "Contacts")]
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(return_value=subtasks)

        # Mock holder hydration to fail
        with patch.object(
            Business,
            "_fetch_holders_async",
            new_callable=AsyncMock,
            side_effect=Exception("Holder fetch failed"),
        ):
            result = await hydrate_from_gid_async(mock_client, "bus_001", partial_ok=True)

        assert result.business is not None
        assert result.is_complete is False
        assert len(result.failed) > 0

    async def test_hydrate_without_partial_ok_raises(
        self,
        mock_client: MagicMock,
    ) -> None:
        """partial_ok=False (default) raises on failure."""
        business_task = make_mock_task("bus_001", "Acme Corporation")

        mock_client.tasks.get_async = AsyncMock(return_value=business_task)

        subtasks = [make_subtask("holder_001", "Contacts")]
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(return_value=subtasks)

        with patch.object(
            Business,
            "_fetch_holders_async",
            new_callable=AsyncMock,
            side_effect=Exception("Holder fetch failed"),
        ):
            with pytest.raises(HydrationError):
                await hydrate_from_gid_async(mock_client, "bus_001", partial_ok=False)

    async def test_hydrate_not_found_raises(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Non-existent GID raises HydrationError."""
        from autom8_asana.errors import NotFoundError

        mock_client.tasks.get_async = AsyncMock(side_effect=NotFoundError("Task not found"))

        with pytest.raises(HydrationError) as exc_info:
            await hydrate_from_gid_async(mock_client, "nonexistent_gid")

        assert "Failed to fetch" in str(exc_info.value)


# --- Test: Detection During Hydration ---


class TestDetectionDuringHydration:
    """Tests for entity type detection during hydration."""

    async def test_detection_uses_project_membership(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Detection uses project membership (Tier 1) when available."""
        from autom8_asana.models.business.registry import get_registry

        # Register Business project
        registry = get_registry()
        registry.register("business_project", EntityType.BUSINESS)

        business_task = make_mock_task(
            "bus_001",
            "Acme Corporation",
            memberships=[{"project": {"gid": "business_project"}}],
        )

        mock_client.tasks.get_async = AsyncMock(return_value=business_task)

        with patch.object(Business, "_fetch_holders_async", new_callable=AsyncMock):
            result = await hydrate_from_gid_async(mock_client, "bus_001")

        assert result.entry_type == EntityType.BUSINESS

    async def test_detection_uses_structure_inspection(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Detection uses structure inspection (Tier 4) as fallback."""
        # Task with no project membership or name pattern
        business_task = make_mock_task("bus_001", "Acme Corporation")

        mock_client.tasks.get_async = AsyncMock(return_value=business_task)

        # Mock subtasks that indicate Business structure
        subtasks = [
            make_subtask("holder_001", "Contacts"),
            make_subtask("holder_002", "Units"),
            make_subtask("holder_003", "Location"),
        ]
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(return_value=subtasks)

        with patch.object(Business, "_fetch_holders_async", new_callable=AsyncMock):
            result = await hydrate_from_gid_async(mock_client, "bus_001")

        assert result.entry_type == EntityType.BUSINESS


# --- Test: API Call Tracking ---


class TestApiCallTracking:
    """Tests for API call counting in HydrationResult."""

    async def test_api_calls_counted(
        self,
        mock_client: MagicMock,
    ) -> None:
        """API calls are tracked in result."""
        business_task = make_mock_task("bus_001", "Acme Corporation")

        mock_client.tasks.get_async = AsyncMock(return_value=business_task)

        subtasks = [make_subtask("holder_001", "Contacts")]
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(return_value=subtasks)

        with patch.object(Business, "_fetch_holders_async", new_callable=AsyncMock):
            result = await hydrate_from_gid_async(mock_client, "bus_001")

        # Should have at least 1 API call (initial fetch)
        # Plus detection calls
        assert result.api_calls >= 1

    async def test_api_calls_increase_with_traversal(
        self,
        mock_client: MagicMock,
    ) -> None:
        """API calls increase when traversing hierarchy."""
        contact_task = make_mock_task("contact_001", "John Smith", parent_gid="holder_001")
        holder_task = make_mock_task("holder_001", "Contacts", parent_gid="bus_001")
        business_task = make_mock_task("bus_001", "Acme Corporation")

        tasks = {
            "contact_001": contact_task,
            "holder_001": holder_task,
            "bus_001": business_task,
        }
        mock_client.tasks.get_async = AsyncMock(
            side_effect=lambda gid, **kwargs: tasks.get(gid, business_task)
        )

        subtasks = [make_subtask("holder_001", "Contacts")]
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(return_value=subtasks)

        with patch.object(Business, "_fetch_holders_async", new_callable=AsyncMock):
            result = await hydrate_from_gid_async(mock_client, "contact_001")

        # Traversal adds API calls
        assert result.api_calls >= 3  # At least: contact, holder, business


# --- Test: Edge Cases ---


class TestHydrationEdgeCases:
    """Tests for edge cases in hydration."""

    async def test_orphan_task_raises_error(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Task without parent and unknown type raises error."""
        orphan_task = make_mock_task("orphan_001", "Orphan Task")

        mock_client.tasks.get_async = AsyncMock(return_value=orphan_task)

        # No subtasks (not a Business structure)
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(return_value=[])

        with pytest.raises(HydrationError):
            await hydrate_from_gid_async(mock_client, "orphan_001")

    async def test_empty_holders_tracked_as_warning(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Empty holders are tracked as warnings, not failures."""
        business_task = make_mock_task("bus_001", "Acme Corporation")

        mock_client.tasks.get_async = AsyncMock(return_value=business_task)

        # Business structure detected
        subtasks = [make_subtask("holder_001", "Contacts")]
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(return_value=subtasks)

        # Empty holders are not failures (just no children)
        with patch.object(Business, "_fetch_holders_async", new_callable=AsyncMock):
            result = await hydrate_from_gid_async(mock_client, "bus_001")

        # Should succeed (empty is valid state)
        assert result.is_complete is True
