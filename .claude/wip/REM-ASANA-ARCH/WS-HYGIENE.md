# WS-HYGIENE: Cross-Rite Hygiene Referrals

**Objective**: Address the 6 cross-rite referrals from the architecture analysis
that route to the hygiene rite -- directory reorg, private API elimination,
TYPE_CHECKING cleanup, cycle elimination, and test status verification.

**Rite**: hygiene
**Complexity**: PATCH to MODULE (mixed)
**Referrals**: XR-ARCH-001, XR-ARCH-003, XR-ARCH-004, XR-ARCH-005, XR-ARCH-006
**Preconditions**: None (independent, any phase)
**Estimated Effort**: 3-4 days total

Note: XR-ARCH-002 (v1 sunset) routes to debt-triage, covered in WS-DEBT.

---

## XR-ARCH-001: automation/ Directory Reorganization (Low Priority)

**Problem**: `automation/` contains 3 distinct concerns: legacy pipeline, event
system, workflows (including 1,476 LOC insights_formatter). No functional
relationship between insights HTML rendering and automation rules.

**Evidence**: ARCHITECTURE-REPORT.md Section 8, XR-ARCH-001
**Effort**: 0.5-1 day | **Priority**: Low (leverage 3/10)

### Steps
1. Extract `automation/workflows/` to top-level `workflows/` directory
   OR extract `insights_formatter.py` to a standalone renderer module
2. Update all imports referencing moved modules
3. No logic changes -- purely structural
4. Run: `pytest tests/ -x`

### Do NOT
- Change any business logic in the moved files
- Restructure the event system (it belongs in automation/)
- Move `pipeline.py` (it has established references everywhere)

---

## XR-ARCH-003: Eliminate Private API Cross-Boundary Call (Low Priority)

**Problem**: `dataframes/models/registry.py` calls `services.resolver._clear_resolvable_cache`
-- a private function in a higher-level module for cache coherence.

**Evidence**: ARCHITECTURE-REPORT.md Section 8, XR-ARCH-003;
DEPENDENCY-MAP.md Section 8, Unknown #4
**Effort**: 0.5 day | **Priority**: Low

### Steps
1. Read `dataframes/models/registry.py` line 97 to understand the call context
2. Add `SchemaRegistry.on_schema_change` callback hook (or event)
3. In `services/resolver.py`, subscribe to the callback at initialization:
   `SchemaRegistry.on_schema_change(lambda: _clear_resolvable_cache())`
4. Remove the cross-boundary private function import
5. Run: `pytest tests/unit/dataframes/ tests/unit/services/ -x`

---

## XR-ARCH-004: Replace Business->DataServiceClient TYPE_CHECKING (Low Priority)

**Problem**: `models/business/business.py` has a TYPE_CHECKING import of
`DataServiceClient` and `InsightsResponse` -- conceptual dependency from
domain model to client layer.

**Evidence**: ARCHITECTURE-REPORT.md Section 8, XR-ARCH-004;
DEPENDENCY-MAP.md Section 7.1
**Effort**: 0.5 day | **Priority**: Low (TYPE_CHECKING only, no runtime impact)

### Steps
1. Define `InsightsProvider` protocol in `protocols/insights.py`
   with the method signatures currently type-hinted against DataServiceClient
2. Replace TYPE_CHECKING import in `business.py` with protocol import
3. Ensure DataServiceClient satisfies the protocol (structural typing)
4. Run: `pytest tests/unit/models/business/ -x`
5. Run: `mypy src/autom8_asana/models/business/business.py`

---

## XR-ARCH-005: Eliminate cache->api Metrics Cycle (Low Priority)

**Problem**: `cache/integration/dataframe_cache.py` imports `api/metrics.py`
creating Cycle 5. Guarded by try/except and nosemgrep suppression.

**Evidence**: ARCHITECTURE-REPORT.md Section 8, XR-ARCH-005;
DEPENDENCY-MAP.md Section 6.1, Cycle 5
**Effort**: 0.5-1 day | **Priority**: Low

### Steps
1. Define `MetricsEmitter` protocol in `protocols/` with the metric
   emission interface used by dataframe_cache
2. Inject `MetricsEmitter` into DataFrameCache rather than importing directly
3. In `api/startup.py` or DI wiring, provide the concrete implementation
4. Remove the try/except import guard in dataframe_cache.py
5. Cycle 5 eliminated
6. Run: `pytest tests/unit/cache/ tests/api/ -x`

---

## XR-ARCH-006: Verify Pre-Existing Test Failures (Medium Priority)

**Problem**: `test_adversarial_pacing.py` and `test_paced_fetch.py` are noted as
pre-existing failures across all prior workstreams. Current status unknown.

**Evidence**: ARCHITECTURE-REPORT.md Section 8, XR-ARCH-006;
ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md Paradox 4
**Effort**: 0.5 day | **Priority**: Medium (checkpoint resume reliability)

### Steps
1. Run: `pytest tests/ -k "adversarial_pacing or paced_fetch" --tb=long`
2. **If passing**: Update MEMORY.md to reflect current state. Close XR-ARCH-006.
3. **If failing**: Determine whether they represent:
   (a) genuine behavioral gaps in checkpoint resume -> fix or file as debt
   (b) aspirational test design -> mark as xfail with rationale
4. Document outcome

---

## Recommended Order

1. XR-ARCH-006 (verify tests -- 30 min, resolves U-008)
2. XR-ARCH-003 (private API elimination -- 0.5 day)
3. XR-ARCH-004 (InsightsProvider protocol -- 0.5 day)
4. XR-ARCH-005 (MetricsEmitter protocol -- 0.5-1 day)
5. XR-ARCH-001 (directory reorg -- last, biggest, least urgent)

---

## Green-to-Green Gates

- Full test suite passes after each referral is addressed
- No new cross-boundary private API calls introduced
- Cycle 5 eliminated (if XR-ARCH-005 completed)
- `mypy` passes on modified files

---

## Definition of Done

- [ ] XR-ARCH-006: Test failure status resolved and documented
- [ ] XR-ARCH-003: Private API call replaced with callback/event
- [ ] XR-ARCH-004: InsightsProvider protocol replaces TYPE_CHECKING import
- [ ] XR-ARCH-005: MetricsEmitter protocol eliminates Cycle 5
- [ ] XR-ARCH-001: automation/ reorganized (or documented as deferred)
- [ ] Full test suite green
- [ ] MEMORY.md updated: "WS-HYGIENE: cross-rite referrals DONE"
