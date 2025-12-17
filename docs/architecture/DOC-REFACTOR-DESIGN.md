# DOC-REFACTOR-DESIGN: Documentation Transformation Blueprint

> **Status**: Session 2 Deliverable
> **Author**: Architect
> **Date**: 2025-12-17
> **Input**: CONTENT-INVENTORY.md (Session 1)
> **Output**: Executable transformation plan for Sessions 3-4

---

## Executive Summary

This document provides a complete transformation blueprint for restructuring `/docs` from its current state (~107 documents across 14 directories) to a clean, content-based naming structure. The Principal Engineer can execute Sessions 3-4 from this document alone.

### Transformation Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Active directories | 14 | 8 |
| Codename-based files | 44 | 0 |
| Process artifacts in active dirs | 33 | 0 |
| Duplicate/redundant docs | 10 | 0 |
| Misplaced files | 5 | 0 |

---

## 1. Target Directory Structure

```
/docs/
├── INDEX.md                          # Documentation registry (rewrite after refactor)
├── CONTENT-INVENTORY.md              # Archive after refactor complete
│
├── requirements/                     # PRDs: WHAT we build
│   ├── PRD-0001-sdk-extraction.md
│   ├── PRD-0002-intelligent-caching.md
│   ├── ...
│   └── PRD-0023-qa-triage-fixes.md
│
├── design/                           # TDDs: HOW we build it
│   ├── TDD-0001-sdk-architecture.md
│   ├── TDD-0002-models-pagination.md
│   ├── ...
│   └── TDD-0027-sdk-demo.md
│
├── decisions/                        # ADRs: WHY we decided
│   ├── ADR-0001-protocol-extensibility.md
│   ├── ...
│   └── ADR-0092-crud-base-class-nogo.md
│
├── testing/                          # Test Plans: HOW we validate
│   ├── TP-0001-sdk-phase1-parity.md
│   ├── TP-0002-intelligent-caching.md
│   ├── ...
│   └── TP-0009-savesession-reliability.md
│
├── guides/                           # User-facing docs (OUT OF SCOPE)
│   └── [unchanged]
│
├── releases/                         # Release notes (unchanged)
│   └── v0.3.0-RELEASE-NOTES.md
│
├── migration/                        # Migration guides (active only)
│   └── MIGRATION-ASYNC-METHOD.md
│
├── reference/                        # NEW: Extracted reference data
│   ├── REF-entity-type-table.md      # From DISCOVERY-HYDRATION-001.md
│   └── REF-custom-field-catalog.md   # From DISCOVERY-PATTERNS-A-CUSTOM-FIELDS.md
│
└── .archive/                         # Historical/process artifacts
    ├── initiatives/                  # PROMPT-0, PROMPT-MINUS-1 files
    ├── discovery/                    # DISCOVERY-* files
    ├── validation/                   # VALIDATION-*, VR-*, NFR-* files
    ├── historical/                   # One-off historical docs
    └── architecture/                 # Superseded architecture docs
```

### Directory Purpose Matrix

| Directory | Content Type | Naming Convention | Owner |
|-----------|--------------|-------------------|-------|
| requirements/ | PRDs | `PRD-NNNN-slug.md` | Analyst |
| design/ | TDDs | `TDD-NNNN-slug.md` | Architect |
| decisions/ | ADRs | `ADR-NNNN-slug.md` | Architect |
| testing/ | Test Plans | `TP-NNNN-slug.md` | QA |
| guides/ | User docs | descriptive-slug.md | Engineer |
| releases/ | Release notes | vX.Y.Z-RELEASE-NOTES.md | Release Mgr |
| migration/ | Migration guides | MIGRATION-slug.md | Engineer |
| reference/ | Reference data | REF-slug.md | Various |
| .archive/ | Historical | [original name] | N/A |

---

## 2. Complete File Mapping

### 2.1 Requirements (/docs/requirements/)

#### KEEP (10 files)

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| PRD-0001-sdk-extraction.md | KEEP | PRD-0001-sdk-extraction.md | No change |
| PRD-0002-intelligent-caching.md | KEEP | PRD-0002-intelligent-caching.md | No change |
| PRD-0003-structured-dataframe-layer.md | KEEP | PRD-0003-structured-dataframe-layer.md | No change |
| PRD-0003.1-dynamic-custom-field-resolution.md | KEEP | PRD-0003.1-dynamic-custom-field-resolution.md | No change |
| PRD-0004-test-hang-fix.md | KEEP | PRD-0004-test-hang-fix.md | No change |
| PRD-0005-save-orchestration.md | KEEP | PRD-0005-save-orchestration.md | No change |
| PRD-0006-action-endpoint-support.md | KEEP | PRD-0006-action-endpoint-support.md | No change |
| PRD-0007-sdk-functional-parity.md | KEEP | PRD-0007-sdk-functional-parity.md | No change |
| PRD-0008-parent-subtask-operations.md | KEEP | PRD-0008-parent-subtask-operations.md | No change |
| PRD-0009-sdk-ga-readiness.md | KEEP | PRD-0009-sdk-ga-readiness.md | No change |

#### RENAME (13 files)

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| PRD-BIZMODEL.md | RENAME | PRD-0010-business-model-layer.md | Business model typed entities |
| PRD-SDKDEMO.md | RENAME | PRD-0011-sdk-demonstration-suite.md | SDK validation demo script |
| PRD-SDKUX.md | RENAME | PRD-0012-sdk-usability-improvements.md | Convenience methods, implicit sessions |
| PRD-HYDRATION.md | RENAME | PRD-0013-hierarchy-hydration.md | Hierarchy loading from any entry point |
| PRD-RESOLUTION.md | RENAME | PRD-0014-cross-holder-resolution.md | AssetEdit to Unit/Offer resolution |
| PRD-HARDENING-A.md | RENAME | PRD-0015-foundation-hardening.md | Exceptions, logging, observability |
| PRD-HARDENING-B.md | RENAME | PRD-0016-custom-field-tracking.md | Change tracking unification |
| PRD-HARDENING-C.md | RENAME | PRD-0017-navigation-descriptors.md | Navigation pattern consolidation |
| PRD-HARDENING-F.md | RENAME | PRD-0018-savesession-reliability.md | GID identity, retryable errors |
| PRD-PATTERNS-A.md | RENAME | PRD-0019-custom-field-descriptors.md | Property descriptors |
| PRD-PATTERNS-C.md | RENAME | PRD-0020-holder-factory.md | __init_subclass__ pattern |
| PRD-DESIGN-PATTERNS-D.md | RENAME | PRD-0021-async-method-generator.md | @async_method decorator |
| PRD-DESIGN-PATTERNS-E.md | RENAME | PRD-0022-crud-base-class.md | CRUD base class evaluation |

#### RENAME (Non-standard) (1 file)

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| TRIAGE-FIXES-REQUIREMENTS.md | RENAME | PRD-0023-qa-triage-fixes.md | QA findings - actionable requirements |

#### ARCHIVE (1 file)

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| TECH-DEBT.md | ARCHIVE | .archive/historical/TECH-DEBT.md | Backlog tracking, not active requirements |

---

### 2.2 Design (/docs/design/)

#### KEEP (14 files)

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| TDD-0001-sdk-architecture.md | KEEP | TDD-0001-sdk-architecture.md | No change |
| TDD-0002-models-pagination.md | KEEP | TDD-0002-models-pagination.md | No change |
| TDD-0003-tier1-clients.md | KEEP | TDD-0003-tier1-clients.md | No change |
| TDD-0004-tier2-clients.md | KEEP | TDD-0004-tier2-clients.md | No change |
| TDD-0005-batch-api.md | KEEP | TDD-0005-batch-api.md | No change |
| TDD-0006-backward-compatibility.md | KEEP | TDD-0006-backward-compatibility.md | No change |
| TDD-0007-observability.md | KEEP | TDD-0007-observability.md | No change |
| TDD-0008-intelligent-caching.md | KEEP | TDD-0008-intelligent-caching.md | No change |
| TDD-0009-structured-dataframe-layer.md | KEEP | TDD-0009-structured-dataframe-layer.md | No change |
| TDD-0009.1-dynamic-custom-field-resolution.md | KEEP | TDD-0009.1-dynamic-custom-field-resolution.md | No change |
| TDD-0010-save-orchestration.md | KEEP | TDD-0010-save-orchestration.md | No change |
| TDD-0011-action-endpoint-support.md | KEEP | TDD-0011-action-endpoint-support.md | No change |
| TDD-0012-sdk-functional-parity.md | KEEP | TDD-0012-sdk-functional-parity.md | No change |
| TDD-0013-parent-subtask-operations.md | KEEP | TDD-0013-parent-subtask-operations.md | No change |
| TDD-0014-sdk-ga-readiness.md | KEEP | TDD-0014-sdk-ga-readiness.md | No change |

#### RENAME (12 files)

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| TDD-SDKUX.md | RENAME | TDD-0015-sdk-usability.md | Convenience methods, implicit sessions |
| CASCADE-AND-FIXES-TDD.md | RENAME | TDD-0016-cascade-and-fixes.md | Cascade execution + QA bug fixes |
| TDD-HYDRATION.md | RENAME | TDD-0017-hierarchy-hydration.md | Hydration algorithm design |
| TDD-RESOLUTION.md | RENAME | TDD-0018-cross-holder-resolution.md | Resolution strategy pattern |
| TDD-HARDENING-A.md | RENAME | TDD-0019-foundation-hardening.md | Exceptions, logging design |
| TDD-HARDENING-B.md | RENAME | TDD-0020-custom-field-tracking.md | Tracking unification design |
| TDD-HARDENING-C.md | RENAME | TDD-0021-navigation-descriptors.md | Descriptor pattern design |
| TDD-HARDENING-F.md | RENAME | TDD-0022-savesession-reliability.md | GID identity + retryable errors |
| TDD-PATTERNS-A.md | RENAME | TDD-0023-custom-field-descriptors.md | Property descriptors design |
| TDD-PATTERNS-C.md | RENAME | TDD-0024-holder-factory.md | __init_subclass__ design |
| TDD-DESIGN-PATTERNS-D.md | RENAME | TDD-0025-async-method-decorator.md | @async_method design |
| TDD-DESIGN-PATTERNS-E.md | RENAME | TDD-0026-crud-base-class-evaluation.md | NO-GO evaluation |

---

### 2.3 Architecture (/docs/architecture/) - RELOCATE/ARCHIVE

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| business-model-tdd.md | MERGE+MOVE | design/TDD-0027-business-model-architecture.md | Merge with TDD-BIZMODEL.md |
| TDD-BIZMODEL.md | MERGE | (merged into TDD-0027) | Source for merge |
| TDD-SDKDEMO.md | MOVE | design/TDD-0028-sdk-demo.md | Misplaced TDD |
| cascading-fields-implementation.md | ARCHIVE | .archive/architecture/cascading-fields-implementation.md | Implementation notes |
| DESIGN-PATTERN-OPPORTUNITIES.md | ARCHIVE | .archive/architecture/DESIGN-PATTERN-OPPORTUNITIES.md | Analysis doc, insights extracted |

---

### 2.4 Decisions (/docs/decisions/)

#### KEEP (83 files)

ADR-0001 through ADR-0083 - all KEEP with no changes.

#### RENAME (9 files)

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| ADR-HARDENING-A-001-exception-rename-strategy.md | RENAME | ADR-0084-exception-rename-strategy.md | |
| ADR-HARDENING-A-002-observability-protocol-design.md | RENAME | ADR-0085-observability-hook-protocol.md | |
| ADR-HARDENING-A-003-logging-standardization.md | RENAME | ADR-0086-structured-logging.md | |
| ADR-HARDENING-A-004-minimal-stub-model-pattern.md | RENAME | ADR-0087-stub-model-pattern.md | |
| ADR-DEMO-001-state-capture-strategy.md | RENAME | ADR-0088-demo-state-capture.md | |
| ADR-DEMO-002-name-resolution-approach.md | RENAME | ADR-0089-demo-name-resolution.md | |
| ADR-DEMO-003-error-handling-strategy.md | RENAME | ADR-0090-demo-error-handling.md | |
| ADR-DESIGN-B-001-retryable-error-mixin.md | RENAME | ADR-0091-error-classification-mixin.md | |
| ADR-DESIGN-E-001-crud-base-class-evaluation.md | RENAME | ADR-0092-crud-base-class-nogo.md | |

---

### 2.5 Testing (/docs/testing/)

#### KEEP (2 files)

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| TEST-PLAN-0001.md | RENAME | TP-0001-sdk-phase1-parity.md | Normalize naming |
| TP-0002-intelligent-caching.md | KEEP | TP-0002-intelligent-caching.md | No change |

#### RENAME (8 files)

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| TP-batch-api-adversarial.md | RENAME | TP-0003-batch-api-adversarial.md | |
| TP-RESOLUTION.md | RENAME | TP-0004-cross-holder-resolution.md | Absorbs TP-RESOLUTION-BATCH.md |
| TP-HARDENING-A.md | RENAME | TP-0005-foundation-hardening.md | |
| TP-HARDENING-B.md | RENAME | TP-0006-custom-field-tracking.md | |
| TP-HARDENING-C.md | RENAME | TP-0007-navigation-descriptors.md | |
| TP-HYDRATION.md | RENAME | TP-0008-hierarchy-hydration.md | |
| TP-HARDENING-F.md | RENAME | TP-0009-savesession-reliability.md | |

#### MERGE (1 file)

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| TP-RESOLUTION-BATCH.md | MERGE | (into TP-0004-cross-holder-resolution.md) | See Merge Group 1 |

#### ARCHIVE (2 files)

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| NFR-VALIDATION-REPORT.md | ARCHIVE | .archive/validation/NFR-VALIDATION-REPORT.md | Point-in-time, 2025-12-08 |
| TRIAGE-SAVE-ORCHESTRATION-LAYER.md | ARCHIVE | .archive/historical/TRIAGE-SAVE-ORCHESTRATION-LAYER.md | Historical triage |

---

### 2.6 Discovery (/docs/discovery/) - ARCHIVE ALL

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| DISCOVERY-HYDRATION-001.md | EXTRACT+ARCHIVE | .archive/discovery/DISCOVERY-HYDRATION-001.md | Extract entity table first |
| DISCOVERY-PATTERNS-A-CUSTOM-FIELDS.md | EXTRACT+ARCHIVE | .archive/discovery/DISCOVERY-PATTERNS-A-CUSTOM-FIELDS.md | Extract field catalog first |
| save-orchestration-discovery.md | ARCHIVE | .archive/discovery/save-orchestration-discovery.md | |
| DISCOVERY-BIZMODEL-001.md | ARCHIVE | .archive/discovery/DISCOVERY-BIZMODEL-001.md | |
| DISCOVERY-SDKDEMO.md | ARCHIVE | .archive/discovery/DISCOVERY-SDKDEMO.md | |
| DISCOVERY-SDKUX-001.md | ARCHIVE | .archive/discovery/DISCOVERY-SDKUX-001.md | |
| DISCOVERY-RESOLUTION-001.md | ARCHIVE | .archive/discovery/DISCOVERY-RESOLUTION-001.md | |
| DISCOVERY-HARDENING-A.md | ARCHIVE | .archive/discovery/DISCOVERY-HARDENING-A.md | |
| DISCOVERY-HARDENING-B.md | ARCHIVE | .archive/discovery/DISCOVERY-HARDENING-B.md | |
| DISCOVERY-HARDENING-C.md | ARCHIVE | .archive/discovery/DISCOVERY-HARDENING-C.md | |
| DISCOVERY-HARDENING-F.md | ARCHIVE | .archive/discovery/DISCOVERY-HARDENING-F.md | |

---

### 2.7 Initiatives (/docs/initiatives/) - ARCHIVE ALL

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| PROMPT-0-HARDENING-A-FOUNDATION.md | ARCHIVE | .archive/initiatives/PROMPT-0-HARDENING-A-FOUNDATION.md | |
| PROMPT-0-HARDENING-B-CUSTOM-FIELDS.md | ARCHIVE | .archive/initiatives/PROMPT-0-HARDENING-B-CUSTOM-FIELDS.md | |
| PROMPT-0-HARDENING-C-NAVIGATION.md | ARCHIVE | .archive/initiatives/PROMPT-0-HARDENING-C-NAVIGATION.md | |
| PROMPT-0-HARDENING-D-RESOLUTION.md | ARCHIVE | .archive/initiatives/PROMPT-0-HARDENING-D-RESOLUTION.md | |
| PROMPT-0-HARDENING-E-HYDRATION.md | ARCHIVE | .archive/initiatives/PROMPT-0-HARDENING-E-HYDRATION.md | |
| PROMPT-0-HARDENING-F-SAVESESSION.md | ARCHIVE | .archive/initiatives/PROMPT-0-HARDENING-F-SAVESESSION.md | |
| PROMPT-0-HYDRATION.md | ARCHIVE | .archive/initiatives/PROMPT-0-HYDRATION.md | |
| PROMPT-0-INITIATIVE-B.md | ARCHIVE | .archive/initiatives/PROMPT-0-INITIATIVE-B.md | |
| PROMPT-0-PATTERNS-A-CUSTOM-FIELD-DESCRIPTORS.md | ARCHIVE | .archive/initiatives/PROMPT-0-PATTERNS-A-CUSTOM-FIELD-DESCRIPTORS.md | |
| PROMPT-0-RELATIONSHIP-RESOLUTION.md | ARCHIVE | .archive/initiatives/PROMPT-0-RELATIONSHIP-RESOLUTION.md | |
| PROMPT-0-RESOLUTION-BATCH.md | ARCHIVE | .archive/initiatives/PROMPT-0-RESOLUTION-BATCH.md | |
| PROMPT-MINUS-1-ARCHITECTURE-HARDENING.md | ARCHIVE | .archive/initiatives/PROMPT-MINUS-1-ARCHITECTURE-HARDENING.md | |
| PROMPT-MINUS-1-DESIGN-PATTERNS.md | ARCHIVE | .archive/initiatives/PROMPT-MINUS-1-DESIGN-PATTERNS.md | |
| PROMPT-MINUS-1-HYDRATION.md | ARCHIVE | .archive/initiatives/PROMPT-MINUS-1-HYDRATION.md | |
| PROMPT-MINUS-1-RELATIONSHIP-RESOLUTION.md | ARCHIVE | .archive/initiatives/PROMPT-MINUS-1-RELATIONSHIP-RESOLUTION.md | |
| sdk-usability-prompt-0.md | ARCHIVE | .archive/initiatives/sdk-usability-prompt-0.md | |
| sdk-usability-prompt-minus-1.md | ARCHIVE | .archive/initiatives/sdk-usability-prompt-minus-1.md | |

---

### 2.8 Validation (/docs/validation/) - ARCHIVE ALL

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| VALIDATION-BIZMODEL.md | ARCHIVE | .archive/validation/VALIDATION-BIZMODEL.md | |
| VALIDATION-HYDRATION-E.md | ARCHIVE | .archive/validation/VALIDATION-HYDRATION-E.md | |
| VALIDATION-SDKDEMO.md | ARCHIVE | .archive/validation/VALIDATION-SDKDEMO.md | |
| VR-PATTERNS-A.md | ARCHIVE | .archive/validation/VR-PATTERNS-A.md | |

---

### 2.9 Migration (/docs/migration/)

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| MIGRATION-ASYNC-METHOD.md | KEEP | MIGRATION-ASYNC-METHOD.md | Active migration guide |
| PROMPT-0-business-model-migration.md | ARCHIVE | .archive/initiatives/PROMPT-0-business-model-migration.md | Process artifact |

---

### 2.10 Root Level (/docs/)

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| INDEX.md | REWRITE | INDEX.md | Regenerate after refactor |
| CONTENT-INVENTORY.md | ARCHIVE | .archive/historical/CONTENT-INVENTORY.md | Archive after refactor complete |

---

### 2.11 Already Archived (/docs/.archive/)

| Current Path | Action | Target Path | Notes |
|--------------|--------|-------------|-------|
| .archive/CACHE_REDESIGN_EXECUTIVE_SUMMARY.md | KEEP | .archive/historical/CACHE_REDESIGN_EXECUTIVE_SUMMARY.md | Move to historical/ |
| .archive/initiatives/* (27 files) | KEEP | .archive/initiatives/* | Already archived |
| .archive/validation/* (5 files) | KEEP | .archive/validation/* | Already archived |
| .archive/decisions/ | DELETE | - | Empty directory |

---

### 2.12 Out of Scope

| Directory | Reason |
|-----------|--------|
| /docs/guides/ | User-facing documentation, separate evaluation |
| /docs/releases/ | Release notes, structure is appropriate |

---

## 3. Merge Groups - Detailed Plans

### Merge Group 1: Cross-Holder Resolution Test Plans

**Objective**: Consolidate TP-RESOLUTION.md and TP-RESOLUTION-BATCH.md into single test plan.

**Source Files**:
- `/docs/testing/TP-RESOLUTION.md` (15k, comprehensive resolution tests)
- `/docs/testing/TP-RESOLUTION-BATCH.md` (9.3k, batch-specific tests)

**Target File**: `/docs/testing/TP-0004-cross-holder-resolution.md`

**Merge Strategy**: Append with section marker

**Content Outline**:
```markdown
# TP-0004: Cross-Holder Resolution Test Plan

## Metadata
- Combined from: TP-RESOLUTION.md, TP-RESOLUTION-BATCH.md
- PRD Reference: PRD-0014-cross-holder-resolution.md
- TDD Reference: TDD-0018-cross-holder-resolution.md

## 1. Single Resolution Tests
[Content from TP-RESOLUTION.md sections 1-4]

## 2. Batch Resolution Tests
[Content from TP-RESOLUTION-BATCH.md]
- Append as new section
- Preserve all test cases
- Update internal references

## 3. Integration Tests
[Combined integration scenarios]

## Exit Criteria
[Unified exit criteria from both documents]
```

**Execution Steps**:
1. Read both source files
2. Create unified header with proper numbering
3. Copy TP-RESOLUTION.md content as base
4. Append TP-RESOLUTION-BATCH.md content as "Batch Resolution Tests" section
5. Update cross-references to use new filename
6. Save as TP-0004-cross-holder-resolution.md
7. Delete both source files

---

### Merge Group 2: Business Model TDDs

**Objective**: Consolidate business-model-tdd.md and TDD-BIZMODEL.md into single authoritative TDD.

**Source Files**:
- `/docs/architecture/business-model-tdd.md` (43k, self-identifies as TDD-0015)
- `/docs/architecture/TDD-BIZMODEL.md` (30k, detailed implementation TDD)

**Target File**: `/docs/design/TDD-0027-business-model-architecture.md`

**Merge Strategy**: Primary + supplement

**Analysis**:
- `business-model-tdd.md`: Higher-level skills architecture, comprehensive
- `TDD-BIZMODEL.md`: Implementation-focused, more granular

**Content Outline**:
```markdown
# TDD-0027: Business Model Architecture

## Metadata
- PRD Reference: PRD-0010-business-model-layer.md
- Consolidated from: business-model-tdd.md, TDD-BIZMODEL.md

## 1. Overview
[From business-model-tdd.md - executive summary]

## 2. Architecture
[From business-model-tdd.md - core architecture sections]

## 3. Implementation Details
[From TDD-BIZMODEL.md - implementation specifics]

## 4. Interface Contracts
[Merged from both sources]

## 5. Technical Decisions
[ADR references from both]
```

**Execution Steps**:
1. Read both source files
2. Use business-model-tdd.md as primary structure
3. Supplement with unique content from TDD-BIZMODEL.md
4. Resolve any conflicts (prefer more recent content)
5. Update document number to TDD-0027
6. Save to /docs/design/TDD-0027-business-model-architecture.md
7. Delete both source files from /docs/architecture/

---

## 4. Extraction Plan

### 4.1 Entity Type Table Extraction

**Source**: `/docs/discovery/DISCOVERY-HYDRATION-001.md` (Section 1.1)

**Target**: `/docs/reference/REF-entity-type-table.md`

**Content to Extract**:
```markdown
# Reference: Entity Type Table

> Extracted from: DISCOVERY-HYDRATION-001.md (Section 1.1)
> Date: 2025-12-17
> Related: PRD-0013-hierarchy-hydration.md, TDD-0017-hierarchy-hydration.md

## Entity Hierarchy

| Entity Type | Parent Type | Holder Type | Navigation Properties | Population Methods | Custom Fields |
|-------------|-------------|-------------|----------------------|-------------------|---------------|
| Business | (root) | - | contact_holder, unit_holder, ... | _populate_holders() | 19 fields |
| ContactHolder | Business | HolderMixin[Contact] | business, contacts, owner | _populate_children() | - |
| Contact | ContactHolder | - | business, contact_holder | - | 19 fields |
| UnitHolder | Business | HolderMixin[Unit] | business, units | _populate_children() | - |
| Unit | UnitHolder | - | business, unit_holder, offer_holder, ... | _populate_holders() | 31 fields |
| OfferHolder | Unit | HolderMixin[Offer] | unit, business, offers | _populate_children() | - |
| Offer | OfferHolder | - | unit, business, offer_holder | - | 39 fields |
| ProcessHolder | Unit | HolderMixin[Process] | unit, business, processes | _populate_children() | - |
| Process | ProcessHolder | - | unit, business, process_holder | - | 9 fields |
| LocationHolder | Business | HolderMixin[Location] | business, locations, hours | _populate_children() | - |
| Location | LocationHolder | - | business, location_holder | - | 8 fields |
| Hours | LocationHolder | - | business, location_holder | - | 9 fields |

## Hierarchy Depth

- Maximum downward depth from Business: 4 levels
- Maximum upward depth to Business: 4 levels
- Total traversal may span 8-9 levels (4 up + 4 down + root)
```

**Execution**:
1. Create /docs/reference/ directory
2. Extract Section 1.1 and 1.2 from DISCOVERY-HYDRATION-001.md
3. Format as standalone reference document
4. Add cross-references to PRD/TDD
5. Archive original after extraction

---

### 4.2 Custom Field Catalog Extraction

**Source**: `/docs/discovery/DISCOVERY-PATTERNS-A-CUSTOM-FIELDS.md` (Section 1)

**Target**: `/docs/reference/REF-custom-field-catalog.md`

**Content to Extract**:
```markdown
# Reference: Custom Field Catalog

> Extracted from: DISCOVERY-PATTERNS-A-CUSTOM-FIELDS.md (Section 1)
> Date: 2025-12-17
> Related: PRD-0019-custom-field-descriptors.md, TDD-0023-custom-field-descriptors.md

## Summary Statistics

| Model | Text | Enum | Multi-Enum | Number | People | Date | Total |
|-------|------|------|------------|--------|--------|------|-------|
| Business | 13 | 4 | 0 | 1 | 1 | 0 | 19 |
| Contact | 16 | 3 | 0 | 0 | 0 | 0 | 19 |
| Unit | 13 | 8 | 3 | 8 | 1 | 0 | 31 |
| Offer | [extracted] | | | | | | 39 |
| ... | | | | | | | |
| **Total** | 56 | 21 | 7 | 12 | 4 | 8 | 108 |

## Complete Field Catalog by Model

### Business Model (19 fields)
[Table from Section 1.1]

### Contact Model (19 fields)
[Table from Section 1.2]

### Unit Model (31 fields)
[Table from Section 1.3]

### Offer Model (39 fields)
[Table from Section 1.4]

[Continue for all models...]
```

**Execution**:
1. Extract Section 1 complete field tables from source
2. Add summary statistics table at top
3. Format as standalone reference document
4. Add cross-references to PRD/TDD
5. Archive original after extraction

---

## 5. Gap Analysis

### 5.1 PRD-TDD Chain Analysis

| PRD | Has TDD? | TDD Number | Gap |
|-----|----------|------------|-----|
| PRD-0001-sdk-extraction | YES | TDD-0001 | - |
| PRD-0002-intelligent-caching | YES | TDD-0008 | - |
| PRD-0003-structured-dataframe-layer | YES | TDD-0009 | - |
| PRD-0003.1-dynamic-custom-field-resolution | YES | TDD-0009.1 | - |
| PRD-0004-test-hang-fix | NO | - | **GAP**: No TDD (likely too small) |
| PRD-0005-save-orchestration | YES | TDD-0010 | - |
| PRD-0006-action-endpoint-support | YES | TDD-0011 | - |
| PRD-0007-sdk-functional-parity | YES | TDD-0012 | - |
| PRD-0008-parent-subtask-operations | YES | TDD-0013 | - |
| PRD-0009-sdk-ga-readiness | YES | TDD-0014 | - |
| PRD-0010-business-model-layer | YES | TDD-0027 | After merge |
| PRD-0011-sdk-demonstration-suite | YES | TDD-0028 | After move |
| PRD-0012-sdk-usability-improvements | YES | TDD-0015 | - |
| PRD-0013-hierarchy-hydration | YES | TDD-0017 | - |
| PRD-0014-cross-holder-resolution | YES | TDD-0018 | - |
| PRD-0015-foundation-hardening | YES | TDD-0019 | - |
| PRD-0016-custom-field-tracking | YES | TDD-0020 | - |
| PRD-0017-navigation-descriptors | YES | TDD-0021 | - |
| PRD-0018-savesession-reliability | YES | TDD-0022 | - |
| PRD-0019-custom-field-descriptors | YES | TDD-0023 | - |
| PRD-0020-holder-factory | YES | TDD-0024 | - |
| PRD-0021-async-method-generator | YES | TDD-0025 | - |
| PRD-0022-crud-base-class | YES | TDD-0026 | - |
| PRD-0023-qa-triage-fixes | YES | TDD-0016 | CASCADE-AND-FIXES-TDD |

**Gap Summary**: 1 PRD without TDD (PRD-0004, acceptable - small fix)

### 5.2 TDD-ADR Chain Analysis

| TDD | Related ADRs | Notes |
|-----|--------------|-------|
| TDD-0001 | ADR-0001 through ADR-0005 | Well-linked |
| TDD-0010 | ADR-0035 through ADR-0041 | Well-linked |
| TDD-0019 | ADR-0084 through ADR-0087 | After rename |
| TDD-0022 | ADR-0078 through ADR-0080 | Well-linked |
| TDD-0025 | **MISSING** | **GAP**: No ADR for @async_method pattern |
| TDD-0026 | ADR-0092 | After rename |

**Gap Summary**: 1 TDD missing ADR linkage (TDD-0025 for async method decorator)

### 5.3 Orphaned ADRs

ADRs without clear TDD reference (may be acceptable for cross-cutting concerns):

| ADR | Topic | Status |
|-----|-------|--------|
| ADR-0088 through ADR-0090 | Demo script ADRs | Belong to TDD-0028 (SDK Demo) |

**Action**: Update TDD-0028 to reference these ADRs after move.

### 5.4 Missing Test Plans

| Feature | Has TP? | Notes |
|---------|---------|-------|
| PRD-0010 Business Model | NO | **GAP**: No test plan |
| PRD-0011 SDK Demo | NO | **GAP**: No test plan (VALIDATION-SDKDEMO exists in archive) |
| PRD-0012 SDK Usability | NO | **GAP**: No test plan |
| PRD-0019 Custom Field Descriptors | Partial | VR-PATTERNS-A exists (validation report, not test plan) |

**Gap Summary**: 3 features without formal test plans

---

## 6. Execution Plan for Sessions 3-4

### Session 3: Archive and Delete (Low Risk)

**Duration**: ~1 hour
**Risk Level**: Low (moving to archive, no content loss)

#### Phase 3.1: Create Archive Structure (5 min)

```bash
# Ensure archive subdirectories exist
mkdir -p docs/.archive/discovery
mkdir -p docs/.archive/historical
mkdir -p docs/.archive/architecture
# initiatives/ and validation/ already exist
```

#### Phase 3.2: Archive Discovery Documents (10 min)

Execute in order:
1. **Extract reference content first** (see Section 4)
2. Move all 11 discovery files to .archive/discovery/

```bash
# After extraction complete:
mv docs/discovery/*.md docs/.archive/discovery/
rmdir docs/discovery/
```

#### Phase 3.3: Archive Initiatives Documents (10 min)

Move all 17 files from /docs/initiatives/ to .archive/initiatives/

```bash
mv docs/initiatives/*.md docs/.archive/initiatives/
rmdir docs/initiatives/
```

#### Phase 3.4: Archive Validation Documents (5 min)

Move all 4 files from /docs/validation/ to .archive/validation/

```bash
mv docs/validation/*.md docs/.archive/validation/
rmdir docs/validation/
```

#### Phase 3.5: Archive Historical Documents (5 min)

Move miscellaneous historical docs:

```bash
mv docs/requirements/TECH-DEBT.md docs/.archive/historical/
mv docs/testing/NFR-VALIDATION-REPORT.md docs/.archive/validation/
mv docs/testing/TRIAGE-SAVE-ORCHESTRATION-LAYER.md docs/.archive/historical/
mv docs/migration/PROMPT-0-business-model-migration.md docs/.archive/initiatives/
mv docs/.archive/CACHE_REDESIGN_EXECUTIVE_SUMMARY.md docs/.archive/historical/
```

#### Phase 3.6: Archive Architecture Documents (5 min)

```bash
mv docs/architecture/cascading-fields-implementation.md docs/.archive/architecture/
mv docs/architecture/DESIGN-PATTERN-OPPORTUNITIES.md docs/.archive/architecture/
```

#### Phase 3.7: Cleanup Empty Archive Directories (2 min)

```bash
rmdir docs/.archive/decisions/  # Empty
```

#### Session 3 Verification Checklist

- [ ] /docs/discovery/ directory removed (contents in .archive/discovery/)
- [ ] /docs/initiatives/ directory removed (contents in .archive/initiatives/)
- [ ] /docs/validation/ directory removed (contents in .archive/validation/)
- [ ] Historical docs moved to .archive/historical/
- [ ] Reference docs created in /docs/reference/
- [ ] No files deleted (only moved)
- [ ] Git status shows moves, no deletions

---

### Session 4: Rename and Merge (Medium Risk)

**Duration**: ~2 hours
**Risk Level**: Medium (renames affect cross-references)

#### Phase 4.1: Create Reference Directory (5 min)

```bash
mkdir -p docs/reference
```

Create extraction documents (see Section 4):
- REF-entity-type-table.md
- REF-custom-field-catalog.md

#### Phase 4.2: Execute Merges (30 min)

**Merge 1: Test Plan Resolution**

1. Read TP-RESOLUTION.md and TP-RESOLUTION-BATCH.md
2. Create TP-0004-cross-holder-resolution.md with merged content
3. Delete both source files

**Merge 2: Business Model TDDs**

1. Read business-model-tdd.md and TDD-BIZMODEL.md
2. Create TDD-0027-business-model-architecture.md
3. Move to /docs/design/
4. Delete both source files from /docs/architecture/

#### Phase 4.3: Move Misplaced Files (10 min)

```bash
# Move TDD-SDKDEMO from architecture to design
mv docs/architecture/TDD-SDKDEMO.md docs/design/TDD-0028-sdk-demo.md
```

#### Phase 4.4: Rename Requirements (20 min)

Execute renames in /docs/requirements/:

| From | To |
|------|-----|
| PRD-BIZMODEL.md | PRD-0010-business-model-layer.md |
| PRD-SDKDEMO.md | PRD-0011-sdk-demonstration-suite.md |
| PRD-SDKUX.md | PRD-0012-sdk-usability-improvements.md |
| PRD-HYDRATION.md | PRD-0013-hierarchy-hydration.md |
| PRD-RESOLUTION.md | PRD-0014-cross-holder-resolution.md |
| PRD-HARDENING-A.md | PRD-0015-foundation-hardening.md |
| PRD-HARDENING-B.md | PRD-0016-custom-field-tracking.md |
| PRD-HARDENING-C.md | PRD-0017-navigation-descriptors.md |
| PRD-HARDENING-F.md | PRD-0018-savesession-reliability.md |
| PRD-PATTERNS-A.md | PRD-0019-custom-field-descriptors.md |
| PRD-PATTERNS-C.md | PRD-0020-holder-factory.md |
| PRD-DESIGN-PATTERNS-D.md | PRD-0021-async-method-generator.md |
| PRD-DESIGN-PATTERNS-E.md | PRD-0022-crud-base-class.md |
| TRIAGE-FIXES-REQUIREMENTS.md | PRD-0023-qa-triage-fixes.md |

#### Phase 4.5: Rename Designs (20 min)

Execute renames in /docs/design/:

| From | To |
|------|-----|
| TDD-SDKUX.md | TDD-0015-sdk-usability.md |
| CASCADE-AND-FIXES-TDD.md | TDD-0016-cascade-and-fixes.md |
| TDD-HYDRATION.md | TDD-0017-hierarchy-hydration.md |
| TDD-RESOLUTION.md | TDD-0018-cross-holder-resolution.md |
| TDD-HARDENING-A.md | TDD-0019-foundation-hardening.md |
| TDD-HARDENING-B.md | TDD-0020-custom-field-tracking.md |
| TDD-HARDENING-C.md | TDD-0021-navigation-descriptors.md |
| TDD-HARDENING-F.md | TDD-0022-savesession-reliability.md |
| TDD-PATTERNS-A.md | TDD-0023-custom-field-descriptors.md |
| TDD-PATTERNS-C.md | TDD-0024-holder-factory.md |
| TDD-DESIGN-PATTERNS-D.md | TDD-0025-async-method-decorator.md |
| TDD-DESIGN-PATTERNS-E.md | TDD-0026-crud-base-class-evaluation.md |

#### Phase 4.6: Rename Decisions (10 min)

Execute renames in /docs/decisions/:

| From | To |
|------|-----|
| ADR-HARDENING-A-001-exception-rename-strategy.md | ADR-0084-exception-rename-strategy.md |
| ADR-HARDENING-A-002-observability-protocol-design.md | ADR-0085-observability-hook-protocol.md |
| ADR-HARDENING-A-003-logging-standardization.md | ADR-0086-structured-logging.md |
| ADR-HARDENING-A-004-minimal-stub-model-pattern.md | ADR-0087-stub-model-pattern.md |
| ADR-DEMO-001-state-capture-strategy.md | ADR-0088-demo-state-capture.md |
| ADR-DEMO-002-name-resolution-approach.md | ADR-0089-demo-name-resolution.md |
| ADR-DEMO-003-error-handling-strategy.md | ADR-0090-demo-error-handling.md |
| ADR-DESIGN-B-001-retryable-error-mixin.md | ADR-0091-error-classification-mixin.md |
| ADR-DESIGN-E-001-crud-base-class-evaluation.md | ADR-0092-crud-base-class-nogo.md |

#### Phase 4.7: Rename Test Plans (10 min)

Execute renames in /docs/testing/:

| From | To |
|------|-----|
| TEST-PLAN-0001.md | TP-0001-sdk-phase1-parity.md |
| TP-batch-api-adversarial.md | TP-0003-batch-api-adversarial.md |
| TP-HARDENING-A.md | TP-0005-foundation-hardening.md |
| TP-HARDENING-B.md | TP-0006-custom-field-tracking.md |
| TP-HARDENING-C.md | TP-0007-navigation-descriptors.md |
| TP-HYDRATION.md | TP-0008-hierarchy-hydration.md |
| TP-HARDENING-F.md | TP-0009-savesession-reliability.md |

Note: TP-RESOLUTION.md and TP-RESOLUTION-BATCH.md already merged in Phase 4.2.

#### Phase 4.8: Update Cross-References (20 min)

Search and replace old filenames with new filenames across all documents:

1. Search for each old filename
2. Replace with corresponding new filename
3. Priority targets:
   - INDEX.md
   - All PRD files (TDD references)
   - All TDD files (ADR references)
   - CLAUDE.md and skills files

#### Phase 4.9: Regenerate INDEX.md (15 min)

Rewrite /docs/INDEX.md with:
- Updated file listing
- Correct paths
- Updated counts
- Next available numbers

#### Phase 4.10: Archive Inventory (2 min)

```bash
mv docs/CONTENT-INVENTORY.md docs/.archive/historical/
```

#### Session 4 Verification Checklist

- [ ] All renames complete (no codename files remain)
- [ ] All merges complete (no duplicate content)
- [ ] Reference documents created
- [ ] Cross-references updated
- [ ] INDEX.md regenerated
- [ ] No broken links
- [ ] Git status clean after commit

---

## 7. Post-Refactor State

### Final Directory Structure

```
/docs/
├── INDEX.md                          # Regenerated
├── requirements/                     # 24 PRDs (PRD-0001 through PRD-0023 + 0003.1)
├── design/                           # 28 TDDs (TDD-0001 through TDD-0028 + 0009.1)
├── decisions/                        # 92 ADRs (ADR-0001 through ADR-0092)
├── testing/                          # 9 TPs (TP-0001 through TP-0009)
├── guides/                           # Unchanged (7 files)
├── releases/                         # Unchanged (1 file)
├── migration/                        # 1 file (MIGRATION-ASYNC-METHOD.md)
├── reference/                        # NEW: 2 files
│   ├── REF-entity-type-table.md
│   └── REF-custom-field-catalog.md
└── .archive/                         # ~65 files
    ├── initiatives/                  # ~44 files
    ├── discovery/                    # 11 files
    ├── validation/                   # ~10 files
    ├── historical/                   # ~6 files
    └── architecture/                 # 2 files
```

### Next Available Numbers

| Type | After Refactor |
|------|----------------|
| PRD | PRD-0024 |
| TDD | TDD-0029 |
| ADR | ADR-0093 |
| TP | TP-0010 |

---

## 8. Quality Gate Checklist

- [x] Every file from the inventory appears in the mapping (107 files mapped)
- [x] Target directory structure is complete (8 active directories + archive)
- [x] All merge groups have detailed execution plans (2 merge groups)
- [x] Extraction plan covers all flagged content (2 extractions)
- [x] Gap analysis identifies documentation holes (4 gaps identified)
- [x] Execution plan is ordered to minimize risk (Session 3: low, Session 4: medium)
- [x] A Principal Engineer could execute Sessions 3-4 from this document alone

---

## Appendix A: File Count Summary

| Category | Count |
|----------|-------|
| Files to KEEP (unchanged) | 109 (83 ADRs + 14 TDDs + 10 PRDs + 2 TPs) |
| Files to RENAME | 44 |
| Files to ARCHIVE | 42 |
| Files to MERGE | 4 (into 2) |
| Files to MOVE | 1 |
| Files to EXTRACT FROM | 2 |
| New files to CREATE | 2 (reference docs) |
| **Total files processed** | ~107 |

---

## Appendix B: Risk Mitigation

### Rollback Strategy

All operations are reversible:
- Archives preserve original content
- Git history tracks all moves/renames
- No files are permanently deleted

### Backup Recommendation

Before Session 3:
```bash
git checkout -b docs-refactor-backup
git add -A
git commit -m "Pre-refactor backup"
git checkout main
```

### Verification Scripts

After each phase, run:
```bash
# Check for broken internal links
grep -r "\.md)" docs/ | grep -v ".archive" | grep -v "http"

# Count files by type
find docs -name "PRD-*.md" | wc -l
find docs -name "TDD-*.md" | wc -l
find docs -name "ADR-*.md" | wc -l
find docs -name "TP-*.md" | wc -l
```
