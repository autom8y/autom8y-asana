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

from datetime import UTC, datetime
from typing import Any

import polars as pl

from autom8_asana.cache.models.entry import CacheEntry, EntryType
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


# ── 8. cold-tier (S3) recovery — the deliberately-broken fixture (G-THEATER) ──
#
# This is the steady-state-warm reality the cure must heal: the HOT store is COLD
# (resume=True warm re-fetches 0 tasks), so the tier-1 read misses EVERY null gid.
# But the durable S3 per-task copies DO carry the number_value. The unmodified
# cure (tier-1 only) heals 0 here (RED). The fix adds a tier-2 batched S3 read of
# the per-task copies and heals the active cells (GREEN). Template/cache-miss gids
# stay null; populated cells are NOT overwritten; the S3 read is a SINGLE batch.


def _entry(gid: str, task_data: dict[str, Any]) -> CacheEntry:
    """A durable S3 CacheEntry whose .data is the raw per-task copy."""
    return CacheEntry(
        key=gid,
        data=task_data,
        entry_type=EntryType.TASK,
        version=datetime(2026, 1, 1, tzinfo=UTC),
        cached_at=datetime.now(UTC),
        ttl=604800,  # 7d — mirrors the durable-write TTL
    )


class _S3Backend:
    """Durable S3 cold-tier stand-in. Mirrors S3CacheProvider.get_versioned:
    get_versioned(key, EntryType.TASK) -> CacheEntry | None (the per-key API the
    bounded-concurrency cure fans out across worker threads). Counts each
    per-gid read (the not-N+1-at-gid-granularity proof for the cold tier: exactly
    one read per distinct hot-miss gid) and makes ZERO Asana calls (a pure dict
    lookup over durable copies)."""

    _degraded = False  # the cure skips a degraded backend; this one is healthy

    def __init__(self, entries: dict[str, CacheEntry | None]):
        self._entries = entries
        self.read_calls = 0
        self.read_gids: list[str] = []
        self.last_entry_type: EntryType | None = None

    def get_versioned(self, key, entry_type, freshness=None):
        self.read_calls += 1
        self.read_gids.append(key)
        self.last_entry_type = entry_type
        return self._entries.get(key)


class _TieredCacheStub:
    """TieredCacheProvider stand-in exposing a cold tier via ``_cold`` — the
    same handle the cure resolves first (reuse-configured-infrastructure path)."""

    def __init__(self, cold: _S3Backend):
        self._cold = cold


class _ColdHotStore:
    """UnifiedTaskStore stand-in for the broken fixture: the HOT store is COLD
    (get_batch_async returns all None) but ``store.cache._cold`` is a POPULATED
    durable S3 tier. ZERO Asana calls on either tier (pure dict lookups)."""

    def __init__(self, cold: _S3Backend):
        self.cache = _TieredCacheStub(cold)
        self.hot_batch_calls = 0

    async def get_batch_async(self, gids, freshness=None, required_level=None):
        self.hot_batch_calls += 1
        return {g: None for g in gids}  # HOT IS COLD — the steady-state warm reality


# Active units carry a populated MRR in S3 (1500.0). g_tmpl is a Template whose
# S3 copy is genuinely null. g_miss is absent from S3 entirely (cache MISS).
def _cold_fixture() -> _S3Backend:
    return _S3Backend(
        {
            "g_active1": _entry("g_active1", _task(1500.0, 200.0)),
            "g_active2": _entry("g_active2", _task(1500.0, 200.0)),
            "g_tmpl": _entry("g_tmpl", _task(None, None)),
            "g_miss": None,
        }
    )


async def test_cold_tier_heals_when_hot_is_cold_but_s3_populated():
    """RED on the unmodified (tier-1-only) cure; GREEN after the tier-2 S3 fill."""
    frame = _frame(
        [
            _row("g_active1"),
            _row("g_active2"),
            _row("g_tmpl"),
            _row("g_miss"),
            _row("g_pop", mrr=4242.0),  # already-populated mrr; was null
        ]
    )
    cold = _cold_fixture()
    cold._entries["g_pop"] = _entry("g_pop", _task(99.0, 777.0))  # disagrees on mrr
    store = _ColdHotStore(cold)

    healed, receipt = await recover_null_number_cells(frame, _schema(), store, "unit", "P")

    # heal-proof (falsifiable EXACT values): active units recover the cached 1500.0
    by_gid = dict(zip(healed["gid"].to_list(), healed["mrr"].to_list(), strict=True))
    assert by_gid["g_active1"] == 1500.0
    assert by_gid["g_active2"] == 1500.0
    # never-fabricate: Template (S3 null) + cache-MISS (absent from S3) stay null
    assert by_gid["g_tmpl"] is None
    assert by_gid["g_miss"] is None
    # never-overwrite: the already-populated mrr is preserved (cache 99.0 must NOT win)
    assert by_gid["g_pop"] == 4242.0

    # weekly_ad_spend heals field-agnostically through the SAME loop
    was_by_gid = dict(
        zip(healed["gid"].to_list(), healed["weekly_ad_spend"].to_list(), strict=True)
    )
    assert was_by_gid["g_active1"] == 200.0
    assert was_by_gid["g_pop"] == 777.0  # the null was-cell heals even on a populated-mrr row

    # not-N+1 at gid granularity: ONE hot batch + EXACTLY ONE cold read per distinct
    # hot-miss gid. All 5 rows have a null cell (g_pop's mrr is populated but its
    # weekly_ad_spend is null, so g_pop enters the null set too), and the hot store
    # is COLD for all of them => 5 distinct hot-miss gids => 5 cold reads, keyed by
    # EntryType.TASK. The fan-out parallelizes those reads; it does not multiply them.
    assert store.hot_batch_calls == 1
    assert cold.read_calls == 5, (
        f"cold tier must be ONE read per distinct hot-miss gid (got {cold.read_calls})"
    )
    assert sorted(cold.read_gids) == ["g_active1", "g_active2", "g_miss", "g_pop", "g_tmpl"]
    assert cold.last_entry_type == EntryType.TASK

    # receipt: cold_present_gids counts hot-miss gids whose durable S3 copy was
    # PRESENT (a task dict came back), independent of whether its CF was null:
    # g_active1, g_active2, g_tmpl (present-but-null source), g_pop = 4. g_miss is
    # absent from S3 (None) so it is NOT counted as present.
    assert receipt.attempted is True
    assert receipt.cold_present_gids == 4
    # cache_miss = null in BOTH tiers: only g_miss (absent from S3). g_tmpl is a
    # cold HIT with a genuinely-null source, so it is NOT a cache miss.
    assert receipt.cache_miss_gids == 1
    # healed_by_column counts recoverable non-null values found per column (mrr:
    # active1+active2+pop=3, was: active1+active2+pop=3). Distinct from healed_cells
    # (=5): the populated g_pop mrr is found but coalesce-preserved, not flipped.
    assert receipt.healed_by_column == {"mrr": 3, "weekly_ad_spend": 3}
    assert receipt.healed_cells == 5


async def test_cold_tier_noop_when_no_cold_backend_resolvable(monkeypatch):
    """No durable backend resolvable => clean no-op, frame unchanged, never raises.

    Forces ``_resolve_cold_backend -> None`` (the unconfigured-bucket / missing-boto3
    / degraded production posture) so the test is hermetic (no live S3/boto3) and
    asserts the honest-null contract: the hot read ran (attempted), but with no cold
    tier nothing heals and nothing is fabricated."""
    import autom8_asana.dataframes.builders.null_number_recovery as mod

    monkeypatch.setattr(mod, "_resolve_cold_backend", lambda _store: None)

    class _ColdHotNoBackend:
        async def get_batch_async(self, gids, freshness=None, required_level=None):
            return {g: None for g in gids}  # hot is cold

    frame = _frame([_row("g1")])
    healed, receipt = await recover_null_number_cells(
        frame, _schema(), _ColdHotNoBackend(), "unit", "P"
    )
    assert healed["mrr"].to_list() == [None]
    assert receipt.attempted is True  # the pass ran (hot read happened), healed 0
    assert receipt.healed_cells == 0
    assert receipt.cold_present_gids == 0
    assert receipt.cache_miss_gids == 1  # g1 missed both tiers -> honest-null


# ── 9. cold read is CONCURRENT and BOUNDED (the latency-blocker cure) ─────────
#
# The qa-adversary NO-GO: a single-worker sequential cold read is linear+unbounded
# in N (~3021 unit hot-miss gids => ~3021 sequential S3 GETs against a ~375s slack
# of the 900s Lambda budget). The cure fans the per-gid get_versioned reads out
# across worker threads, capped by a Semaphore. This test proves the read is BOTH
# parallel (max-in-flight > 1) AND bounded (max-in-flight <= cap), while every heal
# still lands at its exact cached value.


class _ConcurrencyProbeBackend:
    """Cold-tier stand-in that records the MAX number of get_versioned calls
    in flight at once. Each call briefly blocks (a real sleep on the worker
    thread) so concurrent reads genuinely overlap -- the in-flight high-water
    mark is the parallelism proof. Thread-safe counters (the cure fans the reads
    across asyncio.to_thread worker threads). ZERO Asana calls (dict lookup)."""

    _degraded = False

    def __init__(self, entries: dict[str, CacheEntry | None]):
        import threading

        self._entries = entries
        self._lock = threading.Lock()
        self._in_flight = 0
        self.max_in_flight = 0
        self.read_calls = 0

    def get_versioned(self, key, entry_type, freshness=None):
        import time

        with self._lock:
            self._in_flight += 1
            self.read_calls += 1
            if self._in_flight > self.max_in_flight:
                self.max_in_flight = self._in_flight
        try:
            # Hold the "connection" briefly so siblings overlap; long enough that
            # a serial implementation would NEVER show in_flight > 1.
            time.sleep(0.02)
            return self._entries.get(key)
        finally:
            with self._lock:
                self._in_flight -= 1


class _ConcurrencyProbeStore:
    """Hot store is COLD; store.cache._cold is the concurrency-probe backend."""

    def __init__(self, cold: _ConcurrencyProbeBackend):
        self.cache = _TieredCacheStub(cold)

    async def get_batch_async(self, gids, freshness=None, required_level=None):
        return {g: None for g in gids}  # HOT IS COLD


async def test_cold_read_is_concurrent_and_bounded(monkeypatch):
    """max-in-flight ∈ (1, cap]: the cold read parallelizes AND respects the cap,
    and every active gid still heals to its EXACT cached value."""
    cap = 8
    monkeypatch.setenv("ASANA_CURE_COLD_CONCURRENCY", str(cap))

    n = 40  # well above the cap, so the Semaphore must actually gate
    frame = _frame([_row(f"u{i}") for i in range(n)])  # all mrr+was null
    # Every gid is an active unit whose S3 copy carries a distinct populated MRR.
    entries: dict[str, CacheEntry | None] = {
        f"u{i}": _entry(f"u{i}", _task(float(1000 + i), float(i))) for i in range(n)
    }
    cold = _ConcurrencyProbeBackend(entries)
    store = _ConcurrencyProbeStore(cold)

    healed, receipt = await recover_null_number_cells(frame, _schema(), store, "unit", "P")

    # PARALLELISM: at least two reads overlapped (a serial reader caps at 1).
    assert cold.max_in_flight > 1, (
        f"cold read must be CONCURRENT (max in-flight was {cold.max_in_flight} <= 1)"
    )
    # BOUND: the Semaphore never let more than `cap` reads run at once.
    assert cold.max_in_flight <= cap, (
        f"cold read must be BOUNDED by the cap (max in-flight {cold.max_in_flight} > {cap})"
    )
    # not-N+1 at gid granularity: exactly one cold read per distinct hot-miss gid.
    assert cold.read_calls == n

    # heal-proof (falsifiable EXACT values): every active gid recovered its MRR.
    by_gid = dict(zip(healed["gid"].to_list(), healed["mrr"].to_list(), strict=True))
    for i in range(n):
        assert by_gid[f"u{i}"] == float(1000 + i)
    assert healed["mrr"].null_count() == 0
    assert healed["weekly_ad_spend"].null_count() == 0
    assert receipt.healed_cells == 2 * n  # mrr + weekly_ad_spend, every row
    assert receipt.cold_present_gids == n


async def test_cold_concurrency_env_override_is_clamped(monkeypatch):
    """The env override is clamped to a sane range and shrugs off garbage."""
    import autom8_asana.dataframes.builders.null_number_recovery as mod

    monkeypatch.setenv("ASANA_CURE_COLD_CONCURRENCY", "0")
    assert mod._cold_concurrency() == mod._COLD_CONCURRENCY_MIN  # 0 -> clamped up

    monkeypatch.setenv("ASANA_CURE_COLD_CONCURRENCY", "100000")
    assert mod._cold_concurrency() == mod._COLD_CONCURRENCY_MAX  # absurd -> clamped down

    monkeypatch.setenv("ASANA_CURE_COLD_CONCURRENCY", "not-a-number")
    assert mod._cold_concurrency() == mod._COLD_CONCURRENCY_DEFAULT  # garbage -> default

    monkeypatch.delenv("ASANA_CURE_COLD_CONCURRENCY", raising=False)
    assert mod._cold_concurrency() == mod._COLD_CONCURRENCY_DEFAULT  # unset -> default
