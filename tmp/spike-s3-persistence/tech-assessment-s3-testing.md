# Tech Assessment: S3 Testing for DataFramePersistence

**Date**: 2026-01-05
**Scout**: Technology Scout (R&D Pack)
**Timebox**: 30 minutes
**Status**: Complete

## Executive Summary

**Recommendation**: **ADOPT moto** for S3 testing of DataFramePersistence

moto is already a dev dependency in `pyproject.toml`, has established patterns in `tests/unit/cache/test_s3_backend.py`, and provides sufficient fidelity for testing parquet save/load round-trips. LocalStack offers no meaningful advantage for this use case and adds Docker complexity.

## Context

DataFramePersistence (`src/autom8_asana/dataframes/persistence.py`) needs S3 testing for:
- `save_dataframe()` / `load_dataframe()` round-trip with Parquet format
- `save_index()` / `load_index()` for GidLookupIndex JSON serialization
- Watermark metadata persistence
- Graceful degradation when S3 unavailable

## Decision Matrix

| Criterion | moto | LocalStack | Winner |
|-----------|------|------------|--------|
| **Already in codebase** | Yes (pyproject.toml) | No | moto |
| **Existing test patterns** | Yes (test_s3_backend.py) | No | moto |
| **Setup complexity** | Zero (pip install) | Docker required | moto |
| **CI integration** | Trivial | Docker-in-Docker | moto |
| **Test speed** | Fast (in-process) | Slower (container) | moto |
| **S3 API fidelity** | Sufficient for boto3 | Higher (real endpoints) | LocalStack |
| **Debugging** | Python stack traces | External logs | moto |

**Final Score**: moto 6/7, LocalStack 1/7

## Analysis

### moto (Recommended)

**Pros**:
1. **Already a dependency**: `moto>=5.0.0` in `[project.optional-dependencies].dev`
2. **Proven patterns exist**: `tests/unit/cache/test_s3_backend.py` has 1000+ lines of working moto tests
3. **Zero infrastructure**: Pure Python, runs in-process
4. **Fast execution**: No container startup overhead
5. **Simple fixtures**: `@mock_aws` decorator + bucket creation
6. **Full boto3 compatibility**: Intercepts at boto3 layer, supports all S3 operations we need

**Cons**:
1. Not a real S3 endpoint (acceptable for unit/integration tests)
2. Some edge cases may differ from production S3

**Risk**: Low - moto is mature (v5.x), actively maintained, and already working in this codebase.

### LocalStack

**Pros**:
1. Real HTTP endpoints (closer to production behavior)
2. Multi-service support (if we needed SQS, DynamoDB, etc.)

**Cons**:
1. **Not in dependencies** - would need to add docker-compose and CI changes
2. **No existing patterns** - would need to establish conventions
3. **Slower tests** - container startup adds seconds per test file
4. **CI complexity** - requires docker-compose setup in GitHub Actions
5. **Debugging overhead** - external process logs vs Python stack traces

**Risk**: Medium - unnecessary complexity for our use case.

## Implementation

### Fixture Pattern (Ready to Use)

```python
# tests/unit/dataframes/test_persistence.py
"""Tests for DataFramePersistence S3 operations."""

from datetime import datetime, timezone
from typing import Generator

import polars as pl
import pytest

# Conditional import for moto
try:
    from moto import mock_aws
    import boto3
    MOTO_AVAILABLE = True
except ImportError:
    MOTO_AVAILABLE = False
    mock_aws = None  # type: ignore

from autom8_asana.dataframes.persistence import DataFramePersistence, PersistenceConfig


@pytest.fixture
def s3_persistence() -> Generator[DataFramePersistence, None, None]:
    """Create DataFramePersistence with moto-mocked S3 backend."""
    if not MOTO_AVAILABLE:
        pytest.skip("moto not installed")

    with mock_aws():
        # Create the mock bucket
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-persistence-bucket")

        config = PersistenceConfig(
            bucket="test-persistence-bucket",
            prefix="dataframes/",
            region="us-east-1",
        )
        persistence = DataFramePersistence(config=config)

        yield persistence


@pytest.fixture
def sample_dataframe() -> pl.DataFrame:
    """Create a sample DataFrame for testing."""
    return pl.DataFrame({
        "gid": ["123", "456", "789"],
        "name": ["Task 1", "Task 2", "Task 3"],
        "completed": [False, True, False],
        "created_at": [
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 2, tzinfo=timezone.utc),
            datetime(2025, 1, 3, tzinfo=timezone.utc),
        ],
    })


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
class TestDataFramePersistenceRoundTrip:
    """Integration tests for DataFrame persistence round-trip."""

    @pytest.mark.asyncio
    async def test_save_load_dataframe_round_trip(
        self,
        s3_persistence: DataFramePersistence,
        sample_dataframe: pl.DataFrame,
    ) -> None:
        """Test DataFrame survives save/load cycle with correct data."""
        project_gid = "project_123"
        watermark = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Save
        success = await s3_persistence.save_dataframe(
            project_gid, sample_dataframe, watermark
        )
        assert success is True

        # Load
        loaded_df, loaded_wm = await s3_persistence.load_dataframe(project_gid)

        # Verify
        assert loaded_df is not None
        assert loaded_wm is not None
        assert loaded_wm == watermark
        assert loaded_df.shape == sample_dataframe.shape
        assert loaded_df.columns == sample_dataframe.columns
        assert loaded_df["gid"].to_list() == sample_dataframe["gid"].to_list()
        assert loaded_df["name"].to_list() == sample_dataframe["name"].to_list()

    @pytest.mark.asyncio
    async def test_load_nonexistent_returns_none(
        self,
        s3_persistence: DataFramePersistence,
    ) -> None:
        """Test loading non-existent DataFrame returns (None, None)."""
        df, wm = await s3_persistence.load_dataframe("nonexistent_project")

        assert df is None
        assert wm is None

    @pytest.mark.asyncio
    async def test_watermark_only_fast_path(
        self,
        s3_persistence: DataFramePersistence,
        sample_dataframe: pl.DataFrame,
    ) -> None:
        """Test get_watermark_only without loading full DataFrame."""
        project_gid = "project_456"
        watermark = datetime(2025, 2, 1, 8, 30, 0, tzinfo=timezone.utc)

        await s3_persistence.save_dataframe(project_gid, sample_dataframe, watermark)

        wm_only = await s3_persistence.get_watermark_only(project_gid)

        assert wm_only == watermark

    @pytest.mark.asyncio
    async def test_delete_dataframe(
        self,
        s3_persistence: DataFramePersistence,
        sample_dataframe: pl.DataFrame,
    ) -> None:
        """Test DataFrame deletion."""
        project_gid = "project_789"
        watermark = datetime.now(timezone.utc)

        await s3_persistence.save_dataframe(project_gid, sample_dataframe, watermark)
        success = await s3_persistence.delete_dataframe(project_gid)

        assert success is True

        df, wm = await s3_persistence.load_dataframe(project_gid)
        assert df is None
        assert wm is None

    @pytest.mark.asyncio
    async def test_is_available_true_with_bucket(
        self,
        s3_persistence: DataFramePersistence,
    ) -> None:
        """Test is_available returns True when bucket accessible."""
        assert s3_persistence.is_available is True

    @pytest.mark.asyncio
    async def test_list_persisted_projects(
        self,
        s3_persistence: DataFramePersistence,
        sample_dataframe: pl.DataFrame,
    ) -> None:
        """Test listing all persisted projects."""
        watermark = datetime.now(timezone.utc)

        # Save to multiple projects
        await s3_persistence.save_dataframe("proj_a", sample_dataframe, watermark)
        await s3_persistence.save_dataframe("proj_b", sample_dataframe, watermark)
        await s3_persistence.save_dataframe("proj_c", sample_dataframe, watermark)

        projects = await s3_persistence.list_persisted_projects()

        assert set(projects) == {"proj_a", "proj_b", "proj_c"}


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
class TestDataFramePersistenceDegraded:
    """Tests for graceful degradation."""

    @pytest.mark.asyncio
    async def test_degraded_mode_save_returns_false(self) -> None:
        """Test save returns False in degraded mode."""
        config = PersistenceConfig(bucket="", prefix="test/")
        persistence = DataFramePersistence(config=config)

        # No bucket = degraded mode
        df = pl.DataFrame({"gid": ["1"]})
        watermark = datetime.now(timezone.utc)

        success = await persistence.save_dataframe("proj", df, watermark)

        assert success is False

    @pytest.mark.asyncio
    async def test_degraded_mode_load_returns_none(self) -> None:
        """Test load returns (None, None) in degraded mode."""
        config = PersistenceConfig(bucket="", prefix="test/")
        persistence = DataFramePersistence(config=config)

        df, wm = await persistence.load_dataframe("proj")

        assert df is None
        assert wm is None
```

### CI Integration

No changes needed - moto is already in dev dependencies and works with standard pytest:

```yaml
# .github/workflows/test.yml (existing pattern works)
- name: Run tests
  run: uv run pytest tests/unit/ -v
```

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| moto behavior differs from real S3 | Low | Low | Use moto for unit tests; optional real S3 integration test |
| moto version incompatibility | Low | Low | Pin version in pyproject.toml (already done: `>=5.0.0`) |
| Parquet serialization issues | Low | Medium | Round-trip tests verify data integrity |

## Files Modified

None required - moto already available. Test file creation only.

## Verdict

| Category | Rating |
|----------|--------|
| Maturity | Mature (v5.x, 15+ years active) |
| Risk | Low |
| Fit | Excellent (already in codebase) |
| **Recommendation** | **ADOPT** |

## Next Steps

1. Copy fixture pattern above to `tests/unit/dataframes/test_persistence.py`
2. Run tests: `uv run pytest tests/unit/dataframes/test_persistence.py -v`
3. Add additional edge case tests as needed (large DataFrames, concurrent access)

## Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| Tech Assessment | `/Users/tomtenuta/Code/autom8_asana/tmp/spike-s3-persistence/tech-assessment-s3-testing.md` | Pending |
| pyproject.toml (moto dep) | `/Users/tomtenuta/Code/autom8_asana/pyproject.toml` | Line 54: `moto>=5.0.0` |
| Existing moto tests | `/Users/tomtenuta/Code/autom8_asana/tests/unit/cache/test_s3_backend.py` | 1030 lines |
| DataFramePersistence | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/persistence.py` | 994 lines |
