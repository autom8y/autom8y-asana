"""Schema definition models for typed DataFrame generation.

Per FR-MODEL-001 through FR-MODEL-006: Provides ColumnDef and DataFrameSchema
for type-safe column definitions with Polars dtype support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    import polars as pl


@dataclass(frozen=True)
class ColumnDef:
    """Definition of a single DataFrame column (FR-MODEL-001).

    Per TDD-0009: Type-safe column definitions with Polars dtypes.

    Attributes:
        name: Column name in output DataFrame
        dtype: Polars data type for the column (as string for lazy import)
        nullable: Whether column allows null values (default True)
        source: Attribute path or custom field GID for extraction
        extractor: Optional custom extraction function
        description: Human-readable description for documentation

    Example:
        >>> col = ColumnDef("gid", "Utf8", nullable=False, source="gid")
        >>> col.name
        'gid'
    """

    name: str
    dtype: str  # Polars dtype name (e.g., "Utf8", "Int64", "Datetime")
    nullable: bool = True
    source: str | None = None
    extractor: Callable[[Any], Any] | None = field(default=None, compare=False)
    description: str | None = None

    def get_polars_dtype(self) -> pl.DataType:
        """Convert dtype string to actual Polars DataType.

        Returns:
            Polars DataType instance

        Raises:
            ValueError: If dtype string is not recognized
        """
        import polars as pl

        # Mapping of string dtype names to Polars DataType instances.
        # Note: Simple types like pl.Utf8 are singleton instances in Polars.
        dtype_map: dict[str, pl.DataType] = {
            "Utf8": pl.Utf8,  # type: ignore[dict-item]
            "String": pl.Utf8,  # type: ignore[dict-item]
            "Int64": pl.Int64,  # type: ignore[dict-item]
            "Int32": pl.Int32,  # type: ignore[dict-item]
            "Float64": pl.Float64,  # type: ignore[dict-item]
            "Boolean": pl.Boolean,  # type: ignore[dict-item]
            "Date": pl.Date,  # type: ignore[dict-item]
            "Datetime": pl.Datetime("us", "UTC"),
            # Use Float64 for decimal values - Polars Decimal requires precision/scale
            # and Python floats work better for most use cases
            "Decimal": pl.Float64,  # type: ignore[dict-item]
            "List[Utf8]": pl.List(pl.Utf8),
            "List[String]": pl.List(pl.Utf8),
        }

        if self.dtype not in dtype_map:
            raise ValueError(f"Unknown Polars dtype: {self.dtype}")

        return dtype_map[self.dtype]


@dataclass
class DataFrameSchema:
    """Schema definition for typed DataFrame generation (FR-MODEL-001-006).

    Per TDD-0009: Complete schema with column definitions, versioning,
    and export capabilities for cache compatibility.

    Attributes:
        name: Schema identifier (e.g., "base", "unit", "contact")
        task_type: Task type this schema applies to (e.g., "Unit", "*" for base)
        columns: Ordered list of column definitions
        version: Schema version for cache compatibility (semver)

    Example:
        >>> schema = DataFrameSchema(
        ...     name="base",
        ...     task_type="*",
        ...     columns=[ColumnDef("gid", "Utf8", nullable=False)],
        ... )
        >>> schema.column_names()
        ['gid']
    """

    name: str
    task_type: str
    columns: list[ColumnDef]
    version: str = "1.0.0"

    def get_column(self, name: str) -> ColumnDef | None:
        """Get column definition by name.

        Args:
            name: Column name to find

        Returns:
            ColumnDef if found, None otherwise
        """
        return next((c for c in self.columns if c.name == name), None)

    def to_polars_schema(self) -> dict[str, pl.DataType]:
        """Convert to Polars schema dict for DataFrame construction.

        Returns:
            Dict mapping column names to Polars DataType instances
        """
        return {col.name: col.get_polars_dtype() for col in self.columns}

    def column_names(self) -> list[str]:
        """Return ordered list of column names.

        Returns:
            List of column names in schema order
        """
        return [col.name for col in self.columns]

    def has_cascade_columns(self) -> bool:
        """Check if schema has any cascade: source columns.

        Per TDD-GID-RESOLUTION-SERVICE: Used to determine if parent
        pre-warming is beneficial for extraction.

        Returns:
            True if any column has a cascade: source prefix.
        """
        return any(
            col.source and col.source.lower().startswith("cascade:")
            for col in self.columns
        )

    def get_cascade_columns(self) -> list[tuple[str, str]]:
        """Extract cascade column pairs from schema.

        Returns:
            List of (column_name, cascade_field_name) tuples.
            E.g., ``[("office_phone", "Office Phone"), ("vertical", "Vertical")]``
        """
        return [
            (col.name, col.source[len("cascade:") :].strip())
            for col in self.columns
            if col.source and col.source.lower().startswith("cascade:")
        ]

    def to_dict(self) -> dict[str, Any]:
        """Export schema as JSON-serializable dict (FR-MODEL-006).

        Returns:
            Dict representation suitable for JSON serialization
        """
        return {
            "name": self.name,
            "task_type": self.task_type,
            "version": self.version,
            "columns": [
                {
                    "name": col.name,
                    "dtype": col.dtype,
                    "nullable": col.nullable,
                    "source": col.source,
                    "description": col.description,
                }
                for col in self.columns
            ],
        }

    def validate_row(self, row: dict[str, Any]) -> list[str]:
        """Validate row against schema, return list of errors.

        Args:
            row: Dict representing a single row

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []
        for col in self.columns:
            value = row.get(col.name)
            if value is None and not col.nullable:
                errors.append(f"{col.name}: required field is null")
        return errors

    def __len__(self) -> int:
        """Return number of columns in schema."""
        return len(self.columns)
