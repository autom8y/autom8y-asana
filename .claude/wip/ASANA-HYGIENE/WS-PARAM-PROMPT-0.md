# WS-PARAM Session Prompt

## Rite & Workflow
- Rite: hygiene
- Workflow: `/task`
- Complexity: MODULE
- Sessions: 2 (this prompt covers Session 1; Session 2 uses the checkpoint)

## Objective

Parametrize 8 copy-paste test clusters (Session 1: LS-011 to LS-016, LS-019, LS-020) into `@pytest.mark.parametrize` calls, reducing ~400 LOC while preserving every test case. Session 2 handles the remaining 8 clusters.

## Context

Slop-chop quality gate on `tests/unit/` (Partition 1) identified 16 copy-paste clusters -- groups of nearly-identical test functions that differ only in input values. All 16 were deferred as SMELL findings. This workstream resolves them via parametrization.

- Seed doc: `.claude/wip/ASANA-HYGIENE/WS-PARAM.md`
- Finding details: `.claude/wip/SLOP-CHOP-TESTS-P1/phase2-analysis/ANALYSIS-REPORT.md` (LS-009 to LS-024 table)

## Scope

### IN SCOPE -- Session 1 (8 clusters, simpler patterns)

| ID | File | Tests | Lines Each | Parametrize On |
|----|------|-------|-----------|----------------|
| LS-011 | `tests/unit/dataframes/test_unit_schema.py` | 10 | ~6 | column name, dtype |
| LS-012 | `tests/unit/api/test_error_helpers.py` | 7 | ~6 | error class, expected message |
| LS-013 | `tests/unit/clients/data/test_client_extensions.py` | 7 | ~5 | case input, expected output |
| LS-014 | `tests/unit/clients/data/test_models.py` | 4 | ~15 | status code, is_retryable flag |
| LS-015 | `tests/unit/persistence/test_executor.py` | 6 | ~6 | resource path |
| LS-016 | `tests/unit/models/business/matching/test_normalizers.py` | 9 | ~5 | input/expected (two groups: phone, domain) |
| LS-019 | `tests/unit/models/business/test_custom_field_descriptors.py` | 7 | ~5 | field type, expected |
| LS-020 | `tests/unit/dataframes/test_base_schema.py` | 5 | ~7 | column, dtype |

### OUT OF SCOPE

- Session 2 clusters: LS-009, LS-010, LS-017, LS-018, LS-021 to LS-024
- Any production source files (test-only changes)
- Adding new test cases (only extract existing cases into parametrize)
- Changing test logic or assertions (only extract the varying parameter)
- Other SMELL findings (LS-025 to LS-030)

## Execution Plan

For each cluster, follow this exact sequence:

1. **Read** the test file. Identify the copy-paste function group.
2. **Verify** the functions truly differ only in input values. If a function has unique logic beyond the parameter (risk flag: MEDIUM -- some clusters may have subtle behavioral differences), keep it as a separate test and document why.
3. **Extract** the varying values into a `pytest.param(value, ..., id="descriptive_name")` list.
4. **Write** a single parametrized test function using `@pytest.mark.parametrize`.
5. **Delete** the original N functions.
6. **Run** scoped pytest verification on the file.
7. **Move** to the next cluster only after green.

Order: LS-011 -> LS-016 -> LS-012 -> LS-013 -> LS-019 -> LS-015 -> LS-020 -> LS-014 (highest variant count first to front-load LOC savings).

### Parametrize Pattern

```python
@pytest.mark.parametrize(
    "param_a,param_b",
    [
        pytest.param("value1", "expected1", id="descriptive-case-name"),
        pytest.param("value2", "expected2", id="another-case-name"),
    ],
)
def test_the_behavior(self, param_a, param_b):
    # Single implementation using param_a, param_b
    ...
```

Use `pytest.param(..., id=...)` for every entry so test output stays readable.

## Verification

After each file:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest <modified_file> -v --tb=short
```

Check test count is preserved (parametrize generates the same number of test IDs):
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest <modified_file> --collect-only -q | tail -1
```

After all 8 clusters:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest \
  tests/unit/dataframes/test_unit_schema.py \
  tests/unit/api/test_error_helpers.py \
  tests/unit/clients/data/test_client_extensions.py \
  tests/unit/clients/data/test_models.py \
  tests/unit/persistence/test_executor.py \
  tests/unit/models/business/matching/test_normalizers.py \
  tests/unit/models/business/test_custom_field_descriptors.py \
  tests/unit/dataframes/test_base_schema.py \
  -n auto -q --tb=short
```

LOC baseline (run BEFORE starting):
```bash
wc -l \
  tests/unit/dataframes/test_unit_schema.py \
  tests/unit/api/test_error_helpers.py \
  tests/unit/clients/data/test_client_extensions.py \
  tests/unit/clients/data/test_models.py \
  tests/unit/persistence/test_executor.py \
  tests/unit/models/business/matching/test_normalizers.py \
  tests/unit/models/business/test_custom_field_descriptors.py \
  tests/unit/dataframes/test_base_schema.py
```

## Checkpoint (Session 1 -> Session 2)

Before ending Session 1, write a checkpoint file at `.claude/wip/ASANA-HYGIENE/WS-PARAM-CHECKPOINT.md`:

```markdown
# WS-PARAM Session 1 Checkpoint

## Completed
- [list each cluster ID, file, LOC delta, test count before/after]

## LOC Delta
- Baseline: {N} lines across 8 files
- After S1: {N} lines
- Delta: -{N} lines

## Clusters Skipped (if any)
- [ID]: [reason -- e.g., "functions differ in assertion logic, not just parameter"]

## Session 2 Scope
Remaining 8 clusters: LS-009, LS-010, LS-017, LS-018, LS-021, LS-022, LS-023, LS-024

Files:
- `tests/unit/clients/data/test_cache.py` (LS-009: 4 tests, ~40 lines each)
- `tests/unit/clients/data/test_feature_flag.py` (LS-010: 4 tests, ~32 lines each)
- `tests/unit/api/test_routes_admin_edge_cases.py` (LS-017: 3 tests, ~21 lines each)
- `tests/unit/api/test_routes_dataframes.py` (LS-018: 5 tests, ~13 lines each)
- `tests/unit/clients/data/test_pii.py` (LS-021: 5 tests, ~7 lines each)
- `tests/unit/persistence/test_session_healing.py` (LS-022: 4 tests, ~8 lines each)
- `tests/unit/automation/test_config.py` (LS-023: 4 tests, ~7 lines each)
- `tests/unit/automation/polling/test_config_schema.py` (LS-024: 4 tests, ~6 lines each)

## Observations
- [any patterns or gotchas discovered during S1 that S2 should know about]
```

## Time Budget

- Session 1: ~3 hours (8 clusters, simpler patterns)
- Session 2: ~3 hours (8 clusters, includes larger 40-line and 32-line patterns)
