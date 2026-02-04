"""Backward-compatibility shim for cache.factory -> cache.integration.factory.

Per HYG-012 FINDING-001: api/main.py (read-only zone) imports from
cache.factory which was moved to cache.integration.factory during
reorganization. This shim preserves the old import path.
"""

from autom8_asana.cache.integration.factory import *  # noqa: F403, F401
