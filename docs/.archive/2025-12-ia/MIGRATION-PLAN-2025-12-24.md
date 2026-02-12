# Documentation Migration Plan

Version: 1.0
Date: 2025-12-24
Author: Information Architect Agent
Based on: [DOC-AUDIT-REPORT-2025-12-24.md](DOC-AUDIT-REPORT-2025-12-24.md)
Target: [INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md](INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md)

---

## Overview

This migration plan reorganizes 115 documentation files (62 PRDs + 53 TDDs + PROMPT files) into a clearer structure optimized for findability. The migration is sequenced to minimize disruption and preserve git history.

**Estimated Total Time**: 4-6 hours (across 8 phases)

**Key Principle**: Use `git mv` for all file relocations to preserve history.

---

## Phase 1: Structure Creation (15 minutes)

**Goal**: Create new directories and README files

**No dependencies**: Safe to execute immediately

### Actions

#### 1.1 Create New Directories
```bash
cd /Users/tomtenuta/Code/autom8_asana/docs
mkdir -p planning/sprints
mkdir -p runbooks
```

#### 1.2 Create Directory READMEs

Create these files (content briefs in [CONTENT-BRIEFS-2025-12-24.md](CONTENT-BRIEFS-2025-12-24.md)):

- `requirements/README.md` - What PRDs are, naming conventions
- `design/README.md` - What TDDs are, PRD-TDD pairing
- `initiatives/README.md` - What PROMPT files are, lifecycle
- `planning/README.md` - Sprint planning process
- `planning/sprints/README.md` - Sprint decomposition docs
- `reference/README.md` - What reference docs are
- `runbooks/README.md` - What runbooks are, when to use

#### 1.3 Update .gitignore (if needed)
Ensure no accidental exclusions of new directories.

**Completion Criteria**:
- [ ] All new directories exist
- [ ] All README files created with proper content
- [ ] No existing documentation affected

---

## Phase 2: PROMPT File Relocation (15 minutes)

**Goal**: Move 15 PROMPT-* files from `/requirements/` to `/initiatives/`

**Dependencies**: Phase 1 complete (`/initiatives/` must exist)

### Files to Move

From `/docs/requirements/` to `/docs/initiatives/`:

```bash
cd /Users/tomtenuta/Code/autom8_asana/docs

# Move PROMPT-0-* files
git mv initiatives/PROMPT-0-CACHE-INTEGRATION.md initiatives/
git mv initiatives/PROMPT-0-CACHE-LIGHTWEIGHT-STALENESS.md initiatives/
git mv initiatives/PROMPT-0-CACHE-OPTIMIZATION-PHASE2.md initiatives/
git mv initiatives/PROMPT-0-CACHE-OPTIMIZATION-PHASE3.md initiatives/
git mv initiatives/PROMPT-0-CACHE-PERF-DETECTION.md initiatives/
git mv initiatives/PROMPT-0-CACHE-PERF-FETCH-PATH.md initiatives/
git mv initiatives/PROMPT-0-CACHE-PERF-HYDRATION.md initiatives/
git mv initiatives/PROMPT-0-CACHE-PERF-STORIES.md initiatives/
git mv initiatives/PROMPT-0-CACHE-UTILIZATION.md initiatives/
git mv initiatives/PROMPT-0-DOCS-EPOCH-RESET.md initiatives/
git mv initiatives/PROMPT-0-PIPELINE-AUTOMATION-ENHANCEMENT.md initiatives/
git mv initiatives/PROMPT-0-TECH-DEBT-REMEDIATION.md initiatives/
git mv initiatives/PROMPT-0-WATERMARK-CACHE.md initiatives/
git mv initiatives/PROMPT-0-WORKSPACE-PROJECT-REGISTRY.md initiatives/

# Move PROMPT-MINUS-1-* files
git mv initiatives/PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md initiatives/
```

**Files Affected**: 15 files (~280K total)

### Update INDEX.md

Update paths in Initiatives section (lines 172-188):

**Before**:
```markdown
| [PROMPT-0-WORKSPACE-PROJECT-REGISTRY](initiatives/PROMPT-0-WORKSPACE-PROJECT-REGISTRY.md) | ...
```

**After**:
```markdown
| [PROMPT-0-WORKSPACE-PROJECT-REGISTRY](initiatives/PROMPT-0-WORKSPACE-PROJECT-REGISTRY.md) | ...
```

**Completion Criteria**:
- [ ] All 15 PROMPT files moved to `/initiatives/`
- [ ] INDEX.md links updated to point to new locations
- [ ] No broken links in repository
- [ ] Git history preserved (check `git log --follow initiatives/PROMPT-0-CACHE-INTEGRATION.md`)

---

## Phase 3: Sprint Documentation Relocation (15 minutes)

**Goal**: Move sprint planning docs from `/requirements/` and `/design/` to `/planning/sprints/`

**Dependencies**: Phase 1 complete (`/planning/sprints/` must exist)

### Files to Move

**From `/docs/requirements/` to `/docs/planning/sprints/`**:
```bash
cd /Users/tomtenuta/Code/autom8_asana/docs

git mv planning/sprints/PRD-SPRINT-1-PATTERN-COMPLETION.md planning/sprints/
git mv planning/sprints/PRD-SPRINT-3-DETECTION-DECOMPOSITION.md planning/sprints/
git mv planning/sprints/PRD-SPRINT-4-SAVESESSION-DECOMPOSITION.md planning/sprints/
git mv planning/sprints/PRD-SPRINT-5-CLEANUP.md planning/sprints/
```

**From `/docs/design/` to `/docs/planning/sprints/`**:
```bash
git mv planning/sprints/TDD-SPRINT-1-PATTERN-COMPLETION.md planning/sprints/
git mv planning/sprints/TDD-SPRINT-3-DETECTION-DECOMPOSITION.md planning/sprints/
git mv planning/sprints/TDD-SPRINT-4-SAVESESSION-DECOMPOSITION.md planning/sprints/
git mv planning/sprints/TDD-SPRINT-5-CLEANUP.md planning/sprints/
```

**Files Affected**: 8 files (4 PRDs + 4 TDDs)

### Update INDEX.md

**Option A**: Remove from INDEX.md (sprint docs are not formal requirements)

**Option B**: Create new "Sprint Planning" section in INDEX.md

**Recommendation**: Remove from INDEX.md. Sprint docs are temporary planning artifacts, not formal specifications.

**Completion Criteria**:
- [ ] All 8 sprint docs moved to `/planning/sprints/`
- [ ] INDEX.md updated (sprint entries removed or relocated to new section)
- [ ] No broken links
- [ ] Git history preserved

---

## Phase 4: Archive Completed Initiatives (10 minutes)

**Goal**: Move completed PROMPT-* files to `.archive/initiatives/2025-Q4/`

**Dependencies**: Phase 2 complete (PROMPT files in `/initiatives/`)

### Create Archive Directory
```bash
cd /Users/tomtenuta/Code/autom8_asana/docs
mkdir -p .archive/initiatives/2025-Q4
```

### Files to Archive

Based on audit findings (status = "Complete"):

```bash
cd /Users/tomtenuta/Code/autom8_asana/docs

git mv initiatives/PROMPT-0-CACHE-OPTIMIZATION-PHASE2.md .archive/initiatives/2025-Q4/
git mv initiatives/PROMPT-0-CACHE-OPTIMIZATION-PHASE3.md .archive/initiatives/2025-Q4/
git mv initiatives/PROMPT-0-CACHE-PERF-FETCH-PATH.md .archive/initiatives/2025-Q4/
git mv initiatives/PROMPT-0-WATERMARK-CACHE.md .archive/initiatives/2025-Q4/
git mv initiatives/PROMPT-0-WORKSPACE-PROJECT-REGISTRY.md .archive/initiatives/2025-Q4/
```

**Rationale**:
- CACHE-OPTIMIZATION-PHASE2: Validated (VP-CACHE-OPTIMIZATION-P2 PASS)
- CACHE-OPTIMIZATION-PHASE3: Validated (VP-CACHE-OPTIMIZATION-P3 PASS)
- CACHE-PERF-FETCH-PATH: Validated (VP-CACHE-PERF-FETCH-PATH PASS)
- WATERMARK-CACHE: Validated (VALIDATION-WATERMARK-CACHE PASS)
- WORKSPACE-PROJECT-REGISTRY: Validated (VP-WORKSPACE-PROJECT-REGISTRY APPROVED)

**Files Affected**: 5 files

### Update INDEX.md

Update Initiatives section to mark these as archived:

**Before**:
```markdown
| [PROMPT-0-CACHE-OPTIMIZATION-PHASE2](initiatives/PROMPT-0-CACHE-OPTIMIZATION-PHASE2.md) | ... | Complete |
```

**After**:
```markdown
| [PROMPT-0-CACHE-OPTIMIZATION-PHASE2](.archive/initiatives/2025-Q4/PROMPT-0-CACHE-OPTIMIZATION-PHASE2.md) | ... | Archived |
```

Or remove from active Initiatives section, add to Archived Content section.

**Completion Criteria**:
- [ ] 5 completed PROMPT files archived
- [ ] INDEX.md updated to reflect archive locations
- [ ] Active initiatives section decluttered

---

## Phase 5: Consolidation - Create Cache Reference Docs (1-2 hours)

**Goal**: Extract duplicated cache concepts to reference docs

**Dependencies**: None (creates new files, doesn't move existing)

### New Files to Create

Content briefs in [CONTENT-BRIEFS-2025-12-24.md](CONTENT-BRIEFS-2025-12-24.md).

#### 5.1 REF-cache-staleness-detection.md
**Source Material**:
- PRD-CACHE-LIGHTWEIGHT-STALENESS.md (sections on staleness heuristics)
- PRD-CACHE-OPTIMIZATION-P2.md (staleness detection discussion)
- PRD-WATERMARK-CACHE.md (watermark-based staleness)
- ADR-0019-staleness-detection-algorithm.md
- ADR-0133-progressive-ttl-extension-algorithm.md

**Extraction Process**:
1. Read all source documents
2. Identify common staleness detection concepts
3. Create authoritative reference covering all algorithms
4. Update source PRDs to replace explanations with link: `For staleness detection details, see [REF-cache-staleness-detection](../reference/REF-cache-staleness-detection.md).`

**Estimated Size**: 8-10K
**Estimated Time**: 45 minutes

#### 5.2 REF-cache-ttl-strategy.md
**Source Material**:
- PRD-CACHE-INTEGRATION.md (base TTL calculation)
- PRD-CACHE-LIGHTWEIGHT-STALENESS.md (progressive TTL extension)
- PRD-CACHE-OPTIMIZATION-P2.md (TTL tuning)
- PRD-WATERMARK-CACHE.md (TTL for watermark cache)
- ADR-0126-entity-ttl-resolution.md
- ADR-0133-progressive-ttl-extension-algorithm.md

**Extraction Process**: Same as 5.1

**Estimated Size**: 6-8K
**Estimated Time**: 30 minutes

#### 5.3 REF-cache-provider-protocol.md
**Source Material**:
- PRD-CACHE-INTEGRATION.md (CacheProvider protocol definition)
- PRD-CACHE-PERF-FETCH-PATH.md (fetch path integration)
- PRD-CACHE-PERF-DETECTION.md (detection caching)
- PRD-CACHE-PERF-HYDRATION.md (hydration caching)
- PRD-CACHE-PERF-STORIES.md (stories caching)
- TDD-CACHE-INTEGRATION.md (implementation details)
- ADR-0123-cache-provider-selection.md

**Extraction Process**: Same as 5.1

**Estimated Size**: 10-12K
**Estimated Time**: 45 minutes

### Update INDEX.md

Add to Reference Data section:

```markdown
## Reference Data

| File | Description |
|------|-------------|
| [REF-entity-type-table.md](reference/REF-entity-type-table.md) | Business model entity hierarchy reference |
| [REF-custom-field-catalog.md](reference/REF-custom-field-catalog.md) | Custom field catalog (108 fields across 5 models) |
| [REF-cache-staleness-detection.md](reference/REF-cache-staleness-detection.md) | Cache staleness detection algorithms and heuristics |
| [REF-cache-ttl-strategy.md](reference/REF-cache-ttl-strategy.md) | TTL calculation and progressive extension strategy |
| [REF-cache-provider-protocol.md](reference/REF-cache-provider-protocol.md) | CacheProvider protocol specification |
```

**Completion Criteria**:
- [ ] All 3 reference docs created with comprehensive content
- [ ] Source PRDs updated to link to reference docs instead of duplicating
- [ ] INDEX.md updated with new reference docs
- [ ] Cross-references verified

---

## Phase 6: Create Runbooks (2-3 hours)

**Goal**: Create operational troubleshooting guides for production support

**Dependencies**: None (creates new files)

### New Files to Create

Content briefs in [CONTENT-BRIEFS-2025-12-24.md](CONTENT-BRIEFS-2025-12-24.md).

#### 6.1 RUNBOOK-cache-troubleshooting.md
**Source Material**:
- TDD-CACHE-INTEGRATION.md (error handling)
- ADR-0127-graceful-degradation.md (fallback strategies)
- Recent cache-related commits and issues
- Interview engineer who built cache system

**Estimated Size**: 6-8K
**Estimated Time**: 1 hour

#### 6.2 RUNBOOK-savesession-debugging.md
**Source Material**:
- TDD-0010-save-orchestration.md (dependency graph, error handling)
- PRD-0018-savesession-reliability.md
- ADR-0035-unit-of-work-pattern.md
- ADR-0040-partial-failure-handling.md

**Estimated Size**: 8-10K
**Estimated Time**: 1 hour

#### 6.3 RUNBOOK-detection-system-debugging.md
**Source Material**:
- TDD-DETECTION.md (tier system)
- PRD-DETECTION.md
- ADR-0068-type-detection-strategy.md
- Detection system code in `src/autom8_asana/detection/`

**Estimated Size**: 6-8K
**Estimated Time**: 1 hour

### Update INDEX.md

Add new "Runbooks" section:

```markdown
## Runbooks

| Runbook | System | Description |
|---------|--------|-------------|
| [RUNBOOK-cache-troubleshooting.md](runbooks/RUNBOOK-cache-troubleshooting.md) | Cache | Diagnose cache failures, staleness issues, TTL problems |
| [RUNBOOK-savesession-debugging.md](runbooks/RUNBOOK-savesession-debugging.md) | SaveSession | Debug dependency graphs, partial failures, healing system |
| [RUNBOOK-detection-system-debugging.md](runbooks/RUNBOOK-detection-system-debugging.md) | Detection | Troubleshoot entity type detection failures |
```

**Completion Criteria**:
- [ ] All 3 runbooks created with actionable troubleshooting steps
- [ ] INDEX.md updated with Runbooks section
- [ ] Runbooks validated by on-call engineer (if possible)

---

## Phase 7: Fix INDEX.md Status Divergence (1-2 hours)

**Goal**: Ensure INDEX.md status matches document frontmatter status

**Dependencies**: None (updates metadata only)

**CRITICAL**: This is highest priority for accuracy.

### Audit Process

For each document in INDEX.md:

1. Read document frontmatter `status` field
2. Compare to INDEX.md `Status` column
3. If divergent, determine ground truth:
   - Check git log for implementation commits
   - Check for validation reports (VP-*)
   - Check for code references in codebase
4. Update INDEX.md to match reality
5. Update document frontmatter if needed

### Documents with Known Divergence

From audit report:

| Document | INDEX.md Status | File Status | Ground Truth | Action |
|----------|----------------|-------------|--------------|--------|
| PRD-0002-intelligent-caching.md | Implemented | Draft | Implemented (code updated Dec 24) | Update file → `Implemented` |
| PRD-0005-save-orchestration.md | Implemented | Unknown | Implemented (healing system Dec 15) | Update file → `Implemented` |
| PRD-0007-sdk-functional-parity.md | Implemented | Unknown | Implemented | Update file → `Implemented` |
| PRD-0008-parent-subtask-operations.md | Implemented | Unknown | Implemented | Update file → `Implemented` |
| PRD-0010-business-model-layer.md | Draft | Unknown | Implemented (code Dec 15) | Update both → `Implemented` |
| PRD-0013-hierarchy-hydration.md | Implemented | Unknown | Implemented | Update file → `Implemented` |
| PRD-0014-cross-holder-resolution.md | Implemented | Unknown | Implemented | Update file → `Implemented` |
| PRD-0020-holder-factory.md | Implemented | Unknown | Implemented (Dec 16) | Update file → `Implemented` |
| PRD-0021-async-method-generator.md | Active | Unknown | Superseded by @async_method | Update both → `Superseded` |
| PRD-0022-crud-base-class.md | Active | Unknown | Rejected (TDD-0026 NO-GO) | Update both → `Rejected` |
| PRD-CACHE-INTEGRATION.md | Implemented | Unknown | Implemented (Dec 22) | Update file → `Implemented` |
| PRD-DETECTION.md | Draft | Unknown | Implemented (Dec 15) | Update both → `Implemented` |
| PRD-TECH-DEBT-REMEDIATION.md | Unknown | Unknown | Implemented (Dec 15) | Update both → `Implemented` |
| PRD-WORKSPACE-PROJECT-REGISTRY.md | Draft | Unknown | Implemented (VP APPROVED) | Update both → `Implemented` |

**Estimated Time**: 1-2 hours (verify each, update frontmatter + INDEX.md)

### Validation Script (Optional)

Create `scripts/validate-doc-status.sh`:

```bash
#!/bin/bash
# Validate that INDEX.md status matches document frontmatter

for doc in docs/requirements/PRD-*.md docs/design/TDD-*.md; do
    frontmatter_status=$(grep "^status:" "$doc" | head -1 | cut -d: -f2 | xargs)
    doc_basename=$(basename "$doc")
    index_status=$(grep "$doc_basename" docs/INDEX.md | grep -oP '\| \K[^|]+(?= \|)' | tail -1 | xargs)

    if [ "$frontmatter_status" != "$index_status" ]; then
        echo "DIVERGENCE: $doc_basename"
        echo "  Frontmatter: $frontmatter_status"
        echo "  INDEX.md: $index_status"
    fi
done
```

**Completion Criteria**:
- [ ] All PRDs and TDDs have `status:` in frontmatter
- [ ] INDEX.md status matches document frontmatter (100%)
- [ ] All `Implemented` status claims verified against code/commits
- [ ] All `Superseded` docs have `superseded_by:` link in frontmatter
- [ ] All `Rejected` docs have `decision:` link in frontmatter

---

## Phase 8: Add Supersession Notices (30 minutes)

**Goal**: Add prominent notices to superseded/rejected docs

**Dependencies**: Phase 7 complete (status verified)

### Documents Requiring Notices

#### PRD-PROCESS-PIPELINE.md (Partially Superseded)
**Add at top of file (after frontmatter)**:
```markdown
> **PARTIALLY SUPERSEDED**
>
> The ProcessProjectRegistry requirements (FR-REG-001 through FR-REG-005) have been superseded by [ADR-0101-process-pipeline-correction](../decisions/ADR-0101-process-pipeline-correction.md), which implements WorkspaceProjectRegistry instead.
>
> The FR-TYPE, FR-SECTION, and FR-STATE requirements remain valid.
>
> See [PRD-TECH-DEBT-REMEDIATION](PRD-TECH-DEBT-REMEDIATION.md) for the implemented approach.
```

**Update frontmatter**:
```yaml
status: Superseded
superseded_by: ../decisions/ADR-0101-process-pipeline-correction.md
```

#### PRD-0021-async-method-generator.md (Superseded)
**Add at top of file**:
```markdown
> **SUPERSEDED**
>
> This document has been superseded by the `@async_method` decorator pattern documented in [PRD-PATTERNS-D](PRD-PATTERNS-D.md) (if exists) or implemented in commit `ee3ef8b`.
>
> See [TDD-0025-async-method-decorator](../design/TDD-0025-async-method-decorator.md) for the actual implementation.
>
> Preserved for historical context. Do not implement.
```

**Update frontmatter**:
```yaml
status: Superseded
superseded_by: ../design/TDD-0025-async-method-decorator.md
```

#### PRD-0022-crud-base-class.md (Rejected)
**Add at top of file**:
```markdown
> **REJECTED**
>
> This proposal has been rejected. See [TDD-0026-crud-base-class-evaluation](../design/TDD-0026-crud-base-class-evaluation.md) for the NO-GO decision and rationale.
>
> **Decision**: Explicit methods preferred over metaclass magic for SDK clarity.
>
> Preserved for historical context. Do not implement.
```

**Update frontmatter**:
```yaml
status: Rejected
decision: ../design/TDD-0026-crud-base-class-evaluation.md
```

#### TDD-PROCESS-PIPELINE.md (Partially Superseded)
**Add at top of file**:
```markdown
> **PARTIALLY SUPERSEDED**
>
> This design has been partially superseded by [ADR-0101-process-pipeline-correction](../decisions/ADR-0101-process-pipeline-correction.md).
>
> ProcessProjectRegistry was not implemented. WorkspaceProjectRegistry used instead.
>
> Other design elements (ProcessType, ProcessSection, state machine) remain valid.
```

**Update frontmatter**:
```yaml
status: Superseded
superseded_by: ../decisions/ADR-0101-process-pipeline-correction.md
```

**Completion Criteria**:
- [ ] All superseded docs have prominent notices at top
- [ ] All rejected docs have prominent notices at top
- [ ] All notices link to replacement/decision docs
- [ ] Frontmatter updated with `superseded_by:` or `decision:` fields

---

## Phase 9: Update Cross-References (30 minutes)

**Goal**: Fix broken links caused by file relocations

**Dependencies**: Phases 2, 3, 4 complete (all moves done)

### Link Audit Process

1. Search for references to moved files:
```bash
cd /Users/tomtenuta/Code/autom8_asana/docs
grep -r "initiatives/PROMPT-0-" --include="*.md" .
grep -r "planning/sprints/PRD-SPRINT-" --include="*.md" .
grep -r "planning/sprints/TDD-SPRINT-" --include="*.md" .
```

2. Update links to point to new locations:
   - `initiatives/PROMPT-0-*.md` → `initiatives/PROMPT-0-*.md`
   - `planning/sprints/PRD-SPRINT-*.md` → `planning/sprints/PRD-SPRINT-*.md`
   - `planning/sprints/TDD-SPRINT-*.md` → `planning/sprints/TDD-SPRINT-*.md`
   - Archived files → `.archive/initiatives/2025-Q4/*.md`

3. Verify no broken links:
```bash
# Using markdown-link-check or similar tool
find docs -name "*.md" -exec markdown-link-check {} \;
```

**Completion Criteria**:
- [ ] All cross-references updated
- [ ] No broken internal links
- [ ] Links use relative paths (not absolute)

---

## Rollback Plan

If migration causes issues:

### Rollback Phase 2-4 (File Moves)
```bash
# Revert all moves
git log --oneline | grep "mv" | head -n 30
git revert <commit-hash>...

# Or manually move files back
git mv initiatives/PROMPT-0-*.md requirements/
git mv planning/sprints/PRD-SPRINT-*.md requirements/
git mv planning/sprints/TDD-SPRINT-*.md design/
git mv .archive/initiatives/2025-Q4/PROMPT-0-*.md initiatives/
```

### Rollback Phase 5-6 (New Content)
```bash
# Delete new files
rm reference/REF-cache-*.md
rm runbooks/RUNBOOK-*.md

# Revert PRD updates
git checkout HEAD -- requirements/PRD-CACHE-*.md
```

### Rollback Phase 7-8 (Metadata Updates)
```bash
# Revert INDEX.md and frontmatter changes
git checkout HEAD -- INDEX.md
git checkout HEAD -- requirements/*.md design/*.md
```

---

## Testing & Validation

After each phase:

1. **Build verification**: Ensure documentation build succeeds (if automated)
2. **Link check**: Verify no broken links
3. **INDEX.md validation**: Ensure INDEX.md links resolve
4. **Git history check**: Verify `git log --follow` works for moved files
5. **Search test**: Test common search queries (e.g., "cache staleness") find relevant docs

**Final Validation Checklist**:
- [ ] All files in expected locations per IA spec
- [ ] INDEX.md accurate and up-to-date
- [ ] No broken links in repository
- [ ] Git history preserved for all moved files
- [ ] All new directories have README files
- [ ] Reference docs created and linked from PRDs
- [ ] Runbooks created and accessible
- [ ] Status divergence resolved (100% accuracy)
- [ ] Supersession notices added
- [ ] 30-second findability test passes for key scenarios

---

## Migration Schedule

**Recommended**: Execute in order, one phase per session

| Phase | Time | Can Execute In Parallel | Reviewer |
|-------|------|-------------------------|----------|
| 1 | 15 min | No (foundation) | Tech Writer |
| 2 | 15 min | No (depends on 1) | Tech Writer |
| 3 | 15 min | No (depends on 1) | Tech Writer |
| 4 | 10 min | No (depends on 2) | Tech Writer |
| 5 | 2 hrs | Yes (independent) | Tech Writer |
| 6 | 3 hrs | Yes (independent) | Tech Writer + SME |
| 7 | 2 hrs | No (critical accuracy) | Tech Writer + Lead |
| 8 | 30 min | No (depends on 7) | Tech Writer |
| 9 | 30 min | No (final validation) | Doc Reviewer |

**Total**: 6-8 hours over 2-3 work sessions

**Suggested Sessions**:
- **Session 1** (1 hour): Phases 1-4 (structure + moves)
- **Session 2** (3 hours): Phases 5-6 (content creation)
- **Session 3** (2 hours): Phases 7-9 (accuracy + validation)

---

## Success Criteria

Migration is complete when:

1. **Structure**: All directories match IA spec
2. **Placement**: All files in correct locations
3. **Metadata**: INDEX.md matches document frontmatter (100%)
4. **Links**: No broken cross-references
5. **History**: Git history preserved for all moves
6. **Content**: All new docs created per content briefs
7. **Navigation**: All directories have README files
8. **Notices**: All superseded/rejected docs have prominent warnings
9. **Findability**: Engineers can find docs in <30 seconds
10. **Approval**: Doc Reviewer signs off

---

## Appendix: Complete File Inventory

### Files Staying in Place (85 files)

**In `/requirements/` (47 PRDs after moves)**:
- PRD-0001 through PRD-0024 (24 numbered PRDs)
- PRD-AUTOMATION-LAYER, PRD-CACHE-*, PRD-DETECTION, etc. (23 named PRDs)

**In `/design/` (53 TDDs after moves)**:
- TDD-0001 through TDD-0030 (30 numbered TDDs)
- TDD-AUTOMATION-LAYER, TDD-CACHE-*, TDD-DETECTION, etc. (23 named TDDs)

### Files Moving (23 files)

**requirements/ → initiatives/ (15 files)**:
- All PROMPT-0-*.md files
- PROMPT-MINUS-1-*.md files

**requirements/ → planning/sprints/ (4 files)**:
- PRD-SPRINT-1, PRD-SPRINT-3, PRD-SPRINT-4, PRD-SPRINT-5

**design/ → planning/sprints/ (4 files)**:
- TDD-SPRINT-1, TDD-SPRINT-3, TDD-SPRINT-4, TDD-SPRINT-5

**initiatives/ → .archive/initiatives/2025-Q4/ (5 files)**:
- PROMPT-0-CACHE-OPTIMIZATION-PHASE2
- PROMPT-0-CACHE-OPTIMIZATION-PHASE3
- PROMPT-0-CACHE-PERF-FETCH-PATH
- PROMPT-0-WATERMARK-CACHE
- PROMPT-0-WORKSPACE-PROJECT-REGISTRY

### New Files Created (13 files)

**Directory READMEs (7 files)**:
- requirements/README.md
- design/README.md
- initiatives/README.md
- planning/README.md
- planning/sprints/README.md
- reference/README.md
- runbooks/README.md

**Reference Docs (3 files)**:
- reference/REF-cache-staleness-detection.md
- reference/REF-cache-ttl-strategy.md
- reference/REF-cache-provider-protocol.md

**Runbooks (3 files)**:
- runbooks/RUNBOOK-cache-troubleshooting.md
- runbooks/RUNBOOK-savesession-debugging.md
- runbooks/RUNBOOK-detection-system-debugging.md

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-24 | Initial migration plan based on audit findings |
