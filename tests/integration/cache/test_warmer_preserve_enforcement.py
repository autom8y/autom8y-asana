"""Warmer-Path PRESERVE Enforcement — the SECOND finalize writer (W3) gated.

Anti-theater integration test for ADR-warmer-path-preserve-enforcement-2026-06-11
(extends #127). #127 gated Writer A (the builder finalize). The 2026-06-11 game-day
proved Writer B (the warmer's ``put_async`` → ``tiers/progressive.put_async`` →
``section_persistence.write_final_artifacts_async`` → ``save_dataframe``) is the
OPERATIVE write site and was UNGATED: the cure *decided* PRESERVE and *logged*
``fail_closed_write_preserve_prior_good``, yet the unit frame persisted **0/N** with
``index_written:false``. The decision was made but NOT enforced at the operative site.

This module drives the REAL warmer store path end-to-end:

    warmer._warm_entity_type_async
      → strategy._build_dataframe        (returns the degraded frame + decision
                                           context — the production reality: the
                                           builder PRESERVED on disk via Writer A
                                           then handed BACK the degraded frame)
      → cache.put_async                   (REAL integration DataFrameCache)
      → ProgressiveTier.put_async         (REAL tier)
      → SectionPersistence.write_final_artifacts_async   (the CONVERGENCE primitive)
      → save_dataframe                    (REAL persistence against in-memory storage)

The ONLY stub layer is the strategy's ``_build_dataframe`` (the builder's output —
NOT the write path) and an in-memory ``DataFrameStorage`` (the persistence backend,
distinct from the write logic). Every WRITE-PATH layer above ``save_dataframe`` is
the REAL code path (@THROUGHLINE-integration-boundary-fidelity §4 — converge the two
finalize writers; cover the operative one).

Assert by FRAME CONTENT, never the log. The game-day proved the
``fail_closed_write_preserve_prior_good`` log FIRED while the write degraded. Content
is the only honest oracle: after the warm, load the persisted frame and assert the
active-subset ``count(mrr non-null)`` equals the prior-good count (723-shaped, scaled
to 3 here), NOT 0.

Mutation proof: ``test_BASELINE_warmer_ungated_persists_degraded`` asserts the
CURRENT (pre-fix) bug (0/N persisted over the prior-good). It is RED-after-fix —
reverting the convergence gate flips the primary GREEN test back to 0/N and the
baseline back to GREEN.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import polars as pl
import pytest

from autom8_asana.dataframes.builders.fail_closed_write import WriteDecision

# Canonical unit-frame economics — mirrors the game-day 723/3021 prior-good shape,
# scaled (3 active / 0 healed) so the active-subset floor breaches deterministically.
_ENTITY = "unit"
_PROJECT = "1207519540893045"

_SCHEMA_COLS = {
    "gid": pl.Utf8,
    "section": pl.Utf8,
    "is_completed": pl.Boolean,
    "mrr": pl.Float64,
}


def _frame(rows: list[dict[str, Any]]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=_SCHEMA_COLS)


def _prior_good_frame(n_active: int = 3) -> pl.DataFrame:
    """A healthy prior-good frame: every active row carries a populated mrr
    (the 723/3021 game-day prior-good, scaled)."""
    return _frame(
        [
            {"gid": f"g{i}", "section": "Active", "is_completed": False, "mrr": 100.0 * (i + 1)}
            for i in range(n_active)
        ]
    )


def _degraded_frame(n_active: int = 3) -> pl.DataFrame:
    """The freshly-built degraded frame the builder hands back on a wholesale
    durable-read outage: same active rows, mrr entirely null (the 0/3021 frame)."""
    return _frame(
        [
            {"gid": f"g{i}", "section": "Active", "is_completed": False, "mrr": None}
            for i in range(n_active)
        ]
    )


# ── in-memory DataFrameStorage (real persistence path, no S3) ───────────────


class _InMemoryStorage:
    """In-memory DataFrameStorage stand-in for the PERSISTENCE backend (distinct
    from the WRITE LOGIC under test). Implements the v2 entity-keyed save/load
    contract faithfully so ``write_final_artifacts_async`` and the prior-good read
    exercise REAL section_persistence code."""

    def __init__(self) -> None:
        self.is_available = True
        self._frames: dict[str, tuple[pl.DataFrame, Any, dict[str, Any]]] = {}
        self._json: dict[str, bytes] = {}
        self.save_dataframe_calls: list[dict[str, Any]] = []

    def _key(self, project_gid: str, entity_type: str | None) -> str:
        return f"{project_gid}:{entity_type}"

    async def save_dataframe(
        self,
        project_gid,
        df,
        watermark,
        *,
        entity_type=None,
        population_degraded=None,
        population_min_rate=None,
    ) -> bool:
        meta = {
            "row_count": len(df),
            "columns": df.columns,
            "entity_type": entity_type,
            "population_degraded": population_degraded,
            "population_min_rate": population_min_rate,
        }
        self.save_dataframe_calls.append(
            {
                "entity_type": entity_type,
                "mrr_nonnull": (
                    df.height - int(df["mrr"].null_count()) if "mrr" in df.columns else None
                ),
                "population_degraded": population_degraded,
            }
        )
        self._frames[self._key(project_gid, entity_type)] = (df.clone(), watermark, meta)
        return True

    async def load_dataframe(self, project_gid, entity_type=None):
        hit = self._frames.get(self._key(project_gid, entity_type))
        if hit is None:
            return None, None
        df, wm, _meta = hit
        return df.clone(), wm

    async def load_dataframe_with_metadata(self, project_gid, entity_type=None):
        hit = self._frames.get(self._key(project_gid, entity_type))
        if hit is None:
            return None, None, None
        df, wm, meta = hit
        return df.clone(), wm, dict(meta)

    async def save_index(self, project_gid, index_data, entity_type=None) -> bool:
        return True

    async def load_index(self, project_gid, entity_type=None):
        return None

    async def save_json(self, key, data) -> bool:
        self._json[key] = data
        return True

    async def load_json(self, key):
        return self._json.get(key)


# ── stub strategy: returns the degraded frame the builder hands BACK ────────


class _DegradedBuildStrategy:
    """Strategy stand-in whose ``_build_dataframe`` returns the degraded frame the
    builder produced under a wholesale durable-read outage — the EXACT production
    reality of the two-writer split: the builder PRESERVED on disk (Writer A
    early-return) but RETURNED the degraded frame + the ``PRESERVE_PRIOR_GOOD``
    write decision. ``_last_write_context`` is the carry the warmer reads (the fix
    threads it; pre-fix the warmer ignores it and the gate is unreached).

    On the pre-fix code the warmer reads neither attribute, so this stub reproduces
    the bug; on the fixed code the warmer reads ``_last_write_context`` and threads
    it into ``put_async`` so the convergence primitive honors PRESERVE.
    """

    def __init__(self, *, decision: WriteDecision, frame: pl.DataFrame) -> None:
        self.entity_type = _ENTITY
        self._frame = frame
        # The carry the builder populates on BuildResult and _build_entity_dataframe
        # stashes; the warmer reads it post-build (the fix).
        self._last_write_context: dict[str, Any] = {
            "write_decision": decision,
            "population_degraded": decision is not WriteDecision.WRITE_AS_IS,
            "population_min_rate": 0.0 if decision is not WriteDecision.WRITE_AS_IS else 1.0,
        }

    async def _build_dataframe(
        self, project_gid: str, client: Any
    ) -> tuple[pl.DataFrame, datetime]:
        return self._frame, datetime.now(UTC)


def _make_real_cache(storage: _InMemoryStorage):
    """Construct a REAL integration DataFrameCache whose progressive tier writes
    through the REAL SectionPersistence onto the in-memory storage. Everything from
    ``cache.put_async`` down to ``save_dataframe`` is production code."""
    from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
    from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
    from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
    from autom8_asana.cache.dataframe.tiers.progressive import ProgressiveTier
    from autom8_asana.cache.integration.dataframe_cache import DataFrameCache
    from autom8_asana.dataframes.section_persistence import SectionPersistence

    persistence = SectionPersistence(storage=storage)
    return DataFrameCache(
        memory_tier=MemoryTier(max_heap_percent=0.3, max_entries=64),
        progressive_tier=ProgressiveTier(persistence=persistence),
        coalescer=DataFrameCacheCoalescer(max_wait_seconds=60.0),
        circuit_breaker=CircuitBreaker(
            failure_threshold=3, reset_timeout_seconds=60, success_threshold=1
        ),
    )


async def _warm_via_real_path(
    *,
    monkeypatch,
    storage: _InMemoryStorage,
    strategy: _DegradedBuildStrategy,
):
    """Drive the REAL warmer store path: warmer._warm_entity_type_async →
    cache.put_async → ProgressiveTier.put_async → write_final_artifacts_async →
    save_dataframe. Only the strategy (builder output) is stubbed."""
    from autom8_asana.cache.dataframe.warmer import CacheWarmer

    cache = _make_real_cache(storage)
    warmer = CacheWarmer(cache=cache)
    monkeypatch.setattr(warmer, "_get_strategy_instance", lambda et: strategy)
    return await warmer._warm_entity_type_async(_ENTITY, _PROJECT, client=None)


# ── BASELINE: the GAP is real (today's warmer re-writes the degraded frame) ──


async def test_BASELINE_warmer_ungated_persists_degraded(monkeypatch):
    """BEHAVIORAL BASELINE (proves the W3 gap is real, not a strawman): reconstruct
    the PRE-FIX warmer write VERBATIM — the warmer ignored the build's decision and
    called ``put_async`` BARE (no ``write_decision``, no population flags), so
    ``tiers/progressive.put_async`` invoked ``write_final_artifacts_async`` UNGATED.
    Driven against the REAL integration cache + tier + persistence onto an in-memory
    store seeded with a strictly-better prior-good (3/3).

    This reproduces the game-day RED in isolation: PRESERVE was decided upstream, yet
    the degraded 0/3 frame OVERWROTE the prior-good 3/3 at the operative warmer write
    site. It asserts the OLD code path's behavior (no decision threaded, no guard
    predicate satisfied) and therefore stays GREEN before AND after the fix —
    documenting WHY the decision-threading seam is load-bearing (mirrors the #127
    ``test_BASELINE_unconditional_write_persists_degraded_frame`` convention)."""
    storage = _InMemoryStorage()
    now = datetime.now(UTC)
    await storage.save_dataframe(_PROJECT, _prior_good_frame(3), now, entity_type=_ENTITY)

    cache = _make_real_cache(storage)
    # The PRE-FIX warmer call shape: bare put_async — no write_decision, no population
    # flags. (The fixed warmer threads write_ctx; this asserts the gap the threading
    # closes.) The guard does NOT fire (population_degraded defaults False, as the old
    # warmer passed), so the unconditional save persists the degraded frame.
    await cache.put_async(
        project_gid=_PROJECT,
        entity_type=_ENTITY,
        dataframe=_degraded_frame(3),
        watermark=now,
    )

    persisted, _wm = await storage.load_dataframe(_PROJECT, entity_type=_ENTITY)
    assert persisted is not None
    mrr_nonnull = persisted.height - int(persisted["mrr"].null_count())
    # The W3 bug: with no decision threaded, the degraded frame OVERWROTE the
    # prior-good (PRESERVE decided upstream but not enforced at the write site).
    assert mrr_nonnull == 0, (
        f"BASELINE did not reproduce the W3 gap (expected 0/3 persisted, got "
        f"{mrr_nonnull}/3) — the unconditional write should overwrite the prior-good"
    )
    # Sanity: the bare put DID drive a save_dataframe through the real tier.
    assert any(c["entity_type"] == _ENTITY for c in storage.save_dataframe_calls)


# ── PRIMARY: PRESERVE is ENFORCED at the warmer write site (W3) ──────────────


async def test_warmer_preserve_enforced_under_revoked_grant(monkeypatch):
    """GREEN (post-fix): a wholesale-outage warm whose builder decided
    ``PRESERVE_PRIOR_GOOD`` MUST preserve the prior-good frame at the OPERATIVE
    warmer write site — the persisted active-subset ``count(mrr non-null)`` equals
    the prior-good count (3), NEVER 0.

    Asserts by CONTENT (the persisted frame), NOT the PRESERVE log (the game-day
    proved the log lied). On unmodified code the warmer ignores the decision and
    this is RED (0/3); after convergence it is GREEN (3/3)."""
    storage = _InMemoryStorage()
    now = datetime.now(UTC)
    await storage.save_dataframe(_PROJECT, _prior_good_frame(3), now, entity_type=_ENTITY)

    strategy = _DegradedBuildStrategy(
        decision=WriteDecision.PRESERVE_PRIOR_GOOD, frame=_degraded_frame(3)
    )
    await _warm_via_real_path(monkeypatch=monkeypatch, storage=storage, strategy=strategy)

    persisted, _wm = await storage.load_dataframe(_PROJECT, entity_type=_ENTITY)
    assert persisted is not None
    mrr_nonnull = persisted.height - int(persisted["mrr"].null_count())
    assert mrr_nonnull == 3, (
        f"PRESERVE was NOT enforced at the warmer write site: persisted {mrr_nonnull}/3 "
        f"(expected the prior-good 3/3 — the degraded 0/3 frame must NOT overwrite it)"
    )


async def test_warmer_write_as_is_still_persists(monkeypatch):
    """Non-regression: a HEALTHY warm (decision WRITE_AS_IS) persists the freshly-
    built frame unchanged through the same converged primitive — the gate is a skip
    ONLY on PRESERVE, never a blanket block."""
    storage = _InMemoryStorage()
    healthy = _prior_good_frame(3)  # 3/3 healthy
    strategy = _DegradedBuildStrategy(decision=WriteDecision.WRITE_AS_IS, frame=healthy)
    await _warm_via_real_path(monkeypatch=monkeypatch, storage=storage, strategy=strategy)

    persisted, _wm = await storage.load_dataframe(_PROJECT, entity_type=_ENTITY)
    assert persisted is not None
    assert persisted.height - int(persisted["mrr"].null_count()) == 3


async def test_warmer_cold_start_writes_honest_when_no_prior_good(monkeypatch):
    """Cold-start honest-empty-200 invariant: a degraded frame with NO prior-good on
    disk and decision WRITE_AS_IS (decide_write degrades to WRITE_AS_IS on cold start)
    MUST persist the honest-null frame — never strand the project in a 503 trap."""
    storage = _InMemoryStorage()  # empty — no prior-good
    strategy = _DegradedBuildStrategy(decision=WriteDecision.WRITE_AS_IS, frame=_degraded_frame(3))
    await _warm_via_real_path(monkeypatch=monkeypatch, storage=storage, strategy=strategy)

    persisted, _wm = await storage.load_dataframe(_PROJECT, entity_type=_ENTITY)
    assert persisted is not None, "cold-start frame was SKIPPED (503 trap risk)"
    assert persisted.height == 3  # the honest-null frame IS persisted


# ── GUARD (c): impossible-by-construction backstop ───────────────────────────


async def test_guard_refuses_below_floor_write_with_no_decision(monkeypatch):
    """Backstop guard (Option c): a below-floor frame (population_degraded True) that
    reaches the convergence primitive with NO recorded write_decision is REFUSED — the
    prior-good is preserved, NOT overwritten by a silent 0/N degrade. This is the
    impossible-by-construction guard that covers W4/W5 + any future orphan writer.

    Drives the primitive directly (the future-orphan altitude: a caller that DID NOT
    thread a decision). On unmodified code there is no guard, so the degraded frame
    persists (RED 0/3); after the fix the guard refuses (GREEN 3/3)."""
    storage = _InMemoryStorage()
    now = datetime.now(UTC)
    await storage.save_dataframe(_PROJECT, _prior_good_frame(3), now, entity_type=_ENTITY)

    from autom8_asana.dataframes.section_persistence import SectionPersistence

    persistence = SectionPersistence(storage=storage)
    # A future orphan writer: below-floor frame, NO write_decision threaded.
    await persistence.write_final_artifacts_async(
        _PROJECT,
        _degraded_frame(3),
        now,
        entity_type=_ENTITY,
        population_degraded=True,
        population_min_rate=0.0,
    )

    persisted, _wm = await storage.load_dataframe(_PROJECT, entity_type=_ENTITY)
    assert persisted is not None
    mrr_nonnull = persisted.height - int(persisted["mrr"].null_count())
    assert mrr_nonnull == 3, (
        f"guard did not refuse an ungated below-floor write: persisted {mrr_nonnull}/3 "
        f"(the prior-good 3/3 must NOT be overwritten by a decision-less degrade)"
    )


# ── OFFER-SYMMETRY (NFR-3): per-entity, never cross-entity ───────────────────


async def test_warmer_preserve_offer_isolated(monkeypatch):
    """OFFER-SYMMETRY (NFR-3): a PRESERVE on the unit warm preserves the unit
    prior-good AND leaves a concurrently-good offer frame byte-stable. The decision
    is per-entity (the offer warm carries its OWN decision); a unit PRESERVE cannot
    touch the offer frame."""
    storage = _InMemoryStorage()
    now = datetime.now(UTC)

    # Seed a healthy offer frame (live-served, must not regress).
    offer_cols = {**_SCHEMA_COLS, "offer_id": pl.Utf8}
    offer_frame = pl.DataFrame(
        [
            {
                "gid": f"o{i}",
                "section": "Active",
                "is_completed": False,
                "mrr": 50.0 * (i + 1),
                "offer_id": f"OFF{i}",
            }
            for i in range(4)
        ],
        schema=offer_cols,
    )
    await storage.save_dataframe(_PROJECT, offer_frame, now, entity_type="offer")
    # Seed a strictly-better prior-good unit frame.
    await storage.save_dataframe(_PROJECT, _prior_good_frame(3), now, entity_type=_ENTITY)

    # Warm UNIT under a PRESERVE decision.
    strategy = _DegradedBuildStrategy(
        decision=WriteDecision.PRESERVE_PRIOR_GOOD, frame=_degraded_frame(3)
    )
    await _warm_via_real_path(monkeypatch=monkeypatch, storage=storage, strategy=strategy)

    # The unit prior-good is preserved (3/3).
    unit_persisted, _wm = await storage.load_dataframe(_PROJECT, entity_type=_ENTITY)
    assert unit_persisted.height - int(unit_persisted["mrr"].null_count()) == 3

    # The OFFER frame is byte-stable — never touched by the unit warm.
    offer_persisted, _wm = await storage.load_dataframe(_PROJECT, entity_type="offer")
    assert offer_persisted is not None
    assert offer_persisted.equals(offer_frame), "offer frame regressed during a unit warm"
