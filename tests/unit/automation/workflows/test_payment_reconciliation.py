"""Tests for PaymentReconciliationWorkflow.

Per TDD-data-attachment-bridge-platform Section 7.
Unit tests for the payment reconciliation workflow including happy path,
skip scenarios, error isolation, upload-first ordering, feature flag,
cache behavior, and PII masking.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from autom8_asana.automation.workflows.bridge_base import BridgeOutcome
from autom8_asana.automation.workflows.payment_reconciliation.workflow import (
    DEFAULT_ATTACHMENT_PATTERN,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_MAX_CONCURRENCY,
    RECONCILIATION_ENABLED_ENV_VAR,
    UNIT_PROJECT_GID,
    PaymentReconciliationWorkflow,
    _UnitOutcome,
)
from autom8_asana.clients.data.models import InsightsResponse
from autom8_asana.core.scope import EntityScope

# Patch paths
_RC_PATCH_PATH = (
    "autom8_asana.automation.workflows.payment_reconciliation.workflow.ResolutionContext"
)
_COMPOSE_PATCH_PATH = (
    "autom8_asana.automation.workflows.payment_reconciliation.workflow.compose_excel"
)
_MASK_PATCH_PATH = (
    "autom8_asana.automation.workflows.payment_reconciliation.workflow.mask_phone_number"
)


# --- Helpers ---


class _AsyncIter:
    """Async iterator over a list of items."""

    def __init__(self, items: list[Any]) -> None:
        self._items = iter(items)

    def __aiter__(self) -> _AsyncIter:
        return self

    async def __anext__(self) -> Any:
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration


def _make_task(
    gid: str,
    name: str,
    parent_gid: str | None = None,
    completed: bool = False,
) -> MagicMock:
    """Create a mock task object."""
    task = MagicMock()
    task.gid = gid
    task.name = name
    task.completed = completed
    if parent_gid:
        task.parent = MagicMock()
        task.parent.gid = parent_gid
    else:
        task.parent = None
    return task


def _make_workflow(
    *,
    tasks: list[MagicMock] | None = None,
) -> tuple[PaymentReconciliationWorkflow, MagicMock, MagicMock, MagicMock]:
    """Create a PaymentReconciliationWorkflow with mock clients.

    Returns:
        Tuple of (workflow, mock_asana_client, mock_data_client, mock_attachments_client).
    """
    mock_asana = MagicMock()
    mock_data = AsyncMock()
    mock_attachments = MagicMock()
    mock_attachments.upload_async = AsyncMock()
    mock_attachments.delete_async = AsyncMock()
    mock_attachments.list_for_task_async = MagicMock(return_value=_AsyncIter([]))

    # Configure task listing
    if tasks is not None:
        page_iter = AsyncMock()
        page_iter.collect = AsyncMock(return_value=tasks)
        mock_asana.tasks.list_async.return_value = page_iter

    wf = PaymentReconciliationWorkflow(
        asana_client=mock_asana,
        data_client=mock_data,
        attachments_client=mock_attachments,
    )
    return wf, mock_asana, mock_data, mock_attachments


def _make_mock_business(
    office_phone: str | None = "+17705753103",
    vertical: str | None = "chiropractic",
    name: str = "Test Business",
    gid: str = "biz_001",
) -> MagicMock:
    """Create a mock Business entity for ResolutionContext."""
    business = MagicMock()
    business.gid = gid
    business.office_phone = office_phone
    business.vertical = vertical
    business.name = name
    return business


def _setup_resolution_context(
    mock_rc: MagicMock,
    business: MagicMock | None = None,
) -> MagicMock:
    """Configure a patched ResolutionContext to return the given business."""
    if business is None:
        business = _make_mock_business()
    mock_ctx = AsyncMock()
    mock_ctx.business_async = AsyncMock(return_value=business)
    mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
    mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_ctx


def _make_reconciliation_response(
    rows: list[dict[str, Any]] | None = None,
) -> InsightsResponse:
    """Create a mock InsightsResponse with reconciliation data."""
    if rows is None:
        rows = [
            {"date": "2026-01-01", "spend": 100.0, "payments": 50.0},
            {"date": "2026-01-15", "spend": 200.0, "payments": 100.0},
        ]
    response = MagicMock(spec=InsightsResponse)
    response.data = rows
    return response


# ---------------------------------------------------------------------------
# TestConstants
# ---------------------------------------------------------------------------


class TestConstants:
    """Verify module-level constants match spec."""

    def test_reconciliation_enabled_env_var(self) -> None:
        assert RECONCILIATION_ENABLED_ENV_VAR == "AUTOM8_RECONCILIATION_ENABLED"

    def test_unit_project_gid(self) -> None:
        assert UNIT_PROJECT_GID == "1201081073731555"

    def test_default_max_concurrency(self) -> None:
        assert DEFAULT_MAX_CONCURRENCY == 5

    def test_default_attachment_pattern(self) -> None:
        assert DEFAULT_ATTACHMENT_PATTERN == "reconciliation_*.xlsx"

    def test_default_lookback_days(self) -> None:
        assert DEFAULT_LOOKBACK_DAYS == 30


# ---------------------------------------------------------------------------
# TestWorkflowIdentity
# ---------------------------------------------------------------------------


class TestWorkflowIdentity:
    """Verify workflow identity and base class wiring."""

    def test_workflow_id(self) -> None:
        wf, *_ = _make_workflow()
        assert wf.workflow_id == "payment-reconciliation"

    def test_feature_flag_env_var(self) -> None:
        wf, *_ = _make_workflow()
        assert wf.feature_flag_env_var == RECONCILIATION_ENABLED_ENV_VAR

    def test_inherits_bridge_workflow_action(self) -> None:
        from autom8_asana.automation.workflows.bridge_base import (
            BridgeWorkflowAction,
        )

        wf, *_ = _make_workflow()
        assert isinstance(wf, BridgeWorkflowAction)

    def test_per_run_cache_initialized(self) -> None:
        wf, *_ = _make_workflow()
        assert wf._business_cache == {}


# ---------------------------------------------------------------------------
# TestEnumerateEntities
# ---------------------------------------------------------------------------


class TestEnumerateEntities:
    """Tests for enumerate_entities (full enumeration path)."""

    @pytest.mark.asyncio
    async def test_enumerate_entities_full_path(self) -> None:
        """enumerate_entities fetches non-completed units from project."""
        tasks = [
            _make_task("u1", "Unit 1", parent_gid="uh1"),
            _make_task("u2", "Unit 2", parent_gid="uh2"),
            _make_task("u3", "Completed", parent_gid="uh3", completed=True),
        ]
        wf, mock_asana, _, _ = _make_workflow(tasks=tasks)
        scope = EntityScope()

        result = await wf.enumerate_entities(scope)

        assert len(result) == 2
        assert result[0] == {"gid": "u1", "name": "Unit 1", "parent_gid": "uh1"}
        assert result[1] == {"gid": "u2", "name": "Unit 2", "parent_gid": "uh2"}

        # Verify correct project was queried
        mock_asana.tasks.list_async.assert_called_once()
        call_kwargs = mock_asana.tasks.list_async.call_args
        assert (
            call_kwargs.kwargs.get("project") == UNIT_PROJECT_GID
            or (call_kwargs.args and call_kwargs.args[0] == UNIT_PROJECT_GID)
            or call_kwargs[1].get("project") == UNIT_PROJECT_GID
        )

    @pytest.mark.asyncio
    async def test_enumerate_entities_excludes_completed(self) -> None:
        """Completed tasks are filtered out."""
        tasks = [
            _make_task("u1", "Unit 1", completed=True),
            _make_task("u2", "Unit 2", completed=True),
        ]
        wf, _, _, _ = _make_workflow(tasks=tasks)
        scope = EntityScope()

        result = await wf.enumerate_entities(scope)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_enumerate_entities_section_filter(self) -> None:
        """When section_filter is populated, tasks in non-matching sections are excluded."""
        task = _make_task("u1", "Unit 1")
        # Add membership data
        membership = MagicMock()
        membership.section = MagicMock()
        membership.section.name = "Active"
        task.memberships = [membership]

        wf, _, _, _ = _make_workflow(tasks=[task])
        scope = EntityScope(section_filter=frozenset({"Active"}))

        result = await wf.enumerate_entities(scope)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_enumerate_entities_section_filter_excludes(self) -> None:
        """Tasks not in any matching section are excluded by section_filter."""
        task = _make_task("u1", "Unit 1")
        membership = MagicMock()
        membership.section = MagicMock()
        membership.section.name = "Inactive"
        task.memberships = [membership]

        wf, _, _, _ = _make_workflow(tasks=[task])
        scope = EntityScope(section_filter=frozenset({"Active"}))

        result = await wf.enumerate_entities(scope)

        assert len(result) == 0


# ---------------------------------------------------------------------------
# TestProcessEntity -- Happy Path
# ---------------------------------------------------------------------------


class TestProcessEntityHappyPath:
    """Tests for process_entity happy path."""

    @pytest.mark.asyncio
    async def test_process_entity_happy_path(self) -> None:
        """Full pipeline: resolve, fetch, format, upload, delete-old."""
        wf, mock_asana, mock_data, mock_attachments = _make_workflow()

        # Setup resolution
        unit_task = _make_task("u1", "Unit 1", parent_gid="uh1")
        mock_asana.tasks.get_async = AsyncMock(return_value=unit_task)

        with patch(_RC_PATCH_PATH) as mock_rc:
            business = _make_mock_business()
            _setup_resolution_context(mock_rc, business)

            # Setup data fetch
            response = _make_reconciliation_response()
            mock_data.get_reconciliation_async = AsyncMock(return_value=response)

            # Setup attachment ops
            mock_attachments.upload_async = AsyncMock()
            mock_attachments.list_for_task_async.return_value = _AsyncIter([])

            entity = {"gid": "u1", "name": "Unit 1", "parent_gid": "uh1"}
            params = {
                "lookback_days": 30,
                "attachment_pattern": DEFAULT_ATTACHMENT_PATTERN,
                "dry_run": False,
            }
            result = await wf.process_entity(entity, params)

        assert result.status == "succeeded"
        assert isinstance(result, _UnitOutcome)
        assert result.excel_rows == 2

        # Verify upload was called
        mock_attachments.upload_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_before_delete_ordering(self) -> None:
        """Upload is called before delete-old attachments."""
        wf, mock_asana, mock_data, mock_attachments = _make_workflow()

        unit_task = _make_task("u1", "Unit 1", parent_gid="uh1")
        mock_asana.tasks.get_async = AsyncMock(return_value=unit_task)

        call_order: list[str] = []

        async def track_upload(*args: Any, **kwargs: Any) -> None:
            call_order.append("upload")

        def track_list(*args: Any, **kwargs: Any) -> _AsyncIter:
            call_order.append("list_for_delete")
            return _AsyncIter([])

        mock_attachments.upload_async = AsyncMock(side_effect=track_upload)
        mock_attachments.list_for_task_async = MagicMock(side_effect=track_list)

        with patch(_RC_PATCH_PATH) as mock_rc:
            _setup_resolution_context(mock_rc)
            mock_data.get_reconciliation_async = AsyncMock(
                return_value=_make_reconciliation_response()
            )

            entity = {"gid": "u1", "name": "Unit 1"}
            params = {
                "dry_run": False,
                "attachment_pattern": DEFAULT_ATTACHMENT_PATTERN,
            }
            await wf.process_entity(entity, params)

        assert call_order.index("upload") < call_order.index("list_for_delete")


# ---------------------------------------------------------------------------
# TestProcessEntity -- Skip/Failure Scenarios
# ---------------------------------------------------------------------------


class TestProcessEntitySkipScenarios:
    """Tests for process_entity skip and failure paths."""

    @pytest.mark.asyncio
    async def test_process_entity_resolution_failure(self) -> None:
        """_resolve_unit returns None -> skipped with no_resolution."""
        wf, mock_asana, _, _ = _make_workflow()

        # No parent -> resolution returns None
        unit_task = _make_task("u1", "Unit 1", parent_gid=None)
        mock_asana.tasks.get_async = AsyncMock(return_value=unit_task)

        entity = {"gid": "u1", "name": "Unit 1"}
        params = {}
        result = await wf.process_entity(entity, params)

        assert result.status == "skipped"
        assert result.reason == "no_resolution"

    @pytest.mark.asyncio
    async def test_process_entity_empty_data(self) -> None:
        """Empty reconciliation data -> skipped with no_data."""
        wf, mock_asana, mock_data, _ = _make_workflow()

        unit_task = _make_task("u1", "Unit 1", parent_gid="uh1")
        mock_asana.tasks.get_async = AsyncMock(return_value=unit_task)

        with patch(_RC_PATCH_PATH) as mock_rc:
            _setup_resolution_context(mock_rc)

            # Empty data response
            response = MagicMock(spec=InsightsResponse)
            response.data = []
            mock_data.get_reconciliation_async = AsyncMock(return_value=response)

            entity = {"gid": "u1", "name": "Unit 1"}
            params = {}
            result = await wf.process_entity(entity, params)

        assert result.status == "skipped"
        assert result.reason == "no_data"

    @pytest.mark.asyncio
    async def test_process_entity_dry_run(self) -> None:
        """dry_run=True skips upload and delete."""
        wf, mock_asana, mock_data, mock_attachments = _make_workflow()

        unit_task = _make_task("u1", "Unit 1", parent_gid="uh1")
        mock_asana.tasks.get_async = AsyncMock(return_value=unit_task)

        with patch(_RC_PATCH_PATH) as mock_rc:
            _setup_resolution_context(mock_rc)
            mock_data.get_reconciliation_async = AsyncMock(
                return_value=_make_reconciliation_response()
            )

            entity = {"gid": "u1", "name": "Unit 1"}
            params = {"dry_run": True}
            result = await wf.process_entity(entity, params)

        assert result.status == "succeeded"
        mock_attachments.upload_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_entity_missing_phone(self) -> None:
        """Resolution returns business with no phone -> skipped."""
        wf, mock_asana, _, _ = _make_workflow()

        unit_task = _make_task("u1", "Unit 1", parent_gid="uh1")
        mock_asana.tasks.get_async = AsyncMock(return_value=unit_task)

        with patch(_RC_PATCH_PATH) as mock_rc:
            business = _make_mock_business(office_phone=None)
            _setup_resolution_context(mock_rc, business)

            entity = {"gid": "u1", "name": "Unit 1"}
            params = {}
            result = await wf.process_entity(entity, params)

        assert result.status == "skipped"
        assert result.reason == "no_resolution"

    @pytest.mark.asyncio
    async def test_process_entity_missing_vertical(self) -> None:
        """Resolution returns business with no vertical -> skipped."""
        wf, mock_asana, _, _ = _make_workflow()

        unit_task = _make_task("u1", "Unit 1", parent_gid="uh1")
        mock_asana.tasks.get_async = AsyncMock(return_value=unit_task)

        with patch(_RC_PATCH_PATH) as mock_rc:
            business = _make_mock_business(vertical=None)
            _setup_resolution_context(mock_rc, business)

            entity = {"gid": "u1", "name": "Unit 1"}
            params = {}
            result = await wf.process_entity(entity, params)

        assert result.status == "skipped"
        assert result.reason == "no_resolution"


# ---------------------------------------------------------------------------
# TestResolveUnit -- Caching
# ---------------------------------------------------------------------------


class TestResolveUnitCache:
    """Tests for _resolve_unit caching behavior."""

    @pytest.mark.asyncio
    async def test_resolve_unit_cache_hit(self) -> None:
        """Second resolution with same business uses cache."""
        wf, mock_asana, mock_data, mock_attachments = _make_workflow()

        # Both units share the same parent business
        unit_task_1 = _make_task("u1", "Unit 1", parent_gid="uh1")
        unit_task_2 = _make_task("u2", "Unit 2", parent_gid="uh1")
        mock_asana.tasks.get_async = AsyncMock(side_effect=[unit_task_1, unit_task_2])

        with patch(_RC_PATCH_PATH) as mock_rc:
            business = _make_mock_business(gid="biz_shared")
            _setup_resolution_context(mock_rc, business)

            result1 = await wf._resolve_unit("u1")
            result2 = await wf._resolve_unit("u2")

        assert result1 is not None
        assert result2 is not None
        assert result1[0] == result2[0]  # Same phone
        assert "biz_shared" in wf._business_cache

    @pytest.mark.asyncio
    async def test_resolve_unit_missing_parent(self) -> None:
        """Unit with no parent returns None."""
        wf, mock_asana, _, _ = _make_workflow()

        unit_task = _make_task("u1", "Unit 1", parent_gid=None)
        mock_asana.tasks.get_async = AsyncMock(return_value=unit_task)

        result = await wf._resolve_unit("u1")

        assert result is None


# ---------------------------------------------------------------------------
# TestBuildResultMetadata
# ---------------------------------------------------------------------------


class TestBuildResultMetadata:
    """Tests for _build_result_metadata."""

    def test_build_result_metadata(self) -> None:
        """Aggregates total_excel_rows from _UnitOutcome instances."""
        wf, *_ = _make_workflow()

        outcomes: list[BridgeOutcome] = [
            _UnitOutcome(gid="u1", status="succeeded", excel_rows=10),
            _UnitOutcome(gid="u2", status="succeeded", excel_rows=25),
            _UnitOutcome(gid="u3", status="skipped", reason="no_data"),
            BridgeOutcome(gid="u4", status="failed"),
        ]

        metadata = wf._build_result_metadata(outcomes)

        assert metadata["total_excel_rows"] == 35

    def test_build_result_metadata_empty(self) -> None:
        """Empty outcomes produce zero total."""
        wf, *_ = _make_workflow()

        metadata = wf._build_result_metadata([])

        assert metadata["total_excel_rows"] == 0


# ---------------------------------------------------------------------------
# TestUnitOutcome
# ---------------------------------------------------------------------------


class TestUnitOutcome:
    """Tests for _UnitOutcome dataclass."""

    def test_unit_outcome_extends_bridge_outcome(self) -> None:
        """_UnitOutcome inherits from BridgeOutcome."""
        outcome = _UnitOutcome(gid="u1", status="succeeded", excel_rows=10)
        assert isinstance(outcome, BridgeOutcome)

    def test_unit_outcome_does_not_duplicate_fields(self) -> None:
        """_UnitOutcome does not re-declare gid, status, reason, error."""
        import dataclasses

        outcome_fields = {f.name for f in dataclasses.fields(_UnitOutcome)}
        base_fields = {f.name for f in dataclasses.fields(BridgeOutcome)}
        unique_fields = outcome_fields - base_fields
        assert unique_fields == {"excel_rows"}

    def test_unit_outcome_defaults(self) -> None:
        """Default excel_rows is 0."""
        outcome = _UnitOutcome(gid="u1", status="skipped")
        assert outcome.excel_rows == 0


# ---------------------------------------------------------------------------
# TestPIIMasking
# ---------------------------------------------------------------------------


class TestPIIMasking:
    """Tests for PII masking in log calls."""

    @pytest.mark.asyncio
    async def test_pii_masking_in_process_entity(self) -> None:
        """mask_phone_number is called before any log emission."""
        wf, mock_asana, mock_data, mock_attachments = _make_workflow()

        unit_task = _make_task("u1", "Unit 1", parent_gid="uh1")
        mock_asana.tasks.get_async = AsyncMock(return_value=unit_task)

        with (
            patch(_RC_PATCH_PATH) as mock_rc,
            patch(_MASK_PATCH_PATH, return_value="***-***-3103") as mock_mask,
        ):
            _setup_resolution_context(mock_rc)
            mock_data.get_reconciliation_async = AsyncMock(
                return_value=_make_reconciliation_response()
            )
            mock_attachments.upload_async = AsyncMock()
            mock_attachments.list_for_task_async.return_value = _AsyncIter([])

            entity = {"gid": "u1", "name": "Unit 1"}
            params = {
                "dry_run": False,
                "attachment_pattern": DEFAULT_ATTACHMENT_PATTERN,
            }
            await wf.process_entity(entity, params)

        mock_mask.assert_called_once()


# ---------------------------------------------------------------------------
# TestAcidTest -- Zero Boilerplate Copied
# ---------------------------------------------------------------------------


class TestAcidTest:
    """Acid test: verify zero platform boilerplate in bridge code."""

    def test_no_validate_async(self) -> None:
        """PaymentReconciliationWorkflow does NOT define validate_async()."""
        # The method should be inherited, not overridden
        assert "validate_async" not in PaymentReconciliationWorkflow.__dict__

    def test_no_execute_async(self) -> None:
        """PaymentReconciliationWorkflow does NOT define execute_async()."""
        assert "execute_async" not in PaymentReconciliationWorkflow.__dict__

    def test_no_imports_from_insights(self) -> None:
        """No imports from insights/ package."""
        import inspect

        source = inspect.getsource(PaymentReconciliationWorkflow)
        assert "from autom8_asana.automation.workflows.insights" not in source

    def test_no_imports_from_conversation_audit(self) -> None:
        """No imports from conversation_audit/ package."""
        import inspect

        source = inspect.getsource(PaymentReconciliationWorkflow)
        assert "from autom8_asana.automation.workflows.conversation_audit" not in source

    def test_no_circuit_breaker_private_access(self) -> None:
        """No _circuit_breaker private attribute access."""
        import inspect

        source = inspect.getsource(PaymentReconciliationWorkflow)
        assert "_circuit_breaker" not in source

    def test_no_pii_private_import(self) -> None:
        """No _pii private module imports."""
        import inspect

        module = __import__(
            "autom8_asana.automation.workflows.payment_reconciliation.workflow",
            fromlist=["PaymentReconciliationWorkflow"],
        )
        source = inspect.getsource(module)
        assert "from autom8_asana.clients.data._pii" not in source
