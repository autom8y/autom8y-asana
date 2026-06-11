"""Warmer-Path PRESERVE Enforcement — the SERVE altitude (hot-tier closure).

Sibling of ``test_warmer_preserve_enforcement.py`` (#128). #128 closed the
**S3 disk** write site under PRESERVE and asserts the persisted disk frame by
content (``storage.load_dataframe``). It did NOT cover the **in-process memory
(hot) tier**: ``cache.put_async`` promotes the freshly-built ``entry.dataframe``
to ``memory_tier`` (``dataframe_cache.py`` finalize) regardless of the
PRESERVE/COALESCE decision, and ``get_async`` checks memory FIRST and
``_check_freshness_and_serve`` rejects only on schema/watermark mismatch — never
on ``population_degraded``. So a PRESERVE that correctly skipped the disk write
still poisons the hot tier with the degraded 0/N frame (fresh ``created_at``),
which is then served preferentially over the good prior-good frame on S3 — the
game-day 0/N symptom RELOCATED from disk to the hot tier.

These probes drive the REAL put → serve loop through ``cache.get_async`` (NOT
``storage.load_dataframe``) and assert by FRAME CONTENT (the log lied at the
game-day; content is the only honest oracle). They cover:

  * the WARMER path (``warmer._warm_entity_type_async`` → ``put_async`` → serve),
  * the W7 request-decorator / serving-process path (a direct ``put_async`` under
    the same singleton, as the request path does), and
  * an EVICTION-RECOVERY probe: a pre-existing poisoned ``population_degraded``
    memory entry self-corrects on the next serve (rehydrates the good S3 frame).

RED-first contract: against the unmodified #128 head these serve-altitude probes
are RED (``get_async`` returns 0/N from the poisoned memory tier). After the fix
they are GREEN (``get_async`` returns the prior-good count). Mutation-reverting
the memory-skip flips the primary serve probe back to RED.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import polars as pl

from autom8_asana.dataframes.builders.fail_closed_write import WriteDecision

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
    """Healthy prior-good: every active row carries a populated mrr (723/3021 scaled)."""
    return _frame(
        [
            {"gid": f"g{i}", "section": "Active", "is_completed": False, "mrr": 100.0 * (i + 1)}
            for i in range(n_active)
        ]
    )


def _degraded_frame(n_active: int = 3) -> pl.DataFrame:
    """Freshly-built degraded frame: same active rows, mrr entirely null (0/3021 scaled)."""
    return _frame(
        [
            {"gid": f"g{i}", "section": "Active", "is_completed": False, "mrr": None}
            for i in range(n_active)
        ]
    )


def _partial_degraded_frame(n_active: int = 3) -> pl.DataFrame:
    """Below-floor frame with SOME cells null (the WRITE_COALESCED precondition): the
    first active row keeps its value, the rest are null — coalesce against prior-good
    rescues them so the WRITTEN (and served) frame is >= prior-good."""
    rows = [
        {"gid": f"g{i}", "section": "Active", "is_completed": False, "mrr": None}
        for i in range(n_active)
    ]
    if rows:
        rows[0]["mrr"] = 100.0  # one real cell -> partial heal, not wholesale outage
    return _frame(rows)


# ── in-memory DataFrameStorage (real persistence path, no S3) ───────────────


class _InMemoryStorage:
    """In-memory DataFrameStorage stand-in for the PERSISTENCE backend (distinct from
    the WRITE LOGIC / SERVE LOGIC under test). Faithful v2 entity-keyed save/load so
    ``write_final_artifacts_async``, the prior-good read, AND the progressive-tier
    read on serve all exercise REAL section_persistence + tier code."""

    def __init__(self) -> None:
        self.is_available = True
        self._frames: dict[str, tuple[pl.DataFrame, Any, dict[str, Any]]] = {}
        self._json: dict[str, bytes] = {}

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
        }
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


class _DegradedBuildStrategy:
    """Strategy stand-in returning the degraded frame + the build's write decision
    via ``_last_write_context`` — the production reality of the two-writer split
    (the builder PRESERVED on disk via Writer A then handed BACK the degraded frame).
    The warmer reads ``_last_write_context`` and threads it into ``put_async``."""

    def __init__(self, *, decision: WriteDecision, frame: pl.DataFrame) -> None:
        self.entity_type = _ENTITY
        self._frame = frame
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
    """A REAL integration DataFrameCache: memory tier + progressive tier writing
    through REAL SectionPersistence onto the in-memory storage. Everything from
    ``put_async``/``get_async`` down is production code."""
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


def _served_mrr_nonnull(entry) -> int:
    assert entry is not None, "get_async returned None (project stranded — no serve)"
    df = entry.dataframe
    return df.height - int(df["mrr"].null_count())


# ── PRIMARY: WARMER path serve — PRESERVE must SERVE the prior-good, not 0/N ──


async def test_warmer_preserve_serves_prior_good_not_degraded(monkeypatch):
    """SERVE-ALTITUDE PRIMARY (the layer #128's S3-only tests missed). Drive the REAL
    warmer store path under a wholesale-outage PRESERVE decision, then SERVE via
    ``cache.get_async`` (the production read path, memory-first). The served frame's
    active-subset ``count(mrr non-null)`` MUST equal the prior-good count (3), NEVER 0.

    On unmodified #128 this is RED: ``put_async`` promoted the degraded 0/3 frame to
    the hot tier (``created_at`` fresh), and ``get_async`` serves memory first with no
    ``population_degraded`` rejection — so it returns 0/3 from the poisoned hot tier
    even though S3 correctly holds the prior-good 3/3. After the fix it is GREEN (3/3)."""
    from autom8_asana.cache.dataframe.warmer import CacheWarmer

    storage = _InMemoryStorage()
    now = datetime.now(UTC)
    await storage.save_dataframe(_PROJECT, _prior_good_frame(3), now, entity_type=_ENTITY)

    cache = _make_real_cache(storage)
    warmer = CacheWarmer(cache=cache)
    strategy = _DegradedBuildStrategy(
        decision=WriteDecision.PRESERVE_PRIOR_GOOD, frame=_degraded_frame(3)
    )
    monkeypatch.setattr(warmer, "_get_strategy_instance", lambda et: strategy)
    await warmer._warm_entity_type_async(_ENTITY, _PROJECT, client=None)

    # SERVE through the production read path (memory-first), NOT storage.load_dataframe.
    served = await cache.get_async(_PROJECT, _ENTITY)
    assert _served_mrr_nonnull(served) == 3, (
        "PRESERVE leaked into the HOT TIER: get_async served the degraded 0/3 frame "
        "from memory instead of rehydrating the prior-good 3/3 from S3"
    )


# ── PRIMARY: W7 request-decorator / serving-process path serve ───────────────


async def test_w7_serving_process_preserve_serves_prior_good(monkeypatch):
    """W7 / serving-process altitude: the request path calls ``put_async`` on the
    SAME singleton cache the serve path reads (warmer + serve share
    ``get_dataframe_cache()``). A PRESERVE put from the serving process must NOT poison
    the hot tier: the next ``get_async`` must serve the prior-good 3/3, not 0/3.

    Drives ``put_async`` directly (the request decorator's call shape — threading the
    build's decision), then serves. RED on #128 (0/3 from memory), GREEN after fix."""
    storage = _InMemoryStorage()
    now = datetime.now(UTC)
    await storage.save_dataframe(_PROJECT, _prior_good_frame(3), now, entity_type=_ENTITY)

    cache = _make_real_cache(storage)
    # The serving-process put under PRESERVE (decision threaded as the build computed it).
    await cache.put_async(
        project_gid=_PROJECT,
        entity_type=_ENTITY,
        dataframe=_degraded_frame(3),
        watermark=now,
        write_decision=WriteDecision.PRESERVE_PRIOR_GOOD,
        population_degraded=True,
        population_min_rate=0.0,
    )

    served = await cache.get_async(_PROJECT, _ENTITY)
    assert _served_mrr_nonnull(served) == 3, (
        "W7 serving-process PRESERVE poisoned the hot tier: get_async served 0/3 "
        "from memory instead of the prior-good 3/3 from S3"
    )


# ── EVICTION-RECOVERY: a pre-existing poisoned memory entry self-corrects ────


async def test_preexisting_poisoned_memory_entry_self_corrects_on_serve(monkeypatch):
    """EVICTION-RECOVERY (belt-and-braces serve-path guard). Even a memory entry that
    is ALREADY poisoned (a degraded frame promoted before the fix shipped, or by any
    future orphan write path) must self-correct on the next serve: the serve path
    treats a ``population_degraded`` memory entry as a soft-reject → rehydrate from S3.

    Seed S3 with the prior-good 3/3, then DIRECTLY inject a poisoned degraded 0/3
    entry into the memory tier (simulating a pre-fix poisoned hot entry). The next
    ``get_async`` must serve the prior-good 3/3 (soft-reject the poisoned memory entry,
    rehydrate from S3). RED on #128 (memory served first, returns 0/3), GREEN after."""
    from autom8_asana.cache.integration.dataframe_cache import DataFrameCacheEntry
    from autom8_asana.dataframes.models.registry import get_schema_version

    storage = _InMemoryStorage()
    now = datetime.now(UTC)
    await storage.save_dataframe(_PROJECT, _prior_good_frame(3), now, entity_type=_ENTITY)

    cache = _make_real_cache(storage)
    cache_key = cache._build_key(_PROJECT, _ENTITY)
    schema_version = get_schema_version(_ENTITY) or "unknown"
    poisoned = DataFrameCacheEntry(
        project_gid=_PROJECT,
        entity_type=_ENTITY,
        dataframe=_degraded_frame(3),
        watermark=now,
        created_at=datetime.now(UTC),
        schema_version=schema_version,
        population_degraded=True,
        population_min_rate=0.0,
    )
    cache.memory_tier.put(cache_key, poisoned)

    served = await cache.get_async(_PROJECT, _ENTITY)
    assert _served_mrr_nonnull(served) == 3, (
        "pre-existing poisoned memory entry was served (0/3) — the serve path did NOT "
        "soft-reject population_degraded + rehydrate the prior-good 3/3 from S3"
    )
    # The poisoned entry must NOT survive: either evicted on soft-reject, or replaced
    # by the rehydrated good frame. A second serve must also return the prior-good.
    served_again = await cache.get_async(_PROJECT, _ENTITY)
    assert _served_mrr_nonnull(served_again) == 3, "poisoned memory entry survived the soft-reject"


# ── WRITE_COALESCED: serve the COALESCED (good) frame, not the degraded one ──


async def test_warmer_write_coalesced_serves_coalesced_not_degraded(monkeypatch):
    """WRITE_COALESCED serve path: a partial-heal warm coalesces the prior-good cells
    into the new frame's nulls on disk (>= prior-good population). The HOT TIER must
    serve the COALESCED (good) frame, NOT the original degraded frame the builder
    handed back. After a coalesced warm, ``get_async`` must serve >= prior-good (3),
    never the degraded count (1). RED on #128 (degraded frame promoted to memory)."""
    from autom8_asana.cache.dataframe.warmer import CacheWarmer

    storage = _InMemoryStorage()
    now = datetime.now(UTC)
    await storage.save_dataframe(_PROJECT, _prior_good_frame(3), now, entity_type=_ENTITY)

    cache = _make_real_cache(storage)
    warmer = CacheWarmer(cache=cache)
    strategy = _DegradedBuildStrategy(
        decision=WriteDecision.WRITE_COALESCED, frame=_partial_degraded_frame(3)
    )
    monkeypatch.setattr(warmer, "_get_strategy_instance", lambda et: strategy)
    await warmer._warm_entity_type_async(_ENTITY, _PROJECT, client=None)

    served = await cache.get_async(_PROJECT, _ENTITY)
    assert _served_mrr_nonnull(served) >= 3, (
        "WRITE_COALESCED leaked the DEGRADED frame into the hot tier: get_async served "
        f"{_served_mrr_nonnull(served)}/3 (expected the coalesced >= prior-good 3/3)"
    )


# ── NON-REGRESSION: a healthy WRITE_AS_IS warm still serves from memory ──────


async def test_warmer_write_as_is_serves_from_memory(monkeypatch):
    """Non-regression: a HEALTHY warm (WRITE_AS_IS) still promotes to the hot tier and
    ``get_async`` serves the fresh 3/3 frame from memory — the fix is a skip ONLY on
    PRESERVE/COALESCE-degraded, never a blanket hot-tier disable."""
    from autom8_asana.cache.dataframe.warmer import CacheWarmer

    storage = _InMemoryStorage()
    cache = _make_real_cache(storage)
    warmer = CacheWarmer(cache=cache)
    strategy = _DegradedBuildStrategy(
        decision=WriteDecision.WRITE_AS_IS, frame=_prior_good_frame(3)
    )
    monkeypatch.setattr(warmer, "_get_strategy_instance", lambda et: strategy)
    await warmer._warm_entity_type_async(_ENTITY, _PROJECT, client=None)

    # Memory tier holds the fresh healthy entry (served without an S3 round-trip).
    cache_key = cache._build_key(_PROJECT, _ENTITY)
    assert cache.memory_tier.get(cache_key) is not None, "healthy warm did not promote to hot tier"
    served = await cache.get_async(_PROJECT, _ENTITY)
    assert _served_mrr_nonnull(served) == 3
