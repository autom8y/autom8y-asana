"""Unit tests for WorkspaceProjectRegistry.

Per TDD-WORKSPACE-PROJECT-REGISTRY Phase 1: Tests for registry operations.
Per ADR-0108: Composition with ProjectTypeRegistry, module-level singleton.
Per ADR-0109: Lazy discovery on first unregistered GID.

Test cases:
1. Singleton behavior
2. discover_async() - discovery, name mapping, pipeline identification
3. lookup_or_discover_async() - lazy discovery triggering
4. get_by_name() - O(1) name resolution
5. get_process_type() - ProcessType derivation
6. Edge cases - empty workspace, no pipeline projects, duplicates
7. Reset for test isolation
8. Idempotent discovery (refresh)
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from autom8_asana.models.business.detection import EntityType
from autom8_asana.models.business.process import ProcessType
from autom8_asana.models.business.registry import (
    ProjectTypeRegistry,
    WorkspaceProjectRegistry,
    get_registry,
    get_workspace_registry,
)


# --- Test Fixtures ---


@dataclass
class MockProject:
    """Mock Project object for testing."""

    gid: str
    name: str


def create_mock_client(
    workspace_gid: str | None = "workspace_123",
    projects: list[MockProject] | None = None,
) -> MagicMock:
    """Create a mock AsanaClient for testing.

    Args:
        workspace_gid: Default workspace GID.
        projects: List of mock projects to return from list_async.

    Returns:
        Mock AsanaClient instance.
    """
    if projects is None:
        projects = []

    mock_client = MagicMock()
    mock_client.default_workspace_gid = workspace_gid

    # Mock PageIterator with collect() method
    async def mock_collect() -> list[MockProject]:
        return projects

    mock_iterator = MagicMock()
    mock_iterator.collect = mock_collect

    mock_client.projects.list_async.return_value = mock_iterator

    return mock_client


# --- Singleton Tests ---


class TestWorkspaceProjectRegistrySingleton:
    """Tests for singleton behavior."""

    def test_singleton_returns_same_instance(self) -> None:
        """Verify singleton pattern - same instance returned."""
        registry1 = get_workspace_registry()
        registry2 = get_workspace_registry()

        assert registry1 is registry2

    def test_singleton_via_class_instantiation(self) -> None:
        """Verify singleton via direct class instantiation."""
        registry1 = WorkspaceProjectRegistry()
        registry2 = WorkspaceProjectRegistry()

        assert registry1 is registry2

    def test_reset_creates_new_instance(self) -> None:
        """Verify reset() creates a new singleton instance."""
        registry1 = get_workspace_registry()
        registry1._name_to_gid["test"] = "test_gid"

        WorkspaceProjectRegistry.reset()

        registry2 = get_workspace_registry()
        assert registry1 is not registry2
        assert "test" not in registry2._name_to_gid


# --- Discovery Tests ---


class TestDiscoverAsync:
    """Tests for discover_async() method."""

    @pytest.mark.asyncio
    async def test_discover_populates_name_to_gid(self) -> None:
        """discover_async() populates name-to-GID mapping."""
        projects = [
            MockProject(gid="gid_123", name="Sales Pipeline"),
            MockProject(gid="gid_456", name="Onboarding Process"),
            MockProject(gid="gid_789", name="Internal Docs"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_by_name("Sales Pipeline") == "gid_123"
        assert registry.get_by_name("Onboarding Process") == "gid_456"
        assert registry.get_by_name("Internal Docs") == "gid_789"

    @pytest.mark.asyncio
    async def test_discover_identifies_pipeline_projects(
        self,
    ) -> None:
        """discover_async() identifies pipeline projects by ProcessType."""
        projects = [
            MockProject(gid="sales_gid", name="Sales Pipeline"),
            MockProject(gid="onboard_gid", name="Client Onboarding"),
            MockProject(gid="retention_gid", name="Retention Tracking"),
            MockProject(gid="docs_gid", name="Documentation"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # Pipeline projects should have ProcessType
        assert registry.get_process_type("sales_gid") == ProcessType.SALES
        assert registry.get_process_type("onboard_gid") == ProcessType.ONBOARDING
        assert registry.get_process_type("retention_gid") == ProcessType.RETENTION

        # Non-pipeline projects should return None
        assert registry.get_process_type("docs_gid") is None

    @pytest.mark.asyncio
    async def test_discover_registers_pipeline_as_process_entity(
        self,
    ) -> None:
        """discover_async() registers pipeline projects as EntityType.PROCESS."""
        projects = [
            MockProject(gid="sales_gid", name="Sales Pipeline"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # Should be registered with static registry
        type_registry = get_registry()
        assert type_registry.lookup("sales_gid") == EntityType.PROCESS

    @pytest.mark.asyncio
    async def test_discover_requires_workspace_gid(
        self,
    ) -> None:
        """discover_async() raises ValueError if no workspace_gid."""
        mock_client = create_mock_client(workspace_gid=None)

        registry = get_workspace_registry()

        with pytest.raises(ValueError) as exc_info:
            await registry.discover_async(mock_client)

        assert "default_workspace_gid is not set" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_discover_marks_discovered(self) -> None:
        """discover_async() marks registry as discovered."""
        mock_client = create_mock_client(projects=[])

        registry = get_workspace_registry()
        assert not registry.is_discovered()

        await registry.discover_async(mock_client)

        assert registry.is_discovered()

    @pytest.mark.asyncio
    async def test_discover_idempotent_refresh(self) -> None:
        """Repeated discover_async() calls refresh the registry."""
        projects_v1 = [MockProject(gid="gid_1", name="Project One")]
        projects_v2 = [
            MockProject(gid="gid_1", name="Project One"),
            MockProject(gid="gid_2", name="Project Two"),
        ]

        # First discovery
        mock_client_v1 = create_mock_client(projects=projects_v1)
        registry = get_workspace_registry()
        await registry.discover_async(mock_client_v1)

        assert registry.get_by_name("Project One") == "gid_1"
        assert registry.get_by_name("Project Two") is None

        # Second discovery (refresh)
        mock_client_v2 = create_mock_client(projects=projects_v2)
        await registry.discover_async(mock_client_v2)

        assert registry.get_by_name("Project One") == "gid_1"
        assert registry.get_by_name("Project Two") == "gid_2"

    @pytest.mark.asyncio
    async def test_discover_does_not_overwrite_static_registration(
        self,
    ) -> None:
        """discover_async() does not overwrite static PRIMARY_PROJECT_GID."""
        # Pre-register a GID as BUSINESS (simulating static registration)
        type_registry = get_registry()
        type_registry.register("business_gid", EntityType.BUSINESS)

        # Now discover a project with same GID that would match SALES
        projects = [
            MockProject(gid="business_gid", name="Sales Team"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # Should still be BUSINESS, not overwritten to PROCESS
        assert type_registry.lookup("business_gid") == EntityType.BUSINESS


# --- Lookup or Discover Tests ---


class TestLookupOrDiscoverAsync:
    """Tests for lookup_or_discover_async() method."""

    @pytest.mark.asyncio
    async def test_returns_static_registration_without_discovery(
        self,
    ) -> None:
        """lookup_or_discover_async() returns static type without triggering discovery."""
        # Pre-register a GID
        type_registry = get_registry()
        type_registry.register("static_gid", EntityType.CONTACT)

        mock_client = create_mock_client()
        registry = get_workspace_registry()

        result = await registry.lookup_or_discover_async("static_gid", mock_client)

        assert result == EntityType.CONTACT
        # Discovery should NOT have been triggered
        assert not registry.is_discovered()
        mock_client.projects.list_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_triggers_discovery_on_unknown_gid(
        self,
    ) -> None:
        """lookup_or_discover_async() triggers discovery on unknown GID."""
        projects = [
            MockProject(gid="sales_gid", name="Sales Pipeline"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        assert not registry.is_discovered()

        result = await registry.lookup_or_discover_async("sales_gid", mock_client)

        assert registry.is_discovered()
        assert result == EntityType.PROCESS

    @pytest.mark.asyncio
    async def test_returns_none_for_truly_unknown_after_discovery(
        self,
    ) -> None:
        """lookup_or_discover_async() returns None for unknown GID after discovery."""
        projects = [MockProject(gid="known_gid", name="Known Project")]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()

        # First call triggers discovery
        await registry.lookup_or_discover_async("unknown_gid", mock_client)

        # Second call should not re-discover (already discovered)
        mock_client.projects.list_async.reset_mock()
        result = await registry.lookup_or_discover_async("another_unknown", mock_client)

        assert result is None
        mock_client.projects.list_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_discovery_only_once(self) -> None:
        """lookup_or_discover_async() only triggers discovery once."""
        projects = [MockProject(gid="gid_1", name="Project")]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()

        # Multiple lookups for unknown GIDs
        await registry.lookup_or_discover_async("unknown_1", mock_client)
        await registry.lookup_or_discover_async("unknown_2", mock_client)
        await registry.lookup_or_discover_async("unknown_3", mock_client)

        # Discovery should only happen once
        assert mock_client.projects.list_async.call_count == 1


# --- Name Resolution Tests ---


class TestGetByName:
    """Tests for get_by_name() method."""

    @pytest.mark.asyncio
    async def test_case_insensitive_lookup(self) -> None:
        """get_by_name() is case-insensitive."""
        projects = [MockProject(gid="gid_123", name="Sales Pipeline")]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_by_name("Sales Pipeline") == "gid_123"
        assert registry.get_by_name("sales pipeline") == "gid_123"
        assert registry.get_by_name("SALES PIPELINE") == "gid_123"
        assert registry.get_by_name("SaLeS PiPeLiNe") == "gid_123"

    @pytest.mark.asyncio
    async def test_whitespace_normalized(self) -> None:
        """get_by_name() normalizes whitespace."""
        projects = [MockProject(gid="gid_123", name="Sales Pipeline")]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_by_name("  Sales Pipeline  ") == "gid_123"
        assert registry.get_by_name("Sales Pipeline") == "gid_123"

    def test_returns_none_before_discovery(self) -> None:
        """get_by_name() returns None before discovery."""
        registry = get_workspace_registry()

        assert registry.get_by_name("Any Project") is None

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_name(self) -> None:
        """get_by_name() returns None for unknown project name."""
        projects = [MockProject(gid="gid_123", name="Known Project")]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_by_name("Unknown Project") is None


# --- ProcessType Tests ---


class TestGetProcessType:
    """Tests for get_process_type() method."""

    @pytest.mark.asyncio
    async def test_returns_correct_process_type(self) -> None:
        """get_process_type() returns correct ProcessType for pipeline projects."""
        projects = [
            MockProject(gid="sales_gid", name="Sales Pipeline"),
            MockProject(gid="outreach_gid", name="Outreach Campaigns"),
            MockProject(gid="onboard_gid", name="Client Onboarding"),
            MockProject(gid="impl_gid", name="Implementation Queue"),
            MockProject(gid="retention_gid", name="Retention Tracking"),
            MockProject(gid="react_gid", name="Reactivation Pipeline"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_process_type("sales_gid") == ProcessType.SALES
        assert registry.get_process_type("outreach_gid") == ProcessType.OUTREACH
        assert registry.get_process_type("onboard_gid") == ProcessType.ONBOARDING
        assert registry.get_process_type("impl_gid") == ProcessType.IMPLEMENTATION
        assert registry.get_process_type("retention_gid") == ProcessType.RETENTION
        assert registry.get_process_type("react_gid") == ProcessType.REACTIVATION

    def test_returns_none_for_unknown_gid(self) -> None:
        """get_process_type() returns None for unknown GID."""
        registry = get_workspace_registry()

        assert registry.get_process_type("unknown_gid") is None

    @pytest.mark.asyncio
    async def test_returns_none_for_non_pipeline(self) -> None:
        """get_process_type() returns None for non-pipeline projects."""
        projects = [MockProject(gid="docs_gid", name="Documentation")]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_process_type("docs_gid") is None


# --- ProcessType Matching Tests ---


class TestProcessTypeMatching:
    """Tests for ProcessType matching logic."""

    @pytest.mark.asyncio
    async def test_first_match_wins(self) -> None:
        """First ProcessType match wins when multiple could match."""
        # "Sales Outreach" contains both "sales" and "outreach"
        # SALES should win because it's checked first
        projects = [
            MockProject(gid="combo_gid", name="Sales Outreach Campaign"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_process_type("combo_gid") == ProcessType.SALES

    @pytest.mark.asyncio
    async def test_generic_is_never_matched(self) -> None:
        """GENERIC ProcessType is never matched from project names."""
        # Even if "generic" appears in the name, it shouldn't match
        projects = [
            MockProject(gid="gen_gid", name="Generic Project"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_process_type("gen_gid") is None

    @pytest.mark.asyncio
    async def test_contains_match_variations(self) -> None:
        """Contains matching handles various name patterns.

        Each name pattern is tested in isolation to verify it can match.
        Only one project per ProcessType gets the ProcessType assigned.
        """
        # Test each variation in isolation
        test_cases = [
            ("Sales", ProcessType.SALES),  # Exact
            ("ActiveSales", ProcessType.SALES),  # No space
            ("sales-pipeline", ProcessType.SALES),  # Hyphenated
            ("My Sales Project", ProcessType.SALES),  # Middle
            ("ONBOARDING", ProcessType.ONBOARDING),  # Uppercase exact
        ]

        for name, expected_type in test_cases:
            # Reset for clean test
            WorkspaceProjectRegistry.reset()
            ProjectTypeRegistry.reset()

            projects = [MockProject(gid="test_gid", name=name)]
            mock_client = create_mock_client(projects=projects)

            registry = get_workspace_registry()
            await registry.discover_async(mock_client)

            assert registry.get_process_type("test_gid") == expected_type, (
                f"Expected {name!r} to match {expected_type}"
            )

    @pytest.mark.asyncio
    async def test_only_one_project_per_process_type(
        self,
    ) -> None:
        """Only one project gets assigned per ProcessType.

        When multiple projects could match the same ProcessType,
        only the first match (exact > contains) wins.
        """
        projects = [
            MockProject(gid="gid_1", name="Sales"),  # Exact - wins
            MockProject(gid="gid_2", name="ActiveSales"),  # Contains - loses
            MockProject(gid="gid_3", name="sales-pipeline"),  # Contains - loses
            MockProject(gid="gid_4", name="My Sales Project"),  # Contains - loses
            MockProject(gid="gid_5", name="ONBOARDING"),  # Exact - wins
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # Exact matches win
        assert registry.get_process_type("gid_1") == ProcessType.SALES
        assert registry.get_process_type("gid_5") == ProcessType.ONBOARDING
        # Other projects don't get ProcessType (already claimed)
        assert registry.get_process_type("gid_2") is None
        assert registry.get_process_type("gid_3") is None
        assert registry.get_process_type("gid_4") is None


# --- Sync Lookup Tests ---


class TestSyncLookup:
    """Tests for sync lookup() method."""

    def test_lookup_delegates_to_type_registry(self) -> None:
        """lookup() delegates to ProjectTypeRegistry."""
        type_registry = get_registry()
        type_registry.register("static_gid", EntityType.BUSINESS)

        workspace_registry = get_workspace_registry()

        assert workspace_registry.lookup("static_gid") == EntityType.BUSINESS
        assert workspace_registry.lookup("unknown_gid") is None

    @pytest.mark.asyncio
    async def test_lookup_includes_discovered_pipeline_projects(
        self,
    ) -> None:
        """lookup() returns pipeline projects after discovery."""
        projects = [MockProject(gid="sales_gid", name="Sales Pipeline")]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # Sync lookup should find discovered pipeline project
        assert registry.lookup("sales_gid") == EntityType.PROCESS


# --- Edge Case Tests ---


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_workspace(self) -> None:
        """Discovery handles empty workspace (no projects)."""
        mock_client = create_mock_client(projects=[])

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.is_discovered()
        assert len(registry._name_to_gid) == 0
        assert len(registry._gid_to_process_type) == 0

    @pytest.mark.asyncio
    async def test_no_pipeline_projects(self) -> None:
        """Discovery handles workspace with no pipeline projects."""
        projects = [
            MockProject(gid="gid_1", name="Documentation"),
            MockProject(gid="gid_2", name="Archive"),
            MockProject(gid="gid_3", name="Planning"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.is_discovered()
        assert len(registry._name_to_gid) == 3
        assert len(registry._gid_to_process_type) == 0

    @pytest.mark.asyncio
    async def test_project_without_name_skipped(self) -> None:
        """Projects without name are skipped."""
        projects = [
            MockProject(gid="gid_1", name="Valid Project"),
            MockProject(gid="gid_2", name=""),  # Empty name
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_by_name("Valid Project") == "gid_1"
        assert len(registry._name_to_gid) == 1

    @pytest.mark.asyncio
    async def test_project_without_gid_skipped(self) -> None:
        """Projects without GID are skipped."""
        projects = [
            MockProject(gid="gid_1", name="Valid Project"),
            MockProject(gid="", name="No GID Project"),  # Empty GID
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_by_name("Valid Project") == "gid_1"
        assert registry.get_by_name("No GID Project") is None


# --- Composition Tests ---


class TestCompositionWithProjectTypeRegistry:
    """Tests for composition with ProjectTypeRegistry."""

    def test_composes_with_project_type_registry(self) -> None:
        """WorkspaceProjectRegistry composes with ProjectTypeRegistry."""
        workspace_registry = get_workspace_registry()

        assert isinstance(workspace_registry._type_registry, ProjectTypeRegistry)
        assert workspace_registry._type_registry is get_registry()

    @pytest.mark.asyncio
    async def test_static_takes_precedence(self) -> None:
        """Static registrations take precedence over dynamic discovery."""
        # Pre-register statically
        type_registry = get_registry()
        type_registry.register("priority_gid", EntityType.UNIT)

        # Discover a project that would match SALES
        projects = [MockProject(gid="priority_gid", name="Sales-ish")]
        mock_client = create_mock_client(projects=projects)

        workspace_registry = get_workspace_registry()
        await workspace_registry.discover_async(mock_client)

        # lookup_or_discover should return UNIT (static), not PROCESS
        result = await workspace_registry.lookup_or_discover_async(
            "priority_gid", mock_client
        )
        assert result == EntityType.UNIT


# --- Reset Tests ---


class TestReset:
    """Tests for registry reset functionality."""

    @pytest.mark.asyncio
    async def test_reset_clears_all_state(self) -> None:
        """reset() clears all discovered state."""
        projects = [MockProject(gid="gid_1", name="Sales Pipeline")]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.is_discovered()
        assert registry.get_by_name("Sales Pipeline") is not None

        WorkspaceProjectRegistry.reset()

        new_registry = get_workspace_registry()
        assert not new_registry.is_discovered()
        assert new_registry.get_by_name("Sales Pipeline") is None


# --- O(1) Lookup Tests ---


class TestO1Lookup:
    """Tests verifying O(1) lookup performance requirements."""

    @pytest.mark.asyncio
    async def test_name_lookup_is_dict_based(self) -> None:
        """Verify name lookup uses dict (O(1) by design)."""
        projects = [
            MockProject(gid=f"gid_{i}", name=f"Project {i}") for i in range(100)
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # Verify underlying data structure is dict
        assert isinstance(registry._name_to_gid, dict)
        assert len(registry._name_to_gid) == 100

    @pytest.mark.asyncio
    async def test_process_type_lookup_is_dict_based(
        self,
    ) -> None:
        """Verify process type lookup uses dict (O(1) by design)."""
        projects = [
            MockProject(gid="gid_1", name="Sales A"),
            MockProject(gid="gid_2", name="Sales B"),
            MockProject(gid="gid_3", name="Onboarding X"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # Verify underlying data structure is dict
        assert isinstance(registry._gid_to_process_type, dict)


# --- Exact Match Precedence Tests ---


class TestExactMatchPrecedence:
    """Tests for exact-match precedence in ProcessType identification.

    Per bug fix: When multiple projects could match a ProcessType,
    exact matches (name.lower() == process_type.value) should win
    over contains matches.

    Example: "Onboarding" should match ProcessType.ONBOARDING before
    "Onboarding/Review Calls" can claim it via contains matching.
    """

    @pytest.mark.asyncio
    async def test_exact_match_wins_over_contains_match(
        self,
    ) -> None:
        """Exact match takes precedence over contains match.

        This is the primary bug scenario: "Onboarding" vs "Onboarding/Review Calls".
        """
        projects = [
            # Contains match appears first in list
            MockProject(gid="review_calls_gid", name="Onboarding/Review Calls"),
            # Exact match appears second
            MockProject(gid="onboarding_gid", name="Onboarding"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # The exact match "Onboarding" should win ProcessType.ONBOARDING
        assert registry.get_process_type("onboarding_gid") == ProcessType.ONBOARDING
        # The contains match should NOT have ProcessType (already claimed)
        assert registry.get_process_type("review_calls_gid") is None

    @pytest.mark.asyncio
    async def test_exact_match_case_insensitive(self) -> None:
        """Exact match is case-insensitive."""
        projects = [
            MockProject(gid="sales_gid", name="SALES"),
            MockProject(gid="sales_pipeline_gid", name="Sales Pipeline"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # "SALES" (case-insensitive) exact matches ProcessType.SALES
        assert registry.get_process_type("sales_gid") == ProcessType.SALES
        # "Sales Pipeline" should not get ProcessType (already claimed)
        assert registry.get_process_type("sales_pipeline_gid") is None

    @pytest.mark.asyncio
    async def test_contains_match_used_when_no_exact_match(
        self,
    ) -> None:
        """Contains match is used when no exact match exists."""
        projects = [
            # No exact "sales" project exists, only contains match
            MockProject(gid="sales_pipeline_gid", name="Sales Pipeline"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # Should match via contains since no exact match
        assert registry.get_process_type("sales_pipeline_gid") == ProcessType.SALES

    @pytest.mark.asyncio
    async def test_multiple_process_types_exact_wins_each(
        self,
    ) -> None:
        """Each ProcessType prefers its exact match over contains matches."""
        projects = [
            # Contains matches appear first
            MockProject(gid="sales_team_gid", name="Sales Team"),
            MockProject(gid="onboarding_calls_gid", name="Onboarding Calls"),
            # Exact matches appear second
            MockProject(gid="sales_gid", name="Sales"),
            MockProject(gid="onboarding_gid", name="Onboarding"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # Exact matches win
        assert registry.get_process_type("sales_gid") == ProcessType.SALES
        assert registry.get_process_type("onboarding_gid") == ProcessType.ONBOARDING
        # Contains matches don't get ProcessType (already claimed)
        assert registry.get_process_type("sales_team_gid") is None
        assert registry.get_process_type("onboarding_calls_gid") is None

    @pytest.mark.asyncio
    async def test_exact_match_with_whitespace_trim(
        self,
    ) -> None:
        """Exact match handles whitespace (trimmed for comparison)."""
        projects = [
            MockProject(gid="onboard_ws_gid", name="  Onboarding  "),  # Has whitespace
            MockProject(gid="onboard_slash_gid", name="Onboarding/Other"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # "  Onboarding  " should exact-match after strip()
        assert registry.get_process_type("onboard_ws_gid") == ProcessType.ONBOARDING
        assert registry.get_process_type("onboard_slash_gid") is None

    @pytest.mark.asyncio
    async def test_all_process_types_have_exact_match_priority(
        self,
    ) -> None:
        """All pipeline ProcessTypes support exact-match precedence."""
        projects = [
            # Contains matches first in list
            MockProject(gid="sales_ext_gid", name="Sales Extended"),
            MockProject(gid="outreach_ext_gid", name="Outreach Extended"),
            MockProject(gid="onboard_ext_gid", name="Onboarding Extended"),
            MockProject(gid="impl_ext_gid", name="Implementation Extended"),
            MockProject(gid="ret_ext_gid", name="Retention Extended"),
            MockProject(gid="react_ext_gid", name="Reactivation Extended"),
            # Exact matches second in list
            MockProject(gid="sales_gid", name="Sales"),
            MockProject(gid="outreach_gid", name="Outreach"),
            MockProject(gid="onboard_gid", name="Onboarding"),
            MockProject(gid="impl_gid", name="Implementation"),
            MockProject(gid="ret_gid", name="Retention"),
            MockProject(gid="react_gid", name="Reactivation"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # All exact matches should win
        assert registry.get_process_type("sales_gid") == ProcessType.SALES
        assert registry.get_process_type("outreach_gid") == ProcessType.OUTREACH
        assert registry.get_process_type("onboard_gid") == ProcessType.ONBOARDING
        assert registry.get_process_type("impl_gid") == ProcessType.IMPLEMENTATION
        assert registry.get_process_type("ret_gid") == ProcessType.RETENTION
        assert registry.get_process_type("react_gid") == ProcessType.REACTIVATION

        # All contains matches should NOT have ProcessType
        assert registry.get_process_type("sales_ext_gid") is None
        assert registry.get_process_type("outreach_ext_gid") is None
        assert registry.get_process_type("onboard_ext_gid") is None
        assert registry.get_process_type("impl_ext_gid") is None
        assert registry.get_process_type("ret_ext_gid") is None
        assert registry.get_process_type("react_ext_gid") is None

    @pytest.mark.asyncio
    async def test_mixed_exact_and_contains_matches(
        self,
    ) -> None:
        """Mix of exact matches and fallback to contains matches."""
        projects = [
            # Sales has exact match
            MockProject(gid="sales_gid", name="Sales"),
            # Onboarding has only contains match
            MockProject(gid="onboard_process_gid", name="Onboarding Process"),
            # Retention has exact match
            MockProject(gid="retention_gid", name="Retention"),
        ]
        mock_client = create_mock_client(projects=projects)

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # Exact matches
        assert registry.get_process_type("sales_gid") == ProcessType.SALES
        assert registry.get_process_type("retention_gid") == ProcessType.RETENTION
        # Contains match (no exact match for ONBOARDING)
        assert (
            registry.get_process_type("onboard_process_gid") == ProcessType.ONBOARDING
        )
