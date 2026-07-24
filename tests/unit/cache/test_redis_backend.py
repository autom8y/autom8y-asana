"""Tests for RedisCacheProvider."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.cache.models.entry import CacheEntry, EntryType

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

    def test_init_with_redis_installed_is_not_degraded(self) -> None:
        """GREEN companion to the packaging fix.

        With the ``redis`` package present -- as the production image now
        installs via ``--extra redis`` -- the provider imports redis, builds its
        (lazy) connection pool, and constructs NON-degraded. This is the live
        warmer path that was broken while the extra was omitted from the prod
        image (``import redis`` -> ImportError -> NO-OP degraded cache).
        """
        import redis as real_redis  # noqa: F401  proves the extra resolves

        from autom8_asana.cache.backends.redis import RedisCacheProvider

        provider = RedisCacheProvider()

        # import resolved and construction is non-degraded (lazy pool, no connect)
        assert provider._redis_module is not None
        assert provider._degraded is False

    def test_import_failure_announces_degraded_mode_loudly(self) -> None:
        """Never-silent guard on the exact production packaging omission.

        When the ``redis`` package is absent, construction MUST (a) fail open
        into degraded mode -- the warmer still degrades gracefully, it does not
        raise -- and (b) emit a distinct high-visibility ERROR-level
        ``cache_degraded_mode`` event so the dead warmer cache can never run dark
        again (a CloudWatch Logs metric filter alarms on that event).
        """
        import sys

        from autom8y_log.testing import MockLogger

        from autom8_asana.cache.backends import redis as redis_backend

        mock_logger = MockLogger()
        # Setting sys.modules["redis"] = None forces the in-__init__ `import redis`
        # to raise ImportError even though the package is installed in the test env.
        with (
            patch.object(redis_backend, "logger", mock_logger),
            patch.dict(sys.modules, {"redis": None}),
        ):
            provider = redis_backend.RedisCacheProvider()

        # (a) fail-open: constructs, degrades gracefully, is not healthy
        assert provider._degraded is True
        assert provider._redis_module is None
        assert provider.is_healthy() is False

        # (b) LOUD: a distinct ERROR-level cache_degraded_mode event was emitted
        mock_logger.assert_logged("error", "cache_degraded_mode")
        entry = next(
            e
            for e in mock_logger.entries
            if e.event == "cache_degraded_mode" and e.level == "error"
        )
        assert entry.kwargs["extra"]["reason"] == "redis_package_not_installed"
        assert entry.kwargs["extra"]["fail_open"] is True

    def test_init_with_config(self) -> None:
        """Test initialization with RedisConfig."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider, RedisConfig

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


class TestRedisPoolConstruction:
    """Pool construction against the REAL installed redis-py (F1a root cause).

    The dead-warmer-cache signature: ``ssl``/``ssl_cert_reqs`` forwarded as
    plain connection kwargs are rejected by redis-py's ``Connection.__init__``
    with a TypeError at CHECKOUT time -- pool construction itself is lazy and
    succeeds silently. ``make_connection()`` counts the connection BEFORE
    constructing it, so each failed construction permanently leaked one pool
    slot until the cap was reached and every subsequent op raised
    ``MaxConnectionsError("Too many connections")`` -> sticky degraded mode ->
    silent no-op writes. Zero commands ever reached the ElastiCache server
    (SetTypeCmds absent, CurrItems 0, CurrConnections flat at baseline).
    """

    def test_ssl_pool_uses_ssl_connection_class_and_kwargs_construct(self) -> None:
        """TLS selects SSLConnection; checkout-time construction succeeds.

        RED on the broken construction: connection_class stayed the plain
        ``Connection`` and constructing it with the pool's own kwargs raised
        ``TypeError: unexpected keyword argument 'ssl'``.
        """
        import redis as real_redis

        from autom8_asana.cache.backends.redis import RedisCacheProvider, RedisConfig

        provider = RedisCacheProvider(config=RedisConfig(host="localhost", ssl=True))

        assert provider._degraded is False
        pool = provider._pool
        assert pool is not None
        assert pool.connection_class is real_redis.SSLConnection
        # EXACTLY what make_connection() performs at first checkout. No I/O:
        # the socket is opened only by connection.connect() at first command.
        conn = pool.connection_class(**pool.connection_kwargs)
        assert conn is not None

    def test_plain_pool_uses_connection_class_without_ssl_kwargs(self) -> None:
        """Non-TLS pool carries NO ssl kwargs; construction succeeds."""
        import redis as real_redis

        from autom8_asana.cache.backends.redis import RedisCacheProvider, RedisConfig

        provider = RedisCacheProvider(config=RedisConfig(host="localhost", ssl=False))

        assert provider._degraded is False
        pool = provider._pool
        assert pool is not None
        assert pool.connection_class is real_redis.Connection
        assert "ssl" not in pool.connection_kwargs
        assert "ssl_cert_reqs" not in pool.connection_kwargs
        conn = pool.connection_class(**pool.connection_kwargs)
        assert conn is not None

    def test_pool_is_blocking_with_bounded_timeout(self) -> None:
        """A burst wider than the cap QUEUES (bounded) instead of throwing.

        ``BlockingConnectionPool`` waits up to ``pool_timeout`` for a free
        pooled connection; sustained exhaustion still fails loudly into the
        degraded-mode WARNING rather than silently.
        """
        import redis as real_redis

        from autom8_asana.cache.backends.redis import RedisCacheProvider, RedisConfig

        provider = RedisCacheProvider(
            config=RedisConfig(host="localhost", ssl=False, max_connections=7, pool_timeout=3.5)
        )

        pool = provider._pool
        assert isinstance(pool, real_redis.BlockingConnectionPool)
        assert pool.max_connections == 7
        assert pool.timeout == 3.5

    def test_kwarg_drift_announces_degraded_loudly(self) -> None:
        """Never-silent guard on the connection-kwargs incompatibility class.

        A kwarg the installed redis-py connection class rejects must (a) fail
        OPEN into degraded mode at boot -- never raise out of construction --
        and (b) emit the alarmed ERROR-level ``cache_degraded_mode`` event with
        a distinct reason, instead of leaking pool slots op-by-op into a
        misleading "Too many connections" N ops later.
        """
        from autom8y_log.testing import MockLogger

        from autom8_asana.cache.backends import redis as redis_backend

        class _RejectingConnection:
            def __init__(self, **kwargs: object) -> None:
                raise TypeError("__init__() got an unexpected keyword argument 'ssl'")

        class _StubPool:
            def __init__(self, **kwargs: object) -> None:
                self.connection_class = kwargs["connection_class"]
                self.connection_kwargs = {"ssl": True}

        fake_redis = MagicMock()
        fake_redis.Connection = _RejectingConnection
        fake_redis.SSLConnection = _RejectingConnection
        fake_redis.BlockingConnectionPool = _StubPool

        with patch.object(redis_backend.RedisCacheProvider, "_initialize_pool"):
            provider = redis_backend.RedisCacheProvider(
                config=redis_backend.RedisConfig(host="localhost", ssl=True)
            )
        provider._redis_module = fake_redis

        mock_logger = MockLogger()
        with patch.object(redis_backend, "logger", mock_logger):
            provider._initialize_pool()  # (a) fail-open: must not raise

        assert provider._degraded is True
        # (b) LOUD: distinct ERROR-level cache_degraded_mode event
        mock_logger.assert_logged("error", "cache_degraded_mode")
        entry = next(
            e
            for e in mock_logger.entries
            if e.event == "cache_degraded_mode" and e.level == "error"
        )
        assert entry.kwargs["extra"]["reason"] == "redis_connection_kwargs_invalid"
        assert entry.kwargs["extra"]["fail_open"] is True


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

    def test_make_key_dataframe(self) -> None:
        """Test key generation for dataframe entries."""
        from autom8_asana.cache.backends.redis import RedisCacheProvider

        with patch.object(RedisCacheProvider, "_initialize_pool"):
            provider = RedisCacheProvider()

            # Dataframe keys use a different prefix
            key = provider._make_key("task:project", EntryType.DATAFRAME)
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
                version=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                cached_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
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
            version=datetime.now(UTC),
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
        cached_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
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
        newer = datetime(2025, 1, 1, 14, 0, 0, tzinfo=UTC)
        assert redis_provider.check_freshness("123", EntryType.TASK, newer) is False

    def test_invalidate(self, redis_provider) -> None:
        """Test invalidate operation."""
        now = datetime.now(UTC)

        redis_provider.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={},
                entry_type=EntryType.TASK,
                version=now,
            ),
        )
        redis_provider.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={},
                entry_type=EntryType.SUBTASKS,
                version=now,
            ),
        )

        redis_provider.invalidate("123", [EntryType.TASK])

        assert redis_provider.get_versioned("123", EntryType.TASK) is None
        assert redis_provider.get_versioned("123", EntryType.SUBTASKS) is not None

    def test_get_batch(self, redis_provider) -> None:
        """Test get_batch operation."""
        now = datetime.now(UTC)

        redis_provider.set_versioned(
            "1",
            CacheEntry(
                key="1",
                data={"id": 1},
                entry_type=EntryType.TASK,
                version=now,
            ),
        )
        redis_provider.set_versioned(
            "2",
            CacheEntry(
                key="2",
                data={"id": 2},
                entry_type=EntryType.TASK,
                version=now,
            ),
        )

        result = redis_provider.get_batch(["1", "2", "3"], EntryType.TASK)

        assert result["1"] is not None
        assert result["1"].data["id"] == 1
        assert result["2"] is not None
        assert result["3"] is None

    def test_set_batch(self, redis_provider) -> None:
        """Test set_batch operation."""
        now = datetime.now(UTC)

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
