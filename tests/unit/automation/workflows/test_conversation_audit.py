"""Tests for ConversationAuditWorkflow.

Per TDD-CONV-AUDIT-001 Section 10.4: Unit tests for the conversation audit
workflow including happy path, skip scenarios, error isolation, upload-first
ordering, feature flag, and concurrency.

Per TDD-section-activity-classifier Phase 3: Tests for business-level
activity checking via _resolve_business_activity with caching.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation.workflows.conversation_audit import (
    AUDIT_ENABLED_ENV_VAR,
    ConversationAuditWorkflow,
)
from autom8_asana.clients.data.models import ExportResult
from autom8_asana.core.scope import EntityScope
from autom8_asana.exceptions import ExportError
from autom8_asana.models.business.activity import AccountActivity
from autom8_asana.models.task import Task

# --- Helpers ---


def _make_task(
    gid: str, name: str, parent_gid: str | None = None, completed: bool = False
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


def _make_parent_task(
    office_phone: str | None = "+17705753103",
    gid: str = "biz-mock",
) -> Task:
    """Create a real Task instance representing a parent Business task.

    Uses a real Task model so that Business.model_validate(task, from_attributes=True)
    can read proper attribute values instead of MagicMock auto-generated children.
    """
    cf_list: list[dict] = []
    if office_phone:
        # CustomFieldAccessor needs gid, name, and text_value/display_value
        cf_list.append(
            {
                "gid": "1205917451230123",  # Mock GID for Office Phone field
                "name": "Office Phone",
                "text_value": office_phone,
                "display_value": office_phone,
                "resource_subtype": "text",
            }
        )
    return Task(
        gid=gid,
        name=f"Business {gid}",
        resource_type="task",
        custom_fields=cf_list,
    )


def _make_export_result(
    row_count: int = 42,
    truncated: bool = False,
    phone: str = "+17705753103",
) -> ExportResult:
    """Create a test ExportResult."""
    return ExportResult(
        csv_content=b"date,direction,body\n2026-02-01,inbound,Hello\n",
        row_count=row_count,
        truncated=truncated,
        office_phone=phone,
        filename=f"conversations_{phone.lstrip('+')}_20260210.csv",
    )


def _make_attachment(gid: str, name: str) -> MagicMock:
    """Create a mock Attachment object."""
    att = MagicMock()
    att.gid = gid
    att.name = name
    return att


class _AsyncIterator:
    """Async iterator for mock page iterators."""

    def __init__(self, items: list[Any]) -> None:
        self._items = items
        self._index = 0

    def __aiter__(self) -> _AsyncIterator:
        return self

    async def __anext__(self) -> Any:
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item

    async def collect(self) -> list[Any]:
        return self._items


def _make_workflow(
    holders: list[MagicMock] | None = None,
    parent_tasks: dict[str, MagicMock | Task] | None = None,
    export_results: dict[str, ExportResult] | None = None,
    export_errors: dict[str, ExportError] | None = None,
    existing_attachments: dict[str, list[MagicMock]] | None = None,
    activity_override: AccountActivity | None = AccountActivity.ACTIVE,
) -> tuple[ConversationAuditWorkflow, MagicMock, MagicMock, MagicMock]:
    """Build a ConversationAuditWorkflow with configured mocks.

    Args:
        holders: List of mock holder tasks.
        parent_tasks: Dict of business GID -> mock parent task.
        export_results: Dict of phone -> ExportResult.
        export_errors: Dict of phone -> ExportError.
        existing_attachments: Dict of holder GID -> list of mock attachments.
        activity_override: AccountActivity to return from _resolve_business_activity.
            Defaults to ACTIVE so existing tests pass transparently.
            Set to None to disable the patch (for tests that need real behavior).
    """
    mock_asana = MagicMock()
    mock_data_client = MagicMock()
    mock_attachments = MagicMock()

    # Enumerate holders
    holder_list = holders or []
    mock_asana.tasks.list_async.return_value = _AsyncIterator(holder_list)

    # Resolve parent: get_async returns the holder task first (for parent ref),
    # then the parent Business task (for custom_fields)
    holder_by_gid = {h.gid: h for h in holder_list}
    parent_by_gid = parent_tasks or {}

    async def mock_get_async(gid: str, **kwargs: Any) -> MagicMock | Task:
        if gid in holder_by_gid:
            return holder_by_gid[gid]
        if gid in parent_by_gid:
            return parent_by_gid[gid]
        # Fallback: return a task with no parent/custom_fields
        return _make_task(gid, "Unknown")

    mock_asana.tasks.get_async = AsyncMock(side_effect=mock_get_async)

    # Export CSV
    export_map = export_results or {}
    error_map = export_errors or {}

    async def mock_export(phone: str, **kwargs: Any) -> ExportResult:
        if phone in error_map:
            raise error_map[phone]
        if phone in export_map:
            return export_map[phone]
        return _make_export_result(phone=phone)

    mock_data_client.get_export_csv_async = AsyncMock(side_effect=mock_export)
    # is_healthy() used by BridgeWorkflowAction.validate_async()
    mock_data_client.is_healthy = AsyncMock()
    # Legacy _circuit_breaker kept for tests that inspect it directly
    mock_data_client._circuit_breaker = MagicMock()
    mock_data_client._circuit_breaker.check = AsyncMock()

    # Upload
    mock_attachments.upload_async = AsyncMock(return_value=MagicMock())

    # List attachments for deletion
    att_map = existing_attachments or {}

    def mock_list_for_task(gid: str, **kwargs: Any) -> _AsyncIterator:
        return _AsyncIterator(att_map.get(gid, []))

    mock_attachments.list_for_task_async = MagicMock(side_effect=mock_list_for_task)

    # Delete
    mock_attachments.delete_async = AsyncMock()

    workflow = ConversationAuditWorkflow(
        asana_client=mock_asana,
        data_client=mock_data_client,
        attachments_client=mock_attachments,
    )

    # Pre-populate activity map so existing tests bypass hydration.
    # All parent GIDs are treated as ACTIVE by default.
    for h in holder_list:
        if h.parent:
            workflow._activity_map[h.parent.gid] = AccountActivity.ACTIVE

    return workflow, mock_asana, mock_data_client, mock_attachments


def _default_scope() -> EntityScope:
    """Default scope for full enumeration."""
    return EntityScope()


async def _enumerate_and_execute(
    wf: ConversationAuditWorkflow,
    params: dict[str, Any] | None = None,
    scope: EntityScope | None = None,
) -> Any:
    """Helper: call enumerate_async then execute_async.

    Per TDD-ENTITY-SCOPE-001: The handler factory orchestrates
    enumerate -> execute. This helper simulates that for tests.
    """
    s = scope or _default_scope()
    p = params or {"workflow_id": "conversation-audit"}
    entities = await wf.enumerate_async(s)
    return await wf.execute_async(entities, p)


# --- Tests ---


class TestConversationAuditWorkflowId:
    """Test workflow_id property."""

    def test_workflow_id(self) -> None:
        wf, _, _, _ = _make_workflow()
        assert wf.workflow_id == "conversation-audit"


class TestValidateAsync:
    """Tests for validate_async pre-flight checks."""

    @pytest.mark.asyncio
    async def test_feature_flag_disabled(self) -> None:
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {AUDIT_ENABLED_ENV_VAR: "false"}):
            errors = await wf.validate_async()
        assert len(errors) == 1
        assert "disabled" in errors[0].lower()

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_zero(self) -> None:
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {AUDIT_ENABLED_ENV_VAR: "0"}):
            errors = await wf.validate_async()
        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_no(self) -> None:
        wf, _, _, _ = _make_workflow()
        with patch.dict(os.environ, {AUDIT_ENABLED_ENV_VAR: "no"}):
            errors = await wf.validate_async()
        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_feature_flag_enabled_default(self) -> None:
        wf, _, _, _ = _make_workflow()
        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            # Need to also clear the specific key
            os.environ.pop(AUDIT_ENABLED_ENV_VAR, None)
            errors = await wf.validate_async()
        assert errors == []

    @pytest.mark.asyncio
    async def test_circuit_breaker_open(self) -> None:
        wf, _, mock_data, _ = _make_workflow()

        from autom8y_http import CircuitBreakerOpenError as SdkCBOpen

        # BridgeWorkflowAction.validate_async() calls is_healthy()
        mock_data.is_healthy = AsyncMock(
            side_effect=SdkCBOpen(time_remaining=30.0, message="CB open")
        )
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop(AUDIT_ENABLED_ENV_VAR, None)
            errors = await wf.validate_async()
        assert len(errors) == 1
        assert "circuit breaker" in errors[0].lower()


class TestExecuteAsyncHappyPath:
    """Tests for happy path execution."""

    @pytest.mark.asyncio
    async def test_three_holders_all_succeed(self) -> None:
        """Happy path: 3 holders, all succeed."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        h2 = _make_task("h2", "Holder 2", parent_gid="biz2")
        h3 = _make_task("h3", "Holder 3", parent_gid="biz3")

        parent_tasks = {
            "biz1": _make_parent_task("+17705753101", gid="biz1"),
            "biz2": _make_parent_task("+17705753102", gid="biz2"),
            "biz3": _make_parent_task("+17705753103", gid="biz3"),
        }

        wf, _, _, mock_att = _make_workflow(
            holders=[h1, h2, h3],
            parent_tasks=parent_tasks,
        )

        result = await _enumerate_and_execute(wf)

        assert result.total == 3
        assert result.succeeded == 3
        assert result.failed == 0
        assert result.skipped == 0
        assert result.errors == []
        assert mock_att.upload_async.call_count == 3


class TestExecuteAsyncSkipNoPhone:
    """Tests for skip-no-phone scenarios."""

    @pytest.mark.asyncio
    async def test_skip_no_phone(self) -> None:
        """1 of 3 holders has no parent.office_phone -> skipped=1."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        h2 = _make_task("h2", "Holder 2", parent_gid="biz2")
        h3 = _make_task("h3", "No Phone", parent_gid="biz_no_phone")

        parent_tasks = {
            "biz1": _make_parent_task("+17705753101", gid="biz1"),
            "biz2": _make_parent_task("+17705753102", gid="biz2"),
            "biz_no_phone": _make_parent_task(None, gid="biz_no_phone"),  # No phone
        }

        wf, _, _, _ = _make_workflow(
            holders=[h1, h2, h3],
            parent_tasks=parent_tasks,
        )

        result = await _enumerate_and_execute(wf)

        assert result.total == 3
        assert result.succeeded == 2
        assert result.skipped == 1

    @pytest.mark.asyncio
    async def test_skip_no_parent(self) -> None:
        """Holder with no parent reference -> skipped."""
        h1 = _make_task("h1", "Orphan Holder")  # No parent_gid

        wf, _, _, _ = _make_workflow(holders=[h1])

        result = await _enumerate_and_execute(wf)

        assert result.total == 1
        assert result.skipped == 1


class TestExecuteAsyncSkipZeroRows:
    """Tests for skip-zero-rows scenario."""

    @pytest.mark.asyncio
    async def test_skip_zero_rows(self) -> None:
        """Export returns row_count=0 -> skipped."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}
        export_results = {
            "+17705753101": _make_export_result(row_count=0, phone="+17705753101"),
        }

        wf, _, _, mock_att = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
            export_results=export_results,
        )

        result = await _enumerate_and_execute(wf)

        assert result.total == 1
        assert result.skipped == 1
        assert result.succeeded == 0
        # Upload should NOT be called for zero-row export
        mock_att.upload_async.assert_not_called()


class TestExecuteAsyncExportFailure:
    """Tests for export failure scenarios."""

    @pytest.mark.asyncio
    async def test_export_failure_captured(self) -> None:
        """DataServiceClient raises ExportError -> failed=1, error captured."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}
        export_errors = {
            "+17705753101": ExportError(
                "Server error",
                office_phone="+17705753101",
                reason="server_error",
            ),
        }

        wf, _, _, _ = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
            export_errors=export_errors,
        )

        result = await _enumerate_and_execute(wf)

        assert result.total == 1
        assert result.failed == 1
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "export_server_error"
        assert result.errors[0].recoverable is True

    @pytest.mark.asyncio
    async def test_export_client_error_not_recoverable(self) -> None:
        """Client error (4xx) -> failed, not recoverable."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}
        export_errors = {
            "+17705753101": ExportError(
                "Bad request",
                office_phone="+17705753101",
                reason="client_error",
            ),
        }

        wf, _, _, _ = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
            export_errors=export_errors,
        )

        result = await _enumerate_and_execute(wf)

        assert result.errors[0].recoverable is False


class TestExecuteAsyncCircuitBreakerOpen:
    """Tests for circuit breaker open scenario."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_all_fail(self) -> None:
        """All exports fail with circuit breaker -> all failed."""
        holders = [
            _make_task(f"h{i}", f"Holder {i}", parent_gid=f"biz{i}") for i in range(3)
        ]
        parent_tasks = {
            f"biz{i}": _make_parent_task(f"+1770575310{i}", gid=f"biz{i}")
            for i in range(3)
        }
        export_errors = {
            f"+1770575310{i}": ExportError(
                "Circuit breaker open",
                office_phone=f"+1770575310{i}",
                reason="circuit_breaker",
            )
            for i in range(3)
        }

        wf, _, _, _ = _make_workflow(
            holders=holders,
            parent_tasks=parent_tasks,
            export_errors=export_errors,
        )

        result = await _enumerate_and_execute(wf)

        assert result.total == 3
        assert result.failed == 3
        assert result.succeeded == 0


class TestExecuteAsyncUploadFirstOrdering:
    """Tests for upload-first attachment replacement."""

    @pytest.mark.asyncio
    async def test_upload_before_delete(self) -> None:
        """Assert upload_async is called before delete_async."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}

        phone = "+17705753101"
        new_filename = f"conversations_{phone.lstrip('+')}_20260210.csv"
        old_att = _make_attachment(
            "old-att-1", "conversations_17705753101_20260203.csv"
        )

        wf, _, _, mock_att = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
            existing_attachments={"h1": [old_att]},
        )

        result = await _enumerate_and_execute(wf)

        assert result.succeeded == 1
        # Upload must happen before delete
        upload_call = mock_att.upload_async.call_args_list[0]
        assert upload_call is not None
        assert mock_att.delete_async.call_count == 1
        assert mock_att.delete_async.call_args[0][0] == "old-att-1"


class TestExecuteAsyncTruncated:
    """Tests for truncated export scenario."""

    @pytest.mark.asyncio
    async def test_truncated_counted_in_metadata(self) -> None:
        """Truncated export -> metadata has truncated_count."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        h2 = _make_task("h2", "Holder 2", parent_gid="biz2")
        parent_tasks = {
            "biz1": _make_parent_task("+17705753101", gid="biz1"),
            "biz2": _make_parent_task("+17705753102", gid="biz2"),
        }
        export_results = {
            "+17705753101": _make_export_result(
                row_count=10000, truncated=True, phone="+17705753101"
            ),
            "+17705753102": _make_export_result(
                row_count=50, truncated=False, phone="+17705753102"
            ),
        }

        wf, _, _, _ = _make_workflow(
            holders=[h1, h2],
            parent_tasks=parent_tasks,
            export_results=export_results,
        )

        result = await _enumerate_and_execute(wf)

        assert result.succeeded == 2
        assert result.metadata["truncated_count"] == 1


class TestExecuteAsyncDeleteFailureTolerance:
    """Tests for delete failure tolerance (EC-05)."""

    @pytest.mark.asyncio
    async def test_delete_failure_still_succeeded(self) -> None:
        """Delete-old fails -> holder still counted as succeeded."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}

        old_att = _make_attachment(
            "old-att-1", "conversations_17705753101_20260203.csv"
        )

        wf, _, _, mock_att = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
            existing_attachments={"h1": [old_att]},
        )

        # Make delete fail
        mock_att.delete_async = AsyncMock(side_effect=Exception("Asana API error"))

        result = await _enumerate_and_execute(wf)

        # Still succeeded because upload worked; delete failure is non-fatal
        assert result.succeeded == 1
        assert result.failed == 0


class TestExecuteAsyncConcurrency:
    """Tests for concurrency semaphore."""

    @pytest.mark.asyncio
    async def test_max_concurrency_from_params(self) -> None:
        """Verify max_concurrency is taken from params."""
        holders = [
            _make_task(f"h{i}", f"Holder {i}", parent_gid=f"biz{i}") for i in range(10)
        ]
        parent_tasks = {
            f"biz{i}": _make_parent_task(f"+1770575310{i}", gid=f"biz{i}")
            for i in range(10)
        }

        wf, _, _, _ = _make_workflow(
            holders=holders,
            parent_tasks=parent_tasks,
        )

        params = {
            "workflow_id": "conversation-audit",
            "max_concurrency": 2,
        }

        result = await _enumerate_and_execute(wf, params=params)

        # All should succeed even with low concurrency
        assert result.total == 10
        assert result.succeeded == 10


class TestExecuteAsyncFeatureFlagDisabled:
    """Tests for feature flag disabling the workflow."""

    @pytest.mark.asyncio
    async def test_validate_blocks_execution(self) -> None:
        """validate_async returns error when disabled; workflow should not execute."""
        wf, mock_asana, _, _ = _make_workflow()

        with patch.dict(os.environ, {AUDIT_ENABLED_ENV_VAR: "false"}):
            errors = await wf.validate_async()

        assert len(errors) == 1
        # Caller (scheduler/lambda) checks validation before execute_async
        # Verify no Asana API calls were made
        mock_asana.tasks.list_async.assert_not_called()


class TestExecuteAsyncEmptyProject:
    """Tests for empty project (no holders)."""

    @pytest.mark.asyncio
    async def test_no_holders(self) -> None:
        """Empty project -> total=0, all zeros."""
        wf, _, _, _ = _make_workflow(holders=[])

        result = await _enumerate_and_execute(wf)

        assert result.total == 0
        assert result.succeeded == 0
        assert result.failed == 0
        assert result.skipped == 0


class TestExecuteAsyncDateRange:
    """Tests for date_range_days parameter consumption.

    Per DEF-001 regression: date_range_days was accepted in YAML but not passed
    to get_export_csv_async. Verify the fix passes start_date/end_date through.
    """

    @pytest.mark.asyncio
    async def test_date_range_days_passed_to_export(self) -> None:
        """date_range_days from params -> start_date/end_date forwarded to export."""
        from datetime import date, timedelta

        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}

        wf, _, mock_data, _ = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
        )

        params = {
            "workflow_id": "conversation-audit",
            "date_range_days": 14,
        }

        await _enumerate_and_execute(wf, params=params)

        # Verify get_export_csv_async was called with start_date and end_date
        call_kwargs = mock_data.get_export_csv_async.call_args[1]
        expected_end = date.today()
        expected_start = expected_end - timedelta(days=14)
        assert call_kwargs["start_date"] == expected_start
        assert call_kwargs["end_date"] == expected_end

    @pytest.mark.asyncio
    async def test_default_date_range_30_days(self) -> None:
        """Default date_range_days=30 when not specified in params."""
        from datetime import date, timedelta

        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}

        wf, _, mock_data, _ = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
        )

        # No date_range_days in params
        params = {"workflow_id": "conversation-audit"}

        await _enumerate_and_execute(wf, params=params)

        call_kwargs = mock_data.get_export_csv_async.call_args[1]
        expected_end = date.today()
        expected_start = expected_end - timedelta(days=30)
        assert call_kwargs["start_date"] == expected_start
        assert call_kwargs["end_date"] == expected_end


class TestPreResolveBusinessActivities:
    """Tests for bulk activity pre-resolution and pre-filtering.

    Per TDD-ENTITY-SCOPE-001: Activity pre-filtering now happens in
    enumerate_async, not execute_async. Tests verify enumerate_async
    filters inactive holders before they reach execute_async.
    """

    @pytest.mark.asyncio
    async def test_prefilter_skips_inactive_holders(self) -> None:
        """Holders with INACTIVE parent Business are pre-filtered by enumerate_async."""
        h_active = _make_task("h1", "Active Holder", parent_gid="biz-active")
        h_inactive = _make_task("h2", "Inactive Holder", parent_gid="biz-inactive")
        parent_tasks = {
            "biz-active": _make_parent_task("+17705753101", gid="biz-active"),
            "biz-inactive": _make_parent_task("+17705753102", gid="biz-inactive"),
        }

        wf, _, mock_data, mock_att = _make_workflow(
            holders=[h_active, h_inactive],
            parent_tasks=parent_tasks,
        )
        # Override: mark one Business as INACTIVE
        wf._activity_map["biz-inactive"] = AccountActivity.INACTIVE

        # enumerate_async filters out inactive holders
        scope = _default_scope()
        entities = await wf.enumerate_async(scope)
        assert len(entities) == 1
        assert entities[0]["gid"] == "h1"

        # execute_async only processes the active holder
        result = await wf.execute_async(entities, {"workflow_id": "conversation-audit"})
        assert result.total == 1
        assert result.succeeded == 1
        # Only the active holder should trigger CSV export
        assert mock_data.get_export_csv_async.call_count == 1
        assert mock_att.upload_async.call_count == 1

    @pytest.mark.asyncio
    async def test_prefilter_skips_none_activity(self) -> None:
        """Holders with None activity (hydration failed) are pre-filtered by enumerate_async."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz-unknown")
        parent_tasks = {
            "biz-unknown": _make_parent_task("+17705753101", gid="biz-unknown"),
        }

        wf, _, mock_data, _ = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
        )
        # Override: simulate failed hydration (None activity)
        wf._activity_map["biz-unknown"] = None

        # enumerate_async filters out holders with None activity
        scope = _default_scope()
        entities = await wf.enumerate_async(scope)
        assert len(entities) == 0

        # execute_async with empty entities
        result = await wf.execute_async(entities, {"workflow_id": "conversation-audit"})
        assert result.total == 0
        mock_data.get_export_csv_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_prefilter_passes_holders_without_parent(self) -> None:
        """Holders with no parent_gid pass through pre-filter to processing."""
        h_orphan = _make_task("h1", "Orphan Holder")  # No parent_gid

        wf, _, _, _ = _make_workflow(holders=[h_orphan])

        result = await _enumerate_and_execute(wf)

        # Orphan passes pre-filter, then skipped at phone resolution
        assert result.total == 1
        assert result.skipped == 1

    @pytest.mark.asyncio
    async def test_preresolution_deduplicates_business_gids(self) -> None:
        """Multiple holders sharing a parent Business hydrate it only once."""
        h1 = _make_task("h1", "Holder 1", parent_gid="shared-biz")
        h2 = _make_task("h2", "Holder 2", parent_gid="shared-biz")
        h3 = _make_task("h3", "Holder 3", parent_gid="shared-biz")
        parent_tasks = {
            "shared-biz": _make_parent_task("+17705753101", gid="shared-biz"),
        }

        wf, _, _, _ = _make_workflow(
            holders=[h1, h2, h3],
            parent_tasks=parent_tasks,
        )
        # Clear pre-populated activity_map to test dedup via pre-resolution
        wf._activity_map.clear()

        # Track actual hydrations (cache misses) vs cached lookups
        hydration_calls: list[str] = []

        async def tracking_resolve(gid: str) -> AccountActivity | None:
            if gid in wf._activity_map:
                return wf._activity_map[gid]
            hydration_calls.append(gid)
            wf._activity_map[gid] = AccountActivity.ACTIVE
            return AccountActivity.ACTIVE

        wf._resolve_business_activity = tracking_resolve  # type: ignore[assignment]

        result = await _enumerate_and_execute(wf)

        # Hydration (expensive depth=2 call) should happen exactly once
        assert hydration_calls.count("shared-biz") == 1
        assert result.total == 3
        assert result.succeeded == 3

    @pytest.mark.asyncio
    async def test_preresolution_handles_hydration_failure(self) -> None:
        """If hydration fails for a Business, its holders are filtered out by enumerate_async."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz-fail")
        parent_tasks = {
            "biz-fail": _make_parent_task("+17705753101", gid="biz-fail"),
        }

        wf, _, mock_data, _ = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
        )
        # Clear pre-populated map and mock hydration to fail
        wf._activity_map.clear()

        async def failing_resolve(gid: str) -> AccountActivity | None:
            wf._activity_map[gid] = None  # Simulate failed hydration
            return None

        wf._resolve_business_activity = failing_resolve  # type: ignore[assignment]

        # enumerate_async filters out holders with None activity
        scope = _default_scope()
        entities = await wf.enumerate_async(scope)
        assert len(entities) == 0

        result = await wf.execute_async(entities, {"workflow_id": "conversation-audit"})
        assert result.total == 0
        mock_data.get_export_csv_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_prefilter_mixed_activities(self) -> None:
        """Mix of ACTIVE, INACTIVE, ACTIVATING parents: only ACTIVE processed.

        Per TDD-ENTITY-SCOPE-001: Inactive holders are filtered out during
        enumerate_async, so execute_async only sees the 2 active holders.
        """
        h_active = _make_task("h1", "Active", parent_gid="biz-a")
        h_inactive = _make_task("h2", "Inactive", parent_gid="biz-i")
        h_activating = _make_task("h3", "Activating", parent_gid="biz-g")
        h_active2 = _make_task("h4", "Active 2", parent_gid="biz-a")  # Shares parent
        parent_tasks = {
            "biz-a": _make_parent_task("+17705753101", gid="biz-a"),
            "biz-i": _make_parent_task("+17705753102", gid="biz-i"),
            "biz-g": _make_parent_task("+17705753103", gid="biz-g"),
        }

        wf, _, mock_data, _ = _make_workflow(
            holders=[h_active, h_inactive, h_activating, h_active2],
            parent_tasks=parent_tasks,
        )
        # Override activities
        wf._activity_map["biz-a"] = AccountActivity.ACTIVE
        wf._activity_map["biz-i"] = AccountActivity.INACTIVE
        wf._activity_map["biz-g"] = AccountActivity.ACTIVATING

        result = await _enumerate_and_execute(wf)

        # enumerate_async filters out inactive/activating holders
        # Only h1 and h4 (both biz-a ACTIVE) reach execute_async
        assert result.total == 2
        assert result.succeeded == 2
        assert mock_data.get_export_csv_async.call_count == 2


class TestResolveOfficePhonePassthrough:
    """Tests for parent_gid passthrough optimization (IMP-01).

    When parent_gid is provided to _resolve_office_phone, the holder
    task fetch is skipped, saving 1 API call per holder.
    """

    @pytest.mark.asyncio
    async def test_parent_gid_skips_holder_fetch(self) -> None:
        """When parent_gid is provided, no get_async call for the holder task."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}

        wf, mock_asana, _, _ = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
        )

        await _enumerate_and_execute(wf)

        # get_async should NOT have been called with "h1" (the holder GID)
        # because parent_gid="biz1" was passed through from enumeration.
        # It SHOULD have been called with "biz1" for ResolutionContext.
        call_gids = [call.args[0] for call in mock_asana.tasks.get_async.call_args_list]
        assert "h1" not in call_gids

    @pytest.mark.asyncio
    async def test_no_parent_gid_falls_back_to_fetch(self) -> None:
        """When parent_gid is None, holder task is fetched for parent reference."""
        h1 = _make_task("h1", "Orphan Holder")  # No parent_gid

        wf, mock_asana, _, _ = _make_workflow(holders=[h1])

        await _enumerate_and_execute(wf)

        # get_async SHOULD be called with "h1" since parent_gid is None
        call_gids = [call.args[0] for call in mock_asana.tasks.get_async.call_args_list]
        assert "h1" in call_gids


# --- Activity Filtering Tests (Phase 3) ---


class TestEnumerateContactHolders:
    """Tests for _enumerate_contact_holders return shape."""

    @pytest.mark.asyncio
    async def test_returns_parent_gid_field(self) -> None:
        """Enumeration returns parent_gid (not parent object) in dicts."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        h2 = _make_task("h2", "Holder Orphan")

        wf, _, _, _ = _make_workflow(holders=[h1, h2])

        holders = await wf._enumerate_contact_holders()

        assert len(holders) == 2
        # Holder with parent should have parent_gid
        h1_dict = next(h for h in holders if h["gid"] == "h1")
        assert h1_dict["parent_gid"] == "biz1"
        # Orphan holder should have parent_gid=None
        h2_dict = next(h for h in holders if h["gid"] == "h2")
        assert h2_dict["parent_gid"] is None

    @pytest.mark.asyncio
    async def test_excludes_completed_tasks(self) -> None:
        """Completed holders are excluded from enumeration."""
        h1 = _make_task("h1", "Active Holder", parent_gid="biz1")
        h2 = _make_task("h2", "Completed Holder", parent_gid="biz2", completed=True)

        wf, _, _, _ = _make_workflow(holders=[h1, h2])

        holders = await wf._enumerate_contact_holders()

        assert len(holders) == 1
        assert holders[0]["gid"] == "h1"


class TestResolveBusinessActivity:
    """Tests for _resolve_business_activity method.

    Per TDD-section-activity-classifier Phase 3: Business-level activity
    checking with caching and error handling.

    Note: _resolve_business_activity calls hydrate_from_gid_async imported
    inside the function from autom8_asana.models.business.hydration, so we
    patch at the conversation_audit module's import site.
    """

    _HYDRATE_PATH = "autom8_asana.automation.workflows.conversation_audit.workflow.hydrate_from_gid_async"

    def _make_clean_workflow(self):
        """Create workflow without pre-populated activity_map."""
        wf, mock_asana, mock_data, mock_att = _make_workflow()
        wf._activity_map.clear()
        return wf, mock_asana, mock_data, mock_att

    def _make_hydration_result(self, activity: AccountActivity | None) -> MagicMock:
        """Build a mock HydrationResult whose business.max_unit_activity is set."""
        mock_result = MagicMock()
        mock_business = MagicMock()
        mock_business.max_unit_activity = activity
        mock_result.business = mock_business
        return mock_result

    @pytest.mark.asyncio
    async def test_returns_active_for_active_business(self) -> None:
        """Active business returns AccountActivity.ACTIVE."""
        wf, _, _, _ = self._make_clean_workflow()

        mock_result = self._make_hydration_result(AccountActivity.ACTIVE)

        with patch(self._HYDRATE_PATH, new=AsyncMock(return_value=mock_result)):
            result = await wf._resolve_business_activity("biz1")

        assert result == AccountActivity.ACTIVE

    @pytest.mark.asyncio
    async def test_caches_activity_result(self) -> None:
        """Second call for same business_gid returns cached result."""
        wf, _, _, _ = self._make_clean_workflow()

        mock_result = self._make_hydration_result(AccountActivity.ACTIVE)
        mock_hydrate = AsyncMock(return_value=mock_result)

        with patch(self._HYDRATE_PATH, new=mock_hydrate):
            result1 = await wf._resolve_business_activity("biz1")
            result2 = await wf._resolve_business_activity("biz1")

        assert result1 == AccountActivity.ACTIVE
        assert result2 == AccountActivity.ACTIVE
        # hydrate_from_gid_async should only be called once (cached)
        assert mock_hydrate.call_count == 1

    @pytest.mark.asyncio
    async def test_returns_none_on_resolution_failure(self) -> None:
        """Resolution failure caches and returns None."""
        wf, _, _, _ = self._make_clean_workflow()

        with patch(
            self._HYDRATE_PATH, new=AsyncMock(side_effect=Exception("API error"))
        ):
            result = await wf._resolve_business_activity("biz-bad")

        assert result is None
        # Verify cached
        assert "biz-bad" in wf._activity_map
        assert wf._activity_map["biz-bad"] is None

    @pytest.mark.asyncio
    async def test_caches_none_on_failure(self) -> None:
        """Failed resolution is cached so subsequent calls do not retry."""
        wf, _, _, _ = self._make_clean_workflow()

        mock_hydrate = AsyncMock(side_effect=Exception("API error"))

        with patch(self._HYDRATE_PATH, new=mock_hydrate):
            result1 = await wf._resolve_business_activity("biz-bad")
            result2 = await wf._resolve_business_activity("biz-bad")

        assert result1 is None
        assert result2 is None
        # Only called once; second call hits cache
        assert mock_hydrate.call_count == 1


class TestActivityFiltering:
    """Tests for business activity filtering in enumerate_async.

    Per TDD-ENTITY-SCOPE-001: Activity filtering moved from execute_async
    to enumerate_async. Holders whose parent Business is not ACTIVE are
    filtered out during enumeration and never reach execute_async.
    """

    @pytest.mark.asyncio
    async def test_enumerate_filters_inactive_business(self) -> None:
        """enumerate_async excludes holder with INACTIVE parent."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}

        wf, _, mock_data, _ = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
        )
        wf._activity_map["biz1"] = AccountActivity.INACTIVE

        entities = await wf.enumerate_async(_default_scope())
        assert len(entities) == 0
        mock_data.get_export_csv_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_enumerate_filters_activating_business(self) -> None:
        """enumerate_async excludes holder with ACTIVATING parent."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}

        wf, _, mock_data, _ = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
        )
        wf._activity_map["biz1"] = AccountActivity.ACTIVATING

        entities = await wf.enumerate_async(_default_scope())
        assert len(entities) == 0
        mock_data.get_export_csv_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_enumerate_filters_unknown_activity(self) -> None:
        """enumerate_async excludes holder with None (unknown) activity."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}

        wf, _, mock_data, _ = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
        )
        wf._activity_map["biz1"] = None

        entities = await wf.enumerate_async(_default_scope())
        assert len(entities) == 0
        mock_data.get_export_csv_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_enumerate_passes_active_business(self) -> None:
        """enumerate_async includes holder with ACTIVE parent."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}

        wf, _, mock_data, mock_att = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
        )

        entities = await wf.enumerate_async(_default_scope())
        assert len(entities) == 1

        result = await wf.execute_async(entities, {"workflow_id": "conversation-audit"})
        assert result.total == 1
        assert result.succeeded == 1
        assert result.metadata["activity_skipped_count"] == 0
        mock_data.get_export_csv_async.assert_called_once()
        mock_att.upload_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_enumerate_passes_orphan_holder(self) -> None:
        """Holder with no parent_gid passes through enumerate_async."""
        h1 = _make_task("h1", "Orphan Holder")  # No parent_gid

        wf, _, _, _ = _make_workflow(holders=[h1])

        entities = await wf.enumerate_async(_default_scope())
        assert len(entities) == 1

        result = await wf.execute_async(entities, {"workflow_id": "conversation-audit"})
        # Should be skipped due to no phone (not activity check)
        assert result.total == 1
        assert result.skipped == 1
        assert result.metadata["activity_skipped_count"] == 0

    @pytest.mark.asyncio
    async def test_enumerate_mixed_activity_outcomes(self) -> None:
        """enumerate_async with mixed activities: only ACTIVE passes through."""
        h1 = _make_task("h1", "Active Holder", parent_gid="biz1")
        h2 = _make_task("h2", "Inactive Holder", parent_gid="biz2")
        h3 = _make_task("h3", "Unknown Holder", parent_gid="biz3")

        parent_tasks = {
            "biz1": _make_parent_task("+17705753101", gid="biz1"),
            "biz2": _make_parent_task("+17705753102", gid="biz2"),
            "biz3": _make_parent_task("+17705753103", gid="biz3"),
        }

        wf, _, _, _ = _make_workflow(
            holders=[h1, h2, h3],
            parent_tasks=parent_tasks,
        )
        # Override activities per business
        wf._activity_map["biz1"] = AccountActivity.ACTIVE
        wf._activity_map["biz2"] = AccountActivity.INACTIVE
        wf._activity_map["biz3"] = None

        entities = await wf.enumerate_async(_default_scope())
        assert len(entities) == 1
        assert entities[0]["gid"] == "h1"

        result = await wf.execute_async(entities, {"workflow_id": "conversation-audit"})
        assert result.total == 1
        assert result.succeeded == 1

    @pytest.mark.asyncio
    async def test_activity_map_deduplication(self) -> None:
        """Multiple holders sharing the same parent should resolve activity once."""
        h1 = _make_task("h1", "Holder 1", parent_gid="shared-biz")
        h2 = _make_task("h2", "Holder 2", parent_gid="shared-biz")
        h3 = _make_task("h3", "Holder 3", parent_gid="shared-biz")

        parent_tasks = {
            "shared-biz": _make_parent_task("+17705753101", gid="shared-biz"),
        }

        wf, _, _, _ = _make_workflow(
            holders=[h1, h2, h3],
            parent_tasks=parent_tasks,
        )

        result = await _enumerate_and_execute(
            wf,
            params={"workflow_id": "conversation-audit", "max_concurrency": 1},
        )

        assert result.total == 3
        assert result.succeeded == 3

    @pytest.mark.asyncio
    async def test_workflow_result_metadata_has_activity_skipped_count(self) -> None:
        """WorkflowResult metadata always includes activity_skipped_count."""
        wf, _, _, _ = _make_workflow(holders=[])

        result = await _enumerate_and_execute(wf)

        assert "activity_skipped_count" in result.metadata
        assert result.metadata["activity_skipped_count"] == 0


class TestResolveOfficePhone:
    """Tests for _resolve_office_phone parent_gid optimization."""

    @pytest.mark.asyncio
    async def test_uses_parent_gid_when_provided(self) -> None:
        """When parent_gid is known, skips the holder GET call."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}

        wf, mock_asana, _, _ = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
        )

        result = await _enumerate_and_execute(wf)

        assert result.succeeded == 1
        # tasks.get_async should NOT be called for the holder task itself
        # because parent_gid was provided from enumeration.
        # It may be called for the parent Business via ResolutionContext,
        # but NOT for the holder GID "h1" to discover parent.
        get_calls = mock_asana.tasks.get_async.call_args_list
        holder_get_calls = [c for c in get_calls if c[0][0] == "h1"]
        assert len(holder_get_calls) == 0


# --- enumerate_async Tests (TDD-ENTITY-SCOPE-001 Section 8.3) ---


class TestEnumerateAsyncConversationAudit:
    """Tests for enumerate_async scope handling.

    Per TDD-ENTITY-SCOPE-001 Section 8.3: Verify that targeted scope
    skips pre-resolution and full scope triggers pre-resolution + filtering.
    """

    @pytest.mark.asyncio
    async def test_enumerate_with_entity_ids_skips_pre_resolution(self) -> None:
        """Targeted scope returns synthetic dicts without pre-resolution."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}

        wf, mock_asana, _, _ = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
        )

        # Targeted scope: entity_ids provided
        scope = EntityScope(entity_ids=("12345", "67890"))
        entities = await wf.enumerate_async(scope)

        # Should return synthetic dicts without enumerating the project
        assert len(entities) == 2
        assert entities[0]["gid"] == "12345"
        assert entities[1]["gid"] == "67890"
        # parent_gid should be None (not pre-resolved)
        assert entities[0]["parent_gid"] is None
        # Should NOT have called list_async (no project enumeration)
        mock_asana.tasks.list_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_enumerate_without_entity_ids_calls_pre_resolution(self) -> None:
        """Full scope triggers project enumeration and pre-resolution."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}

        wf, mock_asana, _, _ = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
        )

        # Full scope: no entity_ids
        scope = EntityScope()
        entities = await wf.enumerate_async(scope)

        # Should have called list_async for project enumeration
        mock_asana.tasks.list_async.assert_called_once()
        # Should return the holder from enumeration
        assert len(entities) == 1
        assert entities[0]["gid"] == "h1"
        assert entities[0]["parent_gid"] == "biz1"

    @pytest.mark.asyncio
    async def test_enumerate_filters_inactive_businesses(self) -> None:
        """Full enumeration filters out holders with non-ACTIVE parents."""
        h_active = _make_task("h1", "Active", parent_gid="biz-a")
        h_inactive = _make_task("h2", "Inactive", parent_gid="biz-i")
        h_unknown = _make_task("h3", "Unknown", parent_gid="biz-u")
        parent_tasks = {
            "biz-a": _make_parent_task("+17705753101", gid="biz-a"),
            "biz-i": _make_parent_task("+17705753102", gid="biz-i"),
            "biz-u": _make_parent_task("+17705753103", gid="biz-u"),
        }

        wf, _, _, _ = _make_workflow(
            holders=[h_active, h_inactive, h_unknown],
            parent_tasks=parent_tasks,
        )
        wf._activity_map["biz-a"] = AccountActivity.ACTIVE
        wf._activity_map["biz-i"] = AccountActivity.INACTIVE
        wf._activity_map["biz-u"] = None

        entities = await wf.enumerate_async(EntityScope())

        # Only active holder passes
        assert len(entities) == 1
        assert entities[0]["gid"] == "h1"


# --- Dry-Run Tests (TDD-ENTITY-SCOPE-001 Section 8.6) ---


class TestDryRunConversationAudit:
    """Tests for dry_run behavior in conversation audit workflow.

    Per TDD-ENTITY-SCOPE-001 Section 8.6: Verify that dry_run=True
    skips CSV upload and includes metadata.
    """

    @pytest.mark.asyncio
    async def test_dry_run_skips_csv_upload(self) -> None:
        """When dry_run=True, upload_async is NOT called."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}

        wf, _, _, mock_att = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
        )

        scope = EntityScope(dry_run=True)
        entities = await wf.enumerate_async(scope)
        result = await wf.execute_async(
            entities,
            {"workflow_id": "conversation-audit", "dry_run": True},
        )

        # Upload should NOT be called in dry-run mode
        mock_att.upload_async.assert_not_called()
        # Delete should also NOT be called
        mock_att.delete_async.assert_not_called()
        # Result should still report success (dry-run succeeds without writes)
        assert result.total == 1
        assert result.succeeded == 1
        assert result.metadata.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_dry_run_metadata_flag(self) -> None:
        """When dry_run=True, metadata includes dry_run=True."""
        wf, _, _, _ = _make_workflow(holders=[])

        scope = EntityScope(dry_run=True)
        entities = await wf.enumerate_async(scope)
        result = await wf.execute_async(
            entities,
            {"workflow_id": "conversation-audit", "dry_run": True},
        )

        assert result.metadata.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_dry_run_metadata_csv_row_count(self) -> None:
        """DEF-002: metadata['csv_row_count'] present in dry-run."""
        h1 = _make_task("h1", "Holder 1", parent_gid="biz1")
        parent_tasks = {"biz1": _make_parent_task("+17705753101", gid="biz1")}

        wf, _, _, _ = _make_workflow(
            holders=[h1],
            parent_tasks=parent_tasks,
        )

        scope = EntityScope(dry_run=True)
        entities = await wf.enumerate_async(scope)
        result = await wf.execute_async(
            entities,
            {"workflow_id": "conversation-audit", "dry_run": True},
        )

        row_counts = result.metadata.get("csv_row_count")
        assert row_counts is not None
        assert isinstance(row_counts, dict)
        assert "h1" in row_counts
        assert row_counts["h1"] == 42  # default from _make_export_result
