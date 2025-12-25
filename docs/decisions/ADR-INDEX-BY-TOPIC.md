# ADR Index by Topic

**Purpose**: Navigate 145+ ADRs by topical grouping rather than chronological order.

Use this index to find decisions by concern area. For chronological listing, see the main [decisions README](README.md).

## Table of Contents
- [Architecture](#architecture)
- [Patterns](#patterns)
- [Data Model](#data-model)
- [Cache](#cache)
- [Performance](#performance)
- [Detection & Auto-Resolution](#detection--auto-resolution)
- [SaveSession & Persistence](#savesession--persistence)
- [Custom Fields](#custom-fields)
- [Integration](#integration)
- [Error Handling & Resilience](#error-handling--resilience)
- [Observability](#observability)
- [API Design](#api-design)
- [Process & Workflow](#process--workflow)
- [Testing & Demo](#testing--demo)
- [Refactoring & Migration](#refactoring--migration)
- [Rejection Decisions](#rejection-decisions)

---

## Architecture

Core structural decisions about system design and module organization.

- [ADR-0001](ADR-0001-protocol-extensibility.md) - Protocol-Based Extensibility for Dependency Injection
- [ADR-0003](ADR-0003-asana-sdk-integration.md) - Replace Asana SDK HTTP Layer, Retain Types and Error Parsing
- [ADR-0004](ADR-0004-item-class-boundary.md) - Minimal AsanaResource in SDK, Full Item Stays in Monolith
- [ADR-0012](ADR-0012-public-api-surface.md) - Public API Surface Definition
- [ADR-0017](ADR-0017-redis-backend-architecture.md) - Redis Backend Architecture
- [ADR-0024](ADR-0024-thread-safety-guarantees.md) - Thread-Safety Guarantees
- [ADR-0026](ADR-0026-two-tier-cache-architecture.md) - Two-Tier Cache Architecture (Redis + S3)
- [ADR-0080](ADR-0080-entity-registry-scope.md) - Entity Registry Scope
- [ADR-0101](ADR-0101-process-pipeline-correction.md) - Process Pipeline Architecture Correction
- [ADR-0102](ADR-0102-post-commit-hook-architecture.md) - Post-Commit Hook Architecture
- [ADR-0105](ADR-0105-field-seeding-architecture.md) - Field Seeding Architecture
- [ADR-0108](ADR-0108-workspace-project-registry.md) - WorkspaceProjectRegistry Architecture
- [ADR-0136](ADR-0136-process-field-architecture.md) - Process Field Accessor Architecture
- [ADR-0142](ADR-0142-detection-package-structure.md) - Detection Package Structure

## Patterns

Reusable code patterns, decorators, protocols, and design patterns.

- [ADR-0007](ADR-0007-consistent-client-pattern.md) - Consistent Client Pattern Across Resource Types
- [ADR-0016](ADR-0016-cache-protocol-extension.md) - Cache Protocol Extension
- [ADR-0035](ADR-0035-unit-of-work-pattern.md) - Unit of Work Pattern for Save Orchestration
- [ADR-0041](ADR-0041-event-hook-system.md) - Synchronous Event Hooks with Async Support
- [ADR-0048](ADR-0048-circuit-breaker-pattern.md) - Circuit Breaker Pattern for Transport Layer
- [ADR-0050](ADR-0050-holder-lazy-loading-strategy.md) - Holder Lazy Loading Strategy
- [ADR-0075](ADR-0075-navigation-descriptor-pattern.md) - Navigation Descriptor Pattern
- [ADR-0077](ADR-0077-pydantic-descriptor-compatibility.md) - Pydantic v2 Descriptor Compatibility
- [ADR-0081](ADR-0081-custom-field-descriptor-pattern.md) - Custom Field Descriptor Pattern
- [ADR-0085](ADR-0085-observability-hook-protocol.md) - ObservabilityHook Protocol Design
- [ADR-0087](ADR-0087-stub-model-pattern.md) - Minimal Stub Model Pattern
- [ADR-0091](ADR-0091-error-classification-mixin.md) - RetryableErrorMixin for Error Classification
- [ADR-0093](ADR-0093-project-type-registry.md) - Project-to-EntityType Registry Pattern
- [ADR-0097](ADR-0097-processsection-state-machine.md) - ProcessSection State Machine Pattern
- [ADR-0099](ADR-0099-businessseeder-factory.md) - BusinessSeeder Factory Pattern
- [ADR-0100](ADR-0100-state-transition-composition.md) - State Transition Composition with SaveSession
- [ADR-0103](ADR-0103-automation-rule-protocol.md) - Automation Rule Protocol
- [ADR-0106](ADR-0106-template-discovery-pattern.md) - Template Discovery Pattern
- [ADR-0113](ADR-0113-rep-field-cascade-pattern.md) - Rep Field Cascade Pattern
- [ADR-0116](ADR-0116-batch-cache-population-pattern.md) - Batch Cache Population Pattern
- [ADR-0117](ADR-0117-accessor-descriptor-unification.md) - CustomFieldAccessor/Descriptor Unification Strategy
- [ADR-0119](ADR-0119-client-cache-integration-pattern.md) - Client Cache Integration Pattern
- [ADR-0122](ADR-0122-action-method-factory-pattern.md) - Action Method Factory Pattern
- [ADR-0124](ADR-0124-client-cache-pattern.md) - Client Cache Integration Pattern
- [ADR-0134](ADR-0134-staleness-check-integration-pattern.md) - Staleness Check Integration Pattern
- [ADR-0138](ADR-0138-tier2-pattern-enhancement.md) - Detection Tier 2 Pattern Matching Enhancement
- [ADR-0141](ADR-0141-field-mixin-strategy.md) - Field Mixin Strategy for Sprint 1 Pattern Completion

## Data Model

Entity models, relationships, schemas, and typing.

- [ADR-0005](ADR-0005-pydantic-model-config.md) - Pydantic v2 with `extra="ignore"` for Forward Compatibility
- [ADR-0006](ADR-0006-namegid-standalone-model.md) - NameGid as Standalone Frozen Model
- [ADR-0028](ADR-0028-polars-dataframe-library.md) - Polars DataFrame Library
- [ADR-0029](ADR-0029-task-subclass-strategy.md) - Task Subclass Strategy
- [ADR-0030](ADR-0030-custom-field-typing.md) - Custom Field Typing
- [ADR-0033](ADR-0033-schema-enforcement.md) - Schema Enforcement
- [ADR-0049](ADR-0049-gid-validation-strategy.md) - GID Validation Strategy
- [ADR-0051](ADR-0051-custom-field-type-safety.md) - Custom Field Type Safety
- [ADR-0078](ADR-0078-gid-based-entity-identity.md) - GID-Based Entity Identity Strategy
- [ADR-0082](ADR-0082-fields-auto-generation-strategy.md) - Fields Class Auto-Generation Strategy
- [ADR-0083](ADR-0083-datefield-arrow-integration.md) - DateField Arrow Integration
- [ADR-0098](ADR-0098-dual-membership-model.md) - Dual Membership Model
- [ADR-0114](ADR-0114-hours-backward-compat.md) - Hours Model Backward Compatibility Strategy
- [ADR-SDK-005](ADR-SDK-005-pydantic-settings-standards.md) - Pydantic Settings Standards

## Cache

Caching strategies, staleness detection, TTL, invalidation, and cache architecture.

- [ADR-0016](ADR-0016-cache-protocol-extension.md) - Cache Protocol Extension
- [ADR-0018](ADR-0018-batch-modification-checking.md) - Batch Modification Checking
- [ADR-0019](ADR-0019-staleness-detection-algorithm.md) - Staleness Detection Algorithm
- [ADR-0021](ADR-0021-dataframe-caching-strategy.md) - Dataframe Caching Strategy
- [ADR-0026](ADR-0026-two-tier-cache-architecture.md) - Two-Tier Cache Architecture (Redis + S3)
- [ADR-0032](ADR-0032-cache-granularity.md) - Cache Granularity
- [ADR-0052](ADR-0052-bidirectional-reference-caching.md) - Bidirectional Reference Caching
- [ADR-0060](ADR-0060-name-resolution-caching-strategy.md) - Name Resolution Caching Strategy
- [ADR-0072](ADR-0072-resolution-caching-decision.md) - Resolution Caching Decision
- [ADR-0076](ADR-0076-auto-invalidation-strategy.md) - Auto-Invalidation Strategy
- [ADR-0116](ADR-0116-batch-cache-population-pattern.md) - Batch Cache Population Pattern
- [ADR-0119](ADR-0119-client-cache-integration-pattern.md) - Client Cache Integration Pattern
- [ADR-0120](ADR-0120-batch-cache-population-on-bulk-fetch.md) - Batch Cache Population on Bulk Fetch
- [ADR-0123](ADR-0123-cache-provider-selection.md) - Default Cache Provider Selection Strategy
- [ADR-0124](ADR-0124-client-cache-pattern.md) - Client Cache Integration Pattern
- [ADR-0125](ADR-0125-savesession-invalidation.md) - SaveSession Cache Invalidation Hook
- [ADR-0126](ADR-0126-entity-ttl-resolution.md) - Entity-Type TTL Resolution Strategy
- [ADR-0127](ADR-0127-graceful-degradation.md) - Cache Graceful Degradation Strategy
- [ADR-0129](ADR-0129-stories-client-cache-wiring.md) - Stories Client Cache Wiring Strategy
- [ADR-0130](ADR-0130-cache-population-location.md) - Cache Population Location Strategy
- [ADR-0131](ADR-0131-gid-enumeration-cache-strategy.md) - GID Enumeration Cache Strategy
- [ADR-0133](ADR-0133-progressive-ttl-extension-algorithm.md) - Progressive TTL Extension Algorithm
- [ADR-0137](ADR-0137-post-commit-invalidation-hook.md) - Post-Commit Invalidation Hook for DataFrame Cache
- [ADR-0140](ADR-0140-dataframe-task-cache-integration.md) - DataFrame Task Cache Integration Strategy
- [ADR-0143](ADR-0143-detection-result-caching.md) - Detection Result Caching Strategy

## Performance

Optimization strategies, batching, async operations, and performance improvements.

- [ADR-0002](ADR-0002-sync-wrapper-strategy.md) - Fail-Fast Strategy for Sync Wrappers in Async Contexts
- [ADR-0010](ADR-0010-batch-chunking-strategy.md) - Sequential Chunk Execution for Batch Operations
- [ADR-0015](ADR-0015-batch-api-request-format.md) - Batch API Request Format Fix
- [ADR-0020](ADR-0020-incremental-story-loading.md) - Incremental Story Loading
- [ADR-0031](ADR-0031-lazy-eager-evaluation.md) - Lazy vs Eager Evaluation
- [ADR-0038](ADR-0038-save-concurrency-model.md) - Async-First Concurrency for Save Operations
- [ADR-0039](ADR-0039-batch-execution-strategy.md) - Fixed-Size Sequential Batch Execution
- [ADR-0057](ADR-0057-subtasks-async-method.md) - Add subtasks_async Method to TasksClient
- [ADR-0073](ADR-0073-batch-resolution-api-design.md) - Batch Resolution API Design
- [ADR-0115](ADR-0115-parallel-section-fetch-strategy.md) - Parallel Section Fetch Strategy
- [ADR-0132](ADR-0132-batch-request-coalescing-strategy.md) - Batch Request Coalescing Strategy

## Detection & Auto-Resolution

Auto-detection, inference, type detection, and name resolution.

- [ADR-0034](ADR-0034-dynamic-custom-field-resolution.md) - Dynamic Custom Field Resolution Strategy
- [ADR-0043](ADR-0043-unsupported-operation-detection.md) - Validation-Phase Detection for Unsupported Direct Modifications
- [ADR-0068](ADR-0068-type-detection-strategy.md) - Type Detection Strategy for Upward Traversal
- [ADR-0071](ADR-0071-resolution-ambiguity-handling.md) - Resolution Ambiguity Handling
- [ADR-0089](ADR-0089-demo-name-resolution.md) - Name Resolution Approach for Demo Scripts
- [ADR-0094](ADR-0094-detection-fallback-chain.md) - Detection Fallback Chain Design
- [ADR-0095](ADR-0095-self-healing-integration.md) - Self-Healing Integration with SaveSession
- [ADR-0096](ADR-0096-processtype-expansion.md) - ProcessType Expansion and Detection
- [ADR-0106](ADR-0106-template-discovery-pattern.md) - Template Discovery Pattern
- [ADR-0109](ADR-0109-lazy-discovery-timing.md) - Lazy Discovery Timing for WorkspaceProjectRegistry
- [ADR-0112](ADR-0112-custom-field-gid-resolution.md) - Custom Field GID Resolution Pattern
- [ADR-0135](ADR-0135-processholder-detection.md) - ProcessHolder Detection Strategy
- [ADR-0138](ADR-0138-tier2-pattern-enhancement.md) - Detection Tier 2 Pattern Matching Enhancement
- [ADR-0139](ADR-0139-self-healing-design.md) - Self-Healing Opt-In Design
- [ADR-0142](ADR-0142-detection-package-structure.md) - Detection Package Structure
- [ADR-0143](ADR-0143-detection-result-caching.md) - Detection Result Caching Strategy
- [ADR-0144](ADR-0144-healingresult-consolidation.md) - HealingResult Type Consolidation

## SaveSession & Persistence

Save orchestration, change tracking, action management, and persistence lifecycle.

- [ADR-0035](ADR-0035-unit-of-work-pattern.md) - Unit of Work Pattern for Save Orchestration
- [ADR-0036](ADR-0036-change-tracking-strategy.md) - Change Tracking via Snapshot Comparison
- [ADR-0037](ADR-0037-dependency-graph-algorithm.md) - Kahn's Algorithm for Dependency Ordering
- [ADR-0038](ADR-0038-save-concurrency-model.md) - Async-First Concurrency for Save Operations
- [ADR-0040](ADR-0040-partial-failure-handling.md) - Commit and Report on Partial Failure
- [ADR-0042](ADR-0042-action-operation-types.md) - Separate ActionType Enum for Action Endpoint Operations
- [ADR-0044](ADR-0044-extra-params-field.md) - extra_params Field Design for ActionOperation
- [ADR-0045](ADR-0045-like-operations-without-target.md) - Like Operations Without Target GID
- [ADR-0053](ADR-0053-composite-savesession-support.md) - Composite SaveSession Support
- [ADR-0055](ADR-0055-action-result-integration.md) - Action Result Integration into SaveResult
- [ADR-0059](ADR-0059-direct-methods-vs-session-actions.md) - Direct Methods vs. SaveSession Actions
- [ADR-0061](ADR-0061-implicit-savesession-lifecycle.md) - Implicit SaveSession Lifecycle
- [ADR-0064](ADR-0064-dirty-detection-strategy.md) - Dirty Detection Strategy
- [ADR-0065](ADR-0065-savesession-error-exception.md) - SaveSessionError Exception for P1 Methods
- [ADR-0066](ADR-0066-selective-action-clearing.md) - Selective Action Clearing Strategy
- [ADR-0100](ADR-0100-state-transition-composition.md) - State Transition Composition with SaveSession
- [ADR-0104](ADR-0104-loop-prevention-strategy.md) - Loop Prevention Strategy
- [ADR-0107](ADR-0107-namegid-action-targets.md) - NameGid for ActionOperation Targets
- [ADR-0110](ADR-0110-task-duplication-strategy.md) - Task Duplication vs Creation Strategy
- [ADR-0111](ADR-0111-subtask-wait-strategy.md) - Subtask Wait Strategy
- [ADR-0121](ADR-0121-savesession-decomposition-strategy.md) - SaveSession Decomposition Strategy
- [ADR-0122](ADR-0122-action-method-factory-pattern.md) - Action Method Factory Pattern
- [ADR-0125](ADR-0125-savesession-invalidation.md) - SaveSession Cache Invalidation Hook

## Custom Fields

Custom field handling, accessors, cascading, tracking, and resolution.

- [ADR-0030](ADR-0030-custom-field-typing.md) - Custom Field Typing
- [ADR-0034](ADR-0034-dynamic-custom-field-resolution.md) - Dynamic Custom Field Resolution Strategy
- [ADR-0051](ADR-0051-custom-field-type-safety.md) - Custom Field Type Safety
- [ADR-0054](ADR-0054-cascading-custom-fields.md) - Cascading Custom Fields Strategy
- [ADR-0056](ADR-0056-custom-field-api-format.md) - Custom Field API Format Conversion
- [ADR-0062](ADR-0062-custom-field-accessor-enhancement.md) - CustomFieldAccessor Enhancement vs. Wrapper
- [ADR-0067](ADR-0067-custom-field-snapshot-detection.md) - Custom Field Snapshot Detection Strategy
- [ADR-0074](ADR-0074-unified-custom-field-tracking.md) - Unified Custom Field Tracking via CustomFieldAccessor
- [ADR-0081](ADR-0081-custom-field-descriptor-pattern.md) - Custom Field Descriptor Pattern
- [ADR-0112](ADR-0112-custom-field-gid-resolution.md) - Custom Field GID Resolution Pattern
- [ADR-0113](ADR-0113-rep-field-cascade-pattern.md) - Rep Field Cascade Pattern
- [ADR-0117](ADR-0117-accessor-descriptor-unification.md) - CustomFieldAccessor/Descriptor Unification Strategy

## Integration

External API integration, Asana SDK, webhooks, and service boundaries.

- [ADR-0003](ADR-0003-asana-sdk-integration.md) - Replace Asana SDK HTTP Layer, Retain Types and Error Parsing
- [ADR-0007](ADR-0007-consistent-client-pattern.md) - Consistent Client Pattern Across Resource Types
- [ADR-0008](ADR-0008-webhook-signature-verification.md) - Webhook Signature Verification Strategy
- [ADR-0009](ADR-0009-attachment-multipart-handling.md) - Attachment Multipart/Form-Data Handling
- [ADR-0013](ADR-0013-correlation-id-strategy.md) - Correlation ID Strategy for SDK Observability
- [ADR-0015](ADR-0015-batch-api-request-format.md) - Batch API Request Format Fix
- [ADR-0063](ADR-0063-client-reference-storage.md) - Client Reference Storage

## Error Handling & Resilience

Error classification, retry strategies, circuit breakers, and graceful degradation.

- [ADR-0040](ADR-0040-partial-failure-handling.md) - Commit and Report on Partial Failure
- [ADR-0048](ADR-0048-circuit-breaker-pattern.md) - Circuit Breaker Pattern for Transport Layer
- [ADR-0065](ADR-0065-savesession-error-exception.md) - SaveSessionError Exception for P1 Methods
- [ADR-0070](ADR-0070-hydration-partial-failure.md) - Hydration Partial Failure Handling
- [ADR-0079](ADR-0079-retryable-error-classification.md) - Retryable Error Classification
- [ADR-0084](ADR-0084-exception-rename-strategy.md) - Exception Rename Strategy
- [ADR-0090](ADR-0090-demo-error-handling.md) - Error Handling Strategy for Demo Scripts
- [ADR-0091](ADR-0091-error-classification-mixin.md) - RetryableErrorMixin for Error Classification
- [ADR-0127](ADR-0127-graceful-degradation.md) - Cache Graceful Degradation Strategy

## Observability

Logging, monitoring, correlation, telemetry, and debugging support.

- [ADR-0013](ADR-0013-correlation-id-strategy.md) - Correlation ID Strategy for SDK Observability
- [ADR-0022](ADR-0022-overflow-management.md) - Overflow Management
- [ADR-0023](ADR-0023-observability-strategy.md) - Observability Strategy
- [ADR-0085](ADR-0085-observability-hook-protocol.md) - ObservabilityHook Protocol Design
- [ADR-0086](ADR-0086-structured-logging.md) - Logging Standardization
- [ADR-0088](ADR-0088-demo-state-capture.md) - State Capture Strategy for Demo Restoration

## API Design

Public API design, hydration, field selection, and interface contracts.

- [ADR-0012](ADR-0012-public-api-surface.md) - Public API Surface Definition
- [ADR-0046](ADR-0046-comment-text-storage.md) - Comment Text Storage Strategy
- [ADR-0047](ADR-0047-positioning-validation-timing.md) - Positioning Validation Timing
- [ADR-0069](ADR-0069-hydration-api-design.md) - Hydration API Design
- [ADR-0073](ADR-0073-batch-resolution-api-design.md) - Batch Resolution API Design
- [ADR-0128](ADR-0128-hydration-opt-fields-normalization.md) - Hydration opt_fields Normalization

## Process & Workflow

Process pipelines, workflow automation, and business logic orchestration.

- [ADR-0093](ADR-0093-project-type-registry.md) - Project-to-EntityType Registry Pattern
- [ADR-0096](ADR-0096-processtype-expansion.md) - ProcessType Expansion and Detection
- [ADR-0097](ADR-0097-processsection-state-machine.md) - ProcessSection State Machine Pattern
- [ADR-0099](ADR-0099-businessseeder-factory.md) - BusinessSeeder Factory Pattern
- [ADR-0101](ADR-0101-process-pipeline-correction.md) - Process Pipeline Architecture Correction
- [ADR-0102](ADR-0102-post-commit-hook-architecture.md) - Post-Commit Hook Architecture
- [ADR-0103](ADR-0103-automation-rule-protocol.md) - Automation Rule Protocol
- [ADR-0105](ADR-0105-field-seeding-architecture.md) - Field Seeding Architecture
- [ADR-0135](ADR-0135-processholder-detection.md) - ProcessHolder Detection Strategy
- [ADR-0136](ADR-0136-process-field-architecture.md) - Process Field Accessor Architecture

## Testing & Demo

Demo scripts, test strategies, example code, and validation approaches.

- [ADR-0014](ADR-0014-example-scripts-env-config.md) - Environment Variable Configuration for Example Scripts
- [ADR-0058](ADR-0058-bug4-out-of-scope.md) - BUG-4 Demo GID Display Out of Scope
- [ADR-0088](ADR-0088-demo-state-capture.md) - State Capture Strategy for Demo Restoration
- [ADR-0089](ADR-0089-demo-name-resolution.md) - Name Resolution Approach for Demo Scripts
- [ADR-0090](ADR-0090-demo-error-handling.md) - Error Handling Strategy for Demo Scripts

## Refactoring & Migration

Code cleanup, tech debt, migration strategies, and backward compatibility.

- [ADR-0011](ADR-0011-deprecation-warning-strategy.md) - Deprecation Warning Strategy for Compatibility Layer
- [ADR-0025](ADR-0025-migration-strategy.md) - Big-Bang Migration Strategy
- [ADR-0027](ADR-0027-dataframe-layer-migration-strategy.md) - Dataframe Layer Migration Strategy
- [ADR-0084](ADR-0084-exception-rename-strategy.md) - Exception Rename Strategy
- [ADR-0114](ADR-0114-hours-backward-compat.md) - Hours Model Backward Compatibility Strategy

## Rejection Decisions

NO-GO decisions and rejected architectural approaches.

- [ADR-0058](ADR-0058-bug4-out-of-scope.md) - BUG-4 Demo GID Display Out of Scope
- [ADR-0092](ADR-0092-crud-base-class-nogo.md) - CRUD Client Base Class Evaluation (Rejected)
- [ADR-0118](ADR-0118-rejection-multi-level-cache.md) - Rejection of Multi-Level Cache Hierarchy

---

**Maintenance Note**: When creating new ADRs, update this index to maintain discoverability. Category assignments are editorial - some ADRs fit multiple topics.
