"""Integration tests proving the resolution triad for PARTIAL-triad entities.

Per Sprint 3 Integration Test Design: Proves that all 4 PARTIAL-triad
entities (business, offer, asset_edit, asset_edit_holder) can be:
1. Represented as realistic Polars DataFrames with full schema column coverage
2. Indexed by DynamicIndex and resolved via their key_columns
3. Validated by check_cascade_health at both healthy and degraded states
4. Audited by audit_cascade_key_nulls without error

Non-goals: No async extraction, no Asana client mocks, no
UniversalResolutionStrategy integration.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import polars as pl
import pytest

from autom8_asana.dataframes.builders.cascade_validator import (
    CASCADE_NULL_ERROR_THRESHOLD,
    CascadeHealthResult,
    audit_cascade_key_nulls,
    check_cascade_health,
)
from autom8_asana.dataframes.schemas import (
    ASSET_EDIT_HOLDER_SCHEMA,
    ASSET_EDIT_SCHEMA,
    BUSINESS_SCHEMA,
    OFFER_SCHEMA,
)
from autom8_asana.services.dynamic_index import DynamicIndex
from autom8_asana.services.errors import CascadeNotReadyError

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import DataFrameSchema

# ---------------------------------------------------------------------------
# Shared constants (per design spec section 3.1)
# ---------------------------------------------------------------------------

TS_CREATED = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
TS_MODIFIED = datetime(2024, 6, 20, 14, 45, 0, tzinfo=UTC)
TS_COMPLETED = datetime(2024, 3, 10, 9, 0, 0, tzinfo=UTC)
DATE_DUE = date(2024, 7, 15)
DATE_PRIMARY = date(2024, 6, 1)
N_ROWS = 10


# ---------------------------------------------------------------------------
# DataFrame builder functions (per design spec section 3.2-3.5)
# ---------------------------------------------------------------------------


def _build_business_df(
    n_rows: int = N_ROWS,
    null_office_phone_count: int = 0,
) -> pl.DataFrame:
    """Build a realistic Business DataFrame with all 18 schema columns."""
    names = [
        "Acme Dental Springfield",
        "Bright Smile Portland",
        "ClearView Optometry",
        "Delta Medical Group",
        "Elite Chiropractic",
        "Family Health Clinic",
        "Golden Dental Care",
        "Harbor Medical Center",
        "Infinity Wellness",
        "Jupiter Health Partners",
    ]
    booking_types = ["Online", "Phone"] * 5

    office_phones: list[str | None] = [
        f"+1555010{i:04d}" for i in range(n_rows)
    ]
    # Null out the last null_office_phone_count entries
    for idx in range(n_rows - null_office_phone_count, n_rows):
        office_phones[idx] = None

    return pl.DataFrame(
        {
            "gid": [f"120065301256{i:04d}" for i in range(n_rows)],
            "name": [names[i % len(names)] for i in range(n_rows)],
            "type": ["Business"] * n_rows,
            "date": [DATE_PRIMARY] * n_rows,
            "created": [TS_CREATED] * n_rows,
            "due_on": [DATE_DUE] * n_rows,
            "is_completed": [False] * n_rows,
            "completed_at": [None] * n_rows,
            "url": [
                f"https://app.asana.com/0/0/120065301256{i:04d}"
                for i in range(n_rows)
            ],
            "last_modified": [TS_MODIFIED] * n_rows,
            "section": ["Active"] * n_rows,
            "tags": [["vip", "dental"]] * n_rows,
            "parent_gid": [None] * n_rows,
            "company_id": [f"COMP-{i:04d}" for i in range(n_rows)],
            "office_phone": office_phones,
            "stripe_id": [f"cus_test{i:08d}" for i in range(n_rows)],
            "booking_type": [booking_types[i % len(booking_types)] for i in range(n_rows)],
            "facebook_page_id": [f"fb_{i:012d}" for i in range(n_rows)],
        },
        schema_overrides={
            "created": pl.Datetime("us", "UTC"),
            "last_modified": pl.Datetime("us", "UTC"),
            "completed_at": pl.Datetime("us", "UTC"),
        },
    )


def _build_offer_df(
    n_rows: int = N_ROWS,
    null_office_phone_count: int = 0,
) -> pl.DataFrame:
    """Build a realistic Offer DataFrame with all 23 schema columns."""
    verticals = ["dental", "medical"] * 5

    office_phones: list[str | None] = [
        f"+1555010{i:04d}" for i in range(n_rows)
    ]
    for idx in range(n_rows - null_office_phone_count, n_rows):
        office_phones[idx] = None

    return pl.DataFrame(
        {
            "gid": [f"114384366209{i:04d}" for i in range(n_rows)],
            "name": [
                f"Google Ads - {verticals[i % 2].title()} - Office {i}"
                for i in range(n_rows)
            ],
            "type": ["Offer"] * n_rows,
            "date": [DATE_PRIMARY] * n_rows,
            "created": [TS_CREATED] * n_rows,
            "due_on": [DATE_DUE] * n_rows,
            "is_completed": [False] * n_rows,
            "completed_at": [None] * n_rows,
            "url": [
                f"https://app.asana.com/0/0/114384366209{i:04d}"
                for i in range(n_rows)
            ],
            "last_modified": [TS_MODIFIED] * n_rows,
            "section": ["Active"] * n_rows,
            "tags": [["google-ads"]] * n_rows,
            "parent_gid": [None] * n_rows,
            "office": [f"Acme Dental Office {i}" for i in range(n_rows)],
            "office_phone": office_phones,
            "vertical": [verticals[i % len(verticals)] for i in range(n_rows)],
            "specialty": ["general"] * n_rows,
            "offer_id": [f"OID-{i:04d}" for i in range(n_rows)],
            "platforms": [["google", "facebook"]] * n_rows,
            "language": ["English"] * n_rows,
            "cost": [f"{1500 + i * 100}.00" for i in range(n_rows)],
            "mrr": [2500.0 + i * 100 for i in range(n_rows)],
            "weekly_ad_spend": [350.0 + i * 25 for i in range(n_rows)],
        },
        schema_overrides={
            "created": pl.Datetime("us", "UTC"),
            "last_modified": pl.Datetime("us", "UTC"),
            "completed_at": pl.Datetime("us", "UTC"),
        },
    )


def _build_asset_edit_df(
    n_rows: int = N_ROWS,
    null_office_phone_count: int = 0,
) -> pl.DataFrame:
    """Build a realistic AssetEdit DataFrame with all 34 schema columns."""
    statuses = ["In Progress", "Complete"] * 5
    priorities = ["High", "Normal"] * 5
    approvals = ["Approved", "Pending"] * 5

    office_phones: list[str | None] = [
        f"+1555010{i:04d}" for i in range(n_rows)
    ]
    for idx in range(n_rows - null_office_phone_count, n_rows):
        office_phones[idx] = None

    return pl.DataFrame(
        {
            "gid": [f"120220418456{i:04d}" for i in range(n_rows)],
            "name": [f"Asset Edit - Dental Video {i}" for i in range(n_rows)],
            "type": ["AssetEdit"] * n_rows,
            "date": [DATE_PRIMARY] * n_rows,
            "created": [TS_CREATED] * n_rows,
            "due_on": [DATE_DUE] * n_rows,
            "is_completed": [False] * n_rows,
            "completed_at": [None] * n_rows,
            "url": [
                f"https://app.asana.com/0/0/120220418456{i:04d}"
                for i in range(n_rows)
            ],
            "last_modified": [TS_MODIFIED] * n_rows,
            "section": ["In Progress"] * n_rows,
            "tags": [["video"]] * n_rows,
            "parent_gid": [None] * n_rows,
            # Process fields (10)
            "started_at": ["2024-05-01T10:00:00Z"] * n_rows,
            "process_completed_at": ["2024-05-15T16:00:00Z"] * n_rows,
            "process_notes": [f"Revision round {i % 3 + 1}" for i in range(n_rows)],
            "status": [statuses[i % len(statuses)] for i in range(n_rows)],
            "priority": [priorities[i % len(priorities)] for i in range(n_rows)],
            "process_due_date": ["2024-06-01"] * n_rows,
            "assigned_to": [f"user_{i:04d}" for i in range(n_rows)],
            "vertical": ["dental"] * n_rows,
            "office_phone": office_phones,
            "specialty": [["general", "cosmetic"]] * n_rows,
            # AssetEdit-specific fields (11)
            "asset_approval": [approvals[i % len(approvals)] for i in range(n_rows)],
            "asset_id": [f"AST-{i:06d}" for i in range(n_rows)],
            "editor": [f"editor_{i:02d}" for i in range(n_rows)],
            "reviewer": [f"reviewer_{i:02d}" for i in range(n_rows)],
            "offer_id": [100 + i for i in range(n_rows)],
            "raw_assets": [
                f"https://drive.google.com/file/{i}" for i in range(n_rows)
            ],
            "review_all_ads": [i % 2 == 0 for i in range(n_rows)],
            "score": [85.5 + i for i in range(n_rows)],
            "asset_edit_specialty": [["video", "static"]] * n_rows,
            "template_id": [200 + i for i in range(n_rows)],
            "videos_paid": [i + 1 for i in range(n_rows)],
        },
        schema_overrides={
            "created": pl.Datetime("us", "UTC"),
            "last_modified": pl.Datetime("us", "UTC"),
            "completed_at": pl.Datetime("us", "UTC"),
            "offer_id": pl.Int64,
            "template_id": pl.Int64,
            "videos_paid": pl.Int64,
        },
    )


def _build_asset_edit_holder_df(
    n_rows: int = N_ROWS,
    null_office_phone_count: int = 0,
) -> pl.DataFrame:
    """Build a realistic AssetEditHolder DataFrame with all 14 schema columns."""
    office_phones: list[str | None] = [
        f"+1555010{i:04d}" for i in range(n_rows)
    ]
    for idx in range(n_rows - null_office_phone_count, n_rows):
        office_phones[idx] = None

    return pl.DataFrame(
        {
            "gid": [f"120399266440{i:04d}" for i in range(n_rows)],
            "name": [f"Asset Edits - Acme Dental {i}" for i in range(n_rows)],
            "type": ["AssetEditHolder"] * n_rows,
            "date": [DATE_PRIMARY] * n_rows,
            "created": [TS_CREATED] * n_rows,
            "due_on": [DATE_DUE] * n_rows,
            "is_completed": [False] * n_rows,
            "completed_at": [None] * n_rows,
            "url": [
                f"https://app.asana.com/0/0/120399266440{i:04d}"
                for i in range(n_rows)
            ],
            "last_modified": [TS_MODIFIED] * n_rows,
            "section": ["Active"] * n_rows,
            "tags": [["holder"]] * n_rows,
            "parent_gid": [None] * n_rows,
            "office_phone": office_phones,
        },
        schema_overrides={
            "created": pl.Datetime("us", "UTC"),
            "last_modified": pl.Datetime("us", "UTC"),
            "completed_at": pl.Datetime("us", "UTC"),
        },
    )


# ---------------------------------------------------------------------------
# Assertion helpers (per design spec section 5)
# ---------------------------------------------------------------------------


def assert_schema_coverage(df: pl.DataFrame, schema: DataFrameSchema) -> None:
    """Assert DataFrame covers all schema columns with realistic data."""
    schema_cols = set(schema.column_names())
    df_cols = set(df.columns)
    missing = schema_cols - df_cols
    assert not missing, f"DataFrame missing schema columns: {missing}"

    for col_def in schema.columns:
        if not col_def.nullable:
            null_count = df[col_def.name].null_count()
            assert null_count == 0, (
                f"Non-nullable column {col_def.name!r} has {null_count} nulls"
            )


def assert_resolves(
    index: DynamicIndex, criterion: dict[str, Any], expected_gid: str
) -> None:
    """Assert single criterion resolves to expected GID."""
    gids = index.lookup(criterion)
    assert len(gids) >= 1, f"Expected match for {criterion}, got empty"
    assert expected_gid in gids, f"Expected {expected_gid} in {gids}"


# ---------------------------------------------------------------------------
# Parametrization registry: maps entity key -> test configuration
# ---------------------------------------------------------------------------

ENTITY_CONFIG: dict[str, dict[str, Any]] = {
    "business": {
        "schema": BUSINESS_SCHEMA,
        "builder": _build_business_df,
        "key_columns": ["office_phone"],
        "criterion": {"office_phone": "+15550100001"},
        "expected_gid": "1200653012560001",
    },
    "offer": {
        "schema": OFFER_SCHEMA,
        "builder": _build_offer_df,
        "key_columns": ["office_phone", "vertical", "offer_id"],
        "criterion": {
            "office_phone": "+15550100002",
            "vertical": "dental",
            "offer_id": "OID-0002",
        },
        "expected_gid": "1143843662090002",
    },
    "asset_edit": {
        "schema": ASSET_EDIT_SCHEMA,
        "builder": _build_asset_edit_df,
        # Note: offer_id is Int64 in schema; DynamicIndex converts via str()
        "key_columns": ["office_phone", "vertical", "asset_id", "offer_id"],
        "criterion": {
            "office_phone": "+15550100003",
            "vertical": "dental",
            "asset_id": "AST-000003",
            "offer_id": "103",
        },
        "expected_gid": "1202204184560003",
    },
    "asset_edit_holder": {
        "schema": ASSET_EDIT_HOLDER_SCHEMA,
        "builder": _build_asset_edit_holder_df,
        "key_columns": ["office_phone"],
        "criterion": {"office_phone": "+15550100004"},
        "expected_gid": "1203992664400004",
    },
}

_ENTITY_KEYS = list(ENTITY_CONFIG.keys())

# Downstream entities that have cascade columns (excludes business)
_CASCADE_ENTITY_KEYS = ["offer", "asset_edit", "asset_edit_holder"]


# ---------------------------------------------------------------------------
# 4.1 Per-Entity Resolution Tests (parametrized x4)
# ---------------------------------------------------------------------------


class TestResolutionLookup:
    """Prove: DataFrame -> DynamicIndex -> lookup succeeds for all entities."""

    @pytest.mark.parametrize("entity_key", _ENTITY_KEYS)
    def test_resolution_lookup(self, entity_key: str) -> None:
        cfg = ENTITY_CONFIG[entity_key]
        df = cfg["builder"]()
        index = DynamicIndex.from_dataframe(
            df=df,
            key_columns=cfg["key_columns"],
            value_column="gid",
        )
        assert_resolves(index, cfg["criterion"], cfg["expected_gid"])

    @pytest.mark.parametrize("entity_key", _ENTITY_KEYS)
    def test_resolution_lookup_single(self, entity_key: str) -> None:
        """lookup_single returns the expected GID for each entity."""
        cfg = ENTITY_CONFIG[entity_key]
        df = cfg["builder"]()
        index = DynamicIndex.from_dataframe(
            df=df,
            key_columns=cfg["key_columns"],
            value_column="gid",
        )
        result = index.lookup_single(cfg["criterion"])
        assert result == cfg["expected_gid"]

    @pytest.mark.parametrize("entity_key", _ENTITY_KEYS)
    def test_index_entry_count_matches_rows(self, entity_key: str) -> None:
        """Index should have exactly N_ROWS entries when no nulls present."""
        cfg = ENTITY_CONFIG[entity_key]
        df = cfg["builder"](n_rows=N_ROWS, null_office_phone_count=0)
        index = DynamicIndex.from_dataframe(
            df=df,
            key_columns=cfg["key_columns"],
            value_column="gid",
        )
        assert len(index) == N_ROWS


# ---------------------------------------------------------------------------
# 4.2 SchemaExtractor Column Coverage Tests (parametrized x4)
# ---------------------------------------------------------------------------


class TestSchemaColumnCoverage:
    """Prove: Builder DataFrames cover the full schema surface."""

    @pytest.mark.parametrize("entity_key", _ENTITY_KEYS)
    def test_schema_column_coverage(self, entity_key: str) -> None:
        cfg = ENTITY_CONFIG[entity_key]
        df = cfg["builder"]()
        assert_schema_coverage(df, cfg["schema"])

    @pytest.mark.parametrize("entity_key", _ENTITY_KEYS)
    def test_column_count_matches_schema(self, entity_key: str) -> None:
        """DataFrame column count matches schema column count exactly."""
        cfg = ENTITY_CONFIG[entity_key]
        df = cfg["builder"]()
        expected_count = len(cfg["schema"].columns)
        assert len(df.columns) == expected_count, (
            f"Expected {expected_count} columns for {entity_key}, "
            f"got {len(df.columns)}. "
            f"Extra: {set(df.columns) - set(cfg['schema'].column_names())}. "
            f"Missing: {set(cfg['schema'].column_names()) - set(df.columns)}."
        )


# ---------------------------------------------------------------------------
# 4.3 Cascade Chain Test -- Healthy Propagation
# ---------------------------------------------------------------------------


class TestCascadeChainHealthy:
    """Prove: Cascade chain passes health check when all columns populated."""

    def test_cascade_chain_healthy(self) -> None:
        """All downstream entities pass cascade health with 0% nulls.

        Business has NO cascade columns (office_phone is cf:, not cascade:),
        so it always passes trivially.  The other 3 entities have cascade
        columns and should pass because 0% of their cascade key columns
        are null.
        """
        entities_and_key_columns = [
            ("business", _build_business_df, BUSINESS_SCHEMA, ("office_phone",)),
            ("offer", _build_offer_df, OFFER_SCHEMA, ("office_phone", "vertical", "offer_id")),
            (
                "asset_edit",
                _build_asset_edit_df,
                ASSET_EDIT_SCHEMA,
                ("office_phone", "vertical", "asset_id", "offer_id"),
            ),
            (
                "asset_edit_holder",
                _build_asset_edit_holder_df,
                ASSET_EDIT_HOLDER_SCHEMA,
                ("office_phone",),
            ),
        ]

        for entity_type, builder, schema, key_columns in entities_and_key_columns:
            df = builder(n_rows=N_ROWS, null_office_phone_count=0)
            result = check_cascade_health(df, entity_type, schema, key_columns)
            assert result.healthy is True, (
                f"{entity_type}: expected healthy=True, "
                f"got degraded_columns={result.degraded_columns}"
            )
            assert result.degraded_columns == {}
            assert result.max_null_rate == pytest.approx(0.0)

    def test_business_has_no_cascade_columns(self) -> None:
        """Business schema has zero cascade columns (office_phone is cf:)."""
        cascade_cols = BUSINESS_SCHEMA.get_cascade_columns()
        assert cascade_cols == [], (
            f"Business should have no cascade columns, got: {cascade_cols}"
        )


# ---------------------------------------------------------------------------
# 4.4 CASCADE_NOT_READY Test -- Degraded Cascade
# ---------------------------------------------------------------------------


class TestCascadeNotReady:
    """Prove: Degraded cascade data triggers unhealthy results."""

    @pytest.mark.parametrize("entity_key", _CASCADE_ENTITY_KEYS)
    def test_cascade_not_ready_degraded(self, entity_key: str) -> None:
        """Downstream entities fail cascade health with >20% null office_phone.

        3 of 10 rows null = 30% null rate, which exceeds the 20% threshold.
        """
        cfg = ENTITY_CONFIG[entity_key]
        df = cfg["builder"](n_rows=N_ROWS, null_office_phone_count=3)
        result = check_cascade_health(
            df,
            entity_key,
            cfg["schema"],
            tuple(cfg["key_columns"]),
        )
        assert result.healthy is False, (
            f"{entity_key}: expected healthy=False at 30% null"
        )
        assert "office_phone" in result.degraded_columns
        assert result.degraded_columns["office_phone"] == pytest.approx(0.3)
        assert result.max_null_rate == pytest.approx(0.3)

    @pytest.mark.parametrize("entity_key", _CASCADE_ENTITY_KEYS)
    def test_cascade_at_threshold_boundary_passes(self, entity_key: str) -> None:
        """Exactly 20% null (2 of 10) should NOT trigger degradation.

        CASCADE_NULL_ERROR_THRESHOLD is 0.20 and the check is > (not >=).
        """
        cfg = ENTITY_CONFIG[entity_key]
        df = cfg["builder"](n_rows=N_ROWS, null_office_phone_count=2)
        result = check_cascade_health(
            df,
            entity_key,
            cfg["schema"],
            tuple(cfg["key_columns"]),
        )
        assert result.healthy is True, (
            f"{entity_key}: exactly 20% null should pass (threshold is >0.20)"
        )

    # ---- 4.5 CascadeNotReadyError construction test ----

    def test_cascade_not_ready_error_from_health_result(self) -> None:
        """CascadeNotReadyError can be constructed from CascadeHealthResult."""
        df = _build_offer_df(n_rows=N_ROWS, null_office_phone_count=3)
        result = check_cascade_health(
            df, "offer", OFFER_SCHEMA, ("office_phone", "vertical", "offer_id")
        )
        assert not result.healthy

        err = CascadeNotReadyError(
            entity_type="offer",
            project_gid="proj-test-001",
            degraded_columns=result.degraded_columns,
            max_null_rate=result.max_null_rate,
        )
        assert err.error_code == "CASCADE_NOT_READY"
        assert err.status_hint == 503
        assert "office_phone" in err.degraded_columns
        assert err.degraded_columns["office_phone"] == pytest.approx(0.3)
        assert err.max_null_rate == pytest.approx(0.3)

        # Verify serialization
        d = err.to_dict()
        assert d["error"] == "CASCADE_NOT_READY"
        assert "office_phone" in d["degraded_columns"]


# ---------------------------------------------------------------------------
# 4.6 audit_cascade_key_nulls Integration Test
# ---------------------------------------------------------------------------


class TestAuditCascadeKeyNulls:
    """Prove: audit_cascade_key_nulls logs at correct severity."""

    def test_audit_cascade_key_nulls_healthy(self) -> None:
        """Healthy data (0% null cascade keys) logs at INFO severity."""
        df = _build_offer_df(n_rows=N_ROWS, null_office_phone_count=0)
        with patch(
            "autom8_asana.dataframes.builders.cascade_validator.logger"
        ) as mock_logger:
            audit_cascade_key_nulls(
                df,
                "offer",
                "proj-1",
                schema=OFFER_SCHEMA,
                key_columns=("office_phone", "vertical", "offer_id"),
            )
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "cascade_key_null_audit"
            assert call_args[1]["extra"]["severity"] == "ok"
            mock_logger.warning.assert_not_called()
            mock_logger.error.assert_not_called()

    def test_audit_cascade_key_nulls_degraded(self) -> None:
        """Degraded data (30% null) logs at ERROR severity."""
        df = _build_offer_df(n_rows=N_ROWS, null_office_phone_count=3)
        with patch(
            "autom8_asana.dataframes.builders.cascade_validator.logger"
        ) as mock_logger:
            audit_cascade_key_nulls(
                df,
                "offer",
                "proj-1",
                schema=OFFER_SCHEMA,
                key_columns=("office_phone", "vertical", "offer_id"),
            )
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert call_args[0][0] == "cascade_key_null_audit"
            assert call_args[1]["extra"]["severity"] == "error"

    def test_audit_cascade_key_nulls_no_schema_is_noop(self) -> None:
        """Passing schema=None causes silent skip (safe degradation)."""
        df = _build_offer_df(n_rows=N_ROWS, null_office_phone_count=3)
        with patch(
            "autom8_asana.dataframes.builders.cascade_validator.logger"
        ) as mock_logger:
            audit_cascade_key_nulls(
                df,
                "offer",
                "proj-1",
                schema=None,
                key_columns=("office_phone", "vertical", "offer_id"),
            )
            mock_logger.info.assert_not_called()
            mock_logger.warning.assert_not_called()
            mock_logger.error.assert_not_called()


# ---------------------------------------------------------------------------
# 4.7 DynamicIndex Null Row Exclusion Test
# ---------------------------------------------------------------------------


class TestDynamicIndexNullExclusion:
    """Prove: Rows with null key columns are excluded from the index."""

    def test_dynamic_index_excludes_null_key_rows(self) -> None:
        """3 of 10 rows with null office_phone yields index of size 7."""
        df = _build_business_df(n_rows=N_ROWS, null_office_phone_count=3)
        index = DynamicIndex.from_dataframe(
            df=df,
            key_columns=["office_phone"],
            value_column="gid",
        )
        assert len(index) == 7

    def test_null_lookup_returns_empty(self) -> None:
        """Looking up a criterion with None value returns empty list."""
        df = _build_business_df(n_rows=N_ROWS, null_office_phone_count=0)
        index = DynamicIndex.from_dataframe(
            df=df,
            key_columns=["office_phone"],
            value_column="gid",
        )
        # None converted to "none" by str(); should not match any real phone
        result = index.lookup({"office_phone": "None"})
        assert result == []

    def test_index_size_decreases_with_nulls(self) -> None:
        """Verify index size reflects null exclusion across entities."""
        for null_count in [0, 2, 5, 8]:
            df = _build_asset_edit_holder_df(
                n_rows=N_ROWS, null_office_phone_count=null_count
            )
            index = DynamicIndex.from_dataframe(
                df=df,
                key_columns=["office_phone"],
                value_column="gid",
            )
            assert len(index) == N_ROWS - null_count


# ---------------------------------------------------------------------------
# 4.8 Multi-Key Compound Lookup Test
# ---------------------------------------------------------------------------


class TestDynamicIndexMultiKey:
    """Prove: DynamicIndex correctly handles multi-column key lookups."""

    def test_compound_key_exact_match(self) -> None:
        """4-key lookup on asset_edit matches exactly one row."""
        df = _build_asset_edit_df(n_rows=N_ROWS)
        index = DynamicIndex.from_dataframe(
            df=df,
            key_columns=["office_phone", "vertical", "asset_id", "offer_id"],
            value_column="gid",
        )
        # Row i=5: office_phone="+15550100005", vertical="dental",
        #          asset_id="AST-000005", offer_id=105 (Int64 -> "105")
        gids = index.lookup({
            "office_phone": "+15550100005",
            "vertical": "dental",
            "asset_id": "AST-000005",
            "offer_id": "105",
        })
        assert gids == ["1202204184560005"]

    def test_partial_key_mismatch_returns_empty(self) -> None:
        """Lookup with wrong offer_id returns empty even if other keys match."""
        df = _build_asset_edit_df(n_rows=N_ROWS)
        index = DynamicIndex.from_dataframe(
            df=df,
            key_columns=["office_phone", "vertical", "asset_id", "offer_id"],
            value_column="gid",
        )
        gids = index.lookup({
            "office_phone": "+15550100005",
            "vertical": "dental",
            "asset_id": "AST-000005",
            "offer_id": "999",  # Wrong offer_id
        })
        assert gids == []

    def test_offer_triple_key_lookup(self) -> None:
        """3-key lookup on offer resolves correctly."""
        df = _build_offer_df(n_rows=N_ROWS)
        index = DynamicIndex.from_dataframe(
            df=df,
            key_columns=["office_phone", "vertical", "offer_id"],
            value_column="gid",
        )
        # Row i=6: vertical = verticals[6 % 2] = "dental", offer_id = "OID-0006"
        gids = index.lookup({
            "office_phone": "+15550100006",
            "vertical": "dental",
            "offer_id": "OID-0006",
        })
        assert gids == ["1143843662090006"]

    def test_contains_check_works_for_compound_key(self) -> None:
        """index.contains() returns True for existing compound keys."""
        df = _build_asset_edit_df(n_rows=N_ROWS)
        index = DynamicIndex.from_dataframe(
            df=df,
            key_columns=["office_phone", "vertical", "asset_id", "offer_id"],
            value_column="gid",
        )
        assert index.contains({
            "office_phone": "+15550100002",
            "vertical": "dental",
            "asset_id": "AST-000002",
            "offer_id": "102",
        })
        assert not index.contains({
            "office_phone": "+15550100002",
            "vertical": "dental",
            "asset_id": "AST-000002",
            "offer_id": "999",
        })


# ---------------------------------------------------------------------------
# Additional coverage: edge cases and invariants
# ---------------------------------------------------------------------------


class TestCascadeHealthEdgeCases:
    """Additional cascade health edge cases for completeness."""

    def test_empty_dataframe_is_healthy(self) -> None:
        """check_cascade_health returns healthy for empty DataFrames."""
        df = _build_offer_df(n_rows=0)
        result = check_cascade_health(
            df, "offer", OFFER_SCHEMA, ("office_phone", "vertical", "offer_id")
        )
        assert result.healthy is True
        assert result.max_null_rate == 0.0

    def test_all_nulls_is_degraded(self) -> None:
        """100% null cascade key columns = degraded."""
        df = _build_asset_edit_holder_df(
            n_rows=N_ROWS, null_office_phone_count=N_ROWS
        )
        result = check_cascade_health(
            df, "asset_edit_holder", ASSET_EDIT_HOLDER_SCHEMA, ("office_phone",)
        )
        assert result.healthy is False
        assert result.max_null_rate == pytest.approx(1.0)

    def test_cascade_health_result_is_frozen(self) -> None:
        """CascadeHealthResult is a frozen dataclass."""
        result = CascadeHealthResult(
            healthy=True, degraded_columns={}, max_null_rate=0.0
        )
        with pytest.raises(AttributeError):
            result.healthy = False  # type: ignore[misc]
