"""Unit tests for SectionPersistence with DataFrameStorage delegation.

Per TDD-UNIFIED-DF-PERSISTENCE-001 Phase 2:
Verifies SectionPersistence delegates S3 I/O to DataFrameStorage
when the storage parameter is provided at construction.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from autom8_asana.dataframes.section_persistence import (
    SectionInfo,
    SectionManifest,
    SectionPersistence,
    SectionStatus,
)


def _make_mock_storage() -> MagicMock:
    """Create a mock DataFrameStorage with async methods."""
    storage = MagicMock()
    storage.is_available = True
    storage.save_json = AsyncMock(return_value=True)
    storage.load_json = AsyncMock(return_value=None)
    storage.save_section = AsyncMock(return_value=True)
    storage.load_section = AsyncMock(return_value=None)
    storage.delete_section = AsyncMock(return_value=True)
    storage.delete_object = AsyncMock(return_value=True)
    storage.save_dataframe = AsyncMock(return_value=True)
    storage.save_index = AsyncMock(return_value=True)
    return storage


def _make_df() -> pl.DataFrame:
    """Create a simple test DataFrame."""
    return pl.DataFrame({"gid": ["123", "456"], "name": ["Task A", "Task B"]})


def _make_persistence(
    storage: MagicMock | None = None,
) -> SectionPersistence:
    """Create SectionPersistence with storage injection."""
    if storage is None:
        storage = _make_mock_storage()
    return SectionPersistence(storage=storage)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestStorageConstruction:
    """Test that SectionPersistence correctly accepts storage parameter."""

    def test_with_storage_assigned(self) -> None:
        """Storage is assigned to _storage on construction."""
        storage = _make_mock_storage()
        persistence = _make_persistence(storage=storage)

        assert persistence._storage is storage

    def test_is_available_delegates_to_storage(self) -> None:
        """is_available checks storage.is_available."""
        storage = _make_mock_storage()
        persistence = _make_persistence(storage=storage)

        assert persistence.is_available is True

        storage.is_available = False
        assert persistence.is_available is False


# ---------------------------------------------------------------------------
# Context Manager
# ---------------------------------------------------------------------------


class TestStorageContextManager:
    """Test async context manager with storage path."""

    @pytest.mark.asyncio()
    async def test_context_manager_noop(self) -> None:
        """Context manager enter/exit are no-ops (storage manages lifecycle)."""
        storage = _make_mock_storage()
        persistence = _make_persistence(storage=storage)

        async with persistence as p:
            assert p._storage is storage


# ---------------------------------------------------------------------------
# Manifest Operations via Storage
# ---------------------------------------------------------------------------


class TestManifestViaStorage:
    """Test manifest CRUD operations delegated to DataFrameStorage."""

    @pytest.mark.asyncio()
    async def test_create_manifest_saves_via_storage(self) -> None:
        """create_manifest_async writes manifest JSON via storage.save_json."""
        storage = _make_mock_storage()
        persistence = _make_persistence(storage=storage)

        manifest = await persistence.create_manifest_async("proj_123", "offer", ["sec_1", "sec_2"])

        assert manifest.project_gid == "proj_123"
        assert manifest.total_sections == 2
        storage.save_json.assert_called_once()

        # Verify key format
        call_key = storage.save_json.call_args[0][0]
        assert call_key == "dataframes/proj_123/manifest.json"

    @pytest.mark.asyncio()
    async def test_get_manifest_loads_via_storage(self) -> None:
        """get_manifest_async reads manifest JSON via storage.load_json."""
        storage = _make_mock_storage()
        manifest_data = {
            "project_gid": "proj_123",
            "entity_type": "offer",
            "sections": {"sec_1": {"status": "pending"}},
            "total_sections": 1,
            "completed_sections": 0,
            "version": 1,
        }
        storage.load_json = AsyncMock(return_value=json.dumps(manifest_data).encode("utf-8"))

        persistence = _make_persistence(storage=storage)
        manifest = await persistence.get_manifest_async("proj_123")

        assert manifest is not None
        assert manifest.project_gid == "proj_123"
        assert "sec_1" in manifest.sections
        storage.load_json.assert_called_once_with("dataframes/proj_123/manifest.json")

    @pytest.mark.asyncio()
    async def test_get_manifest_returns_none_when_not_found(self) -> None:
        """get_manifest_async returns None when storage.load_json returns None."""
        storage = _make_mock_storage()
        storage.load_json = AsyncMock(return_value=None)

        persistence = _make_persistence(storage=storage)
        manifest = await persistence.get_manifest_async("proj_missing")

        assert manifest is None

    @pytest.mark.asyncio()
    async def test_delete_manifest_via_storage(self) -> None:
        """delete_manifest_async delegates to storage.delete_object."""
        storage = _make_mock_storage()
        persistence = _make_persistence(storage=storage)

        result = await persistence.delete_manifest_async("proj_123")

        assert result is True
        storage.delete_object.assert_called_once_with("dataframes/proj_123/manifest.json")


# ---------------------------------------------------------------------------
# Section Write via Storage
# ---------------------------------------------------------------------------


class TestSectionWriteViaStorage:
    """Test section DataFrame write operations delegated to storage."""

    @pytest.mark.asyncio()
    async def test_write_section_delegates_to_storage(self) -> None:
        """write_section_async calls storage.save_section."""
        storage = _make_mock_storage()
        persistence = _make_persistence(storage=storage)

        # Pre-populate manifest in cache so update_manifest doesn't fail
        persistence._manifest_cache["proj_123"] = SectionManifest(
            project_gid="proj_123",
            entity_type="offer",
            total_sections=1,
            sections={"sec_1": {}},
        )

        df = _make_df()
        result = await persistence.write_section_async("proj_123", "sec_1", df)

        assert result is True
        storage.save_section.assert_called_once()

        call_args = storage.save_section.call_args
        assert call_args[0][0] == "proj_123"
        assert call_args[0][1] == "sec_1"
        # Third positional arg is the DataFrame
        assert isinstance(call_args[0][2], pl.DataFrame)

    @pytest.mark.asyncio()
    async def test_write_section_failure_marks_manifest_failed(self) -> None:
        """When storage.save_section returns False, manifest is marked FAILED."""
        storage = _make_mock_storage()
        storage.save_section = AsyncMock(return_value=False)

        persistence = _make_persistence(storage=storage)
        persistence._manifest_cache["proj_123"] = SectionManifest(
            project_gid="proj_123",
            entity_type="offer",
            total_sections=1,
            sections={"sec_1": {}},
        )

        df = _make_df()
        result = await persistence.write_section_async("proj_123", "sec_1", df)

        assert result is False
        # Manifest should show failed
        manifest = persistence._manifest_cache["proj_123"]
        assert manifest.sections["sec_1"].status == SectionStatus.FAILED


# ---------------------------------------------------------------------------
# Section Read via Storage
# ---------------------------------------------------------------------------


class TestSectionReadViaStorage:
    """Test section DataFrame read operations delegated to storage."""

    @pytest.mark.asyncio()
    async def test_read_section_delegates_to_storage(self) -> None:
        """read_section_async calls storage.load_section."""
        storage = _make_mock_storage()
        expected_df = _make_df()
        storage.load_section = AsyncMock(return_value=expected_df)

        persistence = _make_persistence(storage=storage)
        df = await persistence.read_section_async("proj_123", "sec_1")

        assert df is expected_df
        storage.load_section.assert_called_once_with("proj_123", "sec_1")

    @pytest.mark.asyncio()
    async def test_read_section_returns_none_when_not_found(self) -> None:
        """read_section_async returns None when storage returns None."""
        storage = _make_mock_storage()
        storage.load_section = AsyncMock(return_value=None)

        persistence = _make_persistence(storage=storage)
        df = await persistence.read_section_async("proj_123", "sec_missing")

        assert df is None


# ---------------------------------------------------------------------------
# Checkpoint via Storage
# ---------------------------------------------------------------------------


class TestCheckpointViaStorage:
    """Test checkpoint writes delegated to storage."""

    @pytest.mark.asyncio()
    async def test_write_checkpoint_delegates_to_storage(self) -> None:
        """write_checkpoint_async calls storage.save_section with checkpoint metadata."""
        storage = _make_mock_storage()
        persistence = _make_persistence(storage=storage)

        # Pre-populate manifest
        persistence._manifest_cache["proj_123"] = SectionManifest(
            project_gid="proj_123",
            entity_type="offer",
            total_sections=1,
            sections={"sec_1": {"status": "in_progress"}},
        )

        df = _make_df()
        result = await persistence.write_checkpoint_async(
            "proj_123", "sec_1", df, pages_fetched=5, rows_fetched=100
        )

        assert result is True
        storage.save_section.assert_called_once()

        # Verify checkpoint metadata is passed
        call_kwargs = storage.save_section.call_args[1]
        assert call_kwargs["metadata"]["checkpoint"] == "true"
        assert call_kwargs["metadata"]["pages-fetched"] == "5"


# ---------------------------------------------------------------------------
# Final Artifacts via Storage
# ---------------------------------------------------------------------------


class TestFinalArtifactsViaStorage:
    """Test write_final_artifacts_async delegation to storage."""

    @pytest.mark.asyncio()
    async def test_write_final_artifacts_delegates_to_storage(self) -> None:
        """write_final_artifacts_async calls storage.save_dataframe and save_index."""
        storage = _make_mock_storage()
        persistence = _make_persistence(storage=storage)

        df = _make_df()
        watermark = datetime(2026, 2, 4, 12, 0, 0, tzinfo=UTC)
        index_data = {"by_phone": {"+15551234": "task_123"}}

        result = await persistence.write_final_artifacts_async(
            "proj_123", df, watermark, index_data=index_data, entity_type="offer"
        )

        assert result is True
        storage.save_dataframe.assert_called_once_with(
            "proj_123", df, watermark, entity_type="offer"
        )
        storage.save_index.assert_called_once_with("proj_123", index_data)

    @pytest.mark.asyncio()
    async def test_write_final_artifacts_without_index(self) -> None:
        """write_final_artifacts_async works without index data."""
        storage = _make_mock_storage()
        persistence = _make_persistence(storage=storage)

        df = _make_df()
        watermark = datetime(2026, 2, 4, 12, 0, 0, tzinfo=UTC)

        result = await persistence.write_final_artifacts_async("proj_123", df, watermark)

        assert result is True
        storage.save_dataframe.assert_called_once()
        storage.save_index.assert_not_called()


# ---------------------------------------------------------------------------
# Delete Operations via Storage
# ---------------------------------------------------------------------------


class TestDeleteViaStorage:
    """Test delete operations delegated to storage."""

    @pytest.mark.asyncio()
    async def test_delete_section_files_delegates_to_storage(self) -> None:
        """delete_section_files_async uses storage.delete_section."""
        storage = _make_mock_storage()
        manifest_data = {
            "project_gid": "proj_123",
            "entity_type": "offer",
            "sections": {
                "sec_1": {"status": "complete"},
                "sec_2": {"status": "complete"},
            },
            "total_sections": 2,
            "completed_sections": 2,
            "version": 1,
        }
        storage.load_json = AsyncMock(return_value=json.dumps(manifest_data).encode("utf-8"))

        persistence = _make_persistence(storage=storage)
        result = await persistence.delete_section_files_async("proj_123")

        assert result is True
        assert storage.delete_section.call_count == 2


# ---------------------------------------------------------------------------
# Hotfix: IN_PROGRESS stale timeout (ADR-HOTFIX-001)
# ---------------------------------------------------------------------------


class TestIncompleteGidsStaleInProgress:
    """Tests for get_incomplete_section_gids with stale IN_PROGRESS recovery."""

    def test_get_incomplete_section_gids_includes_stale_in_progress(self) -> None:
        """IN_PROGRESS section with in_progress_since 10 min ago appears in results."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="offer",
            total_sections=2,
            sections={
                "sec_ok": SectionInfo(status=SectionStatus.COMPLETE, rows=10),
                "sec_stuck": SectionInfo(
                    status=SectionStatus.IN_PROGRESS,
                    in_progress_since=datetime.now(UTC) - timedelta(minutes=10),
                ),
            },
        )
        incomplete = manifest.get_incomplete_section_gids()
        assert "sec_stuck" in incomplete

    def test_get_incomplete_section_gids_excludes_fresh_in_progress(self) -> None:
        """IN_PROGRESS section with in_progress_since 30 sec ago is NOT in results."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="offer",
            total_sections=2,
            sections={
                "sec_ok": SectionInfo(status=SectionStatus.COMPLETE, rows=10),
                "sec_fresh": SectionInfo(
                    status=SectionStatus.IN_PROGRESS,
                    in_progress_since=datetime.now(UTC) - timedelta(seconds=30),
                ),
            },
        )
        incomplete = manifest.get_incomplete_section_gids()
        assert "sec_fresh" not in incomplete

    def test_get_incomplete_section_gids_includes_legacy_in_progress(self) -> None:
        """IN_PROGRESS with in_progress_since=None (legacy) appears in results."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="offer",
            total_sections=2,
            sections={
                "sec_ok": SectionInfo(status=SectionStatus.COMPLETE, rows=10),
                "sec_legacy": SectionInfo(
                    status=SectionStatus.IN_PROGRESS,
                    in_progress_since=None,
                ),
            },
        )
        incomplete = manifest.get_incomplete_section_gids()
        assert "sec_legacy" in incomplete

    def test_pending_and_failed_still_included(self) -> None:
        """PENDING and FAILED sections remain in results (existing behavior)."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="offer",
            total_sections=3,
            sections={
                "sec_pending": SectionInfo(status=SectionStatus.PENDING),
                "sec_failed": SectionInfo(status=SectionStatus.FAILED, error="timeout"),
                "sec_ok": SectionInfo(status=SectionStatus.COMPLETE, rows=5),
            },
        )
        incomplete = manifest.get_incomplete_section_gids()
        assert "sec_pending" in incomplete
        assert "sec_failed" in incomplete
        assert "sec_ok" not in incomplete


class TestMarkSectionInProgressTimestamp:
    """Tests for mark_section_in_progress setting in_progress_since."""

    def test_mark_section_in_progress_sets_timestamp(self) -> None:
        """Verify in_progress_since is set to approximately now."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="offer",
            total_sections=1,
            sections={"sec_1": SectionInfo(status=SectionStatus.PENDING)},
        )
        before = datetime.now(UTC)
        manifest.mark_section_in_progress("sec_1")
        after = datetime.now(UTC)

        info = manifest.sections["sec_1"]
        assert info.status == SectionStatus.IN_PROGRESS
        assert info.in_progress_since is not None
        assert before <= info.in_progress_since <= after

    def test_mark_section_in_progress_new_section_sets_timestamp(self) -> None:
        """New section (not already in manifest) also gets in_progress_since."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="offer",
            total_sections=1,
            sections={},
        )
        before = datetime.now(UTC)
        manifest.mark_section_in_progress("sec_new")
        after = datetime.now(UTC)

        info = manifest.sections["sec_new"]
        assert info.status == SectionStatus.IN_PROGRESS
        assert info.in_progress_since is not None
        assert before <= info.in_progress_since <= after


class TestSectionInfoBackwardCompat:
    """Tests for SectionInfo backward compatibility with legacy manifests."""

    def test_section_info_backward_compat(self) -> None:
        """Deserialize JSON without in_progress_since loads as None."""
        legacy_data = {
            "status": "in_progress",
            "rows": 0,
            "written_at": None,
            "error": None,
            "watermark": None,
            "gid_hash": None,
            "name": "Sales Process",
            "last_fetched_offset": 5,
            "rows_fetched": 100,
            "chunks_checkpointed": 2,
        }
        info = SectionInfo.model_validate(legacy_data)
        assert info.in_progress_since is None
        assert info.status == SectionStatus.IN_PROGRESS
        assert info.name == "Sales Process"

    def test_section_info_with_in_progress_since(self) -> None:
        """Deserialize JSON with in_progress_since roundtrips correctly."""
        now = datetime.now(UTC)
        info = SectionInfo(
            status=SectionStatus.IN_PROGRESS,
            in_progress_since=now,
        )
        dumped = json.loads(info.model_dump_json())
        restored = SectionInfo.model_validate(dumped)
        assert restored.in_progress_since is not None
        # Timestamps may lose microsecond precision in JSON roundtrip
        assert abs((restored.in_progress_since - now).total_seconds()) < 1
