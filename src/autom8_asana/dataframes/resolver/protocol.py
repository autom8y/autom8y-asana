"""CustomFieldResolver Protocol for dynamic field resolution.

Per ADR-0034: Defines the protocol for resolving schema field names
to Asana custom field GIDs using the task's existing custom_fields list.

Per ADR-0001: Uses Protocol for structural subtyping without inheritance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import ColumnDef
    from autom8_asana.models.custom_field import CustomField
    from autom8_asana.models.task import Task


@runtime_checkable
class CustomFieldResolver(Protocol):
    """Protocol for custom field name resolution.

    Per ADR-0034: Resolves schema field names to custom field GIDs
    using the task's existing custom_fields list.

    Implementations:
        - DefaultCustomFieldResolver: Production implementation
        - MockCustomFieldResolver: Testing implementation

    Example:
        >>> resolver = DefaultCustomFieldResolver()
        >>> resolver.build_index(task.custom_fields)
        >>> gid = resolver.resolve("cf:MRR")
        >>> value = resolver.get_value(task, "cf:MRR")
    """

    def build_index(self, custom_fields: list[CustomField]) -> None:
        """Build name->gid index from custom fields.

        Called once with the first task's custom_fields to build
        the resolution index for the session. Subsequent calls
        are no-ops (idempotent).

        Args:
            custom_fields: List of CustomField objects from task

        Thread-Safety:
            Must be thread-safe for concurrent calls.
        """
        ...

    def resolve(self, field_name: str) -> str | None:
        """Resolve field name to custom field GID.

        Handles prefixes:
            - "cf:Name" -> resolve "Name" by normalized lookup
            - "gid:123" -> return "123" directly (bypass resolution)
            - "name" -> resolve "name" by normalized lookup

        Args:
            field_name: Schema field name (snake_case) or cf: prefixed name

        Returns:
            GID if found, None if not resolvable
        """
        ...

    def get_value(
        self,
        task: Task,
        field_name: str,
        *,
        column_def: ColumnDef | None = None,
    ) -> Any:
        """Extract custom field value from task.

        Args:
            task: Task to extract value from
            field_name: Schema field name (with optional prefix)
            column_def: Optional column definition for schema-aware coercion

        Returns:
            Extracted and optionally coerced value, or None if:
            - Field cannot be resolved
            - Field not present on task
            - Value is null

        Note:
            When column_def is provided, its dtype is used for coercion.

        Raises:
            KeyError: If strict mode enabled and field not found
        """
        ...

    def has_field(self, field_name: str) -> bool:
        """Check if field is resolvable.

        Args:
            field_name: Schema field name (with optional prefix)

        Returns:
            True if field can be resolved to a GID
        """
        ...
