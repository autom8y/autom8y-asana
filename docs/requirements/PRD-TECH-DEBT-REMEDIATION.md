# PRD: Technical Debt Remediation Initiative

## Metadata

| Field | Value |
|-------|-------|
| **PRD ID** | PRD-TECH-DEBT-REMEDIATION |
| **Status** | Draft |
| **Author** | Requirements Analyst |
| **Created** | 2025-12-19 |
| **Last Updated** | 2025-12-19 |
| **Stakeholders** | SDK Team, Platform Team |
| **Discovery Document** | [DISCOVERY-TECH-DEBT-REMEDIATION.md](/docs/analysis/DISCOVERY-TECH-DEBT-REMEDIATION.md) |
| **Related PRDs** | PRD-0024 (Custom Field Remediation - COMPLETE) |

---

## Problem Statement

### What Problem Are We Solving?

The autom8_asana SDK has accumulated technical debt that compromises detection reliability, limits Process entity functionality, and creates gaps in test coverage. Specifically:

1. **Detection System Gaps**: Entity type detection for Process and several Holder types relies on fragile Tier 2 name-pattern matching because PRIMARY_PROJECT_GID values are not configured. This causes detection failures when task names deviate from expected patterns.

2. **Process Model Limitations**: The Process entity has only 8 generic fields while actual Asana projects contain 67+ fields (Sales), 41+ fields (Onboarding), etc. Developers cannot access pipeline-specific data without raw API calls.

3. **Test Coverage Imbalance**: The test pyramid shows 86% unit / 14% integration / 0% e2e, with critical paths like detection and hydration lacking integration test coverage.

### For Whom?

- **SDK developers** who need reliable entity detection and type-safe Process field access
- **Platform engineers** who integrate with Business hierarchy hydration
- **QA engineers** who need comprehensive test coverage for validation

### Impact of Not Solving

- Detection failures during hierarchy hydration cause incomplete Business loading
- Developers bypass SDK to access Process fields via raw API (duplicated logic)
- Integration bugs reach production due to insufficient integration test coverage
- Stale documentation causes confusion and incorrect implementation patterns

---

## Goals & Success Metrics

### Primary Goals

| Goal | Success Metric | Target |
|------|----------------|--------|
| Reliable entity detection | Tier 1 detection success rate | 100% for entities with PRIMARY_PROJECT_GID |
| Process field accessibility | Field coverage for Sales pipeline | >= 80% (54/67 fields) |
| Test coverage balance | Integration test file ratio | >= 20% of test files |
| Documentation accuracy | Stale reference count | 0 references to deleted code |

### Secondary Goals

| Goal | Success Metric | Target |
|------|----------------|--------|
| Self-healing capability | Auto-repair of missing project membership | Opt-in available |
| Startup validation | Invalid configuration detection | Fail-fast on startup |

---

## Scope

### In Scope

**Phase 1: Detection System Foundation** (7 DEBT items)
- Configure PRIMARY_PROJECT_GID for Process, ProcessHolder entities
- Validate holder PRIMARY_PROJECT_GID values (LocationHolder, UnitHolder)
- Improve Detection Tier 2 pattern matching reliability
- Implement self-healing for missing project membership
- Validate WorkspaceProjectRegistry lazy discovery timing
- Add startup validation for ASANA_PROJECT_* environment variables
- Delete ProcessProjectRegistry (architectural cleanup prerequisite)

**Phase 2: Process Entity Enhancement** (4 DEBT items)
- Add Sales-specific field accessors to Process model
- Add Onboarding-specific field accessors
- Add Implementation-specific field accessors
- Extend ProcessType enum if granular types needed

**Phase 3: Test Coverage & Documentation** (3 DEBT items)
- Add integration tests for detection system
- Improve test pyramid ratio toward 70/20/10 target
- Remove stale documentation references to deleted code

### Out of Scope

| Item | Rationale |
|------|-----------|
| **DEBT-009 through DEBT-018** | Already fixed per Discovery document |
| **DEBT-027: AssetEditHolder custom fields** | Deferred - requires architectural decision on holder pattern (see Appendix A) |
| **DEBT-028: Specialty field dual GIDs** | Deferred - lower priority than core detection (see Appendix A) |
| **DEBT-029: Business missing 16 fields** | Deferred - separate field expansion initiative (see Appendix A) |
| **Retention/Reactivation/Outreach fields** | Phase 2 focuses on top 3 pipelines by usage |
| **End-to-end test suite** | Separate initiative after integration tests |
| **Performance optimization** | Not a stated problem; address if metrics indicate need |

---

## Requirements

### Phase 1: Detection System Foundation (FR-DET-*)

| ID | Requirement | Priority | Acceptance Criteria | DEBT Reference |
|----|-------------|----------|---------------------|----------------|
| FR-DET-001 | Delete ProcessProjectRegistry module and all references | Must | 1. `process_registry.py` deleted; 2. No import errors; 3. All tests pass; 4. ~1,085 lines removed | DEBT-022 |
| FR-DET-002 | Configure Process.PRIMARY_PROJECT_GID to use WorkspaceProjectRegistry | Must | 1. Process entities in registered pipeline projects detected via Tier 1; 2. ProcessType correctly identified from project membership | DEBT-001 |
| FR-DET-003 | Configure ProcessHolder.PRIMARY_PROJECT_GID appropriately | Must | 1. ProcessHolder detection uses Tier 1 when project exists; 2. Falls back to Tier 2 name pattern when no project | DEBT-002 |
| FR-DET-004 | Validate LocationHolder and UnitHolder PRIMARY_PROJECT_GID | Should | 1. Confirm None is correct (no dedicated project); 2. Document as intentional in entity docstring | DEBT-003, DEBT-004 |
| FR-DET-005 | Improve Detection Tier 2 name pattern matching | Should | 1. Support prefix/suffix decorated names (e.g., "[URGENT] Contacts"); 2. 95% accuracy on decorated name variations | DEBT-005 |
| FR-DET-006 | Implement optional self-healing for missing project membership | Could | 1. `add_to_project()` called when entity missing from expected project; 2. Opt-in via `healing_enabled=True` parameter; 3. Dry-run mode available | DEBT-006 |
| FR-DET-007 | Add startup validation for ASANA_PROJECT_* environment variables | Could | 1. Warning logged if env var set but project GID invalid format; 2. Optional fail-fast mode via `ASANA_STRICT_CONFIG=true` | DEBT-008 |

### Phase 2: Process Entity Enhancement (FR-PROC-*)

| ID | Requirement | Priority | Acceptance Criteria | DEBT Reference |
|----|-------------|----------|---------------------|----------------|
| FR-PROC-001 | Add Sales pipeline field accessors to Process | Must | 1. >= 54 of 67 Sales fields have typed accessors; 2. Fields use correct descriptor types (EnumField, TextField, etc.); 3. Backward compatible with existing 8 fields | DEBT-019 |
| FR-PROC-002 | Add Onboarding pipeline field accessors to Process | Should | 1. >= 33 of 41 Onboarding fields have typed accessors; 2. Fields not overlapping with Sales reuse same accessors | DEBT-020 |
| FR-PROC-003 | Add Implementation pipeline field accessors to Process | Should | 1. >= 28 of 35 Implementation fields have typed accessors; 2. Common fields unified across pipeline types | DEBT-021 |
| FR-PROC-004 | Extend ProcessType enum if granular types needed | Could | 1. If new pipeline types discovered, add to enum; 2. Maintain backward compatibility with existing 7 types | DEBT-023 |

### Phase 3: Test Coverage & Documentation (FR-TEST-*)

| ID | Requirement | Priority | Acceptance Criteria | DEBT Reference |
|----|-------------|----------|---------------------|----------------|
| FR-TEST-001 | Add integration tests for detection system | Must | 1. Test file `tests/integration/test_detection.py` exists; 2. Tests cover Tier 1 and Tier 2 detection; 3. Tests cover edge cases (missing projects, decorated names) | DEBT-025 |
| FR-TEST-002 | Improve test pyramid ratio | Should | 1. Integration test files >= 18 (from 15); 2. Ratio moves toward 80/20 target; 3. New tests cover WorkspaceProjectRegistry, hydration | DEBT-024 |
| FR-TEST-003 | Remove stale documentation references | Must | 1. No TDD/ADR references ProcessProjectRegistry; 2. All import examples in docs are valid; 3. Glossary updated if terms deprecated | DEBT-026 |

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

## User Stories / Use Cases

### UC-1: Reliable Process Detection

**As a** SDK developer
**I want** Process entities to be detected reliably via project membership
**So that** Business hierarchy hydration includes all Process children

**Scenario:**
1. Business.from_gid_async() called with hydrate=True
2. SDK fetches ProcessHolder subtasks
3. Each Process task has projects[] containing Sales project GID
4. Detection returns EntityType.PROCESS with ProcessType.SALES
5. Process model created with correct type-specific field accessors

### UC-2: Type-Safe Sales Field Access

**As a** platform engineer
**I want** to access Sales pipeline fields via typed properties
**So that** I get IDE autocomplete and type checking

**Scenario:**
1. Process entity loaded from Sales pipeline
2. Access `process.close_date` returns `datetime | None`
3. Access `process.deal_value` returns `Decimal | None`
4. Access `process.stage` returns `str | None` (enum value)
5. IDE provides autocomplete for all 54+ Sales fields

### UC-3: Self-Healing Missing Project Membership

**As a** operations engineer
**I want** the SDK to optionally repair tasks missing from their canonical project
**So that** detection continues to work even after manual Asana edits

**Scenario:**
1. Task removed from Sales project manually in Asana UI
2. SDK attempts detection, Tier 1 fails
3. With `healing_enabled=True`, SDK calls `add_to_project()`
4. Log emitted: `{"action": "self_heal", "task_gid": "...", "project_gid": "..."}`
5. Next detection succeeds via Tier 1

---

## Assumptions

| ID | Assumption | Basis |
|----|------------|-------|
| A-1 | ProcessProjectRegistry deletion will not break production workflows | Per IMPACT-PROCESS-CLEANUP.md analysis - no external consumers |
| A-2 | Pipeline project GIDs are stable and will not change | Historical pattern - project GIDs unchanged for 2+ years |
| A-3 | Process fields are consistent within a pipeline type | Audit shows same fields for all Sales tasks |
| A-4 | Holders without projects (LocationHolder, UnitHolder) are intentional | These are container tasks, not Asana project members |
| A-5 | 80% field coverage is sufficient for initial Process enhancement | Pareto principle - cover high-usage fields first |

---

## Dependencies

| Dependency | Owner | Status | Impact if Blocked |
|------------|-------|--------|-------------------|
| Discovery document complete | Requirements Analyst | DONE | Cannot start |
| CUSTOM-FIELD-REALITY-AUDIT.md | Platform Team | DONE | Cannot verify field types |
| IMPACT-PROCESS-CLEANUP.md | Architect | DONE | Cannot proceed with DEBT-022 |
| Pipeline project GIDs confirmed | Operations | DONE | Cannot configure PRIMARY_PROJECT_GID |
| Field type mapping for Sales | Platform Team | DONE | Cannot implement FR-PROC-001 |

---

## Open Questions

| ID | Question | Owner | Due Date | Resolution |
|----|----------|-------|----------|------------|
| OQ-1 | Should ProcessHolder have a dedicated project? | Architect | Pre-TDD | Confirm None is correct or identify project |
| OQ-2 | How should composition vs inheritance be used for Process pipeline variants? | Architect | TDD Phase | ADR needed |
| OQ-3 | What is the rollback plan if ProcessProjectRegistry deletion causes issues? | Engineer | Pre-implementation | Git revert + hotfix process |

---

## Constraints

| Constraint | Rationale |
|------------|-----------|
| Must maintain backward compatibility | Existing integrations cannot break |
| Cannot add mandatory environment variables | Optional configuration only |
| Self-healing must be opt-in | Automatic writes could cause unexpected behavior |
| Integration tests must not require live Asana credentials in CI | Use mocks or recorded fixtures |

---

## Appendix A: Disposition Decisions for Discovered DEBT Items

### DEBT-027: AssetEditHolder Custom Fields (Pattern Break)

**Decision: OUT OF SCOPE**

**Rationale:**
AssetEditHolder having 4 custom fields (Generic Assets, Template Assets, Review All Ads, Asset Edit Comments) breaks the holder pattern assumption that holders have 0 custom fields. However:

1. These fields are configuration/metadata, not child entity data
2. Adding field accessors to AssetEditHolder would require architectural decision on holder responsibilities
3. No current use cases require programmatic access to these holder fields

**Recommended Future Action:** Create ADR to decide whether holders can have field accessors or if this is an exception to document.

### DEBT-028: Specialty Field Dual GIDs

**Decision: OUT OF SCOPE**

**Rationale:**
Two distinct Specialty fields exist with different GIDs:
- GID `1202981898844151` (multi_enum) - Used by Unit, AssetEdit
- GID `1200943943116217` (enum) - Used by Offer, Business, Process types

However:
1. Current field resolution by name works because projects don't have both
2. Custom field accessor pattern handles both enum and multi_enum
3. Disambiguation only needed if a project has both fields (not currently the case)

**Recommended Future Action:** Add field GID-aware resolution if use case arises.

### DEBT-029: Business Missing 16 Fields

**Decision: OUT OF SCOPE**

**Rationale:**
Business model has 54% field coverage (19/35 fields). Missing fields include:
- Financial: MRR, Weekly Ad Spend, Discount
- Platform: Specialty, Time Zone, Ad Account ID, TikTok Profile
- Media: Logo URL, Header URL, Landing Page URL
- Meta: Status

However:
1. This PRD focuses on detection and Process enhancement, not field expansion
2. Business field expansion is a separate concern requiring its own audit
3. Existing Business fields cover primary use cases

**Recommended Future Action:** Create separate PRD-BUSINESS-FIELD-EXPANSION if field coverage becomes priority.

---

## Appendix B: Phase Execution Order

Per Discovery document dependency analysis:

```
Phase 0: Prerequisite Cleanup
    FR-DET-001 (Delete ProcessProjectRegistry)
        |
        v
Phase 1: Detection Foundation
    FR-DET-002, FR-DET-003 (PRIMARY_PROJECT_GID)
        |
        v
    FR-DET-004 (Holder validation)
    FR-DET-005 (Tier 2 improvements)
    FR-DET-006 (Self-healing)
    FR-DET-007 (Startup validation)
        |
        v
Phase 2: Process Enhancement
    FR-PROC-001 (Sales fields) [depends on FR-DET-002]
        |
        v
    FR-PROC-002, FR-PROC-003 (Other pipelines)
    FR-PROC-004 (ProcessType enum)
        |
        v
Phase 3: Test & Documentation
    FR-TEST-001, FR-TEST-002, FR-TEST-003
```

---

## Appendix C: Acceptance Criteria Matrix

### Phase 1 Verification Checklist

| Requirement | Test Type | Pass Criteria |
|-------------|-----------|---------------|
| FR-DET-001 | Unit + Integration | `pytest tests/` passes; no `process_registry` imports |
| FR-DET-002 | Integration | `detect_entity_type(sales_task)` returns `EntityType.PROCESS` |
| FR-DET-003 | Integration | ProcessHolder in hierarchy detected correctly |
| FR-DET-004 | Code Review | Docstrings document None as intentional |
| FR-DET-005 | Unit | `detect_entity_type("[URGENT] Contacts")` returns `CONTACT_HOLDER` |
| FR-DET-006 | Integration | Task added to project when healing enabled |
| FR-DET-007 | Unit | Warning logged for malformed env var |

### Phase 2 Verification Checklist

| Requirement | Test Type | Pass Criteria |
|-------------|-----------|---------------|
| FR-PROC-001 | Unit | `process.close_date`, `process.deal_value` etc. accessible |
| FR-PROC-002 | Unit | Onboarding-specific fields accessible |
| FR-PROC-003 | Unit | Implementation-specific fields accessible |
| FR-PROC-004 | Unit | ProcessType enum unchanged or extended |

### Phase 3 Verification Checklist

| Requirement | Test Type | Pass Criteria |
|-------------|-----------|---------------|
| FR-TEST-001 | CI | `tests/integration/test_detection.py` exists and passes |
| FR-TEST-002 | Metric | `find tests/integration -name "*.py" \| wc -l` >= 18 |
| FR-TEST-003 | Search | `grep -r "ProcessProjectRegistry" docs/` returns no results |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-19 | Requirements Analyst | Initial draft based on Discovery |

---

## Quality Gate Checklist

- [x] Problem statement is clear and compelling
- [x] Scope explicitly defines in/out (14 items in, 3 discovered items out with rationale)
- [x] All 14 remaining DEBT items have corresponding functional requirements
- [x] Each requirement has testable acceptance criteria
- [x] Newly discovered items (DEBT-027, 028, 029) have disposition decisions
- [x] Assumptions documented (5 assumptions)
- [x] No open questions blocking design (3 questions have owners assigned)
- [x] PRD references Discovery document for evidence
- [x] Requirements are prioritized (Must/Should/Could)

---

*End of PRD*
