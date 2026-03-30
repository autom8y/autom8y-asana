"""Test that ECS lifespan successfully imports workflow configs from Lambda handlers.

Per REMEDY-002: The try/except Exception in lifespan.py lines 210-232 silently
swallows import failures. This test ensures the import path is exercised and
catches regressions from Lambda handler module changes.
"""

import importlib

import pytest


class TestLifespanWorkflowImportPath:
    """Verify the Lambda handler -> ECS lifespan import contract."""

    def test_conversation_audit_config_importable(self) -> None:
        """Verify _config is importable from conversation_audit handler."""
        mod = importlib.import_module("autom8_asana.lambda_handlers.conversation_audit")
        assert hasattr(mod, "_config"), (
            "conversation_audit module must export _config "
            "(WorkflowHandlerConfig instance)"
        )
        # Verify it quacks like a WorkflowHandlerConfig
        config = mod._config
        assert hasattr(config, "workflow_id")
        assert config.workflow_id == "conversation-audit"

    def test_insights_export_config_importable(self) -> None:
        """Verify _config is importable from insights_export handler."""
        mod = importlib.import_module("autom8_asana.lambda_handlers.insights_export")
        assert hasattr(mod, "_config"), (
            "insights_export module must export _config "
            "(WorkflowHandlerConfig instance)"
        )
        config = mod._config
        assert hasattr(config, "workflow_id")
        assert config.workflow_id == "insights-export"

    def test_register_workflow_config_importable(self) -> None:
        """Verify register_workflow_config is importable from workflows route."""
        mod = importlib.import_module("autom8_asana.api.routes.workflows")
        assert hasattr(mod, "register_workflow_config"), (
            "workflows route must export register_workflow_config function"
        )
        assert callable(mod.register_workflow_config)
