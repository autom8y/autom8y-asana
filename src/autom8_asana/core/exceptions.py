"""Cross-cutting exception hierarchy for autom8_asana infrastructure.

Provides domain-specific exception types for transport, cache, and
automation subsystems. These exceptions wrap vendor-specific errors
at backend boundaries so upstream code never imports botocore or redis.

Module: src/autom8_asana/core/exceptions.py

Design reference: docs/design/TDD-exception-hierarchy.md
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
            "NoSuchKey",
            "NoSuchBucket",
            "AccessDenied",
            "InvalidAccessKeyId",
            "SignatureDoesNotMatch",
            "AllAccessDisabled",
            "InvalidBucketName",
        }
        return self.error_code not in permanent_codes

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


# ---------------------------------------------------------------------------
# Error tuples for catch-site convenience
# ---------------------------------------------------------------------------
# These are used during the migration period while backends are being
# wrapped. Once all backends wrap at the boundary, upstream code catches
# TransportError/CacheError instead.

# S3/boto3 errors (import-safe)
# Includes builtin network errors (ConnectionError, TimeoutError, OSError) that can
# surface before boto3 wraps them, plus all botocore/ClientError types.
S3_TRANSPORT_ERRORS: tuple[type[Exception], ...] = (
    S3TransportError,
    ConnectionError,
    TimeoutError,
    OSError,
)
try:
    from botocore.exceptions import BotoCoreError, ClientError

    S3_TRANSPORT_ERRORS = (
        S3TransportError,
        BotoCoreError,
        ClientError,
        ConnectionError,
        TimeoutError,
        OSError,
    )
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
CACHE_TRANSIENT_ERRORS: tuple[type[Exception], ...] = ALL_TRANSPORT_ERRORS + (
    CacheConnectionError,
)

# Asana API errors (import-safe)
# Used by automation/pipeline.py for catch-site convenience.
# Includes AsanaError from the SDK + builtin network errors.
ASANA_API_ERRORS: tuple[type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
)
try:
    from autom8_asana.exceptions import AsanaError

    ASANA_API_ERRORS = (AsanaError, ConnectionError, TimeoutError)
except ImportError:
    pass
