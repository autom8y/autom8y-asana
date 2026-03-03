# PROMPT_0: ASANA_DATA Initiative

## Identity

**Initiative**: ASANA_DATA
**Objective**: Close the gap between the existing metrics/classification infrastructure and trivial CLI-driven business metric computation.
**Estimated effort**: 1.75 days across 4 workstreams.

## Business Motivation

The cofounder asked "Can you get up to date MRR number for meeting today?" Answering required writing two bespoke scripts (`scripts/calc_mrr.py`, `scripts/calc_weekly_ad_spend.py`) because the metrics layer cannot:

1. Express "all sections classified as active" (21 sections, not just literal ACTIVE)
2. Load data offline without platform dependencies (S3 persistence requires full DI stack)
3. Import classification data without pulling in `autom8y_cache` transitive deps
4. Run from CLI (`python -m autom8_asana.metrics active_mrr` does not exist)

The infrastructure to fix this is 80% built. `SectionClassifier.sections_for()`, `SectionPersistence.read_all_sections_async()`, `compute_metric()`, and `MetricRegistry` all exist. This initiative wires them together.

## Scope Boundary

### IN

- **WS-1**: Offline DataFrame loader (`dataframes/offline.py`) -- sync, no platform deps
- **WS-2**: Classification-aware `Scope` -- add `classification: str | None` field
- **WS-3**: Update ACTIVE_MRR / ACTIVE_AD_SPEND to use `classification="active"` instead of single-section GID
- **WS-4**: `metrics/__main__.py` CLI entry point

### OUT

- Parquet type fix (String -> Decimal) -- separate PR, requires cache rebuild (S5 from architect plan)
- Full QueryEngine offline mode -- QueryEngine already works offline via mock DataFrameProvider (see `scripts/demo_query_layer.py`)
- New metric definitions beyond active_mrr / active_ad_spend
- Removing the bespoke scripts (they remain as validation reference)

## Prior Art (reference, do not re-derive)

| Artifact | Path | Relevance |
|----------|------|-----------|
| Classification API surface analysis | `.claude/wip/ANALYSIS-classification-api-surface.md` | 3 disconnected surfaces, auth divergence, integration gap |
| Opportunity gap synthesis | `docs/architecture/ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md` | Opp-3 (classification config), Opp-4 (query DSL), Gap-4 (classification abstraction) |
| Bespoke MRR script | `scripts/calc_mrr.py` | Validation oracle -- must produce identical $96,126 |
| Bespoke ad spend script | `scripts/calc_weekly_ad_spend.py` | Second validation oracle |
| Demo query layer | `scripts/demo_query_layer.py` | Proves offline QueryEngine with mock DataFrameProvider |
| Offer metric definitions | `src/autom8_asana/metrics/definitions/offer.py` | Current single-section scoped metrics |
| SectionClassifier | `src/autom8_asana/models/business/activity.py` | OFFER_CLASSIFIER with 21 active sections |
| SectionPersistence | `src/autom8_asana/dataframes/section_persistence.py` | `read_all_sections_async()` exists |
| QueryEngine | `src/autom8_asana/query/engine.py` | `_resolve_classification()` already works |
| Scope model | `src/autom8_asana/metrics/metric.py` | Current: `section: str | None`, no classification |
| compute_metric | `src/autom8_asana/metrics/compute.py` | 6-step pipeline, does NOT handle classification |
| MetricRegistry | `src/autom8_asana/metrics/registry.py` | Singleton, lazy init, 2 metrics registered |
| DataFrameProvider protocol | `src/autom8_asana/protocols/dataframe_provider.py` | Requires AsanaClient param |

## Workstream Definitions

### WS-1: Offline DataFrame Loader (0.5d)

**Goal**: Extract a sync `load_project_dataframe(project_gid, bucket, region) -> pl.DataFrame` that reads all section parquets from S3 without importing any platform module.

**Files to create**:
- `src/autom8_asana/dataframes/offline.py`

**Files to read** (not modify):
- `src/autom8_asana/dataframes/section_persistence.py` (for S3 key structure reference)

**Contract**:
```python
# BEFORE: scripts/calc_mrr.py lines 86-111
# Manual boto3 list + read + concat, 25 lines of boilerplate

# AFTER: dataframes/offline.py
def load_project_dataframe(
    project_gid: str,
    *,
    bucket: str | None = None,  # falls back to ASANA_CACHE_S3_BUCKET
    region: str = "us-east-1",
) -> pl.DataFrame:
    """Load all section parquets for a project, concatenated.

    Sync, no platform deps. Uses boto3 directly.
    Key structure: dataframes/{project_gid}/sections/*.parquet
    Concat strategy: how="diagonal_relaxed" (matches SectionPersistence)
    """
```

**Imports allowed**: `boto3`, `polars`, `io`, `os` -- nothing from `autom8_asana` except constants.

**Verification**:
```bash
python -c "
from autom8_asana.dataframes.offline import load_project_dataframe
df = load_project_dataframe('1143843662099250')
print(f'{len(df)} rows, {df.columns}')
"
```

### WS-2: Classification-Aware Scope (0.5d)

**Goal**: Add `classification: str | None` to `Scope` so metrics can express "all active-classified sections" without hardcoding GIDs.

**Files to modify**:
- `src/autom8_asana/metrics/metric.py` -- add field to Scope
- `src/autom8_asana/metrics/compute.py` -- resolve classification before dedup

**Contract**:
```python
# BEFORE: Scope only has section: str | None (single GID)
@dataclass(frozen=True)
class Scope:
    entity_type: str
    section: str | None = None
    section_name: str | None = None
    classification: str | None = None  # NEW
    dedup_keys: list[str] | None = None
    pre_filters: list[pl.Expr] | None = None

# AFTER: compute_metric accepts full DataFrame, filters by classification
def compute_metric(
    metric: Metric,
    df: pl.DataFrame,
    *,
    verbose: bool = False,
) -> pl.DataFrame:
    # NEW step between current Step 1 and Step 2:
    # If scope.classification is set, filter df to matching sections
    # using SectionClassifier.sections_for(AccountActivity(classification))
```

**Classification resolution** (reuse existing code from `QueryEngine._resolve_classification`):
```python
from autom8_asana.models.business.activity import CLASSIFIERS, AccountActivity
classifier = CLASSIFIERS[scope.entity_type]
sections = classifier.sections_for(AccountActivity(scope.classification))
df = df.filter(pl.col("section").str.to_lowercase().is_in(list(sections)))
```

**Verification**: Existing tests pass (Scope is backward-compatible: `classification=None` is no-op).

### WS-3: Update Metric Definitions (0.25d)

**Goal**: Change ACTIVE_MRR and ACTIVE_AD_SPEND from single-section scope to classification scope.

**Files to modify**:
- `src/autom8_asana/metrics/definitions/offer.py`

**Contract**:
```python
# BEFORE (line 21-26):
_ACTIVE_OFFER_SCOPE = Scope(
    entity_type="offer",
    section=OfferSection.ACTIVE.value,  # single GID
    section_name="Active",
    dedup_keys=["office_phone", "vertical"],
)

# AFTER:
_ACTIVE_OFFER_SCOPE = Scope(
    entity_type="offer",
    classification="active",  # 21 sections via OFFER_CLASSIFIER
    dedup_keys=["office_phone", "vertical"],
)
```

**Verification**: `compute_metric(ACTIVE_MRR, full_df)` on full offer DataFrame produces same $96,126 as `scripts/calc_mrr.py`.

### WS-4: CLI Entry Point (0.5d)

**Goal**: `python -m autom8_asana.metrics active_mrr` prints the metric value.

**Files to create**:
- `src/autom8_asana/metrics/__main__.py`

**Contract**:
```python
# Usage:
#   python -m autom8_asana.metrics active_mrr
#   python -m autom8_asana.metrics active_mrr --verbose
#   python -m autom8_asana.metrics --list
#
# Flow:
#   1. Parse args (metric name, --verbose, --list, --project-gid override)
#   2. MetricRegistry.get_metric(name)
#   3. load_project_dataframe(project_gid)  # from WS-1
#   4. compute_metric(metric, df, verbose=verbose)  # enhanced in WS-2
#   5. Aggregate and print result
```

**Dependencies**: WS-1 (offline loader), WS-2 (classification scope), WS-3 (updated definitions).

**Verification**:
```bash
python -m autom8_asana.metrics active_mrr
# Output: active_mrr: $96,126.00

python -m autom8_asana.metrics active_ad_spend
# Output: active_ad_spend: $X,XXX.XX

python -m autom8_asana.metrics --list
# Output:
#   active_mrr        Total MRR for ACTIVE offers, deduped by phone+vertical
#   active_ad_spend   Total weekly ad spend for ACTIVE offers, deduped by phone+vertical
```

## Hard Constraints

1. **Zero merge conflicts**: Each workstream has exclusive file-scope contracts (see REMEDIATION-PLAN.md).
2. **No platform dep imports in offline path**: `dataframes/offline.py` must not import from `autom8_asana.config`, `autom8_asana.settings`, `autom8_asana.cache`, or `autom8y_cache`. Only `boto3`, `polars`, `io`, `os`, and optionally `autom8_asana.models.business.activity` (pure data, no I/O deps).
3. **Existing test suite must pass**: `pytest tests/unit/metrics/` must remain green after all changes.
4. **MRR oracle**: Final `python -m autom8_asana.metrics active_mrr` must produce $96,126 (same as `scripts/calc_mrr.py` against Feb 22 parquets).
5. **Backward compatibility**: `Scope(entity_type="offer", section="...")` must continue to work unchanged. `classification=None` is the default, preserving all existing behavior.

## Dependency Graph

```
WS-1 (offline loader)  ──────────────────────────┐
WS-2 (classification scope) ──┬──> WS-3 (defs) ──┼──> WS-4 (CLI)
                              │                   │
                              └───────────────────┘
```

- WS-1 and WS-2 are **independent** (can run in parallel).
- WS-3 depends on WS-2 (needs classification field on Scope).
- WS-4 depends on WS-1 + WS-3 (needs both offline loader and updated definitions).

## Execution Mode

**Native** or **Cross-Cutting** -- no rite coordination needed. 4 small workstreams, 1 developer, sequential or parallel-2.

## Project GID Reference

| Entity | Project GID | Source |
|--------|-------------|--------|
| Offer | `1143843662099250` | `OFFER_CLASSIFIER.project_gid` in `activity.py:184` |
| Unit | `1201081073731555` | `UNIT_CLASSIFIER.project_gid` in `activity.py:232` |

## Success Criteria

1. `python -m autom8_asana.metrics active_mrr` outputs `$96,126` (within rounding tolerance)
2. `python -m autom8_asana.metrics active_ad_spend` outputs a value matching `scripts/calc_weekly_ad_spend.py`
3. `python -m autom8_asana.metrics --list` shows both metrics with descriptions
4. `pytest tests/unit/metrics/` passes with zero regressions
5. No new imports from platform modules (`autom8y_cache`, `autom8_asana.config`, `autom8_asana.settings`) in `dataframes/offline.py`
