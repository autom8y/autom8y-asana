# ADR Renumbering Specification

**Date**: 2024-12-24
**Session ID**: session-20251224-223231-ba28610c
**Sprint**: ADR Quality Standardization
**Task**: Duplicate Resolution (P0 Critical)

---

## Problem Statement

18 ADR files across 6 number ranges have duplicate numbering, breaking documentation navigation and creating ambiguity. This specification documents the renumbering resolution.

**Affected Ranges**: ADR-0115 through ADR-0120
**Target Range**: ADR-0135 through ADR-0144
**Total Files to Rename**: 10

---

## Renumbering Strategy

**Keep Policy**: First file alphabetically for each duplicate number remains unchanged.
**Renumber Policy**: All other duplicates renumbered sequentially starting at ADR-0135.

**Rationale**: Alphabetical ordering provides deterministic, reproducible selection. ADR-0134 is current highest number, so ADR-0135+ is the next available range.

---

## Complete Renumbering Map

### ADR-0115 (2 files)
- **KEEP**: ADR-0115-parallel-section-fetch-strategy.md
- **RENAME**: ADR-0115-processholder-detection.md → **ADR-0135-processholder-detection.md**

### ADR-0116 (2 files)
- **KEEP**: ADR-0116-batch-cache-population-pattern.md
- **RENAME**: ADR-0116-process-field-architecture.md → **ADR-0136-process-field-architecture.md**

### ADR-0117 (3 files)
- **KEEP**: ADR-0117-accessor-descriptor-unification.md
- **RENAME**: ADR-0117-post-commit-invalidation-hook.md → **ADR-0137-post-commit-invalidation-hook.md**
- **RENAME**: ADR-0117-tier2-pattern-enhancement.md → **ADR-0138-tier2-pattern-enhancement.md**

### ADR-0118 (2 files)
- **KEEP**: ADR-0118-rejection-multi-level-cache.md
- **RENAME**: ADR-0118-self-healing-design.md → **ADR-0139-self-healing-design.md**

### ADR-0119 (3 files)
- **KEEP**: ADR-0119-client-cache-integration-pattern.md
- **RENAME**: ADR-0119-dataframe-task-cache-integration.md → **ADR-0140-dataframe-task-cache-integration.md**
- **RENAME**: ADR-0119-field-mixin-strategy.md → **ADR-0141-field-mixin-strategy.md**

### ADR-0120 (4 files)
- **KEEP**: ADR-0120-batch-cache-population-on-bulk-fetch.md
- **RENAME**: ADR-0120-detection-package-structure.md → **ADR-0142-detection-package-structure.md**
- **RENAME**: ADR-0120-detection-result-caching.md → **ADR-0143-detection-result-caching.md**
- **RENAME**: ADR-0120-healingresult-consolidation.md → **ADR-0144-healingresult-consolidation.md**

---

## Execution Plan

### Phase 1: File Renaming
```bash
git mv docs/decisions/ADR-0115-processholder-detection.md docs/decisions/ADR-0135-processholder-detection.md
git mv docs/decisions/ADR-0116-process-field-architecture.md docs/decisions/ADR-0136-process-field-architecture.md
git mv docs/decisions/ADR-0117-post-commit-invalidation-hook.md docs/decisions/ADR-0137-post-commit-invalidation-hook.md
git mv docs/decisions/ADR-0117-tier2-pattern-enhancement.md docs/decisions/ADR-0138-tier2-pattern-enhancement.md
git mv docs/decisions/ADR-0118-self-healing-design.md docs/decisions/ADR-0139-self-healing-design.md
git mv docs/decisions/ADR-0119-dataframe-task-cache-integration.md docs/decisions/ADR-0140-dataframe-task-cache-integration.md
git mv docs/decisions/ADR-0119-field-mixin-strategy.md docs/decisions/ADR-0141-field-mixin-strategy.md
git mv docs/decisions/ADR-0120-detection-package-structure.md docs/decisions/ADR-0142-detection-package-structure.md
git mv docs/decisions/ADR-0120-detection-result-caching.md docs/decisions/ADR-0143-detection-result-caching.md
git mv docs/decisions/ADR-0120-healingresult-consolidation.md docs/decisions/ADR-0144-healingresult-consolidation.md
```

### Phase 2: Internal Title Updates
Update the `# ADR-XXXX:` header in each renamed file to match new number.

**Files Requiring Title Updates**:
1. ADR-0135-processholder-detection.md
2. ADR-0136-process-field-architecture.md
3. ADR-0137-post-commit-invalidation-hook.md
4. ADR-0138-tier2-pattern-enhancement.md
5. ADR-0139-self-healing-design.md
6. ADR-0140-dataframe-task-cache-integration.md
7. ADR-0141-field-mixin-strategy.md
8. ADR-0142-detection-package-structure.md
9. ADR-0143-detection-result-caching.md
10. ADR-0144-healingresult-consolidation.md

### Phase 3: Cross-Reference Updates
Search and update references to old ADR numbers in:
- `docs/` directory (all markdown files)
- `.claude/` directory
- `README.md`
- Any other markdown files in project root

**Search Patterns**:
- `ADR-0115` (excluding parallel-section-fetch-strategy)
- `ADR-0116` (excluding batch-cache-population-pattern)
- `ADR-0117` (excluding accessor-descriptor-unification)
- `ADR-0118` (excluding rejection-multi-level-cache)
- `ADR-0119` (excluding client-cache-integration-pattern)
- `ADR-0120` (excluding batch-cache-population-on-bulk-fetch)

---

## Validation Checklist

- [ ] All 10 files renamed using `git mv`
- [ ] All internal ADR titles updated to match new numbers
- [ ] No duplicate ADR numbers remain
- [ ] All cross-references updated
- [ ] No broken references to old ADR numbers
- [ ] Git history preserved through git mv

---

## Post-Execution Verification

**Commands**:
```bash
# Verify no duplicates remain
cd docs/decisions && ls -1 ADR-*.md | sed 's/ADR-\([0-9]*\)-.*/\1/' | sort | uniq -d

# Should return empty

# Verify new numbers exist
ls -1 docs/decisions/ADR-013[5-9]-*.md docs/decisions/ADR-014[0-4]-*.md

# Should show all 10 renamed files

# Search for orphaned references to old numbers
grep -r "ADR-0115-processholder" docs/ .claude/ README.md
grep -r "ADR-0116-process-field" docs/ .claude/ README.md
# ... (repeat for each renamed ADR)

# All searches should return no results
```

---

## Status

**Specification Status**: APPROVED
**Execution Status**: COMPLETE
**Completion Date**: 2024-12-24

---

## Validation Results

### Phase 1: File Renaming ✓ COMPLETE
All 10 files successfully renamed using `git mv`:
```bash
✓ ADR-0115-processholder-detection.md → ADR-0135-processholder-detection.md
✓ ADR-0116-process-field-architecture.md → ADR-0136-process-field-architecture.md
✓ ADR-0117-post-commit-invalidation-hook.md → ADR-0137-post-commit-invalidation-hook.md
✓ ADR-0117-tier2-pattern-enhancement.md → ADR-0138-tier2-pattern-enhancement.md
✓ ADR-0118-self-healing-design.md → ADR-0139-self-healing-design.md
✓ ADR-0119-dataframe-task-cache-integration.md → ADR-0140-dataframe-task-cache-integration.md
✓ ADR-0119-field-mixin-strategy.md → ADR-0141-field-mixin-strategy.md
✓ ADR-0120-detection-package-structure.md → ADR-0142-detection-package-structure.md
✓ ADR-0120-detection-result-caching.md → ADR-0143-detection-result-caching.md
✓ ADR-0120-healingresult-consolidation.md → ADR-0144-healingresult-consolidation.md
```

**Verification**: No duplicate ADR numbers remain in `/docs/decisions/`
**Verification**: All 10 renamed files exist in new number range (ADR-0135 to ADR-0144)

### Phase 2: Internal Title Updates ✓ COMPLETE
All 10 renamed ADRs have internal `# ADR-XXXX:` titles updated to match new numbers.

### Phase 3: Cross-Reference Updates ✓ COMPLETE
Updated references in 12 documentation files:
1. `/docs/CONTENT-BRIEFS-2025-12-24.md` - ADR-0137 reference
2. `/docs/runbooks/RUNBOOK-cache-troubleshooting.md` - ADR-0137 reference
3. `/docs/analysis/GAP-ANALYSIS-REMEDIATION-MARATHON.md` - ADR-0138, ADR-0142, ADR-0144 references
4. `/docs/reports/REPORT-CACHE-OPTIMIZATION-P2.md` - ADR-0140 reference
5. `/docs/analysis/INTEGRATION-CACHE-PERF-P1-LEARNINGS.md` - ADR-0140 reference
6. `/docs/design/TDD-CACHE-OPTIMIZATION-P2.md` - ADR-0140 reference
7. `/docs/design/TDD-CACHE-PERF-FETCH-PATH.md` - ADR-0140 reference
8. `/docs/planning/sprints/TDD-SPRINT-1-PATTERN-COMPLETION.md` - ADR-0141 reference
9. `/docs/testing/VP-SPRINT-1-PATTERN-COMPLETION.md` - ADR-0141 references (2 locations)
10. `/docs/planning/sprints/TDD-SPRINT-3-DETECTION-DECOMPOSITION.md` - ADR-0142, ADR-0138 references
11. `/docs/design/TDD-CACHE-PERF-DETECTION.md` - ADR-0143 reference
12. `/docs/INDEX.md` - Updated Caching topic with new numbers, added new topics (Detection, Process Architecture, Self-Healing, Field Patterns), updated document allocation table

**Verification**: No orphaned references to old ADR filenames found (excluding audit documentation)

### Impact Summary
- **Files Renamed**: 10
- **Cross-References Updated**: 20+ references across 12 files
- **Git History**: Preserved through `git mv`
- **Duplicate Numbers**: Eliminated (0 duplicates remain)
- **Next Available ADR**: ADR-0145
- **Documentation Integrity**: Verified

---

## Post-Execution Notes

**Success Criteria Met**:
- ✓ All duplicate ADR numbers resolved
- ✓ Git history preserved through proper git mv
- ✓ All internal titles updated
- ✓ All cross-references updated
- ✓ No broken links remain
- ✓ INDEX.md updated with new topic categories
- ✓ Document allocation table updated

**Breaking Changes**: None - All ADR content unchanged, only numbering corrected

**Follow-Up Actions**: None required - Resolution complete
