"""Shared pytest fixtures for autom8_asana tests."""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# R4-FIX-002: schemathesis 4.14.3 / pytest-xdist 3.x incompatibility
#
# schemathesis.pytest.xdist.XdistReportingPlugin.pytest_testnodedown (line 351
# of xdist.py) dereferences ``node.workeroutput`` unconditionally. In
# pytest-xdist 3.x the controller-side ``WorkerController`` only gains a
# ``workeroutput`` attribute when the worker exits cleanly via the
# ``workerfinished`` event. If a worker errors out (``worker_errordown``),
# the attribute is never set and the hook raises ``AttributeError``,
# triggering pytest ``INTERNALERROR`` (exit code 3).
#
# Prior remediation attempts (FIX-004 fae6ff1e, R3-FIX-003 2341b32b) failed:
#   - fae6ff1e patched the plugin *instance* from inside ``pytest_configure``,
#     but pluggy caches the hook implementation reference at registration
#     time (``pluggy._manager`` stores ``getattr(plugin, hook_name)`` when the
#     plugin is registered). Mutating the instance attribute after pluggy has
#     already snapshotted it does nothing - pluggy keeps calling the original
#     unpatched method.
#   - 2341b32b pinned schemathesis<4.15.0, but the same bug exists unchanged
#     in 4.14.3 and earlier.
#
# Correct fix: patch the *class method* inside ``pytest_configure``, which
# pytest guarantees runs before plugin registration. This ensures the patch
# is applied before schemathesis calls
# ``pluginmanager.register(XdistReportingPlugin())``, regardless of conftest
# import ordering in xdist workers.
# ---------------------------------------------------------------------------


def pytest_configure(config):  # type: ignore[no-untyped-def]
    """Patch schemathesis xdist plugin before pluggy registration."""
    try:
        from schemathesis.pytest import xdist as _sx_xdist

        _original = _sx_xdist.XdistReportingPlugin.pytest_testnodedown

        def _safe_testnodedown(self, node, error):  # type: ignore[no-untyped-def]
            # Skip the hook entirely if the worker never populated workeroutput
            # (i.e. it errored out before sending the workerfinished event).
            if not hasattr(node, "workeroutput"):
                return None
            return _original(self, node, error)

        _sx_xdist.XdistReportingPlugin.pytest_testnodedown = _safe_testnodedown
    except ImportError:
        # schemathesis not installed - nothing to patch.
        pass


# Set test environment BEFORE any model imports.
# This relaxes AsanaResource.gid pattern validation (production: ^\d{1,64}$, test: any string)
# and controls other environment-gated behaviors.
# Force-set (not setdefault) because shell may have AUTOM8Y_ENV=local.
os.environ["AUTOM8Y_ENV"] = "test"

# Bypass Autom8yBaseSettings production URL guard in test context.
# AuthSettings.jwks_url defaults to the production autom8y.io domain;
# the base-settings SDK guard rejects it when AUTOM8Y_ENV=test.
# This must be set BEFORE any AuthSettings instantiation.
os.environ.setdefault("AUTH__JWKS_URL", "http://localhost:8000/.well-known/jwks.json")

from unittest.mock import AsyncMock

import pytest
from autom8y_log.testing import MockLogger

from autom8_asana.config import AsanaConfig


class MockHTTPClient:
    """Mock HTTP client for testing (8-method superset)."""

    def __init__(self) -> None:
        self.get = AsyncMock()
        self.post = AsyncMock()
        self.put = AsyncMock()
        self.delete = AsyncMock()
        self.request = AsyncMock()
        self.get_paginated = AsyncMock()
        self.post_multipart = AsyncMock()
        self.get_stream_url = AsyncMock()


class MockAuthProvider:
    """Mock auth provider for testing."""

    def get_secret(self, key: str) -> str:
        return "test-token"


@pytest.fixture
def mock_http() -> MockHTTPClient:
    """Create a mock HTTP client."""
    return MockHTTPClient()


@pytest.fixture
def config() -> AsanaConfig:
    """Create an AsanaConfig for testing."""
    return AsanaConfig()


@pytest.fixture
def auth_provider() -> MockAuthProvider:
    """Create a mock auth provider."""
    return MockAuthProvider()


@pytest.fixture
def logger() -> MockLogger:
    """SDK MockLogger for capturing and asserting log calls.

    Uses autom8y-log SDK MockLogger which stores _LogEntry objects
    in .entries (not .messages). Use logger.assert_logged(level, event)
    or logger.get_events(level) for assertions.
    """
    return MockLogger()


@pytest.fixture(autouse=True, scope="session")
def _bootstrap_session():
    """Bootstrap the application once per test session.

    Populates ProjectTypeRegistry before any tests run. Individual tests
    that call SystemContext.reset_all() will get re-populated via
    _ensure_bootstrapped() on first registry access.

    Also resolves NameGid forward references on all Pydantic models.
    Model files use ``from __future__ import annotations`` with NameGid
    imported only under TYPE_CHECKING, so Pydantic cannot resolve the
    forward-reference string without an explicit model_rebuild() call.
    Rebuilding Task first propagates to all BusinessEntity subclasses.
    """
    from autom8_asana.models.business._bootstrap import bootstrap

    bootstrap()

    # ------------------------------------------------------------------
    # Resolve NameGid forward references for all resource models.
    # Must happen after bootstrap() so all model modules are loaded.
    # ------------------------------------------------------------------
    from autom8_asana.models.attachment import Attachment
    from autom8_asana.models.common import NameGid
    from autom8_asana.models.custom_field import (
        CustomField,
        CustomFieldSetting,
    )
    from autom8_asana.models.goal import Goal, GoalMembership, GoalMetric
    from autom8_asana.models.portfolio import Portfolio
    from autom8_asana.models.project import Project
    from autom8_asana.models.section import Section
    from autom8_asana.models.story import Story
    from autom8_asana.models.tag import Tag
    from autom8_asana.models.task import Task
    from autom8_asana.models.team import Team, TeamMembership
    from autom8_asana.models.user import User
    from autom8_asana.models.webhook import Webhook, WebhookFilter
    from autom8_asana.models.workspace import Workspace

    _ns: dict[str, type] = {"NameGid": NameGid}

    # Task first -- BusinessEntity and all business models inherit from it
    Task.model_rebuild(_types_namespace=_ns)

    for model_cls in (
        Attachment,
        CustomField,
        CustomFieldSetting,
        Goal,
        GoalMembership,
        GoalMetric,
        Portfolio,
        Project,
        Section,
        Story,
        Tag,
        Team,
        TeamMembership,
        User,
        Webhook,
        WebhookFilter,
        Workspace,
    ):
        model_cls.model_rebuild(_types_namespace=_ns)


@pytest.fixture(autouse=True)
def reset_all_singletons():
    """Reset all singletons before and after each test.

    Per QW-5: Uses SystemContext.reset_all() to ensure complete test
    isolation across all registries, caches, and settings in one call.
    """
    from autom8_asana.core.system_context import SystemContext

    SystemContext.reset_all()
    yield
    SystemContext.reset_all()
