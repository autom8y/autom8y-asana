"""Resolution result supporting multi-match scenarios with status classification.

Per TDD-DYNAMIC-RESOLVER-001 / FR-004:
Returns all matching GIDs while preserving backwards-compatible `gid` property.

Per TDD-STATUS-AWARE-RESOLUTION / FR-3, FR-4, FR-8:
Each matched GID carries an AccountActivity status annotation.
GIDs are ordered by ACTIVITY_PRIORITY. The `gid` property returns
the highest-priority match, not an arbitrary gids[0].
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResolutionResult:
    """Resolution result supporting multi-match scenarios with status classification.

    Per TDD-STATUS-AWARE-RESOLUTION / FR-3, FR-4, FR-8:
    Each matched GID carries an AccountActivity status annotation.
    GIDs are ordered by ACTIVITY_PRIORITY. The `gid` property returns
    the highest-priority match, not gids[0].

    Attributes:
        gids: All matching GIDs (plural), sorted by ACTIVITY_PRIORITY.
        match_count: Explicit count of matches (post-filter).
        match_context: Optional additional fields per match.
        error: Error code if resolution failed.
        status_annotations: Per FR-3. Parallel tuple, same length as gids.
            None when no classifier available (FR-7 degradation).
            Each entry is the AccountActivity.value string or None (UNKNOWN).
        total_match_count: Per FR-11. Pre-filter total count for diagnostic
            metadata. None when active_only=False or no classifier.

    Backwards Compatibility:
        The `gid` property returns the first match (or None),
        matching the current API contract. New clients should
        use `gids` for full match list.

    Example:
        >>> result = ResolutionResult(
        ...     gids=["123", "456"],
        ...     match_count=2,
        ...     status_annotations=("active", "activating"),
        ... )
        >>> result.gid  # Backwards compatible -- best match
        "123"
        >>> result.is_unique
        False
        >>> result.is_ambiguous
        True
    """

    gids: tuple[str, ...] = field(default_factory=tuple)
    match_count: int = 0
    match_context: tuple[dict[str, Any], ...] | None = None
    error: str | None = None

    # Per TDD-STATUS-AWARE-RESOLUTION / FR-3:
    # Parallel tuple, same length as gids. None when no classifier (FR-7).
    status_annotations: tuple[str | None, ...] | None = None

    # Per TDD-STATUS-AWARE-RESOLUTION / FR-11:
    # Pre-filter total count for diagnostic metadata.
    total_match_count: int | None = None

    def __post_init__(self) -> None:
        """Compute match_count from gids if not provided."""
        # Use object.__setattr__ since frozen=True
        if self.match_count == 0 and self.gids:
            object.__setattr__(self, "match_count", len(self.gids))

    @property
    def is_unique(self) -> bool:
        """True if exactly one match found.

        Returns:
            True if match_count == 1.
        """
        return self.match_count == 1

    @property
    def is_ambiguous(self) -> bool:
        """True if multiple matches found.

        Returns:
            True if match_count > 1.
        """
        return self.match_count > 1

    @property
    def gid(self) -> str | None:
        """Backwards-compatible single GID (first match or None).

        Per FR-006: Existing clients expecting single GID continue to work.

        Returns:
            First matching GID or None if no matches.
        """
        return self.gids[0] if self.gids else None

    @classmethod
    def not_found(cls) -> ResolutionResult:
        """Factory for NOT_FOUND result.

        Returns:
            Result with empty gids and NOT_FOUND error.
        """
        return cls(gids=(), match_count=0, error="NOT_FOUND")

    @classmethod
    def from_gids(
        cls,
        gids: list[str],
        context: list[dict[str, Any]] | None = None,
    ) -> ResolutionResult:
        """Factory from list of GIDs with optional context.

        Args:
            gids: List of matching GID strings.
            context: Optional context data per match.

        Returns:
            Result with gids populated, or NOT_FOUND if empty.
        """
        if not gids:
            return cls.not_found()

        return cls(
            gids=tuple(gids),
            match_count=len(gids),
            match_context=tuple(context) if context else None,
        )

    @classmethod
    def from_gids_with_status(
        cls,
        gids: list[str],
        status_annotations: list[str | None] | None = None,
        context: list[dict[str, Any]] | None = None,
        total_match_count: int | None = None,
    ) -> ResolutionResult:
        """Factory from GIDs with status annotations.

        Per TDD-STATUS-AWARE-RESOLUTION / FR-3:
        Creates result with parallel status annotation tuple.
        Caller is responsible for pre-sorting gids by ACTIVITY_PRIORITY.

        Args:
            gids: List of matching GID strings (pre-sorted).
            status_annotations: Parallel list of status strings or None.
            context: Optional context data per match.
            total_match_count: Pre-filter total count (when active_only=True).

        Returns:
            Result with gids and status populated, or NOT_FOUND if empty.
        """
        if not gids:
            return cls.not_found()

        return cls(
            gids=tuple(gids),
            match_count=len(gids),
            match_context=tuple(context) if context else None,
            status_annotations=tuple(status_annotations) if status_annotations else None,
            total_match_count=total_match_count,
        )

    @classmethod
    def error_result(cls, error: str) -> ResolutionResult:
        """Factory for error result.

        Args:
            error: Error code string.

        Returns:
            Result with specified error.
        """
        return cls(gids=(), match_count=0, error=error)

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response dict.

        Per TDD-STATUS-AWARE-RESOLUTION / FR-3, FR-11:
        Includes status_annotations and total_match_count when present.

        Returns:
            Dict suitable for JSON serialization.
        """
        result: dict[str, Any] = {
            "gids": list(self.gids),
            "match_count": self.match_count,
            "gid": self.gid,  # Backwards compat
        }

        if self.error:
            result["error"] = self.error

        if self.match_context:
            result["context"] = list(self.match_context)

        # Per TDD-STATUS-AWARE-RESOLUTION / FR-3:
        if self.status_annotations is not None:
            result["status_annotations"] = list(self.status_annotations)

        # Per TDD-STATUS-AWARE-RESOLUTION / FR-11:
        if self.total_match_count is not None:
            result["total_match_count"] = self.total_match_count

        return result
