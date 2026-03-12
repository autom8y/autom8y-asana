"""SaveSession - Unit of Work pattern for batched Asana operations.

Per FR-UOW-001 through FR-UOW-008.
Per ADR-0035: Unit of Work Pattern for Save Orchestration.
Per TDD-0011: Action endpoint support for tag, project, dependency, and section.
Per TDD-TRIAGE-FIXES: Cascade execution integration.
Per TDD-DEBT-003: Thread-safe state transitions via RLock.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, TypeVar

from autom8_asana.clients.name_resolver import NameResolver
from autom8_asana.persistence.action_executor import ActionExecutor
from autom8_asana.persistence.actions import ActionBuilder
from autom8_asana.persistence.cache_invalidator import CacheInvalidator
from autom8_asana.persistence.events import EventSystem
from autom8_asana.persistence.exceptions import (
    PositioningConflictError,
    SessionClosedError,
)
from autom8_asana.persistence.graph import DependencyGraph
from autom8_asana.persistence.healing import HealingManager
from autom8_asana.persistence.models import (
    ActionOperation,
    ActionResult,
    ActionType,
    EntityState,
    HealingReport,
    OperationType,
    PlannedOperation,
    SaveResult,
)
from autom8_asana.persistence.pipeline import SavePipeline
from autom8_asana.persistence.tracker import ChangeTracker
from autom8_asana.transport.sync import sync_wrapper

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Generator

    from autom8_asana.client import AsanaClient
    from autom8_asana.models.base import AsanaResource
    from autom8_asana.models.common import NameGid
    from autom8_asana.models.user import User
    from autom8_asana.persistence.cascade import CascadeResult
    from autom8_asana.persistence.reorder import ReorderPlan


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
    Per TDD-DEBT-003: Thread-safe state transitions via RLock.

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

    Thread Safety:
        SaveSession is thread-safe. Multiple threads may call track(),
        commit_async(), and other methods concurrently on the same
        instance. However, for optimal performance, prefer one session
        per thread/task.

        Entities tracked during an active commit will be included in
        the next commit, not the current one (per ADR-DEBT-003-002).

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
        auto_heal: bool = False,
        automation_enabled: bool | None = None,
        auto_create_holders: bool = True,
    ) -> None:
        """Initialize save session.

        Per FR-UOW-005: Accept optional configuration.
        Per TDD-DETECTION/ADR-0095: auto_heal enables self-healing.
        Per TDD-AUTOMATION-LAYER: automation_enabled controls Phase 5 execution.
        Per TDD-GAP-01/FR-006: auto_create_holders controls ENSURE_HOLDERS phase.

        Args:
            client: AsanaClient instance for API calls. The client's
                   batch property is used for batch operations.
            batch_size: Maximum operations per batch (default: 10, Asana limit).
            max_concurrent: Maximum concurrent batch requests (default: 15).
                           Reserved for future optimization.
            auto_heal: If True, entities detected via fallback tiers (2-5)
                      will be added to their expected project during commit.
                      Default: False (disabled).
            automation_enabled: Override for automation execution during commit.
                              If None, uses client._config.automation.enabled.
                              If True/False, overrides client config for this session.
            auto_create_holders: If True (default), automatically detect and create
                                missing holder subtasks during commit when children
                                are tracked beneath a parent with HOLDER_KEY_MAP.
                                If False, ENSURE_HOLDERS phase is skipped entirely
                                and behavior matches pre-GAP-01 (unpopulated holders
                                are silently skipped). Per PRD-GAP-01 OQ-1.
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

        # TDD-0011/TDD-GAP-05: Action executor with batch support
        self._action_executor = ActionExecutor(client._http, client.batch)

        # TDD-0011: Pending action operations
        self._pending_actions: list[ActionOperation] = []

        # TDD-TRIAGE-FIXES: Cascade executor for field propagation
        from autom8_asana.persistence.cascade import CascadeExecutor, CascadeOperation

        self._cascade_executor = CascadeExecutor(client)

        # TDD-TRIAGE-FIXES: Initialize cascade operations list in __init__ (not lazily)
        self._cascade_operations: list[CascadeOperation] = []

        # P3: Name resolver with per-session caching (ADR-0060)
        self._name_cache: dict[str, str] = {}
        self._name_resolver = NameResolver(client, self._name_cache)

        # TDD-DETECTION/ADR-0095, TDD-TECH-DEBT-REMEDIATION: Self-healing via HealingManager
        self._healing_manager = HealingManager(auto_heal=auto_heal)

        # TDD-AUTOMATION-LAYER: Automation configuration
        # Resolve automation_enabled: explicit override > client config
        if automation_enabled is not None:
            self._automation_enabled: bool = automation_enabled
        else:
            # Use client config if available
            client_config = getattr(client, "_config", None)
            automation_config = getattr(client_config, "automation", None)
            if automation_config is not None:
                self._automation_enabled = bool(automation_config.enabled)
            else:
                self._automation_enabled = False

        # TDD-DEBT-003: Reentrant lock for thread-safe state operations
        self._lock = threading.RLock()
        self._state = SessionState.OPEN
        self._log = getattr(client, "_log", None)

        # ADR-0059: Cache invalidation coordinator (extracted for SRP)
        # Per TDD-CACHE-INVALIDATION-001: Wire DataFrameCache for project-level invalidation
        cache_provider = getattr(client, "_cache_provider", None)
        if cache_provider:
            from autom8_asana.cache.dataframe.factory import get_dataframe_cache

            self._cache_invalidator: CacheInvalidator | None = CacheInvalidator(
                cache_provider,
                self._log,
                dataframe_cache=get_dataframe_cache(),
            )
        else:
            self._cache_invalidator = None

        # TDD-GAP-01: Holder auto-creation configuration
        self._auto_create_holders = auto_create_holders
        if auto_create_holders:
            from autom8_asana.persistence.holder_concurrency import (
                HolderConcurrencyManager,
            )

            self._holder_concurrency: HolderConcurrencyManager | None = (
                HolderConcurrencyManager()
            )
        else:
            self._holder_concurrency = None

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

        Per TDD-DEBT-003: State transition is atomic.
        """
        with self._state_lock():
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

        Per TDD-DEBT-003: State transition is atomic.
        """
        with self._state_lock():
            self._state = SessionState.CLOSED

    # --- Inspection Properties (TDD-SPRINT-4/FR-INSP-001 through FR-INSP-005) ---

    @property
    def state(self) -> str:
        """Current session state for inspection.

        Per FR-INSP-001: Public access to session state.
        Per TDD-DEBT-003: Read under lock for memory visibility.

        Returns:
            One of SessionState.OPEN, COMMITTED, or CLOSED.
        """
        with self._state_lock():
            return self._state

    @property
    def pending_actions(self) -> list[ActionOperation]:
        """Copy of pending action operations for inspection.

        Per FR-INSP-002: Public access to pending actions.

        Returns:
            Copy of the pending actions list.
        """
        return list(self._pending_actions)

    @property
    def healing_queue(self) -> list[tuple[AsanaResource, str]]:
        """Copy of the healing queue for inspection.

        Per FR-INSP-003: Public access to healing queue.

        Returns:
            List of (entity, expected_project_gid) tuples.
        """
        return self._healing_manager.queue

    @property
    def auto_heal(self) -> bool:
        """Whether auto-healing is enabled for this session.

        Per FR-INSP-004: Public access to auto_heal configuration.

        Returns:
            True if auto_heal was passed as True to __init__.
        """
        return self._healing_manager.auto_heal

    @property
    def automation_enabled(self) -> bool:
        """Whether automation is enabled for this session.

        Per FR-INSP-005: Public access to automation configuration.

        Returns:
            True if automation will run during commit.
        """
        return self._automation_enabled

    @property
    def auto_create_holders(self) -> bool:
        """Whether holder auto-creation is enabled for this session.

        Per TDD-GAP-01 Section 8.3: Read-only property for inspection.

        Returns:
            True if ENSURE_HOLDERS phase will run during commit.
        """
        return self._auto_create_holders

    # --- Name Resolution ---

    @property
    def name_resolver(self) -> NameResolver:
        """Get name resolver for this session (cached per-session).

        Per ADR-0060: Name resolution with per-SaveSession caching.

        Returns:
            NameResolver instance with session-scoped cache.

        Example:
            >>> async with SaveSession(client) as session:
            >>>     tag_gid = await session.name_resolver.resolve_tag_async("Urgent")
        """
        return self._name_resolver

    # --- Entity Registration ---

    def track(
        self,
        entity: T,
        *,
        prefetch_holders: bool = False,
        recursive: bool = False,
        heal: bool | None = None,
    ) -> T:
        """Register entity for change tracking.

        Per FR-UOW-002: Explicit opt-in tracking.
        Per FR-CHANGE-001: Capture snapshot at track time.
        Per ADR-0050: Support prefetch_holders for BusinessEntity types.
        Per ADR-0053: Support recursive tracking of hierarchies.
        Per ADR-0078: GID-based deduplication returns existing entity if same GID.
        Per TDD-DETECTION/ADR-0095: Support heal parameter for self-healing.

        Tracks an entity for changes. A snapshot of the entity's current
        state is captured. After tracking, any modifications to the entity
        will be detected at commit time.

        New entities (with gid starting with "temp_" or without gid) will
        be created via POST. Existing entities will be updated via PUT if
        they have changes.

        If an entity with the same GID is already tracked, the reference is
        updated but the original snapshot is preserved, enabling change
        detection across re-fetches.

        Args:
            entity: AsanaResource instance to track. Can be an existing
                   entity from the API or a new entity to be created.
            prefetch_holders: If True and entity has HOLDER_KEY_MAP,
                            queue holder subtasks for prefetch at commit time.
                            (Note: Actual prefetch requires async client operation)
            recursive: If True, recursively track all descendants in holders.
            heal: Override auto_heal for this entity. None uses session default,
                 True forces healing, False skips healing.

        Returns:
            The tracked entity (may be updated reference if same GID).

        Raises:
            SessionClosedError: If session is closed.

        Example:
            # Simple tracking
            task = session.track(Task(gid="temp_1", name="New Task"))
            task.notes = "Added notes"  # This change will be detected

            # Track with recursive for full hierarchy
            session.track(business, recursive=True)
            # All contacts, units, offers, processes now tracked

            # Track with explicit healing override
            session.track(entity, heal=True)  # Force healing even if auto_heal=False
        """
        # TDD-DEBT-003: Full operation under lock
        with self._require_open():
            tracked = self._tracker.track(entity)

            if self._log:
                self._log.debug(
                    "session_track",
                    entity_type=type(entity).__name__,
                    entity_gid=entity.gid,
                    prefetch_holders=prefetch_holders,
                    recursive=recursive,
                    heal=heal,
                )

            # TDD-DETECTION/ADR-0095, TDD-TECH-DEBT-REMEDIATION: Healing via HealingManager
            if heal is not None and entity.gid:
                self._healing_manager.set_entity_heal_flag(entity.gid, heal)

            # Queue healing if needed (via HealingManager)
            if self._healing_manager.should_heal(entity, heal):
                self._healing_manager.enqueue(entity)
                if self._log:
                    detection = getattr(entity, "_detection_result", None)
                    self._log.debug(
                        "session_queue_healing",
                        entity_type=type(entity).__name__,
                        entity_gid=entity.gid,
                        expected_project_gid=detection.expected_project_gid
                        if detection
                        else None,
                        tier_used=detection.tier_used if detection else None,
                    )

            # Recursive tracking of descendants
            if recursive:
                self._track_recursive(entity)

            return tracked

    def _track_recursive(self, entity: AsanaResource) -> None:
        """Recursively track all children in entity's holders.

        Per ADR-0053: Optional recursive=True for composite SaveSession.

        Args:
            entity: Entity that may have HOLDER_KEY_MAP with holders.
        """
        # Track holders if entity has HOLDER_KEY_MAP (Business, Unit, etc.)
        holder_key_map = getattr(entity, "HOLDER_KEY_MAP", None)
        if holder_key_map:
            for holder_name in holder_key_map:
                holder = getattr(entity, f"_{holder_name}", None)
                if holder is not None:
                    self._tracker.track(holder)
                    self._track_recursive(holder)

        # Track direct children based on holder type patterns
        # Check for known child collection patterns
        for child_attr in ("_contacts", "_units", "_offers", "_processes"):
            children = getattr(entity, child_attr, None)
            if children and isinstance(children, list):
                for child in children:
                    self._tracker.track(child)
                    self._track_recursive(child)

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
        # TDD-DEBT-003: Full operation under lock
        with self._require_open():
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
        # TDD-DEBT-003: Full operation under lock
        with self._require_open():
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

    def find_by_gid(self, gid: str) -> AsanaResource | None:
        """Look up entity by GID.

        Per FR-EL-001: New capability enabled by GID-based tracking.
        Per ADR-0078: GID-based entity identity for deduplication.

        Searches tracked entities by GID, including temp GIDs that have
        been transitioned to real GIDs after successful CREATE operations.

        Args:
            gid: The GID to look up (real or temp).

        Returns:
            Tracked entity or None if not found.

        Example:
            task = session.find_by_gid("12345")
            if task:
                task.completed = True
        """
        return self._tracker.find_by_gid(gid)

    def is_tracked(self, gid: str) -> bool:
        """Check if GID is currently tracked.

        Per FR-EL-005: Boolean helper for tracking state.
        Per ADR-0078: GID-based entity identity.

        Args:
            gid: The GID to check.

        Returns:
            True if entity with this GID is tracked.

        Example:
            if not session.is_tracked("12345"):
                task = await client.tasks.get_async("12345")
                session.track(task)
        """
        return self._tracker.is_tracked(gid)

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
        Per TDD-TRIAGE-FIXES: Execute cascade operations after actions.
        Per TDD-DETECTION/ADR-0095: Execute healing operations after cascades.
        Per TDD-DEBT-003: Thread-safe state transitions via RLock.

        Commits all tracked entities with pending changes. Entities are
        saved in dependency order. Then action operations (add_tag, etc.)
        are executed. Then cascade operations propagate field values.
        Finally, healing operations add missing project memberships.
        Partial failures are reported but don't roll back successful operations.

        After commit, successfully saved entities are marked clean and
        have their GIDs updated (for new entities). Pending actions are
        cleared regardless of success. Failed cascades remain for retry.
        Healing failures are logged but do not fail the commit.

        Thread Safety:
            Lock is held during state check and state capture, released
            during I/O, and re-acquired for state updates. Entities tracked
            during commit will be included in the next commit, not the
            current one (per ADR-DEBT-003-002).

        Returns:
            SaveResult with succeeded/failed lists. Action failures are
            included in action_results. Cascade results in cascade_results.
            Healing results in healing_report.

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
        # TDD-DEBT-003: Acquire lock for state check and state capture
        dirty_entities, pending_actions, pending_cascades, pending_healing = (
            self._capture_commit_state()
        )

        # Check for empty commit (no lock needed - local variables)
        if (
            not dirty_entities
            and not pending_actions
            and not pending_cascades
            and not pending_healing
        ):
            if self._log:
                self._log.warning(
                    "commit_empty_session",
                    message="No tracked entities, pending actions, cascades, or healing to commit. "
                    "Did you forget to call track() on your entities?",
                )
            return SaveResult()

        if self._log:
            self._log.info(
                "session_commit_start",
                entity_count=len(dirty_entities),
                action_count=len(pending_actions),
                cascade_count=len(pending_cascades),
                healing_count=len(self._healing_manager.queue),
                auto_create_holders=self._auto_create_holders,
            )

        # TDD-DEBT-003: Lock released during I/O - allows track() during execution
        # Entities tracked during commit are queued for next commit (per ADR-DEBT-003-002)

        # Phase 0: ENSURE_HOLDERS
        dirty_entities = await self._execute_ensure_holders(dirty_entities)

        # Phase 1 + 1.5: CRUD + actions + cache invalidation
        crud_result, action_results = await self._execute_crud_and_actions(
            dirty_entities, pending_actions
        )

        # Phase 2: Cascades
        cascade_results = await self._execute_cascades(pending_cascades)

        # Phase 3: Healing
        healing_report = await self._execute_healing()

        # State updates + result assembly
        self._update_post_commit_state(crud_result, action_results)

        crud_result.action_results = action_results
        crud_result.cascade_results = cascade_results
        crud_result.healing_report = healing_report

        # Phase 5: Automation
        automation_results = await self._execute_automation(crud_result)

        # Post-commit hooks + logging
        await self._finalize_commit(
            crud_result,
            action_results,
            cascade_results,
            healing_report,
            automation_results,
        )

        return crud_result

    def _capture_commit_state(
        self,
    ) -> tuple[list[Any], list[ActionOperation], list[Any], bool]:
        """Acquire lock, validate session state, and snapshot pending work.

        Per TDD-DEBT-003: Lock held during state check and state capture.

        Returns:
            Tuple of (dirty_entities, pending_actions, pending_cascades, pending_healing).

        Raises:
            SessionClosedError: If session is closed.
        """
        with self._state_lock():
            if self._state == SessionState.CLOSED:
                raise SessionClosedError()

            dirty_entities = self._tracker.get_dirty_entities()
            pending_actions = list(self._pending_actions)
            pending_cascades = list(self._cascade_operations)
            pending_healing = bool(self._healing_manager.queue)

        return dirty_entities, pending_actions, pending_cascades, pending_healing

    async def _execute_ensure_holders(self, dirty_entities: list[Any]) -> list[Any]:
        """Phase 0: Detect and construct missing holders before CRUD.

        Per TDD-GAP-01: Runs before CRUD when auto_create_holders=True.

        Args:
            dirty_entities: Entities to check for missing holders.

        Returns:
            Updated dirty_entities list (may include newly created holders).
        """
        if self._auto_create_holders and dirty_entities and self._holder_concurrency:
            from autom8_asana.persistence.holder_ensurer import HolderEnsurer

            holder_ensurer = HolderEnsurer(
                client=self._client,
                tracker=self._tracker,
                concurrency=self._holder_concurrency,
                log=self._log,
            )
            dirty_entities = await holder_ensurer.ensure_holders_for_entities(
                dirty_entities
            )
        return dirty_entities

    async def _execute_crud_and_actions(
        self,
        dirty_entities: list[Any],
        pending_actions: list[ActionOperation],
    ) -> tuple[SaveResult, list[ActionResult]]:
        """Phase 1 + 1.5: Execute CRUD, actions, and cache invalidation.

        Args:
            dirty_entities: Entities with pending changes.
            pending_actions: Action operations to execute after CRUD.

        Returns:
            Tuple of (crud_result, action_results).
        """
        # Phase 1: Execute CRUD operations and actions together
        crud_result, action_results = await self._pipeline.execute_with_actions(
            entities=dirty_entities,
            actions=pending_actions,
            action_executor=self._action_executor,
        )

        # Phase 1.5: Cache invalidation for modified entities
        # Per FR-INVALIDATE-001 through FR-INVALIDATE-006
        # ADR-0059: Delegated to CacheInvalidator for SRP
        if self._cache_invalidator:
            gid_to_entity = self._build_gid_lookup(crud_result, action_results)
            await self._cache_invalidator.invalidate_for_commit(
                crud_result, action_results, gid_to_entity
            )

        # TDD-DEBT-003: Re-acquire lock for state updates
        with self._state_lock():
            # Per TDD-TRIAGE-FIXES/ADR-0066: Selective clearing - only remove successful actions
            self._clear_successful_actions(action_results)

        return crud_result, action_results

    async def _execute_cascades(self, pending_cascades: list[Any]) -> list[Any]:
        """Phase 2: Execute cascade operations.

        Args:
            pending_cascades: Cascade operations to execute.

        Returns:
            List of CascadeResult objects.
        """

        cascade_results: list[CascadeResult] = []
        if pending_cascades:
            cascade_result = await self._cascade_executor.execute(pending_cascades)
            cascade_results = [cascade_result]

            # TDD-DEBT-003: Lock for state update
            with self._state_lock():
                # Clear only successful cascades, keep failed for retry
                if cascade_result.success:
                    self._cascade_operations.clear()
                # Failed cascades remain in _cascade_operations for retry

        return cascade_results

    async def _execute_healing(self) -> HealingReport | None:
        """Phase 3: Execute healing operations.

        Per TDD-DETECTION/ADR-0095, TDD-TECH-DEBT-REMEDIATION.

        Returns:
            HealingReport if healing was attempted, None otherwise.
        """
        healing_report: HealingReport | None = None
        if self._healing_manager.queue:
            healing_report = await self._healing_manager.execute_async(
                self._client.http
            )
            if self._log:
                for result in healing_report.results:
                    if result.success:
                        self._log.info(
                            "session_healing_success",
                            entity_gid=result.entity_gid,
                            entity_type=result.entity_type,
                            project_gid=result.project_gid,
                        )
                    else:
                        self._log.warning(
                            "session_healing_failed",
                            entity_gid=result.entity_gid,
                            entity_type=result.entity_type,
                            project_gid=result.project_gid,
                            error=result.error,
                        )
        return healing_report

    def _update_post_commit_state(
        self,
        crud_result: SaveResult,
        action_results: list[ActionResult],
    ) -> None:
        """Update session state after successful phases.

        Per FR-CHANGE-009: Reset entity state after successful save.
        Per TDD-DEBT-003: Re-acquire lock for final state updates.

        Args:
            crud_result: Result of CRUD operations.
            action_results: Results of action operations.
        """
        with self._state_lock():
            # Reset state for successful entities (FR-CHANGE-009)
            # DEF-001 FIX: Order matters - clear accessor BEFORE capturing snapshot
            for entity in crud_result.succeeded:
                # Per ADR-0074: Reset custom field tracking (Systems 2 & 3) FIRST
                # This clears stale modifications before snapshot capture
                self._reset_custom_field_tracking(entity)
                # Then capture clean snapshot (mark_clean calls model_dump())
                self._tracker.mark_clean(entity)

            self._state = SessionState.COMMITTED

    async def _execute_automation(self, crud_result: SaveResult) -> list[Any]:
        """Phase 5: Execute automation evaluation.

        Per TDD-AUTOMATION-LAYER / NFR-003: Automation failures do NOT
        propagate (isolated execution).

        Args:
            crud_result: Result of CRUD operations for automation evaluation.

        Returns:
            List of AutomationResult objects.
        """
        from autom8_asana.persistence.models import AutomationResult

        automation_results: list[AutomationResult] = []

        if self._automation_enabled and self._client.automation:
            try:
                automation_results = await self._client.automation.evaluate_async(
                    crud_result,
                    self._client,
                )
                crud_result.automation_results = automation_results
            except (
                ConnectionError,
                TimeoutError,
                OSError,
                RuntimeError,
                TypeError,
            ) as e:  # isolation -- per NFR-003, automation failures must not fail commit
                # Per NFR-003: Automation failures don't fail commit
                # TypeError can come from mock/plugin configuration issues
                from autom8y_log import get_logger

                get_logger(__name__).warning(
                    "automation_evaluation_failed", error=str(e)
                )

        return automation_results

    async def _finalize_commit(
        self,
        crud_result: SaveResult,
        action_results: list[ActionResult],
        cascade_results: list[Any],
        healing_report: HealingReport | None,
        automation_results: list[Any],
    ) -> None:
        """Emit post-commit hooks and log final commit metrics.

        Per TDD-AUTOMATION-LAYER/FR-002: Post-commit event emission.

        Args:
            crud_result: Result of CRUD operations.
            action_results: Results of action operations.
            cascade_results: Results of cascade operations.
            healing_report: Healing report if healing was attempted.
            automation_results: Results of automation evaluation.
        """
        # Emit post-commit hooks (TDD-AUTOMATION-LAYER/FR-002)
        await self._events.emit_post_commit(crud_result)

        # Count failures for logging
        action_failures = sum(1 for r in action_results if not r.success)
        cascade_failures = sum(1 for r in cascade_results if not r.success)
        healing_attempted = healing_report.attempted if healing_report else 0
        healing_failures = healing_report.failed if healing_report else 0

        # Count automation metrics for logging
        automation_succeeded = sum(
            1 for r in automation_results if r.success and not r.was_skipped
        )
        automation_failed = sum(1 for r in automation_results if not r.success)
        automation_skipped = sum(1 for r in automation_results if r.was_skipped)

        if self._log:
            self._log.info(
                "session_commit_complete",
                succeeded=len(crud_result.succeeded),
                failed=len(crud_result.failed),
                action_succeeded=len(action_results) - action_failures,
                action_failed=action_failures,
                cascade_succeeded=len(cascade_results) - cascade_failures,
                cascade_failed=cascade_failures,
                healing_attempted=healing_attempted,
                healing_failed=healing_failures,
                automation_succeeded=automation_succeeded,
                automation_failed=automation_failed,
                automation_skipped=automation_skipped,
            )

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
            | Callable[
                [AsanaResource, OperationType, Exception], Coroutine[Any, Any, None]
            ]
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

    def on_post_commit(
        self,
        func: (
            Callable[[SaveResult], None]
            | Callable[[SaveResult], Coroutine[Any, Any, None]]
        ),
    ) -> Callable[..., Any]:
        """Register post-commit hook (decorator).

        Per TDD-AUTOMATION-LAYER/FR-002: Post-commit hooks receive SaveResult.

        Post-commit hooks are called after the entire commit operation
        completes, including CRUD, actions, cascades, healing, and automation.
        They receive the full SaveResult for inspection.

        Post-commit hooks cannot fail the commit (it already succeeded).
        Exceptions are swallowed.

        Args:
            func: Hook function receiving (SaveResult). Can be sync or async.

        Returns:
            The decorated function.

        Example:
            @session.on_post_commit
            async def log_automation(result: SaveResult) -> None:
                for auto_result in result.automation_results:
                    logger.info("Rule %s: %s", auto_result.rule_name, auto_result.success)
        """
        return self._events.register_post_commit(func)

    # --- TDD-0011: Action Operations (via ActionBuilder) ---
    # Per TDD-SPRINT-4/ADR-0122: Descriptor-based factory replaces 770+ lines
    # with 13 descriptor declarations. Docstrings are in ACTION_REGISTRY.

    # Tag operations
    add_tag = ActionBuilder("add_tag")
    remove_tag = ActionBuilder("remove_tag")

    # Project operations
    add_to_project = ActionBuilder("add_to_project")
    remove_from_project = ActionBuilder("remove_from_project")

    # Dependency operations
    add_dependency = ActionBuilder("add_dependency")
    remove_dependency = ActionBuilder("remove_dependency")

    # Section operations
    move_to_section = ActionBuilder("move_to_section")

    # Follower operations
    add_follower = ActionBuilder("add_follower")
    remove_follower = ActionBuilder("remove_follower")

    # Dependent operations
    add_dependent = ActionBuilder("add_dependent")
    remove_dependent = ActionBuilder("remove_dependent")

    # Like operations
    add_like = ActionBuilder("add_like")
    remove_like = ActionBuilder("remove_like")

    # --- Batch and Custom Action Methods ---
    # These methods have custom logic and cannot be generated by ActionBuilder.

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
            target=None,  # Comments don't need a target
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
            target=None,  # Per ADR-0045: Not used for SET_PARENT
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

    def reorder_subtasks(
        self,
        parent: AsanaResource | str,
        current_order: list[AsanaResource],
        desired_order: list[AsanaResource],
    ) -> ReorderPlan:
        """Reorder subtasks under a parent with minimum API calls.

        Per TDD-GAP-06: Computes LIS-optimized reorder plan, then queues
        SET_PARENT actions for each Move.

        Does NOT modify the existing reorder_subtask() singular method.

        Args:
            parent: Parent task (AsanaResource or GID string). All items in
                current_order must be subtasks of this parent.
            current_order: Children in their current sequence.
            desired_order: Children in the target sequence.

        Returns:
            The computed ReorderPlan (for logging/inspection).

        Raises:
            ValueError: If current_order and desired_order contain different elements.
            SessionClosedError: If session is closed.
        """
        from autom8_asana.persistence.reorder import compute_reorder_plan

        self._ensure_open()

        plan = compute_reorder_plan(current_order, desired_order)

        if plan.moves_required > 0:
            parent_gid = parent if isinstance(parent, str) else parent.gid
            if self._log:
                self._log.info(
                    "reorder_plan_computed",
                    parent_gid=parent_gid,
                    total_children=plan.total_children,
                    lis_length=plan.lis_length,
                    moves_required=plan.moves_required,
                )

        for move in plan.moves:
            if move.direction == "insert_after":
                self.set_parent(move.item, parent, insert_after=move.reference)
            else:
                self.set_parent(move.item, parent, insert_before=move.reference)

            if self._log:
                self._log.debug(
                    "move_planned",
                    item=move.item.gid,
                    reference=move.reference.gid,
                    direction=move.direction,
                )

        return plan

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

    # --- TDD-BIZMODEL Phase 3: Cascade Operations ---

    def cascade_field(
        self,
        entity: T,
        field_name: str,
        *,
        target_types: tuple[type, ...] | None = None,
    ) -> SaveSession:
        """Queue a cascade operation for the commit phase.

        Per ADR-0054: Queue cascade operations to propagate field values
        from a source entity to its descendants.

        Cascade operations are executed after CRUD operations during commit.
        The field value from the source entity will be propagated to all
        descendants based on the CascadingFieldDef rules.

        Args:
            entity: Source entity owning the cascading field.
            field_name: Name of the custom field to cascade.
            target_types: Optional tuple of entity types to cascade to.
                         If None, uses types from CascadingFieldDef.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.

        Example:
            # Cascade office phone to all descendants
            session.cascade_field(business, "Office Phone")

            # Cascade vertical only to Offers
            from autom8_asana.models.business import Offer
            session.cascade_field(unit, "Vertical", target_types=(Offer,))

            await session.commit_async()
        """
        self._ensure_open()

        from autom8_asana.persistence.cascade import CascadeOperation

        op = CascadeOperation(
            source_entity=entity,
            field_name=field_name,
            target_types=target_types,
        )

        # TDD-TRIAGE-FIXES: Use pre-initialized list (not hasattr check)
        self._cascade_operations.append(op)

        if self._log:
            self._log.debug(
                "session_cascade_field",
                entity_type=type(entity).__name__,
                entity_gid=entity.gid,
                field_name=field_name,
                target_types=[t.__name__ for t in target_types]
                if target_types
                else None,
            )

        return self

    def get_pending_cascades(self) -> list[Any]:
        """Get list of pending cascade operations.

        Per ADR-0054: Allow inspection of pending cascades before commit.

        Returns:
            Copy of the pending cascade operations list.
        """
        # TDD-TRIAGE-FIXES: Use pre-initialized list
        return list(self._cascade_operations)

    # --- Internal ---

    @contextmanager
    def _state_lock(self) -> Generator[None, None, None]:
        """Context manager for thread-safe state operations.

        Per TDD-DEBT-003: Protects all state reads and writes.

        Usage:
            with self._state_lock():
                # State operations here are atomic

        Yields:
            None
        """
        self._lock.acquire()
        try:
            yield
        finally:
            self._lock.release()

    @contextmanager
    def _require_open(self) -> Generator[None, None, None]:
        """Context manager ensuring session stays open during operation.

        Per TDD-DEBT-003: Acquires lock, verifies session is open, yields,
        then releases lock. The entire block is atomic with respect to
        state changes.

        Usage:
            with self._require_open():
                # Operations here are protected and session is guaranteed open

        Yields:
            None

        Raises:
            SessionClosedError: If session is closed at entry.
        """
        with self._state_lock():
            if self._state == SessionState.CLOSED:
                raise SessionClosedError()
            yield

    def _ensure_open(self) -> None:
        """Ensure session is still open for operations.

        Note: This method is NOT thread-safe by itself. Use _require_open()
        context manager for thread-safe check-and-operate patterns.

        Raises:
            SessionClosedError: If session has been closed.
        """
        if self._state == SessionState.CLOSED:
            raise SessionClosedError()

    def _reset_custom_field_tracking(self, entity: AsanaResource) -> None:
        """Reset custom field tracking state after successful commit.

        Per ADR-0074: SaveSession coordinates reset across all tracking systems.
        Only Task has custom fields; uses duck typing for extensibility.

        Args:
            entity: Successfully committed entity.
        """
        if hasattr(entity, "reset_custom_field_tracking"):
            entity.reset_custom_field_tracking()

    def _clear_successful_actions(self, action_results: list[ActionResult]) -> None:
        """Remove only successful actions from pending list.

        Per TDD-TRIAGE-FIXES/ADR-0066: Failed actions remain for inspection/retry.

        Args:
            action_results: Results from action execution.
        """
        if not action_results:
            # No actions executed, clear all (original behavior for empty case)
            self._pending_actions.clear()
            return

        # Build set of successful action identities
        # Per ADR-0107: Identity uses NameGid (hashable via gid-based __hash__)
        # Identity = (task.gid, action_type, target)
        successful_identities: set[tuple[str, ActionType, NameGid | None]] = set()
        for result in action_results:
            if result.success:
                action = result.action
                identity = (action.task.gid, action.action, action.target)
                successful_identities.add(identity)

        # Keep only failed actions
        self._pending_actions = [
            action
            for action in self._pending_actions
            if (action.task.gid, action.action, action.target)
            not in successful_identities
        ]

    # --- Cache Invalidation Support (ADR-0059) ---

    def _build_gid_lookup(
        self,
        crud_result: SaveResult,
        action_results: list[ActionResult],
    ) -> dict[str, Any]:
        """Build GID to entity lookup map for cache invalidation.

        Per ADR-0059: Support method for CacheInvalidator delegation.

        Collects entities from:
        1. CRUD succeeded entities
        2. Tracker (for membership access)
        3. Action results (entities may not be tracked)

        Args:
            crud_result: Result of CRUD operations.
            action_results: Results of action operations.

        Returns:
            Dict mapping GID -> entity for membership lookup.
        """
        gid_to_entity: dict[str, Any] = {}

        # Add succeeded entities from CRUD result
        for entity in crud_result.succeeded:
            if hasattr(entity, "gid") and entity.gid:
                gid_to_entity[entity.gid] = entity

        # Add entities from tracker (may have richer membership data)
        for entity in crud_result.succeeded:
            if hasattr(entity, "gid") and entity.gid:
                tracked = self._tracker.find_by_gid(entity.gid)
                if tracked:
                    gid_to_entity[entity.gid] = tracked

        # Add entities from action results (may not be tracked)
        for action_result in action_results:
            if action_result.success and action_result.action.task:
                action_task = action_result.action.task
                if hasattr(action_task, "gid") and action_task.gid:
                    if action_task.gid not in gid_to_entity:
                        gid_to_entity[action_task.gid] = action_task

        return gid_to_entity

    # --- Self-Healing (TDD-DETECTION/ADR-0095, TDD-TECH-DEBT-REMEDIATION) ---
    # Healing logic is now in HealingManager. These methods are preserved for
    # backward compatibility if any subclasses override them.
    # The track() and commit_async() methods now use self._healing_manager directly.
