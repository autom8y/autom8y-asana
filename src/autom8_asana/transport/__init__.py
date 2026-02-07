"""HTTP transport layer components.

Per TDD-ASANA-HTTP-MIGRATION-001/FR-005: Legacy transport modules have been
removed. The transport layer now uses autom8y-http platform SDK.

Active Components:
    - sync_wrapper: Utility for creating sync wrappers
    - AsanaHttpClient: New transport wrapper (recommended for internal use)
    - ConfigTranslator: Config translation layer
    - AsanaResponseHandler: Response handling utilities
    - CircuitState: Circuit breaker state enum (from autom8y-http)
"""

from __future__ import annotations

# CircuitState enum re-exported from platform SDK (autom8y-http >= 0.3.0)
from autom8y_http.protocols import CircuitState

# Re-export AIMD adaptive concurrency components (per TDD-GAP-04)
from autom8_asana.transport.adaptive_semaphore import AsyncAdaptiveSemaphore

# Re-export new transport components (recommended)
from autom8_asana.transport.asana_http import AsanaHttpClient
from autom8_asana.transport.config_translator import ConfigTranslator
from autom8_asana.transport.response_handler import AsanaResponseHandler

# Re-export sync_wrapper (utility for sync operations)
from autom8_asana.transport.sync import sync_wrapper

__all__ = [
    # Transport components
    "AsanaHttpClient",
    "AsyncAdaptiveSemaphore",
    "ConfigTranslator",
    "AsanaResponseHandler",
    # Utilities
    "sync_wrapper",
    "CircuitState",
]
