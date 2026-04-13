"""Tests for the core exception hierarchy.

Verifies the exception classes, inheritance, transient property,
factory methods, and error tuples defined in core/exceptions.py.
"""

from __future__ import annotations

import pytest

from autom8_asana.core.errors import (
    ALL_TRANSPORT_ERRORS,
    CACHE_TRANSIENT_ERRORS,
    REDIS_TRANSPORT_ERRORS,
    S3_TRANSPORT_ERRORS,
    Autom8Error,
    AutomationError,
    CacheConnectionError,
    CacheError,
    PipelineActionError,
    RedisTransportError,
    RuleExecutionError,
    S3TransportError,
    SeedingError,
    TransportError,
)

# ---------------------------------------------------------------------------
# Hierarchy tests
# ---------------------------------------------------------------------------


class TestHierarchy:
    """Verify the class inheritance tree."""

    def test_autom8_error_is_exception(self) -> None:
        assert issubclass(Autom8Error, Exception)

    def test_transport_error_is_autom8_error(self) -> None:
        assert issubclass(TransportError, Autom8Error)

    def test_s3_transport_error_is_transport_error(self) -> None:
        assert issubclass(S3TransportError, TransportError)

    def test_redis_transport_error_is_transport_error(self) -> None:
        assert issubclass(RedisTransportError, TransportError)

    def test_cache_error_is_autom8_error(self) -> None:
        assert issubclass(CacheError, Autom8Error)

    def test_cache_connection_error_is_cache_error(self) -> None:
        assert issubclass(CacheConnectionError, CacheError)

    def test_automation_error_is_autom8_error(self) -> None:
        assert issubclass(AutomationError, Autom8Error)

    def test_rule_execution_error_is_automation_error(self) -> None:
        assert issubclass(RuleExecutionError, AutomationError)

    def test_seeding_error_is_automation_error(self) -> None:
        assert issubclass(SeedingError, AutomationError)

    def test_pipeline_action_error_is_automation_error(self) -> None:
        assert issubclass(PipelineActionError, AutomationError)


# ---------------------------------------------------------------------------
# Autom8Error base
# ---------------------------------------------------------------------------


class TestAutom8Error:
    """Test the base Autom8Error class."""

    def test_message_attribute(self) -> None:
        err = Autom8Error("something broke")
        assert err.message == "something broke"
        assert str(err) == "something broke"

    def test_context_default_empty(self) -> None:
        err = Autom8Error("fail")
        assert err.context == {}

    def test_context_provided(self) -> None:
        err = Autom8Error("fail", context={"key": "val"})
        assert err.context == {"key": "val"}

    def test_cause_chaining(self) -> None:
        original = ValueError("original")
        err = Autom8Error("wrapped", cause=original)
        assert err.__cause__ is original

    def test_transient_default_false(self) -> None:
        err = Autom8Error("fail")
        assert err.transient is False


# ---------------------------------------------------------------------------
# TransportError
# ---------------------------------------------------------------------------


class TestTransportError:
    """Test the TransportError class."""

    def test_transient_default_true(self) -> None:
        err = TransportError("timeout")
        assert err.transient is True

    def test_backend_and_operation(self) -> None:
        err = TransportError("fail", backend="s3", operation="get")
        assert err.backend == "s3"
        assert err.operation == "get"
        assert err.context["backend"] == "s3"
        assert err.context["operation"] == "get"


# ---------------------------------------------------------------------------
# S3TransportError
# ---------------------------------------------------------------------------


class TestS3TransportError:
    """Test S3TransportError including transient classification."""

    def test_backend_is_s3(self) -> None:
        err = S3TransportError("fail", operation="get")
        assert err.backend == "s3"

    def test_transient_for_unknown_error(self) -> None:
        err = S3TransportError("fail")
        assert err.transient is True

    def test_permanent_for_nosuchkey(self) -> None:
        err = S3TransportError("fail", error_code="NoSuchKey")
        assert err.transient is False

    def test_permanent_for_access_denied(self) -> None:
        err = S3TransportError("fail", error_code="AccessDenied")
        assert err.transient is False

    def test_transient_for_service_error(self) -> None:
        err = S3TransportError("fail", error_code="InternalError")
        assert err.transient is True

    def test_context_includes_bucket_and_key(self) -> None:
        err = S3TransportError("fail", bucket="my-bucket", key="my-key", operation="get")
        assert err.context["bucket"] == "my-bucket"
        assert err.context["key"] == "my-key"

    def test_from_boto_error_basic(self) -> None:
        original = RuntimeError("connection reset")
        wrapped = S3TransportError.from_boto_error(original, operation="get", bucket="b", key="k")
        assert wrapped.__cause__ is original
        assert wrapped.operation == "get"
        assert wrapped.bucket == "b"
        assert wrapped.key == "k"
        assert wrapped.error_code is None

    def test_from_boto_error_extracts_error_code(self) -> None:
        """Simulate a botocore ClientError with a response dict."""

        class FakeClientError(Exception):
            def __init__(self) -> None:
                super().__init__("Access Denied")
                self.response = {"Error": {"Code": "AccessDenied"}}

        original = FakeClientError()
        wrapped = S3TransportError.from_boto_error(original, operation="get")
        assert wrapped.error_code == "AccessDenied"
        assert wrapped.transient is False


# ---------------------------------------------------------------------------
# RedisTransportError
# ---------------------------------------------------------------------------


class TestRedisTransportError:
    """Test RedisTransportError."""

    def test_backend_is_redis(self) -> None:
        err = RedisTransportError("fail", operation="get")
        assert err.backend == "redis"

    def test_transient_default_true(self) -> None:
        err = RedisTransportError("fail")
        assert err.transient is True

    def test_from_redis_error(self) -> None:
        original = ConnectionError("refused")
        wrapped = RedisTransportError.from_redis_error(original, operation="set")
        assert wrapped.__cause__ is original
        assert wrapped.operation == "set"


# ---------------------------------------------------------------------------
# CacheError
# ---------------------------------------------------------------------------


class TestCacheError:
    """Test CacheError and subclasses."""

    def test_transient_default_false(self) -> None:
        err = CacheError("corrupt data")
        assert err.transient is False

    def test_cache_key_in_context(self) -> None:
        err = CacheError("fail", cache_key="task:123")
        assert err.cache_key == "task:123"
        assert err.context["cache_key"] == "task:123"

    def test_cache_connection_error_is_transient(self) -> None:
        err = CacheConnectionError("backend down")
        assert err.transient is True


# ---------------------------------------------------------------------------
# AutomationError
# ---------------------------------------------------------------------------


class TestAutomationError:
    """Test AutomationError and subclasses."""

    def test_entity_gid_in_context(self) -> None:
        err = AutomationError("rule failed", entity_gid="12345")
        assert err.entity_gid == "12345"
        assert err.context["entity_gid"] == "12345"

    def test_rule_execution_error(self) -> None:
        err = RuleExecutionError("condition eval failed", entity_gid="1")
        assert isinstance(err, AutomationError)

    def test_seeding_error(self) -> None:
        err = SeedingError("seed failed")
        assert isinstance(err, AutomationError)

    def test_pipeline_action_error(self) -> None:
        err = PipelineActionError("move failed", entity_gid="2")
        assert isinstance(err, AutomationError)


# ---------------------------------------------------------------------------
# Error tuples
# ---------------------------------------------------------------------------


class TestErrorTuples:
    """Test error tuple composition."""

    def test_s3_transport_errors_includes_domain_type(self) -> None:
        assert S3TransportError in S3_TRANSPORT_ERRORS

    def test_redis_transport_errors_includes_domain_type(self) -> None:
        assert RedisTransportError in REDIS_TRANSPORT_ERRORS

    def test_all_transport_errors_union(self) -> None:
        assert S3TransportError in ALL_TRANSPORT_ERRORS
        assert RedisTransportError in ALL_TRANSPORT_ERRORS

    def test_cache_transient_errors_includes_connection(self) -> None:
        assert CacheConnectionError in CACHE_TRANSIENT_ERRORS

    def test_s3_transport_errors_catches_domain_exception(self) -> None:
        """Verify the tuple actually works in an except clause."""
        with pytest.raises(S3_TRANSPORT_ERRORS):
            raise S3TransportError("test")

    def test_redis_transport_errors_catches_domain_exception(self) -> None:
        with pytest.raises(REDIS_TRANSPORT_ERRORS):
            raise RedisTransportError("test")


# ---------------------------------------------------------------------------
# Catch behavior integration
# ---------------------------------------------------------------------------


class TestCatchBehavior:
    """Test that exceptions are catchable by parent types."""

    def test_catch_s3_as_transport(self) -> None:
        with pytest.raises(TransportError):
            raise S3TransportError("s3 fail")

    def test_catch_redis_as_transport(self) -> None:
        with pytest.raises(TransportError):
            raise RedisTransportError("redis fail")

    def test_catch_transport_as_autom8(self) -> None:
        with pytest.raises(Autom8Error):
            raise TransportError("transport fail")

    def test_catch_cache_as_autom8(self) -> None:
        with pytest.raises(Autom8Error):
            raise CacheError("cache fail")

    def test_catch_automation_as_autom8(self) -> None:
        with pytest.raises(Autom8Error):
            raise RuleExecutionError("rule fail")
