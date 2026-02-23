# WS-PARAM Session 2 Prompt

## Rite & Workflow
- Rite: hygiene
- Workflow: `/task`
- Complexity: MODULE
- Session: 2 of 2

## Objective

Parametrize the remaining 8 copy-paste test clusters (LS-009, LS-010, LS-017, LS-018, LS-021 to LS-024) into `@pytest.mark.parametrize` calls. Session 1 completed 7 clusters with -298 LOC; this session targets ~100-300 additional LOC reduction.

## Context

- Session 1 checkpoint: `.claude/wip/ASANA-HYGIENE/WS-PARAM-CHECKPOINT.md`
- Seed doc: `.claude/wip/ASANA-HYGIENE/WS-PARAM.md`
- Finding details: `.claude/wip/SLOP-CHOP-TESTS-P1/phase2-analysis/ANALYSIS-REPORT.md` (LS-009 to LS-024 table)

## Session 1 Observations (apply these)

- **Front-load large clusters**: LS-009 (~40 lines each) and LS-010 (~32 lines each) yield the biggest LOC savings. Do these first.
- **Schema/column tests compress best**: -53 to -69 lines per cluster in S1.
- **Small clusters may yield minimal savings**: LS-023 and LS-024 (~6-7 lines each) may save very little. Still parametrize for consistency but don't force it if overhead exceeds savings.
- **Multi-assertion tests**: Splitting into individual parametrize cases slightly increases test count. This is acceptable if all assertions are preserved.
- **Some clusters may not exist**: LS-014 was a no-op in S1 (cluster removed in prior refactoring). If a cluster doesn't exist, skip it and document why.

## Scope

### IN SCOPE -- Session 2 (8 clusters)

| ID | File | Tests | Lines Each | Parametrize On |
|----|------|-------|-----------|----------------|
| LS-009 | `tests/unit/clients/data/test_cache.py` | 4 | ~40 | cache key, expected behavior |
| LS-010 | `tests/unit/clients/data/test_feature_flag.py` | 4 | ~32 | flag name, expected state |
| LS-017 | `tests/unit/api/test_routes_admin_edge_cases.py` | 3 | ~21 | endpoint, expected response |
| LS-018 | `tests/unit/api/test_routes_dataframes.py` | 5 | ~13 | dataframe type, expected schema |
| LS-021 | `tests/unit/clients/data/test_pii.py` | 5 | ~7 | input, expected masked output |
| LS-022 | `tests/unit/persistence/test_session_healing.py` | 4 | ~8 | session state, expected healing |
| LS-023 | `tests/unit/automation/test_config.py` | 4 | ~7 | config key, expected value |
| LS-024 | `tests/unit/automation/polling/test_config_schema.py` | 4 | ~6 | schema field, expected type |

### OUT OF SCOPE

- Session 1 clusters (LS-011 to LS-016, LS-019, LS-020) -- already done
- Any production source files (test-only changes)
- Adding new test cases (only extract existing cases into parametrize)
- Changing test logic or assertions (only extract the varying parameter)

## Execution Plan

For each cluster, follow this exact sequence:

1. **Read** the test file. Identify the copy-paste function group.
2. **Verify** the functions truly differ only in input values. If a function has unique logic beyond the parameter, keep it as a separate test and document why.
3. **Extract** the varying values into a `pytest.param(value, ..., id="descriptive_name")` list.
4. **Write** a single parametrized test function using `@pytest.mark.parametrize`.
5. **Delete** the original N functions.
6. **Run** scoped pytest verification on the file.
7. **Move** to the next cluster only after green.

Order: LS-009 -> LS-010 -> LS-017 -> LS-018 -> LS-021 -> LS-022 -> LS-023 -> LS-024 (largest clusters first).

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

Check test count is preserved:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest <modified_file> --collect-only -q | tail -1
```

After all 8 clusters, run full unit suite:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/unit/ -n auto -q --tb=short
```

LOC baseline (run BEFORE starting):
```bash
wc -l \
  tests/unit/clients/data/test_cache.py \
  tests/unit/clients/data/test_feature_flag.py \
  tests/unit/api/test_routes_admin_edge_cases.py \
  tests/unit/api/test_routes_dataframes.py \
  tests/unit/clients/data/test_pii.py \
  tests/unit/persistence/test_session_healing.py \
  tests/unit/automation/test_config.py \
  tests/unit/automation/polling/test_config_schema.py
```

## Completion

When done, update the checkpoint at `.claude/wip/ASANA-HYGIENE/WS-PARAM-CHECKPOINT.md` with S2 results appended (same schema as S1 section). Include combined S1+S2 LOC delta.

Commit with message prefix `test(hygiene):`.
