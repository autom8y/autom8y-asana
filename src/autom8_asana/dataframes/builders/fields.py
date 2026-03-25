"""Consolidated opt_fields for DataFrame extraction.

Per TDD-DATAFRAME-BUILDER-WATERMARK-001 Phase 1: Provides shared BASE_OPT_FIELDS
used by both ProjectDataFrameBuilder and ProgressiveProjectBuilder, including
the modified_at field required for watermark-based incremental processing.

This module eliminates duplication of _BASE_OPT_FIELDS across builders and
provides a single source of truth for the fields required during task fetching.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    import polars as pl

    from autom8_asana.dataframes.models.schema import DataFrameSchema

# Base opt_fields required for DataFrame extraction.
#
# These fields are needed to populate the 12 base TaskRow fields plus
# the _modified_at watermark column for incremental processing.
#
# Field categories:
# - Core identity: gid, name, resource_subtype
# - Status: completed, completed_at, created_at, modified_at, due_on
# - Relationships: tags, memberships, parent
# - Custom fields: custom_fields with nested subfields
#
# Note: modified_at is required for watermark-based task filtering.

BASE_OPT_FIELDS: list[str] = [
    # Core identity fields
    "gid",
    "name",
    "resource_subtype",
    # Status fields
    "completed",
    "completed_at",
    "created_at",
    "modified_at",  # Required for watermark tracking
    "due_on",
    # Tag relationships
    "tags",
    "tags.name",
    # Section membership for project context
    "memberships.section.name",
    "memberships.project.gid",
    # Parent reference for cascade: field resolution
    # Per TDD-CASCADING-FIELD-RESOLUTION-001: CascadingFieldResolver needs parent.gid
    # to traverse the parent chain and resolve fields from ancestor tasks
    "parent",
    "parent.gid",
    # Custom fields for resolver-based extraction (cf:* sources)
    # Per TDD-0009.1: DefaultCustomFieldResolver needs custom_fields to build
    # the name->GID index and extract values for office_phone, vertical, etc.
    "custom_fields",
    "custom_fields.gid",
    "custom_fields.name",
    "custom_fields.resource_subtype",
    "custom_fields.display_value",
    "custom_fields.enum_value",
    "custom_fields.enum_value.name",
    "custom_fields.multi_enum_values",
    "custom_fields.multi_enum_values.name",
    "custom_fields.number_value",
    "custom_fields.text_value",
]


def coerce_rows_to_schema(
    rows: list[dict[str, Any]],
    schema: DataFrameSchema,
) -> list[dict[str, Any]]:
    """Coerce row values to match schema types before DataFrame creation.

    Per TDD-DATAFRAME-BUILDER-WATERMARK-001: Ensures row data types are
    compatible with the Polars schema to avoid type inference errors.

    This handles common coercion cases:
    - Percentage strings ("0%") → float (0.0) for Decimal columns
    - String numbers ("123") → float for Decimal/Float64 columns
    - Empty lists remain as empty lists (schema handles typing)
    - None values remain as None (nullable columns handle this)

    Args:
        rows: List of row dicts with extracted values.
        schema: DataFrameSchema defining column types.

    Returns:
        List of coerced row dicts ready for DataFrame construction.
    """

    # Build column type lookup
    dtype_map: dict[str, str] = {col.name: col.dtype for col in schema.columns}

    coerced_rows: list[dict[str, Any]] = []

    for row in rows:
        coerced_row: dict[str, Any] = {}
        for col_name, value in row.items():
            dtype = dtype_map.get(col_name)
            coerced_row[col_name] = _coerce_value(value, dtype)
        coerced_rows.append(coerced_row)

    return coerced_rows


def _coerce_value(value: Any, dtype: str | None) -> Any:
    """Coerce a single value to match the expected dtype.

    Args:
        value: Raw extracted value.
        dtype: Target dtype string (e.g., "Decimal", "Float64", "Int64").

    Returns:
        Coerced value compatible with Polars schema.
    """
    if value is None:
        return None

    if dtype is None:
        return value

    # Handle numeric types - convert percentage strings and string numbers
    if dtype in ("Decimal", "Float64", "Float32"):
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Handle percentage strings like "0%", "50%", "100%"
            if value.endswith("%"):
                try:
                    return float(value[:-1])
                except ValueError:
                    return None
            # Handle plain numeric strings
            try:
                return float(value)
            except ValueError:
                return None
        return None

    if dtype in ("Int64", "Int32"):
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return None
        return None

    # List types - ensure empty lists are preserved (Polars handles typing)
    if dtype.startswith("List["):
        if value is None:
            return None
        if isinstance(value, list):
            return value
        return [value]  # Wrap single values in list

    # String types - convert non-strings
    if dtype in ("Utf8", "String"):
        if isinstance(value, str):
            return value
        if value is not None:
            return str(value)
        return None

    # Boolean
    if dtype == "Boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1")
        return bool(value) if value is not None else None

    # Date/Datetime - pass through (extraction should handle)
    return value


def safe_dataframe_construct(
    rows: list[dict[str, Any]],
    schema: DataFrameSchema,
    *,
    coerce: bool = True,
) -> pl.DataFrame:
    """Construct a Polars DataFrame with unified coercion and error boundary.

    This is the single construction function that all DataFrame build paths
    should call.  It applies ``coerce_rows_to_schema`` (unless opted out)
    and wraps the Polars constructor in a diagnostic error boundary so that
    type mismatches produce a ``DataFrameConstructionError`` (maps to HTTP
    422) instead of an unhandled 500.

    Args:
        rows: List of row dicts extracted from tasks.
        schema: The ``DataFrameSchema`` defining columns and Polars types.
        coerce: Whether to run ``coerce_rows_to_schema`` first (default True).

    Returns:
        A Polars DataFrame matching the schema.

    Raises:
        DataFrameConstructionError: If construction fails after coercion.
    """
    import polars as pl
    from autom8y_log import get_logger

    from autom8_asana.dataframes.exceptions import DataFrameConstructionError

    _logger = get_logger(__name__)

    if coerce:
        rows = coerce_rows_to_schema(rows, schema)

    try:
        return pl.DataFrame(rows, schema=schema.to_polars_schema())
    except (pl.exceptions.SchemaError, TypeError, pl.exceptions.ComputeError) as exc:
        _logger.error(
            "dataframe_construction_failed",
            extra={
                "schema_name": schema.name,
                "row_count": len(rows),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )
        raise DataFrameConstructionError(
            schema_name=schema.name,
            row_count=len(rows),
            original_error=exc,
        ) from exc
