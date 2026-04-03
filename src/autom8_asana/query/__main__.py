"""CLI entry point for QueryEngine.

Usage:
    python -m autom8_asana.query rows offer --classification active --select gid,name,mrr
    python -m autom8_asana.query rows offer --join business:booking_type --classification active
    python -m autom8_asana.query rows offer --live --select gid,name,mrr
    python -m autom8_asana.query rows offer --save my_active_offers
    python -m autom8_asana.query aggregate offer --group-by section --agg sum:mrr
    python -m autom8_asana.query aggregate offer --group-by section --agg sum:mrr --live
    python -m autom8_asana.query run active_offers
    python -m autom8_asana.query run active_offers --classification inactive --limit 50
    python -m autom8_asana.query run ./queries/mrr_by_vertical.yaml --format json
    python -m autom8_asana.query entities
    python -m autom8_asana.query fields offer
    python -m autom8_asana.query relations offer
    python -m autom8_asana.query sections offer
    python -m autom8_asana.query list-queries
    python -m autom8_asana.query timeline offer --moved-to ACTIVE --since 30d --format table

For a standalone entry point that bypasses the settings guard, use:
    python -m autom8_asana.query.cli <subcommand> [options]
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import IO, Any, Literal


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


def parse_where_flag(raw: str) -> dict[str, Any]:
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


def parse_where_json(raw: str) -> dict[str, Any]:
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
) -> dict[str, Any] | None:
    """Combine --where and --where-json into a single predicate dict.

    Rules:
    - Multiple --where flags: wrapped in AndGroup
    - --where-json: parsed as-is
    - Both: AndGroup([parsed_json, *parsed_flags])
    - Neither: None (no filter)

    Raises CLIError if --where-json contains invalid JSON or predicate structure.
    """
    nodes: list[dict[str, Any]] = []
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


def parse_agg_flag(raw: str) -> dict[str, Any]:
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
    result: dict[str, Any] = {"column": column, "agg": func.value}
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
# Live mode (--live): HTTP client that hits the existing API
# ---------------------------------------------------------------------------
# ADR-AQ-007: --live mode uses the existing HTTP API surface rather than
# wiring up EntityQueryService's full DI stack (UniversalResolutionStrategy,
# DataFrameCache, AsanaClient, EntityProjectRegistry). This keeps the CLI
# thin and avoids duplicating the service wiring that the API already handles.


def _get_live_config() -> tuple[str, dict[str, str]]:
    """Resolve live API URL + auth headers via platform TokenManager.

    Uses autom8y_core.TokenManager for S2S JWT exchange with retry,
    backoff, and proper error handling. Reads SERVICE_CLIENT_ID and
    SERVICE_CLIENT_SECRET from environment (ServiceAccount convention).

    Returns:
        Tuple of (base_url, headers_with_jwt).

    Raises:
        CLIError: If ServiceAccount credentials are not set or auth exchange fails.
    """
    import os

    from autom8y_core import Config, TokenManager
    from autom8y_core.errors import TokenAcquisitionError

    base_url = os.environ.get("AUTOM8Y_DATA_URL", "https://data.api.autom8y.io")
    try:
        config = Config.from_env()
    except ValueError:
        raise CLIError(
            "Live mode requires SERVICE_CLIENT_ID and SERVICE_CLIENT_SECRET "
            "environment variables. Set them or remove --live for offline (S3 cache) mode.",
            exit_code=2,
        )
    manager = TokenManager(config)
    try:
        token = manager.get_token()
    except TokenAcquisitionError as e:
        raise CLIError(f"Auth failed: {e}", exit_code=2)
    finally:
        manager.close()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    return base_url, headers


def execute_live_rows(
    entity_type: str,
    request_data: dict[str, Any],
) -> Any:
    """Execute a rows query via the live HTTP API.

    Args:
        entity_type: Entity type to query.
        request_data: RowsRequest-compatible dict for the POST body.

    Returns:
        RowsResponse parsed from the API response.

    Raises:
        CLIError: On HTTP errors or connectivity issues.
    """
    import httpx

    from autom8_asana.query.models import RowsResponse

    base_url, headers = _get_live_config()
    url = f"{base_url}/v1/query/{entity_type}/rows"

    try:
        resp = httpx.post(
            url,
            json=request_data,
            headers=headers,
            timeout=30.0,
        )
        resp.raise_for_status()
    except httpx.ConnectError:
        raise CLIError(
            f"Cannot connect to {base_url}. "
            "Is the data service running? Start with 'just dev-up data'.",
            exit_code=2,
        )
    except httpx.HTTPStatusError as e:
        raise CLIError(
            f"API error ({e.response.status_code}): {e.response.text}",
            exit_code=1,
        )
    except httpx.TimeoutException:
        raise CLIError(
            f"Request to {url} timed out after 30s.",
            exit_code=2,
        )

    return RowsResponse.model_validate(resp.json())


def execute_live_aggregate(
    entity_type: str,
    request_data: dict[str, Any],
) -> Any:
    """Execute an aggregate query via the live HTTP API.

    Args:
        entity_type: Entity type to query.
        request_data: AggregateRequest-compatible dict for the POST body.

    Returns:
        AggregateResponse parsed from the API response.

    Raises:
        CLIError: On HTTP errors or connectivity issues.
    """
    import httpx

    from autom8_asana.query.models import AggregateResponse

    base_url, headers = _get_live_config()
    url = f"{base_url}/v1/query/{entity_type}/aggregate"

    try:
        resp = httpx.post(
            url,
            json=request_data,
            headers=headers,
            timeout=30.0,
        )
        resp.raise_for_status()
    except httpx.ConnectError:
        raise CLIError(
            f"Cannot connect to {base_url}. "
            "Is the data service running? Start with 'just dev-up data'.",
            exit_code=2,
        )
    except httpx.HTTPStatusError as e:
        raise CLIError(
            f"API error ({e.response.status_code}): {e.response.text}",
            exit_code=1,
        )
    except httpx.TimeoutException:
        raise CLIError(
            f"Request to {url} timed out after 30s.",
            exit_code=2,
        )

    return AggregateResponse.model_validate(resp.json())


# ---------------------------------------------------------------------------
# Metadata output
# ---------------------------------------------------------------------------


def _format_age(seconds: float) -> str:
    """Format age in seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    elif seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    else:
        return f"{seconds / 86400:.1f}d"


def print_metadata(meta: Any, file: IO[str] | None = None) -> None:
    """Print query metadata to stderr.

    Format:
      total: 342, returned: 100, query_ms: 1247.3, freshness: s3_offline, data_age: 2.3h

    Per AC-4.7: metadata to stderr prevents contamination of
    stdout data when piping to jq/csv tools.
    """
    if file is None:
        file = sys.stderr

    parts: list[str] = []
    if hasattr(meta, "total_count"):
        parts.append(f"total: {meta.total_count}")
        parts.append(f"returned: {meta.returned_count}")
    if hasattr(meta, "group_count"):
        parts.append(f"groups: {meta.group_count}")
    parts.append(f"query_ms: {meta.query_ms}")
    if hasattr(meta, "freshness") and meta.freshness:
        parts.append(f"freshness: {meta.freshness}")
    if hasattr(meta, "data_age_seconds") and meta.data_age_seconds is not None:
        age = meta.data_age_seconds
        parts.append(f"data_age: {_format_age(age)}")
    if hasattr(meta, "join_entity") and meta.join_entity:
        parts.append(
            f"join: {meta.join_entity} "
            f"({meta.join_matched} matched, "
            f"{meta.join_unmatched} unmatched)"
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
    if isinstance(error, OSError):
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
        return cls(no_truncate=no_truncate)
    return cls()


def _get_output_stream(args: argparse.Namespace) -> IO[str]:
    """Get the output stream from parsed args."""
    output_path = getattr(args, "output", None)
    if output_path:
        return open(output_path, "w")  # noqa: SIM115
    return sys.stdout


def _create_data_client_if_needed(
    join_spec: dict[str, Any] | None,
) -> Any:
    """Create DataServiceClient when a data-service join is requested.

    Returns None for entity joins (no data-service access needed).
    Raises CLIError with clear message if init fails for data-service joins.
    """
    if join_spec is None or join_spec.get("source") != "data-service":
        return None

    try:
        from autom8_asana.clients.data.client import DataServiceClient

        # Prefer SERVICE_CLIENT_ID + SERVICE_CLIENT_SECRET → TokenManager → JWT.
        # Falls back to AUTOM8Y_DATA_API_KEY env var via DataServiceClient default.
        auth_provider = None
        try:
            from autom8_asana.auth.service_token import ServiceTokenAuthProvider

            auth_provider = ServiceTokenAuthProvider()
        except (ValueError, ImportError):
            pass

        return DataServiceClient(auth_provider=auth_provider)
    except Exception as e:
        raise CLIError(
            f"Data-service joins require AUTOM8Y_DATA_URL and authentication "
            f"(SERVICE_CLIENT_ID + SERVICE_CLIENT_SECRET or AUTOM8Y_DATA_API_KEY). Error: {e}"
        ) from None


def handle_rows(args: argparse.Namespace) -> int:
    """Handle the 'rows' subcommand."""
    import asyncio

    from autom8_asana.query.engine import QueryEngine
    from autom8_asana.query.models import RowsRequest

    entity_type, project_gid = resolve_entity_type(args.entity_type)

    # Build predicate
    predicate = build_predicate(
        getattr(args, "where", None),
        getattr(args, "where_json", None),
    )

    # Build join spec (--join or --enrich)
    join_spec = None
    enrich_str = getattr(args, "enrich", None)
    join_list = getattr(args, "join", None)

    if enrich_str and join_list:
        raise CLIError("--enrich and --join are mutually exclusive")

    if enrich_str:
        # --enrich is shorthand for data-service join
        join_spec = _parse_join(
            enrich_str,
            join_on=getattr(args, "join_on", None),
            source="data-service",
            factory=enrich_str.split(":")[0].strip() if ":" in enrich_str else None,
            period=getattr(args, "join_period", "LIFETIME"),
        )
    elif join_list:
        if len(join_list) > 1:
            print(
                f"Note: Only one --join is supported per query. "
                f"Using first: {join_list[0]}",
                file=sys.stderr,
            )
        join_spec = _parse_join(
            join_list[0],
            getattr(args, "join_on", None),
            source=getattr(args, "join_source", "entity"),
            factory=getattr(args, "join_factory", None),
            period=getattr(args, "join_period", "LIFETIME"),
        )

    # Build RowsRequest dict
    request_data: dict[str, Any] = {
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

    # --live: execute via HTTP API instead of local S3 parquets
    if getattr(args, "live", False):
        result = execute_live_rows(entity_type, request_data)
    else:
        from .offline_provider import (
            NullClient,
            OfflineDataFrameProvider,
            OfflineProjectRegistry,
        )

        request = RowsRequest.model_validate(request_data)

        provider = OfflineDataFrameProvider()
        data_client = _create_data_client_if_needed(join_spec)
        engine = QueryEngine(provider=provider, data_client=data_client)
        client = NullClient()
        project_registry = OfflineProjectRegistry()

        result = asyncio.run(
            engine.execute_rows(
                entity_type=entity_type,
                project_gid=project_gid,
                client=client,
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

    # --save post-execution hook
    save_name = getattr(args, "save", None)
    if save_name:
        _save_rows_query(args, save_name)

    return 0


def _save_rows_query(args: argparse.Namespace, name: str) -> None:
    """Build a SavedQuery from rows args and persist to disk."""
    from autom8_asana.query.saved import SavedQuery, save_query

    data: dict[str, Any] = {
        "name": name,
        "command": "rows",
        "entity_type": args.entity_type,
        "format": getattr(args, "output_format", "table") or "table",
    }
    if args.classification:
        data["classification"] = args.classification
    if args.section:
        data["section"] = args.section
    if args.select:
        data["select"] = [s.strip() for s in args.select.split(",")]
    if args.limit != 100:
        data["limit"] = args.limit
    if args.offset != 0:
        data["offset"] = args.offset
    if args.order_by:
        data["order_by"] = args.order_by
    if args.order_dir != "asc":
        data["order_dir"] = args.order_dir

    predicate = build_predicate(
        getattr(args, "where", None),
        getattr(args, "where_json", None),
    )
    if predicate:
        data["where"] = predicate

    join_list = getattr(args, "join", None)
    if join_list:
        join_spec = _parse_join(join_list[0], getattr(args, "join_on", None))
        data["join"] = join_spec

    saved = SavedQuery.model_validate(data)
    try:
        path = save_query(saved, name)
        print(f"Query saved: {path}", file=sys.stderr)
    except FileExistsError as e:
        print(f"Warning: {e}", file=sys.stderr)


def handle_aggregate(args: argparse.Namespace) -> int:
    """Handle the 'aggregate' subcommand."""
    import asyncio

    from autom8_asana.query.engine import QueryEngine
    from autom8_asana.query.models import AggregateRequest

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

    # Build AggregateRequest dict
    request_data: dict[str, Any] = {
        "where": predicate,
        "group_by": [s.strip() for s in args.group_by.split(",")],
        "aggregations": agg_specs,
    }
    if args.section:
        request_data["section"] = args.section
    if having:
        request_data["having"] = having

    # --live: execute via HTTP API instead of local S3 parquets
    if getattr(args, "live", False):
        result = execute_live_aggregate(entity_type, request_data)
    else:
        from .offline_provider import NullClient, OfflineDataFrameProvider

        request = AggregateRequest.model_validate(request_data)

        provider = OfflineDataFrameProvider()
        engine = QueryEngine(provider=provider, data_client=None)
        client = NullClient()

        result = asyncio.run(
            engine.execute_aggregate(
                entity_type=entity_type,
                project_gid=project_gid,
                client=client,
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

    # --save post-execution hook
    save_name = getattr(args, "save", None)
    if save_name:
        _save_aggregate_query(args, save_name)

    return 0


def _save_aggregate_query(args: argparse.Namespace, name: str) -> None:
    """Build a SavedQuery from aggregate args and persist to disk."""
    from autom8_asana.query.saved import SavedQuery, save_query

    data: dict[str, Any] = {
        "name": name,
        "command": "aggregate",
        "entity_type": args.entity_type,
        "format": getattr(args, "output_format", "table") or "table",
        "group_by": [s.strip() for s in args.group_by.split(",")],
        "aggregations": [parse_agg_flag(raw) for raw in args.agg],
    }
    if args.classification:
        data["classification"] = args.classification
    if args.section:
        data["section"] = args.section

    predicate = build_predicate(
        getattr(args, "where", None),
        getattr(args, "where_json", None),
    )
    if predicate:
        data["where"] = predicate

    having = None
    if args.having:
        having = build_predicate(args.having, None)
    if having:
        data["having"] = having

    saved = SavedQuery.model_validate(data)
    try:
        path = save_query(saved, name)
        print(f"Query saved: {path}", file=sys.stderr)
    except FileExistsError as e:
        print(f"Warning: {e}", file=sys.stderr)


def handle_entities(args: argparse.Namespace) -> int:
    """Handle the 'entities' subcommand."""
    from autom8_asana.query.introspection import list_entities

    rows = list_entities()

    formatter = _get_formatter(args)
    out = _get_output_stream(args)
    try:
        formatter.format_discovery(rows, out)  # type: ignore[attr-defined]
    finally:
        if out is not sys.stdout:
            out.close()

    return 0


def handle_data_sources(args: argparse.Namespace) -> int:
    """Handle the 'data-sources' subcommand."""
    from autom8_asana.query.data_service_entities import list_data_service_entities

    rows = list_data_service_entities()

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
    from autom8_asana.query.introspection import list_fields

    try:
        rows = list_fields(args.entity_type)
    except ValueError as e:
        raise CLIError(str(e)) from None

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
    from autom8_asana.query.introspection import list_relations

    rows = list_relations(args.entity_type)

    formatter = _get_formatter(args)
    out = _get_output_stream(args)
    try:
        formatter.format_discovery(rows, out)  # type: ignore[attr-defined]
    finally:
        if out is not sys.stdout:
            out.close()

    return 0


def handle_sections(args: argparse.Namespace) -> int:
    """Handle the 'sections' subcommand."""
    from autom8_asana.query.introspection import list_sections

    try:
        rows = list_sections(args.entity_type)
    except ValueError as e:
        raise CLIError(str(e)) from None

    formatter = _get_formatter(args)
    out = _get_output_stream(args)
    try:
        formatter.format_discovery(rows, out)  # type: ignore[attr-defined]
    finally:
        if out is not sys.stdout:
            out.close()

    return 0


def handle_timeline(args: argparse.Namespace) -> int:
    """Handle the 'timeline' subcommand.

    Loads cached SectionTimeline data from local parquet, applies
    TemporalFilter, and formats matching timelines as flat rows.
    """
    from pathlib import Path

    from autom8_asana.query.temporal import TemporalFilter, parse_date_or_relative
    from autom8_asana.query.timeline_provider import TimelineStore

    # Parse date arguments
    since = None
    until = None
    if args.since:
        try:
            since = parse_date_or_relative(args.since)
        except ValueError as e:
            raise CLIError(str(e)) from None
    if args.until:
        try:
            until = parse_date_or_relative(args.until)
        except ValueError as e:
            raise CLIError(str(e)) from None

    # Build filter
    temporal_filter = TemporalFilter(
        moved_to=args.moved_to,
        moved_from=args.moved_from,
        since=since,
        until=until,
    )

    # Resolve cache directory and load
    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    store = TimelineStore(cache_dir=cache_dir) if cache_dir else TimelineStore()

    # We need a project GID to locate cached timelines.
    # Use the entity_type to resolve it from the registry.
    _, project_gid = resolve_entity_type(args.entity_type)

    timelines = store.load(project_gid)
    if timelines is None:
        cache_path = store._parquet_path(project_gid)
        raise CLIError(
            f"No cached timeline data found for '{args.entity_type}' "
            f"(project {project_gid}).\n"
            f"Expected: {cache_path}\n"
            "Timeline data requires live computation from Asana stories. "
            "A future release will add a --compute flag for live generation."
        )

    # Apply filter
    matched = [tl for tl in timelines if temporal_filter.matches(tl)]

    # Flatten to rows for output
    rows: list[dict[str, object]] = []
    for tl in matched:
        for interval in tl.intervals:
            rows.append(
                {
                    "offer_gid": tl.offer_gid,
                    "office_phone": tl.office_phone,
                    "offer_id": tl.offer_id,
                    "section_name": interval.section_name,
                    "classification": (
                        interval.classification.value
                        if interval.classification is not None
                        else None
                    ),
                    "entered_at": str(interval.entered_at),
                    "exited_at": (
                        str(interval.exited_at) if interval.exited_at else None
                    ),
                }
            )

    # Output
    formatter = _get_formatter(args)
    out = _get_output_stream(args)
    try:
        formatter.format_discovery(rows, out)  # type: ignore[attr-defined]
        # Print summary metadata to stderr
        print(
            f"matched: {len(matched)} timelines, "
            f"intervals: {len(rows)}, "
            f"total_cached: {len(timelines)}",
            file=sys.stderr,
        )
    finally:
        if out is not sys.stdout:
            out.close()

    return 0


def handle_list_queries(args: argparse.Namespace) -> int:
    """Handle the 'list-queries' subcommand -- discover saved query templates.

    Scans ``./queries/`` and ``~/.autom8/queries/`` for YAML/JSON files,
    loads each via ``load_saved_query()``, and displays a discovery table
    with name, description, entity_type, and command.
    """
    from pathlib import Path

    from autom8_asana.query.saved import load_saved_query

    search_dirs = [
        Path.cwd() / "queries",
        Path.home() / ".autom8" / "queries",
    ]

    rows: list[dict[str, object]] = []
    for d in search_dirs:
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.suffix not in (".yaml", ".yml", ".json"):
                continue
            try:
                saved = load_saved_query(p)
                rows.append(
                    {
                        "name": saved.name,
                        "description": saved.description,
                        "entity_type": saved.entity_type,
                        "command": saved.command,
                        "path": str(p),
                    }
                )
            except Exception:
                # Skip malformed query files silently
                continue

    if not rows:
        print(
            "No saved queries found. Place .yaml/.json files in "
            "./queries/ or ~/.autom8/queries/",
            file=sys.stderr,
        )

    formatter = _get_formatter(args)
    out = _get_output_stream(args)
    try:
        formatter.format_discovery(rows, out)  # type: ignore[attr-defined]
    finally:
        if out is not sys.stdout:
            out.close()

    return 0


def handle_run(args: argparse.Namespace) -> int:
    """Handle the 'run' subcommand -- execute a saved query template.

    Loads a SavedQuery from a file path or by name, constructs the
    appropriate RowsRequest or AggregateRequest, and executes it.
    """
    import asyncio
    from pathlib import Path

    from autom8_asana.query.engine import QueryEngine
    from autom8_asana.query.models import AggregateRequest, RowsRequest
    from autom8_asana.query.saved import (
        SavedQuery,
        find_saved_query,
        load_saved_query,
    )

    from .offline_provider import (
        NullClient,
        OfflineDataFrameProvider,
        OfflineProjectRegistry,
    )

    # 1. Locate the query
    query_arg = args.query
    query_path = Path(query_arg)
    if query_path.exists():
        saved = load_saved_query(query_path)
    else:
        found = find_saved_query(query_arg)
        if found is None:
            raise CLIError(
                f"Saved query not found: '{query_arg}'. "
                "Provide a file path or place query YAML in ./queries/ "
                "or ~/.autom8/queries/"
            )
        saved = load_saved_query(found)

    # 2. Apply CLI overrides -- explicitly provided flags win over saved values
    overrides: dict[str, Any] = {}
    fmt_override = getattr(args, "output_format", None)
    if fmt_override is not None:
        overrides["format"] = fmt_override

    # Predicate overrides
    cli_where = getattr(args, "where", None)
    cli_where_json = getattr(args, "where_json", None)
    cli_predicate = build_predicate(cli_where, cli_where_json)
    if cli_predicate is not None:
        overrides["where"] = cli_predicate

    if getattr(args, "classification", None) is not None:
        overrides["classification"] = args.classification
    if getattr(args, "section", None) is not None:
        overrides["section"] = args.section
    if getattr(args, "select", None) is not None:
        overrides["select"] = [s.strip() for s in args.select.split(",")]
    if getattr(args, "limit", None) is not None:
        overrides["limit"] = args.limit
    if getattr(args, "offset", None) is not None:
        overrides["offset"] = args.offset
    if getattr(args, "order_by", None) is not None:
        overrides["order_by"] = args.order_by
    if getattr(args, "order_dir", None) is not None:
        overrides["order_dir"] = args.order_dir

    if overrides:
        saved = SavedQuery(**{**saved.model_dump(), **overrides})

    # 3. Resolve entity type
    entity_type, project_gid = resolve_entity_type(saved.entity_type)

    # 4. Build and execute based on command type
    provider = OfflineDataFrameProvider()

    # Create DataServiceClient for saved queries with data-service joins
    saved_join_dict = saved.join.model_dump(exclude_none=True) if saved.join else None
    data_client = _create_data_client_if_needed(saved_join_dict)

    engine = QueryEngine(provider=provider, data_client=data_client)
    client = NullClient()
    project_registry = OfflineProjectRegistry()

    # Override args for formatter
    args.output_format = saved.format
    if not hasattr(args, "no_truncate"):
        args.no_truncate = False

    if saved.command == "rows":
        request_data: dict[str, Any] = {
            "limit": saved.limit,
            "offset": saved.offset,
        }
        if saved.where:
            request_data["where"] = saved.where
        if saved.section:
            request_data["section"] = saved.section
        if saved.classification:
            request_data["classification"] = saved.classification
        if saved.select:
            request_data["select"] = saved.select
        if saved.order_by:
            request_data["order_by"] = saved.order_by
        if saved.order_dir:
            request_data["order_dir"] = saved.order_dir
        if saved.join:
            request_data["join"] = saved.join.model_dump(exclude_none=True)

        request = RowsRequest.model_validate(request_data)

        result = asyncio.run(
            engine.execute_rows(
                entity_type=entity_type,
                project_gid=project_gid,
                client=client,
                request=request,
                entity_project_registry=project_registry,
            )
        )

        formatter = _get_formatter(args)
        out = _get_output_stream(args)
        try:
            formatter.format_rows(result, out)  # type: ignore[attr-defined]
            print_metadata(result.meta)
        finally:
            if out is not sys.stdout:
                out.close()

    elif saved.command == "aggregate":
        if not saved.group_by:
            raise CLIError("Saved aggregate query must specify 'group_by'")
        if not saved.aggregations:
            raise CLIError("Saved aggregate query must specify 'aggregations'")

        agg_data: dict[str, Any] = {
            "group_by": saved.group_by,
            "aggregations": saved.aggregations,
        }
        if saved.where:
            agg_data["where"] = saved.where
        if saved.section:
            agg_data["section"] = saved.section
        if saved.having:
            agg_data["having"] = saved.having

        agg_request = AggregateRequest.model_validate(agg_data)

        agg_result = asyncio.run(
            engine.execute_aggregate(
                entity_type=entity_type,
                project_gid=project_gid,
                client=client,
                request=agg_request,
            )
        )

        formatter = _get_formatter(args)
        out = _get_output_stream(args)
        try:
            formatter.format_aggregate(agg_result, out)  # type: ignore[attr-defined]
            print_metadata(agg_result.meta)
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


def _parse_join(
    join_str: str,
    join_on: str | None,
    source: str = "entity",
    factory: str | None = None,
    period: str = "LIFETIME",
) -> dict[str, Any]:
    """Parse 'entity:col1,col2' to a JoinSpec-compatible dict.

    Args:
        join_str: Combined entity:columns string (e.g., "business:booking_type,stripe_id").
        join_on: Optional explicit join key override.
        source: Join source ("entity" or "data-service").
        factory: DataService factory name (required when source="data-service").
        period: Period for data-service joins (default: LIFETIME).

    Returns:
        Dict suitable for JoinSpec.model_validate().

    Raises:
        CLIError: If the join string format is invalid.
    """
    if ":" not in join_str:
        raise CLIError(
            f"Invalid --join format: {join_str!r}. Expected ENTITY:col1,col2"
        )
    entity_type, cols_str = join_str.split(":", 1)
    select = [c.strip() for c in cols_str.split(",") if c.strip()]
    if not select:
        raise CLIError(f"No columns specified in --join: {join_str!r}")
    result: dict[str, Any] = {"entity_type": entity_type.strip(), "select": select}
    if join_on is not None:
        result["on"] = join_on

    # Cross-service join parameters
    if source == "data-service":
        if factory is None:
            raise CLIError("--join-factory is required when --join-source=data-service")
        result["source"] = "data-service"
        result["factory"] = factory
        result["period"] = period

    return result


def _add_join_args(parser: argparse.ArgumentParser) -> None:
    """Cross-entity join args (rows only).

    Accepts multiple --join flags via action="append". Currently only the
    first join is used (RowsRequest supports single join). A warning is
    printed to stderr if more than one --join is provided.
    """
    parser.add_argument(
        "--join",
        action="append",
        help="Join entity:col1,col2 (e.g., --join business:booking_type). "
        "Can be specified multiple times (only first used in current release).",
    )
    parser.add_argument(
        "--join-on",
        dest="join_on",
        help="Explicit join key (default: auto-resolved from relationship)",
    )
    # Cross-service join parameters
    parser.add_argument(
        "--join-source",
        dest="join_source",
        choices=["entity", "data-service"],
        default="entity",
        help="Join source: 'entity' (Asana cache) or 'data-service' (autom8y-data API)",
    )
    parser.add_argument(
        "--join-factory",
        dest="join_factory",
        help="DataService factory name (required when --join-source=data-service). "
        "E.g., spend, leads, appts, campaigns, base.",
    )
    parser.add_argument(
        "--join-period",
        dest="join_period",
        default="LIFETIME",
        help="Period for data-service joins (T7, T30, LIFETIME). Default: LIFETIME",
    )
    # Shorthand for data-service enrichment joins
    parser.add_argument(
        "--enrich",
        help="Shorthand for data-service join: FACTORY:col1,col2 "
        "(e.g., --enrich spend:spend,cps). Implies --join-source=data-service. "
        "Use --join-period to set period (default: LIFETIME).",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="autom8_asana.query",
        description="Query entity data from cached Asana section parquets",
    )
    # Logging verbosity (mutually exclusive)
    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging output",
    )
    log_group.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress all logging (including errors)",
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
    rows_parser.add_argument(
        "--save",
        help="Save this query as a reusable template to ~/.autom8/queries/<name>.yaml",
    )
    rows_parser.add_argument(
        "--live",
        action="store_true",
        help="Use live API instead of S3 cache (requires SERVICE_CLIENT_ID + SERVICE_CLIENT_SECRET)",
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
    agg_parser.add_argument(
        "--save",
        help="Save this query as a reusable template to ~/.autom8/queries/<name>.yaml",
    )
    agg_parser.add_argument(
        "--live",
        action="store_true",
        help="Use live API instead of S3 cache (requires SERVICE_CLIENT_ID + SERVICE_CLIENT_SECRET)",
    )

    # --- discovery subcommands ---
    ent_parser = subparsers.add_parser(
        "entities",
        help="List queryable entity types",
        description="List all queryable entity types with project GIDs and categories.",
        epilog=(
            "Examples:\n"
            "  %(prog)s                          # table output\n"
            "  %(prog)s --format json             # JSON output for scripting\n"
            "  %(prog)s --format csv --output entities.csv\n"
            "\n"
            "Use 'fields <entity>' to see columns, "
            "'sections <entity>' for classification mapping."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
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

    # --- sections subcommand ---
    sections_parser = subparsers.add_parser(
        "sections",
        help="List section names and classifications for an entity type",
        description=(
            "List all Asana project sections and their activity classifications\n"
            "(active, activating, inactive, ignored) for the given entity type.\n\n"
            "Example: sections offer"
        ),
    )
    sections_parser.add_argument(
        "entity_type",
        help="Entity type to inspect (offer, unit)",
    )
    _add_output_args(sections_parser)

    # --- data-sources subcommand ---
    ds_parser = subparsers.add_parser(
        "data-sources",
        help="List available data-service factories for cross-service joins",
        description=(
            "List analytics data sources from autom8y-data that can be used\n"
            "with --enrich or --join-source=data-service for cross-service joins.\n\n"
            "Example: data-sources --format json"
        ),
    )
    _add_output_args(ds_parser)

    # --- timeline subcommand ---
    timeline_parser = subparsers.add_parser(
        "timeline",
        help="Query section transitions over time",
        description=(
            "Query section transitions using cached SectionTimeline data.\n\n"
            "Examples:\n"
            "  timeline offer --moved-to ACTIVE --since 30d\n"
            "  timeline offer --moved-from 'Sales Process' --moved-to ACTIVE --since 2025-01-01"
        ),
    )
    timeline_parser.add_argument(
        "entity_type",
        help="Entity type (offer, unit)",
    )
    timeline_parser.add_argument(
        "--moved-to",
        dest="moved_to",
        help="Filter to transitions entering this section or classification",
    )
    timeline_parser.add_argument(
        "--moved-from",
        dest="moved_from",
        help="Filter to transitions from this section or classification",
    )
    timeline_parser.add_argument(
        "--since",
        help="Transitions on or after this date (ISO date or relative: 30d, 4w)",
    )
    timeline_parser.add_argument(
        "--until",
        help="Transitions on or before this date (ISO date or relative: 30d, 4w)",
    )
    timeline_parser.add_argument(
        "--cache-dir",
        dest="cache_dir",
        help="Local timeline cache directory (default: ~/.autom8/timelines)",
    )
    _add_output_args(timeline_parser)

    # --- list-queries subcommand ---
    list_queries_parser = subparsers.add_parser(
        "list-queries",
        help="Discover available saved query templates",
        description=(
            "Scan ./queries/ and ~/.autom8/queries/ for saved query templates\n"
            "and display their name, description, entity type, and command.\n\n"
            "Example: list-queries --format json"
        ),
    )
    _add_output_args(list_queries_parser)

    # --- run subcommand (saved queries) ---
    run_parser = subparsers.add_parser(
        "run",
        help="Execute a saved query template",
        description=(
            "Execute a saved query from a YAML/JSON template file.\n\n"
            "Examples:\n"
            "  run active_offers\n"
            "  run ./queries/mrr_by_vertical.yaml --format json\n"
            "  run offers_with_business --format csv"
        ),
    )
    run_parser.add_argument(
        "query",
        help="Saved query name or path to YAML/JSON file",
    )
    run_parser.add_argument(
        "--format",
        choices=["table", "json", "csv", "jsonl"],
        dest="output_format",
        default=None,
        help="Override output format from saved query",
    )
    run_parser.add_argument(
        "--output",
        help="Write to file instead of stdout",
    )
    run_parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="Disable table column truncation",
    )
    # Override flags for saved query parameters
    run_parser.add_argument(
        "--where",
        action="append",
        help="Override filter: 'field op value' (multiple ANDed)",
    )
    run_parser.add_argument(
        "--where-json",
        help="Override complex predicate tree as JSON",
    )
    run_parser.add_argument(
        "--classification",
        default=None,
        help="Override classification filter",
    )
    run_parser.add_argument(
        "--section",
        default=None,
        help="Override section name filter",
    )
    run_parser.add_argument(
        "--select",
        default=None,
        help="Override comma-separated column list",
    )
    run_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Override max rows to return",
    )
    run_parser.add_argument(
        "--offset",
        type=int,
        default=None,
        help="Override row offset",
    )
    run_parser.add_argument(
        "--order-by",
        default=None,
        help="Override sort column",
    )
    run_parser.add_argument(
        "--order-dir",
        choices=["asc", "desc"],
        default=None,
        help="Override sort direction",
    )

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _configure_logging(*, verbose: bool = False, quiet: bool = False) -> None:
    """Configure logging for CLI usage.

    By default, suppresses all library noise (structlog JSON lines from
    HolderFactory, schema warnings, etc.) so only query output appears.
    --verbose enables DEBUG output; --quiet suppresses everything.
    """
    from autom8y_log import LogConfig, configure_logging

    level_name: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    if quiet:
        level_name = "ERROR"
        level = logging.CRITICAL + 10  # Suppress everything via stdlib
    elif verbose:
        level_name = "DEBUG"
        level = logging.DEBUG
    else:
        level_name = "ERROR"
        level = logging.ERROR

    # Configure stdlib logging to suppress library noise
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stderr,
        force=True,
    )
    for logger_name in (
        "autom8_asana",
        "autom8y_log",
        "autom8y_config",
        "httpx",
        "httpcore",
        "boto3",
        "botocore",
        "urllib3",
    ):
        logging.getLogger(logger_name).setLevel(level)

    # Reconfigure autom8y_log/structlog to match
    configure_logging(LogConfig(level=level_name))


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code."""
    import os

    # G-01: Bypass settings guard for offline CLI -- we never need the
    # data service or workspace GID.  setdefault() is safe: it only sets
    # the value when the var is absent, so it won't interfere with tests
    # or production environments that already set these.
    os.environ.setdefault("AUTOM8Y_DATA_URL", "http://offline-cli.local")
    os.environ.setdefault("ASANA_WORKSPACE_GID", "offline")
    # G-02: Suppress import-time log noise.  When invoked via
    # `python -m autom8_asana.query`, the package __init__.py has already
    # loaded and emitted logs by this point.  For fully clean output, use
    # `python -m autom8_asana.query.cli` which sets LOG_LEVEL before imports.
    os.environ.setdefault("LOG_LEVEL", "ERROR")

    parser = build_parser()
    args = parser.parse_args(argv)

    # G-02: Suppress log noise before any handler imports trigger logging
    _configure_logging(
        verbose=getattr(args, "verbose", False),
        quiet=getattr(args, "quiet", False),
    )

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
        "sections": handle_sections,
        "data-sources": handle_data_sources,
        "timeline": handle_timeline,
        "list-queries": handle_list_queries,
        "run": handle_run,
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
