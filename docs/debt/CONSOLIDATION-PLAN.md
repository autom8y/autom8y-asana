# Documentation Consolidation Plan

**Target**: 50-75% volume reduction in `/docs`
**Status**: Draft for Review
**Date**: 2025-12-25

---

## Executive Summary

Current documentation spans 400 markdown files totaling 6.7 MB. Through strategic consolidation, archival, and deletion, we can reduce this to approximately 100-150 active files (~2.0 MB), achieving **70% volume reduction** while improving findability.

**Key Insight**: The majority of documentation bloat comes from:
1. **149 ADRs** that should be rolled into topic summaries
2. **69 archived files** that can be deleted (already archived)
3. **11 validation plans** that are post-ship artifacts
4. **22 test plans** that duplicate validation coverage
5. **One-time analysis artifacts** that served their purpose

---

## Current State Metrics

### By Directory

| Directory | Files | Size | Category | Retention Priority |
|-----------|-------|------|----------|-------------------|
| **decisions/** | 149 | 1.36 MB | ADRs | Consolidate to summaries |
| **archive/** | 69 | 1.50 MB | Already archived | Delete |
| **requirements/** | 32 | 812 KB | PRDs | Keep, some consolidation |
| **design/** | 39 | 1.20 MB | TDDs | Keep, some consolidation |
| **testing/** | 22 | 323 KB | Test Plans | Consolidate to validation |
| **validation/** | 11 | 185 KB | Post-ship artifacts | Archive most |
| **reference/** | 18 | 280 KB | Active reference | Keep all |
| **audits/** | 8 | 216 KB | One-time artifacts | Archive |
| **debt/** | 6 | 152 KB | Active debt tracking | Keep all |
| **guides/** | 8 | 104 KB | User-facing docs | Keep all |
| **analysis/** | 4 | 88 KB | One-time artifacts | Archive |
| **planning/** | 4 | 56 KB | Sprint artifacts | Archive completed |
| **initiatives/** | 4 | 68 KB | PROMPT-0 files | Archive completed |
| **Other dirs** | 26 | ~400 KB | Mixed | Varies |

### Totals

- **Current**: 400 files, 6.7 MB
- **Target**: 100-150 files, 2.0 MB
- **Reduction**: 250-300 files, 4.7 MB (70%)

---

## Consolidation Strategy

### Priority 1: ADR Topic Summaries (HIGH IMPACT)

**Current**: 149 individual ADR files
**Target**: 12-15 topic summary files + index
**Reduction**: ~135 files, 1.2 MB (88%)

#### Grouping by Topic

1. **ADR-CACHE-SUMMARY.md** (13 ADRs → 1 file)
   - ADR-0016: cache-protocol-extension
   - ADR-0026: two-tier-cache-architecture
   - ADR-0032: cache-granularity
   - ADR-0116: batch-cache-population-pattern
   - ADR-0118: rejection-multi-level-cache
   - ADR-0119: client-cache-integration-pattern
   - ADR-0120: batch-cache-population-on-bulk-fetch
   - ADR-0123: cache-provider-selection
   - ADR-0124: client-cache-pattern
   - ADR-0129: stories-client-cache-wiring
   - ADR-0130: cache-population-location
   - ADR-0131: gid-enumeration-cache-strategy
   - ADR-0140: dataframe-task-cache-integration

2. **ADR-CUSTOM-FIELDS-SUMMARY.md** (10 ADRs → 1 file)
   - ADR-0030: custom-field-typing
   - ADR-0034: dynamic-custom-field-resolution
   - ADR-0051: custom-field-type-safety
   - ADR-0054: cascading-custom-fields
   - ADR-0056: custom-field-api-format
   - ADR-0062: custom-field-accessor-enhancement
   - ADR-0067: custom-field-snapshot-detection
   - ADR-0074: unified-custom-field-tracking
   - ADR-0081: custom-field-descriptor-pattern
   - ADR-0112: custom-field-gid-resolution

3. **ADR-SAVESESSION-SUMMARY.md** (6 ADRs → 1 file)
   - ADR-0038: save-concurrency-model
   - ADR-0053: composite-savesession-support
   - ADR-0061: implicit-savesession-lifecycle
   - ADR-0065: savesession-error-exception
   - ADR-0121: savesession-decomposition-strategy
   - ADR-0125: savesession-invalidation

4. **ADR-DETECTION-SUMMARY.md** (9 ADRs → 1 file)
   - ADR-0019: staleness-detection-algorithm
   - ADR-0043: unsupported-operation-detection
   - ADR-0064: dirty-detection-strategy
   - ADR-0067: custom-field-snapshot-detection
   - ADR-0068: type-detection-strategy
   - ADR-0094: detection-fallback-chain
   - ADR-0135: processholder-detection
   - ADR-0142: detection-package-structure
   - ADR-0143: detection-result-caching

5. **ADR-ARCHITECTURE-SUMMARY.md** (~25 ADRs → 1 file)
   - Protocol patterns (0001, 0004, 0007, 0016)
   - Client architecture (0002, 0003, 0004)
   - Pydantic config (0005, SDK-005)
   - Unit of Work (0035)
   - Thread safety (0024)
   - Migration strategy (0025)
   - Schema enforcement (0033)
   - Change tracking (0036)
   - Event hooks (0041)
   - Observability (0007, 0085, 0086)

6. **ADR-DATA-PATTERNS-SUMMARY.md** (~20 ADRs → 1 file)
   - NameGid pattern (0078)
   - Descriptors (0077, 0081, 0117)
   - Lazy loading (0050)
   - Bidirectional caching (0052)
   - Resolution patterns (0060, 0071, 0072, 0073)
   - Registry patterns (0080, 0093, 0105, 0108)
   - Dataframe layer (0021, 0027, 0028)

7. **ADR-API-INTEGRATION-SUMMARY.md** (~15 ADRs → 1 file)
   - Batch API (0015, 0018)
   - Partial failure (0040, 0070)
   - Error handling (0090, 0091, 0127)
   - Webhooks (0008)
   - Attachments (0009)
   - Rate limiting (0022)
   - Graceful degradation (0127)

8. **ADR-BUSINESS-MODEL-SUMMARY.md** (~12 ADRs → 1 file)
   - Process patterns (0096, 0097)
   - Seeding (0099, 0105, 0106)
   - Detection integration (0094, 0095)
   - Loop prevention (0104)
   - Template discovery (0106)
   - Dual membership (0098)
   - State transitions (0100)

9. **ADR-OPERATIONS-SUMMARY.md** (~15 ADRs → 1 file)
   - Action patterns (0059, 0122, 0107)
   - Positioning (0047)
   - Parent/subtask (0029, 0057, 0110, 0111)
   - Duplication (0110)
   - Tag operations (0045, 0066)
   - Project operations (0115)
   - Section handling (0113)

10. **ADR-DEMO-SUMMARY.md** (3 ADRs → 1 file)
    - ADR-0088: demo-state-capture
    - ADR-0090: demo-error-handling

11. **ADR-EDGE-CASES-SUMMARY.md** (~10 ADRs → 1 file)
    - Bug scope decisions (0058)
    - CRUD base class rejection (0092)
    - Backward compat (0114)
    - Validation timing (0047, 0049)
    - Extra params (0044)
    - Unsupported operations (0043)

12. **ADR-PERFORMANCE-SUMMARY.md** (~10 ADRs → 1 file)
    - Async decorators (0025)
    - Parallel fetching (0115)
    - Batching patterns (0116, 0120, 0132)
    - Hydration (0069, 0128)

**Approach**:
- Each summary consolidates related ADRs into narrative sections
- Format: Topic overview → Key decisions → Rationale → Cross-references
- Archive individual ADRs to `docs/archive/2025-12-adrs/`
- Maintain `decisions/INDEX.md` with summary → ADR mapping

---

### Priority 2: Archive Deletion (HIGH IMPACT, ZERO RISK)

**Current**: 69 files in `docs/archive/`
**Target**: 0 files (move to external archive or delete)
**Reduction**: 69 files, 1.5 MB (100%)

**Rationale**: Archive directory already serves archival purpose. No need to keep these in active repo.

#### Actions

1. **Delete `docs/archive/2025-12-cache-superseded/`** (4 files)
   - These were superseded by recent cache work
   - Already have git history

2. **Delete `docs/archive/2025-12-completed-initiatives/`** (13 files)
   - Completed initiatives, captured in git history
   - No ongoing reference value

3. **Delete `docs/archive/rejected/`** (varies)
   - Rejected proposals, git history sufficient

**Alternative**: If retention required for compliance, move to separate git repo or external storage.

---

### Priority 3: Validation Plan Consolidation (MEDIUM IMPACT)

**Current**: 11 validation plans in `docs/validation/`
**Target**: 2-3 summary files
**Reduction**: 8-9 files, 150 KB (80%)

#### Grouping

1. **VALIDATION-CACHE-PERFORMANCE.md** (consolidates 5 files)
   - VP-CACHE-PERF-DETECTION.md
   - VP-CACHE-PERF-DETECTION-INTEGRATION.md
   - VP-CACHE-PERF-FETCH-PATH.md
   - VALIDATION-CACHE-PERF-HYDRATION.md
   - INTEGRATION-CACHE-PERF-HYDRATION.md

2. **VALIDATION-CACHE-OPTIMIZATION.md** (consolidates 3 files)
   - VP-CACHE-OPTIMIZATION-P2.md
   - VP-CACHE-OPTIMIZATION-P3.md
   - VP-CACHE-LIGHTWEIGHT-STALENESS.md

3. **VALIDATION-CACHE-STORIES.md** (consolidates 2 files)
   - VAL-CACHE-PERF-STORIES.md
   - VAL-CACHE-PERF-STORIES-INTEGRATION.md

4. **Archive remaining**: VALIDATION-WATERMARK-CACHE.md (covered elsewhere)

**Format**: Each consolidated validation file follows template:
```markdown
# Validation Summary: [Topic]

## Scope
- [List of initiatives validated]

## Test Coverage
- [Aggregate coverage metrics]

## Results by Initiative
### [Initiative 1]
- Status: PASS/FAIL
- Key findings
- Reference: [link to original VP if needed]

### [Initiative 2]
...

## Cumulative Metrics
- Total tests: X
- Coverage: Y%
- Defects found: Z
```

---

### Priority 4: Test Plan Consolidation (MEDIUM IMPACT)

**Current**: 22 test plans in `docs/testing/`
**Target**: 8-10 files (consolidate VPs, keep TPs)
**Reduction**: 12-14 files, 200 KB (60%)

#### Strategy

**Keep Test Plans (TP-*.md)** - These are pre-implementation:
- TP-0001 through TP-0009 (feature-specific test plans)
- TP-AUTOMATION-LAYER.md
- TP-CUSTOM-FIELD-REMEDIATION.md
- TP-DETECTION.md

**Consolidate Validation Plans (VP-*.md)** - These are post-ship:
1. **VP-SPRINT-SUMMARY.md** (consolidates 5 files)
   - VP-SPRINT-1-PATTERN-COMPLETION.md
   - VP-SPRINT-3-DETECTION-DECOMPOSITION.md
   - VP-SPRINT-4-SAVESESSION-DECOMPOSITION.md
   - VP-SPRINT-5-CLEANUP.md

2. **VP-FEATURE-VALIDATION.md** (consolidates 5 files)
   - VP-CACHE-INTEGRATION.md
   - VP-PIPELINE-AUTOMATION-ENHANCEMENT.md
   - VP-SAVESESSION.md
   - VP-TECH-DEBT-REMEDIATION.md
   - VP-WORKSPACE-PROJECT-REGISTRY.md

**Archive**: testing/README.md can stay as index

---

### Priority 5: Analysis & Audit Archival (MEDIUM IMPACT)

**Current**: 12 files (analysis: 4, audits: 8)
**Target**: 0 active, all archived
**Reduction**: 12 files, 304 KB (100%)

#### Analysis Files → Archive

All 4 files in `docs/analysis/` are one-time artifacts:
- SECTION-HANDLING-ANALYSIS.md (architectural analysis, findings captured in ADRs)
- CUSTOM-FIELD-REALITY-AUDIT.md (audit complete, findings in ADRs)
- DETECTION-SYSTEM-ANALYSIS.md (analysis complete)
- ANALYSIS-PROCESS-ENTITIES.md (completed analysis)

**Action**: Move to `docs/archive/2025-12-analysis/`

#### Audit Files → Archive

6 of 8 audit files are completed artifacts:
- AUDIT-doc-synthesis.md (synthesis complete)
- MIGRATION-REPORT.md (migration complete)
- REVIEW-SIGNOFF.md (review complete)
- AUDIT-adr-quality-standardization.md (audit complete)
- TECH-WRITER-PROGRESS-REPORT-TASK-4.md (report delivered)
- ADR-QUALITY-CLOSEOUT.md (closeout complete)

**Keep in audits/** (active debt tracking):
- ADR-RENUMBERING-SPEC.md (may need reference)
- ADR-BACKFILL-PRIORITIES.md (ongoing priorities)

**Action**: Move 6 files to `docs/archive/2025-12-audits/`

---

### Priority 6: PRD/TDD Selective Consolidation (LOW-MEDIUM IMPACT)

**Current**: 71 files (PRDs: 32, TDDs: 39)
**Target**: 60 files
**Reduction**: 11 files, 300 KB (15%)

#### Approach

PRDs and TDDs are core design artifacts - consolidate only where clear redundancy exists.

**Consolidate**:
1. **PRD-SDK-EXTRACTION-FAMILY.md** (consolidates 3 PRDs)
   - PRD-0001-sdk-extraction.md
   - PRD-0007-sdk-functional-parity.md
   - PRD-0009-sdk-ga-readiness.md
   - PRD-0011-sdk-demonstration-suite.md

2. **TDD-SDK-EXTRACTION-FAMILY.md** (consolidates 3 TDDs)
   - TDD-0001-sdk-architecture.md
   - TDD-0012-sdk-functional-parity.md
   - TDD-0014-sdk-ga-readiness.md
   - TDD-0029-sdk-demo.md

3. **PRD-CUSTOM-FIELD-EVOLUTION.md** (consolidates 2 PRDs)
   - PRD-0016-custom-field-tracking.md
   - PRD-0019-custom-field-descriptors.md
   - PRD-0024-custom-field-remediation.md

4. **TDD-CUSTOM-FIELD-EVOLUTION.md** (consolidates 2 TDDs)
   - TDD-0020-custom-field-tracking.md
   - TDD-0023-custom-field-descriptors.md
   - TDD-CUSTOM-FIELD-REMEDIATION.md

**Keep separate** (distinct features):
- PRD/TDD pairs for major features (save orchestration, hierarchy hydration, detection, etc.)

---

### Priority 7: Initiatives & Planning Archival (LOW IMPACT)

**Current**: 8 files (initiatives: 4, planning: 4)
**Target**: 2 files
**Reduction**: 6 files, 80 KB (75%)

#### Initiatives

**Archive** (completed):
- PROMPT-0-TECH-DEBT-REMEDIATION.md (complete)
- PROMPT-0-SPRINT-5-CLEANUP.md (complete)
- SPRINT-5-ISSUE-MANIFEST.md (sprint complete)

**Keep**:
- initiatives/README.md (index)

#### Planning

**Archive**:
- All files in `docs/planning/` except README.md
- These are sprint artifacts with temporal value only

**Action**: Move to `docs/archive/2025-12-planning/`

---

## Consolidation Plan Execution Order

### Phase 1: Quick Wins (Week 1)

**Impact**: 80 files, 2.0 MB reduction

1. **Delete archive/** entirely (69 files, 1.5 MB)
2. **Archive analysis/** (4 files, 88 KB)
3. **Archive audits/** (6 files, 200 KB)
4. **Archive initiatives/** (3 files, 50 KB)
5. **Archive planning/** (varies, ~50 KB)

**Risk**: NONE - All files are completed artifacts

---

### Phase 2: Validation/Testing Consolidation (Week 2)

**Impact**: 30 files, 500 KB reduction

1. **Consolidate validation/** (11 → 3 files)
2. **Consolidate testing/VP-*.md** (10 → 2 files)

**Risk**: LOW - Post-ship artifacts, reference value low

---

### Phase 3: ADR Topic Summaries (Weeks 3-4)

**Impact**: 135 files, 1.2 MB reduction

1. Create 12 topic summary files
2. Archive individual ADRs to `docs/archive/2025-12-adrs/`
3. Update `decisions/INDEX.md`

**Risk**: MEDIUM - High-value reference content
**Mitigation**:
- Keep archive in repo initially
- Can restore individual ADRs if needed
- Git history preserves all content

---

### Phase 4: PRD/TDD Selective Consolidation (Week 5)

**Impact**: 11 files, 300 KB reduction

1. Consolidate SDK extraction family
2. Consolidate custom field evolution
3. Update cross-references

**Risk**: MEDIUM - Core design artifacts
**Mitigation**: Only consolidate clear families, preserve distinct features

---

## Post-Consolidation Structure

### Target Directory Layout

```
docs/
├── INDEX.md                           # Top-level navigation
├── decisions/
│   ├── INDEX.md                       # ADR index
│   ├── ADR-CACHE-SUMMARY.md           # Cache decisions
│   ├── ADR-CUSTOM-FIELDS-SUMMARY.md   # Custom field decisions
│   ├── ADR-SAVESESSION-SUMMARY.md     # SaveSession decisions
│   ├── ADR-DETECTION-SUMMARY.md       # Detection decisions
│   ├── ADR-ARCHITECTURE-SUMMARY.md    # Architectural patterns
│   ├── ADR-DATA-PATTERNS-SUMMARY.md   # Data patterns
│   ├── ADR-API-INTEGRATION-SUMMARY.md # API integration
│   ├── ADR-BUSINESS-MODEL-SUMMARY.md  # Business model
│   ├── ADR-OPERATIONS-SUMMARY.md      # Operations
│   ├── ADR-DEMO-SUMMARY.md            # Demo system
│   ├── ADR-EDGE-CASES-SUMMARY.md      # Edge cases
│   └── ADR-PERFORMANCE-SUMMARY.md     # Performance
├── design/
│   ├── README.md
│   ├── TDD-SDK-FAMILY.md              # Consolidated SDK TDDs
│   ├── TDD-CUSTOM-FIELD-FAMILY.md     # Consolidated CF TDDs
│   └── [~25 individual TDDs]          # Distinct features
├── requirements/
│   ├── README.md
│   ├── PRD-SDK-FAMILY.md              # Consolidated SDK PRDs
│   ├── PRD-CUSTOM-FIELD-FAMILY.md     # Consolidated CF PRDs
│   └── [~20 individual PRDs]          # Distinct features
├── reference/
│   └── [18 files - KEEP ALL]          # Active reference docs
├── guides/
│   └── [8 files - KEEP ALL]           # User-facing guides
├── debt/
│   ├── CONSOLIDATION-PLAN.md          # This file
│   └── [5 other debt docs]            # Active debt tracking
├── testing/
│   ├── README.md
│   ├── [12 TP files]                  # Test plans (keep)
│   └── VP-SUMMARY.md                  # Consolidated VPs
├── validation/
│   ├── VALIDATION-CACHE-PERFORMANCE.md
│   ├── VALIDATION-CACHE-OPTIMIZATION.md
│   └── VALIDATION-CACHE-STORIES.md
├── runbooks/
│   └── [6 files - KEEP ALL]           # Operational runbooks
├── architecture/
│   └── [2 files - KEEP ALL]           # Architecture docs
└── archive/
    ├── 2025-12-adrs/                  # Individual ADRs
    ├── 2025-12-analysis/              # Analysis artifacts
    ├── 2025-12-audits/                # Audit artifacts
    ├── 2025-12-planning/              # Sprint artifacts
    └── 2025-12-initiatives/           # Completed initiatives
```

### File Count Summary

| Directory | Before | After | Reduction |
|-----------|--------|-------|-----------|
| decisions/ | 149 | 13 | 91% |
| archive/ | 69 | 0 (deleted) | 100% |
| validation/ | 11 | 3 | 73% |
| testing/ | 22 | 13 | 41% |
| analysis/ | 4 | 0 | 100% |
| audits/ | 8 | 2 | 75% |
| design/ | 39 | 30 | 23% |
| requirements/ | 32 | 25 | 22% |
| initiatives/ | 4 | 1 | 75% |
| planning/ | 4 | 1 | 75% |
| **Other** | 58 | 58 | 0% |
| **TOTAL** | **400** | **146** | **64%** |

**Size**: 6.7 MB → 2.0 MB (70% reduction)

---

## Success Metrics

### Quantitative

- [ ] File count reduced from 400 to ~150 (62%)
- [ ] Total size reduced from 6.7 MB to ~2.0 MB (70%)
- [ ] ADRs consolidated from 149 to 13 topic summaries (91%)
- [ ] Archive directory deleted (100%)
- [ ] Validation plans consolidated from 11 to 3 (73%)

### Qualitative

- [ ] Engineers can find relevant ADR content in <2 minutes
- [ ] Topic summaries provide narrative context, not just lists
- [ ] Cross-references between docs remain intact
- [ ] No critical design information lost
- [ ] Git history preserves all original content

---

## Risk Mitigation

### Risk 1: Information Loss

**Mitigation**:
- Archive to `docs/archive/` first, don't delete
- Git history preserves all content
- Keep archive in repo for 1 release cycle
- Can restore individual files if needed

### Risk 2: Broken Cross-References

**Mitigation**:
- Run link checker before/after
- Update INDEX files
- Test common navigation paths

### Risk 3: Loss of Historical Context

**Mitigation**:
- Topic summaries include "Evolution" sections
- Archive maintains chronological record
- Git history with commit messages

---

## Tools & Automation

### Link Checker

```bash
# Find all internal markdown links
grep -r '\[.*\](.*\.md)' docs/ | grep -v archive

# Find broken links after consolidation
find docs -name "*.md" -exec grep -l "docs/decisions/ADR-[0-9]" {} \;
```

### Size Tracking

```bash
# Before consolidation
find docs -name "*.md" -exec wc -c {} + | tail -1

# After each phase
find docs -name "*.md" -exec wc -c {} + | tail -1
```

---

## Appendix A: ADR Summary Template

```markdown
# ADR Summary: [Topic]

## Overview

[1-2 paragraphs describing the topic area and why these decisions matter]

## Timeline & Evolution

| Date | Milestone | Key Decision |
|------|-----------|--------------|
| 2024-XX | [Context] | [What was decided] |
| 2024-YY | [Context] | [What changed] |

## Key Decisions

### [Decision Category 1]

**Context**: [Why this decision was needed]

**Decision**: [What was decided]

**Rationale**: [Why this approach]

**Alternatives Considered**: [What was rejected and why]

**Related ADRs**: ADR-XXXX, ADR-YYYY

---

### [Decision Category 2]
...

## Cross-Cutting Concerns

[How these decisions interact with other topics]

## Future Considerations

[Open questions, pending decisions, tech debt]

## Reference

### Original ADRs

- [ADR-XXXX](/docs/archive/2025-12-adrs/ADR-XXXX.md): [Title]
- [ADR-YYYY](/docs/archive/2025-12-adrs/ADR-YYYY.md): [Title]

### Related Documentation

- [Link to TDD]
- [Link to PRD]
- [Link to implementation]
```

---

## Appendix B: Validation Plan Summary Template

```markdown
# Validation Summary: [Topic]

## Scope

This summary consolidates validation results for:
- [Initiative 1] ([PRD link], [TDD link])
- [Initiative 2] ([PRD link], [TDD link])
- [Initiative 3] ([PRD link], [TDD link])

**Validation Period**: [Start] - [End]
**Total Test Coverage**: [X]%
**Total Tests**: [N]

---

## Results by Initiative

### [Initiative 1 Name]

**Status**: PASS / FAIL
**Test Coverage**: [X]%
**Tests**: [N passed] / [N total]
**Defects**: [Critical: X, High: Y, Medium: Z, Low: W]

**Key Findings**:
- [Finding 1]
- [Finding 2]

**Original Report**: [Link to archived VP if detailed reference needed]

---

### [Initiative 2 Name]
...

---

## Cumulative Metrics

| Metric | Value |
|--------|-------|
| Total Initiatives Validated | [N] |
| Total Tests Executed | [N] |
| Total Defects Found | [N] |
| Critical Defects | [N] |
| Test Coverage | [X]% |

## Cross-Initiative Patterns

[Common failure modes, recurring issues, systemic insights]

## Recommendations

[Post-validation recommendations for future work]

---

## Reference

### Original Validation Plans

- [VP-XXXX](/docs/archive/2025-12-validation/VP-XXXX.md): [Title]
- [VP-YYYY](/docs/archive/2025-12-validation/VP-YYYY.md): [Title]
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Information Architect | Initial consolidation plan |
