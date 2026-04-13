"""Unit tests for DataFrameStorage protocol and S3DataFrameStorage implementation.

Per TDD-UNIFIED-DF-PERSISTENCE-001 Section 16: Comprehensive unit tests
covering protocol compliance, key formatting, RetryOrchestrator integration,
S3TransportError wrapping, async operations, and round-trip persistence.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import polars as pl
import pytest
from botocore.exceptions import ClientError

from autom8_asana.config import S3LocationConfig
from autom8_asana.core.retry import (
    BudgetConfig,
    CBState,
    CircuitBreaker,
    CircuitBreakerConfig,
    DefaultRetryPolicy,
    RetryBudget,
    RetryOrchestrator,
    RetryPolicyConfig,
    Subsystem,
)
from autom8_asana.dataframes.storage import (
    DataFrameStorage,
    S3DataFrameStorage,
    create_s3_retry_orchestrator,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BUCKET = "test-bucket"
PREFIX = "dataframes/"
REGION = "us-east-1"
ENDPOINT = "http://localhost:4566"


def _make_location(
    bucket: str = BUCKET,
    region: str = REGION,
    endpoint_url: str | None = ENDPOINT,
) -> S3LocationConfig:
    """Create test S3LocationConfig."""
    return S3LocationConfig(
        bucket=bucket,
        region=region,
        endpoint_url=endpoint_url,
    )


def _make_orchestrator(
    max_attempts: int = 3,
    budget: RetryBudget | None = None,
) -> RetryOrchestrator:
    """Create test RetryOrchestrator with deterministic config."""
    policy = DefaultRetryPolicy(
        RetryPolicyConfig(
            max_attempts=max_attempts,
            base_delay=0.0,  # No delay in tests
            jitter=False,
        )
    )
    if budget is None:
        budget = RetryBudget(BudgetConfig(per_subsystem_max=20, global_max=50))
    cb = CircuitBreaker(
        CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60.0,
            half_open_max_probes=2,
            name="test-s3",
        )
    )
    return RetryOrchestrator(
        policy=policy,
        budget=budget,
        circuit_breaker=cb,
        subsystem=Subsystem.S3,
    )


def _make_storage(
    location: S3LocationConfig | None = None,
    orchestrator: RetryOrchestrator | None = None,
    enabled: bool = True,
) -> S3DataFrameStorage:
    """Create test S3DataFrameStorage with mock-ready config."""
    return S3DataFrameStorage(
        location=location or _make_location(),
        prefix=PREFIX,
        retry_orchestrator=orchestrator or _make_orchestrator(),
        enabled=enabled,
    )


def _make_mock_client() -> MagicMock:
    """Create a mock boto3 S3 client."""
    return MagicMock(name="mock_s3_client")


def _make_df() -> pl.DataFrame:
    """Create a simple test DataFrame."""
    return pl.DataFrame(
        {
            "gid": ["123", "456"],
            "name": ["Task A", "Task B"],
        }
    )


def _make_watermark() -> datetime:
    """Create a timezone-aware watermark."""
    return datetime(2026, 2, 4, 12, 0, 0, tzinfo=UTC)


def _client_error(code: str, message: str = "Error") -> ClientError:
    """Create a botocore ClientError with given code."""
    return ClientError(
        error_response={"Error": {"Code": code, "Message": message}},
        operation_name="TestOperation",
    )


# ---------------------------------------------------------------------------
# Protocol Compliance
# ---------------------------------------------------------------------------


class TestDataFrameStorageProtocol:
    """Verify DataFrameStorage is a proper runtime_checkable protocol."""

    def test_s3_storage_implements_protocol(self) -> None:
        """S3DataFrameStorage satisfies the DataFrameStorage protocol."""
        storage = _make_storage()
        assert isinstance(storage, DataFrameStorage)

    def test_protocol_is_runtime_checkable(self) -> None:
        """Protocol supports isinstance checks."""

        class FakeStorage:
            """Minimal implementation for protocol check."""

            @property
            def is_available(self) -> bool:
                return True

            async def save_dataframe(self, *a: Any, **kw: Any) -> bool:
                return True

            async def load_dataframe(self, *a: Any, **kw: Any) -> tuple:
                return (None, None)

            async def load_dataframe_with_metadata(self, *a: Any, **kw: Any) -> tuple:
                return (None, None, None)

            async def delete_dataframe(self, *a: Any, **kw: Any) -> bool:
                return True

            async def save_watermark(self, *a: Any, **kw: Any) -> bool:
                return True

            async def get_watermark(self, *a: Any, **kw: Any) -> datetime | None:
                return None

            async def load_all_watermarks(self, *a: Any, **kw: Any) -> dict:
                return {}

            async def save_index(self, *a: Any, **kw: Any) -> bool:
                return True

            async def load_index(self, *a: Any, **kw: Any) -> dict | None:
                return None

            async def delete_index(self, *a: Any, **kw: Any) -> bool:
                return True

            async def save_section(self, *a: Any, **kw: Any) -> bool:
                return True

            async def load_section(self, *a: Any, **kw: Any) -> pl.DataFrame | None:
                return None

            async def delete_section(self, *a: Any, **kw: Any) -> bool:
                return True

            async def save_json(self, *a: Any, **kw: Any) -> bool:
                return True

            async def load_json(self, *a: Any, **kw: Any) -> bytes | None:
                return None

            async def delete_object(self, *a: Any, **kw: Any) -> bool:
                return True

            async def list_projects(self, *a: Any, **kw: Any) -> list[str]:
                return []

        assert isinstance(FakeStorage(), DataFrameStorage)


# ---------------------------------------------------------------------------
# Key Formatting
# ---------------------------------------------------------------------------


class TestKeyFormatting:
    """Verify key formatting matches legacy schemes exactly."""

    def test_df_key(self) -> None:
        """DataFrame key matches the established key format."""
        storage = _make_storage()
        assert storage._df_key("proj_123") == "dataframes/proj_123/dataframe.parquet"

    def test_watermark_key(self) -> None:
        """Watermark key matches the established key format."""
        storage = _make_storage()
        assert storage._watermark_key("proj_123") == "dataframes/proj_123/watermark.json"

    def test_index_key(self) -> None:
        """Index key matches the established key format."""
        storage = _make_storage()
        assert storage._index_key("proj_123") == "dataframes/proj_123/gid_lookup_index.json"

    def test_section_key(self) -> None:
        """Section key matches SectionPersistence key format."""
        storage = _make_storage()
        assert (
            storage._section_key("proj_123", "sec_456")
            == "dataframes/proj_123/sections/sec_456.parquet"
        )

    def test_manifest_key(self) -> None:
        """Manifest key matches SectionPersistence manifest key format."""
        storage = _make_storage()
        assert storage._manifest_key("proj_123") == "dataframes/proj_123/manifest.json"

    def test_custom_prefix(self) -> None:
        """Keys use custom prefix when configured."""
        storage = S3DataFrameStorage(
            location=_make_location(),
            prefix="custom/prefix/",
            retry_orchestrator=_make_orchestrator(),
        )
        assert storage._df_key("proj_123") == "custom/prefix/proj_123/dataframe.parquet"
        assert storage._watermark_key("proj_123") == "custom/prefix/proj_123/watermark.json"


# ---------------------------------------------------------------------------
# RetryOrchestrator Factory
# ---------------------------------------------------------------------------


class TestCreateS3RetryOrchestrator:
    """Test the factory function for S3 retry orchestrator."""

    def test_creates_orchestrator_with_defaults(self) -> None:
        """Factory creates correctly configured orchestrator."""
        orchestrator = create_s3_retry_orchestrator()
        assert orchestrator.subsystem == Subsystem.S3
        assert orchestrator.policy.max_attempts == 3

    def test_accepts_shared_budget(self) -> None:
        """Factory uses provided shared budget."""
        shared_budget = RetryBudget(BudgetConfig(per_subsystem_max=10))
        orchestrator = create_s3_retry_orchestrator(budget=shared_budget)
        assert orchestrator.budget is shared_budget


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


class TestAvailability:
    """Test is_available property."""

    def test_available_when_healthy(self) -> None:
        """is_available returns True when not degraded and bucket configured."""
        storage = _make_storage()
        assert storage.is_available is True

    def test_not_available_when_disabled(self) -> None:
        """is_available returns False when enabled=False."""
        storage = _make_storage(enabled=False)
        assert storage.is_available is False

    def test_not_available_when_no_bucket(self) -> None:
        """is_available returns False when no bucket configured."""
        storage = _make_storage(location=_make_location(bucket=""))
        assert storage.is_available is False

    def test_not_available_when_permanently_disabled(self) -> None:
        """is_available returns False when permanently disabled."""
        storage = _make_storage()
        storage._permanently_disabled = True
        assert storage.is_available is False

    def test_not_available_when_cb_open(self) -> None:
        """is_available returns False when circuit breaker is open."""
        storage = _make_storage()
        storage._retry.circuit_breaker.force_open("test")
        assert storage.is_available is False


# ---------------------------------------------------------------------------
# Degraded Mode
# ---------------------------------------------------------------------------


class TestPermanentlyDisabledMode:
    """Test permanently disabled mode behavior across all operations."""

    @pytest.fixture()
    def disabled_storage(self) -> S3DataFrameStorage:
        """Create storage in permanently disabled mode."""
        storage = _make_storage()
        storage._permanently_disabled = True
        return storage

    @pytest.mark.asyncio()
    async def test_save_dataframe_skips_when_disabled(
        self, disabled_storage: S3DataFrameStorage
    ) -> None:
        result = await disabled_storage.save_dataframe("proj_123", _make_df(), _make_watermark())
        assert result is False

    @pytest.mark.asyncio()
    async def test_load_dataframe_skips_when_disabled(
        self, disabled_storage: S3DataFrameStorage
    ) -> None:
        df, wm = await disabled_storage.load_dataframe("proj_123")
        assert df is None
        assert wm is None

    @pytest.mark.asyncio()
    async def test_save_watermark_skips_when_disabled(
        self, disabled_storage: S3DataFrameStorage
    ) -> None:
        result = await disabled_storage.save_watermark("proj_123", _make_watermark())
        assert result is False

    @pytest.mark.asyncio()
    async def test_get_watermark_skips_when_disabled(
        self, disabled_storage: S3DataFrameStorage
    ) -> None:
        result = await disabled_storage.get_watermark("proj_123")
        assert result is None

    @pytest.mark.asyncio()
    async def test_save_index_skips_when_disabled(
        self, disabled_storage: S3DataFrameStorage
    ) -> None:
        result = await disabled_storage.save_index("proj_123", {"key": "val"})
        assert result is False

    @pytest.mark.asyncio()
    async def test_load_index_skips_when_disabled(
        self, disabled_storage: S3DataFrameStorage
    ) -> None:
        result = await disabled_storage.load_index("proj_123")
        assert result is None

    @pytest.mark.asyncio()
    async def test_list_projects_skips_when_disabled(
        self, disabled_storage: S3DataFrameStorage
    ) -> None:
        result = await disabled_storage.list_projects()
        assert result == []

    @pytest.mark.asyncio()
    async def test_load_all_watermarks_skips_when_disabled(
        self, disabled_storage: S3DataFrameStorage
    ) -> None:
        result = await disabled_storage.load_all_watermarks()
        assert result == {}

    @pytest.mark.asyncio()
    async def test_save_section_skips_when_disabled(
        self, disabled_storage: S3DataFrameStorage
    ) -> None:
        result = await disabled_storage.save_section("proj_123", "sec_456", _make_df())
        assert result is False

    @pytest.mark.asyncio()
    async def test_delete_dataframe_skips_when_disabled(
        self, disabled_storage: S3DataFrameStorage
    ) -> None:
        result = await disabled_storage.delete_dataframe("proj_123")
        assert result is False


# ---------------------------------------------------------------------------
# Enabled=False  # noqa: ERA001
# ---------------------------------------------------------------------------


class TestEnabledFalse:
    """Test that enabled=False disables all operations."""

    @pytest.mark.asyncio()
    async def test_all_ops_return_failure(self) -> None:
        """All operations return failure when enabled=False."""
        storage = _make_storage(enabled=False)

        assert await storage.save_dataframe("p", _make_df(), _make_watermark()) is False
        df, wm = await storage.load_dataframe("p")
        assert df is None
        assert wm is None
        assert await storage.save_watermark("p", _make_watermark()) is False
        assert await storage.get_watermark("p") is None
        assert await storage.save_index("p", {}) is False
        assert await storage.load_index("p") is None
        assert await storage.list_projects() == []


# ---------------------------------------------------------------------------
# Naive Watermark Validation
# ---------------------------------------------------------------------------


class TestNaiveWatermarkValidation:
    """Test ValueError on timezone-naive watermarks."""

    @pytest.mark.asyncio()
    async def test_save_dataframe_naive_watermark_raises(self) -> None:
        """save_dataframe raises ValueError for naive watermark."""
        storage = _make_storage()
        naive_wm = datetime(2026, 1, 1, 0, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            await storage.save_dataframe("proj_123", _make_df(), naive_wm)

    @pytest.mark.asyncio()
    async def test_save_watermark_naive_watermark_raises(self) -> None:
        """save_watermark raises ValueError for naive watermark."""
        storage = _make_storage()
        naive_wm = datetime(2026, 1, 1, 0, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            await storage.save_watermark("proj_123", naive_wm)


# ---------------------------------------------------------------------------
# DataFrame Round-Trip (with mock S3)
# ---------------------------------------------------------------------------


class TestDataFrameRoundTrip:
    """Test save/load DataFrame round-trip with mock S3."""

    @pytest.fixture()
    def mock_s3(self) -> MagicMock:
        """Create mock S3 client."""
        return _make_mock_client()

    @pytest.fixture()
    def storage_with_mock(self, mock_s3: MagicMock) -> S3DataFrameStorage:
        """Create storage with injected mock client."""
        storage = _make_storage()
        storage._client = mock_s3
        return storage

    @pytest.mark.asyncio()
    async def test_save_dataframe_happy_path(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """save_dataframe writes parquet and watermark with correct keys."""
        df = _make_df()
        wm = _make_watermark()

        result = await storage_with_mock.save_dataframe("proj_123", df, wm)
        assert result is True

        # Verify two put_object calls
        assert mock_s3.put_object.call_count == 2

        # First call: DataFrame parquet
        first_call = mock_s3.put_object.call_args_list[0]
        assert first_call.kwargs["Key"] == "dataframes/proj_123/dataframe.parquet"
        assert first_call.kwargs["ContentType"] == "application/octet-stream"
        assert first_call.kwargs["Bucket"] == BUCKET

        # Second call: Watermark JSON
        second_call = mock_s3.put_object.call_args_list[1]
        assert second_call.kwargs["Key"] == "dataframes/proj_123/watermark.json"
        assert second_call.kwargs["ContentType"] == "application/json"

    @pytest.mark.asyncio()
    async def test_save_and_load_roundtrip(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """DataFrame survives save/load round-trip."""
        df = _make_df()
        wm = _make_watermark()

        # Capture what gets written
        written_data: dict[str, bytes] = {}

        def capture_put(**kwargs: Any) -> dict[str, str]:
            written_data[kwargs["Key"]] = kwargs["Body"]
            return {"ETag": '"abc123"'}

        mock_s3.put_object.side_effect = capture_put

        # Save
        await storage_with_mock.save_dataframe("proj_123", df, wm)

        # Set up get to return captured data
        def mock_get(**kwargs: Any) -> dict:
            key = kwargs["Key"]
            if key in written_data:
                body = MagicMock()
                body.read.return_value = written_data[key]
                return {"Body": body}
            raise _client_error("NoSuchKey", "Not found")

        mock_s3.get_object.side_effect = mock_get

        # Load
        loaded_df, loaded_wm = await storage_with_mock.load_dataframe("proj_123")

        assert loaded_df is not None
        assert loaded_wm is not None
        assert loaded_df.shape == df.shape
        assert loaded_df.columns == df.columns
        assert loaded_wm == wm

    @pytest.mark.asyncio()
    async def test_load_dataframe_not_found(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """load_dataframe returns (None, None) when watermark missing."""
        mock_s3.get_object.side_effect = _client_error("NoSuchKey")

        df, wm = await storage_with_mock.load_dataframe("proj_missing")
        assert df is None
        assert wm is None

    @pytest.mark.asyncio()
    async def test_load_dataframe_orphan_watermark(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """load_dataframe returns (None, None) when watermark exists but parquet missing."""
        wm_data = json.dumps({"watermark": _make_watermark().isoformat()}).encode()

        call_count = 0

        def mock_get(**kwargs: Any) -> dict:
            nonlocal call_count
            call_count += 1
            key = kwargs["Key"]
            if "watermark.json" in key:
                body = MagicMock()
                body.read.return_value = wm_data
                return {"Body": body}
            raise _client_error("NoSuchKey")

        mock_s3.get_object.side_effect = mock_get

        df, wm = await storage_with_mock.load_dataframe("proj_123")
        assert df is None
        assert wm is None


# ---------------------------------------------------------------------------
# Watermark Persistence
# ---------------------------------------------------------------------------


class TestWatermarkPersistence:
    """Test watermark save/load operations."""

    @pytest.fixture()
    def mock_s3(self) -> MagicMock:
        return _make_mock_client()

    @pytest.fixture()
    def storage_with_mock(self, mock_s3: MagicMock) -> S3DataFrameStorage:
        storage = _make_storage()
        storage._client = mock_s3
        return storage

    @pytest.mark.asyncio()
    async def test_save_watermark_happy_path(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """save_watermark writes JSON to correct key."""
        wm = _make_watermark()
        result = await storage_with_mock.save_watermark("proj_123", wm)
        assert result is True

        call = mock_s3.put_object.call_args
        assert call.kwargs["Key"] == "dataframes/proj_123/watermark.json"
        body = json.loads(call.kwargs["Body"].decode())
        assert body["watermark"] == wm.isoformat()

    @pytest.mark.asyncio()
    async def test_get_watermark_happy_path(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """get_watermark returns datetime from stored JSON."""
        wm = _make_watermark()
        wm_bytes = json.dumps({"watermark": wm.isoformat()}).encode()
        body = MagicMock()
        body.read.return_value = wm_bytes
        mock_s3.get_object.return_value = {"Body": body}

        result = await storage_with_mock.get_watermark("proj_123")
        assert result == wm

    @pytest.mark.asyncio()
    async def test_get_watermark_not_found(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """get_watermark returns None when key does not exist."""
        mock_s3.get_object.side_effect = _client_error("NoSuchKey")
        result = await storage_with_mock.get_watermark("proj_missing")
        assert result is None


# ---------------------------------------------------------------------------
# GidLookupIndex Persistence
# ---------------------------------------------------------------------------


class TestIndexPersistence:
    """Test GidLookupIndex save/load operations."""

    @pytest.fixture()
    def mock_s3(self) -> MagicMock:
        return _make_mock_client()

    @pytest.fixture()
    def storage_with_mock(self, mock_s3: MagicMock) -> S3DataFrameStorage:
        storage = _make_storage()
        storage._client = mock_s3
        return storage

    @pytest.mark.asyncio()
    async def test_save_and_load_index_roundtrip(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """Index data survives save/load round-trip."""
        index_data = {
            "by_phone": {"+15551234": "task_123"},
            "by_vertical": {"sales": ["task_456"]},
        }

        # Capture written data
        written: dict[str, bytes] = {}

        def capture_put(**kwargs: Any) -> dict:
            written[kwargs["Key"]] = kwargs["Body"]
            return {}

        mock_s3.put_object.side_effect = capture_put

        # Save
        result = await storage_with_mock.save_index("proj_123", index_data)
        assert result is True

        # Set up load
        def mock_get(**kwargs: Any) -> dict:
            key = kwargs["Key"]
            body = MagicMock()
            body.read.return_value = written[key]
            return {"Body": body}

        mock_s3.get_object.side_effect = mock_get

        # Load
        loaded = await storage_with_mock.load_index("proj_123")
        assert loaded == index_data

    @pytest.mark.asyncio()
    async def test_load_index_not_found(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """load_index returns None when key does not exist."""
        mock_s3.get_object.side_effect = _client_error("NoSuchKey")
        result = await storage_with_mock.load_index("proj_missing")
        assert result is None

    @pytest.mark.asyncio()
    async def test_delete_index(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """delete_index calls delete_object with correct key."""
        result = await storage_with_mock.delete_index("proj_123")
        assert result is True
        mock_s3.delete_object.assert_called_once_with(
            Bucket=BUCKET,
            Key="dataframes/proj_123/gid_lookup_index.json",
        )


# ---------------------------------------------------------------------------
# Section Operations
# ---------------------------------------------------------------------------


class TestSectionOperations:
    """Test section-level parquet operations."""

    @pytest.fixture()
    def mock_s3(self) -> MagicMock:
        return _make_mock_client()

    @pytest.fixture()
    def storage_with_mock(self, mock_s3: MagicMock) -> S3DataFrameStorage:
        storage = _make_storage()
        storage._client = mock_s3
        return storage

    @pytest.mark.asyncio()
    async def test_save_section_key_format(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """save_section writes to sections/ subdirectory."""
        df = _make_df()
        result = await storage_with_mock.save_section("proj_123", "sec_456", df)
        assert result is True

        call = mock_s3.put_object.call_args
        assert call.kwargs["Key"] == "dataframes/proj_123/sections/sec_456.parquet"

    @pytest.mark.asyncio()
    async def test_save_section_with_metadata(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """save_section passes metadata to S3."""
        df = _make_df()
        meta = {"section-name": "Backlog", "task-count": "42"}
        await storage_with_mock.save_section("proj_123", "sec_456", df, metadata=meta)

        call = mock_s3.put_object.call_args
        assert call.kwargs["Metadata"] == meta

    @pytest.mark.asyncio()
    async def test_section_roundtrip(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """Section DataFrame survives save/load."""
        df = _make_df()
        written: dict[str, bytes] = {}

        def capture_put(**kwargs: Any) -> dict:
            written[kwargs["Key"]] = kwargs["Body"]
            return {}

        mock_s3.put_object.side_effect = capture_put
        await storage_with_mock.save_section("proj_123", "sec_456", df)

        def mock_get(**kwargs: Any) -> dict:
            body = MagicMock()
            body.read.return_value = written[kwargs["Key"]]
            return {"Body": body}

        mock_s3.get_object.side_effect = mock_get
        loaded = await storage_with_mock.load_section("proj_123", "sec_456")

        assert loaded is not None
        assert loaded.shape == df.shape
        assert loaded.columns == df.columns

    @pytest.mark.asyncio()
    async def test_delete_section(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """delete_section calls delete_object with correct key."""
        result = await storage_with_mock.delete_section("proj_123", "sec_456")
        assert result is True
        mock_s3.delete_object.assert_called_once_with(
            Bucket=BUCKET,
            Key="dataframes/proj_123/sections/sec_456.parquet",
        )


# ---------------------------------------------------------------------------
# Raw JSON Operations
# ---------------------------------------------------------------------------


class TestRawJsonOperations:
    """Test save_json / load_json for manifest support."""

    @pytest.fixture()
    def mock_s3(self) -> MagicMock:
        return _make_mock_client()

    @pytest.fixture()
    def storage_with_mock(self, mock_s3: MagicMock) -> S3DataFrameStorage:
        storage = _make_storage()
        storage._client = mock_s3
        return storage

    @pytest.mark.asyncio()
    async def test_save_json_and_load_json_roundtrip(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """Raw JSON bytes survive save/load round-trip."""
        key = "dataframes/proj_123/manifest.json"
        raw_data = json.dumps({"sections": ["a", "b"]}).encode()

        written: dict[str, bytes] = {}

        def capture_put(**kwargs: Any) -> dict:
            written[kwargs["Key"]] = kwargs["Body"]
            return {}

        mock_s3.put_object.side_effect = capture_put

        result = await storage_with_mock.save_json(key, raw_data)
        assert result is True

        def mock_get(**kwargs: Any) -> dict:
            body = MagicMock()
            body.read.return_value = written[kwargs["Key"]]
            return {"Body": body}

        mock_s3.get_object.side_effect = mock_get
        loaded = await storage_with_mock.load_json(key)
        assert loaded == raw_data


# ---------------------------------------------------------------------------
# List Projects
# ---------------------------------------------------------------------------


class TestListProjects:
    """Test project enumeration."""

    @pytest.fixture()
    def mock_s3(self) -> MagicMock:
        return _make_mock_client()

    @pytest.fixture()
    def storage_with_mock(self, mock_s3: MagicMock) -> S3DataFrameStorage:
        storage = _make_storage()
        storage._client = mock_s3
        return storage

    @pytest.mark.asyncio()
    async def test_list_projects_extracts_gids(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """list_projects extracts project GIDs from S3 common prefixes."""
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                "CommonPrefixes": [
                    {"Prefix": "dataframes/proj_aaa/"},
                    {"Prefix": "dataframes/proj_zzz/"},
                    {"Prefix": "dataframes/proj_mmm/"},
                ]
            }
        ]
        mock_s3.get_paginator.return_value = paginator

        result = await storage_with_mock.list_projects()
        assert result == ["proj_aaa", "proj_mmm", "proj_zzz"]  # sorted


# ---------------------------------------------------------------------------
# Load All Watermarks
# ---------------------------------------------------------------------------


class TestLoadAllWatermarks:
    """Test bulk watermark loading."""

    @pytest.fixture()
    def mock_s3(self) -> MagicMock:
        return _make_mock_client()

    @pytest.fixture()
    def storage_with_mock(self, mock_s3: MagicMock) -> S3DataFrameStorage:
        storage = _make_storage()
        storage._client = mock_s3
        return storage

    @pytest.mark.asyncio()
    async def test_load_all_watermarks(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """load_all_watermarks returns dict of project_gid -> datetime."""
        wm1 = datetime(2026, 1, 1, tzinfo=UTC)
        wm2 = datetime(2026, 2, 1, tzinfo=UTC)

        # Set up list_projects
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                "CommonPrefixes": [
                    {"Prefix": "dataframes/proj_a/"},
                    {"Prefix": "dataframes/proj_b/"},
                ]
            }
        ]
        mock_s3.get_paginator.return_value = paginator

        # Set up get_object for watermarks
        def mock_get(**kwargs: Any) -> dict:
            key = kwargs["Key"]
            body = MagicMock()
            if "proj_a" in key:
                body.read.return_value = json.dumps({"watermark": wm1.isoformat()}).encode()
            else:
                body.read.return_value = json.dumps({"watermark": wm2.isoformat()}).encode()
            return {"Body": body}

        mock_s3.get_object.side_effect = mock_get

        result = await storage_with_mock.load_all_watermarks()
        assert len(result) == 2
        assert result["proj_a"] == wm1
        assert result["proj_b"] == wm2


# ---------------------------------------------------------------------------
# RetryOrchestrator Integration
# ---------------------------------------------------------------------------


class TestRetryIntegration:
    """Test that S3 operations properly integrate with RetryOrchestrator."""

    @pytest.mark.asyncio()
    async def test_retry_on_transient_error(self) -> None:
        """Transient S3 errors trigger retry through orchestrator."""
        orchestrator = _make_orchestrator(max_attempts=3)
        storage = _make_storage(orchestrator=orchestrator)
        mock_client = _make_mock_client()
        storage._client = mock_client

        # Fail once, then succeed
        call_count = 0

        def flaky_put(**kwargs: Any) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise _client_error("InternalError", "Transient S3 error")
            return {"ETag": '"ok"'}

        mock_client.put_object.side_effect = flaky_put

        result = await storage.save_watermark("proj_123", _make_watermark())

        # Should succeed after retry
        assert result is True
        assert call_count == 2

    @pytest.mark.asyncio()
    async def test_not_found_errors_return_none(self) -> None:
        """NoSuchKey errors are handled gracefully, returning None.

        Note: ClientError (including NoSuchKey) is in CACHE_TRANSIENT_ERRORS,
        so the RetryOrchestrator will retry it. After exhausting retries,
        the storage layer catches the error and classifies NoSuchKey as
        not-found, returning None without entering degraded mode.
        """
        orchestrator = _make_orchestrator(max_attempts=1)
        storage = _make_storage(orchestrator=orchestrator)
        mock_client = _make_mock_client()
        storage._client = mock_client

        mock_client.get_object.side_effect = _client_error("NoSuchKey")

        result = await storage.get_watermark("proj_missing")
        assert result is None
        # Storage should NOT be permanently disabled for not-found
        assert storage._permanently_disabled is False


# ---------------------------------------------------------------------------
# S3TransportError Wrapping
# ---------------------------------------------------------------------------


class TestErrorWrapping:
    """Test that S3 errors are wrapped as S3TransportError at the boundary."""

    @pytest.mark.asyncio()
    async def test_permanent_errors_do_not_permanently_disable(self) -> None:
        """AccessDenied errors fail the operation but do not permanently disable storage.

        Per B3 fix: permanent errors are specific to the operation, not indicative
        of global S3 failure. The circuit breaker handles transient degradation.
        """
        storage = _make_storage()
        mock_client = _make_mock_client()
        storage._client = mock_client

        mock_client.put_object.side_effect = _client_error("AccessDenied")

        assert storage._permanently_disabled is False
        result = await storage.save_watermark("proj_123", _make_watermark())
        assert result is False
        # Permanent errors no longer set _permanently_disabled
        assert storage._permanently_disabled is False

    @pytest.mark.asyncio()
    async def test_circuit_breaker_opens_on_repeated_failure(self) -> None:
        """Circuit breaker opens after threshold failures.

        Per B3 fix: CB open state blocks operations via allow_request(),
        but does NOT permanently disable the storage. Recovery is automatic
        via HALF_OPEN after recovery_timeout.
        """
        # Use real circuit breaker with low threshold
        budget = RetryBudget(BudgetConfig(per_subsystem_max=100, global_max=200))
        policy = DefaultRetryPolicy(RetryPolicyConfig(max_attempts=1, base_delay=0.0))
        cb = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=300.0,
                name="test-cb",
            )
        )
        orchestrator = RetryOrchestrator(
            policy=policy, budget=budget, circuit_breaker=cb, subsystem=Subsystem.S3
        )
        storage = _make_storage(orchestrator=orchestrator)
        mock_client = _make_mock_client()
        storage._client = mock_client

        # Simulate repeated transient errors
        mock_client.put_object.side_effect = ConnectionError("Connection reset")

        # Keep calling until circuit opens. With failure_threshold=3 and
        # max_attempts=1, each call records one failure.
        for _ in range(4):
            await storage.save_watermark("proj_123", _make_watermark())

        # After enough failures, circuit breaker should be open
        assert cb.state == CBState.OPEN
        # Storage is NOT permanently disabled -- CB handles recovery
        assert storage._permanently_disabled is False
        # But is_available reflects CB state
        assert storage.is_available is False

    @pytest.mark.asyncio()
    async def test_budget_exhaustion_fails_fast(self) -> None:
        """Operations fail when retry budget is exhausted."""
        # Create tiny budget
        budget = RetryBudget(BudgetConfig(per_subsystem_max=1, global_max=1))
        orchestrator = _make_orchestrator(budget=budget)
        storage = _make_storage(orchestrator=orchestrator)
        mock_client = _make_mock_client()
        storage._client = mock_client

        # Exhaust the budget
        budget.try_acquire(Subsystem.S3)

        # Now any operation that needs retry will fail fast
        mock_client.put_object.side_effect = ConnectionError("Connection reset")
        result = await storage.save_watermark("proj_123", _make_watermark())
        assert result is False


# ---------------------------------------------------------------------------
# Delete Operations
# ---------------------------------------------------------------------------


class TestDeleteOperations:
    """Test delete operations."""

    @pytest.fixture()
    def mock_s3(self) -> MagicMock:
        return _make_mock_client()

    @pytest.fixture()
    def storage_with_mock(self, mock_s3: MagicMock) -> S3DataFrameStorage:
        storage = _make_storage()
        storage._client = mock_s3
        return storage

    @pytest.mark.asyncio()
    async def test_delete_dataframe_deletes_all_keys(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """delete_dataframe removes parquet, watermark, and index."""
        result = await storage_with_mock.delete_dataframe("proj_123")
        assert result is True
        assert mock_s3.delete_object.call_count == 3

        deleted_keys = [call.kwargs["Key"] for call in mock_s3.delete_object.call_args_list]
        assert "dataframes/proj_123/dataframe.parquet" in deleted_keys
        assert "dataframes/proj_123/watermark.json" in deleted_keys
        assert "dataframes/proj_123/gid_lookup_index.json" in deleted_keys

    @pytest.mark.asyncio()
    async def test_delete_object_raw_key(
        self, storage_with_mock: S3DataFrameStorage, mock_s3: MagicMock
    ) -> None:
        """delete_object accepts raw S3 key."""
        result = await storage_with_mock.delete_object("custom/key.json")
        assert result is True
        mock_s3.delete_object.assert_called_once_with(Bucket=BUCKET, Key="custom/key.json")


# ---------------------------------------------------------------------------
# Serialization Helpers
# ---------------------------------------------------------------------------


class TestSerializationHelpers:
    """Test parquet and watermark serialization."""

    def test_parquet_roundtrip(self) -> None:
        """DataFrame survives parquet serialize/deserialize."""
        df = _make_df()
        data = S3DataFrameStorage._serialize_parquet(df)
        loaded = S3DataFrameStorage._deserialize_parquet(data)
        assert loaded.shape == df.shape
        assert loaded.columns == df.columns
        assert loaded.to_dicts() == df.to_dicts()

    def test_watermark_serialization(self) -> None:
        """Watermark JSON contains expected fields."""
        wm = _make_watermark()
        df = _make_df()
        data = S3DataFrameStorage._serialize_watermark("proj_123", wm, df, "business")
        parsed = json.loads(data)
        assert parsed["project_gid"] == "proj_123"
        assert parsed["watermark"] == wm.isoformat()
        assert parsed["row_count"] == 2
        assert parsed["entity_type"] == "business"
        assert "saved_at" in parsed
        assert "columns" in parsed

    def test_watermark_deserialization(self) -> None:
        """Watermark datetime is reconstructed from JSON."""
        wm = _make_watermark()
        data = json.dumps({"watermark": wm.isoformat()}).encode()
        loaded = S3DataFrameStorage._deserialize_watermark(data)
        assert loaded == wm

    def test_watermark_without_df(self) -> None:
        """Watermark serialization works without DataFrame."""
        wm = _make_watermark()
        data = S3DataFrameStorage._serialize_watermark("proj_123", wm)
        parsed = json.loads(data)
        assert "row_count" not in parsed
        assert "columns" not in parsed


# ---------------------------------------------------------------------------
# Async Context Manager
# ---------------------------------------------------------------------------


class TestAsyncContextManager:
    """Test async context manager lifecycle."""

    @pytest.mark.asyncio()
    async def test_context_manager_init_and_cleanup(self) -> None:
        """Context manager initializes client and cleans up."""
        storage = _make_storage()
        mock_client = _make_mock_client()

        with patch("boto3.client", return_value=mock_client):
            async with storage as s:
                assert s._client is not None

        # After exit, client is reset
        assert storage._client is None

    @pytest.mark.asyncio()
    async def test_context_manager_permanently_disabled_skips_init(self) -> None:
        """Context manager skips client init when permanently disabled."""
        storage = _make_storage(enabled=False)
        async with storage as s:
            assert s._client is None


# ---------------------------------------------------------------------------
# Layer 2 Tests: Degradation Model Fix (B3)
# ---------------------------------------------------------------------------


class TestDegradationModelFix:
    """Test that the degradation model uses CB recovery, not permanent latch.

    Per TDD Section 4.3: Replace _degraded sticky latch with
    _permanently_disabled (config-time only) + CB-based health checks.
    """

    @pytest.mark.asyncio()
    async def test_storage_recovers_after_cb_open(self) -> None:
        """After CB opens from transient failures, storage recovers via HALF_OPEN.

        Verifies: B3 fix -- no permanent latch, CB recovery works.
        """
        budget = RetryBudget(BudgetConfig(per_subsystem_max=100, global_max=200))
        policy = DefaultRetryPolicy(RetryPolicyConfig(max_attempts=1, base_delay=0.0, jitter=False))
        cb = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=0.1,  # 100ms for testing
                half_open_max_probes=1,
                name="test-recovery",
            )
        )
        orchestrator = RetryOrchestrator(
            policy=policy, budget=budget, circuit_breaker=cb, subsystem=Subsystem.S3
        )
        storage = _make_storage(orchestrator=orchestrator)
        mock_client = _make_mock_client()
        storage._client = mock_client

        # Phase 1: Force CB open with transient failures
        mock_client.put_object.side_effect = ConnectionError("Connection reset")
        for _ in range(4):
            await storage.save_watermark("proj_123", _make_watermark())

        assert cb.state == CBState.OPEN
        assert storage.is_available is False

        # Phase 2: Wait for recovery timeout
        import time

        time.sleep(0.15)

        assert cb.state == CBState.HALF_OPEN

        # Phase 3: Successful probe closes CB
        mock_client.put_object.side_effect = None
        mock_client.put_object.return_value = {"ETag": '"ok"'}

        result = await storage.save_watermark("proj_123", _make_watermark())
        assert result is True
        assert cb.state == CBState.CLOSED
        assert storage.is_available is True

    @pytest.mark.asyncio()
    async def test_permanently_disabled_never_attempts_s3(self) -> None:
        """Storage with enabled=False never makes boto3 calls.

        Verifies: B3 regression test (config-time permanent disable path).
        """
        storage = _make_storage(enabled=False)
        mock_client = _make_mock_client()
        # Set the client to verify it's never called
        storage._client = mock_client

        assert storage._permanently_disabled is True
        assert storage.is_available is False

        # All operations should return failure without touching boto3
        assert await storage.save_watermark("p", _make_watermark()) is False
        assert await storage.get_watermark("p") is None
        df, wm = await storage.load_dataframe("p")
        assert df is None
        assert wm is None
        assert await storage.save_index("p", {}) is False
        assert await storage.load_index("p") is None

        # Verify no boto3 calls were made
        mock_client.put_object.assert_not_called()
        mock_client.get_object.assert_not_called()
        mock_client.delete_object.assert_not_called()

    @pytest.mark.asyncio()
    async def test_cb_open_returns_none_not_permanent_death(self) -> None:
        """CB open returns None/False but recovery is possible.

        Verifies: B3 fix -- CB open is not permanent death.
        """
        budget = RetryBudget(BudgetConfig(per_subsystem_max=100, global_max=200))
        policy = DefaultRetryPolicy(RetryPolicyConfig(max_attempts=1, base_delay=0.0, jitter=False))
        cb = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout=0.1,
                half_open_max_probes=1,
                name="test-cb-recovery",
            )
        )
        orchestrator = RetryOrchestrator(
            policy=policy, budget=budget, circuit_breaker=cb, subsystem=Subsystem.S3
        )
        storage = _make_storage(orchestrator=orchestrator)
        mock_client = _make_mock_client()
        storage._client = mock_client

        # Force CB open
        mock_client.get_object.side_effect = ConnectionError("Connection reset")
        for _ in range(3):
            await storage.get_watermark("proj_123")

        assert cb.state == CBState.OPEN

        # CB open -> returns None (not permanent death)
        result = await storage.get_watermark("proj_123")
        assert result is None
        assert storage._permanently_disabled is False

        # Wait for recovery
        import time

        time.sleep(0.15)
        assert cb.state == CBState.HALF_OPEN

        # Successful probe
        wm_bytes = json.dumps({"watermark": _make_watermark().isoformat()}).encode()
        body = MagicMock()
        body.read.return_value = wm_bytes
        mock_client.get_object.side_effect = None
        mock_client.get_object.return_value = {"Body": body}

        result = await storage.get_watermark("proj_123")
        assert result is not None
        assert cb.state == CBState.CLOSED

    @pytest.mark.asyncio()
    async def test_nosuchkey_does_not_set_permanently_disabled(self) -> None:
        """NoSuchKey in _get_object does not set _permanently_disabled.

        Verifies: B3 fix -- not-found is a normal condition, not degradation.
        """
        orchestrator = _make_orchestrator(max_attempts=1)
        storage = _make_storage(orchestrator=orchestrator)
        mock_client = _make_mock_client()
        storage._client = mock_client

        mock_client.get_object.side_effect = _client_error("NoSuchKey")

        result = await storage.get_watermark("proj_missing")
        assert result is None
        assert storage._permanently_disabled is False
        # CB should also not be affected
        assert orchestrator.circuit_breaker.state == CBState.CLOSED
        assert orchestrator.circuit_breaker._failure_count == 0

    def test_is_available_reflects_cb_state(self) -> None:
        """is_available returns True (CB CLOSED), False (CB OPEN), True (recovered).

        Verifies: B3 fix -- is_available delegates to CB, not sticky latch.
        """
        storage = _make_storage()
        cb = storage._retry.circuit_breaker

        # CLOSED -> available
        assert cb.state == CBState.CLOSED
        assert storage.is_available is True

        # Force OPEN -> not available
        cb.force_open("test")
        assert cb.state == CBState.OPEN
        assert storage.is_available is False

        # Reset (simulates recovery) -> available again
        cb.reset()
        assert cb.state == CBState.CLOSED
        assert storage.is_available is True
