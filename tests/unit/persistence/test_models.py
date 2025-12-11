"""Tests for persistence data models.

Per TDD-0010: Verify EntityState, OperationType, PlannedOperation,
SaveError, and SaveResult classes.

Per TDD-0011: Verify ActionType, ActionOperation, and ActionResult classes.
"""

from __future__ import annotations

import pytest

from autom8_asana.models import Task
from autom8_asana.persistence.models import (
    EntityState,
    OperationType,
    PlannedOperation,
    SaveError,
    SaveResult,
    # TDD-0011: Action types
    ActionType,
    ActionOperation,
    ActionResult,
)


# ---------------------------------------------------------------------------
# EntityState Tests
# ---------------------------------------------------------------------------


class TestEntityState:
    """Tests for EntityState enum."""

    def test_new_state_value(self) -> None:
        """NEW state has value 'new'."""
        assert EntityState.NEW.value == "new"

    def test_clean_state_value(self) -> None:
        """CLEAN state has value 'clean'."""
        assert EntityState.CLEAN.value == "clean"

    def test_modified_state_value(self) -> None:
        """MODIFIED state has value 'modified'."""
        assert EntityState.MODIFIED.value == "modified"

    def test_deleted_state_value(self) -> None:
        """DELETED state has value 'deleted'."""
        assert EntityState.DELETED.value == "deleted"

    def test_all_states_exist(self) -> None:
        """All expected states exist."""
        states = [s.value for s in EntityState]
        assert set(states) == {"new", "clean", "modified", "deleted"}


# ---------------------------------------------------------------------------
# OperationType Tests
# ---------------------------------------------------------------------------


class TestOperationType:
    """Tests for OperationType enum."""

    def test_create_operation_value(self) -> None:
        """CREATE operation has value 'create'."""
        assert OperationType.CREATE.value == "create"

    def test_update_operation_value(self) -> None:
        """UPDATE operation has value 'update'."""
        assert OperationType.UPDATE.value == "update"

    def test_delete_operation_value(self) -> None:
        """DELETE operation has value 'delete'."""
        assert OperationType.DELETE.value == "delete"

    def test_all_operations_exist(self) -> None:
        """All expected operations exist."""
        ops = [o.value for o in OperationType]
        assert set(ops) == {"create", "update", "delete"}


# ---------------------------------------------------------------------------
# PlannedOperation Tests
# ---------------------------------------------------------------------------


class TestPlannedOperation:
    """Tests for PlannedOperation dataclass."""

    def test_create_planned_operation(self) -> None:
        """PlannedOperation can be created with required fields."""
        task = Task(gid="123", name="Test Task")
        payload = {"name": "Test Task"}

        op = PlannedOperation(
            entity=task,
            operation=OperationType.CREATE,
            payload=payload,
            dependency_level=0,
        )

        assert op.entity is task
        assert op.operation == OperationType.CREATE
        assert op.payload == payload
        assert op.dependency_level == 0

    def test_planned_operation_is_frozen(self) -> None:
        """PlannedOperation is immutable (frozen=True)."""
        task = Task(gid="123", name="Test Task")
        op = PlannedOperation(
            entity=task,
            operation=OperationType.UPDATE,
            payload={"name": "Updated"},
            dependency_level=1,
        )

        with pytest.raises(AttributeError):
            op.dependency_level = 2  # type: ignore[misc]

    def test_planned_operation_repr(self) -> None:
        """PlannedOperation repr is readable."""
        task = Task(gid="123", name="Test Task")
        op = PlannedOperation(
            entity=task,
            operation=OperationType.CREATE,
            payload={"name": "Test"},
            dependency_level=0,
        )

        repr_str = repr(op)
        assert "PlannedOperation" in repr_str
        assert "create" in repr_str
        assert "Task" in repr_str
        assert "gid=123" in repr_str
        assert "level=0" in repr_str

    def test_planned_operation_with_empty_payload(self) -> None:
        """PlannedOperation accepts empty payload (for DELETE)."""
        task = Task(gid="456")
        op = PlannedOperation(
            entity=task,
            operation=OperationType.DELETE,
            payload={},
            dependency_level=2,
        )

        assert op.payload == {}


# ---------------------------------------------------------------------------
# SaveError Tests
# ---------------------------------------------------------------------------


class TestSaveError:
    """Tests for SaveError dataclass."""

    def test_create_save_error(self) -> None:
        """SaveError can be created with required fields."""
        task = Task(gid="123", name="Failed Task")
        error = ValueError("Something went wrong")
        payload = {"name": "Failed Task"}

        save_error = SaveError(
            entity=task,
            operation=OperationType.CREATE,
            error=error,
            payload=payload,
        )

        assert save_error.entity is task
        assert save_error.operation == OperationType.CREATE
        assert save_error.error is error
        assert save_error.payload == payload

    def test_save_error_repr(self) -> None:
        """SaveError repr is readable."""
        task = Task(gid="789")
        error = RuntimeError("API failed")

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={"name": "Test"},
        )

        repr_str = repr(save_error)
        assert "SaveError" in repr_str
        assert "update" in repr_str
        assert "Task" in repr_str
        assert "gid=789" in repr_str
        assert "RuntimeError" in repr_str

    def test_save_error_with_nested_exception(self) -> None:
        """SaveError handles nested exceptions."""
        task = Task(gid="123")
        cause = IOError("Network failed")
        error = RuntimeError("Request failed")
        error.__cause__ = cause

        save_error = SaveError(
            entity=task,
            operation=OperationType.CREATE,
            error=error,
            payload={},
        )

        assert save_error.error.__cause__ is cause


# ---------------------------------------------------------------------------
# SaveResult Tests
# ---------------------------------------------------------------------------


class TestSaveResult:
    """Tests for SaveResult dataclass."""

    def test_empty_save_result(self) -> None:
        """Empty SaveResult has sensible defaults."""
        result = SaveResult()

        assert result.succeeded == []
        assert result.failed == []
        assert result.success is True
        assert result.partial is False
        assert result.total_count == 0

    def test_successful_save_result(self) -> None:
        """SaveResult with only successes."""
        task1 = Task(gid="123")
        task2 = Task(gid="456")

        result = SaveResult(succeeded=[task1, task2])

        assert len(result.succeeded) == 2
        assert result.failed == []
        assert result.success is True
        assert result.partial is False
        assert result.total_count == 2

    def test_failed_save_result(self) -> None:
        """SaveResult with only failures."""
        task = Task(gid="123")
        error = SaveError(
            entity=task,
            operation=OperationType.CREATE,
            error=ValueError("Failed"),
            payload={},
        )

        result = SaveResult(failed=[error])

        assert result.succeeded == []
        assert len(result.failed) == 1
        assert result.success is False
        assert result.partial is False
        assert result.total_count == 1

    def test_partial_save_result(self) -> None:
        """SaveResult with both successes and failures."""
        task1 = Task(gid="123")
        task2 = Task(gid="456")
        error = SaveError(
            entity=task2,
            operation=OperationType.UPDATE,
            error=ValueError("Failed"),
            payload={},
        )

        result = SaveResult(succeeded=[task1], failed=[error])

        assert len(result.succeeded) == 1
        assert len(result.failed) == 1
        assert result.success is False
        assert result.partial is True
        assert result.total_count == 2

    def test_save_result_repr(self) -> None:
        """SaveResult repr is readable."""
        task1 = Task(gid="123")
        task2 = Task(gid="456")
        error = SaveError(
            entity=task2,
            operation=OperationType.UPDATE,
            error=ValueError("Failed"),
            payload={},
        )

        result = SaveResult(succeeded=[task1], failed=[error])
        repr_str = repr(result)

        assert "SaveResult" in repr_str
        assert "succeeded=1" in repr_str
        assert "failed=1" in repr_str

    def test_raise_on_failure_with_no_failures(self) -> None:
        """raise_on_failure does nothing when no failures."""
        task = Task(gid="123")
        result = SaveResult(succeeded=[task])

        # Should not raise
        result.raise_on_failure()

    def test_raise_on_failure_with_failures(self) -> None:
        """raise_on_failure raises PartialSaveError when failures exist."""
        from autom8_asana.persistence.exceptions import PartialSaveError

        task = Task(gid="123")
        error = SaveError(
            entity=task,
            operation=OperationType.CREATE,
            error=ValueError("Failed"),
            payload={},
        )

        result = SaveResult(failed=[error])

        with pytest.raises(PartialSaveError) as exc_info:
            result.raise_on_failure()

        assert exc_info.value.result is result
        assert "1/1 operations failed" in str(exc_info.value)

    def test_raise_on_failure_with_partial_result(self) -> None:
        """raise_on_failure raises PartialSaveError for partial results."""
        from autom8_asana.persistence.exceptions import PartialSaveError

        task1 = Task(gid="123")
        task2 = Task(gid="456")
        error = SaveError(
            entity=task2,
            operation=OperationType.UPDATE,
            error=ValueError("Failed"),
            payload={},
        )

        result = SaveResult(succeeded=[task1], failed=[error])

        with pytest.raises(PartialSaveError) as exc_info:
            result.raise_on_failure()

        assert exc_info.value.result is result
        assert "1/2 operations failed" in str(exc_info.value)


# ---------------------------------------------------------------------------
# ActionType Tests (TDD-0011)
# ---------------------------------------------------------------------------


class TestActionType:
    """Tests for ActionType enum."""

    def test_add_tag_value(self) -> None:
        """ADD_TAG has value 'add_tag'."""
        assert ActionType.ADD_TAG.value == "add_tag"

    def test_remove_tag_value(self) -> None:
        """REMOVE_TAG has value 'remove_tag'."""
        assert ActionType.REMOVE_TAG.value == "remove_tag"

    def test_add_to_project_value(self) -> None:
        """ADD_TO_PROJECT has value 'add_to_project'."""
        assert ActionType.ADD_TO_PROJECT.value == "add_to_project"

    def test_remove_from_project_value(self) -> None:
        """REMOVE_FROM_PROJECT has value 'remove_from_project'."""
        assert ActionType.REMOVE_FROM_PROJECT.value == "remove_from_project"

    def test_add_dependency_value(self) -> None:
        """ADD_DEPENDENCY has value 'add_dependency'."""
        assert ActionType.ADD_DEPENDENCY.value == "add_dependency"

    def test_remove_dependency_value(self) -> None:
        """REMOVE_DEPENDENCY has value 'remove_dependency'."""
        assert ActionType.REMOVE_DEPENDENCY.value == "remove_dependency"

    def test_move_to_section_value(self) -> None:
        """MOVE_TO_SECTION has value 'move_to_section'."""
        assert ActionType.MOVE_TO_SECTION.value == "move_to_section"

    def test_set_parent_value(self) -> None:
        """SET_PARENT has value 'set_parent'."""
        assert ActionType.SET_PARENT.value == "set_parent"

    def test_all_action_types_exist(self) -> None:
        """All expected action types exist."""
        actions = [a.value for a in ActionType]
        expected = {
            "add_tag",
            "remove_tag",
            "add_to_project",
            "remove_from_project",
            "add_dependency",
            "remove_dependency",
            "move_to_section",
            "add_follower",
            "remove_follower",
            "add_dependent",
            "remove_dependent",
            "add_like",
            "remove_like",
            "add_comment",
            "set_parent",
        }
        assert set(actions) == expected

    def test_action_type_is_str_enum(self) -> None:
        """ActionType is a str enum (can be used as string)."""
        assert isinstance(ActionType.ADD_TAG, str)
        assert ActionType.ADD_TAG == "add_tag"


# ---------------------------------------------------------------------------
# ActionOperation Tests (TDD-0011)
# ---------------------------------------------------------------------------


class TestActionOperation:
    """Tests for ActionOperation dataclass."""

    def test_create_action_operation(self) -> None:
        """ActionOperation can be created with required fields."""
        task = Task(gid="task_123", name="Test Task")

        op = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target_gid="tag_456",
        )

        assert op.task is task
        assert op.action == ActionType.ADD_TAG
        assert op.target_gid == "tag_456"

    def test_action_operation_is_frozen(self) -> None:
        """ActionOperation is immutable (frozen=True)."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target_gid="tag_456",
        )

        with pytest.raises(AttributeError):
            op.target_gid = "tag_789"  # type: ignore[misc]

    def test_action_operation_repr(self) -> None:
        """ActionOperation repr is readable."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target_gid="tag_456",
        )

        repr_str = repr(op)
        assert "ActionOperation" in repr_str
        assert "add_tag" in repr_str
        assert "Task" in repr_str
        assert "task_123" in repr_str
        assert "tag_456" in repr_str

    def test_to_api_call_add_tag(self) -> None:
        """to_api_call returns correct endpoint for ADD_TAG."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target_gid="tag_456",
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/addTag"
        assert payload == {"data": {"tag": "tag_456"}}

    def test_to_api_call_remove_tag(self) -> None:
        """to_api_call returns correct endpoint for REMOVE_TAG."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.REMOVE_TAG,
            target_gid="tag_456",
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/removeTag"
        assert payload == {"data": {"tag": "tag_456"}}

    def test_to_api_call_add_to_project(self) -> None:
        """to_api_call returns correct endpoint for ADD_TO_PROJECT."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_TO_PROJECT,
            target_gid="project_789",
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/addProject"
        assert payload == {"data": {"project": "project_789"}}

    def test_to_api_call_remove_from_project(self) -> None:
        """to_api_call returns correct endpoint for REMOVE_FROM_PROJECT."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.REMOVE_FROM_PROJECT,
            target_gid="project_789",
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/removeProject"
        assert payload == {"data": {"project": "project_789"}}

    def test_to_api_call_add_dependency(self) -> None:
        """to_api_call returns correct endpoint for ADD_DEPENDENCY."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_DEPENDENCY,
            target_gid="task_456",
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/addDependencies"
        assert payload == {"data": {"dependencies": ["task_456"]}}

    def test_to_api_call_remove_dependency(self) -> None:
        """to_api_call returns correct endpoint for REMOVE_DEPENDENCY."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.REMOVE_DEPENDENCY,
            target_gid="task_456",
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/removeDependencies"
        assert payload == {"data": {"dependencies": ["task_456"]}}

    def test_to_api_call_move_to_section(self) -> None:
        """to_api_call returns correct endpoint for MOVE_TO_SECTION."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.MOVE_TO_SECTION,
            target_gid="section_789",
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/sections/section_789/addTask"
        assert payload == {"data": {"task": "task_123"}}


# ---------------------------------------------------------------------------
# ActionResult Tests (TDD-0011)
# ---------------------------------------------------------------------------


class TestActionResult:
    """Tests for ActionResult dataclass."""

    def test_create_successful_action_result(self) -> None:
        """ActionResult can be created for success."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target_gid="tag_456",
        )

        result = ActionResult(
            action=action,
            success=True,
            response_data={"gid": "tag_456"},
        )

        assert result.action is action
        assert result.success is True
        assert result.error is None
        assert result.response_data == {"gid": "tag_456"}

    def test_create_failed_action_result(self) -> None:
        """ActionResult can be created for failure."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target_gid="tag_456",
        )
        error = RuntimeError("API error")

        result = ActionResult(
            action=action,
            success=False,
            error=error,
        )

        assert result.action is action
        assert result.success is False
        assert result.error is error
        assert result.response_data is None

    def test_action_result_repr_success(self) -> None:
        """ActionResult repr shows success status."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target_gid="tag_456",
        )

        result = ActionResult(action=action, success=True)

        repr_str = repr(result)
        assert "ActionResult" in repr_str
        assert "add_tag" in repr_str
        assert "success" in repr_str

    def test_action_result_repr_failed(self) -> None:
        """ActionResult repr shows failed status."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.REMOVE_TAG,
            target_gid="tag_456",
        )

        result = ActionResult(
            action=action,
            success=False,
            error=ValueError("test"),
        )

        repr_str = repr(result)
        assert "ActionResult" in repr_str
        assert "remove_tag" in repr_str
        assert "failed" in repr_str

    def test_action_result_defaults(self) -> None:
        """ActionResult has correct defaults."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target_gid="tag_456",
        )

        result = ActionResult(action=action, success=True)

        assert result.error is None
        assert result.response_data is None


# ---------------------------------------------------------------------------
# TDD-0012: Extended ActionOperation Tests
# ---------------------------------------------------------------------------


class TestActionOperationExtended:
    """Extended tests for ActionOperation with TDD-0012 features."""

    def test_action_operation_add_follower_to_api_call(self) -> None:
        """to_api_call returns correct endpoint for ADD_FOLLOWER."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_FOLLOWER,
            target_gid="user_456",
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/addFollowers"
        assert payload == {"data": {"followers": ["user_456"]}}

    def test_action_operation_remove_follower_to_api_call(self) -> None:
        """to_api_call returns correct endpoint for REMOVE_FOLLOWER."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.REMOVE_FOLLOWER,
            target_gid="user_456",
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/removeFollowers"
        assert payload == {"data": {"followers": ["user_456"]}}

    def test_action_operation_add_to_project_with_positioning(self) -> None:
        """to_api_call includes positioning for ADD_TO_PROJECT."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_TO_PROJECT,
            target_gid="project_789",
            extra_params={"insert_before": "other_task"},
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/addProject"
        assert payload == {
            "data": {
                "project": "project_789",
                "insert_before": "other_task",
            }
        }

    def test_action_operation_add_to_project_with_insert_after(self) -> None:
        """to_api_call includes insert_after for ADD_TO_PROJECT."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_TO_PROJECT,
            target_gid="project_789",
            extra_params={"insert_after": "other_task"},
        )

        method, endpoint, payload = op.to_api_call()

        assert payload == {
            "data": {
                "project": "project_789",
                "insert_after": "other_task",
            }
        }

    def test_action_operation_move_to_section_with_positioning(self) -> None:
        """to_api_call includes positioning for MOVE_TO_SECTION."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.MOVE_TO_SECTION,
            target_gid="section_789",
            extra_params={"insert_before": "other_task"},
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/sections/section_789/addTask"
        assert payload == {
            "data": {
                "task": "task_123",
                "insert_before": "other_task",
            }
        }

    def test_action_operation_move_to_section_with_insert_after(self) -> None:
        """to_api_call includes insert_after for MOVE_TO_SECTION."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.MOVE_TO_SECTION,
            target_gid="section_789",
            extra_params={"insert_after": "other_task"},
        )

        method, endpoint, payload = op.to_api_call()

        assert payload == {
            "data": {
                "task": "task_123",
                "insert_after": "other_task",
            }
        }

    def test_action_operation_with_extra_params_default(self) -> None:
        """ActionOperation extra_params defaults to empty dict."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target_gid="tag_456",
        )

        assert op.extra_params == {}

    def test_action_operation_target_gid_optional(self) -> None:
        """ActionOperation target_gid can be None."""
        task = Task(gid="task_123")
        # This is valid for potential future actions that don't need a target
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target_gid=None,
        )

        assert op.target_gid is None


class TestActionTypeExtended:
    """Extended tests for ActionType enum with TDD-0012 features."""

    def test_add_follower_value(self) -> None:
        """ADD_FOLLOWER has value 'add_follower'."""
        assert ActionType.ADD_FOLLOWER.value == "add_follower"

    def test_remove_follower_value(self) -> None:
        """REMOVE_FOLLOWER has value 'remove_follower'."""
        assert ActionType.REMOVE_FOLLOWER.value == "remove_follower"

    def test_add_dependent_value(self) -> None:
        """ADD_DEPENDENT has value 'add_dependent'."""
        assert ActionType.ADD_DEPENDENT.value == "add_dependent"

    def test_remove_dependent_value(self) -> None:
        """REMOVE_DEPENDENT has value 'remove_dependent'."""
        assert ActionType.REMOVE_DEPENDENT.value == "remove_dependent"

    def test_add_like_value(self) -> None:
        """ADD_LIKE has value 'add_like'."""
        assert ActionType.ADD_LIKE.value == "add_like"

    def test_remove_like_value(self) -> None:
        """REMOVE_LIKE has value 'remove_like'."""
        assert ActionType.REMOVE_LIKE.value == "remove_like"

    def test_add_comment_value(self) -> None:
        """ADD_COMMENT has value 'add_comment'."""
        assert ActionType.ADD_COMMENT.value == "add_comment"

    def test_all_action_types_exist(self) -> None:
        """All expected action types exist including Phase 2 and Phase 3 actions."""
        actions = [a.value for a in ActionType]
        expected = {
            "add_tag",
            "remove_tag",
            "add_to_project",
            "remove_from_project",
            "add_dependency",
            "remove_dependency",
            "move_to_section",
            "add_follower",
            "remove_follower",
            "add_dependent",
            "remove_dependent",
            "add_like",
            "remove_like",
            "add_comment",
            "set_parent",
        }
        assert set(actions) == expected


# ---------------------------------------------------------------------------
# TDD-0012 Phase 2: Extended ActionOperation to_api_call Tests
# ---------------------------------------------------------------------------


class TestActionOperationPhase2:
    """Tests for ActionOperation to_api_call() with Phase 2 actions."""

    def test_add_dependent_to_api_call(self) -> None:
        """to_api_call returns correct endpoint for ADD_DEPENDENT."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_DEPENDENT,
            target_gid="dependent_456",
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/addDependents"
        assert payload == {"data": {"dependents": ["dependent_456"]}}

    def test_remove_dependent_to_api_call(self) -> None:
        """to_api_call returns correct endpoint for REMOVE_DEPENDENT."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.REMOVE_DEPENDENT,
            target_gid="dependent_456",
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/removeDependents"
        assert payload == {"data": {"dependents": ["dependent_456"]}}

    def test_add_like_to_api_call(self) -> None:
        """to_api_call returns correct endpoint for ADD_LIKE (no target_gid)."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_LIKE,
            target_gid=None,  # Per ADR-0045: No target_gid for likes
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/addLike"
        assert payload == {"data": {}}

    def test_remove_like_to_api_call(self) -> None:
        """to_api_call returns correct endpoint for REMOVE_LIKE (no target_gid)."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.REMOVE_LIKE,
            target_gid=None,  # Per ADR-0045: No target_gid for likes
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/removeLike"
        assert payload == {"data": {}}

    def test_add_comment_to_api_call(self) -> None:
        """to_api_call returns correct endpoint for ADD_COMMENT."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_COMMENT,
            target_gid=None,
            extra_params={"text": "This is a comment"},
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/stories"
        assert payload == {"data": {"text": "This is a comment"}}

    def test_add_comment_with_html_to_api_call(self) -> None:
        """to_api_call includes html_text for ADD_COMMENT when provided."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_COMMENT,
            target_gid=None,
            extra_params={
                "text": "Plain text",
                "html_text": "<body>Rich <strong>HTML</strong></body>",
            },
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/stories"
        assert payload == {
            "data": {
                "text": "Plain text",
                "html_text": "<body>Rich <strong>HTML</strong></body>",
            }
        }

    def test_add_comment_with_empty_text(self) -> None:
        """to_api_call handles empty text for ADD_COMMENT."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_COMMENT,
            target_gid=None,
            extra_params={"text": ""},
        )

        method, endpoint, payload = op.to_api_call()

        assert payload == {"data": {"text": ""}}

    def test_set_parent_to_api_call(self) -> None:
        """to_api_call returns correct endpoint for SET_PARENT."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.SET_PARENT,
            target_gid=None,
            extra_params={"parent": "parent_456"},
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/setParent"
        assert payload == {"data": {"parent": "parent_456"}}

    def test_set_parent_with_none_promotes(self) -> None:
        """to_api_call SET_PARENT with None parent promotes to top-level."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.SET_PARENT,
            target_gid=None,
            extra_params={"parent": None},
        )

        method, endpoint, payload = op.to_api_call()

        assert method == "POST"
        assert endpoint == "/tasks/task_123/setParent"
        assert payload == {"data": {"parent": None}}

    def test_set_parent_with_positioning(self) -> None:
        """to_api_call SET_PARENT includes positioning in API call."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.SET_PARENT,
            target_gid=None,
            extra_params={
                "parent": "parent_456",
                "insert_after": "sibling_789",
            },
        )

        method, endpoint, payload = op.to_api_call()

        assert payload == {
            "data": {
                "parent": "parent_456",
                "insert_after": "sibling_789",
            }
        }

    def test_set_parent_with_insert_before(self) -> None:
        """to_api_call SET_PARENT includes insert_before in API call."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.SET_PARENT,
            target_gid=None,
            extra_params={
                "parent": "parent_456",
                "insert_before": "sibling_789",
            },
        )

        method, endpoint, payload = op.to_api_call()

        assert payload == {
            "data": {
                "parent": "parent_456",
                "insert_before": "sibling_789",
            }
        }
