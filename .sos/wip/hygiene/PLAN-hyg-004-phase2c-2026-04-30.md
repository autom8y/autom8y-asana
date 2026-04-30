---
type: design
artifact_type: refactor-plan
rite: hygiene
session_id: session-20260430-144514-3693fe01
target: HYG-004 Phase 2C
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-phase2
authored_by: main-thread (15K-token retry path; mirrors Phase 2A/2B template)
authored_at: 2026-04-30
evidence_grade: STRONG
status: proposed
---

# PLAN — HYG-004 Phase 2C — test_batch_adversarial.py

## §1 Purpose

Final HYG-004 Phase 2 sub-sprint. Closes the 4-of-4 adversarial files commitment from Phase 1 + Phase 2A/B/C. After this commit lands: HYG-004 fully discharges from HANDOFF-eunomia-to-hygiene-2026-04-29.

## §2 Pre-flight Drift-Audit (D1/D2 Pattern Recurrence)

**HANDOFF cite**: "tests/unit/test_batch_adversarial.py: upload edge-case cluster (lines 356-438, 12 tests)"

**Empirical re-probe** (READ tests/unit/test_batch_adversarial.py L356-438):
- L356-438 region contains BatchRequest validation tests (paths, methods, data) — **NOT upload edge-cases**
- HANDOFF cluster identification was inaccurate (Pattern-6 drift; consistent with Phase 1 D1/D2 + Phase 2A 6-test off-by-six + Phase 2B 13-line under-spec)

**Empirical actual cluster**: `TestBatchResultPropertyEdgeCases` L432-540, **14 status-code classification tests** (L436-503: test_status_199 through test_status_503). All structurally identical modulo:
- `status_code` integer value (14 distinct codes: 199, 200, 201, 204, 299, 300, 400, 401, 403, 404, 429, 500, 502, 503)
- `expected_success` boolean (5 success codes; 9 failure codes)
- One asymmetric test: `test_status_199_is_failure` ALSO asserts `result.error is not None` (other failure tests don't)

**D-pattern adjudication**: ACCEPT per Phase 1 audit-lead precedent + Phase 2A/B established pattern. Empirical enumeration is authoritative.

## §3 Cluster Enumeration

| # | Source line | test_name | status_code | expected_success | extra_assertion |
|---|---|---|---|---|---|
| 1 | L436 | test_status_199_is_failure | 199 | False | error is not None |
| 2 | L442 | test_status_200_is_success | 200 | True | — |
| 3 | L447 | test_status_201_is_success | 201 | True | — |
| 4 | L452 | test_status_204_is_success | 204 | True | — |
| 5 | L457 | test_status_299_is_success | 299 | True | — |
| 6 | L462 | test_status_300_is_failure | 300 | False | — |
| 7 | L467 | test_status_400_is_failure | 400 | False | — |
| 8 | L472 | test_status_401_is_failure | 401 | False | — |
| 9 | L477 | test_status_403_is_failure | 403 | False | — |
| 10 | L482 | test_status_404_is_failure | 404 | False | — |
| 11 | L487 | test_status_429_is_failure | 429 | False | — |
| 12 | L492 | test_status_500_is_failure | 500 | False | — |
| 13 | L497 | test_status_502_is_failure | 502 | False | — |
| 14 | L502 | test_status_503_is_failure | 503 | False | — |

## §4 Parametrize-Target

Single parametrized test `test_status_code_classification`. Tuple: `(status_code, expected_success, expected_has_error)`. Use `pytest.param(..., id="...")` to preserve descriptive test ids.

Asymmetric handling: row 1 (status 199) gets `expected_has_error=True`; rows 2-5 (success codes) get `None`; rows 6-14 (failure codes) get `None` (failure tests didn't originally assert error presence). Conditional assertion in test body: `if expected_has_error is not None: assert (result.error is not None) is expected_has_error`.

## §5 Mutation Pattern

Replace L436-503 (14 method definitions) with single parametrized method. ~80 lines collapse to ~25 lines (-55 net).

## §6 Specificity-Preservation Rules

- R1: each `pytest.param` id mirrors original test function name (e.g., `id="status_199_is_failure"`)
- R2: assertion `result.success is expected_success` preserved verbatim
- R3: row 1's `error is not None` check preserved via conditional `if expected_has_error is not None` branch
- R4: BatchResult instantiation pattern unchanged
- R5: docstring on parametrized method summarizes class-level intent (status code maps to success/failure)

## §7 Coverage-Delta Verification

Pre/post `pytest --cov=src/autom8_asana --cov-report=term tests/unit/test_batch_adversarial.py | grep -E "TOTAL|src/autom8_asana/" | tail -10`. Coverage Δ ≥0 (HANDOFF AC 6 strict gate).

## §8 Atomic Commit Shape

Single commit per Phase 2 charter Q2. Title: `refactor(tests): parametrize-promote batch_adversarial status-code cluster (HYG-004 Phase 2C)`.

## §9 Risks

- R1 specificity loss → mitigated by §6 R1-R5
- R2 SCAR ≥47 BLOCKING → pre/post collection check
- R3 coverage delta → §7 strict gate
- R4 D-pattern drift documented → §2 ACCEPT precedent

## §10 Out-of-Scope Refusal

- DO NOT modify other tests in this file (e.g., TestBatchRequestValidationEdgeCases at L311-430 is out of scope)
- DO NOT touch production code
- DO NOT touch other test files
- DO NOT push to remote
