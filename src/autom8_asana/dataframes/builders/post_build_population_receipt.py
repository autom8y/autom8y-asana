"""Post-build value-population receipt (FM-4, ADR-SEAM1 Decision 4).

A WARN-first (never hard-fail) attestation that the active-classified subset of a
warmed entity DataFrame actually carries non-null *economic value* columns. The
existing post-build validators audit cascade-sourced KEY columns (office_phone,
vertical) for resolution-readiness; this receipt is the missing assertion for the
VALUE columns (mrr, offer_id) that the active_mrr denominator is computed over.

The defect it catches (G-THEATER proof obligation #2): a "present-but-null"
economics frame -- 62 active offer rows whose ``mrr`` is entirely null -- passes
every existing gate silently (cascade key audits don't cover mrr; honest-empty-200
only checks row count). This receipt fires RED (population rate 0.0 < floor) so a
degraded warm is OBSERVABLE and alarmable.

Design (Decision 4):
- WARN-first: emits a structured ``logger.warning`` + OTel span attributes; it
  NEVER raises and NEVER changes the build's success/failure. A degraded-but-
  present warm must still serve (62 partially-populated rows beat an empty
  denominator); the receipt makes the degradation alarmable without 503ing.
- Active-subset scoped: the non-null rate is computed over rows the entity's
  classifier maps to ACTIVE/ACTIVATING -- the same population the active_mrr
  denominator uses (universal_strategy active_only filter). Inactive/ignored rows
  legitimately have null economics and must not drag the rate down.
- Entity-scoped: only entities that declare economic value columns (offer) are
  assessed. Section/project (no value columns) skip via an empty value-column set
  -- the same safe-degradation shape as the cascade audits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import polars as pl
from autom8y_log import get_logger
from opentelemetry import trace as _otel_trace

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import DataFrameSchema

__all__ = [
    "POPULATION_WARN_THRESHOLD",
    "PopulationReceipt",
    "post_build_population_receipt",
]

logger = get_logger(__name__)

# Non-null rate floor for the active-classified subset's value columns. Mirrors
# the cascade_validator threshold-constant convention (CASCADE_NULL_WARN_THRESHOLD
# = 0.05). 0.80 means: at least 80% of active rows must carry a non-null value in
# EACH declared value column, else WARN. A present-but-null frame (rate 0.0) is
# the RED signal.
POPULATION_WARN_THRESHOLD = 0.80

# Economic value columns per entity. Only entities listed here are assessed; all
# others (section, project, pipeline types) have an empty value-column set and the
# receipt is a no-op for them. Kept local to the receipt's concern (single
# responsibility) rather than mutating the frozen schema model.
_VALUE_COLUMNS_BY_ENTITY: dict[str, tuple[str, ...]] = {
    "offer": ("mrr", "offer_id"),
}

# Section names (lowercased) that count as "active" for the population subset.
# Matches universal_strategy._ACTIVE_STATUSES (ACTIVE + ACTIVATING).
_ACTIVE_ACTIVITY_VALUES = frozenset({"active", "activating"})


@dataclass(frozen=True)
class PopulationReceipt:
    """Outcome of the post-build value-population assessment.

    Attributes:
        entity_type: Entity type assessed.
        assessed: True if the entity declares value columns AND had a non-empty
            active subset (i.e., the receipt actually evaluated a rate). False
            means skipped (no value columns / no active rows / no classifier).
        active_rows: Number of rows in the active-classified subset.
        column_nonnull_rates: Per value-column non-null rate over the active
            subset (empty when not assessed).
        below_floor: True if any assessed column's rate < POPULATION_WARN_THRESHOLD.
        min_rate: Lowest per-column non-null rate observed (1.0 when not assessed).
    """

    entity_type: str
    assessed: bool
    active_rows: int
    column_nonnull_rates: dict[str, float]
    below_floor: bool
    min_rate: float


def _active_subset(
    merged_df: pl.DataFrame,
    entity_type: str,
) -> pl.DataFrame | None:
    """Return the rows whose ``section`` classifies to ACTIVE/ACTIVATING.

    Returns None when no classifier exists for the entity or the frame lacks a
    ``section`` column (cannot determine the active subset -> skip, not WARN).
    """
    from autom8_asana.models.business.activity import get_classifier

    classifier = get_classifier(entity_type)
    if classifier is None or "section" not in merged_df.columns:
        return None

    active_section_names = classifier.billable_sections()  # ACTIVE + ACTIVATING (lowercased)
    if not active_section_names:
        return None

    # Lowercase the section column and keep rows whose section maps to an active
    # category. is_completed=True is a terminal override (SD-6) -> not active.
    section_lower = pl.col("section").cast(pl.Utf8).str.to_lowercase()
    mask = section_lower.is_in(list(active_section_names))
    if "is_completed" in merged_df.columns:
        mask = mask & (~pl.col("is_completed").fill_null(False))
    return merged_df.filter(mask)


def post_build_population_receipt(
    merged_df: pl.DataFrame,
    schema: DataFrameSchema | None,
    entity_type: str,
    project_gid: str,
) -> PopulationReceipt:
    """Assess value-column population over the active-classified subset (WARN-first).

    Computes, for each economic value column declared for ``entity_type``, the
    non-null rate over the active-classified rows. Emits a structured WARNING +
    OTel span attributes when any column falls below ``POPULATION_WARN_THRESHOLD``.
    NEVER raises; NEVER changes build status.

    Args:
        merged_df: Final merged DataFrame for the warm.
        schema: Entity schema (used only to confirm declared columns exist;
            None -> skip safely).
        entity_type: Entity type string (selects the value-column set).
        project_gid: Project GID (log/span context).

    Returns:
        PopulationReceipt describing the assessment (assessed=False when skipped).
    """
    value_columns = _VALUE_COLUMNS_BY_ENTITY.get(entity_type, ())
    if not value_columns or schema is None or merged_df.is_empty():
        return PopulationReceipt(
            entity_type=entity_type,
            assessed=False,
            active_rows=0,
            column_nonnull_rates={},
            below_floor=False,
            min_rate=1.0,
        )

    # Only assess columns that are both declared in the schema AND present in the
    # frame (safe degradation if a column is missing for any reason).
    present_value_columns = [
        c for c in value_columns if schema.get_column(c) is not None and c in merged_df.columns
    ]
    if not present_value_columns:
        return PopulationReceipt(
            entity_type=entity_type,
            assessed=False,
            active_rows=0,
            column_nonnull_rates={},
            below_floor=False,
            min_rate=1.0,
        )

    try:
        active = _active_subset(merged_df, entity_type)
    except Exception as e:  # BROAD-CATCH: receipt is additive  # noqa: BLE001
        logger.warning(
            "population_receipt_subset_failed",
            extra={
                "entity_type": entity_type,
                "project_gid": project_gid,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return PopulationReceipt(
            entity_type=entity_type,
            assessed=False,
            active_rows=0,
            column_nonnull_rates={},
            below_floor=False,
            min_rate=1.0,
        )

    if active is None or active.is_empty():
        # No active subset to assess -> not a population defect, just no data.
        return PopulationReceipt(
            entity_type=entity_type,
            assessed=False,
            active_rows=0 if active is None else len(active),
            column_nonnull_rates={},
            below_floor=False,
            min_rate=1.0,
        )

    active_rows = len(active)
    rates: dict[str, float] = {}
    min_rate = 1.0
    for col in present_value_columns:
        non_null = active_rows - int(active[col].null_count())
        rate = non_null / active_rows if active_rows > 0 else 0.0
        rates[col] = round(rate, 6)
        min_rate = min(min_rate, rate)

    below_floor = min_rate < POPULATION_WARN_THRESHOLD

    # OTel span attributes (no-op span when none active).
    span = _otel_trace.get_current_span()
    span.set_attribute("computation.population_receipt.entity_type", entity_type)
    span.set_attribute("computation.population_receipt.active_rows", active_rows)
    span.set_attribute("computation.population_receipt.min_nonnull_rate", round(min_rate, 6))
    span.set_attribute("computation.population_receipt.below_floor", below_floor)

    extra = {
        "entity_type": entity_type,
        "project_gid": project_gid,
        "active_rows": active_rows,
        "value_columns": present_value_columns,
        "column_nonnull_rates": rates,
        "warn_threshold": POPULATION_WARN_THRESHOLD,
        "min_nonnull_rate": round(min_rate, 6),
    }

    if below_floor:
        # The RED signal. WARN-first: alarmable, but does NOT fail the warm.
        logger.warning("population_receipt_below_floor", extra=extra)
    else:
        logger.info("population_receipt_ok", extra=extra)

    return PopulationReceipt(
        entity_type=entity_type,
        assessed=True,
        active_rows=active_rows,
        column_nonnull_rates=rates,
        below_floor=below_floor,
        min_rate=min_rate,
    )
