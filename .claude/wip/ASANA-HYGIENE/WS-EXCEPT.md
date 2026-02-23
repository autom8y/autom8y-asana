# WS-EXCEPT: Tighten Broad Exception Assertions

**Finding IDs**: LS-025, LS-026, LS-027
**Severity**: SMELL
**Estimated Effort**: 2-3 hours
**Dependencies**: None (independent)
**Lane**: C

---

## Scope

Replace 16 instances of `pytest.raises(Exception)` with specific exception types across 8 test files. The analysis report identified the correct exception types for each group.

---

## Target Files and Fixes

### LS-025: Retry client errors (7 occurrences)
- **File**: `tests/unit/clients/data/test_retry.py`
- **Current**: `pytest.raises(Exception)` in 7 test functions
- **Correct type**: `ClientError` (or the specific subclass from `autom8y_http` or `autom8_asana`)
- **Action**: Read the production retry module to confirm the exact exception class, then replace all 7 occurrences

### LS-026: Model validation errors (5 occurrences across 4 files)
- **Files**:
  - `tests/unit/models/test_common_models.py`
  - `tests/unit/resolution/test_result.py`
  - `tests/unit/persistence/test_cascade.py`
  - `tests/unit/dataframes/test_cache_integration.py`
- **Current**: `pytest.raises(Exception)` in 5 test functions
- **Correct types**: `ValidationError` (pydantic) and/or `FrozenInstanceError` depending on context
- **Action**: Read each test to determine which operation triggers the exception, then identify the precise exception class from the production code

### LS-027: Schema/query errors (4 occurrences across 3 files)
- **Files**:
  - `tests/unit/query/test_section_edge_cases.py`
  - `tests/unit/query/test_join.py`
  - `tests/unit/cache/test_edge_cases.py`
- **Current**: `pytest.raises(Exception)` in 4 test functions
- **Correct types**: `SchemaError` and/or `ColumnNotFoundError` depending on context
- **Action**: Read each test and the invoked production function to determine the precise exception class

---

## Objective

**Done when**:
- All 16 `pytest.raises(Exception)` replaced with specific exception types
- Zero occurrences of `pytest.raises(Exception)` remain in the 7 target files
- All tests pass with the tighter exception matching
- No regressions in surrounding tests

---

## Execution Strategy

For each finding group:
1. Read the test file to find the `pytest.raises(Exception)` sites
2. Read the production code being tested to identify what exception it actually raises
3. Import the specific exception class in the test file
4. Replace `pytest.raises(Exception)` with `pytest.raises(SpecificException)`
5. Run scoped verification

**Important**: If a test is genuinely catching multiple exception types (e.g., the code path can raise either `ValidationError` or `TypeError`), use `pytest.raises((ValidationError, TypeError))` -- but document why the multi-catch is needed.

---

## Production Files to Read (do NOT modify)

For LS-025:
- `src/autom8_asana/clients/data/` -- retry module, check what exceptions the retry mechanism raises
- `autom8y_http` package -- check `ClientError`, `TimeoutException`, etc.

For LS-026:
- `src/autom8_asana/models/` -- check pydantic model definitions for `ValidationError`
- `pydantic` -- `ValidationError`, `FrozenInstanceError`

For LS-027:
- `src/autom8_asana/query/` -- check for `SchemaError`, `ColumnNotFoundError`
- `src/autom8_asana/dataframes/` -- check schema-related exceptions

---

## Constraints

- **Test-only changes**: Do NOT modify any production source files
- **Tighten only**: Replace broad with specific. Do NOT weaken (e.g., changing `ValueError` to `Exception`)
- **Match production behavior**: The specific exception must be what the production code actually raises
- **Preserve test intent**: Do not change what operation the test is exercising
- **Do NOT add new test cases**: This workstream only tightens existing assertions

---

## Context References

- **Finding details**: `.claude/wip/SLOP-CHOP-TESTS-P1/phase2-analysis/ANALYSIS-REPORT.md` (LS-025 to LS-027 table)

---

## Verification

After each file group:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest <modified_file> -n auto -q --tb=short
```

After all changes:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest \
  tests/unit/clients/data/test_retry.py \
  tests/unit/models/test_common_models.py \
  tests/unit/resolution/test_result.py \
  tests/unit/persistence/test_cascade.py \
  tests/unit/dataframes/test_cache_integration.py \
  tests/unit/query/test_section_edge_cases.py \
  tests/unit/query/test_join.py \
  tests/unit/cache/test_edge_cases.py \
  -n auto -q --tb=short
```

Confirm zero broad exceptions remain:
```bash
grep -rn "pytest.raises(Exception)" \
  tests/unit/clients/data/test_retry.py \
  tests/unit/models/test_common_models.py \
  tests/unit/resolution/test_result.py \
  tests/unit/persistence/test_cascade.py \
  tests/unit/dataframes/test_cache_integration.py \
  tests/unit/query/test_section_edge_cases.py \
  tests/unit/query/test_join.py \
  tests/unit/cache/test_edge_cases.py
# Expected: 0 matches
```
