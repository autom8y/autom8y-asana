# ADR-0028: Polars DataFrame Library

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team
- **Related**: [PRD-0003](../requirements/PRD-0003-structured-dataframe-layer.md), [TDD-0009](../design/TDD-0009-structured-dataframe-layer.md), [ADR-0027](ADR-0027-dataframe-layer-migration-strategy.md)

## Context

PRD-0003 requires the autom8_asana SDK to provide typed DataFrame output for task data extraction. The legacy `struc()` method (at `project/main.py:793-1225`) returns `pandas.DataFrame`, which has been the de facto standard for tabular data in Python.

However, several factors create pressure to reconsider the DataFrame library choice:

1. **Performance requirements**: PRD-0003 targets 20-30% improvement over legacy `struc()` (NFR-PERF-001)
2. **Type safety**: The SDK emphasizes type safety via Pydantic models and strict typing
3. **Memory efficiency**: Large projects (10,000+ tasks) need efficient memory handling (NFR-PERF-009)
4. **Lazy evaluation**: PRD-0003 Design Decision 3 requires threshold-based lazy evaluation (NFR-PERF-020)
5. **Tech stack alignment**: `TECH_STACK.md` specifies Polars as the preferred DataFrame library
6. **User decision**: The user explicitly chose Polars over pandas during PRD requirements gathering

### Forces at Play

| Force | Pull Toward |
|-------|-------------|
| Performance requirements | Polars (faster) |
| Memory efficiency | Polars (Arrow backend) |
| Lazy evaluation support | Polars (native LazyFrame) |
| Type safety | Polars (stricter types) |
| Legacy compatibility | pandas (existing struc() returns pandas) |
| Ecosystem maturity | pandas (more established) |
| Team familiarity | pandas (more common knowledge) |
| Tech stack alignment | Polars (TECH_STACK.md preference) |

## Decision

**Use Polars as the primary DataFrame library for the Structured Dataframe Layer.** The `to_dataframe()` method returns `polars.DataFrame`. Backward compatibility with pandas consumers is provided via the deprecated `struc()` wrapper that calls `to_dataframe().to_pandas()`.

### Implementation

```python
import polars as pl

class Project:
    def to_dataframe(
        self,
        task_type: str | None = None,
        concurrency: int = 10,
        use_cache: bool = True,
        lazy: bool | None = None,
    ) -> pl.DataFrame:
        """Generate typed DataFrame from project tasks.

        Returns:
            Polars DataFrame with schema-defined columns.
        """
        ...

    def struc(self, ...) -> "pd.DataFrame":
        """DEPRECATED: Use to_dataframe() instead."""
        warnings.warn(...)
        return self.to_dataframe(...).to_pandas()
```

### Version Requirements

- Minimum Polars version: `>= 0.20.0` (per NFR-COMPAT-001)
- Python version: `>= 3.12` (per project constraints)

## Rationale

### Why Polars Over pandas?

| Criterion | Polars | pandas | Winner |
|-----------|--------|--------|--------|
| **Execution speed** | 10-100x faster for common ops | Baseline | Polars |
| **Memory efficiency** | Arrow columnar, zero-copy | NumPy-backed, copies | Polars |
| **Lazy evaluation** | Native LazyFrame with query optimization | No native support | Polars |
| **Type strictness** | Enforced dtypes, early error detection | Permissive, silent coercion | Polars |
| **Multithreading** | Parallel by default | GIL-limited | Polars |
| **API consistency** | Method chaining, no index confusion | Mixed paradigms | Polars |
| **Ecosystem maturity** | Growing rapidly (2020+) | Established (2008+) | pandas |
| **Documentation/tutorials** | Good, improving | Extensive | pandas |

### Performance Benchmarks

Based on published benchmarks and internal testing patterns:

| Operation | Polars | pandas | Speedup |
|-----------|--------|--------|---------|
| CSV read (1GB) | ~2s | ~15s | 7.5x |
| Group-by aggregation | ~100ms | ~2s | 20x |
| Filter + select | ~50ms | ~500ms | 10x |
| Join (1M x 1M rows) | ~1s | ~10s | 10x |

These align with PRD-0003's 20-30% performance improvement target.

### Lazy Evaluation Support

Polars provides `LazyFrame` with automatic query optimization:

```python
# Polars: Query optimization happens automatically
df = (
    pl.scan_parquet("data.parquet")
    .filter(pl.col("status") == "active")
    .select(["name", "value"])
    .collect()  # Execution happens here
)

# pandas: No equivalent; all operations execute immediately
```

This directly supports PRD-0003 Design Decision 3 (100-task threshold for lazy evaluation).

### Type Safety Alignment

Polars enforces strict types, matching the SDK's Pydantic-based type safety philosophy:

```python
# Polars: Type mismatch raises error
df = pl.DataFrame({"x": [1, 2, "three"]})  # Error: mixed types

# pandas: Silent type coercion
df = pd.DataFrame({"x": [1, 2, "three"]})  # Becomes object dtype silently
```

### User Decision

The user explicitly chose Polars during PRD-0003 requirements gathering:

> "Decision 6: DataFrame Library - Polars (not pandas)"

This decision was documented in PRD-0003 User Decisions section.

## Alternatives Considered

### Alternative 1: pandas

- **Description**: Use pandas as the DataFrame library, matching the legacy `struc()` implementation.
- **Pros**:
  - Zero migration effort for legacy consumers
  - Extensive ecosystem integration
  - More tutorials and Stack Overflow answers
  - Team likely more familiar
- **Cons**:
  - 10-100x slower for many operations
  - No native lazy evaluation
  - Permissive typing hides errors
  - Higher memory footprint
  - Index-based API causes confusion
- **Why not chosen**: Performance requirements (NFR-PERF-001) and user decision override familiarity concerns. The `.to_pandas()` conversion path provides backward compatibility.

### Alternative 2: Support Both Libraries

- **Description**: Return type based on parameter: `to_dataframe(output="polars")` vs `to_dataframe(output="pandas")`.
- **Pros**:
  - Maximum flexibility for consumers
  - No migration needed for pandas users
  - Gradual adoption path
- **Cons**:
  - Doubled testing surface
  - API complexity (which output is default?)
  - Maintenance burden for two codepaths
  - Type annotations become complex (`pl.DataFrame | pd.DataFrame`)
  - Inconsistent behavior between outputs
- **Why not chosen**: Complexity not justified. Single output with `.to_pandas()` conversion achieves compatibility without dual implementation.

### Alternative 3: DuckDB

- **Description**: Use DuckDB's Python API for DataFrame operations.
- **Pros**:
  - SQL-based queries (familiar to many)
  - Excellent performance
  - In-process analytics database
- **Cons**:
  - Different API paradigm (SQL vs DataFrame)
  - Less common for pure Python workflows
  - Additional dependency with database semantics
  - Not a drop-in DataFrame replacement
- **Why not chosen**: SDK consumers expect DataFrame API, not SQL interface. DuckDB is better suited for analytical workloads with complex queries.

### Alternative 4: Vaex

- **Description**: Use Vaex for out-of-core DataFrame processing.
- **Pros**:
  - Handles datasets larger than memory
  - Lazy evaluation
  - Good performance
- **Cons**:
  - Smaller community than Polars or pandas
  - Development has slowed
  - API less polished than Polars
  - Not as well-maintained
- **Why not chosen**: Polars has better momentum, API design, and community. Out-of-core is not a primary requirement for MVP scope.

## Consequences

### Positive

- **Performance**: 10-100x speedup for common operations enables meeting NFR-PERF-001
- **Memory efficiency**: Arrow backend reduces memory footprint for large projects
- **Native lazy evaluation**: Supports PRD-0003 threshold-based optimization without workarounds
- **Type safety**: Strict dtype enforcement catches errors at DataFrame construction
- **Modern API**: Method chaining and consistent API reduce boilerplate
- **Tech stack alignment**: Matches TECH_STACK.md preference; consistent across codebase
- **Future-proof**: Polars is the trajectory of the Python data ecosystem

### Negative

- **Learning curve**: Team members familiar with pandas need to learn Polars idioms
- **Ecosystem integration**: Some libraries expect pandas (e.g., some ML frameworks)
- **Conversion overhead**: `.to_pandas()` adds ~10-20ms for typical DataFrames
- **Less Stack Overflow help**: Fewer community answers for edge cases
- **Breaking change for legacy**: Consumers expecting pandas from `struc()` must migrate

### Neutral

- **pandas interoperability**: `.to_pandas()` and `pl.from_pandas()` enable bidirectional conversion
- **Documentation updates**: SDK docs must cover Polars API patterns
- **Testing adjustments**: Test assertions use Polars matchers instead of pandas

## Compliance

### How This Decision Is Enforced

1. **Code review checklist**:
   - [ ] New DataFrame code uses Polars, not pandas
   - [ ] No direct pandas imports in `dataframes/` package
   - [ ] pandas only imported for `struc()` wrapper compatibility

2. **Linting rules**:
   ```python
   # In dataframes/ package, pandas imports should be flagged
   # Exception: deprecation.py for struc() wrapper
   ```

3. **Type annotations**:
   - Public API returns `polars.DataFrame`, not `pandas.DataFrame`
   - Type checkers will catch misuse

4. **Import structure**:
   ```python
   # Good: Polars in main code
   import polars as pl

   # Bad: pandas in main extraction code
   import pandas as pd  # Should be in deprecation.py only
   ```

5. **Test coverage**:
   - Integration tests verify Polars output
   - Deprecation tests verify pandas conversion in `struc()` wrapper
