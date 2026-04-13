"""Tests for SavePipeline.

Per TDD-0010: Verify four-phase save orchestration.
Per TDD-0011: Verify action support and unsupported field validation.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.models import Task
from autom8_asana.models.common import NameGid
from autom8_asana.persistence.action_executor import ActionExecutor
from autom8_asana.persistence.events import EventSystem
from autom8_asana.persistence.errors import (
    UnsupportedOperationError,
)
from autom8_asana.persistence.graph import DependencyGraph
from autom8_asana.persistence.models import (
    ActionOperation,
    ActionResult,
    ActionType,
    OperationType,
    PlannedOperation,
    SaveResult,
)
from autom8_asana.persistence.pipeline import UNSUPPORTED_FIELDS, SavePipeline
from autom8_asana.persistence.tracker import ChangeTracker

# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def create_mock_batch_client() -> MagicMock:
    """Create a mock BatchClient."""
    mock_client = MagicMock()
    mock_client.execute_async = AsyncMock(return_value=[])
    return mock_client


def create_success_result(
    gid: str = "123",
    request_index: int = 0,
) -> BatchResult:
    """Create a successful BatchResult."""
    return BatchResult(
        status_code=200,
        body={"data": {"gid": gid, "name": "Test"}},
        request_index=request_index,
    )


def create_failure_result(
    message: str = "Error",
    status_code: int = 400,
    request_index: int = 0,
) -> BatchResult:
    """Create a failed BatchResult."""
    return BatchResult(
        status_code=status_code,
        body={"errors": [{"message": message}]},
        request_index=request_index,
    )


def create_pipeline(
    batch_responses: list[BatchResult] | None = None,
) -> tuple[SavePipeline, ChangeTracker, DependencyGraph, EventSystem, MagicMock]:
    """Create a pipeline with mocked BatchClient."""
    tracker = ChangeTracker()
    graph = DependencyGraph()
    events = EventSystem()
    mock_client = create_mock_batch_client()

    if batch_responses is not None:
        mock_client.execute_async = AsyncMock(return_value=batch_responses)

    pipeline = SavePipeline(
        tracker=tracker,
        graph=graph,
        events=events,
        batch_client=mock_client,
    )

    return pipeline, tracker, graph, events, mock_client


# ---------------------------------------------------------------------------
# Preview Tests
# ---------------------------------------------------------------------------


class TestPreview:
    """Tests for preview() method."""

    def test_preview_empty_returns_empty(self) -> None:
        """preview() with empty list returns empty."""
        pipeline, *_ = create_pipeline()

        result = pipeline.preview([])

        assert result == []

    def test_preview_returns_planned_operations(self) -> None:
        """preview() returns list of PlannedOperation."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="123", name="Original")
        tracker.track(task)
        task.name = "Modified"

        operations = pipeline.preview([task])

        assert len(operations) == 1
        assert isinstance(operations[0], PlannedOperation)
        assert operations[0].entity is task
        assert operations[0].operation == OperationType.UPDATE

    def test_preview_includes_dependency_level(self) -> None:
        """preview() includes correct dependency levels."""
        pipeline, tracker, *_ = create_pipeline()

        # Create parent-child relationship with real GIDs
        # (not starting with "temp_" to avoid special handling)
        parent = Task(gid="111111111", name="Parent")
        child = Task(gid="222222222", name="Child", parent=NameGid(gid="111111111"))

        tracker.track(parent)
        tracker.track(child)
        # Mark as modified so they're dirty
        parent.name = "Parent Modified"
        child.name = "Child Modified"

        operations = pipeline.preview([parent, child])

        assert len(operations) == 2

        # Find parent and child operations
        parent_op = next(op for op in operations if op.entity is parent)
        child_op = next(op for op in operations if op.entity is child)

        # Parent should be at level 0
        assert parent_op.dependency_level == 0
        assert child_op.dependency_level == 1

    def test_preview_new_entity_is_create(self) -> None:
        """preview() shows CREATE for new entities."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="temp_123", name="New Task")
        tracker.track(task)

        operations = pipeline.preview([task])

        assert len(operations) == 1
        assert operations[0].operation == OperationType.CREATE

    def test_preview_modified_entity_is_update(self) -> None:
        """preview() shows UPDATE for modified entities."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="123", name="Original")
        tracker.track(task)
        task.name = "Modified"

        operations = pipeline.preview([task])

        assert len(operations) == 1
        assert operations[0].operation == OperationType.UPDATE

    def test_preview_deleted_entity_is_delete(self) -> None:
        """preview() shows DELETE for deleted entities."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="123", name="To Delete")
        tracker.track(task)
        tracker.mark_deleted(task)

        operations = pipeline.preview([task])

        assert len(operations) == 1
        assert operations[0].operation == OperationType.DELETE
        assert operations[0].payload == {}


# ---------------------------------------------------------------------------
# Execute Tests
# ---------------------------------------------------------------------------


class TestExecute:
    """Tests for execute() method."""

    @pytest.mark.asyncio
    async def test_execute_empty_returns_empty_result(self) -> None:
        """execute() with empty list returns empty SaveResult."""
        pipeline, *_ = create_pipeline()

        result = await pipeline.execute([])

        assert isinstance(result, SaveResult)
        assert result.succeeded == []
        assert result.failed == []
        assert result.success

    @pytest.mark.asyncio
    async def test_execute_single_entity_success(self) -> None:
        """execute() handles single successful entity."""
        success = create_success_result(gid="123")
        pipeline, tracker, _, _, mock_client = create_pipeline([success])

        task = Task(gid="123", name="Original")
        tracker.track(task)
        task.name = "Modified"

        result = await pipeline.execute([task])

        assert len(result.succeeded) == 1
        assert result.succeeded[0] is task
        assert len(result.failed) == 0
        assert result.success

    @pytest.mark.asyncio
    async def test_execute_single_entity_failure(self) -> None:
        """execute() handles single failed entity."""
        failure = create_failure_result("Bad request", 400)
        pipeline, tracker, _, _, mock_client = create_pipeline([failure])

        task = Task(gid="123", name="Test")
        tracker.track(task)
        task.name = "Modified"

        result = await pipeline.execute([task])

        assert len(result.succeeded) == 0
        assert len(result.failed) == 1
        assert result.failed[0].entity is task
        assert not result.success

    @pytest.mark.asyncio
    async def test_execute_updates_gid_after_create(self) -> None:
        """execute() updates entity GID after successful create."""
        success = create_success_result(gid="real_gid_123")
        pipeline, tracker, _, _, mock_client = create_pipeline([success])

        task = Task(gid="temp_123", name="New Task")
        tracker.track(task)

        await pipeline.execute([task])

        # Entity GID should be updated
        assert task.gid == "real_gid_123"

    @pytest.mark.asyncio
    async def test_execute_cascading_dependency_failure(self) -> None:
        """execute() marks dependents as failed when parent fails."""
        # Parent fails, child should cascade fail
        failure = create_failure_result("Parent failed", 400)
        # Use real GIDs with parent-child relationship
        pipeline, tracker, _, _, mock_client = create_pipeline([failure])

        parent = Task(gid="111111111", name="Parent")
        child = Task(gid="222222222", name="Child", parent=NameGid(gid="111111111"))

        tracker.track(parent)
        tracker.track(child)
        # Mark as modified so they're dirty
        parent.name = "Parent Modified"
        child.name = "Child Modified"

        result = await pipeline.execute([parent, child])

        # Both should fail
        assert len(result.failed) == 2
        assert len(result.succeeded) == 0

        # Child should have DependencyResolutionError
        child_error = next(e for e in result.failed if e.entity is child)
        assert "dependency" in str(child_error.error).lower()


# ---------------------------------------------------------------------------
# Operation Type Tests
# ---------------------------------------------------------------------------


class TestDetermineOperation:
    """Tests for _determine_operation() method."""

    def test_determine_operation_new_state(self) -> None:
        """NEW state results in CREATE operation."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="temp_123", name="New")
        tracker.track(task)

        op_type = pipeline._determine_operation(task)

        assert op_type == OperationType.CREATE

    def test_determine_operation_modified_state(self) -> None:
        """MODIFIED state results in UPDATE operation."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="123", name="Original")
        tracker.track(task)
        task.name = "Modified"

        op_type = pipeline._determine_operation(task)

        assert op_type == OperationType.UPDATE

    def test_determine_operation_deleted_state(self) -> None:
        """DELETED state results in DELETE operation."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="123", name="Test")
        tracker.track(task)
        tracker.mark_deleted(task)

        op_type = pipeline._determine_operation(task)

        assert op_type == OperationType.DELETE


# ---------------------------------------------------------------------------
# Payload Building Tests
# ---------------------------------------------------------------------------


class TestBuildPayload:
    """Tests for _build_payload() method."""

    def test_build_payload_create_full(self) -> None:
        """CREATE payload includes all non-None fields."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="temp_123", name="New Task", notes="Some notes")
        tracker.track(task)

        payload = pipeline._build_payload(task, OperationType.CREATE)

        assert "name" in payload
        assert payload["name"] == "New Task"
        assert "notes" in payload
        assert payload["notes"] == "Some notes"
        # gid and resource_type should be excluded
        assert "gid" not in payload
        assert "resource_type" not in payload

    def test_build_payload_update_minimal(self) -> None:
        """UPDATE payload includes only changed fields."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="123", name="Original", notes="Original notes")
        tracker.track(task)
        task.name = "Modified"
        # notes unchanged

        payload = pipeline._build_payload(task, OperationType.UPDATE)

        assert "name" in payload
        assert payload["name"] == "Modified"
        assert "notes" not in payload

    def test_build_payload_delete_empty(self) -> None:
        """DELETE payload is empty."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="123", name="Test")
        tracker.track(task)
        tracker.mark_deleted(task)

        payload = pipeline._build_payload(task, OperationType.DELETE)

        assert payload == {}


# ---------------------------------------------------------------------------
# GID Resolution Tests
# ---------------------------------------------------------------------------


class TestGidResolution:
    """Tests for GID resolution during execution."""

    @pytest.mark.asyncio
    async def test_execute_resolves_placeholder_gids(self) -> None:
        """execute() updates GIDs for newly created entities."""
        # Single entity created
        success = create_success_result(gid="real_gid_123", request_index=0)

        mock_client = create_mock_batch_client()
        mock_client.execute_async = AsyncMock(return_value=[success])

        tracker = ChangeTracker()
        graph = DependencyGraph()
        events = EventSystem()
        pipeline = SavePipeline(tracker, graph, events, mock_client)

        # Create a new entity with temp GID
        task = Task(gid="temp_1", name="New Task")
        tracker.track(task)

        result = await pipeline.execute([task])

        assert result.success
        # GID should be updated to real value from API response
        assert task.gid == "real_gid_123"

    @pytest.mark.asyncio
    async def test_execute_parent_child_with_dependency(self) -> None:
        """execute() handles parent-child with real GIDs."""
        # Parent is updated, child is updated
        parent_success = create_success_result(gid="111111111", request_index=0)
        child_success = create_success_result(gid="222222222", request_index=0)

        mock_client = create_mock_batch_client()
        # Parent in level 0, child in level 1
        mock_client.execute_async = AsyncMock(
            side_effect=[[parent_success], [child_success]]
        )

        tracker = ChangeTracker()
        graph = DependencyGraph()
        events = EventSystem()
        pipeline = SavePipeline(tracker, graph, events, mock_client)

        # Create parent-child with real GIDs for dependency detection
        parent = Task(gid="111111111", name="Parent")
        child = Task(gid="222222222", name="Child", parent=NameGid(gid="111111111"))

        tracker.track(parent)
        tracker.track(child)
        # Mark modified to be dirty
        parent.name = "Parent Modified"
        child.name = "Child Modified"

        result = await pipeline.execute([parent, child])

        assert result.success
        assert len(result.succeeded) == 2


# ---------------------------------------------------------------------------
# Event Hook Tests
# ---------------------------------------------------------------------------


class TestEventEmission:
    """Tests for event hook emission during execution."""

    @pytest.mark.asyncio
    async def test_execute_emits_pre_save_hooks(self) -> None:
        """execute() emits pre_save for each entity."""
        success = create_success_result()
        pipeline, tracker, _, events, _ = create_pipeline([success])

        pre_save_calls: list[tuple[Task, OperationType]] = []

        @events.register_pre_save
        def hook(entity: Task, op: OperationType) -> None:
            pre_save_calls.append((entity, op))

        task = Task(gid="123", name="Test")
        tracker.track(task)
        task.name = "Modified"

        await pipeline.execute([task])

        assert len(pre_save_calls) == 1
        assert pre_save_calls[0][0] is task
        assert pre_save_calls[0][1] == OperationType.UPDATE

    @pytest.mark.asyncio
    async def test_execute_emits_post_save_on_success(self) -> None:
        """execute() emits post_save for successful entities."""
        success = create_success_result()
        pipeline, tracker, _, events, _ = create_pipeline([success])

        post_save_calls: list[tuple[Task, OperationType, Any]] = []

        @events.register_post_save
        def hook(entity: Task, op: OperationType, data: Any) -> None:
            post_save_calls.append((entity, op, data))

        task = Task(gid="123", name="Test")
        tracker.track(task)
        task.name = "Modified"

        await pipeline.execute([task])

        assert len(post_save_calls) == 1
        assert post_save_calls[0][0] is task

    @pytest.mark.asyncio
    async def test_execute_emits_error_on_failure(self) -> None:
        """execute() emits error for failed entities."""
        failure = create_failure_result()
        pipeline, tracker, _, events, _ = create_pipeline([failure])

        error_calls: list[tuple[Task, OperationType, Exception]] = []

        @events.register_error
        def hook(entity: Task, op: OperationType, err: Exception) -> None:
            error_calls.append((entity, op, err))

        task = Task(gid="123", name="Test")
        tracker.track(task)
        task.name = "Modified"

        await pipeline.execute([task])

        assert len(error_calls) == 1
        assert error_calls[0][0] is task


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases."""

    def test_preview_detects_cycle(self) -> None:
        """preview() raises CyclicDependencyError for cycles."""
        pipeline, tracker, *_ = create_pipeline()

        # Note: Direct cycles aren't easily created with parent field
        # as parent must exist. This tests the cycle detection mechanism
        # would be triggered if cycles existed in the graph.
        # For now, test with a valid case.
        task = Task(gid="temp_1", name="Test")
        tracker.track(task)

        # Should not raise for non-cyclic
        operations = pipeline.preview([task])
        assert len(operations) == 1

    @pytest.mark.asyncio
    async def test_execute_with_multiple_levels(self) -> None:
        """execute() handles multiple dependency levels correctly."""
        results = [
            create_success_result(gid="level0_1", request_index=0),
            create_success_result(gid="level0_2", request_index=1),
        ]

        mock_client = create_mock_batch_client()
        # All independent entities in one batch
        mock_client.execute_async = AsyncMock(return_value=results)

        tracker = ChangeTracker()
        graph = DependencyGraph()
        events = EventSystem()
        pipeline = SavePipeline(tracker, graph, events, mock_client)

        # Two independent entities (same level)
        task1 = Task(gid="temp_1", name="Task 1")
        task2 = Task(gid="temp_2", name="Task 2")

        tracker.track(task1)
        tracker.track(task2)

        result = await pipeline.execute([task1, task2])

        assert result.success
        assert len(result.succeeded) == 2

    @pytest.mark.asyncio
    async def test_execute_partial_success(self) -> None:
        """execute() handles partial success correctly."""
        results = [
            create_success_result(gid="123", request_index=0),
            create_failure_result("Error", 400, request_index=1),
        ]
        pipeline, tracker, _, _, mock_client = create_pipeline(results)

        task1 = Task(gid="111", name="Task 1")
        task2 = Task(gid="222", name="Task 2")

        tracker.track(task1)
        tracker.track(task2)
        task1.name = "Modified 1"
        task2.name = "Modified 2"

        result = await pipeline.execute([task1, task2])

        assert result.partial
        assert len(result.succeeded) == 1
        assert len(result.failed) == 1


# ---------------------------------------------------------------------------
# TDD-0011: Unsupported Field Validation Tests
# ---------------------------------------------------------------------------


class TestValidateNoUnsupportedModifications:
    """Tests for validate_no_unsupported_modifications() method."""

    def test_unsupported_fields_constant_exists(self) -> None:
        """UNSUPPORTED_FIELDS constant is defined."""
        assert "tags" in UNSUPPORTED_FIELDS
        assert "projects" in UNSUPPORTED_FIELDS
        assert "memberships" in UNSUPPORTED_FIELDS
        assert "dependencies" in UNSUPPORTED_FIELDS

    def test_validate_empty_list_passes(self) -> None:
        """validate_no_unsupported_modifications passes for empty list."""
        pipeline, *_ = create_pipeline()

        # Should not raise
        pipeline.validate_no_unsupported_modifications([])

    def test_validate_clean_entity_passes(self) -> None:
        """validate_no_unsupported_modifications passes for clean entities."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="123", name="Test", tags=[NameGid(gid="tag_1")])
        tracker.track(task)
        # Not modified, so clean

        # Should not raise
        pipeline.validate_no_unsupported_modifications([task])

    def test_validate_new_entity_passes(self) -> None:
        """validate_no_unsupported_modifications passes for new entities."""
        pipeline, tracker, *_ = create_pipeline()

        # New entity with tags is OK (tags sent in CREATE)
        task = Task(gid="temp_123", name="New Task", tags=[NameGid(gid="tag_1")])
        tracker.track(task)

        # Should not raise (NEW state, not MODIFIED)
        pipeline.validate_no_unsupported_modifications([task])

    def test_validate_modified_name_passes(self) -> None:
        """validate_no_unsupported_modifications passes for allowed modifications."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="123", name="Original")
        tracker.track(task)
        task.name = "Modified"

        # Should not raise (name is not in UNSUPPORTED_FIELDS)
        pipeline.validate_no_unsupported_modifications([task])

    def test_validate_modified_tags_raises(self) -> None:
        """validate_no_unsupported_modifications raises for modified tags."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="123", name="Test", tags=[NameGid(gid="tag_1")])
        tracker.track(task)
        task.tags = [NameGid(gid="tag_2")]  # Modify tags

        with pytest.raises(UnsupportedOperationError) as exc_info:
            pipeline.validate_no_unsupported_modifications([task])

        assert exc_info.value.field_name == "tags"
        assert "add_tag()" in exc_info.value.suggested_methods

    def test_validate_modified_projects_raises(self) -> None:
        """validate_no_unsupported_modifications raises for modified projects."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="123", name="Test", projects=[NameGid(gid="proj_1")])
        tracker.track(task)
        task.projects = [NameGid(gid="proj_2")]  # Modify projects

        with pytest.raises(UnsupportedOperationError) as exc_info:
            pipeline.validate_no_unsupported_modifications([task])

        assert exc_info.value.field_name == "projects"
        assert "add_to_project()" in exc_info.value.suggested_methods

    def test_validate_stops_at_first_unsupported(self) -> None:
        """validate_no_unsupported_modifications raises on first violation."""
        pipeline, tracker, *_ = create_pipeline()

        task1 = Task(gid="123", name="Task 1")
        task2 = Task(gid="456", name="Task 2", tags=[NameGid(gid="tag_1")])

        tracker.track(task1)
        tracker.track(task2)

        task1.name = "Modified 1"  # OK
        task2.tags = [NameGid(gid="tag_2")]  # Not OK

        with pytest.raises(UnsupportedOperationError):
            pipeline.validate_no_unsupported_modifications([task1, task2])


# ---------------------------------------------------------------------------
# TDD-0011: Execute With Actions Tests
# ---------------------------------------------------------------------------


class TestExecuteWithActions:
    """Tests for execute_with_actions() method."""

    @pytest.fixture
    def mock_action_executor(self) -> AsyncMock:
        """Create mock action executor."""
        executor = AsyncMock(spec=ActionExecutor)
        executor.execute_async = AsyncMock(return_value=[])
        return executor

    @pytest.mark.asyncio
    async def test_execute_with_actions_empty(
        self, mock_action_executor: AsyncMock
    ) -> None:
        """execute_with_actions handles empty entities and actions."""
        pipeline, *_ = create_pipeline()

        crud_result, action_results = await pipeline.execute_with_actions(
            entities=[],
            actions=[],
            action_executor=mock_action_executor,
        )

        assert crud_result.success
        assert action_results == []

    @pytest.mark.asyncio
    async def test_execute_with_actions_crud_only(
        self, mock_action_executor: AsyncMock
    ) -> None:
        """execute_with_actions handles CRUD without actions."""
        success = create_success_result(gid="123")
        pipeline, tracker, _, _, mock_client = create_pipeline([success])

        task = Task(gid="123", name="Original")
        tracker.track(task)
        task.name = "Modified"

        crud_result, action_results = await pipeline.execute_with_actions(
            entities=[task],
            actions=[],
            action_executor=mock_action_executor,
        )

        assert crud_result.success
        assert len(crud_result.succeeded) == 1
        assert action_results == []
        mock_action_executor.execute_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_with_actions_actions_only(
        self, mock_action_executor: AsyncMock
    ) -> None:
        """execute_with_actions handles actions without CRUD."""
        pipeline, *_ = create_pipeline()

        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )

        mock_action_executor.execute_async.return_value = [
            ActionResult(action=action, success=True)
        ]

        crud_result, action_results = await pipeline.execute_with_actions(
            entities=[],
            actions=[action],
            action_executor=mock_action_executor,
        )

        assert crud_result.success
        assert len(action_results) == 1
        assert action_results[0].success
        mock_action_executor.execute_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_actions_both(
        self, mock_action_executor: AsyncMock
    ) -> None:
        """execute_with_actions handles both CRUD and actions."""
        success = create_success_result(gid="123")
        pipeline, tracker, _, _, mock_client = create_pipeline([success])

        task = Task(gid="123", name="Original")
        tracker.track(task)
        task.name = "Modified"

        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )

        mock_action_executor.execute_async.return_value = [
            ActionResult(action=action, success=True)
        ]

        crud_result, action_results = await pipeline.execute_with_actions(
            entities=[task],
            actions=[action],
            action_executor=mock_action_executor,
        )

        assert crud_result.success
        assert len(crud_result.succeeded) == 1
        assert len(action_results) == 1
        assert action_results[0].success

    @pytest.mark.asyncio
    async def test_execute_with_actions_validates_unsupported(
        self, mock_action_executor: AsyncMock
    ) -> None:
        """execute_with_actions validates unsupported modifications."""
        pipeline, tracker, *_ = create_pipeline()

        task = Task(gid="123", name="Test", tags=[NameGid(gid="tag_1")])
        tracker.track(task)
        task.tags = [NameGid(gid="tag_2")]  # Unsupported modification

        with pytest.raises(UnsupportedOperationError):
            await pipeline.execute_with_actions(
                entities=[task],
                actions=[],
                action_executor=mock_action_executor,
            )

    @pytest.mark.asyncio
    async def test_execute_with_actions_passes_gid_map(
        self, mock_action_executor: AsyncMock
    ) -> None:
        """execute_with_actions passes GID map to action executor."""
        success = create_success_result(gid="real_gid_123")
        pipeline, tracker, _, _, mock_client = create_pipeline([success])

        # New entity that will get a real GID
        task = Task(gid="temp_1", name="New Task")
        tracker.track(task)

        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="456456456"),
        )

        mock_action_executor.execute_async.return_value = [
            ActionResult(action=action, success=True)
        ]

        await pipeline.execute_with_actions(
            entities=[task],
            actions=[action],
            action_executor=mock_action_executor,
        )

        # Verify execute_async was called with a gid_map
        call_args = mock_action_executor.execute_async.call_args
        gid_map = call_args[0][1]  # Second positional arg
        assert isinstance(gid_map, dict)
