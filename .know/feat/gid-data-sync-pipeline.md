---
domain: feat/gid-data-sync-pipeline
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/services/gid_push.py"
  - "./src/autom8_asana/services/gid_lookup.py"
  - "./src/autom8_asana/lambda_handlers/push_orchestrator.py"
  - "./src/autom8_asana/lambda_handlers/pipeline_stage_aggregator.py"
  - "./tests/unit/services/test_gid_push.py"
  - "./tests/unit/services/test_gid_lookup.py"
  - "./tests/unit/lambda_handlers/test_push_orchestrator.py"
  - "./tests/unit/lambda_handlers/test_pipeline_stage_aggregator.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.93
format_version: "1.0"
---

# Feature Knowledge: GID Data Sync Pipeline

## 1. Purpose and Design Rationale

### Problem Statement

The Asana cache warmer builds in-memory DataFrames from Asana project data, covering 10 pipeline types and several core entity types (unit, offer, contact, etc.). Other services in the autom8y platform — specifically `autom8_data` — need to resolve business GIDs from `(phone, vertical)` pairs and to know which Asana pipeline section a business is currently in. Without a push mechanism, `autom8_data` would have to call back into `autom8_asana` on every lookup, creating tight runtime coupling and adding per-request latency.

The GID Data Sync Pipeline solves this by exporting two derived datasets to `autom8_data` after each cache warm cycle:

1. **GID Mappings**: `(phone, vertical) → task_gid` — enables `autom8_data` to resolve Asana GIDs locally without calling back.
2. **Account Status**: `(phone, vertical) → pipeline_type + section + activity` — enables `autom8_data` to serve account-activity queries locally.

Both pushes are **best-effort side-effects**: if they fail, the cache warm cycle succeeds anyway. This design avoids making `autom8_data` availability a hard dependency of the cache warmer.

### Design Decisions and Rationale

**ADR-WS1-001: Pydantic models use `extra="ignore"`** — Response envelopes (`GidPushResponse`, `AccountStatusPushResponse`) intentionally tolerate unknown fields from upstream, as the `autom8_data` response shape is not formally contractualized. This avoids breaking changes when `autom8_data` adds fields.

**ADR-PVP-002: Canonical key format `pv1:{phone}:{vertical}`** — The `GidLookupIndex` uses a version-prefixed key scheme. The `pv1:` prefix enables future key schema migrations without breaking existing serialized indexes. Keys are stored lowercase to normalize phone/vertical inconsistencies across data sources.

**ADR-account-status-state-projection (SD-02, active-only registry)** — The status push filters to only `ACTIVE` and `ACTIVATING` classifications. `INACTIVE`, `IGNORED`, and unclassifiable rows are excluded. This keeps the `autom8_data` account-status table lean (only actionable accounts) and avoids stale/misleading status data for churned businesses.

**ADR-pipeline-stage-aggregation, Option C (ephemeral summary)** — The `pipeline_stage_aggregator` does NOT write its output to the cache. It computes an in-memory pipeline summary DataFrame within the Lambda invocation and passes it downstream (e.g., to reconciliation). Writing it to cache was considered (Options A and B) but rejected: the summary is a derived cross-pipeline view with no independent TTL, and caching a derived DataFrame that becomes stale the next warm cycle was judged to add complexity without benefit.

**FLAG-1: Orchestration code stays in `lambda_handlers/`** — `push_orchestrator.py` and `pipeline_stage_aggregator.py` both explicitly document this placement in their module docstrings. The `push_orchestrator` imports from `services.gid_lookup` and `services.gid_push`; if it lived in `services/`, it would create a circular import (services importing from services). The `lambda_handlers/` placement breaks the cycle. This is documented as **TENSION-004** in `.know/design-constraints.md`.

**Best-effort isolation pattern (BROAD-CATCH)** — All push paths use a `try/except Exception` broad-catch annotated with `# BROAD-CATCH: isolation — push failure must never fail cache warmer`. This is an intentional, deliberate pattern (not sloppy error handling). It mirrors the same pattern used in `reconciliation_runner.py` in the same directory.

**Emergency kill switches** — Both the GID mapping push (`GID_PUSH_ENABLED`) and the account status push (`STATUS_PUSH_ENABLED`) have environment-variable kill switches. They default to enabled; setting to `"false"`, `"0"`, or `"no"` disables them. This was built as an operational safety valve for production incidents.

### Alternatives Rejected

- **Calling `autom8_asana` from `autom8_data` at lookup time**: Rejected — creates tight runtime coupling, adds latency, and creates a failure mode where `autom8_data` cannot answer queries when `autom8_asana` is degraded.
- **Caching the pipeline stage summary (Options A/B)**: Rejected in ADR-pipeline-stage-aggregation. The summary is a short-lived derived view best computed fresh per invocation.

---

## 2. Conceptual Model

### Key Terminology

| Term | Definition |
|------|-----------|
| **GidLookupIndex** | An O(1) lookup structure mapping `pv1:{phone}:{vertical}` canonical keys to Asana task GIDs. Built from a warmed DataFrame. Supports serialization to JSON for S3 persistence. |
| **canonical_key** | The string `pv1:{phone}:{vertical}` — version-prefixed, lowercase. Format defined by ADR-PVP-002. |
| **GidPushResponse** | Pydantic model for the `POST /api/v1/gid-mappings/sync` response. Fields: `accepted: int | None`, `replaced: int | None`. Uses `extra="ignore"`. |
| **AccountStatusPushResponse** | Pydantic model for `POST /api/v1/account-status/sync`. Fields: `deleted: int | None`, `inserted: int | None`. Uses `extra="ignore"`. |
| **AccountActivity** | Enum in `models/business/activity.py`. Values include `ACTIVE`, `ACTIVATING`, `INACTIVE`, `IGNORED`. SD-02 active-only rule: only ACTIVE and ACTIVATING are pushed. |
| **pipeline_type** | String identifier for an Asana pipeline (e.g., `"unit"`, `"sales"`, `"onboarding"`). Derived from `PIPELINE_TYPE_BY_PROJECT_GID` (keyed by Asana project GID). |
| **build_gid_index_data** | Callback function conforming to the `index_builder` interface of `ProgressiveProjectBuilder`. Called during DataFrame build to produce serialized index data. |
| **pipeline_summary** | Ephemeral Polars DataFrame produced by `_aggregate_pipeline_stages`. Columns: `office_phone`, `vertical`, `latest_process_type`, `latest_process_section`, `latest_created`. Never written to cache. |
| **push_orchestrator** | Lambda-layer module that sequences post-warm side-effects: iterates completed entity types, builds indexes, and calls push functions. |
| **PIPELINE_TYPE_BY_PROJECT_GID** | Static dict in `gid_push.py` mapping Asana project GIDs to pipeline type strings. 10 entries covering the main business pipelines. Independent of the entity registry. |

### State Machine: Post-Cache-Warm Push Sequence

```
Lambda invocation
    ↓
cache_warmer.py warms DataFrames for all entity types
    ↓ (completed_entities list populated)
push_orchestrator._push_gid_mappings_for_completed_entities()
    for each entity_type in completed_entities:
        project_gid = get_project_gid(entity_type)
        entry = cache.get_async(project_gid, entity_type)
        index = GidLookupIndex.from_dataframe(entry.dataframe, key_cols)
        push_gid_mappings_to_data_service(project_gid, index)
            → POST /api/v1/gid-mappings/sync  →  autom8_data
    ↓
push_orchestrator._push_account_status_for_completed_entities()
    for each entity_type in completed_entities:
        entries = extract_status_from_dataframe(df, project_gid, entity_type)
        [aggregate all_entries across entity types]
    push_status_to_data_service(all_entries, source_timestamp)
        → POST /api/v1/account-status/sync  →  autom8_data
    ↓
pipeline_stage_aggregator._aggregate_pipeline_stages()
    filter completed_entities to process_* entries
    for each pipeline entity:
        retrieve DataFrame from cache
        add pipeline_type discriminator column
    concat all pipeline DFs
    filter is_completed == False (active only)
    group_by (office_phone, vertical) → pick latest by 'created'
    → returns pipeline_summary DataFrame (or None)
    [consumed by reconciliation_runner.py within the same invocation]
```

### GidLookupIndex Lifecycle

```
Build path:   DataFrame (warmed) → GidLookupIndex.from_dataframe() → in-memory index
Push path:    in-memory index → extract_mappings_from_index() → POST /api/v1/gid-mappings/sync
S3 path:      in-memory index → index.serialize() → S3 store
              S3 load → GidLookupIndex.deserialize() → in-memory index (warm-start)
Lookup path:  PhoneVerticalPair.canonical_key → index.get_gid() → task_gid (O(1))
Stale check:  index.is_stale(ttl_seconds) → bool
```

### Inter-Feature Relationships

| Direction | Feature | Via |
|-----------|---------|-----|
| **Consumes from** | Cache subsystem | `cache.DataFrameCache.get_async()` — retrieves warmed DataFrames |
| **Consumes from** | Entity registry | `core.entity_registry.get_registry()` — resolves project GIDs by entity name |
| **Consumes from** | Universal strategy | `services.universal_strategy.DEFAULT_KEY_COLUMNS` — per-entity-type key column configuration |
| **Consumes from** | Business models | `models.business.activity.AccountActivity`, `get_classifier()`, `extract_section_name()` — section classification |
| **Provides to** | autom8_data satellite | GID mappings via `POST /api/v1/gid-mappings/sync`; account status via `POST /api/v1/account-status/sync` |
| **Provides to** | Reconciliation pipeline | `pipeline_summary` DataFrame consumed by `reconciliation_runner.py` within same Lambda invocation |
| **Provides to** | Preload paths | `GidLookupIndex` used by `api/preload/progressive.py`, `api/preload/legacy.py`, `dataframes/builders/progressive.py` during warm-up phases |

---

## 3. Implementation Map

### File Responsibilities

| File | LOC | Responsibility |
|------|-----|---------------|
| `src/autom8_asana/services/gid_lookup.py` | 318 | `GidLookupIndex` class: O(1) dict-backed lookup, `from_dataframe()` factory, `serialize()`/`deserialize()` S3 round-trip, stale check, batch lookup. Also `build_gid_index_data()` — the `index_builder` callback used during DataFrame build. |
| `src/autom8_asana/services/gid_push.py` | 536 | Push execution: `push_gid_mappings_to_data_service()`, `push_status_to_data_service()`, `extract_mappings_from_index()`, `extract_status_from_dataframe()`. Response models: `GidPushResponse`, `AccountStatusPushResponse`. Shared HTTP helper `_push_to_data_service()`. Feature-flag checks. `PIPELINE_TYPE_BY_PROJECT_GID` registry. |
| `src/autom8_asana/lambda_handlers/push_orchestrator.py` | 207 | Thin orchestration wrappers: `_push_gid_mappings_for_completed_entities()` and `_push_account_status_for_completed_entities()`. Sequences iteration over completed entity types, invokes push functions, emits CloudWatch metrics. Lives in `lambda_handlers/` per FLAG-1. |
| `src/autom8_asana/lambda_handlers/pipeline_stage_aggregator.py` | 217 | `_aggregate_pipeline_stages()`: scans all `process_*` pipeline DataFrames, adds `pipeline_type` discriminator, concatenates, filters to active tasks, groups by `(office_phone, vertical)`, picks most recent. Returns ephemeral summary or `None`. Lives in `lambda_handlers/` per FLAG-1. |

**Total: 4 files, ~1,278 LOC**

### Entry Points and Key Types

**`gid_lookup.py`**
- `GidLookupIndex` — main class; constructed via `from_dataframe(df, key_columns)` or `deserialize(data)`
- `build_gid_index_data(df, entity_type) → dict | None` — index_builder callback; returns `index.serialize()` output
- `GidLookupIndex.serialize() → dict` — JSON-safe dict for S3 storage
- `GidLookupIndex.deserialize(data) → GidLookupIndex` — raises `KeyError`/`ValueError` on invalid data
- `GidLookupIndex.get_gid(pair: PhoneVerticalPair) → str | None` — O(1) lookup
- `GidLookupIndex.is_stale(ttl_seconds: int) → bool`

**`gid_push.py`**
- `push_gid_mappings_to_data_service(project_gid, index, *, data_service_url, auth_token) → bool` — async; returns True on 2xx
- `push_status_to_data_service(entries, source_timestamp, *, data_service_url, auth_token) → bool` — async
- `extract_mappings_from_index(index) → list[dict]` — parses `pv1:phone:vertical` keys
- `extract_status_from_dataframe(df, project_gid, entity_type) → list[dict]` — section classification + SD-02 filter
- `PIPELINE_TYPE_BY_PROJECT_GID: dict[str, str]` — 10 entries; must be kept in sync with entity registry
- `GID_PUSH_ENABLED_ENV_VAR = "GID_PUSH_ENABLED"`, `STATUS_PUSH_ENABLED_ENV_VAR = "STATUS_PUSH_ENABLED"`

**`push_orchestrator.py`**
- `_push_gid_mappings_for_completed_entities(completed_entities, get_project_gid, cache, invocation_id)` — async; emits `GidPushSuccess`/`GidPushFailure` CloudWatch metrics
- `_push_account_status_for_completed_entities(completed_entities, get_project_gid, cache, invocation_id)` — async; emits `StatusPushSuccess`/`StatusPushFailure`

**`pipeline_stage_aggregator.py`**
- `_aggregate_pipeline_stages(*, completed_entities, cache, invocation_id) → pl.DataFrame | None` — async

### Data Flow

```
Input:  warmed DataFrame (Polars) from DataFrameCache
        entity_type, project_gid from entity registry

GID mapping path:
  DataFrame
    → GidLookupIndex.from_dataframe(df, key_columns=["office_phone","vertical"])
    → {pv1:phone:vertical → task_gid} dict
    → extract_mappings_from_index() → [{phone, vertical, task_gid}, ...]
    → HTTP POST /api/v1/gid-mappings/sync → autom8_data

Account status path:
  DataFrame
    → extract_status_from_dataframe(df, project_gid, entity_type)
    → SectionClassifier.classify(section_name) → AccountActivity
    → filter: only ACTIVE, ACTIVATING (SD-02)
    → [{phone, vertical, pipeline_type, account_activity, pipeline_section, stage_entered_at}, ...]
    → aggregate across all entity types
    → HTTP POST /api/v1/account-status/sync → autom8_data

Pipeline summary path:
  process_* DataFrames from cache
    → add pipeline_type column (_derive_pipeline_type strips "process_" prefix)
    → pl.concat(frames, how="diagonal_relaxed")
    → filter is_completed == False
    → filter null (office_phone, vertical)
    → group_by((office_phone, vertical)).first() [sorted desc by created]
    → pipeline_summary DataFrame → returned to cache_warmer → passed to reconciliation_runner
```

### Import Call Sites (7 consumers)

| File | What it uses |
|------|-------------|
| `cache/dataframe/factory.py` | `build_gid_index_data` as `index_builder` callback |
| `core/registry_validation.py` | `PIPELINE_TYPE_BY_PROJECT_GID` — validates GID registry coverage |
| `api/preload/progressive.py` | `build_gid_index_data` as `index_builder` + `GidLookupIndex.deserialize()` for warm-start |
| `api/preload/legacy.py` | `build_gid_index_data` as `index_builder` |
| `services/universal_strategy.py` | `DEFAULT_KEY_COLUMNS` (indirectly: `build_gid_index_data` calls it) |
| `services/dataframe_service.py` | `GidLookupIndex` for lookup operations |
| `api/routes/admin.py` | `GidLookupIndex` for admin introspection |
| `lambda_handlers/cache_warmer.py` | `push_orchestrator` and `pipeline_stage_aggregator` (top-level imports at module load) |

### Test Coverage

| Test File | Covers |
|-----------|--------|
| `tests/unit/services/test_gid_push.py` | `extract_mappings_from_index`, `_is_push_enabled`, `push_gid_mappings_to_data_service` (happy path, disabled, no-URL, no-token, HTTP errors, timeout, broad exception, URL override, trailing-slash), `GidPushResponse` contract, `extract_status_from_dataframe` (all 6 early-exit branches + SD-02 filter + output shape + classifier fallback) |
| `tests/unit/services/test_gid_lookup.py` | `serialize`/`deserialize` (all required keys, version validation, datetime parsing, entry-count mismatch), round-trip guarantee through JSON, `from_dataframe` (null filtering, missing columns, extra columns), `get_gid`, `get_gids` batch, `is_stale`, `__contains__`, `__len__` |
| `tests/unit/lambda_handlers/test_push_orchestrator.py` | Module importability, both entry points callable, `__all__` exports, empty entity list no-ops, entity with no project GID skipped, cache miss gracefully skipped, push failure isolation (BROAD-CATCH) |
| `tests/unit/lambda_handlers/test_pipeline_stage_aggregator.py` | `_derive_pipeline_type` for all 5 pipeline types, zero pipeline entities, single DF, multiple DFs (concatenation + latest-by-created wins), completed task filtering, grouping picks most recent, null grouping key exclusion, error isolation (cache exception, registry exception), cache edge cases |

---

## 4. Boundaries and Failure Modes

### Scope Boundaries (What This Feature Does NOT Do)

- **Not a live read path.** `GidLookupIndex` is built at cache-warm time and pushed to `autom8_data`. Live GID resolution at request time is served by `autom8_data` from its own store — not by calling back into `autom8_asana`.
- **Not responsible for push receipt confirmation.** The push is fire-and-forget from the cache warmer's perspective. If `autom8_data` accepts but silently discards, the warmer has no mechanism to detect this.
- **Not responsible for data consistency across partial warm cycles.** If only some entity types complete warming (partial invocation), only those entity types' GID mappings are pushed. There is no compensating transaction for the un-warmed types.
- **`pipeline_stage_aggregator` output is not persisted.** The pipeline summary DataFrame exists only for the duration of the Lambda invocation. It is not written to cache, S3, or any external store. Consuming code (reconciliation_runner) must use it inline.
- **`PIPELINE_TYPE_BY_PROJECT_GID` is a static registry** — it does not auto-populate from the entity registry. If a new Asana project is added to the entity registry but not to this dict, its pipeline type resolution will return `None` and its rows will be silently excluded from status extraction. `core/registry_validation.py` validates this alignment at startup.

### Configuration Boundaries

| Variable | Default | Effect when disabled/unset |
|----------|---------|---------------------------|
| `GID_PUSH_ENABLED` | `""` (enabled) | Set to `"false"`, `"0"`, or `"no"` to disable GID mapping push entirely |
| `STATUS_PUSH_ENABLED` | `""` (enabled) | Set to `"false"`, `"0"`, or `"no"` to disable account status push entirely |
| `AUTOM8Y_DATA_URL` | unset | Push is skipped (logged as `gid_push_skipped` or `status_push_skipped`). Not an error condition. |
| `AUTOM8Y_DATA_API_KEY` | unset | Push is skipped. Resolved via `autom8y_config.lambda_extension.resolve_secret_from_env()` — supports SSM ARN references. |

HTTP timeout configuration: `_PUSH_CONFIG` — `connect_timeout=5s`, `read_timeout=10s`, `write_timeout=10s`, `pool_timeout=5s`. Retries and circuit breaker are disabled (`enable_retry=False`, `enable_circuit_breaker=False`). This is intentional: a slow `autom8_data` should not block the Lambda invocation.

### Failure Modes

**1. Push failure (network, timeout, HTTP 4xx/5xx)**
- Handled by `_push_to_data_service()` — `TimeoutException` and broad `Exception` are caught and logged.
- Return value: `False`. CloudWatch metrics `GidPushFailure` or `StatusPushFailure` are emitted.
- Impact: `autom8_data` GID/status data is not updated for this warm cycle. Stale data persists from the previous successful push.
- Recovery: Automatic on next successful warm cycle.

**2. Entity type not in `PIPELINE_TYPE_BY_PROJECT_GID`**
- `extract_status_from_dataframe` logs `status_extract_unknown_project` at DEBUG level and returns `[]`.
- No entries are pushed for that project GID.
- Detected at startup by `core/registry_validation.py` which validates alignment between entity registry and `PIPELINE_TYPE_BY_PROJECT_GID`.

**3. Entity type DataFrame missing required columns (`office_phone`, `gid`)**
- `GidLookupIndex.from_dataframe()` raises `KeyError` (missing required columns).
- Caught in `push_orchestrator._push_gid_mappings_for_completed_entities()` — `KeyError` on index build causes `continue` (the entity is silently skipped). This is the correct behavior for entity types that are not GID-bearing (e.g., `offer`, `contact`).
- For status extraction: `extract_status_from_dataframe()` checks `required_cols = {"office_phone"}` and returns `[]` if absent.

**4. `GidLookupIndex.deserialize()` on corrupted S3 data**
- Raises `KeyError` (missing required keys), `ValueError` (bad version, bad datetime format, entry count mismatch).
- Callers in `api/preload/progressive.py` and `api/preload/legacy.py` handle these exceptions and fall back to rebuilding from DataFrame.

**5. `_aggregate_pipeline_stages()` error**
- Wrapped in top-level `try/except Exception` (BROAD-CATCH). Logs `pipeline_stage_aggregation_error` at WARNING.
- Returns `None`. Reconciliation runner must handle `None` pipeline summary.

**6. Empty push (no entries)**
- `push_gid_mappings_to_data_service`: empty index returns `True` immediately (no HTTP call). Logged as `gid_push_skipped` with reason `no_mappings_to_push`.
- `push_status_to_data_service`: empty entries returns `True` immediately. Logged as `status_push_skipped`.
- Returning `True` for an empty push is intentional — "nothing to push" is not a failure.

**7. PII in error logs**
- Response body text and error strings are passed through `mask_pii_in_string()` before logging. This prevents phone numbers from appearing in CloudWatch logs on HTTP error responses.

### Interaction Points with Adjacent Features

- **`reconciliation_runner.py`** (same `lambda_handlers/` directory) receives the `pipeline_summary` DataFrame from `_aggregate_pipeline_stages()`. This is the primary downstream consumer of the pipeline aggregation output.
- **`DataFrameCache`** (cache subsystem) provides warmed DataFrames. The push pipeline is strictly downstream of warming — it never triggers warming or writes back to cache.
- **`core.entity_registry`** is consulted by `pipeline_stage_aggregator` to resolve `primary_project_gid` for each pipeline entity. If registry returns `None` for an entity, that entity is skipped with a WARNING log.
- **`models.business.activity.get_classifier(entity_type)`** — the account status path depends on entity-type classifiers being registered. An unrecognized entity type causes a WARNING log and produces no entries (warn+skip behavior, not silent fallback — changed from earlier behavior per TC-5 of H-03 remediation).

---

```metadata
confidence: 0.93

Criterion grades:
  purpose_and_design_rationale: A (95%)
    - Problem statement clearly articulated: autom8_data GID/status coupling problem
    - FLAG-1 architectural rationale: documented in source + design-constraints TENSION-004
    - ADR references: ADR-WS1-001, ADR-PVP-002, ADR-account-status-state-projection, ADR-pipeline-stage-aggregation
    - Rejected alternatives documented for both cache strategy and runtime coupling
    - SD-02 active-only registry design decision documented with rationale

  conceptual_model: A (92%)
    - All 9 key terms defined with context
    - State machine traced from Lambda invocation through all three push paths
    - GidLookupIndex lifecycle documented (build/push/S3/lookup/stale paths)
    - Inter-feature relationships mapped with direction (provides/consumes)
    - Minor gap: no diagram of full Lambda invocation sequence (text state machine covers it)

  implementation_map: A (95%)
    - All 4 implementing files documented with LOC, responsibility, key types, entry points
    - Data flow traced for all three paths (GID mapping, account status, pipeline summary)
    - 7+ import call sites identified and documented
    - All 4 test files listed with explicit coverage descriptions
    - Public API surface documented with function signatures and return types

  boundaries_and_failure_modes: A (94%)
    - 7 explicit failure modes documented with causes, log events, and recovery paths
    - Scope boundaries listed with "NOT" statements for all major out-of-scope concerns
    - Configuration boundaries tabulated for all 4 environment variables
    - PII masking in logs noted
    - PIPELINE_TYPE_BY_PROJECT_GID static registry limitation documented
    - Empty push semantics (True for no-op) explicitly documented

overall: A (94%)
weighted: purpose(0.30)*95 + model(0.25)*92 + implementation(0.25)*95 + boundaries(0.20)*94 = 28.5 + 23.0 + 23.75 + 18.8 = 94.05
```
