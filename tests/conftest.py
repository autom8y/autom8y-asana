"""Shared pytest fixtures for autom8_asana tests."""

from __future__ import annotations

import os

# Bypass Autom8yBaseSettings production URL guard in test context.
# AuthSettings.jwks_url defaults to the production autom8y.io domain;
# the base-settings SDK guard rejects it when AUTOM8Y_ENV=test.
# This must be set BEFORE any AuthSettings instantiation.
os.environ.setdefault("AUTH__JWKS_URL", "http://localhost:8000/.well-known/jwks.json")

from typing import Any
from unittest.mock import AsyncMock, MagicMock

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


class MockClientBuilder:
    """Builder pattern for mock AsanaClient.

    Provides consistent mock client construction with explicit
    opt-in for each capability (batch, http, cache, etc.).

    Example:
        >>> client = (MockClientBuilder()
        ...     .with_batch(results=[success_result])
        ...     .with_http()
        ...     .build())
    """

    def __init__(self) -> None:
        self._client = MagicMock()
        self._client._log = None

    def with_workspace_gid(self, gid: str = "workspace_123") -> MockClientBuilder:
        """Set default workspace GID."""
        self._client.default_workspace_gid = gid
        return self

    def with_batch(
        self,
        results: list[Any] | None = None,
    ) -> MockClientBuilder:
        """Add mock batch client with execute_async."""
        batch_mock = MagicMock()
        batch_mock.execute_async = AsyncMock(return_value=results or [])
        self._client.batch = batch_mock
        return self

    def with_http(
        self,
        response: dict[str, Any] | None = None,
    ) -> MockClientBuilder:
        """Add mock HTTP client."""
        http_mock = AsyncMock()
        http_mock.request = AsyncMock(return_value=response or {"data": {}})
        self._client._http = http_mock
        return self

    def with_cache(self, cache_provider: Any = None) -> MockClientBuilder:
        """Add cache provider to client."""
        self._client._cache = cache_provider
        return self

    def with_projects_list(
        self,
        projects: list[Any] | None = None,
    ) -> MockClientBuilder:
        """Add mock projects.list_async with collect() support."""
        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(return_value=projects or [])
        self._client.projects = MagicMock()
        self._client.projects.list_async = MagicMock(return_value=mock_iterator)
        return self

    def with_tasks(self) -> MockClientBuilder:
        """Add mock tasks client."""
        self._client.tasks = MagicMock()
        self._client.tasks.update_async = AsyncMock(return_value=MagicMock())
        self._client.tasks.get_async = AsyncMock(return_value=MagicMock())
        return self

    def build(self) -> MagicMock:
        """Build and return the mock client."""
        return self._client


@pytest.fixture
def mock_client_builder() -> type[MockClientBuilder]:
    """Provide MockClientBuilder class for test customization."""
    return MockClientBuilder


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
