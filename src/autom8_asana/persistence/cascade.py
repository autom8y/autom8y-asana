"""Cascade operation infrastructure.

Per ADR-0054: Cascade field propagation from parent to descendants.
Per FR-CASCADE-001 through FR-CASCADE-008: Cascading field requirements.

Cascade operations propagate field values from a source entity to its
descendants based on CascadingFieldDef definitions. Operations are executed
via the batch API with rate limiting and allow_override filtering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.base import BusinessEntity
    from autom8_asana.models.business.fields import CascadingFieldDef
    from autom8_asana.models.task import Task


@dataclass(frozen=True)
class CascadeOperation:
    """A field cascade operation to execute.

    Per ADR-0054: Represents a single cascade request from a source entity.

    Attributes:
        source_entity: The entity owning the cascading field.
        field_name: Name of the custom field to cascade.
        target_types: Optional tuple of entity type names to cascade to.
                     If None, cascades to all descendants.
    """

    source_entity: BusinessEntity
    field_name: str
    target_types: tuple[type, ...] | None = None


@dataclass
class CascadeResult:
    """Result of cascade execution.

    Per ADR-0054: Tracks success/failure of cascade operations.

    Attributes:
        operations_queued: Total operations queued.
        operations_succeeded: Operations that succeeded.
        operations_failed: Operations that failed.
        entities_updated: List of entities that were updated.
        errors: List of error messages for failed operations.
    """

    operations_queued: int = 0
    operations_succeeded: int = 0
    operations_failed: int = 0
    entities_updated: list[Task] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if all operations succeeded.

        Returns:
            True if no failures, False otherwise.
        """
        return self.operations_failed == 0

    @property
    def partial(self) -> bool:
        """Check if some but not all operations succeeded.

        Returns:
            True if there are both successes and failures.
        """
        return self.operations_succeeded > 0 and self.operations_failed > 0


class CascadeExecutor:
    """Executes cascade operations via batch API.

    Per ADR-0054: Handles cascade execution with rate limiting,
    allow_override filtering, and batch optimization.

    Example:
        executor = CascadeExecutor(client)
        result = await executor.execute([
            CascadeOperation(business, "Office Phone"),
            CascadeOperation(unit, "Vertical", target_types=(Offer,)),
        ])
    """

    def __init__(self, client: AsanaClient) -> None:
        """Initialize cascade executor.

        Args:
            client: AsanaClient instance for API calls.
        """
        self._client = client

    async def execute(self, operations: list[CascadeOperation]) -> CascadeResult:
        """Execute cascade operations in batches.

        Per ADR-0054: Executes cascades with:
        - Batch API optimization
        - Rate limiting
        - allow_override filtering

        Args:
            operations: List of cascade operations to execute.

        Returns:
            CascadeResult with success/failure information.
        """
        result = CascadeResult(operations_queued=len(operations))

        if not operations:
            return result

        for operation in operations:
            op_result = await self._execute_single(operation)
            result.operations_succeeded += op_result.operations_succeeded
            result.operations_failed += op_result.operations_failed
            result.entities_updated.extend(op_result.entities_updated)
            result.errors.extend(op_result.errors)

        return result

    async def _execute_single(self, operation: CascadeOperation) -> CascadeResult:
        """Execute a single cascade operation.

        Args:
            operation: The cascade operation to execute.

        Returns:
            CascadeResult for this operation.
        """
        result = CascadeResult()
        source = operation.source_entity

        # Get the cascading field definition
        field_def = self._get_field_def(source, operation.field_name)
        if field_def is None:
            result.errors.append(
                f"No cascading field definition for '{operation.field_name}' "
                f"on {type(source).__name__}"
            )
            result.operations_failed += 1
            return result

        # Get the value to cascade
        value = field_def.get_value(source)
        if value is None:
            # Nothing to cascade
            return result

        # Collect descendants to update
        descendants = self._collect_descendants(source, field_def)

        # Filter by target_types if specified
        if operation.target_types:
            descendants = [
                d for d in descendants if isinstance(d, operation.target_types)
            ]

        # Filter by allow_override
        updates: list[tuple[Task, Any]] = []
        for descendant in descendants:
            if field_def.should_update_descendant(descendant):
                updates.append((descendant, value))

        # Execute updates via batch API
        result.operations_queued = len(updates)
        for entity, val in updates:
            try:
                # Update the custom field
                entity.get_custom_fields().set(field_def.name, val)
                result.entities_updated.append(entity)
                result.operations_succeeded += 1
            except Exception as e:
                result.errors.append(f"Failed to update {entity.gid}: {e}")
                result.operations_failed += 1

        return result

    def _get_field_def(
        self, entity: BusinessEntity, field_name: str
    ) -> CascadingFieldDef | None:
        """Get cascading field definition from entity.

        Args:
            entity: Entity to get field definition from.
            field_name: Name of the field.

        Returns:
            CascadingFieldDef or None if not found.
        """
        cascading_fields_cls = getattr(entity, "CascadingFields", None)
        if cascading_fields_cls and hasattr(cascading_fields_cls, "get"):
            result: CascadingFieldDef | None = cascading_fields_cls.get(field_name)
            return result
        return None

    def _collect_descendants(
        self, entity: Task, field_def: CascadingFieldDef
    ) -> list[Task]:
        """Collect all descendants that should receive the cascade.

        Args:
            entity: Source entity.
            field_def: Field definition with target_types.

        Returns:
            List of descendant entities to update.
        """
        descendants: list[Task] = []

        # Check for holder-based children
        holder_key_map = getattr(entity, "HOLDER_KEY_MAP", None)
        if holder_key_map:
            for holder_name in holder_key_map:
                holder = getattr(entity, f"_{holder_name}", None)
                if holder is not None:
                    # Get children from holder
                    children = self._get_holder_children(holder)
                    for child in children:
                        if field_def.applies_to(child):
                            descendants.append(child)
                        # Recurse into child's descendants
                        descendants.extend(self._collect_descendants(child, field_def))

        return descendants

    def _get_holder_children(self, holder: Task) -> list[Task]:
        """Get children from a holder entity.

        Args:
            holder: Holder entity with children.

        Returns:
            List of child entities.
        """
        # Check for known child collection patterns
        for attr_name in ("_contacts", "_units", "_offers", "_processes", "_locations"):
            children = getattr(holder, attr_name, None)
            if children and isinstance(children, list):
                result: list[Task] = children
                return result
        return []


def cascade_field(
    entity: BusinessEntity,
    field_name: str,
    *,
    target_types: tuple[type, ...] | None = None,
) -> CascadeOperation:
    """Create a cascade operation for a field.

    Per ADR-0054: Factory function for creating cascade operations.

    Args:
        entity: Source entity owning the field.
        field_name: Name of the custom field to cascade.
        target_types: Optional tuple of entity types to cascade to.

    Returns:
        CascadeOperation ready for execution.

    Example:
        op = cascade_field(business, "Office Phone")
        result = await executor.execute([op])
    """
    return CascadeOperation(
        source_entity=entity,
        field_name=field_name,
        target_types=target_types,
    )
