---
domain: feat/query-cli
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_query_cli.py"
  - "./src/autom8_asana/query/__main__.py"
  - "./pyproject.toml"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.90
format_version: "1.0"
---

# autom8-query CLI Tool

## Purpose and Design Rationale

Interactive, offline-first CLI for the `QueryEngine` operating over cached Asana entity
DataFrames. Three design constraints shape the architecture:

**Settings guard bypass (G-01)**: `autom8_asana` requires `AUTOM8Y_DATA_URL` and
`ASANA_WORKSPACE_GID` at import time. The CLI sets dummy values (`http://offline-cli.local`
and `offline`) via `os.environ.setdefault()` before importing. This is why the entry point
(`src/autom8_query_cli.py`) lives **outside** the package — if it lived inside, the package
`__init__.py` would fire before the env-var guard.

**Import-time log noise (G-02)**: `autom8y_log` reads `LOG_LEVEL` during its auto-configure
step. The CLI sets `LOG_LEVEL=ERROR` before imports so stdout data output isn't contaminated
by structlog JSON from `HolderFactory`, schema warnings, etc. `--verbose` or `--quiet` flags
override post-parse via `_configure_logging()`.

**DI stack avoidance (ADR-AQ-007)**: Rather than wiring `EntityQueryService`'s full DI stack
(UniversalResolutionStrategy, DataFrameCache, AsanaClient, EntityProjectRegistry), offline mode
uses `OfflineDataFrameProvider` (reads Polars parquets from local S3 cache) and `NullClient`
(no-op). `--live` flag routes through the existing HTTP API surface instead, keeping the CLI thin.

**SCAR-LOG-001 migration (commit `20ef7952`)**: `_configure_logging()` in `query/__main__.py`
was migrated to the `autom8y_log` SDK (`LogConfig` + `configure_logging` with
`intercept_stdlib=True`). This migration is complete at `8980bcd7`. The `autom8y_core` lower
bound was lifted to `>=4.2.0` (commit `f6864435`), which affects live-mode `TokenManager`.

## Conceptual Model

### Two CLI Surfaces

**Surface 1 — `autom8-query` standalone** (`src/autom8_query_cli.py`, TID251-exempt):
- Console scripts entry point registered in `pyproject.toml`: `autom8-query = "autom8_query_cli:main"`
- Sets G-01 + G-02 env vars before any package import
- Delegates immediately to `autom8_asana.query.__main__:main`
- Use this for clean stdout output when piping to jq/csv

**Surface 2 — `python -m autom8_asana.query`** (`src/autom8_asana/query/__main__.py`, 1724 lines):
- Full CLI dispatcher: all 10 subcommands, argument parser, logging config, live-mode HTTP, predicate parsing
- Can also be invoked as `python -m autom8_asana.query.cli` via the `cli.py` shim, but with the caveat that `autom8_asana/__init__.py` has already fired before the shim runs, so import-time log noise cannot be suppressed

### Operation Types

**Query**: `rows` (filtered retrieval with `--where`, `--classification`, `--section`,
`--join`/`--enrich`), `aggregate` (`--group-by`, `--agg`, `--having`),
`timeline` (section transition history from `SectionTimeline` parquets).

**Introspection**: `entities`, `fields`, `relations`, `sections`, `data-sources`.

**Saved queries**: `run <name|path>` (load YAML/JSON template with CLI override support),
`list-queries`, `--save <name>` (persist executed rows/aggregate query as YAML).

### Data Source Modes

**Offline (default)**: `OfflineDataFrameProvider` reads Polars parquets. No live credentials
needed. `NullClient` satisfies DI. `OfflineProjectRegistry` provides project GIDs.

**Live (`--live`)**: HTTP POST to `AUTOM8Y_DATA_URL` at `/v1/query/{entity_type}/rows` or
`/aggregate`. Auth via `autom8y_core.TokenManager` — reads `SERVICE_CLIENT_ID` and
`SERVICE_CLIENT_SECRET` from env (ServiceAccount convention) to acquire S2S JWT. Hardcoded
30-second timeout. Only `rows` and `aggregate` subcommands support `--live`.

### Join Model

**Entity join** (`--join-source=entity`, default): Asana-to-Asana via `EntityRegistry`
relationships. Format: `--join entity_type:col1,col2`.

**Data-service join** (`--join-source=data-service` or `--enrich`): Asana-to-autom8y-data via
`DataServiceClient`. `--enrich FACTORY:col1,col2` is shorthand. `--join-period` (T7/T30/LIFETIME,
default LIFETIME). Multiple `--join` flags accepted but only first is used (non-fatal warning
to stderr).

### Predicate Model

`--where 'field op value'` (AND-combined, multiple flags). `--where-json '{"or": [...]}` for
complex trees. Type coercion: int > float > bool > str. Strings starting with `+` preserved as
strings (phone number guard). `build_predicate()` combines both sources — multiple `--where`
flags wrap into `AndGroup`, `--where-json` appended; combined into outer `AndGroup` if both
present.

### Output Model

Metadata (row count, group count, query_ms, freshness, data_age, join stats) to **stderr**
(AC-4.7). Data to **stdout**. `--output <file>` redirects data only to file. Formatters:
`table` (Polars repr, default), `json`, `csv`, `jsonl`. `--no-truncate` disables table column
truncation.

### Saved Query Resolution

`run <arg>` first tries `Path(arg).exists()` for direct file path. On miss, calls
`find_saved_query(arg)` which scans `./queries/` then `~/.autom8/queries/`. CLI flags
(`--where`, `--classification`, `--select`, `--limit`, `--offset`, `--order-by`, `--order-dir`,
`--format`) override saved values when explicitly provided. `--save` after `rows`/`aggregate`
persists to `~/.autom8/queries/<name>.yaml`; raises `FileExistsError` on collision (warning
to stderr, no override).

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_query_cli.py` | Standalone entry point (outside package). Sets G-01/G-02 env vars, delegates to `query.__main__:main`. TID251-exempt (direct httpx in live-mode functions). 39 lines. |
| `src/autom8_asana/query/__main__.py` | Full CLI (1724 lines): all 10 subcommand handlers, `build_parser()`, `_configure_logging()` (autom8y_log SDK, SCAR-LOG-001 migrated), live-mode HTTP (`execute_live_rows`, `execute_live_aggregate`), predicate/agg/join parsing helpers |
| `src/autom8_asana/query/cli.py` | In-package shim (24 lines) for `python -m autom8_asana.query.cli`. Delegates to `__main__.main`. Cannot suppress import-time log noise. |
| `src/autom8_asana/query/saved.py` | `SavedQuery` Pydantic model, `load_saved_query()`, `save_query()`, `find_saved_query()`. Searches `./queries/` then `~/.autom8/queries/` |
| `src/autom8_asana/query/formatters.py` | `OutputFormatter` protocol + `TableFormatter`/`JSONFormatter`/`CSVFormatter`/`JSONLFormatter`. `FORMATTERS` dict keyed by format name string. |
| `src/autom8_asana/query/offline_provider.py` | `OfflineDataFrameProvider`, `NullClient`, `OfflineProjectRegistry` — DI shims for offline mode |
| `src/autom8_asana/query/temporal.py` | `TemporalFilter`, `parse_date_or_relative()` — used by `timeline` subcommand |
| `src/autom8_asana/query/timeline_provider.py` | `TimelineStore` — loads cached `SectionTimeline` parquets for `timeline` subcommand |
| `src/autom8_asana/query/introspection.py` | `list_entities()`, `list_fields()`, `list_relations()`, `list_sections()` — used by introspection subcommands |
| `src/autom8_asana/query/data_service_entities.py` | `list_data_service_entities()` — used by `data-sources` subcommand |

**pyproject.toml entry point (line 93)**: `autom8-query = "autom8_query_cli:main"` — canonical
invocation path. Package src path registered at line 96: `"src/autom8_query_cli.py"` is
explicitly included alongside the `src/autom8_asana` package.

**Exit codes** (NFR-006): 0 (success), 1 (query error / CLIError), 2 (infrastructure error /
ConnectError / ValueError / OSError).

**Handler dispatch table** (in `main()`):
```
rows → handle_rows
aggregate → handle_aggregate
entities → handle_entities
fields → handle_fields
relations → handle_relations
sections → handle_sections
data-sources → handle_data_sources
timeline → handle_timeline
list-queries → handle_list_queries
run → handle_run
```

**autom8y_core lower bound**: `>=4.2.0,<5.0.0` (lifted from `>=4.0.0` at commit `f6864435`).
This affects `TokenManager` + `Config` availability for live-mode auth.

## Boundaries and Failure Modes

### Does Not

- Warm the DataFrame cache (reads existing parquets only; `OfflineDataFrameProvider` is read-only)
- Write to Asana (NullClient no-op)
- Support multi-join (only first `--join` used; non-fatal warning to stderr)
- Support `--live` for `timeline`, `run`, `entities`, `fields`, `relations`, `sections`,
  `data-sources`, `list-queries` — only `rows` and `aggregate` have `--live` wired
- Override saved query files on collision (`FileExistsError`, warning to stderr)
- Support `--live` + data-service joins (data-service joins via `DataServiceClient` are
  offline-mode only; `_create_data_client_if_needed()` never invoked in live path)

### Known Failure Modes

- **Timeline with no cached parquet**: `CLIError("future release will add --compute flag")` —
  `TimelineStore.load()` returns `None`; `handle_timeline()` raises with expected cache path
- **Dummy URL accidentally hit**: `AUTOM8Y_DATA_URL=http://offline-cli.local` used as offline
  sentinel. Confusing `ConnectError` if live HTTP path somehow hits it.
- **`--live` 30-second hardcoded timeout**: No CLI flag to adjust (`timeout=30.0` in
  `execute_live_rows` and `execute_live_aggregate`, `__main__.py:289,350`)
- **`python -m autom8_asana.query.cli`**: Cannot suppress import-time log noise (noted in
  `cli.py` docstring and `__main__.py:1678-1679` comment)
- **`--join` silently drops entries beyond first**: Non-fatal `print(..., file=sys.stderr)`
  at `__main__.py:543-546`; only `join_list[0]` used
- **Metrics CLI under-count (SCAR candidate)**: `autom8-query` parquet loading silently drops
  sections — ~6 in parquet vs ~22 expected. Root cause unresolved (4 open questions: bucket
  mapping, freshness SLA, section-coverage gap, staleness-surface decision). See
  `.know/scar-tissue.md` "Metrics CLI Under-count" and `metrics/compute.py`,
  `dataframes/offline.py`.
- **`--enrich` + `--join` mutually exclusive**: `CLIError` raised; not silently ignored
- **`run` subcommand offline-only**: `handle_run` always uses `OfflineDataFrameProvider` —
  no `--live` flag on `run` subcommand

### Interaction Points / Boundaries

- **`query/engine.py`** (P1-C-04 frozen): `execute_rows` steps 6-9 and aggregate logic frozen.
  `__main__.py` calls `asyncio.run(engine.execute_rows(...))` and
  `asyncio.run(engine.execute_aggregate(...))`.
- **`query/compiler.py`** (P1-C-04 frozen): `OPERATOR_MATRIX`, `_compile_node`. Imported
  lazily in `__main__.py:513,669`.
- **`autom8y_core.TokenManager`**: Live-mode auth. `Config.from_env()` reads
  `SERVICE_CLIENT_ID` and `SERVICE_CLIENT_SECRET`. `TokenAcquisitionError` maps to
  `CLIError(exit_code=2)`.
- **`DataServiceClient`** (`clients/data/client.py`): Created only for data-service joins
  (`_create_data_client_if_needed()`). Falls back to `AUTOM8Y_DATA_API_KEY` if
  `ServiceTokenAuthProvider` init fails.
- **`EntityRegistry`** (`core/entity_registry.py`): `resolve_entity_type()` validates entity
  type and returns project GID. `CLIError` if entity type unknown or has no project GID.
- **`models.py` discriminator (SCAR-DISCRIMINATOR-001)**: `_predicate_discriminator` at
  `query/models.py:97-112` only handles dict inputs correctly; model-instance `NotGroup`
  construction fails Pydantic validation. CLI works around this via dict-passing pattern in
  `build_predicate()` — never constructs model instances directly. Unguarded at `8980bcd7`.

### Configuration Boundaries

| Env Var | Effect | Default When CLI Sets It |
|---------|--------|--------------------------|
| `AUTOM8Y_DATA_URL` | Base URL for live API | `http://offline-cli.local` (G-01 offline sentinel) |
| `ASANA_WORKSPACE_GID` | Required by settings guard | `"offline"` (G-01 bypass) |
| `LOG_LEVEL` | Controls structlog level at import | `"ERROR"` (G-02 noise suppression) |
| `SERVICE_CLIENT_ID` | Live mode JWT auth (required) | Not set by CLI |
| `SERVICE_CLIENT_SECRET` | Live mode JWT auth (required) | Not set by CLI |
| `AUTOM8Y_DATA_API_KEY` | Fallback auth for data-service joins | Not set by CLI |

```metadata
domain: feat/query-cli
source_hash: "8980bcd7"
generated_at: "2026-05-08T00:00Z"
confidence: 0.90
criteria_grades:
  purpose_and_design_rationale:
    grade: A
    pct: 92
    weight: 0.30
    notes: >
      G-01/G-02 guards clearly documented with rationale. ADR-AQ-007 referenced for
      DI stack avoidance decision. SCAR-LOG-001 migration status documented with commit
      reference. autom8y-core lower-bound lift documented. Minor gap: no decision record
      ADR-AQ-007 was read directly (architecture seed reference only).
  conceptual_model:
    grade: A
    pct: 92
    weight: 0.25
    notes: >
      Both CLI surfaces distinguished. All operation types, data modes, join model,
      predicate model, output model, saved query resolution documented with terminology.
      Inter-feature relationships (engine, compiler, DataServiceClient, EntityRegistry)
      mapped with direction.
  implementation_map:
    grade: A
    pct: 93
    weight: 0.25
    notes: >
      Every implementing file listed with role and purpose. 1724-line count corrected
      from prior 1759 (lines removed in SCAR-LOG-001 migration). Handler dispatch table
      explicit. pyproject.toml line references provided. P1-C-04 frozen module status
      noted. Previously unknown files (offline_provider, temporal, timeline_provider,
      introspection, data_service_entities) now surfaced.
  boundaries_and_failure_modes:
    grade: A
    pct: 91
    weight: 0.20
    notes: >
      Explicit "Does Not" list with 7 items. Known failure modes catalogued with line
      references. Interaction points mapped. Configuration boundaries tabulated.
      SCAR-DISCRIMINATOR-001 boundary documented. Metrics CLI under-count scar referenced.
      Minor gap: offline_provider.py internals not read; S3 parquet path conventions
      unknown.
overall_grade: A
overall_pct: 92
notes: >
  Refresh from 2026-04-01 (source_hash c213958) to 2026-05-08 (source_hash 8980bcd7).
  Key deltas captured: SCAR-LOG-001 migration complete in _configure_logging()
  (autom8y_log LogConfig + configure_logging + intercept_stdlib=True);
  autom8y-core lower bound lifted to >=4.2.0; __main__.py now 1724 lines (was ~1759);
  live-mode auth corrected to SERVICE_CLIENT_ID + SERVICE_CLIENT_SECRET via
  autom8y_core.Config (prior file incorrectly referenced SERVICE_API_KEY);
  previously unknown implementation files now listed; SCAR-CONSUMER-GATE-001 and
  SCAR-ARTIPACKED-001 are CI-layer scars not affecting CLI behavior directly.
  Confidence 0.90 (was 0.88): offline_provider.py and timeline_provider.py internals
  not read, S3 parquet naming conventions unknown.
```
