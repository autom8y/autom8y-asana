"""HTTP transport layer components.

Per TDD-ASANA-HTTP-MIGRATION-001/FR-005: The legacy transport modules are
deprecated in favor of autom8y-http platform SDK. This module provides
deprecation warnings for direct access to legacy components.

Migration Guide:
    The transport layer now uses autom8y-http internally. Direct access to
    the following is deprecated and will be removed in v2.0:
    - AsyncHTTPClient
    - TokenBucketRateLimiter
    - RetryHandler
    - CircuitBreaker

    Use the AsanaClient facade instead, which handles transport configuration
    automatically with shared rate limiting.

Preserved Components:
    - sync_wrapper: Utility for creating sync wrappers (not deprecated)
    - AsanaHttpClient: New transport wrapper (recommended for internal use)
    - ConfigTranslator: Config translation layer
    - AsanaResponseHandler: Response handling utilities
"""

from __future__ import annotations

import importlib
import warnings
from typing import TYPE_CHECKING

# Re-export sync_wrapper (not deprecated - it's a utility)
from autom8_asana.transport.sync import sync_wrapper

# Re-export new transport components (recommended)
from autom8_asana.transport.asana_http import AsanaHttpClient
from autom8_asana.transport.config_translator import ConfigTranslator
from autom8_asana.transport.response_handler import AsanaResponseHandler

# CircuitState enum re-exported from platform SDK (autom8y-http >= 0.3.0)
from autom8y_http.protocols import CircuitState

if TYPE_CHECKING:
    # Type hints for deprecated imports
    from autom8_asana.transport.http import AsyncHTTPClient as _AsyncHTTPClient
    from autom8_asana.transport.rate_limiter import (
        TokenBucketRateLimiter as _TokenBucketRateLimiter,
    )
    from autom8_asana.transport.retry import RetryHandler as _RetryHandler
    from autom8_asana.transport.circuit_breaker import CircuitBreaker as _CircuitBreaker


# Mapping of deprecated names to their modules
_DEPRECATED_COMPONENTS = {
    "AsyncHTTPClient": "autom8_asana.transport.http",
    "TokenBucketRateLimiter": "autom8_asana.transport.rate_limiter",
    "RetryHandler": "autom8_asana.transport.retry",
    "CircuitBreaker": "autom8_asana.transport.circuit_breaker",
}


def __getattr__(name: str):
    """Emit deprecation warnings for legacy transport access.

    Per TDD-ASANA-HTTP-MIGRATION-001/FR-005: Deprecated components emit
    warnings but remain functional for backward compatibility.
    """
    if name in _DEPRECATED_COMPONENTS:
        module_path = _DEPRECATED_COMPONENTS[name]
        warnings.warn(
            f"{name} is deprecated. The transport layer now uses autom8y-http. "
            f"Direct access to {module_path} will be removed in v2.0. "
            f"Use AsanaClient instead, which handles transport configuration automatically.",
            DeprecationWarning,
            stacklevel=2,
        )
        module = importlib.import_module(module_path)
        return getattr(module, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # New transport components (recommended)
    "AsanaHttpClient",
    "ConfigTranslator",
    "AsanaResponseHandler",
    # Preserved utilities
    "sync_wrapper",
    "CircuitState",
    # Legacy components (deprecated but still exported for backward compat)
    "AsyncHTTPClient",
    "TokenBucketRateLimiter",
    "RetryHandler",
    "CircuitBreaker",
]
