"""Cure-Recovery-Path Hardening — fail-closed write + quality-aware freshness.

Anti-theater integration test for ADR-cure-recovery-path-hardening-2026-06-11.
Stubs ONLY the boto3 transport boundary (a revoked-grant ``get_object`` raising
AccessDenied for the ``asana-cache/tasks/<gid>/task.json`` prefix). REAL
``DataFrameSchema`` / ``PopulationReceipt`` / ``NumericRecoveryReceipt`` shapes,
REAL keys, exact-key assertions. The cure
(``recover_null_number_cells``), the population floor
(``post_build_population_receipt``), the write decision
(``fail_closed_write.decide_write``), and the persistence
(``write_final_artifacts_async`` against an in-memory storage) are all the REAL
code paths — NEVER stubbed above the transport boundary
(@THROUGHLINE-integration-boundary-fidelity §4).

The forcing question this guards (GRANDEUR ANCHOR): under a durable-read OUTAGE
the cure heals nothing, the floor breaches, and the warm MUST degrade to the
LAST-GOOD frame (never persist a freshly-nulled frame) AND auto-re-heal on the
next healthy warm (never freshness-skip the recovery).

RED-1 (Fork-1): a wholesale revoked-grant warm with a strictly-better prior-good
frame on disk MUST NOT overwrite it with the degraded (0/N) frame. On unmodified
code the Step-6 write gate is unconditional, so the degraded frame persists — the
inline behavioral baseline ``test_BASELINE_*`` proves the gap is real.

RED-2 (Fork-2): a persisted below-floor frame + a now-healthy durable read MUST
trigger a rebuild (the quality term in the rebuild gate), NOT freshness-skip.
"""

from __future__ import annotations

import json
from typing import Any

import polars as pl
import pytest

import autom8_asana.dataframes.builders.null_number_recovery as nnr
from autom8_asana.dataframes.builders.fail_closed_write import (
    WriteDecision,
    coalesce_prior_good,
    decide_write,
)
from autom8_asana.dataframes.builders.null_number_recovery import (
    recover_null_number_cells,
)
from autom8_asana.dataframes.builders.post_build_population_receipt import (
    post_build_population_receipt,
)
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema

# Canonical unit-frame economics: mrr is the value column the active_mrr
# denominator is computed over (post_build_population_receipt._VALUE_COLUMNS_BY_ENTITY
# "unit": ("mrr",)). The active subset is the "Active" section.
_BUCKET = "autom8-s3"
_ENTITY = "unit"
_PROJECT = "1207519540893045"

_SCHEMA_COLS = {
    "gid": pl.Utf8,
    "section": pl.Utf8,
    "is_completed": pl.Boolean,
    "mrr": pl.Float64,
}


def _schema() -> DataFrameSchema:
    """Real unit schema: mrr is a numeric cf: column (the cure heals it)."""
    return DataFrameSchema(
        name="unit",
        task_type="Unit",
        columns=[
            ColumnDef(name="gid", dtype="Utf8", source="gid"),
            ColumnDef(name="section", dtype="Utf8", source="section"),
            ColumnDef(name="is_completed", dtype="Boolean", source="is_completed"),
            ColumnDef(name="mrr", dtype="Float64", source="cf:MRR"),
        ],
    )


def _frame(rows: list[dict[str, Any]]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=_SCHEMA_COLS)


def _prior_good_frame(n_active: int = 5) -> pl.DataFrame:
    """A healthy prior-good frame: every active row carries a populated mrr."""
    rows = [
        {"gid": f"g{i}", "section": "Active", "is_completed": False, "mrr": 100.0 * (i + 1)}
        for i in range(n_active)
    ]
    return _frame(rows)


def _degraded_frame(n_active: int = 5) -> pl.DataFrame:
    """The freshly-built degraded frame: same active rows, mrr entirely null
    (the GID-only warm path stripped number_value and the cure cannot heal)."""
    rows = [
        {"gid": f"g{i}", "section": "Active", "is_completed": False, "mrr": None}
        for i in range(n_active)
    ]
    return _frame(rows)


def _raw_task_object(gid: str, mrr: float | None) -> dict[str, Any]:
    """A REAL durable per-task copy carrying the MRR number CF (the shape
    ``DurableTaskCacheReader.read_object`` parses)."""
    return {
        "gid": gid,
        "resource_type": "task",
        "name": f"Unit {gid}",
        "custom_fields": [
            {
                "gid": "1100000000000001",
                "name": "MRR",
                "resource_subtype": "number",
                "type": "number",
                "number_value": mrr,
                "display_value": None if mrr is None else str(mrr),
            }
        ],
        "memberships": [{"section": {"name": "Active"}}],
    }


# ── boto3-boundary stubs (the ONLY stub layer) ──────────────────────────────


class _Body:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


class _ClientError(Exception):
    """Mirrors botocore.exceptions.ClientError by class name + response shape.

    DurableTaskCacheReader.read_object classifies by type name + message:
    AccessDenied is neither NoSuchKey/404 nor ValueError/OSError, so read_object
    RE-RAISES it (durable_task_cache.py:240) -> read_batch_with._one maps the gid
    to None + WARN durable_task_cache_read_gid_failed (the wholesale-outage path)."""

    def __init__(self, op: str = "GetObject"):
        self.response = {
            "Error": {
                "Code": "AccessDenied",
                "Message": "User is not authorized to perform: s3:GetObject",
            }
        }
        super().__init__(f"An error occurred (AccessDenied) when calling the {op} operation")


class _RevokedGrantS3Client:
    """boto3-CLIENT-boundary stub: get_object RAISES AccessDenied for the
    durable-task prefix (asana-cache/tasks/<gid>/task.json). Asserts the EXACT key
    the cure built (key-construction proof) BEFORE raising, so a wrong prefix still
    fails loudly. Records every key seen (the keys_seen proof)."""

    def __init__(self, bucket: str, task_prefix: str):
        self._bucket = bucket
        self._prefix = task_prefix
        self.keys_seen: list[str] = []
        self.get_calls = 0

    def get_object(self, *, Bucket: str, Key: str):
        self.get_calls += 1
        self.keys_seen.append(Key)
        assert Bucket == self._bucket, f"unexpected bucket {Bucket!r}"
        assert Key.startswith(self._prefix), f"unexpected prefix: {Key!r}"
        raise _ClientError()


class _HealthyGrantS3Client:
    """boto3-CLIENT-boundary stub: get_object RETURNS the REAL raw-dict bytes for
    present gids (the restored-grant healthy warm). Asserts the EXACT key + bucket
    before serving; raises NoSuchKey-named for absent keys (honest 404)."""

    def __init__(self, bucket: str, objects: dict[str, dict[str, Any]]):
        self._bucket = bucket
        self._objects = objects
        self.keys_seen: list[str] = []
        self.get_calls = 0

    def get_object(self, *, Bucket: str, Key: str):
        self.get_calls += 1
        self.keys_seen.append(Key)
        assert Bucket == self._bucket, f"unexpected bucket {Bucket!r}"
        if Key in self._objects:
            return {"Body": _Body(json.dumps(self._objects[Key]).encode("utf-8"))}

        class _NoSuchKey(Exception):
            pass

        raise _NoSuchKey(f"NoSuchKey: {Key}")


class _ColdHotStore:
    """UnifiedTaskStore stand-in: the HOT store is COLD (get_batch_async returns all
    None — the steady-state resume=True warm reality), so every null gid falls
    through to the durable S3 tier. ZERO Asana calls (pure dict lookup)."""

    def __init__(self) -> None:
        self.hot_batch_calls = 0

    async def get_batch_async(self, gids, freshness=None, required_level=None):
        self.hot_batch_calls += 1
        return {g: None for g in gids}


# ── in-memory DataFrameStorage (real persistence path, no S3) ───────────────


class _InMemoryStorage:
    """In-memory DataFrameStorage stand-in for the PERSISTENCE path (distinct from
    the boto3 transport boundary the cure reads through). It implements the v2
    entity-keyed save/load contract faithfully so write_final_artifacts_async and
    the prior-good read exercise REAL section_persistence code."""

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
            "population_degraded": population_degraded,
            "population_min_rate": population_min_rate,
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


# ── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def _reset_s3_client(monkeypatch):
    """Reset the cure's module-cached boto3 client around each test and pin the
    bucket so no live AWS/boto3 is touched."""
    monkeypatch.setattr(nnr, "_S3_CLIENT", None, raising=False)
    monkeypatch.setattr(nnr, "_S3_CLIENT_BUILD_ATTEMPTED", False, raising=False)
    yield
    monkeypatch.setattr(nnr, "_S3_CLIENT", None, raising=False)
    monkeypatch.setattr(nnr, "_S3_CLIENT_BUILD_ATTEMPTED", False, raising=False)


def _make_get_settings(settings):
    def _get_settings():
        return settings

    return _get_settings


def _install_fake_client(monkeypatch, client: Any, bucket: str) -> None:
    """Pin the cure's module-cached client to ``client`` and its bucket to
    ``bucket`` via a stubbed settings object — the ONLY stub boundary is the boto3
    client (mirrors test_null_number_recovery._install_fake_client)."""
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
    import autom8_asana.settings as settings_mod

    monkeypatch.setattr(settings_mod, "get_settings", _make_get_settings(settings))


async def _warm_once(
    *,
    monkeypatch,
    client: Any,
    persistence,
    initial_frame: pl.DataFrame,
):
    """Run ONE faithful Step-6 warm sequence end-to-end:

    real cure -> real population receipt -> real write decision -> real persistence.

    Drives the builder's extracted Step-6 finalizer (the authoritative
    progressive.py write-gate seam) so the test exercises the SAME code path the
    warm runs in production. Returns (write_decision, recovery_receipt,
    population_receipt)."""
    _install_fake_client(monkeypatch, client, _BUCKET)
    from autom8_asana.dataframes.builders.progressive import ProgressiveProjectBuilder

    builder = ProgressiveProjectBuilder(
        client=None,
        project_gid=_PROJECT,
        entity_type=_ENTITY,
        schema=_schema(),
        persistence=persistence,
        store=_ColdHotStore(),
    )
    result = await builder._finalize_artifacts_write_async(
        merged_df=initial_frame,
        watermark=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )
    return result.decision, result.recovery_receipt, result.population_receipt


# ── BASELINE: the GAP is real (today's unconditional write persists nulls) ───


async def test_BASELINE_unconditional_write_persists_degraded_frame(monkeypatch, _reset_s3_client):
    """BEHAVIORAL BASELINE (proves the gap is real, not a strawman): reconstruct
    TODAY's Step-6 sequence VERBATIM — real cure under a revoked grant, real
    population receipt (return discarded), then the UNCONDITIONAL
    write_final_artifacts_async (progressive.py:868 `if total_rows > 0 ...`). This
    is exactly what unmodified code does; it MUST persist the degraded (0/5) frame
    OVER the prior-good (5/5). This test stays GREEN before AND after the fix — it
    asserts the OLD code path's behavior in isolation, documenting why the new
    decision seam is load-bearing."""
    storage = _InMemoryStorage()
    from autom8_asana.dataframes.section_persistence import SectionPersistence

    persistence = SectionPersistence(storage=storage)
    prior = _prior_good_frame(5)
    await storage.save_dataframe(
        _PROJECT,
        prior,
        __import__("datetime").datetime.now(__import__("datetime").UTC),
        entity_type=_ENTITY,
    )
    _install_fake_client(monkeypatch, _RevokedGrantS3Client(_BUCKET, "asana-cache/tasks/"), _BUCKET)

    degraded = _degraded_frame(5)
    # --- today's Step-6 sequence, verbatim ---
    healed, _recovery = await recover_null_number_cells(
        merged_df=degraded,
        schema=_schema(),
        store=_ColdHotStore(),
        entity_type=_ENTITY,
        project_gid=_PROJECT,
    )
    population = post_build_population_receipt(healed, _schema(), _ENTITY, _PROJECT)
    assert population.below_floor is True  # the floor WARNed (honest) ...
    # ... but the write fired UNCONDITIONALLY (return value discarded today):
    await persistence.write_final_artifacts_async(
        _PROJECT,
        healed,
        __import__("datetime").datetime.now(__import__("datetime").UTC),
        entity_type=_ENTITY,
    )
    persisted, _wm = await storage.load_dataframe(_PROJECT, entity_type=_ENTITY)
    mrr_nonnull = persisted.height - int(persisted["mrr"].null_count())
    assert mrr_nonnull == 0, "baseline did not reproduce the gap (degraded frame should persist)"


# ── RED-1 / GREEN-1: Fork-1 fail-closed write ────────────────────────────────


async def test_fork1_preserves_prior_good_under_revoked_grant(monkeypatch, _reset_s3_client):
    """RED-1 -> GREEN-1: a wholesale revoked-grant warm with a strictly-better
    prior-good frame on disk MUST preserve the prior-good frame (mrr_nonnull==5),
    never persist the degraded (0/5) frame.

    GREEN: persisted frame mrr_nonnull == prior-good count (5); keys_seen confirms
    the cure ATTEMPTED the exact durable keys (failure was at transport)."""
    storage = _InMemoryStorage()
    from autom8_asana.dataframes.section_persistence import SectionPersistence

    persistence = SectionPersistence(storage=storage)

    # Seed the prior-good frame at the REAL v2 key (5 active rows, all populated).
    prior = _prior_good_frame(5)
    await storage.save_dataframe(
        _PROJECT,
        prior,
        __import__("datetime").datetime.now(__import__("datetime").UTC),
        entity_type=_ENTITY,
    )

    client = _RevokedGrantS3Client(_BUCKET, "asana-cache/tasks/")
    decision, recovery, population = await _warm_once(
        monkeypatch=monkeypatch,
        client=client,
        persistence=persistence,
        initial_frame=_degraded_frame(5),
    )

    # The cure attempted the EXACT durable keys, then transport raised AccessDenied.
    assert client.get_calls > 0, "cure did not attempt any durable read (over-stub?)"
    assert all(
        k.startswith("asana-cache/tasks/") and k.endswith("/task.json") for k in client.keys_seen
    ), f"unexpected durable keys: {client.keys_seen!r}"

    # The floor breached over the ACTIVE subset, the cure healed nothing.
    assert population.below_floor is True
    assert recovery.healed_cells == 0
    assert recovery.cold_present_gids == 0

    # The write decision preserved the prior-good frame (no overwrite).
    assert decision is WriteDecision.PRESERVE_PRIOR_GOOD

    # The persisted frame is the PRIOR-GOOD frame (5/5), NOT the degraded (0/5).
    persisted, _wm = await storage.load_dataframe(_PROJECT, entity_type=_ENTITY)
    assert persisted is not None
    mrr_nonnull = persisted.height - int(persisted["mrr"].null_count())
    assert mrr_nonnull == 5, f"degraded frame persisted (mrr_nonnull={mrr_nonnull}, expected 5)"


async def test_fork1_cold_start_writes_honest_null(monkeypatch, _reset_s3_client):
    """COLD-START (Fork-1 1c fallback): NO prior-good frame + revoked grant =>
    WRITE_AS_IS the honest-null frame (NOT skipped) => honest-empty-200 invariant
    holds, no 503 trap."""
    storage = _InMemoryStorage()  # empty: no prior-good
    from autom8_asana.dataframes.section_persistence import SectionPersistence

    persistence = SectionPersistence(storage=storage)
    client = _RevokedGrantS3Client(_BUCKET, "asana-cache/tasks/")

    decision, _recovery, population = await _warm_once(
        monkeypatch=monkeypatch,
        client=client,
        persistence=persistence,
        initial_frame=_degraded_frame(5),
    )

    assert population.below_floor is True
    assert decision is WriteDecision.WRITE_AS_IS
    persisted, _wm = await storage.load_dataframe(_PROJECT, entity_type=_ENTITY)
    assert persisted is not None, "cold-start frame was SKIPPED (503 trap risk)"
    assert persisted.height == 5  # the honest-null frame IS persisted


# ── RED-2 / GREEN-2: Fork-2 quality-aware freshness ──────────────────────────


def test_fork2_below_floor_forces_rebuild_when_grant_healthy():
    """RED-2 -> GREEN-2: the rebuild gate fires on a persisted below-floor frame
    when the grant is healthy again — the quality term, NOT age. Dropping the
    `OR population_degraded` term makes this RED."""
    from autom8_asana.metrics.rebuild_gate import needs_rebuild

    # Frame is FRESH by age (stale_by_age False) but degraded by quality, grant healthy.
    assert (
        needs_rebuild(stale_by_age=False, population_degraded=True, grant_unhealthy_recently=False)
        is True
    )
    # Storm-suppressor: degraded but grant STILL revoked => do NOT rebuild on quality.
    assert (
        needs_rebuild(stale_by_age=False, population_degraded=True, grant_unhealthy_recently=True)
        is False
    )
    # Healthy frame, fresh => no rebuild.
    assert (
        needs_rebuild(stale_by_age=False, population_degraded=False, grant_unhealthy_recently=False)
        is False
    )
    # Age-stale always rebuilds (the load-bearing relief valve preserved).
    assert (
        needs_rebuild(stale_by_age=True, population_degraded=False, grant_unhealthy_recently=False)
        is True
    )


async def test_fork2_below_floor_clears_on_healthy_rewarm(monkeypatch, _reset_s3_client):
    """GREEN-2 end-to-end: after a healthy re-warm the durable read heals the
    cells, the floor clears (below_floor False), and population_degraded is no
    longer set on the persisted frame."""
    storage = _InMemoryStorage()
    from autom8_asana.dataframes.section_persistence import SectionPersistence

    persistence = SectionPersistence(storage=storage)

    # Durable copies are PRESENT and populated (grant restored).
    objects = {
        f"asana-cache/tasks/g{i}/task.json": _raw_task_object(f"g{i}", 100.0 * (i + 1))
        for i in range(5)
    }
    client = _HealthyGrantS3Client(_BUCKET, objects)

    decision, recovery, population = await _warm_once(
        monkeypatch=monkeypatch,
        client=client,
        persistence=persistence,
        initial_frame=_degraded_frame(5),
    )

    assert recovery.healed_cells == 5  # all cells healed from the durable tier
    assert population.below_floor is False  # floor cleared
    assert decision is WriteDecision.WRITE_AS_IS
    persisted, _wm = await storage.load_dataframe(_PROJECT, entity_type=_ENTITY)
    assert persisted is not None
    assert persisted.height - int(persisted["mrr"].null_count()) == 5


# ── COALESCE: Fork-1 1c partial-heal path ────────────────────────────────────


def test_coalesce_prior_good_fills_only_nulls():
    """WRITE_COALESCED rescues prior-good value cells into the new frame's NULL
    cells ONLY; an already-populated new cell is NEVER overwritten (never-fabricate
    / coalesce-only, NFR-6)."""
    new = _frame(
        [
            {"gid": "g0", "section": "Active", "is_completed": False, "mrr": 999.0},  # populated
            {"gid": "g1", "section": "Active", "is_completed": False, "mrr": None},  # null
            {
                "gid": "g2",
                "section": "Active",
                "is_completed": False,
                "mrr": None,
            },  # null, no prior
        ]
    )
    prior = _frame(
        [
            {"gid": "g0", "section": "Active", "is_completed": False, "mrr": 100.0},
            {"gid": "g1", "section": "Active", "is_completed": False, "mrr": 200.0},
        ]
    )
    out = coalesce_prior_good(new, prior, ("mrr",))
    by_gid = {r["gid"]: r["mrr"] for r in out.to_dicts()}
    assert by_gid["g0"] == 999.0  # NOT overwritten
    assert by_gid["g1"] == 200.0  # rescued from prior-good
    assert by_gid["g2"] is None  # honest-null (no prior value to copy)


def test_decide_write_partial_heal_with_better_prior_coalesces():
    """A partial heal (some cells came back) that is STILL below floor, with a
    strictly-better prior-good frame, decides WRITE_COALESCED — rescue the
    prior-good cells rather than preserve-or-overwrite."""
    from autom8_asana.dataframes.builders.null_number_recovery import (
        NumericRecoveryReceipt,
    )

    # New frame: 1/5 active healed (below floor 0.8); prior-good 5/5.
    new = _frame(
        [
            {"gid": "g0", "section": "Active", "is_completed": False, "mrr": 100.0},
            *[
                {"gid": f"g{i}", "section": "Active", "is_completed": False, "mrr": None}
                for i in range(1, 5)
            ],
        ]
    )
    population = post_build_population_receipt(new, _schema(), _ENTITY, _PROJECT)
    assert population.below_floor is True  # 1/5 = 0.2 < 0.8
    recovery = NumericRecoveryReceipt(
        entity_type=_ENTITY,
        attempted=True,
        columns=("mrr",),
        null_cells_before=5,
        healed_cells=1,  # partial heal -> NOT a wholesale outage
        residual_null_cells=4,
        cache_miss_gids=4,
        cold_present_gids=1,
    )
    decision = decide_write(population, recovery, _prior_good_frame(5), ("mrr",))
    assert decision is WriteDecision.WRITE_COALESCED


# ── OFFER-INTACT (NFR-3): per-entity, never cross-entity ─────────────────────


def _offer_schema() -> DataFrameSchema:
    return DataFrameSchema(
        name="offer",
        task_type="Offer",
        columns=[
            ColumnDef(name="gid", dtype="Utf8", source="gid"),
            ColumnDef(name="section", dtype="Utf8", source="section"),
            ColumnDef(name="is_completed", dtype="Boolean", source="is_completed"),
            ColumnDef(name="mrr", dtype="Float64", source="cf:MRR"),
            ColumnDef(name="offer_id", dtype="Utf8", source="cf:Offer ID"),
        ],
    )


_OFFER_COLS = {
    "gid": pl.Utf8,
    "section": pl.Utf8,
    "is_completed": pl.Boolean,
    "mrr": pl.Float64,
    "offer_id": pl.Utf8,
}


async def test_offer_intact_during_unit_revoked_grant_warm(monkeypatch, _reset_s3_client):
    """OFFER-INTACT (NFR-3): a revoked-grant warm of the UNIT entity fail-closes the
    unit frame, but the OFFER frame persisted under the SAME storage + project is
    UNTOUCHED. The offer decision is computed from the offer's OWN population receipt
    over the offer's OWN value columns — a unit fail-close cannot cross entities.

    Mutation proof (TDD §7.5 row 3): if the decision read a cross-entity frame, the
    offer write would change; this test asserts the offer frame is byte-stable."""
    storage = _InMemoryStorage()
    from autom8_asana.dataframes.builders.progressive import ProgressiveProjectBuilder
    from autom8_asana.dataframes.section_persistence import SectionPersistence

    persistence = SectionPersistence(storage=storage)
    now = __import__("datetime").datetime.now(__import__("datetime").UTC)

    # Seed a HEALTHY offer frame (live-served, must not regress) at the offer key.
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
        schema=_OFFER_COLS,
    )
    await storage.save_dataframe(_PROJECT, offer_frame, now, entity_type="offer")

    # Seed a strictly-better prior-good UNIT frame, then warm unit under revoked grant.
    await storage.save_dataframe(_PROJECT, _prior_good_frame(5), now, entity_type=_ENTITY)
    _install_fake_client(monkeypatch, _RevokedGrantS3Client(_BUCKET, "asana-cache/tasks/"), _BUCKET)
    unit_builder = ProgressiveProjectBuilder(
        client=None,
        project_gid=_PROJECT,
        entity_type=_ENTITY,
        schema=_schema(),
        persistence=persistence,
        store=_ColdHotStore(),
    )
    unit_result = await unit_builder._finalize_artifacts_write_async(
        merged_df=_degraded_frame(5),
        watermark=now,
    )
    assert unit_result.decision is WriteDecision.PRESERVE_PRIOR_GOOD  # unit fail-closed

    # The OFFER frame is byte-stable — never touched by the unit fail-close.
    offer_persisted, _wm = await storage.load_dataframe(_PROJECT, entity_type="offer")
    assert offer_persisted is not None
    assert offer_persisted.equals(offer_frame), "offer frame regressed during a unit warm"

    # And the offer's OWN decision is computed from its OWN value columns.
    offer_pop = post_build_population_receipt(offer_frame, _offer_schema(), "offer", _PROJECT)
    assert offer_pop.below_floor is False
    assert decide_write(offer_pop, None, offer_frame, ("mrr", "offer_id")) is (
        WriteDecision.WRITE_AS_IS
    )


# ── G-DENOM (NFR-4): inactive-null rows do NOT trip below_floor ──────────────


def test_g_denom_inactive_null_rows_do_not_trip_floor():
    """A frame whose NULL mrr rows are all INACTIVE (non-active sections) must NOT
    trip below_floor (the active-subset filter excludes them) => WRITE_AS_IS, no
    fail-close, no Fork-2 rebuild. Widening the floor to all rows makes this RED."""
    frame = _frame(
        [
            # active + populated
            *[
                {"gid": f"a{i}", "section": "Active", "is_completed": False, "mrr": 100.0}
                for i in range(4)
            ],
            # inactive + legitimately null (Backlog/Done) — must not drag the rate
            {"gid": "i0", "section": "Backlog", "is_completed": False, "mrr": None},
            {"gid": "i1", "section": "Done", "is_completed": True, "mrr": None},
        ]
    )
    population = post_build_population_receipt(frame, _schema(), _ENTITY, _PROJECT)
    assert population.below_floor is False, "inactive-null rows wrongly tripped the floor"
    decision = decide_write(population, None, _prior_good_frame(5), ("mrr",))
    assert decision is WriteDecision.WRITE_AS_IS
