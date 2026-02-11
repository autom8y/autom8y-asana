"""Shared fixtures for cache module tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_batch_client() -> MagicMock:
    """Create a mock BatchClient."""
    client = MagicMock()
    client.execute_async = AsyncMock(return_value=[])
    return client
