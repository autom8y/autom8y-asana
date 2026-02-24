# WS-AUTO: Apply 5 AUTO Patches

**Objective**: Apply the 5 mechanically safe AUTO patches from the SLOP-CHOP-TESTS-P2 remedy plan. Zero behavioral judgment required.

---

## Source Findings

| RS-ID | Finding | File | Lines | Fix |
|-------|---------|------|-------|-----|
| RS-008 | Test name contradicts behavior | `tests/integration/test_custom_field_type_validation.py` | 493-501 | Rename `test_boolean_rejected_as_number` to `test_boolean_accepted_as_number`, update docstring |
| RS-010 | Bare `except Exception` in attribute loop | `tests/integration/test_entity_write_smoke.py` | 995 | Narrow to `except (AttributeError, TypeError)` |
| RS-019 | 2 perf tests without assertions | `tests/integration/test_unified_cache_integration.py` | 594, 624 | Add `assert elapsed_ms < 1000.0` after each timing print |
| RS-021 | Missing cache-hit assertion | `tests/integration/test_platform_performance.py` | 236 | Add `assert fetch_count == 2` after second resolve_batch |
| RS-024 | Tautological `len(levels) >= 0` | `tests/validation/persistence/test_concurrency.py` | 212 | Change to `assert len(levels) >= 1` with failure message |

---

## File Targets

1. `tests/integration/test_custom_field_type_validation.py` (RS-008 only, lines 493-501)
2. `tests/integration/test_entity_write_smoke.py` (RS-010)
3. `tests/integration/test_unified_cache_integration.py` (RS-019)
4. `tests/integration/test_platform_performance.py` (RS-021)
5. `tests/validation/persistence/test_concurrency.py` (RS-024)

---

## Effort Estimate

- **Total**: ~30 minutes
- **Risk**: Zero -- all patches are diff-ready and mechanically safe

---

## Dependencies

- None. No ordering constraints.

---

## Rite / Complexity

- **Rite**: hygiene (recommended, confirm at dispatch)
- **Complexity**: SPOT
