"""Staleness check configuration settings.

Per TDD-CACHE-LIGHTWEIGHT-STALENESS: Settings for lightweight staleness detection
with progressive TTL extension.

Per ADR-0132: Configurable coalescing parameters (50ms window, 100 max batch).
Per ADR-0133: Configurable TTL parameters (base 300s, max 86400s).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StalenessCheckSettings:
    """Configuration for lightweight staleness checking.

    Per TDD-CACHE-LIGHTWEIGHT-STALENESS: Frozen dataclass for staleness check
    configuration with sensible defaults.

    Attributes:
        enabled: Whether staleness checking is enabled (default True).
        base_ttl: Base TTL in seconds for cache entries (default 300 = 5 min).
        max_ttl: Maximum TTL ceiling in seconds (default 86400 = 24 hours).
        coalesce_window_ms: Coalescing window in milliseconds (default 50).
        max_batch_size: Maximum entries per batch before immediate flush (default 100).

    Example:
        >>> settings = StalenessCheckSettings()
        >>> settings.base_ttl
        300
        >>> settings.max_ttl
        86400
        >>> settings.coalesce_window_ms
        50

        >>> # Custom settings
        >>> custom = StalenessCheckSettings(
        ...     base_ttl=600,
        ...     max_ttl=43200,  # 12 hours
        ...     coalesce_window_ms=100,
        ... )
    """

    enabled: bool = True
    base_ttl: int = 300  # 5 minutes, per ADR-0133
    max_ttl: int = 86400  # 24 hours, per ADR-0133
    coalesce_window_ms: int = 50  # Per ADR-0132
    max_batch_size: int = 100  # Per ADR-0132

    def __post_init__(self) -> None:
        """Validate settings configuration."""
        if self.base_ttl <= 0:
            raise ValueError(f"base_ttl must be positive, got {self.base_ttl}")
        if self.max_ttl <= 0:
            raise ValueError(f"max_ttl must be positive, got {self.max_ttl}")
        if self.max_ttl < self.base_ttl:
            raise ValueError(
                f"max_ttl ({self.max_ttl}) must be >= base_ttl ({self.base_ttl})"
            )
        if self.coalesce_window_ms < 0:
            raise ValueError(
                f"coalesce_window_ms must be non-negative, got {self.coalesce_window_ms}"
            )
        if self.max_batch_size <= 0:
            raise ValueError(
                f"max_batch_size must be positive, got {self.max_batch_size}"
            )

    def calculate_extended_ttl(self, extension_count: int) -> int:
        """Calculate TTL after N extensions using exponential doubling.

        Per ADR-0133: new_ttl = min(base_ttl * 2^count, max_ttl)

        Args:
            extension_count: Number of extensions applied (0 = base TTL).

        Returns:
            TTL in seconds, capped at max_ttl.

        Example:
            >>> settings = StalenessCheckSettings()
            >>> settings.calculate_extended_ttl(0)  # base
            300
            >>> settings.calculate_extended_ttl(1)  # 300 * 2
            600
            >>> settings.calculate_extended_ttl(2)  # 300 * 4
            1200
            >>> settings.calculate_extended_ttl(9)  # hits ceiling
            86400
        """
        if extension_count < 0:
            raise ValueError(
                f"extension_count must be non-negative, got {extension_count}"
            )
        # Exponential doubling: base * 2^count, capped at max
        calculated: int = self.base_ttl * (2**extension_count)
        return min(calculated, self.max_ttl)
