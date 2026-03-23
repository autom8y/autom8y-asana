"""Unit tests for conversation_audit Lambda handler.

Per CLEANUP-002: ConversationAudit handler had zero dedicated tests.
Tests follow test_payment_reconciliation_handler.py structure.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from autom8_asana.automation.workflows.conversation_audit import (
    DEFAULT_ATTACHMENT_PATTERN,
    DEFAULT_DATE_RANGE_DAYS,
    DEFAULT_MAX_CONCURRENCY,
    ConversationAuditWorkflow,
)

# ---------------------------------------------------------------------------
# TestHandlerConfig
# ---------------------------------------------------------------------------


class TestHandlerConfig:
    """Handler config matches spec."""

    def test_config_workflow_id(self) -> None:
        from autom8_asana.lambda_handlers.conversation_audit import _config

        assert _config.workflow_id == "conversation-audit"

    def test_config_log_prefix(self) -> None:
        from autom8_asana.lambda_handlers.conversation_audit import _config

        assert _config.log_prefix == "lambda_conversation_audit"

    def test_config_dms_namespace(self) -> None:
        from autom8_asana.lambda_handlers.conversation_audit import _config

        assert _config.dms_namespace == "Autom8y/AsanaAudit"

    def test_config_response_metadata_keys(self) -> None:
        from autom8_asana.lambda_handlers.conversation_audit import _config

        assert "truncated_count" in _config.response_metadata_keys

    def test_config_default_params_max_concurrency(self) -> None:
        from autom8_asana.lambda_handlers.conversation_audit import _config

        assert _config.default_params["max_concurrency"] == DEFAULT_MAX_CONCURRENCY

    def test_config_default_params_attachment_pattern(self) -> None:
        from autom8_asana.lambda_handlers.conversation_audit import _config

        assert (
            _config.default_params["attachment_pattern"] == DEFAULT_ATTACHMENT_PATTERN
        )

    def test_config_default_params_date_range_days(self) -> None:
        from autom8_asana.lambda_handlers.conversation_audit import _config

        assert _config.default_params["date_range_days"] == DEFAULT_DATE_RANGE_DAYS


# ---------------------------------------------------------------------------
# TestHandlerModule
# ---------------------------------------------------------------------------


class TestHandlerModule:
    """Handler module is importable and exposes expected interface."""

    def test_module_importable(self) -> None:
        import autom8_asana.lambda_handlers.conversation_audit as mod

        assert mod is not None

    def test_handler_function_exists(self) -> None:
        from autom8_asana.lambda_handlers.conversation_audit import handler

        assert callable(handler)


# ---------------------------------------------------------------------------
# TestHandlerRegistration
# ---------------------------------------------------------------------------


class TestHandlerRegistration:
    """Handler is registered in lambda_handlers.__init__."""

    def test_registered_in_all(self) -> None:
        import autom8_asana.lambda_handlers as lh

        assert "conversation_audit_handler" in lh.__all__

    def test_importable_from_package(self) -> None:
        from autom8_asana.lambda_handlers import conversation_audit_handler

        assert callable(conversation_audit_handler)

    def test_handler_identity(self) -> None:
        from autom8_asana.lambda_handlers import conversation_audit_handler
        from autom8_asana.lambda_handlers.conversation_audit import handler

        assert conversation_audit_handler is handler


# ---------------------------------------------------------------------------
# TestCreateWorkflow
# ---------------------------------------------------------------------------


class TestCreateWorkflow:
    """_create_workflow constructs the workflow correctly."""

    def test_create_workflow_constructs_correctly(self) -> None:
        from autom8_asana.lambda_handlers.conversation_audit import (
            _create_workflow,
        )

        mock_asana_client = MagicMock()
        mock_asana_client.attachments = MagicMock()
        mock_data_client = AsyncMock()

        workflow = _create_workflow(mock_asana_client, mock_data_client)

        assert isinstance(workflow, ConversationAuditWorkflow)
        assert workflow._asana_client is mock_asana_client
        assert workflow._data_client is mock_data_client
        assert workflow._attachments_client is mock_asana_client.attachments
