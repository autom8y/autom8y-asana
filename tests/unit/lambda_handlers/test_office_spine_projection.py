"""Two-sided proof for the WS-B office-spine re-source (PR-2).

DIAG-ws-b-offer-frame-collapse-2026-08-05 §"Two-sided proof shape".

LEG A (positive) -- the universe is RECOVERED. A realistic office-spine fixture
projects to a spine-scale universe with populated posture, and clears the value
floor. Scaled to the measured live shape: ~921 offices on the spine vs a
``prior_count`` of 949, of which a large minority carry a real posture signal.

LEG B (discriminating negative) -- the UNCHANGED guards still BITE. Four
deliberately-broken INPUT FIXTURES, one per guard. No defect is injected into
working code: each fixture is a malformed *input* that the untouched guard must
correctly refuse, and each is paired with a healthy variant that passes the SAME
code path. A guard that stops being reachable has removed a safety, not passed a
test.

    | # | Broken fixture              | Guard that must refuse            |
    |---|----------------------------|-----------------------------------|
    | 1 | full universe, all-null posture | assert_posture_signal_floor  |
    | 2 | every company_id null       | assert_complete_office_set        |
    | 3 | collapsed universe          | data-side shrink guard (contract) |
    | 4 | unit_holder lacks posture cols | join_office_spine schema-lag   |

The value floor and the completeness gate are the ONLY reason 949 live office
postures were not overwritten with empties across 120/120 producer ticks. They are
untouched by WS-B; these tests prove it.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any

import polars as pl
import pytest

from autom8_asana.lambda_handlers import scheduling_stratum_snapshot as snap
from autom8_asana.lambda_handlers.scheduling_stratum_snapshot import (
    SnapshotRefusedError,
    assert_complete_office_set,
    assert_posture_signal_floor,
    execute_snapshot_push,
    join_office_spine,
    posture_signal_row_count,
    project_office_frame,
)
from autom8_asana.normalizer.scheduling_extractor import (
    CUSTOM_CAL_STATUS_FIELD,
    GUID_FIELD,
    ExtractedScheduling,
    FrameSchemaLagError,
)

if TYPE_CHECKING:
    from autom8_asana.services.scheduling_stratum_push import StratumPushResult

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]

_TS = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)

#: The nine posture columns UNIT_HOLDER_SCHEMA declares.
_POSTURE_COLUMNS: tuple[str, ...] = snap._POSTURE_SIGNAL_COLUMNS

#: Live-measured spine shape (DIAG §"Universe arithmetic"): 921 offices, prior 949.
SPINE_OFFICE_COUNT = 921
LIVE_PRIOR_COUNT = 949
SHRINK_GUARD_MAX_RATIO = 0.500


def _unit_holder_frame(rows: list[dict[str, Any]]) -> pl.DataFrame:
    """A UNIT_HOLDER_SCHEMA-shaped frame: base identity + the nine cf: posture columns."""
    built: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        base: dict[str, Any] = {
            "gid": row.get("gid", f"uh{i}"),
            "parent_gid": row.get("parent_gid", f"biz{i}"),
            "last_modified": row.get("last_modified", _TS),
        }
        for col in _POSTURE_COLUMNS:
            base[col] = row.get(col)
        built.append(base)
    return pl.DataFrame(
        built,
        schema={
            "gid": pl.Utf8,
            "parent_gid": pl.Utf8,
            "last_modified": pl.Datetime(time_unit="us", time_zone="UTC"),
            **{c: pl.Utf8 for c in _POSTURE_COLUMNS},
        },
    )


def _business_frame(pairs: list[tuple[str, str | None]]) -> pl.DataFrame:
    """A BUSINESS_SCHEMA-shaped identity frame: gid + company_id (the office guid)."""
    return pl.DataFrame(
        {"gid": [g for g, _ in pairs], GUID_FIELD: [c for _, c in pairs]},
        schema={"gid": pl.Utf8, GUID_FIELD: pl.Utf8},
    )


def _realistic_spine(
    office_count: int = SPINE_OFFICE_COUNT,
    *,
    enrolled_every: int = 3,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """A spine at live scale: every office has a guid; a share carry real posture.

    Mirrors the live composition -- a large ``Inactive`` majority (which still
    carries a NON-NULL custom_cal_status, hence a posture signal) plus a minority on
    the alternative providers.
    """
    uh_rows: list[dict[str, Any]] = []
    biz_pairs: list[tuple[str, str | None]] = []
    for i in range(office_count):
        biz_gid = f"biz{i}"
        biz_pairs.append((biz_gid, f"guid-{i:04d}"))
        row: dict[str, Any] = {"gid": f"uh{i}", "parent_gid": biz_gid}
        if i % enrolled_every == 0:
            row[CUSTOM_CAL_STATUS_FIELD] = "Enabled"
            row["calendly_url"] = f"https://calendly.com/office-{i}"
        else:
            row[CUSTOM_CAL_STATUS_FIELD] = "Inactive"
        uh_rows.append(row)
    return _unit_holder_frame(uh_rows), _business_frame(biz_pairs)


async def _push_bomb(_offices: list[ExtractedScheduling]) -> StratumPushResult:
    raise AssertionError("push must NEVER run on a refused snapshot")


# =============================================================================
# LEG A -- the universe is RECOVERED off the office spine
# =============================================================================


class TestLegAUniverseRecovered:
    def test_spine_projects_the_full_office_universe(self) -> None:
        """The projection yields ONE office per distinct guid, at spine scale."""
        uh, biz = _realistic_spine()
        extracted, drift = project_office_frame(uh, biz)

        assert len(extracted) == SPINE_OFFICE_COUNT
        assert len({e.guid for e in extracted}) == SPINE_OFFICE_COUNT
        assert drift == []

    def test_universe_clears_the_data_side_shrink_guard(self) -> None:
        """921 vs prior 949 => shrink ratio 0.030, well inside the 0.500 guard.

        The DIAG's decisive discriminator: an Offer-ACTIVE-scoped universe would be
        57 guids (ratio 0.940) and would be REFUSED on arrival. The universe must be
        the office spine.
        """
        uh, biz = _realistic_spine()
        extracted, _ = project_office_frame(uh, biz)

        shrink_ratio = (LIVE_PRIOR_COUNT - len(extracted)) / LIVE_PRIOR_COUNT
        assert shrink_ratio == pytest.approx(0.0295, abs=0.005)
        assert shrink_ratio < SHRINK_GUARD_MAX_RATIO

        # ... and the arithmetic floor the guard imposes on any healthy push.
        assert len(extracted) >= LIVE_PRIOR_COUNT * SHRINK_GUARD_MAX_RATIO

    def test_posture_is_populated_from_the_unit_holder_side(self) -> None:
        """Posture columns arrive from unit_holder -- far above a floor of 1."""
        uh, biz = _realistic_spine()
        joined = join_office_spine(uh, biz)

        signal_rows = posture_signal_row_count(joined)
        assert signal_rows == SPINE_OFFICE_COUNT
        # Assert a floor MATERIALLY above MIN_POSTURE_SIGNAL_ROWS so a re-collapse
        # cannot squeak past (DIAG: "assert a floor materially above 1, e.g. >= 100").
        assert signal_rows >= 100

    def test_frame_passes_the_value_floor(self) -> None:
        uh, biz = _realistic_spine()
        assert_posture_signal_floor(join_office_spine(uh, biz))  # must not raise

    def test_company_id_arrives_from_the_business_ancestor(self) -> None:
        """The guid is joined, never cascaded -- parent_gid -> business.gid."""
        uh = _unit_holder_frame(
            [{"gid": "uh1", "parent_gid": "bizA", CUSTOM_CAL_STATUS_FIELD: "Enabled"}]
        )
        biz = _business_frame([("bizA", "241355e3-ad2b-4efb-8935-cf44f311a3a1")])

        extracted, _ = project_office_frame(uh, biz)
        assert [e.guid for e in extracted] == ["241355e3-ad2b-4efb-8935-cf44f311a3a1"]

    def test_guidless_office_drops_and_fails_safe_by_absence(self) -> None:
        """A business with no Company ID yields a null guid -> DROPPED, not fabricated.

        DIAG CARD WS-B/3: 9 of 71 active offices are in this state today. They are
        enrollment-invisible by design rather than given a fabricated identity.
        """
        uh = _unit_holder_frame(
            [
                {"gid": "uh1", "parent_gid": "bizA", CUSTOM_CAL_STATUS_FIELD: "Enabled"},
                {"gid": "uh2", "parent_gid": "bizB", CUSTOM_CAL_STATUS_FIELD: "Enabled"},
            ]
        )
        biz = _business_frame([("bizA", "guid-A"), ("bizB", None)])

        extracted, _ = project_office_frame(uh, biz)
        assert [e.guid for e in extracted] == ["guid-A"]

    def test_de_enrolled_offices_stay_in_the_universe(self) -> None:
        """wire-v2 HARD CONSTRAINT: an Inactive office remains PRESENT in the snapshot.

        This is what the office-spine universe preserves and an active-offer scoping
        would destroy.
        """
        uh = _unit_holder_frame(
            [
                {"gid": "uh1", "parent_gid": "bizA", CUSTOM_CAL_STATUS_FIELD: "Enabled"},
                {"gid": "uh2", "parent_gid": "bizB", CUSTOM_CAL_STATUS_FIELD: "Inactive"},
            ]
        )
        biz = _business_frame([("bizA", "guid-A"), ("bizB", "guid-B")])

        extracted, _ = project_office_frame(uh, biz)
        assert {e.guid for e in extracted} == {"guid-A", "guid-B"}

    def test_multi_unit_holder_guid_collapses_to_one_representative(self) -> None:
        """36 guids carry >1 unit_holder (max 19); the representative rule transfers."""
        uh = _unit_holder_frame(
            [
                {
                    "gid": "uh-old",
                    "parent_gid": "bizA",
                    "last_modified": dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
                    CUSTOM_CAL_STATUS_FIELD: "Inactive",
                },
                {
                    "gid": "uh-new",
                    "parent_gid": "bizA",
                    "last_modified": dt.datetime(2026, 6, 1, tzinfo=dt.UTC),
                    CUSTOM_CAL_STATUS_FIELD: "Enabled",
                    "calendly_url": "https://calendly.com/winner",
                },
            ]
        )
        biz = _business_frame([("bizA", "guid-A")])

        extracted, drift = project_office_frame(uh, biz)
        assert len(extracted) == 1
        assert extracted[0].guid == "guid-A"
        # max(last_modified) wins, and status+destination come from the SAME row.
        assert extracted[0].normalized_inputs["calendly_url"] == "https://calendly.com/winner"
        assert drift == ["guid-A"]  # the disagreement is metered, not silenced

    def test_the_offer_frame_is_never_read(self) -> None:
        """Structural: the producer's source constants name the spine, not the offer."""
        assert snap.SNAPSHOT_UNIT_HOLDER_ENTITY_TYPE == "unit_holder"
        assert snap.SNAPSHOT_BUSINESS_ENTITY_TYPE == "business"
        assert not hasattr(snap, "SNAPSHOT_OFFER_ENTITY_TYPE")


# =============================================================================
# LEG B -- the UNCHANGED guards still BITE (deliberately-broken fixtures)
# =============================================================================


class TestLegBGuardsStillBite:
    # --- Fixture 1: value floor ------------------------------------------------

    def test_b1_all_null_posture_universe_is_refused_by_the_value_floor(self) -> None:
        """BROKEN INPUT: a full, non-empty guid universe with EVERY posture null.

        Faithful replay of the observed era-2 signature
        ("degenerate posture source (value floor): 0/N"). The office SET gate passes
        (company_id resolves fine); only the VALUE floor catches it.
        """
        uh = _unit_holder_frame([{"gid": f"uh{i}", "parent_gid": f"biz{i}"} for i in range(50)])
        biz = _business_frame([(f"biz{i}", f"guid-{i}") for i in range(50)])
        joined = join_office_spine(uh, biz)

        assert joined.height == 50  # universe is FULL, not empty
        assert posture_signal_row_count(joined) == 0

        with pytest.raises(SnapshotRefusedError, match="degenerate posture source"):
            assert_posture_signal_floor(joined)

    def test_b1_healthy_variant_passes_the_same_code_path(self) -> None:
        """PAIRED HEALTHY: one non-null custom_cal_status clears the floor."""
        rows: list[dict[str, Any]] = [{"gid": f"uh{i}", "parent_gid": f"biz{i}"} for i in range(50)]
        rows[0][CUSTOM_CAL_STATUS_FIELD] = "Enabled"
        joined = join_office_spine(
            _unit_holder_frame(rows),
            _business_frame([(f"biz{i}", f"guid-{i}") for i in range(50)]),
        )

        assert posture_signal_row_count(joined) == 1
        assert_posture_signal_floor(joined)  # must NOT raise

    # --- Fixture 2: completeness contract --------------------------------------

    def test_b2_all_guidless_universe_is_refused_as_empty(self) -> None:
        """BROKEN INPUT: every company_id null -> empty universe.

        Replays era-1 verbatim ("refused: empty active-office set"). An empty batch
        fed to the whole-source DELETE would wipe every live office.
        """
        uh = _unit_holder_frame(
            [
                {"gid": f"uh{i}", "parent_gid": f"biz{i}", CUSTOM_CAL_STATUS_FIELD: "Enabled"}
                for i in range(30)
            ]
        )
        biz = _business_frame([(f"biz{i}", None) for i in range(30)])

        extracted, _ = project_office_frame(uh, biz)
        assert extracted == []

        with pytest.raises(SnapshotRefusedError, match="empty active-office set"):
            assert_complete_office_set([o.guid for o in extracted], source_complete=True)

    async def test_b2_end_to_end_refuses_and_never_pushes(self) -> None:
        """The empty universe drives a ``refused`` run -- push is NEVER invoked."""
        uh = _unit_holder_frame(
            [{"gid": "uh0", "parent_gid": "biz0", CUSTOM_CAL_STATUS_FIELD: "Enabled"}]
        )
        biz = _business_frame([("biz0", None)])

        async def _enumerate() -> tuple[list[ExtractedScheduling], bool]:
            extracted, _ = project_office_frame(uh, biz)
            return extracted, True

        result = await execute_snapshot_push(
            gate=lambda: True, enumerate_offices=_enumerate, push=_push_bomb
        )
        assert result.status == "refused"
        assert result.entry_count == 0

    def test_b2_healthy_variant_passes_the_same_code_path(self) -> None:
        uh = _unit_holder_frame(
            [
                {"gid": f"uh{i}", "parent_gid": f"biz{i}", CUSTOM_CAL_STATUS_FIELD: "Enabled"}
                for i in range(30)
            ]
        )
        biz = _business_frame([(f"biz{i}", f"guid-{i}") for i in range(30)])

        extracted, _ = project_office_frame(uh, biz)
        gids = assert_complete_office_set([o.guid for o in extracted], source_complete=True)
        assert len(gids) == 30

    # --- Fixture 3: shrink guard (data-side contract) ---------------------------

    def test_b3_collapsed_universe_would_trip_the_shrink_guard(self) -> None:
        """BROKEN INPUT: a 5-office universe against prior_count=949.

        The data side refuses this with HTTP 422 SNAPSHOT_SHRINK_GUARD_TRIPPED. This
        asserts the guard remains REACHABLE -- a cure that made the shrink guard
        unreachable would have removed a safety, not passed a test. Mirrors the 15/15
        observed 422s (ratio 0.954-0.995 vs max 0.500).
        """
        uh = _unit_holder_frame(
            [
                {"gid": f"uh{i}", "parent_gid": f"biz{i}", CUSTOM_CAL_STATUS_FIELD: "Enabled"}
                for i in range(5)
            ]
        )
        biz = _business_frame([(f"biz{i}", f"guid-{i}") for i in range(5)])

        extracted, _ = project_office_frame(uh, biz)
        shrink_ratio = (LIVE_PRIOR_COUNT - len(extracted)) / LIVE_PRIOR_COUNT

        assert len(extracted) == 5
        assert shrink_ratio == pytest.approx(0.9947, abs=0.001)
        assert shrink_ratio > SHRINK_GUARD_MAX_RATIO, "shrink guard must still TRIP"

    def test_b3_healthy_spine_does_not_trip_the_shrink_guard(self) -> None:
        """PAIRED HEALTHY: the full 921-office spine passes the same arithmetic."""
        uh, biz = _realistic_spine()
        extracted, _ = project_office_frame(uh, biz)
        shrink_ratio = (LIVE_PRIOR_COUNT - len(extracted)) / LIVE_PRIOR_COUNT
        assert shrink_ratio < SHRINK_GUARD_MAX_RATIO

    # --- Fixture 4: schema-lag (the PR-1-before-PR-2 safety) --------------------

    def test_b4_unit_holder_without_posture_columns_is_refused(self) -> None:
        """BROKEN INPUT: a base-columns-only unit_holder frame (PR-1 not deployed).

        This MUST fire honestly rather than fabricate a default-filled push. It is
        the exact state of the live unit_holder frame TODAY (2085 rows, base columns
        only), so shipping PR-2 before PR-1 lands+warms yields refusals, not a
        degenerate whole-source overwrite of 949 live offices.
        """
        base_only = pl.DataFrame(
            {
                "gid": ["uh1", "uh2"],
                "parent_gid": ["biz1", "biz2"],
                "last_modified": [_TS, _TS],
            }
        )
        biz = _business_frame([("biz1", "guid-1"), ("biz2", "guid-2")])

        with pytest.raises(FrameSchemaLagError, match="scheduling-posture columns"):
            join_office_spine(base_only, biz)

    def test_b4_business_frame_without_company_id_is_refused(self) -> None:
        """BROKEN INPUT: the identity side lacks company_id -> refuse, never null-fill."""
        uh, _ = _realistic_spine(office_count=5)
        biz_no_guid = pl.DataFrame({"gid": ["biz0"]}, schema={"gid": pl.Utf8})

        with pytest.raises(FrameSchemaLagError, match="office-identity columns"):
            join_office_spine(uh, biz_no_guid)

    def test_b4_unit_holder_without_join_key_is_refused(self) -> None:
        """BROKEN INPUT: no parent_gid -> the spine cannot be joined at all."""
        no_key = pl.DataFrame(
            {
                "gid": ["uh1"],
                "last_modified": [_TS],
                **{c: [None] for c in _POSTURE_COLUMNS},
            },
            schema={
                "gid": pl.Utf8,
                "last_modified": pl.Datetime(time_unit="us", time_zone="UTC"),
                **{c: pl.Utf8 for c in _POSTURE_COLUMNS},
            },
        )
        biz = _business_frame([("biz1", "guid-1")])

        with pytest.raises(FrameSchemaLagError, match="join key"):
            join_office_spine(no_key, biz)

    def test_b4_healthy_variant_passes_the_same_code_path(self) -> None:
        """PAIRED HEALTHY: a PR-1-schema unit_holder frame joins cleanly."""
        uh, biz = _realistic_spine(office_count=5)
        joined = join_office_spine(uh, biz)
        assert GUID_FIELD in joined.columns
        assert joined.get_column(GUID_FIELD).null_count() == 0
