"""FM-5 ARM-B — two-sided discriminating canary for the honest-refusal contract.

Per ``discriminating-canary-doctrine`` and ``TDD-fm5-armb-honest-refusal-contract`` §5.

The canary is **two-sided** and **discriminating**: the RED arm is a deliberately-
broken INPUT (a request declaring a required column the project serve-boundary
cannot satisfy) that the live surface CORRECTLY REJECTS with a TYPED
``contract_complete=False`` signal — NEVER a defect injected into production code.
The GREEN arm flips the SAME fixture to a served column and the surface passes.
A fixture that cannot fire both arms is rejected (G-HALT).

The RED arm proves the gap FM-5 exists to make loud (``offer_id`` declared
required on a ``project`` frame, where it is ABSENT from the 16-column served
schema) raises the typed signal instead of a silent narrow frame / daily KeyError
/ $0-7-row fossil. The GREEN arm proves the gate does NOT over-fire on a served
column (``office_phone``), and — critically — uses an ALREADY-served column so it
does not depend on any Door-C schema widen landing (SEAM-2, deferred).

The S4 rite-disjoint critic RUNS this for the verified-realized verdict; this file
is authored in-rite (caps MODERATE).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.project import PROJECT_SCHEMA
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.models import RowsRequest
from autom8_asana.services.query_service import EntityQueryService

_PROJECT_GID = "1200653012566782"


def _project_frame() -> pl.DataFrame:
    """A small project frame whose columns are a subset of the served schema.

    ``office_phone`` is present (served, the GREEN arm target); ``offer_id`` is
    deliberately ABSENT — exactly the production project serve-boundary FM-5 must
    make loud (offer_id is a key column of the OFFER entity, not PROJECT).
    """
    return pl.DataFrame(
        {
            "gid": ["1", "2", "3"],
            "name": ["Acme", "Beta", "Gamma"],
            "section": ["Active", "Active", "Won"],
            "office_phone": ["555-0100", None, "555-0102"],
        }
    )


@pytest.fixture
def project_engine() -> QueryEngine:
    service = EntityQueryService()
    service.get_dataframe = AsyncMock(return_value=_project_frame())  # type: ignore[method-assign]
    return QueryEngine(provider=service)


@pytest.fixture
def mock_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def project_schema_registry():  # type: ignore[no-untyped-def]
    """Patch SchemaRegistry so the engine serves the real PROJECT_SCHEMA."""
    with patch("autom8_asana.query.engine.SchemaRegistry") as mock_registry_cls:
        mock_registry = MagicMock()
        mock_registry.get_schema.return_value = PROJECT_SCHEMA
        mock_registry_cls.get_instance.return_value = mock_registry
        yield mock_registry


class TestFm5ArmBCanary:
    """Two-sided discriminating canary on the FM-5 ARM-B honest-refusal contract."""

    async def test_red_arm_declared_unservable_column_fires_typed_signal(
        self,
        project_engine: QueryEngine,
        mock_client: AsyncMock,
        project_schema_registry: object,
    ) -> None:
        """RED arm (bites): a declared-but-unservable column raises the typed signal.

        Deliberately-broken INPUT: ``required_columns=["offer_id"]`` against a
        ``project`` frame. ``offer_id`` is ABSENT from the 16-column PROJECT_SCHEMA,
        so the live surface CORRECTLY REJECTS the declaration with
        ``contract_complete=False`` and names the unservable column — not a
        KeyError, not a silent drop, not a fossil.
        """
        request = RowsRequest.model_validate({"required_columns": ["offer_id"]})
        result = await project_engine.execute_rows(
            entity_type="project",
            project_gid=_PROJECT_GID,
            client=mock_client,
            request=request,
        )

        assert result.meta.contract_complete is False
        assert "offer_id" in result.meta.unservable_required_columns
        # The signal is TYPED, not a crash and not a $0/7-row fossil: rows still serve.
        assert result.meta.returned_count == 3

    async def test_green_arm_declared_served_column_passes(
        self,
        project_engine: QueryEngine,
        mock_client: AsyncMock,
        project_schema_registry: object,
    ) -> None:
        """GREEN arm (passes): a declared-AND-served column does not fire.

        Same fixture, flipped INPUT: ``required_columns=["office_phone"]`` — a
        column the PROJECT_SCHEMA serves. The gate does NOT over-fire. Uses an
        already-served column, so it does NOT depend on any Door-C widen landing.
        """
        request = RowsRequest.model_validate({"required_columns": ["office_phone"]})
        result = await project_engine.execute_rows(
            entity_type="project",
            project_gid=_PROJECT_GID,
            client=mock_client,
            request=request,
        )

        assert result.meta.contract_complete is True
        assert result.meta.unservable_required_columns == []

    async def test_two_way_door_no_declaration_preserves_today_behavior(
        self,
        project_engine: QueryEngine,
        mock_client: AsyncMock,
        project_schema_registry: object,
    ) -> None:
        """A non-declaring consumer gets today's behavior (additive two-way door)."""
        request = RowsRequest.model_validate({})
        result = await project_engine.execute_rows(
            entity_type="project",
            project_gid=_PROJECT_GID,
            client=mock_client,
            request=request,
        )

        assert result.meta.contract_complete is True
        assert result.meta.unservable_required_columns == []
        assert result.meta.column_manifest is None

    async def test_no_select_path_carries_typed_signal_not_silent_drop(
        self,
        project_engine: QueryEngine,
        mock_client: AsyncMock,
        project_schema_registry: object,
    ) -> None:
        """The no-select/default-projection path now carries the typed signal.

        Today ``UnknownFieldError`` fires ONLY on an explicit ``select`` of an
        unknown field; the no-select path silently narrows the frame. ARM-B closes
        that gap: with NO ``select`` but a declared ``required_columns=["offer_id"]``,
        the contract still fires ``contract_complete=False`` — the genuine
        silent-drop site now emits an honest typed signal. The belt-and-braces
        ``column_manifest`` is populated (a contract was declared) and, correctly,
        does NOT list the unservable column among served.
        """
        request = RowsRequest.model_validate({"required_columns": ["offer_id"]})
        result = await project_engine.execute_rows(
            entity_type="project",
            project_gid=_PROJECT_GID,
            client=mock_client,
            request=request,
        )

        assert result.meta.contract_complete is False
        assert "offer_id" in result.meta.unservable_required_columns
        assert result.meta.column_manifest is not None
        assert "offer_id" not in result.meta.column_manifest["served"]  # type: ignore[operator]


class TestDeriveColumnContractUnit:
    """Direct unit coverage of the schema-membership derivation (ADR D3)."""

    def test_completeness_uses_schema_not_df_columns(self) -> None:
        """Immunity to a 100%-NULL served column: SCHEMA membership, never df.columns.

        The production project parquet carries a 100%-NULL ``offer_id`` (present in
        the physical frame, absent from the served schema). A physical-presence
        (``df.columns``) check would mis-read the contract as COMPLETE. The
        schema-membership derivation correctly fires INCOMPLETE even though the
        column is physically present in the frame.
        """
        engine = QueryEngine(provider=MagicMock())
        schema = DataFrameSchema(
            name="project",
            task_type="Project",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("office_phone", "Utf8", nullable=True),
            ],
        )
        # df HAS offer_id (100% null) — the presence-check trap.
        df = pl.DataFrame({"gid": ["1", "2"], "offer_id": [None, None]})

        complete, unservable, manifest = engine._derive_column_contract(
            schema=schema,
            required_columns=["offer_id"],
            df=df,
        )

        assert complete is False
        assert unservable == ["offer_id"]
        # offer_id is in df.columns but NOT in the served schema, so it is not "served".
        assert manifest is not None
        assert "offer_id" not in manifest["served"]  # type: ignore[operator]

    def test_non_declaring_request_is_two_way_door_identity(self) -> None:
        engine = QueryEngine(provider=MagicMock())
        schema = DataFrameSchema(
            name="project",
            task_type="Project",
            columns=[ColumnDef("gid", "Utf8", nullable=False)],
        )
        df = pl.DataFrame({"gid": ["1"]})

        complete, unservable, manifest = engine._derive_column_contract(
            schema=schema,
            required_columns=None,
            df=df,
        )

        assert complete is True
        assert unservable == []
        assert manifest is None
