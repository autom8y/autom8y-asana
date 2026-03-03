# COMPAT-PURGE: Backward-Compatibility Shim & Legacy Accommodation Elimination

**Initiative**: Deep hygiene targeting backward-compat shims, legacy-caller accommodations,
orphaned migration paths, and hardcoded bespoke logic.
**Rite**: hygiene (code-smeller -> architect-enforcer -> janitor -> audit-lead)
**Codebase**: ~115K LOC async Python, FastAPI, ~10,500+ tests
**Premise**: There are no legacy callers. All consumers are internal and controlled.
Clean-break migrations are preferred over shim maintenance.

---

## 1. Objective

Eliminate backward-compatibility debt that exists to accommodate callers that no longer exist.
Prior initiatives (ASANA-HYGIENE, REM-ASANA-ARCH, REM-HYGIENE) modernized the codebase but
left shims, re-exports, dual-path logic, and "legacy alias" constructs in place out of caution.
That caution is no longer warranted: all consumers are controlled, internal code.

**Goal**: Remove every shim, re-export, dual-path conditional, and legacy alias that exists
solely for backward compatibility. Replace with direct imports, single code paths, and
canonical patterns.

**Non-goal**: Feature changes, new abstractions, or architectural redesign. This is pure
entropy reduction.

---

## 2. Phase 0: Pre-Flight (30 min)

Highest-leverage step per prior initiative learnings. Resolve before any workstream launches.

### 2.1 Consumer Audit for D-002

D-002 (deprecated POST /v1/query/{entity_type} handler) has a conditional-remove gate:
confirm zero traffic via CloudWatch query on `deprecated_query_endpoint_used` (30 days).

- **Action**: Run the CloudWatch query or confirm with ops that zero traffic exists.
- **If zero traffic**: D-002 is in-scope for this initiative (remove handler + 3 legacy models + test file).
- **If traffic exists**: D-002 stays deferred with consumer migration plan. Out of scope.
- **File**: `src/autom8_asana/api/routes/query.py:96-145` (models), `query.py:420-550` (handler)

### 2.2 Re-Export Consumer Census

Before removing any re-export, the code-smeller must verify no external package imports from the
shim location. Census method: `grep -r "from autom8_asana.<shim_module>" ../autom8y-*/src/` across
sibling repos (autom8y-data, autom8y-http, etc.). If any sibling repo imports from a shim location,
that re-export is out-of-scope unless the sibling is also updated in the same PR.

### 2.3 Test Baseline

Capture: `pytest --tb=no -q 2>&1 | tail -5` and record pass/fail/skip counts.
All workstreams must maintain green-to-green against this baseline.

---

## 3. Discovery Surface (What to Scan)

The code-smeller scans for these antipatterns. Do NOT assume hit counts -- discover the actual surface.

### 3.1 Backward-Compat Re-Exports

Files that exist solely to re-export symbols from their new canonical location:
- `from X import Y` followed by `__all__` containing `Y`, with a comment about "backward compat"
- Entire modules that are thin wrappers delegating to another module

**Scan patterns**:
```
"re-export.*backward"
"backward compat.*re-export"
"for backward compat"
"Re-exported from"
"preserved for backward"
"kept for backward"
"retained for compat"
```

**Known hotspot files** (verify, do not assume current):
- `src/autom8_asana/core/schema.py` -- delegates to `dataframes.models.registry`
- `src/autom8_asana/models/business/detection/types.py:20-22` -- re-exports EntityType from `core.types`
- `src/autom8_asana/models/business/detection/__init__.py` -- package re-exports for compat
- `src/autom8_asana/clients/data/client.py:66-77` -- PII + metrics re-exports
- `src/autom8_asana/automation/seeding.py:31-36` -- field_utils re-exports
- `src/autom8_asana/cache/models/freshness.py` -- entire file is a compat alias
- `src/autom8_asana/cache/__init__.py:295-298` -- `dataframe_cache` lazy re-export
- `src/autom8_asana/api/routes/resolver.py:79-85` -- model re-exports for test imports
- `src/autom8_asana/models/business/patterns.py:132-135` -- module-level constant aliases
- `src/autom8_asana/dataframes/cache_integration.py:450-456` -- `warm_struc_async` alias
- `src/autom8_asana/core/logging.py:104` -- module-level logger alias

### 3.2 Deprecated Functions/Classes Still Present

Code marked `deprecated` that has a successor and can be removed:
- `Task.get_custom_fields()` -- deprecated in favor of `custom_fields_editor()` (with `warnings.warn`)
- Deprecated `expected_type` parameter on `DefaultResolver.extract_value()` -- superseded by `column_def`
- `Freshness` alias for `FreshnessIntent` (entire `cache/models/freshness.py`)
- `ProcessType.GENERIC` -- "preserved for backward compatibility"

**Scan patterns**:
```
"deprecated"
"warnings.warn"
"DeprecationWarning"
".. deprecated::"
```

### 3.3 Dual-Path Logic (Old Way + New Way Coexisting)

Conditionals where one branch is the "legacy" or "fallback" path:
- `AutomationConfig.pipeline_templates` vs `pipeline_stages` with fallback resolution
- `_defaults/cache.py` "Original methods (backward compatible)" vs "New versioned methods"
- `protocols/cache.py` same dual-method surface
- `cache/backends/s3.py` / `redis.py` -- "legacy path" for internal client fallback
- `LEGACY_ATTACHMENT_PATTERN` cleanup in insights_export.py (transitional, one-cycle)
- `_StubReopenService` in lifecycle/engine.py (parallel-rewrite compatibility)
- `_children_cache` dual-write in `models/business/base.py:145-147`
- `HOLDER_KEY_MAP` fallback matching in `detection/facade.py:577` (legacy path with warning)
- `_apply_legacy_mapping` in `services/resolver.py:528`

**Scan patterns**:
```
"legacy path"
"legacy fallback"
"fallback to legacy"
"Fall back to"
"backward compatible"
"Original methods"
"parallel.rewrite"
"Stubs for"
```

### 3.4 Hardcoded Bespoke Workarounds

Hardcoded values or logic that should use a generic/configurable pattern:
- `config.py:106-117` -- "address" legacy alias for "location" with `_LEGACY_TTL_EXCLUDE` set
- `DEFAULT_ENTITY_TTLS["address"]` hardcoded at line 117
- `services/gid_lookup.py:253` -- `["office_phone", "vertical"]` hardcoded for backward compat
- `models/custom_field_accessor.py:38-53` -- `strict=False` legacy behavior path

**Scan patterns**:
```
"legacy alias"
"hardcoded"
"bespoke"
"preserved for"
"magic value"
```

### 3.5 Dead Migration Scaffolding

Artifacts from completed migrations that were never cleaned up:
- `cache/integration/autom8_adapter.py` -- migration helpers for legacy S3-to-Redis cutover (ADR-0025 migration complete)
- `cache/integration/factory.py:228` -- references `MIGRATION-PLAN-legacy-cache-elimination`
- `dataframes/builders/__init__.py:9` -- docstring references "compatibility shim"
- `BuildResult.to_legacy()` method -- converts to `ProgressiveBuildResult` for compat

**Scan patterns**:
```
"MIGRATION-PLAN"
"migration"
"compatibility shim"
"to_legacy"
"from_legacy"
```

### 3.6 Orphaned Test Fixtures

Tests that exercise deprecated/removed code paths or import from shim locations:
- Tests importing models from `api/routes/resolver.py` instead of `api/routes/resolver_models.py`
- Tests for deprecated `query_entities` endpoint

**Scan patterns**:
```
"from autom8_asana.api.routes.resolver import Resolution"
"from autom8_asana.cache.models.freshness import Freshness"
```

---

## 4. Scope Boundaries

### 4.1 IN SCOPE

- Backward-compat re-exports where the canonical location exists and all consumers can be updated
- Deprecated functions/parameters with existing successors
- Legacy alias constructs (e.g., "address" -> "location")
- Dual-path logic where one path is labeled "legacy" and the other is canonical
- Dead migration scaffolding from completed migrations
- Orphaned test code for removed features
- Import path updates across the codebase when removing re-exports
- `_StubReopenService` if `ReopenService` is now available (verify via import check)
- LEGACY_ATTACHMENT_PATTERN cleanup if confirmed as one-cycle transitional

### 4.2 OUT OF SCOPE (Do NOT Touch)

| Item | Reason | Reference |
|------|--------|-----------|
| `api/preload/legacy.py` (613 LOC) | Active degraded-mode fallback | ADR-011, D-003 |
| SaveSession decomposition | Coordinator pattern, confirmed | MEMORY.md |
| Cache divergence (12/14 dimensions) | Intentional, documented | ADR-0067 |
| Pipeline divergence (lifecycle vs automation) | Essential differences retained | D-022 CLOSED |
| Circular dep wholesale fix (915 deferred imports) | Trigger: production incident | SI-3 deferred |
| Heavy mock usage (540 sites) | Dedicated test initiative | D-027 deferred |
| D-002 (deprecated query handler) | Only if CloudWatch gate fails | Pre-flight 2.1 |
| Feature changes or new abstractions | Behavior preservation only | -- |
| Third-party code, vendored deps | Not our code | -- |
| `ResolutionResult.gid` property | Active API contract (multi-match + single-GID) | Not a shim |

### 4.3 Guardrails

1. **Behavior preservation**: No functional changes. Move imports, remove dead paths, collapse dual-path to single-path.
2. **Green-to-green**: Run scoped tests after every commit. Full suite before merge.
3. **File-scope contracts**: Each workstream declares exactly which files it touches. No file appears in two workstreams.
4. **Atomic commits**: One concern per commit, independently revertible.
5. **Import updates are exhaustive**: When removing a re-export, update ALL consumers in the same commit. `grep -rn` verification mandatory.
6. **No new abstractions**: If collapsing a dual-path creates a gap, document it as a follow-on -- do not design a new solution.

---

## 5. Prior Work References

| Artifact | Location | Relevance |
|----------|----------|-----------|
| Debt ledger | `docs/debt/LEDGER-cleanup-modernization.md` | D-002, D-003 status |
| ADR-011 (legacy preload) | `docs/decisions/ADR-011-*` | Confirms legacy.py is out-of-scope |
| ADR-0067 (cache divergence) | `docs/decisions/ADR-0067-*` | Confirms cache dual-path is intentional |
| ADR-0025 (cache migration) | Migration-plan items | May confirm autom8_adapter.py is dead |
| Patterns guide | `docs/guides/patterns.md` | Canonical error/DI patterns |
| REM-ASANA-ARCH PROMPT_0 | `.claude/wip/REM-ASANA-ARCH/PROMPT_0.md` | Closed items list |
| REM-HYGIENE WORKFLOW-SPEC | `.claude/wip/REM-HYGIENE/WORKFLOW-SPEC.md` | Proven worktree template |

---

## 6. Workflow Execution Model

### 6.1 Hygiene Rite Phases

```
[code-smeller]          Produce SMELL-REPORT-COMPAT-PURGE.md
       |                  (categorized findings with file:line, severity, ROI)
       v
[architect-enforcer]    Produce REFACTORING-PLAN-COMPAT-PURGE.md
       |                  (before/after contracts, workstream grouping,
       |                   file-scope isolation, dependency sequencing)
       v
[janitor]               Execute workstreams per plan
       |                  (atomic commits, scoped test verification)
       v
[audit-lead]            Produce AUDIT-REPORT-COMPAT-PURGE.md
                          (contract verification, behavior preservation, verdict)
```

### 6.2 Workstream Isolation Strategy

The architect-enforcer groups findings into workstreams with strict file-scope contracts.
Suggested grouping axes (architect-enforcer decides final grouping):

- **By module boundary**: cache/, models/, api/, services/, dataframes/, automation/, core/
- **By antipattern type**: re-exports, deprecated code, dual-path, dead scaffolding

Workstreams execute in parallel worktrees when file scopes are disjoint.
Three consecutive initiatives achieved zero merge conflicts with this pattern.

### 6.3 Merge Protocol

Per proven pattern from REM-HYGIENE/REM-ASANA-ARCH:

1. Worktree session executes workstream autonomously
2. Hub merges to main, runs scoped tests
3. Hub updates TRACKER.md
4. Next worktree session starts from updated main

### 6.4 Estimated Scope

Code-smeller discovery will determine actual scope. Rough signal from codebase scan:

| Category | Estimated Sites | Typical Fix |
|----------|----------------|-------------|
| Backward-compat re-exports | 12-18 | Update importers, delete shim |
| Deprecated functions/params | 4-6 | Remove deprecated path, update callers |
| Dual-path logic | 8-12 | Collapse to canonical path |
| Legacy aliases/hardcodes | 4-6 | Replace with canonical names |
| Dead migration scaffolding | 3-5 | Delete files/methods |
| Orphaned test code | 2-4 | Delete or update imports |

Total estimated: 33-51 sites, -1,500 to -3,000 LOC net reduction.

---

## 7. Success Criteria

### Quality Gate (Audit Lead)

- [ ] Zero backward-compat re-exports remain (unless explicitly documented as still-needed with justification)
- [ ] Zero deprecated functions/parameters remain that have active successors
- [ ] Zero dual-path logic where one path is labeled "legacy"
- [ ] Zero dead migration scaffolding from completed migrations
- [ ] All tests pass (green-to-green against pre-flight baseline)
- [ ] Zero new test failures introduced
- [ ] Every removed import path has been grep-verified with zero remaining consumers
- [ ] Net LOC reduction documented
- [ ] Each workstream's file-scope contract was honored (no cross-workstream file edits)

### Acceptance Criteria

- The codebase has one code path where there were two
- Import paths are canonical (no shim indirection)
- Comments containing "backward compat", "legacy alias", "preserved for" are eliminated or justified
- No warnings.warn(DeprecationWarning) calls remain for internal-only APIs

---

## 8. Artifacts

All artifacts go in `.claude/wip/COMPAT-PURGE/`:

| Artifact | Producer | Purpose |
|----------|----------|---------|
| `SMELL-REPORT.md` | code-smeller | Categorized findings with evidence |
| `REFACTORING-PLAN.md` | architect-enforcer | Workstream contracts and sequencing |
| `TRACKER.md` | hub thread | Workstream status tracking |
| `AUDIT-REPORT.md` | audit-lead | Final verification and verdict |

---

## 9. How to Launch

### Fresh Session Start

```
@.claude/wip/COMPAT-PURGE/PROMPT_0.md

Start the COMPAT-PURGE initiative. Begin with Phase 0 pre-flight,
then proceed to code-smeller assessment.
```

### Workstream Session Start (after plan is produced)

```
@.claude/wip/COMPAT-PURGE/PROMPT_0.md
@.claude/wip/COMPAT-PURGE/REFACTORING-PLAN.md

Execute workstream WS-{ID} per the refactoring plan.
```

---

## 10. Anti-Patterns for This Initiative

- **Removing something that is still used**: Always grep-verify before deleting. The re-export census (Phase 0) exists for this reason.
- **Treating ResolutionResult.gid as a shim**: It is an active API contract supporting both multi-match and single-GID consumers. It stays.
- **Touching legacy.py**: ADR-011 says no. It is an active fallback, not dead code.
- **Scope creep into architecture**: Collapsing a dual-path is cleanup. Designing a replacement system is architecture. Stay in cleanup.
- **Inflating LOC estimates**: Let the code-smeller discover the actual surface. The estimates in Section 6.4 are directional, not commitments.
