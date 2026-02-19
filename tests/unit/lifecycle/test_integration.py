"""Integration tests for LifecycleEngine full workflow chains.

These tests exercise the engine with real LifecycleConfig from YAML and
let the engine construct its own services. Only the Asana client,
ResolutionContext, discover_template_async, wait_for_subtasks_async,
AutoCascadeSeeder, and SaveSession are mocked.

Key transition paths tested:
1. Sales CONVERTED -> Onboarding
2. Onboarding CONVERTED -> Implementation
3. Implementation CONVERTED -> Terminal
4. Outreach CONVERTED -> Sales
5. Sales DNC -> Outreach (create_new)
6. Onboarding DNC -> Sales (reopen)
7. Implementation DNC -> Outreach (create_new)
8. Outreach DNC -> Outreach (deferred)

Additional edge cases:
- Unknown stage -> error result
- Pre-validation block mode
- Creation failure -> hard failure
- Init action failure -> warning (not hard failure)
- Cascade sections verification
- Wiring phase verification
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.lifecycle.config import LifecycleConfig
from autom8_asana.lifecycle.engine import LifecycleEngine
from autom8_asana.lifecycle.seeding import SeedingResult
from autom8_asana.models.business.process import Process, ProcessType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_paginator(items: list) -> MagicMock:
    """Create a mock paginator that returns items on .collect()."""
    paginator = MagicMock()
    paginator.collect = AsyncMock(return_value=items)
    return paginator


def _make_mock_task(gid: str, task_name: str, **kwargs) -> MagicMock:
    """Create a mock Asana task with proper name attribute.

    MagicMock(name=...) sets the mock's internal _mock_name, not the
    .name attribute. This helper sets .name explicitly to avoid issues
    with code that reads task.name (e.g., re.sub in _generate_name).

    Sets num_subtasks=0 by default so that getattr(template, "num_subtasks", 0)
    returns a real int instead of a MagicMock child (IMP-13 compatibility).
    """
    task = MagicMock()
    task.gid = gid
    task.name = task_name
    task.num_subtasks = 0
    for key, value in kwargs.items():
        setattr(task, key, value)
    return task


def _make_mock_client() -> MagicMock:
    """Create a comprehensive mock AsanaClient for integration tests.

    Sets up all API namespaces that the lifecycle services access:
    - tasks: duplicate, create, update, add_to_project, subtasks, get,
             set_assignee, add_dependent, add_dependency, add_dependencies,
             search
    - sections: list_for_project, add_task
    - stories: create_comment
    """
    client = MagicMock()

    # --- Tasks namespace ---
    client.tasks = MagicMock()

    # Template task for duplication
    mock_new_task = _make_mock_task("new_process_gid", "Template - [Business Name]")

    client.tasks.duplicate_async = AsyncMock(return_value=mock_new_task)
    client.tasks.create_async = AsyncMock(return_value=mock_new_task)
    client.tasks.add_to_project_async = AsyncMock()
    client.tasks.update_async = AsyncMock()
    client.tasks.set_assignee_async = AsyncMock()
    client.tasks.add_dependent_async = AsyncMock()
    client.tasks.add_dependency_async = AsyncMock()
    client.tasks.add_dependencies_async = AsyncMock()
    client.tasks.search_async = AsyncMock(return_value=[])

    # Subtasks paginator (returns empty by default)
    client.tasks.subtasks_async = MagicMock(return_value=_make_paginator([]))

    # get_async returns a task with custom_fields and dependencies
    mock_fetched_task = MagicMock()
    mock_fetched_task.custom_fields = []
    mock_fetched_task.dependencies = []
    client.tasks.get_async = AsyncMock(return_value=mock_fetched_task)

    # --- Sections namespace ---
    client.sections = MagicMock()

    # Default sections for any project (TEMPLATE, OPPORTUNITY, etc.)
    mock_template_section = _make_mock_task("sec_template", "TEMPLATE")
    mock_opportunity_section = _make_mock_task("sec_opportunity", "OPPORTUNITY")

    client.sections.list_for_project_async = MagicMock(
        return_value=_make_paginator([mock_template_section, mock_opportunity_section])
    )
    client.sections.add_task_async = AsyncMock()

    # --- Stories namespace ---
    client.stories = MagicMock()
    client.stories.create_comment_async = AsyncMock()

    return client


def _make_mock_process(
    process_type: ProcessType,
    project_gid: str,
    project_name: str,
    *,
    gid: str = "src_process_gid",
    name: str = "Sales - Test Business",
    completed: bool = False,
) -> MagicMock:
    """Create a mock Process with appropriate memberships for process_type detection."""
    process = MagicMock(spec=Process)
    process.gid = gid
    process.name = name
    process.process_type = process_type
    process.completed = completed
    process.memberships = [
        {
            "project": {"gid": project_gid, "name": project_name},
            "section": {"gid": "sec_converted", "name": "Converted"},
        }
    ]
    # ProcessHolder not directly available in integration tests
    process.process_holder = None
    # Fields for assignee resolution
    process.rep = [{"gid": "rep_user_gid"}]
    process.onboarding_specialist = None
    process.implementation_lead = None
    process.custom_fields = []
    return process


def _make_mock_context(
    mock_business: MagicMock,
    mock_unit: MagicMock,
    mock_offer: MagicMock,
) -> AsyncMock:
    """Create a mock ResolutionContext for patching."""
    ctx = AsyncMock()
    ctx.business_async = AsyncMock(return_value=mock_business)
    ctx.unit_async = AsyncMock(return_value=mock_unit)
    ctx.offer_async = AsyncMock(return_value=mock_offer)
    ctx.cache_entity = MagicMock()
    ctx.hydrate_branch_async = AsyncMock()
    ctx.resolve_holder_async = AsyncMock(return_value=None)
    ctx._trigger_entity = None

    # Context manager support
    ctx.__aenter__ = AsyncMock(return_value=ctx)
    ctx.__aexit__ = AsyncMock(return_value=None)

    return ctx


def _make_mock_business() -> MagicMock:
    """Create a mock Business entity."""
    business = MagicMock()
    business.gid = "biz_gid"
    business.name = "Test Business"
    business.dna_holder = None
    business.rep = [{"gid": "rep_user_gid"}]
    business.products = None
    business.custom_fields = []
    business.memberships = [
        {
            "project": {"gid": "biz_proj_gid", "name": "Businesses"},
            "section": {"gid": "biz_sec_gid", "name": "OPPORTUNITY"},
        }
    ]
    return business


def _make_mock_unit() -> MagicMock:
    """Create a mock Unit entity."""
    unit = MagicMock()
    unit.gid = "unit_gid"
    unit.name = "Test Unit"
    unit.processes = []
    unit.offer_holder = MagicMock(gid="offer_holder_gid")
    unit.rep = [{"gid": "rep_user_gid"}]
    unit.custom_fields = []
    unit.memberships = [
        {
            "project": {"gid": "unit_proj_gid", "name": "Units"},
            "section": {"gid": "unit_sec_gid", "name": "Engaged"},
        }
    ]
    return unit


def _make_mock_offer() -> MagicMock:
    """Create a mock Offer entity."""
    offer = MagicMock()
    offer.gid = "offer_gid"
    offer.name = "Test Offer"
    offer.memberships = [
        {
            "project": {"gid": "offer_proj_gid", "name": "Offers"},
            "section": {"gid": "offer_sec_gid", "name": "Active"},
        }
    ]
    return offer


def _configure_standard_patches(
    mock_ctx: AsyncMock,
    mock_template: MagicMock,
    MockCtx: MagicMock,
    MockTD: MagicMock,
    MockWaiter: MagicMock,
    MockSeeder: MagicMock,
    MockSaveSession: MagicMock,
    *,
    seeding_result: SeedingResult | None = None,
) -> None:
    """Apply standard patch configuration for the 5-patch integration setup.

    This configures the mocked ResolutionContext, discover_template_async,
    wait_for_subtasks_async, AutoCascadeSeeder, and SaveSession with reasonable
    defaults for a successful pipeline execution.
    """
    MockCtx.return_value = mock_ctx

    MockTD.return_value = mock_template
    MockWaiter.return_value = True
    MockSeeder.return_value.seed_async = AsyncMock(
        return_value=seeding_result or SeedingResult()
    )

    mock_session = MagicMock()
    mock_session.set_parent = MagicMock()
    mock_session.commit_async = AsyncMock()
    MockSaveSession.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    MockSaveSession.return_value.__aexit__ = AsyncMock(return_value=None)


# ---------------------------------------------------------------------------
# Shared patch context
# ---------------------------------------------------------------------------


def _integration_patches():
    """Return the common set of patches needed for integration tests.

    Patches:
    - ResolutionContext at engine module level
    - discover_template_async at core.creation module level
    - wait_for_subtasks_async at lifecycle.creation module level
    - AutoCascadeSeeder at creation module level
    - SaveSession at its source module (lazy import in creation.py)
    """
    return {
        "resolution_context": patch("autom8_asana.lifecycle.engine.ResolutionContext"),
        "template_discovery": patch(
            "autom8_asana.lifecycle.creation.discover_template_async"
        ),
        "subtask_waiter": patch(
            "autom8_asana.lifecycle.creation.wait_for_subtasks_async"
        ),
        "auto_cascade_seeder": patch(
            "autom8_asana.lifecycle.creation.AutoCascadeSeeder"
        ),
        "save_session": patch("autom8_asana.persistence.session.SaveSession"),
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client() -> MagicMock:
    """Comprehensive mock Asana client for integration tests."""
    return _make_mock_client()


@pytest.fixture
def mock_business() -> MagicMock:
    return _make_mock_business()


@pytest.fixture
def mock_unit() -> MagicMock:
    return _make_mock_unit()


@pytest.fixture
def mock_offer() -> MagicMock:
    return _make_mock_offer()


@pytest.fixture
def mock_ctx(
    mock_business: MagicMock,
    mock_unit: MagicMock,
    mock_offer: MagicMock,
) -> AsyncMock:
    return _make_mock_context(mock_business, mock_unit, mock_offer)


# ---------------------------------------------------------------------------
# Test: Sales CONVERTED -> Onboarding
# ---------------------------------------------------------------------------


class TestSalesConvertedToOnboarding:
    """Sales CONVERTED transition: template creation, section cascade,
    auto-complete source, create_comment init action."""

    @pytest.mark.asyncio
    async def test_full_pipeline(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
        mock_ctx: AsyncMock,
    ) -> None:
        """Sales CONVERTED -> Onboarding runs all 4 phases successfully."""
        process = _make_mock_process(
            ProcessType.SALES,
            "1200944186565610",
            "Sales Pipeline",
        )

        mock_template = _make_mock_task("template_gid", "Template - [Business Name]")

        patches = _integration_patches()
        with (
            patches["resolution_context"] as MockCtx,
            patches["template_discovery"] as MockTD,
            patches["subtask_waiter"] as MockWaiter,
            patches["auto_cascade_seeder"] as MockSeeder,
            patches["save_session"] as MockSaveSession,
        ):
            _configure_standard_patches(
                mock_ctx,
                mock_template,
                MockCtx,
                MockTD,
                MockWaiter,
                MockSeeder,
                MockSaveSession,
                seeding_result=SeedingResult(
                    fields_seeded=["Vertical", "Rep"],
                    fields_skipped=[],
                    warnings=[],
                ),
            )

            engine = LifecycleEngine(mock_client, lifecycle_config)
            result = await engine.handle_transition_async(process, "converted")

        # Verify success
        assert result.success is True
        assert result.error == "" or result.error is None

        # Verify actions: create + configure + comment
        assert "create_process" in result.actions_executed
        assert "init_create_comment" in result.actions_executed

        # Verify entity was created
        assert len(result.entities_created) >= 1
        assert "new_process_gid" in result.entities_created

        # Auto-complete: Sales has auto_complete_prior=true
        assert "auto_complete_source" in result.actions_executed

        # Comment was created on the new process
        mock_client.stories.create_comment_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_rule_id_reflects_transition(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
        mock_ctx: AsyncMock,
    ) -> None:
        """Result rule_id contains source and target stage names."""
        process = _make_mock_process(
            ProcessType.SALES,
            "1200944186565610",
            "Sales Pipeline",
        )
        mock_template = _make_mock_task("t1", "Template - [Business Name]")

        patches = _integration_patches()
        with (
            patches["resolution_context"] as MockCtx,
            patches["template_discovery"] as MockTD,
            patches["subtask_waiter"] as MockWaiter,
            patches["auto_cascade_seeder"] as MockSeeder,
            patches["save_session"] as MockSaveSession,
        ):
            _configure_standard_patches(
                mock_ctx,
                mock_template,
                MockCtx,
                MockTD,
                MockWaiter,
                MockSeeder,
                MockSaveSession,
            )

            engine = LifecycleEngine(mock_client, lifecycle_config)
            result = await engine.handle_transition_async(process, "converted")

        assert "sales" in result.rule_id
        assert "onboarding" in result.rule_id


# ---------------------------------------------------------------------------
# Test: Onboarding CONVERTED -> Implementation
# ---------------------------------------------------------------------------


class TestOnboardingConvertedToImplementation:
    """Onboarding CONVERTED: template creation, computed fields (Launch Date=today),
    play_creation (BOAB), entity_creation (AssetEdit), products_check, create_comment."""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_init_actions(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
        mock_ctx: AsyncMock,
        mock_business: MagicMock,
    ) -> None:
        """Onboarding CONVERTED -> Implementation runs all phases including init actions."""
        process = _make_mock_process(
            ProcessType.ONBOARDING,
            "1201319387632570",
            "Onboarding Pipeline",
            name="Onboarding - Test Business",
        )
        # Products check needs a products field on business
        mock_business.products = ["Video Production"]

        mock_template = _make_mock_task("impl_template", "Template - [Business Name]")
        mock_play_template = _make_mock_task("play_template", "BOAB Template")

        # Need separate duplicate_async returns for process vs play vs entity
        duplicate_results = iter(
            [
                _make_mock_task("new_process_gid", "Impl Process"),
                _make_mock_task("play_gid", "BOAB - Test Business"),
                _make_mock_task("asset_edit_gid", "AssetEdit - Test Business"),
                _make_mock_task("videography_gid", "Videography - Test Business"),
            ]
        )

        async def _duplicate_side_effect(*args, **kwargs):
            return next(duplicate_results)

        mock_client.tasks.duplicate_async = AsyncMock(
            side_effect=_duplicate_side_effect
        )

        # get_async for play creation: task with no dependencies
        mock_task_no_deps = MagicMock()
        mock_task_no_deps.custom_fields = []
        mock_task_no_deps.dependencies = []
        mock_client.tasks.get_async = AsyncMock(return_value=mock_task_no_deps)

        patches = _integration_patches()
        with (
            patches["resolution_context"] as MockCtx,
            patches["template_discovery"] as MockTD,
            patches["subtask_waiter"] as MockWaiter,
            patches["auto_cascade_seeder"] as MockSeeder,
            patches["save_session"] as MockSaveSession,
        ):
            MockCtx.return_value = mock_ctx

            # discover_template_async returns templates for each creation call
            template_results = iter(
                [
                    mock_template,  # process creation
                    mock_play_template,  # play creation
                    mock_template,  # entity creation (AssetEdit)
                    mock_template,  # videography (products_check)
                ]
            )

            async def _find_template(*args, **kwargs):
                try:
                    return next(template_results)
                except StopIteration:
                    return mock_template

            MockTD.side_effect = _find_template
            MockWaiter.return_value = True
            MockSeeder.return_value.seed_async = AsyncMock(
                return_value=SeedingResult(
                    fields_seeded=["Launch Date", "Vertical"],
                    fields_skipped=[],
                    warnings=[],
                )
            )

            mock_session = MagicMock()
            mock_session.set_parent = MagicMock()
            mock_session.commit_async = AsyncMock()
            MockSaveSession.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            MockSaveSession.return_value.__aexit__ = AsyncMock(return_value=None)

            engine = LifecycleEngine(mock_client, lifecycle_config)
            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True

        # Process creation
        assert "create_process" in result.actions_executed

        # Auto-complete (onboarding has auto_complete_prior=true)
        assert "auto_complete_source" in result.actions_executed

        # Init actions: products_check, create_comment
        assert "init_create_comment" in result.actions_executed

        # Entities created should include the new process at minimum
        assert len(result.entities_created) >= 1

    @pytest.mark.asyncio
    async def test_pre_validation_warn_mode(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
        mock_ctx: AsyncMock,
    ) -> None:
        """Onboarding has pre_transition validation in warn mode for Contact Phone."""
        process = _make_mock_process(
            ProcessType.ONBOARDING,
            "1201319387632570",
            "Onboarding Pipeline",
        )
        # contact_phone not set => validation warning but continues
        process.contact_phone = None

        mock_template = _make_mock_task("t1", "Template - [Business Name]")

        patches = _integration_patches()
        with (
            patches["resolution_context"] as MockCtx,
            patches["template_discovery"] as MockTD,
            patches["subtask_waiter"] as MockWaiter,
            patches["auto_cascade_seeder"] as MockSeeder,
            patches["save_session"] as MockSaveSession,
        ):
            _configure_standard_patches(
                mock_ctx,
                mock_template,
                MockCtx,
                MockTD,
                MockWaiter,
                MockSeeder,
                MockSaveSession,
            )

            engine = LifecycleEngine(mock_client, lifecycle_config)
            result = await engine.handle_transition_async(process, "converted")

        # Should still succeed despite missing field (warn mode, not block)
        assert result.success is True
        assert "pre_validation" in result.actions_executed


# ---------------------------------------------------------------------------
# Test: Implementation CONVERTED -> Terminal
# ---------------------------------------------------------------------------


class TestImplementationConvertedTerminal:
    """Implementation CONVERTED has no target stage -- terminal handling."""

    @pytest.mark.asyncio
    async def test_terminal_transition(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
    ) -> None:
        """Implementation CONVERTED produces terminal result with auto-complete."""
        process = _make_mock_process(
            ProcessType.IMPLEMENTATION,
            "1201476141989746",
            "Implementation Pipeline",
            name="Impl - Test Business",
        )

        engine = LifecycleEngine(mock_client, lifecycle_config)
        result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        assert "terminal" in result.actions_executed
        # Implementation has auto_complete_prior=true
        assert "auto_complete_source" in result.actions_executed
        # No entities created for terminal transitions
        assert len(result.entities_created) == 0
        assert "implementation" in result.rule_id
        assert "terminal" in result.rule_id


# ---------------------------------------------------------------------------
# Test: Outreach CONVERTED -> Sales
# ---------------------------------------------------------------------------


class TestOutreachConvertedToSales:
    """Outreach CONVERTED -> Sales: template creation, section cascade, create_comment."""

    @pytest.mark.asyncio
    async def test_full_pipeline(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
        mock_ctx: AsyncMock,
    ) -> None:
        """Outreach CONVERTED -> Sales creates process with comment."""
        process = _make_mock_process(
            ProcessType.OUTREACH,
            "1201753128450029",
            "Outreach Pipeline",
            name="Outreach - Test Business",
        )

        mock_template = _make_mock_task("sales_template", "Template - [Business Name]")

        patches = _integration_patches()
        with (
            patches["resolution_context"] as MockCtx,
            patches["template_discovery"] as MockTD,
            patches["subtask_waiter"] as MockWaiter,
            patches["auto_cascade_seeder"] as MockSeeder,
            patches["save_session"] as MockSaveSession,
        ):
            _configure_standard_patches(
                mock_ctx,
                mock_template,
                MockCtx,
                MockTD,
                MockWaiter,
                MockSeeder,
                MockSaveSession,
            )

            engine = LifecycleEngine(mock_client, lifecycle_config)
            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        assert "create_process" in result.actions_executed
        assert "init_create_comment" in result.actions_executed
        assert "new_process_gid" in result.entities_created

        # Outreach has auto_complete_prior=false
        assert "auto_complete_source" not in result.actions_executed


# ---------------------------------------------------------------------------
# Test: Sales DNC -> Outreach (create_new)
# ---------------------------------------------------------------------------


class TestSalesDncCreateNew:
    """Sales DNC -> Outreach: create_new routing, standard pipeline."""

    @pytest.mark.asyncio
    async def test_dnc_create_new(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
        mock_ctx: AsyncMock,
    ) -> None:
        """Sales DNC creates new Outreach process via create_new routing."""
        process = _make_mock_process(
            ProcessType.SALES,
            "1200944186565610",
            "Sales Pipeline",
        )

        mock_template = _make_mock_task(
            "outreach_template", "Template - [Business Name]"
        )

        patches = _integration_patches()
        with (
            patches["resolution_context"] as MockCtx,
            patches["template_discovery"] as MockTD,
            patches["subtask_waiter"] as MockWaiter,
            patches["auto_cascade_seeder"] as MockSeeder,
            patches["save_session"] as MockSaveSession,
        ):
            _configure_standard_patches(
                mock_ctx,
                mock_template,
                MockCtx,
                MockTD,
                MockWaiter,
                MockSeeder,
                MockSaveSession,
            )

            engine = LifecycleEngine(mock_client, lifecycle_config)
            result = await engine.handle_transition_async(process, "did_not_convert")

        assert result.success is True
        assert "create_process" in result.actions_executed
        # Sales DNC -> Outreach: Outreach has create_comment init action
        assert "init_create_comment" in result.actions_executed
        assert "new_process_gid" in result.entities_created
        # Rule ID reflects DNC routing
        assert "sales" in result.rule_id
        assert "dnc" in result.rule_id


# ---------------------------------------------------------------------------
# Test: Onboarding DNC -> Sales (reopen)
# ---------------------------------------------------------------------------


class TestOnboardingDncReopen:
    """Onboarding DNC -> Sales: reopen routing, finds and reopens Sales process."""

    @pytest.mark.asyncio
    async def test_dnc_reopen(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
        mock_ctx: AsyncMock,
    ) -> None:
        """Onboarding DNC reopens existing Sales process."""
        process = _make_mock_process(
            ProcessType.ONBOARDING,
            "1201319387632570",
            "Onboarding Pipeline",
            name="Onboarding - Test Business",
        )

        # Set up ProcessHolder with a completed Sales subtask
        mock_process_holder = MagicMock()
        mock_process_holder.gid = "process_holder_gid"
        process.process_holder = mock_process_holder

        # ReopenService lists subtasks and finds Sales process
        mock_sales_subtask = MagicMock()
        mock_sales_subtask.gid = "reopened_sales_gid"
        mock_sales_subtask.name = "Sales - Test Business"
        mock_sales_subtask.completed = True
        mock_sales_subtask.created_at = "2026-01-15T00:00:00Z"
        mock_sales_subtask.custom_fields = [
            {
                "name": "Process Type",
                "display_value": "sales",
            }
        ]

        # Configure subtasks for the holder
        mock_client.tasks.subtasks_async = MagicMock(
            return_value=_make_paginator([mock_sales_subtask])
        )

        # Sections for moving to OPPORTUNITY
        mock_opportunity = _make_mock_task("sec_opp", "OPPORTUNITY")
        mock_client.sections.list_for_project_async = MagicMock(
            return_value=_make_paginator([mock_opportunity])
        )

        patches = _integration_patches()
        with patches["resolution_context"] as MockCtx:
            MockCtx.return_value = mock_ctx

            engine = LifecycleEngine(mock_client, lifecycle_config)
            result = await engine.handle_transition_async(process, "did_not_convert")

        assert result.success is True
        assert "reopen_process" in result.actions_executed
        assert "reopened_sales_gid" in result.entities_updated
        assert "reopen" in result.rule_id

    @pytest.mark.asyncio
    async def test_dnc_reopen_no_candidate(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
        mock_ctx: AsyncMock,
    ) -> None:
        """Onboarding DNC with no Sales process to reopen produces warning."""
        process = _make_mock_process(
            ProcessType.ONBOARDING,
            "1201319387632570",
            "Onboarding Pipeline",
        )
        process.process_holder = MagicMock(gid="ph_gid")

        # Empty subtasks -> no candidate
        mock_client.tasks.subtasks_async = MagicMock(return_value=_make_paginator([]))

        patches = _integration_patches()
        with patches["resolution_context"] as MockCtx:
            MockCtx.return_value = mock_ctx

            engine = LifecycleEngine(mock_client, lifecycle_config)
            result = await engine.handle_transition_async(process, "did_not_convert")

        # Reopen fails but overall result is still success
        # (reopen failure is a warning, not a hard failure)
        assert result.success is True
        assert "reopen_process" not in result.actions_executed


# ---------------------------------------------------------------------------
# Test: Implementation DNC -> Outreach (create_new)
# ---------------------------------------------------------------------------


class TestImplementationDncCreateNew:
    """Implementation DNC -> Outreach: create_new routing with corrected target."""

    @pytest.mark.asyncio
    async def test_dnc_create_new(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
        mock_ctx: AsyncMock,
    ) -> None:
        """Implementation DNC creates new Outreach process (corrected from Sales)."""
        process = _make_mock_process(
            ProcessType.IMPLEMENTATION,
            "1201476141989746",
            "Implementation Pipeline",
            name="Impl - Test Business",
        )

        mock_template = _make_mock_task("t1", "Template - [Business Name]")

        patches = _integration_patches()
        with (
            patches["resolution_context"] as MockCtx,
            patches["template_discovery"] as MockTD,
            patches["subtask_waiter"] as MockWaiter,
            patches["auto_cascade_seeder"] as MockSeeder,
            patches["save_session"] as MockSaveSession,
        ):
            _configure_standard_patches(
                mock_ctx,
                mock_template,
                MockCtx,
                MockTD,
                MockWaiter,
                MockSeeder,
                MockSaveSession,
            )

            engine = LifecycleEngine(mock_client, lifecycle_config)
            result = await engine.handle_transition_async(process, "did_not_convert")

        assert result.success is True
        assert "create_process" in result.actions_executed
        # Target is outreach per corrected YAML
        assert "implementation" in result.rule_id
        assert "outreach" in result.rule_id


# ---------------------------------------------------------------------------
# Test: Outreach DNC -> Outreach (deferred)
# ---------------------------------------------------------------------------


class TestOutreachDncDeferred:
    """Outreach DNC: deferred action, no entity creation."""

    @pytest.mark.asyncio
    async def test_dnc_deferred(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
    ) -> None:
        """Outreach DNC is deferred -- logs and returns with no actions."""
        process = _make_mock_process(
            ProcessType.OUTREACH,
            "1201753128450029",
            "Outreach Pipeline",
        )

        engine = LifecycleEngine(mock_client, lifecycle_config)
        result = await engine.handle_transition_async(process, "did_not_convert")

        assert result.success is True
        assert "dnc_deferred" in result.actions_executed
        assert len(result.entities_created) == 0
        assert "deferred" in result.rule_id


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases: unknown stage, creation failure, init action failure."""

    @pytest.mark.asyncio
    async def test_unknown_stage_returns_error(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
    ) -> None:
        """Process with unknown ProcessType returns error result."""
        process = _make_mock_process(
            ProcessType.GENERIC,
            "unknown_proj",
            "Unknown Pipeline",
        )

        engine = LifecycleEngine(mock_client, lifecycle_config)
        result = await engine.handle_transition_async(process, "converted")

        assert result.success is False
        assert "No stage config" in result.error
        assert "generic" in result.rule_id

    @pytest.mark.asyncio
    async def test_creation_failure_is_hard_failure(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
        mock_ctx: AsyncMock,
    ) -> None:
        """When entity creation fails, the result is a hard failure."""
        process = _make_mock_process(
            ProcessType.SALES,
            "1200944186565610",
            "Sales Pipeline",
        )

        patches = _integration_patches()
        with (
            patches["resolution_context"] as MockCtx,
            patches["template_discovery"] as MockTD,
            patches["subtask_waiter"],
            patches["auto_cascade_seeder"],
            patches["save_session"],
        ):
            MockCtx.return_value = mock_ctx

            # discover_template_async raises an error (bubbles up to creation service)
            MockTD.side_effect = ConnectionError("Asana API unreachable")

            engine = LifecycleEngine(mock_client, lifecycle_config)
            result = await engine.handle_transition_async(process, "converted")

        # Creation failure is a hard failure
        assert result.success is False
        assert (
            "creation failed" in result.error.lower()
            or "asana api" in result.error.lower()
        )

    @pytest.mark.asyncio
    async def test_init_action_failure_is_warning_not_hard_failure(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
        mock_ctx: AsyncMock,
    ) -> None:
        """When an init action fails, the transition still succeeds."""
        process = _make_mock_process(
            ProcessType.SALES,
            "1200944186565610",
            "Sales Pipeline",
        )

        mock_template = _make_mock_task("t1", "Template - [Business Name]")

        # Make comment creation fail
        mock_client.stories.create_comment_async = AsyncMock(
            side_effect=ConnectionError("Comment API down")
        )

        patches = _integration_patches()
        with (
            patches["resolution_context"] as MockCtx,
            patches["template_discovery"] as MockTD,
            patches["subtask_waiter"] as MockWaiter,
            patches["auto_cascade_seeder"] as MockSeeder,
            patches["save_session"] as MockSaveSession,
        ):
            _configure_standard_patches(
                mock_ctx,
                mock_template,
                MockCtx,
                MockTD,
                MockWaiter,
                MockSeeder,
                MockSaveSession,
            )

            engine = LifecycleEngine(mock_client, lifecycle_config)
            result = await engine.handle_transition_async(process, "converted")

        # CommentHandler catches errors and returns success=True (soft fail)
        # So the overall transition should still succeed
        assert result.success is True
        assert "create_process" in result.actions_executed

    @pytest.mark.asyncio
    async def test_pre_validation_block_mode(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
    ) -> None:
        """Pre-validation in block mode prevents the transition.

        Note: Onboarding uses warn mode by default. This test patches
        the validation mode to block to verify the blocking path.
        """
        process = _make_mock_process(
            ProcessType.ONBOARDING,
            "1201319387632570",
            "Onboarding Pipeline",
        )
        process.contact_phone = None

        engine = LifecycleEngine(mock_client, lifecycle_config)

        # Temporarily patch the stage validation mode to block
        stage = lifecycle_config.get_stage("onboarding")
        original_mode = stage.validation.pre_transition.mode
        stage.validation.pre_transition.mode = "block"

        try:
            result = await engine.handle_transition_async(process, "converted")
        finally:
            stage.validation.pre_transition.mode = original_mode

        assert result.success is False
        assert (
            "validation" in result.rule_id.lower()
            or "validation" in (result.error or "").lower()
        )

    @pytest.mark.asyncio
    async def test_cascade_sections_updates_entities(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
        mock_ctx: AsyncMock,
    ) -> None:
        """Verify that cascading section updates run and update entities."""
        process = _make_mock_process(
            ProcessType.OUTREACH,
            "1201753128450029",
            "Outreach Pipeline",
        )

        mock_template = _make_mock_task("t1", "Template - [Business Name]")

        # Set up section matching with all target sections available
        # Outreach -> Sales cascading_sections: offer="Sales Process", unit="Next Steps", business="OPPORTUNITY"
        all_sections = [
            _make_mock_task("sec_sales_process", "Sales Process"),
            _make_mock_task("sec_next_steps", "Next Steps"),
            _make_mock_task("sec_engaged", "Engaged"),
            _make_mock_task("sec_opp", "OPPORTUNITY"),
            _make_mock_task("sec_template", "TEMPLATE"),
        ]

        mock_client.sections.list_for_project_async = MagicMock(
            return_value=_make_paginator(all_sections)
        )

        patches = _integration_patches()
        with (
            patches["resolution_context"] as MockCtx,
            patches["template_discovery"] as MockTD,
            patches["subtask_waiter"] as MockWaiter,
            patches["auto_cascade_seeder"] as MockSeeder,
            patches["save_session"] as MockSaveSession,
        ):
            _configure_standard_patches(
                mock_ctx,
                mock_template,
                MockCtx,
                MockTD,
                MockWaiter,
                MockSeeder,
                MockSaveSession,
            )

            engine = LifecycleEngine(mock_client, lifecycle_config)
            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        # Outreach -> Sales cascading_sections: offer="Sales Process", unit="Engaged", business="OPPORTUNITY"
        assert "cascade_sections" in result.actions_executed
        # All three entities should be updated
        assert len(result.entities_updated) >= 3

    @pytest.mark.asyncio
    async def test_wiring_phase_runs(
        self,
        lifecycle_config: LifecycleConfig,
        mock_client: MagicMock,
        mock_ctx: AsyncMock,
    ) -> None:
        """Verify Phase 4 (WIRE) runs and wires dependencies."""
        process = _make_mock_process(
            ProcessType.SALES,
            "1200944186565610",
            "Sales Pipeline",
        )

        mock_template = _make_mock_task("t1", "Template - [Business Name]")

        patches = _integration_patches()
        with (
            patches["resolution_context"] as MockCtx,
            patches["template_discovery"] as MockTD,
            patches["subtask_waiter"] as MockWaiter,
            patches["auto_cascade_seeder"] as MockSeeder,
            patches["save_session"] as MockSaveSession,
        ):
            _configure_standard_patches(
                mock_ctx,
                mock_template,
                MockCtx,
                MockTD,
                MockWaiter,
                MockSeeder,
                MockSaveSession,
            )

            engine = LifecycleEngine(mock_client, lifecycle_config)
            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        # Wiring should have been attempted (unit dependent + offer_holder dependent)
        assert mock_client.tasks.add_dependent_async.called
        assert "wire_dependencies" in result.actions_executed
