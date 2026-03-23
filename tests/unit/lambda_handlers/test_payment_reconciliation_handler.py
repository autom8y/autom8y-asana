"""Unit tests for payment_reconciliation Lambda handler.

Per TDD-data-attachment-bridge-platform Section 7.
Tests for Lambda handler config, registration, and workflow construction.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from autom8_asana.automation.workflows.payment_reconciliation import (
    DEFAULT_ATTACHMENT_PATTERN,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_MAX_CONCURRENCY,
    PaymentReconciliationWorkflow,
)

# ---------------------------------------------------------------------------
# TestHandlerConfig
# ---------------------------------------------------------------------------


class TestHandlerConfig:
    """Handler config matches spec."""

    def test_config_workflow_id(self) -> None:
        from autom8_asana.lambda_handlers.payment_reconciliation import _config

        assert _config.workflow_id == "payment-reconciliation"

    def test_config_log_prefix(self) -> None:
        from autom8_asana.lambda_handlers.payment_reconciliation import _config

        assert _config.log_prefix == "lambda_payment_reconciliation"

    def test_config_dms_namespace(self) -> None:
        from autom8_asana.lambda_handlers.payment_reconciliation import _config

        assert _config.dms_namespace == "Autom8y/AsanaReconciliation"

    def test_config_response_metadata_keys(self) -> None:
        from autom8_asana.lambda_handlers.payment_reconciliation import _config

        assert "total_excel_rows" in _config.response_metadata_keys

    def test_config_requires_data_client(self) -> None:
        from autom8_asana.lambda_handlers.payment_reconciliation import _config

        assert _config.requires_data_client is True

    def test_config_default_params_max_concurrency(self) -> None:
        from autom8_asana.lambda_handlers.payment_reconciliation import _config

        assert _config.default_params["max_concurrency"] == DEFAULT_MAX_CONCURRENCY

    def test_config_default_params_attachment_pattern(self) -> None:
        from autom8_asana.lambda_handlers.payment_reconciliation import _config

        assert (
            _config.default_params["attachment_pattern"] == DEFAULT_ATTACHMENT_PATTERN
        )

    def test_config_default_params_lookback_days(self) -> None:
        from autom8_asana.lambda_handlers.payment_reconciliation import _config

        assert _config.default_params["lookback_days"] == DEFAULT_LOOKBACK_DAYS


# ---------------------------------------------------------------------------
# TestHandlerModule
# ---------------------------------------------------------------------------


class TestHandlerModule:
    """Handler module is importable and exposes expected interface."""

    def test_module_importable(self) -> None:
        import autom8_asana.lambda_handlers.payment_reconciliation as mod

        assert mod is not None

    def test_handler_function_exists(self) -> None:
        from autom8_asana.lambda_handlers.payment_reconciliation import handler

        assert callable(handler)


# ---------------------------------------------------------------------------
# TestHandlerRegistration
# ---------------------------------------------------------------------------


class TestHandlerRegistration:
    """Handler is registered in lambda_handlers.__init__."""

    def test_registered_in_all(self) -> None:
        import autom8_asana.lambda_handlers as lh

        assert "payment_reconciliation_handler" in lh.__all__

    def test_importable_from_package(self) -> None:
        from autom8_asana.lambda_handlers import payment_reconciliation_handler

        assert callable(payment_reconciliation_handler)

    def test_handler_identity(self) -> None:
        from autom8_asana.lambda_handlers import payment_reconciliation_handler
        from autom8_asana.lambda_handlers.payment_reconciliation import handler

        assert payment_reconciliation_handler is handler


# ---------------------------------------------------------------------------
# TestCreateWorkflow
# ---------------------------------------------------------------------------


class TestCreateWorkflow:
    """_create_workflow constructs the workflow correctly."""

    def test_create_workflow_constructs_correctly(self) -> None:
        from autom8_asana.lambda_handlers.payment_reconciliation import (
            _create_workflow,
        )

        mock_asana_client = MagicMock()
        mock_asana_client.attachments = MagicMock()
        mock_data_client = AsyncMock()

        workflow = _create_workflow(mock_asana_client, mock_data_client)

        assert isinstance(workflow, PaymentReconciliationWorkflow)
        assert workflow._asana_client is mock_asana_client
        assert workflow._data_client is mock_data_client
        assert workflow._attachments_client is mock_asana_client.attachments
