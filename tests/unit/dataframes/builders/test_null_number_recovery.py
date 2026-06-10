"""FPC Phase-2 path-canon number-cell recovery — anti-theater test suite.

Exercises the REAL cure (recover_null_number_cells) against a counting in-test
store + real ColumnDef/DataFrameSchema. NOT stubs of the cure. Proves:
  - not-N+1 (G-THEATER): exactly ONE cache batch read regardless of rows x null-cols;
    the store makes ZERO Asana calls (pure dict lookup, mirroring cache-only reads).
  - heal-proof (G-PROVE): null cells heal to the EXACT cached values (falsifiable).
  - never-fabricate: null-cache / cache-miss cells stay honest-null.
  - never-overwrite: an already-populated cell is preserved (coalesce-only).
  - G-PROPAGATE: one loop heals mrr + weekly_ad_spend; cascade: and non-numeric cf:
    columns are excluded.
  - additive: a store error returns the frame UNCHANGED and never raises.
  - no-op guards: schema/store None, empty frame, no-null-cells => no store call.
"""

from __future__ import annotations

from typing import Any

import polars as pl

from autom8_asana.dataframes.builders.null_number_recovery import (
    recover_null_number_cells,
)
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema

_SCHEMA_COLS = {
    "gid": pl.Utf8,
    "mrr": pl.Float64,
    "weekly_ad_spend": pl.Float64,
    "discount": pl.Utf8,
    "offer_mrr": pl.Float64,
}


def _schema() -> DataFrameSchema:
    """mrr/weekly_ad_spend = numeric cf: (eligible); discount = non-numeric cf:
    (excluded); offer_mrr = cascade: (excluded)."""
    return DataFrameSchema(
        name="unit",
        task_type="Unit",
        columns=[
            ColumnDef(name="gid", dtype="Utf8", source="gid"),
            ColumnDef(name="mrr", dtype="Float64", source="cf:MRR"),
            ColumnDef(name="weekly_ad_spend", dtype="Float64", source="cf:Weekly Ad Spend"),
            ColumnDef(name="discount", dtype="Utf8", source="cf:Discount"),
            ColumnDef(name="offer_mrr", dtype="Float64", source="cascade:MRR"),
        ],
    )


def _row(gid: str, mrr=None, was=None, discount=None, offer_mrr=None) -> dict[str, Any]:
    return {
        "gid": gid,
        "mrr": mrr,
        "weekly_ad_spend": was,
        "discount": discount,
        "offer_mrr": offer_mrr,
    }


def _frame(rows: list[dict[str, Any]]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=_SCHEMA_COLS)


def _cf(name: str, number: float | None) -> dict[str, Any]:
    return {"name": name, "resource_subtype": "number", "number_value": number}


def _task(mrr: float | None, was: float | None = None) -> dict[str, Any]:
    """A cached per-task GET-copy carrying the MRR + Weekly Ad Spend number CFs."""
    return {"custom_fields": [_cf("MRR", mrr), _cf("Weekly Ad Spend", was)]}


class _CountingStore:
    """UnifiedTaskStore stand-in. Counts get_batch_async calls (the not-N+1 proof)
    and makes ZERO Asana calls — a pure dict lookup, mirroring IMMEDIATE cache-only
    reads (cache-miss => None, never a live fetch)."""

    def __init__(self, cache: dict[str, dict[str, Any] | None]):
        self._cache = cache
        self.batch_calls = 0
        self.total_gids_requested = 0

    async def get_batch_async(self, gids, freshness=None, required_level=None):
        self.batch_calls += 1
        self.total_gids_requested += len(list(gids))
        return {g: self._cache.get(g) for g in gids}


class _RaisingStore:
    async def get_batch_async(self, *a, **k):
        raise RuntimeError("cache backend exploded")


# ── 1. not-N+1 (G-THEATER) ──────────────────────────────────────────────────


async def test_single_batch_read_never_n_plus_1():
    frame = _frame([_row(f"g{i}") for i in range(1, 5)])  # 4 rows, mrr+was both null
    store = _CountingStore(
        {
            "g1": _task(450.0, 150.0),
            "g2": _task(425.0, 125.0),
            "g3": _task(650.0, 350.0),
            "g4": _task(600.0, 300.0),
        }
    )
    healed, receipt = await recover_null_number_cells(frame, _schema(), store, "unit", "P")

    assert store.batch_calls == 1, (
        f"not-N+1: exactly ONE cache batch read for 4 rows x 2 null cols (got {store.batch_calls})"
    )
    assert store.total_gids_requested == 4, "batch bounded by distinct null-row gids, not cells"
    assert healed["mrr"].null_count() == 0
    assert healed["weekly_ad_spend"].null_count() == 0
    assert receipt.healed_cells == 8


# ── 2. heal-proof (G-PROVE, falsifiable exact values) ───────────────────────


async def test_heal_proof_specific_values_from_cache():
    frame = _frame([_row("g1")])
    store = _CountingStore({"g1": _task(1800.0, 300.0)})
    healed, receipt = await recover_null_number_cells(frame, _schema(), store, "unit", "P")

    assert healed["mrr"].to_list() == [1800.0]
    assert healed["weekly_ad_spend"].to_list() == [300.0]
    assert receipt.attempted is True
    assert receipt.healed_cells == 2
    assert receipt.healed_by_column == {"mrr": 1, "weekly_ad_spend": 1}


# ── 3. never-fabricate (null-cache + cache-miss stay null) ──────────────────


async def test_never_fabricate_null_cache_and_cache_miss_stay_null():
    frame = _frame([_row("g1"), _row("g2")])
    # g1: cache copy present but MRR/WAS genuinely null. g2: cache MISS (None).
    store = _CountingStore({"g1": _task(None, None), "g2": None})
    healed, receipt = await recover_null_number_cells(frame, _schema(), store, "unit", "P")

    assert healed["mrr"].to_list() == [None, None]
    assert healed["weekly_ad_spend"].to_list() == [None, None]
    assert receipt.healed_cells == 0
    assert receipt.cache_miss_gids == 1  # g2
    assert receipt.residual_null_cells == 4


# ── 4. never-overwrite (coalesce-only) ──────────────────────────────────────


async def test_never_overwrite_already_populated_cell():
    frame = _frame([_row("g1", mrr=999.0)])  # mrr already populated; was null
    store = _CountingStore({"g1": _task(450.0, 150.0)})  # cache disagrees (450) — must NOT win
    healed, _receipt = await recover_null_number_cells(frame, _schema(), store, "unit", "P")

    assert healed["mrr"].to_list() == [999.0], "populated cell must NOT be overwritten"
    assert healed["weekly_ad_spend"].to_list() == [150.0], "the null cell heals"


# ── 5. G-PROPAGATE (one loop; cascade + non-numeric excluded) ───────────────


async def test_g_propagate_one_loop_excludes_cascade_and_nonnumeric():
    frame = _frame([_row("g1", discount=None, offer_mrr=None)])
    store = _CountingStore({"g1": _task(450.0, 150.0)})
    healed, receipt = await recover_null_number_cells(frame, _schema(), store, "unit", "P")

    assert store.batch_calls == 1
    assert set(receipt.columns) == {"mrr", "weekly_ad_spend"}
    assert healed["discount"].to_list() == [None], "non-numeric cf: untouched"
    assert healed["offer_mrr"].to_list() == [None], "cascade: untouched"


# ── 6. additive / never-raises ──────────────────────────────────────────────


async def test_additive_never_raises_on_store_error():
    frame = _frame([_row("g1")])
    healed, receipt = await recover_null_number_cells(
        frame, _schema(), _RaisingStore(), "unit", "P"
    )

    assert healed["mrr"].to_list() == [None], "frame returned unchanged on store error"
    assert receipt.attempted is False


# ── 7. no-op guards (no store read) ─────────────────────────────────────────


async def test_noop_guards_make_no_store_call():
    f_null = _frame([_row("g1")])
    store = _CountingStore({})

    _, r_no_schema = await recover_null_number_cells(f_null, None, store, "unit", "P")
    assert r_no_schema.attempted is False
    assert store.batch_calls == 0

    _, r_no_store = await recover_null_number_cells(f_null, _schema(), None, "unit", "P")
    assert r_no_store.attempted is False

    f_empty = _frame([])
    _, r_empty = await recover_null_number_cells(f_empty, _schema(), store, "unit", "P")
    assert r_empty.attempted is False
    assert store.batch_calls == 0

    # all numeric cf cells populated => null_rows empty => early return, NO store read
    f_full = _frame([_row("g1", mrr=1.0, was=2.0)])
    _, r_full = await recover_null_number_cells(f_full, _schema(), store, "unit", "P")
    assert r_full.attempted is False
    assert store.batch_calls == 0
