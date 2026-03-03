# PRD: AUTOM8_QUERY -- CLI and Offline Query Surface for QueryEngine

## Overview

Expose the existing QueryEngine infrastructure through a composable CLI (`python -m autom8_asana.query`) and an offline DataFrameProvider, enabling ad-hoc business queries against S3-cached parquet data without requiring the running service stack. The engine already handles predicates, classification, joins, aggregation, and pagination -- the gap is a user-facing surface and the offline data bridge.

## Impact Assessment

```yaml
impact: high
impact_categories: [api_contract]
```

**Rationale**: Extends the public API surface with new introspection endpoints (entity/field/relation discovery). Introduces a new DataFrameProvider implementation (OfflineDataFrameProvider) that bridges sync S3 access to the async protocol. No schema changes, no auth changes, no cross-service dependencies beyond the existing S3 bucket.

## Background

Asana's native search operates on tasks. Our business model -- offers, contacts, units, businesses -- spans entity types with classification (active/activating/inactive/ignored), temporal state tracking (SectionTimeline), and hierarchical relationships (Business > Unit > Offer) that Asana cannot query.

Today, answering questions like "show me active dental offers with MRR > $5k and their business booking type" requires writing bespoke scripts. The QueryEngine (`query/engine.py`) already handles this via `execute_rows()` and `execute_aggregate()`, but these are only accessible through the authenticated HTTP API (`POST /v1/query/{entity_type}/rows` and `/aggregate`). There is no local execution path.

The metrics CLI (`python -m autom8_asana.metrics`) proved the pattern: S3 offline loader + CLI surface = immediate value. The query initiative generalizes this pattern across all entity types and query capabilities.

**Primary users**:
- **Founder**: Ad-hoc business questions (pipeline analysis, MRR reporting, cross-entity lookups)
- **Engineering**: Data investigation, debugging, entity relationship exploration

**Why now**: Infrastructure is 80%+ built. QueryEngine, PredicateCompiler, join resolution, classification, aggregation -- all production-tested. The missing piece is the last-mile UX: CLI flags that map to RowsRequest/AggregateRequest models.

## User Stories

### US-1: Basic Row Query via CLI
**As a** founder, **I want to** query entity rows from the command line with filters, **so that** I can answer ad-hoc business questions without writing code.

**Acceptance Criteria**:
- AC-1.1: `python -m autom8_asana.query rows offer --where 'section eq ACTIVE'` returns filtered rows
- AC-1.2: `--classification active` filters to sections classified as active (via SectionClassifier)
- AC-1.3: `--select gid,name,mrr,office_phone` limits output columns
- AC-1.4: `--limit 50 --offset 100` controls pagination
- AC-1.5: `--order-by mrr --order-dir desc` sorts results
- AC-1.6: Multiple `--where` flags combine with AND semantics
- AC-1.7: Complex predicates supported via `--where-json '{"or": [...]}'` for non-CLI-expressible trees
- AC-1.8: Default output is a human-readable table with column headers

### US-2: Aggregate Query via CLI
**As a** founder, **I want to** aggregate entity data with grouping and filters, **so that** I can compute business metrics without spreadsheets.

**Acceptance Criteria**:
- AC-2.1: `python -m autom8_asana.query aggregate offer --group-by section --agg 'sum:mrr'` produces grouped results
- AC-2.2: Multiple `--agg` flags supported: `--agg 'count:gid' --agg 'mean:mrr'`
- AC-2.3: `--having 'sum_mrr gt 1000'` filters post-aggregation groups
- AC-2.4: `--where` and `--classification` filter pre-aggregation (same as rows)
- AC-2.5: Agg function aliases generated automatically (`sum_mrr`, `count_gid`) or specified via `--agg 'sum:mrr:total_revenue'`

### US-3: Cross-Entity Join via CLI
**As a** founder, **I want to** enrich query results with columns from related entities, **so that** I can answer cross-entity questions in a single command.

**Acceptance Criteria**:
- AC-3.1: `python -m autom8_asana.query rows offer --join business --join-select booking_type,stripe_id` appends business columns
- AC-3.2: Join key auto-resolved from ENTITY_RELATIONSHIPS (e.g., offer<->business via office_phone)
- AC-3.3: `--join-on office_phone` overrides default join key
- AC-3.4: Join metadata displayed: matched count, unmatched count, join key used
- AC-3.5: Joined columns prefixed with entity type (e.g., `business_booking_type`)

### US-4: Output Formatting
**As an** engineer, **I want to** control output format, **so that** I can pipe results to other tools or export for analysis.

**Acceptance Criteria**:
- AC-4.1: `--format table` (default): Human-readable aligned table with headers
- AC-4.2: `--format json`: JSON array of row objects, suitable for `jq` piping
- AC-4.3: `--format csv`: CSV with headers, suitable for spreadsheet import
- AC-4.4: `--format jsonl`: One JSON object per line (for streaming/logging)
- AC-4.5: `--output /path/to/file.csv` writes to file instead of stdout
- AC-4.6: Table format truncates long values (>40 chars) with ellipsis; `--no-truncate` disables
- AC-4.7: Metadata line printed to stderr (total count, query time, data freshness) so it does not interfere with stdout piping

### US-5: Entity and Field Discovery
**As an** engineer, **I want to** discover available entity types, fields, and relationships, **so that** I can construct queries without reading source code.

**Acceptance Criteria**:
- AC-5.1: `python -m autom8_asana.query entities` lists all queryable entity types with project GIDs
- AC-5.2: `python -m autom8_asana.query fields offer` lists all columns with dtype, nullable, description
- AC-5.3: `python -m autom8_asana.query relations offer` lists joinable entity types with default join keys
- AC-5.4: `python -m autom8_asana.query sections offer` lists section names with classification (active/activating/inactive/ignored)
- AC-5.5: Discovery output respects `--format` flag (table/json)

### US-6: Offline Data Source (S3 Cache)
**As a** user, **I want** queries to run against cached S3 data by default, with the option to force live API access, **so that** I can query without running the service stack.

**Acceptance Criteria**:
- AC-6.1: Default behavior loads from S3 parquets via `load_project_dataframe()` (no service stack required)
- AC-6.2: `--live` flag routes through EntityQueryService with AsanaClient (requires credentials + service)
- AC-6.3: Data freshness metadata displayed (last modified timestamp from S3 objects)
- AC-6.4: Clear error message when S3 bucket not configured (ASANA_CACHE_S3_BUCKET env var)
- AC-6.5: Clear error message when no parquet files exist for requested entity type
- AC-6.6: OfflineDataFrameProvider implements DataFrameProvider protocol, bridging sync S3 loader to async interface

### US-7: Temporal Queries (Section Transitions)
**As a** founder, **I want to** query offer section transition history, **so that** I can analyze how long offers spend in each pipeline stage.

**Acceptance Criteria**:
- AC-7.1: `python -m autom8_asana.query timeline offer --period 2026-01-01:2026-01-31` returns per-offer active/billable days
- AC-7.2: `--classification active` filters to offers currently classified as active
- AC-7.3: Output includes offer_gid, office_phone, offer_id, active_section_days, billable_section_days, current_section
- AC-7.4: Timeline data sourced from SectionTimeline infrastructure (load_stories_incremental, always live)
- AC-7.5: `--format` flag respected for output formatting

### US-8: Saved Query Templates
**As a** user, **I want to** save and reuse common queries as named templates, **so that** I don't have to re-type complex query parameters.

**Acceptance Criteria**:
- AC-8.1: `--save my_query` persists current query parameters to `~/.autom8/queries/my_query.yaml`
- AC-8.2: `python -m autom8_asana.query run my_query` executes a saved query
- AC-8.3: `python -m autom8_asana.query list-queries` lists saved query names with descriptions
- AC-8.4: Saved query YAML includes entity_type, subcommand (rows/aggregate), all parameters
- AC-8.5: CLI flags override saved query parameters (explicit flag > saved value)
- AC-8.6: `--save` with existing name prompts confirmation (overwrite protection)

### US-9: API Introspection Endpoints
**As a** service consumer, **I want to** discover available entity types, fields, and relationships via HTTP, **so that** I can build dynamic query UIs.

**Acceptance Criteria**:
- AC-9.1: `GET /v1/query/entities` returns list of queryable entity types with metadata
- AC-9.2: `GET /v1/query/{entity_type}/schema` returns column definitions (name, dtype, nullable, description)
- AC-9.3: `GET /v1/query/{entity_type}/relations` returns joinable types with default join keys and cardinality hints
- AC-9.4: `GET /v1/query/{entity_type}/sections` returns section names with classification labels
- AC-9.5: Introspection endpoints require service token authentication (same as existing query routes)

## Functional Requirements

### Must Have (P0)

- **FR-001**: CLI entry point at `python -m autom8_asana.query` with subcommands: `rows`, `aggregate`, `entities`, `fields`, `relations`, `sections`
  - _Source_: US-1, US-2, US-5
  - _Asset_: New module `query/__main__.py`

- **FR-002**: OfflineDataFrameProvider implementing DataFrameProvider protocol
  - _Source_: US-6
  - _Asset_: New class in `query/offline_provider.py` (or extend `dataframes/offline.py`)
  - _Behavior_: Wraps sync `load_project_dataframe()` in async interface. Resolves entity_type to project_gid via EntityRegistry. Implements `last_freshness_info` property.

- **FR-003**: Row query CLI with flag-to-RowsRequest mapping
  - _Source_: US-1
  - _Asset_: `query/__main__.py` rows subcommand
  - _Behavior_: Maps CLI flags to RowsRequest fields. `--where 'field op value'` parsed into Comparison nodes. Multiple `--where` flags ANDed. `--where-json` for complex trees.

- **FR-004**: Aggregate query CLI with flag-to-AggregateRequest mapping
  - _Source_: US-2
  - _Asset_: `query/__main__.py` aggregate subcommand
  - _Behavior_: Maps `--group-by`, `--agg`, `--having` to AggregateRequest fields. Agg spec format: `function:column[:alias]`.

- **FR-005**: Output formatting layer supporting table, JSON, CSV, JSONL
  - _Source_: US-4
  - _Asset_: New module `query/formatters.py`
  - _Behavior_: Accepts polars DataFrame or list[dict], format flag, optional file path. Table uses polars native pretty-print or tabulate. JSON/CSV/JSONL use polars export methods.

- **FR-006**: Entity/field/relation/section discovery subcommands
  - _Source_: US-5
  - _Asset_: `query/__main__.py` discovery subcommands
  - _Behavior_: `entities` reads from EntityRegistry. `fields` reads from SchemaRegistry. `relations` reads from ENTITY_RELATIONSHIPS. `sections` reads from CLASSIFIERS.

- **FR-007**: Cross-entity join CLI flags
  - _Source_: US-3
  - _Asset_: `query/__main__.py` join flags on rows subcommand
  - _Behavior_: `--join`, `--join-select`, `--join-on` map to JoinSpec in RowsRequest.

- **FR-008**: Metadata output to stderr
  - _Source_: US-4 (AC-4.7)
  - _Behavior_: Print total_count, returned_count, query_ms, freshness info to stderr. Data goes to stdout. Enables clean piping: `query rows offer --format json | jq '.[] | .mrr'`.

### Should Have (P1)

- **FR-009**: Temporal query subcommand (`timeline`)
  - _Source_: US-7
  - _Asset_: `query/__main__.py` timeline subcommand
  - _Behavior_: `--period start:end` required. Uses SectionTimeline builder (which calls `load_stories_incremental()` -- always live). Returns OfferTimelineEntry data via output formatter.
  - _Constraint_: Requires live API access (SectionTimeline is story-based, not cached in parquets). Must document this clearly.

- **FR-010**: Saved query templates
  - _Source_: US-8
  - _Asset_: `query/templates.py`, storage at `~/.autom8/queries/`
  - _Behavior_: YAML serialization of query parameters. Load + merge with CLI overrides. List command for discovery.

- **FR-011**: `--live` flag for live API data source
  - _Source_: US-6 (AC-6.2)
  - _Behavior_: When `--live` is passed, instantiate EntityQueryService as DataFrameProvider instead of OfflineDataFrameProvider. Requires ASANA_SERVICE_KEY or PAT credentials.

### Could Have (P2)

- **FR-012**: API introspection endpoints
  - _Source_: US-9
  - _Asset_: New routes in `api/routes/query.py` (or separate `api/routes/introspection.py`)
  - _Behavior_: GET endpoints for entity list, schema, relations, sections. S2S JWT auth required.

- **FR-013**: Multi-hop joins (depth > 1)
  - _Source_: Spike gap #3
  - _Behavior_: Allow `--join unit --join business` (offer -> unit -> business via two hops). Currently blocked by MAX_JOIN_DEPTH=1 in `query/join.py`. Requires join planner that chains relationships.
  - _Constraint_: Increases result cardinality. Must validate intermediate join keys exist.

- **FR-014**: Cardinality annotations on relationships
  - _Source_: Spike gap #8
  - _Behavior_: Annotate EntityRelationship with cardinality (1:1, 1:N, N:1). Display in `relations` discovery. Inform join strategy (dedup vs. fan-out warning).

- **FR-015**: Predicate-level temporal filters
  - _Source_: Spike gap #4
  - _Behavior_: `--where 'active_days_in_period(2026-01-01,2026-01-31) gt 15'` as a virtual predicate that evaluates against SectionTimeline data joined to DataFrame rows.

## Non-Functional Requirements

- **NFR-001**: Query Latency (Offline)
  - Row queries against S3 parquets: < 3 seconds for 20k-row entity types on first load, < 500ms on subsequent (OS page cache warm)
  - Aggregation queries: < 2 seconds for any single-entity aggregation
  - _Measurement_: query_ms in response metadata, logged to stderr

- **NFR-002**: Query Latency (Live)
  - Same as existing API endpoint latency targets (already instrumented via query_ms)

- **NFR-003**: Memory
  - Peak memory for single-entity query: < 500MB (20k rows * ~50 columns)
  - Cross-entity join: < 1GB (two entity types loaded simultaneously)
  - _Rationale_: S3 parquets for largest entity (offer) are ~3MB compressed. Polars is columnar and memory-efficient.

- **NFR-004**: Error Messages
  - All errors must include actionable guidance (e.g., "Unknown entity type 'offr'. Available: business, contact, offer, unit")
  - S3 access errors must suggest checking ASANA_CACHE_S3_BUCKET env var
  - Unknown fields must list available fields

- **NFR-005**: CLI Help
  - Every subcommand must have `--help` with usage examples
  - Main `--help` must list all subcommands with one-line descriptions

- **NFR-006**: Exit Codes
  - 0: Success
  - 1: Query error (unknown entity, unknown field, invalid predicate, etc.)
  - 2: Infrastructure error (S3 unreachable, credentials missing, etc.)

- **NFR-007**: No Service Dependency (Offline Mode)
  - Default mode must work with only: AWS credentials (for S3 access), ASANA_CACHE_S3_BUCKET env var
  - No running web service, no ASANA_SERVICE_KEY, no AsanaClient required

## Edge Cases

| ID | Case | Expected Behavior |
|----|------|------------------|
| EC-001 | Entity type not in EntityRegistry | Exit 1 with "Unknown entity type '{name}'. Available: {sorted list}" |
| EC-002 | Field not in SchemaRegistry for entity | Exit 1 with "Unknown field '{name}' for {entity_type}. Available: {sorted list}" |
| EC-003 | No S3 parquets for entity type | Exit 1 with "No cached data for {entity_type}. Run sync pipeline or use --live." |
| EC-004 | S3 bucket env var not set | Exit 2 with "ASANA_CACHE_S3_BUCKET not configured." |
| EC-005 | Empty result set | Print empty table/JSON/CSV (headers only for table/CSV, `[]` for JSON). Metadata to stderr shows total_count=0. Exit 0 (not an error). |
| EC-006 | Classification not available for entity type | Exit 1 with "Classification not available for {entity_type}. Available for: offer, unit" |
| EC-007 | Invalid predicate operator for dtype | Exit 1 with InvalidOperatorError message (field, dtype, operator, allowed operators) |
| EC-008 | --where flag with malformed syntax | Exit 1 with "Invalid predicate: '{raw}'. Expected format: 'field op value'. Supported ops: eq, ne, gt, lt, gte, lte, in, not_in, contains, starts_with" |
| EC-009 | --agg flag with malformed syntax | Exit 1 with "Invalid aggregation: '{raw}'. Expected format: 'function:column[:alias]'. Supported functions: sum, count, mean, min, max, count_distinct" |
| EC-010 | Join target entity has no cached data | Exit 1 with "No cached data for join target '{entity_type}'." |
| EC-011 | No relationship between source and join target | Exit 1 with JoinError message (source, target, joinable types list) |
| EC-012 | --output file path not writable | Exit 2 with "Cannot write to '{path}': {os error}" |
| EC-013 | --live without credentials | Exit 2 with "Live mode requires ASANA_SERVICE_KEY or configured PAT." |
| EC-014 | section and classification both specified | Exit 1 with "section and classification are mutually exclusive" (matches RowsRequest validator) |
| EC-015 | --where-json with invalid JSON | Exit 1 with "Invalid JSON in --where-json: {parse error}" |
| EC-016 | Predicate depth exceeds limit (5) | Exit 1 with QueryTooComplexError message |
| EC-017 | Aggregate group count exceeds limit (10,000) | Exit 1 with AggregateGroupLimitError message |
| EC-018 | Entity without schema (non-warmable, e.g., process) | Exit 1 with "No schema available for {entity_type}. Queryable entities: {list}" |
| EC-019 | --period flag with invalid date format | Exit 1 with "Invalid period: '{raw}'. Expected format: 'YYYY-MM-DD:YYYY-MM-DD'" |
| EC-020 | Saved query name not found | Exit 1 with "No saved query named '{name}'. Use 'list-queries' to see available." |

## Success Criteria

- [ ] SC-1: `python -m autom8_asana.query rows offer --classification active --select gid,name,mrr --format table` returns active offers in table format within 3 seconds (offline mode)
- [ ] SC-2: `python -m autom8_asana.query aggregate offer --group-by section --agg sum:mrr --classification active` returns correct MRR per section matching known oracle ($96,126 total active MRR)
- [ ] SC-3: `python -m autom8_asana.query rows offer --join business --join-select booking_type --format json | jq length` returns count matching total offers
- [ ] SC-4: `python -m autom8_asana.query entities` lists all warmable entity types from EntityRegistry
- [ ] SC-5: `python -m autom8_asana.query fields offer` lists all columns from OFFER_SCHEMA with dtypes
- [ ] SC-6: `python -m autom8_asana.query relations offer` shows joinable types: business, unit (with join keys)
- [ ] SC-7: All edge cases EC-001 through EC-020 produce correct exit codes and actionable error messages
- [ ] SC-8: `--format json` output pipes cleanly to `jq` without metadata contamination (metadata goes to stderr)
- [ ] SC-9: OfflineDataFrameProvider passes isinstance check against DataFrameProvider protocol
- [ ] SC-10: Existing API endpoints (`POST /v1/query/{entity_type}/rows` and `/aggregate`) continue to function unchanged (no regression)
- [ ] SC-11: Unit test coverage for new modules >= 90% line coverage
- [ ] SC-12: CLI `--help` for every subcommand includes at least one usage example

## Out of Scope

| Item | Rationale |
|------|-----------|
| Natural language / LLM query interface | Separate initiative; requires prompt engineering and semantic parsing layer |
| Interactive REPL | CLI with history is sufficient for V1; REPL requires state management, tab completion, session persistence |
| Multi-workspace queries | Single workspace assumption permeates the codebase (ASANA_WORKSPACE_GID); cross-workspace requires auth refactoring |
| Full-text / fuzzy search | QueryEngine uses exact predicate matching; full-text requires search index infrastructure |
| Custom aggregation functions (UDFs) | 6 built-in aggregations (sum, count, mean, min, max, count_distinct) cover known use cases; UDFs need sandboxing |
| Write operations via CLI | CLI is read-only; mutations go through the existing API |
| Real-time streaming / watch mode | Batch query model; streaming requires event infrastructure |
| GUI / web dashboard | CLI-first; GUI built on top of API introspection endpoints (FR-012) in separate initiative |

## Open Questions

None. All stakeholder decisions captured in the interview summary above.

## Phase Boundaries

### Phase 1: CLI Foundation + Output + Discovery (independently valuable)

**Deliverables**: FR-001, FR-002, FR-003, FR-005, FR-006, FR-008
**User stories**: US-1 (rows only), US-4, US-5, US-6 (offline only)
**Value**: Users can query any single entity type with filters, pagination, column selection, and multiple output formats. Discovery subcommands eliminate "what fields exist?" friction.

**Key implementation notes**:
- OfflineDataFrameProvider bridges `load_project_dataframe()` to DataFrameProvider protocol
- CLI arg parser maps flags to RowsRequest models (reuse existing Pydantic validation)
- Output formatter wraps polars DataFrame serialization
- Entity/field/relation/section discovery reads from existing registries (zero new infrastructure)

### Phase 2: Aggregation + Cross-Entity Joins

**Deliverables**: FR-004, FR-007
**User stories**: US-2, US-3
**Value**: Aggregation queries (MRR by section, count by classification) and cross-entity enrichment (offer + business columns).

**Key implementation notes**:
- Aggregate CLI maps `--agg function:column[:alias]` to AggSpec models
- Join CLI maps `--join entity --join-select cols --join-on key` to JoinSpec
- Both reuse QueryEngine.execute_rows() and execute_aggregate() directly

### Phase 3: Temporal + Saved Queries + Live Mode

**Deliverables**: FR-009, FR-010, FR-011
**User stories**: US-7, US-8, US-6 (live mode)
**Value**: Section transition analysis, reusable query templates, live API fallback.

**Key implementation notes**:
- Timeline subcommand requires live API access (SectionTimeline is story-based)
- Saved queries stored as YAML in `~/.autom8/queries/`
- `--live` flag swaps OfflineDataFrameProvider for EntityQueryService

### Phase 4: API Introspection + Multi-Hop Joins + Relationship Metadata

**Deliverables**: FR-012, FR-013, FR-014, FR-015
**User stories**: US-9
**Value**: Dynamic query UI support, multi-hop joins, cardinality awareness.

**Key implementation notes**:
- API endpoints read same registries as CLI discovery subcommands
- Multi-hop joins require join planner and lifting MAX_JOIN_DEPTH
- Cardinality annotations added to EntityRelationship dataclass

## Existing Asset Reference Map

| Asset | Location | Used By |
|-------|----------|---------|
| QueryEngine | `src/autom8_asana/query/engine.py` | FR-003, FR-004, FR-007 (core query execution) |
| RowsRequest / AggregateRequest | `src/autom8_asana/query/models.py` | FR-003, FR-004 (CLI flag target models) |
| PredicateCompiler | `src/autom8_asana/query/compiler.py` | FR-003 (predicate AST to polars expression) |
| PredicateNode (Comparison, AndGroup, OrGroup, NotGroup) | `src/autom8_asana/query/models.py` | FR-003 (CLI flag parsing target) |
| Op enum (10 operators) | `src/autom8_asana/query/models.py` | FR-003 (CLI --where parsing) |
| AggFunction enum (6 functions) | `src/autom8_asana/query/models.py` | FR-004 (CLI --agg parsing) |
| AggregationCompiler | `src/autom8_asana/query/aggregator.py` | FR-004 (agg spec to polars expression) |
| JoinSpec | `src/autom8_asana/query/join.py` | FR-007 (CLI join flag target) |
| execute_join() | `src/autom8_asana/query/join.py` | FR-007 (left join execution) |
| EntityRelationship / ENTITY_RELATIONSHIPS | `src/autom8_asana/query/hierarchy.py` | FR-006, FR-007 (relation discovery, join resolution) |
| find_relationship(), get_join_key(), get_joinable_types() | `src/autom8_asana/query/hierarchy.py` | FR-007 (smart join key resolution) |
| QueryLimits | `src/autom8_asana/query/guards.py` | FR-003, FR-004 (depth/row/group limits) |
| QueryEngineError hierarchy | `src/autom8_asana/query/errors.py` | FR-003, FR-004 (error handling) |
| DataFrameProvider protocol | `src/autom8_asana/protocols/dataframe_provider.py` | FR-002 (OfflineDataFrameProvider target) |
| load_project_dataframe() | `src/autom8_asana/dataframes/offline.py` | FR-002 (S3 parquet loading) |
| EntityRegistry / get_registry() | `src/autom8_asana/core/entity_registry.py` | FR-002, FR-006 (entity type resolution, discovery) |
| EntityDescriptor | `src/autom8_asana/core/entity_registry.py` | FR-006 (entity metadata for discovery) |
| SchemaRegistry | `src/autom8_asana/dataframes/models/registry.py` | FR-006 (field discovery) |
| CLASSIFIERS (OFFER_CLASSIFIER, UNIT_CLASSIFIER) | `src/autom8_asana/models/business/activity.py` | FR-006 (section/classification discovery) |
| SectionClassifier | `src/autom8_asana/models/business/activity.py` | FR-003 (classification resolution in engine) |
| AccountActivity enum | `src/autom8_asana/models/business/activity.py` | FR-003, FR-006 (classification values) |
| SectionTimeline / OfferTimelineEntry | `src/autom8_asana/models/business/section_timeline.py` | FR-009 (temporal query data model) |
| API routes (query_rows, query_aggregate) | `src/autom8_asana/api/routes/query.py` | FR-012 (introspection routes, co-located) |
| metrics CLI (__main__.py) | `src/autom8_asana/metrics/__main__.py` | FR-001 (reference pattern for CLI structure) |
| DataFrameBuilder.to_csv/to_json/to_parquet | `src/autom8_asana/dataframes/builders/base.py` | FR-005 (export method reference) |

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/AUTOM8_QUERY/PRD.md` | Read-confirmed |
