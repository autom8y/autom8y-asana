"""Configuration dataclasses for autom8_asana SDK.

Per TDD-TECH-DEBT-REMEDIATION/FR-DET-007: Includes startup validation for
ASANA_PROJECT_* environment variables.

Per TDD-CACHE-INTEGRATION: Includes CacheConfig for environment-aware
cache provider selection.

Per TDD-PRIMITIVE-MIGRATION-001: Platform config imports available for new code.
Domain-specific configs (RateLimitConfig, etc.) remain as local dataclasses
for backward compatibility. Transport wrappers handle translation.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

# Platform primitive configs - imported for use in transport wrappers
# Per TDD-PRIMITIVE-MIGRATION-001 Phase 2
from autom8y_http import (
    CircuitBreakerConfig as PlatformCircuitBreakerConfig,
)
from autom8y_http import (
    RateLimiterConfig as PlatformRateLimiterConfig,
)
from autom8y_http import (
    RetryConfig as PlatformRetryConfig,
)
from autom8y_log import get_logger

from autom8_asana.automation.config import AutomationConfig
from autom8_asana.errors import ConfigurationError
from autom8_asana.settings import get_settings

if TYPE_CHECKING:
    from autom8_asana.cache.models.freshness_unified import FreshnessIntent
    from autom8_asana.cache.models.settings import OverflowSettings, TTLSettings

__all__ = [
    # Domain-specific configs (backward compatible)
    "RateLimitConfig",
    "RetryConfig",
    "ConcurrencyConfig",
    "TimeoutConfig",
    "ConnectionPoolConfig",
    "CircuitBreakerConfig",
    "S3LocationConfig",
    "CacheConfig",
    "DataFrameConfig",
    "AutomationConfig",
    "AsanaConfig",
    "validate_project_env_vars",
    "DEFAULT_ENTITY_TTLS",
    "DEFAULT_TTL",
    "SWR_GRACE_MULTIPLIER",
    "LKG_MAX_STALENESS_MULTIPLIER",
    "FRESHNESS_CONTRACT_MAX_AGE_SECONDS",
    # Platform primitive configs (for new code)
    "PlatformRateLimiterConfig",
    "PlatformRetryConfig",
    "PlatformCircuitBreakerConfig",
    # Accessors
    "get_workspace_gid",
]

logger = get_logger(__name__)


def _env_int(name: str, default: int) -> int:
    """Read an int from the environment, falling back to ``default``.

    Used for C-3 concurrency tuning knobs so SRE can damp the warm storm without
    a redeploy. A malformed value falls back to the default rather than crashing
    the Lambda cold start (and logs a warning for diagnosability).
    """
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning(
            "invalid_int_env_override",
            extra={"env": name, "value": raw, "fallback": default},
        )
        return default


def _env_float(name: str, default: float) -> float:
    """Read a float from the environment, falling back to ``default``.

    Companion to :func:`_env_int` for fractional AIMD knobs (e.g. the
    multiplicative-decrease factor).
    """
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning(
            "invalid_float_env_override",
            extra={"env": name, "value": raw, "fallback": default},
        )
        return default


# =============================================================================
# Environment Accessors
# =============================================================================


def get_workspace_gid() -> str | None:
    """Get workspace GID from settings (ASANA_WORKSPACE_GID env var).

    Returns:
        Workspace GID string if configured, None otherwise.
    """
    return get_settings().asana.workspace_gid


# =============================================================================
# Entity TTL Configuration (Single Source of Truth)
# =============================================================================
# Per ADR-0126: Entity-type-specific TTL configuration.
# These values are used by CacheConfig, TasksClient, and TaskCacheCoordinator.
# DO NOT duplicate these values elsewhere - import from this module.

DEFAULT_TTL: int = 300  # 5 minutes - fallback for unknown entity types

# Per SPIKE-stale-while-revalidate-freshness Option A:
# Stale entries are served for up to GRACE_MULTIPLIER * entity_TTL seconds
# while a background refresh runs. Beyond that window the entry is expired.
SWR_GRACE_MULTIPLIER: float = 3.0

# Last-Known-Good (LKG) configuration:
# Controls how long expired entries can be served as LKG fallback.
# 0.0 = ceiling DISABLED — serve forever if schema/watermark valid (the guard at
#       dataframe_cache.py:531 `if LKG_MAX_STALENESS_MULTIPLIER > 0:` is never
#       entered, so unbounded-stale entries are returned as 2xx).
# >0.0 = bound: serve for up to LKG_MAX_STALENESS_MULTIPLIER * entity_TTL seconds,
#        then trip to None -> _build_on_miss -> 503+Retry-After (backpressure).
#
# PDR-001 (thermia capacity-specification §3): the default is 10.0, NOT 0.0.
# A multiplier of 0.0 flatters the success rate by serving unbounded-stale data
# as 2xx; 10.0 bounds it (offer TTL=180s -> 1800s/30min ceiling; covers the
# warmer cycle while keeping stale offer data operationally meaningful).
# HONESTY NOTE: enabling the ceiling LOWERS the apparent success rate — honest
# 503s replace flattered 2xx once a frame ages past the ceiling. OPS MUST run a
# full warmer cycle BEFORE deploying this change so the warmer has covered the
# key set before backpressure can fire (deploy-order is an ops-runbook concern,
# cache-architecture.md §3.1; not a code gate here).
LKG_MAX_STALENESS_MULTIPLIER: float = 10.0

# ADR-serve-stale-within-bound (2026-06-03): per-entity ABSOLUTE max-age ceiling
# (seconds) that OVERRIDES the multiplier-derived ceiling
# (LKG_MAX_STALENESS_MULTIPLIER * entity_ttl) for entities that have a calibrated
# freshness contract. Map key = entity_type (lowercased); value = max age in
# seconds a STALE/LKG entry may be served before hard-reject -> 503+Retry-After.
#
# CALIBRATED to the ratified OQ-2 contract (2026-06-03). OQ-2 returned the
# per-entity freshness tolerance directly from the consumer/monolith owners'
# source of truth: autom8/config/thresholds/caching.py (repo autom8y/autom8).
# Values below are the consumer's own declared refresh cadences, transcribed to
# seconds and keyed on the receiver entity_type (the key this map is `.get()`-ed
# on at dataframe_cache.py STALE branch). NOT internal best-guesses — each value
# carries a consumer-source receipt:
#
#   "project" = 86400  (24h)  <- PROJECT_DF_REFRESH_HOURS=24    caching.py:33
#   "section" =  3000  (50min) <- RECALIBRATED 2026-06-04 (see SECTION RECALIBRATION)
#
# NOTE on the project value: caching.py:33 source is PROJECT_DF_REFRESH_HOURS=24
# = 86400s. Unchanged by this recalibration.
#
# SECTION RECALIBRATION (2026-06-04, T1 knob re-think — GATED on CQ-RETURN-3):
# The section value was 576s (SECTION_DF_REFRESH_HOURS=0.16 -> caching.py:39), the
# transcribed OQ-2 contract. That value was correct ONLY while it was PAIRED with
# the §B ≤10-min SECTION warm lane that kept steady-state section reads younger
# than 576s so they never reached the build path (ADR-section-10min-x-502-headroom
# §B goal). That lane has been DEPLOYED, EXECUTED, found INFEASIBLE, and PAUSED:
# the §B lane hit ~896 Asana rate_limit_429 on the resolver token and reached only
# 5 of 34 GIDs in ~12 min (full-coverage projection ~80 min ≈ 8× over the 576s
# contract). Root cause = the upstream Asana API rate limit, NOT receiver compute;
# raising the lane's reserved_concurrency WORSENS it (more parallel links -> more
# concurrent 429s on the same token bucket). The lane is PAUSED
# (reserved_concurrency=0 + EventBridge rule autom8-asana-cache-warmer-section-
# schedule DISABLED) and stays paused. See
# HANDOFF-asana-sre-to-autom8-cr3-return-3-2026-06-04.md §2.
#
# CONSEQUENCE of the old 576s with the lane paused: section=576 is a max_age
# CEILING that is TIGHTER (5.2×) than the multiplier-derived ceiling
# (LKG_MAX_STALENESS_MULTIPLIER(10.0) × DEFAULT_TTL(300) = 3000s = 50min — both
# section and project carry default_ttl_seconds=300 at entity_registry.py:897/:935,
# so neither appears in DEFAULT_ENTITY_TTLS' !=300 filter and both fall back to
# DEFAULT_TTL in the STALE branch at dataframe_cache.py:529). So with the lane
# paused, every section read older than 576s HARD-REJECTS -> cache-miss -> build
# -> 502/503 path (gate: dataframe_cache.py:550-564). The §D re-scope (V6 serve-
# stale-section) puts SECTION on the SAME serve-stale/LKG relief path as PROJECT,
# absorbing builds in the 2048/8192 headroom — which requires LOOSENING the bound.
#
# BOUND OPTIONS considered (each is a freshness-vs-build-pressure trade-off):
#   (i)  3000  (50min)  — align to the LKG multiplier ceiling exactly; section
#                          rides LKG like the multiplier intends -> MAX relief,
#                          section joins project on serve-stale. RECOMMENDED.
#   (ii) 2760  (~46min) — the bulk warmer's empirically-achievable heaviest-GID
#                          inter-warm cadence (ADR-section-10min-x-502-headroom
#                          §B.1: ~46-min inter-warm for the heaviest GID on the
#                          30-min bulk tick). Ties the contract to the demonstrated
#                          warm cadence rather than the internal ceiling.
#   (iii) drop the key   — section falls back to the multiplier ceiling (3000s) by
#                          the .get() default, identical RUNTIME effect to (i) but
#                          STOPS declaring a section freshness "contract" (honest:
#                          there is no consumer-ratified section contract once 576
#                          is abandoned). Cleanest if section has no real contract.
#
# RECOMMENDED DEFAULT = (i) 3000.0. Rationale: it is the cleanest "section joins
# project on LKG-serve", it is exactly the multiplier ceiling (so the override is
# a no-op relative to the multiplier — maximal relief with zero surprise), and it
# is a concrete declared value (vs (iii) which silently relies on the .get()
# default). (iii) is the honest runner-up if the consumer says 576s was never
# load-bearing. (ii) is the choice if the consumer wants the contract pinned to
# the achievable warm cadence rather than the internal ceiling.
#
# GATE: this VALUE is GATED on the consumer's answer to CQ-RETURN-3 ("is 576s
# SECTION freshness load-bearing for offer-join correctness, or is serve-stale-
# section at ~30–50min acceptable?"). PR is AUTHORED-NOT-MERGED; the section
# value below is the RECOMMENDED DEFAULT pending (a) the CQ-RETURN-3 answer and
# (b) a deliberate land gate. If the consumer chooses (b) WAIT-for-CDC, the
# section arm stays HELD and this value is moot until the CDC R&D lands. DO NOT
# merge/deploy this value without the consumer answer + an explicit land gate.
#
# DELIBERATELY keyed on ONLY the two entity_types this knob can actually affect.
# The knob keys on entry.entity_type (dataframe_cache.py STALE branch); the only
# entity_types served through that serve-stale path are the receiver dataframe
# entities in entity_registry.py — "project" and "section". The other OQ-2 tiers
# (BASE_FACTORY/analytics + RECONCILIATION/backfill = 24h, caching.py:15/:28;
# VERTICAL_SUMMARY = 720h, caching.py:22) are CONSUMER-SIDE (autom8 monolith)
# refresh cadences with NO corresponding entity_type in this receiver's cache
# keyspace. Adding "analytics"/"backfill"/"vertical_summary" keys here would be
# DEAD KEYS (.get() never matches) — an arbitrary internal mapping masquerading
# as a contract, the exact anti-pattern this knob's prior comment forbade. They
# are intentionally OMITTED, not forgotten.
#
# LOAD-BEARING TENSION (dual-edge ceiling — see ADR-serve-stale-within-bound
# §Consequences): this knob is a max_age CEILING. Each entry is a CEILING above
# which a stale frame hard-rejects -> build path. A TIGHTER value = fresher data
# but MORE build/502 pressure; a LOOSER value = more serve-stale relief but staler
# data. "project" = 86400s (24h) LOOSENS project well past the 3000s multiplier
# ceiling -> project reads ride serve-stale/LKG and almost never rebuild. With the
# §B section warm lane PAUSED (see SECTION RECALIBRATION above), "section" is
# loosened from 576s to the 3000s LKG ceiling so section reads ALSO ride serve-
# stale/LKG (the §D V6 serve-stale-section paradigm) instead of hard-rejecting
# onto the POST /v1/query/section/rows 502 hotspot. The prior 576s value only made
# sense paired with the ≤10-min warm lane, which proved Asana-429-infeasible.
# OFFER WARM-RESILIENCE (2026-06-25, operator-adjudicated (b)+(c) availability-first):
# The offer frame (entity_type "offer", primary_project_gid=1143843662099250;
# entity_registry.py warmable=True warm_priority=3 ttl=180s) had NO contract entry,
# so its ceiling fell back to the multiplier: LKG_MAX_STALENESS_MULTIPLIER(10.0) ×
# ttl(180) = 1800s. The offer frame's OBSERVED warm cadence is ~70 min (per the SRE
# measured handoff: warms at 20:39 / 21:49Z, ~70 min apart), so for the bulk of
# every ~70-min window the frame is older than 1800s; the STALE branch sheds None,
# offer is cache-only (no build-on-miss) => 503 via
# dataframe_cache_*_lkg_max_staleness_exceeded. NOT a warm-coverage gap — a ceiling
# mis-calibration relative to the observed warm cadence.
#
# NOTE — `0 */4` is NOT a warm lane. The 4-hourly cron `0 */4`
# (`autom8y-account-status-recon-schedule`) is the DISABLED ASR consumer-READ
# schedule (node-4, currently DEFERRED), i.e. how often the consumer READS offer
# data — NOT how often this receiver warms the frame. Conflating the two
# (the prior comment's "warmed on a 4h cron warm_all lane `0 */4`") was a
# FACTUALLY-FALSE premise; corrected here. The receiver has no `0 */4` warm lane.
#
# OPERATOR RATIFICATION: the ASR/BI consumer ACCEPTS up-to-~4h-stale offer data —
# availability-first ((b)+(c): "≤~4h-stale offer data accepted for the 4-hourly
# recon"). That tolerance — keyed to the consumer's 4-hourly recon READ, not to any
# warm cadence — is the basis for this ceiling: it is the consumer's declared real
# freshness tolerance (the OQ-2-class contract receipt for offer), not an internal
# best-guess.
#
# VALUE = 16200.0 (4h30m): the operator-ratified availability-first read-tolerance
# bound, set comfortably ABOVE the observed ~70-min warm cadence so a frame warmed
# once per warm window never ages past the ceiling mid-window even under AIMD
# warm-governor backoff / 429-throttled hierarchy-gap warming, while remaining
# within the ~4h consumer tolerance. This value is NOT load-bearing for
# availability: FIX (c) is the cadence-INDEPENDENT backstop — it serves ANY
# populated/healthy cache-only frame over ANY ceiling as LKG 2xx (with
# record_serving_stale honesty) + SWR refresh, regardless of this number. FIX (b)
# (this entry) flips ceiling_source multiplier -> freshness_contract for offer so
# the honest-LKG path is attributed to the ratified contract rather than the
# multiplier.
FRESHNESS_CONTRACT_MAX_AGE_SECONDS: dict[str, float] = {
    "project": 86400.0,  # PROJECT_DF_REFRESH_HOURS=24  -> caching.py:33 (24h)
    # section: RECALIBRATED 576 -> 3000 (50min LKG ceiling). GATED on CQ-RETURN-3
    # + a deliberate land gate. See SECTION RECALIBRATION comment above.
    "section": 3000.0,
    # offer: 16200s (4h30m) = operator-ratified availability-first read-tolerance
    # bound (≤~4h-stale for the 4-hourly recon), set above the observed ~70-min warm
    # cadence; NOT load-bearing (FIX (c) is the cadence-independent backstop). GATED
    # on operator land-gate / OQ-2 consumer ratification — see memory
    # autom8y-asana-query503-coldframe. See OFFER WARM-RESILIENCE comment above.
    "offer": 16200.0,
}

# FACADE: Delegates to EntityRegistry. Preserves existing import path.
# See: src/autom8_asana/core/entity_registry.py for the single source of truth.
from autom8_asana.core.entity_registry import get_registry as _get_entity_registry

DEFAULT_ENTITY_TTLS: dict[str, int] = {
    d.name: d.default_ttl_seconds
    for d in _get_entity_registry().all_descriptors()
    if d.default_ttl_seconds != 300
}


@dataclass(frozen=True)
class RateLimitConfig:
    """Rate limiting configuration.

    Default: 1500 requests per 60 seconds (Asana's limit).
    """

    max_requests: int = field(default_factory=lambda: get_settings().rate_limit.max_requests)
    window_seconds: int = field(default_factory=lambda: get_settings().rate_limit.window_seconds)

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_requests <= 0:
            raise ConfigurationError(f"max_requests must be positive, got {self.max_requests}")
        if self.window_seconds <= 0:
            raise ConfigurationError(f"window_seconds must be positive, got {self.window_seconds}")


@dataclass(frozen=True)
class RetryConfig:
    """Retry behavior configuration.

    Attributes:
        max_retries: Maximum retry attempts (default 5)
        base_delay: Initial delay in seconds (default 0.5)
        max_delay: Maximum delay cap in seconds (default 60)
        exponential_base: Multiplier for exponential backoff (default 2)
        jitter: Add random jitter to delays (default True)
        retryable_status_codes: HTTP status codes that trigger retry
    """

    max_retries: int = 5
    base_delay: float = 0.5
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_status_codes: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 503, 504})
    )

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_retries < 0:
            raise ConfigurationError(f"max_retries must be non-negative, got {self.max_retries}")
        if self.base_delay < 0:
            raise ConfigurationError(f"base_delay must be non-negative, got {self.base_delay}")
        if self.max_delay <= 0:
            raise ConfigurationError(f"max_delay must be positive, got {self.max_delay}")
        if self.exponential_base < 1:
            raise ConfigurationError(
                f"exponential_base must be at least 1, got {self.exponential_base}"
            )


@dataclass(frozen=True)
class ConcurrencyConfig:
    """Concurrency limits for API requests.

    Separate limits for read (GET) and write (POST/PUT/DELETE) operations.

    Per TDD-GAP-04: AIMD parameters control adaptive concurrency behavior.
    When aimd_enabled=True (default), AsanaHttpClient uses AsyncAdaptiveSemaphore
    that halves concurrency on 429 and increments by 1 on success.
    When aimd_enabled=False, plain asyncio.Semaphore behavior is used via
    FixedSemaphoreAdapter (kill switch for safe rollback).
    """

    # C-3 (TDD-asr-offer-warmer-durability §6): the read ceiling and AIMD
    # aggressiveness are env-overridable so SRE can damp the self-inflicted 429
    # storm WITHOUT a redeploy. Defaults are lowered from the prior read_limit=50
    # / decrease=0.5: a cold warm that begins at a 50-wide window blasts the API
    # before AIMD can react (the proven ROOT-1a self-storm). Env knobs:
    #   ASANA_CONCURRENCY_READ_LIMIT, ASANA_CONCURRENCY_WRITE_LIMIT,
    #   ASANA_CONCURRENCY_AIMD_START_WINDOW, ASANA_CONCURRENCY_AIMD_MULT_DECREASE
    read_limit: int = field(
        default_factory=lambda: _env_int("ASANA_CONCURRENCY_READ_LIMIT", 12)
    )  # Concurrent GET requests (AIMD ceiling) -- lowered from 50 (ROOT-1a)
    write_limit: int = field(
        default_factory=lambda: _env_int("ASANA_CONCURRENCY_WRITE_LIMIT", 8)
    )  # Concurrent mutation requests (AIMD ceiling)

    # AIMD parameters (all optional, sensible defaults)
    aimd_enabled: bool = True  # Kill switch: False falls back to fixed semaphore
    aimd_floor: int = 1  # Minimum concurrency (>= 1 to prevent deadlock)
    aimd_multiplicative_decrease: float = field(
        default_factory=lambda: _env_float("ASANA_CONCURRENCY_AIMD_MULT_DECREASE", 0.4)
    )  # Sharper than the TCP-standard 0.5 so a storm is damped faster (ROOT-1a)
    aimd_additive_increase: float = 1.0  # +1 on success (TCP standard)
    # C-3: conservative cold-start window. The semaphore previously began at the
    # ceiling, so a fresh Lambda link blasted the full ceiling wide on its first
    # fan-out then halved -- self-inflicting the burst. Starting at a small window
    # (env: ASANA_CONCURRENCY_AIMD_START_WINDOW) ramps UP additively only when the
    # API tolerates it, never blasting first. 0 / unset => start at floor-safe min.
    aimd_start_window: int = field(
        default_factory=lambda: _env_int("ASANA_CONCURRENCY_AIMD_START_WINDOW", 4)
    )
    aimd_grace_period_seconds: float = 5.0  # Suppress increases after decrease
    aimd_increase_interval_seconds: float = 2.0  # Min time between increases (FR-007)
    aimd_cooldown_trigger: int = 5  # Consecutive 429s for cooldown warning
    aimd_cooldown_duration_seconds: float = 30.0  # Cooldown duration (unused in v1)

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.read_limit <= 0:
            raise ConfigurationError(f"read_limit must be positive, got {self.read_limit}")
        if self.write_limit <= 0:
            raise ConfigurationError(f"write_limit must be positive, got {self.write_limit}")
        # AIMD-specific validation
        if self.aimd_floor < 1:
            raise ConfigurationError("aimd_floor must be >= 1")
        if self.aimd_floor > self.read_limit or self.aimd_floor > self.write_limit:
            raise ConfigurationError("aimd_floor must be <= read_limit and write_limit")
        if not 0.0 < self.aimd_multiplicative_decrease < 1.0:
            raise ConfigurationError("aimd_multiplicative_decrease must be in (0, 1)")
        # C-3: the cold-start window must sit within [floor, ceiling]. A start
        # above the ceiling would defeat the conservative ramp; below the floor
        # would deadlock. Clamp-by-rejection keeps the env override honest.
        if self.aimd_start_window < self.aimd_floor:
            raise ConfigurationError(
                f"aimd_start_window ({self.aimd_start_window}) must be >= aimd_floor "
                f"({self.aimd_floor})"
            )
        if self.aimd_start_window > self.read_limit:
            raise ConfigurationError(
                f"aimd_start_window ({self.aimd_start_window}) must be <= read_limit "
                f"({self.read_limit})"
            )


@dataclass(frozen=True)
class TimeoutConfig:
    """HTTP timeout configuration.

    Attributes:
        connect: Timeout for establishing connection
        read: Timeout for reading response
        write: Timeout for sending request body
        pool: Timeout for acquiring connection from pool
    """

    connect: float = 5.0
    read: float = 30.0
    write: float = 30.0
    pool: float = 10.0

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.connect <= 0:
            raise ConfigurationError(f"connect timeout must be positive, got {self.connect}")
        if self.read <= 0:
            raise ConfigurationError(f"read timeout must be positive, got {self.read}")
        if self.write <= 0:
            raise ConfigurationError(f"write timeout must be positive, got {self.write}")
        if self.pool <= 0:
            raise ConfigurationError(f"pool timeout must be positive, got {self.pool}")


@dataclass(frozen=True)
class ConnectionPoolConfig:
    """HTTP connection pool configuration."""

    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 30.0

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_connections <= 0:
            raise ConfigurationError(
                f"max_connections must be positive, got {self.max_connections}"
            )
        if self.max_keepalive_connections <= 0:
            raise ConfigurationError(
                f"max_keepalive_connections must be positive, got {self.max_keepalive_connections}"
            )
        if self.keepalive_expiry <= 0:
            raise ConfigurationError(
                f"keepalive_expiry must be positive, got {self.keepalive_expiry}"
            )


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Circuit breaker configuration.

    Per ADR-0048: Opt-in pattern for cascading failure prevention.

    Attributes:
        enabled: Whether circuit breaker is active (default False for backward compat)
        failure_threshold: Consecutive failures before opening circuit
        recovery_timeout: Seconds to wait before half-open probe
        half_open_max_calls: Successful probes required to close circuit
    """

    enabled: bool = False  # Opt-in for backward compatibility
    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: float = 60.0  # Seconds before half-open probe
    half_open_max_calls: int = 1  # Probes before closing

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.failure_threshold < 1:
            raise ConfigurationError(
                f"failure_threshold must be at least 1, got {self.failure_threshold}"
            )
        if self.recovery_timeout <= 0:
            raise ConfigurationError(
                f"recovery_timeout must be positive, got {self.recovery_timeout}"
            )
        if self.half_open_max_calls < 1:
            raise ConfigurationError(
                f"half_open_max_calls must be at least 1, got {self.half_open_max_calls}"
            )


@dataclass(frozen=True)
class S3LocationConfig:
    """Shared S3 location configuration primitive.

    Per B4 Config Consolidation: Extracted from duplicate S3 location fields
    that appeared in S3Config and other backend configs. Backend-specific
    configs compose from this primitive rather than redefining
    bucket/region/endpoint_url independently.

    Attributes:
        bucket: S3 bucket name.
        region: AWS region (default "us-east-1").
        endpoint_url: Custom endpoint URL for LocalStack or S3-compatible storage.
    """

    bucket: str = ""
    region: str = "us-east-1"
    endpoint_url: str | None = None

    @classmethod
    def from_env(cls) -> S3LocationConfig:
        """Create S3 location config from Pydantic Settings.

        Reads ASANA_CACHE_S3_BUCKET, ASANA_CACHE_S3_REGION, and
        ASANA_CACHE_S3_ENDPOINT_URL environment variables via settings.

        Returns:
            S3LocationConfig populated from environment.
        """
        from autom8_asana.settings import get_settings

        s3_settings = get_settings().s3
        return cls(
            bucket=s3_settings.bucket or "",
            region=s3_settings.region,
            endpoint_url=s3_settings.endpoint_url,
        )


@dataclass(frozen=True)
class DataFrameConfig:
    """Configuration for DataFrame operations.

    Per TDD-WATERMARK-CACHE/FR-CONFIG-001: Parallel fetch enabled by default.
    Per TDD-WATERMARK-CACHE/FR-CONFIG-005: Configurable max_concurrent_sections.

    Attributes:
        parallel_fetch_enabled: Enable parallel section fetch (default True).
            Per FR-CONFIG-001: Zero-configuration goal.
        max_concurrent_sections: Maximum concurrent section fetches (default 8).
            Must be between 1 and 20. Higher values may hit rate limits.
            Per FR-CONFIG-005: Configurable parallelism.
        cache_enabled: Enable automatic DataFrame caching (default True).
            Per FR-CONFIG-003: Cache integration enabled by default.

    Example:
        >>> config = DataFrameConfig(max_concurrent_sections=4)
        >>> client = AsanaClient(config=AsanaConfig(dataframe=config))

    Raises:
        ConfigurationError: If max_concurrent_sections is not in valid range.
    """

    parallel_fetch_enabled: bool = True
    max_concurrent_sections: int = 8
    cache_enabled: bool = True

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not 1 <= self.max_concurrent_sections <= 20:
            raise ConfigurationError(
                f"max_concurrent_sections must be 1-20, got {self.max_concurrent_sections}"
            )


# --- Large Section Pacing Configuration ---
# Per TDD-large-section-resilience / FR-004
#
# These control paced ingestion for sections with 100+ tasks.
# Module-level constants are sufficient; environment variable
# overrides can be added later if production tuning is needed.

PACE_PAGES_PER_PAUSE: int = 25
"""Number of pages to fetch before pausing. Must be >= 1."""

PACE_DELAY_SECONDS: float = 2.0
"""Seconds to sleep between page batches. Must be >= 0.0."""

CHECKPOINT_EVERY_N_PAGES: int = 50
"""Pages between checkpoint writes to S3. Must be >= 1.
Should be a multiple of PACE_PAGES_PER_PAUSE for predictable behavior."""


# --- Hierarchy Warming Pacing Configuration ---
# Per ADR-hierarchy-backpressure-hardening: Batch pacing for Phase 1
# immediate parent fetches to prevent 429 bursts from unbounded
# asyncio.gather() when parent count exceeds threshold.

HIERARCHY_PACING_THRESHOLD: int = 100
"""Number of parent GIDs above which batched pacing activates.
Sections with fewer parents use unbounded asyncio.gather() (no overhead)."""

HIERARCHY_BATCH_SIZE: int = 50
"""Number of parent GIDs to fetch per batch when pacing is active. Must be >= 1."""

HIERARCHY_BATCH_DELAY: float = 1.0
"""Seconds to sleep between hierarchy parent fetch batches. Must be >= 0.0."""


@dataclass
class CacheConfig:
    """Cache configuration with environment variable overrides.

    Per TDD-CACHE-INTEGRATION: Environment-aware provider selection.
    Per ADR-0123: Detection chain priority for provider selection.
    Per FR-TTL-001 through FR-TTL-007: Entity-type-specific TTL configuration.

    Environment Variables:
        ASANA_CACHE_ENABLED: Master enable/disable ("true"/"false")
        ASANA_CACHE_PROVIDER: Explicit provider selection ("memory", "redis", "tiered", "none")
        ASANA_CACHE_TTL_DEFAULT: Default TTL in seconds
        ASANA_ENVIRONMENT: Environment hint for auto-detection ("development", "production")

    Attributes:
        enabled: Whether caching is enabled (default True).
        provider: Explicit provider name ("memory", "redis", "tiered", "none").
            None means auto-detect based on environment.
        ttl: TTL configuration settings.
        overflow: Overflow threshold settings.
        freshness: Default freshness mode for cache reads.
        dataframe_caching: Whether DataFrame operations use caching.
        entity_ttls: Entity-type-specific TTL overrides in seconds.
            Default values per ADR-0126:
            - business: 3600 (1 hour) - rarely changes
            - contact: 900 (15 minutes)
            - unit: 900 (15 minutes)
            - offer: 180 (3 minutes) - frequently updated
            - process: 60 (1 minute) - pipeline state changes often
            - location: 3600 (1 hour) - rarely changes
            - hours: 3600 (1 hour) - rarely changes

    Example:
        >>> config = CacheConfig(enabled=True, provider="memory")
        >>> client = AsanaClient(config=AsanaConfig(cache=config))

        >>> # From environment variables
        >>> config = CacheConfig.from_env()

        >>> # Get entity-specific TTL
        >>> config.get_entity_ttl("business")  # Returns 3600
        >>> config.get_entity_ttl("process")   # Returns 60
        >>> config.get_entity_ttl("unknown")   # Returns default_ttl (300)
    """

    enabled: bool = True
    provider: str | None = None  # None = auto-detect
    dataframe_caching: bool = True
    entity_ttls: dict[str, int] = field(default_factory=lambda: DEFAULT_ENTITY_TTLS.copy())

    # These use factory functions to avoid circular imports at module load
    # The actual TTLSettings/OverflowSettings/FreshnessIntent are created lazily
    _ttl: TTLSettings | None = field(default=None, repr=False)
    _overflow: OverflowSettings | None = field(default=None, repr=False)
    _freshness: FreshnessIntent | None = field(default=None, repr=False)

    @property
    def ttl(self) -> TTLSettings:
        """TTL configuration settings (lazy-loaded)."""
        if self._ttl is None:
            from autom8_asana.cache.models.settings import TTLSettings

            object.__setattr__(self, "_ttl", TTLSettings())
        return self._ttl  # type: ignore[return-value]

    @ttl.setter
    def ttl(self, value: TTLSettings) -> None:
        """Set TTL configuration."""
        object.__setattr__(self, "_ttl", value)

    @property
    def overflow(self) -> OverflowSettings:
        """Overflow threshold settings (lazy-loaded)."""
        if self._overflow is None:
            from autom8_asana.cache.models.settings import OverflowSettings

            object.__setattr__(self, "_overflow", OverflowSettings())
        return self._overflow  # type: ignore[return-value]

    @overflow.setter
    def overflow(self, value: OverflowSettings) -> None:
        """Set overflow configuration."""
        object.__setattr__(self, "_overflow", value)

    @property
    def freshness(self) -> FreshnessIntent:
        """Default freshness mode for cache reads (lazy-loaded)."""
        if self._freshness is None:
            from autom8_asana.cache.models.freshness_unified import FreshnessIntent

            object.__setattr__(self, "_freshness", FreshnessIntent.EVENTUAL)
        return self._freshness  # type: ignore[return-value]

    @freshness.setter
    def freshness(self, value: FreshnessIntent) -> None:
        """Set freshness mode."""
        object.__setattr__(self, "_freshness", value)

    def get_entity_ttl(self, entity_type: str) -> int:
        """Get TTL for entity type with fallback to default.

        Per FR-TTL-001 through FR-TTL-007: Entity-type-specific TTL resolution.

        Priority:
        1. entity_ttls[entity_type] if configured
        2. ttl.default_ttl from TTLSettings
        3. 300s hardcoded fallback

        Args:
            entity_type: Entity type name (case-insensitive).
                Valid types: business, contact, unit, offer, process, location, hours.

        Returns:
            TTL in seconds for the entity type.

        Example:
            >>> config = CacheConfig()
            >>> config.get_entity_ttl("business")
            3600
            >>> config.get_entity_ttl("Process")  # Case-insensitive
            60
            >>> config.get_entity_ttl("unknown")  # Falls back to default
            300
        """
        # Normalize entity type to lowercase for lookup
        normalized = entity_type.lower()

        # Check entity_ttls first
        if normalized in self.entity_ttls:
            return self.entity_ttls[normalized]

        # Fall back to TTLSettings.default_ttl
        if self._ttl is not None:
            return self._ttl.default_ttl

        # Fall back to module-level DEFAULT_TTL
        return DEFAULT_TTL

    @classmethod
    def from_env(cls) -> CacheConfig:
        """Create configuration from environment variables.

        Per FR-ENV-001 through FR-ENV-005: Reads ASANA_CACHE_* environment
        variables via Pydantic Settings and creates a CacheConfig instance.

        Programmatic config always takes precedence when passed to AsanaClient.

        Environment Variables:
            ASANA_CACHE_ENABLED: "true"/"false" (default "true")
            ASANA_CACHE_PROVIDER: "memory", "redis", "tiered", "none" (default auto-detect)
            ASANA_CACHE_TTL_DEFAULT: Default TTL in seconds (default 300)

        Returns:
            CacheConfig populated from environment variables.

        Example:
            >>> import os
            >>> os.environ["ASANA_CACHE_ENABLED"] = "false"
            >>> config = CacheConfig.from_env()
            >>> config.enabled
            False
        """
        from autom8_asana.cache.models.settings import TTLSettings
        from autom8_asana.settings import CacheSettings as PydanticCacheSettings

        # Create fresh settings instance to read current env vars
        # (not the singleton, which may be stale in tests)
        cache_settings = PydanticCacheSettings()

        config = cls(
            enabled=cache_settings.enabled,
            provider=cache_settings.provider,
        )
        config._ttl = TTLSettings(default_ttl=cache_settings.ttl_default)
        return config


@dataclass
class AsanaConfig:
    """Main configuration for AsanaClient.

    Per TDD-AUTOMATION-LAYER: Includes automation configuration.
    Per TDD-CACHE-INTEGRATION: Includes cache configuration.
    Per TDD-WATERMARK-CACHE: Includes DataFrame configuration.

    Attributes:
        token_key: Environment variable name containing the Asana PAT.
            Defaults to "ASANA_PAT".

    Example:
        config = AsanaConfig(
            rate_limit=RateLimitConfig(max_requests=1000),
            retry=RetryConfig(max_retries=5),
            cache=CacheConfig(enabled=True, provider="memory"),
            dataframe=DataFrameConfig(max_concurrent_sections=4),
            automation=AutomationConfig(
                enabled=True,
                pipeline_stages={
                    "sales": PipelineStage(project_gid="123"),
                    "onboarding": PipelineStage(project_gid="456"),
                },
            ),
        )
        client = AsanaClient(config=config)
    """

    base_url: str = "https://app.asana.com/api/1.0"
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    concurrency: ConcurrencyConfig = field(default_factory=ConcurrencyConfig)
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    connection_pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    dataframe: DataFrameConfig = field(default_factory=DataFrameConfig)
    automation: AutomationConfig = field(default_factory=AutomationConfig)

    # Auth key names (used with AuthProvider.get_secret)
    token_key: str = "ASANA_PAT"  # noqa: S105 -- env var name for secret lookup, not a password


# --- Startup Validation ---

# Valid GID pattern (numeric string, typically 16+ digits)
GID_PATTERN = re.compile(r"^\d{10,}$")


def validate_project_env_vars(strict: bool = False) -> list[str]:
    """Validate ASANA_PROJECT_* environment variables.

    Per TDD-TECH-DEBT-REMEDIATION/FR-DET-007: Warn on invalid env vars.

    This function checks all ASANA_PROJECT_* environment variables for valid
    GID format (numeric string, 10+ digits). Empty values are allowed (use
    class defaults).

    Args:
        strict: If True, raise ConfigurationError on invalid vars.
                If False (default), warn only and return warnings list.

    Returns:
        List of warning messages for invalid variables.

    Raises:
        ConfigurationError: If strict=True and invalid vars found.

    Example:
        # Check at startup (warn only)
        warnings = validate_project_env_vars()
        if warnings:
            print(f"Found {len(warnings)} invalid ASANA_PROJECT_* vars")

        # Strict mode (fail on invalid)
        validate_project_env_vars(strict=True)  # Raises if invalid
    """
    warnings_list: list[str] = []

    for key, value in os.environ.items():
        if not key.startswith("ASANA_PROJECT_"):
            continue

        # Empty values are valid (use class default)
        if not value.strip():
            continue

        # Check GID format
        if not GID_PATTERN.match(value.strip()):
            msg = f"Invalid GID format for {key}: '{value}' (expected numeric string, 10+ digits)"
            warnings_list.append(msg)
            logger.warning(msg)

    if strict and warnings_list:
        raise ConfigurationError(f"Invalid ASANA_PROJECT_* environment variables: {warnings_list}")

    return warnings_list


# Auto-validate at import if ASANA_STRICT_CONFIG is set
# Uses Pydantic Settings for consistent configuration.
#
# Lazy resolution: get_settings() must NOT execute at module import time
# inside AWS Lambda. Settings includes secret-resolving fields wired to the
# AWS Parameters & Secrets Lambda Extension; resolving secrets at module
# import fails because the extension's HTTP listener is not guaranteed to
# be ready when the runtime imports user code (INCIDENT autom8y-asana-cache-warmer
# 2026-04-28). The strict-config validator now runs only when the
# ASANA_STRICT_CONFIG env var is set as a literal "1"/"true"/"yes" — checking
# the env var directly avoids invoking get_settings() at module load while
# preserving the opt-in fail-fast behavior for local strict-mode workflows.
_strict_flag = os.environ.get("ASANA_STRICT_CONFIG", "").strip().lower()
if _strict_flag in {"1", "true", "yes"}:
    validate_project_env_vars(strict=True)
