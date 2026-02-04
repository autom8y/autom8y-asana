"""Backward-compatibility shim for cache.schema_providers -> cache.integration.schema_providers.

Per HYG-012 FINDING-001: api/main.py (read-only zone) imports from
cache.schema_providers which was moved to cache.integration.schema_providers
during reorganization. This shim preserves the old import path.
"""

from autom8_asana.cache.integration.schema_providers import *  # noqa: F403, F401
