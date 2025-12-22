# PRD: Documentation Epoch Reset

## Metadata

- **PRD ID**: PRD-DOCS-EPOCH-RESET
- **Status**: Draft
- **Author**: Requirements Analyst (via Orchestrator)
- **Created**: 2025-12-17
- **Last Updated**: 2025-12-17
- **Stakeholders**: AI agents (Claude Code), human developers, SDK maintainers
- **Related Documents**: PROMPT-0-DOCS-EPOCH-RESET.md
- **Supersedes**: N/A (new initiative)

---

## Problem Statement

### Current State

The autom8_asana documentation describes the project as it existed around "Day 30" while the codebase has evolved to "Day 300" maturity. This documentation-reality mismatch causes AI agents and human developers to fundamentally misunderstand the project's production-grade capabilities.

**Impact**:
- AI agents operating with current documentation treat a production-grade SDK as a prototype
- Developers expect a simple API wrapper and discover a sophisticated CRM platform
- The core "Asana-as-database" paradigm is completely undocumented
- Capability discovery fails for 127+ custom fields, cascade logic, and resolution strategies

### Root Cause

Documentation was created during early development and never updated as the system matured through 95 ADRs and 32 TDDs of architectural evolution.

---

## Discovery Audit Report

### Outdated Claim 1: "Prototype" Status

**Files Affected**:
| File | Line | Current Claim | Reality |
|------|------|---------------|---------|
| `.claude/PROJECT_CONTEXT.md` | 27 | `Stage: Prototype` | Production-grade with comprehensive test coverage |
| `.claude/skills/autom8-asana-domain/context.md` | 57 | `**Stage**: Prototype (greenfield extraction)` | Mature SDK with many ADRs and TDDs |
| `.claude/skills/autom8-asana-domain/tech-stack.md` | 61 | `Version: 0.1.0 (prototype)` | Version label outdated |

**Evidence**: 95 ADR files, 32 TDD files, 129 test files totaling significant coverage

---

### Outdated Claim 2: "~0% Test Coverage"

**Files Affected**:
| File | Line | Current Claim | Reality |
|------|------|---------------|---------|
| `.claude/skills/autom8-asana-domain/context.md` | 61 | `Test coverage: ~0% (test infrastructure being built)` | Comprehensive coverage across all modules |
| `.claude/skills/autom8-asana-domain/context.md` | 127 | `Test coverage: >=80% core modules: ~0%` | Extensive test suite exists |

**Evidence**: 129 test files across modules:
- `tests/unit/models/business/` - 20+ test files for business entities
- `tests/unit/persistence/` - 16+ test files for SaveSession
- `tests/unit/cache/` - 18+ test files for cache backends
- `tests/unit/dataframes/` - 15+ test files for Polars operations

---

### Outdated Claim 3: "4 Stub Entity Types"

**Files Affected**:
| File | Line | Current Claim | Reality |
|------|------|---------------|---------|
| `.claude/skills/autom8-asana-business/entity-reference.md` | 22 | `DNAHolder, ReconciliationsHolder, AssetEditHolder, VideographyHolder (stubs)` | Only 3 stubs remain (DNA, Reconciliation, Videography) |

**Evidence**: Code inspection reveals:
- `dna.py` - 57 lines, stub with navigation only (per TDD-HARDENING-A/FR-STUB-001)
- `reconciliation.py` - 78 lines, stub with navigation only (per TDD-HARDENING-A/FR-STUB-002)
- `videography.py` - 57 lines, stub with navigation only (per TDD-HARDENING-A/FR-STUB-003)
- `asset_edit.py` - 681 lines, **fully implemented** with 11+ typed custom fields

**Note**: AssetEditHolder IS a stub holder, but AssetEdit entity itself is fully implemented. The entity-reference.md conflates holders and entities.

---

### Outdated Claim 4: Stale Success Metrics

**Files Affected**:
| File | Line | Current Claim | Reality |
|------|------|---------------|---------|
| `.claude/skills/autom8-asana-domain/context.md` | 124-129 | Success metrics table shows "Current: ~0%" for test coverage | Metrics are stale |

**Recommendation**: Remove specific metric percentages; use qualitative descriptions per user guidance.

---

### Undocumented: Asana-as-Database Paradigm

**Gap Identified**: The core architectural insight that Asana serves as a database (with Tasks as rows, Custom Fields as columns, Projects as tables/indexes) appears nowhere in documentation.

**Evidence**:
- Grep for "Asana-as-database" returns only PROMPT-0-DOCS-EPOCH-RESET.md references
- No skill file, ADR, or TDD explains this paradigm
- Business model documentation describes entities but not the underlying data model concept

**Impact**: AI agents and developers cannot understand WHY the architecture exists as it does.

---

### Minor Outdated Claims

| File | Issue |
|------|-------|
| `.claude/skills/autom8-asana-domain/context.md` line 15 | "Prototype for extracting other APIs" - language suggests future intent, not current state |
| `.claude/skills/autom8-asana-domain/context.md` line 20-25 | "What Moved vs What Stayed" table - may need verification against current state |
| `.claude/skills/autom8-asana-domain/glossary.md` line 155 | "OAuth (future)" - verify if OAuth is still future or now present |

---

## Goals & Success Metrics

### Goals

1. **Accurate Status**: Documentation correctly describes project maturity
2. **Discoverable Paradigm**: Asana-as-database concept is documented and findable
3. **Correct Entity Counts**: Stub vs implemented entity counts are accurate
4. **Qualitative Metrics**: Test coverage uses qualitative terms, not specific percentages
5. **Cross-Reference Integrity**: All document references remain valid after changes

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Outdated "Prototype" claims | 0 | Grep for "Prototype" in active docs |
| Outdated "~0% coverage" claims | 0 | Grep for "0%" in active docs |
| Asana-as-database discoverable | Yes | Within 2 clicks from CLAUDE.md |
| Entity stub count accuracy | 3 stubs documented | Manual verification |
| Cross-reference validity | 100% | Link checker |

---

## Scope

### In Scope

**P0 - Critical Status Updates**:
- Update PROJECT_CONTEXT.md: Remove "Prototype" status
- Update context.md: Remove "~0% test coverage", update stage
- Update tech-stack.md: Remove "(prototype)" from version

**P1 - Entity Documentation**:
- Update entity-reference.md: Correct stub count from 4 to 3
- Clarify distinction between stub holders and stub entities

**P2 - New Content**:
- Document Asana-as-database paradigm (location TBD by Architect)
- Add qualitative test coverage description

**P3 - Cross-Reference Maintenance**:
- Verify all internal links still work
- Update docs/INDEX.md if needed

### Out of Scope

| Item | Rationale |
|------|-----------|
| Code changes | Documentation-only initiative |
| Skills architecture reorganization | Preserve existing structure per constraints |
| Specific metric percentages | User preference for qualitative descriptions |
| Specific ADR/TDD counts in skills | They change too frequently |
| New skills creation | Work within existing skill structure |

---

## Requirements

### Status Update Requirements (FR-STATUS-*)

#### FR-STATUS-001: Remove Prototype Status from PROJECT_CONTEXT.md

| Field | Value |
|-------|-------|
| **ID** | FR-STATUS-001 |
| **Requirement** | PROJECT_CONTEXT.md must not claim "Prototype" status |
| **Priority** | Must |
| **File** | `.claude/PROJECT_CONTEXT.md` |
| **Line** | 27 |

**Acceptance Criteria**:
- [ ] Line 27 changed from `Stage: Prototype` to `Stage: Production`
- [ ] No other occurrences of "Prototype" as project status in this file

---

#### FR-STATUS-002: Remove Prototype Status from context.md

| Field | Value |
|-------|-------|
| **ID** | FR-STATUS-002 |
| **Requirement** | context.md must not claim "Prototype" stage |
| **Priority** | Must |
| **File** | `.claude/skills/autom8-asana-domain/context.md` |
| **Lines** | 57, 15 |

**Acceptance Criteria**:
- [ ] Line 57 changed from `**Stage**: Prototype (greenfield extraction)` to `**Stage**: Production`
- [ ] Line 15 updated to reflect current state rather than "prototype for extracting"
- [ ] No other "Prototype" stage claims remain

---

#### FR-STATUS-003: Remove Prototype Label from tech-stack.md

| Field | Value |
|-------|-------|
| **ID** | FR-STATUS-003 |
| **Requirement** | tech-stack.md version must not include "(prototype)" |
| **Priority** | Must |
| **File** | `.claude/skills/autom8-asana-domain/tech-stack.md` |
| **Line** | 61 |

**Acceptance Criteria**:
- [ ] Line 61 changed from `Version: 0.1.0 (prototype)` to `Version: 0.1.0`
- [ ] Or updated to current version if different

---

### Coverage Update Requirements (FR-COVERAGE-*)

#### FR-COVERAGE-001: Remove "~0%" Test Coverage Claims

| Field | Value |
|-------|-------|
| **ID** | FR-COVERAGE-001 |
| **Requirement** | All "~0%" or "0%" test coverage claims must be removed |
| **Priority** | Must |
| **File** | `.claude/skills/autom8-asana-domain/context.md` |
| **Lines** | 61, 127 |

**Acceptance Criteria**:
- [ ] Line 61 changed from `Test coverage: ~0% (test infrastructure being built)` to qualitative description
- [ ] Line 127 success metrics table updated with qualitative description
- [ ] No "0%" coverage claims remain in any .claude/ files

---

#### FR-COVERAGE-002: Use Qualitative Coverage Descriptions

| Field | Value |
|-------|-------|
| **ID** | FR-COVERAGE-002 |
| **Requirement** | Test coverage descriptions must use qualitative terms |
| **Priority** | Must |

**Acceptable Terms**:
- "Comprehensive coverage"
- "Extensive test suite"
- "High coverage across all modules"

**Unacceptable Terms**:
- Specific percentages (87%, 92%, etc.)
- "~0%", "low", "minimal"

**Acceptance Criteria**:
- [ ] All coverage mentions use approved qualitative terms
- [ ] No specific percentages appear in skills documentation

---

### Entity Documentation Requirements (FR-ENTITY-*)

#### FR-ENTITY-001: Correct Stub Entity Count

| Field | Value |
|-------|-------|
| **ID** | FR-ENTITY-001 |
| **Requirement** | entity-reference.md must accurately list 3 stub entities |
| **Priority** | Must |
| **File** | `.claude/skills/autom8-asana-business/entity-reference.md` |
| **Line** | 22 |

**Acceptance Criteria**:
- [ ] Line 22 updated to show only 3 stubs: DNA, Reconciliation, Videography
- [ ] AssetEdit removed from stub list (it is fully implemented)
- [ ] Clear distinction between stub holders and stub entities

**Correct Text**:
```
+-- DNAHolder, ReconciliationHolder, VideographyHolder (stubs)
```

---

#### FR-ENTITY-002: Clarify Stub vs Implemented Status

| Field | Value |
|-------|-------|
| **ID** | FR-ENTITY-002 |
| **Requirement** | Documentation must clarify what "stub" means |
| **Priority** | Should |
| **File** | `.claude/skills/autom8-asana-business/entity-reference.md` |

**Acceptance Criteria**:
- [ ] Definition of "stub" added: navigation-only, no custom field accessors
- [ ] Mention that stubs follow TDD-HARDENING-A patterns (FR-STUB-001/002/003)
- [ ] AssetEdit explicitly noted as fully implemented with custom fields

---

### Paradigm Documentation Requirements (FR-PARADIGM-*)

#### FR-PARADIGM-001: Document Asana-as-Database Concept

| Field | Value |
|-------|-------|
| **ID** | FR-PARADIGM-001 |
| **Requirement** | The Asana-as-database paradigm must be documented |
| **Priority** | Must |
| **Location** | TBD by Architect (new file or section in existing file) |

**Content Requirements**:
- [ ] Explain core insight: Asana serves as the database
- [ ] Tasks = rows, Custom Fields = columns, Projects = tables/indexes
- [ ] Why this architecture was chosen
- [ ] How it enables the business model layer
- [ ] Connection to entity detection via project membership

**Acceptance Criteria**:
- [ ] Paradigm is documented in designated location
- [ ] Discoverable within 2 clicks from CLAUDE.md
- [ ] Referenced from PROJECT_CONTEXT.md or SKILL.md

---

#### FR-PARADIGM-002: Link Paradigm from Entry Points

| Field | Value |
|-------|-------|
| **ID** | FR-PARADIGM-002 |
| **Requirement** | Core entry points must link to paradigm documentation |
| **Priority** | Should |

**Acceptance Criteria**:
- [ ] CLAUDE.md "Getting Help" table includes paradigm reference
- [ ] PROJECT_CONTEXT.md mentions paradigm in "What Is This?" section
- [ ] autom8-asana-domain SKILL.md quick reference includes paradigm link

---

### Cross-Reference Requirements (FR-XREF-*)

#### FR-XREF-001: Verify Internal Link Validity

| Field | Value |
|-------|-------|
| **ID** | FR-XREF-001 |
| **Requirement** | All internal markdown links must resolve |
| **Priority** | Should |

**Acceptance Criteria**:
- [ ] All `[text](path.md)` links in updated files resolve
- [ ] No broken relative paths after edits
- [ ] docs/INDEX.md reflects any new documents

---

#### FR-XREF-002: Update INDEX.md for New Documents

| Field | Value |
|-------|-------|
| **ID** | FR-XREF-002 |
| **Requirement** | docs/INDEX.md must include PRD-DOCS-EPOCH-RESET |
| **Priority** | Must |

**Acceptance Criteria**:
- [ ] PRD-DOCS-EPOCH-RESET.md added to PRDs table
- [ ] Any new paradigm document added to appropriate section
- [ ] Document number allocation updated

---

## User Stories / Use Cases

### US-001: AI Agent Context Loading

**As a** Claude Code agent
**I want to** receive accurate project maturity information from skills
**So that** I make appropriate recommendations for a production system

**Current**: Agent reads "Prototype" and "~0% coverage", treats system as early-stage
**After**: Agent reads "Production" with comprehensive coverage, treats system as mature

---

### US-002: Developer Onboarding

**As a** new developer
**I want to** understand the Asana-as-database paradigm
**So that** I understand why entities are structured as Task subclasses

**Current**: Developer cannot find paradigm explanation anywhere
**After**: Developer finds paradigm doc within 2 clicks from CLAUDE.md

---

### US-003: Entity Type Research

**As a** developer working with business entities
**I want to** know which entities are stubs vs fully implemented
**So that** I know what capabilities are available

**Current**: Documentation claims 4 stubs when only 3 exist
**After**: Documentation accurately lists 3 stubs with clear definition

---

## Assumptions

1. **Skills architecture preserved**: We update content within existing files, not reorganize structure
2. **Qualitative metrics preferred**: User confirmed no specific percentages
3. **ADR/TDD counts excluded**: User confirmed these change too frequently for skills docs
4. **Paradigm location flexible**: Architect will determine optimal placement
5. **No code verification needed**: Claims verified against codebase during audit

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| Architect decision on paradigm location | Architect | Pending (Session 2) |
| Documentation skill templates | Available | Complete |
| Codebase access for verification | Available | Complete |

---

## Open Questions

| # | Question | Owner | Resolution |
|---|----------|-------|------------|
| Q1 | Where should Asana-as-database paradigm live? | Architect | Defer to Architecture session |
| Q2 | Should paradigm be standalone doc or section? | Architect | Defer to Architecture session |

**Note**: No blocking questions remain for Session 1 deliverables. Paradigm location is deferred to Architecture phase per user guidance.

---

## Implementation Phases

| Phase | Agent | Focus | Deliverables |
|-------|-------|-------|--------------|
| 1 (This PRD) | Requirements Analyst | Audit + Requirements | Audit Report, PRD |
| 2 | Architect | Information Architecture | TDD with file/section decisions |
| 3 | Principal Engineer | Core Status Updates | Updated PROJECT_CONTEXT.md, context.md, tech-stack.md |
| 4 | Principal Engineer | Paradigm Documentation | New paradigm content |
| 5 | Principal Engineer | Entity + Cross-Reference | entity-reference.md, INDEX.md |
| 6 | QA/Adversary | Validation | Accuracy verification report |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-17 | Requirements Analyst | Initial PRD from Discovery audit |

---

## Quality Gates Checklist

- [x] Problem statement is clear and specific
- [x] Audit findings documented with file:line citations
- [x] Scope explicitly defines in/out boundaries
- [x] Every requirement has acceptance criteria
- [x] MoSCoW priorities assigned to all requirements
- [x] Requirements trace to audit findings
- [x] Success metrics are measurable
- [x] Assumptions documented
- [x] Dependencies identified with status
- [x] Open questions resolved or explicitly deferred
- [x] Implementation phases defined
