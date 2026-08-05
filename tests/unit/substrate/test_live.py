"""WU-3 live-parity arming tests (3a-3d) — DARK, offline, fakes at the HTTP boundary.

CARDINAL P10 boundary: ZERO live Asana calls. Post F-305-1 the parity is a DUAL-LEG ledger:
LEG A (gate anchor) is the SERVED-definition active_mrr (22-section classifier + dedup +
mrr>0, via the real ``compute_metric``, identical on v1/v2); LEG B (tripwire, NOT the gate)
is the 3-section raw exemplar aggregate. Discriminating, two-sided where a guard is added:
torn-read + generation-monotonicity refusal (3a), fetch-plan coverage fail-closed (§6 #2),
budget-charge-per-attempt incl. 429 (3b), first-class refusal/error on non-SWAPPED (F-305-2/3).
"""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import polars as pl
import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.models.business.activity import CLASSIFIERS, AccountActivity
from autom8_asana.substrate import live
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.live import (
    OFFER_PROJECT_GID,
    ActiveMrrColumnMissing,
    ActiveMrrRefused,
    ArmedParityWindow,
    OfferSectionPlan,
    ParityLegRefused,
    ParityReceiptWriter,
    ReusedSection,
    S3OfferPlaneReader,
    TornOfferPlaneRead,
    arm_offer_parity_window,
    arm_process_parity_fetcher,
    assert_plan_covers_active_set,
    build_parity_outbound,
    build_v1_offer_materialization,
    classifier_active_sections,
    exemplar_aggregate_value,
    guarded_v1_offer_frame,
    materialize_v1_offer_plane,
    served_active_mrr,
)
from autom8_asana.substrate.rebuild import RebuildOutcome
from tests.harness.substrate_gate.budget import ParityBudgetExhausted, PerDayBudgetLedger
from tests.harness.substrate_gate.parity import ParityObservation, reset_process_fetcher

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterator, Mapping

try:
    import boto3
    from moto import mock_aws

    MOTO_AVAILABLE = True
except ImportError:  # pragma: no cover - moto is a dev dep; guard mirrors the house pattern
    MOTO_AVAILABLE = False

_FIXTURE_DIR = (
    Path(__file__).resolve().parents[2] / "harness/substrate_gate/fixtures/offer_1143843662099250"
)
_V2_BUCKET = "substrate-v2-live-test"
_DAY = datetime(2026, 8, 4, 18, 0, tzinfo=UTC)
_BUILT = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)


def _fixed_clock() -> Callable[[], datetime]:
    return lambda: _DAY


def _aid() -> ArtifactId:
    return ArtifactId(project_gid=OFFER_PROJECT_GID, entity_type=EntityType.OFFER)


def _all_active_covered() -> frozenset[str]:
    """The full classifier active set as covered names — a coverage-clean plan (§6 #2)."""
    return classifier_active_sections()


def _fixture_bytes() -> tuple[bytes, bytes]:
    return (
        (_FIXTURE_DIR / "offer_plane_section_mrr.parquet").read_bytes(),
        (_FIXTURE_DIR / "watermark.json").read_bytes(),
    )


def _offer_row(
    section: str, *, offer_id: str, mrr: float, office_phone: str = "p", vertical: str = "v"
) -> dict[str, Any]:
    """A value-complete + served-complete offer row (4 value cols + section + dedup keys)."""
    return {
        "section": section,
        "offer_id": offer_id,
        "cost": 100.0,
        "mrr": mrr,
        "weekly_ad_spend": 10.0,
        "office_phone": office_phone,
        "vertical": vertical,
    }


def _synth_v1_bytes(
    rows: list[dict[str, Any]], *, project_gid: str = OFFER_PROJECT_GID, built: datetime = _BUILT
) -> tuple[bytes, bytes]:
    """Synthesize a full-column v1 offer plane (parquet + consistent watermark) — PII stays local."""
    frame = pl.DataFrame(rows)
    buf = io.BytesIO()
    frame.write_parquet(buf)
    watermark = {
        "project_gid": project_gid,
        "watermark": built.isoformat(),
        "saved_at": built.replace(second=30).isoformat(),
        "row_count": frame.height,
    }
    return buf.getvalue(), json.dumps(watermark).encode("utf-8")


def _ledger(tmp_path: Path, *, cap: int = 100) -> PerDayBudgetLedger:
    return PerDayBudgetLedger(path=tmp_path / "budget.json", cap=cap, clock=_fixed_clock())


class _FastClock:
    def __init__(self) -> None:
        self._t = 0.0

    def __call__(self) -> float:
        self._t += 1000.0
        return self._t


async def _no_sleep(_seconds: float) -> None:
    return None


class _Fake429(Exception):
    """A 429-signalling boundary error (status_code=429; non-Autom8Error; classifier-safe fast-fail)."""

    status_code = 429


class _FakePageFetch:
    """Offline HTTP boundary: canned pages per section; optional 429 per section."""

    def __init__(
        self,
        pages_by_section: Mapping[str, list[list[dict[str, Any]]]],
        *,
        raise_429_on: tuple[str, ...] = (),
    ) -> None:
        self._pages = pages_by_section
        self._raise_429_on = set(raise_429_on)
        self.calls: list[tuple[str, str | None]] = []

    async def __call__(
        self, _aid: ArtifactId, section_gid: str, cursor: str | None
    ) -> tuple[list[dict[str, Any]], str | None]:
        self.calls.append((section_gid, cursor))
        if section_gid in self._raise_429_on:
            raise _Fake429(f"429 on {section_gid}")
        pages = self._pages[section_gid]
        idx = 0 if cursor is None else int(cursor)
        next_cursor = str(idx + 1) if idx + 1 < len(pages) else None
        return pages[idx], next_cursor


def _plan(
    refetch: tuple[str, ...],
    *,
    reuse: Mapping[str, ReusedSection] | None = None,
    covered: frozenset[str] | None = None,
) -> Callable[[ArtifactId], Awaitable[OfferSectionPlan]]:
    covered_names = covered if covered is not None else _all_active_covered()

    async def _fn(_aid: ArtifactId) -> OfferSectionPlan:
        return OfferSectionPlan(
            refetch=refetch, reuse=dict(reuse or {}), covered_section_names=covered_names
        )

    return _fn


def _fetcher(
    tmp_path: Path,
    *,
    page_fetch: _FakePageFetch,
    plan: Callable[[ArtifactId], Awaitable[OfferSectionPlan]],
    ledger: PerDayBudgetLedger | None = None,
) -> live.PacedOfferSectionFetcher:
    return live.PacedOfferSectionFetcher(
        page_fetch=page_fetch,
        plan=plan,
        budget=ledger if ledger is not None else _ledger(tmp_path),
        now=lambda: _DAY,
        gate_clock=_FastClock(),
        gate_sleep=_no_sleep,
    )


# ===========================================================================
# served-definition (LEG A) + fetch-plan coverage (§6 #1/#2/#3/#7)
# ===========================================================================


def test_served_active_mrr_dedups_and_filters() -> None:
    """LEG A = the real served metric: 22-section classifier + dedup(phone,vertical) + mrr>0."""
    frame = pl.DataFrame(
        [
            _offer_row("ACTIVE", offer_id="a", mrr=100.0, office_phone="p1", vertical="v1"),
            _offer_row("ACTIVE", offer_id="b", mrr=100.0, office_phone="p1", vertical="v1"),  # dup
            _offer_row("STAGED", offer_id="c", mrr=50.0, office_phone="p2", vertical="v2"),
            _offer_row("ACTIVE", offer_id="d", mrr=0.0, office_phone="p3", vertical="v3"),  # mrr=0
            _offer_row(
                "COMPLETE", offer_id="e", mrr=999.0, office_phone="p9", vertical="v9"
            ),  # inactive
        ]
    )
    active_mrr, deduped_rows = served_active_mrr(frame)
    assert active_mrr == 150.0  # 100 (p1/v1 kept once) + 50 (p2/v2); d filtered, e not active
    assert deduped_rows == 2
    # LEG B on the SAME frame differs (raw, no dedup/filter) — distinct instruments
    assert exemplar_aggregate_value(frame)[0] == 250.0  # ACTIVE 100+100+0 raw + STAGED 50


def test_served_active_mrr_reports_missing_column() -> None:
    """A missing dedup-key column is a FINDING (ActiveMrrColumnMissing), never a silent partial."""
    frame = pl.DataFrame({"section": ["ACTIVE"], "mrr": [100.0]})  # PII-safe projection shape
    with pytest.raises(ActiveMrrColumnMissing, match="office_phone"):
        served_active_mrr(frame)


def test_classifier_active_set_is_sourced_not_hardcoded() -> None:
    """§6 #1: the active set comes FROM THE CLASSIFIER (22 sections), not a hardcoded list."""
    active = classifier_active_sections()
    assert active == frozenset(CLASSIFIERS["offer"].sections_for(AccountActivity("active")))
    assert len(active) == 22


def test_coverage_assertion_two_sided() -> None:
    """§6 #2 fail-closed: full coverage passes; a plan missing one active section REFUSES."""
    assert_plan_covers_active_set(_all_active_covered())  # superset -> OK
    missing_one = frozenset(list(_all_active_covered())[:-1])  # drop one active section
    with pytest.raises(ActiveMrrRefused, match="omits"):
        assert_plan_covers_active_set(missing_one)


def test_coverage_follows_classifier_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    """§6 #1 proof-of-no-hardcode: mutate the active set -> the coverage assertion PROPAGATES."""
    monkeypatch.setattr(live, "classifier_active_sections", lambda: frozenset({"mutated-only"}))
    with pytest.raises(ActiveMrrRefused, match="mutated-only"):
        assert_plan_covers_active_set(frozenset())  # the mutated section is now the requirement
    assert_plan_covers_active_set(frozenset({"mutated-only"}))  # covering it passes


# ===========================================================================
# 3a — torn-read guard (leg-agnostic) + LEG A/B materialization + F-305-4
# ===========================================================================


def test_3a_torn_read_row_count_mismatch_refuses() -> None:
    """Two-sided: the consistent fixture set guards clean; a tampered row_count is REFUSED loud."""
    parquet, watermark = _fixture_bytes()
    frame, built = guarded_v1_offer_frame(parquet, watermark)  # consistent -> OK
    assert frame.height == 4191 and built is not None

    torn = json.loads(watermark)
    torn["row_count"] = torn["row_count"] + 1
    with pytest.raises(TornOfferPlaneRead, match="row count"):
        guarded_v1_offer_frame(parquet, json.dumps(torn).encode("utf-8"))


def test_3a_build_after_save_and_wrong_project_refuse() -> None:
    parquet, watermark = _fixture_bytes()
    late = json.loads(watermark)
    late["watermark"] = "2026-09-01T00:00:00+00:00"  # after saved_at
    with pytest.raises(TornOfferPlaneRead, match="post-dates"):
        guarded_v1_offer_frame(parquet, json.dumps(late).encode("utf-8"))

    wrong = json.loads(watermark)
    wrong["project_gid"] = "9999999999999999"
    with pytest.raises(TornOfferPlaneRead, match="not the same plane"):
        guarded_v1_offer_frame(parquet, json.dumps(wrong).encode("utf-8"))


def test_3a_generation_monotonicity_guard_two_sided() -> None:
    """§F-305-4: an equal-rowcount generation SWAP (build instant regressed) is REFUSED."""
    parquet, watermark = _synth_v1_bytes(
        [_offer_row("ACTIVE", offer_id="a", mrr=1.0, office_phone="p1", vertical="v1")],
        built=_BUILT,
    )
    guarded_v1_offer_frame(parquet, watermark, min_build_instant=_BUILT)  # equal-or-after -> OK
    with pytest.raises(TornOfferPlaneRead, match="regressed below"):
        guarded_v1_offer_frame(parquet, watermark, min_build_instant=_BUILT.replace(day=5))


def test_3a_leg_b_exemplar_aggregate_from_fixture() -> None:
    """LEG B (tripwire): the 3-section raw exemplar aggregate on the re-pinned fixture = $75,985."""
    parquet, _ = _fixture_bytes()
    frame = pl.read_parquet(parquet)
    value, cells = exemplar_aggregate_value(frame)
    assert value == 75_985.0  # F-305-5: the leg-2 re-pin generation ($75,985), not $80,985
    assert set(cells) == {"ACTIVE", "OPTIMIZE - Human Review", "STAGED"}


def test_3a_leg_a_materialization_from_full_frame() -> None:
    """materialize_v1_offer_plane computes the SERVED number (LEG A) from a full-column frame."""
    parquet, watermark = _synth_v1_bytes(
        [
            _offer_row("ACTIVE", offer_id="a", mrr=100.0, office_phone="p1", vertical="v1"),
            _offer_row("ACTIVE", offer_id="b", mrr=100.0, office_phone="p1", vertical="v1"),
            _offer_row("STAGED", offer_id="c", mrr=50.0, office_phone="p2", vertical="v2"),
        ]
    )
    mat = materialize_v1_offer_plane(parquet, watermark)
    assert mat.plane == "v1/offer"
    assert mat.served_value == 150.0  # served definition, NOT the raw 250
    assert mat.frame_digest == mat.proof.content_digest  # coherent, not corrupt


def test_3a_leg_a_on_pii_safe_fixture_reports_missing() -> None:
    """The PII-safe fixture (section, mrr) cannot compute LEG A — reported, not papered over."""
    parquet, watermark = _fixture_bytes()
    with pytest.raises(ActiveMrrColumnMissing):
        materialize_v1_offer_plane(parquet, watermark)


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
def test_3a_s3_reader_reads_and_materializes_served() -> None:
    """S3-read-only reader (moto): GETs the v1 plane and computes LEG A (no Asana)."""
    parquet, watermark = _synth_v1_bytes(
        [_offer_row("ACTIVE", offer_id="a", mrr=500.0, office_phone="p1", vertical="v1")]
    )
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="autom8-s3")
        key = f"dataframes/{OFFER_PROJECT_GID}/offer"
        client.put_object(Bucket="autom8-s3", Key=f"{key}/dataframe.parquet", Body=parquet)
        client.put_object(Bucket="autom8-s3", Key=f"{key}/watermark.json", Body=watermark)
        reader = S3OfferPlaneReader(bucket="autom8-s3", client=client)
        mat = build_v1_offer_materialization(reader)
    assert mat.served_value == 500.0


# ===========================================================================
# 3b — paced fetcher: budget per HTTP attempt; §6 #2 coverage fail-closed
# ===========================================================================


async def test_3b_clean_multipage_charges_once_per_page(tmp_path: Path) -> None:
    pages = {
        "S1": [
            [_offer_row("ACTIVE", offer_id="a", mrr=1.0)],
            [_offer_row("ACTIVE", offer_id="b", mrr=2.0)],
        ]
    }
    ledger = _ledger(tmp_path)
    fetcher = _fetcher(
        tmp_path, page_fetch=_FakePageFetch(pages), plan=_plan(("S1",)), ledger=ledger
    )
    fetched = await fetcher.fetch(_aid())
    assert fetched.telemetry is not None
    assert fetched.telemetry.requests_issued == 2
    assert ledger.count_today() == 2  # count == boundary attempts
    assert fetched.frame.height == 2


async def test_3b_429_attempt_still_charges(tmp_path: Path) -> None:
    """Two-sided invariant: a 429'd attempt charges exactly like a success (count == requests)."""
    pages = {"S1": [[_offer_row("ACTIVE", offer_id="a", mrr=1.0)]]}
    ledger = _ledger(tmp_path)
    fetcher = _fetcher(
        tmp_path,
        page_fetch=_FakePageFetch(pages, raise_429_on=("S1",)),
        plan=_plan(("S1",)),
        ledger=ledger,
    )
    fetched = await fetcher.fetch(_aid())
    assert fetched.telemetry is not None
    assert fetched.telemetry.http_429_count >= 1
    assert ledger.count_today() == fetched.telemetry.requests_issued  # the 429 charged
    assert "S1" in fetched.failed_sections
    assert fetcher._semaphore.get_stats()["decrease_count"] >= 1  # AIMD shrank on the 429


async def test_3b_reused_section_never_charges(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    reuse = {
        "S_reuse": ReusedSection(
            instant=_BUILT, rows=(_offer_row("STAGED", offer_id="r", mrr=9.0),)
        )
    }
    fetcher = _fetcher(
        tmp_path, page_fetch=_FakePageFetch({}), plan=_plan((), reuse=reuse), ledger=ledger
    )
    fetched = await fetcher.fetch(_aid())
    assert ledger.count_today() == 0
    assert fetched.telemetry is not None
    assert fetched.telemetry.sections_reused == 1 and fetched.telemetry.requests_issued == 0
    assert fetched.frame.height == 1


async def test_3b_frame_uses_explicit_schema_not_bare_inference(tmp_path: Path) -> None:
    """The v2 leg builds its frame with EXPLICIT OFFER_SCHEMA dtypes, never bare inference.

    Regression for the 2026-08-05 first-sweep exit-30: a ``office_phone`` Utf8 cascade column
    was null for more than polars' ``infer_schema_length`` rows, then a late row carried a string
    custom-field value ("COvGsYz26fe7oVUjzYLP") — bare ``pl.DataFrame(rows)`` inferred a Null
    builder and raised ``ComputeError: could not append value ... of type: str to the builder``
    (receipt offer-1143843662099250-091945246412-ec83614f.json). Two-sided: this fixture is RED
    (ComputeError in ``fetch``) on bare inference and GREEN with ``safe_dataframe_construct`` +
    ``OFFER_SCHEMA``. Also pins v1/v2 dtype identity for the LEG A compare (§6 #3-7).
    """
    # 120 (> default infer_schema_length 100) rows with a null office_phone, then one carrying
    # the real string — reproduces the exact prod row shape at zero live cost.
    null_run = [{**_offer_row("ACTIVE", offer_id=str(i), mrr=1.0), "office_phone": None} for i in range(120)]
    late_string = _offer_row("ACTIVE", offer_id="late", mrr=1.0, office_phone="COvGsYz26fe7oVUjzYLP")
    pages = {"ACTIVE": [null_run + [late_string]]}
    ledger = _ledger(tmp_path)
    fetcher = _fetcher(
        tmp_path, page_fetch=_FakePageFetch(pages), plan=_plan(("ACTIVE",)), ledger=ledger
    )
    fetched = await fetcher.fetch(_aid())  # RED without the fix: ComputeError raised here
    assert fetched.frame.height == 121
    assert fetched.frame.schema["office_phone"] == pl.String  # explicit dtype, not inferred Null
    assert "COvGsYz26fe7oVUjzYLP" in fetched.frame["office_phone"].to_list()


async def test_3b_coverage_refusal_before_any_charge(tmp_path: Path) -> None:
    """§6 #2 keystone: a plan omitting an active section REFUSES BEFORE spending any budget."""
    pages = {"S1": [[_offer_row("ACTIVE", offer_id="a", mrr=1.0)]]}
    ledger = _ledger(tmp_path)
    incomplete = frozenset(list(_all_active_covered())[:-1])  # missing one active section
    fetcher = _fetcher(
        tmp_path,
        page_fetch=_FakePageFetch(pages),
        plan=_plan(("S1",), covered=incomplete),
        ledger=ledger,
    )
    with pytest.raises(ActiveMrrRefused):
        await fetcher.fetch(_aid())
    assert ledger.count_today() == 0  # fail-closed BEFORE the fetch — no wasted charge


async def test_3b_budget_exhaustion_halts_and_propagates(tmp_path: Path) -> None:
    pages = {
        "S1": [[_offer_row("ACTIVE", offer_id="a", mrr=1.0)]],
        "S2": [[_offer_row("ACTIVE", offer_id="b", mrr=2.0)]],
    }
    ledger = _ledger(tmp_path, cap=1)
    fetcher = _fetcher(
        tmp_path, page_fetch=_FakePageFetch(pages), plan=_plan(("S1", "S2")), ledger=ledger
    )
    with pytest.raises(ParityBudgetExhausted):
        await fetcher.fetch(_aid())


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
async def test_3b_rebuild_caller_swaps_with_telemetry(tmp_path: Path) -> None:
    pages = {"ACTIVE": [[_offer_row("ACTIVE", offer_id="a", mrr=100.0)]]}
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_V2_BUCKET)
        from autom8_asana.substrate.store import S3ArtifactStore

        store = S3ArtifactStore(_V2_BUCKET, client=client)
        ledger = _ledger(tmp_path)
        fetcher = _fetcher(
            tmp_path, page_fetch=_FakePageFetch(pages), plan=_plan(("ACTIVE",)), ledger=ledger
        )
        result, fetched = await live.rebuild_offer_v2(
            _aid(), fetcher=fetcher, store=store, now=lambda: _DAY, sla_for=lambda _e: 3600
        )
    assert result.outcome is RebuildOutcome.SWAPPED
    assert result.telemetry is not None and result.telemetry.requests_issued == 1
    assert fetched is not None and fetched.frame.height == 1


# ===========================================================================
# 3c — the dual-leg outbound: served / first-class refusal / error (F-305-1/2/3)
# ===========================================================================


@pytest.fixture
def _reset_singleton() -> Iterator[None]:
    reset_process_fetcher()
    yield
    reset_process_fetcher()


def _seed_v1(client: Any, rows: list[dict[str, Any]]) -> None:
    parquet, watermark = _synth_v1_bytes(rows)
    key = f"dataframes/{OFFER_PROJECT_GID}/offer"
    client.put_object(Bucket="autom8-s3", Key=f"{key}/dataframe.parquet", Body=parquet)
    client.put_object(Bucket="autom8-s3", Key=f"{key}/watermark.json", Body=watermark)


def _outbound_env(
    client: Any,
    tmp_path: Path,
    *,
    pages: Mapping[str, Any],
    refetch: tuple[str, ...],
    cap: int = 100,
    raise_429_on: tuple[str, ...] = (),
    covered: frozenset[str] | None = None,
) -> tuple[Callable[[ArtifactId], Awaitable[ParityObservation]], PerDayBudgetLedger, Path]:
    from autom8_asana.substrate.store import S3ArtifactStore

    store = S3ArtifactStore(_V2_BUCKET, client=client)
    ledger = _ledger(tmp_path, cap=cap)
    fetcher = _fetcher(
        tmp_path,
        page_fetch=_FakePageFetch(pages, raise_429_on=raise_429_on),
        plan=_plan(refetch, covered=covered),
        ledger=ledger,
    )
    receipts = tmp_path / "receipts"
    outbound = build_parity_outbound(
        s3_reader=S3OfferPlaneReader(bucket="autom8-s3", client=client),
        fetcher=fetcher,
        store=store,
        receipt_writer=ParityReceiptWriter(root=receipts),
        budget=ledger,
        now=lambda: _DAY,
        sla_for=lambda _e: 3600,
    )
    return outbound, ledger, receipts


def _only_receipt(receipts: Path) -> dict[str, Any]:
    files = list(receipts.rglob("*.json"))
    assert len(files) == 1, f"expected exactly one receipt, got {files}"
    return json.loads(files[0].read_text())


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
async def test_3c_served_dual_leg_observation(tmp_path: Path) -> None:
    """A SWAPPED coverage-clean touch yields a ParityObservation + a served dual-leg receipt."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="autom8-s3")
        client.create_bucket(Bucket=_V2_BUCKET)
        _seed_v1(
            client,
            [_offer_row("ACTIVE", offer_id="x", mrr=300.0, office_phone="p1", vertical="v1")],
        )
        pages = {
            "ACTIVE": [
                [_offer_row("ACTIVE", offer_id="y", mrr=100.0, office_phone="p2", vertical="v2")]
            ]
        }
        outbound, _ledger_, receipts = _outbound_env(
            client, tmp_path, pages=pages, refetch=("ACTIVE",)
        )
        obs = await outbound(_aid())

    assert isinstance(obs, ParityObservation)
    assert obs.v1.plane == "v1/offer" and obs.v1.served_value == 300.0  # LEG A v1 (served)
    assert obs.v2.plane == "v2/offer" and obs.v2.served_value == 100.0  # LEG A v2 (served)
    receipt = _only_receipt(receipts)
    assert receipt["outcome"] == "served"
    legs = receipt["legs"]
    assert legs["served_active_mrr"]["v1"] == 300.0
    assert legs["served_active_mrr"]["v2"] == 100.0
    assert legs["exemplar_aggregate"]["v1"] == 300.0  # ACTIVE raw (single row)
    assert "office_phone" not in json.dumps(receipt)  # §6 #8 PII discipline


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
async def test_3c_fetch_refused_is_first_class_not_an_observation(tmp_path: Path) -> None:
    """F-305-2 regression: a completeness-gap rebuild -> ParityLegRefused + refusal receipt, NOT an obs."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="autom8-s3")
        client.create_bucket(Bucket=_V2_BUCKET)
        _seed_v1(client, [_offer_row("ACTIVE", offer_id="x", mrr=300.0)])
        pages = {"ACTIVE": [[_offer_row("ACTIVE", offer_id="y", mrr=100.0)]]}
        # ACTIVE 429s -> failed_sections -> C16 FETCH_REFUSED (coverage passes; the gap is the fetch)
        outbound, ledger, receipts = _outbound_env(
            client, tmp_path, pages=pages, refetch=("ACTIVE",), raise_429_on=("ACTIVE",)
        )
        with pytest.raises(ParityLegRefused):
            await outbound(_aid())

    receipt = _only_receipt(receipts)
    assert (
        receipt["outcome"] == "refused-fetch_refused"
    )  # first-class, never a coherent observation
    assert receipt["legs"]["served_active_mrr"]["v1"] == 300.0  # v1 served number preserved
    assert receipt["legs"]["served_active_mrr"]["v2"] is None  # v2 refused, not coerced to zero
    assert ledger.count_today() >= 1  # the charged 429 attempt still receipted (F-305-3)


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
async def test_3c_coverage_refusal_is_first_class_no_charge(tmp_path: Path) -> None:
    """A plan omitting an active section -> refused-coverage receipt, no charge, no observation."""
    incomplete = frozenset(list(_all_active_covered())[:-1])
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="autom8-s3")
        client.create_bucket(Bucket=_V2_BUCKET)
        _seed_v1(client, [_offer_row("ACTIVE", offer_id="x", mrr=300.0)])
        outbound, ledger, receipts = _outbound_env(
            client,
            tmp_path,
            pages={"ACTIVE": [[_offer_row("ACTIVE", offer_id="y", mrr=1.0)]]},
            refetch=("ACTIVE",),
            covered=incomplete,
        )
        with pytest.raises(ParityLegRefused):
            await outbound(_aid())

    receipt = _only_receipt(receipts)
    assert receipt["outcome"] == "refused-coverage"
    assert ledger.count_today() == 0  # fail-closed, no budget spent


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
async def test_3c_null_value_column_refuses_and_receipts(tmp_path: Path) -> None:
    """F-305-3 + 2026-08-05 frame-schema fix: a charged touch whose v2 frame carries a null value
    column REFUSES (staged_rejected) and still leaves a receipt. Explicit OFFER_SCHEMA construction
    fills a missing value column with null, so the rebuild's null-value-column guard refuses
    gracefully (incumbent v1 served number preserved) instead of the old uncaught crash — the
    charged-failure-leaves-a-receipt invariant now holds at the refusal altitude.
    """
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="autom8-s3")
        client.create_bucket(Bucket=_V2_BUCKET)
        _seed_v1(client, [_offer_row("ACTIVE", offer_id="x", mrr=300.0)])
        # v2 row omits 'cost' -> explicit-schema construction fills it null -> the rebuild's
        # null-value-column guard REFUSES (staged_rejected), preserving the v1 served number.
        bad_row = {
            "section": "ACTIVE",
            "offer_id": "y",
            "mrr": 1.0,
            "weekly_ad_spend": 1.0,
            "office_phone": "p",
            "vertical": "v",
        }
        outbound, ledger, receipts = _outbound_env(
            client, tmp_path, pages={"ACTIVE": [[bad_row]]}, refetch=("ACTIVE",)
        )
        with pytest.raises(Exception, match="value column"):
            await outbound(_aid())

    receipt = _only_receipt(receipts)
    assert receipt["outcome"] == "refused-staged_rejected"  # graceful refusal, not an error/crash
    assert "value column" in receipt["detail"]  # the null-value-column reason is carried
    assert ledger.count_today() >= 1  # the fetch charged before the refusal — receipted (P10)


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
async def test_3c_budget_halt_writes_receipt_and_reraises(tmp_path: Path) -> None:
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="autom8-s3")
        client.create_bucket(Bucket=_V2_BUCKET)
        _seed_v1(client, [_offer_row("ACTIVE", offer_id="x", mrr=300.0)])
        outbound, ledger, receipts = _outbound_env(
            client,
            tmp_path,
            pages={"ACTIVE": [[_offer_row("ACTIVE", offer_id="y", mrr=1.0)]]},
            refetch=("ACTIVE",),
            cap=1,
        )
        ledger.consume()  # exhaust before the touch
        with pytest.raises(ParityBudgetExhausted):
            await outbound(_aid())

    receipt = _only_receipt(receipts)
    assert receipt["outcome"] == "budget-halt"
    assert "operator_interrupt" in receipt


def test_3c_arm_routes_singleton(_reset_singleton: None) -> None:
    from tests.harness.substrate_gate.parity import get_process_fetcher

    async def _outbound(_aid: ArtifactId) -> ParityObservation:  # pragma: no cover - never run here
        raise AssertionError

    source = arm_process_parity_fetcher(_outbound)
    assert source.armed is True
    assert source.routes_through_paced_primitives() is True
    assert get_process_fetcher() is source  # never a second instance


def test_3c_conflicting_rearm_refuses(_reset_singleton: None) -> None:
    async def _a(_aid: ArtifactId) -> ParityObservation:  # pragma: no cover
        raise AssertionError

    async def _b(_aid: ArtifactId) -> ParityObservation:  # pragma: no cover
        raise AssertionError

    arm_process_parity_fetcher(_a)
    with pytest.raises(RuntimeError, match="already armed"):
        arm_process_parity_fetcher(_b)


# ===========================================================================
# 3d — per-touch DUAL-LEG receipt writer
# ===========================================================================


def _swapped_result() -> Any:
    from autom8_asana.substrate.rebuild import FetchTelemetry, RebuildResult
    from autom8_asana.substrate.store import VersionId

    return RebuildResult(
        outcome=RebuildOutcome.SWAPPED,
        version_id=VersionId("v-abc"),
        built_from_live_at=_DAY,
        telemetry=FetchTelemetry(
            requests_issued=3,
            http_429_count=1,
            retries_issued=1,
            sections_refetched=2,
            sections_reused=1,
        ),
    )


def test_3d_write_served_dual_leg(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.consume(3)
    writer = ParityReceiptWriter(root=tmp_path / "receipts")
    legs = live.ParityLegs(
        served_v1=150.0,
        served_v2=150.0,
        served_digest="sha256:aa",
        exemplar_v1=250.0,
        exemplar_v2=250.0,
        exemplar_digest="sha256:bb",
    )
    path = writer.write_served(_aid(), result=_swapped_result(), legs=legs, ledger=ledger, at=_DAY)
    payload = json.loads(path.read_text())
    assert path.parent.name == "2026-08-04"
    assert payload["outcome"] == "served"
    assert payload["legs"]["served_active_mrr"]["v1"] == 150.0
    assert payload["legs"]["exemplar_aggregate"]["v1"] == 250.0
    assert payload["telemetry"]["requests_issued"] == 3
    assert payload["budget"] == {"count_today": 3, "cap": 100}
    assert "office_phone" not in json.dumps(payload)  # §6 #8 PII discipline


def test_3d_write_error_names_the_exception(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.consume(2)
    writer = ParityReceiptWriter(root=tmp_path / "receipts")
    path = writer.write_error(
        _aid(),
        error=ValueError("boom"),
        ledger=ledger,
        at=_DAY,
        legs=live.ParityLegs(served_v1=1.0),
    )
    payload = json.loads(path.read_text())
    assert payload["outcome"] == "error"
    assert payload["error"] == {"type": "ValueError", "message": "boom"}
    assert payload["budget"]["count_today"] == 2  # the charged touch is receipted


def test_3d_write_budget_halt_marks_operator_interrupt(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, cap=1)
    ledger.consume()
    writer = ParityReceiptWriter(root=tmp_path / "receipts")
    path = writer.write_budget_halt(_aid(), ledger=ledger, at=_DAY, detail="exhausted")
    payload = json.loads(path.read_text())
    assert payload["outcome"] == "budget-halt"
    assert payload["legs"] is None
    assert "budget-exhaustion" in payload["operator_interrupt"]


# ===========================================================================
# entry point — arm_offer_parity_window composes 3a-3d (no I/O by itself)
# ===========================================================================


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
def test_entry_arm_window_composes_and_is_dark(tmp_path: Path, _reset_singleton: None) -> None:
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_V2_BUCKET)
        from autom8_asana.substrate.store import S3ArtifactStore

        window = arm_offer_parity_window(
            bucket="autom8-s3",
            page_fetch=_FakePageFetch({}),
            plan=_plan(()),
            store=S3ArtifactStore(_V2_BUCKET, client=client),
            cap=11_200,
            ledger_path=tmp_path / "budget.json",
            receipts_root=tmp_path / "receipts",
        )
    assert isinstance(window, ArmedParityWindow)
    assert window.source.armed is True
    assert window.source.routes_through_paced_primitives() is True
    assert window.ledger.cap == 11_200
