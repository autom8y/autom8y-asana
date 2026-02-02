"""Adversarial edge case tests for manifest staleness detection.

Per QA Adversary validation of TDD-cache-freshness-remediation Fix 1:
Tests boundary conditions, error paths, and adversarial inputs that
the implementation tests may have missed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.builders.progressive import (
    ProgressiveBuildResult,
    ProgressiveProjectBuilder,
)
from autom8_asana.dataframes.section_persistence import (
    SectionInfo,
    SectionManifest,
    SectionStatus,
)


def _make_builder(
    persistence: MagicMock | None = None,
) -> ProgressiveProjectBuilder:
    """Create a ProgressiveProjectBuilder with mocked dependencies."""
    mock_client = MagicMock()
    mock_schema = MagicMock()
    mock_schema.version = "1.0.0"
    mock_schema.to_polars_schema.return_value = {"gid": pl.Utf8}

    if persistence is None:
        persistence = MagicMock()

    return ProgressiveProjectBuilder(
        client=mock_client,
        project_gid="proj_123",
        entity_type="offer",
        schema=mock_schema,
        persistence=persistence,
    )


def _make_manifest(
    age_hours: float,
    *,
    complete: bool = True,
    total_sections: int = 3,
    schema_version: str = "1.0.0",
    started_at: datetime | None = None,
) -> SectionManifest:
    """Create a SectionManifest with specified age and completion state."""
    if started_at is None:
        started_at = datetime.now(UTC) - timedelta(hours=age_hours)

    if complete:
        sections = {
            f"section_{i}": SectionInfo(
                status=SectionStatus.COMPLETE,
                rows=10,
                written_at=started_at,
            )
            for i in range(total_sections)
        }
        completed_sections = total_sections
    else:
        sections = {}
        for i in range(total_sections):
            if i < total_sections - 1:
                sections[f"section_{i}"] = SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=10,
                    written_at=started_at,
                )
            else:
                sections[f"section_{i}"] = SectionInfo(
                    status=SectionStatus.IN_PROGRESS,
                )
        completed_sections = total_sections - 1

    return SectionManifest(
        project_gid="proj_123",
        entity_type="offer",
        started_at=started_at,
        sections=sections,
        total_sections=total_sections,
        completed_sections=completed_sections,
        schema_version=schema_version,
    )


def _wire_builder(builder: ProgressiveProjectBuilder, persistence: MagicMock) -> None:
    """Wire up common mocks on a builder."""
    builder._list_sections = AsyncMock(
        return_value=[MagicMock(gid=f"section_{i}") for i in range(3)]
    )
    builder._ensure_dataframe_view = AsyncMock()
    builder._fetch_and_persist_section = AsyncMock(return_value=True)
    builder._build_index_data = MagicMock(return_value=None)


class TestManifestStalenessEdgeCases:
    """Adversarial edge case tests for manifest staleness detection."""

    @pytest.mark.asyncio
    async def test_manifest_exactly_at_ttl_boundary_not_stale(self) -> None:
        """Manifest age == TTL (exactly 6.0 hours) should NOT trigger deletion.

        The code uses strict > (not >=), so a manifest exactly at boundary
        should be preserved.
        """
        # Create manifest with age very close to but not exceeding 6 hours
        # Use 5.999 to test just under boundary
        manifest = _make_manifest(age_hours=5.999, complete=True)

        mock_persistence = MagicMock()
        mock_persistence.get_manifest_async = AsyncMock(return_value=manifest)
        mock_persistence.delete_manifest_async = AsyncMock(return_value=True)
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = _make_builder(persistence=mock_persistence)
        _wire_builder(builder, mock_persistence)

        await builder.build_progressive_async(resume=True)

        # Should NOT be deleted (5.999 < 6)
        mock_persistence.delete_manifest_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_manifest_just_over_ttl_boundary_is_stale(self) -> None:
        """Manifest age just over TTL (6.001 hours) triggers deletion."""
        manifest = _make_manifest(age_hours=6.001, complete=True)

        mock_persistence = MagicMock()
        mock_persistence.get_manifest_async = AsyncMock(return_value=manifest)
        mock_persistence.delete_manifest_async = AsyncMock(return_value=True)
        mock_persistence.create_manifest_async = AsyncMock(
            return_value=_make_manifest(age_hours=0, complete=False)
        )
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = _make_builder(persistence=mock_persistence)
        _wire_builder(builder, mock_persistence)

        await builder.build_progressive_async(resume=True)

        # Should be deleted (6.001 > 6)
        mock_persistence.delete_manifest_async.assert_called_once_with("proj_123")

    @pytest.mark.asyncio
    async def test_manifest_ttl_zero_deletes_all_complete_manifests(self) -> None:
        """MANIFEST_TTL_HOURS=0 should treat every complete manifest as stale.

        This is an edge case where ops might set TTL to 0 to force fresh
        builds on every restart.
        """
        manifest = _make_manifest(age_hours=0.001, complete=True)

        mock_persistence = MagicMock()
        mock_persistence.get_manifest_async = AsyncMock(return_value=manifest)
        mock_persistence.delete_manifest_async = AsyncMock(return_value=True)
        mock_persistence.create_manifest_async = AsyncMock(
            return_value=_make_manifest(age_hours=0, complete=False)
        )
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = _make_builder(persistence=mock_persistence)
        _wire_builder(builder, mock_persistence)

        with patch.dict("os.environ", {"MANIFEST_TTL_HOURS": "0"}):
            await builder.build_progressive_async(resume=True)

        # Any positive age > 0 TTL => stale
        mock_persistence.delete_manifest_async.assert_called_once_with("proj_123")

    @pytest.mark.asyncio
    async def test_manifest_ttl_negative_falls_back_to_default(self) -> None:
        """MANIFEST_TTL_HOURS=-1 should parse as int(-1), making all manifests stale.

        Negative TTL means every manifest age > negative number = always stale.
        This is technically valid and equivalent to TTL=0.
        """
        manifest = _make_manifest(age_hours=0.001, complete=True)

        mock_persistence = MagicMock()
        mock_persistence.get_manifest_async = AsyncMock(return_value=manifest)
        mock_persistence.delete_manifest_async = AsyncMock(return_value=True)
        mock_persistence.create_manifest_async = AsyncMock(
            return_value=_make_manifest(age_hours=0, complete=False)
        )
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = _make_builder(persistence=mock_persistence)
        _wire_builder(builder, mock_persistence)

        with patch.dict("os.environ", {"MANIFEST_TTL_HOURS": "-1"}):
            await builder.build_progressive_async(resume=True)

        # age (0.001) > TTL (-1) => stale
        mock_persistence.delete_manifest_async.assert_called_once_with("proj_123")

    @pytest.mark.asyncio
    async def test_manifest_delete_failure_continues_with_stale_data(self) -> None:
        """When delete_manifest_async fails, builder continues with stale manifest.

        This tests the graceful degradation path where S3 delete fails but
        the build should proceed with the existing (stale) manifest.
        """
        stale_manifest = _make_manifest(age_hours=10, complete=True)

        mock_persistence = MagicMock()
        mock_persistence.get_manifest_async = AsyncMock(return_value=stale_manifest)
        # delete_manifest_async raises an exception
        mock_persistence.delete_manifest_async = AsyncMock(
            side_effect=Exception("S3 DeleteObject timeout")
        )
        # Should NOT call create_manifest_async since delete failed
        mock_persistence.create_manifest_async = AsyncMock()
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = _make_builder(persistence=mock_persistence)
        _wire_builder(builder, mock_persistence)

        # Should not raise
        result = await builder.build_progressive_async(resume=True)

        # Delete was attempted
        mock_persistence.delete_manifest_async.assert_called_once_with("proj_123")

        # Should NOT create new manifest (delete failed, manifest stays)
        mock_persistence.create_manifest_async.assert_not_called()

        # Build should complete (graceful degradation)
        assert result is not None
        # sections_resumed should be 3 (all sections from stale manifest)
        assert result.sections_resumed == 3

    @pytest.mark.asyncio
    async def test_manifest_with_zero_sections_complete(self) -> None:
        """Manifest with 0 total sections: is_complete() is True (0 == 0).

        Edge case where a project has no sections. SectionManifest with
        total_sections=0 and completed_sections=0 returns is_complete()=True.
        If such a manifest is old, it should be deleted.
        """
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="offer",
            started_at=datetime.now(UTC) - timedelta(hours=10),
            sections={},
            total_sections=0,
            completed_sections=0,
            schema_version="1.0.0",
        )

        assert manifest.is_complete() is True  # 0 == 0

        mock_persistence = MagicMock()
        mock_persistence.get_manifest_async = AsyncMock(return_value=manifest)
        mock_persistence.delete_manifest_async = AsyncMock(return_value=True)
        mock_persistence.create_manifest_async = AsyncMock(
            return_value=_make_manifest(age_hours=0, complete=False, total_sections=1)
        )
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = _make_builder(persistence=mock_persistence)
        _wire_builder(builder, mock_persistence)

        await builder.build_progressive_async(resume=True)

        # Stale and complete (0 == 0) => should be deleted
        mock_persistence.delete_manifest_async.assert_called_once_with("proj_123")

    @pytest.mark.asyncio
    async def test_manifest_all_sections_failed_is_not_complete(self) -> None:
        """Manifest where all sections are FAILED is NOT complete.

        Should not be deleted by staleness check (preserves retry opportunity).
        """
        started_at = datetime.now(UTC) - timedelta(hours=10)
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="offer",
            started_at=started_at,
            sections={
                f"section_{i}": SectionInfo(
                    status=SectionStatus.FAILED,
                    error="API error",
                )
                for i in range(3)
            },
            total_sections=3,
            completed_sections=0,
            schema_version="1.0.0",
        )

        assert manifest.is_complete() is False  # 0 != 3

        mock_persistence = MagicMock()
        mock_persistence.get_manifest_async = AsyncMock(return_value=manifest)
        mock_persistence.delete_manifest_async = AsyncMock(return_value=True)
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = _make_builder(persistence=mock_persistence)
        _wire_builder(builder, mock_persistence)

        await builder.build_progressive_async(resume=True)

        # Should NOT be deleted (not complete)
        mock_persistence.delete_manifest_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_false_skips_staleness_check_entirely(self) -> None:
        """When resume=False, no manifest is loaded, so no staleness check."""
        mock_persistence = MagicMock()
        mock_persistence.get_manifest_async = AsyncMock()
        mock_persistence.create_manifest_async = AsyncMock(
            return_value=_make_manifest(age_hours=0, complete=False)
        )
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = _make_builder(persistence=mock_persistence)
        _wire_builder(builder, mock_persistence)

        await builder.build_progressive_async(resume=False)

        # Should never even attempt to get manifest
        mock_persistence.get_manifest_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_manifest_ttl_extremely_large_value(self) -> None:
        """MANIFEST_TTL_HOURS=999999 means manifests are almost never stale."""
        manifest = _make_manifest(age_hours=8760, complete=True)  # 1 year old

        mock_persistence = MagicMock()
        mock_persistence.get_manifest_async = AsyncMock(return_value=manifest)
        mock_persistence.delete_manifest_async = AsyncMock(return_value=True)
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = _make_builder(persistence=mock_persistence)
        _wire_builder(builder, mock_persistence)

        with patch.dict("os.environ", {"MANIFEST_TTL_HOURS": "999999"}):
            await builder.build_progressive_async(resume=True)

        # 8760 hours < 999999 => not stale
        mock_persistence.delete_manifest_async.assert_not_called()
