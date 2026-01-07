---
sprint_id: sprint-dataframe-cache-20260106
session_id: session-20260105-145920-f6c9a679
sprint_name: DataFrame Caching Architecture
sprint_goal: Implement unified caching layer to fix Contact/Offer timeout issues
initiative: DataFrame Caching Architecture
complexity: MODULE
active_team: 10x-dev-pack
workflow: sequential
status: completed
created_at: 2026-01-06T00:00:00Z
started_at: 2026-01-06T00:00:00Z
completed_at: 2026-01-06T22:30:00Z
parent_session: session-20260105-145920-f6c9a679
schema_version: "1.0"
tasks:
  - id: task-001
    name: TDD-dataframe-cache
    description: Create Technical Design Document for unified DataFrame caching architecture
    status: completed
    complexity: MODULE
    agent: architect
    completed_at: 2026-01-06T00:00:00Z
    artifacts:
      - type: tdd
        path: docs/design/TDD-dataframe-cache.md
        status: completed
  - id: task-002
    name: cache-decorator-layer
    description: Implement class decorator cache layer with protocol abstraction
    status: completed
    complexity: MODULE
    agent: principal-engineer
    depends_on:
      - task-001
    completed_at: 2026-01-06T13:23:13Z
    artifacts:
      - type: code
        path: src/autom8_asana/cache/dataframe_cache.py
        status: completed
      - type: code
        path: src/autom8_asana/cache/dataframe/
        status: completed
        description: "Full implementation: coalescer.py, circuit_breaker.py, decorator.py, tiers/memory.py, tiers/s3.py"
      - type: test
        path: tests/unit/cache/dataframe/
        status: completed
        description: "8 test files, 86 tests passing"
  - id: task-003
    name: s3-memory-tiering
    description: Wire S3 read-through with memory tier integration
    status: completed
    complexity: MODULE
    agent: principal-engineer
    depends_on:
      - task-002
    completed_at: 2026-01-06T21:00:00Z
    artifacts:
      - type: code
        path: src/autom8_asana/cache/dataframe/factory.py
        status: completed
        description: "Cache singleton factory with S3 + Memory tiering"
      - type: code
        path: src/autom8_asana/services/resolver.py
        status: completed
        description: "Applied @dataframe_cache decorator to OfferResolutionStrategy and ContactResolutionStrategy"
      - type: code
        path: src/autom8_asana/api/main.py
        status: completed
        description: "Cache initialization in API main"
  - id: task-004
    name: request-coalescing
    description: Add request coalescing for thundering herd prevention
    status: completed
    complexity: SCRIPT
    agent: principal-engineer
    depends_on:
      - task-002
    completed_at: 2026-01-06T21:00:00Z
    artifacts:
      - type: code
        path: src/autom8_asana/cache/dataframe/coalescer.py
        status: completed
        description: "DataFrameCacheCoalescer with lock-based request deduplication"
      - type: code
        path: src/autom8_asana/cache/dataframe/decorator.py
        status: completed
        description: "@dataframe_cache decorator with built-in coalescing support"
      - type: test
        path: tests/unit/cache/dataframe/test_strategies_cached.py
        status: completed
        description: "18 new tests for cached strategies, all passing"
  - id: task-005
    name: qa-entity-validation
    description: QA validation of all 4 entity types (Unit, Business, Offer, Contact)
    status: completed
    complexity: SCRIPT
    agent: qa-adversary
    depends_on:
      - task-003
      - task-004
    completed_at: 2026-01-06T22:30:00Z
    artifacts:
      - type: test-plan
        path: docs/test-plans/TEST-SUMMARY-dataframe-cache-validation.md
        status: completed
completed_tasks: 5
total_tasks: 5
---

# Sprint: DataFrame Caching Architecture

## Sprint Overview

This sprint implements a unified DataFrame caching layer to resolve timeout issues affecting Contact and Offer entity resolution strategies. Unit and Business strategies currently use `_gid_index_cache` for O(1) lookups, but Contact and Offer strategies have NO caching and rebuild the entire DataFrame (10-50K tasks for Contacts) on EVERY request, causing timeouts.

## Problem Statement

**Current State**:
- Unit/Business strategies: Use `_gid_index_cache` for O(1) lookups
- Contact/Offer strategies: NO caching, rebuild entire DataFrame on every request
- Impact: 10-50K tasks for Contacts causes timeouts

**Root Cause**:
- No unified caching layer for DataFrame builders
- Each strategy implements caching independently (or not at all)
- No S3 integration for DataFrame persistence
- No request coalescing for concurrent access

## Sprint Goal

Implement unified caching layer to fix Contact/Offer timeout issues by:
1. Creating class decorator cache layer with protocol abstraction
2. Wiring S3 read-through with memory tier integration
3. Adding request coalescing for thundering herd prevention
4. Validating all 4 entity types (Unit, Business, Offer, Contact)

## Tasks Breakdown

### Phase 1: Design (Task 001)
**task-001**: TDD-dataframe-cache
- Create Technical Design Document for unified DataFrame caching architecture
- Define protocol abstraction for cache layer
- Design S3 read-through and memory tiering strategy
- Document request coalescing approach
- **Complexity**: MODULE
- **Agent**: architect
- **Artifacts**: docs/design/TDD-dataframe-cache.md

### Phase 2: Implementation (Tasks 002-004)
**task-002**: cache-decorator-layer
- Implement class decorator for DataFrame caching
- Create protocol abstraction for cache layer
- Add cache invalidation and TTL support
- **Complexity**: MODULE
- **Agent**: principal-engineer
- **Depends on**: task-001
- **Artifacts**: src/autom8_asana/cache/dataframe_cache.py

**task-003**: s3-memory-tiering
- Wire S3 read-through with memory tier integration
- Implement fallback logic (S3 -> rebuild)
- Add watermark coordination
- **Complexity**: MODULE
- **Agent**: principal-engineer
- **Depends on**: task-002
- **Artifacts**: Integration in cache layer

**task-004**: request-coalescing
- Add request coalescing for thundering herd prevention
- Implement lock-based coalescing for concurrent requests
- Add timeout and error handling
- **Complexity**: SCRIPT
- **Agent**: principal-engineer
- **Depends on**: task-002
- **Artifacts**: Coalescing logic in cache layer

### Phase 3: Quality Assurance (Task 005)
**task-005**: qa-entity-validation
- QA validation of all 4 entity types (Unit, Business, Offer, Contact)
- Test cache hit/miss scenarios
- Validate S3 integration
- Test request coalescing under load
- Create test plan and validation report
- **Complexity**: SCRIPT
- **Agent**: qa-adversary
- **Depends on**: task-003, task-004
- **Artifacts**: Test plan and validation report

## Success Criteria

1. TDD document approved with unified caching architecture design
2. Class decorator cache layer implemented with protocol abstraction
3. S3 read-through with memory tier integration working
4. Request coalescing prevents thundering herd
5. All 4 entity types (Unit, Business, Offer, Contact) pass validation
6. Contact/Offer timeout issues resolved
7. Cache hit rate > 90% for repeated requests
8. Integration tests pass for all entity types

## Dependencies

- Existing codebase: src/autom8_asana/dataframes/builders/
- S3 DataFrame persistence: tmp/spike-s3-persistence/SPIKE-s3-dataframe-persistence.md
- UnifiedTaskStore: src/autom8_asana/cache/unified.py
- Entity resolution strategies: src/autom8_asana/dataframes/resolver/

## Technical Context

**Current Implementation**:
- Unit/Business: `_gid_index_cache` provides O(1) lookups
- Contact/Offer: No caching, full DataFrame rebuild every request
- Scale: 10-50K tasks for Contacts

**Proposed Architecture**:
1. **Class Decorator**: `@dataframe_cache` decorator for builders
2. **Protocol Abstraction**: `DataFrameCacheProtocol` for pluggable backends
3. **Memory Tier**: In-memory LRU cache with TTL
4. **S3 Tier**: Read-through S3 persistence for cold starts
5. **Request Coalescing**: Lock-based coalescing for concurrent requests

**Key Design Decisions** (to be validated in TDD):
- Cache key strategy (project_gid, entity_type, watermark)
- TTL configuration (default: 5 minutes)
- S3 bucket structure
- Coalescing timeout (default: 10 seconds)
- Cache invalidation triggers

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Cache invalidation complexity | Use watermark-based invalidation |
| S3 latency impact | Memory tier first, S3 as fallback |
| Thundering herd on cold start | Request coalescing with lock |
| Cache key collisions | Include entity_type + watermark in key |
| Memory pressure | LRU eviction + configurable max size |

## Out of Scope

- Changes to core DataFrame builder logic (preserve existing)
- New entity types beyond Unit, Business, Offer, Contact
- Cross-project cache sharing (session-scoped only)
- Cache warming strategies (will rebuild on miss)
- Distributed cache (single-instance only)

## Notes

- Sprint follows sequential workflow (design -> implement -> test)
- Estimated duration: 1-2 weeks
- Focus on Contact/Offer timeout resolution
- Generalize solution for all entity types
- Leverage existing S3 persistence spike findings

## References

- S3 Persistence Spike: tmp/spike-s3-persistence/SPIKE-s3-dataframe-persistence.md
- Entity Resolution: src/autom8_asana/dataframes/resolver/cascading.py
- UnifiedTaskStore: src/autom8_asana/cache/unified.py
- DataFrame Builders: src/autom8_asana/dataframes/builders/
