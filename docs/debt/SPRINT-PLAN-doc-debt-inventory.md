---
plan_id: "SPRINT-doc-debt-inventory"
created_at: "2025-12-24"
session_id: "session-20251224-232654-1a1ac669"
total_items: 47
planned_sprints: 4
total_effort: "28-42 hours"
---

# Documentation Debt Sprint Plan

## Executive Summary

**Total Effort**: 28-42 hours (3.5-5 working days at 100% allocation)
**Sprint Count**: 4 sprints (1 critical, 2 high-value, 1 polish)
**Expected Outcomes**:
- Restore documentation trust (INDEX.md accuracy)
- Unblock onboarding (fix broken references)
- Establish structural integrity (correct file organization)
- Prevent wasted implementation effort (mark superseded features)
- Create sustainable documentation maintenance practices

**Critical Finding**: 6 items pose immediate risk of data loss, trust erosion, or wasted developer time. Sprint 1 addresses all critical items within 6-8 hours, restoring documentation reliability.

**Success Metric**: Developers can trust INDEX.md as source of truth for feature status and find accurate documentation within 2 minutes of searching.

---

## Sprint 1: Critical Path

**Goal**: Restore documentation trust, prevent data loss, unblock onboarding
**Duration**: 1 day (6-8 hours)
**Items**: 6 critical + 5 high-priority cascades = 11 total
**Priority**: P0 - Start immediately

### Overview

Sprint 1 addresses the trust crisis in documentation. Currently, developers cannot rely on INDEX.md for accurate feature status, new developers hit broken references during onboarding, and 40+ uncommitted documentation changes risk data loss. This sprint restores reliability and unblocks downstream work.

**Why these items together**: All are blocking issues with cascading impacts. DEBT-040 prevents data loss. DEBT-037 → DEBT-001 cascade restores trust. DEBT-016 unblocks structural improvements. DEBT-026 unblocks onboarding. DEBT-008 prevents wasted implementation.

**Dependencies resolved**: Completing this sprint enables 8 items in Sprint 2 (status fixes, archival, READMEs).

---

### Task 1.1: Commit Uncommitted Documentation Changes (DEBT-040)

**Priority**: P0 - DO THIS FIRST
**Effort**: 30 minutes
**Dependencies**: None
**Risk**: CRITICAL - Data loss imminent

**Context**: Git status shows 40+ modified documentation files in working tree. One `git reset --hard` or branch switch destroys hours of work. This is a non-negotiable risk mitigation step.

**Acceptance Criteria**:
- [ ] Review all modified files in git status (40+ files)
- [ ] Group changes into logical commits (status updates, content updates, structural changes)
- [ ] Commit with clear messages following project convention
- [ ] Verify git status clean or only intentional WIP remains
- [ ] Push to remote to ensure backup

**Steps**:
1. Run `git status > /tmp/uncommitted-changes.txt` to capture current state
2. Run `git diff docs/ .claude/` to review changes (redirect to file for analysis)
3. Group changes: (a) INDEX.md + status metadata, (b) content updates, (c) structural
4. Commit group (a) first: "docs(index): Update INDEX.md status metadata"
5. Commit remaining with descriptive messages
6. Verify: `git status` should show clean working tree
7. Push to remote: `git push origin main`

**Notes**: This task must complete before any other documentation work. If changes are extensive, consider creating feature branch for review.

---

### Task 1.2: Define Canonical Status Values (DEBT-037)

**Priority**: P0 - BLOCKS DEBT-001
**Effort**: 1 hour
**Dependencies**: DEBT-040 (commit first)
**Risk**: HIGH - Root cause of trust crisis

**Context**: Documentation uses 7+ different status values inconsistently: "Draft", "Active", "Ready", "Approved", "Implemented", "Complete", "Unknown", "NO-GO", "Invalidated". No documented lifecycle. This inconsistency is the root cause of DEBT-001 (INDEX.md status metadata stale).

**Acceptance Criteria**:
- [ ] Define canonical status lifecycle in /docs/CONVENTIONS.md
- [ ] Document status values: Draft, Active, Implemented, Superseded, Rejected, Archived
- [ ] Specify lifecycle transitions (Draft → Active → Implemented → Archived)
- [ ] Define when to use each status
- [ ] Establish frontmatter status field as single source of truth
- [ ] Document INDEX.md as derived/validated against frontmatter

**Steps**:
1. Create or update /docs/CONVENTIONS.md with "Documentation Status Lifecycle" section
2. Define canonical values:
   - **Draft**: Requirements gathering, design in progress
   - **Active**: Approved for implementation, work may be in progress
   - **Implemented**: Code complete, feature shipped
   - **Superseded**: Replaced by newer design/requirement (link to replacement)
   - **Rejected**: Decided not to implement (link to ADR)
   - **Archived**: Historical record, implementation complete and stable
3. Document transitions: Draft → Active (approval), Active → Implemented (code complete), Implemented → Archived (after stabilization), any → Superseded/Rejected (ADR decision)
4. Add section: "Frontmatter status field is canonical source of truth. INDEX.md must validate against or generate from frontmatter."
5. Commit: "docs(conventions): Define canonical documentation status lifecycle"

**Output Artifact**: /docs/CONVENTIONS.md with clear status lifecycle

---

### Task 1.3: Fix INDEX.md Status Metadata (DEBT-001)

**Priority**: P0 - TRUST RESTORATION
**Effort**: 2-3 hours
**Dependencies**: DEBT-037 (status values defined)
**Risk**: CRITICAL - Developers cannot trust documentation

**Context**: INDEX.md status contradicts reality for 13+ PRDs. Developers checking feature status receive incorrect information, leading to confusion about what's implemented, wasted effort, and trust erosion in all documentation.

**Acceptance Criteria**:
- [ ] Audit all 13+ identified status mismatches in INDEX.md
- [ ] Update each PRD/TDD frontmatter to canonical status (per DEBT-037)
- [ ] Update INDEX.md to match frontmatter status
- [ ] Cross-verify with git log (code implementation dates)
- [ ] Document verification methodology in commit message
- [ ] All status mismatches resolved

**Identified Mismatches** (from Risk Report):
1. PRD-0002 (Intelligent Caching) - INDEX: "Implemented", Reality: Active work through Dec 24
2. PRD-0013/0014 (Hydration/Resolution) - INDEX: "Implemented", Last updated Dec 16
3. PRD-0020 (Holder Factory) - INDEX: "Implemented", Implemented Dec 16
4. PRD-DETECTION - INDEX: "Draft", Implemented Dec 15
5. PRD-WORKSPACE-PROJECT-REGISTRY - INDEX: "Draft", VP APPROVED + implemented
6. PRD-CACHE-INTEGRATION - INDEX: "Implemented", Status field "Unknown"
7. PRD-TECH-DEBT-REMEDIATION - INDEX: "Unknown", Implemented Dec 15
8. PRD-PROCESS-PIPELINE - INDEX: "Active", Partially superseded (see DEBT-008)
9. PRD-0021 (Async Method Generator) - INDEX: "Active", Superseded by decorator
10. PRD-0022 (CRUD Base Class) - INDEX: "Active", Rejected per TDD-0026
11. Additional mismatches from DEBT-009, 010, 011, 012

**Steps**:
1. Create checklist of all 13+ items to audit
2. For each item:
   a. Check document frontmatter current status
   b. Check git log for implementation commits
   c. Check for ADRs documenting decisions
   d. Determine correct canonical status per DEBT-037
   e. Update document frontmatter if needed
   f. Update INDEX.md entry
3. Special cases:
   - PRD-0002: Mark "Active" (cache work ongoing) or "Superseded by PRD-CACHE-*"
   - PRD-PROCESS-PIPELINE: Mark "Partially Superseded" (see Task 1.6)
   - PRD-0021, 0022: Mark "Superseded"/"Rejected" (links in Task 1.7-1.8)
4. Verify: All INDEX.md statuses match document frontmatter
5. Commit: "docs(index): Fix status metadata for 13+ PRDs - restore accuracy"

**Output Artifact**: Accurate INDEX.md reflecting canonical status values

---

### Task 1.4: Move PROMPT-* Files to Correct Directory (DEBT-016)

**Priority**: P0 - UNBLOCKS DEBT-021, 022, 017
**Effort**: 1 hour
**Dependencies**: DEBT-040 (commit first to avoid conflicts)
**Risk**: CRITICAL - Broken taxonomy blocks navigation

**Context**: 15 PROMPT-0-* initiative files located in /docs/requirements/ but should be in /docs/initiatives/. Breaks documentation taxonomy. Developers searching /initiatives/ won't find files. Confuses purpose of /requirements/. Blocks archival (can't archive files in wrong directory) and README creation.

**Acceptance Criteria**:
- [ ] All 15 PROMPT-* files moved from /requirements/ to /initiatives/
- [ ] INDEX.md paths updated to reflect new location
- [ ] No broken references in other docs
- [ ] Git history preserved (use git mv)
- [ ] Directory structure verified

**Files to Move** (15 total):
1. PROMPT-0-CACHE-INTEGRATION.md
2. PROMPT-0-CACHE-OPTIMIZATION-PHASE2.md
3. PROMPT-0-CACHE-PERF-FETCH-PATH.md
4. PROMPT-0-CACHE-PERF-HYDRATION.md
5. PROMPT-0-CACHE-UTILIZATION.md
6. PROMPT-0-WATERMARK-CACHE.md
7. PROMPT-0-WORKSPACE-PROJECT-REGISTRY.md
8. (Plus 8 others identified in /docs/requirements/)

**Steps**:
1. List all PROMPT-* files: `find /docs/requirements -name "PROMPT-*.md"`
2. Verify /docs/initiatives/ directory exists: `ls -la /docs/initiatives/`
3. Move files preserving git history:
   ```bash
   cd /docs
   for file in requirements/PROMPT-*.md; do
     git mv "$file" "initiatives/$(basename "$file")"
   done
   ```
4. Update INDEX.md paths:
   - Find all PROMPT-* references in INDEX.md
   - Replace `requirements/PROMPT-` with `initiatives/PROMPT-`
   - Verify line numbers and links
5. Grep for any other references: `grep -r "requirements/PROMPT-" docs/ .claude/`
6. Update any found references
7. Commit: "docs(structure): Move 15 PROMPT-* initiative files to /initiatives/ directory"

**Output Artifact**: Correct directory structure, updated INDEX.md

**Unblocks**: DEBT-021 (archival), DEBT-022 (initiatives README), DEBT-017 (requirements README easier without mixed files)

---

### Task 1.5: Fix Broken autom8-asana Skill References (DEBT-026)

**Priority**: P0 - UNBLOCKS ONBOARDING
**Effort**: 1-2 hours
**Dependencies**: None
**Risk**: CRITICAL - New developers cannot onboard

**Context**: PROJECT_CONTEXT.md references `.claude/skills/autom8-asana/paradigm.md` but directory was deleted in cleanup. New developers hit broken link immediately during onboarding. Claude Code cannot resolve skill references. No discoverable paradigm documentation.

**Acceptance Criteria**:
- [ ] Broken reference in PROJECT_CONTEXT.md fixed
- [ ] Paradigm documentation accessible to new developers
- [ ] Claude Code skill lookups work
- [ ] All .claude/ references to autom8-asana skill updated
- [ ] Onboarding path validated (manual walkthrough)

**Options** (choose one):
1. **Option A**: Restore skill from git history
2. **Option B**: Update references to point to docs/architecture/DOC-ARCHITECTURE.md
3. **Option C**: Create new skill directory with link to DOC-ARCHITECTURE.md

**Recommended**: Option B (update references) - simpler, DOC-ARCHITECTURE.md already contains paradigm documentation.

**Steps** (Option B):
1. Verify docs/architecture/DOC-ARCHITECTURE.md contains paradigm explanation:
   - Read file, confirm sections on "Asana-as-database", entities, SaveSession
   - If incomplete, enhance with paradigm overview
2. Find all references to autom8-asana skill:
   ```bash
   grep -r "autom8-asana" .claude/ docs/
   grep -r "paradigm.md" .claude/ docs/
   ```
3. Update PROJECT_CONTEXT.md:
   - Replace skill reference with: "See docs/architecture/DOC-ARCHITECTURE.md for paradigm overview"
   - Add direct link: `[Asana-as-Database Paradigm](docs/architecture/DOC-ARCHITECTURE.md)`
4. Update any other .claude/ files with similar references
5. Test onboarding path:
   - Open PROJECT_CONTEXT.md
   - Follow link to DOC-ARCHITECTURE.md
   - Verify paradigm explanation clear
6. Commit: "docs(fix): Replace deleted autom8-asana skill references with DOC-ARCHITECTURE.md"

**Output Artifact**: Working onboarding path with accessible paradigm documentation

---

### Task 1.6: Mark PRD-PROCESS-PIPELINE Superseded (DEBT-008)

**Priority**: P0 - PREVENTS WASTED IMPLEMENTATION
**Effort**: 30 minutes
**Dependencies**: None
**Risk**: HIGH - Developer could waste 1-2 days implementing wrong feature

**Context**: PRD-PROCESS-PIPELINE describes ProcessProjectRegistry but ADR-0101 documents rejection of this approach. Actual implementation uses WorkspaceProjectRegistry. Developer assigned to implement process pipeline without reading ADR-0101 could waste days building wrong feature.

**Acceptance Criteria**:
- [ ] Prominent supersession notice added to PRD-PROCESS-PIPELINE
- [ ] FR-REG-* requirements marked as superseded
- [ ] Link to ADR-0101 (Process Pipeline Correction)
- [ ] Link to WorkspaceProjectRegistry as implemented alternative
- [ ] INDEX.md status updated to "Partially Superseded"

**Steps**:
1. Open /docs/requirements/PRD-PROCESS-PIPELINE.md
2. Add supersession notice at top (after frontmatter):
   ```markdown
   > **SUPERSESSION NOTICE**: Requirements FR-REG-001 through FR-REG-003 (ProcessProjectRegistry)
   > were superseded by ADR-0101 (Process Pipeline Correction). The implemented architecture uses
   > WorkspaceProjectRegistry instead. See PRD-WORKSPACE-PROJECT-REGISTRY for current design.
   >
   > Requirements FR-TYPE-*, FR-SECTION-*, FR-STATE-* remain valid and are implemented.
   ```
3. Update frontmatter status: "Partially Superseded"
4. Mark FR-REG-* requirements with "(Superseded - see ADR-0101)" in requirements table
5. Update INDEX.md:
   - Change status to "Partially Superseded"
   - Add note: "FR-REG-* superseded by ADR-0101, other requirements implemented"
6. Commit: "docs(prd): Mark ProcessProjectRegistry requirements as superseded - link to ADR-0101"

**Output Artifact**: Clear supersession notice preventing wasted implementation

---

### Task 1.7: Batch Status Updates (DEBT-009, 010, 011, 012)

**Priority**: P1 - Completes trust restoration
**Effort**: 1 hour
**Dependencies**: DEBT-001, DEBT-037 (status values defined, INDEX.md framework fixed)
**Risk**: MEDIUM - Individual mismatches compound trust issues

**Context**: 4 additional status mismatches not covered in DEBT-001. Fixing these completes the status accuracy restoration.

**Acceptance Criteria**:
- [ ] PRD-DETECTION status updated to "Implemented"
- [ ] PRD-WORKSPACE-PROJECT-REGISTRY status updated to "Implemented"
- [ ] PRD-CACHE-INTEGRATION frontmatter status clarified
- [ ] PRD-TECH-DEBT-REMEDIATION status updated to "Implemented"
- [ ] All updates committed with verification

**Items**:
1. **DEBT-009**: PRD-DETECTION - INDEX: "Draft", Reality: Implemented Dec 15
2. **DEBT-010**: PRD-WORKSPACE-PROJECT-REGISTRY - INDEX: "Draft", Reality: VP APPROVED + implemented
3. **DEBT-011**: PRD-CACHE-INTEGRATION - INDEX: "Implemented", Frontmatter: "Unknown"
4. **DEBT-012**: PRD-TECH-DEBT-REMEDIATION - INDEX: "Unknown", Reality: Implemented Dec 15

**Steps**:
1. For each item:
   a. Open PRD file
   b. Verify implementation in codebase (git log, src/ directory)
   c. Update frontmatter status to canonical value
   d. Update INDEX.md to match
   e. Note verification source in commit message
2. PRD-DETECTION:
   - Verify: src/autom8_asana/detection/ exists, ADR-0135/0142/0143
   - Update frontmatter: "Implemented"
   - Update INDEX.md: "Implemented"
3. PRD-WORKSPACE-PROJECT-REGISTRY:
   - Verify: VP-WORKSPACE-PROJECT-REGISTRY status "APPROVED", code in src/autom8_asana/models/registry.py
   - Update frontmatter: "Implemented"
   - Update INDEX.md: "Implemented"
4. PRD-CACHE-INTEGRATION:
   - Verify: commit 3b1c48f (Dec 22) "feat(cache): Activate dormant cache"
   - Update frontmatter: "Implemented"
   - INDEX.md already correct
5. PRD-TECH-DEBT-REMEDIATION:
   - Verify: commit 3483715 (Dec 15)
   - Update frontmatter: "Implemented"
   - Update INDEX.md: "Implemented"
6. Commit: "docs(status): Batch update 4 PRD statuses to Implemented - verification complete"

**Output Artifact**: 4 PRDs with accurate status metadata

---

### Task 1.8: Mark Additional Superseded PRDs (DEBT-006, 007)

**Priority**: P1 - Prevents confusion
**Effort**: 30 minutes
**Dependencies**: DEBT-001 (status framework fixed)
**Risk**: MEDIUM - Developers may implement rejected features

**Acceptance Criteria**:
- [ ] PRD-0021 marked as "Superseded" with link to decorator implementation
- [ ] PRD-0022 marked as "Rejected" with link to TDD-0026 NO-GO decision
- [ ] INDEX.md statuses updated
- [ ] Supersession notices prominent

**Items**:
1. **DEBT-006**: PRD-0021 Async Method Generator - superseded by @async_method decorator
2. **DEBT-007**: PRD-0022 CRUD Base Class - rejected per TDD-0026 NO-GO

**Steps**:
1. PRD-0021 (Async Method Generator):
   - Open /docs/requirements/PRD-0021-async-method-generator.md
   - Add supersession notice: "Superseded by @async_method decorator pattern (commit ee3ef8b, Dec 16). See PATTERNS-D for implementation."
   - Update frontmatter status: "Superseded"
   - Update INDEX.md: "Superseded"
2. PRD-0022 (CRUD Base Class):
   - Open /docs/requirements/PRD-0022-crud-base-class.md
   - Add rejection notice: "Rejected per TDD-0026 NO-GO decision (commit 8fb895c). Architecture uses entity-specific implementations instead."
   - Update frontmatter status: "Rejected"
   - Update INDEX.md: "Rejected"
3. Commit: "docs(status): Mark PRD-0021 superseded, PRD-0022 rejected - prevent implementation"

**Output Artifact**: Clear supersession/rejection notices on 2 PRDs

---

### Sprint 1 Completion Criteria

**Must have all**:
- [ ] Git working tree clean (no uncommitted documentation changes)
- [ ] Canonical status values documented in /docs/CONVENTIONS.md
- [ ] INDEX.md status metadata accurate for all 13+ identified mismatches
- [ ] All 15 PROMPT-* files in /docs/initiatives/ directory
- [ ] INDEX.md paths updated to reflect PROMPT-* file moves
- [ ] PROJECT_CONTEXT.md autom8-asana skill reference fixed
- [ ] PRD-PROCESS-PIPELINE supersession notice prominent
- [ ] All 4 status mismatches (DEBT-009/010/011/012) resolved
- [ ] PRD-0021 and PRD-0022 marked superseded/rejected
- [ ] No broken references in .claude/ directory
- [ ] Onboarding path validated (manual test)

**Success Indicator**: Developer can:
1. Open INDEX.md and trust status column
2. Follow onboarding path from PROJECT_CONTEXT.md without hitting broken links
3. Navigate to /docs/initiatives/ and find all initiative files
4. Read supersession notices before implementing rejected features

**Unblocks for Sprint 2**:
- Archival (DEBT-021) - files now in correct directory
- README creation (DEBT-017, 022) - structure stable
- Additional status fixes - framework established

---

## Sprint 2: High-Value Cleanup

**Goal**: Update stale documentation, create structural READMEs, archive completed work
**Duration**: 1 day (10-14 hours)
**Items**: 11 high-priority items
**Priority**: P1 - Schedule immediately after Sprint 1

### Overview

Sprint 2 builds on Sprint 1's structural fixes to update stale cache documentation, create directory READMEs for discoverability, and archive completed initiatives. This sprint addresses the cache documentation family issue (DEBT-002, 005, 046) and establishes navigation aids for new developers.

**Dependencies from Sprint 1**: DEBT-016 (file moves) enables archival tasks. DEBT-001 (status framework) enables batch status updates.

---

### Task 2.1: Update Cache Documentation Family (DEBT-002, 005, 046)

**Priority**: P1 - Cache is critical system
**Effort**: 3-4 hours
**Dependencies**: Sprint 1 complete (status framework established)

**Context**: TDD-0008 describes original cache vision from Dec 9. Architecture evolved to multi-tier, staleness detection, progressive TTL by Dec 24. PRD-0002 also stale. 9 PRDs + 9 TDDs (189K + 320K) with conceptual overlap. Developers implementing cache features will build wrong architecture.

**Acceptance Criteria**:
- [ ] TDD-0008 marked "Superseded" with links to TDD-CACHE-* series
- [ ] PRD-0002 updated or marked "Superseded" with links to PRD-CACHE-* series
- [ ] All 9 cache PRDs verified to link to REF-cache-*.md instead of duplicating
- [ ] All 9 cache TDDs verified to link to REF-cache-*.md
- [ ] Cache architecture navigation clear (developer can find current design in <2 min)

**Steps**:
1. **TDD-0008 Supersession**:
   - Open /docs/design/TDD-0008-intelligent-caching.md
   - Add notice: "This TDD describes original cache vision (Dec 9). Architecture evolved significantly. See current architecture: TDD-CACHE-INTEGRATION (activation), TDD-CACHE-LIGHTWEIGHT-STALENESS (detection), TDD-CACHE-OPTIMIZATION-P2/P3 (performance), and REF-cache-architecture.md (overview)."
   - Update frontmatter status: "Superseded"
   - Update INDEX.md: "Superseded by TDD-CACHE-* series"

2. **PRD-0002 Update**:
   - Open /docs/requirements/PRD-0002-intelligent-caching.md
   - Determine: Update to current or mark superseded?
   - Recommended: Mark superseded with links to PRD-CACHE-* series (9 granular PRDs)
   - Add notice: "Original requirements decomposed into PRD-CACHE-* series (Dec 22-24). See PRD-CACHE-INTEGRATION, PRD-CACHE-LIGHTWEIGHT-STALENESS, PRD-CACHE-OPTIMIZATION-P2/P3, PRD-WATERMARK-CACHE for current requirements."
   - Update INDEX.md: "Superseded by PRD-CACHE-* series"

3. **Verify Cache Concept Cross-References**:
   - List all cache docs: `ls docs/requirements/PRD-CACHE-* docs/design/TDD-CACHE-*`
   - For each cache PRD/TDD:
     a. Grep for duplicated concepts: "staleness detection", "TTL strategy", "provider protocol"
     b. If found: Replace with link to REF-cache-architecture.md, REF-cache-staleness-detection.md, etc.
     c. If REF doesn't exist: Note as gap (create in Sprint 3)
   - Create checklist of 18 cache docs (9 PRDs + 9 TDDs)
   - Mark each verified or updated

4. **Create Cache Navigation Guide**:
   - Add section to /docs/reference/README.md: "Cache System Documentation"
   - List hierarchy:
     - Overview: REF-cache-architecture.md
     - Requirements: PRD-CACHE-* series
     - Design: TDD-CACHE-* series
     - Superseded: PRD-0002, TDD-0008 (historical context)
   - Link from INDEX.md cache section

5. Commit: "docs(cache): Mark PRD-0002/TDD-0008 superseded, verify cache concept cross-references"

**Output Artifacts**:
- Clear cache documentation hierarchy
- No duplicated concepts (all link to REF-cache-*.md)
- Navigation guide for cache system

---

### Task 2.2: Update PRD-0005 with Healing System (DEBT-003)

**Priority**: P1 - SaveSession is core feature
**Effort**: 1-2 hours
**Dependencies**: None

**Context**: PRD-0005 last updated Dec 10, but SaveSession healing system added Dec 15+. Missing self-healing capabilities, HealingResult consolidation, error recovery patterns.

**Acceptance Criteria**:
- [ ] Healing system section added to PRD-0005
- [ ] References to ADR-0139, ADR-0144 (healing system decisions)
- [ ] Acceptance criteria include healing behaviors
- [ ] Status updated to "Implemented" (was incomplete before)

**Steps**:
1. Read ADR-0139, ADR-0144 to understand healing system design
2. Open /docs/requirements/PRD-0005-save-orchestration.md
3. Add section: "FR-HEALING: Self-Healing and Error Recovery"
   - FR-HEALING-001: SaveSession detects conflicts and offers resolution strategies
   - FR-HEALING-002: HealingResult consolidates error information
   - FR-HEALING-003: Automatic retries for transient failures
   - FR-HEALING-004: Manual healing hooks for custom recovery
4. Update existing sections to reference healing where relevant
5. Add "See Also" links: ADR-0139 (Healing Strategy), ADR-0144 (HealingResult Model)
6. Update frontmatter: "Implemented" (healing system shipped Dec 15)
7. Update INDEX.md if needed
8. Commit: "docs(prd): Add SaveSession healing system requirements - complete PRD-0005"

**Output Artifact**: Complete PRD-0005 reflecting all SaveSession capabilities

---

### Task 2.3: Verify ADR Renumbering Complete (DEBT-038)

**Priority**: P1 - ADRs are critical decision records
**Effort**: 1 hour
**Dependencies**: None

**Context**: INDEX.md notes "ADR-0115 through ADR-0120 duplicates renumbered to ADR-0135 through ADR-0144" but unclear if all references updated. Broken ADR references lead to wrong implementation decisions.

**Acceptance Criteria**:
- [ ] All old ADR numbers (ADR-0115 through ADR-0120) removed from /docs/decisions/
- [ ] All references to old numbers updated in PRDs/TDDs
- [ ] Git history shows rename/renumber commits
- [ ] No broken ADR references in documentation

**Steps**:
1. List ADR files: `ls docs/decisions/ADR-01*.md` - verify no ADR-0115 through ADR-0120
2. Grep for old references:
   ```bash
   grep -r "ADR-0115\|ADR-0116\|ADR-0117\|ADR-0118\|ADR-0119\|ADR-0120" docs/
   ```
3. For each found reference:
   - Identify correct new ADR number (use INDEX.md mapping or git log)
   - Update reference in document
   - Note in checklist
4. Verify git history: `git log --grep="ADR-011[5-9]\|ADR-0120"` to see renumber commits
5. If renumbering incomplete:
   - Document which ADRs need renumbering
   - Perform renumbers: `git mv docs/decisions/ADR-0115-*.md docs/decisions/ADR-0135-*.md`
   - Update all references
6. Commit: "docs(adr): Complete ADR duplicate renumbering - update all references"

**Output Artifact**: No references to old ADR-0115 through ADR-0120 numbers

---

### Task 2.4: Archive Completed Initiatives (DEBT-021, 042)

**Priority**: P1 - Clears active directories
**Effort**: 1 hour
**Dependencies**: Sprint 1 Task 1.4 (PROMPT-* files in correct directory)

**Context**: 4 completed PROMPT-0 initiatives still in /docs/initiatives/ directory. Clutters active directory, confuses what's in-flight vs. completed. Precedent exists: .archive/initiatives/2025-Q4/ contains 5 archived initiatives.

**Acceptance Criteria**:
- [ ] 4 completed initiatives moved to .archive/initiatives/2025-Q4/
- [ ] INDEX.md updated to "Archived Initiatives" section
- [ ] Archive README.md updated with new entries
- [ ] No broken references to moved files

**Initiatives to Archive**:
1. PROMPT-0-CACHE-OPTIMIZATION-PHASE2.md (complete per commit eff1d0d)
2. PROMPT-0-CACHE-PERF-FETCH-PATH.md (P1 complete)
3. PROMPT-0-WATERMARK-CACHE.md (validated PASS)
4. PROMPT-0-WORKSPACE-PROJECT-REGISTRY.md (VP APPROVED)

**Steps**:
1. Verify completion status for each initiative:
   - Check validation reports
   - Check git log for completion commits
   - Confirm no open work
2. Move to archive preserving git history:
   ```bash
   git mv docs/initiatives/PROMPT-0-CACHE-OPTIMIZATION-PHASE2.md \
          docs/.archive/initiatives/2025-Q4/
   ```
   Repeat for all 4 initiatives
3. Update /docs/.archive/initiatives/2025-Q4/README.md:
   - Add entries for 4 new archives
   - Include completion date, validation status, outcome
4. Update INDEX.md:
   - Move 4 initiatives from "Active Initiatives" to "Archived Initiatives (2025-Q4)"
   - Update paths to .archive/initiatives/2025-Q4/
5. Grep for references to moved files:
   ```bash
   grep -r "PROMPT-0-CACHE-OPTIMIZATION-PHASE2\|PROMPT-0-CACHE-PERF-FETCH-PATH\|PROMPT-0-WATERMARK-CACHE\|PROMPT-0-WORKSPACE-PROJECT-REGISTRY" docs/ .claude/
   ```
6. Update any found references with archive paths
7. Commit: "docs(archive): Move 4 completed initiatives to 2025-Q4 archive"

**Output Artifact**: Clean /docs/initiatives/ with only active work

---

### Task 2.5: Archive Invalidated Validation Report (DEBT-045)

**Priority**: P1 - Clears testing directory
**Effort**: 30 minutes
**Dependencies**: None

**Context**: VALIDATION-PROCESS-PIPELINE shows status "Invalidated" but still in active /docs/testing/ directory. Report invalidated because ProcessProjectRegistry never implemented (superseded by WorkspaceProjectRegistry per ADR-0101).

**Acceptance Criteria**:
- [ ] VALIDATION-PROCESS-PIPELINE moved to .archive/validation/
- [ ] Archive includes invalidation note
- [ ] INDEX.md updated
- [ ] No broken references

**Steps**:
1. Create archive directory if needed: `mkdir -p docs/.archive/validation/`
2. Move file: `git mv docs/testing/VALIDATION-PROCESS-PIPELINE.md docs/.archive/validation/`
3. Add invalidation note to file:
   - Open archived file
   - Add at top: "INVALIDATION NOTICE: This validation report is invalidated because ProcessProjectRegistry (FR-REG-* requirements) was never implemented. ADR-0101 (Process Pipeline Correction) documents decision to use WorkspaceProjectRegistry instead. See VP-WORKSPACE-PROJECT-REGISTRY for actual validation."
4. Update INDEX.md:
   - Remove from "Validation Reports" section
   - Add to "Archived Validation Reports" section (create if needed)
5. Commit: "docs(archive): Invalidate VALIDATION-PROCESS-PIPELINE - ProcessProjectRegistry never implemented"

**Output Artifact**: Clean testing directory with only valid validation reports

---

### Task 2.6: Create Directory READMEs (DEBT-017, 022, 025)

**Priority**: P1 - Improves discoverability
**Effort**: 3 hours (1 hour per README)
**Dependencies**: Sprint 1 Task 1.4 (file structure stable)

**Context**: New developers navigating /docs/requirements/, /docs/initiatives/, /docs/runbooks/ have no context. No explanation of directory purpose, file naming, lifecycle. Contrast with excellent /docs/reference/README.md.

**Acceptance Criteria**:
- [ ] /docs/requirements/README.md created
- [ ] /docs/initiatives/README.md created
- [ ] /docs/runbooks/README.md created
- [ ] Each README follows consistent structure
- [ ] Links from INDEX.md or root README.md

**README Structure** (consistent across all 3):
1. Purpose (what this directory contains)
2. File Naming Convention
3. Lifecycle/Status Values
4. Relationship to Other Docs
5. How to Create New Files
6. Archival Policy

**Steps**:

**DEBT-017: /docs/requirements/README.md**:
1. Create file with sections:
   - Purpose: "Product Requirements Documents (PRDs) define what to build and why."
   - Naming: "PRD-XXXX-feature-name.md (numbered legacy) or PRD-FEATURE-NAME.md (current)"
   - Status lifecycle: Link to /docs/CONVENTIONS.md
   - PRD-TDD pairing: "Each PRD paired with TDD in /docs/design/. See INDEX.md for mappings."
   - How to create: "Copy docs/templates/PRD-TEMPLATE.md (if exists, else describe frontmatter)"
   - Archival: "Superseded PRDs marked with notice, link to replacement. Rejected PRDs link to ADR."
2. Add examples: Link to exemplar PRDs (PRD-DETECTION, PRD-CACHE-INTEGRATION)
3. Commit: "docs(readme): Add /docs/requirements/README.md - explain PRD purpose and conventions"

**DEBT-022: /docs/initiatives/README.md**:
1. Create file with sections:
   - Purpose: "Initiative orchestration files for multi-document workflows."
   - File types: "PROMPT-0 (Session 0 - implementation sprint) vs PROMPT-MINUS-1 (meta-initiative planning)"
   - Naming: "PROMPT-0-INITIATIVE-NAME.md or PROMPT-MINUS-1-INITIATIVE-NAME.md"
   - Lifecycle: "Created → Active → Validation → Archived"
   - Relationship: "Each PROMPT-0 typically references 1+ PRD/TDD. Orchestrator uses these for context."
   - How to create: "See .claude/skills/initiative-scoping/session-0-protocol.md"
   - Archival: "Archive to .archive/initiatives/YYYY-QN/ after validation PASS/APPROVED."
2. Add current initiatives list (dynamic - or link to INDEX.md)
3. Commit: "docs(readme): Add /docs/initiatives/README.md - explain PROMPT-0 vs PROMPT-MINUS-1"

**DEBT-025: /docs/runbooks/README.md**:
1. Create file with sections:
   - Purpose: "Operational troubleshooting guides for complex features."
   - When to create: "Create runbook when feature has: (a) complex failure modes, (b) ops escalation history, (c) non-obvious debugging steps."
   - Naming: "RUNBOOK-feature-name.md"
   - Structure: "Problem → Symptoms → Diagnosis → Resolution → Prevention"
   - Severity classification: "P0 (outage), P1 (degraded), P2 (advisory)"
   - How to create: "Copy docs/templates/RUNBOOK-TEMPLATE.md (if exists, else provide template)"
2. List existing runbooks: RUNBOOK-cache.md, RUNBOOK-savesession.md, RUNBOOK-detection.md
3. Note gaps: "Needed: batch operations, business model navigation, automation troubleshooting"
4. Commit: "docs(readme): Add /docs/runbooks/README.md - explain operational runbook purpose"

**Output Artifacts**: 3 directory READMEs improving navigation

---

### Sprint 2 Completion Criteria

**Must have all**:
- [ ] TDD-0008 and PRD-0002 marked superseded with links to current cache docs
- [ ] All 18 cache docs verified to link to REF-cache-*.md (no concept duplication)
- [ ] PRD-0005 updated with healing system requirements
- [ ] No references to old ADR-0115 through ADR-0120 numbers
- [ ] 4 completed initiatives archived to .archive/initiatives/2025-Q4/
- [ ] VALIDATION-PROCESS-PIPELINE archived with invalidation notice
- [ ] /docs/requirements/README.md created
- [ ] /docs/initiatives/README.md created
- [ ] /docs/runbooks/README.md created
- [ ] INDEX.md updated to reflect all archival and status changes

**Success Indicator**: New developer can:
1. Navigate to any /docs directory and understand purpose from README
2. Find current cache architecture in <2 minutes
3. Distinguish active vs. archived initiatives
4. Follow ADR references without hitting broken links

---

## Sprint 3: Content Quality & Gaps

**Goal**: Fill documentation gaps, improve discoverability, update stale content
**Duration**: 1-2 days (6-10 hours)
**Items**: 10 medium-priority items
**Priority**: P2 - Schedule after Sprint 2

### Overview

Sprint 3 addresses medium-priority documentation gaps and quality issues. Create remaining directory READMEs, operational runbooks, validation reports, and ADR index. Update stale business model and sprint decomposition docs.

**These items enhance documentation but are not blocking** - system is usable after Sprint 2.

---

### Task 3.1: Create Remaining Directory READMEs (DEBT-018, 023, 024)

**Priority**: P2
**Effort**: 2 hours
**Dependencies**: Sprint 2 (README pattern established)

**Items**:
- DEBT-018: Verify /docs/design/README.md completeness
- DEBT-023: Create /docs/decisions/README.md
- DEBT-024: Create /docs/testing/README.md

**Acceptance Criteria**:
- [ ] All 3 directory READMEs exist and follow consistent structure
- [ ] Links from INDEX.md or navigation docs

**Steps**: (Follow Task 2.6 pattern for each README)

---

### Task 3.2: Create Priority Operational Runbooks (DEBT-027)

**Priority**: P2 - High operational value
**Effort**: 4-6 hours (2-3 hours per runbook)
**Dependencies**: Sprint 2 Task 2.6 (runbooks README created)

**Context**: Complex features lack operational troubleshooting guides. Create 2 highest-impact runbooks.

**Acceptance Criteria**:
- [ ] RUNBOOK-batch-operations.md created
- [ ] RUNBOOK-business-model-navigation.md created
- [ ] Each follows standard structure (Problem/Symptoms/Diagnosis/Resolution/Prevention)

**Priority Runbooks**:
1. **RUNBOOK-batch-operations.md**: Troubleshooting batch entity operations, rate limiting, partial failures
2. **RUNBOOK-business-model-navigation.md**: Debugging business model traversal, contact mapping, stub vs. full models

**Steps**:
1. Interview subject matter expert or review code for failure modes
2. Document common issues, symptoms, debugging steps
3. Add resolution procedures
4. Include prevention/mitigation strategies
5. Link from relevant PRDs/TDDs
6. Commit: "docs(runbook): Add operational troubleshooting for batch operations and business model"

---

### Task 3.3: Create Validation Reports for Key Features (DEBT-028)

**Priority**: P2
**Effort**: 2-4 hours (1-2 hours per VP)
**Dependencies**: None

**Context**: SaveSession and Cache Integration lack formal validation reports. Create retrospective VPs documenting validation.

**Acceptance Criteria**:
- [ ] VP-SAVESESSION.md created (or equivalent)
- [ ] VP-CACHE-INTEGRATION.md created
- [ ] Status: "APPROVED" (post-implementation validation)
- [ ] Links from INDEX.md

**Steps**:
1. Review acceptance criteria from PRD-0005 (SaveSession), PRD-CACHE-INTEGRATION
2. Document validation approach (unit tests, integration tests, manual testing)
3. List test coverage (which acceptance criteria validated, how)
4. Note any deferred items or known limitations
5. Status: "APPROVED" (features are shipped and working)
6. Commit: "docs(validation): Add retrospective validation reports for SaveSession and Cache Integration"

---

### Task 3.4: Create ADR Index by Topic (DEBT-032)

**Priority**: P2 - Improves decision discoverability
**Effort**: 1-2 hours
**Dependencies**: None

**Context**: 135 ADRs hard to discover. Create topic-based index for navigation.

**Acceptance Criteria**:
- [ ] /docs/decisions/ADR-INDEX-BY-TOPIC.md created
- [ ] ADRs grouped by: Architecture, Patterns, Rejection Decisions, Performance, Security, etc.
- [ ] Links from decisions/README.md

**Steps**:
1. Review all ADRs in INDEX.md (or scan /docs/decisions/)
2. Group by topic categories
3. Create index file with topic sections
4. List relevant ADRs under each topic with brief description
5. Commit: "docs(adr): Create ADR index by topic - improve decision discoverability"

---

### Task 3.5: Update Stale PRDs (DEBT-004, 015)

**Priority**: P2
**Effort**: 1 hour
**Dependencies**: None

**Items**:
- DEBT-004: Update PRD-0010 Business Model Layer to reflect foundation hardening
- DEBT-015: Clarify sprint decomposition doc status (archive or update)

**Steps**: (Standard PRD update - review code, update requirements, verify status)

---

### Sprint 3 Completion Criteria

**Must have all**:
- [ ] 3 directory READMEs created (design, decisions, testing)
- [ ] 2 operational runbooks created (batch ops, business model)
- [ ] 2 validation reports created (SaveSession, Cache Integration)
- [ ] ADR index by topic created
- [ ] Stale PRDs updated (business model, sprint decomposition)

**Success Indicator**: Developer can find operational troubleshooting, validation evidence, and ADRs by topic within 2 minutes.

---

## Sprint 4: Polish & Continuous Improvement

**Goal**: Standardize conventions, resolve backlog items, establish maintenance practices
**Duration**: Backlog (4-6 hours)
**Items**: 10 low-priority items
**Priority**: P3 - Nice-to-have, can defer indefinitely

### Overview

Sprint 4 addresses low-priority polish items. These enhance documentation quality but have minimal impact on developer workflows. Distribute across maintenance windows or dedicate "cleanup sprint" when higher priorities clear.

### Batches

**Batch 4.1: Documentation Standards** (2 hours):
- DEBT-019: Document naming convention in CONVENTIONS.md
- DEBT-020: Update INDEX.md number allocation section
- DEBT-039: Define frontmatter standard in CONVENTIONS.md

**Batch 4.2: Backlog Cleanup** (2-3 hours):
- DEBT-013: Resolve DOC-INVENTORY annotations
- DEBT-014: Accept TDD-CUSTOM-FIELD-REMEDIATION naming, clarify in INDEX.md
- DEBT-036: Create follow-up items for deferred validation NFRs
- DEBT-043: Archive DOC-INVENTORY-2025-12-24.csv to .archive/historical/
- DEBT-044: Determine sprint doc status, archive if complete
- DEBT-047: Document archival policy for PROMPT-0 files in CONVENTIONS.md

**Batch 4.3: Low-Priority Enhancements** (1-2 hours):
- DEBT-029: Create how-to guides (opportunistic)
- DEBT-030: Create migration guides (if migration need arises)
- DEBT-031: Verify examples/README.md completeness
- DEBT-033: Verify contributor guide location (move to /CONTRIBUTING.md)
- DEBT-034: Verify CHANGELOG.md currency
- DEBT-041: Assess large TDD splitting (only if navigation problem)

### Sprint 4 Completion Criteria

**Optional - complete as capacity allows**:
- [ ] Naming conventions documented
- [ ] Frontmatter standard defined
- [ ] DOC-INVENTORY annotations resolved
- [ ] Deferred validation NFRs tracked
- [ ] Stale artifacts archived
- [ ] How-to guides created (opportunistic)

---

## Dependencies Graph

```
DEBT-040 (commit changes)
    ↓
ALL WORK (stable foundation)

DEBT-037 (canonical status)
    ↓
DEBT-001 (INDEX.md fix)
    ↓
DEBT-009/010/011/012 (batch status updates)
    ↓
DEBT-013 (resolve DOC-INVENTORY)

DEBT-016 (move PROMPT-* files)
    ↓
DEBT-021 (archive initiatives)
    ↓
DEBT-042 (archive other completed)

DEBT-016 (file structure stable)
    ↓
DEBT-017, 022, 025 (directory READMEs)
    ↓
DEBT-018, 023, 024 (additional READMEs)

DEBT-001 (status framework)
    ↓
DEBT-006, 007, 008 (supersession notices)
    ↓
DEBT-045 (archive invalidated)

DEBT-005, 002 (cache doc fixes)
    ↓
DEBT-046 (verify cache cross-references)

Independent:
- DEBT-026 (skill references) - no dependencies
- DEBT-003 (healing system) - no dependencies
- DEBT-027 (runbooks) - depends on DEBT-025 (runbooks README)
- DEBT-028 (validation reports) - no dependencies
- DEBT-032 (ADR index) - no dependencies
- DEBT-038 (ADR renumbering) - no dependencies
- Sprint 4 items - mostly independent
```

---

## Risk Mitigation

### How Sprints Address Identified Cascades

**Cascade 1: Documentation Trust Crisis** (DEBT-037 → DEBT-001 → DEBT-009/010/011/012 → DEBT-013)
- **Resolution**: Sprint 1 Tasks 1.2, 1.3, 1.7 address full cascade
- **Impact**: Restores developer trust in INDEX.md, eliminates 10-15 min waste per feature lookup
- **Timeline**: Resolved by end of Sprint 1 (Day 1)

**Cascade 2: Structural Reorganization Blocked** (DEBT-016 → DEBT-021 → DEBT-022 → DEBT-017)
- **Resolution**: Sprint 1 Task 1.4 unblocks, Sprint 2 Tasks 2.4, 2.6 complete cascade
- **Impact**: Stable directory structure enables navigation and archival
- **Timeline**: Unblocked end of Sprint 1, completed end of Sprint 2

**Cascade 3: Cache Documentation Family Issue** (Cache evolution → DEBT-005 → DEBT-002 → DEBT-046)
- **Resolution**: Sprint 2 Task 2.1 addresses full cascade
- **Impact**: Reduces cache learning burden from 4-6 hours to <1 hour
- **Timeline**: Resolved end of Sprint 2

**Cascade 4: Superseded Features Active** (DEBT-008 → DEBT-045 → DEBT-006 → DEBT-007)
- **Resolution**: Sprint 1 Tasks 1.6, 1.8; Sprint 2 Task 2.5
- **Impact**: Prevents 1-2 days wasted implementation per incident
- **Timeline**: Critical items (DEBT-008) resolved Sprint 1, full cascade Sprint 2

**Cascade 5: Onboarding Workflow Broken** (DEBT-026 → PROJECT_CONTEXT.md → Paradigm missing)
- **Resolution**: Sprint 1 Task 1.5
- **Impact**: Restores onboarding, reduces onboarding time +2-4 hours per developer
- **Timeline**: Resolved end of Sprint 1 (Day 1)

### Process Improvements Implemented

**Prevention Measures** (established during Sprint 1-2):
1. **Canonical Status Lifecycle** (Task 1.2): Prevents future status divergence
2. **Archival Policy** (Task 2.4): Prevents completed work cluttering active directories
3. **Directory READMEs** (Task 2.6): Prevents navigation confusion
4. **Supersession Template** (Task 1.6): Prevents re-implementation of rejected features

**Recommended CI/Automation** (for post-sprint implementation):
1. Status sync check: Fail build if INDEX.md disagrees with frontmatter
2. Link validation: Detect broken internal references
3. Archival reminders: CI comment when PROMPT-0 initiative validated PASS
4. Doc-with-feature policy: Reject PRs with code changes but no doc updates

---

## Success Metrics

### Sprint 1 Success Metrics

**Quantitative**:
- 0 uncommitted documentation changes (down from 40+)
- 100% INDEX.md status accuracy (up from ~75%)
- 0 broken references in .claude/ directory (down from 1+)
- 15 files in correct directory location (up from 0)

**Qualitative**:
- Developer can trust INDEX.md as source of truth
- New developer completes onboarding without broken links
- Developer can find initiative files in /docs/initiatives/
- Developer reads supersession notice before implementing rejected feature

### Sprint 2 Success Metrics

**Quantitative**:
- 18 cache docs link to REF-cache-*.md (eliminates 189K + 320K duplication)
- 4 completed initiatives archived (down from 0)
- 3 directory READMEs created
- Cache architecture findable in <2 minutes (down from ~30 minutes)

**Qualitative**:
- Developer navigates to directory and understands purpose from README
- Developer finds current cache architecture quickly
- Developer distinguishes active vs. archived work

### Sprint 3 Success Metrics

**Quantitative**:
- 2 operational runbooks created
- 2 validation reports created (retrospective)
- 135 ADRs indexed by topic
- 3 additional directory READMEs created

**Qualitative**:
- Developer finds operational troubleshooting for batch ops issue
- Developer locates validation evidence for shipped feature
- Developer discovers relevant ADRs by topic search

### Overall Success (Post-Sprint 1-3)

**Documentation Trust Score**: Developers can find accurate information within 2 minutes
- **Before**: INDEX.md unreliable, broken references, files mislocated, 4-6 hour cache learning
- **After**: INDEX.md accurate, no broken links, stable structure, <1 hour cache learning

**Broken Reference Count**: 0 (target)
- **Before**: 1+ broken skill reference, unknown link health
- **After**: All references validated, CI checks prevent regression

**Status Accuracy**: 100% (INDEX.md matches reality)
- **Before**: 13+ mismatches (~75% accuracy)
- **After**: Canonical status values, frontmatter source of truth, INDEX.md derived

---

## Effort Summary

| Sprint | Items | Effort Range | Priority | Outcome |
|--------|-------|-------------|----------|---------|
| Sprint 1 | 11 (6 critical + 5 cascades) | 6-8 hours | P0 | Trust restored, structure stable, onboarding working |
| Sprint 2 | 11 | 10-14 hours | P1 | Stale docs updated, READMEs created, archival complete |
| Sprint 3 | 10 | 6-10 hours | P2 | Gaps filled, discoverability improved, validation documented |
| Sprint 4 | 10 | 4-6 hours | P3 | Standards defined, backlog cleared, polish complete |
| **Total** | **42 (47 items, 5 batched)** | **28-42 hours** | - | **Documentation debt remediated** |

**Allocation Strategies**:

1. **Aggressive** (2 weeks, 50% documentation allocation):
   - Week 1: Sprint 1 (Day 1-2, 8h) + Sprint 2 start (Day 3-5, 12h)
   - Week 2: Sprint 2 finish (Day 1, 2h) + Sprint 3 (Day 2-4, 10h) + Sprint 4 start (Day 5, 2h)
   - Result: All critical/high items complete, most medium items complete

2. **Moderate** (1 month, 20% documentation allocation):
   - Week 1: Sprint 1 (8h)
   - Week 2-3: Sprint 2 (14h)
   - Week 4: Sprint 3 start (8h)
   - Month 2: Sprint 3 finish + Sprint 4
   - Result: Steady progress, sustainable pace

3. **Conservative** (Continuous, 10% documentation allocation):
   - Month 1: Sprint 1 (8h over 2 weeks)
   - Month 2: Sprint 2 (14h over 3 weeks)
   - Month 3: Sprint 3 (10h over 2 weeks)
   - Month 4+: Sprint 4 (backlog, as capacity allows)
   - Result: Minimal disruption to feature work, longer timeline

**Recommended**: Aggressive for Sprint 1 (8h dedicated, resolves critical items), then Moderate for Sprint 2-3.

---

## Execution Notes

### Who Should Execute

**Sprint 1** (Critical Path):
- **Best**: Senior engineer familiar with codebase + documentation system
- **Rationale**: Requires judgment on status values, git history review, structural decisions
- **Can delegate**: Task 1.1 (commit), Task 1.4 (file moves) to any engineer
- **Should not delegate**: Task 1.2 (status lifecycle), Task 1.3 (INDEX.md audit) - require domain knowledge

**Sprint 2** (High-Value Cleanup):
- **Best**: Technical writer or senior engineer
- **Rationale**: README creation benefits from writing skill, cache docs need technical understanding
- **Can delegate**: Task 2.4 (archival), Task 2.5 (archive validation) to junior engineer
- **Automatable**: Task 2.3 (ADR renumbering verification) - grep scripts

**Sprint 3** (Content Quality):
- **Best**: Mix of technical writer (runbooks, VPs) and engineer (ADR index, PRD updates)
- **Can parallelize**: READMEs, runbooks, validation reports all independent
- **Opportunistic**: Can distribute across multiple team members

**Sprint 4** (Polish):
- **Best**: Continuous improvement, distribute across team
- **Automatable**: Many tasks (DOC-INVENTORY resolution, frontmatter standardization)
- **Low priority**: Complete as capacity allows

### Automation Opportunities

**Immediate** (implement during sprints):
- Task 1.3: Script to compare INDEX.md status vs. frontmatter status (status-check.sh)
- Task 2.3: Script to find ADR references (find-adr-refs.sh)
- Task 2.6: README template generator (readme-gen.sh)

**Post-Sprint** (prevent recurrence):
- CI check: Validate INDEX.md status matches frontmatter
- CI check: Detect broken internal links
- CI reminder: Comment on PR when PROMPT-0 initiative validated (archive reminder)
- CI reject: Block PR with code changes but no doc updates (doc-with-feature policy)

**Long-term** (continuous improvement):
- Auto-generate INDEX.md from frontmatter + directory scan
- Documentation coverage reports (which features lack PRD/TDD/VP)
- Stale doc detector (PRD/TDD not updated in 90+ days)

---

## Handoff Checklist

**Sprint 1 Handoff** (to execution team):
- [ ] Sprint 1 tasks reviewed with execution team
- [ ] Task 1.1 (commit) scheduled as first task (non-negotiable)
- [ ] Task 1.2 (status lifecycle) assigned to senior engineer or tech lead
- [ ] Task 1.3 (INDEX.md audit) assigned to engineer familiar with features
- [ ] Task 1.4 (file moves) can execute independently (git mv automation)
- [ ] Task 1.5 (skill references) reviewed with architect (decision: restore vs. replace)
- [ ] All Sprint 1 completion criteria understood
- [ ] Sprint 1 end date set (recommended: 1 day dedicated)

**Sprint 2 Handoff**:
- [ ] Dependencies from Sprint 1 verified complete
- [ ] Task 2.1 (cache docs) assigned to cache system SME
- [ ] Task 2.6 (READMEs) assigned to technical writer or senior engineer
- [ ] Archival tasks (2.4, 2.5) can parallelize
- [ ] Sprint 2 end date set

**Sprint 3 Handoff**:
- [ ] Runbook creation (3.2) assigned to ops-familiar engineer
- [ ] Validation reports (3.3) assigned to feature owners (SaveSession, Cache)
- [ ] ADR index (3.4) can execute independently
- [ ] Tasks can distribute across team (all independent)

**Sprint 4 Handoff**:
- [ ] Backlog items prioritized for continuous improvement
- [ ] Automation opportunities identified for implementation
- [ ] Quarterly documentation cleanup policy established

---

## Appendix: Quick Reference

### Critical Items (Must Fix Immediately)

1. **DEBT-040**: Commit uncommitted changes (30 min) - PREVENTS DATA LOSS
2. **DEBT-037**: Define status values (1 hr) - BLOCKS TRUST RESTORATION
3. **DEBT-001**: Fix INDEX.md status (2-3 hr) - RESTORES TRUST
4. **DEBT-016**: Move PROMPT-* files (1 hr) - UNBLOCKS STRUCTURE
5. **DEBT-026**: Fix skill references (1-2 hr) - UNBLOCKS ONBOARDING
6. **DEBT-008**: Mark superseded PRD (30 min) - PREVENTS WASTED WORK

**Total Critical Path**: 6-8 hours

### High-ROI Quick Wins (30 min - 1 hour each)

- DEBT-040: Commit changes (30 min) - prevents data loss
- DEBT-008: Supersession notice (30 min) - prevents 1-2 days wasted work
- DEBT-016: Move files (1 hr) - unblocks 3 downstream items
- DEBT-045: Archive invalidated VP (30 min) - clears testing directory
- DEBT-021: Archive initiatives (1 hr) - clears active directory

### Long-Pole Items (3+ hours each)

- DEBT-001: INDEX.md audit (2-3 hr) - comprehensive status fix
- DEBT-002, 005, 046: Cache docs (3-4 hr) - family-wide update
- DEBT-017, 022, 025: READMEs (3 hr) - directory navigation aids
- DEBT-027: Runbooks (4-6 hr) - operational troubleshooting guides

### Items That Can Parallelize

**Sprint 1**: Tasks 1.1, 1.4, 1.5, 1.6 can run in parallel (no dependencies)
**Sprint 2**: Tasks 2.3, 2.4, 2.5 can run in parallel; Task 2.6 (3 READMEs) can distribute
**Sprint 3**: All tasks independent, full parallelization possible
**Sprint 4**: All items independent, distribute across team

---

**Sprint Plan Complete**

**Handoff to**: Execution team (senior engineer, technical writer, or dedicated doc sprint team)
**Status**: Ready for execution
**Next action**: Schedule Sprint 1 (1 day, 6-8 hours), commit to execution start date
**Expected outcome**: Documentation trust restored, onboarding unblocked, structural integrity established

---

**End of Sprint Plan**
