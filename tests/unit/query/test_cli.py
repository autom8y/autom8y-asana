"""Tests for query/__main__.py: CLI argument parsing, subcommand routing, end-to-end with mock provider."""

from __future__ import annotations

import argparse
import io
import json
import sys
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

if TYPE_CHECKING:
    from pathlib import Path

from autom8_asana.query.__main__ import (
    CLIError,
    _coerce_value,
    _format_age,
    _get_live_config,
    build_parser,
    build_predicate,
    execute_live_aggregate,
    execute_live_rows,
    handle_sections,
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

    def test_unknown_entity_exits_with_error(self, capsys: pytest.CaptureFixture) -> None:
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
            exit_code = main(["rows", "offer", "--format", "json", "--classification", "active"])
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


# ---------------------------------------------------------------------------
# G-01: Settings guard bypass
# ---------------------------------------------------------------------------


class TestSettingsGuardBypass:
    """Verify main() sets env defaults for offline CLI usage."""

    def test_main_sets_autom8_data_url_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """main() should set AUTOM8Y_DATA_URL if not already set."""
        import os

        monkeypatch.delenv("AUTOM8Y_DATA_URL", raising=False)
        # Call main with no command to trigger early exit after env setup
        main([])
        assert os.environ.get("AUTOM8Y_DATA_URL") == "http://offline-cli.local"

    def test_main_does_not_override_existing_data_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() should NOT override AUTOM8Y_DATA_URL if already set."""
        monkeypatch.setenv("AUTOM8Y_DATA_URL", "http://my-custom-url:8000")
        main([])
        import os

        assert os.environ.get("AUTOM8Y_DATA_URL") == "http://my-custom-url:8000"

    def test_main_sets_workspace_gid_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """main() should set ASANA_WORKSPACE_GID if not already set."""
        import os

        monkeypatch.delenv("ASANA_WORKSPACE_GID", raising=False)
        main([])
        assert os.environ.get("ASANA_WORKSPACE_GID") == "offline"


# ---------------------------------------------------------------------------
# G-02: Log noise suppression
# ---------------------------------------------------------------------------


class TestLogNoiseSuppression:
    """Verify logging is configured to suppress noise."""

    def test_verbose_flag_in_parser(self) -> None:
        """Parser should accept --verbose flag."""
        parser = build_parser()
        args = parser.parse_args(["--verbose", "entities"])
        assert args.verbose is True

    def test_quiet_flag_in_parser(self) -> None:
        """Parser should accept --quiet flag."""
        parser = build_parser()
        args = parser.parse_args(["--quiet", "entities"])
        assert args.quiet is True

    def test_verbose_and_quiet_mutually_exclusive(self) -> None:
        """--verbose and --quiet cannot be used together."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--verbose", "--quiet", "entities"])

    def test_short_flags(self) -> None:
        """Short flags -v and -q should work."""
        parser = build_parser()
        args_v = parser.parse_args(["-v", "entities"])
        assert args_v.verbose is True
        args_q = parser.parse_args(["-q", "entities"])
        assert args_q.quiet is True


# ---------------------------------------------------------------------------
# G-03: Age formatting
# ---------------------------------------------------------------------------


class TestFormatAge:
    """Test human-readable data age formatting."""

    def test_seconds(self) -> None:
        assert _format_age(30.0) == "30s"

    def test_minutes(self) -> None:
        assert _format_age(150.0) == "2.5m"

    def test_hours(self) -> None:
        assert _format_age(7200.0) == "2.0h"

    def test_days(self) -> None:
        assert _format_age(172800.0) == "2.0d"

    def test_zero(self) -> None:
        assert _format_age(0.0) == "0s"

    def test_just_under_minute(self) -> None:
        assert _format_age(59.0) == "59s"

    def test_exactly_one_minute(self) -> None:
        assert _format_age(60.0) == "1.0m"


class TestPrintMetadataWithAge:
    """Test that print_metadata displays data_age when available."""

    def test_metadata_with_data_age_seconds(self) -> None:
        """print_metadata should include data_age when data_age_seconds is present."""
        from types import SimpleNamespace

        meta = SimpleNamespace(
            total_count=100,
            returned_count=50,
            query_ms=42.5,
            freshness="s3_offline",
            data_age_seconds=3600.0,
        )
        buf = io.StringIO()
        print_metadata(meta, file=buf)
        output = buf.getvalue()
        assert "data_age: 1.0h" in output
        assert "freshness: s3_offline" in output

    def test_metadata_without_data_age(self) -> None:
        """print_metadata should not include data_age when attribute is missing."""
        meta = RowsMeta(
            total_count=10,
            returned_count=10,
            limit=100,
            offset=0,
            entity_type="offer",
            project_gid="123",
            query_ms=5.0,
            freshness="s3_offline",
        )
        buf = io.StringIO()
        print_metadata(meta, file=buf)
        output = buf.getvalue()
        assert "data_age" not in output
        assert "freshness: s3_offline" in output


# ---------------------------------------------------------------------------
# B-1: sections subcommand
# ---------------------------------------------------------------------------


class TestSectionsSubcommand:
    """Test the 'sections' subcommand."""

    def test_sections_parser(self) -> None:
        """Parser accepts 'sections <entity_type>'."""
        parser = build_parser()
        args = parser.parse_args(["sections", "offer"])
        assert args.command == "sections"
        assert args.entity_type == "offer"

    def test_sections_offer_json(self, capsys: pytest.CaptureFixture) -> None:
        """'sections offer --format json' returns section/classification rows."""
        capsys.readouterr()
        exit_code = main(["sections", "offer", "--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        stdout = captured.out
        arr_start = stdout.index("[")
        data = json.loads(stdout[arr_start:])
        assert isinstance(data, list)
        assert len(data) > 0
        # All entries have required keys
        for entry in data:
            assert "section_name" in entry
            assert "classification" in entry
        # Check known sections exist
        section_names = {e["section_name"] for e in data}
        assert "active" in section_names
        classifications = {e["classification"] for e in data}
        assert "active" in classifications

    def test_sections_unit(self, capsys: pytest.CaptureFixture) -> None:
        """'sections unit' returns unit-specific sections."""
        capsys.readouterr()
        exit_code = main(["sections", "unit", "--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        stdout = captured.out
        arr_start = stdout.index("[")
        data = json.loads(stdout[arr_start:])
        section_names = {e["section_name"] for e in data}
        # Unit-specific sections
        assert "onboarding" in section_names or "active" in section_names

    def test_sections_unknown_entity(self, capsys: pytest.CaptureFixture) -> None:
        """'sections' with unknown entity type returns exit code 1."""
        exit_code = main(["sections", "nonexistent_xyz"])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "ERROR" in captured.err

    def test_sections_entity_without_classifier(self, capsys: pytest.CaptureFixture) -> None:
        """'sections' with entity that has no classifier returns exit code 1."""
        exit_code = main(["sections", "business"])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "No section classifier" in captured.err

    def test_sections_table_format(self, capsys: pytest.CaptureFixture) -> None:
        """'sections offer' default table format contains classification data."""
        exit_code = main(["sections", "offer"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "active" in captured.out.lower()


# ---------------------------------------------------------------------------
# B-2: list-queries subcommand
# ---------------------------------------------------------------------------


class TestListQueriesSubcommand:
    """Test the 'list-queries' subcommand."""

    def test_list_queries_parser(self) -> None:
        """Parser accepts 'list-queries'."""
        parser = build_parser()
        args = parser.parse_args(["list-queries"])
        assert args.command == "list-queries"

    def test_list_queries_with_files(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """'list-queries' discovers YAML files in ./queries/."""
        import yaml

        queries_dir = tmp_path / "queries"
        queries_dir.mkdir()
        (queries_dir / "my_query.yaml").write_text(
            yaml.dump(
                {
                    "name": "my_query",
                    "description": "Test query for listing",
                    "entity_type": "offer",
                    "command": "rows",
                }
            )
        )
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        exit_code = main(["list-queries", "--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        stdout = captured.out
        arr_start = stdout.index("[")
        data = json.loads(stdout[arr_start:])
        assert isinstance(data, list)
        assert len(data) >= 1
        names = {e["name"] for e in data}
        assert "my_query" in names
        # Check all fields present
        for entry in data:
            assert "name" in entry
            assert "entity_type" in entry
            assert "command" in entry

    def test_list_queries_empty_dir(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """'list-queries' with no query files prints hint to stderr."""
        monkeypatch.chdir(tmp_path)
        # Also override home to avoid picking up real user queries
        monkeypatch.setenv("HOME", str(tmp_path))
        capsys.readouterr()
        exit_code = main(["list-queries", "--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "No saved queries found" in captured.err

    def test_list_queries_skips_malformed(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """'list-queries' skips malformed YAML files without error."""
        queries_dir = tmp_path / "queries"
        queries_dir.mkdir()
        # Malformed YAML (missing required fields)
        (queries_dir / "bad.yaml").write_text("just: a string\n")
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        exit_code = main(["list-queries", "--format", "json"])
        assert exit_code == 0


# ---------------------------------------------------------------------------
# B-3: --save flag
# ---------------------------------------------------------------------------


class TestSaveFlag:
    """Test the --save flag on rows and aggregate subcommands."""

    def test_save_flag_on_rows_parser(self) -> None:
        """Parser accepts --save on rows subcommand."""
        parser = build_parser()
        args = parser.parse_args(["rows", "offer", "--save", "my_query"])
        assert args.save == "my_query"

    def test_save_flag_on_aggregate_parser(self) -> None:
        """Parser accepts --save on aggregate subcommand."""
        parser = build_parser()
        args = parser.parse_args(
            [
                "aggregate",
                "offer",
                "--group-by",
                "section",
                "--agg",
                "sum:mrr",
                "--save",
                "my_agg",
            ]
        )
        assert args.save == "my_agg"

    def test_save_writes_yaml(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--save creates a YAML file in ~/.autom8/queries/."""
        import yaml

        from autom8_asana.query.models import RowsMeta, RowsResponse

        # Redirect HOME to tmp_path so we write to a temp dir
        monkeypatch.setenv("HOME", str(tmp_path))

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
                    "--classification",
                    "active",
                    "--select",
                    "gid,name,mrr",
                    "--format",
                    "json",
                    "--save",
                    "test_saved",
                ]
            )
            assert exit_code == 0

        # Verify file was created
        saved_path = tmp_path / ".autom8" / "queries" / "test_saved.yaml"
        assert saved_path.exists()
        data = yaml.safe_load(saved_path.read_text())
        assert data["name"] == "test_saved"
        assert data["entity_type"] == "offer"
        assert data["classification"] == "active"
        assert data["command"] == "rows"

    def test_save_no_overwrite(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--save prints warning and skips if file already exists."""
        from autom8_asana.query.models import RowsMeta, RowsResponse

        monkeypatch.setenv("HOME", str(tmp_path))
        # Pre-create the file
        target_dir = tmp_path / ".autom8" / "queries"
        target_dir.mkdir(parents=True)
        (target_dir / "existing.yaml").write_text("name: existing\n")

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
            ),
        ):
            exit_code = main(
                [
                    "rows",
                    "offer",
                    "--format",
                    "json",
                    "--save",
                    "existing",
                ]
            )
            assert exit_code == 0

        captured = capsys.readouterr()
        assert "Warning:" in captured.err
        assert "already exists" in captured.err

    def test_save_aggregate_writes_yaml(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--save on aggregate creates YAML with group_by and aggregations."""
        import yaml

        from autom8_asana.query.models import AggregateMeta, AggregateResponse

        monkeypatch.setenv("HOME", str(tmp_path))

        mock_response = AggregateResponse(
            data=[{"section": "Active", "sum_mrr": 400}],
            meta=AggregateMeta(
                group_count=1,
                aggregation_count=1,
                group_by=["section"],
                entity_type="offer",
                project_gid="1143843662099250",
                query_ms=3.0,
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
                    "--save",
                    "agg_saved",
                ]
            )
            assert exit_code == 0

        saved_path = tmp_path / ".autom8" / "queries" / "agg_saved.yaml"
        assert saved_path.exists()
        data = yaml.safe_load(saved_path.read_text())
        assert data["name"] == "agg_saved"
        assert data["command"] == "aggregate"
        assert data["group_by"] == ["section"]
        assert len(data["aggregations"]) == 1


# ---------------------------------------------------------------------------
# B-5: entities help improvement
# ---------------------------------------------------------------------------


class TestEntitiesHelp:
    """Test that entities subparser has improved help/epilog."""

    def test_entities_has_epilog(self) -> None:
        """The entities subparser should have an epilog with examples."""
        parser = build_parser()
        # Access the entities subparser
        for action in parser._subparsers._actions:
            if isinstance(action, argparse._SubParsersAction):
                ent = action.choices.get("entities")
                assert ent is not None
                assert ent.epilog is not None
                assert "Examples" in ent.epilog
                assert "fields" in ent.epilog
                assert "sections" in ent.epilog
                break
        else:
            pytest.fail("No subparsers found")


# ---------------------------------------------------------------------------
# C-1: --live flag
# ---------------------------------------------------------------------------


class TestLiveFlagParser:
    """Test that --live flag is accepted by rows and aggregate parsers."""

    def test_live_flag_on_rows(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["rows", "offer", "--live"])
        assert args.live is True

    def test_live_flag_default_false_rows(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["rows", "offer"])
        assert args.live is False

    def test_live_flag_on_aggregate(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "aggregate",
                "offer",
                "--group-by",
                "section",
                "--agg",
                "sum:mrr",
                "--live",
            ]
        )
        assert args.live is True

    def test_live_flag_default_false_aggregate(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["aggregate", "offer", "--group-by", "section", "--agg", "sum:mrr"]
        )
        assert args.live is False


class TestGetLiveConfig:
    """Test live mode configuration resolution via platform TokenManager."""

    def test_missing_service_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_get_live_config raises CLIError when SERVICE_CLIENT_ID/SECRET is not set."""
        monkeypatch.delenv("SERVICE_CLIENT_ID", raising=False)
        monkeypatch.delenv("SERVICE_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("SERVICE_API_KEY", raising=False)
        with pytest.raises(CLIError, match="SERVICE_CLIENT_ID"):
            _get_live_config()

    def test_returns_url_and_jwt_headers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_get_live_config exchanges service credentials for JWT via TokenManager."""
        monkeypatch.setenv("SERVICE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("SERVICE_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("AUTOM8Y_DATA_URL", "http://myhost:9999")

        mock_manager = MagicMock()
        mock_manager.get_token.return_value = "jwt-token-abc"

        with (
            patch("autom8y_core.Config.from_env") as mock_config,
            patch("autom8y_core.TokenManager", return_value=mock_manager),
        ):
            mock_config.return_value = MagicMock()
            base_url, headers = _get_live_config()

        assert base_url == "http://myhost:9999"
        assert headers["Authorization"] == "Bearer jwt-token-abc"
        assert headers["Content-Type"] == "application/json"
        mock_manager.get_token.assert_called_once()
        mock_manager.close.assert_called_once()

    def test_default_url_is_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_get_live_config defaults to production API URL."""
        monkeypatch.setenv("SERVICE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("SERVICE_CLIENT_SECRET", "test-client-secret")
        monkeypatch.delenv("AUTOM8Y_DATA_URL", raising=False)

        mock_manager = MagicMock()
        mock_manager.get_token.return_value = "jwt-token"

        with (
            patch("autom8y_core.Config.from_env") as mock_config,
            patch("autom8y_core.TokenManager", return_value=mock_manager),
        ):
            mock_config.return_value = MagicMock()
            base_url, _ = _get_live_config()

        assert base_url == "https://data.api.autom8y.io"

    def test_exit_code_is_2(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing service credentials exits with code 2 (infrastructure error)."""
        monkeypatch.delenv("SERVICE_CLIENT_ID", raising=False)
        monkeypatch.delenv("SERVICE_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("SERVICE_API_KEY", raising=False)
        with pytest.raises(CLIError) as exc_info:
            _get_live_config()
        assert exc_info.value.exit_code == 2

    def test_token_acquisition_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_get_live_config raises CLIError when token exchange fails."""
        monkeypatch.setenv("SERVICE_CLIENT_ID", "bad-client-id")
        monkeypatch.setenv("SERVICE_CLIENT_SECRET", "bad-client-secret")

        from autom8y_core.errors import TokenAcquisitionError

        mock_manager = MagicMock()
        mock_manager.get_token.side_effect = TokenAcquisitionError("Invalid key")

        with (
            patch("autom8y_core.Config.from_env") as mock_config,
            patch("autom8y_core.TokenManager", return_value=mock_manager),
        ):
            mock_config.return_value = MagicMock()
            with pytest.raises(CLIError, match="Auth failed"):
                _get_live_config()


class TestExecuteLiveRows:
    """Test execute_live_rows HTTP client function."""

    def _mock_live_config(self) -> Any:
        """Patch _get_live_config to return mock URL + JWT headers."""
        return patch(
            "autom8_asana.query.__main__._get_live_config",
            return_value=(
                "http://mock:5200",
                {
                    "Authorization": "Bearer jwt-test",
                    "Content-Type": "application/json",
                },
            ),
        )

    def test_successful_request(self) -> None:
        """execute_live_rows returns RowsResponse on successful HTTP call."""
        import httpx

        mock_response_data = {
            "data": [{"gid": "1", "name": "Alpha"}],
            "meta": {
                "total_count": 1,
                "returned_count": 1,
                "limit": 100,
                "offset": 0,
                "entity_type": "offer",
                "project_gid": "123",
                "query_ms": 5.0,
            },
        }

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_data
        mock_resp.raise_for_status = MagicMock()

        with (
            self._mock_live_config(),
            patch("httpx.post", return_value=mock_resp) as mock_post,
        ):
            result = execute_live_rows("offer", {"limit": 100, "offset": 0})
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "/v1/query/offer/rows" in call_args.args[0]
            assert call_args.kwargs["headers"]["Authorization"] == "Bearer jwt-test"

        assert result.data == [{"gid": "1", "name": "Alpha"}]
        assert result.meta.total_count == 1

    def test_connect_error(self) -> None:
        """execute_live_rows raises CLIError with exit_code=2 on connection failure."""
        import httpx

        with (
            self._mock_live_config(),
            patch("httpx.post", side_effect=httpx.ConnectError("Connection refused")),
        ):
            with pytest.raises(CLIError, match="Cannot connect") as exc_info:
                execute_live_rows("offer", {"limit": 100})
            assert exc_info.value.exit_code == 2

    def test_http_status_error(self) -> None:
        """execute_live_rows raises CLIError with exit_code=1 on HTTP errors."""
        import httpx

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 503
        mock_resp.text = "Cache not warm"
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503", request=MagicMock(), response=mock_resp
        )

        with self._mock_live_config(), patch("httpx.post", return_value=mock_resp):
            with pytest.raises(CLIError, match="API error") as exc_info:
                execute_live_rows("offer", {"limit": 100})
            assert exc_info.value.exit_code == 1

    def test_timeout_error(self) -> None:
        """execute_live_rows raises CLIError with exit_code=2 on timeout."""
        import httpx

        with (
            self._mock_live_config(),
            patch("httpx.post", side_effect=httpx.TimeoutException("timed out")),
        ):
            with pytest.raises(CLIError, match="timed out") as exc_info:
                execute_live_rows("offer", {"limit": 100})
            assert exc_info.value.exit_code == 2


class TestExecuteLiveAggregate:
    """Test execute_live_aggregate HTTP client function."""

    def _mock_live_config(self) -> Any:
        """Patch _get_live_config to return mock URL + JWT headers."""
        return patch(
            "autom8_asana.query.__main__._get_live_config",
            return_value=(
                "http://mock:5200",
                {
                    "Authorization": "Bearer jwt-test",
                    "Content-Type": "application/json",
                },
            ),
        )

    def test_successful_request(self) -> None:
        """execute_live_aggregate returns AggregateResponse on success."""
        import httpx

        mock_response_data = {
            "data": [{"section": "Active", "sum_mrr": 400}],
            "meta": {
                "group_count": 1,
                "aggregation_count": 1,
                "group_by": ["section"],
                "entity_type": "offer",
                "project_gid": "123",
                "query_ms": 3.0,
            },
        }

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_data
        mock_resp.raise_for_status = MagicMock()

        with (
            self._mock_live_config(),
            patch("httpx.post", return_value=mock_resp) as mock_post,
        ):
            result = execute_live_aggregate(
                "offer",
                {
                    "group_by": ["section"],
                    "aggregations": [{"column": "mrr", "agg": "sum"}],
                },
            )
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "/v1/query/offer/aggregate" in call_args.args[0]

        assert result.data == [{"section": "Active", "sum_mrr": 400}]
        assert result.meta.group_count == 1

    def test_connect_error(self) -> None:
        """execute_live_aggregate raises CLIError on connection failure."""
        import httpx

        with (
            self._mock_live_config(),
            patch("httpx.post", side_effect=httpx.ConnectError("refused")),
        ):
            with pytest.raises(CLIError, match="Cannot connect"):
                execute_live_aggregate(
                    "offer",
                    {
                        "group_by": ["section"],
                        "aggregations": [{"column": "mrr", "agg": "sum"}],
                    },
                )


class TestLiveCLIIntegration:
    """End-to-end CLI tests for --live mode with mocked HTTP."""

    def _mock_live_config(self) -> Any:
        """Patch _get_live_config to return mock URL + JWT headers."""
        return patch(
            "autom8_asana.query.__main__._get_live_config",
            return_value=(
                "http://mock:5200",
                {
                    "Authorization": "Bearer jwt-test",
                    "Content-Type": "application/json",
                },
            ),
        )

    def test_rows_live_mode(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """'rows offer --live --format json' calls the HTTP API and formats output."""
        import httpx

        mock_response_data = {
            "data": [
                {"gid": "1", "name": "Alpha", "section": "Active"},
                {"gid": "2", "name": "Beta", "section": "Active"},
            ],
            "meta": {
                "total_count": 2,
                "returned_count": 2,
                "limit": 100,
                "offset": 0,
                "entity_type": "offer",
                "project_gid": "1143843662099250",
                "query_ms": 10.0,
            },
        }

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_data
        mock_resp.raise_for_status = MagicMock()

        capsys.readouterr()
        with self._mock_live_config(), patch("httpx.post", return_value=mock_resp):
            exit_code = main(["rows", "offer", "--live", "--format", "json"])

        assert exit_code == 0
        captured = capsys.readouterr()
        stdout = captured.out
        arr_start = stdout.index("[")
        data = json.loads(stdout[arr_start:])
        assert len(data) == 2
        assert data[0]["gid"] == "1"

    def test_aggregate_live_mode(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """'aggregate offer --group-by section --agg sum:mrr --live --format json' works."""
        import httpx

        mock_response_data = {
            "data": [{"section": "Active", "sum_mrr": 400}],
            "meta": {
                "group_count": 1,
                "aggregation_count": 1,
                "group_by": ["section"],
                "entity_type": "offer",
                "project_gid": "1143843662099250",
                "query_ms": 5.0,
            },
        }

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_data
        mock_resp.raise_for_status = MagicMock()

        capsys.readouterr()
        with self._mock_live_config(), patch("httpx.post", return_value=mock_resp):
            exit_code = main(
                [
                    "aggregate",
                    "offer",
                    "--group-by",
                    "section",
                    "--agg",
                    "sum:mrr",
                    "--live",
                    "--format",
                    "json",
                ]
            )

        assert exit_code == 0
        captured = capsys.readouterr()
        stdout = captured.out
        arr_start = stdout.index("[")
        data = json.loads(stdout[arr_start:])
        assert len(data) == 1
        assert data[0]["section"] == "Active"

    def test_live_without_service_key_exits_2(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """--live without SERVICE_CLIENT_ID/SECRET exits with code 2."""
        monkeypatch.delenv("SERVICE_CLIENT_ID", raising=False)
        monkeypatch.delenv("SERVICE_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("SERVICE_API_KEY", raising=False)
        exit_code = main(["rows", "offer", "--live"])
        assert exit_code == 2
        captured = capsys.readouterr()
        assert "SERVICE_CLIENT_ID" in captured.err
