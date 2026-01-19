---
schema_version: "1.0"
sprint_id: sprint-unified-cache-20260116
session_id: session-20260116-075931-80329c81
name: "Unified Progressive DataFrame Cache Architecture"
goal: "Delete S3Tier, make everything use SectionPersistence via ProgressiveTier"
status: IN_PROGRESS
created_at: "2026-01-16T07:59:31Z"
complexity: SERVICE
current_task: TASK-001
---

# Sprint: Unified Progressive DataFrame Cache Architecture

## Sprint Goal

Unify two parallel S3 caching systems into a single progressive cache architecture with resume capability.

## Problem Statement

Two parallel S3 caching systems evolved accidentally, creating duplication and bugs:

1. **SectionPersistence** (`dataframes/{project_gid}/`) - The good one
   - Resume capability, incremental refresh, manifest tracking
   - Used by ProgressiveProjectBuilder during warming

2. **S3Tier** (`asana-cache/dataframes/{entity}:{project}.parquet`) - The redundant one
   - Simple flat file, no resume, TTL-based staleness
   - Used by DataFrameCache for query reads

**The Bug**: Self-refresh writes to location #1, but queries read from location #2. Cache is stale at location #2 → CACHE_NOT_WARMED.

## Target Architecture

```
SINGLE STORAGE (Progressive):
  dataframes/{entity_type}/{project_gid}/
  ├── manifest.json       # Build state, schema version
  ├── dataframe.parquet   # Final DataFrame
  ├── watermark.json      # Freshness tracking
  ├── index.json          # GidLookupIndex
  └── sections/           # Resume artifacts

CACHE LAYERS:
  L1: MemoryTier (keep as-is)
  L2: ProgressiveTier (replaces S3Tier, reads from above structure)
```

## Tasks

### TASK-001: Requirements (PRD)
- **Agent**: requirements-analyst
- **Status**: PENDING
- **Produces**: PRD-unified-progressive-cache.md
- **Scope**: Define success criteria, non-goals, acceptance criteria for cache unification

### TASK-002: Technical Design (TDD)
- **Agent**: architect
- **Status**: PENDING
- **Depends**: TASK-001
- **Produces**: TDD-unified-progressive-cache.md
- **Scope**: ProgressiveTier interface, SectionPersistence enhancements, migration path

### TASK-003: Implementation
- **Agent**: principal-engineer
- **Status**: PENDING
- **Depends**: TASK-002
- **Produces**: Code changes across 7 files
- **Scope**:
  - CREATE: cache/dataframe/tiers/progressive.py
  - DELETE: cache/dataframe/tiers/s3.py
  - UPDATE: cache/dataframe/factory.py (use ProgressiveTier)
  - UPDATE: cache/dataframe_cache.py (watermark-based validation)
  - SIMPLIFY: cache/dataframe/warmer.py (remove redundant put_async)
  - FIX: services/universal_strategy.py (unified read/write path)
  - ENHANCE: dataframes/section_persistence.py (add get for cache reads)

### TASK-004: QA Validation
- **Agent**: qa-adversary
- **Status**: PENDING
- **Depends**: TASK-003
- **Produces**: QA approval report
- **Scope**:
  - /v1/query/offer returns data
  - Single S3 location verification
  - Resume capability test
  - All existing tests green

## Key Files

| File | Action |
|------|--------|
| cache/dataframe/tiers/s3.py | DELETE (replace with progressive.py) |
| cache/dataframe/tiers/progressive.py | CREATE (new ProgressiveTier) |
| cache/dataframe/factory.py | UPDATE (use ProgressiveTier) |
| cache/dataframe_cache.py | UPDATE (simplify validation, watermark-based) |
| cache/dataframe/warmer.py | SIMPLIFY (remove redundant put_async) |
| services/universal_strategy.py | FIX (unified read/write path) |
| dataframes/section_persistence.py | ENHANCE (add get for cache reads) |

## Success Criteria

1. `/v1/query/offer` returns data (currently broken)
2. Single S3 location: `dataframes/{entity}/{project}/`
3. Cache warmer and self-refresh use same storage
4. Resume capability works (kill Lambda mid-build, restart completes)
5. All tests green

## Non-Goals (Freedom to Break)

- Backwards compatibility with old S3 location
- Migration scripts for old cached data (delete it, Lambda rebuilds)
- Preserving S3Tier interface exactly
- Supporting both storage formats simultaneously

## Questions for Architect

1. Should key structure be `{entity}/{project}/` or keep `{project}/` and add entity to manifest?
2. Watermark staleness threshold - configurable or hardcoded 24h?
3. Should ProgressiveTier lazy-load index.json or always load with DataFrame?

## Dependencies

None - greenfield refactoring.

## Sprint Log

- 2026-01-16T07:59:31Z: Sprint created
- 2026-01-16T07:59:31Z: TASK-001 (PRD) queued for requirements-analyst
