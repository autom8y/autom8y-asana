---
domain: feat/query-cli
generated_at: "2026-04-01T18:15:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_query_cli.py"
  - "./src/autom8_asana/query/__main__.py"
  - "./src/autom8_asana/query/cli.py"
  - "./src/autom8_asana/query/saved.py"
  - "./src/autom8_asana/query/formatters.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.88
format_version: "1.0"
---

# autom8-query CLI Tool

## Purpose and Design Rationale

Interactive, offline-first CLI for the `QueryEngine` operating over cached Asana entity DataFrames. Three design constraints shape the architecture:

**Settings guard bypass**: `autom8_asana` requires `AUTOM8Y_DATA_URL` and `ASANA_WORKSPACE_GID` at import. The CLI sets dummy values before importing. This is why the entry point (`src/autom8_query_cli.py`) lives **outside** the package.

**Import-time log noise**: `LOG_LEVEL=ERROR` set before imports so stdout data output isn't contaminated. Loggers for autom8_asana, autom8y_log, boto3, botocore, httpx, httpcore all silenced unless `--verbose`.

**DI stack avoidance**: Uses `OfflineDataFrameProvider` (reads parquets from local S3 cache) and `NullClient` (no-op). `--live` flag routes to HTTP API instead.

## Conceptual Model

### Operation Types

**Query**: `rows` (filtered retrieval with --where, --classification, --section, --join/--enrich), `aggregate` (--group-by, --agg, --having), `timeline` (section transition history).

**Introspection**: `entities`, `fields`, `relations`, `sections`, `data-sources`.

**Saved queries**: `run <name>` (load YAML/JSON template), `list-queries`, `--save <name>` (persist executed query).

### Data Source Modes

**Offline (default)**: `OfflineDataFrameProvider` reads Polars parquets. No live credentials needed.

**Live (`--live`)**: HTTP calls to API at `AUTOM8Y_DATA_URL` with S2S JWT via `TokenManager`. Requires `SERVICE_API_KEY`.

### Join Model

Entity join (`--join-source=entity`, default): Asana-to-Asana via EntityRegistry relationships. Data-service join (`--join-source=data-service` or `--enrich`): Asana-to-autom8y-data via `DataServiceClient`. `--join-period` (T7/T30/LIFETIME).

### Predicate Model

`--where 'field op value'` (AND-combined). `--where-json '{"or": [...]}'` for complex trees. Type coercion: int > float > bool > str. Strings starting with `+` preserved (phone numbers).

### Output Model

Metadata to **stderr**, data to **stdout** (AC-4.7). `--output <file>` redirects data only. Formatters: table (Polars repr), json, csv, jsonl.

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_query_cli.py` | Standalone entry point (outside package). Sets env vars, delegates to `query.__main__:main` |
| `src/autom8_asana/query/__main__.py` | Full CLI (~1759 lines): all subcommand handlers, argument parser, logging config, live-mode HTTP, predicate parsing |
| `src/autom8_asana/query/cli.py` | In-package shim (24 lines) for `python -m autom8_asana.query.cli` |
| `src/autom8_asana/query/saved.py` | `SavedQuery` Pydantic model, `load_saved_query()`, `save_query()`, `find_saved_query()`. Searches `./queries/` then `~/.autom8/queries/` |
| `src/autom8_asana/query/formatters.py` | `OutputFormatter` protocol + Table/JSON/CSV/JSONL implementations. `FORMATTERS` dict |

**pyproject.toml**: `autom8-query = "autom8_query_cli:main"` -- canonical invocation path.

**Exit codes**: 0 (success), 1 (query error), 2 (infrastructure error).

## Boundaries and Failure Modes

### Does Not

- Warm the DataFrame cache (reads existing parquets only)
- Write to Asana (NullClient)
- Support multi-join (warning emitted, only first used)
- Support `--live` + aggregate + cross-service joins
- Override save files (FileExistsError on collision, warning to stderr)

### Known Failure Modes

- **Timeline with no cached parquet**: CLIError ("future release will add --compute flag")
- **Dummy URL contacted**: `http://offline-cli.local` used as AUTOM8Y_DATA_URL; confusing ConnectError if accidentally hit
- **`--live` 30-second hardcoded timeout**: No CLI flag to adjust
- **`python -m autom8_asana.query.cli`**: Cannot suppress import-time log noise (caveat documented in shim)
- **`--join` silently drops entries beyond first**: Non-fatal warning to stderr

## Knowledge Gaps

1. `offline_provider.py` (OfflineDataFrameProvider, NullClient) internals not read.
2. `temporal.py` and `timeline_provider.py` (timeline filter semantics, parquet conventions) not read.
3. `introspection.py` function contracts not read.
4. `data_service_entities.py` (data-sources subcommand) not read.
5. `ServiceTokenAuthProvider` initialization requirements not read.
