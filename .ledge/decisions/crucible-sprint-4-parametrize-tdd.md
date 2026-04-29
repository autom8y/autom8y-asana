---
type: decision
initiative: project-crucible
sprint: 4
rite: 10x-dev
created: 2026-04-15
author: architect
supersedes:
  - .ledge/decisions/crucible-sprint-3-parametrize-tdd.md  # for sprint-4 scope only; sprint-3 record is historical
consumes:
  - .sos/wip/crucible/sprint-3-qa-verdict.md
  - .sos/wip/crucible/sprint-3-parametrize-log.md
  - .sos/wip/frames/project-crucible-17-second-frontier.shape.md
  - .know/scar-tissue.md
produces:
  - CI filter change (@pytest.mark.slow excluded from PR gate)
  - parametrize conversions in tests/unit/clients/test_tasks_client.py
  - parametrize conversions across automation/, persistence/, dataframes/, cache/, core/ (scoped per micro-audit)
downstream_agent: principal-engineer
baseline_head: 105e26a2
status: accepted
---

# TDD: Crucible Sprint-4 Parametrize Campaign (Extended + Taxonomy Fast-Track)

## Overview

Sprint-4 executes three merged tracks on the sprint-3 output:

1. **Track A (Taxonomy fast-track)**: A one-edit change to the CI workflow's `test_markers_exclude` expression to exclude `@pytest.mark.slow` from the PR gate. 23 slow-marked tests across 14 files. Immediate compounding CI win; unblocks every downstream PR.
2. **Track B (Deferred Phase 3)**: Execute the sprint-3 TDD Phase 3 scope on `tests/unit/clients/test_tasks_client.py` (32 functions today). Low-risk, well-scoped, single-file.
3. **Track C (Extended parametrize)**: Extend the parametrize campaign across automation/, persistence/, dataframes/, cache/, and core/ — gated by a mandatory per-package micro-audit protocol.

**Calibration correction vs sprint-3 TDD**: Sprint-3 set aspirational targets (tier1 51 → 12–15, i.e., ~75% reduction) that evidence disproves. Actual sprint-3 landing was 37% (tier1) and 13% (tier2), both validated by qa-adversary as ceilings of safe consolidation, not under-execution. This TDD replaces the per-file 75% ceiling with a **per-file 15–40% band** and requires pre-phase micro-audit before any principal-engineer dispatch inside Track C.

## Context

### Sprint-3 Evidence (Load-Bearing Calibration)

| Source | Signal | Calibration Implication |
|--------|--------|------------------------|
| `sprint-3-parametrize-log.md` (PE) | tier1: 51→32 functions (37% reduction); tier2: 71→62 functions (13%) | Per-file reduction is bounded by test-semantic diversity, not copy-paste prevalence |
| `sprint-3-qa-verdict.md` (QA) | 122→122 cases collected; 355/355 scar tests pass; 13,012 full-suite pass (delta 0) | Behavioral preservation is achievable at per-file 15–40% reduction; no evidence it is achievable at 75% |
| DEV-02 (PE, QA-confirmed) | Scar-sweep paths in sprint-3 TDD drifted — two paths (`test_registry_consolidation.py`, `test_project_registry.py` under `tests/unit/core/`) did not exist at HEAD | TDD scar-path enumeration is a load-bearing artifact; must be reverified at HEAD 105e26a2 for sprint-4 |
| DEV-01 (PE, QA-confirmed) | CRU-S3-001 bundled into a mislabeled `style(tests):` commit by Terminus hook | Principal-engineer must drain dirty test state before first CRU-S4 commit |
| Attack 8 (QA) | Remaining 32 tier1 functions are genuinely diverse (8 spot-checked, all distinct semantics) | Forcing additional consolidation damages maintainability; "stop at genuine-diversity boundary" is correct |

### Throughline Reminder (from shape file)

- Success criteria includes: `@pytest.mark.slow excluded from PR gate CI filter expression`
- Sprint-4 exit criteria include: running count documented, SCAR-S3-LOOP cluster (`test_retry.py` 86 tests, `test_storage.py` 63 tests) audited with scar intent preserved, SCAR-005/006 (`test_cascade_validator.py`) audited
- PT-04 gate is **soft**: if function count lands at 5,500–6,500 range, proceed to sprint-5 anyway

### Sacred Constraints (Unchanged From Sprint-3)

1. All 33 scar-tissue tests pass after every commit
2. Coverage >= 80% at phase boundaries (run as pre-phase gate, not per-commit)
3. No `src/autom8_asana/` changes — tests-only
4. Independent revertibility per commit
5. `tests/unit/events/test_events.py` MockCacheProvider preserved
6. `tests/unit/clients/data/` subtree off-limits (TENSION-001)
7. SCAR-026 `spec=` track is parallel — `chore(tests): SCAR-026 -- ...` prefix, NOT `CRU-S4-NNN`

## System Design

### Architecture (Three-Track Pipeline)

```
                 ┌──────────────────────────────────────────────┐
                 │          Sprint-4 Execution Pipeline         │
                 └─────────────────────┬────────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
 ┌─────────────┐             ┌─────────────────┐           ┌────────────────────┐
 │  TRACK A    │             │    TRACK B      │           │      TRACK C       │
 │  Taxonomy   │             │  Phase 3 exec   │           │ Extended per-pkg   │
 │ Fast-Track  │             │ test_tasks_*    │           │ parametrize        │
 │             │             │  (32 fns)       │           │ (5 packages)       │
 └──────┬──────┘             └────────┬────────┘           └─────────┬──────────┘
        │                             │                              │
        │ 1-commit edit               │ 3-5 commits                  │ Per-pkg micro-audit GATE
        │ 23 slow tests               │ Pattern C + B                │       │
        │ excluded from PR gate       │ SCAR-S3-LOOP adjacent? NO    │       ▼
        │                             │ (test_tasks_client is        │   ┌─────────────────┐
        │                             │  model/raw/sync surface)     │   │  PROCEED? SKIP? │
        │                             │                              │   │    DEFER?       │
        ▼                             ▼                              │   └────┬────┬───┬───┘
  Immediate CI win              +~5 consolidations                   │        │    │   │
                                                                     │     Convert│   Defer
                                                                     │        │   │   │
                                                                     ▼        ▼   ▼   ▼
                                                              ┌──────────────────────────┐
                                                              │ Realistic per-pkg yield  │
                                                              │ 15-40% reduction band    │
                                                              └──────────────────────────┘
```

### Components

| Component | Responsibility | Location |
|-----------|----------------|----------|
| CI filter expression | Excludes marked tests from PR gate | `.github/workflows/test.yml:53` (primary), `justfile:108` (parity) |
| `@pytest.mark.slow` marker registry | Identifies slow tests | `pyproject.toml:110-114` (declaration) |
| `client_factory` fixture | Unchanged from sprint-3 | `tests/unit/clients/conftest.py` |
| Micro-audit reports (NEW) | Per-package go/skip/defer decision + rationale | `.sos/wip/crucible/sprint-4-micro-audit-{package}.md` |
| Scar-sweep command (refreshed) | Runs 33 scar-adjacent regression tests | See "Refreshed Scar Matrix" section below |
| Coverage gate | `--cov-fail-under=80` | Pre-phase and exit gate only |

### Data Model

Not applicable (test-structural refactor). The only new artifact class is the **micro-audit report** (see Track C protocol).

## Track A: Domain 4 Taxonomy Fast-Track

### Objective

Exclude `@pytest.mark.slow` tests from the CI PR gate. The shape file lists this as a distinct success criterion; it compounds across every subsequent Crucible commit (each `CRU-S4-NNN` PR runs faster, reducing reviewer wait time).

### Scope Clarification (IMPORTANT: brief said pyproject.toml; actual location is different)

The sprint-4 brief directs the edit to `pyproject.toml`'s CI filter expression. However, `pyproject.toml` does **not** contain the CI filter. Grep evidence:

- `.github/workflows/test.yml:53` — `test_markers_exclude: 'not integration and not benchmark'` (actual CI gate)
- `justfile:108` — `uv run pytest tests/ -m "not slow and not integration and not benchmark" {{args}}` (local dev parity, already correct)
- `pyproject.toml:110-114` — declares the `slow` marker but holds no filter expression

**Edit targets**: The primary edit is `.github/workflows/test.yml:53`. The `justfile` is already correct (`test-fast` excludes `slow`); no `justfile` edit required. The `pyproject.toml` marker declaration is preserved.

### Exact Edit (Track A)

**File**: `.github/workflows/test.yml`, line 53

**Before**:
```yaml
      test_markers_exclude: 'not integration and not benchmark'
```

**After**:
```yaml
      test_markers_exclude: 'not integration and not benchmark and not slow'
```

One line. No other edits required.

### Slow-Marked Test Inventory (23 tests, 14 files)

Verified by `Grep("@pytest\.mark\.slow", path=tests/)` at HEAD 105e26a2:

| File | Count | Scar-adjacent? |
|------|-------|----------------|
| `tests/unit/api/test_startup_preload.py` | 1 | No |
| `tests/unit/api/test_routes_admin.py` | 2 | No |
| `tests/unit/api/test_routes_admin_edge_cases.py` | 2 | No |
| `tests/unit/api/test_health.py` | 1 | SCAR-011 adjacent — liveness/readiness split. Verify. |
| `tests/unit/cache/test_concurrency.py` | 1 | No (concurrency test; not SCAR-010 territory) |
| `tests/unit/cache/test_edge_cases.py` | 1 | No |
| `tests/unit/cache/test_memory_backend.py` | 3 | No |
| `tests/unit/clients/data/test_cache.py` | 2 | **Off-limits subtree (TENSION-001)** — don't touch the tests, but the slow marker exclusion applies via filter without any edits to this file |
| `tests/unit/clients/data/test_insights.py` | 4 | Same (filter-only, no file edit) |
| `tests/unit/clients/data/test_observability.py` | 1 | Same |
| `tests/unit/clients/data/test_circuit_breaker.py` | 2 | Same |
| `tests/unit/metrics/test_edge_cases.py` | 1 | No |
| `tests/unit/metrics/test_adversarial.py` | 1 | No |
| `tests/validation/persistence/test_performance.py` | 1 | Validation suite, not unit path |

**Total**: 23 markers across 14 files. Validated against the throughline's claim of 23 slow tests. The `clients/data/` subtree slow tests are reachable via the filter change without touching those off-limits files.

### Verification Protocol (Track A)

Principal-engineer runs these checks in order before committing:

1. **Baseline without flag**: `uv run pytest tests/ -m 'not integration and not benchmark' --collect-only -q | tail -5` — record collected count.
2. **Simulated new filter**: `uv run pytest tests/ -m 'not integration and not benchmark and not slow' --collect-only -q | tail -5` — record collected count. Delta must equal 23 (or match within collection quirks; document if not).
3. **Scar sweep passes**: Run refreshed scar sweep (see below). All scar tests are `not slow` by evidence (verify inventory table above; only `test_health.py` flirts with SCAR-011 territory and its slow marker is on `TestDepsEndpoint`, not on the SCAR-011 liveness tests).
4. **Full suite with new filter**: `uv run pytest tests/ -m 'not integration and not benchmark and not slow' --timeout=120 -q` — confirm zero failures, delta from baseline = -23 tests deselected.
5. **Commit**: `ci(tests): CRU-S4-001 -- exclude @pytest.mark.slow from PR gate filter`

### Commit (Track A)

Single commit. Message format (conventions skill compliant):

```
ci(tests): CRU-S4-001 -- exclude @pytest.mark.slow from PR gate filter

Adds 'and not slow' to test_markers_exclude in satellite-ci-reusable invocation.
23 tests across 14 files move from PR gate to post-merge full-suite run.

Evidence: .sos/wip/crucible/sprint-3-qa-verdict.md
Frame: .sos/wip/frames/project-crucible-17-second-frontier.shape.md (success criterion)
TDD: .ledge/decisions/crucible-sprint-4-parametrize-tdd.md (Track A)
```

### Risk (Track A)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| A scar-critical test carries `@pytest.mark.slow` and regresses silently on main | LOW | HIGH | Inventory table above verifies zero overlap with scar paths. `tests/unit/api/test_health.py` slow marker is on `TestDepsEndpoint` (not SCAR-011 liveness), but PE must spot-check this before committing |
| Post-merge full-suite run becomes the only gate for slow tests | MED | MED | Acceptable per shape file success criterion. The full-suite run still runs on push (`run_integration: ${{ github.event_name == 'push' }}`) |

## Track B: Deferred Phase 3 — `test_tasks_client.py`

### Objective

Execute sprint-3 TDD Phase 3 on `tests/unit/clients/test_tasks_client.py` (32 functions, HEAD 105e26a2 verified). Carry forward sprint-3's pattern catalog (A/B/C/D/E) unchanged. Estimated ~11 functions consolidated.

### Scope

| CRU-ID | Pattern | Target | Expected yield |
|--------|---------|--------|----------------|
| CRU-S4-002 | C (raw=True) | `get_async` family (model + raw + sync variants) | 3 → 1 |
| CRU-S4-003 | C (raw=True) | `create_async` family | 3 → 1 |
| CRU-S4-004 | B | sync-wrapper method-name parametrize | 2 → 1 |
| CRU-S4-005 | E (opportunistic) | Boundary-inversion cleanup in remaining `assert_called_once_with` duplicates | Variable |

**Realistic yield**: 32 → ~21 functions (34% reduction). This matches sprint-3's tier1 37% landing and aligns with the "per-file 15–40% band" calibration.

### Pattern Reference

Patterns A/B/C/D/E are defined in `.ledge/decisions/crucible-sprint-3-parametrize-tdd.md` (Pattern Catalog section). Not duplicated here; PE reads the sprint-3 TDD for pattern templates.

### Risk (Track B)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `test_tasks_client.py` has genuine-diversity functions that resist Pattern C | MED | LOW | Apply "defer ambiguity: STOP" rule from sprint-3; 11 is an estimate, not a floor |
| Coverage regression in `TasksClient` surface | LOW | MED | Coverage is gated at phase boundary, not per-commit |

## Track C: Extended Parametrize with Mandatory Pre-Phase Micro-Audit

### Objective

Extend parametrize across 5 packages (automation/, persistence/, dataframes/, cache/, core/). Budget realistically: not every package yields consolidation.

### Package Inventory (HEAD 105e26a2)

| Package | Files | Test functions | Scar density | Audit cost |
|---------|-------|----------------|--------------|------------|
| automation/ | 43 | 1,086 | LOW (SCAR-016, 017, 018, 019 are single-file regression suites) | 3-5 files read |
| persistence/ | 28 | 982 | **HIGH** (SCAR-010/010b on `test_session_concurrency.py` 19+ tests, SCAR-008 in session.py territory) | 5-7 files read |
| dataframes/ | 49 | 1,150 | **HIGH** (SCAR-005/006/023 on `test_cascade_validator.py`, SCAR-S3-LOOP on `test_storage.py` 63 tests, SCAR-007 on `test_build_result.py`) | 6-8 files read |
| cache/ | 56 | 1,301 | MED (SCAR-004 adjacent; no single cache file carries a scar, but proliferation effects are real) | 5-7 files read |
| core/ | 10 | 355 | **VERY HIGH** (SCAR-001 on `test_project_registry.py`, SCAR-027 on `test_creation.py`, SCAR-S3-LOOP on `test_retry.py` 86 tests) | ALL 10 files — small corpus |

**Aggregate**: 186 files, 4,874 test functions across 5 packages. Note the non-linear scar density.

### Pre-Phase Micro-Audit Protocol (Track C Execution Gate)

Before principal-engineer opens ANY `CRU-S4-NNN` commit inside Track C for a given package, the following protocol is MANDATORY. Potnia should reject PE dispatch for Track C packages without a completed micro-audit artifact.

#### Step 1: Read 3-5 files from the package

Principal-engineer selects files by:
- Highest function count (most consolidation potential)
- Plus at least one scar-intersection file (to confirm scar-preservation strategy)

#### Step 2: Classify each read file

Per file, classify into one of three buckets:

| Classification | Criterion | Action |
|----------------|-----------|--------|
| **PROCEED** | >= 3 near-duplicate test bodies with copy-paste pattern fitting Pattern A/B/C/D | Parametrize in a `CRU-S4-NNN` commit |
| **SKIP** | Tests are genuinely diverse; forcing parametrize damages maintainability | No commit; document in micro-audit artifact with one-line rationale per test-class |
| **DEFER** | Scar-intersection file; consolidation requires sole-coverage verification or scar-intent rewrite | Defer to sprint-5 or explicit architect re-consultation |

#### Step 3: Estimate realistic consolidation ratio

Using the **15–40% band** calibration:

- If estimated per-file yield is < 15%: SKIP the file.
- If estimated 15–40%: PROCEED with a concrete Pattern assignment.
- If estimated > 40%: Treat with suspicion — sprint-3 evidence suggests this is rare. Re-read for missed diversity. If still confident, PROCEED but verify via `pytest --collect-only` case count before/after.

#### Step 4: Produce the micro-audit artifact

Write to `.sos/wip/crucible/sprint-4-micro-audit-{package}.md` with frontmatter:

```yaml
---
type: scratch
initiative: project-crucible
sprint: 4
rite: 10x-dev
agent: principal-engineer
package: {automation|persistence|dataframes|cache|core}
baseline_head: 105e26a2
created: YYYY-MM-DD
---
```

Contents (per package):
- Files read (absolute paths)
- Per-file classification (PROCEED/SKIP/DEFER) with one-line rationale
- Realistic consolidation estimate (range, not point)
- Pattern assignment for PROCEED files (A/B/C/D/E)
- Scar-intersection flags with regression-test coordinates
- Commit plan (`CRU-S4-NNN` → file → pattern → estimated yield)

#### Step 5: Self-gate

Principal-engineer proceeds to commit ONLY IF:
- [ ] Micro-audit artifact written and committed as `chore(docs): sprint-4 micro-audit {package}`
- [ ] All DEFER files have an explicit sprint-5 parking note
- [ ] Coverage baseline recorded for the package (`uv run pytest tests/unit/{package}/ --cov=src --cov-fail-under=80`)
- [ ] Scar tests adjacent to PROCEED files identified with regression-test coordinates

### Package-Specific Guidance

#### automation/ (1,086 fns, LOW scar density)

- **Likely PROCEED patterns**: Polling scheduler per-rule dispatch tests, workflow dry-run/live parametrize, per-schedule-type config validation
- **Likely SKIP patterns**: `test_conversation_audit.py` per-scenario end-to-end tests (already scenario-structured); `test_polling_scheduler.py:839,928,1036` (SCAR-018 regression — preserve)
- **Realistic band**: 20–35% reduction (~215–380 fns saved)

#### persistence/ (982 fns, HIGH scar density)

- **DEFER ALL**: `tests/unit/persistence/test_session_concurrency.py` (SCAR-010/010b, 19+ tests). Do not touch. The concurrency tests are semantic distinct per-method and scar-intent requires preserving the structural shape.
- **Likely PROCEED patterns**: Save-session happy-path lifecycle tests, snapshot-read/write parametrize
- **Realistic band**: 10–25% reduction (~100–245 fns saved) — lower than other packages because ~40% of the file count is scar territory

#### dataframes/ (1,150 fns, HIGH scar density)

- **DEFER ALL**: `tests/unit/dataframes/test_storage.py` (SCAR-S3-LOOP, 63 tests), `tests/unit/dataframes/builders/test_cascade_validator.py` (SCAR-005/006/023, 580+ lines), `tests/unit/dataframes/test_cascade_ordering_assertion.py`, `tests/unit/dataframes/test_warmup_ordering_guard.py`, `tests/unit/dataframes/builders/test_build_result.py` (SCAR-007), `tests/unit/dataframes/test_section_persistence_storage.py` (SCAR-002)
- **Likely PROCEED**: Builder/extractor families (progressive builder steps, row-coercion parametrize, schema-field descriptor tests), view plugin per-column tests
- **Realistic band**: 25–40% reduction on non-deferred subset (~200–350 fns saved overall)

#### cache/ (1,301 fns, MED scar density)

- **Likely PROCEED**: Per-backend (memory, disk, derived) CRUD parametrize, TTL variant tests, key-composition parametrize
- **DEFER**: `test_concurrency.py` (SCAR-004 adjacent — cache provider isolation), any `test_derived*.py` that crosses SCAR-004 territory
- **Realistic band**: 20–35% reduction (~260–455 fns saved)

#### core/ (355 fns, VERY HIGH scar density)

- **DEFER**: `tests/unit/core/test_retry.py` (SCAR-S3-LOOP, 86 tests), `tests/unit/core/test_project_registry.py` (SCAR-001), `tests/unit/core/test_creation.py` (SCAR-027 — already parametrize-like, preserve intent), `tests/unit/core/test_entity_registry.py` (SCAR-001 adjacent)
- **Likely PROCEED**: Remaining core helpers (formatters, small utility modules). Small corpus — low absolute yield.
- **Realistic band**: 5–15% reduction (~17–53 fns saved)

### Aggregate Track C Realistic Yield

| Package | Low | High |
|---------|-----|------|
| automation/ | 215 | 380 |
| persistence/ | 100 | 245 |
| dataframes/ | 200 | 350 |
| cache/ | 260 | 455 |
| core/ | 17 | 53 |
| **Track C total** | **~790** | **~1,480** |

Combined with Track B (~11) and Track A (0 fns removed, filter-level), sprint-4 realistic total: **~800–1,490 fns reduced**. The sprint-4 exit target from the shape file (4,500–5,500 range) requires aggregate reduction from HEAD 105e26a2's running total — PE must record the current running total at Track C kickoff and project against this band.

## Refreshed Scar-Tissue Matrix (HEAD 105e26a2)

Per DEV-02: sprint-3 TDD's scar paths included two files that did not exist. Re-verification against HEAD 105e26a2 confirms the corrected inventory below. **All 22 paths verified present via direct filesystem check.** The original DEV-02 concern was a false positive — `tests/unit/core/test_project_registry.py` (SCAR-001) DOES exist at HEAD; the sprint-3 PE's scar sweep skipped it because the execution-log command contained a subset list, not the full canonical list.

### Canonical Scar Sweep Command (Sprint-4)

```bash
uv run pytest \
  tests/unit/core/test_project_registry.py \
  tests/unit/core/test_entity_registry.py \
  tests/unit/core/test_registry_validation.py \
  tests/unit/core/test_creation.py \
  tests/unit/core/test_retry.py \
  tests/unit/dataframes/test_storage.py \
  tests/unit/dataframes/test_cascade_ordering_assertion.py \
  tests/unit/dataframes/test_warmup_ordering_guard.py \
  tests/unit/dataframes/test_section_persistence_storage.py \
  tests/unit/dataframes/builders/test_cascade_validator.py \
  tests/unit/dataframes/builders/test_build_result.py \
  tests/unit/persistence/test_session_concurrency.py \
  tests/unit/reconciliation/test_section_registry.py \
  tests/unit/models/business/matching/test_normalizers.py \
  tests/unit/models/business/test_registry_consolidation.py \
  tests/unit/services/test_gid_push.py \
  tests/unit/services/test_universal_strategy_status.py \
  tests/unit/api/test_routes_resolver.py \
  tests/unit/api/routes/test_admin_force_rebuild.py \
  tests/unit/api/routes/test_webhooks.py \
  tests/unit/api/test_lifespan_workflow_import.py \
  tests/integration/test_lifecycle_smoke.py \
  -q --timeout=60
```

### Scar-Path Mapping (Verified)

| Scar | Regression test path | Verified at HEAD |
|------|---------------------|------------------|
| SCAR-001 | `tests/unit/core/test_project_registry.py:225-270` | OK |
| SCAR-002 | `tests/unit/dataframes/test_section_persistence_storage.py` | OK |
| SCAR-003 | `tests/unit/api/routes/test_admin_force_rebuild.py` | OK |
| SCAR-005/006/023 | `tests/unit/dataframes/builders/test_cascade_validator.py:668`, `tests/unit/dataframes/test_warmup_ordering_guard.py`, `tests/unit/dataframes/test_cascade_ordering_assertion.py:71-106` | OK |
| SCAR-007 | `tests/unit/dataframes/builders/test_build_result.py` | OK |
| SCAR-010/010b | `tests/unit/persistence/test_session_concurrency.py` (19+ tests) | OK |
| SCAR-011b | `tests/unit/api/test_lifespan_workflow_import.py` | OK |
| SCAR-014 | `tests/integration/test_lifecycle_smoke.py:1720-1751` | OK |
| SCAR-015 | `tests/unit/services/test_section_timeline_service.py`, `tests/unit/api/test_routes_section_timelines.py` | OK (add to sweep if sprint-4 touches dataframes/services) |
| SCAR-016 | `tests/unit/automation/workflows/test_conversation_audit.py:642` | Add to sweep when automation/ micro-audit proceeds |
| SCAR-017 | `tests/unit/automation/workflows/test_conversation_audit.py:1362` | Same |
| SCAR-018 | `tests/unit/automation/polling/test_polling_scheduler.py:839,928,1036` | Same |
| SCAR-019 | `tests/unit/automation/polling/test_config_schema.py:492,566` | Same |
| SCAR-020 | `tests/unit/api/test_routes_resolver.py:565`, `tests/unit/models/business/matching/test_normalizers.py:65-67` | OK |
| SCAR-024 | `tests/unit/models/business/matching/test_normalizers.py:65` | OK |
| SCAR-027 | `tests/unit/core/test_creation.py` (12 cases) | OK |
| SCAR-028 | `tests/unit/services/test_gid_push.py` | OK |
| SCAR-029 | `tests/unit/api/routes/test_webhooks.py` (45 adversarial, 78+ total) | OK |
| SCAR-S3-LOOP | `tests/unit/core/test_retry.py` (86 tests), `tests/unit/dataframes/test_storage.py` (63 tests) | OK |

Scars without dedicated regression tests (SCAR-004, SCAR-008, SCAR-009, SCAR-012, SCAR-013, SCAR-021, SCAR-022, SCAR-025, SCAR-026, SCAR-030, SCAR-IDEM-001, SCAR-REG-001, SCAR-WS8, Env Var) are known-gap items from `.know/scar-tissue.md` — not enforceable in the sweep.

## Failure Modes (From Sprint-3 Lessons — Do Not Repeat)

| Anti-pattern | Sprint-3 symptom | Sprint-4 prevention |
|--------------|------------------|---------------------|
| **Aspirational ratio targets** | 75% targets achieved 13–37% actual | Per-file 15–40% band; micro-audit before execute |
| **Forcing parametrize on diverse tests** | Would have bloated `extra_assertions` dict in sprint-3 if PE had continued past 32 | "Defer ambiguity: STOP" rule; SKIP classification in micro-audit |
| **Mislabeled commits** (DEV-01) | `style(tests):` hid CRU-S3-001 content | Drain dirty test state before first `CRU-S4-NNN` commit; verify commit message matches content |
| **Fusing SCAR-026 `spec=` into CRU commits** | Would bundle additive change with reduction change | SCAR-026 parallel track: `chore(tests):` prefix only |
| **Per-commit coverage measurement** | Doubled wall-clock in sprint-3 | Phase-boundary only: run at Track entry and Track exit |
| **Skipping Domain 1 + Domain 2 merge** | Single-pass efficiency on boundary-inversion was correct in sprint-3 | Same approach — Pattern E boundary fuse lands in same commit as Pattern A/B/C conversion where applicable |
| **Drift in scar-path enumeration** | DEV-02 | Canonical sweep command above verified at HEAD 105e26a2 |

## Commit Naming Convention

| ID range | Track | Prefix |
|----------|-------|--------|
| CRU-S4-001 | A | `ci(tests):` |
| CRU-S4-002..005 | B | `refactor(tests):` |
| CRU-S4-006..NNN | C (convert) | `refactor(tests):` |
| CRU-S4-NNN | C (test-case removal, only if QA-confirmed duplicate) | `refactor(tests):` |
| chore-audit | C (micro-audit docs) | `chore(docs):` |
| SCAR-026 spec= work | Parallel | `chore(tests): SCAR-026 -- ...` (NOT `CRU-S4-NNN`) |

Example: `refactor(tests): CRU-S4-002 -- Pattern C fuse tasks_client get_async family (3->1)`

## Success Criteria

| Track | Criterion | Measurement |
|-------|-----------|-------------|
| A | `test_markers_exclude` contains `and not slow` | Grep at `.github/workflows/test.yml:53` |
| A | PR gate collection count drops by ~23 | `pytest --collect-only` delta |
| A | Full suite on `push` still runs slow tests | Manual check of CI run artifacts after first push |
| B | `test_tasks_client.py` function count: 32 → ~21 | `grep -c 'def test_' tests/unit/clients/test_tasks_client.py` |
| B | Case count preserved | `pytest --collect-only tests/unit/clients/test_tasks_client.py` delta = 0 |
| C | Each package has a micro-audit artifact OR is documented as deferred | `ls .sos/wip/crucible/sprint-4-micro-audit-*.md` |
| C | 800–1,490 fns reduced across all 5 packages | Running total documented in sprint-4 log |
| All | 33 scar tests pass after every commit | Canonical scar sweep command above |
| All | Coverage >= 80% at phase boundaries | `--cov-fail-under=80` at Track A entry, Track B exit, and each Track C package exit |
| All | Every original test case preserved (no `--collect-only` case loss) | Per-file case count check before/after each `CRU-S4-NNN` |

## Exit Handoff

Sprint-4 exit produces:

- `.sos/wip/crucible/sprint-4-extended-parametrize-log.md` (PE)
- Per-package micro-audit artifacts (PE)
- `.sos/wip/crucible/sprint-4-qa-verdict.md` (QA)

These consume into sprint-5 (taxonomy completion — fast-marker application) or sprint-6 (final verification).

## ADR-Style Decisions (Inline)

### ADR-S4-001: Per-File 15–40% Reduction Band Replaces 75% Ceiling

**Context**: Sprint-3 TDD set 51→12–15 tier1 target (~75%). Actual was 51→32 (37%). qa-adversary confirmed the remaining 32 functions are genuinely diverse.

**Decision**: Replace 75% per-file ceiling with a 15–40% band calibrated on sprint-3 evidence. Values below 15% trigger SKIP classification; values above 40% trigger re-read (suspicion of missed diversity).

**Consequences**:
- (+) Estimates are defensible against evidence, not aspirational
- (+) PE is protected against pressure to force over-consolidation
- (−) Aggregate fn-count yield lower than sprint-3 TDD projected
- (−) Requires micro-audit overhead per package (mitigated: small-corpus packages like core/ audit is ~1 hour)

### ADR-S4-002: CI Filter Edit Targets `.github/workflows/test.yml`, Not `pyproject.toml`

**Context**: Sprint-4 brief directed the edit to `pyproject.toml`'s CI filter expression. Grep confirms `pyproject.toml` holds only marker declarations; the actual filter is in `.github/workflows/test.yml:53`.

**Decision**: Edit `.github/workflows/test.yml:53`. Preserve `pyproject.toml` marker declaration unchanged.

**Consequences**:
- (+) Edit lands in the load-bearing location
- (−) `justfile:108` already correct — no edit needed, but PE must confirm parity before commit

### ADR-S4-003: Track C Requires Mandatory Per-Package Micro-Audit

**Context**: Sprint-3's per-file yield was highly variable (37% tier1, 13% tier2). Packages with high scar density (persistence/, dataframes/, core/) carry larger variance risk.

**Decision**: No `CRU-S4-NNN` commit lands in Track C without a committed micro-audit artifact.

**Consequences**:
- (+) PE makes evidence-based SKIP/DEFER decisions before investing commit effort
- (+) Scar-intersection files surface early
- (−) Adds a read-and-document phase before each package's first commit
- (−) Potnia gate complexity grows slightly (must verify artifact exists before dispatching)

## Open Items

- **Running function count at sprint-4 entry**: PE must record this at Track C kickoff. Shape-file 4,500–5,500 target is a suite-wide envelope, not a sprint-4 delta.
- **`tests/unit/clients/` residue** (Phase 1/2 per sprint-3 PE handoff): sprint-3 identified ~4 additional pair-fuses (ProjectsClient create pair, CustomFields create pair, sync-wrapper pair) pushing tier1 to ~28. These are NOT in this sprint-4 scope unless Potnia explicitly adds them. Recommended: park to sprint-5 residue pass.
- **SCAR-026 `spec=` track**: Proceeds in parallel under `chore(tests):` — not `CRU-S4-NNN`. Scope determined by separate audit; not a sprint-4 architect deliverable.

## Acid Test

"In 18 months, will we look at this TDD and say 'the ratios made sense given what sprint-3 actually demonstrated'? Or will we say 'they kept the 75% target from sprint-3 and the PE had no budget protection'?"

This TDD answers with: defensible 15–40% band grounded in sprint-3 landing evidence, mandatory micro-audit before investment, explicit DEFER list for scar-heavy files. The principal-engineer has a realistic budget, not an aspirational ceiling.
