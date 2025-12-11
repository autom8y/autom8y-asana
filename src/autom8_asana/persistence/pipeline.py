"""Save pipeline orchestrating the four-phase execution.

Per TDD-0010: Four-phase save orchestration:
1. VALIDATE: Cycle detection
2. PREPARE: Build operations, assign temp GIDs
3. EXECUTE: Execute per dependency level
4. CONFIRM: Resolve GIDs, update entities

Per TDD-0011: Extended five-phase execution with actions:
1. VALIDATE: Cycle detection + unsupported field validation
2. PREPARE: Build operations, assign temp GIDs
3. EXECUTE: Execute CRUD via BatchExecutor
4. ACTIONS: Execute action operations via ActionExecutor
5. CONFIRM: Resolve GIDs, update entities
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from autom8_asana.persistence.models import (
    EntityState,
    OperationType,
    PlannedOperation,
    SaveResult,
    SaveError,
    ActionOperation,
    ActionResult,
)
from autom8_asana.persistence.exceptions import (
    DependencyResolutionError,
    UnsupportedOperationError,
)
from autom8_asana.persistence.executor import BatchExecutor

if TYPE_CHECKING:
    from autom8_asana.batch.client import BatchClient
    from autom8_asana.models.base import AsanaResource
    from autom8_asana.persistence.tracker import ChangeTracker
    from autom8_asana.persistence.graph import DependencyGraph
    from autom8_asana.persistence.events import EventSystem
    from autom8_asana.persistence.action_executor import ActionExecutor


# Fields that cannot be directly modified via PUT/PATCH
# Per TDD-0011: These require action endpoints instead
# Per TDD-0012: Extended with followers and dependents fields
UNSUPPORTED_FIELDS: dict[str, list[str]] = {
    "tags": ["add_tag()", "remove_tag()"],
    "projects": ["add_to_project()", "remove_from_project()"],
    "memberships": ["add_to_project()", "remove_from_project()"],
    "dependencies": ["add_dependency()", "remove_dependency()"],
    "dependents": ["add_dependent()", "remove_dependent()"],
    "followers": ["add_follower()", "remove_follower()"],
}


class SavePipeline:
    """Orchestrates the save operation through phases.

    Per TDD component design: Four-phase execution.

    Phases:
    1. VALIDATE: Cycle detection, required field validation
    2. PREPARE: Build BatchRequests, assign temp GIDs
    3. EXECUTE: Execute batches per dependency level
    4. CONFIRM: Resolve GIDs, update entities, clear dirty state

    The pipeline processes entities level-by-level according to their
    dependency order. Entities at level 0 have no dependencies and are
    saved first. Entities at level N depend only on entities at levels < N.

    Partial failures are handled per ADR-0040: commit successful operations,
    report failures. Entities whose dependencies failed are marked as
    cascading failures.

    Example:
        pipeline = SavePipeline(tracker, graph, events, batch_client)

        # Preview without executing
        planned = pipeline.preview(entities)

        # Execute with full pipeline
        result = await pipeline.execute(entities)
        if result.success:
            print("All saved successfully")
        else:
            print(f"Partial failure: {len(result.failed)} failed")
    """

    def __init__(
        self,
        tracker: ChangeTracker,
        graph: DependencyGraph,
        events: EventSystem,
        batch_client: BatchClient,
        batch_size: int = 10,
    ) -> None:
        """Initialize pipeline with required components.

        Args:
            tracker: ChangeTracker for determining entity state and changes.
            graph: DependencyGraph for building dependency order.
            events: EventSystem for hook emission.
            batch_client: BatchClient for API execution.
            batch_size: Maximum operations per batch (default: 10).
        """
        self._tracker = tracker
        self._graph = graph
        self._events = events
        self._executor = BatchExecutor(batch_client, batch_size)

    def preview(
        self,
        entities: list[AsanaResource],
    ) -> list[PlannedOperation]:
        """Preview operations without executing.

        Per FR-DRY-001 through FR-DRY-005.

        Builds the dependency graph, validates for cycles, and returns
        a list of planned operations in execution order. No API calls
        are made.

        Args:
            entities: List of entities to preview operations for.

        Returns:
            List of PlannedOperation in execution order.

        Raises:
            CyclicDependencyError: If dependency cycle detected.
        """
        if not entities:
            return []

        # Build graph and validate (raises CyclicDependencyError if cycle)
        self._graph.build(entities)
        levels = self._graph.get_levels()

        operations: list[PlannedOperation] = []

        for level_idx, level_entities in enumerate(levels):
            for entity in level_entities:
                op_type = self._determine_operation(entity)
                payload = self._build_payload(entity, op_type)

                operations.append(
                    PlannedOperation(
                        entity=entity,
                        operation=op_type,
                        payload=payload,
                        dependency_level=level_idx,
                    )
                )

        return operations

    async def execute(
        self,
        entities: list[AsanaResource],
    ) -> SaveResult:
        """Execute all pending changes.

        Per FR-BATCH-001 through FR-BATCH-009.
        Per FR-ERROR-001: Commit successful, report failures.

        Executes the four-phase pipeline:
        1. VALIDATE: Build graph, detect cycles
        2. PREPARE: Build operations per level
        3. EXECUTE: Execute via BatchExecutor
        4. CONFIRM: Update GIDs, emit hooks

        Args:
            entities: List of entities to save.

        Returns:
            SaveResult with succeeded and failed lists.

        Raises:
            CyclicDependencyError: If dependency cycle detected.
        """
        if not entities:
            return SaveResult()

        # Phase 1: VALIDATE - build graph and detect cycles
        self._graph.build(entities)
        levels = self._graph.get_levels()

        # Track overall results
        all_succeeded: list[AsanaResource] = []
        all_failed: list[SaveError] = []

        # Track GID resolutions for placeholder replacement
        # Maps temp_xxx -> real_gid
        gid_map: dict[str, str] = {}

        # Track failed dependencies for cascading errors
        failed_gids: set[str] = set()

        # Phases 2-4: Process each level
        for level_entities in levels:
            # Filter out entities whose dependencies failed
            executable, cascaded_failures = self._filter_executable(
                level_entities,
                failed_gids,
                entities,
            )

            # Add cascading failures to result
            all_failed.extend(cascaded_failures)
            for failure in cascaded_failures:
                failed_gids.add(self._get_entity_gid(failure.entity))

            if not executable:
                continue

            # Phase 2: PREPARE operations for this level
            operations = self._prepare_operations(executable, gid_map)

            # Emit pre-save hooks (can raise to abort)
            for entity, op_type, _ in operations:
                await self._events.emit_pre_save(entity, op_type)

            # Phase 3: EXECUTE
            level_results = await self._executor.execute_level(operations)

            # Phase 4: CONFIRM - process results
            for entity, op_type, batch_result in level_results:
                if batch_result.success:
                    all_succeeded.append(entity)

                    # Update GID map for new entities
                    if op_type == OperationType.CREATE and batch_result.data:
                        temp_gid = f"temp_{id(entity)}"
                        real_gid = batch_result.data.get("gid")
                        if real_gid:
                            gid_map[temp_gid] = real_gid
                            # Update entity GID in place
                            object.__setattr__(entity, "gid", real_gid)

                    # Emit post-save hook
                    await self._events.emit_post_save(
                        entity, op_type, batch_result.data
                    )
                else:
                    # Find the payload for this entity
                    payload = self._find_payload_for_entity(entity, operations)
                    error = batch_result.error or Exception("Unknown batch error")
                    all_failed.append(
                        SaveError(
                            entity=entity,
                            operation=op_type,
                            error=error,
                            payload=payload,
                        )
                    )
                    failed_gids.add(self._get_entity_gid(entity))

                    # Emit error hook
                    await self._events.emit_error(entity, op_type, error)

        return SaveResult(succeeded=all_succeeded, failed=all_failed)

    def _filter_executable(
        self,
        level_entities: list[AsanaResource],
        failed_gids: set[str],
        all_entities: list[AsanaResource],
    ) -> tuple[list[AsanaResource], list[SaveError]]:
        """Filter entities whose dependencies haven't failed.

        Args:
            level_entities: Entities at this dependency level.
            failed_gids: Set of GIDs that have failed.
            all_entities: All entities for dependency lookup.

        Returns:
            Tuple of (executable entities, cascading failures).
        """
        executable: list[AsanaResource] = []
        cascaded: list[SaveError] = []

        for entity in level_entities:
            parent_gid = self._get_parent_gid(entity)

            if parent_gid and parent_gid in failed_gids:
                # Dependency failed - mark as cascading failure
                parent_entity = self._find_entity_by_gid(parent_gid, all_entities)
                error = DependencyResolutionError(
                    entity=entity,
                    dependency=parent_entity,
                    cause=Exception("Parent save failed"),
                )
                cascaded.append(
                    SaveError(
                        entity=entity,
                        operation=self._determine_operation(entity),
                        error=error,
                        payload={},
                    )
                )
            else:
                executable.append(entity)

        return executable, cascaded

    def _determine_operation(
        self,
        entity: AsanaResource,
    ) -> OperationType:
        """Determine operation type for entity based on its state.

        Args:
            entity: The entity to determine operation for.

        Returns:
            OperationType (CREATE, UPDATE, or DELETE).
        """
        state = self._tracker.get_state(entity)

        if state == EntityState.NEW:
            return OperationType.CREATE
        elif state == EntityState.DELETED:
            return OperationType.DELETE
        else:
            return OperationType.UPDATE

    def _build_payload(
        self,
        entity: AsanaResource,
        op_type: OperationType,
    ) -> dict[str, Any]:
        """Build API payload for entity.

        Per FR-CHANGE-006: Generate minimal payloads for updates.

        For CREATE operations, builds a full payload with all non-None fields.
        For UPDATE operations, only includes changed fields.
        For DELETE operations, returns empty dict.

        Args:
            entity: The entity to build payload for.
            op_type: The type of operation.

        Returns:
            Dict payload for the API request.
        """
        if op_type == OperationType.DELETE:
            return {}

        if op_type == OperationType.CREATE:
            # Full payload for creates, excluding gid and resource_type
            # which are generated by the API
            data = entity.model_dump(
                exclude_none=True,
                exclude={"gid", "resource_type"},
            )
            # Convert NameGid objects to GID strings for API
            return self._convert_references_to_gids(data)

        # For updates, only changed fields
        changed_fields = self._tracker.get_changed_fields(entity)
        return self._convert_references_to_gids(changed_fields)

    def _convert_references_to_gids(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert object references to GID strings for API.

        Args:
            data: The payload data.

        Returns:
            Data with object references converted to GID strings.
        """
        result: dict[str, Any] = {}

        for key, value in data.items():
            if value is None:
                result[key] = value
            elif hasattr(value, "gid"):
                # Convert NameGid or other reference to GID string
                result[key] = value.gid
            elif isinstance(value, list):
                # Handle lists of references (e.g., projects)
                converted: list[Any] = []
                for item in value:
                    if hasattr(item, "gid"):
                        converted.append(item.gid)
                    else:
                        converted.append(item)
                result[key] = converted
            else:
                result[key] = value

        return result

    def _prepare_operations(
        self,
        entities: list[AsanaResource],
        gid_map: dict[str, str],
    ) -> list[tuple[AsanaResource, OperationType, dict[str, Any]]]:
        """Prepare operations with GID resolution.

        Per FR-DEPEND-004: Resolve placeholder GIDs.

        Builds the operation tuple for each entity and resolves
        any placeholder GIDs (temp_xxx) to their real values from
        previous levels.

        Args:
            entities: Entities to prepare operations for.
            gid_map: Map of temp GIDs to real GIDs from previous levels.

        Returns:
            List of (entity, operation_type, payload) tuples.
        """
        operations: list[tuple[AsanaResource, OperationType, dict[str, Any]]] = []

        for entity in entities:
            op_type = self._determine_operation(entity)
            payload = self._build_payload(entity, op_type)

            # Resolve parent GID if it was a temp GID
            if "parent" in payload:
                parent_ref = payload["parent"]
                if isinstance(parent_ref, str) and parent_ref.startswith("temp_"):
                    if parent_ref in gid_map:
                        payload["parent"] = gid_map[parent_ref]

            operations.append((entity, op_type, payload))

        return operations

    def _get_parent_gid(self, entity: AsanaResource) -> str | None:
        """Get parent GID from entity.

        Args:
            entity: The entity to get parent GID from.

        Returns:
            Parent GID string or None if no parent.
        """
        parent = getattr(entity, "parent", None)
        if parent is None:
            return None
        if isinstance(parent, str):
            return parent
        if hasattr(parent, "gid"):
            gid: str | None = parent.gid
            if gid:
                return gid
        return None

    def _get_entity_gid(self, entity: AsanaResource) -> str:
        """Get GID or temp GID for entity.

        Args:
            entity: The entity to get GID for.

        Returns:
            Entity's GID or temp_{id} for new entities.
        """
        if entity.gid and not entity.gid.startswith("temp_"):
            return entity.gid
        return f"temp_{id(entity)}"

    def _find_entity_by_gid(
        self,
        gid: str,
        entities: list[AsanaResource],
    ) -> AsanaResource:
        """Find entity by GID or temp GID.

        Args:
            gid: The GID to search for.
            entities: List of entities to search.

        Returns:
            The matching entity, or first entity as fallback.
        """
        for entity in entities:
            if entity.gid == gid:
                return entity
            if f"temp_{id(entity)}" == gid:
                return entity
        # Fallback to first entity (should not happen in normal usage)
        return entities[0]

    def _find_payload_for_entity(
        self,
        entity: AsanaResource,
        operations: list[tuple[AsanaResource, OperationType, dict[str, Any]]],
    ) -> dict[str, Any]:
        """Find the payload for a specific entity in operations.

        Args:
            entity: The entity to find payload for.
            operations: List of (entity, op_type, payload) tuples.

        Returns:
            The payload for the entity, or empty dict if not found.
        """
        for op_entity, _, payload in operations:
            if op_entity is entity:
                return payload
        return {}

    # -----------------------------------------------------------------------
    # TDD-0011: Action Support
    # -----------------------------------------------------------------------

    def validate_no_unsupported_modifications(
        self,
        entities: list[AsanaResource],
    ) -> None:
        """Validate that no entities have unsupported field modifications.

        Per TDD-0011: Raise UnsupportedOperationError if any entity has
        modifications to fields that require action endpoints.

        Args:
            entities: List of entities to validate.

        Raises:
            UnsupportedOperationError: If any entity has unsupported modifications.
        """
        for entity in entities:
            state = self._tracker.get_state(entity)

            # Only check modified entities (not new or deleted)
            if state != EntityState.MODIFIED:
                continue

            changed_fields = self._tracker.get_changed_fields(entity)

            for field_name in changed_fields:
                if field_name in UNSUPPORTED_FIELDS:
                    raise UnsupportedOperationError(
                        field_name=field_name,
                        suggested_methods=UNSUPPORTED_FIELDS[field_name],
                    )

    async def execute_with_actions(
        self,
        entities: list[AsanaResource],
        actions: list[ActionOperation],
        action_executor: ActionExecutor,
    ) -> tuple[SaveResult, list[ActionResult]]:
        """Execute CRUD operations followed by action operations.

        Per TDD-0011: Extended five-phase execution:
        1. VALIDATE: Cycle detection + unsupported field validation
        2. PREPARE: Build operations, assign temp GIDs
        3. EXECUTE: Execute CRUD via BatchExecutor
        4. ACTIONS: Execute action operations via ActionExecutor
        5. CONFIRM: Build combined result

        Args:
            entities: List of entities with CRUD changes.
            actions: List of ActionOperation for relationship changes.
            action_executor: ActionExecutor for executing actions.

        Returns:
            Tuple of (SaveResult for CRUD, list of ActionResult for actions).

        Raises:
            CyclicDependencyError: If dependency cycle detected.
            UnsupportedOperationError: If entities have unsupported modifications.
        """
        # Phase 1: VALIDATE - check for unsupported modifications
        if entities:
            self.validate_no_unsupported_modifications(entities)

        # Execute CRUD operations (phases 2-4 of original pipeline)
        crud_result = await self.execute(entities)

        # Build GID map from CRUD results for action resolution
        gid_map: dict[str, str] = {}
        for entity in crud_result.succeeded:
            # Map temp GIDs to real GIDs
            temp_gid = f"temp_{id(entity)}"
            if entity.gid and not entity.gid.startswith("temp_"):
                gid_map[temp_gid] = entity.gid

        # Phase 4: ACTIONS - execute action operations
        action_results: list[ActionResult] = []
        if actions:
            action_results = await action_executor.execute_async(actions, gid_map)

        return crud_result, action_results
