"""Tests for persistence exception hierarchy.

Per TDD-0010: Verify SaveOrchestrationError and subclasses.
Per TDD-0011: Verify UnsupportedOperationError.
"""

from __future__ import annotations

import pytest

from autom8_asana.exceptions import AsanaError
from autom8_asana.models import Task
from autom8_asana.persistence.exceptions import (
    CyclicDependencyError,
    DependencyResolutionError,
    PartialSaveError,
    SaveOrchestrationError,
    SessionClosedError,
    UnsupportedOperationError,
)
from autom8_asana.persistence.models import (
    OperationType,
    SaveError,
    SaveResult,
)


# ---------------------------------------------------------------------------
# SaveOrchestrationError Tests
# ---------------------------------------------------------------------------


class TestSaveOrchestrationError:
    """Tests for SaveOrchestrationError base class."""

    def test_inherits_from_asana_error(self) -> None:
        """SaveOrchestrationError inherits from AsanaError."""
        assert issubclass(SaveOrchestrationError, AsanaError)

    def test_create_with_message(self) -> None:
        """SaveOrchestrationError can be created with message."""
        error = SaveOrchestrationError("Test error message")

        assert str(error) == "Test error message"

    def test_can_catch_as_asana_error(self) -> None:
        """SaveOrchestrationError can be caught as AsanaError."""
        try:
            raise SaveOrchestrationError("Test")
        except AsanaError as e:
            assert str(e) == "Test"


# ---------------------------------------------------------------------------
# SessionClosedError Tests
# ---------------------------------------------------------------------------


class TestSessionClosedError:
    """Tests for SessionClosedError."""

    def test_inherits_from_save_orchestration_error(self) -> None:
        """SessionClosedError inherits from SaveOrchestrationError."""
        assert issubclass(SessionClosedError, SaveOrchestrationError)

    def test_default_message(self) -> None:
        """SessionClosedError has standard message."""
        error = SessionClosedError()

        assert "Session is closed" in str(error)
        assert "Cannot perform operations" in str(error)

    def test_can_catch_as_save_orchestration_error(self) -> None:
        """SessionClosedError can be caught as SaveOrchestrationError."""
        try:
            raise SessionClosedError()
        except SaveOrchestrationError as e:
            assert "closed" in str(e).lower()


# ---------------------------------------------------------------------------
# CyclicDependencyError Tests
# ---------------------------------------------------------------------------


class TestCyclicDependencyError:
    """Tests for CyclicDependencyError."""

    def test_inherits_from_save_orchestration_error(self) -> None:
        """CyclicDependencyError inherits from SaveOrchestrationError."""
        assert issubclass(CyclicDependencyError, SaveOrchestrationError)

    def test_stores_cycle_entities(self) -> None:
        """CyclicDependencyError stores cycle participants."""
        task1 = Task(gid="123", name="Task 1")
        task2 = Task(gid="456", name="Task 2")

        error = CyclicDependencyError([task1, task2])

        assert error.cycle == [task1, task2]

    def test_message_includes_entity_info(self) -> None:
        """CyclicDependencyError message includes entity details."""
        task1 = Task(gid="123")
        task2 = Task(gid="456")

        error = CyclicDependencyError([task1, task2])
        message = str(error)

        assert "Cyclic dependency detected" in message
        assert "Task(gid=123)" in message
        assert "Task(gid=456)" in message
        assert " -> " in message

    def test_single_entity_cycle(self) -> None:
        """CyclicDependencyError handles single entity cycle."""
        task = Task(gid="123")

        error = CyclicDependencyError([task])

        assert error.cycle == [task]
        assert "Task(gid=123)" in str(error)

    def test_empty_cycle(self) -> None:
        """CyclicDependencyError handles empty cycle list."""
        error = CyclicDependencyError([])

        assert error.cycle == []
        assert "Cyclic dependency detected:" in str(error)


# ---------------------------------------------------------------------------
# DependencyResolutionError Tests
# ---------------------------------------------------------------------------


class TestDependencyResolutionError:
    """Tests for DependencyResolutionError."""

    def test_inherits_from_save_orchestration_error(self) -> None:
        """DependencyResolutionError inherits from SaveOrchestrationError."""
        assert issubclass(DependencyResolutionError, SaveOrchestrationError)

    def test_stores_entity_and_dependency(self) -> None:
        """DependencyResolutionError stores entity and dependency."""
        entity = Task(gid="123", name="Dependent Task")
        dependency = Task(gid="456", name="Parent Task")
        cause = ValueError("Parent failed")

        error = DependencyResolutionError(entity, dependency, cause)

        assert error.entity is entity
        assert error.dependency is dependency
        assert error.__cause__ is cause

    def test_message_includes_both_entities(self) -> None:
        """DependencyResolutionError message includes both entities."""
        entity = Task(gid="child")
        dependency = Task(gid="parent")
        cause = RuntimeError("API error")

        error = DependencyResolutionError(entity, dependency, cause)
        message = str(error)

        assert "Cannot save" in message
        assert "Task(gid=child)" in message
        assert "dependency" in message
        assert "Task(gid=parent)" in message
        assert "failed" in message

    def test_cause_is_chained(self) -> None:
        """DependencyResolutionError chains cause exception."""
        entity = Task(gid="123")
        dependency = Task(gid="456")
        cause = IOError("Network error")

        error = DependencyResolutionError(entity, dependency, cause)

        # Check that cause is properly chained
        assert error.__cause__ is cause
        # Can access cause details
        assert isinstance(error.__cause__, IOError)
        assert "Network error" in str(error.__cause__)


# ---------------------------------------------------------------------------
# PartialSaveError Tests
# ---------------------------------------------------------------------------


class TestPartialSaveError:
    """Tests for PartialSaveError."""

    def test_inherits_from_save_orchestration_error(self) -> None:
        """PartialSaveError inherits from SaveOrchestrationError."""
        assert issubclass(PartialSaveError, SaveOrchestrationError)

    def test_stores_save_result(self) -> None:
        """PartialSaveError stores SaveResult."""
        task = Task(gid="123")
        save_error = SaveError(
            entity=task,
            operation=OperationType.CREATE,
            error=ValueError("Failed"),
            payload={},
        )
        result = SaveResult(failed=[save_error])

        error = PartialSaveError(result)

        assert error.result is result

    def test_message_includes_failure_counts(self) -> None:
        """PartialSaveError message includes failure statistics."""
        task1 = Task(gid="123")
        task2 = Task(gid="456")
        task3 = Task(gid="789")
        save_error = SaveError(
            entity=task3,
            operation=OperationType.UPDATE,
            error=ValueError("Failed"),
            payload={},
        )
        result = SaveResult(succeeded=[task1, task2], failed=[save_error])

        error = PartialSaveError(result)
        message = str(error)

        assert "Partial save" in message
        assert "1/3" in message
        assert "operations failed" in message

    def test_all_failures_message(self) -> None:
        """PartialSaveError message correct when all fail."""
        task1 = Task(gid="123")
        task2 = Task(gid="456")
        errors = [
            SaveError(
                entity=task1,
                operation=OperationType.CREATE,
                error=ValueError("Failed 1"),
                payload={},
            ),
            SaveError(
                entity=task2,
                operation=OperationType.CREATE,
                error=ValueError("Failed 2"),
                payload={},
            ),
        ]
        result = SaveResult(failed=errors)

        error = PartialSaveError(result)
        message = str(error)

        assert "2/2" in message

    def test_can_access_result_details(self) -> None:
        """PartialSaveError allows access to result details."""
        task1 = Task(gid="123")
        task2 = Task(gid="456")
        save_error = SaveError(
            entity=task2,
            operation=OperationType.DELETE,
            error=RuntimeError("API rejected"),
            payload={},
        )
        result = SaveResult(succeeded=[task1], failed=[save_error])

        error = PartialSaveError(result)

        # Can access all details through result
        assert len(error.result.succeeded) == 1
        assert len(error.result.failed) == 1
        assert error.result.failed[0].entity.gid == "456"
        assert isinstance(error.result.failed[0].error, RuntimeError)


# ---------------------------------------------------------------------------
# UnsupportedOperationError Tests (TDD-0011)
# ---------------------------------------------------------------------------


class TestUnsupportedOperationError:
    """Tests for UnsupportedOperationError."""

    def test_inherits_from_save_orchestration_error(self) -> None:
        """UnsupportedOperationError inherits from SaveOrchestrationError."""
        assert issubclass(UnsupportedOperationError, SaveOrchestrationError)

    def test_stores_field_name_and_suggested_methods(self) -> None:
        """UnsupportedOperationError stores field name and methods."""
        error = UnsupportedOperationError(
            field_name="tags",
            suggested_methods=["add_tag", "remove_tag"],
        )

        assert error.field_name == "tags"
        assert error.suggested_methods == ["add_tag", "remove_tag"]

    def test_message_includes_field_name(self) -> None:
        """UnsupportedOperationError message includes field name."""
        error = UnsupportedOperationError(
            field_name="projects",
            suggested_methods=["add_to_project", "remove_from_project"],
        )
        message = str(error)

        assert "projects" in message
        assert "not supported" in message

    def test_message_includes_suggested_methods(self) -> None:
        """UnsupportedOperationError message includes suggested methods."""
        error = UnsupportedOperationError(
            field_name="dependencies",
            suggested_methods=["add_dependency", "remove_dependency"],
        )
        message = str(error)

        assert "add_dependency" in message
        assert "remove_dependency" in message
        assert "Use" in message

    def test_single_suggested_method(self) -> None:
        """UnsupportedOperationError handles single method."""
        error = UnsupportedOperationError(
            field_name="section",
            suggested_methods=["move_to_section"],
        )
        message = str(error)

        assert "move_to_section" in message
        # Should not have comma since only one method
        assert "section" in error.field_name

    def test_can_catch_as_save_orchestration_error(self) -> None:
        """UnsupportedOperationError can be caught as SaveOrchestrationError."""
        try:
            raise UnsupportedOperationError("tags", ["add_tag"])
        except SaveOrchestrationError as e:
            assert "tags" in str(e)

    def test_full_message_format(self) -> None:
        """UnsupportedOperationError message has correct format."""
        error = UnsupportedOperationError(
            field_name="memberships",
            suggested_methods=["add_to_project", "remove_from_project"],
        )
        message = str(error)

        expected = (
            "Direct modification of 'memberships' is not supported. "
            "Use add_to_project, remove_from_project instead. "
            "See: docs/guides/limitations.md#unsupported-direct-field-modifications"
        )
        assert message == expected


# ---------------------------------------------------------------------------
# Exception Hierarchy Tests
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    """Tests for exception hierarchy relationships."""

    def test_all_save_exceptions_inherit_correctly(self) -> None:
        """All save exceptions inherit from SaveOrchestrationError."""
        exceptions = [
            SessionClosedError,
            CyclicDependencyError,
            DependencyResolutionError,
            PartialSaveError,
            UnsupportedOperationError,
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, SaveOrchestrationError), (
                f"{exc_class.__name__} should inherit from SaveOrchestrationError"
            )

    def test_can_catch_all_save_errors(self) -> None:
        """All save errors can be caught with SaveOrchestrationError."""
        task = Task(gid="123")
        exceptions_to_test = [
            SessionClosedError(),
            CyclicDependencyError([task]),
            DependencyResolutionError(task, task, ValueError("test")),
            PartialSaveError(SaveResult(failed=[
                SaveError(entity=task, operation=OperationType.CREATE,
                          error=ValueError("x"), payload={})
            ])),
            UnsupportedOperationError("tags", ["add_tag", "remove_tag"]),
        ]

        for exc in exceptions_to_test:
            try:
                raise exc
            except SaveOrchestrationError:
                pass  # Expected
            except Exception as e:
                pytest.fail(f"{type(exc).__name__} was not caught: {e}")

    def test_can_distinguish_exception_types(self) -> None:
        """Different exception types can be distinguished."""
        task = Task(gid="123")

        try:
            raise SessionClosedError()
        except SessionClosedError:
            pass
        except SaveOrchestrationError:
            pytest.fail("SessionClosedError should be caught specifically")

        try:
            raise CyclicDependencyError([task])
        except CyclicDependencyError:
            pass
        except SaveOrchestrationError:
            pytest.fail("CyclicDependencyError should be caught specifically")
