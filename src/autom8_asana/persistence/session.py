"""SaveSession - Unit of Work pattern for batched Asana operations.

Per FR-UOW-001 through FR-UOW-008.
Per ADR-0035: Unit of Work Pattern for Save Orchestration.
Per TDD-0011: Action endpoint support for tag, project, dependency, and section.
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar, TYPE_CHECKING, Coroutine

from autom8_asana.persistence.tracker import ChangeTracker
from autom8_asana.persistence.graph import DependencyGraph
from autom8_asana.persistence.pipeline import SavePipeline
from autom8_asana.persistence.events import EventSystem
from autom8_asana.persistence.action_executor import ActionExecutor
from autom8_asana.persistence.models import (
    EntityState,
    OperationType,
    PlannedOperation,
    SaveResult,
    ActionType,
    ActionOperation,
    ActionResult,
)
from autom8_asana.persistence.exceptions import (
    SessionClosedError,
    PositioningConflictError,
)
from autom8_asana.transport.sync import sync_wrapper

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.base import AsanaResource
    from autom8_asana.models.common import NameGid
    from autom8_asana.models.tag import Tag
    from autom8_asana.models.project import Project
    from autom8_asana.models.section import Section
    from autom8_asana.models.task import Task
    from autom8_asana.models.user import User

T = TypeVar("T", bound="AsanaResource")


class SessionState:
    """Internal state machine for SaveSession.

    States:
        OPEN: Session is active and accepting operations.
        COMMITTED: Session has been committed (can still accept new operations).
        CLOSED: Session has exited context manager, no more operations allowed.
    """

    OPEN = "open"
    COMMITTED = "committed"
    CLOSED = "closed"


class SaveSession:
    """Unit of Work pattern for batched Asana operations.

    Per FR-UOW-001: Async context manager for bulk saves.
    Per FR-UOW-004: Sync wrapper per ADR-0002.

    SaveSession provides a Django-ORM-style deferred save pattern where
    multiple model changes are collected and executed in optimized batches
    rather than immediately persisting each change.

    Features:
    - Explicit entity registration via track()
    - Snapshot-based dirty detection
    - Dependency graph construction for parent-child relationships
    - Automatic placeholder GID resolution for new entities
    - Partial failure handling with commit-and-report semantics
    - Event hooks for pre-save, post-save, and error handling

    Usage (async):
        async with SaveSession(client) as session:
            # Track existing entity
            session.track(task)
            task.name = "Updated Name"

            # Track new entity (with temp GID)
            new_task = Task(gid="temp_1", name="New Task")
            session.track(new_task)

            # Commit all changes
            result = await session.commit_async()

            if result.success:
                print("All saved!")
            else:
                print(f"Partial: {len(result.failed)} failed")

    Usage (sync):
        with SaveSession(client) as session:
            session.track(task)
            task.name = "Updated"
            result = session.commit()

    Usage with hooks:
        async with SaveSession(client) as session:
            @session.on_pre_save
            def validate(entity, op):
                if op == OperationType.CREATE and not entity.name:
                    raise ValueError("Task must have a name")

            @session.on_post_save
            async def notify(entity, op, data):
                await send_notification(entity.gid)

            session.track(task)
            await session.commit_async()
    """

    def __init__(
        self,
        client: AsanaClient,
        batch_size: int = 10,
        max_concurrent: int = 15,
    ) -> None:
        """Initialize save session.

        Per FR-UOW-005: Accept optional configuration.

        Args:
            client: AsanaClient instance for API calls. The client's
                   batch property is used for batch operations.
            batch_size: Maximum operations per batch (default: 10, Asana limit).
            max_concurrent: Maximum concurrent batch requests (default: 15).
                           Reserved for future optimization.
        """
        self._client = client
        self._batch_size = batch_size
        self._max_concurrent = max_concurrent

        self._tracker = ChangeTracker()
        self._graph = DependencyGraph()
        self._events = EventSystem()
        self._pipeline = SavePipeline(
            tracker=self._tracker,
            graph=self._graph,
            events=self._events,
            batch_client=client.batch,
            batch_size=batch_size,
        )

        # TDD-0011: Action executor for non-batch operations
        self._action_executor = ActionExecutor(client._http)

        # TDD-0011: Pending action operations
        self._pending_actions: list[ActionOperation] = []

        self._state = SessionState.OPEN
        self._log = getattr(client, "_log", None)

    # --- Context Manager Protocol ---

    async def __aenter__(self) -> SaveSession:
        """Enter async context (FR-UOW-001)."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context (FR-UOW-001).

        Closes the session. No further operations are allowed.
        Does not auto-commit; uncommitted changes are discarded.
        """
        self._state = SessionState.CLOSED

    def __enter__(self) -> SaveSession:
        """Enter sync context (FR-UOW-004)."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit sync context (FR-UOW-004).

        Closes the session. No further operations are allowed.
        Does not auto-commit; uncommitted changes are discarded.
        """
        self._state = SessionState.CLOSED

    # --- Entity Registration ---

    def track(self, entity: T) -> T:
        """Register entity for change tracking.

        Per FR-UOW-002: Explicit opt-in tracking.
        Per FR-CHANGE-001: Capture snapshot at track time.

        Tracks an entity for changes. A snapshot of the entity's current
        state is captured. After tracking, any modifications to the entity
        will be detected at commit time.

        New entities (with gid starting with "temp_" or without gid) will
        be created via POST. Existing entities will be updated via PUT if
        they have changes.

        Args:
            entity: AsanaResource instance to track. Can be an existing
                   entity from the API or a new entity to be created.

        Returns:
            The same entity (for chaining).

        Raises:
            SessionClosedError: If session is closed.

        Example:
            task = session.track(Task(gid="temp_1", name="New Task"))
            task.notes = "Added notes"  # This change will be detected
        """
        self._ensure_open()
        self._tracker.track(entity)

        if self._log:
            self._log.debug(
                "session_track",
                entity_type=type(entity).__name__,
                entity_gid=entity.gid,
            )

        return entity

    def untrack(self, entity: AsanaResource) -> None:
        """Remove entity from change tracking.

        Per FR-CHANGE-008: Support untracking.

        Removes an entity from the session. Any pending changes to the
        entity will be discarded. Safe to call on entities that are
        not tracked.

        Args:
            entity: Previously tracked entity.

        Raises:
            SessionClosedError: If session is closed.
        """
        self._ensure_open()
        self._tracker.untrack(entity)

        if self._log:
            self._log.debug(
                "session_untrack",
                entity_type=type(entity).__name__,
                entity_gid=entity.gid,
            )

    def delete(self, entity: AsanaResource) -> None:
        """Mark entity for deletion.

        Per FR-CHANGE-004: Mark for DELETE operation.

        Marks an entity for deletion. The entity must have a real GID
        (not a temp GID). At commit time, a DELETE request will be sent.

        Args:
            entity: Entity to delete (must have GID).

        Raises:
            ValueError: If entity has no GID or has a temp GID.
            SessionClosedError: If session is closed.

        Example:
            session.delete(task)  # Will send DELETE request at commit
            result = await session.commit_async()
        """
        self._ensure_open()

        if not entity.gid or entity.gid.startswith("temp_"):
            raise ValueError(
                f"Cannot delete entity without GID: {type(entity).__name__}"
            )

        self._tracker.mark_deleted(entity)

        if self._log:
            self._log.debug(
                "session_delete",
                entity_type=type(entity).__name__,
                entity_gid=entity.gid,
            )

    # --- Change Inspection ---

    def get_changes(
        self,
        entity: AsanaResource,
    ) -> dict[str, tuple[Any, Any]]:
        """Get field-level changes for tracked entity.

        Per FR-CHANGE-002: Compute {field: (old, new)} changes.

        Returns a dict showing what fields have changed since tracking,
        with both old and new values.

        Args:
            entity: Tracked entity.

        Returns:
            Dict of {field_name: (old_value, new_value)} for changed fields.
            Empty dict if entity is not tracked or has no changes.

        Example:
            session.track(task)
            task.name = "New Name"
            changes = session.get_changes(task)
            # {"name": ("Old Name", "New Name")}
        """
        return self._tracker.get_changes(entity)

    def get_state(self, entity: AsanaResource) -> EntityState:
        """Get lifecycle state of tracked entity.

        Per FR-UOW-008: Track entity lifecycle state.

        Returns the current state of an entity: NEW, CLEAN, MODIFIED, or DELETED.
        State is computed dynamically based on snapshot comparison.

        Args:
            entity: Tracked entity.

        Returns:
            Current EntityState.

        Raises:
            ValueError: If entity is not tracked.

        Example:
            session.track(task)
            state = session.get_state(task)  # EntityState.CLEAN
            task.name = "Modified"
            state = session.get_state(task)  # EntityState.MODIFIED
        """
        return self._tracker.get_state(entity)

    def get_dependency_order(self) -> list[list[AsanaResource]]:
        """Get entities grouped by dependency level.

        Per FR-DEPEND-009: Inspect computed order.

        Returns dirty entities grouped by their dependency level.
        Level 0 entities have no dependencies, level 1 depends on level 0, etc.
        Useful for understanding the order of operations before commit.

        Returns:
            List of lists, where index is dependency level.

        Raises:
            CyclicDependencyError: If dependency cycle detected.

        Example:
            session.track(parent_task)
            session.track(subtask)  # subtask.parent = parent_task
            levels = session.get_dependency_order()
            # [[parent_task], [subtask]]
        """
        dirty = self._tracker.get_dirty_entities()
        if not dirty:
            return []
        self._graph.build(dirty)
        return self._graph.get_levels()

    # --- Dry Run ---

    def preview(self) -> tuple[list[PlannedOperation], list[ActionOperation]]:
        """Preview planned operations without executing.

        Per FR-DRY-001: Return PlannedOperation list, no API calls.
        Per FR-DRY-003: Include dependency order.
        Per FR-DRY-004: Validate (cycle detection).
        Per FR-DRY-005: Do not modify session state.
        Per FR-PREV-001: Include queued action operations.
        Per FR-PREV-002: Actions listed after CRUD operations.
        Per FR-PREV-003: Validate unsupported direct modifications.

        Returns a tuple of (CRUD operations, action operations) that would
        be executed at commit time. CRUD operations are in dependency order.
        No API calls are made. Useful for debugging or user confirmation.

        Returns:
            Tuple of (crud_operations, action_operations).

        Raises:
            CyclicDependencyError: If dependency cycle detected.
            UnsupportedOperationError: If unsupported direct modifications detected.

        Example:
            crud_ops, action_ops = session.preview()
            for op in crud_ops:
                print(f"{op.operation.value} {op.entity.gid} at level {op.dependency_level}")
            for action in action_ops:
                print(f"{action.action.value} on {action.task.gid}")
        """
        dirty = self._tracker.get_dirty_entities()

        # FR-PREV-003: Validate before returning preview
        if dirty:
            self._pipeline.validate_no_unsupported_modifications(dirty)

        # FR-PREV-001: Include both CRUD and action operations
        crud_ops = self._pipeline.preview(dirty)

        # FR-PREV-002: Actions come after CRUD (returned as separate list)
        return (crud_ops, list(self._pending_actions))

    # --- Commit ---

    async def commit_async(self) -> SaveResult:
        """Execute all pending changes (async).

        Per FR-UOW-003: Execute pending changes.
        Per FR-UOW-007: Support multiple commits within session.
        Per FR-CHANGE-009: Reset entity state after successful save.
        Per TDD-0011: Execute action operations after CRUD operations.

        Commits all tracked entities with pending changes. Entities are
        saved in dependency order. Then action operations (add_tag, etc.)
        are executed. Partial failures are reported but don't roll back
        successful operations.

        After commit, successfully saved entities are marked clean and
        have their GIDs updated (for new entities). Pending actions are
        cleared regardless of success.

        Returns:
            SaveResult with succeeded/failed lists. Action failures are
            included in the failed list with SaveError.

        Raises:
            SessionClosedError: If session is closed.
            CyclicDependencyError: If dependency cycle detected.
            UnsupportedOperationError: If entities have unsupported direct modifications.

        Example:
            result = await session.commit_async()
            if result.success:
                print("All operations succeeded")
            elif result.partial:
                print(f"{len(result.succeeded)} succeeded, {len(result.failed)} failed")
            else:
                print("All operations failed")
        """
        self._ensure_open()

        dirty_entities = self._tracker.get_dirty_entities()
        pending_actions = list(self._pending_actions)

        if not dirty_entities and not pending_actions:
            if self._log:
                self._log.warning(
                    "commit_empty_session",
                    message="No tracked entities or pending actions to commit. "
                            "Did you forget to call track() on your entities?",
                )
            return SaveResult()

        if self._log:
            self._log.info(
                "session_commit_start",
                entity_count=len(dirty_entities),
                action_count=len(pending_actions),
            )

        # Execute CRUD operations and actions together
        crud_result, action_results = await self._pipeline.execute_with_actions(
            entities=dirty_entities,
            actions=pending_actions,
            action_executor=self._action_executor,
        )

        # Clear pending actions after commit (regardless of success)
        self._pending_actions.clear()

        # Reset state for successful entities (FR-CHANGE-009)
        for entity in crud_result.succeeded:
            self._tracker.mark_clean(entity)

        self._state = SessionState.COMMITTED

        # Count action failures for logging
        action_failures = sum(1 for r in action_results if not r.success)

        if self._log:
            self._log.info(
                "session_commit_complete",
                succeeded=len(crud_result.succeeded),
                failed=len(crud_result.failed),
                action_succeeded=len(action_results) - action_failures,
                action_failed=action_failures,
            )

        return crud_result

    def commit(self) -> SaveResult:
        """Execute all pending changes (sync wrapper).

        Per FR-UOW-004: Sync wrapper per ADR-0002.

        Synchronous version of commit_async(). Uses asyncio.run()
        internally. Cannot be called from an async context.

        Returns:
            SaveResult with succeeded/failed lists.

        Raises:
            SessionClosedError: If session is closed.
            CyclicDependencyError: If dependency cycle detected.
            SyncInAsyncContextError: If called from an async context.
        """
        return self._commit_sync()

    @sync_wrapper("commit_async")
    async def _commit_sync(self) -> SaveResult:
        """Internal sync wrapper implementation."""
        return await self.commit_async()

    # --- Event Hooks ---

    def on_pre_save(
        self,
        func: (
            Callable[[AsanaResource, OperationType], None]
            | Callable[[AsanaResource, OperationType], Coroutine[Any, Any, None]]
        ),
    ) -> Callable[..., Any]:
        """Register pre-save hook (decorator).

        Per FR-EVENT-001: Hook called before each entity save.
        Per FR-EVENT-005: Support both function and coroutine hooks.

        Pre-save hooks are called before each entity is saved. They can
        raise exceptions to abort the save for that entity.

        Args:
            func: Hook function receiving (entity, operation_type).
                  Can be sync or async.

        Returns:
            The decorated function.

        Example:
            @session.on_pre_save
            def validate(entity: AsanaResource, op: OperationType) -> None:
                if op == OperationType.CREATE and not entity.name:
                    raise ValueError("Name required")
        """
        return self._events.register_pre_save(func)

    def on_post_save(
        self,
        func: (
            Callable[[AsanaResource, OperationType, Any], None]
            | Callable[[AsanaResource, OperationType, Any], Coroutine[Any, Any, None]]
        ),
    ) -> Callable[..., Any]:
        """Register post-save hook (decorator).

        Per FR-EVENT-002: Hook called after successful entity save.

        Post-save hooks are called after each entity is successfully saved.
        They cannot abort the operation (save already happened). Exceptions
        are swallowed.

        Args:
            func: Hook function receiving (entity, operation_type, response_data).
                  Can be sync or async.

        Returns:
            The decorated function.

        Example:
            @session.on_post_save
            async def notify(entity: AsanaResource, op: OperationType, data: Any) -> None:
                await send_webhook(entity.gid, data)
        """
        return self._events.register_post_save(func)

    def on_error(
        self,
        func: (
            Callable[[AsanaResource, OperationType, Exception], None]
            | Callable[[AsanaResource, OperationType, Exception], Coroutine[Any, Any, None]]
        ),
    ) -> Callable[..., Any]:
        """Register error hook (decorator).

        Per FR-EVENT-003: Hook called when entity save fails.

        Error hooks are called when an entity save fails. They are for
        logging/notification purposes. Exceptions are swallowed.

        Args:
            func: Hook function receiving (entity, operation_type, exception).
                  Can be sync or async.

        Returns:
            The decorated function.

        Example:
            @session.on_error
            def log_error(entity: AsanaResource, op: OperationType, err: Exception) -> None:
                logger.error(f"Failed to {op.value} {entity.gid}: {err}")
        """
        return self._events.register_error(func)

    # --- TDD-0011: Action Operations ---

    def add_tag(self, task: AsanaResource, tag: AsanaResource | str) -> SaveSession:
        """Add a tag to a task.

        Per TDD-0011: Register action for tag addition.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task to add the tag to.
            tag: Tag object or tag GID string.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.

        Example:
            session.add_tag(task, tag).add_tag(task, other_tag)
            await session.commit_async()
        """
        self._ensure_open()
        tag_gid = tag if isinstance(tag, str) else tag.gid

        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target_gid=tag_gid,
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_add_tag",
                task_gid=task.gid,
                tag_gid=tag_gid,
            )

        return self

    def remove_tag(self, task: AsanaResource, tag: AsanaResource | str) -> SaveSession:
        """Remove a tag from a task.

        Per TDD-0011: Register action for tag removal.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task to remove the tag from.
            tag: Tag object or tag GID string.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.

        Example:
            session.remove_tag(task, old_tag)
            await session.commit_async()
        """
        self._ensure_open()
        tag_gid = tag if isinstance(tag, str) else tag.gid

        action = ActionOperation(
            task=task,
            action=ActionType.REMOVE_TAG,
            target_gid=tag_gid,
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_remove_tag",
                task_gid=task.gid,
                tag_gid=tag_gid,
            )

        return self

    def add_to_project(
        self,
        task: AsanaResource,
        project: AsanaResource | str,
        *,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> SaveSession:
        """Add a task to a project with optional positioning.

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

        Example:
            session.add_to_project(task, project)
            session.add_to_project(task, project, insert_after="other_task_gid")
            await session.commit_async()
        """
        self._ensure_open()

        # Per ADR-0047: Fail-fast validation
        if insert_before is not None and insert_after is not None:
            raise PositioningConflictError(insert_before, insert_after)

        project_gid = project if isinstance(project, str) else project.gid

        # Build extra_params for positioning
        extra_params: dict[str, str] = {}
        if insert_before is not None:
            extra_params["insert_before"] = insert_before
        if insert_after is not None:
            extra_params["insert_after"] = insert_after

        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TO_PROJECT,
            target_gid=project_gid,
            extra_params=extra_params,
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_add_to_project",
                task_gid=task.gid,
                project_gid=project_gid,
                insert_before=insert_before,
                insert_after=insert_after,
            )

        return self

    def remove_from_project(
        self, task: AsanaResource, project: AsanaResource | str
    ) -> SaveSession:
        """Remove a task from a project.

        Per TDD-0011: Register action for project removal.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task to remove from the project.
            project: Project object or project GID string.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.

        Example:
            session.remove_from_project(task, old_project)
            await session.commit_async()
        """
        self._ensure_open()
        project_gid = project if isinstance(project, str) else project.gid

        action = ActionOperation(
            task=task,
            action=ActionType.REMOVE_FROM_PROJECT,
            target_gid=project_gid,
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_remove_from_project",
                task_gid=task.gid,
                project_gid=project_gid,
            )

        return self

    def add_dependency(
        self, task: AsanaResource, depends_on: AsanaResource | str
    ) -> SaveSession:
        """Add a dependency to a task.

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

        Example:
            session.add_dependency(subtask, parent_task)
            await session.commit_async()
        """
        self._ensure_open()
        depends_on_gid = depends_on if isinstance(depends_on, str) else depends_on.gid

        action = ActionOperation(
            task=task,
            action=ActionType.ADD_DEPENDENCY,
            target_gid=depends_on_gid,
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_add_dependency",
                task_gid=task.gid,
                depends_on_gid=depends_on_gid,
            )

        return self

    def remove_dependency(
        self, task: AsanaResource, depends_on: AsanaResource | str
    ) -> SaveSession:
        """Remove a dependency from a task.

        Per TDD-0011: Register action for dependency removal.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task to remove the dependency from.
            depends_on: Task object or task GID string to remove as dependency.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.

        Example:
            session.remove_dependency(task, old_dependency)
            await session.commit_async()
        """
        self._ensure_open()
        depends_on_gid = depends_on if isinstance(depends_on, str) else depends_on.gid

        action = ActionOperation(
            task=task,
            action=ActionType.REMOVE_DEPENDENCY,
            target_gid=depends_on_gid,
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_remove_dependency",
                task_gid=task.gid,
                depends_on_gid=depends_on_gid,
            )

        return self

    def move_to_section(
        self,
        task: AsanaResource,
        section: AsanaResource | str,
        *,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> SaveSession:
        """Move a task to a section with optional positioning.

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

        Example:
            session.move_to_section(task, done_section)
            session.move_to_section(task, section, insert_before="other_task_gid")
            await session.commit_async()
        """
        self._ensure_open()

        # Per ADR-0047: Fail-fast validation
        if insert_before is not None and insert_after is not None:
            raise PositioningConflictError(insert_before, insert_after)

        section_gid = section if isinstance(section, str) else section.gid

        # Build extra_params for positioning
        extra_params: dict[str, str] = {}
        if insert_before is not None:
            extra_params["insert_before"] = insert_before
        if insert_after is not None:
            extra_params["insert_after"] = insert_after

        action = ActionOperation(
            task=task,
            action=ActionType.MOVE_TO_SECTION,
            target_gid=section_gid,
            extra_params=extra_params,
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_move_to_section",
                task_gid=task.gid,
                section_gid=section_gid,
                insert_before=insert_before,
                insert_after=insert_after,
            )

        return self

    def add_follower(
        self,
        task: AsanaResource,
        user: User | NameGid | str,
    ) -> SaveSession:
        """Add a follower to a task.

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
        """
        self._ensure_open()
        user_gid = user if isinstance(user, str) else user.gid

        action = ActionOperation(
            task=task,
            action=ActionType.ADD_FOLLOWER,
            target_gid=user_gid,
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_add_follower",
                task_gid=task.gid,
                user_gid=user_gid,
            )

        return self

    def remove_follower(
        self,
        task: AsanaResource,
        user: User | NameGid | str,
    ) -> SaveSession:
        """Remove a follower from a task.

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
        """
        self._ensure_open()
        user_gid = user if isinstance(user, str) else user.gid

        action = ActionOperation(
            task=task,
            action=ActionType.REMOVE_FOLLOWER,
            target_gid=user_gid,
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_remove_follower",
                task_gid=task.gid,
                user_gid=user_gid,
            )

        return self

    def add_followers(
        self,
        task: AsanaResource,
        users: list[User | NameGid | str],
    ) -> SaveSession:
        """Add multiple followers to a task.

        Per TDD-0012: Batch follower addition via repeated add_follower calls.

        The actions will be executed at commit time after CRUD operations.
        Each user is added via a separate API call internally.

        Args:
            task: The task to add the followers to.
            users: List of User objects, NameGid references, or user GID strings.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.

        Example:
            session.add_followers(task, [user1, user2, "user3_gid"])
            await session.commit_async()
        """
        for user in users:
            self.add_follower(task, user)
        return self

    def remove_followers(
        self,
        task: AsanaResource,
        users: list[User | NameGid | str],
    ) -> SaveSession:
        """Remove multiple followers from a task.

        Per TDD-0012: Batch follower removal via repeated remove_follower calls.

        The actions will be executed at commit time after CRUD operations.
        Each user is removed via a separate API call internally.

        Args:
            task: The task to remove the followers from.
            users: List of User objects, NameGid references, or user GID strings.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.

        Example:
            session.remove_followers(task, [user1, user2, "user3_gid"])
            await session.commit_async()
        """
        for user in users:
            self.remove_follower(task, user)
        return self

    # --- TDD-0012 Phase 2: Dependents, Likes, and Comments ---

    def add_dependent(
        self,
        task: AsanaResource,
        dependent_task: AsanaResource | str,
    ) -> SaveSession:
        """Add a task as a dependent of another task.

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
        """
        self._ensure_open()
        dependent_gid = (
            dependent_task if isinstance(dependent_task, str) else dependent_task.gid
        )

        action = ActionOperation(
            task=task,
            action=ActionType.ADD_DEPENDENT,
            target_gid=dependent_gid,
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_add_dependent",
                task_gid=task.gid,
                dependent_gid=dependent_gid,
            )

        return self

    def remove_dependent(
        self,
        task: AsanaResource,
        dependent_task: AsanaResource | str,
    ) -> SaveSession:
        """Remove a dependent task relationship.

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
        """
        self._ensure_open()
        dependent_gid = (
            dependent_task if isinstance(dependent_task, str) else dependent_task.gid
        )

        action = ActionOperation(
            task=task,
            action=ActionType.REMOVE_DEPENDENT,
            target_gid=dependent_gid,
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_remove_dependent",
                task_gid=task.gid,
                dependent_gid=dependent_gid,
            )

        return self

    def add_like(self, task: AsanaResource) -> SaveSession:
        """Like a task using the authenticated user.

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
        """
        self._ensure_open()

        action = ActionOperation(
            task=task,
            action=ActionType.ADD_LIKE,
            target_gid=None,  # Per ADR-0045: No target_gid for likes
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_add_like",
                task_gid=task.gid,
            )

        return self

    def remove_like(self, task: AsanaResource) -> SaveSession:
        """Remove a like from a task using the authenticated user.

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
        """
        self._ensure_open()

        action = ActionOperation(
            task=task,
            action=ActionType.REMOVE_LIKE,
            target_gid=None,  # Per ADR-0045: No target_gid for likes
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_remove_like",
                task_gid=task.gid,
            )

        return self

    def add_comment(
        self,
        task: AsanaResource,
        text: str,
        *,
        html_text: str | None = None,
    ) -> SaveSession:
        """Add a comment (story) to a task.

        Per TDD-0012/ADR-0046: Register action for comment addition.

        Adds a comment to the task's story feed. You can provide plain text,
        HTML text, or both. At least one must be non-empty.

        The action will be executed at commit time after CRUD operations.

        Args:
            task: The task to add the comment to.
            text: Plain text content of the comment.
            html_text: Optional HTML-formatted text for rich content.
                      If provided, this will be shown instead of plain text
                      in the Asana UI.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.
            ValueError: If both text and html_text are empty.

        Example:
            # Plain text comment
            session.add_comment(task, "This looks good!")

            # Rich HTML comment
            session.add_comment(
                task,
                "Status update",
                html_text="<body>Status: <strong>Complete</strong></body>"
            )

            await session.commit_async()
        """
        self._ensure_open()

        # Validate that at least one text field is provided
        if not text and not html_text:
            raise ValueError(
                "add_comment requires either text or html_text to be non-empty"
            )

        # Per ADR-0046: Store text in extra_params
        extra_params: dict[str, str] = {"text": text}
        if html_text:
            extra_params["html_text"] = html_text

        action = ActionOperation(
            task=task,
            action=ActionType.ADD_COMMENT,
            target_gid=None,  # Comments don't need a target_gid
            extra_params=extra_params,
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_add_comment",
                task_gid=task.gid,
                text_length=len(text),
                has_html=html_text is not None,
            )

        return self

    # -------------------------------------------------------------------------
    # Parent Operations (PRD-0008 / TDD-0013)
    # -------------------------------------------------------------------------

    def set_parent(
        self,
        task: AsanaResource,
        parent: AsanaResource | str | None,
        *,
        insert_before: AsanaResource | str | None = None,
        insert_after: AsanaResource | str | None = None,
    ) -> SaveSession:
        """Set or change the parent of a task.

        Per TDD-0013: Register action for parent/subtask operations.

        This method handles multiple use cases:
        - Convert task to subtask: `set_parent(task, parent_task)`
        - Promote subtask to top-level: `set_parent(task, None)`
        - Move subtask to different parent: `set_parent(task, new_parent)`
        - Reorder subtask: `set_parent(task, same_parent, insert_after=sibling)`

        Args:
            task: The task to reparent.
            parent: New parent task, GID string, or None to promote to top-level.
            insert_before: Position before this sibling (mutually exclusive with
                          insert_after).
            insert_after: Position after this sibling (mutually exclusive with
                         insert_before).

        Returns:
            Self for fluent chaining.

        Raises:
            PositioningConflictError: If both insert_before and insert_after specified.
            SessionClosedError: If session is closed.

        Example:
            # Convert task to subtask
            session.set_parent(task, parent_task)

            # Promote subtask to top-level
            session.set_parent(subtask, None)

            # Reorder subtask
            session.set_parent(subtask, subtask.parent, insert_after=other_subtask)
        """
        self._ensure_open()

        # Per ADR-0047: Fail-fast validation for positioning conflict
        if insert_before is not None and insert_after is not None:
            before_gid = (
                insert_before if isinstance(insert_before, str) else insert_before.gid
            )
            after_gid = (
                insert_after if isinstance(insert_after, str) else insert_after.gid
            )
            raise PositioningConflictError(before_gid, after_gid)

        # Resolve parent GID (None means promote to top-level)
        parent_gid: str | None = None
        if parent is not None:
            parent_gid = parent if isinstance(parent, str) else parent.gid

        # Build extra_params (per ADR-0044)
        extra_params: dict[str, Any] = {"parent": parent_gid}
        if insert_before is not None:
            extra_params["insert_before"] = (
                insert_before if isinstance(insert_before, str) else insert_before.gid
            )
        if insert_after is not None:
            extra_params["insert_after"] = (
                insert_after if isinstance(insert_after, str) else insert_after.gid
            )

        action = ActionOperation(
            task=task,
            action=ActionType.SET_PARENT,
            target_gid=None,  # Per ADR-0045: Not used for SET_PARENT
            extra_params=extra_params,
        )
        self._pending_actions.append(action)

        if self._log:
            self._log.debug(
                "session_set_parent",
                task_gid=task.gid,
                parent_gid=parent_gid,
                insert_before=extra_params.get("insert_before"),
                insert_after=extra_params.get("insert_after"),
            )

        return self

    def reorder_subtask(
        self,
        task: AsanaResource,
        *,
        insert_before: AsanaResource | str | None = None,
        insert_after: AsanaResource | str | None = None,
    ) -> SaveSession:
        """Reorder a subtask within its current parent.

        Per TDD-0013: Convenience method for reordering subtasks.

        Convenience method that calls set_parent() with the task's current parent.
        Task must be a subtask (have a parent attribute set).

        Args:
            task: The subtask to reorder (must have task.parent set).
            insert_before: Position before this sibling.
            insert_after: Position after this sibling.

        Returns:
            Self for fluent chaining.

        Raises:
            ValueError: If task has no parent (is not a subtask).
            PositioningConflictError: If both insert_before and insert_after specified.
            SessionClosedError: If session is closed.

        Example:
            # Move subtask after another subtask
            session.reorder_subtask(subtask1, insert_after=subtask2)

            # Move subtask to first position
            session.reorder_subtask(subtask1, insert_before=first_subtask)
        """
        # Per FR-PAR-007: Task must have a parent to be reordered
        if not hasattr(task, "parent") or task.parent is None:
            raise ValueError(
                f"Task {task.gid} has no parent. "
                "reorder_subtask() only works on subtasks."
            )

        return self.set_parent(
            task,
            task.parent,
            insert_before=insert_before,
            insert_after=insert_after,
        )

    def get_pending_actions(self) -> list[ActionOperation]:
        """Get list of pending action operations.

        Per TDD-0011: Allow inspection of pending actions before commit.

        Returns:
            Copy of the pending actions list.

        Example:
            session.add_tag(task, tag)
            actions = session.get_pending_actions()
            # [ActionOperation(add_tag, task, tag)]
        """
        return list(self._pending_actions)

    # --- Internal ---

    def _ensure_open(self) -> None:
        """Ensure session is still open for operations.

        Raises:
            SessionClosedError: If session has been closed.
        """
        if self._state == SessionState.CLOSED:
            raise SessionClosedError()
