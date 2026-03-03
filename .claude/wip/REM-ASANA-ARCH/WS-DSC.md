# WS-DSC: DataServiceClient Execution Policy Abstraction

**Objective**: Extract the shared 8-step orchestration scaffolding from the 5
DataServiceClient endpoint modules into a reusable execution policy, reducing
per-endpoint boilerplate from ~50-80 LOC to ~20-30 LOC.

**Rite**: 10x-dev
**Complexity**: MODULE
**Recommendations**: R-008
**Preconditions**: None (Phase 1 -- independent, parallelizable with WS-SYSCTX)
**Estimated Effort**: 3-5 days

---

## Problem

Five endpoint modules in `clients/data/_endpoints/` each replicate the same
8-step orchestration pattern:
1. Circuit breaker check
2. Get HTTP client
3. Build retry callbacks
4. Execute with retry
5. Handle error response
6. Parse success response
7. Record circuit breaker success
8. Emit metrics

The retry callbacks have already been extracted to `_retry.py:build_retry_callbacks()`.
The orchestration flow itself has not been abstracted.

**Evidence**: ARCHITECTURE-ASSESSMENT.md AP-3; ARCHITECTURE-REPORT.md R-008

---

## Artifact References

- Anti-pattern: `ARCHITECTURE-ASSESSMENT.md` Section 2, AP-3
- Risk register: `ARCHITECTURE-ASSESSMENT.md` Section 8, Risk 6
- Migration readiness: `ARCHITECTURE-REPORT.md` Section 6, R-008
- Current modules: TOPOLOGY-INVENTORY.md Section 5.5

### Key Source Files

- `src/autom8_asana/clients/data/client.py` (1,277 LOC)
- `src/autom8_asana/clients/data/_endpoints/simple.py` (234 LOC)
- `src/autom8_asana/clients/data/_endpoints/batch.py` (310 LOC)
- `src/autom8_asana/clients/data/_endpoints/insights.py` (219 LOC)
- `src/autom8_asana/clients/data/_endpoints/export.py` (173 LOC)
- `src/autom8_asana/clients/data/_endpoints/reconciliation.py` (133 LOC)
- `src/autom8_asana/clients/data/_retry.py` (191 LOC)

---

## Implementation Sketch

### Step 1: Define Execution Policy (no changes to endpoints yet)

Create `src/autom8_asana/clients/data/_policy.py`:
- Define `EndpointPolicy` Protocol with `execute(request: T) -> R`
- Implement `DefaultEndpointPolicy` that owns the 8-step flow
- Accept as constructor params: circuit breaker state, retry config,
  response parser callable, success recorder, metric emitter

### Step 2: Refactor simplest endpoint first

Refactor `_endpoints/simple.py` to use `DefaultEndpointPolicy`:
- Each endpoint method instantiates the policy with endpoint-specific params
  (URL path, request serialization, response type mapping)
- Endpoint-specific logic remains in the endpoint module
- Shared orchestration delegates to the policy
- Run: `pytest tests/unit/clients/data/ -k simple -x`

### Step 3: Migrate remaining endpoints (one at a time)

Order: `reconciliation.py` -> `export.py` -> `insights.py` -> `batch.py`
(simplest to most complex)

Run `pytest tests/unit/clients/data/ -x` after each migration.

### Step 4: Verify composition

- Confirm `client.py` still composes endpoints correctly
- Run: `pytest tests/unit/clients/ -x`
- Run: `pytest tests/integration/ -x`

---

## Do NOT

- Change the retry callback factory in `_retry.py` (already extracted, working)
- Modify the circuit breaker logic itself (only abstract how it is invoked)
- Change response shapes or error types (external API contract)
- Remove `client.py:_execute_with_retry()` if endpoints still reference it
  during transition

---

## Green-to-Green Gates

- `pytest tests/unit/clients/` passes after each endpoint migration
- `pytest tests/api/` (API integration tests) passes after all endpoints migrated
- No changes to response types, error handling semantics, or metric emission
- Per-endpoint LOC reduced from ~50-80 to ~20-30 (measure before/after)

---

## Definition of Done

- [ ] `_policy.py` created with `EndpointPolicy` protocol + `DefaultEndpointPolicy`
- [ ] All 5 endpoint modules refactored to use the policy
- [ ] Per-endpoint boilerplate measurably reduced
- [ ] Full clients test suite green
- [ ] Integration tests green
- [ ] MEMORY.md updated: "WS-DSC: execution policy abstraction DONE"
