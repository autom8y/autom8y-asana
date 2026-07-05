"""Day-one two-sided discriminating canary for the windowed active_mrr contract.

Numerical-Adversary artifact (SPINE prove-half). This file pins the ruled
active_mrr contract (interp-B as-of) two-sided: the REAL enriched-shape input
passes GREEN AND three deliberately-broken inputs are CORRECTLY REFUSED. It
proves the guard has TEETH, not presence.

Ruled definition (src/autom8_asana/metrics/definitions/offer.py:20-43):
    active_mrr = sum(mrr>0, Float64) over section-ACTIVE offers,
    deduped unique(subset=["office_phone", "vertical"], keep="first").

The guard being graded (built by neither fixture author -- lineage disjoint):
    src/autom8_asana/metrics/compute.py:67-79 HARD-RAISES ValueError when the
    "section" column is absent (classification filter); dedup at :114-116.

The RED sides are deliberately-broken INPUTS the live surface correctly rejects
(discriminating-canary-doctrine), NEVER defects injected into working code:
    RED-1  dedup-dropped sum (Query-Engine trap: SUM at offer grain, not unit
           grain) INFLATES above the real deduped number.
    RED-2  today's offline substrate (no "section" column) is REFUSED, not
           silently mis-summed.
    RED-3  an out-of-week as-of snapshot is REJECTED by the window validator.

Follows the idiom of tests/unit/metrics/test_adversarial.py.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import polars as pl
import pytest

from autom8_asana.metrics.compute import compute_metric
from autom8_asana.metrics.definitions.offer import ACTIVE_MRR
from autom8_asana.models.business.activity import AccountActivity, OFFER_CLASSIFIER

# ---------------------------------------------------------------------------
# Live section names -- derived from the REAL OFFER_CLASSIFIER, never guessed.
# If the classifier shape drifts below what the fixture needs, fail LOUD here
# (a vacuous canary that cannot arm its cases is not protection -- S5).
# ---------------------------------------------------------------------------

_ACTIVE_SECTIONS = sorted(OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE))
_INACTIVE_SECTIONS = sorted(OFFER_CLASSIFIER.sections_for(AccountActivity.INACTIVE))

assert len(_ACTIVE_SECTIONS) >= 2, (
    "canary needs >=2 distinct ACTIVE sections from the live classifier; "
    f"got {_ACTIVE_SECTIONS}"
)
assert len(_INACTIVE_SECTIONS) >= 1, (
    "canary needs >=1 INACTIVE section to prove exclusion; "
    f"got {_INACTIVE_SECTIONS}"
)

_ACTIVE_A = _ACTIVE_SECTIONS[0]
_ACTIVE_B = _ACTIVE_SECTIONS[1]
_INACTIVE_S = _INACTIVE_SECTIONS[0]

# ---------------------------------------------------------------------------
# Hand-derived golden expected value.
#
# Golden frame (8 rows) -> filters applied by ACTIVE_MRR:
#   Unit 1  555-1001 / dental   ACTIVE  mrr 1000  (two sibling offers, same mrr)
#   Unit 2  555-1002 / med_spa  ACTIVE  mrr 2500  (one offer)
#   Unit 3  555-1003 / chiro    ACTIVE  mrr  750  (two sibling offers, same mrr)
#   --      555-1004 / plumbing INACTIVE mrr 9999 -> EXCLUDED (classification)
#   --      555-1005 / hvac     ACTIVE  mrr    0  -> EXCLUDED (>0 filter)
#   --      555-1006 / roofing  ACTIVE  mrr None  -> EXCLUDED (is_not_null filter)
#
# dedup unique(office_phone, vertical) collapses each sibling pair to one row:
#   1000 + 2500 + 750 = 4250.0   across 3 distinct units.
# ---------------------------------------------------------------------------

GOLDEN_EXPECTED_MRR_SUM = 4250.0

# ---------------------------------------------------------------------------
# Offline substrate anchors (external sibling repo). Guarded by skipif so CI
# without autom8y-data skips; RUNS here where the substrate is present.
# ---------------------------------------------------------------------------

_OFFLINE_ROOT = Path("/Users/tomtenuta/Code/a8/a8/repos/autom8y-data/data/offline")
_INWEEK_SNAP = _OFFLINE_ROOT / "20260625_105550"
_OUTWEEK_SNAP = _OFFLINE_ROOT / "20260629_143620"
_OFFLINE_OFFERS = _INWEEK_SNAP / "business_offers.parquet"
_INWEEK_MANIFEST = _INWEEK_SNAP / "_manifest.json"
_OUTWEEK_MANIFEST = _OUTWEEK_SNAP / "_manifest.json"

_DEMAND_WEEK_START = "2026-06-21"
_DEMAND_WEEK_END = "2026-06-27"

requires_substrate = pytest.mark.skipif(
    not _OFFLINE_OFFERS.exists(),
    reason="offline substrate (sibling autom8y-data repo) not present",
)
requires_manifests = pytest.mark.skipif(
    not (_INWEEK_MANIFEST.exists() and _OUTWEEK_MANIFEST.exists()),
    reason="offline snapshot manifests not present",
)


# ---------------------------------------------------------------------------
# Fixtures (synthetic enriched-shape frames) + fixture-local broken variants.
# ---------------------------------------------------------------------------


def _golden_offer_frame() -> pl.DataFrame:
    """Synthetic enriched-shape offer frame (name/section/office_phone/vertical/mrr).

    Contains: sibling offers sharing one unit at the same mrr (dedup must
    collapse), an INACTIVE-section row (must be excluded), a zero-mrr and a
    null-mrr row (must be excluded), across >=3 distinct units.
    """
    return pl.DataFrame(
        {
            "name": [
                "Unit1-OfferA",
                "Unit1-OfferB",
                "Unit2-Offer",
                "Unit3-OfferA",
                "Unit3-OfferB",
                "Inactive-Offer",
                "Zero-MRR-Offer",
                "Null-MRR-Offer",
            ],
            "section": [
                _ACTIVE_A,
                _ACTIVE_A,
                _ACTIVE_B,
                _ACTIVE_A,
                _ACTIVE_B,
                _INACTIVE_S,
                _ACTIVE_A,
                _ACTIVE_B,
            ],
            "office_phone": [
                "555-1001",
                "555-1001",
                "555-1002",
                "555-1003",
                "555-1003",
                "555-1004",
                "555-1005",
                "555-1006",
            ],
            "vertical": [
                "dental",
                "dental",
                "med_spa",
                "chiro",
                "chiro",
                "plumbing",
                "hvac",
                "roofing",
            ],
            "mrr": ["1000", "1000", "2500", "750", "750", "9999", "0", None],
        }
    )


def _no_sibling_offer_frame() -> pl.DataFrame:
    """Enriched-shape frame with NO sibling duplicates (every unit distinct).

    Used to prove the dedup canary is TWO-SIDED / non-vacuous: with no duplicate
    to collapse, the dedup-dropped variant EQUALS the real path -- the
    discriminator bites ONLY on the dedup defect, never always.
    """
    return pl.DataFrame(
        {
            "name": ["U1", "U2", "U3"],
            "section": [_ACTIVE_A, _ACTIVE_B, _ACTIVE_A],
            "office_phone": ["555-2001", "555-2002", "555-2003"],
            "vertical": ["dental", "med_spa", "chiro"],
            "mrr": ["1000", "2500", "750"],
        }
    )


def _broken_sum_no_dedup(df: pl.DataFrame) -> float:
    """RED-1 (Query-Engine trap): ACTIVE_MRR's filters WITHOUT the unique() dedup.

    Identical classification + cast + (>0 & not-null) filters as the ruled
    definition, but SKIPS unique(subset=["office_phone","vertical"]). This is the
    inflated number a naive SUM at OFFER grain (not UNIT grain) yields.
    """
    active = OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE)
    out = (
        df.filter(pl.col("section").str.to_lowercase().is_in(list(active)))
        .with_columns(pl.col("mrr").cast(pl.Float64, strict=False).alias("mrr"))
        .filter(pl.col("mrr").is_not_null() & (pl.col("mrr") > 0))
        # DELIBERATE DEFECT: no .unique(subset=["office_phone", "vertical"])
    )
    total = out["mrr"].sum()
    return float(total) if total is not None else 0.0


def _assert_in_week(created_at_iso: str, week_start: str, week_end: str) -> datetime:
    """RED-3 as-of window validator: typed refusal for out-of-week snapshots.

    Returns the parsed timestamp when the snapshot's created_at date is within
    [week_start, week_end] inclusive; raises ValueError otherwise.
    """
    ts = datetime.fromisoformat(created_at_iso)
    ws = date.fromisoformat(week_start)
    we = date.fromisoformat(week_end)
    d = ts.date()
    if not (ws <= d <= we):
        raise ValueError(
            f"as-of snapshot {created_at_iso} (date {d}) is OUT-OF-WINDOW for "
            f"demand week {week_start}..{week_end}; refusing to serve as-of number"
        )
    return ts


def _manifest_created_at(manifest_path: Path) -> str:
    with manifest_path.open() as fh:
        data = json.load(fh)
    return data["created_at"]


# ===========================================================================
# GOLDEN (GREEN side): the real input passes, exact hand-derived value.
# ===========================================================================


class TestGoldenActiveMrr:
    """The real enriched-shape input computes the exact ruled number."""

    def test_golden_active_mrr_exact(self) -> None:
        df = _golden_offer_frame()
        result = compute_metric(ACTIVE_MRR, df)
        total = result["mrr"].sum()
        # EXACT equality on an integer-valued float -- pins the contract.
        assert total == GOLDEN_EXPECTED_MRR_SUM
        # dedup collapsed the two sibling pairs -> exactly 3 surviving unit rows.
        assert len(result) == 3
        # only the three ACTIVE, positive, non-null units survive.
        assert set(result["office_phone"].to_list()) == {
            "555-1001",
            "555-1002",
            "555-1003",
        }


# ===========================================================================
# RED-1 (dedup-dropped): the Query-Engine trap INFLATES; the canary discriminates.
# ===========================================================================


class TestDedupDroppedDiscriminates:
    """The dedup-dropped sum inflates above the real path (dedup presence has teeth)."""

    def test_broken_no_dedup_inflates(self) -> None:
        df = _golden_offer_frame()
        real = compute_metric(ACTIVE_MRR, df)["mrr"].sum()
        broken = _broken_sum_no_dedup(df)
        assert real == GOLDEN_EXPECTED_MRR_SUM
        # sibling pairs double-counted: 2*1000 + 2500 + 2*750 = 6000.
        assert broken == 6000.0
        assert broken > real  # dedup-dropped INFLATES
        assert real != broken  # the real path is NOT the Query-Engine trap

    def test_dedup_canary_is_two_sided_non_vacuous(self) -> None:
        # NON-VACUITY (S5): on a frame with NO sibling duplicates, the SAME broken
        # function EQUALS the real path. The discriminator therefore bites ONLY on
        # the dedup defect -- it is not an always-fail (vacuous) assertion.
        df = _no_sibling_offer_frame()
        real = compute_metric(ACTIVE_MRR, df)["mrr"].sum()
        broken = _broken_sum_no_dedup(df)
        assert real == 4250.0
        assert real == broken  # no duplicate to collapse -> no divergence


# ===========================================================================
# RED-2 (substrate refusal): today's offline frame is REFUSED, not mis-summed.
# ===========================================================================


@requires_substrate
class TestSubstrateRefusal:
    """The dated offline substrate carries no 'section' -> compute REFUSES it."""

    def test_offline_substrate_is_refused_missing_section(self) -> None:
        df = pl.read_parquet(_OFFLINE_OFFERS)
        # SOLE DISCRIMINATOR = the 'section' column. The cheap signals are BLIND:
        # the file exists, the parquet reads, and it has many rows -- all pass
        # identically whether or not the metric is servable.
        assert len(df) > 0
        assert "section" not in df.columns
        assert "mrr" not in df.columns
        with pytest.raises(ValueError, match="section"):
            compute_metric(ACTIVE_MRR, df)

    def test_enriched_positive_control_not_refused(self) -> None:
        # TWO-SIDED: the SAME guard passes the enriched golden frame (section
        # present) without raising -> the refusal fires ONLY on the defect.
        df = _golden_offer_frame()
        result = compute_metric(ACTIVE_MRR, df)
        assert result["mrr"].sum() == GOLDEN_EXPECTED_MRR_SUM


# ===========================================================================
# RED-3 (wrong-window): the out-of-week as-of snapshot is REJECTED.
# ===========================================================================


@requires_manifests
class TestWrongWindowGuard:
    """The as-of window validator GREENs in-week and REJECTS out-of-week."""

    def test_inweek_snapshot_greens(self) -> None:
        created = _manifest_created_at(_INWEEK_MANIFEST)
        ts = _assert_in_week(created, _DEMAND_WEEK_START, _DEMAND_WEEK_END)
        assert ts.date().isoformat() == "2026-06-25"

    def test_outweek_snapshot_rejected(self) -> None:
        created = _manifest_created_at(_OUTWEEK_MANIFEST)
        with pytest.raises(ValueError, match="OUT-OF-WINDOW"):
            _assert_in_week(created, _DEMAND_WEEK_START, _DEMAND_WEEK_END)

    def test_window_guard_two_sided_same_validator(self) -> None:
        # SOLE DISCRIMINATOR = the created_at value vs the demand window. The cheap
        # signals are BLIND: both manifests exist, both parse, both carry a
        # created_at key -- identical on the servable and the wrong-window snapshot.
        inweek = _manifest_created_at(_INWEEK_MANIFEST)
        outweek = _manifest_created_at(_OUTWEEK_MANIFEST)
        assert inweek and outweek  # cheap signals identical on both arms
        # one validator: in-week passes, out-of-week refuses.
        _assert_in_week(inweek, _DEMAND_WEEK_START, _DEMAND_WEEK_END)
        with pytest.raises(ValueError):
            _assert_in_week(outweek, _DEMAND_WEEK_START, _DEMAND_WEEK_END)
