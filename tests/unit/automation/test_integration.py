"""Integration tests for the Automation Layer.

Per TDD-AUTOMATION-LAYER Phase 3: Verify end-to-end wiring and full flow.

These tests verify that:
1. AsanaConfig.automation integration is complete (FR-008)
2. client.automation property returns AutomationEngine (FR-009)
3. Rule registration works end-to-end (FR-010)
4. SaveSession commit triggers AutomationEngine evaluation (FR-001, FR-002)
5. AutomationResult is returned in SaveResult (FR-003, FR-007)
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation import (
    AutomationConfig,
    AutomationEngine,
    EventType,
    PipelineConversionRule,
    TriggerCondition,
)
from autom8_asana.automation.config import PipelineStage
from autom8_asana.config import AsanaConfig
from autom8_asana.models.common import NameGid
from autom8_asana.persistence.models import (
    ActionOperation,
    ActionResult,
    ActionType,
    AutomationResult,
    SaveResult,
)

if TYPE_CHECKING:
    from autom8_asana.automation.context import AutomationContext

# --- Mock Classes for Integration Testing ---


class MockProcessType(Enum):
    """Mock ProcessType for testing."""

    SALES = "sales"
    ONBOARDING = "onboarding"


class MockProcessSection(Enum):
    """Mock ProcessSection for testing."""

    CONVERTED = "converted"
    ACTIVE = "active"


class _MockProcessBase:
    """Base Mock Process entity for integration tests."""

    def __init__(
        self,
        gid: str = "process_123",
        name: str | None = "Test Process",
        process_type: MockProcessType = MockProcessType.SALES,
    ) -> None:
        self.gid = gid
        self.name = name
        self.process_type = process_type
        self._business = None
        self._unit = None
        self._is_new = False

    @property
    def business(self) -> Any:
        return self._business

    @property
    def unit(self) -> Any:
        return self._unit

    def model_dump(self) -> dict[str, Any]:
        """Pydantic-like model_dump for change tracking compatibility."""
        return {
            "gid": self.gid,
            "name": self.name,
            "process_type": self.process_type.value if self.process_type else None,
        }


# Named "MockProcess" for tests that explicitly check for MockProcess
MockProcess = _MockProcessBase


# Named "Process" for tests that need TriggerCondition entity_type matching
class Process(_MockProcessBase):
    """Process entity mock with correct class name for TriggerCondition matching."""

    pass


class MockTask:
    """Mock Task for template task."""

    def __init__(
        self,
        gid: str = "task_123",
        name: str | None = None,
        notes: str | None = None,
    ) -> None:
        self.gid = gid
        self.name = name
        self.notes = notes


class MockSection:
    """Mock Section for template section."""

    def __init__(self, gid: str = "section_123", name: str | None = None) -> None:
        self.gid = gid
        self.name = name


class MockPageIterator:
    """Mock PageIterator that returns items via collect()."""

    def __init__(self, items: list[Any]) -> None:
        self._items = items

    async def collect(self) -> list[Any]:
        return self._items


# --- Test Classes ---


class TestAsanaConfigAutomationIntegration:
    """Tests for AsanaConfig.automation field (FR-008, FR-009)."""

    def test_asana_config_has_automation_field(self) -> None:
        """FR-008: AsanaConfig should include automation: AutomationConfig."""
        config = AsanaConfig()

        assert hasattr(config, "automation")
        assert isinstance(config.automation, AutomationConfig)

    def test_asana_config_default_automation_enabled(self) -> None:
        """Default automation config should have enabled=True (per TDD-AUTOMATION-LAYER)."""
        config = AsanaConfig()

        # Per AutomationConfig defaults, enabled=True
        assert config.automation.enabled is True

    def test_asana_config_with_automation_enabled(self) -> None:
        """AsanaConfig can be created with automation enabled."""
        automation_config = AutomationConfig(
            enabled=True,
            max_cascade_depth=5,
            pipeline_stages={
                "sales": PipelineStage(project_gid="123"),
                "onboarding": PipelineStage(project_gid="456"),
            },
        )
        config = AsanaConfig(automation=automation_config)

        assert config.automation.enabled is True
        assert config.automation.max_cascade_depth == 5
        assert config.automation.pipeline_stages["sales"].project_gid == "123"


class TestClientAutomationProperty:
    """Tests for client.automation property (FR-009)."""

    def test_client_automation_none_when_disabled(self) -> None:
        """FR-009: client.automation is None when automation disabled."""
        # Mock the client with disabled automation
        with patch("autom8_asana.client.AsanaHttpClient"):
            from autom8_asana.client import AsanaClient

            config = AsanaConfig(automation=AutomationConfig(enabled=False))

            # Create client with mocked HTTP and workspace detection
            with patch.object(AsanaClient, "_auto_detect_workspace", return_value=None):
                client = AsanaClient(token="test_token", config=config)

                assert client.automation is None

    def test_client_automation_present_when_enabled(self) -> None:
        """FR-009: client.automation is AutomationEngine when enabled."""
        with patch("autom8_asana.client.AsanaHttpClient"):
            from autom8_asana.client import AsanaClient

            config = AsanaConfig(automation=AutomationConfig(enabled=True))

            with patch.object(AsanaClient, "_auto_detect_workspace", return_value=None):
                client = AsanaClient(token="test_token", config=config)

                assert client.automation is not None
                assert isinstance(client.automation, AutomationEngine)


class TestRuleRegistrationEndToEnd:
    """Tests for rule registration via client.automation (FR-010)."""

    def test_register_pipeline_conversion_rule(self) -> None:
        """FR-010: Consumer can register PipelineConversionRule."""
        with patch("autom8_asana.client.AsanaHttpClient"):
            from autom8_asana.client import AsanaClient

            config = AsanaConfig(
                automation=AutomationConfig(
                    enabled=True,
                    pipeline_stages={"onboarding": PipelineStage(project_gid="123456")},
                )
            )

            with patch.object(AsanaClient, "_auto_detect_workspace", return_value=None):
                client = AsanaClient(token="test_token", config=config)

                # Register the built-in rule
                rule = PipelineConversionRule()
                client.automation.register(rule)

                assert len(client.automation.rules) == 1
                assert client.automation.rules[0].id == "pipeline_sales_to_onboarding"

    def test_register_custom_rule(self) -> None:
        """FR-010: Consumer can register custom rules."""
        with patch("autom8_asana.client.AsanaHttpClient"):
            from autom8_asana.client import AsanaClient

            config = AsanaConfig(automation=AutomationConfig(enabled=True))

            with patch.object(AsanaClient, "_auto_detect_workspace", return_value=None):
                client = AsanaClient(token="test_token", config=config)

                # Create and register custom rule
                class CustomRule:
                    @property
                    def id(self) -> str:
                        return "custom_rule"

                    @property
                    def name(self) -> str:
                        return "Custom Rule"

                    @property
                    def trigger(self) -> TriggerCondition:
                        return TriggerCondition(entity_type="Task", event=EventType.UPDATED)

                    def should_trigger(
                        self, entity: Any, event: str, context: dict[str, Any]
                    ) -> bool:
                        return True

                    async def execute_async(
                        self, entity: Any, context: AutomationContext
                    ) -> AutomationResult:
                        return AutomationResult(
                            rule_id=self.id,
                            rule_name=self.name,
                            triggered_by_gid=entity.gid,
                            triggered_by_type=type(entity).__name__,
                            success=True,
                        )

                client.automation.register(CustomRule())

                assert len(client.automation.rules) == 1
                assert client.automation.rules[0].id == "custom_rule"


class TestSaveSessionAutomationTrigger:
    """Tests for SaveSession commit triggering automation (FR-001, FR-002, FR-003)."""

    async def test_commit_triggers_automation_evaluation(self) -> None:
        """FR-001: SaveSession.commit_async calls AutomationEngine.evaluate_async."""
        # Create mock client components
        mock_http = MagicMock()
        mock_batch = MagicMock()
        mock_batch.execute_async = AsyncMock(return_value=[])

        with patch("autom8_asana.client.AsanaHttpClient", return_value=mock_http):
            from autom8_asana.client import AsanaClient
            from autom8_asana.persistence import SaveSession

            config = AsanaConfig(automation=AutomationConfig(enabled=True))

            with patch.object(AsanaClient, "_auto_detect_workspace", return_value=None):
                client = AsanaClient(token="test_token", config=config)
                client._batch = mock_batch

                # Create a mock entity
                mock_entity = MagicMock()
                mock_entity.gid = "entity_123"

                # Mock the automation engine's evaluate_async
                mock_auto_result = AutomationResult(
                    rule_id="test_rule",
                    rule_name="Test Rule",
                    triggered_by_gid="entity_123",
                    triggered_by_type="MagicMock",
                    success=True,
                )

                # Create session
                session = SaveSession(
                    client=client,
                    automation_enabled=True,
                )

                # Track the entity
                session._tracker._entities["entity_123"] = mock_entity
                session._tracker._snapshots["entity_123"] = {}

                # Create a SaveResult with our entity
                mock_save_result = SaveResult(succeeded=[mock_entity])

                with patch.object(
                    session._pipeline,
                    "execute_with_actions",
                    new_callable=AsyncMock,
                    return_value=(mock_save_result, []),
                ):
                    with patch.object(
                        client.automation,
                        "evaluate_async",
                        new_callable=AsyncMock,
                        return_value=[mock_auto_result],
                    ) as mock_evaluate:
                        result = await session.commit_async()

                        # Verify automation was called
                        mock_evaluate.assert_called_once()
                        # Verify automation results are in SaveResult
                        assert len(result.automation_results) == 1
                        assert result.automation_results[0].rule_id == "test_rule"

    async def test_automation_disabled_skips_evaluation(self) -> None:
        """FR-001: Automation disabled skips evaluation."""
        mock_http = MagicMock()
        mock_batch = MagicMock()
        mock_batch.execute_async = AsyncMock(return_value=[])

        with patch("autom8_asana.client.AsanaHttpClient", return_value=mock_http):
            from autom8_asana.client import AsanaClient
            from autom8_asana.persistence import SaveSession

            config = AsanaConfig(automation=AutomationConfig(enabled=False))

            with patch.object(AsanaClient, "_auto_detect_workspace", return_value=None):
                client = AsanaClient(token="test_token", config=config)
                client._batch = mock_batch

                # Session with automation explicitly disabled
                session = SaveSession(
                    client=client,
                    automation_enabled=False,
                )

                mock_entity = MagicMock()
                mock_entity.gid = "entity_123"

                # Track entity
                session._tracker._entities["entity_123"] = mock_entity
                session._tracker._snapshots["entity_123"] = {}

                mock_save_result = SaveResult(succeeded=[mock_entity])

                with patch.object(
                    session._pipeline,
                    "execute_with_actions",
                    new_callable=AsyncMock,
                    return_value=(mock_save_result, []),
                ):
                    result = await session.commit_async()

                    # No automation results since disabled
                    assert len(result.automation_results) == 0


class TestAutomationResultInSaveResult:
    """Tests for AutomationResult in SaveResult (FR-007)."""

    def test_save_result_has_automation_results_field(self) -> None:
        """FR-007: SaveResult includes automation_results list."""
        result = SaveResult()

        assert hasattr(result, "automation_results")
        assert isinstance(result.automation_results, list)
        assert len(result.automation_results) == 0

    def test_save_result_automation_succeeded_property(self) -> None:
        """FR-007: SaveResult.automation_succeeded counts successful rules."""
        result = SaveResult(
            automation_results=[
                AutomationResult(
                    rule_id="rule_1",
                    rule_name="Rule 1",
                    triggered_by_gid="123",
                    triggered_by_type="Task",
                    success=True,
                ),
                AutomationResult(
                    rule_id="rule_2",
                    rule_name="Rule 2",
                    triggered_by_gid="456",
                    triggered_by_type="Task",
                    success=True,
                ),
                AutomationResult(
                    rule_id="rule_3",
                    rule_name="Rule 3",
                    triggered_by_gid="789",
                    triggered_by_type="Task",
                    success=False,
                    error="Failed",
                ),
            ]
        )

        assert result.automation_succeeded == 2

    def test_save_result_automation_failed_property(self) -> None:
        """FR-007: SaveResult.automation_failed counts failed rules."""
        result = SaveResult(
            automation_results=[
                AutomationResult(
                    rule_id="rule_1",
                    rule_name="Rule 1",
                    triggered_by_gid="123",
                    triggered_by_type="Task",
                    success=True,
                ),
                AutomationResult(
                    rule_id="rule_2",
                    rule_name="Rule 2",
                    triggered_by_gid="456",
                    triggered_by_type="Task",
                    success=False,
                    error="API Error",
                ),
            ]
        )

        assert result.automation_failed == 1

    def test_save_result_automation_skipped_property(self) -> None:
        """FR-007: SaveResult.automation_skipped counts skipped rules."""
        result = SaveResult(
            automation_results=[
                AutomationResult(
                    rule_id="rule_1",
                    rule_name="Rule 1",
                    triggered_by_gid="123",
                    triggered_by_type="Task",
                    success=True,
                ),
                AutomationResult(
                    rule_id="rule_2",
                    rule_name="Rule 2",
                    triggered_by_gid="456",
                    triggered_by_type="Task",
                    success=True,
                    skipped_reason="circular_reference_prevented",
                ),
            ]
        )

        assert result.automation_skipped == 1
        assert result.automation_succeeded == 1  # Skipped counts as success but separate


class TestAutomationFailureIsolation:
    """Tests for automation failure isolation (NFR-003)."""

    async def test_automation_failure_does_not_fail_commit(self) -> None:
        """NFR-003: Automation failures do not propagate to commit."""
        mock_http = MagicMock()
        mock_batch = MagicMock()
        mock_batch.execute_async = AsyncMock(return_value=[])

        with patch("autom8_asana.client.AsanaHttpClient", return_value=mock_http):
            from autom8_asana.client import AsanaClient
            from autom8_asana.persistence import SaveSession

            config = AsanaConfig(automation=AutomationConfig(enabled=True))

            with patch.object(AsanaClient, "_auto_detect_workspace", return_value=None):
                client = AsanaClient(token="test_token", config=config)
                client._batch = mock_batch

                mock_entity = MagicMock()
                mock_entity.gid = "entity_123"

                mock_save_result = SaveResult(succeeded=[mock_entity])

                session = SaveSession(
                    client=client,
                    automation_enabled=True,
                )

                # Track entity
                session._tracker._entities["entity_123"] = mock_entity
                session._tracker._snapshots["entity_123"] = {}

                with patch.object(
                    session._pipeline,
                    "execute_with_actions",
                    new_callable=AsyncMock,
                    return_value=(mock_save_result, []),
                ):
                    # Make automation evaluation raise an exception
                    with patch.object(
                        client.automation,
                        "evaluate_async",
                        new_callable=AsyncMock,
                        side_effect=RuntimeError("Automation crashed!"),
                    ):
                        # Should NOT raise - automation failure is isolated
                        result = await session.commit_async()

                        # CRUD succeeded
                        assert len(result.succeeded) == 1
                        # Automation results empty due to failure
                        assert len(result.automation_results) == 0


class TestFullFlowIntegration:
    """Full integration test demonstrating complete flow."""

    async def test_full_flow_savesession_to_automation_result(self) -> None:
        """Integration test: SaveSession -> AutomationEngine -> AutomationResult.

        This test demonstrates the complete flow:
        1. Create AsanaClient with automation enabled
        2. Register PipelineConversionRule
        3. Create mock Process with section change to CONVERTED
        4. Call SaveSession.commit_async (mocked CRUD operations)
        5. Verify AutomationResult in SaveResult.automation_results
        """
        # Create mock clients for sections and tasks
        mock_http = MagicMock()
        mock_batch = MagicMock()
        mock_batch.execute_async = AsyncMock(return_value=[])

        # Mock template discovery and task creation
        template_section = MockSection("template_section", "Template")
        template_task = MockTask("template_task", "Onboarding Template", "Notes")
        new_task = MockTask("new_onboarding_123", "Hot Lead")

        mock_sections_client = MagicMock()
        mock_sections_client.list_for_project_async.return_value = MockPageIterator(
            [template_section]
        )

        mock_tasks_client = MagicMock()
        mock_tasks_client.list_async.return_value = MockPageIterator([template_task])
        # Mock subtasks_async for template subtask count (no subtasks in this test)
        mock_tasks_client.subtasks_async.return_value = MockPageIterator([])
        # Mock duplicate_async (replaces create_async)
        mock_tasks_client.duplicate_async = AsyncMock(return_value=new_task)
        # Mock add_to_project_async
        mock_tasks_client.add_to_project_async = AsyncMock(return_value=new_task)
        # Mock tasks used by pipeline post-creation steps
        mock_tasks_client.update_async = AsyncMock(return_value=None)
        mock_tasks_client.get_async = AsyncMock(return_value=MagicMock(custom_fields=[]))
        mock_tasks_client.set_assignee_async = AsyncMock(return_value=None)

        # Mock stories client for onboarding comment
        mock_stories_client = MagicMock()
        mock_stories_client.create_comment_async = AsyncMock(return_value=None)

        # Mock sections.add_task_async for section placement
        mock_sections_client.add_task_async = AsyncMock(return_value=None)

        with patch("autom8_asana.client.AsanaHttpClient", return_value=mock_http):
            from autom8_asana.client import AsanaClient
            from autom8_asana.persistence import SaveSession

            # Step 1: Create client with automation enabled
            automation_config = AutomationConfig(
                enabled=True,
                max_cascade_depth=5,
                pipeline_stages={
                    "sales": PipelineStage(project_gid="sales_project_123"),
                    "onboarding": PipelineStage(project_gid="onboarding_project_456"),
                },
            )
            config = AsanaConfig(automation=automation_config)

            with patch.object(AsanaClient, "_auto_detect_workspace", return_value=None):
                client = AsanaClient(token="test_token", config=config)
                client._batch = mock_batch
                # Inject mocked clients
                client._sections = mock_sections_client
                client._tasks = mock_tasks_client
                client._stories = mock_stories_client

                # Step 2: Register PipelineConversionRule
                rule = PipelineConversionRule()
                client.automation.register(rule)

                # Step 3: Create mock Process that moved to CONVERTED section
                # Use "Process" class so TriggerCondition matches entity_type="Process"
                process = Process(
                    gid="process_123",
                    name="Hot Lead",
                    process_type=MockProcessType.SALES,
                )

                # Create session
                session = SaveSession(
                    client=client,
                    automation_enabled=True,
                )

                # Track entity
                session._tracker._entities["process_123"] = process
                session._tracker._snapshots["process_123"] = {}

                # Step 4: Mock the CRUD pipeline to succeed
                # The CRUD phase returns the process as succeeded
                mock_save_result = SaveResult(succeeded=[process])

                # Mock action results that indicate section change to CONVERTED
                # Per ADR-0107: target is NameGid with gid and name
                section_action = ActionOperation(
                    task=process,
                    action=ActionType.MOVE_TO_SECTION,
                    target=NameGid(gid="converted_section_gid", name="Converted"),
                )
                mock_action_result = ActionResult(
                    action=section_action,
                    success=True,
                )
                mock_save_result.action_results = [mock_action_result]

                with patch.object(
                    session._pipeline,
                    "execute_with_actions",
                    new_callable=AsyncMock,
                    return_value=(mock_save_result, [mock_action_result]),
                ):
                    # Step 5: Commit and verify results
                    result = await session.commit_async()

                    # Verify CRUD succeeded
                    assert len(result.succeeded) == 1

                    # Verify automation was triggered and executed
                    assert len(result.automation_results) == 1

                    auto_result = result.automation_results[0]
                    assert auto_result.rule_id == "pipeline_sales_to_onboarding"
                    assert auto_result.rule_name == "Pipeline: Sales to Onboarding"
                    assert auto_result.triggered_by_gid == "process_123"
                    assert auto_result.triggered_by_type == "Process"
                    assert auto_result.success is True
                    assert "new_onboarding_123" in auto_result.entities_created
                    assert auto_result.execution_time_ms > 0

                    # Verify convenience properties
                    assert result.automation_succeeded == 1
                    assert result.automation_failed == 0
                    assert result.automation_skipped == 0


class TestPostCommitHook:
    """Tests for post-commit hook with automation results (FR-002)."""

    async def test_post_commit_hook_receives_automation_results(self) -> None:
        """FR-002: Post-commit hooks receive SaveResult with automation_results."""
        mock_http = MagicMock()
        mock_batch = MagicMock()
        mock_batch.execute_async = AsyncMock(return_value=[])

        with patch("autom8_asana.client.AsanaHttpClient", return_value=mock_http):
            from autom8_asana.client import AsanaClient
            from autom8_asana.persistence import SaveSession

            config = AsanaConfig(automation=AutomationConfig(enabled=True))

            with patch.object(AsanaClient, "_auto_detect_workspace", return_value=None):
                client = AsanaClient(token="test_token", config=config)
                client._batch = mock_batch

                # Mock automation to return a result
                mock_auto_result = AutomationResult(
                    rule_id="test_rule",
                    rule_name="Test Rule",
                    triggered_by_gid="entity_123",
                    triggered_by_type="MockEntity",
                    success=True,
                )

                session = SaveSession(
                    client=client,
                    automation_enabled=True,
                )

                # Track what post_commit receives
                received_result: SaveResult | None = None

                @session.on_post_commit
                def capture_result(result: SaveResult) -> None:
                    nonlocal received_result
                    received_result = result

                mock_entity = MagicMock()
                mock_entity.gid = "entity_123"

                # Track entity
                session._tracker._entities["entity_123"] = mock_entity
                session._tracker._snapshots["entity_123"] = {}

                mock_save_result = SaveResult(succeeded=[mock_entity])

                with patch.object(
                    session._pipeline,
                    "execute_with_actions",
                    new_callable=AsyncMock,
                    return_value=(mock_save_result, []),
                ):
                    with patch.object(
                        client.automation,
                        "evaluate_async",
                        new_callable=AsyncMock,
                        return_value=[mock_auto_result],
                    ):
                        await session.commit_async()

                        # Verify hook received results with automation
                        assert received_result is not None
                        assert len(received_result.automation_results) == 1
                        assert received_result.automation_results[0].rule_id == "test_rule"
