"""Unit tests for cascade_validator module.

Per TDD-CASCADE-FAILURE-FIXES-001 section 7.3: Tests post-build cascade
validation that detects and corrects stale cascade-critical fields in
merged DataFrames.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest  # noqa: TC002

from autom8_asana.dataframes.builders.cascade_validator import (
    CASCADE_NULL_ERROR_THRESHOLD,
    CASCADE_NULL_WARN_THRESHOLD,
    CascadeValidationResult,
    audit_cascade_key_nulls,
    validate_cascade_fields_async,
)


def _make_office_phone_schema() -> MagicMock:
    """Create a mock schema with office_phone as a cascade column.

    Returns a mock DataFrameSchema where ``get_cascade_columns()``
    returns ``[("office_phone", "Office Phone")]``.
    """
    schema = MagicMock()
    schema.get_cascade_columns.return_value = [("office_phone", "Office Phone")]
    return schema


def _make_mock_store(
    *,
    ancestor_chains: dict[str, list[str]] | None = None,
    parent_chains: dict[str, list[dict]] | None = None,
) -> MagicMock:
    """Create a mock UnifiedTaskStore with hierarchy index and parent chain.

    Args:
        ancestor_chains: Mapping of gid -> list of ancestor GIDs for hierarchy index.
        parent_chains: Mapping of gid -> list of parent data dicts for get_parent_chain_async.

    Returns:
        Mock store with configured hierarchy index and parent chain behavior.
    """
    ancestor_chains = ancestor_chains or {}
    parent_chains = parent_chains or {}

    mock_hierarchy = MagicMock()
    mock_hierarchy.get_ancestor_chain.side_effect = lambda gid, max_depth=5: ancestor_chains.get(
        gid, []
    )

    mock_store = MagicMock()
    mock_store.get_hierarchy_index.return_value = mock_hierarchy
    mock_store.get_parent_chain_async = AsyncMock(
        side_effect=lambda gid, **kw: parent_chains.get(gid, [])
    )

    return mock_store


def _make_mock_cascade_plugin(
    *,
    field_values: dict[str, dict[str, str | None]] | None = None,
) -> MagicMock:
    """Create a mock CascadeViewPlugin.

    Args:
        field_values: Mapping of parent_gid -> {field_name: value}.
            Uses parent_data["gid"] to key lookups.

    Returns:
        Mock cascade plugin with configured field value extraction.
    """
    field_values = field_values or {}

    mock_plugin = MagicMock()

    def _get_value(task_data: dict, field_name: str) -> str | None:
        gid = task_data.get("gid", "")
        return field_values.get(gid, {}).get(field_name)

    mock_plugin._get_custom_field_value_from_dict.side_effect = _get_value

    return mock_plugin


async def test_validation_corrects_null_office_phone() -> None:
    """1 row with null office_phone, store resolves from parent chain."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1"],
            "name": ["Offer 1"],
            "office_phone": [None],
            "section_gid": ["sec-1"],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
            "section_gid": pl.Utf8,
        },
    )

    store = _make_mock_store(
        ancestor_chains={"task-1": ["holder-1", "business-1"]},
        parent_chains={
            "task-1": [
                {"gid": "holder-1", "custom_fields": []},
                {
                    "gid": "business-1",
                    "custom_fields": [{"name": "Office Phone", "display_value": "555-1234"}],
                },
            ]
        },
    )

    plugin = _make_mock_cascade_plugin(
        field_values={
            "holder-1": {"Office Phone": None},
            "business-1": {"Office Phone": "555-1234"},
        }
    )

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 1
    assert result.rows_stale == 1
    assert result.rows_corrected == 1
    assert result.sections_affected == {"sec-1"}
    assert corrected_df["office_phone"][0] == "555-1234"


async def test_validation_noop_when_all_populated() -> None:
    """No null rows, assert unchanged."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1", "task-2"],
            "name": ["Offer 1", "Offer 2"],
            "office_phone": ["555-1111", "555-2222"],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
        },
    )

    store = _make_mock_store()
    plugin = _make_mock_cascade_plugin()

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 0
    assert result.rows_stale == 0
    assert result.rows_corrected == 0
    assert corrected_df["office_phone"].to_list() == ["555-1111", "555-2222"]


async def test_validation_noop_when_no_ancestors() -> None:
    """Null row but no ancestors in hierarchy, assert not corrected."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1"],
            "name": ["Offer 1"],
            "office_phone": [None],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
        },
    )

    # No ancestors registered in hierarchy
    store = _make_mock_store(
        ancestor_chains={},
        parent_chains={},
    )
    plugin = _make_mock_cascade_plugin()

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 1
    assert result.rows_stale == 0
    assert result.rows_corrected == 0
    assert corrected_df["office_phone"][0] is None


async def test_validation_noop_when_ancestors_also_null() -> None:
    """Ancestors exist but also have null for the cascade field."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1"],
            "name": ["Offer 1"],
            "office_phone": [None],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
        },
    )

    store = _make_mock_store(
        ancestor_chains={"task-1": ["holder-1", "business-1"]},
        parent_chains={
            "task-1": [
                {"gid": "holder-1", "custom_fields": []},
                {"gid": "business-1", "custom_fields": []},
            ]
        },
    )

    # All ancestors return None for Office Phone
    plugin = _make_mock_cascade_plugin(
        field_values={
            "holder-1": {"Office Phone": None},
            "business-1": {"Office Phone": None},
        }
    )

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 1
    assert result.rows_stale == 0
    assert result.rows_corrected == 0
    assert corrected_df["office_phone"][0] is None


async def test_validation_multiple_rows() -> None:
    """3 rows with null, 2 resolvable, assert 2 corrected."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1", "task-2", "task-3"],
            "name": ["Offer 1", "Offer 2", "Offer 3"],
            "office_phone": [None, None, None],
            "section_gid": ["sec-1", "sec-1", "sec-2"],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
            "section_gid": pl.Utf8,
        },
    )

    store = _make_mock_store(
        ancestor_chains={
            "task-1": ["holder-1", "business-1"],
            "task-2": ["holder-2", "business-1"],
            "task-3": ["holder-3"],  # ancestors exist but no parent chain resolves
        },
        parent_chains={
            "task-1": [
                {"gid": "holder-1", "custom_fields": []},
                {
                    "gid": "business-1",
                    "custom_fields": [
                        {"name": "Office Phone", "text_value": "555-9999"},
                    ],
                },
            ],
            "task-2": [
                {"gid": "holder-2", "custom_fields": []},
                {
                    "gid": "business-1",
                    "custom_fields": [
                        {"name": "Office Phone", "text_value": "555-9999"},
                    ],
                },
            ],
            "task-3": [
                {"gid": "holder-3", "custom_fields": []},
            ],
        },
    )

    plugin = _make_mock_cascade_plugin()

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 3
    assert result.rows_stale == 2
    assert result.rows_corrected == 2
    # task-3 was NOT corrected (holder-3 has no Office Phone), so sec-2 is
    # not in sections_affected. Only sec-1 (task-1, task-2 both corrected).
    assert result.sections_affected == {"sec-1"}
    assert corrected_df["office_phone"][0] == "555-9999"
    assert corrected_df["office_phone"][1] == "555-9999"
    assert corrected_df["office_phone"][2] is None


async def test_validation_skips_when_no_gid_column() -> None:
    """DataFrame without gid column should return immediately."""
    merged_df = pl.DataFrame(
        {
            "name": ["Offer 1"],
            "office_phone": [None],
        },
        schema={
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
        },
    )

    store = _make_mock_store()
    plugin = _make_mock_cascade_plugin()

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 0
    assert result.rows_corrected == 0


async def test_validation_skips_when_column_not_present() -> None:
    """DataFrame without cascade column should return immediately."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1"],
            "name": ["Offer 1"],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
        },
    )

    store = _make_mock_store(
        ancestor_chains={"task-1": ["holder-1"]},
    )
    plugin = _make_mock_cascade_plugin()

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 0
    assert result.rows_corrected == 0


async def test_validation_skips_when_parent_chain_empty() -> None:
    """Ancestors exist in hierarchy but parent chain returns empty."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1"],
            "name": ["Offer 1"],
            "office_phone": [None],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
        },
    )

    # Hierarchy says ancestors exist, but store returns empty parent chain
    store = _make_mock_store(
        ancestor_chains={"task-1": ["holder-1", "business-1"]},
        parent_chains={"task-1": []},
    )
    plugin = _make_mock_cascade_plugin()

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.rows_checked == 1
    assert result.rows_stale == 0
    assert result.rows_corrected == 0
    assert corrected_df["office_phone"][0] is None


async def test_validation_result_duration_populated() -> None:
    """Verify duration_ms is populated on the result."""
    merged_df = pl.DataFrame(
        {
            "gid": ["task-1"],
            "name": ["Offer 1"],
            "office_phone": ["555-1111"],
        },
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "office_phone": pl.Utf8,
        },
    )

    store = _make_mock_store()
    plugin = _make_mock_cascade_plugin()

    _, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=_make_office_phone_schema(),
    )

    assert result.duration_ms >= 0.0


def test_feature_flag_default_is_enabled() -> None:
    """section_cascade_validation defaults to '1' (enabled).

    Per TDD-CASCADE-FAILURE-FIXES-001 section 5.2: Feature flag
    section_cascade_validation defaults to enabled. Setting to '0' disables.
    """
    from autom8_asana.settings import Settings

    settings = Settings()
    assert settings.runtime.section_cascade_validation == "1"


def test_feature_flag_disabled_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """When ASANA_RUNTIME_SECTION_CASCADE_VALIDATION=0, the setting reflects disabled state."""
    from autom8_asana.settings import Settings, reset_settings

    reset_settings()
    monkeypatch.setenv("ASANA_RUNTIME_SECTION_CASCADE_VALIDATION", "0")
    reset_settings()  # Force fresh settings with new env var

    settings = Settings()
    assert settings.runtime.section_cascade_validation == "0"


async def test_schema_driven_validates_all_cascade_columns() -> None:
    """When schema is passed, validates ALL its cascade columns, not just office_phone."""
    schema = MagicMock()
    schema.get_cascade_columns.return_value = [
        ("office_phone", "Office Phone"),
        ("vertical", "Vertical"),
    ]

    merged_df = pl.DataFrame(
        {"gid": ["t-1"], "office_phone": [None], "vertical": [None]},
        schema={"gid": pl.Utf8, "office_phone": pl.Utf8, "vertical": pl.Utf8},
    )

    store = _make_mock_store(
        ancestor_chains={"t-1": ["holder-1", "biz-1"]},
        parent_chains={
            "t-1": [
                {"gid": "holder-1", "custom_fields": []},
                {
                    "gid": "biz-1",
                    "custom_fields": [
                        {"name": "Office Phone", "text_value": "555-0001"},
                        {"name": "Vertical", "text_value": "Chiro"},
                    ],
                },
            ]
        },
    )
    plugin = _make_mock_cascade_plugin()

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="test",
        schema=schema,
    )

    # Both cascade columns should be checked and corrected
    assert result.rows_checked == 2  # 1 row x 2 cascade columns
    assert result.rows_corrected == 2
    assert corrected_df["office_phone"][0] == "555-0001"
    assert corrected_df["vertical"][0] == "Chiro"


async def test_no_schema_validates_nothing() -> None:
    """When schema=None, no cascade fields are checked (safe degradation)."""
    merged_df = pl.DataFrame(
        {"gid": ["t-1"], "office_phone": [None]},
        schema={"gid": pl.Utf8, "office_phone": pl.Utf8},
    )

    store = _make_mock_store()
    plugin = _make_mock_cascade_plugin()

    _, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=plugin,
        project_gid="proj-1",
        entity_type="test",
        # schema=None (default)  # noqa: ERA001
    )

    assert result.rows_checked == 0
    assert result.rows_corrected == 0


# =============================================================================
# Cascade Key Null Audit Tests (ADR-cascade-contract-policy)
# =============================================================================


class TestAuditCascadeKeyNulls:
    """Tests for audit_cascade_key_nulls() structured logging."""

    def _make_schema(
        self,
        cascade_columns: list[tuple[str, str]],
    ) -> MagicMock:
        """Create a mock schema returning the given cascade columns."""
        schema = MagicMock()
        schema.get_cascade_columns.return_value = cascade_columns
        return schema

    def test_no_nulls_logs_info(self) -> None:
        """All cascade key columns populated -> severity 'ok', info log."""
        df = pl.DataFrame(
            {"office_phone": ["555-1111", "555-2222"], "gid": ["t1", "t2"]},
            schema={"office_phone": pl.Utf8, "gid": pl.Utf8},
        )
        schema = self._make_schema([("office_phone", "Office Phone")])

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_cascade_key_nulls(
                df=df,
                entity_type="unit",
                project_gid="proj-1",
                schema=schema,
                key_columns=("office_phone", "vertical"),
            )

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "cascade_key_null_audit"
            extra = call_args[1]["extra"]
            assert extra["severity"] == "ok"
            assert extra["entity_type"] == "unit"
            assert extra["total_rows"] == 2
            assert extra["cascade_key_nulls"]["office_phone"]["null_count"] == 0
            assert extra["cascade_key_nulls"]["office_phone"]["null_rate"] == 0.0

    def test_low_nulls_logs_info(self) -> None:
        """Null rate below 5% -> severity 'ok'."""
        # 1 null out of 100 rows = 1%
        phones = [None] + ["555-0000"] * 99
        df = pl.DataFrame(
            {"office_phone": phones},
            schema={"office_phone": pl.Utf8},
        )
        schema = self._make_schema([("office_phone", "Office Phone")])

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_cascade_key_nulls(
                df=df,
                entity_type="unit",
                project_gid="proj-1",
                schema=schema,
                key_columns=("office_phone",),
            )

            mock_logger.info.assert_called_once()
            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["severity"] == "ok"
            assert extra["cascade_key_nulls"]["office_phone"]["null_count"] == 1

    def test_medium_nulls_logs_warning(self) -> None:
        """Null rate between 5% and 20% -> severity 'warning'."""
        # 10 nulls out of 100 = 10%
        phones = [None] * 10 + ["555-0000"] * 90
        df = pl.DataFrame(
            {"office_phone": phones},
            schema={"office_phone": pl.Utf8},
        )
        schema = self._make_schema([("office_phone", "Office Phone")])

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_cascade_key_nulls(
                df=df,
                entity_type="unit",
                project_gid="proj-1",
                schema=schema,
                key_columns=("office_phone",),
            )

            mock_logger.warning.assert_called_once()
            extra = mock_logger.warning.call_args[1]["extra"]
            assert extra["severity"] == "warning"
            assert extra["cascade_key_nulls"]["office_phone"]["null_count"] == 10
            assert extra["cascade_key_nulls"]["office_phone"]["null_rate"] == 0.1

    def test_high_nulls_logs_error(self) -> None:
        """Null rate above 20% -> severity 'error'."""
        # 30 nulls out of 100 = 30% (SCAR-005 scenario)
        phones = [None] * 30 + ["555-0000"] * 70
        df = pl.DataFrame(
            {"office_phone": phones},
            schema={"office_phone": pl.Utf8},
        )
        schema = self._make_schema([("office_phone", "Office Phone")])

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_cascade_key_nulls(
                df=df,
                entity_type="unit",
                project_gid="proj-1",
                schema=schema,
                key_columns=("office_phone",),
            )

            mock_logger.error.assert_called_once()
            extra = mock_logger.error.call_args[1]["extra"]
            assert extra["severity"] == "error"
            assert extra["cascade_key_nulls"]["office_phone"]["null_count"] == 30
            assert extra["cascade_key_nulls"]["office_phone"]["null_rate"] == 0.3

    def test_multiple_cascade_columns_reports_all(self) -> None:
        """Audit reports null rates for each cascade key column independently."""
        df = pl.DataFrame(
            {
                "office_phone": [None, "555-0000"],
                "vertical": [None, None],
            },
            schema={"office_phone": pl.Utf8, "vertical": pl.Utf8},
        )
        schema = self._make_schema(
            [
                ("office_phone", "Office Phone"),
                ("vertical", "Vertical"),
            ]
        )

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_cascade_key_nulls(
                df=df,
                entity_type="offer",
                project_gid="proj-1",
                schema=schema,
                key_columns=("office_phone", "vertical", "offer_id"),
            )

            # vertical has 100% nulls -> error
            mock_logger.error.assert_called_once()
            extra = mock_logger.error.call_args[1]["extra"]
            assert extra["severity"] == "error"
            assert "office_phone" in extra["cascade_key_nulls"]
            assert "vertical" in extra["cascade_key_nulls"]
            assert extra["cascade_key_nulls"]["vertical"]["null_count"] == 2
            assert extra["cascade_key_nulls"]["office_phone"]["null_count"] == 1

    def test_non_key_cascade_columns_ignored(self) -> None:
        """Cascade columns that are NOT key columns are not audited."""
        df = pl.DataFrame(
            {
                "office_phone": ["555-0000"],
                "mrr": [None],  # cascade but not a key column
            },
            schema={"office_phone": pl.Utf8, "mrr": pl.Utf8},
        )
        schema = self._make_schema(
            [
                ("office_phone", "Office Phone"),
                ("mrr", "MRR"),
            ]
        )

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_cascade_key_nulls(
                df=df,
                entity_type="offer",
                project_gid="proj-1",
                schema=schema,
                key_columns=("office_phone", "vertical", "offer_id"),
            )

            mock_logger.info.assert_called_once()
            extra = mock_logger.info.call_args[1]["extra"]
            # Only office_phone should be reported (mrr is not a key column)
            assert "office_phone" in extra["cascade_key_nulls"]
            assert "mrr" not in extra["cascade_key_nulls"]

    def test_empty_dataframe_skips_audit(self) -> None:
        """Empty DataFrame -> audit silently skipped (no log)."""
        df = pl.DataFrame(
            {"office_phone": []},
            schema={"office_phone": pl.Utf8},
        )
        schema = self._make_schema([("office_phone", "Office Phone")])

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_cascade_key_nulls(
                df=df,
                entity_type="unit",
                project_gid="proj-1",
                schema=schema,
                key_columns=("office_phone",),
            )

            mock_logger.info.assert_not_called()
            mock_logger.warning.assert_not_called()
            mock_logger.error.assert_not_called()

    def test_no_schema_skips_audit(self) -> None:
        """schema=None -> audit silently skipped."""
        df = pl.DataFrame(
            {"office_phone": [None]},
            schema={"office_phone": pl.Utf8},
        )

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_cascade_key_nulls(
                df=df,
                entity_type="unit",
                project_gid="proj-1",
                schema=None,
                key_columns=("office_phone",),
            )

            mock_logger.info.assert_not_called()
            mock_logger.warning.assert_not_called()
            mock_logger.error.assert_not_called()

    def test_source_entity_annotation(self) -> None:
        """Audit includes cascade source entity name in log event."""
        df = pl.DataFrame(
            {"office_phone": [None, "555-0000"]},
            schema={"office_phone": pl.Utf8},
        )
        schema = self._make_schema([("office_phone", "Office Phone")])

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_cascade_key_nulls(
                df=df,
                entity_type="unit",
                project_gid="proj-1",
                schema=schema,
                key_columns=("office_phone",),
            )

            extra = mock_logger.error.call_args[1]["extra"]
            assert extra["cascade_key_nulls"]["office_phone"]["source_entity"] == "business"
            assert extra["cascade_key_nulls"]["office_phone"]["cascade_source"] == "Office Phone"

    def test_thresholds_match_adr_calibration(self) -> None:
        """Verify threshold constants match ADR-cascade-contract-policy specification."""
        assert CASCADE_NULL_WARN_THRESHOLD == 0.05
        assert CASCADE_NULL_ERROR_THRESHOLD == 0.20


# ---------------------------------------------------------------------------
# GAP-A Sprint-2 tests: Cascade contract repair for Offer office column
# ---------------------------------------------------------------------------


class TestOfferOfficeCascadeContract:
    """Tests for GAP-A: Offer office column under cascade governance."""

    def test_offer_office_schema_source_is_cascade_business_name(self) -> None:
        """Offer schema office column must use cascade:Business Name source."""
        from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA

        office_col = None
        for col in OFFER_SCHEMA.columns:
            if col.name == "office":
                office_col = col
                break

        assert office_col is not None, "office column missing from OFFER_SCHEMA"
        assert office_col.source == "cascade:Business Name", (
            f"Expected source='cascade:Business Name', got source={office_col.source!r}"
        )

    def test_offer_schema_version_is_1_4_0(self) -> None:
        """OFFER_SCHEMA version must be 1.4.0 after cascade contract addition."""
        from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA

        assert OFFER_SCHEMA.version == "1.4.0", (
            f"Expected version='1.4.0', got version={OFFER_SCHEMA.version!r}"
        )

    def test_offer_office_in_cascade_columns(self) -> None:
        """office must appear in get_cascade_columns() as (office, Business Name)."""
        from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA

        cascade_cols = OFFER_SCHEMA.get_cascade_columns()
        office_entry = None
        for col_name, cascade_name in cascade_cols:
            if col_name == "office":
                office_entry = (col_name, cascade_name)
                break

        assert office_entry is not None, "office not in get_cascade_columns()"
        assert office_entry == ("office", "Business Name")


async def test_cascade_validator_corrects_business_name_from_task_name() -> None:
    """Cascade validator resolves Business Name from task['name'], not custom_fields.

    Per GAP-A fix: The validator must use get_field_value() which reads
    task_data['name'] when CascadingFieldDef.source_field='name'.
    """
    merged_df = pl.DataFrame(
        {
            "gid": ["offer-1"],
            "name": ["Test Offer"],
            "office": pl.Series("office", [None], dtype=pl.Utf8),
            "section_gid": ["sec-1"],
        }
    )

    # Schema returns office as a cascade column
    schema = MagicMock()
    schema.get_cascade_columns.return_value = [("office", "Business Name")]

    # Store provides a parent chain with a Business task that has a name
    business_parent = {
        "gid": "biz-1",
        "name": "Acme Chiropractic",  # This is Task.name, NOT a custom field
        "custom_fields": [],  # No "Business Name" custom field exists
        "parent": None,
    }
    store = _make_mock_store(
        ancestor_chains={"offer-1": ["biz-1"]},
        parent_chains={"offer-1": [business_parent]},
    )

    # Cascade plugin is passed but the fix bypasses its _get_custom_field_value_from_dict
    cascade_plugin = MagicMock()

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=cascade_plugin,
        project_gid="proj-1",
        entity_type="offer",
        schema=schema,
    )

    # The office column should now be populated from business_parent["name"]
    assert corrected_df["office"][0] == "Acme Chiropractic", (
        f"Expected 'Acme Chiropractic', got {corrected_df['office'][0]!r}"
    )
    assert result.rows_corrected >= 1


async def test_cascade_validator_office_phone_correction_unaffected() -> None:
    """Office Phone correction still works after the get_field_value refactor.

    Regression guard: Office Phone is a real custom field (no source_field),
    so get_field_value falls through to get_custom_field_value — same as before.
    """
    merged_df = pl.DataFrame(
        {
            "gid": ["unit-1"],
            "name": ["Test Unit"],
            "office_phone": pl.Series("office_phone", [None], dtype=pl.Utf8),
            "section_gid": ["sec-1"],
        }
    )

    schema = MagicMock()
    schema.get_cascade_columns.return_value = [("office_phone", "Office Phone")]

    business_parent = {
        "gid": "biz-1",
        "name": "Some Business",
        "custom_fields": [
            {"name": "Office Phone", "text_value": "(614) 636-2433"},
        ],
        "parent": None,
    }
    store = _make_mock_store(
        ancestor_chains={"unit-1": ["biz-1"]},
        parent_chains={"unit-1": [business_parent]},
    )

    cascade_plugin = MagicMock()

    corrected_df, result = await validate_cascade_fields_async(
        merged_df=merged_df,
        store=store,
        cascade_plugin=cascade_plugin,
        project_gid="proj-1",
        entity_type="unit",
        schema=schema,
    )

    # Office Phone should be corrected from custom_fields (raw, not normalized — GAP-B)
    assert corrected_df["office_phone"][0] == "(614) 636-2433", (
        f"Expected '(614) 636-2433', got {corrected_df['office_phone'][0]!r}"
    )
    assert result.rows_corrected >= 1


# ---------------------------------------------------------------------------
# Sprint-4 observability tests
# ---------------------------------------------------------------------------


class TestAuditCascadeDisplayNulls:
    """Tests for display-column null rate audit (GAP-A observability)."""

    def test_reports_display_column_null_rate(self) -> None:
        """Display columns (not key columns) are reported with null rates."""
        from autom8_asana.dataframes.builders.cascade_validator import (
            audit_cascade_display_nulls,
        )

        df = pl.DataFrame(
            {
                "office": pl.Series(["Acme", None, None], dtype=pl.Utf8),
                "office_phone": ["+15551234567", "+15559876543", None],
            }
        )
        schema = MagicMock()
        schema.get_cascade_columns.return_value = [
            ("office", "Business Name"),
            ("office_phone", "Office Phone"),
        ]

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_cascade_display_nulls(
                df=df,
                entity_type="offer",
                project_gid="proj-1",
                schema=schema,
                key_columns=("office_phone",),  # office is NOT a key column
            )

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "cascade_display_null_audit"
            extra = call_args[1]["extra"]
            assert "office" in extra["cascade_display_nulls"]
            assert extra["cascade_display_nulls"]["office"]["null_count"] == 2
            # office_phone is a key column — should NOT appear in display audit
            assert "office_phone" not in extra["cascade_display_nulls"]

    def test_skips_when_no_display_columns(self) -> None:
        """When all cascade columns are key columns, nothing is audited."""
        from autom8_asana.dataframes.builders.cascade_validator import (
            audit_cascade_display_nulls,
        )

        df = pl.DataFrame({"office_phone": ["+15551234567"]})
        schema = MagicMock()
        schema.get_cascade_columns.return_value = [("office_phone", "Office Phone")]

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_cascade_display_nulls(
                df=df,
                entity_type="offer",
                project_gid="proj-1",
                schema=schema,
                key_columns=("office_phone",),
            )
            mock_logger.info.assert_not_called()


class TestAuditPhoneE164Compliance:
    """Tests for phone E.164 compliance audit (GAP-B observability)."""

    def test_reports_e164_compliance_rate(self) -> None:
        """Compliant and non-compliant phones are counted correctly."""
        from autom8_asana.dataframes.builders.cascade_validator import (
            audit_phone_e164_compliance,
        )

        df = pl.DataFrame(
            {
                "office_phone": [
                    "+15551234567",  # compliant
                    "+16146362433",  # compliant
                    "(614) 636-2433",  # non-compliant (raw format)
                    None,  # null — excluded from count
                ],
            }
        )

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_phone_e164_compliance(
                df=df,
                entity_type="offer",
                project_gid="proj-1",
            )

            mock_logger.info.assert_called_once()
            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["total_phones"] == 3  # 4 rows - 1 null = 3
            assert extra["e164_compliant"] == 2  # two E.164 formatted
            assert extra["non_compliant"] == 1  # one raw format

    def test_skips_when_no_office_phone_column(self) -> None:
        """DataFrames without office_phone column are silently skipped."""
        from autom8_asana.dataframes.builders.cascade_validator import (
            audit_phone_e164_compliance,
        )

        df = pl.DataFrame({"name": ["Test"]})

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_phone_e164_compliance(
                df=df,
                entity_type="contact",
                project_gid="proj-1",
            )
            mock_logger.info.assert_not_called()

    def test_all_compliant_reports_100_percent(self) -> None:
        """100% compliance when all phones are E.164."""
        from autom8_asana.dataframes.builders.cascade_validator import (
            audit_phone_e164_compliance,
        )

        df = pl.DataFrame(
            {"office_phone": ["+15551234567", "+16146362433"]},
        )

        with patch("autom8_asana.dataframes.builders.cascade_validator.logger") as mock_logger:
            audit_phone_e164_compliance(
                df=df,
                entity_type="offer",
                project_gid="proj-1",
            )

            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["compliance_rate"] == 1.0
            assert extra["non_compliant"] == 0
