# CONSOLIDATION-CANDIDATES.md

> Documentation Consolidation Sprint - Phase 1 Audit Results
> Session: session-20251225-031118-2027af23
> Date: 2025-12-25

## Executive Summary

| Metric | Current | After Phase 1 | Target |
|--------|---------|---------------|--------|
| **Total Size** | 7.2M | 5.5M | ~3M |
| **Reduction** | - | 1.7M (24%) | 65% |
| **Files to Archive** | - | 61 | - |

## Phase 1 Quick Wins (Ready to Execute)

### Category 1: Cache PRDs (9 files, 204K)

All 9 superseded by `REF-cache-*.md` reference documents:

| File | Size | Superseded By |
|------|------|---------------|
| PRD-CACHE-INTEGRATION.md | 31K | REF-cache-architecture.md |
| PRD-CACHE-OPTIMIZATION-P2.md | 14K | REF-cache-invalidation.md |
| PRD-CACHE-OPTIMIZATION-P3.md | 20K | REF-cache-invalidation.md |
| PRD-CACHE-LIGHTWEIGHT-STALENESS.md | 27K | REF-cache-invalidation.md |
| PRD-CACHE-PERF-DETECTION.md | 18K | REF-cache-patterns.md |
| PRD-CACHE-PERF-FETCH-PATH.md | 16K | REF-cache-patterns.md |
| PRD-CACHE-PERF-HYDRATION.md | 18K | REF-cache-patterns.md |
| PRD-CACHE-PERF-STORIES.md | 25K | REF-cache-patterns.md |
| PRD-WATERMARK-CACHE.md | 20K | REF-cache-architecture.md |
| PRD-0002-intelligent-caching.md | 35K | REF-cache-architecture.md |

### Category 2: Cache TDDs (10 files, 348K)

All 10 superseded by same `REF-cache-*.md` reference documents:

| File | Size | Superseded By |
|------|------|---------------|
| TDD-CACHE-INTEGRATION.md | 51K | REF-cache-architecture.md |
| TDD-CACHE-OPTIMIZATION-P2.md | 38K | REF-cache-invalidation.md |
| TDD-CACHE-OPTIMIZATION-P3.md | 46K | REF-cache-invalidation.md |
| TDD-CACHE-LIGHTWEIGHT-STALENESS.md | 43K | REF-cache-invalidation.md |
| TDD-CACHE-PERF-DETECTION.md | 31K | REF-cache-patterns.md |
| TDD-CACHE-PERF-FETCH-PATH.md | 21K | REF-cache-patterns.md |
| TDD-CACHE-PERF-HYDRATION.md | 20K | REF-cache-patterns.md |
| TDD-CACHE-PERF-STORIES.md | 32K | REF-cache-patterns.md |
| TDD-CACHE-UTILIZATION.md | 19K | REF-cache-patterns.md |
| TDD-0008-intelligent-caching.md | 47K | REF-cache-architecture.md |

### Category 3: Discovery/Analysis Documents (18 files, 400K)

Completed discovery documents for finished initiatives:

- DISCOVERY-CACHE-INTEGRATION.md (~25K)
- DISCOVERY-CACHE-OPTIMIZATION-P2.md (~28K)
- DISCOVERY-CACHE-LIGHTWEIGHT-STALENESS.md (~30K)
- DISCOVERY-CACHE-PERF-DETECTION.md (~22K)
- DISCOVERY-CACHE-PERF-FETCH-PATH.md (~20K)
- DISCOVERY-TECH-DEBT-REMEDIATION.md (~24K)
- DISCOVERY-AUTOMATION-LAYER.md (~20K)
- DISCOVERY-PROCESS-PIPELINE.md (~22K)
- DISCOVERY-DETECTION-SYSTEM.md (~18K)
- DISCOVERY-SPRINT-1-PATTERN-COMPLETION.md (~16K)
- DISCOVERY-SPRINT-3-DETECTION.md (~18K)
- DISCOVERY-SAVESESSION-DECOMPOSITION.md (~20K)
- DISCOVERY-PIPELINE-AUTOMATION-ENHANCEMENT.md (~22K)
- GAP-ANALYSIS-CACHE-UTILIZATION.md (~15K)
- GAP-ANALYSIS-WORKSPACE-PROJECT-REGISTRY.md (~14K)
- GAP-ANALYSIS-REMEDIATION-MARATHON.md (~16K)
- SPIKE-SAVESESSION-DECOMPOSITION.md (~12K)
- INTEGRATION-CACHE-PERF-P1-LEARNINGS.md (~18K)

### Category 4: Cache-Specific Analysis (5 files, 71K)

- stories-cache-wiring-discovery.md (~14K)
- multi-level-cache-hierarchy-analysis.md (~15K)
- hydration-cache-opt-fields-analysis.md (~16K)
- watermark-cache-discovery.md (~12K)
- IMPACT-PROCESS-CLEANUP.md (~14K)

### Category 5: Completed Initiative Files (15 files, 380K)

PROMPT-0 files for completed work:

- PROMPT-0-CACHE-INTEGRATION.md (~28K)
- PROMPT-0-CACHE-LIGHTWEIGHT-STALENESS.md (~30K)
- PROMPT-0-CACHE-PERF-DETECTION.md (~24K)
- PROMPT-0-CACHE-PERF-HYDRATION.md (~26K)
- PROMPT-0-CACHE-PERF-STORIES.md (~28K)
- PROMPT-0-CACHE-UTILIZATION.md (~22K)
- PROMPT-0-SPRINT-1-PATTERN-COMPLETION.md (~20K)
- PROMPT-0-SPRINT-3-DETECTION-DECOMPOSITION.md (~22K)
- PROMPT-0-SPRINT-4-SAVESESSION-DECOMPOSITION.md (~24K)
- PROMPT-0-AUTOMATION-LAYER.md (~26K)
- PROMPT-0-PIPELINE-AUTOMATION-ENHANCEMENT.md (~28K)
- PROMPT-0-PROCESS-PIPELINE.md (~30K)
- PROMPT-0-PROCESS-CLEANUP.md (~20K)
- PROMPT-0-DOCS-EPOCH-RESET.md (~16K)
- PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md (~32K)

### Category 6: Rejected PRD/TDD Pairs (4 files, 78K)

- PRD-0021-async-method-generator.md (~16K) - Rejected approach
- PRD-0022-crud-base-class.md (~14K) - Explicit NO-GO
- TDD-0026-crud-base-class-evaluation.md (~18K) - NO-GO decision doc
- PRD-PROCESS-PIPELINE.md (partial) (~30K) - Never implemented

## Archive Structure

```
docs/archive/
├── 2025-12-cache-superseded/
│   ├── prds/           # 9 cache PRDs (204K)
│   ├── tdds/           # 10 cache TDDs (348K)
│   ├── analysis/       # 5 cache analysis docs (71K)
│   └── README.md
├── 2025-12-completed-initiatives/
│   ├── cache-performance/  # 6 PROMPT-0 cache docs
│   ├── sprints/           # 4 sprint PROMPT-0 docs
│   ├── discovery/         # 18 discovery documents (400K)
│   └── README.md
└── rejected/
    ├── PRD-0021-async-method-generator.md
    ├── PRD-0022-crud-base-class.md
    ├── TDD-0026-crud-base-class-evaluation.md
    └── README.md
```

## Phase 1 Summary

| Category | Files | Savings |
|----------|-------|---------|
| Cache PRDs | 9 | 204K |
| Cache TDDs | 10 | 348K |
| Discovery/Analysis | 18 | 400K |
| Cache Analysis | 5 | 71K |
| Completed Initiatives | 15 | 380K |
| Rejected PRD/TDD | 4 | 78K |
| **TOTAL** | **61** | **1.7M** |

## Gap to Target

- **After Phase 1**: 5.5M (24% reduction)
- **Target**: 3.0M (65% reduction)
- **Gap**: 2.5M additional reduction needed

### Additional Opportunities (Phase 2+)

1. **ADR Optimization**: ~500K (create indices, mark supersession chains)
2. **PRD/TDD Compression**: ~1.0M (merge related docs)
3. **Remaining Analysis**: ~56K
4. **Remaining Initiatives**: ~77K

## Validation Checklist

- [ ] All superseded docs have valid superseded_by links
- [ ] REF-cache-*.md contain consolidated information
- [ ] No broken links in active documentation
- [ ] Git history preserved (move, not delete)
- [ ] INDEX.md updated with archive locations

## Approval

**Status**: Pending approval for Phase 1 execution
**Next Step**: Execute archival of 61 files (1.7M)
