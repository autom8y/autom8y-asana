# SDK Requirements Evolution

## Overview

The autom8_asana SDK evolved from initial extraction concept through functional parity, production hardening, and operational validation. This document synthesizes the requirements evolution across four major phases, each building on the foundation of its predecessors.

## Evolution Timeline

| Phase | Document | Key Focus | Outcome |
|-------|----------|-----------|---------|
| **Foundation** | PRD-0001 (2025-12-08) | SDK extraction from monolith | Protocol-based architecture, 68 requirements |
| **Expansion** | PRD-0007 (2025-12-10) | Action endpoint functional parity | 53 new requirements, 9 action types |
| **Hardening** | PRD-0009 (2025-12-10) | GA readiness, production resilience | Documentation, validation, circuit breaker |
| **Validation** | PRD-0011 (2025-12-12) | Interactive demonstration suite | Operational proof, reversible validation |

## Phase 1: Foundation (PRD-0001)

**Goal**: Extract pure Asana API functionality from autom8 monolith into standalone, reusable SDK.

### Key Requirements

**Transport Layer (FR-SDK-001-015)**:
- Connection pooling, SSL/TLS configuration, timeout control
- Token-bucket rate limiting (1500 req/min)
- Automatic retry on 429/503/504 with exponential backoff + jitter
- Concurrency limits: 50 concurrent reads, 15 concurrent writes
- Thread safety for shared client instances

**Resource Clients (FR-SDK-016-029)**:
- 13 resource clients: Tasks, Projects, Sections, CustomFields, Webhooks, Users, Teams, Attachments, Tags, Goals, Portfolios, Workspaces, Stories
- Unified `AsanaClient` facade as single entry point
- Async-first API with sync wrappers for compatibility

**Batch API (FR-SDK-030-035)**:
- Batch request composition with automatic chunking
- Partial failure handling (per-item error attribution)
- Automatic pagination for large result sets

**Boundary Protocols (FR-BOUNDARY-001-007)**:
- `AuthProvider`: Token/secret retrieval (enables autom8 to inject `ENV.SecretManager`)
- `CacheProvider`: Get/set/delete interface (enables autom8 to inject S3-backed `TaskCache`)
- `LogProvider`: Python logging-compatible interface
- Default no-op implementations for standalone usage

### Success Criteria

- Zero imports from `sql/`, `contente_api/`, `aws_api/` (coupling eliminated)
- < 5MB wheel size, < 500ms cold import time
- >= 80% test coverage on core modules
- Backward compatible with autom8's existing API surface

### Critical Constraints

- Must use httpx as HTTP client (async-first design)
- Must maintain same public API signatures for migrated functions
- Must support Python 3.10, 3.11
- Must keep asana 5.0.3+ as dependency (leverage official types/errors)

## Phase 2: Expansion (PRD-0007)

**Goal**: Achieve functional parity with Asana's task action API endpoints through SaveSession.

### Gap Analysis

| Operation Category | Asana API | SaveSession Coverage | Priority |
|--------------------|-----------|---------------------|----------|
| Tags | 100% | 100% | ✅ Complete (Phase 1) |
| Projects | 100% | 100% | ✅ Complete (Phase 1) |
| Dependencies | 50% | 50% | ⚠️ **Dependents missing** |
| Sections | 100% | 100% | ✅ Complete (Phase 1) |
| **Followers** | **100%** | **0%** | ❌ **Critical gap** |
| **Likes** | **100%** | **0%** | ❌ **Critical gap** |
| **Comments** | **100%** | **0%** | ❌ **Critical gap** |
| **Positioning** | **100%** | **0%** | ❌ **Critical gap** |

### New Requirements

**Positioning Extensions (FR-POS-001-008)**:
- Extend `add_to_project()` with `insert_before`, `insert_after` parameters
- Extend `move_to_section()` with positioning parameters
- Fail-fast validation: `PositioningConflictError` when both params specified
- Temp GID resolution before API call

**Follower Management (FR-FOL-001-010)**:
- `add_follower(task, user)`, `remove_follower(task, user)`
- `add_followers(task, users)`, `remove_followers(task, users)` (batch convenience)
- One ActionOperation per user for clear error attribution
- Fluent chaining: `session.add_follower(t, u1).add_follower(t, u2)`

**Dependent Relationships (FR-DEP-001-009)**:
- `add_dependent(A, B)`: Make B depend on A (inverse of `add_dependency(B, A)`)
- `remove_dependent(A, B)`
- Symmetric interface reduces cognitive load

**Like Operations (FR-LIK-001-009)**:
- `add_like(task)`, `remove_like(task)` (no user parameter - uses authenticated user)
- Idempotent operations (no error on repeat)

**Comment Operations (FR-CMT-001-009)**:
- `add_comment(task, text, *, html_text=None)` with deferred execution
- Validation: empty text raises error at queue time, not commit time
- Proper sequencing: comment created after task update

### Design Decisions

1. **One ActionOperation per follower**: If adding 3 followers and one fails, the other two succeed. Clear error attribution more important than object count.

2. **Deferred comment execution**: Comments queued and executed on commit, ensuring proper ordering (e.g., task update before comment).

3. **Positioning conflict raises error**: Specifying both `insert_before` and `insert_after` raises `PositioningConflictError` immediately (fail-fast).

### Success Criteria

- 92% coverage of Asana task actions
- 9 new methods + 2 extended methods
- 0 regressions (all 327 existing tests pass)
- 100% mypy strict compliance

## Phase 3: Hardening (PRD-0009)

**Goal**: Achieve GA readiness by addressing documentation, edge cases, developer ergonomics, and production resilience.

### Pre-Launch QA Findings

| Dimension | Score | Status | Gap |
|-----------|-------|--------|-----|
| Correctness | 8/10 | ✅ Strong | Minor edge cases |
| Error Handling | 9/10 | ✅ Strong | - |
| Performance | 8/10 | ✅ Strong | - |
| **Documentation** | **5/10** | ❌ **Critical** | No discovery path |
| **Edge Cases** | **6/10** | ⚠️ **Needs work** | Boundary conditions |
| **Developer Ergonomics** | **7/10** | ⚠️ **Steep curve** | Footgun patterns |
| **Production Readiness** | **7/10** | ⚠️ **Missing resilience** | No circuit breaker |

### Critical Blockers

**Documentation (FR-DOC-001-007)**:
- README.md with quick example, feature matrix
- Limitations.md documenting 6 unsupported fields + 10 footgun patterns
- SaveSession.md explaining Unit of Work pattern
- SDK Adoption migration guide for 3 source patterns

**Validation (FR-VAL-001-004)**:
- GID format validation at `track()` time (fail-fast)
- Warn when entity modified but not tracked (common mistake)
- Empty task.name validation before API call

**Circuit Breaker (FR-RETRY-005-010)**:
- Failure threshold triggers open state
- Half-open probe requests test recovery
- Event hooks for state transitions
- Prevents cascading failures in production

**Boundary Tests (FR-TEST-001-010)**:
- P0: Empty strings, malformed GIDs, type mismatches
- P1: Unicode, emoji, large batches (1000+ entities)

### Footgun Patterns Documented

| ID | Pattern | Severity | Impact |
|----|---------|----------|--------|
| FG-001 | `task.tags.append(tag)` (direct list mutation) | HIGH | Silent no-op |
| FG-002 | Forgetting `track()` | MEDIUM | Changes ignored |
| FG-004 | Using closed session | HIGH | `SessionClosedError` |
| FG-005 | Both `insert_before` and `insert_after` | HIGH | `PositioningConflictError` |
| FG-006 | Dependency cycles | HIGH | `CyclicDependencyError` |
| FG-007 | Partial save scenarios | MEDIUM | `SaveResult.partial` |

### Success Criteria

- Documentation score ≥ 8/10
- Edge case coverage ≥ 8/10
- Developer ergonomics ≥ 8/10
- New developer onboarding < 30 min
- QA verdict: **SHIP** (not CONDITIONAL SHIP)

## Phase 4: Validation (PRD-0011)

**Goal**: Prove SDK functionality through executable, interactive demonstration against real Asana workspace.

### Validation Coverage

| Category | Operations | Validation Approach |
|----------|------------|-------------------|
| **Tags** | add_tag, remove_tag | Name resolution → modify → verify → restore |
| **Dependencies** | add_dependency, remove_dependency, add_dependent, remove_dependent | All 4 operations execute and reverse |
| **Description** | set notes, update notes, clear notes | Scalar field CRUD with restoration |
| **Custom Fields** | String, People, Enum, Number, Multi-Enum | Type-specific operations for 5 field types |
| **Subtasks** | set_parent, reorder_subtask | Parent removal, reorder top/bottom, restore |
| **Memberships** | move_to_section, add/remove_from_project | Section/project changes with restoration |

### Requirements

**Interactivity (FR-INT-001-006)**:
- `session.preview()` before every commit
- Enter/s/q controls (execute, skip, quit)
- Show CRUD and Action operations separately
- Allow operation skip without abort

**State Restoration (FR-REST-001-006)**:
- Capture initial state before any modifications
- Track current state after each operation
- Restore all entities to initial state at completion
- Verify restoration success (post-restore fetch confirms match)
- Handle partial failure during restoration

**Name Resolution (FR-RES-001-006)**:
- Resolve tag/user/section/project names to GIDs
- Resolve enum options via field definitions
- Cache resolved GIDs within session
- No hardcoded GIDs in demo code

### Interactive Flow

```
Category Function
  → Set up operation (e.g., session.add_tag(task, tag_gid))
  → session.preview() → (crud_ops, action_ops)
  → confirm(description, crud_ops, action_ops) → UserAction
    → [EXECUTE]: commit_async() → update state → log success
    → [SKIP]: continue to next operation
    → [QUIT]: restore all → exit
```

### Success Criteria

- All 10 demo categories complete without errors
- User prompted before every mutating operation
- All entities return to initial state after demo
- No hardcoded GIDs (all resolved by name)
- Demo can be safely interrupted and re-run

## Cross-Cutting Concerns

### Security

- **No hardcoded secrets**: All auth via protocols
- **Input validation**: GID format, field values validated before API calls
- **Safe subprocess execution**: Not applicable (pure HTTP client)

### Performance

| Metric | Phase 1 Target | Phase 2 Impact | Phase 3 Impact |
|--------|---------------|---------------|---------------|
| Package size | < 5MB | No change | No change |
| Cold import | < 500ms | +5-10ms (new methods) | +10-15ms (validation) |
| Individual action | - | < 500ms p95 (excluding network) | < 5ms retry overhead |
| Validation overhead | - | - | < 2ms at track() |

### Compatibility

- **Backward compatible**: All existing tests pass in every phase
- **Graceful degradation**: Circuit breaker opt-in, validation warnings (not errors initially)
- **Migration support**: Import aliases, same signatures, sync wrappers

### Observability

- **Logging**: DEBUG (request/response), INFO (operations), WARNING (retries, rate limits), ERROR (failures)
- **Metrics**: Requests, latency, rate limit remaining, retries, cache hit/miss, circuit breaker state
- **Correlation IDs**: Every request traceable through logs

## Current State

**Phase 1**: ✅ Complete (327 tests passing, SDK extracted)

**Phase 2**: ✅ Complete (All 9 action types implemented, positioning support added)

**Phase 3**: ⚠️ In Progress
- Documentation: README, limitations.md, save-session.md complete
- Validation: GID format validation implemented
- Circuit breaker: Implementation planned

**Phase 4**: ⚠️ In Progress
- Demo script suite designed
- Implementation in progress

## Lessons Learned

1. **Protocol-based architecture was critical**: Allowed autom8 integration without coupling. No other approach would have enabled gradual migration.

2. **Async-first with sync wrappers**: Right balance. Power users get performance, compatibility users get convenience.

3. **Fail-fast validation**: GID validation at `track()` time (not commit time) dramatically improved developer experience. Errors caught early with clear context.

4. **One ActionOperation per item**: Clear error attribution justified extra object creation. When batch operation partially fails, knowing exactly which item failed is essential.

5. **Documentation is product**: Phase 3 revealed documentation gaps were blocking adoption more than missing features.

6. **Executable validation beats tests**: Phase 4 demo suite found edge cases that unit tests missed because it operated against real Asana workspace.

## Open Items

| Item | Owner | Due Date | Resolution Path |
|------|-------|----------|----------------|
| Circuit breaker implementation | Architect | TDD-0014 | Session 6 |
| Demo script completion | Engineer | TDD-0029 | Session 7 |
| Public PyPI publication | Product | Post-GA | Separate initiative |

## Archived Documents

This summary synthesizes requirements from:

| Original | Archive Location |
|----------|------------------|
| PRD-0001-sdk-extraction.md | `docs/.archive/2025-12-prds/PRD-0001-sdk-extraction.md` |
| PRD-0007-sdk-functional-parity.md | `docs/.archive/2025-12-prds/PRD-0007-sdk-functional-parity.md` |
| PRD-0009-sdk-ga-readiness.md | `docs/.archive/2025-12-prds/PRD-0009-sdk-ga-readiness.md` |
| PRD-0011-sdk-demonstration-suite.md | `docs/.archive/2025-12-prds/PRD-0011-sdk-demonstration-suite.md` |

---

**Last Updated**: 2025-12-25 (Phase 4 consolidation)
