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
    from autom8_asana.cache import (  # noqa: F401
        AsanaTaskUpgrader,
        CacheEntry,
        CacheEvent,
        CacheMetrics,
        CacheSettings,
        CompletenessLevel,
        EntryType,
        Freshness,
        FreshnessIntent,
        HierarchyIndex,
        LightweightChecker,
        OverflowSettings,
        RequestCoalescer,
        StalenessCheckSettings,
        TieredCacheProvider,
        TieredConfig,
        TTLSettings,
        UnifiedTaskStore,
        check_batch_staleness,
        check_entry_staleness,
        load_batch_entries,
        load_task_entries,
        load_task_entry,
    )

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
    from autom8_asana.cache.integration.factory import (
        CacheProviderFactory,  # noqa: F401
    )
    from autom8_asana.cache.integration.freshness_coordinator import (
        FreshnessIntent,  # noqa: F401
    )
    from autom8_asana.cache.integration.mutation_invalidator import (
        MutationInvalidator,  # noqa: F401
    )
    from autom8_asana.cache.models.completeness import CompletenessLevel  # noqa: F401
    from autom8_asana.cache.models.entry import CacheEntry, EntryType  # noqa: F401
    from autom8_asana.cache.models.errors import DegradedModeMixin  # noqa: F401
    from autom8_asana.cache.models.freshness import Freshness  # noqa: F401
    from autom8_asana.cache.models.freshness_stamp import FreshnessStamp  # noqa: F401
    from autom8_asana.cache.models.metrics import CacheEvent, CacheMetrics  # noqa: F401
    from autom8_asana.cache.models.mutation_event import MutationEvent  # noqa: F401
    from autom8_asana.cache.models.settings import CacheSettings  # noqa: F401
    from autom8_asana.cache.models.versioning import compare_versions  # noqa: F401
    from autom8_asana.cache.policies.coalescer import RequestCoalescer  # noqa: F401
    from autom8_asana.cache.policies.freshness_policy import (
        FreshnessPolicy,  # noqa: F401
    )
    from autom8_asana.cache.policies.hierarchy import HierarchyIndex  # noqa: F401
    from autom8_asana.cache.policies.lightweight_checker import (
        LightweightChecker,  # noqa: F401
    )
    from autom8_asana.cache.policies.staleness import (
        check_entry_staleness,  # noqa: F401
    )
    from autom8_asana.cache.providers.tiered import TieredCacheProvider  # noqa: F401
    from autom8_asana.cache.providers.unified import UnifiedTaskStore  # noqa: F401

    assert CacheEntry is not None
    assert FreshnessStamp is not None
    assert FreshnessPolicy is not None
    assert TieredCacheProvider is not None
    assert MutationInvalidator is not None


# Removed test_shim_imports - shims were deleted in Batch B07.
# All imports now use canonical paths.


def test_subpackage_imports():
    """Subpackage __init__.py re-exports work."""
    from autom8_asana.cache.integration import (  # noqa: F401
        FreshnessIntent,
        MutationInvalidator,
    )
    from autom8_asana.cache.models import (  # noqa: F401
        CacheEntry,
        CacheMetrics,
        FreshnessStamp,
    )
    from autom8_asana.cache.policies import (  # noqa: F401
        FreshnessPolicy,
        LightweightChecker,
    )
    from autom8_asana.cache.providers import (  # noqa: F401
        TieredCacheProvider,
        UnifiedTaskStore,
    )

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
