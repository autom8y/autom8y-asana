"""Shared mixins for workflow actions.

Per ADR-DRY-WORKFLOW-001: Extracted from ConversationAuditWorkflow and
InsightsExportWorkflow to eliminate 39-line duplication of upload-first
attachment replacement logic.

Follows the established mixin pattern (models/business/mixins.py).
"""

from __future__ import annotations

import fnmatch
from typing import Any

from autom8y_log import get_logger

logger = get_logger(__name__)


class AttachmentReplacementMixin:
    """Mixin for workflows that do upload-first attachment replacement.

    Requires the concrete class to set ``_attachments_client`` (an
    :class:`~autom8_asana.clients.attachments.AttachmentsClient`) and
    expose a ``workflow_id`` property for structured logging.

    Usage::

        class MyWorkflow(AttachmentReplacementMixin, WorkflowAction):
            ...
    """

    _attachments_client: Any  # AttachmentsClient (provided by concrete class)
    workflow_id: str  # Provided by WorkflowAction

    async def _delete_old_attachments(
        self,
        task_gid: str,
        pattern: str,
        exclude_name: str,
    ) -> None:
        """Delete old attachments matching *pattern*, excluding the new upload.

        Non-fatal: individual delete failures are logged as warnings and
        swallowed so the batch can continue.  The next execution will
        clean up any stragglers.

        Args:
            task_gid: Task GID to list attachments for.
            pattern: Glob pattern to match (e.g., ``"conversations_*.csv"``).
            exclude_name: Filename to exclude from deletion (the new upload).
        """
        page_iter = self._attachments_client.list_for_task_async(
            task_gid,
            opt_fields=["name"],
        )
        async for attachment in page_iter:
            att_name = attachment.name or ""
            if fnmatch.fnmatch(att_name, pattern) and att_name != exclude_name:
                try:
                    await self._attachments_client.delete_async(attachment.gid)
                    logger.debug(
                        "workflow_attachment_deleted",
                        workflow_id=self.workflow_id,
                        task_gid=task_gid,
                        attachment_gid=attachment.gid,
                        attachment_name=att_name,
                    )
                except Exception as exc:  # BROAD-CATCH: boundary -- attachment delete soft-fails per item
                    logger.warning(
                        "workflow_attachment_delete_failed",
                        workflow_id=self.workflow_id,
                        task_gid=task_gid,
                        attachment_gid=attachment.gid,
                        error=str(exc),
                    )
