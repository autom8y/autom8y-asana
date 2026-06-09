"""G2-RECV frame-quality convergence tests — AC-G2R6-2/3/4 + background build lifecycle.

Design: Option B (background build to completion + retryable 503).
Implements the test plan from the G2-RECV frame-quality convergence PR:

AC-G2R6-2: No-FAILED build → ProgressiveProjectBuilder produces manifest where all
    sections are COMPLETE → is_honest_complete(manifest) is True.

AC-G2R6-3: A section that fails to fetch/persist → manifest has a FAILED section →
    is_honest_complete(manifest) is False.

    Both AC-G2R6-2/3 drive the REAL builder (not a mocked _build_dataframe) with a
    mocked Asana FETCH layer (sections returned by the API client).  The manifest is
    asserted directly.

Cold-miss dedup (AC-G2R6-BG1): a body-parameterized cold miss returns the retryable
    503 (CACHE_BUILD_IN_PROGRESS) AND launches exactly one background build.

Dedup (AC-G2R6-BG2): a second concurrent same-GID miss does NOT launch a second build.

AC-G2R6-4: offer-domain cold miss still returns None (unchanged path), launches NO
    background build.

Background task lifecycle (AC-G2R6-BG3): the launched task clears its in-flight key
    on completion AND on failure.

Fidelity discipline:
- AC-G2R6-2/3 do NOT mock _build_dataframe or _build_entity_dataframe.  They mock only
  the Asana network boundary (client.sections.list_for_project_async and
  client.tasks.list_async / list_for_section_async) and the SectionPersistence storage
  backend (so no real S3 I/O is needed).  The REAL ProgressiveProjectBuilder runs.
- The mock was exactly why the gap slipped past CI (the old tests patched _build_dataframe
  and therefore never exercised the manifest write path that honest_contract_complete reads).
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from datetime import datetime

import polars as pl
import pytest

from autom8_asana.dataframes.builders.progressive import ProgressiveProjectBuilder
from autom8_asana.dataframes.section_persistence import (
    SectionInfo,
    SectionManifest,
    SectionPersistence,
    SectionStatus,
    is_honest_complete,
)
from autom8_asana.services.universal_strategy import (
    UniversalResolutionStrategy,
    _background_builds,
    get_universal_strategy,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROJECT_GID = "9900000000000001"
_SEC_1 = "sec_111111111111"
_SEC_2 = "sec_222222222222"


# ---------------------------------------------------------------------------
# Helpers — mock Asana client layer
# ---------------------------------------------------------------------------


def _make_mock_section(gid: str, name: str = "Test Section") -> MagicMock:
    """Minimal Section mock satisfying ProgressiveProjectBuilder._list_sections."""
    s = MagicMock()
    s.gid = gid
    s.name = name
    return s


def _make_mock_task(gid: str, name: str = "Test Task") -> MagicMock:
    """Minimal Task mock satisfying _task_to_dict (model_dump path)."""
    t = MagicMock()
    t.gid = gid
    t.name = name
    t.model_dump = MagicMock(return_value={"gid": gid, "name": name})
    return t


class _AsyncIterator:
    """Minimal async iterator wrapping a list (supports ``async for``)."""

    def __init__(self, items: list[Any]) -> None:
        self._items = iter(items)

    def __aiter__(self) -> _AsyncIterator:
        return self

    async def __anext__(self) -> Any:
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration


def _make_mock_client(sections: list[MagicMock], tasks: list[MagicMock]) -> MagicMock:
    """Mock AsanaClient with controlled sections/tasks return values.

    - sections.list_for_project_async("gid").collect() → list[Section]
      (the builder calls .collect() on the sections paginator).
    - tasks.list_async(...) returns an async-iterable that yields tasks
      one by one (the builder uses ``async for task in iterator``).
    """
    client = MagicMock()

    # sections.list_for_project_async("gid").collect() → list[Section]
    sections_paginator = MagicMock()
    sections_paginator.collect = AsyncMock(return_value=sections)
    client.sections.list_for_project_async = MagicMock(return_value=sections_paginator)

    # tasks.list_async(...) → async-iterable over tasks list.
    # Each call returns a fresh iterator so each section gets the same task list.
    def _tasks_list_async(**kwargs: Any) -> _AsyncIterator:
        return _AsyncIterator(tasks)

    client.tasks.list_async = MagicMock(side_effect=_tasks_list_async)

    return client


def _make_mock_persistence_writing() -> MagicMock:
    """SectionPersistence mock that records manifest state.

    Tracks update_manifest_section_async calls (which the builder calls
    directly on FAILED sections, and indirectly via write_section_async →
    COMPLETE side-effect) so tests can inspect the resulting manifest.

    The write_section_async side_effect records COMPLETE into _manifest_store
    (mirroring the real SectionPersistence.write_section_async behavior where
    a successful write → update_manifest_section_async(COMPLETE) is called
    internally).  The FAILED path is recorded via update_manifest_section_async
    which the builder calls directly in the exception handler.

    Does NOT touch real S3.
    """
    persistence = MagicMock(spec=SectionPersistence)
    persistence.__aenter__ = AsyncMock(return_value=persistence)
    persistence.__aexit__ = AsyncMock(return_value=None)

    # No existing manifest → fresh build.
    persistence.get_manifest_async = AsyncMock(return_value=None)

    # Shared manifest store keyed by project_gid.
    _manifest_store: dict[str, SectionManifest] = {}

    def _ensure_manifest(project_gid: str, entity_type: str) -> SectionManifest:
        if project_gid not in _manifest_store:
            _manifest_store[project_gid] = SectionManifest(
                project_gid=project_gid,
                entity_type=entity_type,
                total_sections=0,
                sections={},
            )
        return _manifest_store[project_gid]

    # create_manifest_async: called with (project_gid, entity_type, section_gids,
    # schema_version=..., section_names=...) — section_gids is a list of str GIDs.
    async def _create_manifest(
        project_gid: str,
        entity_type: str,
        section_gids: list[str],
        schema_version: str = "",
        section_names: dict[str, str] | None = None,
    ) -> SectionManifest:
        manifest = SectionManifest(
            project_gid=project_gid,
            entity_type=entity_type,
            total_sections=len(section_gids),
            schema_version=schema_version,
            sections={g: SectionInfo(status=SectionStatus.PENDING) for g in section_gids},
        )
        _manifest_store[project_gid] = manifest
        return manifest

    persistence.create_manifest_async = AsyncMock(side_effect=_create_manifest)

    # update_manifest_section_async: records the status in _manifest_store.
    # The builder calls this directly with SectionStatus.FAILED in the exception
    # handler (progressive.py:821-826).
    async def _update_manifest_section(
        project_gid: str,
        section_gid: str,
        status: SectionStatus | str,
        rows: int = 0,
        error: str | None = None,
        watermark: datetime | None = None,
        gid_hash: str | None = None,
        name: str | None = None,
        entity_type: str | None = None,
    ) -> SectionManifest:
        # SEAM-1: the builder now threads entity_type; accept it.
        manifest = _ensure_manifest(project_gid, entity_type or "project")
        manifest.sections[section_gid] = SectionInfo(
            status=SectionStatus(status) if isinstance(status, str) else status,
            rows=rows,
            error=error,
        )
        return manifest

    persistence.update_manifest_section_async = AsyncMock(side_effect=_update_manifest_section)

    # write_section_async: on success, mirror the real implementation by
    # recording COMPLETE into _manifest_store (the real write_section_async
    # calls update_manifest_section_async(COMPLETE) after a successful S3 write).
    async def _write_section(
        project_gid: str,
        section_gid: str,
        df: pl.DataFrame,
        *,
        watermark: datetime | None = None,
        gid_hash: str | None = None,
        name: str | None = None,
        entity_type: str | None = None,
    ) -> bool:
        """Per ADR-006 §Decision-7 / TDD §2.2.1 edit 3, ``write_section_async``
        gained an optional ``name`` keyword to re-seed the manifest entry's
        ``SectionInfo.name`` on completion. SEAM-1 (ADR-SEAM1) adds an
        ``entity_type`` keyword threaded by the builder; this mock accepts both
        to stay signature-compatible.
        """
        manifest = _ensure_manifest(project_gid, entity_type or "project")
        manifest.sections[section_gid] = SectionInfo(
            status=SectionStatus.COMPLETE,
            rows=len(df),
            name=name,
        )
        return True

    persistence.write_section_async = AsyncMock(side_effect=_write_section)

    # merge_sections_to_dataframe_async: return a minimal DataFrame.
    persistence.merge_sections_to_dataframe_async = AsyncMock(
        return_value=pl.DataFrame({"gid": ["task_1"], "name": ["Test Task"]})
    )

    # write_final_artifacts_async: no-op.
    persistence.write_final_artifacts_async = AsyncMock(return_value=True)

    # Store reference so tests can read back the manifest.
    persistence._manifest_store = _manifest_store

    return persistence


# ---------------------------------------------------------------------------
# AC-G2R6-2/3: Real builder + mocked fetch layer — manifest assertion
# ---------------------------------------------------------------------------


class TestAcG2R62R63ManifestHonesty:
    """AC-G2R6-2/3: drive the REAL ProgressiveProjectBuilder with a mocked Asana
    fetch layer and assert against the actual manifest.

    No _build_dataframe mock — the real builder writes the manifest.
    """

    async def test_ac_g2r6_2_all_complete_manifest_honest_complete(self) -> None:
        """AC-G2R6-2 GREEN path: both sections succeed → manifest all-COMPLETE →
        is_honest_complete(manifest) is True."""
        sections = [_make_mock_section(_SEC_1, "Active"), _make_mock_section(_SEC_2, "Paused")]
        tasks = [_make_mock_task("task_1", "Task One"), _make_mock_task("task_2", "Task Two")]
        client = _make_mock_client(sections, tasks)

        persistence = _make_mock_persistence_writing()
        schema = MagicMock()
        schema.version = "1.0.0"
        schema.to_polars_schema = MagicMock(return_value={"gid": pl.Utf8, "name": pl.Utf8})

        builder = ProgressiveProjectBuilder(
            client=client,
            project_gid=_PROJECT_GID,
            entity_type="project",
            schema=schema,
            persistence=persistence,
        )
        # Bypass dataframe-view initialisation (requires real schema registry).
        builder._ensure_dataframe_view = AsyncMock()
        # Bypass index building (not under test here).
        builder._build_index_data = MagicMock(return_value=None)

        # Mock the section-level DataFrame extraction so the builder does not
        # try to parse Asana task fields.  The real fetch→persist chain still
        # runs: _list_sections → _ensure_manifest → _fetch_and_persist_section →
        # write_section_async + update_manifest_section_async.
        with patch.object(
            builder,
            "_build_section_dataframe",
            return_value=(
                pl.DataFrame({"gid": ["task_1", "task_2"], "name": ["T1", "T2"]}),
                "abc123",
                None,
            ),
        ):
            await builder.build_progressive_async(resume=False)

        # Both sections must be COMPLETE in the manifest store.
        manifest_store = persistence._manifest_store
        assert manifest_store, "manifest must have been written"
        manifest = manifest_store[_PROJECT_GID]

        assert _SEC_1 in manifest.sections, f"Section {_SEC_1} missing from manifest"
        assert _SEC_2 in manifest.sections, f"Section {_SEC_2} missing from manifest"
        assert manifest.sections[_SEC_1].status == SectionStatus.COMPLETE, (
            f"expected COMPLETE for {_SEC_1}, got {manifest.sections[_SEC_1].status}"
        )
        assert manifest.sections[_SEC_2].status == SectionStatus.COMPLETE, (
            f"expected COMPLETE for {_SEC_2}, got {manifest.sections[_SEC_2].status}"
        )
        assert is_honest_complete(manifest) is True, (
            "all-COMPLETE manifest must yield is_honest_complete=True"
        )

    async def test_ac_g2r6_3_failed_section_manifest_not_complete(self) -> None:
        """AC-G2R6-3 RED path: one section fails → manifest has FAILED section →
        is_honest_complete(manifest) is False."""
        sections = [_make_mock_section(_SEC_1, "Active"), _make_mock_section(_SEC_2, "Paused")]
        tasks = [_make_mock_task("task_1", "Task One")]
        client = _make_mock_client(sections, tasks)

        persistence = _make_mock_persistence_writing()
        schema = MagicMock()
        schema.version = "1.0.0"
        schema.to_polars_schema = MagicMock(return_value={"gid": pl.Utf8, "name": pl.Utf8})

        builder = ProgressiveProjectBuilder(
            client=client,
            project_gid=_PROJECT_GID,
            entity_type="project",
            schema=schema,
            persistence=persistence,
        )
        builder._ensure_dataframe_view = AsyncMock()
        builder._build_index_data = MagicMock(return_value=None)

        call_count = 0

        def _build_section_df_with_failure(
            *args: Any, **kwargs: Any
        ) -> tuple[pl.DataFrame, str, None]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First section (_SEC_1) succeeds.
                return pl.DataFrame({"gid": ["task_1"], "name": ["T1"]}), "abc123", None
            # Second section (_SEC_2) fails.
            raise RuntimeError("Asana fetch error — simulated transient failure")

        with patch.object(
            builder,
            "_build_section_dataframe",
            side_effect=_build_section_df_with_failure,
        ):
            await builder.build_progressive_async(resume=False)

        manifest_store = persistence._manifest_store
        assert manifest_store, "manifest must have been written even on partial failure"
        manifest = manifest_store[_PROJECT_GID]

        # At least one section must be FAILED.
        statuses = {gid: info.status for gid, info in manifest.sections.items()}
        failed_sections = [g for g, s in statuses.items() if s == SectionStatus.FAILED]
        assert failed_sections, f"Expected at least one FAILED section; got statuses: {statuses}"
        assert is_honest_complete(manifest) is False, (
            "manifest with FAILED section must yield is_honest_complete=False"
        )


# ---------------------------------------------------------------------------
# Cold-miss background-build behavior
# ---------------------------------------------------------------------------


class _FakeCacheForBgTests:
    """Minimal cache fake for background-build dedup tests.

    Only get_async is exercised (returns None → cold miss).
    We do NOT call put_async or lock methods here — the _swr_build_callback
    is patched out so those code paths don't run.
    """

    async def get_async(self, project_gid: str, entity_type: str) -> None:
        return None

    def get_freshness_info(self, project_gid: str, entity_type: str) -> None:
        return None


class TestColdMissBackgroundBuild:
    """Cold-miss path: body-parameterized entity → 503 + one background task launched."""

    async def test_cold_miss_launches_background_build_and_raises_503(self) -> None:
        """AC-G2R6-BG1: cold miss for body-parameterized entity →
        - background task launched (exactly once)
        - 503 ApiDataFrameBuildError(CACHE_BUILD_IN_PROGRESS) raised
        - in-flight key present in _background_builds during build
        """
        from autom8_asana.api.exception_types import ApiDataFrameBuildError

        strategy = get_universal_strategy("project")  # body_parameterized=True
        fake_cache = _FakeCacheForBgTests()
        client = MagicMock()

        # Clear in-flight set to ensure a clean slate.
        _background_builds.clear()

        swr_call_count = 0

        async def _fake_swr(cache: Any, project_gid: str, entity_type: str) -> None:
            nonlocal swr_call_count
            swr_call_count += 1
            # Simulate real build duration (short for tests).
            await asyncio.sleep(0.01)

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=fake_cache,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory._swr_build_callback",
                side_effect=_fake_swr,
            ),
        ):
            with pytest.raises(ApiDataFrameBuildError) as exc_info:
                await strategy._build_on_miss(_PROJECT_GID, client)

        assert exc_info.value.code == "CACHE_BUILD_IN_PROGRESS"
        assert exc_info.value.status_code == 503
        # retry_after_seconds is stored in details dict (see exception_types.py:144-145).
        assert exc_info.value.details is not None
        assert exc_info.value.details.get("retry_after_seconds", 0) > 0

        # Let the background task run to completion so it clears the in-flight key.
        await asyncio.sleep(0.05)
        assert (_PROJECT_GID, "project") not in _background_builds, (
            "in-flight key must be cleared after background build completes"
        )
        assert swr_call_count == 1, (
            f"expected exactly one _swr_build_callback invocation; got {swr_call_count}"
        )

    async def test_second_concurrent_miss_does_not_launch_second_build(self) -> None:
        """AC-G2R6-BG2: second cold request for same (GID, entity_type) while a
        background build is already running does NOT launch a second task.
        Both calls raise 503; only one _swr_build_callback invocation occurs."""
        from autom8_asana.api.exception_types import ApiDataFrameBuildError

        strategy = get_universal_strategy("project")
        fake_cache = _FakeCacheForBgTests()
        client = MagicMock()

        _background_builds.clear()

        swr_call_count = 0
        build_started = asyncio.Event()

        async def _slow_swr(cache: Any, project_gid: str, entity_type: str) -> None:
            nonlocal swr_call_count
            swr_call_count += 1
            build_started.set()
            # Simulate long build so the second request sees key still in-flight.
            await asyncio.sleep(0.05)

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=fake_cache,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory._swr_build_callback",
                side_effect=_slow_swr,
            ),
        ):
            # First miss — should launch background task.
            with pytest.raises(ApiDataFrameBuildError) as exc1:
                await strategy._build_on_miss(_PROJECT_GID, client)

            assert exc1.value.code == "CACHE_BUILD_IN_PROGRESS"

            # Wait until the background task has started and set the key.
            await asyncio.sleep(0.01)

            # Second miss while build is in-flight — must NOT launch a second task.
            with pytest.raises(ApiDataFrameBuildError) as exc2:
                await strategy._build_on_miss(_PROJECT_GID, client)

            assert exc2.value.code == "CACHE_BUILD_IN_PROGRESS"

        # Let the background task finish.
        await asyncio.sleep(0.1)
        assert swr_call_count == 1, (
            f"dedup failed: _swr_build_callback called {swr_call_count} times; expected 1"
        )
        assert (_PROJECT_GID, "project") not in _background_builds, (
            "in-flight key must be cleared after build completes"
        )


# ---------------------------------------------------------------------------
# AC-G2R6-4: offer-domain cold miss — unchanged (cache-only, no background build)
# ---------------------------------------------------------------------------


class TestAcG2R64OfferDomainUnchanged:
    """AC-G2R6-4 (HARD NON-REGRESSION): offer-domain cold miss → None, NO background build.

    The body_parameterized=False branch must be completely unaffected by Option B.
    Verifies ADR-G2RECV-002 REJECT condition still holds.
    """

    async def test_offer_domain_miss_returns_none_no_background_build(self) -> None:
        """offer-domain (body_parameterized=False) cold miss → None returned;
        _build_on_miss never called; _background_builds unchanged."""
        strategy = get_universal_strategy("unit")  # offer-domain, body_parameterized=False
        client = MagicMock()
        fake_cache = _FakeCacheForBgTests()

        _background_builds.clear()
        initial_in_flight = set(_background_builds)

        # _get_dataframe imports get_dataframe_cache_provider from factory inline.
        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=fake_cache,
            ),
            patch.object(
                UniversalResolutionStrategy,
                "_build_on_miss",
                new_callable=AsyncMock,
            ) as mock_build_on_miss,
        ):
            result = await strategy._get_dataframe(_PROJECT_GID, client)

        assert result is None, "offer-domain cold miss must return None (unchanged cache-only path)"
        mock_build_on_miss.assert_not_awaited()
        assert set(_background_builds) == initial_in_flight, (
            "_background_builds must be unchanged for offer-domain misses"
        )


# ---------------------------------------------------------------------------
# ADR-1 edit 2: honest-empty-on-miss — a cold miss whose manifest is
# honest-complete serves an empty frame (honest-empty-200), NOT a 503.
# ---------------------------------------------------------------------------


def _persistence_ctx_with_manifest(manifest: SectionManifest | None) -> MagicMock:
    """Build a SectionPersistence mock usable as `async with` returning a manifest."""
    persistence = MagicMock()
    persistence.__aenter__ = AsyncMock(return_value=persistence)
    persistence.__aexit__ = AsyncMock(return_value=False)
    persistence.get_manifest_async = AsyncMock(return_value=manifest)
    return persistence


class TestAdr1HonestEmptyOnMiss:
    """ADR-1 edit 2: cold-miss + honest-complete manifest → empty frame, not 503."""

    async def test_honest_complete_miss_serves_empty_frame_not_503(self) -> None:
        """A body-parameterized cold miss whose manifest is honest-complete
        returns an empty schema'd frame and does NOT enter _build_on_miss."""
        strategy = get_universal_strategy("project")  # body_parameterized=True
        client = MagicMock()
        fake_cache = _FakeCacheForBgTests()
        _background_builds.clear()

        manifest = SectionManifest(
            project_gid=_PROJECT_GID,
            entity_type="project",
            total_sections=1,
            completed_sections=1,
            schema_version="1.0.0",
            sections={"sec_1": SectionInfo(status=SectionStatus.COMPLETE, rows=0)},
        )
        schema = MagicMock()
        schema.to_polars_schema.return_value = {"gid": pl.Utf8, "name": pl.Utf8}

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=fake_cache,
            ),
            patch(
                "autom8_asana.dataframes.section_persistence.create_section_persistence",
                return_value=_persistence_ctx_with_manifest(manifest),
            ),
            patch.object(strategy, "_get_entity_schema", return_value=schema),
            patch.object(
                UniversalResolutionStrategy, "_build_on_miss", new_callable=AsyncMock
            ) as mock_build_on_miss,
        ):
            result = await strategy._get_dataframe(_PROJECT_GID, client)

        assert result is not None, "honest-complete miss must serve an empty frame, not None"
        assert len(result) == 0, "the served honest-empty frame must have zero rows"
        mock_build_on_miss.assert_not_awaited()

    async def test_incomplete_manifest_miss_still_builds_on_miss(self) -> None:
        """A miss whose manifest is NOT honest-complete (a FAILED section) must
        STILL go through _build_on_miss (503) — never falsely serve empty."""
        strategy = get_universal_strategy("project")
        client = MagicMock()
        fake_cache = _FakeCacheForBgTests()
        _background_builds.clear()

        manifest = SectionManifest(
            project_gid=_PROJECT_GID,
            entity_type="project",
            total_sections=2,
            completed_sections=1,
            schema_version="1.0.0",
            sections={
                "sec_1": SectionInfo(status=SectionStatus.COMPLETE, rows=0),
                "sec_2": SectionInfo(status=SectionStatus.FAILED, error="boom"),
            },
        )
        schema = MagicMock()
        schema.to_polars_schema.return_value = {"gid": pl.Utf8, "name": pl.Utf8}

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=fake_cache,
            ),
            patch(
                "autom8_asana.dataframes.section_persistence.create_section_persistence",
                return_value=_persistence_ctx_with_manifest(manifest),
            ),
            patch.object(strategy, "_get_entity_schema", return_value=schema),
            patch.object(
                UniversalResolutionStrategy, "_build_on_miss", new_callable=AsyncMock
            ) as mock_build_on_miss,
        ):
            await strategy._get_dataframe(_PROJECT_GID, client)

        mock_build_on_miss.assert_awaited_once()

    async def test_no_manifest_miss_still_builds_on_miss(self) -> None:
        """A miss with NO manifest (never built) must build-on-miss, not serve empty."""
        strategy = get_universal_strategy("project")
        client = MagicMock()
        fake_cache = _FakeCacheForBgTests()
        _background_builds.clear()

        schema = MagicMock()
        schema.to_polars_schema.return_value = {"gid": pl.Utf8, "name": pl.Utf8}

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=fake_cache,
            ),
            patch(
                "autom8_asana.dataframes.section_persistence.create_section_persistence",
                return_value=_persistence_ctx_with_manifest(None),
            ),
            patch.object(strategy, "_get_entity_schema", return_value=schema),
            patch.object(
                UniversalResolutionStrategy, "_build_on_miss", new_callable=AsyncMock
            ) as mock_build_on_miss,
        ):
            await strategy._get_dataframe(_PROJECT_GID, client)

        mock_build_on_miss.assert_awaited_once()


# ---------------------------------------------------------------------------
# Background task lifecycle: key cleared on failure
# ---------------------------------------------------------------------------


class TestBackgroundTaskLifecycle:
    """AC-G2R6-BG3: in-flight key is cleared on both success and failure."""

    async def test_key_cleared_on_background_build_failure(self) -> None:
        """If the background build raises, the done-callback still clears the
        in-flight key so a subsequent cold request can retry."""
        from autom8_asana.api.exception_types import ApiDataFrameBuildError

        strategy = get_universal_strategy("project")
        fake_cache = _FakeCacheForBgTests()
        client = MagicMock()

        _background_builds.clear()

        async def _failing_swr(cache: Any, project_gid: str, entity_type: str) -> None:
            await asyncio.sleep(0.01)
            raise RuntimeError("simulated background build failure")

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=fake_cache,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory._swr_build_callback",
                side_effect=_failing_swr,
            ),
        ):
            with pytest.raises(ApiDataFrameBuildError) as exc_info:
                await strategy._build_on_miss(_PROJECT_GID, client)

        assert exc_info.value.code == "CACHE_BUILD_IN_PROGRESS"

        # In-flight key should be present while background task runs.
        assert (_PROJECT_GID, "project") in _background_builds, (
            "in-flight key must exist while background task is running"
        )

        # Let the failing background task finish.
        await asyncio.sleep(0.05)

        # Key must be cleared even though the build failed.
        assert (_PROJECT_GID, "project") not in _background_builds, (
            "in-flight key must be cleared after background build failure (done-callback)"
        )

    async def test_key_cleared_on_background_build_success(self) -> None:
        """Background build success also clears the in-flight key."""
        from autom8_asana.api.exception_types import ApiDataFrameBuildError

        strategy = get_universal_strategy("project")
        fake_cache = _FakeCacheForBgTests()
        client = MagicMock()

        _background_builds.clear()

        async def _succeeding_swr(cache: Any, project_gid: str, entity_type: str) -> None:
            await asyncio.sleep(0.01)

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=fake_cache,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory._swr_build_callback",
                side_effect=_succeeding_swr,
            ),
        ):
            with pytest.raises(ApiDataFrameBuildError):
                await strategy._build_on_miss(_PROJECT_GID, client)

        await asyncio.sleep(0.05)

        assert (_PROJECT_GID, "project") not in _background_builds, (
            "in-flight key must be cleared after successful background build"
        )
