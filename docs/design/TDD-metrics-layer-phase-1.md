# TDD: Metrics Layer Phase 1

**Status**: PROPOSED
**Author**: Architect Agent
**Date**: 2026-02-02
**Complexity**: MODULE

---

## 1. Overview & Problem Statement

### 1.1 Business Problem

Calculating aggregate metrics over Asana project data (e.g., total MRR, total weekly ad spend for ACTIVE offers) currently requires per-metric throwaway scripts. `scripts/calc_mrr.py` and `scripts/calc_ad_spend.py` are 90% identical -- same data loading, same deduplication logic, same output formatting -- differing only in which column they aggregate. Every new metric means copying a script and changing two strings.

### 1.2 Goals

1. **Eliminate duplication**: Replace N copy-paste scripts with one CLI backed by a composable metrics layer.
2. **Declarative metric definitions**: New metrics are added by instantiating a `Metric` dataclass, not by writing a new script.
3. **Registry pattern**: Follow the established `ProjectTypeRegistry` singleton pattern (see `models/business/registry.py`) for discoverability and lazy loading.
4. **Output parity**: `calc_metric.py active_mrr` must produce byte-identical output to `calc_mrr.py` for the same input data.

### 1.3 Non-Goals (Phase 1)

- Time-series tracking or historical storage of metric values.
- Multi-project or cross-project metric computation.
- Dynamic section GID resolution via Asana API (hardcoded GIDs in Phase 1).
- Thread safety in the registry (single-threaded CLI usage only).
- Metric composition (combining multiple MetricExprs into a single Metric).

### 1.4 Success Criteria

| ID | Criterion | Verification |
|----|-----------|-------------|
| SC-1 | `calc_metric.py active_mrr` output matches `calc_mrr.py` output exactly (same totals, same verbose rows) | Integration test comparing outputs |
| SC-2 | `calc_metric.py active_ad_spend` output matches `calc_ad_spend.py` output exactly | Integration test comparing outputs |
| SC-3 | Adding a new metric requires only a `Metric(...)` instantiation in `definitions/` | Review: no CLI or compute changes needed |
| SC-4 | All new code has unit tests with >= 90% line coverage | `pytest --cov` |
| SC-5 | Existing test suite passes with zero regressions | CI green |

---

## 2. System Context

### 2.1 Component Diagram

```
                    CLI Layer                    Metrics Layer                   Data Layer
               +-----------------+          +-------------------+          +----------------+
               |                 |          |                   |          |                |
  User ------->  calc_metric.py  |--------->  MetricRegistry    |          |   S3 Bucket    |
               |  (argparse)     |          |  .get_metric()    |          |  (section      |
               +-----------------+          +-------------------+          |   parquets)    |
                       |                            |                      +-------+--------+
                       |                            v                              |
                       |                    +-------------------+                  |
                       +-------------------->  compute_metric() |<-----------------+
                                            |  (filter, dedup,  |    load_section_parquet()
                                            |   aggregate)      |
                                            +-------------------+
```

### 2.2 Relationship to Existing Systems

| System | Relationship |
|--------|-------------|
| `SectionPersistence` | Metrics layer reads section parquets from the same S3 key structure (`dataframes/{project_gid}/sections/{section_gid}.parquet`) |
| `ProjectTypeRegistry` | Architectural pattern reference -- MetricRegistry follows the same singleton + lazy-init + reset pattern |
| `Offer` model | `PRIMARY_PROJECT_GID = "1143843662099250"` is the Business Offers project; section GIDs come from this project |
| `calc_mrr.py` / `calc_ad_spend.py` | Scripts being replaced; source of truth for current behavior |

---

## 3. Module Structure

```
src/autom8_asana/metrics/
    __init__.py              # Public API exports
    expr.py                  # MetricExpr dataclass
    metric.py                # Metric, Scope dataclasses
    registry.py              # MetricRegistry singleton
    compute.py               # compute_metric function
    definitions/
        __init__.py          # Auto-imports definition modules
        offer.py             # ACTIVE_MRR, ACTIVE_AD_SPEND definitions

src/autom8_asana/models/business/
    sections.py              # OfferSection enum (NEW)

scripts/
    calc_metric.py           # Unified CLI (NEW, replaces calc_mrr.py and calc_ad_spend.py)
```

---

## 4. Detailed Design

### 4.1 MetricExpr (frozen dataclass)

**File**: `src/autom8_asana/metrics/expr.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import polars as pl


# Supported aggregation functions
SUPPORTED_AGGS: frozenset[str] = frozenset({"sum", "count", "mean", "min", "max"})


@dataclass(frozen=True)
class MetricExpr:
    """A single column aggregation expression.

    Encapsulates the column selection, optional type cast, optional row filter,
    and aggregation function needed to compute one scalar from a DataFrame.

    Attributes:
        name: Expression identifier used in output (e.g., "sum_mrr").
        column: Source column name in the DataFrame (e.g., "mrr").
        cast_dtype: If set, cast column to this Polars dtype before aggregation.
            Use pl.Float64 for financial columns to handle string-encoded numbers.
        agg: Aggregation function name. Must be one of SUPPORTED_AGGS.
        filter_expr: Optional Polars expression applied as row filter BEFORE
            aggregation. Rows where this evaluates to False are excluded.

    Example:
        >>> expr = MetricExpr(
        ...     name="sum_mrr",
        ...     column="mrr",
        ...     cast_dtype=pl.Float64,
        ...     agg="sum",
        ...     filter_expr=pl.col("mrr").is_not_null() & (pl.col("mrr") > 0),
        ... )
        >>> polars_expr = expr.to_polars_expr()
    """

    name: str
    column: str
    cast_dtype: pl.DataType | None = None
    agg: str = "sum"
    filter_expr: pl.Expr | None = None

    def __post_init__(self) -> None:
        """Validate agg is a supported aggregation."""
        if self.agg not in SUPPORTED_AGGS:
            raise ValueError(
                f"Unsupported aggregation '{self.agg}'. "
                f"Must be one of: {', '.join(sorted(SUPPORTED_AGGS))}"
            )

    def to_polars_expr(self) -> pl.Expr:
        """Build a Polars aggregation expression.

        Constructs a chained Polars expression that:
        1. Selects self.column
        2. Casts to self.cast_dtype (if set)
        3. Applies the aggregation function named by self.agg

        NOTE: filter_expr is NOT applied here. Filtering happens in
        compute_metric() at the DataFrame level, because deduplication
        must occur between filtering and aggregation.

        Returns:
            Polars expression ready for use in .select() or .agg().

        Example:
            >>> expr = MetricExpr(name="sum_mrr", column="mrr",
            ...                   cast_dtype=pl.Float64, agg="sum")
            >>> expr.to_polars_expr()
            # Equivalent to: pl.col("mrr").cast(pl.Float64).sum().alias("sum_mrr")
        """
        e = pl.col(self.column)

        if self.cast_dtype is not None:
            e = e.cast(self.cast_dtype, strict=False)

        # Apply aggregation
        e = getattr(e, self.agg)()

        return e.alias(self.name)
```

**Design Decisions**:

- `filter_expr` is stored on MetricExpr but applied at the DataFrame level in `compute_metric()`, not inside `to_polars_expr()`. This is because the existing scripts filter rows, then deduplicate, then aggregate. If we applied the filter inside the expression, deduplication would not work correctly.
- `cast_dtype` uses `strict=False` to match the existing script behavior where non-numeric MRR values become null rather than raising.
- The `frozen=True` constraint ensures MetricExprs are immutable and safe to share across threads in future phases.

### 4.2 Scope (frozen dataclass)

**File**: `src/autom8_asana/metrics/metric.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field

import polars as pl


@dataclass(frozen=True)
class Scope:
    """Defines where and how a metric applies.

    Scope controls which data is loaded (entity_type + section) and
    how rows are deduplicated before aggregation.

    Attributes:
        entity_type: The entity type whose project contains the data.
            Maps to a project GID via OfferSection or future section enums.
            Phase 1 supports "offer" only.
        section: Section GID string (e.g., "1143843662099256" for ACTIVE).
            None means "all sections" (not implemented in Phase 1).
        dedup_keys: Column names for row uniqueness. Rows are deduplicated
            using these columns with keep="first" after sorting.
            None means no deduplication.
        pre_filters: Additional Polars filter expressions applied before
            deduplication. These are ANDed together with MetricExpr.filter_expr.

    Example:
        >>> scope = Scope(
        ...     entity_type="offer",
        ...     section="1143843662099256",
        ...     dedup_keys=["office_phone", "vertical"],
        ... )
    """

    entity_type: str
    section: str | None = None
    dedup_keys: list[str] | None = field(default=None)
    pre_filters: list[pl.Expr] | None = field(default=None)
```

### 4.3 Metric (frozen dataclass)

**File**: `src/autom8_asana/metrics/metric.py` (same file as Scope)

```python
@dataclass(frozen=True)
class Metric:
    """A named, scoped metric definition.

    Combines a MetricExpr (what to compute) with a Scope (where to compute it)
    under a registry-friendly name.

    Attributes:
        name: Registry key, used as CLI argument (e.g., "active_mrr").
            Must be unique within the MetricRegistry. Convention: snake_case.
        description: Human-readable description shown in --list output
            and error messages.
        expr: The MetricExpr defining the column, cast, filter, and aggregation.
        scope: The Scope defining entity type, section, dedup, and pre-filters.

    Example:
        >>> metric = Metric(
        ...     name="active_mrr",
        ...     description="Total MRR for ACTIVE offers, deduped by phone+vertical",
        ...     expr=MetricExpr(
        ...         name="sum_mrr", column="mrr",
        ...         cast_dtype=pl.Float64, agg="sum",
        ...         filter_expr=pl.col("mrr").is_not_null() & (pl.col("mrr") > 0),
        ...     ),
        ...     scope=Scope(
        ...         entity_type="offer",
        ...         section="1143843662099256",
        ...         dedup_keys=["office_phone", "vertical"],
        ...     ),
        ... )
    """

    name: str
    description: str
    expr: MetricExpr
    scope: Scope
```

### 4.4 MetricRegistry (singleton)

**File**: `src/autom8_asana/metrics/registry.py`

```python
from __future__ import annotations

from typing import ClassVar

from autom8_asana.metrics.metric import Metric


class MetricRegistry:
    """Singleton registry for metric definitions.

    Follows the ProjectTypeRegistry pattern (ADR-0093):
    - Module-level singleton via __new__
    - Lazy initialization of definitions on first access
    - Explicit reset() for test isolation

    The registry does NOT auto-discover metrics at import time. Instead,
    _ensure_initialized() imports definitions/offer.py (and future
    definition modules) on first get_metric() or list_metrics() call.

    Attributes:
        _instance: Class-level singleton reference.
        _metrics: Internal name-to-Metric mapping.
        _initialized: Whether definitions have been loaded.

    Example:
        >>> registry = MetricRegistry()
        >>> metric = registry.get_metric("active_mrr")
        >>> print(metric.description)
        'Total MRR for ACTIVE offers, deduped by phone+vertical'

    Testing:
        >>> MetricRegistry.reset()  # Clears singleton for test isolation
    """

    _instance: ClassVar[MetricRegistry | None] = None

    _metrics: dict[str, Metric]
    _initialized: bool

    def __new__(cls) -> MetricRegistry:
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._metrics = {}
            instance._initialized = False
            cls._instance = instance
        return cls._instance

    def register(self, metric: Metric) -> None:
        """Register a metric definition.

        Args:
            metric: The Metric to register.

        Raises:
            ValueError: If a metric with the same name is already registered
                with a different definition.
        """
        if metric.name in self._metrics:
            existing = self._metrics[metric.name]
            if existing is not metric:
                raise ValueError(
                    f"Metric '{metric.name}' already registered. "
                    f"Existing: {existing.description}"
                )
            return  # Idempotent

        self._metrics[metric.name] = metric

    def get_metric(self, name: str) -> Metric:
        """Look up a metric by name.

        Triggers lazy initialization on first call.

        Args:
            name: Registry key (e.g., "active_mrr").

        Returns:
            The registered Metric.

        Raises:
            KeyError: If no metric is registered with this name.
        """
        self._ensure_initialized()

        if name not in self._metrics:
            available = ", ".join(sorted(self._metrics.keys()))
            raise KeyError(
                f"Unknown metric '{name}'. Available: {available}"
            )

        return self._metrics[name]

    def list_metrics(self) -> list[str]:
        """List all registered metric names.

        Triggers lazy initialization on first call.

        Returns:
            Sorted list of registered metric names.
        """
        self._ensure_initialized()
        return sorted(self._metrics.keys())

    def _ensure_initialized(self) -> None:
        """Lazy-load definition modules if not already loaded.

        Imports autom8_asana.metrics.definitions which triggers
        auto-registration of all metrics defined in submodules.
        """
        if self._initialized:
            return

        import autom8_asana.metrics.definitions  # noqa: F401

        self._initialized = True

    @classmethod
    def reset(cls) -> None:
        """Reset singleton for test isolation.

        Per ADR-0093 pattern: explicit reset clears singleton so
        next access creates a fresh instance.
        """
        cls._instance = None
```

**Design Decisions**:

- **Lazy initialization**: Definitions are imported on first `get_metric()` or `list_metrics()` call, not at module import time. This avoids circular imports and keeps import costs low for code that only needs the registry type.
- **No thread safety**: Phase 1 is single-threaded CLI. Thread-safe registration can be added in Phase 2 with `threading.Lock` if the registry is used in the API server.
- **Idempotent registration**: Re-registering the same Metric object is a no-op. Registering a different Metric with the same name raises ValueError.

### 4.5 compute_metric Function

**File**: `src/autom8_asana/metrics/compute.py`

```python
from __future__ import annotations

import polars as pl

from autom8_asana.metrics.metric import Metric


def compute_metric(
    metric: Metric,
    df: pl.DataFrame,
    *,
    verbose: bool = False,
) -> pl.DataFrame:
    """Execute a metric against a DataFrame, returning deduped/filtered rows.

    This function applies the metric's filter, deduplication, and sorting
    logic but does NOT compute the final aggregate scalar. The caller is
    responsible for aggregation (e.g., df["mrr"].sum()) so it can also
    inspect row-level data in verbose mode.

    Processing pipeline:
        1. Select relevant columns (dedup keys + metric column + "name" for display)
        2. Cast metric column to target dtype (if cast_dtype is set)
        3. Apply MetricExpr.filter_expr (row-level filter)
        4. Apply Scope.pre_filters (additional filters, ANDed)
        5. Deduplicate by Scope.dedup_keys (keep="first")
        6. Sort by dedup_keys for deterministic output

    Args:
        metric: The Metric definition to compute.
        df: Input DataFrame (typically a section parquet).
        verbose: If True, print the per-row breakdown to stdout using
            the same Polars Config as the original scripts.

    Returns:
        Filtered, deduped, sorted DataFrame containing the metric column
        and relevant context columns. Caller can then aggregate:
            total = result[metric.expr.column].sum()

    Raises:
        pl.exceptions.ColumnNotFoundError: If metric.expr.column or any
            dedup_key is missing from the DataFrame.

    Example:
        >>> from autom8_asana.metrics.registry import MetricRegistry
        >>> registry = MetricRegistry()
        >>> metric = registry.get_metric("active_mrr")
        >>> df = load_section_parquet(bucket, project_gid, section_gid)
        >>> result = compute_metric(metric, df, verbose=True)
        >>> total = result["mrr"].sum()
        >>> print(f"Total MRR: ${total:,.0f}")
    """
    expr = metric.expr
    scope = metric.scope

    # Step 1: Select relevant columns
    # Include "name" for display if present, plus dedup keys and metric column
    select_cols = ["name"] if "name" in df.columns else []
    if scope.dedup_keys:
        select_cols.extend(scope.dedup_keys)
    select_cols.append(expr.column)
    # Deduplicate column list while preserving order
    seen: set[str] = set()
    unique_cols: list[str] = []
    for c in select_cols:
        if c not in seen:
            seen.add(c)
            unique_cols.append(c)
    result = df.select(unique_cols)

    # Step 2: Cast metric column if needed
    if expr.cast_dtype is not None:
        result = result.with_columns(
            pl.col(expr.column).cast(expr.cast_dtype, strict=False).alias(expr.column)
        )

    # Step 3: Apply MetricExpr filter
    if expr.filter_expr is not None:
        result = result.filter(expr.filter_expr)

    # Step 4: Apply Scope pre_filters
    if scope.pre_filters:
        for f in scope.pre_filters:
            result = result.filter(f)

    # Step 5: Deduplicate
    if scope.dedup_keys:
        result = result.unique(subset=scope.dedup_keys, keep="first")

    # Step 6: Sort for deterministic output
    if scope.dedup_keys:
        result = result.sort(scope.dedup_keys)

    # Verbose output (matches original script format)
    if verbose:
        with pl.Config(tbl_rows=200, tbl_cols=10, fmt_str_lengths=30):
            print(result)
        print()

    return result
```

**Design Decisions**:

- **Returns DataFrame, not scalar**: The function returns the filtered/deduped DataFrame rather than the aggregated scalar. This matches the existing scripts' pattern where the caller prints both per-row details (verbose) and the aggregate total.
- **Sort order**: Sorting by dedup_keys matches the existing scripts' `sort("vertical", "office_phone")` behavior since the dedup_keys for offer metrics are `["office_phone", "vertical"]`. Note: the existing scripts sort by `("vertical", "office_phone")` but the dedup_keys are declared as `["office_phone", "vertical"]`. The sort in `compute_metric` will sort by `["office_phone", "vertical"]` -- this is the one intentional difference from the original scripts. If exact sort-order parity is required, a `sort_keys` field can be added to Scope.

**ADR-ML-001**: Sort order deviation from original scripts.

**Context**: The original `calc_mrr.py` sorts by `("vertical", "office_phone")` while the natural `dedup_keys` ordering is `["office_phone", "vertical"]`.

**Decision**: Accept the sort order difference. The sort affects only verbose output ordering, not the computed totals. Adding a separate `sort_keys` field to Scope adds complexity for no business value.

**Consequences**: Verbose output rows may appear in a different order. Totals are identical.

### 4.6 OfferSection Enum

**File**: `src/autom8_asana/models/business/sections.py`

```python
from __future__ import annotations

from enum import Enum


class OfferSection(str, Enum):
    """Section GIDs for the Business Offers project (1143843662099250).

    Maps human-readable section names to their Asana GIDs. These are
    hardcoded for Phase 1; dynamic resolution via Asana API is planned
    for a future phase.

    Usage:
        >>> from autom8_asana.models.business.sections import OfferSection
        >>> section_gid = OfferSection.ACTIVE.value
        >>> # "1143843662099256"
    """

    ACTIVE = "1143843662099256"
    # Future sections can be added as GIDs are identified:
    # PAUSED = "..."
    # CANCELLED = "..."
    # ONBOARDING = "..."
```

**Design Decisions**:

- Only ACTIVE is defined in Phase 1 because it is the only section GID used by the scripts being replaced. Additional sections will be added as their GIDs are confirmed.
- `str, Enum` inheritance allows direct use as a string (e.g., in S3 key construction) without `.value`.

### 4.7 Metric Definitions (offer.py)

**File**: `src/autom8_asana/metrics/definitions/offer.py`

```python
"""Offer-level metric definitions.

Registered automatically when autom8_asana.metrics.definitions is imported
(triggered by MetricRegistry._ensure_initialized).

Metrics defined here:
- active_mrr: Total MRR for ACTIVE offers
- active_ad_spend: Total weekly ad spend for ACTIVE offers
"""

from __future__ import annotations

import polars as pl

from autom8_asana.metrics.expr import MetricExpr
from autom8_asana.metrics.metric import Metric, Scope
from autom8_asana.metrics.registry import MetricRegistry
from autom8_asana.models.business.sections import OfferSection

# Shared scope: ACTIVE offers deduped by (office_phone, vertical)
_ACTIVE_OFFER_SCOPE = Scope(
    entity_type="offer",
    section=OfferSection.ACTIVE,
    dedup_keys=["office_phone", "vertical"],
)

ACTIVE_MRR = Metric(
    name="active_mrr",
    description="Total MRR for ACTIVE offers, deduped by phone+vertical",
    expr=MetricExpr(
        name="sum_mrr",
        column="mrr",
        cast_dtype=pl.Float64,
        agg="sum",
        filter_expr=pl.col("mrr").is_not_null() & (pl.col("mrr") > 0),
    ),
    scope=_ACTIVE_OFFER_SCOPE,
)

ACTIVE_AD_SPEND = Metric(
    name="active_ad_spend",
    description="Total weekly ad spend for ACTIVE offers, deduped by phone+vertical",
    expr=MetricExpr(
        name="sum_weekly_ad_spend",
        column="weekly_ad_spend",
        cast_dtype=pl.Float64,
        agg="sum",
        filter_expr=(
            pl.col("weekly_ad_spend").is_not_null()
            & (pl.col("weekly_ad_spend") > 0)
        ),
    ),
    scope=_ACTIVE_OFFER_SCOPE,
)

# Auto-register with singleton
_registry = MetricRegistry()
_registry.register(ACTIVE_MRR)
_registry.register(ACTIVE_AD_SPEND)
```

### 4.8 Definitions __init__.py (Auto-Import)

**File**: `src/autom8_asana/metrics/definitions/__init__.py`

```python
"""Auto-import all metric definition modules.

When this package is imported (by MetricRegistry._ensure_initialized),
all submodules are imported, triggering their module-level registration
with the MetricRegistry singleton.

To add new metrics: create a new .py file in this directory that
instantiates Metric objects and calls MetricRegistry().register().
"""

from autom8_asana.metrics.definitions import offer  # noqa: F401

# Future definition modules:
# from autom8_asana.metrics.definitions import unit  # noqa: F401
# from autom8_asana.metrics.definitions import business  # noqa: F401
```

**Design Decision**: Explicit imports rather than dynamic `importlib` scanning. This is intentional -- explicit imports are greppable, fail loudly if a module is missing, and don't introduce the complexity of runtime module discovery. When the number of definition files grows past ~10, dynamic scanning can be reconsidered.

### 4.9 Metrics Package __init__.py

**File**: `src/autom8_asana/metrics/__init__.py`

```python
"""Metrics layer for declarative metric computation.

Public API:
    MetricExpr   - Column aggregation expression
    Metric       - Named, scoped metric definition
    Scope        - Data scope (entity type, section, dedup)
    MetricRegistry - Singleton registry of metric definitions
    compute_metric - Execute a metric against a DataFrame
"""

from autom8_asana.metrics.compute import compute_metric
from autom8_asana.metrics.expr import MetricExpr
from autom8_asana.metrics.metric import Metric, Scope
from autom8_asana.metrics.registry import MetricRegistry

__all__ = [
    "MetricExpr",
    "Metric",
    "Scope",
    "MetricRegistry",
    "compute_metric",
]
```

### 4.10 Unified CLI Script

**File**: `scripts/calc_metric.py`

```python
#!/usr/bin/env python3
"""Calculate metrics from Business Offers section parquets.

Unified CLI replacing calc_mrr.py and calc_ad_spend.py.

Usage:
    python scripts/calc_metric.py active_mrr
    python scripts/calc_metric.py active_ad_spend --verbose
    python scripts/calc_metric.py --list

Environment Variables:
    ASANA_CACHE_S3_BUCKET  - S3 bucket for persistence (required)
    ASANA_CACHE_S3_REGION  - AWS region (default: us-east-1)
"""

from __future__ import annotations

import argparse
import io
import os
import sys

import boto3
import polars as pl

from autom8_asana.metrics import MetricRegistry, compute_metric


# Business Offers project GID (same as Offer.PRIMARY_PROJECT_GID)
PROJECT_GID = "1143843662099250"


def load_section_parquet(bucket: str, project_gid: str, section_gid: str) -> pl.DataFrame:
    """Load a section parquet from S3.

    Reads from the same S3 key structure used by SectionPersistence:
        dataframes/{project_gid}/sections/{section_gid}.parquet

    Args:
        bucket: S3 bucket name.
        project_gid: Asana project GID.
        section_gid: Asana section GID.

    Returns:
        Polars DataFrame from the parquet file.

    Raises:
        botocore.exceptions.ClientError: If the S3 object doesn't exist.
    """
    region = os.environ.get("ASANA_CACHE_S3_REGION", "us-east-1")
    s3 = boto3.client("s3", region_name=region)

    key = f"dataframes/{project_gid}/sections/{section_gid}.parquet"
    response = s3.get_object(Bucket=bucket, Key=key)
    buf = io.BytesIO(response["Body"].read())
    return pl.read_parquet(buf)


def main() -> None:
    registry = MetricRegistry()

    parser = argparse.ArgumentParser(
        description="Calculate metrics from Asana section data",
    )
    parser.add_argument(
        "metric",
        nargs="?",
        help="Metric name to compute (e.g., active_mrr, active_ad_spend)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show per-row breakdown",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_metrics",
        help="List all available metrics",
    )
    args = parser.parse_args()

    # --list mode
    if args.list_metrics:
        names = registry.list_metrics()
        print("Available metrics:")
        for name in names:
            metric = registry.get_metric(name)
            print(f"  {name:25s} {metric.description}")
        return

    # Require metric name
    if not args.metric:
        parser.error("metric name is required (or use --list)")

    # Look up metric
    try:
        metric = registry.get_metric(args.metric)
    except KeyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Load data
    bucket = os.environ.get("ASANA_CACHE_S3_BUCKET")
    if not bucket:
        print("ERROR: Set ASANA_CACHE_S3_BUCKET environment variable.", file=sys.stderr)
        sys.exit(1)

    if metric.scope.section is None:
        print("ERROR: Metrics without a section scope are not yet supported.", file=sys.stderr)
        sys.exit(1)

    df = load_section_parquet(bucket, PROJECT_GID, metric.scope.section)
    section_label = metric.scope.section  # Future: resolve to name via OfferSection
    print(f"Section {section_label}: {len(df)} tasks")

    # Compute
    result = compute_metric(metric, df, verbose=args.verbose)

    # Aggregate and display
    total = result[metric.expr.column].sum()
    if metric.scope.dedup_keys:
        dedup_desc = ", ".join(metric.scope.dedup_keys)
        print(f"Unique ({dedup_desc}) combos: {len(result)}")
    print(f"{metric.description}: ${total:,.0f}")


if __name__ == "__main__":
    main()
```

**Output Parity Analysis**:

Original `calc_mrr.py` output:
```
ACTIVE section: 80 tasks
Unique (office_phone, vertical) combos: 72
Total MRR: $47,500
```

New `calc_metric.py active_mrr` output:
```
Section 1143843662099256: 80 tasks
Unique (office_phone, vertical) combos: 72
Total MRR for ACTIVE offers, deduped by phone+vertical: $47,500
```

The output format differs slightly (section label shows GID instead of "ACTIVE", description line uses metric description). This is acceptable because:
1. The numeric values (task count, combo count, total) are identical.
2. The original scripts are being retired, not maintained in parallel.
3. If exact format parity is needed, the CLI can be adjusted to use OfferSection name resolution.

---

## 5. Key Flows

### 5.1 Metric Computation (Happy Path)

```
User                calc_metric.py       MetricRegistry       compute_metric        S3
 |                       |                    |                     |                |
 |-- active_mrr -------->|                    |                     |                |
 |                       |-- get_metric() --->|                     |                |
 |                       |                    |-- _ensure_init() -->|                |
 |                       |                    |   (imports offer.py)|                |
 |                       |<-- Metric ---------|                     |                |
 |                       |                    |                     |                |
 |                       |-- load_section_parquet() ----------------|-- GET obj ---->|
 |                       |<-- DataFrame --------------------------------- parquet --|
 |                       |                    |                     |                |
 |                       |-- compute_metric(metric, df) ----------->|                |
 |                       |                    |     select columns  |                |
 |                       |                    |     cast dtype      |                |
 |                       |                    |     apply filter    |                |
 |                       |                    |     deduplicate     |                |
 |                       |                    |     sort            |                |
 |                       |<-- deduped DataFrame -------------------|                |
 |                       |                    |                     |                |
 |                       |-- result["mrr"].sum()                    |                |
 |<-- print totals ------|                    |                     |                |
```

### 5.2 Metric Registration Flow

```
MetricRegistry._ensure_initialized()
    |
    +-- import autom8_asana.metrics.definitions
         |
         +-- import autom8_asana.metrics.definitions.offer
              |
              +-- ACTIVE_MRR = Metric(...)
              +-- ACTIVE_AD_SPEND = Metric(...)
              +-- MetricRegistry().register(ACTIVE_MRR)
              +-- MetricRegistry().register(ACTIVE_AD_SPEND)
```

### 5.3 Error Flow: Unknown Metric

```
User                calc_metric.py       MetricRegistry
 |                       |                    |
 |-- bad_name ---------->|                    |
 |                       |-- get_metric() --->|
 |                       |                    |-- _ensure_init()
 |                       |                    |-- KeyError: "Unknown metric 'bad_name'.
 |                       |                    |    Available: active_ad_spend, active_mrr"
 |                       |<-- KeyError -------|
 |<-- ERROR: ... --------|
 |   (exit code 1)       |
```

---

## 6. Data Model

### 6.1 Class Relationships

```
MetricRegistry (singleton)
    |
    +-- _metrics: dict[str, Metric]
                            |
                            +-- name: str
                            +-- description: str
                            +-- expr: MetricExpr
                            |       +-- name: str
                            |       +-- column: str
                            |       +-- cast_dtype: pl.DataType | None
                            |       +-- agg: str
                            |       +-- filter_expr: pl.Expr | None
                            |
                            +-- scope: Scope
                                    +-- entity_type: str
                                    +-- section: str | None
                                    +-- dedup_keys: list[str] | None
                                    +-- pre_filters: list[pl.Expr] | None
```

### 6.2 OfferSection Enum Values

| Name | GID | Source |
|------|-----|--------|
| ACTIVE | `1143843662099256` | From `calc_mrr.py` / `calc_ad_spend.py` |

---

## 7. Error Handling

| Error Scenario | Handling | User-Facing Message |
|----------------|----------|---------------------|
| Unknown metric name | `KeyError` from registry | `ERROR: Unknown metric 'x'. Available: ...` |
| Missing S3 bucket env var | Check before loading | `ERROR: Set ASANA_CACHE_S3_BUCKET environment variable.` |
| S3 object not found | `botocore.exceptions.ClientError` propagates | Stack trace (acceptable for CLI scripts) |
| Column not in DataFrame | `pl.exceptions.ColumnNotFoundError` propagates | Stack trace with column name |
| Invalid aggregation function | `ValueError` at MetricExpr construction | `Unsupported aggregation 'xyz'. Must be one of: count, max, mean, min, sum` |
| Duplicate metric registration | `ValueError` from registry | `Metric 'x' already registered. Existing: ...` |

---

## 8. Performance Considerations

### 8.1 Phase 1 Constraints

- **Single section, single metric**: Each CLI invocation loads one section parquet and computes one metric. No cross-section or multi-metric optimization is needed.
- **In-memory processing**: Section parquets are small (~80-200 rows for offer data). All operations are in-memory Polars expressions with sub-second execution.
- **S3 latency dominates**: The `load_section_parquet()` call is the bottleneck (~200-500ms). Metric computation is negligible.

### 8.2 Future Optimization (Phase 2+)

- **Multi-metric computation**: Load the DataFrame once, compute multiple metrics. Requires `compute_metrics(metrics: list[Metric], df)` variant.
- **Cached S3 reads**: If the CLI is called repeatedly, a local file cache could avoid redundant S3 reads.

---

## 9. Security Considerations

This design has no security-sensitive components:
- No authentication/authorization flows
- No PII processing (office_phone is a business phone, not personal)
- No external integrations beyond existing S3 access
- No new API endpoints
- Reads existing S3 data using existing IAM credentials

Threat modeling consultation is not required per the trigger domain checklist.

---

## 10. Test Strategy

### 10.1 Unit Tests

**File**: `tests/unit/metrics/test_expr.py`

| Test | Description |
|------|-------------|
| `test_metric_expr_to_polars_sum` | `MetricExpr(agg="sum")` produces `col.sum().alias(name)` |
| `test_metric_expr_to_polars_with_cast` | Cast dtype is applied with `strict=False` |
| `test_metric_expr_to_polars_count` | `agg="count"` produces `.count()` |
| `test_metric_expr_to_polars_mean` | `agg="mean"` produces `.mean()` |
| `test_metric_expr_invalid_agg` | Raises `ValueError` for unsupported agg |
| `test_metric_expr_frozen` | Cannot mutate attributes after creation |

**File**: `tests/unit/metrics/test_registry.py`

| Test | Description |
|------|-------------|
| `test_registry_singleton` | Two calls to `MetricRegistry()` return same instance |
| `test_registry_reset` | `reset()` clears singleton; next call creates new instance |
| `test_register_and_get` | Register a metric, retrieve by name |
| `test_get_unknown_raises_key_error` | `get_metric("nonexistent")` raises `KeyError` with available names |
| `test_duplicate_register_same_object` | Re-registering same Metric is idempotent |
| `test_duplicate_register_different_object` | Registering different Metric with same name raises `ValueError` |
| `test_list_metrics_sorted` | `list_metrics()` returns names in alphabetical order |
| `test_lazy_initialization` | Definitions not loaded until first access |

**File**: `tests/unit/metrics/test_compute.py`

| Test | Description |
|------|-------------|
| `test_compute_basic_sum` | Sum of a column with no filters or dedup |
| `test_compute_with_cast` | String column cast to Float64 before aggregation |
| `test_compute_with_filter` | Rows failing filter_expr are excluded |
| `test_compute_with_dedup` | Duplicate rows removed by dedup_keys |
| `test_compute_with_pre_filters` | Scope pre_filters applied |
| `test_compute_deterministic_sort` | Output sorted by dedup_keys |
| `test_compute_verbose_output` | Verbose mode prints table to stdout (capsys) |
| `test_compute_null_handling` | Null values in metric column handled correctly |
| `test_compute_empty_dataframe` | Empty input returns empty output |

**File**: `tests/unit/metrics/test_definitions.py`

| Test | Description |
|------|-------------|
| `test_active_mrr_definition` | ACTIVE_MRR has correct column, agg, scope |
| `test_active_ad_spend_definition` | ACTIVE_AD_SPEND has correct column, agg, scope |
| `test_definitions_registered` | Both metrics appear in `list_metrics()` |

**File**: `tests/unit/models/business/test_sections.py`

| Test | Description |
|------|-------------|
| `test_offer_section_active_value` | `OfferSection.ACTIVE == "1143843662099256"` |
| `test_offer_section_is_str` | Can use OfferSection.ACTIVE directly as string |

### 10.2 Integration Tests

**File**: `tests/integration/metrics/test_metric_parity.py`

These tests verify output parity between the old scripts and the new metrics layer by constructing a synthetic DataFrame that matches the parquet schema and running both code paths.

| Test | Description |
|------|-------------|
| `test_mrr_parity` | `compute_metric(ACTIVE_MRR, df)["mrr"].sum()` equals `calc_mrr(df)["mrr"].sum()` |
| `test_ad_spend_parity` | `compute_metric(ACTIVE_AD_SPEND, df)["weekly_ad_spend"].sum()` equals `calc_ad_spend(df)["weekly_ad_spend"].sum()` |
| `test_dedup_count_parity` | Row counts match between old and new for both metrics |

### 10.3 Test Fixtures

```python
@pytest.fixture
def sample_offer_df() -> pl.DataFrame:
    """Synthetic ACTIVE section DataFrame matching parquet schema."""
    return pl.DataFrame({
        "name": ["Offer A", "Offer B", "Offer C", "Offer D"],
        "office_phone": ["555-0001", "555-0001", "555-0002", "555-0003"],
        "vertical": ["dental", "dental", "dental", "med_spa"],
        "mrr": ["1000", "2000", "1500", None],
        "weekly_ad_spend": ["500", "600", None, "200"],
    })
```

Expected results for this fixture:
- **active_mrr**: Dedup by (office_phone, vertical) keeps Offer A and Offer C and Offer D. Offer D has null MRR so is filtered. Result: 1000 + 1500 = 2500.
- **active_ad_spend**: Dedup keeps Offer A, Offer C, Offer D. Offer C has null ad_spend so is filtered. Result: 500 + 200 = 700.

---

## 11. Migration Plan

### 11.1 Phase 1 Rollout

1. Implement metrics layer (all files in Section 3).
2. Write and pass all unit tests.
3. Write and pass integration parity tests.
4. Add `calc_metric.py` to scripts/.
5. Verify manually: `calc_metric.py active_mrr` vs `calc_mrr.py` against live S3 data.
6. Update any documentation referencing the old scripts.
7. Old scripts (`calc_mrr.py`, `calc_ad_spend.py`) are NOT deleted in Phase 1. They remain as reference until the team confirms the new CLI is working correctly.

### 11.2 Post-Phase 1 Cleanup

- Delete `scripts/calc_mrr.py` and `scripts/calc_ad_spend.py`.
- Add new metric definitions as needed (e.g., paused_mrr, total_offers_count).

---

## 12. Architecture Decision Records

### ADR-ML-001: Sort Order in compute_metric

**Status**: ACCEPTED

**Context**: The original scripts sort by `("vertical", "office_phone")` for verbose output. The metrics layer sorts by `dedup_keys` which may be `["office_phone", "vertical"]` -- a different column order.

**Decision**: Sort by `dedup_keys` order. Do not introduce a separate `sort_keys` field.

**Rationale**: Sort order affects only the visual layout of verbose output. The computed totals are identical regardless of sort order. Adding a `sort_keys` field to Scope increases the API surface for zero business value. If exact sort parity matters, `dedup_keys` can be reordered in the metric definition.

**Consequences**: Verbose output rows may appear in a different column-sort order than the original scripts. This is cosmetic only.

### ADR-ML-002: Explicit Definition Imports vs Dynamic Discovery

**Status**: ACCEPTED

**Context**: The `definitions/__init__.py` module needs to ensure all definition modules are imported so their metrics get registered. Two approaches: (a) explicit `from .offer import ...` lines, (b) dynamic `importlib` scanning of the directory.

**Decision**: Use explicit imports in `definitions/__init__.py`.

**Rationale**:
- Explicit imports are greppable and IDE-navigable.
- Missing modules cause immediate `ImportError` rather than silent omission.
- The number of definition files is expected to stay small (< 10) for the foreseeable future.
- Dynamic scanning adds ~15 lines of `importlib`/`pkgutil` complexity with no near-term benefit.

**Consequences**: Each new definition module requires adding one import line to `definitions/__init__.py`. This is acceptable overhead.

### ADR-ML-003: compute_metric Returns DataFrame, Not Scalar

**Status**: ACCEPTED

**Context**: `compute_metric` could return either (a) the aggregated scalar value, or (b) the filtered/deduped DataFrame that the caller then aggregates.

**Decision**: Return the filtered/deduped DataFrame.

**Rationale**:
- The existing scripts need both the row-level data (for verbose mode) and the aggregate (for the total line). Returning only the scalar would require a second function or a second pass for verbose output.
- Returning the DataFrame gives callers maximum flexibility: they can aggregate, inspect rows, or perform further analysis.
- The aggregation step is trivial: `result["column"].sum()`.

**Consequences**: Callers must perform one additional step to get the scalar. This is a minor inconvenience traded for significantly more flexibility.

### ADR-ML-004: No Thread Safety in Phase 1

**Status**: ACCEPTED

**Context**: The `MetricRegistry` singleton could use `threading.Lock` for thread-safe registration, as done in some production registries.

**Decision**: No thread safety mechanisms in Phase 1.

**Rationale**:
- Phase 1 usage is exclusively single-threaded CLI scripts.
- Adding locks increases complexity and import cost for zero benefit.
- Thread safety can be added in Phase 2 if the registry is used in the API server.

**Consequences**: The registry is NOT safe for concurrent registration from multiple threads. This is acceptable for Phase 1 CLI usage.

---

## 13. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Parquet schema changes break column access | Low | Medium | `ColumnNotFoundError` provides clear error; add schema validation in Phase 2 |
| Section GID changes in Asana | Very Low | High | GIDs are stable identifiers in Asana; if changed, update `OfferSection` enum |
| New metric definitions have subtle filter bugs | Medium | Medium | Parity tests against original scripts; require tests for each new definition |
| `pl.Expr` serialization issues in frozen dataclass | Low | Low | Polars expressions are immutable by design; `frozen=True` adds Python-level immutability |

---

## 14. Artifact Attestation

| Artifact | Absolute Path | Status |
|----------|--------------|--------|
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-metrics-layer-phase-1.md` | WRITTEN |
