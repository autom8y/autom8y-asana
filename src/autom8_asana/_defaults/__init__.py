"""Default provider implementations for standalone SDK usage.

Per TDD-HARDENING-A/FR-OBS-010: Export NullObservabilityHook.
Per ADR-VAULT-001: Export SecretsManagerAuthProvider for AWS deployments.
"""

from autom8_asana._defaults.auth import (
    EnvAuthProvider,
    NotConfiguredAuthProvider,
    SecretsManagerAuthProvider,
)
from autom8_asana._defaults.cache import InMemoryCacheProvider, NullCacheProvider
from autom8_asana._defaults.log import DefaultLogProvider
from autom8_asana._defaults.observability import NullObservabilityHook

__all__ = [
    # Auth providers
    "EnvAuthProvider",
    "NotConfiguredAuthProvider",
    "SecretsManagerAuthProvider",  # ADR-VAULT-001
    # Cache providers
    "NullCacheProvider",
    "InMemoryCacheProvider",
    # Log providers
    "DefaultLogProvider",
    # Observability (TDD-HARDENING-A/FR-OBS-010)
    "NullObservabilityHook",
]
