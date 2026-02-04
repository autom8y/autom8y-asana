"""Cache preload subsystem for DataFrame warming at startup.

Extracted from api/main.py per TDD-I5 (API Main Decomposition).
"""

from .progressive import _preload_dataframe_cache_progressive

__all__ = ["_preload_dataframe_cache_progressive"]
