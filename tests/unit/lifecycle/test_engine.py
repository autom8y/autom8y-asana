"""Tests for LifecycleEngine.

Per TDD-lifecycle-engine-hardening Section 2.2:
- CONVERTED routing for all 4 stages
- DNC routing: create_new, reopen, deferred
- Auto-completion per-transition flag
- Result accumulator: hard failure vs soft failure (warnings)
- Phase ordering: Create -> Configure -> Actions -> Wire
- Invalid stage name -> error result
- Terminal transitions
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.lifecycle.engine import (
    ActionResult,
    CascadeResult,
    CompletionResult,
    CreationResult,
    LifecycleEngine,
    ReopenResult,
    TransitionResult,
    WiringResult,
)
from autom8_asana.models.business.process import ProcessType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_process(
    process_type: ProcessType,
    gid: str = "src_123",
    name: str = "Test Process",
) -> MagicMock:
    """Create a mock Process with the given type."""
    process = MagicMock()
    process.gid = gid
    process.name = name
    process.process_type = process_type
    process.completed = False
    process.memberships = []
    return process


def _make_mock_services(
    *,
    creation_success: bool = True,
    creation_gid: str = "new_456",
    creation_error: str = "",
    cascade_updates: list[str] | None = None,
    completion_completed: list[str] | None = None,
    action_results: list[ActionResult] | None = None,
    wiring_wired: list[str] | None = None,
    reopen_success: bool = True,
    reopen_gid: str = "reopened_789",
    reopen_error: str = "",
) -> dict:
    """Create mock services matching engine protocols."""
    creation_service = AsyncMock()
    creation_service.create_process_async = AsyncMock(
        return_value=CreationResult(
            success=creation_success,
            entity_gid=creation_gid,
            error=creation_error,
        )
    )

    section_service = AsyncMock()
    section_service.cascade_async = AsyncMock(
        return_value=CascadeResult(updates=cascade_updates or [])
    )

    completion_service = AsyncMock()
    completion_service.complete_source_async = AsyncMock(
        return_value=CompletionResult(completed=completion_completed or [])
    )

    init_action_registry = AsyncMock()
    init_action_registry.execute_actions_async = AsyncMock(
        return_value=action_results or []
    )

    wiring_service = AsyncMock()
    wiring_service.wire_defaults_async = AsyncMock(
        return_value=WiringResult(wired=wiring_wired or [])
    )

    reopen_service = AsyncMock()
    reopen_service.reopen_async = AsyncMock(
        return_value=ReopenResult(
            success=reopen_success,
            entity_gid=reopen_gid,
            error=reopen_error,
        )
    )

    return {
        "creation_service": creation_service,
        "section_service": section_service,
        "completion_service": completion_service,
        "init_action_registry": init_action_registry,
        "wiring_service": wiring_service,
        "reopen_service": reopen_service,
    }


def _make_engine(
    lifecycle_config,
    mock_client,
    **service_overrides,
) -> LifecycleEngine:
    """Create engine with mock services."""
    services = _make_mock_services(**service_overrides)
    return LifecycleEngine(
        mock_client,
        lifecycle_config,
        creation_service=services["creation_service"],
        section_service=services["section_service"],
        completion_service=services["completion_service"],
        init_action_registry=services["init_action_registry"],
        wiring_service=services["wiring_service"],
        reopen_service=services["reopen_service"],
    )


def _make_engine_with_services(
    lifecycle_config,
    mock_client,
    services: dict,
) -> LifecycleEngine:
    """Create engine with pre-built services dict."""
    return LifecycleEngine(
        mock_client,
        lifecycle_config,
        creation_service=services["creation_service"],
        section_service=services["section_service"],
        completion_service=services["completion_service"],
        init_action_registry=services["init_action_registry"],
        wiring_service=services["wiring_service"],
        reopen_service=services["reopen_service"],
    )


# ---------------------------------------------------------------------------
# TransitionResult unit tests
# ---------------------------------------------------------------------------


class TestTransitionResult:
    """Tests for the TransitionResult accumulator."""

    def test_initial_state_is_success(self):
        result = TransitionResult("gid1")
        assert result.success is True
        assert result.hard_failure is None
        assert result.actions_executed == []
        assert result.entities_created == []
        assert result.entities_updated == []
        assert result.warnings == []

    def test_add_warning_does_not_block_success(self):
        result = TransitionResult("gid1")
        result.add_warning("some warning")
        assert result.success is True
        assert result.warnings == ["some warning"]

    def test_fail_blocks_success(self):
        result = TransitionResult("gid1")
        result.fail("hard error")
        assert result.success is False
        assert result.hard_failure == "hard error"

    def test_add_action(self):
        result = TransitionResult("gid1")
        result.add_action("create_process")
        result.add_action("cascade_sections")
        assert result.actions_executed == ["create_process", "cascade_sections"]

    def test_add_entity_created(self):
        result = TransitionResult("gid1")
        result.add_entity_created("new1")
        result.add_entity_created("new2")
        assert result.entities_created == ["new1", "new2"]

    def test_add_entity_updated(self):
        result = TransitionResult("gid1")
        result.add_entity_updated("upd1")
        assert result.entities_updated == ["upd1"]

    def test_success_with_warnings_still_success(self):
        """FR-ERR-001: soft failures do not prevent success."""
        result = TransitionResult("gid1")
        result.add_warning("seeding missed a field")
        result.add_warning("comment creation failed")
        result.add_action("create_process")
        assert result.success is True


# ---------------------------------------------------------------------------
# CONVERTED routing tests (FR-ROUTE-001..004)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestConvertedRouting:
    """CONVERTED transitions for all 4 stages."""

    async def test_outreach_converted_to_sales(self, lifecycle_config, mock_client):
        """FR-ROUTE-001: Outreach CONVERTED creates Sales."""
        process = _make_mock_process(ProcessType.OUTREACH)
        engine = _make_engine(lifecycle_config, mock_client)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        assert "create_process" in result.actions_executed
        assert "new_456" in result.entities_created
        assert "lifecycle_outreach_to_sales" == result.rule_id

    async def test_sales_converted_to_onboarding(self, lifecycle_config, mock_client):
        """FR-ROUTE-002: Sales CONVERTED creates Onboarding (PCR absorption)."""
        process = _make_mock_process(ProcessType.SALES)
        engine = _make_engine(
            lifecycle_config,
            mock_client,
            cascade_updates=["offer1", "unit1"],
            completion_completed=["src_123"],
        )

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        assert "create_process" in result.actions_executed
        assert "cascade_sections" in result.actions_executed
        assert "auto_complete_source" in result.actions_executed
        assert "lifecycle_sales_to_onboarding" == result.rule_id
        assert "offer1" in result.entities_updated
        assert "unit1" in result.entities_updated

    async def test_onboarding_converted_to_implementation(
        self, lifecycle_config, mock_client
    ):
        """FR-ROUTE-003: Onboarding CONVERTED creates Implementation."""
        process = _make_mock_process(ProcessType.ONBOARDING)
        # Onboarding has pre-validation for "Contact Phone" (mode=warn)
        # The mock process won't have it, so validation warning expected
        engine = _make_engine(
            lifecycle_config,
            mock_client,
            completion_completed=["src_123"],
        )

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        assert "create_process" in result.actions_executed
        assert "pre_validation" in result.actions_executed
        assert "lifecycle_onboarding_to_implementation" == result.rule_id

    async def test_implementation_converted_terminal(
        self, lifecycle_config, mock_client
    ):
        """FR-ROUTE-004: Implementation CONVERTED is terminal."""
        process = _make_mock_process(ProcessType.IMPLEMENTATION)
        engine = _make_engine(
            lifecycle_config,
            mock_client,
            completion_completed=["src_123"],
        )

        result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        assert "terminal" in result.actions_executed
        # Implementation has auto_complete_prior: true
        assert "auto_complete_source" in result.actions_executed
        assert "lifecycle_implementation_terminal" == result.rule_id
        assert result.entities_created == []


# ---------------------------------------------------------------------------
# DNC routing tests (FR-DNC-001..004)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDncRouting:
    """DID NOT CONVERT routing for all stage types."""

    async def test_sales_dnc_creates_outreach(self, lifecycle_config, mock_client):
        """FR-DNC-001: Sales DNC creates new Outreach (create_new)."""
        process = _make_mock_process(ProcessType.SALES)
        engine = _make_engine(lifecycle_config, mock_client)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "did_not_convert")

        assert result.success is True
        assert "create_process" in result.actions_executed
        assert "new_456" in result.entities_created
        assert "lifecycle_sales_dnc_outreach" == result.rule_id

    async def test_onboarding_dnc_reopens_sales(self, lifecycle_config, mock_client):
        """FR-DNC-002: Onboarding DNC reopens Sales (reopen)."""
        process = _make_mock_process(ProcessType.ONBOARDING)
        engine = _make_engine(
            lifecycle_config,
            mock_client,
            reopen_success=True,
            reopen_gid="sales_999",
        )

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "did_not_convert")

        assert result.success is True
        assert "reopen_process" in result.actions_executed
        assert "sales_999" in result.entities_updated
        assert "lifecycle_onboarding_dnc_reopen" == result.rule_id
        # No entities created for reopen
        assert result.entities_created == []

    async def test_implementation_dnc_creates_outreach(
        self, lifecycle_config, mock_client
    ):
        """FR-DNC-003: Implementation DNC creates new Outreach (create_new)."""
        process = _make_mock_process(ProcessType.IMPLEMENTATION)
        engine = _make_engine(lifecycle_config, mock_client)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "did_not_convert")

        assert result.success is True
        assert "create_process" in result.actions_executed
        assert "lifecycle_implementation_dnc_outreach" == result.rule_id

    async def test_outreach_dnc_deferred(self, lifecycle_config, mock_client):
        """FR-DNC-004: Outreach DNC is deferred (self-loop out of scope)."""
        process = _make_mock_process(ProcessType.OUTREACH)
        engine = _make_engine(lifecycle_config, mock_client)

        result = await engine.handle_transition_async(process, "did_not_convert")

        assert result.success is True
        assert "dnc_deferred" in result.actions_executed
        assert "lifecycle_outreach_dnc_deferred" == result.rule_id
        # No creation, no reopen
        assert result.entities_created == []
        assert result.entities_updated == []


# ---------------------------------------------------------------------------
# Auto-completion tests (FR-COMPLETE-001)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAutoCompletion:
    """Auto-completion per-transition flag."""

    async def test_auto_complete_triggered_when_true(
        self, lifecycle_config, mock_client
    ):
        """Sales has auto_complete_prior: true."""
        process = _make_mock_process(ProcessType.SALES)
        services = _make_mock_services(
            completion_completed=["src_123"],
        )
        engine = _make_engine_with_services(lifecycle_config, mock_client, services)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        assert "auto_complete_source" in result.actions_executed
        services["completion_service"].complete_source_async.assert_called_once()

    async def test_auto_complete_not_triggered_when_false(
        self, lifecycle_config, mock_client
    ):
        """Outreach has auto_complete_prior: false."""
        process = _make_mock_process(ProcessType.OUTREACH)
        services = _make_mock_services()
        engine = _make_engine_with_services(lifecycle_config, mock_client, services)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        assert "auto_complete_source" not in result.actions_executed
        services["completion_service"].complete_source_async.assert_not_called()


# ---------------------------------------------------------------------------
# Result accumulator tests (FR-ERR-001)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestResultAccumulator:
    """Result accumulation: hard failures vs soft failures."""

    async def test_creation_success_with_soft_failures_is_overall_success(
        self, lifecycle_config, mock_client
    ):
        """FR-ERR-001 AC-3: success if creation succeeded + soft failures."""
        process = _make_mock_process(ProcessType.SALES)
        services = _make_mock_services(
            cascade_updates=["offer1"],
        )
        # Make init actions return a failure (soft)
        services["init_action_registry"].execute_actions_async = AsyncMock(
            return_value=[
                ActionResult(success=True, entity_gid=""),
                ActionResult(success=False, error="comment handler not found"),
            ]
        )
        engine = _make_engine_with_services(lifecycle_config, mock_client, services)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        # Overall success because creation succeeded
        assert result.success is True
        assert "create_process" in result.actions_executed

    async def test_creation_failure_is_overall_failure(
        self, lifecycle_config, mock_client
    ):
        """Creation failure -> overall failure."""
        process = _make_mock_process(ProcessType.SALES)
        engine = _make_engine(
            lifecycle_config,
            mock_client,
            creation_success=False,
            creation_error="Template not found",
        )

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.success is False
        assert "Process creation failed" in result.error

    async def test_exception_in_service_returns_failure(
        self, lifecycle_config, mock_client
    ):
        """Unhandled exception in pipeline -> overall failure."""
        process = _make_mock_process(ProcessType.SALES)
        services = _make_mock_services()
        services["creation_service"].create_process_async = AsyncMock(
            side_effect=RuntimeError("Network error")
        )
        engine = _make_engine_with_services(lifecycle_config, mock_client, services)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.success is False
        assert "Network error" in result.error

    async def test_section_failure_is_soft_failure(self, lifecycle_config, mock_client):
        """Section cascade exception -> warning, not hard failure."""
        process = _make_mock_process(ProcessType.SALES)
        services = _make_mock_services()
        services["section_service"].cascade_async = AsyncMock(
            side_effect=RuntimeError("Section API down")
        )
        engine = _make_engine_with_services(lifecycle_config, mock_client, services)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        # Success despite section failure
        assert result.success is True
        assert "create_process" in result.actions_executed

    async def test_wiring_failure_is_soft_failure(self, lifecycle_config, mock_client):
        """Wiring exception -> warning, not hard failure."""
        process = _make_mock_process(ProcessType.SALES)
        services = _make_mock_services()
        services["wiring_service"].wire_defaults_async = AsyncMock(
            side_effect=RuntimeError("Wiring API down")
        )
        engine = _make_engine_with_services(lifecycle_config, mock_client, services)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        assert "create_process" in result.actions_executed


# ---------------------------------------------------------------------------
# Invalid stage / error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestErrorHandling:
    """Error conditions and edge cases."""

    async def test_invalid_stage_name_returns_error(
        self, lifecycle_config, mock_client
    ):
        """Unknown process type -> error result."""
        process = _make_mock_process(ProcessType.GENERIC)
        engine = _make_engine(lifecycle_config, mock_client)

        result = await engine.handle_transition_async(process, "converted")

        assert result.success is False
        assert "No stage config for" in result.error

    async def test_dnc_reopen_failure_is_warning(self, lifecycle_config, mock_client):
        """Reopen service failure is a warning, not hard failure."""
        process = _make_mock_process(ProcessType.ONBOARDING)
        engine = _make_engine(
            lifecycle_config,
            mock_client,
            reopen_success=False,
            reopen_error="No Sales process found",
        )

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "did_not_convert")

        # Reopen failure is not a hard failure (fail-forward)
        assert result.success is True
        assert "reopen_process" not in result.actions_executed

    async def test_dnc_reopen_exception_is_warning(self, lifecycle_config, mock_client):
        """Reopen service exception -> warning, not crash."""
        process = _make_mock_process(ProcessType.ONBOARDING)
        services = _make_mock_services()
        services["reopen_service"].reopen_async = AsyncMock(
            side_effect=RuntimeError("Reopen boom")
        )
        engine = _make_engine_with_services(lifecycle_config, mock_client, services)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "did_not_convert")

        assert result.success is True


# ---------------------------------------------------------------------------
# Phase ordering tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPhaseOrdering:
    """Verify phase execution order: Create -> Configure -> Actions -> Wire."""

    async def test_phase_order_create_before_configure(
        self, lifecycle_config, mock_client
    ):
        """Phase 1 (Create) runs before Phase 2 (Configure)."""
        call_order = []

        services = _make_mock_services(
            cascade_updates=["offer1"],
            completion_completed=["old1"],
        )

        async def track_creation(*args, **kwargs):
            call_order.append("create")
            return CreationResult(success=True, entity_gid="new_456")

        async def track_cascade(*args, **kwargs):
            call_order.append("configure_sections")
            return CascadeResult(updates=["offer1"])

        async def track_completion(*args, **kwargs):
            call_order.append("configure_completion")
            return CompletionResult(completed=["old1"])

        async def track_actions(*args, **kwargs):
            call_order.append("actions")
            return [ActionResult(success=True)]

        async def track_wiring(*args, **kwargs):
            call_order.append("wire")
            return WiringResult(wired=["dep1"])

        services["creation_service"].create_process_async = AsyncMock(
            side_effect=track_creation
        )
        services["section_service"].cascade_async = AsyncMock(side_effect=track_cascade)
        services["completion_service"].complete_source_async = AsyncMock(
            side_effect=track_completion
        )
        services["init_action_registry"].execute_actions_async = AsyncMock(
            side_effect=track_actions
        )
        services["wiring_service"].wire_defaults_async = AsyncMock(
            side_effect=track_wiring
        )

        engine = _make_engine_with_services(lifecycle_config, mock_client, services)

        # Sales has auto_complete_prior: true and init_actions
        process = _make_mock_process(ProcessType.SALES)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        # Verify order: create -> configure (sections, completion) -> actions -> wire
        assert call_order.index("create") < call_order.index("configure_sections")
        assert call_order.index("configure_sections") < call_order.index("actions")
        assert call_order.index("actions") < call_order.index("wire")

    async def test_creation_failure_skips_later_phases(
        self, lifecycle_config, mock_client
    ):
        """If Phase 1 fails, Phases 2-4 are skipped."""
        services = _make_mock_services(
            creation_success=False,
            creation_error="No template",
        )
        engine = _make_engine_with_services(lifecycle_config, mock_client, services)

        process = _make_mock_process(ProcessType.SALES)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.success is False
        # Phase 2+ services should NOT have been called
        services["section_service"].cascade_async.assert_not_called()
        services["completion_service"].complete_source_async.assert_not_called()
        services["init_action_registry"].execute_actions_async.assert_not_called()
        services["wiring_service"].wire_defaults_async.assert_not_called()


# ---------------------------------------------------------------------------
# Terminal transition tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestTerminalTransitions:
    """Terminal state handling."""

    async def test_implementation_converted_is_terminal(
        self, lifecycle_config, mock_client
    ):
        """Implementation CONVERTED has no target -> terminal result."""
        process = _make_mock_process(ProcessType.IMPLEMENTATION)
        engine = _make_engine(lifecycle_config, mock_client)

        result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        assert "terminal" in result.actions_executed
        assert result.rule_id == "lifecycle_implementation_terminal"

    async def test_terminal_with_auto_complete(self, lifecycle_config, mock_client):
        """Terminal transition with auto_complete_prior: true.

        D-LC-004 fix: _handle_terminal_async now calls CompletionService
        instead of just recording the action. The mock must return a
        non-empty completed list for the action to be recorded.
        """
        process = _make_mock_process(ProcessType.IMPLEMENTATION)
        services = _make_mock_services(
            completion_completed=["src_123"],
        )
        engine = _make_engine_with_services(lifecycle_config, mock_client, services)

        result = await engine.handle_transition_async(process, "converted")

        # Implementation has auto_complete_prior: true
        assert "auto_complete_source" in result.actions_executed
        assert "terminal" in result.actions_executed
        # D-LC-004: CompletionService is now actually called
        services["completion_service"].complete_source_async.assert_called_once_with(
            process
        )
        assert "src_123" in result.entities_updated

    async def test_month1_terminal(self, lifecycle_config, mock_client):
        """Month1 CONVERTED is also terminal (converted: null)."""
        process = _make_mock_process(ProcessType.MONTH1)
        engine = _make_engine(lifecycle_config, mock_client)

        result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        assert "terminal" in result.actions_executed
        assert "lifecycle_month1_terminal" == result.rule_id


# ---------------------------------------------------------------------------
# DNC create_new pipeline tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDncCreateNewPipeline:
    """DNC create_new uses the same 4-phase pipeline as CONVERTED."""

    async def test_dnc_create_new_runs_full_pipeline(
        self, lifecycle_config, mock_client
    ):
        """Sales DNC -> Outreach runs all 4 phases."""
        services = _make_mock_services(
            cascade_updates=["offer1"],
            wiring_wired=["dep1"],
        )
        engine = _make_engine_with_services(lifecycle_config, mock_client, services)
        process = _make_mock_process(ProcessType.SALES)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "did_not_convert")

        assert result.success is True
        # All phases should have been called
        services["creation_service"].create_process_async.assert_called_once()
        services["section_service"].cascade_async.assert_called_once()
        services["wiring_service"].wire_defaults_async.assert_called_once()

    async def test_dnc_create_new_creation_failure(self, lifecycle_config, mock_client):
        """DNC create_new with creation failure -> overall failure."""
        engine = _make_engine(
            lifecycle_config,
            mock_client,
            creation_success=False,
            creation_error="DNC creation template missing",
        )
        process = _make_mock_process(ProcessType.SALES)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "did_not_convert")

        assert result.success is False
        assert "creation failed" in result.error.lower()


# ---------------------------------------------------------------------------
# Init actions tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestInitActions:
    """Init action execution in Phase 3."""

    async def test_init_actions_executed_for_onboarding(
        self, lifecycle_config, mock_client
    ):
        """Onboarding target has products_check and create_comment."""
        services = _make_mock_services(
            action_results=[
                ActionResult(success=True, entity_gid="vid_123"),
                ActionResult(success=True),
            ],
            completion_completed=["src_123"],
        )
        engine = _make_engine_with_services(lifecycle_config, mock_client, services)
        # Sales CONVERTED -> Onboarding (which has init_actions)
        process = _make_mock_process(ProcessType.SALES)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        assert "init_products_check" in result.actions_executed
        assert "init_create_comment" in result.actions_executed
        assert "vid_123" in result.entities_created

    async def test_failed_init_action_produces_warning(
        self, lifecycle_config, mock_client
    ):
        """Failed init action -> warning, not hard failure."""
        services = _make_mock_services(
            action_results=[
                ActionResult(success=False, error="Handler not found"),
                ActionResult(success=True),
            ],
            completion_completed=["src_123"],
        )
        engine = _make_engine_with_services(lifecycle_config, mock_client, services)
        process = _make_mock_process(ProcessType.SALES)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True  # Soft failure does not block


# ---------------------------------------------------------------------------
# Pre-transition validation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPreTransitionValidation:
    """Onboarding has pre_transition validation (Contact Phone, mode=warn)."""

    async def test_validation_warn_mode_continues(self, lifecycle_config, mock_client):
        """Warn mode: missing fields logged but transition continues."""
        process = _make_mock_process(ProcessType.ONBOARDING)
        # Process doesn't have contact_phone attribute
        engine = _make_engine(lifecycle_config, mock_client)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        assert "pre_validation" in result.actions_executed


# ---------------------------------------------------------------------------
# Structured logging tests (FR-AUDIT-001)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestStructuredLogging:
    """Verify structured audit logging via autom8y_log."""

    async def test_transition_start_logged(self, lifecycle_config, mock_client):
        """Transition start event is logged."""
        process = _make_mock_process(ProcessType.SALES)
        engine = _make_engine(lifecycle_config, mock_client)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            with patch("autom8_asana.lifecycle.engine.logger") as mock_logger:
                await engine.handle_transition_async(process, "converted")

                # Verify structured log calls
                info_calls = [c for c in mock_logger.info.call_args_list]
                event_names = [c[0][0] for c in info_calls]
                assert "lifecycle_transition_start" in event_names
                assert "lifecycle_transition_complete" in event_names

    async def test_dnc_deferred_logged(self, lifecycle_config, mock_client):
        """DNC deferred event is logged."""
        process = _make_mock_process(ProcessType.OUTREACH)
        engine = _make_engine(lifecycle_config, mock_client)

        with patch("autom8_asana.lifecycle.engine.logger") as mock_logger:
            await engine.handle_transition_async(process, "did_not_convert")

            info_calls = [c for c in mock_logger.info.call_args_list]
            event_names = [c[0][0] for c in info_calls]
            assert "lifecycle_dnc_deferred" in event_names

    async def test_error_logged_on_unknown_stage(self, lifecycle_config, mock_client):
        """Unknown stage triggers error log."""
        process = _make_mock_process(ProcessType.GENERIC)
        engine = _make_engine(lifecycle_config, mock_client)

        with patch("autom8_asana.lifecycle.engine.logger") as mock_logger:
            await engine.handle_transition_async(process, "converted")

            error_calls = [c for c in mock_logger.error.call_args_list]
            event_names = [c[0][0] for c in error_calls]
            assert "lifecycle_unknown_stage" in event_names


# ---------------------------------------------------------------------------
# Service protocol injection tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestServiceInjection:
    """Verify services are injectable via constructor kwargs."""

    async def test_injected_services_are_used(self, lifecycle_config, mock_client):
        """Injected mock services are called instead of real ones."""
        services = _make_mock_services(
            creation_gid="injected_001",
            cascade_updates=["injected_offer"],
        )
        engine = _make_engine_with_services(lifecycle_config, mock_client, services)
        process = _make_mock_process(ProcessType.OUTREACH)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.success is True
        assert "injected_001" in result.entities_created
        assert "injected_offer" in result.entities_updated


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestEdgeCases:
    """Edge cases and boundary conditions."""

    async def test_no_init_actions_stage(self, lifecycle_config, mock_client):
        """Stage with empty init_actions skips Phase 3 entirely."""
        services = _make_mock_services()
        engine = _make_engine_with_services(lifecycle_config, mock_client, services)
        # Outreach CONVERTED -> Sales, and Sales has init_actions: [create_comment]
        # But let's test a stage with no init_actions directly:
        # We'll use the month1 terminal case for a clean test
        process = _make_mock_process(ProcessType.MONTH1)

        result = await engine.handle_transition_async(process, "converted")

        # Terminal, so init_action_registry should NOT be called
        services["init_action_registry"].execute_actions_async.assert_not_called()

    async def test_result_has_correct_triggered_by(self, lifecycle_config, mock_client):
        """AutomationResult has correct triggered_by fields."""
        process = _make_mock_process(ProcessType.SALES, gid="specific_gid_123")
        engine = _make_engine(lifecycle_config, mock_client)

        with patch("autom8_asana.lifecycle.engine.ResolutionContext") as MockCtx:
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
            MockCtx.return_value = ctx

            result = await engine.handle_transition_async(process, "converted")

        assert result.triggered_by_gid == "specific_gid_123"
        assert result.triggered_by_type == "Process"

    async def test_execution_time_is_positive(self, lifecycle_config, mock_client):
        """AutomationResult has non-negative execution time."""
        process = _make_mock_process(ProcessType.OUTREACH)
        engine = _make_engine(lifecycle_config, mock_client)

        result = await engine.handle_transition_async(process, "did_not_convert")

        assert result.execution_time_ms >= 0
