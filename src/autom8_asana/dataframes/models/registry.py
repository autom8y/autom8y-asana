"""Singleton registry for task-type to schema mapping.

Per FR-MODEL-030 through FR-MODEL-033: Singleton with lazy initialization
and runtime registration support.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Callable, ClassVar

from autom8y_log import get_logger

from autom8_asana.dataframes.exceptions import SchemaNotFoundError, SchemaVersionError

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import DataFrameSchema


def get_schema(task_type: str) -> DataFrameSchema:
    """Convenience accessor: look up schema by task type.

    Equivalent to ``SchemaRegistry.get_instance().get_schema(task_type)``
    but avoids the ceremony of obtaining the singleton first.

    Args:
        task_type: Task type identifier (e.g., "Unit", "Contact", "*")

    Returns:
        DataFrameSchema for the task type

    Raises:
        SchemaNotFoundError: If no schema registered for type
    """
    return SchemaRegistry.get_instance().get_schema(task_type)


class SchemaRegistry:
    """Singleton registry for task-type to schema mapping (FR-MODEL-030-033).

    Per TDD-0009: Singleton with lazy initialization and runtime
    registration support. Thread-safe via lock.

    Usage:
        >>> registry = SchemaRegistry.get_instance()
        >>> schema = registry.get_schema("Unit")
        >>> schema.name
        'unit'

    Thread Safety:
        The registry is thread-safe. Schema registration and retrieval
        use a lock to prevent race conditions.
    """

    _instance: ClassVar[SchemaRegistry | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()
    _on_reset_callbacks: ClassVar[list[Callable[[], None]]] = []

    # Instance attributes (set in __new__)
    _schemas: dict[str, DataFrameSchema]
    _initialized: bool

    def __new__(cls) -> SchemaRegistry:
        """Create or return singleton instance."""
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._schemas = {}
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> SchemaRegistry:
        """Get or create singleton instance.

        Returns:
            The singleton SchemaRegistry instance
        """
        return cls()

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (for testing only).

        Warning:
            This method is intended for testing only. Do not use
            in production code.

        Note:
            Notifies subscribers via on_reset callbacks (e.g., resolver
            cache clearing) instead of importing private functions directly.
        """
        with cls._lock:
            cls._instance = None

        for callback in cls._on_reset_callbacks:
            callback()

    @classmethod
    def on_reset(cls, callback: Callable[[], None]) -> None:
        """Register a callback to be invoked when the registry is reset.

        Used by dependent modules to subscribe to reset events without
        creating cross-boundary private API imports.

        Args:
            callback: Zero-argument callable invoked on reset.
        """
        cls._on_reset_callbacks.append(callback)

    def _ensure_initialized(self) -> None:
        """Lazy initialization of built-in schemas.

        Per WS1-S2: Auto-wires schemas from EntityDescriptor registry instead
        of hardcoded imports. Each descriptor with a schema_module_path is
        resolved via _resolve_dotted_path() and keyed by effective_schema_key.
        BASE_SCHEMA remains hardcoded because "*" is not an entity type.

        Errors from _resolve_dotted_path() propagate -- a misconfigured
        descriptor must fail loudly at initialization time.
        """
        if self._initialized:
            return

        with self._lock:
            # Double-checked locking
            if self._initialized:
                return

            # Deferred import to avoid circular dependency:
            # dataframes/ must not import core.entity_registry at module scope
            from autom8_asana.core.entity_registry import (
                _resolve_dotted_path,
                get_registry,
            )

            # Auto-wire from entity descriptors
            for desc in get_registry().all_descriptors():
                if desc.schema_module_path:
                    schema = _resolve_dotted_path(desc.schema_module_path)
                    self._schemas[desc.effective_schema_key] = schema

            # BASE_SCHEMA has no entity descriptor -- it's a universal fallback
            from autom8_asana.dataframes.schemas.base import BASE_SCHEMA

            self._schemas["*"] = BASE_SCHEMA
            self._initialized = True

            # Per TDD-ENTITY-EXT-001: Import-time validation
            # Warn about schemas without dedicated extractors
            try:
                self._validate_extractor_coverage()
            except Exception:
                # Per R1.1: Validation MUST NOT crash startup
                # If validation itself fails, log and continue
                from autom8y_log import get_logger

                get_logger(__name__).warning(
                    "schema_validation_failed",
                    exc_info=True,
                )

    def _validate_extractor_coverage(self) -> None:
        """Warn about schemas that lack dedicated extractors.

        Per TDD-ENTITY-EXT-001 US-7: Emits structured warnings for schemas
        registered without hand-coded extractors. SchemaExtractor will handle
        these at runtime, but the warning makes the situation visible in logs.

        This method is called inside _ensure_initialized() and MUST NOT raise
        exceptions that propagate to callers.
        """
        from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

        # Known hand-coded extractors by task_type
        dedicated_extractors: set[str] = {"Unit", "Contact", "*"}

        base_col_names = {c.name for c in BASE_COLUMNS}

        for task_type, schema in self._schemas.items():
            if task_type in dedicated_extractors:
                continue  # Has a hand-coded extractor -- no warning

            schema_col_names = {c.name for c in schema.columns}
            extra_columns = schema_col_names - base_col_names

            if extra_columns:
                from autom8y_log import get_logger

                get_logger(__name__).warning(
                    "schema_using_generic_extractor",
                    extra={
                        "entity": task_type,
                        "schema_name": schema.name,
                        "extra_column_count": len(extra_columns),
                        "note": (
                            "SchemaExtractor will handle extraction; "
                            "add a dedicated extractor only if custom "
                            "derived field logic is needed"
                        ),
                    },
                )

    def get_schema(self, task_type: str) -> DataFrameSchema:
        """Get schema for task type (FR-MODEL-004).

        Args:
            task_type: Task type identifier (e.g., "Unit", "Contact")

        Returns:
            DataFrameSchema for the task type

        Raises:
            SchemaNotFoundError: If no schema registered for type
        """
        self._ensure_initialized()

        with self._lock:
            if task_type in self._schemas:
                return self._schemas[task_type]

            # Fall back to base schema for unknown types
            if "*" in self._schemas:
                return self._schemas["*"]

        raise SchemaNotFoundError(task_type)

    def register(
        self,
        task_type: str,
        schema: DataFrameSchema,
        *,
        allow_override: bool = False,
    ) -> None:
        """Register schema for task type (FR-MODEL-031, post-MVP).

        Args:
            task_type: Task type identifier
            schema: Schema to register
            allow_override: If True, allow replacing existing schema

        Raises:
            SchemaVersionError: If schema conflicts with existing registration
        """
        self._ensure_initialized()

        with self._lock:
            if task_type in self._schemas and not allow_override:
                existing = self._schemas[task_type]
                if existing.version != schema.version:
                    raise SchemaVersionError(
                        schema.name,
                        existing.version,
                        schema.version,
                    )
                # Same version, same type - skip registration
                return

            self._schemas[task_type] = schema

    def has_schema(self, task_type: str) -> bool:
        """Check if schema exists for task type.

        Args:
            task_type: Task type identifier

        Returns:
            True if schema is registered, False otherwise
        """
        self._ensure_initialized()

        with self._lock:
            return task_type in self._schemas

    def list_task_types(self) -> list[str]:
        """List all registered task types.

        Returns:
            List of registered task type identifiers (excludes "*")
        """
        self._ensure_initialized()

        with self._lock:
            return [k for k in self._schemas.keys() if k != "*"]

    def get_all_schemas(self) -> dict[str, DataFrameSchema]:
        """Get all registered schemas.

        Returns:
            Dict mapping task types to schemas
        """
        self._ensure_initialized()

        with self._lock:
            return dict(self._schemas)


def get_schema_version(entity_type: str | None) -> str | None:
    """Look up schema version from SchemaRegistry for an entity type.

    Args:
        entity_type: Entity type in lowercase (e.g., "unit", "contact").
            Returns None if entity_type is None or empty.

    Returns:
        Schema version string if found, None if lookup fails.
    """
    if not entity_type:
        return None
    try:
        from autom8_asana.core.string_utils import to_pascal_case

        registry = SchemaRegistry.get_instance()
        registry_key = to_pascal_case(entity_type)
        schema = registry.get_schema(registry_key)
        return schema.version if schema else None
    except (ValueError, KeyError, TypeError, AttributeError, RuntimeError) as e:
        get_logger(__name__).warning(
            "schema_version_lookup_failed",
            extra={"entity_type": entity_type, "error": str(e)},
        )
        return None


# Self-register for SystemContext.reset_all()
from autom8_asana.core.system_context import register_reset  # noqa: E402

register_reset(SchemaRegistry.reset)
