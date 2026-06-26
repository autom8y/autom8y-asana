"""Fail-closed write decision for the cure-recovery path (Cure-Recovery-Path Hardening).

A PURE, side-effect-free decision helper for the Step-6 write gate of the
progressive builder. It answers ONE question: under a cure-failure that drives the
active-subset value column below the population floor, what does the write gate do
with the freshly-built (degraded) frame given the prior-good frame on disk?

Design (ADR-cure-recovery-path-hardening-2026-06-11, FORK-1):

- **PRESERVE_PRIOR_GOOD** -- the freshly-built frame is below-floor, the cure healed
  nothing from cache (a wholesale durable-read outage: ``healed_cells == 0`` AND
  ``cold_present_gids == 0``), AND a prior-good frame exists whose active-subset
  population is strictly higher. The write is SKIPPED so the last-good frame is
  served in the gap, never a freshly-nulled frame. (Option 1a.)
- **WRITE_COALESCED** -- the freshly-built frame is below-floor and a prior-good
  frame exists carrying SOME higher-population value cells, but the wholesale-outage
  precondition for PRESERVE does not hold (a partial heal, or a prior-good that is
  not strictly-better whole-frame yet has rows we can rescue). The caller coalesces
  the prior-good value cells into the new frame's null cells before writing -- the
  written frame is then >= prior-good in population. (Option 1c.)
- **WRITE_AS_IS** -- the frame is healthy (not below-floor), OR there is no usable
  prior-good frame (cold start). Writing the honest-null frame in the cold-start
  case preserves the honest-empty-200 invariant (never strands a project in the
  503 trap). (The default; also the safe degradation on any prior-good read error.)

Key invariants:

- NEVER fabricates: COALESCE copies a PRIOR REAL value for the same gid+column; it
  never invents a number (NFR-6).
- Per-entity, never cross-entity: the decision is computed from THIS entity's own
  population receipt + THIS entity's own prior-good frame. The offer frame cannot
  be touched by a unit-frame fail-close (NFR-3).
- G-DENOM honest: the floor breach is over the ACTIVE subset (the population receipt
  already filters it; this helper consumes that verdict, it does not re-derive a
  denominator).
- Additive / two-way door: ``WRITE_AS_IS`` is the safe default; any uncertainty
  (no receipt, not-assessed, no prior-good, read error) degrades to ``WRITE_AS_IS``.

This module is PURE: it imports polars for the coalesce expression builder and the
receipt types for the decision, but performs NO I/O. The prior-good READ and the
actual WRITE live in the caller (``progressive.py`` Step 6).
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from autom8_asana.dataframes.builders.null_number_recovery import (
        NumericRecoveryReceipt,
    )
    from autom8_asana.dataframes.builders.post_build_population_receipt import (
        PopulationReceipt,
    )

__all__ = [
    "WriteDecision",
    "coalesce_prior_good",
    "decide_write",
    "prior_good_active_nonnull",
]


class WriteDecision(Enum):
    """The Step-6 write-gate decision for a freshly-built frame.

    Attributes:
        WRITE_AS_IS: Persist the new frame unchanged (healthy frame, or cold-start
            with no usable prior-good -- preserves honest-empty-200).
        PRESERVE_PRIOR_GOOD: Skip the write entirely; the prior-good frame on disk is
            served in the gap. Manifest stamping is ALSO skipped for this entity so
            freshness does not falsely advance over a frame that was never rewritten.
        WRITE_COALESCED: Merge the prior-good value cells into the new frame's null
            cells, then write. The written frame is >= prior-good in population.
    """

    WRITE_AS_IS = "write_as_is"
    PRESERVE_PRIOR_GOOD = "preserve_prior_good"
    WRITE_COALESCED = "write_coalesced"


def prior_good_active_nonnull(
    prior_good_frame: pl.DataFrame | None,
    population_receipt: PopulationReceipt,
    value_columns: tuple[str, ...],
) -> int:
    """Min active-subset non-null COUNT across ``value_columns`` of the prior-good frame.

    Mirrors the population receipt's active-subset semantics so the prior-good
    "better-ness" comparison is apples-to-apples with the floor verdict the new
    frame was judged against. The active subset is the SAME classifier-derived
    ACTIVE/ACTIVATING filter the receipt uses (``post_build_population_receipt``);
    this helper re-applies it to the prior-good frame via that module's
    ``_active_subset`` so the two denominators match exactly.

    Returns 0 when there is no prior-good frame, no value columns, or the active
    subset cannot be determined (the safe floor -- "prior-good carries nothing
    better", which degrades the decision toward WRITE_AS_IS).

    Args:
        prior_good_frame: The prior-good frame loaded from storage, or None.
        population_receipt: The receipt for the freshly-built frame (carries the
            entity_type used to resolve the active classifier).
        value_columns: The value columns to assess (e.g. ``("mrr",)`` for unit).

    Returns:
        The minimum active-subset non-null cell COUNT across ``value_columns``.
    """
    if prior_good_frame is None or not value_columns or prior_good_frame.is_empty():
        return 0

    # Re-use the receipt module's active-subset filter so the prior-good comparison
    # uses the IDENTICAL active classification (G-DENOM parity). Import locally to
    # keep this module import-light and avoid a cycle at module load.
    from autom8_asana.dataframes.builders.post_build_population_receipt import (
        _active_subset,
    )

    try:
        active = _active_subset(prior_good_frame, population_receipt.entity_type)
    except Exception:  # BROAD-CATCH: comparison is additive  # noqa: BLE001
        return 0

    if active is None or active.is_empty():
        return 0

    present = [c for c in value_columns if c in active.columns]
    if not present:
        return 0

    active_rows = len(active)
    return min(active_rows - int(active[c].null_count()) for c in present)


def decide_write(
    population_receipt: PopulationReceipt | None,
    recovery_receipt: NumericRecoveryReceipt | None,
    prior_good_frame: pl.DataFrame | None,
    value_columns: tuple[str, ...],
) -> WriteDecision:
    """Decide what the Step-6 write gate does with a freshly-built frame.

    Pure decision -- no I/O, no mutation. See module docstring for the three
    outcomes and their preconditions.

    Args:
        population_receipt: The floor verdict for the freshly-built frame. None or
            ``assessed == False`` or ``below_floor == False`` -> WRITE_AS_IS (the
            frame is healthy or the floor does not apply to this entity).
        recovery_receipt: The cure's receipt for this warm. Used to distinguish a
            WHOLESALE durable-read outage (``healed_cells == 0`` AND
            ``cold_present_gids == 0`` -- nothing came back from cache OR S3) from a
            partial heal. None is treated as a wholesale failure (no heal observed).
        prior_good_frame: The prior-good frame loaded from storage, or None
            (cold start / read error -> WRITE_AS_IS).
        value_columns: The entity's economic value columns (e.g. ``("mrr",)``).

    Returns:
        The WriteDecision the caller must honor.
    """
    # Healthy frame, or floor does not apply to this entity -> write unchanged.
    if (
        population_receipt is None
        or not population_receipt.assessed
        or not population_receipt.below_floor
    ):
        return WriteDecision.WRITE_AS_IS

    # Below-floor. We need a prior-good frame strictly better than what we just
    # built to fail closed; otherwise (cold start) write the honest-null frame.
    prior_nonnull = prior_good_active_nonnull(prior_good_frame, population_receipt, value_columns)

    # The freshly-built frame's active-subset min non-null COUNT (the receipt gives
    # the RATE over active_rows; reconstruct the count for an apples-to-apples
    # comparison with the prior-good count).
    new_active_rows = population_receipt.active_rows
    new_nonnull = round(population_receipt.min_rate * new_active_rows)

    # No prior-good carries anything better -> write what we built (cold start /
    # genuinely-degraded-everywhere). Preserves honest-empty-200; never a 503 trap.
    if prior_nonnull <= new_nonnull:
        return WriteDecision.WRITE_AS_IS

    # Prior-good IS strictly better. Distinguish a WHOLESALE durable-read outage
    # (the cure healed nothing from cache OR S3) from a partial heal.
    healed_cells = recovery_receipt.healed_cells if recovery_receipt is not None else 0
    cold_present = recovery_receipt.cold_present_gids if recovery_receipt is not None else 0
    wholesale_outage = healed_cells == 0 and cold_present == 0

    if wholesale_outage:
        # Nothing recovered AND prior-good is strictly better -> serve last-good.
        return WriteDecision.PRESERVE_PRIOR_GOOD

    # Partial heal (some cells came back, but the frame is still below floor) with a
    # strictly-better prior-good -> rescue the prior-good cells into the new frame.
    return WriteDecision.WRITE_COALESCED


def coalesce_prior_good(
    new_frame: pl.DataFrame,
    prior_good_frame: pl.DataFrame,
    value_columns: tuple[str, ...],
    *,
    join_key: str = "gid",
) -> pl.DataFrame:
    """Coalesce prior-good value cells into ``new_frame``'s null value cells.

    For each value column, fill ONLY the null cells of ``new_frame`` with the
    prior-good frame's value for the SAME ``join_key`` (gid). Already-populated
    cells in ``new_frame`` are NEVER overwritten (coalesce semantics, the same
    ``pl.when(is_null).then(...).otherwise(...)`` shape the cure uses at
    ``null_number_recovery.py``). Copies a PRIOR REAL value -- never fabricates.

    Args:
        new_frame: The freshly-built (partially-degraded) frame.
        prior_good_frame: The prior-good frame to rescue cells from.
        value_columns: The value columns to coalesce.
        join_key: The row-identity key (default ``"gid"``).

    Returns:
        A new frame with prior-good value cells coalesced into the null cells.
        Returns ``new_frame`` unchanged when the join key is absent from either
        frame, or no value column is present in both.
    """
    if join_key not in new_frame.columns or join_key not in prior_good_frame.columns:
        return new_frame

    present = [c for c in value_columns if c in new_frame.columns and c in prior_good_frame.columns]
    if not present:
        return new_frame

    # Build a {join_key -> prior value} mapping per column and fill nulls only.
    prior_select = prior_good_frame.select([join_key, *present]).rename(
        {c: f"__prior__{c}" for c in present}
    )
    joined = new_frame.join(prior_select, on=join_key, how="left")

    fill_exprs = [
        pl.when(pl.col(c).is_null()).then(pl.col(f"__prior__{c}")).otherwise(pl.col(c)).alias(c)
        for c in present
    ]
    return joined.with_columns(fill_exprs).drop([f"__prior__{c}" for c in present])
