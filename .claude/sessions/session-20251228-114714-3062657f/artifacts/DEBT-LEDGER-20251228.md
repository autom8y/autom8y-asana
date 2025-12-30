# Technical Debt Ledger

**Audit Date**: 2025-12-28
**Scope**: Full codebase - Recent Features, Core Infrastructure, Test Coverage
**Auditor**: Debt Collector (debt-triage-pack)

---

## Executive Summary

### Total Debt Items: 82

| Severity | Count | Percentage |
|----------|-------|------------|
| CRITICAL | 2 | 2.4% |
| HIGH | 18 | 22.0% |
| MEDIUM | 42 | 51.2% |
| LOW | 20 | 24.4% |

### By Category

| Category | Count | Description |
|----------|-------|-------------|
| BUG | 12 | Functional defects, incorrect behavior |
| DESIGN_DEBT | 28 | Architectural issues, code smells |
| COVERAGE_GAP | 22 | Missing tests, untested paths |
| TODO | 8 | Unimplemented features, marked TODOs |
| CONFIG | 12 | Hardcoded values, missing configurability |

### By Blast Radius

| Blast Radius | Count |
|--------------|-------|
| SYSTEM | 4 |
| CROSS-CUTTING | 16 |
| MODULE | 38 |
| ISOLATED | 24 |

### By Module

| Module | Critical | High | Medium | Low | Total |
|--------|----------|------|--------|-----|-------|
| persistence/ | 1 | 4 | 4 | 4 | 13 |
| cache/ | 1 | 2 | 6 | 4 | 13 |
| transport/ | 0 | 2 | 4 | 2 | 8 |
| automation/polling/ | 0 | 1 | 5 | 3 | 9 |
| search/ | 0 | 1 | 4 | 3 | 8 |
| models/business/matching/ | 0 | 1 | 4 | 3 | 8 |
| api/routes/ | 0 | 3 | 0 | 0 | 3 |
| clients/ | 0 | 2 | 4 | 2 | 8 |
| dataframes/ | 0 | 0 | 4 | 0 | 4 |
| tests/ | 0 | 2 | 5 | 1 | 8 |

---

## Debt Items Table

### CRITICAL Severity

| ID | Title | Category | Module | Blast Radius | Location | Description |
|----|-------|----------|--------|--------------|----------|-------------|
| DEBT-001 | Two-tier cache write-through inconsistency | BUG | cache/ | SYSTEM | tiered.py:75-86 | Write-through to S3 is fire-and-forget; failures leave L1/L2 inconsistent, causing stale reads system-wide |
| DEBT-002 | Pending actions cleared on partial commit failure | BUG | persistence/ | SYSTEM | session.py:737-738 | Queue corruption possible when commit partially fails; data loss risk |

### HIGH Severity

| ID | Title | Category | Module | Blast Radius | Location | Description |
|----|-------|----------|--------|--------------|----------|-------------|
| DEBT-003 | Session state transitions not atomic | BUG | persistence/ | CROSS-CUTTING | session.py:47-58 | No lock protection on `_state`; race conditions in concurrent usage |
| DEBT-004 | Cascade operations remain after partial failures | BUG | persistence/ | MODULE | session.py:749-751 | No max retry counter; infinite retry loop possible |
| DEBT-005 | Concurrent track() calls race condition | BUG | persistence/ | MODULE | session.py:367 | No lock; could corrupt entity snapshots |
| DEBT-006 | Batch executor assumes sequential results | BUG | persistence/ | MODULE | executor.py:106-108 | No validation that result count matches input count |
| DEBT-007 | Circuit breaker hooks swallow exceptions | BUG | transport/ | CROSS-CUTTING | circuit_breaker.py:196-219 | Bare `pass` in exception handlers hides failures |
| DEBT-008 | Half-open state max calls not enforced | BUG | transport/ | MODULE | circuit_breaker.py:124-127 | Counter can exceed intended probing calls; defeats circuit breaker purpose |
| DEBT-009 | Simple get/set bypass two-tier logic | DESIGN_DEBT | cache/ | CROSS-CUTTING | tiered.py:129-156 | Clients calling simple API get incomplete behavior; consistency violations |
| DEBT-010 | Lock file UnboundLocalError risk | BUG | automation/polling/ | MODULE | polling_scheduler.py:445-462 | `lock_file` may be undefined when OSError caught |
| DEBT-011 | SearchCriteria OR combinator unsupported | DESIGN_DEBT | search/ | MODULE | models.py:52, 69 | OR field exists but only AND implemented; misleading API |
| DEBT-012 | Code duplication in field comparisons | DESIGN_DEBT | models/business/matching/ | MODULE | engine.py:222-459 | Four `_compare_*` methods follow identical pattern (~150 lines boilerplate) |
| DEBT-013 | API dataframes routes untested | COVERAGE_GAP | api/routes/ | CROSS-CUTTING | dataframes.py | 455 lines, 0% coverage; critical user-facing functionality |
| DEBT-014 | API projects routes untested | COVERAGE_GAP | api/routes/ | CROSS-CUTTING | projects.py | 351 lines, 0% coverage; critical user-facing functionality |
| DEBT-015 | API sections routes untested | COVERAGE_GAP | api/routes/ | MODULE | sections.py | 220 lines, 0% coverage |
| DEBT-016 | Goals client low coverage | COVERAGE_GAP | clients/ | MODULE | goals.py | 1,124 lines, <30% coverage |
| DEBT-017 | Portfolios client low coverage | COVERAGE_GAP | clients/ | MODULE | portfolios.py | 905 lines, <30% coverage |
| DEBT-018 | SaveSession bloat and complexity | DESIGN_DEBT | persistence/ | CROSS-CUTTING | session.py | 1,560 lines, 16 try/except blocks; maintenance burden |
| DEBT-019 | Tasks client overcrowded | DESIGN_DEBT | clients/ | MODULE | tasks.py | 1,397 lines, 58 methods; SRP violation |
| DEBT-020 | Test collection errors blocking coverage | COVERAGE_GAP | tests/ | SYSTEM | pytest | 151 errors preventing full test suite execution |

### MEDIUM Severity

| ID | Title | Category | Module | Blast Radius | Location | Description |
|----|-------|----------|--------|--------------|----------|-------------|
| DEBT-021 | Healing queue operations not fail-safe | BUG | persistence/ | MODULE | session.py:384-385 | No rollback on enqueue failure |
| DEBT-022 | No action target validation | DESIGN_DEBT | persistence/ | MODULE | session.py:999-1023 | Queues invalid actions silently |
| DEBT-023 | Custom field reset order dependency | DESIGN_DEBT | persistence/ | MODULE | session.py:782-784 | Reset before mark_clean risky |
| DEBT-024 | Snapshot comparison non-determinism | BUG | persistence/ | MODULE | tracker.py:116 | model_dump() comparison issues |
| DEBT-025 | Staleness check ignores version for EVENTUAL | DESIGN_DEBT | cache/ | MODULE | staleness.py:57-59 | Stale data served indefinitely |
| DEBT-026 | Coalescer deduplication never resets | BUG | cache/ | MODULE | coalescer.py:96-99 | Future might hang on silent failure |
| DEBT-027 | Lightweight checker doesn't validate timestamps | DESIGN_DEBT | cache/ | MODULE | lightweight_checker.py | No chronological validation |
| DEBT-028 | Metrics are not thread-safe | BUG | cache/ | MODULE | metrics.py | Counter corruption under concurrency |
| DEBT-029 | Memory cache eviction is deterministic, not LRU | DESIGN_DEBT | cache/ | MODULE | backends/memory.py:107-110 | Can thrash on repeated access |
| DEBT-030 | Promotion TTL hardcoded | CONFIG | cache/ | MODULE | tiered.py:49-50 | 3600s not configurable |
| DEBT-031 | Hardcoded rate limit values | CONFIG | transport/ | CROSS-CUTTING | rate_limiter.py:21-22 | Asana limit embedded in defaults |
| DEBT-032 | No semaphore asymmetry validation | DESIGN_DEBT | transport/ | MODULE | http.py:66-67 | Read/write limits not validated |
| DEBT-033 | Retry-After not checked at initial limit | BUG | transport/ | MODULE | http.py:188-192 | Could cause unnecessary delays |
| DEBT-034 | Stream bypasses rate limiter on chunks | DESIGN_DEBT | transport/ | MODULE | http.py:417 | Could exceed limits on large files |
| DEBT-035 | PID logging writes wrong value | BUG | automation/polling/ | ISOLATED | polling_scheduler.py:451 | Writes `sys.executable` instead of `os.getpid()` |
| DEBT-036 | Repeated sync/async wrapper pattern | DESIGN_DEBT | automation/polling/ | MODULE | service.py:392-457 | Five methods create new event loops; duplication |
| DEBT-037 | Incomplete action validation | DESIGN_DEBT | automation/polling/ | MODULE | action_executor.py:136-148 | No param type/value validation |
| DEBT-038 | Task attribute access assumptions | DESIGN_DEBT | automation/polling/ | MODULE | trigger_evaluator.py:58-99 | No validation of task attributes |
| DEBT-039 | Missing file lock integration test | COVERAGE_GAP | automation/polling/ | MODULE | tests/integration/ | No concurrent lock tests |
| DEBT-040 | Rule enabled field not tested | COVERAGE_GAP | automation/polling/ | ISOLATED | tests/unit/ | Disabled rules not verified |
| DEBT-041 | Sync/async dual API with asyncio.run | DESIGN_DEBT | search/ | MODULE | service.py:380-457 | RuntimeError if called from async context |
| DEBT-042 | Field name normalization inconsistent | DESIGN_DEBT | search/ | MODULE | service.py:738-762 | Two different normalization strategies |
| DEBT-043 | Error handling swallows context | DESIGN_DEBT | search/ | MODULE | service.py:220-233 | Silent empty results on error |
| DEBT-044 | Matched fields extraction complex | DESIGN_DEBT | search/ | MODULE | service.py:717-725 | Three lookups, easy to miss edge cases |
| DEBT-045 | Hardcoded fuzzy thresholds | CONFIG | models/business/matching/ | MODULE | comparators.py:84-87, config.py:80-97 | Thresholds scattered between docstring and config |
| DEBT-046 | Magic numbers in term frequency | CONFIG | models/business/matching/ | MODULE | comparators.py:214-217, 246 | Hard-coded frequencies not configurable |
| DEBT-047 | Incomplete blocking rule semantics | DESIGN_DEBT | models/business/matching/ | MODULE | blocking.py:259-281 | Pass-through pattern unclear |
| DEBT-048 | Incomplete edge case tests | COVERAGE_GAP | models/business/matching/ | MODULE | test_engine.py | No tests for extreme log-odds, competing priorities |
| DEBT-049 | BaseClient cache helpers swallow exceptions | DESIGN_DEBT | clients/ | CROSS-CUTTING | base.py:120-128 | Cache failures never raised |
| DEBT-050 | Modified_at parsing fallback | BUG | clients/ | MODULE | base.py:157-159 | Uses now() on invalid timestamp; data integrity |
| DEBT-051 | Duplicated cache logic across clients | DESIGN_DEBT | clients/ | CROSS-CUTTING | clients/*.py | Hard to keep consistent |
| DEBT-052 | Attachments client limited coverage | COVERAGE_GAP | clients/ | MODULE | attachments.py | 672 lines, limited coverage |
| DEBT-053 | Tags client partial coverage | COVERAGE_GAP | clients/ | MODULE | tags.py | 531 lines, 47% coverage |
| DEBT-054 | Teams client partial coverage | COVERAGE_GAP | clients/ | MODULE | teams.py | 378 lines, 40% coverage |
| DEBT-055 | Webhooks client no dedicated tests | COVERAGE_GAP | clients/ | MODULE | webhooks.py | 479 lines, no dedicated tests |
| DEBT-056 | Office derivation TODO | TODO | dataframes/ | MODULE | extractors/unit.py:90 | Blocks Unit DataFrame feature |
| DEBT-057 | Office phone TODO | TODO | dataframes/ | MODULE | extractors/unit.py:113 | Blocks unit extraction |
| DEBT-058 | Vertical ID TODO | TODO | dataframes/ | MODULE | extractors/unit.py:136 | Incomplete field mapping |
| DEBT-059 | Pipeline stage TODO | TODO | dataframes/ | MODULE | extractors/unit.py:159 | Incomplete business logic |
| DEBT-060 | Goals client complexity | DESIGN_DEBT | clients/ | MODULE | goals.py | 1,124 lines, 62 methods |
| DEBT-061 | Pipeline automation complexity | DESIGN_DEBT | automation/ | MODULE | pipeline.py | 1,081 lines, implicit state machine |
| DEBT-062 | Adversarial tests scattered | DESIGN_DEBT | tests/ | CROSS-CUTTING | tests/unit/test_tier*.py | 5,458 lines at root; organization debt |

### LOW Severity

| ID | Title | Category | Module | Blast Radius | Location | Description |
|----|-------|----------|--------|--------------|----------|-------------|
| DEBT-063 | Automation failures silently logged | DESIGN_DEBT | persistence/ | ISOLATED | session.py:812-818 | Not included in SaveResult |
| DEBT-064 | Cache invalidation failures don't fail commit | DESIGN_DEBT | persistence/ | ISOLATED | session.py:1499-1505 | Stale entries leak |
| DEBT-065 | Name resolver cache never cleared | DESIGN_DEBT | persistence/ | ISOLATED | session.py:175-176 | Unbounded growth |
| DEBT-066 | GID transition map never cleaned | DESIGN_DEBT | persistence/ | ISOLATED | tracker.py:42-43 | Unbounded growth |
| DEBT-067 | Dependency graph cycle error truncated | DESIGN_DEBT | persistence/ | ISOLATED | graph.py:63-70 | Large cycles hard to debug |
| DEBT-068 | Action executor no GID format validation | DESIGN_DEBT | persistence/ | ISOLATED | action_executor.py:95-120 | Confusing API errors |
| DEBT-069 | Batch staleness fetches all entries | DESIGN_DEBT | cache/ | ISOLATED | loader.py:249 | Wasted deserialization |
| DEBT-070 | Cache loader version parsing fallback | BUG | cache/ | ISOLATED | loader.py:329-330 | Uses now() on parse failure |
| DEBT-071 | Redis reconnect interval hardcoded | CONFIG | cache/ | ISOLATED | backends/redis.py:190 | Interval not exposed in config |
| DEBT-072 | S3 metadata stored as string | DESIGN_DEBT | cache/ | ISOLATED | backends/s3.py:76-80 | No type validation on read |
| DEBT-073 | Rate limiter jitter hardcoded | CONFIG | transport/ | ISOLATED | retry.py:70 | Jitter multiplier not configurable |
| DEBT-074 | Multipart upload no size validation | DESIGN_DEBT | transport/ | ISOLATED | http.py:464-471 | Could cause OOM or API rejection |
| DEBT-075 | Config path in error messages | BUG | automation/polling/ | ISOLATED | config_loader.py:131-138 | List indices formatted incorrectly |
| DEBT-076 | Env var substitution case sensitivity | CONFIG | automation/polling/ | ISOLATED | config_loader.py:43 | Mixed case sensitivity |
| DEBT-077 | Structured logging fallback untested | COVERAGE_GAP | automation/polling/ | ISOLATED | structured_logger.py:57-64 | Fallback path unverified |
| DEBT-078 | ProjectDataFrame cache TTL hardcoded | CONFIG | search/ | ISOLATED | service.py:76, 527 | 300s not configurable |
| DEBT-079 | Empty DataFrame cache miss unclear | DESIGN_DEBT | search/ | ISOLATED | service.py:157, 175 | Can't distinguish no-results vs cache-miss |
| DEBT-080 | Entity type filter hardcoded columns | DESIGN_DEBT | search/ | ISOLATED | service.py:656 | Non-deterministic first-match behavior |
| DEBT-081 | Hardcoded stop words | CONFIG | models/business/matching/ | ISOLATED | blocking.py:147-174 | Stop words list not configurable |
| DEBT-082 | Missing log-odds clipping docs | TODO | models/business/matching/ | ISOLATED | engine.py:49-52 | Clipping lacks justification |

---

## Critical/High Priority Details

### DEBT-001: Two-tier cache write-through inconsistency [CRITICAL]

**Location**: `cache/tiered.py:75-86`
**Category**: BUG
**Blast Radius**: SYSTEM

**Description**: The two-tier cache implementation uses a fire-and-forget pattern for write-through to S3 (L2). When the L2 write fails, no retry or rollback occurs, leaving L1 (memory/Redis) and L2 (S3) in an inconsistent state. Subsequent reads may return stale data from L2 if L1 is evicted.

**Impact**:
- Data inconsistency across cache tiers
- Stale reads after L1 eviction
- Silent data corruption in long-running processes

**Recommended Fix**: Implement transactional write-through with rollback on L2 failure, or mark L1 entries as "unsynced" for later reconciliation.

---

### DEBT-002: Pending actions cleared on partial commit failure [CRITICAL]

**Location**: `persistence/session.py:737-738`
**Category**: BUG
**Blast Radius**: SYSTEM

**Description**: When a commit partially fails, the pending actions queue is cleared regardless of which actions succeeded. This can result in data loss where some operations were intended but never executed, and the user has no way to know which actions were lost.

**Impact**:
- Data loss on partial failures
- Queue corruption
- Unrecoverable state after failures

**Recommended Fix**: Implement action-level tracking with success/failure status; only clear actions that confirmed success. Provide recovery mechanism for failed actions.

---

### DEBT-003: Session state transitions not atomic [HIGH]

**Location**: `persistence/session.py:47-58`
**Category**: BUG
**Blast Radius**: CROSS-CUTTING

**Description**: The `_state` attribute on SaveSession is modified without lock protection. In concurrent usage scenarios (multiple threads or async tasks using the same session), race conditions can cause invalid state transitions.

**Impact**:
- Race conditions in concurrent code
- Invalid state transitions
- Undefined behavior in multi-threaded contexts

**Recommended Fix**: Add threading.Lock for state transitions, or document that SaveSession is not thread-safe.

---

### DEBT-004: Cascade operations remain after partial failures [HIGH]

**Location**: `persistence/session.py:749-751`
**Category**: BUG
**Blast Radius**: MODULE

**Description**: When cascade operations fail, they remain in the queue without a max retry counter. This can cause infinite retry loops that never resolve and block progress.

**Impact**:
- Infinite retry loops
- Resource exhaustion
- Blocked commits

**Recommended Fix**: Implement max retry counter with exponential backoff; move to dead-letter queue after max attempts.

---

### DEBT-005: Concurrent track() calls race condition [HIGH]

**Location**: `persistence/session.py:367`
**Category**: BUG
**Blast Radius**: MODULE

**Description**: The `track()` method modifies entity snapshots without synchronization. Concurrent calls to track the same entity can corrupt the snapshot state.

**Impact**:
- Corrupted entity snapshots
- Inconsistent change detection
- Silent data corruption

**Recommended Fix**: Add per-entity locking or document single-threaded usage requirement.

---

### DEBT-006: Batch executor assumes sequential results [HIGH]

**Location**: `persistence/executor.py:106-108`
**Category**: BUG
**Blast Radius**: MODULE

**Description**: The batch executor assumes that API results arrive in the same order as requests and that the count matches. No validation is performed, which can cause mismatched result attribution.

**Impact**:
- Wrong results attributed to wrong entities
- Silent data corruption
- Incorrect success/failure reporting

**Recommended Fix**: Validate result count matches request count; use request IDs for correlation.

---

### DEBT-007: Circuit breaker hooks swallow exceptions [HIGH]

**Location**: `transport/circuit_breaker.py:196-219`
**Category**: BUG
**Blast Radius**: CROSS-CUTTING

**Description**: Exception handlers in circuit breaker hooks use bare `pass` statements, silently swallowing any exceptions that occur. This hides failures and makes debugging extremely difficult.

**Impact**:
- Hidden failures
- Difficult debugging
- Potential cascading issues from unhandled errors

**Recommended Fix**: Log exceptions at minimum; consider propagating or collecting for later inspection.

---

### DEBT-008: Half-open state max calls not enforced [HIGH]

**Location**: `transport/circuit_breaker.py:124-127`
**Category**: BUG
**Blast Radius**: MODULE

**Description**: In half-open state, the circuit breaker is supposed to limit probing calls. However, the counter can exceed the intended limit, allowing more traffic than desired through a potentially failing service.

**Impact**:
- Circuit breaker ineffective during recovery
- Potential cascade failures
- Service overload during recovery

**Recommended Fix**: Add atomic check-and-increment with strict enforcement.

---

### DEBT-009: Simple get/set bypass two-tier logic [HIGH]

**Location**: `cache/tiered.py:129-156`
**Category**: DESIGN_DEBT
**Blast Radius**: CROSS-CUTTING

**Description**: The simple `get()` and `set()` methods don't utilize the full two-tier logic (promotion, staleness checking, write-through). Clients using these methods get incomplete behavior and may experience consistency violations.

**Impact**:
- Inconsistent cache behavior based on method used
- Confusion about correct API usage
- Potential data inconsistency

**Recommended Fix**: Either route simple methods through full logic, or clearly deprecate and document the intended API.

---

### DEBT-010: Lock file UnboundLocalError risk [HIGH]

**Location**: `automation/polling/polling_scheduler.py:445-462`
**Category**: BUG
**Blast Radius**: MODULE

**Description**: The `lock_file` variable may be undefined when an OSError is caught during lock acquisition. Attempting to close or clean up the lock file will raise UnboundLocalError.

**Impact**:
- Unhandled exception in error path
- Potential lock file leaks
- Scheduler crash on lock errors

**Recommended Fix**: Initialize `lock_file = None` before try block; check before cleanup.

---

### DEBT-011: SearchCriteria OR combinator unsupported [HIGH]

**Location**: `search/models.py:52, 69`
**Category**: DESIGN_DEBT
**Blast Radius**: MODULE

**Description**: The SearchCriteria model includes an `or_` field suggesting OR combinator support, but only AND logic is implemented. This is a misleading API that may cause users to think OR queries work.

**Impact**:
- Misleading API contract
- User frustration when OR doesn't work
- Incomplete feature

**Recommended Fix**: Either implement OR support or remove the field with deprecation warning.

---

### DEBT-012: Code duplication in field comparisons [HIGH]

**Location**: `models/business/matching/engine.py:222-459`
**Category**: DESIGN_DEBT
**Blast Radius**: MODULE

**Description**: Four `_compare_*` methods (name, address, phone, email) follow an identical pattern with ~150 lines of boilerplate each. This violates DRY and makes maintenance error-prone.

**Impact**:
- Maintenance burden
- Inconsistent bug fixes
- Higher cognitive load

**Recommended Fix**: Extract common comparison logic into base method with strategy pattern for field-specific behavior.

---

### DEBT-013 to DEBT-015: API Routes Untested [HIGH]

**Locations**: `api/routes/dataframes.py`, `api/routes/projects.py`, `api/routes/sections.py`
**Category**: COVERAGE_GAP
**Blast Radius**: CROSS-CUTTING

**Description**: Critical user-facing API routes have 0% test coverage. These routes handle dataframes (455 lines), projects (351 lines), and sections (220 lines) - all core functionality.

**Impact**:
- Regressions undetected
- Confidence degradation
- Risky refactoring

**Recommended Fix**: Prioritize integration tests for these routes; consider contract testing.

---

### DEBT-016 to DEBT-017: Large Clients Low Coverage [HIGH]

**Locations**: `clients/goals.py`, `clients/portfolios.py`
**Category**: COVERAGE_GAP
**Blast Radius**: MODULE

**Description**: Goals client (1,124 lines) and Portfolios client (905 lines) have less than 30% test coverage despite being substantial codebases.

**Impact**:
- High risk of undetected bugs
- Regression risk during changes
- Technical debt accumulation

**Recommended Fix**: Establish coverage targets; prioritize critical paths.

---

### DEBT-018: SaveSession bloat and complexity [HIGH]

**Location**: `persistence/session.py`
**Category**: DESIGN_DEBT
**Blast Radius**: CROSS-CUTTING

**Description**: SaveSession has grown to 1,560 lines with 16 try/except blocks. This indicates the class has accumulated too many responsibilities and is difficult to maintain and reason about.

**Impact**:
- High cognitive load for developers
- Difficult to test comprehensively
- Prone to unintended side effects

**Recommended Fix**: Decompose into smaller, focused classes (e.g., StateManager, ActionQueue, CascadeHandler).

---

### DEBT-019: Tasks client overcrowded [HIGH]

**Location**: `clients/tasks.py`
**Category**: DESIGN_DEBT
**Blast Radius**: MODULE

**Description**: Tasks client contains 1,397 lines and 58 methods, indicating SRP violation. The class likely handles too many concerns.

**Impact**:
- Difficult navigation and maintenance
- Testing complexity
- Potential for method proliferation

**Recommended Fix**: Group related methods into sub-clients or mixins.

---

### DEBT-020: Test collection errors blocking coverage [HIGH]

**Location**: `pytest` (test infrastructure)
**Category**: COVERAGE_GAP
**Blast Radius**: SYSTEM

**Description**: 151 test collection errors are preventing the full test suite from running. This blocks coverage measurement and CI reliability.

**Impact**:
- Incomplete test execution
- Unknown coverage gaps
- CI reliability issues

**Recommended Fix**: Triage and fix collection errors systematically; consider quarantine strategy for persistent failures.

---

## Deduplication Notes

The following items from multiple exploration agents were consolidated:

### SaveSession Items (Agents 2 & 3)
- Agent 2 found 13 specific SaveSession issues
- Agent 3 flagged SaveSession for complexity (1,560 lines)
- **Resolution**: All specific issues retained with unique IDs; complexity noted as DEBT-018

### Sync/Async Wrapper Pattern (Agents 1 & 2)
- Agent 1: `automation/polling/service.py:392-457` - Five methods create new event loops
- Similar patterns in search service noted by Agent 1
- **Resolution**: Kept as separate items since they're in different modules with different fix strategies

### Client Cache Logic (Agent 2)
- BaseClient cache helpers swallow exceptions
- Duplicated cache logic across clients
- **Resolution**: Kept as separate items - DEBT-049 (exception swallowing) and DEBT-051 (duplication)

### API Route Coverage (Agent 3)
- Three routes with 0% coverage initially listed
- **Resolution**: Assigned individual IDs (DEBT-013 to DEBT-015) since each requires separate test suites

### Test Infrastructure (Agent 3)
- Collection errors (151) and scattered tests (5,458 lines)
- **Resolution**: DEBT-020 for collection errors (HIGH - blocks CI), DEBT-062 for organization (MEDIUM - maintenance)

---

## Audit Limitations

1. **Static Analysis Only**: This audit relies on code exploration and documented patterns. Runtime behavior and production metrics were not analyzed.

2. **Coverage Metrics Estimated**: Test coverage percentages are based on file examination and test presence, not actual coverage tools.

3. **Age/Ownership Not Determined**: Git blame was not run for individual items due to scope constraints. Age and ownership should be enriched in subsequent audits.

4. **Implicit Debt Gaps**: Some forms of implicit debt (e.g., performance bottlenecks, API response time degradation) require runtime profiling not performed here.

5. **Third-Party Dependencies**: Outdated dependencies and security vulnerabilities were not analyzed in this audit.

---

## Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| Debt Ledger | /Users/tomtenuta/Code/autom8_asana/.claude/sessions/session-20251228-114714-3062657f/artifacts/DEBT-LEDGER-20251228.md | YES |

---

*Generated by Debt Collector - debt-triage-pack*
*Next: Route to Risk Assessor for scoring and prioritization*
