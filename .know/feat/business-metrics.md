---
domain: feat/business-metrics
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/metrics/"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.93
format_version: "1.0"
---

# Business Metrics Computation (MRR, Ad Spend, Lifecycle)

## Purpose and Design Rationale

Declarative, data-pipeline-independent system for computing business scalar metrics from Polars DataFrames loaded from S3-backed parquet cache. The system answers: "What is the current MRR / Ad Spend / pipeline throughput?" without requiring a live Asana API call.

**Primary metrics**: `active_mrr` (Monthly Recurring Revenue) and `active_ad_spend` (total weekly ad spend), both summed across ACTIVE-classified offer rows, deduplicated by `(office_phone, vertical)` to prevent inflation from multiple Offers per Unit.

**Why deduplication is domain-critical**: MRR and ad spend live at Unit level, not Offer level. One business unit may have multiple sibling Offer rows in the DataFrame. Without `(office_phone, vertical)` dedup (the "PVP" — Phone+Vertical Pair), sums inflate proportional to the number of offers per unit. This invariant is documented inline in `definitions/offer.py`.

**Lifecycle pipeline metrics** (separate domain): 7 metrics operating on the `stage_transition` entity type — conversion counts between pipeline stages, duration statistics, stall detection, and weekly throughput.

**CLI-only surface**: `python -m autom8_asana.metrics`. No REST API route; offline computation only.

**Design decisions**:
- Declarative composition (MetricExpr + Scope + Metric) separates WHAT from WHERE, enabling per-metric overrides without touching the pipeline.
- `compute_metric()` returns a filtered DataFrame, not a scalar — the caller aggregates. This enables `--verbose` per-row inspection and caller-controlled aggregation (e.g., rate computation across two metrics).
- `MetricRegistry` follows the ProjectTypeRegistry singleton pattern (ADR-0093) with lazy init and explicit `reset()` for test isolation.
- Freshness signal declared alongside scalar value (ADR-001): the CLI emits `FreshnessReport` derived from an S3 list operation, surfacing parquet age independently of the computed value.
- SLA profile layering (ADR-005): TTL thresholds are expressed as a 4-class taxonomy (`active=6h`, `warm=12h`, `cold=24h`, `near-empty=7d`), resolved via sidecar (S3, runtime) > manifest (YAML, version-controlled) > built-in defaults.
- CloudWatch metric emission (ADR-006): 5-metric batch to `Autom8y/FreshnessProbe` namespace. C-6 HARD CONSTRAINT: `SectionCoverageDelta` MUST NOT be wired to any CloudWatch alarm — enforced mechanically via `c6_guard_check()` and the `ALARMED_METRICS` frozenset.

**Freshness CLI history**: Per `__main__.py` comments, the force-warm CLI surface was unified via PT-2 Option B refactor (HANDOFF-thermia-to-10x-dev-2026-04-27) to delegate through `autom8_asana.cache.integration.force_warm` (canonical coalescer path), prohibiting direct Lambda invocation.

## Conceptual Model

### Declarative Pipeline Composition

```
MetricExpr  — WHAT (column name, optional cast dtype, row filter expr, aggregation fn)
Scope       — WHERE (entity type, section/classification, dedup keys, pre-filters)
Metric      — NAME + description + (MetricExpr, Scope) binding
```

`compute_metric(metric, df)` runs a fixed 7-step pipeline:

1. **Classification filter** (Step 0.5): if `scope.classification` is set, resolve `AccountActivity` sections via `CLASSIFIERS` and filter rows whose `section` column (lowercased) is in the resolved set.
2. **Column select**: `["name"] + dedup_keys + [expr.column]` (name included if present; dedup preserving order).
3. **Cast dtype**: cast `expr.column` to `expr.cast_dtype` with `strict=False` (handles string-encoded floats in financial columns).
4. **Apply expr filter**: `expr.filter_expr` (row-level; `None` means no filter).
5. **Apply scope pre_filters**: ANDed additional filters from `scope.pre_filters`.
6. **Deduplicate**: `unique(subset=dedup_keys, keep="first")`.
7. **Sort**: `sort(dedup_keys)` for deterministic output.

The caller is responsible for final aggregation: `result[metric.expr.column].sum()` etc.

### MetricExpr — Supported Aggregations

`SUPPORTED_AGGS` (frozenset, validated at construction): `sum`, `count`, `mean`, `min`, `max`, `median`, `quantile`. The `quantile` aggregation requires `quantile_value` (float ∈ [0,1]). Validation enforced in `MetricExpr.__post_init__()`.

### Section Resolution: Offline-First

`SectionIndex` provides case-insensitive name → GID lookup. Two constructors:
- `SectionIndex.from_manifest_async(persistence, project_gid)` — S3 manifest via `SectionPersistence.get_manifest_async()` (preferred).
- `SectionIndex.from_enum_fallback(entity_type)` — hardcoded `OfferSection` enum (supports `entity_type="offer"` only; empty index for unknown types).

`resolve_metric_scope(metric, index)` returns a new immutable `Metric` with its `scope.section` GID resolved from `scope.section_name`. Priority: `section` set → passthrough; `section_name` set → index lookup; lookup failure → `ValueError`.

### MetricRegistry — Singleton with Lazy Init

`MetricRegistry` follows singleton-via-`__new__` pattern (ADR-0093):
- Class-level `_instance` holds the single instance.
- `_ensure_initialized()` imports `autom8_asana.metrics.definitions` on first `get_metric()` / `list_metrics()` call; if the definitions package is already in `sys.modules` (e.g., post-`reset()` in tests), it reloads submodules so module-level registration re-executes.
- `reset()` classmethod sets `_instance = None`; self-registered with `SystemContext.reset_all()` via `register_reset(MetricRegistry.reset)` at module load time.
- `register()` is idempotent for the same object; raises `ValueError` on name collision with a different definition.

### Registered Metrics

**Offer domain** (both share `_ACTIVE_OFFER_SCOPE`: `entity_type="offer"`, `classification="active"`, `dedup_keys=["office_phone", "vertical"]`):
- `active_mrr`: `sum` of `mrr` (cast `pl.Float64`), filtered `is_not_null() & (> 0)`.
- `active_ad_spend`: `sum` of `weekly_ad_spend` (cast `pl.Float64`), filtered `is_not_null() & (> 0)`.

**Lifecycle domain** (all on `entity_type="stage_transition"`):
- `outreach_to_sales_conversion`: `count` of `entity_gid` where `from_stage="outreach"`, `to_stage="sales"`, `transition_type="converted"`. Uses `_STAGE_TRANSITION_DEDUP_SCOPE` (`dedup_keys=["entity_gid"]`).
- `sales_to_onboarding_conversion`: same structure, `from_stage="sales"`, `to_stage="onboarding"`.
- `onboarding_to_implementation_conversion`: same structure, `from_stage="onboarding"`, `to_stage="implementation"`.
- `stage_duration_median`: `median` of `duration_days` (cast `pl.Float64`), filtered `exited_at is_not_null()`. No dedup.
- `stage_duration_p95`: `quantile(0.95)` of `duration_days` (cast `pl.Float64`), filtered `exited_at is_not_null()`. No dedup.
- `stalled_entities`: `count` of `entity_gid` where `exited_at IS NULL AND entered_at < (now - 30 days)`. Threshold cutoff computed at module import time (known staleness if process long-running; see Boundaries).
- `weekly_transitions`: `count` of `entity_gid` with no filter. No dedup.

Total: 9 registered metrics (2 offer + 7 lifecycle).

### Freshness Model

`FreshnessReport` (frozen dataclass) is built from an S3 `list_objects_v2` paginator scan over `s3://{bucket}/dataframes/{project_gid}/sections/`. Key attributes:
- `oldest_mtime`, `newest_mtime`, `max_age_seconds`: derived from per-key `LastModified`.
- `stale`: `max_age_seconds > threshold_seconds` (exclusive; equality = fresh).
- `parquet_count`: total `.parquet` keys found.
- `mtimes`: per-key mtime tuple, retained for `section_age_p95_seconds()` computation.
- Sentinel: `parquet_count=0` → epoch-UTC mtimes, `max_age_seconds` at epoch distance; CLI exits 1.
- Error taxonomy: `FreshnessError.kind` ∈ `{auth, not-found, network, unknown}`.

### SLA Profile Taxonomy

4-class TTL taxonomy (ADR-005, FROZEN by FLAG-2):
| Class | Threshold | Default usage |
|---|---|---|
| `active` | 6h (21600s) | Default when no manifest/sidecar; CLI default |
| `warm` | 12h (43200s) | Relaxed; informational sections |
| `cold` | 24h (86400s) | Slow-moving sections |
| `near-empty` | 7d (604800s) | Presumably-inactive sections |

Override precedence: S3 sidecar JSON > YAML manifest (`.know/cache-freshness-ttl-manifest.yaml`) > built-in defaults.

### CloudWatch — C-6 Mechanical Guard

5 metrics emitted in one `put_metric_data` call to `Autom8y/FreshnessProbe` namespace:
- `MaxParquetAgeSeconds` — alarmed (ALERT-1/ALERT-2 per obs.md)
- `ForceWarmLatencySeconds` — emitted on `--force-warm --wait` success only (FLAG-1 boundary)
- `SectionCount` — from `parquet_count`
- `SectionAgeP95Seconds` — from `FreshnessReport.section_age_p95_seconds()`
- `SectionCoverageDelta` — informational only, **NO ALARM** (C-6 HARD CONSTRAINT)

`c6_guard_check(metric_name)` raises `C6ConstraintViolation` at any alarm-wiring site that targets a metric outside `ALARMED_METRICS`. `ALARMED_METRICS` deliberately excludes `SectionCoverageDelta`. Emission is best-effort: `put_metric_data` failures surface on stderr and do NOT change CLI exit code (PRD C-2 backwards-compat).

### CLI Preflight Contract (ADR-0001 / TDD-0001)

`_preflight_cli_profile()` runs `secretspec check --profile cli` before any S3 call. Required vars: `ASANA_CACHE_S3_BUCKET`, `ASANA_CACHE_S3_REGION`. On binary absence/timeout: falls back to inline check. Exit code 2 on preflight violation (distinct from runtime exit 1).

### Force-Warm Path (PT-2 Option B)

`--force-warm [--wait]` delegates to `autom8_asana.cache.integration.force_warm.force_warm()`. Direct Lambda invocation is FORBIDDEN (LD-P3-2). The coalescer key shape is `forcewarm:{project_gid}:{entity_types|*}`. On `--wait` success: L1 MemoryTier invalidated (ADR-003 HYBRID) + post-warm S3 recheck + FLAG-1 `ForceWarmLatencySeconds` emission. Env var: `CACHE_WARMER_LAMBDA_ARN` (fleet convention, matches `api/routes/admin.py:211` and `api/preload/progressive.py:548`).

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_asana/metrics/__init__.py` | Public API exports: `MetricExpr`, `Metric`, `Scope`, `MetricRegistry`, `compute_metric`, `SectionIndex`, `resolve_metric_scope` |
| `src/autom8_asana/metrics/metric.py` | `Scope` and `Metric` frozen dataclasses; `Scope.with_resolved_section()` returns new Scope with GID set |
| `src/autom8_asana/metrics/expr.py` | `MetricExpr` frozen dataclass; `SUPPORTED_AGGS` frozenset (7 aggs); `to_polars_expr()` builds chained Polars expr; `__post_init__` validates agg + quantile_value |
| `src/autom8_asana/metrics/compute.py` | `compute_metric()` with `@trace_computation("metric.compute", ...)` OTel decorator; 7-step pipeline |
| `src/autom8_asana/metrics/registry.py` | `MetricRegistry` singleton (ADR-0093); lazy `_ensure_initialized()`; `register_reset(MetricRegistry.reset)` at module load |
| `src/autom8_asana/metrics/resolve.py` | `SectionIndex` (frozen dataclass, case-insensitive lookup); `resolve_metric_scope()` — GID resolution from name via index |
| `src/autom8_asana/metrics/freshness.py` | `FreshnessReport` (frozen dataclass with `stale` property + `section_age_p95_seconds()`); `FreshnessError` (kind attribute); `parse_duration_spec()` / `format_duration()` / `format_human_lines()` / `format_json_envelope()` / `format_warning()` |
| `src/autom8_asana/metrics/sla_profile.py` | `SLA_CLASSES` (4-class tuple), `DEFAULT_THRESHOLDS`, `TtlManifest` / `TtlSidecar` / `SectionTtl` / `ProjectTtl` frozen dataclasses; validators V-1..V-6; `load_manifest()` / `load_sidecar()` / `resolve_ttl()` / `resolve_threshold_for_class()` |
| `src/autom8_asana/metrics/cloudwatch_emit.py` | `FRESHNESS_PROBE_NAMESPACE`, 5 metric name constants, `ALARMED_METRICS` frozenset, `C6ConstraintViolation`, `c6_guard_check()`, `emit_freshness_probe_metrics()` |
| `src/autom8_asana/metrics/__main__.py` | CLI entry: argparse (`--list`, `--verbose`, `--project-gid`, `--strict`, `--staleness-threshold`, `--json`, `--force-warm`, `--wait`, `--sla-profile`); preflight; data load; compute; freshness report; CW emission; exit code matrix |
| `src/autom8_asana/metrics/definitions/__init__.py` | Auto-imports `lifecycle` and `offer` submodules — triggers registration |
| `src/autom8_asana/metrics/definitions/offer.py` | `ACTIVE_MRR`, `ACTIVE_AD_SPEND` definitions; `_ACTIVE_OFFER_SCOPE` shared scope; auto-registers on import |
| `src/autom8_asana/metrics/definitions/lifecycle.py` | 7 lifecycle metrics; `_stall_filter()` computes cutoff at import time; auto-registers on import |

**Test coverage**: 14 test files in `tests/unit/metrics/` covering compute, expr, metric, registry, resolve, freshness, freshness-adversarial, freshness-S3, lifecycle, main, sla_profile, cloudwatch_emit, definitions, edge_cases, adversarial.

**Supported aggregation expressions**: `sum`, `count`, `mean`, `min`, `max`, `median`, `quantile` (requires `quantile_value`).

**OTel**: `compute_metric()` is decorated with `@trace_computation("metric.compute", record_dataframe_shape=True, df_param="df", engine="autom8y-asana")` from `autom8y_telemetry`. Sets `computation.duration_ms` span attribute.

**Data source**: `autom8_asana.dataframes.offline.load_project_dataframe(project_gid)` — reads S3-backed parquet; implementation not in metrics package scope.

## Boundaries and Failure Modes

### What This Feature Does NOT Do

- Does NOT import from `services/`, `clients/`, or `api/` — pure Domain Layer; no coupling upward.
- Does NOT provide a REST API route — CLI/offline only (no `GET /metrics` endpoint).
- Does NOT compute conversion rates as atomic metrics — callers compute rates from two scalar counts (by design; `MetricExpr` produces one scalar).
- Does NOT auto-discover definition files — `definitions/__init__.py` explicitly imports `lifecycle` and `offer`; adding a new file requires updating `definitions/__init__.py`.
- Does NOT validate that required DataFrame columns exist before pipeline start — `ColumnNotFoundError` from Polars is the runtime failure mode.
- Does NOT perform online section GID lookup — `SectionIndex` is built offline from either S3 manifest or `OfferSection` enum.

### Known Constraints and Failure Modes

**MRR inflation risk**: If `dedup_keys` is omitted or set incorrectly on an offer-domain metric, sums inflate by Offer count per Unit. No runtime enforcement beyond docstring comments in `definitions/offer.py`. Guard is documentation-only.

**Stall threshold computed at import time**: `_stall_filter(threshold_days=30)` computes `datetime.now(UTC) - timedelta(days=30)` at module-level when `lifecycle.py` is imported. If the process is long-running and `MetricRegistry._ensure_initialized()` triggered import hours/days ago, the cutoff is stale relative to wall-clock now. In CLI usage (single-invocation process) this is not an issue.

**Classification filter requires `section` column**: `compute_metric()` raises `ValueError` with message listing available columns if `section` is absent when `scope.classification` is set. This is a hard precondition for offer-domain metrics.

**`stage_transition` entity type unconfirmed**: The `stage_transition` entity type used by lifecycle metrics must be registered in `EntityRegistry` and have a DataFrame populated by `load_project_dataframe`. The registration path and DataFrame population path are not in the metrics package — they live in entity registration and data loading layers (not read; see Knowledge Gaps).

**S3 freshness probe vs. DataFrame load are separate S3 calls**: `load_project_dataframe` and `FreshnessReport.from_s3_listing` are independent calls to S3. The freshness report reflects the S3 state at the time of the listing call, which may differ slightly from the DataFrame actually loaded (a new write between the two calls would create inconsistency).

**SLA sidecar best-effort degradation**: `load_sidecar()` catches all boto3/botocore exceptions and returns `None` (fallback to manifest/defaults). A misconfigured sidecar is silently ignored with a WARN log — callers receive built-in defaults without knowing the sidecar was present but malformed.

**V-5 duplicate detection limitation** (sla_profile.py): YAML/JSON map parsers collapse duplicate keys to last-write-wins before `_build_sections_map` sees them. V-5 WARN code path is only reachable via programmatic map construction, not via file parse.

**`Scope` frozen dataclass with `list` fields**: `dedup_keys` and `pre_filters` are `list | None` typed but stored in a `@dataclass(frozen=True)`. This means the list contents are mutable even though the Scope reference is immutable. Callers should not mutate the lists post-construction.

**Metrics CLI Under-count (4 open questions from scar-tissue.md)**:
- **Bucket mapping**: The actual S3 bucket layout for `stage_transition` entity type and whether `load_project_dataframe` maps to the correct project GID is unverified.
- **Freshness SLA**: No SLA manifest entry exists for `stage_transition` section GIDs; all lifecycle metrics fall through to the `active` class default (6h).
- **Section-coverage gap**: `SectionCoverageDelta` computation uses `classifier.active_sections()` — the lifecycle domain has no registered classifier, so `_resolve_section_coverage_delta` returns 0 for lifecycle metrics.
- **Staleness-surface decision**: No decision on whether CLI staleness warnings should surface differently for lifecycle vs. offer metrics (same threshold logic applied to both).

### Interaction Points

- **`autom8_asana.dataframes.offline.load_project_dataframe`**: Only consumer of `compute_metric()` in the CLI path. Provides the input DataFrame. Not in metrics package.
- **`autom8_asana.models.business.activity.CLASSIFIERS`** and **`AccountActivity`**: Consumed by `compute_metric()` Step 0.5 to resolve sections for ACTIVE classification. If CLASSIFIERS does not contain the metric's `entity_type`, `ValueError` is raised.
- **`autom8_asana.cache.integration.force_warm.force_warm()`**: Only called by `--force-warm` CLI path; not called during normal metric computation.
- **`autom8_asana.cache.dataframe.factory.{get_dataframe_cache, initialize_dataframe_cache}`**: Only called by `_resolve_dataframe_cache_for_cli()` on the `--force-warm` path.
- **`autom8_asana.core.system_context.register_reset`**: `registry.py` calls this at module load to self-register `MetricRegistry.reset` for xdist test isolation.
- **`autom8_asana.models.business.sections.OfferSection`**: Used by `SectionIndex.from_enum_fallback("offer")` only. No other entity type supported.

### Configuration Boundaries

- `ASANA_CACHE_S3_BUCKET` (required for CLI): S3 bucket name for DataFrame and freshness probe.
- `ASANA_CACHE_S3_REGION` (required for CLI): S3 region; defaults to `us-east-1`.
- `CACHE_WARMER_LAMBDA_ARN` (required for `--force-warm`): Lambda function ARN/name.
- `AWS_REGION` or `ASANA_CACHE_S3_REGION`: Used by `cloudwatch_emit._get_cloudwatch_client()` for CloudWatch region resolution.
- `.know/cache-freshness-ttl-manifest.yaml`: Optional YAML TTL manifest (ADR-005 `SLA_MANIFEST_PATH`). Absent = silent fallback to built-in defaults.

```metadata
domain: feat/business-metrics
source_hash: "8980bcd7"
generated_at: "2026-05-08T00:00Z"
confidence: 0.93
criteria_grades:
  purpose_and_design_rationale:
    grade: A
    pct: 92
    weight: 0.30
  conceptual_model:
    grade: A
    pct: 95
    weight: 0.25
  implementation_map:
    grade: A
    pct: 95
    weight: 0.25
  boundaries_and_failure_modes:
    grade: A
    pct: 92
    weight: 0.20
overall_grade: A
overall_pct: 94
notes: >
  Full refresh from source_hash 8980bcd7. All 11 source files read directly.
  Prior version at c213958 (2026-04-01) had 4 knowledge gaps; 3 resolved this
  cycle (stage_transition scope details, classification filter mechanics,
  CLI force-warm path). One cluster of 4 open questions (Metrics CLI Under-count)
  remains unresolved — documented as open questions in Boundaries section.
  New content vs prior: sla_profile.py fully documented (validators V-1..V-6,
  4-class taxonomy, sidecar/manifest/default precedence); cloudwatch_emit.py
  documented with C-6 mechanical guard; CLI preflight contract (TDD-0001);
  force-warm delegation pattern (PT-2 Option B); FLAG-1 latency boundary;
  FreshnessReport.section_age_p95_seconds() documented; Scope frozen-list
  mutability hazard identified.
```
