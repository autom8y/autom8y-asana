# ADR-0033: Schema Enforcement

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team
- **Related**: [PRD-0003](../requirements/PRD-0003-structured-dataframe-layer.md) (FR-MODEL-005, NFR-REL-002), [TDD-0009](../design/TDD-0009-structured-dataframe-layer.md), [ADR-0028](ADR-0028-polars-dataframe-library.md)

## Context

The Structured Dataframe Layer extracts Asana task data into typed Polars DataFrames. Each schema defines column names, Polars dtypes, and nullability constraints. The question is: how strictly should the system enforce type conformance when extracted data doesn't match the schema?

### Type Mismatch Scenarios

| Scenario | Example | Expected Type | Actual Value |
|----------|---------|---------------|--------------|
| String in number field | MRR = "N/A" | `Decimal` | `str` |
| Missing required field | gid = None | `str` (non-null) | `None` |
| Wrong date format | created = "yesterday" | `datetime` | `str` |
| Unexpected enum value | status = "UNKNOWN" | enum | `str` |
| Number in string field | phone = 5551234567 | `str` | `int` |
| List where scalar expected | email = ["a@b.com", "c@d.com"] | `str` | `list` |

### Enforcement Options

| Approach | Behavior on Mismatch |
|----------|---------------------|
| **Strict failure** | Raise exception, abort extraction |
| **Strict with fallback** | Coerce to null, log warning |
| **Permissive coercion** | Best-effort coercion, silent |
| **Permissive (Any type)** | Store as-is, lose type safety |

### PRD-0003 Requirements

FR-MODEL-005:
> SDK shall validate that extracted values match declared types. Type mismatches logged as warnings; values coerced or set to null.

NFR-REL-002:
> Type coercion success rate >= 99% with graceful fallback.

FR-ERROR-005:
> SDK shall continue processing on individual task extraction failures.

### Forces at Play

| Force | Pull Toward |
|-------|-------------|
| Type safety | Strict enforcement |
| Data quality visibility | Logged warnings |
| Robustness | Continue on error |
| Debugging | Fail fast |
| Production stability | Graceful degradation |
| Polars compatibility | Strict dtypes |
| Data analysis needs | Type consistency |

## Decision

**Strict Polars dtype enforcement with logged coercion fallbacks.** When extracted data doesn't match the schema type:

1. Attempt type coercion (e.g., string "5000" to Decimal 5000)
2. If coercion fails, set value to `null`
3. Log a warning with field name, expected type, and actual value
4. Continue extraction (don't fail the entire batch)

### Coercion Rules

| Expected Type | Actual Type | Coercion Behavior |
|---------------|-------------|-------------------|
| `pl.Decimal` | `str` (numeric) | Parse as Decimal |
| `pl.Decimal` | `str` (non-numeric) | -> `null`, warn |
| `pl.Datetime` | `str` (ISO format) | Parse as datetime |
| `pl.Datetime` | `str` (invalid) | -> `null`, warn |
| `pl.Boolean` | `str` ("true"/"false") | Parse as bool |
| `pl.Boolean` | `int` (0/1) | Convert to bool |
| `pl.Utf8` | `int` | Stringify |
| `pl.Utf8` | `None` (non-nullable) | -> `null`, warn |
| `pl.List(pl.Utf8)` | `str` | Wrap in list |
| `pl.List(pl.Utf8)` | `None` | -> empty list |

### Implementation

```python
from typing import Any
import polars as pl
from decimal import Decimal, InvalidOperation
from datetime import datetime

class TypeCoercer:
    """Type coercion with logging for schema enforcement."""

    def __init__(self, logger: LogProvider):
        self._log = logger
        self._warnings: list[TypeCoercionWarning] = []

    def coerce(
        self,
        value: Any,
        target_dtype: pl.DataType,
        field_name: str,
        task_gid: str,
    ) -> Any:
        """Coerce value to target type, fallback to null on failure.

        Args:
            value: The extracted value
            target_dtype: Expected Polars dtype
            field_name: Column name (for logging)
            task_gid: Task GID (for logging)

        Returns:
            Coerced value or None if coercion failed
        """
        if value is None:
            return None

        try:
            return self._coerce_to_type(value, target_dtype)
        except (ValueError, TypeError, InvalidOperation) as e:
            self._log_coercion_warning(
                field_name=field_name,
                task_gid=task_gid,
                expected_type=target_dtype,
                actual_value=value,
                error=str(e),
            )
            return None  # Fallback to null

    def _coerce_to_type(self, value: Any, dtype: pl.DataType) -> Any:
        """Attempt type coercion."""
        if isinstance(dtype, pl.Decimal):
            return self._to_decimal(value)
        elif isinstance(dtype, pl.Datetime):
            return self._to_datetime(value)
        elif isinstance(dtype, pl.Date):
            return self._to_date(value)
        elif isinstance(dtype, pl.Boolean):
            return self._to_boolean(value)
        elif isinstance(dtype, pl.Utf8):
            return str(value) if value is not None else None
        elif isinstance(dtype, pl.List):
            return self._to_list(value, dtype.inner)
        else:
            return value  # Pass through for other types

    def _to_decimal(self, value: Any) -> Decimal | None:
        """Convert to Decimal."""
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            return Decimal(value)  # Raises InvalidOperation if invalid
        raise TypeError(f"Cannot convert {type(value).__name__} to Decimal")

    def _to_datetime(self, value: Any) -> datetime | None:
        """Convert to datetime."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise TypeError(f"Cannot convert {type(value).__name__} to datetime")

    def _to_boolean(self, value: Any) -> bool | None:
        """Convert to boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            if value.lower() in ("true", "yes", "1"):
                return True
            if value.lower() in ("false", "no", "0"):
                return False
        raise TypeError(f"Cannot convert {type(value).__name__} to bool")

    def _to_list(self, value: Any, inner_dtype: pl.DataType) -> list:
        """Convert to list."""
        if isinstance(value, list):
            return [self._coerce_to_type(v, inner_dtype) for v in value]
        return [self._coerce_to_type(value, inner_dtype)]  # Wrap scalar

    def _log_coercion_warning(
        self,
        field_name: str,
        task_gid: str,
        expected_type: pl.DataType,
        actual_value: Any,
        error: str,
    ) -> None:
        """Log type coercion failure as warning."""
        warning = TypeCoercionWarning(
            field_name=field_name,
            task_gid=task_gid,
            expected_type=str(expected_type),
            actual_type=type(actual_value).__name__,
            actual_value=repr(actual_value)[:100],  # Truncate large values
            error=error,
        )
        self._warnings.append(warning)

        self._log.warning(
            "type_coercion_failed",
            field=field_name,
            task_gid=task_gid,
            expected=str(expected_type),
            actual_type=type(actual_value).__name__,
            error=error,
        )

    def get_warnings(self) -> list[TypeCoercionWarning]:
        """Return accumulated warnings for this extraction."""
        return self._warnings.copy()
```

### DataFrame Construction

```python
class DataFrameBuilder:
    def _build_dataframe(self, rows: list[dict]) -> pl.DataFrame:
        """Build DataFrame with schema enforcement."""
        schema = self._schema.to_polars_schema()

        # Polars enforces types at DataFrame construction
        try:
            df = pl.DataFrame(rows, schema=schema)
        except pl.exceptions.SchemaError as e:
            # Should not happen if coercion worked correctly
            self._log.error(
                "dataframe_schema_error",
                error=str(e),
                schema=schema,
            )
            raise DataFrameError(f"Schema enforcement failed: {e}")

        return df
```

### Extraction Result with Warnings

```python
@dataclass
class ExtractionResult:
    """Result of DataFrame extraction including warnings."""
    dataframe: pl.DataFrame
    warnings: list[TypeCoercionWarning]
    error_count: int

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

def to_dataframe(...) -> pl.DataFrame:
    """Public API returns DataFrame; warnings logged."""
    result = self._extract_with_result(...)
    return result.dataframe

def to_dataframe_with_result(...) -> ExtractionResult:
    """Alternative API returns result with warnings."""
    return self._extract_with_result(...)
```

## Rationale

### Why Strict Polars Dtypes?

**1. Type safety propagates to consumers**: DataFrame consumers can trust that `mrr` is always `Decimal`, not sometimes `str`. This enables safe downstream operations:

```python
# Safe: mrr is always Decimal or null
df.select(pl.col("mrr") * 12)  # Annual revenue

# Unsafe (if types were permissive): Would fail at runtime
# pl.col("mrr") = "N/A" -> "N/AN/AN/A..."
```

**2. Polars enforces types anyway**: Polars DataFrames have strict dtypes. Attempting to construct a DataFrame with mismatched types raises `SchemaError`. We must handle type mismatches; the question is how.

**3. Catches data quality issues**: Type coercion failures indicate data quality problems (e.g., "N/A" in a number field). Logging these as warnings surfaces issues without breaking extraction.

### Why Coerce to Null (Not Fail)?

**1. Robustness**: One bad field shouldn't abort extraction of 1,000 tasks. FR-ERROR-005 requires continuing on individual failures.

**2. Null is type-safe**: Polars handles null values correctly. `null` is valid for any nullable column and propagates safely through operations.

**3. Data is preserved**: Other fields in the row are still extracted correctly. Only the problematic field is lost.

**4. Matches FR-MODEL-005**: "Type mismatches logged as warnings; values coerced or set to null."

### Why Log Warnings?

**1. Visibility**: Operators can monitor type coercion failures and identify data quality issues.

**2. Debugging**: When a value is unexpectedly null, the warning log explains why.

**3. Trend detection**: Increasing warning rates may indicate Asana data changes or extraction bugs.

**4. Non-blocking**: Warnings don't fail the extraction but provide actionable information.

## Alternatives Considered

### Alternative 1: Strict Failure (Fail Fast)

- **Description**: Raise exception on any type mismatch; abort extraction.
- **Pros**:
  - Forces data quality fixes
  - No silent data loss
  - Clear failure mode
- **Cons**:
  - One bad task fails entire project
  - Fragile in production
  - Violates FR-ERROR-005
  - Poor user experience
- **Why not chosen**: Production systems need robustness. One bad field shouldn't prevent all extraction.

### Alternative 2: Silent Coercion (No Warnings)

- **Description**: Coerce types silently; don't log failures.
- **Pros**:
  - No log noise
  - Simplest implementation
  - Always succeeds
- **Cons**:
  - Data quality issues hidden
  - No visibility into coercion failures
  - Debugging difficult
  - Violates FR-MODEL-005 (requires logging)
- **Why not chosen**: Visibility into type mismatches is essential for data quality monitoring and debugging.

### Alternative 3: Permissive (Any Type)

- **Description**: Store values as-is without type enforcement; use `pl.Object` dtype.
- **Pros**:
  - No data loss
  - No coercion logic
  - Flexible for heterogeneous data
- **Cons**:
  - Loses all type safety
  - Defeats purpose of typed DataFrames
  - Downstream operations fail at runtime
  - Violates FR-MODEL-005 (requires validation)
- **Why not chosen**: Type safety is a core requirement. Permissive types provide no value over raw dicts.

### Alternative 4: Best-Effort Coercion (No Null Fallback)

- **Description**: Try multiple coercion strategies; keep original value if all fail.
- **Pros**:
  - No data loss to null
  - More aggressive recovery
- **Cons**:
  - Type inconsistency (sometimes `Decimal`, sometimes `str`)
  - Polars rejects heterogeneous columns
  - Downstream operations unpredictable
  - Would require `pl.Object` dtype anyway
- **Why not chosen**: Polars enforces homogeneous column types. Mixed types are not possible.

### Alternative 5: Configurable Strictness

- **Description**: Allow users to choose enforcement level (strict, warn, permissive).
- **Pros**:
  - Maximum flexibility
  - Users choose their trade-off
- **Cons**:
  - API complexity
  - Multiple code paths
  - Testing burden
  - Most users want the sensible default
- **Why not chosen**: One correct behavior is better than configurability. Strict with warnings is the right default for all cases.

## Consequences

### Positive

- **Type safety preserved**: DataFrame columns have consistent, predictable types
- **Robustness**: Extraction continues despite individual field failures
- **Visibility**: Warnings surface data quality issues
- **Debugging support**: Warning logs explain unexpected null values
- **Polars compatibility**: Schema enforcement aligns with Polars strict typing
- **Production-ready**: Graceful degradation handles real-world data inconsistencies

### Negative

- **Data loss to null**: Uncoercible values become null (information lost)
- **Warning volume**: High-volume extractions may produce many warnings
- **False positives**: Some coercion warnings may be acceptable (known bad data)
- **Log parsing needed**: Operators must monitor warning patterns

### Neutral

- **Coercion logic complexity**: Rules for each type must be implemented and tested
- **Warning aggregation**: May want to summarize warnings rather than log each one
- **Metrics integration**: Warning counts should be metrics for monitoring

## Compliance

### How This Decision Is Enforced

1. **Code review checklist**:
   - [ ] All extraction paths use `TypeCoercer` for type handling
   - [ ] No raw value assignment without coercion
   - [ ] Coercion failures logged as warnings (not errors)
   - [ ] Extraction continues after coercion failure

2. **Unit tests**:
   ```python
   def test_string_to_decimal_coerces():
       assert coercer.coerce("5000.00", pl.Decimal, "mrr", "123") == Decimal("5000.00")

   def test_invalid_string_to_decimal_returns_null():
       result = coercer.coerce("N/A", pl.Decimal, "mrr", "123")
       assert result is None

   def test_coercion_failure_logs_warning():
       coercer.coerce("N/A", pl.Decimal, "mrr", "123")
       assert len(coercer.get_warnings()) == 1

   def test_extraction_continues_after_coercion_failure():
       tasks = [task_with_bad_mrr, task_with_good_mrr]
       result = builder.build(tasks)
       assert len(result.dataframe) == 2  # Both tasks extracted
   ```

3. **Logging format**:
   ```python
   # Structured warning log
   {
       "level": "warning",
       "event": "type_coercion_failed",
       "field": "mrr",
       "task_gid": "123456789",
       "expected": "Decimal",
       "actual_type": "str",
       "error": "Invalid literal for Decimal: 'N/A'",
       "timestamp": "2025-01-15T10:30:00Z"
   }
   ```

4. **Metrics**:
   - `dataframe_coercion_failures_total` (counter by field name)
   - `dataframe_coercion_success_rate` (gauge)
   - Alert if success rate < 99% (per NFR-REL-002)

5. **Documentation**:
   - [ ] Coercion rules documented for each type
   - [ ] Warning log format documented
   - [ ] Troubleshooting guide for common coercion failures
