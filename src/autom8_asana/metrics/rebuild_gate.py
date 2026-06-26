"""Quality-aware rebuild gate (Cure-Recovery-Path Hardening, FORK-2).

A PURE predicate for the warmer/consumer rebuild decision. It keeps
``FreshnessReport.stale`` (``metrics/freshness.py``) a PURE age signal — the
quality term lives HERE, in the rebuild gate, NOT in the age predicate
(ADR-cure-recovery-path-hardening-2026-06-11 §FORK-2 / TDD §4.3).

The defect this closes (EXP-1 GAP-2): after a durable-read grant is restored, the
next warm refreshes the manifest but freshness-SKIPS the dataframe rebuild because
the degraded parquet's mtime is recent (``stale_by_age == False``). The degraded
frame then does NOT self-heal until forced. Freshness keys on AGE, not data
QUALITY.

The fix: ``needs_rebuild = stale_by_age OR (population_degraded AND grant_healthy)``.
The ``grant_now_healthy`` conjunct (expressed here as ``not grant_unhealthy_recently``)
is the storm-suppressor: a degraded frame whose CAUSE is still active (the durable
read is still wholesale-failing) must NOT rebuild on quality alone — it would
rebuild, re-degrade, and loop. It clears automatically when a healthy warm produces
``cold_present_gids > 0`` (so ``grant_unhealthy_recently`` flips False).

G-DENOM: ``population_degraded`` derives from ``PopulationReceipt.below_floor``,
which is computed over the ACTIVE subset. The gate fires ONLY on a real
active-subset floor-breach — never a blanket "any null -> rebuild".
"""

from __future__ import annotations

__all__ = ["needs_rebuild"]


def needs_rebuild(
    *,
    stale_by_age: bool,
    population_degraded: bool,
    grant_unhealthy_recently: bool,
) -> bool:
    """Decide whether the warmer/consumer rebuilds the dataframe this cycle.

    Args:
        stale_by_age: The PURE age signal (``FreshnessReport.stale`` /
            ``max_age_seconds > threshold_seconds``). The load-bearing relief valve
            for the healthy path — when True, always rebuild.
        population_degraded: True when the persisted frame's last build was
            below-floor over the active subset (``BuildQuality.population_degraded``,
            read from the persisted frame metadata). The quality term.
        grant_unhealthy_recently: True when the last warm's durable read failed
            wholesale (``cache_miss_gids == total_null_gids AND
            cold_present_gids == 0``). The storm-suppressor: do NOT rebuild on
            quality alone while the cause is still active.

    Returns:
        True iff a rebuild should run this cycle.
    """
    if stale_by_age:
        return True
    return population_degraded and not grant_unhealthy_recently
