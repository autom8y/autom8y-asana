"""Resolution result supporting multi-match scenarios.

Per TDD-DYNAMIC-RESOLVER-001 / FR-004:
Returns all matching GIDs while preserving backwards-compatible `gid` property.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResolutionResult:
    """Resolution result supporting multi-match scenarios.

    Per FR-004: Supports multiple GID matches while maintaining
    backwards compatibility with single-GID responses.

    Attributes:
        gids: All matching GIDs (plural).
        match_count: Explicit count of matches.
        match_context: Optional additional fields per match.
        error: Error code if resolution failed.

    Backwards Compatibility:
        The `gid` property returns the first match (or None),
        matching the current API contract. New clients should
        use `gids` for full match list.

    Example:
        >>> result = ResolutionResult(
        ...     gids=["123", "456"],
        ...     match_count=2,
        ... )
        >>> result.gid  # Backwards compatible
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

        return result
