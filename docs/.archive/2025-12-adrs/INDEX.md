# Archived ADRs (Pre-Consolidation)

Original 145 ADRs from initial development, consolidated December 2025.

## About This Archive

These ADRs represent the decision history from the initial SDK development phase. 
They have been synthesized into 57 consolidated ADRs for improved navigation while 
preserving the historical record.

**Active decisions**: See `/Users/tomtenuta/Code/autom8_asana/docs/decisions/` for current consolidated ADRs  
**Reference docs**: See `/Users/tomtenuta/Code/autom8_asana/docs/decisions/reference/` for topic overviews

## Consolidation Mapping

This table shows which original ADRs have been consolidated into which new ADRs.

| Original ADR | Title | Consolidated Into |
|--------------|-------|-------------------|
| ADR-0001 | Protocol-Based Extensibility for Dependency Injection | ADR-0029-foundation-architecture |
| ADR-0002 | Fail-Fast Strategy for Sync Wrappers in Async Contexts | ADR-0025-async-first-concurrency-pattern |
| ADR-0003 | Replace Asana SDK HTTP Layer, Retain Types and Error Parsing | ADR-0029-foundation-architecture, ADR-0034-http-transport-integration |
| ADR-0004 | Minimal AsanaResource in SDK, Full Item Stays in Monolith | ADR-0029-foundation-architecture |
| ADR-0005 | Pydantic v2 with `extra="ignore"` for Forward Compatibility | ADR-0010-pydantic-model-foundation |
| ADR-0006 | NameGid as Standalone Frozen Model | ADR-0011-entity-identity-tracking |
| ADR-0007 | Consistent Client Pattern Across Resource Types | ADR-0034-http-transport-integration, ADR-0052-protocol-extensibility |
| ADR-0008 | Webhook Signature Verification Strategy | ADR-0035-specialized-protocol-handling |
| ADR-0009 | Attachment Multipart/Form-Data Handling | ADR-0035-specialized-protocol-handling |
| ADR-0010 | Sequential Chunk Execution for Batch Operations | ADR-0026-batching-sequential-execution |
| ADR-0011 | Deprecation Warning Strategy for Compatibility Layer | ADR-0018-deprecation-and-migration |
| ADR-0012 | Public API Surface Definition | ADR-0029-foundation-architecture, ADR-0039-api-design-surface-control |
| ADR-0013 | Correlation ID Strategy for SDK Observability | ADR-0003-request-correlation-structured-logging, ADR-0034-http-transport-integration |
| ADR-0014 | Environment Variable Configuration for Example Scripts | *(not consolidated)* |
| ADR-0015 (ADR-0011) | Batch API Request Format Fix | ADR-0026-batching-sequential-execution, ADR-0035-specialized-protocol-handling |
| ADR-0016 | Cache Protocol Extension | ADR-0046-cache-protocol-extension, ADR-0052-protocol-extensibility |
| ADR-0017 | Redis Backend Architecture | ADR-0030-cache-infrastructure |
| ADR-0018 | Batch Modification Checking | *(not consolidated)* |
| ADR-0019 | Staleness Detection Algorithm | ADR-0048-staleness-detection-progressive-ttl |
| ADR-0020 | Incremental Story Loading | ADR-0027-incremental-loading-lazy-evaluation |
| ADR-0021 | Dataframe Caching Strategy | *(not consolidated)* |
| ADR-0022 | Overflow Management | ADR-0005-overflow-detection-metrics |
| ADR-0023 | Observability Strategy | ADR-0004-observability-hooks-cache-events |
| ADR-0024 | Thread-Safety Guarantees | ADR-0030-cache-infrastructure |
| ADR-0025 | Big-Bang Migration Strategy | ADR-0018-deprecation-and-migration |
| ADR-0026 | Two-Tier Cache Architecture (Redis + S3) | ADR-0030-cache-infrastructure, ADR-0047-two-tier-cache-architecture |
| ADR-0027 | Dataframe Layer Migration Strategy | ADR-0018-deprecation-and-migration |
| ADR-0028 | Polars DataFrame Library | ADR-0012-dataframe-layer-architecture |
| ADR-0029 | Task Subclass Strategy | ADR-0012-dataframe-layer-architecture |
| ADR-0030 | Custom Field Typing | ADR-0006-custom-field-resolution, ADR-0013-custom-field-type-safety |
| ADR-0031 | Lazy vs Eager Evaluation | ADR-0027-incremental-loading-lazy-evaluation |
| ADR-0032 | Cache Granularity | *(not consolidated)* |
| ADR-0033 | Schema Enforcement | ADR-0012-dataframe-layer-architecture |
| ADR-0034 | Dynamic Custom Field Resolution Strategy | ADR-0006-custom-field-resolution, ADR-0024-name-resolution-dynamic-discovery |
| ADR-0035 | Unit of Work Pattern for Save Orchestration | ADR-0040-savesession-unit-of-work |
| ADR-0036 | Change Tracking via Snapshot Comparison | ADR-0040-savesession-unit-of-work |
| ADR-0037 | Kahn's Algorithm for Dependency Ordering | ADR-0041-savesession-dependencies-concurrency |
| ADR-0038 | Async-First Concurrency for Save Operations | ADR-0025-async-first-concurrency-pattern, ADR-0041-savesession-dependencies-concurrency |
| ADR-0039 | Fixed-Size Sequential Batch Execution | ADR-0026-batching-sequential-execution |
| ADR-0040 | Commit and Report on Partial Failure | ADR-0037-partial-failure-result-patterns, ADR-0042-savesession-error-handling |
| ADR-0041 | Synchronous Event Hooks with Async Support | ADR-0057-resilience-hook-patterns |
| ADR-0042 | Separate ActionType Enum for Action Endpoint Operations | ADR-0043-savesession-action-operations |
| ADR-0043 | Validation-Phase Detection for Unsupported Direct Modifications | *(not consolidated)* |
| ADR-0044 | extra_params Field Design for ActionOperation | ADR-0043-savesession-action-operations |
| ADR-0045 | Like Operations Without Target GID | ADR-0043-savesession-action-operations |
| ADR-0046 | Comment Text Storage Strategy | ADR-0037-partial-failure-result-patterns |
| ADR-0047 | Positioning Validation Timing | ADR-0037-partial-failure-result-patterns |
| ADR-0048 | Circuit Breaker Pattern for Transport Layer | ADR-0038-resilience-graceful-degradation, ADR-0057-resilience-hook-patterns |
| ADR-0049 | GID Validation Strategy | ADR-0011-entity-identity-tracking |
| ADR-0050 | Holder Lazy Loading Strategy | ADR-0056-integration-patterns |
| ADR-0051 | Custom Field Type Safety | ADR-0007-custom-field-accessors-and-descriptors, ADR-0013-custom-field-type-safety |
| ADR-0052 | Bidirectional Reference Caching | *(not consolidated)* |
| ADR-0053 | Composite SaveSession Support | ADR-0044-savesession-lifecycle-integration |
| ADR-0054 | Cascading Custom Fields Strategy | ADR-0009-cascading-custom-fields |
| ADR-0055 | Action Result Integration into SaveResult | ADR-0043-savesession-action-operations |
| ADR-0056 | Custom Field API Format Conversion | ADR-0008-custom-field-api-format-and-change-tracking |
| ADR-0057 | Add subtasks_async Method to TasksClient | ADR-0028-parallelization-request-optimization |
| ADR-0058 | BUG-4 Demo GID Display Out of Scope | ADR-0002-demo-scope-boundaries |
| ADR-0059 | Direct Methods vs. SaveSession Actions | ADR-0043-savesession-action-operations |
| ADR-0060 | Name Resolution Caching Strategy | *(not consolidated)* |
| ADR-0061 | Implicit SaveSession Lifecycle | ADR-0044-savesession-lifecycle-integration |
| ADR-0062 | CustomFieldAccessor Enhancement vs. Wrapper | ADR-0007-custom-field-accessors-and-descriptors |
| ADR-0063 | Client Reference Storage | ADR-0034-http-transport-integration |
| ADR-0064 | Dirty Detection Strategy | ADR-0044-savesession-lifecycle-integration |
| ADR-0065 | SaveSessionError Exception for P1 Methods | ADR-0036-error-classification-handling, ADR-0042-savesession-error-handling |
| ADR-0066 | Selective Action Clearing Strategy | ADR-0042-savesession-error-handling |
| ADR-0067 | Custom Field Snapshot Detection Strategy | ADR-0008-custom-field-api-format-and-change-tracking |
| ADR-0068 | Type Detection Strategy for Upward Traversal | ADR-0020-entity-type-detection-architecture |
| ADR-0069 | Hydration API Design | ADR-0039-api-design-surface-control |
| ADR-0070 | Hydration Partial Failure Handling | ADR-0037-partial-failure-result-patterns |
| ADR-0071 | Resolution Ambiguity Handling | ADR-0024-name-resolution-dynamic-discovery |
| ADR-0072 | Resolution Caching Decision | *(not consolidated)* |
| ADR-0073 | Batch Resolution API Design | ADR-0028-parallelization-request-optimization, ADR-0039-api-design-surface-control |
| ADR-0074 | Unified Custom Field Tracking via CustomFieldAccessor | ADR-0008-custom-field-api-format-and-change-tracking |
| ADR-0075 | Navigation Descriptor Pattern | ADR-0053-descriptor-patterns |
| ADR-0076 | Auto-Invalidation Strategy | *(not consolidated)* |
| ADR-0077 | Pydantic v2 Descriptor Compatibility | ADR-0053-descriptor-patterns |
| ADR-0078 | GID-Based Entity Identity Strategy | ADR-0011-entity-identity-tracking |
| ADR-0079 | Retryable Error Classification | ADR-0036-error-classification-handling |
| ADR-0080 | Entity Registry Scope | ADR-0031-registry-and-discovery |
| ADR-0081 | Custom Field Descriptor Pattern | ADR-0007-custom-field-accessors-and-descriptors, ADR-0053-descriptor-patterns |
| ADR-0082 | Fields Class Auto-Generation Strategy | ADR-0013-custom-field-type-safety |
| ADR-0083 | DateField Arrow Integration | ADR-0013-custom-field-type-safety |
| ADR-0084 (ADR-HARDENING-A-001) | Exception Rename Strategy | ADR-0018-deprecation-and-migration, ADR-0036-error-classification-handling |
| ADR-0085 (ADR-HARDENING-A-002) | ObservabilityHook Protocol Design | ADR-0004-observability-hooks-cache-events, ADR-0052-protocol-extensibility |
| ADR-0086 (ADR-HARDENING-A-003) | Logging Standardization | ADR-0003-request-correlation-structured-logging |
| ADR-0087 (ADR-HARDENING-A-004) | Minimal Stub Model Pattern | ADR-0056-integration-patterns |
| ADR-0088 (ADR-DEMO-001) | State Capture Strategy for Demo Restoration | ADR-0001-demo-infrastructure |
| ADR-0089 (ADR-DEMO-002) | Name Resolution Approach for Demo Scripts | ADR-0001-demo-infrastructure, ADR-0024-name-resolution-dynamic-discovery |
| ADR-0090 (ADR-DEMO-003) | Error Handling Strategy for Demo Scripts | ADR-0001-demo-infrastructure, ADR-0038-resilience-graceful-degradation |
| ADR-0091 (ADR-DESIGN-B-001) | RetryableErrorMixin for Error Classification | ADR-0036-error-classification-handling, ADR-0057-resilience-hook-patterns |
| ADR-0092 (ADR-DESIGN-E-001) | CRUD Client Base Class Evaluation | *(not consolidated)* |
| ADR-0093 | Project-to-EntityType Registry Pattern | ADR-0015-process-pipeline-architecture, ADR-0055-state-discovery-patterns |
| ADR-0094 | Detection Fallback Chain Design | ADR-0020-entity-type-detection-architecture |
| ADR-0095 | Self-Healing Integration with SaveSession | ADR-0022-self-healing-resolution |
| ADR-0096 | ProcessType Expansion and Detection | ADR-0015-process-pipeline-architecture |
| ADR-0097 | ProcessSection State Machine Pattern | ADR-0015-process-pipeline-architecture, ADR-0055-state-discovery-patterns |
| ADR-0098 | Dual Membership Model | ADR-0012-dataframe-layer-architecture |
| ADR-0099 | BusinessSeeder Factory Pattern | ADR-0016-business-entity-seeding, ADR-0054-factory-patterns |
| ADR-0100 | State Transition Composition with SaveSession | ADR-0044-savesession-lifecycle-integration, ADR-0055-state-discovery-patterns |
| ADR-0101 | Process Pipeline Architecture Correction | ADR-0015-process-pipeline-architecture, ADR-0032-business-domain-architecture |
| ADR-0102 | Post-Commit Hook Architecture | ADR-0017-automation-architecture, ADR-0033-extension-and-integration |
| ADR-0103 | Automation Rule Protocol | ADR-0017-automation-architecture, ADR-0052-protocol-extensibility |
| ADR-0104 | Loop Prevention Strategy | ADR-0044-savesession-lifecycle-integration |
| ADR-0105 | Field Seeding Architecture | ADR-0016-business-entity-seeding, ADR-0032-business-domain-architecture |
| ADR-0106 | Template Discovery Pattern | ADR-0024-name-resolution-dynamic-discovery, ADR-0055-state-discovery-patterns |
| ADR-0107 | NameGid for ActionOperation Targets | ADR-0044-savesession-lifecycle-integration |
| ADR-0108 | WorkspaceProjectRegistry Architecture | ADR-0031-registry-and-discovery |
| ADR-0109 | Lazy Discovery Timing for WorkspaceProjectRegistry | ADR-0024-name-resolution-dynamic-discovery |
| ADR-0110 | Task Duplication vs Creation Strategy | ADR-0044-savesession-lifecycle-integration |
| ADR-0111 | Subtask Wait Strategy | ADR-0044-savesession-lifecycle-integration |
| ADR-0112 | Custom Field GID Resolution Pattern | ADR-0006-custom-field-resolution, ADR-0024-name-resolution-dynamic-discovery |
| ADR-0113 | Rep Field Cascade Pattern | ADR-0009-cascading-custom-fields, ADR-0055-state-discovery-patterns |
| ADR-0114 | Hours Model Backward Compatibility Strategy | ADR-0014-backward-compatibility-deprecation, ADR-0018-deprecation-and-migration |
| ADR-0115 | Parallel Section Fetch Strategy | ADR-0028-parallelization-request-optimization |
| ADR-0116 | Batch Cache Population Pattern | ADR-0049-batch-operations-gid-enumeration, ADR-0056-integration-patterns |
| ADR-0117 | CustomFieldAccessor/Descriptor Unification Strategy | ADR-0007-custom-field-accessors-and-descriptors, ADR-0053-descriptor-patterns |
| ADR-0118 | Rejection of Multi-Level Cache Hierarchy | *(not consolidated)* |
| ADR-0119 | Client Cache Integration Pattern | ADR-0056-integration-patterns |
| ADR-0120 | Batch Cache Population on Bulk Fetch | *(not consolidated)* |
| ADR-0121 | SaveSession Decomposition Strategy | ADR-0045-savesession-decomposition |
| ADR-0122 | Action Method Factory Pattern | ADR-0045-savesession-decomposition, ADR-0054-factory-patterns |
| ADR-0123 | Default Cache Provider Selection Strategy | *(not consolidated)* |
| ADR-0124 | Client Cache Integration Pattern | ADR-0051-cache-invalidation-hooks, ADR-0056-integration-patterns |
| ADR-0125 | SaveSession Cache Invalidation Hook | ADR-0044-savesession-lifecycle-integration, ADR-0051-cache-invalidation-hooks |
| ADR-0126 | Entity-Type TTL Resolution Strategy | ADR-0050-entity-aware-ttl-management |
| ADR-0127 | Cache Graceful Degradation Strategy | ADR-0038-resilience-graceful-degradation |
| ADR-0128 | Hydration opt_fields Normalization | ADR-0039-api-design-surface-control |
| ADR-0129 | Stories Client Cache Wiring Strategy | *(not consolidated)* |
| ADR-0130 | Cache Population Location Strategy | *(not consolidated)* |
| ADR-0131 | GID Enumeration Cache Strategy | ADR-0049-batch-operations-gid-enumeration |
| ADR-0132 | Batch Request Coalescing Strategy | ADR-0028-parallelization-request-optimization |
| ADR-0133 | Progressive TTL Extension Algorithm | ADR-0048-staleness-detection-progressive-ttl |
| ADR-0134 | Staleness Check Integration Pattern | ADR-0056-integration-patterns |
| ADR-0135 | ProcessHolder Detection Strategy | ADR-0015-process-pipeline-architecture, ADR-0020-entity-type-detection-architecture |
| ADR-0136 | Process Field Accessor Architecture | ADR-0015-process-pipeline-architecture, ADR-0032-business-domain-architecture |
| ADR-0137 | Post-Commit Invalidation Hook for DataFrame Cache | ADR-0051-cache-invalidation-hooks |
| ADR-0138 | Detection Tier 2 Pattern Matching Enhancement | ADR-0021-detection-pattern-matching, ADR-0055-state-discovery-patterns |
| ADR-0139 | Self-Healing Opt-In Design | ADR-0022-self-healing-resolution |
| ADR-0140 | DataFrame Task Cache Integration Strategy | *(not consolidated)* |
| ADR-0141 | Field Mixin Strategy for Sprint 1 Pattern Completion | ADR-0053-descriptor-patterns |
| ADR-0142 | Detection Package Structure | ADR-0023-detection-package-structure, ADR-0031-registry-and-discovery |
| ADR-0143 | Detection Result Caching Strategy | ADR-0023-detection-package-structure |
| ADR-0144 | HealingResult Type Consolidation | ADR-0022-self-healing-resolution |
| ADR-SDK-005 | Pydantic Settings Standards | *(not consolidated)* |

## ADRs by Consolidation Status

### Consolidated (128 ADRs)
ADRs that have been merged into consolidated decision documents.

### Not Consolidated (17 ADRs)
ADRs that were not included in the consolidation:
- ADR-0014: Environment Variable Configuration for Example Scripts
- ADR-0018: Batch Modification Checking
- ADR-0021: Dataframe Caching Strategy
- ADR-0032: Cache Granularity
- ADR-0043: Validation-Phase Detection for Unsupported Direct Modifications
- ADR-0052: Bidirectional Reference Caching
- ADR-0060: Name Resolution Caching Strategy
- ADR-0072: Resolution Caching Decision
- ADR-0076: Auto-Invalidation Strategy
- ADR-0092 (ADR-DESIGN-E-001): CRUD Client Base Class Evaluation
- ADR-0118: Rejection of Multi-Level Cache Hierarchy
- ADR-0120: Batch Cache Population on Bulk Fetch
- ADR-0123: Default Cache Provider Selection Strategy
- ADR-0129: Stories Client Cache Wiring Strategy
- ADR-0130: Cache Population Location Strategy
- ADR-0140: DataFrame Task Cache Integration Strategy
- ADR-SDK-005: Pydantic Settings Standards

## Navigation

- **By topic**: See `/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-INDEX-BY-TOPIC.md`
- **Summary docs**: See `/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-SUMMARY-*.md`
- **Reference guides**: See `/Users/tomtenuta/Code/autom8_asana/docs/decisions/reference/`

## Archive Organization

All archived ADRs are preserved in this directory with their original structure and content. 
The consolidation process created new, synthesized ADRs that incorporate the substance of these 
decisions while eliminating redundancy and improving discoverability.

### Why Consolidate?

The original 145 ADRs had several issues:
- **Fragmentation**: Related decisions scattered across multiple files
- **Duplication**: Same concepts documented in multiple places
- **Granularity**: Some decisions too fine-grained for effective reference
- **Navigation**: Difficult to find the authoritative source for a topic

The consolidated ADRs address these issues while preserving the historical record in this archive.

### How to Use This Archive

1. **For current decisions**: Consult the consolidated ADRs in `/Users/tomtenuta/Code/autom8_asana/docs/decisions/`
2. **For historical context**: Use this archive to understand the evolution of specific decisions
3. **For detailed rationale**: Original ADRs may contain context not preserved in consolidation
4. **For completeness**: When validating implementation, cross-reference both consolidated and archived versions

---

*Archive created: December 2025*  
*Consolidation methodology: See ADR-CONSOLIDATION-PLAN.md in this directory*
