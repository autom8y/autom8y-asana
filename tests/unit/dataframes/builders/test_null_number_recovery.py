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

Cold-tier (§8/§9): the cold read is stubbed ONLY at the boto3-CLIENT boundary (a
fake ``get_object(Bucket, Key)``), so it exercises the cure's REAL key construction
(``asana-cache/tasks/<gid>/task.json``), REAL ``json.loads`` of raw-dict bytes, and
REAL ``{"data": ...}`` envelope unwrap. A ``CacheEntry``-stub at the provider
boundary is DELIBERATELY NOT used: that boundary hides the #120 dual defect (wrong
prefix + ``S3CacheProvider`` envelope deserialization) the rebuild corrects.
"""

from __future__ import annotations

import json
from typing import Any

import polars as pl
import pytest

import autom8_asana.dataframes.builders.null_number_recovery as nnr
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


# ── 1+2. not-N+1 (G-THEATER) + heal-proof (G-PROVE) — merged parameterized ──
#
# CHANGE-004 (eunomia): merged §1 and §2 into one parameterized test.
# Assertion union preserved across both param cases:
#   §1 (not_n_plus_1_4rows): batch_calls 1, total_gids_requested 4,
#       null_count 0 on both cols, healed_cells 8.
#   §2 (heal_proof_exact_values): mrr 1800.0, weekly_ad_spend 300.0,
#       attempted True, healed_cells 2, healed_by_column mrr+was each 1.


@pytest.mark.parametrize(
    "frame,cache_dict,expected",
    [
        pytest.param(
            # §1: 4-row frame — proves not-N+1 (exactly ONE batch read, batch bounded
            # by distinct null-row gids not cells) and full null healing across 4 rows.
            _frame([_row(f"g{i}") for i in range(1, 5)]),
            {
                "g1": _task(450.0, 150.0),
                "g2": _task(425.0, 125.0),
                "g3": _task(650.0, 350.0),
                "g4": _task(600.0, 300.0),
            },
            {
                "batch_calls": 1,
                "total_gids_requested": 4,
                "mrr_null_count": 0,
                "was_null_count": 0,
                "healed_cells": 8,
            },
            id="not_n_plus_1_4rows",
        ),
        pytest.param(
            # §2: 1-row frame — proves EXACT cached values (falsifiable heal-proof).
            _frame([_row("g1")]),
            {"g1": _task(1800.0, 300.0)},
            {
                "batch_calls": 1,
                "total_gids_requested": 1,
                "mrr_exact": [1800.0],
                "was_exact": [300.0],
                "attempted": True,
                "healed_cells": 2,
                "healed_by_column": {"mrr": 1, "weekly_ad_spend": 1},
            },
            id="heal_proof_exact_values",
        ),
    ],
)
async def test_hot_tier_heal_not_n_plus_1_and_exact_values(frame, cache_dict, expected):
    """§1+§2 merged: not-N+1 (G-THEATER) + heal-proof (G-PROVE) in one parameterized test.

    Both cases share the _CountingStore infra and assert overlapping hot-path heal
    behavior. Assertions are case-conditional: §1 checks batch bounds + null_count;
    §2 checks exact values + receipt fields.
    """
    store = _CountingStore(cache_dict)
    healed, receipt = await recover_null_number_cells(frame, _schema(), store, "unit", "P")

    # Common across both cases: exactly one batch call.
    assert store.batch_calls == expected["batch_calls"], (
        f"not-N+1: expected exactly ONE batch call (got {store.batch_calls})"
    )

    if "total_gids_requested" in expected:
        assert store.total_gids_requested == expected["total_gids_requested"], (
            "batch bounded by distinct null-row gids, not cells"
        )

    # §1-specific: null_count assertions (4-row frame, both cols fully healed).
    if "mrr_null_count" in expected:
        assert healed["mrr"].null_count() == expected["mrr_null_count"]
        assert healed["weekly_ad_spend"].null_count() == expected["was_null_count"]

    assert receipt.healed_cells == expected["healed_cells"]

    # §2-specific: exact-value heal-proof assertions.
    if "mrr_exact" in expected:
        assert healed["mrr"].to_list() == expected["mrr_exact"]
        assert healed["weekly_ad_spend"].to_list() == expected["was_exact"]
        assert receipt.attempted is expected["attempted"]
        assert receipt.healed_by_column == expected["healed_by_column"]


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


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ COLD-TIER (durable S3) — REAL key construction + REAL parsing             ║
# ╚══════════════════════════════════════════════════════════════════════════╝
#
# These stub ONLY at the boto3-CLIENT boundary. The fake client's
# get_object(Bucket, Key) ASSERTS the EXACT key the cure built and returns a Body
# of the REAL raw-dict JSON bytes that live at asana-cache/tasks/<gid>/task.json in
# production. This exercises the cure's REAL _cold_task_cache_key, REAL json.loads,
# and REAL _unwrap_task_data envelope handling. A CacheEntry/get_versioned stub is
# DELIBERATELY NOT used — that boundary masks the #120 prefix + envelope defect.


class _NoSuchKey(Exception):
    """Mirrors botocore's NoSuchKey class name (the cure classifies by type name)."""


class _Body:
    """Minimal stand-in for the StreamingBody returned by boto3 get_object."""

    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


# A REAL raw-Asana-task-dict shape, as the live object at
# asana-cache/tasks/1207519540893045/task.json looks (top-level gid/name/
# custom_fields; the MRR cf is resource_subtype "number" with number_value).
def _raw_task_object(gid: str, mrr: float | None, was: float | None = None) -> dict[str, Any]:
    return {
        "gid": gid,
        "resource_type": "task",
        "name": f"Unit {gid}",
        "resource_subtype": "default_task",
        "custom_fields": [
            {
                "gid": "1100000000000001",
                "name": "MRR",
                "resource_subtype": "number",
                "type": "number",
                "number_value": mrr,
                "display_value": None if mrr is None else str(mrr),
            },
            {
                "gid": "1100000000000002",
                "name": "Weekly Ad Spend",
                "resource_subtype": "number",
                "type": "number",
                "number_value": was,
                "display_value": None if was is None else str(was),
            },
            {
                "gid": "1100000000000003",
                "name": "Discount",
                "resource_subtype": "enum",
                "type": "enum",
                "enum_value": {"name": "10%"} if mrr is not None else None,
                "display_value": "10%" if mrr is not None else None,
            },
        ],
        "memberships": [{"section": {"name": "Active"}}],
    }


class _FakeS3Client:
    """boto3-CLIENT-boundary stub. get_object(Bucket, Key) asserts the bucket and the
    EXACT key, and returns the REAL raw-dict JSON bytes for present gids; raises a
    NoSuchKey-named error otherwise (the cure's 404 classification). Counts each GET
    (the not-N+1-at-gid proof) and records every key seen (the key-construction proof).

    ``objects`` maps the EXACT S3 key -> the raw task dict (so the test asserts the
    cure constructed asana-cache/tasks/<gid>/task.json byte-for-byte). ZERO Asana
    calls — this is a pure dict lookup over durable S3 copies."""

    def __init__(self, bucket: str, objects: dict[str, dict[str, Any]]):
        self._bucket = bucket
        self._objects = objects
        self.get_calls = 0
        self.keys_seen: list[str] = []

    def get_object(self, *, Bucket: str, Key: str):
        self.get_calls += 1
        self.keys_seen.append(Key)
        assert Bucket == self._bucket, f"unexpected bucket {Bucket!r}"
        if Key in self._objects:
            return {"Body": _Body(json.dumps(self._objects[Key]).encode("utf-8"))}
        raise _NoSuchKey(f"NoSuchKey: {Key}")


class _ColdHotStore:
    """UnifiedTaskStore stand-in: the HOT store is COLD (get_batch_async returns all
    None — the steady-state resume=True warm reality) so every null gid falls through
    to the cold tier. ZERO Asana calls (pure dict lookup)."""

    def __init__(self):
        self.hot_batch_calls = 0

    async def get_batch_async(self, gids, freshness=None, required_level=None):
        self.hot_batch_calls += 1
        return {g: None for g in gids}  # HOT IS COLD


@pytest.fixture
def _reset_s3_client(monkeypatch):
    """Reset the module-cached boto3 client around each cold-tier test and pin the
    bucket so no live AWS/boto3 is touched. The fake client is installed per-test."""
    monkeypatch.setattr(nnr, "_S3_CLIENT", None, raising=False)
    monkeypatch.setattr(nnr, "_S3_CLIENT_BUILD_ATTEMPTED", False, raising=False)
    yield
    monkeypatch.setattr(nnr, "_S3_CLIENT", None, raising=False)
    monkeypatch.setattr(nnr, "_S3_CLIENT_BUILD_ATTEMPTED", False, raising=False)


def _install_fake_client(monkeypatch, client: _FakeS3Client, bucket: str) -> None:
    """Pin the cure's module-cached client to ``client`` and its bucket to ``bucket``
    via a stubbed settings object — the ONLY stub boundary is the boto3 client."""
    monkeypatch.setattr(nnr, "_get_s3_client", lambda: client)

    class _S3:
        pass

    s3 = _S3()
    s3.bucket = bucket
    s3.region = "us-east-1"
    s3.endpoint_url = None
    s3.prefix = "asana-cache/project-frames/"  # the POLLUTED prefix — must be IGNORED

    class _Settings:
        pass

    settings = _Settings()
    settings.s3 = s3
    monkeypatch.setattr(nnr, "get_settings", _make_get_settings(settings), raising=False)
    # get_settings is imported INSIDE _cold_read_durable from autom8_asana.settings,
    # so patch it at the source module too.
    import autom8_asana.settings as settings_mod

    monkeypatch.setattr(settings_mod, "get_settings", _make_get_settings(settings))


def _make_get_settings(settings):
    def _get_settings():
        return settings

    return _get_settings


# ── 8. cold-tier heals from the durable S3 raw-dict copies (REAL key + parse) ─


async def test_cold_tier_heals_from_real_raw_s3_objects(monkeypatch, _reset_s3_client):
    """RED on the as-merged #120 cure (wrong prefix + S3CacheProvider envelope read);
    GREEN after the raw-S3-GET rebuild. The fake client asserts the EXACT key the
    cure built and returns REAL raw-dict bytes — no CacheEntry stub anywhere."""
    bucket = "autom8-s3"
    # g_active1/2: present in S3 with populated MRR=1500. g_tmpl: present but null
    # source (Template). g_miss: absent from S3 (404). g_pop: present (mrr 99) but
    # already-populated in the frame (4242) — must NOT be overwritten.
    objects = {
        "asana-cache/tasks/g_active1/task.json": _raw_task_object("g_active1", 1500.0, 200.0),
        "asana-cache/tasks/g_active2/task.json": _raw_task_object("g_active2", 1500.0, 200.0),
        "asana-cache/tasks/g_tmpl/task.json": _raw_task_object("g_tmpl", None, None),
        "asana-cache/tasks/g_pop/task.json": _raw_task_object("g_pop", 99.0, 777.0),
        # g_miss intentionally absent -> 404
    }
    client = _FakeS3Client(bucket, objects)
    _install_fake_client(monkeypatch, client, bucket)

    frame = _frame(
        [
            _row("g_active1"),
            _row("g_active2"),
            _row("g_tmpl"),
            _row("g_miss"),
            _row("g_pop", mrr=4242.0),  # already-populated mrr; was null
        ]
    )
    store = _ColdHotStore()

    healed, receipt = await recover_null_number_cells(frame, _schema(), store, "unit", "P")

    # heal-proof (falsifiable EXACT values): active units recover the cached 1500.0
    by_gid = dict(zip(healed["gid"].to_list(), healed["mrr"].to_list(), strict=True))
    assert by_gid["g_active1"] == 1500.0
    assert by_gid["g_active2"] == 1500.0
    # never-fabricate: Template (S3 null) + cache-MISS (absent from S3 -> 404) stay null
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

    # KEY-CONSTRUCTION proof: the cure built EXACTLY asana-cache/tasks/<gid>/task.json
    # for every hot-miss gid (NOT the polluted asana-cache/project-frames/... prefix).
    # The 4 present gids hit on the un-suffixed key; g_miss 404s and also probes .gz.
    assert sorted(set(client.keys_seen)) == [
        "asana-cache/tasks/g_active1/task.json",
        "asana-cache/tasks/g_active2/task.json",
        "asana-cache/tasks/g_miss/task.json",
        "asana-cache/tasks/g_miss/task.json.gz",  # .gz fallback after the 404
        "asana-cache/tasks/g_pop/task.json",
        "asana-cache/tasks/g_tmpl/task.json",
    ]
    # No key ever used the polluted dataframe-storage prefix.
    assert all("project-frames" not in k for k in client.keys_seen)
    # not-N+1 at gid granularity: ONE hot batch + EXACTLY ONE GET per distinct hot-miss
    # gid for the 4 present gids. g_miss misses the un-suffixed key then tries .gz, so
    # it accounts for 2 GETs (404 + 404 -> honest cache-miss). 4 present + 2 (g_miss) = 6.
    assert store.hot_batch_calls == 1
    assert client.get_calls == 6, (
        f"one GET per present gid + a .gz fallback only for the 404 (got {client.get_calls})"
    )

    # receipt: cold_present_gids counts hot-miss gids whose durable S3 copy was PRESENT
    # (a task dict came back), independent of CF nullity: active1, active2, tmpl, pop = 4.
    assert receipt.attempted is True
    assert receipt.cold_present_gids == 4
    # cache_miss = null in BOTH tiers: only g_miss (404 on S3). g_tmpl is a cold HIT
    # with a genuinely-null source, so it is NOT a cache miss.
    assert receipt.cache_miss_gids == 1
    # healed_by_column counts recoverable non-null values per column (mrr:
    # active1+active2+pop=3, was: active1+active2+pop=3). Distinct from healed_cells
    # (=5): the populated g_pop mrr is found but coalesce-preserved, not flipped.
    assert receipt.healed_by_column == {"mrr": 3, "weekly_ad_spend": 3}
    assert receipt.healed_cells == 5


# ── 8b. envelope unwrap: {"data": {...}} Asana-wrapped copies parse identically ─


async def test_cold_tier_unwraps_data_envelope(monkeypatch, _reset_s3_client):
    """Some durable copies are persisted as the verbatim Asana ``{"data": {...}}``
    response. The cure's _unwrap_task_data must reach the inner task dict (mirrors the
    probe's raw.get('data', raw))."""
    bucket = "autom8-s3"
    wrapped = {"data": _raw_task_object("g_wrap", 1234.0, 56.0)}
    objects = {"asana-cache/tasks/g_wrap/task.json": wrapped}
    client = _FakeS3Client(bucket, objects)
    _install_fake_client(monkeypatch, client, bucket)

    frame = _frame([_row("g_wrap")])
    healed, receipt = await recover_null_number_cells(
        frame, _schema(), _ColdHotStore(), "unit", "P"
    )

    assert healed["mrr"].to_list() == [1234.0]
    assert healed["weekly_ad_spend"].to_list() == [56.0]
    assert receipt.healed_cells == 2
    assert client.keys_seen == ["asana-cache/tasks/g_wrap/task.json"]


# ── 8c. gzip body: a .json.gz fallback decompresses + parses ────────────────


async def test_cold_tier_reads_gzip_fallback(monkeypatch, _reset_s3_client):
    """When only the .gz key exists, the cure tries the un-suffixed key (404), falls
    back to .gz, gunzips, and parses — mirroring the probe's two-key probe."""
    import gzip as _gzip

    bucket = "autom8-s3"
    raw = _raw_task_object("g_gz", 4321.0, 21.0)
    gz_bytes = _gzip.compress(json.dumps(raw).encode("utf-8"))

    class _GzClient:
        def __init__(self):
            self.get_calls = 0
            self.keys_seen: list[str] = []

        def get_object(self, *, Bucket, Key):
            self.get_calls += 1
            self.keys_seen.append(Key)
            assert Bucket == bucket
            if Key == "asana-cache/tasks/g_gz/task.json.gz":
                return {"Body": _Body(gz_bytes)}
            raise _NoSuchKey(f"NoSuchKey: {Key}")

    client = _GzClient()
    _install_fake_client(monkeypatch, client, bucket)

    healed, receipt = await recover_null_number_cells(
        _frame([_row("g_gz")]), _schema(), _ColdHotStore(), "unit", "P"
    )

    assert healed["mrr"].to_list() == [4321.0]
    assert healed["weekly_ad_spend"].to_list() == [21.0]
    assert client.keys_seen == [
        "asana-cache/tasks/g_gz/task.json",  # 404
        "asana-cache/tasks/g_gz/task.json.gz",  # hit
    ]


# ── 8d. no client resolvable => clean no-op (honest-null), never raises ─────


async def test_cold_tier_noop_when_no_client(monkeypatch, _reset_s3_client):
    """No boto3 client resolvable (missing creds / boto3 / bucket) => clean no-op:
    the hot read ran (attempted) but nothing heals and nothing is fabricated."""
    monkeypatch.setattr(nnr, "_get_s3_client", lambda: None)

    healed, receipt = await recover_null_number_cells(
        _frame([_row("g1")]), _schema(), _ColdHotStore(), "unit", "P"
    )
    assert healed["mrr"].to_list() == [None]
    assert receipt.attempted is True  # the pass ran (hot read happened), healed 0
    assert receipt.healed_cells == 0
    assert receipt.cold_present_gids == 0
    assert receipt.cache_miss_gids == 1  # g1 missed both tiers -> honest-null


# ── 8e. per-gid GET error (creds/throttle) => that gid honest-null, no raise ─


async def test_cold_tier_per_gid_error_is_swallowed_to_null(monkeypatch, _reset_s3_client):
    """A non-404 per-gid error (e.g. AccessDenied / throttle) contributes None for
    that gid (honest-null) and never raises — the additive contract."""
    bucket = "autom8-s3"

    class _PartlyBrokenClient:
        def __init__(self):
            self.get_calls = 0

        def get_object(self, *, Bucket, Key):
            self.get_calls += 1
            if "g_ok" in Key:
                return {"Body": _Body(json.dumps(_raw_task_object("g_ok", 500.0, 50.0)).encode())}
            raise RuntimeError("AccessDenied: throttled")

    client = _PartlyBrokenClient()
    _install_fake_client(monkeypatch, client, bucket)

    healed, receipt = await recover_null_number_cells(
        _frame([_row("g_ok"), _row("g_err")]), _schema(), _ColdHotStore(), "unit", "P"
    )
    by_gid = dict(zip(healed["gid"].to_list(), healed["mrr"].to_list(), strict=True))
    assert by_gid["g_ok"] == 500.0  # the healthy gid heals
    assert by_gid["g_err"] is None  # the erroring gid -> honest-null
    assert receipt.healed_cells == 2  # g_ok mrr + was
    assert receipt.cache_miss_gids == 1  # g_err


# ── 9. cold read is CONCURRENT and BOUNDED (the latency-blocker cure) ─────────
#
# The qa-adversary NO-GO: a single-worker sequential cold read is linear+unbounded
# in N (~3021 unit hot-miss gids => ~3021 sequential S3 GETs against a ~375s slack
# of the 900s Lambda budget). The cure fans the per-gid GETs out across worker
# threads, capped by a Semaphore. This test proves the read is BOTH parallel
# (max-in-flight > 1) AND bounded (max-in-flight <= cap), while every heal still
# lands at its exact cached value. Stubbed at the boto3-CLIENT boundary.


class _ConcurrencyProbeClient:
    """boto3-CLIENT-boundary stub that records the MAX number of get_object calls in
    flight at once. Each call briefly blocks (a real sleep on the worker thread) so
    concurrent reads genuinely overlap — the in-flight high-water mark is the
    parallelism proof. Thread-safe counters (the cure fans across to_thread workers).
    ZERO Asana calls."""

    def __init__(self, bucket: str, objects: dict[str, dict[str, Any]]):
        import threading

        self._bucket = bucket
        self._objects = objects
        self._lock = threading.Lock()
        self._in_flight = 0
        self.max_in_flight = 0
        self.get_calls = 0

    def get_object(self, *, Bucket, Key):
        import time

        with self._lock:
            self._in_flight += 1
            self.get_calls += 1
            if self._in_flight > self.max_in_flight:
                self.max_in_flight = self._in_flight
        try:
            time.sleep(0.02)  # hold the "connection" so siblings overlap
            if Key in self._objects:
                return {"Body": _Body(json.dumps(self._objects[Key]).encode("utf-8"))}
            raise _NoSuchKey(f"NoSuchKey: {Key}")
        finally:
            with self._lock:
                self._in_flight -= 1


async def test_cold_read_is_concurrent_and_bounded(monkeypatch, _reset_s3_client):
    """max-in-flight ∈ (1, cap]: the cold read parallelizes AND respects the cap,
    and every active gid still heals to its EXACT cached value."""
    cap = 8
    monkeypatch.setenv("ASANA_CURE_COLD_CONCURRENCY", str(cap))

    bucket = "autom8-s3"
    n = 40  # well above the cap, so the Semaphore must actually gate
    frame = _frame([_row(f"u{i}") for i in range(n)])  # all mrr+was null
    objects = {
        f"asana-cache/tasks/u{i}/task.json": _raw_task_object(f"u{i}", float(1000 + i), float(i))
        for i in range(n)
    }
    client = _ConcurrencyProbeClient(bucket, objects)
    _install_fake_client(monkeypatch, client, bucket)

    healed, receipt = await recover_null_number_cells(
        frame, _schema(), _ColdHotStore(), "unit", "P"
    )

    # PARALLELISM: at least two reads overlapped (a serial reader caps at 1).
    assert client.max_in_flight > 1, (
        f"cold read must be CONCURRENT (max in-flight was {client.max_in_flight} <= 1)"
    )
    # BOUND: the Semaphore never let more than `cap` reads run at once.
    assert client.max_in_flight <= cap, (
        f"cold read must be BOUNDED by the cap (max in-flight {client.max_in_flight} > {cap})"
    )
    # not-N+1 at gid granularity: exactly one GET per distinct hot-miss gid (all hit).
    assert client.get_calls == n

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
    monkeypatch.setenv("ASANA_CURE_COLD_CONCURRENCY", "0")
    assert nnr._cold_concurrency() == nnr._COLD_CONCURRENCY_MIN  # 0 -> clamped up

    monkeypatch.setenv("ASANA_CURE_COLD_CONCURRENCY", "100000")
    assert nnr._cold_concurrency() == nnr._COLD_CONCURRENCY_MAX  # absurd -> clamped down

    monkeypatch.setenv("ASANA_CURE_COLD_CONCURRENCY", "not-a-number")
    assert nnr._cold_concurrency() == nnr._COLD_CONCURRENCY_DEFAULT  # garbage -> default

    monkeypatch.delenv("ASANA_CURE_COLD_CONCURRENCY", raising=False)
    assert nnr._cold_concurrency() == nnr._COLD_CONCURRENCY_DEFAULT  # unset -> default


# ── KEY-CONSTRUCTION unit: the pinned prefix is DECOUPLED from settings.prefix ─


def test_cold_key_uses_pinned_prefix_not_settings_prefix():
    """The cure pins asana-cache/tasks/<gid>/task.json — NOT get_settings().s3.prefix
    (which prod overloads to asana-cache/project-frames/). This is the #120 cure's
    root defect; assert the key construction is decoupled from the polluted setting."""
    assert nnr._DURABLE_TASK_CACHE_PREFIX == "asana-cache"
    assert nnr._cold_task_cache_key("1207519540893045") == (
        "asana-cache/tasks/1207519540893045/task.json"
    )
    # explicitly NOT the polluted dataframe-storage prefix
    assert "project-frames" not in nnr._cold_task_cache_key("1207519540893045")
