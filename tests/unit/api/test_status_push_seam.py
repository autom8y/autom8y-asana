"""Tests for the SD-02 account-status push live execution home (sprint-C6).

Diagnosis (SPIKE-sd02-empty-registry-diagnosis-2026-07-08, H1 SUPPORTED): the
push existed only in the schedule-paused cache-warmer Lambda entity-type warm
lane, so prod account_status has held 0 rows since creation. The fix gives the
push two ECS firing points: a one-shot at the tail of progressive preload and
a periodic loop at the ratified 4h cadence.

Covers TDD sprint-C6 T1 (a: preload wiring, b: real seam -> POST payload,
c: loop lifecycle) and T4 (fatal isolation).
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from autom8_asana.api.status_push import (
    DEFAULT_STATUS_PUSH_INTERVAL_SECONDS,
    AccountStatusPushLoop,
    push_account_status_snapshot,
)

_STATUS_PUSH_MODULE = "autom8_asana.api.status_push"
_PROGRESSIVE_MODULE = "autom8_asana.api.preload.progressive"

#: Unit project GID -- the ONE default-warm-set project present in
#: PIPELINE_TYPE_BY_PROJECT_GID (gid_push.py), so extraction yields rows.
_UNIT_PROJECT_GID = "1201081073731555"


# ---------------------------------------------------------------------------
# Helpers (fixture style mirrors tests/integration/api/test_preload_manifest_check.py)
# ---------------------------------------------------------------------------


@dataclass
class _FakeEntityConfig:
    """Minimal stand-in for EntityProjectConfig."""

    entity_type: str
    project_gid: str
    project_name: str = "Test Project"
    schema_task_type: str | None = None


def _make_mock_app(project_configs: list[_FakeEntityConfig]) -> MagicMock:
    """Build a mock FastAPI app whose entity_project_registry yields *configs*."""
    registry = MagicMock()
    registry.is_ready.return_value = True
    registry.get_all_entity_types.return_value = [c.entity_type for c in project_configs]
    registry.get_config.side_effect = lambda et: next(
        (c for c in project_configs if c.entity_type == et), None
    )

    app = MagicMock()
    app.state.entity_project_registry = registry
    return app


def _make_mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.s3.bucket = "test-bucket"
    settings.s3.region = "us-east-1"
    settings.s3.endpoint_url = None
    settings.is_production = True
    settings.autom8y_env.value = "production"
    return settings


def _make_mock_persistence() -> MagicMock:
    """SectionPersistence mock in the manifest-exists branch."""
    persistence = MagicMock()
    persistence.is_available = True
    persistence.get_manifest_async = AsyncMock(return_value=MagicMock())
    persistence.__aenter__ = AsyncMock(return_value=persistence)
    persistence.__aexit__ = AsyncMock(return_value=False)
    return persistence


def _make_mock_builder_result(total_rows: int = 3) -> MagicMock:
    import polars as pl

    result = MagicMock()
    result.total_rows = total_rows
    result.sections_succeeded = 1
    result.sections_resumed = 0
    result.watermark = datetime.now(UTC)
    result.dataframe = pl.DataFrame({"gid": ["1"] * total_rows})
    return result


def _make_unit_frame():
    """A small unit frame whose rows classify ACTIVE under UNIT_CLASSIFIER."""
    import polars as pl

    return pl.DataFrame(
        {
            "office_phone": ["+15551230001", "+15551230002"],
            "vertical": ["chiropractor", "chiropractor"],
            "section": ["Active", "Month 1"],
        }
    )


def _make_fake_cache(dataframe) -> MagicMock:
    entry = MagicMock()
    entry.dataframe = dataframe
    cache = MagicMock()
    cache.get_async = AsyncMock(return_value=entry)
    return cache


def _make_ready_registry(entity_type: str = "unit", project_gid: str = _UNIT_PROJECT_GID):
    registry = MagicMock()
    registry.is_ready.return_value = True
    registry.get_all_entity_types.return_value = [entity_type]
    config = MagicMock()
    config.project_gid = project_gid
    registry.get_config.side_effect = lambda et: config if et == entity_type else None
    return registry


_PATCHES_COMMON = {
    "bot_pat": "autom8_asana.auth.bot_pat.get_bot_pat",
    "workspace": "autom8_asana.config.get_workspace_gid",
    "settings": "autom8_asana.settings.get_settings",
    "s3_storage_cls": "autom8_asana.dataframes.storage.S3DataFrameStorage",
    "s3_retry": "autom8_asana.dataframes.storage.create_s3_retry_orchestrator",
    "section_persist": "autom8_asana.dataframes.section_persistence.SectionPersistence",
    "watermark_repo": "autom8_asana.dataframes.watermark.get_watermark_repo",
    "df_cache": "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
    "set_ready": "autom8_asana.api.routes.health.set_cache_ready",
    "asana_client": "autom8_asana.AsanaClient",
    "builder_cls": "autom8_asana.dataframes.builders.progressive.ProgressiveProjectBuilder",
    "get_schema": "autom8_asana.dataframes.models.registry.get_schema",
    "resolver": "autom8_asana.dataframes.resolver.DefaultCustomFieldResolver",
    "cpf": "autom8_asana.cache.integration.factory.CacheProviderFactory",
    "cache_config": "autom8_asana.config.CacheConfig",
    "cascade_warm_phases": "autom8_asana.dataframes.cascade_utils.cascade_warm_phases",
    "get_cascade_providers": "autom8_asana.dataframes.cascade_utils.get_cascade_providers",
}


# ---------------------------------------------------------------------------
# T1(a) -- wiring: the preload tail fires the push exactly once
# ---------------------------------------------------------------------------


class TestPreloadTailFiresStatusPush:
    """The push FIRES on the live preload lane (fake seam, real preload path)."""

    async def test_preload_tail_calls_push_with_preload_trigger(self) -> None:
        """_preload_dataframe_cache_progressive awaits the seam once, trigger='preload'."""
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )

        entity_config = _FakeEntityConfig(entity_type="unit", project_gid="proj-111")
        app = _make_mock_app([entity_config])
        mock_settings = _make_mock_settings()
        mock_persistence = _make_mock_persistence()
        mock_df_storage = MagicMock()
        mock_df_storage.is_available = True
        mock_df_storage.load_dataframe = AsyncMock(return_value=(None, None))
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_progressive_async = AsyncMock(
            return_value=_make_mock_builder_result()
        )

        with (
            patch(_PATCHES_COMMON["bot_pat"], return_value="fake-pat"),
            patch(_PATCHES_COMMON["workspace"], return_value="ws-001"),
            patch(_PATCHES_COMMON["settings"], return_value=mock_settings),
            patch(_PATCHES_COMMON["s3_storage_cls"], return_value=mock_df_storage),
            patch(_PATCHES_COMMON["s3_retry"]),
            patch(_PATCHES_COMMON["section_persist"], return_value=mock_persistence),
            patch(_PATCHES_COMMON["watermark_repo"]) as mock_wm_fn,
            patch(_PATCHES_COMMON["df_cache"]) as mock_cache_fn,
            patch(_PATCHES_COMMON["set_ready"]),
            patch(_PATCHES_COMMON["asana_client"]) as MockClient,
            patch(_PATCHES_COMMON["builder_cls"], return_value=mock_builder_instance),
            patch(_PATCHES_COMMON["get_schema"]),
            patch(_PATCHES_COMMON["resolver"]),
            patch(_PATCHES_COMMON["cpf"]),
            patch(_PATCHES_COMMON["cache_config"]),
            patch(_PATCHES_COMMON["cascade_warm_phases"], return_value=[["unit"]]),
            patch(_PATCHES_COMMON["get_cascade_providers"], return_value=set()),
            patch(
                f"{_STATUS_PUSH_MODULE}.push_account_status_snapshot",
                new_callable=AsyncMock,
            ) as mock_push_seam,
        ):
            mock_client_cm = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_cm)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_wm_fn.return_value = MagicMock()
            mock_cache_fn.return_value = AsyncMock()

            await _preload_dataframe_cache_progressive(app)

            mock_push_seam.assert_awaited_once_with(trigger="preload")


# ---------------------------------------------------------------------------
# T1(b) -- seam: real push_account_status_snapshot builds a real POST payload
# ---------------------------------------------------------------------------


class TestPushAccountStatusSnapshotSeam:
    """Real seam with fake registry + fake cache -> real extraction -> recorder."""

    async def test_seam_posts_full_snapshot_to_account_status_sync(self) -> None:
        """The seam produces a POST to /api/v1/account-status/sync with
        non-empty entries and entry_count == len(entries)."""
        registry = _make_ready_registry()
        cache = _make_fake_cache(_make_unit_frame())

        env = {
            "AUTOM8Y_DATA_URL": "http://data.internal.test",
            "AUTOM8Y_DATA_API_KEY": "test-token-not-a-secret",
            "STATUS_PUSH_ENABLED": "true",
        }

        with (
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=registry,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=cache,
            ),
            patch(
                "autom8_asana.services.gid_push._push_to_data_service",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_transport,
            patch("autom8_asana.services.gid_push.emit_metric"),
            patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric"),
            patch.dict(os.environ, env),
        ):
            await push_account_status_snapshot(trigger="preload")

        mock_transport.assert_awaited_once()
        kwargs = mock_transport.call_args.kwargs
        assert kwargs["endpoint_path"] == "/api/v1/account-status/sync"
        payload = kwargs["payload"]
        assert payload["entries"], "expected a non-empty snapshot"
        assert payload["entry_count"] == len(payload["entries"])
        # ACTIVE-scoped registry: every pushed row is active/activating unit rows
        assert {e["pipeline_type"] for e in payload["entries"]} == {"unit"}

    async def test_seam_skips_when_cache_unready(self) -> None:
        """cache=None -> status_push_skipped{ecs_cache_or_registry_unready}, no push."""
        registry = _make_ready_registry()

        with (
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=registry,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=None,
            ),
            patch(
                "autom8_asana.lambda_handlers.push_orchestrator._push_account_status_for_completed_entities",
                new_callable=AsyncMock,
            ) as mock_orchestrator,
            patch(f"{_STATUS_PUSH_MODULE}.logger") as mock_logger,
        ):
            await push_account_status_snapshot(trigger="interval")

        mock_orchestrator.assert_not_awaited()
        skip_calls = [
            c for c in mock_logger.info.call_args_list if c.args[0] == "status_push_skipped"
        ]
        assert skip_calls, "expected status_push_skipped to be logged"
        assert skip_calls[0].kwargs["extra"]["reason"] == "ecs_cache_or_registry_unready"
        assert skip_calls[0].kwargs["extra"]["trigger"] == "interval"

    async def test_seam_invocation_id_carries_ecs_lane_prefix(self) -> None:
        """invocation_id is prefixed ecs-{trigger}- for lane visibility."""
        registry = _make_ready_registry()
        cache = _make_fake_cache(_make_unit_frame())

        with (
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=registry,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=cache,
            ),
            patch(
                "autom8_asana.lambda_handlers.push_orchestrator._push_account_status_for_completed_entities",
                new_callable=AsyncMock,
            ) as mock_orchestrator,
        ):
            await push_account_status_snapshot(trigger="interval")

        mock_orchestrator.assert_awaited_once()
        invocation_id = mock_orchestrator.call_args.kwargs["invocation_id"]
        assert invocation_id.startswith("ecs-interval-")


# ---------------------------------------------------------------------------
# T1(c) -- loop lifecycle
# ---------------------------------------------------------------------------


class TestAccountStatusPushLoop:
    """Loop fires on interval with trigger='interval'; stop() cancels cleanly."""

    async def test_loop_fires_and_stops_cleanly(self) -> None:
        with patch(
            f"{_STATUS_PUSH_MODULE}.push_account_status_snapshot",
            new_callable=AsyncMock,
        ) as mock_seam:
            loop = AccountStatusPushLoop(interval_seconds=0.01)
            task = loop.start()
            assert task is not None
            await asyncio.sleep(0.08)
            await loop.stop()

        assert mock_seam.await_count >= 1
        mock_seam.assert_awaited_with(trigger="interval")
        assert task.done()

    async def test_loop_sleeps_before_first_push(self) -> None:
        """First cycle sleeps first -- the startup push is the preload tail's job."""
        with patch(
            f"{_STATUS_PUSH_MODULE}.push_account_status_snapshot",
            new_callable=AsyncMock,
        ) as mock_seam:
            loop = AccountStatusPushLoop(interval_seconds=60.0)
            loop.start()
            await asyncio.sleep(0)  # let the task start
            await loop.stop()

        mock_seam.assert_not_awaited()

    async def test_nonpositive_interval_disables_loop(self) -> None:
        loop = AccountStatusPushLoop(interval_seconds=0)
        assert loop.start() is None

        with patch.dict(os.environ, {"STATUS_PUSH_INTERVAL_SECONDS": "-1"}):
            env_loop = AccountStatusPushLoop()
        assert env_loop.start() is None

    def test_default_interval_is_ratified_four_hours(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "STATUS_PUSH_INTERVAL_SECONDS"}
        with patch.dict(os.environ, env, clear=True):
            loop = AccountStatusPushLoop()
        assert loop._interval == DEFAULT_STATUS_PUSH_INTERVAL_SECONDS == 14400.0

    def test_unparseable_interval_falls_back_to_default(self) -> None:
        with patch.dict(os.environ, {"STATUS_PUSH_INTERVAL_SECONDS": "four-hours"}):
            loop = AccountStatusPushLoop()
        assert loop._interval == DEFAULT_STATUS_PUSH_INTERVAL_SECONDS


# ---------------------------------------------------------------------------
# T4 -- fatal isolation
# ---------------------------------------------------------------------------


class TestFatalIsolation:
    """An orchestrator crash degrades to status_push_fatal_error; nothing escapes."""

    async def test_orchestrator_crash_never_escapes_seam(self) -> None:
        registry = _make_ready_registry()
        cache = _make_fake_cache(_make_unit_frame())

        with (
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=registry,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=cache,
            ),
            patch(
                "autom8_asana.lambda_handlers.push_orchestrator._push_account_status_for_completed_entities",
                new_callable=AsyncMock,
                side_effect=RuntimeError("orchestrator exploded"),
            ),
            patch(f"{_STATUS_PUSH_MODULE}.logger") as mock_logger,
        ):
            # Must not raise -- BROAD-CATCH isolation
            await push_account_status_snapshot(trigger="preload")

        fatal_calls = [
            c for c in mock_logger.error.call_args_list if c.args[0] == "status_push_fatal_error"
        ]
        assert fatal_calls, "expected status_push_fatal_error"
        extra = fatal_calls[0].kwargs["extra"]
        assert extra["trigger"] == "preload"
        assert extra["error_type"] == "RuntimeError"

    async def test_loop_survives_seam_crash(self) -> None:
        """A crashing cycle does not kill the loop task (the seam absorbs it)."""
        registry = MagicMock()
        registry.is_ready.side_effect = RuntimeError("registry exploded")

        with (
            patch(
                "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                return_value=registry,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                return_value=MagicMock(),
            ),
            patch(f"{_STATUS_PUSH_MODULE}.logger"),
        ):
            loop = AccountStatusPushLoop(interval_seconds=0.01)
            task = loop.start()
            assert task is not None
            await asyncio.sleep(0.05)
            # The loop task is still alive despite every cycle raising inside
            # the seam (and being absorbed there).
            assert not task.done()
            await loop.stop()


# ---------------------------------------------------------------------------
# Lifespan contract: loop object is stored on app.state (wiring shape)
# ---------------------------------------------------------------------------


class TestLoopStartIdempotence:
    async def test_start_twice_returns_same_task(self) -> None:
        with patch(
            f"{_STATUS_PUSH_MODULE}.push_account_status_snapshot",
            new_callable=AsyncMock,
        ):
            loop = AccountStatusPushLoop(interval_seconds=60.0)
            task1 = loop.start()
            task2 = loop.start()
            assert task1 is task2
            await loop.stop()

    async def test_stop_without_start_is_noop(self) -> None:
        loop = AccountStatusPushLoop(interval_seconds=60.0)
        await loop.stop()  # must not raise
