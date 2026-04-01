---
domain: feat/business-metrics
generated_at: "2026-04-01T16:45:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/metrics/**/*.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.91
format_version: "1.0"
---

# Business Metrics Computation (MRR, Ad Spend)

## Purpose and Design Rationale

Declarative, data-pipeline-independent system for computing business scalar metrics from Polars DataFrames. Primary metrics: **MRR** (Monthly Recurring Revenue) and **Ad Spend**, both summed across ACTIVE-classified offer rows, deduplicated by `(office_phone, vertical)` to prevent inflation from multiple Offers per Unit.

Also supports lifecycle pipeline metrics (conversion counts, duration stats, stall detection, throughput) operating on `stage_transition` entity type.

CLI entry: `python -m autom8_asana.metrics`. No REST API route -- offline/CLI only.

## Conceptual Model

### Declarative Pipeline Composition

```
MetricExpr  -- WHAT (column, cast, filter, aggregation)
Scope       -- WHERE (entity type, section, dedup keys, classification)
Metric      -- NAME + description binding expr to scope
```

`compute_metric()` runs a fixed 6-step pipeline: select columns -> cast dtype -> apply expr filter -> apply scope pre_filters -> deduplicate by keys -> sort. Returns filtered DataFrame; caller aggregates.

### Deduplication (Domain-Critical)

`(office_phone, vertical)` dedup encodes the invariant: MRR and ad spend live at Unit level, not Offer level. Without it, sums inflate by Offer count per Unit.

### Registered Metrics

**Offer domain**: `active_mrr` (sum of mrr, ACTIVE, dedup PVP), `active_ad_spend` (sum of weekly_ad_spend, ACTIVE, dedup PVP).

**Lifecycle domain**: 3 conversion counts (outreach->sales, sales->onboarding, onboarding->implementation), `stage_duration_median`, `stage_duration_p95`, `stalled_entities` (>30 days, null exited_at), `weekly_transitions`.

### Section Resolution: Offline-First

S3 manifest via `SectionPersistence.get_manifest_async()`, fallback to `OfferSection` enum for the offer entity type.

### Singleton Registry with Lazy Init

`MetricRegistry` follows singleton pattern (ADR-0093). Definition modules loaded lazily on first `get_metric()`. Integrates with `SystemContext.reset_all()` for test isolation.

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_asana/metrics/metric.py` | `Scope` and `Metric` frozen dataclasses |
| `src/autom8_asana/metrics/expr.py` | `MetricExpr` with `to_polars_expr()` and `SUPPORTED_AGGS` (7 functions) |
| `src/autom8_asana/metrics/compute.py` | 6-step pipeline with `@trace_computation` OTel decorator |
| `src/autom8_asana/metrics/registry.py` | Singleton registry with lazy definition loading |
| `src/autom8_asana/metrics/resolve.py` | `SectionIndex` (case-insensitive name->GID) + `resolve_metric_scope()` |
| `src/autom8_asana/metrics/definitions/offer.py` | `ACTIVE_MRR`, `ACTIVE_AD_SPEND` definitions |
| `src/autom8_asana/metrics/definitions/lifecycle.py` | 7 lifecycle pipeline metrics |
| `src/autom8_asana/metrics/__main__.py` | CLI: argparse, `--list`, `--verbose`, `--project-gid` |

**Supported aggregations**: sum, count, mean, min, max, median, quantile (requires `quantile_value` float).

**10 test files** in `tests/unit/metrics/` with adversarial and edge-case coverage.

## Boundaries and Failure Modes

### Isolation

- Does NOT import from `services/`, `clients/`, or `api/` -- pure Domain Layer
- Accepts any `pl.DataFrame` with required columns; agnostic to data source
- No REST route -- CLI/offline only

### Known Constraints

- **MRR inflation risk**: If `dedup_keys` omitted or wrong, sums inflate. No runtime enforcement beyond comments in `definitions/offer.py`.
- **Stall threshold hardcoded**: `_stall_filter(threshold_days=30)` computes cutoff at module import time. Stale if module cached across long-running processes.
- **Classification filter** requires `"section"` column in DataFrame.

## Knowledge Gaps

1. `autom8_asana.dataframes.offline.load_project_dataframe` implementation not read.
2. `stage_transition` entity type registration and DataFrame population path unknown.
3. No REST API route -- whether by design or gap not confirmed.
4. `AccountActivity` enum values and classification-to-section mapping detail not documented.
