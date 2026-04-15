"""Tests for bridge workflow protocols.

Per TDD sprint-3 Section 8: Verify DataSource protocol conformance
and structural typing contract.

Per ADR-bridge-format-engine: Verify FormatEngine protocol conformance.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from autom8_asana.automation.workflows.protocols import DataSource, FormatEngine


class TestDataSourceProtocol:
    """Tests for the DataSource protocol."""

    def test_runtime_checkable(self) -> None:
        """DataSource is runtime_checkable."""
        assert hasattr(DataSource, "__protocol_attrs__") or hasattr(
            DataSource, "__abstractmethods__"
        )

    def test_data_service_client_conformance(self) -> None:
        """DataServiceClient structurally satisfies DataSource."""
        from autom8_asana.clients.data.client import DataServiceClient

        assert issubclass(DataServiceClient, DataSource)

    def test_mock_with_is_healthy_conforms(self) -> None:
        """A mock with is_healthy satisfies the protocol at runtime."""

        class _FakeDataSource:
            async def is_healthy(self) -> None:
                pass

        assert isinstance(_FakeDataSource(), DataSource)

    def test_object_without_is_healthy_does_not_conform(self) -> None:
        """An object missing is_healthy does NOT satisfy DataSource."""

        class _NotADataSource:
            pass

        assert not isinstance(_NotADataSource(), DataSource)

    async def test_is_healthy_can_be_awaited(self) -> None:
        """is_healthy() returns a coroutine that can be awaited."""

        class _FakeDataSource:
            is_healthy = AsyncMock()

        ds = _FakeDataSource()
        await ds.is_healthy()
        ds.is_healthy.assert_awaited_once()


class TestFormatEngineProtocol:
    """Tests for the FormatEngine protocol.

    Per ADR-bridge-format-engine: FormatEngine is a platform-level protocol
    for bridge output formatters. It defines content_type, file_extension,
    and render(data) -> bytes.
    """

    def test_runtime_checkable(self) -> None:
        """FormatEngine is runtime_checkable."""
        assert hasattr(FormatEngine, "__protocol_attrs__") or hasattr(
            FormatEngine, "__abstractmethods__"
        )

    def test_conforming_class_is_instance(self) -> None:
        """A class with content_type, file_extension, and render() conforms."""

        class _HtmlEngine:
            content_type = "text/html"
            file_extension = ".html"

            def render(self, data: dict[str, Any]) -> bytes:
                return b"<html></html>"

        assert isinstance(_HtmlEngine(), FormatEngine)

    def test_conforming_csv_engine(self) -> None:
        """A CSV passthrough engine conforms."""

        class _CsvPassthrough:
            content_type = "text/csv"
            file_extension = ".csv"

            def render(self, data: dict[str, Any]) -> bytes:
                return data.get("csv_content", b"")

        engine = _CsvPassthrough()
        assert isinstance(engine, FormatEngine)

    def test_conforming_excel_engine(self) -> None:
        """A hypothetical Excel engine conforms."""

        class _ExcelEngine:
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            file_extension = ".xlsx"

            def render(self, data: dict[str, Any]) -> bytes:
                return b"PK..."  # xlsx is zip-based

        assert isinstance(_ExcelEngine(), FormatEngine)

    def test_missing_render_does_not_conform(self) -> None:
        """An object without render() does NOT satisfy FormatEngine."""

        class _NoRender:
            content_type = "text/html"
            file_extension = ".html"

        assert not isinstance(_NoRender(), FormatEngine)

    def test_missing_content_type_does_not_conform(self) -> None:
        """An object without content_type does NOT satisfy FormatEngine."""

        class _NoContentType:
            file_extension = ".html"

            def render(self, data: dict[str, Any]) -> bytes:
                return b""

        assert not isinstance(_NoContentType(), FormatEngine)

    def test_missing_file_extension_does_not_conform(self) -> None:
        """An object without file_extension does NOT satisfy FormatEngine."""

        class _NoFileExtension:
            content_type = "text/html"

            def render(self, data: dict[str, Any]) -> bytes:
                return b""

        assert not isinstance(_NoFileExtension(), FormatEngine)

    def test_render_returns_bytes(self) -> None:
        """render() returns bytes, not str."""

        class _HtmlEngine:
            content_type = "text/html"
            file_extension = ".html"

            def render(self, data: dict[str, Any]) -> bytes:
                title = data.get("title", "Report")
                return f"<html><body>{title}</body></html>".encode()

        engine = _HtmlEngine()
        result = engine.render({"title": "Test Report"})
        assert isinstance(result, bytes)
        assert b"Test Report" in result

    def test_render_with_empty_data(self) -> None:
        """render() handles empty data dict."""

        class _MinimalEngine:
            content_type = "text/plain"
            file_extension = ".txt"

            def render(self, data: dict[str, Any]) -> bytes:
                return b"empty"

        engine = _MinimalEngine()
        result = engine.render({})
        assert result == b"empty"

    def test_protocol_is_opt_in(self) -> None:
        """FormatEngine is opt-in: BridgeWorkflowAction does not require it.

        Per ADR-bridge-format-engine: ConversationAudit does not use
        FormatEngine. Verify that BridgeWorkflowAction subclasses are
        not required to implement or reference FormatEngine.
        """
        from autom8_asana.automation.workflows.bridge_base import (
            BridgeWorkflowAction,
        )

        # BridgeWorkflowAction has no reference to FormatEngine
        assert not hasattr(BridgeWorkflowAction, "format_engine")

    def test_format_engine_importable_from_package(self) -> None:
        """FormatEngine is importable from the workflows package."""
        from autom8_asana.automation.workflows import FormatEngine as FE

        assert FE is FormatEngine


class TestInteropProtocolAlignment:
    """Tests for protocol alignment with autom8y-client-sdk.

    Per ADR-bridge-dispatch-model H-003: Verify that DataServiceClient
    structurally satisfies both DataSource (bridge protocol) and partially
    satisfies interop protocols. This test class documents the alignment
    gap and prevents regression.
    """

    def test_data_service_client_satisfies_data_source(self) -> None:
        """DataServiceClient structurally satisfies bridge DataSource."""
        from autom8_asana.clients.data.client import DataServiceClient

        assert issubclass(DataServiceClient, DataSource)

    def test_data_service_client_has_insight_method(self) -> None:
        """DataServiceClient has get_insights_async (maps to interop get_insight).

        Per INTEGRATE Section 1.3: The insight fetch overlap is partial --
        bridge client has richer params (batch, caching, async).
        """
        from autom8_asana.clients.data.client import DataServiceClient

        assert hasattr(DataServiceClient, "get_insights_async")

    def test_data_service_client_has_health_check(self) -> None:
        """DataServiceClient has is_healthy (maps to interop health_check).

        The signatures differ: DataSource.is_healthy() -> None (raises)
        vs DataReadProtocol.health_check() -> dict[str, Any].
        """
        from autom8_asana.clients.data.client import DataServiceClient

        assert hasattr(DataServiceClient, "is_healthy")

    def test_data_service_client_has_reconciliation_gap(self) -> None:
        """DataServiceClient has get_reconciliation_async with no interop equivalent.

        Per INTEGRATE Section 1.3: No DataReconciliationProtocol exists
        in autom8y-client-sdk. This test documents the gap.
        """
        from autom8_asana.clients.data.client import DataServiceClient

        # Bridge client has reconciliation -- interop does not
        assert hasattr(DataServiceClient, "get_reconciliation_async")

    def test_interop_insight_protocol_importable(self) -> None:
        """autom8y_client_sdk.data.DataInsightProtocol is importable.

        Per H-003: Verifies the interop dependency resolves correctly
        as an optional extra.
        """
        from autom8y_client_sdk.data import DataInsightProtocol

        assert hasattr(DataInsightProtocol, "get_insight")

    def test_interop_read_protocol_has_health_check(self) -> None:
        """autom8y_client_sdk.data.DataReadProtocol has health_check.

        Documents the semantic overlap with DataSource.is_healthy().
        """
        from autom8y_client_sdk.data import DataReadProtocol

        assert hasattr(DataReadProtocol, "health_check")

    def test_protocol_coverage_map_documented(self) -> None:
        """protocols.py module docstring documents the coverage map.

        Per H-003: Alignment documentation must exist in the protocol
        module for future engineers.
        """
        from autom8_asana.automation.workflows import protocols

        docstring = protocols.__doc__ or ""
        assert "Protocol Alignment with autom8y-client-sdk" in docstring
        assert "DataReconciliationProtocol" in docstring
