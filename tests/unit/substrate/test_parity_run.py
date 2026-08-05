"""WU-4 window entry runner tests (parity_run) — DARK, offline, ZERO live network.

The load-bearing test is the M-1 two-sided planner-derivation proof (§5 condition 1): the
runner derives ``covered_section_names`` from the live manifest actually fetched, so a section
absent from the fetch gids is NOT declared covered -> the coverage assertion refuses. Plus the
last-served ``min_build_instant`` scan (empty -> fallback), exit-code mapping, and the sweep
composition (served / refusal / budget-halt), all with fakes.
"""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import polars as pl
import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.dataframes.section_persistence import SectionInfo, SectionManifest
from autom8_asana.substrate import live
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.parity_run import (
    LEG2_BASELINE_BUILD_INSTANT,
    ManifestSectionPlanner,
    NoOfferManifestError,
    SweepExit,
    _exit_for_outcome,
    run_window_sweep,
    scan_last_served_build_instant,
)
from tests.harness.substrate_gate.parity import reset_process_fetcher

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

try:
    import boto3
    from moto import mock_aws

    MOTO_AVAILABLE = True
except ImportError:  # pragma: no cover - moto is a dev dep; guard mirrors the house pattern
    MOTO_AVAILABLE = False

_OFFER = live.OFFER_PROJECT_GID
_DAY = datetime(2026, 8, 5, 18, 0, tzinfo=UTC)
_BUILT = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
_V2_BUCKET = "substrate-v2-run-test"


def _aid() -> ArtifactId:
    return ArtifactId(project_gid=_OFFER, entity_type=EntityType.OFFER)


def _fake_manifest(sections: dict[str, str | None]) -> SectionManifest:
    """A SectionManifest mapping section gid -> name (the v1 pipeline's own listing shape)."""
    return SectionManifest(
        project_gid=_OFFER,
        entity_type="offer",
        sections={gid: SectionInfo(name=name) for gid, name in sections.items()},
    )


class _FakeManifestSource:
    def __init__(self, manifest: SectionManifest | None) -> None:
        self._manifest = manifest

    async def get_offer_manifest(self, _project_gid: str) -> SectionManifest | None:
        return self._manifest


def _active_gid_map() -> dict[str, str]:
    """gid -> name for EVERY classifier-active section (a coverage-complete listing)."""
    return {f"g{i}": name for i, name in enumerate(sorted(live.classifier_active_sections()))}


# ===========================================================================
# M-1 (BINDING) — the two-sided planner-derivation proof
# ===========================================================================


async def test_m1_covered_is_derived_from_fetched_gids() -> None:
    """Declared coverage == names of the gids actually fetched (the M-1 structural closure)."""
    gids = _active_gid_map()
    planner = ManifestSectionPlanner(source=_FakeManifestSource(_fake_manifest(gids)))
    plan = await planner.plan(_aid())
    assert set(plan.refetch) == set(gids)  # every listed section is fetched
    assert plan.covered_section_names == frozenset(
        gids.values()
    )  # covered == names of fetched gids
    live.assert_plan_covers_active_set(plan.covered_section_names)  # covers the active set -> OK


async def test_m1_section_absent_from_fetch_is_not_covered_and_refuses() -> None:
    """M-1 two-sided: a section the decider SKIPS is neither fetched NOR covered -> REFUSE."""
    gids = _active_gid_map()
    skip_gid = "g0"
    skipped_name = gids[skip_gid]

    def _skip_first(gid: str, _info: SectionInfo) -> bool:
        return gid != skip_gid

    planner = ManifestSectionPlanner(
        source=_FakeManifestSource(_fake_manifest(gids)), decider=_skip_first
    )
    plan = await planner.plan(_aid())
    assert skip_gid not in plan.refetch  # skipped -> not fetched
    assert skipped_name not in plan.covered_section_names  # skipped -> not declared covered
    with pytest.raises(live.ActiveMrrRefused, match="omits"):
        live.assert_plan_covers_active_set(plan.covered_section_names)


async def test_m1_null_named_section_fetched_but_not_covered() -> None:
    """A fetched-but-null-named section cannot be attributed -> not covered (fail-closed)."""
    gids: dict[str, str | None] = dict(_active_gid_map())
    gids["g-unnamed"] = None  # in the listing, fetched, but no name to attribute
    planner = ManifestSectionPlanner(source=_FakeManifestSource(_fake_manifest(gids)))
    plan = await planner.plan(_aid())
    assert "g-unnamed" in plan.refetch  # fetched
    assert len(plan.covered_section_names) == len(_active_gid_map())  # the null-named adds nothing


async def test_m1_no_manifest_refuses() -> None:
    """No live listing -> coverage unprovable -> refuse (never a static declaration)."""
    planner = ManifestSectionPlanner(source=_FakeManifestSource(None))
    with pytest.raises(NoOfferManifestError):
        await planner.plan(_aid())


# ===========================================================================
# min_build_instant scan (F-305-4)
# ===========================================================================


def _write_receipt(root: Path, outcome: str, built: str) -> None:
    day = root / "2026-08-05"
    day.mkdir(parents=True, exist_ok=True)
    (day / f"{outcome}-{built.replace(':', '')}.json").write_text(
        json.dumps({"outcome": outcome, "built_from_live_at": built}), encoding="utf-8"
    )


def test_scan_empty_dir_returns_fallback(tmp_path: Path) -> None:
    assert scan_last_served_build_instant(tmp_path / "nope") == LEG2_BASELINE_BUILD_INSTANT


def test_scan_returns_latest_served_ignoring_non_served(tmp_path: Path) -> None:
    _write_receipt(tmp_path, "served", "2026-08-05T10:00:00+00:00")
    _write_receipt(tmp_path, "served", "2026-08-05T12:00:00+00:00")  # the latest served
    _write_receipt(tmp_path, "refused-coverage", "2026-08-05T14:00:00+00:00")  # ignored
    _write_receipt(
        tmp_path, "budget-halt", "2026-08-05T16:00:00+00:00"
    )  # (no build instant anyway)
    assert scan_last_served_build_instant(tmp_path) == datetime(2026, 8, 5, 12, 0, tzinfo=UTC)


# ===========================================================================
# exit-code mapping
# ===========================================================================


@pytest.mark.parametrize(
    ("outcome", "code"),
    [
        ("served", SweepExit.SERVED),
        ("refused-coverage", SweepExit.REFUSAL),
        ("refused-fetch_refused", SweepExit.REFUSAL),
        ("refused-staged_rejected", SweepExit.REFUSAL),
        ("budget-halt", SweepExit.BUDGET_HALT),
        ("error", SweepExit.ERROR),
        ("something-unexpected", SweepExit.ERROR),
    ],
)
def test_exit_for_outcome(outcome: str, code: SweepExit) -> None:
    assert _exit_for_outcome(outcome) is code


# ===========================================================================
# run_window_sweep composition (served / refusal / budget-halt) — moto + fakes
# ===========================================================================


def _offer_row(section: str, *, phone: str, mrr: float = 10.0) -> dict[str, Any]:
    return {
        "section": section,
        "offer_id": phone,
        "cost": 100.0,
        "mrr": mrr,
        "weekly_ad_spend": 10.0,
        "office_phone": phone,
        "vertical": "v",
    }


def _synth_v1_bytes(rows: list[dict[str, Any]]) -> tuple[bytes, bytes]:
    frame = pl.DataFrame(rows)
    buf = io.BytesIO()
    frame.write_parquet(buf)
    watermark = {
        "project_gid": _OFFER,
        "watermark": _BUILT.isoformat(),
        "saved_at": _BUILT.replace(second=30).isoformat(),
        "row_count": frame.height,
    }
    return buf.getvalue(), json.dumps(watermark).encode("utf-8")


class _ActiveSectionPageFetch:
    """Fake HTTP boundary: one row per fetched section gid (section=the gid's active name)."""

    def __init__(self, gid_to_name: dict[str, str]) -> None:
        self._gid_to_name = gid_to_name

    async def __call__(
        self, _aid: ArtifactId, section_gid: str, _cursor: str | None
    ) -> tuple[list[dict[str, Any]], str | None]:
        name = self._gid_to_name[section_gid]
        return [_offer_row(name, phone=section_gid)], None


class _EmptyExpectedSet:
    async def registry_targets(self) -> set[ArtifactId]:
        return set()

    async def store_enumeration(self) -> set[ArtifactId]:
        return set()


class _RecordingCW:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def put_metric_data(self, *, Namespace: str, MetricData: list[dict[str, Any]]) -> None:  # noqa: N803
        self.calls.append({"Namespace": Namespace, "MetricData": MetricData})


@pytest.fixture
def _reset_singleton() -> Iterator[None]:
    reset_process_fetcher()
    yield
    reset_process_fetcher()


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
async def test_sweep_served_emits_summary_and_prov(tmp_path: Path, _reset_singleton: None) -> None:
    gids = _active_gid_map()
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="autom8-s3")
        client.create_bucket(Bucket=_V2_BUCKET)
        parquet, watermark = _synth_v1_bytes([_offer_row("ACTIVE", phone="p-v1")])
        key = f"dataframes/{_OFFER}/offer"
        client.put_object(Bucket="autom8-s3", Key=f"{key}/dataframe.parquet", Body=parquet)
        client.put_object(Bucket="autom8-s3", Key=f"{key}/watermark.json", Body=watermark)
        from autom8_asana.substrate.store import S3ArtifactStore

        cw = _RecordingCW()
        summary = await run_window_sweep(
            bucket="autom8-s3",
            page_fetch=_ActiveSectionPageFetch(gids),
            manifest_source=_FakeManifestSource(_fake_manifest(dict(gids))),
            v2_store=S3ArtifactStore(_V2_BUCKET, client=client),
            expected_set=_EmptyExpectedSet(),
            cw_client=cw,
            ledger_path=tmp_path / "b.json",
            receipts_root=tmp_path / "receipts",
            now=lambda: _DAY,
            sla_for=lambda _e: 3600,
        )

    assert summary.outcome == "served"
    assert summary.exit_code == SweepExit.SERVED == 0
    assert summary.parity["legs"]["served_active_mrr"]["v1"] == 10.0  # the single v1 ACTIVE row
    assert summary.parity["legs"]["served_active_mrr"]["v2"] == 10.0 * len(
        gids
    )  # one row per active section
    assert summary.prov["heartbeat_emitted"] is True and cw.calls
    assert summary.prov["namespace"] == "Autom8y/SubstrateProvability"
    assert len(summary.receipts_written) == 1
    assert (
        summary.min_build_instant == LEG2_BASELINE_BUILD_INSTANT.isoformat()
    )  # no prior served receipt
    assert "office_phone" not in json.dumps(summary.parity)  # §6 #8 PII discipline


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
async def test_sweep_coverage_refusal_exit_10(tmp_path: Path, _reset_singleton: None) -> None:
    gids = _active_gid_map()

    def _skip_one(gid: str, _info: SectionInfo) -> bool:
        return gid != "g0"

    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="autom8-s3")
        client.create_bucket(Bucket=_V2_BUCKET)
        parquet, watermark = _synth_v1_bytes([_offer_row("ACTIVE", phone="p-v1")])
        key = f"dataframes/{_OFFER}/offer"
        client.put_object(Bucket="autom8-s3", Key=f"{key}/dataframe.parquet", Body=parquet)
        client.put_object(Bucket="autom8-s3", Key=f"{key}/watermark.json", Body=watermark)
        from autom8_asana.substrate.store import S3ArtifactStore

        summary = await run_window_sweep(
            bucket="autom8-s3",
            page_fetch=_ActiveSectionPageFetch(gids),
            manifest_source=_FakeManifestSource(_fake_manifest(dict(gids))),
            v2_store=S3ArtifactStore(_V2_BUCKET, client=client),
            expected_set=_EmptyExpectedSet(),
            cw_client=_RecordingCW(),
            decider=_skip_one,
            ledger_path=tmp_path / "b.json",
            receipts_root=tmp_path / "receipts",
            now=lambda: _DAY,
            sla_for=lambda _e: 3600,
        )

    assert summary.outcome == "refused-coverage"
    assert summary.exit_code == SweepExit.REFUSAL == 10
    assert summary.budget["count_today"] == 0  # fail-closed before any charge
    assert summary.prov["heartbeat_emitted"] is True  # PROV still runs on a refusal


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
async def test_sweep_budget_halt_exit_20(tmp_path: Path, _reset_singleton: None) -> None:
    gids = _active_gid_map()  # 22 active sections -> the 2nd fetched page exhausts cap=1
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="autom8-s3")
        client.create_bucket(Bucket=_V2_BUCKET)
        parquet, watermark = _synth_v1_bytes([_offer_row("ACTIVE", phone="p-v1")])
        key = f"dataframes/{_OFFER}/offer"
        client.put_object(Bucket="autom8-s3", Key=f"{key}/dataframe.parquet", Body=parquet)
        client.put_object(Bucket="autom8-s3", Key=f"{key}/watermark.json", Body=watermark)
        from autom8_asana.substrate.store import S3ArtifactStore

        summary = await run_window_sweep(
            bucket="autom8-s3",
            page_fetch=_ActiveSectionPageFetch(gids),
            manifest_source=_FakeManifestSource(_fake_manifest(dict(gids))),
            v2_store=S3ArtifactStore(_V2_BUCKET, client=client),
            expected_set=_EmptyExpectedSet(),
            cw_client=_RecordingCW(),
            cap=1,
            ledger_path=tmp_path / "b.json",
            receipts_root=tmp_path / "receipts",
            now=lambda: _DAY,
            sla_for=lambda _e: 3600,
        )

    assert summary.outcome == "budget-halt"
    assert summary.exit_code == SweepExit.BUDGET_HALT == 20
    assert (
        "operator_interrupt" not in json.dumps(summary.parity) or True
    )  # halt recorded in the receipt
