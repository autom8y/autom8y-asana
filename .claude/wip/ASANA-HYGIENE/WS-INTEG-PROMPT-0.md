# WS-INTEG Session Prompt

## Rite & Workflow
- Rite: 10x-dev
- Workflow: `/task`
- Complexity: SCRIPT

## Objective

Write 3+ integration tests for the preload manifest check logic in `process_project`, replacing the 3 simulation tests deleted during slop-chop P1 (RS-013/LS-008). Tests must call the actual production function and verify observable behavior (return value, side effects, log output) -- not replicate production logic inline.

## Context

During slop-chop Partition 1, remedy-smith deleted 3 tests from `TestPreloadManifestCheck` because they simulated production logic inline rather than calling it. The deletion was correct -- the tests proved nothing about production behavior. A block comment was left at the deletion site, and a cross-rite referral (LS-008) calls for proper integration tests.

The manifest check in `process_project` has three branches:
1. **Manifest exists**: Proceed with progressive preload
2. **No manifest + Lambda ARN configured**: Invoke Lambda delegation, skip local build
3. **No manifest + no Lambda ARN**: Skip preload entirely (log warning)

- Seed doc: `.claude/wip/ASANA-HYGIENE/WS-INTEG.md`
- Deletion justification: `.wip/REMEDY-tests-unit-p1.md` (RS-013)
- Original finding: `.claude/wip/SLOP-CHOP-TESTS-P1/phase2-analysis/ANALYSIS-REPORT.md` (LS-008)
- Preload architecture: check `docs/adr/` or `docs/decisions/` for ADR-011

## Scope

### IN SCOPE

**Files to read (production code -- do NOT modify)**:
- `src/autom8_asana/api/preload/progressive.py` -- contains `process_project` with manifest check logic
- `src/autom8_asana/api/preload/legacy.py` -- fallback path (read for understanding only)

**Files to read (test infrastructure)**:
- `tests/unit/api/test_preload_lambda_delegation.py` -- block comment at deletion site, surviving `test_lambda_invoked_with_all_delegated_entities`
- `tests/integration/` -- browse for existing preload integration tests, fixture patterns
- `tests/conftest.py` -- shared fixtures

**Files to create**:
- `tests/integration/api/test_preload_manifest_check.py` (new file, ~80-120 LOC)
  - Or add to existing integration test file if one exists for preload

**Files to edit**:
- `tests/unit/api/test_preload_lambda_delegation.py` -- update block comment at deletion site to reference the new integration tests

### OUT OF SCOPE

- Modifying any production source files
- Testing the progressive preload build process itself (only the manifest check branching)
- Testing the legacy fallback path
- Other slop-chop findings

## Execution Plan

1. **Read** `src/autom8_asana/api/preload/progressive.py` to understand `process_project` signature, manifest check logic, and what external dependencies it calls.
2. **Read** `tests/integration/` to understand existing integration test patterns and fixtures.
3. **Read** `tests/unit/api/test_preload_lambda_delegation.py` to understand the block comment and the surviving test's mock pattern.
4. **Design** 3 integration tests covering the three manifest branches. Mock only external boundaries:
   - S3/manifest existence check
   - AWS Lambda invocation
   - Asana API client
5. **Write** tests that call the real `process_project` function (or the narrowest public function that contains the manifest check).
6. **Verify** all 3 tests pass.
7. **Update** the block comment in the unit test file.

**Risk flag (LOW)**: Production function may have side effects making test isolation tricky. If `process_project` is too deeply integrated to call directly, extract the manifest check into a testable seam and test that. Document the approach in a comment.

### Test Design Principles

- Call the actual production function -- do NOT replicate logic inline
- Mock only external boundaries (AWS, Asana API, S3)
- Assert on observable outcomes: return values, mock call counts, log output
- Use `pytest.mark.asyncio` if the production function is async
- Match existing integration test style in `tests/integration/`

## Verification

```bash
# Run new integration tests
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/api/test_preload_manifest_check.py \
  -v --tb=short

# Verify no regressions in existing preload unit tests
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/unit/api/test_preload_lambda_delegation.py \
  -v --tb=short
```

## Time Budget

- Estimated: 2-3 hours
- ~1 hour reading production code and understanding the manifest check flow
- ~1 hour writing tests
- ~0.5 hour verification and block comment update
