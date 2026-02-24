# WS-CFVAL: Assert-Free Custom Field Validation Tests

**Objective**: Add behavioral get-back assertions to all 26 assert-free test functions in `test_custom_field_type_validation.py`, so they verify the stored value after `accessor.set()`.

---

## Source Findings

| RS-ID | Finding | Severity | Confidence |
|-------|---------|----------|------------|
| RS-001 | 26 test functions call `accessor.set(field, value)` with only `# Should not raise` and zero assertions. Suite passes even if `set()` is a no-op. | DEFECT HIGH | HIGH |

---

## File Targets

- **Test file**: `tests/integration/test_custom_field_type_validation.py`
- **Production source (read only)**: `src/autom8_asana/models/custom_field_accessor.py`

### Test Functions to Fix (26 total)

Lines: 14, 40, 60, 67, 74, 91, 111, 118, 155, 166, 183, 199, 210, 227, 246, 263, 269, 376, 383, 394, 417, 444, 451, 503, 510, 519

### Assertion Pattern

For each test function that calls `accessor.set(field, value)`:

```python
accessor.set("Budget", 42)
assert accessor.get("Budget") == 42  # get-back assertion
```

Type-specific variations:
- **Number fields**: `assert accessor.get(field) == value`
- **Text fields**: `assert accessor.get(field) == value`
- **Date fields**: `assert accessor.get(field) == value`
- **Enum fields**: `assert accessor.get(field) == value` (may need dict comparison)
- **Multi-enum fields**: `assert accessor.get(field) == value` (list comparison)
- **People fields**: `assert accessor.get(field) == value` (list comparison)
- **None-acceptance tests**: `assert accessor.get(field) is None`
- **Missing field test** (line 519): verify accessor state unchanged or expect raise

---

## Effort Estimate

- **Total**: ~3 hours
- **Breakdown**: ~5 min per function (read, understand stored form, write assertion, verify)
- **Risk**: MEDIUM -- some fields may store in a different representation than the input (e.g., enum by GID). Read `CustomFieldAccessor` source to determine correct stored form.

---

## Dependencies

- WS-AUTO must complete first (RS-008 renames `test_boolean_rejected_as_number` in the same file)

---

## Rite / Complexity

- **Rite**: 10x-dev (recommended, confirm at dispatch)
- **Complexity**: MODULE
