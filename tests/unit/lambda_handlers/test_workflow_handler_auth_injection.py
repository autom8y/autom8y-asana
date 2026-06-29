"""Prod-path auth-injection contract for the generic workflow Lambda handler.

W-AUTH (insights-export ``succeeded:0`` since 2026-06-10): the Lambda entrypoint
``workflow_handler._execute`` constructed ``DataServiceClient()`` with NO
``auth_provider`` (workflow_handler.py:155-161 at HEAD), so the client's
``_get_auth_token`` fell back to ``resolve_secret_from_env(token_key)`` where
``token_key`` defaults to ``AUTOM8Y_DATA_API_KEY`` -- NOT a service JWT. The
S2S call to autom8_data carried no Bearer (or the wrong key) and was rejected
(AUTH-TEB-001) -> every entity failed -> ``succeeded:0``.

The API DI path (dependencies.py:497-505) already injects a
``ServiceTokenAuthProvider``; the Lambda path did not. These tests pin the
contract that the Lambda path MUST inject the provider too, and that the
provider resolves ``SERVICE_CLIENT_SECRET`` through ``resolve_secret_from_env``
(the both-topologies-correct read: ``_ARN`` suffix on Lambda via the secrets
extension, bare name on ECS) rather than a bare ``os.environ.get``.

D4 guard (#149 scar): these tests drive the REAL production ``handler`` and do
NOT patch the ``DataServiceClient`` class wholesale -- doing so would hide the
``auth_provider`` kwarg, which is the exact thing under test. Instead the real
``DataServiceClient.__init__`` is spied to capture the kwarg while neutering its
heavy (network-touching) setup, and the per-instance workflow methods are
stubbed so the handler runs end-to-end without I/O.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation.workflows.base import WorkflowAction, WorkflowResult
from autom8_asana.client import AsanaClient
from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.lambda_handlers.workflow_handler import (
    WorkflowHandlerConfig,
    create_workflow_handler,
)

# Preserve the workflow_handler harness idiom (see test_workflow_handler.py):
# the production ``handler`` runs ``asyncio.run`` internally, so invoke it
# synchronously from plain ``def`` tests. xdist_group co-locates the module on a
# single worker; worker_isolated excludes it from the sharded run (the in-handler
# nested-loop + AsyncMock teardown SIGKILLs an xdist worker under CI pressure).
pytestmark = [
    pytest.mark.xdist_group("workflow_handler"),
    pytest.mark.worker_isolated,
]


def _make_workflow_result(*, succeeded: int = 8, total: int = 10) -> WorkflowResult:
    started = datetime(2026, 6, 24, 6, 0, 0, tzinfo=UTC)
    return WorkflowResult(
        workflow_id="insights-export",
        started_at=started,
        completed_at=started + timedelta(seconds=12.0),
        total=total,
        succeeded=succeeded,
        failed=total - succeeded,
        skipped=0,
        errors=[],
        metadata={},
    )


def _mock_workflow() -> MagicMock:
    wf = MagicMock(spec=WorkflowAction)
    wf.validate_async = AsyncMock(return_value=[])
    wf.enumerate_async = AsyncMock(return_value=[{"gid": "1"}])
    wf.execute_async = AsyncMock(return_value=_make_workflow_result())
    return wf


def _make_config() -> WorkflowHandlerConfig:
    # requires_data_client=True is the production insights-export shape -- this is
    # the branch (workflow_handler.py:155-161) that constructs DataServiceClient.
    return WorkflowHandlerConfig(
        workflow_factory=MagicMock(return_value=_mock_workflow()),
        workflow_id="insights-export",
        log_prefix="lambda_insights_export",
        default_params={"max_concurrency": 5},
        dms_namespace="Autom8y/AsanaInsights",
    )


class _ConstructorSpy:
    """Spies the REAL DataServiceClient.__init__ to capture the auth_provider
    kwarg the production handler passes, while neutering the client's heavy
    setup so the handler can run without touching the network.

    This deliberately does NOT replace the DataServiceClient class: the class
    identity, ``token_key`` semantics, and ``_get_auth_token`` wiring stay real.
    Only the constructor body is shimmed.
    """

    def __init__(self) -> None:
        self.captured_auth_provider: Any = "<<uncalled>>"
        self.call_count = 0

    def install(self, instance: DataServiceClient, **kwargs: Any) -> None:
        self.call_count += 1
        self.captured_auth_provider = kwargs.get("auth_provider")
        # Minimal attributes so the REAL async-context-manager protocol
        # (__aenter__/__aexit__ -> close()) runs cleanly without network setup.
        # ``async with`` resolves the dunders on the TYPE, not the instance, so
        # we keep the real DataServiceClient.__aenter__/__aexit__ and just give
        # close() the attributes it reads (client.py:383-387). No HTTP client is
        # ever created (self._client stays None), so no I/O occurs.
        instance._auth_provider = kwargs.get("auth_provider")
        instance._client = None
        instance._log = None


def _run_handler_capturing_auth_provider() -> _ConstructorSpy:
    """Invoke the production handler and return the constructor spy.

    AsanaClient is patched (prod-faithful: the auth question under test is the
    DataServiceClient path, and AsanaClient does heavy work in __init__). The
    real DataServiceClient class is preserved; only __init__ is shimmed to
    capture the auth_provider kwarg.
    """
    spy = _ConstructorSpy()

    def _fake_init(self: DataServiceClient, *args: Any, **kwargs: Any) -> None:
        spy.install(self, **kwargs)

    with (
        patch("autom8_asana.client.AsanaClient") as mock_asana_class,
        patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric"),
        patch.object(DataServiceClient, "__init__", _fake_init),
    ):
        mock_asana_class.return_value = MagicMock(spec=AsanaClient)
        handler = create_workflow_handler(_make_config())
        result = handler({}, MagicMock())
        # The handler must run to a successful completion; a 500 here would mean
        # the provider construction raised and we'd be asserting on the wrong path.
        assert result["statusCode"] == 200, f"handler did not complete: {result.get('body')}"
    return spy


class TestLambdaInjectsServiceTokenAuthProvider:
    """AC-1: the Lambda entrypoint must inject a ServiceTokenAuthProvider into
    DataServiceClient -- not construct it bare."""

    def test_handler_constructs_data_service_client_with_auth_provider(self) -> None:
        """RED on HEAD: handler passes auth_provider=None (bare DataServiceClient()).
        GREEN after fix: handler passes a real ServiceTokenAuthProvider.

        This pins the INJECTION contract at the handler altitude only. The
        provider's internal secret-read mechanism (AC-2) is deliberately
        neutralised here by no-op'ing ServiceTokenAuthProvider.__init__, so this
        test's RED/GREEN turns solely on whether the handler injects the
        provider -- not on how the provider reads its secret. That keeps the AC-1
        failure clean (assertion: auth_provider is not None) rather than
        incidental to the AC-2 mechanism.
        """
        from autom8_asana.auth.service_token import ServiceTokenAuthProvider

        # No-op the provider constructor: a bare object that is-a
        # ServiceTokenAuthProvider, constructible without any secret/TokenManager.
        def _noop_init(self: ServiceTokenAuthProvider, *args: Any, **kwargs: Any) -> None:
            return None

        with patch.object(ServiceTokenAuthProvider, "__init__", _noop_init):
            spy = _run_handler_capturing_auth_provider()

        assert spy.call_count == 1, "DataServiceClient should be constructed exactly once"
        assert spy.captured_auth_provider is not None, (
            "W-AUTH regression: Lambda handler constructed DataServiceClient() with "
            "no auth_provider -> _get_auth_token falls back to AUTOM8Y_DATA_API_KEY "
            "(not a service JWT) -> autom8_data rejects the S2S call -> succeeded:0. "
            "The handler MUST inject a ServiceTokenAuthProvider (mirroring "
            "dependencies.py:497-505)."
        )
        # Pin the provider TYPE, not merely truthiness, so a stray sentinel does
        # not satisfy the contract.
        from autom8_asana.auth.service_token import ServiceTokenAuthProvider

        assert isinstance(spy.captured_auth_provider, ServiceTokenAuthProvider), (
            "auth_provider must be a ServiceTokenAuthProvider instance, got "
            f"{type(spy.captured_auth_provider)!r}"
        )


class TestProviderResolvesSecretConventionAgnostic:
    """AC-2: the provider must read SERVICE_CLIENT_SECRET via
    resolve_secret_from_env (resolves the _ARN suffix on Lambda, falls back to
    bare on ECS) -- NOT bare os.environ.get, which is blind to the Lambda
    secret_arns/_ARN delivery convention."""

    def test_provider_uses_resolve_secret_from_env_for_client_secret(self) -> None:
        """RED on HEAD: provider reads bare os.environ['SERVICE_CLIENT_SECRET'];
        with only the _ARN form set (Lambda topology) it raises ValueError.
        GREEN after fix: provider calls resolve_secret_from_env('SERVICE_CLIENT_SECRET'),
        which resolves the _ARN form."""
        from autom8_asana.auth.service_token import ServiceTokenAuthProvider

        # Simulate the Lambda topology: the BARE name is UNSET; only the
        # _ARN-suffixed key exists (as the scheduled-lambda module delivers it).
        # resolve_secret_from_env is the helper that knows to read X_ARN first.
        resolved = {"SERVICE_CLIENT_SECRET": "jwt-secret-from-extension"}

        def _fake_resolve(name: str, *args: Any, **kwargs: Any) -> str:
            return resolved[name]

        with (
            patch(
                "autom8_asana.auth.service_token.resolve_secret_from_env",
                side_effect=_fake_resolve,
            ) as mock_resolve,
            patch("autom8y_core.TokenManager") as mock_tm,
            patch("autom8y_core.Config") as mock_config,
            patch.dict(
                "os.environ",
                {
                    "SERVICE_CLIENT_ID": "cid-123",
                    # Deliberately do NOT set bare SERVICE_CLIENT_SECRET: a
                    # bare os.environ.get read returns "" here and the provider
                    # would raise ValueError -- which is the HEAD bug.
                    "SERVICE_CLIENT_SECRET_ARN": "arn:aws:secretsmanager:...:SERVICE_CLIENT_SECRET",
                },
                clear=True,
            ),
        ):
            mock_tm.return_value = MagicMock()
            provider = ServiceTokenAuthProvider()

            mock_resolve.assert_any_call("SERVICE_CLIENT_SECRET")
            # The resolved value must flow into the TokenManager Config.
            _, config_kwargs = mock_config.call_args
            assert config_kwargs["client_secret"] == "jwt-secret-from-extension", (
                "provider must pass the resolve_secret_from_env-resolved secret "
                "into Config(client_secret=...), not an empty bare-env read"
            )
            assert provider is not None
