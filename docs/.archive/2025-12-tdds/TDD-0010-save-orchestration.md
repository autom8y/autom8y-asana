# TDD-0010: Save Orchestration Layer

## Metadata
- **TDD ID**: TDD-0010
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-10
- **Last Updated**: 2025-12-24
- **PRD Reference**: [PRD-0005](../requirements/PRD-0005-save-orchestration.md)
- **Related TDDs**:
  - [TDD-0005](TDD-0005-batch-api.md) - Batch API for Bulk Operations (BatchClient foundation)
  - [TDD-0001](TDD-0001-sdk-architecture.md) - SDK Architecture (foundation)
- **Related ADRs**:
  - [ADR-0035](../decisions/ADR-0035-unit-of-work-pattern.md) - Unit of Work Pattern for Save Orchestration
  - [ADR-0036](../decisions/ADR-0036-change-tracking-strategy.md) - Change Tracking via Snapshot Comparison
  - [ADR-0037](../decisions/ADR-0037-dependency-graph-algorithm.md) - Kahn's Algorithm for Dependency Ordering
  - [ADR-0038](../decisions/ADR-0038-save-concurrency-model.md) - Async-First Concurrency for Save Operations
  - [ADR-0039](../decisions/ADR-0039-batch-execution-strategy.md) - Fixed-Size Sequential Batch Execution
  - [ADR-0040](../decisions/ADR-0040-partial-failure-handling.md) - Commit and Report on Partial Failure
  - [ADR-0041](../decisions/ADR-0041-event-hook-system.md) - Synchronous Event Hooks with Async Support
  - [ADR-0002](../decisions/ADR-0002-sync-wrapper-strategy.md) - Sync/Async Wrapper Strategy
  - [ADR-0010](../decisions/ADR-0010-batch-chunking-strategy.md) - Sequential Chunk Execution

## Overview

This design introduces a Save Orchestration Layer for the autom8_asana SDK that implements the Unit of Work pattern for batched Asana API operations. The layer enables Django-ORM-style deferred saves where multiple model changes are collected and executed in optimized batches rather than immediately persisting each change. The architecture provides explicit entity registration via `SaveSession.track()`, snapshot-based dirty detection, dependency graph construction using Kahn's algorithm for topological sorting, automatic placeholder GID resolution, and partial failure handling with commit-and-report semantics. The design reuses the existing `BatchClient` infrastructure and follows the SDK's async-first pattern per ADR-0002.

## Requirements Summary

This design addresses [PRD-0005](../requirements/PRD-0005-save-orchestration.md) v1.0, which defines:

- **46 functional requirements** across Unit of Work (FR-UOW-*), Change Tracking (FR-CHANGE-*), Dependency Graph (FR-DEPEND-*), Batch Execution (FR-BATCH-*), Error Handling (FR-ERROR-*), Custom Fields (FR-FIELD-*), Event Hooks (FR-EVENT-*), and Dry Run (FR-DRY-*) domains
- **21 non-functional requirements** covering performance (NFR-PERF-*), compatibility (NFR-COMPAT-*), observability (NFR-OBSERVE-*), and reliability (NFR-REL-*)
- **Key constraints**: Opt-in tracking, snapshot comparison, commit-and-report on partial failure, Kahn's algorithm, fixed batch size of 10, async-first with sync wrappers

Key requirements driving this design:

| Requirement | Summary | Design Impact |
|-------------|---------|---------------|
| FR-UOW-001 | SaveSession as async context manager | SaveSession class with `__aenter__`, `__aexit__` |
| FR-UOW-002 | Explicit entity registration via `track()` | ChangeTracker with opt-in model |
| FR-CHANGE-001 | Dirty detection via `model_dump()` snapshot | ChangeTracker stores snapshots |
| FR-DEPEND-002 | Topological sort using Kahn's algorithm | DependencyGraph component |
| FR-BATCH-002 | Delegate to existing BatchClient | SavePipeline uses BatchClient |
| FR-ERROR-001 | Commit successful, report failures | Partial failure handling in SaveResult |

## System Context

The Save Orchestration Layer sits between SDK consumers and the existing BatchClient infrastructure, orchestrating multi-entity saves through dependency-aware batching.

```
+---------------------------------------------------------------------------+
|                              SYSTEM CONTEXT                                |
+---------------------------------------------------------------------------+

                            +------------------------+
                            |    SDK Consumers       |
                            |  (autom8, services)    |
                            +-----------+------------+
                                        |
                           async with SaveSession(client):
                               session.track(entity)
                               await session.commit()
                                        |
                                        v
+---------------------------------------------------------------------------+
|                         autom8_asana SDK                                   |
|                                                                            |
|  +----------------------------------------------------------------------+ |
|  |                    Save Orchestration Layer                          | |
|  |                                                                      | |
|  |  +----------------+  +----------------+  +----------------+          | |
|  |  |  SaveSession   |  | ChangeTracker  |  |DependencyGraph |          | |
|  |  | (entry point)  |  | (snapshots)    |  |  (Kahn's alg)  |          | |
|  |  +-------+--------+  +-------+--------+  +-------+--------+          | |
|  |          |                   |                   |                   | |
|  |          +-------------------+-------------------+                   | |
|  |                              |                                       | |
|  |                              v                                       | |
|  |              +---------------+---------------+                       | |
|  |              |         SavePipeline          |                       | |
|  |              | (validate->prepare->execute)  |                       | |
|  |              +---------------+---------------+                       | |
|  |                              |                                       | |
|  |                              v                                       | |
|  |              +---------------+---------------+                       | |
|  |              |        BatchExecutor          |                       | |
|  |              |  (chunk, delegate, correlate) |                       | |
|  |              +---------------+---------------+                       | |
|  |                              |                                       | |
|  +------------------------------+---------------------------------------+ |
|                                 |                                         |
|  +------------------------------+---------------------------------------+ |
|  |                              |                                       | |
|  |              +---------------+---------------+                       | |
|  |              |         BatchClient           |                       | |
|  |              |  (TDD-0005 implementation)    |                       | |
|  |              +---------------+---------------+                       | |
|  |                              |                                       | |
|  |                    Existing SDK Infrastructure                       | |
|  +----------------------------------------------------------------------+ |
|                                                                            |
+---------------------------------------------------------------------------+
                                        |
                                        v
                            +------------------------+
                            |    Infrastructure      |
                            |  (Asana Batch API)     |
                            +------------------------+
```

## Document Structure

This TDD has been split into focused sub-documents for maintainability:

### Main Documents

1. **This Document (TDD-0010-save-orchestration.md)** - Overview and navigation
2. **[TDD-0010-architecture-models.md](TDD-0010-architecture-models.md)** - Architecture, data models, exceptions
3. **[TDD-0010-component-specs.md](TDD-0010-component-specs.md)** - Detailed component interfaces and implementations
4. **[TDD-0010-implementation.md](TDD-0010-implementation.md)** - Data flows, testing, observability, implementation plan

### Content Breakdown

#### TDD-0010-architecture-models.md
- Package structure
- Component architecture diagram
- Entity state machine
- Core data classes (EntityState, OperationType, PlannedOperation, SaveError, SaveResult)
- Exception hierarchy
- Technical decisions table

#### TDD-0010-component-specs.md
- SaveSession interface specification
- ChangeTracker implementation
- DependencyGraph with Kahn's algorithm
- SavePipeline orchestration
- BatchExecutor
- EventSystem

#### TDD-0010-implementation.md
- Commit flow sequence diagram
- Placeholder GID resolution flow
- Implementation plan (7 phases)
- Testing strategy
- Observability (metrics, logging, alerting)
- Risks & mitigations
- Requirement traceability matrix

## Quick Reference

### Integration Points

| Integration Point | Interface | Direction | Notes |
|-------------------|-----------|-----------|-------|
| `AsanaResource` models | Pydantic model | Read/Write | Source entities; GID updated after create |
| `BatchClient` | SDK client | Write | Delegates batch execution |
| `BatchRequest` / `BatchResult` | Data classes | Read/Write | Request building and result parsing |
| `AsanaError` hierarchy | Exceptions | Read | Error classification and chaining |
| `sync_wrapper` | Decorator | Wrap | Sync API surface per ADR-0002 |

### Key Design Choices

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Unit of Work pattern | SaveSession context manager | Familiar pattern, explicit scope, resource cleanup | [ADR-0035](../decisions/ADR-0035-unit-of-work-pattern.md) |
| Change tracking | Snapshot comparison via model_dump() | Simple, no model changes, works with existing Pydantic | [ADR-0036](../decisions/ADR-0036-change-tracking-strategy.md) |
| Dependency ordering | Kahn's algorithm | O(V+E), cycle detection, level grouping | [ADR-0037](../decisions/ADR-0037-dependency-graph-algorithm.md) |
| Concurrency model | Async-first with sync wrappers | Consistent with SDK pattern per ADR-0002 | [ADR-0038](../decisions/ADR-0038-save-concurrency-model.md) |
| Batch execution | Fixed 10, sequential chunks | Asana limit, per ADR-0010 | [ADR-0039](../decisions/ADR-0039-batch-execution-strategy.md) |
| Partial failure | Commit + Report | No rollback in Asana, preserve successful work | [ADR-0040](../decisions/ADR-0040-partial-failure-handling.md) |
| Event hooks | Sync-first with async support | Simple invocation, flexibility | [ADR-0041](../decisions/ADR-0041-event-hook-system.md) |

## Complexity Assessment

**Level**: SERVICE

**Justification**:

This feature adds significant complexity to the SDK but remains within the SERVICE level:

1. **Multiple interacting components**: SaveSession, ChangeTracker, DependencyGraph, SavePipeline, BatchExecutor, EventSystem
2. **State management complexity**: Entity lifecycle states, snapshot tracking, GID resolution
3. **Algorithm complexity**: Kahn's algorithm for topological sort, cycle detection
4. **Error handling complexity**: Partial failures, cascading dependency failures, error attribution
5. **Integration requirements**: BatchClient, Pydantic models, sync/async wrappers

**Not PLATFORM because**:
- Single SDK boundary (no multi-service orchestration)
- No infrastructure provisioning logic
- Batch execution delegated to existing BatchClient
- No deployment coordination required

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-10 | Architect | Initial design with 6 components, 7 ADRs |
| 1.1 | 2025-12-24 | Tech Writer | Split into focused sub-documents for maintainability |
