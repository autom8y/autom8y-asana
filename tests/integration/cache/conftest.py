"""Shared test infrastructure for tests/integration/cache/.

Extracted from test_warmer_preserve_enforcement.py and
test_warmer_preserve_serve_altitude.py per eunomia E4 CHANGE-E4-008.
The two integration files share identical constants, frame-builder helpers,
stub classes (_InMemoryStorage, _DegradedBuildStrategy), and the real-cache
factory. Consolidating here removes the copy-paste and gives a single
update point for the DataFrameStorage contract (v2 entity-keyed API).

_InMemoryStorage uses the tracking variant (save_dataframe_calls) from the
enforcement file. The serve-altitude file does not assert on that list, so
the extra attribute is additive and harmless.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import polars as pl

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


class _InMemoryStorage:
    """In-memory DataFrameStorage stand-in for the PERSISTENCE backend (distinct
    from the WRITE LOGIC / SERVE LOGIC under test). Implements the v2 entity-keyed
    save/load contract faithfully so ``write_final_artifacts_async``, the prior-good
    read, AND the progressive-tier read on serve all exercise REAL section_persistence
    and tier code.

    Carries ``save_dataframe_calls`` for tests that need to verify the write was
    called (enforcement file). Tests that do not assert on this list (serve-altitude
    file) can ignore it — the extra attribute is additive and harmless.
    """

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
