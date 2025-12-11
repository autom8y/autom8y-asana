"""Name normalization for custom field matching.

Per TDD-0009.1: Normalizes field names to a canonical form for matching:
- "Weekly Ad Spend" -> "weeklyadspend"
- "weekly_ad_spend" -> "weeklyadspend"
- "MRR" -> "mrr"
- "Monthly-Recurring-Revenue" -> "monthlyrecurringrevenue"

Uses LRU cache for performance (maxsize=1024).
"""

from __future__ import annotations

import re
from functools import lru_cache


class NameNormalizer:
    """Normalize field names for matching.

    Converts various naming conventions to a canonical form
    for comparison. The canonical form is lowercase with only
    alphanumeric characters (no spaces, underscores, hyphens, etc.).

    This enables matching between:
    - Schema field names (snake_case): "weekly_ad_spend"
    - Asana field names (Title Case): "Weekly Ad Spend"
    - Acronyms: "MRR", "ID"
    - Hyphenated: "Monthly-Recurring-Revenue"

    Example:
        >>> NameNormalizer.normalize("Weekly Ad Spend")
        'weeklyadspend'
        >>> NameNormalizer.normalize("weekly_ad_spend")
        'weeklyadspend'
        >>> NameNormalizer.is_match("MRR", "mrr")
        True

    Thread-Safety:
        All methods are thread-safe (pure functions with LRU cache).
    """

    # Pre-compiled regex for performance
    _NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]")

    @staticmethod
    @lru_cache(maxsize=1024)
    def normalize(name: str) -> str:
        """Normalize name to canonical form.

        Args:
            name: Field name in any format

        Returns:
            Canonical lowercase form with only alphanumeric chars.
            Empty string if name is empty or None-like.

        Example:
            >>> NameNormalizer.normalize("Weekly Ad Spend")
            'weeklyadspend'
            >>> NameNormalizer.normalize("MRR")
            'mrr'
            >>> NameNormalizer.normalize("")
            ''
        """
        if not name:
            return ""
        # Lowercase first, then remove non-alphanumeric
        return NameNormalizer._NON_ALPHANUMERIC.sub("", name.lower())

    @staticmethod
    def is_match(name1: str, name2: str) -> bool:
        """Check if two names match after normalization.

        Args:
            name1: First field name
            name2: Second field name

        Returns:
            True if normalized forms are equal

        Example:
            >>> NameNormalizer.is_match("Weekly Ad Spend", "weekly_ad_spend")
            True
            >>> NameNormalizer.is_match("MRR", "ARR")
            False
        """
        return NameNormalizer.normalize(name1) == NameNormalizer.normalize(name2)

    @staticmethod
    def cache_info() -> dict[str, int]:
        """Get LRU cache statistics for debugging.

        Returns:
            Dict with hits, misses, maxsize, currsize

        Example:
            >>> NameNormalizer.normalize("test")
            'test'
            >>> info = NameNormalizer.cache_info()
            >>> info["currsize"] >= 1
            True
        """
        info = NameNormalizer.normalize.cache_info()
        return {
            "hits": info.hits,
            "misses": info.misses,
            "maxsize": info.maxsize or 0,
            "currsize": info.currsize,
        }

    @staticmethod
    def clear_cache() -> None:
        """Clear the LRU cache.

        Useful for testing or when memory pressure is high.
        """
        NameNormalizer.normalize.cache_clear()
