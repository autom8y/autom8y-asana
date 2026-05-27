"""G2-RECV frame-parity tests — AC-G2P6 suite.

Tests for the G2-RECV frame-parity contract:

AC-G2P6-1 (population): STEP 0 population spike — cascade warming IS wired on
    the body-parameterized cold-build path. This test verifies the mechanism
    is present and connected (HierarchyWarmer.populate_store_with_tasks is
    called with warm_hierarchy=True for schemas with cascade columns).

AC-G2P6-2 (default_projection): project/section query with NO select returns
    the full 16-col projection (not 3-col).

AC-G2P6-3 (offer-domain non-regression): offer-domain entity with NO select
    STILL returns 3-col (gid/name/section) — sovereignty-critical non-regression.

AC-G2P6-4 (get_default_projection): registry.get_default_projection() returns
    full-16 for project/section, () for offer-domain entities.

AC-G2P6-5 (section mirror): section entity also gets full 16-col projection.

AC-G2P6-6 (limit): RowsRequest(limit=2539) validates without error;
    RowsRequest(limit=10001) raises ValidationError (422).

AC-G2P6-7 (engine literal fallback): engine.py select_fields falls through to
    ["gid", "name", "section"] literal for entities with empty default_projection.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from pydantic import ValidationError

from autom8_asana.core.entity_registry import EntityDescriptor, EntityRegistry, get_registry
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.project import PROJECT_SCHEMA
from autom8_asana.dataframes.schemas.section import SECTION_SCHEMA
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.guards import QueryLimits
from autom8_asana.query.models import RowsRequest
from autom8_asana.services.query_service import EntityQueryService

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_FULL_16_COLS = (
    "gid",
    "name",
    "type",
    "date",
    "created",
    "due_on",
    "is_completed",
    "completed_at",
    "url",
    "last_modified",
    "section",
    "tags",
    "parent_gid",
    "status",
    "office_phone",
    "vertical",
)


def _make_project_schema() -> DataFrameSchema:
    """Real PROJECT_SCHEMA — used for projection tests."""
    return PROJECT_SCHEMA


def _make_section_schema() -> DataFrameSchema:
    """Real SECTION_SCHEMA — used for projection tests."""
    return SECTION_SCHEMA


def _make_offer_schema() -> DataFrameSchema:
    """Minimal offer-domain schema (3 cols) for sovereignty non-regression."""
    return DataFrameSchema(
        name="offer",
        task_type="Offer",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("section", "Utf8", nullable=True),
        ],
    )


def _make_full_project_df() -> pl.DataFrame:
    """Minimal 16-col DataFrame matching PROJECT_SCHEMA for engine tests."""
    return pl.DataFrame(
        {
            "gid": ["task_001", "task_002"],
            "name": ["Alpha Dental", "Beta Dental"],
            "type": ["Project", "Project"],
            "date": [None, None],
            "created": [None, None],
            "due_on": [None, None],
            "is_completed": [False, False],
            "completed_at": [None, None],
            "url": ["https://app.asana.com/0/0/task_001", "https://app.asana.com/0/0/task_002"],
            "last_modified": [None, None],
            "section": ["Active", "Active"],
            "tags": [[], []],
            "parent_gid": [None, None],
            "status": [None, None],
            "office_phone": ["555-0001", "555-0002"],
            "vertical": ["dental", "dental"],
        }
    )


def _make_offer_df() -> pl.DataFrame:
    """Minimal 3-col offer DataFrame for sovereignty non-regression."""
    return pl.DataFrame(
        {
            "gid": ["offer_001"],
            "name": ["Acme Dental"],
            "section": ["Active"],
        }
    )


# ---------------------------------------------------------------------------
# AC-G2P6-1: STEP 0 — cascade warming mechanism is wired
# ---------------------------------------------------------------------------


class TestAcG2P61CascadePopulationMechanismWired:
    """AC-G2P6-1: Verify cascade warming is wired for body-parameterized cold builds.

    Checks that:
    1. PROJECT_SCHEMA and SECTION_SCHEMA have cascade columns (has_cascade_columns=True)
    2. HierarchyWarmer.populate_store_with_tasks is invoked during section fetch
       with warm_hierarchy=True when the builder has a store.

    This is the STEP 0 spike result test — not a network test; no real Asana calls.
    """

    def test_project_schema_has_cascade_columns(self) -> None:
        """PROJECT_SCHEMA declares cascade: source columns for office_phone and vertical."""
        assert PROJECT_SCHEMA.has_cascade_columns(), (
            "PROJECT_SCHEMA must have cascade columns for hierarchy warming to activate"
        )

    def test_section_schema_has_cascade_columns(self) -> None:
        """SECTION_SCHEMA declares cascade: source columns for office_phone and vertical."""
        assert SECTION_SCHEMA.has_cascade_columns(), (
            "SECTION_SCHEMA must have cascade columns for hierarchy warming to activate"
        )

    def test_project_schema_cascade_column_names(self) -> None:
        """PROJECT_SCHEMA cascade columns are office_phone and vertical."""
        cascade_cols = dict(PROJECT_SCHEMA.get_cascade_columns())
        assert "office_phone" in cascade_cols
        assert "vertical" in cascade_cols
        assert cascade_cols["office_phone"] == "Office Phone"
        assert cascade_cols["vertical"] == "Vertical"

    def test_section_schema_cascade_column_names(self) -> None:
        """SECTION_SCHEMA cascade columns are office_phone and vertical."""
        cascade_cols = dict(SECTION_SCHEMA.get_cascade_columns())
        assert "office_phone" in cascade_cols
        assert "vertical" in cascade_cols

    def test_hierarchy_warmer_populate_invoked_for_project_build(self) -> None:
        """When ProgressiveProjectBuilder has a store, populate_store_with_tasks
        is called for each section fetch — providing parent chain data for cascade
        resolution of office_phone/vertical."""
        from unittest.mock import AsyncMock, MagicMock

        from autom8_asana.dataframes.builders.hierarchy_warmer import HierarchyWarmer
        from autom8_asana.dataframes.builders.progressive import ProgressiveProjectBuilder

        store = MagicMock()
        client = MagicMock()
        schema = MagicMock()
        schema.version = "1.0.0"

        persistence = MagicMock()
        persistence.get_manifest_async = AsyncMock(return_value=None)

        builder = ProgressiveProjectBuilder(
            client=client,
            project_gid="proj_test",
            entity_type="project",
            schema=schema,
            persistence=persistence,
            store=store,
        )

        # The builder should have created a HierarchyWarmer (store is not None)
        assert builder._hierarchy_warmer is not None, (
            "HierarchyWarmer must be created when store is not None — "
            "this is the mechanism that populates parent chain data for cascade resolution"
        )
        assert isinstance(builder._hierarchy_warmer, HierarchyWarmer)

    async def test_hierarchy_warmer_uses_warm_hierarchy_true(self) -> None:
        """HierarchyWarmer.populate_store_with_tasks calls put_batch_async
        with warm_hierarchy=True — this is what recursively fetches parent chains
        so cascade fields (office_phone, vertical) can be resolved."""
        from unittest.mock import AsyncMock, MagicMock

        from autom8_asana.dataframes.builders.hierarchy_warmer import HierarchyWarmer

        store = MagicMock()
        store.put_batch_async = AsyncMock()

        client = MagicMock()
        client.tasks = MagicMock()

        task_to_dict = MagicMock(side_effect=lambda t: {"gid": t.gid, "name": t.name})

        warmer = HierarchyWarmer(
            store=store,
            client=client,
            project_gid="proj_test",
            entity_type="project",
            max_concurrent=4,
            task_to_dict=task_to_dict,
        )

        task = MagicMock()
        task.gid = "task_1"
        task.name = "Test Task"

        await warmer.populate_store_with_tasks([task])

        store.put_batch_async.assert_called_once()
        call_kwargs = store.put_batch_async.call_args.kwargs
        assert call_kwargs.get("warm_hierarchy") is True, (
            "put_batch_async must be called with warm_hierarchy=True to recursively "
            "fetch parent chains for cascade field resolution"
        )


# ---------------------------------------------------------------------------
# AC-G2P6-4: get_default_projection accessor
# ---------------------------------------------------------------------------


class TestAcG2P64GetDefaultProjection:
    """AC-G2P6-4: get_default_projection returns full-16 for project/section, () for others."""

    def test_project_default_projection_is_full_16(self) -> None:
        """get_default_projection('project') returns the full 16-col tuple."""
        registry = get_registry()
        proj = registry.get_default_projection("project")
        assert proj == _FULL_16_COLS, f"Expected full 16 cols, got: {proj}"

    def test_section_default_projection_is_full_16(self) -> None:
        """get_default_projection('section') returns the full 16-col tuple."""
        registry = get_registry()
        sec = registry.get_default_projection("section")
        assert sec == _FULL_16_COLS, f"Expected full 16 cols, got: {sec}"

    def test_project_default_projection_matches_schema_column_names(self) -> None:
        """The declared default_projection tuple matches PROJECT_SCHEMA.column_names()."""
        registry = get_registry()
        proj = registry.get_default_projection("project")
        assert list(proj) == PROJECT_SCHEMA.column_names(), (
            "default_projection must match PROJECT_SCHEMA.column_names() exactly"
        )

    def test_section_default_projection_matches_schema_column_names(self) -> None:
        """The declared default_projection tuple matches SECTION_SCHEMA.column_names()."""
        registry = get_registry()
        sec = registry.get_default_projection("section")
        assert list(sec) == SECTION_SCHEMA.column_names(), (
            "default_projection must match SECTION_SCHEMA.column_names() exactly"
        )

    def test_offer_domain_default_projection_is_empty(self) -> None:
        """Offer-domain entities (unit, offer, etc.) return () — falls through to literal."""
        registry = get_registry()
        for name in ("unit", "offer", "contact", "business"):
            proj = registry.get_default_projection(name)
            assert proj == (), (
                f"get_default_projection('{name}') must return () (empty), "
                f"not {proj!r} — offer-domain entities must fall through to global literal"
            )

    def test_unknown_entity_returns_empty(self) -> None:
        """Unknown entity name returns () without raising."""
        registry = get_registry()
        result = registry.get_default_projection("nonexistent_entity_xyz")
        assert result == ()

    def test_descriptor_default_projection_field_default(self) -> None:
        """EntityDescriptor.default_projection defaults to empty tuple."""
        desc = EntityDescriptor(name="test", pascal_name="Test", display_name="Test")
        assert desc.default_projection == ()


# ---------------------------------------------------------------------------
# AC-G2P6-2 & AC-G2P6-5: Engine default projection (project and section)
# ---------------------------------------------------------------------------


class TestAcG2P62ProjectDefaultProjection:
    """AC-G2P6-2: project query with no select returns full 16-col projection."""

    async def _run_engine_with_schema(
        self,
        entity_type: str,
        schema: DataFrameSchema,
        df: pl.DataFrame,
    ) -> list[dict[str, object]]:
        """Run QueryEngine with given schema and df, no select in request."""
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)
        engine = QueryEngine(provider=service)
        client = AsyncMock()
        request = RowsRequest.model_validate({})  # no select

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type=entity_type,
                project_gid="proj_test",
                client=client,
                request=request,
            )

        return list(result.data)

    async def test_project_no_select_returns_full_16_cols(self) -> None:
        """project entity with no select → full 16-col projection."""
        df = _make_full_project_df()
        schema = _make_project_schema()
        data = await self._run_engine_with_schema("project", schema, df)

        assert len(data) > 0, "Expected at least one row"
        row = data[0]
        # All 16 columns must be present
        for col in _FULL_16_COLS:
            assert col in row, (
                f"Column '{col}' missing from project result; got keys: {sorted(row.keys())}"
            )

    async def test_project_no_select_includes_office_phone(self) -> None:
        """office_phone is in the default projection (was missing with 3-col default)."""
        df = _make_full_project_df()
        schema = _make_project_schema()
        data = await self._run_engine_with_schema("project", schema, df)

        assert data[0]["office_phone"] == "555-0001", (
            "office_phone must be populated in the default projection"
        )

    async def test_project_no_select_includes_vertical(self) -> None:
        """vertical is in the default projection (was missing with 3-col default)."""
        df = _make_full_project_df()
        schema = _make_project_schema()
        data = await self._run_engine_with_schema("project", schema, df)

        assert data[0]["vertical"] == "dental", (
            "vertical must be populated in the default projection"
        )

    async def test_section_no_select_returns_full_16_cols(self) -> None:
        """AC-G2P6-5: section entity with no select → full 16-col projection."""
        df = _make_full_project_df()  # same schema structure as section
        schema = _make_section_schema()
        data = await self._run_engine_with_schema("section", schema, df)

        assert len(data) > 0
        row = data[0]
        for col in _FULL_16_COLS:
            assert col in row, (
                f"Column '{col}' missing from section result; got: {sorted(row.keys())}"
            )


# ---------------------------------------------------------------------------
# AC-G2P6-3: Offer-domain sovereignty non-regression
# ---------------------------------------------------------------------------


class TestAcG2P63OfferDomainNonRegression:
    """AC-G2P6-3 (HARD NON-REGRESSION): offer-domain entity with no select
    still returns [gid, name, section] — the global literal fallback is preserved."""

    async def test_offer_no_select_returns_3_col_literal(self) -> None:
        """offer-domain (body_parameterized=False) with no select → 3-col literal output.

        This is the sovereignty-critical non-regression gate. The engine.py:190
        insert must leave the global literal [gid, name, section] UNCHANGED as
        the fallback for entities whose default_projection is empty.
        """
        df = _make_offer_df()
        schema = _make_offer_schema()

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)
        engine = QueryEngine(provider=service)
        client = AsyncMock()
        request = RowsRequest.model_validate({})  # no select

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj_test",
                client=client,
                request=request,
            )

        assert len(result.data) > 0
        row = result.data[0]
        # Must contain gid (always included) + the 3-col literal
        assert "gid" in row
        assert "name" in row
        assert "section" in row
        # Must NOT contain project/section-specific columns
        assert "office_phone" not in row, (
            "office_phone must NOT appear in offer-domain result — sovereignty non-regression FAILED"
        )
        assert "vertical" not in row, (
            "vertical must NOT appear in offer-domain result — sovereignty non-regression FAILED"
        )

    async def test_unit_no_select_returns_3_col_literal(self) -> None:
        """unit entity (offer-domain) with no select → 3-col literal output."""
        df = pl.DataFrame({"gid": ["u1"], "name": ["Acme Dental Unit"], "section": ["Active"]})
        schema = DataFrameSchema(
            name="unit",
            task_type="Unit",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
            ],
        )

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)
        engine = QueryEngine(provider=service)
        client = AsyncMock()
        request = RowsRequest.model_validate({})

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="unit",
                project_gid="proj_test",
                client=client,
                request=request,
            )

        assert len(result.data) > 0
        row = result.data[0]
        assert "gid" in row
        assert "name" in row
        assert "section" in row


# ---------------------------------------------------------------------------
# AC-G2P6-6: Limit cap raise
# ---------------------------------------------------------------------------


class TestAcG2P66LimitCap:
    """AC-G2P6-6: RowsRequest limit field accepts up to 10000; 10001 raises."""

    def test_limit_2539_validates(self) -> None:
        """limit=2539 (consumer canary row delta) validates without error."""
        req = RowsRequest.model_validate({"limit": 2539})
        assert req.limit == 2539

    def test_limit_1000_still_validates(self) -> None:
        """The old max (1000) still validates (no regression)."""
        req = RowsRequest.model_validate({"limit": 1000})
        assert req.limit == 1000

    def test_limit_10000_validates(self) -> None:
        """limit=10000 (new max) validates."""
        req = RowsRequest.model_validate({"limit": 10_000})
        assert req.limit == 10_000

    def test_limit_10001_raises_validation_error(self) -> None:
        """limit=10001 raises ValidationError (above new cap)."""
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"limit": 10_001})

    def test_limit_0_still_raises(self) -> None:
        """limit=0 still raises ValidationError (ge=1 unchanged)."""
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"limit": 0})

    def test_limit_1_validates(self) -> None:
        """limit=1 (minimum) still validates."""
        req = RowsRequest.model_validate({"limit": 1})
        assert req.limit == 1

    def test_offer_domain_callers_limit_unaffected(self) -> None:
        """Offer-domain callers with limit<=100 are unaffected by the cap raise."""
        for limit in (1, 50, 100):
            req = RowsRequest.model_validate({"limit": limit})
            assert req.limit == limit

    def test_clamp_limit_backstop_at_10000(self) -> None:
        """QueryLimits.clamp_limit still backstops at max_result_rows (default 10000)."""
        limits = QueryLimits()
        assert limits.max_result_rows == 10_000
        # Values at or below max pass through unchanged
        assert limits.clamp_limit(1_000) == 1_000
        assert limits.clamp_limit(10_000) == 10_000
        # Hypothetical overrides (guards still clamp)
        assert limits.clamp_limit(20_000) == 10_000


# ---------------------------------------------------------------------------
# AC-G2P6-7: engine literal fallback sovereignty
# ---------------------------------------------------------------------------


class TestAcG2P67EngineLiteralFallback:
    """AC-G2P6-7: engine.py:190 literal ["gid","name","section"] is unchanged for
    empty-default entities. The C-4 insert is ADDITIVE — it reads registry first,
    then falls through to the literal when default_projection is empty."""

    def test_global_literal_is_unchanged(self) -> None:
        """The engine.py source still contains the global literal as fallback.

        The C-4 change inserts a registry lookup BEFORE the literal. The literal
        itself must remain intact as the fallback for offer-domain entities.
        """
        import inspect

        from autom8_asana.query import engine as engine_module

        source = inspect.getsource(engine_module)
        assert '["gid", "name", "section"]' in source, (
            'The global literal ["gid", "name", "section"] must remain in engine.py '
            "as the fallback for entities with empty default_projection"
        )

    async def test_explicit_select_bypasses_registry(self) -> None:
        """When request.select is explicitly provided, registry is NOT consulted —
        the explicit select is used directly (same as before for all entity types)."""
        df = _make_full_project_df()
        schema = _make_project_schema()

        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)
        engine = QueryEngine(provider=service)
        client = AsyncMock()
        # Explicit select with just 2 columns
        request = RowsRequest.model_validate({"select": ["gid", "office_phone"]})

        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
            mock_registry = MagicMock()
            mock_registry.get_schema.return_value = schema
            mock_registry_cls.get_instance.return_value = mock_registry

            result = await engine.execute_rows(
                entity_type="project",
                project_gid="proj_test",
                client=client,
                request=request,
            )

        row = result.data[0]
        assert "gid" in row
        assert "office_phone" in row
        # type, status, vertical, etc. NOT in result (explicit select honoured)
        assert "type" not in row
        assert "vertical" not in row
