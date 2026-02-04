"""Backward-compatibility shim for cache.tiered -> cache.providers.tiered.

Per HYG-012 FINDING-001: lambda_handlers/cache_invalidate.py (read-only zone)
imports from cache.tiered which was moved to cache.providers.tiered during
reorganization. This shim preserves the old import path.
"""

from autom8_asana.cache.providers.tiered import *  # noqa: F403, F401
