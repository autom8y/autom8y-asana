# WS-INTEG: Add Preload Manifest Integration Tests

**Finding IDs**: LS-008 referral (cross-rite to 10x-dev)
**Severity**: DEFECT referral
**Estimated Effort**: 2-3 hours
**Dependencies**: None (independent)
**Lane**: A or C (after predecessor completes)

---

## Scope

The slop-chop sprint deleted 3 simulation tests from `TestPreloadManifestCheck` (RS-013) because they replicated production logic inline rather than calling production code. The cross-rite referral calls for proper integration tests that exercise the actual manifest check logic in `process_project`.

### Background

The deleted tests were:
- `test_skips_build_when_no_manifest_and_lambda_available`
- `test_proceeds_normally_when_manifest_exists`
- `test_skips_without_lambda_arn_when_no_manifest`

These asserted on local variables populated by test code, not production code. A block comment was left at the deletion site explaining what was removed and the required fix path.

### Behaviors to Cover

The manifest check in `process_project` has three branches:
1. **Manifest exists**: Proceed with progressive preload
2. **No manifest + Lambda ARN configured**: Invoke Lambda delegation, skip local build
3. **No manifest + no Lambda ARN**: Skip preload entirely (log warning)

---

## Objective

**Done when**:
- 3+ integration tests cover the manifest check branches in `process_project`
- Tests call the actual production function (or a thin wrapper around it)
- Tests verify observable behavior (return value, side effects, log output) -- not internal state
- Tests pass in the standard test environment
- Block comment at deletion site in `test_preload_lambda_delegation.py` can be updated to reference new tests

---

## Files to Read

### Production code (read-only, do NOT modify)
- `src/autom8_asana/api/preload/progressive.py` -- contains `process_project` and manifest check logic
- `src/autom8_asana/api/preload/legacy.py` -- fallback path (for understanding, not testing)

### Existing test infrastructure
- `tests/unit/api/test_preload_lambda_delegation.py` -- where deletions occurred; read the block comment at the deletion site and the surviving `test_lambda_invoked_with_all_delegated_entities`
- `tests/integration/` -- check for existing preload integration tests and fixtures
- `tests/conftest.py` -- shared fixtures

---

## Files to Create/Edit

- **New file** (preferred): `tests/integration/api/test_preload_manifest_check.py`
  - OR add to existing integration test file if one exists for preload
- **Edit**: `tests/unit/api/test_preload_lambda_delegation.py` -- update block comment to reference new integration tests

---

## Constraints

- **Production code is read-only**: Do NOT modify `progressive.py` or any production files
- **Integration test style**: Use real function calls with mocked external dependencies (Asana API, Lambda, S3). Do NOT replicate production logic inline.
- **Minimal mocking**: Mock only external boundaries (AWS Lambda invoke, Asana API calls, S3 manifest check). Do not mock internal functions.
- **Follow existing patterns**: Match the integration test style found in `tests/integration/`

---

## Context References

- **Deletion justification**: `.wip/REMEDY-tests-unit-p1.md` (RS-013)
- **Original finding**: `.claude/wip/SLOP-CHOP-TESTS-P1/phase2-analysis/ANALYSIS-REPORT.md` (LS-008)
- **Preload architecture**: ADR-011 (`docs/adr/ADR-011-*.md` or `docs/decisions/`)

---

## Verification

```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/api/test_preload_manifest_check.py \
  -v --tb=short

# Also verify no regressions in existing preload tests
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/unit/api/test_preload_lambda_delegation.py \
  -n auto -q --tb=short
```
