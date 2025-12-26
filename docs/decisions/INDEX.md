# Architecture Decision Records

> Consolidated ADRs for the Autom8 Asana SDK. 57 decisions organized by topic.

## Quick Navigation

| Topic | ADRs | Reference |
|-------|------|-----------|
| Demo | 0001-0002 | [reference/DEMO.md](reference/DEMO.md) |
| Observability | 0003-0005 | [reference/OBSERVABILITY.md](reference/OBSERVABILITY.md) |
| Custom Fields | 0006-0009 | [reference/CUSTOM-FIELDS.md](reference/CUSTOM-FIELDS.md) |
| Data Model | 0010-0014 | [reference/DATA-MODEL.md](reference/DATA-MODEL.md) |
| Operations | 0015-0018 | [reference/OPERATIONS.md](reference/OPERATIONS.md) |
| Detection | 0020-0024 | [reference/DETECTION.md](reference/DETECTION.md) |
| Performance | 0025-0028 | [reference/PERFORMANCE.md](reference/PERFORMANCE.md) |
| Architecture | 0029-0033 | [reference/ARCHITECTURE.md](reference/ARCHITECTURE.md) |
| API Integration | 0034-0039 | [reference/API-INTEGRATION.md](reference/API-INTEGRATION.md) |
| SaveSession | 0040-0045 | [reference/SAVESESSION.md](reference/SAVESESSION.md) |
| Cache | 0046-0051 | [reference/CACHE.md](reference/CACHE.md) |
| Patterns | 0052-0057 | [reference/PATTERNS.md](reference/PATTERNS.md) |

## All ADRs (Chronological)

| ADR | Title | Topic |
|-----|-------|-------|
| [ADR-0001](ADR-0001-demo-infrastructure.md) | Demo Infrastructure Design | Demo |
| [ADR-0002](ADR-0002-demo-scope-boundaries.md) | Demo Scope Boundaries | Demo |
| [ADR-0003](ADR-0003-request-correlation-structured-logging.md) | Request Correlation and Structured Logging | Observability |
| [ADR-0004](ADR-0004-observability-hooks-cache-events.md) | Observability Hooks and Cache Events | Observability |
| [ADR-0005](ADR-0005-overflow-detection-metrics.md) | Overflow Detection and Metrics | Observability |
| [ADR-0006](ADR-0006-custom-field-resolution.md) | Custom Field Resolution Strategy | Custom Fields |
| [ADR-0007](ADR-0007-custom-field-accessors-and-descriptors.md) | Custom Field Accessors and Descriptors | Custom Fields |
| [ADR-0008](ADR-0008-custom-field-api-format-and-change-tracking.md) | Custom Field API Format and Change Tracking | Custom Fields |
| [ADR-0009](ADR-0009-cascading-custom-fields.md) | Cascading Custom Fields | Custom Fields |
| [ADR-0010](ADR-0010-pydantic-model-foundation.md) | Pydantic Model Foundation | Data Model |
| [ADR-0011](ADR-0011-entity-identity-tracking.md) | Entity Identity and Tracking | Data Model |
| [ADR-0012](ADR-0012-dataframe-layer-architecture.md) | DataFrame Layer Architecture | Data Model |
| [ADR-0013](ADR-0013-custom-field-type-safety.md) | Custom Field Type Safety | Data Model |
| [ADR-0014](ADR-0014-backward-compatibility-deprecation.md) | Backward Compatibility and Deprecation | Data Model |
| [ADR-0015](ADR-0015-process-pipeline-architecture.md) | Process Pipeline Architecture | Operations |
| [ADR-0016](ADR-0016-business-entity-seeding.md) | Business Entity Seeding and Field Population | Operations |
| [ADR-0017](ADR-0017-automation-architecture.md) | Automation Architecture | Operations |
| [ADR-0018](ADR-0018-deprecation-and-migration.md) | Deprecation and Migration Strategies | Operations |
| [ADR-0020](ADR-0020-entity-type-detection-architecture.md) | Entity Type Detection Architecture | Detection |
| [ADR-0021](ADR-0021-detection-pattern-matching.md) | Detection Pattern Matching Enhancement | Detection |
| [ADR-0022](ADR-0022-self-healing-resolution.md) | Self-Healing Resolution System | Detection |
| [ADR-0023](ADR-0023-detection-package-structure.md) | Detection Package Structure and Caching | Detection |
| [ADR-0024](ADR-0024-name-resolution-dynamic-discovery.md) | Name Resolution and Dynamic Discovery | Detection |
| [ADR-0025](ADR-0025-async-first-concurrency-pattern.md) | Async-First Concurrency Pattern | Performance |
| [ADR-0026](ADR-0026-batching-sequential-execution.md) | Batching and Sequential Execution | Performance |
| [ADR-0027](ADR-0027-incremental-loading-lazy-evaluation.md) | Incremental Loading and Lazy Evaluation | Performance |
| [ADR-0028](ADR-0028-parallelization-request-optimization.md) | Parallelization and Request Optimization | Performance |
| [ADR-0029](ADR-0029-foundation-architecture.md) | Foundation Architecture | Architecture |
| [ADR-0030](ADR-0030-cache-infrastructure.md) | Cache Infrastructure | Architecture |
| [ADR-0031](ADR-0031-registry-and-discovery.md) | Registry and Discovery Architecture | Architecture |
| [ADR-0032](ADR-0032-business-domain-architecture.md) | Business Domain Architecture | Architecture |
| [ADR-0033](ADR-0033-extension-and-integration.md) | Extension and Integration Architecture | Architecture |
| [ADR-0034](ADR-0034-http-transport-integration.md) | HTTP Transport & SDK Integration Strategy | API Integration |
| [ADR-0035](ADR-0035-specialized-protocol-handling.md) | Specialized Protocol Handling (Webhooks & Attachments) | API Integration |
| [ADR-0036](ADR-0036-error-classification-handling.md) | Error Classification & Retryability | API Integration |
| [ADR-0037](ADR-0037-partial-failure-result-patterns.md) | Partial Failure Handling & Result Patterns | API Integration |
| [ADR-0038](ADR-0038-resilience-graceful-degradation.md) | Resilience & Graceful Degradation | API Integration |
| [ADR-0039](ADR-0039-api-design-surface-control.md) | API Design & Surface Control | API Integration |
| [ADR-0040](ADR-0040-savesession-unit-of-work.md) | SaveSession Unit of Work Pattern & Change Tracking | SaveSession |
| [ADR-0041](ADR-0041-savesession-dependencies-concurrency.md) | SaveSession Dependency Ordering & Concurrency Model | SaveSession |
| [ADR-0042](ADR-0042-savesession-error-handling.md) | SaveSession Error Handling & Partial Failures | SaveSession |
| [ADR-0043](ADR-0043-savesession-action-operations.md) | SaveSession Action Operations Architecture | SaveSession |
| [ADR-0044](ADR-0044-savesession-lifecycle-integration.md) | SaveSession Lifecycle & System Integration | SaveSession |
| [ADR-0045](ADR-0045-savesession-decomposition.md) | SaveSession Decomposition & Optimization | SaveSession |
| [ADR-0046](ADR-0046-cache-protocol-extension.md) | Cache Protocol Extension | Cache |
| [ADR-0047](ADR-0047-two-tier-cache-architecture.md) | Two-Tier Cache Architecture (Redis + S3) | Cache |
| [ADR-0048](ADR-0048-staleness-detection-progressive-ttl.md) | Staleness Detection with Progressive TTL Extension | Cache |
| [ADR-0049](ADR-0049-batch-operations-gid-enumeration.md) | Batch Operations and GID Enumeration Caching | Cache |
| [ADR-0050](ADR-0050-entity-aware-ttl-management.md) | Entity-Aware TTL Management | Cache |
| [ADR-0051](ADR-0051-cache-invalidation-hooks.md) | Cache Invalidation Hooks | Cache |
| [ADR-0052](ADR-0052-protocol-extensibility.md) | Protocol-Based Extensibility | Patterns |
| [ADR-0053](ADR-0053-descriptor-patterns.md) | Descriptor Patterns for Domain Layer | Patterns |
| [ADR-0054](ADR-0054-factory-patterns.md) | Factory Patterns for Complex Creation | Patterns |
| [ADR-0055](ADR-0055-state-discovery-patterns.md) | State and Discovery Patterns | Patterns |
| [ADR-0056](ADR-0056-integration-patterns.md) | Integration Patterns for Cross-Layer Orchestration | Patterns |
| [ADR-0057](ADR-0057-resilience-hook-patterns.md) | Resilience and Hook Patterns | Patterns |

## For New Contributors

Start with these 5 foundational decisions:
1. **[ADR-0029](ADR-0029-foundation-architecture.md)**: Foundation Architecture
2. **[ADR-0040](ADR-0040-savesession-unit-of-work.md)**: SaveSession Unit of Work
3. **[ADR-0046](ADR-0046-cache-protocol-extension.md)**: Cache Protocol Extension
4. **[ADR-0052](ADR-0052-protocol-extensibility.md)**: Protocol-Based Extensibility
5. **[ADR-0020](ADR-0020-entity-type-detection-architecture.md)**: Entity Type Detection

These five ADRs cover the core architectural patterns that shape the entire system.

## Understanding the Structure

### Topic-Based Organization

Each topic has:
- **Reference document** (`reference/*.md`): High-level overview with decision narrative and evolution timeline
- **Individual ADRs**: Detailed decisions with context, rationale, alternatives considered, and consequences

**When to use which:**
- Start with reference documents for topic overview and decision evolution
- Use individual ADRs when you need implementation details, alternatives analysis, or compliance requirements

### Reference Documents

The 12 reference documents provide narrative summaries organized by functional area:

1. **[DEMO](reference/DEMO.md)** - Demo infrastructure, state management, name resolution
2. **[OBSERVABILITY](reference/OBSERVABILITY.md)** - Logging, monitoring, correlation IDs, telemetry
3. **[CUSTOM-FIELDS](reference/CUSTOM-FIELDS.md)** - Field resolution, accessors, descriptors, cascading
4. **[DATA-MODEL](reference/DATA-MODEL.md)** - Pydantic models, entity identity, typing, backwards compatibility
5. **[OPERATIONS](reference/OPERATIONS.md)** - Process pipelines, automation, business logic
6. **[DETECTION](reference/DETECTION.md)** - Type detection, pattern matching, self-healing, name resolution
7. **[PERFORMANCE](reference/PERFORMANCE.md)** - Async patterns, batching, lazy loading, parallelization
8. **[ARCHITECTURE](reference/ARCHITECTURE.md)** - Foundation, cache infrastructure, registry, domain architecture
9. **[API-INTEGRATION](reference/API-INTEGRATION.md)** - HTTP transport, error handling, resilience, API design
10. **[SAVESESSION](reference/SAVESESSION.md)** - Unit of work pattern, dependencies, actions, lifecycle
11. **[CACHE](reference/CACHE.md)** - Protocol extension, two-tier architecture, TTL, invalidation
12. **[PATTERNS](reference/PATTERNS.md)** - Protocols, descriptors, factories, state discovery, hooks

## Historical Archive

Individual ADRs from the initial development phase (ADR-0001 through ADR-0144, plus ADR-SDK-005) are preserved in `docs/.archive/2025-12-adrs/` with full git history.

**Archive structure:**
- Original ADR content and formatting preserved
- Complete git history via `git mv` operations
- Supersession relationships documented
- Context for architectural evolution over time

See [Archive INDEX](../.archive/2025-12-adrs/INDEX.md) for mapping between historical ADRs and consolidated versions.

**Consolidation process:**
- 145 individual ADRs consolidated into 57 decisions (Dec 2025)
- Related decisions merged where they addressed the same concern
- All historical context preserved in consolidated metadata
- Archive maintained for historical reference and detailed analysis

---

**Last Updated**: 2025-12-25
**Current ADRs**: 57 consolidated decisions (ADR-0001 through ADR-0057)
**Reference Documents**: 12 topic-based summaries
**Archive**: 145 historical ADRs preserved with full git history
