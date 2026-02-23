# WS-EXCEPT Session Prompt

## Rite & Workflow
- Rite: hygiene
- Workflow: `/task`
- Complexity: SPOT

## Objective

Replace all 16 `pytest.raises(Exception)` with specific exception types across 8 test files (LS-025 to LS-027). Every test must still pass with the tighter exception matching. Zero broad exceptions remain in the target files.

## Context

Slop-chop Partition 1 identified 16 sites where tests use `pytest.raises(Exception)` instead of the specific exception the production code actually raises. The analysis report pre-identified the correct types for each group. This is a direct-apply workstream: read production code to confirm the type, then replace.

- Seed doc: `.claude/wip/ASANA-HYGIENE/WS-EXCEPT.md`
- Finding details: `.claude/wip/SLOP-CHOP-TESTS-P1/phase2-analysis/ANALYSIS-REPORT.md` (LS-025 to LS-027 table)

## Scope

### IN SCOPE

**LS-025: Retry client errors (7 occurrences)**
- File: `tests/unit/clients/data/test_retry.py`
- Suggested type: `ClientError` from `autom8y_http` or the retry module's own exception
- Production code to read: `src/autom8_asana/clients/data/` retry-related modules; also check `autom8y_http` exception hierarchy

**LS-026: Model validation errors (5 occurrences across 4 files)**
- `tests/unit/models/test_common_models.py`
- `tests/unit/resolution/test_result.py`
- `tests/unit/persistence/test_cascade.py`
- `tests/unit/dataframes/test_cache_integration.py`
- Suggested types: `pydantic.ValidationError` for model instantiation, `dataclasses.FrozenInstanceError` or `pydantic.ValidationError` for frozen field mutation
- Production code to read: the model classes being tested in each file

**LS-027: Schema/query errors (4 occurrences across 3 files)**
- `tests/unit/query/test_section_edge_cases.py`
- `tests/unit/query/test_join.py`
- `tests/unit/cache/test_edge_cases.py`
- Suggested types: `SchemaError`, `ColumnNotFoundError` from query/dataframe exception hierarchy
- Production code to read: `src/autom8_asana/query/` and `src/autom8_asana/dataframes/` exception definitions

### OUT OF SCOPE

- Any production source files (test-only changes)
- Adding new test cases
- Changing test logic or what operation is exercised
- Weakening any exception type (only tighten: `Exception` -> specific)
- Other SMELL findings (LS-009 to LS-024, LS-028 to LS-030)

## Execution Plan

Work through each finding group in order: LS-025 -> LS-026 -> LS-027.

For each occurrence:

1. **Read the test function** containing `pytest.raises(Exception)`. Note what operation it calls.
2. **Read the production function** being called. Trace to the `raise` statement. Note the exact exception class and its import path.
3. **Add the import** to the test file if not already present.
4. **Replace** `pytest.raises(Exception)` with `pytest.raises(SpecificException)`.
5. **Run** scoped pytest to confirm the test still passes with tighter matching.

**Edge case handling**: If a code path can raise multiple exception types depending on input, use `pytest.raises((TypeA, TypeB))` and add a comment explaining why a tuple is needed. But first verify this is actually the case -- in most situations there is one dominant exception type.

**Edge case handling**: If you discover a `pytest.raises(Exception)` is catching a base class that IS the narrowest reasonable catch (e.g., the production code raises different subclasses), use the base class of the hierarchy rather than `Exception`. The goal is to be as specific as possible while still matching production behavior.

## Verification

After each finding group:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest <modified_files> -v --tb=short
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

## Time Budget

- Estimated: 2-3 hours
- 16 occurrences x ~10 min each (read production code + replace + verify)
