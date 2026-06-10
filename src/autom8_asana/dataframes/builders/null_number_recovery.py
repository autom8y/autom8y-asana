"""Post-build path-canon recovery of stripped numeric custom-field cells (FPC Phase-2).

A field-agnostic, cache-reuse-only pass that re-populates null *numeric*
custom-field cells (``mrr``, ``weekly_ad_spend``, and any other ``cf:`` number
column) by re-reading the per-task cache copy that the hierarchy warm already
fetched. It runs post-build, BEFORE the value-population receipt, so the floor
receipt assesses a HEALED frame.

The defect it cures (FPC Phase-2, path-asymmetry null mechanism)
---------------------------------------------------------------
``BASE_OPT_FIELDS`` includes ``custom_fields.number_value``, so the full-section
fetch carries the number. The null arises on the GID-only warm path
(``parallel_fetch._fetch_section_gids`` lists with ``opt_fields=["gid"]`` then
hydrates from cache): when the section-list frame is built from a reduced-field
view, a populated ``number_value`` that DOES live in the standard-completeness
cache copy of the same task is dropped from the cell. The user's economics
question then gets a silent ``$0`` instead of the populated figure.

The cure re-reads the standard-completeness cache copy of each null-cell task and
backfills ONLY where the cache carries a genuinely non-null ``number_value``. A
cell whose cache copy is ALSO null (operator never entered the value, or the task
was warmed at MINIMAL completeness) stays honest-null -- the pass NEVER fabricates.

Invariants (HARD)
-----------------
1. **Cache-reuse only.** The single ``store.get_batch_async`` call uses
   ``FreshnessIntent.IMMEDIATE``, which returns ``entry.data`` for every
   cache-present-and-sufficient gid with ZERO freshness round-trips and ZERO
   Asana GETs. Cache-MISS gids map to ``None`` and are skipped (honest-null).
   There is NO live fallback on this path -- the single-worker receiver's
   SlowAPI budget (CR-3) is never charged. (PV-7 measured: warmed corpus =>
   0 GET delta; an N+1-per-null mutant => row-count GETs, which the regression
   guard catches RED.)
2. **IMMEDIATE freshness.** The just-warmed cache copy IS the post-warm
   truth-of-record; re-validating it would be both wasteful and a network hit.
3. **Never-fabricate.** A null-cache-AND-null-source cell stays null.
4. **Additive / never-raises.** Mirrors the population-receipt posture: a
   degraded-but-present warm must still serve; any failure logs a structured
   WARN and returns the frame unchanged.
5. **Warm path untouched.** This is a post-build heal; it does not change
   ``parallel_fetch`` opt_fields or the merge.

Field-agnosticism (G-PROPAGATE)
-------------------------------
The pass iterates every ``ColumnDef`` whose ``source`` is ``cf:<name>`` and whose
dtype is numeric. ``mrr`` and ``weekly_ad_spend`` heal through the SAME loop with
no per-field special-casing; any future numeric cf column heals for free. Columns
sourced via ``cascade:`` (e.g. offer ``mrr`` from an ancestor Unit) are out of
scope -- those re-derive from the healed ancestor, not from the task's own CF.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger
from opentelemetry import trace as _otel_trace

from autom8_asana.cache.models.completeness import CompletenessLevel
from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.dataframes.builders.fields import _coerce_value
from autom8_asana.dataframes.views.cf_utils import get_custom_field_value

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import DataFrameSchema

__all__ = [
    "NumericRecoveryReceipt",
    "recover_null_number_cells",
]

logger = get_logger(__name__)

# Polars dtype names that the recovery pass treats as numeric. Mirrors
# TypeCoercer.NUMERIC_DTYPES; kept local so the pass does not depend on the
# coercer's internals beyond the public _coerce_value entrypoint.
_NUMERIC_DTYPES: frozenset[str] = frozenset({"Decimal", "Float64", "Int64", "Int32"})

_CF_PREFIX = "cf:"


@dataclass(frozen=True)
class NumericRecoveryReceipt:
    """Outcome of the post-build numeric-cell recovery pass.

    Attributes:
        entity_type: Entity type assessed.
        attempted: True if the entity declared at least one numeric ``cf:``
            column AND the frame carried null cells in it (i.e. the pass made a
            cache read). False means a safe no-op (no eligible columns / no null
            cells / no store).
        columns: The numeric ``cf:`` column names considered.
        null_cells_before: Total null cells across the considered columns prior
            to the pass.
        healed_cells: Count of cells backfilled from a non-null cache value.
        residual_null_cells: Null cells remaining after the pass (cache-miss or
            genuinely-null source -- honest-null).
        cache_miss_gids: Number of distinct null-cell gids absent/insufficient in
            cache (the live-fallback residual stratum, which this pass leaves to
            an explicit, opt-in, ASANA-PAT-gated step -- never charged here).
    """

    entity_type: str
    attempted: bool
    columns: tuple[str, ...]
    null_cells_before: int
    healed_cells: int
    residual_null_cells: int
    cache_miss_gids: int
    healed_by_column: dict[str, int] = field(default_factory=dict)


def _numeric_cf_columns(schema: DataFrameSchema) -> list[tuple[str, str, str]]:
    """Return ``(column_name, cf_field_name, dtype)`` for numeric ``cf:`` columns.

    A column qualifies when its ``source`` is ``cf:<name>`` and its dtype is in
    ``_NUMERIC_DTYPES``. ``cascade:`` and non-numeric ``cf:`` columns are excluded.
    """
    out: list[tuple[str, str, str]] = []
    for col in schema.columns:
        source = col.source
        if not source or not source.startswith(_CF_PREFIX):
            continue
        if col.dtype not in _NUMERIC_DTYPES:
            continue
        cf_name = source[len(_CF_PREFIX) :].strip()
        if cf_name:
            out.append((col.name, cf_name, col.dtype))
    return out


async def recover_null_number_cells(
    merged_df: pl.DataFrame,
    schema: DataFrameSchema | None,
    store: Any | None,
    entity_type: str,
    project_gid: str,
) -> tuple[pl.DataFrame, NumericRecoveryReceipt]:
    """Backfill null numeric ``cf:`` cells from the warmed cache (cache-reuse only).

    Field-agnostic: heals every numeric ``cf:`` column (``mrr``,
    ``weekly_ad_spend``, ...) through one loop. Makes at most ONE
    ``store.get_batch_async`` call (IMMEDIATE freshness => zero Asana GETs for
    cached gids). Never fabricates; never raises; never changes build status.

    Args:
        merged_df: Final merged DataFrame for the warm.
        schema: Entity schema (selects numeric ``cf:`` columns; None -> no-op).
        store: UnifiedTaskStore exposing ``get_batch_async``; None -> no-op.
        entity_type: Entity type string (log/span context).
        project_gid: Project GID (log/span context).

    Returns:
        ``(healed_df, receipt)``. On any skip/failure, ``healed_df`` is the input
        frame unchanged and ``receipt.attempted`` is False.
    """
    no_op = NumericRecoveryReceipt(
        entity_type=entity_type,
        attempted=False,
        columns=(),
        null_cells_before=0,
        healed_cells=0,
        residual_null_cells=0,
        cache_miss_gids=0,
    )

    if schema is None or store is None or merged_df.is_empty() or "gid" not in merged_df.columns:
        return merged_df, no_op

    try:
        return await _recover_impl(merged_df, schema, store, entity_type, project_gid)
    except Exception as e:  # BROAD-CATCH: recovery is additive  # noqa: BLE001
        logger.warning(
            "null_number_recovery_failed",
            extra={
                "entity_type": entity_type,
                "project_gid": project_gid,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return merged_df, no_op


async def _recover_impl(
    merged_df: pl.DataFrame,
    schema: DataFrameSchema,
    store: Any,
    entity_type: str,
    project_gid: str,
) -> tuple[pl.DataFrame, NumericRecoveryReceipt]:
    """Inner recovery body (exceptions handled by the public wrapper)."""
    numeric_cols = _numeric_cf_columns(schema)
    # Only consider columns actually present in the frame.
    present_cols = [
        (name, cf_name, dtype)
        for (name, cf_name, dtype) in numeric_cols
        if name in merged_df.columns
    ]
    if not present_cols:
        return merged_df, NumericRecoveryReceipt(
            entity_type=entity_type,
            attempted=False,
            columns=(),
            null_cells_before=0,
            healed_cells=0,
            residual_null_cells=0,
            cache_miss_gids=0,
        )

    # Collect the union of gids that have a null in ANY considered numeric column.
    # One batch read serves every null cell across every column (a task's single
    # cache copy carries all of its CFs), so the read count is bounded by distinct
    # null-row gids, never by (rows x columns).
    null_any = pl.lit(False)  # noqa: FBT003 -- polars boolean literal seed
    for name, _cf_name, _dtype in present_cols:
        null_any = null_any | pl.col(name).is_null()
    null_rows = merged_df.filter(null_any & pl.col("gid").is_not_null())

    null_cells_before = sum(int(merged_df[name].null_count()) for name, _c, _d in present_cols)

    if null_rows.is_empty():
        return merged_df, NumericRecoveryReceipt(
            entity_type=entity_type,
            attempted=False,
            columns=tuple(name for name, _c, _d in present_cols),
            null_cells_before=null_cells_before,
            healed_cells=0,
            residual_null_cells=null_cells_before,
            cache_miss_gids=0,
        )

    null_gids: list[str] = [g for g in null_rows["gid"].to_list() if g is not None]

    # THE single cache read. IMMEDIATE => entry.data for cache-present-and-
    # STANDARD-sufficient gids, ZERO Asana GETs. STANDARD is the level that
    # guarantees custom_fields.number_value is materialized (see
    # completeness.STANDARD_FIELDS) and is the same level the progressive build
    # itself uses. Cache-MISS / sub-STANDARD gids map to None.
    cached: dict[str, dict[str, Any] | None] = await store.get_batch_async(
        null_gids,
        freshness=FreshnessIntent.IMMEDIATE,
        required_level=CompletenessLevel.STANDARD,
    )

    cache_miss_gids = sum(1 for g in null_gids if cached.get(g) is None)

    # Build per-column {gid: healed_value} maps. NEVER fabricate: only when the
    # cached CF carries a non-null number_value (coerced through the SAME merge-
    # path coercer the warm used, so dtype-parity with the existing column holds).
    healed_by_column: dict[str, int] = {}
    replacement_exprs: list[pl.Expr] = []

    for name, cf_name, dtype in present_cols:
        value_by_gid: dict[str, Any] = {}
        for gid in null_gids:
            task_data = cached.get(gid)
            if task_data is None:
                continue
            raw = get_custom_field_value(task_data, cf_name)
            if raw is None:
                continue  # honest-null: cache copy has no value for this CF
            coerced = _coerce_value(raw, dtype)
            if coerced is None:
                continue
            value_by_gid[gid] = coerced

        if not value_by_gid:
            continue

        # Map gid -> healed value across the frame; null where no healed value.
        # Backfill ONLY where the existing cell is null (coalesce semantics):
        # never overwrite an already-populated cell.
        mapped = pl.col("gid").replace_strict(
            old=list(value_by_gid.keys()),
            new=list(value_by_gid.values()),
            default=None,
            return_dtype=merged_df[name].dtype,
        )
        replacement_exprs.append(
            pl.when(pl.col(name).is_null()).then(mapped).otherwise(pl.col(name)).alias(name)
        )
        healed_by_column[name] = len(value_by_gid)

    if not replacement_exprs:
        # Cache carried nothing recoverable -> honest-null residual, no GET spent
        # beyond the single batch (which was free for cached gids).
        return merged_df, _emit(
            entity_type=entity_type,
            project_gid=project_gid,
            columns=tuple(name for name, _c, _d in present_cols),
            null_cells_before=null_cells_before,
            healed_cells=0,
            residual_null_cells=null_cells_before,
            cache_miss_gids=cache_miss_gids,
            healed_by_column={},
        )

    healed_df = merged_df.with_columns(replacement_exprs)

    null_cells_after = sum(int(healed_df[name].null_count()) for name, _c, _d in present_cols)
    healed_cells = null_cells_before - null_cells_after

    return healed_df, _emit(
        entity_type=entity_type,
        project_gid=project_gid,
        columns=tuple(name for name, _c, _d in present_cols),
        null_cells_before=null_cells_before,
        healed_cells=healed_cells,
        residual_null_cells=null_cells_after,
        cache_miss_gids=cache_miss_gids,
        healed_by_column=healed_by_column,
    )


def _emit(
    *,
    entity_type: str,
    project_gid: str,
    columns: tuple[str, ...],
    null_cells_before: int,
    healed_cells: int,
    residual_null_cells: int,
    cache_miss_gids: int,
    healed_by_column: dict[str, int],
) -> NumericRecoveryReceipt:
    """Emit OTel span attributes + a structured log line and build the receipt."""
    span = _otel_trace.get_current_span()
    span.set_attribute("computation.null_number_recovery.entity_type", entity_type)
    span.set_attribute("computation.null_number_recovery.null_cells_before", null_cells_before)
    span.set_attribute("computation.null_number_recovery.healed_cells", healed_cells)
    span.set_attribute("computation.null_number_recovery.residual_null_cells", residual_null_cells)
    span.set_attribute("computation.null_number_recovery.cache_miss_gids", cache_miss_gids)

    extra = {
        "entity_type": entity_type,
        "project_gid": project_gid,
        "columns": list(columns),
        "null_cells_before": null_cells_before,
        "healed_cells": healed_cells,
        "residual_null_cells": residual_null_cells,
        "cache_miss_gids": cache_miss_gids,
        "healed_by_column": healed_by_column,
    }

    if healed_cells > 0:
        logger.info("null_number_recovery_healed", extra=extra)
    else:
        # Nothing to heal from cache (all residual is honest-null / cache-miss).
        logger.info("null_number_recovery_no_op", extra=extra)

    return NumericRecoveryReceipt(
        entity_type=entity_type,
        attempted=True,
        columns=columns,
        null_cells_before=null_cells_before,
        healed_cells=healed_cells,
        residual_null_cells=residual_null_cells,
        cache_miss_gids=cache_miss_gids,
        healed_by_column=healed_by_column,
    )
