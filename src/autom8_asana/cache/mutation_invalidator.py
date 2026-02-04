"""Backward-compatibility shim for cache.mutation_invalidator -> cache.integration.mutation_invalidator.

Per HYG-012 FINDING-001: api/main.py (read-only zone) imports from
cache.mutation_invalidator which was moved to cache.integration.mutation_invalidator
during reorganization. This shim preserves the old import path.
"""

from autom8_asana.cache.integration.mutation_invalidator import *  # noqa: F403, F401
