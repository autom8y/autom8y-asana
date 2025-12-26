# Archived PRDs (Pre-Consolidation)

Original PRDs from SDK development, archived December 2025.

## About This Archive

These 32 PRDs represent the requirements history from initial SDK development through production hardening. They document the evolution from monolith extraction (PRD-0001) through business domain automation (PRD-AUTOMATION-LAYER).

The PRDs have been synthesized into 11 consolidated PRDs that provide a cleaner, topic-focused structure while preserving all requirements.

**Active requirements**: See `docs/requirements/PRD-*.md`

---

## Consolidation Mapping

| Consolidated PRD | Source PRDs |
|------------------|-------------|
| **PRD-01: Foundation & SDK Architecture** | PRD-SDK-FAMILY, PRD-0001, PRD-0004, PRD-0007, PRD-0009, PRD-0011, PRD-0015 |
| **PRD-02: Data Layer Architecture** | PRD-0003, PRD-0003.1 |
| **PRD-03: Batch & Save Operations** | PRD-0005, PRD-0006, PRD-0008, PRD-0018 |
| **PRD-04: Custom Fields Architecture** | PRD-0016, PRD-0019, PRD-0024 |
| **PRD-05: Navigation & Hydration** | PRD-0013, PRD-0017, PRD-0020 |
| **PRD-06: Business Domain Architecture** | PRD-0010, PRD-PROCESS-PIPELINE, PRD-PROCESS-PIPELINE-AMENDMENT, PRD-AUTOMATION-LAYER, PRD-PIPELINE-AUTOMATION-ENHANCEMENT |
| **PRD-07: Detection & Resolution** | PRD-DETECTION, PRD-0014, PRD-WORKSPACE-PROJECT-REGISTRY |
| **PRD-08: Field Seeding Configuration** | PRD-FIELD-SEEDING-GAP |
| **PRD-09: SDK Usability** | PRD-0012 |
| **PRD-10: Quality & Triage** | PRD-0023 |
| **PRD-11: Technical Debt & Migration** | PRD-TECH-DEBT-REMEDIATION, PRD-DOCS-EPOCH-RESET |

---

## Files in Archive

### SDK Foundation & Evolution

| File | Original Title | Date |
|------|----------------|------|
| `PRD-0001-sdk-extraction.md` | SDK Extraction | 2025-12-08 |
| `PRD-0004-test-hang-fix.md` | Test Hang Fix | 2025-12 |
| `PRD-0007-sdk-functional-parity.md` | SDK Functional Parity Initiative | 2025-12-10 |
| `PRD-0009-sdk-ga-readiness.md` | SDK GA Readiness | 2025-12-10 |
| `PRD-0011-sdk-demonstration-suite.md` | SDK Demonstration Suite | 2025-12-12 |
| `PRD-0015-foundation-hardening.md` | Foundation Hardening | 2025-12 |
| `PRD-SDK-FAMILY.md` | SDK Requirements Evolution (synthesis) | 2025-12 |

### Data Layer

| File | Original Title | Date |
|------|----------------|------|
| `PRD-0003-structured-dataframe-layer.md` | Structured Dataframe Layer | 2025-12 |
| `PRD-0003.1-dynamic-custom-field-resolution.md` | Dynamic Custom Field Resolution | 2025-12 |

### Save & Batch Operations

| File | Original Title | Date |
|------|----------------|------|
| `PRD-0005-save-orchestration.md` | Save Orchestration Layer | 2025-12 |
| `PRD-0006-action-endpoint-support.md` | Action Endpoint Support | 2025-12 |
| `PRD-0008-parent-subtask-operations.md` | Parent/Subtask Operations | 2025-12 |
| `PRD-0018-savesession-reliability.md` | SaveSession Reliability | 2025-12 |

### Custom Fields

| File | Original Title | Date |
|------|----------------|------|
| `PRD-0016-custom-field-tracking.md` | Custom Field Tracking | 2025-12 |
| `PRD-0019-custom-field-descriptors.md` | Custom Field Descriptors | 2025-12 |
| `PRD-0024-custom-field-remediation.md` | Custom Field Remediation | 2025-12 |

### Navigation & Hydration

| File | Original Title | Date |
|------|----------------|------|
| `PRD-0013-hierarchy-hydration.md` | Hierarchy Hydration | 2025-12 |
| `PRD-0014-cross-holder-resolution.md` | Cross-Holder Resolution | 2025-12 |
| `PRD-0017-navigation-descriptors.md` | Navigation Descriptors | 2025-12 |
| `PRD-0020-holder-factory.md` | Holder Factory | 2025-12 |

### Business Domain & Automation

| File | Original Title | Date |
|------|----------------|------|
| `PRD-0010-business-model-layer.md` | Business Model Layer | 2025-12 |
| `PRD-AUTOMATION-LAYER.md` | Automation Layer | 2025-12 |
| `PRD-PIPELINE-AUTOMATION-ENHANCEMENT.md` | Pipeline Automation Enhancement | 2025-12 |
| `PRD-PROCESS-PIPELINE.md` | Process Pipeline | 2025-12 |
| `PRD-PROCESS-PIPELINE-AMENDMENT.md` | Process Pipeline Amendment | 2025-12 |

### Detection & Resolution

| File | Original Title | Date |
|------|----------------|------|
| `PRD-DETECTION.md` | Entity Detection | 2025-12 |
| `PRD-WORKSPACE-PROJECT-REGISTRY.md` | Workspace Project Registry | 2025-12 |

### Field Seeding

| File | Original Title | Date |
|------|----------------|------|
| `PRD-FIELD-SEEDING-GAP.md` | Field Seeding Gap Analysis | 2025-12 |

### SDK Usability

| File | Original Title | Date |
|------|----------------|------|
| `PRD-0012-sdk-usability-improvements.md` | SDK Usability Improvements | 2025-12 |

### Quality & Maintenance

| File | Original Title | Date |
|------|----------------|------|
| `PRD-0023-qa-triage-fixes.md` | QA Triage Fixes | 2025-12 |
| `PRD-DOCS-EPOCH-RESET.md` | Documentation Epoch Reset | 2025-12 |
| `PRD-TECH-DEBT-REMEDIATION.md` | Technical Debt Remediation | 2025-12 |

---

## Archive Notes

- **Archive Date**: 2025-12-25
- **Total Files**: 32 PRDs
- **Consolidated Into**: 11 PRDs in `docs/requirements/`
- **Consolidation Rationale**: Reduce document count while preserving requirements traceability; group related requirements by domain rather than chronology

For the current authoritative requirements, refer to the consolidated PRDs in `docs/requirements/`.
