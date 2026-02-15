"""Shared fixtures for lifecycle engine tests."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.lifecycle.config import LifecycleConfig
from autom8_asana.models.business.process import Process, ProcessType


@pytest.fixture
def lifecycle_config() -> LifecycleConfig:
    """Lifecycle configuration loaded from YAML."""
    config_path = (
        Path(__file__).parent.parent.parent.parent / "config" / "lifecycle_stages.yaml"
    )
    return LifecycleConfig(config_path)


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock AsanaClient."""
    client = MagicMock()
    client.tasks = MagicMock()
    client.sections = MagicMock()
    return client


@pytest.fixture
def mock_process() -> Process:
    """Mock Process entity."""
    process = MagicMock(spec=Process)
    process.gid = "12345"
    process.name = "Test Process"
    process.process_type = ProcessType.SALES
    process.completed = False
    process.memberships = [
        {
            "project": {"gid": "1200944186565610", "name": "Sales Pipeline"},
            "section": {"gid": "sec1", "name": "Opportunity"},
        }
    ]
    return process


@pytest.fixture
def mock_business() -> MagicMock:
    """Mock Business entity."""
    business = MagicMock()
    business.gid = "biz1"
    business.name = "Test Business"
    business.dna_holder = None
    return business


@pytest.fixture
def mock_unit() -> MagicMock:
    """Mock Unit entity."""
    unit = MagicMock()
    unit.gid = "unit1"
    unit.name = "Test Unit"
    unit.processes = []
    unit.offer_holder = None
    return unit


@pytest.fixture
def mock_offer() -> MagicMock:
    """Mock Offer entity."""
    offer = MagicMock()
    offer.gid = "offer1"
    offer.name = "Test Offer"
    offer.memberships = [
        {
            "project": {"gid": "proj1", "name": "Offers"},
            "section": {"gid": "sec1", "name": "Active"},
        }
    ]
    return offer


@pytest.fixture
def mock_resolution_context(
    mock_business: MagicMock,
    mock_unit: MagicMock,
    mock_offer: MagicMock,
) -> AsyncMock:
    """Mock ResolutionContext."""
    ctx = AsyncMock()
    ctx.business_async = AsyncMock(return_value=mock_business)
    ctx.unit_async = AsyncMock(return_value=mock_unit)
    ctx.offer_async = AsyncMock(return_value=mock_offer)
    ctx.cache_entity = MagicMock()
    ctx.hydrate_branch_async = AsyncMock()
    ctx._trigger_entity = None

    # Make context manager work
    ctx.__aenter__ = AsyncMock(return_value=ctx)
    ctx.__aexit__ = AsyncMock(return_value=None)

    return ctx
