# TDD: autom8_asana SDK Alignment

**TDD ID**: TDD-SDK-ALIGNMENT
**Version**: 1.0
**Date**: 2026-02-05
**Author**: Architect
**Status**: DRAFT
**PRD**: PRD-SDK-ALIGNMENT (task-301)
**Task**: task-302

---

## 1. Overview

This document specifies the technical design for aligning autom8_asana with the autom8y SDK ecosystem across two implementation paths:

1. **Path 1: Settings Migration** -- Base class swap to `Autom8yBaseSettings` + `SecretStr` for credential fields
2. **Path 3: Observability** -- Domain-specific Prometheus metrics (ECS) + CloudWatch metrics (Lambda)

Path 2 (DataFrame Cache Disposition) is a documentation-only deliverable covered by a separate ADR (`ADR-DATAFRAME-CACHE-DISPOSITION.md`).

---

## 2. System Context

```
+-------------------+       +--------------------+       +------------------+
|  Environment Vars |------>|  Autom8yBaseSettings|------>|  Settings        |
|  (ASANA_*, REDIS_)|       |  _resolve_secret_uris      |  (singleton)     |
+-------------------+       +--------------------+       +--+-------+-------+
                                                            |       |
                                            +---------------+       +----------+
                                            |                                  |
                                   +--------v--------+             +-----------v---------+
                                   | EnvAuthProvider  |             | autom8_adapter.py   |
                                   | (.get_secret())  |             | (create_autom8_     |
                                   +---------+--------+             |  cache_provider())  |
                                             |                      +-----------+---------+
                                             |                                  |
                                     +-------v--------+              +---------v----------+
                                     | AsanaClient    |              | RedisConfig        |
                                     | (uses PAT str) |              | (uses password str)|
                                     +----------------+              +--------------------+
```

The settings layer sits at the top of the dependency chain. Downstream consumers expect raw `str` values, not `SecretStr` wrappers. The design principle: **`SecretStr` stays at the settings boundary; raw strings flow through domain code.**

---

## 3. Path 1: Settings Migration Design

### 3.1. Approach: Two-Stage Migration

**Stage 1 (Base Class Swap)** and **Stage 2 (SecretStr)** are implemented as a single PR but tested independently. The stages are logically separate because Stage 1 is pure infrastructure (zero behavioral change) while Stage 2 changes field types with downstream impact.

### 3.2. Stage 1: Base Class Swap

#### 3.2.1. Import Changes

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/settings.py`

Replace the import:

```python
# BEFORE
from pydantic_settings import BaseSettings, SettingsConfigDict

# AFTER
from autom8y_config import Autom8yBaseSettings
from pydantic_settings import SettingsConfigDict
```

Note: `SettingsConfigDict` is still imported from `pydantic_settings` because it is a type alias used in `model_config` declarations. `Autom8yBaseSettings` re-exports it but the explicit import from `pydantic_settings` is clearer.

#### 3.2.2. Class Hierarchy Changes

All 8 subsetting classes and the root `Settings` class change their base class:

| Class | Line | Change |
|-------|------|--------|
| `AsanaSettings` | 78 | `BaseSettings` -> `Autom8yBaseSettings` |
| `CacheSettings` | 111 | `BaseSettings` -> `Autom8yBaseSettings` |
| `RedisSettings` | 271 | `BaseSettings` -> `Autom8yBaseSettings` |
| `EnvironmentSettings` | 324 | `BaseSettings` -> `Autom8yBaseSettings` |
| `S3Settings` | 359 | `BaseSettings` -> `Autom8yBaseSettings` |
| `PacingSettings` | 391 | `BaseSettings` -> `Autom8yBaseSettings` |
| `S3RetrySettings` | 451 | `BaseSettings` -> `Autom8yBaseSettings` |
| `ProjectOverrideSettings` | 532 | `BaseSettings` -> `Autom8yBaseSettings` |
| `Settings` | 604 | `BaseSettings` -> `Autom8yBaseSettings` |

#### 3.2.3. model_config Merge Analysis

`Autom8yBaseSettings.model_config` sets:

```python
model_config = SettingsConfigDict(
    env_nested_delimiter="__",
    extra="ignore",
    validate_default=True,
)
```

Each subsetting class already sets `extra="ignore"` (redundant with parent, no conflict). The child's `env_prefix` takes precedence via Pydantic's config merge semantics. The parent adds two new behaviors:

| Config Key | Parent Value | Child Value | Merge Result | Impact |
|------------|-------------|-------------|-------------|--------|
| `env_nested_delimiter` | `"__"` | (unset) | `"__"` | Additive. No existing fields use `__` in names, so this is inert for current fields. |
| `extra` | `"ignore"` | `"ignore"` | `"ignore"` | Redundant. No change. |
| `validate_default` | `True` | (unset) | `True` | Additive. Pydantic validates default values. All current defaults are valid. |
| `env_prefix` | (unset) | Various | Various | Child wins. No conflict. |
| `case_sensitive` | (unset) | `False` | `False` | Child wins. No conflict. |

**Verdict**: No conflicts. The merge is safe for all 8 subsetting classes.

**Special case -- `ProjectOverrideSettings`**: This class has `model_config = SettingsConfigDict(extra="ignore")` with no `env_prefix`. After inheriting from `Autom8yBaseSettings`, it gains `env_nested_delimiter="__"` and `validate_default=True`. Neither affects its behavior because it has no env-loaded fields (all validation happens in the `model_validator`).

**Special case -- root `Settings`**: Has `model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)` with no `env_prefix`. After inheriting from `Autom8yBaseSettings`, it gains `env_nested_delimiter="__"` and `validate_default=True`. The `env_nested_delimiter` means environment variables like `ASANA__PAT` could theoretically set `Settings.asana.pat`, but since each subsetting class is instantiated independently via `default_factory`, this does not apply. The root `Settings` does not read env vars for its subsetting fields; it delegates to each subsetting's own env var loading.

#### 3.2.4. Validator Ordering

`Autom8yBaseSettings._resolve_secret_uris` is a `model_validator(mode="before")`. This runs **before** field validators and child model validators. The ordering for each class:

1. `Autom8yBaseSettings._resolve_secret_uris` (mode="before") -- resolves secret URIs in raw dict
2. Child field validators (mode="before") -- e.g., `CacheSettings.parse_ttl_with_fallback`, `RedisSettings.parse_ssl`
3. Child field validators (mode="after") -- standard field post-validation
4. Child model validators (mode="after") -- e.g., `ProjectOverrideSettings.validate_project_overrides`

This ordering is correct:
- `_resolve_secret_uris` converts `ssm://path` strings to resolved values before field validators see them
- Field validators receive already-resolved strings (or plain values if no URI scheme)
- The `ProjectOverrideSettings.validate_project_overrides` runs last (mode="after"), reading from `os.environ` directly, so it is unaffected

#### 3.2.5. Singleton Pattern Compatibility

The module-level singleton pattern (`_settings`, `get_settings()`, `reset_settings()`) is independent of the base class. No changes needed.

`Autom8yBaseSettings._secret_resolver` is a `ClassVar` shared across all instances. `reset_settings()` clears `_settings` but does not clear the resolver. For testing, add a call to `Autom8yBaseSettings.reset_resolver()` inside `reset_settings()`:

```python
def reset_settings() -> None:
    global _settings
    _settings = None
    Autom8yBaseSettings.reset_resolver()
```

This ensures test isolation when mocking secret resolution.

### 3.3. Stage 2: SecretStr Migration

#### 3.3.1. Field Type Changes

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/settings.py`

```python
# Add import
from pydantic import Field, SecretStr, field_validator, model_validator

# AsanaSettings.pat (line 100)
# BEFORE
pat: str | None = Field(default=None, description="Asana Personal Access Token")
# AFTER
pat: SecretStr | None = Field(default=None, description="Asana Personal Access Token")

# RedisSettings.password (line 302)
# BEFORE
password: str | None = Field(default=None, description="Redis password")
# AFTER
password: SecretStr | None = Field(default=None, description="Redis password")
```

#### 3.3.2. Downstream Fix: EnvAuthProvider

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/_defaults/auth.py`

Lines 57-63 must be updated. The `get_secret()` method returns `str`, so we must extract the raw value at this boundary:

```python
# BEFORE (lines 57-63)
if key == "ASANA_PAT" and settings.asana.pat:
    if not settings.asana.pat.strip():
        raise AuthenticationError(
            f"Environment variable '{key}' is empty. Provide a valid token value."
        )
    return settings.asana.pat

# AFTER
if key == "ASANA_PAT" and settings.asana.pat:
    pat_value = settings.asana.pat.get_secret_value()
    if not pat_value.strip():
        raise AuthenticationError(
            f"Environment variable '{key}' is empty. Provide a valid token value."
        )
    return pat_value
```

**Why this works**: `SecretStr.__bool__` returns `True` when the internal value is non-empty, so `settings.asana.pat` as a truthiness check still works. The `.get_secret_value()` call extracts the raw string for `.strip()` and return.

#### 3.3.3. Downstream Fix: autom8_adapter.py

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/autom8_adapter.py`

Line 144 passes `redis_settings.password` (now `SecretStr | None`) to `RedisConfig.password` (expects `str | None`). The fix extracts the raw value at the settings-to-config translation boundary:

```python
# BEFORE (line 144)
password = redis_password if redis_password is not None else redis_settings.password

# AFTER
password = redis_password if redis_password is not None else (
    redis_settings.password.get_secret_value() if redis_settings.password else None
)
```

**Why here**: This is the translation boundary between settings (SecretStr) and domain config (plain string). The function parameter `redis_password: str | None` remains `str | None` because callers providing explicit passwords pass plain strings. Only the settings fallback path needs unwrapping.

#### 3.3.4. No Other Downstream Consumers

A grep for `settings.asana.pat` and `settings.redis.password` (and variants) across the source tree shows only the two locations above. The `BotPATProvider` at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/auth/bot_pat.py` reads the PAT from environment directly via `os.environ.get("ASANA_PAT")`, not through settings, so it is unaffected by the SecretStr change.

#### 3.3.5. to_safe_dict() Behavior

After Stage 1 + Stage 2, calling `get_settings().to_safe_dict()` will return:

```python
{
    "asana": {"pat": "***REDACTED***", "workspace_gid": "...", ...},
    "redis": {"password": "***REDACTED***", "host": "...", ...},
    ...
}
```

This is the primary security win: safe logging/debugging output without credential leakage.

**Implementation note**: `Autom8yBaseSettings._redact_secrets()` checks `field_info.annotation` for `SecretStr` and `SecretStr | None`. The `pat: SecretStr | None` annotation uses `Union` origin with `SecretStr` in args, which the `_redact_secrets` method handles correctly (lines 122-128 of `base_settings.py`).

### 3.4. File-by-File Implementation Spec

| # | File | Changes | Risk |
|---|------|---------|------|
| 1 | `settings.py` | Replace `BaseSettings` import with `Autom8yBaseSettings`, change 9 class declarations, add `SecretStr` import, change `pat` and `password` types, add `reset_resolver()` to `reset_settings()` | LOW -- mechanical swap; model_config merge verified |
| 2 | `_defaults/auth.py` | Update lines 57-63 to use `.get_secret_value()` on `settings.asana.pat` | LOW -- isolated change, well-tested code path |
| 3 | `cache/integration/autom8_adapter.py` | Update line 144 to unwrap `redis_settings.password` via `.get_secret_value()` | LOW -- isolated change at translation boundary |

### 3.5. Backward Compatibility

| Concern | Assessment |
|---------|-----------|
| Existing env vars (ASANA_PAT, REDIS_PASSWORD) | No change. `Autom8yBaseSettings` loads from env vars identically to `BaseSettings`. |
| `ssm://` URIs in env vars | Supported after migration. `_resolve_secret_uris` resolves before validation. Zero code change -- infrastructure change only. |
| Lambda cold start | `SecretResolver.__init__` is cheap (no I/O). boto3 import is lazy (only on `ssm://` or `secretsmanager://` URIs). With env-var-only secrets, the overhead is one string prefix check per field value per subsetting class. |
| `env_nested_delimiter="__"` | Additive but inert for current fields. No existing env vars use `__` as a separator. |
| Test suite | Existing tests pass. Tests that assert `isinstance(settings.asana.pat, str)` will need updating to `isinstance(settings.asana.pat, SecretStr)`. |

---

## 4. Path 3: Observability Design

### 4.1. Dual-Strategy Architecture

```
+---------------------------------------------------+
|  ECS FastAPI Service                               |
|                                                    |
|  instrument_app() --> autom8y_http_* metrics       |
|  api/metrics.py   --> asana_* domain metrics       |
|  /metrics endpoint <-- prometheus_client.REGISTRY  |
|                    (serves BOTH SDK + domain)      |
+---------------------------------------------------+

+---------------------------------------------------+
|  Lambda Handlers                                   |
|                                                    |
|  cache_warmer.py  --> _emit_metric() -> CloudWatch |
|  cache_invalidate.py --> _emit_metric() -> CW      |
+---------------------------------------------------+
```

### 4.2. ECS Domain Metrics Module

**New file**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/metrics.py`

This module defines domain-specific Prometheus metrics using `prometheus_client` directly. Metrics are registered on the default `prometheus_client.REGISTRY` (the same registry that `instrument_app()` uses), so the existing `/metrics` endpoint serves them automatically with zero changes to `autom8y-telemetry`.

#### 4.2.1. Metric Definitions

```python
"""Domain-specific Prometheus metrics for autom8_asana.

Metrics are registered on the default prometheus_client.REGISTRY and
served alongside autom8y_http_* platform metrics via the /metrics endpoint
provided by instrument_app().

All metric recording is in-memory (fire-and-forget) with no synchronous I/O.
"""

from prometheus_client import Counter, Gauge, Histogram

# --- DataFrame Cache Metrics ---

DATAFRAME_BUILD_DURATION = Histogram(
    "asana_dataframe_build_duration_seconds",
    "Time to build a DataFrame from API data",
    labelnames=["entity_type"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

DATAFRAME_CACHE_OPS = Counter(
    "asana_dataframe_cache_operations_total",
    "DataFrame cache operations by tier and result",
    labelnames=["entity_type", "tier", "result"],
)

DATAFRAME_ROWS_CACHED = Gauge(
    "asana_dataframe_rows_cached",
    "Current row count in most recent cached DataFrame per entity type",
    labelnames=["entity_type"],
)

DATAFRAME_SWR_REFRESHES = Counter(
    "asana_dataframe_swr_refreshes_total",
    "Stale-while-revalidate background refresh attempts",
    labelnames=["entity_type", "result"],
)

DATAFRAME_CIRCUIT_BREAKER = Gauge(
    "asana_dataframe_circuit_breaker_state",
    "Circuit breaker state per project (0=closed, 1=open, 2=half_open)",
    labelnames=["project_gid"],
)

# --- Asana API Metrics ---
# These supplement the autom8y_http_* metrics from instrument_app() with
# domain-specific API call tracking at the Asana resource level.

ASANA_API_CALLS = Counter(
    "asana_api_calls_total",
    "Asana API calls by endpoint pattern and status",
    labelnames=["method", "path_pattern", "status_code"],
)

ASANA_API_DURATION = Histogram(
    "asana_api_call_duration_seconds",
    "Asana API call duration by endpoint pattern",
    labelnames=["method", "path_pattern"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
```

#### 4.2.2. Helper Functions

The module provides recording functions that domain code calls. These functions are fire-and-forget with no error propagation:

```python
def record_build_duration(entity_type: str, duration_seconds: float) -> None:
    """Record DataFrame build duration."""
    DATAFRAME_BUILD_DURATION.labels(entity_type=entity_type).observe(duration_seconds)


def record_cache_op(
    entity_type: str,
    tier: str,
    result: str,
) -> None:
    """Record a cache operation (hit/miss/error).

    Args:
        entity_type: Entity type (e.g., "unit", "offer").
        tier: Cache tier ("memory" or "s3").
        result: Operation result ("hit", "miss", or "error").
    """
    DATAFRAME_CACHE_OPS.labels(
        entity_type=entity_type,
        tier=tier,
        result=result,
    ).inc()


def record_rows_cached(entity_type: str, row_count: int) -> None:
    """Update the rows-cached gauge for an entity type."""
    DATAFRAME_ROWS_CACHED.labels(entity_type=entity_type).set(row_count)


def record_swr_refresh(entity_type: str, result: str) -> None:
    """Record an SWR refresh attempt (success/failure)."""
    DATAFRAME_SWR_REFRESHES.labels(entity_type=entity_type, result=result).inc()


def record_circuit_breaker_state(project_gid: str, state: int) -> None:
    """Update circuit breaker state gauge.

    Args:
        project_gid: Project GID.
        state: 0=closed, 1=open, 2=half_open.
    """
    DATAFRAME_CIRCUIT_BREAKER.labels(project_gid=project_gid).set(state)


def record_api_call(
    method: str,
    path_pattern: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """Record an Asana API call."""
    ASANA_API_CALLS.labels(
        method=method,
        path_pattern=path_pattern,
        status_code=str(status_code),
    ).inc()
    ASANA_API_DURATION.labels(
        method=method,
        path_pattern=path_pattern,
    ).observe(duration_seconds)
```

#### 4.2.3. Label Cardinality Control

The `project_gid` label on `DATAFRAME_CIRCUIT_BREAKER` is bounded by the number of active projects (typically 5-15 in production). This is safe for Prometheus.

The `path_pattern` label on `ASANA_API_CALLS` and `ASANA_API_DURATION` uses parameterized patterns (e.g., `/projects/{gid}/tasks`) rather than concrete paths with GIDs, keeping cardinality bounded. The transport layer should normalize paths before recording.

#### 4.2.4. Module Registration

Import `api/metrics.py` during app startup to ensure metrics are registered before the first Prometheus scrape. Add to `create_app()` in `main.py`:

```python
# In create_app(), after instrument_app() call:
import autom8_asana.api.metrics  # noqa: F401 - register domain metrics
```

This is a side-effect import that registers Prometheus metrics on the default registry. The metrics are then served by the `/metrics` endpoint that `instrument_app()` creates.

### 4.3. Integration Points -- ECS

The metrics recording functions are called from existing domain code. Each integration point is a one-line addition at an existing code path:

#### 4.3.1. DataFrameCache.get_async()

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/dataframe_cache.py`

After memory tier lookup (existing stats increment lines):

```python
# After memory hit
self._stats[entity_type]["memory_hits"] += 1
# ADD:
from autom8_asana.api.metrics import record_cache_op
record_cache_op(entity_type, "memory", "hit")

# After memory miss
self._stats[entity_type]["memory_misses"] += 1
# ADD:
record_cache_op(entity_type, "memory", "miss")

# After S3 hit
self._stats[entity_type]["s3_hits"] += 1
# ADD:
record_cache_op(entity_type, "s3", "hit")

# After S3 miss
self._stats[entity_type]["s3_misses"] += 1
# ADD:
record_cache_op(entity_type, "s3", "miss")
```

**Import strategy**: Use a module-level import with graceful degradation to avoid import failures in Lambda context (where `prometheus_client` may not be installed):

```python
try:
    from autom8_asana.api.metrics import record_cache_op, record_build_duration, record_rows_cached, record_swr_refresh
    _HAS_METRICS = True
except ImportError:
    _HAS_METRICS = False
```

Then guard all metric calls:

```python
if _HAS_METRICS:
    record_cache_op(entity_type, "memory", "hit")
```

This pattern ensures the DataFrameCache works in both ECS (with metrics) and Lambda (without prometheus_client).

#### 4.3.2. DataFrameCache.put_async()

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/dataframe_cache.py`

After successful write, record build duration and row count:

```python
# After successful progressive + memory tier write
if _HAS_METRICS:
    record_build_duration(entity_type, build_duration_seconds)
    record_rows_cached(entity_type, len(dataframe))
```

The `build_duration_seconds` should be measured using `time.monotonic()` at the caller (the build pipeline), not inside `put_async()` itself. The `put_async()` method receives the DataFrame after build is complete. The calling code (entity builders) should time the build and pass duration to a metrics recording call.

**Recommended approach**: Rather than passing duration through `put_async()`, add metric recording at the entity builder level where the build timing naturally lives. The builder calls `time.monotonic()` before and after building, then calls `record_build_duration()`.

#### 4.3.3. SWR Refresh Tracking

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/dataframe_cache.py`

In the SWR background refresh path (inside `_trigger_swr_refresh_async` or similar):

```python
# On SWR refresh success
if _HAS_METRICS:
    record_swr_refresh(entity_type, "success")

# On SWR refresh failure
if _HAS_METRICS:
    record_swr_refresh(entity_type, "failure")
```

### 4.4. Lambda Metrics Design -- cache_invalidate.py

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_invalidate.py`

#### 4.4.1. Add _emit_metric Infrastructure

Copy the `_emit_metric()` helper from `cache_warmer.py`. To avoid code duplication, extract the shared CloudWatch metric emission into a shared module:

**New file**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cloudwatch.py`

```python
"""Shared CloudWatch metric emission for Lambda handlers.

Provides a reusable _emit_metric() function used by both
cache_warmer.py and cache_invalidate.py.
"""

from __future__ import annotations

import os
from typing import Any

from autom8y_log import get_logger

logger = get_logger(__name__)

CLOUDWATCH_NAMESPACE = os.environ.get("CLOUDWATCH_NAMESPACE", "autom8/cache-warmer")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "staging")

_cloudwatch_client: Any = None


def _get_cloudwatch_client() -> Any:
    """Lazily initialize CloudWatch client."""
    global _cloudwatch_client
    if _cloudwatch_client is None:
        import boto3
        _cloudwatch_client = boto3.client("cloudwatch")
    return _cloudwatch_client


def emit_metric(
    metric_name: str,
    value: float,
    unit: str = "Count",
    dimensions: dict[str, str] | None = None,
    namespace: str | None = None,
) -> None:
    """Emit CloudWatch metric with graceful degradation.

    Args:
        metric_name: Name of the metric.
        value: Metric value.
        unit: CloudWatch unit (Count, Milliseconds, etc.).
        dimensions: Optional additional dimensions.
        namespace: Override namespace (defaults to CLOUDWATCH_NAMESPACE).
    """
    client = _get_cloudwatch_client()
    ns = namespace or CLOUDWATCH_NAMESPACE

    metric_dimensions = [
        {"Name": "environment", "Value": ENVIRONMENT},
    ]
    if dimensions:
        for dim_name, dim_value in dimensions.items():
            metric_dimensions.append({"Name": dim_name, "Value": dim_value})

    try:
        client.put_metric_data(
            Namespace=ns,
            MetricData=[{
                "MetricName": metric_name,
                "Value": value,
                "Unit": unit,
                "Dimensions": metric_dimensions,
            }],
        )
    except Exception as e:
        logger.warning(
            "metric_emit_error",
            extra={"metric": metric_name, "error": str(e)},
        )
```

**Migration note**: `cache_warmer.py` can be refactored to use `from autom8_asana.lambda_handlers.cloudwatch import emit_metric` instead of its own `_emit_metric`. This is a refactoring step, not a behavior change.

#### 4.4.2. Metric Emission Points in cache_invalidate.py

Add metric emission at the existing logging points:

```python
from autom8_asana.lambda_handlers.cloudwatch import emit_metric

# After successful task cache clear (line 132-134 area):
emit_metric(
    "InvalidateSuccess",
    1,
    dimensions={"type": "tasks"},
)
emit_metric(
    "KeysCleared",
    tasks_cleared["redis"],
    dimensions={"tier": "redis"},
)
emit_metric(
    "KeysCleared",
    tasks_cleared["s3"],
    dimensions={"tier": "s3"},
)

# After successful dataframe cache clear (line 130-131 area):
emit_metric(
    "InvalidateSuccess",
    1,
    dimensions={"type": "dataframes"},
)

# After failure (line 155-174 area):
emit_metric(
    "InvalidateFailure",
    1,
)

# Total duration (line 132 area, before return):
emit_metric(
    "InvalidateDuration",
    duration_ms,
    unit="Milliseconds",
)
```

### 4.5. File-by-File Implementation Spec -- Observability

| # | File | Changes | Risk |
|---|------|---------|------|
| 1 | `api/metrics.py` (NEW) | Define Prometheus metrics + helper functions | NONE -- new additive module |
| 2 | `api/main.py` | Add side-effect import of `api/metrics` in `create_app()` | LOW -- single import line |
| 3 | `cache/integration/dataframe_cache.py` | Add `_HAS_METRICS` guard + metric recording at cache hit/miss/SWR points | LOW -- guarded one-liners alongside existing stats tracking |
| 4 | `lambda_handlers/cloudwatch.py` (NEW) | Extract shared CloudWatch emission function | NONE -- new module, no behavior change to existing code |
| 5 | `lambda_handlers/cache_invalidate.py` | Add `emit_metric()` calls at success/failure/duration logging points | LOW -- fire-and-forget calls at existing log points |
| 6 | `lambda_handlers/cache_warmer.py` | (Optional refactor) Import from shared `cloudwatch.py` instead of local `_emit_metric` | LOW -- refactor only, no behavior change |

### 4.6. Dependency Notes

`prometheus_client` is already a transitive dependency of `autom8y-telemetry[fastapi]` (which is in `pyproject.toml` dependencies). No new dependency needed for ECS.

For Lambda handlers, `prometheus_client` is NOT needed. Lambda handlers use CloudWatch via boto3. The `_HAS_METRICS` guard in `dataframe_cache.py` handles the case where the cache module is imported in Lambda context.

---

## 5. Component Architecture

### 5.1. Settings Layer (After Migration)

```
                    Autom8yBaseSettings
                    (model_validator: _resolve_secret_uris)
                    (method: to_safe_dict())
                    (method: reset_resolver())
                           |
         +---------+-------+-------+---------+
         |         |       |       |         |
    AsanaSettings  CacheSettings  RedisSettings  ...
    (pat: SecretStr|None)         (password: SecretStr|None)
    (env_prefix: ASANA_)          (env_prefix: REDIS_)
         |         |       |       |         |
         +---------+-------+-------+---------+
                           |
                     Settings (root)
                     (default_factory composition)
                           |
                     get_settings() singleton
                           |
              +------------+------------+
              |                         |
    EnvAuthProvider           autom8_adapter.py
    (.get_secret_value()      (.get_secret_value()
     at boundary)              at boundary)
```

### 5.2. Observability Layer

```
    ECS FastAPI Service                         Lambda Handlers
    ==================                          ===============

    instrument_app()                            cache_warmer.py
         |                                           |
    autom8y_http_* metrics                      _emit_metric()
    (request duration, count, in-flight)             |
         |                                      CloudWatch
    api/metrics.py                              (WarmSuccess, WarmDuration, ...)
         |
    asana_* domain metrics                      cache_invalidate.py
    (build duration, cache ops, SWR, API)            |
         |                                      emit_metric()
    /metrics endpoint                                |
    (prometheus_client.REGISTRY)                CloudWatch
                                                (InvalidateSuccess, KeysCleared, ...)
```

---

## 6. Data Model Changes

### 6.1. Settings Field Type Changes

| Class | Field | Before | After |
|-------|-------|--------|-------|
| `AsanaSettings` | `pat` | `str \| None` | `SecretStr \| None` |
| `RedisSettings` | `password` | `str \| None` | `SecretStr \| None` |

No database schema changes. No API contract changes. No serialization format changes.

### 6.2. Prometheus Metric Schema

| Metric Name | Type | Labels | Buckets |
|-------------|------|--------|---------|
| `asana_dataframe_build_duration_seconds` | Histogram | entity_type | 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0 |
| `asana_dataframe_cache_operations_total` | Counter | entity_type, tier, result | N/A |
| `asana_dataframe_rows_cached` | Gauge | entity_type | N/A |
| `asana_dataframe_swr_refreshes_total` | Counter | entity_type, result | N/A |
| `asana_dataframe_circuit_breaker_state` | Gauge | project_gid | N/A |
| `asana_api_calls_total` | Counter | method, path_pattern, status_code | N/A |
| `asana_api_call_duration_seconds` | Histogram | method, path_pattern | 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0 |

### 6.3. CloudWatch Metric Schema (cache_invalidate.py)

| Metric Name | Unit | Dimensions |
|-------------|------|-----------|
| `InvalidateSuccess` | Count | environment, type (tasks/dataframes) |
| `InvalidateFailure` | Count | environment |
| `InvalidateDuration` | Milliseconds | environment |
| `KeysCleared` | Count | environment, tier (redis/s3) |

---

## 7. Key Flows

### 7.1. Settings Loading with Secret Resolution

```
Environment Variables             Autom8yBaseSettings              Domain Code
===================              ===================              ===========

ASANA_PAT="xoxp-123"    --->    _resolve_secret_uris()   --->    AsanaSettings(
                                 (string prefix check:             pat=SecretStr("xoxp-123")
                                  no ssm:// prefix,               )
                                  passthrough)

ASANA_PAT="ssm:///prod/pat" ->  _resolve_secret_uris()   --->    AsanaSettings(
                                 (detects ssm:// prefix,           pat=SecretStr("<resolved>")
                                  calls SecretResolver,            )
                                  returns resolved value)
```

### 7.2. EnvAuthProvider.get_secret("ASANA_PAT") After Migration

```
1. get_settings() -> Settings (cached singleton)
2. settings.asana.pat -> SecretStr("xoxp-123")  (truthy check: True)
3. settings.asana.pat.get_secret_value() -> "xoxp-123"
4. "xoxp-123".strip() -> "xoxp-123" (non-empty check)
5. return "xoxp-123"  (raw string to caller)
```

### 7.3. Redis Cache Provider Creation After Migration

```
1. get_settings() -> Settings (cached singleton)
2. sdk_settings.redis -> RedisSettings(password=SecretStr("redis-pass"))
3. redis_settings.password -> SecretStr("redis-pass")
4. redis_settings.password.get_secret_value() -> "redis-pass"
5. RedisConfig(password="redis-pass") -> plain string to Redis client
```

### 7.4. Prometheus Metric Flow (ECS)

```
1. DataFrameCache.get_async("proj-123", "unit")
2. Memory tier lookup -> miss
3. self._stats["unit"]["memory_misses"] += 1  (existing)
4. record_cache_op("unit", "memory", "miss")   (NEW)
   -> DATAFRAME_CACHE_OPS.labels(...).inc()    (in-memory counter)
5. S3 tier lookup -> hit
6. self._stats["unit"]["s3_hits"] += 1         (existing)
7. record_cache_op("unit", "s3", "hit")        (NEW)

... Later, Prometheus scrapes /metrics ...

8. GET /metrics
9. prometheus_client.generate_latest()
10. Response includes both:
    - autom8y_http_request_duration_seconds{...}  (SDK)
    - asana_dataframe_cache_operations_total{...}  (domain)
```

### 7.5. CloudWatch Metric Flow (Lambda cache_invalidate)

```
1. handler(event, context)
2. _invalidate_cache_async(clear_tasks=True)
3. cache.clear_all_tasks() -> {"redis": 500, "s3": 1200}
4. emit_metric("InvalidateSuccess", 1, dimensions={"type": "tasks"})
   -> boto3.put_metric_data(Namespace="autom8/cache-warmer", ...)
5. emit_metric("KeysCleared", 500, dimensions={"tier": "redis"})
6. emit_metric("KeysCleared", 1200, dimensions={"tier": "s3"})
7. emit_metric("InvalidateDuration", duration_ms, unit="Milliseconds")
8. Return response
```

---

## 8. Error Handling

### 8.1. SecretStr Unwrapping Errors

If `settings.asana.pat` is `SecretStr` but caller forgets `.get_secret_value()`, the result is:
- Passing `SecretStr` object where `str` is expected
- `str(secret_str)` returns `"**********"` (Pydantic's SecretStr.__str__ behavior)
- This would surface as an authentication failure ("invalid token") rather than a type error

**Mitigation**: The design ensures `.get_secret_value()` is called at exactly two boundaries (auth.py and autom8_adapter.py). Type checking (mypy strict mode) will catch additional misuse.

### 8.2. Secret Resolution Failures

If `ASANA_PAT=ssm:///prod/pat` and SSM is unreachable:
- `SecretResolver.resolve()` raises `SecretNotFoundError` or `SecretAccessDeniedError`
- This propagates as a startup failure (settings are loaded at `get_settings()` time)
- Lambda cold start will fail with a clear error message

**Mitigation**: Existing behavior -- if env vars are wrong, settings loading fails at startup. The error messages from `autom8y-config` are descriptive.

### 8.3. Metrics Recording Failures

All Prometheus metric operations are in-memory and cannot fail (the prometheus_client library handles internal errors gracefully). CloudWatch metric emission uses the existing `_emit_metric` pattern with broad exception catch and warning log. Neither path can affect request processing.

---

## 9. Security Considerations

### 9.1. Secret Redaction

After migration:
- `repr(settings.asana)` shows `pat=SecretStr('**********')` instead of `pat='xoxp-actual-token'`
- `settings.to_safe_dict()` shows `pat='***REDACTED***'`
- `model_dump()` returns `pat='**********'` (Pydantic SecretStr behavior)

This eliminates the risk of credential leakage in logs, error messages, and debug output.

### 9.2. SSM/SecretsManager Future Path

After Stage 1, the infrastructure team can change from:
```
ASANA_PAT=xoxp-12345
```
to:
```
ASANA_PAT=ssm:///prod/asana-pat
```
with zero code changes. The `_resolve_secret_uris` validator handles resolution transparently.

### 9.3. No New Attack Surface

The observability additions (Prometheus metrics, CloudWatch metrics) contain no PII or secrets. Metric labels use entity types and project GIDs (which are numeric identifiers, not sensitive data). The `/metrics` endpoint is already exposed by `instrument_app()`.

---

## 10. Performance Considerations

### 10.1. Lambda Cold Start Impact

| Component | Cost | Measurement Approach |
|-----------|------|---------------------|
| `Autom8yBaseSettings.__init_subclass__` | Negligible | No work done at class definition time |
| `SecretResolver.__init__()` | Negligible | Sets up empty cache dict |
| `_resolve_secret_uris` per-class | O(n) string prefix checks where n = field count | ~8 fields per subsetting class, 8 classes = ~64 checks |
| boto3 import (lazy) | NOT triggered with env-var-only secrets | Only triggered by `ssm://` or `secretsmanager://` prefix |

**Expected impact**: < 5ms additional cold start time. The PRD acceptance criterion is < 50ms delta (AC-1.7).

### 10.2. Prometheus Metric Recording

All Prometheus operations are in-memory counter/histogram increments. No I/O, no locks beyond the per-metric Lock (which is uncontended in practice). Expected overhead: < 1 microsecond per metric recording call.

### 10.3. Metric Cardinality

| Metric | Max Label Combinations | Assessment |
|--------|----------------------|------------|
| `asana_dataframe_cache_operations_total` | ~7 entity_types x 2 tiers x 3 results = 42 | Safe |
| `asana_dataframe_build_duration_seconds` | ~7 entity_types = 7 | Safe |
| `asana_dataframe_circuit_breaker_state` | ~15 project_gids = 15 | Safe |
| `asana_api_calls_total` | ~5 methods x ~20 path_patterns x ~10 status_codes = 1000 | Monitor; may need path_pattern bucketing |

---

## 11. Test Plan

### 11.1. Settings Migration Tests

| Test | Description | Type |
|------|-------------|------|
| `test_base_class_is_autom8y` | Verify all 9 classes inherit from `Autom8yBaseSettings` | Unit |
| `test_env_prefix_preserved` | Verify each class reads from correct env prefix after swap | Unit |
| `test_to_safe_dict_redacts_pat` | `get_settings().to_safe_dict()["asana"]["pat"] == "***REDACTED***"` | Unit |
| `test_to_safe_dict_redacts_password` | `get_settings().to_safe_dict()["redis"]["password"] == "***REDACTED***"` | Unit |
| `test_env_auth_provider_returns_str` | `EnvAuthProvider().get_secret("ASANA_PAT")` returns `str`, not `SecretStr` | Unit |
| `test_env_auth_provider_rejects_empty` | `EnvAuthProvider().get_secret("ASANA_PAT")` raises on whitespace-only value | Unit |
| `test_redis_adapter_passes_str` | `create_autom8_cache_provider()` creates `RedisConfig` with `str` password | Unit |
| `test_model_config_merge_per_class` | Each of 8 subsettings resolves correct env vars with parent config merged | Parameterized unit |
| `test_parse_ttl_with_fallback_still_works` | `CacheSettings.parse_ttl_with_fallback` field_validator works after base class swap | Unit |
| `test_parse_ssl_still_works` | `RedisSettings.parse_ssl` field_validator works after base class swap | Unit |
| `test_project_overrides_validator_fires` | `ProjectOverrideSettings.validate_project_overrides` model_validator works | Unit |
| `test_singleton_reset_clears_resolver` | `reset_settings()` clears both `_settings` and `SecretResolver` cache | Unit |
| `test_ssm_uri_resolution` | Setting `ASANA_PAT=ssm:///test/pat` triggers `SecretResolver` (mock) | Unit |
| `test_cold_start_budget` | Settings initialization completes in < 50ms with no SSM URIs | Benchmark |

### 11.2. Observability Tests

| Test | Description | Type |
|------|-------------|------|
| `test_metrics_module_registers_on_default_registry` | Import `api/metrics.py`, verify metric names in `prometheus_client.REGISTRY` | Unit |
| `test_record_cache_op_increments_counter` | `record_cache_op("unit", "memory", "hit")` increments the correct counter | Unit |
| `test_record_build_duration_observes_histogram` | `record_build_duration("unit", 1.5)` adds observation | Unit |
| `test_metrics_endpoint_serves_domain_metrics` | GET `/metrics` response includes `asana_dataframe_*` metrics | Integration |
| `test_cache_invalidate_emits_cloudwatch_metrics` | `handler({"clear_tasks": True}, mock_context)` calls `emit_metric` for success/duration/keys | Unit (mocked boto3) |
| `test_has_metrics_guard_in_dataframe_cache` | DataFrameCache works when `prometheus_client` is not importable | Unit |
| `test_emit_metric_graceful_degradation` | `emit_metric()` logs warning but does not raise on CloudWatch error | Unit |

---

## 12. Risks and Mitigations

| # | Risk | Probability | Impact | Mitigation |
|---|------|-------------|--------|------------|
| R1 | `model_config` merge breaks env var loading | Low | High | Parameterized test per class; Pydantic docs confirm child precedence |
| R2 | `SecretStr` propagation past boundary | Medium | High | Only 2 boundaries identified; mypy strict mode catches `str` vs `SecretStr` misuse |
| R3 | Lambda cold start regression | Low | Medium | Benchmark test with threshold; `_resolve_secret_uris` is string prefix check only |
| R4 | `prometheus_client` import fails in Lambda | Low | Low | `_HAS_METRICS` guard ensures graceful degradation |
| R5 | Metric label cardinality explosion on `path_pattern` | Low | Medium | Use parameterized patterns (`/projects/{gid}/tasks`), not concrete paths |
| R6 | `reset_settings()` does not clear resolver cache between tests | Medium | Medium | Add `Autom8yBaseSettings.reset_resolver()` call to `reset_settings()` |

---

## 13. ADR References

| ADR | Decision | Relevance |
|-----|----------|-----------|
| ADR-DATAFRAME-CACHE-DISPOSITION | DataFrame cache remains separate from SDK | Path 2 -- no code changes, documentation only |
| ADR-0064-checkpoint-persistence-strategy | Checkpoint uses S3 | Cache warmer Lambda context |
| ADR-VAULT-001 | Platform uses Secrets Manager | Future SSM/SM integration enabled by Stage 1 |

---

## 14. Implementation Order

```
Stage 1: Base Class Swap
  settings.py (import + 9 class declarations)
  |
Stage 2: SecretStr
  settings.py (2 field types)
  _defaults/auth.py (3 lines)
  cache/integration/autom8_adapter.py (1 line)
  |
Stage 3: Observability (parallel with Stage 1+2)
  api/metrics.py (NEW)
  api/main.py (1 import line)
  cache/integration/dataframe_cache.py (metric recording calls)
  lambda_handlers/cloudwatch.py (NEW)
  lambda_handlers/cache_invalidate.py (emit_metric calls)
```

Stages 1+2 and Stage 3 can be implemented as separate PRs since they have no code dependencies on each other.

---

## 15. Artifact Attestation

| # | Artifact | Absolute Path | Verified |
|---|----------|---------------|----------|
| 1 | autom8_asana settings.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/settings.py` | Read |
| 2 | autom8_asana _defaults/auth.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/_defaults/auth.py` | Read |
| 3 | autom8_asana autom8_adapter.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/autom8_adapter.py` | Read |
| 4 | autom8_asana config_translator.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/config_translator.py` | Read |
| 5 | autom8_asana dataframe_cache.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/dataframe_cache.py` | Read |
| 6 | autom8_asana cache_warmer.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_warmer.py` | Read |
| 7 | autom8_asana cache_invalidate.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_invalidate.py` | Read |
| 8 | autom8_asana api/main.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | Read |
| 9 | autom8_asana pyproject.toml | `/Users/tomtenuta/Code/autom8_asana/pyproject.toml` | Read |
| 10 | autom8y-config base_settings.py | `/Users/tomtenuta/Code/autom8y_platform/sdks/python/autom8y-config/src/autom8y_config/base_settings.py` | Read |
| 11 | autom8y-config __init__.py | `/Users/tomtenuta/Code/autom8y_platform/sdks/python/autom8y-config/src/autom8y_config/__init__.py` | Read |
| 12 | autom8y-telemetry instrument.py | `/Users/tomtenuta/Code/autom8y_platform/sdks/python/autom8y-telemetry/src/autom8y_telemetry/fastapi/instrument.py` | Read |
| 13 | autom8y-telemetry endpoint.py | `/Users/tomtenuta/Code/autom8y_platform/sdks/python/autom8y-telemetry/src/autom8y_telemetry/fastapi/endpoint.py` | Read |
| 14 | PRD-SDK-ALIGNMENT | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-SDK-ALIGNMENT.md` | Read |
| 15 | SDK Adoption Gap Inventory | `/Users/tomtenuta/Code/autom8y_platform/docs/requirements/SDK-ADOPTION-GAP-INVENTORY.md` | Read |
| 16 | Initiative Family Brief | `/Users/tomtenuta/Code/autom8y_platform/.claude/sessions/session-20260114-011615-d1d89188/INITIATIVE_FAMILY_BRIEF.md` | Read |
