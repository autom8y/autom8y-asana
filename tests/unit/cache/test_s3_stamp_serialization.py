"""Tests for S3 serialization of FreshnessStamp.

Per TDD-CROSS-TIER-FRESHNESS-001: Ensures stamps survive S3
round-trip serialization and legacy data deserializes with stamp=None.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.freshness_stamp import FreshnessStamp, VerificationSource


def _make_s3_provider() -> S3CacheProvider:
    """Create an S3 provider for serialization testing.

    Uses a config that will not connect (which is fine, we are
    only testing serialization methods).
    """
    provider = S3CacheProvider.__new__(S3CacheProvider)
    provider._config = S3Config(bucket="test-bucket")
    provider._degraded = True
    provider._boto3_module = None
    provider._botocore_module = None
    return provider


class TestS3SerializeWithStamp:
    """Tests for S3 serialization with freshness stamp."""

    def test_s3_serialize_with_stamp(self) -> None:
        """S3 serialization includes stamp as nested dict."""
        stamp = FreshnessStamp(
            last_verified_at=datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC),
            source=VerificationSource.API_FETCH,
        )
        entry = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            cached_at=datetime(2025, 1, 1, tzinfo=UTC),
            ttl=300,
            freshness_stamp=stamp,
        )

        provider = _make_s3_provider()
        body, metadata, is_compressed = provider._serialize_entry(entry)

        # Parse the body to check stamp
        data = json.loads(body.decode("utf-8"))
        assert data["freshness_stamp"] is not None
        assert data["freshness_stamp"]["source"] == "api_fetch"
        assert data["freshness_stamp"]["staleness_hint"] is None

    def test_s3_serialize_without_stamp(self) -> None:
        """S3 serialization handles None stamp."""
        entry = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            ttl=300,
        )

        provider = _make_s3_provider()
        body, metadata, is_compressed = provider._serialize_entry(entry)

        data = json.loads(body.decode("utf-8"))
        assert data["freshness_stamp"] is None


class TestS3DeserializeLegacy:
    """Tests for S3 deserialization of legacy data."""

    def test_s3_deserialize_legacy(self) -> None:
        """Legacy S3 data without freshness_stamp deserializes with stamp=None."""
        legacy_body = json.dumps({
            "data": {"gid": "123"},
            "entry_type": "task",
            "version": "2025-01-01T00:00:00+00:00",
            "cached_at": "2025-01-01T00:00:00+00:00",
            "ttl": 300,
            "project_gid": None,
            "metadata": {},
            "key": "123",
            # No freshness_stamp
        }).encode("utf-8")

        provider = _make_s3_provider()
        entry = provider._deserialize_entry(
            body=legacy_body,
            metadata={"compressed": "false"},
            key="123",
        )

        assert entry is not None
        assert entry.freshness_stamp is None

    def test_s3_deserialize_null_stamp(self) -> None:
        """S3 data with null freshness_stamp deserializes with stamp=None."""
        body = json.dumps({
            "data": {"gid": "123"},
            "entry_type": "task",
            "version": "2025-01-01T00:00:00+00:00",
            "cached_at": "2025-01-01T00:00:00+00:00",
            "ttl": 300,
            "project_gid": None,
            "metadata": {},
            "key": "123",
            "freshness_stamp": None,
        }).encode("utf-8")

        provider = _make_s3_provider()
        entry = provider._deserialize_entry(
            body=body,
            metadata={"compressed": "false"},
            key="123",
        )

        assert entry is not None
        assert entry.freshness_stamp is None


class TestS3DeserializeWithStamp:
    """Tests for S3 deserialization with stamp."""

    def test_s3_deserialize_with_stamp(self) -> None:
        """S3 deserialization reconstructs stamp from nested dict."""
        body = json.dumps({
            "data": {"gid": "123"},
            "entry_type": "task",
            "version": "2025-01-01T00:00:00+00:00",
            "cached_at": "2025-01-01T00:00:00+00:00",
            "ttl": 300,
            "project_gid": None,
            "metadata": {},
            "key": "123",
            "freshness_stamp": {
                "last_verified_at": "2025-06-01T12:00:00+00:00",
                "source": "batch_check",
                "staleness_hint": "mutation:task:update:999",
            },
        }).encode("utf-8")

        provider = _make_s3_provider()
        entry = provider._deserialize_entry(
            body=body,
            metadata={"compressed": "false"},
            key="123",
        )

        assert entry is not None
        assert entry.freshness_stamp is not None
        assert entry.freshness_stamp.source == VerificationSource.BATCH_CHECK
        assert entry.freshness_stamp.staleness_hint == "mutation:task:update:999"
        assert entry.freshness_stamp.last_verified_at.year == 2025


class TestS3RoundTrip:
    """Tests for complete S3 serialize/deserialize round-trip."""

    def test_round_trip_with_stamp(self) -> None:
        """Stamp survives full S3 serialize/deserialize cycle."""
        original_stamp = FreshnessStamp(
            last_verified_at=datetime(2025, 7, 1, 8, 0, 0, tzinfo=UTC),
            source=VerificationSource.CACHE_WARM,
            staleness_hint=None,
        )
        original_entry = CacheEntry(
            key="456",
            data={"gid": "456", "name": "S3 Round Trip"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 7, 1, tzinfo=UTC),
            cached_at=datetime(2025, 7, 1, 8, 0, 0, tzinfo=UTC),
            ttl=900,
            freshness_stamp=original_stamp,
        )

        provider = _make_s3_provider()
        body, metadata, _ = provider._serialize_entry(original_entry)
        restored = provider._deserialize_entry(body, metadata, "456")

        assert restored is not None
        assert restored.freshness_stamp is not None
        assert restored.freshness_stamp.source == VerificationSource.CACHE_WARM
        assert restored.freshness_stamp.staleness_hint is None
        assert restored.freshness_stamp.last_verified_at.month == 7

    def test_round_trip_without_stamp(self) -> None:
        """Entry without stamp survives S3 round-trip with stamp=None."""
        original_entry = CacheEntry(
            key="456",
            data={"gid": "456"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            ttl=300,
        )

        provider = _make_s3_provider()
        body, metadata, _ = provider._serialize_entry(original_entry)
        restored = provider._deserialize_entry(body, metadata, "456")

        assert restored is not None
        assert restored.freshness_stamp is None
