"""Unit tests for the format-negotiation extension at ``dataframes.py:111``.

Maps to TDD §13.3 + PRD AC-7 / AC-11 / AC-15:

- AC-7: format negotiation matrix produces correct MIME for json | csv | parquet
- AC-11: unsupported format surfaces 400 (covered at the route level — Pydantic)
- AC-15: All branches operate on eager ``pl.DataFrame`` (P1-C-06 binding)
- ESC-3 (TDD §15.3): observability log records emitted with row + size info
"""

from __future__ import annotations

import io

import polars as pl

from autom8_asana.api.routes.dataframes import (
    MIME_CSV,
    MIME_JSON,
    MIME_PARQUET,
    MIME_POLARS,
    _format_csv_response,
    _format_dataframe_response,
    _format_parquet_response,
)


def _sample_df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "gid": ["1", "2", "3"],
            "name": ["a", "b", "c"],
            "office_phone": ["555-1", None, "555-2"],
            "vertical": ["saas", "retail", None],
            "identity_complete": [True, False, False],
        }
    )


class TestFormatNegotiationCsvBranch:
    def test_csv_explicit_format_returns_csv_mime(self) -> None:
        df = _sample_df()
        resp = _format_dataframe_response(
            df=df,
            request_id="req-1",
            limit=df.height,
            has_more=False,
            next_offset=None,
            accept=None,
            format="csv",
        )
        assert resp.media_type == MIME_CSV

    def test_csv_body_contains_identity_complete_column(self) -> None:
        df = _sample_df()
        resp = _format_csv_response(df, request_id="req-1")
        body = resp.body.decode("utf-8")
        # Header includes identity_complete (PRD AC-4).
        first_line = body.split("\n", 1)[0]
        assert "identity_complete" in first_line
        # Null-key row marked false per AP-6 / SCAR-005-006 transparency.
        assert "false" in body.lower() or "False" in body

    def test_csv_request_id_header(self) -> None:
        resp = _format_csv_response(_sample_df(), request_id="req-csv-id-42")
        assert resp.headers.get("X-Request-ID") == "req-csv-id-42"


class TestFormatNegotiationParquetBranch:
    def test_parquet_explicit_format_returns_parquet_mime(self) -> None:
        df = _sample_df()
        resp = _format_dataframe_response(
            df=df,
            request_id="req-1",
            limit=df.height,
            has_more=False,
            next_offset=None,
            accept=None,
            format="parquet",
        )
        assert resp.media_type == MIME_PARQUET

    def test_parquet_body_round_trips_through_polars(self) -> None:
        df = _sample_df()
        resp = _format_parquet_response(df, request_id="req-1")
        # Round-trip: reading the body bytes back via polars must reproduce
        # the exact frame (including identity_complete column — AC-4).
        round_tripped = pl.read_parquet(io.BytesIO(resp.body))
        assert round_tripped.columns == df.columns
        assert round_tripped.height == df.height
        assert round_tripped["identity_complete"].to_list() == [True, False, False]


class TestFormatNegotiationJsonDefaults:
    """Existing JSON / Polars-binary content negotiation MUST be unchanged."""

    def test_format_none_falls_back_to_json(self) -> None:
        df = _sample_df()
        resp = _format_dataframe_response(
            df=df,
            request_id="req-1",
            limit=df.height,
            has_more=False,
            next_offset=None,
            accept=None,
            format=None,
        )
        assert resp.media_type == MIME_JSON

    def test_format_json_explicit_returns_json_mime(self) -> None:
        df = _sample_df()
        resp = _format_dataframe_response(
            df=df,
            request_id="req-1",
            limit=df.height,
            has_more=False,
            next_offset=None,
            accept=None,
            format="json",
        )
        assert resp.media_type == MIME_JSON

    def test_polars_accept_header_with_format_none_uses_polars(self) -> None:
        df = _sample_df()
        resp = _format_dataframe_response(
            df=df,
            request_id="req-1",
            limit=df.height,
            has_more=False,
            next_offset=None,
            accept=MIME_POLARS,
            format=None,
        )
        assert resp.media_type == MIME_POLARS

    def test_explicit_format_supersedes_accept_header(self) -> None:
        # When the route handler passes format=csv explicitly, the Accept
        # header path is NOT taken — the explicit selector wins.
        df = _sample_df()
        resp = _format_dataframe_response(
            df=df,
            request_id="req-1",
            limit=df.height,
            has_more=False,
            next_offset=None,
            accept=MIME_POLARS,
            format="csv",
        )
        assert resp.media_type == MIME_CSV


class TestEsc3SizeMeasurement:
    """ESC-3 (TDD §15.3 + DEFER-WATCH-7) — log row + serialized byte counts.

    Verifies the observability side-effect is wired by patching the logger's
    ``info`` method directly. The structlog wrapper used by ``autom8y_log``
    does not propagate to pytest's ``caplog`` by default, so direct patching
    is the deterministic verification approach.
    """

    def test_csv_response_emits_size_log_record(self) -> None:
        from unittest.mock import patch

        df = _sample_df()
        with patch("autom8_asana.api.routes.dataframes._export_format_logger") as mock_logger:
            _format_csv_response(df, request_id="req-csv")
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args.args[0] == "export_format_serialized"
        extra = call_args.kwargs["extra"]
        assert extra["format"] == "csv"
        assert extra["row_count"] == df.height
        assert extra["column_count"] == df.width
        assert extra["serialized_bytes"] > 0
        assert extra["request_id"] == "req-csv"

    def test_parquet_response_emits_size_log_record(self) -> None:
        from unittest.mock import patch

        df = _sample_df()
        with patch("autom8_asana.api.routes.dataframes._export_format_logger") as mock_logger:
            _format_parquet_response(df, request_id="req-pq")
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args.args[0] == "export_format_serialized"
        extra = call_args.kwargs["extra"]
        assert extra["format"] == "parquet"
        assert extra["row_count"] == df.height
        assert extra["serialized_bytes"] > 0


class TestEagerOnlyConsumerSurface:
    """AC-15 / P1-C-06: every branch operates on eager pl.DataFrame."""

    def test_csv_branch_does_not_require_lazy_frame(self) -> None:
        df = _sample_df()
        # Must not raise — eager DataFrame is the supported input.
        resp = _format_csv_response(df, request_id="req-1")
        assert resp.media_type == MIME_CSV

    def test_parquet_branch_does_not_require_lazy_frame(self) -> None:
        df = _sample_df()
        resp = _format_parquet_response(df, request_id="req-1")
        assert resp.media_type == MIME_PARQUET
