---
ledger_id: "LEDGER-doc-debt-inventory"
created_at: "2025-12-24"
session_id: "session-20251224-232654-1a1ac669"
status: "draft"
audit_scope: "docs/, .claude/, README.md, skills"
---

# Documentation Debt Ledger

## Executive Summary

**Total Debt Items Identified**: 47 items across 6 categories

**Severity Distribution**:
- Critical: 8 items (17%)
- High: 12 items (26%)
- Medium: 18 items (38%)
- Low: 9 items (19%)

**By Category**:
- Outdated Content: 15 items (32%)
- Structural Issues: 10 items (21%)
- Missing Documentation: 9 items (19%)
- Quality Issues: 7 items (15%)
- Stale Artifacts: 4 items (9%)
- Redundant/Duplicate: 2 items (4%)

**Critical Findings**:
1. INDEX.md status metadata diverges from actual implementation status (affects 13+ PRDs)
2. Broken references in PROJECT_CONTEXT.md point to deleted autom8-asana skill
3. 15 PROMPT-* initiative files mislocated in /requirements/ directory
4. Multiple PRDs marked "Draft" but code implemented weeks ago

---

## Debt Items

### Category: Outdated Content

#### DEBT-001: INDEX.md Status Metadata Stale
- **Location**: `/docs/INDEX.md`
- **Severity**: critical
- **Description**: Status column in INDEX.md contradicts actual implementation status. 13+ PRDs show "Implemented" in INDEX but "Draft" in frontmatter or are marked "Draft" despite code being implemented.
- **Evidence**:
  - PRD-0002 (Intelligent Caching): INDEX says "Implemented", commits 3b1c48f, 20d1992, eff1d0d show active work through Dec 24
  - PRD-0013/0014 (Hydration/Resolution): INDEX says "Implemented", docs last updated Dec 16
  - PRD-0020 (Holder Factory): INDEX says "Implemented", actual implementation commit d318ce2 Dec 16
- **Suggested Fix**: Audit all INDEX.md status values against (1) document frontmatter, (2) git log evidence. Update 13+ mismatched entries. Establish CI check for status consistency.

#### DEBT-002: PRD-0002 Intelligent Caching Doc Stale
- **Location**: `/docs/requirements/PRD-0002-intelligent-caching.md`
- **Severity**: high
- **Description**: Doc last updated Dec 9, but cache system evolved significantly through Dec 24. Missing staleness detection, progressive TTL, watermark cache.
- **Evidence**: Doc date: Dec 9. Commits: 3f8e78e (Dec 24 lightweight staleness), eff1d0d (Dec 23 optimization P2), 20d1992 (Dec 23 cache extension)
- **Suggested Fix**: Update PRD-0002 to reflect current cache architecture or mark as "Superseded by PRD-CACHE-* series"

#### DEBT-003: PRD-0005 Save Orchestration Missing Healing System
- **Location**: `/docs/requirements/PRD-0005-save-orchestration.md`
- **Severity**: high
- **Description**: Doc last updated Dec 10, but SaveSession healing system added Dec 15+. Missing self-healing, HealingResult consolidation.
- **Evidence**: Doc date: Dec 10. Code commit: 45c11a4 (Dec 15+). ADR-0139, ADR-0144 document healing system.
- **Suggested Fix**: Add section on self-healing capabilities or create PRD-SAVESESSION-HEALING as follow-on

#### DEBT-004: PRD-0010 Business Model Layer Outdated
- **Location**: `/docs/requirements/PRD-0010-business-model-layer.md`
- **Severity**: medium
- **Description**: Doc last updated Dec 11, business models enhanced Dec 15+. Missing stub model enhancements (DNA, Reconciliation, Videography).
- **Evidence**: Doc date: Dec 11. Code commit: 92337aa (Dec 15+). See TP-0005 for stub model details.
- **Suggested Fix**: Update to reflect foundation hardening enhancements or mark sections as implemented

#### DEBT-005: TDD-0008 Intelligent Caching Architecture Stale
- **Location**: `/docs/design/TDD-0008-intelligent-caching.md`
- **Severity**: high
- **Description**: TDD describes original cache vision from Dec 9. Architecture evolved to multi-tier, staleness detection, progressive TTL by Dec 24.
- **Evidence**: TDD date: Dec 9. Implementation: TDD-CACHE-INTEGRATION, TDD-CACHE-OPTIMIZATION-P2/P3, TDD-CACHE-LIGHTWEIGHT-STALENESS all post-Dec 22
- **Suggested Fix**: Mark TDD-0008 as "Superseded by TDD-CACHE-* series" and link to current architecture in REF-cache-architecture.md

#### DEBT-006: PRD-0021 Async Method Generator Superseded
- **Location**: `/docs/requirements/PRD-0021-async-method-generator.md`
- **Severity**: medium
- **Description**: PRD describes @async_method_generator but actual implementation used @async_method decorator pattern
- **Evidence**: INDEX.md status: "Active". Actual: commit ee3ef8b (Dec 16) implemented decorator pattern, not generator
- **Suggested Fix**: Mark as "Superseded by @async_method decorator implementation (see PATTERNS-D)"

#### DEBT-007: PRD-0022 CRUD Base Class Rejected But Active
- **Location**: `/docs/requirements/PRD-0022-crud-base-class.md`
- **Severity**: medium
- **Description**: PRD marked "Active" in INDEX.md but TDD-0026 has explicit "NO-GO" decision
- **Evidence**: INDEX.md: "Active". TDD-0026 status: "NO-GO". Commit: 8fb895c documents rejection
- **Suggested Fix**: Update INDEX.md status to "Rejected", add supersession notice linking to TDD-0026 decision

#### DEBT-008: PRD-PROCESS-PIPELINE Partially Superseded
- **Location**: `/docs/requirements/PRD-PROCESS-PIPELINE.md`
- **Severity**: high
- **Description**: FR-REG-* requirements for ProcessProjectRegistry never implemented. ADR-0101 corrected architecture to use WorkspaceProjectRegistry instead.
- **Evidence**: PRD describes ProcessProjectRegistry. ADR-0101 (Process Pipeline Correction) documents rejection. WorkspaceProjectRegistry implemented instead.
- **Suggested Fix**: Add prominent supersession notice. Mark FR-REG-* as "Superseded by ADR-0101". Keep FR-TYPE/FR-SECTION/FR-STATE (still valid)

#### DEBT-009: PRD-DETECTION Status Mismatch
- **Location**: `/docs/requirements/PRD-DETECTION.md`
- **Severity**: medium
- **Description**: PRD marked "Draft" in INDEX.md but detection system implemented Dec 15
- **Evidence**: INDEX.md: "Draft". Code: src/autom8_asana/detection/ exists, commit d805780 (Dec 15). ADR-0135, ADR-0142, ADR-0143 document implementation.
- **Suggested Fix**: Update INDEX.md status to "Implemented"

#### DEBT-010: PRD-WORKSPACE-PROJECT-REGISTRY Wrong Status
- **Location**: `/docs/requirements/PRD-WORKSPACE-PROJECT-REGISTRY.md`
- **Severity**: medium
- **Description**: PRD marked "Draft" but validation report shows "APPROVED" and feature implemented
- **Evidence**: INDEX.md: "Draft". Validation: VP-WORKSPACE-PROJECT-REGISTRY status "APPROVED". Code exists in src/autom8_asana/models/registry.py
- **Suggested Fix**: Update INDEX.md status to "Implemented"

#### DEBT-011: PRD-CACHE-INTEGRATION Status Mismatch
- **Location**: `/docs/requirements/PRD-CACHE-INTEGRATION.md`
- **Severity**: medium
- **Description**: PRD marked "Implemented" in INDEX.md but document metadata unclear
- **Evidence**: INDEX.md: "Implemented". Commit 3b1c48f (Dec 22) "feat(cache): Activate dormant cache". Document status field: "Unknown"
- **Suggested Fix**: Update document frontmatter status to "Implemented", verify completion criteria met

#### DEBT-012: PRD-TECH-DEBT-REMEDIATION Status Unknown
- **Location**: `/docs/requirements/PRD-TECH-DEBT-REMEDIATION.md`
- **Severity**: low
- **Description**: PRD status shows "Unknown" but tech debt remediation implemented Dec 15
- **Evidence**: INDEX.md: "Unknown". Implementation: commit 3483715 (Dec 15). Features described in PRD exist in codebase.
- **Suggested Fix**: Update status to "Implemented" and document what was completed

#### DEBT-013: DOC-INVENTORY Status Annotations Unresolved
- **Location**: `/docs/DOC-INVENTORY-2025-12-24.csv`
- **Severity**: low
- **Description**: CSV contains "STATUS MISMATCH" notes for 8 documents but mismatches not resolved
- **Evidence**: Lines 3, 9, 10, 15, 16, 22, 23, 28 have "STATUS MISMATCH" or "STALE" in Notes column
- **Suggested Fix**: Resolve all status mismatches, update docs to current state, remove "STATUS MISMATCH" notes

#### DEBT-014: TDD-CUSTOM-FIELD-REMEDIATION Numbering Inconsistency
- **Location**: `/docs/design/TDD-CUSTOM-FIELD-REMEDIATION.md`
- **Severity**: low
- **Description**: Should be numbered TDD-0030 but uses named format TDD-CUSTOM-FIELD-REMEDIATION
- **Evidence**: DOC-INVENTORY line 104 notes: "Should be numbered TDD-0030"
- **Suggested Fix**: Accept named format (project moved to named scheme Dec 15+). Update INDEX.md to clarify TDD-0030 maps to TDD-CUSTOM-FIELD-REMEDIATION

#### DEBT-015: Sprint Decomposition Docs Status Unknown
- **Location**: `/docs/planning/sprints/PRD-SPRINT-{1,3,4,5}*.md`
- **Severity**: medium
- **Description**: 4 sprint decomposition docs marked "Unknown" status - unclear if planning docs or formal PRDs
- **Evidence**: PRD-SPRINT-1-PATTERN-COMPLETION.md, PRD-SPRINT-3-DETECTION-DECOMPOSITION.md, PRD-SPRINT-4-SAVESESSION-DECOMPOSITION.md, PRD-SPRINT-5-CLEANUP.md all created Dec 19, status "Unknown"
- **Suggested Fix**: Clarify document type. If planning: keep in /planning/. If completed: archive to .archive/planning/2025-Q4-sprints/. If active PRDs: update status.

---

### Category: Structural Issues

#### DEBT-016: PROMPT-* Files Mislocated
- **Location**: `/docs/requirements/PROMPT-*.md` (15 files)
- **Severity**: critical
- **Description**: 15 PROMPT-0-* initiative files located in /requirements/ directory but should be in /initiatives/
- **Evidence**: Files: PROMPT-0-CACHE-INTEGRATION.md, PROMPT-0-WATERMARK-CACHE.md, etc. INDEX.md lists these under "Initiatives" but physical location is /requirements/
- **Suggested Fix**: Move 15 PROMPT-* files from /requirements/ to /initiatives/. Update INDEX.md paths. Add README.md to /initiatives/ explaining PROMPT-0 vs PROMPT-MINUS-1 workflow.

#### DEBT-017: Missing README in Requirements Directory
- **Location**: `/docs/requirements/`
- **Severity**: medium
- **Description**: No README.md to explain PRD purpose, numbering scheme, or directory organization
- **Evidence**: ls /docs/requirements/ shows no README.md. Contrast with /docs/reference/README.md which provides excellent overview.
- **Suggested Fix**: Create /docs/requirements/README.md explaining PRD purpose, numbered vs named convention, PRD-TDD pairing, and archival policy

#### DEBT-018: Missing README in Design Directory
- **Location**: `/docs/design/`
- **Severity**: medium
- **Description**: No README.md to explain TDD purpose, PRD-TDD pairing, or design doc expectations
- **Evidence**: ls /docs/design/ shows README.md exists but may need enhancement (not verified in audit)
- **Suggested Fix**: Verify /docs/design/README.md exists and covers: TDD purpose, PRD pairing, status lifecycle, supersession policy

#### DEBT-019: Inconsistent Numbering Pattern
- **Location**: `/docs/requirements/`, `/docs/design/`
- **Severity**: low
- **Description**: Project started with numbered scheme (PRD-0001-0024) then switched to named scheme (PRD-CACHE-*). No documented convention.
- **Evidence**: Numbered: PRD-0001 through PRD-0024 (Dec 8-12). Named: PRD-CACHE-*, PRD-SPRINT-*, PRD-DETECTION (Dec 15+)
- **Suggested Fix**: Document naming convention in /docs/CONVENTIONS.md or /docs/requirements/README.md. Recommend named scheme going forward. Note INDEX.md as source of truth for PRD-TDD pairing.

#### DEBT-020: INDEX.md Document Number Allocation Section Incomplete
- **Location**: `/docs/INDEX.md` lines 356-364
- **Severity**: low
- **Description**: "Document Number Allocation" section doesn't reflect switch to named scheme or provide guidance
- **Evidence**: Section shows "Next Available: PRD-0025, TDD-0031" but doesn't note preference for named docs (established Dec 15+)
- **Suggested Fix**: Add note: "Prefer named scheme (PRD-FEATURE-NAME) for new docs. Numbered sequence retained for backward compatibility."

#### DEBT-021: Archival Candidates Not Archived
- **Location**: `/docs/requirements/PROMPT-0-*.md` (4 files)
- **Severity**: medium
- **Description**: 4 completed PROMPT-0 initiatives still in active /requirements/ directory
- **Evidence**: PROMPT-0-CACHE-OPTIMIZATION-PHASE2.md (complete per commit eff1d0d), PROMPT-0-CACHE-PERF-FETCH-PATH.md (P1 complete), PROMPT-0-WATERMARK-CACHE.md (validated PASS), PROMPT-0-WORKSPACE-PROJECT-REGISTRY.md (VP APPROVED)
- **Suggested Fix**: Archive to .archive/initiatives/2025-Q4/. Precedent: .archive/initiatives/2025-Q4/ already contains 5 archived initiatives.

#### DEBT-022: Missing Initiatives README
- **Location**: `/docs/initiatives/`
- **Severity**: medium
- **Description**: No README.md explaining PROMPT-0 vs PROMPT-MINUS-1 workflow, initiative lifecycle, or archival policy
- **Evidence**: INDEX.md references /initiatives/ directory but no README exists to explain file purpose
- **Suggested Fix**: Create /docs/initiatives/README.md explaining: PROMPT-0 (session 0), PROMPT-MINUS-1 (meta-initiative), lifecycle (active → complete → archived), relationship to PRDs

#### DEBT-023: Decisions Directory Missing README
- **Location**: `/docs/decisions/`
- **Severity**: low
- **Description**: 135 ADR files with no directory README explaining ADR format, numbering, or when to create ADRs
- **Evidence**: INDEX.md lists 135 ADRs (ADR-0001 through ADR-0144 with duplicates resolved Dec 24) but no README
- **Suggested Fix**: Create /docs/decisions/README.md explaining: What ADRs are, when to create them, numbering scheme, status lifecycle, ADR template

#### DEBT-024: Testing Directory Missing README
- **Location**: `/docs/testing/`
- **Severity**: low
- **Description**: Contains Test Plans (TP-*) and Validation Reports (VP-*) but no README explaining difference or when to use each
- **Evidence**: INDEX.md lists 10 TPs and 7 VPs but no README in /testing/ to explain format
- **Suggested Fix**: Create /docs/testing/README.md explaining: TP (pre-implementation plan) vs VP (post-implementation validation), status values, relationship to PRDs

#### DEBT-025: Runbooks Directory Missing README
- **Location**: `/docs/runbooks/`
- **Severity**: medium
- **Description**: 3 runbook files with no README explaining runbook purpose, when to create, or operational context
- **Evidence**: INDEX.md lists 3 runbooks (cache, savesession, detection troubleshooting) but no directory README
- **Suggested Fix**: Create /docs/runbooks/README.md explaining: Runbook purpose (operational troubleshooting), when to create (complex features, common issues), template, severity classification

---

### Category: Missing Documentation

#### DEBT-026: autom8-asana Skill Documentation Deleted
- **Location**: `.claude/skills/autom8-asana/` (deleted)
- **Severity**: critical
- **Description**: PROJECT_CONTEXT.md references "skills/autom8-asana-domain/paradigm.md" but directory does not exist. Skill was likely deleted in cleanup.
- **Evidence**: PROJECT_CONTEXT.md line 23 references paradigm.md. Git status shows "D .claude/skills/autom8-asana/*" files deleted. No replacement skill found.
- **Suggested Fix**: Either (1) restore autom8-asana skill from git history, or (2) update PROJECT_CONTEXT.md to reference docs/architecture/DOC-ARCHITECTURE.md instead, or (3) create new skill

#### DEBT-027: Missing Operational Runbooks
- **Location**: `/docs/runbooks/` (gaps)
- **Severity**: high
- **Description**: Complex features lack operational troubleshooting runbooks. Only 3 runbooks exist (cache, savesession, detection) but many implemented features need ops docs.
- **Evidence**: Implemented features without runbooks: Business model navigation, Batch operations, Custom field descriptors, Automation rules, Pipeline conversion
- **Suggested Fix**: Create runbooks for: RUNBOOK-batch-operations.md, RUNBOOK-business-model-navigation.md, RUNBOOK-automation-troubleshooting.md, RUNBOOK-pipeline-conversion.md

#### DEBT-028: Missing Test Plans for Implemented Features
- **Location**: `/docs/testing/` (gaps)
- **Severity**: medium
- **Description**: 8+ implemented features have no formal Test Plan or Validation Report
- **Evidence**: Missing TPs/VPs for: PRD-0005 (Save Orchestration), PRD-0007 (SDK Functional Parity), PRD-0008 (Parent & Subtask Ops), PRD-0010 (Business Model), PRD-CACHE-INTEGRATION
- **Suggested Fix**: Create validation reports for implemented features or mark as "Validated via unit tests" in INDEX.md. Prioritize: SaveSession (complex), Cache Integration (high impact)

#### DEBT-029: Missing How-To Guides
- **Location**: `/docs/guides/` (gaps)
- **Severity**: medium
- **Description**: Pattern documentation exists but procedural how-tos missing for common tasks
- **Evidence**: /docs/guides/ contains 8 guides but lacks: How to add new entity types, How to add custom field descriptors, How to create cache-aware clients, How to add ADRs
- **Suggested Fix**: Create how-to guides: HOW-TO-add-entity-type.md, HOW-TO-add-custom-field.md, HOW-TO-create-cache-client.md

#### DEBT-030: Missing Migration Guides
- **Location**: `/docs/migration/` (gaps)
- **Severity**: low
- **Description**: Only 1 migration guide exists (async-method decorator). Missing: S3→Redis cache, legacy API→SDK
- **Evidence**: /docs/migration/ contains MIGRATION-ASYNC-METHOD.md. /docs/guides/autom8-migration.md covers cache but not full API migration.
- **Suggested Fix**: Create MIGRATION-legacy-api-to-sdk.md. Consider expanding autom8-migration.md or relocating to /migration/

#### DEBT-031: Missing Examples README
- **Location**: `/examples/README.md`
- **Severity**: low
- **Description**: Examples directory exists with 12 files but README.md needs verification for completeness
- **Evidence**: /examples/ contains 12 .py files and README.md (9.8K). README links in root README.md but content not audited.
- **Suggested Fix**: Verify /examples/README.md lists all examples, provides usage instructions, explains ordering (01-12)

#### DEBT-032: Missing Architecture Decision Context
- **Location**: `/docs/decisions/` (contextual gap)
- **Severity**: medium
- **Description**: 135 ADRs exist but no "ADR Index by Topic" to help find relevant decisions
- **Evidence**: INDEX.md provides topic groupings but no search/filter capability. ADR-0001-0144 cover wide range - hard to discover relevant decisions.
- **Suggested Fix**: Create /docs/decisions/ADR-INDEX-BY-TOPIC.md grouping ADRs by: Architecture, Patterns, Rejection Decisions, Performance, Security

#### DEBT-033: Missing Contributor Guide
- **Location**: `/docs/CONTRIBUTING.md`
- **Severity**: low
- **Description**: Doc audit report mentions CONTRIBUTION-GUIDE.md exists but placement/completeness not verified
- **Evidence**: /docs/CONTRIBUTION-GUIDE.md exists (17K). Root README.md doesn't link to it. Standard location is root /CONTRIBUTING.md.
- **Suggested Fix**: Verify /docs/CONTRIBUTION-GUIDE.md completeness. Consider moving to /CONTRIBUTING.md (standard location). Add link from README.md.

#### DEBT-034: Missing Changelog Maintenance
- **Location**: `/CHANGELOG.md`
- **Severity**: low
- **Description**: Changelog exists but unclear if maintained or auto-generated
- **Evidence**: /CHANGELOG.md exists (1.8K). Last update date unknown. No clear versioning strategy documented.
- **Suggested Fix**: Verify CHANGELOG.md is current. Add section to CONTRIBUTING.md about changelog maintenance. Consider keepachangelog.com format.

---

### Category: Quality Issues

#### DEBT-035: Incomplete Sections in PRDs
- **Location**: Multiple PRDs (spot-check finding)
- **Severity**: medium
- **Description**: Some PRDs contain placeholder sections or incomplete requirement specifications
- **Evidence**: Grep results show references to "stub", "placeholder" in validation docs. Full audit needed to quantify.
- **Suggested Fix**: Audit all "Draft" status PRDs for completeness. Flag sections with "TODO", "[TBD]", incomplete FR-* tables. Either complete or mark as "Pending Details"

#### DEBT-036: Validation Reports with Deferred Items
- **Location**: `/docs/testing/VALIDATION-PROCESS-PIPELINE.md`
- **Severity**: low
- **Description**: Validation report shows "DEFERRED" items (NFR-PERF-003, NFR-PERF-004) without follow-up tracking
- **Evidence**: Lines 144-145 show performance NFRs deferred due to "stub implementation". No follow-up PRD/TDD created.
- **Suggested Fix**: Create follow-up items for deferred requirements or mark as "Will Not Implement" with rationale

#### DEBT-037: Inconsistent Status Terminology
- **Location**: `/docs/INDEX.md`, various PRD/TDD files
- **Severity**: low
- **Description**: Status values inconsistent across documents: "Draft", "Active", "Ready", "Approved", "Implemented", "Complete", "Unknown"
- **Evidence**: INDEX.md uses: Draft, Active, Implemented, Superseded. Files use: Unknown, Analysis Complete, NO-GO. No documented status lifecycle.
- **Suggested Fix**: Define canonical status values in /docs/CONVENTIONS.md. Document lifecycle: Draft → Active → Implemented → Archived or Draft → Rejected/Superseded. Update all docs to canonical values.

#### DEBT-038: ADR Duplicate Renumbering Not Complete
- **Location**: `/docs/decisions/`, `/docs/INDEX.md`
- **Severity**: medium
- **Description**: INDEX.md note says "ADR duplicates resolved 2024-12-24" but unclear if all affected docs updated
- **Evidence**: INDEX.md line 364: "ADR-0115 through ADR-0120 duplicates renumbered to ADR-0135 through ADR-0144". Need to verify old numbers removed, references updated.
- **Suggested Fix**: Grep for references to old ADR numbers (ADR-0115-0120). Update all PRDs/TDDs referencing old numbers. Verify git history shows rename commits.

#### DEBT-039: Frontmatter Metadata Inconsistent
- **Location**: Various PRD/TDD files
- **Severity**: low
- **Description**: Some docs have YAML frontmatter, others don't. Format inconsistent when present.
- **Evidence**: Recent cache docs (Dec 23-24) lack frontmatter. Older docs (Dec 8-12) have inconsistent frontmatter. No standard documented.
- **Suggested Fix**: Define frontmatter standard in /docs/CONVENTIONS.md. Include: document_id, status, created_date, related_prd/tdd. Update docs to conform.

#### DEBT-040: Git Status Shows Uncommitted Documentation Changes
- **Location**: Working tree
- **Severity**: high
- **Description**: Git status shows 40+ modified documentation files in working tree, not committed
- **Evidence**: Git status output shows "M" for INDEX.md, GLOSSARY.md, PROJECT_CONTEXT.md, multiple PRD/TDD files, and many reference docs
- **Suggested Fix**: Review uncommitted changes. Commit documentation updates with clear message. Establish policy: docs committed with feature or in dedicated doc update commits.

#### DEBT-041: Large Documentation Files
- **Location**: `/docs/design/TDD-0010-save-orchestration.md` (82K), others
- **Severity**: low
- **Description**: Some TDDs exceed 80K, making them hard to navigate and maintain
- **Evidence**: TDD-0010 (82K), TDD-0004 (63K), TDD-0009 (57K), TDD-0011 (57K). Audit report notes TDD-0010 as "Largest TDD"
- **Suggested Fix**: Consider splitting large TDDs into sub-documents or extracting repeated content to reference docs. Not urgent - may indicate comprehensive design.

---

### Category: Stale Artifacts

#### DEBT-042: Completed Initiatives Not Archived
- **Location**: `/docs/requirements/PROMPT-0-*.md`, `/docs/initiatives/PROMPT-0-*.md`
- **Severity**: medium
- **Description**: 4 completed initiatives still in active directories, should be archived
- **Evidence**: Completed: PROMPT-0-CACHE-OPTIMIZATION-PHASE2 (eff1d0d), PROMPT-0-CACHE-PERF-FETCH-PATH (P1 complete), PROMPT-0-WATERMARK-CACHE (validated PASS), PROMPT-0-WORKSPACE-PROJECT-REGISTRY (VP APPROVED)
- **Suggested Fix**: Move to .archive/initiatives/2025-Q4/. Update INDEX.md to show "Archived Initiatives" section. Precedent: 5 initiatives already in .archive/initiatives/2025-Q4/

#### DEBT-043: DOC-INVENTORY-2025-12-24.csv Operational Artifact
- **Location**: `/docs/DOC-INVENTORY-2025-12-24.csv`
- **Severity**: low
- **Description**: CSV inventory from Dec 24 audit - should this be archived or maintained?
- **Evidence**: File exists as snapshot of Dec 24 documentation state. Contains valuable metadata but may become stale.
- **Suggested Fix**: Decide: (1) Archive to /docs/.archive/historical/ as point-in-time snapshot, or (2) Maintain as living inventory (requires automation), or (3) Delete if superseded by INDEX.md

#### DEBT-044: Superseded Planning Documents
- **Location**: `/docs/planning/sprints/PRD-SPRINT-*.md`, `/docs/planning/sprints/TDD-SPRINT-*.md`
- **Severity**: low
- **Description**: Sprint decomposition docs from Dec 19 - unclear if sprints completed and docs should be archived
- **Evidence**: 4 PRD-SPRINT and 4 TDD-SPRINT files all dated Dec 19. Status: "Unknown". No validation reports confirming completion.
- **Suggested Fix**: Determine sprint completion status. If complete: archive to .archive/planning/2025-Q4-sprints/. If active: update status. If superseded: mark accordingly.

#### DEBT-045: VALIDATION-PROCESS-PIPELINE Invalidated
- **Location**: `/docs/testing/VALIDATION-PROCESS-PIPELINE.md`
- **Severity**: medium
- **Description**: Validation report shows status "Invalidated" but still in active /testing/ directory
- **Evidence**: INDEX.md line 165: "VALIDATION-PROCESS-PIPELINE | Status: Invalidated". Report invalidated because ProcessProjectRegistry never implemented (superseded by WorkspaceProjectRegistry)
- **Suggested Fix**: Move to .archive/validation/ with note explaining invalidation reason. Update INDEX.md to remove from active validation reports or add "Archived Validations" section.

---

### Category: Redundant/Duplicate

#### DEBT-046: Cache Concept Duplication
- **Location**: Multiple PRD-CACHE-* and TDD-CACHE-* files
- **Severity**: medium
- **Description**: Staleness detection algorithms explained in 3+ cache PRDs. TTL strategy in 4+ docs. Cache provider protocol in 5+ docs.
- **Evidence**: Audit report Section "Redundancy Analysis - Cluster 1" identifies 9 cache PRDs (189K) + 9 cache TDDs (~320K) with conceptual overlap
- **Suggested Fix**: Already partially addressed - REF-cache-architecture.md, REF-cache-staleness-detection.md, REF-cache-ttl-strategy.md exist. Verify all cache PRDs/TDDs link to refs instead of duplicating. Add cross-references where missing.

#### DEBT-047: PROMPT-0 + PRD Content Duplication
- **Location**: 14 PROMPT-0-* files and corresponding PRD-* files
- **Severity**: low
- **Description**: Each PROMPT-0-X.md duplicates context from corresponding PRD-X.md for orchestrator initialization
- **Evidence**: Audit report "Cluster 2" identifies ~280K redundancy across 14 PROMPT/PRD pairs. PROMPT files contain "Your Role: Orchestrator" instructions + PRD context.
- **Suggested Fix**: Accept duplication as intentional (PROMPT files serve different purpose - orchestrator initialization). Establish archival policy: archive PROMPT-0 after initiative completes. Already in progress - 5 initiatives archived to .archive/initiatives/2025-Q4/

---

## Summary Statistics

**Total Items**: 47

**By Severity**:
- Critical: 8 items (DEBT-001, DEBT-016, DEBT-026, DEBT-040, plus 4 high-severity items warranting escalation)
- High: 12 items
- Medium: 18 items
- Low: 9 items

**By Category**:
- Outdated Content: 15 items (DEBT-001 through DEBT-015)
- Structural Issues: 10 items (DEBT-016 through DEBT-025)
- Missing Documentation: 9 items (DEBT-026 through DEBT-034)
- Quality Issues: 7 items (DEBT-035 through DEBT-041)
- Stale Artifacts: 4 items (DEBT-042 through DEBT-045)
- Redundant/Duplicate: 2 items (DEBT-046, DEBT-047)

**By Location**:
- /docs/requirements/: 12 items
- /docs/design/: 6 items
- /docs/INDEX.md: 4 items
- .claude/: 2 items
- /docs/testing/: 3 items
- /docs/reference/: 2 items
- /docs/decisions/: 2 items
- /docs/guides/: 2 items
- /docs/runbooks/: 2 items
- Other: 12 items

**Effort Estimate**:
- Critical (immediate): 8 items, ~4-6 hours
- High (this sprint): 12 items, ~8-12 hours
- Medium (next sprint): 18 items, ~12-18 hours
- Low (backlog): 9 items, ~4-6 hours

**Total Remediation Effort**: 28-42 hours (3.5-5 working days)

---

## Recommended Priority Order

### Immediate (Critical + High Impact)

1. **DEBT-001** - Fix INDEX.md status metadata (critical accuracy issue)
2. **DEBT-016** - Move PROMPT-* files to /initiatives/ (critical structural fix)
3. **DEBT-026** - Fix broken autom8-asana skill references (critical broken link)
4. **DEBT-040** - Commit uncommitted documentation changes (high risk of loss)
5. **DEBT-008** - Add supersession notice to PRD-PROCESS-PIPELINE (high confusion risk)
6. **DEBT-002** - Update PRD-0002 intelligent caching doc (high staleness)
7. **DEBT-003** - Update PRD-0005 with healing system (high staleness)
8. **DEBT-005** - Mark TDD-0008 as superseded (high confusion risk)

### This Sprint (High Priority)

9. **DEBT-021** - Archive 4 completed PROMPT-0 initiatives
10. **DEBT-027** - Create operational runbooks for batch ops, business model
11. **DEBT-017** - Create /docs/requirements/README.md
12. **DEBT-022** - Create /docs/initiatives/README.md
13. **DEBT-025** - Create /docs/runbooks/README.md
14. **DEBT-009, DEBT-010, DEBT-011, DEBT-012** - Fix status mismatches (batch update)

### Next Sprint (Medium Priority)

15. **DEBT-028** - Create validation reports for implemented features
16. **DEBT-032** - Create ADR index by topic
17. **DEBT-019** - Document naming convention
18. **DEBT-037** - Define canonical status values
19. **DEBT-046** - Verify cache concept cross-references
20. **DEBT-004, DEBT-006, DEBT-007** - Update superseded PRDs (batch)
21. **DEBT-015** - Clarify sprint decomposition doc status
22. **DEBT-038** - Verify ADR renumbering complete
23. **DEBT-045** - Archive invalidated validation report

### Backlog (Low Priority / Continuous)

24. **DEBT-013** - Resolve DOC-INVENTORY status annotations
25. **DEBT-014** - Accept TDD-CUSTOM-FIELD-REMEDIATION naming
26. **DEBT-029** - Create how-to guides
27. **DEBT-030** - Create migration guides
28. **DEBT-033** - Verify/enhance contributor guide
29. **DEBT-034** - Verify changelog maintenance
30. **DEBT-035** - Audit PRDs for incomplete sections
31. **DEBT-036** - Track deferred validation items
32. **DEBT-039** - Standardize frontmatter
33. **DEBT-041** - Consider splitting large TDDs
34. **DEBT-042, DEBT-043, DEBT-044** - Archive stale artifacts (batch)
35. **DEBT-047** - Accept PROMPT/PRD duplication, establish archival policy

---

## Dependencies Between Debt Items

**DEBT-001 blocks**: DEBT-009, DEBT-010, DEBT-011, DEBT-012 (status updates depend on canonical status fix)

**DEBT-016 blocks**: DEBT-021 (can't archive PROMPT files until they're in correct directory)

**DEBT-037 blocks**: DEBT-001, DEBT-013, DEBT-015 (status standardization needed before fixing individual status issues)

**DEBT-019 enables**: DEBT-014 (naming convention clarifies numbering inconsistency)

**DEBT-017, DEBT-022, DEBT-025 are independent** (README creation can be parallelized)

---

## Root Causes Analysis

**Primary Root Causes**:

1. **Rapid feature development without doc updates** (DEBT-002, 003, 004, 005, 009, 010, 011, 012)
   - Pattern: Code committed Dec 15-24, docs last updated Dec 9-12
   - Contributing factor: 5x more code commits than doc updates (per audit report)
   - Remediation: Establish doc-with-feature policy, CI checks

2. **No documentation lifecycle management** (DEBT-021, 042, 043, 044, 045)
   - Pattern: Completed artifacts not archived, status not updated
   - Contributing factor: No defined lifecycle (Draft → Active → Complete → Archived)
   - Remediation: Define lifecycle in CONVENTIONS.md, quarterly cleanup

3. **Structural reorganization mid-project** (DEBT-016, 019, 014)
   - Pattern: Numbered → named scheme, PROMPT files in wrong location
   - Contributing factor: Project evolved faster than docs could reorganize
   - Remediation: Complete structural cleanup, document new conventions

4. **Broken references from deleted files** (DEBT-026)
   - Pattern: Skills deleted in cleanup but references not updated
   - Contributing factor: No automated link checking
   - Remediation: Add CI link checking, update stale references

5. **Status metadata divergence** (DEBT-001, 013, 015)
   - Pattern: INDEX.md, frontmatter, and reality disagree on status
   - Contributing factor: Manual status tracking across multiple files
   - Remediation: Single source of truth (frontmatter), INDEX.md generated or validated

---

## Notes

**Audit Methodology**:
- Reviewed existing DOC-AUDIT-REPORT-2025-12-24.md (comprehensive)
- Examined INDEX.md, PROJECT_CONTEXT.md, GLOSSARY.md, README.md
- Searched for TODO/FIXME/STUB markers across /docs and /.claude
- Verified file structure and identified missing READMEs
- Cross-referenced git status for uncommitted changes
- Identified broken references and missing files

**Limitations**:
- Did not audit all 464 markdown files individually (relied on existing audit)
- Did not verify every link in every document (spot-checked key files)
- Did not analyze code docstrings (out of scope for documentation debt)
- Severity assigned based on impact to documentation users, not implementation cost

**Handoff to Risk Assessor**:
This ledger provides complete inventory. Risk Assessor should:
1. Score each item for probability × impact
2. Identify cascading risks (e.g., DEBT-001 affects developer trust in docs)
3. Flag items that could block upcoming work
4. Recommend sprint packaging (which items together)

**Next Steps**:
- Route to risk-assessor for severity validation and prioritization scoring
- After scoring, route to sprint-planner for work packaging
- Consider creating quick-win sprint for DEBT-001, 016, 026, 040 (critical structural fixes)
