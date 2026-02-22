"""Unit tests for AutomationEngine.

Per TDD-AUTOMATION-LAYER: Test register/unregister, evaluate_async with mock rules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from autom8_asana.automation.base import TriggerCondition
from autom8_asana.automation.config import AutomationConfig
from autom8_asana.automation.engine import AutomationEngine
from autom8_asana.automation.events.types import EventType
from autom8_asana.persistence.models import AutomationResult, SaveResult

if TYPE_CHECKING:
    from autom8_asana.automation.context import AutomationContext


class MockRule:
    """Mock automation rule for testing."""

    def __init__(
        self,
        rule_id: str = "mock_rule",
        rule_name: str = "Mock Rule",
        should_trigger_result: bool = True,
        execute_result: AutomationResult | None = None,
        execute_error: Exception | None = None,
    ) -> None:
        self._id = rule_id
        self._name = rule_name
        self._should_trigger_result = should_trigger_result
        self._execute_result = execute_result
        self._execute_error = execute_error
        self._trigger = TriggerCondition(entity_type="Task", event=EventType.CREATED)
        self.execute_called = False
        self.execute_call_args: tuple[Any, ...] | None = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def trigger(self) -> TriggerCondition:
        return self._trigger

    def should_trigger(
        self,
        entity: Any,
        event: str,
        context: dict[str, Any],
    ) -> bool:
        return self._should_trigger_result

    async def execute_async(
        self,
        entity: Any,
        context: AutomationContext,
    ) -> AutomationResult:
        self.execute_called = True
        self.execute_call_args = (entity, context)

        if self._execute_error:
            raise self._execute_error

        if self._execute_result:
            return self._execute_result

        return AutomationResult(
            rule_id=self._id,
            rule_name=self._name,
            triggered_by_gid=entity.gid,
            triggered_by_type=type(entity).__name__,
            success=True,
        )


class MockEntity:
    """Mock entity for testing."""

    def __init__(self, gid: str = "123456") -> None:
        self.gid = gid


class TestAutomationEngineRegistration:
    """Tests for rule registration/unregistration."""

    @pytest.fixture
    def engine(self) -> AutomationEngine:
        """Create engine with default config."""
        config = AutomationConfig()
        return AutomationEngine(config)

    def test_register_rule(self, engine: AutomationEngine) -> None:
        """Test registering a rule."""
        rule = MockRule()
        engine.register(rule)

        assert len(engine.rules) == 1
        assert engine.rules[0] is rule

    def test_register_multiple_rules(self, engine: AutomationEngine) -> None:
        """Test registering multiple rules."""
        rule1 = MockRule(rule_id="rule_1", rule_name="Rule 1")
        rule2 = MockRule(rule_id="rule_2", rule_name="Rule 2")

        engine.register(rule1)
        engine.register(rule2)

        assert len(engine.rules) == 2

    def test_register_duplicate_id_raises(self, engine: AutomationEngine) -> None:
        """Test that registering duplicate ID raises ValueError."""
        rule1 = MockRule(rule_id="same_id")
        rule2 = MockRule(rule_id="same_id")

        engine.register(rule1)

        with pytest.raises(ValueError) as exc_info:
            engine.register(rule2)

        assert "already registered" in str(exc_info.value)

    def test_unregister_rule(self, engine: AutomationEngine) -> None:
        """Test unregistering a rule."""
        rule = MockRule(rule_id="to_remove")
        engine.register(rule)

        result = engine.unregister("to_remove")

        assert result is True
        assert len(engine.rules) == 0

    def test_unregister_nonexistent_rule(self, engine: AutomationEngine) -> None:
        """Test unregistering nonexistent rule returns False."""
        result = engine.unregister("nonexistent")

        assert result is False

    def test_rules_property_returns_copy(self, engine: AutomationEngine) -> None:
        """Test that rules property returns a copy."""
        rule = MockRule()
        engine.register(rule)

        rules = engine.rules
        rules.clear()  # Modify the returned list

        # Original list should be unaffected
        assert len(engine.rules) == 1


class TestAutomationEngineEnabled:
    """Tests for enabled/disabled behavior."""

    def test_enabled_by_default(self) -> None:
        """Test that engine is enabled by default."""
        config = AutomationConfig(enabled=True)
        engine = AutomationEngine(config)

        assert engine.enabled is True

    def test_disabled_via_config(self) -> None:
        """Test that engine can be disabled via config."""
        config = AutomationConfig(enabled=False)
        engine = AutomationEngine(config)

        assert engine.enabled is False

    def test_enabled_setter(self) -> None:
        """Test setting enabled property."""
        config = AutomationConfig()
        engine = AutomationEngine(config)

        engine.enabled = False
        assert engine.enabled is False

        engine.enabled = True
        assert engine.enabled is True


class TestAutomationEngineEvaluate:
    """Tests for evaluate_async method."""

    @pytest.fixture
    def engine(self) -> AutomationEngine:
        """Create engine with default config."""
        config = AutomationConfig()
        return AutomationEngine(config)

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock client."""
        return MagicMock()

    @pytest.fixture
    def mock_entity(self) -> MockEntity:
        """Create mock entity."""
        return MockEntity()

    @pytest.fixture
    def save_result(self, mock_entity: MockEntity) -> SaveResult:
        """Create SaveResult with one succeeded entity."""
        return SaveResult(succeeded=[mock_entity])

    @pytest.mark.asyncio
    async def test_evaluate_disabled_returns_empty(
        self,
        mock_client: MagicMock,
        save_result: SaveResult,
    ) -> None:
        """Test that evaluate returns empty when disabled."""
        config = AutomationConfig(enabled=False)
        engine = AutomationEngine(config)
        rule = MockRule()
        engine.register(rule)

        results = await engine.evaluate_async(save_result, mock_client)

        assert results == []
        assert rule.execute_called is False

    @pytest.mark.asyncio
    async def test_evaluate_no_rules_returns_empty(
        self,
        engine: AutomationEngine,
        mock_client: MagicMock,
        save_result: SaveResult,
    ) -> None:
        """Test that evaluate with no rules returns empty."""
        results = await engine.evaluate_async(save_result, mock_client)

        assert results == []

    @pytest.mark.asyncio
    async def test_evaluate_rule_should_not_trigger(
        self,
        engine: AutomationEngine,
        mock_client: MagicMock,
        save_result: SaveResult,
    ) -> None:
        """Test that rule not triggering produces no result."""
        rule = MockRule(should_trigger_result=False)
        engine.register(rule)

        results = await engine.evaluate_async(save_result, mock_client)

        assert results == []
        assert rule.execute_called is False

    @pytest.mark.asyncio
    async def test_evaluate_rule_triggers_and_executes(
        self,
        engine: AutomationEngine,
        mock_client: MagicMock,
        mock_entity: MockEntity,
        save_result: SaveResult,
    ) -> None:
        """Test that triggering rule executes and produces result."""
        rule = MockRule(should_trigger_result=True)
        engine.register(rule)

        results = await engine.evaluate_async(save_result, mock_client)

        assert len(results) == 1
        assert results[0].rule_id == "mock_rule"
        assert results[0].triggered_by_gid == mock_entity.gid
        assert results[0].success is True
        assert rule.execute_called is True

    @pytest.mark.asyncio
    async def test_evaluate_rule_execution_error_captured(
        self,
        engine: AutomationEngine,
        mock_client: MagicMock,
        save_result: SaveResult,
    ) -> None:
        """Test that rule execution error is captured, not propagated."""
        rule = MockRule(
            should_trigger_result=True,
            execute_error=RuntimeError("Execution failed"),
        )
        engine.register(rule)

        # Should not raise
        results = await engine.evaluate_async(save_result, mock_client)

        assert len(results) == 1
        assert results[0].success is False
        assert "Execution failed" in results[0].error

    @pytest.mark.asyncio
    async def test_evaluate_multiple_rules(
        self,
        engine: AutomationEngine,
        mock_client: MagicMock,
        save_result: SaveResult,
    ) -> None:
        """Test that multiple rules all execute."""
        rule1 = MockRule(rule_id="rule_1", rule_name="Rule 1")
        rule2 = MockRule(rule_id="rule_2", rule_name="Rule 2")
        engine.register(rule1)
        engine.register(rule2)

        results = await engine.evaluate_async(save_result, mock_client)

        assert len(results) == 2
        assert rule1.execute_called is True
        assert rule2.execute_called is True

    @pytest.mark.asyncio
    async def test_evaluate_loop_prevention_skips(
        self,
        mock_client: MagicMock,
        mock_entity: MockEntity,
    ) -> None:
        """Test that loop prevention skips repeated (entity, rule) pairs."""
        config = AutomationConfig(max_cascade_depth=5)
        engine = AutomationEngine(config)

        # Create rule that would trigger twice for same entity
        rule = MockRule(rule_id="loop_rule", should_trigger_result=True)
        engine.register(rule)

        # Create SaveResult with same entity twice (simulates nested trigger)
        save_result = SaveResult(succeeded=[mock_entity, mock_entity])

        results = await engine.evaluate_async(save_result, mock_client)

        # First triggers normally, second is skipped
        assert len(results) == 2
        # First result: executed
        assert results[0].success is True
        assert results[0].skipped_reason is None
        # Second result: skipped
        assert results[1].success is True
        assert results[1].skipped_reason == "circular_reference_prevented"

    @pytest.mark.asyncio
    async def test_evaluate_empty_succeeded_returns_empty(
        self,
        engine: AutomationEngine,
        mock_client: MagicMock,
    ) -> None:
        """Test that empty succeeded list produces no results."""
        rule = MockRule()
        engine.register(rule)
        save_result = SaveResult(succeeded=[])

        results = await engine.evaluate_async(save_result, mock_client)

        assert results == []
        assert rule.execute_called is False
