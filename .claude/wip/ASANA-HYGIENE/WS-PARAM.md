# WS-PARAM: Parametrize Copy-Paste Test Clusters

**Finding IDs**: LS-009 through LS-024 (16 clusters)
**Severity**: SMELL
**Estimated Effort**: 4-6 hours
**Dependencies**: None (independent)
**Lane**: B

---

## Scope

Convert 16 copy-paste test clusters to `@pytest.mark.parametrize`. Each cluster has N nearly-identical test functions that differ only in input values. Parametrization preserves all test coverage while reducing ~600-800 LOC.

---

## Target Files (16 clusters, sorted by LOC savings)

### Cluster 1: LS-011 -- Schema column definitions (highest LOC savings)
- **File**: `tests/unit/dataframes/test_unit_schema.py`
- **Pattern**: 10 tests, ~6 lines each, differ only in column name and dtype
- **Fix**: `@pytest.mark.parametrize("col,dtype", [...])` single test function

### Cluster 2: LS-016 -- Phone and domain normalizers
- **File**: `tests/unit/models/business/matching/test_normalizers.py`
- **Pattern**: 9 tests, ~5 lines each, differ in input/expected for phone + domain
- **Fix**: Two parametrize groups (phone normalization, domain normalization)

### Cluster 3: LS-012 -- Error helper formatting
- **File**: `tests/unit/api/test_error_helpers.py`
- **Pattern**: 7 tests, ~6 lines each, differ in error type/message
- **Fix**: `@pytest.mark.parametrize("error_class,expected_msg", [...])`

### Cluster 4: LS-013 -- Client extension case handling
- **File**: `tests/unit/clients/data/test_client_extensions.py`
- **Pattern**: 7 tests, ~5 lines each, differ in case input
- **Fix**: `@pytest.mark.parametrize("input_case,expected", [...])`

### Cluster 5: LS-019 -- Custom field descriptors
- **File**: `tests/unit/models/business/test_custom_field_descriptors.py`
- **Pattern**: 7 tests, ~5 lines each, differ in field type
- **Fix**: `@pytest.mark.parametrize("field_type,expected", [...])`

### Cluster 6: LS-015 -- Executor resource paths
- **File**: `tests/unit/persistence/test_executor.py`
- **Pattern**: 6 tests, ~6 lines each, differ in resource path
- **Fix**: `@pytest.mark.parametrize("resource_path", [...])`

### Cluster 7: LS-018 -- Dataframes schema entity types
- **File**: `tests/unit/api/test_routes_dataframes.py`
- **Pattern**: 5 tests, ~13 lines each, differ in entity type
- **Fix**: `@pytest.mark.parametrize("entity_type", [...])`

### Cluster 8: LS-020 -- Base schema column definitions
- **File**: `tests/unit/dataframes/test_base_schema.py`
- **Pattern**: 5 tests, ~7 lines each, differ in column/dtype
- **Fix**: `@pytest.mark.parametrize("col,dtype", [...])`

### Cluster 9: LS-021 -- PII phone format masking
- **File**: `tests/unit/clients/data/test_pii.py`
- **Pattern**: 5 tests, ~7 lines each, differ in phone format
- **Fix**: `@pytest.mark.parametrize("phone_format", [...])`

### Cluster 10: LS-009 -- Cache stale fallback status codes
- **File**: `tests/unit/clients/data/test_cache.py`
- **Pattern**: 4 tests, ~40 lines each, differ only in HTTP status code
- **Fix**: `@pytest.mark.parametrize("status_code", [400, 404, 500, 503])`

### Cluster 11: LS-010 -- Feature flag env values
- **File**: `tests/unit/clients/data/test_feature_flag.py`
- **Pattern**: 4 tests, ~32 lines each, differ in env var value
- **Fix**: `@pytest.mark.parametrize("env_value,expected", [...])`

### Cluster 12: LS-014 -- Retryable status codes
- **File**: `tests/unit/clients/data/test_models.py`
- **Pattern**: 4 tests, ~15 lines each, differ in status code
- **Fix**: `@pytest.mark.parametrize("status_code,is_retryable", [...])`

### Cluster 13: LS-022 -- Session healing tiers
- **File**: `tests/unit/persistence/test_session_healing.py`
- **Pattern**: 4 tests, ~8 lines each, differ in healing tier
- **Fix**: `@pytest.mark.parametrize("tier", [...])`

### Cluster 14: LS-023 -- Config sections
- **File**: `tests/unit/automation/test_config.py`
- **Pattern**: 4 tests, ~7 lines each, differ in config section name
- **Fix**: `@pytest.mark.parametrize("section", [...])`

### Cluster 15: LS-024 -- Config schema time values
- **File**: `tests/unit/automation/polling/test_config_schema.py`
- **Pattern**: 4 tests, ~6 lines each, differ in time value
- **Fix**: `@pytest.mark.parametrize("time_value", [...])`

### Cluster 16: LS-017 -- Admin edge case route inputs
- **File**: `tests/unit/api/test_routes_admin_edge_cases.py`
- **Pattern**: 3 tests, ~21 lines each, differ in input payload
- **Fix**: `@pytest.mark.parametrize("payload,expected_status", [...])`

---

## Objective

**Done when**:
- All 16 clusters converted to `@pytest.mark.parametrize`
- Net LOC reduction of 400+ lines (conservative target; report estimates 600-800)
- All parametrized tests pass
- Test count is identical or higher (parametrize generates same number of test cases)
- Zero regressions in any other tests in the affected files

---

## Execution Strategy

Work through clusters in the order listed (highest LOC savings first). For each cluster:
1. Read the file, identify the copy-paste functions
2. Extract the varying parameters into a parametrize tuple list
3. Write single parametrized test function
4. Delete the N original functions
5. Run scoped verification before moving to next cluster

---

## Constraints

- **Test-only changes**: Do NOT modify any production source files
- **Preserve test IDs**: Use `pytest.param(..., id="descriptive_name")` so test names remain readable
- **Preserve coverage**: Every original test case must have a corresponding parametrize entry
- **Do NOT change test logic**: Only extract parameters. Do not "improve" assertions or add new cases.
- **One file at a time**: Complete and verify each file before moving to the next

---

## Context References

- **Finding details**: `.claude/wip/SLOP-CHOP-TESTS-P1/phase2-analysis/ANALYSIS-REPORT.md` (SMELL section, LS-009 to LS-024 table)
- **No remediation instructions exist** -- these were deferred. This workstream produces the fixes.

---

## Verification

After each file:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest <modified_file> -n auto -q --tb=short
```

After all 16 clusters:
```bash
# Full verification across all 16 files
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest \
  tests/unit/dataframes/test_unit_schema.py \
  tests/unit/models/business/matching/test_normalizers.py \
  tests/unit/api/test_error_helpers.py \
  tests/unit/clients/data/test_client_extensions.py \
  tests/unit/models/business/test_custom_field_descriptors.py \
  tests/unit/persistence/test_executor.py \
  tests/unit/api/test_routes_dataframes.py \
  tests/unit/dataframes/test_base_schema.py \
  tests/unit/clients/data/test_pii.py \
  tests/unit/clients/data/test_cache.py \
  tests/unit/clients/data/test_feature_flag.py \
  tests/unit/clients/data/test_models.py \
  tests/unit/persistence/test_session_healing.py \
  tests/unit/automation/test_config.py \
  tests/unit/automation/polling/test_config_schema.py \
  tests/unit/api/test_routes_admin_edge_cases.py \
  -n auto -q --tb=short
```

LOC delta check:
```bash
# Before starting, count total lines across all 16 files
wc -l tests/unit/dataframes/test_unit_schema.py \
  tests/unit/models/business/matching/test_normalizers.py \
  tests/unit/api/test_error_helpers.py \
  tests/unit/clients/data/test_client_extensions.py \
  tests/unit/models/business/test_custom_field_descriptors.py \
  tests/unit/persistence/test_executor.py \
  tests/unit/api/test_routes_dataframes.py \
  tests/unit/dataframes/test_base_schema.py \
  tests/unit/clients/data/test_pii.py \
  tests/unit/clients/data/test_cache.py \
  tests/unit/clients/data/test_feature_flag.py \
  tests/unit/clients/data/test_models.py \
  tests/unit/persistence/test_session_healing.py \
  tests/unit/automation/test_config.py \
  tests/unit/automation/polling/test_config_schema.py \
  tests/unit/api/test_routes_admin_edge_cases.py
# Record this number. After completion, re-run and verify delta >= 400 lines.
```
