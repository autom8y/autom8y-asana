"""Integration tests for entity type detection.

Per TDD-TECH-DEBT-REMEDIATION Phase 3 / FR-TEST-001:
Tests detection system with realistic task data across all tiers.

These tests validate the full detection chain with mocked API responses,
ensuring:
- Tier 1 detection with project membership works correctly
- Tier 2 detection with decorated names handles edge cases
- Tier 3 detection with parent inference works correctly
- Edge cases like missing projects and unknown entities are handled

Hard Constraint: Uses mocks (no live Asana credentials required in CI).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.models.business.detection import (
    CONFIDENCE_TIER_1,
    CONFIDENCE_TIER_2,
    CONFIDENCE_TIER_3,
    DetectionResult,
    EntityType,
    detect_by_parent,
    detect_entity_type,
    detect_entity_type_async,
)
from autom8_asana.models.business.registry import (
    get_registry,
    get_workspace_registry,
)
from autom8_asana.models.task import Task


# --- Fixtures ---


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock AsanaClient with workspace configuration."""
    client = MagicMock()
    client.default_workspace_gid = "workspace_test_123"
    return client


@pytest.fixture
def business_task() -> Task:
    """Create a Business task with registered project membership."""
    project_gid = "business_project_gid_001"
    registry = get_registry()
    registry.register(project_gid, EntityType.BUSINESS)

    return Task(
        gid="business_task_001",
        name="Acme Corporation",
        memberships=[{"project": {"gid": project_gid}}],
    )


@pytest.fixture
def sales_process_task() -> Task:
    """Create a Sales Process task with registered pipeline project."""
    project_gid = "sales_pipeline_gid_001"
    registry = get_registry()
    registry.register(project_gid, EntityType.PROCESS)

    return Task(
        gid="process_task_001",
        name="Demo Call - Acme Corp",
        memberships=[{"project": {"gid": project_gid}}],
    )


@pytest.fixture
def contact_task() -> Task:
    """Create a Contact task without project membership."""
    return Task(
        gid="contact_task_001",
        name="John Smith",
        memberships=None,
    )


# --- Test: Tier 1 Detection (Project Membership) ---


class TestTier1Detection:
    """Tier 1: Project membership detection.

    Tests deterministic O(1) detection via registered project GIDs.
    """

    def test_business_detected_by_project(
        self,
        business_task: Task,
    ) -> None:
        """Business task is detected via project membership."""
        result = detect_entity_type(business_task)

        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 1
        assert result.confidence == CONFIDENCE_TIER_1
        assert result.needs_healing is False

    def test_process_detected_by_pipeline_project(
        self,
        sales_process_task: Task,
    ) -> None:
        """Process task is detected via pipeline project membership."""
        result = detect_entity_type(sales_process_task)

        assert result.entity_type == EntityType.PROCESS
        assert result.tier_used == 1
        assert result.confidence == CONFIDENCE_TIER_1
        assert result.needs_healing is False

    def test_unregistered_project_falls_through(
        self,
    ) -> None:
        """Task in unregistered project falls through to later tiers."""
        task = Task(
            gid="task_001",
            name="Random Task",
            memberships=[{"project": {"gid": "unregistered_project_gid"}}],
        )

        result = detect_entity_type(task)

        # Should fall through to Tier 5 (UNKNOWN) - no name pattern match
        assert result.entity_type == EntityType.UNKNOWN
        assert result.tier_used == 5

    def test_missing_memberships_falls_through(
        self,
    ) -> None:
        """Task without memberships falls through to later tiers."""
        task = Task(
            gid="task_001",
            name="Orphan Task",
            memberships=None,
        )

        result = detect_entity_type(task)

        assert result.tier_used == 5
        assert result.entity_type == EntityType.UNKNOWN

    def test_empty_memberships_falls_through(
        self,
    ) -> None:
        """Task with empty memberships list falls through."""
        task = Task(
            gid="task_001",
            name="Empty Memberships Task",
            memberships=[],
        )

        result = detect_entity_type(task)

        assert result.tier_used == 5


# --- Test: Tier 2 Detection (Name Patterns) ---


class TestTier2Detection:
    """Tier 2: Name pattern detection with word boundary matching.

    Per ADR-0117: Tests word boundary-aware matching and decoration stripping.
    """

    @pytest.mark.parametrize(
        ("name", "expected_type"),
        [
            # Basic holder names
            ("Contacts", EntityType.CONTACT_HOLDER),
            ("Contact", EntityType.CONTACT_HOLDER),
            ("Units", EntityType.UNIT_HOLDER),
            ("Offers", EntityType.OFFER_HOLDER),
            ("Processes", EntityType.PROCESS_HOLDER),
            ("Location", EntityType.LOCATION_HOLDER),
            ("DNA", EntityType.DNA_HOLDER),
            ("Reconciliations", EntityType.RECONCILIATIONS_HOLDER),
            ("Asset Edit", EntityType.ASSET_EDIT_HOLDER),
            ("Videography", EntityType.VIDEOGRAPHY_HOLDER),
        ],
    )
    def test_basic_holder_names(
        self,
        name: str,
        expected_type: EntityType,
    ) -> None:
        """Basic holder names are detected correctly."""
        task = Task(gid="test", name=name)

        result = detect_entity_type(task)

        assert result.entity_type == expected_type
        assert result.tier_used == 2
        assert result.confidence == CONFIDENCE_TIER_2
        assert result.needs_healing is True

    @pytest.mark.parametrize(
        ("name", "expected_type"),
        [
            # Decorated names - prefixes
            ("[URGENT] Contacts", EntityType.CONTACT_HOLDER),
            (">> Contacts", EntityType.CONTACT_HOLDER),
            ("1. Contacts", EntityType.CONTACT_HOLDER),
            ("- Contacts", EntityType.CONTACT_HOLDER),
            ("* Contacts", EntityType.CONTACT_HOLDER),
            # Decorated names - suffixes
            ("Contacts (Primary)", EntityType.CONTACT_HOLDER),
            ("Contacts <<", EntityType.CONTACT_HOLDER),
            # Decorated names - both
            ("[IMPORTANT] Units (Main)", EntityType.UNIT_HOLDER),
            (">> Offers <<", EntityType.OFFER_HOLDER),
        ],
    )
    def test_decorated_names(
        self,
        name: str,
        expected_type: EntityType,
    ) -> None:
        """Decorated names are stripped and matched correctly."""
        task = Task(gid="test", name=name)

        result = detect_entity_type(task)

        assert result.entity_type == expected_type
        assert result.tier_used == 2
        assert result.needs_healing is True

    @pytest.mark.parametrize(
        ("name", "expected_type"),
        [
            # Embedded in longer strings (word boundary matching)
            ("Acme Corp - Contacts (Primary)", EntityType.CONTACT_HOLDER),
            ("All Business Units Here", EntityType.UNIT_HOLDER),
            ("Special Offers List", EntityType.OFFER_HOLDER),
            ("Our Processes Overview", EntityType.PROCESS_HOLDER),
        ],
    )
    def test_patterns_in_context(
        self,
        name: str,
        expected_type: EntityType,
    ) -> None:
        """Patterns embedded in longer names are matched with word boundaries."""
        task = Task(gid="test", name=name)

        result = detect_entity_type(task)

        assert result.entity_type == expected_type

    @pytest.mark.parametrize(
        "name",
        [
            # False positives avoided by word boundary matching
            "Community",  # Contains "unit" but not at word boundary
            "Recontact",  # Contains "contact" but not at word boundary
            "Prooffer",  # Contains "offer" but not at word boundary
            "Unprocessed",  # Contains "process" but not at word boundary
            "Random Task Name",
            "Something Else",
            "",
        ],
    )
    def test_false_positives_avoided(
        self,
        name: str,
    ) -> None:
        """False positives are avoided by word boundary matching."""
        task = Task(gid="test", name=name)

        result = detect_entity_type(task)

        assert result.entity_type == EntityType.UNKNOWN
        assert result.tier_used == 5

    def test_case_insensitive_matching(
        self,
    ) -> None:
        """Pattern matching is case-insensitive."""
        for name in ["CONTACTS", "Contacts", "contacts", "CoNtAcTs"]:
            task = Task(gid="test", name=name)
            result = detect_entity_type(task)
            assert result.entity_type == EntityType.CONTACT_HOLDER


# --- Test: Tier 3 Detection (Parent Inference) ---


class TestTier3Detection:
    """Tier 3: Parent inference detection.

    Tests child type inference from known parent types.
    """

    @pytest.mark.parametrize(
        ("parent_type", "expected_child_type"),
        [
            (EntityType.CONTACT_HOLDER, EntityType.CONTACT),
            (EntityType.UNIT_HOLDER, EntityType.UNIT),
            (EntityType.OFFER_HOLDER, EntityType.OFFER),
            (EntityType.PROCESS_HOLDER, EntityType.PROCESS),
            (EntityType.LOCATION_HOLDER, EntityType.LOCATION),
        ],
    )
    def test_parent_inference_rules(
        self,
        parent_type: EntityType,
        expected_child_type: EntityType,
    ) -> None:
        """Child type is correctly inferred from parent type."""
        task = Task(gid="child_001", name="Some Child Task")

        result = detect_by_parent(task, parent_type)

        assert result is not None
        assert result.entity_type == expected_child_type
        assert result.tier_used == 3
        assert result.confidence == CONFIDENCE_TIER_3
        assert result.needs_healing is True

    def test_contact_inferred_from_contact_holder(
        self,
        contact_task: Task,
    ) -> None:
        """Contact is inferred from ContactHolder parent."""
        result = detect_entity_type(
            contact_task,
            parent_type=EntityType.CONTACT_HOLDER,
        )

        assert result.entity_type == EntityType.CONTACT
        assert result.tier_used == 3

    def test_tier_3_used_when_no_name_pattern(
        self,
    ) -> None:
        """Tier 3 is used when name doesn't match any pattern."""
        task = Task(gid="task_001", name="John Smith - CEO")

        result = detect_entity_type(task, parent_type=EntityType.CONTACT_HOLDER)

        assert result.entity_type == EntityType.CONTACT
        assert result.tier_used == 3

    def test_parent_without_child_mapping_returns_none(
        self,
    ) -> None:
        """Parent types without child mappings return None from detect_by_parent."""
        task = Task(gid="task_001", name="Some Task")

        # BUSINESS doesn't have a child inference rule
        result = detect_by_parent(task, EntityType.BUSINESS)

        assert result is None


# --- Test: Edge Cases and Error Handling ---


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_none_name(
        self,
    ) -> None:
        """Task with None name is handled gracefully."""
        task = Task(gid="task_001", name=None)

        result = detect_entity_type(task)

        assert result.entity_type == EntityType.UNKNOWN
        assert result.tier_used == 5

    def test_whitespace_only_name(
        self,
    ) -> None:
        """Task with whitespace-only name is handled."""
        task = Task(gid="task_001", name="   ")

        result = detect_entity_type(task)

        assert result.entity_type == EntityType.UNKNOWN

    def test_malformed_membership(
        self,
    ) -> None:
        """Malformed membership data is handled gracefully."""
        # Missing project key
        task = Task(
            gid="task_001",
            name="Test",
            memberships=[{"section": {"gid": "section_001"}}],
        )
        result = detect_entity_type(task)
        assert result.tier_used in (2, 5)  # Falls through

        # Missing gid in project
        task = Task(
            gid="task_002",
            name="Test",
            memberships=[{"project": {"name": "No GID"}}],
        )
        result = detect_entity_type(task)
        assert result.tier_used in (2, 5)

    def test_tier_1_short_circuits_tier_2(
        self,
    ) -> None:
        """Tier 1 detection short-circuits Tier 2 even with matching name."""
        project_gid = "business_gid"
        registry = get_registry()
        registry.register(project_gid, EntityType.BUSINESS)

        # Task has both: registered project AND name pattern (Contacts)
        task = Task(
            gid="task_001",
            name="Contacts",  # Would match CONTACT_HOLDER via Tier 2
            memberships=[{"project": {"gid": project_gid}}],
        )

        result = detect_entity_type(task)

        # Should use Tier 1 (BUSINESS), not Tier 2 (CONTACT_HOLDER)
        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 1

    def test_multiple_memberships_uses_first(
        self,
    ) -> None:
        """First project membership is used for detection."""
        business_gid = "business_gid"
        contact_gid = "contact_gid"
        registry = get_registry()
        registry.register(business_gid, EntityType.BUSINESS)
        registry.register(contact_gid, EntityType.CONTACT)

        task = Task(
            gid="task_001",
            name="Multi-project Task",
            memberships=[
                {"project": {"gid": business_gid}},  # First
                {"project": {"gid": contact_gid}},  # Second
            ],
        )

        result = detect_entity_type(task)

        # Should use first membership (BUSINESS)
        assert result.entity_type == EntityType.BUSINESS


# --- Test: Async Detection with Discovery ---


@pytest.mark.asyncio
class TestAsyncDetection:
    """Async detection with workspace discovery.

    Per TDD-WORKSPACE-PROJECT-REGISTRY: Tests async detection with lazy discovery.
    """

    def _make_mock_project(self, gid: str, name: str) -> MagicMock:
        """Create a mock Project with gid and name."""
        project = MagicMock()
        project.gid = gid
        project.name = name
        return project

    async def test_process_detected_via_workspace_discovery(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Process is detected via workspace discovery for pipeline projects."""
        # Mock Sales Pipeline project discovery
        sales_project = self._make_mock_project("sales_gid", "Sales Pipeline")
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=[sales_project]
        )

        task = Task(
            gid="process_001",
            name="Demo Call - Acme",
            memberships=[{"project": {"gid": "sales_gid"}}],
        )

        result = await detect_entity_type_async(task, mock_client)

        assert result.entity_type == EntityType.PROCESS
        assert result.tier_used == 1
        assert result.needs_healing is False

    async def test_static_registry_takes_precedence(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Static registry entries take precedence over discovery."""
        # Pre-register in static registry
        registry = get_registry()
        registry.register("static_gid", EntityType.BUSINESS)

        task = Task(
            gid="task_001",
            name="Test Task",
            memberships=[{"project": {"gid": "static_gid"}}],
        )

        result = await detect_entity_type_async(task, mock_client)

        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 1
        # No discovery API call should be made
        mock_client.projects.list_async.assert_not_called()

    async def test_discovery_registers_multiple_pipelines(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Discovery registers all pipeline projects found."""
        from autom8_asana.models.business.process import ProcessType

        # Mock multiple pipeline projects
        sales = self._make_mock_project("sales_gid", "Sales Pipeline")
        onboarding = self._make_mock_project("onboarding_gid", "Onboarding")
        retention = self._make_mock_project("retention_gid", "Retention")
        other = self._make_mock_project("other_gid", "Random Project")

        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=[sales, onboarding, retention, other]
        )

        task = Task(
            gid="task_001",
            name="Onboarding Task",
            memberships=[{"project": {"gid": "onboarding_gid"}}],
        )

        await detect_entity_type_async(task, mock_client)

        # All pipeline projects should be registered
        static_registry = get_registry()
        assert static_registry.lookup("sales_gid") == EntityType.PROCESS
        assert static_registry.lookup("onboarding_gid") == EntityType.PROCESS
        assert static_registry.lookup("retention_gid") == EntityType.PROCESS
        # Non-pipeline project should NOT be registered
        assert static_registry.lookup("other_gid") is None

        # ProcessType should be available
        workspace_registry = get_workspace_registry()
        assert workspace_registry.get_process_type("sales_gid") == ProcessType.SALES
        assert (
            workspace_registry.get_process_type("onboarding_gid")
            == ProcessType.ONBOARDING
        )

    async def test_async_falls_through_to_name_pattern(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Async detection falls through to Tier 2 for non-pipeline projects."""
        # Mock non-pipeline project
        other = self._make_mock_project("other_gid", "Random Project")
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=[other]
        )

        # Task with holder name pattern
        task = Task(
            gid="task_001",
            name="Contacts",
            memberships=[{"project": {"gid": "other_gid"}}],
        )

        result = await detect_entity_type_async(task, mock_client)

        # Falls through to Tier 2
        assert result.entity_type == EntityType.CONTACT_HOLDER
        assert result.tier_used == 2

    async def test_discovery_is_idempotent(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Discovery only happens once, subsequent calls use cached registry."""
        sales = self._make_mock_project("sales_gid", "Sales Pipeline")
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=[sales]
        )

        task1 = Task(
            gid="task1",
            name="Task 1",
            memberships=[{"project": {"gid": "sales_gid"}}],
        )
        task2 = Task(
            gid="task2",
            name="Task 2",
            memberships=[{"project": {"gid": "sales_gid"}}],
        )

        await detect_entity_type_async(task1, mock_client)
        await detect_entity_type_async(task2, mock_client)

        # Discovery API called only once
        mock_client.projects.list_async.assert_called_once()

    async def test_no_memberships_skips_discovery(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Task without memberships skips discovery entirely."""
        task = Task(
            gid="task_001",
            name="Orphan Task",
            memberships=None,
        )

        result = await detect_entity_type_async(task, mock_client)

        assert result.entity_type == EntityType.UNKNOWN
        mock_client.projects.list_async.assert_not_called()


# --- Test: DetectionResult ---


class TestDetectionResult:
    """Tests for DetectionResult dataclass behavior."""

    def test_bool_true_for_detected_types(self) -> None:
        """DetectionResult is truthy for non-UNKNOWN types."""
        result = DetectionResult(
            entity_type=EntityType.BUSINESS,
            confidence=1.0,
            tier_used=1,
            needs_healing=False,
            expected_project_gid="123",
        )

        assert bool(result) is True

    def test_bool_false_for_unknown(self) -> None:
        """DetectionResult is falsy for UNKNOWN type."""
        result = DetectionResult(
            entity_type=EntityType.UNKNOWN,
            confidence=0.0,
            tier_used=5,
            needs_healing=True,
            expected_project_gid=None,
        )

        assert bool(result) is False

    def test_is_deterministic_tier_1_only(self) -> None:
        """is_deterministic is True only for Tier 1."""
        tier_1_result = DetectionResult(
            entity_type=EntityType.BUSINESS,
            confidence=1.0,
            tier_used=1,
            needs_healing=False,
            expected_project_gid="123",
        )
        tier_2_result = DetectionResult(
            entity_type=EntityType.CONTACT_HOLDER,
            confidence=0.6,
            tier_used=2,
            needs_healing=True,
            expected_project_gid=None,
        )

        assert tier_1_result.is_deterministic is True
        assert tier_2_result.is_deterministic is False
