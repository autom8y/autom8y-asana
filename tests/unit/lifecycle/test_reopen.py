"""Tests for ReopenService -- DNC reopen mechanics.

Coverage targets:
- Happy path: ProcessHolder has a Sales process -> reopen succeeds
- Most recent selection: Multiple Sales processes -> picks most recent
- No candidates: No matching ProcessType -> returns failure
- No ProcessHolder: source_process has no process_holder -> uses resolve_holder_async
- resolve_holder_async returns None -> "Cannot resolve" error
- Mark incomplete called: tasks.update_async called with completed=False
- Section move: sections API called to move to OPPORTUNITY
- Section not found: target section doesn't exist -> graceful no-op
- API error: Exception during reopen -> caught, returns failure
- ProcessType matching: Case-insensitive, both dict and object formats
- No project_gid: Skips section move when target_stage has no project_gid
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.lifecycle.config import StageConfig, TransitionConfig
from autom8_asana.lifecycle.reopen import ReopenResult, ReopenService

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_stage_config(**overrides: Any) -> StageConfig:
    """Create a minimal StageConfig for testing."""
    defaults = {
        "name": "sales",
        "project_gid": "1200944186565610",
        "target_section": "OPPORTUNITY",
        "transitions": TransitionConfig(converted="onboarding"),
    }
    defaults.update(overrides)
    return StageConfig(**defaults)


def _make_mock_client() -> MagicMock:
    """Build a mock AsanaClient with standard sub-clients."""
    client = MagicMock()

    # Tasks sub-client
    client.tasks = MagicMock()
    client.tasks.update_async = AsyncMock()

    # subtasks_async returns a paginator with .collect()
    subtasks_paginator = MagicMock()
    subtasks_paginator.collect = AsyncMock(return_value=[])
    client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

    # Sections sub-client
    client.sections = MagicMock()
    sections_paginator = MagicMock()
    sections_paginator.collect = AsyncMock(return_value=[])
    client.sections.list_for_project_async = MagicMock(
        return_value=sections_paginator,
    )
    client.sections.add_task_async = AsyncMock()

    return client


def _make_mock_ctx(holder: Any = None) -> AsyncMock:
    """Build a mock ResolutionContext."""
    ctx = AsyncMock()
    ctx.resolve_holder_async = AsyncMock(return_value=holder)
    ctx.__aenter__ = AsyncMock(return_value=ctx)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


def _make_task(
    gid: str,
    created_at: str = "2025-01-15T00:00:00.000Z",
    process_type_value: str = "Sales",
    *,
    use_dict_custom_fields: bool = True,
) -> MagicMock:
    """Build a mock Asana task with ProcessType custom field.

    Args:
        gid: Task GID.
        created_at: ISO timestamp for sorting.
        process_type_value: Display value for ProcessType custom field.
        use_dict_custom_fields: If True, custom_fields are dicts; else objects.
    """
    task = MagicMock()
    task.gid = gid
    task.created_at = created_at
    task.name = f"Process {gid}"

    if use_dict_custom_fields:
        task.custom_fields = [
            {"name": "Process Type", "display_value": process_type_value},
        ]
    else:
        cf = MagicMock()
        cf.name = "Process Type"
        cf.display_value = process_type_value
        task.custom_fields = [cf]

    return task


def _make_section(gid: str, name: str) -> MagicMock:
    """Build a mock section object."""
    section = MagicMock()
    section.gid = gid
    section.name = name
    return section


def _make_holder(gid: str = "holder_gid") -> MagicMock:
    """Build a mock ProcessHolder."""
    holder = MagicMock()
    holder.gid = gid
    return holder


# ------------------------------------------------------------------
# Tests: Happy Path
# ------------------------------------------------------------------


class TestReopenHappyPath:
    """Happy path: ProcessHolder has a Sales process, reopen succeeds."""

    @pytest.mark.asyncio
    async def test_reopen_succeeds_with_matching_process(self) -> None:
        """A single matching Sales process is found, reopened, and moved."""
        client = _make_mock_client()
        stage = _make_stage_config()
        holder = _make_holder()
        sales_task = _make_task("task_001", process_type_value="Sales")

        # Wire subtasks to return the sales task
        subtasks_paginator = MagicMock()
        subtasks_paginator.collect = AsyncMock(return_value=[sales_task])
        client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

        # Wire sections for the move
        opp_section = _make_section("sec_opp", "Opportunity")
        sections_paginator = MagicMock()
        sections_paginator.collect = AsyncMock(return_value=[opp_section])
        client.sections.list_for_project_async = MagicMock(
            return_value=sections_paginator,
        )

        source_process = MagicMock()
        source_process.process_holder = holder

        ctx = _make_mock_ctx()
        service = ReopenService(client)

        result = await service.reopen_async(stage, ctx, source_process)

        assert result.success is True
        assert result.entity_gid == "task_001"
        assert result.error == ""

    @pytest.mark.asyncio
    async def test_mark_incomplete_called(self) -> None:
        """Verify tasks.update_async is called with completed=False."""
        client = _make_mock_client()
        stage = _make_stage_config()
        holder = _make_holder()
        sales_task = _make_task("task_002")

        subtasks_paginator = MagicMock()
        subtasks_paginator.collect = AsyncMock(return_value=[sales_task])
        client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

        # No sections needed (section move tested separately)
        sections_paginator = MagicMock()
        sections_paginator.collect = AsyncMock(return_value=[])
        client.sections.list_for_project_async = MagicMock(
            return_value=sections_paginator,
        )

        source_process = MagicMock()
        source_process.process_holder = holder
        ctx = _make_mock_ctx()
        service = ReopenService(client)

        await service.reopen_async(stage, ctx, source_process)

        client.tasks.update_async.assert_awaited_once_with(
            "task_002",
            completed=False,
        )

    @pytest.mark.asyncio
    async def test_section_move_to_opportunity(self) -> None:
        """Verify section APIs called to move task to OPPORTUNITY."""
        client = _make_mock_client()
        stage = _make_stage_config()
        holder = _make_holder()
        sales_task = _make_task("task_003")

        subtasks_paginator = MagicMock()
        subtasks_paginator.collect = AsyncMock(return_value=[sales_task])
        client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

        opp_section = _make_section("sec_opp_001", "Opportunity")
        active_section = _make_section("sec_active", "Active")
        sections_paginator = MagicMock()
        sections_paginator.collect = AsyncMock(
            return_value=[active_section, opp_section],
        )
        client.sections.list_for_project_async = MagicMock(
            return_value=sections_paginator,
        )

        source_process = MagicMock()
        source_process.process_holder = holder
        ctx = _make_mock_ctx()
        service = ReopenService(client)

        await service.reopen_async(stage, ctx, source_process)

        client.sections.list_for_project_async.assert_called_once_with(
            "1200944186565610",
        )
        client.sections.add_task_async.assert_awaited_once_with(
            "sec_opp_001",
            task="task_003",
        )


# ------------------------------------------------------------------
# Tests: Most Recent Selection
# ------------------------------------------------------------------


class TestMostRecentSelection:
    """Multiple candidates: picks most recent by created_at."""

    @pytest.mark.asyncio
    async def test_picks_most_recent_by_created_at(self) -> None:
        """With three Sales processes, the newest one is selected."""
        client = _make_mock_client()
        stage = _make_stage_config()
        holder = _make_holder()

        old_task = _make_task(
            "task_old",
            created_at="2024-06-01T00:00:00.000Z",
        )
        mid_task = _make_task(
            "task_mid",
            created_at="2025-01-15T00:00:00.000Z",
        )
        new_task = _make_task(
            "task_new",
            created_at="2025-03-20T00:00:00.000Z",
        )

        subtasks_paginator = MagicMock()
        subtasks_paginator.collect = AsyncMock(
            return_value=[mid_task, old_task, new_task],
        )
        client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

        # Minimal section setup
        sections_paginator = MagicMock()
        sections_paginator.collect = AsyncMock(return_value=[])
        client.sections.list_for_project_async = MagicMock(
            return_value=sections_paginator,
        )

        source_process = MagicMock()
        source_process.process_holder = holder
        ctx = _make_mock_ctx()
        service = ReopenService(client)

        result = await service.reopen_async(stage, ctx, source_process)

        assert result.success is True
        assert result.entity_gid == "task_new"

    @pytest.mark.asyncio
    async def test_filters_non_matching_process_types(self) -> None:
        """Non-matching ProcessType tasks are excluded from candidates."""
        client = _make_mock_client()
        stage = _make_stage_config()
        holder = _make_holder()

        sales_task = _make_task(
            "task_sales",
            created_at="2025-01-01T00:00:00.000Z",
            process_type_value="Sales",
        )
        onboarding_task = _make_task(
            "task_onboarding",
            created_at="2025-06-01T00:00:00.000Z",
            process_type_value="Onboarding",
        )

        subtasks_paginator = MagicMock()
        subtasks_paginator.collect = AsyncMock(
            return_value=[onboarding_task, sales_task],
        )
        client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

        sections_paginator = MagicMock()
        sections_paginator.collect = AsyncMock(return_value=[])
        client.sections.list_for_project_async = MagicMock(
            return_value=sections_paginator,
        )

        source_process = MagicMock()
        source_process.process_holder = holder
        ctx = _make_mock_ctx()
        service = ReopenService(client)

        result = await service.reopen_async(stage, ctx, source_process)

        # Should pick sales_task, not the newer onboarding_task
        assert result.success is True
        assert result.entity_gid == "task_sales"


# ------------------------------------------------------------------
# Tests: No Candidates
# ------------------------------------------------------------------


class TestNoCandidates:
    """No matching ProcessType in subtasks -> failure."""

    @pytest.mark.asyncio
    async def test_no_matching_process_type_returns_failure(self) -> None:
        """When no subtask matches the target ProcessType, return failure."""
        client = _make_mock_client()
        stage = _make_stage_config()
        holder = _make_holder()

        onboarding_task = _make_task(
            "task_ob",
            process_type_value="Onboarding",
        )

        subtasks_paginator = MagicMock()
        subtasks_paginator.collect = AsyncMock(return_value=[onboarding_task])
        client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

        source_process = MagicMock()
        source_process.process_holder = holder
        ctx = _make_mock_ctx()
        service = ReopenService(client)

        result = await service.reopen_async(stage, ctx, source_process)

        assert result.success is False
        assert "No sales process found to reopen" in result.error

    @pytest.mark.asyncio
    async def test_empty_subtasks_returns_failure(self) -> None:
        """When ProcessHolder has no subtasks, return failure."""
        client = _make_mock_client()
        stage = _make_stage_config()
        holder = _make_holder()

        # Default: subtasks_async returns empty list
        source_process = MagicMock()
        source_process.process_holder = holder
        ctx = _make_mock_ctx()
        service = ReopenService(client)

        result = await service.reopen_async(stage, ctx, source_process)

        assert result.success is False
        assert "No sales process found to reopen" in result.error


# ------------------------------------------------------------------
# Tests: ProcessHolder Resolution
# ------------------------------------------------------------------


class TestProcessHolderResolution:
    """ProcessHolder obtained from source_process or ctx fallback."""

    @pytest.mark.asyncio
    async def test_uses_source_process_holder_when_available(self) -> None:
        """If source_process.process_holder is set, uses it directly."""
        client = _make_mock_client()
        stage = _make_stage_config()
        holder = _make_holder("direct_holder")
        sales_task = _make_task("task_direct")

        subtasks_paginator = MagicMock()
        subtasks_paginator.collect = AsyncMock(return_value=[sales_task])
        client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

        sections_paginator = MagicMock()
        sections_paginator.collect = AsyncMock(return_value=[])
        client.sections.list_for_project_async = MagicMock(
            return_value=sections_paginator,
        )

        source_process = MagicMock()
        source_process.process_holder = holder
        ctx = _make_mock_ctx()
        service = ReopenService(client)

        result = await service.reopen_async(stage, ctx, source_process)

        assert result.success is True
        # Should have used the direct holder, not ctx
        client.tasks.subtasks_async.assert_called_once()
        call_args = client.tasks.subtasks_async.call_args
        assert call_args[0][0] == "direct_holder"
        ctx.resolve_holder_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_falls_back_to_resolve_holder_async(self) -> None:
        """When source_process.process_holder is None, uses ctx fallback."""
        client = _make_mock_client()
        stage = _make_stage_config()
        holder = _make_holder("resolved_holder")
        sales_task = _make_task("task_resolved")

        subtasks_paginator = MagicMock()
        subtasks_paginator.collect = AsyncMock(return_value=[sales_task])
        client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

        sections_paginator = MagicMock()
        sections_paginator.collect = AsyncMock(return_value=[])
        client.sections.list_for_project_async = MagicMock(
            return_value=sections_paginator,
        )

        source_process = MagicMock()
        source_process.process_holder = None
        ctx = _make_mock_ctx(holder=holder)
        service = ReopenService(client)

        result = await service.reopen_async(stage, ctx, source_process)

        assert result.success is True
        ctx.resolve_holder_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resolve_holder_returns_none(self) -> None:
        """When resolve_holder_async returns None, return error."""
        client = _make_mock_client()
        stage = _make_stage_config()

        source_process = MagicMock()
        source_process.process_holder = None
        ctx = _make_mock_ctx(holder=None)  # resolve returns None
        service = ReopenService(client)

        result = await service.reopen_async(stage, ctx, source_process)

        assert result.success is False
        assert "Cannot resolve ProcessHolder" in result.error


# ------------------------------------------------------------------
# Tests: Section Move Edge Cases
# ------------------------------------------------------------------


class TestSectionMoveEdgeCases:
    """Edge cases for section move logic."""

    @pytest.mark.asyncio
    async def test_section_not_found_is_graceful(self) -> None:
        """If target section name doesn't match any section, no error."""
        client = _make_mock_client()
        stage = _make_stage_config(target_section="NONEXISTENT")
        holder = _make_holder()
        sales_task = _make_task("task_nosec")

        subtasks_paginator = MagicMock()
        subtasks_paginator.collect = AsyncMock(return_value=[sales_task])
        client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

        # Sections exist but none match "NONEXISTENT"
        active_section = _make_section("sec_active", "Active")
        sections_paginator = MagicMock()
        sections_paginator.collect = AsyncMock(return_value=[active_section])
        client.sections.list_for_project_async = MagicMock(
            return_value=sections_paginator,
        )

        source_process = MagicMock()
        source_process.process_holder = holder
        ctx = _make_mock_ctx()
        service = ReopenService(client)

        result = await service.reopen_async(stage, ctx, source_process)

        # Should still succeed -- section move is best-effort
        assert result.success is True
        assert result.entity_gid == "task_nosec"
        client.sections.add_task_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_section_match_is_case_insensitive(self) -> None:
        """Section name matching is case-insensitive."""
        client = _make_mock_client()
        stage = _make_stage_config(target_section="OPPORTUNITY")
        holder = _make_holder()
        sales_task = _make_task("task_case")

        subtasks_paginator = MagicMock()
        subtasks_paginator.collect = AsyncMock(return_value=[sales_task])
        client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

        # Section name has different casing
        opp_section = _make_section("sec_opp", "opportunity")
        sections_paginator = MagicMock()
        sections_paginator.collect = AsyncMock(return_value=[opp_section])
        client.sections.list_for_project_async = MagicMock(
            return_value=sections_paginator,
        )

        source_process = MagicMock()
        source_process.process_holder = holder
        ctx = _make_mock_ctx()
        service = ReopenService(client)

        result = await service.reopen_async(stage, ctx, source_process)

        assert result.success is True
        client.sections.add_task_async.assert_awaited_once_with(
            "sec_opp",
            task="task_case",
        )

    @pytest.mark.asyncio
    async def test_no_project_gid_skips_section_move(self) -> None:
        """When target_stage has no project_gid, skip section move entirely."""
        client = _make_mock_client()
        stage = _make_stage_config(project_gid=None)
        holder = _make_holder()
        sales_task = _make_task("task_noproj")

        subtasks_paginator = MagicMock()
        subtasks_paginator.collect = AsyncMock(return_value=[sales_task])
        client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

        source_process = MagicMock()
        source_process.process_holder = holder
        ctx = _make_mock_ctx()
        service = ReopenService(client)

        result = await service.reopen_async(stage, ctx, source_process)

        assert result.success is True
        client.sections.list_for_project_async.assert_not_called()
        client.sections.add_task_async.assert_not_awaited()


# ------------------------------------------------------------------
# Tests: API Error Handling
# ------------------------------------------------------------------


class TestErrorHandling:
    """Exception during reopen -> caught, returns failure."""

    @pytest.mark.asyncio
    async def test_api_error_caught_and_returned(self) -> None:
        """If Asana API raises, ReopenResult reflects the error."""
        client = _make_mock_client()
        stage = _make_stage_config()
        holder = _make_holder()

        # subtasks_async raises
        subtasks_paginator = MagicMock()
        subtasks_paginator.collect = AsyncMock(
            side_effect=ConnectionError("Asana unavailable"),
        )
        client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

        source_process = MagicMock()
        source_process.process_holder = holder
        ctx = _make_mock_ctx()
        service = ReopenService(client)

        result = await service.reopen_async(stage, ctx, source_process)

        assert result.success is False
        assert "Asana unavailable" in result.error

    @pytest.mark.asyncio
    async def test_update_async_error_caught(self) -> None:
        """If tasks.update_async raises, error is caught."""
        client = _make_mock_client()
        stage = _make_stage_config()
        holder = _make_holder()
        sales_task = _make_task("task_update_fail")

        subtasks_paginator = MagicMock()
        subtasks_paginator.collect = AsyncMock(return_value=[sales_task])
        client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

        client.tasks.update_async = AsyncMock(
            side_effect=ConnectionError("update failed"),
        )

        source_process = MagicMock()
        source_process.process_holder = holder
        ctx = _make_mock_ctx()
        service = ReopenService(client)

        result = await service.reopen_async(stage, ctx, source_process)

        assert result.success is False
        assert "update failed" in result.error

    @pytest.mark.asyncio
    async def test_section_api_error_caught(self) -> None:
        """If sections API raises, error is caught in boundary guard."""
        client = _make_mock_client()
        stage = _make_stage_config()
        holder = _make_holder()
        sales_task = _make_task("task_sec_fail")

        subtasks_paginator = MagicMock()
        subtasks_paginator.collect = AsyncMock(return_value=[sales_task])
        client.tasks.subtasks_async = MagicMock(return_value=subtasks_paginator)

        # sections call raises
        sections_paginator = MagicMock()
        sections_paginator.collect = AsyncMock(
            side_effect=ConnectionError("sections unavailable"),
        )
        client.sections.list_for_project_async = MagicMock(
            return_value=sections_paginator,
        )

        source_process = MagicMock()
        source_process.process_holder = holder
        ctx = _make_mock_ctx()
        service = ReopenService(client)

        result = await service.reopen_async(stage, ctx, source_process)

        assert result.success is False
        assert "sections unavailable" in result.error


# ------------------------------------------------------------------
# Tests: ProcessType Matching
# ------------------------------------------------------------------


class TestProcessTypeMatching:
    """_matches_process_type: case-insensitive, dict + object formats."""

    def test_dict_custom_fields_exact_match(self) -> None:
        """Dict-style custom field with exact case match."""
        task = _make_task("t1", process_type_value="Sales", use_dict_custom_fields=True)
        assert ReopenService._matches_process_type(task, "sales") is True

    def test_dict_custom_fields_case_insensitive(self) -> None:
        """Dict-style custom field with different case."""
        task = _make_task("t2", process_type_value="SALES", use_dict_custom_fields=True)
        assert ReopenService._matches_process_type(task, "Sales") is True

    def test_object_custom_fields_match(self) -> None:
        """Object-style custom field (attributes, not dict keys)."""
        task = _make_task(
            "t3", process_type_value="Sales", use_dict_custom_fields=False
        )
        assert ReopenService._matches_process_type(task, "sales") is True

    def test_object_custom_fields_case_insensitive(self) -> None:
        """Object-style custom field with different case."""
        task = _make_task(
            "t4", process_type_value="ONBOARDING", use_dict_custom_fields=False
        )
        assert ReopenService._matches_process_type(task, "onboarding") is True

    def test_no_match_returns_false(self) -> None:
        """When display_value doesn't match stage_name, returns False."""
        task = _make_task("t5", process_type_value="Onboarding")
        assert ReopenService._matches_process_type(task, "sales") is False

    def test_no_custom_fields_returns_false(self) -> None:
        """Task with no custom_fields attribute returns False."""
        task = MagicMock()
        task.custom_fields = None
        assert ReopenService._matches_process_type(task, "sales") is False

    def test_empty_custom_fields_returns_false(self) -> None:
        """Task with empty custom_fields list returns False."""
        task = MagicMock()
        task.custom_fields = []
        assert ReopenService._matches_process_type(task, "sales") is False

    def test_processtype_field_name_variant(self) -> None:
        """Handles 'ProcessType' (no space) field name variant."""
        task = MagicMock()
        task.custom_fields = [
            {"name": "ProcessType", "display_value": "Sales"},
        ]
        assert ReopenService._matches_process_type(task, "sales") is True

    def test_empty_display_value_returns_false(self) -> None:
        """If display_value is empty string, returns False."""
        task = MagicMock()
        task.custom_fields = [
            {"name": "Process Type", "display_value": ""},
        ]
        assert ReopenService._matches_process_type(task, "sales") is False

    def test_none_display_value_returns_false(self) -> None:
        """If display_value is None, returns False."""
        task = MagicMock()
        task.custom_fields = [
            {"name": "Process Type", "display_value": None},
        ]
        assert ReopenService._matches_process_type(task, "sales") is False


# ------------------------------------------------------------------
# Tests: ReopenResult Structural Typing
# ------------------------------------------------------------------


class TestReopenResultStructure:
    """ReopenResult matches engine.ReopenResult by structure."""

    def test_success_result_fields(self) -> None:
        """Successful result has expected fields."""
        result = ReopenResult(success=True, entity_gid="gid_123")
        assert result.success is True
        assert result.entity_gid == "gid_123"
        assert result.error == ""

    def test_failure_result_fields(self) -> None:
        """Failed result has expected fields."""
        result = ReopenResult(success=False, error="Something failed")
        assert result.success is False
        assert result.entity_gid == ""
        assert result.error == "Something failed"

    def test_default_field_values(self) -> None:
        """Default values match engine.ReopenResult contract."""
        result = ReopenResult(success=True)
        assert result.entity_gid == ""
        assert result.error == ""


# ------------------------------------------------------------------
# Tests: Subtask Listing API Call
# ------------------------------------------------------------------


class TestSubtaskListing:
    """Verify correct opt_fields passed to subtasks_async."""

    @pytest.mark.asyncio
    async def test_subtasks_called_with_correct_opt_fields(self) -> None:
        """subtasks_async receives the required opt_fields for matching."""
        client = _make_mock_client()
        stage = _make_stage_config()
        holder = _make_holder("holder_check")

        source_process = MagicMock()
        source_process.process_holder = holder
        ctx = _make_mock_ctx()
        service = ReopenService(client)

        await service.reopen_async(stage, ctx, source_process)

        client.tasks.subtasks_async.assert_called_once()
        call_args = client.tasks.subtasks_async.call_args
        assert call_args[0][0] == "holder_check"
        opt_fields = call_args[1].get(
            "opt_fields", call_args[0][1] if len(call_args[0]) > 1 else None
        )
        assert "name" in opt_fields
        assert "created_at" in opt_fields
        assert "custom_fields" in opt_fields
        assert "custom_fields.name" in opt_fields
        assert "custom_fields.display_value" in opt_fields
