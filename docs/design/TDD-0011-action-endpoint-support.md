# TDD-0011: Action Endpoint Support for Save Orchestration

## Metadata
- **TDD ID**: TDD-0011
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-10
- **Last Updated**: 2025-12-10
- **PRD Reference**: [PRD-0006](../requirements/PRD-0006-action-endpoint-support.md)
- **Related TDDs**:
  - [TDD-0010](TDD-0010-save-orchestration.md) - Save Orchestration Layer (foundation)
  - [TDD-0005](TDD-0005-batch-api.md) - Batch API for Bulk Operations
- **Related ADRs**:
  - [ADR-0042](../decisions/ADR-0042-action-operation-types.md) - Separate ActionType Enum for Action Endpoint Operations
  - [ADR-0043](../decisions/ADR-0043-unsupported-operation-detection.md) - Validation-Phase Detection for Unsupported Direct Modifications
  - [ADR-0035](../decisions/ADR-0035-unit-of-work-pattern.md) - Unit of Work Pattern (from TDD-0010)
  - [ADR-0036](../decisions/ADR-0036-change-tracking-strategy.md) - Change Tracking via Snapshot Comparison

## Overview

This design extends the Save Orchestration Layer (TDD-0010) to support Asana action endpoints. Action operations (`add_tag`, `remove_tag`, `add_to_project`, `remove_from_project`, `add_dependency`, `remove_dependency`, `move_to_section`) are queued via new `SaveSession` methods and executed after CRUD operations during commit. Additionally, direct modifications to collection fields (`tags`, `projects`, `memberships`, `dependencies`) are detected and rejected with actionable error messages. This ensures developers use the correct API patterns and prevents silent data loss.

## Requirements Summary

This design addresses [PRD-0006](../requirements/PRD-0006-action-endpoint-support.md) v1.0:

- **12 Action Operation Requirements** (FR-ACTION-001 through FR-ACTION-012): Fluent API methods for action operations
- **9 Unsupported Operation Detection Requirements** (FR-UNSUP-001 through FR-UNSUP-009): Detect and reject direct modifications
- **9 Custom Field Persistence Test Requirements** (FR-CF-001 through FR-CF-009): Test coverage for 6 custom field types
- **5 Exception Requirements** (FR-EXC-001 through FR-EXC-005): `UnsupportedOperationError` exception
- **3 Preview Integration Requirements** (FR-PREV-001 through FR-PREV-003): Action operations in preview

Key requirements driving this design:

| Requirement | Summary | Design Impact |
|-------------|---------|---------------|
| FR-ACTION-010 | Actions queued and executed on commit | New `_pending_actions` list in SaveSession |
| FR-ACTION-011 | Actions execute after CRUD operations | New action execution phase in SavePipeline |
| FR-ACTION-012 | Actions support newly created entities (temp GIDs) | GID resolution extends to action operations |
| FR-UNSUP-005 | Detection before API calls | Validation in SavePipeline.preview/execute |
| FR-UNSUP-007 | Error includes correct API guidance | UnsupportedOperationError with suggestions |

## System Context

The action endpoint support extends the existing Save Orchestration Layer architecture. New components are shown in **bold**.

```
+---------------------------------------------------------------------------+
|                              SYSTEM CONTEXT                                |
+---------------------------------------------------------------------------+

                            +------------------------+
                            |    SDK Consumers       |
                            |  (autom8, services)    |
                            +-----------+------------+
                                        |
                           session.add_tag(task, tag)
                           session.move_to_section(task, section)
                           await session.commit()
                                        |
                                        v
+---------------------------------------------------------------------------+
|                         autom8_asana SDK                                   |
|                                                                            |
|  +----------------------------------------------------------------------+ |
|  |                    Save Orchestration Layer                          | |
|  |                                                                      | |
|  |  +----------------+  +----------------+  +----------------+          | |
|  |  |  SaveSession   |  | ChangeTracker  |  |DependencyGraph |          | |
|  |  | + add_tag()    |  | (unchanged)    |  |  (unchanged)   |          | |
|  |  | + remove_tag() |  +----------------+  +----------------+          | |
|  |  | + add_to_proj()|                                                  | |
|  |  | + move_to_sec()|  +----------------+                              | |
|  |  | +_pending_acts |  | **ActionQueue**|  <-- NEW: queues actions     | |
|  |  +-------+--------+  +-------+--------+                              | |
|  |          |                   |                                       | |
|  |          +-------------------+                                       | |
|  |                              |                                       | |
|  |                              v                                       | |
|  |              +---------------+---------------+                       | |
|  |              |         SavePipeline          |                       | |
|  |              | + _validate_unsupported()     |  <-- NEW: validation  | |
|  |              | + _execute_actions()          |  <-- NEW: action exec | |
|  |              +---------------+---------------+                       | |
|  |                              |                                       | |
|  |                +-------------+-------------+                         | |
|  |                |                           |                         | |
|  |                v                           v                         | |
|  |  +-------------+-------+     +-------------+-------+                 | |
|  |  |   BatchExecutor     |     | **ActionExecutor**  |  <-- NEW       | |
|  |  | (CRUD via Batch API)|     | (individual POSTs)  |                 | |
|  |  +---------------------+     +---------------------+                 | |
|  |                                                                      | |
|  +----------------------------------------------------------------------+ |
|                                                                            |
+---------------------------------------------------------------------------+
                                    |
                                    v
                    +------------------------+
                    |    Infrastructure      |
                    |  (Asana REST API)      |
                    |  POST /tasks/gid/addTag|
                    |  POST /sections/gid/...|
                    +------------------------+
```

### Integration Points

| Integration Point | Interface | Direction | Notes |
|-------------------|-----------|-----------|-------|
| `SaveSession` API | New methods | In | `add_tag()`, `remove_tag()`, etc. |
| `SavePipeline` | Extended phases | Internal | Validation + action execution |
| `ActionExecutor` | New component | Internal | Individual API calls for actions |
| `AsanaClient.http` | HTTP client | Out | Direct POST calls (not batch) |
| `UnsupportedOperationError` | New exception | Out | Raised on validation failure |

## Design

### Package Structure Extension

```
src/autom8_asana/
+-- persistence/
|   +-- __init__.py              # Extended exports: ActionType, ActionOperation, etc.
|   +-- session.py               # Extended: add_tag(), remove_tag(), etc.
|   +-- tracker.py               # Unchanged
|   +-- graph.py                 # Unchanged
|   +-- pipeline.py              # Extended: _validate_unsupported(), _execute_actions()
|   +-- executor.py              # Unchanged (CRUD execution)
|   +-- action_executor.py       # NEW: Action endpoint execution
|   +-- events.py                # Unchanged
|   +-- models.py                # Extended: ActionType, ActionOperation
|   +-- exceptions.py            # Extended: UnsupportedOperationError
```

### Component Architecture

```
+---------------------------------------------------------------------------+
|                      EXTENDED COMPONENT ARCHITECTURE                        |
+---------------------------------------------------------------------------+

+---------------------------------------------------------------------------+
|                              PUBLIC API                                    |
|                                                                            |
|    SaveSession (extended)                                                  |
|    +-- track(entity)           # Existing                                 |
|    +-- delete(entity)          # Existing                                 |
|    +-- preview()               # Extended: includes actions               |
|    +-- commit_async()          # Extended: executes actions               |
|    +-- commit()                # Extended: executes actions               |
|                                                                            |
|    NEW ACTION METHODS (fluent, return self):                              |
|    +-- add_tag(task, tag)                                                 |
|    +-- remove_tag(task, tag)                                              |
|    +-- add_to_project(task, project, section=None)                        |
|    +-- remove_from_project(task, project)                                 |
|    +-- add_dependency(task, depends_on)                                   |
|    +-- remove_dependency(task, depends_on)                                |
|    +-- move_to_section(task, section)                                     |
|                                                                            |
+---------------------------------+-----------------------------------------+
                                  |
                                  v
+---------------------------------------------------------------------------+
|                           INTERNAL COMPONENTS                              |
|                                                                            |
|  +-------------------+    +------------------+    +------------------+     |
|  |  ChangeTracker    |    | DependencyGraph  |    |   EventSystem    |     |
|  |   (unchanged)     |    |   (unchanged)    |    |   (unchanged)    |     |
|  +--------+----------+    +--------+---------+    +--------+---------+     |
|           |                        |                       |               |
|           +------------------------+-----------------------+               |
|                                    |                                       |
|                                    v                                       |
|                       +------------+------------+                          |
|                       |       SavePipeline      |                          |
|                       |       (extended)        |                          |
|                       |                         |                          |
|                       | Phase 0: VALIDATE-NEW   | <-- NEW                  |
|                       |   _validate_unsupported |                          |
|                       |                         |                          |
|                       | Phase 1: VALIDATE       |                          |
|                       |   - cycle detection     |                          |
|                       |                         |                          |
|                       | Phase 2: PREPARE        |                          |
|                       |   - build requests      |                          |
|                       |                         |                          |
|                       | Phase 3: EXECUTE-CRUD   |                          |
|                       |   - per-level batching  |                          |
|                       |   - GID resolution      |                          |
|                       |                         |                          |
|                       | Phase 4: EXECUTE-ACTIONS| <-- NEW                  |
|                       |   - resolve target GIDs |                          |
|                       |   - individual POSTs    |                          |
|                       |                         |                          |
|                       | Phase 5: CONFIRM        |                          |
|                       |   - update entities     |                          |
|                       +------------+------------+                          |
|                                    |                                       |
|                       +------------+------------+                          |
|                       |                         |                          |
|                       v                         v                          |
|           +-----------+---------+   +-----------+---------+                |
|           |    BatchExecutor    |   |   ActionExecutor    | <-- NEW        |
|           | (CRUD via batch)    |   | (individual POSTs)  |                |
|           +---------------------+   +---------------------+                |
|                                                                            |
+---------------------------------------------------------------------------+
```

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `SaveSession` (extended) | Action method API; action queue management | `persistence/session.py` |
| `SavePipeline` (extended) | Unsupported field validation; action execution phase | `persistence/pipeline.py` |
| `ActionExecutor` (new) | Execute individual action API calls | `persistence/action_executor.py` |
| `ActionType` (new) | Enum of action operation types | `persistence/models.py` |
| `ActionOperation` (new) | Queued action with target, related entity, params | `persistence/models.py` |
| `UnsupportedOperationError` (new) | Exception for direct modifications | `persistence/exceptions.py` |

### Data Model Extensions

#### ActionType Enum (per ADR-0042)

```python
# autom8_asana/persistence/models.py

class ActionType(Enum):
    """Type of action operation requiring dedicated API endpoint.

    Per ADR-0042: Separate from OperationType because action operations
    have different execution characteristics (not batch-eligible,
    execute after CRUD, relationship-focused).
    """
    ADD_TAG = "add_tag"
    REMOVE_TAG = "remove_tag"
    ADD_TO_PROJECT = "add_to_project"
    REMOVE_FROM_PROJECT = "remove_from_project"
    ADD_DEPENDENCY = "add_dependency"
    REMOVE_DEPENDENCY = "remove_dependency"
    MOVE_TO_SECTION = "move_to_section"
```

#### ActionOperation Dataclass

```python
# autom8_asana/persistence/models.py

@dataclass(frozen=True)
class ActionOperation:
    """A planned action operation requiring a dedicated API endpoint.

    Per FR-ACTION-010: Action operations queued and executed on commit.
    Per FR-ACTION-011: Action operations execute after CRUD operations.

    Attributes:
        action_type: The type of action to perform
        target_entity: The primary entity (e.g., task for add_tag)
        related_entity_gid: The GID of the related entity (e.g., tag GID)
        extra_params: Additional parameters (e.g., section for add_to_project)
    """
    action_type: ActionType
    target_entity: AsanaResource
    related_entity_gid: str
    extra_params: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        entity_repr = f"{type(self.target_entity).__name__}(gid={self.target_entity.gid})"
        return f"ActionOperation({self.action_type.value}, {entity_repr}, related={self.related_entity_gid})"
```

#### UnsupportedOperationError (per ADR-0043)

```python
# autom8_asana/persistence/exceptions.py

class UnsupportedOperationError(SaveOrchestrationError):
    """Raised when attempting unsupported direct modification.

    Per FR-UNSUP-006, FR-UNSUP-007: Error message includes field name
    and suggests correct action methods.

    Attributes:
        field_name: The field that was modified directly
        suggested_methods: Tuple of correct session method names
        entity: The entity with the unsupported modification (optional)
    """

    FIELD_SUGGESTIONS: ClassVar[dict[str, tuple[str, ...]]] = {
        "tags": ("add_tag", "remove_tag"),
        "projects": ("add_to_project", "remove_from_project"),
        "memberships": ("add_to_project", "remove_from_project", "move_to_section"),
        "dependencies": ("add_dependency", "remove_dependency"),
    }

    def __init__(
        self,
        field_name: str,
        entity: AsanaResource | None = None,
    ) -> None:
        """Initialize with field name and optional entity.

        Args:
            field_name: The field that was modified directly
            entity: The entity with the modification (for error context)
        """
        self.field_name = field_name
        self.entity = entity
        suggestions = self.FIELD_SUGGESTIONS.get(field_name, ())
        self.suggested_methods = suggestions

        entity_desc = ""
        if entity:
            entity_desc = f" on {type(entity).__name__}(gid={entity.gid})"

        if suggestions:
            methods = " or ".join(f"session.{m}()" for m in suggestions)
            message = (
                f"Direct modification of '{field_name}'{entity_desc} is not supported. "
                f"Use {methods} instead."
            )
        else:
            message = f"Direct modification of '{field_name}'{entity_desc} is not supported."

        super().__init__(message)
```

### Interface Specifications

#### SaveSession Extensions

```python
# autom8_asana/persistence/session.py (extended)

class SaveSession:
    """Unit of Work pattern for batched Asana operations.

    Extended per PRD-0006 with action endpoint methods.
    """

    def __init__(
        self,
        client: AsanaClient,
        batch_size: int = 10,
        max_concurrent: int = 15,
    ) -> None:
        # ... existing initialization ...

        # NEW: Queue for action operations
        self._pending_actions: list[ActionOperation] = []

    # --- Action Methods (per FR-ACTION-001 through FR-ACTION-009) ---

    def add_tag(
        self,
        task: Task | str,
        tag: Tag | NameGid | str,
    ) -> SaveSession:
        """Add a tag to a task.

        Per FR-ACTION-001: Queues action; on commit, POST /tasks/{gid}/addTag.
        Per FR-ACTION-008: Accepts entity objects or GID strings.
        Per FR-ACTION-009: Returns self for fluent chaining.

        Args:
            task: Task entity or GID string
            tag: Tag entity, NameGid, or GID string

        Returns:
            Self for fluent chaining

        Raises:
            SessionClosedError: If session is closed

        Example:
            session.add_tag(task, urgent_tag).add_tag(task, priority_tag)
        """
        self._ensure_open()

        task_entity = self._resolve_entity(task, "task")
        tag_gid = self._resolve_gid(tag)

        self._pending_actions.append(
            ActionOperation(
                action_type=ActionType.ADD_TAG,
                target_entity=task_entity,
                related_entity_gid=tag_gid,
            )
        )

        if self._log:
            self._log.debug(
                "session_add_tag",
                task_gid=task_entity.gid,
                tag_gid=tag_gid,
            )

        return self

    def remove_tag(
        self,
        task: Task | str,
        tag: Tag | NameGid | str,
    ) -> SaveSession:
        """Remove a tag from a task.

        Per FR-ACTION-002: Queues action; on commit, POST /tasks/{gid}/removeTag.

        Args:
            task: Task entity or GID string
            tag: Tag entity, NameGid, or GID string

        Returns:
            Self for fluent chaining
        """
        self._ensure_open()

        task_entity = self._resolve_entity(task, "task")
        tag_gid = self._resolve_gid(tag)

        self._pending_actions.append(
            ActionOperation(
                action_type=ActionType.REMOVE_TAG,
                target_entity=task_entity,
                related_entity_gid=tag_gid,
            )
        )

        return self

    def add_to_project(
        self,
        task: Task | str,
        project: Project | NameGid | str,
        *,
        section: Section | NameGid | str | None = None,
    ) -> SaveSession:
        """Add a task to a project.

        Per FR-ACTION-003: Queues action; on commit, POST /tasks/{gid}/addProject.

        Args:
            task: Task entity or GID string
            project: Project entity, NameGid, or GID string
            section: Optional section within the project

        Returns:
            Self for fluent chaining
        """
        self._ensure_open()

        task_entity = self._resolve_entity(task, "task")
        project_gid = self._resolve_gid(project)

        extra_params: dict[str, Any] = {}
        if section is not None:
            extra_params["section"] = self._resolve_gid(section)

        self._pending_actions.append(
            ActionOperation(
                action_type=ActionType.ADD_TO_PROJECT,
                target_entity=task_entity,
                related_entity_gid=project_gid,
                extra_params=extra_params,
            )
        )

        return self

    def remove_from_project(
        self,
        task: Task | str,
        project: Project | NameGid | str,
    ) -> SaveSession:
        """Remove a task from a project.

        Per FR-ACTION-004: Queues action; on commit, POST /tasks/{gid}/removeProject.

        Args:
            task: Task entity or GID string
            project: Project entity, NameGid, or GID string

        Returns:
            Self for fluent chaining
        """
        self._ensure_open()

        task_entity = self._resolve_entity(task, "task")
        project_gid = self._resolve_gid(project)

        self._pending_actions.append(
            ActionOperation(
                action_type=ActionType.REMOVE_FROM_PROJECT,
                target_entity=task_entity,
                related_entity_gid=project_gid,
            )
        )

        return self

    def add_dependency(
        self,
        task: Task | str,
        depends_on: Task | str,
    ) -> SaveSession:
        """Add a dependency (task depends on another task).

        Per FR-ACTION-005: Queues action; on commit, POST /tasks/{gid}/addDependencies.

        Args:
            task: Task entity or GID string (the dependent task)
            depends_on: Task entity or GID string (the prerequisite task)

        Returns:
            Self for fluent chaining

        Example:
            # Task C depends on Tasks A and B
            session.add_dependency(task_c, task_a).add_dependency(task_c, task_b)
        """
        self._ensure_open()

        task_entity = self._resolve_entity(task, "task")
        dependency_gid = self._resolve_gid(depends_on)

        self._pending_actions.append(
            ActionOperation(
                action_type=ActionType.ADD_DEPENDENCY,
                target_entity=task_entity,
                related_entity_gid=dependency_gid,
            )
        )

        return self

    def remove_dependency(
        self,
        task: Task | str,
        depends_on: Task | str,
    ) -> SaveSession:
        """Remove a dependency.

        Per FR-ACTION-006: Queues action; on commit, POST /tasks/{gid}/removeDependencies.

        Args:
            task: Task entity or GID string (the dependent task)
            depends_on: Task entity or GID string (the prerequisite task)

        Returns:
            Self for fluent chaining
        """
        self._ensure_open()

        task_entity = self._resolve_entity(task, "task")
        dependency_gid = self._resolve_gid(depends_on)

        self._pending_actions.append(
            ActionOperation(
                action_type=ActionType.REMOVE_DEPENDENCY,
                target_entity=task_entity,
                related_entity_gid=dependency_gid,
            )
        )

        return self

    def move_to_section(
        self,
        task: Task | str,
        section: Section | NameGid | str,
    ) -> SaveSession:
        """Move a task to a section.

        Per FR-ACTION-007: Queues action; on commit, POST /sections/{gid}/addTask.

        Note: This endpoint uses the section GID in the path, not the task GID.

        Args:
            task: Task entity or GID string
            section: Section entity, NameGid, or GID string

        Returns:
            Self for fluent chaining
        """
        self._ensure_open()

        task_entity = self._resolve_entity(task, "task")
        section_gid = self._resolve_gid(section)

        self._pending_actions.append(
            ActionOperation(
                action_type=ActionType.MOVE_TO_SECTION,
                target_entity=task_entity,
                related_entity_gid=section_gid,
            )
        )

        return self

    # --- Helper Methods ---

    def _resolve_entity(
        self,
        entity_or_gid: AsanaResource | str,
        expected_type: str,
    ) -> AsanaResource:
        """Resolve entity reference to AsanaResource.

        Per FR-ACTION-008: Accept entity objects or GID strings.
        For GID strings, creates a minimal entity wrapper for consistency.
        """
        if isinstance(entity_or_gid, str):
            # Create minimal entity from GID
            # Note: This is a stub; real implementation may need type-specific handling
            from autom8_asana.models.task import Task
            return Task(gid=entity_or_gid)
        return entity_or_gid

    def _resolve_gid(
        self,
        ref: AsanaResource | NameGid | str,
    ) -> str:
        """Resolve any reference type to GID string."""
        if isinstance(ref, str):
            return ref
        if hasattr(ref, "gid"):
            return ref.gid
        raise ValueError(f"Cannot resolve GID from {type(ref).__name__}")

    # --- Extended Preview ---

    def preview(self) -> list[PlannedOperation | ActionOperation]:
        """Preview planned operations without executing.

        Per FR-PREV-001: Includes queued action operations.
        Per FR-PREV-002: Actions appear after CRUD operations.
        Per FR-PREV-003: Detects unsupported direct modifications.

        Returns:
            List of PlannedOperation and ActionOperation in execution order

        Raises:
            CyclicDependencyError: If dependency cycle detected
            UnsupportedOperationError: If unsupported direct modification detected
        """
        dirty = self._tracker.get_dirty_entities()

        # Get CRUD operations with validation
        crud_ops = self._pipeline.preview(dirty)

        # Append action operations (per FR-PREV-002)
        all_ops: list[PlannedOperation | ActionOperation] = list(crud_ops)
        all_ops.extend(self._pending_actions)

        return all_ops
```

#### SavePipeline Extensions

```python
# autom8_asana/persistence/pipeline.py (extended)

class SavePipeline:
    """Orchestrates the save operation through phases.

    Extended per TDD-0011 with:
    - Unsupported field validation (Phase 0)
    - Action execution (Phase 4)
    """

    UNSUPPORTED_FIELDS: ClassVar[set[str]] = {
        "tags",
        "projects",
        "memberships",
        "dependencies",
    }

    def __init__(
        self,
        tracker: ChangeTracker,
        graph: DependencyGraph,
        events: EventSystem,
        batch_client: BatchClient,
        action_executor: ActionExecutor,  # NEW
        batch_size: int = 10,
    ) -> None:
        self._tracker = tracker
        self._graph = graph
        self._events = events
        self._executor = BatchExecutor(batch_client, batch_size)
        self._action_executor = action_executor  # NEW

    def preview(
        self,
        entities: list[AsanaResource],
    ) -> list[PlannedOperation]:
        """Preview operations without executing.

        Per FR-PREV-003: Validates for unsupported modifications.
        """
        if not entities:
            return []

        # Phase 0: Validate unsupported modifications
        self._validate_no_unsupported_changes(entities)

        # Phase 1: Build graph and validate cycles
        self._graph.build(entities)
        levels = self._graph.get_levels()

        # ... rest unchanged ...

    async def execute(
        self,
        entities: list[AsanaResource],
        actions: list[ActionOperation],  # NEW parameter
    ) -> SaveResult:
        """Execute all pending changes and actions.

        Extended per FR-ACTION-011: Actions execute after CRUD.

        Args:
            entities: List of entities to save
            actions: List of action operations to execute

        Returns:
            SaveResult with succeeded and failed lists
        """
        if not entities and not actions:
            return SaveResult()

        # Phase 0: Validate unsupported modifications
        self._validate_no_unsupported_changes(entities)

        # Phases 1-3: CRUD execution (unchanged)
        crud_result = await self._execute_crud(entities)

        # Build GID map for action resolution
        gid_map = self._build_gid_map(entities, crud_result.succeeded)

        # Phase 4: Execute actions
        action_result = await self._execute_actions(actions, gid_map)

        # Combine results
        return SaveResult(
            succeeded=crud_result.succeeded + action_result.succeeded,
            failed=crud_result.failed + action_result.failed,
        )

    def _validate_no_unsupported_changes(
        self,
        entities: list[AsanaResource],
    ) -> None:
        """Validate that no entities have unsupported direct modifications.

        Per ADR-0043: Detection occurs in VALIDATE phase.
        Per FR-UNSUP-005: Detection occurs before any API calls.

        Raises:
            UnsupportedOperationError: If any entity has direct modifications
                to fields that require action endpoints.
        """
        for entity in entities:
            changes = self._tracker.get_changes(entity)

            for field_name in changes.keys():
                if field_name in self.UNSUPPORTED_FIELDS:
                    raise UnsupportedOperationError(field_name, entity)

    async def _execute_actions(
        self,
        actions: list[ActionOperation],
        gid_map: dict[str, str],
    ) -> SaveResult:
        """Execute action operations.

        Per FR-ACTION-011: Actions execute after CRUD.
        Per FR-ACTION-012: Resolves temp GIDs for newly created entities.

        Args:
            actions: List of action operations
            gid_map: Map of temp GIDs to real GIDs from CRUD phase

        Returns:
            SaveResult for action operations
        """
        if not actions:
            return SaveResult()

        succeeded: list[AsanaResource] = []
        failed: list[SaveError] = []

        for action in actions:
            # Resolve target entity GID (may be temp_xxx from newly created)
            target_gid = self._resolve_action_gid(action.target_entity, gid_map)

            # Resolve related entity GID
            related_gid = gid_map.get(action.related_entity_gid, action.related_entity_gid)

            try:
                await self._action_executor.execute(
                    action_type=action.action_type,
                    target_gid=target_gid,
                    related_gid=related_gid,
                    extra_params=action.extra_params,
                )
                succeeded.append(action.target_entity)

                # Emit post-save hook (using synthetic OperationType for compatibility)
                await self._events.emit_post_save(
                    action.target_entity,
                    OperationType.UPDATE,  # Actions are conceptually updates
                    {"action": action.action_type.value},
                )
            except Exception as e:
                failed.append(
                    SaveError(
                        entity=action.target_entity,
                        operation=OperationType.UPDATE,
                        error=e,
                        payload={"action": action.action_type.value, "related": related_gid},
                    )
                )
                await self._events.emit_error(
                    action.target_entity,
                    OperationType.UPDATE,
                    e,
                )

        return SaveResult(succeeded=succeeded, failed=failed)

    def _resolve_action_gid(
        self,
        entity: AsanaResource,
        gid_map: dict[str, str],
    ) -> str:
        """Resolve entity to GID, checking gid_map for temp GIDs."""
        if entity.gid and not entity.gid.startswith("temp_"):
            return entity.gid

        temp_gid = f"temp_{id(entity)}"
        if temp_gid in gid_map:
            return gid_map[temp_gid]

        # Entity may have been updated with real GID during CRUD phase
        if entity.gid and not entity.gid.startswith("temp_"):
            return entity.gid

        raise ValueError(f"Cannot resolve GID for {type(entity).__name__}")

    def _build_gid_map(
        self,
        all_entities: list[AsanaResource],
        succeeded: list[AsanaResource],
    ) -> dict[str, str]:
        """Build map from temp GIDs to real GIDs."""
        gid_map: dict[str, str] = {}

        for entity in succeeded:
            temp_gid = f"temp_{id(entity)}"
            if entity.gid and not entity.gid.startswith("temp_"):
                gid_map[temp_gid] = entity.gid

        return gid_map
```

#### ActionExecutor (New Component)

```python
# autom8_asana/persistence/action_executor.py

"""Action executor for non-batched action endpoints.

Per ADR-0042: Action operations are not batch-eligible and require
individual API calls.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from autom8_asana.persistence.models import ActionType

if TYPE_CHECKING:
    from autom8_asana.transport.http import HttpClient


class ActionExecutor:
    """Executes action endpoint API calls.

    Per FR-ACTION-011: Executes after CRUD operations.
    Per Asana API: Action endpoints are not batch-eligible.

    Each action type maps to a specific Asana endpoint:
    - ADD_TAG: POST /tasks/{task_gid}/addTag
    - REMOVE_TAG: POST /tasks/{task_gid}/removeTag
    - ADD_TO_PROJECT: POST /tasks/{task_gid}/addProject
    - REMOVE_FROM_PROJECT: POST /tasks/{task_gid}/removeProject
    - ADD_DEPENDENCY: POST /tasks/{task_gid}/addDependencies
    - REMOVE_DEPENDENCY: POST /tasks/{task_gid}/removeDependencies
    - MOVE_TO_SECTION: POST /sections/{section_gid}/addTask
    """

    def __init__(self, http_client: HttpClient) -> None:
        """Initialize executor with HTTP client.

        Args:
            http_client: The HTTP client for making API calls
        """
        self._http = http_client

    async def execute(
        self,
        action_type: ActionType,
        target_gid: str,
        related_gid: str,
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an action operation.

        Args:
            action_type: Type of action to perform
            target_gid: GID of the primary entity (usually task)
            related_gid: GID of the related entity (tag, project, etc.)
            extra_params: Additional parameters (e.g., section for add_to_project)

        Returns:
            API response data

        Raises:
            AsanaError: If API call fails
        """
        extra = extra_params or {}

        match action_type:
            case ActionType.ADD_TAG:
                return await self._add_tag(target_gid, related_gid)

            case ActionType.REMOVE_TAG:
                return await self._remove_tag(target_gid, related_gid)

            case ActionType.ADD_TO_PROJECT:
                section_gid = extra.get("section")
                return await self._add_to_project(target_gid, related_gid, section_gid)

            case ActionType.REMOVE_FROM_PROJECT:
                return await self._remove_from_project(target_gid, related_gid)

            case ActionType.ADD_DEPENDENCY:
                return await self._add_dependency(target_gid, related_gid)

            case ActionType.REMOVE_DEPENDENCY:
                return await self._remove_dependency(target_gid, related_gid)

            case ActionType.MOVE_TO_SECTION:
                return await self._move_to_section(target_gid, related_gid)

            case _:
                raise ValueError(f"Unknown action type: {action_type}")

    async def _add_tag(self, task_gid: str, tag_gid: str) -> dict[str, Any]:
        """POST /tasks/{task_gid}/addTag"""
        return await self._http.post(
            f"/tasks/{task_gid}/addTag",
            data={"tag": tag_gid},
        )

    async def _remove_tag(self, task_gid: str, tag_gid: str) -> dict[str, Any]:
        """POST /tasks/{task_gid}/removeTag"""
        return await self._http.post(
            f"/tasks/{task_gid}/removeTag",
            data={"tag": tag_gid},
        )

    async def _add_to_project(
        self,
        task_gid: str,
        project_gid: str,
        section_gid: str | None = None,
    ) -> dict[str, Any]:
        """POST /tasks/{task_gid}/addProject"""
        data: dict[str, Any] = {"project": project_gid}
        if section_gid:
            data["section"] = section_gid

        return await self._http.post(
            f"/tasks/{task_gid}/addProject",
            data=data,
        )

    async def _remove_from_project(
        self,
        task_gid: str,
        project_gid: str,
    ) -> dict[str, Any]:
        """POST /tasks/{task_gid}/removeProject"""
        return await self._http.post(
            f"/tasks/{task_gid}/removeProject",
            data={"project": project_gid},
        )

    async def _add_dependency(
        self,
        task_gid: str,
        dependency_gid: str,
    ) -> dict[str, Any]:
        """POST /tasks/{task_gid}/addDependencies"""
        return await self._http.post(
            f"/tasks/{task_gid}/addDependencies",
            data={"dependencies": [dependency_gid]},
        )

    async def _remove_dependency(
        self,
        task_gid: str,
        dependency_gid: str,
    ) -> dict[str, Any]:
        """POST /tasks/{task_gid}/removeDependencies"""
        return await self._http.post(
            f"/tasks/{task_gid}/removeDependencies",
            data={"dependencies": [dependency_gid]},
        )

    async def _move_to_section(
        self,
        task_gid: str,
        section_gid: str,
    ) -> dict[str, Any]:
        """POST /sections/{section_gid}/addTask

        Note: This endpoint uses section_gid in path, not task_gid.
        """
        return await self._http.post(
            f"/sections/{section_gid}/addTask",
            data={"task": task_gid},
        )
```

### Data Flow

#### Action Operation Flow Sequence

```
+---------------------------------------------------------------------------+
|                     ACTION OPERATION FLOW SEQUENCE                          |
+---------------------------------------------------------------------------+

  Client Code                                                       Asana API
       |                                                                |
       |  async with SaveSession(client) as session:                   |
       |      new_task = Task(gid="temp_1", name="New Task")           |
       |      session.track(new_task)                                   |
       |      session.add_tag(new_task, priority_tag)                   |
       |      session.add_to_project(new_task, project_a)               |
       |      await session.commit_async()                              |
       |                                                                |
       v                                                                |
  +----------+                                                          |
  |SaveSession|                                                         |
  +----+-----+                                                          |
       |                                                                |
       | 1. _pending_actions = [                                        |
       |      ActionOperation(ADD_TAG, new_task, "tag_gid"),           |
       |      ActionOperation(ADD_TO_PROJECT, new_task, "proj_gid")    |
       |    ]                                                           |
       |                                                                |
       | 2. commit_async()                                              |
       |    - dirty_entities = [new_task]                               |
       |    - pipeline.execute(entities, actions)                       |
       v                                                                |
  +------------+                                                        |
  |SavePipeline |                                                       |
  +-----+------+                                                        |
        |                                                               |
        | Phase 0: VALIDATE                                             |
        | 3. _validate_no_unsupported_changes()                         |
        |    - Check changes for tags/projects/memberships/dependencies |
        |    - No unsupported changes found, continue                   |
        |                                                               |
        | Phase 1-3: CRUD EXECUTION                                     |
        | 4. Execute new_task creation via BatchClient                  |
        v                                                               |
  +-------------+                                                       |
  |BatchExecutor|                                                       |
  +------+------+                                                       |
         |                                                              |
         | 5. POST /tasks (via batch) -> {gid: "123", name: "New Task"}|
         +-------------------------------------------------------------->|
         |                                                              |
         |<--------------------------------------------------------------+
         | Response: gid="123"                                          |
         |                                                              |
         | 6. new_task.gid = "123"                                      |
         | 7. gid_map = {"temp_xxx": "123"}                             |
         v                                                              |
  +------------+                                                        |
  |SavePipeline |                                                       |
  +-----+------+                                                        |
        |                                                               |
        | Phase 4: ACTION EXECUTION                                     |
        | 8. _execute_actions(actions, gid_map)                         |
        |    - Resolve new_task GID: temp_xxx -> "123"                  |
        v                                                               |
  +---------------+                                                     |
  |ActionExecutor |                                                     |
  +-------+-------+                                                     |
          |                                                             |
          | 9. ADD_TAG: POST /tasks/123/addTag {tag: "tag_gid"}        |
          +------------------------------------------------------------->|
          |                                                             |
          |<-------------------------------------------------------------+
          | 10. Response: {}                                            |
          |                                                             |
          | 11. ADD_TO_PROJECT: POST /tasks/123/addProject {project: ..}|
          +------------------------------------------------------------->|
          |                                                             |
          |<-------------------------------------------------------------+
          | 12. Response: {}                                            |
          v                                                             |
  +------------+                                                        |
  |SavePipeline |                                                       |
  +-----+------+                                                        |
        |                                                               |
        | Phase 5: CONFIRM                                              |
        | 13. Build SaveResult(succeeded=[new_task], failed=[])         |
        v                                                               |
  +----------+                                                          |
  |SaveSession|                                                         |
  +----+-----+                                                          |
       |                                                                |
       | 14. Clear _pending_actions                                     |
       | 15. Mark new_task as clean                                     |
       | 16. Return SaveResult                                          |
       v                                                                |
  Client Code                                                           |
```

#### Unsupported Operation Detection Flow

```
+---------------------------------------------------------------------------+
|                  UNSUPPORTED OPERATION DETECTION FLOW                       |
+---------------------------------------------------------------------------+

  Client Code
       |
       |  async with SaveSession(client) as session:
       |      task = await client.tasks.get_async("123")
       |      session.track(task)
       |
       |      # WRONG: Direct modification of tags
       |      task.tags.append(NameGid(gid="456", name="Priority"))
       |
       |      await session.commit_async()
       |
       v
  +----------+
  |SaveSession|
  +----+-----+
       |
       | 1. commit_async()
       |    - dirty_entities = [task]
       |    - pipeline.execute(entities, [])
       v
  +------------+
  |SavePipeline |
  +-----+------+
        |
        | Phase 0: VALIDATE
        | 2. _validate_no_unsupported_changes([task])
        |
        | 3. tracker.get_changes(task)
        |    returns: {"tags": (old_tags, new_tags)}
        |
        | 4. "tags" in UNSUPPORTED_FIELDS? YES
        |
        | 5. raise UnsupportedOperationError("tags", task)
        |
        v
  +-----------------------------+
  |UnsupportedOperationError    |
  |                             |
  | "Direct modification of     |
  |  'tags' on Task(gid=123)    |
  |  is not supported. Use      |
  |  session.add_tag() or       |
  |  session.remove_tag()       |
  |  instead."                  |
  +-----------------------------+
        |
        v
  Client Code (exception raised)
```

### Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Action type modeling | Separate `ActionType` enum | Clear separation of CRUD vs action operations | [ADR-0042](../decisions/ADR-0042-action-operation-types.md) |
| Unsupported detection location | VALIDATE phase in SavePipeline | Single validation point for preview and execute | [ADR-0043](../decisions/ADR-0043-unsupported-operation-detection.md) |
| Action execution timing | After CRUD, sequential | Entity must exist; actions not batch-eligible | Per Asana API |
| GID resolution for actions | Use CRUD gid_map | Temp GIDs resolved during CRUD phase | Per TDD-0010 pattern |
| Fluent API | Return self from action methods | Ergonomic chaining per FR-ACTION-009 | Common Python pattern |

## Complexity Assessment

**Level**: SERVICE

**Justification**:

This extension maintains the SERVICE level complexity of TDD-0010:

1. **New component**: ActionExecutor is a focused component with single responsibility
2. **Minimal coupling**: Action methods on SaveSession delegate to existing pipeline
3. **Clear boundaries**: Validation, CRUD execution, and action execution are distinct phases
4. **Reuses infrastructure**: Leverages existing ChangeTracker, BatchExecutor patterns

**Not escalated to PLATFORM because**:
- Extension of existing layer, not new service
- No new infrastructure requirements
- No cross-service coordination

## Implementation Plan

### Phase 1: Data Models and Exceptions (1.5 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `ActionType` enum in `models.py` | None | 0.25h |
| `ActionOperation` dataclass in `models.py` | ActionType | 0.25h |
| `UnsupportedOperationError` in `exceptions.py` | None | 0.5h |
| Unit tests for new types | Above | 0.5h |

**Exit Criteria**: Types pass mypy strict; unit tests cover all action types and error messages.

### Phase 2: ActionExecutor (2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `action_executor.py` - ActionExecutor class | ActionType, HttpClient | 1.5h |
| Unit tests with mocked HttpClient | action_executor.py | 0.5h |

**Exit Criteria**: All 7 action methods tested; correct endpoint paths verified.

### Phase 3: SavePipeline Extensions (2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `_validate_no_unsupported_changes()` method | ChangeTracker | 0.5h |
| `_execute_actions()` method | ActionExecutor | 1h |
| Unit tests for validation and execution | pipeline.py | 0.5h |

**Exit Criteria**: Validation detects all 4 unsupported fields; action execution works with GID resolution.

### Phase 4: SaveSession Extensions (2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| 7 action methods on SaveSession | ActionOperation, pipeline | 1h |
| Helper methods (`_resolve_entity`, `_resolve_gid`) | Task model | 0.25h |
| Extended `preview()` method | pipeline.preview | 0.25h |
| Unit tests for action methods | session.py | 0.5h |

**Exit Criteria**: Fluent chaining works; preview includes actions; GID and entity resolution works.

### Phase 5: Integration Testing (2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| End-to-end tests: action operations with mock API | All components | 1h |
| Edge cases: temp GID resolution, partial failures | All components | 0.5h |
| Unsupported modification tests for all 4 fields | All components | 0.5h |

**Exit Criteria**: All PRD requirements have test coverage; existing 327 tests still pass.

### Phase 6: Custom Field Persistence Tests (1 hour)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Tests for 6 custom field types (per FR-CF-*) | Existing pipeline | 1h |

**Exit Criteria**: CREATE and UPDATE tests for text, number, enum, multi-enum, date, people fields.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| R-001: Action execution increases API calls | Medium | High | Document limitation; group related actions |
| R-002: Temp GID resolution fails for actions | High | Low | Comprehensive GID map building; clear error on failure |
| R-003: Breaking change from strict validation | Medium | Medium | Clear error messages with guidance; migration notes |
| R-004: Event hooks incompatible with actions | Low | Low | Use synthetic OperationType.UPDATE for hooks |
| R-005: Move_to_section endpoint path differs | Medium | Low | Special handling in ActionExecutor; tested explicitly |

## Observability

### Metrics

All metrics emitted via SDK LogProvider:

| Metric | Type | Description |
|--------|------|-------------|
| `save_session_action_count` | Histogram | Action operations per commit |
| `save_session_action_type_count` | Counter (labeled) | Count by action type |
| `save_session_action_duration_ms` | Histogram | Time for action execution phase |
| `save_session_unsupported_errors` | Counter | Unsupported modification errors raised |

### Logging

| Level | Events |
|-------|--------|
| DEBUG | Action queued (type, target, related), action executed |
| INFO | Action phase start/complete with counts |
| WARNING | Action failed (with error) |
| ERROR | Unsupported modification detected |

### Log Examples

```python
# DEBUG: Action queued
logger.debug(
    "session_action_queued",
    action_type="add_tag",
    target_gid="temp_123",
    related_gid="456",
)

# INFO: Action phase complete
logger.info(
    "session_actions_complete",
    total=5,
    succeeded=4,
    failed=1,
    duration_ms=250,
)

# ERROR: Unsupported modification
logger.error(
    "session_unsupported_modification",
    field="tags",
    entity_type="Task",
    entity_gid="123",
)
```

## Testing Strategy

### Unit Testing (Target: 95% coverage for new code)

- **ActionType**: All enum values present
- **ActionOperation**: Dataclass creation, repr, equality
- **UnsupportedOperationError**: Message formatting for all 4 fields
- **ActionExecutor**: Correct endpoint paths, request bodies for all 7 actions
- **SavePipeline validation**: Detection for each unsupported field
- **SavePipeline action execution**: GID resolution, error handling
- **SaveSession action methods**: Fluent chaining, entity/GID resolution

### Integration Testing

- **End-to-end action flow**: Track -> action method -> commit -> verify API call
- **Action with new entity**: Create task, add tag, verify temp GID resolved
- **Multiple actions same entity**: Multiple add_tag calls, all executed
- **Unsupported detection**: Direct tags modification, error raised before API calls
- **Preview with actions**: Actions included in preview list

### Regression Testing

- **Existing 327 tests must pass**: No changes to CRUD behavior
- **Custom field tests**: All 6 field types work with existing pipeline

## Requirement Traceability

| Requirement | Implementation | Test |
|-------------|----------------|------|
| FR-ACTION-001 | `SaveSession.add_tag()` | `test_add_tag_queues_action` |
| FR-ACTION-002 | `SaveSession.remove_tag()` | `test_remove_tag_queues_action` |
| FR-ACTION-003 | `SaveSession.add_to_project()` | `test_add_to_project_queues_action` |
| FR-ACTION-004 | `SaveSession.remove_from_project()` | `test_remove_from_project_queues_action` |
| FR-ACTION-005 | `SaveSession.add_dependency()` | `test_add_dependency_queues_action` |
| FR-ACTION-006 | `SaveSession.remove_dependency()` | `test_remove_dependency_queues_action` |
| FR-ACTION-007 | `SaveSession.move_to_section()` | `test_move_to_section_queues_action` |
| FR-ACTION-008 | `_resolve_entity()`, `_resolve_gid()` | `test_action_accepts_entity_or_gid` |
| FR-ACTION-009 | Return `self` from action methods | `test_action_fluent_chaining` |
| FR-ACTION-010 | `_pending_actions` list | `test_actions_queued_until_commit` |
| FR-ACTION-011 | `_execute_actions()` after CRUD | `test_actions_execute_after_crud` |
| FR-ACTION-012 | GID resolution in `_execute_actions()` | `test_actions_resolve_temp_gids` |
| FR-UNSUP-001 | `UNSUPPORTED_FIELDS` includes "tags" | `test_detect_tags_modification` |
| FR-UNSUP-002 | `UNSUPPORTED_FIELDS` includes "projects" | `test_detect_projects_modification` |
| FR-UNSUP-003 | `UNSUPPORTED_FIELDS` includes "memberships" | `test_detect_memberships_modification` |
| FR-UNSUP-004 | `UNSUPPORTED_FIELDS` includes "dependencies" | `test_detect_dependencies_modification` |
| FR-UNSUP-005 | `_validate_no_unsupported_changes()` first | `test_validation_before_api_calls` |
| FR-UNSUP-006 | `UnsupportedOperationError.field_name` | `test_error_includes_field_name` |
| FR-UNSUP-007 | `UnsupportedOperationError.suggested_methods` | `test_error_includes_suggestions` |
| FR-PREV-001 | Actions in `preview()` return | `test_preview_includes_actions` |
| FR-PREV-002 | Actions after CRUD in preview | `test_preview_actions_after_crud` |
| FR-PREV-003 | Validation in preview | `test_preview_detects_unsupported` |
| FR-EXC-001 | `UnsupportedOperationError` class | `test_exception_exists` |
| FR-EXC-002 | Inherits `SaveOrchestrationError` | `test_exception_hierarchy` |
| FR-EXC-003 | `field_name` attribute | `test_exception_field_name` |
| FR-EXC-004 | `suggested_methods` attribute | `test_exception_suggested_methods` |

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should action failures affect CRUD success tracking? | Architect | Phase 5 | Document as separate result category |
| Should rollback be attempted for failed actions? | Architect | Phase 5 | No rollback per existing semantics |
| Should preview validate related entity GIDs exist? | Architect | Phase 4 | No, would require API calls |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-10 | Architect | Initial design with action operations and unsupported detection |
