# QA Report: EntityScope Invocation Layer

```yaml
prd: PRD-ENTITY-SCOPE-001
tdd: TDD-ENTITY-SCOPE-001 (Revision 2)
qa_agent: qa-adversary
date: 2026-02-19
recommendation: CONDITIONAL GO
```

---

## 1. Test Plan Summary

| Category | Tests Run | Passed | Failed | Skipped |
|----------|-----------|--------|--------|---------|
| Full regression suite | 3984 | 3983 | 1 (pre-existing flake) | 45 |
| Entity-scope targeted tests | 154 | 154 | 0 | 0 |
| Pipeline transition tests | 16 | 16 | 0 | 0 |
| E2E CLI dry-run (insights-export) | 1 | 1 | 0 | 0 |
| E2E CLI dry-run (conversation-audit) | 1 | 1 | 0 | 0 |

### Pre-existing Flake (Not a Regression)

`tests/unit/core/test_concurrency.py::TestStructuredLogging::test_label_in_log` fails in the full suite due to test-isolation issue (shared logger state), but passes when run in isolation. This pre-dates the EntityScope implementation.

---

## 2. Success Criteria Assessment

| ID | Criterion | Verdict | Evidence |
|----|-----------|---------|----------|
| SC-1 | `just invoke insights-export --gid=1205925604226368 --dry-run` returns entity metadata without executing writes | **CONDITIONAL PASS** | CLI executes successfully. JSON output includes `dry_run: true` in metadata. Entity was skipped (no_resolution -- parent Business lacks office_phone). However, `report_preview` is NOT present in metadata. PRD SC-1 requires `report_preview`; TDD Section 2.4.3 specifies `metadata["report_preview"] = markdown_content[:2000]`. See DEF-001. |
| SC-2 | `just invoke insights-export --gid=1205925604226368` processes single offer, uploads attachment | **NOT TESTED** | The test GID's parent Business has `office_phone=None`, so the entity is correctly skipped with `no_resolution`. A different GID with a valid parent Business would be needed. This is a test data limitation, not an implementation defect. |
| SC-3 | Existing EventBridge-triggered Lambda behavior unchanged (no regression) | **PASS** | 3983 tests pass (full suite). All migrated workflow tests pass. Handler factory orchestration (`validate -> enumerate -> execute`) is verified by 4 new tests in `test_workflow_handler.py`. The `from_event({})` path produces default scope (empty entity_ids, dry_run=False), preserving existing Lambda behavior. |
| SC-4 | `POST /api/v1/workflows/insights-export/invoke` with JWT returns WorkflowResult | **PASS** | Verified by `test_invoke_success` and `test_invoke_response_shape` in `tests/unit/api/routes/test_workflows.py`. Response includes `request_id`, `invocation_source: "api"`, `workflow_id`, `dry_run`, `entity_count`, and `result` sub-object. |
| SC-5 | Invalid workflow_id returns 404 | **PASS** | Verified by `test_invoke_unknown_workflow_404`. Response: `{"detail": {"error": "WORKFLOW_NOT_FOUND"}}`. |
| SC-6 | Unauthenticated request returns 401 | **PASS** | Verified by `test_invoke_no_auth_401`. Auth dependency raises HTTPException(401). |
| SC-7 | `entity_ids=[]` returns 400 validation error | **PARTIAL PASS** | Implementation returns HTTP 422 (Pydantic validation), not 400 as the PRD specifies. The test `test_invoke_empty_entity_ids_400` asserts 422. This is a PRD specification vs. FastAPI convention deviation -- see DEF-003. |
| SC-8 | conversation-audit workflow supports entity_ids targeting | **PASS** | Verified by `TestEnumerateAsyncConversationAudit::test_targeted_scope_skips_pre_resolution` in `test_conversation_audit.py`. Targeted scope produces synthetic entity dicts and skips the expensive pre-resolution step. E2E dry-run CLI also verified (entity skipped due to missing phone -- correct behavior). |

---

## 3. Defect Register

### DEF-001: Missing `report_preview` in insights-export dry-run metadata

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Priority** | P2 |
| **Type** | Missing feature |
| **Reproducible** | Always |
| **Blocking** | No (dry-run functions correctly; only preview enrichment is absent) |

**Location**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/workflows/insights_export.py` lines 292-293

**Expected (per TDD Section 2.4.3, lines 511-513)**:
```python
if dry_run:
    metadata["dry_run"] = True
    metadata["report_preview"] = markdown_content[:2000]
```

**Actual**:
```python
if dry_run:
    metadata["dry_run"] = True
```

**Impact**: The `report_preview` field is specified in both the PRD (SC-1: "verify JSON output includes `report_preview`") and TDD (Section 2.4.3: "Dry-run metadata enrichment"). Its absence means developers cannot preview what a dry-run would produce without examining logs. The TDD also specifies a test `test_dry_run_includes_report_preview` (Section 8.6, line 1511) that was never written.

**Root Cause**: The dry-run metadata enrichment happens at the `execute_async` level (WorkflowResult.metadata), but `markdown_content` is only available inside `_process_offer`. The per-offer outcome type `_OfferOutcome` does not carry markdown content back to the aggregation layer. Implementing this requires either: (a) adding a `preview` field to `_OfferOutcome`, or (b) accumulating previews in `execute_async` alongside the existing per-offer tracking.

**Missing Test**: `test_dry_run_includes_report_preview` (TDD Section 8.6 line 1511) was not implemented.

---

### DEF-002: Missing `csv_row_count` in conversation-audit dry-run metadata

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **Priority** | P3 |
| **Type** | Missing feature |
| **Reproducible** | Always |
| **Blocking** | No |

**Location**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/workflows/conversation_audit.py` lines 273-274

**Expected (per TDD Section 2.5.3, lines 679-681; PRD FR-004.4)**:
```python
if dry_run:
    metadata["dry_run"] = True
    metadata["csv_row_count"] = export.row_count
```

**Actual**:
```python
if dry_run:
    metadata["dry_run"] = True
```

**Impact**: PRD FR-004.4 explicitly requires `metadata.csv_row_count` for dry-run results. Without it, operators cannot gauge the size of the CSV that would have been uploaded. Lower severity than DEF-001 because csv_row_count is less actionable than report_preview.

**Missing Test**: `test_dry_run_metadata_csv_row_count` (TDD Section 8.6 line 1519) was not implemented.

---

### DEF-003: API returns 422 where PRD specifies 400 for validation errors

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **Priority** | P3 |
| **Type** | Specification deviation |
| **Reproducible** | Always |
| **Blocking** | No |

**Location**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/workflows.py` lines 55-67

**PRD Reference**: SC-7 says "`entity_ids=[]` returns 400 validation error". FR-005.5 says "return 400 if empty or missing". FR-005.6 says "return 400 if non-numeric".

**Actual**: Pydantic's `field_validator` raises `ValueError`, which FastAPI converts to HTTP 422 (Unprocessable Entity). The test suite asserts 422.

**Analysis**: This is a deliberate divergence favoring FastAPI convention (422 for request body validation) over the PRD specification (400). The TDD does not explicitly override this. The endpoint's OpenAPI spec documents `400` in the responses dict (line 121) but the implementation never returns 400. This is cosmetic -- the semantics are correct (invalid input is rejected), and 422 is the standard FastAPI behavior for Pydantic validation failures.

**Recommendation**: Accept as-is. Changing to 400 would require custom exception handling that fights FastAPI conventions. Update PRD to reflect 422 if needed.

---

### DEF-004: CLI exit code 1 for argument errors (PRD specifies exit code 2)

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **Priority** | P4 |
| **Type** | Specification deviation |
| **Reproducible** | Always |
| **Blocking** | No |

**Location**: `/Users/tomtenuta/Code/autom8y-asana/scripts/invoke_workflow.py` lines 101-106 and 161-166

**PRD Reference**: FR-006.8 says "Exit code: 0 on success, 1 on workflow failure, 2 on CLI argument error".

**Actual**: Missing `--gid` exits with code 1 (line 166). Unknown workflow_id exits with code 1 (line 106). There is no exit code 2 path.

**Impact**: Negligible. Exit codes 1 vs 2 distinction only matters for scripted automation that differentiates between "workflow failed" and "bad arguments". Not a blocking issue.

---

### DEF-005: CLI API mode not implemented

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **Priority** | P4 |
| **Type** | Deferred feature |
| **Reproducible** | N/A |
| **Blocking** | No |

**Location**: `/Users/tomtenuta/Code/autom8y-asana/scripts/invoke_workflow.py`

**PRD Reference**: FR-006.4 says "Primary mode (API): when `--api-url` is provided or API is detected running on localhost:8000, send POST to invoke endpoint".

**Actual**: The CLI only supports direct invocation mode. There is no `--api-url` argument and no HTTP POST path. Only the fallback mode (FR-006.5: direct construction) is implemented.

**Analysis**: The TDD Section 2.8 only specifies direct invocation, not API mode. This appears to be an intentional scope reduction by the architect. The direct mode is fully functional and serves the primary use case (developer debugging).

---

## 4. Code Review Findings

### 4.1 Security Assessment

| Area | Status | Notes |
|------|--------|-------|
| Authentication | PASS | JWT/PAT dual-mode auth via existing `get_auth_context` |
| Rate limiting | PASS | 10/min per client on invoke endpoint |
| Input validation | PASS | entity_ids: non-empty, max 100, numeric-only |
| Audit logging | PASS | `workflow_invoke_api` log includes caller identity, entity_ids, workflow_id |
| Params injection | ACCEPTABLE RISK | `body.params` can override workflow params. Documented as intentional in TDD. Only authenticated callers can invoke. |
| PII in logs | PASS | entity_ids are Asana GIDs (not PII). No phone numbers or names logged. |
| Timeout protection | PASS | 120s timeout via `asyncio.wait_for`. `TimeoutError` caught correctly (Python 3.11+). |

### 4.2 Error Handling Assessment

| Path | Status | Notes |
|------|--------|-------|
| Unknown workflow_id | PASS | 404 with `WORKFLOW_NOT_FOUND` |
| Pydantic validation failure | PASS | 422 with structured error details |
| Workflow validate_async failure | PASS | 422 with `WORKFLOW_VALIDATION_FAILED` |
| Execution timeout | PASS | 504 with `WORKFLOW_TIMEOUT` |
| Top-level Lambda exception | PASS | 500 with error type and traceback |
| Missing auth | PASS | 401 |

### 4.3 Architectural Assessment

| Decision | Assessment |
|----------|-----------|
| EntityScope in `core/scope.py` | CORRECT -- follows dependency direction (core consumed by automation, lambda_handlers, api). TDD ADR-001 override of PRD FR-001.1 is sound. |
| Clean break on WorkflowAction ABC | CORRECT -- all 3 implementations updated. No deprecation bridge needed (private ABC, no external consumers). |
| Module-level `_WORKFLOW_CONFIGS` dict | ACCEPTABLE -- populated once at startup, read-only thereafter. Not thread-safety-sensitive in async context. |
| Handler factory orchestration | CORRECT -- validate -> enumerate -> execute lifecycle is clean and consistent across Lambda, API, and CLI entry points. |
| Frozen dataclass for EntityScope | CORRECT -- immutability prevents accidental mutation. `from_event()` normalizes types correctly. |

### 4.4 Test Coverage Assessment

| Area | Tests | Coverage | Gaps |
|------|-------|----------|------|
| EntityScope construction | 10 | Comprehensive | None observed |
| EntityScope properties | 2 | Complete | None |
| EntityScope serialization | 2 | Complete | None |
| EntityScope immutability | 1 | Sufficient | None |
| Handler factory orchestration | 4 | Good | None |
| API endpoint | 11 | Good | Missing: concurrent request test, body.params injection boundary test |
| InsightsExport enumerate | 4 | Good | None |
| InsightsExport dry-run | 3 | **GAP** | Missing: `test_dry_run_includes_report_preview` (TDD Section 8.6) |
| ConversationAudit enumerate | 3 | Good | None |
| ConversationAudit dry-run | 2 | **GAP** | Missing: `test_dry_run_metadata_csv_row_count` (TDD Section 8.6) |
| PipelineTransition enumerate | Covered in existing tests | Adequate | None |
| CLI invocation | 0 | **GAP** | No unit tests for `invoke_workflow.py` (PRD FR-006 has no test requirement, but TDD Section 8.7 specifies integration tests) |

---

## 5. E2E Smoke Test Results

### Test 1: insights-export dry-run

```
Command: uv run python scripts/invoke_workflow.py insights-export --gid=1205925604226368 --dry-run
Result: SUCCESS (exit code 0)
Entities enumerated: 1
Entities processed: 0 succeeded, 0 failed, 1 skipped
Skip reason: no_resolution (parent Business lacks office_phone)
Metadata: dry_run=True present; report_preview ABSENT
```

The entity skip is correct behavior -- GID 1205925604226368 is an Offer whose parent Business (GID 1205925488574909) has `office_phone=None`. The workflow correctly resolves the parent chain (Offer -> Offer Holder -> Business) and skips when the Business lacks phone data.

### Test 2: conversation-audit dry-run

```
Command: uv run python scripts/invoke_workflow.py conversation-audit --gid=1205925604226368 --dry-run
Result: SUCCESS (exit code 0)
Entities enumerated: 1
Entities processed: 0 succeeded, 0 failed, 1 skipped
Skip reason: holder_skipped_no_phone
Metadata: dry_run=True present; csv_row_count ABSENT
```

Consistent behavior -- same underlying data limitation.

### Test 3: Full (non-dry-run) execution

**NOT EXECUTED**. The test GID produces a skip (correct behavior), so removing `--dry-run` would produce the identical result with zero write operations. Running a full execution against a GID with valid data would require identifying a Business with a valid office_phone in the production Asana workspace. The test would execute real writes (upload attachment to Asana task), which is appropriate only with explicit stakeholder authorization.

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| DEF-001 report_preview missing in production dry-runs | HIGH (will occur on every dry-run) | LOW (dry-run still functions; preview is informational) | Fix in follow-up. Does not affect non-dry-run behavior. |
| API 422 vs 400 confuses consumers | LOW | LOW | Document in API changelog. FastAPI convention is widely understood. |
| CLI missing API mode | LOW | LOW | Direct mode covers primary use case. API mode is additive. |
| Params injection via API | LOW | MEDIUM | Only authenticated callers. Rate limited. Audit logged. |

---

## 7. Recommendation

### CONDITIONAL GO

The EntityScope Invocation Layer implementation is production-ready for merge with the following conditions:

**Conditions for merge (P2 -- should fix before merge)**:
1. **DEF-001**: Add `report_preview` to insights-export dry-run metadata per TDD Section 2.4.3. Add the missing test `test_dry_run_includes_report_preview`.

**Accepted for merge (fix in follow-up)**:
2. **DEF-002**: Add `csv_row_count` to conversation-audit dry-run metadata per PRD FR-004.4. Add the missing test `test_dry_run_metadata_csv_row_count`. (P3 -- lower urgency than DEF-001)
3. **DEF-003**: Accept 422 vs 400 as FastAPI convention. Update PRD to reflect actual behavior.
4. **DEF-004**: Accept exit code 1 for all errors. Cosmetic.
5. **DEF-005**: Accept CLI API mode as deferred. Direct mode is sufficient.

**Rationale**: The core functionality is sound. All 154 entity-scope tests pass. No regressions in the full 3983-test suite. Security posture is good (auth, rate limiting, audit logging, input validation). The two missing metadata fields (DEF-001, DEF-002) are informational enrichments that do not affect the correctness of dry-run write gating (uploads and deletes ARE correctly skipped). However, DEF-001 specifically appears in both the PRD success criteria (SC-1) and the TDD specification, making it a contractual gap that should be addressed before declaring the feature complete.

---

## 8. Artifact Verification

All artifacts verified via Read tool:

| File | Status | Lines |
|------|--------|-------|
| `src/autom8_asana/core/scope.py` | Verified | EntityScope dataclass, from_event, to_params |
| `src/autom8_asana/automation/workflows/base.py` | Verified | WorkflowAction ABC with enumerate_async, execute_async |
| `src/autom8_asana/lambda_handlers/workflow_handler.py` | Verified | Handler factory with scope orchestration |
| `src/autom8_asana/automation/workflows/insights_export.py` | Verified | enumerate_async + dry_run gating |
| `src/autom8_asana/automation/workflows/conversation_audit.py` | Verified | enumerate_async + dry_run gating |
| `src/autom8_asana/automation/workflows/pipeline_transition.py` | Verified | enumerate_async (API wiring deferred) |
| `src/autom8_asana/api/routes/workflows.py` | Verified | POST endpoint with auth, rate limit, timeout |
| `scripts/invoke_workflow.py` | Verified | CLI with direct invocation mode |
| `src/autom8_asana/api/lifespan.py` | Verified | Workflow config registration at startup |
| `src/autom8_asana/api/routes/__init__.py` | Verified | workflows_router exported |
| `src/autom8_asana/api/main.py` | Verified | workflows_router included |
| `tests/unit/core/test_scope.py` | Verified | 15 tests |
| `tests/unit/lambda_handlers/test_workflow_handler.py` | Verified | 13 tests (9 existing + 4 new) |
| `tests/unit/api/routes/test_workflows.py` | Verified | 11 tests |
| `tests/unit/automation/workflows/test_insights_export.py` | Verified | Migrated + 7 new tests |
| `tests/unit/automation/workflows/test_conversation_audit.py` | Verified | Migrated + 5 new tests |
