"""Tests for WorkflowRegistry and module-level registry helpers.

Per TDD sprint-2 Item 3: Verify registry registration, lookup,
duplicate handling, singleton behavior, and reset for test isolation.

Per ADR-bridge-invocation-model Decisions 1 and 5.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from autom8_asana.automation.workflows.registry import (
    WorkflowRegistry,
    get_workflow_registry,
    reset_workflow_registry,
)


def _make_mock_workflow(workflow_id: str) -> MagicMock:
    """Create a mock WorkflowAction with a given workflow_id."""
    wf = MagicMock()
    wf.workflow_id = workflow_id
    return wf


class TestWorkflowRegistryClass:
    """Tests for WorkflowRegistry class methods."""

    def test_registry_register_and_get(self) -> None:
        """Register a workflow and retrieve it by ID."""
        registry = WorkflowRegistry()
        wf = _make_mock_workflow("test-wf")

        registry.register(wf)

        assert registry.get("test-wf") is wf
        assert registry.get("nonexistent") is None

    def test_registry_duplicate_raises(self) -> None:
        """Registering the same workflow_id twice raises ValueError."""
        registry = WorkflowRegistry()
        wf1 = _make_mock_workflow("dup-wf")
        wf2 = _make_mock_workflow("dup-wf")

        registry.register(wf1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(wf2)

    def test_registry_list_ids(self) -> None:
        """list_ids returns sorted list of registered workflow IDs."""
        registry = WorkflowRegistry()
        registry.register(_make_mock_workflow("zebra-wf"))
        registry.register(_make_mock_workflow("alpha-wf"))

        ids = registry.list_ids()

        assert ids == ["alpha-wf", "zebra-wf"]


class TestGetWorkflowRegistry:
    """Tests for the module-level get_workflow_registry() singleton."""

    def setup_method(self) -> None:
        """Reset the registry before each test."""
        reset_workflow_registry()

    def teardown_method(self) -> None:
        """Reset the registry after each test."""
        reset_workflow_registry()

    def test_get_workflow_registry_singleton(self) -> None:
        """Consecutive calls return the same instance."""
        reg1 = get_workflow_registry()
        reg2 = get_workflow_registry()

        assert reg1 is reg2

    def test_reset_workflow_registry_creates_new_instance(self) -> None:
        """After reset, get_workflow_registry returns a new instance."""
        reg1 = get_workflow_registry()
        reset_workflow_registry()
        reg2 = get_workflow_registry()

        assert reg1 is not reg2

    def test_reset_clears_registered_workflows(self) -> None:
        """After reset, previously registered workflows are gone."""
        reg = get_workflow_registry()
        reg.register(_make_mock_workflow("ephemeral-wf"))

        reset_workflow_registry()

        new_reg = get_workflow_registry()
        assert new_reg.get("ephemeral-wf") is None
        assert new_reg.list_ids() == []
