# Archived TDDs (Pre-Consolidation)

Original TDDs from SDK development, consolidated December 2025.

## About This Archive

These 38 TDDs represent the design history from initial SDK development through production hardening. They have been synthesized into 12 consolidated TDDs that provide a cleaner navigation experience while preserving all design decisions.

**Active designs**: See [`docs/design/TDD-*.md`](../../design/)

**Why archived?** As the SDK matured, documentation grew organically. This created navigation overhead and redundancy. The consolidation reduced 34 active TDDs to 12, grouping related designs by domain.

## Consolidation Mapping

| Original TDD | Title | Consolidated Into |
|--------------|-------|-------------------|
| TDD-SDK-FAMILY | SDK Design Evolution | [TDD-01: Foundation & SDK Architecture](../../design/TDD-01-foundation-architecture.md) |
| TDD-0006 | Backward Compatibility Layer | [TDD-01: Foundation & SDK Architecture](../../design/TDD-01-foundation-architecture.md) |
| TDD-0002 | Core Models and Pagination Infrastructure | [TDD-02: Data Layer Architecture](../../design/TDD-02-data-layer.md) |
| TDD-0009 | Structured Dataframe Layer | [TDD-02: Data Layer Architecture](../../design/TDD-02-data-layer.md) |
| TDD-0009.1 | Dynamic Custom Field Resolution | [TDD-02: Data Layer Architecture](../../design/TDD-02-data-layer.md) |
| TDD-0003 | Tier 1 Resource Clients | [TDD-03: Resource Client Architecture](../../design/TDD-03-resource-clients.md) |
| TDD-0004 | Tier 2 Resource Clients | [TDD-03: Resource Client Architecture](../../design/TDD-03-resource-clients.md) |
| TDD-0005 | Batch API for Bulk Operations | [TDD-04: Batch & Save Operations](../../design/TDD-04-batch-save-operations.md) |
| TDD-0010 | Save Orchestration Layer | [TDD-04: Batch & Save Operations](../../design/TDD-04-batch-save-operations.md) |
| TDD-0022 | SaveSession Reliability | [TDD-04: Batch & Save Operations](../../design/TDD-04-batch-save-operations.md) |
| TDD-0007 | Observability Enhancements | [TDD-05: Observability & Telemetry](../../design/TDD-05-observability.md) |
| TDD-0020 | Custom Field Unification | [TDD-06: Custom Fields Architecture](../../design/TDD-06-custom-fields.md) |
| TDD-0023 | Custom Field Property Descriptors | [TDD-06: Custom Fields Architecture](../../design/TDD-06-custom-fields.md) |
| TDD-CUSTOM-FIELD-REMEDIATION | Custom Field Reality Remediation | [TDD-06: Custom Fields Architecture](../../design/TDD-06-custom-fields.md) |
| TDD-0017 | Business Model Hydration | [TDD-07: Navigation & Hydration Architecture](../../design/TDD-07-navigation-hydration.md) |
| TDD-0021 | Navigation Pattern Consolidation | [TDD-07: Navigation & Hydration Architecture](../../design/TDD-07-navigation-hydration.md) |
| TDD-0024 | Holder Factory with `__init_subclass__` | [TDD-07: Navigation & Hydration Architecture](../../design/TDD-07-navigation-hydration.md) |
| TDD-PROCESS-PIPELINE | Process Pipeline | [TDD-08: Business Domain Architecture](../../design/TDD-08-business-domain.md) |
| TDD-AUTOMATION-LAYER | Automation Layer | [TDD-08: Business Domain Architecture](../../design/TDD-08-business-domain.md) |
| TDD-DETECTION | Membership-Based Entity Type Detection | [TDD-08: Business Domain Architecture](../../design/TDD-08-business-domain.md) |
| TDD-PIPELINE-AUTOMATION-ENHANCEMENT | Pipeline Automation Enhancement | [TDD-08: Business Domain Architecture](../../design/TDD-08-business-domain.md) |
| TDD-0027 | Business Model Skills Architecture | [TDD-08: Business Domain Architecture](../../design/TDD-08-business-domain.md) |
| TDD-0028 | Business Model Layer Implementation | [TDD-08: Business Domain Architecture](../../design/TDD-08-business-domain.md) |
| TDD-WORKSPACE-PROJECT-REGISTRY | Workspace Project Registry | [TDD-09: Registry & Field Seeding](../../design/TDD-09-registry-seeding.md) |
| TDD-FIELD-SEEDING-CONFIG | Field Seeding Configuration | [TDD-09: Registry & Field Seeding](../../design/TDD-09-registry-seeding.md) |
| TDD-0011 | Action Endpoint Support | [TDD-10: Operations & SDK Usability](../../design/TDD-10-operations-usability.md) |
| TDD-0013 | Parent & Subtask Operations | [TDD-10: Operations & SDK Usability](../../design/TDD-10-operations-usability.md) |
| TDD-0015 | SDK Usability Overhaul | [TDD-10: Operations & SDK Usability](../../design/TDD-10-operations-usability.md) |
| TDD-0025 | Async/Sync Method Generator | [TDD-10: Operations & SDK Usability](../../design/TDD-10-operations-usability.md) |
| TDD-0016 | QA Findings Cascade Integration | [TDD-11: Resolution & Foundation Hardening](../../design/TDD-11-resolution-hardening.md) |
| TDD-0018 | Cross-Holder Relationship Resolution | [TDD-11: Resolution & Foundation Hardening](../../design/TDD-11-resolution-hardening.md) |
| TDD-0019 | Architecture Hardening Initiative A | [TDD-11: Resolution & Foundation Hardening](../../design/TDD-11-resolution-hardening.md) |
| TDD-TECH-DEBT-REMEDIATION | Technical Debt Remediation | [TDD-12: Technical Debt & Migration](../../design/TDD-12-debt-migration.md) |
| TDD-DOCS-EPOCH-RESET | Documentation Epoch Reset | [TDD-12: Technical Debt & Migration](../../design/TDD-12-debt-migration.md) |

## Files Not Consolidated

The following files were not part of the consolidation effort (supplementary or reference documents):

| File | Reason |
|------|--------|
| TDD-0001-sdk-architecture.md | Superseded by TDD-SDK-FAMILY |
| TDD-0012-sdk-functional-parity.md | Supplementary parity tracking |
| TDD-0014-sdk-ga-readiness.md | GA checklist (operational, not design) |
| TDD-0029-sdk-demo.md | Demo suite (validation, not design) |
| PHASE-6-TDD-SPLITTING-SUMMARY.md | Process documentation |

## Files in Archive

### Foundation & SDK (TDD-01)
- [TDD-SDK-FAMILY.md](TDD-SDK-FAMILY.md) - SDK Design Evolution
- [TDD-0001-sdk-architecture.md](TDD-0001-sdk-architecture.md) - autom8_asana SDK Architecture
- [TDD-0006-backward-compatibility.md](TDD-0006-backward-compatibility.md) - Backward Compatibility Layer

### Data Layer (TDD-02)
- [TDD-0002-models-pagination.md](TDD-0002-models-pagination.md) - Core Models and Pagination Infrastructure
- [TDD-0009-structured-dataframe-layer.md](TDD-0009-structured-dataframe-layer.md) - Structured Dataframe Layer
- [TDD-0009.1-dynamic-custom-field-resolution.md](TDD-0009.1-dynamic-custom-field-resolution.md) - Dynamic Custom Field Resolution

### Resource Clients (TDD-03)
- [TDD-0003-tier1-clients.md](TDD-0003-tier1-clients.md) - Tier 1 Resource Clients
- [TDD-0004-tier2-clients.md](TDD-0004-tier2-clients.md) - Tier 2 Resource Clients

### Batch & Save (TDD-04)
- [TDD-0005-batch-api.md](TDD-0005-batch-api.md) - Batch API for Bulk Operations
- [TDD-0010-save-orchestration.md](TDD-0010-save-orchestration.md) - Save Orchestration Layer
- [TDD-0022-savesession-reliability.md](TDD-0022-savesession-reliability.md) - SaveSession Reliability

### Observability (TDD-05)
- [TDD-0007-observability.md](TDD-0007-observability.md) - Observability Enhancements

### Custom Fields (TDD-06)
- [TDD-0020-custom-field-tracking.md](TDD-0020-custom-field-tracking.md) - Custom Field Unification
- [TDD-0023-custom-field-descriptors.md](TDD-0023-custom-field-descriptors.md) - Custom Field Property Descriptors
- [TDD-CUSTOM-FIELD-REMEDIATION.md](TDD-CUSTOM-FIELD-REMEDIATION.md) - Custom Field Reality Remediation

### Navigation & Hydration (TDD-07)
- [TDD-0017-hierarchy-hydration.md](TDD-0017-hierarchy-hydration.md) - Business Model Hydration
- [TDD-0021-navigation-descriptors.md](TDD-0021-navigation-descriptors.md) - Navigation Pattern Consolidation
- [TDD-0024-holder-factory.md](TDD-0024-holder-factory.md) - Holder Factory with `__init_subclass__`

### Business Domain (TDD-08)
- [TDD-PROCESS-PIPELINE.md](TDD-PROCESS-PIPELINE.md) - Process Pipeline
- [TDD-AUTOMATION-LAYER.md](TDD-AUTOMATION-LAYER.md) - Automation Layer
- [TDD-DETECTION.md](TDD-DETECTION.md) - Membership-Based Entity Type Detection
- [TDD-PIPELINE-AUTOMATION-ENHANCEMENT.md](TDD-PIPELINE-AUTOMATION-ENHANCEMENT.md) - Pipeline Automation Enhancement
- [TDD-0027-business-model-architecture.md](TDD-0027-business-model-architecture.md) - Business Model Skills Architecture
- [TDD-0028-business-model-implementation.md](TDD-0028-business-model-implementation.md) - Business Model Layer Implementation

### Registry & Seeding (TDD-09)
- [TDD-WORKSPACE-PROJECT-REGISTRY.md](TDD-WORKSPACE-PROJECT-REGISTRY.md) - Workspace Project Registry
- [TDD-FIELD-SEEDING-CONFIG.md](TDD-FIELD-SEEDING-CONFIG.md) - Field Seeding Configuration

### Operations & Usability (TDD-10)
- [TDD-0011-action-endpoint-support.md](TDD-0011-action-endpoint-support.md) - Action Endpoint Support
- [TDD-0013-parent-subtask-operations.md](TDD-0013-parent-subtask-operations.md) - Parent & Subtask Operations
- [TDD-0015-sdk-usability.md](TDD-0015-sdk-usability.md) - SDK Usability Overhaul
- [TDD-0025-async-method-decorator.md](TDD-0025-async-method-decorator.md) - Async/Sync Method Generator

### Resolution & Hardening (TDD-11)
- [TDD-0016-cascade-and-fixes.md](TDD-0016-cascade-and-fixes.md) - QA Findings Cascade Integration
- [TDD-0018-cross-holder-resolution.md](TDD-0018-cross-holder-resolution.md) - Cross-Holder Relationship Resolution
- [TDD-0019-foundation-hardening.md](TDD-0019-foundation-hardening.md) - Architecture Hardening Initiative A

### Debt & Migration (TDD-12)
- [TDD-TECH-DEBT-REMEDIATION.md](TDD-TECH-DEBT-REMEDIATION.md) - Technical Debt Remediation
- [TDD-DOCS-EPOCH-RESET.md](TDD-DOCS-EPOCH-RESET.md) - Documentation Epoch Reset

### Supplementary Files
- [TDD-0012-sdk-functional-parity.md](TDD-0012-sdk-functional-parity.md) - SDK Functional Parity Initiative
- [TDD-0014-sdk-ga-readiness.md](TDD-0014-sdk-ga-readiness.md) - SDK GA Readiness
- [TDD-0029-sdk-demo.md](TDD-0029-sdk-demo.md) - SDK Demonstration Suite
- [PHASE-6-TDD-SPLITTING-SUMMARY.md](PHASE-6-TDD-SPLITTING-SUMMARY.md) - Phase 6 TDD Splitting Summary

---

*Archive created: 2025-12-25*
*Total files: 38*
*Consolidated designs: 34 -> 12*
