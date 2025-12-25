---
report_id: "RISK-doc-debt-inventory"
created_at: "2025-12-24"
session_id: "session-20251224-232654-1a1ac669"
assessed_items: 47
methodology: "Probability × Impact matrix (1-5 scale)"
---

# Documentation Debt Risk Report

## Executive Summary

**Bottom Line**: 47 documentation debt items assessed. 6 items classified as Critical (risk score 20-25), requiring immediate attention to prevent developer confusion, workflow disruption, and trust erosion in documentation.

**Key Findings**:
1. **Trust Crisis**: INDEX.md status metadata affects 13+ PRDs - developers cannot rely on documentation index as source of truth (DEBT-001, Risk Score: 25)
2. **Broken Navigation**: Deleted autom8-asana skill breaks PROJECT_CONTEXT.md references - new developers cannot onboard (DEBT-026, Risk Score: 20)
3. **Data Loss Risk**: 40+ uncommitted documentation changes at risk of loss (DEBT-040, Risk Score: 20)
4. **Structural Chaos**: 15 PROMPT-* files mislocated, breaking documentation taxonomy (DEBT-016, Risk Score: 20)
5. **Cascading Confusion**: Superseded PRDs marked "Active" cause wasted implementation effort (DEBT-008, Risk Score: 16)

**Immediate Recommended Actions**:
1. Commit uncommitted changes within 24 hours (prevents data loss)
2. Fix INDEX.md status metadata (restores trust in documentation)
3. Restore or replace autom8-asana skill references (unblocks onboarding)
4. Move PROMPT-* files to correct directory (fixes taxonomy)

**Total Estimated Remediation**: 28-42 hours (3.5-5 working days)
- Critical items: 6 items, 6-8 hours
- High priority: 11 items, 10-14 hours
- Medium priority: 20 items, 10-16 hours
- Low priority: 10 items, 2-4 hours

---

## Risk Matrix

| Risk Level | Count | Risk Score Range | Items |
|------------|-------|------------------|-------|
| **Critical** (20-25) | 6 | 20-25 | DEBT-001, DEBT-016, DEBT-026, DEBT-040, DEBT-008, DEBT-005 |
| **High** (12-19) | 11 | 12-16 | DEBT-002, DEBT-003, DEBT-027, DEBT-021, DEBT-038, DEBT-046, DEBT-009, DEBT-010, DEBT-011, DEBT-045, DEBT-037 |
| **Medium** (6-11) | 20 | 6-10 | DEBT-004, 006, 007, 012, 015, 017, 018, 022, 025, 028, 032, 035, 042, 044, 020, 023, 024, 031, 036, 039 |
| **Low** (1-5) | 10 | 1-5 | DEBT-013, 014, 019, 029, 030, 033, 034, 041, 043, 047 |

---

## Critical Priority Items (Risk Score 20-25)

### DEBT-001: INDEX.md Status Metadata Stale
- **Original Severity**: Critical (confirmed)
- **Probability**: 5/5 - Already causing problems. Every developer using INDEX.md as source of truth receives incorrect information.
- **Impact**: 5/5 - Affects 13+ PRDs. Developers cannot trust documentation index, leads to implementation of wrong features, wasted effort, confusion about what's actually implemented.
- **Risk Score**: 25 (Catastrophic)
- **Validated Severity**: Critical
- **Cascading Risks**:
  - DEBT-009, 010, 011, 012 (other status mismatches stem from same root cause)
  - DEBT-013 (DOC-INVENTORY annotations unresolved)
  - DEBT-037 (inconsistent status terminology compounds the problem)
  - Erodes trust in all documentation when index is unreliable
- **Trigger Conditions**: Every time a developer checks INDEX.md for feature status
- **Effort to Fix**: 2-3 hours (audit 13+ PRDs, update INDEX.md, verify consistency)
- **Recommendation**: **Address immediately - Sprint 1, P0**. This is a trust crisis. Until fixed, developers cannot rely on documentation.

### DEBT-016: PROMPT-* Files Mislocated
- **Original Severity**: Critical (confirmed)
- **Probability**: 4/5 - High probability. Affects anyone navigating /docs/requirements/ or /initiatives/ directories. Already causing confusion.
- **Impact**: 5/5 - Breaks documentation taxonomy. 15 files in wrong location. Developers searching /initiatives/ won't find initiative files. Confuses purpose of /requirements/ directory.
- **Risk Score**: 20 (Critical)
- **Validated Severity**: Critical
- **Cascading Risks**:
  - DEBT-021 (archival policy blocked - can't archive files until they're in correct directory)
  - DEBT-022 (can't write initiatives README without fixing structure first)
  - DEBT-017 (requirements README harder to explain with initiative files mixed in)
  - Affects INDEX.md accuracy (paths are wrong)
- **Trigger Conditions**: Every time developer navigates documentation structure or searches for initiative files
- **Effort to Fix**: 1 hour (move 15 files, update INDEX.md paths)
- **Recommendation**: **Address immediately - Sprint 1, P0**. Structural fix enables other improvements.

### DEBT-026: autom8-asana Skill Documentation Deleted
- **Original Severity**: Critical (confirmed)
- **Probability**: 4/5 - High probability. Affects new developers, anyone reading PROJECT_CONTEXT.md, Claude Code skill lookups.
- **Impact**: 5/5 - Broken reference in primary onboarding doc. New developers hit dead link immediately. Claude Code cannot resolve skill references. No paradigm documentation available.
- **Risk Score**: 20 (Critical)
- **Validated Severity**: Critical
- **Cascading Risks**:
  - Blocks onboarding workflow
  - Forces developers to reverse-engineer paradigm from code
  - May affect other .claude/ files referencing the skill
- **Trigger Conditions**: Every new developer reading PROJECT_CONTEXT.md, every Claude Code skill lookup
- **Effort to Fix**: 1-2 hours (restore from git or update references to docs/architecture/DOC-ARCHITECTURE.md)
- **Recommendation**: **Address immediately - Sprint 1, P0**. Broken onboarding is critical path issue.

### DEBT-040: Git Status Shows Uncommitted Documentation Changes
- **Original Severity**: High → Critical (escalated)
- **Probability**: 4/5 - High probability. 40+ modified files at risk. One `git reset --hard` or branch switch destroys work.
- **Impact**: 5/5 - Data loss risk. Hours of documentation work could vanish. Unclear what's been reviewed vs. work-in-progress. Blocks handoff between developers.
- **Risk Score**: 20 (Critical)
- **Validated Severity**: Critical (escalated from High)
- **Cascading Risks**:
  - All documentation debt remediation builds on unstable foundation
  - Can't assess true state of documentation until changes committed
  - Risk of merge conflicts if work continues in parallel
- **Trigger Conditions**: Git branch switch, reset, merge, or developer error
- **Effort to Fix**: 30 minutes (review changes, commit with clear message)
- **Recommendation**: **Address immediately - Today**. Commit before any other work. Non-negotiable risk mitigation.

### DEBT-008: PRD-PROCESS-PIPELINE Partially Superseded
- **Original Severity**: High → Critical (escalated based on risk)
- **Probability**: 4/5 - High probability. Developers reading PRD-PROCESS-PIPELINE will attempt to implement ProcessProjectRegistry (already rejected).
- **Impact**: 4/5 - Wasted implementation effort. Rejected architecture (ADR-0101) could be re-implemented by developer unaware of decision. Causes confusion about actual implementation (WorkspaceProjectRegistry).
- **Risk Score**: 16 (Critical threshold)
- **Validated Severity**: Critical (escalated from High)
- **Cascading Risks**:
  - DEBT-045 (VALIDATION-PROCESS-PIPELINE invalidated - same root cause)
  - Wastes developer time implementing wrong feature
  - Creates technical debt if implemented before discovery
- **Trigger Conditions**: Developer assigned to implement process pipeline without reading ADR-0101
- **Effort to Fix**: 30 minutes (add supersession notice, mark FR-REG-* as superseded)
- **Recommendation**: **Address immediately - Sprint 1, P0**. Prevent wasted implementation effort.

### DEBT-005: TDD-0008 Intelligent Caching Architecture Stale
- **Original Severity**: High → Critical (escalated based on cascading impact)
- **Probability**: 4/5 - High probability. TDD-0008 is primary cache architecture doc. Developers will read it first.
- **Impact**: 4/5 - Describes original vision from Dec 9, but architecture evolved to multi-tier, staleness detection, progressive TTL by Dec 24. Developers implementing from TDD-0008 will build wrong architecture.
- **Risk Score**: 16 (Critical threshold)
- **Validated Severity**: Critical (escalated from High)
- **Cascading Risks**:
  - DEBT-002 (PRD-0002 also stale - cache docs family-wide issue)
  - DEBT-046 (cache concept duplication across 9 PRDs + 9 TDDs)
  - Affects understanding of current cache implementation
  - REF-cache-architecture.md may not be discoverable
- **Trigger Conditions**: Developer implementing cache feature, reviewing cache architecture, or onboarding to cache system
- **Effort to Fix**: 1 hour (mark as superseded, link to TDD-CACHE-* series and REF-cache-architecture.md)
- **Recommendation**: **Address immediately - Sprint 1, P0**. Cache is critical system - stale architecture doc is high risk.

---

## High Priority Items (Risk Score 12-16)

### DEBT-002: PRD-0002 Intelligent Caching Doc Stale
- **Probability**: 4/5 - Affects all cache-related work
- **Impact**: 3/5 - PRD missing recent features but not primary cache doc
- **Risk Score**: 12
- **Validated Severity**: High (confirmed)
- **Cascading Risks**: Compounds DEBT-005, part of cache documentation family issue
- **Recommendation**: Sprint 1. Update or mark superseded by PRD-CACHE-* series.

### DEBT-003: PRD-0005 Save Orchestration Missing Healing System
- **Probability**: 4/5 - SaveSession is core feature, healing system is significant addition
- **Impact**: 4/5 - Missing self-healing capabilities, HealingResult consolidation. Developers won't know feature exists.
- **Risk Score**: 16
- **Validated Severity**: High (confirmed)
- **Cascading Risks**: SaveSession is critical path - incomplete docs affect all workflows using it
- **Recommendation**: Sprint 1. Add healing system section or create PRD-SAVESESSION-HEALING.

### DEBT-027: Missing Operational Runbooks
- **Probability**: 3/5 - Triggered when operational issues arise (moderate frequency)
- **Impact**: 4/5 - Batch operations, business model navigation, automation troubleshooting lack ops docs. Extends incident resolution time.
- **Risk Score**: 12
- **Validated Severity**: High (confirmed)
- **Cascading Risks**: Each incident without runbook wastes 2-4 hours of troubleshooting. Compounds over time.
- **Recommendation**: Sprint 1-2. Create RUNBOOK-batch-operations.md, RUNBOOK-business-model-navigation.md as highest priority.

### DEBT-021: Archival Candidates Not Archived
- **Probability**: 3/5 - Affects developers searching for current work vs. completed initiatives
- **Impact**: 4/5 - 4 completed initiatives cluttering active directories. Causes confusion about what's in flight.
- **Risk Score**: 12
- **Validated Severity**: Medium → High (escalated)
- **Cascading Risks**: Blocked by DEBT-016. Can't archive until files in correct directory.
- **Recommendation**: Sprint 1, immediately after DEBT-016 resolved.

### DEBT-038: ADR Duplicate Renumbering Not Complete
- **Probability**: 3/5 - Affects anyone referencing ADR-0115 through ADR-0120
- **Impact**: 4/5 - If old numbers still referenced, creates broken links and confusion. ADRs are critical decision records.
- **Risk Score**: 12
- **Validated Severity**: Medium → High (escalated)
- **Cascading Risks**: ADRs inform implementation decisions. Broken references lead to wrong decisions.
- **Recommendation**: Sprint 1. Grep for old ADR numbers, update all references.

### DEBT-046: Cache Concept Duplication
- **Probability**: 3/5 - Affects developers learning cache system
- **Impact**: 4/5 - Staleness detection in 3+ docs, TTL in 4+ docs, provider protocol in 5+ docs. Developer must read 9 PRDs + 9 TDDs to understand cache (189K + 320K).
- **Risk Score**: 12
- **Validated Severity**: Medium → High (escalated based on learning burden)
- **Cascading Risks**: Part of cache documentation family issue (DEBT-002, 005)
- **Recommendation**: Sprint 1-2. Verify all cache PRDs/TDDs link to REF-cache-*.md instead of duplicating.

### DEBT-009, 010, 011: Status Mismatches (batch)
- **Probability**: 4/5 - Each affects developers checking feature status
- **Impact**: 3/5 - Individual mismatch less severe than DEBT-001, but cumulative effect is high
- **Risk Score**: 12 each
- **Validated Severity**: Medium → High (escalated as batch)
- **Cascading Risks**: All stem from DEBT-001 root cause. Fix DEBT-001 first, then batch-fix these.
- **Recommendation**: Sprint 1, immediately after DEBT-001 resolved.

### DEBT-045: VALIDATION-PROCESS-PIPELINE Invalidated
- **Probability**: 3/5 - Affects anyone reviewing validation reports
- **Impact**: 4/5 - Status "Invalidated" but still in active directory. Confuses validation status.
- **Risk Score**: 12
- **Validated Severity**: Medium → High (escalated)
- **Cascading Risks**: Related to DEBT-008 (same rejected feature)
- **Recommendation**: Sprint 1. Archive to .archive/validation/ with invalidation note.

### DEBT-037: Inconsistent Status Terminology
- **Probability**: 4/5 - Affects all documentation status tracking
- **Impact**: 3/5 - 7+ different status values across docs. No canonical lifecycle.
- **Risk Score**: 12
- **Validated Severity**: Low → High (escalated - this is root cause of DEBT-001)
- **Cascading Risks**: **Blocks DEBT-001 resolution**. Must define canonical status values before fixing individual mismatches.
- **Recommendation**: Sprint 1, **before DEBT-001**. Define status lifecycle in /docs/CONVENTIONS.md.

---

## Medium Priority Items (Risk Score 6-10)

### DEBT-004: PRD-0010 Business Model Layer Outdated
- **Probability**: 2/5 - Affects developers working on business model enhancements
- **Impact**: 3/5 - Missing stub model enhancements but not blocking
- **Risk Score**: 6
- **Validated Severity**: Medium (confirmed)
- **Recommendation**: Sprint 2. Update to reflect foundation hardening.

### DEBT-006: PRD-0021 Async Method Generator Superseded
- **Probability**: 3/5 - Affects developers implementing async patterns
- **Impact**: 3/5 - Describes @async_method_generator but actual implementation is @async_method decorator
- **Risk Score**: 9
- **Validated Severity**: Medium (confirmed)
- **Recommendation**: Sprint 2. Mark as superseded, link to decorator pattern.

### DEBT-007: PRD-0022 CRUD Base Class Rejected But Active
- **Probability**: 3/5 - Affects developers exploring CRUD patterns
- **Impact**: 3/5 - PRD marked "Active" but TDD-0026 has explicit "NO-GO" decision
- **Risk Score**: 9
- **Validated Severity**: Medium (confirmed)
- **Recommendation**: Sprint 2. Update INDEX.md to "Rejected", link to TDD-0026.

### DEBT-012: PRD-TECH-DEBT-REMEDIATION Status Unknown
- **Probability**: 2/5 - Low frequency access
- **Impact**: 3/5 - Status unclear but feature implemented
- **Risk Score**: 6
- **Validated Severity**: Low → Medium (escalated slightly)
- **Recommendation**: Sprint 2. Batch with DEBT-009, 010, 011 status fixes.

### DEBT-015: Sprint Decomposition Docs Status Unknown
- **Probability**: 2/5 - Affects sprint planning workflow
- **Impact**: 4/5 - 4 sprint docs unclear if planning vs. formal PRDs. High impact if misunderstood.
- **Risk Score**: 8
- **Validated Severity**: Medium (confirmed)
- **Recommendation**: Sprint 2. Clarify document type, archive if completed.

### DEBT-017: Missing README in Requirements Directory
- **Probability**: 3/5 - Affects new developers exploring /docs/requirements/
- **Impact**: 3/5 - No explanation of PRD purpose, numbering, directory organization
- **Risk Score**: 9
- **Validated Severity**: Medium (confirmed)
- **Cascading Risks**: Blocked by DEBT-016 (easier to write after PROMPT-* files moved)
- **Recommendation**: Sprint 1-2. Create after DEBT-016 resolved.

### DEBT-018: Missing README in Design Directory
- **Probability**: 2/5 - Affects new developers exploring /docs/design/
- **Impact**: 3/5 - README may exist but needs verification for completeness
- **Risk Score**: 6
- **Validated Severity**: Medium (confirmed)
- **Recommendation**: Sprint 2. Verify and enhance if needed.

### DEBT-022: Missing Initiatives README
- **Probability**: 3/5 - Affects developers using PROMPT-0 workflow
- **Impact**: 3/5 - No explanation of PROMPT-0 vs PROMPT-MINUS-1, initiative lifecycle
- **Risk Score**: 9
- **Validated Severity**: Medium (confirmed)
- **Cascading Risks**: Blocked by DEBT-016 (must move files first)
- **Recommendation**: Sprint 1-2. Create after DEBT-016 resolved.

### DEBT-025: Runbooks Directory Missing README
- **Probability**: 2/5 - Affects ops personnel and developers during incidents
- **Impact**: 4/5 - No explanation of runbook purpose, when to create, severity classification
- **Risk Score**: 8
- **Validated Severity**: Medium (confirmed)
- **Recommendation**: Sprint 2. Create with DEBT-027 (runbook creation sprint).

### DEBT-028: Missing Test Plans for Implemented Features
- **Probability**: 2/5 - Affects QA workflow, feature validation
- **Impact**: 4/5 - 8+ implemented features lack formal Test Plan or Validation Report. Unclear if tested.
- **Risk Score**: 8
- **Validated Severity**: Medium (confirmed)
- **Recommendation**: Sprint 2-3. Create VPs for SaveSession, Cache Integration as priority.

### DEBT-032: Missing Architecture Decision Context
- **Probability**: 2/5 - Affects developers searching for relevant ADRs
- **Impact**: 4/5 - 135 ADRs hard to discover. No ADR index by topic.
- **Risk Score**: 8
- **Validated Severity**: Medium (confirmed)
- **Recommendation**: Sprint 2. Create /docs/decisions/ADR-INDEX-BY-TOPIC.md.

### DEBT-035: Incomplete Sections in PRDs
- **Probability**: 2/5 - Affects developers implementing from PRDs
- **Impact**: 4/5 - Some PRDs have placeholder sections. Unclear what's complete vs. TBD.
- **Risk Score**: 8
- **Validated Severity**: Medium (confirmed)
- **Recommendation**: Sprint 3. Audit all "Draft" PRDs, flag incomplete sections.

### DEBT-042: Completed Initiatives Not Archived
- **Probability**: 2/5 - Affects developers distinguishing current vs. completed work
- **Impact**: 3/5 - 4 completed initiatives cluttering directories
- **Risk Score**: 6
- **Validated Severity**: Medium (confirmed)
- **Recommendation**: Sprint 2. Batch with DEBT-021 (same archival policy).

### DEBT-044: Superseded Planning Documents
- **Probability**: 2/5 - Affects sprint planning workflow
- **Impact**: 3/5 - 4 PRD-SPRINT + 4 TDD-SPRINT docs unclear if completed
- **Risk Score**: 6
- **Validated Severity**: Low → Medium (escalated slightly)
- **Recommendation**: Sprint 2-3. Determine status, archive if complete.

### DEBT-020: INDEX.md Document Number Allocation Section Incomplete
- **Probability**: 2/5 - Affects developers creating new PRDs
- **Impact**: 3/5 - Section doesn't reflect named scheme preference
- **Risk Score**: 6
- **Validated Severity**: Low → Medium (escalated slightly)
- **Recommendation**: Sprint 2. Add note about named scheme preference.

### DEBT-023: Decisions Directory Missing README
- **Probability**: 2/5 - Affects new developers understanding ADR format
- **Impact**: 3/5 - 135 ADRs with no directory-level explanation
- **Risk Score**: 6
- **Validated Severity**: Low → Medium (escalated slightly)
- **Recommendation**: Sprint 2. Create /docs/decisions/README.md.

### DEBT-024: Testing Directory Missing README
- **Probability**: 2/5 - Affects QA workflow understanding
- **Impact**: 3/5 - TP vs VP difference not explained
- **Risk Score**: 6
- **Validated Severity**: Low → Medium (escalated slightly)
- **Recommendation**: Sprint 2. Create /docs/testing/README.md.

### DEBT-031: Missing Examples README
- **Probability**: 2/5 - Affects new developers exploring examples
- **Impact**: 3/5 - README exists but completeness not verified
- **Risk Score**: 6
- **Validated Severity**: Low → Medium (escalated slightly)
- **Recommendation**: Sprint 3. Verify completeness.

### DEBT-036: Validation Reports with Deferred Items
- **Probability**: 2/5 - Affects long-term NFR tracking
- **Impact**: 3/5 - Deferred performance NFRs lack follow-up
- **Risk Score**: 6
- **Validated Severity**: Low → Medium (escalated slightly)
- **Recommendation**: Sprint 3. Create follow-up items or mark as "Will Not Implement".

### DEBT-039: Frontmatter Metadata Inconsistent
- **Probability**: 2/5 - Affects documentation automation, parsing
- **Impact**: 3/5 - Some docs have YAML frontmatter, others don't. No standard.
- **Risk Score**: 6
- **Validated Severity**: Low → Medium (escalated slightly)
- **Recommendation**: Sprint 3. Define standard in /docs/CONVENTIONS.md.

---

## Low Priority Items (Risk Score 1-5)

### DEBT-013: DOC-INVENTORY Status Annotations Unresolved
- **Probability**: 1/5 - CSV inventory is point-in-time artifact
- **Impact**: 2/5 - Annotations helpful but resolving doesn't change underlying docs
- **Risk Score**: 2
- **Validated Severity**: Low (confirmed)
- **Recommendation**: Backlog. Resolve as part of status standardization effort (DEBT-037).

### DEBT-014: TDD-CUSTOM-FIELD-REMEDIATION Numbering Inconsistency
- **Probability**: 1/5 - Rarely accessed, naming is acceptable
- **Impact**: 2/5 - Should be TDD-0030 but named format is fine
- **Risk Score**: 2
- **Validated Severity**: Low (confirmed)
- **Recommendation**: Backlog. Accept named format, clarify in INDEX.md.

### DEBT-019: Inconsistent Numbering Pattern
- **Probability**: 2/5 - Affects new PRD/TDD creation
- **Impact**: 2/5 - Pattern switched but no documented convention
- **Risk Score**: 4
- **Validated Severity**: Low (confirmed)
- **Recommendation**: Backlog. Document in /docs/CONVENTIONS.md with DEBT-037.

### DEBT-029: Missing How-To Guides
- **Probability**: 2/5 - Affects specific workflows
- **Impact**: 2/5 - Pattern docs exist, how-tos are enhancement
- **Risk Score**: 4
- **Validated Severity**: Medium → Low (de-escalated)
- **Recommendation**: Backlog. Create as continuous improvement.

### DEBT-030: Missing Migration Guides
- **Probability**: 1/5 - Affects legacy migration scenarios
- **Impact**: 3/5 - Helpful for migrations but limited audience
- **Risk Score**: 3
- **Validated Severity**: Low (confirmed)
- **Recommendation**: Backlog. Create if migration need arises.

### DEBT-033: Missing Contributor Guide
- **Probability**: 1/5 - Guide exists, placement needs verification
- **Impact**: 3/5 - Standard location issue, not missing content
- **Risk Score**: 3
- **Validated Severity**: Low (confirmed)
- **Recommendation**: Backlog. Verify and move to standard location.

### DEBT-034: Missing Changelog Maintenance
- **Probability**: 1/5 - Changelog exists, maintenance unclear
- **Impact**: 3/5 - Helpful for version tracking
- **Risk Score**: 3
- **Validated Severity**: Low (confirmed)
- **Recommendation**: Backlog. Verify currency, establish maintenance policy.

### DEBT-041: Large Documentation Files
- **Probability**: 1/5 - Large TDDs may indicate comprehensive design
- **Impact**: 2/5 - Navigation slightly harder but manageable
- **Risk Score**: 2
- **Validated Severity**: Low (confirmed)
- **Recommendation**: Backlog. Consider splitting only if navigation becomes problem.

### DEBT-043: DOC-INVENTORY-2025-12-24.csv Operational Artifact
- **Probability**: 1/5 - Point-in-time snapshot
- **Impact**: 2/5 - Archive vs. maintain decision
- **Risk Score**: 2
- **Validated Severity**: Low (confirmed)
- **Recommendation**: Backlog. Archive to /docs/.archive/historical/.

### DEBT-047: PROMPT-0 + PRD Content Duplication
- **Probability**: 1/5 - Intentional duplication for orchestrator
- **Impact**: 2/5 - Archival policy resolves over time
- **Risk Score**: 2
- **Validated Severity**: Low (confirmed)
- **Recommendation**: Backlog. Accept duplication, follow archival policy (DEBT-021).

---

## Cascading Risk Analysis

### Cascade 1: Documentation Trust Crisis
**Root**: DEBT-037 (Inconsistent status terminology)
**→** DEBT-001 (INDEX.md status metadata stale)
**→** DEBT-009, 010, 011, 012 (Individual status mismatches)
**→** DEBT-013 (DOC-INVENTORY annotations)

**Impact**: Developers cannot trust documentation index. Every feature status check requires manual verification. Wastes 10-15 minutes per feature lookup across team.

**Trigger**: Every documentation query
**Mitigation**: Fix DEBT-037 first (define canonical statuses), then DEBT-001 (fix INDEX.md), then batch-fix individual mismatches.

---

### Cascade 2: Structural Reorganization Blocked
**Root**: DEBT-016 (PROMPT-* files mislocated)
**→** DEBT-021 (Can't archive until files in correct directory)
**→** DEBT-022 (Can't write initiatives README without stable structure)
**→** DEBT-017 (Requirements README harder with mixed files)

**Impact**: 15 files in wrong location block 3 downstream improvements. Directory structure unreliable for navigation.

**Trigger**: Any directory navigation or README creation
**Mitigation**: Fix DEBT-016 immediately (1 hour effort), unblocks 3 downstream items.

---

### Cascade 3: Cache Documentation Family Issue
**Root**: Cache system evolved faster than docs (Dec 9 → Dec 24)
**→** DEBT-005 (TDD-0008 stale architecture)
**→** DEBT-002 (PRD-0002 stale requirements)
**→** DEBT-046 (Cache concept duplication across 18 docs)

**Impact**: 9 PRDs + 9 TDDs (189K + 320K) with conceptual overlap. Developers must read entire family to understand cache. Learning burden 4-6 hours.

**Trigger**: Any cache implementation or learning
**Mitigation**: Fix DEBT-005 first (mark TDD-0008 superseded, link to current architecture), then DEBT-002 (update or supersede PRD-0002), then DEBT-046 (consolidate to REF-cache-*.md references).

---

### Cascade 4: Superseded Features Active
**Root**: Features rejected but PRDs not updated
**→** DEBT-008 (PRD-PROCESS-PIPELINE partially superseded)
**→** DEBT-045 (VALIDATION-PROCESS-PIPELINE invalidated)
**→** DEBT-006 (PRD-0021 superseded)
**→** DEBT-007 (PRD-0022 rejected but Active)

**Impact**: Developers implement rejected features, waste 1-2 days per incident. Historical: ProcessProjectRegistry almost re-implemented before ADR-0101 discovered.

**Trigger**: Developer assigned feature implementation without ADR review
**Mitigation**: Add supersession notices immediately (DEBT-008, 006, 007). Archive invalidated validations (DEBT-045). Establish policy: link rejections from PRD to ADR.

---

### Cascade 5: Onboarding Workflow Broken
**Root**: DEBT-026 (autom8-asana skill deleted)
**→** PROJECT_CONTEXT.md references broken
**→** No paradigm documentation discoverable
**→** New developers forced to reverse-engineer from code

**Impact**: Onboarding time +2-4 hours per developer. Risk of paradigm misunderstanding, incorrect implementation patterns.

**Trigger**: Every new developer onboarding, every Claude Code skill lookup
**Mitigation**: Restore skill or update references to docs/architecture/DOC-ARCHITECTURE.md within 24 hours.

---

## Recommended Sprint Packages

### Sprint 1: Critical Path (6 items, 6-8 hours)
**Theme**: Restore documentation trust and structural integrity

**Must fix before other work**:
1. **DEBT-040** (30 min) - Commit uncommitted changes - **DO THIS FIRST**
2. **DEBT-037** (1 hour) - Define canonical status values in /docs/CONVENTIONS.md - **BLOCKS DEBT-001**
3. **DEBT-001** (2-3 hours) - Fix INDEX.md status metadata - **TRUST RESTORATION**
4. **DEBT-016** (1 hour) - Move PROMPT-* files to /initiatives/ - **UNBLOCKS DEBT-021, 022, 017**
5. **DEBT-026** (1-2 hours) - Restore or replace autom8-asana skill - **UNBLOCKS ONBOARDING**
6. **DEBT-008** (30 min) - Mark PRD-PROCESS-PIPELINE superseded - **PREVENTS WASTED WORK**

**Why together**: These are blocking issues. DEBT-040 prevents data loss. DEBT-037 + DEBT-001 restore trust. DEBT-016 unblocks structural improvements. DEBT-026 unblocks onboarding. DEBT-008 prevents wasted implementation.

**Risk if deferred**: Data loss (DEBT-040), continued trust erosion (DEBT-001), structural confusion (DEBT-016), onboarding failures (DEBT-026), wasted implementation (DEBT-008).

---

### Sprint 2: High-Value Cleanup (11 items, 10-14 hours)
**Theme**: Fix stale documentation and create structural READMEs

**Batch 1: Status Fixes** (2 hours):
- DEBT-009, 010, 011, 012 - Batch status updates after DEBT-001 resolved
- DEBT-038 - Verify ADR renumbering complete, update references

**Batch 2: Supersession Notices** (1.5 hours):
- DEBT-005 - Mark TDD-0008 superseded, link to TDD-CACHE-* series
- DEBT-002 - Update or mark PRD-0002 superseded
- DEBT-006 - Mark PRD-0021 superseded
- DEBT-007 - Mark PRD-0022 rejected

**Batch 3: Structural READMEs** (3 hours):
- DEBT-017 - Create /docs/requirements/README.md
- DEBT-022 - Create /docs/initiatives/README.md
- DEBT-025 - Create /docs/runbooks/README.md

**Batch 4: Archival** (2 hours):
- DEBT-021 - Archive 4 completed PROMPT-0 initiatives
- DEBT-045 - Archive VALIDATION-PROCESS-PIPELINE
- DEBT-042 - Archive other completed initiatives

**Batch 5: Documentation Enhancements** (2-3 hours):
- DEBT-003 - Update PRD-0005 with healing system
- DEBT-046 - Verify cache docs link to REF-cache-*.md

**Why together**: All high-value fixes with dependencies resolved in Sprint 1. Batch status fixes for efficiency. Group READMEs for consistent structure. Consolidate archival work.

---

### Sprint 3: Medium Priority Refinements (10 items, 6-10 hours)
**Theme**: Fill documentation gaps and improve discoverability

**Batch 1: Directory READMEs** (2 hours):
- DEBT-018 - Verify /docs/design/README.md
- DEBT-023 - Create /docs/decisions/README.md
- DEBT-024 - Create /docs/testing/README.md

**Batch 2: Documentation Gaps** (4-6 hours):
- DEBT-027 - Create RUNBOOK-batch-operations.md, RUNBOOK-business-model-navigation.md
- DEBT-028 - Create validation reports for SaveSession, Cache Integration
- DEBT-032 - Create ADR-INDEX-BY-TOPIC.md

**Batch 3: Quality Improvements** (2 hours):
- DEBT-004 - Update PRD-0010 business model layer
- DEBT-015 - Clarify sprint decomposition doc status
- DEBT-035 - Audit "Draft" PRDs for incomplete sections
- DEBT-044 - Determine sprint doc status, archive if complete

**Why together**: Medium-impact improvements. No blocking dependencies. Can parallelize README creation. Batch documentation gap filling.

---

### Sprint 4: Continuous Improvement (10 items, 4-6 hours)
**Theme**: Polish and standardization

**Batch 1: Documentation Standards** (2 hours):
- DEBT-019 - Document naming convention in CONVENTIONS.md
- DEBT-020 - Update INDEX.md number allocation section
- DEBT-039 - Define frontmatter standard

**Batch 2: Backlog Cleanup** (2-3 hours):
- DEBT-013 - Resolve DOC-INVENTORY annotations
- DEBT-014 - Accept TDD-CUSTOM-FIELD-REMEDIATION naming
- DEBT-036 - Create follow-up items for deferred validation NFRs
- DEBT-043 - Archive DOC-INVENTORY CSV
- DEBT-047 - Document archival policy for PROMPT-0 files

**Batch 3: Low-Priority Enhancements** (1-2 hours):
- DEBT-029 - Create how-to guides (opportunistic)
- DEBT-030 - Create migration guides (if needed)
- DEBT-031 - Verify examples README
- DEBT-033 - Verify contributor guide location
- DEBT-034 - Verify changelog maintenance
- DEBT-041 - Assess large TDD splitting (only if problem)

**Why together**: Low-risk polish work. Can defer indefinitely if higher priorities arise. Good for "cleanup sprint" or distributed across maintenance windows.

---

## Risk Mitigation Recommendations

### Immediate Actions (Within 24 Hours)
1. **Commit uncommitted changes** (DEBT-040) - Non-negotiable. Prevents data loss.
2. **Add supersession notice to PRD-PROCESS-PIPELINE** (DEBT-008) - Quick fix (30 min), prevents wasted implementation.
3. **Restore autom8-asana skill or update references** (DEBT-026) - Unblocks onboarding.

### Process Improvements
1. **Establish doc-with-feature policy**: PRD/TDD updates mandatory in same commit as feature implementation. CI check rejects PRs with code changes but no doc updates.
2. **Define documentation lifecycle**: Draft → Active → Implemented → Archived. Document in /docs/CONVENTIONS.md. Enforce via frontmatter status field.
3. **Add automated link checking**: CI job detects broken internal references. Prevents DEBT-026 recurrence.
4. **Quarterly documentation cleanup**: Scheduled sprints for archival, status updates, stale doc remediation.
5. **Single source of truth for status**: Frontmatter status field is canonical. INDEX.md validates against frontmatter or auto-generates from it.

### Prevention Measures
1. **Supersession template**: When rejecting PRD/TDD, add prominent notice at top linking to rejection ADR. Include in ADR template.
2. **Archival policy**: PROMPT-0 initiatives archived within 1 week of VP APPROVED. Automate with CI reminder.
3. **Status sync CI check**: Fail build if INDEX.md status disagrees with document frontmatter status.
4. **Documentation review checklist**: Before merging feature PR, verify: (1) PRD/TDD updated, (2) Status updated, (3) Links valid, (4) ADRs referenced.
5. **Onboarding smoke test**: New developer onboarding checklist includes verifying all PROJECT_CONTEXT.md references are valid.

---

## Risk Score Methodology

**Probability Scale (1-5)**:
- 1: Rare - Triggers only in edge cases, low-frequency workflows
- 2: Unlikely - Requires unusual conditions, infrequent access
- 3: Possible - Moderate frequency, common workflows
- 4: Likely - High frequency, core workflows
- 5: Certain - Already triggering, every access affected

**Impact Scale (1-5)**:
- 1: Minimal - Cosmetic issue, no workflow disruption
- 2: Minor - Slight inconvenience, easy workaround
- 3: Moderate - Noticeable delay, confusion, but recoverable
- 4: Significant - Wastes hours, blocks workflows, requires escalation
- 5: Catastrophic - Data loss, trust erosion, implements wrong features, extends incidents

**Risk Score**: Probability × Impact (1-25)
- 20-25: Critical - Address immediately (blocking, high frequency, severe impact)
- 12-19: High - Address this sprint (high frequency or high impact)
- 6-11: Medium - Address next sprint (moderate frequency and impact)
- 1-5: Low - Backlog (low frequency, low impact, or both)

**Severity Adjustments**:
- Escalated 8 items based on cascading risks or root cause status
- De-escalated 1 item based on availability of alternatives
- Confirmed 38 items at original severity

---

## Assessment Notes

**Strengths of Current Debt Profile**:
- Most debt is structural/organizational, not technical accuracy
- Reference documentation (REF-*.md) appears solid - good foundation
- Audit was comprehensive - 464 files reviewed
- Precedent exists for archival (.archive/ structure in place)
- Some remediation already in progress (5 initiatives archived)

**Areas of Concern**:
- Trust crisis: Developers cannot rely on INDEX.md as source of truth (DEBT-001)
- Velocity mismatch: Code commits outpacing doc updates 5:1 (per audit report)
- Broken onboarding: Critical references deleted without replacement (DEBT-026)
- Structural chaos: 15 files mislocated for unknown duration (DEBT-016)
- Data loss risk: 40+ uncommitted changes vulnerable to loss (DEBT-040)

**Root Cause Patterns**:
1. **Rapid development without doc updates** (15 items) - Code Dec 15-24, docs Dec 9-12
2. **No lifecycle management** (4 items) - Completed artifacts not archived
3. **Structural reorganization mid-project** (3 items) - Numbered → named, files moved
4. **Broken references from cleanup** (1 item) - Files deleted, references orphaned
5. **Manual status tracking** (4 items) - INDEX.md, frontmatter, reality diverge

**Assumptions**:
- Risk scores assume current project velocity continues
- Probability based on workflow frequency observed in git log
- Impact based on developer time waste and trust erosion
- Effort estimates assume single developer, no major obstacles
- Sprint packages assume 20 hours/sprint capacity for documentation work

**Limitations**:
- Did not verify every link in 464 markdown files (spot-checked critical files)
- Did not analyze code docstrings (out of scope)
- Did not assess external documentation (if any)
- Risk scores are point-in-time; re-assessment recommended quarterly

---

## Handoff to Sprint Planner

**Ready for sprint packaging**: All 47 items scored, prioritized, and grouped.

**Recommended sprint allocation**:
- **Sprint 1** (Critical): 6 items, 6-8 hours - **Start immediately**
- **Sprint 2** (High): 11 items, 10-14 hours - **Next sprint**
- **Sprint 3** (Medium): 10 items, 6-10 hours - **Following sprint**
- **Sprint 4** (Low): 10 items, 4-6 hours - **Backlog/continuous improvement**

**Quick wins identified**:
- DEBT-040 (30 min) - Commit changes - **Prevents data loss**
- DEBT-008 (30 min) - Supersession notice - **Prevents wasted work**
- DEBT-016 (1 hour) - Move files - **Unblocks 3 items**
- DEBT-026 (1-2 hours) - Fix skill reference - **Unblocks onboarding**

**Critical path dependencies**:
1. DEBT-040 → All work (prevents data loss)
2. DEBT-037 → DEBT-001 → DEBT-009/010/011/012 (status standardization cascade)
3. DEBT-016 → DEBT-021/022/017 (structural reorganization cascade)

**Risk flags for sprint planner**:
- **DEBT-001, 040**: Cannot defer - trust/data loss issues
- **DEBT-016, 026**: Blocking onboarding and structure
- **DEBT-008**: High ROI - 30 min prevents days of wasted work
- **Cache documentation family** (DEBT-002, 005, 046): Consider dedicated sprint to consolidate

**External dependencies**: None identified. All remediation can proceed with current team.

---

## Conclusion

Documentation debt is **manageable but requires immediate action on 6 critical items**. Total remediation is 28-42 hours (approximately one month at 20% allocation or two sprints at 50% allocation).

**Critical insight**: Most severe debt stems from status tracking and structural organization, not technical inaccuracy. Reference documentation appears solid. Fixing DEBT-037 (status terminology) and DEBT-001 (INDEX.md metadata) will restore trust. Fixing DEBT-016 (file location) will unblock structural improvements.

**Immediate next steps**:
1. Commit uncommitted changes (DEBT-040) - **Today**
2. Define canonical status values (DEBT-037) - **Sprint 1, Day 1**
3. Fix INDEX.md status metadata (DEBT-001) - **Sprint 1, Day 1-2**
4. Move PROMPT-* files (DEBT-016) - **Sprint 1, Day 2**
5. Fix skill references (DEBT-026) - **Sprint 1, Day 2-3**
6. Mark superseded PRDs (DEBT-008) - **Sprint 1, Day 3**

After Sprint 1 completes (6-8 hours), documentation will have:
- Reliable status tracking (trust restored)
- Correct structural organization
- Working onboarding path
- Reduced risk of wasted implementation

Remaining work is refinement, gap-filling, and polish - important but not blocking.

---

**Risk Assessment Complete**
**Handoff to**: sprint-planner
**Status**: Ready for sprint packaging
**Next action**: Create sprint tickets from recommended packages
