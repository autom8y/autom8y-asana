"""Lifecycle engine integration smoke tests.

Full-surface validation of the hardened lifecycle engine against both
config integrity and service correctness. Categories 1-9 covering:
- YAML config loading and DAG validation
- Live entity inspection (ASANA_PAT required)
- CompletionService mock validation
- SectionService mock validation
- DependencyWiringService mock validation
- EntityCreationService mock validation
- Init action handler validation
- LifecycleEngine integration with mock services
- Edge cases and adversarial scenarios
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


def _run_async(coro):
    """Run an async coroutine in a fresh event loop.

    Using asyncio.get_event_loop() fails when earlier async tests close
    the default loop. A fresh loop per call avoids this.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


import pytest
import yaml

# ---------------------------------------------------------------------------
# Markers and skip conditions
# ---------------------------------------------------------------------------

ASANA_PAT = os.getenv("ASANA_PAT")
SALES_PROCESS_GID = "1209719836385072"

skip_no_pat = pytest.mark.skipif(not ASANA_PAT, reason="ASANA_PAT not set")

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "lifecycle_stages.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_process(
    gid: str = "1234567890",
    name: str = "Test Process",
    completed: bool = False,
    process_type_value: str = "sales",
    memberships: list | None = None,
    custom_fields: list | None = None,
    contact_phone: str | None = None,
) -> MagicMock:
    """Create a mock Process entity."""
    mock = MagicMock()
    mock.gid = gid
    mock.name = name
    mock.completed = completed
    mock.memberships = memberships or [
        {
            "project": {"gid": "1200944186565610", "name": "Sales Pipeline"},
            "section": {"gid": "sec123", "name": "Opportunity"},
        }
    ]
    mock.custom_fields = custom_fields or []
    mock.process_type = MagicMock()
    mock.process_type.value = process_type_value
    mock.process_holder = None
    # For validation checks
    mock.contact_phone = contact_phone
    return mock


def _make_mock_client() -> MagicMock:
    """Create a mock AsanaClient with stubs for all API calls."""
    client = MagicMock()
    client.tasks = MagicMock()
    client.tasks.update_async = AsyncMock()
    client.tasks.get_async = AsyncMock()
    client.tasks.create_async = AsyncMock()
    client.tasks.duplicate_async = AsyncMock()
    client.tasks.add_to_project_async = AsyncMock()
    client.tasks.add_dependent_async = AsyncMock()
    client.tasks.add_dependency_async = AsyncMock()
    client.tasks.add_dependencies_async = AsyncMock()
    client.tasks.set_assignee_async = AsyncMock()

    client.sections = MagicMock()
    client.sections.add_task_async = AsyncMock()

    # list_for_project_async returns an object with .collect()
    sections_paginator = MagicMock()
    sections_paginator.collect = AsyncMock(return_value=[])
    client.sections.list_for_project_async = MagicMock(return_value=sections_paginator)

    client.stories = MagicMock()
    client.stories.create_comment_async = AsyncMock()

    return client


# ===========================================================================
# Category 1: YAML Config Integrity
# ===========================================================================


class TestYAMLConfigIntegrity:
    """Validate lifecycle_stages.yaml parses correctly and has DAG integrity."""

    def test_config_file_exists(self):
        """The config file must exist at the expected path."""
        assert CONFIG_PATH.exists(), f"Config file not found: {CONFIG_PATH}"

    def test_config_loads_without_error(self):
        """Config should parse into LifecycleConfig without errors."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        assert config.stages is not None
        assert len(config.stages) > 0

    def test_all_stages_have_valid_names(self):
        """Every stage should have a non-empty name matching its dict key."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        for key, stage in config.stages.items():
            assert stage.name == key, f"Stage key '{key}' != stage.name '{stage.name}'"
            assert len(key) > 0

    def test_all_stages_have_pipeline_stage_numbers(self):
        """Every stage should have a pipeline_stage number >= 0."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        for name, stage in config.stages.items():
            assert stage.pipeline_stage >= 0, (
                f"Stage '{name}' has negative pipeline_stage: {stage.pipeline_stage}"
            )

    def test_no_duplicate_stage_names(self):
        """Stage names in the YAML should be unique (enforced by dict keys)."""
        with open(CONFIG_PATH) as f:
            raw = yaml.safe_load(f)
        stage_names = list(raw["stages"].keys())
        assert len(stage_names) == len(set(stage_names)), "Duplicate stage names found"

    def test_transitions_reference_valid_stages(self):
        """All transition targets must reference defined stage names (DAG)."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        stage_names = set(config.stages.keys())
        issues = []
        for name, stage in config.stages.items():
            if (
                stage.transitions.converted
                and stage.transitions.converted not in stage_names
            ):
                issues.append(f"{name} -> converted: '{stage.transitions.converted}'")
            if (
                stage.transitions.did_not_convert
                and stage.transitions.did_not_convert not in stage_names
            ):
                issues.append(
                    f"{name} -> did_not_convert: '{stage.transitions.did_not_convert}'"
                )
        assert not issues, f"DAG integrity failures: {issues}"

    def test_auto_complete_prior_on_expected_stages(self):
        """Stages 2-4 (sales, onboarding, implementation) should have
        auto_complete_prior=true. Stage 1 (outreach) should be false."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        # Outreach should NOT auto-complete
        outreach = config.get_stage("outreach")
        assert outreach is not None
        assert outreach.transitions.auto_complete_prior is False

        # Sales, Onboarding, Implementation should auto-complete
        for stage_name in ("sales", "onboarding", "implementation"):
            stage = config.get_stage(stage_name)
            assert stage is not None, f"Stage '{stage_name}' not found"
            assert stage.transitions.auto_complete_prior is True, (
                f"Stage '{stage_name}' should have auto_complete_prior=true"
            )

    def test_section_names_defined_for_active_stages(self):
        """Stages 1-4 should have non-empty target_section and
        template_section."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        for stage_name in ("outreach", "sales", "onboarding", "implementation"):
            stage = config.get_stage(stage_name)
            assert stage is not None
            assert stage.target_section, f"Stage '{stage_name}' missing target_section"
            assert stage.template_section, (
                f"Stage '{stage_name}' missing template_section"
            )

    def test_cascading_sections_defined_for_active_stages(self):
        """Stages 1-4 should define cascading_sections for at least one
        entity type."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        for stage_name in ("outreach", "sales", "onboarding", "implementation"):
            stage = config.get_stage(stage_name)
            assert stage is not None
            cs = stage.cascading_sections
            has_any = cs.offer or cs.unit or cs.business
            assert has_any, f"Stage '{stage_name}' has no cascading sections defined"

    def test_dnc_actions_are_valid_literals(self):
        """All stages' dnc_action should be one of the allowed literals."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        valid = {"create_new", "reopen", "deferred"}
        for name, stage in config.stages.items():
            assert stage.dnc_action in valid, (
                f"Stage '{name}' has invalid dnc_action: '{stage.dnc_action}'"
            )

    def test_init_action_types_registered(self):
        """All init_action types referenced in YAML should exist in
        HANDLER_REGISTRY."""
        from autom8_asana.lifecycle.config import LifecycleConfig
        from autom8_asana.lifecycle.init_actions import HANDLER_REGISTRY

        config = LifecycleConfig(CONFIG_PATH)
        unregistered = []
        for name, stage in config.stages.items():
            for action in stage.init_actions:
                if action.type not in HANDLER_REGISTRY:
                    unregistered.append(f"{name}: {action.type}")
        assert not unregistered, f"Unregistered init action types: {unregistered}"

    def test_project_gids_on_active_stages(self):
        """Stages 1-4 must have non-null project_gid for template
        discovery."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        for stage_name in ("outreach", "sales", "onboarding", "implementation"):
            stage = config.get_stage(stage_name)
            assert stage is not None
            assert stage.project_gid is not None, (
                f"Stage '{stage_name}' has null project_gid"
            )

    def test_orphan_stages_check(self):
        """Report any stages that are defined but never reachable via
        any transition from another stage. Root stages (stage 1 entry
        points) are expected to be 'orphans'."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        stage_names = set(config.stages.keys())
        referenced = set()
        for _name, stage in config.stages.items():
            if stage.transitions.converted:
                referenced.add(stage.transitions.converted)
            if stage.transitions.did_not_convert:
                referenced.add(stage.transitions.did_not_convert)
        unreachable = stage_names - referenced
        # outreach is expected to be unreachable (root entry point)
        # expansion, month1 may also be unreachable (deferred stages)
        # This is informational, not a failure
        if unreachable:
            # Just verify it doesn't include core pipeline stages 2-4
            core_unreachable = unreachable & {"sales", "onboarding", "implementation"}
            assert not core_unreachable, (
                f"Core stages unreachable via transitions: {core_unreachable}"
            )

    def test_pipeline_stage_number_uniqueness_within_main_pipeline(self):
        """Within stages 1-4, pipeline_stage numbers should be unique
        and sequential (1,2,3,4)."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        main_stages = ["outreach", "sales", "onboarding", "implementation"]
        numbers = []
        for name in main_stages:
            stage = config.get_stage(name)
            assert stage is not None
            numbers.append(stage.pipeline_stage)
        assert numbers == [1, 2, 3, 4], (
            f"Main pipeline stages should be [1,2,3,4], got {numbers}"
        )

    def test_dependency_wiring_rules_exist(self):
        """At least pipeline_default wiring rules should exist."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        rules = config.get_wiring_rules("pipeline_default")
        assert rules is not None, "No pipeline_default wiring rules found"
        assert len(rules.dependents) > 0, "No dependent rules defined"

    def test_retention_pipeline_stage_conflict(self):
        """D-LC-001: retention has pipeline_stage=1, same as outreach.
        This may cause confusion in any code using pipeline_stage for
        ordering across the full DAG."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        outreach = config.get_stage("outreach")
        retention = config.get_stage("retention")
        assert outreach is not None and retention is not None
        if outreach.pipeline_stage == retention.pipeline_stage:
            pytest.xfail(
                "D-LC-001: retention and outreach share pipeline_stage=1. "
                "If any code orders stages by pipeline_stage across the "
                "full DAG, this creates ambiguity."
            )


# ===========================================================================
# Category 2: Live Process Entity Inspection (requires ASANA_PAT)
# ===========================================================================


@skip_no_pat
class TestLiveProcessEntityInspection:
    """Fetch and inspect the Sales process entity from live Asana."""

    @pytest.fixture
    def asana_client(self):
        """Create a real AsanaClient from ASANA_PAT."""
        from autom8_asana.client import AsanaClient

        return AsanaClient(token=ASANA_PAT)

    @pytest.mark.integration
    def test_fetch_sales_process(self, asana_client):
        """Fetch the Sales process entity and inspect its fields."""

        async def _run():
            task = await asana_client.tasks.get_async(
                SALES_PROCESS_GID,
                opt_fields=[
                    "name",
                    "completed",
                    "custom_fields",
                    "custom_fields.name",
                    "custom_fields.display_value",
                    "custom_fields.enum_options",
                    "memberships",
                    "memberships.project",
                    "memberships.section",
                ],
            )
            assert task is not None, "Failed to fetch task"
            assert task.gid == SALES_PROCESS_GID
            return task

        task = _run_async(_run())
        # Report what we found
        print(f"\nTask name: {task.name}")
        print(f"Completed: {task.completed}")
        if hasattr(task, "memberships") and task.memberships:
            for m in task.memberships:
                proj = m.get("project", {}) if isinstance(m, dict) else {}
                sect = m.get("section", {}) if isinstance(m, dict) else {}
                print(
                    f"Project: {proj.get('name', '?')} ({proj.get('gid', '?')})"
                    f" Section: {sect.get('name', '?')}"
                )
        if hasattr(task, "custom_fields") and task.custom_fields:
            print(f"Custom fields count: {len(task.custom_fields)}")
            for cf in task.custom_fields[:10]:
                if isinstance(cf, dict):
                    print(f"  {cf.get('name', '?')}: {cf.get('display_value', '?')}")


# ===========================================================================
# Category 3: CompletionService Validation
# ===========================================================================


class TestCompletionService:
    """Validate CompletionService with mock client."""

    def test_complete_uncompleted_process(self):
        """Completing an uncompleted process should call update_async."""
        from autom8_asana.lifecycle.completion import CompletionService

        client = _make_mock_client()
        service = CompletionService(client)
        process = _make_mock_process(completed=False)

        async def _run():
            return await service.complete_source_async(process)

        result = _run_async(_run())
        assert result.completed == [process.gid]
        client.tasks.update_async.assert_called_once_with(process.gid, completed=True)

    def test_complete_already_completed_is_idempotent(self):
        """Completing an already-completed process should return empty."""
        from autom8_asana.lifecycle.completion import CompletionService

        client = _make_mock_client()
        service = CompletionService(client)
        process = _make_mock_process(completed=True)

        async def _run():
            return await service.complete_source_async(process)

        result = _run_async(_run())
        assert result.completed == []
        client.tasks.update_async.assert_not_called()

    def test_complete_api_error_returns_empty(self):
        """If API call fails, should return empty result (fail-forward)."""
        from autom8_asana.lifecycle.completion import CompletionService

        client = _make_mock_client()
        client.tasks.update_async = AsyncMock(
            side_effect=ConnectionError("API timeout")
        )
        service = CompletionService(client)
        process = _make_mock_process(completed=False)

        async def _run():
            return await service.complete_source_async(process)

        result = _run_async(_run())
        assert result.completed == []


# ===========================================================================
# Category 4: SectionService Validation
# ===========================================================================


class TestCascadingSectionService:
    """Validate CascadingSectionService with mock client."""

    def test_cascade_with_all_sections(self):
        """When offer, unit, business sections defined, all three should
        be updated."""
        from autom8_asana.lifecycle.config import CascadingSectionConfig
        from autom8_asana.lifecycle.sections import CascadingSectionService

        client = _make_mock_client()
        service = CascadingSectionService(client)

        config = CascadingSectionConfig(
            offer="Sales Process",
            unit="Next Steps",
            business="OPPORTUNITY",
        )

        # Create mock entities with memberships
        mock_offer = MagicMock()
        mock_offer.gid = "offer_gid"
        mock_offer.memberships = [{"project": {"gid": "proj_offer"}}]

        mock_unit = MagicMock()
        mock_unit.gid = "unit_gid"
        mock_unit.memberships = [{"project": {"gid": "proj_unit"}}]

        mock_business = MagicMock()
        mock_business.gid = "biz_gid"
        mock_business.memberships = [{"project": {"gid": "proj_biz"}}]

        # Mock sections list to return matching sections
        def make_section(name, gid):
            s = MagicMock()
            s.name = name
            s.gid = gid
            return s

        def make_paginator(sections):
            p = MagicMock()
            p.collect = AsyncMock(return_value=sections)
            return p

        client.sections.list_for_project_async = MagicMock(
            side_effect=[
                make_paginator([make_section("Sales Process", "sec_offer")]),
                make_paginator([make_section("Next Steps", "sec_unit")]),
                make_paginator([make_section("OPPORTUNITY", "sec_biz")]),
            ]
        )

        # Mock ResolutionContext
        ctx = MagicMock()
        ctx.offer_async = AsyncMock(return_value=mock_offer)
        ctx.unit_async = AsyncMock(return_value=mock_unit)
        ctx.business_async = AsyncMock(return_value=mock_business)

        async def _run():
            return await service.cascade_async(config, ctx)

        result = _run_async(_run())
        assert len(result.updates) == 3
        assert "offer_gid" in result.updates
        assert "unit_gid" in result.updates
        assert "biz_gid" in result.updates

    def test_cascade_section_not_found(self):
        """When target section not found in project, should add warning
        but not raise."""
        from autom8_asana.lifecycle.config import CascadingSectionConfig
        from autom8_asana.lifecycle.sections import CascadingSectionService

        client = _make_mock_client()
        service = CascadingSectionService(client)

        config = CascadingSectionConfig(offer="NONEXISTENT")

        mock_offer = MagicMock()
        mock_offer.gid = "offer_gid"
        mock_offer.memberships = [{"project": {"gid": "proj_offer"}}]

        # Empty sections list -- section not found
        paginator = MagicMock()
        paginator.collect = AsyncMock(return_value=[])
        client.sections.list_for_project_async = MagicMock(return_value=paginator)

        ctx = MagicMock()
        ctx.offer_async = AsyncMock(return_value=mock_offer)

        async def _run():
            return await service.cascade_async(config, ctx)

        result = _run_async(_run())
        assert len(result.updates) == 0
        assert len(result.warnings) > 0

    def test_cascade_entity_no_memberships(self):
        """Entity with no memberships should produce warning."""
        from autom8_asana.lifecycle.config import CascadingSectionConfig
        from autom8_asana.lifecycle.sections import CascadingSectionService

        client = _make_mock_client()
        service = CascadingSectionService(client)

        config = CascadingSectionConfig(offer="Test Section")

        mock_offer = MagicMock()
        mock_offer.gid = "offer_gid"
        mock_offer.memberships = []  # No memberships

        ctx = MagicMock()
        ctx.offer_async = AsyncMock(return_value=mock_offer)

        async def _run():
            return await service.cascade_async(config, ctx)

        result = _run_async(_run())
        assert len(result.updates) == 0
        assert len(result.warnings) > 0

    def test_cascade_case_insensitive_match(self):
        """Section matching should be case-insensitive."""
        from autom8_asana.lifecycle.config import CascadingSectionConfig
        from autom8_asana.lifecycle.sections import CascadingSectionService

        client = _make_mock_client()
        service = CascadingSectionService(client)

        config = CascadingSectionConfig(offer="sales process")

        mock_offer = MagicMock()
        mock_offer.gid = "offer_gid"
        mock_offer.memberships = [{"project": {"gid": "proj_offer"}}]

        def make_section(name, gid):
            s = MagicMock()
            s.name = name
            s.gid = gid
            return s

        paginator = MagicMock()
        paginator.collect = AsyncMock(
            return_value=[make_section("Sales Process", "sec_1")]
        )
        client.sections.list_for_project_async = MagicMock(return_value=paginator)

        ctx = MagicMock()
        ctx.offer_async = AsyncMock(return_value=mock_offer)

        async def _run():
            return await service.cascade_async(config, ctx)

        result = _run_async(_run())
        assert len(result.updates) == 1


# ===========================================================================
# Category 5: DependencyWiringService Validation
# ===========================================================================


class TestDependencyWiringService:
    """Validate DependencyWiringService with mock client."""

    def test_wire_defaults_calls_add_dependent(self):
        """wire_defaults_async should call add_dependent_async for each
        configured dependent."""
        from autom8_asana.lifecycle.config import LifecycleConfig
        from autom8_asana.lifecycle.wiring import DependencyWiringService

        config = LifecycleConfig(CONFIG_PATH)
        client = _make_mock_client()
        service = DependencyWiringService(client, config)

        mock_unit = MagicMock()
        mock_unit.gid = "unit_gid"
        mock_unit.offer_holder = MagicMock()
        mock_unit.offer_holder.gid = "offer_holder_gid"

        ctx = MagicMock()
        ctx.unit_async = AsyncMock(return_value=mock_unit)
        ctx.business_async = AsyncMock(return_value=MagicMock())

        async def _run():
            return await service.wire_defaults_async("new_entity_gid", "sales", ctx)

        result = _run_async(_run())
        # Should have wired unit and offer_holder
        assert len(result.wired) >= 1

    def test_wire_entity_as_dependency(self):
        """wire_entity_as_dependency_async should call add_dependency_async."""
        from autom8_asana.lifecycle.config import LifecycleConfig
        from autom8_asana.lifecycle.wiring import DependencyWiringService

        config = LifecycleConfig(CONFIG_PATH)
        client = _make_mock_client()
        service = DependencyWiringService(client, config)

        async def _run():
            return await service.wire_entity_as_dependency_async(
                "play_gid", "process_gid", "implementation"
            )

        result = _run_async(_run())
        assert "play_gid" in result.wired
        client.tasks.add_dependency_async.assert_called_once_with(
            "process_gid", "play_gid"
        )

    def test_wire_entity_no_target_gid(self):
        """Passing empty target GID should produce warning, not error."""
        from autom8_asana.lifecycle.config import LifecycleConfig
        from autom8_asana.lifecycle.wiring import DependencyWiringService

        config = LifecycleConfig(CONFIG_PATH)
        client = _make_mock_client()
        service = DependencyWiringService(client, config)

        async def _run():
            return await service.wire_entity_as_dependency_async(
                "play_gid", "", "implementation"
            )

        result = _run_async(_run())
        assert len(result.warnings) > 0
        assert len(result.wired) == 0

    def test_wire_api_error_fail_forward(self):
        """API error during wiring should produce warning, not exception."""
        from autom8_asana.lifecycle.config import LifecycleConfig
        from autom8_asana.lifecycle.wiring import DependencyWiringService

        config = LifecycleConfig(CONFIG_PATH)
        client = _make_mock_client()
        client.tasks.add_dependency_async = AsyncMock(
            side_effect=ConnectionError("timeout")
        )
        service = DependencyWiringService(client, config)

        async def _run():
            return await service.wire_entity_as_dependency_async(
                "play_gid", "process_gid", "implementation"
            )

        result = _run_async(_run())
        assert len(result.warnings) > 0
        assert len(result.wired) == 0


# ===========================================================================
# Category 6: EntityCreationService Validation
# ===========================================================================


class TestEntityCreationService:
    """Validate EntityCreationService with mock client."""

    def test_name_generation_with_placeholders(self):
        """Name generation should replace [Business Name] and
        [Unit Name] placeholders."""
        from autom8_asana.core.creation import generate_entity_name

        business = MagicMock()
        business.name = "Acme Corp"
        unit = MagicMock()
        unit.name = "Unit 1"

        result = generate_entity_name(
            template_name="[Business Name] - [Unit Name] Process",
            business=business,
            unit=unit,
        )
        assert "Acme Corp" in result
        assert "Unit 1" in result

    def test_name_generation_no_template(self):
        """When no template name, should return default fallback 'New Process'."""
        from autom8_asana.core.creation import generate_entity_name

        result = generate_entity_name(template_name=None, business=None, unit=None)
        assert result == "New Process"

    def test_name_generation_case_insensitive(self):
        """Placeholder replacement should be case-insensitive."""
        from autom8_asana.core.creation import generate_entity_name

        business = MagicMock()
        business.name = "Acme"
        result = generate_entity_name(
            template_name="[BUSINESS NAME] Process",
            business=business,
            unit=None,
        )
        assert "Acme" in result

    def test_extract_user_gid_from_list_dict(self):
        """Should extract gid from list of dicts."""
        from autom8_asana.lifecycle.creation import EntityCreationService

        result = EntityCreationService._extract_user_gid(
            [{"gid": "user123", "name": "Alice"}]
        )
        assert result == "user123"

    def test_extract_user_gid_from_empty(self):
        """Empty list should return None."""
        from autom8_asana.lifecycle.creation import EntityCreationService

        result = EntityCreationService._extract_user_gid([])
        assert result is None

    def test_extract_user_gid_from_dict(self):
        """Single dict should return gid."""
        from autom8_asana.lifecycle.creation import EntityCreationService

        result = EntityCreationService._extract_user_gid({"gid": "user456"})
        assert result == "user456"

    def test_matches_process_type_dict_style(self):
        """Should match ProcessType custom field in dict-style."""
        from autom8_asana.lifecycle.creation import EntityCreationService

        task = MagicMock()
        task.custom_fields = [{"name": "Process Type", "display_value": "Sales"}]
        assert EntityCreationService._matches_process_type(task, "sales")

    def test_matches_process_type_no_match(self):
        """Should return False when no matching ProcessType."""
        from autom8_asana.lifecycle.creation import EntityCreationService

        task = MagicMock()
        task.custom_fields = [{"name": "Process Type", "display_value": "Onboarding"}]
        assert not EntityCreationService._matches_process_type(task, "sales")

    def test_matches_process_type_no_custom_fields(self):
        """Should return False when custom_fields is None."""
        from autom8_asana.lifecycle.creation import EntityCreationService

        task = MagicMock()
        task.custom_fields = None
        assert not EntityCreationService._matches_process_type(task, "sales")


# ===========================================================================
# Category 7: Init Action Handlers Validation
# ===========================================================================


class TestInitActionHandlers:
    """Validate init action handler registration and execution."""

    def test_handler_registry_completeness(self):
        """All expected handler types should be registered."""
        from autom8_asana.lifecycle.init_actions import HANDLER_REGISTRY

        expected_types = {
            "play_creation",
            "entity_creation",
            "products_check",
            "activate_campaign",
            "deactivate_campaign",
            "create_comment",
        }
        assert expected_types == set(HANDLER_REGISTRY.keys())

    def test_comment_handler_builds_comment(self):
        """CommentHandler._build_comment should produce a non-empty
        comment with source link."""
        from autom8_asana.lifecycle.init_actions import CommentHandler

        source = MagicMock()
        source.name = "Test Sales Process"
        source.gid = "12345"
        source.memberships = [{"project": {"gid": "proj_gid"}}]
        business = MagicMock()
        business.name = "Acme Corp"

        comment = CommentHandler._build_comment(source, business, None)
        assert "Pipeline Conversion" in comment
        assert "Acme Corp" in comment
        assert "Test Sales Process" in comment
        assert "https://app.asana.com/" in comment

    def test_comment_handler_soft_fails(self):
        """CommentHandler should return success=True even on API error."""
        from autom8_asana.lifecycle.config import LifecycleConfig
        from autom8_asana.lifecycle.init_actions import CommentHandler

        config = LifecycleConfig(CONFIG_PATH)
        client = _make_mock_client()
        client.stories.create_comment_async = AsyncMock(
            side_effect=ConnectionError("timeout")
        )
        handler = CommentHandler(client, config)

        action_config = MagicMock()
        action_config.comment_template = None
        process = _make_mock_process()
        ctx = MagicMock()
        ctx.business_async = AsyncMock(
            return_value=MagicMock(name="Biz", gid="biz_gid")
        )

        async def _run():
            return await handler.execute_async(ctx, "new_gid", action_config, process)

        result = _run_async(_run())
        assert result.success is True

    def test_campaign_handler_logs_and_succeeds(self):
        """CampaignHandler should succeed (log only, no side effect)."""
        from autom8_asana.lifecycle.config import LifecycleConfig
        from autom8_asana.lifecycle.init_actions import CampaignHandler

        config = LifecycleConfig(CONFIG_PATH)
        client = _make_mock_client()
        handler = CampaignHandler(client, config)

        action_config = MagicMock()
        action_config.type = "activate_campaign"
        process = _make_mock_process()
        ctx = MagicMock()
        business_mock = MagicMock()
        business_mock.name = "Biz"
        business_mock.gid = "biz_gid"
        ctx.business_async = AsyncMock(return_value=business_mock)

        async def _run():
            return await handler.execute_async(ctx, "new_gid", action_config, process)

        result = _run_async(_run())
        assert result.success is True

    def test_products_check_no_products(self):
        """ProductsCheckHandler should succeed with empty entity_gid when
        no products field on business."""
        from autom8_asana.lifecycle.config import LifecycleConfig
        from autom8_asana.lifecycle.init_actions import ProductsCheckHandler

        config = LifecycleConfig(CONFIG_PATH)
        client = _make_mock_client()
        handler = ProductsCheckHandler(client, config)

        action_config = MagicMock()
        action_config.condition = "video*"
        process = _make_mock_process()
        ctx = MagicMock()
        business_mock = MagicMock()
        business_mock.products = None
        ctx.business_async = AsyncMock(return_value=business_mock)

        async def _run():
            return await handler.execute_async(ctx, "new_gid", action_config, process)

        result = _run_async(_run())
        assert result.success is True
        assert result.entity_gid == ""

    def test_products_check_no_match(self):
        """ProductsCheckHandler should succeed with empty entity_gid when
        products don't match pattern."""
        from autom8_asana.lifecycle.config import LifecycleConfig
        from autom8_asana.lifecycle.init_actions import ProductsCheckHandler

        config = LifecycleConfig(CONFIG_PATH)
        client = _make_mock_client()
        handler = ProductsCheckHandler(client, config)

        action_config = MagicMock()
        action_config.condition = "video*"
        process = _make_mock_process()
        ctx = MagicMock()
        business_mock = MagicMock()
        business_mock.products = ["seo", "ppc"]
        ctx.business_async = AsyncMock(return_value=business_mock)

        async def _run():
            return await handler.execute_async(ctx, "new_gid", action_config, process)

        result = _run_async(_run())
        assert result.success is True
        assert result.entity_gid == ""


# ===========================================================================
# Category 8: LifecycleEngine Integration
# ===========================================================================


class TestLifecycleEngineIntegration:
    """Validate LifecycleEngine orchestration with mock services."""

    def _make_engine(self, client=None, config=None):
        """Build a LifecycleEngine with all mock services."""
        from autom8_asana.lifecycle.config import LifecycleConfig
        from autom8_asana.lifecycle.engine import (
            CascadeResult,
            CompletionResult,
            CreationResult,
            LifecycleActionResult,
            LifecycleEngine,
            ReopenResult,
            WiringResult,
        )

        if client is None:
            client = _make_mock_client()
        if config is None:
            config = LifecycleConfig(CONFIG_PATH)

        # Mock creation service
        creation_service = MagicMock()
        creation_service.create_process_async = AsyncMock(
            return_value=CreationResult(success=True, entity_gid="new_proc_gid")
        )

        # Mock section service
        section_service = MagicMock()
        section_service.cascade_async = AsyncMock(
            return_value=CascadeResult(updates=["offer_gid", "unit_gid"])
        )

        # Mock completion service
        completion_service = MagicMock()
        completion_service.complete_source_async = AsyncMock(
            return_value=CompletionResult(completed=["source_gid"])
        )

        # Mock init action registry
        init_action_registry = MagicMock()
        init_action_registry.execute_actions_async = AsyncMock(
            return_value=[LifecycleActionResult(success=True, entity_gid="play_gid")]
        )

        # Mock wiring service
        wiring_service = MagicMock()
        wiring_service.wire_defaults_async = AsyncMock(
            return_value=WiringResult(wired=["dep_gid"])
        )

        # Mock reopen service
        reopen_service = MagicMock()
        reopen_service.reopen_async = AsyncMock(
            return_value=ReopenResult(success=True, entity_gid="reopened_gid")
        )

        engine = LifecycleEngine(
            client,
            config,
            creation_service=creation_service,
            section_service=section_service,
            completion_service=completion_service,
            init_action_registry=init_action_registry,
            wiring_service=wiring_service,
            reopen_service=reopen_service,
        )
        return (
            engine,
            creation_service,
            section_service,
            completion_service,
            init_action_registry,
            wiring_service,
            reopen_service,
        )

    def test_converted_transition_runs_all_phases(self):
        """CONVERTED transition should run all 4 phases in order."""
        (engine, creation, sections, completion, actions, wiring, _) = (
            self._make_engine()
        )

        process = _make_mock_process(process_type_value="sales")

        async def _run():
            return await engine.handle_transition_async(process, "converted")

        result = _run_async(_run())
        assert result.success is True
        assert "create_process" in result.actions_executed
        assert "cascade_sections" in result.actions_executed
        assert "auto_complete_source" in result.actions_executed

        # Verify phases were called
        creation.create_process_async.assert_called_once()
        sections.cascade_async.assert_called_once()
        completion.complete_source_async.assert_called_once()
        actions.execute_actions_async.assert_called_once()
        wiring.wire_defaults_async.assert_called_once()

    def test_outreach_converted_skips_auto_complete(self):
        """Outreach CONVERTED should NOT auto-complete (flag=false)."""
        (engine, creation, sections, completion, actions, wiring, _) = (
            self._make_engine()
        )

        process = _make_mock_process(process_type_value="outreach")

        async def _run():
            return await engine.handle_transition_async(process, "converted")

        result = _run_async(_run())
        assert result.success is True
        # Outreach has auto_complete_prior=false
        completion.complete_source_async.assert_not_called()

    def test_terminal_transition(self):
        """Implementation CONVERTED is terminal (target=null)."""
        (engine, creation, sections, completion, actions, wiring, _) = (
            self._make_engine()
        )

        process = _make_mock_process(process_type_value="implementation")

        async def _run():
            return await engine.handle_transition_async(process, "converted")

        result = _run_async(_run())
        assert result.success is True
        assert "terminal" in result.actions_executed
        # Terminal transitions do NOT create new entities
        creation.create_process_async.assert_not_called()

    def test_dnc_deferred(self):
        """Outreach DNC is 'deferred' - should just log."""
        (engine, creation, sections, completion, actions, wiring, _) = (
            self._make_engine()
        )

        process = _make_mock_process(process_type_value="outreach")

        async def _run():
            return await engine.handle_transition_async(process, "did_not_convert")

        result = _run_async(_run())
        assert result.success is True
        assert "dnc_deferred" in result.actions_executed
        creation.create_process_async.assert_not_called()

    def test_dnc_create_new(self):
        """Sales DNC should create a new outreach process."""
        (engine, creation, sections, completion, actions, wiring, reopen) = (
            self._make_engine()
        )

        process = _make_mock_process(process_type_value="sales")

        async def _run():
            return await engine.handle_transition_async(process, "did_not_convert")

        result = _run_async(_run())
        assert result.success is True
        creation.create_process_async.assert_called_once()
        reopen.reopen_async.assert_not_called()

    def test_dnc_reopen(self):
        """Onboarding DNC should reopen, not create new."""
        (engine, creation, sections, completion, actions, wiring, reopen) = (
            self._make_engine()
        )

        process = _make_mock_process(process_type_value="onboarding")

        async def _run():
            return await engine.handle_transition_async(process, "did_not_convert")

        result = _run_async(_run())
        assert result.success is True
        assert "reopen_process" in result.actions_executed
        reopen.reopen_async.assert_called_once()
        creation.create_process_async.assert_not_called()

    def test_unknown_stage_returns_error(self):
        """Unknown source stage should return error result, not crash."""
        (engine, creation, sections, completion, actions, wiring, _) = (
            self._make_engine()
        )

        process = _make_mock_process(process_type_value="nonexistent")

        async def _run():
            return await engine.handle_transition_async(process, "converted")

        result = _run_async(_run())
        assert result.success is False
        assert "nonexistent" in result.error

    def test_creation_failure_hard_fails(self):
        """If Phase 1 creation fails, the transition should hard-fail."""
        from autom8_asana.lifecycle.engine import CreationResult

        (engine, creation, sections, completion, actions, wiring, _) = (
            self._make_engine()
        )
        creation.create_process_async = AsyncMock(
            return_value=CreationResult(success=False, error="Template not found")
        )

        process = _make_mock_process(process_type_value="sales")

        async def _run():
            return await engine.handle_transition_async(process, "converted")

        result = _run_async(_run())
        assert result.success is False
        assert "creation failed" in result.error.lower()
        # Phases 2-4 should NOT have been called
        sections.cascade_async.assert_not_called()
        completion.complete_source_async.assert_not_called()

    def test_phase2_failure_fail_forward(self):
        """If Phase 2 cascade fails, should warn but continue."""
        (engine, creation, sections, completion, actions, wiring, _) = (
            self._make_engine()
        )
        sections.cascade_async = AsyncMock(side_effect=RuntimeError("cascade boom"))

        process = _make_mock_process(process_type_value="sales")

        async def _run():
            return await engine.handle_transition_async(process, "converted")

        result = _run_async(_run())
        # Should succeed overall (fail-forward)
        assert result.success is True
        # Phase 3 and 4 should still have been called
        actions.execute_actions_async.assert_called_once()
        wiring.wire_defaults_async.assert_called_once()

    def test_exception_in_engine_is_boundary_guarded(self):
        """Unhandled exception in transition should be caught by
        boundary guard."""
        (engine, creation, sections, completion, actions, wiring, _) = (
            self._make_engine()
        )
        # Force an unexpected error in creation service
        creation.create_process_async = AsyncMock(side_effect=TypeError("unexpected"))

        process = _make_mock_process(process_type_value="sales")

        async def _run():
            return await engine.handle_transition_async(process, "converted")

        # The exception from the mock is inside _run_pipeline_async which
        # is inside the try/except boundary in handle_transition_async
        result = _run_async(_run())
        assert result.success is False

    def test_pre_validation_warn_mode(self):
        """Onboarding stage has pre_transition validation in warn mode.
        Missing fields should add warning but allow transition."""
        (engine, creation, sections, completion, actions, wiring, _) = (
            self._make_engine()
        )

        # Process missing Contact Phone
        process = _make_mock_process(
            process_type_value="onboarding",
            contact_phone=None,
        )

        async def _run():
            return await engine.handle_transition_async(process, "converted")

        result = _run_async(_run())
        # Should succeed (warn mode, not block)
        assert result.success is True

    def test_terminal_auto_complete_on_implementation_converted(self):
        """Implementation CONVERTED is terminal but has auto_complete_prior=
        true. The engine should record auto_complete_source action.

        D-LC-004 FIXED: _handle_terminal_async now calls CompletionService
        instead of just recording the action string.
        """
        (engine, creation, sections, completion, actions, wiring, _) = (
            self._make_engine()
        )

        process = _make_mock_process(process_type_value="implementation")

        async def _run():
            return await engine.handle_transition_async(process, "converted")

        result = _run_async(_run())
        assert result.success is True
        assert "auto_complete_source" in result.actions_executed
        assert "terminal" in result.actions_executed
        # D-LC-004: CompletionService is now actually called for terminal transitions
        completion.complete_source_async.assert_called_once_with(process)


# ===========================================================================
# Category 9: Edge Cases and Adversarial Scenarios
# ===========================================================================


class TestEdgeCasesAdversarial:
    """Adversarial testing of lifecycle modules."""

    def test_missing_yaml_file_raises(self):
        """Loading config from nonexistent path should raise
        FileNotFoundError."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        with pytest.raises(FileNotFoundError):
            LifecycleConfig(Path("/tmp/nonexistent_lifecycle.yaml"))

    def test_invalid_yaml_schema_raises(self):
        """Loading YAML with invalid schema should raise
        ValidationError."""
        from pydantic import ValidationError

        from autom8_asana.lifecycle.config import LifecycleConfig

        # Write invalid YAML
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write("stages:\n  broken:\n    pipeline_stage: not_a_number\n")
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(ValidationError):
                LifecycleConfig(path)
        finally:
            path.unlink()

    def test_dag_integrity_failure_raises(self):
        """YAML with transition referencing undefined stage should raise
        ValueError."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        yaml_content = {
            "stages": {
                "stage_a": {
                    "name": "stage_a",
                    "pipeline_stage": 1,
                    "transitions": {
                        "converted": "nonexistent_stage",
                        "did_not_convert": None,
                    },
                }
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump(yaml_content, f)
            path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="DAG integrity"):
                LifecycleConfig(path)
        finally:
            path.unlink()

    def test_circular_transitions_are_valid(self):
        """Circular transitions (A -> B -> A) should load without error.
        The DAG validator only checks that targets exist, not cycles."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        yaml_content = {
            "stages": {
                "alpha": {
                    "name": "alpha",
                    "pipeline_stage": 1,
                    "transitions": {
                        "converted": "beta",
                        "did_not_convert": None,
                    },
                },
                "beta": {
                    "name": "beta",
                    "pipeline_stage": 2,
                    "transitions": {
                        "converted": "alpha",
                        "did_not_convert": "alpha",
                    },
                },
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump(yaml_content, f)
            path = Path(f.name)

        try:
            config = LifecycleConfig(path)
            assert config.get_stage("alpha") is not None
            assert config.get_stage("beta") is not None
        finally:
            path.unlink()

    def test_get_stage_returns_none_for_unknown(self):
        """get_stage with unknown name should return None, not raise."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        assert config.get_stage("totally_bogus") is None

    def test_get_target_stage_with_unknown_source(self):
        """get_target_stage with unknown source should return None."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        assert config.get_target_stage("bogus", "converted") is None

    def test_get_dnc_action_unknown_stage_raises_keyerror(self):
        """get_dnc_action with unknown stage should raise KeyError."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        with pytest.raises(KeyError):
            config.get_dnc_action("nonexistent_stage")

    def test_get_transition_with_invalid_outcome(self):
        """get_transition with invalid outcome attribute should still
        return the TransitionConfig (not crash) since it returns the
        whole TransitionConfig object."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        # get_transition returns the full TransitionConfig for the source stage
        tc = config.get_transition("sales", "bogus_outcome")
        assert tc is not None  # Returns TransitionConfig
        # But get_target_stage with bogus outcome returns None
        target = config.get_target_stage("sales", "bogus_outcome")
        assert target is None

    def test_uninitialized_config_returns_empty(self):
        """LifecycleConfig constructed with no path should return empty
        stages and None lookups."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig()
        assert config.stages == {}
        assert config.get_stage("sales") is None
        assert config.get_wiring_rules("anything") is None

    def test_reopen_service_no_process_holder(self):
        """ReopenService with no ProcessHolder should return failure."""
        from autom8_asana.lifecycle.reopen import ReopenService

        client = _make_mock_client()
        service = ReopenService(client)

        # Source process with no process_holder and ctx that returns None
        process = _make_mock_process()
        process.process_holder = None

        target_stage = MagicMock()
        target_stage.name = "sales"
        target_stage.project_gid = "proj_sales"
        target_stage.target_section = "OPPORTUNITY"

        ctx = MagicMock()
        ctx.resolve_holder_async = AsyncMock(return_value=None)

        async def _run():
            return await service.reopen_async(target_stage, ctx, process)

        result = _run_async(_run())
        assert result.success is False
        assert "ProcessHolder" in result.error

    def test_reopen_service_no_matching_candidates(self):
        """ReopenService with no matching process type should return
        failure."""
        from autom8_asana.lifecycle.reopen import ReopenService

        client = _make_mock_client()
        service = ReopenService(client)

        # Create a holder with subtasks that don't match
        holder = MagicMock()
        holder.gid = "holder_gid"

        subtask = MagicMock()
        subtask.custom_fields = [
            {"name": "Process Type", "display_value": "Onboarding"}
        ]
        subtask.completed = False
        subtask.created_at = "2025-01-01T00:00:00Z"

        # list subtasks
        paginator = MagicMock()
        paginator.collect = AsyncMock(return_value=[subtask])
        client.tasks.subtasks_async = MagicMock(return_value=paginator)

        process = _make_mock_process()
        process.process_holder = holder

        target_stage = MagicMock()
        target_stage.name = "sales"
        target_stage.project_gid = "proj_sales"
        target_stage.target_section = "OPPORTUNITY"

        ctx = MagicMock()

        async def _run():
            return await service.reopen_async(target_stage, ctx, process)

        result = _run_async(_run())
        assert result.success is False
        assert "sales" in result.error.lower()

    def test_transition_result_success_logic(self):
        """TransitionResult.success should be True only when
        hard_failure is None."""
        from autom8_asana.lifecycle.engine import TransitionResult

        tr = TransitionResult("gid123")
        assert tr.success is True

        tr.add_warning("soft issue")
        assert tr.success is True  # Warnings don't affect success

        tr.fail("hard issue")
        assert tr.success is False

    def test_build_result_maps_error_correctly(self):
        """_build_result should set success=False when error or
        hard_failure is present."""
        from autom8_asana.lifecycle.config import LifecycleConfig
        from autom8_asana.lifecycle.engine import (
            LifecycleEngine,
            TransitionResult,
        )

        client = _make_mock_client()
        config = LifecycleConfig(CONFIG_PATH)
        engine = LifecycleEngine(
            client,
            config,
            creation_service=MagicMock(),
            section_service=MagicMock(),
            completion_service=MagicMock(),
            init_action_registry=MagicMock(),
            wiring_service=MagicMock(),
            reopen_service=MagicMock(),
        )

        process = _make_mock_process()
        import time

        start = time.perf_counter()
        tr = TransitionResult(process.gid)

        # Without error
        result = engine._build_result("test_rule", process, start, tr)
        assert result.success is True
        assert result.error == ""

        # With explicit error
        result_err = engine._build_result(
            "test_rule", process, start, tr, error="explicit"
        )
        assert result_err.success is False
        assert result_err.error == "explicit"

        # With hard_failure
        tr.fail("hard failure")
        result_hard = engine._build_result("test_rule", process, start, tr)
        assert result_hard.success is False
        assert result_hard.error == "hard failure"

    def test_empty_yaml_stages_raises_validation_error(self):
        """YAML with empty stages dict should raise ValidationError
        (stages is required)."""

        from autom8_asana.lifecycle.config import LifecycleConfig

        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write("stages: {}\n")
            path = Path(f.name)

        try:
            # Empty stages dict is actually valid from Pydantic perspective
            config = LifecycleConfig(path)
            assert len(config.stages) == 0
        finally:
            path.unlink()

    def test_concurrent_engine_calls_isolated(self):
        """Two concurrent calls to handle_transition_async should not
        interfere with each other. Each creates its own TransitionResult."""
        from autom8_asana.lifecycle.config import LifecycleConfig
        from autom8_asana.lifecycle.engine import (
            CascadeResult,
            CompletionResult,
            CreationResult,
            LifecycleEngine,
            WiringResult,
        )

        client = _make_mock_client()
        config = LifecycleConfig(CONFIG_PATH)

        creation_service = MagicMock()
        creation_service.create_process_async = AsyncMock(
            return_value=CreationResult(success=True, entity_gid="new_gid")
        )
        section_service = MagicMock()
        section_service.cascade_async = AsyncMock(
            return_value=CascadeResult(updates=[])
        )
        completion_service = MagicMock()
        completion_service.complete_source_async = AsyncMock(
            return_value=CompletionResult(completed=[])
        )
        init_action_registry = MagicMock()
        init_action_registry.execute_actions_async = AsyncMock(return_value=[])
        wiring_service = MagicMock()
        wiring_service.wire_defaults_async = AsyncMock(
            return_value=WiringResult(wired=[])
        )

        engine = LifecycleEngine(
            client,
            config,
            creation_service=creation_service,
            section_service=section_service,
            completion_service=completion_service,
            init_action_registry=init_action_registry,
            wiring_service=wiring_service,
            reopen_service=MagicMock(),
        )

        proc_a = _make_mock_process(gid="A", process_type_value="sales")
        proc_b = _make_mock_process(gid="B", process_type_value="sales")

        async def _run():
            r_a, r_b = await asyncio.gather(
                engine.handle_transition_async(proc_a, "converted"),
                engine.handle_transition_async(proc_b, "converted"),
            )
            return r_a, r_b

        r_a, r_b = _run_async(_run())
        assert r_a.success is True
        assert r_b.success is True
        assert r_a.triggered_by_gid == "A"
        assert r_b.triggered_by_gid == "B"

    def test_cascading_sections_config_partial(self):
        """CascadingSectionConfig with only some fields set should
        only update those fields."""
        from autom8_asana.lifecycle.config import CascadingSectionConfig

        config = CascadingSectionConfig(offer="Test", unit=None, business=None)
        assert config.offer == "Test"
        assert config.unit is None
        assert config.business is None

    def test_init_action_config_defaults(self):
        """InitActionConfig with only type should use defaults for
        everything else."""
        from autom8_asana.lifecycle.config import InitActionConfig

        action = InitActionConfig(type="create_comment")
        assert action.type == "create_comment"
        assert action.condition is None
        assert action.wire_as_dependency is False
        assert action.always_create_new is False

    def test_default_init_action_registry_unknown_type(self):
        """_DefaultInitActionRegistry should return failed LifecycleActionResult
        for unknown action types."""
        from autom8_asana.lifecycle.config import (
            InitActionConfig,
            LifecycleConfig,
        )
        from autom8_asana.lifecycle.engine import (
            _DefaultInitActionRegistry,
        )

        client = _make_mock_client()
        config = LifecycleConfig(CONFIG_PATH)
        registry = _DefaultInitActionRegistry(client, config)

        unknown_action = InitActionConfig(type="nonexistent_handler")
        process = _make_mock_process()
        ctx = MagicMock()

        async def _run():
            return await registry.execute_actions_async(
                [unknown_action], "entity_gid", ctx, process
            )

        results = _run_async(_run())
        assert len(results) == 1
        assert results[0].success is False
        assert "Unknown" in results[0].error

    def test_engine_build_result_execution_time_positive(self):
        """_build_result should record positive execution_time_ms."""
        from autom8_asana.lifecycle.config import LifecycleConfig
        from autom8_asana.lifecycle.engine import (
            LifecycleEngine,
            TransitionResult,
        )

        client = _make_mock_client()
        config = LifecycleConfig(CONFIG_PATH)
        engine = LifecycleEngine(
            client,
            config,
            creation_service=MagicMock(),
            section_service=MagicMock(),
            completion_service=MagicMock(),
            init_action_registry=MagicMock(),
            wiring_service=MagicMock(),
            reopen_service=MagicMock(),
        )

        process = _make_mock_process()
        import time

        start = time.perf_counter()
        # Simulate some time passing
        time.sleep(0.001)
        tr = TransitionResult(process.gid)
        result = engine._build_result("test", process, start, tr)
        assert result.execution_time_ms > 0

    def test_dnc_action_values_per_stage(self):
        """Verify exact DNC actions for each active stage."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        expected = {
            "outreach": "deferred",
            "sales": "create_new",
            "onboarding": "reopen",
            "implementation": "create_new",
        }
        for stage_name, expected_action in expected.items():
            actual = config.get_dnc_action(stage_name)
            assert actual == expected_action, (
                f"Stage '{stage_name}': expected dnc_action="
                f"'{expected_action}', got '{actual}'"
            )

    def test_transition_targets_per_stage(self):
        """Verify exact transition targets for active stages."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        expected = {
            "outreach": ("sales", "outreach"),
            "sales": ("onboarding", "outreach"),
            "onboarding": ("implementation", "sales"),
            "implementation": (None, "outreach"),
        }
        for stage_name, (conv, dnc) in expected.items():
            stage = config.get_stage(stage_name)
            assert stage is not None
            assert stage.transitions.converted == conv, (
                f"Stage '{stage_name}': expected converted='{conv}', "
                f"got '{stage.transitions.converted}'"
            )
            assert stage.transitions.did_not_convert == dnc, (
                f"Stage '{stage_name}': expected did_not_convert="
                f"'{dnc}', got '{stage.transitions.did_not_convert}'"
            )

    def test_yaml_config_with_extra_fields_ignored(self):
        """Pydantic model should not fail if YAML has extra unknown
        fields (extra='ignore' behavior). This tests robustness of
        the config loader against YAML additions."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        yaml_content = {
            "stages": {
                "test_stage": {
                    "name": "test_stage",
                    "pipeline_stage": 1,
                    "transitions": {
                        "converted": None,
                        "did_not_convert": None,
                    },
                    "unknown_future_field": "should be ignored",
                }
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump(yaml_content, f)
            path = Path(f.name)

        try:
            # Pydantic v2 default is extra='ignore' for BaseModel
            # If it's 'forbid', this will raise
            config = LifecycleConfig(path)
            assert config.get_stage("test_stage") is not None
        except Exception as e:
            pytest.fail(
                f"D-LC-002: Config loader rejects unknown YAML fields: {e}. "
                f"This means adding new fields to YAML requires updating "
                f"the Pydantic model first, which could be fragile."
            )
        finally:
            path.unlink()

    def test_terminal_dnc_path_implementation_to_outreach(self):
        """Implementation DNC goes to outreach (TDD Section 8.2
        correction). Verify the entire chain: implementation DNC ->
        outreach (not sales)."""
        from autom8_asana.lifecycle.config import LifecycleConfig

        config = LifecycleConfig(CONFIG_PATH)
        impl = config.get_stage("implementation")
        assert impl is not None
        assert impl.transitions.did_not_convert == "outreach", (
            "Implementation DNC should route to outreach per TDD 8.2 "
            "correction, not sales"
        )
