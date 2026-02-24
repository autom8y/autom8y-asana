# WS-CFVAL Session Prompt

## Rite & Workflow
- Rite: 10x-dev
- Workflow: `/task`
- Complexity: MODULE

## Objective

Add behavioral get-back assertions to all 26 assert-free test functions in `test_custom_field_type_validation.py`. After this session, every test that calls `accessor.set(field, value)` must also verify the stored value via `accessor.get(field)`.

## Context

- Seed doc: `.claude/wip/REM-HYGIENE/WS-CFVAL.md`
- Remedy plan: `.claude/wip/SLOP-CHOP-TESTS-P2/phase4-remediation/REMEDY-PLAN.md` (RS-001)
- Analysis: `.claude/wip/SLOP-CHOP-TESTS-P2/phase2-analysis/ANALYSIS-REPORT-integ-batch1.md` (P2B1-001, P2B1-012)

## Scope

### IN SCOPE

- **Test file**: `tests/integration/test_custom_field_type_validation.py`
- **Production source (read only)**: `src/autom8_asana/models/custom_field_accessor.py`

26 test functions at lines: 14, 40, 60, 67, 74, 91, 111, 118, 155, 166, 183, 199, 210, 227, 246, 263, 269, 376, 383, 394, 417, 444, 451, 503, 510, 519

### OUT OF SCOPE

- Modifying production source files
- Adding new test cases (only add assertions to existing functions)
- Other test files
- RS-008 (already applied by WS-AUTO)

## Execution Plan

### Step 1: Read Production Source

Read `src/autom8_asana/models/custom_field_accessor.py` to understand:
- How `set(field_name, value)` stores the value
- How `get(field_name)` retrieves it
- What representation is used for each field type (number, text, date, enum, multi_enum, people)
- Whether None storage differs by type

### Step 2: Add Assertions (per function)

For each of the 26 test functions, add a get-back assertion after the `accessor.set()` call:

**Pattern for value-setting tests**:
```python
accessor.set("Budget", 42)
assert accessor.get("Budget") == 42
```

**Pattern for None-acceptance tests**:
```python
accessor.set("Budget", None)
assert accessor.get("Budget") is None
```

**Pattern for enum/dict types** (determine exact stored form from source):
```python
accessor.set("Priority", {"gid": "enum_gid_1"})
assert accessor.get("Priority") == {"gid": "enum_gid_1"}  # or whatever the stored form is
```

**Pattern for list types (multi_enum, people)**:
```python
accessor.set("Tags", [{"gid": "1"}, {"gid": "2"}])
assert accessor.get("Tags") == [{"gid": "1"}, {"gid": "2"}]
```

**For `test_validation_with_missing_field` (line 519)**: If the test expects no-raise for unknown fields, verify the accessor state is unchanged after the set call. If it should raise, convert to `pytest.raises`.

### Step 3: Verify After Each Batch

After every 5-6 functions, run:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/test_custom_field_type_validation.py -v --tb=short
```

### Step 4: Final Verification

```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/test_custom_field_type_validation.py -v --tb=short

# Verify assertion count increased:
grep -c "assert" tests/integration/test_custom_field_type_validation.py
# Expected: >> 26 (was ~1 before)
```

## Escalation Triggers

- If `accessor.get(field)` returns a different representation than the input to `set()` (e.g., enum stored as GID string vs. dict), read the source carefully and assert the correct stored form. Document the mapping.
- If a test function has unique behavior beyond the "set then get" pattern, document why and implement the appropriate assertion.
- Do NOT add `assert True` or trivial non-vacuous assertions. Each assertion must exercise a real behavioral contract.

## Time Budget

- Estimated: 3 hours
- ~30 min reading CustomFieldAccessor source
- ~2 hours adding assertions (26 functions at ~5 min each)
- ~30 min verification and edge cases

Commit with message prefix `test(10x):`.
