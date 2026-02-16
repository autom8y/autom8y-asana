"""Unit tests for ProgressiveTier.

Per TDD-UNIFIED-PROGRESSIVE-CACHE-001: Tests for reading/writing via
SectionPersistence storage delegation, key parsing, error handling,
and statistics tracking.

Uses DataFrameStorage protocol mocks for S3 persistence operations.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import polars as pl
import pytest

from autom8_asana.cache.dataframe.tiers.progressive import ProgressiveTier
from autom8_asana.cache.integration.dataframe_cache import CacheEntry


def make_entry(project_gid: str = "proj-1") -> CacheEntry:
    """Create a test CacheEntry."""
    df = pl.DataFrame(
        {
            "gid": ["gid-1", "gid-2"],
            "name": ["A", "B"],
            "value": [1, 2],
        }
    )

    return CacheEntry(
        project_gid=project_gid,
        entity_type="unit",
        dataframe=df,
        watermark=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        created_at=datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC),
        schema_version="1.0.0",
    )


def make_watermark_json(watermark: str = "2024-01-15T12:00:00+00:00") -> bytes:
    """Create watermark JSON bytes."""
    return json.dumps(
        {
            "project_gid": "proj-1",
            "watermark": watermark,
            "row_count": 2,
            "columns": ["gid", "name"],
            "saved_at": "2024-01-15T12:00:00+00:00",
            "schema_version": "1.0.0",
        }
    ).encode("utf-8")


def make_watermark_metadata(
    schema_version: str = "1.0.0",
    watermark: str = "2024-01-15T12:00:00+00:00",
) -> dict:
    """Create a watermark metadata dict (as returned by load_dataframe_with_metadata)."""
    return {
        "project_gid": "proj-1",
        "watermark": watermark,
        "row_count": 2,
        "columns": ["gid", "name"],
        "saved_at": "2024-01-15T12:00:00+00:00",
        "schema_version": schema_version,
    }


def make_mock_storage() -> MagicMock:
    """Create a mock DataFrameStorage with async methods."""
    storage = MagicMock()
    storage.is_available = True
    storage.load_dataframe = AsyncMock(return_value=(None, None))
    storage.load_dataframe_with_metadata = AsyncMock(return_value=(None, None, None))
    storage.save_dataframe = AsyncMock(return_value=True)
    storage.load_json = AsyncMock(return_value=None)
    storage.delete_dataframe = AsyncMock(return_value=True)
    return storage


def make_mock_persistence(
    storage: MagicMock | None = None,
    prefix: str = "dataframes/",
) -> MagicMock:
    """Create a mock SectionPersistence with configured storage."""
    persistence = MagicMock()
    persistence._prefix = prefix
    mock_storage = storage if storage else make_mock_storage()
    type(persistence).storage = PropertyMock(return_value=mock_storage)
    persistence.write_final_artifacts_async = AsyncMock(return_value=True)
    return persistence


class TestProgressiveTierKeyParsing:
    """Tests for key parsing logic."""

    def test_parse_key_valid(self) -> None:
        """Valid key formats are parsed correctly."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        entity_type, project_gid = tier._parse_key("unit:1234567890")
        assert entity_type == "unit"
        assert project_gid == "1234567890"

    def test_parse_key_with_underscore_entity(self) -> None:
        """Entity types with underscores are parsed correctly."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        entity_type, project_gid = tier._parse_key("asset_edit:5555555555")
        assert entity_type == "asset_edit"
        assert project_gid == "5555555555"

    def test_parse_key_invalid_no_colon(self) -> None:
        """Key without colon raises ValueError."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        with pytest.raises(ValueError, match="Invalid cache key format"):
            tier._parse_key("invalid-key")

    def test_parse_key_invalid_empty_entity(self) -> None:
        """Key with empty entity type raises ValueError."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        with pytest.raises(ValueError, match="Invalid cache key format"):
            tier._parse_key(":1234567890")

    def test_parse_key_invalid_empty_project(self) -> None:
        """Key with empty project_gid raises ValueError."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        with pytest.raises(ValueError, match="Invalid cache key format"):
            tier._parse_key("unit:")


class TestProgressiveTierGet:
    """Tests for get_async method."""

    @pytest.mark.asyncio
    async def test_get_async_reads_from_storage(self) -> None:
        """Get reads DataFrame and watermark via DataFrameStorage."""
        df = pl.DataFrame({"gid": ["gid-1", "gid-2"], "name": ["A", "B"]})
        watermark = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        wm_meta = make_watermark_metadata()

        storage = make_mock_storage()
        storage.load_dataframe_with_metadata = AsyncMock(
            return_value=(df, watermark, wm_meta)
        )

        persistence = make_mock_persistence(storage=storage)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.get_async("unit:proj-123")

        assert result is not None
        assert result.project_gid == "proj-123"
        assert result.entity_type == "unit"
        assert result.row_count == 2
        assert result.schema_version == "1.0.0"
        storage.load_dataframe_with_metadata.assert_called_once_with("proj-123")
        # load_json should NOT be called -- schema_version comes from metadata
        storage.load_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_async_returns_none_on_missing(self) -> None:
        """Get returns None when DataFrame doesn't exist."""
        storage = make_mock_storage()
        storage.load_dataframe_with_metadata = AsyncMock(
            return_value=(None, None, None)
        )

        persistence = make_mock_persistence(storage=storage)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.get_async("unit:proj-123")

        assert result is None

        stats = tier.get_stats()
        assert stats["not_found"] == 1
        assert stats["reads"] == 1

    @pytest.mark.asyncio
    async def test_get_async_handles_missing_watermark(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Get uses fallback watermark and SchemaRegistry when watermark metadata is None."""
        df = pl.DataFrame({"gid": ["gid-1", "gid-2"], "name": ["A", "B"]})

        storage = make_mock_storage()
        # Metadata is None (watermark.json missing or no schema_version field)
        storage.load_dataframe_with_metadata = AsyncMock(return_value=(df, None, None))

        persistence = make_mock_persistence(storage=storage)
        tier = ProgressiveTier(persistence=persistence)

        # Mock SchemaRegistry to return a known version
        monkeypatch.setattr(
            "autom8_asana.cache.dataframe.tiers.progressive.get_schema_version",
            lambda entity_type: "1.1.0",
            raising=False,
        )
        # The import happens inside the function, so we patch the module-level import target
        import autom8_asana.core.schema

        monkeypatch.setattr(
            autom8_asana.core.schema, "get_schema_version", lambda entity_type: "1.1.0"
        )

        result = await tier.get_async("unit:proj-123")

        assert result is not None
        assert result.project_gid == "proj-123"
        # Watermark should be recent (fallback to current time)
        assert result.watermark.tzinfo is not None
        # Schema version should come from registry, NOT "unknown"
        assert result.schema_version == "1.1.0"

    @pytest.mark.asyncio
    async def test_get_async_metadata_missing_schema_version_uses_registry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When watermark metadata lacks schema_version, falls back to SchemaRegistry."""
        df = pl.DataFrame({"gid": ["gid-1", "gid-2"], "name": ["A", "B"]})
        watermark = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        # Metadata present but without schema_version key
        wm_meta = {
            "project_gid": "proj-123",
            "watermark": "2024-01-15T12:00:00+00:00",
            "row_count": 2,
        }

        storage = make_mock_storage()
        storage.load_dataframe_with_metadata = AsyncMock(
            return_value=(df, watermark, wm_meta)
        )

        persistence = make_mock_persistence(storage=storage)
        tier = ProgressiveTier(persistence=persistence)

        # Mock SchemaRegistry
        import autom8_asana.core.schema

        monkeypatch.setattr(
            autom8_asana.core.schema, "get_schema_version", lambda entity_type: "1.1.0"
        )

        result = await tier.get_async("unit:proj-123")

        assert result is not None
        assert result.schema_version == "1.1.0"
        assert result.watermark == watermark

    @pytest.mark.asyncio
    async def test_get_async_handles_storage_error(self) -> None:
        """Get returns None on storage read error."""
        storage = make_mock_storage()
        storage.load_dataframe_with_metadata = AsyncMock(
            side_effect=ConnectionError("S3 timeout")
        )

        persistence = make_mock_persistence(storage=storage)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.get_async("unit:proj-123")

        assert result is None

        stats = tier.get_stats()
        assert stats["read_errors"] == 1

    @pytest.mark.asyncio
    async def test_get_async_fallback_without_metadata_method(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Get falls back to load_dataframe when load_dataframe_with_metadata is absent."""
        df = pl.DataFrame({"gid": ["gid-1", "gid-2"], "name": ["A", "B"]})
        watermark = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        storage = make_mock_storage()
        # Remove the load_dataframe_with_metadata method to simulate old storage
        del storage.load_dataframe_with_metadata
        storage.load_dataframe = AsyncMock(return_value=(df, watermark))

        persistence = make_mock_persistence(storage=storage)
        tier = ProgressiveTier(persistence=persistence)

        # Mock SchemaRegistry since metadata is unavailable
        import autom8_asana.core.schema

        monkeypatch.setattr(
            autom8_asana.core.schema, "get_schema_version", lambda entity_type: "2.0.0"
        )

        result = await tier.get_async("unit:proj-123")

        assert result is not None
        assert result.project_gid == "proj-123"
        assert result.schema_version == "2.0.0"
        storage.load_dataframe.assert_called_once_with("proj-123")

    @pytest.mark.asyncio
    async def test_get_async_invalid_key_returns_none(self) -> None:
        """Get returns None for invalid key format."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.get_async("invalid-key")

        assert result is None

        stats = tier.get_stats()
        assert stats["read_errors"] == 1


class TestProgressiveTierPut:
    """Tests for put_async method."""

    @pytest.mark.asyncio
    async def test_put_async_delegates_to_persistence(self) -> None:
        """Put calls write_final_artifacts_async correctly."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        entry = make_entry()
        result = await tier.put_async("unit:proj-1", entry)

        assert result is True
        persistence.write_final_artifacts_async.assert_called_once_with(
            project_gid="proj-1",
            df=entry.dataframe,
            watermark=entry.watermark,
            index_data=None,
            entity_type="unit",
        )

        stats = tier.get_stats()
        assert stats["writes"] == 1
        assert stats["bytes_written"] > 0

    @pytest.mark.asyncio
    async def test_put_async_returns_false_on_error(self) -> None:
        """Put returns False when SectionPersistence write fails."""
        persistence = make_mock_persistence()
        persistence.write_final_artifacts_async.return_value = False

        tier = ProgressiveTier(persistence=persistence)

        entry = make_entry()
        result = await tier.put_async("unit:proj-1", entry)

        assert result is False

        stats = tier.get_stats()
        assert stats["write_errors"] == 1

    @pytest.mark.asyncio
    async def test_put_async_handles_exception(self) -> None:
        """Put returns False on exception."""
        persistence = make_mock_persistence()
        persistence.write_final_artifacts_async.side_effect = ConnectionError(
            "S3 error"
        )

        tier = ProgressiveTier(persistence=persistence)

        entry = make_entry()
        result = await tier.put_async("unit:proj-1", entry)

        assert result is False

        stats = tier.get_stats()
        assert stats["write_errors"] == 1

    @pytest.mark.asyncio
    async def test_put_async_invalid_key_returns_false(self) -> None:
        """Put returns False for invalid key format."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        entry = make_entry()
        result = await tier.put_async("invalid-key", entry)

        assert result is False

        stats = tier.get_stats()
        assert stats["write_errors"] == 1


class TestProgressiveTierExists:
    """Tests for exists_async method."""

    @pytest.mark.asyncio
    async def test_exists_async_returns_true_when_found(self) -> None:
        """Exists returns True when DataFrame exists."""
        df = pl.DataFrame({"gid": ["gid-1"], "name": ["A"]})
        storage = make_mock_storage()
        storage.load_dataframe = AsyncMock(return_value=(df, datetime.now(UTC)))

        persistence = make_mock_persistence(storage=storage)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.exists_async("unit:proj-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_async_returns_false_when_missing(self) -> None:
        """Exists returns False when file doesn't exist."""
        storage = make_mock_storage()
        storage.load_dataframe = AsyncMock(return_value=(None, None))

        persistence = make_mock_persistence(storage=storage)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.exists_async("unit:proj-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_async_invalid_key_returns_false(self) -> None:
        """Exists returns False for invalid key format."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.exists_async("invalid-key")

        assert result is False


class TestProgressiveTierDelete:
    """Tests for delete_async method."""

    @pytest.mark.asyncio
    async def test_delete_async_delegates_to_storage(self) -> None:
        """Delete calls storage.delete_dataframe."""
        storage = make_mock_storage()
        storage.delete_dataframe = AsyncMock(return_value=True)

        persistence = make_mock_persistence(storage=storage)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.delete_async("unit:proj-123")

        assert result is True
        storage.delete_dataframe.assert_called_once_with("proj-123")

    @pytest.mark.asyncio
    async def test_delete_async_returns_false_on_failure(self) -> None:
        """Delete returns False if storage deletion fails."""
        storage = make_mock_storage()
        storage.delete_dataframe = AsyncMock(return_value=False)

        persistence = make_mock_persistence(storage=storage)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.delete_async("unit:proj-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_async_invalid_key_returns_false(self) -> None:
        """Delete returns False for invalid key format."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.delete_async("invalid-key")

        assert result is False


class TestProgressiveTierStats:
    """Tests for statistics tracking."""

    def test_stats_initial_values(self) -> None:
        """Stats are initialized to zero."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        stats = tier.get_stats()

        assert stats["reads"] == 0
        assert stats["writes"] == 0
        assert stats["read_errors"] == 0
        assert stats["write_errors"] == 0
        assert stats["bytes_read"] == 0
        assert stats["bytes_written"] == 0
        assert stats["not_found"] == 0

    @pytest.mark.asyncio
    async def test_stats_tracking(self) -> None:
        """Stats correctly track reads, writes, errors."""
        df = pl.DataFrame({"gid": ["gid-1", "gid-2"], "name": ["A", "B"]})
        watermark = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        wm_meta = make_watermark_metadata()

        storage = make_mock_storage()
        storage.load_dataframe_with_metadata = AsyncMock(
            return_value=(df, watermark, wm_meta)
        )

        persistence = make_mock_persistence(storage=storage)
        tier = ProgressiveTier(persistence=persistence)

        # Perform read
        await tier.get_async("unit:proj-1")

        stats = tier.get_stats()
        assert stats["reads"] == 1
        assert stats["bytes_read"] > 0

        # Perform write
        entry = make_entry()
        await tier.put_async("unit:proj-1", entry)

        stats = tier.get_stats()
        assert stats["writes"] == 1
        assert stats["bytes_written"] > 0


class TestProgressiveTierDatetimeParsing:
    """Tests for datetime parsing helper."""

    def test_parse_datetime_valid_iso(self) -> None:
        """Valid ISO datetime is parsed correctly."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        result = tier._parse_datetime("2024-01-15T12:00:00+00:00")

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12
        assert result.tzinfo is not None

    def test_parse_datetime_z_suffix(self) -> None:
        """Datetime with Z suffix is parsed correctly."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        result = tier._parse_datetime("2024-01-15T12:00:00Z")

        assert result.year == 2024
        assert result.tzinfo is not None

    def test_parse_datetime_none(self) -> None:
        """None value returns current time."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        result = tier._parse_datetime(None)

        assert result.tzinfo is not None
        # Should be recent
        now = datetime.now(UTC)
        assert abs((now - result).total_seconds()) < 5

    def test_parse_datetime_invalid(self) -> None:
        """Invalid value returns current time."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        result = tier._parse_datetime("not-a-date")

        assert result.tzinfo is not None
        # Should be recent
        now = datetime.now(UTC)
        assert abs((now - result).total_seconds()) < 5
