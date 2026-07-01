"""Tests for BridgeWorkflowAction base class.

Per TDD sprint-3 Section 8, Phase 1: Base class tests covering
BridgeOutcome dataclass, validate_async, enumerate_async, execute_async,
and _build_result_metadata.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog

from autom8_asana.automation.workflows.base import (
    WorkflowItemError,
    WorkflowResult,
)
from autom8_asana.automation.workflows.bridge_base import (
    BridgeOutcome,
    BridgeWorkflowAction,
)
from autom8_asana.core.scope import EntityScope

# --- Concrete test subclass ---


class _TestBridge(BridgeWorkflowAction):
    """Minimal concrete bridge for testing base class behavior."""

    feature_flag_env_var = "TEST_BRIDGE_ENABLED"

    @property
    def workflow_id(self) -> str:  # type: ignore[override]
        return "test-bridge"

    async def enumerate_entities(
        self,
        scope: EntityScope,
    ) -> list[dict[str, Any]]:
        return [{"gid": "test-1", "name": "Test Entity"}]

    async def process_entity(
        self,
        entity: dict[str, Any],
        params: dict[str, Any],
    ) -> BridgeOutcome:
        return BridgeOutcome(gid=entity["gid"], status="succeeded")


def _make_test_bridge(
    *,
    data_client: Any | None = None,
) -> _TestBridge:
    """Build a _TestBridge with mock clients."""
    mock_asana = MagicMock()
    mock_attachments = MagicMock()
    dc = data_client if data_client is not None else MagicMock()
    if data_client is None:
        dc.is_healthy = AsyncMock()
    return _TestBridge(
        asana_client=mock_asana,
        data_client=dc,
        attachments_client=mock_attachments,
    )


def _capture_bridge_logs() -> Any:
    """structlog capture over the shared bridge_base module logger.

    Clears the BoundLoggerLazyProxy ``bind`` cache so ``capture_logs`` intercepts
    even when an earlier test materialized the logger via
    ``cache_logger_on_first_use`` (mirrors
    test_onboarding_walkthrough._capture_workflow_logs).
    """
    from autom8_asana.automation.workflows import bridge_base as _bb_mod

    proxy = _bb_mod.logger
    if "bind" in getattr(proxy, "__dict__", {}):
        del proxy.__dict__["bind"]
    return structlog.testing.capture_logs()


# --- BridgeOutcome Tests ---


class TestBridgeOutcome:
    """Tests for the BridgeOutcome dataclass."""

    def test_bridge_outcome_all_fields(self) -> None:
        error = WorkflowItemError(
            item_id="g1",
            error_type="test",
            message="fail",
        )
        outcome = BridgeOutcome(
            gid="g1",
            status="failed",
            reason="bad data",
            error=error,
        )
        assert outcome.gid == "g1"
        assert outcome.status == "failed"
        assert outcome.reason == "bad data"
        assert outcome.error is error

    def test_bridge_outcome_defaults(self) -> None:
        outcome = BridgeOutcome(gid="g1", status="succeeded")
        assert outcome.reason is None
        assert outcome.error is None


# --- DataSource Protocol Tests ---


class TestDataSourceProtocol:
    """Tests for DataSource protocol conformance."""

    def test_data_service_client_is_data_source(self) -> None:
        """DataServiceClient structurally satisfies DataSource protocol."""
        from autom8_asana.automation.workflows.protocols import DataSource
        from autom8_asana.clients.data.client import DataServiceClient

        assert issubclass(DataServiceClient, DataSource)


# --- validate_async Tests ---


class TestValidateAsync:
    """Tests for BridgeWorkflowAction.validate_async."""

    async def test_feature_flag_disabled_false(self) -> None:
        bridge = _make_test_bridge()
        with patch.dict(os.environ, {"TEST_BRIDGE_ENABLED": "false"}):
            errors = await bridge.validate_async()
        assert len(errors) == 1
        assert "disabled" in errors[0].lower()
        assert "TEST_BRIDGE_ENABLED" in errors[0]

    async def test_feature_flag_disabled_zero(self) -> None:
        bridge = _make_test_bridge()
        with patch.dict(os.environ, {"TEST_BRIDGE_ENABLED": "0"}):
            errors = await bridge.validate_async()
        assert len(errors) == 1

    async def test_feature_flag_disabled_no(self) -> None:
        bridge = _make_test_bridge()
        with patch.dict(os.environ, {"TEST_BRIDGE_ENABLED": "no"}):
            errors = await bridge.validate_async()
        assert len(errors) == 1

    async def test_feature_flag_enabled_true(self) -> None:
        bridge = _make_test_bridge()
        with patch.dict(os.environ, {"TEST_BRIDGE_ENABLED": "true"}):
            errors = await bridge.validate_async()
        assert errors == []

    async def test_feature_flag_enabled_default(self) -> None:
        """Unset env var means enabled."""
        bridge = _make_test_bridge()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TEST_BRIDGE_ENABLED", None)
            errors = await bridge.validate_async()
        assert errors == []

    async def test_circuit_breaker_open(self) -> None:
        from autom8y_http import CircuitBreakerOpenError as SdkCBOpen

        mock_dc = MagicMock()
        mock_dc.is_healthy = AsyncMock(
            side_effect=SdkCBOpen(time_remaining=30.0, message="CB open")
        )
        bridge = _make_test_bridge(data_client=mock_dc)
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TEST_BRIDGE_ENABLED", None)
            errors = await bridge.validate_async()
        assert len(errors) == 1
        assert "circuit breaker" in errors[0].lower()

    async def test_data_client_none(self) -> None:
        """No health check when data_client is None."""
        bridge = _TestBridge(
            asana_client=MagicMock(),
            data_client=None,
            attachments_client=MagicMock(),
        )
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TEST_BRIDGE_ENABLED", None)
            errors = await bridge.validate_async()
        assert errors == []

    async def test_connection_error_ignored(self) -> None:
        """ConnectionError from is_healthy is NOT a pre-flight failure."""
        mock_dc = MagicMock()
        mock_dc.is_healthy = AsyncMock(side_effect=ConnectionError("refused"))
        bridge = _make_test_bridge(data_client=mock_dc)
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TEST_BRIDGE_ENABLED", None)
            errors = await bridge.validate_async()
        assert errors == []


# --- enumerate_async Tests ---


class TestEnumerateAsync:
    """Tests for BridgeWorkflowAction.enumerate_async."""

    async def test_targeted_fast_path(self) -> None:
        bridge = _make_test_bridge()
        scope = EntityScope(entity_ids=("gid1", "gid2"))
        result = await bridge.enumerate_async(scope)
        assert result == [
            {"gid": "gid1", "name": None},
            {"gid": "gid2", "name": None},
        ]

    async def test_full_path_delegates(self) -> None:
        bridge = _make_test_bridge()
        scope = EntityScope()
        result = await bridge.enumerate_async(scope)
        # _TestBridge.enumerate_entities returns one entity
        assert len(result) == 1
        assert result[0]["gid"] == "test-1"

    async def test_limit_truncation(self) -> None:
        """Limit is applied after full enumeration."""

        class _BigBridge(_TestBridge):
            async def enumerate_entities(self, scope: EntityScope) -> list[dict[str, Any]]:
                return [{"gid": f"e{i}", "name": f"E{i}"} for i in range(10)]

        bridge = _BigBridge(
            asana_client=MagicMock(),
            data_client=MagicMock(),
            attachments_client=MagicMock(),
        )
        bridge._data_client.is_healthy = AsyncMock()
        scope = EntityScope(limit=3)
        result = await bridge.enumerate_async(scope)
        assert len(result) == 3
        assert result[0]["gid"] == "e0"


# --- execute_async Tests ---


class TestExecuteAsync:
    """Tests for BridgeWorkflowAction.execute_async."""

    async def test_happy_path(self) -> None:
        bridge = _make_test_bridge()
        entities = [
            {"gid": "e1", "name": "E1"},
            {"gid": "e2", "name": "E2"},
        ]
        result = await bridge.execute_async(entities, {})
        assert isinstance(result, WorkflowResult)
        assert result.total == 2
        assert result.succeeded == 2
        assert result.failed == 0
        assert result.skipped == 0
        assert result.workflow_id == "test-bridge"

    async def test_broad_catch(self) -> None:
        """process_entity raising Exception results in failed outcome."""

        class _FailBridge(_TestBridge):
            async def process_entity(
                self, entity: dict[str, Any], params: dict[str, Any]
            ) -> BridgeOutcome:
                msg = f"boom {entity['gid']}"
                raise RuntimeError(msg)

        bridge = _FailBridge(
            asana_client=MagicMock(),
            data_client=MagicMock(),
            attachments_client=MagicMock(),
        )
        bridge._data_client.is_healthy = AsyncMock()
        entities = [{"gid": "e1", "name": "E1"}]
        result = await bridge.execute_async(entities, {})
        assert result.total == 1
        assert result.failed == 1
        assert result.succeeded == 0
        assert len(result.errors) == 1
        assert result.errors[0].item_id == "e1"
        assert "boom e1" in result.errors[0].message

    async def test_mixed_outcomes(self) -> None:
        """Mix of succeeded, failed, and skipped outcomes."""
        call_count = 0

        class _MixBridge(_TestBridge):
            async def process_entity(
                self, entity: dict[str, Any], params: dict[str, Any]
            ) -> BridgeOutcome:
                nonlocal call_count
                call_count += 1
                gid = entity["gid"]
                if gid == "fail":
                    return BridgeOutcome(
                        gid=gid,
                        status="failed",
                        error=WorkflowItemError(
                            item_id=gid,
                            error_type="test",
                            message="fail",
                        ),
                    )
                if gid == "skip":
                    return BridgeOutcome(
                        gid=gid,
                        status="skipped",
                        reason="skipped",
                    )
                return BridgeOutcome(gid=gid, status="succeeded")

        bridge = _MixBridge(
            asana_client=MagicMock(),
            data_client=MagicMock(),
            attachments_client=MagicMock(),
        )
        bridge._data_client.is_healthy = AsyncMock()
        entities = [
            {"gid": "ok", "name": "OK"},
            {"gid": "fail", "name": "Fail"},
            {"gid": "skip", "name": "Skip"},
        ]
        result = await bridge.execute_async(entities, {})
        assert result.total == 3
        assert result.succeeded == 1
        assert result.failed == 1
        assert result.skipped == 1
        assert call_count == 3

    async def test_concurrency_param(self) -> None:
        """max_concurrency param is respected."""
        bridge = _make_test_bridge()
        entities = [{"gid": f"e{i}", "name": f"E{i}"} for i in range(10)]
        result = await bridge.execute_async(entities, {"max_concurrency": 2})
        assert result.total == 10
        assert result.succeeded == 10


# --- _build_result_metadata Tests ---


class TestBuildResultMetadata:
    """Tests for the default _build_result_metadata."""

    def test_default_returns_empty(self) -> None:
        bridge = _make_test_bridge()
        outcomes = [BridgeOutcome(gid="e1", status="succeeded")]
        assert bridge._build_result_metadata(outcomes) == {}


# --- FR-1: terminal broad-catch observability (the swallow-close) ---


class TestBroadCatchObservability:
    """FR-1: the SHARED bridge runner's terminal broad-catch must emit a structured
    ERROR log on every swallowed per-entity failure -- closing the 2026-07-01
    fleet-wide observability swallow. Two-sided: the log fires ONLY on the fault
    path, never on a clean succeeded/skipped outcome.

    Discriminating-canary MODE 2 (genuine guard-absence): the broken entity is a
    broken INPUT fed to the REAL runner whose logger was genuinely absent -- NOT a
    defect injected into working code.
    """

    def _bridge(self, cls: type[_TestBridge]) -> _TestBridge:
        bridge = cls(
            asana_client=MagicMock(),
            data_client=MagicMock(),
            attachments_client=MagicMock(),
        )
        bridge._data_client.is_healthy = AsyncMock()
        return bridge

    async def test_broken_entity_logs_structured_error(self) -> None:
        """RED on pre-fix (failed:1 but ZERO logs -- reproduces 2026-07-01); GREEN on
        fixed (failed:1 AND exactly one ``bridge_entity_failed`` log carrying
        ``task_gid`` + ``error_type='ValueError'`` + a scrubbed ``error_message``)."""

        class _BrokenBridge(_TestBridge):
            async def process_entity(
                self, entity: dict[str, Any], params: dict[str, Any]
            ) -> BridgeOutcome:
                msg = "boom"
                raise ValueError(msg)

        bridge = self._bridge(_BrokenBridge)
        with _capture_bridge_logs() as captured:
            result = await bridge.execute_async([{"gid": "neu-life-fixture"}], {})

        assert result.failed == 1
        failed_logs = [e for e in captured if e["event"] == "bridge_entity_failed"]
        assert len(failed_logs) == 1  # exactly one structured line per failed outcome
        entry = failed_logs[0]
        assert entry["task_gid"] == "neu-life-fixture"
        assert entry["error_type"] == "ValueError"  # names the escaping class (R1/R2 signal)
        assert entry["error_message"] == "boom"  # scrubbed str(exc) (PII-safe here)
        assert entry["workflow_id"] == "test-bridge"  # fleet-shared line self-identifies
        assert entry["log_level"] == "error"
        # ``exc_info`` is deliberately DROPPED (XR-003): a rendered traceback's final
        # ``Type: str(exc)`` line would leak unmasked on the unredacted runtime surfaces.
        assert "exc_info" not in entry

    async def test_broken_entity_masks_pii_in_error_message(self) -> None:
        """F3 (XR-003, BLOCKING): when a swallowed exception's ``str()`` embeds a
        customer phone (mirrors autom8y_core ``BusinessNotFoundError`` "No business
        found for phone: +1..."), the SHARED runner MUST scrub it at the log call-site
        BEFORE emission. ``capture_logs`` bypasses the processor chain, so the mask is
        observable ONLY because it is applied at the call-site (which it now is).

        Teeth (two vectors, one guard): reverting the ``_mask_pii_in_string`` wrap OR
        re-adding ``exc_info=exc`` reintroduces the raw phone and trips
        ``raw_phone not in repr(entry)``.
        """
        raw_phone = "+17705753103"
        masked_phone = "+1770***3103"

        class _PhoneLeakBridge(_TestBridge):
            async def process_entity(
                self, entity: dict[str, Any], params: dict[str, Any]
            ) -> BridgeOutcome:
                msg = f"No business found for phone: {raw_phone}"
                raise ValueError(msg)

        bridge = self._bridge(_PhoneLeakBridge)
        with _capture_bridge_logs() as captured:
            result = await bridge.execute_async([{"gid": "pii-fixture"}], {})

        assert result.failed == 1
        failed_logs = [e for e in captured if e["event"] == "bridge_entity_failed"]
        assert len(failed_logs) == 1
        entry = failed_logs[0]
        # the scrubbed field carries the MASKED form ...
        assert entry["error_message"] == f"No business found for phone: {masked_phone}"
        # ... and the raw E.164 number is absent from EVERY captured field/value
        # (the message AND any residual exc_info the mask would not reach).
        haystack = repr(entry)
        assert raw_phone not in haystack
        assert masked_phone in haystack

    async def test_clean_entity_emits_no_error_log(self) -> None:
        """Two-sided teeth: a succeeded entity emits ZERO bridge_entity_failed logs."""
        bridge = self._bridge(_TestBridge)  # default process_entity returns succeeded
        with _capture_bridge_logs() as captured:
            result = await bridge.execute_async([{"gid": "clean-1"}], {})
        assert result.succeeded == 1
        assert [e for e in captured if e["event"] == "bridge_entity_failed"] == []

    async def test_skipped_entity_emits_no_error_log(self) -> None:
        """Two-sided teeth: a skipped entity emits ZERO bridge_entity_failed logs."""

        class _SkipBridge(_TestBridge):
            async def process_entity(
                self, entity: dict[str, Any], params: dict[str, Any]
            ) -> BridgeOutcome:
                return BridgeOutcome(gid=entity["gid"], status="skipped", reason="nothing_to_do")

        bridge = self._bridge(_SkipBridge)
        with _capture_bridge_logs() as captured:
            result = await bridge.execute_async([{"gid": "skip-1"}], {})
        assert result.skipped == 1
        assert [e for e in captured if e["event"] == "bridge_entity_failed"] == []
