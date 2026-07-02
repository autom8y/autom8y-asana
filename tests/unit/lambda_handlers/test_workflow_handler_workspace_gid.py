"""Prod-path workspace-GID contract for the generic workflow Lambda handler.

BRIDGE-WORKSPACE-GID (contente-onboarding-walkthrough first-attach fault,
prod structured log 2026-07-02T02:06:34Z):

    {"task_gid":"1213653428400851","error_type":"ValueError",
     "error_message":"Cannot discover workspace projects:
       client.default_workspace_gid is not set. Create client with workspace_gid
       parameter: AsanaClient(token=..., workspace_gid='...')",
     "event":"bridge_entity_failed"}

Root cause: the SHARED factory ``workflow_handler._execute`` constructed
``AsanaClient()`` with NO ``workspace_gid`` (workflow_handler.py:153 at HEAD).
The client's own fallback (``get_workspace_gid`` -> ``get_settings().asana``)
reads only the BARE ``ASANA_WORKSPACE_GID`` env var, which is UNSET on Lambda --
only the ``_ARN`` form is delivered via the secrets extension. So
``default_workspace_gid`` stayed ``None`` and the walkthrough's anchor step
(``WorkspaceProjectRegistry.discover_async``, registry.py:449-456) raised.

The sibling scheduled handlers already prove the pattern
(cache_warmer.py:447-449): resolve ``ASANA_WORKSPACE_GID`` via
``resolve_secret_from_env`` (which reads the ``_ARN`` form first) and pass
``workspace_gid=`` into ``AsanaClient``. This module pins the contract that the
SHARED factory does the same -- and that workflows which do NOT need workspace
discovery still construct cleanly when the var is absent (graceful None).

Harness idiom mirrors test_workflow_handler_auth_injection.py: the production
``handler`` runs ``asyncio.run`` internally, so it is invoked synchronously from
plain ``def`` tests. worker_isolated excludes the handler-invoking tests from the
sharded run (the in-handler nested-loop SIGKILLs an xdist worker under CI
pressure); xdist_group co-locates the module on a single worker.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation.workflows.base import WorkflowAction, WorkflowResult
from autom8_asana.client import AsanaClient
from autom8_asana.lambda_handlers.workflow_handler import (
    WorkflowHandlerConfig,
    create_workflow_handler,
)
from autom8_asana.models.business.registry import get_workspace_registry

pytestmark = [
    pytest.mark.xdist_group("workflow_handler"),
    pytest.mark.worker_isolated,
]

# The live prod task_gid (reference-only; the workspace GID itself is
# semi-sensitive and is never a real value in this suite -- a synthetic 16-digit
# stand-in is used everywhere a GID is asserted).
_SYNTHETIC_WORKSPACE_GID = "9990001112223334"


# --- Handler harness helpers (mirror test_workflow_handler_auth_injection.py) ---


def _make_workflow_result(*, succeeded: int = 8, total: int = 10) -> WorkflowResult:
    started = datetime(2026, 7, 2, 2, 6, 0, tzinfo=UTC)
    return WorkflowResult(
        workflow_id="onboarding-walkthrough",
        started_at=started,
        completed_at=started + timedelta(seconds=0.76),
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
    # requires_data_client=False takes the workspace-discovery-only branch
    # (workflow_handler.py else-clause): it still constructs AsanaClient at
    # workflow_handler.py:153 -- the exact line under test -- without dragging in
    # the DataServiceClient/ServiceToken S2S path (owned by the auth_injection
    # suite). fleet_namespace=None opts out of fleet emission side effects.
    return WorkflowHandlerConfig(
        workflow_factory=MagicMock(return_value=_mock_workflow()),
        workflow_id="onboarding-walkthrough",
        log_prefix="lambda_onboarding_walkthrough",
        default_params={"max_concurrency": 5},
        requires_data_client=False,
        fleet_namespace=None,
    )


def _run_handler_capturing_asana_kwargs(
    *, resolve_side_effect: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Invoke the production handler with resolve_secret_from_env stubbed.

    Returns ``(handler_response, asana_construction_kwargs)``. AsanaClient is
    patched to a spy class so the ``workspace_gid`` kwarg the handler passes is
    captured without doing the real (heavy) client construction.
    """
    with (
        patch("autom8_asana.client.AsanaClient") as mock_asana_class,
        patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric"),
        patch(
            "autom8_asana.lambda_handlers.workflow_handler.resolve_secret_from_env",
            side_effect=resolve_side_effect,
        ),
    ):
        mock_asana_class.return_value = MagicMock(spec=AsanaClient)
        handler = create_workflow_handler(_make_config())
        result = handler({}, MagicMock())
        assert mock_asana_class.call_count == 1, (
            "AsanaClient should be constructed exactly once per invocation, got "
            f"{mock_asana_class.call_count}"
        )
        _, asana_kwargs = mock_asana_class.call_args
    return result, asana_kwargs


class TestFactoryConstructsClientWithWorkspaceGid:
    """AC-1: the shared factory must resolve ASANA_WORKSPACE_GID (ARN-first) and
    pass it into AsanaClient(workspace_gid=...)."""

    def test_handler_passes_arn_resolved_workspace_gid_into_client(self) -> None:
        """RED on HEAD: factory builds bare ``AsanaClient()`` -> no workspace_gid
        kwarg -> the anchor's discover_async raises. GREEN after fix: factory
        resolves the GID via resolve_secret_from_env (the ARN-first read that
        works on Lambda) and threads it into AsanaClient(workspace_gid=...)."""

        def _resolve(name: str, *args: Any, **kwargs: Any) -> str:
            assert name == "ASANA_WORKSPACE_GID", (
                "factory must resolve the ASANA_WORKSPACE_GID key (the ARN-first "
                f"resolver reads ASANA_WORKSPACE_GID_ARN), got {name!r}"
            )
            return _SYNTHETIC_WORKSPACE_GID

        result, asana_kwargs = _run_handler_capturing_asana_kwargs(resolve_side_effect=_resolve)

        assert result["statusCode"] == 200, f"handler did not complete: {result.get('body')}"
        assert asana_kwargs.get("workspace_gid") == _SYNTHETIC_WORKSPACE_GID, (
            "BRIDGE-WORKSPACE-GID regression: shared factory constructed "
            "AsanaClient without the resolved workspace_gid -> "
            "default_workspace_gid stays None -> registry.discover_async raises "
            "'client.default_workspace_gid is not set' at the walkthrough anchor "
            "(prod log 2026-07-02T02:06:34Z). The factory MUST pass "
            "workspace_gid=resolve_secret_from_env('ASANA_WORKSPACE_GID') "
            "(mirroring cache_warmer.py:447-449)."
        )


class TestConstructedClientCarriesWorkspaceGid:
    """AC-2 (teeth): the kwarg the factory passes actually lands on
    ``default_workspace_gid`` -- the field the anchor guard reads (registry.py:451).
    Constructs a REAL AsanaClient (no network: explicit workspace_gid skips
    auto-detect, stub auth_provider skips EnvAuthProvider)."""

    def test_real_client_with_workspace_gid_sets_default_workspace_gid(self) -> None:
        client = AsanaClient(
            workspace_gid=_SYNTHETIC_WORKSPACE_GID,
            auth_provider=MagicMock(),
        )
        assert client.default_workspace_gid == _SYNTHETIC_WORKSPACE_GID, (
            "passing workspace_gid must set default_workspace_gid -- this is the "
            "field WorkspaceProjectRegistry.discover_async reads at registry.py:451"
        )


# --- The prod-fault reproduction (two-sided registry-guard canary) -----------
#
# This is the live surface that raised in prod. The RED variant reproduces the
# EXACT ValueError from the 2026-07-02T02:06:34Z log; the GREEN variant proves
# the guard bites ONLY when the GID is absent (no false-RED). The existing
# tests/unit/models/business/test_workspace_registry.py::TestDiscoverAsync
# ::test_discover_requires_workspace_gid covers the raise in isolation;
# this pairing ties it to the fix (GID present -> guard passes).


@dataclass
class _MockProject:
    gid: str
    name: str


def _mock_client_for_discovery(*, workspace_gid: str | None) -> MagicMock:
    mock_client = MagicMock()
    mock_client.default_workspace_gid = workspace_gid

    async def _collect() -> list[_MockProject]:
        return []

    iterator = MagicMock()
    iterator.collect = _collect
    mock_client.projects.list_async.return_value = iterator
    return mock_client


class TestAnchorGuardReproducesProdFault:
    """The walkthrough anchor step (registry.discover_async) is the raise-site."""

    _PROD_MSG_FRAGMENT = "client.default_workspace_gid is not set"

    async def test_discover_raises_exact_prod_valueerror_when_gid_absent(self) -> None:
        """RED (prod reproduction): a client whose default_workspace_gid is None
        (what bare ``AsanaClient()`` produced on Lambda) raises the exact prod
        ValueError at the anchor's workspace-project discovery."""
        registry = get_workspace_registry()
        client = _mock_client_for_discovery(workspace_gid=None)

        with pytest.raises(ValueError) as exc_info:
            await registry.discover_async(client)

        assert self._PROD_MSG_FRAGMENT in str(exc_info.value), (
            "must reproduce the 2026-07-02T02:06:34Z prod fault message"
        )

    async def test_discover_proceeds_when_gid_present(self) -> None:
        """GREEN (no-defect variant / teeth): with default_workspace_gid set --
        exactly what the fixed factory now delivers -- discover_async passes the
        guard and completes without the ValueError."""
        registry = get_workspace_registry()
        client = _mock_client_for_discovery(workspace_gid=_SYNTHETIC_WORKSPACE_GID)

        # Must NOT raise the prod ValueError; the guard bites only when GID absent.
        await registry.discover_async(client)
        client.projects.list_async.assert_called_once()


class TestSiblingsUnaffectedWhenWorkspaceEnvAbsent:
    """AC-3: workflows that do NOT need workspace discovery (insights-export,
    conversation-audit topology has no ASANA_WORKSPACE_GID) must still construct
    -- the factory degrades to workspace_gid=None, never hard-fails a sibling."""

    def test_handler_constructs_with_none_gid_and_completes_when_env_absent(
        self,
    ) -> None:
        def _resolve_raises(name: str, *args: Any, **kwargs: Any) -> str:
            # Mirrors resolve_secret_from_env's real behavior when neither
            # ASANA_WORKSPACE_GID nor its _ARN form is set.
            raise ValueError(f"No secret source for {name}")

        result, asana_kwargs = _run_handler_capturing_asana_kwargs(
            resolve_side_effect=_resolve_raises
        )

        assert result["statusCode"] == 200, (
            "graceful-None regression: a sibling workflow with no workspace env "
            f"must still construct and complete, got {result.get('body')}"
        )
        assert asana_kwargs.get("workspace_gid") is None, (
            "when the workspace env is absent the factory must pass "
            "workspace_gid=None (preserving the prior bare-construction behavior "
            "for insights/conversation_audit), not raise"
        )
