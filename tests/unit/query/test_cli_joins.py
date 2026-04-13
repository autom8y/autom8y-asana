"""Tests for cross-entity join CLI arguments: --join ENTITY:col1,col2 and --join-on KEY.

Covers:
- _parse_join() parsing logic (valid and invalid inputs)
- Full CLI integration with mocked provider (join columns in output)
- JoinError handling (CLI catches and prints available join targets)
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.query.__main__ import CLIError, _parse_join, build_parser, main
from autom8_asana.query.errors import JoinError

# ---------------------------------------------------------------------------
# _parse_join unit tests
# ---------------------------------------------------------------------------


class TestParseJoin:
    """Test _parse_join() helper for --join argument parsing."""

    def test_parse_join_basic(self) -> None:
        """Single column: 'business:booking_type' -> correct JoinSpec dict."""
        result = _parse_join("business:booking_type", None)
        assert result == {
            "entity_type": "business",
            "select": ["booking_type"],
        }

    def test_parse_join_multiple_columns(self) -> None:
        """Multiple columns: 'business:booking_type,stripe_id' -> select has both."""
        result = _parse_join("business:booking_type,stripe_id", None)
        assert result == {
            "entity_type": "business",
            "select": ["booking_type", "stripe_id"],
        }

    def test_parse_join_with_on(self) -> None:
        """Explicit join key: join_on='office_phone' sets 'on' in result."""
        result = _parse_join("business:booking_type", "office_phone")
        assert result == {
            "entity_type": "business",
            "select": ["booking_type"],
            "on": "office_phone",
        }

    def test_parse_join_invalid_no_colon(self) -> None:
        """Missing colon raises CLIError with format guidance."""
        with pytest.raises(CLIError, match="Invalid --join format"):
            _parse_join("business", None)

    def test_parse_join_invalid_no_columns(self) -> None:
        """Empty columns after colon raises CLIError."""
        with pytest.raises(CLIError, match="No columns specified"):
            _parse_join("business:", None)

    def test_parse_join_strips_whitespace(self) -> None:
        """Leading/trailing whitespace in entity and columns is stripped."""
        result = _parse_join(" business : booking_type , stripe_id ", None)
        assert result["entity_type"] == "business"
        assert result["select"] == ["booking_type", "stripe_id"]

    def test_parse_join_on_none_omits_key(self) -> None:
        """When join_on is None, 'on' key is absent from result dict."""
        result = _parse_join("business:booking_type", None)
        assert "on" not in result


# ---------------------------------------------------------------------------
# Parser structure tests
# ---------------------------------------------------------------------------


class TestJoinParserArgs:
    """Test that argparse wires --join and --join-on correctly."""

    def test_join_arg_parsed(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["rows", "offer", "--join", "business:booking_type"])
        # --join now uses action="append" for multi-join support
        assert args.join == ["business:booking_type"]

    def test_join_on_arg_parsed(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "rows",
                "offer",
                "--join",
                "business:booking_type",
                "--join-on",
                "office_phone",
            ]
        )
        # --join now uses action="append" for multi-join support
        assert args.join == ["business:booking_type"]
        assert args.join_on == "office_phone"

    def test_join_defaults_to_none(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["rows", "offer"])
        assert args.join is None


# ---------------------------------------------------------------------------
# CLI integration tests (with mocked engine)
# ---------------------------------------------------------------------------


class TestCLIJoinIntegration:
    """End-to-end CLI join tests with mocked QueryEngine."""

    def test_cli_rows_with_join_integration(self, capsys: pytest.CaptureFixture) -> None:
        """Full flow: --join business:booking_type produces output with join columns."""
        from autom8_asana.query.models import RowsMeta, RowsResponse

        mock_response = RowsResponse(
            data=[
                {
                    "gid": "1",
                    "name": "Alpha",
                    "section": "Active",
                    "business_booking_type": "manual",
                },
                {
                    "gid": "2",
                    "name": "Beta",
                    "section": "Active",
                    "business_booking_type": "online",
                },
            ],
            meta=RowsMeta(
                total_count=2,
                returned_count=2,
                limit=100,
                offset=0,
                entity_type="offer",
                project_gid="1143843662099250",
                query_ms=15.0,
                join_entity="business",
                join_key="office_phone",
                join_matched=2,
                join_unmatched=0,
            ),
        )

        mock_provider = MagicMock()
        mock_provider.get_dataframe = AsyncMock()
        mock_provider.last_freshness_info = None

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
            ) as mock_execute,
        ):
            exit_code = main(
                [
                    "rows",
                    "offer",
                    "--join",
                    "business:booking_type",
                    "--format",
                    "json",
                ]
            )
            assert exit_code == 0

            # Verify execute_rows was called with a request containing JoinSpec
            call_kwargs = mock_execute.call_args
            request = call_kwargs.kwargs.get("request") or call_kwargs[1].get("request")
            if request is None:
                # Positional args: execute_rows(entity_type, project_gid, client, request, ...)
                request = call_kwargs[0][3] if len(call_kwargs[0]) > 3 else None
            assert request is not None
            assert request.join is not None
            assert request.join.entity_type == "business"
            assert request.join.select == ["booking_type"]
            assert request.join.on is None

            # Verify output contains join columns
            captured = capsys.readouterr()
            stdout = captured.out
            arr_start = stdout.index("[")
            data = json.loads(stdout[arr_start:])
            assert len(data) == 2
            assert "business_booking_type" in data[0]

            # Verify metadata on stderr shows join info
            assert "join: business" in captured.err

    def test_cli_rows_with_join_on(self, capsys: pytest.CaptureFixture) -> None:
        """--join-on explicitly sets the join key on the request."""
        from autom8_asana.query.models import RowsMeta, RowsResponse

        mock_response = RowsResponse(
            data=[{"gid": "1", "name": "Alpha", "section": "Active"}],
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
            ) as mock_execute,
        ):
            exit_code = main(
                [
                    "rows",
                    "offer",
                    "--join",
                    "business:booking_type",
                    "--join-on",
                    "office_phone",
                    "--format",
                    "json",
                ]
            )
            assert exit_code == 0

            call_kwargs = mock_execute.call_args
            request = call_kwargs.kwargs.get("request") or call_kwargs[1].get("request")
            if request is None:
                request = call_kwargs[0][3] if len(call_kwargs[0]) > 3 else None
            assert request is not None
            assert request.join is not None
            assert request.join.on == "office_phone"

    def test_cli_join_error_shows_available(self, capsys: pytest.CaptureFixture) -> None:
        """When engine raises JoinError, CLI prints error with available join targets."""
        mock_provider = MagicMock()
        mock_provider.get_dataframe = AsyncMock()
        mock_provider.last_freshness_info = None

        join_error = JoinError(
            message=(
                "No relationship between 'offer' and 'nonexistent'. "
                "Joinable types: ['business', 'unit']"
            )
        )

        capsys.readouterr()
        with (
            patch(
                "autom8_asana.query.offline_provider.OfflineDataFrameProvider",
                return_value=mock_provider,
            ),
            patch(
                "autom8_asana.query.engine.QueryEngine.execute_rows",
                new_callable=AsyncMock,
                side_effect=join_error,
            ),
        ):
            exit_code = main(
                [
                    "rows",
                    "offer",
                    "--join",
                    "nonexistent:some_col",
                    "--format",
                    "json",
                ]
            )
            assert exit_code == 1
            captured = capsys.readouterr()
            assert "No relationship" in captured.err
            assert "Joinable types" in captured.err

    def test_cli_join_invalid_format_exits_with_error(self, capsys: pytest.CaptureFixture) -> None:
        """Invalid --join format (no colon) returns exit code 1 with helpful message."""
        capsys.readouterr()
        exit_code = main(["rows", "offer", "--join", "business_no_colon", "--format", "json"])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Invalid --join format" in captured.err
