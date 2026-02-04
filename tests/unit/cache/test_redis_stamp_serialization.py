"""Tests for Redis serialization of FreshnessStamp.

Per TDD-CROSS-TIER-FRESHNESS-001: Ensures stamps survive Redis
round-trip serialization and legacy data deserializes with stamp=None.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from autom8_asana.cache.backends.redis import RedisCacheProvider, RedisConfig
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.freshness_stamp import FreshnessStamp, VerificationSource


def _make_redis_provider() -> RedisCacheProvider:
    """Create a Redis provider for serialization testing.

    Uses a config that will fail to connect (which is fine, we are
    only testing serialization methods, not actual Redis operations).
    """
    provider = RedisCacheProvider.__new__(RedisCacheProvider)
    provider._config = RedisConfig()
    provider._degraded = True
    provider._redis_module = None
    return provider


class TestRedisSerializeWithStamp:
    """Tests for Redis serialization with freshness stamp."""

    def test_redis_serialize_with_stamp(self) -> None:
        """Redis serialization includes stamp as JSON string."""
        stamp = FreshnessStamp(
            last_verified_at=datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC),
            source=VerificationSource.API_FETCH,
            staleness_hint=None,
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

        provider = _make_redis_provider()
        serialized = provider._serialize_entry(entry)

        # Stamp should be a non-empty JSON string
        assert serialized["freshness_stamp"] != ""
        stamp_data = json.loads(serialized["freshness_stamp"])
        assert stamp_data["source"] == "api_fetch"
        assert stamp_data["staleness_hint"] is None
        assert "2025-06-01" in stamp_data["last_verified_at"]

    def test_redis_serialize_with_stamp_and_hint(self) -> None:
        """Redis serialization preserves staleness hint."""
        stamp = FreshnessStamp(
            last_verified_at=datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC),
            source=VerificationSource.BATCH_CHECK,
            staleness_hint="mutation:task:update:999",
        )
        entry = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            ttl=300,
            freshness_stamp=stamp,
        )

        provider = _make_redis_provider()
        serialized = provider._serialize_entry(entry)

        stamp_data = json.loads(serialized["freshness_stamp"])
        assert stamp_data["staleness_hint"] == "mutation:task:update:999"
        assert stamp_data["source"] == "batch_check"


class TestRedisSerializeWithoutStamp:
    """Tests for Redis serialization without stamp."""

    def test_redis_serialize_without_stamp(self) -> None:
        """Redis serialization handles None stamp."""
        entry = CacheEntry(
            key="123",
            data={"gid": "123"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            ttl=300,
        )

        provider = _make_redis_provider()
        serialized = provider._serialize_entry(entry)

        assert serialized["freshness_stamp"] == ""


class TestRedisDeserializeWithStamp:
    """Tests for Redis deserialization with stamp."""

    def test_redis_deserialize_with_stamp(self) -> None:
        """Deserialization reconstructs stamp from JSON."""
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

        provider = _make_redis_provider()
        serialized = provider._serialize_entry(entry)
        deserialized = provider._deserialize_entry(serialized, "123")

        assert deserialized is not None
        assert deserialized.freshness_stamp is not None
        assert deserialized.freshness_stamp.source == VerificationSource.API_FETCH
        assert deserialized.freshness_stamp.staleness_hint is None
        assert deserialized.freshness_stamp.last_verified_at.year == 2025


class TestRedisDeserializeLegacy:
    """Tests for Redis deserialization of legacy data."""

    def test_redis_deserialize_without_stamp(self) -> None:
        """Legacy data without freshness_stamp deserializes with stamp=None."""
        legacy_data = {
            "data": '{"gid": "123"}',
            "entry_type": "task",
            "version": "2025-01-01T00:00:00+00:00",
            "cached_at": "2025-01-01T00:00:00+00:00",
            "ttl": "300",
            "project_gid": "",
            "metadata": "{}",
            "key": "123",
            # No freshness_stamp field at all
        }

        provider = _make_redis_provider()
        entry = provider._deserialize_entry(legacy_data, "123")

        assert entry is not None
        assert entry.freshness_stamp is None
        assert entry.key == "123"

    def test_redis_deserialize_empty_stamp(self) -> None:
        """Data with empty freshness_stamp string deserializes with stamp=None."""
        data = {
            "data": '{"gid": "123"}',
            "entry_type": "task",
            "version": "2025-01-01T00:00:00+00:00",
            "cached_at": "2025-01-01T00:00:00+00:00",
            "ttl": "300",
            "project_gid": "",
            "metadata": "{}",
            "key": "123",
            "freshness_stamp": "",
        }

        provider = _make_redis_provider()
        entry = provider._deserialize_entry(data, "123")

        assert entry is not None
        assert entry.freshness_stamp is None


class TestRedisRoundTrip:
    """Tests for complete serialize/deserialize round-trip."""

    def test_round_trip_with_stamp(self) -> None:
        """Stamp survives full serialize/deserialize cycle."""
        original_stamp = FreshnessStamp(
            last_verified_at=datetime(2025, 6, 15, 14, 30, 0, tzinfo=UTC),
            source=VerificationSource.MUTATION_EVENT,
            staleness_hint="mutation:task:update:12345",
        )
        original_entry = CacheEntry(
            key="789",
            data={"gid": "789", "name": "Round Trip"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 6, 15, tzinfo=UTC),
            cached_at=datetime(2025, 6, 15, 14, 30, 0, tzinfo=UTC),
            ttl=600,
            freshness_stamp=original_stamp,
        )

        provider = _make_redis_provider()
        serialized = provider._serialize_entry(original_entry)
        restored = provider._deserialize_entry(serialized, "789")

        assert restored is not None
        assert restored.freshness_stamp is not None
        assert restored.freshness_stamp.source == VerificationSource.MUTATION_EVENT
        assert restored.freshness_stamp.staleness_hint == "mutation:task:update:12345"
        assert restored.freshness_stamp.last_verified_at.year == 2025
        assert restored.freshness_stamp.last_verified_at.month == 6

    def test_round_trip_without_stamp(self) -> None:
        """Entry without stamp survives round-trip with stamp=None."""
        original_entry = CacheEntry(
            key="789",
            data={"gid": "789"},
            entry_type=EntryType.TASK,
            version=datetime(2025, 1, 1, tzinfo=UTC),
            ttl=300,
        )

        provider = _make_redis_provider()
        serialized = provider._serialize_entry(original_entry)
        restored = provider._deserialize_entry(serialized, "789")

        assert restored is not None
        assert restored.freshness_stamp is None
