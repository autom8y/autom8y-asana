# Documentation Audit Summary (2025-12-24)

## Quick Stats

- **Total PRD/TDD files**: 115 (62 PRDs + 53 TDDs)
- **Total size**: 3.2M
- **Healthy docs**: ~25 (22%)
- **Stale docs**: ~40 (35%)
- **Orphaned docs**: ~5 (4%)
- **Unknown status**: ~45 (39%)

## Top 5 Critical Issues

### 1. INDEX.md Status Divergence (CRITICAL)
**Impact**: Engineers cannot trust documentation index
**Files affected**: 10+ PRDs/TDDs
**Fix time**: 1-2 hours
**Example**: PRD-0002 says "Implemented" in INDEX but "Draft" in file, actual code updated Dec 24

### 2. PROMPT-* File Misplacement (HIGH)
**Impact**: Confuses documentation taxonomy, inflates requirements directory
**Files affected**: 15 files, ~280K
**Fix time**: 15 minutes
**Action**: Move from `/docs/requirements/` to `/docs/initiatives/`, archive completed ones

### 3. Superseded Docs Not Marked (HIGH)
**Impact**: Engineers read outdated/rejected feature docs
**Files affected**: PRD-0021, PRD-0022, PRD-PROCESS-PIPELINE
**Fix time**: 30 minutes
**Action**: Add supersession notices, link to actual implementations

### 4. Sprint Docs Without Status (MEDIUM)
**Impact**: Unclear if planning docs or formal PRDs
**Files affected**: PRD-SPRINT-1 through PRD-SPRINT-5 + TDDs
**Fix time**: 30 minutes
**Action**: Categorize as planning docs, move to `/docs/planning/` or archive

### 5. Implementation-Documentation Gap (MEDIUM)
**Impact**: Implemented features lack formal PRDs
**Files affected**: 5+ features (S2S auth, satellite service, dataframe v2.0, etc.)
**Fix time**: 2-4 hours (if retrospective docs desired)
**Action**: Decide policy - require PRDs retroactively or document as ADRs only

## Immediate Actions (Priority 1)

1. **Audit INDEX.md status values** against actual doc frontmatter and git commits
2. **Add supersession notices** to PRD-0021, PRD-0022, PRD-PROCESS-PIPELINE
3. **Relocate PROMPT-* files** to `/docs/initiatives/`
4. **Archive completed initiatives**: PROMPT-0-CACHE-OPTIMIZATION-PHASE2, PROMPT-0-WATERMARK-CACHE, etc.

**Estimated time**: 2-3 hours total

## Consolidation Opportunities

### Cache Documentation Cluster (9 PRDs, 9 TDDs, ~640K)
**Recommendation**: Extract common concepts to reference docs
- REF-cache-staleness-detection.md
- REF-cache-ttl-strategy.md
- REF-cache-architecture.md

**Benefit**: Reduce duplication across 9 PRD/TDD pairs, single source of truth for cache concepts

### PROMPT-0 + PRD Duplication (14 pairs, ~280K)
**Recommendation**: Archive PROMPT-0-* files after initiative completion
**Benefit**: Remove 280K of redundant context from requirements directory

## Missing Documentation

### Operational Runbooks (Missing)
- Cache troubleshooting
- SaveSession debugging
- Detection system troubleshooting

### Test Plans (Implemented features without TPs)
- Save Orchestration (PRD-0005)
- SDK Functional Parity (PRD-0007)
- Cache Integration (PRD-CACHE-INTEGRATION)

### Directory READMEs (Missing)
- `/docs/requirements/README.md`
- `/docs/design/README.md`
- `/docs/initiatives/README.md`

## Archival Candidates (8 files)

**Immediate**:
1. PROMPT-0-CACHE-OPTIMIZATION-PHASE2.md (phase complete)
2. PROMPT-0-CACHE-PERF-FETCH-PATH.md (P1 complete)
3. PROMPT-0-WORKSPACE-PROJECT-REGISTRY.md (validated APPROVED)
4. PROMPT-0-WATERMARK-CACHE.md (validated PASS)

**Conditional** (if confirmed):
5. PRD-0021-async-method-generator.md (superseded by @async_method)
6. PRD-0022-crud-base-class.md (rejected per TDD-0026)
7. PRD-SPRINT-* series (if sprints completed)
8. PRD-PROCESS-PIPELINE.md FR-REG-* sections (superseded by ADR-0101)

## Recommendations by Role

### Information Architect (Next)
- Design target documentation structure
- Create consolidation plan for cache docs
- Establish archival policy for completed initiatives
- Define PROMPT-* file lifecycle

### Tech Writer (After IA)
- Update stale PRD/TDD status fields
- Create missing runbooks (cache, SaveSession, detection)
- Write directory READMEs
- Extract cache reference docs

### Doc Reviewer (After Writer)
- Verify INDEX.md matches updated documents
- Review supersession notices for clarity
- Validate archival decisions
- Approve final consolidated structure

## Document Organization Recommendations

### Current Structure Issues
1. **Numbered vs Named**: Inconsistent naming (PRD-0001 vs PRD-CACHE-*)
2. **PROMPT-* location**: Should be in `/initiatives/`, not `/requirements/`
3. **Sprint docs**: Should be in `/planning/sprints/`, not mixed with formal PRDs

### Proposed Structure
```
/docs/
  /requirements/
    PRD-*.md (formal requirements only)
  /design/
    TDD-*.md (formal technical designs only)
  /initiatives/
    PROMPT-0-*.md (orchestrator init files)
    PROMPT-MINUS-1-*.md (meta-initiative files)
  /planning/
    /sprints/
      PRD-SPRINT-*.md (sprint decomposition docs)
      TDD-SPRINT-*.md
  /reference/
    REF-cache-*.md (extracted common concepts)
    REF-entity-type-table.md (existing)
    REF-custom-field-catalog.md (existing)
  /runbooks/
    RUNBOOK-cache-troubleshooting.md (new)
    RUNBOOK-savesession-debugging.md (new)
```

### Naming Convention Recommendation
**Going forward**: Use descriptive names (PRD-FEATURE-NAME, TDD-FEATURE-NAME)
**Existing numbered docs**: Keep as-is (don't renumber - preserves git history)
**INDEX.md**: Continue tracking PRD-TDD relationships, use as source of truth

## Staleness Pattern Observed

**Docs updated Dec 18-24**: Well synchronized with code (e.g., cache optimization series)
**Docs updated Dec 9-12**: Show staleness (e.g., PRD-0002 hasn't reflected Dec 24 cache updates)

**Recommendation**: Establish policy - when feature implementation commits occur, corresponding PRD/TDD status should update within 1 week.

## Success Metrics for Cleanup

- [ ] INDEX.md status matches document frontmatter (100% accuracy)
- [ ] Zero PROMPT-* files in `/requirements/` directory
- [ ] All superseded docs have prominent notices
- [ ] All implemented features have status="Implemented" in docs
- [ ] All rejected features have status="Rejected" with rationale
- [ ] Redundant cache explanations reduced from 9 docs to 3 reference docs
- [ ] Engineers can find doc status in <30 seconds using INDEX.md

## Next Steps

1. **Review this audit** with stakeholders
2. **Prioritize recommendations** (1-2-3 priority levels)
3. **Create action plan** with assignments and deadlines
4. **Execute Priority 1 actions** (2-3 hours, immediate impact)
5. **Invoke Information Architect** to design target structure
6. **Schedule quarterly audits** to prevent future drift

---

**Full Report**: `/docs/DOC-AUDIT-REPORT-2025-12-24.md` (detailed findings, evidence, methodology)
**Inventory Data**: `/docs/DOC-INVENTORY-2025-12-24.csv` (structured data for analysis)
