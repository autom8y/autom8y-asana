"""Output formatters for query results.

Protocol + implementations for table, JSON, CSV, and JSONL output formats.
Each formatter accepts a RowsResponse, AggregateResponse, or discovery
rows list and writes formatted output to an IO stream.

Per TDD: Metadata goes to stderr, data goes to stdout. Formatters
only handle data output; metadata is handled separately by print_metadata().
"""

from __future__ import annotations

import json
from typing import IO, TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from autom8_asana.query.models import AggregateResponse, RowsResponse


class OutputFormatter(Protocol):
    """Protocol for query result formatting."""

    def format_rows(self, response: RowsResponse, out: IO[str]) -> None:
        """Format a RowsResponse to the output stream."""
        ...

    def format_aggregate(self, response: AggregateResponse, out: IO[str]) -> None:
        """Format an AggregateResponse to the output stream."""
        ...

    def format_discovery(self, rows: list[dict[str, object]], out: IO[str]) -> None:
        """Format discovery data (entities, fields, relations) to the output stream."""
        ...


class TableFormatter:
    """Human-readable aligned table using polars DataFrame repr.

    Truncates values > max_col_width characters with ellipsis.
    """

    def __init__(self, *, max_col_width: int = 40, no_truncate: bool = False) -> None:
        self._max_col_width = max_col_width
        self._no_truncate = no_truncate

    def format_rows(self, response: RowsResponse, out: IO[str]) -> None:
        """Format row query results as a polars table."""
        import polars as pl

        if not response.data:
            out.write("(empty result set)\n")
            return
        df = pl.DataFrame(response.data)
        self._write_df(df, out)

    def format_aggregate(self, response: AggregateResponse, out: IO[str]) -> None:
        """Format aggregate query results as a polars table."""
        import polars as pl

        if not response.data:
            out.write("(empty result set)\n")
            return
        df = pl.DataFrame(response.data)
        self._write_df(df, out)

    def format_discovery(self, rows: list[dict[str, object]], out: IO[str]) -> None:
        """Format discovery data as a polars table."""
        import polars as pl

        if not rows:
            out.write("(no results)\n")
            return
        df = pl.DataFrame(rows)
        self._write_df(df, out)

    def _write_df(self, df: Any, out: IO[str]) -> None:
        """Write a polars DataFrame using configured display settings."""
        import polars as pl

        with pl.Config(
            tbl_cols=-1,
            tbl_width_chars=None if self._no_truncate else 200,
            fmt_str_lengths=0 if self._no_truncate else self._max_col_width,
        ):
            out.write(str(df) + "\n")


class JsonFormatter:
    """JSON array output suitable for jq piping."""

    def format_rows(self, response: RowsResponse, out: IO[str]) -> None:
        """Format row query results as a JSON array."""
        json.dump(response.data, out, indent=2, default=str)
        out.write("\n")

    def format_aggregate(self, response: AggregateResponse, out: IO[str]) -> None:
        """Format aggregate query results as a JSON array."""
        json.dump(response.data, out, indent=2, default=str)
        out.write("\n")

    def format_discovery(self, rows: list[dict[str, object]], out: IO[str]) -> None:
        """Format discovery data as a JSON array."""
        json.dump(rows, out, indent=2, default=str)
        out.write("\n")


class CsvFormatter:
    """CSV with headers suitable for spreadsheet import."""

    def format_rows(self, response: RowsResponse, out: IO[str]) -> None:
        """Format row query results as CSV."""
        self._write_csv(response.data, out)

    def format_aggregate(self, response: AggregateResponse, out: IO[str]) -> None:
        """Format aggregate query results as CSV."""
        self._write_csv(response.data, out)

    def format_discovery(self, rows: list[dict[str, object]], out: IO[str]) -> None:
        """Format discovery data as CSV."""
        self._write_csv(rows, out)

    def _write_csv(self, data: list[dict[str, Any]], out: IO[str]) -> None:
        """Write data as CSV using polars."""
        import polars as pl

        if not data:
            return
        df = pl.DataFrame(data)
        out.write(df.write_csv())


class JsonlFormatter:
    """One JSON object per line (for streaming/logging)."""

    def format_rows(self, response: RowsResponse, out: IO[str]) -> None:
        """Format row query results as JSONL (one object per line)."""
        for row in response.data:
            json.dump(row, out, default=str)
            out.write("\n")

    def format_aggregate(self, response: AggregateResponse, out: IO[str]) -> None:
        """Format aggregate query results as JSONL."""
        for row in response.data:
            json.dump(row, out, default=str)
            out.write("\n")

    def format_discovery(self, rows: list[dict[str, object]], out: IO[str]) -> None:
        """Format discovery data as JSONL."""
        for row in rows:
            json.dump(row, out, default=str)
            out.write("\n")


# Formatter registry for --format flag resolution
FORMATTERS: dict[str, type] = {
    "table": TableFormatter,
    "json": JsonFormatter,
    "csv": CsvFormatter,
    "jsonl": JsonlFormatter,
}
