"""WU-3 live-parity arming tests (3a-3d) — DARK, offline, fakes at the HTTP boundary.

CARDINAL P10 boundary: ZERO live Asana calls. The v1 side reads S3 (moto fake); the v2
side fetches through an injected fake ``page_fetch`` (no network). Discriminating, two-sided
where a guard is added: torn-read refusal (3a), budget-charge-per-attempt incl. 429 (3b),
reuse-never-charges (3b), receipt-per-touch incl. budget-halt (3d).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import polars as pl
import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.live import (
    OFFER_PROJECT_GID,
    ArmedParityWindow,
    OfferSectionPlan,
    PacedOfferSectionFetcher,
    ParityReceiptWriter,
    ReusedSection,
    S3OfferPlaneReader,
    TornOfferPlaneRead,
    arm_offer_parity_window,
    arm_process_parity_fetcher,
    build_parity_outbound,
    build_v1_offer_materialization,
    materialize_v1_offer_plane,
    rebuild_offer_v2,
)
from autom8_asana.substrate.rebuild import RebuildOutcome
from tests.harness.substrate_gate.budget import ParityBudgetExhausted, PerDayBudgetLedger
from tests.harness.substrate_gate.exemplars import exemplar_two_materialization
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
_DAY = datetime(2026, 7, 30, 18, 0, tzinfo=UTC)


def _fixed_clock() -> Callable[[], datetime]:
    return lambda: _DAY


def _aid() -> ArtifactId:
    return ArtifactId(project_gid=OFFER_PROJECT_GID, entity_type=EntityType.OFFER)


def _fixture_bytes() -> tuple[bytes, bytes]:
    return (
        (_FIXTURE_DIR / "offer_plane_section_mrr.parquet").read_bytes(),
        (_FIXTURE_DIR / "watermark.json").read_bytes(),
    )


def _ledger(tmp_path: Path, *, cap: int = 100) -> PerDayBudgetLedger:
    return PerDayBudgetLedger(path=tmp_path / "budget.json", cap=cap, clock=_fixed_clock())


class _FastClock:
    """Monotone fake clock so the floor gate earns tokens instantly (no real sleeps)."""

    def __init__(self) -> None:
        self._t = 0.0

    def __call__(self) -> float:
        self._t += 1000.0
        return self._t


async def _no_sleep(_seconds: float) -> None:
    return None


class _Fake429(Exception):
    """A 429-signalling boundary error (status_code=429, NOT an Autom8Error, no botocore .response).

    ``_is_transient`` classifies it non-transient (no orchestrator retry), so it fails fast —
    the budget charge already landed BEFORE the boundary call (pythia §5: 429s charge).
    """

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


def _offer_row(section: str, *, offer_id: str, mrr: float) -> dict[str, Any]:
    """A value-complete offer row (the four pinned value columns + section)."""
    return {
        "section": section,
        "offer_id": offer_id,
        "cost": 100.0,
        "mrr": mrr,
        "weekly_ad_spend": 10.0,
    }


def _plan(
    refetch: tuple[str, ...], reuse: Mapping[str, ReusedSection] | None = None
) -> Callable[[ArtifactId], Awaitable[OfferSectionPlan]]:
    async def _fn(_aid: ArtifactId) -> OfferSectionPlan:
        return OfferSectionPlan(refetch=refetch, reuse=dict(reuse or {}))

    return _fn


def _fetcher(
    tmp_path: Path,
    *,
    page_fetch: _FakePageFetch,
    plan: Callable[[ArtifactId], Awaitable[OfferSectionPlan]],
    ledger: PerDayBudgetLedger | None = None,
    now: datetime = _DAY,
) -> PacedOfferSectionFetcher:
    return PacedOfferSectionFetcher(
        page_fetch=page_fetch,
        plan=plan,
        budget=ledger if ledger is not None else _ledger(tmp_path),
        now=lambda: now,
        gate_clock=_FastClock(),
        gate_sleep=_no_sleep,
    )


# ===========================================================================
# 3a — v1 offer plane materialization + torn-read guard
# ===========================================================================


def test_3a_reproduces_exemplar_two_from_fixture_bytes() -> None:
    """The constructor re-derives the pinned active_mrr + composition digest from real bytes."""
    parquet, watermark = _fixture_bytes()
    mat = materialize_v1_offer_plane(parquet, watermark)
    exemplar = exemplar_two_materialization()
    assert mat.served_value == exemplar.served_value == 80_985.0
    assert mat.proof.content_digest == exemplar.proof.content_digest
    assert mat.frame_digest == mat.proof.content_digest  # coherent, not corrupt
    assert mat.proof.built_from_live_at == exemplar.proof.built_from_live_at
    assert {k: (c.rows, c.value) for k, c in mat.composition.items()} == {
        "ACTIVE": (47, 60_085.0),
        "OPTIMIZE - Human Review": (7, 10_900.0),
        "STAGED": (7, 10_000.0),
    }


def test_3a_torn_read_row_count_mismatch_refuses() -> None:
    """Two-sided: the consistent set materializes; a tampered row_count is REFUSED loud."""
    parquet, watermark = _fixture_bytes()
    assert materialize_v1_offer_plane(parquet, watermark) is not None  # consistent -> OK

    torn = json.loads(watermark)
    torn["row_count"] = torn["row_count"] + 1  # frame no longer matches the watermark
    with pytest.raises(TornOfferPlaneRead, match="row count"):
        materialize_v1_offer_plane(parquet, json.dumps(torn).encode("utf-8"))


def test_3a_build_after_save_refuses() -> None:
    """A watermark whose build instant post-dates its own save is a torn write — REFUSE."""
    parquet, watermark = _fixture_bytes()
    bad = json.loads(watermark)
    bad["watermark"] = "2026-08-01T00:00:00+00:00"  # after saved_at
    with pytest.raises(TornOfferPlaneRead, match="post-dates"):
        materialize_v1_offer_plane(parquet, json.dumps(bad).encode("utf-8"))


def test_3a_wrong_project_refuses() -> None:
    """A watermark for a different project is not the same plane — REFUSE."""
    parquet, watermark = _fixture_bytes()
    bad = json.loads(watermark)
    bad["project_gid"] = "9999999999999999"
    with pytest.raises(TornOfferPlaneRead, match="not the same plane"):
        materialize_v1_offer_plane(parquet, json.dumps(bad).encode("utf-8"))


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
def test_3a_s3_reader_reads_and_materializes() -> None:
    """S3-read-only reader (moto): GETs the v1 offer plane and materializes it (no Asana)."""
    parquet, watermark = _fixture_bytes()
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="autom8-s3")
        key = f"dataframes/{OFFER_PROJECT_GID}/offer"
        client.put_object(Bucket="autom8-s3", Key=f"{key}/dataframe.parquet", Body=parquet)
        client.put_object(Bucket="autom8-s3", Key=f"{key}/watermark.json", Body=watermark)
        reader = S3OfferPlaneReader(bucket="autom8-s3", client=client)
        mat = build_v1_offer_materialization(reader)
    assert mat.served_value == 80_985.0
    assert mat.plane == "v1/offer"


# ===========================================================================
# 3b — paced fetcher: budget charged per HTTP attempt (429s included; reuse never)
# ===========================================================================


async def test_3b_clean_multipage_charges_once_per_page(tmp_path: Path) -> None:
    """Each pagination page == one attempt == one budget charge (pythia §5)."""
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
    assert fetched.telemetry.requests_issued == 2  # two pages -> two attempts
    assert fetched.telemetry.http_429_count == 0
    assert ledger.count_today() == 2  # the budget invariant: count == boundary attempts
    assert fetched.frame.height == 2
    assert not fetched.failed_sections


async def test_3b_429_attempt_still_charges_and_shrinks_aimd(tmp_path: Path) -> None:
    """Two-sided: a 429'd attempt charges the budget exactly like a success, and hits AIMD."""
    pages = {"S1": [[_offer_row("ACTIVE", offer_id="a", mrr=1.0)]]}
    ledger = _ledger(tmp_path)
    page_fetch = _FakePageFetch(pages, raise_429_on=("S1",))
    fetcher = _fetcher(tmp_path, page_fetch=page_fetch, plan=_plan(("S1",)), ledger=ledger)

    fetched = await fetcher.fetch(_aid())

    assert fetched.telemetry is not None
    assert fetched.telemetry.http_429_count >= 1
    # THE budget invariant — every boundary attempt charged, the 429 included:
    assert ledger.count_today() == fetched.telemetry.requests_issued
    assert "S1" in fetched.failed_sections  # C16: the 429'd section is a partial -> refused
    assert fetcher._semaphore.get_stats()["decrease_count"] >= 1  # AIMD window shrank on 429


async def test_3b_reused_section_never_charges(tmp_path: Path) -> None:
    """A hash-CLEAN reused section touches no boundary and charges nothing (pythia §5)."""
    ledger = _ledger(tmp_path)
    reuse = {
        "S_reuse": ReusedSection(
            instant=datetime(2026, 7, 30, 17, 0, tzinfo=UTC),
            rows=(_offer_row("STAGED", offer_id="r", mrr=9.0),),
        )
    }
    fetcher = _fetcher(
        tmp_path, page_fetch=_FakePageFetch({}), plan=_plan((), reuse), ledger=ledger
    )

    fetched = await fetcher.fetch(_aid())

    assert ledger.count_today() == 0  # reuse never charges
    assert fetched.telemetry is not None
    assert fetched.telemetry.sections_reused == 1
    assert fetched.telemetry.requests_issued == 0
    assert fetched.frame.height == 1  # the reused rows are in the assembled frame
    assert fetched.section_instants["S_reuse"] == datetime(2026, 7, 30, 17, 0, tzinfo=UTC)


async def test_3b_budget_exhaustion_halts_and_propagates(tmp_path: Path) -> None:
    """At cap the charge raises ParityBudgetExhausted and it PROPAGATES (never swallowed)."""
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
async def test_3b_rebuild_caller_swaps_with_telemetry() -> None:
    """rebuild_offer_v2 threads the paced fetcher into SubstrateRebuilder -> SWAPPED + telemetry."""
    import tempfile

    pages = {
        "ACTIVE": [
            [
                _offer_row("ACTIVE", offer_id="a", mrr=100.0),
                _offer_row("ACTIVE", offer_id="b", mrr=200.0),
            ]
        ]
    }
    with mock_aws(), tempfile.TemporaryDirectory() as td:
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_V2_BUCKET)
        from autom8_asana.substrate.store import S3ArtifactStore

        store = S3ArtifactStore(_V2_BUCKET, client=client)
        ledger = PerDayBudgetLedger(path=Path(td) / "b.json", cap=100, clock=_fixed_clock())
        fetcher = _fetcher(
            Path(td), page_fetch=_FakePageFetch(pages), plan=_plan(("ACTIVE",)), ledger=ledger
        )
        result, fetched = await rebuild_offer_v2(
            _aid(), fetcher=fetcher, store=store, now=lambda: _DAY, sla_for=lambda _e: 3600
        )
    assert result.outcome is RebuildOutcome.SWAPPED
    assert result.telemetry is not None
    assert result.telemetry.requests_issued == 1
    assert fetched is not None
    assert fetched.frame.height == 2


# ===========================================================================
# 3c — the armed outbound + get_process_fetcher singleton arming
# ===========================================================================


@pytest.fixture
def _reset_singleton() -> Iterator[None]:
    reset_process_fetcher()
    yield
    reset_process_fetcher()


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
async def test_3c_outbound_produces_v1_beside_v2(tmp_path: Path) -> None:
    """The outbound reads v1 (S3) beside v2 (paced rebuild) into a ParityObservation."""
    parquet, watermark = _fixture_bytes()
    pages = {"ACTIVE": [[_offer_row("ACTIVE", offer_id="a", mrr=100.0)]]}
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="autom8-s3")
        client.create_bucket(Bucket=_V2_BUCKET)
        key = f"dataframes/{OFFER_PROJECT_GID}/offer"
        client.put_object(Bucket="autom8-s3", Key=f"{key}/dataframe.parquet", Body=parquet)
        client.put_object(Bucket="autom8-s3", Key=f"{key}/watermark.json", Body=watermark)
        from autom8_asana.substrate.store import S3ArtifactStore

        store = S3ArtifactStore(_V2_BUCKET, client=client)
        ledger = _ledger(tmp_path)
        fetcher = _fetcher(
            tmp_path, page_fetch=_FakePageFetch(pages), plan=_plan(("ACTIVE",)), ledger=ledger
        )
        writer = ParityReceiptWriter(root=tmp_path / "receipts")
        reader = S3OfferPlaneReader(bucket="autom8-s3", client=client)
        outbound = build_parity_outbound(
            s3_reader=reader,
            fetcher=fetcher,
            store=store,
            receipt_writer=writer,
            budget=ledger,
            now=lambda: _DAY,
            sla_for=lambda _e: 3600,
        )
        obs = await outbound(_aid())

    assert isinstance(obs, ParityObservation)
    assert obs.v1.plane == "v1/offer"
    assert obs.v1.served_value == 80_985.0  # v1 from the real S3 fixture
    assert obs.v2.plane == "v2/offer"
    assert obs.v2.served_value == 100.0  # v2 from the paced live rebuild
    # a per-touch receipt landed (3d):
    assert list((tmp_path / "receipts").rglob("*.json"))


def test_3c_arm_routes_singleton(_reset_singleton: None) -> None:
    """Arming goes through get_process_fetcher (one instance) and passes the RC-E-4 check."""
    from tests.harness.substrate_gate.parity import get_process_fetcher

    async def _outbound(_aid: ArtifactId) -> ParityObservation:  # pragma: no cover - never run here
        raise AssertionError

    source = arm_process_parity_fetcher(_outbound)
    assert source.armed is True
    assert source.routes_through_paced_primitives() is True
    assert get_process_fetcher() is source  # never a second instance


def test_3c_conflicting_rearm_refuses(_reset_singleton: None) -> None:
    """A second arm with a DIFFERENT outbound is a wiring bug — refuse loud (one instance)."""

    async def _a(_aid: ArtifactId) -> ParityObservation:  # pragma: no cover
        raise AssertionError

    async def _b(_aid: ArtifactId) -> ParityObservation:  # pragma: no cover
        raise AssertionError

    arm_process_parity_fetcher(_a)
    with pytest.raises(RuntimeError, match="already armed"):
        arm_process_parity_fetcher(_b)


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
async def test_3c_budget_halt_writes_receipt_and_reraises(tmp_path: Path) -> None:
    """A budget HALT records a budget-halt receipt and re-raises (never retried — charter L81)."""
    parquet, watermark = _fixture_bytes()
    pages = {"ACTIVE": [[_offer_row("ACTIVE", offer_id="a", mrr=100.0)]]}
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="autom8-s3")
        client.create_bucket(Bucket=_V2_BUCKET)
        key = f"dataframes/{OFFER_PROJECT_GID}/offer"
        client.put_object(Bucket="autom8-s3", Key=f"{key}/dataframe.parquet", Body=parquet)
        client.put_object(Bucket="autom8-s3", Key=f"{key}/watermark.json", Body=watermark)
        from autom8_asana.substrate.store import S3ArtifactStore

        store = S3ArtifactStore(_V2_BUCKET, client=client)
        ledger = _ledger(tmp_path, cap=1)
        ledger.consume()  # exhaust the day before the touch
        fetcher = _fetcher(
            tmp_path, page_fetch=_FakePageFetch(pages), plan=_plan(("ACTIVE",)), ledger=ledger
        )
        writer = ParityReceiptWriter(root=tmp_path / "receipts")
        reader = S3OfferPlaneReader(bucket="autom8-s3", client=client)
        outbound = build_parity_outbound(
            s3_reader=reader,
            fetcher=fetcher,
            store=store,
            receipt_writer=writer,
            budget=ledger,
            now=lambda: _DAY,
            sla_for=lambda _e: 3600,
        )
        with pytest.raises(ParityBudgetExhausted):
            await outbound(_aid())

    receipts = list((tmp_path / "receipts").rglob("*.json"))
    assert len(receipts) == 1
    payload = json.loads(receipts[0].read_text())
    assert payload["outcome"] == "budget-halt"
    assert "operator_interrupt" in payload


# ===========================================================================
# 3d — per-touch receipt writer
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


def test_3d_writes_receipt_consuming_telemetry_and_budget(tmp_path: Path) -> None:
    """One durable JSON receipt per touch: telemetry + budget state + outcome + timestamps."""
    ledger = _ledger(tmp_path)
    ledger.consume(3)
    writer = ParityReceiptWriter(root=tmp_path / "receipts")
    path = writer.write(_aid(), result=_swapped_result(), ledger=ledger, at=_DAY)

    assert path.parent.name == "2026-07-30"  # dated directory
    payload = json.loads(path.read_text())
    assert payload["outcome"] == "swapped"
    assert payload["aid"] == {"project_gid": OFFER_PROJECT_GID, "entity_type": "offer"}
    assert payload["telemetry"] == {
        "requests_issued": 3,
        "http_429_count": 1,
        "retries_issued": 1,
        "sections_refetched": 2,
        "sections_reused": 1,
    }
    assert payload["budget"] == {"count_today": 3, "cap": 100}
    assert payload["version_id"] == "v-abc"


def test_3d_budget_halt_receipt_marks_operator_interrupt(tmp_path: Path) -> None:
    """A budget-halt receipt records outcome=budget-halt + the charter L81 interrupt marker."""
    ledger = _ledger(tmp_path, cap=1)
    ledger.consume()
    writer = ParityReceiptWriter(root=tmp_path / "receipts")
    path = writer.write_budget_halt(_aid(), ledger=ledger, at=_DAY, detail="exhausted")

    payload = json.loads(path.read_text())
    assert payload["outcome"] == "budget-halt"
    assert payload["telemetry"] is None
    assert payload["budget"]["count_today"] == 1
    assert "budget-exhaustion" in payload["operator_interrupt"]


# ===========================================================================
# entry point — arm_offer_parity_window composes 3a-3d (no I/O by itself)
# ===========================================================================


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
def test_entry_arm_window_composes_and_is_dark(tmp_path: Path, _reset_singleton: None) -> None:
    """arm_offer_parity_window wires the armed source; performs NO Asana/S3 I/O itself."""
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
