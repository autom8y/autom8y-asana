"""Tests for query/__main__.py: CLI argument parsing, subcommand routing, end-to-end with mock provider."""

from __future__ import annotations

import io
import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.query.__main__ import (
    CLIError,
    _coerce_value,
    build_parser,
    build_predicate,
    main,
    parse_agg_flag,
    parse_where_flag,
    parse_where_json,
    print_metadata,
    resolve_entity_type,
)
from autom8_asana.query.models import RowsMeta

# ---------------------------------------------------------------------------
# Value coercion
# ---------------------------------------------------------------------------


class TestCoerceValue:
    """Test best-effort type coercion for CLI values."""

    def test_coerce_int(self) -> None:
        assert _coerce_value("42") == 42
        assert isinstance(_coerce_value("42"), int)

    def test_coerce_negative_int(self) -> None:
        assert _coerce_value("-5") == -5

    def test_coerce_float(self) -> None:
        assert _coerce_value("3.14") == 3.14
        assert isinstance(_coerce_value("3.14"), float)

    def test_coerce_bool_true(self) -> None:
        assert _coerce_value("true") is True
        assert _coerce_value("True") is True

    def test_coerce_bool_false(self) -> None:
        assert _coerce_value("false") is False

    def test_coerce_string_fallback(self) -> None:
        assert _coerce_value("hello") == "hello"
        assert isinstance(_coerce_value("hello"), str)

    def test_coerce_phone_number(self) -> None:
        """Phone numbers stay as strings."""
        assert _coerce_value("+17175558734") == "+17175558734"


# ---------------------------------------------------------------------------
# Where flag parsing
# ---------------------------------------------------------------------------


class TestParseWhereFlag:
    """Test --where flag parsing."""

    def test_simple_eq(self) -> None:
        result = parse_where_flag("section eq ACTIVE")
        assert result == {"field": "section", "op": "eq", "value": "ACTIVE"}

    def test_numeric_gt(self) -> None:
        result = parse_where_flag("mrr gt 5000")
        assert result["field"] == "mrr"
        assert result["op"] == "gt"
        assert result["value"] == 5000

    def test_in_operator_splits_values(self) -> None:
        result = parse_where_flag("vertical in dental,chiropractic")
        assert result["op"] == "in"
        assert result["value"] == ["dental", "chiropractic"]

    def test_starts_with(self) -> None:
        result = parse_where_flag("office_phone starts_with +1")
        assert result["op"] == "starts_with"
        assert result["value"] == "+1"

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(CLIError, match="Invalid predicate"):
            parse_where_flag("bad")

    def test_unknown_operator_raises(self) -> None:
        with pytest.raises(CLIError, match="Unknown operator"):
            parse_where_flag("field zz value")


# ---------------------------------------------------------------------------
# Where JSON parsing
# ---------------------------------------------------------------------------


class TestParseWhereJson:
    """Test --where-json flag parsing."""

    def test_valid_comparison(self) -> None:
        result = parse_where_json('{"field": "mrr", "op": "gt", "value": 5000}')
        assert result["field"] == "mrr"

    def test_valid_and_group(self) -> None:
        raw = json.dumps({"and": [{"field": "mrr", "op": "gt", "value": 100}]})
        result = parse_where_json(raw)
        assert "and" in result

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(CLIError, match="Invalid JSON"):
            parse_where_json("{bad json")

    def test_non_object_raises(self) -> None:
        with pytest.raises(CLIError, match="expected a JSON object"):
            parse_where_json('"just a string"')


# ---------------------------------------------------------------------------
# Predicate building
# ---------------------------------------------------------------------------


class TestBuildPredicate:
    """Test combining --where and --where-json."""

    def test_none_when_empty(self) -> None:
        assert build_predicate(None, None) is None

    def test_single_where(self) -> None:
        result = build_predicate(["section eq ACTIVE"], None)
        assert result is not None
        assert result["field"] == "section"

    def test_multiple_where_and_group(self) -> None:
        result = build_predicate(["section eq ACTIVE", "mrr gt 100"], None)
        assert result is not None
        assert "and" in result
        assert len(result["and"]) == 2

    def test_where_json_only(self) -> None:
        result = build_predicate(None, '{"field": "mrr", "op": "gt", "value": 100}')
        assert result is not None
        assert result["field"] == "mrr"

    def test_both_where_and_where_json(self) -> None:
        result = build_predicate(
            ["section eq ACTIVE"],
            '{"field": "mrr", "op": "gt", "value": 100}',
        )
        assert result is not None
        assert "and" in result
        assert len(result["and"]) == 2


# ---------------------------------------------------------------------------
# Agg flag parsing
# ---------------------------------------------------------------------------


class TestParseAggFlag:
    """Test --agg flag parsing."""

    def test_simple_sum(self) -> None:
        result = parse_agg_flag("sum:mrr")
        assert result == {"column": "mrr", "agg": "sum"}

    def test_with_alias(self) -> None:
        result = parse_agg_flag("sum:mrr:total_revenue")
        assert result == {"column": "mrr", "agg": "sum", "alias": "total_revenue"}

    def test_count(self) -> None:
        result = parse_agg_flag("count:gid")
        assert result == {"column": "gid", "agg": "count"}

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(CLIError, match="Invalid aggregation"):
            parse_agg_flag("bad")

    def test_unknown_function_raises(self) -> None:
        with pytest.raises(CLIError, match="Unknown aggregation function"):
            parse_agg_flag("median:mrr")


# ---------------------------------------------------------------------------
# Entity resolution
# ---------------------------------------------------------------------------


class TestResolveEntityType:
    """Test entity type validation and project GID resolution."""

    def test_known_entity(self) -> None:
        entity_type, project_gid = resolve_entity_type("offer")
        assert entity_type == "offer"
        assert project_gid == "1143843662099250"

    def test_unknown_entity_raises(self) -> None:
        with pytest.raises(CLIError, match="Unknown entity type"):
            resolve_entity_type("nonexistent_xyz")


# ---------------------------------------------------------------------------
# Metadata output
# ---------------------------------------------------------------------------


class TestPrintMetadata:
    """Test metadata output to stderr."""

    def test_rows_metadata(self) -> None:
        meta = RowsMeta(
            total_count=100,
            returned_count=50,
            limit=50,
            offset=0,
            entity_type="offer",
            project_gid="123",
            query_ms=42.5,
            freshness="s3_offline",
        )
        buf = io.StringIO()
        print_metadata(meta, file=buf)
        output = buf.getvalue()
        assert "total: 100" in output
        assert "returned: 50" in output
        assert "query_ms: 42.5" in output
        assert "freshness: s3_offline" in output


# ---------------------------------------------------------------------------
# Parser structure
# ---------------------------------------------------------------------------


class TestParserStructure:
    """Test argparse configuration."""

    def test_rows_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["rows", "offer", "--classification", "active", "--format", "json"]
        )
        assert args.command == "rows"
        assert args.entity_type == "offer"
        assert args.classification == "active"
        assert args.output_format == "json"

    def test_aggregate_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "aggregate",
                "offer",
                "--group-by",
                "section",
                "--agg",
                "sum:mrr",
            ]
        )
        assert args.command == "aggregate"
        assert args.group_by == "section"
        assert args.agg == ["sum:mrr"]

    def test_entities_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["entities"])
        assert args.command == "entities"

    def test_fields_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["fields", "offer"])
        assert args.command == "fields"
        assert args.entity_type == "offer"

    def test_relations_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["relations", "offer"])
        assert args.command == "relations"
        assert args.entity_type == "offer"

    def test_where_append(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "rows",
                "offer",
                "--where",
                "section eq ACTIVE",
                "--where",
                "mrr gt 100",
            ]
        )
        assert args.where == ["section eq ACTIVE", "mrr gt 100"]

    def test_no_subcommand(self) -> None:
        """No subcommand returns exit code 1."""
        exit_code = main([])
        assert exit_code == 1


# ---------------------------------------------------------------------------
# CLI integration (with mocked provider)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_provider():
    """Mock OfflineDataFrameProvider that returns a known DataFrame."""
    sample_df = pl.DataFrame(
        {
            "gid": ["1", "2", "3"],
            "name": ["Alpha", "Beta", "Gamma"],
            "section": ["Active", "Active", "Won"],
            "mrr": ["100", "200", "300"],
            "is_completed": [False, False, True],
        }
    )
    provider = MagicMock()
    provider.get_dataframe = AsyncMock(return_value=sample_df)
    provider.last_freshness_info = None
    return provider


class TestCLIIntegration:
    """End-to-end CLI tests with mocked provider and engine."""

    def test_entities_subcommand(self, capsys: pytest.CaptureFixture) -> None:
        """'entities' lists entity types without needing S3."""
        capsys.readouterr()  # drain prior output
        exit_code = main(["entities", "--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        stdout = captured.out
        arr_start = stdout.index("[")
        data = json.loads(stdout[arr_start:])
        assert isinstance(data, list)
        assert len(data) > 0
        # All entries have required keys
        for entry in data:
            assert "entity_type" in entry
            assert "project_gid" in entry

    def test_entities_table_format(self, capsys: pytest.CaptureFixture) -> None:
        """'entities' with table format contains entity names."""
        exit_code = main(["entities"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "offer" in captured.out
        assert "unit" in captured.out

    def test_fields_subcommand(self, capsys: pytest.CaptureFixture) -> None:
        """'fields offer' lists columns with dtypes."""
        # Clear any prior output from fixtures
        capsys.readouterr()
        exit_code = main(["fields", "offer", "--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        # Extract JSON array from stdout (may have log lines before it)
        stdout = captured.out
        # Find the JSON array start
        arr_start = stdout.index("[")
        data = json.loads(stdout[arr_start:])
        assert isinstance(data, list)
        assert len(data) > 0
        # All entries have required keys
        names = {entry["name"] for entry in data}
        assert "gid" in names
        assert "name" in names

    def test_relations_subcommand(self, capsys: pytest.CaptureFixture) -> None:
        """'relations offer' lists joinable entities."""
        capsys.readouterr()  # drain prior output
        exit_code = main(["relations", "offer", "--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        stdout = captured.out
        arr_start = stdout.index("[")
        data = json.loads(stdout[arr_start:])
        assert isinstance(data, list)
        # Offer should have relationships with unit and business
        targets = {entry["target"] for entry in data}
        assert "unit" in targets or "business" in targets

    def test_unknown_entity_exits_with_error(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Unknown entity type in 'fields' returns exit code 1."""
        exit_code = main(["fields", "nonexistent_xyz_entity"])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "ERROR" in captured.err

    def test_rows_with_mock_provider(
        self, mock_provider: MagicMock, capsys: pytest.CaptureFixture
    ) -> None:
        """'rows offer --format json' with mocked provider returns data."""
        from autom8_asana.query.models import RowsMeta, RowsResponse

        mock_response = RowsResponse(
            data=[
                {"gid": "1", "name": "Alpha", "section": "Active"},
                {"gid": "2", "name": "Beta", "section": "Active"},
            ],
            meta=RowsMeta(
                total_count=2,
                returned_count=2,
                limit=100,
                offset=0,
                entity_type="offer",
                project_gid="1143843662099250",
                query_ms=10.0,
            ),
        )

        capsys.readouterr()  # drain prior output
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
                ["rows", "offer", "--format", "json", "--classification", "active"]
            )
            assert exit_code == 0
            captured = capsys.readouterr()
            stdout = captured.out
            arr_start = stdout.index("[")
            data = json.loads(stdout[arr_start:])
            assert isinstance(data, list)
            assert len(data) == 2

    def test_aggregate_with_mock_provider(
        self, mock_provider: MagicMock, capsys: pytest.CaptureFixture
    ) -> None:
        """'aggregate offer --group-by section --agg sum:mrr --format json' with mocked provider."""
        from autom8_asana.query.models import AggregateMeta, AggregateResponse

        mock_response = AggregateResponse(
            data=[
                {"section": "Active", "sum_mrr": 400},
                {"section": "Won", "sum_mrr": 300},
            ],
            meta=AggregateMeta(
                group_count=2,
                aggregation_count=1,
                group_by=["section"],
                entity_type="offer",
                project_gid="1143843662099250",
                query_ms=5.0,
            ),
        )

        capsys.readouterr()  # drain prior output
        with (
            patch(
                "autom8_asana.query.offline_provider.OfflineDataFrameProvider",
                return_value=mock_provider,
            ),
            patch(
                "autom8_asana.query.engine.QueryEngine.execute_aggregate",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            exit_code = main(
                [
                    "aggregate",
                    "offer",
                    "--group-by",
                    "section",
                    "--agg",
                    "sum:mrr",
                    "--format",
                    "json",
                ]
            )
            assert exit_code == 0
            captured = capsys.readouterr()
            stdout = captured.out
            arr_start = stdout.index("[")
            data = json.loads(stdout[arr_start:])
            assert isinstance(data, list)
            assert len(data) == 2

    def test_rows_unknown_entity(self, capsys: pytest.CaptureFixture) -> None:
        """Rows with unknown entity returns exit code 1."""
        exit_code = main(["rows", "nonexistent_xyz_entity", "--format", "json"])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Unknown entity type" in captured.err
