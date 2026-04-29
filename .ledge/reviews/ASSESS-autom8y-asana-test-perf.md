---
type: assessment
target: autom8y-asana
focus: test-coverage-and-performance
scan_ref: SCAN-autom8y-asana-test-perf.md
assess_date: "2026-04-12"
assessor: pattern-profiler
signal_count: 18
validated: 17
false_positives: 1
categories:
  test-coverage: C
  mock-quality: D
  performance-testing: D
  test-infrastructure: C
overall: D
status: draft
---

# Assessment: autom8y-asana — Test Coverage & Performance

## Health Report Card

| Category | Grade | Rationale |
|----------|-------|-----------|
| Test Coverage | C | 4 zero-test packages including 434-line write-path multiplexer; intake services (1,326 lines) only route-tested; integration gap across auth, transport, search, reconciliation; 8 workspace tests permanently skipped |
| Mock Quality | D | 2,990 unspec'd mock sites (97.3% unspec rate); root MockClientBuilder fixture unspec'd, propagating SCAR-026 exposure to all 485 test files; stale xfail in active suite |
| Performance Testing | D | No CI gate for performance regressions; benchmarks are standalone scripts not in CI; no scale-boundary test for documented 504 cliff (SCAR-015); double model_dump() in hot loop confirmed in production code |
| Test Infrastructure | C | --dist=loadfile band-aid masks singleton isolation failure without fixing root cause; one permanently-skipped observability span test; no per-package coverage floor allowing zero-tested packages to hide beneath 80% aggregate |
| **Overall** | **D** | Two D categories (Mock Quality, Performance Testing); weakest-link: D caps overall at C, but two D categories and the compound write-path exposure push this to D |

**Overall Grade Calculation**: Median across 4 categories (C, D, D, C) = C-to-D boundary. Two D categories trigger the "any D caps at C" rule twice, and the write-path / SCAR-026 compound pattern (see Theme 3) elevates to D. Overall: **D**.

---

## Signal Validation Table

| Signal | Confirmed | Severity | Disposition |
|--------|-----------|----------|-------------|
| SCAN-TC-001 | YES | HIGH | Confirmed. batch/client.py (434 lines, 9 async public methods) is the write-path multiplexer with zero test directory. protocols/ (926 lines, 8 files), observability/ and _defaults/ also untested in dedicated directories, though observability is partially covered via tests/unit/test_observability.py. Batch remains the critical gap. |
| SCAN-TC-002 | YES | HIGH | Confirmed. mixins.py (315 lines, 5 mixin classes) contains UpwardTraversalMixin.to_business_async — the graph traversal logic for Contact, Unit, Offer paths (2-4 level traversals). Zero isolated tests; traversal error handling (HydrationError, partial_ok path) is untested at the unit level. |
| SCAN-TC-003 | YES | HIGH | Confirmed with nuance. Route-level tests exist (test_intake_create.py, test_intake_resolve.py, test_intake_custom_fields.py) but they test through the HTTP layer with mocked SDK. intake_create_service.py at 732 lines (7-phase SaveSession orchestration) has no service-layer unit tests. Service internals — phase ordering, parallel Phase 2 gather, idempotency checks — are invisible to current tests. |
| SCAN-TC-004 | FALSE POSITIVE | N/A | Dismissed. tests/unit/api/test_workspaces.py exists with 10 test functions covering both route handlers (GET /workspaces, GET /workspaces/{gid}), pagination, offset, default limit, and response envelope structure. Signal-sifter missed this file. |
| SCAN-TC-005 | YES | MEDIUM | Confirmed. No dedicated test for rate_limit.py (83 lines). The _get_rate_limit_key() function — which controls rate limit partitioning by PAT prefix vs IP — is untested. Incorrect key derivation would collapse per-user isolation to a single shared bucket. Rate limit behavior is partially exercised in transport tests but not the API-layer key logic. |
| SCAN-TC-006 | YES | HIGH | Confirmed. Integration test suite (25 files) covers entity/cache/hydration well. No integration tests exercise JWT/PAT middleware flows against the full FastAPI middleware stack, transport-layer behavior end-to-end, search service (758 lines), or reconciliation E2E. RISK-001 (unverified reconciliation section GIDs) has no integration-level gate. |
| SCAN-TC-007 | YES | HIGH | Confirmed and amplified. All 8 workspace switching tests permanently skipped. Skip reasons document that AsanaClient.default_workspace_gid is a plain unguarded attribute and FieldResolver is stateless with no workspace validation. These are not "not yet implemented" gaps — they are documented correctness risks (cross-workspace GID contamination) with no enforcement and no test gate. |
| SCAN-TC-008 | YES | HIGH | Confirmed. bench_cache_operations.py and bench_batch_operations.py are `if __name__ == "__main__"` scripts with zero `test_` functions. CI excludes all `benchmark`-marked tests. No .benchmarks/ baseline storage. test_insights_benchmark.py is pytest-structured but also CI-excluded. SCAR-015 recurrence (timeline 504 at scale) has no regression detection path. |
| SCAN-TC-009 | YES | MEDIUM | Confirmed. grep across entire tests/ directory returns zero hits for SCAR-004, SCAR-008, SCAR-013. Scar-tissue.md explicitly flags SCAR-004 and SCAR-008 as having "Known gap: No dedicated isolated-provider regression test." SCAR-013's `_SCHEMA_VERSIONING_AVAILABLE = False` path is similarly unexercised. These are acknowledged debts with no remediation. |
| SCAN-MQ-001 | YES | HIGH | Confirmed. 2,360 unspec'd MagicMock + 630 unspec'd AsyncMock = 2,990 total unspec'd sites vs 66 spec'd (2.7% spec rate). Per SCAR-026: unspec'd mocks silently accept attribute access on non-existent methods, allowing tests to pass on interfaces that no longer exist. |
| SCAN-MQ-002 | YES | HIGH | Confirmed and amplified. tests/conftest.py:137 `self._client = MagicMock()` is the root fixture for MockClientBuilder, inherited by 485 test files. This is not one bad mock — it is the foundation that makes every MockClientBuilder-derived test blind to interface regressions. Single highest-leverage fix in the codebase. |
| SCAN-MQ-003 | YES | MEDIUM | Confirmed. tests/unit/dataframes/test_cascading_resolver.py:503 carries `@pytest.mark.xfail(reason="clear_cache method removed")`. The method was removed; the test remains. It is counted in suite metrics but tests nothing. Stale xfail with no resolution date or issue reference. |
| SCAN-PERF-001 | YES | HIGH | Confirmed by direct file read. section_timeline_service.py lines 560-561 call `task.model_dump()` twice per iteration: once for `_extract_office_phone()` and once for `_extract_offer_id()`. At 3,800+ offers this doubles Pydantic v2 serialization cost (7,600 calls instead of 3,800). Task has 20+ fields. This is an O(n) amplification in the hottest path of the SCAR-015-protected timeline handler. |
| SCAN-PERF-002 | YES | HIGH | Confirmed. No test in test_section_timeline_service.py (730 lines, 38 tests) references 3,800, threshold, or 504. The service's "< 5 seconds" claim is asserted nowhere in CI. The scale boundary that caused SCAR-015 has no regression gate. |
| SCAN-PERF-003 | YES | MEDIUM | Confirmed. memory.py lines 115 and 121 both use `list(self._cache.keys())[:n]` — insertion-order FIFO eviction. The docstring says "LRU eviction." At default capacity of 10,000 entries, each write that triggers eviction performs O(n) list construction on the locked cache. The LRU claim in the docstring is a documentation correctness bug with secondary O(n) performance impact. |
| SCAN-PERF-004 | YES | MEDIUM | Confirmed. retry.py:724 uses `time.sleep(delay)` in the sync execute path. Scanner confidence MEDIUM is appropriate — Lambda handlers use `asyncio.run()` which creates a new event loop, so the sync path does not literally block an existing event loop. However, if the sync retry path is ever called from within an async context (e.g., via `sync_wrapper`), it will block. Risk is latent rather than immediate. Severity confirmed MEDIUM. |
| SCAN-PERF-005 | YES | MEDIUM | Confirmed. data/config.py:88 `max_connections: int = 10`. For batch workloads with 50+ parallel PVP operations, pool exhaustion is plausible. Scanner confidence is MEDIUM because the actual bottleneck depends on whether DataServiceClient is used concurrently in batch paths — not directly verifiable without runtime instrumentation. Severity confirmed MEDIUM. |
| SCAN-TI-001 | YES | HIGH | Confirmed. pyproject.toml documents that `--dist=load` crashed workers at 31.23% coverage due to SystemContext singletons and hypothesis DB shared state. The `--dist=loadfile` workaround prevents the crash but does not fix the isolation failure. Root cause (shared singleton state across workers) remains live — it is masked, not resolved. |
| SCAN-TI-002 | YES | LOW | Confirmed. test_computation_spans.py:706 carries `@pytest.mark.skip(reason="DataServiceClient.get_insights_batch_async not yet instrumented")`. This is a deferred instrumentation gap, not a correctness risk. Severity LOW confirmed. |
| SCAN-CA-001 | YES | MEDIUM | Confirmed. pyproject.toml `fail_under = 80` is a single codebase-wide threshold with no per-module floors. Four packages with zero dedicated test directories (batch, protocols, _defaults, plus partial observability) are hidden beneath high-coverage packages. The 80% floor provides a false assurance signal: zero-tested write-path code can coexist with a green CI badge. |

---

## Thematic Pattern Analysis

### Theme 1: Write-Path Coverage Blindspot

**Signals**: SCAN-TC-001 (batch/client.py), SCAN-TC-003 (intake_create_service.py), SCAN-CA-001 (no per-package floor)

**Compound severity**: HIGH. The two most critical write paths in the codebase — BatchClient (external Asana write multiplexer) and IntakeCreateService (7-phase SaveSession orchestration) — share a structural coverage gap: they are tested only through integrating layers (HTTP routes or mock-based integration fixtures), never in isolation. BatchClient has no tests whatsoever. IntakeCreateService's phase ordering, parallel Phase 2 gather, and idempotency logic are invisible to the test suite. The coverage architecture flaw (SCAN-CA-001) allows this to persist without alarming CI — the 80% aggregate hides these zeros.

**Risk projection**: A regression in BatchClient chunk logic or IntakeCreateService phase ordering would not be caught until it reached a route-level test that happens to exercise the specific failure mode, or production.

---

### Theme 2: Mock Quality Debt Creates SCAR-026 Exposure Across All 485 Test Files

**Signals**: SCAN-MQ-001 (2,990 unspec'd mocks), SCAN-MQ-002 (unspec'd root fixture), SCAN-TC-009 (no SCAR regression markers)

**Compound severity**: HIGH. The root MockClientBuilder fixture at conftest.py:137 is `MagicMock()` without a spec. Every test that uses MockClientBuilder — the majority of unit tests — inherits this structural weakness. Unspec'd mocks accept attribute access to methods that no longer exist on the real AsanaClient, meaning interface regressions pass silently. SCAR-026 exists precisely because this pattern allowed a real API change to go undetected through the test suite. The absence of SCAR-004/SCAR-008/SCAR-013 regression markers (TC-009) means the same pattern can repeat for documented production failures.

**Risk projection**: Any refactor of AsanaClient's public interface is invisible to the test suite. The 12,393 test functions and 23,860 assertions create a false confidence signal — passing tests do not verify the contract is intact.

---

### Theme 3: Performance Regression Blindness

**Signals**: SCAN-PERF-001 (double model_dump in hot loop), SCAN-PERF-002 (no scale-boundary test), SCAN-TC-008 (benchmarks excluded from CI)

**Compound severity**: HIGH. Three signals combine to create a complete performance regression detection gap. PERF-001 is a confirmed CPU amplification in the exact code path that caused SCAR-015 (timeline 504 at 3,800 offers). PERF-002 confirms that no test would catch a recurrence — the scale boundary is not tested. TC-008 confirms that performance is not part of CI at all. The combination means: (1) there is an existing performance bug in production code that doubles serialization cost, (2) there is no test that would detect if this or a similar regression pushed response time over the 504 cliff, and (3) the benchmark infrastructure exists but is deliberately excluded from CI with no regression gate.

**Risk projection**: SCAR-015 can recur. The defensive pattern (I/O at warm-up) is correct, but the CPU-side amplification in the request handler hot loop is a direct contributor and will not be caught by current CI.

---

### Theme 4: Test Infrastructure Masking Real Isolation Failures

**Signals**: SCAN-TI-001 (--dist=loadfile band-aid), SCAN-TC-007 (8 workspace tests permanently skipped), SCAN-CA-001 (no per-package floor)

**Compound severity**: HIGH. The `--dist=loadfile` workaround prevents xdist worker crashes but does not eliminate the shared singleton state. The 8 workspace switching tests are permanently skipped not because the feature is unimplemented, but because the singleton pattern makes the tests impossible to run without false results. The coverage floor architecture allows these gaps to be invisible. These three signals collectively describe an infrastructure that masks rather than surfaces isolation failures — CI is green but the guarantees it provides are weaker than they appear.

**Risk projection**: Cross-workspace GID contamination (documented in skip reasons) is a live correctness risk with no enforcement path. The singleton isolation bug could manifest differently under different load patterns than those currently exercised.

---

### Theme 5: Stale Test Artifacts Erode Suite Integrity

**Signals**: SCAN-MQ-003 (xfail for removed method), SCAN-TI-002 (permanently skipped T9 span), SCAN-TC-007 (8 permanently skipped workspace tests)

**Compound severity**: MEDIUM. Eleven test functions (8 workspace + 1 span + 1 xfail + stale xfail marker) are permanently parked with no resolution path, issue reference, or remediation timeline. This is a maintenance hygiene concern that compounds with the mock quality issue: the suite appears larger and more comprehensive than it is. Test count metrics (12,393 functions, 23,860 assertions) are inflated by tests that cannot run or that test removed interfaces.

---

## Cross-Rite Routing Recommendations

| Finding | Target Rite | Trigger Signal |
|---------|-------------|----------------|
| SCAN-TC-001: batch/client.py zero coverage | 10x-dev | Write-path multiplexer with 9 async methods, zero tests; test authoring required |
| SCAN-TC-002: mixins.py traversal logic untested | 10x-dev | Graph traversal with HydrationError paths; unit tests for UpwardTraversalMixin needed |
| SCAN-TC-003: intake services tested only at route layer | 10x-dev | 732-line SaveSession orchestrator; service-layer unit tests for phase ordering needed |
| SCAN-TC-005: rate_limit.py key derivation untested | 10x-dev | Security-adjacent: per-user rate limit partitioning logic untested |
| SCAN-TC-006: integration gap for auth/transport/search/reconciliation | 10x-dev | Integration test authoring across 4 subsystems; RISK-001 gate needed |
| SCAN-TC-007: 8 workspace tests permanently skipped | arch | Root cause is singleton registry design; workspace affinity enforcement requires architectural decision |
| SCAN-TC-008: benchmarks excluded from CI | 10x-dev | Benchmark CI integration + baseline storage; pytest-benchmark or similar |
| SCAN-TC-009: SCAR-004/008/013 no regression markers | 10x-dev | Regression test authoring for 3 documented production failures |
| SCAN-MQ-001: 2,990 unspec'd mocks | hygiene | Systematic mock quality improvement; spec= adoption campaign |
| SCAN-MQ-002: MockClientBuilder root fixture unspec'd | hygiene | Single highest-leverage fix; add spec=AsanaClient to conftest.py:137 |
| SCAN-MQ-003: stale xfail for removed method | hygiene | Dead test removal; suite integrity cleanup |
| SCAN-PERF-001: double model_dump() in hot loop | 10x-dev | Confirmed CPU amplification in SCAR-015 hot path; fix is merge model_dump() calls |
| SCAN-PERF-002: no scale-boundary test for 504 cliff | 10x-dev | Add parameterized test with 3,800+ offer fixture asserting < 5s SLA |
| SCAN-PERF-003: FIFO vs LRU eviction mismatch | hygiene | Documentation correctness fix + optional OrderedDict-based LRU |
| SCAN-PERF-004: time.sleep() in sync retry path | hygiene | Latent async-blocking risk; low friction fix |
| SCAN-PERF-005: max_connections=10 undersized | 10x-dev | Tune or document rationale; add connection pool exhaustion test |
| SCAN-TI-001: --dist=loadfile masks singleton isolation | arch | Root cause fix requires singleton registry redesign or scoped fixtures |
| SCAN-TI-002: T9 batch span test permanently skipped | 10x-dev | DataServiceClient OTel instrumentation gap |
| SCAN-CA-001: no per-package coverage floor | 10x-dev | Add per-package minimums to pyproject.toml coverage config |

---

## Priority Queue (Fix Order)

### Immediate (blocks correctness or SCAR recurrence)

1. **SCAN-MQ-002**: Add `spec=AsanaClient` to `MockClientBuilder.__init__` at `tests/conftest.py:137`. Single change; eliminates SCAR-026 exposure for 485 test files. Effort: quick fix (30 min + ripple fixing broken tests that were masking interface drift).

2. **SCAN-PERF-001**: Merge the two `task.model_dump()` calls at `section_timeline_service.py:560-561` into a single call, capturing the result in a local variable before passing to both extractors. Effort: quick fix (5 min). This is the only confirmed production-code bug with direct SCAR-015 recurrence risk.

3. **SCAN-TC-001**: Write unit tests for `batch/client.py` — at minimum `execute_async`, chunking logic, partial failure handling, and result ordering. Effort: moderate (2-3 hours). This is a write-path multiplexer with zero coverage.

### High (significant risk, address in current cycle)

4. **SCAN-PERF-002 + SCAN-TC-008**: Add a scale-boundary test for the timeline service (3,800+ offers, assert < 5s) and integrate benchmarks into CI with stored baselines. Effort: moderate (half-day).

5. **SCAN-TC-003**: Add service-layer unit tests for `intake_create_service.py` covering phase ordering, Phase 2 parallelism, and idempotency. Route-level tests are not a substitute. Effort: significant (1 day).

6. **SCAN-TC-007**: Architectural decision required on workspace affinity enforcement. Until singleton registry is redesigned, document the correctness risk with a RISK-003 entry and track in design-constraints.md. Effort: quick (documentation), significant (real fix).

7. **SCAN-TI-001**: Resolve the singleton isolation root cause — either scope `SystemContext` fixtures to file or remove shared global state. `--dist=loadfile` is a band-aid that caps parallel test throughput and conceals the real bug. Effort: significant.

### Planned (upcoming cycle)

8. **SCAN-TC-002**: Unit tests for `mixins.py` traversal mixins, especially `UpwardTraversalMixin.to_business_async` error paths. Effort: moderate.

9. **SCAN-TC-006**: Integration tests for JWT/PAT middleware stack, transport layer, and search service. RISK-001 (reconciliation section GIDs unverified) needs an integration-level gate. Effort: significant.

10. **SCAN-TC-009**: Add `@pytest.mark.regression("SCAR-004")` etc. markers and write the three missing regression tests. Effort: moderate.

11. **SCAN-CA-001**: Add `[tool.coverage.paths]` or per-module `fail_under` thresholds in pyproject.toml for `batch/`, `protocols/`, `_defaults/`. Effort: quick fix.

### Opportunistic (hygiene)

12. **SCAN-MQ-001**: Systematic spec= adoption in highest-risk test directories (`tests/unit/cache/`, `tests/unit/clients/`, `tests/unit/transport/`). Address in batches alongside other work.

13. **SCAN-MQ-003**: Delete stale xfail test at `test_cascading_resolver.py:503`.

14. **SCAN-PERF-003**: Fix `InMemoryCacheProvider` docstring to accurately describe FIFO eviction; optionally migrate to `OrderedDict` with LRU semantics.

15. **SCAN-PERF-004**: Rename or guard `time.sleep()` in sync retry path with a note about async-safety constraint.

16. **SCAN-TI-002**: Implement `@trace_computation` on `DataServiceClient.get_insights_batch_async` or remove the dead skip.

---

## False Positives Dismissed

| Signal | Dismissal Reason |
|--------|-----------------|
| SCAN-TC-004 | `tests/unit/api/test_workspaces.py` exists and covers both route handlers (`TestListWorkspaces`: 4 tests, `TestGetWorkspaceByGid`: 2 tests) with full pagination and envelope structure assertions. Signal-sifter search for `*workspaces*` in tests/ missed this file. |

---

## Coverage Gaps

No back-route to signal-sifter required. All 18 signals validated with evidence from direct file reads. One false positive (SCAN-TC-004) dismissed with documented rationale.

Minor gap noted for future scan pass: the `protocols/` package (926 lines, 8 files) was flagged as having zero test directories but indirect coverage through protocol adapter tests was not fully characterized. A dedicated protocols/ test scan could sharpen the TC-001 severity split between batch (critical) and protocols (moderate).
