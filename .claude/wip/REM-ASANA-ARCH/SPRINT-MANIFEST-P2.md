# REM-ASANA-ARCH Phase 2 Sprint Manifest

**Pattern**: sprint-parallel-worktrees (hub-and-spoke, 1-lane primary)
**Initiative**: Architecture Remediation Phase 2 (83 -> 92+)
**Sessions**: 3 required + 1 optional
**Parallelism**: 1 primary lane (P2-04 can parallel with P2-01 if desired)
**Target**: ~10-13 hours total

---

## Execution Protocol

### Per-Worktree Lifecycle (Identical to Phase 1)

```
1. HUB:       ari worktree create "<ws-name>" --rite "<rite>"
2. HUB:       Note worktree path from output
3. TERMINAL:  cd <worktree-path> && claude
4. WORKTREE:  @.claude/wip/REM-ASANA-ARCH/PROMPT_0-P2.md
              @.claude/wip/REM-ASANA-ARCH/WS-P2-{NN}.md
              <session prompt from manifest below>
5. WORKTREE:  (autonomous execution per seed)
6. WORKTREE:  /wrap
7. HUB:       cd <main-project> && git merge <worktree-branch>
8. HUB:       Update TRACKER.md + MEMORY.md
9. HUB:       ari worktree remove "<worktree-id>"
```

### Rite Switching

Rite changes require full Claude restart:
```bash
# In the worktree BEFORE launching claude:
ari sync --rite=<rite-name>
# Then start claude fresh in that worktree
claude
```

### Test Protocol

- **During development**: Scoped tests only (`pytest tests/unit/<module>/ -x`)
- **At QA gates**: Full suite (`AUTOM8Y_ENV=production .venv/bin/python -m pytest tests/ -x`)
- QA gates: end of each session, NOT after every change

---

## Session Definitions

### Session P2-01: Utility Extraction + EntityRegistry Fix

| Field | Value |
|-------|-------|
| **Worktree** | `ws-p2-01` |
| **Rite** | hygiene |
| **Lane** | 1 (solo) |
| **Effort** | 2 hours |
| **Dependencies** | None |

**Worktree setup**:
```bash
ari worktree create "ws-p2-01"
cd <worktree-path>
ari sync --rite=hygiene
claude
```

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0-P2.md
@.claude/wip/REM-ASANA-ARCH/WS-P2-01.md

Execute P2-01: Utility Extraction + EntityRegistry Fix.

No Phase 0 pre-flight needed -- the gap analysis is complete.
Skip Pythia orchestration -- the seed IS the plan.

Order: G-01 (to_pascal_case) -> G-02 (register_holder) -> G-03 (EntityRegistry).
Scoped tests after each. Full suite at the end only.

When complete, output checkpoint text for MEMORY.md.
```

**Scope boundary**: `core/string_utils.py`, `core/registry.py`, `core/entity_registry.py`,
`services/resolver.py`, `persistence/holder_construction.py`, import sites in cache/, core/,
dataframes/, models/business/

**Done gate**: All 3 grep gates pass, full suite green

---

### Session P2-02: Surgical Cycle Cuts

| Field | Value |
|-------|-------|
| **Worktree** | `ws-p2-02` |
| **Rite** | 10x-dev |
| **Lane** | 1 (solo -- too complex for parallel) |
| **Effort** | 4-5 hours |
| **Dependencies** | P2-01 (soft -- G-01 helps core<->dataframes) |

**Worktree setup**:
```bash
ari worktree create "ws-p2-02"
cd <worktree-path>
ari sync --rite=10x-dev
claude
```

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0-P2.md
@.claude/wip/REM-ASANA-ARCH/WS-P2-02.md

Execute P2-02: Surgical Cycle Cuts (5 bidirectional imports).

P2-01 is complete -- to_pascal_case is now in core/string_utils.py,
register_holder is now in core/registry.py.

This is a 10x-dev session. Read each cycle's files before fixing.
Combined architect+implement within this session (no separate TDD).

Order: automation<->lifecycle (smallest) -> dataframes<->services ->
cache<->models -> core<->dataframes -> core<->models (largest).

Per-cycle pattern: read -> fix -> grep gate -> scoped test.
Full suite at the end only.

When complete, output checkpoint listing which cycles were cut and how.
```

**Scope boundary**: `automation/workflows/pipeline_transition.py`, `lifecycle/seeding.py`,
`dataframes/builders/progressive.py`, `cache/integration/derived.py`,
`models/business/detection/facade.py`, `core/schema.py`, `core/registry_validation.py`

**Done gate**: All 5 grep gates pass, full suite green

---

### Session P2-03: Protocol Purity + Guard Cleanup

| Field | Value |
|-------|-------|
| **Worktree** | `ws-p2-03` |
| **Rite** | hygiene |
| **Lane** | 1 |
| **Effort** | 2-3 hours |
| **Dependencies** | P2-02 (hard -- G-08 depends on which cycles were cut) |

**Worktree setup**:
```bash
ari worktree create "ws-p2-03"
cd <worktree-path>
ari sync --rite=hygiene
claude
```

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0-P2.md
@.claude/wip/REM-ASANA-ARCH/WS-P2-03.md

Execute P2-03: Protocol Purity + TYPE_CHECKING Guard Cleanup.

P2-02 is complete. See MEMORY.md for which cycles were cut.

Order: G-05 (protocol purity, 3 files) -> G-08 (guard cleanup in cycle-cut files).

For G-08: only remove TYPE_CHECKING guards for cycles confirmed cut in P2-02.
If in doubt about whether a guard is still needed, keep it.

Full suite at the end only.

When complete, output checkpoint with before/after TYPE_CHECKING guard counts.
```

**Scope boundary**: `protocols/cache.py`, `protocols/dataframe_provider.py`,
`protocols/insights.py`, plus scan of cycle-cut files from P2-02

**Done gate**: Zero runtime impl imports in protocols/, guard counts reduced, full suite green

---

### Session P2-04 (OPTIONAL): Test Fixes + automation/ Reorg

| Field | Value |
|-------|-------|
| **Worktree** | `ws-p2-04` |
| **Rite** | hygiene |
| **Lane** | 1 (or parallel with P2-01 in Lane 2) |
| **Effort** | 5 hours |
| **Dependencies** | None |

**Worktree setup**:
```bash
ari worktree create "ws-p2-04"
cd <worktree-path>
ari sync --rite=hygiene
claude
```

**Session prompt**:
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0-P2.md
@.claude/wip/REM-ASANA-ARCH/WS-P2-04.md

Execute P2-04 (OPTIONAL): Fix phantom HTTP mock targets + automation/ reorg.

G-07 first (mock fixes, 2-3 hrs). Reference: .wip/REMEDY-tests-unit-p1.md
G-06 second only if time permits. Stop G-06 after 2 hrs if not complete.

Full suite at the end only.

When complete, output checkpoint.
```

**Scope boundary**: `tests/unit/clients/data/test_client.py`,
`tests/unit/services/test_gid_push.py`, optionally `automation/pipeline.py`

**Done gate**: Phantom mocks fixed, full suite green

---

## Execution Schedule

### Recommended Order (Sequential, 1 Lane)

```
Session 1:  P2-01 (2 hrs)    -- utility extraction + EntityRegistry
            [merge -> TRACKER -> MEMORY]

Session 2:  P2-02 (4-5 hrs)  -- surgical cycle cuts
            [merge -> TRACKER -> MEMORY]

Session 3:  P2-03 (2-3 hrs)  -- protocol purity + guard cleanup
            [merge -> TRACKER -> MEMORY]

Session 4:  P2-04 (5 hrs)    -- OPTIONAL test fixes + reorg
(optional)  [merge -> TRACKER -> MEMORY]
```

### Alternative: P2-01 + P2-04 Parallel (2 Lanes)

```
Lane 1:  P2-01 (2 hrs)     Lane 2:  P2-04 (5 hrs)
         [merge]                     [merge when done]
         P2-02 (4-5 hrs)
         [merge]
         P2-03 (2-3 hrs)
         [merge]
```

P2-04 has zero file overlap with P2-01, P2-02, or P2-03 (test files only).
Safe to run in parallel with any session.

---

## Phase Gates (Hub Thread Verifies)

**[GP2-01] Post P2-01** (after merge):
```bash
# Verify utility extraction
grep "from autom8_asana.services.resolver import to_pascal_case" src/ -r | wc -l  # -> 0
grep "from autom8_asana.persistence.holder_construction import register_holder" src/autom8_asana/models/ -r | wc -l  # -> 0
grep "register_reset" src/autom8_asana/core/entity_registry.py | wc -l  # -> 1+
```

**[GP2-02] Post P2-02** (after merge):
```bash
# Verify 5 cycles broken
grep "from autom8_asana.lifecycle" src/autom8_asana/automation/ -r | wc -l   # 0
grep "from autom8_asana.automation" src/autom8_asana/lifecycle/ -r | wc -l   # 0
grep "from autom8_asana.services" src/autom8_asana/dataframes/ -r | wc -l   # 0
grep "from autom8_asana.cache" src/autom8_asana/models/ -r | wc -l          # 0
grep "from autom8_asana.dataframes" src/autom8_asana/core/ -r | wc -l       # 0
grep "from autom8_asana.models" src/autom8_asana/core/ -r | wc -l           # 0 or TYPE_CHECKING only
```

**[GP2-03] Post P2-03** (after merge):
```bash
# Verify protocol purity
grep -r "from autom8_asana.cache" src/autom8_asana/protocols/ | grep -v TYPE_CHECKING | wc -l   # 0
grep -r "from autom8_asana.clients" src/autom8_asana/protocols/ | grep -v TYPE_CHECKING | wc -l  # 0
```

**[GP2-04] Post P2-04** (after merge, optional):
```bash
# Verify mock fixes
grep -r "httpx.AsyncClient" tests/unit/clients/data/test_client.py | wc -l  # 0
grep -r "httpx.AsyncClient" tests/unit/services/test_gid_push.py | wc -l   # 0
```

---

## Merge Protocol (Identical to Phase 1)

After each session completes:
```bash
# 1. In main project directory
cd /Users/tomtenuta/Code/autom8y-asana

# 2. Ensure main is clean
git status

# 3. Merge worktree branch
git merge <worktree-branch>

# 4. Run full suite to verify
AUTOM8Y_ENV=production .venv/bin/python -m pytest tests/ -x

# 5. Update TRACKER.md (mark workstream complete)
# 6. Update MEMORY.md (paste checkpoint from session output)
# 7. Remove worktree (AFTER checking for uncommitted changes)
git -C <worktree-path> status  # MUST check first
ari worktree remove "<worktree-id>"
```

---

## MEMORY.md Write Templates

### Session Completion
```markdown
## P2-{NN} Complete [{date}]
- P2-{NN}: {summary} DONE
  - {gap}: {result}
  - {gap}: {result}
  - Test status: {passed}/{total}
  - Health score: {previous} -> {new}
```

### Phase 2 Initiative Completion
```markdown
## REM-ASANA-ARCH Phase 2 Complete [{date}]
- Health score: 83 -> {final}/100
- Cycles cut: {list of 5}
- Protocols purified: cache, dataframe_provider, insights
- Utilities extracted: to_pascal_case -> core/, register_holder -> core/
- EntityRegistry registered with SystemContext
- TYPE_CHECKING guards reduced by {N}
```

---

## Score Projection

| After Session | Score | Delta | Cumulative Effort |
|---------------|-------|-------|-------------------|
| Phase 1 (done) | 83 | +15 from 68 | ~10 hrs |
| P2-01 | 88 | +5 | +2 hrs |
| P2-02 | 91 | +3 | +5 hrs |
| P2-03 | 93 | +2 | +3 hrs |
| P2-04 (optional) | 94-95 | +1-2 | +5 hrs |

**Minimum sessions to hit 92+**: 3 (P2-01 through P2-03, ~10 hrs)

---

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| File path drift | Guardrail #7: verify paths before editing. Seeds list exact paths. |
| Cycle cut breaks runtime imports | Read-first pattern in P2-02. Per-cycle scoped tests. |
| TYPE_CHECKING guard removal causes circular import | G-08 explicitly says: if removal causes import error, keep the guard. |
| P2-02 too complex for single session | If >5 hrs, emit checkpoint and continue in P2-02b session. |
| P2-04 G-06 scope creep | Hard 2-hour time-box on G-06. Stop and defer if not complete. |
| Merge conflicts between parallel P2-01 + P2-04 | Zero file overlap (src/ vs tests/). Safe. |
