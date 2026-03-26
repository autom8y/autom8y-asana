"""Post-build cascade validation for progressive builder.

Per TDD-CASCADE-FAILURE-FIXES-001 Fix 3: Validates cascade-critical fields
after section merge and re-resolves from live store when stale values detected.

Per ADR-cascade-contract-policy: Also provides ``audit_cascade_key_nulls()``
which emits a structured ``cascade_key_null_audit`` log event reporting
per-column null rates for cascade-sourced key columns after corrections are
applied.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger
from opentelemetry import trace as _otel_trace

if TYPE_CHECKING:
    from autom8_asana.cache.providers.unified import UnifiedTaskStore
    from autom8_asana.dataframes.models.schema import DataFrameSchema
    from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin

logger = get_logger(__name__)

# Cascade null rate thresholds (per ADR-cascade-contract-policy,
# calibrated against SCAR-005's 30% production incident).
CASCADE_NULL_WARN_THRESHOLD = 0.05  # 5% null rate -> WARNING
CASCADE_NULL_ERROR_THRESHOLD = 0.20  # 20% null rate -> ERROR


@dataclass
class CascadeValidationResult:
    """Result of cascade validation pass."""

    rows_checked: int = 0
    rows_stale: int = 0
    rows_corrected: int = 0
    sections_affected: set[str] = field(default_factory=set)
    duration_ms: float = 0.0


async def validate_cascade_fields_async(
    merged_df: pl.DataFrame,
    store: UnifiedTaskStore,
    cascade_plugin: CascadeViewPlugin,
    project_gid: str,
    entity_type: str,
    *,
    schema: DataFrameSchema | None = None,
) -> tuple[pl.DataFrame, CascadeValidationResult]:
    """Validate and correct cascade-critical fields in merged DataFrame.

    For each row where a cascade-critical field is None, checks whether
    the hierarchy index has an ancestor that should provide the value.
    If the live store can resolve the value, updates the row.

    Args:
        merged_df: Merged DataFrame from all sections.
        store: UnifiedTaskStore for parent chain lookups.
        cascade_plugin: CascadeViewPlugin for field resolution.
        project_gid: Project GID for logging.
        entity_type: Entity type for logging.
        schema: Optional DataFrameSchema. When provided, cascade columns
            are derived dynamically via ``schema.get_cascade_columns()``.
            When None, no fields are validated (safe degradation).

    Returns:
        Tuple of (corrected DataFrame, validation result).
        DataFrame is the same object if no corrections needed.
    """
    start = time.perf_counter()
    result = CascadeValidationResult()

    if "gid" not in merged_df.columns:
        result.duration_ms = (time.perf_counter() - start) * 1000
        return merged_df, result

    hierarchy = store.get_hierarchy_index()
    corrections: dict[int, dict[str, Any]] = {}  # row_index -> {col: value}

    cascade_fields = schema.get_cascade_columns() if schema is not None else []
    for col_name, cascade_field_name in cascade_fields:
        if col_name not in merged_df.columns:
            continue

        # Find rows where the cascade field is null
        null_mask = merged_df[col_name].is_null()
        null_indices = null_mask.arg_true().to_list()

        for row_idx in null_indices:
            result.rows_checked += 1
            gid = merged_df["gid"][row_idx]

            if gid is None:
                continue

            # Check if hierarchy index has ancestors for this task
            ancestor_gids = hierarchy.get_ancestor_chain(str(gid), max_depth=5)
            if not ancestor_gids:
                continue

            # Try to resolve the cascade field from live store
            parent_chain = await store.get_parent_chain_async(str(gid))
            if not parent_chain:
                continue

            # Search parent chain for field value using cascade-aware resolution.
            # Per GAP-A fix: use get_field_value() which handles source_field
            # (e.g., "Business Name" -> Task.name) instead of searching custom_fields only.
            from autom8_asana.models.business.fields import get_cascading_field
            from autom8_asana.dataframes.views.cf_utils import (
                get_field_value,
                get_custom_field_value,
            )

            field_entry = get_cascading_field(cascade_field_name)
            for parent_data in parent_chain:
                if field_entry is not None:
                    _owner_class, field_def = field_entry
                    value = get_field_value(parent_data, field_def)
                else:
                    # Fallback for unregistered cascade fields
                    value = get_custom_field_value(parent_data, cascade_field_name)
                if value is not None:
                    result.rows_stale += 1
                    if row_idx not in corrections:
                        corrections[row_idx] = {}
                    corrections[row_idx][col_name] = value

                    # Track affected section for re-persistence
                    if "section_gid" in merged_df.columns:
                        section_gid = merged_df["section_gid"][row_idx]
                        if section_gid is not None:
                            result.sections_affected.add(str(section_gid))
                    break

    # Apply corrections if any
    if corrections:
        # Build correction series for each column
        for col_name, _ in cascade_fields:
            if col_name not in merged_df.columns:
                continue

            col_corrections = {
                idx: vals[col_name]
                for idx, vals in corrections.items()
                if col_name in vals
            }
            if col_corrections:
                # Create updated column
                values = merged_df[col_name].to_list()
                for idx, val in col_corrections.items():
                    values[idx] = val
                    result.rows_corrected += 1
                merged_df = merged_df.with_columns(
                    pl.Series(col_name, values).cast(merged_df[col_name].dtype)
                )

    result.duration_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "cascade_validation_complete",
        extra={
            "project_gid": project_gid,
            "entity_type": entity_type,
            "rows_checked": result.rows_checked,
            "rows_stale": result.rows_stale,
            "rows_corrected": result.rows_corrected,
            "sections_affected": list(result.sections_affected),
            "duration_ms": round(result.duration_ms, 2),
        },
    )

    return merged_df, result


# ---------------------------------------------------------------------------
# Cascade key null rate audit (ADR-cascade-contract-policy)
# ---------------------------------------------------------------------------

# Maps cascade field names to their source entity.  Used by the audit
# to annotate log events so operators know where the cascade originates.
_CASCADE_SOURCE_MAP: dict[str, str] = {
    "Office Phone": "business",
    "Vertical": "unit",
    "Business Name": "business",
    "MRR": "unit",
    "Weekly Ad Spend": "unit",
}


def audit_cascade_key_nulls(
    df: pl.DataFrame,
    entity_type: str,
    project_gid: str,
    *,
    schema: DataFrameSchema | None = None,
    key_columns: tuple[str, ...] = (),
) -> None:
    """Emit a structured log event reporting null rates for cascade key columns.

    Runs *after* ``validate_cascade_fields_async`` so that the reported
    null rates reflect the post-correction state.  Only columns that are
    both cascade-sourced AND listed in the entity's ``key_columns`` are
    audited -- these are the columns where a null means the row will be
    excluded from the DynamicIndex and resolution returns NOT_FOUND.

    Severity thresholds (per ADR-cascade-contract-policy):
        - null_rate > 5%  -> WARNING
        - null_rate > 20% -> ERROR

    Args:
        df: Post-correction DataFrame.
        entity_type: Entity type name (e.g. "unit", "offer").
        project_gid: Project GID for log context.
        schema: DataFrameSchema to derive cascade columns.  When None
            the audit is silently skipped (safe degradation).
        key_columns: Tuple of column names that are key columns for
            DynamicIndex resolution (from ``EntityDescriptor.key_columns``).
    """
    if schema is None or df.is_empty():
        return

    cascade_columns = schema.get_cascade_columns()
    if not cascade_columns:
        return

    key_set = set(key_columns)
    total_rows = len(df)

    cascade_key_nulls: dict[str, dict[str, object]] = {}
    max_severity = "ok"

    for col_name, cascade_field_name in cascade_columns:
        # Only audit columns that are both cascade-sourced AND key columns.
        if col_name not in key_set:
            continue
        if col_name not in df.columns:
            continue

        null_count = int(df[col_name].null_count())
        null_rate = null_count / total_rows if total_rows > 0 else 0.0

        cascade_key_nulls[col_name] = {
            "null_count": null_count,
            "null_rate": round(null_rate, 6),
            "cascade_source": cascade_field_name,
            "source_entity": _CASCADE_SOURCE_MAP.get(cascade_field_name, "unknown"),
        }

        if null_rate > CASCADE_NULL_ERROR_THRESHOLD:
            max_severity = "error"
        elif null_rate > CASCADE_NULL_WARN_THRESHOLD and max_severity != "error":
            max_severity = "warning"

    if not cascade_key_nulls:
        return

    # Attach cascade audit attributes to the ambient span (computation.progressive.build).
    # trace.get_current_span() returns a no-op span when no span is active -- set_attribute
    # calls are safe no-ops in that case.
    _span = _otel_trace.get_current_span()
    _span.set_attribute("computation.cascade_audit.entity_type", entity_type)
    _span.set_attribute("computation.cascade_audit.total_rows", total_rows)
    _span.set_attribute("computation.cascade_audit.max_severity", max_severity)
    _span.set_attribute(
        "computation.cascade_audit.null_column_count", len(cascade_key_nulls)
    )

    if max_severity in ("warning", "error"):
        columns_at_warning = ",".join(
            col
            for col, data in cascade_key_nulls.items()
            if float(data["null_rate"]) > CASCADE_NULL_WARN_THRESHOLD  # type: ignore[arg-type]
        )
        if columns_at_warning:
            _span.set_attribute(
                "computation.cascade_audit.columns_at_warning", columns_at_warning
            )

    if max_severity == "error":
        columns_at_error = ",".join(
            col
            for col, data in cascade_key_nulls.items()
            if float(data["null_rate"]) > CASCADE_NULL_ERROR_THRESHOLD  # type: ignore[arg-type]
        )
        if columns_at_error:
            _span.set_attribute(
                "computation.cascade_audit.columns_at_error", columns_at_error
            )

    extra = {
        "entity_type": entity_type,
        "project_gid": project_gid,
        "total_rows": total_rows,
        "cascade_key_nulls": cascade_key_nulls,
        "severity": max_severity,
    }

    if max_severity == "error":
        logger.error("cascade_key_null_audit", extra=extra)
    elif max_severity == "warning":
        logger.warning("cascade_key_null_audit", extra=extra)
    else:
        logger.info("cascade_key_null_audit", extra=extra)


# ---------------------------------------------------------------------------
# Display-column null rate audit (GAP-A observability, sprint-4)
# ---------------------------------------------------------------------------


def audit_cascade_display_nulls(
    df: pl.DataFrame,
    entity_type: str,
    project_gid: str,
    *,
    schema: DataFrameSchema | None = None,
    key_columns: tuple[str, ...] = (),
) -> None:
    """Emit structured log + OTel span attributes for cascade display-column null rates.

    Complements ``audit_cascade_key_nulls`` by reporting null rates for
    cascade-sourced columns that are NOT key columns (e.g., ``office``).
    These are display-only columns — nulls do not affect resolution, but
    degrade report readability.

    Always emits at INFO level — no threshold enforcement.

    Per GAP-A sprint-4: Makes the Offer ``office`` null rate visible in
    operational telemetry so before/after remediation can be measured.
    """
    if schema is None or df.is_empty():
        return

    cascade_columns = schema.get_cascade_columns()
    if not cascade_columns:
        return

    key_set = set(key_columns)
    total_rows = len(df)

    display_nulls: dict[str, dict[str, object]] = {}

    for col_name, cascade_field_name in cascade_columns:
        # Only audit display columns (cascade-sourced but NOT key columns)
        if col_name in key_set:
            continue
        if col_name not in df.columns:
            continue

        null_count = int(df[col_name].null_count())
        null_rate = null_count / total_rows if total_rows > 0 else 0.0

        display_nulls[col_name] = {
            "null_count": null_count,
            "null_rate": round(null_rate, 6),
            "cascade_source": cascade_field_name,
            "source_entity": _CASCADE_SOURCE_MAP.get(cascade_field_name, "unknown"),
        }

    if not display_nulls:
        return

    _span = _otel_trace.get_current_span()
    _span.set_attribute(
        "computation.cascade_audit.display_null_column_count", len(display_nulls)
    )
    for col_name, data in display_nulls.items():
        _span.set_attribute(
            f"computation.cascade_audit.display.{col_name}.null_rate",
            float(data["null_rate"]),  # type: ignore[arg-type]
        )

    logger.info(
        "cascade_display_null_audit",
        extra={
            "entity_type": entity_type,
            "project_gid": project_gid,
            "total_rows": total_rows,
            "cascade_display_nulls": display_nulls,
        },
    )


# ---------------------------------------------------------------------------
# Phone E.164 compliance audit (GAP-B observability, sprint-4)
# ---------------------------------------------------------------------------

_E164_PATTERN = r"^\+1\d{10}$"


def audit_phone_e164_compliance(
    df: pl.DataFrame,
    entity_type: str,
    project_gid: str,
) -> None:
    """Emit structured log + OTel span attributes for phone E.164 compliance rate.

    Checks ``office_phone`` column values against the E.164 pattern
    (``+1XXXXXXXXXX`` for US numbers). Reports the compliance rate as a
    span attribute and structured log event.

    Per GAP-B sprint-4: Makes phone format compliance visible in operational
    telemetry so before/after normalization can be measured.
    """
    if df.is_empty() or "office_phone" not in df.columns:
        return

    import re

    total_rows = len(df)
    non_null = df.filter(pl.col("office_phone").is_not_null())
    non_null_count = len(non_null)

    if non_null_count == 0:
        return

    compliant_count = int(
        non_null.filter(pl.col("office_phone").str.contains(_E164_PATTERN)).height
    )
    compliance_rate = compliant_count / non_null_count
    non_compliant_count = non_null_count - compliant_count

    _span = _otel_trace.get_current_span()
    _span.set_attribute("computation.phone_audit.entity_type", entity_type)
    _span.set_attribute("computation.phone_audit.total_phones", non_null_count)
    _span.set_attribute("computation.phone_audit.e164_compliant", compliant_count)
    _span.set_attribute(
        "computation.phone_audit.e164_compliance_rate", round(compliance_rate, 6)
    )

    logger.info(
        "phone_e164_compliance_audit",
        extra={
            "entity_type": entity_type,
            "project_gid": project_gid,
            "total_phones": non_null_count,
            "e164_compliant": compliant_count,
            "non_compliant": non_compliant_count,
            "compliance_rate": round(compliance_rate, 6),
        },
    )


# ---------------------------------------------------------------------------
# Cascade health check (Sprint 1: CascadeNotReadyError enforcement)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CascadeHealthResult:
    """Result of cascade health check.

    Attributes:
        healthy: True if all cascade key columns are below error threshold.
        degraded_columns: Dict of column_name -> null_rate for columns exceeding threshold.
        max_null_rate: Highest null rate observed, or 0.0 if all healthy.
    """

    healthy: bool
    degraded_columns: dict[str, float]
    max_null_rate: float


def check_cascade_health(
    df: pl.DataFrame,
    entity_type: str,
    schema: DataFrameSchema,
    key_columns: tuple[str, ...],
) -> CascadeHealthResult:
    """Check whether cascade-sourced key columns meet the health threshold.

    Examines each column that is BOTH cascade-sourced (per schema) AND a key
    column for DynamicIndex resolution (per EntityDescriptor.key_columns).
    A column is degraded if its null rate exceeds CASCADE_NULL_ERROR_THRESHOLD.

    This function is pure computation -- no logging, no side effects. The
    caller decides how to act on the result (raise, log, ignore).

    Args:
        df: Post-build DataFrame to check.
        entity_type: Entity type name (for diagnostics only).
        schema: DataFrameSchema with cascade column metadata.
        key_columns: Key columns from EntityDescriptor.

    Returns:
        CascadeHealthResult indicating pass/fail with details.
    """
    if df.is_empty():
        return CascadeHealthResult(healthy=True, degraded_columns={}, max_null_rate=0.0)

    cascade_columns = schema.get_cascade_columns()
    if not cascade_columns:
        return CascadeHealthResult(healthy=True, degraded_columns={}, max_null_rate=0.0)

    key_set = set(key_columns)
    total_rows = len(df)
    degraded: dict[str, float] = {}
    max_rate = 0.0

    for col_name, _cascade_field_name in cascade_columns:
        # Only check columns that are both cascade-sourced AND key columns
        if col_name not in key_set:
            continue
        if col_name not in df.columns:
            continue

        null_count = int(df[col_name].null_count())
        null_rate = null_count / total_rows

        if null_rate > max_rate:
            max_rate = null_rate

        if null_rate > CASCADE_NULL_ERROR_THRESHOLD:
            degraded[col_name] = null_rate

    healthy = len(degraded) == 0
    return CascadeHealthResult(
        healthy=healthy,
        degraded_columns=degraded,
        max_null_rate=max_rate,
    )
