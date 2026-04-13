"""Unit tests for AutomationContext.

Per TDD-AUTOMATION-LAYER: Test loop prevention (depth, visited set).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from autom8_asana.automation.config import AutomationConfig
from autom8_asana.automation.context import AutomationContext


class TestAutomationContext:
    """Tests for AutomationContext loop prevention."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock AsanaClient."""
        return MagicMock()

    @pytest.fixture
    def default_config(self) -> AutomationConfig:
        """Create default config with depth=5."""
        return AutomationConfig(max_cascade_depth=5)

    @pytest.fixture
    def context(
        self, mock_client: MagicMock, default_config: AutomationConfig
    ) -> AutomationContext:
        """Create default context."""
        return AutomationContext(
            client=mock_client,
            config=default_config,
            depth=0,
            visited=set(),
        )

    # --- can_continue tests ---

    def test_can_continue_fresh_context(self, context: AutomationContext) -> None:
        """Test that fresh context allows continuation."""
        assert context.can_continue("entity_1", "rule_1") is True

    def test_can_continue_depth_at_limit(
        self, mock_client: MagicMock, default_config: AutomationConfig
    ) -> None:
        """Test that depth at limit prevents continuation."""
        context = AutomationContext(
            client=mock_client,
            config=default_config,
            depth=5,  # At max depth
            visited=set(),
        )

        assert context.can_continue("entity_1", "rule_1") is False

    def test_can_continue_depth_exceeds_limit(
        self, mock_client: MagicMock, default_config: AutomationConfig
    ) -> None:
        """Test that depth exceeding limit prevents continuation."""
        context = AutomationContext(
            client=mock_client,
            config=default_config,
            depth=10,  # Way over max
            visited=set(),
        )

        assert context.can_continue("entity_1", "rule_1") is False

    def test_can_continue_visited_pair(self, context: AutomationContext) -> None:
        """Test that visited (entity, rule) pair prevents continuation."""
        context.mark_visited("entity_1", "rule_1")

        assert context.can_continue("entity_1", "rule_1") is False

    def test_can_continue_same_entity_different_rule(self, context: AutomationContext) -> None:
        """Test that same entity with different rule can continue."""
        context.mark_visited("entity_1", "rule_1")

        # Different rule is allowed
        assert context.can_continue("entity_1", "rule_2") is True

    def test_can_continue_different_entity_same_rule(self, context: AutomationContext) -> None:
        """Test that different entity with same rule can continue."""
        context.mark_visited("entity_1", "rule_1")

        # Different entity is allowed
        assert context.can_continue("entity_2", "rule_1") is True

    # --- mark_visited tests ---

    def test_mark_visited_adds_pair(self, context: AutomationContext) -> None:
        """Test that mark_visited adds the (entity, rule) pair."""
        context.mark_visited("entity_1", "rule_1")

        assert ("entity_1", "rule_1") in context.visited

    def test_mark_visited_multiple_pairs(self, context: AutomationContext) -> None:
        """Test that multiple pairs can be marked visited."""
        context.mark_visited("entity_1", "rule_1")
        context.mark_visited("entity_2", "rule_2")

        assert ("entity_1", "rule_1") in context.visited
        assert ("entity_2", "rule_2") in context.visited

    # --- child_context tests ---

    def test_child_context_increments_depth(self, context: AutomationContext) -> None:
        """Test that child_context increments depth."""
        child = context.child_context()

        assert child.depth == context.depth + 1

    def test_child_context_shares_visited(self, context: AutomationContext) -> None:
        """Test that child_context shares visited set reference."""
        context.mark_visited("entity_1", "rule_1")
        child = context.child_context()

        # Child sees parent's visited entries
        assert ("entity_1", "rule_1") in child.visited

        # Modifications in child affect parent (shared reference)
        child.mark_visited("entity_2", "rule_2")
        assert ("entity_2", "rule_2") in context.visited

    def test_child_context_preserves_client(self, context: AutomationContext) -> None:
        """Test that child_context preserves client reference."""
        child = context.child_context()

        assert child.client is context.client

    def test_child_context_preserves_config(self, context: AutomationContext) -> None:
        """Test that child_context preserves config reference."""
        child = context.child_context()

        assert child.config is context.config

    def test_child_context_preserves_save_result(self, context: AutomationContext) -> None:
        """Test that child_context preserves save_result reference."""
        mock_result = MagicMock()
        context.save_result = mock_result
        child = context.child_context()

        assert child.save_result is mock_result

    def test_multiple_child_contexts_depth(self, context: AutomationContext) -> None:
        """Test that nested child contexts increment depth correctly."""
        child1 = context.child_context()
        child2 = child1.child_context()
        child3 = child2.child_context()

        assert context.depth == 0
        assert child1.depth == 1
        assert child2.depth == 2
        assert child3.depth == 3

    def test_depth_limit_prevents_deep_nesting(self, mock_client: MagicMock) -> None:
        """Test that depth limit prevents unbounded nesting."""
        config = AutomationConfig(max_cascade_depth=3)
        context = AutomationContext(
            client=mock_client,
            config=config,
            depth=0,
            visited=set(),
        )

        # Can continue at depth 0, 1, 2
        assert context.can_continue("e1", "r1") is True

        child1 = context.child_context()
        assert child1.can_continue("e2", "r1") is True

        child2 = child1.child_context()
        assert child2.can_continue("e3", "r1") is True

        child3 = child2.child_context()
        # Depth 3 = max_cascade_depth, cannot continue
        assert child3.can_continue("e4", "r1") is False
