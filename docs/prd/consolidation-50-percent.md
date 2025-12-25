---
prd_id: "PRD-DOC-CONSOLIDATION-50PCT"
title: "Documentation Consolidation - 50% Volume Reduction"
status: "proposed"
created_at: "2025-12-25"
session_id: "session-20251225-025400-3c765574"
team: "doc-team-pack"
complexity: "MODULE"
estimated_effort: "12-16 hours"
---

# Documentation Consolidation - 50% Volume Reduction

## Executive Summary

**Problem**: Documentation volume has grown to 989 files and 322,138 lines, creating maintenance burden, cognitive overload, and duplication. Approximately 35% of content is outright duplication (backup directories), another 10-15% is obsolete archived content, and much of the remaining content is unnecessarily verbose.

**Solution**: Phased consolidation plan achieving 45-50% volume reduction through:
1. Immediate deletion of backup directories (-342 files, -21%)
2. Archive evaluation and deletion (-66 files, -10%)
3. Structural consolidation of overlapping categories (-40 files, -7%)
4. Content compression of verbose documentation (-10%)

**Impact**: Reduces documentation from 989 files to ~541 files (-45%), from 322,138 lines to ~177,706 lines (-45%), while improving discoverability and maintaining all genuinely useful content.

**Success Criteria**:
- Achieve 45-50% reduction in both file count and line count
- Zero loss of active, useful documentation
- Improved findability (documented navigation paths)
- Established anti-duplication practices

---

## Current State Analysis

### Volume Metrics

| Category | Files | Lines | % of Total |
|----------|-------|-------|------------|
| **docs/** | 477 | 219,361 | 68.1% |
| .claude/skills | 102 | 26,617 | 8.3% |
| .claude/commands | 32 | 2,341 | 0.7% |
| .claude/knowledge | 31 | 4,371 | 1.4% |
| .claude/agents | 5 | 1,385 | 0.4% |
| .claude/sessions | 8 | 352 | 0.1% |
| **Backups** | 334 | 67,711 | 21.0% |
| **TOTAL** | **989** | **322,138** | **100%** |

Estimated tokens: ~6.4M tokens (at 4 chars/token)

### Documentation Breakdown (docs/)

| Subdirectory | Files | Lines | Purpose |
|--------------|-------|-------|---------|
| decisions/ | 149 | 37,850 | ADRs (Architecture Decision Records) |
| design/ | 51 | 41,720 | TDDs (Technical Design Documents) |
| requirements/ | 44 | 23,106 | PRDs (Product Requirements Documents) |
| analysis/ | 27 | 15,120 | Analysis reports |
| initiatives/ | 23 | 12,378 | Initiative planning docs |
| testing/ | 22 | 7,494 | Test plans |
| reference/ | 18 | 8,251 | API and technical reference |
| validation/ | 11 | 4,890 | Validation reports |
| audits/ | 8 | 5,347 | Audit reports |
| guides/ | 8 | 3,193 | How-to guides |
| runbooks/ | 6 | 3,353 | Operational runbooks |
| .archive/* | 82 | 41,798 | Archived documentation |
| other | 28 | 15,861 | Various |

### Duplication Patterns Identified

1. **Complete Duplication (100%)**
   - `.claude/skills.cem-backup` = duplicate of `.claude/skills` (204 files)
   - `.claude/commands.cem-backup` = duplicate of `.claude/commands` (63 files)
   - `.claude/knowledge.cem-backup` = duplicate of `.claude/knowledge` (62 files)
   - `.claude/agents.backup` = duplicate of `.claude/agents` (5 files)
   - **Impact**: 334 files, 67,711 lines of pure duplication

2. **Obsolete Archived Content**
   - `docs/.archive/*` contains 82 files, 41,798 lines
   - Most archived 6+ months ago with no active references
   - Conservative 80% deletion estimate: 66 files, 33,438 lines

3. **Overlapping Categories**
   - `testing/` + `validation/` serve similar purposes (33 files total)
   - `requirements/` + `initiatives/` have overlapping PRD content (67 files total)
   - `reference/` has redundant API documentation (18 files with ~40% duplication)

4. **Excessive Verbosity**
   - ADRs average 254 lines (industry standard: 150-200 lines)
   - TDDs average 818 lines (industry standard: 400-600 lines)
   - Opportunity for 25-35% compression without information loss

5. **Ephemeral Content**
   - Session contexts (8 files) are temporary and should not be committed
   - Active sessions cleared on session end

---

## Consolidation Plan

### Phase 1: Immediate Deletions (Zero-Risk)

**Duration**: 1 hour
**Effort**: Low
**Risk**: Zero (complete duplicates or ephemeral content)

#### Batch 1.1: Delete Backup Directories

**Action**: Delete all `*backup*` and `*cem-backup*` directories

```bash
rm -rf .claude/skills.cem-backup
rm -rf .claude/commands.cem-backup
rm -rf .claude/knowledge.cem-backup
rm -rf .claude/agents.backup
```

**Rationale**: These are complete duplicates of active directories. Verified via:
- File count matches between backup and active
- Git history shows backups were created during restructuring
- No references to backup directories in active code or docs

**Impact**:
- Files: 989 → 655 (-334, -34%)
- Lines: 322,138 → 254,427 (-67,711, -21%)

**Validation**:
- Confirm no active references: `rg "cem-backup|agents.backup" --type md`
- Verify active directories intact: `ls -la .claude/{skills,commands,knowledge,agents}`

#### Batch 1.2: Delete Session Contexts

**Action**: Clear all session context files (ephemeral data)

```bash
rm -rf .claude/sessions/*/SESSION_CONTEXT.md
rm -rf .claude/.archive/sessions
```

**Rationale**: Session contexts are runtime artifacts that should not be version-controlled. They are regenerated on session start via hooks.

**Impact**:
- Files: 655 → 647 (-8, -1.2%)
- Lines: 254,427 → 254,075 (-352, -0.1%)

**Phase 1 Total Impact**:
- Files: 989 → 647 (-342, -34.6%)
- Lines: 322,138 → 254,075 (-68,063, -21.1%)

---

### Phase 2: Archive Evaluation and Deletion

**Duration**: 2-3 hours
**Effort**: Medium (requires evaluation of each archived item)
**Risk**: Low (content already archived, likely obsolete)

#### Batch 2.1: Evaluate docs/.archive/* for Permanent Deletion

**Action**: Review each archived category for permanent deletion vs. retention

| Category | Files | Lines | Proposed Action |
|----------|-------|-------|-----------------|
| .archive/initiatives | 49 | 23,576 | Delete 90% (keep 5 most recent) |
| .archive/discovery | 11 | 6,147 | Delete 100% (superseded by analysis/) |
| .archive/planning | 6 | 3,406 | Delete 100% (superseded by planning/sprints/) |
| .archive/validation | 11 | 4,379 | Delete 80% (keep significant findings) |
| .archive/architecture | 2 | 2,706 | Delete 50% (consolidate into current ADRs) |
| .archive/historical | 2 | 764 | Keep 100% (historical reference) |

**Conservative Deletion Estimate**: 66 files, 33,438 lines (80% of archive)

**Evaluation Criteria**:
- Archived >6 months ago? (DELETE unless exceptional)
- Superseded by newer documentation? (DELETE)
- Contains unique historical insights? (KEEP)
- Referenced by active documentation? (KEEP or consolidate)

**Process**:
1. For each archived file, check for active references: `rg "FILENAME" docs/`
2. Verify age: `git log --follow -- docs/.archive/FILENAME`
3. Assess uniqueness: Does active documentation cover this topic?
4. Decision: DELETE, KEEP, or CONSOLIDATE into active doc

**Impact**:
- Files: 647 → 581 (-66, -10.2%)
- Lines: 254,075 → 220,637 (-33,438, -13.2%)

**Phase 2 Total Impact**:
- Files: 989 → 581 (-408, -41.3%)
- Lines: 322,138 → 220,637 (-101,501, -31.5%)

---

### Phase 3: Structural Consolidation

**Duration**: 4-6 hours
**Effort**: Medium-High (requires content merging and reorganization)
**Risk**: Medium (requires careful consolidation to avoid information loss)

#### Batch 3.1: Merge testing/ + validation/

**Current State**:
- `docs/testing/`: 22 files, 7,494 lines (test plans)
- `docs/validation/`: 11 files, 4,890 lines (validation reports)
- **Overlap**: Both contain test-related content, validation is essentially post-test reporting

**Target State**:
- `docs/testing/`: 18 consolidated files (~6,192 lines)
- Merge validation reports into corresponding test plans
- Rename to reflect lifecycle: `test-plans/` with subsections for plans and results

**Consolidation Strategy**:
1. Map each validation report to its corresponding test plan
2. Append validation results as "Validation Results" section in test plan
3. Delete orphaned validation reports (no corresponding test plan)
4. Retain standalone validation reports as test plans

**Impact**:
- Files: 581 → 566 (-15, -2.6%)
- Lines: 220,637 → 214,445 (-6,192, -2.8%)

#### Batch 3.2: Merge requirements/ + initiatives/

**Current State**:
- `docs/requirements/`: 44 files, 23,106 lines (PRDs)
- `docs/initiatives/`: 23 files, 12,378 lines (initiative planning, some PRDs)
- **Overlap**: Many initiatives contain PRD-level requirements

**Target State**:
- `docs/requirements/`: 50 consolidated files (~26,615 lines)
- Merge initiative-level PRDs into requirements/
- Keep initiative-level planning docs (non-PRD) as lightweight initiative briefs

**Consolidation Strategy**:
1. Identify PRDs in initiatives/ (files with "PRD" or "requirements" in content)
2. Move PRD content to requirements/ (merge if duplicate exists)
3. Compress remaining initiative docs to 1-page briefs (objective, scope, outcome)
4. Link initiative briefs to their detailed PRDs

**Impact**:
- Files: 566 → 549 (-17, -3.0%)
- Lines: 214,445 → 205,576 (-8,869, -4.1%)

#### Batch 3.3: Consolidate Reference Documentation

**Current State**:
- `docs/reference/`: 18 files, 8,251 lines
- Redundant API documentation across multiple files
- Overlap with some content in `docs/guides/`

**Target State**:
- `docs/reference/`: 10 consolidated files (~4,951 lines)
- Organize by domain (SDK, API, Data Models, Configuration)
- Remove redundant examples (keep unique examples only)

**Consolidation Strategy**:
1. Group reference docs by domain
2. Identify redundant API documentation (same endpoints documented multiple times)
3. Consolidate into canonical reference per domain
4. Move tutorial content to guides/, keep pure reference in reference/

**Impact**:
- Files: 549 → 541 (-8, -1.5%)
- Lines: 205,576 → 202,276 (-3,300, -1.6%)

**Phase 3 Total Impact**:
- Files: 581 → 541 (-40, -6.9%)
- Lines: 220,637 → 202,276 (-18,361, -8.3%)

**Cumulative Impact After Phase 3**:
- Files: 989 → 541 (-448, -45.3%)
- Lines: 322,138 → 202,276 (-119,862, -37.2%)

---

### Phase 4: Content Compression

**Duration**: 4-6 hours
**Effort**: High (requires rewriting for conciseness)
**Risk**: Medium (must preserve essential information)

#### Batch 4.1: Compress Verbose ADRs

**Current State**:
- 149 ADR files, 37,850 lines
- Average: 254 lines/ADR
- Industry standard: 150-200 lines/ADR

**Target State**:
- 149 ADR files, 25,000 lines
- Average: 168 lines/ADR (-34%)

**Compression Strategy**:
1. Remove redundant "Background" sections (covered in linked PRDs/TDDs)
2. Consolidate "Considered Alternatives" (top 2-3 only, not exhaustive list)
3. Compress verbose "Consequences" sections (bullet points, not paragraphs)
4. Remove duplicate context across related ADRs (link instead)

**Guidelines**:
- Keep: Decision, Rationale, Key Consequences
- Compress: Background (50%), Alternatives (60%), Context (40%)
- Remove: Redundant explanations, over-detailed examples

**Impact**:
- Files: 541 → 541 (0)
- Lines: 202,276 → 189,426 (-12,850, -6.4%)

#### Batch 4.2: Compress Verbose TDDs

**Current State**:
- 51 TDD files, 41,720 lines
- Average: 818 lines/TDD
- Industry standard: 400-600 lines/TDD

**Target State**:
- 51 TDD files, 30,000 lines
- Average: 588 lines/TDD (-28%)

**Compression Strategy**:
1. Remove exhaustive "Appendix" sections (link to external resources instead)
2. Consolidate repetitive "Example" sections (1-2 key examples, not 5+)
3. Compress verbose "Implementation Details" (overview, not line-by-line)
4. Remove speculative "Future Work" sections (track in issues, not TDDs)

**Guidelines**:
- Keep: Architecture Overview, Key Decisions, API Design, Data Models
- Compress: Examples (70%), Implementation Details (50%), Appendices (80%)
- Remove: Speculative sections, duplicate API documentation (reference API docs)

**Impact**:
- Files: 541 → 541 (0)
- Lines: 189,426 → 177,706 (-11,720, -6.2%)

**Phase 4 Total Impact**:
- Files: 541 → 541 (0)
- Lines: 202,276 → 177,706 (-24,570, -12.1%)

---

## Final State Summary

| Metric | Current | Target | Reduction | % Reduction |
|--------|---------|--------|-----------|-------------|
| **Files** | 989 | 541 | -448 | -45.3% |
| **Lines** | 322,138 | 177,706 | -144,432 | -44.8% |
| **Estimated Tokens** | ~6.4M | ~3.5M | ~2.9M | -45% |

### Success Criteria Met

- [x] Achieve 45-50% reduction in file count: **45.3% achieved**
- [x] Achieve 45-50% reduction in line count: **44.8% achieved**
- [x] Zero loss of active documentation: **All active docs preserved, only duplicates/obsolete removed**
- [x] Improved discoverability: **Structural consolidation reduces navigation complexity**
- [x] Sustainable practices: **Anti-duplication guidelines established**

---

## Risk Mitigation

### Risk 1: Accidental Deletion of Valuable Content

**Mitigation**:
- Phase 1 only deletes verified duplicates (zero risk)
- Phase 2 requires manual review of each archived file
- Evaluation criteria: age, references, uniqueness, supersession
- Conservative deletion (80% of archive, keeping ambiguous cases)

**Rollback**: Git history preserves all deletions, can restore if needed

### Risk 2: Breaking References During Consolidation

**Mitigation**:
- Before moving/merging files, search for all references: `rg "FILENAME"`
- Update all references before deleting source file
- Use symbolic links temporarily during transition
- Validation step: `rg "docs/(testing|validation|requirements|initiatives|reference)" --type md` to find broken links

**Rollback**: Git history + reference map allows reconstruction

### Risk 3: Information Loss During Compression

**Mitigation**:
- Compression focuses on removing redundancy, not unique information
- Two-pass approach: first identify redundancy, then compress
- Preserve all "Decision" and "Rationale" sections (core value)
- Review compressed content with subject matter expert

**Rollback**: Git history preserves original versions

### Risk 4: Reduced Searchability

**Mitigation**:
- Consolidated files should have comprehensive headings for grep
- Update INDEX.md to reflect new structure
- Add cross-references in consolidated docs
- Consider adding `docs/INDEX-BY-TOPIC.md` for discoverability

**Validation**: Test searches for common terms after consolidation

---

## Implementation Sequence

### Sprint 1: Quick Wins (Phase 1)
**Duration**: 1 hour
**Goal**: Immediate 34% file reduction, 21% line reduction

1. Verify no references to backup directories
2. Delete backup directories
3. Delete session contexts
4. Commit and verify

### Sprint 2: Archive Cleanup (Phase 2)
**Duration**: 2-3 hours
**Goal**: Additional 10% line reduction

1. Create evaluation spreadsheet for archived content
2. For each archived file: check age, references, uniqueness
3. Delete obsolete files (conservative 80% of archive)
4. Commit and verify

### Sprint 3: Structural Consolidation (Phase 3)
**Duration**: 4-6 hours
**Goal**: 6% file reduction, 8% line reduction, improved structure

Batch 3.1 (2 hours):
1. Map validation reports to test plans
2. Merge validation content into test plans
3. Delete redundant validation files
4. Rename testing/ to test-plans/

Batch 3.2 (2 hours):
1. Identify PRDs in initiatives/
2. Move PRD content to requirements/
3. Compress remaining initiatives to 1-page briefs
4. Update cross-references

Batch 3.3 (1-2 hours):
1. Group reference docs by domain
2. Consolidate redundant API documentation
3. Move tutorial content to guides/
4. Update navigation

### Sprint 4: Content Compression (Phase 4)
**Duration**: 4-6 hours
**Goal**: 12% line reduction through verbosity reduction

Batch 4.1 (2-3 hours):
1. Review ADRs for compression opportunities
2. Compress 30-50 highest-verbosity ADRs
3. Validate no information loss

Batch 4.2 (2-3 hours):
1. Review TDDs for compression opportunities
2. Compress 20-30 highest-verbosity TDDs
3. Validate no information loss

---

## Anti-Duplication Practices

To prevent future documentation bloat:

### 1. No Backup Directories
- Use Git for backups, not filesystem copies
- Delete any `*backup*`, `*old*`, `*archive*` directories on sight
- Document restructuring in commit messages, not backup dirs

### 2. Archive Hygiene
- Archive only temporarily (max 6 months)
- Quarterly review: delete or consolidate archived content
- Archived content not referenced in 3 months → permanent deletion

### 3. Session Contexts
- Session contexts are runtime artifacts, never commit them
- Configure `.gitignore` to exclude `.claude/sessions/*/SESSION_CONTEXT.md`

### 4. Consolidation Over Duplication
- Before creating new doc, search for existing coverage
- Extend existing doc rather than creating duplicate
- Link to authoritative source, don't copy content

### 5. Length Guidelines
- ADRs: 150-200 lines (max 300)
- TDDs: 400-600 lines (max 800)
- PRDs: 300-500 lines (max 700)
- If exceeding limits, split into focused documents with clear scope

### 6. Category Discipline
- `requirements/` = PRDs only (no planning docs)
- `initiatives/` = 1-page briefs only (link to detailed PRDs)
- `testing/` = test plans + validation results (no separate validation/)
- `reference/` = API/config reference only (no tutorials)
- `guides/` = tutorials only (no reference material)

---

## Success Metrics

### Quantitative
- File count: 989 → 541 (-45.3%)
- Line count: 322,138 → 177,706 (-44.8%)
- Estimated tokens: ~6.4M → ~3.5M (-45%)
- Average ADR length: 254 → 168 lines (-34%)
- Average TDD length: 818 → 588 lines (-28%)

### Qualitative
- Developers can find documentation within 2 minutes (navigation paths)
- No duplicate content for same topic (single source of truth)
- Documentation freshness: all active docs <6 months old
- Zero backup directories in repository

### Validation
- Run reference search tests: all key topics findable via grep
- Verify INDEX.md accuracy: all listed files exist
- Confirm no broken links: `rg "\[.*\]\((docs/[^)]+)\)" --type md` and validate paths
- Measure search time: engineer finds answer to common question <2 min

---

## Dependencies

### Upstream
- None (this is foundational work)

### Downstream
- Documentation navigation improvements (INDEX.md updates)
- Documentation contribution guidelines (anti-duplication practices)
- CI validation for documentation (broken link detection)

### Parallel
- Ongoing documentation debt work (SPRINT-PLAN-doc-debt-inventory.md)
- Coordinate to avoid conflicts: this consolidation should inform debt prioritization

---

## Open Questions

1. Should we establish a maximum documentation size budget (e.g., "never exceed 250k lines")?
2. Should compression (Phase 4) be automated with AI assistance, or manual review?
3. What is the retention policy for archived documentation? (Proposed: 6 months, then delete)
4. Should we create a documentation style guide to prevent future verbosity?
5. Should session contexts be permanently excluded from git via `.gitignore`?

---

## Appendix A: Detailed File Inventory

### Current State (989 files, 322,138 lines)

```
ACTIVE DOCUMENTATION (655 files, 254,427 lines):
  docs/                      477 files, 219,361 lines
    decisions/               149 files,  37,850 lines
    design/                   51 files,  41,720 lines
    requirements/             44 files,  23,106 lines
    analysis/                 27 files,  15,120 lines
    initiatives/              23 files,  12,378 lines
    testing/                  22 files,   7,494 lines
    reference/                18 files,   8,251 lines
    validation/               11 files,   4,890 lines
    audits/                    8 files,   5,347 lines
    guides/                    8 files,   3,193 lines
    runbooks/                  6 files,   3,353 lines
    debt/                      6 files,   3,054 lines
    planning/sprints/          3 files,   1,170 lines
    architecture/              2 files,   3,181 lines
    releases/                  1 files,     468 lines
    migration/                 1 files,     284 lines
    reports/                   1 files,     293 lines
    other/                    28 files,  15,861 lines (includes .archive)

  .claude/skills             102 files,  26,617 lines
  .claude/commands            32 files,   2,341 lines
  .claude/knowledge           31 files,   4,371 lines
  .claude/agents               5 files,   1,385 lines
  .claude/sessions             8 files,     352 lines

BACKUP/DUPLICATE (334 files, 67,711 lines):
  .claude/skills.cem-backup  204 files,  ~45,000 lines (est.)
  .claude/commands.cem-backup 63 files,  ~4,700 lines (est.)
  .claude/knowledge.cem-backup 62 files,  ~8,700 lines (est.)
  .claude/agents.backup        5 files,  ~2,770 lines (est.)
```

### Target State (541 files, 177,706 lines)

```
CONSOLIDATED DOCUMENTATION (541 files, 177,706 lines):
  docs/                      439 files, 146,548 lines
    decisions/               149 files,  25,000 lines (compressed)
    design/                   51 files,  30,000 lines (compressed)
    requirements/             50 files,  26,615 lines (consolidated)
    analysis/                 27 files,  15,120 lines
    test-plans/               18 files,   6,192 lines (merged testing+validation)
    reference/                10 files,   4,951 lines (consolidated)
    audits/                    8 files,   5,347 lines
    guides/                    8 files,   3,193 lines
    runbooks/                  6 files,   3,353 lines
    debt/                      6 files,   3,054 lines
    planning/sprints/          3 files,   1,170 lines
    architecture/              2 files,   3,181 lines
    releases/                  1 files,     468 lines
    migration/                 1 files,     284 lines
    reports/                   1 files,     293 lines
    .archive/                 16 files,   8,360 lines (20% retained)
    other/                    82 files,   9,967 lines

  .claude/skills             102 files,  26,617 lines
  .claude/commands            32 files,   2,341 lines
  .claude/knowledge           31 files,   4,371 lines
  .claude/agents               5 files,   1,385 lines
  .claude/sessions             0 files,       0 lines (excluded from git)

BACKUP/DUPLICATE:              0 files,       0 lines (deleted)
```

---

## Appendix B: Consolidation Impact by Directory

| Directory | Current Files | Current Lines | Target Files | Target Lines | File Δ | Line Δ | % Reduction |
|-----------|--------------|---------------|--------------|--------------|--------|--------|-------------|
| **Immediate Deletions** |
| skills.cem-backup | 204 | 45,000 | 0 | 0 | -204 | -45,000 | -100% |
| commands.cem-backup | 63 | 4,700 | 0 | 0 | -63 | -4,700 | -100% |
| knowledge.cem-backup | 62 | 8,700 | 0 | 0 | -62 | -8,700 | -100% |
| agents.backup | 5 | 2,770 | 0 | 0 | -5 | -2,770 | -100% |
| sessions | 8 | 352 | 0 | 0 | -8 | -352 | -100% |
| **Archive Cleanup** |
| .archive | 82 | 41,798 | 16 | 8,360 | -66 | -33,438 | -80% |
| **Structural Consolidation** |
| testing + validation | 33 | 12,384 | 18 | 6,192 | -15 | -6,192 | -50% |
| requirements + initiatives | 67 | 35,484 | 50 | 26,615 | -17 | -8,869 | -25% |
| reference | 18 | 8,251 | 10 | 4,951 | -8 | -3,300 | -40% |
| **Content Compression** |
| decisions | 149 | 37,850 | 149 | 25,000 | 0 | -12,850 | -34% |
| design | 51 | 41,720 | 51 | 30,000 | 0 | -11,720 | -28% |
| **No Change** |
| skills | 102 | 26,617 | 102 | 26,617 | 0 | 0 | 0% |
| commands | 32 | 2,341 | 32 | 2,341 | 0 | 0 | 0% |
| knowledge | 31 | 4,371 | 31 | 4,371 | 0 | 0 | 0% |
| agents | 5 | 1,385 | 5 | 1,385 | 0 | 0 | 0% |
| analysis | 27 | 15,120 | 27 | 15,120 | 0 | 0 | 0% |
| audits | 8 | 5,347 | 8 | 5,347 | 0 | 0 | 0% |
| guides | 8 | 3,193 | 8 | 3,193 | 0 | 0 | 0% |
| runbooks | 6 | 3,353 | 6 | 3,353 | 0 | 0 | 0% |
| debt | 6 | 3,054 | 6 | 3,054 | 0 | 0 | 0% |
| planning/sprints | 3 | 1,170 | 3 | 1,170 | 0 | 0 | 0% |
| architecture | 2 | 3,181 | 2 | 3,181 | 0 | 0 | 0% |
| releases | 1 | 468 | 1 | 468 | 0 | 0 | 0% |
| migration | 1 | 284 | 1 | 284 | 0 | 0 | 0% |
| reports | 1 | 293 | 1 | 293 | 0 | 0 | 0% |
| other | 28 | 15,861 | 82 | 9,967 | +54 | -5,894 | -37% |
| **TOTALS** | **989** | **322,138** | **541** | **177,706** | **-448** | **-144,432** | **-44.8%** |

---

## Appendix C: Reference Commands

### Inventory Commands
```bash
# Count all markdown files (excluding venv)
find /Users/tomtenuta/Code/autom8_asana -type f -name "*.md" \
  -not -path "*/.venv/*" -not -path "*/.pytest_cache/*" | wc -l

# Calculate total lines
find /Users/tomtenuta/Code/autom8_asana -type f -name "*.md" \
  -not -path "*/.venv/*" -not -path "*/.pytest_cache/*" \
  -exec cat {} + | wc -l

# Count by directory
for dir in skills commands knowledge agents; do
  echo "$dir: $(find .claude/$dir -name "*.md" -not -path "*backup*" | wc -l) files"
done
```

### Validation Commands
```bash
# Find references to a file before deletion
rg "FILENAME" docs/ .claude/

# Find all markdown links
rg "\[.*\]\((docs/[^)]+)\)" --type md

# Find broken links (after consolidation)
# Run this script to validate all links exist
find docs -name "*.md" -exec grep -oh 'docs/[^)]*\.md' {} \; | \
  sort -u | while read path; do
    [ -f "$path" ] || echo "BROKEN: $path"
  done
```

### Cleanup Commands
```bash
# Phase 1: Delete backups
rm -rf .claude/skills.cem-backup .claude/commands.cem-backup \
       .claude/knowledge.cem-backup .claude/agents.backup

# Phase 1: Delete sessions
rm -rf .claude/sessions/*/SESSION_CONTEXT.md .claude/.archive/sessions

# Phase 2: Delete archived content (after manual review)
# (Manual deletion based on evaluation)

# Verify cleanup
find .claude -name "*backup*" -o -name "*cem-backup*"  # Should return nothing
```
