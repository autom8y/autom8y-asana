"""Integration tests for WorkspaceProjectRegistry discovery.

Per TDD-TECH-DEBT-REMEDIATION Phase 3 / FR-TEST-002:
Tests registry discovery with mocked API responses.

These tests validate:
- Workspace project discovery via API
- Pipeline project identification and registration
- ProcessType assignment after discovery
- Name-to-GID lookup after discovery
- Idempotent discovery behavior

Hard Constraint: Uses mocks (no live Asana credentials required in CI).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.models.business.detection import EntityType
from autom8_asana.models.business.process import ProcessType
from autom8_asana.models.business.registry import (
    ProjectTypeRegistry,
    WorkspaceProjectRegistry,
    get_registry,
    get_workspace_registry,
)

# --- Fixtures ---


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock AsanaClient with workspace configuration."""
    client = MagicMock()
    client.default_workspace_gid = "workspace_test_123"
    return client


def make_mock_project(gid: str, name: str) -> MagicMock:
    """Create a mock Project with gid and name."""
    project = MagicMock()
    project.gid = gid
    project.name = name
    return project


# --- Test: Basic Discovery ---


@pytest.mark.asyncio
class TestWorkspaceDiscovery:
    """Tests for workspace project discovery."""

    async def test_discover_populates_name_to_gid_mapping(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Discovery populates name-to-GID mapping for all projects."""
        projects = [
            make_mock_project("gid_001", "Project Alpha"),
            make_mock_project("gid_002", "Project Beta"),
            make_mock_project("gid_003", "Project Gamma"),
        ]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects
        )

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_by_name("Project Alpha") == "gid_001"
        assert registry.get_by_name("Project Beta") == "gid_002"
        assert registry.get_by_name("Project Gamma") == "gid_003"

    async def test_discover_is_case_insensitive(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Name lookup is case-insensitive after discovery."""
        projects = [make_mock_project("gid_001", "Sales Pipeline")]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects
        )

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_by_name("sales pipeline") == "gid_001"
        assert registry.get_by_name("SALES PIPELINE") == "gid_001"
        assert registry.get_by_name("Sales Pipeline") == "gid_001"

    async def test_discover_handles_whitespace(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Name lookup handles whitespace in names."""
        projects = [make_mock_project("gid_001", "  Sales Pipeline  ")]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects
        )

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_by_name("sales pipeline") == "gid_001"

    async def test_discover_requires_workspace_gid(
        self,
    ) -> None:
        """Discovery raises ValueError if workspace_gid not set."""
        client = MagicMock()
        client.default_workspace_gid = None

        registry = get_workspace_registry()

        with pytest.raises(ValueError) as exc_info:
            await registry.discover_async(client)

        assert "default_workspace_gid" in str(exc_info.value)

    async def test_discover_sets_discovered_flag(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Discovery sets is_discovered() to True."""
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=[]
        )

        registry = get_workspace_registry()
        assert registry.is_discovered() is False

        await registry.discover_async(mock_client)

        assert registry.is_discovered() is True


# --- Test: Pipeline Project Identification ---


@pytest.mark.asyncio
class TestPipelineProjectIdentification:
    """Tests for pipeline project identification during discovery."""

    @pytest.mark.parametrize(
        ("project_name", "expected_process_type"),
        [
            # Exact matches
            ("Sales", ProcessType.SALES),
            ("Onboarding", ProcessType.ONBOARDING),
            ("Implementation", ProcessType.IMPLEMENTATION),
            ("Retention", ProcessType.RETENTION),
            ("Reactivation", ProcessType.REACTIVATION),
            ("Outreach", ProcessType.OUTREACH),
        ],
    )
    async def test_exact_match_pipeline_names(
        self,
        mock_client: MagicMock,
        project_name: str,
        expected_process_type: ProcessType,
    ) -> None:
        """Exact pipeline names are identified correctly."""
        projects = [make_mock_project("pipeline_gid", project_name)]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects
        )

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_process_type("pipeline_gid") == expected_process_type

    @pytest.mark.parametrize(
        ("project_name", "expected_process_type"),
        [
            # Contains matches
            ("Sales Pipeline", ProcessType.SALES),
            ("Client Onboarding", ProcessType.ONBOARDING),
            ("New Onboarding Process", ProcessType.ONBOARDING),
            ("Implementation Project", ProcessType.IMPLEMENTATION),
            ("Customer Retention", ProcessType.RETENTION),
            ("Reactivation Campaign", ProcessType.REACTIVATION),
            ("Cold Outreach", ProcessType.OUTREACH),
        ],
    )
    async def test_contains_match_pipeline_names(
        self,
        mock_client: MagicMock,
        project_name: str,
        expected_process_type: ProcessType,
    ) -> None:
        """Pipeline names containing keywords are identified correctly."""
        projects = [make_mock_project("pipeline_gid", project_name)]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects
        )

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_process_type("pipeline_gid") == expected_process_type

    async def test_pipeline_projects_registered_as_process(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Pipeline projects are registered as EntityType.PROCESS."""
        projects = [
            make_mock_project("sales_gid", "Sales Pipeline"),
            make_mock_project("onboarding_gid", "Onboarding"),
        ]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects
        )

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        static_registry = get_registry()
        assert static_registry.lookup("sales_gid") == EntityType.PROCESS
        assert static_registry.lookup("onboarding_gid") == EntityType.PROCESS

    async def test_non_pipeline_projects_not_registered(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Non-pipeline projects are not registered in static registry."""
        projects = [
            make_mock_project("sales_gid", "Sales Pipeline"),
            make_mock_project("other_gid", "Random Project"),
            make_mock_project("internal_gid", "Internal Tasks"),
        ]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects
        )

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        static_registry = get_registry()
        assert static_registry.lookup("sales_gid") == EntityType.PROCESS
        assert static_registry.lookup("other_gid") is None
        assert static_registry.lookup("internal_gid") is None

    async def test_exact_match_takes_precedence(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Exact match takes precedence over contains match (two-pass matching)."""
        # Two projects: exact "Onboarding" and contains "Onboarding/Review"
        projects = [
            make_mock_project("review_gid", "Onboarding/Review Calls"),
            make_mock_project("main_gid", "Onboarding"),  # Exact match
        ]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects
        )

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # Exact match project should get ProcessType.ONBOARDING
        assert registry.get_process_type("main_gid") == ProcessType.ONBOARDING
        # Contains match should not get a ProcessType (first match wins per type)
        # Since ONBOARDING was already matched by exact, review won't get it
        assert registry.get_process_type("review_gid") is None


# --- Test: Static Registry Integration ---


@pytest.mark.asyncio
class TestStaticRegistryIntegration:
    """Tests for integration with static ProjectTypeRegistry."""

    async def test_static_registrations_not_overwritten(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Discovery does not overwrite existing static registrations."""
        # Pre-register as BUSINESS
        static_registry = get_registry()
        static_registry.register("preregistered_gid", EntityType.BUSINESS)

        # Discovery finds a pipeline project with same GID (unlikely but tests behavior)
        projects = [make_mock_project("preregistered_gid", "Sales Pipeline")]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects
        )

        workspace_registry = get_workspace_registry()
        await workspace_registry.discover_async(mock_client)

        # Static registration should be preserved
        assert static_registry.lookup("preregistered_gid") == EntityType.BUSINESS

    async def test_sync_lookup_uses_static_registry(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Sync lookup() uses static registry only, no discovery."""
        static_registry = get_registry()
        static_registry.register("static_gid", EntityType.BUSINESS)

        workspace_registry = get_workspace_registry()

        # Sync lookup should work without discovery
        assert workspace_registry.lookup("static_gid") == EntityType.BUSINESS
        assert workspace_registry.lookup("unknown_gid") is None

        # No API call should have been made
        mock_client.projects.list_async.assert_not_called()


# --- Test: Lazy Discovery (lookup_or_discover_async) ---


@pytest.mark.asyncio
class TestLazyDiscovery:
    """Tests for lazy discovery via lookup_or_discover_async."""

    async def test_triggers_discovery_on_first_call(
        self,
        mock_client: MagicMock,
    ) -> None:
        """First call triggers discovery."""
        projects = [make_mock_project("sales_gid", "Sales Pipeline")]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects
        )

        registry = get_workspace_registry()
        assert registry.is_discovered() is False

        result = await registry.lookup_or_discover_async("sales_gid", mock_client)

        assert result == EntityType.PROCESS
        assert registry.is_discovered() is True
        mock_client.projects.list_async.assert_called_once()

    async def test_subsequent_calls_use_cache(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Subsequent calls use cached registry, no additional discovery."""
        projects = [make_mock_project("sales_gid", "Sales Pipeline")]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects
        )

        registry = get_workspace_registry()

        # First call triggers discovery
        await registry.lookup_or_discover_async("sales_gid", mock_client)
        # Second call should use cache
        await registry.lookup_or_discover_async("sales_gid", mock_client)
        # Third call with different GID
        await registry.lookup_or_discover_async("unknown_gid", mock_client)

        # Discovery only called once
        mock_client.projects.list_async.assert_called_once()

    async def test_returns_static_registry_without_discovery(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Returns static registry entry without triggering discovery."""
        static_registry = get_registry()
        static_registry.register("static_gid", EntityType.BUSINESS)

        workspace_registry = get_workspace_registry()
        result = await workspace_registry.lookup_or_discover_async(
            "static_gid", mock_client
        )

        assert result == EntityType.BUSINESS
        # No discovery triggered
        mock_client.projects.list_async.assert_not_called()
        assert workspace_registry.is_discovered() is False

    async def test_returns_none_for_unknown_after_discovery(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Returns None for unknown GID after discovery."""
        projects = [make_mock_project("known_gid", "Known Project")]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects
        )

        registry = get_workspace_registry()
        result = await registry.lookup_or_discover_async("unknown_gid", mock_client)

        assert result is None
        assert registry.is_discovered() is True


# --- Test: ProcessType Lookup ---


@pytest.mark.asyncio
class TestProcessTypeLookup:
    """Tests for ProcessType lookup after discovery."""

    async def test_get_process_type_returns_correct_type(
        self,
        mock_client: MagicMock,
    ) -> None:
        """get_process_type returns correct ProcessType for pipeline projects."""
        projects = [
            make_mock_project("sales_gid", "Sales Pipeline"),
            make_mock_project("onboarding_gid", "Onboarding"),
            make_mock_project("retention_gid", "Customer Retention"),
        ]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects
        )

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_process_type("sales_gid") == ProcessType.SALES
        assert registry.get_process_type("onboarding_gid") == ProcessType.ONBOARDING
        assert registry.get_process_type("retention_gid") == ProcessType.RETENTION

    async def test_get_process_type_returns_none_for_non_pipeline(
        self,
        mock_client: MagicMock,
    ) -> None:
        """get_process_type returns None for non-pipeline projects."""
        projects = [
            make_mock_project("other_gid", "Random Project"),
        ]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects
        )

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_process_type("other_gid") is None
        assert registry.get_process_type("unknown_gid") is None


# --- Test: Registry Reset ---


class TestRegistryReset:
    """Tests for registry reset functionality."""

    def test_reset_clears_workspace_registry(
        self,
    ) -> None:
        """Reset clears workspace registry state."""
        registry = get_workspace_registry()
        # Manually set some state
        registry._name_to_gid["test"] = "gid"
        registry._discovered_workspace = "workspace"

        WorkspaceProjectRegistry.reset()
        new_registry = get_workspace_registry()

        assert new_registry._name_to_gid == {}
        assert new_registry._discovered_workspace is None
        assert new_registry.is_discovered() is False

    def test_reset_clears_static_registry(
        self,
    ) -> None:
        """Reset clears static registry state."""
        static_registry = get_registry()
        static_registry.register("test_gid", EntityType.BUSINESS)

        ProjectTypeRegistry.reset()
        new_registry = get_registry()

        assert new_registry.lookup("test_gid") is None

    def test_registries_are_independent(
        self,
    ) -> None:
        """Resetting one registry doesn't affect the other."""
        static_registry = get_registry()
        static_registry.register("static_gid", EntityType.BUSINESS)

        workspace_registry = get_workspace_registry()
        workspace_registry._name_to_gid["test"] = "gid"

        # Reset only workspace registry
        WorkspaceProjectRegistry.reset()

        # Static registry should be unaffected
        assert get_registry().lookup("static_gid") == EntityType.BUSINESS

        # Workspace registry should be cleared
        assert get_workspace_registry()._name_to_gid == {}


# --- Test: Edge Cases ---


@pytest.mark.asyncio
class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    async def test_empty_workspace_discovery(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Empty workspace discovery completes without error."""
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=[]
        )

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.is_discovered() is True
        assert registry.get_by_name("anything") is None

    async def test_projects_without_name_are_skipped(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Projects without name are skipped during discovery."""
        project_no_name = MagicMock()
        project_no_name.gid = "gid_001"
        project_no_name.name = None

        project_no_gid = MagicMock()
        project_no_gid.gid = None
        project_no_gid.name = "No GID Project"

        valid_project = make_mock_project("valid_gid", "Valid Project")

        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=[project_no_name, project_no_gid, valid_project]
        )

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        # Only valid project should be registered
        assert registry.get_by_name("valid project") == "valid_gid"
        assert registry.get_by_name("no gid project") is None

    async def test_discovery_refresh_clears_previous_state(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Repeated discovery clears and refreshes state."""
        # First discovery
        projects_v1 = [make_mock_project("old_gid", "Old Project")]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects_v1
        )

        registry = get_workspace_registry()
        await registry.discover_async(mock_client)

        assert registry.get_by_name("old project") == "old_gid"

        # Second discovery with different projects
        projects_v2 = [make_mock_project("new_gid", "New Project")]
        mock_client.projects.list_async.return_value.collect = AsyncMock(
            return_value=projects_v2
        )

        await registry.discover_async(mock_client)

        # Old mapping should be cleared, new one should exist
        assert registry.get_by_name("old project") is None
        assert registry.get_by_name("new project") == "new_gid"
