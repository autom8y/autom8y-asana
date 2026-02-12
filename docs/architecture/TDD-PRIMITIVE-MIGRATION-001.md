# TDD: autom8_asana Platform Primitive Migration

**TDD ID**: TDD-PRIMITIVE-MIGRATION-001
**Version**: 1.0
**Date**: 2025-12-31
**Author**: Architect
**Status**: DRAFT
**Spike Reference**: [SPIKE-AUTOM8-ASANA-PRIMITIVE-ADOPTION](../../autom8y/docs/spikes/SPIKE-AUTOM8-ASANA-PRIMITIVE-ADOPTION.md)
**Platform TDD Reference**: [TDD-PLATFORM-PRIMITIVES-001](../../autom8y/docs/architecture/TDD-PLATFORM-PRIMITIVES-001.md)

---

## Overview

This document defines the technical approach for migrating autom8_asana's transport layer from local implementations to platform-standard `autom8y-*` primitives. This is a **circular migration**: the platform primitives were extracted FROM autom8_asana in a previous initiative, and we're now migrating back to the generalized versions.

**Critical Finding**: The spike confirmed that platform primitives and autom8_asana implementations are 90-100% compatible for most components, with the notable exception of the `LogProvider` to `LoggerProtocol` signature change (printf-style vs. structured).

---

## Constraints

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Python version | >= 3.11 | Match platform primitive requirements |
| Test coverage | >= existing baseline | No coverage regression allowed |
| External API | Unchanged | autom8_asana consumers unaffected |
| Quality gates | All phases | ruff check, mypy, pytest must pass |
| Rollback | Per-phase | Each phase independently revertible |

---

## Migration Phases

### Phase Summary

| Phase | Description | Risk | Execute |
|-------|-------------|------|---------|
| **Phase 1** | Add dependencies + Create LogProviderAdapter shim | Low | Yes |
| **Phase 2** | Config layer migration | Low | Yes |
| **Phase 3** | Transport layer migration | Medium | Yes |
| **Phase 4** | Settings layer migration | Low | Yes |
| **Phase 5** | Structured logging migration | High | Defer |
| **Phase 6** | Telemetry integration | Low | Skip |
| **Phase 7** | Cleanup | Low | Yes |

---

## Phase 1: Non-Breaking Additions

**Goal**: Add platform primitive dependencies and create the LogProviderAdapter shim layer.

**Risk**: Low - additive only, no existing code modified.

### 1.1 Dependency Addition

**File**: `pyproject.toml`

```diff
[project]
dependencies = [
    # Existing dependencies...
    "httpx>=0.25,<0.28",
    "pydantic>=2.5,<3.0",
    "pydantic-settings>=2.1,<3.0",
+   "autom8y-config>=0.1.0",
+   "autom8y-http>=0.1.0",
+   "autom8y-log>=0.1.0",
+   # autom8y-telemetry deferred - see Phase 6
]
```

**Implementation Steps**:
1. Add platform primitive dependencies to pyproject.toml
2. Run `uv sync` to install dependencies
3. Verify imports work: `python -c "from autom8y_http import TokenBucketRateLimiter"`

### 1.2 LogProviderAdapter Shim

**New File**: `src/autom8_asana/compat/__init__.py`

```python
"""Compatibility shims for platform primitive migration."""
```

**New File**: `src/autom8_asana/compat/log_adapter.py`

```python
"""Adapter bridging LogProvider (printf-style) to LoggerProtocol (structured).

This shim allows gradual migration from autom8_asana's printf-style logging
to the platform's structured logging format without modifying all call sites.

The adapter converts:
    logger.info("Rate limit: waiting %.2fs", wait_time)
to:
    logger.info("Rate limit: waiting %.2fs" % (wait_time,))

This is a TEMPORARY solution. Phase 5 will migrate all logging call sites
to structured format and remove this adapter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8y_log import LoggerProtocol


class LogProviderAdapter:
    """Adapts autom8y_log.LoggerProtocol to autom8_asana LogProvider interface.

    This adapter allows platform primitives (which expect LoggerProtocol with
    structured logging) to be used with autom8_asana's printf-style logging.

    The adapter converts printf-style calls to structured calls:
    - Input: logger.info("Waiting %.2fs", wait_time)
    - Output: logger.info("Waiting %.2fs" % (wait_time,))

    Note: This is a compatibility shim. The proper migration (Phase 5) will
    update all logging call sites to use structured logging directly.

    Example:
        from autom8y_log import get_logger
        from autom8_asana.compat.log_adapter import LogProviderAdapter

        # Wrap a platform logger for use with transport components
        platform_logger = get_logger(__name__)
        adapted_logger = LogProviderAdapter(platform_logger)

        # Transport components can use printf-style logging
        rate_limiter = OldTokenBucketRateLimiter(logger=adapted_logger)
    """

    def __init__(self, logger: LoggerProtocol) -> None:
        """Initialize adapter with a platform LoggerProtocol.

        Args:
            logger: Platform logger implementing LoggerProtocol
        """
        self._logger = logger

    def _format_message(self, msg: str, args: tuple[Any, ...]) -> str:
        """Format printf-style message with arguments.

        Args:
            msg: Format string
            args: Format arguments

        Returns:
            Formatted message string
        """
        if args:
            try:
                return msg % args
            except (TypeError, ValueError):
                # If formatting fails, return message with args appended
                return f"{msg} (args={args})"
        return msg

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message (printf-style to structured).

        Args:
            msg: Format string
            *args: Format arguments
            **kwargs: Additional context (passed through)
        """
        formatted = self._format_message(msg, args)
        self._logger.debug(formatted, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message (printf-style to structured).

        Args:
            msg: Format string
            *args: Format arguments
            **kwargs: Additional context (passed through)
        """
        formatted = self._format_message(msg, args)
        self._logger.info(formatted, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message (printf-style to structured).

        Args:
            msg: Format string
            *args: Format arguments
            **kwargs: Additional context (passed through)
        """
        formatted = self._format_message(msg, args)
        self._logger.warning(formatted, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message (printf-style to structured).

        Args:
            msg: Format string
            *args: Format arguments
            **kwargs: Additional context (passed through)
        """
        formatted = self._format_message(msg, args)
        self._logger.error(formatted, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with traceback (printf-style to structured).

        Args:
            msg: Format string
            *args: Format arguments
            **kwargs: Additional context (passed through)
        """
        formatted = self._format_message(msg, args)
        self._logger.exception(formatted, **kwargs)

    def bind(self, **kwargs: Any) -> "LogProviderAdapter":
        """Create new adapter with bound context.

        Args:
            **kwargs: Context to bind

        Returns:
            New LogProviderAdapter with bound context
        """
        return LogProviderAdapter(self._logger.bind(**kwargs))
```

### 1.3 Unit Tests for LogProviderAdapter

**New File**: `tests/test_log_adapter.py`

```python
"""Tests for LogProviderAdapter compatibility shim."""

from unittest.mock import Mock

import pytest

from autom8_asana.compat.log_adapter import LogProviderAdapter


class TestLogProviderAdapter:
    """Test LogProviderAdapter printf-to-structured conversion."""

    @pytest.fixture
    def mock_logger(self) -> Mock:
        """Create a mock LoggerProtocol."""
        mock = Mock()
        mock.bind.return_value = mock
        return mock

    @pytest.fixture
    def adapter(self, mock_logger: Mock) -> LogProviderAdapter:
        """Create adapter with mock logger."""
        return LogProviderAdapter(mock_logger)

    def test_info_no_args(self, adapter: LogProviderAdapter, mock_logger: Mock) -> None:
        """Test info with no format arguments."""
        adapter.info("Simple message")
        mock_logger.info.assert_called_once_with("Simple message")

    def test_info_with_args(self, adapter: LogProviderAdapter, mock_logger: Mock) -> None:
        """Test info with printf-style arguments."""
        adapter.info("Rate limit: waiting %.2fs", 1.5)
        mock_logger.info.assert_called_once_with("Rate limit: waiting 1.50s")

    def test_info_with_multiple_args(
        self, adapter: LogProviderAdapter, mock_logger: Mock
    ) -> None:
        """Test info with multiple printf-style arguments."""
        adapter.info("Retry attempt %d/%d: waiting %.2fs", 1, 3, 0.5)
        mock_logger.info.assert_called_once_with("Retry attempt 1/3: waiting 0.50s")

    def test_warning_with_args(
        self, adapter: LogProviderAdapter, mock_logger: Mock
    ) -> None:
        """Test warning with printf-style arguments."""
        adapter.warning("Circuit breaker open: %s", "timeout")
        mock_logger.warning.assert_called_once_with("Circuit breaker open: timeout")

    def test_error_with_kwargs(
        self, adapter: LogProviderAdapter, mock_logger: Mock
    ) -> None:
        """Test error passes through kwargs."""
        adapter.error("Request failed", error_code=500)
        mock_logger.error.assert_called_once_with("Request failed", error_code=500)

    def test_debug_level(self, adapter: LogProviderAdapter, mock_logger: Mock) -> None:
        """Test debug level logging."""
        adapter.debug("Debug message %s", "value")
        mock_logger.debug.assert_called_once_with("Debug message value")

    def test_exception_level(
        self, adapter: LogProviderAdapter, mock_logger: Mock
    ) -> None:
        """Test exception level logging."""
        adapter.exception("Exception occurred: %s", "details")
        mock_logger.exception.assert_called_once_with("Exception occurred: details")

    def test_bind_returns_new_adapter(
        self, adapter: LogProviderAdapter, mock_logger: Mock
    ) -> None:
        """Test bind returns a new adapter with bound context."""
        bound_adapter = adapter.bind(request_id="123")
        assert isinstance(bound_adapter, LogProviderAdapter)
        mock_logger.bind.assert_called_once_with(request_id="123")

    def test_format_error_fallback(
        self, adapter: LogProviderAdapter, mock_logger: Mock
    ) -> None:
        """Test fallback when format string doesn't match args."""
        adapter.info("Message with %s %s", "only_one_arg")
        # Should not raise, should log with fallback
        assert mock_logger.info.called
```

### 1.4 Quality Gate

```bash
# Run after Phase 1 completion
ruff check src/autom8_asana/compat/
mypy src/autom8_asana/compat/
pytest tests/test_log_adapter.py -v
```

**Rollback Point**: Revert pyproject.toml and delete `compat/` directory.

---

## Phase 2: Config Layer Migration

**Goal**: Migrate configuration dataclasses to platform primitives.

**Risk**: Low - config objects are data containers.

### 2.1 Import Replacement Table - Config

| Old Import | New Import | Change Type |
|------------|------------|-------------|
| `autom8_asana.config.RateLimitConfig` | `autom8y_http.RateLimiterConfig` | Alias |
| `autom8_asana.config.RetryConfig` | `autom8y_http.RetryConfig` | Drop-in |
| `autom8_asana.config.CircuitBreakerConfig` | `autom8y_http.CircuitBreakerConfig` | Drop-in |

### 2.2 Config Changes

**File**: `src/autom8_asana/config.py`

```diff
"""Configuration classes for autom8_asana."""

from __future__ import annotations

-from dataclasses import dataclass, field
-from typing import FrozenSet
+from autom8y_http import (
+    CircuitBreakerConfig,
+    RateLimiterConfig,
+    RetryConfig,
+)

# Domain-specific configs remain unchanged
from autom8_asana.automation.config import AutomationConfig
from autom8_asana.exceptions import ConfigurationError
from autom8_asana.settings import get_settings


-@dataclass(frozen=True)
-class RateLimitConfig:
-    """Configuration for token bucket rate limiter."""
-    max_requests: int = 1500
-    window_seconds: int = 60
-
-
-@dataclass(frozen=True)
-class RetryConfig:
-    """Configuration for retry handler."""
-    max_retries: int = 3
-    base_delay: float = 0.1
-    max_delay: float = 60.0
-    exponential_base: float = 2.0
-    jitter: bool = True
-    retryable_status_codes: FrozenSet[int] = field(
-        default_factory=lambda: frozenset({429, 500, 502, 503, 504})
-    )
-
-
-@dataclass(frozen=True)
-class CircuitBreakerConfig:
-    """Configuration for circuit breaker."""
-    enabled: bool = False
-    failure_threshold: int = 5
-    recovery_timeout: float = 60.0
-    half_open_max_calls: int = 1
+# Backward compatibility aliases
+RateLimitConfig = RateLimiterConfig  # Alias for old name
+
+__all__ = [
+    # Re-exported from platform
+    "RateLimiterConfig",
+    "RetryConfig",
+    "CircuitBreakerConfig",
+    # Deprecated alias
+    "RateLimitConfig",
+    # Domain-specific
+    "AsanaConfig",
+    "DataFrameConfig",
+    "CacheConfig",
+    # ... other domain configs
+]
```

### 2.3 Config Attribute Mapping

| Old Attribute | New Attribute | Notes |
|---------------|---------------|-------|
| `RateLimitConfig.max_requests` | `RateLimiterConfig.max_tokens` | Renamed |
| `RateLimitConfig.window_seconds` | `RateLimiterConfig.refill_period` | Renamed |
| `RetryConfig.*` | `RetryConfig.*` | Identical |
| `CircuitBreakerConfig.*` | `CircuitBreakerConfig.*` | Identical |

### 2.4 Quality Gate

```bash
ruff check src/autom8_asana/config.py
mypy src/autom8_asana/config.py
pytest tests/test_config.py -v
```

**Rollback Point**: Restore old dataclass definitions in config.py.

---

## Phase 3: Transport Layer Migration

**Goal**: Replace transport implementations with platform primitives.

**Risk**: Medium - core transport logic.

### 3.1 Import Replacement Table - Transport

| Old Import | New Import | Notes |
|------------|------------|-------|
| `autom8_asana.transport.rate_limiter.TokenBucketRateLimiter` | `autom8y_http.TokenBucketRateLimiter` | Wrapper needed for backward compat |
| `autom8_asana.transport.retry.RetryHandler` | `autom8y_http.ExponentialBackoffRetry` | Class renamed |
| `autom8_asana.transport.circuit_breaker.CircuitBreaker` | `autom8y_http.CircuitBreaker` | Wrapper for logger adaptation |
| `autom8_asana.transport.circuit_breaker.CircuitState` | `autom8y_http.CircuitState` | Drop-in |
| `autom8_asana.transport.sync.sync_wrapper` | `autom8y_http.sync_wrapper` | Drop-in |

### 3.2 Backward Compatibility Wrappers

**File**: `src/autom8_asana/transport/rate_limiter.py`

```python
"""Token bucket rate limiter - backward compatibility wrapper.

This module re-exports the platform TokenBucketRateLimiter with a
backward-compatible constructor that accepts the old LogProvider interface.

For new code, import directly from autom8y_http.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_http import RateLimiterConfig
from autom8y_http import TokenBucketRateLimiter as _PlatformRateLimiter

if TYPE_CHECKING:
    from autom8_asana.protocols.log import LogProvider


class TokenBucketRateLimiter(_PlatformRateLimiter):
    """Backward-compatible rate limiter wrapper.

    Accepts the old LogProvider interface and adapts it for the platform
    primitive. New code should import from autom8y_http directly.

    Example:
        # Old style (still works)
        limiter = TokenBucketRateLimiter(
            max_tokens=100, refill_period=60.0, logger=my_log_provider
        )

        # New style (preferred)
        from autom8y_http import TokenBucketRateLimiter, RateLimiterConfig
        limiter = TokenBucketRateLimiter(
            config=RateLimiterConfig(max_tokens=100, refill_period=60.0),
            logger=platform_logger,
        )
    """

    def __init__(
        self,
        max_tokens: int = 1500,
        refill_period: float = 60.0,
        logger: LogProvider | None = None,
        config: RateLimiterConfig | None = None,
    ) -> None:
        """Initialize rate limiter with backward-compatible signature.

        Args:
            max_tokens: Maximum bucket capacity (deprecated, use config)
            refill_period: Seconds to refill bucket (deprecated, use config)
            logger: Logger (LogProvider or LoggerProtocol)
            config: Platform config (preferred)
        """
        from autom8_asana.compat.log_adapter import LogProviderAdapter
        from autom8y_log import LoggerProtocol

        # Use config if provided, otherwise build from positional args
        if config is None:
            config = RateLimiterConfig(
                max_tokens=max_tokens,
                refill_period=refill_period,
            )

        # Adapt logger if it's the old LogProvider type
        adapted_logger = None
        if logger is not None:
            if isinstance(logger, LoggerProtocol):
                adapted_logger = logger
            else:
                # Wrap old LogProvider in adapter
                adapted_logger = LogProviderAdapter(logger)

        super().__init__(config=config, logger=adapted_logger)


# Re-export for backward compatibility
__all__ = ["TokenBucketRateLimiter"]
```

**File**: `src/autom8_asana/transport/retry.py`

```python
"""Retry handler - backward compatibility wrapper.

This module provides RetryHandler as an alias for ExponentialBackoffRetry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8y_http import ExponentialBackoffRetry as _PlatformRetry
from autom8y_http import RetryConfig

if TYPE_CHECKING:
    from autom8_asana.protocols.log import LogProvider


class RetryHandler(_PlatformRetry):
    """Backward-compatible retry handler wrapper.

    Maintains the old class name and constructor signature.
    """

    def __init__(
        self,
        config: RetryConfig | None = None,
        logger: LogProvider | None = None,
    ) -> None:
        """Initialize retry handler.

        Args:
            config: Retry configuration
            logger: Logger (LogProvider or LoggerProtocol)
        """
        from autom8_asana.compat.log_adapter import LogProviderAdapter
        from autom8y_log import LoggerProtocol

        adapted_logger = None
        if logger is not None:
            if isinstance(logger, LoggerProtocol):
                adapted_logger = logger
            else:
                adapted_logger = LogProviderAdapter(logger)

        super().__init__(config=config, logger=adapted_logger)


# Also export the new name
ExponentialBackoffRetry = RetryHandler

__all__ = ["RetryHandler", "ExponentialBackoffRetry"]
```

**File**: `src/autom8_asana/transport/circuit_breaker.py`

```python
"""Circuit breaker - backward compatibility wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8y_http import CircuitBreaker as _PlatformCircuitBreaker
from autom8y_http import CircuitBreakerConfig
from autom8y_http import CircuitState

if TYPE_CHECKING:
    from autom8_asana.protocols.log import LogProvider


class CircuitBreaker(_PlatformCircuitBreaker):
    """Backward-compatible circuit breaker wrapper."""

    def __init__(
        self,
        config: CircuitBreakerConfig | None = None,
        log: LogProvider | None = None,
        logger: LogProvider | None = None,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
            log: Logger (deprecated name, use logger)
            logger: Logger (LogProvider or LoggerProtocol)
        """
        from autom8_asana.compat.log_adapter import LogProviderAdapter
        from autom8y_log import LoggerProtocol

        # Support both 'log' and 'logger' parameter names
        effective_logger = logger or log

        adapted_logger = None
        if effective_logger is not None:
            if isinstance(effective_logger, LoggerProtocol):
                adapted_logger = effective_logger
            else:
                adapted_logger = LogProviderAdapter(effective_logger)

        super().__init__(config=config, logger=adapted_logger)


__all__ = ["CircuitBreaker", "CircuitState"]
```

**File**: `src/autom8_asana/transport/sync.py`

```python
"""Sync wrapper utilities - re-exported from platform.

This module re-exports sync_wrapper from autom8y_http for backward
compatibility. New code should import from autom8y_http directly.
"""

from autom8y_http import sync_wrapper
from autom8y_http import SyncInAsyncContextError

__all__ = ["sync_wrapper", "SyncInAsyncContextError"]
```

### 3.3 Exception Migration

**File**: `src/autom8_asana/exceptions.py`

```diff
"""Exception hierarchy for autom8_asana."""

from __future__ import annotations

+from autom8y_http import CircuitBreakerOpenError, SyncInAsyncContextError


class AsanaError(Exception):
    """Base exception for all autom8_asana errors."""
    pass


-class CircuitBreakerOpenError(AsanaError):
-    """Raised when circuit breaker is open."""
-
-    def __init__(self, time_remaining: float, message: str) -> None:
-        self.time_remaining = time_remaining
-        super().__init__(message)


-class SyncInAsyncContextError(AsanaError):
-    """Raised when sync method called from async context."""
-
-    def __init__(self, sync_method: str, async_method: str, message: str) -> None:
-        self.sync_method = sync_method
-        self.async_method = async_method
-        super().__init__(message)


# Domain-specific errors remain unchanged
class RateLimitError(AsanaError):
    """Raised when rate limit exceeded."""
    pass


class ServerError(AsanaError):
    """Raised on server errors (5xx)."""
    pass


# ... other domain-specific errors
+
+__all__ = [
+    "AsanaError",
+    "CircuitBreakerOpenError",  # Re-exported from platform
+    "SyncInAsyncContextError",  # Re-exported from platform
+    "RateLimitError",
+    "ServerError",
+    # ... other domain errors
+]
```

### 3.4 Test Updates for Transport

**File**: `tests/conftest.py`

```diff
"""Test fixtures for autom8_asana."""

import pytest
+from autom8y_http import RateLimiterConfig, RetryConfig, CircuitBreakerConfig
+from autom8_asana.compat.log_adapter import LogProviderAdapter


-@pytest.fixture
-def rate_limit_config():
-    """Create rate limit config for testing."""
-    from autom8_asana.config import RateLimitConfig
-    return RateLimitConfig(max_requests=100, window_seconds=10)
+@pytest.fixture
+def rate_limiter_config() -> RateLimiterConfig:
+    """Platform-standard rate limiter config."""
+    return RateLimiterConfig(max_tokens=100, refill_period=10.0)


+@pytest.fixture
+def retry_config() -> RetryConfig:
+    """Platform-standard retry config."""
+    return RetryConfig(max_retries=3, base_delay=0.1)


+@pytest.fixture
+def circuit_breaker_config() -> CircuitBreakerConfig:
+    """Platform-standard circuit breaker config."""
+    return CircuitBreakerConfig(enabled=True, failure_threshold=3)


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    from unittest.mock import Mock
-   from autom8_asana.protocols.log import LogProvider
-   return Mock(spec=LogProvider)
+   return Mock(spec=LogProviderAdapter)
```

### 3.5 Quality Gate

```bash
ruff check src/autom8_asana/transport/
mypy src/autom8_asana/transport/
pytest tests/test_rate_limiter.py tests/test_retry.py tests/test_circuit_breaker.py tests/test_http.py -v
```

**Rollback Point**: Restore original transport implementations.

---

## Phase 4: Settings Layer Migration

**Goal**: Verify settings layer compatibility (minimal changes expected).

**Risk**: Low - already using Pydantic Settings.

### 4.1 Assessment

The spike found that `autom8_asana/settings.py` already uses `pydantic-settings.BaseSettings`. No changes required.

**Optional Enhancement**: Inherit from `autom8y_config.Autom8yBaseSettings` for secret resolution support. Defer this to future work.

### 4.2 Quality Gate

```bash
pytest tests/test_settings.py -v
```

**No changes required for Phase 4.**

---

## Phase 5: Structured Logging Migration (DEFERRED)

**Goal**: Migrate all printf-style logging calls to structured format.

**Risk**: HIGH - touches 100+ logging call sites.

**Recommendation**: DEFER to future sprint after primitive adoption stabilizes.

### 5.1 Scope

When executed, this phase will:

1. Update all logging calls from printf-style to structured:
   ```python
   # Before
   logger.info("Rate limit: waiting %.2fs", wait_time)

   # After
   logger.info("rate_limit_waiting", wait_seconds=round(wait_time, 2))
   ```

2. Remove LogProviderAdapter shim layer

3. Update test assertions for new log format

### 5.2 Files Affected

- `src/autom8_asana/_defaults/log.py` (190 lines)
- `src/autom8_asana/transport/*.py` (logging calls in each)
- `src/autom8_asana/_defaults/auth.py` (logging calls)
- All test files with logging assertions

### 5.3 Estimated Effort

- 4-6 hours of development
- Additional testing time
- **Not critical path** - LogProviderAdapter provides compatibility

---

## Phase 6: Telemetry Integration (SKIP)

**Goal**: Add distributed tracing support.

**Risk**: Low - additive only.

**Recommendation**: SKIP for now - new feature work, not migration.

### 6.1 Future Scope

When executed, this phase will:

1. Add `autom8y-telemetry` dependency
2. Initialize tracing in entry points
3. Add span creation to AsyncHTTPClient

This is **new feature work**, not migration. Schedule separately.

---

## Phase 7: Cleanup

**Goal**: Remove deprecated code after migration confirmed stable.

**Risk**: Low - unreferenced code removal.

### 7.1 Files to Delete

After migration is confirmed working in production (1-2 weeks observation):

| File | Reason |
|------|--------|
| Old dataclass definitions in `config.py` | Replaced by platform imports |
| Old transport implementations (if any remain) | Replaced by wrappers |

### 7.2 Files to Keep

| File | Reason |
|------|--------|
| `transport/http.py` | Orchestrates primitives, contains Asana-specific logic |
| `exceptions.py` (domain errors) | Asana-specific error types |
| `compat/log_adapter.py` | Until Phase 5 executes |
| `protocols/log.py` | LogProvider protocol still used by consumers |
| `_defaults/log.py` | DefaultLogProvider implementation |

### 7.3 Deprecation Warnings

Add deprecation warnings to backward-compatibility aliases:

```python
import warnings

# In config.py
def __getattr__(name: str):
    if name == "RateLimitConfig":
        warnings.warn(
            "RateLimitConfig is deprecated, use RateLimiterConfig from autom8y_http",
            DeprecationWarning,
            stacklevel=2,
        )
        return RateLimiterConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

### 7.4 Quality Gate

```bash
# Full test suite
ruff check src/
mypy src/
pytest tests/ -v --cov=autom8_asana --cov-report=term-missing
```

---

## Import Replacement Summary

### Complete Import Mapping

| autom8_asana Import | Platform Primitive Import | Compatibility |
|---------------------|---------------------------|---------------|
| `autom8_asana.config.RateLimitConfig` | `autom8y_http.RateLimiterConfig` | Alias provided |
| `autom8_asana.config.RetryConfig` | `autom8y_http.RetryConfig` | 100% |
| `autom8_asana.config.CircuitBreakerConfig` | `autom8y_http.CircuitBreakerConfig` | 100% |
| `autom8_asana.transport.rate_limiter.TokenBucketRateLimiter` | `autom8y_http.TokenBucketRateLimiter` | Wrapper provided |
| `autom8_asana.transport.retry.RetryHandler` | `autom8y_http.ExponentialBackoffRetry` | Alias + wrapper |
| `autom8_asana.transport.circuit_breaker.CircuitBreaker` | `autom8y_http.CircuitBreaker` | Wrapper provided |
| `autom8_asana.transport.circuit_breaker.CircuitState` | `autom8y_http.CircuitState` | 100% |
| `autom8_asana.transport.sync.sync_wrapper` | `autom8y_http.sync_wrapper` | 100% |
| `autom8_asana.exceptions.CircuitBreakerOpenError` | `autom8y_http.CircuitBreakerOpenError` | Re-export |
| `autom8_asana.exceptions.SyncInAsyncContextError` | `autom8y_http.SyncInAsyncContextError` | Re-export |
| `autom8_asana.protocols.log.LogProvider` | `autom8y_log.LoggerProtocol` | Adapter required |

---

## Config/Env Var Analysis

### No Conflicts Confirmed

The spike confirmed that platform primitives use different env var prefixes from autom8_asana:

| autom8_asana Env Var | Platform Equivalent | Conflict |
|----------------------|---------------------|----------|
| `ASANA_PAT` | (None - domain-specific) | No |
| `ASANA_WORKSPACE_GID` | (None - domain-specific) | No |
| `ASANA_CACHE_ENABLED` | (None - domain-specific) | No |
| `REDIS_HOST` | (Standard) | No |
| (None) | `RATE_LIMIT_MAX_TOKENS` | No - new |
| (None) | `RETRY_MAX_RETRIES` | No - new |
| (None) | `CIRCUIT_BREAKER_ENABLED` | No - new |

**Conclusion**: Platform primitives can be enabled via env vars without affecting existing autom8_asana configuration.

---

## Test Strategy

### Per-Phase Test Approach

| Phase | Test Strategy |
|-------|---------------|
| Phase 1 | New unit tests for LogProviderAdapter |
| Phase 2 | Existing config tests should pass unchanged |
| Phase 3 | Existing transport tests + new adapter tests |
| Phase 4 | Existing settings tests unchanged |
| Phase 5 | Update all logging assertions (deferred) |
| Phase 7 | Full regression suite |

### Test Files Affected

| Test File | Phase | Changes Required |
|-----------|-------|------------------|
| `tests/test_log_adapter.py` | 1 | New file |
| `tests/test_config.py` | 2 | Import path updates |
| `tests/test_rate_limiter.py` | 3 | Mock updates for adapter |
| `tests/test_retry.py` | 3 | Class name updates |
| `tests/test_circuit_breaker.py` | 3 | Import path, mock updates |
| `tests/test_http.py` | 3 | Integration tests (indirect) |
| `tests/conftest.py` | 3 | New fixtures for platform configs |

### Coverage Preservation

Before migration:
```bash
pytest --cov=autom8_asana --cov-report=html:coverage_before
```

After each phase:
```bash
pytest --cov=autom8_asana --cov-report=html:coverage_after_phase_N
# Coverage must be >= baseline
```

---

## Risk Mitigations

| Risk ID | Risk | Mitigation |
|---------|------|------------|
| RISK-001 | LogProvider signature incompatibility | LogProviderAdapter shim (Phase 1) |
| RISK-002 | Circuit breaker behavior divergence | Comprehensive integration tests |
| RISK-003 | Rate limiter calculation differences | Load testing before production |
| RISK-004 | Config validation rule differences | Config validation test suite |
| RISK-005 | Import cycles from wrappers | Wrappers in separate `compat/` module |
| RISK-006 | Test mocks break | Update fixtures to use adapter types |
| RISK-007 | Performance regression | Benchmark critical paths |
| RISK-008 | Dependency version conflicts | Lock compatible versions in pyproject.toml |

---

## Success Criteria

Migration complete when:

- [ ] All tests pass after each phase
- [ ] Coverage >= baseline (no regression)
- [ ] HTTP client continues to work unchanged (external API preserved)
- [ ] Circuit breaker, rate limiter, retry behavior equivalent to original
- [ ] ruff check passes
- [ ] mypy passes
- [ ] No runtime warnings in production for 1 week

---

## Rollback Plan

Each phase is independently revertible:

| Phase | Rollback Action |
|-------|-----------------|
| Phase 1 | Remove dependencies + delete `compat/` |
| Phase 2 | Restore dataclass definitions in config.py |
| Phase 3 | Restore original transport implementations |
| Phase 4 | N/A (no changes) |
| Phase 5 | N/A (deferred) |
| Phase 6 | N/A (skipped) |
| Phase 7 | N/A (cleanup only) |

Maximum rollback: Revert entire migration branch.

---

## Platform ADR References

This TDD references decisions documented in platform ADRs:

| ADR | Title | Relevance |
|-----|-------|-----------|
| ADR-PRIM-001 | Protocol-based DI | Why we use LoggerProtocol |
| ADR-PRIM-002 | Pydantic Settings for configuration | Config class design |
| ADR-PRIM-004 | Structlog over stdlib logging | Why LogProvider -> LoggerProtocol differs |
| ADR-PRIM-006 | Sync wrapper fail-fast behavior | SyncInAsyncContextError design |

No new ADRs required in autom8_asana - the architectural decisions were made at the platform level.

---

## Artifact Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/architecture/TDD-PRIMITIVE-MIGRATION-001.md` | Pending |
| Spike (input) | `/Users/tomtenuta/Code/autom8y/docs/spikes/SPIKE-AUTOM8-ASANA-PRIMITIVE-ADOPTION.md` | Yes |
| Platform TDD (input) | `/Users/tomtenuta/Code/autom8y/docs/architecture/TDD-PLATFORM-PRIMITIVES-001.md` | Yes |
| Platform PRD (input) | `/Users/tomtenuta/Code/autom8y/docs/requirements/PRD-PLATFORM-PRIMITIVES-001.md` | Yes |
| Platform autom8y-http | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-http/` | Yes |
| Platform autom8y-log | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-log/` | Yes |
| Platform autom8y-config | `/Users/tomtenuta/Code/autom8y/sdks/python/autom8y-config/` | Yes |

---

**End of TDD**
