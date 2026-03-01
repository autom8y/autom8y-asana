"""Shared fixtures for workflow tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

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


# --- ResolutionContext fixture (per TDD-SPRINT-C D-09, D-10) ---

# Patch target for ResolutionContext in insights_export module
_RC_PATCH_PATH = "autom8_asana.automation.workflows.insights_export.ResolutionContext"


def _make_mock_business(
    office_phone: str | None = "+17705753103",
    vertical: str | None = "chiropractic",
    name: str = "Test Business",
) -> MagicMock:
    """Create a mock Business entity returned by ResolutionContext.

    This helper is composed with the mock_resolution_context fixture
    (per D-09). Tests that need non-default business attributes call
    this function and reconfigure the fixture's mock.
    """
    business = MagicMock()
    business.office_phone = office_phone
    business.vertical = vertical
    business.name = name
    return business


@pytest.fixture
def mock_resolution_context():
    """Pre-configured ResolutionContext patch for insights export tests.

    Yields a namespace with:
        .mock_rc: The patched ResolutionContext class mock.
        .mock_ctx: The async context manager instance.
        .mock_business: The default Business mock (phone, vertical, name).
        .set_business(**kwargs): Factory to reconfigure with custom attributes.

    Usage (default business):
        def test_something(self, mock_resolution_context):
            # ResolutionContext is already patched
            result = await _enumerate_and_execute(wf)

    Usage (custom business):
        def test_missing_phone(self, mock_resolution_context):
            mock_resolution_context.set_business(office_phone=None)
            result = await _enumerate_and_execute(wf)
    """
    with patch(_RC_PATCH_PATH) as mock_rc:
        mock_ctx = AsyncMock()
        mock_business = _make_mock_business()
        mock_ctx.business_async = AsyncMock(return_value=mock_business)
        mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

        class _Namespace:
            """Mutable namespace for fixture state."""

            pass

        ns = _Namespace()
        ns.mock_rc = mock_rc
        ns.mock_ctx = mock_ctx
        ns.mock_business = mock_business

        def set_business(**kwargs: Any) -> MagicMock:
            """Reconfigure the mock business with custom attributes.

            Args:
                **kwargs: Passed to _make_mock_business (office_phone, vertical, name).

            Returns:
                The new mock business (also wired into mock_ctx).
            """
            new_business = _make_mock_business(**kwargs)
            ns.mock_business = new_business
            mock_ctx.business_async = AsyncMock(return_value=new_business)
            return new_business

        ns.set_business = set_business

        yield ns
