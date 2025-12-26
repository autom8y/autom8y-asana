# PRD-11: Technical Debt & Migration

> Consolidated PRD for debt remediation and documentation reset.

## Metadata

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2025-12-25 |
| **Consolidated From** | PRD-TECH-DEBT-REMEDIATION, PRD-DOCS-EPOCH-RESET |
| **Related TDD** | TDD-12-debt-migration |
| **Stakeholders** | SDK Team, Platform Team, AI Agents, Human Developers |

---

## Executive Summary

This PRD consolidates two initiatives addressing accumulated technical debt and documentation staleness in the autom8_asana SDK:

1. **Technical Debt Remediation**: Detection system gaps, Process model limitations, and test coverage imbalance that compromise SDK reliability and developer experience.

2. **Documentation Epoch Reset**: Documentation describing a "Day 30 prototype" when the codebase has evolved to "Day 300 production maturity," causing AI agents and developers to fundamentally misunderstand the system.

Both initiatives share a common theme: the project has matured significantly through 95+ ADRs and 32+ TDDs of architectural evolution, but artifacts (both code and documentation) have not kept pace with this maturity.

---

## Problem Statement

### Technical Debt Problems

The autom8_asana SDK has accumulated technical debt that compromises detection reliability, limits Process entity functionality, and creates gaps in test coverage:

1. **Detection System Gaps**: Entity type detection for Process and several Holder types relies on fragile Tier 2 name-pattern matching because PRIMARY_PROJECT_GID values are not configured. This causes detection failures when task names deviate from expected patterns.

2. **Process Model Limitations**: The Process entity has only 8 generic fields while actual Asana projects contain 67+ fields (Sales), 41+ fields (Onboarding), etc. Developers cannot access pipeline-specific data without raw API calls.

3. **Test Coverage Imbalance**: The test pyramid shows 86% unit / 14% integration / 0% e2e, with critical paths like detection and hydration lacking integration test coverage.

### Documentation Problems

The documentation describes the project as it existed around "Day 30" while the codebase has evolved to "Day 300" maturity:

1. **Prototype Status Claims**: Multiple files claim "Prototype" status when the system is production-grade with comprehensive test coverage.

2. **Zero Coverage Claims**: Documentation claims "~0% test coverage" when 129 test files exist across all modules.

3. **Inaccurate Entity Counts**: Documentation lists 4 stub entities when only 3 remain (AssetEdit is now fully implemented).

4. **Missing Paradigm Documentation**: The core "Asana-as-database" architectural insight is completely undocumented.

### Impact of Not Solving

- Detection failures during hierarchy hydration cause incomplete Business loading
- Developers bypass SDK to access Process fields via raw API (duplicated logic)
- Integration bugs reach production due to insufficient integration test coverage
- AI agents treat a production-grade SDK as a prototype
- Developer onboarding fails due to undocumented architectural paradigm
- Capability discovery fails for 127+ custom fields, cascade logic, and resolution strategies

---

## Goals & Non-Goals

### Goals

| Category | Goal | Success Metric | Target |
|----------|------|----------------|--------|
| Detection | Reliable entity detection | Tier 1 detection success rate | 100% for entities with PRIMARY_PROJECT_GID |
| Process | Process field accessibility | Field coverage for Sales pipeline | >= 80% (54/67 fields) |
| Testing | Test coverage balance | Integration test file ratio | >= 20% of test files |
| Documentation | Accurate status | Outdated "Prototype" claims | 0 |
| Documentation | Coverage descriptions | Outdated "~0% coverage" claims | 0 |
| Documentation | Entity accuracy | Stub entity count matches reality | 3 stubs documented |
| Documentation | Paradigm discovery | Asana-as-database discoverable | Within 2 clicks from CLAUDE.md |
| Documentation | Reference integrity | Cross-reference validity | 100% |

### Non-Goals

| Item | Rationale |
|------|-----------|
| AssetEditHolder custom fields (DEBT-027) | Requires architectural decision on holder pattern |
| Specialty field dual GIDs (DEBT-028) | Lower priority than core detection |
| Business missing 16 fields (DEBT-029) | Separate field expansion initiative |
| End-to-end test suite | Separate initiative after integration tests |
| Skills architecture reorganization | Preserve existing structure |
| Specific metric percentages in docs | User preference for qualitative descriptions |
| Specific ADR/TDD counts in skills | They change too frequently |

---

## Requirements

### Detection System Foundation (FR-DET-*)

| ID | Requirement | Priority | Acceptance Criteria | DEBT Reference |
|----|-------------|----------|---------------------|----------------|
| FR-DET-001 | Delete ProcessProjectRegistry module and all references | Must | 1. `process_registry.py` deleted; 2. No import errors; 3. All tests pass; 4. ~1,085 lines removed | DEBT-022 |
| FR-DET-002 | Configure Process.PRIMARY_PROJECT_GID to use WorkspaceProjectRegistry | Must | 1. Process entities in registered pipeline projects detected via Tier 1; 2. ProcessType correctly identified from project membership | DEBT-001 |
| FR-DET-003 | Configure ProcessHolder.PRIMARY_PROJECT_GID appropriately | Must | 1. ProcessHolder detection uses Tier 1 when project exists; 2. Falls back to Tier 2 name pattern when no project | DEBT-002 |
| FR-DET-004 | Validate LocationHolder and UnitHolder PRIMARY_PROJECT_GID | Should | 1. Confirm None is correct (no dedicated project); 2. Document as intentional in entity docstring | DEBT-003, DEBT-004 |
| FR-DET-005 | Improve Detection Tier 2 name pattern matching | Should | 1. Support prefix/suffix decorated names (e.g., "[URGENT] Contacts"); 2. 95% accuracy on decorated name variations | DEBT-005 |
| FR-DET-006 | Implement optional self-healing for missing project membership | Could | 1. `add_to_project()` called when entity missing from expected project; 2. Opt-in via `healing_enabled=True` parameter; 3. Dry-run mode available | DEBT-006 |
| FR-DET-007 | Add startup validation for ASANA_PROJECT_* environment variables | Could | 1. Warning logged if env var set but project GID invalid format; 2. Optional fail-fast mode via `ASANA_STRICT_CONFIG=true` | DEBT-008 |

### Process Entity Enhancement (FR-PROC-*)

| ID | Requirement | Priority | Acceptance Criteria | DEBT Reference |
|----|-------------|----------|---------------------|----------------|
| FR-PROC-001 | Add Sales pipeline field accessors to Process | Must | 1. >= 54 of 67 Sales fields have typed accessors; 2. Fields use correct descriptor types (EnumField, TextField, etc.); 3. Backward compatible with existing 8 fields | DEBT-019 |
| FR-PROC-002 | Add Onboarding pipeline field accessors to Process | Should | 1. >= 33 of 41 Onboarding fields have typed accessors; 2. Fields not overlapping with Sales reuse same accessors | DEBT-020 |
| FR-PROC-003 | Add Implementation pipeline field accessors to Process | Should | 1. >= 28 of 35 Implementation fields have typed accessors; 2. Common fields unified across pipeline types | DEBT-021 |
| FR-PROC-004 | Extend ProcessType enum if granular types needed | Could | 1. If new pipeline types discovered, add to enum; 2. Maintain backward compatibility with existing 7 types | DEBT-023 |

### Test Coverage & Documentation (FR-TEST-*)

| ID | Requirement | Priority | Acceptance Criteria | DEBT Reference |
|----|-------------|----------|---------------------|----------------|
| FR-TEST-001 | Add integration tests for detection system | Must | 1. Test file `tests/integration/test_detection.py` exists; 2. Tests cover Tier 1 and Tier 2 detection; 3. Tests cover edge cases (missing projects, decorated names) | DEBT-025 |
| FR-TEST-002 | Improve test pyramid ratio | Should | 1. Integration test files >= 18 (from 15); 2. Ratio moves toward 80/20 target; 3. New tests cover WorkspaceProjectRegistry, hydration | DEBT-024 |
| FR-TEST-003 | Remove stale documentation references | Must | 1. No TDD/ADR references ProcessProjectRegistry; 2. All import examples in docs are valid; 3. Glossary updated if terms deprecated | DEBT-026 |

### Documentation Status Updates (FR-STATUS-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-STATUS-001 | Remove Prototype Status from PROJECT_CONTEXT.md | Must | 1. Line 27 changed from `Stage: Prototype` to `Stage: Production`; 2. No other "Prototype" status claims |
| FR-STATUS-002 | Remove Prototype Status from context.md | Must | 1. Line 57 changed from `**Stage**: Prototype` to `**Stage**: Production`; 2. Line 15 updated to reflect current state |
| FR-STATUS-003 | Remove Prototype Label from tech-stack.md | Must | 1. Line 61 changed from `Version: 0.1.0 (prototype)` to `Version: 0.1.0` |

### Documentation Coverage Updates (FR-COVERAGE-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-COVERAGE-001 | Remove "~0%" Test Coverage Claims | Must | 1. Line 61 of context.md changed from `Test coverage: ~0%` to qualitative description; 2. Line 127 success metrics table updated; 3. No "0%" coverage claims remain |
| FR-COVERAGE-002 | Use Qualitative Coverage Descriptions | Must | 1. All coverage mentions use terms like "Comprehensive coverage", "Extensive test suite"; 2. No specific percentages in skills documentation |

### Documentation Entity Updates (FR-ENTITY-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-ENTITY-001 | Correct Stub Entity Count | Must | 1. entity-reference.md updated to show only 3 stubs: DNA, Reconciliation, Videography; 2. AssetEdit removed from stub list; 3. Clear distinction between stub holders and entities |
| FR-ENTITY-002 | Clarify Stub vs Implemented Status | Should | 1. Definition of "stub" added: navigation-only, no custom field accessors; 2. Reference to TDD-HARDENING-A patterns; 3. AssetEdit noted as fully implemented |

### Documentation Paradigm (FR-PARADIGM-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-PARADIGM-001 | Document Asana-as-Database Concept | Must | 1. Explain core insight: Asana serves as the database; 2. Tasks = rows, Custom Fields = columns, Projects = tables/indexes; 3. Why architecture was chosen; 4. Connection to entity detection via project membership |
| FR-PARADIGM-002 | Link Paradigm from Entry Points | Should | 1. CLAUDE.md "Getting Help" table includes paradigm reference; 2. PROJECT_CONTEXT.md mentions paradigm; 3. autom8-asana-domain SKILL.md includes paradigm link |

### Documentation Cross-References (FR-XREF-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-XREF-001 | Verify Internal Link Validity | Should | 1. All `[text](path.md)` links in updated files resolve; 2. No broken relative paths after edits |
| FR-XREF-002 | Update INDEX.md for New Documents | Must | 1. Any new paradigm document added to appropriate section; 2. Document number allocation updated |

---

## Non-Functional Requirements

| ID | Category | Requirement | Target | Measurement |
|----|----------|-------------|--------|-------------|
| NFR-001 | Performance | Detection lookup time | O(1) for Tier 1 | Unit test with timing assertion |
| NFR-002 | Reliability | Detection accuracy for Tier 1 | 100% | Integration test with known project GIDs |
| NFR-003 | Reliability | Detection accuracy overall (Tier 1 + Tier 2) | >= 95% | Integration test with decorated name variants |
| NFR-004 | Maintainability | No increase in cyclomatic complexity | <= current | `radon cc` before/after comparison |
| NFR-005 | Backward Compatibility | Existing API signatures unchanged | 100% | All existing tests pass without modification |
| NFR-006 | Observability | Self-healing operations logged | Structured log with entity_gid, action | Log output verification |

---

## User Stories

### US-001: Reliable Process Detection

**As a** SDK developer
**I want** Process entities to be detected reliably via project membership
**So that** Business hierarchy hydration includes all Process children

**Scenario:**
1. Business.from_gid_async() called with hydrate=True
2. SDK fetches ProcessHolder subtasks
3. Each Process task has projects[] containing Sales project GID
4. Detection returns EntityType.PROCESS with ProcessType.SALES
5. Process model created with correct type-specific field accessors

### US-002: Type-Safe Sales Field Access

**As a** platform engineer
**I want** to access Sales pipeline fields via typed properties
**So that** I get IDE autocomplete and type checking

**Scenario:**
1. Process entity loaded from Sales pipeline
2. Access `process.close_date` returns `datetime | None`
3. Access `process.deal_value` returns `Decimal | None`
4. Access `process.stage` returns `str | None` (enum value)
5. IDE provides autocomplete for all 54+ Sales fields

### US-003: Self-Healing Missing Project Membership

**As a** operations engineer
**I want** the SDK to optionally repair tasks missing from their canonical project
**So that** detection continues to work even after manual Asana edits

**Scenario:**
1. Task removed from Sales project manually in Asana UI
2. SDK attempts detection, Tier 1 fails
3. With `healing_enabled=True`, SDK calls `add_to_project()`
4. Log emitted: `{"action": "self_heal", "task_gid": "...", "project_gid": "..."}`
5. Next detection succeeds via Tier 1

### US-004: AI Agent Context Loading

**As a** Claude Code agent
**I want to** receive accurate project maturity information from skills
**So that** I make appropriate recommendations for a production system

**Current**: Agent reads "Prototype" and "~0% coverage", treats system as early-stage
**After**: Agent reads "Production" with comprehensive coverage, treats system as mature

### US-005: Developer Onboarding

**As a** new developer
**I want to** understand the Asana-as-database paradigm
**So that** I understand why entities are structured as Task subclasses

**Current**: Developer cannot find paradigm explanation anywhere
**After**: Developer finds paradigm doc within 2 clicks from CLAUDE.md

### US-006: Entity Type Research

**As a** developer working with business entities
**I want to** know which entities are stubs vs fully implemented
**So that** I know what capabilities are available

**Current**: Documentation claims 4 stubs when only 3 exist
**After**: Documentation accurately lists 3 stubs with clear definition

---

## Success Metrics

### Technical Debt Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Tier 1 detection success rate | Variable | 100% for configured entities | Integration test |
| Sales field coverage | 8 fields | 54+ fields (80%) | Field count |
| Integration test file ratio | 14% | >= 20% | File count |
| Stale documentation references | Unknown | 0 | Grep for deleted code |

### Documentation Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Outdated "Prototype" claims | 3+ | 0 | Grep for "Prototype" in active docs |
| Outdated "~0% coverage" claims | 2+ | 0 | Grep for "0%" in active docs |
| Asana-as-database discoverable | No | Yes | Within 2 clicks from CLAUDE.md |
| Entity stub count accuracy | 4 listed | 3 (correct) | Manual verification |
| Cross-reference validity | Unknown | 100% | Link checker |

---

## Dependencies

| Dependency | Owner | Status | Impact if Blocked |
|------------|-------|--------|-------------------|
| Discovery documents complete | Requirements Analyst | DONE | Cannot scope work |
| CUSTOM-FIELD-REALITY-AUDIT.md | Platform Team | DONE | Cannot verify field types |
| IMPACT-PROCESS-CLEANUP.md | Architect | DONE | Cannot proceed with DEBT-022 |
| Pipeline project GIDs confirmed | Operations | DONE | Cannot configure PRIMARY_PROJECT_GID |
| Field type mapping for Sales | Platform Team | DONE | Cannot implement FR-PROC-001 |
| Architect decision on paradigm location | Architect | Pending | Paradigm placement deferred |

---

## Assumptions

| ID | Assumption | Basis |
|----|------------|-------|
| A-1 | ProcessProjectRegistry deletion will not break production workflows | Per IMPACT-PROCESS-CLEANUP.md analysis - no external consumers |
| A-2 | Pipeline project GIDs are stable and will not change | Historical pattern - project GIDs unchanged for 2+ years |
| A-3 | Process fields are consistent within a pipeline type | Audit shows same fields for all Sales tasks |
| A-4 | Holders without projects (LocationHolder, UnitHolder) are intentional | These are container tasks, not Asana project members |
| A-5 | 80% field coverage is sufficient for initial Process enhancement | Pareto principle - cover high-usage fields first |
| A-6 | Skills architecture preserved | Update content within existing files, not reorganize structure |
| A-7 | Qualitative metrics preferred | User confirmed no specific percentages |

---

## Constraints

| Constraint | Rationale |
|------------|-----------|
| Must maintain backward compatibility | Existing integrations cannot break |
| Cannot add mandatory environment variables | Optional configuration only |
| Self-healing must be opt-in | Automatic writes could cause unexpected behavior |
| Integration tests must not require live Asana credentials in CI | Use mocks or recorded fixtures |
| Documentation changes within existing file structure | Preserve skills architecture |
| No specific percentage metrics in documentation | User preference for qualitative descriptions |

---

## Implementation Phases

### Phase 0: Prerequisite Cleanup

- FR-DET-001: Delete ProcessProjectRegistry (~1,085 lines)

### Phase 1: Detection Foundation

- FR-DET-002, FR-DET-003: Configure PRIMARY_PROJECT_GID
- FR-DET-004: Validate Holder configurations
- FR-DET-005: Improve Tier 2 patterns
- FR-DET-006: Self-healing (opt-in)
- FR-DET-007: Startup validation

### Phase 2: Process Enhancement

- FR-PROC-001: Sales fields (depends on FR-DET-002)
- FR-PROC-002: Onboarding fields
- FR-PROC-003: Implementation fields
- FR-PROC-004: ProcessType enum

### Phase 3: Documentation Status Reset

- FR-STATUS-001, FR-STATUS-002, FR-STATUS-003: Remove Prototype claims
- FR-COVERAGE-001, FR-COVERAGE-002: Update coverage descriptions
- FR-ENTITY-001, FR-ENTITY-002: Correct entity counts

### Phase 4: Paradigm Documentation

- FR-PARADIGM-001: Document Asana-as-database concept
- FR-PARADIGM-002: Link from entry points

### Phase 5: Test & Cross-Reference

- FR-TEST-001, FR-TEST-002: Integration test coverage
- FR-TEST-003: Remove stale references
- FR-XREF-001, FR-XREF-002: Verify and update links

---

## Open Questions

| ID | Question | Owner | Resolution |
|----|----------|-------|------------|
| OQ-1 | Should ProcessHolder have a dedicated project? | Architect | Confirm None is correct or identify project |
| OQ-2 | How should composition vs inheritance be used for Process pipeline variants? | Architect | ADR needed |
| OQ-3 | What is the rollback plan if ProcessProjectRegistry deletion causes issues? | Engineer | Git revert + hotfix process |
| OQ-4 | Where should Asana-as-database paradigm live? | Architect | Defer to Architecture session |
| OQ-5 | Should paradigm be standalone doc or section? | Architect | Defer to Architecture session |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Tech Writer | Consolidated from PRD-TECH-DEBT-REMEDIATION and PRD-DOCS-EPOCH-RESET |
