"""Dispatch tests for push_orchestrator Lambda utility module.

Per SCAN-asana-deep-triage Task 4: Cold-start dispatch validation for
push_orchestrator.py. Validates module importability, function signatures,
error propagation (failures are isolated, never abort the warmer), and
that both GID push and account-status push paths work as documented.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestPushOrchestratorModuleInterface:
    """Module is importable and exposes expected interface."""

    def test_module_importable(self) -> None:
        import autom8_asana.lambda_handlers.push_orchestrator as mod

        assert mod is not None

    def test_push_gid_mappings_callable(self) -> None:
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_gid_mappings_for_completed_entities,
        )

        assert callable(_push_gid_mappings_for_completed_entities)

    def test_push_account_status_callable(self) -> None:
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )

        assert callable(_push_account_status_for_completed_entities)

    def test_all_exports_present(self) -> None:
        from autom8_asana.lambda_handlers import push_orchestrator

        assert "_push_gid_mappings_for_completed_entities" in push_orchestrator.__all__
        assert (
            "_push_account_status_for_completed_entities" in push_orchestrator.__all__
        )


class TestPushGidMappingsDispatch:
    """_push_gid_mappings_for_completed_entities dispatch validation."""

    @pytest.mark.asyncio
    async def test_empty_entities_is_noop(self) -> None:
        """No entities means no pushes, no errors."""
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_gid_mappings_for_completed_entities,
        )

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=None)

        await _push_gid_mappings_for_completed_entities(
            completed_entities=[],
            get_project_gid=lambda _: None,
            cache=mock_cache,
            invocation_id="test-inv",
        )

        mock_cache.get_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_entity_with_no_project_gid_skipped(self) -> None:
        """Entities where get_project_gid returns None are skipped."""
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_gid_mappings_for_completed_entities,
        )

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=None)

        await _push_gid_mappings_for_completed_entities(
            completed_entities=["unit"],
            get_project_gid=lambda _: None,
            cache=mock_cache,
            invocation_id="test-inv",
        )

        mock_cache.get_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_cache_miss_skipped_gracefully(self) -> None:
        """When cache returns None for a project, entity is skipped without error."""
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_gid_mappings_for_completed_entities,
        )

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=None)

        with patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric"):
            await _push_gid_mappings_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid=lambda _: "proj-001",
                cache=mock_cache,
                invocation_id="test-inv",
            )

        mock_cache.get_async.assert_awaited_once_with("proj-001", "unit")

    @pytest.mark.asyncio
    async def test_push_failure_does_not_propagate(self) -> None:
        """push_gid_mappings_to_data_service failure is isolated — must not raise."""
        import polars as pl

        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_gid_mappings_for_completed_entities,
        )

        mock_entry = MagicMock()
        mock_entry.dataframe = pl.DataFrame({"gid": ["123"], "office_phone": ["555"]})

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=mock_entry)

        mock_index = MagicMock()
        mock_index.__len__ = MagicMock(return_value=1)

        with (
            patch(
                "autom8_asana.services.gid_lookup.GidLookupIndex"
            ) as mock_index_cls,
            patch(
                "autom8_asana.services.gid_push.push_gid_mappings_to_data_service",
                side_effect=Exception("push service down"),
            ),
            patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric"),
        ):
            mock_index_cls.from_dataframe.return_value = mock_index
            # Must not raise — failure is isolated per BROAD-CATCH: isolation
            await _push_gid_mappings_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid=lambda _: "proj-001",
                cache=mock_cache,
                invocation_id="test-inv",
            )


class TestPushAccountStatusDispatch:
    """_push_account_status_for_completed_entities dispatch validation."""

    @pytest.mark.asyncio
    async def test_empty_entities_is_noop(self) -> None:
        """No entities means no pushes, no errors."""
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=None)

        with patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric"):
            await _push_account_status_for_completed_entities(
                completed_entities=[],
                get_project_gid=lambda _: None,
                cache=mock_cache,
                invocation_id="test-inv",
            )

        mock_cache.get_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_entity_with_no_project_gid_skipped(self) -> None:
        """Entities where get_project_gid returns None are skipped."""
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=None)

        with patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric"):
            await _push_account_status_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid=lambda _: None,
                cache=mock_cache,
                invocation_id="test-inv",
            )

        mock_cache.get_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_extract_failure_does_not_propagate(self) -> None:
        """Extraction failure per-entity is isolated — must not raise."""
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )

        mock_entry = MagicMock()
        mock_entry.dataframe = MagicMock()

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=mock_entry)

        with (
            patch(
                "autom8_asana.services.gid_push.extract_status_from_dataframe",
                side_effect=Exception("extraction failed"),
            ),
            patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric"),
        ):
            # Must not raise — BROAD-CATCH: isolation
            await _push_account_status_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid=lambda _: "proj-001",
                cache=mock_cache,
                invocation_id="test-inv",
            )
