---
status: superseded
superseded_by: /docs/reference/REF-cache-architecture.md
superseded_date: 2025-12-24
---

# TDD-CACHE-INTEGRATION: Activate Dormant Cache Infrastructure

**Document ID**: TDD-CACHE-INTEGRATION
**Version**: 1.0
**Date**: 2025-12-22
**Status**: Draft
**Author**: Architect
**PRD**: [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md)
**Discovery**: [DISCOVERY-CACHE-INTEGRATION](../analysis/DISCOVERY-CACHE-INTEGRATION.md)

---

## 1. Overview

This TDD specifies the technical design for wiring up the existing 4,000 lines of dormant cache infrastructure in the autom8_asana SDK. The cache layer is fully implemented but currently bypassed because `AsanaClient.__init__()` defaults to `NullCacheProvider()`.

The design introduces environment-aware default provider selection, TasksClient cache integration, SaveSession invalidation hooks, and entity-type-specific TTLs while maintaining full backward compatibility.

**Key Design Principle**: All new behavior is opt-in. Existing code that passes `cache_provider=NullCacheProvider()` or relies on the previous default behavior continues to work unchanged.

---

## 2. Requirements Summary

Per PRD-CACHE-INTEGRATION, this design addresses:

| Category | Count | Summary |
|----------|-------|---------|
| FR-DEFAULT-* | 6 | Environment-aware provider selection |
| FR-CLIENT-* | 7 | TasksClient.get_async() cache integration |
| FR-INVALIDATE-* | 6 | SaveSession post-commit invalidation |
| FR-TTL-* | 7 | Entity-type specific TTLs |
| FR-DF-* | 2 | DataFrame default caching |
| FR-CONFIG-* | 4 | CacheConfig in AsanaConfig |
| FR-ENV-* | 5 | Environment variable support |
| NFR-PERF-* | 4 | <5ms cache hit latency |
| NFR-COMPAT-* | 4 | Zero breaking changes |
| NFR-DEGRADE-* | 4 | Graceful degradation |

---

## 3. System Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AsanaClient                                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │ CacheConfig  │───>│Provider      │───>│  CacheProvider           │  │
│  │ (new)        │    │Factory (new) │    │  ├─ NullCacheProvider    │  │
│  └──────────────┘    └──────────────┘    │  ├─ InMemoryCacheProvider│  │
│         │                                 │  ├─ RedisCacheProvider   │  │
│         v                                 │  └─ TieredCacheProvider  │  │
│  ┌──────────────────────────────────────┐└──────────────────────────┘  │
│  │          TasksClient                  │            │                 │
│  │  ┌───────────────────────────────┐   │            │                 │
│  │  │ get_async()                   │<──┼────────────┘                 │
│  │  │  1. _cache_get(gid, TASK)     │   │   cache check               │
│  │  │  2. HTTP GET if miss          │   │                             │
│  │  │  3. _cache_set(gid, entry)    │   │   cache store               │
│  │  └───────────────────────────────┘   │                             │
│  └──────────────────────────────────────┘                             │
│                                                                         │
│  ┌──────────────────────────────────────┐                             │
│  │          SaveSession                  │                             │
│  │  ┌───────────────────────────────┐   │                             │
│  │  │ commit_async()                │   │                             │
│  │  │  ...Phase 1: CRUD...          │   │                             │
│  │  │  ...Phase 1.5: Invalidate...  │<──┼──── NEW: cache invalidation │
│  │  │  ...Phase 2: Cascade...       │   │                             │
│  │  └───────────────────────────────┘   │                             │
│  └──────────────────────────────────────┘                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Architecture

### 4.1 CacheConfig (NEW)

**Location**: `src/autom8_asana/config.py`

**Purpose**: Cache configuration nested within AsanaConfig, following the existing pattern for RateLimitConfig, RetryConfig, etc.

```python
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.cache.freshness import Freshness
    from autom8_asana.cache.settings import TTLSettings, OverflowSettings


@dataclass
class CacheConfig:
    """Cache configuration with environment variable overrides.

    Environment Variables:
        ASANA_CACHE_ENABLED: Master enable/disable ("true"/"false")
        ASANA_CACHE_PROVIDER: Explicit provider selection
        ASANA_CACHE_TTL_DEFAULT: Default TTL in seconds
        ASANA_ENVIRONMENT: Environment hint for auto-detection

    Attributes:
        enabled: Whether caching is enabled (default True).
        provider: Explicit provider name ("memory", "redis", "tiered", "none").
            None means auto-detect based on environment.
        ttl: TTL configuration settings.
        overflow: Overflow threshold settings.
        freshness: Default freshness mode for cache reads.
        dataframe_caching: Whether DataFrame operations use caching.

    Example:
        >>> config = CacheConfig(enabled=True, provider="memory")
        >>> client = AsanaClient(config=AsanaConfig(cache=config))
    """

    enabled: bool = True
    provider: str | None = None  # None = auto-detect
    ttl: "TTLSettings" = field(default_factory=lambda: TTLSettings())
    overflow: "OverflowSettings" = field(default_factory=lambda: OverflowSettings())
    freshness: "Freshness" = field(default_factory=lambda: Freshness.EVENTUAL)
    dataframe_caching: bool = True

    @classmethod
    def from_env(cls) -> "CacheConfig":
        """Create configuration from environment variables.

        Reads ASANA_CACHE_* environment variables and creates
        a CacheConfig instance. Programmatic config always takes
        precedence when passed to AsanaClient.

        Returns:
            CacheConfig populated from environment variables.
        """
        import os
        from autom8_asana.cache.settings import TTLSettings

        enabled_str = os.environ.get("ASANA_CACHE_ENABLED", "true").lower()
        enabled = enabled_str not in ("false", "0", "no")

        provider = os.environ.get("ASANA_CACHE_PROVIDER") or None
        if provider:
            provider = provider.lower()

        default_ttl = int(os.environ.get("ASANA_CACHE_TTL_DEFAULT", "300"))

        return cls(
            enabled=enabled,
            provider=provider,
            ttl=TTLSettings(default_ttl=default_ttl),
        )
```

**Integration with AsanaConfig**:

```python
@dataclass
class AsanaConfig:
    """Main configuration for AsanaClient."""

    # ... existing fields ...
    cache: CacheConfig = field(default_factory=CacheConfig)
```

**Traceability**: FR-CONFIG-001, FR-CONFIG-002, FR-CONFIG-003, FR-CONFIG-004

---

### 4.2 Provider Factory (NEW)

**Location**: `src/autom8_asana/cache/factory.py`

**Purpose**: Environment-aware provider instantiation following the priority order defined in FR-DEFAULT-002.

```python
"""Cache provider factory with environment-aware selection."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.config import CacheConfig
    from autom8_asana.protocols.cache import CacheProvider

logger = logging.getLogger(__name__)


class CacheProviderFactory:
    """Factory for creating cache providers based on configuration.

    Selection Priority (per FR-DEFAULT-002):
        1. Explicit cache_provider parameter (handled in AsanaClient)
        2. CacheConfig.provider setting (from env or programmatic)
        3. Environment-based auto-detection
        4. InMemoryCacheProvider fallback

    Environment Detection (per FR-DEFAULT-005, FR-DEFAULT-006):
        - ASANA_ENVIRONMENT=production/staging: Prefer Redis if configured
        - ASANA_ENVIRONMENT=development/test or not set: Use InMemory
    """

    @staticmethod
    def create(config: CacheConfig) -> CacheProvider:
        """Create a cache provider based on configuration.

        Args:
            config: CacheConfig with provider settings.

        Returns:
            Configured CacheProvider instance.

        Raises:
            ConfigurationError: If explicit provider requires
                configuration that is missing (e.g., redis without REDIS_HOST).
        """
        from autom8_asana._defaults.cache import NullCacheProvider, InMemoryCacheProvider
        from autom8_asana.exceptions import ConfigurationError

        # FR-DEFAULT-004: Master enable/disable switch
        if not config.enabled:
            logger.debug("Cache disabled via config.enabled=False")
            return NullCacheProvider()

        # FR-DEFAULT-003: Explicit provider selection
        if config.provider:
            return CacheProviderFactory._create_explicit(config.provider, config)

        # FR-DEFAULT-005, FR-DEFAULT-006: Environment-based auto-detection
        return CacheProviderFactory._auto_detect(config)

    @staticmethod
    def _create_explicit(provider_name: str, config: CacheConfig) -> CacheProvider:
        """Create explicitly specified provider.

        Args:
            provider_name: Provider name ("memory", "redis", "tiered", "none").
            config: CacheConfig for TTL and other settings.

        Returns:
            Configured CacheProvider.

        Raises:
            ConfigurationError: If provider requires missing configuration.
        """
        from autom8_asana._defaults.cache import NullCacheProvider, InMemoryCacheProvider
        from autom8_asana.exceptions import ConfigurationError

        provider_name = provider_name.lower()

        if provider_name in ("none", "null"):
            return NullCacheProvider()

        if provider_name == "memory":
            return InMemoryCacheProvider(
                default_ttl=config.ttl.default_ttl,
                max_size=10000,
            )

        if provider_name == "redis":
            redis_host = os.environ.get("REDIS_HOST")
            if not redis_host:
                raise ConfigurationError(
                    "ASANA_CACHE_PROVIDER=redis requires REDIS_HOST environment variable"
                )
            return CacheProviderFactory._create_redis_provider(config)

        if provider_name == "tiered":
            redis_host = os.environ.get("REDIS_HOST")
            if not redis_host:
                raise ConfigurationError(
                    "ASANA_CACHE_PROVIDER=tiered requires REDIS_HOST environment variable"
                )
            return CacheProviderFactory._create_tiered_provider(config)

        raise ConfigurationError(
            f"Unknown cache provider: '{provider_name}'. "
            f"Valid options: memory, redis, tiered, none"
        )

    @staticmethod
    def _auto_detect(config: CacheConfig) -> CacheProvider:
        """Auto-detect provider based on environment.

        Args:
            config: CacheConfig for TTL and other settings.

        Returns:
            Appropriate CacheProvider for the environment.
        """
        from autom8_asana._defaults.cache import NullCacheProvider, InMemoryCacheProvider

        environment = os.environ.get("ASANA_ENVIRONMENT", "development").lower()
        redis_host = os.environ.get("REDIS_HOST")

        if environment in ("production", "staging"):
            if redis_host:
                logger.info(
                    "Production environment with Redis configured, using RedisCacheProvider"
                )
                return CacheProviderFactory._create_redis_provider(config)
            else:
                logger.warning(
                    "Production environment without REDIS_HOST configured. "
                    "Using InMemoryCacheProvider as fallback. "
                    "Set REDIS_HOST for production-grade caching or "
                    "ASANA_CACHE_PROVIDER=none to disable caching."
                )
                return InMemoryCacheProvider(
                    default_ttl=config.ttl.default_ttl,
                    max_size=10000,
                )
        else:
            # Development/test: use in-memory
            logger.debug(
                "Development environment, using InMemoryCacheProvider (default_ttl=%d)",
                config.ttl.default_ttl,
            )
            return InMemoryCacheProvider(
                default_ttl=config.ttl.default_ttl,
                max_size=10000,
            )

    @staticmethod
    def _create_redis_provider(config: CacheConfig) -> CacheProvider:
        """Create Redis cache provider from environment.

        Uses REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_SSL
        environment variables.
        """
        from autom8_asana.cache.autom8_adapter import create_autom8_cache_provider

        return create_autom8_cache_provider()

    @staticmethod
    def _create_tiered_provider(config: CacheConfig) -> CacheProvider:
        """Create tiered cache provider (Redis hot + S3 cold).

        Uses existing TieredCacheProvider infrastructure.
        """
        # For Phase 1, tiered maps to Redis (S3 cold tier is Phase 3)
        return CacheProviderFactory._create_redis_provider(config)
```

**Traceability**: FR-DEFAULT-001 through FR-DEFAULT-006, FR-ENV-001 through FR-ENV-005

---

### 4.3 AsanaClient Cache Integration (MODIFY)

**Location**: `src/autom8_asana/client.py`

**Purpose**: Wire CacheConfig and provider factory into client initialization.

**Changes to `__init__`**:

```python
def __init__(
    self,
    token: str | None = None,
    *,
    workspace_gid: str | None = None,
    auth_provider: AuthProvider | None = None,
    cache_provider: CacheProvider | None = None,  # UNCHANGED - backward compat
    log_provider: LogProvider | None = None,
    config: AsanaConfig | None = None,
    observability_hook: ObservabilityHook | None = None,
) -> None:
    """Initialize AsanaClient.

    Args:
        ...existing docstring...
        cache_provider: Custom cache provider. If None, uses environment-aware
            auto-selection based on config.cache settings. Pass
            NullCacheProvider() explicitly to disable all caching.
    """
    self._config = config or AsanaConfig()

    # ... existing auth provider resolution ...

    # Resolve cache provider with priority:
    # 1. Explicit cache_provider parameter (backward compat)
    # 2. CacheConfig-based selection via factory
    if cache_provider is not None:
        # FR-CLIENT-006: Explicit provider takes precedence
        self._cache_provider: CacheProvider = cache_provider
    else:
        # FR-DEFAULT-001: Use factory for environment-aware selection
        from autom8_asana.cache.factory import CacheProviderFactory
        self._cache_provider = CacheProviderFactory.create(self._config.cache)

    # ... rest of initialization unchanged ...
```

**Backward Compatibility** (NFR-COMPAT-001, NFR-COMPAT-004):
- `AsanaClient()` without arguments now gets environment-aware caching (enhancement)
- `AsanaClient(cache_provider=NullCacheProvider())` continues to work exactly as before
- `AsanaClient(cache_provider=MyProvider())` continues to work exactly as before

---

### 4.4 BaseClient Cache Helpers (MODIFY)

**Location**: `src/autom8_asana/clients/base.py`

**Purpose**: Add reusable cache check/store pattern methods for use by TasksClient and other clients.

```python
"""Base client class for all resource clients."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.cache.entry import CacheEntry, EntryType
    from autom8_asana.config import AsanaConfig
    from autom8_asana.protocols.auth import AuthProvider
    from autom8_asana.protocols.cache import CacheProvider
    from autom8_asana.protocols.log import LogProvider
    from autom8_asana.transport.http import AsyncHTTPClient

logger = logging.getLogger(__name__)


class BaseClient:
    """Base class for resource-specific clients.

    Provides common functionality including cache helpers for
    the check-before-HTTP, store-on-miss pattern.
    """

    # ... existing __init__ unchanged ...

    def _cache_get(
        self,
        key: str,
        entry_type: "EntryType",
    ) -> "CacheEntry | None":
        """Check cache for an entry (graceful degradation).

        Per NFR-DEGRADE-001: Cache failures log warnings without raising.

        Args:
            key: Cache key (typically task GID).
            entry_type: Type of cache entry.

        Returns:
            CacheEntry if found and not expired, None otherwise.
        """
        if self._cache is None:
            return None

        try:
            entry = self._cache.get_versioned(key, entry_type)
            if entry is not None and not entry.is_expired():
                return entry
            return None
        except Exception as exc:
            # NFR-DEGRADE-001: Log and continue
            logger.warning(
                "Cache get failed for %s (key=%s): %s",
                entry_type.value,
                key,
                exc,
            )
            return None

    def _cache_set(
        self,
        key: str,
        data: dict[str, Any],
        entry_type: "EntryType",
        ttl: int | None = None,
    ) -> None:
        """Store data in cache (graceful degradation).

        Per NFR-DEGRADE-004: Operation succeeds even if caching fails.

        Args:
            key: Cache key (typically task GID).
            data: Data to cache (typically API response dict).
            entry_type: Type of cache entry.
            ttl: Time-to-live in seconds. If None, uses default.
        """
        if self._cache is None:
            return

        try:
            from autom8_asana.cache.entry import CacheEntry

            # Extract version from modified_at if present
            modified_at = data.get("modified_at")
            if modified_at:
                version = self._parse_modified_at(modified_at)
            else:
                version = datetime.now(timezone.utc)

            entry = CacheEntry(
                key=key,
                data=data,
                entry_type=entry_type,
                version=version,
                ttl=ttl or self._config.cache.ttl.default_ttl if hasattr(self._config, 'cache') else 300,
            )
            self._cache.set_versioned(key, entry)
        except Exception as exc:
            # NFR-DEGRADE-004: Log and continue
            logger.warning(
                "Cache set failed for %s (key=%s): %s",
                entry_type.value,
                key,
                exc,
            )

    def _cache_invalidate(
        self,
        key: str,
        entry_types: list["EntryType"] | None = None,
    ) -> None:
        """Invalidate cache entries for a key (graceful degradation).

        Args:
            key: Cache key to invalidate (typically task GID).
            entry_types: Entry types to invalidate. None = all types.
        """
        if self._cache is None:
            return

        try:
            self._cache.invalidate(key, entry_types)
        except Exception as exc:
            logger.warning(
                "Cache invalidate failed (key=%s): %s",
                key,
                exc,
            )

    @staticmethod
    def _parse_modified_at(value: str | datetime) -> datetime:
        """Parse modified_at to datetime.

        Args:
            value: ISO format string or datetime.

        Returns:
            Timezone-aware datetime (UTC).
        """
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value

        # Handle ISO format with Z suffix
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    # ... existing methods unchanged ...
```

**Traceability**: FR-CLIENT-003, NFR-DEGRADE-001, NFR-DEGRADE-004

---

### 4.5 TasksClient Cache Integration (MODIFY)

**Location**: `src/autom8_asana/clients/tasks.py`

**Purpose**: Wire `get_async()` to use cache with check-before-HTTP, store-on-miss pattern.

```python
from autom8_asana.cache.entry import EntryType

class TasksClient(BaseClient):
    """Client for Asana Task operations with caching support."""

    # ... existing __init__ unchanged ...

    @error_handler
    async def get_async(
        self,
        task_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Task | dict[str, Any]:
        """Get a task by GID with cache support.

        Per FR-CLIENT-001: Checks cache before HTTP request.
        Per FR-CLIENT-002: Uses task GID as cache key with EntryType.TASK.
        Per FR-CLIENT-004: Respects TTL expiration.
        Per FR-CLIENT-007: raw=True returns cached dict directly.

        Args:
            task_gid: Task GID.
            raw: If True, return raw dict instead of Task model.
            opt_fields: Optional fields to include.

        Returns:
            Task model by default, or dict if raw=True.
        """
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")

        # FR-CLIENT-001: Check cache first
        cached_entry = self._cache_get(task_gid, EntryType.TASK)
        if cached_entry is not None:
            # Cache hit
            data = cached_entry.data
            if raw:
                return data
            task = Task.model_validate(data)
            task._client = self._client
            return task

        # Cache miss: fetch from API
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/tasks/{task_gid}", params=params)

        # Store in cache with entity-type TTL
        ttl = self._resolve_entity_ttl(data)
        self._cache_set(task_gid, data, EntryType.TASK, ttl=ttl)

        if raw:
            return data
        task = Task.model_validate(data)
        task._client = self._client
        return task

    def _resolve_entity_ttl(self, data: dict[str, Any]) -> int:
        """Resolve TTL based on entity type detection.

        Per FR-TTL-001 through FR-TTL-005: Different TTLs for
        Business (3600s), Contact/Unit (900s), Offer (180s),
        Process (60s), and generic tasks (300s).

        Args:
            data: Task data dict from API.

        Returns:
            TTL in seconds.
        """
        # Entity type TTL defaults (per Discovery Section E.1)
        ENTITY_TTLS = {
            "business": 3600,
            "contact": 900,
            "unit": 900,
            "offer": 180,
            "process": 60,
        }

        # Check config overrides first (FR-TTL-006)
        if hasattr(self._config, 'cache'):
            config_ttls = self._config.cache.ttl.entry_type_ttls
            for entity_type, ttl in config_ttls.items():
                if entity_type.lower() in ENTITY_TTLS:
                    ENTITY_TTLS[entity_type.lower()] = ttl

        # Try to detect entity type from data
        entity_type = self._detect_entity_type(data)
        if entity_type and entity_type.lower() in ENTITY_TTLS:
            return ENTITY_TTLS[entity_type.lower()]

        # FR-TTL-005: Default TTL for generic tasks
        if hasattr(self._config, 'cache'):
            return self._config.cache.ttl.default_ttl
        return 300

    def _detect_entity_type(self, data: dict[str, Any]) -> str | None:
        """Detect entity type from task data.

        Uses existing detection infrastructure if available.

        Args:
            data: Task data dict.

        Returns:
            Entity type name or None if not detectable.
        """
        try:
            from autom8_asana.models.business.detection import detect_entity_type_from_dict
            return detect_entity_type_from_dict(data)
        except ImportError:
            # Detection module not available
            return None
        except Exception:
            # Detection failed, use default
            return None
```

**Traceability**: FR-CLIENT-001 through FR-CLIENT-007, FR-TTL-001 through FR-TTL-007

---

### 4.6 SaveSession Invalidation Hook (MODIFY)

**Location**: `src/autom8_asana/persistence/session.py`

**Purpose**: Invalidate cache entries after successful mutations to prevent stale reads.

**Changes to `commit_async()`**:

```python
async def commit_async(self) -> SaveResult:
    """Execute all pending changes (async).

    Per FR-INVALIDATE-001: Invalidates cache for mutated entities after commit.
    """
    self._ensure_open()

    # ... existing Phase 1 code ...

    # Phase 1: Execute CRUD operations and actions together
    crud_result, action_results = await self._pipeline.execute_with_actions(
        entities=dirty_entities,
        actions=pending_actions,
        action_executor=self._action_executor,
    )

    # NEW: Phase 1.5: Cache invalidation for modified entities
    # Per FR-INVALIDATE-001 through FR-INVALIDATE-006
    await self._invalidate_cache_for_results(crud_result, action_results)

    # ... rest of existing commit_async unchanged ...

async def _invalidate_cache_for_results(
    self,
    crud_result: SaveResult,
    action_results: list[ActionResult],
) -> None:
    """Invalidate cache entries for successfully mutated entities.

    Per FR-INVALIDATE-001: Invalidates after successful mutations.
    Per FR-INVALIDATE-002: UPDATE operations invalidate.
    Per FR-INVALIDATE-003: DELETE operations invalidate.
    Per FR-INVALIDATE-004: CREATE operations warm cache.
    Per FR-INVALIDATE-005: Batch invalidation efficiency (O(n)).
    Per FR-INVALIDATE-006: Action operations invalidate.

    Args:
        crud_result: Result of CRUD operations.
        action_results: Results of action operations.
    """
    if not hasattr(self._client, '_cache_provider') or self._client._cache_provider is None:
        return

    cache = self._client._cache_provider
    from autom8_asana.cache.entry import EntryType

    # Collect all GIDs to invalidate (FR-INVALIDATE-005: batch efficiency)
    gids_to_invalidate: set[str] = set()

    # FR-INVALIDATE-002, FR-INVALIDATE-003: CRUD succeeded entities
    for entity in crud_result.succeeded:
        if hasattr(entity, 'gid') and entity.gid:
            gids_to_invalidate.add(entity.gid)

    # FR-INVALIDATE-006: Action operations
    for action_result in action_results:
        if action_result.success and action_result.action.task:
            if hasattr(action_result.action.task, 'gid'):
                gids_to_invalidate.add(action_result.action.task.gid)

    # Invalidate all collected GIDs
    for gid in gids_to_invalidate:
        try:
            cache.invalidate(gid, [EntryType.TASK, EntryType.SUBTASKS])
        except Exception as exc:
            # NFR-DEGRADE-001: Log and continue
            if self._log:
                self._log.warning(
                    "cache_invalidation_failed",
                    gid=gid,
                    error=str(exc),
                )

    # FR-INVALIDATE-004: Warm cache with newly created entities
    # For creates, we have fresh data - store it instead of invalidating
    for entity in crud_result.succeeded:
        if hasattr(entity, '_operation_type') and entity._operation_type == 'CREATE':
            if hasattr(entity, 'gid') and hasattr(entity, 'model_dump'):
                try:
                    from autom8_asana.cache.entry import CacheEntry
                    from datetime import datetime, timezone

                    entry = CacheEntry(
                        key=entity.gid,
                        data=entity.model_dump(),
                        entry_type=EntryType.TASK,
                        version=datetime.now(timezone.utc),
                        ttl=300,  # Use default TTL for new entities
                    )
                    cache.set_versioned(entity.gid, entry)
                except Exception:
                    pass  # Best effort cache warming
```

**Traceability**: FR-INVALIDATE-001 through FR-INVALIDATE-006

---

### 4.7 Entity TTL Configuration (MODIFY)

**Location**: `src/autom8_asana/cache/settings.py`

**Purpose**: Add entity-type-aware TTL defaults.

```python
@dataclass
class TTLSettings:
    """TTL configuration with entity-type defaults.

    Per FR-TTL-001 through FR-TTL-005:
    - Business: 3600s (1 hour) - rarely changes
    - Contact/Unit: 900s (15 min) - low update frequency
    - Offer: 180s (3 min) - frequent pipeline movement
    - Process: 60s (1 min) - very frequent state changes
    - Default: 300s (5 min) - generic tasks

    Attributes:
        default_ttl: Default TTL in seconds (default 300).
        project_ttls: Per-project TTL overrides keyed by project GID.
        entry_type_ttls: Per-entry-type TTL overrides.
        entity_type_ttls: Per-entity-type TTL overrides (Business, Contact, etc).
    """

    default_ttl: int = 300
    project_ttls: dict[str, int] = field(default_factory=dict)
    entry_type_ttls: dict[str, int] = field(default_factory=dict)
    entity_type_ttls: dict[str, int] = field(default_factory=lambda: {
        "business": 3600,
        "contact": 900,
        "unit": 900,
        "offer": 180,
        "process": 60,
    })

    def get_ttl(
        self,
        project_gid: str | None = None,
        entry_type: str | EntryType | None = None,
        entity_type: str | None = None,
    ) -> int:
        """Resolve TTL with priority: project > entity_type > entry_type > default.

        Per FR-TTL-006: Priority resolution.

        Args:
            project_gid: Optional project GID for project-specific TTL.
            entry_type: Optional entry type for type-specific TTL.
            entity_type: Optional Business entity type name.

        Returns:
            Resolved TTL in seconds.
        """
        # Highest priority: project-specific
        if project_gid and project_gid in self.project_ttls:
            return self.project_ttls[project_gid]

        # Second priority: entity type (Business, Contact, etc.)
        if entity_type:
            entity_key = entity_type.lower()
            if entity_key in self.entity_type_ttls:
                return self.entity_type_ttls[entity_key]

        # Third priority: entry type (TASK, SUBTASKS, etc.)
        if entry_type:
            type_key = (
                entry_type.value if isinstance(entry_type, EntryType) else entry_type
            )
            if type_key in self.entry_type_ttls:
                return self.entry_type_ttls[type_key]

        return self.default_ttl
```

**Traceability**: FR-TTL-001 through FR-TTL-007

---

## 5. Technical Decisions

| Decision | ADR | Summary |
|----------|-----|---------|
| Default provider selection strategy | [ADR-0123](../decisions/ADR-0123-cache-provider-selection.md) | Environment-aware with detection chain |
| Client cache integration pattern | [ADR-0124](../decisions/ADR-0124-client-cache-pattern.md) | Inline check with helper methods |
| SaveSession invalidation hook | [ADR-0125](../decisions/ADR-0125-savesession-invalidation.md) | Post-commit callback with GID collection |
| Entity-type TTL resolution | [ADR-0126](../decisions/ADR-0126-entity-ttl-resolution.md) | Config-driven with sensible defaults |
| Graceful degradation strategy | [ADR-0127](../decisions/ADR-0127-graceful-degradation.md) | Logged warning with metric increment |

---

## 6. Sequence Diagrams

### 6.1 Cache Hit Flow

```
┌─────────┐      ┌─────────────┐      ┌──────────────┐
│  User   │      │ TasksClient │      │CacheProvider │
└────┬────┘      └──────┬──────┘      └──────┬───────┘
     │                  │                    │
     │ get_async("123") │                    │
     │─────────────────>│                    │
     │                  │                    │
     │                  │ _cache_get("123", TASK)
     │                  │───────────────────>│
     │                  │                    │
     │                  │   CacheEntry(data) │
     │                  │<───────────────────│
     │                  │                    │
     │                  │ entry.is_expired()?│
     │                  │ ─> False           │
     │                  │                    │
     │     Task         │                    │
     │<─────────────────│                    │
     │                  │                    │
     │  (No HTTP call)  │                    │
```

### 6.2 Cache Miss Flow

```
┌─────────┐      ┌─────────────┐      ┌──────────────┐      ┌────────┐
│  User   │      │ TasksClient │      │CacheProvider │      │  HTTP  │
└────┬────┘      └──────┬──────┘      └──────┬───────┘      └────┬───┘
     │                  │                    │                   │
     │ get_async("123") │                    │                   │
     │─────────────────>│                    │                   │
     │                  │                    │                   │
     │                  │ _cache_get("123", TASK)                │
     │                  │───────────────────>│                   │
     │                  │                    │                   │
     │                  │       None         │                   │
     │                  │<───────────────────│                   │
     │                  │                    │                   │
     │                  │ GET /tasks/123     │                   │
     │                  │───────────────────────────────────────>│
     │                  │                    │                   │
     │                  │               {data}                   │
     │                  │<───────────────────────────────────────│
     │                  │                    │                   │
     │                  │ _cache_set("123", data, TASK)          │
     │                  │───────────────────>│                   │
     │                  │                    │                   │
     │     Task         │                    │                   │
     │<─────────────────│                    │                   │
```

### 6.3 SaveSession Invalidation Flow

```
┌─────────┐      ┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│  User   │      │ SaveSession │      │   Pipeline   │      │CacheProvider │
└────┬────┘      └──────┬──────┘      └──────┬───────┘      └──────┬───────┘
     │                  │                    │                    │
     │ commit_async()   │                    │                    │
     │─────────────────>│                    │                    │
     │                  │                    │                    │
     │                  │ Phase 1: CRUD      │                    │
     │                  │───────────────────>│                    │
     │                  │                    │                    │
     │                  │   crud_result      │                    │
     │                  │<───────────────────│                    │
     │                  │                    │                    │
     │                  │ Phase 1.5: Invalidate                   │
     │                  │────────────────────────────────────────>│
     │                  │                    │                    │
     │                  │ invalidate("123", [TASK, SUBTASKS])     │
     │                  │ invalidate("456", [TASK, SUBTASKS])     │
     │                  │                    │                    │
     │                  │ Phase 2: Cascade   │                    │
     │                  │───────────────────>│                    │
     │                  │                    │                    │
     │   SaveResult     │                    │                    │
     │<─────────────────│                    │                    │
```

### 6.4 Graceful Degradation Flow

```
┌─────────┐      ┌─────────────┐      ┌──────────────┐      ┌────────┐
│  User   │      │ TasksClient │      │CacheProvider │      │  HTTP  │
└────┬────┘      └──────┬──────┘      └──────┬───────┘      └────┬───┘
     │                  │                    │                   │
     │ get_async("123") │                    │                   │
     │─────────────────>│                    │                   │
     │                  │                    │                   │
     │                  │ _cache_get("123", TASK)                │
     │                  │───────────────────>│                   │
     │                  │                    │                   │
     │                  │   ConnectionError! │                   │
     │                  │<───────────────────│                   │
     │                  │                    │                   │
     │                  │ [Log warning]      │                   │
     │                  │ return None        │                   │
     │                  │                    │                   │
     │                  │ GET /tasks/123 (fallback to HTTP)      │
     │                  │───────────────────────────────────────>│
     │                  │                    │                   │
     │                  │               {data}                   │
     │                  │<───────────────────────────────────────│
     │                  │                    │                   │
     │                  │ _cache_set (best effort, may fail)     │
     │                  │───────────────────>│                   │
     │                  │                    │                   │
     │     Task         │ [Logged if fails]  │                   │
     │<─────────────────│                    │                   │
```

---

## 7. Module Modification Summary

| File | Change | Scope |
|------|--------|-------|
| `config.py` | Add CacheConfig dataclass | NEW CLASS |
| `config.py` | Add cache field to AsanaConfig | 1 line |
| `cache/factory.py` | Create provider factory | NEW FILE (~120 lines) |
| `client.py` | Integrate factory in __init__ | ~10 lines |
| `clients/base.py` | Add cache helper methods | ~60 lines |
| `clients/tasks.py` | Wire get_async() to cache | ~40 lines |
| `persistence/session.py` | Add invalidation hook | ~50 lines |
| `cache/settings.py` | Add entity_type_ttls | ~10 lines |

**Total estimated changes**: ~300 lines (new) + ~100 lines (modified)

---

## 8. Interface Contracts

### 8.1 CacheConfig --> AsanaConfig

```python
# Access pattern
config = AsanaConfig(cache=CacheConfig(enabled=True, provider="memory"))
client = AsanaClient(config=config)

# Or use environment
config = AsanaConfig(cache=CacheConfig.from_env())
```

### 8.2 Provider Factory --> AsanaClient

```python
# Factory is called from AsanaClient.__init__ if no explicit cache_provider
provider = CacheProviderFactory.create(self._config.cache)
self._cache_provider = provider
```

### 8.3 BaseClient --> TasksClient

```python
# TasksClient inherits cache helpers
class TasksClient(BaseClient):
    async def get_async(self, task_gid: str, ...) -> Task:
        entry = self._cache_get(task_gid, EntryType.TASK)  # From BaseClient
        if entry:
            return Task.model_validate(entry.data)
        # ... fetch and cache ...
        self._cache_set(task_gid, data, EntryType.TASK)  # From BaseClient
```

### 8.4 SaveSession --> CacheProvider

```python
# SaveSession calls invalidate via client's cache provider
cache = self._client._cache_provider
cache.invalidate(gid, [EntryType.TASK, EntryType.SUBTASKS])
```

### 8.5 CacheSettings --> CacheProvider

```python
# TTL resolution chain
ttl = settings.get_ttl(entity_type="business")  # Returns 3600
ttl = settings.get_ttl(entity_type="offer")     # Returns 180
ttl = settings.get_ttl()                         # Returns 300 (default)
```

---

## 9. Test Strategy

### 9.1 Unit Tests

| Component | Test File | Coverage Target |
|-----------|-----------|-----------------|
| CacheConfig | `tests/unit/test_config.py` | from_env(), field validation |
| CacheProviderFactory | `tests/unit/cache/test_factory.py` | All provider types, error cases |
| BaseClient cache helpers | `tests/unit/clients/test_base_cache.py` | get/set/invalidate, error handling |
| TasksClient cache | `tests/unit/clients/test_tasks_cache.py` | Hit/miss/TTL scenarios |
| SaveSession invalidation | `tests/unit/persistence/test_session_cache.py` | CRUD/action invalidation |
| TTLSettings | `tests/unit/cache/test_settings.py` | Priority resolution |

### 9.2 Integration Tests

| Scenario | Test File | Requirements |
|----------|-----------|--------------|
| End-to-end cache hit | `tests/integration/test_cache_integration.py` | InMemoryCacheProvider |
| Redis provider | `tests/integration/test_redis_cache.py` | Docker Compose with Redis |
| Environment detection | `tests/integration/test_env_detection.py` | Environment variable manipulation |

### 9.3 Performance Tests

| Metric | Target | Test |
|--------|--------|------|
| Cache hit latency | <5ms p99 | Benchmark 1000 cache hits |
| Cache miss overhead | <10ms | Compare cached vs uncached |
| Memory bounded | <100MB for 10k entries | Memory profiling |

### 9.4 Backward Compatibility Tests

| Scenario | Assertion |
|----------|-----------|
| NullCacheProvider explicit | Zero cache operations |
| Existing tests unchanged | 100% pass rate |
| Public API signatures | No changes detected |

---

## 10. Implementation Phases

### Phase 1: Foundation (Session 4)

**Goal**: CacheConfig and provider factory

| Task | File | Lines |
|------|------|-------|
| Add CacheConfig to config.py | `config.py` | ~50 |
| Create CacheProviderFactory | `cache/factory.py` | ~120 |
| Integrate factory in AsanaClient | `client.py` | ~10 |
| Unit tests for config and factory | `tests/unit/` | ~150 |

**Exit Criteria**:
- `AsanaClient()` uses InMemoryCacheProvider by default
- `ASANA_CACHE_ENABLED=false` uses NullCacheProvider
- `ASANA_CACHE_PROVIDER=redis` fails gracefully without REDIS_HOST

### Phase 2: Client Integration (Session 5)

**Goal**: TasksClient caching

| Task | File | Lines |
|------|------|-------|
| Add cache helpers to BaseClient | `clients/base.py` | ~60 |
| Wire get_async() to cache | `clients/tasks.py` | ~40 |
| Add entity-type TTL resolution | `clients/tasks.py` | ~30 |
| Unit tests for cache behavior | `tests/unit/clients/` | ~200 |

**Exit Criteria**:
- `get_async()` returns cached data on hit
- Cache miss fetches from API and stores
- Entity-type TTLs applied correctly

### Phase 3: Invalidation (Session 6)

**Goal**: SaveSession invalidation and polish

| Task | File | Lines |
|------|------|-------|
| Add invalidation hook | `persistence/session.py` | ~50 |
| Add entity_type_ttls to TTLSettings | `cache/settings.py` | ~10 |
| Integration tests | `tests/integration/` | ~150 |
| Performance benchmarks | `tests/performance/` | ~50 |

**Exit Criteria**:
- Mutations invalidate cache
- CREATE operations warm cache
- Performance targets met
- All existing tests pass

---

## 11. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Cache invalidation race conditions | Medium | Medium | Invalidate aggressively; stale reads resolve at TTL |
| Memory growth (InMemory) | Low | Medium | max_size=10000 eviction enforced |
| Redis dependency in production | Low | High | Graceful degradation to InMemory, logged warning |
| Entity type detection failures | Low | Low | Default to generic TTL (300s) |
| Test suite disruption | Low | High | NullCacheProvider when explicit, existing behavior preserved |
| Performance regression | Low | Medium | Benchmarks in Phase 3, <5% latency increase threshold |

---

## 12. Observability Strategy

### 12.1 Logging

| Event | Level | Fields |
|-------|-------|--------|
| Cache hit | DEBUG | `key`, `entry_type`, `ttl_remaining` |
| Cache miss | DEBUG | `key`, `entry_type` |
| Cache set | DEBUG | `key`, `entry_type`, `ttl` |
| Cache invalidate | DEBUG | `key`, `entry_types` |
| Cache error | WARNING | `key`, `entry_type`, `error` |
| Provider selection | INFO | `provider_type`, `environment` |

### 12.2 Metrics (via ObservabilityHook)

| Metric | Type | Tags |
|--------|------|------|
| `cache.hit_rate` | Gauge | `entry_type` |
| `cache.latency_ms` | Histogram | `operation`, `entry_type` |
| `cache.size` | Gauge | `provider` |
| `cache.evictions` | Counter | `provider` |

---

## 13. Quality Gate Checklist

- [x] TDD traces every FR-* to component/method
- [x] All 5 ADRs document decision rationale with alternatives
- [x] Sequence diagrams cover: cache hit, cache miss, invalidation, degradation
- [x] Interface contracts explicit (method signatures, return types)
- [x] Backward compatibility explicitly addressed
- [x] Implementation phases map to Sessions 4-6
- [x] Test strategy defined per component

---

## 14. Appendix: Requirement Traceability

| Requirement | Component | Method/Field |
|-------------|-----------|--------------|
| FR-DEFAULT-001 | CacheProviderFactory | create() |
| FR-DEFAULT-002 | CacheProviderFactory | create() priority logic |
| FR-DEFAULT-003 | CacheProviderFactory | _create_explicit() |
| FR-DEFAULT-004 | CacheProviderFactory | create() enabled check |
| FR-DEFAULT-005 | CacheProviderFactory | _auto_detect() production |
| FR-DEFAULT-006 | CacheProviderFactory | _auto_detect() development |
| FR-CLIENT-001 | TasksClient | get_async() cache check |
| FR-CLIENT-002 | TasksClient | get_async() EntryType.TASK |
| FR-CLIENT-003 | BaseClient | _cache_set() version extraction |
| FR-CLIENT-004 | BaseClient | _cache_get() is_expired() |
| FR-CLIENT-005 | TasksClient | get() via sync wrapper |
| FR-CLIENT-006 | AsanaClient | __init__ explicit provider |
| FR-CLIENT-007 | TasksClient | get_async() raw=True |
| FR-INVALIDATE-001 | SaveSession | _invalidate_cache_for_results() |
| FR-INVALIDATE-002 | SaveSession | _invalidate_cache_for_results() |
| FR-INVALIDATE-003 | SaveSession | _invalidate_cache_for_results() |
| FR-INVALIDATE-004 | SaveSession | _invalidate_cache_for_results() |
| FR-INVALIDATE-005 | SaveSession | gids_to_invalidate set |
| FR-INVALIDATE-006 | SaveSession | action_results loop |
| FR-TTL-001 | TTLSettings | entity_type_ttls["business"] |
| FR-TTL-002 | TTLSettings | entity_type_ttls["contact"/"unit"] |
| FR-TTL-003 | TTLSettings | entity_type_ttls["offer"] |
| FR-TTL-004 | TTLSettings | entity_type_ttls["process"] |
| FR-TTL-005 | TTLSettings | default_ttl |
| FR-TTL-006 | TTLSettings | get_ttl() priority |
| FR-TTL-007 | TasksClient | _detect_entity_type() |
| FR-DF-001 | CacheConfig | dataframe_caching=True |
| FR-DF-002 | CacheConfig | dataframe_caching field |
| FR-CONFIG-001 | AsanaConfig | cache field |
| FR-CONFIG-002 | CacheConfig | all fields |
| FR-CONFIG-003 | CacheConfig | from_env() |
| FR-CONFIG-004 | AsanaClient | __init__ programmatic override |
| FR-ENV-001 | CacheConfig.from_env | ASANA_CACHE_ENABLED |
| FR-ENV-002 | CacheConfig.from_env | ASANA_CACHE_PROVIDER |
| FR-ENV-003 | CacheConfig.from_env | ASANA_CACHE_TTL_DEFAULT |
| FR-ENV-004 | CacheProviderFactory | ASANA_ENVIRONMENT |
| FR-ENV-005 | CacheProviderFactory | REDIS_* variables |
| NFR-PERF-001 | InMemoryCacheProvider | <5ms p99 |
| NFR-PERF-002 | BaseClient | cache check overhead |
| NFR-PERF-003 | Integration test | 10x improvement |
| NFR-PERF-004 | InMemoryCacheProvider | max_size eviction |
| NFR-COMPAT-001 | AsanaClient | unchanged signatures |
| NFR-COMPAT-002 | Test suite | 100% pass rate |
| NFR-COMPAT-003 | TasksClient | unchanged signatures |
| NFR-COMPAT-004 | AsanaClient | NullCacheProvider explicit |
| NFR-DEGRADE-001 | BaseClient | _cache_get() try/except |
| NFR-DEGRADE-002 | CacheProviderFactory | _auto_detect() fallback |
| NFR-DEGRADE-003 | BaseClient | _cache_get() exception handling |
| NFR-DEGRADE-004 | BaseClient | _cache_set() try/except |

---

## 15. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-22 | Architect | Initial TDD |
