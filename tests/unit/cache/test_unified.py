"""Tests for UnifiedTaskStore.

Per TDD-UNIFIED-CACHE-001: Validates unified caching with hierarchy
awareness, freshness coordination, and parent chain resolution.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.freshness_coordinator import FreshnessMode
from autom8_asana.cache.unified import UnifiedTaskStore


@pytest.fixture
def mock_cache_provider() -> MagicMock:
    """Create a mock CacheProvider."""
    provider = MagicMock()
    provider.get_versioned = MagicMock(return_value=None)
    provider.set_versioned = MagicMock()
    provider.get_batch = MagicMock(return_value={})
    provider.set_batch = MagicMock()
    provider.invalidate = MagicMock()
    return provider


@pytest.fixture
def mock_batch_client() -> MagicMock:
    """Create a mock BatchClient."""
    client = MagicMock()
    client.execute_async = AsyncMock(return_value=[])
    return client


@pytest.fixture
def store(
    mock_cache_provider: MagicMock, mock_batch_client: MagicMock
) -> UnifiedTaskStore:
    """Create a UnifiedTaskStore with mocks."""
    return UnifiedTaskStore(
        cache=mock_cache_provider,
        batch_client=mock_batch_client,
        freshness_mode=FreshnessMode.EVENTUAL,
    )


def make_task(
    gid: str,
    name: str = "Test Task",
    parent_gid: str | None = None,
    modified_at: str = "2025-12-23T10:00:00.000Z",
) -> dict:
    """Create a test task dict."""
    task = {
        "gid": gid,
        "name": name,
        "modified_at": modified_at,
    }
    if parent_gid:
        task["parent"] = {"gid": parent_gid}
    return task


def make_entry(
    gid: str,
    modified_at: str = "2025-12-23T10:00:00.000Z",
    ttl: int = 300,
    cached_ago_seconds: int = 0,
    completeness_level: int | None = 20,  # STANDARD by default
) -> CacheEntry:
    """Create a test CacheEntry.

    Args:
        gid: Task GID.
        modified_at: Modified timestamp.
        ttl: Cache TTL in seconds.
        cached_ago_seconds: How long ago entry was cached.
        completeness_level: Completeness level value (default STANDARD=20).
            Set to None to create legacy entries without completeness.
    """
    version = datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
    cached_at = datetime.now(UTC) - timedelta(seconds=cached_ago_seconds)
    metadata = {}
    if completeness_level is not None:
        metadata["completeness_level"] = completeness_level
    return CacheEntry(
        key=gid,
        data={"gid": gid, "name": f"Task {gid}", "modified_at": modified_at},
        entry_type=EntryType.TASK,
        version=version,
        cached_at=cached_at,
        ttl=ttl,
        metadata=metadata,
    )


def make_batch_result(gid: str, modified_at: str) -> BatchResult:
    """Create a successful BatchResult."""
    return BatchResult(
        status_code=200,
        body={"data": {"gid": gid, "modified_at": modified_at}},
        request_index=0,
    )


class TestUnifiedTaskStoreInit:
    """Tests for UnifiedTaskStore initialization."""

    def test_init_with_defaults(self, mock_cache_provider: MagicMock) -> None:
        """Test initialization with default values."""
        store = UnifiedTaskStore(cache=mock_cache_provider)

        assert store.cache == mock_cache_provider
        assert store.batch_client is None
        assert store.freshness_mode == FreshnessMode.EVENTUAL
        assert store._hierarchy is not None
        assert store._freshness is not None

    def test_init_with_custom_mode(
        self, mock_cache_provider: MagicMock, mock_batch_client: MagicMock
    ) -> None:
        """Test initialization with custom freshness mode."""
        store = UnifiedTaskStore(
            cache=mock_cache_provider,
            batch_client=mock_batch_client,
            freshness_mode=FreshnessMode.STRICT,
        )

        assert store.freshness_mode == FreshnessMode.STRICT


class TestUnifiedTaskStoreGet:
    """Tests for get_async method."""

    @pytest.mark.asyncio
    async def test_get_cache_miss(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test get_async returns None on cache miss."""
        mock_cache_provider.get_versioned.return_value = None

        result = await store.get_async("task-123")

        assert result is None
        mock_cache_provider.get_versioned.assert_called_once_with(
            "task-123", EntryType.TASK
        )

    @pytest.mark.asyncio
    async def test_get_immediate_returns_cached(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test get_async with IMMEDIATE mode returns cached without check."""
        entry = make_entry("task-123")
        mock_cache_provider.get_versioned.return_value = entry

        result = await store.get_async("task-123", freshness=FreshnessMode.IMMEDIATE)

        assert result == entry.data
        # Should not check freshness for IMMEDIATE

    @pytest.mark.asyncio
    async def test_get_eventual_fresh_entry(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test get_async with EVENTUAL mode and fresh (non-expired) entry."""
        # Entry not expired (cached 0 seconds ago, TTL 300)
        entry = make_entry("task-123", cached_ago_seconds=0, ttl=300)
        mock_cache_provider.get_versioned.return_value = entry

        result = await store.get_async("task-123", freshness=FreshnessMode.EVENTUAL)

        assert result == entry.data

    @pytest.mark.asyncio
    async def test_get_eventual_stale_entry(
        self,
        store: UnifiedTaskStore,
        mock_cache_provider: MagicMock,
        mock_batch_client: MagicMock,
    ) -> None:
        """Test get_async with EVENTUAL mode and stale (expired, changed) entry."""
        # Entry expired and API shows different version
        entry = make_entry(
            "task-123",
            modified_at="2025-12-23T10:00:00.000Z",
            cached_ago_seconds=400,
            ttl=300,
        )
        mock_cache_provider.get_versioned.return_value = entry

        # API returns newer version
        mock_batch_client.execute_async.return_value = [
            make_batch_result("task-123", "2025-12-23T12:00:00.000Z")
        ]

        result = await store.get_async("task-123", freshness=FreshnessMode.EVENTUAL)

        # Should return None since entry is stale
        assert result is None


class TestUnifiedTaskStoreGetBatch:
    """Tests for get_batch_async method."""

    @pytest.mark.asyncio
    async def test_get_batch_empty(self, store: UnifiedTaskStore) -> None:
        """Test get_batch_async with empty list."""
        result = await store.get_batch_async([])

        assert result == {}

    @pytest.mark.asyncio
    async def test_get_batch_all_misses(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test get_batch_async when all entries miss."""
        mock_cache_provider.get_batch.return_value = {
            "task-1": None,
            "task-2": None,
        }

        result = await store.get_batch_async(["task-1", "task-2"])

        assert result == {"task-1": None, "task-2": None}

    @pytest.mark.asyncio
    async def test_get_batch_immediate_returns_all(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test get_batch_async with IMMEDIATE returns all found."""
        entry1 = make_entry("task-1")
        entry2 = make_entry("task-2")
        mock_cache_provider.get_batch.return_value = {
            "task-1": entry1,
            "task-2": entry2,
        }

        result = await store.get_batch_async(
            ["task-1", "task-2"], freshness=FreshnessMode.IMMEDIATE
        )

        assert result["task-1"] == entry1.data
        assert result["task-2"] == entry2.data

    @pytest.mark.asyncio
    async def test_get_batch_mixed_hits_misses(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test get_batch_async with mix of hits and misses."""
        entry1 = make_entry("task-1")
        mock_cache_provider.get_batch.return_value = {
            "task-1": entry1,
            "task-2": None,  # Miss
        }

        result = await store.get_batch_async(
            ["task-1", "task-2"], freshness=FreshnessMode.IMMEDIATE
        )

        assert result["task-1"] == entry1.data
        assert result["task-2"] is None


class TestUnifiedTaskStorePut:
    """Tests for put_async method."""

    @pytest.mark.asyncio
    async def test_put_stores_in_cache(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test put_async stores task in cache."""
        task = make_task("task-123")

        await store.put_async(task)

        mock_cache_provider.set_versioned.assert_called_once()
        call_args = mock_cache_provider.set_versioned.call_args
        assert call_args[0][0] == "task-123"  # key
        assert call_args[0][1].data == task  # entry.data

    @pytest.mark.asyncio
    async def test_put_registers_hierarchy(self, store: UnifiedTaskStore) -> None:
        """Test put_async registers task in hierarchy index."""
        parent = make_task("parent-1")
        child = make_task("child-1", parent_gid="parent-1")

        await store.put_async(parent)
        await store.put_async(child)

        hierarchy = store.get_hierarchy_index()
        assert hierarchy.get_parent_gid("child-1") == "parent-1"
        assert "child-1" in hierarchy.get_children_gids("parent-1")

    @pytest.mark.asyncio
    async def test_put_with_custom_ttl(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test put_async respects custom TTL."""
        task = make_task("task-123")

        await store.put_async(task, ttl=600)

        call_args = mock_cache_provider.set_versioned.call_args
        entry = call_args[0][1]
        assert entry.ttl == 600

    @pytest.mark.asyncio
    async def test_put_missing_gid_raises(self, store: UnifiedTaskStore) -> None:
        """Test put_async raises for task without gid."""
        with pytest.raises(ValueError, match="must have 'gid' field"):
            await store.put_async({"name": "No GID"})


class TestUnifiedTaskStorePutBatch:
    """Tests for put_batch_async method."""

    @pytest.mark.asyncio
    async def test_put_batch_stores_all(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test put_batch_async stores all tasks."""
        tasks = [
            make_task("task-1"),
            make_task("task-2"),
            make_task("task-3"),
        ]

        count = await store.put_batch_async(tasks)

        assert count == 3
        mock_cache_provider.set_batch.assert_called_once()
        call_args = mock_cache_provider.set_batch.call_args
        entries = call_args[0][0]
        assert len(entries) == 3
        assert "task-1" in entries
        assert "task-2" in entries
        assert "task-3" in entries

    @pytest.mark.asyncio
    async def test_put_batch_registers_hierarchy(self, store: UnifiedTaskStore) -> None:
        """Test put_batch_async registers all in hierarchy."""
        tasks = [
            make_task("parent"),
            make_task("child-1", parent_gid="parent"),
            make_task("child-2", parent_gid="parent"),
        ]

        await store.put_batch_async(tasks)

        hierarchy = store.get_hierarchy_index()
        assert hierarchy.get_children_gids("parent") == {"child-1", "child-2"}

    @pytest.mark.asyncio
    async def test_put_batch_empty(self, store: UnifiedTaskStore) -> None:
        """Test put_batch_async with empty list."""
        count = await store.put_batch_async([])

        assert count == 0

    @pytest.mark.asyncio
    async def test_put_batch_skips_missing_gid(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test put_batch_async skips tasks without gid."""
        tasks = [
            make_task("task-1"),
            {"name": "No GID"},  # Should be skipped
            make_task("task-3"),
        ]

        count = await store.put_batch_async(tasks)

        assert count == 2
        call_args = mock_cache_provider.set_batch.call_args
        entries = call_args[0][0]
        assert len(entries) == 2
        assert "task-1" in entries
        assert "task-3" in entries


class TestUnifiedTaskStoreParentChain:
    """Tests for get_parent_chain_async method."""

    @pytest.mark.asyncio
    async def test_parent_chain_empty_for_root(self, store: UnifiedTaskStore) -> None:
        """Test parent chain is empty for root task."""
        await store.put_async(make_task("root"))

        chain = await store.get_parent_chain_async("root")

        assert chain == []

    @pytest.mark.asyncio
    async def test_parent_chain_single_parent(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test parent chain with single parent."""
        parent = make_task("parent")
        child = make_task("child", parent_gid="parent")

        await store.put_async(parent)
        await store.put_async(child)

        # Mock cache get_batch to return parent
        parent_entry = make_entry("parent")
        mock_cache_provider.get_batch.return_value = {"parent": parent_entry}

        chain = await store.get_parent_chain_async("child")

        assert len(chain) == 1
        assert chain[0]["gid"] == "parent"

    @pytest.mark.asyncio
    async def test_parent_chain_multi_level(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test parent chain with multiple levels."""
        grandparent = make_task("grandparent")
        parent = make_task("parent", parent_gid="grandparent")
        child = make_task("child", parent_gid="parent")

        await store.put_async(grandparent)
        await store.put_async(parent)
        await store.put_async(child)

        # Mock cache get_batch to return all ancestors
        gp_entry = make_entry("grandparent")
        p_entry = make_entry("parent")
        mock_cache_provider.get_batch.return_value = {
            "parent": p_entry,
            "grandparent": gp_entry,
        }

        chain = await store.get_parent_chain_async("child")

        assert len(chain) == 2
        assert chain[0]["gid"] == "parent"
        assert chain[1]["gid"] == "grandparent"

    @pytest.mark.asyncio
    async def test_parent_chain_respects_max_depth(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test parent chain respects max_depth."""
        # Build 5-level hierarchy
        await store.put_async(make_task("level-0"))
        for i in range(1, 5):
            await store.put_async(make_task(f"level-{i}", parent_gid=f"level-{i - 1}"))

        # Mock all entries available
        entries = {f"level-{i}": make_entry(f"level-{i}") for i in range(4)}
        mock_cache_provider.get_batch.return_value = entries

        chain = await store.get_parent_chain_async("level-4", max_depth=2)

        assert len(chain) == 2  # Stopped at max_depth

    @pytest.mark.asyncio
    async def test_parent_chain_stops_at_missing(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test parent chain stops when ancestor is missing from cache."""
        await store.put_async(make_task("grandparent"))
        await store.put_async(make_task("parent", parent_gid="grandparent"))
        await store.put_async(make_task("child", parent_gid="parent"))

        # Parent is in cache but grandparent is not
        p_entry = make_entry("parent")
        mock_cache_provider.get_batch.return_value = {
            "parent": p_entry,
            "grandparent": None,  # Missing
        }

        chain = await store.get_parent_chain_async("child")

        # Should stop at parent since grandparent is missing
        assert len(chain) == 1
        assert chain[0]["gid"] == "parent"


class TestUnifiedTaskStoreInvalidate:
    """Tests for invalidate method."""

    def test_invalidate_single(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test invalidating single task."""
        store.invalidate("task-123")

        mock_cache_provider.invalidate.assert_called_once_with(
            "task-123", [EntryType.TASK]
        )

    @pytest.mark.asyncio
    async def test_invalidate_cascade(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test cascade invalidation of parent and descendants."""
        # Build hierarchy
        await store.put_async(make_task("parent"))
        await store.put_async(make_task("child-1", parent_gid="parent"))
        await store.put_async(make_task("child-2", parent_gid="parent"))

        store.invalidate("parent", cascade=True)

        # Should invalidate parent + both children
        assert mock_cache_provider.invalidate.call_count == 3

    @pytest.mark.asyncio
    async def test_invalidate_removes_from_hierarchy(
        self, store: UnifiedTaskStore
    ) -> None:
        """Test that invalidate removes task from hierarchy index."""
        await store.put_async(make_task("task-123"))

        assert store._hierarchy.contains("task-123")

        store.invalidate("task-123")

        assert not store._hierarchy.contains("task-123")


class TestUnifiedTaskStoreFreshness:
    """Tests for check_freshness_batch_async method."""

    @pytest.mark.asyncio
    async def test_check_freshness_empty(self, store: UnifiedTaskStore) -> None:
        """Test freshness check with empty list."""
        result = await store.check_freshness_batch_async([])

        assert result == {}

    @pytest.mark.asyncio
    async def test_check_freshness_all_missing(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test freshness check when all entries missing from cache."""
        mock_cache_provider.get_batch.return_value = {
            "task-1": None,
            "task-2": None,
        }

        result = await store.check_freshness_batch_async(["task-1", "task-2"])

        assert result == {"task-1": False, "task-2": False}

    @pytest.mark.asyncio
    async def test_check_freshness_fresh_entries(
        self,
        store: UnifiedTaskStore,
        mock_cache_provider: MagicMock,
        mock_batch_client: MagicMock,
    ) -> None:
        """Test freshness check with fresh entries."""
        entry = make_entry("task-1", modified_at="2025-12-23T10:00:00.000Z")
        mock_cache_provider.get_batch.return_value = {"task-1": entry}

        # API returns same version
        mock_batch_client.execute_async.return_value = [
            make_batch_result("task-1", "2025-12-23T10:00:00.000Z")
        ]

        result = await store.check_freshness_batch_async(["task-1"])

        assert result["task-1"] is True


class TestUnifiedTaskStoreStats:
    """Tests for statistics tracking."""

    @pytest.mark.asyncio
    async def test_stats_tracking(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test that stats are tracked correctly."""
        # Put
        await store.put_async(make_task("task-1"))

        # Get miss
        mock_cache_provider.get_versioned.return_value = None
        await store.get_async("task-2")

        # Get hit (immediate)
        entry = make_entry("task-3")
        mock_cache_provider.get_versioned.return_value = entry
        await store.get_async("task-3", freshness=FreshnessMode.IMMEDIATE)

        stats = store.get_stats()
        assert stats["put_count"] == 1
        assert stats["get_misses"] >= 1
        assert stats["get_hits"] >= 1

    def test_reset_stats(self, store: UnifiedTaskStore) -> None:
        """Test that reset_stats clears all statistics."""
        store._stats["put_count"] = 10
        store._stats["get_hits"] = 5

        store.reset_stats()

        stats = store.get_stats()
        for value in stats.values():
            assert value == 0


class TestUnifiedTaskStoreAccessors:
    """Tests for accessor methods."""

    def test_get_hierarchy_index(self, store: UnifiedTaskStore) -> None:
        """Test get_hierarchy_index returns the index."""
        hierarchy = store.get_hierarchy_index()

        assert hierarchy is store._hierarchy

    def test_get_freshness_coordinator(self, store: UnifiedTaskStore) -> None:
        """Test get_freshness_coordinator returns the coordinator."""
        coordinator = store.get_freshness_coordinator()

        assert coordinator is store._freshness


class TestUnifiedTaskStoreMetadata:
    """Tests for metadata extraction."""

    @pytest.mark.asyncio
    async def test_extracts_parent_gid(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test that parent_gid is extracted to metadata."""
        task = make_task("child", parent_gid="parent")

        await store.put_async(task)

        call_args = mock_cache_provider.set_versioned.call_args
        entry = call_args[0][1]
        assert entry.metadata.get("parent_gid") == "parent"

    @pytest.mark.asyncio
    async def test_extracts_project_gids(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test that project_gids are extracted to metadata."""
        task = {
            "gid": "task-1",
            "name": "Test",
            "modified_at": "2025-12-23T10:00:00.000Z",
            "projects": [
                {"gid": "proj-1", "name": "Project 1"},
                {"gid": "proj-2", "name": "Project 2"},
            ],
        }

        await store.put_async(task)

        call_args = mock_cache_provider.set_versioned.call_args
        entry = call_args[0][1]
        assert entry.metadata.get("project_gids") == ["proj-1", "proj-2"]


class TestUnifiedTaskStoreCompleteness:
    """Tests for cache completeness integration.

    Per TDD-CACHE-COMPLETENESS-001 Section 12.1:
    - TC-001: MINIMAL entry, STANDARD required -> returns None
    - TC-002: STANDARD entry, STANDARD required -> returns data
    - TC-003: FULL entry, STANDARD required -> returns data
    - TC-004: UNKNOWN entry, MINIMAL required -> returns data
    - TC-005: UNKNOWN entry, STANDARD required -> returns None
    """

    @pytest.mark.asyncio
    async def test_tc001_minimal_entry_standard_required_returns_none(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """TC-001: MINIMAL entry with STANDARD required returns None."""
        from autom8_asana.cache.completeness import CompletenessLevel

        # Create entry with MINIMAL completeness (level=10)
        entry = make_entry("task-123")
        # Add MINIMAL completeness metadata
        entry = CacheEntry(
            key=entry.key,
            data=entry.data,
            entry_type=entry.entry_type,
            version=entry.version,
            cached_at=entry.cached_at,
            ttl=entry.ttl,
            metadata={"completeness_level": CompletenessLevel.MINIMAL.value},
        )
        mock_cache_provider.get_versioned.return_value = entry

        result = await store.get_async(
            "task-123",
            freshness=FreshnessMode.IMMEDIATE,
            required_level=CompletenessLevel.STANDARD,
        )

        assert result is None
        assert store._stats["completeness_misses"] == 1

    @pytest.mark.asyncio
    async def test_tc002_standard_entry_standard_required_returns_data(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """TC-002: STANDARD entry with STANDARD required returns data."""
        from autom8_asana.cache.completeness import CompletenessLevel

        entry = make_entry("task-123")
        # Add STANDARD completeness metadata
        entry = CacheEntry(
            key=entry.key,
            data=entry.data,
            entry_type=entry.entry_type,
            version=entry.version,
            cached_at=entry.cached_at,
            ttl=entry.ttl,
            metadata={"completeness_level": CompletenessLevel.STANDARD.value},
        )
        mock_cache_provider.get_versioned.return_value = entry

        result = await store.get_async(
            "task-123",
            freshness=FreshnessMode.IMMEDIATE,
            required_level=CompletenessLevel.STANDARD,
        )

        assert result == entry.data
        assert store._stats["completeness_misses"] == 0
        assert store._stats["get_hits"] == 1

    @pytest.mark.asyncio
    async def test_tc003_full_entry_standard_required_returns_data(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """TC-003: FULL entry with STANDARD required returns data."""
        from autom8_asana.cache.completeness import CompletenessLevel

        entry = make_entry("task-123")
        # Add FULL completeness metadata
        entry = CacheEntry(
            key=entry.key,
            data=entry.data,
            entry_type=entry.entry_type,
            version=entry.version,
            cached_at=entry.cached_at,
            ttl=entry.ttl,
            metadata={"completeness_level": CompletenessLevel.FULL.value},
        )
        mock_cache_provider.get_versioned.return_value = entry

        result = await store.get_async(
            "task-123",
            freshness=FreshnessMode.IMMEDIATE,
            required_level=CompletenessLevel.STANDARD,
        )

        assert result == entry.data
        assert store._stats["completeness_misses"] == 0
        assert store._stats["get_hits"] == 1

    @pytest.mark.asyncio
    async def test_tc004_unknown_entry_minimal_required_returns_data(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """TC-004: UNKNOWN (legacy) entry with MINIMAL required returns data."""
        from autom8_asana.cache.completeness import CompletenessLevel

        # Entry without completeness metadata (legacy)
        entry = make_entry("task-123", completeness_level=None)
        mock_cache_provider.get_versioned.return_value = entry

        result = await store.get_async(
            "task-123",
            freshness=FreshnessMode.IMMEDIATE,
            required_level=CompletenessLevel.MINIMAL,
        )

        assert result == entry.data
        assert store._stats["completeness_misses"] == 0
        assert store._stats["get_hits"] == 1

    @pytest.mark.asyncio
    async def test_tc005_unknown_entry_standard_required_returns_none(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """TC-005: UNKNOWN (legacy) entry with STANDARD required returns None."""
        from autom8_asana.cache.completeness import CompletenessLevel

        # Entry without completeness metadata (legacy)
        entry = make_entry("task-123", completeness_level=None)
        mock_cache_provider.get_versioned.return_value = entry

        result = await store.get_async(
            "task-123",
            freshness=FreshnessMode.IMMEDIATE,
            required_level=CompletenessLevel.STANDARD,
        )

        assert result is None
        assert store._stats["completeness_misses"] == 1

    @pytest.mark.asyncio
    async def test_put_async_with_opt_fields_stores_completeness(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test put_async stores completeness metadata based on opt_fields."""
        from autom8_asana.cache.completeness import CompletenessLevel

        task = make_task("task-123")

        # Put with gid-only opt_fields (MINIMAL)
        await store.put_async(task, opt_fields=["gid"])

        call_args = mock_cache_provider.set_versioned.call_args
        entry = call_args[0][1]
        assert (
            entry.metadata.get("completeness_level") == CompletenessLevel.MINIMAL.value
        )
        assert entry.metadata.get("opt_fields_used") == ["gid"]

    @pytest.mark.asyncio
    async def test_put_async_with_standard_fields_stores_standard_level(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test put_async with standard fields stores STANDARD level."""
        from autom8_asana.cache.completeness import CompletenessLevel

        task = make_task("task-123")

        # Put with standard opt_fields
        opt_fields = ["gid", "name", "custom_fields", "parent"]
        await store.put_async(task, opt_fields=opt_fields)

        call_args = mock_cache_provider.set_versioned.call_args
        entry = call_args[0][1]
        assert (
            entry.metadata.get("completeness_level") == CompletenessLevel.STANDARD.value
        )

    @pytest.mark.asyncio
    async def test_put_async_without_opt_fields_stores_unknown_level(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test put_async without opt_fields stores UNKNOWN level."""
        from autom8_asana.cache.completeness import CompletenessLevel

        task = make_task("task-123")

        # Put without opt_fields (legacy behavior)
        await store.put_async(task)

        call_args = mock_cache_provider.set_versioned.call_args
        entry = call_args[0][1]
        assert (
            entry.metadata.get("completeness_level") == CompletenessLevel.UNKNOWN.value
        )

    @pytest.mark.asyncio
    async def test_put_batch_async_with_opt_fields_stores_completeness(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test put_batch_async stores completeness for all entries."""
        from autom8_asana.cache.completeness import CompletenessLevel

        tasks = [make_task("task-1"), make_task("task-2")]

        await store.put_batch_async(tasks, opt_fields=["gid"])

        call_args = mock_cache_provider.set_batch.call_args
        entries = call_args[0][0]

        for gid, entry in entries.items():
            assert (
                entry.metadata.get("completeness_level")
                == CompletenessLevel.MINIMAL.value
            )

    @pytest.mark.asyncio
    async def test_get_batch_async_filters_insufficient_entries(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test get_batch_async returns None for insufficient entries."""
        from autom8_asana.cache.completeness import CompletenessLevel

        # Create two entries: one MINIMAL, one STANDARD
        minimal_entry = CacheEntry(
            key="task-1",
            data={"gid": "task-1", "name": "Task 1"},
            entry_type=EntryType.TASK,
            version=make_entry("task-1").version,
            cached_at=make_entry("task-1").cached_at,
            ttl=300,
            metadata={"completeness_level": CompletenessLevel.MINIMAL.value},
        )
        standard_entry = CacheEntry(
            key="task-2",
            data={"gid": "task-2", "name": "Task 2"},
            entry_type=EntryType.TASK,
            version=make_entry("task-2").version,
            cached_at=make_entry("task-2").cached_at,
            ttl=300,
            metadata={"completeness_level": CompletenessLevel.STANDARD.value},
        )
        mock_cache_provider.get_batch.return_value = {
            "task-1": minimal_entry,
            "task-2": standard_entry,
        }

        result = await store.get_batch_async(
            ["task-1", "task-2"],
            freshness=FreshnessMode.IMMEDIATE,
            required_level=CompletenessLevel.STANDARD,
        )

        # MINIMAL entry should be filtered out
        assert result["task-1"] is None
        assert result["task-2"] == standard_entry.data
        assert store._stats["completeness_misses"] == 1

    @pytest.mark.asyncio
    async def test_default_required_level_is_standard(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test that default required_level is STANDARD to preserve behavior."""
        from autom8_asana.cache.completeness import CompletenessLevel

        # MINIMAL entry should fail with default (STANDARD)
        minimal_entry = CacheEntry(
            key="task-123",
            data={"gid": "task-123"},
            entry_type=EntryType.TASK,
            version=make_entry("task-123").version,
            cached_at=make_entry("task-123").cached_at,
            ttl=300,
            metadata={"completeness_level": CompletenessLevel.MINIMAL.value},
        )
        mock_cache_provider.get_versioned.return_value = minimal_entry

        # Call without explicit required_level (should use default STANDARD)
        result = await store.get_async("task-123", freshness=FreshnessMode.IMMEDIATE)

        assert result is None
        assert store._stats["completeness_misses"] == 1

    @pytest.mark.asyncio
    async def test_completeness_misses_stat_incremented(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Test completeness_misses stat is properly tracked."""
        from autom8_asana.cache.completeness import CompletenessLevel

        minimal_entry = CacheEntry(
            key="task-123",
            data={"gid": "task-123"},
            entry_type=EntryType.TASK,
            version=make_entry("task-123").version,
            cached_at=make_entry("task-123").cached_at,
            ttl=300,
            metadata={"completeness_level": CompletenessLevel.MINIMAL.value},
        )
        mock_cache_provider.get_versioned.return_value = minimal_entry

        # Multiple get calls should accumulate completeness_misses
        await store.get_async(
            "task-123",
            freshness=FreshnessMode.IMMEDIATE,
            required_level=CompletenessLevel.STANDARD,
        )
        await store.get_async(
            "task-123",
            freshness=FreshnessMode.IMMEDIATE,
            required_level=CompletenessLevel.FULL,
        )

        assert store._stats["completeness_misses"] == 2
