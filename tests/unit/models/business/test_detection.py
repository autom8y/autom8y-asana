"""Unit tests for detection chain.

Per TDD-DETECTION Phase 2: Tests for all detection tiers.
Per ADR-0094: Detection Fallback Chain Design.

Test cases:
1. DetectionResult immutability and __bool__
2. Tier 1: registered project -> correct type
3. Tier 1: unregistered project -> None
4. Tier 2: name patterns matching
5. Tier 3: parent inference rules
6. Tier 4: structure inspection (mock API)
7. Unified: short-circuit behavior
8. Unified: falls through to Tier 5
9. Performance: Tier 1 < 1ms
10. Backward compatibility: detect_by_name deprecation
"""

from __future__ import annotations

import time
from dataclasses import FrozenInstanceError
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.models.business.detection import (
    CONFIDENCE_TIER_1,
    CONFIDENCE_TIER_2,
    CONFIDENCE_TIER_3,
    CONFIDENCE_TIER_4,
    CONFIDENCE_TIER_5,
    PARENT_CHILD_MAP,
    DetectionResult,
    EntityType,
    _detect_tier1_project_membership_async,
    detect_by_name,
    detect_by_parent,
    detect_by_project,
    detect_by_structure_async,
    detect_entity_type,
    detect_entity_type_async,
)
from autom8_asana.models.business.registry import (
    ProjectTypeRegistry,
    WorkspaceProjectRegistry,
    get_registry,
    get_workspace_registry,
)
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from collections.abc import Generator


# --- Fixtures ---


@pytest.fixture
def clean_registry() -> Generator[None, None, None]:
    """Reset registry before and after each test for isolation."""
    ProjectTypeRegistry.reset()
    yield
    ProjectTypeRegistry.reset()


@pytest.fixture
def clean_registries() -> Generator[None, None, None]:
    """Reset both registries before and after each test for isolation.

    Per TDD-WORKSPACE-PROJECT-REGISTRY Appendix C: Test fixture pattern.
    """
    ProjectTypeRegistry.reset()
    WorkspaceProjectRegistry.reset()
    yield
    ProjectTypeRegistry.reset()
    WorkspaceProjectRegistry.reset()


@pytest.fixture
def registered_business_project(clean_registry: None) -> str:
    """Register a Business project and return the GID."""
    gid = "1234567890123456"
    registry = get_registry()
    registry.register(gid, EntityType.BUSINESS)
    return gid


@pytest.fixture
def registered_contact_project(clean_registry: None) -> str:
    """Register a Contact project and return the GID."""
    gid = "contact_project_gid"
    registry = get_registry()
    registry.register(gid, EntityType.CONTACT)
    return gid


def make_task(
    gid: str = "task_gid",
    name: str | None = "Test Task",
    memberships: list[dict] | None = None,
) -> Task:
    """Create a Task with specified attributes."""
    return Task(gid=gid, name=name, memberships=memberships)


def make_task_with_project(
    task_gid: str,
    project_gid: str,
    name: str | None = None,
) -> Task:
    """Create a Task with a project membership."""
    return Task(
        gid=task_gid,
        name=name,
        memberships=[{"project": {"gid": project_gid}}],
    )


# --- Test: DetectionResult ---


class TestDetectionResult:
    """Tests for DetectionResult dataclass."""

    def test_creation(self) -> None:
        """DetectionResult can be created with all fields."""
        result = DetectionResult(
            entity_type=EntityType.BUSINESS,
            confidence=1.0,
            tier_used=1,
            needs_healing=False,
            expected_project_gid="123",
        )

        assert result.entity_type == EntityType.BUSINESS
        assert result.confidence == 1.0
        assert result.tier_used == 1
        assert result.needs_healing is False
        assert result.expected_project_gid == "123"

    def test_frozen_immutability(self) -> None:
        """DetectionResult is immutable (frozen)."""
        result = DetectionResult(
            entity_type=EntityType.BUSINESS,
            confidence=1.0,
            tier_used=1,
            needs_healing=False,
            expected_project_gid="123",
        )

        with pytest.raises(FrozenInstanceError):
            result.entity_type = EntityType.CONTACT  # type: ignore[misc]

    def test_bool_true_for_non_unknown(self) -> None:
        """__bool__ returns True for non-UNKNOWN types."""
        for entity_type in EntityType:
            if entity_type == EntityType.UNKNOWN:
                continue

            result = DetectionResult(
                entity_type=entity_type,
                confidence=0.5,
                tier_used=2,
                needs_healing=True,
                expected_project_gid=None,
            )

            assert bool(result) is True

    def test_bool_false_for_unknown(self) -> None:
        """__bool__ returns False for UNKNOWN type."""
        result = DetectionResult(
            entity_type=EntityType.UNKNOWN,
            confidence=0.0,
            tier_used=5,
            needs_healing=True,
            expected_project_gid=None,
        )

        assert bool(result) is False

    def test_is_deterministic_tier_1(self) -> None:
        """is_deterministic is True for tier 1."""
        result = DetectionResult(
            entity_type=EntityType.BUSINESS,
            confidence=1.0,
            tier_used=1,
            needs_healing=False,
            expected_project_gid="123",
        )

        assert result.is_deterministic is True

    def test_is_deterministic_other_tiers(self) -> None:
        """is_deterministic is False for tiers > 1."""
        for tier in [2, 3, 4, 5]:
            result = DetectionResult(
                entity_type=EntityType.BUSINESS,
                confidence=0.5,
                tier_used=tier,
                needs_healing=True,
                expected_project_gid="123",
            )

            assert result.is_deterministic is False


# --- Test: Tier 1 - detect_by_project ---


class TestDetectByProject:
    """Tests for Tier 1 project membership detection."""

    def test_registered_project_returns_correct_type(
        self,
        registered_business_project: str,
    ) -> None:
        """Registered project GID returns correct EntityType."""
        task = make_task_with_project(
            task_gid="task1",
            project_gid=registered_business_project,
        )

        result = detect_by_project(task)

        assert result is not None
        assert result.entity_type == EntityType.BUSINESS
        assert result.confidence == CONFIDENCE_TIER_1
        assert result.tier_used == 1
        assert result.needs_healing is False
        assert result.expected_project_gid == registered_business_project

    def test_unregistered_project_returns_none(self, clean_registry: None) -> None:
        """Unregistered project GID returns None."""
        task = make_task_with_project(
            task_gid="task1",
            project_gid="unregistered_project_gid",
        )

        result = detect_by_project(task)

        assert result is None

    def test_no_memberships_returns_none(self, clean_registry: None) -> None:
        """Task with no memberships returns None."""
        task = make_task(gid="task1", memberships=None)

        result = detect_by_project(task)

        assert result is None

    def test_empty_memberships_returns_none(self, clean_registry: None) -> None:
        """Task with empty memberships list returns None."""
        task = make_task(gid="task1", memberships=[])

        result = detect_by_project(task)

        assert result is None

    def test_membership_without_project_returns_none(
        self,
        clean_registry: None,
    ) -> None:
        """Membership without project key returns None."""
        task = make_task(gid="task1", memberships=[{"section": {"gid": "section1"}}])

        result = detect_by_project(task)

        assert result is None

    def test_project_without_gid_returns_none(self, clean_registry: None) -> None:
        """Project without gid returns None."""
        task = make_task(gid="task1", memberships=[{"project": {"name": "No GID"}}])

        result = detect_by_project(task)

        assert result is None

    def test_performance_under_1ms(self, registered_business_project: str) -> None:
        """Tier 1 detection completes in under 1ms."""
        task = make_task_with_project(
            task_gid="task1",
            project_gid=registered_business_project,
        )

        # Warm up
        detect_by_project(task)

        # Measure
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            detect_by_project(task)
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / iterations) * 1000
        assert avg_time_ms < 1.0, f"Tier 1 detection took {avg_time_ms:.3f}ms (>1ms)"


# --- Test: Tier 2 - Name Pattern Matching ---


class TestDetectByNamePattern:
    """Tests for Tier 2 name pattern detection (via detect_entity_type)."""

    @pytest.mark.parametrize(
        ("name", "expected_type"),
        [
            ("Contacts", EntityType.CONTACT_HOLDER),
            ("contacts", EntityType.CONTACT_HOLDER),
            ("CONTACTS", EntityType.CONTACT_HOLDER),
            ("My Contacts List", EntityType.CONTACT_HOLDER),
            ("Units", EntityType.UNIT_HOLDER),
            ("All Units Here", EntityType.UNIT_HOLDER),
            ("Offers", EntityType.OFFER_HOLDER),
            ("Processes", EntityType.PROCESS_HOLDER),
            ("Location", EntityType.LOCATION_HOLDER),
            ("DNA", EntityType.DNA_HOLDER),
            ("Reconciliations", EntityType.RECONCILIATIONS_HOLDER),
            ("Asset Edit", EntityType.ASSET_EDIT_HOLDER),
            ("Videography", EntityType.VIDEOGRAPHY_HOLDER),
        ],
    )
    def test_name_patterns_match(
        self,
        clean_registry: None,
        name: str,
        expected_type: EntityType,
    ) -> None:
        """Name containing pattern returns correct type via Tier 2."""
        task = make_task(gid="task1", name=name)

        result = detect_entity_type(task)

        assert result.entity_type == expected_type
        assert result.confidence == CONFIDENCE_TIER_2
        assert result.tier_used == 2
        assert result.needs_healing is True

    def test_no_pattern_match_falls_through(self, clean_registry: None) -> None:
        """Name without pattern falls through to UNKNOWN."""
        task = make_task(gid="task1", name="Random Task Name")

        result = detect_entity_type(task)

        assert result.entity_type == EntityType.UNKNOWN
        assert result.tier_used == 5

    def test_none_name_falls_through(self, clean_registry: None) -> None:
        """None name falls through to UNKNOWN."""
        task = make_task(gid="task1", name=None)

        result = detect_entity_type(task)

        assert result.entity_type == EntityType.UNKNOWN
        assert result.tier_used == 5


# --- Test: Tier 3 - Parent Inference ---


class TestDetectByParent:
    """Tests for Tier 3 parent type inference."""

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
        clean_registry: None,
        parent_type: EntityType,
        expected_child_type: EntityType,
    ) -> None:
        """Parent type correctly infers child type."""
        task = make_task(gid="task1", name="Some Child Task")

        result = detect_by_parent(task, parent_type)

        assert result is not None
        assert result.entity_type == expected_child_type
        assert result.confidence == CONFIDENCE_TIER_3
        assert result.tier_used == 3
        assert result.needs_healing is True

    def test_parent_without_mapping_returns_none(self, clean_registry: None) -> None:
        """Parent type without mapping returns None."""
        task = make_task(gid="task1", name="Some Task")

        # BUSINESS doesn't have a child inference rule
        result = detect_by_parent(task, EntityType.BUSINESS)

        assert result is None

    def test_all_parent_child_map_entries_covered(self) -> None:
        """All PARENT_CHILD_MAP entries are tested."""
        # This ensures we don't miss any inference rules
        expected_mappings = {
            EntityType.CONTACT_HOLDER: EntityType.CONTACT,
            EntityType.UNIT_HOLDER: EntityType.UNIT,
            EntityType.OFFER_HOLDER: EntityType.OFFER,
            EntityType.PROCESS_HOLDER: EntityType.PROCESS,
            EntityType.LOCATION_HOLDER: EntityType.LOCATION,
        }

        assert PARENT_CHILD_MAP == expected_mappings


# --- Test: Tier 4 - Structure Inspection ---


class TestDetectByStructureAsync:
    """Tests for Tier 4 structure inspection."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock AsanaClient."""
        return MagicMock()

    def _make_subtask(self, name: str) -> MagicMock:
        """Create a mock subtask with a name."""
        subtask = MagicMock()
        subtask.name = name
        return subtask

    @pytest.mark.asyncio
    async def test_business_structure_detected(
        self,
        clean_registry: None,
        mock_client: MagicMock,
    ) -> None:
        """Business detected via holder subtasks (contacts, units, location)."""
        task = make_task(gid="task1", name="Acme Corp")

        # Mock subtasks response
        subtasks = [
            self._make_subtask("Contacts"),
            self._make_subtask("Units"),
            self._make_subtask("Location"),
        ]
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(
            return_value=subtasks
        )

        result = await detect_by_structure_async(task, mock_client)

        assert result is not None
        assert result.entity_type == EntityType.BUSINESS
        assert result.confidence == CONFIDENCE_TIER_4
        assert result.tier_used == 4
        assert result.needs_healing is True

    @pytest.mark.asyncio
    async def test_unit_structure_detected(
        self,
        clean_registry: None,
        mock_client: MagicMock,
    ) -> None:
        """Unit detected via holder subtasks (offers, processes)."""
        task = make_task(gid="task1", name="Premium Package")

        # Mock subtasks response
        subtasks = [
            self._make_subtask("Offers"),
            self._make_subtask("Processes"),
        ]
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(
            return_value=subtasks
        )

        result = await detect_by_structure_async(task, mock_client)

        assert result is not None
        assert result.entity_type == EntityType.UNIT
        assert result.confidence == CONFIDENCE_TIER_4
        assert result.tier_used == 4
        assert result.needs_healing is True

    @pytest.mark.asyncio
    async def test_no_structure_match_returns_none(
        self,
        clean_registry: None,
        mock_client: MagicMock,
    ) -> None:
        """No structure match returns None."""
        task = make_task(gid="task1", name="Random Task")

        # Mock subtasks response with no indicators
        subtasks = [
            self._make_subtask("Subtask A"),
            self._make_subtask("Subtask B"),
        ]
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(
            return_value=subtasks
        )

        result = await detect_by_structure_async(task, mock_client)

        assert result is None

    @pytest.mark.asyncio
    async def test_partial_business_indicators_still_match(
        self,
        clean_registry: None,
        mock_client: MagicMock,
    ) -> None:
        """Business detected with partial indicator set (any intersection)."""
        task = make_task(gid="task1", name="Some Business")

        # Only has "contacts" - still enough to detect Business
        subtasks = [self._make_subtask("Contacts")]
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(
            return_value=subtasks
        )

        result = await detect_by_structure_async(task, mock_client)

        assert result is not None
        assert result.entity_type == EntityType.BUSINESS


# --- Test: Unified Detection Functions ---


class TestDetectEntityType:
    """Tests for unified sync detection (detect_entity_type)."""

    def test_tier_1_short_circuits(self, registered_business_project: str) -> None:
        """Detection short-circuits at Tier 1 when project is registered."""
        # Task has both: registered project AND name pattern
        task = Task(
            gid="task1",
            name="Contacts",  # Would match Tier 2
            memberships=[{"project": {"gid": registered_business_project}}],
        )

        result = detect_entity_type(task)

        # Should use Tier 1 (project), not Tier 2 (name)
        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 1
        assert result.needs_healing is False

    def test_tier_2_short_circuits_over_tier_3(self, clean_registry: None) -> None:
        """Detection short-circuits at Tier 2 before Tier 3."""
        task = make_task(gid="task1", name="Contacts")

        # Pass parent_type that would infer different type
        result = detect_entity_type(task, parent_type=EntityType.UNIT_HOLDER)

        # Should use Tier 2 (name pattern), not Tier 3 (parent inference)
        assert result.entity_type == EntityType.CONTACT_HOLDER
        assert result.tier_used == 2

    def test_tier_3_used_when_no_name_pattern(self, clean_registry: None) -> None:
        """Tier 3 used when name doesn't match any pattern."""
        task = make_task(gid="task1", name="My Child Task")

        result = detect_entity_type(task, parent_type=EntityType.CONTACT_HOLDER)

        assert result.entity_type == EntityType.CONTACT
        assert result.tier_used == 3

    def test_falls_through_to_tier_5_unknown(self, clean_registry: None) -> None:
        """Falls through to Tier 5 UNKNOWN when all tiers fail."""
        task = make_task(gid="task1", name="Random Name")

        result = detect_entity_type(task)

        assert result.entity_type == EntityType.UNKNOWN
        assert result.confidence == CONFIDENCE_TIER_5
        assert result.tier_used == 5
        assert result.needs_healing is True
        assert result.expected_project_gid is None

    def test_parent_type_none_skips_tier_3(self, clean_registry: None) -> None:
        """parent_type=None skips Tier 3."""
        task = make_task(gid="task1", name="Random Name")

        result = detect_entity_type(task, parent_type=None)

        # Should go straight to Tier 5 (no parent inference without parent_type)
        assert result.tier_used == 5


class TestDetectEntityTypeAsync:
    """Tests for unified async detection (detect_entity_type_async)."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock AsanaClient."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_sync_tiers_used_first(
        self,
        registered_business_project: str,
        mock_client: MagicMock,
    ) -> None:
        """Sync tiers (1-3) are used before Tier 4."""
        task = make_task_with_project(
            task_gid="task1",
            project_gid=registered_business_project,
        )

        result = await detect_entity_type_async(
            task,
            mock_client,
            allow_structure_inspection=True,
        )

        # Should use Tier 1, not call API for Tier 4
        assert result.tier_used == 1
        mock_client.tasks.subtasks_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_tier_4_disabled_by_default(
        self,
        clean_registry: None,
        mock_client: MagicMock,
    ) -> None:
        """Tier 4 is disabled by default."""
        task = make_task(gid="task1", name="Random Name")

        result = await detect_entity_type_async(task, mock_client)

        # Should return UNKNOWN (Tier 5), not attempt Tier 4
        assert result.tier_used == 5
        mock_client.tasks.subtasks_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_tier_4_enabled_when_requested(
        self,
        clean_registry: None,
        mock_client: MagicMock,
    ) -> None:
        """Tier 4 is used when allow_structure_inspection=True."""
        task = make_task(gid="task1", name="Some Business")

        # Mock subtasks for Business detection
        subtask = MagicMock()
        subtask.name = "Contacts"
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(
            return_value=[subtask]
        )

        result = await detect_entity_type_async(
            task,
            mock_client,
            allow_structure_inspection=True,
        )

        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 4
        mock_client.tasks.subtasks_async.assert_called_once_with(task.gid)

    @pytest.mark.asyncio
    async def test_tier_4_falls_to_tier_5_on_no_match(
        self,
        clean_registry: None,
        mock_client: MagicMock,
    ) -> None:
        """Tier 4 falls through to Tier 5 when no structure match."""
        task = make_task(gid="task1", name="Random Task")

        # Mock subtasks with no indicators
        subtask = MagicMock()
        subtask.name = "Subtask A"
        mock_client.tasks.subtasks_async.return_value.collect = AsyncMock(
            return_value=[subtask]
        )

        result = await detect_entity_type_async(
            task,
            mock_client,
            allow_structure_inspection=True,
        )

        # Falls through to UNKNOWN
        assert result.entity_type == EntityType.UNKNOWN
        assert result.tier_used == 5


# --- Test: Backward Compatibility ---


class TestBackwardCompatibility:
    """Tests for backward compatibility with legacy detect_by_name."""

    def test_detect_by_name_emits_deprecation_warning(self) -> None:
        """detect_by_name() emits DeprecationWarning."""
        with pytest.warns(DeprecationWarning) as warning_list:
            detect_by_name("Contacts")

        assert len(warning_list) == 1
        assert "deprecated" in str(warning_list[0].message).lower()
        assert "detect_entity_type" in str(warning_list[0].message)

    def test_detect_by_name_still_works(self) -> None:
        """detect_by_name() still returns correct results."""
        with pytest.warns(DeprecationWarning):
            result = detect_by_name("Contacts")

        assert result == EntityType.CONTACT_HOLDER

    def test_detect_by_name_returns_none_for_unknown(self) -> None:
        """detect_by_name() returns None for unknown names."""
        with pytest.warns(DeprecationWarning):
            result = detect_by_name("Random Name")

        assert result is None


# --- Test: Edge Cases ---


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_name_string(self, clean_registry: None) -> None:
        """Empty string name is handled."""
        task = make_task(gid="task1", name="")

        result = detect_entity_type(task)

        assert result.entity_type == EntityType.UNKNOWN

    def test_whitespace_name(self, clean_registry: None) -> None:
        """Whitespace-only name is handled."""
        task = make_task(gid="task1", name="   ")

        result = detect_entity_type(task)

        assert result.entity_type == EntityType.UNKNOWN

    def test_case_insensitive_name_matching(self, clean_registry: None) -> None:
        """Name matching is case-insensitive."""
        for name in ["CONTACTS", "Contacts", "contacts", "CoNtAcTs"]:
            task = make_task(gid="task1", name=name)
            result = detect_entity_type(task)
            assert result.entity_type == EntityType.CONTACT_HOLDER

    def test_name_with_pattern_substring(self, clean_registry: None) -> None:
        """Name containing pattern as substring matches."""
        task = make_task(gid="task1", name="All My Contacts Here")

        result = detect_entity_type(task)

        assert result.entity_type == EntityType.CONTACT_HOLDER

    def test_multiple_project_memberships_uses_first(
        self,
        registered_business_project: str,
        registered_contact_project: str,
    ) -> None:
        """Multiple memberships: first project is used."""
        task = Task(
            gid="task1",
            name="Test",
            memberships=[
                {"project": {"gid": registered_business_project}},
                {"project": {"gid": registered_contact_project}},
            ],
        )

        result = detect_entity_type(task)

        # Should use first membership (Business)
        assert result.entity_type == EntityType.BUSINESS


# --- Test: Process Detection via ProjectTypeRegistry ---
# Per ADR-0101: Process detection now uses only ProjectTypeRegistry


class TestProcessDetection:
    """Tests for Process entity detection via ProjectTypeRegistry.

    Per ADR-0101: ProcessProjectRegistry removed, only ProjectTypeRegistry used.
    """

    @pytest.fixture
    def registered_process_project(self, clean_registry: None) -> str:
        """Register a Process project and return the GID."""
        gid = "process_project_gid"
        registry = get_registry()
        registry.register(gid, EntityType.PROCESS)
        return gid

    def test_tier1_detects_process_from_registered_project(
        self,
        registered_process_project: str,
    ) -> None:
        """Task in registered Process project is detected as PROCESS via Tier 1."""
        task = Task(
            gid="task1",
            name="Demo Call - Acme Corp",
            memberships=[{"project": {"gid": registered_process_project}}],
        )

        result = detect_entity_type(task)

        assert result.entity_type == EntityType.PROCESS
        assert result.confidence == CONFIDENCE_TIER_1
        assert result.tier_used == 1
        assert result.needs_healing is False
        assert result.expected_project_gid == registered_process_project

    def test_unregistered_project_falls_through(
        self,
        clean_registry: None,
    ) -> None:
        """Task in unregistered project falls through to later tiers."""
        task = Task(
            gid="task1",
            name="Some Task",
            memberships=[{"project": {"gid": "unregistered_project_gid"}}],
        )

        result = detect_entity_type(task)

        # Should fall through to Tier 5 (UNKNOWN) since no name pattern match
        assert result.entity_type == EntityType.UNKNOWN
        assert result.tier_used == 5


# --- Test: Async Tier 1 with Lazy Discovery ---
# Per TDD-WORKSPACE-PROJECT-REGISTRY Phase 2: Detection Integration Tests
# Per ADR-0109: Lazy discovery on first unregistered GID in async path


class TestAsyncTier1WithLazyDiscovery:
    """Tests for async Tier 1 detection with WorkspaceProjectRegistry.

    Per TDD-WORKSPACE-PROJECT-REGISTRY Phase 2:
    - _detect_tier1_project_membership_async triggers lazy discovery
    - detect_entity_type_async uses async Tier 1 first
    - Pipeline projects discovered and registered as EntityType.PROCESS
    """

    @pytest.fixture
    def mock_client_with_workspace(self) -> MagicMock:
        """Create a mock AsanaClient with default_workspace_gid."""
        client = MagicMock()
        client.default_workspace_gid = "workspace_123"
        return client

    def _make_mock_project(self, gid: str, name: str) -> MagicMock:
        """Create a mock Project with gid and name."""
        project = MagicMock()
        project.gid = gid
        project.name = name
        return project

    @pytest.mark.asyncio
    async def test_async_tier1_returns_static_registry_hit(
        self,
        clean_registries: None,
        mock_client_with_workspace: MagicMock,
    ) -> None:
        """Async Tier 1 returns result from static registry without discovery."""
        # Register a project in static registry
        registry = get_registry()
        registry.register("static_gid", EntityType.BUSINESS)

        task = Task(
            gid="task1",
            name="Some Task",
            memberships=[{"project": {"gid": "static_gid"}}],
        )

        result = await _detect_tier1_project_membership_async(
            task, mock_client_with_workspace
        )

        assert result is not None
        assert result.entity_type == EntityType.BUSINESS
        assert result.confidence == CONFIDENCE_TIER_1
        assert result.tier_used == 1
        assert result.needs_healing is False

        # Discovery should NOT have been triggered (no API call)
        mock_client_with_workspace.projects.list_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_tier1_triggers_discovery_on_unregistered_gid(
        self,
        clean_registries: None,
        mock_client_with_workspace: MagicMock,
    ) -> None:
        """Async Tier 1 triggers discovery when project GID not in static registry."""
        # Mock projects response with a Sales pipeline project
        sales_project = self._make_mock_project("sales_pipeline_gid", "Sales Pipeline")
        other_project = self._make_mock_project("other_gid", "Other Project")

        mock_client_with_workspace.projects.list_async.return_value.collect = AsyncMock(
            return_value=[sales_project, other_project]
        )

        # Task is in the Sales Pipeline project (not registered statically)
        task = Task(
            gid="task1",
            name="Demo Call - Acme",
            memberships=[{"project": {"gid": "sales_pipeline_gid"}}],
        )

        result = await _detect_tier1_project_membership_async(
            task, mock_client_with_workspace
        )

        # Should discover and detect as PROCESS
        assert result is not None
        assert result.entity_type == EntityType.PROCESS
        assert result.confidence == CONFIDENCE_TIER_1
        assert result.tier_used == 1
        assert result.needs_healing is False
        assert result.expected_project_gid == "sales_pipeline_gid"

        # Discovery should have been triggered
        mock_client_with_workspace.projects.list_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_tier1_discovers_multiple_pipeline_projects(
        self,
        clean_registries: None,
        mock_client_with_workspace: MagicMock,
    ) -> None:
        """Async Tier 1 discovery registers all pipeline projects."""
        # Mock multiple pipeline projects
        sales_project = self._make_mock_project("sales_gid", "Sales Pipeline")
        onboarding_project = self._make_mock_project(
            "onboarding_gid", "Client Onboarding"
        )
        retention_project = self._make_mock_project("retention_gid", "Retention")
        non_pipeline = self._make_mock_project("other_gid", "Other Project")

        mock_client_with_workspace.projects.list_async.return_value.collect = AsyncMock(
            return_value=[
                sales_project,
                onboarding_project,
                retention_project,
                non_pipeline,
            ]
        )

        # Task in Onboarding project triggers discovery
        task = Task(
            gid="task1",
            name="Onboarding Task",
            memberships=[{"project": {"gid": "onboarding_gid"}}],
        )

        result = await _detect_tier1_project_membership_async(
            task, mock_client_with_workspace
        )

        # Should detect as PROCESS
        assert result is not None
        assert result.entity_type == EntityType.PROCESS
        assert result.expected_project_gid == "onboarding_gid"

        # All pipeline projects should now be registered
        static_registry = get_registry()
        assert static_registry.lookup("sales_gid") == EntityType.PROCESS
        assert static_registry.lookup("onboarding_gid") == EntityType.PROCESS
        assert static_registry.lookup("retention_gid") == EntityType.PROCESS

        # Non-pipeline project should NOT be registered
        assert static_registry.lookup("other_gid") is None

    @pytest.mark.asyncio
    async def test_async_tier1_returns_none_for_non_pipeline_project(
        self,
        clean_registries: None,
        mock_client_with_workspace: MagicMock,
    ) -> None:
        """Async Tier 1 returns None for project not in static or dynamic registry."""
        # Mock projects response with no pipeline projects
        non_pipeline = self._make_mock_project("other_gid", "Random Project")

        mock_client_with_workspace.projects.list_async.return_value.collect = AsyncMock(
            return_value=[non_pipeline]
        )

        # Task in a project that doesn't match any pattern
        task = Task(
            gid="task1",
            name="Some Task",
            memberships=[{"project": {"gid": "unknown_gid"}}],
        )

        result = await _detect_tier1_project_membership_async(
            task, mock_client_with_workspace
        )

        # Should return None (project not a pipeline)
        assert result is None

        # Discovery was triggered
        mock_client_with_workspace.projects.list_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_tier1_no_memberships_returns_none(
        self,
        clean_registries: None,
        mock_client_with_workspace: MagicMock,
    ) -> None:
        """Async Tier 1 returns None when task has no memberships."""
        task = Task(
            gid="task1",
            name="Orphan Task",
            memberships=None,
        )

        result = await _detect_tier1_project_membership_async(
            task, mock_client_with_workspace
        )

        assert result is None
        mock_client_with_workspace.projects.list_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_tier1_empty_memberships_returns_none(
        self,
        clean_registries: None,
        mock_client_with_workspace: MagicMock,
    ) -> None:
        """Async Tier 1 returns None when task has empty memberships."""
        task = Task(
            gid="task1",
            name="Orphan Task",
            memberships=[],
        )

        result = await _detect_tier1_project_membership_async(
            task, mock_client_with_workspace
        )

        assert result is None
        mock_client_with_workspace.projects.list_async.assert_not_called()


class TestDetectEntityTypeAsyncWithLazyDiscovery:
    """Tests for detect_entity_type_async with lazy discovery integration.

    Per TDD-WORKSPACE-PROJECT-REGISTRY Phase 2:
    - detect_entity_type_async calls async Tier 1 first
    - Pipeline projects detected via dynamic discovery
    """

    @pytest.fixture
    def mock_client_with_workspace(self) -> MagicMock:
        """Create a mock AsanaClient with default_workspace_gid."""
        client = MagicMock()
        client.default_workspace_gid = "workspace_123"
        return client

    def _make_mock_project(self, gid: str, name: str) -> MagicMock:
        """Create a mock Project with gid and name."""
        project = MagicMock()
        project.gid = gid
        project.name = name
        return project

    @pytest.mark.asyncio
    async def test_detect_async_discovers_pipeline_project(
        self,
        clean_registries: None,
        mock_client_with_workspace: MagicMock,
    ) -> None:
        """detect_entity_type_async triggers discovery for pipeline projects."""
        # Mock Sales Pipeline project
        sales_project = self._make_mock_project("sales_pipeline_gid", "Sales Pipeline")

        mock_client_with_workspace.projects.list_async.return_value.collect = AsyncMock(
            return_value=[sales_project]
        )

        task = Task(
            gid="task1",
            name="Demo Call",
            memberships=[{"project": {"gid": "sales_pipeline_gid"}}],
        )

        result = await detect_entity_type_async(task, mock_client_with_workspace)

        # Should detect as PROCESS via async Tier 1
        assert result.entity_type == EntityType.PROCESS
        assert result.tier_used == 1
        assert result.needs_healing is False

    @pytest.mark.asyncio
    async def test_detect_async_static_registry_takes_precedence(
        self,
        clean_registries: None,
        mock_client_with_workspace: MagicMock,
    ) -> None:
        """Static registry entries take precedence over discovery."""
        # Pre-register as BUSINESS in static registry
        registry = get_registry()
        registry.register("preregistered_gid", EntityType.BUSINESS)

        task = Task(
            gid="task1",
            name="Business Task",
            memberships=[{"project": {"gid": "preregistered_gid"}}],
        )

        result = await detect_entity_type_async(task, mock_client_with_workspace)

        # Should return static registration
        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 1

        # No discovery API call
        mock_client_with_workspace.projects.list_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_detect_async_falls_through_to_name_pattern(
        self,
        clean_registries: None,
        mock_client_with_workspace: MagicMock,
    ) -> None:
        """detect_entity_type_async falls through to Tier 2 if not a pipeline project."""
        # Mock non-pipeline project
        other_project = self._make_mock_project("other_gid", "Random Project")

        mock_client_with_workspace.projects.list_async.return_value.collect = AsyncMock(
            return_value=[other_project]
        )

        # Task with holder name pattern
        task = Task(
            gid="task1",
            name="Contacts",  # Will match Tier 2 pattern
            memberships=[{"project": {"gid": "other_gid"}}],
        )

        result = await detect_entity_type_async(task, mock_client_with_workspace)

        # Should fall through to Tier 2 (name pattern)
        assert result.entity_type == EntityType.CONTACT_HOLDER
        assert result.tier_used == 2

    @pytest.mark.asyncio
    async def test_detect_async_idempotent_discovery(
        self,
        clean_registries: None,
        mock_client_with_workspace: MagicMock,
    ) -> None:
        """Discovery only happens once, subsequent calls use cached registry."""
        # Mock Sales Pipeline
        sales_project = self._make_mock_project("sales_gid", "Sales Pipeline")

        mock_client_with_workspace.projects.list_async.return_value.collect = AsyncMock(
            return_value=[sales_project]
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

        # First detection triggers discovery
        result1 = await detect_entity_type_async(task1, mock_client_with_workspace)

        # Second detection uses cached registry (no new discovery)
        result2 = await detect_entity_type_async(task2, mock_client_with_workspace)

        assert result1.entity_type == EntityType.PROCESS
        assert result2.entity_type == EntityType.PROCESS

        # Discovery API called only once
        mock_client_with_workspace.projects.list_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_async_process_type_available_after_discovery(
        self,
        clean_registries: None,
        mock_client_with_workspace: MagicMock,
    ) -> None:
        """WorkspaceProjectRegistry provides ProcessType after discovery."""
        from autom8_asana.models.business.process import ProcessType

        # Mock multiple pipeline types
        sales = self._make_mock_project("sales_gid", "Sales Pipeline")
        onboarding = self._make_mock_project("onboarding_gid", "Onboarding Process")
        retention = self._make_mock_project("retention_gid", "Customer Retention")

        mock_client_with_workspace.projects.list_async.return_value.collect = AsyncMock(
            return_value=[sales, onboarding, retention]
        )

        # Trigger discovery
        task = Task(
            gid="task1",
            name="Test",
            memberships=[{"project": {"gid": "sales_gid"}}],
        )
        await detect_entity_type_async(task, mock_client_with_workspace)

        # Check ProcessType lookup
        workspace_registry = get_workspace_registry()
        assert workspace_registry.get_process_type("sales_gid") == ProcessType.SALES
        assert (
            workspace_registry.get_process_type("onboarding_gid")
            == ProcessType.ONBOARDING
        )
        assert (
            workspace_registry.get_process_type("retention_gid")
            == ProcessType.RETENTION
        )
