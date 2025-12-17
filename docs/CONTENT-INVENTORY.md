# Documentation Content Inventory

> Generated: 2025-12-17
> Purpose: Content audit of `/docs` directory for documentation refactor initiative

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Documents Audited** | ~107 |
| **KEEP (well-named)** | 24 |
| **RENAME (good content, bad name)** | 35 |
| **ARCHIVE (process artifact)** | 33 |
| **MERGE (redundant)** | 10 |
| **MOVE (misplaced)** | 5 |
| **DELETE** | 0 |

### Key Findings

1. **Well-named docs exist**: PRD-0001 through PRD-0009 and TDD-0001 through TDD-0014 follow good content-based naming
2. **Sprint codenames dominate**: ~40 docs use HARDENING-*, HYDRATION, RESOLUTION, PATTERNS-* naming
3. **Process artifacts preserved as docs**: 17 PROMPT-0/PROMPT-MINUS-1 files, 11 DISCOVERY-* files
4. **ADRs have naming drift**: Sequential numbering (ADR-0001-0083) is good, but ADR-HARDENING-A-*, ADR-DEMO-*, ADR-DESIGN-* break pattern
5. **Validation reports are point-in-time**: 4 files that should be archived or converted to status docs
6. **Misplaced files**: 5 TDDs in `/docs/architecture/` should be moved to `/docs/design/`

### Next Available Document Numbers

| Type | Highest Existing | Next Available |
|------|------------------|----------------|
| PRD | PRD-0009 | PRD-0010 |
| TDD | TDD-0014 | TDD-0015 |
| ADR | ADR-0083 | ADR-0084 |
| TP | TP-0002 | TP-0003 |

---

## Requirements (/docs/requirements/)

### Well-Named (KEEP)

| File | Actual Content | Status | Recommendation |
|------|----------------|--------|----------------|
| PRD-0001-sdk-extraction.md | SDK extraction from autom8 monolith | Completed | **KEEP** |
| PRD-0002-intelligent-caching.md | Multi-tier caching with staleness detection | Draft | **KEEP** |
| PRD-0003-structured-dataframe-layer.md | Polars-based dataframe generation from tasks | In Review | **KEEP** |
| PRD-0003.1-dynamic-custom-field-resolution.md | Runtime custom field GID resolution | Draft | **KEEP** |
| PRD-0004-test-hang-fix.md | Thread join timeout fixes for test suite | Implemented | **KEEP** |
| PRD-0005-save-orchestration.md | Unit of Work pattern for batch persistence | Draft | **KEEP** |
| PRD-0006-action-endpoint-support.md | Action endpoints (tags, projects, sections) | Draft | **KEEP** |
| PRD-0007-sdk-functional-parity.md | Full Asana action coverage in SaveSession | Draft | **KEEP** |
| PRD-0008-parent-subtask-operations.md | setParent action support | Draft | **KEEP** |
| PRD-0009-sdk-ga-readiness.md | GA readiness checklist and gaps | Draft | **KEEP** |

### Codename-Based (RENAME)

| File | Actual Content | Status | Recommendation | Suggested Name |
|------|----------------|--------|----------------|----------------|
| PRD-BIZMODEL.md | Business model layer with typed entities and hierarchy navigation | Draft | **RENAME** | `PRD-0010-business-model-layer.md` |
| PRD-SDKDEMO.md | SDK demonstration script for validation | Draft | **RENAME** | `PRD-0011-sdk-demonstration-suite.md` |
| PRD-SDKUX.md | SDK usability overhaul - convenience methods, implicit sessions | Approved | **RENAME** | `PRD-0012-sdk-usability-improvements.md` |
| PRD-HYDRATION.md | Business model hierarchy loading from any entry point | Draft | **RENAME** | `PRD-0013-hierarchy-hydration.md` |
| PRD-RESOLUTION.md | Cross-holder relationship resolution (AssetEdit to Unit/Offer) | Draft | **RENAME** | `PRD-0014-cross-holder-resolution.md` |
| PRD-HARDENING-A.md | Exception naming, logging, observability hooks | Draft | **RENAME** | `PRD-0015-foundation-hardening.md` |
| PRD-HARDENING-B.md | Custom field change tracking unification | Draft | **RENAME** | `PRD-0016-custom-field-tracking.md` |
| PRD-HARDENING-C.md | Navigation pattern consolidation (800+ lines dedup) | Draft | **RENAME** | `PRD-0017-navigation-descriptors.md` |
| PRD-HARDENING-F.md | SaveSession reliability - GID identity, retryable errors | Draft | **RENAME** | `PRD-0018-savesession-reliability.md` |
| PRD-PATTERNS-A.md | Custom field property descriptors | Draft | **RENAME** | `PRD-0019-custom-field-descriptors.md` |
| PRD-PATTERNS-C.md | Holder factory with __init_subclass__ | Active | **RENAME** | `PRD-0020-holder-factory.md` |
| PRD-DESIGN-PATTERNS-D.md | Async/sync method generator decorator | Active | **RENAME** | `PRD-0021-async-method-generator.md` |
| PRD-DESIGN-PATTERNS-E.md | CRUD client base class (evaluation doc) | Active | **RENAME** | `PRD-0022-crud-base-class.md` |

### Non-Standard (RENAME or ARCHIVE)

| File | Actual Content | Status | Recommendation | Notes |
|------|----------------|--------|----------------|-------|
| TRIAGE-FIXES-REQUIREMENTS.md | QA findings triage - 5 critical/high bugs | Ready for Review | **RENAME** | `PRD-00XX-qa-triage-fixes.md` - actionable requirements |
| TECH-DEBT.md | Tech debt backlog from QA review - P3-P5 items | Tracked | **ARCHIVE** | Backlog tracking, not active requirements |

---

## Design (/docs/design/)

### Well-Named (KEEP)

| File | Actual Content | Status | Recommendation |
|------|----------------|--------|----------------|
| TDD-0001-sdk-architecture.md | Overall SDK architecture, protocol design | Draft | **KEEP** |
| TDD-0002-models-pagination.md | Pydantic models and pagination | Draft | **KEEP** |
| TDD-0003-tier1-clients.md | Tasks, Projects, Sections clients | Draft | **KEEP** |
| TDD-0004-tier2-clients.md | Additional resource clients | Draft | **KEEP** |
| TDD-0005-batch-api.md | Batch API client design | Draft | **KEEP** |
| TDD-0006-backward-compatibility.md | Migration strategy for breaking changes | Draft | **KEEP** |
| TDD-0007-observability.md | Logging, metrics, tracing design | Draft | **KEEP** |
| TDD-0008-intelligent-caching.md | Cache architecture and staleness | Draft | **KEEP** |
| TDD-0009-structured-dataframe-layer.md | Dataframe generation design | Draft | **KEEP** |
| TDD-0009.1-dynamic-custom-field-resolution.md | Custom field resolver design | Draft | **KEEP** |
| TDD-0010-save-orchestration.md | SaveSession architecture | Draft | **KEEP** |
| TDD-0011-action-endpoint-support.md | Action operations design | Draft | **KEEP** |
| TDD-0012-sdk-functional-parity.md | Full action coverage design | Draft | **KEEP** |
| TDD-0013-parent-subtask-operations.md | setParent implementation | Draft | **KEEP** |
| TDD-0014-sdk-ga-readiness.md | GA readiness implementation | Draft | **KEEP** |

### Codename-Based (RENAME)

| File | Actual Content | Status | Recommendation | Suggested Name |
|------|----------------|--------|----------------|----------------|
| TDD-SDKUX.md | SDK usability - convenience methods, implicit sessions | Ready | **RENAME** | `TDD-0015-sdk-usability.md` |
| CASCADE-AND-FIXES-TDD.md | Cascade execution + QA bug fixes design | Draft | **RENAME** | `TDD-0016-cascade-and-fixes.md` |
| TDD-HYDRATION.md | Hierarchy hydration algorithm design | Draft | **RENAME** | `TDD-0017-hierarchy-hydration.md` |
| TDD-RESOLUTION.md | Cross-holder resolution strategy pattern | Draft | **RENAME** | `TDD-0018-cross-holder-resolution.md` |
| TDD-HARDENING-A.md | Foundation hardening - exceptions, logging | Draft | **RENAME** | `TDD-0019-foundation-hardening.md` |
| TDD-HARDENING-B.md | Custom field tracking unification | Draft | **RENAME** | `TDD-0020-custom-field-tracking.md` |
| TDD-HARDENING-C.md | Navigation descriptor pattern | Draft | **RENAME** | `TDD-0021-navigation-descriptors.md` |
| TDD-HARDENING-F.md | SaveSession GID identity + retryable errors | Draft | **RENAME** | `TDD-0022-savesession-reliability.md` |
| TDD-PATTERNS-A.md | Custom field property descriptors | Draft | **RENAME** | `TDD-0023-custom-field-descriptors.md` |
| TDD-PATTERNS-C.md | Holder factory __init_subclass__ | Active | **RENAME** | `TDD-0024-holder-factory.md` |
| TDD-DESIGN-PATTERNS-D.md | @async_method decorator design | Active | **RENAME** | `TDD-0025-async-method-decorator.md` |
| TDD-DESIGN-PATTERNS-E.md | CRUD base class (NO-GO evaluation) | Active | **RENAME** | `TDD-0026-crud-base-class-evaluation.md` |

---

## Decisions (/docs/decisions/)

### Well-Named (KEEP) - 83 ADRs

ADR-0001 through ADR-0083 follow good naming: `ADR-NNNN-descriptive-slug.md`

Examples:
- ADR-0001-protocol-extensibility.md
- ADR-0035-unit-of-work-pattern.md
- ADR-0074-unified-custom-field-tracking.md

**Recommendation**: All sequential ADRs (0001-0083) are **KEEP**

### Sprint Codename ADRs (RENAME)

| File | Actual Content | Recommendation | Suggested Name |
|------|----------------|----------------|----------------|
| ADR-HARDENING-A-001-exception-rename-strategy.md | ValidationError rename to GidValidationError | **RENAME** | `ADR-0084-exception-rename-strategy.md` |
| ADR-HARDENING-A-002-observability-protocol-design.md | ObservabilityHook protocol design | **RENAME** | `ADR-0085-observability-hook-protocol.md` |
| ADR-HARDENING-A-003-logging-standardization.md | Structured logging with LogContext | **RENAME** | `ADR-0086-structured-logging.md` |
| ADR-HARDENING-A-004-minimal-stub-model-pattern.md | Stub model pattern for DNA, Reconciliation | **RENAME** | `ADR-0087-stub-model-pattern.md` |
| ADR-DEMO-001-state-capture-strategy.md | Demo script state capture for rollback | **RENAME** | `ADR-0088-demo-state-capture.md` |
| ADR-DEMO-002-name-resolution-approach.md | Demo script name-to-GID resolution | **RENAME** | `ADR-0089-demo-name-resolution.md` |
| ADR-DEMO-003-error-handling-strategy.md | Demo script error handling | **RENAME** | `ADR-0090-demo-error-handling.md` |
| ADR-DESIGN-B-001-retryable-error-mixin.md | Error classification mixin pattern | **RENAME** | `ADR-0091-error-classification-mixin.md` |
| ADR-DESIGN-E-001-crud-base-class-evaluation.md | CRUD base class NO-GO decision | **RENAME** | `ADR-0092-crud-base-class-nogo.md` |

---

## Testing (/docs/testing/)

| File | Actual Content | Status | Recommendation | Notes |
|------|----------------|--------|----------------|-------|
| TEST-PLAN-0001.md | SDK Phase 1 parity validation | Draft | **KEEP** | Good naming |
| TP-batch-api-adversarial.md | Batch API edge case testing | Completed | **RENAME** | `TP-0003-batch-api-adversarial.md` |
| NFR-VALIDATION-REPORT.md | Non-functional requirements validation | Complete | **ARCHIVE** | Point-in-time, 2025-12-08 |
| TP-0002-intelligent-caching.md | Caching test plan | Draft | **KEEP** | Good naming |
| TRIAGE-SAVE-ORCHESTRATION-LAYER.md | Save orchestration bug triage | N/A | **ARCHIVE** | Historical triage, not test plan |
| TP-RESOLUTION.md | Cross-holder resolution tests | Approved | **RENAME** | `TP-0004-cross-holder-resolution.md` |
| TP-RESOLUTION-BATCH.md | Batch resolution tests | N/A | **MERGE** | Merge into TP-0004 |
| TP-HARDENING-A.md | Foundation hardening tests | Approved | **RENAME** | `TP-0005-foundation-hardening.md` |
| TP-HARDENING-B.md | Custom field tracking tests | N/A | **RENAME** | `TP-0006-custom-field-tracking.md` |
| TP-HARDENING-C.md | Navigation descriptor tests | N/A | **RENAME** | `TP-0007-navigation-descriptors.md` |
| TP-HYDRATION.md | Hierarchy hydration tests | PASS | **RENAME** | `TP-0008-hierarchy-hydration.md` |
| TP-HARDENING-F.md | SaveSession reliability tests | N/A | **RENAME** | `TP-0009-savesession-reliability.md` |

---

## Discovery (/docs/discovery/)

**Recommendation**: All discovery documents should be **ARCHIVED** after extracting unique insights into surviving PRDs/TDDs/ADRs.

| File | Actual Content | Unique Insights | Recommendation |
|------|----------------|-----------------|----------------|
| save-orchestration-discovery.md | Save orchestration research | Extracted to PRD-0005 | **ARCHIVE** |
| DISCOVERY-BIZMODEL-001.md | Business model analysis | Extracted to PRD-BIZMODEL | **ARCHIVE** |
| DISCOVERY-SDKDEMO.md | Demo script research | Extracted to PRD-SDKDEMO | **ARCHIVE** |
| DISCOVERY-SDKUX-001.md | SDK usability pain points | Extracted to PRD-SDKUX | **ARCHIVE** |
| DISCOVERY-HYDRATION-001.md | Hydration infrastructure analysis | Contains entity table - **EXTRACT** | **ARCHIVE** after extraction |
| DISCOVERY-RESOLUTION-001.md | Resolution strategy research | Extracted to PRD-RESOLUTION | **ARCHIVE** |
| DISCOVERY-HARDENING-A.md | Foundation issues audit | Extracted to PRD-HARDENING-A | **ARCHIVE** |
| DISCOVERY-HARDENING-B.md | Custom field tracking audit | Extracted to PRD-HARDENING-B | **ARCHIVE** |
| DISCOVERY-HARDENING-C.md | Navigation pattern audit | Extracted to PRD-HARDENING-C | **ARCHIVE** |
| DISCOVERY-HARDENING-F.md | SaveSession issues audit | Extracted to PRD-HARDENING-F | **ARCHIVE** |
| DISCOVERY-PATTERNS-A-CUSTOM-FIELDS.md | Complete field catalog (108 fields) | Contains full catalog - **EXTRACT** | **ARCHIVE** after extraction |

### Insights to Extract Before Archiving

1. **DISCOVERY-HYDRATION-001.md**: Entity type table (1.1) is comprehensive reference - move to TDD or keep as appendix
2. **DISCOVERY-PATTERNS-A-CUSTOM-FIELDS.md**: Complete field catalog by model - move to TDD or reference doc

---

## Initiatives (/docs/initiatives/)

**Recommendation**: All PROMPT-0 and PROMPT-MINUS-1 files are **process inputs**, not documentation. **ARCHIVE** all.

| File | Type | Recommendation |
|------|------|----------------|
| sdk-usability-prompt-minus-1.md | Prompt -1 | **ARCHIVE** |
| sdk-usability-prompt-0.md | Prompt 0 | **ARCHIVE** |
| PROMPT-MINUS-1-HYDRATION.md | Prompt -1 | **ARCHIVE** |
| PROMPT-0-HYDRATION.md | Prompt 0 | **ARCHIVE** |
| PROMPT-MINUS-1-RELATIONSHIP-RESOLUTION.md | Prompt -1 | **ARCHIVE** |
| PROMPT-0-RELATIONSHIP-RESOLUTION.md | Prompt 0 | **ARCHIVE** |
| PROMPT-0-RESOLUTION-BATCH.md | Prompt 0 | **ARCHIVE** |
| PROMPT-MINUS-1-ARCHITECTURE-HARDENING.md | Prompt -1 | **ARCHIVE** |
| PROMPT-0-HARDENING-A-FOUNDATION.md | Prompt 0 | **ARCHIVE** |
| PROMPT-0-HARDENING-B-CUSTOM-FIELDS.md | Prompt 0 | **ARCHIVE** |
| PROMPT-0-HARDENING-C-NAVIGATION.md | Prompt 0 | **ARCHIVE** |
| PROMPT-0-HARDENING-D-RESOLUTION.md | Prompt 0 | **ARCHIVE** |
| PROMPT-0-HARDENING-E-HYDRATION.md | Prompt 0 | **ARCHIVE** |
| PROMPT-0-HARDENING-F-SAVESESSION.md | Prompt 0 | **ARCHIVE** |
| PROMPT-MINUS-1-DESIGN-PATTERNS.md | Prompt -1 | **ARCHIVE** |
| PROMPT-0-PATTERNS-A-CUSTOM-FIELD-DESCRIPTORS.md | Prompt 0 | **ARCHIVE** |
| PROMPT-0-INITIATIVE-B.md | Prompt 0 | **ARCHIVE** |

---

## Validation (/docs/validation/)

**Recommendation**: All validation reports are **point-in-time snapshots**. **ARCHIVE** as historical records.

| File | Actual Content | Date | Recommendation |
|------|----------------|------|----------------|
| VALIDATION-BIZMODEL.md | Business model validation | N/A | **ARCHIVE** |
| VALIDATION-SDKDEMO.md | Demo script validation | N/A | **ARCHIVE** |
| VALIDATION-HYDRATION-E.md | Hydration performance validation | 2025-12-16 | **ARCHIVE** |
| VR-PATTERNS-A.md | Custom field descriptors validation | N/A | **ARCHIVE** |

---

## Other Files

### Root Level

| File | Content | Recommendation |
|------|---------|----------------|
| INDEX.md | Documentation registry | **REWRITE** after refactor |

### Directories to Keep As-Is

- `/docs/guides/` - **OUT OF SCOPE** (user-facing, separate evaluation)
- `/docs/releases/` - Keep as-is (release notes)
- `/docs/.archive/` - Already archived content

---

## Architecture (/docs/architecture/)

**Note**: This directory contains misplaced documents that should be moved.

| File | Actual Content | Status | Recommendation | Notes |
|------|----------------|--------|----------------|-------|
| business-model-tdd.md | Business Model Skills Architecture (self-identifies as TDD-0015) | Draft | **MOVE** to `/docs/design/TDD-0015-business-model-architecture.md` | Misplaced TDD |
| TDD-BIZMODEL.md | Business Model Layer Implementation (detailed implementation TDD) | Draft | **MERGE** with business-model-tdd.md, move to design/ | Likely redundant with above |
| TDD-SDKDEMO.md | SDK Demo TDD | N/A | **MOVE** to `/docs/design/TDD-00XX-sdk-demo.md` | Misplaced TDD |
| cascading-fields-implementation.md | Cascading fields implementation details | N/A | **ARCHIVE** | Implementation notes, not architecture |
| DESIGN-PATTERN-OPPORTUNITIES.md | 5 high-impact pattern opportunities analysis | 2025-12-16 | **ARCHIVE** | Analysis doc, insights extracted to PRD-PATTERNS-* |

---

## Migration (/docs/migration/)

| File | Actual Content | Status | Recommendation | Notes |
|------|----------------|--------|----------------|-------|
| MIGRATION-ASYNC-METHOD.md | @async_method decorator migration guide | Active | **KEEP** | Useful migration guide for Initiative D |
| PROMPT-0-business-model-migration.md | Business model migration prompt | N/A | **ARCHIVE** | Process artifact |

---

## Merge Groups

### Merge Group 1: Cross-Holder Resolution

**Sources**:
- PRD-RESOLUTION.md
- TDD-RESOLUTION.md
- TP-RESOLUTION.md
- TP-RESOLUTION-BATCH.md

**Target Structure**: Keep separate PRD/TDD/TP but rename and merge TP-RESOLUTION-BATCH into main test plan.

### Merge Group 2: Custom Field Patterns

**Sources**:
- PRD-PATTERNS-A.md (custom field descriptors)
- PRD-HARDENING-B.md (custom field tracking)
- DISCOVERY-PATTERNS-A-CUSTOM-FIELDS.md (field catalog)

**Consideration**: These cover different aspects:
- PATTERNS-A: Declarative descriptor syntax
- HARDENING-B: Change tracking state management
- DISCOVERY: Reference data

**Recommendation**: Keep PRDs separate (different concerns), archive discovery, link between them.

---

## Recommended Archive Structure

```
docs/
├── .archive/
│   ├── initiatives/          # All PROMPT-0, PROMPT-MINUS-1 files
│   │   ├── PROMPT-0-HYDRATION.md
│   │   └── ...
│   ├── discovery/            # All DISCOVERY-* files
│   │   ├── DISCOVERY-HYDRATION-001.md
│   │   └── ...
│   ├── validation/           # All VALIDATION-*, VR-* files
│   │   ├── VALIDATION-HYDRATION-E.md
│   │   └── ...
│   └── historical/           # One-off historical docs
│       ├── TECH-DEBT.md
│       ├── NFR-VALIDATION-REPORT.md
│       └── TRIAGE-SAVE-ORCHESTRATION-LAYER.md
```

---

## Action Items Summary

### Phase 1: Archive Process Artifacts (~28 files)
1. Create archive directory structure
2. Move all PROMPT-0/PROMPT-MINUS-1 files
3. Move all DISCOVERY-* files (after extraction)
4. Move all VALIDATION-*/VR-* files
5. Move historical docs (TECH-DEBT, NFR-VALIDATION-REPORT)

### Phase 2: Rename to Content-Based Names (~35 files)
1. PRD codename docs -> PRD-NNNN-slug.md (13 files)
2. TDD codename docs -> TDD-NNNN-slug.md (12 files)
3. ADR sprint codenames -> ADR-NNNN-slug.md (9 files)
4. TP codename docs -> TP-NNNN-slug.md (8 files)

### Phase 3: Update Cross-References
1. Update all internal links to renamed files
2. Regenerate INDEX.md
3. Update CLAUDE.md skill references if needed

### Phase 4: Validate
1. Newcomer test: Can someone navigate the docs?
2. Link integrity check: No broken references
3. Quality check: Every name describes content
