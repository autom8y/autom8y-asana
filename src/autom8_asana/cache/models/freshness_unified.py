"""Unified freshness enums for cache subsystem.

Consolidates four legacy enums into two:
- FreshnessIntent (replaces Freshness + FreshnessMode)
- FreshnessState (replaces FreshnessClassification + FreshnessStatus)

Per SPIKE-cache-freshness-consolidation.md:
- Zero external dependencies (stdlib enum only)
- str-based for serialization compatibility
- Type aliases at old locations for backward compatibility

Mapping:
    Freshness.STRICT / FreshnessMode.STRICT       -> FreshnessIntent.STRICT
    Freshness.EVENTUAL / FreshnessMode.EVENTUAL    -> FreshnessIntent.EVENTUAL
    Freshness.IMMEDIATE / FreshnessMode.IMMEDIATE  -> FreshnessIntent.IMMEDIATE

    FreshnessClassification.FRESH / FreshnessStatus.FRESH       -> FreshnessState.FRESH
    FreshnessClassification.APPROACHING_STALE /
        FreshnessStatus.STALE_SERVABLE                          -> FreshnessState.APPROACHING_STALE
    FreshnessClassification.STALE /
        FreshnessStatus.EXPIRED_SERVABLE                        -> FreshnessState.STALE
    FreshnessStatus.SCHEMA_MISMATCH                             -> FreshnessState.SCHEMA_INVALID
    FreshnessStatus.WATERMARK_STALE                             -> FreshnessState.WATERMARK_BEHIND
    FreshnessStatus.CIRCUIT_LKG                                 -> FreshnessState.CIRCUIT_FALLBACK
"""

from __future__ import annotations

from enum import Enum


class FreshnessIntent(str, Enum):
    """Cache freshness intent controlling validation behavior.

    Determines how aggressively the cache validates data against the source.

    Members:
        STRICT: Always validate against API before serving.
        EVENTUAL: Serve from cache if within TTL; validate on expiry.
        IMMEDIATE: Serve cached data without any validation.
    """

    STRICT = "strict"
    EVENTUAL = "eventual"
    IMMEDIATE = "immediate"


class FreshnessState(str, Enum):
    """Cache entry freshness state after evaluation.

    Six-state classification enabling graduated cache responses from
    both the entity cache (per-GID) and DataFrame cache (per-project).

    Members:
        FRESH: Within TTL, serve immediately.
        APPROACHING_STALE: Past TTL threshold but within grace window;
            serve stale data and consider background refresh.
        STALE: Beyond grace window but structurally valid;
            serve with degradation warning.
        SCHEMA_INVALID: Schema version mismatch; hard reject.
        WATERMARK_BEHIND: Source has newer data; hard reject.
        CIRCUIT_FALLBACK: Circuit breaker open; serving last known good.
    """

    FRESH = "fresh"
    APPROACHING_STALE = "approaching_stale"
    STALE = "stale"
    SCHEMA_INVALID = "schema_invalid"
    WATERMARK_BEHIND = "watermark_behind"
    CIRCUIT_FALLBACK = "circuit_fallback"


__all__ = ["FreshnessIntent", "FreshnessState"]
