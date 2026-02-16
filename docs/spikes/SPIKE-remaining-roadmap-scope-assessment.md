# SPIKE: Remaining Roadmap Scope Assessment

**Date**: 2026-02-15
**Timebox**: 30 minutes
**Decision**: What remains from the deferred-work-roadmap? Which initiatives should be cancelled, adjusted, or executed?

---

## Question

The Deep Hygiene Sprint roadmap defined 7 initiatives across 4 waves. Waves 1-2 (I1, I4-S1, I2, I4-S2/S3) are complete. What is the actual remaining scope for Waves 3-4 (I3, I5, I6, I7)?

---

## Findings

### I3: Storage + Connection Wiring — SCOPE DRAMATICALLY REDUCED

| Part | Roadmap Assumption | Actual State |
|------|-------------------|--------------|
| R09: Storage Protocol | Orphaned `dataframes/storage.py` | **ALREADY WIRED** — 6 active consumers |
| R14: S3 Consolidation | 3 overlapping implementations, ~2000 LOC reduction | **ALREADY COMPLETE** — only `S3DataFrameStorage` exists |
| R08: Connection Lifecycle | Orphaned `cache/connections/` | **NOT IMPLEMENTED** — directory does not exist |

**Net scope**: Only R08 (connection lifecycle) remains. The TDD exists (`docs/design/TDD-connection-lifecycle-management.md`), test stubs exist in `tests/unit/cache/test_backends_with_manager.py`, and backend providers (`redis.py`, `s3.py`) already accept optional `connection_manager` params. Estimated: **1 sprint** (not 2).

### I5: API Main Decomposition — CANCEL

| Metric | Roadmap Assumption | Actual State |
|--------|-------------------|--------------|
| `api/main.py` LOC | 1,466 (god module) | **197** (routing shell) |
| Inline endpoints | Multiple groups to extract | **Zero** — all in dedicated route modules |
| Route modules | Partial extraction | **17 files** fully extracted |
| Backward-compat shims | 4 retained | **0** — all 4 shim files deleted |

**Verdict**: I5-S1/S2/S3 targets are **ALREADY ACHIEVED**. The <250 LOC target is met at 197. All 4 backward-compat shims (`cache/factory.py`, `cache/mutation_invalidator.py`, `cache/schema_providers.py`, `cache/tiered.py`) no longer exist. **Cancel all 3 sprints.**

### I6: API Error Unification — SCOPE ACCURATE

| Metric | Count |
|--------|-------|
| Centralized error handlers | 10 (in `api/errors.py`, 420 LOC) |
| HTTPException direct usage | 95 sites across 12 route files |
| Routes with highest count | `tasks.py` (15), `query.py` (13), `entity_write.py` (12) |

**Net scope**: Infrastructure exists and is solid. Work is to **audit 95 HTTPException sites** for consistency, document the convention (when HTTPException vs centralized handler), and migrate any inconsistencies. Estimated: **1 sprint** (unchanged).

### I7: Mechanical Cleanup — SCOPE DRAMATICALLY REDUCED

| Item | Roadmap Assumption | Actual State |
|------|-------------------|--------------|
| TODO markers | 47+ | **2** (both in `extractors/unit.py`, blocked by OQ-4/OQ-5) |
| Orphaned modules (R07) | 7 modules | **0** — all wired (EntityService, TaskService, SectionService all imported by API layer) |
| Bot PAT boilerplate (R12) | 12 sites | **4 call sites**, centralized function exists |
| Bare-except sites | 158 unannotated | **0 unannotated** — all 116 `except Exception` sites annotated |
| Backward-compat shims (B07) | 4 to delete | **0** — already deleted |

**Remaining R-items**:
- R02 (FreshnessStamp serialization): Verify if still needed
- R03 (S3 config dataclass): May be resolved with R14
- R04 (Schema lookup ceremony, 15+ sites): Mechanical extraction
- R05 (Workspace GID retrieval, 5+ sites): Config pattern
- R06 (Duplicate CircuitBreakerOpenError): Exception cleanup

**Net scope**: Much smaller than estimated. **0.5 sprint** (not 1).

---

## Revised Roadmap

### Original vs Revised

| Wave | Initiatives | Original Sprints | Revised Sprints | Status |
|------|------------|-----------------|-----------------|--------|
| Wave 1 | I1, I4-S1 | 2 | — | COMPLETE |
| Wave 2 | I2, I4-S2/S3 | 3-4 | — | COMPLETE |
| Wave 3 | I3, I5-S1 | 3 | **1** | I5 cancelled, I3 reduced to R08 only |
| Wave 4 | I5-S2/S3, I6, I7 | 3-4 | **1.5** | I5 cancelled, I7 reduced |
| **Total** | | **11-13** | **2.5** | |

### Recommended Execution Order

**Sprint N (Wave 3 revised)**: I6 — API Error Unification
- Audit 95 HTTPException sites
- Document convention (ADR)
- Migrate inconsistencies
- 1 sprint

**Sprint N+1 (Wave 4 revised)**: I7 (reduced) + I3-R08 (optional)
- R04: Schema lookup ceremony extraction (15+ sites)
- R05: Workspace GID retrieval consolidation (5+ sites)
- R06: CircuitBreakerOpenError consolidation
- R02/R03: Verify and close
- R08 (optional): Connection lifecycle wiring — consider deferring unless cache connection pooling is a production issue
- 0.5-1 sprint

### Cancelled Items

| Item | Reason |
|------|--------|
| I5-S1 | `api/main.py` already 197 LOC |
| I5-S2 | All endpoints already extracted |
| I5-S3 | All shims already deleted |
| I3-R09 | `storage.py` already wired (6 consumers) |
| I3-R14 | S3 consolidation already complete |
| I7 bulk | TODOs (2 not 47), orphans (0 not 7), shims (0 not 4) |

---

## Recommendation

**Total remaining effort: 2.5 sprints** (down from original 10-14 estimate).

Prior sessions (I1, I4-S1, I2, I4-S2/S3) consumed the bulk of the roadmap AND organically completed work planned for later waves (main.py decomposition, storage wiring, S3 consolidation, shim deletion, service layer wiring). The roadmap's scope estimates were written before these organic completions occurred.

The **highest-ROI remaining work** is I6 (error unification) — it's the only initiative where infrastructure exists but convention is inconsistent. R08 (connection lifecycle) is the only greenfield work remaining and should be assessed against production needs before committing.

---

## Follow-up Actions

1. Update roadmap status with revised scope
2. Decide on I6 execution (next sprint)
3. Decide on R08 (connection lifecycle) — defer or execute?
4. Close all I5 items as SUPERSEDED
5. Close I3-R09, I3-R14 as ALREADY COMPLETE
