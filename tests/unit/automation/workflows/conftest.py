"""Shared fixtures for workflow tests."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from autom8_asana.lifecycle.config import LifecycleConfig


@pytest.fixture
def lifecycle_config() -> LifecycleConfig:
    """Lifecycle configuration loaded from YAML."""
    config_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "config"
        / "lifecycle_stages.yaml"
    )
    return LifecycleConfig(config_path)


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock AsanaClient."""
    client = MagicMock()
    client.tasks = MagicMock()
    client.sections = MagicMock()
    return client
