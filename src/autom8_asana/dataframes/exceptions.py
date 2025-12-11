"""Exception hierarchy for dataframe operations.

Per FR-ERROR-001 through FR-ERROR-004: Define base exception and
specific error types for schema, extraction, and type coercion failures.
"""

from __future__ import annotations

from typing import Any


class DataFrameError(Exception):
    """Base exception for all dataframe operations (FR-ERROR-001).

    Attributes:
        message: Human-readable error description
        context: Additional context for debugging
    """

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}


class SchemaNotFoundError(DataFrameError):
    """No schema registered for the specified task type (FR-ERROR-002).

    Attributes:
        task_type: The task type that was not found
    """

    def __init__(self, task_type: str) -> None:
        super().__init__(
            f"No schema registered for task type: {task_type}",
            context={"task_type": task_type},
        )
        self.task_type = task_type


class ExtractionError(DataFrameError):
    """Field extraction failed for a task (FR-ERROR-003).

    Attributes:
        task_gid: GID of the task that failed
        field_name: Name of the field that failed extraction
        original_error: The underlying exception
    """

    def __init__(
        self,
        task_gid: str,
        field_name: str,
        original_error: Exception,
    ) -> None:
        super().__init__(
            f"Extraction failed for task {task_gid}, field '{field_name}': {original_error}",
            context={
                "task_gid": task_gid,
                "field_name": field_name,
                "error_type": type(original_error).__name__,
            },
        )
        self.task_gid = task_gid
        self.field_name = field_name
        self.original_error = original_error


class TypeCoercionError(DataFrameError):
    """Type coercion failed for a field value (FR-ERROR-004).

    Attributes:
        field_name: Name of the field
        expected_type: Expected Python/Polars type
        actual_value: The value that could not be coerced
    """

    def __init__(
        self,
        field_name: str,
        expected_type: str,
        actual_value: Any,
    ) -> None:
        # Truncate value repr for safety (avoid logging PII)
        value_repr = repr(actual_value)
        if len(value_repr) > 50:
            value_repr = value_repr[:47] + "..."

        super().__init__(
            f"Type coercion failed for '{field_name}': "
            f"expected {expected_type}, got {type(actual_value).__name__}",
            context={
                "field_name": field_name,
                "expected_type": expected_type,
                "actual_type": type(actual_value).__name__,
            },
        )
        self.field_name = field_name
        self.expected_type = expected_type
        self.actual_value = actual_value


class SchemaVersionError(DataFrameError):
    """Schema version conflict or incompatibility.

    Attributes:
        schema_name: Name of the schema
        expected_version: Expected schema version
        actual_version: Actual schema version found
    """

    def __init__(
        self,
        schema_name: str,
        expected_version: str,
        actual_version: str,
    ) -> None:
        super().__init__(
            f"Schema version mismatch for '{schema_name}': "
            f"expected {expected_version}, found {actual_version}",
            context={
                "schema_name": schema_name,
                "expected_version": expected_version,
                "actual_version": actual_version,
            },
        )
        self.schema_name = schema_name
        self.expected_version = expected_version
        self.actual_version = actual_version
