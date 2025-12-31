"""GID lookup index for O(1) phone/vertical to GID resolution.

This module provides an optimized lookup layer for resolving business GIDs
from (office_phone, vertical) pairs. The index is built from a DataFrame
and provides O(1) dictionary-based lookups.

Per task-002: Builds on cache population pattern from task-001.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import polars as pl

    from autom8_asana.models.contracts.phone_vertical import PhoneVerticalPair


class GidLookupIndex:
    """O(1) lookup index for GID resolution by phone/vertical pair.

    This class builds an internal dictionary from a DataFrame containing
    unit records with office_phone, vertical, and gid columns. It provides
    fast, constant-time lookups using the PhoneVerticalPair.canonical_key.

    Attributes:
        created_at: Timestamp when the index was created.

    Example:
        >>> index = GidLookupIndex.from_dataframe(df)
        >>> pair = PhoneVerticalPair(office_phone="+17705753103", vertical="chiropractic")
        >>> gid = index.get_gid(pair)
        >>> print(gid)  # "1234567890123456"

    Note:
        The index uses canonical_key format 'pv1:{phone}:{vertical}' for
        version-prefixed key compatibility (per ADR-PVP-002).
    """

    def __init__(
        self,
        lookup_dict: dict[str, str],
        created_at: datetime,
    ) -> None:
        """Initialize the lookup index.

        Args:
            lookup_dict: Dictionary mapping canonical_key to gid.
            created_at: Timestamp when the index was created.

        Note:
            Prefer using the from_dataframe() factory method for construction.
        """
        self._lookup: dict[str, str] = lookup_dict
        self._created_at: datetime = created_at

    @property
    def created_at(self) -> datetime:
        """Timestamp when the index was created."""
        return self._created_at

    def __len__(self) -> int:
        """Return the number of entries in the index."""
        return len(self._lookup)

    def __contains__(self, pair: PhoneVerticalPair) -> bool:
        """Check if a phone/vertical pair exists in the index.

        Args:
            pair: PhoneVerticalPair to check.

        Returns:
            True if the pair exists in the index.
        """
        return pair.canonical_key in self._lookup

    def get_gid(self, pair: PhoneVerticalPair) -> Optional[str]:
        """Look up GID for a phone/vertical pair.

        Performs O(1) dictionary lookup using the pair's canonical_key.

        Args:
            pair: PhoneVerticalPair identifying the business.

        Returns:
            The GID string if found, None otherwise.

        Example:
            >>> gid = index.get_gid(pair)
            >>> if gid is None:
            ...     print("Business not found")
        """
        return self._lookup.get(pair.canonical_key)

    def get_gids(
        self,
        pairs: list[PhoneVerticalPair],
    ) -> dict[PhoneVerticalPair, Optional[str]]:
        """Look up GIDs for multiple phone/vertical pairs.

        Performs batch lookup, preserving input order in the result.

        Args:
            pairs: List of PhoneVerticalPair instances to look up.

        Returns:
            Dictionary mapping each input pair to its GID (or None if not found).
            Order matches the input list order.

        Example:
            >>> results = index.get_gids([pair1, pair2, pair3])
            >>> for pair, gid in results.items():
            ...     print(f"{pair.office_phone}: {gid}")
        """
        return {pair: self.get_gid(pair) for pair in pairs}

    def is_stale(self, ttl_seconds: int) -> bool:
        """Check if the index has exceeded its TTL.

        Args:
            ttl_seconds: Maximum age in seconds before index is considered stale.

        Returns:
            True if the index is older than ttl_seconds.

        Example:
            >>> if index.is_stale(ttl_seconds=3600):  # 1 hour
            ...     index = GidLookupIndex.from_dataframe(fresh_df)
        """
        age = datetime.now(timezone.utc) - self._created_at
        return age.total_seconds() > ttl_seconds

    @classmethod
    def from_dataframe(cls, df: pl.DataFrame) -> GidLookupIndex:
        """Create a GidLookupIndex from a DataFrame.

        Builds the internal lookup dictionary from a DataFrame containing
        office_phone, vertical, and gid columns. Filters out rows with
        null values in any of these columns.

        Args:
            df: Polars DataFrame with columns: office_phone, vertical, gid.
                Must follow UNIT_SCHEMA structure.

        Returns:
            New GidLookupIndex instance with O(1) lookup capability.

        Raises:
            KeyError: If required columns are missing from DataFrame.

        Example:
            >>> df = pl.DataFrame({
            ...     "office_phone": ["+17705753103", "+14045551234"],
            ...     "vertical": ["chiropractic", "dental"],
            ...     "gid": ["123", "456"],
            ... })
            >>> index = GidLookupIndex.from_dataframe(df)
            >>> len(index)
            2

        Note:
            Rows with null office_phone, vertical, or gid are skipped.
            The canonical_key format is 'pv1:{phone}:{vertical}'.
        """
        required_columns = {"office_phone", "vertical", "gid"}
        missing = required_columns - set(df.columns)
        if missing:
            raise KeyError(f"Missing required columns: {missing}")

        # Build lookup dictionary, filtering nulls
        lookup_dict: dict[str, str] = {}

        # Filter out rows with null values in required columns
        valid_df = df.filter(
            df["office_phone"].is_not_null()
            & df["vertical"].is_not_null()
            & df["gid"].is_not_null()
        )

        # Build the dictionary using canonical_key format
        for row in valid_df.iter_rows(named=True):
            phone = row["office_phone"]
            vertical = row["vertical"]
            gid = row["gid"]
            # Use canonical_key format: pv1:{phone}:{vertical}
            canonical_key = f"pv1:{phone}:{vertical}"
            lookup_dict[canonical_key] = gid

        return cls(
            lookup_dict=lookup_dict,
            created_at=datetime.now(timezone.utc),
        )
