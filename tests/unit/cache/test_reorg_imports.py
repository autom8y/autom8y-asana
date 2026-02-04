"""Verify all cache import paths work after reorganization (TDD-CACHE-REORG-001).

Tests three import strategies:
1. Root __init__.py (from autom8_asana.cache import X)
2. Canonical paths (from autom8_asana.cache.models.entry import X)
3. Subpackage __init__.py (from autom8_asana.cache.models import X)

NOTE: Shim paths (e.g., cache.entry) were removed in Batch B07.
All code now uses canonical paths. Root __init__.py re-exports for public API.
"""


def test_root_imports():
    """Root __init__.py exports are accessible."""
    from autom8_asana.cache import CacheEntry, EntryType, Freshness
    from autom8_asana.cache import TieredCacheProvider, TieredConfig
    from autom8_asana.cache import CacheMetrics, CacheEvent
    from autom8_asana.cache import CacheSettings, TTLSettings, OverflowSettings
    from autom8_asana.cache import StalenessCheckSettings
    from autom8_asana.cache import UnifiedTaskStore, FreshnessMode, HierarchyIndex
    from autom8_asana.cache import LightweightChecker, RequestCoalescer
    from autom8_asana.cache import check_entry_staleness, check_batch_staleness
    from autom8_asana.cache import load_task_entry, load_task_entries, load_batch_entries
    from autom8_asana.cache import CompletenessLevel, AsanaTaskUpgrader

    assert CacheEntry is not None
    assert TieredCacheProvider is not None
    assert TieredConfig is not None
    assert TTLSettings is not None
    assert OverflowSettings is not None
    assert check_batch_staleness is not None
    assert load_task_entry is not None
    assert load_task_entries is not None
    assert load_batch_entries is not None
    assert UnifiedTaskStore is not None


def test_canonical_imports():
    """New canonical paths work."""
    from autom8_asana.cache.models.entry import CacheEntry, EntryType
    from autom8_asana.cache.models.freshness import Freshness
    from autom8_asana.cache.models.freshness_stamp import FreshnessStamp
    from autom8_asana.cache.models.metrics import CacheMetrics, CacheEvent
    from autom8_asana.cache.models.settings import CacheSettings
    from autom8_asana.cache.models.errors import DegradedModeMixin
    from autom8_asana.cache.models.completeness import CompletenessLevel
    from autom8_asana.cache.models.versioning import compare_versions
    from autom8_asana.cache.models.mutation_event import MutationEvent

    from autom8_asana.cache.policies.freshness_policy import FreshnessPolicy
    from autom8_asana.cache.policies.staleness import check_entry_staleness
    from autom8_asana.cache.policies.lightweight_checker import LightweightChecker
    from autom8_asana.cache.policies.coalescer import RequestCoalescer
    from autom8_asana.cache.policies.hierarchy import HierarchyIndex

    from autom8_asana.cache.providers.tiered import TieredCacheProvider
    from autom8_asana.cache.providers.unified import UnifiedTaskStore

    from autom8_asana.cache.integration.mutation_invalidator import MutationInvalidator
    from autom8_asana.cache.integration.factory import CacheProviderFactory
    from autom8_asana.cache.integration.freshness_coordinator import FreshnessMode

    assert CacheEntry is not None
    assert FreshnessStamp is not None
    assert FreshnessPolicy is not None
    assert TieredCacheProvider is not None
    assert MutationInvalidator is not None


# Removed test_shim_imports - shims were deleted in Batch B07.
# All imports now use canonical paths.


def test_subpackage_imports():
    """Subpackage __init__.py re-exports work."""
    from autom8_asana.cache.models import CacheEntry, FreshnessStamp, CacheMetrics
    from autom8_asana.cache.policies import FreshnessPolicy, LightweightChecker
    from autom8_asana.cache.providers import TieredCacheProvider, UnifiedTaskStore
    from autom8_asana.cache.integration import MutationInvalidator, FreshnessMode

    assert CacheEntry is not None
    assert FreshnessPolicy is not None
    assert TieredCacheProvider is not None
    assert MutationInvalidator is not None


# Removed test_shim_module_identity - shims were deleted in Batch B07.
# Module identity is no longer relevant as there's only one canonical path.


def test_no_circular_imports():
    """Importing the cache package succeeds without circular import errors."""
    import importlib

    importlib.reload(importlib.import_module("autom8_asana.cache"))
