"""Tests for AttachmentReplacementMixin.

Validates the shared attachment deletion logic extracted from
ConversationAuditWorkflow and InsightsExportWorkflow.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.automation.workflows.mixins import AttachmentReplacementMixin

# --- Concrete stub that uses the mixin ---


class _StubWorkflow(AttachmentReplacementMixin):
    """Minimal concrete class to exercise the mixin."""

    def __init__(self, attachments_client: AsyncMock) -> None:
        self._attachments_client = attachments_client

    @property
    def workflow_id(self) -> str:
        return "stub-workflow"


def _make_attachment(gid: str, name: str) -> MagicMock:
    att = MagicMock()
    att.gid = gid
    att.name = name
    return att


class _AsyncIter:
    """Async iterator over a list of items."""

    def __init__(self, items: list) -> None:
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration


# --- Tests ---


class TestDeleteOldAttachments:
    """Tests for AttachmentReplacementMixin._delete_old_attachments."""

    def _make_client(self, attachments: list[MagicMock]) -> MagicMock:
        """Build a mock AttachmentsClient with list_for_task_async → async iter."""
        client = MagicMock()
        client.list_for_task_async.return_value = _AsyncIter(attachments)
        client.delete_async = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_deletes_matching_attachments(self) -> None:
        """Attachments matching the pattern (not excluded) are deleted."""
        att_old = _make_attachment("att-1", "conversations_20260101.csv")
        att_other = _make_attachment("att-2", "notes.txt")
        client = self._make_client([att_old, att_other])

        wf = _StubWorkflow(client)
        await wf._delete_old_attachments(
            "task-1", "conversations_*.csv", exclude_name="conversations_20260210.csv"
        )

        client.delete_async.assert_called_once_with("att-1")

    @pytest.mark.asyncio
    async def test_excludes_new_upload_from_deletion(self) -> None:
        """The just-uploaded file matching the pattern is NOT deleted."""
        att_new = _make_attachment("att-new", "conversations_20260210.csv")
        att_old = _make_attachment("att-old", "conversations_20260101.csv")
        client = self._make_client([att_new, att_old])

        wf = _StubWorkflow(client)
        await wf._delete_old_attachments(
            "task-1", "conversations_*.csv", exclude_name="conversations_20260210.csv"
        )

        client.delete_async.assert_called_once_with("att-old")

    @pytest.mark.asyncio
    async def test_handles_delete_failure_gracefully(self) -> None:
        """A failed delete is non-fatal; other deletes still proceed."""
        att1 = _make_attachment("att-1", "conversations_20260101.csv")
        att2 = _make_attachment("att-2", "conversations_20260102.csv")
        client = self._make_client([att1, att2])
        client.delete_async.side_effect = [
            ConnectionError("network error"),
            None,
        ]

        wf = _StubWorkflow(client)
        await wf._delete_old_attachments(
            "task-1", "conversations_*.csv", exclude_name="conversations_20260210.csv"
        )

        assert client.delete_async.call_count == 2

    @pytest.mark.asyncio
    async def test_no_attachments_no_errors(self) -> None:
        """Empty attachment list completes without errors."""
        client = self._make_client([])

        wf = _StubWorkflow(client)
        await wf._delete_old_attachments(
            "task-1", "conversations_*.csv", exclude_name="conversations_20260210.csv"
        )

        client.delete_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_attachment_name_no_match(self) -> None:
        """Attachment with empty/None name does not match any pattern."""
        att = _make_attachment("att-1", "")
        client = self._make_client([att])

        wf = _StubWorkflow(client)
        await wf._delete_old_attachments(
            "task-1", "conversations_*.csv", exclude_name="conversations_20260210.csv"
        )

        client.delete_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_attachment_name_no_match(self) -> None:
        """Attachment with None name does not match any pattern."""
        att = _make_attachment("att-1", None)
        att.name = None
        client = self._make_client([att])

        wf = _StubWorkflow(client)
        await wf._delete_old_attachments(
            "task-1", "conversations_*.csv", exclude_name="conversations_20260210.csv"
        )

        client.delete_async.assert_not_called()
