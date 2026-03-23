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

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_false(self) -> None:
        bridge = _make_test_bridge()
        with patch.dict(os.environ, {"TEST_BRIDGE_ENABLED": "false"}):
            errors = await bridge.validate_async()
        assert len(errors) == 1
        assert "disabled" in errors[0].lower()
        assert "TEST_BRIDGE_ENABLED" in errors[0]

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_zero(self) -> None:
        bridge = _make_test_bridge()
        with patch.dict(os.environ, {"TEST_BRIDGE_ENABLED": "0"}):
            errors = await bridge.validate_async()
        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_no(self) -> None:
        bridge = _make_test_bridge()
        with patch.dict(os.environ, {"TEST_BRIDGE_ENABLED": "no"}):
            errors = await bridge.validate_async()
        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_feature_flag_enabled_true(self) -> None:
        bridge = _make_test_bridge()
        with patch.dict(os.environ, {"TEST_BRIDGE_ENABLED": "true"}):
            errors = await bridge.validate_async()
        assert errors == []

    @pytest.mark.asyncio
    async def test_feature_flag_enabled_default(self) -> None:
        """Unset env var means enabled."""
        bridge = _make_test_bridge()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TEST_BRIDGE_ENABLED", None)
            errors = await bridge.validate_async()
        assert errors == []

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_targeted_fast_path(self) -> None:
        bridge = _make_test_bridge()
        scope = EntityScope(entity_ids=("gid1", "gid2"))
        result = await bridge.enumerate_async(scope)
        assert result == [
            {"gid": "gid1", "name": None},
            {"gid": "gid2", "name": None},
        ]

    @pytest.mark.asyncio
    async def test_full_path_delegates(self) -> None:
        bridge = _make_test_bridge()
        scope = EntityScope()
        result = await bridge.enumerate_async(scope)
        # _TestBridge.enumerate_entities returns one entity
        assert len(result) == 1
        assert result[0]["gid"] == "test-1"

    @pytest.mark.asyncio
    async def test_limit_truncation(self) -> None:
        """Limit is applied after full enumeration."""

        class _BigBridge(_TestBridge):
            async def enumerate_entities(
                self, scope: EntityScope
            ) -> list[dict[str, Any]]:
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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
