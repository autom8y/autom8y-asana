"""Tests for RedisCacheProvider."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.freshness import Freshness

# Try to import fakeredis, skip tests if not available
try:
    import fakeredis

    FAKEREDIS_AVAILABLE = True
except ImportError:
    FAKEREDIS_AVAILABLE = False


@pytest.fixture
def mock_redis_module():
    """Create a mock redis module."""
    mock_module = MagicMock()
    mock_pool = MagicMock()
    mock_conn = MagicMock()

    mock_module.ConnectionPool.return_value = mock_pool
    mock_module.Redis.return_value = mock_conn
    mock_module.ConnectionError = ConnectionError
    mock_module.TimeoutError = TimeoutError
    mock_module.RedisError = Exception

    return mock_module, mock_pool, mock_conn


class TestRedisCacheProviderInit:
    """Tests for RedisCacheProvider initialization."""

    def test_init_without_redis_installed(self) -> None:
        """Test initialization when redis module not available enters degraded mode."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()
            # Manually set degraded to simulate redis not being available
            provider._redis_module = None
            provider._degraded = True

            assert provider._degraded is True
            assert provider.is_healthy() is False

    def test_init_with_config(self) -> None:
        """Test initialization with RedisConfig."""
        from autom8_asana.cache.backends.redis import RedisConfig, RedisCacheProvider

        config = RedisConfig(host="redis.example.com", port=6380, password="secret")

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider(config=config)
            assert provider._config.host == "redis.example.com"
            assert provider._config.port == 6380

    def test_init_with_individual_params(self) -> None:
        """Test initialization with individual parameters."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider(
                host="localhost",
                port=6379,
                password="test",
                ssl=True,
                db=1,
            )

            assert provider._config.host == "localhost"
            assert provider._config.port == 6379
            assert provider._config.password == "test"
            assert provider._config.ssl is True
            assert provider._config.db == 1


class TestRedisCacheProviderDegraded:
    """Tests for RedisCacheProvider in degraded mode."""

    def test_degraded_get_returns_none(self) -> None:
        """Test get returns None in degraded mode."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()
            provider._degraded = True
            provider._redis_module = None

            assert provider.get("key") is None

    def test_degraded_set_does_nothing(self) -> None:
        """Test set does nothing in degraded mode."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()
            provider._degraded = True
            provider._redis_module = None

            # Should not raise
            provider.set("key", {"data": "value"})

    def test_degraded_get_versioned_returns_none(self) -> None:
        """Test get_versioned returns None in degraded mode."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()
            provider._degraded = True
            provider._redis_module = None

            assert provider.get_versioned("key", EntryType.TASK) is None

    def test_degraded_is_healthy_returns_false(self) -> None:
        """Test is_healthy returns False in degraded mode."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()
            provider._degraded = True

            assert provider.is_healthy() is False


class TestRedisCacheProviderKeyGeneration:
    """Tests for Redis key generation."""

    def test_make_key_task(self) -> None:
        """Test key generation for task entries."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()

            key = provider._make_key("1234567890", EntryType.TASK)
            assert key == "asana:tasks:1234567890:task"

    def test_make_key_subtasks(self) -> None:
        """Test key generation for subtasks entries."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()

            key = provider._make_key("1234567890", EntryType.SUBTASKS)
            assert key == "asana:tasks:1234567890:subtasks"

    def test_make_key_struc(self) -> None:
        """Test key generation for struc entries."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()

            # Struc keys use a different prefix
            key = provider._make_key("task:project", EntryType.STRUC)
            assert key == "asana:struc:task:project"

    def test_make_meta_key(self) -> None:
        """Test meta key generation."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()

            key = provider._make_meta_key("1234567890")
            assert key == "asana:tasks:1234567890:_meta"


class TestRedisCacheProviderSerialization:
    """Tests for cache entry serialization."""

    def test_serialize_entry(self) -> None:
        """Test serializing a CacheEntry."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()

            entry = CacheEntry(
                key="123",
                data={"name": "Test Task"},
                entry_type=EntryType.TASK,
                version=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                cached_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                ttl=300,
                project_gid="project_456",
                metadata={"source": "api"},
            )

            serialized = provider._serialize_entry(entry)

            assert "data" in serialized
            assert "entry_type" in serialized
            assert serialized["entry_type"] == "task"
            assert "version" in serialized
            assert "ttl" in serialized
            assert serialized["ttl"] == "300"
            assert serialized["project_gid"] == "project_456"

    def test_deserialize_entry(self) -> None:
        """Test deserializing a CacheEntry."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()

            data = {
                "data": '{"name": "Test Task"}',
                "entry_type": "task",
                "version": "2025-01-01T12:00:00+00:00",
                "cached_at": "2025-01-01T12:00:00+00:00",
                "ttl": "300",
                "project_gid": "project_456",
                "metadata": '{"source": "api"}',
                "key": "123",
            }

            entry = provider._deserialize_entry(data, "123")

            assert entry is not None
            assert entry.key == "123"
            assert entry.data["name"] == "Test Task"
            assert entry.entry_type == EntryType.TASK
            assert entry.ttl == 300
            assert entry.project_gid == "project_456"

    def test_deserialize_empty_data_returns_none(self) -> None:
        """Test deserializing empty data returns None."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()

            assert provider._deserialize_entry({}, "123") is None

    def test_deserialize_invalid_json_returns_none(self) -> None:
        """Test deserializing invalid JSON returns None."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()

            data = {
                "data": "not valid json{{{",
                "entry_type": "task",
                "version": "2025-01-01T12:00:00+00:00",
            }

            assert provider._deserialize_entry(data, "123") is None


class TestRedisCacheProviderMetrics:
    """Tests for RedisCacheProvider metrics."""

    def test_get_metrics(self) -> None:
        """Test get_metrics returns CacheMetrics."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()

            metrics = provider.get_metrics()
            assert metrics is not None
            assert metrics.hits == 0
            assert metrics.misses == 0

    def test_reset_metrics(self) -> None:
        """Test reset_metrics clears counters."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()

            # Record some metrics
            provider._metrics.record_hit(1.0)
            provider._metrics.record_miss(1.0)

            assert provider.get_metrics().hits == 1

            provider.reset_metrics()

            assert provider.get_metrics().hits == 0
            assert provider.get_metrics().misses == 0


class TestRedisCacheProviderWarm:
    """Tests for RedisCacheProvider warm operation."""

    def test_warm_returns_placeholder(self) -> None:
        """Test warm returns placeholder result."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider
        from autom8_asana.protocols.cache import WarmResult

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()

            result = provider.warm(["1", "2", "3"])

            assert isinstance(result, WarmResult)
            assert result.skipped == 3
            assert result.warmed == 0
            assert result.failed == 0


@pytest.mark.skipif(not FAKEREDIS_AVAILABLE, reason="fakeredis not installed")
class TestRedisCacheProviderIntegration:
    """Integration tests using fakeredis."""

    @pytest.fixture
    def redis_provider(self):
        """Create a provider with fakeredis backend."""
        import redis as real_redis

        from autom8_asana.cache.backends.redis import RedisCacheProvider

        # Create fakeredis server
        server = fakeredis.FakeServer()

        # Create a patched Redis class that uses fakeredis
        class FakeRedisWrapper:
            def __init__(self, connection_pool=None, **kwargs):
                self._fake = fakeredis.FakeRedis(server=server, decode_responses=True)

            def get(self, key):
                return self._fake.get(key)

            def set(self, key, value):
                return self._fake.set(key, value)

            def setex(self, key, ttl, value):
                return self._fake.setex(key, ttl, value)

            def delete(self, *keys):
                return self._fake.delete(*keys)

            def hgetall(self, key):
                return self._fake.hgetall(key)

            def hset(self, key, field=None, value=None, mapping=None, **kwargs):
                if mapping is not None:
                    return self._fake.hset(key, mapping=mapping, **kwargs)
                elif field is not None and value is not None:
                    return self._fake.hset(key, field, value)
                else:
                    return self._fake.hset(key, **kwargs)

            def hget(self, key, field):
                return self._fake.hget(key, field)

            def hdel(self, key, *fields):
                return self._fake.hdel(key, *fields)

            def expire(self, key, ttl):
                return self._fake.expire(key, ttl)

            def pipeline(self):
                return self._fake.pipeline()

            def ping(self):
                return self._fake.ping()

            def close(self):
                pass

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()

            # Patch the _get_connection method to return our fake wrapper
            original_get_connection = provider._get_connection

            def patched_get_connection():
                return FakeRedisWrapper()

            provider._get_connection = patched_get_connection
            provider._redis_module = real_redis
            provider._degraded = False

            yield provider

    def test_simple_get_set(self, redis_provider) -> None:
        """Test simple get/set operations with fakeredis."""
        redis_provider.set("key", {"data": "value"})
        result = redis_provider.get("key")

        assert result == {"data": "value"}

    def test_simple_get_miss(self, redis_provider) -> None:
        """Test simple get returns None for missing key."""
        result = redis_provider.get("nonexistent")

        assert result is None

    def test_simple_delete(self, redis_provider) -> None:
        """Test simple delete operation."""
        redis_provider.set("key", {"data": "value"})
        redis_provider.delete("key")

        assert redis_provider.get("key") is None

    def test_versioned_get_set(self, redis_provider) -> None:
        """Test versioned get/set operations."""
        entry = CacheEntry(
            key="123",
            data={"name": "Test Task"},
            entry_type=EntryType.TASK,
            version=datetime.now(timezone.utc),
            ttl=300,
        )

        redis_provider.set_versioned("123", entry)
        result = redis_provider.get_versioned("123", EntryType.TASK)

        assert result is not None
        assert result.data["name"] == "Test Task"
        assert result.entry_type == EntryType.TASK

    def test_versioned_get_miss(self, redis_provider) -> None:
        """Test versioned get returns None for missing key."""
        result = redis_provider.get_versioned("nonexistent", EntryType.TASK)

        assert result is None

    def test_check_freshness(self, redis_provider) -> None:
        """Test check_freshness operation."""
        cached_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_time,
        )
        redis_provider.set_versioned("123", entry)

        # Same version should be fresh
        assert redis_provider.check_freshness("123", EntryType.TASK, cached_time) is True

        # Newer version should be stale
        newer = datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        assert redis_provider.check_freshness("123", EntryType.TASK, newer) is False

    def test_invalidate(self, redis_provider) -> None:
        """Test invalidate operation."""
        now = datetime.now(timezone.utc)

        redis_provider.set_versioned("123", CacheEntry(
            key="123", data={}, entry_type=EntryType.TASK, version=now,
        ))
        redis_provider.set_versioned("123", CacheEntry(
            key="123", data={}, entry_type=EntryType.SUBTASKS, version=now,
        ))

        redis_provider.invalidate("123", [EntryType.TASK])

        assert redis_provider.get_versioned("123", EntryType.TASK) is None
        assert redis_provider.get_versioned("123", EntryType.SUBTASKS) is not None

    def test_get_batch(self, redis_provider) -> None:
        """Test get_batch operation."""
        now = datetime.now(timezone.utc)

        redis_provider.set_versioned("1", CacheEntry(
            key="1", data={"id": 1}, entry_type=EntryType.TASK, version=now,
        ))
        redis_provider.set_versioned("2", CacheEntry(
            key="2", data={"id": 2}, entry_type=EntryType.TASK, version=now,
        ))

        result = redis_provider.get_batch(["1", "2", "3"], EntryType.TASK)

        assert result["1"] is not None
        assert result["1"].data["id"] == 1
        assert result["2"] is not None
        assert result["3"] is None

    def test_set_batch(self, redis_provider) -> None:
        """Test set_batch operation."""
        now = datetime.now(timezone.utc)

        entries = {
            "1": CacheEntry(key="1", data={"id": 1}, entry_type=EntryType.TASK, version=now),
            "2": CacheEntry(key="2", data={"id": 2}, entry_type=EntryType.TASK, version=now),
        }

        redis_provider.set_batch(entries)

        assert redis_provider.get_versioned("1", EntryType.TASK) is not None
        assert redis_provider.get_versioned("2", EntryType.TASK) is not None

    def test_is_healthy(self, redis_provider) -> None:
        """Test is_healthy returns True when connected."""
        assert redis_provider.is_healthy() is True
