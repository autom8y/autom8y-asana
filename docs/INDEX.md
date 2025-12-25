# Documentation Index

> Central registry of all project documentation.
> **Last Updated**: 2025-12-24

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **What is this SDK?** | [PRD-0001](requirements/PRD-0001-sdk-extraction.md) |
| **How is it architected?** | [TDD-0001](design/TDD-0001-sdk-architecture.md) |
| **Why did we decide X?** | [ADRs](decisions/) |
| **How do I use it?** | [Guides](guides/) |
| **Reference data** | [Reference](reference/) |

---

## PRDs (Requirements)

| ID | Title | Status |
|----|-------|--------|
| [PRD-0001](requirements/PRD-0001-sdk-extraction.md) | SDK Extraction from Monolith | Approved |
| ~~PRD-0002~~ | Intelligent Caching Layer | Archived → [REF-cache-architecture](reference/REF-cache-architecture.md) |
| [PRD-0003](requirements/PRD-0003-structured-dataframe-layer.md) | Structured Dataframe Layer | In Review |
| [PRD-0003.1](requirements/PRD-0003.1-dynamic-custom-field-resolution.md) | Dynamic Custom Field Resolution | Draft |
| [PRD-0004](requirements/PRD-0004-test-hang-fix.md) | Test Suite Hang Prevention | Implemented |
| [PRD-0005](requirements/PRD-0005-save-orchestration.md) | Save Orchestration Layer | Implemented |
| [PRD-0006](requirements/PRD-0006-action-endpoint-support.md) | Action Endpoint Support | Draft |
| [PRD-0007](requirements/PRD-0007-sdk-functional-parity.md) | SDK Functional Parity | Implemented |
| [PRD-0008](requirements/PRD-0008-parent-subtask-operations.md) | Parent & Subtask Operations | Implemented |
| [PRD-0009](requirements/PRD-0009-sdk-ga-readiness.md) | SDK GA Readiness | Draft |
| [PRD-0010](requirements/PRD-0010-business-model-layer.md) | Business Model Layer | Draft |
| [PRD-0011](requirements/PRD-0011-sdk-demonstration-suite.md) | SDK Demonstration Suite | Draft |
| [PRD-0012](requirements/PRD-0012-sdk-usability-improvements.md) | SDK Usability Improvements | Approved |
| [PRD-0013](requirements/PRD-0013-hierarchy-hydration.md) | Hierarchy Hydration | Implemented |
| [PRD-0014](requirements/PRD-0014-cross-holder-resolution.md) | Cross-Holder Resolution | Implemented |
| [PRD-0015](requirements/PRD-0015-foundation-hardening.md) | Foundation Hardening | Draft |
| [PRD-0016](requirements/PRD-0016-custom-field-tracking.md) | Custom Field Tracking | Draft |
| [PRD-0017](requirements/PRD-0017-navigation-descriptors.md) | Navigation Descriptors | Draft |
| [PRD-0018](requirements/PRD-0018-savesession-reliability.md) | SaveSession Reliability | Draft |
| [PRD-0019](requirements/PRD-0019-custom-field-descriptors.md) | Custom Field Descriptors | Draft |
| [PRD-0020](requirements/PRD-0020-holder-factory.md) | Holder Factory | Implemented |
| ~~PRD-0021~~ | Async Method Generator | Archived → [archive/rejected](archive/rejected/) |
| ~~PRD-0022~~ | CRUD Base Class | Archived → [archive/rejected](archive/rejected/) |
| [PRD-0023](requirements/PRD-0023-qa-triage-fixes.md) | QA Triage Fixes | Ready |
| [PRD-0024](requirements/PRD-0024-custom-field-remediation.md) | Custom Field Reality Remediation | Draft |
| [PRD-DOCS-EPOCH-RESET](requirements/PRD-DOCS-EPOCH-RESET.md) | Documentation Epoch Reset | Active |
| [PRD-PROCESS-PIPELINE](requirements/PRD-PROCESS-PIPELINE.md) | Process Pipeline (types, states, seeding) | Superseded |
| [PRD-PROCESS-PIPELINE-AMENDMENT](requirements/PRD-PROCESS-PIPELINE-AMENDMENT.md) | Process Pipeline Architectural Correction | Draft |
| [PRD-AUTOMATION-LAYER](requirements/PRD-AUTOMATION-LAYER.md) | Automation Layer for Pipeline Conversion | Draft |
| [PRD-DETECTION](requirements/PRD-DETECTION.md) | Membership-Based Entity Type Detection | Implemented |
| [PRD-WORKSPACE-PROJECT-REGISTRY](requirements/PRD-WORKSPACE-PROJECT-REGISTRY.md) | Workspace Project Registry for Dynamic Discovery | Implemented |
| [PRD-PIPELINE-AUTOMATION-ENHANCEMENT](requirements/PRD-PIPELINE-AUTOMATION-ENHANCEMENT.md) | Pipeline Automation Enhancement - Legacy Parity | Draft |
| **Cache PRDs** | *Consolidated into Reference Docs* | Archived |

> **Note**: 9 cache PRDs archived to `archive/2025-12-cache-superseded/prds/`. See consolidated docs:
> - [REF-cache-architecture](reference/REF-cache-architecture.md) - Core cache design
> - [REF-cache-invalidation](reference/REF-cache-invalidation.md) - Staleness and TTL
> - [REF-cache-patterns](reference/REF-cache-patterns.md) - Performance patterns

---

## TDDs (Design)

| ID | Title | PRD | Status |
|----|-------|-----|--------|
| [TDD-0001](design/TDD-0001-sdk-architecture.md) | SDK Architecture | PRD-0001 | Draft |
| [TDD-0002](design/TDD-0002-models-pagination.md) | Models and Pagination | PRD-0001 | Draft |
| [TDD-0003](design/TDD-0003-tier1-clients.md) | Tier 1 Resource Clients | PRD-0001 | Draft |
| [TDD-0004](design/TDD-0004-tier2-clients.md) | Tier 2 Resource Clients | PRD-0001 | Draft |
| [TDD-0005](design/TDD-0005-batch-api.md) | Batch API | PRD-0001 | Draft |
| [TDD-0006](design/TDD-0006-backward-compatibility.md) | Backward Compatibility | PRD-0001 | Draft |
| [TDD-0007](design/TDD-0007-observability.md) | Observability | PRD-0001 | Draft |
| ~~TDD-0008~~ | Intelligent Caching | PRD-0002 | Archived → [REF-cache-architecture](reference/REF-cache-architecture.md) |
| [TDD-0009](design/TDD-0009-structured-dataframe-layer.md) | Dataframe Layer | PRD-0003 | Draft |
| [TDD-0009.1](design/TDD-0009.1-dynamic-custom-field-resolution.md) | Custom Field Resolution | PRD-0003.1 | Draft |
| [TDD-0010](design/TDD-0010-save-orchestration.md) | Save Orchestration | PRD-0005 | Draft |
| [TDD-0011](design/TDD-0011-action-endpoint-support.md) | Action Endpoints | PRD-0006 | Draft |
| [TDD-0012](design/TDD-0012-sdk-functional-parity.md) | SDK Functional Parity | PRD-0007 | Implemented |
| [TDD-0013](design/TDD-0013-parent-subtask-operations.md) | Parent & Subtask Ops | PRD-0008 | Implemented |
| [TDD-0014](design/TDD-0014-sdk-ga-readiness.md) | SDK GA Readiness | PRD-0009 | Draft |
| [TDD-0015](design/TDD-0015-sdk-usability.md) | SDK Usability | PRD-0012 | Ready |
| [TDD-0016](design/TDD-0016-cascade-and-fixes.md) | Cascade and Fixes | PRD-0023 | Draft |
| [TDD-0017](design/TDD-0017-hierarchy-hydration.md) | Hierarchy Hydration | PRD-0013 | Implemented |
| [TDD-0018](design/TDD-0018-cross-holder-resolution.md) | Cross-Holder Resolution | PRD-0014 | Implemented |
| [TDD-0019](design/TDD-0019-foundation-hardening.md) | Foundation Hardening | PRD-0015 | Draft |
| [TDD-0020](design/TDD-0020-custom-field-tracking.md) | Custom Field Tracking | PRD-0016 | Draft |
| [TDD-0021](design/TDD-0021-navigation-descriptors.md) | Navigation Descriptors | PRD-0017 | Draft |
| [TDD-0022](design/TDD-0022-savesession-reliability.md) | SaveSession Reliability | PRD-0018 | Draft |
| [TDD-0023](design/TDD-0023-custom-field-descriptors.md) | Custom Field Descriptors | PRD-0019 | Draft |
| [TDD-0024](design/TDD-0024-holder-factory.md) | Holder Factory | PRD-0020 | Implemented |
| [TDD-0025](design/TDD-0025-async-method-decorator.md) | Async Method Decorator | PRD-0021 | Superseded |
| ~~TDD-0026~~ | CRUD Base Class (NO-GO) | PRD-0022 | Archived → [archive/rejected](archive/rejected/) |
| [TDD-0027](design/TDD-0027-business-model-architecture.md) | Business Model Architecture | PRD-0010 | Draft |
| [TDD-0028](design/TDD-0028-business-model-implementation.md) | Business Model Implementation | PRD-0010 | Draft |
| [TDD-0029](design/TDD-0029-sdk-demo.md) | SDK Demo | PRD-0011 | Draft |
| [TDD-DOCS-EPOCH-RESET](design/TDD-DOCS-EPOCH-RESET.md) | Documentation Epoch Reset | PRD-DOCS-EPOCH-RESET | Active |
| [TDD-PROCESS-PIPELINE](design/TDD-PROCESS-PIPELINE.md) | Process Pipeline | PRD-PROCESS-PIPELINE | Superseded |
| [TDD-AUTOMATION-LAYER](design/TDD-AUTOMATION-LAYER.md) | Automation Layer | PRD-AUTOMATION-LAYER | Draft |
| [TDD-DETECTION](design/TDD-DETECTION.md) | Entity Detection System | PRD-DETECTION | Implemented |
| [TDD-WORKSPACE-PROJECT-REGISTRY](design/TDD-WORKSPACE-PROJECT-REGISTRY.md) | Workspace Project Registry | PRD-WORKSPACE-PROJECT-REGISTRY | Implemented |
| [TDD-PIPELINE-AUTOMATION-ENHANCEMENT](design/TDD-PIPELINE-AUTOMATION-ENHANCEMENT.md) | Pipeline Automation Enhancement | PRD-PIPELINE-AUTOMATION-ENHANCEMENT | Draft |
| [TDD-0030](design/TDD-CUSTOM-FIELD-REMEDIATION.md) | Custom Field Reality Remediation | PRD-0024 | Draft |
| **Cache TDDs** | *Consolidated into Reference Docs* | - | Archived |

> **Note**: 11 cache TDDs archived to `archive/2025-12-cache-superseded/tdds/`. See consolidated docs:
> - [REF-cache-architecture](reference/REF-cache-architecture.md) - Core cache design
> - [REF-cache-invalidation](reference/REF-cache-invalidation.md) - Staleness and TTL
> - [REF-cache-patterns](reference/REF-cache-patterns.md) - Performance patterns

**Note on TDD-0030**: This TDD uses filename `TDD-CUSTOM-FIELD-REMEDIATION.md` (named format) while being allocated sequential number 0030. This follows the hybrid convention where documents can have both a sequential ID for INDEX ordering and a descriptive filename for discoverability. See [CONVENTIONS.md](CONVENTIONS.md#when-to-use-numbered-vs-named-format) for naming guidance.

---

## ADRs (Decisions)

135 Architecture Decision Records: [ADR-0001](decisions/ADR-0001-protocol-extensibility.md) through [ADR-0134](decisions/ADR-0134-staleness-check-integration-pattern.md)

### Key ADRs by Topic

| Topic | ADRs |
|-------|------|
| **SDK Architecture** | [0001](decisions/ADR-0001-protocol-extensibility.md), [0002](decisions/ADR-0002-sync-wrapper-strategy.md), [0003](decisions/ADR-0003-asana-sdk-integration.md), [0004](decisions/ADR-0004-item-class-boundary.md), [0005](decisions/ADR-0005-pydantic-model-config.md) |
| **Caching** | [0016](decisions/ADR-0016-cache-protocol-extension.md), [0017](decisions/ADR-0017-redis-backend-architecture.md), [0019](decisions/ADR-0019-staleness-detection-algorithm.md), [0026](decisions/ADR-0026-two-tier-cache-architecture.md), [0115](decisions/ADR-0115-parallel-section-fetch-strategy.md), [0116](decisions/ADR-0116-batch-cache-population-pattern.md), [0117](decisions/ADR-0117-accessor-descriptor-unification.md), [0118](decisions/ADR-0118-rejection-multi-level-cache.md), [0119](decisions/ADR-0119-client-cache-integration-pattern.md), [0123](decisions/ADR-0123-cache-provider-selection.md), [0124](decisions/ADR-0124-client-cache-pattern.md), [0125](decisions/ADR-0125-savesession-invalidation.md), [0126](decisions/ADR-0126-entity-ttl-resolution.md), [0127](decisions/ADR-0127-graceful-degradation.md), [0128](decisions/ADR-0128-hydration-opt-fields-normalization.md), [0129](decisions/ADR-0129-stories-client-cache-wiring.md), [0130](decisions/ADR-0130-cache-population-location.md), [0131](decisions/ADR-0131-gid-enumeration-cache-strategy.md), [0132](decisions/ADR-0132-batch-request-coalescing-strategy.md), [0133](decisions/ADR-0133-progressive-ttl-extension-algorithm.md), [0134](decisions/ADR-0134-staleness-check-integration-pattern.md), [0137](decisions/ADR-0137-post-commit-invalidation-hook.md), [0140](decisions/ADR-0140-dataframe-task-cache-integration.md), [0143](decisions/ADR-0143-detection-result-caching.md) |
| **Save Orchestration** | [0035](decisions/ADR-0035-unit-of-work-pattern.md), [0036](decisions/ADR-0036-change-tracking-strategy.md), [0037](decisions/ADR-0037-dependency-graph-algorithm.md), [0040](decisions/ADR-0040-partial-failure-handling.md) |
| **Business Model** | [0050](decisions/ADR-0050-holder-lazy-loading-strategy.md), [0051](decisions/ADR-0051-custom-field-type-safety.md), [0052](decisions/ADR-0052-bidirectional-reference-caching.md), [0054](decisions/ADR-0054-cascading-custom-fields.md) |
| **Hydration/Resolution** | [0068](decisions/ADR-0068-type-detection-strategy.md), [0069](decisions/ADR-0069-hydration-api-design.md), [0071](decisions/ADR-0071-resolution-ambiguity-handling.md), [0073](decisions/ADR-0073-batch-resolution-api-design.md) |
| **Hardening** | [0074](decisions/ADR-0074-unified-custom-field-tracking.md), [0078](decisions/ADR-0078-gid-based-entity-identity.md), [0084](decisions/ADR-0084-exception-rename-strategy.md), [0086](decisions/ADR-0086-structured-logging.md) |
| **Design Patterns** | [0081](decisions/ADR-0081-custom-field-descriptor-pattern.md), [0091](decisions/ADR-0091-error-classification-mixin.md), [0092](decisions/ADR-0092-crud-base-class-nogo.md) |
| **Process Pipeline** | [0096](decisions/ADR-0096-processtype-expansion.md), [0097](decisions/ADR-0097-processsection-state-machine.md), [0098](decisions/ADR-0098-dual-membership-model.md) (Superseded by 0101), [0099](decisions/ADR-0099-businessseeder-factory.md), [0100](decisions/ADR-0100-state-transition-composition.md) (Superseded by 0101), [0101](decisions/ADR-0101-process-pipeline-correction.md) |
| **Automation Layer** | [0102](decisions/ADR-0102-post-commit-hook-architecture.md), [0103](decisions/ADR-0103-automation-rule-protocol.md), [0104](decisions/ADR-0104-loop-prevention-strategy.md), [0105](decisions/ADR-0105-field-seeding-architecture.md), [0106](decisions/ADR-0106-template-discovery-pattern.md) |
| **Pipeline Enhancement** | [0110](decisions/ADR-0110-task-duplication-strategy.md), [0111](decisions/ADR-0111-subtask-wait-strategy.md), [0112](decisions/ADR-0112-custom-field-gid-resolution.md), [0113](decisions/ADR-0113-rep-field-cascade-pattern.md) |
| **Detection** | [0135](decisions/ADR-0135-processholder-detection.md), [0138](decisions/ADR-0138-tier2-pattern-enhancement.md), [0142](decisions/ADR-0142-detection-package-structure.md) |
| **Process Architecture** | [0136](decisions/ADR-0136-process-field-architecture.md) |
| **Self-Healing** | [0139](decisions/ADR-0139-self-healing-design.md), [0144](decisions/ADR-0144-healingresult-consolidation.md) |
| **Field Patterns** | [0141](decisions/ADR-0141-field-mixin-strategy.md) |

---

## Test Plans

| ID | Title | PRD | Status |
|----|-------|-----|--------|
| [TP-0001](testing/TP-0001-sdk-phase1-parity.md) | SDK Phase 1 Parity | PRD-0001 | Draft |
| [TP-0002](testing/TP-0002-intelligent-caching.md) | Intelligent Caching | PRD-0002 | Draft |
| [TP-0003](testing/TP-0003-batch-api-adversarial.md) | Batch API Adversarial | PRD-0001 | Completed |
| [TP-0004](testing/TP-0004-cross-holder-resolution.md) | Cross-Holder Resolution | PRD-0014 | PASS |
| [TP-0005](testing/TP-0005-foundation-hardening.md) | Foundation Hardening | PRD-0015 | Approved |
| [TP-0006](testing/TP-0006-custom-field-tracking.md) | Custom Field Tracking | PRD-0016 | Draft |
| [TP-0007](testing/TP-0007-navigation-descriptors.md) | Navigation Descriptors | PRD-0017 | Draft |
| [TP-0008](testing/TP-0008-hierarchy-hydration.md) | Hierarchy Hydration | PRD-0013 | PASS |
| [TP-0009](testing/TP-0009-savesession-reliability.md) | SaveSession Reliability | PRD-0018 | Draft |
| [TP-DETECTION](testing/TP-DETECTION.md) | Entity Detection System | PRD-PROCESS-PIPELINE | Draft |

### Validation Reports

| ID | Title | PRD | Status |
|----|-------|-----|--------|
| [VP-WORKSPACE-PROJECT-REGISTRY](testing/VP-WORKSPACE-PROJECT-REGISTRY.md) | Workspace Project Registry | PRD-WORKSPACE-PROJECT-REGISTRY | APPROVED |
| [VP-PIPELINE-AUTOMATION-ENHANCEMENT](testing/VP-PIPELINE-AUTOMATION-ENHANCEMENT.md) | Pipeline Automation Enhancement | PRD-PIPELINE-AUTOMATION-ENHANCEMENT | APPROVED |
| [VALIDATION-WATERMARK-CACHE](validation/VALIDATION-WATERMARK-CACHE.md) | Watermark Cache (Parallel Fetch) | PRD-WATERMARK-CACHE | PASS |
| [VP-CACHE-PERF-FETCH-PATH](validation/VP-CACHE-PERF-FETCH-PATH.md) | DataFrame Fetch Path Cache | PRD-CACHE-PERF-FETCH-PATH | PASS |
| [VP-CACHE-OPTIMIZATION-P2](validation/VP-CACHE-OPTIMIZATION-P2.md) | Cache Optimization Phase 2 | PRD-CACHE-OPTIMIZATION-P2 | PASS |
| [VP-CACHE-OPTIMIZATION-P3](validation/VP-CACHE-OPTIMIZATION-P3.md) | Cache Optimization Phase 3 - GID Enumeration | PRD-CACHE-OPTIMIZATION-P3 | PASS |

---

## Initiatives

| File | Description | Status |
|------|-------------|--------|
| [PROMPT-0-AUTOMATION-LAYER](initiatives/PROMPT-0-AUTOMATION-LAYER.md) | Automation Layer for Pipeline Conversion | Draft |
| [PROMPT-0-PROCESS-CLEANUP](initiatives/PROMPT-0-PROCESS-CLEANUP.md) | Process Pipeline Cleanup Initiative | Pending |
| [PROMPT-0-PROCESS-PIPELINE](initiatives/PROMPT-0-PROCESS-PIPELINE.md) | Process Pipeline Implementation (Superseded) | Superseded |
| [PROMPT-0-membership-detection](initiatives/PROMPT-0-membership-detection.md) | Membership Detection Initiative | Active |
| [PROMPT-0-PIPELINE-AUTOMATION-ENHANCEMENT](initiatives/PROMPT-0-PIPELINE-AUTOMATION-ENHANCEMENT.md) | Pipeline Automation Enhancement Initiative | Active |
| [PROMPT-MINUS-1-CACHE-PERFORMANCE-META](initiatives/PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md) | Cache Performance Meta-Initiative | Active |
| [PROMPT-0-CACHE-INTEGRATION](initiatives/PROMPT-0-CACHE-INTEGRATION.md) | Cache Integration Initiative | Active |
| [PROMPT-0-CACHE-LIGHTWEIGHT-STALENESS](initiatives/PROMPT-0-CACHE-LIGHTWEIGHT-STALENESS.md) | Lightweight Staleness Detection Initiative | Active |
| [PROMPT-0-CACHE-PERF-DETECTION](initiatives/PROMPT-0-CACHE-PERF-DETECTION.md) | P2: Detection Flow Investigation | Active |
| [PROMPT-0-CACHE-PERF-HYDRATION](initiatives/PROMPT-0-CACHE-PERF-HYDRATION.md) | P3: Hydration Caching Investigation | Pending |
| [PROMPT-0-CACHE-PERF-STORIES](initiatives/PROMPT-0-CACHE-PERF-STORIES.md) | P4: Stories/Metrics Caching Investigation | Pending |
| [PROMPT-0-CACHE-UTILIZATION](initiatives/PROMPT-0-CACHE-UTILIZATION.md) | Cache Utilization Initiative | Active |
| [PROMPT-0-DOCS-EPOCH-RESET](initiatives/PROMPT-0-DOCS-EPOCH-RESET.md) | Documentation Epoch Reset | Active |
| [PROMPT-0-TECH-DEBT-REMEDIATION](initiatives/PROMPT-0-TECH-DEBT-REMEDIATION.md) | Tech Debt Remediation Initiative | Active |

### Archived Initiatives (Completed)

| File | Description | Completed |
|------|-------------|-----------|
| [PROMPT-0-WORKSPACE-PROJECT-REGISTRY](.archive/initiatives/2025-Q4/PROMPT-0-WORKSPACE-PROJECT-REGISTRY.md) | Workspace Project Registry Initiative | 2025-Q4 |
| [PROMPT-0-CACHE-PERF-FETCH-PATH](.archive/initiatives/2025-Q4/PROMPT-0-CACHE-PERF-FETCH-PATH.md) | P1: Fetch Path Investigation | 2025-Q4 |
| [PROMPT-0-CACHE-OPTIMIZATION-PHASE2](.archive/initiatives/2025-Q4/PROMPT-0-CACHE-OPTIMIZATION-PHASE2.md) | Cache Optimization Phase 2 | 2025-Q4 |
| [PROMPT-0-CACHE-OPTIMIZATION-PHASE3](.archive/initiatives/2025-Q4/PROMPT-0-CACHE-OPTIMIZATION-PHASE3.md) | Cache Optimization Phase 3 | 2025-Q4 |
| [PROMPT-0-WATERMARK-CACHE](.archive/initiatives/2025-Q4/PROMPT-0-WATERMARK-CACHE.md) | Watermark Cache Initiative | 2025-Q4 |

---

## Initiative Reports

| File | Description | Status |
|------|-------------|--------|
| [REPORT-CACHE-OPTIMIZATION-P2](reports/REPORT-CACHE-OPTIMIZATION-P2.md) | Cache Optimization Phase 2 Final Report | Complete |

---

## Audits and Reports

| File | Description | Status |
|------|-------------|--------|
| [AUDIT-doc-synthesis.md](audits/AUDIT-doc-synthesis.md) | Documentation synthesis audit - SOLID compliance and consolidation opportunities | Complete |
| [MIGRATION-REPORT.md](audits/MIGRATION-REPORT.md) | Documentation migration final report (8 phases) | Complete |

---

## Analysis Documents

| File | Description | Status |
|------|-------------|--------|
| [ANALYSIS-PROCESS-ENTITIES.md](analysis/ANALYSIS-PROCESS-ENTITIES.md) | Process entities as pipeline events - business logic capture | Complete |
| [DISCOVERY-PROCESS-PIPELINE.md](analysis/DISCOVERY-PROCESS-PIPELINE.md) | Process Pipeline initiative discovery - Session 1 | Complete |
| [DISCOVERY-DETECTION-SYSTEM.md](analysis/DISCOVERY-DETECTION-SYSTEM.md) | Entity detection system analysis | Complete |
| [DETECTION-SYSTEM-ANALYSIS.md](analysis/DETECTION-SYSTEM-ANALYSIS.md) | Detection Tier 1-5 deep dive | Complete |
| [IMPACT-PROCESS-CLEANUP.md](analysis/IMPACT-PROCESS-CLEANUP.md) | Process Pipeline Cleanup - impact analysis | Complete |
| [DISCOVERY-AUTOMATION-LAYER.md](analysis/DISCOVERY-AUTOMATION-LAYER.md) | Automation Layer discovery - extension points, fields | Complete |
| [GAP-ANALYSIS-WORKSPACE-PROJECT-REGISTRY.md](analysis/GAP-ANALYSIS-WORKSPACE-PROJECT-REGISTRY.md) | Workspace Project Registry gap analysis | Complete |
| [DISCOVERY-PIPELINE-AUTOMATION-ENHANCEMENT.md](analysis/DISCOVERY-PIPELINE-AUTOMATION-ENHANCEMENT.md) | Pipeline Automation Enhancement discovery - Session 1 | Complete |
| [DISCOVERY-CACHE-PERF-FETCH-PATH.md](analysis/DISCOVERY-CACHE-PERF-FETCH-PATH.md) | Cache Performance - Fetch Path Investigation | Complete |
| [DISCOVERY-CACHE-PERF-DETECTION.md](analysis/DISCOVERY-CACHE-PERF-DETECTION.md) | Cache Performance - Detection Caching Discovery | Complete |
| [INTEGRATION-CACHE-PERF-P1-LEARNINGS.md](analysis/INTEGRATION-CACHE-PERF-P1-LEARNINGS.md) | P1 Learnings for P2-P4 Sub-Initiatives | Complete |
| [DISCOVERY-CACHE-OPTIMIZATION-P2.md](analysis/DISCOVERY-CACHE-OPTIMIZATION-P2.md) | Cache Optimization P2 - Root Cause Analysis | Complete |
| [hydration-cache-opt-fields-analysis.md](analysis/hydration-cache-opt-fields-analysis.md) | Hydration Cache opt_fields Analysis | Complete |
| [multi-level-cache-hierarchy-analysis.md](analysis/multi-level-cache-hierarchy-analysis.md) | Multi-Level Cache Hierarchy Analysis | Complete |
| [stories-cache-wiring-discovery.md](analysis/stories-cache-wiring-discovery.md) | Stories Cache Wiring Discovery | Complete |
| [watermark-cache-discovery.md](analysis/watermark-cache-discovery.md) | Watermark Cache Discovery | Complete |
| [GAP-ANALYSIS-CACHE-UTILIZATION.md](analysis/GAP-ANALYSIS-CACHE-UTILIZATION.md) | Cache Utilization Gap Analysis | Complete |
| [GAP-ANALYSIS-CACHE-OPTIMIZATION-P2.md](analysis/GAP-ANALYSIS-CACHE-OPTIMIZATION-P2.md) | Cache Optimization P2 Gap Analysis | Complete |

---

## Sprint Planning Documents

| File | Description | Status |
|------|-------------|--------|
| [PRD-SPRINT-1-PATTERN-COMPLETION](planning/sprints/PRD-SPRINT-1-PATTERN-COMPLETION.md) | Sprint 1 Pattern Completion Decomposition | Draft |
| [PRD-SPRINT-3-DETECTION-DECOMPOSITION](planning/sprints/PRD-SPRINT-3-DETECTION-DECOMPOSITION.md) | Sprint 3 Detection Decomposition | Draft |
| [PRD-SPRINT-4-SAVESESSION-DECOMPOSITION](planning/sprints/PRD-SPRINT-4-SAVESESSION-DECOMPOSITION.md) | Sprint 4 SaveSession Decomposition | Draft |
| [PRD-SPRINT-5-CLEANUP](planning/sprints/PRD-SPRINT-5-CLEANUP.md) | Sprint 5 Cleanup | Draft |
| [TDD-SPRINT-1-PATTERN-COMPLETION](planning/sprints/TDD-SPRINT-1-PATTERN-COMPLETION.md) | Sprint 1 Pattern Completion Design | Draft |
| [TDD-SPRINT-3-DETECTION-DECOMPOSITION](planning/sprints/TDD-SPRINT-3-DETECTION-DECOMPOSITION.md) | Sprint 3 Detection Design | Draft |
| [TDD-SPRINT-4-SAVESESSION-DECOMPOSITION](planning/sprints/TDD-SPRINT-4-SAVESESSION-DECOMPOSITION.md) | Sprint 4 SaveSession Design | Draft |
| [TDD-SPRINT-5-CLEANUP](planning/sprints/TDD-SPRINT-5-CLEANUP.md) | Sprint 5 Cleanup Design | Draft |

---

## Reference Data

See [reference/README.md](reference/README.md) for complete reference documentation guide.

### Cache Architecture (6 docs)

| File | Description |
|------|-------------|
| [REF-cache-architecture.md](reference/REF-cache-architecture.md) | Core architecture, provider protocol, backend selection |
| [REF-cache-staleness-detection.md](reference/REF-cache-staleness-detection.md) | Detection algorithms, modified-since, batch coalescing |
| [REF-cache-ttl-strategy.md](reference/REF-cache-ttl-strategy.md) | Progressive TTL, watermark approach, max TTL calculation |
| [REF-cache-provider-protocol.md](reference/REF-cache-provider-protocol.md) | CacheProvider interface specification |
| [REF-cache-invalidation.md](reference/REF-cache-invalidation.md) | Invalidation strategies and hooks |
| [REF-cache-patterns.md](reference/REF-cache-patterns.md) | Common cache usage patterns and best practices |

### Entity Model (5 docs)

| File | Description |
|------|-------------|
| [REF-entity-lifecycle.md](reference/REF-entity-lifecycle.md) | Define → Detect → Populate → Navigate → Persist |
| [REF-detection-tiers.md](reference/REF-detection-tiers.md) | 5-tier detection system specification |
| [REF-savesession-lifecycle.md](reference/REF-savesession-lifecycle.md) | Track → Modify → Commit → Validate |
| [REF-asana-hierarchy.md](reference/REF-asana-hierarchy.md) | Workspace → Project → Section → Task → Subtask |
| [REF-entity-type-table.md](reference/REF-entity-type-table.md) | Business model entity hierarchy |

### Workflow (3 docs)

| File | Description |
|------|-------------|
| [REF-workflow-phases.md](reference/REF-workflow-phases.md) | Requirements → Design → Implementation → Testing |
| [REF-command-decision-tree.md](reference/REF-command-decision-tree.md) | When to use /task vs /sprint vs /hotfix |
| [REF-batch-operations.md](reference/REF-batch-operations.md) | Chunking, parallelization, error handling |

### Metadata (3 docs)

| File | Description |
|------|-------------|
| [GLOSSARY.md](reference/GLOSSARY.md) | Unified terminology reference (200+ terms) |
| [REF-skills-index.md](reference/REF-skills-index.md) | Skills architecture and activation triggers |
| [REF-custom-field-catalog.md](reference/REF-custom-field-catalog.md) | 108 custom fields across 5 models |

---

## Runbooks (Operational Troubleshooting)

See [runbooks/README.md](runbooks/README.md) for runbook usage guide.

| File | Description |
|------|-------------|
| [RUNBOOK-cache-troubleshooting.md](runbooks/RUNBOOK-cache-troubleshooting.md) | Cache misses, stale data, errors, performance |
| [RUNBOOK-savesession-debugging.md](runbooks/RUNBOOK-savesession-debugging.md) | SaveSession dependency cycles, partial failures, healing |
| [RUNBOOK-detection-troubleshooting.md](runbooks/RUNBOOK-detection-troubleshooting.md) | Detection failures, wrong types, tier fallback |

---

## Guides

| Guide | Description |
|-------|-------------|
| [concepts.md](guides/concepts.md) | Core SDK concepts and mental model |
| [quickstart.md](guides/quickstart.md) | Get started in 5 minutes |
| [workflows.md](guides/workflows.md) | Common task recipes |
| [patterns.md](guides/patterns.md) | Best practices |
| [save-session.md](guides/save-session.md) | SaveSession Unit of Work guide |
| [sdk-adoption.md](guides/sdk-adoption.md) | Migration from old patterns |
| [autom8-migration.md](guides/autom8-migration.md) | S3 to Redis cache migration |

---

## Migration Guides

| Guide | Description |
|-------|-------------|
| [MIGRATION-ASYNC-METHOD.md](migration/MIGRATION-ASYNC-METHOD.md) | @async_method decorator migration |

---

## Archived Content

Historical artifacts are preserved in `.archive/`:

| Archive | Contents |
|---------|----------|
| `.archive/initiatives/2025-Q4/` | Completed Q4 2025 initiatives (5 files) |
| `.archive/initiatives/` | Other completed PROMPT-0, PROMPT-MINUS-1 files |
| `.archive/discovery/` | DISCOVERY-* analysis documents |
| `.archive/validation/` | Point-in-time validation reports, invalidated reports (VALIDATION-PROCESS-PIPELINE) |
| `.archive/historical/` | Other completed work |
| `.archive/architecture/` | Superseded architecture docs |

---

## Document Number Allocation

### Current Highest Numbers

| Type | Current Max | Next Available | Location |
|------|-------------|----------------|----------|
| PRD | PRD-0024 | PRD-0025 | `docs/requirements/` |
| TDD | TDD-0030 | TDD-0031 | `docs/design/` |
| ADR | ADR-0144 | ADR-0145 | `docs/decisions/` |
| TP | TP-0009 | TP-0010 | `docs/testing/` |

**Note**: ADR duplicates resolved 2024-12-24. ADR-0115 through ADR-0120 duplicates renumbered to ADR-0135 through ADR-0144. Next available ADR number is ADR-0145.

### When to Use Sequential Numbers vs Descriptive Names

See [CONVENTIONS.md](CONVENTIONS.md#when-to-use-numbered-vs-named-format) for detailed naming guidance.

**Quick decision tree:**

```
Is this part of a multi-document initiative?
├─ YES → Use descriptive naming (e.g., PRD-CACHE-INTEGRATION)
│         Group related docs with common prefix (PRD-CACHE-*)
│
└─ NO → Use next sequential number (e.g., PRD-0025)
          Allocate from table above
```

**Sequential numbering rules:**

1. **Check this table** for current highest number
2. **Use next available** number (current max + 1)
3. **Never skip** numbers (no gaps allowed)
4. **Never reuse** numbers (even for deleted documents)
5. **Zero-pad** to 4 digits (0025, not 25)
6. **Update INDEX.md** immediately after creating new numbered document

**Descriptive naming rules:**

1. **Use ALL-CAPS** with hyphens (e.g., CACHE-INTEGRATION)
2. **Group by prefix** for initiatives (e.g., all cache docs start with `CACHE-`)
3. **Match format** between paired PRD/TDD (both numbered or both named)
4. **No sequential tracking** needed (not added to allocation table above)

**Examples of each approach:**

| Approach | Example Documents | When to Use |
|----------|-------------------|-------------|
| **Sequential** | PRD-0013-hierarchy-hydration.md<br>TDD-0017-hierarchy-hydration.md | Standalone feature, independent of broader initiative |
| **Descriptive** | PRD-CACHE-INTEGRATION.md<br>TDD-CACHE-INTEGRATION.md<br>PRD-CACHE-PERF-FETCH-PATH.md<br>TDD-CACHE-PERF-FETCH-PATH.md | Multiple docs for cache initiative, grouped for discoverability |

### How to Allocate a New Number

**For numbered documents:**

1. Find document type row in table above (PRD, TDD, ADR, or TP)
2. Use "Next Available" number from table
3. Create document: `PRD-XXXX-feature-name.md`
4. Update this table: increment "Current Max" and "Next Available"
5. Add entry to appropriate section below (PRDs, TDDs, ADRs, or Test Plans)

**For named documents:**

1. Choose descriptive name matching initiative (e.g., `CACHE-INTEGRATION`)
2. Create document: `PRD-DESCRIPTIVE-NAME.md`
3. No need to update allocation table (named docs don't use sequential numbers)
4. Add entry to appropriate section below

**ADR special case**: ADRs always use sequential numbering. Never use descriptive names for ADRs.
