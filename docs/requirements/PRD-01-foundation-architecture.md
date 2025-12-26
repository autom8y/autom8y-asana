# PRD-01: Foundation & SDK Architecture

> Consolidated Product Requirements Document for SDK extraction, architecture hardening, and operational stability.

## Metadata

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2025-12-25 |
| **Consolidated From** | PRD-SDK-FAMILY, PRD-0015-foundation-hardening, PRD-0004-test-hang-fix |
| **Related TDD** | TDD-01-foundation-architecture |
| **Target Users** | SDK consumers, SDK maintainers, Operations teams |

---

## Executive Summary

The autom8_asana SDK provides a protocol-based, async-first Python client for the Asana API. This consolidated PRD captures requirements across four evolution phases:

1. **Foundation** - SDK extraction from monolith with protocol-based architecture
2. **Expansion** - Functional parity with Asana's task action API endpoints
3. **Hardening** - GA readiness through documentation, validation, and resilience
4. **Validation** - Interactive demonstration suite proving operational correctness

Additionally, this document incorporates foundation-layer hardening (exception hygiene, API surface cleanup, observability hooks) and test infrastructure stability (thread join timeouts, async patterns).

---

## Problem Statement

### Core Architecture Challenge

The autom8 monolith contained tightly coupled Asana API functionality that needed extraction into a standalone, reusable SDK. Key challenges:

- **Coupling** - Imports from `sql/`, `contente_api/`, `aws_api/` prevented standalone usage
- **Action gaps** - SaveSession lacked followers, likes, comments, positioning operations
- **Documentation debt** - No discovery path for new developers (5/10 QA score)
- **Production resilience** - No circuit breaker or structured observability

### Foundation Layer Technical Debt

The SDK foundation accumulated debt impacting developer experience:

- **Exception naming conflict** - `ValidationError` shadows `pydantic.ValidationError`
- **Private function leakage** - 3 private functions incorrectly exported in `__all__`
- **Incomplete type coverage** - 3 stub holders return untyped `Task` children
- **Inconsistent logging** - 22+ modules with varying patterns, no structured format
- **No observability hooks** - No protocol for telemetry/metrics integration

### Test Infrastructure Stability

Five tests could hang indefinitely due to:

- Missing thread join timeouts (3 test files)
- Untracked fire-and-forget threads (1 test)
- asyncio anti-pattern blocking event loop (1 test)

---

## Goals & Non-Goals

### Goals

| ID | Goal | Phase |
|----|------|-------|
| G1 | Extract pure Asana API functionality into standalone SDK | Foundation |
| G2 | Achieve 92%+ coverage of Asana task action endpoints | Expansion |
| G3 | Reach documentation score >= 8/10 for GA readiness | Hardening |
| G4 | Prove SDK via executable interactive demonstration | Validation |
| G5 | Eliminate exception naming conflicts with common libraries | Hardening |
| G6 | Clean API surface with only public functions exported | Hardening |
| G7 | Define extensibility point for observability integration | Hardening |
| G8 | Prevent test suite hangs with thread join timeouts | Stability |

### Non-Goals

| Item | Reason |
|------|--------|
| Concrete observability implementations | Integration-specific; only define protocol |
| Full domain modeling for stub holder children | Custom fields unknown; minimal models sufficient |
| Restructuring exception hierarchy | Would break backward compatibility |
| Adding logging to all modules | Only standardize existing patterns |
| Test architecture refactoring | Out of scope for hang prevention |
| Performance optimization of tests | Focus is stability, not speed |

---

## Requirements

### Functional Requirements

#### Transport Layer (FR-SDK-001-015)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-SDK-001 | Connection pooling with SSL/TLS configuration | Must |
| FR-SDK-002 | Token-bucket rate limiting (1500 req/min) | Must |
| FR-SDK-003 | Automatic retry on 429/503/504 with exponential backoff + jitter | Must |
| FR-SDK-004 | Concurrency limits: 50 concurrent reads, 15 concurrent writes | Must |
| FR-SDK-005 | Thread safety for shared client instances | Must |

#### Resource Clients (FR-SDK-016-029)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-SDK-016 | 13 resource clients (Tasks, Projects, Sections, CustomFields, Webhooks, Users, Teams, Attachments, Tags, Goals, Portfolios, Workspaces, Stories) | Must |
| FR-SDK-017 | Unified `AsanaClient` facade as single entry point | Must |
| FR-SDK-018 | Async-first API with sync wrappers for compatibility | Must |

#### Batch API (FR-SDK-030-035)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-SDK-030 | Batch request composition with automatic chunking | Must |
| FR-SDK-031 | Partial failure handling with per-item error attribution | Must |
| FR-SDK-032 | Automatic pagination for large result sets | Must |

#### Boundary Protocols (FR-BOUNDARY-001-007)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-BOUNDARY-001 | `AuthProvider` protocol for token/secret retrieval | Must |
| FR-BOUNDARY-002 | `CacheProvider` protocol for get/set/delete interface | Must |
| FR-BOUNDARY-003 | `LogProvider` protocol with Python logging compatibility | Must |
| FR-BOUNDARY-004 | Default no-op implementations for standalone usage | Must |

#### Action Endpoints (FR-POS/FOL/DEP/LIK/CMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-POS-001 | Extend `add_to_project()` with `insert_before`, `insert_after` | Must |
| FR-FOL-001 | `add_follower(task, user)`, `remove_follower(task, user)` methods | Must |
| FR-DEP-001 | `add_dependent(A, B)` for inverse dependency relationships | Must |
| FR-LIK-001 | `add_like(task)`, `remove_like(task)` idempotent operations | Must |
| FR-CMT-001 | `add_comment(task, text)` with deferred execution | Must |

#### Exception Hierarchy (FR-EXC-001-006)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-EXC-001 | Rename `ValidationError` to `GidValidationError` | Must |
| FR-EXC-002 | Maintain backward compatibility alias with deprecation warning | Must |
| FR-EXC-003 | Export `PositioningConflictError` in persistence module | Must |
| FR-EXC-004 | Export `GidValidationError` in persistence module | Must |

#### API Surface Cleanup (FR-ALL-001-004)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-ALL-001 | Remove `_traverse_upward_async` from `__all__` | Must |
| FR-ALL-002 | Remove `_convert_to_typed_entity` from `__all__` | Must |
| FR-ALL-003 | Remove `_is_recoverable` from `__all__` | Must |
| FR-ALL-004 | Verify no other `__init__.py` exports private functions | Must |

#### Stub Holder Typed Models (FR-STUB-001-010)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-STUB-001 | Create `DNA` model as minimal `BusinessEntity` subclass | Must |
| FR-STUB-002 | Create `Reconciliation` model as minimal `BusinessEntity` subclass | Must |
| FR-STUB-003 | Create `Videography` model as minimal `BusinessEntity` subclass | Must |
| FR-STUB-004 | Update holders to return typed lists | Must |

#### Observability Protocol (FR-OBS-001-012)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-OBS-001 | Define `ObservabilityHook` protocol in `protocols/observability.py` | Must |
| FR-OBS-002 | Include `on_request_start`, `on_request_end`, `on_request_error` methods | Must |
| FR-OBS-003 | Include `on_rate_limit`, `on_circuit_breaker_state_change`, `on_retry` | Should |
| FR-OBS-004 | Create `NullObservabilityHook` default implementation | Must |

#### Thread Join Timeouts (FR-THREAD-001-004)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-THREAD-001 | Add 10s timeout to thread joins in `test_concurrent_projects_access` | Must |
| FR-THREAD-002 | Add 10s timeout to thread joins in `test_concurrent_index_building` | Must |
| FR-THREAD-003 | Add 10s timeout to thread joins in `test_singleton_thread_safety` | Must |
| FR-THREAD-004 | Track and join callback threads in `test_no_deadlock_on_nested_locks` | Must |

#### Async Pattern (FR-ASYNC-001)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-ASYNC-001 | Convert `asyncio.run()` to async test pattern in test_client.py | Should |

### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-001 | Package size | < 5MB wheel |
| NFR-002 | Cold import time | < 500ms |
| NFR-003 | Test coverage on core modules | >= 80% |
| NFR-004 | Backward compatibility for exception handling | 100% via alias |
| NFR-005 | No new external dependencies | 0 new deps |
| NFR-006 | Logging zero-cost when disabled | <1% overhead |
| NFR-007 | Type checker compatibility | mypy passes |
| NFR-008 | Thread timeout behavior | Fail within 10s, not hang |

---

## User Stories

### US-001: Standalone SDK Usage

**As a** developer building an Asana integration,
**I want** to install autom8_asana without dependencies on autom8 internals,
**So that** I can use it as a standalone Asana client.

### US-002: Batch Task Updates

**As a** developer updating multiple tasks,
**I want** SaveSession to handle followers, likes, comments, and positioning,
**So that** I have complete API coverage without raw HTTP calls.

### US-003: Import Without Conflicts

**As a** developer using both autom8_asana and Pydantic,
**I want** to import `ValidationError` from Pydantic without SDK conflicts,
**So that** I can use both libraries without import aliasing.

### US-004: Type-Safe Holder Children

**As a** developer navigating the Business hierarchy,
**I want** `business.dna_holder.children` to return typed `DNA` instances,
**So that** my type checker provides accurate completions.

### US-005: Custom Metrics Integration

**As a** platform team member,
**I want** to plug in our metrics library via `ObservabilityHook`,
**So that** we can monitor SDK behavior in production dashboards.

### US-006: Reliable CI Pipeline

**As a** developer running tests,
**I want** tests to fail fast with clear errors instead of hanging,
**So that** CI pipelines complete reliably.

---

## Success Metrics

### SDK Extraction (Phase 1)

| Metric | Target |
|--------|--------|
| Coupling eliminated | Zero imports from `sql/`, `contente_api/`, `aws_api/` |
| Package size | < 5MB wheel |
| Cold import | < 500ms |
| Test coverage | >= 80% on core modules |
| Backward compatibility | All existing tests pass |

### Functional Parity (Phase 2)

| Metric | Target |
|--------|--------|
| Action coverage | 92% of Asana task actions |
| New methods | 9 new + 2 extended methods |
| Regression count | 0 (all 327 existing tests pass) |
| Type safety | 100% mypy strict compliance |

### GA Readiness (Phase 3)

| Metric | Target |
|--------|--------|
| Documentation score | >= 8/10 |
| Edge case coverage | >= 8/10 |
| Developer ergonomics | >= 8/10 |
| New developer onboarding | < 30 minutes |

### Foundation Hardening

| Metric | Target |
|--------|--------|
| Exception import conflicts | 0 |
| Private functions in `__all__` | 0 |
| Stub holders with typed children | 3/3 |
| ObservabilityProtocol defined | Yes |

### Test Stability

| Metric | Target |
|--------|--------|
| Full suite passes | `make test` completes without hangs |
| Stability validation | 10 consecutive runs complete |
| No regressions | All ~1850 tests pass |
| Timeout behavior | Fail within 10s, not hang |

---

## Dependencies

### Internal Dependencies

| Dependency | Purpose |
|------------|---------|
| ADR-0002 (Async design) | Documents `SyncInAsyncContextError` inheritance |
| Existing `BusinessEntity` base class | New stub models inherit from it |
| Python `typing.Protocol` | Used for `ObservabilityHook` |

### External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| httpx | Latest | Async-first HTTP client |
| asana | 5.0.3+ | Official SDK types/errors |
| pytest-asyncio | Configured | Async test support (`asyncio_mode = "auto"`) |
| pytest-timeout | Configured | 60s global timeout |

---

## Timeline

### Phase 1: Foundation (Complete)

- SDK extraction from monolith
- Protocol-based architecture
- 327 tests passing

### Phase 2: Expansion (Complete)

- All 9 action types implemented
- Positioning support added
- Functional parity achieved

### Phase 3: Hardening (In Progress)

- Documentation: README, limitations.md, save-session.md complete
- GID format validation implemented
- Circuit breaker implementation planned
- Exception hierarchy cleanup
- Observability protocol definition

### Phase 4: Validation (In Progress)

- Demo script suite designed
- Implementation in progress

### Test Stability (Complete)

- Thread join timeouts added
- Fire-and-forget threads tracked
- Async pattern corrected

---

## Cross-Cutting Concerns

### Security

- **No hardcoded secrets** - All auth via protocols
- **Input validation** - GID format, field values validated before API calls
- **Safe subprocess execution** - Not applicable (pure HTTP client)

### Performance

| Metric | Phase 1 | Phase 2 | Phase 3 |
|--------|---------|---------|---------|
| Package size | < 5MB | No change | No change |
| Cold import | < 500ms | +5-10ms | +10-15ms |
| Validation overhead | - | - | < 2ms at track() |

### Observability

- **Logging** - DEBUG (request/response), INFO (operations), WARNING (retries), ERROR (failures)
- **Metrics** - Requests, latency, rate limit remaining, retries, cache hit/miss, circuit breaker state
- **Correlation IDs** - Every request traceable through logs
- **Structured context** - `LogContext` dataclass with `correlation_id`, `operation`, `entity_gid`, `duration_ms`

---

## Appendix A: Files to Modify

| File | Changes |
|------|---------|
| `src/autom8_asana/persistence/exceptions.py` | Rename ValidationError to GidValidationError |
| `src/autom8_asana/persistence/__init__.py` | Add exception exports |
| `src/autom8_asana/models/business/__init__.py` | Remove private functions from `__all__` |
| `src/autom8_asana/models/business/dna.py` | **NEW** - DNA minimal model |
| `src/autom8_asana/models/business/reconciliation.py` | **NEW** - Reconciliation minimal model |
| `src/autom8_asana/models/business/videography.py` | **NEW** - Videography minimal model |
| `src/autom8_asana/protocols/observability.py` | **NEW** - ObservabilityHook protocol |
| `tests/unit/test_tier1_adversarial.py:1335` | Add thread join timeout |
| `tests/unit/dataframes/test_resolver.py:392` | Add thread join timeout |
| `tests/unit/dataframes/test_registry.py:348` | Add thread join timeout |
| `tests/unit/cache/test_concurrency.py:688-736` | Track and join callback threads |
| `tests/unit/test_client.py:186-197` | Convert to async test pattern |

---

## Appendix B: Lessons Learned

1. **Protocol-based architecture was critical** - Allowed autom8 integration without coupling. No other approach would have enabled gradual migration.

2. **Async-first with sync wrappers** - Right balance. Power users get performance, compatibility users get convenience.

3. **Fail-fast validation** - GID validation at `track()` time dramatically improved developer experience.

4. **One ActionOperation per item** - Clear error attribution justified extra object creation.

5. **Documentation is product** - Phase 3 revealed documentation gaps were blocking adoption more than missing features.

6. **Executable validation beats tests** - Phase 4 demo suite found edge cases that unit tests missed.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Tech Writer | Initial consolidated version |

---

**Archived Source Documents:**

| Original | Archive Location |
|----------|------------------|
| PRD-SDK-FAMILY.md | Active reference document |
| PRD-0015-foundation-hardening.md | `docs/.archive/2025-12-prds/` |
| PRD-0004-test-hang-fix.md | `docs/.archive/2025-12-prds/` |
