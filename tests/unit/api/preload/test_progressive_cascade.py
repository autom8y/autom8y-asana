"""Tests for cascade validation on S3 fast-path in progressive preload.

When the S3 fast-path loads a parquet directly into cache, it previously
bypassed cascade validation.  These tests verify:

WS-2: Business fast-path populates shared_store with task dicts so
      downstream entities can resolve cascading fields.
WS-1: Non-Business fast-path runs validate_cascade_fields_async to fix
      null cascade fields using data from the shared_store.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call, patch

import polars as pl
import pytest

from autom8_asana.api.preload.progressive import (
    _dataframe_to_task_dicts,
    _has_cascade_fields,
)
from autom8_asana.api.routes.health import set_cache_ready
from autom8_asana.dataframes.builders.cascade_validator import (
    CascadeValidationResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_cache_ready():
    set_cache_ready(True)
    yield
    set_cache_ready(True)


def _make_entity_registry(
    *,
    entity_types: list[tuple[str, str, str]] | None = None,
) -> MagicMock:
    """Create a mock EntityProjectRegistry.

    Args:
        entity_types: List of (entity_type, project_gid, project_name).
            Defaults to business + unit.
    """
    from autom8_asana.services.resolver import EntityProjectConfig

    if entity_types is None:
        entity_types = [
            ("business", "proj_business", "Business"),
            ("unit", "proj_unit", "Business Units"),
        ]

    registry = MagicMock()
    registry.is_ready.return_value = True
    registry.get_all_entity_types.return_value = [et[0] for et in entity_types]

    def _get_config(etype: str) -> EntityProjectConfig | None:
        for et, gid, name in entity_types:
            if et == etype:
                return EntityProjectConfig(entity_type=et, project_gid=gid, project_name=name)
        return None

    registry.get_config.side_effect = _get_config
    return registry


def _make_mock_app(registry: MagicMock) -> MagicMock:
    app = MagicMock()
    app.state.entity_project_registry = registry
    return app


def _make_schema(*, has_cascade: bool = False) -> MagicMock:
    schema = MagicMock()
    schema.has_cascade_columns.return_value = has_cascade
    return schema


def _build_patch_stack(  # noqa: PLR0913
    mock_persistence: MagicMock,
    mock_df_persistence: MagicMock,
    mock_dataframe_cache: MagicMock | None = None,
    mock_watermark_repo: MagicMock | None = None,
    mock_shared_store: MagicMock | None = None,
    schemas: dict[str, MagicMock] | None = None,
    env_overrides: dict[str, str] | None = None,
    settings_overrides: dict[str, object] | None = None,
    cascade_providers: dict[str, dict[str, str]] | None = None,
) -> contextlib.ExitStack:
    """Build patch stack for cascade preload tests.

    Args:
        schemas: Mapping of PascalCase entity type to mock schema.
            E.g., ``{"Business": schema_biz, "Unit": schema_unit}``.
        cascade_providers: Mapping of entity_type to field mapping for
            ``is_cascade_provider`` / ``cascade_provider_field_mapping``.
            E.g., ``{"business": {"office_phone": "Office Phone"}}``.
            Default: ``{"business": {"office_phone": "Office Phone"}}``.
    """
    env = {
        "ASANA_WORKSPACE_GID": "workspace-123",
        "ASANA_BOT_PAT": "test-pat",
        "ASANA_CACHE_S3_BUCKET": "test-bucket",
        "ASANA_CACHE_S3_REGION": "us-east-1",
    }
    if env_overrides:
        env.update(env_overrides)

    if mock_dataframe_cache is None:
        mock_dataframe_cache = MagicMock()
        mock_dataframe_cache.put_async = AsyncMock()

    if mock_watermark_repo is None:
        mock_watermark_repo = MagicMock()
        mock_watermark_repo.set_watermark = MagicMock()

    if mock_shared_store is None:
        mock_shared_store = MagicMock()
        mock_shared_store.put_batch_async = AsyncMock(return_value=0)

    # Default schemas: Business has no cascade, Unit has cascade
    if schemas is None:
        schemas = {
            "Business": _make_schema(has_cascade=False),
            "Unit": _make_schema(has_cascade=True),
        }

    # Default cascade providers: Business provides office_phone
    if cascade_providers is None:
        cascade_providers = {"business": {"office_phone": "Office Phone"}}

    def _get_schema(task_type: str) -> MagicMock:
        return schemas.get(task_type, _make_schema(has_cascade=False))

    def _is_cascade_provider(entity_type: str) -> bool:
        return entity_type in cascade_providers

    def _cascade_provider_field_mapping(entity_type: str) -> dict[str, str]:
        return cascade_providers.get(entity_type, {})

    stack = contextlib.ExitStack()
    stack.enter_context(patch.dict("os.environ", env))

    # Patch cascade_utils so they don't hit real entity registry.
    # progressive.py imports these inside the function body via
    # ``from autom8_asana.dataframes.cascade_utils import ...``,
    # so patching the source module is correct.
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.cascade_utils.is_cascade_provider",
            side_effect=_is_cascade_provider,
        )
    )
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.cascade_utils.cascade_provider_field_mapping",
            side_effect=_cascade_provider_field_mapping,
        )
    )
    # Patch cascade_warm_phases so preload ordering doesn't hit real registries.
    # Default: business first, then everything else.
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.cascade_utils.cascade_warm_phases",
            return_value=[
                ["business"],
                ["unit", "offer", "contact", "asset_edit", "asset_edit_holder"],
            ],
        )
    )
    # Patch get_cascade_providers to return empty set so the L2 pre-phase
    # gate passes. These tests focus on fast-path/cascade validation behavior,
    # not on warmup phase ordering which is tested elsewhere.
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.cascade_utils.get_cascade_providers",
            return_value=set(),
        )
    )

    stack.enter_context(patch("autom8_asana.auth.bot_pat.get_bot_pat", return_value="test-pat"))
    stack.enter_context(
        patch(
            "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
            return_value=mock_dataframe_cache,
        )
    )
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.watermark.get_watermark_repo",
            return_value=mock_watermark_repo,
        )
    )
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.models.registry.get_schema",
            side_effect=_get_schema,
        )
    )
    stack.enter_context(patch("autom8_asana.dataframes.resolver.DefaultCustomFieldResolver"))

    # Patch CacheProviderFactory to return our mock store
    mock_factory = MagicMock()
    mock_factory.create_unified_store.return_value = mock_shared_store
    stack.enter_context(
        patch(
            "autom8_asana.cache.integration.factory.CacheProviderFactory",
            mock_factory,
        )
    )

    stack.enter_context(
        patch(
            "autom8_asana.dataframes.section_persistence.SectionPersistence",
            return_value=mock_persistence,
        )
    )

    # Patch S3DataFrameStorage
    mock_storage_cls = MagicMock(return_value=mock_df_persistence)
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.storage.S3DataFrameStorage",
            mock_storage_cls,
        )
    )
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.storage.create_s3_retry_orchestrator",
            return_value=MagicMock(),
        )
    )

    # Mock settings
    mock_settings = MagicMock()
    mock_settings.s3.bucket = "test-bucket"
    mock_settings.s3.region = "us-east-1"
    mock_settings.s3.endpoint_url = None
    mock_settings.is_production = False
    if settings_overrides:
        for key, val in settings_overrides.items():
            setattr(mock_settings, key, val)
    stack.enter_context(
        patch(
            "autom8_asana.settings.get_settings",
            return_value=mock_settings,
        )
    )

    # Builder (won't be called when parquet fallback succeeds)
    stack.enter_context(
        patch(
            "autom8_asana.dataframes.builders.progressive.ProgressiveProjectBuilder",
        )
    )

    # AsanaClient context manager
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_cls = stack.enter_context(patch("autom8_asana.AsanaClient"))
    mock_client_cls.return_value = mock_client

    return stack


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestDataframeToTaskDicts:
    """Tests for _dataframe_to_task_dicts helper."""

    def test_converts_business_df_to_task_dicts(self) -> None:
        df = pl.DataFrame(
            {
                "gid": ["biz-1", "biz-2"],
                "name": ["Acme Corp", "Beta LLC"],
                "office_phone": ["555-1234", "555-5678"],
            },
            schema={"gid": pl.Utf8, "name": pl.Utf8, "office_phone": pl.Utf8},
        )

        result = _dataframe_to_task_dicts(
            df, cascade_field_mapping={"office_phone": "Office Phone"}
        )

        assert len(result) == 2
        assert result[0]["gid"] == "biz-1"
        assert result[0]["parent"] is None
        assert result[0]["custom_fields"] == [{"name": "Office Phone", "display_value": "555-1234"}]
        assert result[1]["gid"] == "biz-2"
        assert result[1]["custom_fields"] == [{"name": "Office Phone", "display_value": "555-5678"}]

    def test_skips_null_gids(self) -> None:
        df = pl.DataFrame(
            {
                "gid": [None, "biz-1"],
                "office_phone": ["555-0000", "555-1111"],
            },
            schema={"gid": pl.Utf8, "office_phone": pl.Utf8},
        )

        result = _dataframe_to_task_dicts(
            df, cascade_field_mapping={"office_phone": "Office Phone"}
        )

        assert len(result) == 1
        assert result[0]["gid"] == "biz-1"

    def test_null_field_value_excluded_from_custom_fields(self) -> None:
        df = pl.DataFrame(
            {
                "gid": ["biz-1"],
                "office_phone": [None],
            },
            schema={"gid": pl.Utf8, "office_phone": pl.Utf8},
        )

        result = _dataframe_to_task_dicts(
            df, cascade_field_mapping={"office_phone": "Office Phone"}
        )

        assert len(result) == 1
        assert result[0]["custom_fields"] == []

    def test_returns_empty_when_no_gid_column(self) -> None:
        df = pl.DataFrame(
            {"name": ["Acme"]},
            schema={"name": pl.Utf8},
        )

        result = _dataframe_to_task_dicts(
            df, cascade_field_mapping={"office_phone": "Office Phone"}
        )

        assert result == []

    def test_handles_missing_mapped_column(self) -> None:
        df = pl.DataFrame(
            {"gid": ["biz-1"], "name": ["Acme"]},
            schema={"gid": pl.Utf8, "name": pl.Utf8},
        )

        result = _dataframe_to_task_dicts(
            df, cascade_field_mapping={"office_phone": "Office Phone"}
        )

        assert len(result) == 1
        assert result[0]["custom_fields"] == []


class TestHasCascadeFields:
    """Tests for _has_cascade_fields helper."""

    def test_returns_true_for_cascade_schema(self) -> None:
        schema = _make_schema(has_cascade=True)
        assert _has_cascade_fields(schema) is True

    def test_returns_false_for_non_cascade_schema(self) -> None:
        schema = _make_schema(has_cascade=False)
        assert _has_cascade_fields(schema) is False


# ---------------------------------------------------------------------------
# Integration tests for process_project fast-path
# ---------------------------------------------------------------------------


class TestBusinessFastPathPopulatesStore:
    """WS-2: Business S3 fast-path populates shared_store."""

    async def test_business_fast_path_populates_shared_store(self) -> None:
        """Business parquet load puts task dicts into shared_store."""
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )

        registry = _make_entity_registry(entity_types=[("business", "proj_biz", "Business")])
        app = _make_mock_app(registry)

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        biz_df = pl.DataFrame(
            {
                "gid": ["biz-1", "biz-2"],
                "name": ["Acme", "Beta"],
                "office_phone": ["555-1234", "555-5678"],
            },
            schema={"gid": pl.Utf8, "name": pl.Utf8, "office_phone": pl.Utf8},
        )
        s3_watermark = datetime.now(UTC) - timedelta(hours=1)

        mock_df_storage = MagicMock()
        mock_df_storage.load_dataframe = AsyncMock(return_value=(biz_df, s3_watermark))

        mock_cache = MagicMock()
        mock_cache.put_async = AsyncMock()

        mock_store = MagicMock()
        mock_store.put_batch_async = AsyncMock(return_value=2)

        with _build_patch_stack(
            mock_persistence,
            mock_df_storage,
            mock_dataframe_cache=mock_cache,
            mock_shared_store=mock_store,
            schemas={"Business": _make_schema(has_cascade=False)},
        ):
            await _preload_dataframe_cache_progressive(app)

        # Verify shared store was populated with Business task dicts
        mock_store.put_batch_async.assert_called_once()
        task_dicts = mock_store.put_batch_async.call_args[0][0]
        assert len(task_dicts) == 2
        assert task_dicts[0]["gid"] == "biz-1"
        assert task_dicts[0]["custom_fields"] == [
            {"name": "Office Phone", "display_value": "555-1234"}
        ]
        assert task_dicts[0]["parent"] is None
        assert task_dicts[1]["gid"] == "biz-2"


class TestBusinessFastPathSkipsCascadeValidation:
    """WS-1 negative: Business does NOT run cascade validation."""

    async def test_business_fast_path_skips_cascade_validation(self) -> None:
        """Business entity is the cascade source, not a target."""
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )

        registry = _make_entity_registry(entity_types=[("business", "proj_biz", "Business")])
        app = _make_mock_app(registry)

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        biz_df = pl.DataFrame(
            {"gid": ["biz-1"], "office_phone": ["555-1234"]},
            schema={"gid": pl.Utf8, "office_phone": pl.Utf8},
        )

        mock_df_storage = MagicMock()
        mock_df_storage.load_dataframe = AsyncMock(return_value=(biz_df, datetime.now(UTC)))

        mock_cache = MagicMock()
        mock_cache.put_async = AsyncMock()

        with _build_patch_stack(
            mock_persistence,
            mock_df_storage,
            mock_dataframe_cache=mock_cache,
        ) as stack:
            mock_validate = stack.enter_context(
                patch(
                    "autom8_asana.dataframes.builders.cascade_validator.validate_cascade_fields_async",
                )
            )
            await _preload_dataframe_cache_progressive(app)

        # validate_cascade_fields_async should NOT have been called
        mock_validate.assert_not_called()


class TestUnitFastPathRunsCascadeValidation:
    """WS-1: Unit S3 fast-path triggers cascade validation."""

    async def test_unit_fast_path_runs_cascade_validation(self) -> None:
        """Unit parquet load runs validate_cascade_fields_async."""
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )

        registry = _make_entity_registry(entity_types=[("unit", "proj_unit", "Business Units")])
        app = _make_mock_app(registry)

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        unit_df = pl.DataFrame(
            {
                "gid": ["unit-1", "unit-2"],
                "office_phone": [None, "555-0000"],
            },
            schema={"gid": pl.Utf8, "office_phone": pl.Utf8},
        )
        s3_watermark = datetime.now(UTC) - timedelta(hours=1)

        mock_df_storage = MagicMock()
        mock_df_storage.load_dataframe = AsyncMock(return_value=(unit_df, s3_watermark))

        mock_cache = MagicMock()
        mock_cache.put_async = AsyncMock()

        cascade_result = CascadeValidationResult(rows_checked=1, rows_stale=0, rows_corrected=0)

        with _build_patch_stack(
            mock_persistence,
            mock_df_storage,
            mock_dataframe_cache=mock_cache,
            schemas={"Unit": _make_schema(has_cascade=True)},
        ) as stack:
            mock_validate = stack.enter_context(
                patch(
                    "autom8_asana.dataframes.builders.cascade_validator.validate_cascade_fields_async",
                    new_callable=AsyncMock,
                    return_value=(unit_df, cascade_result),
                )
            )
            mock_cascade_plugin_cls = stack.enter_context(
                patch(
                    "autom8_asana.dataframes.views.cascade_view.CascadeViewPlugin",
                )
            )
            await _preload_dataframe_cache_progressive(app)

        # validate_cascade_fields_async was called with schema kwarg
        mock_validate.assert_awaited_once()
        call_kwargs = mock_validate.call_args
        assert call_kwargs[1]["project_gid"] == "proj_unit"
        assert call_kwargs[1]["entity_type"] == "unit"
        assert "schema" in call_kwargs[1]

        # DataFrame was still cached
        mock_cache.put_async.assert_called_once()


class TestFastPathCascadeSelfHeals:
    """WS-1 self-heal: corrected DataFrame re-persisted to S3."""

    async def test_fast_path_cascade_self_heals_to_s3(self) -> None:
        """When cascade validation corrects rows, save back to S3."""
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )

        registry = _make_entity_registry(entity_types=[("unit", "proj_unit", "Business Units")])
        app = _make_mock_app(registry)

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        original_df = pl.DataFrame(
            {"gid": ["unit-1"], "office_phone": [None]},
            schema={"gid": pl.Utf8, "office_phone": pl.Utf8},
        )
        corrected_df = pl.DataFrame(
            {"gid": ["unit-1"], "office_phone": ["555-1234"]},
            schema={"gid": pl.Utf8, "office_phone": pl.Utf8},
        )
        s3_watermark = datetime.now(UTC) - timedelta(hours=1)

        mock_df_storage = MagicMock()
        mock_df_storage.load_dataframe = AsyncMock(return_value=(original_df, s3_watermark))
        mock_df_storage.save_dataframe = AsyncMock(return_value=True)

        mock_cache = MagicMock()
        mock_cache.put_async = AsyncMock()

        cascade_result = CascadeValidationResult(rows_checked=1, rows_stale=1, rows_corrected=1)

        with _build_patch_stack(
            mock_persistence,
            mock_df_storage,
            mock_dataframe_cache=mock_cache,
            schemas={"Unit": _make_schema(has_cascade=True)},
        ) as stack:
            stack.enter_context(
                patch(
                    "autom8_asana.dataframes.builders.cascade_validator.validate_cascade_fields_async",
                    new_callable=AsyncMock,
                    return_value=(corrected_df, cascade_result),
                )
            )
            stack.enter_context(
                patch(
                    "autom8_asana.dataframes.views.cascade_view.CascadeViewPlugin",
                )
            )
            await _preload_dataframe_cache_progressive(app)

        # S3 self-heal: save_dataframe was called with corrected data
        mock_df_storage.save_dataframe.assert_awaited_once_with(
            "proj_unit", corrected_df, s3_watermark
        )

        # Corrected DataFrame was cached (not the original)
        put_call = mock_cache.put_async.call_args
        cached_df = put_call[0][2]
        assert cached_df["office_phone"][0] == "555-1234"


class TestFastPathCascadeGracefulDegradation:
    """Cascade validation failures must not block the load."""

    async def test_fast_path_cascade_degrades_gracefully_on_empty_store(
        self,
    ) -> None:
        """Empty store produces zero corrections, no errors."""
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )

        registry = _make_entity_registry(entity_types=[("unit", "proj_unit", "Business Units")])
        app = _make_mock_app(registry)

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        unit_df = pl.DataFrame(
            {"gid": ["unit-1"], "office_phone": [None]},
            schema={"gid": pl.Utf8, "office_phone": pl.Utf8},
        )
        s3_watermark = datetime.now(UTC) - timedelta(hours=1)

        mock_df_storage = MagicMock()
        mock_df_storage.load_dataframe = AsyncMock(return_value=(unit_df, s3_watermark))
        mock_df_storage.save_dataframe = AsyncMock(return_value=True)

        mock_cache = MagicMock()
        mock_cache.put_async = AsyncMock()

        # Zero corrections (empty store, no ancestors)
        cascade_result = CascadeValidationResult(rows_checked=1, rows_stale=0, rows_corrected=0)

        with _build_patch_stack(
            mock_persistence,
            mock_df_storage,
            mock_dataframe_cache=mock_cache,
            schemas={"Unit": _make_schema(has_cascade=True)},
        ) as stack:
            stack.enter_context(
                patch(
                    "autom8_asana.dataframes.builders.cascade_validator.validate_cascade_fields_async",
                    new_callable=AsyncMock,
                    return_value=(unit_df, cascade_result),
                )
            )
            stack.enter_context(
                patch(
                    "autom8_asana.dataframes.views.cascade_view.CascadeViewPlugin",
                )
            )
            await _preload_dataframe_cache_progressive(app)

        # No self-heal (zero corrections)
        mock_df_storage.save_dataframe.assert_not_awaited()

        # DataFrame still loaded into cache
        mock_cache.put_async.assert_called_once()

    async def test_fast_path_cascade_exception_does_not_block_load(
        self,
    ) -> None:
        """Exception in cascade validation still loads the DataFrame."""
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )

        registry = _make_entity_registry(entity_types=[("unit", "proj_unit", "Business Units")])
        app = _make_mock_app(registry)

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        unit_df = pl.DataFrame(
            {"gid": ["unit-1"], "office_phone": [None]},
            schema={"gid": pl.Utf8, "office_phone": pl.Utf8},
        )
        s3_watermark = datetime.now(UTC) - timedelta(hours=1)

        mock_df_storage = MagicMock()
        mock_df_storage.load_dataframe = AsyncMock(return_value=(unit_df, s3_watermark))

        mock_cache = MagicMock()
        mock_cache.put_async = AsyncMock()

        with _build_patch_stack(
            mock_persistence,
            mock_df_storage,
            mock_dataframe_cache=mock_cache,
            schemas={"Unit": _make_schema(has_cascade=True)},
        ) as stack:
            # Cascade validation raises an exception
            stack.enter_context(
                patch(
                    "autom8_asana.dataframes.builders.cascade_validator.validate_cascade_fields_async",
                    new_callable=AsyncMock,
                    side_effect=RuntimeError("cascade exploded"),
                )
            )
            stack.enter_context(
                patch(
                    "autom8_asana.dataframes.views.cascade_view.CascadeViewPlugin",
                )
            )
            await _preload_dataframe_cache_progressive(app)

        # DataFrame was still cached despite cascade failure
        mock_cache.put_async.assert_called_once()
        put_call = mock_cache.put_async.call_args
        assert put_call[0][0] == "proj_unit"
        assert put_call[0][1] == "unit"
        assert len(put_call[0][2]) == 1  # 1 row


class TestUnitFastPathPopulatesStore:
    """Unit entity is a cascade provider AND consumer (both paths fire)."""

    async def test_unit_fast_path_populates_shared_store(self) -> None:
        """Unit parquet load populates shared_store via cascade_provider_field_mapping."""
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )

        registry = _make_entity_registry(entity_types=[("unit", "proj_unit", "Business Units")])
        app = _make_mock_app(registry)

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        unit_df = pl.DataFrame(
            {
                "gid": ["unit-1", "unit-2"],
                "vertical": ["Chiro", "Dental"],
                "mrr": ["500", "1000"],
            },
            schema={"gid": pl.Utf8, "vertical": pl.Utf8, "mrr": pl.Utf8},
        )
        s3_watermark = datetime.now(UTC) - timedelta(hours=1)

        mock_df_storage = MagicMock()
        mock_df_storage.load_dataframe = AsyncMock(return_value=(unit_df, s3_watermark))

        mock_cache = MagicMock()
        mock_cache.put_async = AsyncMock()

        mock_store = MagicMock()
        mock_store.put_batch_async = AsyncMock(return_value=2)

        cascade_result = CascadeValidationResult(rows_checked=0, rows_stale=0, rows_corrected=0)

        with _build_patch_stack(
            mock_persistence,
            mock_df_storage,
            mock_dataframe_cache=mock_cache,
            mock_shared_store=mock_store,
            schemas={"Unit": _make_schema(has_cascade=True)},
            cascade_providers={
                "unit": {"vertical": "Vertical", "mrr": "MRR"},
            },
        ) as stack:
            stack.enter_context(
                patch(
                    "autom8_asana.dataframes.builders.cascade_validator.validate_cascade_fields_async",
                    new_callable=AsyncMock,
                    return_value=(unit_df, cascade_result),
                )
            )
            stack.enter_context(
                patch(
                    "autom8_asana.dataframes.views.cascade_view.CascadeViewPlugin",
                )
            )
            await _preload_dataframe_cache_progressive(app)

        # Shared store was populated with Unit task dicts
        mock_store.put_batch_async.assert_called_once()
        task_dicts = mock_store.put_batch_async.call_args[0][0]
        assert len(task_dicts) == 2
        assert task_dicts[0]["gid"] == "unit-1"
        # Check that field mapping used Vertical and MRR
        field_names = {cf["name"] for cf in task_dicts[0]["custom_fields"]}
        assert "Vertical" in field_names
        assert "MRR" in field_names

    async def test_unit_fast_path_populates_and_validates(self) -> None:
        """Unit does BOTH store population AND cascade validation."""
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )

        registry = _make_entity_registry(entity_types=[("unit", "proj_unit", "Business Units")])
        app = _make_mock_app(registry)

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        unit_df = pl.DataFrame(
            {
                "gid": ["unit-1"],
                "office_phone": [None],
                "vertical": ["Chiro"],
            },
            schema={
                "gid": pl.Utf8,
                "office_phone": pl.Utf8,
                "vertical": pl.Utf8,
            },
        )
        s3_watermark = datetime.now(UTC) - timedelta(hours=1)

        mock_df_storage = MagicMock()
        mock_df_storage.load_dataframe = AsyncMock(return_value=(unit_df, s3_watermark))

        mock_cache = MagicMock()
        mock_cache.put_async = AsyncMock()

        mock_store = MagicMock()
        mock_store.put_batch_async = AsyncMock(return_value=1)

        cascade_result = CascadeValidationResult(rows_checked=1, rows_stale=0, rows_corrected=0)

        with _build_patch_stack(
            mock_persistence,
            mock_df_storage,
            mock_dataframe_cache=mock_cache,
            mock_shared_store=mock_store,
            schemas={"Unit": _make_schema(has_cascade=True)},
            cascade_providers={
                "unit": {"vertical": "Vertical"},
            },
        ) as stack:
            mock_validate = stack.enter_context(
                patch(
                    "autom8_asana.dataframes.builders.cascade_validator.validate_cascade_fields_async",
                    new_callable=AsyncMock,
                    return_value=(unit_df, cascade_result),
                )
            )
            stack.enter_context(
                patch(
                    "autom8_asana.dataframes.views.cascade_view.CascadeViewPlugin",
                )
            )
            await _preload_dataframe_cache_progressive(app)

        # Store was populated (provider path)
        mock_store.put_batch_async.assert_called_once()

        # Cascade validation also ran (consumer path)
        mock_validate.assert_awaited_once()


class TestCascadeValidationPassesSchema:
    """Verify the schema kwarg is forwarded to validate_cascade_fields_async."""

    async def test_cascade_validation_passes_schema(self) -> None:
        """The schema kwarg must be forwarded from preload to validator."""
        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )

        registry = _make_entity_registry(entity_types=[("unit", "proj_unit", "Business Units")])
        app = _make_mock_app(registry)

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.get_manifest_async = AsyncMock(return_value=None)
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        unit_df = pl.DataFrame(
            {"gid": ["unit-1"], "office_phone": [None]},
            schema={"gid": pl.Utf8, "office_phone": pl.Utf8},
        )
        s3_watermark = datetime.now(UTC) - timedelta(hours=1)

        mock_df_storage = MagicMock()
        mock_df_storage.load_dataframe = AsyncMock(return_value=(unit_df, s3_watermark))

        mock_cache = MagicMock()
        mock_cache.put_async = AsyncMock()

        unit_schema = _make_schema(has_cascade=True)

        cascade_result = CascadeValidationResult(rows_checked=1, rows_stale=0, rows_corrected=0)

        with _build_patch_stack(
            mock_persistence,
            mock_df_storage,
            mock_dataframe_cache=mock_cache,
            schemas={"Unit": unit_schema},
        ) as stack:
            mock_validate = stack.enter_context(
                patch(
                    "autom8_asana.dataframes.builders.cascade_validator.validate_cascade_fields_async",
                    new_callable=AsyncMock,
                    return_value=(unit_df, cascade_result),
                )
            )
            stack.enter_context(
                patch(
                    "autom8_asana.dataframes.views.cascade_view.CascadeViewPlugin",
                )
            )
            await _preload_dataframe_cache_progressive(app)

        # Verify schema was passed as keyword argument
        mock_validate.assert_awaited_once()
        call_kwargs = mock_validate.call_args[1]
        assert call_kwargs["schema"] is unit_schema
