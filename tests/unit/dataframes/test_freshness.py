"""Unit tests for section freshness prober and delta merge."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.dataframes.builders.freshness import (
    ProbeVerdict,
    SectionFreshnessProber,
    compute_gid_hash,
)
from autom8_asana.dataframes.section_persistence import (
    SectionInfo,
    SectionManifest,
    SectionStatus,
)


class TestComputeGidHash:
    """Tests for compute_gid_hash helper."""

    def test_empty_list(self) -> None:
        h = compute_gid_hash([])
        assert isinstance(h, str)
        assert len(h) == 16

    def test_stable_across_calls(self) -> None:
        gids = ["123", "456", "789"]
        assert compute_gid_hash(gids) == compute_gid_hash(gids)

    def test_order_independent(self) -> None:
        """Hash of same GIDs in different order should be identical."""
        assert compute_gid_hash(["a", "b", "c"]) == compute_gid_hash(["c", "a", "b"])

    def test_different_gids_different_hash(self) -> None:
        h1 = compute_gid_hash(["a", "b"])
        h2 = compute_gid_hash(["a", "c"])
        assert h1 != h2

    def test_truncated_to_16_chars(self) -> None:
        h = compute_gid_hash(["1", "2", "3"])
        assert len(h) == 16


class TestProbeVerdict:
    """Tests for ProbeVerdict enum."""

    def test_values(self) -> None:
        assert ProbeVerdict.CLEAN == "clean"
        assert ProbeVerdict.STRUCTURE_CHANGED == "structure_changed"
        assert ProbeVerdict.CONTENT_CHANGED == "content_changed"
        assert ProbeVerdict.NO_BASELINE == "no_baseline"
        assert ProbeVerdict.PROBE_FAILED == "probe_failed"


def _make_manifest(
    sections: dict[str, SectionInfo] | None = None,
) -> SectionManifest:
    """Helper to build a test manifest."""
    if sections is None:
        sections = {}
    return SectionManifest(
        project_gid="proj_1",
        entity_type="offer",
        total_sections=len(sections),
        completed_sections=sum(1 for s in sections.values() if s.status == SectionStatus.COMPLETE),
        sections=sections,
        schema_version="v1",
    )


def _make_task_mock(gid: str) -> MagicMock:
    """Create a mock task with a gid."""
    t = MagicMock()
    t.gid = gid
    return t


def _make_page_iterator(tasks: list[MagicMock]) -> MagicMock:
    """Create a mock PageIterator that returns tasks on collect()."""
    pi = MagicMock()
    pi.collect = AsyncMock(return_value=tasks)
    return pi


class TestSectionFreshnessProber:
    """Tests for SectionFreshnessProber probe logic."""

    def _make_prober(
        self,
        manifest: SectionManifest,
        list_async_side_effect: list | None = None,
    ) -> tuple[SectionFreshnessProber, MagicMock]:
        client = MagicMock()
        persistence = MagicMock()
        schema = MagicMock()
        schema.version = "v1"

        if list_async_side_effect:
            client.tasks.list_async.side_effect = list_async_side_effect

        prober = SectionFreshnessProber(
            client=client,
            persistence=persistence,
            project_gid="proj_1",
            manifest=manifest,
            schema=schema,
        )
        return prober, client

    @pytest.mark.asyncio
    async def test_probe_no_complete_sections(self) -> None:
        manifest = _make_manifest({"sec_1": SectionInfo(status=SectionStatus.PENDING)})
        prober, _ = self._make_prober(manifest)
        results = await prober.probe_all_async()
        assert results == []

    @pytest.mark.asyncio
    async def test_probe_no_baseline_when_gid_hash_none(self) -> None:
        """Section with no stored gid_hash should get NO_BASELINE verdict."""
        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    gid_hash=None,
                    watermark=None,
                )
            }
        )
        tasks = [_make_task_mock("t1"), _make_task_mock("t2")]
        prober, client = self._make_prober(
            manifest,
            list_async_side_effect=[_make_page_iterator(tasks)],
        )

        results = await prober.probe_all_async()
        assert len(results) == 1
        assert results[0].verdict == ProbeVerdict.NO_BASELINE

    @pytest.mark.asyncio
    async def test_probe_structure_changed(self) -> None:
        """Hash mismatch → STRUCTURE_CHANGED."""
        stored_hash = compute_gid_hash(["t1", "t2", "t3"])
        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=3,
                    gid_hash=stored_hash,
                    watermark=datetime(2026, 1, 1, tzinfo=UTC),
                )
            }
        )
        # Current API returns different tasks (t3 removed, t4 added)
        current_tasks = [
            _make_task_mock("t1"),
            _make_task_mock("t2"),
            _make_task_mock("t4"),
        ]
        prober, client = self._make_prober(
            manifest,
            list_async_side_effect=[_make_page_iterator(current_tasks)],
        )

        results = await prober.probe_all_async()
        assert len(results) == 1
        assert results[0].verdict == ProbeVerdict.STRUCTURE_CHANGED

    @pytest.mark.asyncio
    async def test_probe_content_changed(self) -> None:
        """Hash matches but modified_since returns >1 → CONTENT_CHANGED."""
        gids = ["t1", "t2"]
        stored_hash = compute_gid_hash(gids)
        watermark = datetime(2026, 1, 1, tzinfo=UTC)

        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=2,
                    gid_hash=stored_hash,
                    watermark=watermark,
                )
            }
        )

        # First call: GID fetch returns same tasks
        gid_tasks = [_make_task_mock("t1"), _make_task_mock("t2")]
        # Second call: modified_since returns 2 tasks (1 false positive + 1 real change)
        modified_tasks = [_make_task_mock("t1"), _make_task_mock("t2")]

        prober, client = self._make_prober(
            manifest,
            list_async_side_effect=[
                _make_page_iterator(gid_tasks),
                _make_page_iterator(modified_tasks),
            ],
        )

        results = await prober.probe_all_async()
        assert len(results) == 1
        assert results[0].verdict == ProbeVerdict.CONTENT_CHANGED

    @pytest.mark.asyncio
    async def test_probe_clean(self) -> None:
        """Hash matches and modified_since returns <=1 → CLEAN."""
        gids = ["t1", "t2"]
        stored_hash = compute_gid_hash(gids)
        watermark = datetime(2026, 1, 1, tzinfo=UTC)

        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=2,
                    gid_hash=stored_hash,
                    watermark=watermark,
                )
            }
        )

        gid_tasks = [_make_task_mock("t1"), _make_task_mock("t2")]
        # Only 1 task from modified_since (the inclusive boundary false-positive)
        modified_tasks = [_make_task_mock("t1")]

        prober, client = self._make_prober(
            manifest,
            list_async_side_effect=[
                _make_page_iterator(gid_tasks),
                _make_page_iterator(modified_tasks),
            ],
        )

        results = await prober.probe_all_async()
        assert len(results) == 1
        assert results[0].verdict == ProbeVerdict.CLEAN

    @pytest.mark.asyncio
    async def test_probe_clean_zero_modified(self) -> None:
        """Hash matches and modified_since returns 0 → CLEAN."""
        gids = ["t1"]
        stored_hash = compute_gid_hash(gids)
        watermark = datetime(2026, 1, 1, tzinfo=UTC)

        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=1,
                    gid_hash=stored_hash,
                    watermark=watermark,
                )
            }
        )

        prober, client = self._make_prober(
            manifest,
            list_async_side_effect=[
                _make_page_iterator([_make_task_mock("t1")]),
                _make_page_iterator([]),
            ],
        )

        results = await prober.probe_all_async()
        assert len(results) == 1
        assert results[0].verdict == ProbeVerdict.CLEAN

    @pytest.mark.asyncio
    async def test_probe_failed_on_api_error(self) -> None:
        """API error → PROBE_FAILED (graceful degradation)."""
        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    gid_hash="abc123",
                    watermark=datetime(2026, 1, 1, tzinfo=UTC),
                )
            }
        )

        pi = MagicMock()
        pi.collect = AsyncMock(side_effect=RuntimeError("API timeout"))

        prober, client = self._make_prober(
            manifest,
            list_async_side_effect=[pi],
        )

        results = await prober.probe_all_async()
        assert len(results) == 1
        assert results[0].verdict == ProbeVerdict.PROBE_FAILED


class TestSectionInfoFreshnessFields:
    """Tests for watermark/gid_hash fields on SectionInfo."""

    def test_default_none(self) -> None:
        info = SectionInfo()
        assert info.watermark is None
        assert info.gid_hash is None

    def test_set_values(self) -> None:
        now = datetime.now(UTC)
        info = SectionInfo(
            status=SectionStatus.COMPLETE,
            rows=10,
            watermark=now,
            gid_hash="abc123def456",
        )
        assert info.watermark == now
        assert info.gid_hash == "abc123def456"

    def test_backward_compat_deserialization(self) -> None:
        """Old manifests without watermark/gid_hash should deserialize fine."""
        data = {
            "status": "complete",
            "rows": 5,
            "written_at": "2026-01-01T00:00:00+00:00",
        }
        info = SectionInfo.model_validate(data)
        assert info.watermark is None
        assert info.gid_hash is None
        assert info.rows == 5

    def test_manifest_mark_section_complete_with_freshness(self) -> None:
        """mark_section_complete passes through watermark and gid_hash."""
        manifest = _make_manifest({"sec_1": SectionInfo()})
        now = datetime.now(UTC)
        manifest.mark_section_complete("sec_1", 10, watermark=now, gid_hash="deadbeef12345678")

        info = manifest.sections["sec_1"]
        assert info.status == SectionStatus.COMPLETE
        assert info.watermark == now
        assert info.gid_hash == "deadbeef12345678"
        assert info.rows == 10
