# TDD: Backward Compatibility Layer

## Metadata
- **TDD ID**: TDD-0006
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-08
- **Last Updated**: 2025-12-08
- **PRD Reference**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md) (FR-COMPAT-001 to FR-COMPAT-008)
- **Related TDDs**: [TDD-0001](TDD-0001-sdk-architecture.md)
- **Related ADRs**:
  - [ADR-0001](../decisions/ADR-0001-protocol-extensibility.md) - Protocol-based DI (enables FR-COMPAT-003-005)
  - [ADR-0011](../decisions/ADR-0011-deprecation-warning-strategy.md) - Deprecation warning strategy (new)
  - [ADR-0012](../decisions/ADR-0012-public-api-surface.md) - Public API surface definition (new)

## Overview

The Backward Compatibility layer enables gradual migration from autom8's existing Asana integrations to the extracted SDK. It provides import aliases with deprecation warnings, protocol adapter examples for autom8 integration, verified asana SDK dependency, and a clearly defined public API surface that hides internal implementation details.

## Requirements Summary

From [PRD-0001](../requirements/PRD-0001-sdk-extraction.md):

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-COMPAT-001 | Maintain same public API signatures for migrated functions | Must |
| FR-COMPAT-002 | Provide import aliases for gradual migration | Must |
| FR-COMPAT-003 | Allow autom8 to inject AuthProvider at runtime | Must |
| FR-COMPAT-004 | Allow autom8 to inject CacheProvider at runtime | Must |
| FR-COMPAT-005 | Allow autom8 to inject LogProvider at runtime | Must |
| FR-COMPAT-006 | SDK works standalone without autom8 dependencies | Must |
| FR-COMPAT-007 | Keep asana (official SDK) as a dependency | Must |
| FR-COMPAT-008 | Don't expose internal implementation details | Should |

## System Context

The compatibility layer sits between legacy autom8 code and the new SDK, providing a migration bridge:

```
autom8 Monolith (Legacy Code)
         │
         │  Legacy imports:
         │  from autom8_asana.compat import Task
         │  from autom8_asana.compat import TasksClient
         │
         ▼
┌─────────────────────────────────────────────────┐
│            _compat.py (Compatibility Layer)     │
│                                                 │
│  ┌─────────────────┐   ┌─────────────────────┐  │
│  │ Import Aliases  │   │ Deprecation         │  │
│  │ - Task          │   │ Warnings            │  │
│  │ - Project       │   │ (warnings.warn)     │  │
│  │ - User          │   └─────────────────────┘  │
│  │ - etc.          │                            │
│  └─────────────────┘                            │
│                                                 │
│  ┌─────────────────────────────────────────┐    │
│  │ Protocol Adapter Examples               │    │
│  │ (in examples/ directory, not _compat)   │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
         │
         │  Delegates to:
         ▼
┌─────────────────────────────────────────────────┐
│            autom8_asana Public API              │
│                                                 │
│  from autom8_asana import Task                  │
│  from autom8_asana.models import Project        │
│  from autom8_asana.protocols import AuthProvider│
└─────────────────────────────────────────────────┘
```

## Design

### Component Architecture

```
autom8_asana/
│
├── __init__.py              # Public API exports (explicitly defined __all__)
├── _compat.py               # Import aliases with deprecation warnings
│
├── models/                  # Public models
│   ├── __init__.py          # Exports all models in __all__
│   ├── task.py
│   └── ...
│
├── clients/                 # Public clients (not directly exported from root)
│   ├── __init__.py          # Exports all clients in __all__
│   └── ...
│
├── protocols/               # Public protocols
│   ├── __init__.py          # Exports all protocols in __all__
│   └── ...
│
├── _defaults/               # Internal (underscore prefix)
│   ├── __init__.py          # Internal defaults, selectively exposed
│   └── ...
│
├── _internal/               # Internal utilities (underscore prefix)
│   └── ...
│
├── transport/               # Semi-internal (power users only)
│   ├── __init__.py          # Limited exports
│   └── ...
│
└── examples/                # Example code (not imported, documentation only)
    └── autom8_adapters.py   # Protocol adapter examples for autom8
```

### 1. _compat.py Module Design

The compatibility module provides old import paths with deprecation warnings:

```python
"""Backward compatibility layer for gradual migration.

This module provides aliases for old import paths. All imports from this
module emit deprecation warnings guiding users to the new canonical paths.

Migration Guide:
    # Old (deprecated):
    from autom8_asana.compat import Task
    from autom8_asana.compat import TasksClient

    # New (canonical):
    from autom8_asana import Task
    from autom8_asana.clients import TasksClient

This module will be removed in version 1.0.0.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

# Version when this module will be removed
_REMOVAL_VERSION = "1.0.0"


def _deprecated_import(name: str, new_path: str) -> None:
    """Emit deprecation warning for legacy import."""
    warnings.warn(
        f"Importing '{name}' from 'autom8_asana.compat' is deprecated. "
        f"Use '{new_path}' instead. "
        f"This alias will be removed in version {_REMOVAL_VERSION}.",
        DeprecationWarning,
        stacklevel=3,  # Points to the actual import statement
    )


# Lazy imports with deprecation warnings
def __getattr__(name: str):
    """Lazy attribute access with deprecation warnings."""

    # Models (from autom8_asana.models)
    _model_aliases = {
        "AsanaResource": "autom8_asana.models.AsanaResource",
        "NameGid": "autom8_asana.models.NameGid",
        "Task": "autom8_asana.models.Task",
        "Project": "autom8_asana.models.Project",
        "Section": "autom8_asana.models.Section",
        "User": "autom8_asana.models.User",
        "Workspace": "autom8_asana.models.Workspace",
        "CustomField": "autom8_asana.models.CustomField",
        "CustomFieldEnumOption": "autom8_asana.models.CustomFieldEnumOption",
        "CustomFieldSetting": "autom8_asana.models.CustomFieldSetting",
        "Attachment": "autom8_asana.models.Attachment",
        "Goal": "autom8_asana.models.Goal",
        "GoalMembership": "autom8_asana.models.GoalMembership",
        "GoalMetric": "autom8_asana.models.GoalMetric",
        "Portfolio": "autom8_asana.models.Portfolio",
        "Story": "autom8_asana.models.Story",
        "Tag": "autom8_asana.models.Tag",
        "Team": "autom8_asana.models.Team",
        "TeamMembership": "autom8_asana.models.TeamMembership",
        "Webhook": "autom8_asana.models.Webhook",
        "WebhookFilter": "autom8_asana.models.WebhookFilter",
        "PageIterator": "autom8_asana.models.PageIterator",
    }

    # Clients (from autom8_asana.clients)
    _client_aliases = {
        "TasksClient": "autom8_asana.clients.TasksClient",
        "ProjectsClient": "autom8_asana.clients.ProjectsClient",
        "SectionsClient": "autom8_asana.clients.SectionsClient",
        "UsersClient": "autom8_asana.clients.UsersClient",
        "WorkspacesClient": "autom8_asana.clients.WorkspacesClient",
        "CustomFieldsClient": "autom8_asana.clients.CustomFieldsClient",
        "WebhooksClient": "autom8_asana.clients.WebhooksClient",
        "TeamsClient": "autom8_asana.clients.TeamsClient",
        "AttachmentsClient": "autom8_asana.clients.AttachmentsClient",
        "TagsClient": "autom8_asana.clients.TagsClient",
        "GoalsClient": "autom8_asana.clients.GoalsClient",
        "PortfoliosClient": "autom8_asana.clients.PortfoliosClient",
        "StoriesClient": "autom8_asana.clients.StoriesClient",
    }

    # Protocols (from autom8_asana.protocols)
    _protocol_aliases = {
        "AuthProvider": "autom8_asana.protocols.AuthProvider",
        "CacheProvider": "autom8_asana.protocols.CacheProvider",
        "LogProvider": "autom8_asana.protocols.LogProvider",
        "ItemLoader": "autom8_asana.protocols.ItemLoader",
    }

    # Exceptions (from autom8_asana.exceptions or autom8_asana)
    _exception_aliases = {
        "AsanaError": "autom8_asana.AsanaError",
        "AuthenticationError": "autom8_asana.AuthenticationError",
        "RateLimitError": "autom8_asana.RateLimitError",
        "NotFoundError": "autom8_asana.NotFoundError",
        "ForbiddenError": "autom8_asana.ForbiddenError",
        "ServerError": "autom8_asana.ServerError",
        "TimeoutError": "autom8_asana.TimeoutError",
        "ConfigurationError": "autom8_asana.ConfigurationError",
    }

    # Main client
    _main_aliases = {
        "AsanaClient": "autom8_asana.AsanaClient",
    }

    all_aliases = {
        **_model_aliases,
        **_client_aliases,
        **_protocol_aliases,
        **_exception_aliases,
        **_main_aliases,
    }

    if name in all_aliases:
        new_path = all_aliases[name]
        _deprecated_import(name, new_path)

        # Perform the actual import
        if name in _model_aliases:
            from autom8_asana import models
            return getattr(models, name)
        elif name in _client_aliases:
            from autom8_asana import clients
            return getattr(clients, name)
        elif name in _protocol_aliases:
            from autom8_asana import protocols
            return getattr(protocols, name)
        elif name in _exception_aliases:
            import autom8_asana
            return getattr(autom8_asana, name)
        elif name in _main_aliases:
            import autom8_asana
            return getattr(autom8_asana, name)

    raise AttributeError(f"module 'autom8_asana.compat' has no attribute '{name}'")


# For IDE support and static analysis, also define __all__
__all__ = [
    # Models
    "AsanaResource",
    "NameGid",
    "Task",
    "Project",
    "Section",
    "User",
    "Workspace",
    "CustomField",
    "CustomFieldEnumOption",
    "CustomFieldSetting",
    "Attachment",
    "Goal",
    "GoalMembership",
    "GoalMetric",
    "Portfolio",
    "Story",
    "Tag",
    "Team",
    "TeamMembership",
    "Webhook",
    "WebhookFilter",
    "PageIterator",
    # Clients
    "TasksClient",
    "ProjectsClient",
    "SectionsClient",
    "UsersClient",
    "WorkspacesClient",
    "CustomFieldsClient",
    "WebhooksClient",
    "TeamsClient",
    "AttachmentsClient",
    "TagsClient",
    "GoalsClient",
    "PortfoliosClient",
    "StoriesClient",
    # Protocols
    "AuthProvider",
    "CacheProvider",
    "LogProvider",
    "ItemLoader",
    # Exceptions
    "AsanaError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "ForbiddenError",
    "ServerError",
    "TimeoutError",
    "ConfigurationError",
    # Main client
    "AsanaClient",
]


# TYPE_CHECKING block for static analysis tools
if TYPE_CHECKING:
    from autom8_asana import (
        AsanaClient,
        AsanaError,
        AuthenticationError,
        ConfigurationError,
        ForbiddenError,
        NotFoundError,
        RateLimitError,
        ServerError,
        TimeoutError,
    )
    from autom8_asana.clients import (
        AttachmentsClient,
        CustomFieldsClient,
        GoalsClient,
        PortfoliosClient,
        ProjectsClient,
        SectionsClient,
        StoriesClient,
        TagsClient,
        TasksClient,
        TeamsClient,
        UsersClient,
        WebhooksClient,
        WorkspacesClient,
    )
    from autom8_asana.models import (
        AsanaResource,
        Attachment,
        CustomField,
        CustomFieldEnumOption,
        CustomFieldSetting,
        Goal,
        GoalMembership,
        GoalMetric,
        NameGid,
        PageIterator,
        Portfolio,
        Project,
        Section,
        Story,
        Tag,
        Task,
        Team,
        TeamMembership,
        User,
        Webhook,
        WebhookFilter,
        Workspace,
    )
    from autom8_asana.protocols import (
        AuthProvider,
        CacheProvider,
        ItemLoader,
        LogProvider,
    )
```

### 2. Protocol Adapter Examples

Example adapters for autom8 integration are provided in `/examples/autom8_adapters.py` (documentation only, not shipped in the package):

```python
"""Example protocol adapters for autom8 integration.

These examples show how autom8 can implement the SDK's protocols
to integrate with its existing infrastructure (SecretManager, TaskCache, LOG).

Copy and adapt these to your autom8 codebase. They are not part of the SDK
package itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # These imports are autom8-specific and not available in the SDK
    from autom8.core.env import ENV
    from autom8.core.log import LOG
    from autom8.apis.aws_api.task_cache import TaskCache


class SecretManagerAuthProvider:
    """AuthProvider adapter wrapping autom8's ENV.SecretManager.

    Example usage in autom8:
        from autom8_asana import AsanaClient
        from your_adapters import SecretManagerAuthProvider

        client = AsanaClient(auth_provider=SecretManagerAuthProvider())
        task = await client.tasks.get_async("task_gid")
    """

    def __init__(self, secret_manager: Any | None = None) -> None:
        """Initialize with optional secret manager override.

        Args:
            secret_manager: Custom secret manager (default: ENV.SecretManager)
        """
        if secret_manager is not None:
            self._sm = secret_manager
        else:
            from autom8.core.env import ENV
            self._sm = ENV.SecretManager

    def get_secret(self, key: str) -> str:
        """Retrieve secret from autom8's SecretManager.

        Args:
            key: Secret key (e.g., "ASANA_PAT")

        Returns:
            Secret value

        Raises:
            AuthenticationError: If secret not found
        """
        try:
            value = self._sm.get(key)
            if value is None:
                from autom8_asana import AuthenticationError
                raise AuthenticationError(f"Secret '{key}' not found in SecretManager")
            return value
        except Exception as e:
            from autom8_asana import AuthenticationError
            raise AuthenticationError(f"Failed to retrieve secret '{key}': {e}") from e


class S3CacheProvider:
    """CacheProvider adapter wrapping autom8's TaskCache (S3-backed).

    Example usage in autom8:
        from autom8_asana import AsanaClient
        from your_adapters import S3CacheProvider

        client = AsanaClient(
            auth_provider=SecretManagerAuthProvider(),
            cache_provider=S3CacheProvider(),
        )
    """

    def __init__(self, task_cache: Any | None = None, prefix: str = "asana_sdk:") -> None:
        """Initialize with optional TaskCache override.

        Args:
            task_cache: Custom cache instance (default: TaskCache)
            prefix: Key prefix for namespacing (default: "asana_sdk:")
        """
        if task_cache is not None:
            self._cache = task_cache
        else:
            from autom8.apis.aws_api.task_cache import TaskCache
            self._cache = TaskCache
        self._prefix = prefix

    def _prefixed_key(self, key: str) -> str:
        """Add prefix to cache key for namespacing."""
        return f"{self._prefix}{key}"

    def get(self, key: str) -> dict[str, Any] | None:
        """Get value from S3-backed cache.

        Args:
            key: Cache key

        Returns:
            Cached dict or None if not found
        """
        try:
            return self._cache.get(self._prefixed_key(key))
        except Exception:
            # Cache failures should not break SDK operations
            return None

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Store value in S3-backed cache.

        Args:
            key: Cache key
            value: Dict to cache
            ttl: TTL in seconds (may be ignored by TaskCache)
        """
        try:
            self._cache.set(self._prefixed_key(key), value, ttl=ttl)
        except Exception:
            # Cache failures should not break SDK operations
            pass

    def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key to delete
        """
        try:
            self._cache.delete(self._prefixed_key(key))
        except Exception:
            pass


class LogAdapter:
    """LogProvider adapter wrapping autom8's LOG.

    Example usage in autom8:
        from autom8_asana import AsanaClient
        from your_adapters import LogAdapter

        client = AsanaClient(
            auth_provider=SecretManagerAuthProvider(),
            log_provider=LogAdapter(),
        )
    """

    def __init__(self, logger: Any | None = None, prefix: str = "[asana_sdk]") -> None:
        """Initialize with optional logger override.

        Args:
            logger: Custom logger (default: LOG)
            prefix: Prefix for log messages
        """
        if logger is not None:
            self._log = logger
        else:
            from autom8.core.log import LOG
            self._log = LOG
        self._prefix = prefix

    def _format_msg(self, msg: str) -> str:
        """Add prefix to message."""
        return f"{self._prefix} {msg}"

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message."""
        self._log.debug(self._format_msg(msg), *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        self._log.info(self._format_msg(msg), *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        self._log.warning(self._format_msg(msg), *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message."""
        self._log.error(self._format_msg(msg), *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._log.exception(self._format_msg(msg), *args, **kwargs)


# Convenience function for full autom8 integration
def create_autom8_client(**config_overrides):
    """Create AsanaClient with full autom8 integration.

    Example:
        client = create_autom8_client()
        task = await client.tasks.get_async("task_gid")

    Args:
        **config_overrides: Override default AsanaConfig settings

    Returns:
        AsanaClient configured for autom8
    """
    from autom8_asana import AsanaClient, AsanaConfig

    config = AsanaConfig(**config_overrides) if config_overrides else None

    return AsanaClient(
        auth_provider=SecretManagerAuthProvider(),
        cache_provider=S3CacheProvider(),
        log_provider=LogAdapter(),
        config=config,
    )
```

### 3. pyproject.toml Dependency Verification

Current `pyproject.toml` correctly lists the asana SDK as a dependency:

```toml
[project]
name = "autom8-asana"
version = "0.1.0"
description = "Async-first Asana API client extracted from autom8"
requires-python = ">=3.10"
dependencies = [
    "httpx>=0.25.0",
    "pydantic>=2.0.0",
    "asana>=5.0.3",  # FR-COMPAT-007: Official Asana SDK as dependency
]
```

**Verification checklist:**
- [x] `asana>=5.0.3` is listed in dependencies (FR-COMPAT-007)
- [x] No autom8-specific dependencies (FR-COMPAT-006)
- [x] No sql, aws_api, or contente_api imports (PRD constraint)

### 4. Public API Surface Definition

The SDK distinguishes between public, semi-public, and internal APIs:

#### Public API (Stable, Documented)

Exported from `autom8_asana/__init__.py`:

| Category | Exports | Import Path |
|----------|---------|-------------|
| Main Client | `AsanaClient` | `from autom8_asana import AsanaClient` |
| Configuration | `AsanaConfig`, `RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig` | `from autom8_asana import AsanaConfig` |
| Exceptions | `AsanaError`, `AuthenticationError`, `ForbiddenError`, `NotFoundError`, `GoneError`, `RateLimitError`, `ServerError`, `TimeoutError`, `ConfigurationError`, `SyncInAsyncContextError` | `from autom8_asana import AsanaError` |
| Protocols | `AuthProvider`, `CacheProvider`, `LogProvider`, `ItemLoader` | `from autom8_asana import AuthProvider` |
| Batch API | `BatchClient`, `BatchRequest`, `BatchResult`, `BatchSummary` | `from autom8_asana import BatchRequest` |
| Models | All models (Task, Project, User, etc.) | `from autom8_asana import Task` |

#### Semi-Public API (Power Users, Subject to Change)

Accessible via submodule imports but not exported from root:

| Submodule | Exports | Use Case |
|-----------|---------|----------|
| `autom8_asana.clients` | Individual client classes | Custom client composition |
| `autom8_asana.models` | Individual model classes | Type annotations |
| `autom8_asana.protocols` | Protocol definitions | Custom implementations |
| `autom8_asana.transport` | `AsyncHTTPClient`, `TokenBucketRateLimiter`, `RetryHandler`, `sync_wrapper` | Advanced transport customization |

#### Internal API (Not Public, May Change Without Notice)

Prefixed with underscore or not exported:

| Module | Contents | Why Internal |
|--------|----------|--------------|
| `autom8_asana._defaults/` | Default provider implementations | Implementation detail |
| `autom8_asana._internal/` | Concurrency utils, correlation IDs | Implementation detail |
| `autom8_asana._compat.py` | Deprecated import aliases | Migration-only |
| `autom8_asana.transport.http` | HTTP client internals | Implementation detail |
| `autom8_asana.transport.rate_limiter` | Rate limiter internals | Implementation detail |
| `autom8_asana.transport.retry` | Retry handler internals | Implementation detail |

### Data Model

No new data models introduced. This layer provides access patterns to existing models.

### API Contracts

#### Compatibility Module Interface

```python
# autom8_asana/_compat.py

def __getattr__(name: str) -> Any:
    """Lazy attribute access with deprecation warnings.

    Args:
        name: Attribute name being accessed

    Returns:
        The requested class/object from the canonical location

    Raises:
        AttributeError: If name is not a known alias

    Side Effects:
        Emits DeprecationWarning via warnings.warn()
    """
```

#### Migration Contract

Users migrating from autom8 can follow this pattern:

```python
# Step 1: Initial migration (works immediately)
from autom8_asana.compat import Task, TasksClient
# Warning: DeprecationWarning emitted

# Step 2: Update imports (target state)
from autom8_asana import Task
from autom8_asana.clients import TasksClient
# No warning
```

### Data Flow

#### Deprecation Warning Flow

```
User Code                 _compat.py              warnings           autom8_asana
    |                          |                      |                    |
    | from compat import Task  |                      |                    |
    |------------------------->|                      |                    |
    |                          |                      |                    |
    |                          | __getattr__("Task")  |                    |
    |                          |---+                  |                    |
    |                          |   |                  |                    |
    |                          |   | warnings.warn()  |                    |
    |                          |   |----------------->|                    |
    |                          |   |                  | emit to stderr     |
    |                          |   |                  |---+                |
    |                          |   |                  |<--+                |
    |                          |   |                  |                    |
    |                          |   | import Task      |                    |
    |                          |   |---------------------------------->    |
    |                          |   |                  |                    |
    |                          |   | Task class       |                    |
    |                          |<--+<------------------------------------- |
    |                          |                      |                    |
    | Task class               |                      |                    |
    |<-------------------------|                      |                    |
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Deprecation warning mechanism | `warnings.warn()` with `DeprecationWarning` | Standard Python mechanism; can be filtered/promoted to errors | [ADR-0011](../decisions/ADR-0011-deprecation-warning-strategy.md) |
| Public API surface | Explicit `__all__` + underscore prefix for internal | Clear contract; follows Python conventions | [ADR-0012](../decisions/ADR-0012-public-api-surface.md) |
| Protocol adapter location | Examples directory (not in package) | Avoids autom8 coupling; documentation-only | Per FR-COMPAT-006 |
| Lazy import in compat | `__getattr__` | Avoids import-time warnings; only warns on use | [ADR-0011](../decisions/ADR-0011-deprecation-warning-strategy.md) |

## Complexity Assessment

**Level**: MODULE

**Justification**:
- Single-purpose module (compatibility aliases)
- No complex interactions or state
- Standard Python mechanisms (warnings, lazy imports)
- No external dependencies beyond existing SDK

This is appropriately simple because:
1. The compatibility layer is a thin wrapper over existing code
2. It follows established Python patterns for deprecation
3. It will be removed in a future version (v1.0.0)

## Implementation Plan

### Phase 1: Compatibility Module (1 day)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Create `_compat.py` with lazy imports | None | 3h |
| Add deprecation warning infrastructure | None | 1h |
| Unit tests for import aliases | _compat.py | 2h |
| Unit tests for deprecation warnings | _compat.py | 2h |

**Exit Criteria**: All legacy imports work with warnings; tests pass.

### Phase 2: API Surface Verification (0.5 day)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Audit `__all__` exports across modules | None | 2h |
| Verify underscore prefix on internal modules | None | 1h |
| Add architecture tests (no internal imports) | Audit complete | 1h |

**Exit Criteria**: Public API clearly defined; internal modules protected.

### Phase 3: Documentation & Examples (0.5 day)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Create `examples/autom8_adapters.py` | Protocols defined | 2h |
| Document migration guide | _compat.py | 2h |

**Exit Criteria**: autom8 team has clear migration path with examples.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Users ignore deprecation warnings | Medium | Medium | Also log warnings at import time; document timeline |
| Legacy imports break in v1.0.0 | High | High (intentional) | Clear deprecation timeline; migration guide |
| Protocol adapters have bugs in autom8 | Medium | Low | Examples are documentation-only; autom8 owns their adapters |
| IDE/type checker confusion with lazy imports | Low | Medium | TYPE_CHECKING block provides static analysis support |

## Observability

### Logging

The compatibility module logs at WARNING level when imports occur:

```python
import logging
logger = logging.getLogger("autom8_asana.compat")

def _deprecated_import(name: str, new_path: str) -> None:
    logger.warning(
        f"Deprecated import: '{name}' from 'autom8_asana.compat'. "
        f"Use '{new_path}' instead."
    )
    warnings.warn(...)
```

### Metrics

No runtime metrics for compatibility layer (it's import-time only).

### Alerting

No alerting needed for compatibility layer.

## Testing Strategy

### Unit Testing

- Test each alias resolves to correct class
- Test deprecation warnings are emitted with correct message
- Test `__all__` includes all expected names
- Test `AttributeError` raised for unknown attributes
- Test warnings include correct stacklevel (points to user code)

### Integration Testing

- Test autom8 adapter examples compile (without autom8)
- Test SDK works standalone without autom8
- Test asana package is importable alongside SDK

### Architecture Testing

- Verify `_defaults/` and `_internal/` not exported from root
- Verify underscore-prefixed modules not in public `__all__`
- Verify no autom8-specific imports in SDK code

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should compat module also provide function aliases (not just classes)? | Architect | Before impl | TBD - need to audit autom8 imports |
| What's the deprecation timeline (when is v1.0.0)? | Product | Before impl | TBD - suggest 6 months from SDK release |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-08 | Architect | Initial design |
