# ADR Index

## Quick Navigation
- [Start Here](#start-here) - Essential reading for new contributors
- [By Theme](#by-theme) - ADRs organized by topic
- [By Number](#by-number) - Complete chronological list
- [Supersession Chains](#supersession-chains) - Decision evolution

---

## Start Here

**New to autom8_asana?** Start with these foundational ADRs to understand the core architectural patterns:

### 1. Protocol-Based Extensibility
[ADR-0001: Protocol-Based Extensibility for Dependency Injection](ADR-0001-protocol-extensibility.md) - **READ FIRST**

Establishes the protocol-based dependency injection pattern used throughout the SDK. Understanding this is essential for understanding how caching, logging, and other cross-cutting concerns integrate.

### 2. SaveSession & Unit of Work
[ADR-0035: Unit of Work Pattern for Save Orchestration](ADR-0035-unit-of-work-pattern.md)

The SaveSession is the heart of autom8_asana's "Asana as database" paradigm. This ADR explains the Django-ORM-inspired pattern for batching and orchestrating changes.

### 3. Two-Tier Caching Architecture
[ADR-0026: Two-Tier Cache Architecture (Redis + S3)](ADR-0026-two-tier-cache-architecture.md)

Explains the Redis (hot) + S3 (cold) caching strategy that makes autom8_asana performant. Essential for understanding cache integration patterns.

### 4. Custom Field Descriptor Pattern
[ADR-0081: Custom Field Descriptor Pattern](ADR-0081-custom-field-descriptor-pattern.md)

Custom fields are pervasive in Asana. This ADR shows how Python descriptors provide type-safe, IDE-friendly access to custom fields with automatic GID resolution.

### 5. Consistent Client Pattern
[ADR-0007: Consistent Client Pattern Across Resource Types](ADR-0007-consistent-client-pattern.md)

Establishes the uniform `*Client` pattern (TasksClient, ProjectsClient, etc.) for SDK API access, including async-first design and sync wrappers.

### 6. Detection & Self-Healing
[ADR-0094: Detection Fallback Chain Design](ADR-0094-detection-fallback-chain.md)

Explains the three-tier detection system (cached metadata → custom field examination → pattern matching) that enables automatic entity type identification.

### 7. Process Pipeline Architecture
[ADR-0101: Process Pipeline Architecture Correction](ADR-0101-process-pipeline-correction.md)

Documents the "hierarchies, not pipelines" insight that simplified the Process automation architecture. Important for understanding why certain patterns were rejected.

---

## By Theme

### Architecture & Extensibility

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0001 | [Protocol-Based Extensibility for Dependency Injection](ADR-0001-protocol-extensibility.md) | Accepted |
| ADR-0002 | [Fail-Fast Strategy for Sync Wrappers in Async Contexts](ADR-0002-sync-wrapper-strategy.md) | Accepted |
| ADR-0003 | [Replace Asana SDK HTTP Layer, Retain Types and Error Parsing](ADR-0003-asana-sdk-integration.md) | Accepted |
| ADR-0004 | [Minimal AsanaResource in SDK, Full Item Stays in Monolith](ADR-0004-item-class-boundary.md) | Accepted |
| ADR-0007 | [Consistent Client Pattern Across Resource Types](ADR-0007-consistent-client-pattern.md) | Accepted |
| ADR-0012 | [Public API Surface Definition](ADR-0012-public-api-surface.md) | Proposed |
| ADR-0025 | [Big-Bang Migration Strategy](ADR-0025-migration-strategy.md) | Accepted |
| ADR-0038 | [Async-First Concurrency for Save Operations](ADR-0038-save-concurrency-model.md) | Accepted |
| ADR-0092 | [CRUD Client Base Class Evaluation](ADR-0092-crud-base-class-nogo.md) | Rejected |

### Caching Architecture

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0016 | [Cache Protocol Extension](ADR-0016-cache-protocol-extension.md) | Accepted |
| ADR-0017 | [Redis Backend Architecture](ADR-0017-redis-backend-architecture.md) | Accepted |
| ADR-0021 | [Dataframe Caching Strategy](ADR-0021-dataframe-caching-strategy.md) | Accepted |
| ADR-0026 | [Two-Tier Cache Architecture (Redis + S3)](ADR-0026-two-tier-cache-architecture.md) | Accepted |
| ADR-0032 | [Cache Granularity](ADR-0032-cache-granularity.md) | Accepted |
| ADR-0052 | [Bidirectional Reference Caching](ADR-0052-bidirectional-reference-caching.md) | Accepted |
| ADR-0060 | [Name Resolution Caching Strategy](ADR-0060-name-resolution-caching-strategy.md) | Accepted |
| ADR-0072 | [Resolution Caching Decision](ADR-0072-resolution-caching-decision.md) | Accepted |
| ADR-0076 | [Auto-Invalidation Strategy](ADR-0076-auto-invalidation-strategy.md) | Accepted |
| ADR-0116 | [Batch Cache Population Pattern](ADR-0116-batch-cache-population-pattern.md) | Accepted |
| ADR-0118 | [Rejection of Multi-Level Cache Hierarchy](ADR-0118-rejection-multi-level-cache.md) | Accepted |
| ADR-0119 | [Client Cache Integration Pattern](ADR-0119-client-cache-integration-pattern.md) | Accepted |
| ADR-0120 | [Batch Cache Population on Bulk Fetch](ADR-0120-batch-cache-population-on-bulk-fetch.md) | Accepted |
| ADR-0123 | [Default Cache Provider Selection Strategy](ADR-0123-cache-provider-selection.md) | Proposed |
| ADR-0124 | [Client Cache Integration Pattern](ADR-0124-client-cache-pattern.md) | Proposed |
| ADR-0127 | [Cache Graceful Degradation Strategy](ADR-0127-graceful-degradation.md) | Proposed |
| ADR-0129 | [Stories Client Cache Wiring Strategy](ADR-0129-stories-client-cache-wiring.md) | Proposed |
| ADR-0130 | [Cache Population Location Strategy](ADR-0130-cache-population-location.md) | Proposed |
| ADR-0131 | [GID Enumeration Cache Strategy](ADR-0131-gid-enumeration-cache-strategy.md) | Proposed |
| ADR-0137 | [Post-Commit Invalidation Hook for DataFrame Cache](ADR-0137-post-commit-invalidation-hook.md) | Accepted |
| ADR-0140 | [DataFrame Task Cache Integration Strategy](ADR-0140-dataframe-task-cache-integration.md) | Proposed |
| ADR-0143 | [Detection Result Caching Strategy](ADR-0143-detection-result-caching.md) | Proposed |

### Staleness Detection & TTL

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0019 | [Staleness Detection Algorithm](ADR-0019-staleness-detection-algorithm.md) | Accepted |
| ADR-0126 | [Entity-Type TTL Resolution Strategy](ADR-0126-entity-ttl-resolution.md) | Proposed |
| ADR-0133 | [Progressive TTL Extension Algorithm](ADR-0133-progressive-ttl-extension-algorithm.md) | Proposed |
| ADR-0134 | [Staleness Check Integration Pattern](ADR-0134-staleness-check-integration-pattern.md) | Proposed |

### SaveSession & Unit of Work

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0035 | [Unit of Work Pattern for Save Orchestration](ADR-0035-unit-of-work-pattern.md) | Accepted |
| ADR-0036 | [Change Tracking via Snapshot Comparison](ADR-0036-change-tracking-strategy.md) | Accepted |
| ADR-0037 | [Kahn's Algorithm for Dependency Ordering](ADR-0037-dependency-graph-algorithm.md) | Accepted |
| ADR-0039 | [Fixed-Size Sequential Batch Execution](ADR-0039-batch-execution-strategy.md) | Accepted |
| ADR-0040 | [Commit and Report on Partial Failure](ADR-0040-partial-failure-handling.md) | Accepted |
| ADR-0041 | [Synchronous Event Hooks with Async Support](ADR-0041-event-hook-system.md) | Accepted |
| ADR-0053 | [Composite SaveSession Support](ADR-0053-composite-savesession-support.md) | Accepted |
| ADR-0059 | [Direct Methods vs. SaveSession Actions](ADR-0059-direct-methods-vs-session-actions.md) | Accepted |
| ADR-0061 | [Implicit SaveSession Lifecycle](ADR-0061-implicit-savesession-lifecycle.md) | Accepted |
| ADR-0064 | [Dirty Detection Strategy](ADR-0064-dirty-detection-strategy.md) | Accepted |
| ADR-0065 | [SaveSessionError Exception for P1 Methods](ADR-0065-savesession-error-exception.md) | Proposed |
| ADR-0066 | [Selective Action Clearing Strategy](ADR-0066-selective-action-clearing.md) | Proposed |
| ADR-0121 | [SaveSession Decomposition Strategy](ADR-0121-savesession-decomposition-strategy.md) | Proposed |
| ADR-0125 | [SaveSession Cache Invalidation Hook](ADR-0125-savesession-invalidation.md) | Proposed |

### Custom Fields

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0030 | [Custom Field Typing](ADR-0030-custom-field-typing.md) | Accepted |
| ADR-0034 | [Dynamic Custom Field Resolution Strategy](ADR-0034-dynamic-custom-field-resolution.md) | Accepted |
| ADR-0051 | [Custom Field Type Safety](ADR-0051-custom-field-type-safety.md) | Accepted |
| ADR-0054 | [Cascading Custom Fields Strategy](ADR-0054-cascading-custom-fields.md) | Proposed |
| ADR-0056 | [Custom Field API Format Conversion](ADR-0056-custom-field-api-format.md) | Proposed |
| ADR-0062 | [CustomFieldAccessor Enhancement vs. Wrapper](ADR-0062-custom-field-accessor-enhancement.md) | Accepted |
| ADR-0067 | [Custom Field Snapshot Detection Strategy](ADR-0067-custom-field-snapshot-detection.md) | Proposed |
| ADR-0074 | [Unified Custom Field Tracking via CustomFieldAccessor](ADR-0074-unified-custom-field-tracking.md) | Proposed |
| ADR-0081 | [Custom Field Descriptor Pattern](ADR-0081-custom-field-descriptor-pattern.md) | Accepted |
| ADR-0082 | [Fields Class Auto-Generation Strategy](ADR-0082-fields-auto-generation-strategy.md) | Accepted |
| ADR-0112 | [Custom Field GID Resolution Pattern](ADR-0112-custom-field-gid-resolution.md) | Accepted |
| ADR-0113 | [Rep Field Cascade Pattern](ADR-0113-rep-field-cascade-pattern.md) | Accepted |
| ADR-0117 | [CustomFieldAccessor/Descriptor Unification Strategy](ADR-0117-accessor-descriptor-unification.md) | Accepted |

### Detection & Type Identification

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0068 | [Type Detection Strategy for Upward Traversal](ADR-0068-type-detection-strategy.md) | Accepted |
| ADR-0080 | [Entity Registry Scope](ADR-0080-entity-registry-scope.md) | Accepted |
| ADR-0093 | [Project-to-EntityType Registry Pattern](ADR-0093-project-type-registry.md) | Proposed |
| ADR-0094 | [Detection Fallback Chain Design](ADR-0094-detection-fallback-chain.md) | Proposed |
| ADR-0108 | [WorkspaceProjectRegistry Architecture](ADR-0108-workspace-project-registry.md) | Proposed |
| ADR-0109 | [Lazy Discovery Timing for WorkspaceProjectRegistry](ADR-0109-lazy-discovery-timing.md) | Proposed |
| ADR-0135 | [ProcessHolder Detection Strategy](ADR-0135-processholder-detection.md) | Proposed |
| ADR-0138 | [Detection Tier 2 Pattern Matching Enhancement](ADR-0138-tier2-pattern-enhancement.md) | Proposed |
| ADR-0142 | [Detection Package Structure](ADR-0142-detection-package-structure.md) | Proposed |

### Self-Healing & Automation

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0095 | [Self-Healing Integration with SaveSession](ADR-0095-self-healing-integration.md) | Proposed |
| ADR-0102 | [Post-Commit Hook Architecture](ADR-0102-post-commit-hook-architecture.md) | Accepted |
| ADR-0103 | [Automation Rule Protocol](ADR-0103-automation-rule-protocol.md) | Accepted |
| ADR-0104 | [Loop Prevention Strategy](ADR-0104-loop-prevention-strategy.md) | Accepted |
| ADR-0105 | [Field Seeding Architecture](ADR-0105-field-seeding-architecture.md) | Accepted |
| ADR-0106 | [Template Discovery Pattern](ADR-0106-template-discovery-pattern.md) | Accepted |
| ADR-0139 | [Self-Healing Opt-In Design](ADR-0139-self-healing-design.md) | Proposed |
| ADR-0144 | [HealingResult Type Consolidation](ADR-0144-healingresult-consolidation.md) | Proposed |

### Process Pipeline & Business Entities

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0096 | [ProcessType Expansion and Detection](ADR-0096-processtype-expansion.md) | Partially Superseded |
| ADR-0097 | [ProcessSection State Machine Pattern](ADR-0097-processsection-state-machine.md) | Accepted |
| ADR-0098 | [Dual Membership Model](ADR-0098-dual-membership-model.md) | Superseded |
| ADR-0099 | [BusinessSeeder Factory Pattern](ADR-0099-businessseeder-factory.md) | Accepted |
| ADR-0100 | [State Transition Composition with SaveSession](ADR-0100-state-transition-composition.md) | Superseded |
| ADR-0101 | [Process Pipeline Architecture Correction](ADR-0101-process-pipeline-correction.md) | Accepted |
| ADR-0136 | [Process Field Accessor Architecture](ADR-0136-process-field-architecture.md) | Proposed |
| ADR-0141 | [Field Mixin Strategy for Sprint 1 Pattern Completion](ADR-0141-field-mixin-strategy.md) | Proposed |

### API Design & Actions

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0042 | [Separate ActionType Enum for Action Endpoint Operations](ADR-0042-action-operation-types.md) | Proposed |
| ADR-0043 | [Validation-Phase Detection for Unsupported Direct Modifications](ADR-0043-unsupported-operation-detection.md) | Proposed |
| ADR-0044 | [extra_params Field Design for ActionOperation](ADR-0044-extra-params-field.md) | Accepted |
| ADR-0045 | [Like Operations Without Target GID](ADR-0045-like-operations-without-target.md) | Accepted |
| ADR-0055 | [Action Result Integration into SaveResult](ADR-0055-action-result-integration.md) | Proposed |
| ADR-0107 | [NameGid for ActionOperation Targets](ADR-0107-namegid-action-targets.md) | Accepted |
| ADR-0122 | [Action Method Factory Pattern](ADR-0122-action-method-factory-pattern.md) | Proposed |

### Batch Operations

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0010 | [Sequential Chunk Execution for Batch Operations](ADR-0010-batch-chunking-strategy.md) | Accepted |
| ADR-0015 | [Batch API Request Format Fix](ADR-0015-batch-api-request-format.md) | Accepted |
| ADR-0018 | [Batch Modification Checking](ADR-0018-batch-modification-checking.md) | Accepted |
| ADR-0132 | [Batch Request Coalescing Strategy](ADR-0132-batch-request-coalescing-strategy.md) | Proposed |

### Hydration & Data Loading

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0020 | [Incremental Story Loading](ADR-0020-incremental-story-loading.md) | Accepted |
| ADR-0031 | [Lazy vs Eager Evaluation](ADR-0031-lazy-eager-evaluation.md) | Accepted |
| ADR-0050 | [Holder Lazy Loading Strategy](ADR-0050-holder-lazy-loading-strategy.md) | Accepted |
| ADR-0069 | [Hydration API Design](ADR-0069-hydration-api-design.md) | Accepted |
| ADR-0070 | [Hydration Partial Failure Handling](ADR-0070-hydration-partial-failure.md) | Accepted |
| ADR-0071 | [Resolution Ambiguity Handling](ADR-0071-resolution-ambiguity-handling.md) | Accepted |
| ADR-0073 | [Batch Resolution API Design](ADR-0073-batch-resolution-api-design.md) | Accepted |
| ADR-0115 | [Parallel Section Fetch Strategy](ADR-0115-parallel-section-fetch-strategy.md) | Accepted |
| ADR-0128 | [Hydration opt_fields Normalization](ADR-0128-hydration-opt-fields-normalization.md) | Proposed |

### DataFrame Integration

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0027 | [Dataframe Layer Migration Strategy](ADR-0027-dataframe-layer-migration-strategy.md) | Completed |
| ADR-0028 | [Polars DataFrame Library](ADR-0028-polars-dataframe-library.md) | Accepted |

### Descriptors & Navigation

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0075 | [Navigation Descriptor Pattern](ADR-0075-navigation-descriptor-pattern.md) | Accepted |
| ADR-0077 | [Pydantic v2 Descriptor Compatibility](ADR-0077-pydantic-descriptor-compatibility.md) | Accepted |

### Observability & Logging

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0013 | [Correlation ID Strategy for SDK Observability](ADR-0013-correlation-id-strategy.md) | Proposed |
| ADR-0023 | [Observability Strategy](ADR-0023-observability-strategy.md) | Accepted |
| ADR-0085 | [ObservabilityHook Protocol Design](ADR-0085-observability-hook-protocol.md) | Proposed |
| ADR-0086 | [Logging Standardization](ADR-0086-structured-logging.md) | Proposed |

### Error Handling & Resilience

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0048 | [Circuit Breaker Pattern for Transport Layer](ADR-0048-circuit-breaker-pattern.md) | Accepted |
| ADR-0079 | [Retryable Error Classification](ADR-0079-retryable-error-classification.md) | Accepted |
| ADR-0084 | [Exception Rename Strategy](ADR-0084-exception-rename-strategy.md) | Proposed |
| ADR-0091 | [RetryableErrorMixin for Error Classification](ADR-0091-error-classification-mixin.md) | Accepted |

### Data Models & Type Safety

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0005 | [Pydantic v2 with `extra="ignore"` for Forward Compatibility](ADR-0005-pydantic-model-config.md) | Accepted |
| ADR-0006 | [NameGid as Standalone Frozen Model](ADR-0006-namegid-standalone-model.md) | Proposed |
| ADR-0029 | [Task Subclass Strategy](ADR-0029-task-subclass-strategy.md) | Accepted |
| ADR-0033 | [Schema Enforcement](ADR-0033-schema-enforcement.md) | Accepted |
| ADR-0046 | [Comment Text Storage Strategy](ADR-0046-comment-text-storage.md) | Accepted |
| ADR-0049 | [GID Validation Strategy](ADR-0049-gid-validation-strategy.md) | Accepted |
| ADR-0078 | [GID-Based Entity Identity Strategy](ADR-0078-gid-based-entity-identity.md) | Accepted |
| ADR-0083 | [DateField Arrow Integration](ADR-0083-datefield-arrow-integration.md) | Accepted |
| ADR-0087 | [Minimal Stub Model Pattern](ADR-0087-stub-model-pattern.md) | Proposed |
| ADR-0114 | [Hours Model Backward Compatibility Strategy](ADR-0114-hours-backward-compat.md) | Proposed |
| ADR-SDK-005 | [Pydantic Settings Standards](ADR-SDK-005-pydantic-settings-standards.md) | Accepted |

### Special Operations

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0047 | [Positioning Validation Timing](ADR-0047-positioning-validation-timing.md) | Accepted |
| ADR-0057 | [Add subtasks_async Method to TasksClient](ADR-0057-subtasks-async-method.md) | Proposed |
| ADR-0110 | [Task Duplication vs Creation Strategy](ADR-0110-task-duplication-strategy.md) | Accepted |
| ADR-0111 | [Subtask Wait Strategy](ADR-0111-subtask-wait-strategy.md) | Accepted |

### Performance & Optimization

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0022 | [Overflow Management](ADR-0022-overflow-management.md) | Accepted |
| ADR-0024 | [Thread-Safety Guarantees](ADR-0024-thread-safety-guarantees.md) | Accepted |

### Client & Transport

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0008 | [Webhook Signature Verification Strategy](ADR-0008-webhook-signature-verification.md) | Accepted |
| ADR-0009 | [Attachment Multipart/Form-Data Handling](ADR-0009-attachment-multipart-handling.md) | Accepted |
| ADR-0063 | [Client Reference Storage](ADR-0063-client-reference-storage.md) | Accepted |

### Deprecation & Compatibility

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0011 | [Deprecation Warning Strategy for Compatibility Layer](ADR-0011-deprecation-warning-strategy.md) | Proposed |

### Development Tooling & Examples

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0014 | [Environment Variable Configuration for Example Scripts](ADR-0014-example-scripts-env-config.md) | Accepted |
| ADR-0058 | [BUG-4 Demo GID Display Out of Scope](ADR-0058-bug4-out-of-scope.md) | Accepted |
| ADR-0088 | [State Capture Strategy for Demo Restoration](ADR-0088-demo-state-capture.md) | Accepted |
| ADR-0089 | [Name Resolution Approach for Demo Scripts](ADR-0089-demo-name-resolution.md) | Accepted |
| ADR-0090 | [Error Handling Strategy for Demo Scripts](ADR-0090-demo-error-handling.md) | Accepted |

---

## Supersession Chains

### Process Pipeline Evolution
The Process Pipeline feature went through significant architectural revision:

1. **ADR-0096**: ProcessType Expansion and Detection (Partially Superseded)
   - ProcessProjectRegistry portion superseded by ADR-0101
   - ProcessType expansion still valid

2. **ADR-0098**: Dual Membership Model (Superseded)
   - Proposed dual membership for process entities
   - **Superseded by ADR-0101**

3. **ADR-0100**: State Transition Composition with SaveSession (Superseded)
   - Proposed move_to_state functionality
   - **Superseded by ADR-0101** (move_to_state removed)

4. **ADR-0101**: Process Pipeline Architecture Correction ✓ **CURRENT**
   - "Hierarchies, not pipelines" insight
   - Removed dual membership complexity
   - Uses WorkspaceProjectRegistry for dynamic discovery

### Cache Architecture Evolution
The caching system evolved from single-tier to two-tier:

1. **ADR-0017**: Redis Backend Architecture
   - Initial Redis-only implementation
   - Still valid for Redis tier

2. **ADR-0026**: Two-Tier Cache Architecture ✓ **CURRENT**
   - Adds S3 cold tier to Redis hot tier
   - Supersedes ADR-0017 for the "S3 aspect"
   - ADR-0017 remains valid for Redis implementation details

### Detection Strategy Evolution
Entity type detection evolved from simple upward traversal to multi-tier fallback:

1. **ADR-0068**: Type Detection Strategy for Upward Traversal
   - Initial upward traversal approach
   - Superseded by ADR-0093 and ADR-0094

2. **ADR-0093**: Project-to-EntityType Registry Pattern
   - Tier 1: Cached metadata lookup
   - References ADR-0068 as superseded

3. **ADR-0094**: Detection Fallback Chain Design ✓ **CURRENT**
   - Tier 1: Registry lookup (ADR-0093)
   - Tier 2: Custom field examination
   - Tier 3: Pattern matching
   - References ADR-0068 as superseded

### Multi-Level Cache Rejection
**ADR-0118**: Rejection of Multi-Level Cache Hierarchy

This ADR documents the decision to **reject** a multi-level cache hierarchy (L1/L2/L3) in favor of the simpler two-tier Redis+S3 architecture. Important for understanding why certain patterns were not adopted.

---

## By Number

### ADR-0001 to ADR-0050
| ADR | Title | Status |
|-----|-------|--------|
| ADR-0001 | [Protocol-Based Extensibility for Dependency Injection](ADR-0001-protocol-extensibility.md) | Accepted |
| ADR-0002 | [Fail-Fast Strategy for Sync Wrappers in Async Contexts](ADR-0002-sync-wrapper-strategy.md) | Accepted |
| ADR-0003 | [Replace Asana SDK HTTP Layer, Retain Types and Error Parsing](ADR-0003-asana-sdk-integration.md) | Accepted |
| ADR-0004 | [Minimal AsanaResource in SDK, Full Item Stays in Monolith](ADR-0004-item-class-boundary.md) | Accepted |
| ADR-0005 | [Pydantic v2 with `extra="ignore"` for Forward Compatibility](ADR-0005-pydantic-model-config.md) | Accepted |
| ADR-0006 | [NameGid as Standalone Frozen Model](ADR-0006-namegid-standalone-model.md) | Proposed |
| ADR-0007 | [Consistent Client Pattern Across Resource Types](ADR-0007-consistent-client-pattern.md) | Accepted |
| ADR-0008 | [Webhook Signature Verification Strategy](ADR-0008-webhook-signature-verification.md) | Accepted |
| ADR-0009 | [Attachment Multipart/Form-Data Handling](ADR-0009-attachment-multipart-handling.md) | Accepted |
| ADR-0010 | [Sequential Chunk Execution for Batch Operations](ADR-0010-batch-chunking-strategy.md) | Accepted |
| ADR-0011 | [Deprecation Warning Strategy for Compatibility Layer](ADR-0011-deprecation-warning-strategy.md) | Proposed |
| ADR-0012 | [Public API Surface Definition](ADR-0012-public-api-surface.md) | Proposed |
| ADR-0013 | [Correlation ID Strategy for SDK Observability](ADR-0013-correlation-id-strategy.md) | Proposed |
| ADR-0014 | [Environment Variable Configuration for Example Scripts](ADR-0014-example-scripts-env-config.md) | Accepted |
| ADR-0015 | [Batch API Request Format Fix](ADR-0015-batch-api-request-format.md) | Accepted |
| ADR-0016 | [Cache Protocol Extension](ADR-0016-cache-protocol-extension.md) | Accepted |
| ADR-0017 | [Redis Backend Architecture](ADR-0017-redis-backend-architecture.md) | Accepted |
| ADR-0018 | [Batch Modification Checking](ADR-0018-batch-modification-checking.md) | Accepted |
| ADR-0019 | [Staleness Detection Algorithm](ADR-0019-staleness-detection-algorithm.md) | Accepted |
| ADR-0020 | [Incremental Story Loading](ADR-0020-incremental-story-loading.md) | Accepted |
| ADR-0021 | [Dataframe Caching Strategy](ADR-0021-dataframe-caching-strategy.md) | Accepted |
| ADR-0022 | [Overflow Management](ADR-0022-overflow-management.md) | Accepted |
| ADR-0023 | [Observability Strategy](ADR-0023-observability-strategy.md) | Accepted |
| ADR-0024 | [Thread-Safety Guarantees](ADR-0024-thread-safety-guarantees.md) | Accepted |
| ADR-0025 | [Big-Bang Migration Strategy](ADR-0025-migration-strategy.md) | Accepted |
| ADR-0026 | [Two-Tier Cache Architecture (Redis + S3)](ADR-0026-two-tier-cache-architecture.md) | Accepted |
| ADR-0027 | [Dataframe Layer Migration Strategy](ADR-0027-dataframe-layer-migration-strategy.md) | Completed |
| ADR-0028 | [Polars DataFrame Library](ADR-0028-polars-dataframe-library.md) | Accepted |
| ADR-0029 | [Task Subclass Strategy](ADR-0029-task-subclass-strategy.md) | Accepted |
| ADR-0030 | [Custom Field Typing](ADR-0030-custom-field-typing.md) | Accepted |
| ADR-0031 | [Lazy vs Eager Evaluation](ADR-0031-lazy-eager-evaluation.md) | Accepted |
| ADR-0032 | [Cache Granularity](ADR-0032-cache-granularity.md) | Accepted |
| ADR-0033 | [Schema Enforcement](ADR-0033-schema-enforcement.md) | Accepted |
| ADR-0034 | [Dynamic Custom Field Resolution Strategy](ADR-0034-dynamic-custom-field-resolution.md) | Accepted |
| ADR-0035 | [Unit of Work Pattern for Save Orchestration](ADR-0035-unit-of-work-pattern.md) | Accepted |
| ADR-0036 | [Change Tracking via Snapshot Comparison](ADR-0036-change-tracking-strategy.md) | Accepted |
| ADR-0037 | [Kahn's Algorithm for Dependency Ordering](ADR-0037-dependency-graph-algorithm.md) | Accepted |
| ADR-0038 | [Async-First Concurrency for Save Operations](ADR-0038-save-concurrency-model.md) | Accepted |
| ADR-0039 | [Fixed-Size Sequential Batch Execution](ADR-0039-batch-execution-strategy.md) | Accepted |
| ADR-0040 | [Commit and Report on Partial Failure](ADR-0040-partial-failure-handling.md) | Accepted |
| ADR-0041 | [Synchronous Event Hooks with Async Support](ADR-0041-event-hook-system.md) | Accepted |
| ADR-0042 | [Separate ActionType Enum for Action Endpoint Operations](ADR-0042-action-operation-types.md) | Proposed |
| ADR-0043 | [Validation-Phase Detection for Unsupported Direct Modifications](ADR-0043-unsupported-operation-detection.md) | Proposed |
| ADR-0044 | [extra_params Field Design for ActionOperation](ADR-0044-extra-params-field.md) | Accepted |
| ADR-0045 | [Like Operations Without Target GID](ADR-0045-like-operations-without-target.md) | Accepted |
| ADR-0046 | [Comment Text Storage Strategy](ADR-0046-comment-text-storage.md) | Accepted |
| ADR-0047 | [Positioning Validation Timing](ADR-0047-positioning-validation-timing.md) | Accepted |
| ADR-0048 | [Circuit Breaker Pattern for Transport Layer](ADR-0048-circuit-breaker-pattern.md) | Accepted |
| ADR-0049 | [GID Validation Strategy](ADR-0049-gid-validation-strategy.md) | Accepted |
| ADR-0050 | [Holder Lazy Loading Strategy](ADR-0050-holder-lazy-loading-strategy.md) | Accepted |

### ADR-0051 to ADR-0100
| ADR | Title | Status |
|-----|-------|--------|
| ADR-0051 | [Custom Field Type Safety](ADR-0051-custom-field-type-safety.md) | Accepted |
| ADR-0052 | [Bidirectional Reference Caching](ADR-0052-bidirectional-reference-caching.md) | Accepted |
| ADR-0053 | [Composite SaveSession Support](ADR-0053-composite-savesession-support.md) | Accepted |
| ADR-0054 | [Cascading Custom Fields Strategy](ADR-0054-cascading-custom-fields.md) | Proposed |
| ADR-0055 | [Action Result Integration into SaveResult](ADR-0055-action-result-integration.md) | Proposed |
| ADR-0056 | [Custom Field API Format Conversion](ADR-0056-custom-field-api-format.md) | Proposed |
| ADR-0057 | [Add subtasks_async Method to TasksClient](ADR-0057-subtasks-async-method.md) | Proposed |
| ADR-0058 | [BUG-4 Demo GID Display Out of Scope](ADR-0058-bug4-out-of-scope.md) | Accepted |
| ADR-0059 | [Direct Methods vs. SaveSession Actions](ADR-0059-direct-methods-vs-session-actions.md) | Accepted |
| ADR-0060 | [Name Resolution Caching Strategy](ADR-0060-name-resolution-caching-strategy.md) | Accepted |
| ADR-0061 | [Implicit SaveSession Lifecycle](ADR-0061-implicit-savesession-lifecycle.md) | Accepted |
| ADR-0062 | [CustomFieldAccessor Enhancement vs. Wrapper](ADR-0062-custom-field-accessor-enhancement.md) | Accepted |
| ADR-0063 | [Client Reference Storage](ADR-0063-client-reference-storage.md) | Accepted |
| ADR-0064 | [Dirty Detection Strategy](ADR-0064-dirty-detection-strategy.md) | Accepted |
| ADR-0065 | [SaveSessionError Exception for P1 Methods](ADR-0065-savesession-error-exception.md) | Proposed |
| ADR-0066 | [Selective Action Clearing Strategy](ADR-0066-selective-action-clearing.md) | Proposed |
| ADR-0067 | [Custom Field Snapshot Detection Strategy](ADR-0067-custom-field-snapshot-detection.md) | Proposed |
| ADR-0068 | [Type Detection Strategy for Upward Traversal](ADR-0068-type-detection-strategy.md) | Accepted (Superseded) |
| ADR-0069 | [Hydration API Design](ADR-0069-hydration-api-design.md) | Accepted |
| ADR-0070 | [Hydration Partial Failure Handling](ADR-0070-hydration-partial-failure.md) | Accepted |
| ADR-0071 | [Resolution Ambiguity Handling](ADR-0071-resolution-ambiguity-handling.md) | Accepted |
| ADR-0072 | [Resolution Caching Decision](ADR-0072-resolution-caching-decision.md) | Accepted |
| ADR-0073 | [Batch Resolution API Design](ADR-0073-batch-resolution-api-design.md) | Accepted |
| ADR-0074 | [Unified Custom Field Tracking via CustomFieldAccessor](ADR-0074-unified-custom-field-tracking.md) | Proposed |
| ADR-0075 | [Navigation Descriptor Pattern](ADR-0075-navigation-descriptor-pattern.md) | Accepted |
| ADR-0076 | [Auto-Invalidation Strategy](ADR-0076-auto-invalidation-strategy.md) | Accepted |
| ADR-0077 | [Pydantic v2 Descriptor Compatibility](ADR-0077-pydantic-descriptor-compatibility.md) | Accepted |
| ADR-0078 | [GID-Based Entity Identity Strategy](ADR-0078-gid-based-entity-identity.md) | Accepted |
| ADR-0079 | [Retryable Error Classification](ADR-0079-retryable-error-classification.md) | Accepted |
| ADR-0080 | [Entity Registry Scope](ADR-0080-entity-registry-scope.md) | Accepted |
| ADR-0081 | [Custom Field Descriptor Pattern](ADR-0081-custom-field-descriptor-pattern.md) | Accepted |
| ADR-0082 | [Fields Class Auto-Generation Strategy](ADR-0082-fields-auto-generation-strategy.md) | Accepted |
| ADR-0083 | [DateField Arrow Integration](ADR-0083-datefield-arrow-integration.md) | Accepted |
| ADR-0084 | [Exception Rename Strategy](ADR-0084-exception-rename-strategy.md) | Proposed |
| ADR-0085 | [ObservabilityHook Protocol Design](ADR-0085-observability-hook-protocol.md) | Proposed |
| ADR-0086 | [Logging Standardization](ADR-0086-structured-logging.md) | Proposed |
| ADR-0087 | [Minimal Stub Model Pattern](ADR-0087-stub-model-pattern.md) | Proposed |
| ADR-0088 | [State Capture Strategy for Demo Restoration](ADR-0088-demo-state-capture.md) | Accepted |
| ADR-0089 | [Name Resolution Approach for Demo Scripts](ADR-0089-demo-name-resolution.md) | Accepted |
| ADR-0090 | [Error Handling Strategy for Demo Scripts](ADR-0090-demo-error-handling.md) | Accepted |
| ADR-0091 | [RetryableErrorMixin for Error Classification](ADR-0091-error-classification-mixin.md) | Accepted |
| ADR-0092 | [CRUD Client Base Class Evaluation](ADR-0092-crud-base-class-nogo.md) | Rejected |
| ADR-0093 | [Project-to-EntityType Registry Pattern](ADR-0093-project-type-registry.md) | Proposed |
| ADR-0094 | [Detection Fallback Chain Design](ADR-0094-detection-fallback-chain.md) | Proposed |
| ADR-0095 | [Self-Healing Integration with SaveSession](ADR-0095-self-healing-integration.md) | Proposed |
| ADR-0096 | [ProcessType Expansion and Detection](ADR-0096-processtype-expansion.md) | Partially Superseded |
| ADR-0097 | [ProcessSection State Machine Pattern](ADR-0097-processsection-state-machine.md) | Accepted |
| ADR-0098 | [Dual Membership Model](ADR-0098-dual-membership-model.md) | Superseded |
| ADR-0099 | [BusinessSeeder Factory Pattern](ADR-0099-businessseeder-factory.md) | Accepted |
| ADR-0100 | [State Transition Composition with SaveSession](ADR-0100-state-transition-composition.md) | Superseded |

### ADR-0101 to ADR-0144
| ADR | Title | Status |
|-----|-------|--------|
| ADR-0101 | [Process Pipeline Architecture Correction](ADR-0101-process-pipeline-correction.md) | Accepted |
| ADR-0102 | [Post-Commit Hook Architecture](ADR-0102-post-commit-hook-architecture.md) | Accepted |
| ADR-0103 | [Automation Rule Protocol](ADR-0103-automation-rule-protocol.md) | Accepted |
| ADR-0104 | [Loop Prevention Strategy](ADR-0104-loop-prevention-strategy.md) | Accepted |
| ADR-0105 | [Field Seeding Architecture](ADR-0105-field-seeding-architecture.md) | Accepted |
| ADR-0106 | [Template Discovery Pattern](ADR-0106-template-discovery-pattern.md) | Accepted |
| ADR-0107 | [NameGid for ActionOperation Targets](ADR-0107-namegid-action-targets.md) | Accepted |
| ADR-0108 | [WorkspaceProjectRegistry Architecture](ADR-0108-workspace-project-registry.md) | Proposed |
| ADR-0109 | [Lazy Discovery Timing for WorkspaceProjectRegistry](ADR-0109-lazy-discovery-timing.md) | Proposed |
| ADR-0110 | [Task Duplication vs Creation Strategy](ADR-0110-task-duplication-strategy.md) | Accepted |
| ADR-0111 | [Subtask Wait Strategy](ADR-0111-subtask-wait-strategy.md) | Accepted |
| ADR-0112 | [Custom Field GID Resolution Pattern](ADR-0112-custom-field-gid-resolution.md) | Accepted |
| ADR-0113 | [Rep Field Cascade Pattern](ADR-0113-rep-field-cascade-pattern.md) | Accepted |
| ADR-0114 | [Hours Model Backward Compatibility Strategy](ADR-0114-hours-backward-compat.md) | Proposed |
| ADR-0115 | [Parallel Section Fetch Strategy](ADR-0115-parallel-section-fetch-strategy.md) | Accepted |
| ADR-0116 | [Batch Cache Population Pattern](ADR-0116-batch-cache-population-pattern.md) | Accepted |
| ADR-0117 | [CustomFieldAccessor/Descriptor Unification Strategy](ADR-0117-accessor-descriptor-unification.md) | Accepted |
| ADR-0118 | [Rejection of Multi-Level Cache Hierarchy](ADR-0118-rejection-multi-level-cache.md) | Accepted |
| ADR-0119 | [Client Cache Integration Pattern](ADR-0119-client-cache-integration-pattern.md) | Accepted |
| ADR-0120 | [Batch Cache Population on Bulk Fetch](ADR-0120-batch-cache-population-on-bulk-fetch.md) | Accepted |
| ADR-0121 | [SaveSession Decomposition Strategy](ADR-0121-savesession-decomposition-strategy.md) | Proposed |
| ADR-0122 | [Action Method Factory Pattern](ADR-0122-action-method-factory-pattern.md) | Proposed |
| ADR-0123 | [Default Cache Provider Selection Strategy](ADR-0123-cache-provider-selection.md) | Proposed |
| ADR-0124 | [Client Cache Integration Pattern](ADR-0124-client-cache-pattern.md) | Proposed |
| ADR-0125 | [SaveSession Cache Invalidation Hook](ADR-0125-savesession-invalidation.md) | Proposed |
| ADR-0126 | [Entity-Type TTL Resolution Strategy](ADR-0126-entity-ttl-resolution.md) | Proposed |
| ADR-0127 | [Cache Graceful Degradation Strategy](ADR-0127-graceful-degradation.md) | Proposed |
| ADR-0128 | [Hydration opt_fields Normalization](ADR-0128-hydration-opt-fields-normalization.md) | Proposed |
| ADR-0129 | [Stories Client Cache Wiring Strategy](ADR-0129-stories-client-cache-wiring.md) | Proposed |
| ADR-0130 | [Cache Population Location Strategy](ADR-0130-cache-population-location.md) | Proposed |
| ADR-0131 | [GID Enumeration Cache Strategy](ADR-0131-gid-enumeration-cache-strategy.md) | Proposed |
| ADR-0132 | [Batch Request Coalescing Strategy](ADR-0132-batch-request-coalescing-strategy.md) | Proposed |
| ADR-0133 | [Progressive TTL Extension Algorithm](ADR-0133-progressive-ttl-extension-algorithm.md) | Proposed |
| ADR-0134 | [Staleness Check Integration Pattern](ADR-0134-staleness-check-integration-pattern.md) | Proposed |
| ADR-0135 | [ProcessHolder Detection Strategy](ADR-0135-processholder-detection.md) | Proposed |
| ADR-0136 | [Process Field Accessor Architecture](ADR-0136-process-field-architecture.md) | Proposed |
| ADR-0137 | [Post-Commit Invalidation Hook for DataFrame Cache](ADR-0137-post-commit-invalidation-hook.md) | Accepted |
| ADR-0138 | [Detection Tier 2 Pattern Matching Enhancement](ADR-0138-tier2-pattern-enhancement.md) | Proposed |
| ADR-0139 | [Self-Healing Opt-In Design](ADR-0139-self-healing-design.md) | Proposed |
| ADR-0140 | [DataFrame Task Cache Integration Strategy](ADR-0140-dataframe-task-cache-integration.md) | Proposed |
| ADR-0141 | [Field Mixin Strategy for Sprint 1 Pattern Completion](ADR-0141-field-mixin-strategy.md) | Proposed |
| ADR-0142 | [Detection Package Structure](ADR-0142-detection-package-structure.md) | Proposed |
| ADR-0143 | [Detection Result Caching Strategy](ADR-0143-detection-result-caching.md) | Proposed |
| ADR-0144 | [HealingResult Type Consolidation](ADR-0144-healingresult-consolidation.md) | Proposed |

### Non-Standard Numbering
| ADR | Title | Status |
|-----|-------|--------|
| ADR-SDK-005 | [Pydantic Settings Standards](ADR-SDK-005-pydantic-settings-standards.md) | Accepted |

---

## Navigation Tips

### Finding ADRs by Topic
Use the [By Theme](#by-theme) section to browse ADRs organized by functional area. Each theme shows ADRs in a logical order.

### Understanding Decision Evolution
Check the [Supersession Chains](#supersession-chains) section to understand how architectural decisions evolved over time. This is especially important for:
- Process Pipeline (ADR-0096 → ADR-0098/0100 → ADR-0101)
- Detection Strategy (ADR-0068 → ADR-0093/0094)
- Cache Architecture (ADR-0017 → ADR-0026)

### Quick Lookup by Number
Use the [By Number](#by-number) section when you know the ADR number or want to browse chronologically.

### Understanding Status
- **Accepted**: Decision is implemented and current
- **Proposed**: Decision is documented but not yet implemented
- **Completed**: Implementation is finished (used for migration ADRs)
- **Superseded**: Decision was replaced by a newer ADR
- **Partially Superseded**: Some portions replaced, others still valid
- **Rejected**: Decision was considered and explicitly rejected (kept for historical record)

---

## Contributing New ADRs

When adding new ADRs:
1. Use the next available number in sequence (currently ADR-0145)
2. Follow the template in existing ADRs
3. Update this INDEX.md:
   - Add to appropriate theme section(s)
   - Add to "By Number" section
   - If it supersedes another ADR, update "Supersession Chains"
   - Consider if it should be in "Start Here" for new contributors

---

**Last Updated**: 2025-12-24
**ADR Count**: 145 (ADR-0001 through ADR-0144, plus ADR-SDK-005)
