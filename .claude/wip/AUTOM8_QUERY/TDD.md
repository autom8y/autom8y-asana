# TDD: AUTOM8_QUERY -- CLI and Offline Query Surface for QueryEngine

## Overview

This TDD specifies the technical design for exposing the existing QueryEngine through a composable CLI (`python -m autom8_asana.query`) and an OfflineDataFrameProvider that bridges sync S3 parquet access to the async DataFrameProvider protocol. The architecture achieves 80%+ reuse of existing infrastructure: QueryEngine, PredicateCompiler, JoinSpec, SchemaRegistry, EntityRegistry, and SectionClassifier are consumed as-is. New code is limited to the CLI argument parser, the offline provider adapter, a NullClient sentinel, an OfflineProjectRegistry adapter, and an output formatter layer.

## Context

- **PRD**: `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/AUTOM8_QUERY/PRD.md`
- **Existing QueryEngine**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/engine.py`
- **DataFrameProvider Protocol**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/protocols/dataframe_provider.py`
- **Reference CLI pattern**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/metrics/__main__.py`
- **Offline S3 loader**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/dataframes/offline.py`

**Constraints**:
1. QueryEngine is async (`execute_rows`/`execute_aggregate` are `async def`). CLI runs single-threaded via `asyncio.run()`.
2. DataFrameProvider.get_dataframe() requires an `AsanaClient` parameter. Offline mode has no client.
3. QueryEngine.execute_rows() uses `entity_project_registry.get_project_gid()` for join target DataFrame loading. Offline mode must resolve entity_type to project_gid without the running service stack.
4. `load_project_dataframe()` is sync (boto3). The provider protocol is async.
5. SectionTimeline data comes from Asana story analysis (live API), not from DataFrame cache parquets.

---

## System Design

### Architecture Diagram

```
CLI Entry Point                          Existing Infrastructure
(new)                                    (reused as-is)

  python -m autom8_asana.query
         |
         v
  +------------------+
  | query/__main__.py|  argparse
  | (CLI Router)     |
  +--------+---------+
           |
     parse flags
           |
           v
  +------------------+     +----------------------------+
  | build_request()  |---->| RowsRequest / AggRequest   |
  | (flag->model)    |     | (query/models.py)          |
  +--------+---------+     +----------------------------+
           |
           v
  +------------------+     +----------------------------+
  | asyncio.run()    |---->| QueryEngine                |
  |                  |     | .execute_rows()            |
  +--------+---------+     | .execute_aggregate()       |
           |               +----------------------------+
           |                     |              |
           |                     v              v
           |          +------------------+  +------------------+
           |          | OfflineDataFrame |  | PredicateCompiler|
           |          | Provider (new)   |  | (reused)         |
           |          +--------+---------+  +------------------+
           |                   |
           |                   v
           |          +------------------+
           |          | load_project_    |
           |          | dataframe()      |
           |          | (offline.py)     |
           |          +------------------+
           |                   |
           |                   v
           |              S3 Parquets
           |
           v
  +------------------+
  | OutputFormatter  |
  | (new)            |
  +--------+---------+
           |
           v
      stdout / file

Supporting Adapters (all new):

  +------------------+    +---------------------+    +------------------+
  | NullClient       |    | OfflineProject      |    | OfflineFreshness |
  | (sentinel)       |    | Registry (adapter)  |    | Info (metadata)  |
  +------------------+    +---------------------+    +------------------+
```

### Components

| Component | Responsibility | Location | Status |
|-----------|---------------|----------|--------|
| CLI Router | argparse subcommands, flag parsing, entry point | `query/__main__.py` | NEW |
| OfflineDataFrameProvider | Bridge sync S3 loader to async DataFrameProvider | `query/offline_provider.py` | NEW |
| NullClient | Sentinel AsanaClient that raises on any call | `query/offline_provider.py` | NEW |
| OfflineProjectRegistry | Adapter wrapping EntityRegistry for join resolution | `query/offline_provider.py` | NEW |
| OutputFormatter | Protocol + implementations (table/json/csv/jsonl) | `query/formatters.py` | NEW |
| QueryEngine | Predicate compilation, filtering, joins, aggregation | `query/engine.py` | REUSED |
| RowsRequest / AggregateRequest | Pydantic request models | `query/models.py` | REUSED |
| PredicateCompiler | AST to polars expression compilation | `query/compiler.py` | REUSED |
| JoinSpec / execute_join | Cross-entity join specification and execution | `query/join.py` | REUSED |
| EntityRelationship / hierarchy | Relationship registry, join key resolution | `query/hierarchy.py` | REUSED |
| EntityRegistry / get_registry | Entity metadata, project GID lookup | `core/entity_registry.py` | REUSED |
| SchemaRegistry | Column definitions, dtype metadata | `dataframes/models/registry.py` | REUSED |
| SectionClassifier / CLASSIFIERS | Section-to-classification mapping | `models/business/activity.py` | REUSED |
| load_project_dataframe | Sync S3 parquet loader | `dataframes/offline.py` | REUSED |
| SectionTimeline / OfferTimelineEntry | Temporal domain models | `models/business/section_timeline.py` | REUSED |
| SavedQueryStore | YAML serialization of named query templates | `query/templates.py` | NEW (Phase 3) |
| Introspection routes | GET endpoints for schema/entity discovery | `api/routes/introspection.py` | NEW (Phase 4) |

### Data Flow

**CLI invocation to stdout (rows query)**:

```
1. User: python -m autom8_asana.query rows offer --classification active --select gid,name,mrr --format table
2. __main__.py: argparse parses flags into namespace
3. build_rows_request(): Maps namespace to RowsRequest(classification="active", select=["gid","name","mrr"])
4. resolve_provider(): Creates OfflineDataFrameProvider (default) or EntityQueryService (--live)
5. resolve_project_gid(): EntityRegistry.get("offer").primary_project_gid -> "1143843662099250"
6. asyncio.run(execute_query()):
   a. engine = QueryEngine(provider=offline_provider)
   b. result = await engine.execute_rows(
        entity_type="offer",
        project_gid="1143843662099250",
        client=NullClient(),
        request=rows_request
      )
   c. engine internally calls provider.get_dataframe("offer", "1143843662099250", null_client)
   d. OfflineDataFrameProvider calls load_project_dataframe("1143843662099250") [sync, cached]
   e. engine applies classification filter, predicate filter, pagination, column select
   f. returns RowsResponse
7. format_output(): TableFormatter.format_rows(result, sys.stdout)
8. print_metadata(): stderr <- "total: 342, returned: 100, query_ms: 1247.3, freshness: s3_cached"
```

**Discovery subcommand (no query engine needed)**:

```
1. User: python -m autom8_asana.query fields offer
2. __main__.py: argparse routes to handle_fields()
3. handle_fields():
   a. SchemaRegistry.get_instance().get_schema("Offer") -> DataFrameSchema
   b. For each ColumnDef: emit (name, dtype, nullable, description)
4. format_output(): TableFormatter or JsonFormatter based on --format flag
```

---

## Interface Specifications

### OfflineDataFrameProvider

```python
# query/offline_provider.py

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

from autom8_asana.dataframes.offline import load_project_dataframe

if TYPE_CHECKING:
    import polars as pl
    from autom8_asana.cache.integration.dataframe_cache import FreshnessInfo
    from autom8_asana.client import AsanaClient


class OfflineDataFrameProvider:
    """DataFrameProvider backed by S3 parquet files.

    Bridges the sync load_project_dataframe() to the async
    DataFrameProvider protocol. Caches loaded DataFrames in-process
    to avoid re-reading S3 for join targets.

    Thread Safety:
        Single-threaded CLI context only. No lock needed.
    """

    def __init__(self, *, bucket: str | None = None, region: str = "us-east-1") -> None:
        self._bucket = bucket or os.environ.get("ASANA_CACHE_S3_BUCKET")
        self._region = region
        self._cache: dict[str, pl.DataFrame] = {}
        self._last_freshness: FreshnessInfo | None = None

    @property
    def last_freshness_info(self) -> FreshnessInfo | None:
        return self._last_freshness

    async def get_dataframe(
        self,
        entity_type: str,
        project_gid: str,
        client: AsanaClient,
    ) -> pl.DataFrame:
        """Load DataFrame from S3 parquets, with in-process caching.

        The client parameter is ignored (offline mode).
        Raises ValueError if bucket not configured.
        Raises FileNotFoundError if no parquets for project.
        """
        if project_gid in self._cache:
            return self._cache[project_gid]

        # Sync call in async wrapper -- acceptable for single-threaded CLI
        start = time.monotonic()
        df = load_project_dataframe(
            project_gid,
            bucket=self._bucket,
            region=self._region,
        )
        elapsed = time.monotonic() - start

        self._cache[project_gid] = df
        self._last_freshness = _build_offline_freshness(elapsed)
        return df
```

**Key design properties**:
- `_cache: dict[str, pl.DataFrame]` keyed by project_gid avoids re-reading S3 when the same entity type is used as both primary and join target, or when multiple join targets share a project.
- `async def get_dataframe(...)` is structurally async (no `await`) because `load_project_dataframe()` is sync boto3. This is acceptable because the CLI is single-threaded (`asyncio.run()` at top level). The alternative (`asyncio.to_thread()`) adds complexity without benefit in this context.
- Passes `@runtime_checkable` isinstance check: `isinstance(provider, DataFrameProvider)` is True.

### NullClient

```python
# query/offline_provider.py

class NullClient:
    """Sentinel AsanaClient for offline mode.

    Raises RuntimeError on any method call, catching accidental
    live API access in offline paths. Cleaner than passing None
    with type: ignore scattered through call sites.
    """

    def __getattr__(self, name: str) -> Never:
        raise RuntimeError(
            f"NullClient: attempted to call '{name}' in offline mode. "
            "Offline queries use S3 parquets and should never invoke the Asana API."
        )
```

**Rationale**: The DataFrameProvider.get_dataframe() signature requires `client: AsanaClient`. In offline mode, the client is never used (OfflineDataFrameProvider ignores it). Options considered:
1. Pass `None` -- requires `type: ignore` at call site, unclear error if accidentally used.
2. Pass `NullClient()` -- clean type, explicit error message, catches bugs in development.
3. Make client optional in protocol -- breaks the existing protocol contract used by EntityQueryService.

Option 2 wins: zero protocol changes, zero type: ignore, fail-fast with actionable message.

### OfflineProjectRegistry

```python
# query/offline_provider.py

class OfflineProjectRegistry:
    """Adapter providing get_project_gid() for offline join resolution.

    Wraps EntityRegistry, which carries primary_project_gid on each
    EntityDescriptor. This is the same data used at runtime by
    EntityProjectRegistry (services/resolver.py), but without requiring
    the running service stack or workspace discovery.

    Duck-types to the same interface expected by QueryEngine.execute_rows()
    entity_project_registry parameter.
    """

    def get_project_gid(self, entity_type: str) -> str | None:
        from autom8_asana.core.entity_registry import get_registry
        desc = get_registry().get(entity_type)
        return desc.primary_project_gid if desc else None
```

**Rationale**: QueryEngine.execute_rows() calls `entity_project_registry.get_project_gid(entity_type)` to resolve the project GID of a join target. At runtime, this is EntityProjectRegistry (services/resolver.py), populated by workspace discovery. Offline, we use EntityDescriptor.primary_project_gid directly. The interface is a single method (`get_project_gid(entity_type) -> str | None`), which is what QueryEngine duck-types against.

### OutputFormatter Protocol and Implementations

```python
# query/formatters.py

from __future__ import annotations

from typing import IO, TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from autom8_asana.query.models import AggregateResponse, RowsResponse


class OutputFormatter(Protocol):
    """Protocol for query result formatting."""

    def format_rows(self, response: RowsResponse, out: IO[str]) -> None: ...
    def format_aggregate(self, response: AggregateResponse, out: IO[str]) -> None: ...
    def format_discovery(self, rows: list[dict[str, object]], out: IO[str]) -> None: ...


class TableFormatter:
    """Human-readable aligned table using polars DataFrame repr.

    Truncates values > max_col_width characters with ellipsis.
    """

    def __init__(self, *, max_col_width: int = 40, no_truncate: bool = False) -> None:
        self._max_col_width = max_col_width
        self._no_truncate = no_truncate

    def format_rows(self, response: RowsResponse, out: IO[str]) -> None:
        import polars as pl
        if not response.data:
            out.write("(empty result set)\n")
            return
        df = pl.DataFrame(response.data)
        with pl.Config(
            tbl_cols=-1,
            tbl_width_chars=None if self._no_truncate else 200,
            fmt_str_lengths=0 if self._no_truncate else self._max_col_width,
        ):
            out.write(str(df) + "\n")

    def format_aggregate(self, response: AggregateResponse, out: IO[str]) -> None:
        # Same pattern as format_rows
        ...

    def format_discovery(self, rows: list[dict[str, object]], out: IO[str]) -> None:
        import polars as pl
        if not rows:
            out.write("(no results)\n")
            return
        df = pl.DataFrame(rows)
        out.write(str(df) + "\n")


class JsonFormatter:
    """JSON array output suitable for jq piping."""

    def format_rows(self, response: RowsResponse, out: IO[str]) -> None:
        import json
        json.dump(response.data, out, indent=2, default=str)
        out.write("\n")

    # format_aggregate, format_discovery: same pattern


class CsvFormatter:
    """CSV with headers suitable for spreadsheet import."""

    def format_rows(self, response: RowsResponse, out: IO[str]) -> None:
        import polars as pl
        if not response.data:
            return
        df = pl.DataFrame(response.data)
        out.write(df.write_csv())

    # format_aggregate, format_discovery: same pattern


class JsonlFormatter:
    """One JSON object per line (for streaming/logging)."""

    def format_rows(self, response: RowsResponse, out: IO[str]) -> None:
        import json
        for row in response.data:
            json.dump(row, out, default=str)
            out.write("\n")

    # format_aggregate, format_discovery: same pattern
```

**Formatter selection**:

```python
FORMATTERS: dict[str, type[OutputFormatter]] = {
    "table": TableFormatter,
    "json": JsonFormatter,
    "csv": CsvFormatter,
    "jsonl": JsonlFormatter,
}
```

### CLI Entry Point Structure

```python
# query/__main__.py

"""CLI entry point for QueryEngine.

Usage:
    python -m autom8_asana.query rows offer --classification active --select gid,name,mrr
    python -m autom8_asana.query aggregate offer --group-by section --agg sum:mrr
    python -m autom8_asana.query entities
    python -m autom8_asana.query fields offer
    python -m autom8_asana.query relations offer
    python -m autom8_asana.query sections offer
"""

import argparse
import asyncio
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="autom8_asana.query",
        description="Query entity data from cached Asana section parquets",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- rows subcommand ---
    rows_parser = subparsers.add_parser("rows", help="Query entity rows with filters")
    _add_common_args(rows_parser)
    _add_filter_args(rows_parser)
    _add_join_args(rows_parser)
    rows_parser.add_argument("--select", help="Comma-separated column list")
    rows_parser.add_argument("--limit", type=int, default=100)
    rows_parser.add_argument("--offset", type=int, default=0)
    rows_parser.add_argument("--order-by", help="Column to sort by")
    rows_parser.add_argument("--order-dir", choices=["asc", "desc"], default="asc")

    # --- aggregate subcommand ---
    agg_parser = subparsers.add_parser("aggregate", help="Aggregate entity data")
    _add_common_args(agg_parser)
    _add_filter_args(agg_parser)
    agg_parser.add_argument("--group-by", required=True, help="Comma-separated group columns")
    agg_parser.add_argument("--agg", action="append", required=True,
                            help="Agg spec: function:column[:alias]")
    agg_parser.add_argument("--having", action="append", help="Post-agg filter: field op value")

    # --- discovery subcommands ---
    ent_parser = subparsers.add_parser("entities", help="List queryable entity types")
    _add_output_args(ent_parser)

    fields_parser = subparsers.add_parser("fields", help="List entity fields")
    fields_parser.add_argument("entity_type", help="Entity type to inspect")
    _add_output_args(fields_parser)

    rel_parser = subparsers.add_parser("relations", help="List joinable entity types")
    rel_parser.add_argument("entity_type", help="Entity type to inspect")
    _add_output_args(rel_parser)

    sec_parser = subparsers.add_parser("sections", help="List sections with classifications")
    sec_parser.add_argument("entity_type", help="Entity type to inspect")
    _add_output_args(sec_parser)

    args = parser.parse_args()
    # Route to handler
    ...


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Entity type + output format args shared across query subcommands."""
    parser.add_argument("entity_type", help="Entity type to query (offer, unit, etc.)")
    _add_output_args(parser)
    parser.add_argument("--live", action="store_true",
                        help="Use live API instead of S3 cache")


def _add_filter_args(parser: argparse.ArgumentParser) -> None:
    """Predicate and classification filter args."""
    parser.add_argument("--where", action="append",
                        help="Filter: 'field op value' (multiple ANDed)")
    parser.add_argument("--where-json", help="Complex predicate tree as JSON")
    parser.add_argument("--section", help="Filter by exact section name")
    parser.add_argument("--classification",
                        help="Filter by classification (active/activating/inactive/ignored)")


def _add_join_args(parser: argparse.ArgumentParser) -> None:
    """Cross-entity join args (rows only)."""
    parser.add_argument("--join", help="Entity type to join")
    parser.add_argument("--join-select", help="Comma-separated columns from joined entity")
    parser.add_argument("--join-on", help="Override join key")


def _add_output_args(parser: argparse.ArgumentParser) -> None:
    """Output format and destination args."""
    parser.add_argument("--format", choices=["table", "json", "csv", "jsonl"],
                        default="table", dest="output_format")
    parser.add_argument("--output", help="Write to file instead of stdout")
    parser.add_argument("--no-truncate", action="store_true",
                        help="Disable table column truncation")
```

### Flag-to-Model Mapping

**`--where` flag parsing**:

```python
def parse_where_flag(raw: str) -> Comparison:
    """Parse 'field op value' into a Comparison node.

    Supports:
      --where 'section eq ACTIVE'
      --where 'mrr gt 5000'
      --where 'office_phone starts_with +1'
      --where 'vertical in dental,chiropractic'

    For 'in' and 'not_in' operators, value is split on commas.
    """
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
        )

    # Coerce value based on operator
    if op in (Op.IN, Op.NOT_IN):
        value = value_str.split(",")
    else:
        value = _coerce_value(value_str)

    return Comparison(field=field_name, op=op, value=value)


def _coerce_value(raw: str) -> str | int | float | bool:
    """Best-effort type coercion for CLI values.

    Order: int -> float -> bool -> str (fallback).
    PredicateCompiler handles final type validation against schema dtype.
    """
    ...
```

**`--agg` flag parsing**:

```python
def parse_agg_flag(raw: str) -> AggSpec:
    """Parse 'function:column[:alias]' into AggSpec.

    Examples:
      --agg sum:mrr          -> AggSpec(column="mrr", agg=AggFunction.SUM)
      --agg count:gid        -> AggSpec(column="gid", agg=AggFunction.COUNT)
      --agg sum:mrr:total    -> AggSpec(column="mrr", agg=AggFunction.SUM, alias="total")
    """
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
        )
    return AggSpec(column=column, agg=func, alias=alias)
```

**`--where-json` flag**:

```python
def parse_where_json(raw: str) -> PredicateNode:
    """Parse a JSON predicate tree into a PredicateNode.

    Delegates to Pydantic model_validate, which uses the
    _predicate_discriminator for automatic variant selection.
    """
    import json
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise CLIError(f"Invalid JSON in --where-json: {e}")

    # Pydantic's discriminated union handles the rest
    from pydantic import TypeAdapter
    adapter = TypeAdapter(PredicateNode)
    return adapter.validate_python(data)
```

**Multiple `--where` flags with AND semantics**:

```python
def build_predicate(where_flags: list[str] | None, where_json: str | None) -> PredicateNode | None:
    """Combine --where and --where-json into a single predicate tree.

    Rules:
    - Multiple --where flags: wrapped in AndGroup
    - --where-json: parsed as-is
    - Both: AndGroup([parsed_json, *parsed_flags])
    - Neither: None (no filter)

    Raises CLIError if --where-json contains invalid JSON or predicate structure.
    """
    nodes: list[PredicateNode] = []
    if where_flags:
        for raw in where_flags:
            nodes.append(parse_where_flag(raw))
    if where_json:
        nodes.append(parse_where_json(where_json))

    if not nodes:
        return None
    if len(nodes) == 1:
        return nodes[0]
    return AndGroup(and_=nodes)
```

### OfflineFreshnessInfo Helper

```python
# query/offline_provider.py

def _build_offline_freshness(load_seconds: float) -> FreshnessInfo:
    """Build FreshnessInfo for offline S3 data.

    Since S3 parquets have no TTL concept, we report a fixed
    freshness state that communicates "offline cache, age unknown".
    """
    from autom8_asana.cache.integration.dataframe_cache import FreshnessInfo

    return FreshnessInfo(
        freshness="s3_offline",
        data_age_seconds=load_seconds,
        staleness_ratio=0.0,  # Not applicable for offline
    )
```

### CLIError and Exit Code Mapping

```python
# query/__main__.py

class CLIError(Exception):
    """User-facing CLI error with actionable message."""
    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


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
        # S3 bucket not configured
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if isinstance(error, (OSError, PermissionError)):
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    # Unexpected
    print(f"INTERNAL ERROR: {error}", file=sys.stderr)
    return 2
```

### Metadata Output (stderr)

```python
def print_metadata(meta: RowsMeta | AggregateMeta, file: IO[str] = sys.stderr) -> None:
    """Print query metadata to stderr.

    Format:
      total: 342, returned: 100, query_ms: 1247.3, freshness: s3_offline

    Per AC-4.7: metadata to stderr prevents contamination of
    stdout data when piping to jq/csv tools.
    """
    parts = []
    if hasattr(meta, "total_count"):
        parts.append(f"total: {meta.total_count}")
        parts.append(f"returned: {meta.returned_count}")
    if hasattr(meta, "group_count"):
        parts.append(f"groups: {meta.group_count}")
    parts.append(f"query_ms: {meta.query_ms}")
    if meta.freshness:
        parts.append(f"freshness: {meta.freshness}")
    if hasattr(meta, "join_entity") and meta.join_entity:
        parts.append(f"join: {meta.join_entity} ({meta.join_matched} matched, {meta.join_unmatched} unmatched)")
    print(", ".join(parts), file=file)
```

---

## Discovery Subcommand Implementations

Discovery subcommands read from existing registries. No QueryEngine involved.

### entities

```python
def handle_entities(formatter: OutputFormatter, out: IO[str]) -> None:
    from autom8_asana.core.entity_registry import get_registry
    registry = get_registry()
    rows = []
    for desc in registry.warmable_entities():
        rows.append({
            "entity_type": desc.name,
            "display_name": desc.display_name,
            "project_gid": desc.primary_project_gid,
            "category": desc.category.value,
        })
    formatter.format_discovery(rows, out)
```

### fields

```python
def handle_fields(entity_type: str, formatter: OutputFormatter, out: IO[str]) -> None:
    from autom8_asana.dataframes.models.registry import SchemaRegistry
    from autom8_asana.query.engine import _to_pascal_case

    registry = SchemaRegistry.get_instance()
    schema = registry.get_schema(_to_pascal_case(entity_type))
    rows = []
    for col in schema.columns:
        rows.append({
            "name": col.name,
            "dtype": col.dtype,
            "nullable": col.nullable,
            "description": col.description or "",
        })
    formatter.format_discovery(rows, out)
```

### relations

```python
def handle_relations(entity_type: str, formatter: OutputFormatter, out: IO[str]) -> None:
    from autom8_asana.query.hierarchy import ENTITY_RELATIONSHIPS
    rows = []
    for rel in ENTITY_RELATIONSHIPS:
        if rel.parent_type == entity_type:
            rows.append({
                "target": rel.child_type,
                "direction": "parent->child",
                "default_join_key": rel.default_join_key,
                "description": rel.description,
            })
        elif rel.child_type == entity_type:
            rows.append({
                "target": rel.parent_type,
                "direction": "child->parent",
                "default_join_key": rel.default_join_key,
                "description": rel.description,
            })
    formatter.format_discovery(rows, out)
```

### sections

```python
def handle_sections(entity_type: str, formatter: OutputFormatter, out: IO[str]) -> None:
    from autom8_asana.models.business.activity import CLASSIFIERS
    classifier = CLASSIFIERS.get(entity_type)
    if classifier is None:
        available = sorted(CLASSIFIERS.keys())
        raise CLIError(
            f"No classification data for '{entity_type}'. "
            f"Available for: {available}"
        )
    rows = []
    for section_name, activity in sorted(classifier._mapping.items()):
        rows.append({
            "section": section_name,
            "classification": activity.value,
        })
    formatter.format_discovery(rows, out)
```

---

## Phase 3 Components

### SavedQueryStore (FR-010)

```python
# query/templates.py

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

QUERIES_DIR = Path.home() / ".autom8" / "queries"


@dataclass
class SavedQuery:
    """Serializable query template."""
    name: str
    command: str  # "rows" or "aggregate"
    entity_type: str
    params: dict[str, Any]  # All CLI params as dict
    description: str = ""

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.__dict__, default_flow_style=False)

    @classmethod
    def from_yaml(cls, raw: str) -> SavedQuery:
        data = yaml.safe_load(raw)
        return cls(**data)


class SavedQueryStore:
    """File-backed storage for named query templates.

    Storage: ~/.autom8/queries/{name}.yaml
    """

    def __init__(self, base_dir: Path = QUERIES_DIR) -> None:
        self._base_dir = base_dir

    def save(self, query: SavedQuery, *, overwrite: bool = False) -> Path:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        path = self._base_dir / f"{query.name}.yaml"
        if path.exists() and not overwrite:
            raise FileExistsError(
                f"Query '{query.name}' already exists at {path}. "
                "Use --force to overwrite."
            )
        path.write_text(query.to_yaml())
        return path

    def load(self, name: str) -> SavedQuery:
        path = self._base_dir / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(
                f"No saved query named '{name}'. "
                "Use 'list-queries' to see available."
            )
        return SavedQuery.from_yaml(path.read_text())

    def list_queries(self) -> list[str]:
        if not self._base_dir.exists():
            return []
        return sorted(p.stem for p in self._base_dir.glob("*.yaml"))
```

### Timeline Subcommand (FR-009)

```python
# Integrated into query/__main__.py as "timeline" subcommand

def handle_timeline(args: argparse.Namespace) -> None:
    """Execute timeline query.

    IMPORTANT: Timeline data comes from Asana story analysis
    (load_stories_incremental), NOT from DataFrame cache parquets.
    This always requires live API access regardless of --live flag.
    """
    from datetime import date
    start_str, end_str = args.period.split(":")
    period_start = date.fromisoformat(start_str)
    period_end = date.fromisoformat(end_str)

    # Timeline requires live API -- use SectionTimelineService
    # This is architecturally separate from the DataFrame query path
    ...
```

**Temporal architecture note**: SectionTimeline is fundamentally different from DataFrame cache. DataFrames are section-level snapshots (current state). Timeline is story-based transition history (historical state changes). These are separate data sources that cannot be unified without semantic loss. The `timeline` subcommand is intentionally separate from `rows`/`aggregate` and always requires live API access.

---

## Non-Functional Considerations

### Performance

| Operation | Target | Mechanism |
|-----------|--------|-----------|
| Single-entity offline query (cold) | < 3s | S3 parquet streaming via boto3 |
| Single-entity offline query (warm) | < 500ms | In-process dict cache by project_gid |
| Cross-entity join (cold) | < 6s | Both DataFrames loaded from S3, in-process cache prevents double-read |
| Aggregation | < 2s | Polars group_by().agg() on columnar data |
| Discovery subcommands | < 100ms | Registry reads only, no I/O |
| CLI startup overhead | < 200ms | Deferred imports (all heavy modules imported inside handlers) |

**In-process cache**: `OfflineDataFrameProvider._cache: dict[str, pl.DataFrame]` persists for the lifetime of one CLI invocation. For a rows query with join, both the primary and target DataFrames are loaded once. The cache is never shared across CLI invocations (process-scoped, not file-backed).

**Memory**: Peak memory for offer (20k rows, ~50 columns) is approximately 50-100MB in polars columnar representation. Cross-entity join with two entity types loaded simultaneously: ~200MB. Well within the 500MB/1GB NFR limits.

### Security

- **No new auth surfaces**: CLI reads from S3 (AWS IAM) and optionally live API (existing ASANA_SERVICE_KEY). No new credentials introduced.
- **NullClient prevents accidental live calls**: Offline mode cannot accidentally reach the Asana API.
- **No PII in error messages**: Error messages reference field names and entity types, not data values.
- **Saved queries stored locally**: `~/.autom8/queries/*.yaml` contains query parameters only, no data or credentials.

### Reliability

- **Graceful degradation**: If S3 is unreachable, clear error with exit code 2 and actionable guidance.
- **Exit code contract**: 0/1/2 mapping enables scripting (`set -e` compatible).
- **No service dependency in default mode**: Only AWS credentials + S3 bucket needed.
- **Existing error hierarchy reused**: All QueryEngineError subclasses produce structured errors via `.to_dict()`.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| S3 parquet schema drift from live cache | Low | Medium | load_project_dataframe uses `diagonal_relaxed` concat (handles missing columns). Schema mismatch detected by PredicateCompiler at query time with actionable error. |
| CLI startup latency from heavy imports | Medium | Low | Deferred imports in handler functions. Module-level imports limited to argparse and sys. Measured in metrics CLI: ~150ms acceptable. |
| `--where` value coercion ambiguity | Medium | Low | Best-effort coercion (int > float > bool > str). PredicateCompiler performs final type validation against schema dtype. Wrong coercion caught downstream with clear error. |
| FreshnessInfo "s3_offline" not recognized by consumers | Low | Low | FreshnessInfo.freshness is a free-form string, not an enum. Existing code handles unknown values (no fallback to enum validation). |
| OfflineDataFrameProvider breaks isinstance check | Low | High | Verified: `@runtime_checkable` protocol check requires `last_freshness_info` property + `get_dataframe` async method. Both present. Unit test in Phase 1 explicitly asserts this. |
| Entity types without schemas (process, location, hours) | Low | Low | EntityRegistry.warmable_entities() filters to schema-bearing entities. Discovery subcommands handle gracefully. Direct query against non-schema entity returns SchemaNotFoundError with available list. |

---

## ADRs

### ADR-AQ-001: OfflineDataFrameProvider Sync-to-Async Bridge

**Status**: Accepted

**Context**: The DataFrameProvider protocol defines `async def get_dataframe()`. The offline S3 loader (`load_project_dataframe()`) is synchronous (boto3). The CLI runs single-threaded via `asyncio.run()`. We need to bridge sync to async.

**Alternatives Considered**:

**Option A: asyncio.to_thread() wrapper**
- Pros: Properly runs sync I/O in a thread pool, non-blocking event loop.
- Cons: Adds complexity (thread pool management). CLI is single-threaded with no concurrent tasks -- there is nothing to "not block". Creates false impression of parallelism.

**Option B: Direct async wrapper (async def calling sync function)**
- Pros: Simple, honest. Clearly communicates that this is a single-threaded adapter. No thread pool overhead. Zero concurrency semantics to reason about.
- Cons: Technically "blocking the event loop" -- but the event loop has no other work.

**Option C: Make load_project_dataframe async (rewrite with aioboto3)**
- Pros: Truly async end-to-end. Would benefit future async consumers.
- Cons: aioboto3 is a third-party dependency with less stability than boto3. Significant rewrite of working code for a CLI that is inherently sequential. No current async consumer of this function.

**Decision**: Option B. The CLI is single-threaded. `asyncio.run()` at the top level drives the QueryEngine's async methods. The "blocking" of a sync S3 call in an async wrapper is harmless because there are no concurrent tasks. If a future consumer needs true async (e.g., a web endpoint), Option C can be pursued at that point -- the adapter pattern makes this a local change.

**Consequences**:
- Positive: Zero new dependencies. Simple to understand. Zero concurrency bugs.
- Negative: Cannot use this provider in a concurrent async context without modification.
- Neutral: In-process cache (`dict[str, pl.DataFrame]`) makes subsequent calls instant regardless of sync/async.

---

### ADR-AQ-002: NullClient Sentinel vs Optional Client

**Status**: Accepted

**Context**: `DataFrameProvider.get_dataframe(entity_type, project_gid, client)` requires an `AsanaClient` parameter. In offline mode, the client is never used. We need to satisfy the type signature without a real client.

**Alternatives Considered**:

**Option A: Pass None + type: ignore**
- Pros: Simplest possible change.
- Cons: Scatters `type: ignore` through call sites. No error message if accidentally used. Mypy cannot catch misuse.

**Option B: NullClient sentinel class**
- Pros: Clean type (duck-types to AsanaClient's interface). Raises RuntimeError with actionable message on any method call. Catches bugs where offline code accidentally reaches the API. No type: ignore needed.
- Cons: Introduces a new class (trivial -- 6 lines).

**Option C: Make client Optional in protocol**
- Pros: Explicit "client not needed" signal in the type system.
- Cons: Breaks existing EntityQueryService implementation. Every call site must handle Optional. Protocol change ripples across the codebase.

**Decision**: Option B. NullClient is a well-known pattern (Null Object). It satisfies the type system, provides a clear error, and requires zero changes to the existing protocol or its implementations.

**Consequences**:
- Positive: Zero protocol changes. Fail-fast with clear error on misuse.
- Negative: None significant.

---

### ADR-AQ-003: OfflineProjectRegistry via EntityRegistry

**Status**: Accepted

**Context**: QueryEngine.execute_rows() calls `entity_project_registry.get_project_gid(entity_type)` to resolve the project GID for join targets. At runtime, EntityProjectRegistry (services/resolver.py) is populated via workspace discovery. Offline mode has no running service stack.

**Alternatives Considered**:

**Option A: OfflineProjectRegistry wrapping EntityRegistry**
- Pros: EntityDescriptor.primary_project_gid is the source of truth for 6/7 warmable entity types. Always available (module-level constant). Single method adapter (`get_project_gid`). Duck-types to the same interface QueryEngine expects.
- Cons: Does not include dynamically-discovered projects (process, which has no primary_project_gid). If a new entity type has a dynamic project, it would not be queryable offline.

**Option B: Precompute a static mapping in config**
- Pros: Explicit, no runtime dependency on entity_registry.
- Cons: Duplicates data from ENTITY_DESCRIPTORS. Drifts when descriptors change. Extra maintenance burden.

**Option C: Require --live for joins**
- Pros: Simplest, avoids the problem entirely.
- Cons: Defeats the purpose of offline mode. Joins are a core use case.

**Decision**: Option A. All current warmable entity types have `primary_project_gid` set in their descriptors. The 1 entity without it (process) has no DataFrame schema and is not queryable. If a future entity has a dynamic project, it can be handled by extending OfflineProjectRegistry with a fallback to a config file.

**Consequences**:
- Positive: Zero config files. No duplication. Correct for all currently queryable entities.
- Negative: Entities with dynamic project GIDs (process) cannot be joined offline. This is acceptable because process has no schema.

---

### ADR-AQ-004: CLI Flag-to-Model Mapping Strategy

**Status**: Accepted

**Context**: CLI flags must be parsed into RowsRequest and AggregateRequest Pydantic models. The models have rich validation (mutual exclusion, min/max constraints, discriminated unions for predicates).

**Alternatives Considered**:

**Option A: Parse flags into dicts, let Pydantic validate**
- Pros: Leverage Pydantic's existing validation (e.g., section/classification mutual exclusion). Single validation path for both CLI and API.
- Cons: Error messages reference Pydantic field names, not CLI flag names. Requires dict construction that mirrors Pydantic schema.

**Option B: Parse flags into model kwargs, validate at construction**
- Pros: Same Pydantic validation. Model construction kwargs map cleanly to CLI flags. Allows pre-validation of CLI-specific constraints (e.g., --where syntax).
- Cons: Must handle Pydantic ValidationError and translate to CLIError with flag names.

**Option C: Separate CLI validation layer**
- Pros: CLI-native error messages. Full control over validation order.
- Cons: Duplicates model validation. Two places to update when model constraints change.

**Decision**: Option B. Parse flags into model kwargs, catch Pydantic `ValidationError`, translate to `CLIError` with CLI flag names. Pre-validate CLI-specific concerns (--where syntax, --agg syntax) before Pydantic model construction.

**Consequences**:
- Positive: Single validation path through Pydantic. CLI-friendly error messages via exception translation. No validation duplication.
- Negative: Must maintain a translation layer from ValidationError to CLIError. Acceptable given the small surface area.

---

### ADR-AQ-005: Output Formatter Architecture

**Status**: Accepted

**Context**: Query results must be rendered in 4 formats: table, JSON, CSV, JSONL. Formatters must handle both row data and aggregate data. Discovery subcommands also need formatting.

**Alternatives Considered**:

**Option A: Protocol with 3 methods (rows, aggregate, discovery)**
- Pros: Type-safe dispatch. Each formatter implements all 3 methods. Easy to add new formatters. Clean separation of data format from output destination.
- Cons: 3 methods per formatter (12 total for 4 formatters).

**Option B: Single format(data, out) method with polymorphic dispatch**
- Pros: Simpler interface. One method per formatter.
- Cons: Type erasure -- formatter receives `Any` and must inspect type. Loses the explicit contract.

**Option C: DataFrame-first (all formatters operate on polars DataFrame)**
- Pros: polars has write_csv, write_json, etc. built-in. Fewer methods.
- Cons: Aggregate results and discovery rows must be converted to DataFrame first. JSON format must match the RowsResponse.data structure (list of dicts), not polars' JSON format.

**Decision**: Option A. The protocol surface is small (3 methods x 4 formatters = 12 implementations, most trivial). Type safety prevents accidental data/format mismatches. The format_discovery method handles both field lists, entity lists, relation lists, and section lists -- all represented as list[dict].

**Consequences**:
- Positive: Type-safe. Easy to add CSV-with-custom-delimiter or Parquet formatter later. Output destination (stdout/file) is a parameter, not a formatter concern.
- Negative: 12 method implementations. Mitigated by shared patterns (most delegates to polars or json.dump).

---

### ADR-AQ-006: Temporal Architecture (Timeline Separate from DataFrame)

**Status**: Accepted

**Context**: PRD includes both DataFrame queries (rows, aggregate) and temporal queries (timeline). These use fundamentally different data sources: DataFrame queries use S3 parquet snapshots; timeline uses Asana story analysis (load_stories_incremental, always live). The question is whether to unify or separate.

**Alternatives Considered**:

**Option A: Separate timeline subcommand (different data path)**
- Pros: Honest about the data source difference. Timeline always requires live API (story-based). No artificial abstraction layer between incompatible data models. Clear to users that `timeline` has different requirements than `rows`.
- Cons: Two conceptually-related features have different invocation patterns.

**Option B: Virtual predicate in rows subcommand**
- Pros: Unified query surface. `--where 'active_days gt 15'` feels natural.
- Cons: Requires joining SectionTimeline data (live API, per-offer story analysis) with DataFrame data (S3 cache, per-section snapshot). The join would require loading ALL offer stories for temporal evaluation -- O(N * stories_per_offer) API calls. Fundamentally different performance characteristics hidden behind the same flag syntax.

**Option C: Pre-compute timeline into parquet**
- Pros: Would enable offline temporal queries.
- Cons: Timeline data requires `load_stories_incremental()` which calls the Asana API for each offer. Cannot be pre-computed without running the full pipeline. Story data volume is 10-100x larger than section snapshots. Storage and freshness concerns.

**Decision**: Option A for Phase 3. Timeline is a separate subcommand with explicit `--period` flag. Always live. FR-015 (predicate-level temporal filters) deferred to Phase 4 as a Could Have. If demand exists, Option C can enable offline temporal queries as a separate initiative.

**Consequences**:
- Positive: Clean separation. Users understand timeline requires API access. No hidden performance cliffs.
- Negative: Cannot combine temporal and DataFrame predicates in a single query (Phase 4 opportunity).

---

## Test Strategy

### Phase 1 Tests

**Unit tests** (`tests/unit/query/`):

| Test File | Scope | Fixture Pattern |
|-----------|-------|-----------------|
| `test_offline_provider.py` | OfflineDataFrameProvider protocol compliance, caching, error paths | Mock `load_project_dataframe` with pre-built polars DataFrames |
| `test_null_client.py` | NullClient raises on any attribute access | Direct instantiation |
| `test_offline_project_registry.py` | OfflineProjectRegistry delegates to EntityRegistry | Real EntityRegistry (singleton) |
| `test_cli_parsers.py` | parse_where_flag, parse_agg_flag, parse_where_json, _coerce_value | String inputs, expected Comparison/AggSpec outputs |
| `test_formatters.py` | All 4 formatters x {rows, aggregate, discovery} | Pre-built RowsResponse/AggregateResponse with known data; capture stdout via StringIO |
| `test_cli_e2e.py` | End-to-end CLI invocation via subprocess | Mock S3 via `monkeypatch` on `load_project_dataframe` |

**Key assertions**:
- `isinstance(OfflineDataFrameProvider(...), DataFrameProvider)` -- protocol compliance (SC-9)
- NullClient.__getattr__ raises RuntimeError with message containing method name
- `parse_where_flag("mrr gt 5000")` produces `Comparison(field="mrr", op=Op.GT, value=5000)`
- `parse_where_flag("vertical in dental,chiro")` produces `Comparison(field="vertical", op=Op.IN, value=["dental","chiro"])`
- `parse_agg_flag("sum:mrr:total")` produces `AggSpec(column="mrr", agg=AggFunction.SUM, alias="total")`
- Table formatter output contains column headers
- JSON formatter output is valid JSON (json.loads succeeds)
- CSV formatter output has header row matching column names
- Metadata goes to stderr, data goes to stdout (captured separately)
- Error messages for all EC-001 through EC-020 match expected format
- Exit codes: 0 for success, 1 for query errors, 2 for infrastructure errors

**Fixture pattern for OfflineDataFrameProvider tests**:
```python
@pytest.fixture
def mock_s3_loader(monkeypatch):
    """Replace load_project_dataframe with a dict of project_gid -> DataFrame."""
    frames = {
        "1143843662099250": pl.DataFrame({
            "gid": ["1", "2", "3"],
            "name": ["Offer A", "Offer B", "Offer C"],
            "section": ["ACTIVE", "INACTIVE", "ACTIVE"],
            "mrr": [1000.0, 0.0, 2500.0],
            "office_phone": ["+1111", "+2222", "+1111"],
        }),
        "1200653012566782": pl.DataFrame({
            "gid": ["b1", "b2"],
            "name": ["Biz A", "Biz B"],
            "office_phone": ["+1111", "+2222"],
            "booking_type": ["direct", "agency"],
        }),
    }
    def fake_loader(project_gid, *, bucket=None, region="us-east-1"):
        if project_gid not in frames:
            raise FileNotFoundError(f"No parquet files found under s3://bucket/dataframes/{project_gid}/sections/")
        return frames[project_gid]
    monkeypatch.setattr("autom8_asana.dataframes.offline.load_project_dataframe", fake_loader)
    return frames
```

### Phase 2 Tests

| Test File | Scope |
|-----------|-------|
| `test_cli_aggregate.py` | --agg flag parsing, group-by, having, multiple aggregations |
| `test_cli_join.py` | --join, --join-select, --join-on flag parsing, join metadata output |
| `test_aggregate_e2e.py` | Full aggregate pipeline through QueryEngine with mock S3 data |
| `test_join_e2e.py` | Full join pipeline with OfflineProjectRegistry resolution |

### Phase 3 Tests

| Test File | Scope |
|-----------|-------|
| `test_templates.py` | SavedQueryStore CRUD, YAML serialization, overwrite protection |
| `test_cli_timeline.py` | Timeline subcommand argument parsing, period validation |
| `test_cli_live_mode.py` | --live flag wires EntityQueryService instead of OfflineDataFrameProvider |

### Phase 4 Tests

| Test File | Scope |
|-----------|-------|
| `test_introspection_routes.py` | GET /v1/query/entities, /schema, /relations, /sections |
| `test_multi_hop_join.py` | Multi-hop join planner, MAX_JOIN_DEPTH > 1 |

---

## File Manifest

### Phase 1: CLI Foundation + Output + Discovery

| File | Action | Description |
|------|--------|-------------|
| `src/autom8_asana/query/__main__.py` | CREATE | CLI entry point with argparse subcommands |
| `src/autom8_asana/query/offline_provider.py` | CREATE | OfflineDataFrameProvider, NullClient, OfflineProjectRegistry |
| `src/autom8_asana/query/formatters.py` | CREATE | OutputFormatter protocol + 4 implementations |
| `tests/unit/query/test_offline_provider.py` | CREATE | Provider protocol compliance, caching, errors |
| `tests/unit/query/test_null_client.py` | CREATE | NullClient sentinel behavior |
| `tests/unit/query/test_offline_project_registry.py` | CREATE | Registry adapter delegation |
| `tests/unit/query/test_cli_parsers.py` | CREATE | Flag parsing (where, agg, where-json) |
| `tests/unit/query/test_formatters.py` | CREATE | Formatter output correctness |
| `tests/unit/query/test_cli_e2e.py` | CREATE | End-to-end CLI subprocess tests |

### Phase 2: Aggregation + Joins

| File | Action | Description |
|------|--------|-------------|
| `src/autom8_asana/query/__main__.py` | MODIFY | Add aggregate subcommand handler |
| `tests/unit/query/test_cli_aggregate.py` | CREATE | Aggregate CLI tests |
| `tests/unit/query/test_cli_join.py` | CREATE | Join CLI tests |

### Phase 3: Temporal + Saved Queries + Live Mode

| File | Action | Description |
|------|--------|-------------|
| `src/autom8_asana/query/__main__.py` | MODIFY | Add timeline, run, list-queries, --save, --live |
| `src/autom8_asana/query/templates.py` | CREATE | SavedQueryStore with YAML persistence |
| `tests/unit/query/test_templates.py` | CREATE | Template CRUD, YAML round-trip |
| `tests/unit/query/test_cli_timeline.py` | CREATE | Timeline subcommand tests |
| `tests/unit/query/test_cli_live_mode.py` | CREATE | Live mode wiring tests |

### Phase 4: API Introspection + Multi-Hop Joins

| File | Action | Description |
|------|--------|-------------|
| `src/autom8_asana/api/routes/introspection.py` | CREATE | GET endpoints for entity/schema/relation/section discovery |
| `src/autom8_asana/query/join.py` | MODIFY | Lift MAX_JOIN_DEPTH, add join planner |
| `src/autom8_asana/query/hierarchy.py` | MODIFY | Add cardinality annotations to EntityRelationship |
| `tests/unit/query/test_introspection_routes.py` | CREATE | API introspection tests |
| `tests/unit/query/test_multi_hop_join.py` | CREATE | Multi-hop join planner tests |

---

## Open Items

None. All design decisions resolved. Implementation can proceed phase-by-phase.

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/AUTOM8_QUERY/PRD.md` | Read-confirmed |
| TDD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/AUTOM8_QUERY/TDD.md` | Self (this document) |
| QueryEngine | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/engine.py` | Read-confirmed |
| DataFrameProvider protocol | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/protocols/dataframe_provider.py` | Read-confirmed |
| RowsRequest / AggregateRequest | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/models.py` | Read-confirmed |
| JoinSpec / execute_join | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/join.py` | Read-confirmed |
| EntityRelationship / hierarchy | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/hierarchy.py` | Read-confirmed |
| EntityRegistry / get_registry | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/entity_registry.py` | Read-confirmed |
| SchemaRegistry | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/dataframes/models/registry.py` | Read-confirmed |
| load_project_dataframe | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/dataframes/offline.py` | Read-confirmed |
| SectionClassifier / CLASSIFIERS | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/activity.py` | Read-confirmed |
| SectionTimeline / OfferTimelineEntry | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/section_timeline.py` | Read-confirmed |
| QueryEngine errors | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/errors.py` | Read-confirmed |
| QueryLimits / guards | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/guards.py` | Read-confirmed |
| Metrics CLI (reference) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/metrics/__main__.py` | Read-confirmed |
| API routes (query) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/query.py` | Read-confirmed |
| EntityProjectRegistry | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/resolver.py` | Read-confirmed |
| FreshnessInfo | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/dataframe_cache.py` | Read-confirmed |
| DataFrameSchema / ColumnDef | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/dataframes/models/schema.py` | Read-confirmed |
