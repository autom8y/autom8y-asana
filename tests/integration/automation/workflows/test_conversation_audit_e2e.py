"""Integration test: full lifecycle from workflow trigger through attachment replacement.

Per TDD-CONV-AUDIT-001 Section 10.2: Integration test with mocked HTTP for
Asana API and autom8_data. Verifies the full enumerate -> resolve -> fetch -> replace
lifecycle with multiple holders including skip and failure scenarios.
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
from autom8_asana.exceptions import ExportError

# --- Helpers ---


def _make_task(
    gid: str, name: str, parent_gid: str | None = None, completed: bool = False
) -> MagicMock:
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


def _make_parent_task(office_phone: str | None, gid: str = "biz-mock") -> MagicMock:
    """Create a mock parent Business task.

    Supports Business.from_gid_async by being a proper Pydantic-validatable
    object (Business.model_validate receives the return of tasks.get_async).
    """
    from autom8_asana.models.business.business import Business

    cf_list: list[dict[str, Any]] = []
    if office_phone:
        cf_list.append(
            {
                "gid": "1205917451230123",
                "name": "Office Phone",
                "text_value": office_phone,
                "display_value": office_phone,
                "resource_subtype": "text",
            }
        )
    # Return a real Business instance so model_validate succeeds
    return Business(
        gid=gid,
        name=f"Business {gid}",
        resource_type="task",
        custom_fields=cf_list,
    )


def _make_attachment(gid: str, name: str) -> MagicMock:
    att = MagicMock()
    att.gid = gid
    att.name = name
    return att


class _AsyncIterator:
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


# --- Integration Test ---


class TestConversationAuditE2E:
    """Full lifecycle integration test with mocked externals."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_mixed_outcomes(self) -> None:
        """Test with 4 holders: 2 succeed, 1 skip (no phone), 1 fail (export error).

        Verifies:
        - Enumeration fetches active holders
        - Phone resolution via parent task
        - CSV fetch from data client
        - Upload-first attachment replacement
        - Old attachment deletion
        - Error isolation (one failure doesn't abort batch)
        - Correct aggregate counts
        """
        # Setup holders
        h_success_1 = _make_task("h1", "Holder Success 1", parent_gid="biz1")
        h_success_2 = _make_task("h2", "Holder Success 2", parent_gid="biz2")
        h_skip = _make_task("h3", "Holder No Phone", parent_gid="biz_no_phone")
        h_fail = _make_task("h4", "Holder Export Fail", parent_gid="biz4")

        all_holders = [h_success_1, h_success_2, h_skip, h_fail]

        # Setup parent tasks
        parent_tasks = {
            "biz1": _make_parent_task("+17705753101", gid="biz1"),
            "biz2": _make_parent_task("+17705753102", gid="biz2"),
            "biz_no_phone": _make_parent_task(None, gid="biz_no_phone"),
            "biz4": _make_parent_task("+17705753104", gid="biz4"),
        }

        # Setup mock Asana client
        mock_asana = MagicMock()
        mock_asana.tasks.list_for_project_async.return_value = _AsyncIterator(
            all_holders
        )

        holder_by_gid = {h.gid: h for h in all_holders}

        async def mock_get_async(gid: str, **kwargs: Any) -> MagicMock:
            if gid in holder_by_gid:
                return holder_by_gid[gid]
            if gid in parent_tasks:
                return parent_tasks[gid]
            return _make_task(gid, "Unknown")

        mock_asana.tasks.get_async = AsyncMock(side_effect=mock_get_async)

        # Setup mock data client
        mock_data_client = MagicMock()
        mock_data_client._circuit_breaker = MagicMock()
        mock_data_client._circuit_breaker.check = AsyncMock()

        async def mock_export(phone: str, **kwargs: Any) -> ExportResult:
            if phone == "+17705753104":
                raise ExportError(
                    "Service unavailable",
                    office_phone=phone,
                    reason="server_error",
                )
            return ExportResult(
                csv_content=b"date,direction,body\n2026-02-01,inbound,Hello\n",
                row_count=10,
                truncated=False,
                office_phone=phone,
                filename=f"conversations_{phone.lstrip('+')}_20260210.csv",
            )

        mock_data_client.get_export_csv_async = AsyncMock(side_effect=mock_export)

        # Setup mock attachments client
        mock_attachments = MagicMock()
        mock_attachments.upload_async = AsyncMock(return_value=MagicMock())

        # h1 has an old attachment, h2 has none
        old_att_h1 = _make_attachment(
            "old-h1", "conversations_17705753101_20260203.csv"
        )

        def mock_list_for_task(gid: str, **kwargs: Any) -> _AsyncIterator:
            if gid == "h1":
                return _AsyncIterator([old_att_h1])
            return _AsyncIterator([])

        mock_attachments.list_for_task_async = MagicMock(side_effect=mock_list_for_task)
        mock_attachments.delete_async = AsyncMock()

        # Create workflow
        workflow = ConversationAuditWorkflow(
            asana_client=mock_asana,
            data_client=mock_data_client,
            attachments_client=mock_attachments,
        )

        # Execute
        result = await workflow.execute_async(
            {
                "workflow_id": "conversation-audit",
                "max_concurrency": 5,
                "attachment_pattern": "conversations_*.csv",
            }
        )

        # Verify aggregate counts
        assert result.total == 4
        assert result.succeeded == 2
        assert result.skipped == 1  # h3 (no phone)
        assert result.failed == 1  # h4 (export error)
        assert len(result.errors) == 1
        assert result.errors[0].item_id == "h4"

        # Verify upload was called for succeeded holders only
        assert mock_attachments.upload_async.call_count == 2

        # Verify old attachment was deleted for h1
        mock_attachments.delete_async.assert_called_once_with("old-h1")

        # Verify workflow_id
        assert result.workflow_id == "conversation-audit"

        # Verify duration is positive
        assert result.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_validate_then_execute(self) -> None:
        """Test the full validate -> execute lifecycle as called by scheduler/lambda."""
        mock_asana = MagicMock()
        mock_asana.tasks.list_for_project_async.return_value = _AsyncIterator([])
        mock_asana.tasks.get_async = AsyncMock()

        mock_data_client = MagicMock()
        mock_data_client._circuit_breaker = MagicMock()
        mock_data_client._circuit_breaker.check = AsyncMock()
        mock_data_client.get_export_csv_async = AsyncMock()

        mock_attachments = MagicMock()

        workflow = ConversationAuditWorkflow(
            asana_client=mock_asana,
            data_client=mock_data_client,
            attachments_client=mock_attachments,
        )

        # Validate first (should pass with feature flag enabled)
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop(AUDIT_ENABLED_ENV_VAR, None)
            errors = await workflow.validate_async()
        assert errors == []

        # Execute
        result = await workflow.execute_async({"workflow_id": "conversation-audit"})
        assert result.total == 0  # Empty project
