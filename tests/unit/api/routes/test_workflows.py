"""Tests for POST /api/v1/workflows/{workflow_id}/invoke endpoint.

Per TDD-ENTITY-SCOPE-001 Section 8.5: Unit tests for the workflow
invocation API endpoint including success, error codes, auth, validation,
dry-run, params override, response shape, and audit logging.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.dependencies import AuthContext, get_auth_context
from autom8_asana.api.main import create_app
from autom8_asana.api.routes.workflows import (
    _WORKFLOW_CONFIGS,
    register_workflow_config,
)
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.dual_mode import AuthMode
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.automation.workflows.base import WorkflowResult
from autom8_asana.lambda_handlers.workflow_handler import WorkflowHandlerConfig
from autom8_asana.services.resolver import EntityProjectRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workflow_result(
    workflow_id: str = "test-workflow",
    total: int = 1,
    succeeded: int = 1,
    failed: int = 0,
    skipped: int = 0,
    metadata: dict[str, Any] | None = None,
) -> WorkflowResult:
    """Create a test WorkflowResult."""
    started = datetime(2026, 2, 19, 12, 0, 0, tzinfo=UTC)
    return WorkflowResult(
        workflow_id=workflow_id,
        started_at=started,
        completed_at=started + timedelta(seconds=5),
        total=total,
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        metadata=metadata or {},
    )


def _make_mock_workflow(
    validate_errors: list[str] | None = None,
    entities: list[dict[str, Any]] | None = None,
    result: WorkflowResult | None = None,
) -> MagicMock:
    """Create a mock WorkflowAction with expected behavior."""
    mock_wf = MagicMock()
    mock_wf.validate_async = AsyncMock(return_value=validate_errors or [])
    mock_wf.enumerate_async = AsyncMock(return_value=entities or [{"gid": "123456789"}])
    mock_wf.execute_async = AsyncMock(return_value=result or _make_workflow_result())
    return mock_wf


def _make_test_config(
    workflow_id: str = "test-workflow",
    requires_data_client: bool = False,
    default_params: dict[str, Any] | None = None,
    response_metadata_keys: tuple[str, ...] = (),
    mock_workflow: MagicMock | None = None,
) -> WorkflowHandlerConfig:
    """Create a test WorkflowHandlerConfig.

    Uses a mutable container so the factory can be redirected to a specific
    mock workflow after config creation (WorkflowHandlerConfig is frozen).
    """
    # Mutable container: the factory lambda captures this by reference,
    # so changing _wf_holder[0] after creation redirects the factory.
    _wf_holder: list[MagicMock | None] = [mock_workflow]

    def _factory(client: Any, data_client: Any) -> MagicMock:
        wf = _wf_holder[0]
        if wf is not None:
            return wf
        return _make_mock_workflow()

    config = WorkflowHandlerConfig(
        workflow_factory=_factory,
        workflow_id=workflow_id,
        log_prefix="test_workflow",
        default_params=default_params or {},
        response_metadata_keys=response_metadata_keys,
        requires_data_client=requires_data_client,
    )
    # Attach holder so tests can swap the mock after creation
    config.__dict__["_wf_holder"] = _wf_holder  # type: ignore[attr-defined]
    return config


def _set_mock_workflow(config: WorkflowHandlerConfig, mock_wf: MagicMock) -> None:
    """Redirect a test config's factory to return a specific mock workflow."""
    config.__dict__["_wf_holder"][0] = mock_wf  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons before and after each test for isolation."""
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    # Clear workflow config registry
    _WORKFLOW_CONFIGS.clear()
    yield
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    _WORKFLOW_CONFIGS.clear()


@pytest.fixture()
def app(monkeypatch):
    """Create a test application with mocked discovery.

    Sets AUTH__DEV_MODE=true so JWTAuthMiddleware returns bypass claims
    instead of validating tokens.
    """
    monkeypatch.setenv("AUTOM8Y_ENV", "LOCAL")
    monkeypatch.setenv("AUTH__DEV_MODE", "true")

    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="offer",
                project_gid="1143843662099250",
                project_name="Business Offers",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        test_app = create_app()

        # Default auth context
        async def _mock_get_auth_context() -> AuthContext:
            return AuthContext(
                mode=AuthMode.JWT,
                asana_pat="test_bot_pat",
                caller_service="autom8_data",
            )

        test_app.dependency_overrides[get_auth_context] = _mock_get_auth_context

        yield test_app


@pytest.fixture()
def client(app) -> TestClient:
    """Create a test client with a default Authorization header.

    The header value doesn't matter because get_auth_context is overridden,
    but the JWTAuthMiddleware still checks for its presence even in dev mode.
    """
    with TestClient(
        app, headers={"Authorization": "Bearer test_token_workflows"}
    ) as tc:
        yield tc


# ---------------------------------------------------------------------------
# Tests: TDD Section 8.5
# ---------------------------------------------------------------------------


class TestInvokeSuccess:
    """Test successful workflow invocation."""

    def test_invoke_success(self, client, app) -> None:
        """Mock workflow returns result; 200 with expected shape."""
        mock_wf = _make_mock_workflow()
        config = _make_test_config(mock_workflow=mock_wf)
        register_workflow_config(config)

        with (
            patch("autom8_asana.client.AsanaClient") as MockAsana,
            patch("autom8_asana.lambda_handlers.cloudwatch.emit_metric"),
        ):
            MockAsana.return_value = MagicMock()

            resp = client.post(
                "/api/v1/workflows/test-workflow/invoke",
                json={"entity_ids": ["123456789"]},
            )

        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["workflow_id"] == "test-workflow"
        assert body["entity_count"] == 1
        assert body["dry_run"] is False
        assert "result" in body


class TestInvokeUnknownWorkflow:
    """Test unknown workflow_id returns 404."""

    def test_invoke_unknown_workflow_404(self, client) -> None:
        """Unregistered workflow_id returns 404."""
        resp = client.post(
            "/api/v1/workflows/nonexistent-workflow/invoke",
            json={"entity_ids": ["123456789"]},
        )

        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "WORKFLOW_NOT_FOUND"


class TestInvokeValidation:
    """Tests for request body validation (400 errors)."""

    def test_invoke_empty_entity_ids_400(self, client) -> None:
        """Empty entity_ids returns 422 (Pydantic validation)."""
        register_workflow_config(_make_test_config())

        resp = client.post(
            "/api/v1/workflows/test-workflow/invoke",
            json={"entity_ids": []},
        )

        # Pydantic validators return 422 for request body validation
        assert resp.status_code == 422

    def test_invoke_non_numeric_gid_400(self, client) -> None:
        """Non-numeric entity_ids returns 422 (Pydantic validation)."""
        register_workflow_config(_make_test_config())

        resp = client.post(
            "/api/v1/workflows/test-workflow/invoke",
            json={"entity_ids": ["abc"]},
        )

        assert resp.status_code == 422

    def test_invoke_too_many_entity_ids_400(self, client) -> None:
        """More than 100 entity_ids returns 422 (Pydantic validation)."""
        register_workflow_config(_make_test_config())

        resp = client.post(
            "/api/v1/workflows/test-workflow/invoke",
            json={"entity_ids": [str(i) for i in range(101)]},
        )

        assert resp.status_code == 422


class TestInvokeAuth:
    """Tests for authentication."""

    def test_invoke_no_auth_401(self, app) -> None:
        """Missing Authorization header returns 401."""
        register_workflow_config(_make_test_config())

        # Override auth to raise 401
        async def _failing_auth() -> AuthContext:
            from fastapi import HTTPException

            raise HTTPException(status_code=401, detail="Missing auth")

        app.dependency_overrides[get_auth_context] = _failing_auth

        with TestClient(app) as no_auth_client:
            resp = no_auth_client.post(
                "/api/v1/workflows/test-workflow/invoke",
                json={"entity_ids": ["123456789"]},
            )

        assert resp.status_code == 401


class TestInvokeValidationFailed:
    """Test workflow pre-flight validation failure."""

    def test_invoke_validation_failed_422(self, client, app) -> None:
        """Workflow validate_async returns errors; 422."""
        mock_wf = _make_mock_workflow(validate_errors=["Data service unavailable"])
        config = _make_test_config(mock_workflow=mock_wf)
        register_workflow_config(config)

        with (
            patch("autom8_asana.client.AsanaClient") as MockAsana,
            patch("autom8_asana.lambda_handlers.cloudwatch.emit_metric"),
        ):
            MockAsana.return_value = MagicMock()

            resp = client.post(
                "/api/v1/workflows/test-workflow/invoke",
                json={"entity_ids": ["123456789"]},
            )

        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "WORKFLOW_VALIDATION_FAILED"


class TestInvokeDryRun:
    """Test dry_run flag propagation."""

    def test_invoke_dry_run_flag_passed(self, client, app) -> None:
        """dry_run=True reaches workflow params."""
        mock_wf = _make_mock_workflow()
        config = _make_test_config(mock_workflow=mock_wf)
        register_workflow_config(config)

        with (
            patch("autom8_asana.client.AsanaClient") as MockAsana,
            patch("autom8_asana.lambda_handlers.cloudwatch.emit_metric"),
        ):
            MockAsana.return_value = MagicMock()

            resp = client.post(
                "/api/v1/workflows/test-workflow/invoke",
                json={"entity_ids": ["123456789"], "dry_run": True},
            )

        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["dry_run"] is True

        # Verify dry_run was passed in params to execute_async
        execute_call = mock_wf.execute_async.call_args
        params = execute_call[0][1]  # second positional arg
        assert params.get("dry_run") is True


class TestInvokeParamsOverride:
    """Test custom params merge into workflow params."""

    def test_invoke_params_override(self, client, app) -> None:
        """Custom params merge into workflow params."""
        mock_wf = _make_mock_workflow()
        config = _make_test_config(
            default_params={"max_concurrency": 5, "date_range_days": 30},
            mock_workflow=mock_wf,
        )
        register_workflow_config(config)

        with (
            patch("autom8_asana.client.AsanaClient") as MockAsana,
            patch("autom8_asana.lambda_handlers.cloudwatch.emit_metric"),
        ):
            MockAsana.return_value = MagicMock()

            resp = client.post(
                "/api/v1/workflows/test-workflow/invoke",
                json={
                    "entity_ids": ["123456789"],
                    "params": {"max_concurrency": 2},
                },
            )

        assert resp.status_code == 200

        # Verify params override merged correctly
        execute_call = mock_wf.execute_async.call_args
        params = execute_call[0][1]
        # Custom override should take precedence
        assert params.get("max_concurrency") == 2


class TestInvokeResponseShape:
    """Test response envelope structure."""

    def test_invoke_response_shape(self, client, app) -> None:
        """Verify response includes all expected fields."""
        mock_wf = _make_mock_workflow(
            result=_make_workflow_result(
                total=3,
                succeeded=2,
                failed=1,
                metadata={"truncated_count": 1},
            )
        )
        config = _make_test_config(
            response_metadata_keys=("truncated_count",),
            mock_workflow=mock_wf,
        )
        register_workflow_config(config)

        with (
            patch("autom8_asana.client.AsanaClient") as MockAsana,
            patch("autom8_asana.lambda_handlers.cloudwatch.emit_metric"),
        ):
            MockAsana.return_value = MagicMock()

            resp = client.post(
                "/api/v1/workflows/test-workflow/invoke",
                json={"entity_ids": ["123456789"]},
            )

        assert resp.status_code == 200
        outer = resp.json()
        assert "data" in outer
        assert "meta" in outer
        body = outer["data"]

        # Verify domain response fields
        assert "request_id" in body
        assert body["invocation_source"] == "api"
        assert body["workflow_id"] == "test-workflow"
        assert body["dry_run"] is False
        assert body["entity_count"] == 3

        # Verify result sub-object
        result = body["result"]
        assert result["total"] == 3
        assert result["succeeded"] == 2
        assert result["failed"] == 1
        assert result["status"] == "completed"
        assert result["truncated_count"] == 1


class TestInvokeAuditLog:
    """Test audit log emission."""

    def test_invoke_audit_log_emitted(self, client, app) -> None:
        """Structured log contains workflow_id, entity_ids, caller_service."""
        mock_wf = _make_mock_workflow()
        config = _make_test_config(mock_workflow=mock_wf)
        register_workflow_config(config)

        with (
            patch("autom8_asana.client.AsanaClient") as MockAsana,
            patch("autom8_asana.lambda_handlers.cloudwatch.emit_metric"),
            patch("autom8_asana.api.routes.workflows.logger") as mock_logger,
        ):
            MockAsana.return_value = MagicMock()

            resp = client.post(
                "/api/v1/workflows/test-workflow/invoke",
                json={"entity_ids": ["123456789"]},
            )

        assert resp.status_code == 200

        # Verify audit log was emitted (at least start event)
        info_calls = mock_logger.info.call_args_list
        # Find the start audit log call
        start_call = next(
            (c for c in info_calls if c[0][0] == "workflow_invoke_api"),
            None,
        )
        assert start_call is not None
        assert start_call[1]["workflow_id"] == "test-workflow"
        assert start_call[1]["entity_ids"] == ["123456789"]
        assert start_call[1]["caller_service"] == "autom8_data"
