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
        assert "_push_account_status_for_completed_entities" in push_orchestrator.__all__


class TestPushGidMappingsDispatch:
    """_push_gid_mappings_for_completed_entities dispatch validation."""

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
            patch("autom8_asana.services.gid_lookup.GidLookupIndex") as mock_index_cls,
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

    async def test_unmapped_entity_surfaced_and_mapped_rows_still_pushed(self) -> None:
        """T3 (sprint-C6): warm-set vs PIPELINE_TYPE_BY_PROJECT_GID
        reconciliation -- an entity whose project GID is absent from the map is
        surfaced (WARNING + StatusPushUnmappedEntities), NOT silently accepted,
        and the mapped entity's rows are still pushed."""
        import polars as pl

        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )

        unit_gid = "1201081073731555"  # mapped -> pipeline_type "unit"
        offer_gid = "1143843662099250"  # absent from PIPELINE_TYPE_BY_PROJECT_GID
        gid_by_entity = {"unit": unit_gid, "offer": offer_gid}

        unit_df = pl.DataFrame(
            {
                "office_phone": ["+15551230001"],
                "vertical": ["chiropractor"],
                "section": ["Active"],
            }
        )
        offer_df = pl.DataFrame(
            {
                "office_phone": ["+15551230002"],
                "vertical": ["chiropractor"],
                "section": ["ACTIVE"],
            }
        )
        frames = {unit_gid: unit_df, offer_gid: offer_df}

        def _make_entry(gid: str) -> MagicMock:
            entry = MagicMock()
            entry.dataframe = frames[gid]
            return entry

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(side_effect=lambda gid, et: _make_entry(gid))

        with (
            patch(
                "autom8_asana.services.gid_push.push_status_to_data_service",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_push,
            patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric") as mock_emit,
            patch("autom8_asana.lambda_handlers.push_orchestrator.logger") as mock_logger,
        ):
            await _push_account_status_for_completed_entities(
                completed_entities=["unit", "offer"],
                get_project_gid=gid_by_entity.get,
                cache=mock_cache,
                invocation_id="test-inv",
            )

        # WARNING status_push_registry_coverage with unmapped=["offer"]
        coverage_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args[0] == "status_push_registry_coverage"
        ]
        assert coverage_calls, "expected status_push_registry_coverage WARNING"
        extra = coverage_calls[0].kwargs["extra"]
        assert extra["mapped"] == ["unit"]
        assert extra["unmapped"] == ["offer"]
        assert extra["invocation_id"] == "test-inv"

        # StatusPushUnmappedEntities = 1 to the bridge fleet namespace
        unmapped_emits = [
            c for c in mock_emit.call_args_list if c.args[0] == "StatusPushUnmappedEntities"
        ]
        assert len(unmapped_emits) == 1
        assert unmapped_emits[0].args[1] == 1
        assert unmapped_emits[0].kwargs["namespace"] == "Autom8y/AsanaBridgeFleet"

        # Unit rows STILL pushed (the narrowing is surfaced, not fatal)
        mock_push.assert_awaited_once()
        pushed_entries = mock_push.call_args.kwargs["entries"]
        assert len(pushed_entries) == 1
        assert pushed_entries[0]["pipeline_type"] == "unit"

    async def test_all_mapped_entities_emit_zero_unmapped_and_no_warning(self) -> None:
        """Positive control: an all-mapped warm set produces NO coverage
        warning and StatusPushUnmappedEntities = 0."""
        import polars as pl

        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )

        unit_gid = "1201081073731555"
        unit_df = pl.DataFrame(
            {
                "office_phone": ["+15551230001"],
                "vertical": ["chiropractor"],
                "section": ["Active"],
            }
        )
        mock_entry = MagicMock()
        mock_entry.dataframe = unit_df
        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=mock_entry)

        with (
            patch(
                "autom8_asana.services.gid_push.push_status_to_data_service",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric") as mock_emit,
            patch("autom8_asana.lambda_handlers.push_orchestrator.logger") as mock_logger,
        ):
            await _push_account_status_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid={"unit": unit_gid}.get,
                cache=mock_cache,
                invocation_id="test-inv",
            )

        assert not [
            c
            for c in mock_logger.warning.call_args_list
            if c.args[0] == "status_push_registry_coverage"
        ], "positive control must not warn"
        unmapped_emits = [
            c for c in mock_emit.call_args_list if c.args[0] == "StatusPushUnmappedEntities"
        ]
        assert len(unmapped_emits) == 1
        assert unmapped_emits[0].args[1] == 0

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
