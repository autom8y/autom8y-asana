# Documentation Index

> Central registry of all project documentation. Update this file when creating new documents.

## PRDs

| ID | Title | Status | Date |
|----|-------|--------|------|
| [PRD-0001](requirements/PRD-0001-sdk-extraction.md) | autom8_asana SDK Extraction | Approved | 2025-12-08 |
| [PRD-0002](requirements/PRD-0002-intelligent-caching.md) | Intelligent Caching Layer | Draft | 2025-12-09 |
| [PRD-0003](requirements/PRD-0003-structured-dataframe-layer.md) | Structured Dataframe Layer | In Review | 2025-12-09 |
| [PRD-0003.1](requirements/PRD-0003.1-dynamic-custom-field-resolution.md) | Dynamic Custom Field Resolution | Draft | 2025-12-09 |
| [PRD-0004](requirements/PRD-0004-test-hang-fix.md) | Test Suite Hang Prevention | Implemented | 2025-12-09 |
| [PRD-0005](requirements/PRD-0005-save-orchestration.md) | Save Orchestration Layer | Draft | 2025-12-10 |
| [PRD-0006](requirements/PRD-0006-action-endpoint-support.md) | Action Endpoint Support for Save Orchestration | Draft | 2025-12-10 |
| [PRD-0007](requirements/PRD-0007-sdk-functional-parity.md) | SDK Functional Parity Initiative | Implemented | 2025-12-10 |
| [PRD-0008](requirements/PRD-0008-parent-subtask-operations.md) | Parent & Subtask Operations | Implemented | 2025-12-10 |
| [PRD-0009](requirements/PRD-0009-sdk-ga-readiness.md) | SDK GA Readiness | Draft | 2025-12-10 |

## TDDs

| ID | Title | PRD | Status | Date |
|----|-------|-----|--------|------|
| [TDD-0001](design/TDD-0001-sdk-architecture.md) | autom8_asana SDK Architecture | PRD-0001 | Draft | 2025-12-08 |
| [TDD-0002](design/TDD-0002-models-pagination.md) | Core Models and Pagination Infrastructure | PRD-0001 | Draft | 2025-12-08 |
| [TDD-0003](design/TDD-0003-tier1-clients.md) | Tier 1 Resource Clients | PRD-0001 | Draft | 2025-12-08 |
| [TDD-0004](design/TDD-0004-tier2-clients.md) | Tier 2 Resource Clients | PRD-0001 | Draft | 2025-12-08 |
| [TDD-0005](design/TDD-0005-batch-api.md) | Batch API for Bulk Operations | PRD-0001 | Draft | 2025-12-08 |
| [TDD-0006](design/TDD-0006-backward-compatibility.md) | Backward Compatibility Layer | PRD-0001 | Draft | 2025-12-08 |
| [TDD-0007](design/TDD-0007-observability.md) | Observability Enhancements | PRD-0001 | Draft | 2025-12-08 |
| [TDD-0008](design/TDD-0008-intelligent-caching.md) | Intelligent Caching Layer | PRD-0002 | Draft | 2025-12-09 |
| [TDD-0009](design/TDD-0009-structured-dataframe-layer.md) | Structured Dataframe Layer | PRD-0003 | Draft | 2025-12-09 |
| [TDD-0009.1](design/TDD-0009.1-dynamic-custom-field-resolution.md) | Dynamic Custom Field Resolution | PRD-0003.1 | Draft | 2025-12-09 |
| [TDD-0010](design/TDD-0010-save-orchestration.md) | Save Orchestration Layer | PRD-0005 | Draft | 2025-12-10 |
| [TDD-0011](design/TDD-0011-action-endpoint-support.md) | Action Endpoint Support | PRD-0006 | Draft | 2025-12-10 |
| [TDD-0012](design/TDD-0012-sdk-functional-parity.md) | SDK Functional Parity Initiative | PRD-0007 | Implemented | 2025-12-10 |
| [TDD-0013](design/TDD-0013-parent-subtask-operations.md) | Parent & Subtask Operations | PRD-0008 | Implemented | 2025-12-10 |
| [TDD-0014](design/TDD-0014-sdk-ga-readiness.md) | SDK GA Readiness | PRD-0009 | Draft | 2025-12-10 |

## ADRs

| ID | Title | Status | Date |
|----|-------|--------|------|
| [ADR-0001](decisions/ADR-0001-protocol-extensibility.md) | Protocol-Based Extensibility for Dependency Injection | Accepted | 2025-12-08 |
| [ADR-0002](decisions/ADR-0002-sync-wrapper-strategy.md) | Fail-Fast Strategy for Sync Wrappers in Async Contexts | Accepted | 2025-12-08 |
| [ADR-0003](decisions/ADR-0003-asana-sdk-integration.md) | Replace Asana SDK HTTP Layer, Retain Types and Error Parsing | Accepted | 2025-12-08 |
| [ADR-0004](decisions/ADR-0004-item-class-boundary.md) | Minimal AsanaResource in SDK, Full Item Stays in Monolith | Accepted | 2025-12-08 |
| [ADR-0005](decisions/ADR-0005-pydantic-model-config.md) | Pydantic v2 with extra="ignore" for Forward Compatibility | Accepted | 2025-12-08 |
| [ADR-0006](decisions/ADR-0006-namegid-standalone-model.md) | NameGid as Standalone Frozen Model | Proposed | 2025-12-08 |
| [ADR-0007](decisions/ADR-0007-consistent-client-pattern.md) | Consistent Client Pattern Across Resource Types | Accepted | 2025-12-08 |
| [ADR-0008](decisions/ADR-0008-webhook-signature-verification.md) | Webhook Signature Verification Strategy | Accepted | 2025-12-08 |
| [ADR-0009](decisions/ADR-0009-attachment-multipart-handling.md) | Attachment Multipart/Form-Data Handling | Accepted | 2025-12-08 |
| [ADR-0010](decisions/ADR-0010-batch-chunking-strategy.md) | Sequential Chunk Execution for Batch Operations | Accepted | 2025-12-08 |
| [ADR-0011](decisions/ADR-0011-deprecation-warning-strategy.md) | Deprecation Warning Strategy for Compatibility Layer | Proposed | 2025-12-08 |
| [ADR-0012](decisions/ADR-0012-public-api-surface.md) | Public API Surface Definition | Proposed | 2025-12-08 |
| [ADR-0013](decisions/ADR-0013-correlation-id-strategy.md) | Correlation ID Strategy for SDK Observability | Proposed | 2025-12-08 |
| [ADR-0014](decisions/ADR-0014-example-scripts-env-config.md) | Environment Variable Configuration for Example Scripts | Accepted | 2025-12-09 |
| [ADR-0015](decisions/ADR-0015-batch-api-request-format.md) | Batch API Request Format Fix | Accepted | 2025-12-09 |
| [ADR-0016](decisions/ADR-0016-cache-protocol-extension.md) | Cache Protocol Extension | Accepted | 2025-12-09 |
| [ADR-0017](decisions/ADR-0017-redis-backend-architecture.md) | Redis Backend Architecture | Accepted | 2025-12-09 |
| [ADR-0018](decisions/ADR-0018-batch-modification-checking.md) | Batch Modification Checking | Accepted | 2025-12-09 |
| [ADR-0019](decisions/ADR-0019-staleness-detection-algorithm.md) | Staleness Detection Algorithm | Accepted | 2025-12-09 |
| [ADR-0020](decisions/ADR-0020-incremental-story-loading.md) | Incremental Story Loading | Accepted | 2025-12-09 |
| [ADR-0021](decisions/ADR-0021-dataframe-caching-strategy.md) | Dataframe Caching Strategy | Accepted | 2025-12-09 |
| [ADR-0022](decisions/ADR-0022-overflow-management.md) | Overflow Management | Accepted | 2025-12-09 |
| [ADR-0023](decisions/ADR-0023-observability-strategy.md) | Observability Strategy | Accepted | 2025-12-09 |
| [ADR-0024](decisions/ADR-0024-thread-safety-guarantees.md) | Thread-Safety Guarantees | Accepted | 2025-12-09 |
| [ADR-0025](decisions/ADR-0025-migration-strategy.md) | Big-Bang Migration Strategy | Accepted | 2025-12-09 |
| [ADR-0026](decisions/ADR-0026-two-tier-cache-architecture.md) | Two-Tier Cache Architecture (Redis + S3) | Accepted | 2025-12-09 |
| [ADR-0027](decisions/ADR-0027-dataframe-layer-migration-strategy.md) | Dataframe Layer Migration Strategy | Proposed | 2025-12-09 |
| [ADR-0028](decisions/ADR-0028-polars-dataframe-library.md) | Polars DataFrame Library | Accepted | 2025-12-09 |
| [ADR-0029](decisions/ADR-0029-task-subclass-strategy.md) | Task Subclass Strategy | Accepted | 2025-12-09 |
| [ADR-0030](decisions/ADR-0030-custom-field-typing.md) | Custom Field Typing | Accepted | 2025-12-09 |
| [ADR-0031](decisions/ADR-0031-lazy-eager-evaluation.md) | Lazy vs Eager Evaluation | Accepted | 2025-12-09 |
| [ADR-0032](decisions/ADR-0032-cache-granularity.md) | Cache Granularity | Accepted | 2025-12-09 |
| [ADR-0033](decisions/ADR-0033-schema-enforcement.md) | Schema Enforcement | Accepted | 2025-12-09 |
| [ADR-0034](decisions/ADR-0034-dynamic-custom-field-resolution.md) | Dynamic Custom Field Resolution Strategy | Accepted | 2025-12-09 |
| [ADR-0035](decisions/ADR-0035-unit-of-work-pattern.md) | Unit of Work Pattern for Save Orchestration | Accepted | 2025-12-10 |
| [ADR-0036](decisions/ADR-0036-change-tracking-strategy.md) | Change Tracking via Snapshot Comparison | Accepted | 2025-12-10 |
| [ADR-0037](decisions/ADR-0037-dependency-graph-algorithm.md) | Kahn's Algorithm for Dependency Ordering | Accepted | 2025-12-10 |
| [ADR-0038](decisions/ADR-0038-save-concurrency-model.md) | Async-First Concurrency for Save Operations | Accepted | 2025-12-10 |
| [ADR-0039](decisions/ADR-0039-batch-execution-strategy.md) | Fixed-Size Sequential Batch Execution | Accepted | 2025-12-10 |
| [ADR-0040](decisions/ADR-0040-partial-failure-handling.md) | Commit and Report on Partial Failure | Accepted | 2025-12-10 |
| [ADR-0041](decisions/ADR-0041-event-hook-system.md) | Synchronous Event Hooks with Async Support | Accepted | 2025-12-10 |
| [ADR-0042](decisions/ADR-0042-action-operation-types.md) | Separate ActionType Enum for Action Endpoint Operations | Proposed | 2025-12-10 |
| [ADR-0043](decisions/ADR-0043-unsupported-operation-detection.md) | Validation-Phase Detection for Unsupported Direct Modifications | Proposed | 2025-12-10 |
| [ADR-0044](decisions/ADR-0044-extra-params-field.md) | extra_params Field Design for ActionOperation | Accepted | 2025-12-10 |
| [ADR-0045](decisions/ADR-0045-like-operations-without-target.md) | Like Operations Without Target GID | Accepted | 2025-12-10 |
| [ADR-0046](decisions/ADR-0046-comment-text-storage.md) | Comment Text Storage Strategy | Accepted | 2025-12-10 |
| [ADR-0047](decisions/ADR-0047-positioning-validation-timing.md) | Positioning Validation Timing | Accepted | 2025-12-10 |
| [ADR-0048](decisions/ADR-0048-circuit-breaker-pattern.md) | Circuit Breaker Pattern for Transport Layer | Accepted | 2025-12-10 |
| [ADR-0049](decisions/ADR-0049-gid-validation-strategy.md) | GID Validation Strategy | Accepted | 2025-12-10 |

## Discovery Documents

| Title | Related PRD | Description | Date |
|-------|-------------|-------------|------|
| [save-orchestration-discovery.md](save-orchestration-discovery.md) | [PRD-0005](requirements/PRD-0005-save-orchestration.md) | Save Orchestration Layer feasibility analysis | 2025-12-10 |

## Guides

| Title | Related | Description |
|-------|---------|-------------|
| [concepts.md](guides/concepts.md) | TDD-0010 | Core SDK concepts and mental model (start here) |
| [quickstart.md](guides/quickstart.md) | TDD-0010 | Get started in 5 minutes |
| [workflows.md](guides/workflows.md) | TDD-0010, TDD-0011 | Common task recipes (cookbook style) |
| [patterns.md](guides/patterns.md) | PRD-0009 | Best practices and recommended patterns |
| [save-session.md](guides/save-session.md) | TDD-0010, TDD-0011 | SaveSession Unit of Work pattern guide |
| [sdk-adoption.md](guides/sdk-adoption.md) | PRD-0009 | Migration guide from old patterns to SDK |
| [autom8-migration.md](guides/autom8-migration.md) | ADR-0025 | Migration guide for legacy autom8 S3 cache to SDK Redis cache |

## Test Plans

| ID | Title | PRD | TDD | Status |
|----|-------|-----|-----|--------|
| [TP-0001](testing/TEST-PLAN-0001.md) | autom8_asana SDK Phase 1 Parity Validation | PRD-0001 | TDD-0001 | Draft |
| [TP-0002](testing/TP-0002-intelligent-caching.md) | Intelligent Caching Layer | PRD-0002 | TDD-0008 | Draft |
| [TP-batch-api-adversarial](testing/TP-batch-api-adversarial.md) | Batch API Adversarial Testing | PRD-0001 | TDD-0005 | Completed |
