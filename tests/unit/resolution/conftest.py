"""Shared fixtures for resolution tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.models.business.base import BusinessEntity
from autom8_asana.models.business.business import Business
from autom8_asana.models.business.contact import Contact, ContactHolder
from autom8_asana.models.business.process import Process, ProcessType
from autom8_asana.models.business.unit import Unit


@pytest.fixture
def mock_client() -> MagicMock:
    """Create mock AsanaClient."""
    client = MagicMock()
    client.tasks = MagicMock()
    client.tasks.get_async = AsyncMock()
    client.tasks.subtasks_async = MagicMock()
    client.tasks.dependencies_async = MagicMock()
    return client


@pytest.fixture
def mock_business() -> Business:
    """Create mock Business entity."""
    business = Business(
        gid="business-123",
        name="Test Business",
        resource_type="task",
    )
    return business


@pytest.fixture
def mock_unit() -> Unit:
    """Create mock Unit entity."""
    unit = Unit(
        gid="unit-456",
        name="Test Unit",
        resource_type="task",
    )
    return unit


@pytest.fixture
def mock_contact() -> Contact:
    """Create mock Contact entity."""
    contact = Contact(
        gid="contact-789",
        name="Test Contact",
        resource_type="task",
    )
    return contact


@pytest.fixture
def mock_process() -> Process:
    """Create mock Process entity."""
    process = Process(
        gid="process-101",
        name="Test Process",
        resource_type="task",
    )
    return process


@pytest.fixture
def mock_contact_holder() -> ContactHolder:
    """Create mock ContactHolder."""
    holder = ContactHolder(
        gid="holder-999",
        name="Contacts",
        resource_type="task",
    )
    return holder


def make_mock_task(gid: str, name: str, **kwargs: Any) -> MagicMock:
    """Helper to create mock task objects."""
    task = MagicMock()
    task.gid = gid
    task.name = name
    task.resource_type = "task"
    task.model_dump.return_value = {
        "gid": gid,
        "name": name,
        "resource_type": "task",
        **kwargs,
    }
    for key, value in kwargs.items():
        setattr(task, key, value)
    return task


def make_business_entity(gid: str, name: str, **kwargs: Any) -> BusinessEntity:
    """Helper to create BusinessEntity instances."""
    return BusinessEntity(
        gid=gid,
        name=name,
        resource_type="task",
        **kwargs,
    )
