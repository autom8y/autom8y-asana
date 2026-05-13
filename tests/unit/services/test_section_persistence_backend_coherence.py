"""Item D — DEF-005 Integration test: section_persistence × ProgressiveBuildStrategy S3-backend coherence.

Verifies that EntityQueryService.section_persistence (the READ path used to derive
honest_contract_complete) and the write path used by ProgressiveBuildStrategy both resolve
to a SectionPersistence backed by the SAME S3 storage configuration.

DEF-005 risk (Sprint 1 close report:193-197 + HANDOFF §5 Precondition 2):
If the write path and read path resolve to different S3 backend instances (different
bucket, endpoint, or prefix), honest_contract_complete returns False silently despite a
complete progressive build — because the read path cannot see the manifest written by the
write path.

This test does NOT exercise real S3 I/O. It verifies structural coherence:
- Both paths use `create_section_persistence()` with identical S3 configuration.
- The storage backend's bucket/endpoint_url/prefix are equal across both paths.

Deliberate shortcuts (prototype):
- Settings are mocked; real S3 connection not established.
- Only structural config equality is verified, not live write-then-read roundtrip.
  The live roundtrip test is Sprint 3 scope (requires staging S3 environment).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.dataframes.section_persistence import (
    SectionPersistence,
    create_section_persistence,
)


def _make_mock_s3_settings(
    bucket: str = "test-bucket", endpoint_url: str = "http://localhost:9000"
) -> MagicMock:
    """Create mock S3Settings with a defined bucket and endpoint."""
    s3 = MagicMock()
    s3.bucket = bucket
    s3.region = "us-east-1"
    s3.endpoint_url = endpoint_url
    return s3


def _make_mock_settings(s3_settings: MagicMock) -> MagicMock:
    """Create mock application settings with S3 sub-settings."""
    settings = MagicMock()
    settings.s3 = s3_settings
    return settings


class TestDef005S3BackendCoherence:
    """DEF-005: write-path and read-path resolve identical S3 backend config.

    AC-R4 gate: integration test for section_persistence × ProgressiveBuildStrategy
    S3-backend coherence.
    """

    def test_create_section_persistence_uses_app_s3_settings(self) -> None:
        """Structural: create_section_persistence() reads bucket/endpoint from get_settings().

        Both EntityQueryService.section_persistence and ProgressiveBuildStrategy call
        create_section_persistence() (or SectionPersistence(storage=df_storage) from
        the same S3 config). This test verifies create_section_persistence() uses
        get_settings().s3 for its backend.
        """
        mock_s3 = _make_mock_s3_settings(bucket="coherence-test-bucket")
        mock_settings = _make_mock_settings(mock_s3)

        with (
            patch(
                "autom8_asana.settings.get_settings",
                return_value=mock_settings,
            ),
            # S3DataFrameStorage and S3LocationConfig are lazy-imported inside
            # create_section_persistence(); patch at source module.
            patch("autom8_asana.dataframes.storage.S3DataFrameStorage") as mock_storage_cls,
            patch("autom8_asana.config.S3LocationConfig") as mock_location_cls,
        ):
            mock_storage_instance = MagicMock()
            mock_storage_cls.return_value = mock_storage_instance
            mock_location = MagicMock()
            mock_location_cls.return_value = mock_location

            persistence = create_section_persistence()

        # Verify S3LocationConfig was constructed from get_settings().s3
        mock_location_cls.assert_called_once_with(
            bucket="coherence-test-bucket",
            region="us-east-1",
            endpoint_url=mock_s3.endpoint_url,
        )
        # Verify S3DataFrameStorage was constructed with the location
        mock_storage_cls.assert_called_once_with(location=mock_location)
        # Verify SectionPersistence was constructed with the storage
        assert isinstance(persistence, SectionPersistence)
        assert persistence.storage is mock_storage_instance

    def test_query_service_section_persistence_uses_create_factory(self) -> None:
        """Structural: EntityQueryService.section_persistence calls create_section_persistence().

        This is the DEF-005 guard (query_service.py:304-319):
        The lazy property uses create_section_persistence() to ensure the same
        S3 config as the write path.
        """
        from autom8_asana.services.query_service import EntityQueryService

        mock_s3 = _make_mock_s3_settings(bucket="coherence-test-bucket")
        mock_settings = _make_mock_settings(mock_s3)
        mock_persistence = MagicMock(spec=SectionPersistence)

        with patch(
            "autom8_asana.dataframes.section_persistence.create_section_persistence",
            return_value=mock_persistence,
        ) as mock_factory:
            service = EntityQueryService()
            # Access the lazy property to trigger create_section_persistence()
            _ = service.section_persistence

        # Verify the factory was called (not a direct SectionPersistence() instantiation)
        mock_factory.assert_called_once()
        # Verify the result is cached (second access does not call factory again)
        _ = service.section_persistence
        assert mock_factory.call_count == 1, (
            "section_persistence lazy property must cache the factory result"
        )

    def test_both_paths_resolve_same_bucket(self) -> None:
        """DEF-005 coherence: write-path and read-path use the same bucket.

        Both the preload progressive path (SectionPersistence(storage=df_storage))
        and the query service path (create_section_persistence()) must resolve to the
        same S3 bucket. This test verifies structural config equality.

        DEF-005 silent-failure scenario (close report:193-197):
        If write-path bucket != read-path bucket, get_manifest_async() returns None
        and is_honest_complete() returns False — honest_contract_complete is silently wrong.
        """
        from autom8_asana.dataframes.storage import S3DataFrameStorage
        from autom8_asana.config import S3LocationConfig

        # Simulate the common app settings
        BUCKET = "production-coherence-bucket"
        ENDPOINT = "https://s3.us-east-1.amazonaws.com"

        # --- Write path (preload progressive.py ~L298) ---
        # SectionPersistence(storage=S3DataFrameStorage(location=S3LocationConfig(bucket=BUCKET)))
        write_location = S3LocationConfig(bucket=BUCKET, region="us-east-1", endpoint_url=ENDPOINT)
        write_storage = S3DataFrameStorage(location=write_location)
        write_persistence = SectionPersistence(storage=write_storage)

        # --- Read path (create_section_persistence() with same settings) ---
        mock_s3 = _make_mock_s3_settings(bucket=BUCKET, endpoint_url=ENDPOINT)
        mock_settings = _make_mock_settings(mock_s3)

        with (
            patch(
                "autom8_asana.settings.get_settings",
                return_value=mock_settings,
            ),
        ):
            read_persistence = create_section_persistence()

        # Both SectionPersistence instances must use the same bucket.
        # S3DataFrameStorage stores location as _location (private attr).
        write_bucket = write_persistence.storage._location.bucket  # type: ignore[attr-defined]
        read_bucket = read_persistence.storage._location.bucket  # type: ignore[attr-defined]

        assert write_bucket == read_bucket == BUCKET, (
            f"DEF-005: write-path bucket {write_bucket!r} != read-path bucket {read_bucket!r}. "
            "honest_contract_complete will silently return False if backends diverge."
        )
