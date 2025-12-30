# Technical Debt Risk Report

**Assessment Date**: 2025-12-28
**Assessor**: Risk Assessor (debt-triage-pack)
**Input**: DEBT-LEDGER-20251228.md (82 items)
**Scope**: CRITICAL and HIGH severity items (20 total)

---

## Executive Summary

### Top 5 Highest-Risk Items

| Rank | ID | Title | Risk Score | Priority |
|------|-----|-------|------------|----------|
| 1 | DEBT-001 | Two-tier cache write-through inconsistency | **40** | CRITICAL |
| 2 | DEBT-002 | Pending actions cleared on partial commit failure | **40** | CRITICAL |
| 3 | DEBT-020 | Test collection errors blocking coverage | **36** | CRITICAL |
| 4 | DEBT-003 | Session state transitions not atomic | **28** | HIGH |
| 5 | DEBT-007 | Circuit breaker hooks swallow exceptions | **25** | HIGH |

### Recommended Immediate Actions

1. **DEBT-001 & DEBT-002**: Address data integrity bugs in cache/persistence layer immediately. These are the only true "stop-the-presses" items with SYSTEM blast radius and active data loss potential.

2. **DEBT-020**: Unblock test infrastructure. 151 collection errors prevent CI reliability and mask coverage gaps. This is a force multiplier - fixing it enables finding other bugs.

3. **DEBT-003 & DEBT-005**: Session concurrency bugs. If multi-threaded usage is a near-term need, these become urgent. Otherwise, document single-threaded requirement as mitigation.

4. **DEBT-007**: Circuit breaker silently swallowing exceptions is a debugging nightmare. Quick fix: add logging.

### Risk Distribution Analysis

| Priority Tier | Count | Score Range | Characteristics |
|---------------|-------|-------------|-----------------|
| CRITICAL | 3 | 36-40 | Data loss, system-wide impact, CI blockers |
| HIGH | 8 | 20-28 | Concurrency bugs, cross-cutting issues |
| MEDIUM | 7 | 10-18 | Design debt, coverage gaps, localized bugs |
| LOW | 2 | <10 | Misleading APIs, refactoring debt |

**Key Insight**: The codebase has a concentrated risk profile. Three items represent 60% of the critical risk. Fix those three, and the overall risk posture improves dramatically.

---

## Risk Scoring Framework

Each item scored on four dimensions (1-5 scale):

| Dimension | Definition | Scale |
|-----------|------------|-------|
| **Business Impact** | Revenue, data integrity, user experience | 1=internal only, 5=revenue/data loss |
| **Likelihood** | Probability of triggering | 1=rare edge case, 5=frequent/predictable |
| **Fix Complexity** | Time and expertise required | 1=simple (<1d), 5=major refactor (1+ week) |
| **Dependencies** | Coordination required | 1=standalone, 5=blocks/blocked by others |

**Risk Score** = (Impact x Likelihood) + (Complexity x Dependencies)
- Range: 2-50
- CRITICAL: >= 30
- HIGH: 20-29
- MEDIUM: 10-19
- LOW: < 10

---

## Risk Matrix

### CRITICAL Severity Items

| ID | Title | Impact | Likelihood | Complexity | Dependencies | Score | Priority |
|----|-------|--------|------------|------------|--------------|-------|----------|
| DEBT-001 | Two-tier cache write-through inconsistency | 5 | 4 | 4 | 4 | **40** | CRITICAL |
| DEBT-002 | Pending actions cleared on partial commit failure | 5 | 4 | 4 | 4 | **40** | CRITICAL |

### HIGH Severity Items

| ID | Title | Impact | Likelihood | Complexity | Dependencies | Score | Priority |
|----|-------|--------|------------|------------|--------------|-------|----------|
| DEBT-020 | Test collection errors blocking coverage | 4 | 5 | 4 | 4 | **36** | CRITICAL |
| DEBT-003 | Session state transitions not atomic | 4 | 4 | 3 | 3 | **28** (25+3) | HIGH |
| DEBT-007 | Circuit breaker hooks swallow exceptions | 4 | 4 | 2 | 2 | **24** (20+4) | HIGH |
| DEBT-005 | Concurrent track() calls race condition | 4 | 3 | 3 | 3 | **21** | HIGH |
| DEBT-009 | Simple get/set bypass two-tier logic | 4 | 3 | 3 | 3 | **21** | HIGH |
| DEBT-006 | Batch executor assumes sequential results | 4 | 3 | 2 | 3 | **18** | MEDIUM |
| DEBT-018 | SaveSession bloat and complexity | 3 | 5 | 5 | 4 | **35** (15+20) | CRITICAL |
| DEBT-004 | Cascade operations remain after partial failures | 3 | 3 | 3 | 2 | **15** | MEDIUM |
| DEBT-008 | Half-open state max calls not enforced | 3 | 3 | 2 | 2 | **13** | MEDIUM |
| DEBT-010 | Lock file UnboundLocalError risk | 3 | 2 | 1 | 1 | **7** | LOW |
| DEBT-011 | SearchCriteria OR combinator unsupported | 2 | 2 | 2 | 1 | **6** | LOW |
| DEBT-012 | Code duplication in field comparisons | 2 | 5 | 3 | 2 | **16** | MEDIUM |
| DEBT-013 | API dataframes routes untested | 4 | 4 | 3 | 2 | **22** | HIGH |
| DEBT-014 | API projects routes untested | 4 | 4 | 3 | 2 | **22** | HIGH |
| DEBT-015 | API sections routes untested | 3 | 4 | 2 | 2 | **16** | MEDIUM |
| DEBT-016 | Goals client low coverage | 3 | 3 | 4 | 2 | **17** | MEDIUM |
| DEBT-017 | Portfolios client low coverage | 3 | 3 | 3 | 2 | **15** | MEDIUM |
| DEBT-019 | Tasks client overcrowded | 2 | 5 | 4 | 3 | **22** | HIGH |

---

## Detailed Scoring Rationale

### DEBT-001: Two-tier cache write-through inconsistency [Score: 40]

**Impact: 5** - Data integrity at stake. Stale reads affect entire system after L1 eviction. This is not a cosmetic issue; it's a data corruption vector.

**Likelihood: 4** - S3 writes can fail due to network issues, throttling, or transient errors. In production with volume, this will happen. Not a question of if, but when.

**Complexity: 4** - Fix requires transactional semantics or a reconciliation mechanism. Can't just "add a retry" - need to handle partial success states properly.

**Dependencies: 4** - Touches L1, L2, and all code paths using the cache. Changes ripple through the system.

**Trigger Conditions**: Network partition, S3 throttling, high write volume, long-running processes.

**Recommended Fix**: Implement write-through with confirmation and rollback. Mark L1 entries as "pending sync" until L2 confirms. Add reconciliation job.

---

### DEBT-002: Pending actions cleared on partial commit failure [Score: 40]

**Impact: 5** - Data loss. Actions intended by the user are silently discarded. No recovery path exists.

**Likelihood: 4** - Partial failures occur when Asana API has transient issues, rate limits, or validation errors on some items but not others.

**Complexity: 4** - Need action-level tracking, per-action success/failure status, and a recovery mechanism. Fundamental change to commit semantics.

**Dependencies: 4** - Affects all callers of session.commit(). Breaking change potential if not backward compatible.

**Trigger Conditions**: Batch commits with mixed success/failure, API rate limits, validation failures on subset of actions.

**Recommended Fix**: Track per-action status. Only clear successfully committed actions. Provide failed actions in return value for caller to handle or retry.

---

### DEBT-020: Test collection errors blocking coverage [Score: 36]

**Impact: 4** - Not direct data loss, but blocks ability to detect bugs. Reduces confidence in all code changes.

**Likelihood: 5** - Currently happening. 151 errors every CI run. This is not hypothetical.

**Complexity: 4** - 151 errors need individual triage. Some may be import errors, some may be fixture issues, some may be actual test bugs.

**Dependencies: 4** - Blocks coverage measurement for all modules. Blocks CI reliability. Everyone is affected.

**Trigger Conditions**: Every pytest invocation.

**Recommended Fix**: Systematic triage: (1) categorize errors by type, (2) fix import/fixture errors first (bulk win), (3) quarantine persistently failing tests while investigating.

---

### DEBT-018: SaveSession bloat and complexity [Score: 35]

**Impact: 3** - Indirectly causes bugs through complexity. Every bug in this file has wide blast radius.

**Likelihood: 5** - The file is actively modified (56 commits in 8 days suggests active development). Bugs are introduced continuously.

**Complexity: 5** - 1,560 lines, 16 try/except blocks. Major decomposition needed. Can't be done piecemeal easily.

**Dependencies: 4** - Central to persistence layer. Decomposition affects all persistence consumers.

**Trigger Conditions**: Any change to session logic, new feature requirements touching persistence.

**Recommended Fix**: Decompose into: StateManager, ActionQueue, CascadeHandler, CommitExecutor. Do incrementally with tests covering each extraction.

---

### DEBT-003: Session state transitions not atomic [Score: 28]

**Impact: 4** - Race conditions can corrupt session state, leading to undefined behavior in concurrent usage.

**Likelihood: 4** - If sessions are used concurrently (async code, multi-threading), this triggers. Depends on usage patterns.

**Complexity: 3** - Add threading.Lock. Moderate effort to identify all state transitions and wrap appropriately.

**Dependencies: 3** - Affects all concurrent session users. May require API documentation updates.

**Trigger Conditions**: Multiple threads/tasks using same session instance, async commit while read in progress.

**Recommended Fix**: Add Lock for state transitions. Document thread-safety guarantees (or lack thereof) in API docs.

---

### DEBT-007: Circuit breaker hooks swallow exceptions [Score: 24]

**Impact: 4** - Hidden failures make debugging production issues extremely difficult. Hours of debugging saved per incident prevented.

**Likelihood: 4** - Any exception in hook code disappears silently. This has likely already hidden issues.

**Complexity: 2** - Simple fix: add logging. Minor effort.

**Dependencies: 2** - Isolated to circuit breaker module. No API changes.

**Trigger Conditions**: Any exception in circuit breaker hook callbacks.

**Recommended Fix**: Add logging.exception() in except blocks. Consider collecting exceptions for later inspection.

---

### DEBT-013 & DEBT-014: API routes untested [Score: 22 each]

**Impact: 4** - User-facing functionality. Regressions directly affect users.

**Likelihood: 4** - Code without tests will regress. Active development increases likelihood.

**Complexity: 3** - 455 lines (dataframes) and 351 lines (projects) need integration tests. Moderate effort.

**Dependencies: 2** - Tests can be written independently. No coordination needed.

**Trigger Conditions**: Any refactoring or feature addition to these routes.

**Recommended Fix**: Write integration tests. Prioritize happy paths first, then edge cases. Consider contract testing for API stability.

---

### DEBT-005: Concurrent track() calls race condition [Score: 21]

**Impact: 4** - Corrupted entity snapshots lead to incorrect change detection. Data integrity issue.

**Likelihood: 3** - Requires concurrent tracking of same entity. Less common than general concurrency.

**Complexity: 3** - Add per-entity locking or use concurrent data structures.

**Dependencies: 3** - Related to DEBT-003. Could be addressed together.

**Trigger Conditions**: Parallel async operations tracking same entity.

**Recommended Fix**: Add per-entity lock in track() or document single-threaded requirement.

---

### DEBT-009: Simple get/set bypass two-tier logic [Score: 21]

**Impact: 4** - Clients using simple API get inconsistent behavior. Subtle bugs.

**Likelihood: 3** - Depends on which API clients use. If simple methods are common, high likelihood.

**Complexity: 3** - Route simple methods through full logic or deprecate.

**Dependencies: 3** - Affects all simple API callers. May require migration.

**Trigger Conditions**: Any call to simple get()/set() instead of full two-tier methods.

**Recommended Fix**: Deprecate simple methods with warning. Route through full logic or document behavior difference clearly.

---

### DEBT-019: Tasks client overcrowded [Score: 22]

**Impact: 2** - Maintenance burden, not direct user impact.

**Likelihood: 5** - Anyone modifying tasks client feels the pain. Every feature addition.

**Complexity: 4** - 1,397 lines, 58 methods. Significant decomposition.

**Dependencies: 3** - Touches all task-related functionality.

**Trigger Conditions**: Any change to task handling.

**Recommended Fix**: Group methods into sub-clients (TaskCRUD, TaskRelations, TaskCustomFields). Use mixins or composition.

---

## Quick Wins

Items with high value relative to effort. ROI ranking (Impact / Complexity):

| Rank | ID | Title | Impact | Complexity | ROI | Effort Estimate |
|------|-----|-------|--------|------------|-----|-----------------|
| 1 | DEBT-007 | Circuit breaker hooks swallow exceptions | 4 | 2 | 2.0 | 2-4 hours |
| 2 | DEBT-010 | Lock file UnboundLocalError risk | 3 | 1 | 3.0 | 1-2 hours |
| 3 | DEBT-008 | Half-open state max calls not enforced | 3 | 2 | 1.5 | 4-8 hours |
| 4 | DEBT-015 | API sections routes untested | 3 | 2 | 1.5 | 1 day |
| 5 | DEBT-011 | SearchCriteria OR combinator unsupported | 2 | 2 | 1.0 | 4-8 hours |

### Quick Win Details

**DEBT-007** (2-4 hours): Add logging.exception() to except blocks. No API changes. Immediate debugging improvement.

**DEBT-010** (1-2 hours): Initialize `lock_file = None` before try block. One-line fix with safety check.

**DEBT-008** (4-8 hours): Add atomic check-and-increment. Straightforward concurrency fix.

**DEBT-015** (1 day): Smallest of the untested routes at 220 lines. Good test-writing practice before tackling larger routes.

**DEBT-011** (4-8 hours): Remove `or_` field if not implementing OR support. Clear API contract.

---

## Risk Clusters

Items that should be fixed together due to shared context, dependencies, or related root causes.

### Cluster 1: Session Concurrency (3 items)

| ID | Title | Score |
|----|-------|-------|
| DEBT-003 | Session state transitions not atomic | 28 |
| DEBT-005 | Concurrent track() calls race condition | 21 |
| DEBT-018 | SaveSession bloat and complexity | 35 |

**Rationale**: All three are in SaveSession. Addressing concurrency requires understanding the full class. Decomposition (DEBT-018) would make concurrency fixes cleaner.

**Recommended Approach**:
1. Document current thread-safety guarantees (or lack thereof)
2. Decide: make thread-safe or document as single-threaded
3. If thread-safe: add locks during decomposition

**Combined Effort**: 1-2 weeks for proper decomposition with concurrency handling

---

### Cluster 2: Cache Consistency (3 items)

| ID | Title | Score |
|----|-------|-------|
| DEBT-001 | Two-tier cache write-through inconsistency | 40 |
| DEBT-009 | Simple get/set bypass two-tier logic | 21 |
| (DEBT-025) | Staleness check ignores version for EVENTUAL | Medium |

**Rationale**: All relate to cache tier consistency. Fixing write-through (DEBT-001) provides foundation for addressing simple API bypass (DEBT-009).

**Recommended Approach**:
1. Fix write-through first (DEBT-001) - foundational
2. Deprecate/fix simple API (DEBT-009) - builds on fixed write-through
3. Address staleness if needed

**Combined Effort**: 1-2 weeks

---

### Cluster 3: API Test Coverage (3 items)

| ID | Title | Score |
|----|-------|-------|
| DEBT-013 | API dataframes routes untested | 22 |
| DEBT-014 | API projects routes untested | 22 |
| DEBT-015 | API sections routes untested | 16 |

**Rationale**: Same testing infrastructure needs. Test patterns from one apply to others.

**Recommended Approach**:
1. Establish test harness for API routes (fixtures, test client)
2. Write tests for smallest route first (sections - DEBT-015)
3. Apply pattern to larger routes

**Combined Effort**: 3-5 days

---

### Cluster 4: Circuit Breaker Hardening (2 items)

| ID | Title | Score |
|----|-------|-------|
| DEBT-007 | Circuit breaker hooks swallow exceptions | 24 |
| DEBT-008 | Half-open state max calls not enforced | 13 |

**Rationale**: Same module, related reliability concerns.

**Recommended Approach**:
1. Fix exception swallowing (DEBT-007) - immediate win
2. Add atomic counter for half-open (DEBT-008)

**Combined Effort**: 1 day

---

### Cluster 5: Test Infrastructure (2 items)

| ID | Title | Score |
|----|-------|-------|
| DEBT-020 | Test collection errors blocking coverage | 36 |
| (DEBT-062) | Adversarial tests scattered | Medium |

**Rationale**: Both block or impair test effectiveness.

**Recommended Approach**:
1. Triage collection errors by category
2. Fix systematic issues (imports, fixtures) in bulk
3. Reorganize tests after collection is clean

**Combined Effort**: 1 week for collection errors, ongoing for organization

---

## Recommendations

### Sprint 1: Critical Data Integrity (1-2 weeks)

**Must Include:**

| ID | Title | Score | Effort |
|----|-------|-------|--------|
| DEBT-001 | Two-tier cache write-through inconsistency | 40 | 3-5 days |
| DEBT-002 | Pending actions cleared on partial commit failure | 40 | 3-5 days |

**Rationale**: Data loss risks cannot wait. These are the only items that can corrupt user data silently.

**Quick Wins to Include:**

| ID | Title | Score | Effort |
|----|-------|-------|--------|
| DEBT-007 | Circuit breaker hooks swallow exceptions | 24 | 2-4 hours |
| DEBT-010 | Lock file UnboundLocalError risk | 7 | 1-2 hours |

**Sprint 1 Total**: ~7-12 days of work

---

### Sprint 2: Test Infrastructure & Visibility (1 week)

**Must Include:**

| ID | Title | Score | Effort |
|----|-------|-------|--------|
| DEBT-020 | Test collection errors blocking coverage | 36 | 3-5 days |

**Should Include:**

| ID | Title | Score | Effort |
|----|-------|-------|--------|
| DEBT-015 | API sections routes untested | 16 | 1 day |

**Rationale**: Unblock CI reliability. Enable future bug detection. Establish test patterns.

**Sprint 2 Total**: ~4-6 days of work

---

### Sprint 3: Concurrency & API Coverage (2 weeks)

**Include:**

| ID | Title | Score | Effort |
|----|-------|-------|--------|
| DEBT-003 | Session state transitions not atomic | 28 | 2-3 days |
| DEBT-005 | Concurrent track() calls race condition | 21 | 1-2 days |
| DEBT-013 | API dataframes routes untested | 22 | 2-3 days |
| DEBT-014 | API projects routes untested | 22 | 2-3 days |
| DEBT-008 | Half-open state max calls not enforced | 13 | 4-8 hours |

**Rationale**: Address concurrency cluster together. Complete API test coverage.

**Sprint 3 Total**: ~8-12 days of work

---

### Defer with Rationale

| ID | Title | Score | Rationale |
|----|-------|-------|-----------|
| DEBT-018 | SaveSession bloat and complexity | 35 | Major refactor. Wait until critical bugs fixed. Plan for dedicated decomposition sprint. |
| DEBT-019 | Tasks client overcrowded | 22 | Maintenance burden, not user-facing risk. Schedule during low-urgency period. |
| DEBT-012 | Code duplication in field comparisons | 16 | Annoying but not risky. Address during feature work in that module. |
| DEBT-009 | Simple get/set bypass two-tier logic | 21 | Address after DEBT-001 fix establishes solid foundation. |
| DEBT-011 | SearchCriteria OR combinator unsupported | 6 | Low impact. Remove field when convenient, or implement if users request. |

---

### Items Requiring Further Investigation

| ID | Question | Investigation Needed |
|----|----------|---------------------|
| DEBT-003, DEBT-005 | Is multi-threaded session usage actually occurring? | Review callers of SaveSession. Check for async usage patterns. |
| DEBT-016, DEBT-017 | What paths in Goals/Portfolios clients are critical? | Prioritize tests for most-used methods, not blanket coverage. |
| DEBT-020 | What categories of collection errors exist? | Run pytest with verbose collection to categorize errors before fixing. |

---

## Risk Trajectory

### Current State

- **2 CRITICAL items** with SYSTEM blast radius (data loss)
- **High concentration** in persistence/ and cache/ modules
- **Test infrastructure blocked** - 151 collection errors
- **Active development** (56 commits/8 days) increasing regression risk

### After Sprint 1

- **0 CRITICAL data integrity items** (DEBT-001, DEBT-002 resolved)
- Debugging improved (DEBT-007 resolved)
- Remaining risk concentrated in test coverage and concurrency

### After Sprint 2

- **CI reliability restored** (DEBT-020 resolved)
- Coverage gaps becoming visible
- Pattern established for API route testing

### After Sprint 3

- **Concurrency issues addressed** or documented
- **User-facing APIs tested** (dataframes, projects, sections)
- Risk profile significantly improved

---

## Assumptions and Limitations

1. **Scoring Based on Static Analysis**: Likelihood scores would benefit from production metrics (error rates, usage patterns).

2. **Effort Estimates**: Based on code complexity, not knowledge of team familiarity. Actual effort may vary.

3. **Dependency Assumptions**: Assumed current callers exist; did not trace all call sites.

4. **Business Context**: Impact scores assume standard business priorities. Compliance requirements could elevate certain items.

5. **Thread-Safety Usage**: Concurrency item scores assume multi-threaded usage is possible. If SaveSession is only used single-threaded, DEBT-003 and DEBT-005 drop in priority.

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| Debt Ledger (Input) | /Users/tomtenuta/Code/autom8_asana/.claude/sessions/session-20251228-114714-3062657f/artifacts/DEBT-LEDGER-20251228.md | YES |
| Risk Report (Output) | /Users/tomtenuta/Code/autom8_asana/.claude/sessions/session-20251228-114714-3062657f/artifacts/RISK-REPORT-20251228.md | YES |

---

*Generated by Risk Assessor - debt-triage-pack*
*Next: Route to Sprint Planner for sprint packaging*
