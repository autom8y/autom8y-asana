"""QA-ADVERSARY fixtures for the frame-first warm-projection build (N3, FORK-1 A-then-D).

Rite-disjoint adversarial suite -- written to BREAK the build, not confirm it.
Covers the seven dispatched fixtures:

  (a) STALE/PRE-1.5.0 FRAME  -> honest REFUSE, never fabricate/default-fill
  (b) EMPTY FRAME/GUID SET   -> REFUSE (empty push == whole-source mass-wipe)
  (c) MIXED COVERAGE         -> universe == exactly the resolvable-guid set;
                                guid-less DROP; nulls follow absent->ACTIVE;
                                de-enrolled PRESENT with enrolled=False
  (d) DEDUP TEETH            -> deterministic joint representative (max
                                last_modified, gid tie-break), row-order
                                independent; drift signal two-sided
  (e) RUNTIME BUDGET         -> synthetic frame at REAL scale (~4,151 rows)
                                through the full projection+dedup+payload path,
                                asserted orders-of-magnitude under the 900s
                                Lambda ceiling
  (f) WIRE COMPAT            -> the built payload validates against an
                                extra="forbid" replica of the FROZEN v2 entry
                                shape (docs/contracts/scheduling-posture-wire-v2.md);
                                enrolled=False entries PRESENT
  (g) GATE SHORT-CIRCUIT     -> gate unset/false => {skipped, gate_off} BEFORE
                                any substrate construction or frame read

Each guard here is TWO-SIDED: it passes on the real build and was demonstrated
RED against deliberately-broken ephemeral variants (fabricating schema-lag fill,
first-row-wins dedup, weakened empty-set gate, wire-shape violation, gate-after-
enumerate) during the N3 adversarial run; the variants were fully reverted.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import random
import time
from typing import Any, Literal

import polars as pl
import pytest
from pydantic import BaseModel, ConfigDict

from autom8_asana.lambda_handlers import scheduling_stratum_snapshot as snap
from autom8_asana.lambda_handlers.scheduling_stratum_snapshot import (
    SnapshotRefusedError,
    execute_snapshot_push,
    handler,
    project_offer_frame,
)
from autom8_asana.normalizer.scheduling_extractor import (
    CUSTOM_CAL_STATUS_FIELD,
    GUID_FIELD,
    REQUIRED_FRAME_COLUMNS,
    ExtractedScheduling,
    FrameSchemaLagError,
    map_frame_row_to_inputs,
)
from autom8_asana.normalizer.scheduling_stratum import CASCADE_PRIORITY
from autom8_asana.services.scheduling_stratum_push import (
    SCHEDULING_STRATUM_PUSH_ENABLED_ENV_VAR,
    StratumPushResult,
    resolve_and_push_snapshot,
    resolve_office_entries,
)

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]

_TS = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)


def _frame(rows: list[dict[str, Any]]) -> pl.DataFrame:
    """A 1.5.0-complete offer frame; omitted posture columns default to null."""
    complete: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        base: dict[str, Any] = {
            "gid": row.get("gid", f"o{i}"),
            "last_modified": row.get("last_modified", _TS),
        }
        for col in REQUIRED_FRAME_COLUMNS:
            base[col] = row.get(col)
        complete.append(base)
    return pl.DataFrame(
        complete,
        schema={
            "gid": pl.Utf8,
            "last_modified": pl.Datetime(time_unit="us", time_zone="UTC"),
            **{c: pl.Utf8 for c in REQUIRED_FRAME_COLUMNS},
        },
    )


def _empty_150_frame() -> pl.DataFrame:
    """A schema-complete (1.5.0) frame with ZERO rows -- the empty-universe case."""
    return pl.DataFrame(
        schema={
            "gid": pl.Utf8,
            "last_modified": pl.Datetime(time_unit="us", time_zone="UTC"),
            **{c: pl.Utf8 for c in REQUIRED_FRAME_COLUMNS},
        }
    )


class _FrameCacheEntry:
    def __init__(self, df: pl.DataFrame | None) -> None:
        self.dataframe = df


class _FakeCache:
    def __init__(self, entry: _FrameCacheEntry | None) -> None:
        self._entry = entry

    async def get_async(self, project_gid: str, entity_type: str) -> _FrameCacheEntry | None:
        return self._entry


async def _push_bomb(_offices: list[ExtractedScheduling]) -> StratumPushResult:
    raise AssertionError("push must NEVER run on a refused/skipped snapshot")


# =============================================================================
# (a) STALE / PRE-1.5.0 FRAME -- refuse honestly, never fabricate
# =============================================================================


def test_qa_a_pre150_frame_refuses_at_projection() -> None:
    """A frame lacking ALL posture columns (true pre-1.5.0) REFUSES -- no fabrication."""
    stale = pl.DataFrame(
        {
            "gid": ["o1", "o2"],
            "name": ["Offer 1", "Offer 2"],
            "last_modified": [_TS, _TS],
        }
    )
    with pytest.raises(FrameSchemaLagError, match="pre-1.5.0"):
        project_offer_frame(stale)


def test_qa_a_partial_lag_frame_refuses_not_default_fills() -> None:
    """PARTIAL lag (has company_id, lacks the other 9) is the fabrication danger.

    A default-filling variant would invent enrolled=True ACTIVE posture for every
    guid here and push a fleet-wide fabricated snapshot. The real build must refuse.
    """
    partial = pl.DataFrame(
        {
            "gid": ["o1", "o2"],
            "last_modified": [_TS, _TS],
            GUID_FIELD: ["g1", "g2"],  # identities present -- the tempting case
            # custom_cal_status + the 8 cascade columns ABSENT
        }
    )
    with pytest.raises(FrameSchemaLagError, match="pre-1.5.0"):
        project_offer_frame(partial)


def test_qa_a_single_missing_column_still_refuses() -> None:
    """Boundary: 9/10 posture columns present, ONLY custom_cal_status missing -> refuse."""
    cols: dict[str, Any] = {
        "gid": ["o1"],
        "last_modified": [_TS],
        GUID_FIELD: ["g1"],
    }
    for field in CASCADE_PRIORITY:
        cols[field] = ["x"]
    lagged = pl.DataFrame(cols)  # no custom_cal_status column
    with pytest.raises(FrameSchemaLagError, match=CUSTOM_CAL_STATUS_FIELD):
        project_offer_frame(lagged)


def test_qa_a_adapter_row_lag_refuses_backstop() -> None:
    """Defensive per-row backstop: a row dict missing a posture KEY refuses too."""
    row: dict[str, Any] = {"gid": "o1", GUID_FIELD: "g1", CUSTOM_CAL_STATUS_FIELD: None}
    for field in CASCADE_PRIORITY[:-1]:
        row[field] = None
    # custom_ghl_id key ABSENT -- the adapter must not .get() it into existence.
    with pytest.raises(FrameSchemaLagError, match="custom_ghl_id"):
        map_frame_row_to_inputs(row)


async def test_qa_a_schema_lag_run_refuses_and_never_pushes() -> None:
    """End-to-end: SWR-stale frame -> refused outcome, reason honest, push NEVER invoked."""
    stale = pl.DataFrame({"gid": ["o1"], "last_modified": [_TS]})
    cache = _FakeCache(_FrameCacheEntry(stale))

    async def _enumerate() -> tuple[list[ExtractedScheduling], bool]:
        return await snap._enumerate_offices_from_frame(cache, "proj-1")

    result = await execute_snapshot_push(
        gate=lambda: True, enumerate_offices=_enumerate, push=_push_bomb
    )
    assert result.status == "refused"
    assert result.entry_count == 0
    assert "pre-1.5.0" in (result.reason or "")


# =============================================================================
# (b) EMPTY FRAME / EMPTY GUID SET -- refusal is load-bearing (mass-wipe guard)
# =============================================================================


async def test_qa_b_empty_frame_refuses_no_push() -> None:
    """A 0-row (schema-complete) frame MUST refuse -- an empty push is a mass-wipe."""
    cache = _FakeCache(_FrameCacheEntry(_empty_150_frame()))

    async def _enumerate() -> tuple[list[ExtractedScheduling], bool]:
        return await snap._enumerate_offices_from_frame(cache, "proj-1")

    result = await execute_snapshot_push(
        gate=lambda: True, enumerate_offices=_enumerate, push=_push_bomb
    )
    assert result.status == "refused"
    assert "empty" in (result.reason or "")
    assert result.entry_count == 0


async def test_qa_b_all_guidless_frame_refuses() -> None:
    """Rows exist but NONE carries a usable guid -> empty universe -> refuse."""
    df = _frame([{GUID_FIELD: None, "calendly_url": "cal"}, {GUID_FIELD: "   "}])
    cache = _FakeCache(_FrameCacheEntry(df))

    async def _enumerate() -> tuple[list[ExtractedScheduling], bool]:
        return await snap._enumerate_offices_from_frame(cache, "proj-1")

    result = await execute_snapshot_push(
        gate=lambda: True, enumerate_offices=_enumerate, push=_push_bomb
    )
    assert result.status == "refused"
    assert "empty" in (result.reason or "")


async def test_qa_b_absent_frame_refuses_source_incomplete() -> None:
    """No warmed offer frame at all -> source_complete=False -> refuse."""
    cache = _FakeCache(None)

    async def _enumerate() -> tuple[list[ExtractedScheduling], bool]:
        return await snap._enumerate_offices_from_frame(cache, "proj-1")

    result = await execute_snapshot_push(
        gate=lambda: True, enumerate_offices=_enumerate, push=_push_bomb
    )
    assert result.status == "refused"
    assert "complete snapshot" in (result.reason or "")


# =============================================================================
# (c) MIXED COVERAGE -- universe == exactly the resolvable-guid set
# =============================================================================


def _mixed_frame() -> pl.DataFrame:
    return _frame(
        [
            # g1: enrolled, fields present
            {GUID_FIELD: "g1", CUSTOM_CAL_STATUS_FIELD: "Active", "calendly_url": "https://c/1"},
            # guid-less offer with RICH fields -- must DROP (fail SAFE by absence)
            {GUID_FIELD: None, CUSTOM_CAL_STATUS_FIELD: "Active", "reviewwave_id": "rw-orphan"},
            # whitespace guid -- must DROP too (not a usable identity)
            {GUID_FIELD: "  ", "sked_id": "sk-orphan"},
            # g2: ALL posture fields null -> absent->ACTIVE default, GHL-fallback stratum
            {GUID_FIELD: "g2"},
            # g3: de-enrolled with an explicit GHL id -- PRESENT with enrolled=False
            {GUID_FIELD: "g3", CUSTOM_CAL_STATUS_FIELD: "Inactive", "custom_ghl_id": "ghl-3"},
        ]
    )


def test_qa_c_universe_is_exactly_the_resolvable_guid_set() -> None:
    extracted, drift = project_offer_frame(_mixed_frame())
    assert sorted(o.guid for o in extracted) == ["g1", "g2", "g3"]
    assert drift == []  # no multi-offer guid disagrees here
    by_guid = {o.guid: o for o in extracted}
    # nulls follow absent->ACTIVE (g2), never fabricated values
    assert by_guid["g2"].enrolled is True
    assert all(v is None for v in by_guid["g2"].normalized_inputs.values())
    # de-enrolled PRESENT (g3), category/destination preserved
    assert by_guid["g3"].enrolled is False
    assert by_guid["g3"].normalized_inputs["custom_ghl_id"] == "ghl-3"
    # the orphan values must not leak into any surviving office
    flat = [v for o in extracted for v in o.normalized_inputs.values() if v is not None]
    assert "rw-orphan" not in flat
    assert "sk-orphan" not in flat


def test_qa_c_deenrolled_survives_into_wire_entries() -> None:
    """enrolled=False rides ALL the way into contract entries -- never filtered."""
    extracted, _ = project_offer_frame(_mixed_frame())
    entries = resolve_office_entries(extracted, resolved_at=_TS)
    assert len(entries) == 3
    flags = {e["guid"]: e["enrolled"] for e in entries}
    assert flags == {"g1": True, "g2": True, "g3": False}


# =============================================================================
# (d) DEDUP TEETH -- deterministic joint representative + drift signal
# =============================================================================


def _disagreeing_multi_offer_rows() -> list[dict[str, Any]]:
    """One guid, three offers DISAGREEING on custom_cal_status AND destination."""
    return [
        {
            "gid": "o-old",
            "last_modified": dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
            GUID_FIELD: "gX",
            CUSTOM_CAL_STATUS_FIELD: "Active",
            "calendly_url": "https://c/old",
        },
        {
            "gid": "o-mid",
            "last_modified": dt.datetime(2026, 2, 1, tzinfo=dt.UTC),
            GUID_FIELD: "gX",
            CUSTOM_CAL_STATUS_FIELD: "Active",
            "reviewwave_id": "rw-mid",
        },
        {
            "gid": "o-new",
            "last_modified": dt.datetime(2026, 3, 1, tzinfo=dt.UTC),
            GUID_FIELD: "gX",
            CUSTOM_CAL_STATUS_FIELD: "Inactive",
            "sked_id": "sk-new",
        },
    ]


def test_qa_d_joint_representative_is_max_modified_status_and_destination() -> None:
    """The winner supplies status AND destination JOINTLY -- never a chimera."""
    extracted, drift = project_offer_frame(_frame(_disagreeing_multi_offer_rows()))
    assert len(extracted) == 1
    rep = extracted[0]
    # Newest offer (o-new) wins BOTH axes jointly:
    assert rep.enrolled is False  # its status (Inactive) -- not the older Active
    assert rep.normalized_inputs["sked_id"] == "sk-new"  # its destination
    assert rep.normalized_inputs["calendly_url"] is None  # NOT the old offer's
    assert rep.normalized_inputs["reviewwave_id"] is None  # NOT the mid offer's
    # ... and the disagreement is metered:
    assert drift == ["gX"]


@pytest.mark.parametrize("seed", [1, 7, 42])
def test_qa_d_representative_is_row_order_independent(seed: int) -> None:
    """FIRST-ROW-WINS NONDETERMINISM GUARD: any input permutation, same output.

    This is the test that fires RED on a broken variant that keeps the first
    frame row per guid instead of sorting by (last_modified, gid).
    """
    rows = _disagreeing_multi_offer_rows()
    shuffled = rows[:]
    random.Random(seed).shuffle(shuffled)
    baseline, drift_a = project_offer_frame(_frame(rows))
    permuted, drift_b = project_offer_frame(_frame(shuffled))
    assert permuted == baseline
    assert sorted(drift_a) == sorted(drift_b) == ["gX"]
    assert permuted[0].enrolled is False  # the max-last_modified winner, always


def test_qa_d_tiebreak_same_timestamp_is_deterministic() -> None:
    """Equal last_modified -> gid tie-break; both orderings agree."""
    rows = [
        {"gid": "o-a", "last_modified": _TS, GUID_FIELD: "gT", "calendly_url": "https://c/a"},
        {"gid": "o-b", "last_modified": _TS, GUID_FIELD: "gT", "calendly_url": "https://c/b"},
    ]
    fwd, _ = project_offer_frame(_frame(rows))
    rev, _ = project_offer_frame(_frame(list(reversed(rows))))
    assert fwd == rev
    assert fwd[0].normalized_inputs["calendly_url"] == "https://c/b"  # gid desc: o-b


def test_qa_d_null_last_modified_never_beats_concrete() -> None:
    rows = [
        {"gid": "o-null", "last_modified": None, GUID_FIELD: "gN", "sked_id": "sk-null"},
        {"gid": "o-real", "last_modified": _TS, GUID_FIELD: "gN", "sked_id": "sk-real"},
    ]
    fwd, _ = project_offer_frame(_frame(rows))
    rev, _ = project_offer_frame(_frame(list(reversed(rows))))
    assert fwd == rev
    assert fwd[0].normalized_inputs["sked_id"] == "sk-real"


def test_qa_d_drift_two_sided_agreement_is_silent() -> None:
    """Drift fires ONLY on genuine disagreement -- agreeing multi-offer guids are quiet."""
    rows = [
        {"gid": "o1", GUID_FIELD: "gA", CUSTOM_CAL_STATUS_FIELD: "Active"},
        {"gid": "o2", GUID_FIELD: "gA", CUSTOM_CAL_STATUS_FIELD: "Active"},
        {"gid": "o3", GUID_FIELD: "gB", CUSTOM_CAL_STATUS_FIELD: "Active"},
        {"gid": "o4", GUID_FIELD: "gB", CUSTOM_CAL_STATUS_FIELD: "Inactive"},
    ]
    extracted, drift = project_offer_frame(_frame(rows))
    assert drift == ["gB"]
    assert len(extracted) == 2  # drift METERS, never blocks


def test_qa_d_drift_blind_spot_null_vs_value_pinned() -> None:
    """PINNED CURRENT BEHAVIOR (QA finding, LOW): null-vs-value is NOT metered.

    A guid whose offers carry {null, "Inactive"} disagrees MATERIALLY (the null
    projects enrolled=True, the value enrolled=False) yet the drift metric counts
    only distinct NON-NULL statuses, so it stays silent. The representative is
    still deterministic (max last_modified), so this is an observability gap,
    not a correctness/safety defect. If drift semantics are widened later this
    pin should flip.
    """
    rows = [
        {"gid": "o1", "last_modified": _TS, GUID_FIELD: "gZ", CUSTOM_CAL_STATUS_FIELD: None},
        {
            "gid": "o2",
            "last_modified": dt.datetime(2026, 2, 1, tzinfo=dt.UTC),
            GUID_FIELD: "gZ",
            CUSTOM_CAL_STATUS_FIELD: "Inactive",
        },
    ]
    extracted, drift = project_offer_frame(_frame(rows))
    assert drift == []  # <-- the blind spot, pinned
    assert extracted[0].enrolled is False  # deterministic winner regardless


# =============================================================================
# (e) RUNTIME BUDGET -- real scale through the full projection+payload path
# =============================================================================


def _real_scale_frame(n_rows: int = 4151, n_guids: int = 600) -> pl.DataFrame:
    rng = random.Random(20260702)
    statuses = [None, None, None, "Active", "Inactive", "active", "Paused"]
    rows: list[dict[str, Any]] = []
    for i in range(n_rows):
        guid = f"guid-{rng.randrange(n_guids):05d}" if rng.random() > 0.05 else None
        row: dict[str, Any] = {
            "gid": f"offer-{i:06d}",
            "last_modified": dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
            + dt.timedelta(minutes=rng.randrange(200_000)),
            GUID_FIELD: guid,
            CUSTOM_CAL_STATUS_FIELD: rng.choice(statuses),
        }
        for field in CASCADE_PRIORITY:
            row[field] = f"{field}-val-{i}" if rng.random() < 0.18 else None
        rows.append(row)
    return _frame(rows)


def test_qa_e_runtime_budget_full_path_at_real_scale() -> None:
    """~4,151 realistic rows through project -> resolve -> payload: << 900s ceiling.

    Budget asserted at 30s (30x margin under the Lambda ceiling); the measured
    wall-clock on the N3 run was well under a second (see the printed timing).
    """
    df = _real_scale_frame()
    started = time.perf_counter()
    extracted, drift = project_offer_frame(df)
    result = asyncio.run(resolve_and_push_snapshot(extracted, dry_run=True))
    elapsed = time.perf_counter() - started

    # Sanity: the run did real work at real scale.
    distinct_guids = df.filter(pl.col(GUID_FIELD).is_not_null()).get_column(GUID_FIELD).n_unique()
    assert len(extracted) == distinct_guids
    assert result.entry_count == distinct_guids
    assert result.pushed is False and result.dry_run is True
    print(
        f"\nQA-E RUNTIME: rows={df.height} guids={distinct_guids} "
        f"drift={len(drift)} elapsed={elapsed:.3f}s (budget 30s, ceiling 900s)"
    )
    assert elapsed < 30.0, f"projection+payload took {elapsed:.1f}s -- budget blown"


# =============================================================================
# (f) WIRE COMPAT -- frozen v2 entry shape, extra="forbid" replica
# =============================================================================


class _FrozenV2Entry(BaseModel):
    """Byte-faithful replica of the FROZEN wire-contract-v2 entry (extra=forbid).

    v1 {guid, stratum, custom_ghl_id, ghl_calendar_id, resolved_at} + v2
    {enrolled, canonical_destination_url, ghl_ownership} -- nothing else may appear
    (envelope-only fields on an entry would 422 the data-side sync).
    """

    model_config = ConfigDict(extra="forbid")

    guid: str
    stratum: str
    custom_ghl_id: str | None
    ghl_calendar_id: str | None
    resolved_at: str | None
    enrolled: bool
    canonical_destination_url: str | None
    ghl_ownership: Literal["client_owned", "internal_duration", "none"]


class _FrozenV2Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_source: str
    entries: list[_FrozenV2Entry]
    source_timestamp: str
    entry_count: int


async def test_qa_f_payload_validates_against_frozen_v2_replica() -> None:
    extracted, _ = project_offer_frame(_mixed_frame())
    result = await resolve_and_push_snapshot(extracted, dry_run=True)
    envelope = _FrozenV2Envelope.model_validate(result.payload)  # raises on ANY drift
    assert envelope.entry_count == len(envelope.entries) == 3
    assert envelope.snapshot_source == "asana"
    # enrolled=False entries PRESENT on the wire (the CH-01 cure) -- never omitted.
    assert [e.guid for e in envelope.entries if e.enrolled is False] == ["g3"]
    # De-enrolled office still carries its GHL coordinates (fail-safe fallback data).
    g3 = next(e for e in envelope.entries if e.guid == "g3")
    assert g3.custom_ghl_id == "ghl-3"
    assert g3.ghl_ownership == "client_owned"


async def test_qa_f_real_scale_payload_every_entry_frozen_shape() -> None:
    """Every real-scale entry validates; no row smuggles extra keys onto the wire."""
    extracted, _ = project_offer_frame(_real_scale_frame())
    result = await resolve_and_push_snapshot(extracted, dry_run=True)
    envelope = _FrozenV2Envelope.model_validate(result.payload)
    assert envelope.entry_count == len(extracted)
    assert any(e.enrolled is False for e in envelope.entries)
    assert any(e.enrolled is True for e in envelope.entries)


# =============================================================================
# (g) GATE SHORT-CIRCUIT -- {skipped, gate_off} BEFORE any frame read
# =============================================================================


def _arm_substrate_bombs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Poison every substrate entry point the enumerate closure would touch."""
    import autom8_asana.cache.dataframe.factory as factory
    import autom8_asana.models.business._bootstrap as bootstrap_mod

    def _bomb(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("substrate touched with the gate OFF -- DARK guarantee broken")

    monkeypatch.setattr(factory, "get_dataframe_cache", _bomb)
    monkeypatch.setattr(factory, "initialize_dataframe_cache", _bomb)
    monkeypatch.setattr(bootstrap_mod, "bootstrap", _bomb)


@pytest.mark.parametrize("gate_value", [None, "", "false", "0", "no", "FALSE"])
def test_qa_g_gate_off_handler_skips_before_any_frame_read(
    monkeypatch: pytest.MonkeyPatch, gate_value: str | None
) -> None:
    if gate_value is None:
        monkeypatch.delenv(SCHEDULING_STRATUM_PUSH_ENABLED_ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(SCHEDULING_STRATUM_PUSH_ENABLED_ENV_VAR, gate_value)
    _arm_substrate_bombs(monkeypatch)

    response = handler({}, None)

    assert response["statusCode"] == 200
    assert response["body"] == {"status": "skipped", "reason": "gate_off", "entry_count": 0}


async def test_qa_g_execute_gate_off_never_enumerates_or_pushes() -> None:
    async def _enumerate_bomb() -> tuple[list[ExtractedScheduling], bool]:
        raise AssertionError("enumerate invoked with the gate OFF")

    result = await execute_snapshot_push(
        gate=lambda: False, enumerate_offices=_enumerate_bomb, push=_push_bomb
    )
    assert result == snap.SnapshotRunResult(status="skipped", reason="gate_off", entry_count=0)
