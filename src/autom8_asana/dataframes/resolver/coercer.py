"""Type coercion for Asana custom field values.

Per TDD-custom-field-type-coercion FR-001:
Schema-aware coercion of raw Asana API values to target dtypes.

The coercer handles the mismatch between Asana API return types
and schema-defined target types, particularly for multi_enum fields
that return lists but may be mapped to string columns.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar

from autom8y_log import get_logger

__all__ = ["TypeCoercer", "coerce_value"]

logger = get_logger(__name__)


class TypeCoercer:
    """Stateless type coercion for custom field values.

    Per FR-001: Provides schema-aware coercion from raw Asana API values
    to target dtypes defined in ColumnDef.

    Coercion Rules:
        - list -> str: Join with ", " separator (empty list -> None)
        - str -> list: Wrap in single-element list
        - Any -> Decimal: Via str intermediate for precision
        - None: Preserved (nullable fields)

    Example:
        >>> coercer = TypeCoercer()
        >>> coercer.coerce(["A", "B"], "Utf8")
        'A, B'
        >>> coercer.coerce([], "Utf8")
        None
        >>> coercer.coerce("single", "List[Utf8]")
        ['single']
        >>> coercer.coerce("123.45", "Decimal")
        Decimal('123.45')

    Thread Safety:
        All methods are stateless and thread-safe.
    """

    # Separator for joining list values into strings
    LIST_SEPARATOR: ClassVar[str] = ", "

    # dtypes that represent list types
    LIST_DTYPES: ClassVar[frozenset[str]] = frozenset(
        {
            "List[Utf8]",
            "List[String]",
        }
    )

    # dtypes that represent string types
    STRING_DTYPES: ClassVar[frozenset[str]] = frozenset(
        {
            "Utf8",
            "String",
        }
    )

    # dtypes that represent numeric types
    NUMERIC_DTYPES: ClassVar[frozenset[str]] = frozenset(
        {
            "Decimal",
            "Float64",
            "Int64",
            "Int32",
        }
    )

    def coerce(
        self,
        value: Any,
        target_dtype: str,
        *,
        source_type: str | None = None,
    ) -> Any:
        """Coerce value to target dtype.

        Args:
            value: Raw value from Asana API
            target_dtype: Target dtype from ColumnDef (e.g., "Utf8", "List[Utf8]")
            source_type: Optional Asana field type hint (e.g., "multi_enum")

        Returns:
            Coerced value, or None if value is None or empty list

        Raises:
            No exceptions - logs warnings and returns best-effort result
        """
        if value is None:
            return None

        # Handle list -> string coercion (multi_enum to Utf8)
        if isinstance(value, list) and target_dtype in self.STRING_DTYPES:
            return self._list_to_string(value)

        # Handle string -> list coercion (single value to List[Utf8])
        if isinstance(value, str) and target_dtype in self.LIST_DTYPES:
            return self._string_to_list(value)

        # Handle numeric coercion
        if target_dtype in self.NUMERIC_DTYPES:
            return self._to_numeric(value, target_dtype)

        # Handle list passthrough (list to List[Utf8])
        if isinstance(value, list) and target_dtype in self.LIST_DTYPES:
            return value  # No coercion needed

        # Handle string passthrough
        if isinstance(value, str) and target_dtype in self.STRING_DTYPES:
            return value  # No coercion needed

        # Fallback: return as-is with debug log
        logger.debug(
            "type_coercion_passthrough",
            extra={
                "value_type": type(value).__name__,
                "target_dtype": target_dtype,
                "source_type": source_type,
            },
        )
        return value

    def _list_to_string(self, value: list[Any]) -> str | None:
        """Convert list to comma-separated string.

        Args:
            value: List of values (typically strings from multi_enum)

        Returns:
            Comma-separated string, or None if list is empty
        """
        if not value:
            return None

        # Filter None values and convert to strings
        str_values = [str(v) for v in value if v is not None]

        if not str_values:
            return None

        return self.LIST_SEPARATOR.join(str_values)

    def _string_to_list(self, value: str) -> list[str]:
        """Wrap string in a single-element list.

        Args:
            value: String value

        Returns:
            Single-element list containing the string
        """
        return [value]

    def _to_numeric(
        self, value: Any, target_dtype: str
    ) -> Decimal | float | int | None:
        """Convert value to numeric type.

        Args:
            value: Value to convert
            target_dtype: Target numeric dtype

        Returns:
            Converted numeric value, or None on failure
        """
        if value is None:
            return None

        try:
            if target_dtype == "Decimal":
                if isinstance(value, Decimal):
                    return value
                return Decimal(str(value))

            if target_dtype == "Float64":
                return float(value)

            if target_dtype in {"Int64", "Int32"}:
                # Try direct int() first to preserve precision for large integers
                # Fall back to float() for decimal strings like "123.0"
                if isinstance(value, str):
                    try:
                        return int(value)
                    except ValueError:
                        return int(float(value))
                return int(float(value))

        except (ValueError, TypeError, InvalidOperation, OverflowError) as e:
            logger.debug(
                "type_coercion_numeric_failed",
                extra={
                    "value": value,
                    "target_dtype": target_dtype,
                    "error": str(e),
                },
            )
            return None

        result: Decimal | float | int = value
        return result


# Module-level singleton for convenience
_coercer = TypeCoercer()


def coerce_value(
    value: Any,
    target_dtype: str,
    *,
    source_type: str | None = None,
) -> Any:
    """Module-level coercion function using singleton.

    See TypeCoercer.coerce() for details.
    """
    return _coercer.coerce(value, target_dtype, source_type=source_type)
