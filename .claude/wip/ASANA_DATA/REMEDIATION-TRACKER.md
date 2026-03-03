# ASANA_DATA Remediation Tracker

## Initiative Summary

| Field | Value |
|-------|-------|
| Initiative | ASANA_DATA |
| Start | 2026-02-24 |
| Target | 1.75 days |
| Status | IMPLEMENTATION COMPLETE (pending oracle validation) |
| Oracle | `scripts/calc_mrr.py` -> $96,126 |

## Workstream Status

| WS | Name | Phase | Status | Files | Notes |
|----|------|-------|--------|-------|-------|
| WS-1 | Offline DataFrame loader | Phase 1 | DONE | `dataframes/offline.py` (create), `tests/unit/dataframes/test_offline.py` (create) | 7 tests, paginated S3 listing |
| WS-2 | Classification-aware Scope | Phase 1 | DONE | `metrics/metric.py`, `metrics/compute.py` (modify), test_compute.py, test_metric.py (modify) | Step 0.5 filter, 8 new tests |
| WS-3 | Update metric definitions | Phase 2 | DONE | `metrics/definitions/offer.py` (modify), test_definitions.py, test_adversarial.py, test_edge_cases.py (modify) | Removed OfferSection dep |
| WS-4 | CLI entry point | Phase 3 | DONE | `metrics/__main__.py` (create), test_main.py (create), `scripts/calc_metric.py` (delete) | 6 tests |

## Phase Gates

### Phase 1: WS-1 + WS-2 (parallel)

- [x] WS-1: `load_project_dataframe()` implemented and tested (7 tests)
- [x] WS-1: No platform dep imports verified
- [x] WS-2: `Scope.classification` field added, defaults to None
- [x] WS-2: `compute_metric` handles classification filter (Step 0.5)
- [x] WS-2: `pytest tests/unit/metrics/test_compute.py tests/unit/metrics/test_metric.py` passes
- [x] Phase 1 gate: 33/33 passed

### Phase 2: WS-3

- [x] WS-3: `_ACTIVE_OFFER_SCOPE` uses `classification="active"`
- [x] WS-3: `OfferSection` import removed from `definitions/offer.py`
- [x] WS-3: `pytest tests/unit/metrics/` passes
- [x] Phase 2 gate: 154/154 passed

### Phase 3: WS-4

- [x] WS-4: `python -m autom8_asana.metrics --list` works (test verified)
- [ ] WS-4: `python -m autom8_asana.metrics active_mrr` matches oracle (needs S3 access)
- [ ] WS-4: `python -m autom8_asana.metrics active_ad_spend` matches oracle (needs S3 access)
- [x] WS-4: `pytest tests/unit/metrics/` passes (including new test_main.py)
- [x] Phase 3 gate: 167/167 passed

## Test Baseline

| Metric | Value | Date |
|--------|-------|------|
| `pytest tests/unit/metrics/ + test_offline.py` | 33 passed | Phase 1 |
| `pytest tests/unit/metrics/` | 154 passed | Phase 2 |
| `pytest tests/unit/metrics/ + test_offline.py` | 167 passed | Phase 3 |

## Deviations

| # | Description | Decision | Impact |
|---|-------------|----------|--------|
| 1 | Step 0.5 instead of Step 1.5 for classification filter | Architect-confirmed: filter before column select is cleaner, matches QueryEngine | Simpler code, no column add/drop |
| 2 | Added paginator to offline loader (not in original PROMPT_0) | User directive: contacts have 20k+ records, future entity types may have 1000+ sections | Future-proof, minimal code cost |
| 3 | Deleted scripts/calc_metric.py (not in original PROMPT_0) | User directive: no consumers, __main__.py supersedes it | Cleaner, no duplicate CLIs |
| 4 | Updated test_adversarial.py and test_edge_cases.py | Required: tests referenced deleted script and old scope.section assertions | 4 assertion updates + 6 subprocess command updates |
