"""Tests for persistence data models.

Per TDD-0010: Verify EntityState, OperationType, PlannedOperation,
SaveError, and SaveResult classes.

Per TDD-0011: Verify ActionType, ActionOperation, and ActionResult classes.
"""

from __future__ import annotations

import pytest

from autom8_asana.models import Task
from autom8_asana.models.common import NameGid
from autom8_asana.persistence.models import (
    ActionOperation,
    ActionResult,
    # TDD-0011: Action types
    ActionType,
    EntityState,
    OperationType,
    PlannedOperation,
    SaveError,
    SaveResult,
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
        cause = OSError("Network failed")
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
            target=NameGid(gid="tag_456"),
        )

        assert op.task is task
        assert op.action == ActionType.ADD_TAG
        assert op.target.gid == "tag_456"

    def test_action_operation_is_frozen(self) -> None:
        """ActionOperation is immutable (frozen=True)."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )

        with pytest.raises(AttributeError):
            op.target = NameGid(gid="tag_789")  # type: ignore[misc]

    def test_action_operation_repr(self) -> None:
        """ActionOperation repr is readable."""
        task = Task(gid="task_123")
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
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
            target=NameGid(gid="tag_456"),
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
            target=NameGid(gid="tag_456"),
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
            target=NameGid(gid="project_789"),
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
            target=NameGid(gid="project_789"),
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
            target=NameGid(gid="task_456"),
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
            target=NameGid(gid="task_456"),
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
            target=NameGid(gid="section_789"),
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
            target=NameGid(gid="tag_456"),
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
            target=NameGid(gid="tag_456"),
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
            target=NameGid(gid="tag_456"),
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
            target=NameGid(gid="tag_456"),
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
            target=NameGid(gid="tag_456"),
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
            target=NameGid(gid="user_456"),
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
            target=NameGid(gid="user_456"),
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
            target=NameGid(gid="project_789"),
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
            target=NameGid(gid="project_789"),
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
            target=NameGid(gid="section_789"),
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
            target=NameGid(gid="section_789"),
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
            target=NameGid(gid="tag_456"),
        )

        assert op.extra_params == {}

    def test_action_operation_target_optional(self) -> None:
        """ActionOperation target can be None."""
        task = Task(gid="task_123")
        # This is valid for potential future actions that don't need a target
        op = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=None,
        )

        assert op.target is None


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
            target=NameGid(gid="dependent_456"),
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
            target=NameGid(gid="dependent_456"),
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
            target=None,  # Per ADR-0045: No target_gid for likes
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
            target=None,  # Per ADR-0045: No target_gid for likes
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
            target=None,
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
            target=None,
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
            target=None,
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
            target=None,
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
            target=None,
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
            target=None,
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
            target=None,
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


# ---------------------------------------------------------------------------
# TDD-HARDENING-F Phase 2: Retryable Error Classification Tests (ADR-0079)
# ---------------------------------------------------------------------------


class TestSaveErrorRetryable:
    """Tests for SaveError.is_retryable property per ADR-0079."""

    def test_is_retryable_429_rate_limit(self) -> None:
        """429 status code is retryable (FR-FH-002)."""
        from autom8_asana.exceptions import RateLimitError

        task = Task(gid="123")
        error = RateLimitError("Rate limited", status_code=429, retry_after=60)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.is_retryable is True

    def test_is_retryable_500_server_error(self) -> None:
        """500 status code is retryable (FR-FH-003)."""
        from autom8_asana.exceptions import ServerError

        task = Task(gid="123")
        error = ServerError("Internal Server Error", status_code=500)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.is_retryable is True

    def test_is_retryable_502_bad_gateway(self) -> None:
        """502 status code is retryable (FR-FH-003)."""
        from autom8_asana.exceptions import ServerError

        task = Task(gid="123")
        error = ServerError("Bad Gateway", status_code=502)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.is_retryable is True

    def test_is_retryable_503_service_unavailable(self) -> None:
        """503 status code is retryable (FR-FH-003)."""
        from autom8_asana.exceptions import ServerError

        task = Task(gid="123")
        error = ServerError("Service Unavailable", status_code=503)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.is_retryable is True

    def test_is_retryable_504_gateway_timeout(self) -> None:
        """504 status code is retryable (FR-FH-003)."""
        from autom8_asana.exceptions import ServerError

        task = Task(gid="123")
        error = ServerError("Gateway Timeout", status_code=504)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.is_retryable is True

    def test_not_retryable_400_bad_request(self) -> None:
        """400 status code is not retryable (FR-FH-004)."""
        from autom8_asana.exceptions import AsanaError

        task = Task(gid="123")
        error = AsanaError("Bad Request", status_code=400)

        save_error = SaveError(
            entity=task,
            operation=OperationType.CREATE,
            error=error,
            payload={},
        )

        assert save_error.is_retryable is False

    def test_not_retryable_401_unauthorized(self) -> None:
        """401 status code is not retryable (FR-FH-004)."""
        from autom8_asana.exceptions import AuthenticationError

        task = Task(gid="123")
        error = AuthenticationError("Unauthorized", status_code=401)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.is_retryable is False

    def test_not_retryable_403_forbidden(self) -> None:
        """403 status code is not retryable (FR-FH-004)."""
        from autom8_asana.exceptions import ForbiddenError

        task = Task(gid="123")
        error = ForbiddenError("Forbidden", status_code=403)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.is_retryable is False

    def test_not_retryable_404_not_found(self) -> None:
        """404 status code is not retryable (FR-FH-004)."""
        from autom8_asana.exceptions import NotFoundError

        task = Task(gid="123")
        error = NotFoundError("Not Found", status_code=404)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.is_retryable is False

    def test_not_retryable_unknown_error(self) -> None:
        """Unknown errors (no status code) are not retryable."""
        task = Task(gid="123")
        error = ValueError("Something went wrong")

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.is_retryable is False

    def test_is_retryable_timeout_error(self) -> None:
        """TimeoutError is retryable (network error)."""
        task = Task(gid="123")
        error = TimeoutError("Connection timed out")

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.is_retryable is True

    def test_is_retryable_connection_error(self) -> None:
        """ConnectionError is retryable (network error)."""
        task = Task(gid="123")
        error = ConnectionError("Connection refused")

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.is_retryable is True

    def test_is_retryable_os_error(self) -> None:
        """OSError is retryable (network error)."""
        task = Task(gid="123")
        error = OSError("Network unreachable")

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.is_retryable is True


class TestSaveErrorRecoveryHint:
    """Tests for SaveError.recovery_hint property."""

    def test_recovery_hint_429(self) -> None:
        """429 provides rate limit specific hint."""
        from autom8_asana.exceptions import RateLimitError

        task = Task(gid="123")
        error = RateLimitError("Rate limited", status_code=429)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert "retry_after_seconds" in save_error.recovery_hint.lower()

    def test_recovery_hint_500(self) -> None:
        """500 provides server error hint."""
        from autom8_asana.exceptions import ServerError

        task = Task(gid="123")
        error = ServerError("Internal Server Error", status_code=500)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert "retry" in save_error.recovery_hint.lower()
        assert "exponential backoff" in save_error.recovery_hint.lower()

    def test_recovery_hint_400(self) -> None:
        """400 provides bad request hint."""
        from autom8_asana.exceptions import AsanaError

        task = Task(gid="123")
        error = AsanaError("Bad Request", status_code=400)

        save_error = SaveError(
            entity=task,
            operation=OperationType.CREATE,
            error=error,
            payload={},
        )

        assert "payload" in save_error.recovery_hint.lower()

    def test_recovery_hint_401(self) -> None:
        """401 provides authentication hint."""
        from autom8_asana.exceptions import AuthenticationError

        task = Task(gid="123")
        error = AuthenticationError("Unauthorized", status_code=401)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert "credential" in save_error.recovery_hint.lower()

    def test_recovery_hint_403(self) -> None:
        """403 provides permission hint."""
        from autom8_asana.exceptions import ForbiddenError

        task = Task(gid="123")
        error = ForbiddenError("Forbidden", status_code=403)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert "permission" in save_error.recovery_hint.lower()

    def test_recovery_hint_404(self) -> None:
        """404 provides not found hint."""
        from autom8_asana.exceptions import NotFoundError

        task = Task(gid="123")
        error = NotFoundError("Not Found", status_code=404)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert "not found" in save_error.recovery_hint.lower()

    def test_recovery_hint_timeout(self) -> None:
        """TimeoutError provides timeout hint."""
        task = Task(gid="123")
        error = TimeoutError("Connection timed out")

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert "timed out" in save_error.recovery_hint.lower()

    def test_recovery_hint_connection_error(self) -> None:
        """ConnectionError provides connectivity hint."""
        task = Task(gid="123")
        error = ConnectionError("Connection refused")

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert "connectivity" in save_error.recovery_hint.lower()

    def test_recovery_hint_unknown_error(self) -> None:
        """Unknown errors provide generic hint."""
        task = Task(gid="123")
        error = ValueError("Something went wrong")

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert "unknown" in save_error.recovery_hint.lower()


class TestSaveErrorRetryAfterSeconds:
    """Tests for SaveError.retry_after_seconds property."""

    def test_retry_after_from_rate_limit_error(self) -> None:
        """retry_after_seconds extracts from RateLimitError."""
        from autom8_asana.exceptions import RateLimitError

        task = Task(gid="123")
        error = RateLimitError("Rate limited", status_code=429, retry_after=60)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.retry_after_seconds == 60

    def test_retry_after_none_for_non_rate_limit(self) -> None:
        """retry_after_seconds is None for non-rate-limit errors."""
        from autom8_asana.exceptions import ServerError

        task = Task(gid="123")
        error = ServerError("Internal Server Error", status_code=500)

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.retry_after_seconds is None

    def test_retry_after_none_for_generic_error(self) -> None:
        """retry_after_seconds is None for generic errors."""
        task = Task(gid="123")
        error = ValueError("Something went wrong")

        save_error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=error,
            payload={},
        )

        assert save_error.retry_after_seconds is None


class TestSaveResultRetryableHelpers:
    """Tests for SaveResult retryable helper methods (FR-FH-005, FR-FH-006, FR-FH-007)."""

    def test_failed_count(self) -> None:
        """failed_count returns number of failures (FR-FH-007)."""
        task1 = Task(gid="123")
        task2 = Task(gid="456")

        error1 = SaveError(
            entity=task1,
            operation=OperationType.UPDATE,
            error=ValueError("Error 1"),
            payload={},
        )
        error2 = SaveError(
            entity=task2,
            operation=OperationType.CREATE,
            error=ValueError("Error 2"),
            payload={},
        )

        result = SaveResult(failed=[error1, error2])

        assert result.failed_count == 2

    def test_failed_count_empty(self) -> None:
        """failed_count returns 0 when no failures."""
        result = SaveResult()

        assert result.failed_count == 0

    def test_get_failed_entities(self) -> None:
        """get_failed_entities returns entities from failures (FR-FH-005)."""
        task1 = Task(gid="123")
        task2 = Task(gid="456")

        error1 = SaveError(
            entity=task1,
            operation=OperationType.UPDATE,
            error=ValueError("Error 1"),
            payload={},
        )
        error2 = SaveError(
            entity=task2,
            operation=OperationType.CREATE,
            error=ValueError("Error 2"),
            payload={},
        )

        result = SaveResult(failed=[error1, error2])
        entities = result.get_failed_entities()

        assert len(entities) == 2
        assert task1 in entities
        assert task2 in entities

    def test_get_failed_entities_empty(self) -> None:
        """get_failed_entities returns empty list when no failures."""
        result = SaveResult()

        assert result.get_failed_entities() == []

    def test_retryable_failures_filters_correctly(self) -> None:
        """retryable_failures returns only retryable errors."""
        from autom8_asana.exceptions import NotFoundError, RateLimitError

        task1 = Task(gid="123")
        task2 = Task(gid="456")

        retryable = SaveError(
            entity=task1,
            operation=OperationType.UPDATE,
            error=RateLimitError("Rate limited", status_code=429),
            payload={},
        )
        non_retryable = SaveError(
            entity=task2,
            operation=OperationType.UPDATE,
            error=NotFoundError("Not found", status_code=404),
            payload={},
        )

        result = SaveResult(failed=[retryable, non_retryable])

        assert len(result.retryable_failures) == 1
        assert result.retryable_failures[0] is retryable

    def test_non_retryable_failures_filters_correctly(self) -> None:
        """non_retryable_failures returns only non-retryable errors."""
        from autom8_asana.exceptions import NotFoundError, RateLimitError

        task1 = Task(gid="123")
        task2 = Task(gid="456")

        retryable = SaveError(
            entity=task1,
            operation=OperationType.UPDATE,
            error=RateLimitError("Rate limited", status_code=429),
            payload={},
        )
        non_retryable = SaveError(
            entity=task2,
            operation=OperationType.UPDATE,
            error=NotFoundError("Not found", status_code=404),
            payload={},
        )

        result = SaveResult(failed=[retryable, non_retryable])

        assert len(result.non_retryable_failures) == 1
        assert result.non_retryable_failures[0] is non_retryable

    def test_has_retryable_failures_true(self) -> None:
        """has_retryable_failures is True when retryable error present."""
        from autom8_asana.exceptions import RateLimitError

        task = Task(gid="123")
        error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=RateLimitError("Rate limited", status_code=429),
            payload={},
        )

        result = SaveResult(failed=[error])

        assert result.has_retryable_failures is True

    def test_has_retryable_failures_false(self) -> None:
        """has_retryable_failures is False when no retryable errors."""
        from autom8_asana.exceptions import NotFoundError

        task = Task(gid="123")
        error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=NotFoundError("Not found", status_code=404),
            payload={},
        )

        result = SaveResult(failed=[error])

        assert result.has_retryable_failures is False

    def test_has_retryable_failures_false_when_empty(self) -> None:
        """has_retryable_failures is False when no failures."""
        result = SaveResult()

        assert result.has_retryable_failures is False

    def test_get_retryable_errors_alias(self) -> None:
        """get_retryable_errors() is alias for retryable_failures (FR-FH-006)."""
        from autom8_asana.exceptions import RateLimitError

        task = Task(gid="123")
        error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=RateLimitError("Rate limited", status_code=429),
            payload={},
        )

        result = SaveResult(failed=[error])

        assert result.get_retryable_errors() == result.retryable_failures

    def test_get_recovery_summary_no_failures(self) -> None:
        """get_recovery_summary returns message when no failures."""
        result = SaveResult()

        assert result.get_recovery_summary() == "No failures."

    def test_get_recovery_summary_with_failures(self) -> None:
        """get_recovery_summary includes retryable and non-retryable sections."""
        from autom8_asana.exceptions import NotFoundError, RateLimitError

        task1 = Task(gid="123")
        task2 = Task(gid="456")

        retryable = SaveError(
            entity=task1,
            operation=OperationType.UPDATE,
            error=RateLimitError("Rate limited", status_code=429),
            payload={},
        )
        non_retryable = SaveError(
            entity=task2,
            operation=OperationType.UPDATE,
            error=NotFoundError("Not found", status_code=404),
            payload={},
        )

        result = SaveResult(failed=[retryable, non_retryable])
        summary = result.get_recovery_summary()

        assert "Total failures: 2" in summary
        assert "Retryable (1)" in summary
        assert "Non-retryable (1)" in summary
        assert "Task(gid=123)" in summary
        assert "Task(gid=456)" in summary


class TestPartialSaveErrorEnhanced:
    """Tests for PartialSaveError with retryable classification."""

    def test_partial_save_error_message_includes_retryable_counts(self) -> None:
        """PartialSaveError message includes retryable/non-retryable counts."""
        from autom8_asana.exceptions import NotFoundError, RateLimitError
        from autom8_asana.persistence.exceptions import PartialSaveError

        task1 = Task(gid="123")
        task2 = Task(gid="456")

        retryable = SaveError(
            entity=task1,
            operation=OperationType.UPDATE,
            error=RateLimitError("Rate limited", status_code=429),
            payload={},
        )
        non_retryable = SaveError(
            entity=task2,
            operation=OperationType.UPDATE,
            error=NotFoundError("Not found", status_code=404),
            payload={},
        )

        result = SaveResult(failed=[retryable, non_retryable])

        with pytest.raises(PartialSaveError) as exc_info:
            result.raise_on_failure()

        message = str(exc_info.value)
        assert "2/2 operations failed" in message
        assert "1 retryable" in message
        assert "1 non-retryable" in message

    def test_partial_save_error_is_retryable_true(self) -> None:
        """PartialSaveError.is_retryable is True when retryable errors exist."""
        from autom8_asana.exceptions import RateLimitError
        from autom8_asana.persistence.exceptions import PartialSaveError

        task = Task(gid="123")
        error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=RateLimitError("Rate limited", status_code=429),
            payload={},
        )

        result = SaveResult(failed=[error])

        with pytest.raises(PartialSaveError) as exc_info:
            result.raise_on_failure()

        assert exc_info.value.is_retryable is True

    def test_partial_save_error_is_retryable_false(self) -> None:
        """PartialSaveError.is_retryable is False when no retryable errors."""
        from autom8_asana.exceptions import NotFoundError
        from autom8_asana.persistence.exceptions import PartialSaveError

        task = Task(gid="123")
        error = SaveError(
            entity=task,
            operation=OperationType.UPDATE,
            error=NotFoundError("Not found", status_code=404),
            payload={},
        )

        result = SaveResult(failed=[error])

        with pytest.raises(PartialSaveError) as exc_info:
            result.raise_on_failure()

        assert exc_info.value.is_retryable is False

    def test_partial_save_error_retryable_count(self) -> None:
        """PartialSaveError.retryable_count returns correct count."""
        from autom8_asana.exceptions import RateLimitError, ServerError
        from autom8_asana.persistence.exceptions import PartialSaveError

        task1 = Task(gid="123")
        task2 = Task(gid="456")

        error1 = SaveError(
            entity=task1,
            operation=OperationType.UPDATE,
            error=RateLimitError("Rate limited", status_code=429),
            payload={},
        )
        error2 = SaveError(
            entity=task2,
            operation=OperationType.UPDATE,
            error=ServerError("Server error", status_code=500),
            payload={},
        )

        result = SaveResult(failed=[error1, error2])

        with pytest.raises(PartialSaveError) as exc_info:
            result.raise_on_failure()

        assert exc_info.value.retryable_count == 2

    def test_partial_save_error_non_retryable_count(self) -> None:
        """PartialSaveError.non_retryable_count returns correct count."""
        from autom8_asana.exceptions import ForbiddenError, NotFoundError
        from autom8_asana.persistence.exceptions import PartialSaveError

        task1 = Task(gid="123")
        task2 = Task(gid="456")

        error1 = SaveError(
            entity=task1,
            operation=OperationType.UPDATE,
            error=NotFoundError("Not found", status_code=404),
            payload={},
        )
        error2 = SaveError(
            entity=task2,
            operation=OperationType.UPDATE,
            error=ForbiddenError("Forbidden", status_code=403),
            payload={},
        )

        result = SaveResult(failed=[error1, error2])

        with pytest.raises(PartialSaveError) as exc_info:
            result.raise_on_failure()

        assert exc_info.value.non_retryable_count == 2


class TestActionResultRetryable:
    """Tests for ActionResult.is_retryable property."""

    def test_is_retryable_false_on_success(self) -> None:
        """ActionResult.is_retryable is False for successful actions."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )

        result = ActionResult(action=action, success=True)

        assert result.is_retryable is False

    def test_is_retryable_429(self) -> None:
        """ActionResult.is_retryable is True for 429 errors."""
        from autom8_asana.exceptions import RateLimitError

        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )
        error = RateLimitError("Rate limited", status_code=429)

        result = ActionResult(action=action, success=False, error=error)

        assert result.is_retryable is True

    def test_is_retryable_500(self) -> None:
        """ActionResult.is_retryable is True for 500 errors."""
        from autom8_asana.exceptions import ServerError

        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )
        error = ServerError("Internal Server Error", status_code=500)

        result = ActionResult(action=action, success=False, error=error)

        assert result.is_retryable is True

    def test_is_retryable_false_for_404(self) -> None:
        """ActionResult.is_retryable is False for 404 errors."""
        from autom8_asana.exceptions import NotFoundError

        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )
        error = NotFoundError("Not found", status_code=404)

        result = ActionResult(action=action, success=False, error=error)

        assert result.is_retryable is False

    def test_is_retryable_timeout_error(self) -> None:
        """ActionResult.is_retryable is True for TimeoutError."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )
        error = TimeoutError("Connection timed out")

        result = ActionResult(action=action, success=False, error=error)

        assert result.is_retryable is True


class TestActionResultRecoveryHint:
    """Tests for ActionResult.recovery_hint property."""

    def test_recovery_hint_empty_on_success(self) -> None:
        """ActionResult.recovery_hint is empty for successful actions."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )

        result = ActionResult(action=action, success=True)

        assert result.recovery_hint == ""

    def test_recovery_hint_429(self) -> None:
        """ActionResult.recovery_hint provides guidance for 429."""
        from autom8_asana.exceptions import RateLimitError

        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )
        error = RateLimitError("Rate limited", status_code=429)

        result = ActionResult(action=action, success=False, error=error)

        assert "rate limit" in result.recovery_hint.lower()

    def test_recovery_hint_500(self) -> None:
        """ActionResult.recovery_hint provides guidance for 500."""
        from autom8_asana.exceptions import ServerError

        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )
        error = ServerError("Internal Server Error", status_code=500)

        result = ActionResult(action=action, success=False, error=error)

        assert "retry" in result.recovery_hint.lower()


class TestActionResultRetryAfterSeconds:
    """Tests for ActionResult.retry_after_seconds property."""

    def test_retry_after_from_rate_limit_error(self) -> None:
        """retry_after_seconds extracts from RateLimitError."""
        from autom8_asana.exceptions import RateLimitError

        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )
        error = RateLimitError("Rate limited", status_code=429, retry_after=30)

        result = ActionResult(action=action, success=False, error=error)

        assert result.retry_after_seconds == 30

    def test_retry_after_none_on_success(self) -> None:
        """retry_after_seconds is None for successful actions."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )

        result = ActionResult(action=action, success=True)

        assert result.retry_after_seconds is None

    def test_retry_after_none_for_non_rate_limit(self) -> None:
        """retry_after_seconds is None for non-rate-limit errors."""
        from autom8_asana.exceptions import ServerError

        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )
        error = ServerError("Server Error", status_code=500)

        result = ActionResult(action=action, success=False, error=error)

        assert result.retry_after_seconds is None
