"""Unit tests for CheckpointManager and CheckpointRecord.

Per TDD-lambda-cache-warmer Section 9.1:
- Test save/load roundtrip
- Test stale checkpoint returns None
- Test clear checkpoint
- Test missing checkpoint returns None
- Test S3 error handling (warning logged, None returned)
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.lambda_handlers.checkpoint import (
    DEFAULT_BUCKET,
    DEFAULT_PREFIX,
    DEFAULT_STALENESS_HOURS,
    CheckpointManager,
    CheckpointRecord,
)

if TYPE_CHECKING:
    pass


class TestCheckpointRecord:
    """Tests for CheckpointRecord dataclass."""

    def test_create_checkpoint_record(self) -> None:
        """Create a CheckpointRecord with all fields."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=1)

        record = CheckpointRecord(
            invocation_id="test-123",
            completed_entities=["unit", "business"],
            pending_entities=["offer", "contact"],
            entity_results=[
                {"entity_type": "unit", "result": "success", "row_count": 100},
            ],
            created_at=now,
            expires_at=expires,
        )

        assert record.invocation_id == "test-123"
        assert record.completed_entities == ["unit", "business"]
        assert record.pending_entities == ["offer", "contact"]
        assert len(record.entity_results) == 1
        assert record.created_at == now
        assert record.expires_at == expires

    def test_is_stale_fresh_checkpoint(self) -> None:
        """Fresh checkpoint is not stale."""
        now = datetime.now(timezone.utc)

        record = CheckpointRecord(
            invocation_id="test-123",
            completed_entities=["unit"],
            pending_entities=["business"],
            entity_results=[],
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )

        assert record.is_stale() is False

    def test_is_stale_expired_checkpoint(self) -> None:
        """Expired checkpoint is stale."""
        now = datetime.now(timezone.utc)

        record = CheckpointRecord(
            invocation_id="test-123",
            completed_entities=["unit"],
            pending_entities=["business"],
            entity_results=[],
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        )

        assert record.is_stale() is True

    def test_to_json(self) -> None:
        """Serialize CheckpointRecord to JSON."""
        now = datetime(2026, 1, 6, 12, 0, 0, tzinfo=timezone.utc)
        expires = now + timedelta(hours=1)

        record = CheckpointRecord(
            invocation_id="test-123",
            completed_entities=["unit"],
            pending_entities=["business", "offer"],
            entity_results=[{"entity_type": "unit", "result": "success"}],
            created_at=now,
            expires_at=expires,
        )

        json_str = record.to_json()
        parsed = json.loads(json_str)

        assert parsed["invocation_id"] == "test-123"
        assert parsed["completed_entities"] == ["unit"]
        assert parsed["pending_entities"] == ["business", "offer"]
        assert parsed["entity_results"] == [{"entity_type": "unit", "result": "success"}]
        assert parsed["created_at"] == "2026-01-06T12:00:00+00:00"
        assert parsed["expires_at"] == "2026-01-06T13:00:00+00:00"

    def test_from_json(self) -> None:
        """Deserialize CheckpointRecord from JSON."""
        json_str = json.dumps({
            "invocation_id": "test-456",
            "completed_entities": ["unit", "business"],
            "pending_entities": ["offer"],
            "entity_results": [{"entity_type": "unit", "result": "success", "row_count": 500}],
            "created_at": "2026-01-06T12:00:00+00:00",
            "expires_at": "2026-01-06T13:00:00+00:00",
        })

        record = CheckpointRecord.from_json(json_str)

        assert record.invocation_id == "test-456"
        assert record.completed_entities == ["unit", "business"]
        assert record.pending_entities == ["offer"]
        assert len(record.entity_results) == 1
        assert record.entity_results[0]["row_count"] == 500
        assert record.created_at == datetime(2026, 1, 6, 12, 0, 0, tzinfo=timezone.utc)
        assert record.expires_at == datetime(2026, 1, 6, 13, 0, 0, tzinfo=timezone.utc)

    def test_from_json_adds_timezone_if_missing(self) -> None:
        """Timezone is added if missing from JSON datetime strings."""
        # Note: datetimes without timezone info are treated as UTC
        json_str = json.dumps({
            "invocation_id": "test-789",
            "completed_entities": [],
            "pending_entities": ["unit"],
            "entity_results": [],
            "created_at": "2026-01-06T12:00:00",
            "expires_at": "2026-01-06T13:00:00",
        })

        record = CheckpointRecord.from_json(json_str)

        assert record.created_at.tzinfo == timezone.utc
        assert record.expires_at.tzinfo == timezone.utc

    def test_roundtrip_serialization(self) -> None:
        """Serialize and deserialize produces equivalent record."""
        now = datetime.now(timezone.utc)
        original = CheckpointRecord(
            invocation_id="roundtrip-test",
            completed_entities=["unit", "business"],
            pending_entities=["offer", "contact"],
            entity_results=[
                {"entity_type": "unit", "result": "success", "row_count": 100},
                {"entity_type": "business", "result": "success", "row_count": 50},
            ],
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )

        json_str = original.to_json()
        restored = CheckpointRecord.from_json(json_str)

        assert restored.invocation_id == original.invocation_id
        assert restored.completed_entities == original.completed_entities
        assert restored.pending_entities == original.pending_entities
        assert restored.entity_results == original.entity_results
        # Datetime comparison with microsecond tolerance due to JSON serialization
        assert abs((restored.created_at - original.created_at).total_seconds()) < 1
        assert abs((restored.expires_at - original.expires_at).total_seconds()) < 1

    def test_from_json_raises_on_invalid_json(self) -> None:
        """from_json raises JSONDecodeError on malformed JSON (GAP-002)."""
        invalid_json = "not valid json {"
        with pytest.raises(json.JSONDecodeError):
            CheckpointRecord.from_json(invalid_json)

    def test_from_json_raises_on_empty_string(self) -> None:
        """from_json raises JSONDecodeError on empty string (GAP-002)."""
        with pytest.raises(json.JSONDecodeError):
            CheckpointRecord.from_json("")

    def test_from_json_raises_on_missing_required_field(self) -> None:
        """from_json raises KeyError when required field is missing (GAP-002)."""
        # Missing invocation_id field
        incomplete_json = json.dumps({
            "completed_entities": ["unit"],
            "pending_entities": ["business"],
            "entity_results": [],
            "created_at": "2026-01-06T12:00:00+00:00",
            "expires_at": "2026-01-06T13:00:00+00:00",
        })
        with pytest.raises(KeyError):
            CheckpointRecord.from_json(incomplete_json)

    def test_from_json_raises_on_missing_created_at(self) -> None:
        """from_json raises KeyError when created_at is missing (GAP-002)."""
        incomplete_json = json.dumps({
            "invocation_id": "test-123",
            "completed_entities": ["unit"],
            "pending_entities": ["business"],
            "entity_results": [],
            # Missing created_at
            "expires_at": "2026-01-06T13:00:00+00:00",
        })
        with pytest.raises(KeyError):
            CheckpointRecord.from_json(incomplete_json)

    def test_from_json_raises_on_invalid_datetime_format(self) -> None:
        """from_json raises ValueError on invalid datetime format (GAP-002)."""
        invalid_datetime_json = json.dumps({
            "invocation_id": "test-123",
            "completed_entities": ["unit"],
            "pending_entities": ["business"],
            "entity_results": [],
            "created_at": "not-a-datetime",
            "expires_at": "2026-01-06T13:00:00+00:00",
        })
        with pytest.raises(ValueError):
            CheckpointRecord.from_json(invalid_datetime_json)

    def test_from_json_handles_null_entity_lists(self) -> None:
        """from_json accepts null/empty entity lists gracefully (GAP-002)."""
        json_str = json.dumps({
            "invocation_id": "test-null",
            "completed_entities": [],
            "pending_entities": [],
            "entity_results": [],
            "created_at": "2026-01-06T12:00:00+00:00",
            "expires_at": "2026-01-06T13:00:00+00:00",
        })
        record = CheckpointRecord.from_json(json_str)
        assert record.completed_entities == []
        assert record.pending_entities == []


class MockS3Client:
    """Mock S3 client for testing.

    Simulates S3 operations with in-memory storage.
    """

    def __init__(self) -> None:
        """Initialize mock storage."""
        self._storage: dict[str, bytes] = {}
        self.exceptions = MagicMock()
        self.exceptions.NoSuchKey = type("NoSuchKey", (Exception,), {})

    def get_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        """Get object from mock storage."""
        storage_key = f"{Bucket}/{Key}"
        if storage_key not in self._storage:
            raise self.exceptions.NoSuchKey(f"Key not found: {Key}")

        return {
            "Body": MagicMock(read=lambda: self._storage[storage_key]),
        }

    def put_object(
        self,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str | None = None,
    ) -> dict[str, Any]:
        """Put object to mock storage."""
        storage_key = f"{Bucket}/{Key}"
        self._storage[storage_key] = Body
        return {"ETag": "mock-etag"}

    def delete_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        """Delete object from mock storage."""
        storage_key = f"{Bucket}/{Key}"
        self._storage.pop(storage_key, None)
        return {}

    def clear(self) -> None:
        """Clear all mock storage."""
        self._storage.clear()


class TestCheckpointManager:
    """Tests for CheckpointManager class."""

    @pytest.fixture
    def mock_s3(self) -> MockS3Client:
        """Create mock S3 client."""
        return MockS3Client()

    @pytest.fixture
    def manager(self, mock_s3: MockS3Client) -> CheckpointManager:
        """Create CheckpointManager with mock S3."""
        return CheckpointManager(
            bucket="test-bucket",
            s3_client=mock_s3,
        )

    def test_default_configuration(self) -> None:
        """Manager uses default configuration values."""
        with patch.dict("os.environ", {"ASANA_CACHE_S3_BUCKET": "env-bucket"}):
            mgr = CheckpointManager()
            assert mgr.bucket == "env-bucket"
            assert mgr.prefix == DEFAULT_PREFIX
            assert mgr.staleness_hours == DEFAULT_STALENESS_HOURS

    def test_default_bucket_fallback(self) -> None:
        """Manager falls back to DEFAULT_BUCKET when env not set."""
        with patch.dict("os.environ", {}, clear=True):
            mgr = CheckpointManager()
            assert mgr.bucket == DEFAULT_BUCKET

    def test_checkpoint_key(self, manager: CheckpointManager) -> None:
        """Checkpoint key is correctly formatted."""
        key = manager._checkpoint_key()
        assert key == "cache-warmer/checkpoints/latest.json"

    def test_custom_prefix(self, mock_s3: MockS3Client) -> None:
        """Custom prefix is used in checkpoint key."""
        mgr = CheckpointManager(
            bucket="test-bucket",
            prefix="custom/path/",
            s3_client=mock_s3,
        )
        assert mgr._checkpoint_key() == "custom/path/latest.json"

    @pytest.mark.asyncio
    async def test_save_and_load_roundtrip(
        self,
        manager: CheckpointManager,
    ) -> None:
        """Checkpoint can be saved and loaded."""
        # Save checkpoint
        success = await manager.save_async(
            invocation_id="test-123",
            completed_entities=["unit"],
            pending_entities=["business", "offer"],
            entity_results=[{"entity_type": "unit", "result": "success"}],
        )
        assert success is True

        # Load checkpoint
        checkpoint = await manager.load_async()

        assert checkpoint is not None
        assert checkpoint.invocation_id == "test-123"
        assert checkpoint.completed_entities == ["unit"]
        assert checkpoint.pending_entities == ["business", "offer"]
        assert checkpoint.entity_results == [{"entity_type": "unit", "result": "success"}]

    @pytest.mark.asyncio
    async def test_load_missing_checkpoint_returns_none(
        self,
        manager: CheckpointManager,
    ) -> None:
        """Loading missing checkpoint returns None."""
        checkpoint = await manager.load_async()
        assert checkpoint is None

    @pytest.mark.asyncio
    async def test_stale_checkpoint_returns_none(
        self,
        manager: CheckpointManager,
        mock_s3: MockS3Client,
    ) -> None:
        """Stale checkpoints are not loaded."""
        # Create a stale checkpoint directly in mock storage
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        stale_record = CheckpointRecord(
            invocation_id="stale-123",
            completed_entities=["unit"],
            pending_entities=["business"],
            entity_results=[],
            created_at=past,
            expires_at=past + timedelta(hours=1),  # Already expired
        )

        storage_key = f"{manager.bucket}/{manager._checkpoint_key()}"
        mock_s3._storage[storage_key] = stale_record.to_json().encode("utf-8")

        # Load should return None due to staleness
        checkpoint = await manager.load_async()
        assert checkpoint is None

    @pytest.mark.asyncio
    async def test_clear_checkpoint(
        self,
        manager: CheckpointManager,
    ) -> None:
        """Checkpoint can be cleared."""
        # Save checkpoint
        await manager.save_async(
            invocation_id="test-123",
            completed_entities=["unit"],
            pending_entities=[],
            entity_results=[],
        )

        # Verify it exists
        checkpoint = await manager.load_async()
        assert checkpoint is not None

        # Clear checkpoint
        success = await manager.clear_async()
        assert success is True

        # Verify it's gone
        checkpoint = await manager.load_async()
        assert checkpoint is None

    @pytest.mark.asyncio
    async def test_clear_nonexistent_checkpoint(
        self,
        manager: CheckpointManager,
    ) -> None:
        """Clearing nonexistent checkpoint succeeds (idempotent)."""
        success = await manager.clear_async()
        assert success is True

    @pytest.mark.asyncio
    async def test_s3_get_error_returns_none_with_warning(
        self,
        manager: CheckpointManager,
        mock_s3: MockS3Client,
    ) -> None:
        """S3 errors during load are logged as warnings and return None."""
        # Override get_object to raise an error
        def raise_error(*args: Any, **kwargs: Any) -> None:
            raise Exception("S3 connection error")

        mock_s3.get_object = raise_error

        # Should return None gracefully
        with patch(
            "autom8_asana.lambda_handlers.checkpoint.logger"
        ) as mock_logger:
            checkpoint = await manager.load_async()

            assert checkpoint is None
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert call_args[0][0] == "checkpoint_load_error"

    @pytest.mark.asyncio
    async def test_s3_put_error_returns_false(
        self,
        manager: CheckpointManager,
        mock_s3: MockS3Client,
    ) -> None:
        """S3 errors during save are logged and return False."""
        # Override put_object to raise an error
        def raise_error(*args: Any, **kwargs: Any) -> None:
            raise Exception("S3 write error")

        mock_s3.put_object = raise_error

        with patch(
            "autom8_asana.lambda_handlers.checkpoint.logger"
        ) as mock_logger:
            success = await manager.save_async(
                invocation_id="test-123",
                completed_entities=["unit"],
                pending_entities=["business"],
                entity_results=[],
            )

            assert success is False
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert call_args[0][0] == "checkpoint_save_error"

    @pytest.mark.asyncio
    async def test_s3_delete_error_returns_false_with_warning(
        self,
        manager: CheckpointManager,
        mock_s3: MockS3Client,
    ) -> None:
        """S3 errors during clear are logged as warnings and return False."""
        # Override delete_object to raise an error
        def raise_error(*args: Any, **kwargs: Any) -> None:
            raise Exception("S3 delete error")

        mock_s3.delete_object = raise_error

        with patch(
            "autom8_asana.lambda_handlers.checkpoint.logger"
        ) as mock_logger:
            success = await manager.clear_async()

            assert success is False
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert call_args[0][0] == "checkpoint_clear_error"

    @pytest.mark.asyncio
    async def test_custom_staleness_hours(
        self,
        mock_s3: MockS3Client,
    ) -> None:
        """Custom staleness_hours is respected."""
        manager = CheckpointManager(
            bucket="test-bucket",
            staleness_hours=0.5,  # 30 minutes
            s3_client=mock_s3,
        )

        await manager.save_async(
            invocation_id="test-123",
            completed_entities=["unit"],
            pending_entities=["business"],
            entity_results=[],
        )

        # Load and check expiration
        checkpoint = await manager.load_async()
        assert checkpoint is not None

        # Check that expires_at is about 30 minutes from created_at
        delta = checkpoint.expires_at - checkpoint.created_at
        assert 25 < (delta.total_seconds() / 60) < 35  # ~30 minutes

    @pytest.mark.asyncio
    async def test_save_logs_checkpoint_info(
        self,
        manager: CheckpointManager,
    ) -> None:
        """Save logs checkpoint information."""
        with patch(
            "autom8_asana.lambda_handlers.checkpoint.logger"
        ) as mock_logger:
            await manager.save_async(
                invocation_id="log-test-123",
                completed_entities=["unit", "business"],
                pending_entities=["offer"],
                entity_results=[],
            )

            mock_logger.info.assert_called()
            # Find the checkpoint_saved call
            calls = [c for c in mock_logger.info.call_args_list
                     if c[0][0] == "checkpoint_saved"]
            assert len(calls) == 1
            extra = calls[0][1]["extra"]
            assert extra["invocation_id"] == "log-test-123"
            assert extra["completed"] == ["unit", "business"]
            assert extra["pending"] == ["offer"]

    @pytest.mark.asyncio
    async def test_load_logs_checkpoint_info(
        self,
        manager: CheckpointManager,
    ) -> None:
        """Load logs checkpoint information for fresh checkpoints."""
        await manager.save_async(
            invocation_id="log-test-456",
            completed_entities=["unit"],
            pending_entities=["business", "offer"],
            entity_results=[],
        )

        with patch(
            "autom8_asana.lambda_handlers.checkpoint.logger"
        ) as mock_logger:
            await manager.load_async()

            mock_logger.info.assert_called()
            calls = [c for c in mock_logger.info.call_args_list
                     if c[0][0] == "checkpoint_loaded"]
            assert len(calls) == 1
            extra = calls[0][1]["extra"]
            assert extra["invocation_id"] == "log-test-456"
            assert extra["completed"] == ["unit"]
            assert extra["pending"] == ["business", "offer"]

    @pytest.mark.asyncio
    async def test_multiple_saves_overwrite(
        self,
        manager: CheckpointManager,
    ) -> None:
        """Multiple saves overwrite previous checkpoint."""
        # First save
        await manager.save_async(
            invocation_id="first-123",
            completed_entities=["unit"],
            pending_entities=["business", "offer", "contact"],
            entity_results=[],
        )

        # Second save
        await manager.save_async(
            invocation_id="second-456",
            completed_entities=["unit", "business"],
            pending_entities=["offer", "contact"],
            entity_results=[],
        )

        # Load should return second checkpoint
        checkpoint = await manager.load_async()
        assert checkpoint is not None
        assert checkpoint.invocation_id == "second-456"
        assert checkpoint.completed_entities == ["unit", "business"]

    @pytest.mark.asyncio
    async def test_ensure_client_creates_boto3_client(self) -> None:
        """_ensure_client creates boto3 S3 client if not provided."""
        manager = CheckpointManager(bucket="test-bucket")

        with patch("boto3.client") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client

            result = manager._ensure_client()

            mock_boto3.assert_called_once_with("s3")
            assert result == mock_client
            # Second call should reuse client
            manager._ensure_client()
            assert mock_boto3.call_count == 1

    @pytest.mark.asyncio
    async def test_entity_results_preserved(
        self,
        manager: CheckpointManager,
    ) -> None:
        """Entity results with complex data are preserved."""
        entity_results = [
            {
                "entity_type": "unit",
                "result": "success",
                "project_gid": "1234567890123456",
                "row_count": 15000,
                "duration_ms": 2500.5,
                "error": None,
            },
            {
                "entity_type": "business",
                "result": "success",
                "project_gid": "2345678901234567",
                "row_count": 2000,
                "duration_ms": 800.2,
                "error": None,
            },
        ]

        await manager.save_async(
            invocation_id="results-test",
            completed_entities=["unit", "business"],
            pending_entities=["offer"],
            entity_results=entity_results,
        )

        checkpoint = await manager.load_async()
        assert checkpoint is not None
        assert checkpoint.entity_results == entity_results


class TestCheckpointManagerIntegration:
    """Integration-style tests for CheckpointManager.

    These tests verify realistic usage scenarios.
    """

    @pytest.fixture
    def mock_s3(self) -> MockS3Client:
        """Create fresh mock S3 client for each test."""
        return MockS3Client()

    @pytest.mark.asyncio
    async def test_resume_workflow_scenario(
        self,
        mock_s3: MockS3Client,
    ) -> None:
        """Simulate a resume workflow after partial completion.

        Scenario:
        1. First invocation completes 2 entity types, times out
        2. Second invocation resumes from checkpoint
        3. Completes remaining entities and clears checkpoint
        """
        manager = CheckpointManager(
            bucket="test-bucket",
            s3_client=mock_s3,
        )

        # First invocation - partial completion
        first_results = [
            {"entity_type": "unit", "result": "success", "row_count": 15000},
            {"entity_type": "business", "result": "success", "row_count": 2000},
        ]

        await manager.save_async(
            invocation_id="first-invoke-123",
            completed_entities=["unit", "business"],
            pending_entities=["offer", "contact"],
            entity_results=first_results,
        )

        # Second invocation - resume
        checkpoint = await manager.load_async()
        assert checkpoint is not None
        assert checkpoint.pending_entities == ["offer", "contact"]
        assert checkpoint.completed_entities == ["unit", "business"]

        # Process remaining and save updated checkpoint
        updated_results = first_results + [
            {"entity_type": "offer", "result": "success", "row_count": 500},
        ]

        await manager.save_async(
            invocation_id="second-invoke-456",
            completed_entities=["unit", "business", "offer"],
            pending_entities=["contact"],
            entity_results=updated_results,
        )

        # Third invocation - complete and clear
        checkpoint = await manager.load_async()
        assert checkpoint is not None
        assert checkpoint.pending_entities == ["contact"]

        # After completing all, clear checkpoint
        await manager.clear_async()

        # Checkpoint should be gone
        checkpoint = await manager.load_async()
        assert checkpoint is None

    @pytest.mark.asyncio
    async def test_fresh_start_no_checkpoint(
        self,
        mock_s3: MockS3Client,
    ) -> None:
        """First invocation with no checkpoint starts fresh."""
        manager = CheckpointManager(
            bucket="test-bucket",
            s3_client=mock_s3,
        )

        # No checkpoint exists
        checkpoint = await manager.load_async()
        assert checkpoint is None

        # Start fresh and save progress
        await manager.save_async(
            invocation_id="fresh-start-123",
            completed_entities=["unit"],
            pending_entities=["business", "offer", "contact"],
            entity_results=[{"entity_type": "unit", "result": "success"}],
        )

        # Verify checkpoint was saved
        checkpoint = await manager.load_async()
        assert checkpoint is not None
        assert checkpoint.invocation_id == "fresh-start-123"
