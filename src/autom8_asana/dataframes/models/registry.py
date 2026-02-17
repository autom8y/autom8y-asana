"""Singleton registry for task-type to schema mapping.

Per FR-MODEL-030 through FR-MODEL-033: Singleton with lazy initialization
and runtime registration support.
"""

from __future__ import annotations

import threading
from typing import ClassVar

from autom8_asana.dataframes.exceptions import SchemaNotFoundError, SchemaVersionError
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
            Also clears the resolvable entities cache in resolver module.
        """
        with cls._lock:
            cls._instance = None

        # Clear resolvable entities cache (import here to avoid circular import)
        try:
            from autom8_asana.services.resolver import _clear_resolvable_cache

            _clear_resolvable_cache()
        except ImportError:
            # If resolver module not yet loaded, no cache to clear
            pass

    def _ensure_initialized(self) -> None:
        """Lazy initialization of built-in schemas."""
        if self._initialized:
            return

        with self._lock:
            # Double-checked locking
            if self._initialized:
                return

            # Import schemas here to avoid circular imports
            # Note: This is the canonical registration point for schemas.
            # See core.entity_types.ENTITY_TYPES for the list of entity types.
            from autom8_asana.dataframes.schemas.asset_edit import ASSET_EDIT_SCHEMA
            from autom8_asana.dataframes.schemas.asset_edit_holder import (
                ASSET_EDIT_HOLDER_SCHEMA,
            )
            from autom8_asana.dataframes.schemas.base import BASE_SCHEMA
            from autom8_asana.dataframes.schemas.business import BUSINESS_SCHEMA
            from autom8_asana.dataframes.schemas.contact import CONTACT_SCHEMA
            from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA
            from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA

            self._schemas["*"] = BASE_SCHEMA
            self._schemas["Unit"] = UNIT_SCHEMA
            self._schemas["Business"] = BUSINESS_SCHEMA
            self._schemas["Contact"] = CONTACT_SCHEMA
            self._schemas["Offer"] = OFFER_SCHEMA
            self._schemas["AssetEdit"] = ASSET_EDIT_SCHEMA
            self._schemas["AssetEditHolder"] = ASSET_EDIT_HOLDER_SCHEMA
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
