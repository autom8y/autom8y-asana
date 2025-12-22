"""Shared fixtures for persistence integration tests.

Provides live API client fixtures and cleanup utilities for
testing against the real Asana API.

Required Environment Variables:
- ASANA_ACCESS_TOKEN: Valid Asana Personal Access Token
- ASANA_WORKSPACE_GID: Workspace GID for testing
- ASANA_PROJECT_GID: Project GID for creating test tasks
"""

from __future__ import annotations

import os

import pytest

# Note: These imports assume the client module exists
# from autom8_asana.client import AsanaClient


# ---------------------------------------------------------------------------
# Environment Variable Helpers
# ---------------------------------------------------------------------------


def get_env_or_skip(name: str) -> str:
    """Get environment variable or skip test."""
    value = os.getenv(name)
    if not value:
        pytest.skip(f"Environment variable {name} not set")
    return value


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def asana_token() -> str:
    """Get Asana access token from environment."""
    return get_env_or_skip("ASANA_ACCESS_TOKEN")


@pytest.fixture
def workspace_gid() -> str:
    """Get test workspace GID from environment."""
    return get_env_or_skip("ASANA_WORKSPACE_GID")


@pytest.fixture
def project_gid() -> str:
    """Get test project GID from environment."""
    return get_env_or_skip("ASANA_PROJECT_GID")


# Uncomment when AsanaClient is available:
#
# @pytest.fixture
# async def live_client(asana_token: str) -> AsyncIterator[AsanaClient]:
#     """Create real AsanaClient for integration tests."""
#     client = AsanaClient(access_token=asana_token)
#     yield client
#     # Cleanup if needed
#
#
# @pytest.fixture
# async def cleanup_tasks(live_client: AsanaClient) -> AsyncIterator[list[str]]:
#     """Track tasks created during tests for cleanup."""
#     created_gids: list[str] = []
#     yield created_gids
#
#     # Cleanup after test
#     for gid in created_gids:
#         try:
#             await live_client.tasks.delete_async(gid)
#         except Exception:
#             pass  # Ignore cleanup errors
