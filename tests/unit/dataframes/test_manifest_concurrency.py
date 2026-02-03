"""Unit tests for manifest concurrency control in SectionPersistence.

Validates that the asyncio.Lock + in-memory cache prevents the
read-modify-write race condition where concurrent section updates
overwrote each other's completion statuses.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from autom8_asana.dataframes.async_s3 import S3ReadResult, S3WriteResult
from autom8_asana.dataframes.section_persistence import (
    SectionManifest,
    SectionPersistence,
    SectionPersistenceConfig,
    SectionStatus,
)


def _make_persistence() -> SectionPersistence:
    """Create a SectionPersistence with mocked S3."""
    config = SectionPersistenceConfig(bucket="test-bucket")
    persistence = SectionPersistence(config=config)
    persistence._s3_client = AsyncMock()
    persistence._s3_client.put_object_async = AsyncMock(
        return_value=S3WriteResult(
            success=True, key="test", size_bytes=100, duration_ms=10.0
        )
    )
    return persistence


@pytest.mark.asyncio
async def test_concurrent_complete_updates_all_preserved() -> None:
    """8 concurrent COMPLETE updates all reflected in manifest.

    This is the core regression test: without the lock, the last writer
    would overwrite all other section statuses.
    """
    persistence = _make_persistence()
    section_gids = [f"sec_{i}" for i in range(8)]

    # Create manifest with 8 sections
    await persistence.create_manifest_async("proj_1", "offer", section_gids)

    # Concurrently mark all 8 as complete
    tasks = [
        persistence.update_manifest_section_async(
            "proj_1", gid, SectionStatus.COMPLETE, rows=(i + 1) * 10
        )
        for i, gid in enumerate(section_gids)
    ]
    results = await asyncio.gather(*tasks)

    # All updates should succeed
    assert all(r is not None for r in results)

    # Get final manifest state
    manifest = await persistence.get_manifest_async("proj_1")
    assert manifest is not None

    # ALL 8 sections must be COMPLETE
    for gid in section_gids:
        assert manifest.sections[gid].status == SectionStatus.COMPLETE, (
            f"Section {gid} was {manifest.sections[gid].status}, expected COMPLETE"
        )

    assert manifest.completed_sections == 8


@pytest.mark.asyncio
async def test_create_manifest_populates_cache() -> None:
    """Cache is seeded after create_manifest_async."""
    persistence = _make_persistence()

    await persistence.create_manifest_async("proj_1", "offer", ["sec_1", "sec_2"])

    assert "proj_1" in persistence._manifest_cache
    assert persistence._manifest_cache["proj_1"].project_gid == "proj_1"


@pytest.mark.asyncio
async def test_get_manifest_returns_cached() -> None:
    """Cache hit skips S3 call."""
    persistence = _make_persistence()

    await persistence.create_manifest_async("proj_1", "offer", ["sec_1"])

    # Reset mock to track new calls
    persistence._s3_client.get_object_async = AsyncMock()

    result = await persistence.get_manifest_async("proj_1")

    assert result is not None
    assert result.project_gid == "proj_1"
    # S3 should NOT have been called
    persistence._s3_client.get_object_async.assert_not_called()


@pytest.mark.asyncio
async def test_get_manifest_falls_through_to_s3() -> None:
    """Cache miss reads from S3 and populates cache."""
    persistence = _make_persistence()

    manifest = SectionManifest(
        project_gid="proj_1",
        entity_type="offer",
        total_sections=2,
    )
    manifest_json = manifest.model_dump_json().encode("utf-8")

    persistence._s3_client.get_object_async = AsyncMock(
        return_value=S3ReadResult(
            success=True,
            key="test",
            data=manifest_json,
            size_bytes=len(manifest_json),
            duration_ms=5.0,
        )
    )

    result = await persistence.get_manifest_async("proj_1")

    assert result is not None
    assert result.project_gid == "proj_1"
    persistence._s3_client.get_object_async.assert_called_once()
    # Should now be cached
    assert "proj_1" in persistence._manifest_cache


@pytest.mark.asyncio
async def test_delete_manifest_invalidates_cache() -> None:
    """Cache is cleared on delete."""
    persistence = _make_persistence()
    persistence._s3_client.delete_object_async = AsyncMock(return_value=True)

    await persistence.create_manifest_async("proj_1", "offer", ["sec_1"])
    assert "proj_1" in persistence._manifest_cache

    await persistence.delete_manifest_async("proj_1")

    assert "proj_1" not in persistence._manifest_cache


@pytest.mark.asyncio
async def test_concurrent_mixed_statuses() -> None:
    """Mix of IN_PROGRESS, COMPLETE, FAILED concurrent updates all preserved."""
    persistence = _make_persistence()
    section_gids = [f"sec_{i}" for i in range(6)]

    await persistence.create_manifest_async("proj_1", "offer", section_gids)

    updates = [
        ("sec_0", SectionStatus.COMPLETE, 10, None),
        ("sec_1", SectionStatus.FAILED, 0, "timeout"),
        ("sec_2", SectionStatus.COMPLETE, 20, None),
        ("sec_3", SectionStatus.IN_PROGRESS, 0, None),
        ("sec_4", SectionStatus.COMPLETE, 30, None),
        ("sec_5", SectionStatus.FAILED, 0, "rate limited"),
    ]

    tasks = [
        persistence.update_manifest_section_async(
            "proj_1", gid, status, rows=rows, error=error
        )
        for gid, status, rows, error in updates
    ]
    await asyncio.gather(*tasks)

    manifest = await persistence.get_manifest_async("proj_1")
    assert manifest is not None

    assert manifest.sections["sec_0"].status == SectionStatus.COMPLETE
    assert manifest.sections["sec_1"].status == SectionStatus.FAILED
    assert manifest.sections["sec_1"].error == "timeout"
    assert manifest.sections["sec_2"].status == SectionStatus.COMPLETE
    assert manifest.sections["sec_3"].status == SectionStatus.IN_PROGRESS
    assert manifest.sections["sec_4"].status == SectionStatus.COMPLETE
    assert manifest.sections["sec_5"].status == SectionStatus.FAILED
    assert manifest.sections["sec_5"].error == "rate limited"
    assert manifest.completed_sections == 3


@pytest.mark.asyncio
async def test_s3_write_still_called_per_update() -> None:
    """Each update flushes to S3 for durability."""
    persistence = _make_persistence()
    section_gids = [f"sec_{i}" for i in range(4)]

    await persistence.create_manifest_async("proj_1", "offer", section_gids)

    # Reset to count only update-related writes
    persistence._s3_client.put_object_async.reset_mock()

    tasks = [
        persistence.update_manifest_section_async(
            "proj_1", gid, SectionStatus.COMPLETE, rows=10
        )
        for gid in section_gids
    ]
    await asyncio.gather(*tasks)

    # One S3 write per update
    assert persistence._s3_client.put_object_async.call_count == 4
