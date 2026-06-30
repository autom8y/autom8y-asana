"""Unit tests for the onboarding_walkthrough Lambda handler (W4, DEPLOYED-DARK).

Centerpiece: the F4 WIRING GATE -- a build-time guard that fails loudly if a
future change unwires ``query_engine`` from the PR2 factory (which would render
the W1 GFR by-GUID guard silently INERT, skipping the whole sweep at
``anchor_unresolved``). Companion: the DARK proof -- with
``AUTOM8_WALKTHROUGH_ENABLED`` unset, the handler short-circuits to ``skipped``
before any enumeration or Asana write.

Structure mirrors test_insights_export.py / test_conversation_audit_handler.py.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_PRODUCER_DIR_ENV = "AUTOM8_WALKTHROUGH_PRODUCER_DIR"
_ENABLED_ENV = "AUTOM8_WALKTHROUGH_ENABLED"
_SDK_RESOLVER_FROM_ENV = "autom8y_core.clients.data_service.DataServiceClient.from_env"


@pytest.fixture(autouse=True)
def _neutralize_service_token_provider():
    """W-AUTH: the generic handler injects ``ServiceTokenAuthProvider()`` into the
    asana-local ``DataServiceClient`` (workflow_handler.py _execute). These tests
    mock at the client level with no SERVICE_CLIENT_ID/SECRET in the env, so a real
    provider construction would raise ValueError and 500 the handler. No-op the
    constructor; the injection contract is owned by
    test_workflow_handler_auth_injection.py.
    """
    from autom8_asana.auth.service_token import ServiceTokenAuthProvider

    with patch.object(ServiceTokenAuthProvider, "__init__", lambda self, *a, **k: None):
        yield


def _factory_clients() -> tuple[MagicMock, MagicMock]:
    """Build the (asana_client, data_client) pair the factory consumes."""
    mock_asana = MagicMock()
    mock_asana.attachments = MagicMock()
    mock_data = MagicMock()
    return mock_asana, mock_data


# ---------------------------------------------------------------------------
# THE F4 WIRING GATE -- query_engine MUST be wired (the silent-inert footgun catcher)
# ---------------------------------------------------------------------------


class TestWiringGate:
    """PR2 build-time gate: the factory MUST wire a real query_engine."""

    def test_handler_wires_query_engine_non_none(self, monkeypatch) -> None:
        """The PR2 factory wires a non-None query_engine onto the workflow.

        If a future change drops ``query_engine=query_engine`` from the factory,
        the workflow ctor defaults it to None, the W1 GFR by-GUID guard fails
        closed on EVERY task (``anchor_unresolved``), and the whole sweep attaches
        nothing while reporting a clean run. This gate makes that regression a
        BUILD failure, not a silent dark-inert deploy.
        """
        monkeypatch.setenv(_PRODUCER_DIR_ENV, "/tmp/walkthrough-producer")
        from autom8_asana.lambda_handlers.onboarding_walkthrough import _create_workflow

        mock_asana, mock_data = _factory_clients()

        with patch(_SDK_RESOLVER_FROM_ENV, return_value=MagicMock()):
            workflow = _create_workflow(mock_asana, mock_data)

        assert workflow._query_engine is not None, (
            "PR2 WIRING GATE: query_engine unwired -> W1 guard silently INERT, "
            "whole sweep skips anchor_unresolved."
        )

    def test_wiring_gate_is_a_real_query_engine(self, monkeypatch) -> None:
        """Strengthen the gate: the wired engine is the REAL QueryEngine type, so a
        truthy-but-fake stand-in cannot satisfy it.
        """
        monkeypatch.setenv(_PRODUCER_DIR_ENV, "/tmp/walkthrough-producer")
        from autom8_asana.lambda_handlers.onboarding_walkthrough import _create_workflow
        from autom8_asana.query.engine import QueryEngine

        mock_asana, mock_data = _factory_clients()
        with patch(_SDK_RESOLVER_FROM_ENV, return_value=MagicMock()):
            workflow = _create_workflow(mock_asana, mock_data)

        assert isinstance(workflow._query_engine, QueryEngine), (
            "PR2 WIRING GATE: query_engine must be the real GFR-backed QueryEngine "
            "(G-PROPAGATE: never a reimpl), not a truthy placeholder."
        )

    def test_factory_resolver_carries_phone_leg_not_the_data_client(self, monkeypatch) -> None:
        """The B1 resolver is the core-SDK client (from_env), NOT the asana-local
        data_client. Guards against the TDD-sketch bug where ``resolver=data_client``
        wires a client lacking ``resolve_routing_address_by_phone_async``.
        """
        monkeypatch.setenv(_PRODUCER_DIR_ENV, "/tmp/walkthrough-producer")
        from autom8_asana.lambda_handlers.onboarding_walkthrough import _create_workflow

        mock_asana, mock_data = _factory_clients()
        sentinel_resolver = MagicMock(name="sdk_resolver")
        with patch(_SDK_RESOLVER_FROM_ENV, return_value=sentinel_resolver) as from_env:
            workflow = _create_workflow(mock_asana, mock_data)

        from_env.assert_called_once()  # the core-SDK from_env factory was used
        assert workflow._resolver is sentinel_resolver
        assert workflow._resolver is not mock_data  # NOT the asana-local data_client


# ---------------------------------------------------------------------------
# THE DARK PROOF -- flag unset => short-circuit, zero enumeration, zero Asana writes
# ---------------------------------------------------------------------------


class TestDeployedDark:
    """With AUTOM8_WALKTHROUGH_ENABLED unset, the sweep is a no-op."""

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    def test_handler_short_circuits_dark_when_flag_unset(
        self, _mock_emit: MagicMock, monkeypatch
    ) -> None:
        """End-to-end: the REAL validate_async (flag unset) makes the handler return
        skipped(validation_failed) BEFORE enumeration -- no section/task list, no
        attachment upload. The producer-dir env is SET (as in the real DARK deploy);
        only the ENABLED flag is unset (the DARK lever).
        """
        monkeypatch.setenv(_PRODUCER_DIR_ENV, "/tmp/walkthrough-producer")
        monkeypatch.delenv(_ENABLED_ENV, raising=False)

        from autom8_asana.lambda_handlers.onboarding_walkthrough import handler

        mock_asana = MagicMock()
        mock_asana.attachments = MagicMock()
        mock_asana.attachments.upload_async = AsyncMock()
        mock_asana.attachments.delete_async = AsyncMock()
        mock_asana.sections = MagicMock()
        mock_asana.tasks = MagicMock()

        mock_data = AsyncMock()
        mock_data.__aenter__ = AsyncMock(return_value=mock_data)
        mock_data.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("autom8_asana.client.AsanaClient", return_value=mock_asana),
            patch(
                "autom8_asana.clients.data.client.DataServiceClient",
                return_value=mock_data,
            ),
            patch(_SDK_RESOLVER_FROM_ENV, return_value=MagicMock()),
        ):
            result = handler({}, MagicMock())

        # Short-circuited to skipped.
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "skipped"
        assert body["reason"] == "validation_failed"
        assert any(_ENABLED_ENV in e for e in body["errors"]), (
            "DARK proof: the skip reason must be the opt-in flag being unset, "
            "not some unrelated validation error."
        )

        # Zero enumeration (no project/section task listing).
        mock_asana.sections.list_for_project_async.assert_not_called()
        mock_asana.tasks.list_async.assert_not_called()
        # Zero Asana writes.
        mock_asana.attachments.upload_async.assert_not_awaited()
        mock_asana.attachments.delete_async.assert_not_awaited()

    async def test_workflow_validate_async_dark_with_engine_wired(self, monkeypatch) -> None:
        """Direct workflow-level DARK proof: a properly-wired workflow (query_engine
        non-None, so the F4 INERT branch does NOT fire) is STILL disabled by the
        opt-in flag being unset. Isolates the DARK lever from the wiring gate.
        """
        monkeypatch.setenv(_PRODUCER_DIR_ENV, "/tmp/walkthrough-producer")
        monkeypatch.delenv(_ENABLED_ENV, raising=False)

        from autom8_asana.lambda_handlers.onboarding_walkthrough import _create_workflow

        mock_asana, mock_data = _factory_clients()
        with patch(_SDK_RESOLVER_FROM_ENV, return_value=MagicMock()):
            workflow = _create_workflow(mock_asana, mock_data)

        errors = await workflow.validate_async()

        assert errors, "flag unset => validate_async must report the workflow disabled"
        assert any(_ENABLED_ENV in e for e in errors)
        # The disablement is the opt-in gate, NOT the F4 query_engine-inert signal.
        assert not any("query_engine unwired" in e for e in errors), (
            "engine is wired here; the only problem must be the opt-in flag"
        )


# ---------------------------------------------------------------------------
# Handler config + module + registration (mirror the sibling handler suites)
# ---------------------------------------------------------------------------


class TestHandlerConfig:
    def test_config_workflow_id(self) -> None:
        from autom8_asana.lambda_handlers.onboarding_walkthrough import _config

        assert _config.workflow_id == "onboarding-walkthrough"

    def test_config_log_prefix(self) -> None:
        from autom8_asana.lambda_handlers.onboarding_walkthrough import _config

        assert _config.log_prefix == "lambda_onboarding_walkthrough"

    def test_config_dms_namespace(self) -> None:
        from autom8_asana.lambda_handlers.onboarding_walkthrough import _config

        assert _config.dms_namespace == "Autom8y/AsanaWalkthrough"

    def test_config_default_params_attachment_pattern(self) -> None:
        from autom8_asana.automation.workflows.onboarding_walkthrough import constants
        from autom8_asana.lambda_handlers.onboarding_walkthrough import _config

        assert _config.default_params["attachment_pattern"] == constants.ATTACHMENT_GLOB
        assert _config.default_params["max_concurrency"] == 5


class TestHandlerModule:
    def test_module_importable(self) -> None:
        import autom8_asana.lambda_handlers.onboarding_walkthrough as mod

        assert mod is not None

    def test_handler_function_exists(self) -> None:
        from autom8_asana.lambda_handlers.onboarding_walkthrough import handler

        assert callable(handler)


class TestHandlerRegistration:
    def test_registered_in_all(self) -> None:
        import autom8_asana.lambda_handlers as lh

        assert "onboarding_walkthrough_handler" in lh.__all__

    def test_importable_from_package(self) -> None:
        from autom8_asana.lambda_handlers import onboarding_walkthrough_handler

        assert callable(onboarding_walkthrough_handler)

    def test_handler_identity(self) -> None:
        from autom8_asana.lambda_handlers import onboarding_walkthrough_handler
        from autom8_asana.lambda_handlers.onboarding_walkthrough import handler

        assert onboarding_walkthrough_handler is handler
