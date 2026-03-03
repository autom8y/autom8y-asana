# REM-ASANA-ARCH Sprint Manifest

**Pattern**: sprint-parallel-worktrees (2-lane execution)
**Initiative**: Architecture Remediation Sprint
**Workstreams**: 7 active (WS-CLASS SKIPPED)
**Sessions**: 11 total across 4 phases + cross-rite
**Parallelism**: 2 concurrent worktrees max
**Started**: 2026-02-23

---

## Execution Protocol

### Per-Worktree Lifecycle

```
1. HUB:       ari worktree create "<ws-name>" --rite "<rite>"
2. HUB:       Note worktree path from output
3. TERMINAL:  cd <worktree-path> && claude
4. WORKTREE:  @.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
              @.claude/wip/REM-ASANA-ARCH/WS-{ID}.md
              <session prompt from manifest below>
5. WORKTREE:  /go "<WS-ID>: <description>"
6. WORKTREE:  (autonomous execution per seed)
7. WORKTREE:  /wrap
8. HUB:       cd <main-project> && git merge <worktree-branch>
9. HUB:       Update TRACKER.md + MEMORY.md
10. HUB:      ari worktree remove "<worktree-id>"
```

### Rite Switching (Critical)

Rite changes require full Claude restart:
```bash
# In the worktree BEFORE launching claude:
ari sync --rite=<rite-name>
# Then start claude fresh in that worktree
claude
```

### Test Protocol (Modified Guardrail #6)

- **During development**: Scoped tests only (`pytest tests/unit/<module>/ -x`)
- **At QA gates**: Full suite (`AUTOM8Y_ENV=production .venv/bin/python -m pytest tests/ -x`)
- QA gates: end of each workstream session, NOT after every change

---

## Phase 0: Quick Wins (Day 1)

### Session 01: WS-QW

| Field | Value |
|-------|-------|
| **Worktree** | `ws-qw` |
| **Rite** | Native (no rite needed) |
| **Lane** | 1 (solo) |
| **Effort** | 2-4 hours (reduced: R-001/R-007 pre-resolved) |
| **Dependencies** | None |

**Worktree setup**:
```bash
ari worktree create "ws-qw"
# No rite sync needed — native execution
cd <worktree-path> && claude
```

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-QW.md

Execute WS-QW Quick Wins. Native execution, no rite activation needed.

Pre-resolved unknowns (from Phase 0 pre-flight):
- U-003: Bootstrap guard PRESENT at conversation_audit.py:21-23. R-001 = verify only, update entry-point audit doc.
- U-007: cloudwatch.py is a utility module (emit_metric for cache_warmer/cache_invalidate). No entity detection, no bootstrap needed. Document in entry-point audit.

Execution order:
1. R-001: Update .claude/wip/ENTRY-POINT-AUDIT.md — mark conversation_audit.py bootstrap VERIFIED
2. R-007: Update .claude/wip/ENTRY-POINT-AUDIT.md — document cloudwatch.py as "utility, no bootstrap required"
3. R-003: Add docstrings to lifecycle/__init__.py and comment to automation/pipeline.py. Zero functional changes.
4. R-002: Extract 3 helpers to core/creation.py. One at a time. Scoped tests after each (pytest tests/unit/lifecycle/ tests/unit/automation/ tests/unit/core/ -x).

Full suite at end only: AUTOM8Y_ENV=production .venv/bin/python -m pytest tests/ -x

When complete, output checkpoint text for MEMORY.md update.
```

**Scope boundary**: Touches `core/creation.py`, `lifecycle/`, `automation/pipeline.py`, `.claude/wip/ENTRY-POINT-AUDIT.md`

**Done gate**: R-001 verified, R-007 documented, R-003 docstrings added, R-002 helpers extracted, full suite green

---

## Phase 1: Foundation (Days 2-5, 2 parallel lanes)

### Session 02: WS-SYSCTX (Lane 1)

| Field | Value |
|-------|-------|
| **Worktree** | `ws-sysctx` |
| **Rite** | hygiene |
| **Lane** | 1 |
| **Effort** | 1-2 days |
| **Dependencies** | None |

**Worktree setup**:
```bash
ari worktree create "ws-sysctx" --rite "hygiene"
# OR if rite flag not supported:
ari worktree create "ws-sysctx"
cd <worktree-path>
ari sync --rite=hygiene
claude
```

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-SYSCTX.md

Execute WS-SYSCTX: system_context.py registration pattern refactor.

Pre-resolved: U-006 confirms system_context.py was a pragmatic creation (single commit: "feat(core): add cross-registry validation"). This validates the registration pattern approach.

Skip Pythia orchestration — the seed IS the implementation plan. Execute as principal-engineer direct.

Steps:
1. Add registration API to system_context.py (Step 1 in seed)
2. Migrate SchemaRegistry first (Step 2) — verify with: pytest tests/ -k reset --tb=short
3. Migrate remaining 7 singletons one-at-a-time (Step 3). Scoped test after each: pytest tests/unit/dataframes/ tests/unit/models/ tests/unit/services/ -x
4. Remove all upward imports (Step 4)
5. Full suite at final gate: AUTOM8Y_ENV=production .venv/bin/python -m pytest tests/ -x
6. Run suite 3x for stability check

Do NOT batch-migrate. Do NOT move system_context.py out of core/.

When complete, output checkpoint text for MEMORY.md.
```

**Scope boundary**: `core/system_context.py` + registration calls in `dataframes/models/registry.py`, `models/business/registry.py`, `models/business/_bootstrap.py`, `dataframes/watermark.py`, `services/resolver.py`, `metrics/registry.py`, `cache/dataframe/factory.py`

**Done gate**: Zero upper-layer imports in system_context.py, Cycle 4 eliminated, 3x stability clean

---

### Session 03: WS-DEBT (Lane 2)

| Field | Value |
|-------|-------|
| **Worktree** | `ws-debt` |
| **Rite** | debt-triage |
| **Lane** | 2 |
| **Effort** | 1-2 days |
| **Dependencies** | None |

**Worktree setup**:
```bash
ari worktree create "ws-debt"
cd <worktree-path>
ari sync --rite=debt-triage
claude
```

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-DEBT.md

Execute WS-DEBT: v1 query sunset consumer audit.

This is an investigation + decision workstream. Use debt-triage rite.

Steps:
1. Code audit: Read api/routes/query.py, search for v1-specific routes. Search codebase for "v1/query" references.
2. Traffic audit: Note that CloudWatch API access logs require operational access. Document what CAN be determined from code, note what requires CloudWatch.
3. Decision: Based on code evidence, recommend remove-now vs. migration-plan. The 2026-06-01 deadline is ~14 weeks out.
4. Update D-002 in docs/debt/LEDGER-cleanup-modernization.md with findings.

When complete, output checkpoint text for MEMORY.md.
```

**Scope boundary**: `api/routes/query.py` (read only), `docs/debt/LEDGER-cleanup-modernization.md`

**Done gate**: v1 consumer inventory documented, D-002 updated, decision documented

---

### Session 04: WS-DSC Session 1 — Architect (Lane 2, after WS-DEBT)

| Field | Value |
|-------|-------|
| **Worktree** | `ws-dsc` |
| **Rite** | 10x-dev |
| **Lane** | 2 |
| **Effort** | 1-2 days |
| **Dependencies** | None |

**Worktree setup**:
```bash
ari worktree create "ws-dsc" --rite "10x-dev"
# OR:
ari worktree create "ws-dsc"
cd <worktree-path>
ari sync --rite=10x-dev
claude
```

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-DSC.md

WS-DSC Session 1: ARCHITECT PHASE ONLY.

This is a 10x-dev rite session. This session produces a TDD spec — no implementation code.

Read all 5 endpoint modules to identify the exact 8-step orchestration pattern:
- src/autom8_asana/clients/data/_endpoints/simple.py (234 LOC)
- src/autom8_asana/clients/data/_endpoints/batch.py (310 LOC)
- src/autom8_asana/clients/data/_endpoints/insights.py (219 LOC)
- src/autom8_asana/clients/data/_endpoints/export.py (173 LOC)
- src/autom8_asana/clients/data/_endpoints/reconciliation.py (133 LOC)
- src/autom8_asana/clients/data/_retry.py (191 LOC)

Document variations (extra steps, different error handling, custom retry logic per endpoint).

Design:
1. EndpointPolicy protocol (exact method signatures)
2. DefaultEndpointPolicy implementation strategy
3. Key decisions: generic type params, error mapping plugin, circuit breaker injection vs. inheritance, metrics parameterization
4. Migration order rationale
5. Before/after LOC estimates per endpoint

Write TDD spec to: .claude/wip/REM-ASANA-ARCH/WS-DSC-TDD-SPEC.md

Do NOT implement code in this session. Design only. Emit checkpoint.
```

**Scope boundary**: Read-only on `clients/data/`. Writes only to `.claude/wip/` (TDD artifact)

**Done gate**: TDD spec produced with protocol definition, migration strategy, test strategy

---

### Session 05: WS-DSC Session 2 — Implementation (Lane 1 or 2)

| Field | Value |
|-------|-------|
| **Worktree** | `ws-dsc` (reuse or new) |
| **Rite** | 10x-dev |
| **Lane** | 1 or 2 (after WS-SYSCTX merges) |
| **Effort** | 2-3 days |
| **Dependencies** | WS-DSC Session 1 (TDD spec) |

**Worktree setup**: Reuse `ws-dsc` worktree if still alive, or create new after merging Session 1 TDD:
```bash
# If reusing: cd <ws-dsc-path> && claude
# If new:
ari worktree create "ws-dsc-impl" --rite "10x-dev"
cd <worktree-path>
claude
```

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-DSC.md
@.claude/wip/REM-ASANA-ARCH/WS-DSC-TDD-SPEC.md

WS-DSC Session 2: IMPLEMENTATION + QA.

Implement the execution policy per the TDD spec from Session 1.

Steps:
1. Create src/autom8_asana/clients/data/_policy.py with EndpointPolicy protocol + DefaultEndpointPolicy
2. Write policy unit tests before migrating any endpoint
3. Migrate simple.py first — scoped tests: pytest tests/unit/clients/data/ -k simple -x
4. Migrate remaining: reconciliation -> export -> insights -> batch (simplest to most complex)
5. Scoped tests after each: pytest tests/unit/clients/data/ -x
6. After all 5 migrated: pytest tests/unit/clients/ -x && pytest tests/api/ -x
7. Full suite at final gate: AUTOM8Y_ENV=production .venv/bin/python -m pytest tests/ -x

Measure before/after LOC per endpoint. Target: 50-80 -> 20-30.

Do NOT change _retry.py, circuit breaker logic, response shapes, or error types.

When complete, output checkpoint text for MEMORY.md.
```

**Scope boundary**: `clients/data/_endpoints/`, `clients/data/_policy.py` (new), `clients/data/client.py`

**Done gate**: All 5 endpoints migrated, LOC reduced, full suite green

---

## Phase 2: Consolidation (Days 6-9, 2 parallel lanes)

### Session 06: WS-DFEX Session 1 — DataFrame Extraction (Lane 1)

| Field | Value |
|-------|-------|
| **Worktree** | `ws-dfex` |
| **Rite** | hygiene |
| **Lane** | 1 |
| **Effort** | 1.5 days |
| **Dependencies** | WS-SYSCTX (soft — cleaner after, not blocked) |

**Worktree setup**:
```bash
ari worktree create "ws-dfex"
cd <worktree-path>
ari sync --rite=hygiene
claude
```

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-DFEX.md

Execute WS-DFEX Part A: Extract build_dataframe() to DataFrameService (R-006).

Skip Pythia — the seed IS the plan. Execute as principal-engineer direct.

Steps:
1. Read convenience methods in models/project.py and models/section.py (identify signatures, deferred imports)
2. Add new functions to services/dataframe_service.py: build_for_project(), build_for_section()
3. Audit ALL callers: grep for .build_dataframe() and .build_section_dataframe() across src/
4. Migrate ONE caller first — scoped tests: pytest tests/unit/models/ tests/unit/services/ -x
5. Migrate remaining callers
6. Remove convenience methods and deferred imports from model files
7. Static check: grep "from autom8_asana.dataframes" src/autom8_asana/models/project.py src/autom8_asana/models/section.py — should be empty
8. Scoped tests: pytest tests/unit/models/ tests/unit/dataframes/ tests/unit/services/ -x

Do NOT extract Task.save(). Do NOT change model fields or Pydantic configs.

Emit checkpoint at end. Part B (holder registry) is a separate session.
```

**Scope boundary**: `models/project.py`, `models/section.py`, `services/dataframe_service.py`, callers of build_dataframe()

**Done gate**: Zero dataframes imports in model files, Cycle 1 direction eliminated

---

### Session 07: WS-HYGIENE Session 1 — Quick Items (Lane 2)

| Field | Value |
|-------|-------|
| **Worktree** | `ws-hygiene` |
| **Rite** | hygiene |
| **Lane** | 2 |
| **Effort** | 1.5 days |
| **Dependencies** | WS-SYSCTX (for XR-003 on registry.py) |

**Worktree setup**:
```bash
ari worktree create "ws-hygiene"
cd <worktree-path>
ari sync --rite=hygiene
claude
```

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-HYGIENE.md

Execute WS-HYGIENE Session 1: Quick items + protocol introductions.

Pre-resolved: U-008 = 30/30 adversarial_pacing/paced_fetch tests PASS. XR-ARCH-006 is already resolved.

Skip Pythia — execute as principal-engineer direct.

Order:
1. XR-ARCH-006: ALREADY RESOLVED. Document in MEMORY.md checkpoint: "Pre-existing test failures resolved, 30/30 pass." (~5 min)
2. XR-ARCH-003: Replace private API call in dataframes/models/registry.py. Add on_schema_change callback, subscribe in services/resolver.py. Scoped tests: pytest tests/unit/dataframes/ tests/unit/services/ -x (~0.5 day)
3. XR-ARCH-004: Create InsightsProvider protocol in protocols/insights.py. Replace TYPE_CHECKING import in models/business/business.py. Scoped tests + mypy check. (~0.5 day)

NOTE: XR-003 touches dataframes/models/registry.py — WS-SYSCTX should have already migrated SchemaRegistry. If not yet merged, add the on_schema_change callback adjacent to (not conflicting with) the register_reset() call.

Emit checkpoint listing completed and remaining referrals.
```

**Scope boundary**: `dataframes/models/registry.py`, `services/resolver.py`, `models/business/business.py`, `protocols/insights.py` (new)

**Done gate**: XR-006 documented, XR-003 private API eliminated, XR-004 protocol created

---

### Session 08: WS-DFEX Session 2 — Holder Registry (Lane 1)

| Field | Value |
|-------|-------|
| **Worktree** | `ws-dfex` (reuse or new) |
| **Rite** | hygiene |
| **Lane** | 1 |
| **Effort** | 1.5-2 days |
| **Dependencies** | WS-DFEX Session 1 |

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-DFEX.md

Execute WS-DFEX Part B: Holder Type Registry (R-009).

Part A (DataFrame extraction) is complete. See MEMORY.md for status.

Steps:
1. Add HOLDER_REGISTRY: dict[str, type[Holder]] to persistence/holder_construction.py
2. Replace 6 explicit Holder imports with registry lookups
3. Each entity type module registers its Holder type (in _bootstrap.py or Holder module)
4. Add completeness test: assert all EntityRegistry types have registered Holders
5. Scoped tests: pytest tests/unit/persistence/ -x
6. Full suite at final gate: AUTOM8Y_ENV=production .venv/bin/python -m pytest tests/ -x

Do NOT modify SaveSession. Do NOT change Pydantic configs.

When complete, output checkpoint text: "WS-DFEX: DataFrame extraction + holder registry DONE"
```

**Scope boundary**: `persistence/holder_construction.py`, entity type modules in `models/business/`

**Done gate**: Registry implemented, completeness test passes, full suite green

---

### Session 09: WS-HYGIENE Session 2 — Structural (Lane 2)

| Field | Value |
|-------|-------|
| **Worktree** | `ws-hygiene` (reuse or new) |
| **Rite** | hygiene |
| **Lane** | 2 |
| **Effort** | 1-1.5 days |
| **Dependencies** | WS-HYGIENE Session 1 |

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-HYGIENE.md

Execute WS-HYGIENE Session 2: Structural work.

Session 1 completed: XR-006 (documented), XR-003 (callback), XR-004 (InsightsProvider). See MEMORY.md.

Order:
1. XR-ARCH-005: Define MetricsEmitter protocol in protocols/. Inject into DataFrameCache via DI. Wire concrete implementation in api/startup.py. Remove try/except import guard. Cycle 5 eliminated. Scoped tests: pytest tests/unit/cache/ tests/api/ -x (~0.5-1 day)
2. XR-ARCH-001: automation/ directory reorg. Extract insights_formatter to standalone location OR document as deferred. If effort exceeds 1 day, DEFER and document. (~0.5-1 day, low priority)

Full suite at final gate: AUTOM8Y_ENV=production .venv/bin/python -m pytest tests/ -x

When complete, output checkpoint: "WS-HYGIENE: cross-rite referrals DONE"
```

**Scope boundary**: `cache/integration/dataframe_cache.py`, `protocols/` (new files), `api/startup.py`, optionally `automation/workflows/`

**Done gate**: Cycle 5 eliminated (XR-005), XR-001 completed or documented as deferred, full suite green

---

## Phase 3: Evolution (Days 10-11, opportunistic)

### Session 10: WS-QUERY Session 1 — Architect (Lane 1)

| Field | Value |
|-------|-------|
| **Worktree** | `ws-query` |
| **Rite** | 10x-dev |
| **Lane** | 1 |
| **Effort** | 1 day |
| **Dependencies** | WS-DFEX (soft — clean service boundaries) |

**Worktree setup**:
```bash
ari worktree create "ws-query" --rite "10x-dev"
# OR:
ari worktree create "ws-query"
cd <worktree-path>
ari sync --rite=10x-dev
claude
```

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-QUERY.md

WS-QUERY Session 1: ARCHITECT PHASE.

Context: WS-DFEX has been completed — DataFrameService now owns build_dataframe(). Use the clean service boundary for the DataFrameProvider protocol design.

Read these files to understand the current query-to-service boundary:
- src/autom8_asana/query/engine.py (QueryEngine)
- src/autom8_asana/services/query_service.py (EntityQueryService)
- src/autom8_asana/services/universal_strategy.py (UniversalStrategy)
- src/autom8_asana/api/routes/query.py (DI wiring)

Design decisions:
1. Protocol location: protocols/dataframe_provider.py or query/protocols.py
2. Method signatures (match what QueryEngine actually needs from services)
3. How to handle to_pascal_case import (local utility or protocol method)
4. DI wiring approach via FastAPI Depends()

Write TDD spec to: .claude/wip/REM-ASANA-ARCH/WS-QUERY-TDD-SPEC.md

Do NOT implement code. Do NOT change query predicates, aggregation, response shapes, or guards.
Emit checkpoint.
```

**Scope boundary**: Read-only on `query/`, `services/`, `api/routes/`. Writes to `.claude/wip/` only.

**Done gate**: TDD spec with protocol definition and DI wiring strategy

---

### Session 11: WS-QUERY Session 2 — Implementation (Lane 1)

| Field | Value |
|-------|-------|
| **Worktree** | `ws-query` (reuse or new) |
| **Rite** | 10x-dev |
| **Lane** | 1 |
| **Effort** | 2 days |
| **Dependencies** | WS-QUERY Session 1 (TDD spec) |

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-QUERY.md
@.claude/wip/REM-ASANA-ARCH/WS-QUERY-TDD-SPEC.md

WS-QUERY Session 2: IMPLEMENTATION + QA.

Implement per TDD spec from Session 1.

Steps:
1. Create DataFrameProvider protocol per spec
2. Verify UniversalStrategy satisfies protocol (structural typing)
3. Refactor QueryEngine constructor: accept DataFrameProvider, remove services/ imports
4. Replace to_pascal_case import per spec decision
5. Update api/routes/query.py DI wiring
6. Write mock-based QueryEngine test (instantiate with mock provider)
7. Scoped tests: pytest tests/unit/query/ -x && pytest tests/api/ -k query -x
8. Full suite at final gate: AUTOM8Y_ENV=production .venv/bin/python -m pytest tests/ -x

Static check: grep "from autom8_asana.services" src/autom8_asana/query/engine.py — should be empty.

When complete, output checkpoint: "WS-QUERY: query engine decoupling DONE"
```

**Scope boundary**: `query/engine.py`, `protocols/` or `query/protocols.py` (new), `services/universal_strategy.py`, `api/routes/query.py`

**Done gate**: No services/ imports in query/engine.py, mock-based test passes, full suite green

---

## Parallel Execution Schedule (2 Lanes)

```
         Day1    Day2    Day3    Day4    Day5    Day6    Day7    Day8    Day9    Day10   Day11
Lane 1:  S01     S02     S02     S05     S05     S06     S06     S08     S08     S10     S11
         WS-QW   SYSCTX  SYSCTX  DSC-2   DSC-2   DFEX-1  DFEX-1  DFEX-2  DFEX-2  QRY-1   QRY-2

Lane 2:          S03     S04     S04     S07     S07     S09     S09
                 DEBT    DSC-1   DSC-1   HYG-1   HYG-1   HYG-2   HYG-2

Gates:   [G0]            [G1a]           [G1b]           [G2a]   [G2b]           [G3]
```

### Phase Gates (Hub Thread Verifies)

**[G0] Post WS-QW** (Day 1 end):
```bash
# Verify R-002 helpers extracted
grep "extract_user_gid\|extract_first_rep\|resolve_assignee_gid" src/autom8_asana/core/creation.py
# Merge ws-qw, update TRACKER.md
```

**[G1a] Post WS-SYSCTX** (Day 3 end):
```bash
# Verify Cycle 4 eliminated
grep "from autom8_asana.models\|from autom8_asana.dataframes\|from autom8_asana.services\|from autom8_asana.metrics" src/autom8_asana/core/system_context.py
# Should return empty. Merge ws-sysctx.
```

**[G1b] Post WS-DSC** (Day 5 end):
```bash
# Verify policy exists and all endpoints use it
ls src/autom8_asana/clients/data/_policy.py
grep "_policy\|EndpointPolicy\|DefaultEndpointPolicy" src/autom8_asana/clients/data/_endpoints/*.py
# Merge ws-dsc.
```

**[G2a] Post WS-DFEX Part A** (Day 7 end):
```bash
# Verify no dataframes imports in models
grep "from autom8_asana.dataframes\|import.*dataframes" src/autom8_asana/models/project.py src/autom8_asana/models/section.py
# Should return empty.
```

**[G2b] Post WS-DFEX Part B** (Day 9 end):
```bash
# Verify holder registry
grep "HOLDER_REGISTRY" src/autom8_asana/persistence/holder_construction.py
# Merge ws-dfex. Run full suite.
```

**[G3] Post WS-QUERY** (Day 11 end):
```bash
# Verify query engine decoupled
grep "from autom8_asana.services" src/autom8_asana/query/engine.py
# Should return empty. Final full suite run. Initiative complete.
```

---

## Merge Protocol

### Sequential Merge Order (prevents conflicts)

After each session completes:
```bash
# 1. In main project directory
cd /Users/tomtenuta/Code/autom8y-asana

# 2. Ensure main is clean
git status

# 3. Merge worktree branch
git merge <worktree-branch>

# 4. If conflicts: resolve manually (expected to be additive-only per scope contracts)

# 5. Run full suite to verify
AUTOM8Y_ENV=production .venv/bin/python -m pytest tests/ -x

# 6. Update TRACKER.md (mark workstream complete, log merge)

# 7. Update MEMORY.md (paste checkpoint from session output)

# 8. Remove worktree
ari worktree remove "<worktree-id>"
```

### Parallel Merge Safety

When 2 sessions complete close together, merge sequentially (not simultaneously):
```
Session A completes -> merge A -> run tests -> update docs
Session B completes -> merge B -> run tests -> update docs
```

Never merge two worktree branches at the same time.

---

## MEMORY.md Write Templates

### Single-Session Completion
```markdown
## Completed Work (WS-{ID}) [date]
- WS-{ID}: {summary} DONE [date]
  - {item}: {result}
  - Test status: {passed}/{total}
```

### Multi-Session Checkpoint
```markdown
## Checkpoint WS-{ID} [date]
Completed: {list}
Remaining: {list}
Decisions: {key decisions}
Test status: {passed} passed
```

### Initiative Completion
```markdown
## REM-ASANA-ARCH Complete [date]
- Health score: 68/100 -> {final}/100
- Cycles eliminated: {list}
- Workstreams: 7 completed (WS-CLASS skipped)
- Test baseline: {final count} (from 10,552)
```

---

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| File path drift (WS6 lesson) | Every seed says "verify file paths before editing" (Guardrail #7) |
| R-002 logic divergence | Diff carefully in Step 3; if divergent, extract only identical logic, file delta as debt |
| WS-SYSCTX registration order | One singleton at a time with scoped tests. 3x stability at end. |
| WS-DSC over-generalization | Architect TDD defines boundaries; PE follows protocol, not aspirational interface |
| Merge conflicts on registry.py | WS-HYGIENE XR-003 scheduled AFTER WS-SYSCTX merges (scope contract) |
| MEMORY.md growth | Hub thread compacts after each phase. Archive detail to COMPLETED-LOG.md if >200 lines. |
