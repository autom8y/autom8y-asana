# PRD-0009: SDK GA Readiness

## Metadata

- **PRD ID**: PRD-0009
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-10
- **Last Updated**: 2025-12-10
- **Stakeholders**: Tom (SDK owner), Internal development team
- **Related PRDs**: [PRD-0001](PRD-0001-sdk-extraction.md) (SDK Extraction), [PRD-0007](PRD-0007-sdk-functional-parity.md) (SDK Functional Parity)

---

## Problem Statement

The autom8_asana SDK implementation received a **"CONDITIONAL SHIP ⚠️"** verdict from pre-launch QA review. While the core implementation is production-ready with strong scores in correctness (8/10), error handling (9/10), and performance (8/10), critical gaps prevent General Availability:

| Dimension | Current Score | Status |
|-----------|---------------|--------|
| Documentation | 5/10 | ❌ Critical gap |
| Edge Case Coverage | 6/10 | ⚠️ Needs work |
| Developer Ergonomics | 7/10 | ⚠️ Steep learning curve |
| Production Readiness | 7/10 | ⚠️ Missing retry/circuit breaker |

**Impact of not solving**:
- Developers cannot discover how to use the SDK
- Users hit undocumented limitations and footguns
- No resilience against transient failures in production
- Failed adoption leads to support burden and frustrated users

---

## Goals & Success Metrics

| Goal | Current | Target | Measurement |
|------|---------|--------|-------------|
| Documentation score | 5/10 | ≥8/10 | QA re-review |
| Edge case coverage | 6/10 | ≥8/10 | QA re-review |
| Developer ergonomics | 7/10 | ≥8/10 | QA re-review |
| New developer onboarding | Unknown | <30 min | Time to first successful API call |
| Critical blockers | 3 | 0 | Checklist completion |
| QA verdict | CONDITIONAL SHIP | SHIP | Final QA review |

---

## Scope

### In Scope

**Documentation**:
- README.md with installation, quick example, and feature highlights
- Limitations documentation covering unsupported operations and footguns
- SaveSession guide explaining Unit of Work pattern
- SDK adoption migration guide for 3 source patterns (internal wrappers, asana-python, raw HTTP)

**Testing**:
- P0 boundary condition tests (empty strings, invalid GIDs, type mismatches)
- P1 boundary condition tests (unicode, emoji, large batches)

**Code Improvements**:
- Pre-commit validation (GID format, required fields)
- Footgun detection warnings (untracked modifications)
- Retry handler with exponential backoff
- Circuit breaker for cascading failure prevention

### Out of Scope

- ❌ Public PyPI publication (internal only for now)
- ❌ External developer documentation site
- ❌ Quick Start guide creation (already exists at `/examples/README.md`)
- ❌ Breaking changes to existing API surface
- ❌ New SDK features or API extensions
- ❌ Performance optimization (already exceeds targets)
- ❌ Tutorial videos or interactive guides

---

## Requirements

### Functional Requirements: Documentation (FR-DOC-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DOC-001 | Create README.md with project description, installation instructions, and quick example | Must | README exists, contains pip install command, shows 10-line working example |
| FR-DOC-002 | README includes feature matrix showing SDK capabilities | Must | Table lists all resource clients and key features |
| FR-DOC-003 | README includes badges for Python version and license | Should | Badges render correctly, link to relevant pages |
| FR-DOC-004 | Create limitations.md documenting 6 unsupported field modifications | Must | All 6 fields listed with correct workaround methods |
| FR-DOC-005 | Limitations doc includes all 10 footgun patterns with examples | Must | Each pattern has: severity, wrong code, correct code |
| FR-DOC-006 | Create save-session.md explaining Unit of Work pattern | Must | Covers track→modify→commit workflow with examples |
| FR-DOC-007 | Create sdk-adoption.md migration guide for 3 source patterns | Should | Separate sections for: internal wrappers, asana-python, raw HTTP |

### Functional Requirements: Footgun Documentation (FR-FG-*)

| ID | Pattern | Severity | Acceptance Criteria |
|----|---------|----------|---------------------|
| FR-FG-001 | Document direct list modification footgun (`task.tags.append()`) | HIGH | Shows wrong code, error message, and correct approach |
| FR-FG-002 | Document forgetting to track() entities | MEDIUM | Explains silent no-op, shows correct pattern |
| FR-FG-003 | Document multiple modifications before commit | LOW | Explains last-value-wins behavior |
| FR-FG-004 | Document using closed session | HIGH | Shows SessionClosedError, explains context manager scope |
| FR-FG-005 | Document insert_before + insert_after conflict | HIGH | Shows PositioningConflictError, explains mutual exclusivity |
| FR-FG-006 | Document dependency cycles | HIGH | Shows CyclicDependencyError, explains parent-child ordering |
| FR-FG-007 | Document partial save scenarios | MEDIUM | Explains SaveResult.partial, shows error handling |
| FR-FG-008 | Document temp GID leakage to logs | LOW | Explains temp_* pattern, warns about log inspection |
| FR-FG-009 | Document objects vs GID strings inconsistency | MEDIUM | Clarifies when to pass object vs string |
| FR-FG-010 | Document empty comment text | LOW | Shows ValueError, explains text/html_text requirement |

### Functional Requirements: Boundary Tests (FR-TEST-*)

| ID | Boundary Condition | Priority | Acceptance Criteria |
|----|-------------------|----------|---------------------|
| FR-TEST-001 | Empty string for task.name | Must | Test verifies API rejection with clear error |
| FR-TEST-002 | Very long strings (>65535 chars) | Must | Test verifies behavior (truncation or rejection) |
| FR-TEST-003 | Invalid GID format (malformed) | Must | Test verifies ValidationError with message |
| FR-TEST-004 | Invalid GID format (empty string) | Must | Test verifies ValidationError with message |
| FR-TEST-005 | Type mismatch in custom fields | Must | Test verifies TypeError with field info |
| FR-TEST-006 | None in required field positions | Must | Test verifies clear error before API call |
| FR-TEST-007 | Invalid GID with special characters | Should | Test verifies injection prevention |
| FR-TEST-008 | Unicode in text fields | Should | Test verifies encoding correctness |
| FR-TEST-009 | Emoji in task names/notes | Should | Test verifies 4-byte UTF-8 handling |
| FR-TEST-010 | Large batches (1000+ entities) | Should | Test verifies memory stability, timeout handling |

### Functional Requirements: Validation (FR-VAL-*)

| ID | Validation | Priority | Acceptance Criteria |
|----|-----------|----------|---------------------|
| FR-VAL-001 | Validate GID format at track() time | Must | Malformed GIDs raise ValidationError immediately |
| FR-VAL-002 | Warn when entity modified but not tracked | Should | Warning logged with entity type and modification |
| FR-VAL-003 | Validate empty task.name at track() time | Should | Empty names raise ValidationError before API call |
| FR-VAL-004 | Validate string length limits at track() time | Could | Over-length strings raise ValidationError with limit |

### Functional Requirements: Retry/Circuit Breaker (FR-RETRY-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-RETRY-001 | Configurable retry handler | Must | RetryConfig dataclass with all settings |
| FR-RETRY-002 | Exponential backoff with jitter | Must | Delay doubles each retry, ±20% jitter |
| FR-RETRY-003 | Retryable error detection | Must | Correctly identifies 429, 5xx, network errors |
| FR-RETRY-004 | Maximum retry count configuration | Must | Default 3, configurable 0-10 |
| FR-RETRY-005 | Circuit breaker with failure threshold | Must | Opens after N consecutive failures |
| FR-RETRY-006 | Half-open state with probe requests | Must | Allows single request to test recovery |
| FR-RETRY-007 | Integration with existing rate limiter | Must | Retry respects rate limit bucket |
| FR-RETRY-008 | Per-operation retry override | Should | Individual calls can disable/configure retry |
| FR-RETRY-009 | Retry event hooks (on_retry callback) | Should | Users can log/monitor retry attempts |
| FR-RETRY-010 | Circuit breaker event hooks | Should | Users notified of open/close transitions |

### Non-Functional Requirements

#### Discoverability (NFR-DISC-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-DISC-001 | All documentation discoverable from README | 100% | All docs linked from README |
| NFR-DISC-002 | SaveSession guide linked from session.py docstring | Yes | Docstring contains link |
| NFR-DISC-003 | Limitations doc linked from exception messages | Yes | UnsupportedOperationError includes doc link |

#### Backward Compatibility (NFR-COMPAT-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-COMPAT-001 | No breaking changes to public API | 0 breaks | All existing code continues to work |
| NFR-COMPAT-002 | Retry is opt-in (disabled by default) | Yes | Default behavior unchanged |
| NFR-COMPAT-003 | Validation errors don't break existing valid usage | 0 false positives | Existing tests pass |
| NFR-COMPAT-004 | Warnings don't affect control flow | Yes | Warnings are logged, not raised |

#### Performance (NFR-PERF-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-PERF-001 | Retry overhead per request | <5ms | Benchmark test |
| NFR-PERF-002 | Circuit breaker check | <1ms | Benchmark test |
| NFR-PERF-003 | Validation overhead at track() | <2ms | Benchmark test |
| NFR-PERF-004 | No memory increase for large entity sets | <10% | Memory profiling |

---

## User Stories / Use Cases

### US-001: New Developer Onboarding

> As a new developer, I want to find documentation quickly so that I can start using the SDK in under 30 minutes.

**Flow**: Find README → Read installation → Copy example → Run successfully → Explore examples

### US-002: Footgun Avoidance

> As a developer, when I make a common mistake like direct list modification, I want to receive a clear error message that tells me how to fix it.

**Flow**: Write `task.tags.append(tag)` → Attempt commit → Receive UnsupportedOperationError with "Use add_tag() instead"

### US-003: Understanding Limitations

> As a developer planning my implementation, I want to know what operations are NOT supported so that I don't waste time trying unsupported approaches.

**Flow**: Read limitations doc → Understand 6 unsupported fields → Plan around constraints

### US-004: Migration from Existing Code

> As a developer with existing Asana integration code, I want a clear migration path so that I can adopt the SDK without rewriting from scratch.

**Flow**: Identify current pattern (asana-python/wrappers/raw HTTP) → Follow relevant migration section → Convert code incrementally

### US-005: Production Resilience

> As a developer deploying to production, I want automatic retry with backoff so that transient failures don't cause cascade failures.

**Flow**: Configure RetryConfig → Enable on client → Transient 5xx automatically retried → Success on retry

### US-006: Circuit Breaker Protection

> As a developer, when Asana API is degraded, I want the SDK to stop hammering the failing service and recover automatically when it's healthy.

**Flow**: API returns errors → Circuit opens → Requests fail-fast locally → API recovers → Circuit half-opens → Probe succeeds → Circuit closes

---

## Assumptions

1. Internal team is the primary audience (can assume Asana domain knowledge)
2. Developers have Python 3.10+ environment
3. Existing test suite (506 tests) provides regression safety
4. Rate limiter implementation is correct and can be extended
5. `/examples/README.md` serves as Quick Start (no separate guide needed)

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| Existing SDK implementation | Tom | Complete |
| Rate limiter (TokenBucketRateLimiter) | Tom | Complete |
| Exception hierarchy | Tom | Complete |
| Test infrastructure (pytest, fixtures) | Tom | Complete |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Build custom retry vs use `tenacity` library? | Architect | Session 3 | Pending ADR |
| Validation strictness: error vs warn for boundary violations? | Architect | Session 3 | Recommend: error (fail-fast) |
| Should circuit breaker be shared across client instances? | Architect | Session 3 | TBD |

---

## Appendices

### Appendix A: Unsupported Fields Reference

| Field | Cannot Do | Must Use Instead |
|-------|-----------|------------------|
| `tags` | `task.tags.append(tag)` | `session.add_tag(task, tag)` |
| `projects` | `task.projects = [proj]` | `session.add_to_project(task, proj)` |
| `memberships` | Direct modification | `session.add_to_project()` / `remove_from_project()` |
| `dependencies` | `task.dependencies.append()` | `session.add_dependency(task, dep)` |
| `dependents` | `task.dependents.append()` | `session.add_dependent(task, dep)` |
| `followers` | `task.followers.append()` | `session.add_follower(task, user)` |

### Appendix B: Footgun Pattern Reference

| ID | Pattern | Severity | Example |
|----|---------|----------|---------|
| FG-001 | Direct list modification | HIGH | `task.tags.append(tag)` |
| FG-002 | Forgetting track() | MEDIUM | Modify without `session.track(entity)` |
| FG-003 | Multiple modifications | LOW | Change field twice before commit |
| FG-004 | Closed session | HIGH | Operate after context manager exits |
| FG-005 | Positioning conflict | HIGH | Both `insert_before` and `insert_after` |
| FG-006 | Dependency cycles | HIGH | A→B→C→A parent chain |
| FG-007 | Partial save | MEDIUM | Some entities fail, others succeed |
| FG-008 | Temp GID leakage | LOW | `temp_xxx` appears in logs |
| FG-009 | Object vs string | MEDIUM | Pass object when GID string expected |
| FG-010 | Empty comment | LOW | `add_comment(task, "")` |

### Appendix C: Boundary Test Matrix

| Condition | Input Example | Expected Behavior |
|-----------|---------------|-------------------|
| Empty task.name | `""` | ValidationError: "Task name cannot be empty" |
| Long string | 100,000 chars | ValidationError or API truncation |
| Malformed GID | `"not-a-gid"` | ValidationError: "Invalid GID format" |
| Empty GID | `""` | ValidationError: "GID cannot be empty" |
| Special chars in GID | `"; DROP TABLE"` | ValidationError: "Invalid GID format" |
| Unicode text | `"任务名称"` | Success (UTF-8 encoded) |
| Emoji | `"Task 🚀"` | Success (4-byte UTF-8) |
| Type mismatch | String to number field | TypeError with field name |
| None required | `task.name = None` | ValidationError: "name is required" |
| Large batch | 1000+ entities | Memory-stable, timeout-safe |

### Appendix D: Effort Estimates

| Category | Items | Effort |
|----------|-------|--------|
| Documentation (README, Limitations, SaveSession, Migration) | 4 docs | 2-3 days |
| Boundary Tests (P0 + P1) | 10 tests | 1-2 days |
| Validation Improvements | 4 validations | 1 day |
| Retry/Circuit Breaker | 10 requirements | 4-5 days |
| **Total** | | **8-11 days** |

### Appendix E: Documentation Structure

```
/
├── README.md                    [NEW - FR-DOC-001,002,003]
├── docs/
│   ├── guides/
│   │   ├── limitations.md       [NEW - FR-DOC-004,005]
│   │   ├── save-session.md      [NEW - FR-DOC-006]
│   │   ├── sdk-adoption.md      [NEW - FR-DOC-007]
│   │   └── autom8-migration.md  [EXISTS - S3→Redis]
│   └── INDEX.md                 [UPDATE - add new docs]
├── examples/
│   └── README.md                [EXISTS - Quick Start]
└── src/autom8_asana/
    └── persistence/
        └── session.py           [UPDATE - docstring link]
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-10 | Requirements Analyst | Initial draft from Discovery findings |
