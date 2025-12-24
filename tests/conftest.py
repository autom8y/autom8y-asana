"""Shared pytest fixtures for autom8_asana tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def reset_settings_singleton():
    """Reset the settings singleton before and after each test.

    This ensures test isolation when tests modify environment variables
    that affect Pydantic Settings.
    """
    from autom8_asana.settings import reset_settings

    reset_settings()
    yield
    reset_settings()


@pytest.fixture(autouse=True)
def reset_registries():
    """Reset all registry singletons before and after each test.

    This ensures test isolation for:
    - ProjectTypeRegistry (entity type detection)
    - WorkspaceProjectRegistry (project discovery)
    """
    from autom8_asana.models.business.registry import (
        ProjectTypeRegistry,
        WorkspaceProjectRegistry,
    )

    # Reset before test - use classmethod to clear singletons
    ProjectTypeRegistry.reset()
    WorkspaceProjectRegistry.reset()

    yield

    # Reset after test
    ProjectTypeRegistry.reset()
    WorkspaceProjectRegistry.reset()
