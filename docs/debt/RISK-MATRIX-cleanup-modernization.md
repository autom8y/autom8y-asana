# Risk Matrix: Cleanup & Modernization Sprint

**Assessor**: risk-assessor agent
**Date**: 2026-02-18
**Input**: LEDGER-cleanup-modernization.md (35 items, 6 categories)
**Methodology**: Blast Radius (1-5) x Likelihood (1-5) = Risk Score (max 25), divided by effort for composite priority

---

## Executive Briefing

The three highest-risk items in this ledger are all pattern inconsistencies that directly impede daily development: the error handling divergence across API routes (D-004, score 16), the DI wiring inconsistency between `Request` and `RequestId` patterns (D-005, score 16), and the v1/v2 query router split that compounds both problems (D-012, score 16). These are not theoretical risks -- they actively create confusion for any developer touching the API layer and propagate inconsistency with every new route added.

Immediate action should focus on the pattern unification cluster (D-004, D-005, D-006, D-008, D-012) as a coordinated batch. These five items share dependencies and collectively eliminate ~600 LOC while establishing a single canonical pattern for error handling and dependency injection. The query router merge (D-012) is the linchpin: it absorbs D-001 (dead v1 handler) and enables D-004/D-005/D-006 cleanup in the merged file.

LOC reduction potential by tier: Critical items address ~970 LOC (pattern unification + query merge + dead code). High-priority items address ~1,640 LOC (deprecated deps, aliases, entity_write/resolver DI migration, pipeline convergence prep). Medium items address ~4,400 LOC (god object decomposition targets, broad exception audit, pipeline duplication). Low-priority items address ~350 LOC (cosmetic and architecture-level concerns). Total addressable: ~7,360 LOC.

Key sequencing dependency: D-005 (DI migration to RequestId) should precede D-006 (narrowing raise_api_error signature), which should precede D-004 (error handling consolidation). D-012 (query router merge) can proceed in parallel with D-005 and absorbs D-001 automatically. The god object decompositions (D-030, D-032) and pipeline convergence (D-022, D-033) are large-effort items that should be deferred to dedicated sprints -- they will not be abandoned in a greenfield migration and represent transferable architectural patterns worth getting right.

---

## Priority Tiers Summary

| Tier | Score Range | Count | Items |
|------|------------|-------|-------|
| **Critical** | 15-25 | 6 | D-004, D-005, D-012, D-033, D-022, D-029 |
| **High** | 10-14 | 8 | D-007, D-008, D-018, D-019, D-011, D-020, D-031, D-026 |
| **Medium** | 5-9 | 12 | D-006, D-010, D-003, D-017, D-021, D-023, D-024, D-030, D-032, D-034, D-027, D-014 |
| **Low** | 1-4 | 9 | D-001, D-002, D-009, D-013, D-015, D-016, D-025, D-028, D-035 |

---

## Prioritized Risk Matrix

All 35 items sorted by Risk Score (descending), then by Effort (ascending) within equal scores.

| Rank | ID | Title | Blast | Likelihood | Risk Score | Effort | Tier | Rationale |
|------|-----|-------|-------|-----------|------------|--------|------|-----------|
| 1 | D-004 | Error handling pattern divergence (v1 vs v2) | 4 | 4 | 16 | M | Critical | Cross-cutting concern across 4+ route files. Every new route must choose a pattern -- wrong choice propagates debt. Stakeholder top pain point (pattern inconsistency). |
| 2 | D-005 | DI wiring -- Request object vs RequestId dependency | 4 | 4 | 16 | M | Critical | Same 4 route files affected. The union overload in raise_api_error silently enables inconsistency. Blocks D-006 cleanup. Active developer confusion during route development. |
| 3 | D-012 | v1/v2 query routers -- consolidation target | 4 | 4 | 16 | M | Critical | [PRIORITY] flagged. Two files for one feature is the most visible pattern inconsistency. Absorbs D-001. Stakeholder explicitly decided to merge and strip "v2" naming. High daily-development friction. |
| 4 | D-033 | Pipeline creation logic duplicated | 4 | 4 | 16 | XL | Critical | Highest-ROI WS4 finding (DRY-001, ROI 13.5). Identical 7-step pipeline in two files. Changes must be replicated or behavior silently diverges -- seeding already diverged. |
| 5 | D-022 | Dual-path automation architecture | 4 | 4 | 16 | XL | Critical | Root cause of D-033 and D-023. Two separate orchestration systems for the same domain. Lifecycle is canonical but automation persists. Architecture-level debt that transfers to greenfield. |
| 6 | D-029 | Pre-existing test failures | 3 | 5 | 15 | M | Critical | Already causing issues -- carried forward through multiple sprints unresolved. Erodes trust in the test suite. Every CI run includes known failures, masking potential regressions. |
| 7 | D-007 | Deprecated DI dependencies still exported | 3 | 4 | 12 | M | High | [PRIORITY] flagged. Two deprecated functions exported in __all__ with duplicated validation logic. New developers may use deprecated path. ~90 LOC of redundant code. |
| 8 | D-008 | Webhooks route uses raw HTTPException | 3 | 4 | 12 | S | High | [PRIORITY] flagged. Webhook errors lack consistent error format (no request_id). Pattern inconsistency in a production-facing endpoint. Small fix, high signal. |
| 9 | D-018 | entity_write.py inline request.app.state access | 3 | 4 | 12 | M | High | Bypasses DI system entirely. Duplicates get_bot_pat() logic. Any DI refactor (D-005) must also touch this file or leave it inconsistent. |
| 10 | D-019 | resolver.py no DI, uses Request directly | 3 | 4 | 12 | M | High | Same DI bypass as D-018. Own entity type validation with broad exception catches. Must be addressed alongside D-005 for pattern consistency. |
| 11 | D-011 | Direct os.environ/os.getenv bypassing Settings | 3 | 4 | 12 | L | High | 20+ call sites undermining Settings as single source of truth. Makes configuration hard to test. Spread across clients, lambda handlers, cache, dataframes, models. |
| 12 | D-020 | Side-effect import for business model bootstrap | 4 | 3 | 12 | L | High | Import-time side effect creates fragile import ordering. Any from models.business import X triggers full registration cascade. Tests depend on this implicit behavior. |
| 13 | D-031 | Retry callback boilerplate repeated 5x | 3 | 4 | 12 | L | High | Near-identical callback definitions in 5 endpoint methods. Changes to retry behavior require 5 edits. Subsumed by D-030 decomposition but independently addressable via callback factory. |
| 14 | D-026 | Tests targeting dead/deprecated v1 query code | 3 | 4 | 12 | M | High | 34 test cases testing dead or deprecated code paths. Tests pass only by bypassing production router registration. Masks coverage gaps on v2 handler. |
| 15 | D-006 | raise_api_error overloaded Request or str parameter | 3 | 3 | 9 | S | Medium | Enables D-005 inconsistency. Once D-005 is resolved, this narrows to str-only. Small change, blocked by D-005. |
| 16 | D-010 | Config access -- module-level get_settings() calls | 3 | 3 | 9 | S | Medium | 4 client files evaluate settings at import time. Stale values persist if env vars change after import. Breaks test overrides. |
| 17 | D-003 | Legacy preload module (active fallback) | 3 | 3 | 9 | XL | Medium | Confirmed active degraded-mode fallback. 613 LOC, complexity 23, 12 bare-except sites. Cannot delete -- must modernize or accept. High effort for uncertain return. |
| 18 | D-017 | Deprecated aliases and backward-compatibility shims | 3 | 3 | 9 | L | Medium | ~150 LOC of accumulated shims across 11+ locations. Each adds import surface and cognitive load. Requires consumer audit before removal. |
| 19 | D-021 | Barrel __init__.py files with non-trivial logic | 3 | 3 | 9 | L | Medium | Four barrels exceed 100 LOC with load-bearing logic. WS7 investigation found most are actually clean re-exports. models/business barrel is the primary concern (subsumed by D-020). |
| 20 | D-023 | Cross-module coupling -- lifecycle imports from automation internals | 3 | 3 | 9 | S | Medium | Private symbol imports across package boundaries. WS6 RF-006 addressed this by promoting to public API. Low remaining risk if WS6 was executed. |
| 21 | D-024 | Bidirectional dependency -- resolver <-> universal_strategy | 3 | 3 | 9 | M | Medium | Inline imports break circular dependency at runtime but indicate structural coupling. Functional but architecturally suspect. |
| 22 | D-030 | God object -- DataServiceClient (2,175 LOC, 49 methods) | 4 | 2 | 8 | XL | Medium | Largest class in codebase. Mixes 6+ concerns. Three C901 violations. But it works -- the risk is maintenance burden and blast radius of change, not imminent failure. Transfers to greenfield as pattern to avoid. |
| 23 | D-032 | God object -- SaveSession (1,853 LOC, 58 methods) | 4 | 2 | 8 | XL | Medium | Second-largest class. Already delegates to collaborators -- orchestration logic itself is the bloat. Same profile as D-030: maintenance burden, not imminent failure. |
| 24 | D-034 | Broad exception catches (136 instances) | 3 | 2 | 6 | XL | Medium | Many are intentionally annotated (BROAD-CATCH: boundary/degrade). Needs per-site audit to separate intentional from accidental. The 12 bare-excepts in legacy preload (D-003) are the highest-risk subset. |
| 25 | D-027 | Heavy mock usage in API tests (540 sites) | 3 | 2 | 6 | XL | Medium | Makes tests brittle to refactoring. But does not cause failures on its own -- only becomes a problem when source code changes (which this sprint does). Risk materializes during pattern unification work. |
| 26 | D-014 | Deprecated PipelineAutoCompletionService wrapper | 2 | 3 | 6 | S | Medium | Single consumer (engine.py). Ignores parameters. Easy to remove once engine.py imports CompletionService directly. 35 LOC. |
| 27 | D-001 | Dead v1 query_rows handler | 2 | 2 | 4 | S | Low | Already dead code (unreachable after QW-6 fix). Absorbed by D-012 query router merge. No independent urgency. 130 LOC removal. |
| 28 | D-002 | v1 query endpoint sunset -- full router removal | 3 | 1 | 3 | M | Low | Sunset date 2026-06-01. Cannot remove until then. Track and schedule removal at sunset. 369 LOC. |
| 29 | D-009 | Logging import source inconsistency | 1 | 3 | 3 | S | Low | Cosmetic -- both paths resolve to same logger. 5 files affected. Quick fix but minimal impact. |
| 30 | D-013 | type:ignore suppression density in clients | 2 | 2 | 4 | XL | Low | Flagged as potentially intentional design. The @async_method decorator pattern requires these suppressions. Reducing them needs a mypy plugin or different codegen. Not actionable without architectural change. |
| 31 | D-015 | Stub implementations in UnitExtractor | 2 | 2 | 4 | M | Low | Two methods always return None. If downstream expects values, silent data quality issue. But "deferred pending team input" suggests this is known and accepted. |
| 32 | D-016 | Commented-out metric definition imports | 1 | 1 | 1 | S | Low | 2 lines of commented code. Minimal cognitive load. Remove or implement when metrics scope expands. |
| 33 | D-025 | Inline deferred imports for circular avoidance (12+ instances) | 2 | 2 | 4 | XL | Low | Valid Python pattern. Density indicates structural issues but each instance works correctly. Architecture-level fix (interface extraction) is disproportionate effort. |
| 34 | D-028 | Largest test file -- test_client.py at 4,848 LOC | 2 | 1 | 2 | XL | Low | Mirrors source complexity. Follows D-030 decomposition -- not independently actionable. |
| 35 | D-035 | Direct os.environ access in Lambda handlers | 2 | 2 | 4 | S | Low | Subset of D-011 scoped to Lambda handlers. Lambda handlers have different lifecycle than API server. Settings integration is less critical here. |

---

## Quick Wins List

Items with Risk Score >= 5 AND Effort = S or M. These deliver high value for low cost and should be prioritized for immediate sprint inclusion.

| ID | Title | Risk Score | Effort | Why It Is a Quick Win |
|----|-------|-----------|--------|----------------------|
| D-008 | Webhooks raw HTTPException | 12 | S | 3 raises to refactor. Pattern fix + consistent error format in under 1 hour. |
| D-006 | raise_api_error overloaded parameter | 9 | S | ~10 LOC change once D-005 is done. Narrows function signature to str-only. |
| D-010 | Module-level get_settings() calls | 9 | S | 4 files, 8 lines. Move TTL reads inside functions. Fixes test override issue. |
| D-023 | Cross-module coupling (private imports) | 9 | S | Promote 2 private functions to public API. Rename only, no logic change. May already be addressed by WS6 RF-006. |
| D-014 | Deprecated PipelineAutoCompletionService | 6 | S | Remove wrapper class, update 1 import in engine.py. 35 LOC removed. |
| D-004 | Error handling pattern divergence | 16 | M | 4 route files. Migrate to dict-mapping pattern. ~200 LOC consolidation. High impact on stakeholder pain point #1. |
| D-005 | DI wiring inconsistency | 16 | M | 3 route files. Migrate to RequestId dependency. ~60 LOC of signature changes. Enables D-006. |
| D-012 | v1/v2 query router consolidation | 16 | M | Merge 2 files into 1. Absorbs D-001. ~370 LOC net reduction. Stakeholder-mandated. |
| D-029 | Pre-existing test failures | 15 | M | 2 test files with known assertion failures. Fix or quarantine. Restores CI signal integrity. |
| D-007 | Deprecated DI dependencies exported | 12 | M | Remove 2 deprecated functions + duplicated validation. ~90 LOC. Audit consumers first. |
| D-018 | entity_write.py inline app.state access | 12 | M | Migrate to Depends pattern. ~40 LOC refactor. Aligns with D-005. |
| D-019 | resolver.py no DI | 12 | M | Migrate to EntityServiceDep + RequestId. ~50 LOC. Aligns with D-005. |
| D-026 | Tests targeting dead v1 query code | 12 | M | Migrate 34 tests to v2 handler or delete. Unblocks accurate coverage reporting. |
| D-024 | Bidirectional resolver <-> strategy dependency | 9 | M | Extract shared interface. ~20 LOC. Structural improvement. |

---

## Dependency Map

### Cluster 1: Pattern Unification (Critical Path)

```
D-005 (DI: RequestId migration)
  |
  +---> D-006 (narrow raise_api_error to str-only)
  |       |
  |       +---> D-004 (error handling consolidation)
  |
  +---> D-018 (entity_write.py DI migration)
  |
  +---> D-019 (resolver.py DI migration)

D-012 (query router merge)
  |
  +---> D-001 (absorbed: dead v1 handler removed during merge)
  |
  +---> D-026 (test migration: tests retargeted to merged router)
  |
  +---> D-002 (future: full v1 removal at sunset 2026-06-01)

D-007 (deprecated DI deps removal)
  |
  +---> requires consumer audit (may be used by D-018, D-019 routes)

D-008 (webhooks HTTPException fix)
  |
  +---> independent, can proceed in parallel
```

**Recommended sequence**: D-005 -> D-018/D-019 (parallel) -> D-006 -> D-004. D-012 can proceed independently in parallel with D-005. D-008 is fully independent.

### Cluster 2: Pipeline Convergence (Architectural)

```
D-023 (extract shared functions from automation/seeding.py)
  |
  +---> D-033 (extract shared creation engine)
          |
          +---> D-022 (consolidate dual-path architecture)
```

**Note**: WS6 (RF-004 through RF-007) already planned this sequence. If WS6 has not been executed, these items represent the next major architectural work package.

### Cluster 3: Configuration Consolidation

```
D-010 (module-level get_settings() calls)
  |
  +---> independent, no blockers

D-011 (os.environ bypassing Settings)
  |
  +---> D-035 (Lambda handler subset of D-011)
```

D-010 and D-011 are independent of each other but address the same root cause (inconsistent config access). D-035 is a strict subset of D-011.

### Cluster 4: God Object Decomposition (Deferred)

```
D-030 (DataServiceClient decomposition)
  |
  +---> D-031 (retry callback factory, can be done first as prep)
  |
  +---> D-028 (test file restructuring follows source decomposition)

D-032 (SaveSession decomposition)
  |
  +---> independent of D-030
```

These items have XL effort and should be scheduled as dedicated sprints, not batched with pattern unification work.

### Cluster 5: Test Integrity

```
D-029 (pre-existing test failures)
  |
  +---> independent, blocks nothing but erodes CI trust

D-026 (tests targeting dead v1 code)
  |
  +---> depends on D-012 (query router merge)

D-027 (heavy mock usage)
  |
  +---> ongoing concern, materializes during D-004/D-005/D-012 work
```

### Independent Items (No Dependencies)

| ID | Title | Notes |
|----|-------|-------|
| D-003 | Legacy preload (active fallback) | Deferred -- confirmed not dead code |
| D-009 | Logging import inconsistency | Cosmetic, 5 files |
| D-013 | type:ignore density in clients | Intentional design trade-off |
| D-014 | Deprecated PipelineAutoCompletionService | Single consumer, easy removal |
| D-015 | UnitExtractor stub implementations | Awaiting team input |
| D-016 | Commented-out metric imports | 2 lines |
| D-017 | Deprecated aliases (accumulated) | Requires consumer audit |
| D-020 | Side-effect import for bootstrap | Deferred per WS7 RF-009 |
| D-021 | Barrel __init__.py files | Mostly clean per WS7 RF-008 investigation |
| D-025 | Inline deferred imports | Valid pattern, architecture-level |
| D-034 | Broad exception catches | Needs per-site audit |

---

## Risk Clusters and Batching Recommendations

### Batch 1: Pattern Unification Sprint (Critical, ~2-3 days)

**Items**: D-004, D-005, D-006, D-007, D-008, D-012, D-018, D-019
**Combined Risk Score**: 105 (sum)
**Combined Effort**: ~3 days (M+M+S+M+S+M+M+M)
**LOC Reduction**: ~600-800
**Stakeholder Alignment**: Directly addresses pain point #1 (pattern inconsistency) and pain point #2 (code bloat)

This batch establishes a single canonical pattern for error handling and DI across all API routes. It is the highest-value work package in the ledger.

### Batch 2: Dead Code and Quick Cleanup (~1 day)

**Items**: D-001 (absorbed by D-012), D-014, D-016, D-010, D-009
**Combined Risk Score**: 19
**Combined Effort**: ~4 hours (S+S+S+S+S)
**LOC Reduction**: ~180

Low-risk, high-confidence removals and fixes. Good warm-up or cool-down work.

### Batch 3: Test Integrity (~1-2 days)

**Items**: D-026, D-029
**Combined Risk Score**: 27
**Combined Effort**: ~1-2 days (M+M)
**LOC Reduction**: ~500 (test LOC)

Restores CI signal integrity and removes tests targeting dead code. D-026 depends on D-012 completing first.

### Batch 4: Configuration Consolidation (~1 day)

**Items**: D-010 (if not done in Batch 2), D-011, D-035
**Combined Risk Score**: 16
**Combined Effort**: ~1 day (S+L+S, but D-035 is subset of D-011)
**LOC Reduction**: ~40

Unifies config access through Settings model. Improves testability.

### Batch 5: Pipeline Convergence (Deferred Sprint, ~5-8 days)

**Items**: D-022, D-023, D-033
**Combined Risk Score**: 34
**Combined Effort**: XL (dedicated sprint)
**LOC Reduction**: ~900-1,500

Highest-ROI WS4 finding. Requires careful extraction of shared creation primitives. WS6 plan (RF-004 through RF-007) provides the blueprint.

### Batch 6: God Object Decomposition (Deferred Sprint, ~5-10 days)

**Items**: D-030, D-031, D-032, D-028
**Combined Risk Score**: 30
**Combined Effort**: XL (dedicated sprint)
**LOC Reduction**: refactor, not reduction

Structural improvement. Does not reduce LOC but dramatically improves maintainability. Worth doing right; not worth rushing.

### Deferred / Track Only

**Items**: D-002, D-003, D-013, D-015, D-017, D-020, D-021, D-024, D-025, D-027, D-034
**Rationale**: Sunset-gated (D-002), confirmed active fallback (D-003), intentional design (D-013), awaiting input (D-015), requires consumer audit (D-017), deferred per WS7 (D-020, D-021), architecture-level (D-024, D-025, D-027, D-034).

---

## Scoring Rationale by Item

### D-001: Dead v1 query_rows handler
- **Blast**: 2 -- Single file, contained to query.py. No downstream consumers since it is unreachable.
- **Likelihood**: 2 -- Cannot cause runtime issues (dead code), but adds confusion when reading the file.
- **Effort**: S -- Delete 130 lines. Absorbed by D-012 merge.
- **Note**: No independent urgency. Will be removed as part of D-012.

### D-002: v1 query endpoint sunset
- **Blast**: 3 -- External callers may depend on the deprecated endpoint. Affects API contract.
- **Likelihood**: 1 -- Sunset date is 2026-06-01. Cannot act until then. External consumer audit incomplete.
- **Effort**: M -- Full file removal plus model cleanup, but straightforward once sunset arrives.
- **Note**: Calendar-gated. Score reflects that action is blocked, not that risk is low.

### D-003: Legacy preload module (active fallback)
- **Blast**: 3 -- Preload affects all dataframe consumers. Degraded mode is a system-wide behavior.
- **Likelihood**: 3 -- S3 outages do occur. The fallback path is exercised in production. 12 bare-except sites are risky.
- **Effort**: XL -- 613 LOC, complexity 23. Modernization requires replacing degraded-mode strategy.
- **Note**: Confirmed not dead code. Cannot delete. Effort to modernize is high relative to return.

### D-004: Error handling pattern divergence [PRIORITY]
- **Blast**: 4 -- Cross-cutting concern. 4+ route files affected. Every new route must choose a pattern.
- **Likelihood**: 4 -- Already causing confusion during development. New routes copy whichever file they look at first.
- **Effort**: M -- Migrate 4 files to dict-mapping pattern. ~200 LOC consolidation. Well-understood target state.
- **Note**: Stakeholder pain point #1 (pattern inconsistency). High confidence in scoring.

### D-005: DI wiring -- Request vs RequestId [PRIORITY]
- **Blast**: 4 -- Same cross-cutting scope as D-004. DI pattern affects every route's function signature.
- **Likelihood**: 4 -- Already causing inconsistency. The union overload in raise_api_error masks the problem.
- **Effort**: M -- 3 route files, ~60 LOC signature changes. Mechanical migration.
- **Note**: Blocks D-006. Must be done before error handling consolidation can complete.

### D-006: raise_api_error overloaded parameter
- **Blast**: 3 -- Single file (errors.py), but consumed by all routes. Narrowing signature improves type safety.
- **Likelihood**: 3 -- The union type actively enables D-005 inconsistency. Moderate ongoing harm.
- **Effort**: S -- ~10 LOC change. Remove Request branch, accept str only.
- **Note**: Blocked by D-005 completion. Quick win once dependency is resolved.

### D-007: Deprecated DI dependencies still exported [PRIORITY]
- **Blast**: 3 -- Exported in __all__, available to all route consumers. New code may adopt deprecated path.
- **Likelihood**: 4 -- Deprecated functions are discoverable via IDE autocomplete and __all__. Likely to be used by mistake.
- **Effort**: M -- Remove 2 functions (~90 LOC), audit consumers, update __all__. Moderate but bounded.
- **Note**: Duplicated validation logic in get_asana_pat() is a maintenance trap.

### D-008: Webhooks raw HTTPException [PRIORITY]
- **Blast**: 3 -- Production-facing webhook endpoint. Inconsistent error format visible to external callers.
- **Likelihood**: 4 -- Every webhook verification failure returns non-standard error format. Frequent execution path.
- **Effort**: S -- 3 raises to refactor. Under 1 hour. Well-defined target pattern (raise_api_error).
- **Note**: Easiest PRIORITY item. High signal, minimal risk.

### D-009: Logging import source inconsistency
- **Blast**: 1 -- Cosmetic. Both paths resolve to the same logger implementation.
- **Likelihood**: 3 -- Creates confusion about canonical import but does not cause bugs.
- **Effort**: S -- 5 import changes. Trivial.
- **Note**: Lowest blast radius in the ledger. Fix opportunistically.

### D-010: Module-level get_settings() calls
- **Blast**: 3 -- 4 client files with stale config values. Affects cache TTL behavior across clients.
- **Likelihood**: 3 -- Breaks test overrides. Settings evaluated at import time persist even if env changes.
- **Effort**: S -- 4 files, 8 lines. Move reads inside functions. No logic change.
- **Note**: Quick win for test reliability improvement.

### D-011: Direct os.environ bypassing Settings
- **Blast**: 3 -- 20+ call sites across the codebase. Undermines Settings as single source of truth.
- **Likelihood**: 4 -- Active friction during testing. Must set env vars instead of overriding Settings.
- **Effort**: L -- 20+ sites across 11+ files. Some require adding new fields to Settings model.
- **Note**: Significant scope. Worth doing but not quick. D-035 is a strict subset.

### D-012: v1/v2 query router consolidation [PRIORITY]
- **Blast**: 4 -- Two files for one feature. Most visible pattern inconsistency in the codebase.
- **Likelihood**: 4 -- Active daily-development friction. Stakeholder explicitly mandated merge.
- **Effort**: M -- Merge 2 files, adopt v2 patterns, preserve deprecated endpoint. ~370 LOC net reduction.
- **Note**: Linchpin item. Absorbs D-001 and enables D-026 test cleanup.

### D-013: type:ignore density in clients
- **Blast**: 2 -- Contained to clients/ directory. Does not affect runtime behavior.
- **Likelihood**: 2 -- Known trade-off for @async_method decorator pattern. Will not cause new issues.
- **Effort**: XL -- Requires mypy plugin or different codegen approach. Architecture-level change.
- **Note**: Flagged as potentially intentional. Scoring reflects low actionability. Track for awareness.

### D-014: Deprecated PipelineAutoCompletionService
- **Blast**: 2 -- Single consumer (engine.py). Wrapper ignores parameters. Isolated impact.
- **Likelihood**: 3 -- Parameters being silently ignored could mask bugs. Moderate latent risk.
- **Effort**: S -- Remove class (~35 LOC), update 1 import. Under 30 minutes.
- **Note**: Clean, safe removal. No consumer audit needed beyond engine.py.

### D-015: UnitExtractor stub implementations
- **Blast**: 2 -- Two methods always returning None. Affects data quality in specific columns.
- **Likelihood**: 2 -- Marked "deferred pending team input." Known and accepted state.
- **Effort**: M -- Either implement (requires domain knowledge) or remove columns from schema.
- **Note**: Requires stakeholder input on whether these columns matter. Cannot score higher without that context.

### D-016: Commented-out metric imports
- **Blast**: 1 -- 2 lines of commented code in a single file. No runtime impact.
- **Likelihood**: 1 -- Will not cause any issues. Purely cosmetic.
- **Effort**: S -- Delete 2 lines. Under 5 minutes.
- **Note**: Lowest risk item in the ledger. Remove if touching the file for other reasons.

### D-017: Deprecated aliases and backward-compatibility shims
- **Blast**: 3 -- ~150 LOC across 11+ locations. Adds import surface and cognitive load.
- **Likelihood**: 3 -- Shims work correctly. Risk is maintenance burden and confusion, not failure.
- **Effort**: L -- Requires consumer audit across the codebase and potentially external consumers.
- **Note**: WS5 RF-003 already removed ReconciliationsHolder (one of these). Remaining shims need per-item audit.

### D-018: entity_write.py inline request.app.state access
- **Blast**: 3 -- Bypasses DI system. Duplicates auth logic. Affects entity write operations.
- **Likelihood**: 4 -- Any DI refactor must also touch this file. Pattern divergence actively maintained.
- **Effort**: M -- Migrate to Depends pattern. ~40 LOC. Well-defined target.
- **Note**: Should be batched with D-005 for consistency. Same pattern migration.

### D-019: resolver.py no DI
- **Blast**: 3 -- Own entity type validation with broad catches. Bypasses EntityServiceDep.
- **Likelihood**: 4 -- Same active inconsistency as D-018. Must be addressed alongside D-005.
- **Effort**: M -- Migrate to EntityServiceDep + RequestId. ~50 LOC.
- **Note**: Same rationale as D-018. Batch together.

### D-020: Side-effect import for business model bootstrap
- **Blast**: 4 -- Any import from models.business triggers full registration cascade. Import ordering is fragile.
- **Likelihood**: 3 -- Works correctly due to idempotency guard but creates hidden coupling. Tests depend on it.
- **Effort**: L -- Moving to explicit init requires auditing all entry points. WS7 RF-009 deferred this.
- **Note**: Deferred per WS7 analysis. Risk-to-reward ratio unfavorable. Idempotency guard is sufficient safety net.

### D-021: Barrel __init__.py with non-trivial logic
- **Blast**: 3 -- 4 barrel files with load-bearing logic. Affects import behavior.
- **Likelihood**: 3 -- WS7 RF-008 found most barrels are actually clean re-exports. models/business barrel is the exception.
- **Effort**: L -- Refactoring barrels touches import chains across the codebase.
- **Note**: Partially addressed by WS7 investigation. Remaining risk concentrated in models/business (subsumed by D-020).

### D-022: Dual-path automation architecture
- **Blast**: 4 -- Two separate orchestration systems. Architecture-level divergence.
- **Likelihood**: 4 -- Active source of confusion. Which path handles what? Seeding already diverged.
- **Effort**: XL -- Architectural consolidation. WS6 plan (RF-005, RF-007) provides blueprint but is multi-day effort.
- **Note**: Root cause of D-033. Highest strategic importance but highest effort. Worth dedicated sprint.

### D-023: Cross-module coupling (lifecycle imports automation internals)
- **Blast**: 3 -- Private symbol imports across package boundaries. Violates underscore prefix contract.
- **Likelihood**: 3 -- Works at runtime but creates tight coupling. Any refactor of automation/seeding.py can break lifecycle.
- **Effort**: S -- Promote to public API (rename, no logic change). WS6 RF-006 already planned this.
- **Note**: May already be resolved if WS6 was executed (commit af09b74 references RF-012 but not RF-006).

### D-024: Bidirectional dependency (resolver <-> universal_strategy)
- **Blast**: 3 -- Inline imports break circularity at runtime. Structural coupling in services layer.
- **Likelihood**: 3 -- Functional but any refactor of either file risks breaking the other.
- **Effort**: M -- Extract shared interface or protocol. ~20 LOC.
- **Note**: Valid Python pattern but indicates dependency graph issues. Medium priority.

### D-025: Inline deferred imports (12+ instances)
- **Blast**: 2 -- Each instance works correctly. Pattern is valid Python.
- **Likelihood**: 2 -- Density indicates structural issues but no imminent risk of failure.
- **Effort**: XL -- Architecture-level fix (interface extraction, dependency inversion). Disproportionate effort.
- **Note**: Observed, not actionable in current sprint. WS7 RF-011 reached same conclusion.

### D-026: Tests targeting dead v1 query code
- **Blast**: 3 -- 34 test cases providing false coverage signal. Masks gaps on v2 handler.
- **Likelihood**: 4 -- Every test run exercises dead code paths. Coverage reports are misleading.
- **Effort**: M -- Migrate tests to v2 handler or delete. Depends on D-012 completing.
- **Note**: Stakeholder pain point #3 (test brittleness). High value once D-012 clears the path.

### D-027: Heavy mock usage in API tests (540 sites)
- **Blast**: 3 -- Makes tests brittle to refactoring. 540 mock sites across API test files.
- **Likelihood**: 2 -- Does not cause issues on its own. Risk materializes during pattern unification work (D-004, D-005, D-012).
- **Effort**: XL -- Test architecture issue. Gradual migration from mocks to integration patterns.
- **Note**: Ongoing concern. Not addressable in a single sprint. Factor mock breakage into effort estimates for Cluster 1.

### D-028: Largest test file (test_client.py, 4,848 LOC)
- **Blast**: 2 -- Mirrors D-030 source complexity. Test file is a symptom, not a cause.
- **Likelihood**: 1 -- Will not cause issues unless D-030 decomposition begins.
- **Effort**: XL -- Follows D-030 decomposition. Not independently actionable.
- **Note**: Dependent on D-030. Cannot be addressed before source is decomposed.

### D-029: Pre-existing test failures
- **Blast**: 3 -- Erodes trust in test suite. Known failures mask potential regressions in CI.
- **Likelihood**: 5 -- Already causing issues. Carried forward through multiple sprints. Every CI run includes noise.
- **Effort**: M -- Investigate 2 test files. Either fix checkpoint assertions or quarantine with skip markers.
- **Note**: Score 15 puts this at Critical threshold. Highest likelihood rating in the ledger.

### D-030: God object -- DataServiceClient
- **Blast**: 4 -- Sole HTTP gateway to data service. 49 methods, 2,175 LOC. Extreme blast radius of change.
- **Likelihood**: 2 -- Works correctly. Risk is maintenance burden, not failure. Has survived multiple sprints.
- **Effort**: XL -- Multi-day decomposition. Callback factory (D-031) + endpoint extraction + parameter objects.
- **Note**: Deferred per WS5-7 plan. Too large for a shared sprint. Dedicated workstream needed.

### D-031: Retry callback boilerplate repeated 5x
- **Blast**: 3 -- 5 endpoint methods with near-identical callbacks. Changes require 5 edits.
- **Likelihood**: 4 -- Any retry behavior change risks inconsistency across endpoints. Active maintenance trap.
- **Effort**: L -- Extract callback factory. Touches all 5 endpoint methods in DataServiceClient.
- **Note**: Can be done independently of full D-030 decomposition. Good prep work for eventual decomp.

### D-032: God object -- SaveSession
- **Blast**: 4 -- Transactional core of persistence layer. 58 methods, 1,853 LOC.
- **Likelihood**: 2 -- Works correctly. Already delegates to collaborators. Orchestration logic is the bloat.
- **Effort**: XL -- Phase-specific handler extraction. Multi-day effort.
- **Note**: Same profile as D-030. Deferred to dedicated sprint.

### D-033: Pipeline creation logic duplicated
- **Blast**: 4 -- Identical 7-step pipeline in 2 files. Changes must be replicated or behavior diverges.
- **Likelihood**: 4 -- Seeding has already diverged (FieldSeeder vs AutoCascadeSeeder). Active risk of further divergence.
- **Effort**: XL -- Extract shared creation engine. WS6 RF-004/RF-005 provide blueprint.
- **Note**: Highest-ROI WS4 finding (13.5). Scores Critical on risk but XL on effort. Worth dedicated sprint investment.

### D-034: Broad exception catches (136 instances)
- **Blast**: 3 -- System-wide. Some catches swallow actionable exceptions silently.
- **Likelihood**: 2 -- Many are intentionally annotated (BROAD-CATCH). Needs per-site triage.
- **Effort**: XL -- 136 sites require individual assessment. Cannot batch blindly.
- **Note**: The 12 bare-excepts in D-003 (legacy preload) are the highest-risk subset. Rest are lower urgency.

### D-035: Direct os.environ in Lambda handlers
- **Blast**: 2 -- Lambda handlers have different lifecycle than API server. Limited blast radius.
- **Likelihood**: 2 -- Works correctly for Lambda context. Settings integration is lower priority here.
- **Effort**: S -- 3 call sites across 3 files. Route through Settings or a Lambda-specific config.
- **Note**: Strict subset of D-011. Lower priority than the broader config consolidation.

---

## Assessment Assumptions

1. **WS5 execution status**: WS5 (RF-001 through RF-003) appears to have been executed based on commit history (27c0491, 5772928, fce83a0). These items are resolved in the WS4 baseline.

2. **WS6 execution status**: WS6 (RF-004 through RF-007) status is unclear. Commit af09b74 references RF-012 (annotation) but not RF-004-RF-007 (creation convergence). Scoring assumes WS6 convergence work has NOT been executed, meaning D-022, D-023, D-033 remain fully open.

3. **Greenfield migration context**: Items scored with awareness that patterns (not just code) transfer to greenfield. God object decomposition (D-030, D-032) and pipeline convergence (D-022, D-033) teach transferable patterns. Cosmetic debt (D-009, D-016) does not transfer.

4. **Risk appetite "aggressive"**: Interpreted as "willing to accept breaking internal changes to achieve pattern unification" but NOT "willing to accept production incidents." Breaking changes to internal module structure are acceptable; breaking changes to the v1 API endpoint before sunset are not.

5. **Effort estimates**: S < 1 hour, M = 1-4 hours, L = 4-16 hours, XL = 16+ hours. These assume a developer familiar with the codebase. First-time contributors would need ~50% more time.

6. **D-013 and D-034 intentionality**: Both items contain a mix of intentional and accidental instances. D-013 is scored low (intentional @async_method trade-off). D-034 is scored medium (136 instances warrant audit even if many are intentional).

---

## Handoff Checklist

- [x] All 35 ledger items scored across three dimensions (Blast, Likelihood, Effort)
- [x] Risk scores calculated and items sorted by descending score
- [x] Priority tiers assigned: 6 Critical, 8 High, 12 Medium, 9 Low
- [x] Quick wins identified: 14 items with score >= 5 and effort S or M
- [x] Risk clusters identified: 6 batches with sequencing recommendations
- [x] Dependency map documenting item relationships and execution order
- [x] Executive briefing summarizing top risks and recommended actions
- [x] Assessment assumptions documented
- [x] Stakeholder priorities reflected in scoring (pattern > bloat > tests)
- [x] Greenfield context factored into priority decisions
- [x] PRIORITY-flagged items given extra scrutiny (D-004, D-005, D-007, D-008, D-012)
- [x] Intentional-debt items (D-013, D-034) scored accordingly
