"""Unit tests for SectionInfo backward compatibility.

Tests that the new checkpoint tracking fields on SectionInfo are
backward compatible with existing manifests per TDD-large-section-resilience
section 9.3.
"""

from __future__ import annotations


from autom8_asana.dataframes.section_persistence import (
    SectionInfo,
    SectionManifest,
    SectionStatus,
)


class TestSectionInfoDefaults:
    """New fields should default to 0."""

    def test_section_info_defaults(self) -> None:
        """SectionInfo() has last_fetched_offset=0, rows_fetched=0, chunks_checkpointed=0."""
        info = SectionInfo()

        assert info.last_fetched_offset == 0
        assert info.rows_fetched == 0
        assert info.chunks_checkpointed == 0

    def test_section_info_with_values(self) -> None:
        """SectionInfo can be created with explicit checkpoint values."""
        info = SectionInfo(
            status=SectionStatus.IN_PROGRESS,
            last_fetched_offset=50,
            rows_fetched=5000,
            chunks_checkpointed=1,
        )

        assert info.last_fetched_offset == 50
        assert info.rows_fetched == 5000
        assert info.chunks_checkpointed == 1


class TestSectionInfoFromLegacyDict:
    """Dicts without new fields should parse with defaults."""

    def test_section_info_from_legacy_dict(self) -> None:
        """Dict without new fields parses successfully with defaults."""
        legacy_dict = {
            "status": "in_progress",
            "rows": 100,
            "written_at": None,
            "error": None,
            "watermark": None,
            "gid_hash": None,
            "name": "Test Section",
        }

        info = SectionInfo.model_validate(legacy_dict)

        assert info.status == SectionStatus.IN_PROGRESS
        assert info.rows == 100
        assert info.name == "Test Section"
        # New fields should default to 0
        assert info.last_fetched_offset == 0
        assert info.rows_fetched == 0
        assert info.chunks_checkpointed == 0

    def test_section_info_from_minimal_dict(self) -> None:
        """Minimal dict (just status) parses with all defaults."""
        minimal_dict = {"status": "pending"}

        info = SectionInfo.model_validate(minimal_dict)

        assert info.status == SectionStatus.PENDING
        assert info.last_fetched_offset == 0
        assert info.rows_fetched == 0
        assert info.chunks_checkpointed == 0


class TestManifestMixedSectionInfos:
    """Manifest with mix of old and new SectionInfo entries."""

    def test_manifest_mixed_section_infos(self) -> None:
        """Manifest with mixed old/new SectionInfo entries parses correctly."""
        manifest_dict = {
            "project_gid": "proj_123",
            "entity_type": "contact",
            "total_sections": 3,
            "completed_sections": 1,
            "version": 1,
            "schema_version": "1.0.0",
            "sections": {
                # Old-style section (no checkpoint fields)
                "sec_1": {
                    "status": "complete",
                    "rows": 50,
                    "name": "Small Section",
                },
                # New-style section with checkpoint fields
                "sec_2": {
                    "status": "in_progress",
                    "rows": 0,
                    "name": "Large Section",
                    "last_fetched_offset": 100,
                    "rows_fetched": 10000,
                    "chunks_checkpointed": 2,
                },
                # Pending section (no checkpoint fields)
                "sec_3": {
                    "status": "pending",
                    "name": "Queued Section",
                },
            },
        }

        manifest = SectionManifest.model_validate(manifest_dict)

        # Old section has defaults
        assert manifest.sections["sec_1"].last_fetched_offset == 0
        assert manifest.sections["sec_1"].rows_fetched == 0
        assert manifest.sections["sec_1"].chunks_checkpointed == 0

        # New section has explicit values
        assert manifest.sections["sec_2"].last_fetched_offset == 100
        assert manifest.sections["sec_2"].rows_fetched == 10000
        assert manifest.sections["sec_2"].chunks_checkpointed == 2

        # Pending section has defaults
        assert manifest.sections["sec_3"].last_fetched_offset == 0
        assert manifest.sections["sec_3"].rows_fetched == 0
        assert manifest.sections["sec_3"].chunks_checkpointed == 0

    def test_manifest_version_unchanged(self) -> None:
        """Manifest version stays at 1 (no bump for additive fields)."""
        manifest = SectionManifest(
            project_gid="proj_123",
            entity_type="contact",
            total_sections=1,
            sections={"sec_1": SectionInfo()},
        )
        assert manifest.version == 1
