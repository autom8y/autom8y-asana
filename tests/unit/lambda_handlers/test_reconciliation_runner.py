"""Unit tests for reconciliation shadow-mode runner."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.lambda_handlers.reconciliation_runner import (
    _run_reconciliation_shadow,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_project_gid(entity_type: str) -> str:
    """Deterministic project GID resolver for tests."""
    return {"unit": "project-unit-1", "offer": "project-offer-2"}.get(
        entity_type, f"project-{entity_type}"
    )


def _make_cache_entry(*, dataframe: object = None) -> MagicMock:
    """Create a mock cache entry with a configurable dataframe attribute."""
    entry = MagicMock()
    entry.dataframe = dataframe
    return entry


# ---------------------------------------------------------------------------
# Feature flag tests
# ---------------------------------------------------------------------------


class TestFeatureFlagGuard:
    """Feature flag must be enabled for reconciliation to run."""

    @pytest.mark.asyncio
    async def test_returns_early_when_flag_not_set(self) -> None:
        """No env var -> returns without calling anything downstream."""
        with patch.dict("os.environ", {}, clear=False):
            # Ensure flag is absent
            import os

            os.environ.pop("ASANA_RECONCILIATION_SHADOW_ENABLED", None)

            with patch(
                "autom8_asana.reconciliation.engine.run_reconciliation"
            ) as mock_engine:
                await _run_reconciliation_shadow(
                    completed_entities=["unit", "offer"],
                    get_project_gid=_get_project_gid,
                    cache=MagicMock(),
                    invocation_id="test-1",
                )
            mock_engine.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_early_when_flag_is_false(self) -> None:
        """Flag set to 'false' -> returns without calling engine."""
        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "false"},
        ):
            with patch(
                "autom8_asana.reconciliation.engine.run_reconciliation"
            ) as mock_engine:
                await _run_reconciliation_shadow(
                    completed_entities=["unit", "offer"],
                    get_project_gid=_get_project_gid,
                    cache=MagicMock(),
                    invocation_id="test-2",
                )
            mock_engine.assert_not_called()

    @pytest.mark.asyncio
    async def test_proceeds_when_flag_is_true(self) -> None:
        """Flag set to 'true' -> engine is called."""
        mock_cache = MagicMock()
        mock_entry = _make_cache_entry(dataframe=MagicMock())
        mock_cache.get_async = AsyncMock(return_value=mock_entry)

        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "true"},
        ):
            with (
                patch(
                    "autom8_asana.reconciliation.engine.run_reconciliation"
                ) as mock_engine,
                patch(
                    "autom8_asana.reconciliation.executor.execute_actions",
                    new_callable=AsyncMock,
                ),
                patch("autom8_asana.reconciliation.report.build_report"),
                patch("autom8_asana.reconciliation.report.emit_report_metrics"),
            ):
                mock_engine.return_value = MagicMock(
                    processor_result=MagicMock(actions=[]),
                    actions_planned=0,
                    total_scanned=10,
                    excluded_count=2,
                )
                await _run_reconciliation_shadow(
                    completed_entities=["unit", "offer"],
                    get_project_gid=_get_project_gid,
                    cache=mock_cache,
                    invocation_id="test-3",
                )
            mock_engine.assert_called_once()

    @pytest.mark.asyncio
    async def test_proceeds_when_flag_is_one(self) -> None:
        """Flag set to '1' -> engine is called."""
        mock_cache = MagicMock()
        mock_entry = _make_cache_entry(dataframe=MagicMock())
        mock_cache.get_async = AsyncMock(return_value=mock_entry)

        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "1"},
        ):
            with (
                patch(
                    "autom8_asana.reconciliation.engine.run_reconciliation"
                ) as mock_engine,
                patch(
                    "autom8_asana.reconciliation.executor.execute_actions",
                    new_callable=AsyncMock,
                ),
                patch("autom8_asana.reconciliation.report.build_report"),
                patch("autom8_asana.reconciliation.report.emit_report_metrics"),
            ):
                mock_engine.return_value = MagicMock(
                    processor_result=MagicMock(actions=[]),
                    actions_planned=0,
                    total_scanned=5,
                    excluded_count=0,
                )
                await _run_reconciliation_shadow(
                    completed_entities=["unit", "offer"],
                    get_project_gid=_get_project_gid,
                    cache=mock_cache,
                    invocation_id="test-4",
                )
            mock_engine.assert_called_once()


# ---------------------------------------------------------------------------
# Entity guard tests
# ---------------------------------------------------------------------------


class TestEntityGuard:
    """Both 'unit' and 'offer' must be in completed_entities."""

    @pytest.mark.asyncio
    async def test_skips_when_unit_missing(self) -> None:
        """Only 'offer' completed -> skips with log."""
        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "true"},
        ):
            with patch(
                "autom8_asana.reconciliation.engine.run_reconciliation"
            ) as mock_engine:
                await _run_reconciliation_shadow(
                    completed_entities=["offer"],
                    get_project_gid=_get_project_gid,
                    cache=MagicMock(),
                    invocation_id="test-5",
                )
            mock_engine.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_offer_missing(self) -> None:
        """Only 'unit' completed -> skips with log."""
        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "true"},
        ):
            with patch(
                "autom8_asana.reconciliation.engine.run_reconciliation"
            ) as mock_engine:
                await _run_reconciliation_shadow(
                    completed_entities=["unit"],
                    get_project_gid=_get_project_gid,
                    cache=MagicMock(),
                    invocation_id="test-6",
                )
            mock_engine.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_empty_list(self) -> None:
        """Empty completed_entities -> skips."""
        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "true"},
        ):
            with patch(
                "autom8_asana.reconciliation.engine.run_reconciliation"
            ) as mock_engine:
                await _run_reconciliation_shadow(
                    completed_entities=[],
                    get_project_gid=_get_project_gid,
                    cache=MagicMock(),
                    invocation_id="test-7",
                )
            mock_engine.assert_not_called()


# ---------------------------------------------------------------------------
# DataFrame availability tests
# ---------------------------------------------------------------------------


class TestDataFrameAvailability:
    """Cache must return valid entries with non-None DataFrames."""

    @pytest.mark.asyncio
    async def test_skips_when_unit_entry_is_none(self) -> None:
        """cache.get_async returns None for unit -> skips."""
        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(
            side_effect=lambda gid, et: (
                None if et == "unit" else _make_cache_entry(dataframe=MagicMock())
            )
        )

        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "true"},
        ):
            with patch(
                "autom8_asana.reconciliation.engine.run_reconciliation"
            ) as mock_engine:
                await _run_reconciliation_shadow(
                    completed_entities=["unit", "offer"],
                    get_project_gid=_get_project_gid,
                    cache=mock_cache,
                    invocation_id="test-8",
                )
            mock_engine.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_unit_dataframe_is_none(self) -> None:
        """Cache entry exists but dataframe attr is None -> skips."""
        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(
            side_effect=lambda gid, et: (
                _make_cache_entry(dataframe=None)
                if et == "unit"
                else _make_cache_entry(dataframe=MagicMock())
            )
        )

        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "true"},
        ):
            with patch(
                "autom8_asana.reconciliation.engine.run_reconciliation"
            ) as mock_engine:
                await _run_reconciliation_shadow(
                    completed_entities=["unit", "offer"],
                    get_project_gid=_get_project_gid,
                    cache=mock_cache,
                    invocation_id="test-9",
                )
            mock_engine.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_offer_entry_is_none(self) -> None:
        """cache.get_async returns None for offer -> skips."""
        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(
            side_effect=lambda gid, et: (
                _make_cache_entry(dataframe=MagicMock())
                if et == "unit"
                else None
            )
        )

        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "true"},
        ):
            with patch(
                "autom8_asana.reconciliation.engine.run_reconciliation"
            ) as mock_engine:
                await _run_reconciliation_shadow(
                    completed_entities=["unit", "offer"],
                    get_project_gid=_get_project_gid,
                    cache=mock_cache,
                    invocation_id="test-10",
                )
            mock_engine.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_offer_dataframe_is_none(self) -> None:
        """Cache entry exists but offer dataframe is None -> skips."""
        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(
            side_effect=lambda gid, et: (
                _make_cache_entry(dataframe=MagicMock())
                if et == "unit"
                else _make_cache_entry(dataframe=None)
            )
        )

        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "true"},
        ):
            with patch(
                "autom8_asana.reconciliation.engine.run_reconciliation"
            ) as mock_engine:
                await _run_reconciliation_shadow(
                    completed_entities=["unit", "offer"],
                    get_project_gid=_get_project_gid,
                    cache=mock_cache,
                    invocation_id="test-11",
                )
            mock_engine.assert_not_called()


# ---------------------------------------------------------------------------
# Happy path test
# ---------------------------------------------------------------------------


class TestHappyPath:
    """Full pipeline: engine -> executor -> report."""

    @pytest.mark.asyncio
    async def test_full_pipeline_executes(self) -> None:
        """Engine called, executor called, report built and emitted."""
        mock_unit_df = MagicMock(name="unit_df")
        mock_offer_df = MagicMock(name="offer_df")

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(
            side_effect=lambda gid, et: (
                _make_cache_entry(dataframe=mock_unit_df)
                if et == "unit"
                else _make_cache_entry(dataframe=mock_offer_df)
            )
        )

        mock_actions = [MagicMock(), MagicMock()]
        mock_processor_result = MagicMock(actions=mock_actions)
        mock_result = MagicMock(
            processor_result=mock_processor_result,
            actions_planned=2,
            total_scanned=50,
            excluded_count=5,
        )

        mock_report = MagicMock()

        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "yes"},
        ):
            with (
                patch(
                    "autom8_asana.reconciliation.engine.run_reconciliation",
                    return_value=mock_result,
                ) as mock_engine,
                patch(
                    "autom8_asana.reconciliation.executor.execute_actions",
                    new_callable=AsyncMock,
                ) as mock_executor,
                patch(
                    "autom8_asana.reconciliation.report.build_report",
                    return_value=mock_report,
                ) as mock_build,
                patch(
                    "autom8_asana.reconciliation.report.emit_report_metrics",
                ) as mock_emit,
            ):
                await _run_reconciliation_shadow(
                    completed_entities=["unit", "offer"],
                    get_project_gid=_get_project_gid,
                    cache=mock_cache,
                    invocation_id="test-happy",
                )

                # Engine called with correct DFs and dry_run config
                mock_engine.assert_called_once()
                call_args = mock_engine.call_args
                assert call_args[0][0] is mock_unit_df
                assert call_args[0][1] is mock_offer_df
                config = call_args[1]["config"]
                assert config.dry_run is True

                # Executor called with actions, dry_run=True
                mock_executor.assert_called_once_with(
                    mock_actions, dry_run=True
                )

                # Report built and emitted
                mock_build.assert_called_once_with(mock_processor_result)
                mock_emit.assert_called_once_with(mock_report)

    @pytest.mark.asyncio
    async def test_accepts_extra_entities_beyond_required(self) -> None:
        """Having extra entities like 'contact' beyond unit/offer still runs."""
        mock_cache = MagicMock()
        mock_entry = _make_cache_entry(dataframe=MagicMock())
        mock_cache.get_async = AsyncMock(return_value=mock_entry)

        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "true"},
        ):
            with (
                patch(
                    "autom8_asana.reconciliation.engine.run_reconciliation"
                ) as mock_engine,
                patch(
                    "autom8_asana.reconciliation.executor.execute_actions",
                    new_callable=AsyncMock,
                ),
                patch("autom8_asana.reconciliation.report.build_report"),
                patch("autom8_asana.reconciliation.report.emit_report_metrics"),
            ):
                mock_engine.return_value = MagicMock(
                    processor_result=MagicMock(actions=[]),
                    actions_planned=0,
                    total_scanned=0,
                    excluded_count=0,
                )
                await _run_reconciliation_shadow(
                    completed_entities=["unit", "offer", "contact"],
                    get_project_gid=_get_project_gid,
                    cache=mock_cache,
                    invocation_id="test-extra",
                )
            mock_engine.assert_called_once()


# ---------------------------------------------------------------------------
# Error isolation tests
# ---------------------------------------------------------------------------


class TestErrorIsolation:
    """Exceptions must be caught and logged, never propagated."""

    @pytest.mark.asyncio
    async def test_engine_exception_is_caught(self) -> None:
        """Exception in engine -> caught, logged, no crash."""
        mock_cache = MagicMock()
        mock_entry = _make_cache_entry(dataframe=MagicMock())
        mock_cache.get_async = AsyncMock(return_value=mock_entry)

        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "true"},
        ):
            with patch(
                "autom8_asana.reconciliation.engine.run_reconciliation",
                side_effect=RuntimeError("engine boom"),
            ):
                # Should NOT raise
                await _run_reconciliation_shadow(
                    completed_entities=["unit", "offer"],
                    get_project_gid=_get_project_gid,
                    cache=mock_cache,
                    invocation_id="test-err-1",
                )

    @pytest.mark.asyncio
    async def test_executor_exception_is_caught(self) -> None:
        """Exception in executor -> caught, logged, no crash."""
        mock_cache = MagicMock()
        mock_entry = _make_cache_entry(dataframe=MagicMock())
        mock_cache.get_async = AsyncMock(return_value=mock_entry)

        mock_result = MagicMock(
            processor_result=MagicMock(actions=[MagicMock()]),
            actions_planned=1,
            total_scanned=10,
            excluded_count=0,
        )

        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "true"},
        ):
            with (
                patch(
                    "autom8_asana.reconciliation.engine.run_reconciliation",
                    return_value=mock_result,
                ),
                patch(
                    "autom8_asana.reconciliation.executor.execute_actions",
                    new_callable=AsyncMock,
                    side_effect=RuntimeError("executor boom"),
                ),
            ):
                # Should NOT raise
                await _run_reconciliation_shadow(
                    completed_entities=["unit", "offer"],
                    get_project_gid=_get_project_gid,
                    cache=mock_cache,
                    invocation_id="test-err-2",
                )

    @pytest.mark.asyncio
    async def test_report_exception_is_caught(self) -> None:
        """Exception in report -> caught, logged, no crash."""
        mock_cache = MagicMock()
        mock_entry = _make_cache_entry(dataframe=MagicMock())
        mock_cache.get_async = AsyncMock(return_value=mock_entry)

        mock_result = MagicMock(
            processor_result=MagicMock(actions=[]),
            actions_planned=0,
            total_scanned=5,
            excluded_count=0,
        )

        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "true"},
        ):
            with (
                patch(
                    "autom8_asana.reconciliation.engine.run_reconciliation",
                    return_value=mock_result,
                ),
                patch(
                    "autom8_asana.reconciliation.executor.execute_actions",
                    new_callable=AsyncMock,
                ),
                patch(
                    "autom8_asana.reconciliation.report.build_report",
                    side_effect=ValueError("report boom"),
                ),
            ):
                # Should NOT raise
                await _run_reconciliation_shadow(
                    completed_entities=["unit", "offer"],
                    get_project_gid=_get_project_gid,
                    cache=mock_cache,
                    invocation_id="test-err-3",
                )

    @pytest.mark.asyncio
    async def test_cache_exception_is_caught(self) -> None:
        """Exception in cache.get_async -> caught, logged, no crash."""
        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(side_effect=ConnectionError("cache down"))

        with patch.dict(
            "os.environ",
            {"ASANA_RECONCILIATION_SHADOW_ENABLED": "true"},
        ):
            # Should NOT raise
            await _run_reconciliation_shadow(
                completed_entities=["unit", "offer"],
                get_project_gid=_get_project_gid,
                cache=mock_cache,
                invocation_id="test-err-4",
            )
