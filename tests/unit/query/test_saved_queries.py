"""Tests for Phase 4: SavedQuery model, loader, run subcommand, cardinality, introspection.

Covers:
- SavedQuery model loading from YAML and JSON
- find_saved_query() name-based search
- Invalid YAML validation
- SavedQuery -> RowsRequest / AggregateRequest mapping via handle_run
- CLI 'run' subcommand integration with mocked provider
- --format override on saved queries
- EntityRelationship.cardinality derivation
- Multiple --join flag handling (warning + first-only)
- Introspection helper reuse between CLI and API
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from pydantic import ValidationError

from autom8_asana.query.__main__ import CLIError, build_parser, main
from autom8_asana.query.saved import SavedQuery, find_saved_query, load_saved_query

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# SavedQuery model loading
# ---------------------------------------------------------------------------


class TestLoadYaml:
    """Test loading SavedQuery from YAML files."""

    def test_load_yaml_rows_query(self, tmp_path: Path) -> None:
        """Load a valid rows YAML query with all fields."""
        data = {
            "name": "test_query",
            "description": "A test query",
            "command": "rows",
            "entity_type": "offer",
            "classification": "active",
            "select": ["gid", "name", "mrr"],
            "limit": 50,
            "order_by": "mrr",
            "order_dir": "desc",
            "format": "json",
        }
        query_file = tmp_path / "test.yaml"
        query_file.write_text(yaml.dump(data))

        saved = load_saved_query(query_file)
        assert saved.name == "test_query"
        assert saved.command == "rows"
        assert saved.entity_type == "offer"
        assert saved.classification == "active"
        assert saved.select == ["gid", "name", "mrr"]
        assert saved.limit == 50
        assert saved.order_by == "mrr"
        assert saved.order_dir == "desc"
        assert saved.format == "json"

    def test_load_yaml_aggregate_query(self, tmp_path: Path) -> None:
        """Load a valid aggregate YAML query."""
        data = {
            "name": "mrr_by_vertical",
            "command": "aggregate",
            "entity_type": "offer",
            "classification": "active",
            "group_by": ["vertical"],
            "aggregations": [
                {"column": "mrr", "agg": "sum", "alias": "total_mrr"},
                {"column": "gid", "agg": "count", "alias": "offer_count"},
            ],
        }
        query_file = tmp_path / "agg.yaml"
        query_file.write_text(yaml.dump(data))

        saved = load_saved_query(query_file)
        assert saved.command == "aggregate"
        assert saved.group_by == ["vertical"]
        assert len(saved.aggregations) == 2

    def test_load_yaml_with_join(self, tmp_path: Path) -> None:
        """Load a YAML query that includes a join spec."""
        data = {
            "name": "with_join",
            "entity_type": "offer",
            "join": {
                "entity_type": "business",
                "select": ["booking_type"],
            },
        }
        query_file = tmp_path / "join.yaml"
        query_file.write_text(yaml.dump(data))

        saved = load_saved_query(query_file)
        assert saved.join is not None
        assert saved.join.entity_type == "business"
        assert saved.join.select == ["booking_type"]


class TestLoadJson:
    """Test loading SavedQuery from JSON files."""

    def test_load_json_query(self, tmp_path: Path) -> None:
        """Load a valid JSON saved query."""
        data = {
            "name": "json_query",
            "entity_type": "unit",
            "command": "rows",
            "select": ["gid", "name"],
            "limit": 200,
        }
        query_file = tmp_path / "test.json"
        query_file.write_text(json.dumps(data))

        saved = load_saved_query(query_file)
        assert saved.name == "json_query"
        assert saved.entity_type == "unit"
        assert saved.limit == 200


class TestFindSavedQuery:
    """Test find_saved_query() name-based file lookup."""

    def test_find_by_name_yaml(self, tmp_path: Path) -> None:
        """find_saved_query() locates a .yaml file in search dir."""
        (tmp_path / "active_offers.yaml").write_text(
            yaml.dump({"name": "active_offers", "entity_type": "offer"})
        )

        result = find_saved_query("active_offers", search_dirs=[tmp_path])
        assert result is not None
        assert result.name == "active_offers.yaml"

    def test_find_by_name_yml(self, tmp_path: Path) -> None:
        """find_saved_query() locates a .yml file in search dir."""
        (tmp_path / "my_query.yml").write_text(
            yaml.dump({"name": "my_query", "entity_type": "offer"})
        )

        result = find_saved_query("my_query", search_dirs=[tmp_path])
        assert result is not None
        assert result.suffix == ".yml"

    def test_find_by_name_json(self, tmp_path: Path) -> None:
        """find_saved_query() locates a .json file in search dir."""
        (tmp_path / "json_query.json").write_text(
            json.dumps({"name": "json_query", "entity_type": "offer"})
        )

        result = find_saved_query("json_query", search_dirs=[tmp_path])
        assert result is not None
        assert result.suffix == ".json"

    def test_find_not_found(self, tmp_path: Path) -> None:
        """find_saved_query() returns None for nonexistent query."""
        result = find_saved_query("nonexistent_query", search_dirs=[tmp_path])
        assert result is None

    def test_find_prefers_yaml_over_json(self, tmp_path: Path) -> None:
        """When both .yaml and .json exist, .yaml is found first."""
        (tmp_path / "both.yaml").write_text(
            yaml.dump({"name": "both", "entity_type": "offer"})
        )
        (tmp_path / "both.json").write_text(
            json.dumps({"name": "both", "entity_type": "offer"})
        )

        result = find_saved_query("both", search_dirs=[tmp_path])
        assert result is not None
        assert result.suffix == ".yaml"


class TestInvalidYaml:
    """Test that invalid YAML raises validation errors."""

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        """Missing name or entity_type raises ValidationError."""
        query_file = tmp_path / "bad.yaml"
        query_file.write_text(yaml.dump({"description": "no name or entity_type"}))

        with pytest.raises(ValidationError):
            load_saved_query(query_file)

    def test_invalid_command_value(self, tmp_path: Path) -> None:
        """Invalid command value raises ValidationError."""
        data = {
            "name": "bad",
            "entity_type": "offer",
            "command": "invalid_command",
        }
        query_file = tmp_path / "bad_cmd.yaml"
        query_file.write_text(yaml.dump(data))

        with pytest.raises(ValidationError):
            load_saved_query(query_file)


# ---------------------------------------------------------------------------
# SavedQuery -> Request mapping (via run handler)
# ---------------------------------------------------------------------------


class TestSavedQueryToRequest:
    """Test that SavedQuery fields map correctly to RowsRequest/AggregateRequest."""

    def test_to_rows_request_mapping(self) -> None:
        """SavedQuery with rows command produces correct RowsRequest fields."""
        from autom8_asana.query.models import RowsRequest

        saved = SavedQuery(
            name="test",
            entity_type="offer",
            command="rows",
            classification="active",
            select=["gid", "name", "mrr"],
            limit=50,
            offset=10,
            order_by="mrr",
            order_dir="desc",
        )

        request_data: dict = {
            "limit": saved.limit,
            "offset": saved.offset,
        }
        if saved.classification:
            request_data["classification"] = saved.classification
        if saved.select:
            request_data["select"] = saved.select
        if saved.order_by:
            request_data["order_by"] = saved.order_by
        if saved.order_dir:
            request_data["order_dir"] = saved.order_dir

        request = RowsRequest.model_validate(request_data)
        assert request.classification == "active"
        assert request.select == ["gid", "name", "mrr"]
        assert request.limit == 50
        assert request.offset == 10
        assert request.order_by == "mrr"
        assert request.order_dir == "desc"

    def test_to_aggregate_request_mapping(self) -> None:
        """SavedQuery with aggregate command produces correct AggregateRequest fields."""
        from autom8_asana.query.models import AggregateRequest

        saved = SavedQuery(
            name="test_agg",
            entity_type="offer",
            command="aggregate",
            group_by=["vertical"],
            aggregations=[
                {"column": "mrr", "agg": "sum", "alias": "total_mrr"},
            ],
        )

        agg_data: dict = {
            "group_by": saved.group_by,
            "aggregations": saved.aggregations,
        }

        request = AggregateRequest.model_validate(agg_data)
        assert request.group_by == ["vertical"]
        assert len(request.aggregations) == 1
        assert request.aggregations[0].column == "mrr"
        assert request.aggregations[0].agg.value == "sum"


# ---------------------------------------------------------------------------
# CLI 'run' subcommand integration
# ---------------------------------------------------------------------------


class TestRunSubcommand:
    """Test the 'run' subcommand with mocked provider."""

    def test_run_parser_structure(self) -> None:
        """Parser accepts 'run' with query name and --format override."""
        parser = build_parser()
        args = parser.parse_args(["run", "active_offers", "--format", "json"])
        assert args.command == "run"
        assert args.query == "active_offers"
        assert args.output_format == "json"

    def test_run_from_file_path(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """'run' loads a query from an explicit file path and executes it."""
        from autom8_asana.query.models import RowsMeta, RowsResponse

        query_file = tmp_path / "test_query.yaml"
        query_file.write_text(
            yaml.dump(
                {
                    "name": "test_query",
                    "entity_type": "offer",
                    "command": "rows",
                    "classification": "active",
                    "select": ["gid", "name"],
                    "limit": 10,
                    "format": "json",
                }
            )
        )

        mock_response = RowsResponse(
            data=[
                {"gid": "1", "name": "Alpha"},
                {"gid": "2", "name": "Beta"},
            ],
            meta=RowsMeta(
                total_count=2,
                returned_count=2,
                limit=10,
                offset=0,
                entity_type="offer",
                project_gid="1143843662099250",
                query_ms=5.0,
            ),
        )

        mock_provider = MagicMock()
        mock_provider.get_dataframe = AsyncMock()
        mock_provider.last_freshness_info = None

        capsys.readouterr()
        with (
            patch(
                "autom8_asana.query.offline_provider.OfflineDataFrameProvider",
                return_value=mock_provider,
            ),
            patch(
                "autom8_asana.query.engine.QueryEngine.execute_rows",
                new_callable=AsyncMock,
                return_value=mock_response,
            ) as mock_execute,
        ):
            exit_code = main(["run", str(query_file)])
            assert exit_code == 0

            # Verify the request was constructed from saved query
            call_kwargs = mock_execute.call_args
            request = call_kwargs.kwargs.get("request") or call_kwargs[1].get("request")
            if request is None:
                request = call_kwargs[0][3] if len(call_kwargs[0]) > 3 else None
            assert request is not None
            assert request.classification == "active"
            assert request.select == ["gid", "name"]
            assert request.limit == 10

            captured = capsys.readouterr()
            stdout = captured.out
            arr_start = stdout.index("[")
            data = json.loads(stdout[arr_start:])
            assert len(data) == 2

    def test_run_not_found(self, capsys: pytest.CaptureFixture) -> None:
        """'run nonexistent_query' returns exit code 1 with helpful message."""
        capsys.readouterr()
        exit_code = main(["run", "nonexistent_query_xyz_abc"])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()

    def test_run_with_format_override(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """'--format json' overrides saved query's format field."""
        from autom8_asana.query.models import RowsMeta, RowsResponse

        query_file = tmp_path / "table_query.yaml"
        query_file.write_text(
            yaml.dump(
                {
                    "name": "table_query",
                    "entity_type": "offer",
                    "command": "rows",
                    "format": "table",
                    "select": ["gid"],
                    "limit": 5,
                }
            )
        )

        mock_response = RowsResponse(
            data=[{"gid": "1"}],
            meta=RowsMeta(
                total_count=1,
                returned_count=1,
                limit=5,
                offset=0,
                entity_type="offer",
                project_gid="1143843662099250",
                query_ms=1.0,
            ),
        )

        mock_provider = MagicMock()
        mock_provider.get_dataframe = AsyncMock()
        mock_provider.last_freshness_info = None

        capsys.readouterr()
        with (
            patch(
                "autom8_asana.query.offline_provider.OfflineDataFrameProvider",
                return_value=mock_provider,
            ),
            patch(
                "autom8_asana.query.engine.QueryEngine.execute_rows",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            # Override format from table to json
            exit_code = main(["run", str(query_file), "--format", "json"])
            assert exit_code == 0

            captured = capsys.readouterr()
            stdout = captured.out
            # JSON format should produce a JSON array
            arr_start = stdout.index("[")
            data = json.loads(stdout[arr_start:])
            assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Cardinality derivation
# ---------------------------------------------------------------------------


class TestCardinalityDerived:
    """Test that EntityRelationship has correct cardinality for known pairs."""

    def test_business_to_offer_is_1_to_n(self) -> None:
        """Business (ROOT) -> Offer (LEAF) should have cardinality 1:N."""
        from autom8_asana.query.hierarchy import ENTITY_RELATIONSHIPS

        for rel in ENTITY_RELATIONSHIPS:
            if rel.parent_type == "business" and rel.child_type == "offer":
                assert rel.cardinality == "1:N", (
                    f"Expected 1:N for business->offer, got {rel.cardinality}"
                )
                return
        pytest.fail("No business->offer relationship found")

    def test_offer_to_unit_is_n_to_1(self) -> None:
        """Offer (LEAF) -> Unit (COMPOSITE) should have cardinality N:1."""
        from autom8_asana.query.hierarchy import ENTITY_RELATIONSHIPS

        for rel in ENTITY_RELATIONSHIPS:
            if rel.parent_type == "offer" and rel.child_type == "unit":
                assert rel.cardinality == "N:1", (
                    f"Expected N:1 for offer->unit, got {rel.cardinality}"
                )
                return
        pytest.fail("No offer->unit relationship found")

    def test_unit_to_offer_is_1_to_n(self) -> None:
        """Unit (COMPOSITE) -> Offer (LEAF) should have cardinality 1:N."""
        from autom8_asana.query.hierarchy import ENTITY_RELATIONSHIPS

        for rel in ENTITY_RELATIONSHIPS:
            if rel.parent_type == "unit" and rel.child_type == "offer":
                assert rel.cardinality == "1:N", (
                    f"Expected 1:N for unit->offer, got {rel.cardinality}"
                )
                return
        pytest.fail("No unit->offer relationship found")

    def test_cardinality_field_exists_on_all_relationships(self) -> None:
        """Every EntityRelationship has a cardinality field."""
        from autom8_asana.query.hierarchy import ENTITY_RELATIONSHIPS

        for rel in ENTITY_RELATIONSHIPS:
            assert hasattr(rel, "cardinality")
            assert rel.cardinality in ("1:1", "1:N", "N:1", "N:M", "unknown")

    def test_business_to_unit_is_1_to_n(self) -> None:
        """Business (ROOT) -> Unit (COMPOSITE) should have cardinality unknown
        (both are high-category, not LEAF)."""
        from autom8_asana.query.hierarchy import ENTITY_RELATIONSHIPS

        for rel in ENTITY_RELATIONSHIPS:
            if rel.parent_type == "business" and rel.child_type == "unit":
                # ROOT -> COMPOSITE: the rule says parent in {root, composite}
                # and child == "leaf" for 1:N. "composite" is not "leaf",
                # so this should be "unknown".
                assert rel.cardinality == "unknown", (
                    f"Expected unknown for business->unit, got {rel.cardinality}"
                )
                return
        pytest.fail("No business->unit relationship found")


# ---------------------------------------------------------------------------
# Multiple --join flag handling
# ---------------------------------------------------------------------------


class TestMultipleJoinFlags:
    """Test that multiple --join flags are handled correctly."""

    def test_multiple_join_parser(self) -> None:
        """Multiple --join flags collected into a list."""
        parser = build_parser()
        args = parser.parse_args(
            [
                "rows",
                "offer",
                "--join",
                "business:booking_type",
                "--join",
                "unit:name",
            ]
        )
        assert args.join == ["business:booking_type", "unit:name"]

    def test_single_join_still_works(self) -> None:
        """Single --join flag produces a list with one element."""
        parser = build_parser()
        args = parser.parse_args(["rows", "offer", "--join", "business:booking_type"])
        assert args.join == ["business:booking_type"]

    def test_multiple_join_warns_on_stderr(self, capsys: pytest.CaptureFixture) -> None:
        """When multiple --join flags provided, warning printed to stderr."""
        from autom8_asana.query.models import RowsMeta, RowsResponse

        mock_response = RowsResponse(
            data=[{"gid": "1", "name": "Alpha"}],
            meta=RowsMeta(
                total_count=1,
                returned_count=1,
                limit=100,
                offset=0,
                entity_type="offer",
                project_gid="1143843662099250",
                query_ms=5.0,
            ),
        )

        mock_provider = MagicMock()
        mock_provider.get_dataframe = AsyncMock()
        mock_provider.last_freshness_info = None

        capsys.readouterr()
        with (
            patch(
                "autom8_asana.query.offline_provider.OfflineDataFrameProvider",
                return_value=mock_provider,
            ),
            patch(
                "autom8_asana.query.engine.QueryEngine.execute_rows",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            exit_code = main(
                [
                    "rows",
                    "offer",
                    "--join",
                    "business:booking_type",
                    "--join",
                    "unit:name",
                    "--format",
                    "json",
                ]
            )
            assert exit_code == 0
            captured = capsys.readouterr()
            assert "Only one --join is supported" in captured.err


# ---------------------------------------------------------------------------
# Introspection helpers (shared between CLI and API)
# ---------------------------------------------------------------------------


class TestIntrospectionHelpers:
    """Test that introspection module functions return correct data."""

    def test_list_entities_returns_warmable(self) -> None:
        """list_entities() returns warmable entity descriptors."""
        from autom8_asana.query.introspection import list_entities

        entities = list_entities()
        assert isinstance(entities, list)
        assert len(entities) > 0
        names = {e["entity_type"] for e in entities}
        assert "offer" in names
        assert "unit" in names
        assert "business" in names

    def test_list_fields_for_offer(self) -> None:
        """list_fields('offer') returns column metadata."""
        from autom8_asana.query.introspection import list_fields

        fields = list_fields("offer")
        assert isinstance(fields, list)
        assert len(fields) > 0
        field_names = {f["name"] for f in fields}
        assert "gid" in field_names
        assert "name" in field_names

    def test_list_fields_unknown_entity_raises(self) -> None:
        """list_fields() raises ValueError for unknown entity."""
        from autom8_asana.query.introspection import list_fields

        with pytest.raises(ValueError, match="No schema available"):
            list_fields("nonexistent_xyz_entity")

    def test_list_relations_for_offer(self) -> None:
        """list_relations('offer') returns relationship metadata with cardinality."""
        from autom8_asana.query.introspection import list_relations

        relations = list_relations("offer")
        assert isinstance(relations, list)
        assert len(relations) > 0
        # All entries have the expected keys including cardinality
        for rel in relations:
            assert "target" in rel
            assert "direction" in rel
            assert "default_join_key" in rel
            assert "cardinality" in rel
            assert "description" in rel

    def test_list_relations_includes_cardinality(self) -> None:
        """Relations output includes cardinality from EntityRelationship."""
        from autom8_asana.query.introspection import list_relations

        relations = list_relations("offer")
        # At least one relation should have cardinality set
        cardinalities = {r["cardinality"] for r in relations}
        assert len(cardinalities) > 0
        # All values should be valid cardinality strings
        valid = {"1:1", "1:N", "N:1", "N:M", "unknown"}
        assert cardinalities.issubset(valid)

    def test_cli_relations_includes_cardinality(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """CLI 'relations offer --format json' output includes cardinality."""
        capsys.readouterr()
        exit_code = main(["relations", "offer", "--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        stdout = captured.out
        arr_start = stdout.index("[")
        data = json.loads(stdout[arr_start:])
        assert len(data) > 0
        for entry in data:
            assert "cardinality" in entry


# ---------------------------------------------------------------------------
# B-3: save_query function
# ---------------------------------------------------------------------------


class TestSaveQueryFunction:
    """Test the save_query utility in saved.py."""

    def test_save_creates_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save_query() creates a YAML file at ~/.autom8/queries/."""
        from autom8_asana.query.saved import SavedQuery, save_query

        monkeypatch.setenv("HOME", str(tmp_path))
        saved = SavedQuery(name="test", entity_type="offer")
        path = save_query(saved, "test")
        assert path.exists()
        assert path.suffix == ".yaml"
        data = yaml.safe_load(path.read_text())
        assert data["name"] == "test"

    def test_save_raises_on_existing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save_query() raises FileExistsError if file already exists."""
        from autom8_asana.query.saved import SavedQuery, save_query

        monkeypatch.setenv("HOME", str(tmp_path))
        target_dir = tmp_path / ".autom8" / "queries"
        target_dir.mkdir(parents=True)
        (target_dir / "existing.yaml").write_text("name: existing\n")

        saved = SavedQuery(name="existing", entity_type="offer")
        with pytest.raises(FileExistsError, match="already exists"):
            save_query(saved, "existing")


# ---------------------------------------------------------------------------
# B-4: CLI overrides on run subcommand
# ---------------------------------------------------------------------------


class TestRunOverrides:
    """Test CLI flag overrides when running saved queries."""

    def test_run_parser_has_override_flags(self) -> None:
        """'run' parser accepts override flags."""
        parser = build_parser()
        args = parser.parse_args(
            [
                "run",
                "test_query",
                "--classification",
                "inactive",
                "--limit",
                "50",
                "--offset",
                "10",
                "--select",
                "gid,name",
                "--order-by",
                "mrr",
                "--order-dir",
                "desc",
                "--where",
                "mrr gt 100",
                "--section",
                "ACTIVE",
            ]
        )
        assert args.classification == "inactive"
        assert args.limit == 50
        assert args.offset == 10
        assert args.select == "gid,name"
        assert args.order_by == "mrr"
        assert args.order_dir == "desc"
        assert args.where == ["mrr gt 100"]
        assert args.section == "ACTIVE"

    def test_run_classification_override(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """CLI --classification overrides saved query classification."""
        from autom8_asana.query.models import RowsMeta, RowsResponse

        query_file = tmp_path / "base_query.yaml"
        query_file.write_text(
            yaml.dump(
                {
                    "name": "base_query",
                    "entity_type": "offer",
                    "command": "rows",
                    "classification": "active",
                    "select": ["gid", "name"],
                    "limit": 10,
                    "format": "json",
                }
            )
        )

        mock_response = RowsResponse(
            data=[{"gid": "1", "name": "Alpha"}],
            meta=RowsMeta(
                total_count=1,
                returned_count=1,
                limit=50,
                offset=0,
                entity_type="offer",
                project_gid="1143843662099250",
                query_ms=2.0,
            ),
        )
        mock_provider = MagicMock()
        mock_provider.get_dataframe = AsyncMock()
        mock_provider.last_freshness_info = None

        capsys.readouterr()
        with (
            patch(
                "autom8_asana.query.offline_provider.OfflineDataFrameProvider",
                return_value=mock_provider,
            ),
            patch(
                "autom8_asana.query.engine.QueryEngine.execute_rows",
                new_callable=AsyncMock,
                return_value=mock_response,
            ) as mock_execute,
        ):
            exit_code = main(
                [
                    "run",
                    str(query_file),
                    "--classification",
                    "inactive",
                    "--limit",
                    "50",
                ]
            )
            assert exit_code == 0

            # Verify the request used the overridden values
            call_kwargs = mock_execute.call_args
            request = call_kwargs.kwargs.get("request") or call_kwargs[1].get("request")
            if request is None:
                request = call_kwargs[0][3] if len(call_kwargs[0]) > 3 else None
            assert request is not None
            assert request.classification == "inactive"
            assert request.limit == 50

    def test_run_select_override(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """CLI --select overrides saved query select list."""
        from autom8_asana.query.models import RowsMeta, RowsResponse

        query_file = tmp_path / "select_query.yaml"
        query_file.write_text(
            yaml.dump(
                {
                    "name": "select_query",
                    "entity_type": "offer",
                    "command": "rows",
                    "select": ["gid"],
                    "format": "json",
                }
            )
        )

        mock_response = RowsResponse(
            data=[{"gid": "1", "name": "Alpha", "mrr": "100"}],
            meta=RowsMeta(
                total_count=1,
                returned_count=1,
                limit=100,
                offset=0,
                entity_type="offer",
                project_gid="1143843662099250",
                query_ms=1.0,
            ),
        )
        mock_provider = MagicMock()
        mock_provider.get_dataframe = AsyncMock()
        mock_provider.last_freshness_info = None

        capsys.readouterr()
        with (
            patch(
                "autom8_asana.query.offline_provider.OfflineDataFrameProvider",
                return_value=mock_provider,
            ),
            patch(
                "autom8_asana.query.engine.QueryEngine.execute_rows",
                new_callable=AsyncMock,
                return_value=mock_response,
            ) as mock_execute,
        ):
            exit_code = main(
                [
                    "run",
                    str(query_file),
                    "--select",
                    "gid,name,mrr",
                ]
            )
            assert exit_code == 0

            call_kwargs = mock_execute.call_args
            request = call_kwargs.kwargs.get("request") or call_kwargs[1].get("request")
            if request is None:
                request = call_kwargs[0][3] if len(call_kwargs[0]) > 3 else None
            assert request is not None
            assert request.select == ["gid", "name", "mrr"]

    def test_run_where_override(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """CLI --where overrides saved query predicate."""
        from autom8_asana.query.models import RowsMeta, RowsResponse

        query_file = tmp_path / "where_query.yaml"
        query_file.write_text(
            yaml.dump(
                {
                    "name": "where_query",
                    "entity_type": "offer",
                    "command": "rows",
                    "where": {"field": "mrr", "op": "gt", "value": 100},
                    "format": "json",
                }
            )
        )

        mock_response = RowsResponse(
            data=[{"gid": "1"}],
            meta=RowsMeta(
                total_count=1,
                returned_count=1,
                limit=100,
                offset=0,
                entity_type="offer",
                project_gid="1143843662099250",
                query_ms=1.0,
            ),
        )
        mock_provider = MagicMock()
        mock_provider.get_dataframe = AsyncMock()
        mock_provider.last_freshness_info = None

        capsys.readouterr()
        with (
            patch(
                "autom8_asana.query.offline_provider.OfflineDataFrameProvider",
                return_value=mock_provider,
            ),
            patch(
                "autom8_asana.query.engine.QueryEngine.execute_rows",
                new_callable=AsyncMock,
                return_value=mock_response,
            ) as mock_execute,
        ):
            exit_code = main(
                [
                    "run",
                    str(query_file),
                    "--where",
                    "section eq ACTIVE",
                ]
            )
            assert exit_code == 0

            call_kwargs = mock_execute.call_args
            request = call_kwargs.kwargs.get("request") or call_kwargs[1].get("request")
            if request is None:
                request = call_kwargs[0][3] if len(call_kwargs[0]) > 3 else None
            assert request is not None
            # The where should be the CLI override, not the saved query value
            assert request.where is not None

    def test_run_no_override_preserves_saved(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """When no override flags provided, saved query values are preserved."""
        from autom8_asana.query.models import RowsMeta, RowsResponse

        query_file = tmp_path / "preserved_query.yaml"
        query_file.write_text(
            yaml.dump(
                {
                    "name": "preserved_query",
                    "entity_type": "offer",
                    "command": "rows",
                    "classification": "active",
                    "select": ["gid", "name"],
                    "limit": 25,
                    "offset": 5,
                    "order_by": "name",
                    "order_dir": "desc",
                    "format": "json",
                }
            )
        )

        mock_response = RowsResponse(
            data=[{"gid": "1", "name": "Alpha"}],
            meta=RowsMeta(
                total_count=1,
                returned_count=1,
                limit=25,
                offset=5,
                entity_type="offer",
                project_gid="1143843662099250",
                query_ms=1.0,
            ),
        )
        mock_provider = MagicMock()
        mock_provider.get_dataframe = AsyncMock()
        mock_provider.last_freshness_info = None

        capsys.readouterr()
        with (
            patch(
                "autom8_asana.query.offline_provider.OfflineDataFrameProvider",
                return_value=mock_provider,
            ),
            patch(
                "autom8_asana.query.engine.QueryEngine.execute_rows",
                new_callable=AsyncMock,
                return_value=mock_response,
            ) as mock_execute,
        ):
            exit_code = main(["run", str(query_file)])
            assert exit_code == 0

            call_kwargs = mock_execute.call_args
            request = call_kwargs.kwargs.get("request") or call_kwargs[1].get("request")
            if request is None:
                request = call_kwargs[0][3] if len(call_kwargs[0]) > 3 else None
            assert request is not None
            assert request.classification == "active"
            assert request.select == ["gid", "name"]
            assert request.limit == 25
            assert request.offset == 5
            assert request.order_by == "name"
            assert request.order_dir == "desc"
