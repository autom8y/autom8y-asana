# ASANA_DATA Remediation Plan

## Gap-to-Workstream Mapping

| ID | Gap Description | Root Cause | Workstream |
|----|----------------|------------|------------|
| G-1 | No sync offline loader | `SectionPersistence.read_all_sections_async()` requires platform DI stack (`create_section_persistence()` imports settings, config, S3DataFrameStorage) | WS-1 |
| G-2 | Scope cannot express classification groups | `Scope.section: str` is a single GID; "active" is 21 sections | WS-2 |
| G-3 | Metric definitions hardcode single-section GID | `_ACTIVE_OFFER_SCOPE` uses `OfferSection.ACTIVE.value` (1 section) instead of OFFER_CLASSIFIER "active" group (21 sections) | WS-3 |
| G-4 | No CLI entry point | `metrics/` package has no `__main__.py` | WS-4 |
| G-5 | Classification data not importable standalone | `activity.py` imports are clean (no platform deps), but consumers don't know this -- scripts inline the 40+ section names | Closed by WS-1 + WS-2 (offline.py proves the import is safe; Scope.classification makes it unnecessary to import directly) |

## Before/After Contracts

### WS-1: Offline DataFrame Loader

**Before** -- `scripts/calc_mrr.py` lines 86-111:
```python
# 25 lines of manual boto3: list_objects_v2 + get_object + read_parquet + concat
def list_section_parquets(s3_client, bucket, project_gid) -> list[str]: ...
def load_all_sections(s3_client, bucket, project_gid) -> pl.DataFrame: ...
```
Every new script must copy this boilerplate. Key structure is hardcoded.

**After** -- `src/autom8_asana/dataframes/offline.py`:
```python
def load_project_dataframe(
    project_gid: str,
    *,
    bucket: str | None = None,
    region: str = "us-east-1",
) -> pl.DataFrame:
    """One-call sync loader. S3 key structure matches SectionPersistence."""
```
- Env fallback: `ASANA_CACHE_S3_BUCKET`
- Key prefix: `dataframes/{project_gid}/sections/*.parquet`
- Concat: `pl.concat(..., how="diagonal_relaxed")` (matches `SectionPersistence.merge_sections_to_dataframe_async`)
- Error: raises `FileNotFoundError` if no parquets found (not `sys.exit`)

### WS-2: Classification-Aware Scope

**Before** -- `src/autom8_asana/metrics/metric.py:19-49`:
```python
@dataclass(frozen=True)
class Scope:
    entity_type: str
    section: str | None = None
    section_name: str | None = None
    dedup_keys: list[str] | None = None
    pre_filters: list[pl.Expr] | None = None
```

**After**:
```python
@dataclass(frozen=True)
class Scope:
    entity_type: str
    section: str | None = None
    section_name: str | None = None
    classification: str | None = None  # NEW: "active", "activating", "inactive", "ignored"
    dedup_keys: list[str] | None = None
    pre_filters: list[pl.Expr] | None = None
```

**Before** -- `src/autom8_asana/metrics/compute.py:17-103` (no classification awareness):
```python
def compute_metric(metric, df, *, verbose=False) -> pl.DataFrame:
    # Step 1: Select columns
    # Step 2: Cast
    # Step 3: Filter (MetricExpr.filter_expr)
    # Step 4: Pre-filters
    # Step 5: Dedup
    # Step 6: Sort
```

**After** -- new Step 1.5 inserted:
```python
def compute_metric(metric, df, *, verbose=False) -> pl.DataFrame:
    # Step 1: Select columns
    # Step 1.5 (NEW): Classification filter
    if scope.classification is not None:
        from autom8_asana.models.business.activity import CLASSIFIERS, AccountActivity
        classifier = CLASSIFIERS.get(scope.entity_type)
        if classifier is None:
            raise ValueError(f"No classifier for entity type '{scope.entity_type}'")
        sections = classifier.sections_for(AccountActivity(scope.classification))
        result = result.filter(
            pl.col("section").str.to_lowercase().is_in(list(sections))
        )
    # Step 2: Cast (unchanged)
    # ...
```

Note: The `section` column must be present in the DataFrame for classification filtering. The select_cols list in Step 1 must include `"section"` when classification is set, then drop it after filtering if it was not originally requested.

### WS-3: Update Metric Definitions

**Before** -- `src/autom8_asana/metrics/definitions/offer.py:21-26`:
```python
_ACTIVE_OFFER_SCOPE = Scope(
    entity_type="offer",
    section=OfferSection.ACTIVE.value,
    section_name="Active",
    dedup_keys=["office_phone", "vertical"],
)
```

**After**:
```python
_ACTIVE_OFFER_SCOPE = Scope(
    entity_type="offer",
    classification="active",
    dedup_keys=["office_phone", "vertical"],
)
```

- Removes `section` and `section_name` (replaced by `classification`)
- Removes `OfferSection` import (no longer needed)
- The scope now captures 21 sections instead of 1

### WS-4: CLI Entry Point

**Before**: No `metrics/__main__.py`. Running metrics requires importing and calling `compute_metric()` programmatically.

**After** -- `src/autom8_asana/metrics/__main__.py`:
```
Usage:
  python -m autom8_asana.metrics active_mrr
  python -m autom8_asana.metrics active_mrr --verbose
  python -m autom8_asana.metrics --list

Flow:
  1. argparse: metric_name (positional), --verbose, --list, --project-gid
  2. --list: print registry.list_metrics() with descriptions, exit
  3. registry.get_metric(metric_name)
  4. Resolve project_gid from metric.scope.entity_type (hardcoded map or CLASSIFIERS)
  5. load_project_dataframe(project_gid)  # WS-1
  6. compute_metric(metric, df, verbose=verbose)  # WS-2 enhanced
  7. Aggregate: result[metric.expr.column].agg(metric.expr.agg)
  8. Print: f"{metric.name}: ${value:,.2f}"
```

Project GID resolution: use `CLASSIFIERS[entity_type].project_gid` from `activity.py`. This is pure data, no I/O.

## File-Scope Contracts

Each workstream has **exclusive** write access to its files. No two workstreams modify the same file.

| File | WS-1 | WS-2 | WS-3 | WS-4 |
|------|------|------|------|------|
| `src/autom8_asana/dataframes/offline.py` | **CREATE** | | | |
| `src/autom8_asana/metrics/metric.py` | | **MODIFY** | | |
| `src/autom8_asana/metrics/compute.py` | | **MODIFY** | | |
| `src/autom8_asana/metrics/definitions/offer.py` | | | **MODIFY** | |
| `src/autom8_asana/metrics/__main__.py` | | | | **CREATE** |

Read-only references (any workstream may read):
- `src/autom8_asana/models/business/activity.py` -- classification data
- `src/autom8_asana/dataframes/section_persistence.py` -- S3 key structure
- `src/autom8_asana/metrics/registry.py` -- MetricRegistry API
- `scripts/calc_mrr.py` -- validation oracle

## Dependency Ordering

```
Phase 1 (parallel):  WS-1, WS-2
Phase 2 (sequential): WS-3 (requires WS-2)
Phase 3 (sequential): WS-4 (requires WS-1 + WS-3)
```

**Parallel opportunity**: WS-1 and WS-2 touch zero shared files. Can run in separate worktrees or sequential in one session.

**Integration checkpoint after Phase 2**: Run `pytest tests/unit/metrics/` to verify backward compatibility before WS-4.

## Test Strategy

### New Tests

| Test | File | Workstream | What it verifies |
|------|------|------------|------------------|
| `test_load_project_dataframe_missing_bucket` | `tests/unit/dataframes/test_offline.py` | WS-1 | Raises ValueError when no bucket configured |
| `test_load_project_dataframe_no_parquets` | `tests/unit/dataframes/test_offline.py` | WS-1 | Raises FileNotFoundError when prefix empty |
| `test_load_project_dataframe_concat` | `tests/unit/dataframes/test_offline.py` | WS-1 | Concatenates multiple parquets with diagonal_relaxed |
| `test_scope_classification_field` | `tests/unit/metrics/test_metric.py` | WS-2 | Scope accepts classification, defaults to None |
| `test_compute_metric_with_classification` | `tests/unit/metrics/test_compute.py` | WS-2 | classification filter applied before dedup |
| `test_compute_metric_classification_none_noop` | `tests/unit/metrics/test_compute.py` | WS-2 | classification=None does not alter behavior |
| `test_active_mrr_uses_classification` | `tests/unit/metrics/test_metric.py` | WS-3 | ACTIVE_MRR scope has classification="active" |
| `test_cli_list` | `tests/unit/metrics/test_main.py` | WS-4 | --list outputs metric names |
| `test_cli_unknown_metric` | `tests/unit/metrics/test_main.py` | WS-4 | Unknown metric name exits with error |

### Existing Tests to Verify

| Test File | Must Pass | Reason |
|-----------|-----------|--------|
| `tests/unit/metrics/test_compute.py` | Yes | compute_metric backward compat |
| `tests/unit/metrics/test_metric.py` | Yes | Scope/Metric model compat |
| `tests/unit/cache/test_metrics.py` | Yes | MetricRegistry integration |

### Integration Validation (manual)

```bash
# Oracle comparison
python scripts/calc_mrr.py                    # produces $96,126
python -m autom8_asana.metrics active_mrr     # must match

python scripts/calc_weekly_ad_spend.py        # produces $X,XXX
python -m autom8_asana.metrics active_ad_spend  # must match
```

## Rollback Strategy

Each workstream is independently revertible because file-scope contracts prevent cross-contamination.

| Workstream | Rollback Action | Side Effects |
|------------|----------------|--------------|
| WS-1 | Delete `dataframes/offline.py` | None -- no existing code depends on it |
| WS-2 | Revert `metric.py` + `compute.py` | WS-3 and WS-4 must also revert |
| WS-3 | Revert `definitions/offer.py` | Metrics revert to single-section scope; WS-4 must also revert |
| WS-4 | Delete `metrics/__main__.py` | None -- no existing code depends on it |

**Full rollback**: Revert in reverse order (WS-4, WS-3, WS-2, WS-1). Each step is a single `git revert` of the workstream's commit.

## Edge Cases and Risks

| Risk | Mitigation |
|------|------------|
| `section` column missing from parquet | `compute_metric` should raise clear error: "classification requires 'section' column in DataFrame" |
| Classification string case sensitivity | Normalize to lowercase in `compute_metric` (matches `QueryEngine._resolve_classification` pattern) |
| Parquet String-typed MRR values | Already handled: `MetricExpr.cast_dtype=pl.Float64` + `strict=False` in `compute_metric` Step 2 |
| Empty classification group | Propagate empty frozenset -- result is 0 rows, metric value is 0 or null. Log warning. |
| boto3 not installed in test env | WS-1 tests mock boto3 client; offline.py import guarded by try/except at call time, not module level |
