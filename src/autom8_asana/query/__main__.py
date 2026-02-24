"""CLI entry point for QueryEngine.

Usage:
    python -m autom8_asana.query rows offer --classification active --select gid,name,mrr
    python -m autom8_asana.query aggregate offer --group-by section --agg sum:mrr
    python -m autom8_asana.query entities
    python -m autom8_asana.query fields offer
    python -m autom8_asana.query relations offer
"""

from __future__ import annotations

import argparse
import sys
from typing import IO


class CLIError(Exception):
    """User-facing CLI error with actionable message."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


# ---------------------------------------------------------------------------
# Flag-to-model mapping helpers
# ---------------------------------------------------------------------------


def _coerce_value(raw: str) -> str | int | float | bool:
    """Best-effort type coercion for CLI values.

    Order: int -> float -> bool -> str (fallback).
    PredicateCompiler handles final type validation against schema dtype.

    Strings starting with '+' are preserved as strings (phone numbers,
    positive markers) since int('+N') silently drops the prefix.
    """
    # Preserve strings starting with '+' as strings (phone numbers etc.)
    if raw.startswith("+"):
        return raw
    # Try int
    try:
        return int(raw)
    except ValueError:
        pass
    # Try float
    try:
        return float(raw)
    except ValueError:
        pass
    # Try bool
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    # Fallback to string
    return raw


def parse_where_flag(raw: str) -> dict:
    """Parse 'field op value' into a Comparison-compatible dict.

    Supports:
      --where 'section eq ACTIVE'
      --where 'mrr gt 5000'
      --where 'office_phone starts_with +1'
      --where 'vertical in dental,chiropractic'

    For 'in' and 'not_in' operators, value is split on commas.
    """
    from autom8_asana.query.models import Op

    parts = raw.split(None, 2)  # Split on first 2 whitespace
    if len(parts) != 3:
        raise CLIError(
            f"Invalid predicate: '{raw}'. Expected format: 'field op value'. "
            f"Supported ops: {', '.join(op.value for op in Op)}"
        )
    field_name, op_str, value_str = parts
    try:
        op = Op(op_str)
    except ValueError:
        raise CLIError(
            f"Unknown operator: '{op_str}'. "
            f"Supported: {', '.join(op.value for op in Op)}"
        ) from None

    # Coerce value based on operator
    if op in (Op.IN, Op.NOT_IN):
        value: str | int | float | bool | list[str] = value_str.split(",")
    else:
        value = _coerce_value(value_str)

    return {"field": field_name, "op": op.value, "value": value}


def parse_where_json(raw: str) -> dict:
    """Parse a JSON predicate tree into a dict for Pydantic validation.

    Delegates to Pydantic model_validate, which uses the
    _predicate_discriminator for automatic variant selection.
    """
    import json

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise CLIError(f"Invalid JSON in --where-json: {e}") from None

    if not isinstance(data, dict):
        raise CLIError(
            f"Invalid --where-json: expected a JSON object, got {type(data).__name__}"
        )
    return data


def build_predicate(
    where_flags: list[str] | None, where_json: str | None
) -> dict | None:
    """Combine --where and --where-json into a single predicate dict.

    Rules:
    - Multiple --where flags: wrapped in AndGroup
    - --where-json: parsed as-is
    - Both: AndGroup([parsed_json, *parsed_flags])
    - Neither: None (no filter)

    Raises CLIError if --where-json contains invalid JSON or predicate structure.
    """
    nodes: list[dict] = []
    if where_flags:
        for raw in where_flags:
            nodes.append(parse_where_flag(raw))
    if where_json:
        nodes.append(parse_where_json(where_json))

    if not nodes:
        return None
    if len(nodes) == 1:
        return nodes[0]
    return {"and": nodes}


def parse_agg_flag(raw: str) -> dict:
    """Parse 'function:column[:alias]' into AggSpec-compatible dict.

    Examples:
      --agg sum:mrr          -> {"column": "mrr", "agg": "sum"}
      --agg count:gid        -> {"column": "gid", "agg": "count"}
      --agg sum:mrr:total    -> {"column": "mrr", "agg": "sum", "alias": "total"}
    """
    from autom8_asana.query.models import AggFunction

    parts = raw.split(":")
    if len(parts) < 2 or len(parts) > 3:
        raise CLIError(
            f"Invalid aggregation: '{raw}'. "
            "Expected format: 'function:column[:alias]'. "
            f"Supported functions: {', '.join(f.value for f in AggFunction)}"
        )
    func_str, column = parts[0], parts[1]
    alias = parts[2] if len(parts) == 3 else None
    try:
        func = AggFunction(func_str)
    except ValueError:
        raise CLIError(
            f"Unknown aggregation function: '{func_str}'. "
            f"Supported: {', '.join(f.value for f in AggFunction)}"
        ) from None
    result: dict = {"column": column, "agg": func.value}
    if alias is not None:
        result["alias"] = alias
    return result


# ---------------------------------------------------------------------------
# Entity resolution
# ---------------------------------------------------------------------------


def resolve_entity_type(entity_type: str) -> tuple[str, str]:
    """Validate entity type and resolve its project GID.

    Returns:
        Tuple of (entity_type, project_gid).

    Raises:
        CLIError: If entity type is unknown or has no project GID.
    """
    from autom8_asana.core.entity_registry import get_registry

    registry = get_registry()
    desc = registry.get(entity_type)
    if desc is None:
        available = sorted(d.name for d in registry.all_descriptors() if d.warmable)
        raise CLIError(
            f"Unknown entity type '{entity_type}'. Available: {', '.join(available)}"
        )
    if desc.primary_project_gid is None:
        available = sorted(d.name for d in registry.all_descriptors() if d.warmable)
        raise CLIError(
            f"Entity type '{entity_type}' has no project GID. "
            f"Queryable entities: {', '.join(available)}"
        )
    return entity_type, desc.primary_project_gid


# ---------------------------------------------------------------------------
# Metadata output
# ---------------------------------------------------------------------------


def print_metadata(meta: object, file: IO[str] | None = None) -> None:
    """Print query metadata to stderr.

    Format:
      total: 342, returned: 100, query_ms: 1247.3, freshness: s3_offline

    Per AC-4.7: metadata to stderr prevents contamination of
    stdout data when piping to jq/csv tools.
    """
    if file is None:
        file = sys.stderr

    parts: list[str] = []
    if hasattr(meta, "total_count"):
        parts.append(f"total: {meta.total_count}")  # type: ignore[attr-defined]
        parts.append(f"returned: {meta.returned_count}")  # type: ignore[attr-defined]
    if hasattr(meta, "group_count"):
        parts.append(f"groups: {meta.group_count}")  # type: ignore[attr-defined]
    parts.append(f"query_ms: {meta.query_ms}")  # type: ignore[attr-defined]
    if hasattr(meta, "freshness") and meta.freshness:  # type: ignore[attr-defined]
        parts.append(f"freshness: {meta.freshness}")  # type: ignore[attr-defined]
    if hasattr(meta, "join_entity") and meta.join_entity:  # type: ignore[attr-defined]
        parts.append(
            f"join: {meta.join_entity} "  # type: ignore[attr-defined]
            f"({meta.join_matched} matched, "  # type: ignore[attr-defined]
            f"{meta.join_unmatched} unmatched)"  # type: ignore[attr-defined]
        )
    print(", ".join(parts), file=file)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def handle_error(error: Exception) -> int:
    """Map exceptions to exit codes per NFR-006.

    Returns:
        Exit code (0=success, 1=query error, 2=infrastructure error).
    """
    from autom8_asana.query.errors import QueryEngineError

    if isinstance(error, CLIError):
        print(f"ERROR: {error}", file=sys.stderr)
        return error.exit_code
    if isinstance(error, QueryEngineError):
        d = error.to_dict()
        print(f"ERROR: {d['message']}", file=sys.stderr)
        return 1
    if isinstance(error, FileNotFoundError):
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if isinstance(error, ValueError):
        # S3 bucket not configured or other value errors
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if isinstance(error, (OSError, PermissionError)):
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    # Unexpected
    print(f"INTERNAL ERROR: {error}", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _get_formatter(args: argparse.Namespace) -> object:
    """Build the output formatter from parsed args."""
    from autom8_asana.query.formatters import FORMATTERS, TableFormatter

    fmt_name = getattr(args, "output_format", "table")
    no_truncate = getattr(args, "no_truncate", False)
    cls = FORMATTERS.get(fmt_name, TableFormatter)
    if cls is TableFormatter:
        return cls(no_truncate=no_truncate)  # type: ignore[call-arg]
    return cls()


def _get_output_stream(args: argparse.Namespace) -> IO[str]:
    """Get the output stream from parsed args."""
    output_path = getattr(args, "output", None)
    if output_path:
        return open(output_path, "w")  # noqa: SIM115
    return sys.stdout


def handle_rows(args: argparse.Namespace) -> int:
    """Handle the 'rows' subcommand."""
    import asyncio

    from autom8_asana.query.engine import QueryEngine
    from autom8_asana.query.models import RowsRequest

    from .offline_provider import (
        NullClient,
        OfflineDataFrameProvider,
        OfflineProjectRegistry,
    )

    entity_type, project_gid = resolve_entity_type(args.entity_type)

    # Build predicate
    predicate = build_predicate(
        getattr(args, "where", None),
        getattr(args, "where_json", None),
    )

    # Build join spec
    join_spec = None
    if args.join:
        if not args.join_select:
            raise CLIError(
                "--join-select is required when --join is specified. "
                "Example: --join business --join-select booking_type,stripe_id"
            )
        join_spec = {
            "entity_type": args.join,
            "select": [s.strip() for s in args.join_select.split(",")],
        }
        if args.join_on:
            join_spec["on"] = args.join_on

    # Build RowsRequest
    request_data: dict = {
        "where": predicate,
        "limit": args.limit,
        "offset": args.offset,
    }
    if args.section:
        request_data["section"] = args.section
    if args.classification:
        request_data["classification"] = args.classification
    if args.select:
        request_data["select"] = [s.strip() for s in args.select.split(",")]
    if args.order_by:
        request_data["order_by"] = args.order_by
    if args.order_dir:
        request_data["order_dir"] = args.order_dir
    if join_spec:
        request_data["join"] = join_spec

    request = RowsRequest.model_validate(request_data)

    # Build engine
    provider = OfflineDataFrameProvider()
    engine = QueryEngine(provider=provider)
    client = NullClient()
    project_registry = OfflineProjectRegistry()

    # Execute
    result = asyncio.run(
        engine.execute_rows(
            entity_type=entity_type,
            project_gid=project_gid,
            client=client,  # type: ignore[arg-type]
            request=request,
            entity_project_registry=project_registry,
        )
    )

    # Output
    formatter = _get_formatter(args)
    out = _get_output_stream(args)
    try:
        formatter.format_rows(result, out)  # type: ignore[attr-defined]
        print_metadata(result.meta)
    finally:
        if out is not sys.stdout:
            out.close()

    return 0


def handle_aggregate(args: argparse.Namespace) -> int:
    """Handle the 'aggregate' subcommand."""
    import asyncio

    from autom8_asana.query.engine import QueryEngine
    from autom8_asana.query.models import AggregateRequest

    from .offline_provider import NullClient, OfflineDataFrameProvider

    entity_type, project_gid = resolve_entity_type(args.entity_type)

    # Build predicate
    predicate = build_predicate(
        getattr(args, "where", None),
        getattr(args, "where_json", None),
    )

    # Parse agg specs
    agg_specs = [parse_agg_flag(raw) for raw in args.agg]

    # Build having predicate
    having = None
    if args.having:
        having = build_predicate(args.having, None)

    # Build AggregateRequest
    request_data: dict = {
        "where": predicate,
        "group_by": [s.strip() for s in args.group_by.split(",")],
        "aggregations": agg_specs,
    }
    if args.section:
        request_data["section"] = args.section
    if having:
        request_data["having"] = having

    request = AggregateRequest.model_validate(request_data)

    # Build engine
    provider = OfflineDataFrameProvider()
    engine = QueryEngine(provider=provider)
    client = NullClient()

    # Execute
    result = asyncio.run(
        engine.execute_aggregate(
            entity_type=entity_type,
            project_gid=project_gid,
            client=client,  # type: ignore[arg-type]
            request=request,
        )
    )

    # Output
    formatter = _get_formatter(args)
    out = _get_output_stream(args)
    try:
        formatter.format_aggregate(result, out)  # type: ignore[attr-defined]
        print_metadata(result.meta)
    finally:
        if out is not sys.stdout:
            out.close()

    return 0


def handle_entities(args: argparse.Namespace) -> int:
    """Handle the 'entities' subcommand."""
    from autom8_asana.core.entity_registry import get_registry

    registry = get_registry()
    rows: list[dict[str, object]] = []
    for desc in registry.warmable_entities():
        rows.append(
            {
                "entity_type": desc.name,
                "display_name": desc.display_name,
                "project_gid": desc.primary_project_gid,
                "category": desc.category.value,
            }
        )

    formatter = _get_formatter(args)
    out = _get_output_stream(args)
    try:
        formatter.format_discovery(rows, out)  # type: ignore[attr-defined]
    finally:
        if out is not sys.stdout:
            out.close()

    return 0


def handle_fields(args: argparse.Namespace) -> int:
    """Handle the 'fields' subcommand."""
    from autom8_asana.dataframes.models.registry import SchemaRegistry
    from autom8_asana.query.engine import _to_pascal_case

    pascal_name = _to_pascal_case(args.entity_type)
    registry = SchemaRegistry.get_instance()

    if not registry.has_schema(pascal_name):
        from autom8_asana.core.entity_registry import get_registry as get_er

        available = sorted(
            d.name for d in get_er().all_descriptors() if d.schema_module_path
        )
        raise CLIError(
            f"No schema available for '{args.entity_type}'. "
            f"Queryable entities: {', '.join(available)}"
        )

    schema = registry.get_schema(pascal_name)
    rows: list[dict[str, object]] = []
    for col in schema.columns:
        rows.append(
            {
                "name": col.name,
                "dtype": col.dtype,
                "nullable": col.nullable,
                "description": col.description or "",
            }
        )

    formatter = _get_formatter(args)
    out = _get_output_stream(args)
    try:
        formatter.format_discovery(rows, out)  # type: ignore[attr-defined]
    finally:
        if out is not sys.stdout:
            out.close()

    return 0


def handle_relations(args: argparse.Namespace) -> int:
    """Handle the 'relations' subcommand."""
    from autom8_asana.query.hierarchy import ENTITY_RELATIONSHIPS

    entity_type = args.entity_type
    rows: list[dict[str, object]] = []
    for rel in ENTITY_RELATIONSHIPS:
        if rel.parent_type == entity_type:
            rows.append(
                {
                    "target": rel.child_type,
                    "direction": "parent->child",
                    "default_join_key": rel.default_join_key,
                    "description": rel.description,
                }
            )
        elif rel.child_type == entity_type:
            rows.append(
                {
                    "target": rel.parent_type,
                    "direction": "child->parent",
                    "default_join_key": rel.default_join_key,
                    "description": rel.description,
                }
            )

    formatter = _get_formatter(args)
    out = _get_output_stream(args)
    try:
        formatter.format_discovery(rows, out)  # type: ignore[attr-defined]
    finally:
        if out is not sys.stdout:
            out.close()

    return 0


# ---------------------------------------------------------------------------
# Argument parser construction
# ---------------------------------------------------------------------------


def _add_output_args(parser: argparse.ArgumentParser) -> None:
    """Output format and destination args."""
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv", "jsonl"],
        default="table",
        dest="output_format",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--output",
        help="Write to file instead of stdout",
    )
    parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="Disable table column truncation",
    )


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Entity type + output format args shared across query subcommands."""
    parser.add_argument(
        "entity_type",
        help="Entity type to query (offer, unit, business, contact, asset_edit)",
    )
    _add_output_args(parser)


def _add_filter_args(parser: argparse.ArgumentParser) -> None:
    """Predicate and classification filter args."""
    parser.add_argument(
        "--where",
        action="append",
        help="Filter: 'field op value' (multiple ANDed). Example: --where 'mrr gt 5000'",
    )
    parser.add_argument(
        "--where-json",
        help="Complex predicate tree as JSON. Example: --where-json '{\"or\": [...]}'",
    )
    parser.add_argument(
        "--section",
        help="Filter by exact section name",
    )
    parser.add_argument(
        "--classification",
        help="Filter by classification (active/activating/inactive/ignored)",
    )


def _add_join_args(parser: argparse.ArgumentParser) -> None:
    """Cross-entity join args (rows only)."""
    parser.add_argument(
        "--join",
        help="Entity type to join (e.g., --join business)",
    )
    parser.add_argument(
        "--join-select",
        help="Comma-separated columns from joined entity. Example: --join-select booking_type,stripe_id",
    )
    parser.add_argument(
        "--join-on",
        help="Override join key (default: auto-resolved from entity relationships)",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="autom8_asana.query",
        description="Query entity data from cached Asana section parquets",
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- rows subcommand ---
    rows_parser = subparsers.add_parser(
        "rows",
        help="Query entity rows with filters",
        description=(
            "Query entity rows with filters, pagination, and column selection.\n\n"
            "Example: rows offer --classification active --select gid,name,mrr --format table"
        ),
    )
    _add_common_args(rows_parser)
    _add_filter_args(rows_parser)
    _add_join_args(rows_parser)
    rows_parser.add_argument(
        "--select",
        help="Comma-separated column list. Example: --select gid,name,mrr,office_phone",
    )
    rows_parser.add_argument(
        "--limit", type=int, default=100, help="Max rows to return (default: 100)"
    )
    rows_parser.add_argument(
        "--offset", type=int, default=0, help="Rows to skip (default: 0)"
    )
    rows_parser.add_argument("--order-by", help="Column to sort by")
    rows_parser.add_argument(
        "--order-dir",
        choices=["asc", "desc"],
        default="asc",
        help="Sort direction (default: asc)",
    )

    # --- aggregate subcommand ---
    agg_parser = subparsers.add_parser(
        "aggregate",
        help="Aggregate entity data with grouping",
        description=(
            "Aggregate entity data with grouping and filters.\n\n"
            "Example: aggregate offer --group-by section --agg sum:mrr"
        ),
    )
    _add_common_args(agg_parser)
    _add_filter_args(agg_parser)
    agg_parser.add_argument(
        "--group-by",
        required=True,
        help="Comma-separated group columns. Example: --group-by section",
    )
    agg_parser.add_argument(
        "--agg",
        action="append",
        required=True,
        help="Agg spec: function:column[:alias]. Example: --agg sum:mrr --agg count:gid",
    )
    agg_parser.add_argument(
        "--having",
        action="append",
        help="Post-agg filter: 'field op value'. Example: --having 'sum_mrr gt 1000'",
    )

    # --- discovery subcommands ---
    ent_parser = subparsers.add_parser(
        "entities",
        help="List queryable entity types",
        description="List all queryable entity types with project GIDs and categories.",
    )
    _add_output_args(ent_parser)

    fields_parser = subparsers.add_parser(
        "fields",
        help="List entity fields",
        description=(
            "List all columns for an entity type with dtype, nullable, and description.\n\n"
            "Example: fields offer"
        ),
    )
    fields_parser.add_argument(
        "entity_type",
        help="Entity type to inspect",
    )
    _add_output_args(fields_parser)

    rel_parser = subparsers.add_parser(
        "relations",
        help="List joinable entity types",
        description=(
            "List entity types that can be joined with the given entity.\n\n"
            "Example: relations offer"
        ),
    )
    rel_parser.add_argument(
        "entity_type",
        help="Entity type to inspect",
    )
    _add_output_args(rel_parser)

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    # Route to handler
    handlers = {
        "rows": handle_rows,
        "aggregate": handle_aggregate,
        "entities": handle_entities,
        "fields": handle_fields,
        "relations": handle_relations,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except CLIError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return e.exit_code
    except Exception as e:
        return handle_error(e)


if __name__ == "__main__":
    sys.exit(main())
