# TDD: Exception Hierarchy

**Status**: Draft
**Author**: Architect (Claude)
**Date**: 2026-02-04
**Sprint**: S1 (Architectural Opportunities)
**Task**: S1-001

---

## 1. Overview

### 1.1 Problem Statement

The codebase contains 229 `except Exception` blocks across 70 files. The audit (spike-S0-002) found that ~195 of these can be narrowed to specific exception types, while ~34 are intentional safety nets at system boundaries. The current exception hierarchy covers Asana API errors (`AsanaError`) and DataFrame operations (`DataFrameError`) but has no domain abstraction for cache, transport, or automation failures. This forces catch sites to import vendor exceptions directly (`botocore.exceptions.BotoCoreError`, `redis.RedisError`) or use broad `except Exception` blocks.

### 1.2 Goals

1. Provide domain-specific base types that wrap vendor exceptions at backend boundaries.
2. Support the transient/permanent distinction for retry and degraded-mode decisions.
3. Integrate with existing `DegradedModeMixin` and `RetryableErrorMixin` patterns.
4. Define a migration pattern for narrowing broad catches incrementally.
5. Establish the `# BROAD-CATCH` annotation convention for intentional broad catches.

### 1.3 Non-Goals

- Modifying the existing `AsanaError` or `DataFrameError` hierarchies.
- Implementing the narrowing of catch sites (that is S1-002 through S1-004).
- Adding structured logging or observability changes beyond what the exceptions themselves carry.

### 1.4 Constraints

- Must not break existing behavior. Narrowing catches is behavior-preserving.
- Must be implementable incrementally (cache subsystem first, then transport, then automation).
- Python 3.11+ (per `pyproject.toml`). `asyncio.CancelledError` is `BaseException`, not `Exception`, so it is not affected.

---

## 2. Module Location

### Decision: `src/autom8_asana/core/exceptions.py`

New exception classes live in `core/exceptions.py`. This module is the canonical home for cross-cutting exception types that do not belong to a single subsystem.

**Rationale**: The `core/` package already exists (`core/schema.py`, `core/entity_types.py`, `core/logging.py`) and contains foundational utilities. Placing exceptions here avoids circular imports between `cache/`, `dataframes/`, and `automation/` packages. The existing `exceptions.py` at the package root (`src/autom8_asana/exceptions.py`) is tightly coupled to Asana API HTTP semantics and should remain focused on that domain.

**Re-exports**: `core/exceptions.py` will be importable as:
```python
from autom8_asana.core.exceptions import CacheError, TransportError
```

The package root `__init__.py` should NOT re-export these. They are internal infrastructure, not part of the public SDK surface.

**Existing modules stay untouched**:
- `src/autom8_asana/exceptions.py` -- AsanaError hierarchy (API domain)
- `src/autom8_asana/dataframes/exceptions.py` -- DataFrameError hierarchy (dataframe domain)
- `src/autom8_asana/cache/errors.py` -- DegradedModeMixin, error classification functions
- `src/autom8_asana/patterns/error_classification.py` -- RetryableErrorMixin

---

## 3. Exception Hierarchy

### 3.1 Class Tree

```
Exception
|
+-- Autom8Error (NEW -- common base for all autom8_asana domain exceptions)
|   |
|   +-- TransportError (NEW -- base for all I/O transport failures)
|   |   +-- S3TransportError (NEW -- wraps botocore.exceptions.*)
|   |   +-- RedisTransportError (NEW -- wraps redis.RedisError)
|   |
|   +-- CacheError (NEW -- base for cache subsystem semantic errors)
|   |   +-- CacheReadError (NEW)
|   |   +-- CacheWriteError (NEW)
|   |   +-- CacheConnectionError (NEW)
|   |
|   +-- AutomationError (NEW -- base for automation subsystem)
|       +-- RuleExecutionError (NEW)
|       +-- SeedingError (NEW)
|       +-- PipelineActionError (NEW)
|
+-- AsanaError (EXISTING -- unchanged, API domain)
|   +-- AuthenticationError, ForbiddenError, NotFoundError, ...
|   +-- HydrationError, ResolutionError, ...
|   +-- InsightsError, ...
|
+-- DataFrameError (EXISTING -- unchanged, dataframe domain)
    +-- SchemaNotFoundError, ExtractionError, TypeCoercionError, ...
```

### 3.2 Design Decision: Autom8Error as Common Base

`Autom8Error` is a new common base that `TransportError`, `CacheError`, and `AutomationError` inherit from. It does NOT become the base of `AsanaError` or `DataFrameError` -- those are established hierarchies with their own constructors, and re-parenting them would be a breaking change for no benefit.

`Autom8Error` provides:
- A `context` dict for structured metadata (backend name, operation, key, etc.)
- A `transient` property indicating whether the error is retryable.
- Standard `__cause__` chaining for wrapped vendor exceptions.

### 3.3 Class Definitions

```python
"""Cross-cutting exception hierarchy for autom8_asana infrastructure.

Module: src/autom8_asana/core/exceptions.py

Provides domain-specific exception types for transport, cache, and
automation subsystems. These exceptions wrap vendor-specific errors
at backend boundaries so upstream code never imports botocore or redis.
"""

from __future__ import annotations

from typing import Any


class Autom8Error(Exception):
    """Base exception for autom8_asana infrastructure errors.

    All new domain exceptions inherit from this class. Provides
    structured context and transient/permanent classification.

    Attributes:
        message: Human-readable error description.
        context: Structured metadata for logging and diagnostics.
    """

    transient: bool = False  # Override in subclasses

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}
        if cause is not None:
            self.__cause__ = cause


# ---------------------------------------------------------------------------
# Transport layer
# ---------------------------------------------------------------------------

class TransportError(Autom8Error):
    """Base exception for I/O transport failures.

    Wraps vendor-specific exceptions from boto3, redis, etc. at the
    backend boundary. Upstream code catches TransportError instead
    of importing vendor types.
    """

    transient: bool = True  # Transport errors are transient by default

    def __init__(
        self,
        message: str,
        *,
        backend: str = "unknown",
        operation: str = "unknown",
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        ctx = {"backend": backend, "operation": operation}
        if context:
            ctx.update(context)
        super().__init__(message, context=ctx, cause=cause)
        self.backend = backend
        self.operation = operation


class S3TransportError(TransportError):
    """S3/boto3 transport failure.

    Wraps botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError,
    and related S3 I/O errors.

    Attributes:
        error_code: AWS error code (e.g., 'NoSuchKey', 'AccessDenied') if available.
        bucket: S3 bucket name if available.
        key: S3 object key if available.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        bucket: str | None = None,
        key: str | None = None,
        operation: str = "unknown",
        cause: Exception | None = None,
    ) -> None:
        ctx: dict[str, Any] = {}
        if error_code:
            ctx["error_code"] = error_code
        if bucket:
            ctx["bucket"] = bucket
        if key:
            ctx["key"] = key
        super().__init__(
            message,
            backend="s3",
            operation=operation,
            context=ctx,
            cause=cause,
        )
        self.error_code = error_code
        self.bucket = bucket
        self.key = key

    @property
    def transient(self) -> bool:  # type: ignore[override]
        """S3 errors are transient unless they are client errors (4xx)."""
        permanent_codes = {
            "NoSuchKey", "NoSuchBucket", "AccessDenied",
            "InvalidAccessKeyId", "SignatureDoesNotMatch",
            "AllAccessDisabled", "InvalidBucketName",
        }
        if self.error_code in permanent_codes:
            return False
        return True

    @classmethod
    def from_boto_error(
        cls,
        error: Exception,
        *,
        operation: str = "unknown",
        bucket: str | None = None,
        key: str | None = None,
    ) -> S3TransportError:
        """Factory: create from a botocore exception.

        Extracts error_code from ClientError.response if available.
        """
        error_code = None
        if hasattr(error, "response"):
            error_code = error.response.get("Error", {}).get("Code")
        return cls(
            str(error),
            error_code=error_code,
            bucket=bucket,
            key=key,
            operation=operation,
            cause=error,
        )


class RedisTransportError(TransportError):
    """Redis transport failure.

    Wraps redis.RedisError and its subclasses.
    """

    def __init__(
        self,
        message: str,
        *,
        operation: str = "unknown",
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            message,
            backend="redis",
            operation=operation,
            cause=cause,
        )

    @classmethod
    def from_redis_error(
        cls,
        error: Exception,
        *,
        operation: str = "unknown",
    ) -> RedisTransportError:
        """Factory: create from a redis exception."""
        return cls(str(error), operation=operation, cause=error)


# ---------------------------------------------------------------------------
# Cache layer
# ---------------------------------------------------------------------------

class CacheError(Autom8Error):
    """Base exception for cache subsystem semantic errors.

    Raised when a cache operation fails for reasons beyond raw transport
    (e.g., serialization failure, key format error). Transport failures
    within cache backends are raised as TransportError subclasses; CacheError
    covers the semantic layer above transport.
    """

    transient: bool = False  # Cache semantic errors are permanent by default

    def __init__(
        self,
        message: str,
        *,
        cache_key: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        ctx: dict[str, Any] = {}
        if cache_key:
            ctx["cache_key"] = cache_key
        if context:
            ctx.update(context)
        super().__init__(message, context=ctx, cause=cause)
        self.cache_key = cache_key


class CacheReadError(CacheError):
    """Cache read operation failed (deserialization, corrupt data)."""

    pass


class CacheWriteError(CacheError):
    """Cache write operation failed (serialization, quota)."""

    pass


class CacheConnectionError(CacheError):
    """Cache backend is unavailable (used by degraded-mode logic)."""

    transient: bool = True


# ---------------------------------------------------------------------------
# Automation layer
# ---------------------------------------------------------------------------

class AutomationError(Autom8Error):
    """Base exception for automation subsystem errors.

    Covers pipeline execution, seeding, and rule evaluation.
    """

    def __init__(
        self,
        message: str,
        *,
        entity_gid: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        ctx: dict[str, Any] = {}
        if entity_gid:
            ctx["entity_gid"] = entity_gid
        if context:
            ctx.update(context)
        super().__init__(message, context=ctx, cause=cause)
        self.entity_gid = entity_gid


class RuleExecutionError(AutomationError):
    """A single automation rule failed during evaluation."""

    pass


class SeedingError(AutomationError):
    """Seeding operation failed."""

    pass


class PipelineActionError(AutomationError):
    """A pipeline action (move, assign, comment, etc.) failed."""

    pass
```

---

## 4. Wrapping Strategy

### 4.1 Principle: Wrap at the Backend Boundary

Vendor exceptions are converted to domain exceptions at the lowest point where vendor code is called -- the backend modules themselves. This means:

- `cache/backends/s3.py` wraps `botocore.exceptions.*` into `S3TransportError`
- `cache/backends/redis.py` wraps `redis.RedisError` into `RedisTransportError`
- `dataframes/persistence.py` wraps `botocore.exceptions.*` into `S3TransportError`
- `dataframes/async_s3.py` wraps `botocore.exceptions.*` into `S3TransportError`

All upstream code (tiered cache, builders, clients) catches the domain type, never the vendor type.

### 4.2 Wrapping Pattern

```python
# BEFORE (current state in cache/backends/s3.py)
def get(self, key: str) -> bytes | None:
    try:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()
    except Exception as e:
        logger.warning("s3_get_failed", extra={"key": key, "error": str(e)})
        self.enter_degraded_mode(f"GET failed: {e}")
        return None

# AFTER (with wrapping)
from autom8_asana.core.exceptions import S3TransportError

# Module-level constant for catch blocks (see Section 5)
_S3_ERRORS: tuple[type[Exception], ...] = ()
try:
    from botocore.exceptions import BotoCoreError, ClientError
    _S3_ERRORS = (BotoCoreError, ClientError)
except ImportError:
    pass

def get(self, key: str) -> bytes | None:
    try:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()
    except _S3_ERRORS as e:
        wrapped = S3TransportError.from_boto_error(
            e, operation="get", bucket=self._bucket, key=key,
        )
        logger.warning(
            "s3_get_failed",
            extra={"key": key, "error": str(e), **wrapped.context},
        )
        self.enter_degraded_mode(f"GET failed: {e}")
        return None
    except (json.JSONDecodeError, gzip.BadGzipFile) as e:
        # Data corruption -- permanent, not transport
        raise CacheReadError(
            f"Corrupt data for key {key}: {e}",
            cache_key=key,
            cause=e,
        ) from e
```

### 4.3 When NOT to Wrap

Do not wrap exceptions that are already domain-typed. For example:
- `AsanaError` subclasses from API calls -- these are already specific.
- `DataFrameError` subclasses from polars operations -- these are already specific.
- Built-in Python exceptions (`ValueError`, `KeyError`, `TypeError`) used for input validation -- these should be caught specifically, not wrapped.

### 4.4 The Two-Tier Catch Pattern

After wrapping is in place at the backend boundary, upstream code uses a two-tier pattern:

```python
# Tier 1: Backend module (wraps vendor exceptions)
# cache/backends/s3.py -- catches botocore, produces S3TransportError

# Tier 2: Consumer module (catches domain exceptions)
# cache/tiered.py -- catches TransportError, CacheError
def get(self, key: str) -> bytes | None:
    try:
        return self._cold_tier.get(key)
    except TransportError as e:
        logger.warning("cold_tier_get_failed", extra=e.context)
        return None
```

---

## 5. Error Tuples

### 5.1 Purpose

Error tuples provide convenient catch blocks for the transitional period when backend boundaries are being incrementally wrapped. They also serve as documentation of which vendor exceptions each subsystem produces.

### 5.2 Location: `core/exceptions.py` (bottom of file)

```python
# ---------------------------------------------------------------------------
# Error tuples for catch-site convenience
# ---------------------------------------------------------------------------
# These are used during the migration period while backends are being
# wrapped. Once all backends wrap at the boundary, upstream code catches
# TransportError/CacheError instead.

# S3/boto3 errors (import-safe)
S3_TRANSPORT_ERRORS: tuple[type[Exception], ...] = (S3TransportError,)
try:
    from botocore.exceptions import BotoCoreError, ClientError
    S3_TRANSPORT_ERRORS = (S3TransportError, BotoCoreError, ClientError)
except ImportError:
    pass

# Redis errors (import-safe)
REDIS_TRANSPORT_ERRORS: tuple[type[Exception], ...] = (RedisTransportError,)
try:
    from redis import RedisError
    REDIS_TRANSPORT_ERRORS = (RedisTransportError, RedisError)
except ImportError:
    pass

# All transport errors (union of S3 + Redis)
ALL_TRANSPORT_ERRORS: tuple[type[Exception], ...] = (
    S3_TRANSPORT_ERRORS + REDIS_TRANSPORT_ERRORS
)

# Cache-layer errors (transport + semantic)
CACHE_TRANSIENT_ERRORS: tuple[type[Exception], ...] = (
    ALL_TRANSPORT_ERRORS + (CacheConnectionError,)
)

# Serialization errors (permanent, not retryable)
SERIALIZATION_ERRORS: tuple[type[Exception], ...] = (
    CacheReadError,
    CacheWriteError,
)
```

### 5.3 Usage

```python
from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS

def get_from_cache(key: str) -> dict | None:
    try:
        return self._backend.get(key)
    except CACHE_TRANSIENT_ERRORS as e:
        logger.warning("cache_miss_transient", extra={"key": key})
        return None
```

### 5.4 Migration Path for Error Tuples

The error tuples are a transitional mechanism. The end state is:

| Phase | Catch Pattern | Example |
|-------|--------------|---------|
| **Current** | `except Exception as e` | Catches everything |
| **Phase 1 (tuples)** | `except CACHE_TRANSIENT_ERRORS as e` | Catches domain + vendor types |
| **Phase 2 (wrapped)** | `except TransportError as e` | Catches only domain types |

Phase 1 can be deployed immediately without waiting for all backends to wrap. Phase 2 requires the wrapping work in the backend modules to be complete.

---

## 6. Migration Pattern

### 6.1 The Three Most Common Catch Patterns

Based on the audit, these three patterns account for approximately 85% of all narrowable catch sites.

#### Pattern A: Cache Backend Operation (S3/Redis) -- ~70 sites

**Before**:
```python
# cache/backends/s3.py, line 438
try:
    self._client.put_object(
        Bucket=self._config.bucket,
        Key=full_key,
        Body=compressed_data,
    )
    return True
except Exception as e:
    logger.warning(
        "s3_set_failed",
        extra={"key": key, "error": str(e), "error_type": type(e).__name__},
    )
    self.enter_degraded_mode(f"SET failed: {e}")
    return False
```

**After (Phase 1 -- narrow to vendor types)**:
```python
try:
    self._client.put_object(
        Bucket=self._config.bucket,
        Key=full_key,
        Body=compressed_data,
    )
    return True
except (BotoCoreError, ClientError) as e:
    logger.warning(
        "s3_set_failed",
        extra={"key": key, "error": str(e), "error_type": type(e).__name__},
    )
    self.enter_degraded_mode(f"SET failed: {e}")
    return False
```

**After (Phase 2 -- wrap and raise domain type)**:
```python
try:
    self._client.put_object(
        Bucket=self._config.bucket,
        Key=full_key,
        Body=compressed_data,
    )
    return True
except (BotoCoreError, ClientError) as e:
    wrapped = S3TransportError.from_boto_error(
        e, operation="set", bucket=self._config.bucket, key=full_key,
    )
    logger.warning(
        "s3_set_failed",
        extra={"key": key, **wrapped.context},
    )
    self.enter_degraded_mode(f"SET failed: {e}")
    return False
```

Note: The backend methods that return defaults (like `return False` above) do not re-raise. They log the wrapped error for structured context but continue the degraded-mode pattern. The wrapping provides better diagnostics, not different control flow.

#### Pattern B: Cache Consumer (Tiered, Clients, Builders) -- ~45 sites

**Before**:
```python
# cache/tiered.py, line 214
try:
    result = self._cold_tier.get_versioned(key)
except Exception as e:
    logger.warning("cold_tier_get_failed", extra={"key": key, "error": str(e)})
    result = None
```

**After (Phase 1 -- narrow to vendor types via tuple)**:
```python
from autom8_asana.core.exceptions import S3_TRANSPORT_ERRORS

try:
    result = self._cold_tier.get_versioned(key)
except S3_TRANSPORT_ERRORS as e:
    logger.warning("cold_tier_get_failed", extra={"key": key, "error": str(e)})
    result = None
```

**After (Phase 2 -- catch domain type after backends wrap)**:
```python
from autom8_asana.core.exceptions import TransportError

try:
    result = self._cold_tier.get_versioned(key)
except TransportError as e:
    logger.warning("cold_tier_get_failed", extra={"key": key, **e.context})
    result = None
```

#### Pattern C: Mixed Catch (API + Cache + Data) -- ~25 sites

**Before**:
```python
# dataframes/builders/progressive.py, line 612
try:
    result = self._fetch_and_persist_section(section, project_gid)
except Exception as e:
    logger.warning("section_build_failed", extra={"section": section, "error": str(e)})
    result = None
```

**After (Phase 1 -- enumerate known types)**:
```python
from autom8_asana.exceptions import AsanaError
from autom8_asana.core.exceptions import S3_TRANSPORT_ERRORS
from autom8_asana.dataframes.exceptions import DataFrameError

try:
    result = self._fetch_and_persist_section(section, project_gid)
except (AsanaError, *S3_TRANSPORT_ERRORS, DataFrameError) as e:
    logger.warning("section_build_failed", extra={"section": section, "error": str(e)})
    result = None
```

Note: Python does not support `*` unpacking in `except` clauses. The actual syntax requires a pre-computed tuple:

```python
_SECTION_BUILD_ERRORS = (AsanaError, DataFrameError) + S3_TRANSPORT_ERRORS

try:
    result = self._fetch_and_persist_section(section, project_gid)
except _SECTION_BUILD_ERRORS as e:
    logger.warning("section_build_failed", extra={"section": section, "error": str(e)})
    result = None
```

### 6.2 Migration Safety Rule

Every narrowed catch must preserve existing behavior exactly:
1. Same return value on error (None, False, [], etc.)
2. Same logging (warning level, same log key)
3. Same degraded-mode transition (if applicable)
4. Same exception chaining (if re-raising)

The ONLY change is the `except` clause type list. If a catch site does anything beyond the pattern (e.g., conditional re-raise, state mutation), it requires individual review.

---

## 7. BROAD-CATCH Annotation Convention

### 7.1 Format

```python
except Exception as e:  # BROAD-CATCH: <category> -- <reason>
```

### 7.2 Categories

| Category | Description | Example Sites |
|----------|-------------|---------------|
| `boundary` | System boundary catch-all (Lambda, API, CLI) | Lambda handlers, API startup |
| `isolation` | Per-entity/per-rule loop isolation | pipeline.py:473, cache_warmer.py:634 |
| `hook` | Hook/callback isolation (must not fail caller) | events.py:190/215/269 |
| `metrics` | Metrics/observability (must not fail operation) | metrics.py:572, data/client.py:527 |
| `cleanup` | Resource cleanup (task cancel, lock release) | api/main.py:239, decorator.py:224 |
| `enrichment` | Catches for enrichment then re-raises | observability/decorators.py:88 |

### 7.3 Examples

```python
# Lambda entry point -- must return valid response
except Exception as e:  # BROAD-CATCH: boundary -- Lambda handler must return HTTP response
    logger.error("handler_failed", extra={"error": str(e)}, exc_info=True)
    return {"statusCode": 500, "body": "Internal error"}

# Per-entity isolation in warming loop
except Exception as e:  # BROAD-CATCH: isolation -- single entity failure must not abort batch
    logger.warning("entity_warm_failed", extra={"gid": gid, "error": str(e)})
    failures.append(gid)
    continue

# Hook dispatch
except Exception:  # BROAD-CATCH: hook -- post_save hooks must not fail the commit
    logger.debug("post_save_hook_failed", exc_info=True)
```

### 7.4 Audit Trail

The ~34 sites identified in the audit as "High risk / intentional" should all receive `BROAD-CATCH` annotations in Sprint 1 Phase 3. The annotation serves as:
1. Signal to ruff (via `noqa` pairing) that the broad catch is intentional.
2. Documentation for future developers on why the catch is broad.
3. Grep target for periodic review (`grep -r "BROAD-CATCH" src/`).

---

## 8. Integration with Existing Patterns

### 8.1 DegradedModeMixin (cache/errors.py)

`DegradedModeMixin` manages the `_degraded` flag and reconnect timing. It is agnostic to exception types -- it just needs `enter_degraded_mode(reason)` to be called when an error occurs.

**Integration**: No changes to `DegradedModeMixin`. The narrowed catch sites still call `enter_degraded_mode()` exactly as before. The only difference is that the `except` clause is narrower.

The existing `is_connection_error()`, `is_s3_not_found_error()`, and `is_s3_retryable_error()` functions in `cache/errors.py` remain as-is during Phase 1. In Phase 2, after wrapping:
- `is_s3_not_found_error(e)` can be replaced by `isinstance(e, S3TransportError) and e.error_code == "NoSuchKey"`
- `is_s3_retryable_error(e)` can be replaced by `isinstance(e, S3TransportError) and e.transient`
- `is_connection_error(e)` can be replaced by `isinstance(e, TransportError) and e.transient`

These replacements are optional and should happen only after the hierarchy is stable.

### 8.2 RetryableErrorMixin (patterns/error_classification.py)

`RetryableErrorMixin` provides `is_retryable`, `recovery_hint`, and `retry_after_seconds` properties based on HTTP status codes from `AsanaError`. It does not currently handle transport or cache errors.

**Integration**: `RetryableErrorMixin._extract_status_code()` can be extended to recognize `Autom8Error.transient` as a retryability signal. However, this is a Phase 2+ concern. For Sprint 1, the `transient` property on `TransportError` and `CacheError` serves the same purpose without modifying `RetryableErrorMixin`.

### 8.3 cache/errors.py CONNECTION_ERROR_TYPES

The existing `CONNECTION_ERROR_TYPES` tuple in `cache/errors.py` lists built-in Python exceptions:

```python
CONNECTION_ERROR_TYPES: tuple[type[Exception], ...] = (
    ConnectionError, TimeoutError, OSError,
)
```

**Integration**: After wrapping, `TransportError` can be added to this tuple. But since the wrapping happens at the boundary and upstream code catches `TransportError` directly, this tuple becomes less relevant. No changes needed in Sprint 1.

---

## 9. Linting Configuration

### 9.1 Ruff Rule for Broad Catches

Ruff rule `BLE001` (blind-except) flags `except Exception` blocks. Currently this rule is not enabled in the project.

**Proposed `pyproject.toml` change**:

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "BLE"]
ignore = [
    "E501",   # Line length handled by formatter
    "B904",   # raise-without-from-inside-except
    "B028",   # stacklevel in warnings
    "B007",   # unused loop variable
    "B905",   # zip-without-strict
]
```

### 9.2 Suppression for Intentional Broad Catches

Sites annotated with `# BROAD-CATCH` should also carry a `noqa` directive:

```python
except Exception as e:  # noqa: BLE001  # BROAD-CATCH: boundary -- Lambda handler
```

### 9.3 Rollout Strategy

1. Enable `BLE001` in `select` but add all ~34 intentional sites to a `per-file-ignores` allowlist OR use inline `noqa`.
2. Inline `noqa` is preferred because it is self-documenting alongside the `BROAD-CATCH` comment.
3. Any new `except Exception` without `noqa: BLE001` will fail CI, preventing regression.

### 9.4 Timing

Enable `BLE001` AFTER Sprint 1 catch-narrowing is complete. Enabling it before would produce ~195 lint errors that are already being addressed. The sequence is:
1. Sprint 1 Phase 1-2: Narrow catches.
2. Sprint 1 Phase 3: Annotate remaining broad catches with `# BROAD-CATCH` + `# noqa: BLE001`.
3. Sprint 1 final: Enable `BLE001` in `pyproject.toml`.

---

## 10. Sequence Diagram: Exception Flow Through Cache Stack

```
Client Code          Tiered Cache         S3 Backend          boto3/S3
    |                    |                    |                   |
    |-- get(key) ------->|                    |                   |
    |                    |-- get(key) -------->|                   |
    |                    |                    |-- get_object() --->|
    |                    |                    |                   |
    |                    |                    |<-- ClientError ----|
    |                    |                    |                   |
    |                    |                    | [wrap at boundary]
    |                    |                    | S3TransportError.from_boto_error(e)
    |                    |                    | enter_degraded_mode()
    |                    |                    |                   |
    |                    |<-- return None -----|                   |
    |                    |                    |                   |
    |                    | [try hot tier or                       |
    |                    |  return None]                          |
    |                    |                    |                   |
    |<-- return None ----|                    |                   |
```

For backends that currently swallow errors and return defaults (the degraded-mode pattern), the wrapping adds structured context to logs but does not change control flow. The wrapped exception is not re-raised -- it is used for diagnostics.

For backends that do re-raise (e.g., `CacheReadError` on corrupt data), the domain exception propagates up the call stack.

---

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Narrowed catch misses an exception type | Medium | High -- unhandled exception crashes request | Error tuples include both domain + vendor types during migration. Test with fault injection. |
| Circular import from `core/exceptions.py` | Low | Medium -- import failure at startup | `core/exceptions.py` has zero intra-project imports. Only stdlib types. |
| `BLE001` produces false positives | Low | Low -- developer friction | Use inline `noqa` with documented `BROAD-CATCH` comments. |
| Wrapping overhead in hot path | Low | Low -- exception construction is not hot path | Exceptions are raised on failure, not success. No measurable overhead. |
| Team unfamiliar with new hierarchy | Medium | Low -- learning curve | TDD documents the hierarchy. Migration is mechanical. |

---

## 12. Implementation Order

| Phase | Scope | Files | Catch Sites | Sprint Task |
|-------|-------|-------|-------------|-------------|
| **0** | Create `core/exceptions.py` module | 1 new file | 0 | S1-001 (this design) |
| **1** | Narrow cache backend catches to vendor types | `cache/backends/s3.py`, `cache/backends/redis.py` | 26 | S1-002 |
| **2** | Narrow cache consumer catches (using error tuples) | `cache/tiered.py`, `cache/unified.py`, `cache/staleness_coordinator.py`, `cache/freshness_coordinator.py`, `cache/coalescer.py`, `cache/autom8_adapter.py`, `cache/lightweight_checker.py`, `cache/upgrader.py`, `cache/hierarchy_warmer.py` | 24 | S1-002 |
| **3** | Narrow transport catches | `dataframes/persistence.py`, `dataframes/async_s3.py`, `dataframes/section_persistence.py`, `dataframes/watermark.py`, `dataframes/builders/freshness.py` | 26 | S1-003 |
| **4** | Narrow consumer catches (clients, builders, integration) | `clients/base.py`, `clients/stories.py`, `dataframes/builders/parallel_fetch.py`, `dataframes/builders/task_cache.py`, `dataframes/cache_integration.py`, `cache/dataframe/*` | 21 | S1-003 |
| **5** | Annotate broad catches | All ~34 intentional sites | 34 | S1-004 |
| **6** | Enable BLE001 linting | `pyproject.toml` | 0 | S1-004 |

Total Sprint 1 scope: 87 narrowed catches + 34 annotated broad catches = 121 sites addressed.

---

## 13. ADR References

### ADR: Use Domain Exception Wrapping Over Direct Vendor Catches

**Context**: The audit found that upstream code (tiered cache, builders, clients) directly catches `botocore.exceptions.BotoCoreError` and `redis.RedisError`. This creates tight coupling to vendor libraries and requires every catch site to import vendor-specific types.

**Decision**: Wrap vendor exceptions at the backend boundary into domain types (`S3TransportError`, `RedisTransportError`). Upstream code catches `TransportError`.

**Alternatives Considered**:
1. **Narrow to vendor types everywhere** (simplest): Replace `except Exception` with `except (BotoCoreError, ClientError)` at every site. Rejected because it spreads vendor coupling across 70+ files instead of isolating it to 4 backend modules.
2. **Single CacheError for everything** (most abstract): Wrap all cache failures into `CacheError` without distinguishing transport from semantic errors. Rejected because transport errors are transient (retry-worthy) while semantic errors (corrupt data) are permanent, and this distinction matters for degraded-mode and retry logic.
3. **Use the error tuples permanently** (pragmatic): Define tuples like `CACHE_TRANSIENT_ERRORS` and never wrap. Rejected as permanent solution because it still requires importing vendor types transitively, but accepted as a transitional mechanism during migration.

**Consequences**: Backend modules become the single point of vendor coupling. Upstream code is simpler and vendor-agnostic. Cost is ~4 backend modules need wrapping logic.

### ADR: Autom8Error Does NOT Become Base of AsanaError/DataFrameError

**Context**: It would be elegant to unify all exceptions under a single `Autom8Error` base. However, `AsanaError` has a `from_response()` factory, `status_code` attribute, and is used in `isinstance` checks throughout the codebase. `DataFrameError` has its own constructor signature with `context` dict.

**Decision**: `Autom8Error` is the base for NEW exception types only (Transport, Cache, Automation). Existing hierarchies remain unchanged.

**Alternatives Considered**:
1. **Re-parent AsanaError(Autom8Error)**: Rejected. Would be a breaking change for any code doing `isinstance(e, Exception)` branching, and provides no practical benefit since `AsanaError` and `TransportError` are caught at different layers.
2. **No common base at all**: Considered viable. Rejected because a common base allows future cross-cutting concerns (structured logging, correlation IDs) to be applied uniformly.

**Consequences**: The exception hierarchy has three independent roots under `Exception`: `AsanaError`, `DataFrameError`, and `Autom8Error`. This is acceptable because these domains have different semantics and are caught at different layers.

---

## 14. Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| Exception audit | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/spike-S0-002-exception-audit.md` | Read |
| Existing exceptions (API) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/exceptions.py` | Read |
| Existing exceptions (DataFrame) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/exceptions.py` | Read |
| DegradedModeMixin | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/errors.py` | Read |
| RetryableErrorMixin | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/patterns/error_classification.py` | Read |
| S3 backend (catch patterns) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py` | Read |
| Redis backend (catch patterns) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py` | Read |
| Ruff config | `/Users/tomtenuta/Code/autom8_asana/pyproject.toml` | Read |
| This TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-exception-hierarchy.md` | Written |
