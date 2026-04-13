"""Action method factory for SaveSession.

Per TDD-SPRINT-4-SAVESESSION-DECOMPOSITION/ADR-0122:
Descriptor-based factory pattern to consolidate 18 action methods.

This module reduces ~920 lines of action methods in session.py to ~20 lines
of descriptor declarations, achieving an 83% reduction in action code.

The ActionBuilder descriptor generates method implementations at class
definition time based on configuration in ACTION_REGISTRY.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, overload

from autom8_asana.models.common import NameGid
from autom8_asana.persistence.errors import PositioningConflictError
from autom8_asana.persistence.models import ActionOperation, ActionType
from autom8_asana.persistence.validation import validate_gid

if TYPE_CHECKING:
    from collections.abc import Callable

    from autom8_asana.models.base import AsanaResource
    from autom8_asana.persistence.session import SaveSession


__all__ = [
    "ActionBuilder",
    "ActionVariant",
    "ActionConfig",
    "ACTION_REGISTRY",
]


class ActionVariant(Enum):
    """Categories of action method behavior.

    Per FR-ACTION-002: Three variants with distinct behaviors.

    Variants:
        NO_TARGET: Actions that don't require a target (add_like, remove_like).
        TARGET_REQUIRED: Actions that require a target entity (add_tag, etc.).
        POSITIONING: Actions with optional insert_before/insert_after params.
    """

    NO_TARGET = "no_target"
    TARGET_REQUIRED = "target_required"
    POSITIONING = "positioning"


@dataclass(frozen=True)
class ActionConfig:
    """Configuration for a single action method.

    Defines everything needed to generate the method body.

    Attributes:
        action_type: The ActionType enum value for ActionOperation.
        variant: Behavioral category determining method signature.
        target_param: Parameter name for the target ("tag", "project", etc.).
        validation_field: Field name for validate_gid error messages.
        requires_validation: Whether to call validate_gid on target.
        log_event: Structured log event name.
        docstring: Method docstring for IDE support.
    """

    action_type: ActionType
    variant: ActionVariant
    target_param: str = "target"
    validation_field: str = "target_gid"
    requires_validation: bool = True
    log_event: str = ""
    docstring: str = ""


# Registry of all 18 action method configurations
# Per ADR-0122: Centralized configuration replaces 920 lines of methods
ACTION_REGISTRY: dict[str, ActionConfig] = {
    # Tag operations
    "add_tag": ActionConfig(
        action_type=ActionType.ADD_TAG,
        variant=ActionVariant.TARGET_REQUIRED,
        target_param="tag",
        validation_field="tag_gid",
        log_event="session_add_tag",
        docstring="""Add a tag to a task.

        Per TDD-0011: Register action for tag addition.
        Per ADR-0107: Uses NameGid for target to preserve name.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task to add the tag to.
            tag: Tag object or tag GID string.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.
            ValidationError: If tag_gid is invalid.

        Example:
            session.add_tag(task, tag).add_tag(task, other_tag)
            await session.commit_async()
        """,
    ),
    "remove_tag": ActionConfig(
        action_type=ActionType.REMOVE_TAG,
        variant=ActionVariant.TARGET_REQUIRED,
        target_param="tag",
        validation_field="tag_gid",
        log_event="session_remove_tag",
        docstring="""Remove a tag from a task.

        Per TDD-0011: Register action for tag removal.
        Per ADR-0107: Uses NameGid for target to preserve name.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task to remove the tag from.
            tag: Tag object or tag GID string.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.
            ValidationError: If tag_gid is invalid.

        Example:
            session.remove_tag(task, old_tag)
            await session.commit_async()
        """,
    ),
    # Project operations
    "add_to_project": ActionConfig(
        action_type=ActionType.ADD_TO_PROJECT,
        variant=ActionVariant.POSITIONING,
        target_param="project",
        validation_field="project_gid",
        log_event="session_add_to_project",
        docstring="""Add a task to a project with optional positioning.

        Per TDD-0011: Register action for project addition.
        Per TDD-0012/ADR-0044: Support positioning via insert_before/insert_after.
        Per ADR-0047: Fail-fast validation when both positioning params provided.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task to add to the project.
            project: Project object or project GID string.
            insert_before: GID of task to insert before. Cannot be used with
                          insert_after.
            insert_after: GID of task to insert after. Cannot be used with
                         insert_before.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.
            PositioningConflictError: If both insert_before and insert_after
                                     are specified.
            ValidationError: If project_gid is invalid.

        Example:
            session.add_to_project(task, project)
            session.add_to_project(task, project, insert_after="other_task_gid")
            await session.commit_async()
        """,
    ),
    "remove_from_project": ActionConfig(
        action_type=ActionType.REMOVE_FROM_PROJECT,
        variant=ActionVariant.TARGET_REQUIRED,
        target_param="project",
        validation_field="project_gid",
        log_event="session_remove_from_project",
        docstring="""Remove a task from a project.

        Per TDD-0011: Register action for project removal.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task to remove from the project.
            project: Project object or project GID string.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.
            ValidationError: If project_gid is invalid.

        Example:
            session.remove_from_project(task, old_project)
            await session.commit_async()
        """,
    ),
    # Dependency operations
    "add_dependency": ActionConfig(
        action_type=ActionType.ADD_DEPENDENCY,
        variant=ActionVariant.TARGET_REQUIRED,
        target_param="depends_on",
        validation_field="dependency_gid",
        log_event="session_add_dependency",
        docstring="""Add a dependency to a task.

        Per TDD-0011: Register action for dependency addition.

        The action will be executed at commit time after CRUD operations.
        This makes `task` dependent on `depends_on` (task cannot complete
        until depends_on is complete).

        Args:
            task: The task that will depend on another.
            depends_on: Task object or task GID string that this task depends on.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.
            ValidationError: If dependency_gid is invalid.

        Example:
            session.add_dependency(subtask, parent_task)
            await session.commit_async()
        """,
    ),
    "remove_dependency": ActionConfig(
        action_type=ActionType.REMOVE_DEPENDENCY,
        variant=ActionVariant.TARGET_REQUIRED,
        target_param="depends_on",
        validation_field="dependency_gid",
        log_event="session_remove_dependency",
        docstring="""Remove a dependency from a task.

        Per TDD-0011: Register action for dependency removal.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task to remove the dependency from.
            depends_on: Task object or task GID string to remove as dependency.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.
            ValidationError: If dependency_gid is invalid.

        Example:
            session.remove_dependency(task, old_dependency)
            await session.commit_async()
        """,
    ),
    # Section operations
    "move_to_section": ActionConfig(
        action_type=ActionType.MOVE_TO_SECTION,
        variant=ActionVariant.POSITIONING,
        target_param="section",
        validation_field="section_gid",
        log_event="session_move_to_section",
        docstring="""Move a task to a section with optional positioning.

        Per TDD-0011: Register action for section movement.
        Per TDD-0012/ADR-0044: Support positioning via insert_before/insert_after.
        Per ADR-0047: Fail-fast validation when both positioning params provided.

        The action will be executed at commit time after CRUD operations.
        This moves the task to the specified section within its project.

        Args:
            task: The task to move.
            section: Section object or section GID string.
            insert_before: GID of task to insert before. Cannot be used with
                          insert_after.
            insert_after: GID of task to insert after. Cannot be used with
                         insert_before.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.
            PositioningConflictError: If both insert_before and insert_after
                                     are specified.
            ValidationError: If section_gid is invalid.

        Example:
            session.move_to_section(task, done_section)
            session.move_to_section(task, section, insert_before="other_task_gid")
            await session.commit_async()
        """,
    ),
    # Follower operations (no GID validation per original implementation)
    "add_follower": ActionConfig(
        action_type=ActionType.ADD_FOLLOWER,
        variant=ActionVariant.TARGET_REQUIRED,
        target_param="user",
        validation_field="user_gid",
        requires_validation=False,
        log_event="session_add_follower",
        docstring="""Add a follower to a task.

        Per TDD-0012: Register action for follower addition.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task to add the follower to.
            user: User object, NameGid reference, or user GID string.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.

        Example:
            session.add_follower(task, user)
            session.add_follower(task, "user_gid")
            await session.commit_async()
        """,
    ),
    "remove_follower": ActionConfig(
        action_type=ActionType.REMOVE_FOLLOWER,
        variant=ActionVariant.TARGET_REQUIRED,
        target_param="user",
        validation_field="user_gid",
        requires_validation=False,
        log_event="session_remove_follower",
        docstring="""Remove a follower from a task.

        Per TDD-0012: Register action for follower removal.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task to remove the follower from.
            user: User object, NameGid reference, or user GID string.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.

        Example:
            session.remove_follower(task, user)
            session.remove_follower(task, "user_gid")
            await session.commit_async()
        """,
    ),
    # Dependent operations (no GID validation per original implementation)
    "add_dependent": ActionConfig(
        action_type=ActionType.ADD_DEPENDENT,
        variant=ActionVariant.TARGET_REQUIRED,
        target_param="dependent_task",
        validation_field="dependent_gid",
        requires_validation=False,
        log_event="session_add_dependent",
        docstring="""Add a task as a dependent of another task.

        Per TDD-0012: Register action for dependent addition.

        This is the inverse of add_dependency. When you call add_dependent(A, B),
        task B becomes dependent on task A (B cannot complete until A completes).

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task that will be depended upon (blocking task).
            dependent_task: Task object or task GID string that will depend on
                           this task (blocked task).

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.

        Example:
            # Make task_b dependent on task_a (task_b waits for task_a)
            session.add_dependent(task_a, task_b)
            await session.commit_async()
        """,
    ),
    "remove_dependent": ActionConfig(
        action_type=ActionType.REMOVE_DEPENDENT,
        variant=ActionVariant.TARGET_REQUIRED,
        target_param="dependent_task",
        validation_field="dependent_gid",
        requires_validation=False,
        log_event="session_remove_dependent",
        docstring="""Remove a dependent task relationship.

        Per TDD-0012: Register action for dependent removal.

        Removes the dependent relationship where dependent_task was waiting
        on task to complete.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task that was being depended upon (blocking task).
            dependent_task: Task object or task GID string to remove as dependent.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.

        Example:
            session.remove_dependent(task_a, task_b)
            await session.commit_async()
        """,
    ),
    # Like operations
    "add_like": ActionConfig(
        action_type=ActionType.ADD_LIKE,
        variant=ActionVariant.NO_TARGET,
        log_event="session_add_like",
        docstring="""Like a task using the authenticated user.

        Per TDD-0012/ADR-0045: Register action for task like.

        Adds a "like" to the task from the currently authenticated user.
        No user parameter is needed - the API uses the authenticated user.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task to like.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.

        Example:
            session.add_like(task)
            await session.commit_async()
        """,
    ),
    "remove_like": ActionConfig(
        action_type=ActionType.REMOVE_LIKE,
        variant=ActionVariant.NO_TARGET,
        log_event="session_remove_like",
        docstring="""Remove a like from a task using the authenticated user.

        Per TDD-0012/ADR-0045: Register action for task unlike.

        Removes the "like" from the task for the currently authenticated user.
        No user parameter is needed - the API uses the authenticated user.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task to unlike.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.

        Example:
            session.remove_like(task)
            await session.commit_async()
        """,
    ),
}


class ActionBuilder:
    """Descriptor that generates action method implementations.

    Per ADR-0122: Uses Python descriptor protocol to generate method bodies
    at access time from centralized configuration.

    This pattern reduces 18 explicit action methods (~920 lines) to 13
    descriptor declarations (~20 lines), achieving an 83% reduction.

    The descriptor looks up the action configuration in ACTION_REGISTRY and
    generates an appropriate method based on the ActionVariant:
    - NO_TARGET: Method takes only (task) parameter
    - TARGET_REQUIRED: Method takes (task, target) parameters
    - POSITIONING: Method takes (task, target, *, insert_before, insert_after)

    Usage in SaveSession:
        add_tag = ActionBuilder("add_tag")
        remove_tag = ActionBuilder("remove_tag")
        add_like = ActionBuilder("add_like")
        # ... generates methods from configuration

    Note:
        5 methods with custom logic are kept explicit:
        - add_comment (text validation)
        - set_parent (None handling for promotion)
        - reorder_subtask (parent validation)
        - add_followers (batch delegation)
        - remove_followers (batch delegation)
    """

    __slots__ = ("_action_name", "_config", "_attr_name")

    def __init__(self, action_name: str) -> None:
        """Initialize descriptor with action name.

        Args:
            action_name: Key in ACTION_REGISTRY for this action.

        Raises:
            KeyError: If action_name is not in ACTION_REGISTRY.
        """
        if action_name not in ACTION_REGISTRY:
            raise KeyError(f"Unknown action: {action_name}")
        self._action_name = action_name
        self._config = ACTION_REGISTRY[action_name]
        self._attr_name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        """Called when descriptor is assigned to class attribute.

        Args:
            owner: The class the descriptor is being assigned to.
            name: The attribute name being assigned.
        """
        self._attr_name = name

    @overload
    def __get__(self, obj: None, objtype: type | None = None) -> ActionBuilder: ...

    @overload
    def __get__(
        self, obj: SaveSession, objtype: type | None = None
    ) -> Callable[..., SaveSession]: ...

    def __get__(
        self, obj: SaveSession | None, objtype: type | None = None
    ) -> Callable[..., SaveSession] | ActionBuilder:
        """Return bound method that implements the action.

        When accessed on the class (obj is None), returns the descriptor.
        When accessed on an instance, returns a bound method.

        Args:
            obj: Instance of SaveSession, or None if accessed on class.
            objtype: The class type.

        Returns:
            The descriptor (if obj is None) or a bound method.
        """
        if obj is None:
            return self
        return self._make_method(obj)

    def _make_method(self, session: SaveSession) -> Callable[..., SaveSession]:
        """Generate the action method for this configuration.

        Dispatches to the appropriate method generator based on variant.

        Args:
            session: The SaveSession instance to bind the method to.

        Returns:
            A callable that implements the action method.
        """
        config = self._config

        if config.variant == ActionVariant.NO_TARGET:
            return self._make_no_target_method(session, config)
        elif config.variant == ActionVariant.TARGET_REQUIRED:
            return self._make_target_method(session, config)
        else:  # POSITIONING
            return self._make_positioning_method(session, config)

    def _make_no_target_method(
        self, session: SaveSession, config: ActionConfig
    ) -> Callable[[AsanaResource], SaveSession]:
        """Generate method for NO_TARGET variant (add_like, remove_like).

        Args:
            session: The SaveSession instance.
            config: The action configuration.

        Returns:
            Method that takes (task) and returns SaveSession.
        """

        def method(task: AsanaResource) -> SaveSession:
            with session._require_open():
                action = ActionOperation(
                    task=task,
                    action=config.action_type,
                    target=None,
                )
                session._pending_actions.append(action)

                if session._log:
                    session._log.debug(config.log_event, task_gid=task.gid)

                return session

        method.__doc__ = config.docstring
        method.__name__ = self._attr_name
        return method

    def _make_target_method(
        self, session: SaveSession, config: ActionConfig
    ) -> Callable[[AsanaResource, Any], SaveSession]:
        """Generate method for TARGET_REQUIRED variant.

        Args:
            session: The SaveSession instance.
            config: The action configuration.

        Returns:
            Method that takes (task, target) and returns SaveSession.
        """

        def method(task: AsanaResource, target: Any) -> SaveSession:
            with session._require_open():
                # Per ADR-0107: Build NameGid preserving name when available
                if isinstance(target, str):
                    target_gid = NameGid(gid=target)
                else:
                    target_gid = NameGid(gid=target.gid, name=getattr(target, "name", None))

                # Validate GID if required by config
                if config.requires_validation:
                    validate_gid(target_gid.gid, config.validation_field)

                action = ActionOperation(
                    task=task,
                    action=config.action_type,
                    target=target_gid,
                )
                session._pending_actions.append(action)

                if session._log:
                    session._log.debug(
                        config.log_event,
                        task_gid=task.gid,
                        target_gid=target_gid.gid,
                    )

                return session

        method.__doc__ = config.docstring
        method.__name__ = self._attr_name
        return method

    def _make_positioning_method(
        self, session: SaveSession, config: ActionConfig
    ) -> Callable[..., SaveSession]:
        """Generate method for POSITIONING variant.

        Args:
            session: The SaveSession instance.
            config: The action configuration.

        Returns:
            Method that takes (task, target, *, insert_before, insert_after)
            and returns SaveSession.
        """

        def method(
            task: AsanaResource,
            target: Any,
            *,
            insert_before: str | None = None,
            insert_after: str | None = None,
        ) -> SaveSession:
            with session._require_open():
                # Per ADR-0047: Fail-fast validation
                if insert_before is not None and insert_after is not None:
                    raise PositioningConflictError(insert_before, insert_after)

                # Per ADR-0107: Build NameGid preserving name when available
                if isinstance(target, str):
                    target_gid = NameGid(gid=target)
                else:
                    target_gid = NameGid(gid=target.gid, name=getattr(target, "name", None))

                # Validate GID if required by config
                if config.requires_validation:
                    validate_gid(target_gid.gid, config.validation_field)

                # Build extra_params for positioning
                extra_params: dict[str, str] = {}
                if insert_before is not None:
                    extra_params["insert_before"] = insert_before
                if insert_after is not None:
                    extra_params["insert_after"] = insert_after

                action = ActionOperation(
                    task=task,
                    action=config.action_type,
                    target=target_gid,
                    extra_params=extra_params,
                )
                session._pending_actions.append(action)

                if session._log:
                    session._log.debug(
                        config.log_event,
                        task_gid=task.gid,
                        target_gid=target_gid.gid,
                        insert_before=insert_before,
                        insert_after=insert_after,
                    )

                return session

        method.__doc__ = config.docstring
        method.__name__ = self._attr_name
        return method
