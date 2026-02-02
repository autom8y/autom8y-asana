"""Unit tests for manifest staleness detection in ProgressiveProjectBuilder.

Per TDD-cache-freshness-remediation Fix 1: Tests for manifest age check
that deletes stale COMPLETE manifests and forces full rebuild.
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
) -> SectionManifest:
    """Create a SectionManifest with specified age and completion state.

    Args:
        age_hours: How many hours old the manifest should be.
        complete: If True, all sections are COMPLETE.
        total_sections: Number of total sections.
        schema_version: Schema version string.
    """
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
        # Some sections in progress
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


class TestManifestStalenessDetection:
    """Tests for manifest staleness detection in build_progressive_async."""

    @pytest.mark.asyncio
    async def test_manifest_stale_triggers_rebuild(self) -> None:
        """Stale COMPLETE manifest is deleted and triggers fresh build."""
        # Manifest older than default TTL (6 hours), all sections COMPLETE
        stale_manifest = _make_manifest(age_hours=10, complete=True)

        mock_persistence = MagicMock()
        mock_persistence.get_manifest_async = AsyncMock(return_value=stale_manifest)
        mock_persistence.delete_manifest_async = AsyncMock(return_value=True)
        mock_persistence.create_manifest_async = AsyncMock(
            return_value=_make_manifest(age_hours=0, complete=False)
        )
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = _make_builder(persistence=mock_persistence)

        # Mock _list_sections and _ensure_dataframe_view
        mock_section = MagicMock()
        mock_section.gid = "section_0"
        builder._list_sections = AsyncMock(return_value=[mock_section])
        builder._ensure_dataframe_view = AsyncMock()

        # Mock _fetch_and_persist_section to simulate successful fetch
        builder._fetch_and_persist_section = AsyncMock(return_value=True)
        builder._build_index_data = MagicMock(return_value=None)

        result = await builder.build_progressive_async(resume=True)

        # Verify stale manifest was deleted
        mock_persistence.delete_manifest_async.assert_called_once_with("proj_123")

        # Verify a new manifest was created (because manifest was set to None)
        mock_persistence.create_manifest_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_manifest_stale_but_incomplete_resumes(self) -> None:
        """Old manifest with IN_PROGRESS sections is NOT deleted."""
        # Manifest older than TTL but NOT complete
        old_incomplete_manifest = _make_manifest(
            age_hours=10, complete=False, total_sections=3
        )

        mock_persistence = MagicMock()
        mock_persistence.get_manifest_async = AsyncMock(
            return_value=old_incomplete_manifest
        )
        mock_persistence.delete_manifest_async = AsyncMock(return_value=True)
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = _make_builder(persistence=mock_persistence)

        mock_section = MagicMock()
        mock_section.gid = "section_2"
        builder._list_sections = AsyncMock(
            return_value=[MagicMock(gid=f"section_{i}") for i in range(3)]
        )
        builder._ensure_dataframe_view = AsyncMock()
        builder._fetch_and_persist_section = AsyncMock(return_value=True)
        builder._build_index_data = MagicMock(return_value=None)

        await builder.build_progressive_async(resume=True)

        # Manifest should NOT have been deleted (not complete)
        # The delete_manifest_async call for schema mismatch should not happen
        # because schema is compatible, and staleness check requires is_complete()
        # Only check that delete was not called for staleness
        # (it was not called at all since schema is compatible and manifest is incomplete)
        mock_persistence.delete_manifest_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_manifest_fresh_resumes_normally(self) -> None:
        """Fresh manifest (under TTL) resumes normally without deletion."""
        # Manifest only 2 hours old (under 6-hour default TTL)
        fresh_manifest = _make_manifest(age_hours=2, complete=True)

        mock_persistence = MagicMock()
        mock_persistence.get_manifest_async = AsyncMock(return_value=fresh_manifest)
        mock_persistence.delete_manifest_async = AsyncMock(return_value=True)
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = _make_builder(persistence=mock_persistence)

        builder._list_sections = AsyncMock(
            return_value=[MagicMock(gid=f"section_{i}") for i in range(3)]
        )
        builder._ensure_dataframe_view = AsyncMock()
        builder._fetch_and_persist_section = AsyncMock(return_value=True)
        builder._build_index_data = MagicMock(return_value=None)

        result = await builder.build_progressive_async(resume=True)

        # Manifest should NOT be deleted
        mock_persistence.delete_manifest_async.assert_not_called()

        # Should have resumed (sections_resumed > 0)
        assert result.sections_resumed == 3

    @pytest.mark.asyncio
    async def test_manifest_ttl_env_var_override(self) -> None:
        """Custom MANIFEST_TTL_HOURS=1 causes 2-hour-old manifest to be stale."""
        manifest = _make_manifest(age_hours=2, complete=True)

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
        builder._list_sections = AsyncMock(
            return_value=[MagicMock(gid="section_0")]
        )
        builder._ensure_dataframe_view = AsyncMock()
        builder._fetch_and_persist_section = AsyncMock(return_value=True)
        builder._build_index_data = MagicMock(return_value=None)

        with patch.dict("os.environ", {"MANIFEST_TTL_HOURS": "1"}):
            await builder.build_progressive_async(resume=True)

        # Manifest should be deleted (2 hours > 1 hour TTL)
        mock_persistence.delete_manifest_async.assert_called_once_with("proj_123")

    @pytest.mark.asyncio
    async def test_manifest_ttl_invalid_env_var(self) -> None:
        """Invalid MANIFEST_TTL_HOURS falls back to default 6."""
        # Manifest 4 hours old - should NOT be stale with default TTL of 6
        manifest = _make_manifest(age_hours=4, complete=True)

        mock_persistence = MagicMock()
        mock_persistence.get_manifest_async = AsyncMock(return_value=manifest)
        mock_persistence.delete_manifest_async = AsyncMock(return_value=True)
        mock_persistence.merge_sections_to_dataframe_async = AsyncMock(
            return_value=pl.DataFrame({"gid": ["1"]})
        )
        mock_persistence.write_final_artifacts_async = AsyncMock(return_value=True)

        builder = _make_builder(persistence=mock_persistence)
        builder._list_sections = AsyncMock(
            return_value=[MagicMock(gid=f"section_{i}") for i in range(3)]
        )
        builder._ensure_dataframe_view = AsyncMock()
        builder._fetch_and_persist_section = AsyncMock(return_value=True)
        builder._build_index_data = MagicMock(return_value=None)

        with patch.dict("os.environ", {"MANIFEST_TTL_HOURS": "abc"}):
            await builder.build_progressive_async(resume=True)

        # With fallback to 6 hours, 4-hour-old manifest should NOT be stale
        mock_persistence.delete_manifest_async.assert_not_called()
