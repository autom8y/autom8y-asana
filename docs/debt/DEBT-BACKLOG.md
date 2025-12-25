# Technical Debt Backlog

> Deferred work items, validation NFRs, and future enhancements identified during sprints and validation.

**Last Updated**: 2025-12-25

---

## Overview

This document tracks technical debt and deferred work that does not require immediate action but should be addressed in future iterations. Items are organized by category and priority.

---

## Deferred Validation NFRs

### NFR-VAL-001: Test Coverage Below Target (Priority: Medium)

**Source**: [NFR-VALIDATION-REPORT.md](../.archive/validation/NFR-VALIDATION-REPORT.md)
**Status**: 79% coverage vs. 80% target (1% gap)
**Created**: 2025-12-08

**Modules requiring coverage improvements**:
- `clients/stories.py` (46%) - Story/comment operations
- `clients/teams.py` (40%) - Team operations
- `clients/tags.py` (47%) - Tag operations
- `clients/webhooks.py` (56%) - Webhook operations
- `clients/goals.py` (60%) - Goal operations
- `clients/portfolios.py` (62%) - Portfolio operations
- `transport/http.py` (47%) - HTTP transport layer
- `_defaults/cache.py` (39%) - Default cache implementation

**Recommendation**: Address incrementally during feature work on related modules.

---

### NFR-VAL-002: API Documentation Coverage (Priority: Medium)

**Source**: [NFR-VALIDATION-REPORT.md](../.archive/validation/NFR-VALIDATION-REPORT.md)
**Status**: 58.8% docstring coverage vs. 100% target
**Created**: 2025-12-08

**Gap**: Public API methods and classes lack comprehensive docstrings.

**Recommendation**: Add docstrings during refactoring or when modules are touched for feature work.

---

## Cache Performance Deferred Enhancements

### CACHE-001: Redis Batch Operations Sequential (Priority: Low)

**Source**: [VALIDATION-WATERMARK-CACHE.md](../validation/VALIDATION-WATERMARK-CACHE.md)
**Status**: Acceptable trade-off; optimize if needed
**Created**: 2025-12-23

**Description**: Redis `get_batch()` operations are sequential rather than pipelined. Per TDD decision, in-memory cache is sufficient for typical use. Pipelining can be added if performance profiling identifies this as a bottleneck.

**Recommendation**: Monitor in production; optimize only if profiling shows impact.

---

### CACHE-002: Performance Benchmark Test Missing (Priority: Low)

**Source**: [VP-CACHE-PERF-DETECTION.md](../validation/VP-CACHE-PERF-DETECTION.md)
**Status**: LOW-001 - Cannot verify <5ms target in CI
**Created**: 2025-12-23

**Description**: No explicit performance benchmark test for cache operations. Cannot verify <5ms target in CI environment.

**Recommendation**: Add benchmark test in future iteration with appropriate CI environment setup.

---

### CACHE-003: Version Comparison for Staleness (Priority: Low)

**Source**: [VP-CACHE-PERF-FETCH-PATH.md](../validation/VP-CACHE-PERF-FETCH-PATH.md)
**Status**: FR-LOOKUP-003 DEFERRED
**Created**: 2025-12-23

**Description**: Design allows version comparison for staleness detection (not implemented). Current modified-since approach is sufficient.

**Recommendation**: Add version comparison in follow-up if staleness becomes an issue.

---

### CACHE-004: Integration Test with Live API (Priority: Low)

**Source**: [VP-CACHE-OPTIMIZATION-P3.md](../validation/VP-CACHE-OPTIMIZATION-P3.md)
**Status**: NFR-TEST-002 DEFERRED - No live API available
**Created**: 2025-12-23

**Description**: Integration test requires live API access which is not available in CI.

**Recommendation**: Add integration test suite for manual validation with test Asana workspace.

---

### CACHE-005: Stories DataFrame Builder Integration (Priority: Low)

**Source**: [VAL-CACHE-PERF-STORIES-INTEGRATION.md](../validation/VAL-CACHE-PERF-STORIES-INTEGRATION.md)
**Status**: NOT STARTED - Future work
**Created**: 2025-12-23

**Description**: DataFrame builder integration for stories client is deferred. No blocking issues identified for future integration.

**Recommendation**: Consider adding integration test in future sprints when DataFrame builder sees active development.

---

### CACHE-006: Hydration Cache Optimization Phase 2 (Priority: Medium)

**Source**: [INTEGRATION-CACHE-PERF-HYDRATION.md](../validation/INTEGRATION-CACHE-PERF-HYDRATION.md)
**Status**: Future improvements identified
**Created**: 2025-12-23

**Description**: P3 Phase 2 hydration cache improvements include opt_fields normalization and batch hydration caching.

**Recommendation**: Prioritize if hydration becomes performance bottleneck.

---

## Documentation Debt

### DOC-001: Cross-Reference Broken Links (Priority: High)

**Source**: [VALIDATION-REPORT-Q4-CLEANUP-2025-12-24.md](../VALIDATION-REPORT-Q4-CLEANUP-2025-12-24.md)
**Status**: 22 files contain broken references to old paths
**Created**: 2025-12-24

**Description**: Legacy documents contain broken cross-references to:
- `initiatives/PROMPT-*` (files moved to `docs/initiatives/`)
- `planning/sprints/PRD-SPRINT-*` (files moved to `docs/planning/sprints/`)
- `planning/sprints/TDD-SPRINT-*` (files moved to `docs/planning/sprints/`)

**Recommendation**: Address in dedicated cleanup sprint or opportunistically during doc edits.

---

## Sprint Planning

### SPRINT-001: Pattern Completion Sprint Status (Priority: Low)

**Source**: [PRD-SPRINT-1-PATTERN-COMPLETION.md](../planning/sprints/PRD-SPRINT-1-PATTERN-COMPLETION.md)
**Status**: Completed 2025-12-25
**Created**: 2025-12-19

**Note**: Sprint marked as completed. Should be archived to `docs/.archive/planning/sprints/` after validation.

---

## Future Work

### Future Enhancements Tracked in Validation Reports

The following validation reports contain "Future Enhancements" sections with additional opportunities:

1. **VP-CACHE-OPTIMIZATION-P2.md** - Section "Future Enhancements"
2. **VP-CACHE-PERF-FETCH-PATH.md** - Section "Future Enhancements"
3. **VP-CACHE-PERF-DETECTION.md** - Section "Future Enhancements"

**Recommendation**: Review these sections when planning future cache optimization work.

---

## Backlog Management

### Adding Items

When deferring work during sprints or validation:

1. Add entry to appropriate section above
2. Include source document reference
3. Assign priority (High/Medium/Low)
4. Provide clear recommendation for when to address

### Retiring Items

When addressing deferred work:

1. Mark item as "Resolved" with date and PR/commit reference
2. Move to archive section at bottom of this document
3. Update source document if needed

---

## Resolved Items (Archive)

None yet.
